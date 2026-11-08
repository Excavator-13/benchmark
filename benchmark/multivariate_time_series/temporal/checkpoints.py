"""Checkpoint payloads: immutable best weights and recoverable last state.

Both payload types are format-2 dictionaries saved with ``torch.save``; neither
is a pickled model object.  The best payload is an immutable copy selected by
validation MSE, while the last payload is the recoverable epoch boundary and is
published atomically (same-directory temporary file, fsync, rename).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import torch

from . import model as temporal_model
from . import protocol

BEST_KIND = "best"
LAST_KIND = "last"


def _base(kind: str, config: protocol.FitConfig, scientific_version: str = protocol.SCIENTIFIC_VERSION) -> Dict[str, Any]:
    return {
        "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
        "scientific_version": scientific_version,
        "kind": kind,
        "config": config.to_payload(),
    }


def best_payload(
    config: protocol.FitConfig,
    *,
    best: Mapping[str, Any],
    model_state: Mapping[str, torch.Tensor],
    optimizer_state: Mapping[str, Any],
    scale: float,
    condition: Optional[Mapping[str, Any]] = None,
    parameter_report: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    payload = _base(BEST_KIND, config)
    payload.update(
        {
            "manifest": dict(best),
            "model_state": {
                name: tensor.detach().to("cpu", dtype=torch.float32).clone()
                for name, tensor in model_state.items()
            },
            "optimizer_state": temporal_model.deepcopy_state(optimizer_state),
            "scale": float(scale),
            "condition": dict(condition or {}),
            "parameter_report": dict(parameter_report or {}),
        }
    )
    return payload


def save_best(path: Path, payload: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(dict(payload), path)
    return path


def load_best(path: Path, *, expected_config: Optional[protocol.FitConfig] = None) -> Dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise protocol.ProtocolError(f"best checkpoint is missing: {path}")
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict):
        raise protocol.ProtocolError(f"{path}: checkpoint payload is not a mapping")
    version = payload.get("artifact_format_version")
    if version != protocol.ARTIFACT_FORMAT_VERSION:
        raise protocol.ProtocolError(
            f"{path}: artifact format {version!r} is not "
            f"{protocol.ARTIFACT_FORMAT_VERSION}; legacy single-window checkpoints "
            "cannot be upgraded or reused"
        )
    if payload.get("kind") != BEST_KIND:
        raise protocol.ProtocolError(f"{path}: checkpoint kind is not 'best'")
    if payload.get("scientific_version") != protocol.SCIENTIFIC_VERSION:
        raise protocol.ProtocolError(
            f"{path}: scientific version {payload.get('scientific_version')!r} is "
            f"not {protocol.SCIENTIFIC_VERSION}"
        )
    if expected_config is not None:
        stored = protocol.FitConfig.from_payload(payload["config"])
        if stored.to_payload() != expected_config.to_payload():
            raise protocol.ProtocolError(
                f"{path}: checkpoint configuration {stored.to_payload()} does not "
                f"match the requested {expected_config.to_payload()}"
            )
    return payload


def last_payload(
    config: protocol.FitConfig,
    trajectory: Any,
    *,
    condition: Mapping[str, Any],
    data_identity: Mapping[str, Any],
    best: Mapping[str, Any],
    best_model_state: Mapping[str, torch.Tensor],
    best_optimizer_state: Mapping[str, Any],
    scale: float,
    ledger: Optional[Mapping[str, Any]] = None,
    execution: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the complete epoch-boundary recovery state for one trajectory."""
    payload = _base(LAST_KIND, config)
    payload.update(
        {
            "completed_epoch": int(trajectory.completed_epoch),
            "updates": int(trajectory.updates),
            "next_window": 0,
            "model_state": temporal_model.clone_state_dict(trajectory.model),
            "optimizer_state": temporal_model.deepcopy_state(
                trajectory.optimizer.state_dict()
            ),
            "random_states": temporal_model.random_states(),
            "history": [dict(record) for record in trajectory.history],
            "scores": {
                key: temporal_model.deepcopy_state(value)
                for key, value in trajectory.scores.items()
            },
            "update_records": [dict(record) for record in trajectory.update_records],
            "best": {
                "epoch": int(best["epoch"]),
                "updates": int(best["updates"]),
                "validation": dict(best["validation"]),
                "scale": float(scale),
                "model_state": {
                    name: tensor.detach().to("cpu").clone()
                    for name, tensor in best_model_state.items()
                },
                "optimizer_state": temporal_model.deepcopy_state(
                    best_optimizer_state
                ),
            },
            "scale": float(scale),
            "condition": dict(condition),
            "data": dict(data_identity),
            "ledger": dict(ledger or {}),
            "execution": dict(execution or {}),
        }
    )
    return payload


class PublicationError(RuntimeError):
    """Raised when an atomic checkpoint publication fails."""


def publish_last(path: Path, payload: Mapping[str, Any]) -> str:
    """Atomically publish the last recovery checkpoint and return its SHA256.

    A failure before the final rename leaves the previous complete file intact;
    a partially written temporary file is removed and never becomes current.
    """
    from .protocol import sha256_file

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            torch.save(dict(payload), handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:  # pragma: no cover - best-effort cleanup
            pass
        raise
    return sha256_file(path)


def load_last(path: Path) -> Dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise protocol.ProtocolError(
            f"recovery checkpoint is missing: {path}; an interrupted trajectory "
            "must restart from a complete epoch boundary"
        )
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as exc:  # corrupt/truncated checkpoint
        raise protocol.ProtocolError(
            f"{path}: recovery checkpoint is unreadable or truncated: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise protocol.ProtocolError(f"{path}: recovery payload is not a mapping")
    version = payload.get("artifact_format_version")
    if version is None:
        raise protocol.ProtocolError(
            f"{path}: legacy checkpoint without artifact_format_version; old "
            "checkpoints cannot be resumed under the staged protocol"
        )
    if version != protocol.ARTIFACT_FORMAT_VERSION:
        raise protocol.ProtocolError(
            f"{path}: recovery artifact format {version!r} is not "
            f"{protocol.ARTIFACT_FORMAT_VERSION}"
        )
    if payload.get("kind") != LAST_KIND:
        raise protocol.ProtocolError(
            f"{path}: checkpoint kind is {payload.get('kind')!r}, not 'last'; the "
            "best snapshot is not a recoverable last state"
        )
    required = (
        "completed_epoch",
        "updates",
        "model_state",
        "optimizer_state",
        "random_states",
        "history",
        "best",
        "condition",
        "data",
    )
    missing = [name for name in required if name not in payload]
    if missing:
        raise protocol.ProtocolError(
            f"{path}: recovery checkpoint is missing required state {missing}"
        )
    return payload
