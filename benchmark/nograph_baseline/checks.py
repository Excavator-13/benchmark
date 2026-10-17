"""Saved-run analysis commands: recompute, compare and immutable v2 alignment.

None of these commands fits a model, reads source demand/graph data, or alters
its input runs.  Each writes exactly one exclusive JSON report carrying its
command, checker source identity, consumed-input identities, tolerances,
status/results/errors and embedded recomputed metrics.  No check-type run
directory, source snapshot, environment copy, sidecar or artifact hash table is
produced.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from . import artifacts, metrics, protocol
from .data import activity_group_masks, sha256_file

#: Normalized tolerances used by saved-run checks.
CPU_RELATIVE_TOLERANCE = 1e-6
DIAGNOSTIC_RELATIVE_TOLERANCE = 1e-12

#: Version of the single-report envelope written by every check command.
REPORT_VERSION = 1

#: Default root for the legacy ``--run-id`` report alias.
DEFAULT_REPORTS_ROOT = ("research", "reports", "nograph-baseline")


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


def default_reports_root(repo_root: Path) -> Path:
    """Return the documented default root for legacy run-ID report aliases."""
    return Path(repo_root).joinpath(*DEFAULT_REPORTS_ROOT)


def resolve_report_path(
    *,
    report_path: Optional[Path] = None,
    run_id: Optional[str] = None,
    runs_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> Path:
    """Resolve the exclusive output choice for one check command.

    ``report_path`` and the legacy ``run_id``/``runs_root`` alias are mutually
    exclusive and one of them is required.
    """
    if report_path is not None and run_id is not None:
        raise CheckError(
            "a check accepts either an explicit report path or a legacy run ID, "
            "not both"
        )
    if report_path is not None:
        return Path(report_path)
    if run_id is None:
        raise CheckError("a report path or a legacy run ID is required")
    try:
        artifacts.validate_run_id(run_id)
    except artifacts.ArtifactError as exc:
        raise CheckError(str(exc)) from exc
    if runs_root is None:
        runs_root = default_reports_root(
            Path(repo_root) if repo_root is not None else protocol.REPO_ROOT
        )
    return Path(runs_root) / f"{run_id}.json"


def _reject_unsafe_destination(
    destination: Path, inputs: Sequence[Any]
) -> None:
    """Refuse an output that already exists or resolves inside an input run.

    Each input entry is ``(label, path, kind)`` where ``kind`` is ``"dir"`` for
    an input run directory (output must not fall inside it) or ``"file"`` for a
    read-only reference (output must merely not replace it).
    """
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
            raise CheckError(
                f"report path {destination} resolves to the {label} input"
            )
        if kind != "dir":
            continue
        if resolved_input in resolved.parents:
            raise CheckError(
                f"report path {destination} resolves inside the {label} input "
                f"{raw}"
            )


def _write_report(destination: Path, envelope: Mapping[str, Any]) -> Path:
    """Publish one complete JSON report with exclusive creation."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(envelope), indent=2, sort_keys=True, ensure_ascii=False)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        descriptor = os.open(destination, flags, 0o644)
    except FileExistsError as exc:
        raise CheckError(
            "report destination already exists and will not be replaced: "
            f"{destination}"
        ) from exc
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


def _envelope(
    kind: str,
    *,
    command: Sequence[str],
    repo_root: Path,
    inputs: Mapping[str, Any],
    tolerances: Mapping[str, Any],
    status: str,
    result: Mapping[str, Any],
    errors: Sequence[Any],
) -> Dict[str, Any]:
    """Assemble the documented single-report envelope."""
    return {
        "version": REPORT_VERSION,
        "kind": kind,
        "created": _now(),
        "status": status,
        "command": {"argv": list(command), "cwd": str(Path.cwd())},
        "checker": {
            "protocol_version": protocol.PROTOCOL_VERSION,
            "source": artifacts.checker_source_identity(Path(repo_root)),
        },
        "inputs": dict(inputs),
        "tolerances": dict(tolerances),
        "result": dict(result),
        "errors": list(errors),
    }


def _failure_envelope(
    kind: str,
    *,
    command: Sequence[str],
    repo_root: Path,
    inputs: Mapping[str, Any],
    tolerances: Mapping[str, Any],
    exc: BaseException,
) -> Dict[str, Any]:
    """Build the honest failure report for an unusable saved input."""
    error = {
        "type": type(exc).__name__,
        "message": str(exc),
    }
    result = {"status": "failed", "error": error}
    return _envelope(
        kind,
        command=command,
        repo_root=repo_root,
        inputs=inputs,
        tolerances=tolerances,
        status="failed",
        result=result,
        errors=[error],
    )


