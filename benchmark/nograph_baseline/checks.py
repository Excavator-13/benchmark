"""Saved-run analysis commands: recompute, compare and immutable v2 alignment.

None of these commands fits a model, reads source demand/graph data, or alters
its input runs.  Each reserves a fresh check-type run directory holding its
linked input hashes, command, report and terminal status.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from . import artifacts, metrics, protocol
from .data import sha256_file

#: Normalized tolerances used by saved-run checks.
CPU_RELATIVE_TOLERANCE = 1e-6
DIAGNOSTIC_RELATIVE_TOLERANCE = 1e-12


class CheckError(RuntimeError):
    """Raised when a saved-run check cannot be completed."""


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise CheckError(f"required artifact is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_npy(path: Path) -> np.ndarray:
    if not path.exists():
        raise CheckError(f"required numeric artifact is missing: {path}")
    return np.load(path, allow_pickle=False)


def _load_npz(path: Path) -> Dict[str, np.ndarray]:
    if not path.exists():
        raise CheckError(f"required mask artifact is missing: {path}")
    with np.load(path, allow_pickle=False) as handle:
        return {name: np.asarray(handle[name]) for name in handle.files}


def _check_run(run_id: str, run_type: str, runs_root: Path) -> artifacts.RunDirectory:
    artifacts.validate_run_id(run_id)
    run = artifacts.RunDirectory(runs_root, run_id, run_type)
    return run.reserve()


def _write_check_provenance(
    run: artifacts.RunDirectory,
    *,
    command: Sequence[str],
    inputs: Mapping[str, Any],
    check: str,
    repo_root: Path,
) -> None:
    run.write_json(
        "command.json",
        {"argv": list(command), "cwd": str(Path.cwd())},
    )
    run.write_json(
        "config.json",
        {"check": check, "protocol_version": protocol.PROTOCOL_VERSION},
    )
    git = artifacts.capture_git(repo_root)
    artifacts.write_git_snapshot(run, git)
    run.write_json(
        "provenance.json",
        {
            "run_id": run.run_id,
            "run_type": run.run_type,
            "check": check,
            "created": _now(),
            "git": {
                "commit": git.get("commit"),
                "dirty": git.get("dirty"),
                "errors": git.get("errors"),
            },
            "inputs": dict(inputs),
            "scientific_acceptance": False,
        },
    )


def _now() -> str:
    from .data import iso_now

    return iso_now()


def _hash_tree(directory: Path, relative_paths: Iterable[str]) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for relative in relative_paths:
        path = directory / relative
        if path.exists() and path.is_file():
            hashes[relative] = sha256_file(path)
    return hashes


def _read_optional_json(path: Path) -> Any:
    """Read a JSON artifact, or return ``None`` when it is absent."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _equal_present(left: Any, right: Any) -> bool:
    """Return True only when both values exist and are equal."""
    return left is not None and right is not None and left == right


#: Run-spec fields that identify one invocation rather than the protocol
#: configuration compared for same-condition reproducibility.
_CONFIG_IDENTITY_EXCLUSIONS = frozenset(
    {
        "run_id",
        "run_type",
        "command",
        "launcher_cwd",
        "demand_path",
        "graph_path",
        "mask_bundle",
        "runs_root",
        "repo_root",
        "protocol_path",
    }
)

#: Environment fields that must match for the same execution condition.
#: Invocation paths (python_executable, repo_root) and timestamps are excluded,
#: but recorded linear-algebra, OS/CPU and package conditions are included.
_ENVIRONMENT_IDENTITY_FIELDS = (
    "python_version",
    "python_version_info",
    "platform",
    "system",
    "machine",
    "processor",
    "cpu_count",
    "packages",
    "optional_packages",
    "numpy_blas_config",
    "pip_freeze",
    "thread_environment",
)


def _missing_environment_fields(environment: Any) -> List[str]:
    """Return recorded execution-condition fields that are absent or null."""
    if not isinstance(environment, Mapping):
        return list(_ENVIRONMENT_IDENTITY_FIELDS)
    return [
        field
        for field in _ENVIRONMENT_IDENTITY_FIELDS
        if environment.get(field) is None
    ]


def find_nonfinite(payload: Any, prefix: str = "") -> List[str]:
    """Return paths whose numeric value is NaN or infinite."""
    paths: List[str] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            paths.extend(
                find_nonfinite(value, f"{prefix}.{key}" if prefix else str(key))
            )
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            paths.extend(find_nonfinite(value, f"{prefix}[{index}]"))
    elif isinstance(payload, bool):
        return paths
    elif isinstance(payload, float) and not math.isfinite(payload):
        paths.append(prefix)
    return paths


def _semantic_config(config: Any) -> Any:
    """Return the invocation-independent configuration identity."""
    if not isinstance(config, Mapping):
        return None
    spec = config.get("spec")
    if not isinstance(spec, Mapping):
        return None
    return {
        "protocol_version": config.get("protocol_version"),
        "lambdas": config.get("lambdas"),
        "naive_methods": config.get("naive_methods"),
        "model_name": config.get("model_name"),
        "clip_nonnegative": config.get("clip_nonnegative"),
        "spec": {
            key: value
            for key, value in spec.items()
            if key not in _CONFIG_IDENTITY_EXCLUSIONS
        },
    }


def _semantic_environment(environment: Any) -> Any:
    """Return the execution-condition identity of a recorded environment."""
    if not isinstance(environment, Mapping):
        return None
    return {field: environment.get(field) for field in _ENVIRONMENT_IDENTITY_FIELDS}


def _source_identity(source: Any) -> Dict[str, Any]:
    """Extract the mandatory source-identity hashes from a run manifest."""
    if not isinstance(source, Mapping):
        return {}
    sources = source.get("sources")
    if not isinstance(sources, Mapping):
        return {}

    def entry(name: str) -> Any:
        value = sources.get(name)
        return value.get("sha256") if isinstance(value, Mapping) else None

    coverage = source.get("coverage_bundle_sha256") or entry("coverage")
    return {
        "protocol": entry("protocol"),
        "demand": entry("demand"),
        "coverage": coverage,
        "node_keys": source.get("node_keys_sha256"),
    }


def _missing_source_identity(source: Any) -> List[str]:
    identity = _source_identity(source)
    return [name for name in ("protocol", "demand", "coverage", "node_keys") if not identity.get(name)]


