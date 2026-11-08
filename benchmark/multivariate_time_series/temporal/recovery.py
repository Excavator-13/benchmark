"""Parent-linked recovery from complete epoch boundaries.

A resume never mutates the parent directory: it reserves a new execution
identity that records the parent run, the parent recovery SHA256 and the shared
condition.  The recovery payload must match the parent's effective conditions
(data contents, canonical keys, configuration, protocol and condition identity)
and the cumulative budget must not be exhausted; old, corrupt or mismatched
checkpoints fail explicitly before any worker starts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import torch

from . import artifacts, checkpoints, protocol
from . import engine as temporal_engine


class RecoveryError(protocol.ProtocolError):
    """Raised when a parent trajectory cannot be resumed safely."""


def _read_json(path: Path) -> Any:
    payload = artifacts.read_json(Path(path))
    return payload


def remaining_budget_seconds(ledger_path: Optional[Path]) -> Optional[float]:
    """Return the remaining cumulative batch budget from the persistent ledger."""
    if ledger_path is None:
        return None
    path = Path(ledger_path)
    if not path.exists():
        return protocol.BATCH_SECONDS
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    active = sum(
        float(entry.get("seconds", 0.0))
        for entry in payload.get("entries", [])
        if entry.get("kind") in {"measured", "replayed"}
    )
    return max(0.0, protocol.BATCH_SECONDS - active)


def load_parent(
    parent_dir: Path,
    *,
    ledger_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Validate a parent run and return its recovery payload plus identity."""
    directory = Path(parent_dir)
    config_doc = _read_json(directory / "config.json")
    provenance = _read_json(directory / "provenance.json")
    status_doc = _read_json(directory / "status.json")
    if config_doc.get("operation") not in {"fit", "resume"}:
        raise RecoveryError(
            f"{directory} is a {config_doc.get('operation')!r} run; only a fit or "
            "resumed trajectory has recoverable training state"
        )
    payload = checkpoints.load_last(directory / protocol.RUN_DIRECTORY_FILES["last_recovery"])
    stored_config = protocol.FitConfig.from_payload(payload["config"])
    parent_config = protocol.FitConfig.from_payload(config_doc["config"])
    if stored_config.to_payload() != parent_config.to_payload():
        raise RecoveryError(
            f"{directory}: recovery configuration {stored_config.to_payload()} does "
            f"not match the parent config {parent_config.to_payload()}"
        )
    data = provenance.get("data") or {}
    checkpoint_data = payload.get("data") or {}
    for field in ("source_sha256", "node_keys_sha256", "dataset"):
        if checkpoint_data.get(field) != data.get(field):
            raise RecoveryError(
                f"{directory}: recovery {field} {checkpoint_data.get(field)!r} does not "
                f"match the parent provenance {data.get(field)!r}"
            )
    condition = config_doc.get("condition") or {}
    checkpoint_condition = payload.get("condition") or {}
    if checkpoint_condition.get("condition_id") != condition.get("condition_id"):
        raise RecoveryError(
            f"{directory}: recovery condition identity does not match the parent run"
        )
    completed_epoch = int(payload.get("completed_epoch", 0))
    if completed_epoch <= 0:
        raise RecoveryError(
            f"{directory}: recovery checkpoint records no complete epoch"
        )
    if completed_epoch >= parent_config.epochs and status_doc.get("state") == "completed":
        raise RecoveryError(
            f"{directory}: the parent trajectory already completed all "
            f"{parent_config.epochs} epochs; there is nothing to resume"
        )
    remaining = remaining_budget_seconds(ledger_path)
    if remaining is not None and remaining <= 0:
        raise RecoveryError(
            "the cumulative batch budget is exhausted; a new execution identity "
            "cannot reset the consumed wall-clock budget"
        )
    from .protocol import sha256_file

    return {
        "payload": payload,
        "parent_config": parent_config,
        "parent_config_doc": config_doc,
        "parent_provenance": provenance,
        "parent_status": status_doc,
        "completed_epoch": completed_epoch,
        "recovery_path": str(
            directory / protocol.RUN_DIRECTORY_FILES["last_recovery"]
        ),
        "recovery_sha256": sha256_file(
            directory / protocol.RUN_DIRECTORY_FILES["last_recovery"]
        ),
        "remaining_batch_seconds": remaining,
    }


def build_restore_state(payload: Mapping[str, Any]) -> temporal_engine.RestoreState:
    """Convert a validated recovery payload into engine restore state."""
    best = payload.get("best")
    return temporal_engine.RestoreState(
        completed_epoch=int(payload["completed_epoch"]),
        updates=int(payload["updates"]),
        model_state={
            name: tensor.detach().to("cpu", dtype=torch.float32).clone()
            for name, tensor in payload["model_state"].items()
        },
        optimizer_state=temporal_engine.temporal_model.deepcopy_state(
            payload["optimizer_state"]
        ),
        history=[dict(record) for record in payload["history"]],
        scores=temporal_engine.temporal_model.deepcopy_state(
            payload.get("scores") or {}
        ),
        update_records=[dict(record) for record in payload.get("update_records") or []],
        best=(
            {
                **dict(best),
                "model_state": temporal_engine.temporal_model.deepcopy_state(
                    best["model_state"]
                ),
                "optimizer_state": temporal_engine.temporal_model.deepcopy_state(
                    best["optimizer_state"]
                ),
            }
            if best
            else None
        ),
        random_states=payload["random_states"],
    )