def _finish(destination: Path, envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Publish a report and return the public command result."""
    _write_report(destination, envelope)
    return {
        "report_path": str(destination),
        "status": envelope["status"],
        "report": envelope["result"],
        "envelope": envelope,
    }



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


#: Run-spec fields that identify one invocation or persistence choice rather
#: than the scientific condition compared for same-condition reproducibility.
#: ``purpose`` and ``retain_candidates`` only select the output root and whether
#: losing candidate arrays are kept, so two otherwise identical executions still
#: compare as the same condition.
_CONFIG_IDENTITY_EXCLUSIONS = frozenset(
    {
        "run_id",
        "run_type",
        "purpose",
        "retain_candidates",
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
# saved split identity (main, fold A or fold B)
# ---------------------------------------------------------------------------
_FOLD_BLOCK_FIELDS = (
    "fold",
    "fitting_observation_months",
    "fitting_month_count",
    "train_starts",
    "validation_starts",
    "eval_starts",
    "omitted_starts",
    "omitted_reasons",
    "outside_fold_starts",
    "eval_target_months",
    "train_mean_method",
    "evaluation_splits",
    "evidence_role",
)


def _normalize_fold(value: Any, label: str) -> Optional[str]:
    """Return a valid explicit fold label, ``None`` when unset, or fail."""
    if value is None:
        return None
    if not isinstance(value, str) or value not in protocol.FOLD_NAMES:
        raise CheckError(
            f"{label} declares unknown fold {value!r}; expected "
            f"{list(protocol.FOLD_NAMES)} (main runs have no fold field)"
        )
    return value


def _fold_block(document: Any, label: str) -> Optional[Dict[str, Any]]:
    """Return a document's ``fold`` object, ``None`` when absent, or fail."""
    if not isinstance(document, Mapping) or "fold" not in document:
        return None
    block = document["fold"]
    if not isinstance(block, Mapping):
        raise CheckError(f"{label} fold metadata must be a JSON object")
    return dict(block)


def _expected_mask_keys(definition: protocol.SplitDefinition) -> set:
    return {
        definition.constant_mask_key,
        definition.nonzero_activity_key,
        "has_nonself_neighbor",
        *definition.activity_mask_keys,
    }


def _mean_artifact(
    definition: protocol.SplitDefinition,
) -> Tuple[str, str, str]:
    """Return ``(relative path, NPZ key, node-errors column)`` for the mean."""
    if definition.is_main:
        return "models/TrainMean27.npz", "train_mean27", "train_mean27"
    return (
        f"models/{definition.train_mean_method}.npz",
        f"train_mean{definition.fitting_month_count}",
        definition.train_mean_column,
    )


def _block_consistency(
    block: Mapping[str, Any],
    source: str,
    expected: Mapping[str, Any],
) -> None:
    """Require a fold block to carry exactly the fixed definition payload."""
    missing = [field for field in _FOLD_BLOCK_FIELDS if field not in block]
    if missing:
        raise CheckError(f"{source} fold metadata is missing field(s) {missing}")
    for field in _FOLD_BLOCK_FIELDS:
        actual = block.get(field)
        wanted = expected[field]
        if field in ("omitted_reasons",):
            if not isinstance(actual, Mapping):
                raise CheckError(f"{source} omitted_reasons must be an object")
            actual = {str(key): value for key, value in actual.items()}
            wanted = {str(key): value for key, value in wanted.items()}
        if actual != wanted:
            raise CheckError(
                f"{source} fold field {field!r} is {actual!r}, expected {wanted!r}"
            )


def _validate_fold_windows(
    windows: Mapping[str, Any], definition: protocol.SplitDefinition
) -> None:
    """Cross-check all 28 saved window roles and months for a fold."""
    expected = definition.to_payload()
    for field in (
        "fold",
        "fitting_observation_months",
        "fitting_month_count",
        "omitted_starts",
        "outside_fold_starts",
        "eval_target_months",
    ):
        if windows.get(field) != expected[field]:
            raise CheckError(
                f"windows.json {field!r} is {windows.get(field)!r}, expected "
                f"{expected[field]!r}"
            )
    reasons = windows.get("omitted_reasons")
    if not isinstance(reasons, Mapping) or {
        str(key): value for key, value in reasons.items()
    } != {str(key): value for key, value in expected["omitted_reasons"].items()}:
        raise CheckError("windows.json omitted_reasons disagree with the fixed fold")
    splits = windows.get("splits")
    if not isinstance(splits, Mapping):
        raise CheckError("windows.json is missing its splits object")
    from_splits = {
        "train": expected["train_starts"],
        "validation": expected["validation_starts"],
        definition.evaluation_split: expected["eval_starts"],
    }
    if set(splits) != set(from_splits):
        raise CheckError(
            f"windows.json split names {sorted(splits)} do not match "
            f"{sorted(from_splits)}"
        )
    for name, starts in from_splits.items():
        if list(splits.get(name, [])) != list(starts):
            raise CheckError(
                f"windows.json {name} starts {splits.get(name)!r} differ from "
                f"{starts!r}"
            )
    entries = windows.get("windows")
    if not isinstance(entries, list) or len(entries) != protocol.N_WINDOWS:
        raise CheckError(
            f"windows.json must list all {protocol.N_WINDOWS} windows with roles"
        )
    seen: set = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise CheckError("windows.json window entries must be objects")
        start = entry.get("start")
        if not isinstance(start, int) or not 0 <= start < protocol.N_WINDOWS:
            raise CheckError(f"windows.json has an invalid window start {start!r}")
        if start in seen:
            raise CheckError(f"windows.json repeats window start {start}")
        seen.add(start)
        role = definition.role_for_start(start)
        if entry.get("role") != role:
            raise CheckError(
                f"window {start} role is {entry.get('role')!r}, expected {role!r}"
            )
        reason = definition.reason_for_start(start)
        if entry.get("reason") != reason:
            raise CheckError(
                f"window {start} reason is {entry.get('reason')!r}, expected {reason!r}"
            )
        if list(entry.get("input_months", [])) != list(
            protocol.window_input_months(start)
        ):
            raise CheckError(f"window {start} input months are inconsistent")
        if list(entry.get("target_months", [])) != list(
            protocol.window_target_months(start)
        ):
            raise CheckError(f"window {start} target months are inconsistent")
        if entry.get("forecast_origin") != protocol.window_forecast_origin(start):
            raise CheckError(f"window {start} forecast origin is inconsistent")
    if seen != set(protocol.ALL_STARTS):
        raise CheckError("windows.json does not cover every window start")


def _validate_main_windows(windows: Mapping[str, Any]) -> None:
    """Accept only the historical, consistent main-split window record."""
    splits = windows.get("splits")
    if not isinstance(splits, Mapping):
        raise CheckError("windows.json is missing its splits object")
    if set(splits) != set(protocol.SPLITS):
        raise CheckError(
            f"main run windows.json split names {sorted(splits)} do not match "
            f"{sorted(protocol.SPLITS)}; a fold/eval record without fold "
            "metadata is rejected instead of falling back to main"
        )
    for name, starts in protocol.SPLITS.items():
        if list(splits.get(name, [])) != list(starts):
            raise CheckError(
                f"main run {name} starts {splits.get(name)!r} differ from "
                f"{list(starts)!r}"
            )
    if list(windows.get("omitted_starts", [])) != list(protocol.OMITTED_STARTS):
        raise CheckError("main run omitted starts differ from the fixed split")
    entries = windows.get("windows")
    if not isinstance(entries, list) or len(entries) != protocol.N_WINDOWS:
        raise CheckError(
            f"windows.json must list all {protocol.N_WINDOWS} windows"
        )
    role_by_start = {
        start: name for name, starts in protocol.SPLITS.items() for start in starts
    }
    for entry in entries:
        start = entry.get("start") if isinstance(entry, Mapping) else None
        if not isinstance(start, int):
            raise CheckError("windows.json has an invalid window start")
        expected_split = role_by_start.get(start)
        if entry.get("split") != expected_split:
            raise CheckError(
                f"main window {start} split is {entry.get('split')!r}, expected "
                f"{expected_split!r}"
            )


def _validate_saved_methods(
    run_dir: Path, identity: Dict[str, Any]
) -> None:
    """Check saved method names, split files and forbidden fold/main mixing."""
    definition = identity["definition"]
    predictions_root = run_dir / "predictions"
    if not predictions_root.is_dir():
        raise CheckError(f"required predictions directory is missing: {predictions_root}")
    methods = sorted(
        path.name for path in predictions_root.iterdir() if path.is_dir()
    )
    required = list(definition.naive_methods) + [protocol.MODEL_NAME]
    optional = {protocol.CLIPPED_MODEL_NAME}
    missing = [name for name in required if name not in methods]
    if missing:
        raise CheckError(f"predictions are missing required method(s) {missing}")
    unknown = [name for name in methods if name not in required and name not in optional]
    if unknown:
        raise CheckError(f"predictions contain unknown method(s) {unknown}")
    if definition.is_main:
        if (run_dir / "gold" / "eval.npy").exists():
            raise CheckError("main run contains an eval gold file")
        for method in methods:
            if (predictions_root / method / "eval.npy").exists():
                raise CheckError(
                    f"main run prediction {method}/eval.npy must not exist"
                )
        if (run_dir / "models" / "TrainMean27.npz").exists() is False:
            raise CheckError("main run is missing models/TrainMean27.npz")
    else:
        if "TrainMean27" in methods:
            raise CheckError("fold run must not reuse the TrainMean27 method name")
        if (run_dir / "gold" / "test.npy").exists():
            raise CheckError("fold run must not write gold/test.npy")
        if (run_dir / "models" / "TrainMean27.npz").exists():
            raise CheckError("fold run must not reuse models/TrainMean27.npz")
        for method in methods:
            if (predictions_root / method / "test.npy").exists():
                raise CheckError(
                    f"fold run prediction {method}/test.npy must not exist"
                )
    for split in definition.evaluation_splits:
        gold_path = run_dir / "gold" / f"{split}.npy"
        if not gold_path.is_file():
            raise CheckError(f"required gold file is missing: {gold_path}")
        for method in methods:
            if not (predictions_root / method / f"{split}.npy").is_file():
                raise CheckError(
                    f"prediction is missing: {predictions_root / method / f'{split}.npy'}"
                )
    if not definition.is_main:
        # Fold evidence must be internally complete before recomputation; a
        # historical main report keeps its existing mismatch semantics for a
        # deleted method record, so its comparison is left to recompute.
        stored_methods = identity["metrics"].get("methods")
        if not isinstance(stored_methods, Mapping) or set(stored_methods) != set(
            definition.evaluation_splits
        ):
            raise CheckError(
                "fold metrics.json method splits do not match the resolved split: "
                f"{sorted(stored_methods) if isinstance(stored_methods, Mapping) else stored_methods!r}"
            )
        for split in definition.evaluation_splits:
            if set(stored_methods.get(split, {})) != set(methods):
                raise CheckError(
                    f"fold metrics.json {split} methods "
                    f"{sorted(stored_methods.get(split, {}))} differ from saved "
                    f"predictions {methods}"
                )
    identity["methods"] = methods


def _validate_saved_mean(
    run_dir: Path, identity: Dict[str, Any]
) -> None:
    """Check the fitting-scope frozen mean artifact and its identity key."""
    definition = identity["definition"]
    relative, key, column = _mean_artifact(definition)
    path = run_dir / relative
    if not path.is_file():
        raise CheckError(f"required fitting mean artifact is missing: {path}")
    with np.load(path, allow_pickle=False) as handle:
        if key not in handle:
            raise CheckError(
                f"{relative} is missing its fitting-mean key {key!r}; "
                f"present keys: {sorted(handle.files)}"
            )
        if "train_observation_month_count" in handle:
            count = int(np.asarray(handle["train_observation_month_count"]).reshape(-1)[0])
            if count != definition.fitting_month_count:
                raise CheckError(
                    f"{relative} records {count} fitting months, expected "
                    f"{definition.fitting_month_count}"
                )
    identity["mean_relative_path"] = relative
    identity["mean_key"] = key
    identity["mean_column"] = column


def _validate_fold_mask_semantics(identity: Dict[str, Any]) -> None:
    """Reject saved fold masks that contradict their own activity fractions.

    ``nonzero_activity_fit18/21`` is a continuous fraction of the unique fold
    fitting observations; the four boolean activity masks must be exactly the
    protocol groups derived from those fractions (0, (0,1/3], (1/3,2/3],
    (2/3,1]).  The constant mask must be a boolean node mask of the same shape.
    These are fixed protocol semantics, so a saved contradiction is invalid
    evidence even when recomputation reproduces the same wrong numbers.
    """
    definition = identity["definition"]
    masks = identity["masks"]
    activity = np.asarray(masks[definition.nonzero_activity_key])
    if activity.ndim != 1:
        raise CheckError(
            f"{definition.nonzero_activity_key} must be a one-dimensional node mask"
        )
    if not np.issubdtype(activity.dtype, np.floating):
        raise CheckError(
            f"{definition.nonzero_activity_key} must store floating-point "
            f"fractions, got {activity.dtype}"
        )
    if not np.isfinite(activity).all():
        raise CheckError(
            f"{definition.nonzero_activity_key} contains non-finite values"
        )
    if (activity < 0.0).any() or (activity > 1.0).any():
        raise CheckError(
            f"{definition.nonzero_activity_key} values must lie within [0, 1]"
        )
    count = definition.fitting_month_count
    steps = activity * float(count)
    if not np.allclose(steps, np.round(steps), rtol=0.0, atol=1e-9):
        raise CheckError(
            f"{definition.nonzero_activity_key} values are not integer multiples "
            f"of 1/{count} (the unique fitting month count)"
        )
    group_arrays = []
    for name in definition.activity_group_names:
        mask = np.asarray(masks[f"activity_{name}"])
        if mask.dtype != np.bool_:
            raise CheckError(f"activity mask {name} must be boolean, got {mask.dtype}")
        if mask.shape != activity.shape:
            raise CheckError(
                f"activity mask {name} shape {mask.shape} != activity shape "
                f"{activity.shape}"
            )
        group_arrays.append(mask)
    partition = np.stack(group_arrays).sum(axis=0)
    if not np.array_equal(partition, np.ones(activity.shape[0], dtype=partition.dtype)):
        raise CheckError(
            "fold activity masks must partition every node exactly once; observed "
            f"multiplicities {sorted(set(int(value) for value in partition))}"
        )
    constant = np.asarray(masks[definition.constant_mask_key])
    if constant.dtype != np.bool_:
        raise CheckError(
            f"{definition.constant_mask_key} must be boolean, got {constant.dtype}"
        )
    if constant.shape != activity.shape:
        raise CheckError(
            f"{definition.constant_mask_key} shape {constant.shape} != activity shape "
            f"{activity.shape}"
        )
    derived = activity_group_masks(activity)
    for raw_name, group_name in zip(
        protocol.ACTIVITY_GROUP_NAMES, definition.activity_group_names
    ):
        saved = np.asarray(masks[f"activity_{group_name}"], dtype=bool)
        expected = np.asarray(derived[raw_name], dtype=bool)
        if not np.array_equal(saved, expected):
            mismatch = int((saved != expected).sum())
            raise CheckError(
                f"activity mask {group_name} disagrees with "
                f"{definition.nonzero_activity_key} at the fixed group boundaries "
                f"for {mismatch} node(s)"
            )


def _validate_saved_masks(run_dir: Path, identity: Dict[str, Any]) -> None:
    """Check every mask key and load the masks for later use."""
    masks = _load_npz(run_dir / "masks.npz")
    expected = _expected_mask_keys(identity["definition"])
    if set(masks) != expected:
        raise CheckError(
            f"masks.npz keys {sorted(masks)} do not match the resolved split "
            f"contract {sorted(expected)}"
        )
    identity["masks"] = masks
    if not identity["definition"].is_main:
        _validate_fold_mask_semantics(identity)


def _validate_fold_selection(identity: Dict[str, Any]) -> None:
    """Cross-check the saved selection record against the fold definition."""
    selection = identity.get("selection")
    if not isinstance(selection, Mapping):
        raise CheckError("fold run is missing selection.json")
    definition = identity["definition"]
    normalization = selection.get("normalization")
    if not isinstance(normalization, Mapping):
        raise CheckError("selection.json is missing its normalization record")
    if list(normalization.get("train_observation_months", [])) != list(
        definition.fitting_observation_months
    ):
        raise CheckError(
            "selection.json normalization months disagree with the fold fitting "
            "period"
        )
    if normalization.get("fitting_month_count") != definition.fitting_month_count:
        raise CheckError(
            "selection.json fitting_month_count disagrees with the fold definition"
        )
    if normalization.get("train_mean_method") != definition.train_mean_method:
        raise CheckError(
            "selection.json TrainMean method disagrees with the fold definition"
        )
    if normalization.get("ddof") != 0:
        raise CheckError(
            "selection.json normalization.ddof must be 0 for the fixed fold "
            f"statistics, got {normalization.get('ddof')!r}"
        )
    if normalization.get("constant_node_std") != 1.0:
        raise CheckError(
            "selection.json normalization.constant_node_std must be 1.0, got "
            f"{normalization.get('constant_node_std')!r}"
        )
    if normalization.get("applied_to_inputs_and_targets") is not True:
        raise CheckError(
            "selection.json must record normalization applied to inputs and targets"
        )
    if normalization.get("activity_scope") != definition.scope_label:
        raise CheckError(
            "selection.json activity_scope disagrees with the fold fitting scope"
        )
    references = selection.get("naive_references")
    if not isinstance(references, Mapping):
        raise CheckError("selection.json is missing naive_references")
    if list(references.get("table_order", [])) != list(definition.naive_methods):
        raise CheckError(
            "selection.json naive method order disagrees with the fold definition"
        )
    scores = selection.get("naive_validation_scores")
    if not isinstance(scores, Mapping) or set(scores) != set(definition.naive_methods):
        raise CheckError(
            "selection.json naive validation scores do not cover the five fold methods"
        )
    if references.get("NaiveRef") not in definition.naive_methods:
        raise CheckError("selection.json NaiveRef is not a fold candidate")
    if references.get("NaiveRef6") not in definition.naive_ref6_methods:
        raise CheckError("selection.json NaiveRef6 is not a fold candidate")
    shared = selection.get("shared_ridge")
    if not isinstance(shared, Mapping):
        raise CheckError("selection.json is missing shared_ridge")
    table = shared.get("candidate_table")
    if not isinstance(table, list) or len(table) != len(protocol.LAMBDA_CANDIDATES):
        raise CheckError(
            "selection.json must retain every Ridge candidate score row"
        )
    lambdas = sorted(float(row.get("lambda")) for row in table)
    if lambdas != sorted(float(value) for value in protocol.LAMBDA_CANDIDATES):
        raise CheckError(
            f"selection.json candidate lambdas {lambdas} differ from the fixed "
            f"candidates {list(protocol.LAMBDA_CANDIDATES)}"
        )
    if selection.get("test_labels_used_for_selection") is not False:
        raise CheckError(
            "selection.json must explicitly record "
            "test_labels_used_for_selection=false"
        )


def resolve_saved_split(
    run_dir: Path,
    *,
    metrics: Any = None,
    windows: Any = None,
    config: Any = None,
    provenance: Any = None,
    selection: Any = None,
) -> Dict[str, Any]:
    """Resolve and cross-validate the saved split identity of a run.

    A historical main run (no fold/eval field anywhere) resolves to the main
    split only when its window record is the consistent main format.  Any
    explicit fold label, fold block or eval artifact requires complete fold
    metadata from every writer; unknown, missing or contradictory evidence
    fails rather than falling back to main.
    """
    run_dir = Path(run_dir)
    if metrics is None:
        metrics = _read_json(run_dir / "metrics.json")
    if windows is None:
        windows = _read_json(run_dir / "windows.json")
    if config is None:
        config = _read_optional_json(run_dir / "config.json")
    if provenance is None:
        provenance = _read_optional_json(run_dir / "provenance.json")
    if selection is None:
        selection = _read_optional_json(run_dir / "selection.json")
    if not isinstance(metrics, Mapping):
        raise CheckError("metrics.json must be a JSON object")
    if not isinstance(windows, Mapping):
        raise CheckError("windows.json must be a JSON object")

    spec_fold = None
    if isinstance(config, Mapping) and isinstance(config.get("spec"), Mapping):
        spec_fold = _normalize_fold(
            config["spec"].get("fold"), "config.json spec.fold"
        )
    blocks = {
        "config.json": _fold_block(config, "config.json"),
        "provenance.json": _fold_block(provenance, "provenance.json"),
        "metrics.json": _fold_block(metrics, "metrics.json"),
        "selection.json": _fold_block(selection, "selection.json"),
    }
    block_folds = {
        source: _normalize_fold(block.get("fold"), f"{source} fold")
        for source, block in blocks.items()
        if block is not None
    }
    windows_fold = None
    if "fold" in windows:
        windows_fold = _normalize_fold(windows.get("fold"), "windows.json fold")
    clues = {
        "config.json spec.fold": spec_fold,
        **block_folds,
        "windows.json fold": windows_fold,
    }
    present = {source: value for source, value in clues.items() if value is not None}

    if present:
        labels = sorted(set(present.values()))
        if len(labels) > 1:
            raise CheckError(
                f"saved fold labels contradict each other: {present}"
            )
        fold = labels[0]
        missing = [
            source
            for source in (
                "config.json spec.fold",
                "config.json",
                "provenance.json",
                "metrics.json",
                "selection.json",
                "windows.json fold",
            )
            if source not in present
        ]
        if missing:
            raise CheckError(
                f"fold {fold} evidence is incomplete; missing fold metadata in "
                f"{missing}"
            )
        block_incomplete = [
            source
            for source, block in blocks.items()
            if block is not None and block.get("fold") is None
        ]
        if block_incomplete:
            raise CheckError(
                f"fold {fold} evidence is incomplete; fold label missing in "
                f"{block_incomplete}"
            )
        definition = protocol.resolve_split(fold)
        definition.validate()
        expected = definition.to_payload()
        for source, block in blocks.items():
            if block is not None:
                _block_consistency(block, source, expected)
        _validate_fold_windows(windows, definition)
        if isinstance(config, Mapping) and isinstance(config.get("spec"), Mapping):
            if config["spec"].get("fold") != fold:
                raise CheckError("config.json spec.fold disagrees with the run fold")
        identity = {
            "fold": fold,
            "is_fold": True,
            "definition": definition,
            "eval_split": definition.evaluation_split,
            "evaluation_splits": list(definition.evaluation_splits),
            "metrics": metrics,
            "windows": windows,
            "config": config,
            "provenance": provenance,
            "selection": selection,
            "evidence_role": expected.get("evidence_role"),
        }
        _validate_fold_selection(identity)
        _validate_saved_methods(run_dir, identity)
        _validate_saved_mean(run_dir, identity)
        _validate_saved_masks(run_dir, identity)
        return identity

    present_blocks = [source for source, block in blocks.items() if block is not None]
    if present_blocks:
        raise CheckError(
            "saved fold metadata is present without a usable fold label in "
            f"{present_blocks}"
        )
    # No fold metadata: reject an eval trace instead of silently using main.
    stored_methods = metrics.get("methods")
    eval_traces: List[str] = []
    if isinstance(stored_methods, Mapping) and "eval" in stored_methods:
        eval_traces.append("metrics.json methods.eval")
    if "eval" in (windows.get("splits") or {}):
        eval_traces.append("windows.json splits.eval")
    if (run_dir / "gold" / "eval.npy").exists():
        eval_traces.append("gold/eval.npy")
    predictions_root = run_dir / "predictions"
    if predictions_root.is_dir():
        for method_dir in predictions_root.iterdir():
            if method_dir.is_dir() and (method_dir / "eval.npy").exists():
                eval_traces.append(f"predictions/{method_dir.name}/eval.npy")
    if eval_traces:
        raise CheckError(
            "eval evidence exists without fold metadata; refusing to fall back "
            f"to main: {eval_traces}"
        )
    _validate_main_windows(windows)
    identity = {
        "fold": None,
        "is_fold": False,
        "definition": protocol.MAIN_SPLIT,
        "eval_split": "test",
        "evaluation_splits": ["validation", "test"],
        "metrics": metrics,
        "windows": windows,
        "config": config,
        "provenance": provenance,
        "selection": selection,
        "evidence_role": None,
    }
    _validate_saved_methods(run_dir, identity)
    _validate_saved_mean(run_dir, identity)
    _validate_saved_masks(run_dir, identity)
    return identity


def _validate_split_against_nodes(
    identity: Dict[str, Any], node_count: int
) -> None:
    """Cross-check node-count-dependent saved identities after loading nodes."""
    definition = identity["definition"]
    expected_m = protocol.expected_train_sample_count(node_count, definition)
    selection = identity.get("selection")
    if isinstance(selection, Mapping) and "training_samples_M" in selection:
        if int(selection.get("training_samples_M")) != expected_m:
            raise CheckError(
                f"selection.json training_samples_M is {selection.get('training_samples_M')}, "
                f"expected {expected_m} for {definition.name}"
            )
        if int(selection.get("expected_training_samples_M", expected_m)) != expected_m:
            raise CheckError(
                "selection.json expected_training_samples_M disagrees with the "
                "resolved split"
            )
        table = selection.get("shared_ridge", {}).get("candidate_table", [])
        for row in table:
            if int(row.get("M")) != expected_m:
                raise CheckError(
                    f"selection.json candidate M {row.get('M')} != {expected_m}"
                )
    masks = identity.get("masks") or {}
    for name, mask in masks.items():
        array = np.asarray(mask)
        if array.shape != (int(node_count),):
            raise CheckError(
                f"mask {name} shape {array.shape} != ({int(node_count)},)"
            )
    mean_path = identity.get("mean_relative_path")
    if mean_path:
        with np.load(
            Path(identity["run_dir"]) / mean_path, allow_pickle=False
        ) as handle:
            mean = np.asarray(handle[identity["mean_key"]]).reshape(-1)
        if mean.shape != (int(node_count),):
            raise CheckError(
                f"{mean_path} mean shape {mean.shape} != ({int(node_count)},)"
            )


# ---------------------------------------------------------------------------
# recompute
# ---------------------------------------------------------------------------
RECOMPUTE_CONSUMED_INPUTS = (
    "metrics.json",
    "nodes.parquet",
    "masks.npz",
    "windows.json",
    "gold/validation.npy",
    "gold/test.npy",
    "status.json",
    "node-errors.parquet",
    "models/TrainMean27.npz",
)

RECOMPUTE_TOLERANCES = {
    "metric_relative": DIAGNOSTIC_RELATIVE_TOLERANCE,
    "definition": "abs(a-b) / max(1, abs(a), abs(b))",
}


def _recompute_consumed_inputs(identity: Mapping[str, Any]) -> Tuple[str, ...]:
    """Return exactly the saved artifacts one recomputation reads."""
    definition = identity["definition"]
    mean_relative, _, _ = _mean_artifact(definition)
    return (
        "config.json",
        "provenance.json",
        "selection.json",
        "status.json",
        "metrics.json",
        "windows.json",
        "nodes.parquet",
        "masks.npz",
        "gold/validation.npy",
        f"gold/{definition.evaluation_split}.npy",
        "node-errors.parquet",
        mean_relative,
    )


def command_recompute(
    *,
    run_dir: Path,
    repo_root: Path,
    command: Sequence[str],
    report_path: Optional[Path] = None,
    run_id: Optional[str] = None,
    runs_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Recompute every saved metric from a completed run directory only.

    The explicit ``report_path`` and the legacy ``run_id``/``runs_root`` alias
    are mutually exclusive and one is required; both produce one JSON report.
    Main and fold A/B evidence are dispatched by the validated saved identity;
    source demand, graph data and model fitting are never read or invoked.
    """
    run_dir = Path(run_dir)
    destination = resolve_report_path(
        report_path=report_path, run_id=run_id, runs_root=runs_root, repo_root=repo_root
    )
    _reject_unsafe_destination(destination, [("run", run_dir, "dir")])
    inputs: Dict[str, Any] = {"input_run_dir": str(run_dir)}
    try:
        if not run_dir.exists():
            raise CheckError(f"input run directory does not exist: {run_dir}")
        status = _read_json(run_dir / "status.json")
        if not isinstance(status, Mapping):
            raise CheckError(
                f"required artifact is not a status object: {run_dir / 'status.json'}"
            )
        metrics_document = _read_json(run_dir / "metrics.json")
        windows_meta = _read_json(run_dir / "windows.json")
        identity = resolve_saved_split(
            run_dir,
            metrics=metrics_document,
            windows=windows_meta,
            config=_read_optional_json(run_dir / "config.json"),
            provenance=_read_optional_json(run_dir / "provenance.json"),
            selection=_read_optional_json(run_dir / "selection.json"),
        )
        identity["run_dir"] = str(run_dir)
        definition = identity["definition"]
        inputs["input_run_id"] = status.get("run_id")
        inputs["input_status"] = status.get("state")
        inputs["fold"] = identity["fold"]
        inputs["evaluation_splits"] = list(identity["evaluation_splits"])
        inputs["consumed_sha256"] = _hash_tree(
            run_dir, _recompute_consumed_inputs(identity)
        )
        nodes = _read_nodes(run_dir / "nodes.parquet")
        key_columns = [column for column in nodes.columns if column != "node_index"]
        node_count = len(nodes)
        _validate_split_against_nodes(identity, node_count)
        masks = identity["masks"]
        activity_masks = {
            group_name: masks[f"activity_{group_name}"]
            for group_name in definition.activity_group_names
        }
        constant_masks = metrics.constant_group_masks(
            masks[definition.constant_mask_key], scope=definition.scope_label
        )
        neighbor_masks = {
            "has_nonself_neighbor": masks["has_nonself_neighbor"],
            "no_nonself_neighbor": ~masks["has_nonself_neighbor"],
        }
        context_values = nodes[key_columns[0]].to_numpy()
        context_masks_map = metrics.context_masks(context_values)

        recomputed: Dict[str, Dict[str, Any]] = {
            split: {} for split in definition.evaluation_splits
        }
        for split in definition.evaluation_splits:
            gold = _load_npy(run_dir / "gold" / f"{split}.npy")
            starts = definition.starts_for(split)
            for method in identity["methods"]:
                pred = _load_npy(run_dir / "predictions" / method / f"{split}.npy")
                if pred.shape != gold.shape:
                    raise CheckError(
                        f"{method}/{split}: prediction shape {pred.shape} != gold {gold.shape}"
                    )
                if pred.ndim != 3 or pred.shape[1] != node_count:
                    raise CheckError(
                        f"{method}/{split}: node axis {pred.shape} != {node_count} nodes"
                    )
                recomputed[split][method] = metrics.split_report(
                    pred,
                    gold,
                    starts=starts,
                    activity_masks=activity_masks,
                    constant_masks=constant_masks,
                    context_masks_map=context_masks_map,
                    neighbor_masks=neighbor_masks,
                    group_names=definition.activity_group_names,
                    inactive_group_name=definition.activity_group_names[0],
                )
        inputs["consumed_prediction_sha256"] = {
            f"predictions/{method}/{split}.npy": sha256_file(
                run_dir / "predictions" / method / f"{split}.npy"
            )
            for split in definition.evaluation_splits
            for method in identity["methods"]
        }
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
        for split in definition.evaluation_splits:
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
                for method in identity["methods"]
                if method not in definition.naive_methods
            ]
            reference_names = [
                name
                for name in (
                    references.get("NaiveRef"),
                    references.get("NaiveRef6"),
                )
                if name is not None
            ]
            for split in definition.evaluation_splits:
                recomputed_gains[split] = metrics.baseline_relative_comparison(
                    recomputed[split],
                    activity_groups=definition.activity_group_names,
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
        # error sums and fitting-scope columns against saved predictions.
        node_error_comparison = _compare_node_error_tables(
            run_dir, key_columns, identity
        )

        failed = [
            split
            for split, comparison in comparisons.items()
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
        result = {
            "check": "recompute",
            "input_run_dir": str(run_dir),
            "fold": identity["fold"],
            "evaluation_splits": list(definition.evaluation_splits),
            "methods": list(identity["methods"]),
            "saved_split": {
                "fold": identity["fold"],
                "fitting_month_count": definition.fitting_month_count,
                "train_mean_method": definition.train_mean_method,
                "mean_artifact": identity["mean_relative_path"],
                "activity_group_names": list(definition.activity_group_names),
                "constant_group_names": list(definition.constant_group_names),
                "consumed_mask_keys": sorted(identity["masks"]),
            },
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
            "recomputed_metrics": recomputed,
            "recomputed_relative_gains": recomputed_gains,
            "source_data_read": False,
            "model_refit": False,
        }
        result["status"] = "ok" if not failed else "mismatch"
        envelope = _envelope(
            "recompute",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=RECOMPUTE_TOLERANCES,
            status=result["status"],
            result=result,
            errors=[],
        )
    except BaseException as exc:  # noqa: BLE001 - a usable destination still gets a report
        envelope = _failure_envelope(
            "recompute",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=RECOMPUTE_TOLERANCES,
            exc=exc,
        )
    return _finish(destination, envelope)


def _read_nodes(path: Path) -> "Any":
    import pandas as pd

    if not path.exists():
        raise CheckError(f"required artifact is missing: {path}")
    return pd.read_parquet(path)


def _compare_node_error_tables(
    run_dir: Path,
    key_columns: Sequence[str],
    identity: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Verify the saved per-node diagnostic table against saved arrays.

    Main runs keep the historical ``train_mean27`` columns.  Fold runs require
    the fitting-scope mean, activity, activity-group and constant columns and
    compare them to the same saved masks used by the metric reports.
    """
    import pandas as pd

    definition = (
        identity["definition"] if identity is not None else protocol.MAIN_SPLIT
    )
    mean_relative, mean_key, mean_column = _mean_artifact(definition)
    is_fold = not definition.is_main
    activity_column = f"activity_{definition.scope_label}"
    group_column = f"activity_group_{definition.scope_label}"
    constant_column = f"constant_{definition.scope_label}"
    stored_path = run_dir / "node-errors.parquet"
    if not stored_path.exists():
        return {
            "status": "mismatch",
            "reason": "node-errors.parquet is missing",
            "compared_rows": 0,
        }
    statistics_path = run_dir / mean_relative
    if not statistics_path.exists():
        return {
            "status": "mismatch",
            "reason": f"{mean_relative} is missing",
            "compared_rows": 0,
        }
    with np.load(statistics_path, allow_pickle=False) as handle:
        if mean_key not in handle:
            return {
                "status": "mismatch",
                "reason": f"{mean_relative} is missing its {mean_key} statistics",
                "compared_rows": 0,
            }
        train_mean = np.asarray(handle[mean_key], dtype=np.float64).reshape(-1)
    nodes = _read_nodes(run_dir / "nodes.parquet")
    keys = nodes[list(key_columns)].to_numpy()
    context_values = nodes[list(key_columns)[0]].to_numpy()
    masks = (
        identity.get("masks")
        if identity is not None
        else _load_npz(run_dir / "masks.npz")
    )
    activity_values = None
    group_values = None
    constant_values = None
    if is_fold:
        activity_values = np.asarray(
            masks[definition.nonzero_activity_key], dtype=np.float64
        )
        constant_values = np.asarray(
            masks[definition.constant_mask_key], dtype=bool
        )
        group_values = np.full(len(nodes), "", dtype=object)
        for group_name in definition.activity_group_names:
            group_values[
                np.asarray(masks[f"activity_{group_name}"], dtype=bool)
            ] = group_name
    frames = []
    for split in definition.evaluation_splits:
        gold = _load_npy(run_dir / "gold" / f"{split}.npy")
        for method in sorted(
            path.name for path in (run_dir / "predictions").iterdir() if path.is_dir()
        ):
            method_dir = run_dir / "predictions" / method
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
                    train_mean_column=mean_column,
                    activity_values=activity_values,
                    activity_column=activity_column if is_fold else None,
                    activity_group_values=group_values if is_fold else None,
                    activity_group_column=group_column if is_fold else None,
                    constant_values=constant_values if is_fold else None,
                    constant_column=constant_column if is_fold else None,
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
        mean_column,
        *key_columns,
    ]
    if is_fold:
        required_columns.extend(
            [activity_column, group_column, constant_column]
        )
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
    numeric_columns = [
        "absolute_error_sum",
        "squared_error_sum",
        "elements",
        "MAE",
        "MSE",
        mean_column,
    ]
    if is_fold:
        numeric_columns.append(activity_column)
    nonfinite_fields: List[str] = []
    for column in numeric_columns:
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
    for column in numeric_columns:
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
    categorical_mismatches = 0
    if is_fold:
        stored_constant = both[f"{constant_column}_stored"].to_numpy()
        recomputed_constant = both[f"{constant_column}_recomputed"].to_numpy()
        categorical_mismatches += int(
            (stored_constant.astype(bool) != recomputed_constant.astype(bool)).sum()
        )
        stored_groups = both[f"{group_column}_stored"].astype(str).to_numpy()
        recomputed_groups = both[f"{group_column}_recomputed"].astype(str).to_numpy()
        categorical_mismatches += int((stored_groups != recomputed_groups).sum())
    status = (
        "ok"
        if failed_fields == 0
        and categorical_mismatches == 0
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
        "categorical_mismatches": categorical_mismatches,
        "nonfinite_fields": nonfinite_fields,
        "max_normalized_difference": worst,
        "max_difference_column": worst_column,
        "mean_column": mean_column,
        "activity_column": activity_column if is_fold else None,
        "activity_group_column": group_column if is_fold else None,
        "constant_column": constant_column if is_fold else None,
        "tolerance": DIAGNOSTIC_RELATIVE_TOLERANCE,
    }


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------
def _compare_consumed_inputs(identity: Mapping[str, Any]) -> Tuple[str, ...]:
    """Return the saved artifacts the resolved comparison actually reads.

    The fold-specific frozen mean and the window/provenance metadata that decide
    the split identity are part of the consumed evidence, not just the generic
    config/environment/mask files.
    """
    mean_relative, _, _ = _mean_artifact(identity["definition"])
    return (
        "metrics.json",
        "selection.json",
        "source-sha256.json",
        "config.json",
        "environment.json",
        "masks.npz",
        "status.json",
        "windows.json",
        "provenance.json",
        mean_relative,
    )

COMPARE_TOLERANCES = {
    "cpu_relative": CPU_RELATIVE_TOLERANCE,
    "definition": "abs(a-b) / max(1, abs(a), abs(b))",
}


def command_compare(
    *,
    run_a: Path,
    run_b: Path,
    repo_root: Path,
    command: Sequence[str],
    report_path: Optional[Path] = None,
    run_id: Optional[str] = None,
    runs_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Compare two same-seed runs and apply the CPU agreement criterion."""
    run_a, run_b = Path(run_a), Path(run_b)
    destination = resolve_report_path(
        report_path=report_path, run_id=run_id, runs_root=runs_root, repo_root=repo_root
    )
    _reject_unsafe_destination(
        destination,
        [("run-a", run_a, "dir"), ("run-b", run_b, "dir")],
    )
    inputs: Dict[str, Any] = {
        "run_a": str(run_a),
        "run_b": str(run_b),
    }
    try:
        for label, run_dir in (("a", run_a), ("b", run_b)):
            if not run_dir.exists():
                raise CheckError(f"run {label} does not exist: {run_dir}")
        status_a = _read_json(run_a / "status.json")
        status_b = _read_json(run_b / "status.json")
        # Link the declared execution identities, not only the current input
        # locations: aliased or relocated runs still report their real run IDs.
        inputs["run_a_id"] = status_a.get("run_id")
        inputs["run_b_id"] = status_b.get("run_id")
        inputs["run_a_status"] = status_a.get("state")
        inputs["run_b_status"] = status_b.get("state")
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
        windows_a = _read_json(run_a / "windows.json")
        windows_b = _read_json(run_b / "windows.json")
        identity_a = resolve_saved_split(
            run_a,
            metrics=metrics_a,
            windows=windows_a,
            config=config_a,
            provenance=_read_optional_json(run_a / "provenance.json"),
            selection=selection_a,
        )
        identity_b = resolve_saved_split(
            run_b,
            metrics=metrics_b,
            windows=windows_b,
            config=config_b,
            provenance=_read_optional_json(run_b / "provenance.json"),
            selection=selection_b,
        )
        inputs["run_a_fold"] = identity_a["fold"]
        inputs["run_b_fold"] = identity_b["fold"]
        inputs["run_a_consumed_sha256"] = _hash_tree(
            run_a, _compare_consumed_inputs(identity_a)
        )
        inputs["run_b_consumed_sha256"] = _hash_tree(
            run_b, _compare_consumed_inputs(identity_b)
        )

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
                and _equal_present(
                    metrics_a.get("dataset"), metrics_b.get("dataset")
                )
            ),
            "fold": bool(identity_a["fold"] == identity_b["fold"]),
            "evaluation_splits": bool(
                identity_a["evaluation_splits"] == identity_b["evaluation_splits"]
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
        split_a = identity_a["eval_split"]
        split_b = identity_b["eval_split"]
        methods_a_set = set(metrics_a.get("methods", {}).get(split_a, {}))
        methods_b_set = set(metrics_b.get("methods", {}).get(split_b, {}))
        methods_equal = methods_a_set == methods_b_set
        methods = sorted(methods_a_set | methods_b_set)
        missing_methods = {
            "run_a": sorted(methods_b_set - methods_a_set),
            "run_b": sorted(methods_a_set - methods_b_set),
        }
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
        for split in identity_a["evaluation_splits"]:
            for method in methods:
                path_a = run_a / "predictions" / method / f"{split}.npy"
                path_b = run_b / "predictions" / method / f"{split}.npy"
                if not path_a.is_file() or not path_b.is_file():
                    prediction_comparisons[f"{split}/{method}"] = {
                        "status": "missing_method",
                        "run_a_file": path_a.is_file(),
                        "run_b_file": path_b.is_file(),
                    }
                    continue
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
        inputs["consumed_prediction_sha256"] = {}
        for label, run_dir in (("a", run_a), ("b", run_b)):
            for split in identity_a["evaluation_splits"]:
                for method in methods:
                    relative = (
                        Path("predictions") / method / f"{split}.npy"
                    )
                    if (run_dir / relative).is_file():
                        inputs["consumed_prediction_sha256"][
                            f"run_{label}:{relative.as_posix()}"
                        ] = sha256_file(run_dir / relative)
        metric_comparison = compare_number_sets(
            flatten_numbers(metrics_a.get("methods", {})),
            flatten_numbers(metrics_b.get("methods", {})),
            tolerance=CPU_RELATIVE_TOLERANCE,
            label="metrics",
        )
        mae_relative_differences: Dict[str, Any] = {}
        mae_ok = True
        for split in identity_a["evaluation_splits"]:
            for method in methods:
                report_a = metrics_a.get("methods", {}).get(split, {}).get(method, {})
                report_b = metrics_b.get("methods", {}).get(split, {}).get(method, {})
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
            and methods_equal
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
            "fold_a": identity_a["fold"],
            "fold_b": identity_b["fold"],
            "evaluation_splits_a": list(identity_a["evaluation_splits"]),
            "evaluation_splits_b": list(identity_b["evaluation_splits"]),
            "identity_checks": identity_checks,
            "methods_equal": methods_equal,
            "missing_methods": missing_methods,
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
        envelope = _envelope(
            "compare",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=COMPARE_TOLERANCES,
            status=report["status"],
            result=report,
            errors=[],
        )
    except BaseException as exc:  # noqa: BLE001 - a usable destination still gets a report
        envelope = _failure_envelope(
            "compare",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=COMPARE_TOLERANCES,
            exc=exc,
        )
    return _finish(destination, envelope)


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


ALIGN_CONSUMED_INPUTS = (
    "metrics.json",
    "audit.json",
    "windows.json",
    "source-sha256.json",
)

ALIGN_TOLERANCES = {
    "diagnostic_relative": DIAGNOSTIC_RELATIVE_TOLERANCE,
    "definition": "abs(a-b) / max(1, abs(a), abs(b))",
}


def command_align_v2(
    *,
    run_dir: Path,
    reference: Path,
    repo_root: Path,
    command: Sequence[str],
    report_path: Optional[Path] = None,
    run_id: Optional[str] = None,
    runs_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Align a completed run's na\"ive results with the immutable v2 diagnostic."""
    run_dir, reference = Path(run_dir), Path(reference)
    destination = resolve_report_path(
        report_path=report_path, run_id=run_id, runs_root=runs_root, repo_root=repo_root
    )
    _reject_unsafe_destination(
        destination,
        [("run", run_dir, "dir"), ("reference", reference, "file")],
    )
    inputs: Dict[str, Any] = {
        "input_run_dir": str(run_dir),
        "reference_path": str(reference),
    }
    try:
        if not run_dir.exists():
            raise CheckError(f"input run directory does not exist: {run_dir}")
        # Resolve the run's own identity before touching the reference.  A fold
        # is rejected from saved run evidence alone, so a missing, unreadable or
        # fabricated reference can never mask the fold-specific reason.
        metrics_document = _read_json(run_dir / "metrics.json")
        # Link the declared execution identity in addition to the input location.
        inputs["input_run_id"] = metrics_document.get("run_id")
        windows_meta = _read_json(run_dir / "windows.json")
        identity = resolve_saved_split(
            run_dir,
            metrics=metrics_document,
            windows=windows_meta,
            config=_read_optional_json(run_dir / "config.json"),
            provenance=_read_optional_json(run_dir / "provenance.json"),
            selection=_read_optional_json(run_dir / "selection.json"),
        )
        inputs["input_fold"] = identity["fold"]
        if identity["is_fold"]:
            raise CheckError(
                f"align-v2 rejects fold run {identity['fold']}: the immutable v2 "
                "reference has no fold records, so no eval-to-test mapping is "
                "constructed and a fabricated fold reference is not accepted"
            )
        if not reference.exists():
            raise CheckError(f"v2 reference log does not exist: {reference}")
        inputs["input_consumed_sha256"] = _hash_tree(run_dir, ALIGN_CONSUMED_INPUTS)
        reference_sha256 = sha256_file(reference)
        inputs["reference_sha256"] = reference_sha256
        parsed = parse_v2_reference(reference)
        audit = _read_json(run_dir / "audit.json")
        dataset = metrics_document["dataset"]
        bucket = parsed["by_dataset"].get(dataset)
        if bucket is None:
            raise CheckError(
                f"v2 reference log has no records for dataset {dataset!r}"
            )

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
        envelope = _envelope(
            "align-v2",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=ALIGN_TOLERANCES,
            status=report["status"],
            result=report,
            errors=[],
        )
    except BaseException as exc:  # noqa: BLE001 - a usable destination still gets a report
        envelope = _failure_envelope(
            "align-v2",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=ALIGN_TOLERANCES,
            exc=exc,
        )
    return _finish(destination, envelope)
