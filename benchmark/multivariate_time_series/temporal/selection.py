"""Frozen learning-rate selection and a/b repetition identity.

Selection reads exactly two completed seed-0 screening trajectories, compares
their best validation original-unit MSE, prefers the smaller learning rate on an
exact tie and records the winner as repetition ``a`` by link.  It never reads a
test score, never refits and never schedules the remaining matrix.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from . import resources, protocol


class SelectionError(protocol.ProtocolError):
    """Raised when selection inputs cannot form a frozen selection."""


@dataclass(frozen=True)
class Candidate:
    learning_rate: float
    run_id: str
    run_dir: str
    status: str
    validation_mse: Optional[float]
    validation_mae: Optional[float]
    selected_epoch: Optional[int]
    seed: int
    model: str
    dataset: str
    mode: str
    purpose: str
    config: Dict[str, Any]
    roles: Dict[str, Any]
    condition_id: Optional[str]
    data_sha256: Optional[str]
    keys_sha256: Optional[str]
    protocol_sha256: Optional[str]
    run_sha256: Optional[str]
    message: Optional[str] = None
    protocol_controls_complete: bool = True

    def payload(self) -> Dict[str, Any]:
        return {
            "learning_rate": float(self.learning_rate),
            "run_id": self.run_id,
            "run_dir": self.run_dir,
            "status": self.status,
            "validation_MSE": self.validation_mse,
            "validation_MAE": self.validation_mae,
            "selected_epoch": self.selected_epoch,
            "seed": int(self.seed),
            "model": self.model,
            "dataset": self.dataset,
            "mode": self.mode,
            "purpose": self.purpose,
            "config": dict(self.config),
            "roles": dict(self.roles),
            "condition_id": self.condition_id,
            "data_sha256": self.data_sha256,
            "keys_sha256": self.keys_sha256,
            "protocol_sha256": self.protocol_sha256,
            "run_sha256": self.run_sha256,
            "message": self.message,
            "protocol_controls_complete": self.protocol_controls_complete,
        }


def _read_json(path: Path) -> Any:
    resources.check_stage_budget()
    if not Path(path).exists():
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_candidate(run_dir: Path) -> Candidate:
    """Read one candidate trajectory's frozen identity and validation score."""
    resources.check_stage_budget()
    directory = Path(run_dir)
    config_doc = _read_json(directory / "config.json")
    if not isinstance(config_doc, dict):
        raise SelectionError(
            f"candidate {directory} is missing config.json; it is not a format-v2 run"
        )
    if config_doc.get("artifact_format_version") != protocol.ARTIFACT_FORMAT_VERSION:
        raise SelectionError(
            f"candidate {directory} is not artifact format "
            f"{protocol.ARTIFACT_FORMAT_VERSION}"
        )
    status_doc = _read_json(directory / "status.json") or {}
    config = protocol.FitConfig.from_payload(config_doc["config"])
    dataset = config_doc.get("dataset", {})
    roles = config_doc.get("roles", {})
    provenance = _read_json(directory / "provenance.json") or {}
    data = provenance.get("data") or {}
    protocol_entry = provenance.get("protocol") or {}
    metrics = _read_json(directory / "validation" / "metrics.json")
    best = (metrics or {}).get("best") if isinstance(metrics, dict) else None
    state = str(status_doc.get("state", "unknown"))
    run_id = str(config_doc.get("run_id") or directory.name)
    if state not in {"completed", "paused", "failed", "incomplete"}:
        raise SelectionError(
            f"candidate {directory} has unexpected status {state!r}"
        )
    if state != "completed" or best is None:
        return Candidate(
            learning_rate=float(config.learning_rate),
            run_id=run_id,
            run_dir=str(directory.resolve()),
            status="failed" if state == "failed" else "incomplete",
            validation_mse=None,
            validation_mae=None,
            selected_epoch=None,
            seed=int(config.seed),
            model=config.model,
            dataset=str(dataset.get("name", "")),
            mode=str(dataset.get("mode", "")),
            purpose=str(config_doc.get("purpose", "")),
            config=config.to_payload(),
            roles=dict(roles),
            condition_id=(config_doc.get("condition") or {}).get("condition_id"),
            data_sha256=data.get("source_sha256"),
            keys_sha256=data.get("node_keys_sha256"),
            protocol_sha256=protocol_entry.get("sha256"),
            run_sha256=None,
            message=str(status_doc.get("detail") or "run did not complete"),
            protocol_controls_complete=(config_doc.get("protocol_controls") or {}).get("complete") is True,
        )
    return Candidate(
        learning_rate=float(config.learning_rate),
        run_id=run_id,
        run_dir=str(directory.resolve()),
        status="complete",
        protocol_controls_complete=(config_doc.get("protocol_controls") or {}).get("complete") is True,
        validation_mse=float(best["MSE"]),
        validation_mae=float(best["MAE"]),
        selected_epoch=int(best.get("epoch", 0)),
        seed=int(config.seed),
        model=config.model,
        dataset=str(dataset.get("name", "")),
        mode=str(dataset.get("mode", "")),
        purpose=str(config_doc.get("purpose", "")),
        config=config.to_payload(),
        roles=dict(roles),
        condition_id=(config_doc.get("condition") or {}).get("condition_id"),
        data_sha256=data.get("source_sha256"),
        keys_sha256=data.get("node_keys_sha256"),
        protocol_sha256=protocol_entry.get("sha256"),
        run_sha256=(provenance.get("source") or {}).get("commit"),
    )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SelectionError(message)


