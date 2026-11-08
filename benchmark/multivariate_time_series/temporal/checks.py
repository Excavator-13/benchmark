"""Saved-only recompute and same-condition compare checks.

Neither check fits a model, imports torch, reads demand or graph data, or alters
its input runs.  Each writes exactly one exclusive compact JSON report carrying
the consumed-input identities, checker source identity, tolerances, decisive
differences and a pass/fail/incomplete status.  Same-seed comparison validates
the scientific condition *before* looking at numbers, so identical predictions
can never hide a seed, data, protocol or environment mismatch.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from benchmark.nograph_baseline import artifacts as nb_artifacts
from benchmark.nograph_baseline import metrics as p01_metrics
from benchmark.nograph_baseline import protocol as p01
from benchmark.nograph_baseline.data import iso_now

from . import protocol, resources

sha256_file = protocol.sha256_file

DIAGNOSTIC_TOLERANCE = 1e-12
NUMERIC_RELATIVE_TOLERANCE = 1e-9
ENVIRONMENT_FIELDS = (
    "python_version_info",
    "platform",
    "machine",
    "device",
    "threads",
    "packages",
    "thread_environment",
    "determinism",
)


class CheckError(RuntimeError):
    """Raised when a saved-evidence check cannot be completed."""


# -- report publication ----------------------------------------------------
def reject_destination(destination: Path, inputs: Sequence[Any]) -> None:
    """Refuse an existing report path or any path inside a consumed input."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise CheckError(
            "report destination already exists and will not be replaced: "
            f"{destination}"
        )
    resolved = destination.resolve()
    for label, raw, kind in inputs:
        if raw is None:
            continue
        resolved_input = Path(raw).resolve()
        if resolved == resolved_input:
            raise CheckError(f"report path {destination} resolves to the {label} input")
        if kind == "dir" and resolved_input in resolved.parents:
            raise CheckError(
                f"report path {destination} resolves inside the {label} input {raw}"
            )


def write_report(destination: Path, envelope: Mapping[str, Any]) -> Path:
    """Publish one complete JSON report with exclusive creation."""
    destination = Path(destination)
    reject_destination(destination, [])
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(envelope), indent=2, sort_keys=True, ensure_ascii=False)
    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.unlink(destination)
        except OSError:  # pragma: no cover - best-effort cleanup
            pass
        raise
    return destination


def checker_identity() -> Dict[str, Any]:
    """Return the honest source identity embedded in every check report."""
    from . import artifacts

    root = artifacts.repo_root()
    commit, commit_error = nb_artifacts.git_command(root, ["rev-parse", "HEAD"])
    status_text, status_error = nb_artifacts.git_command(
        root, ["status", "--porcelain"]
    )
    files: Dict[str, str] = {}
    for relative in artifacts.runtime_source_paths(root):
        path = root / relative
        if path.is_file():
            files[relative] = sha256_file(path)
    errors = {
        key: value
        for key, value in {
            "commit": commit_error,
            "status": status_error,
        }.items()
        if value
    }
    return {
        "module": "benchmark.multivariate_time_series.effective_temporal_training",
        "commit": commit.strip() if commit else None,
        "identity_available": commit is not None,
        "whole_repository_dirty": (
            bool(status_text.strip()) if status_text is not None else None
        ),
        "files": files,
        "protocol_sha256": protocol.protocol_content_sha256(),
        "errors": errors,
    }


def envelope(
    kind: str,
    *,
    argv: Sequence[str],
    inputs: Mapping[str, Any],
    tolerances: Mapping[str, Any],
    status: str,
    result: Mapping[str, Any],
    errors: Sequence[Any],
) -> Dict[str, Any]:
    return {
        "version": protocol.REPORT_VERSION,
        "kind": kind,
        "created": iso_now(),
        "status": status,
        "command": {"argv": [str(item) for item in argv], "cwd": str(Path.cwd())},
        "checker": checker_identity(),
        "inputs": dict(inputs),
        "tolerances": dict(tolerances),
        "result": dict(result),
        "errors": list(errors),
    }