# ---------------------------------------------------------------------------
# metric comparison helpers
# ---------------------------------------------------------------------------
def flatten_numbers(payload: Any, prefix: str = "") -> Dict[str, float]:
    """Flatten a nested structure to ``path -> finite number`` entries."""
    flat: Dict[str, float] = {}
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            flat.update(flatten_numbers(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            flat.update(flatten_numbers(value, f"{prefix}[{index}]"))
    elif isinstance(payload, bool):
        return flat
    elif isinstance(payload, (int, float)):
        value = float(payload)
        if math.isfinite(value):
            flat[prefix] = value
    return flat


def normalized_difference(a: float, b: float) -> float:
    """Return ``abs(a-b) / max(1, abs(a), abs(b))`` for tolerance checks."""
    return abs(a - b) / max(1.0, abs(a), abs(b))


def compare_number_sets(
    expected: Mapping[str, float],
    actual: Mapping[str, float],
    *,
    tolerance: float,
    label: str,
    require_complete: bool = True,
) -> Dict[str, Any]:
    """Compare two flattened numeric maps under a normalized tolerance.

    With ``require_complete`` (the default) the comparison is bidirectional:
    a field present on only one side is incomplete coverage and fails, so a
    deleted report field cannot pass merely because it became an "extra"
    recomputed value.
    """
    common = sorted(set(expected) & set(actual))
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    worst = 0.0
    worst_path = None
    failures: List[Dict[str, Any]] = []
    for path in common:
        difference = normalized_difference(expected[path], actual[path])
        if difference > worst:
            worst = difference
            worst_path = path
        if difference > tolerance:
            failures.append(
                {
                    "path": path,
                    "expected": expected[path],
                    "actual": actual[path],
                    "normalized_difference": difference,
                }
            )
    incomplete = bool(missing or (extra if require_complete else []))
    return {
        "label": label,
        "tolerance": tolerance,
        "require_complete": require_complete,
        "compared_fields": len(common),
        "missing_fields": missing,
        "extra_fields": extra,
        "max_normalized_difference": worst,
        "max_difference_path": worst_path,
        "failed_fields": failures,
        "status": "ok" if not failures and not incomplete else "mismatch",
    }


#: Report keys the run harness adds around the metric payload; they identify the
#: invocation rather than the metric contract and are not present in a
#: recomputed report.
_REPORT_METADATA_KEYS = frozenset(
    {"method", "split", "dataset", "nonself_neighbor_coverage_source"}
)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def compare_report_schema(
    expected: Any,
    actual: Any,
    *,
    tolerance: float,
    label: str,
    ignore_keys: Iterable[str] = frozenset(),
) -> Dict[str, Any]:
    """Compare complete report structure, including null and status fields.

    Flattening only finite numbers would silently drop required ``null``
    metrics and non-numeric status fields, so this walk compares dictionary key
    sets, list lengths and every scalar: nulls must exist on both sides, status
    strings must match, and numbers compare within the normalized tolerance.
    Callers pass the reference structure first, so a required field missing
    from the validated report is reported in ``missing_fields``.
    """
    ignore = frozenset(ignore_keys)
    missing: List[str] = []
    extra: List[str] = []
    failures: List[Dict[str, Any]] = []
    null_fields: List[str] = []
    compared = 0
    worst = 0.0
    worst_path: Optional[str] = None

    def walk(expected_node: Any, actual_node: Any, path: str) -> None:
        nonlocal compared, worst, worst_path
        if isinstance(expected_node, Mapping) and isinstance(actual_node, Mapping):
            expected_keys = {key for key in expected_node if key not in ignore}
            actual_keys = {key for key in actual_node if key not in ignore}
            for key in sorted(expected_keys - actual_keys):
                missing.append(f"{path}.{key}" if path else str(key))
            for key in sorted(actual_keys - expected_keys):
                extra.append(f"{path}.{key}" if path else str(key))
            for key in sorted(expected_keys & actual_keys):
                walk(
                    expected_node[key],
                    actual_node[key],
                    f"{path}.{key}" if path else str(key),
                )
            return
        if isinstance(expected_node, (list, tuple)) and isinstance(
            actual_node, (list, tuple)
        ):
            if len(expected_node) != len(actual_node):
                failures.append(
                    {
                        "path": path,
                        "expected": f"length {len(expected_node)}",
                        "actual": f"length {len(actual_node)}",
                        "reason": "list length mismatch",
                    }
                )
                return
            for index, (left, right) in enumerate(zip(expected_node, actual_node)):
                walk(left, right, f"{path}[{index}]")
            return
        compared += 1
        if expected_node is None and actual_node is None:
            null_fields.append(path)
            return
        if expected_node is None or actual_node is None:
            failures.append(
                {
                    "path": path,
                    "expected": expected_node,
                    "actual": actual_node,
                    "reason": "null/non-null mismatch",
                }
            )
            return
        if isinstance(expected_node, bool) or isinstance(actual_node, bool):
            if expected_node is not actual_node:
                failures.append(
                    {
                        "path": path,
                        "expected": expected_node,
                        "actual": actual_node,
                        "reason": "boolean mismatch",
                    }
                )
            return
        if _is_number(expected_node) and _is_number(actual_node):
            left_value = float(expected_node)
            right_value = float(actual_node)
            if not (math.isfinite(left_value) and math.isfinite(right_value)):
                failures.append(
                    {
                        "path": path,
                        "expected": expected_node,
                        "actual": actual_node,
                        "reason": "non-finite value",
                    }
                )
                return
            difference = normalized_difference(left_value, right_value)
            if difference > worst:
                worst = difference
                worst_path = path
            if difference > tolerance:
                failures.append(
                    {
                        "path": path,
                        "expected": expected_node,
                        "actual": actual_node,
                        "normalized_difference": difference,
                    }
                )
            return
        if expected_node != actual_node:
            failures.append(
                {
                    "path": path,
                    "expected": expected_node,
                    "actual": actual_node,
                    "reason": "value mismatch",
                }
            )

    walk(expected, actual, "")
    incomplete = bool(missing or extra)
    return {
        "label": label,
        "tolerance": tolerance,
        "compared_fields": compared,
        "null_fields": len(null_fields),
        "null_field_paths": null_fields,
        "missing_fields": missing,
        "extra_fields": extra,
        "max_normalized_difference": worst,
        "max_difference_path": worst_path,
        "failed_fields": failures,
        "status": "ok" if not failures and not incomplete else "mismatch",
    }


def validate_report_semantics(payload: Any, *, label: str = "report") -> List[Dict[str, Any]]:
    """Check null/status consistency of required empty and unavailable records.

    Legitimate ``null`` metrics for empty groups and unavailable zero-reference
    gains are preserved; a missing or contradictory status is a problem.
    """
    problems: List[Dict[str, Any]] = []

    def problem(path: str, reason: str, value: Any = None) -> None:
        entry = {"label": label, "path": path, "reason": reason}
        if value is not None:
            entry["value"] = value
        problems.append(entry)

    def walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            if "status" in node:
                record_status = node.get("status")
                if record_status == "empty":
                    if "elements" in node and node["elements"] not in (0, None):
                        problem(path, "empty status with nonzero elements", node["elements"])
                    for field in ("MAE", "MSE", "RMSE", "negative_prediction_ratio"):
                        if field in node and node[field] is not None:
                            problem(
                                path,
                                f"empty status with non-null {field}",
                                node[field],
                            )
                if record_status == "ok":
                    for field in ("MAE", "MSE", "RMSE"):
                        if field in node and node[field] is None:
                            problem(path, f"ok status with null {field}")
                    if (
                        "elements" in node
                        and node["elements"] is not None
                        and node["elements"] <= 0
                    ):
                        problem(path, "ok status with no evaluated elements", node["elements"])
                if "balanced_activity_group_MAE" in node:
                    value = node["balanced_activity_group_MAE"]
                    if record_status == "empty" and value is not None:
                        problem(path, "empty status with a balanced MAE", value)
                    if record_status == "ok" and value is None:
                        problem(path, "ok status without a balanced MAE")
                if "relative_MAE_gain" in node:
                    value = node["relative_MAE_gain"]
                    if record_status == "unavailable" and value is not None:
                        problem(
                            path,
                            "unavailable status with a defined gain",
                            value,
                        )
                    if record_status == "ok" and value is None:
                        problem(path, "ok status without a defined gain")
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, (list, tuple)):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(payload, "")
    return problems


# ---------------------------------------------------------------------------
# recompute
# ---------------------------------------------------------------------------
def command_recompute(
    *,
    run_dir: Path,
    run_id: str,
    runs_root: Path,
    repo_root: Path,
    command: Sequence[str],
) -> Dict[str, Any]:
    """Recompute every saved metric from a completed run directory only."""
    run_dir = Path(run_dir)
    if not run_dir.exists():
        raise CheckError(f"input run directory does not exist: {run_dir}")
    status = _read_json(run_dir / "status.json")
    metrics_document = _read_json(run_dir / "metrics.json")
    nodes = _read_nodes(run_dir / "nodes.parquet")
    key_columns = [column for column in nodes.columns if column != "node_index"]
    masks = _load_npz(run_dir / "masks.npz")
    windows_meta = _read_json(run_dir / "windows.json")
    splits = windows_meta["splits"]

    activity_masks = {
        name: masks[f"activity_{name}"]
        for name in protocol.ACTIVITY_GROUP_NAMES
        if f"activity_{name}" in masks
    }
    constant_masks = {
        "constant_train27": masks["constant_train27"],
        "nonconstant_train27": ~masks["constant_train27"],
    }
    neighbor_masks = {
        "has_nonself_neighbor": masks["has_nonself_neighbor"],
        "no_nonself_neighbor": ~masks["has_nonself_neighbor"],
    }
    context_values = nodes[key_columns[0]].to_numpy()
    context_masks_map = metrics.context_masks(context_values)

    check = _check_run(run_id, "recompute", runs_root)
    try:
        _write_check_provenance(
            check,
            command=command,
            check="recompute",
            repo_root=repo_root,
            inputs={
                "input_run_dir": str(run_dir),
                "input_run_id": status.get("run_id"),
                "input_status": status.get("state"),
                "input_artifacts": _hash_tree(
                    run_dir,
                    [
                        "metrics.json",
                        "nodes.parquet",
                        "masks.npz",
                        "windows.json",
                        "gold/validation.npy",
                        "gold/test.npy",
                        "status.json",
                    ],
                ),
            },
        )
        check.append_event("recompute_started", input_run=str(run_dir))
        recomputed: Dict[str, Dict[str, Any]] = {"validation": {}, "test": {}}
        for split in ("validation", "test"):
            gold = _load_npy(run_dir / "gold" / f"{split}.npy")
            starts = splits[split]
            for method_dir in sorted((run_dir / "predictions").iterdir()):
                if not method_dir.is_dir():
                    continue
                method = method_dir.name
                pred = _load_npy(method_dir / f"{split}.npy")
                if pred.shape != gold.shape:
                    raise CheckError(
                        f"{method}/{split}: prediction shape {pred.shape} != gold {gold.shape}"
                    )
                report = metrics.split_report(
                    pred,
                    gold,
                    starts=starts,
                    activity_masks=activity_masks,
                    constant_masks=constant_masks,
                    context_masks_map=context_masks_map,
                    neighbor_masks=neighbor_masks,
                )
                recomputed[split][method] = report
        stored = metrics_document.get("methods")
        missing_report_fields: List[str] = [
            field
            for field in ("methods", "references", "relative_gains")
            if field not in metrics_document
        ]
        if not isinstance(stored, dict):
            raise CheckError(
                f"{run_dir}/metrics.json does not contain a 'methods' object"
            )
        comparisons = {}
        for split in ("validation", "test"):
            comparisons[split] = compare_report_schema(
                recomputed[split],
                stored.get(split, {}),
                tolerance=DIAGNOSTIC_RELATIVE_TOLERANCE,
                label=f"recompute:{split}",
                ignore_keys=_REPORT_METADATA_KEYS,
            )
        # Non-finite values and required-null/status contradictions are invalid
        # report content, never acceptable nulls.
        nonfinite_stored = find_nonfinite(stored)
        nonfinite_recomputed = find_nonfinite(recomputed)
        stored_semantic_problems = validate_report_semantics(
            stored, label="stored"
        )
        recomputed_semantic_problems = validate_report_semantics(
            recomputed, label="recomputed"
        )

        # Relative gains are part of the reported contract; regenerate them from
        # the saved arrays and frozen references instead of skipping them.
        references = metrics_document.get("references")
        gains_comparison: Dict[str, Any]
        recomputed_gains: Dict[str, Any] = {}
        if isinstance(references, dict) and isinstance(
            metrics_document.get("relative_gains"), dict
        ):
            model_names = [
                method
                for method in sorted(recomputed["test"])
                if method not in protocol.NAIVE_METHODS
            ]
            reference_names = [
                name
                for name in (
                    references.get("NaiveRef"),
                    references.get("NaiveRef6"),
                )
                if name is not None
            ]
            for split in ("validation", "test"):
                recomputed_gains[split] = metrics.baseline_relative_comparison(
                    recomputed[split],
                    context_names=list(context_masks_map),
                    neighbor_names=list(neighbor_masks),
                    model_names=model_names,
                    reference_names=reference_names,
                )
            gains_comparison = compare_report_schema(
                recomputed_gains,
                metrics_document["relative_gains"],
                tolerance=DIAGNOSTIC_RELATIVE_TOLERANCE,
                label="recompute:relative_gains",
            )
            check.write_json("recomputed-relative-gains.json", recomputed_gains)
        else:
            gains_comparison = {
                "label": "recompute:relative_gains",
                "status": "mismatch",
                "reason": "metrics.json is missing references or relative_gains",
                "compared_fields": 0,
                "missing_fields": [],
                "extra_fields": [],
                "failed_fields": [],
                "max_normalized_difference": None,
            }

        nonfinite_gains = find_nonfinite(metrics_document.get("relative_gains", {}))
        gain_semantic_problems = validate_report_semantics(
            metrics_document.get("relative_gains", {}), label="stored_gains"
        )

        # Per-node diagnostic tables are also reported evidence; verify their
        # error sums against freshly reduced saved predictions.
        node_error_comparison = _compare_node_error_tables(run_dir, key_columns)

        check.write_json("recomputed-metrics.json", recomputed)
        failed = [
            name
            for name, comparison in comparisons.items()
            if comparison["status"] != "ok"
        ]
        if gains_comparison["status"] != "ok":
            failed.append("relative_gains")
        if node_error_comparison["status"] != "ok":
            failed.append("node-errors")
        if missing_report_fields:
            failed.append("missing_report_fields")
        if nonfinite_stored or nonfinite_recomputed or nonfinite_gains:
            failed.append("nonfinite_report_values")
        if (
            stored_semantic_problems
            or recomputed_semantic_problems
            or gain_semantic_problems
        ):
            failed.append("report_semantics")
        report = {
            "check": "recompute",
            "input_run_dir": str(run_dir),
            "methods": sorted(
                method
                for method in recomputed["test"].keys()
            ),
            "comparisons": comparisons,
            "relative_gains_comparison": gains_comparison,
            "node_error_comparison": node_error_comparison,
            "missing_report_fields": missing_report_fields,
            "required_report_fields": ["methods", "references", "relative_gains"],
            "nonfinite_stored_fields": nonfinite_stored,
            "nonfinite_recomputed_fields": nonfinite_recomputed,
            "nonfinite_gain_fields": nonfinite_gains,
            "stored_semantic_problems": stored_semantic_problems,
            "recomputed_semantic_problems": recomputed_semantic_problems,
            "gain_semantic_problems": gain_semantic_problems,
            "source_data_read": False,
            "model_refit": False,
            "status": "ok" if not failed else "mismatch",
        }
        check.write_json("report.json", report)
        check.write_text(
            "summary.md",
            f"# Recompute check {run_id}\n\n"
            f"- Input run: `{run_dir}`\n"
            f"- Methods: {', '.join(report['methods']) or 'none'}\n"
            f"- Relative-gain fields compared: "
            f"{gains_comparison.get('compared_fields')}\n"
            f"- Per-node rows compared: "
            f"{node_error_comparison.get('compared_rows')}\n"
            f"- Result: {report['status']}\n"
            f"- Source demand/graph data was not read and no model was fit.\n",
        )
        check.set_status("success" if not failed else "failed", stage="complete")
        check.finalize_artifacts_manifest()
        return {"run_dir": str(check.path), "status": report["status"], "report": report}
    except BaseException as exc:  # noqa: BLE001
        check.set_status("failed", stage="recompute", error=repr(exc))
        raise


def _read_nodes(path: Path) -> "Any":
    import pandas as pd

    if not path.exists():
        raise CheckError(f"required artifact is missing: {path}")
    return pd.read_parquet(path)


def _compare_node_error_tables(
    run_dir: Path,
    key_columns: Sequence[str],
) -> Dict[str, Any]:
    """Verify the saved per-node diagnostic table against saved arrays."""
    import pandas as pd

    stored_path = run_dir / "node-errors.parquet"
    if not stored_path.exists():
        return {
            "status": "mismatch",
            "reason": "node-errors.parquet is missing",
            "compared_rows": 0,
        }
    statistics_path = run_dir / "models" / "TrainMean27.npz"
    if not statistics_path.exists():
        return {
            "status": "mismatch",
            "reason": "models/TrainMean27.npz is missing",
            "compared_rows": 0,
        }
    with np.load(statistics_path, allow_pickle=False) as handle:
        if "train_mean27" not in handle:
            return {
                "status": "mismatch",
                "reason": "TrainMean27 statistics are missing",
                "compared_rows": 0,
            }
        train_mean = np.asarray(handle["train_mean27"], dtype=np.float64).reshape(-1)
    nodes = _read_nodes(run_dir / "nodes.parquet")
    keys = nodes[list(key_columns)].to_numpy()
    context_values = nodes[list(key_columns)[0]].to_numpy()
    frames = []
    for split in ("validation", "test"):
        gold = _load_npy(run_dir / "gold" / f"{split}.npy")
        for method_dir in sorted((run_dir / "predictions").iterdir()):
            if not method_dir.is_dir():
                continue
            method = method_dir.name
            pred = _load_npy(method_dir / f"{split}.npy")
            if pred.shape != gold.shape:
                return {
                    "status": "mismatch",
                    "reason": f"{method}/{split} prediction shape {pred.shape} != gold {gold.shape}",
                    "compared_rows": 0,
                }
            frames.append(
                metrics.node_error_table(
                    pred,
                    gold,
                    method=method,
                    split=split,
                    node_keys=keys,
                    key_columns=list(key_columns),
                    train_mean27_values=train_mean,
                    context_values=context_values,
                )
            )
    recomputed_frame = pd.concat(frames, ignore_index=True)
    stored = pd.read_parquet(stored_path)
    required_columns = [
        "method",
        "split",
        "absolute_error_sum",
        "squared_error_sum",
        "elements",
        "MAE",
        "MSE",
        *key_columns,
    ]
    missing_columns = [column for column in required_columns if column not in stored.columns]
    if missing_columns:
        return {
            "status": "mismatch",
            "reason": f"node-errors.parquet is missing column(s) {missing_columns}",
            "compared_rows": 0,
        }
    merge_keys = ["method", "split", *key_columns]
    merged = stored.merge(
        recomputed_frame,
        on=merge_keys,
        how="outer",
        suffixes=("_stored", "_recomputed"),
        indicator=True,
    )
    unmatched = int((merged["_merge"] != "both").sum())
    both = merged[merged["_merge"] == "both"]
    # Reject non-finite per-node values before tolerance comparison: NaN never
    # exceeds a tolerance, so an unchecked NaN would look like agreement.
    nonfinite_fields: List[str] = []
    for column in (
        "absolute_error_sum",
        "squared_error_sum",
        "elements",
        "MAE",
        "MSE",
        "train_mean27",
    ):
        for side in ("stored", "recomputed"):
            name = f"{column}_{side}"
            if name not in both.columns:
                continue
            values = both[name].to_numpy(dtype=np.float64)
            if not np.isfinite(values).all():
                nonfinite_fields.append(name)
    worst = 0.0
    worst_column = None
    failed_fields = 0
    for column in (
        "absolute_error_sum",
        "squared_error_sum",
        "elements",
        "MAE",
        "MSE",
    ):
        stored_values = both[f"{column}_stored"].to_numpy(dtype=np.float64)
        recomputed_values = both[f"{column}_recomputed"].to_numpy(dtype=np.float64)
        differences = np.abs(stored_values - recomputed_values) / np.maximum(
            1.0, np.maximum(np.abs(stored_values), np.abs(recomputed_values))
        )
        # A non-finite pair is a failure regardless of the tolerance result.
        differences = np.where(
            np.isfinite(differences), differences, np.inf
        )
        maximum = float(differences.max()) if differences.size else 0.0
        if np.isfinite(maximum) and maximum > worst:
            worst = maximum
            worst_column = column
        failed_fields += int((differences > DIAGNOSTIC_RELATIVE_TOLERANCE).sum())
    status = (
        "ok"
        if failed_fields == 0
        and unmatched == 0
        and not nonfinite_fields
        and len(both) == len(stored) == len(recomputed_frame)
        else "mismatch"
    )
    return {
        "status": status,
        "compared_rows": int(len(both)),
        "stored_rows": int(len(stored)),
        "recomputed_rows": int(len(recomputed_frame)),
        "unmatched_rows": unmatched,
        "failed_fields": failed_fields,
        "nonfinite_fields": nonfinite_fields,
        "max_normalized_difference": worst,
        "max_difference_column": worst_column,
        "tolerance": DIAGNOSTIC_RELATIVE_TOLERANCE,
    }


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------
def command_compare(
    *,
    run_a: Path,
    run_b: Path,
    run_id: str,
    runs_root: Path,
    repo_root: Path,
    command: Sequence[str],
) -> Dict[str, Any]:
    """Compare two same-seed runs and apply the CPU agreement criterion."""
    run_a, run_b = Path(run_a), Path(run_b)
    for label, run_dir in (("a", run_a), ("b", run_b)):
        if not run_dir.exists():
            raise CheckError(f"run {label} does not exist: {run_dir}")
    status_a = _read_json(run_a / "status.json")
    status_b = _read_json(run_b / "status.json")
    metrics_a = _read_json(run_a / "metrics.json")
    metrics_b = _read_json(run_b / "metrics.json")
    config_a = _read_json(run_a / "config.json")
    config_b = _read_json(run_b / "config.json")
    selection_a = _read_json(run_a / "selection.json")
    selection_b = _read_json(run_b / "selection.json")
    # Source and environment manifests are mandatory identity evidence; read
    # them tolerantly so a missing file is recorded as incomplete rather than
    # silently treated as agreement.
    source_a = _read_optional_json(run_a / "source-sha256.json")
    source_b = _read_optional_json(run_b / "source-sha256.json")
    environment_a = _read_optional_json(run_a / "environment.json")
    environment_b = _read_optional_json(run_b / "environment.json")

    check = _check_run(run_id, "compare", runs_root)
    try:
        _write_check_provenance(
            check,
            command=command,
            check="compare",
            repo_root=repo_root,
            inputs={
                "run_a": str(run_a),
                "run_b": str(run_b),
                "run_a_artifacts": _hash_tree(
                    run_a, ["metrics.json", "selection.json", "source-sha256.json"]
                ),
                "run_b_artifacts": _hash_tree(
                    run_b, ["metrics.json", "selection.json", "source-sha256.json"]
                ),
            },
        )
        check.append_event("compare_started")
        spec_a = config_a.get("spec", {}) if isinstance(config_a, Mapping) else {}
        spec_b = config_b.get("spec", {}) if isinstance(config_b, Mapping) else {}
        source_identity_a = _source_identity(source_a)
        source_identity_b = _source_identity(source_b)
        missing_evidence: List[str] = []
        for label, run_dir, source, environment in (
            ("a", run_a, source_a, environment_a),
            ("b", run_b, source_b, environment_b),
        ):
            if source is None:
                missing_evidence.append(f"run_{label}:source-sha256.json")
            else:
                missing_evidence.extend(
                    f"run_{label}:source.{name}"
                    for name in _missing_source_identity(source)
                )
            if environment is None:
                missing_evidence.append(f"run_{label}:environment.json")
            else:
                missing_evidence.extend(
                    f"run_{label}:environment.{field}"
                    for field in _missing_environment_fields(environment)
                )
            for required in ("selection.json", "config.json", "metrics.json"):
                if not (run_dir / required).exists():
                    missing_evidence.append(f"run_{label}:{required}")
        identity_checks = {
            "dataset": bool(
                _equal_present(spec_a.get("data_name"), spec_b.get("data_name"))
            ),
            "mode": bool(_equal_present(spec_a.get("mode"), spec_b.get("mode"))),
            "seed": bool(_equal_present(spec_a.get("seed"), spec_b.get("seed"))),
            "ridge_backend": bool(
                _equal_present(
                    spec_a.get("ridge_backend"), spec_b.get("ridge_backend")
                )
            ),
            "clip_nonnegative": bool(
                _equal_present(
                    spec_a.get("clip_nonnegative"), spec_b.get("clip_nonnegative")
                )
            ),
            "semantic_config": bool(
                _equal_present(
                    _semantic_config(config_a), _semantic_config(config_b)
                )
            ),
            "protocol_version": bool(
                _equal_present(
                    metrics_a.get("protocol_version"),
                    metrics_b.get("protocol_version"),
                )
            ),
            "protocol_sha256": bool(
                _equal_present(
                    source_identity_a.get("protocol"),
                    source_identity_b.get("protocol"),
                )
            ),
            "demand_sha256": bool(
                _equal_present(
                    source_identity_a.get("demand"),
                    source_identity_b.get("demand"),
                )
            ),
            "coverage_identity": bool(
                _equal_present(
                    source_identity_a.get("coverage"),
                    source_identity_b.get("coverage"),
                )
            ),
            "node_keys_sha256": bool(
                _equal_present(
                    source_identity_a.get("node_keys"),
                    source_identity_b.get("node_keys"),
                )
            ),
            "environment_packages": bool(
                _equal_present(
                    (environment_a or {}).get("packages"),
                    (environment_b or {}).get("packages"),
                )
            ),
            "environment_optional_packages": bool(
                _equal_present(
                    (environment_a or {}).get("optional_packages"),
                    (environment_b or {}).get("optional_packages"),
                )
            ),
            "environment_semantic": bool(
                _equal_present(
                    _semantic_environment(environment_a),
                    _semantic_environment(environment_b),
                )
            ),
            "selected_lambda": bool(
                _equal_present(
                    selection_a.get("shared_ridge", {}).get("selected_lambda"),
                    selection_b.get("shared_ridge", {}).get("selected_lambda"),
                )
            ),
            "naive_ref": bool(
                _equal_present(
                    selection_a.get("naive_references", {}).get("NaiveRef"),
                    selection_b.get("naive_references", {}).get("NaiveRef"),
                )
            ),
            "naive_ref6": bool(
                _equal_present(
                    selection_a.get("naive_references", {}).get("NaiveRef6"),
                    selection_b.get("naive_references", {}).get("NaiveRef6"),
                )
            ),
            "environment_condition_complete": bool(
                environment_a is not None
                and environment_b is not None
                and not _missing_environment_fields(environment_a)
                and not _missing_environment_fields(environment_b)
            ),
            "identity_evidence_complete": not missing_evidence,
        }
        methods = sorted(
            set(metrics_a.get("methods", {}).get("test", {}))
            & set(metrics_b.get("methods", {}).get("test", {}))
        )
        prediction_comparisons: Dict[str, Any] = {}
        masks_equal = True
        masks_a = _load_npz(run_a / "masks.npz")
        masks_b = _load_npz(run_b / "masks.npz")
        for name in sorted(set(masks_a) | set(masks_b)):
            if name not in masks_a or name not in masks_b:
                masks_equal = False
                break
            if not np.array_equal(masks_a[name], masks_b[name]):
                masks_equal = False
                break
        for split in ("validation", "test"):
            for method in methods:
                path_a = run_a / "predictions" / method / f"{split}.npy"
                path_b = run_b / "predictions" / method / f"{split}.npy"
                pred_a = _load_npy(path_a)
                pred_b = _load_npy(path_b)
                if pred_a.shape != pred_b.shape:
                    prediction_comparisons[f"{split}/{method}"] = {
                        "status": "shape_mismatch",
                        "shape_a": list(pred_a.shape),
                        "shape_b": list(pred_b.shape),
                    }
                    continue
                first = pred_a.astype(np.float64)
                second = pred_b.astype(np.float64)
                absolute = np.abs(first - second)
                denominator = np.maximum(1.0, np.maximum(np.abs(first), np.abs(second)))
                normalized = absolute / denominator
                prediction_comparisons[f"{split}/{method}"] = {
                    "max_absolute_difference": float(absolute.max())
                    if absolute.size
                    else 0.0,
                    "max_normalized_difference": float(normalized.max())
                    if normalized.size
                    else 0.0,
                    "elementwise_violations": int(
                        (normalized > CPU_RELATIVE_TOLERANCE).sum()
                    ),
                    "status": "ok"
                    if normalized.size == 0
                    or float(normalized.max()) <= CPU_RELATIVE_TOLERANCE
                    else "mismatch",
                }
        metric_comparison = compare_number_sets(
            flatten_numbers(metrics_a.get("methods", {})),
            flatten_numbers(metrics_b.get("methods", {})),
            tolerance=CPU_RELATIVE_TOLERANCE,
            label="metrics",
        )
        mae_relative_differences: Dict[str, Any] = {}
        mae_ok = True
        for split in ("validation", "test"):
            for method in methods:
                report_a = metrics_a["methods"][split].get(method, {})
                report_b = metrics_b["methods"][split].get(method, {})
                mae_a = report_a.get("MAE")
                mae_b = report_b.get("MAE")
                if mae_a is None or mae_b is None:
                    continue
                relative = abs(mae_a - mae_b) / max(1.0, abs(mae_a), abs(mae_b))
                passes = relative <= CPU_RELATIVE_TOLERANCE
                mae_ok = mae_ok and passes
                mae_relative_differences[f"{split}/{method}"] = {
                    "MAE_a": mae_a,
                    "MAE_b": mae_b,
                    "relative_difference": relative,
                    "criterion": "abs(MAE_a-MAE_b)/max(1,MAE_a,MAE_b) <= 1e-6",
                    "status": "ok" if passes else "mismatch",
                }
        identity_ok = all(identity_checks.values())
        predictions_ok = all(
            value.get("status") == "ok" for value in prediction_comparisons.values()
        )
        overall_ok = (
            identity_ok
            and predictions_ok
            and metric_comparison["status"] == "ok"
            and mae_ok
            and masks_equal
        )
        report = {
            "check": "compare",
            "run_a": str(run_a),
            "run_b": str(run_b),
            "status_a": status_a.get("state"),
            "status_b": status_b.get("state"),
            "identity_checks": identity_checks,
            "identity_evidence_complete": not missing_evidence,
            "missing_evidence": missing_evidence,
            "identity_evidence": {
                "source_identity_a": source_identity_a,
                "source_identity_b": source_identity_b,
                "config_identity_a": _semantic_config(config_a),
                "config_identity_b": _semantic_config(config_b),
                "environment_identity_a": _semantic_environment(environment_a),
                "environment_identity_b": _semantic_environment(environment_b),
            },
            "masks_equal": masks_equal,
            "selection_a": selection_a.get("shared_ridge", {}).get(
                "selected_lambda"
            ),
            "selection_b": selection_b.get("shared_ridge", {}).get(
                "selected_lambda"
            ),
            "prediction_comparisons": prediction_comparisons,
            "metric_comparison": metric_comparison,
            "mae_relative_differences": mae_relative_differences,
            "cpu_relative_tolerance": CPU_RELATIVE_TOLERANCE,
            "seed_variance_reported": False,
            "status": "ok" if overall_ok else "mismatch",
        }
        check.write_json("report.json", report)
        check.write_text(
            "summary.md",
            f"# Compare check {run_id}\n\n"
            f"- Run A: `{run_a}`\n- Run B: `{run_b}`\n"
            f"- Result: {report['status']}\n"
            f"- Semantic config, recorded environment, protocol/source identities and\n"
            f"  masks are compared before arrays; missing identity evidence is\n"
            f"  incomplete rather than agreement, and disagreement is reported as an\n"
            f"  execution difference, not seed variance.\n",
        )
        check.set_status("success" if overall_ok else "failed", stage="complete")
        check.finalize_artifacts_manifest()
        return {"run_dir": str(check.path), "status": report["status"], "report": report}
    except BaseException as exc:  # noqa: BLE001
        check.set_status("failed", stage="compare", error=repr(exc))
        raise


# ---------------------------------------------------------------------------
# align-v2
# ---------------------------------------------------------------------------
def parse_v2_reference(path: Path) -> Dict[str, Any]:
    """Parse every JSON line of the sealed v2 diagnostic log."""
    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise CheckError(f"{path}:{line_number}: invalid JSON line: {exc}") from exc
    by_dataset: Dict[str, Dict[str, Any]] = {}
    for record in records:
        dataset = record.get("dataset")
        if dataset is None:
            continue
        bucket = by_dataset.setdefault(dataset, {"models": {}, "references": None})
        if "model" in record and "split" in record:
            bucket["models"][(record["split"], record["model"])] = record
        if "NaiveRef" in record:
            bucket["references"] = record
        if "split_windows" in record:
            bucket["windows"] = record
        if "activity_group_counts" in record:
            bucket["audit"] = record
    return {"records": records, "by_dataset": by_dataset}


def command_align_v2(
    *,
    run_dir: Path,
    reference: Path,
    run_id: str,
    runs_root: Path,
    repo_root: Path,
    command: Sequence[str],
) -> Dict[str, Any]:
    """Align a completed run's na\"ive results with the immutable v2 diagnostic."""
    run_dir, reference = Path(run_dir), Path(reference)
    if not run_dir.exists():
        raise CheckError(f"input run directory does not exist: {run_dir}")
    if not reference.exists():
        raise CheckError(f"v2 reference log does not exist: {reference}")
    reference_sha256 = sha256_file(reference)
    parsed = parse_v2_reference(reference)
    metrics_document = _read_json(run_dir / "metrics.json")
    audit = _read_json(run_dir / "audit.json")
    windows_meta = _read_json(run_dir / "windows.json")
    dataset = metrics_document["dataset"]
    bucket = parsed["by_dataset"].get(dataset)
    if bucket is None:
        raise CheckError(f"v2 reference log has no records for dataset {dataset!r}")

    check = _check_run(run_id, "align-v2", runs_root)
    try:
        _write_check_provenance(
            check,
            command=command,
            check="align-v2",
            repo_root=repo_root,
            inputs={
                "input_run_dir": str(run_dir),
                "reference_path": str(reference),
                "reference_sha256": reference_sha256,
                "input_artifacts": _hash_tree(
                    run_dir, ["metrics.json", "audit.json", "windows.json"]
                ),
            },
        )
        check.append_event("align_v2_started", reference=str(reference))
        checks: List[Dict[str, Any]] = []

        def add_scalar(field: str, expected: Any, actual: Any, *, numeric: bool = True) -> None:
            if expected is None and actual is None:
                checks.append(
                    {
                        "field": field,
                        "expected": expected,
                        "actual": actual,
                        "normalized_difference": 0.0,
                        "status": "ok",
                    }
                )
                return
            if numeric and isinstance(expected, (int, float)) and isinstance(
                actual, (int, float)
            ):
                difference = normalized_difference(float(expected), float(actual))
                checks.append(
                    {
                        "field": field,
                        "expected": expected,
                        "actual": actual,
                        "normalized_difference": difference,
                        "tolerance": DIAGNOSTIC_RELATIVE_TOLERANCE,
                        "status": "ok"
                        if difference <= DIAGNOSTIC_RELATIVE_TOLERANCE
                        else "mismatch",
                    }
                )
            else:
                checks.append(
                    {
                        "field": field,
                        "expected": expected,
                        "actual": actual,
                        "status": "ok" if expected == actual else "mismatch",
                    }
                )

        v2_audit = bucket.get("audit", {})
        for field in (
            "nodes",
            "skill_id_nunique",
            "joint_contexts",
            "context_cartesian_size",
            "expected_context_skill_nodes",
            "train_all_zero_fraction",
            "full_36_month_all_zero_fraction_diagnostic_only",
        ):
            if field in v2_audit:
                add_scalar(f"audit.{field}", v2_audit[field], audit.get(field))
        for key, value in v2_audit.get("activity_group_counts", {}).items():
            add_scalar(
                f"audit.activity_group_counts.{key}",
                value,
                audit.get("activity_group_counts", {}).get(key),
            )
        add_scalar(
            "audit.context_id_counts",
            v2_audit.get("context_id_counts"),
            audit.get("context_id_counts"),
            numeric=False,
        )
        add_scalar(
            "audit.is_complete_context_skill_grid",
            v2_audit.get("is_complete_context_skill_grid"),
            audit.get("is_complete_context_skill_grid"),
            numeric=False,
        )
        add_scalar(
            "audit.train_observation_months",
            v2_audit.get("train_observation_months"),
            audit.get("train_observation_months"),
            numeric=False,
        )

        v2_windows = bucket.get("windows", {})
        if "nodes" in v2_windows:
            add_scalar("audit.nodes", v2_windows["nodes"], audit.get("nodes"))
        add_scalar(
            "windows.split_windows",
            {key: list(value) for key, value in v2_windows.get("split_windows", {}).items()},
            {key: list(value) for key, value in windows_meta["splits"].items()},
            numeric=False,
        )
        actual_targets = {
            split: sorted(
                {
                    month
                    for start in starts
                    for month in protocol.window_target_months(start)
                }
            )
            for split, starts in windows_meta["splits"].items()
        }
        add_scalar(
            "windows.target_months",
            v2_windows.get("target_months"),
            actual_targets,
            numeric=False,
        )

        references = metrics_document.get("references", {})
        v2_references = bucket.get("references", {})
        add_scalar(
            "references.NaiveRef",
            v2_references.get("NaiveRef"),
            references.get("NaiveRef"),
            numeric=False,
        )
        add_scalar(
            "references.NaiveRef6",
            v2_references.get("NaiveRef6"),
            references.get("NaiveRef6"),
            numeric=False,
        )
        add_scalar(
            "references.SeasonalNaive12_information_budget",
            v2_references.get("SeasonalNaive12_information_budget"),
            references.get("information_budget", {}).get("SeasonalNaive12"),
            numeric=False,
        )

        methods = metrics_document["methods"]
        for (split, model), record in sorted(bucket["models"].items()):
            actual = methods.get(split, {}).get(model)
            if actual is None:
                checks.append(
                    {
                        "field": f"{split}.{model}",
                        "expected": "present in v2 reference",
                        "actual": None,
                        "status": "mismatch",
                    }
                )
                continue
            for field in ("MAE", "MSE", "RMSE"):
                if field in record:
                    add_scalar(f"{split}.{model}.{field}", record[field], actual.get(field))
            if "balanced_activity_group_MAE" in record:
                add_scalar(
                    f"{split}.{model}.balanced_activity_group_MAE",
                    record["balanced_activity_group_MAE"],
                    actual.get("balanced_activity_group_MAE"),
                )
            for horizon, values in record.get("horizons", {}).items():
                for field, value in values.items():
                    add_scalar(
                        f"{split}.{model}.horizons.{horizon}.{field}",
                        value,
                        actual.get("horizons", {}).get(horizon, {}).get(field),
                    )
            for group, values in record.get("activity_groups", {}).items():
                for field, value in values.items():
                    add_scalar(
                        f"{split}.{model}.activity_groups.{group}.{field}",
                        value,
                        actual.get("activity_groups", {}).get(group, {}).get(field),
                    )
            actual_windows = {
                row["forecast_origin"]: row for row in actual.get("windows", [])
            }
            for index, window in enumerate(record.get("windows", [])):
                origin = window.get("forecast_origin")
                actual_window = actual_windows.get(origin)
                if actual_window is None:
                    checks.append(
                        {
                            "field": f"{split}.{model}.windows[{index}]",
                            "expected": origin,
                            "actual": None,
                            "status": "mismatch",
                        }
                    )
                    continue
                for field in ("MAE", "MSE", "RMSE"):
                    add_scalar(
                        f"{split}.{model}.windows[{origin}].{field}",
                        window.get(field),
                        actual_window.get(field),
                    )
                add_scalar(
                    f"{split}.{model}.windows[{origin}].target_months",
                    window.get("target_months"),
                    actual_window.get("target_months"),
                    numeric=False,
                )

        # Identity evidence: an available contradictory source-identity check is
        # a finding that affects the alignment outcome; unavailable evidence has
        # an explicit limited outcome instead of defaulting to success.
        run_source = _read_optional_json(run_dir / "source-sha256.json")
        run_source_identity = _source_identity(run_source)
        identity_evidence: Dict[str, Any] = {
            "v2_log_contains_counts_not_full_node_keys": True,
            "run_node_keys_sha256": run_source_identity.get("node_keys"),
            "run_demand_sha256": run_source_identity.get("demand"),
            "run_protocol_sha256": run_source_identity.get("protocol"),
            "run_source_manifest_present": run_source is not None,
            "v2_source_sha256_available": False,
            "v2_source_sha256_demand": None,
            "identity_check_limitation": (
                "the v2 log reports aggregate counts rather than full canonical "
                "node keys, so row-level identity equality is established through "
                "the hashed demand source and canonical ordering, not from the log"
            ),
        }
        if run_source_identity.get("node_keys"):
            checks.append(
                {
                    "field": "identity.run_node_keys_sha256",
                    "expected": "present",
                    "actual": run_source_identity["node_keys"],
                    "status": "ok",
                }
            )
        else:
            checks.append(
                {
                    "field": "identity.run_node_keys_sha256",
                    "expected": "present",
                    "actual": None,
                    "status": "mismatch",
                }
            )
        if not run_source_identity.get("demand"):
            checks.append(
                {
                    "field": "identity.run_demand_sha256",
                    "expected": "present",
                    "actual": None,
                    "status": "mismatch",
                }
            )
        v2_source = reference.parent / "source-sha256.txt"
        if v2_source.exists():
            identity_evidence["v2_source_sha256_available"] = True
            identity_evidence["v2_source_sha256_file"] = str(v2_source)
            identity_evidence["v2_source_sha256_sha256"] = sha256_file(v2_source)
            v2_demand_sha256 = None
            for line in v2_source.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1].endswith(
                    f"demand/{dataset}.parquet"
                ):
                    v2_demand_sha256 = parts[0]
            identity_evidence["v2_source_sha256_demand"] = v2_demand_sha256
            if v2_demand_sha256 is None:
                identity_evidence["demand_sha256_matches_v2"] = None
                checks.append(
                    {
                        "field": "identity.demand_sha256_vs_v2",
                        "expected": "a v2 source manifest entry for this dataset",
                        "actual": run_source_identity.get("demand"),
                        "status": "limited",
                        "reason": "the v2 source manifest has no demand entry for this dataset",
                    }
                )
            else:
                matches = (
                    v2_demand_sha256 == run_source_identity.get("demand")
                )
                identity_evidence["demand_sha256_matches_v2"] = matches
                checks.append(
                    {
                        "field": "identity.demand_sha256_vs_v2",
                        "expected": v2_demand_sha256,
                        "actual": run_source_identity.get("demand"),
                        "status": "ok" if matches else "mismatch",
                    }
                )
        else:
            identity_evidence["demand_sha256_matches_v2"] = None
            checks.append(
                {
                    "field": "identity.v2_source_manifest",
                    "expected": "present",
                    "actual": None,
                    "status": "limited",
                    "reason": (
                        "the v2 reference has no source manifest, so source "
                        "identity is unverified rather than equal"
                    ),
                }
            )
        identity_evidence["run_source_manifest"] = run_source

        discrepancies = [row for row in checks if row["status"] == "mismatch"]
        limited_findings = [row for row in checks if row["status"] == "limited"]
        reference_unchanged = sha256_file(reference) == reference_sha256
        if not reference_unchanged:
            discrepancies.append(
                {
                    "field": "reference.integrity",
                    "expected": reference_sha256,
                    "actual": sha256_file(reference),
                    "status": "mismatch",
                }
            )
        if discrepancies:
            status = "mismatch"
        elif limited_findings:
            status = "limited"
        else:
            status = "ok"

        report = {
            "check": "align-v2",
            "input_run_dir": str(run_dir),
            "reference_path": str(reference),
            "reference_sha256": reference_sha256,
            "reference_unchanged": reference_unchanged,
            "dataset": dataset,
            "compared_fields": len(checks),
            "tolerance": DIAGNOSTIC_RELATIVE_TOLERANCE,
            "checks": checks,
            "discrepancies": discrepancies,
            "limited_findings": limited_findings,
            "identity_evidence": identity_evidence,
            "identity_status": (
                "mismatch"
                if any(
                    row["field"].startswith("identity.")
                    for row in discrepancies
                )
                else ("limited" if limited_findings else "ok")
            ),
            "diagnostic_elapsed_time_compared_as_cost": False,
            "status": status,
        }
        check.write_json("report.json", report)
        check.write_text(
            "summary.md",
            f"# align-v2 check {run_id}\n\n"
            f"- Input run: `{run_dir}`\n- Reference: `{reference}`\n"
            f"- Compared fields: {len(checks)}\n"
            f"- Discrepancies: {len(discrepancies)}\n"
            f"- Limited identity findings: {len(limited_findings)}\n"
            f"- Result: {report['status']}\n\n"
            "The reference log is read-only and was not modified. Diagnostic\n"
            "elapsed time is not compared with the new entry's measured cost.\n"
            "Source-identity contradictions are findings, not silent agreement.\n",
        )
        check.set_status("success" if status == "ok" else "failed", stage="complete")
        check.finalize_artifacts_manifest()
        return {"run_dir": str(check.path), "status": report["status"], "report": report}
    except BaseException as exc:  # noqa: BLE001
        check.set_status("failed", stage="align-v2", error=repr(exc))
        raise
