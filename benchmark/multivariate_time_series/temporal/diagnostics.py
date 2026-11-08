"""Saved-evidence learning diagnostics implementing P02 section 5 verbatim.

The gates are computed only from evidence a completed trajectory already saved:
the per-epoch validation history, the fixed-parameter initialization/best scores,
the validation predictions, the fit-time naive baselines and the reported
coverage identities.  A test outcome can never repair a failed validation gate;
missing evidence stays ``incomplete`` and never becomes a pass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

from benchmark.nograph_baseline import metrics as p01_metrics

from . import protocol, resources

PASS = "pass"
FAIL = "fail"
INCOMPLETE = "incomplete"


class DiagnosticsError(protocol.ProtocolError):
    """Raised when diagnostics inputs are malformed beyond repair."""


def _read_json(path: Path) -> Any:
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_array(path: Path) -> Optional[np.ndarray]:
    path = Path(path)
    if not path.exists():
        return None
    return np.load(path, allow_pickle=False)


def evidence_sha256(directory: Path) -> str:
    paths = ("config.json", "provenance.json", "status.json", "history.json", "scores.json",
             "validation/metrics.json", "validation/prediction.npy", "validation/gold.npy",
             "weights/best.pt", "baselines.json", "fit-diagnostics.json")
    return protocol.content_sha256({name: protocol.sha256_file(Path(directory) / name)
                                   if (Path(directory) / name).is_file() else None
                                   for name in paths})


def load_run_evidence(run_dir: Path) -> Dict[str, Any]:
    """Load one completed (or failed) run's saved diagnostics evidence."""
    directory = Path(run_dir)
    config_doc = _read_json(directory / "config.json")
    if not isinstance(config_doc, dict):
        raise DiagnosticsError(
            f"{directory} is not a format-v2 run: config.json is missing"
        )
    status_doc = _read_json(directory / "status.json") or {}
    config = protocol.FitConfig.from_payload(config_doc["config"])
    provenance = _read_json(directory / "provenance.json") or {}
    data = provenance.get("data") or {}
    return {
        "evidence_sha256": evidence_sha256(directory),
        "run_id": config_doc.get("run_id", directory.name),
        "run_dir": str(directory.resolve()),
        "state": str(status_doc.get("state", "unknown")),
        "purpose": config_doc.get("purpose"),
        "config": config,
        "config_payload": config.to_payload(),
        "protocol_controls": config_doc.get("protocol_controls") or {},
        "roles": config_doc.get("roles") or {},
        "dataset": (config_doc.get("dataset") or {}).get("name"),
        "mode": (config_doc.get("dataset") or {}).get("mode"),
        "condition_id": (config_doc.get("condition") or {}).get("condition_id"),
        "data_sha256": data.get("source_sha256"),
        "keys_sha256": data.get("node_keys_sha256"),
        "protocol_sha256": (provenance.get("protocol") or {}).get("sha256"),
        "environment": {field: (provenance.get("environment") or {}).get(field)
                        for field in ("python_version_info", "platform", "machine", "device", "threads",
                                      "packages", "thread_environment", "determinism")},
        "source": {name: entry.get("sha256") for name, entry in
                   ((provenance.get("source") or {}).get("files") or {}).items()},
        "split": config_doc.get("split"),
        "history": _read_json(directory / "history.json"),
        "scores": _read_json(directory / "scores.json"),
        "validation_metrics": _read_json(directory / "validation" / "metrics.json"),
        "validation_prediction": _load_array(
            directory / "validation" / "prediction.npy"
        ),
        "validation_gold": _load_array(directory / "validation" / "gold.npy"),
        "baselines": _read_json(directory / "baselines.json"),
        "fit_diagnostics": _read_json(directory / "fit-diagnostics.json"),
        "masks_present": (directory / "masks.npz").exists(),
    }


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and np.isfinite(float(value))