def failure_envelope(
    kind: str,
    *,
    argv: Sequence[str],
    inputs: Mapping[str, Any],
    tolerances: Mapping[str, Any],
    exc: BaseException,
) -> Dict[str, Any]:
    error = {"type": type(exc).__name__, "message": str(exc)}
    return envelope(
        kind,
        argv=argv,
        inputs=inputs,
        tolerances=tolerances,
        status="failed",
        result={"status": "failed", "errors": [error]},
        errors=[error],
    )


def finish(destination: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    resources.check_stage_budget()
    payload["accounting"] = resources.stage_accounting()
    write_report(destination, payload)
    resources.register_stage_report(destination)
    return {
        "report_path": str(destination),
        "status": payload["status"],
        "result": payload["result"],
    }


# -- shared reading helpers ------------------------------------------------
def read_json(path: Path, *, required: bool = True) -> Any:
    resources.check_stage_budget()
    path = Path(path)
    if not path.exists():
        if required:
            raise CheckError(f"required artifact is missing: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_npy(path: Path, *, required: bool = True) -> Optional[np.ndarray]:
    resources.check_stage_budget()
    path = Path(path)
    if not path.exists():
        if required:
            raise CheckError(f"required numeric artifact is missing: {path}")
        return None
    return np.load(path, allow_pickle=False)


def load_npz(path: Path) -> Dict[str, np.ndarray]:
    resources.check_stage_budget()
    path = Path(path)
    if not path.exists():
        raise CheckError(f"required mask artifact is missing: {path}")
    with np.load(path, allow_pickle=False) as handle:
        return {name: np.asarray(handle[name]) for name in handle.files}


def run_config(run_dir: Path) -> Dict[str, Any]:
    payload = read_json(Path(run_dir) / "config.json")
    if not isinstance(payload, dict):
        raise CheckError(f"{run_dir}: config.json is not an object")
    if payload.get("artifact_format_version") != protocol.ARTIFACT_FORMAT_VERSION:
        raise CheckError(
            f"{run_dir}: artifact format "
            f"{payload.get('artifact_format_version')!r} is not "
            f"{protocol.ARTIFACT_FORMAT_VERSION}; legacy runs cannot be recomputed "
            "as this format"
        )
    return payload


def run_identity(run_dir: Path) -> Dict[str, Any]:
    """Return the scientific condition identity used before numeric comparison."""
    directory = Path(run_dir)
    config_doc = run_config(directory)
    provenance = read_json(directory / "provenance.json", required=False) or {}
    data = provenance.get("data") or {}
    environment = provenance.get("environment") or {}
    return {
        "run_id": config_doc.get("run_id", directory.name),
        "operation": config_doc.get("operation"),
        "purpose": config_doc.get("purpose"),
        "scientific_version": config_doc.get("scientific_version"),
        "dataset": (config_doc.get("dataset") or {}).get("name"),
        "mode": (config_doc.get("dataset") or {}).get("mode"),
        "key_columns": (config_doc.get("dataset") or {}).get("key_columns"),
        "nodes": (config_doc.get("dataset") or {}).get("nodes"),
        "config": config_doc.get("config"),
        "protocol_complete": (config_doc.get("protocol_controls") or {}).get(
            "complete"
        ),
        "roles": config_doc.get("roles"),
        "condition_id": (config_doc.get("condition") or {}).get("condition_id"),
        "data": {
            "source_path": data.get("source_path"),
            "source_sha256": data.get("source_sha256"),
            "node_keys_sha256": data.get("node_keys_sha256"),
        },
        "protocol": provenance.get("protocol") or {},
        "environment": {
            field: environment.get(field) for field in ENVIRONMENT_FIELDS
        },
        "split": config_doc.get("split"),
    }


# -- numeric comparison ----------------------------------------------------
def _numbers(payload: Any, prefix: str = "") -> Dict[str, float]:
    found: Dict[str, float] = {}
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            resources.check_stage_budget()
            found.update(_numbers(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            resources.check_stage_budget()
            found.update(_numbers(value, f"{prefix}[{index}]"))
    elif isinstance(payload, bool):
        return found
    elif isinstance(payload, (int, float)) and math.isfinite(float(payload)):
        found[prefix] = float(payload)
    return found


def compare_numbers(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    tolerance: float,
) -> Dict[str, Any]:
    """Compare numeric leaves and report decisive differences."""
    resources.check_stage_budget()
    left = _numbers(expected)
    right = _numbers(actual)
    differences: List[Dict[str, Any]] = []
    for key in sorted(set(left) | set(right)):
        resources.check_stage_budget()
        if key not in left or key not in right:
            differences.append(
                {
                    "path": key,
                    "reason": "missing on one side",
                    "expected": left.get(key),
                    "actual": right.get(key),
                }
            )
            continue
        a = left[key]
        b = right[key]
        difference = abs(a - b) / max(1.0, abs(a), abs(b))
        if difference > tolerance:
            differences.append(
                {
                    "path": key,
                    "expected": a,
                    "actual": b,
                    "normalized_difference": difference,
                }
            )
    return {
        "tolerance": tolerance,
        "numeric_paths": len(left),
        "differences": differences,
        "status": "pass" if not differences else "fail",
    }


def normalized_mae_difference(left: float, right: float) -> float:
    return abs(float(left) - float(right)) / max(1.0, abs(float(left)), abs(float(right)))


# -- recompute -------------------------------------------------------------
def _recompute_fit_metrics(directory: Path) -> Dict[str, Any]:
    resources.check_stage_budget()
    prediction = load_npy(directory / "validation" / "prediction.npy")
    gold = load_npy(directory / "validation" / "gold.npy")
    if prediction.shape != gold.shape:
        raise CheckError(
            f"validation prediction shape {prediction.shape} != gold {gold.shape}"
        )
    record = p01_metrics.error_metrics(prediction, gold)
    saved = read_json(directory / "validation" / "metrics.json")
    saved_best = saved.get("best", {}) if isinstance(saved, dict) else {}
    comparison = compare_numbers(
        {"best": {"MSE": saved_best.get("MSE"), "MAE": saved_best.get("MAE")}},
        {"best": {"MSE": record["MSE"], "MAE": record["MAE"]}},
        DIAGNOSTIC_TOLERANCE,
    )
    horizon = p01_metrics.horizon_metrics(prediction, gold)
    return {
        "validation": {
            "shape": list(prediction.shape),
            "elements": int(record["elements"]),
            "MAE": record["MAE"],
            "MSE": record["MSE"],
            "RMSE": record["RMSE"],
            "negative_prediction_ratio": record["negative_prediction_ratio"],
            "horizons": horizon,
            "starts": (read_json(directory / "splits.json", required=False) or {}).get(
                "validation_starts"
            ),
        },
        "comparison": comparison,
        "status": comparison["status"],
    }


def _recompute_report_metrics(directory: Path) -> Dict[str, Any]:
    resources.check_stage_budget()
    payload = read_json(directory / "report.json")
    saved = payload.get("metrics") or {}
    windows = read_json(directory / "test" / "windows.json")
    starts = [int(start) for start in windows["starts"]]
    if starts != list(p01.MAIN_SPLIT.evaluation_starts):
        raise CheckError("test windows do not cover all four protocol starts")
    prediction = load_npy(directory / "test" / "prediction.npy")
    gold = load_npy(directory / "test" / "gold.npy")
    keys = load_npy(directory / "keys.npy")
    masks = load_npz(directory / "masks.npz")
    activity = {
        name[len("activity_") :]: np.asarray(mask, dtype=bool)
        for name, mask in masks.items()
        if name.startswith("activity_")
    }
    constants = {
        name: np.asarray(masks[name], dtype=bool)
        for name in ("constant_train27", "nonconstant_train27")
        if name in masks
    }
    expected_shape = (len(starts), int(keys.shape[0]), p01.HORIZON)
    if prediction.shape != expected_shape or gold.shape != expected_shape:
        raise CheckError(
            f"test arrays must be {expected_shape}, got {prediction.shape} and "
            f"{gold.shape}"
        )
    overall = p01_metrics.error_metrics(prediction, gold)
    global_absolute = overall["absolute_error_sum"]
    global_squared = overall["squared_error_sum"]
    recomputed: Dict[str, Any] = dict(overall)
    recomputed["activity_groups"] = p01_metrics.masked_group_metrics(
        prediction,
        gold,
        activity,
        global_absolute=global_absolute,
        global_squared=global_squared,
    )
    recomputed["constant_groups"] = p01_metrics.masked_group_metrics(
        prediction,
        gold,
        constants,
        global_absolute=global_absolute,
        global_squared=global_squared,
    )
    recomputed["contexts"] = p01_metrics.masked_group_metrics(
        prediction,
        gold,
        p01_metrics.context_masks(keys[:, 0]),
        global_absolute=global_absolute,
        global_squared=global_squared,
    )
    if "has_nonself_neighbor" in masks:
        neighbors = p01_metrics.masked_group_metrics(
            prediction,
            gold,
            {
                "has_nonself_neighbor": np.asarray(
                    masks["has_nonself_neighbor"], dtype=bool
                ),
                "no_nonself_neighbor": np.asarray(
                    masks["no_nonself_neighbor"], dtype=bool
                ),
            },
            global_absolute=global_absolute,
            global_squared=global_squared,
        )
        neighbors["coverage_available"] = True
    else:
        neighbors = {
            "has_nonself_neighbor": {
                "status": "unavailable",
                "reason": (
                    "no context-qualified coverage evidence was supplied; missing "
                    "coverage is never converted into an all-isolated mask"
                ),
            },
            "no_nonself_neighbor": {
                "status": "unavailable",
                "reason": (
                    "no context-qualified coverage evidence was supplied; missing "
                    "coverage is never converted into an all-isolated mask"
                ),
            },
            "coverage_available": False,
        }
    recomputed["neighbor_groups"] = neighbors
    recomputed.update(
        p01_metrics.balanced_activity_mae(
            recomputed["activity_groups"], tuple(activity.keys())
        )
    )
    recomputed["windows"] = p01_metrics.window_metrics(prediction, gold, starts)
    recomputed["horizons"] = p01_metrics.horizon_metrics(prediction, gold)
    recomputed["target_month_multiplicities"] = (
        p01_metrics.target_month_multiplicities(starts)
    )
    recomputed["aggregation_note"] = payload.get("metrics", {}).get(
        "aggregation_note"
    )
    recomputed["sample_counts"] = {
        "windows": int(prediction.shape[0]),
        "nodes": int(keys.shape[0]),
        "horizon": int(prediction.shape[2]),
        "elements": int(prediction.size),
        "per_window_elements": int(keys.shape[0] * prediction.shape[2]),
    }
    recomputed["negative_prediction_ratio"] = float((prediction < 0).mean())
    comparison = compare_numbers(saved, recomputed, DIAGNOSTIC_TOLERANCE)
    clipped_saved = payload.get("clipped_nonnegative") or {}
    clipped_recomputed = p01_metrics.error_metrics(
        np.maximum(prediction, 0.0), gold
    )
    clipped_comparison = compare_numbers(
        {
            "MAE": clipped_saved.get("MAE"),
            "MSE": clipped_saved.get("MSE"),
            "RMSE": clipped_saved.get("RMSE"),
        },
        {
            "MAE": clipped_recomputed["MAE"],
            "MSE": clipped_recomputed["MSE"],
            "RMSE": clipped_recomputed["RMSE"],
        },
        DIAGNOSTIC_TOLERANCE,
    )
    comparison["clipped_nonnegative"] = clipped_comparison
    if clipped_comparison["status"] != "pass":
        comparison["status"] = "fail"
        comparison["differences"].extend(clipped_comparison["differences"])
    return {
        "test": {
            "overall": overall,
            "windows": recomputed["windows"],
            "horizons": recomputed["horizons"],
            "target_month_multiplicities": recomputed[
                "target_month_multiplicities"
            ],
            "activity_groups": recomputed["activity_groups"],
            "constant_groups": recomputed["constant_groups"],
            "contexts": recomputed["contexts"],
            "neighbor_groups": neighbors,
            "clipped_nonnegative": clipped_recomputed,
            "shape": list(prediction.shape),
            "elements": int(prediction.size),
        },
        "comparison": comparison,
        "status": comparison["status"],
    }


@resources.account_stage
def run_recompute(
    *,
    run_dir: Path,
    report_path: Path,
    argv: Sequence[str],
    tolerance: float = DIAGNOSTIC_TOLERANCE,
) -> Dict[str, Any]:
    """Recompute every saved metric without source data, fitting or torch."""
    directory = Path(run_dir)
    config_doc = run_config(directory)
    operation = config_doc.get("operation")
    inputs = {
        "run_dir": str(directory.resolve()),
        "operation": operation,
        "run_id": config_doc.get("run_id"),
        "arrays": {},
    }
    for relative in protocol.RECOMPUTE_ARRAYS:
        resources.check_stage_budget()
        path = directory / relative
        if path.is_file():
            inputs["arrays"][relative] = {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
    tolerances = {
        "diagnostic_relative": tolerance,
        "numeric_relative": NUMERIC_RELATIVE_TOLERANCE,
    }
    reject_destination(
        Path(report_path),
        [("run", directory, "dir")],
    )
    try:
        if operation in {"fit", "resume"}:
            result = _recompute_fit_metrics(directory)
        elif operation == "report":
            result = _recompute_report_metrics(directory)
        else:
            raise CheckError(
                f"{directory}: operation {operation!r} has no saved-only recompute"
            )
        result["inputs"] = inputs
        status = result["status"]
        payload = envelope(
            "recompute",
            argv=argv,
            inputs=inputs,
            tolerances=tolerances,
            status=status,
            result=result,
            errors=[] if status == "pass" else result["comparison"]["differences"][:10],
        )
    except BaseException as exc:
        payload = failure_envelope(
            "recompute", argv=argv, inputs=inputs, tolerances=tolerances, exc=exc
        )
    return finish(Path(report_path), payload)


# -- compare ---------------------------------------------------------------
def _identity_mismatches(left: Mapping[str, Any], right: Mapping[str, Any]) -> List[Dict[str, Any]]:
    mismatches: List[Dict[str, Any]] = []

    def record(field: str, a: Any, b: Any) -> None:
        if a != b:
            mismatches.append({"field": field, "a": a, "b": b})

    record("scientific_version", left.get("scientific_version"), right.get("scientific_version"))
    record("dataset", left.get("dataset"), right.get("dataset"))
    record("mode", left.get("mode"), right.get("mode"))
    record("key_columns", left.get("key_columns"), right.get("key_columns"))
    record("nodes", left.get("nodes"), right.get("nodes"))
    record("data.source_sha256", left["data"].get("source_sha256"), right["data"].get("source_sha256"))
    if left["data"].get("source_sha256") in (None, "in-memory") or right["data"].get(
        "source_sha256"
    ) in (None, "in-memory"):
        mismatches.append(
            {
                "field": "data.source_sha256",
                "a": left["data"].get("source_sha256"),
                "b": right["data"].get("source_sha256"),
                "reason": (
                    "a same-condition comparison requires the actual data source "
                    "identity, not an array placeholder"
                ),
            }
        )
    record("data.node_keys_sha256", left["data"].get("node_keys_sha256"), right["data"].get("node_keys_sha256"))
    record("protocol.sha256", (left.get("protocol") or {}).get("sha256"), (right.get("protocol") or {}).get("sha256"))
    record("split", left.get("split"), right.get("split"))
    left_config = left.get("config") or {}
    right_config = right.get("config") or {}
    for field in (
        "model",
        "seed",
        "learning_rate",
        "epochs",
        "hidden_size",
        "layers",
        "node_chunk",
        "grad_clip",
        "threads",
        "diagnostic_epochs",
    ):
        resources.check_stage_budget()
        record(f"config.{field}", left_config.get(field), right_config.get(field))
    record(
        "protocol_complete",
        left.get("protocol_complete"),
        right.get("protocol_complete"),
    )
    for field in ENVIRONMENT_FIELDS:
        resources.check_stage_budget()
        record(
            f"environment.{field}",
            (left.get("environment") or {}).get(field),
            (right.get("environment") or {}).get(field),
        )
    return mismatches


def _prediction_comparison(
    a: np.ndarray,
    b: np.ndarray,
    gold: np.ndarray,
    *,
    label: str,
    tolerance: float,
) -> Dict[str, Any]:
    resources.check_stage_budget()
    if a.shape != b.shape:
        return {
            "label": label,
            "status": "fail",
            "reason": f"shape mismatch {a.shape} vs {b.shape}",
        }
    left = p01_metrics.error_metrics(a, gold)
    right = p01_metrics.error_metrics(b, gold)
    difference = normalized_mae_difference(left["MAE"], right["MAE"])
    maximum = float(np.max(np.abs(np.asarray(a) - np.asarray(b)))) if a.size else 0.0
    return {
        "label": label,
        "MAE_a": left["MAE"],
        "MAE_b": right["MAE"],
        "normalized_MAE_difference": difference,
        "max_absolute_prediction_difference": maximum,
        "tolerance": tolerance,
        "status": "pass" if difference <= tolerance else "fail",
    }


@resources.account_stage
def run_compare(
    *,
    run_a: Path,
    run_b: Path,
    report_path: Path,
    argv: Sequence[str],
    tolerance: float = protocol.REPETITION_TOLERANCE,
) -> Dict[str, Any]:
    """Compare two same-condition runs, validating identity before numbers."""
    directory_a = Path(run_a)
    directory_b = Path(run_b)
    inputs = {
        "run_a": str(directory_a.resolve()),
        "run_b": str(directory_b.resolve()),
    }
    tolerances = {
        "normalized_MAE_difference": tolerance,
        "reproduction_bound": protocol.REPETITION_TOLERANCE,
    }
    reject_destination(
        Path(report_path),
        [("run A", directory_a, "dir"), ("run B", directory_b, "dir")],
    )
    try:
        identity_a = run_identity(directory_a)
        identity_b = run_identity(directory_b)
        inputs["identity_a"] = identity_a
        inputs["identity_b"] = identity_b
        mismatches = _identity_mismatches(identity_a, identity_b)
        result: Dict[str, Any] = {
            "identity_checked_first": True,
            "mismatches": mismatches,
            "comparisons": [],
        }
        if mismatches:
            result["status"] = "failed"
            result["reason"] = (
                "the runs do not describe the same scientific condition; numeric "
                "equality cannot substitute for matching identity"
            )
        else:
            a_validation = load_npy(directory_a / "validation" / "prediction.npy")
            b_validation = load_npy(directory_b / "validation" / "prediction.npy")
            a_gold = load_npy(directory_a / "validation" / "gold.npy")
            b_gold = load_npy(directory_b / "validation" / "gold.npy")
            result["comparisons"].append(
                _prediction_comparison(
                    a_validation,
                    b_validation,
                    a_gold,
                    label="validation",
                    tolerance=tolerance,
                )
            )
            if a_gold.shape != b_gold.shape or not np.array_equal(a_gold, b_gold):
                result["mismatches"].append(
                    {"field": "validation.gold", "reason": "labels differ"}
                )
            a_test = load_npy(directory_a / "test" / "prediction.npy", required=False)
            b_test = load_npy(directory_b / "test" / "prediction.npy", required=False)
            if a_test is not None and b_test is not None:
                a_test_gold = load_npy(directory_a / "test" / "gold.npy")
                result["comparisons"].append(
                    _prediction_comparison(
                        a_test,
                        b_test,
                        a_test_gold,
                        label="test",
                        tolerance=tolerance,
                    )
                )
            else:
                result["test_comparison"] = {
                    "status": "not_applicable",
                    "reason": (
                        "one or both runs have no final test report yet; test "
                        "repetition is checked after the explicit report stage"
                    ),
                }
            failed = [
                comparison
                for comparison in result["comparisons"]
                if comparison.get("status") != "pass"
            ]
            if result["mismatches"] or failed:
                result["status"] = "failed"
                if failed:
                    result["reason"] = (
                        "same-condition repetition bound exceeded: "
                        f"{[row['label'] for row in failed]}"
                    )
            else:
                result["status"] = "pass"
        payload = envelope(
            "compare",
            argv=argv,
            inputs=inputs,
            tolerances=tolerances,
            status=result["status"],
            result=result,
            errors=[] if result["status"] == "pass" else (
                result.get("mismatches") or result.get("comparisons")
            )[:10],
        )
    except BaseException as exc:
        payload = failure_envelope(
            "compare", argv=argv, inputs=inputs, tolerances=tolerances, exc=exc
        )
    return finish(Path(report_path), payload)