def validate_candidates(
    candidates: Sequence[Candidate], *, purpose: str
) -> None:
    """Reject candidates that cannot be compared under one frozen condition."""
    resources.check_stage_budget()
    _require(len(candidates) == 2, "selection needs exactly two candidate runs")
    rates = sorted(float(candidate.learning_rate) for candidate in candidates)
    _require(
        rates == sorted(float(rate) for rate in protocol.LR_CANDIDATES),
        f"candidates must cover exactly {list(protocol.LR_CANDIDATES)}, got {rates}",
    )
    first = candidates[0]
    for candidate in candidates:
        resources.check_stage_budget()
        _require(
            candidate.seed == 0,
            "learning-rate selection must use the screening seed 0; candidate "
            f"{candidate.run_id} uses seed {candidate.seed}",
        )
        _require(
            candidate.roles.get("candidate_role") == "screening",
            f"candidate {candidate.run_id} is not a screening candidate",
        )
        _require(
            candidate.roles.get("repeat_role") == "a",
            "repetition b never chooses a configuration; candidate "
            f"{candidate.run_id} is role b",
        )
        _require(
            candidate.purpose == purpose,
            f"candidate {candidate.run_id} purpose {candidate.purpose!r} does not "
            f"match the block purpose {purpose!r}",
        )
        _require(
            candidate.model == first.model,
            "candidates must share one encoder; "
            f"{candidate.run_id} is {candidate.model}, expected {first.model}",
        )
        _require(
            candidate.dataset == first.dataset and candidate.mode == first.mode,
            "candidates must share one dataset/mode",
        )
        _require(
            candidate.data_sha256 == first.data_sha256
            and candidate.keys_sha256 == first.keys_sha256,
            "candidates must share the same observed data contents and node keys",
        )
        _require(
            candidate.protocol_sha256 == first.protocol_sha256,
            "candidates must share the same protocol content identity",
        )
        _require(
            candidate.config.get("epochs") == first.config.get("epochs")
            and candidate.config.get("hidden_size") == first.config.get("hidden_size")
            and candidate.config.get("layers") == first.config.get("layers")
            and candidate.config.get("node_chunk") == first.config.get("node_chunk")
            and candidate.config.get("grad_clip") == first.config.get("grad_clip"),
            "candidates differ in effective configuration beyond the learning rate",
        )
        _require(
            candidate.condition_id is not None,
            f"candidate {candidate.run_id} has no condition identity",
        )
    _require(
        candidates[0].condition_id != candidates[1].condition_id,
        "candidate condition identities collide; they must differ by learning rate",
    )
    if purpose == "formal":
        for candidate in candidates:
            resources.check_stage_budget()
            _require(
                candidate.status == "complete",
                f"formal selection requires complete candidates; {candidate.run_id} "
                f"is {candidate.status}",
            )
            _require(
                protocol.FitConfig.from_payload(candidate.config).complete_protocol
                and candidate.protocol_controls_complete,
                f"formal selection requires complete protocol controls; "
                f"{candidate.run_id} is a development override",
            )