def _gate_result(
    name: str,
    *,
    status: str,
    threshold: Any,
    per_seed: Sequence[Mapping[str, Any]],
    reasons: Sequence[str] = (),
    required_seeds: int = protocol.MIN_PASSING_SEEDS,
    evidence: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    passed = [row["seed"] for row in per_seed if row["status"] == PASS]
    failed = [row["seed"] for row in per_seed if row["status"] == FAIL]
    incomplete = [row["seed"] for row in per_seed if row["status"] == INCOMPLETE]
    payload: Dict[str, Any] = {
        "name": name,
        "status": status,
        "threshold": threshold,
        "required_passing_seeds": required_seeds,
        "passing_seeds": passed,
        "failing_seeds": failed,
        "incomplete_seeds": incomplete,
        "per_seed": list(per_seed),
        "reasons": list(reasons),
    }
    if evidence is not None:
        payload["evidence"] = dict(evidence)
    return payload


def _aggregate_status(
    per_seed: Sequence[Mapping[str, Any]], *, required_seeds: int
) -> str:
    if required_seeds == len(per_seed) and any(row["status"] == FAIL for row in per_seed):
        return FAIL
    if any(row["status"] == INCOMPLETE for row in per_seed):
        return INCOMPLETE
    passed = sum(1 for row in per_seed if row["status"] == PASS)
    return PASS if passed >= required_seeds else FAIL


def gate_completeness(
    a_runs: Mapping[int, Mapping[str, Any]],
    b_runs: Mapping[int, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Gate 1: complete, finite trajectories with protocol controls and identity."""
    rows: List[Dict[str, Any]] = []
    reasons: List[str] = []
    for seed, role, evidence in (
        (seed, role, runs.get(seed)) for seed in protocol.SEEDS
        for role, runs in (("a", a_runs), ("b", b_runs))
    ):
        if evidence is None:
            rows.append({"seed": seed, "repeat_role": role, "status": INCOMPLETE,
                         "reason": f"no {role}-run"})
            reasons.append(f"seed {seed}: repetition {role} evidence is missing")
            continue
        problems: List[str] = []
        incomplete: List[str] = []
        if evidence["state"] != "completed":
            incomplete.append(f"run state is {evidence['state']!r}")
        controls = evidence.get("protocol_controls") or {}
        if controls.get("complete") is not True or not evidence["config"].complete_protocol:
            incomplete.append(
                "development override, not a complete protocol trajectory "
                f"({controls.get('deviations')})"
            )
        history = evidence.get("history")
        records = (history or {}).get("epochs") if isinstance(history, dict) else None
        if not records:
            incomplete.append("per-epoch validation history is missing")
        else:
            if len(records) != protocol.EPOCHS:
                incomplete.append(
                    f"history has {len(records)} epochs, protocol requires "
                    f"{protocol.EPOCHS}"
                )
            epochs = [int(record.get("epoch", -1)) for record in records]
            if epochs != list(range(1, len(records) + 1)):
                problems.append("history epochs are not the ordered 1..N sequence")
            for record in records:
                for key in (
                    "validation_MSE",
                    "validation_MAE",
                    "online_train_loss_mixed_parameters",
                    "pre_clip_norm_max",
                    "wall_seconds",
                ):
                    if not _finite(record.get(key)):
                        problems.append(
                            f"epoch {record.get('epoch')} has nonfinite {key}"
                        )
                        break
        scores = evidence.get("scores") or {}
        for name in ("init", "10", "50", "100", "best"):
            block = scores.get(name)
            if not isinstance(block, dict):
                incomplete.append(f"missing fixed-parameter {name} score block")
                continue
            for key in ("MSE", "MAE"):
                if not _finite((block.get("train") or {}).get(key)):
                    problems.append(f"{name} train {key} is nonfinite or missing")
                if not _finite((block.get("validation") or {}).get(key)):
                    problems.append(f"{name} validation {key} is nonfinite or missing")
        reproduction = (scores.get("best") or {}).get("reproduction") or {}
        if not reproduction:
            incomplete.append("best-checkpoint reproduction evidence is missing")
        elif reproduction.get("status") != PASS:
            problems.append(
                "restored best checkpoint did not reproduce its saved validation "
                f"metrics: {reproduction.get('absolute_differences')}"
            )
        prediction = evidence.get("validation_prediction")
        gold = evidence.get("validation_gold")
        if prediction is None or gold is None:
            incomplete.append("saved validation predictions or labels are missing")
        elif not (np.isfinite(prediction).all() and np.isfinite(gold).all()):
            problems.append("saved validation arrays contain nonfinite values")
        row = {
            "seed": seed,
            "run_id": evidence["run_id"],
            "repeat_role": role,
            "status": FAIL if problems else (INCOMPLETE if incomplete else PASS),
            "problems": problems,
            "incomplete": incomplete,
        }
        rows.append(row)
        reasons.extend(f"seed {seed}: {item}" for item in incomplete)
        reasons.extend(f"seed {seed}: {item}" for item in problems)
    status = _aggregate_status(rows, required_seeds=2 * len(protocol.SEEDS))
    return _gate_result(
        "complete_and_finite_trajectories",
        status=status,
        threshold="every required a/b run covers all 100 epochs finitely",
        per_seed=rows,
        reasons=reasons,
        required_seeds=2 * len(protocol.SEEDS),
    )


def gate_learning(
    a_runs: Mapping[int, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Gate 2: fixed-parameter train MSE -10% and validation MSE -5% vs init."""
    rows: List[Dict[str, Any]] = []
    reasons: List[str] = []
    for seed in protocol.SEEDS:
        evidence = a_runs.get(seed)
        if evidence is None:
            rows.append({"seed": seed, "status": INCOMPLETE, "reason": "no a-run"})
            reasons.append(f"seed {seed}: repetition a evidence is missing")
            continue
        scores = evidence.get("scores") or {}
        init = scores.get("init") or {}
        best = scores.get("best") or {}
        values: Dict[str, Any] = {}
        problems: List[str] = []
        incomplete: List[str] = []
        for split in ("train", "validation"):
            initial = (init.get(split) or {}).get("MSE")
            selected = (best.get(split) or {}).get("MSE")
            if not _finite(initial) or not _finite(selected):
                incomplete.append(f"{split} MSE is missing for init or best")
                values[f"{split}_reduction"] = None
                continue
            initial_value = float(initial)
            if initial_value == 0.0:
                values[f"{split}_reduction"] = None
                incomplete.append(
                    f"{split} initialization MSE is zero; the relative reduction "
                    "is undefined and is reported as unavailable"
                )
                continue
            values[f"{split}_reduction"] = (initial_value - float(selected)) / initial_value
            values[f"{split}_initial_MSE"] = initial_value
            values[f"{split}_best_MSE"] = float(selected)
        train_ok = (
            values.get("train_reduction") is not None
            and values["train_reduction"] >= protocol.LEARNING_TRAIN_REDUCTION
        )
        val_ok = (
            values.get("validation_reduction") is not None
            and values["validation_reduction"] >= protocol.LEARNING_VAL_REDUCTION
        )
        if incomplete:
            status = INCOMPLETE
        else:
            status = PASS if (train_ok and val_ok) else FAIL
        if status == FAIL:
            reasons.append(
                f"seed {seed}: reductions train={values.get('train_reduction')} "
                f"validation={values.get('validation_reduction')} miss "
                f"{protocol.LEARNING_TRAIN_REDUCTION}/{protocol.LEARNING_VAL_REDUCTION}"
            )
        elif status == INCOMPLETE:
            reasons.extend(f"seed {seed}: {item}" for item in incomplete)
        rows.append(
            {
                "seed": seed,
                "run_id": evidence["run_id"],
                "status": status,
                "values": values,
                "problems": problems,
                "incomplete": incomplete,
            }
        )
    status = _aggregate_status(rows, required_seeds=protocol.MIN_PASSING_SEEDS)
    return _gate_result(
        "definite_learning",
        status=status,
        threshold={
            "train_MSE_reduction": protocol.LEARNING_TRAIN_REDUCTION,
            "validation_MSE_reduction": protocol.LEARNING_VAL_REDUCTION,
            "required_seeds": protocol.MIN_PASSING_SEEDS,
        },
        per_seed=rows,
        reasons=reasons,
    )


def gate_beyond_zero(
    a_runs: Mapping[int, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Gate 3: validation MAE improvement of at least 5% over the Zero baseline."""
    rows: List[Dict[str, Any]] = []
    reasons: List[str] = []
    for seed in protocol.SEEDS:
        evidence = a_runs.get(seed)
        if evidence is None:
            rows.append({"seed": seed, "status": INCOMPLETE, "reason": "no a-run"})
            reasons.append(f"seed {seed}: repetition a evidence is missing")
            continue
        baselines = (evidence.get("baselines") or {}).get("scores") or {}
        zero_mae = (baselines.get("Zero") or {}).get("MAE")
        validation = (evidence.get("validation_metrics") or {}).get("best") or {}
        model_mae = validation.get("MAE")
        if not _finite(zero_mae) or not _finite(model_mae):
            rows.append(
                {
                    "seed": seed,
                    "run_id": evidence["run_id"],
                    "status": INCOMPLETE,
                    "reason": "Zero baseline or model validation MAE is missing",
                }
            )
            reasons.append(f"seed {seed}: Zero baseline or validation MAE is missing")
            continue
        zero_mae = float(zero_mae)
        if zero_mae == 0.0:
            rows.append(
                {
                    "seed": seed,
                    "run_id": evidence["run_id"],
                    "status": INCOMPLETE,
                    "model_MAE": float(model_mae),
                    "zero_MAE": zero_mae,
                    "improvement": None,
                    "reason": (
                        "Zero validation MAE is zero; the all-zero target "
                        "diagnostic replaces the relative improvement and no gate "
                        "is claimed"
                    ),
                }
            )
            reasons.append(
                f"seed {seed}: Zero validation MAE is zero (all-zero target diagnostic)"
            )
            continue
        improvement = (zero_mae - float(model_mae)) / zero_mae
        status = PASS if improvement >= protocol.ZERO_MAE_IMPROVEMENT else FAIL
        if status == FAIL:
            reasons.append(
                f"seed {seed}: Zero improvement {improvement:.6g} is below "
                f"{protocol.ZERO_MAE_IMPROVEMENT}"
            )
        rows.append(
            {
                "seed": seed,
                "run_id": evidence["run_id"],
                "status": status,
                "model_MAE": float(model_mae),
                "zero_MAE": zero_mae,
                "improvement": improvement,
            }
        )
    status = _aggregate_status(rows, required_seeds=protocol.MIN_PASSING_SEEDS)
    return _gate_result(
        "beyond_zero_baseline",
        status=status,
        threshold={
            "validation_MAE_improvement_over_Zero": protocol.ZERO_MAE_IMPROVEMENT,
            "required_seeds": protocol.MIN_PASSING_SEEDS,
            "zero_denominator": "unavailable / all-zero diagnostic, never a pass",
        },
        per_seed=rows,
        reasons=reasons,
    )


def gate_budget_tail(
    a_runs: Mapping[int, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Gate 4: ``(b80-b100)/max(1e-12,b80) <= 1%`` for at least 2/3 seeds."""
    rows: List[Dict[str, Any]] = []
    reasons: List[str] = []
    for seed in protocol.SEEDS:
        evidence = a_runs.get(seed)
        if evidence is None:
            rows.append({"seed": seed, "status": INCOMPLETE, "reason": "no a-run"})
            reasons.append(f"seed {seed}: repetition a evidence is missing")
            continue
        history = (evidence.get("history") or {}).get("epochs") or []
        values = [
            float(record["validation_MSE"])
            for record in history
            if _finite(record.get("validation_MSE"))
        ]
        if len(values) < protocol.EPOCHS:
            rows.append(
                {
                    "seed": seed,
                    "run_id": evidence["run_id"],
                    "status": INCOMPLETE,
                    "epochs": len(values),
                    "reason": (
                        f"complete validation history needs {protocol.EPOCHS} "
                        f"epochs, found {len(values)}"
                    ),
                }
            )
            reasons.append(
                f"seed {seed}: budget-tail check needs a complete 100-epoch history"
            )
            continue
        b80 = min(values[: protocol.BUDGET_TAIL_EPOCH])
        b100 = min(values)
        if b80 == 0.0 and b100 == 0.0:
            relative = 0.0
            both_zero = True
        elif b80 == 0.0:
            both_zero = False
            rows.append(
                {
                    "seed": seed,
                    "run_id": evidence["run_id"],
                    "status": FAIL,
                    "b80": b80,
                    "b100": b100,
                    "relative": None,
                    "reason": (
                        "b80 is zero while b100 is positive; that ordering is "
                        "impossible for a minimum over an extended budget"
                    ),
                }
            )
            reasons.append(f"seed {seed}: inconsistent b80/b100 minima")
            continue
        else:
            relative = (b80 - b100) / max(protocol.BUDGET_TAIL_FLOOR, b80)
            both_zero = False
        status = PASS if relative <= protocol.BUDGET_TAIL_RELATIVE else FAIL
        if status == FAIL:
            reasons.append(
                f"seed {seed}: budget-tail relative change {relative:.6g} exceeds "
                f"{protocol.BUDGET_TAIL_RELATIVE}; the block remains budget-limited"
            )
        rows.append(
            {
                "seed": seed,
                "run_id": evidence["run_id"],
                "status": status,
                "b80": b80,
                "b100": b100,
                "both_zero": both_zero,
                "relative": relative,
            }
        )
    status = _aggregate_status(rows, required_seeds=protocol.MIN_PASSING_SEEDS)
    return _gate_result(
        "budget_tail_stability",
        status=status,
        threshold={
            "relative": protocol.BUDGET_TAIL_RELATIVE,
            "best_through_epoch": protocol.BUDGET_TAIL_EPOCH,
            "required_seeds": protocol.MIN_PASSING_SEEDS,
        },
        per_seed=rows,
        reasons=reasons,
    )


def _normalized_difference(left: float, right: float) -> float:
    return abs(float(left) - float(right)) / max(1.0, abs(float(left)), abs(float(right)))


def gate_repetition(
    a_runs: Mapping[int, Mapping[str, Any]],
    b_runs: Mapping[int, Mapping[str, Any]],
    *,
    model: Optional[str] = None,
    dataset: Optional[str] = None,
) -> Dict[str, Any]:
    """Gate 5: every required same-condition a/b pair agrees within 1e-6."""
    rows: List[Dict[str, Any]] = []
    reasons: List[str] = []
    for seed in protocol.SEEDS:
        a = a_runs.get(seed)
        b = b_runs.get(seed)
        if a is None or b is None:
            rows.append(
                {
                    "seed": seed,
                    "status": INCOMPLETE,
                    "reason": "both a and b repetitions are required",
                }
            )
            reasons.append(
                f"seed {seed}: a/b repetition evidence is incomplete (missing "
                f"{'a' if a is None else 'b'})"
            )
            continue
        problems: List[str] = []
        incomplete: List[str] = []
        for label, run in (("a", a), ("b", b)):
            if run.get("state") != "completed":
                incomplete.append(f"repetition {label} state is {run.get('state')!r}")
            if run["roles"].get("repeat_role") != label:
                problems.append(
                    f"repetition {label} declares repeat_role "
                    f"{run['roles'].get('repeat_role')!r}"
                )
            if int(run["config"].seed) != seed:
                problems.append(
                    f"repetition {label} seed is {run['config'].seed}, expected {seed}"
                )
            if model is not None and run["config"].model != model:
                problems.append(f"repetition {label} encoder is {run['config'].model}")
            if dataset is not None and run.get("dataset") != dataset:
                problems.append(f"repetition {label} dataset is {run.get('dataset')}")
        if a.get("condition_id") != b.get("condition_id"):
            problems.append(
                "a/b condition identities differ: "
                f"{a.get('condition_id')} vs {b.get('condition_id')}"
            )
        for field in ("protocol_sha256", "environment", "source", "split", "config_payload"):
            if a.get(field) != b.get(field):
                problems.append(f"a/b {field} differs")
        if a.get("data_sha256") != b.get("data_sha256"):
            problems.append("a/b demand contents differ; not the same condition")
        if a.get("keys_sha256") != b.get("keys_sha256"):
            problems.append("a/b canonical node keys differ")
        if (
            a["config"].to_payload().get("learning_rate")
            != b["config"].to_payload().get("learning_rate")
        ):
            problems.append("a/b selected learning rates differ")
        a_pred = a.get("validation_prediction")
        b_pred = b.get("validation_prediction")
        a_gold = a.get("validation_gold")
        b_gold = b.get("validation_gold")
        if a_pred is None or b_pred is None or a_gold is None or b_gold is None:
            incomplete.append("saved validation predictions or labels are missing")
        elif not all(np.isfinite(arr).all() for arr in (a_pred, b_pred, a_gold, b_gold)):
            problems.append("a/b validation arrays contain nonfinite values")
        elif a_gold.shape != b_gold.shape or not np.array_equal(a_gold, b_gold):
            problems.append("a/b validation labels differ")
        elif a_pred.shape != a_gold.shape or b_pred.shape != b_gold.shape:
            problems.append("validation predictions and labels have different shapes")
        elif a_pred.shape != b_pred.shape:
            problems.append(
                f"a/b validation prediction shapes differ: {a_pred.shape} vs {b_pred.shape}"
            )
        values: Dict[str, Any] = {}
        status = INCOMPLETE if incomplete else (FAIL if problems else PASS)
        if status == PASS:
            a_metrics = p01_metrics.error_metrics(a_pred, a_gold)
            b_metrics = p01_metrics.error_metrics(b_pred, b_gold)
            difference = _normalized_difference(a_metrics["MAE"], b_metrics["MAE"])
            max_absolute = float(np.max(np.abs(a_pred - b_pred)))
            values = {
                "a_MAE": float(a_metrics["MAE"]),
                "b_MAE": float(b_metrics["MAE"]),
                "normalized_MAE_difference": difference,
                "max_absolute_prediction_difference": max_absolute,
            }
            if difference > protocol.REPETITION_TOLERANCE:
                status = FAIL
                reasons.append(
                    f"seed {seed}: normalized a/b validation MAE difference "
                    f"{difference:.6g} exceeds {protocol.REPETITION_TOLERANCE}"
                )
        if status == FAIL:
            reasons.extend(f"seed {seed}: {item}" for item in problems)
        elif status == INCOMPLETE:
            reasons.extend(f"seed {seed}: {item}" for item in incomplete)
        rows.append(
            {
                "seed": seed,
                "status": status,
                "a_run_id": a["run_id"],
                "b_run_id": b["run_id"],
                "values": values,
                "problems": problems,
                "incomplete": incomplete,
            }
        )
    status = _aggregate_status(rows, required_seeds=len(protocol.SEEDS))
    return _gate_result(
        "same_condition_repetition",
        status=status,
        threshold={
            "normalized_MAE_difference": protocol.REPETITION_TOLERANCE,
            "required_pairs": list(protocol.SEEDS),
        },
        per_seed=rows,
        reasons=reasons,
        required_seeds=len(protocol.SEEDS),
    )


def _baseline_compatibility(
    a_runs: Mapping[int, Mapping[str, Any]],
    ridge: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    reference = a_runs.get(0) or next(iter(a_runs.values()), None)
    record: Dict[str, Any] = {"status": INCOMPLETE, "reasons": []}
    if reference is None:
        record["reasons"].append("no a-run evidence to anchor baseline identity")
        return record
    split_payload = protocol.split_payload()
    expected = {
        "dataset": reference.get("dataset"),
        "data_sha256": reference.get("data_sha256"),
        "keys_sha256": reference.get("keys_sha256"),
        "protocol_sha256": reference.get("protocol_sha256"),
        "split_validation_starts": list(split_payload["validation_starts"]),
        "split_validation_months": list(split_payload["validation_target_months"]),
    }
    record["expected"] = expected
    baselines = (reference.get("baselines") or {}).get("scores")
    if not isinstance(baselines, dict) or "Zero" not in baselines:
        record["reasons"].append("fit-time naive validation baselines are missing")
        return record
    record["naive_validation"] = baselines
    if ridge is None:
        record["reasons"].append(
            "no compatible Ridge validation evidence was supplied; neural vs Ridge "
            "compatibility remains incomplete"
        )
        record["ridge"] = None
        return record
    provided = dict(ridge) if isinstance(ridge, Mapping) else {}
    if "keys_sha256" not in provided and "node_keys_sha256" in provided:
        provided["keys_sha256"] = provided["node_keys_sha256"]
    mismatches: List[str] = []
    for field in ("dataset", "data_sha256", "keys_sha256"):
        if not provided.get(field) or provided.get(field) != expected[field]:
            mismatches.append(
                f"Ridge evidence {field}={provided.get(field)!r} does not match "
                f"{expected[field]!r}"
            )
    split = provided.get("split") or {}
    if list(split.get("validation_starts", [])) != expected[
        "split_validation_starts"
    ]:
        mismatches.append("Ridge evidence validation starts differ from the split")
    if list(split.get("validation_target_months", [])) != expected["split_validation_months"]:
        mismatches.append(
            "Ridge evidence validation target months differ from the protocol month "
            "identity"
        )
    selection = provided.get("selection") or {}
    if selection.get("selected_on") != "validation" or not _finite(selection.get("lambda")) or selection.get("lambda", -1) < 0:
        mismatches.append("Ridge evidence needs a finite nonnegative lambda selected on validation")
    preprocessing = provided.get("preprocessing") or {}
    if (preprocessing.get("definition") != "per-node standardization"
            or preprocessing.get("training_months") != list(protocol.train_observation_months())
            or preprocessing.get("ddof") != 0
            or preprocessing.get("constant_node_std") != 1):
        mismatches.append("Ridge evidence needs training-only 27-month per-node standardization, ddof=0, constant std=1")
    if (selection.get("metric") != "validation original-unit MSE"
            or selection.get("lambda") not in (1e-4, 1e-3, 1e-2, 1e-1, 1.0)
            or selection.get("tie_break") != "larger lambda"):
        mismatches.append("Ridge selection must use the inherited lambda grid, original-unit validation MSE and larger-lambda tie break")
    validation = provided.get("validation") or {}
    if not _finite(validation.get("MAE")) or not _finite(validation.get("MSE")):
        mismatches.append("Ridge evidence has no finite validation MAE/MSE")
    if mismatches:
        record["reasons"].extend(mismatches)
        record["ridge"] = {"provided": dict(provided), "mismatches": mismatches}
        return record
    compatibility = ["node", "month", "source-data", "split", "selection"]
    preprocessing = provided.get("preprocessing") or {}
    if preprocessing.get("definition"):
        compatibility.append("preprocessing")
    record["ridge"] = {
        "provided": {
            "dataset": provided.get("dataset"),
            "data_sha256": provided.get("data_sha256"),
            "keys_sha256": provided.get("keys_sha256"),
            "split": split,
            "selection": selection,
            "preprocessing": preprocessing,
            "validation": validation,
        },
        "mismatches": [],
        "compatibility": compatibility,
        "note": (
            "neural RMS and Ridge per-node standardization are different "
            "preprocessing conditions; compatibility is checked on node/month/"
            "source/split identity, not on a shared scaler"
        ),
    }
    record["status"] = PASS
    return record


def summarize_per_seed(
    selection: Mapping[str, Any],
    a_runs: Mapping[int, Mapping[str, Any]],
    b_runs: Mapping[int, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Per-seed metrics with mean/sample SD, retaining failed/incomplete seeds."""
    per_seed: List[Dict[str, Any]] = []
    complete_mse: List[float] = []
    complete_mae: List[float] = []
    failed: List[Dict[str, Any]] = []
    for seed in protocol.SEEDS:
        a = a_runs.get(seed)
        b = b_runs.get(seed)
        entry: Dict[str, Any] = {
            "seed": seed,
            "a_run_id": a["run_id"] if a else None,
            "b_run_id": b["run_id"] if b else None,
            "a_state": a["state"] if a else "missing",
            "b_state": b["state"] if b else "missing",
        }
        if a and a["state"] == "completed":
            best = (a.get("validation_metrics") or {}).get("best") or {}
            entry["validation_MSE"] = best.get("MSE")
            entry["validation_MAE"] = best.get("MAE")
            entry["selected_epoch"] = best.get("epoch")
            if _finite(best.get("MSE")) and _finite(best.get("MAE")):
                complete_mse.append(float(best["MSE"]))
                complete_mae.append(float(best["MAE"]))
            else:
                entry["status"] = INCOMPLETE
                failed.append({"seed": seed, "role": "a", "reason": "nonfinite metrics"})
        else:
            entry["status"] = INCOMPLETE if a else "missing"
            if a:
                failed.append(
                    {"seed": seed, "role": "a", "reason": f"state {a['state']}"}
                )
            else:
                failed.append({"seed": seed, "role": "a", "reason": "missing run"})
        if b and b["state"] != "completed":
            failed.append({"seed": seed, "role": "b", "reason": f"state {b['state']}"})
        elif not b:
            failed.append(
                {"seed": seed, "role": "b", "reason": "missing repetition b"}
            )
        per_seed.append(entry)
    winner = (selection or {}).get("winner") or {}
    return {
        "selection_status": (selection or {}).get("status"),
        "selected_learning_rate": winner.get("learning_rate"),
        "winner_run_id": winner.get("run_id"),
        "per_seed": per_seed,
        "complete_seed_count": len(complete_mse),
        "validation_MSE": protocol.summary_statistics(complete_mse),
        "validation_MAE": protocol.summary_statistics(complete_mae),
        "failed_or_incomplete": failed,
        "complete_comparison": not failed,
        "note": (
            "failed or incomplete seeds are retained here and never dropped from "
            "a claimed complete comparison"
        ),
    }


def gate_evidence_identity(selection, a_runs, b_runs):
    """Bind all trajectories to the frozen winner and effective execution identity."""
    problems, missing = [], []
    winner = selection.get("winner") or {}
    if selection.get("status") != "frozen" or selection.get("frozen") is not True:
        missing.append("selection is not frozen")
    expected_hash = protocol.content_sha256({k: v for k, v in selection.items() if k != "selection_sha256"})
    if selection.get("selection_sha256") != expected_hash:
        problems.append("selection content identity is invalid")
    reference = a_runs.get(0)
    link = selection.get("winner_as_a") or {}
    if not reference:
        missing.append("seed-0 winner-as-a evidence is missing")
    else:
        for item in (winner, link):
            if not item.get("run_dir") or Path(item["run_dir"]).resolve() != Path(reference["run_dir"]).resolve():
                problems.append("seed-0 a-run is not the frozen winner-as-a")
            if item.get("run_id") != reference.get("run_id"):
                problems.append("winner-as-a run identity differs")
        if link.get("condition_id") != reference.get("condition_id"):
            problems.append("winner-as-a condition differs")
    for seed in protocol.SEEDS:
        for role, runs in (("a", a_runs), ("b", b_runs)):
            run = runs.get(seed)
            if not run:
                continue  # completeness reports absent trajectories
            label = f"seed {seed} {role}"
            cfg = run["config"]
            if cfg.learning_rate != winner.get("learning_rate"):
                problems.append(f"{label}: learning rate differs from frozen selection")
            if cfg.model != selection.get("model") or run.get("dataset") != selection.get("dataset") or run.get("mode") != selection.get("mode"):
                problems.append(f"{label}: model/dataset/mode differs from selection")
            if cfg.seed != seed or (run.get("roles") or {}).get("repeat_role") != role:
                problems.append(f"{label}: seed/repetition identity differs")
            expected = protocol.condition_identity(cfg, dataset=run.get("dataset"), mode=run.get("mode"),
                        data_sha256=run.get("data_sha256"), keys_sha256=run.get("keys_sha256"),
                        protocol_sha256=run.get("protocol_sha256"))["condition_id"]
            if run.get("condition_id") != expected:
                problems.append(f"{label}: effective condition identity is invalid")
            for field in ("data_sha256", "keys_sha256", "protocol_sha256", "source", "environment", "split"):
                value = run.get(field)
                if not value or (isinstance(value, dict) and any(v is None for v in value.values())):
                    missing.append(f"{label}: {field} identity is missing")
                elif reference and value != reference.get(field):
                    problems.append(f"{label}: {field} differs across required trajectories")
            if run.get("split") != protocol.split_payload():
                problems.append(f"{label}: split differs from protocol")
            if reference:
                left, right = cfg.to_payload(), reference["config"].to_payload()
                left.pop("seed"); right.pop("seed")
                if left != right:
                    problems.append(f"{label}: effective configuration differs across seeds")
    return {"name": "frozen_evidence_identity", "status": FAIL if problems else (INCOMPLETE if missing else PASS),
            "reasons": problems + missing, "per_seed": [], "problems": problems, "incomplete": missing}


def build_diagnostics(
    *,
    selection: Mapping[str, Any],
    block_id: str,
    a_runs: Mapping[int, Mapping[str, Any]],
    b_runs: Mapping[int, Mapping[str, Any]],
    ridge: Optional[Mapping[str, Any]] = None,
    required_epochs: int = protocol.EPOCHS,
) -> Dict[str, Any]:
    """Run every section-5 gate and assemble the saved diagnostics record."""
    completeness = gate_completeness(a_runs, b_runs)
    learning = gate_learning(a_runs)
    beyond_zero = gate_beyond_zero(a_runs)
    budget_tail = gate_budget_tail(a_runs)
    repetition = gate_repetition(
        a_runs,
        b_runs,
        model=selection.get("model"),
        dataset=selection.get("dataset"),
    )
    gates = {
        "frozen_evidence_identity": gate_evidence_identity(selection, a_runs, b_runs),
        "complete_and_finite_trajectories": completeness,
        "definite_learning": learning,
        "beyond_zero_baseline": beyond_zero,
        "budget_tail_stability": budget_tail,
        "same_condition_repetition": repetition,
    }
    statuses = [gate["status"] for gate in gates.values()]
    reference = a_runs.get(0) or next(iter(a_runs.values()), None)
    fit_diagnostics = (reference or {}).get("fit_diagnostics")
    appendix = {
        "source_run_id": (reference or {}).get("run_id"),
        "quantiles": (fit_diagnostics or {}).get("quantiles"),
        "saturation": (fit_diagnostics or {}).get("saturation"),
        "prediction_scale": (fit_diagnostics or {}).get("prediction_scale"),
        "input_zeroing": (fit_diagnostics or {}).get("input_zeroing"),
        "note": (
            "diagnostic appendix only; never used to select a configuration or "
            "clip rule"
        ),
    }
    baselines = _baseline_compatibility(a_runs, ridge)
    summary = summarize_per_seed(selection, a_runs, b_runs)
    incomplete_reasons: List[str] = []
    for gate in gates.values():
        if gate["status"] == INCOMPLETE:
            incomplete_reasons.extend(gate.get("reasons", []))
    if baselines.get("status") != PASS:
        incomplete_reasons.extend(baselines.get("reasons", []))
    if all(status == PASS for status in statuses) and baselines.get("status") == PASS:
        status = PASS
    elif any(status == FAIL for status in statuses):
        status = FAIL
    else:
        status = INCOMPLETE
    payload = {
        "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
        "scientific_version": protocol.SCIENTIFIC_VERSION,
        "kind": "diagnostics",
        "block_id": block_id,
        "status": status,
        "learning_ready": status == PASS,
        "selection_sha256": (selection or {}).get("selection_sha256"),
        "gates": gates,
        "summary": summary,
        "appendix": appendix,
        "baselines": baselines,
        "inputs": {
            "a_runs": {
                str(seed): {
                    "run_id": run["run_id"],
                    "run_dir": run["run_dir"],
                    "state": run["state"],
                    "condition_id": run.get("condition_id"),
                    "config": run["config"].to_payload(),
                    "evidence_sha256": run.get("evidence_sha256"),
                    "validation": (run.get("validation_metrics") or {}).get("best"),
                }
                for seed, run in a_runs.items()
            },
            "b_runs": {
                str(seed): {
                    "run_id": run["run_id"],
                    "run_dir": run["run_dir"],
                    "state": run["state"],
                    "condition_id": run.get("condition_id"),
                    "config": run["config"].to_payload(),
                    "evidence_sha256": run.get("evidence_sha256"),
                }
                for seed, run in b_runs.items()
            },
        },
        "incomplete_reasons": incomplete_reasons,
        "test_scores_used": False,
        "declares_research_acceptance": False,
        "required_epochs": required_epochs,
        "note": (
            "learning_ready states only that the frozen section-5 software gates "
            "all evaluated true; it is not research acceptance, graph benefit or a "
            "claim of full convergence"
        ),
    }
    payload["diagnostics_sha256"] = protocol.content_sha256(
        {key: value for key, value in payload.items() if key != "diagnostics_sha256"}
    )
    return payload


@resources.account_stage
def run_diagnose(request: Mapping[str, Any]) -> Dict[str, Any]:
    """Read saved evidence and publish exactly one isolated exclusive report."""
    from . import artifacts, checks, selection as saved_selection

    block = Path(request["block_dir"])
    destination = Path(request["report_path"])
    consumed = [("block", block, "dir")]
    for role in ("a_runs", "b_runs"):
        consumed.extend((f"{role}/{seed}", path, "dir")
                        for seed, path in (request.get(role) or {}).items())
    if request.get("ridge_path"):
        consumed.append(("Ridge", request["ridge_path"], "file"))
    checks.reject_destination(destination, consumed)
    artifacts.check_development_namespace(str(request.get("purpose", "development")), destination)
    inputs = {"block_dir": str(block.resolve()),
              "a_runs": dict(request.get("a_runs") or {}),
              "b_runs": dict(request.get("b_runs") or {}),
              "ridge_path": request.get("ridge_path")}
    tolerances = {"repetition_normalized_mae": protocol.REPETITION_TOLERANCE,
                  "learning_train_reduction": protocol.LEARNING_TRAIN_REDUCTION,
                  "learning_validation_reduction": protocol.LEARNING_VAL_REDUCTION,
                  "zero_mae_improvement": protocol.ZERO_MAE_IMPROVEMENT,
                  "budget_tail_relative": protocol.BUDGET_TAIL_RELATIVE}
    try:
        selection = saved_selection.load_selection(block)
        # Selection may link a winner omitted from the explicit run arguments.
        winner_path = (selection.get("winner") or {}).get("run_dir")
        if winner_path:
            consumed.append(("winner", winner_path, "dir"))
            checks.reject_destination(destination, consumed)
        a_runs = {int(seed): load_run_evidence(Path(path))
                  for seed, path in (request.get("a_runs") or {}).items()}
        b_runs = {int(seed): load_run_evidence(Path(path))
                  for seed, path in (request.get("b_runs") or {}).items()}
        ridge = checks.read_json(Path(request["ridge_path"])) if request.get("ridge_path") else None
        result = build_diagnostics(selection=selection, block_id=block.name,
                                   a_runs=a_runs, b_runs=b_runs, ridge=ridge)
        status = "failed" if result["status"] == FAIL else result["status"]
        payload = checks.envelope("diagnose", argv=request.get("argv") or [],
                                  inputs=inputs, tolerances=tolerances, status=status,
                                  result=result, errors=result["incomplete_reasons"][:10])
    except Exception as exc:
        payload = checks.failure_envelope("diagnose", argv=request.get("argv") or [],
                                          inputs=inputs, tolerances=tolerances, exc=exc)
    checks.reject_destination(destination, consumed)
    written = checks.finish(destination, payload)
    return {**written, "learning_ready": payload["result"].get("learning_ready", False)}
