"""Saved-only verification of one occupation-skill graph audit.

The checker rederives the candidate scores, deterministic selections, union
edges, structural summaries, target mapping counts and trend diagnostics from
the saved training observations.  It never reopens source demand files, never
writes inside the checked input and publishes exactly one exclusive external
report.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from . import artifacts, data, layout, mapping, paths, protocol, scores, structure, trends

__all__ = [
    "CheckError",
    "check_artifact",
]

NUMERIC_RTOL = 1e-12
NUMERIC_ATOL = 1e-12


class CheckError(ValueError):
    """Raised when saved evidence is missing, corrupt or contradictory."""


def _hash_tree(root: Path) -> Dict[str, str]:
    root = Path(root)
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): artifacts.sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _read_json(root: Path, relative: str) -> Any:
    path = root / relative
    if not path.is_file():
        raise CheckError(f"required JSON artifact is missing: {relative}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CheckError(f"cannot read JSON artifact {relative}: {exc}") from exc


def _read_text(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise CheckError(f"required text artifact is missing: {relative}")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckError(f"cannot read text artifact {relative}: {exc}") from exc


def _load_array(root: Path, relative: str, dtype: str) -> np.ndarray:
    path = root / relative
    if not path.is_file():
        raise CheckError(f"required numeric artifact is missing: {relative}")
    try:
        array = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise CheckError(f"cannot load numeric artifact {relative}: {exc}") from exc
    expected = np.dtype(dtype)
    if array.dtype != expected:
        raise CheckError(
            f"{relative}: expected dtype {expected}, got {array.dtype}"
        )
    return array


def _numeric_equal(left: Any, right: Any, label: str) -> None:
    left_array = np.asarray(left)
    right_array = np.asarray(right)
    if left_array.shape != right_array.shape:
        raise CheckError(
            f"{label}: shape mismatch {left_array.shape} != {right_array.shape}"
        )
    if left_array.dtype == bool or right_array.dtype == bool:
        if not np.array_equal(left_array.astype(bool), right_array.astype(bool)):
            raise CheckError(f"{label}: boolean values differ")
        return
    if np.issubdtype(left_array.dtype, np.integer) and np.issubdtype(
        right_array.dtype, np.integer
    ):
        if not np.array_equal(left_array, right_array):
            raise CheckError(f"{label}: integer values differ")
        return
    left_float = left_array.astype(np.float64)
    right_float = right_array.astype(np.float64)
    left_nan = np.isnan(left_float)
    right_nan = np.isnan(right_float)
    if not np.array_equal(left_nan, right_nan):
        raise CheckError(f"{label}: NaN pattern differs")
    if left_nan.any():
        left_float = left_float[~left_nan]
        right_float = right_float[~right_nan]
    if not np.allclose(left_float, right_float, rtol=NUMERIC_RTOL, atol=NUMERIC_ATOL):
        difference = float(np.max(np.abs(left_float - right_float))) if left_float.size else 0.0
        raise CheckError(
            f"{label}: numeric values differ beyond rtol={NUMERIC_RTOL} "
            f"atol={NUMERIC_ATOL}; max_abs_difference={difference}"
        )


def _exact_equal(left: Any, right: Any, label: str) -> None:
    if isinstance(left, float) or isinstance(right, float):
        if left is None or right is None:
            if left != right:
                raise CheckError(f"{label}: value differs: {left!r} != {right!r}")
            return
        if not math.isclose(
            float(left), float(right), rel_tol=NUMERIC_RTOL, abs_tol=NUMERIC_ATOL
        ):
            raise CheckError(f"{label}: numeric value differs: {left!r} != {right!r}")
        return
    if left != right:
        raise CheckError(f"{label}: value differs: {left!r} != {right!r}")


def _compare_payload(expected: Any, actual: Any, label: str) -> None:
    """Compare saved JSON to a recomputed payload exactly or within tolerance."""
    if isinstance(expected, Mapping) and isinstance(actual, Mapping):
        if set(expected) != set(actual):
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            raise CheckError(
                f"{label}: key mismatch; missing={missing} extra={extra}"
            )
        for key in expected:
            _compare_payload(expected[key], actual[key], f"{label}.{key}")
        return
    if isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
        if len(expected) != len(actual):
            raise CheckError(
                f"{label}: list length mismatch {len(expected)} != {len(actual)}"
            )
        for index, (left, right) in enumerate(zip(expected, actual)):
            _compare_payload(left, right, f"{label}[{index}]")
        return
    if isinstance(expected, bool) or isinstance(actual, bool):
        _exact_equal(bool(expected), bool(actual), label)
        return
    if isinstance(expected, int) and isinstance(actual, int):
        _exact_equal(expected, actual, label)
        return
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        _exact_equal(expected, actual, label)
        return
    _exact_equal(expected, actual, label)


class _Checker:
    def __init__(
        self,
        *,
        root: Path,
        repo_root: Path,
        command: Sequence[str],
    ) -> None:
        self.root = Path(root)
        self.repo_root = Path(repo_root)
        self.command = list(command)
        self.checks: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.values: Dict[str, Any] = {}

    def step(self, name: str, function: Any) -> Any:
        try:
            value = function()
        except Exception as exc:  # noqa: BLE001 - report every failure
            self.checks.append(
                {
                    "name": name,
                    "status": "failed",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
            )
            self.errors.append(
                {
                    "check": name,
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            raise
        self.checks.append({"name": name, "status": "passed"})
        return value

    def report(self, status: str) -> Dict[str, Any]:
        manifest = self.values.get("manifest", {})
        return {
            "schema": protocol.CHECK_REPORT_VERSION,
            "kind": "occupation-skill-graph-check",
            "created": artifacts.iso_now(),
            "status": status,
            "command": {"argv": self.command, "cwd": str(Path.cwd())},
            "checker": {
                "protocol_version": protocol.SCIENTIFIC_PROTOCOL_VERSION,
                "source": artifacts.checker_source_identity(self.repo_root),
            },
            "checked_manifest": {
                "path": protocol.MANIFEST_FILE,
                "sha256": self.values.get("manifest_sha256"),
                "files": len(manifest.get("files", {})) if isinstance(manifest, Mapping) else None,
            },
            "inputs": {
                "artifact_dir": str(self.root),
                "files": self.values.get("before", {}),
            },
            "tolerances": {
                "numeric_rtol": NUMERIC_RTOL,
                "numeric_atol": NUMERIC_ATOL,
                "discrete": "exact",
                "source_data_reopened": False,
                "input_modified": self.values.get("input_modified"),
            },
            "checks": self.checks,
            "errors": self.errors,
            "result": self.values.get("result", {}),
        }


def _validate_status(root: Path) -> Dict[str, Any]:
    status = artifacts.read_status(root)
    if status.get("state") != "succeeded":
        raise CheckError(
            f"saved status is {status.get('state')!r}, not 'succeeded'"
        )
    return status


def _validate_manifest(
    root: Path, required: Sequence[str]
) -> Tuple[Dict[str, Any], str]:
    manifest_path = root / protocol.MANIFEST_FILE
    if not manifest_path.is_file():
        raise CheckError(
            f"checksum inventory is missing: {protocol.MANIFEST_FILE}"
        )
    manifest_sha = artifacts.sha256_file(manifest_path)
    manifest = _read_json(root, protocol.MANIFEST_FILE)
    if not isinstance(manifest, Mapping):
        raise CheckError("checksum inventory is not a JSON object")
    if manifest.get("algorithm") != "sha256":
        raise CheckError("checksum inventory algorithm is not sha256")
    problems = artifacts.verify_manifest(root, manifest, required=required)
    if problems:
        raise CheckError("; ".join(problems[:10]))
    return dict(manifest), manifest_sha


def _validate_protocol(
    root: Path, report: Mapping[str, Any], provenance: Mapping[str, Any]
) -> Dict[str, Any]:
    text = _read_text(root, protocol.PROTOCOL_SNAPSHOT)
    digest = artifacts.sha256_file(root / protocol.PROTOCOL_SNAPSHOT)
    if text == "":
        raise CheckError("saved protocol snapshot is empty")
    if report.get("protocol", {}).get("sha256") != digest:
        raise CheckError("report protocol hash disagrees with the saved protocol")
    if provenance.get("protocol", {}).get("sha256") != digest:
        raise CheckError(
            "provenance protocol hash disagrees with the saved protocol"
        )
    if report.get("protocol", {}).get("version") != protocol.SCIENTIFIC_PROTOCOL_VERSION:
        raise CheckError("report protocol version is not the current fixed version")
    protocol.validate_protocol_version(report["protocol"]["version"])
    if provenance.get("protocol", {}).get("version") != report["protocol"]["version"]:
        raise CheckError("provenance and report protocol versions differ")
    return {
        "version": report["protocol"]["version"],
        "sha256": digest,
        "bytes": len(text.encode("utf-8")),
    }


def _load_source(root: Path) -> Dict[str, np.ndarray]:
    arrays = {
        "contexts": _load_array(root, "artifacts/contexts.npy", "int64"),
        "skills": _load_array(root, "artifacts/skills.npy", "int64"),
        "observations": _load_array(root, "artifacts/observations.npy", "float64"),
        "x": _load_array(root, "artifacts/x.npy", "float64"),
        "support": _load_array(root, "artifacts/support.npy", "bool"),
        "profiles": _load_array(root, "artifacts/profiles.npy", "float64"),
        "occupational_support_counts": _load_array(
            root, "artifacts/occupational_support_counts.npy", "int64"
        ),
    }
    contexts = arrays["contexts"]
    skills = arrays["skills"]
    observations = arrays["observations"]
    if contexts.ndim != 1 or skills.ndim != 1:
        raise CheckError("contexts and skills must be one-dimensional")
    if contexts.size == 0 or skills.size == 0:
        raise CheckError("saved source identity is empty")
    if np.unique(contexts).size != contexts.size:
        raise CheckError("saved context ids are duplicated")
    if np.unique(skills).size != skills.size:
        raise CheckError("saved skill ids are duplicated")
    if not np.array_equal(contexts, np.sort(contexts)):
        raise CheckError("saved context ids are not canonically sorted")
    if not np.array_equal(skills, np.sort(skills)):
        raise CheckError("saved skill ids are not canonically sorted")
    expected = (contexts.size, skills.size, protocol.N_TRAIN_MONTHS)
    if observations.shape != expected:
        raise CheckError(
            f"observations shape {observations.shape} != {expected}"
        )
    if arrays["x"].shape != (skills.size, contexts.size):
        raise CheckError("x has the wrong shape")
    if arrays["support"].shape != arrays["x"].shape:
        raise CheckError("support has the wrong shape")
    if arrays["profiles"].shape != arrays["x"].shape:
        raise CheckError("profiles has the wrong shape")
    if arrays["occupational_support_counts"].shape != (skills.size,):
        raise CheckError("occupational support counts have the wrong shape")
    if not np.isfinite(observations).all() or (observations < 0).any():
        raise CheckError("saved observations are not finite and nonnegative")
    if not np.isfinite(arrays["x"]).all() or (arrays["x"] < 0).any():
        raise CheckError("saved x is not finite and nonnegative")
    if not np.isfinite(arrays["profiles"]).all():
        raise CheckError("saved profiles contain nonfinite values")
    _numeric_equal(
        arrays["x"], observations.sum(axis=2).T, "x vs summed observations"
    )
    _numeric_equal(arrays["support"], arrays["x"] > 0, "support vs x > 0")
    if not np.array_equal(
        arrays["occupational_support_counts"],
        arrays["support"].sum(axis=1, dtype=np.int64),
    ):
        raise CheckError("occupational support counts disagree with support")
    totals = arrays["x"].sum(axis=1)
    denominator = np.where(totals > 0, totals, 1.0)
    expected_profiles = arrays["x"] / denominator[:, None]
    expected_profiles[totals == 0, :] = 0.0
    _numeric_equal(arrays["profiles"], expected_profiles, "profiles")
    return arrays


def _training_from_arrays(
    arrays: Mapping[str, np.ndarray], report: Mapping[str, Any]
) -> data.TrainingData:
    source = report.get("source", {})
    file_identity = source.get("file_identity", {})
    return data.training_from_arrays(
        arrays["contexts"],
        arrays["skills"],
        arrays["observations"],
        fixture=bool(report.get("fixture", False)),
        source_path=str(file_identity.get("path", "<saved>")),
        source_sha256=str(file_identity.get("sha256", "saved")),
    )


def _validate_recomputed_candidate(
    name: str,
    graph: scores.CandidateGraph,
    saved: Mapping[str, np.ndarray],
    saved_structure: Mapping[str, Any],
    recomputed_structure: Mapping[str, Any],
    saved_components: np.ndarray,
    recomputed_components: np.ndarray,
) -> None:
    _numeric_equal(saved["selection_index"], graph.selection_index, f"{name}.selection_index")
    _numeric_equal(saved["selection_score"], graph.selection_score, f"{name}.selection_score")
    _numeric_equal(saved["cutoff_score"], graph.cutoff_score, f"{name}.cutoff_score")
    _numeric_equal(
        saved["cutoff_tied_candidates"],
        graph.cutoff_tied_candidates,
        f"{name}.cutoff_tied_candidates",
    )
    _numeric_equal(saved["boundary_tie"], graph.boundary_tie, f"{name}.boundary_tie")
    _numeric_equal(saved["edge_index"], graph.edge_index, f"{name}.edge_index")
    _numeric_equal(saved["edge_score"], graph.edge_score, f"{name}.edge_score")
    _numeric_equal(saved["edge_direction"], graph.edge_direction, f"{name}.edge_direction")
    _numeric_equal(saved["degree"], graph.degree, f"{name}.degree")
    _numeric_equal(saved_components, recomputed_components, f"{name}.components")
    _compare_payload(saved_structure, recomputed_structure, f"{name}.structure")
    expected_edges = int(saved["edge_index"].shape[0])
    if int(saved["degree"].sum()) != expected_edges * 2:
        raise CheckError(
            f"{name}: degree sum {int(saved['degree'].sum())} != 2 * edges "
            f"{expected_edges}"
        )


def _validate_targets(
    root: Path,
    report: Mapping[str, Any],
    graphs: Mapping[str, scores.CandidateGraph],
    source_skills: np.ndarray,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for name in protocol.TARGET_DATA_NAMES:
        keys = _load_array(root, layout.target_array_path(name, "keys"), "int64")
        contexts = _load_array(root, layout.target_array_path(name, "contexts"), "int64")
        skills = _load_array(root, layout.target_array_path(name, "skills"), "int64")
        if keys.ndim != 2 or keys.shape[1] != 2:
            raise CheckError(f"target {name}: keys must have shape [N, 2]")
        if contexts.ndim != 1 or skills.ndim != 1:
            raise CheckError(f"target {name}: contexts/skills must be one-dimensional")
        if not np.array_equal(keys[:, 0], np.repeat(contexts, skills.size)):
            raise CheckError(f"target {name}: key array is not the canonical grid")
        expected_keys = np.stack(
            np.meshgrid(contexts, skills, indexing="ij"), axis=-1
        ).reshape(-1, 2)
        if not np.array_equal(keys, expected_keys):
            raise CheckError(f"target {name}: key array is not the complete grid")
        if not np.array_equal(skills, np.sort(skills)):
            raise CheckError(f"target {name}: skills are not canonically sorted")
        if tuple(int(value) for value in skills) != tuple(
            int(value) for value in source_skills
        ):
            raise CheckError(
                f"target {name}: skill population differs from the source"
            )
        if not bool(report.get("fixture", False)):
            data.assert_published_target(name, contexts, skills, f"saved {name}")
        target = data.target_keys_from_arrays(
            name,
            contexts,
            skills,
            fixture=bool(report.get("fixture", False)),
            source_path=str(
                report.get("targets", {}).get(name, {}).get("source_path", "<saved>")
            ),
            source_sha256=str(
                report.get("targets", {}).get(name, {}).get("source_file_sha256", "saved")
            ),
        )
        recomputed_population = mapping.validate_target_population(
            target, source_skills
        )
        saved_population = _read_json(
            root, layout.target_json_path(name, "population.json")
        )
        _compare_payload(
            saved_population, recomputed_population, f"{name}.population"
        )
        report_target = report.get("targets", {}).get(name)
        if not isinstance(report_target, Mapping):
            raise CheckError(f"report has no target record for {name}")
        _compare_payload(
            report_target.get("identity", {}),
            target.identity,
            f"{name}.report_identity",
        )
        _compare_payload(
            report_target.get("population", {}),
            recomputed_population,
            f"{name}.report_population",
        )
        _compare_payload(
            {
                "contexts": report_target.get("contexts"),
                "skills": report_target.get("skills"),
            },
            {
                "contexts": int(target.n_contexts),
                "skills": int(target.n_skills),
            },
            f"{name}.report_dimensions",
        )
        mappings: Dict[str, Any] = {}
        for candidate_name in protocol.CANDIDATES:
            graph = graphs[candidate_name]
            recomputed_descriptor = mapping.mapping_descriptor(
                target, graph.edge_index, graph.edge_score
            )
            saved_descriptor = _read_json(
                root, layout.target_json_path(name, f"mapping_{candidate_name}.json")
            )
            _compare_payload(
                saved_descriptor,
                recomputed_descriptor,
                f"{name}.{candidate_name}.mapping",
            )
            report_descriptor = report_target.get("mappings", {}).get(
                candidate_name, {}
            ).get("descriptor")
            if report_descriptor is None:
                raise CheckError(
                    f"report target {name} lacks the {candidate_name} mapping descriptor"
                )
            _compare_payload(
                report_descriptor,
                recomputed_descriptor,
                f"{name}.{candidate_name}.report_mapping",
            )
            expanded = 0
            for context in mapping.iter_context_edges(
                target, graph.edge_index, graph.edge_score
            ):
                if context.undirected_edges != graph.n_edges:
                    raise CheckError(
                        f"target {name}: lazy context edge count differs"
                    )
                if context.directed_edges != graph.n_edges * 2:
                    raise CheckError(
                        f"target {name}: lazy directed expansion count differs"
                    )
                expanded += 1
            if expanded != target.n_contexts:
                raise CheckError(f"target {name}: lazy expansion context count differs")
            mappings[candidate_name] = recomputed_descriptor
        result[name] = {
            "contexts": int(target.n_contexts),
            "skills": int(target.n_skills),
            "keys_sha256": data.canonical_key_sha256(keys),
            "mappings": mappings,
        }
    return result


def _validate_trends(
    root: Path,
    report: Mapping[str, Any],
    observations: np.ndarray,
    graphs: Mapping[str, scores.CandidateGraph],
) -> Dict[str, Any]:
    union_pairs = {
        tuple(int(value) for value in pair)
        for graph in graphs.values()
        for pair in graph.edge_index.tolist()
    }
    expected_union = np.asarray(sorted(union_pairs), dtype=np.int64)
    if expected_union.size == 0:
        expected_union = np.empty((0, 2), dtype=np.int64)
    saved_union = _load_array(root, "artifacts/trends/trend_edge_index.npy", "int64")
    _numeric_equal(saved_union, expected_union, "trend union edges")
    recomputed = trends.compute_trends(observations, saved_union)
    saved_arrays = {
        name: _load_array(root, f"artifacts/trends/{name}.npy", dtype)
        for name, dtype in (
            ("trend_eligible_counts", "int64"),
            ("trend_insufficient_counts", "int64"),
            ("trend_constant_counts", "int64"),
            ("trend_reason_codes", "int8"),
            ("trend_positive_counts", "int64"),
            ("trend_zero_counts", "int64"),
            ("trend_negative_counts", "int64"),
            ("trend_common_zero_months", "int64"),
            ("trend_common_zero_fraction", "float64"),
            ("trend_mean_context_common_zero_fraction", "float64"),
            ("trend_correlation_min", "float64"),
            ("trend_correlation_max", "float64"),
            ("trend_correlation_mean", "float64"),
            ("trend_correlation_median", "float64"),
            ("trend_correlation_std", "float64"),
        )
    }
    for name, value in recomputed.arrays().items():
        if name == "trend_edge_index":
            continue
        _numeric_equal(saved_arrays[name], value, f"trends.{name}")
    saved_global = _read_json(root, "artifacts/trends/global.json")
    _compare_payload(saved_global, recomputed.global_summary, "trends.global")
    report_trends = report.get("trends", {})
    _compare_payload(
        report_trends.get("global"), recomputed.global_summary, "report.trends.global"
    )
    lookup = {
        tuple(int(value) for value in pair): index
        for index, pair in enumerate(saved_union.tolist())
    }
    summaries: Dict[str, Any] = {}
    for candidate_name in protocol.CANDIDATES:
        graph = graphs[candidate_name]
        positions = np.asarray(
            [
                lookup[tuple(int(value) for value in pair)]
                for pair in graph.edge_index.tolist()
            ],
            dtype=np.int64,
        )
        summary = trends.candidate_trend_summary(
            recomputed, positions, candidate_name
        )
        saved_summary = _read_json(root, f"artifacts/trends/{candidate_name}.json")
        _compare_payload(saved_summary, summary, f"trends.{candidate_name}")
        report_summary = report_trends.get(candidate_name)
        _compare_payload(
            report_summary, summary, f"report.trends.{candidate_name}"
        )
        summaries[candidate_name] = summary
    if int(report_trends.get("union_edges", -1)) != int(saved_union.shape[0]):
        raise CheckError("report union edge count disagrees with saved trend edges")
    if report.get("graph_bytes_unchanged_by_diagnostics") is not True:
        raise CheckError("report does not assert unchanged graph bytes")
    return {
        "global": recomputed.global_summary,
        "candidates": summaries,
        "union_edges": int(saved_union.shape[0]),
    }


def check_artifact(
    artifact_dir: Path,
    report_path: Path,
    *,
    repo_root: Path,
    command: Sequence[str],
) -> Dict[str, Any]:
    """Check one saved audit and write exactly one exclusive external report."""
    root = Path(artifact_dir).expanduser()
    destination = paths.resolve_report_path(report_path, input_directory=root)
    checker = _Checker(root=root, repo_root=repo_root, command=command)
    before = _hash_tree(root)
    checker.values["before"] = before
    if not root.is_dir():
        checker.errors.append(
            {
                "check": "artifact_directory",
                "type": "CheckError",
                "message": f"artifact directory does not exist: {root}",
            }
        )
        checker.checks.append(
            {
                "name": "artifact_directory",
                "status": "failed",
                "error": checker.errors[-1],
            }
        )
        envelope = checker.report("failed")
        artifacts.write_exclusive_json(destination, envelope)
        return {
            "status": "failed",
            "report_path": str(destination),
            "report": envelope,
        }

    def run() -> None:
        checker.step("status", lambda: _validate_status(root))
        required = (
            [
                protocol.COMMAND_FILE,
                protocol.PROVENANCE_FILE,
                protocol.REPORT_FILE,
                protocol.SUMMARY_FILE,
                protocol.PROTOCOL_SNAPSHOT,
            ]
            + layout.required_payload_files()
        )
        manifest, manifest_sha = checker.step(
            "checksum_inventory", lambda: _validate_manifest(root, required)
        )
        checker.values["manifest"] = manifest
        checker.values["manifest_sha256"] = manifest_sha
        report = checker.step("report", lambda: _read_json(root, protocol.REPORT_FILE))
        if not isinstance(report, Mapping):
            raise CheckError("report.json is not a JSON object")
        if report.get("schema") != protocol.REPORT_VERSION:
            raise CheckError("report schema is not the current report version")
        if report.get("status") != "succeeded" or report.get(
            "terminal_state"
        ) != "succeeded":
            raise CheckError("report does not record a successful terminal state")
        provenance = checker.step(
            "provenance", lambda: _read_json(root, protocol.PROVENANCE_FILE)
        )
        if not isinstance(provenance, Mapping):
            raise CheckError("provenance.json is not a JSON object")
        checker.step("command", lambda: _read_json(root, protocol.COMMAND_FILE))
        checker.step("summary", lambda: _read_text(root, protocol.SUMMARY_FILE))
        protocol_info = checker.step(
            "protocol",
            lambda: _validate_protocol(root, report, provenance),
        )
        arrays = checker.step("source_arrays", lambda: _load_source(root))
        source = report.get("source", {})
        if not isinstance(source, Mapping):
            raise CheckError("report source record is missing")
        file_identity = source.get("file_identity", {})
        if not isinstance(file_identity, Mapping):
            raise CheckError("report source file identity is missing")
        for key in ("path", "sha256", "size_bytes"):
            if key not in file_identity:
                raise CheckError(f"report source file identity lacks {key}")
        if provenance.get("source") is None:
            raise CheckError("provenance does not record the source identity")
        _compare_payload(
            provenance.get("source", {}).get("file_identity", {}),
            file_identity,
            "provenance.source.file_identity",
        )
        _compare_payload(
            provenance.get("source", {}).get("training_content_identity", {}),
            source.get("training_content_identity", {}),
            "provenance.source.training_content_identity",
        )
        recomputed_content = data.training_content_identity(
            months=protocol.TRAIN_MONTHS,
            contexts=arrays["contexts"],
            skills=arrays["skills"],
            observations=arrays["observations"],
        )
        _compare_payload(
            source.get("training_content_identity", {}),
            recomputed_content,
            "source.training_content_identity",
        )
        node_hash = data.canonical_key_sha256(
            data.grid_keys(arrays["contexts"], arrays["skills"])
        )
        if source.get("node_keys_sha256") != node_hash:
            raise CheckError("report node key hash disagrees with saved identity")
        dimensions = source.get("dimensions", {})
        expected_dimensions = {
            "occupations": int(arrays["contexts"].size),
            "skills": int(arrays["skills"].size),
            "training_months": int(arrays["observations"].shape[2]),
        }
        _compare_payload(dimensions, expected_dimensions, "source.dimensions")
        if not bool(report.get("fixture", False)):
            data.assert_published_training(
                arrays["contexts"], arrays["skills"], "saved published source"
            )
        training = _training_from_arrays(arrays, report)
        graphs: Dict[str, scores.CandidateGraph] = {}
        recomputed_structures: Dict[str, Any] = {}
        for candidate_name in protocol.CANDIDATES:
            graph = scores.compute_candidate(
                candidate_name, arrays["x"], arrays["support"]
            )
            recomputed_structure, recomputed_components = structure.candidate_structure(
                graph, training
            )
            graphs[candidate_name] = graph
            recomputed_structures[candidate_name] = recomputed_structure
            saved_arrays = {
                name: _load_array(
                    root, layout.candidate_array_path(candidate_name, name), dtype
                )
                for name, dtype in (
                    ("selection_index", "int64"),
                    ("selection_score", "float64"),
                    ("cutoff_score", "float64"),
                    ("cutoff_tied_candidates", "int64"),
                    ("boundary_tie", "bool"),
                    ("edge_index", "int64"),
                    ("edge_score", "float64"),
                    ("edge_direction", "int8"),
                    ("degree", "int64"),
                    ("components", "int64"),
                )
            }
            saved_structure = _read_json(
                root, layout.candidate_json_path(candidate_name, "structure.json")
            )
            _validate_recomputed_candidate(
                candidate_name,
                graph,
                saved_arrays,
                saved_structure,
                recomputed_structure,
                saved_arrays["components"],
                recomputed_components,
            )
            saved_hashes = _read_json(
                root, layout.candidate_json_path(candidate_name, "graph-hashes.json")
            )
            _compare_payload(
                saved_hashes.get("payload", {}),
                graph.identity_hashes(),
                f"{candidate_name}.graph_hashes",
            )
            report_candidate = report.get("candidates", {}).get(candidate_name)
            if not isinstance(report_candidate, Mapping):
                raise CheckError(f"report lacks candidate {candidate_name}")
            _compare_payload(
                report_candidate,
                recomputed_structure,
                f"report.candidates.{candidate_name}",
            )
        recomputed_overlap = structure.candidate_overlap(
            graphs["jaccard"], graphs["cosine"]
        )
        saved_overlap = _read_json(root, layout.CANDIDATE_OVERLAP_FILE)
        _compare_payload(saved_overlap, recomputed_overlap, "candidate_overlap")
        _compare_payload(
            report.get("candidate_overlap", {}),
            recomputed_overlap,
            "report.candidate_overlap",
        )
        target_result = checker.step(
            "targets",
            lambda: _validate_targets(
                root, report, graphs, arrays["skills"]
            ),
        )
        trend_result = checker.step(
            "trends",
            lambda: _validate_trends(
                root, report, arrays["observations"], graphs
            ),
        )
        # Report dimensions and limits are cross-checked against recomputation.
        expected_report_dimensions = {
            "occupations": int(arrays["contexts"].size),
            "skills": int(arrays["skills"].size),
            "training_months": int(arrays["observations"].shape[2]),
            "union_edges": int(trend_result["union_edges"]),
            "jaccard_edges": int(graphs["jaccard"].n_edges),
            "cosine_edges": int(graphs["cosine"].n_edges),
        }
        _compare_payload(
            report.get("dimensions", {}),
            expected_report_dimensions,
            "report.dimensions",
        )
        if not isinstance(report.get("fixture"), bool):
            raise CheckError("report fixture flag is not boolean")
        _compare_payload(
            report.get("costs", {}).get("dimensions", {}),
            expected_report_dimensions,
            "report.costs.dimensions",
        )
        checker.values["result"] = {
            "source": {
                "file_sha256": file_identity.get("sha256"),
                "training_content_sha256": recomputed_content["sha256"],
                "node_keys_sha256": node_hash,
                "protocol_sha256": protocol_info["sha256"],
            },
            "candidates": {
                name: {
                    "edges": int(graphs[name].n_edges),
                    "degree_sum": int(graphs[name].degree.sum()),
                    "max_degree": int(graphs[name].degree.max())
                    if graphs[name].n_nodes
                    else 0,
                }
                for name in protocol.CANDIDATES
            },
            "candidate_overlap": recomputed_overlap,
            "targets": target_result,
            "trends": trend_result,
        }

    status = "ok"
    try:
        run()
    except BaseException as exc:  # noqa: BLE001 - publish a failure report
        status = "failed"
        if not checker.errors:
            checker.errors.append(
                {
                    "check": "checker",
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )
    after = _hash_tree(root)
    modified = after != before
    checker.values["input_modified"] = modified
    if modified:
        status = "failed"
        checker.errors.append(
            {
                "check": "input_preservation",
                "type": "CheckError",
                "message": "checked artifact directory changed during the check",
            }
        )
    envelope = checker.report(status)
    artifacts.write_exclusive_json(destination, envelope)
    return {
        "status": status,
        "report_path": str(destination),
        "report": envelope,
    }
