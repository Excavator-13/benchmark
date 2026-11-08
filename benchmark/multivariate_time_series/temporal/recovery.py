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

import math

import torch

from . import artifacts, checkpoints, protocol, resources, checks
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
    batch_id: Optional[str] = None,
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
    # The checkpoint binds the captured runtime and actual execution environment.
    execution = payload.get("execution") or {}
    if not execution.get("source") or not execution.get("environment"):
        raise RecoveryError("recovery lacks bound source/environment evidence; refit with the current format")
    if execution["source"] != provenance.get("source") or execution["environment"] != provenance.get("environment"):
        raise RecoveryError("parent source/environment differs from the bound recovery state")
    files = execution["source"].get("files") or {}
    if not files:
        raise RecoveryError("recovery source inventory is missing")
    for name, entry in files.items():
        current = artifacts.repo_root() / name
        actual = protocol.sha256_file(current) if current.is_file() else None
        if actual != entry.get("sha256"):
            raise RecoveryError(f"current source differs from parent: {name}")
    temporal_engine.temporal_model.set_determinism(parent_config.seed, parent_config.threads)
    environment = artifacts.capture_environment()
    if any(environment.get(field) != execution["environment"].get(field) for field in checks.ENVIRONMENT_FIELDS):
        raise RecoveryError("current execution environment differs from parent")
    if (provenance.get("protocol") or {}).get("sha256") != protocol.protocol_content_sha256():
        raise RecoveryError("current protocol differs from parent")
    bound = payload.get("ledger") or {}
    bound_path = bound.get("path")
    if not bound_path or not bound.get("ledger_id") or not bound.get("trajectory_execution_ids"):
        raise RecoveryError("recovery lacks verifiable inherited ledger evidence")
    if ledger_path is not None and Path(ledger_path).resolve() != Path(bound_path).resolve():
        raise RecoveryError("resume ledger path must match the inherited ledger")
    if not Path(bound_path).is_file():
        raise RecoveryError("inherited ledger is missing; budget cannot be reset")
    if batch_id is not None and batch_id != bound.get("batch_id"):
        raise RecoveryError("resume batch identity differs from inherited ledger")
    ledger = resources.Ledger(Path(bound_path), batch_id=bound["batch_id"])
    if ledger.payload.get("ledger_id") != bound["ledger_id"] or ledger.active_seconds() < bound.get("active_seconds", 0):
        raise RecoveryError("inherited ledger was replaced or lost consumed budget")
    entries = {entry["execution_id"]: entry for entry in ledger.payload["entries"]}
    ids = bound["trajectory_execution_ids"]
    if any(identity not in entries for identity in ids):
        raise RecoveryError("inherited trajectory billing evidence is missing")
    for identity in ids:
        entry = entries[identity]
        if (entry.get("kind") not in {"measured", "replayed"}
                or not math.isfinite(float(entry.get("seconds", -1)))
                or float(entry.get("seconds", -1)) < 0
                or entry.get("status") == "running"):
            raise RecoveryError("inherited active-time entry is incomplete or unverifiable")
    fit_spent = sum(float(entries[identity]["seconds"]) for identity in ids)
    billing_path = directory / "billing.json"
    if billing_path.is_file():
        billing = _read_json(billing_path)
        if (billing.get("ledger_id") != bound["ledger_id"]
                or billing.get("execution_id") not in ids
                or float(entries[billing["execution_id"]]["seconds"]) < billing.get("execution_seconds", float("inf"))
                or fit_spent < billing.get("trajectory_seconds", float("inf"))):
            raise RecoveryError("inherited ledger lost measured execution time")
    if fit_spent >= protocol.FIT_SECONDS:
        raise RecoveryError("inherited single-fit trajectory budget is exhausted")
    # Complete-epoch time includes its own checkpoint publication, so the exact
    # final duration is recorded after that publication in this immutable sidecar.
    timing = directory / "epoch-timing.json"
    if timing.is_file():
        durations = _read_json(timing).get("epochs") or {}
        for record in payload["history"]:
            if str(record["epoch"]) in durations:
                record["wall_seconds"] = durations[str(record["epoch"])]
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
    remaining = ledger.remaining_seconds()
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
        "ledger_path": str(Path(bound_path).resolve()),
        "batch_id": bound["batch_id"],
        "trajectory_execution_ids": ids,
        "fit_spent_seconds": fit_spent,
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