def choose(candidates: Sequence[Candidate]) -> Dict[str, Any]:
    """Return the frozen winner and per-candidate decision evidence."""
    ordered = sorted(candidates, key=lambda item: float(item.learning_rate))
    complete = [candidate for candidate in ordered if candidate.status == "complete"]
    table: List[Dict[str, Any]] = []
    for candidate in ordered:
        resources.check_stage_budget()
        table.append(
            {
                "learning_rate": float(candidate.learning_rate),
                "run_id": candidate.run_id,
                "validation_MSE": candidate.validation_mse,
                "status": candidate.status,
                "message": candidate.message,
            }
        )
    if not complete:
        return {
            "status": "incomplete",
            "winner": None,
            "tie": False,
            "candidates": table,
            "reason": "no completed seed-0 candidate trajectory",
        }
    best = min(
        complete,
        key=lambda candidate: (float(candidate.validation_mse), float(candidate.learning_rate)),
    )
    tied = [
        candidate
        for candidate in complete
        if float(candidate.validation_mse) == float(best.validation_mse)
    ]
    eliminated = [
        {
            "learning_rate": float(candidate.learning_rate),
            "run_id": candidate.run_id,
            "reason": (
                f"higher validation MSE {candidate.validation_mse:.6g} than "
                f"{best.validation_mse:.6g}"
            ),
        }
        for candidate in complete
        if candidate is not best
    ]
    for candidate in ordered:
        resources.check_stage_budget()
        if candidate.status != "complete":
            eliminated.append(
                {
                    "learning_rate": float(candidate.learning_rate),
                    "run_id": candidate.run_id,
                    "reason": f"candidate status {candidate.status}: {candidate.message}",
                }
            )
    status = "frozen" if all(c.status == "complete" for c in ordered) else "incomplete"
    return {
        "status": status,
        "winner": {
            "learning_rate": float(best.learning_rate),
            "run_id": best.run_id,
            "run_dir": best.run_dir,
            "validation_MSE": best.validation_mse,
            "validation_MAE": best.validation_mae,
            "selected_epoch": best.selected_epoch,
            "selection_metric": "best validation original-unit MSE",
            "reason": (
                "exact tie resolved to the smaller learning rate"
                if len(tied) > 1
                else "lowest best-validation original-unit MSE"
            ),
        },
        "tie": len(tied) > 1,
        "tied_learning_rates": sorted(float(c.learning_rate) for c in tied),
        "candidates": table,
        "eliminated": eliminated,
        "reason": None,
    }


def build_selection(
    candidates: Sequence[Candidate],
    *,
    block_id: str,
    purpose: str,
    model: str,
    dataset: str,
    mode: str,
) -> Dict[str, Any]:
    resources.check_stage_budget()
    validate_candidates(candidates, purpose=purpose)
    decision = choose(candidates)
    winner = decision["winner"]
    winner_as_a = None
    if winner is not None:
        winner_candidate = next(
            candidate for candidate in candidates if candidate.run_id == winner["run_id"]
        )
        winner_as_a = {
            "run_id": winner_candidate.run_id,
            "run_dir": winner_candidate.run_dir,
            "repeat_role": "a",
            "condition_id": winner_candidate.condition_id,
            "note": (
                "the winning seed-0 screening trajectory is reused as repetition a "
                "by link; it is not refitted"
            ),
        }
    for candidate in candidates:
        resources.check_stage_budget()
        protocol.FitConfig.from_payload(candidate.config)
    payload = {
        "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
        "scientific_version": protocol.SCIENTIFIC_VERSION,
        "kind": "selection",
        "block_id": block_id,
        "purpose": purpose,
        "model": model,
        "dataset": dataset,
        "mode": mode,
        "seed": 0,
        "learning_rate_candidates": list(protocol.LR_CANDIDATES),
        "selection_metric": "best validation original-unit MSE",
        "tie_break": "smaller learning rate on an exact tie",
        "candidates": [candidate.payload() for candidate in candidates],
        "winner": winner,
        "winner_as_a": winner_as_a,
        "tie": decision["tie"],
        "tied_learning_rates": decision.get("tied_learning_rates"),
        "eliminated": decision["eliminated"],
        "status": decision["status"],
        "reason": decision["reason"],
        "test_scores_used": False,
        "b_used_for_selection": False,
        "automatic_matrix_scheduling": False,
        "frozen": decision["status"] == "frozen",
    }
    payload["selection_sha256"] = protocol.content_sha256(
        {key: value for key, value in payload.items() if key != "selection_sha256"}
    )
    return payload


def load_selection(path: Path) -> Dict[str, Any]:
    resources.check_stage_budget()
    payload = _read_json(Path(path) / "selection.json" if Path(path).is_dir() else path)
    if not isinstance(payload, dict):
        raise SelectionError(f"selection record not found at {path}")
    if payload.get("kind") != "selection":
        raise SelectionError(f"{path} is not a selection record")
    return payload


def assert_frozen(selection: Mapping[str, Any]) -> None:
    if selection.get("status") != "frozen" or not selection.get("frozen"):
        raise SelectionError(
            "selection is not frozen (status "
            f"{selection.get('status')!r}); formal reporting requires a frozen "
            "selection of two complete seed-0 candidates"
        )
