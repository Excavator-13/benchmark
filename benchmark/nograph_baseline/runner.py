"""Run orchestration: stages, timing, peak memory and terminal status.

Each formal run reserves its own directory, captures provenance before fitting,
freezes training statistics and model selection, then writes every artifact
needed for independent metric recomputation.  Failures and interruptions keep
partial evidence with an explicit ``failed``/``interrupted`` status; an
uncatchable termination leaves ``running``, which recovery classifies as
unfinished.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

from . import artifacts, baselines, coverage, metrics, protocol, ridge


class RunError(RuntimeError):
    """Raised when a run cannot complete its protocol obligations."""


class RunInterrupted(RuntimeError):
    """Raised after SIGTERM/SIGINT so partial evidence can be finalized."""


@dataclass
class RunSpec:
    """Resolved configuration for one model run."""

    data_name: str
    run_id: str
    mode: str = "count"
    seed: int = 0
    purpose: str = "formal"
    retain_candidates: bool = False
    ridge_backend: str = "numpy"
    clip_nonnegative: bool = False
    demand_path: Optional[str] = None
    graph_path: Optional[str] = None
    mask_bundle: Optional[str] = None
    runs_root: Optional[str] = None
    repo_root: Optional[str] = None
    protocol_path: Optional[str] = None
    command: List[str] = field(default_factory=list)
    launcher_cwd: Optional[str] = None
    run_type: str = "run"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RunSpec":
        known = {field_name for field_name in cls.__dataclass_fields__}
        filtered = {key: value for key, value in payload.items() if key in known}
        return cls(**filtered)


def measure_peak_rss() -> Dict[str, Any]:
    """Return normalized process peak RSS with its native unit and method."""
    try:
        import resource
    except ImportError:  # pragma: no cover - non-POSIX
        return {
            "bytes": None,
            "native_value": None,
            "native_unit": None,
            "method": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
            "status": "unsupported_platform",
            "reason": "resource module unavailable",
        }
    native = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    system = platform.system()
    if system == "Darwin":
        factor, unit = 1, "bytes"
    elif system == "Linux":
        factor, unit = 1024, "KiB"
    else:  # pragma: no cover - other POSIX platforms
        return {
            "bytes": None,
            "native_value": native,
            "native_unit": "unknown",
            "method": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
            "status": "unsupported_platform",
            "reason": f"peak RSS unit for {system} is not defined by this entry",
        }
    return {
        "bytes": native * factor,
        "native_value": native,
        "native_unit": unit,
        "method": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
        "status": "ok",
    }


def execution_settings(seed: int) -> Dict[str, Any]:
    """Record the deterministic execution settings of the worker."""
    return {
        "seed": int(seed),
        "device": "cpu",
        "blas_thread_environment": {
            name: os.environ.get(name)
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS",
            )
        },
        "randomized_behavior": "none: naive rules and shared Ridge are deterministic",
    }


def execute_run(spec: RunSpec) -> Dict[str, Any]:
    """Execute one model run inside the current (isolated worker) process."""
    protocol.validate_dataset_mode(spec.data_name, spec.mode)
    protocol.validate_split_assertions()
    artifacts.validate_run_id(spec.run_id)
    repo_root = Path(spec.repo_root) if spec.repo_root else protocol.REPO_ROOT
    runs_root = _resolve_runs_root(spec, repo_root)
    _validate_purpose(spec, repo_root, runs_root)
    protocol_path = Path(spec.protocol_path) if spec.protocol_path else protocol.PROTOCOL_PATH
    demand_path = Path(spec.demand_path) if spec.demand_path else protocol.demand_path(spec.data_name)
    graph_path = Path(spec.graph_path) if spec.graph_path else None
    mask_bundle_path = Path(spec.mask_bundle) if spec.mask_bundle else None

    run = artifacts.RunDirectory(runs_root, spec.run_id, spec.run_type).reserve()
    durations: Dict[str, float] = {}
    stage = "init"
    total_started = time.perf_counter()
    failure: Optional[Dict[str, Any]] = None
    try:
        run.set_status("running", stage=stage, purpose=spec.purpose)
        run.write_json(
            "config.json",
            {
                "protocol_version": protocol.PROTOCOL_VERSION,
                "spec": spec.to_dict(),
                "lambdas": list(protocol.LAMBDA_CANDIDATES),
                "naive_methods": list(protocol.NAIVE_METHODS),
                "model_name": protocol.MODEL_NAME,
                "clip_nonnegative": bool(spec.clip_nonnegative),
            },
        )
        run.write_json(
            "command.json",
            {
                "argv": list(spec.command),
                "python": sys.executable,
                "cwd": os.getcwd(),
                "launcher_cwd": spec.launcher_cwd,
                "cwd_differs_from_launcher": (
                    spec.launcher_cwd is not None
                    and os.path.realpath(spec.launcher_cwd)
                    != os.path.realpath(os.getcwd())
                ),
            },
        )
        stage = "source_capture"
        git = artifacts.capture_git(repo_root)
        artifacts.write_git_snapshot(run, git)
        source = artifacts.capture_source(
            run, repo_root, protocol_path=protocol_path
        )
        environment = artifacts.capture_environment(repo_root)
        run.write_json("environment.json", environment)
        artifacts.write_environment_snapshot(run, environment)

        stage = "protocol_snapshot"
        protocol_sha256 = _sha256(protocol_path) if protocol_path.exists() else None
        protocol_entry = (
            source.get("protocol") if isinstance(source, Mapping) else None
        )
        reusable_protocol = bool(
            isinstance(protocol_entry, Mapping)
            and protocol_entry.get("git_status") == "committed_clean"
            and protocol_entry.get("git_reference")
        )
        if reusable_protocol:
            # The recorded commit/path locates the exact executing bytes, so no
            # duplicate protocol file is written.
            run.append_event(
                "protocol_referenced",
                commit=protocol_entry["git_reference"]["commit"],
                path=protocol_entry["git_reference"]["path"],
            )
        elif protocol_path.exists():
            run.copy_file(protocol_path, "protocol.md")
        else:
            run.write_text(
                "protocol.md",
                f"protocol snapshot unavailable at {protocol_path}\n",
            )

        stage = "demand_read"
        started = time.perf_counter()
        demand = _load_demand(spec, demand_path)
        durations["demand_read"] = time.perf_counter() - started

        stage = "audit"
        run.save_dataframe("nodes.parquet", _nodes_frame(demand))
        run.write_json("audit.json", demand.audit)
        run.write_json("windows.json", protocol.build_window_metadata())

        stage = "preprocessing"
        started = time.perf_counter()
        stats = ridge.compute_training_stats(demand.signal)
        train_starts = protocol.windows_for_split("train")
        validation_starts = protocol.windows_for_split("validation")
        test_starts = protocol.windows_for_split("test")
        x_train, y_train = ridge.build_design(demand.signal, stats, train_starts)
        x_validation, y_validation = ridge.build_design(
            demand.signal, stats, validation_starts
        )
        x_test, y_test = ridge.build_design(demand.signal, stats, test_starts)
        durations["preprocessing"] = time.perf_counter() - started
        _test_stage_delay()

        stage = "naive"
        started = time.perf_counter()
        frozen_mean = baselines.train_mean27(demand.signal)
        validation_predictions = baselines.naive_predictions(
            demand.signal, validation_starts, frozen_train_mean=frozen_mean
        )
        test_predictions = baselines.naive_predictions(
            demand.signal, test_starts, frozen_train_mean=frozen_mean
        )
        durations["naive_prediction"] = time.perf_counter() - started

        stage = "reference_selection"
        selection_started = time.perf_counter()
        validation_gold = demand.target_windows(validation_starts)
        test_gold = demand.target_windows(test_starts)
        scores = baselines.validation_mse(validation_predictions, validation_gold)
        references = baselines.select_references(scores)
        durations["reference_selection"] = time.perf_counter() - selection_started

        stage = "ridge_fit"
        started = time.perf_counter()
        candidates = ridge.fit_candidates(
            x_train,
            y_train,
            x_validation,
            y_validation,
            stats,
            backend=spec.ridge_backend,
        )
        durations["ridge_fit"] = time.perf_counter() - started

        stage = "ridge_selection"
        started = time.perf_counter()
        ridge_selection = ridge.select_lambda(candidates)
        durations["ridge_selection"] = time.perf_counter() - started
        # Freeze selection before any test target is touched.
        run.write_json(
            "selection.json",
            {
                "naive_references": references,
                "naive_validation_scores": scores,
                "shared_ridge": {
                    key: value
                    for key, value in ridge_selection.items()
                    if key != "selected_candidate"
                },
                "normalization": {
                    "train_observation_months": list(
                        protocol.TRAIN_OBSERVATION_MONTHS
                    ),
                    "ddof": 0,
                    "constant_node_std": 1.0,
                    "applied_to_inputs_and_targets": True,
                },
                "training_samples_M": int(candidates[0]["M"]),
                "expected_training_samples_M": protocol.expected_train_sample_count(
                    demand.node_count
                ),
                "training_design_ordering": "window-major then node-major (row w*N+i)",
                "test_labels_used_for_selection": False,
            },
        )

        stage = "coverage"
        started = time.perf_counter()
        cov = _load_coverage(spec, demand, graph_path, mask_bundle_path)
        durations["coverage_read"] = time.perf_counter() - started
        run.write_json("coverage.json", cov.provenance)
        _save_masks(run, stats, cov)

        stage = "inference"
        started = time.perf_counter()
        selected = ridge_selection["selected_candidate"]
        validation_model = ridge.predict_from_standardized(
            x_validation, stats, selected["W"], selected["b"]
        ).reshape(
            len(validation_starts), demand.node_count, protocol.HORIZON
        )
        test_model = ridge.predict_from_standardized(
            x_test, stats, selected["W"], selected["b"]
        ).reshape(len(test_starts), demand.node_count, protocol.HORIZON)
        predictions_by_split: Dict[str, Dict[str, np.ndarray]] = {
            "validation": dict(validation_predictions),
            "test": dict(test_predictions),
        }
        predictions_by_split["validation"][protocol.MODEL_NAME] = validation_model
        predictions_by_split["test"][protocol.MODEL_NAME] = test_model
        if spec.clip_nonnegative:
            predictions_by_split["validation"][
                protocol.CLIPPED_MODEL_NAME
            ] = ridge.clip_nonnegative(validation_model)
            predictions_by_split["test"][
                protocol.CLIPPED_MODEL_NAME
            ] = ridge.clip_nonnegative(test_model)
        durations["selected_model_inference"] = time.perf_counter() - started

        stage = "persist_model"
        run.save_npz(
            "models/TrainMean27.npz",
            train_mean27=np.asarray(frozen_mean, dtype=np.float32).reshape(-1),
            train_observation_month_count=np.array([27], dtype=np.int64),
        )
        _save_model_artifacts(
            run, spec, stats, candidates, selected, x_validation, x_test
        )

        stage = "metrics_output"
        metrics_started = time.perf_counter()
        gold_by_split = {"validation": validation_gold, "test": test_gold}
        activity_masks = stats.activity_groups
        constant_masks = metrics.constant_group_masks(stats.constant_mask)
        context_values = demand.key_array[:, 0]
        context_masks_map = metrics.context_masks(context_values)
        neighbor_masks = metrics.neighbor_group_masks(cov.mask)
        reports: Dict[str, Dict[str, Any]] = {"validation": {}, "test": {}}
        node_frames: List[Any] = []
        for split, starts in (
            ("validation", validation_starts),
            ("test", test_starts),
        ):
            for method, pred in predictions_by_split[split].items():
                report = metrics.split_report(
                    pred,
                    gold_by_split[split],
                    starts=starts,
                    activity_masks=activity_masks,
                    constant_masks=constant_masks,
                    context_masks_map=context_masks_map,
                    neighbor_masks=neighbor_masks,
                )
                report["method"] = method
                report["split"] = split
                report["dataset"] = spec.data_name
                report["nonself_neighbor_coverage_source"] = cov.provenance.get(
                    "source"
                )
                reports[split][method] = report
                node_frames.append(
                    metrics.node_error_table(
                        pred,
                        gold_by_split[split],
                        method=method,
                        split=split,
                        node_keys=demand.key_array,
                        key_columns=demand.key_columns,
                        train_mean27_values=frozen_mean.reshape(-1),
                        context_values=context_values,
                    )
                )
        model_names = [protocol.MODEL_NAME]
        if spec.clip_nonnegative:
            model_names.append(protocol.CLIPPED_MODEL_NAME)
        relative: Dict[str, Any] = {}
        for split in ("validation", "test"):
            relative[split] = metrics.baseline_relative_comparison(
                reports[split],
                context_names=list(context_masks_map),
                neighbor_names=list(neighbor_masks),
                model_names=model_names,
                reference_names=[references["NaiveRef"], references["NaiveRef6"]],
            )
        run.write_json(
            "metrics.json",
            {
                "protocol_version": protocol.PROTOCOL_VERSION,
                "dataset": spec.data_name,
                "mode": spec.mode,
                "run_id": spec.run_id,
                "references": references,
                "relative_gains": relative,
                "methods": reports,
                "aggregation_note": (
                    "overall RMSE = sqrt(mean squared error over all window-node-"
                    "horizon elements); test target-month multiplicities are "
                    "1,2,3,3,2,1 and are not treated as independent samples"
                ),
            },
        )
        run.write_json("gold/dtype.json", {"dtype": str(test_gold.dtype)})
        _save_predictions(run, predictions_by_split)
        run.save_npy("gold/validation.npy", validation_gold)
        run.save_npy("gold/test.npy", test_gold)
        if node_frames:
            import pandas as pd

            run.save_dataframe(
                "node-errors.parquet", pd.concat(node_frames, ignore_index=True)
            )
        durations["metrics_output"] = time.perf_counter() - metrics_started

        stage = "source_verification"
        manifest = artifacts.source_manifest(
            demand_path=Path(demand.source_path),
            demand_sha256=demand.source_sha256,
            protocol_path=protocol_path,
            protocol_sha256=protocol_sha256 or "<unavailable>",
            coverage_path=Path(cov.provenance["source_path"])
            if cov.provenance.get("source_path")
            and not str(cov.provenance.get("source_path")).startswith("<")
            else None,
            coverage_sha256=cov.provenance.get("source_sha256"),
            reference_path=(
                Path(spec.reference_path) if getattr(spec, "reference_path", None) else None
            ),
        )
        manifest["run_id"] = spec.run_id
        manifest["node_keys_sha256"] = demand.identity_payload()["node_keys_sha256"]
        manifest["coverage_bundle_sha256"] = cov.provenance.get("bundle_sha256")
        mismatches = artifacts.verify_source_hashes(manifest)
        run.write_json("source-sha256.json", manifest)
        if mismatches:
            run.append_event("source_hash_mismatch", mismatches=mismatches)
            raise RunError(
                "source files changed during the run: " + "; ".join(mismatches)
            )

        stage = "provenance"
        run.write_json(
            "provenance.json",
            {
                "run_id": spec.run_id,
                "run_type": spec.run_type,
                "purpose": spec.purpose,
                "dataset": spec.data_name,
                "mode": spec.mode,
                "seed": spec.seed,
                "protocol_version": protocol.PROTOCOL_VERSION,
                "created": _now(),
                "git": {
                    "commit": git.get("commit"),
                    "dirty": git.get("dirty"),
                    "identity_available": git.get("identity_available"),
                    "errors": git.get("errors"),
                },
                "source_capture": source,
                "node_keys_sha256": demand.identity_payload()["node_keys_sha256"],
                "nodes": demand.node_count,
                "source_sha256": demand.source_sha256,
                "coverage": cov.provenance,
                "reference_evidence": None,
                "scientific_acceptance": False,
            },
        )

        stage = "measurements"
        durations["total"] = time.perf_counter() - total_started
        measurements = {
            "run_id": spec.run_id,
            "dataset": spec.data_name,
            "mode": spec.mode,
            "timings_seconds": durations,
            "totals_seconds": {
                "data_reading": durations.get("demand_read", 0.0)
                + durations.get("coverage_read", 0.0),
                "fitting": durations.get("ridge_fit", 0.0),
                "inference": durations.get("selected_model_inference", 0.0),
                "total": durations["total"],
            },
            "peak_memory": measure_peak_rss(),
            "device": "cpu",
            "execution_settings": execution_settings(spec.seed),
            "stage_definitions": {
                "demand_read": "read and validate the demand Parquet source",
                "coverage_read": "read and annotate neighbour coverage evidence",
                "preprocessing": "frozen statistics and standardized design matrices",
                "naive_prediction": "five na\u00efve methods, no optimization",
                "ridge_fit": "all candidate SharedRidge fits",
                "ridge_selection": "validation-only lambda selection",
                "selected_model_inference": "selected-model validation/test prediction",
                "metrics_output": "metric reduction and artifact writing",
            },
            "diagnostic_elapsed_times_used": False,
        }
        run.write_json("measurements.json", measurements)

        stage = "summary"
        run.write_text("summary.md", _summary_text(spec, demand, references, ridge_selection, coverage_prov=cov.provenance, measurements=measurements))
        run.set_status(
            "success",
            stage="complete",
            purpose=spec.purpose,
            total_seconds=durations["total"],
            nodes=demand.node_count,
        )
        run.finalize_artifacts_manifest()
        run.append_event("run_success", nodes=demand.node_count)
        return {
            "run_id": spec.run_id,
            "run_dir": str(run.path),
            "status": "success",
            "state": "success",
        }
    except KeyboardInterrupt as exc:
        failure = _failure_record(stage, exc, "interrupted")
        run.set_status("interrupted", stage=stage, error=failure)
        _write_failure_evidence(run, spec, failure, durations)
        run.append_event("run_interrupted", stage=stage)
        raise RunInterrupted(f"interrupted during {stage}") from exc
    except RunInterrupted as exc:
        failure = _failure_record(stage, exc, "interrupted")
        run.set_status("interrupted", stage=stage, error=failure)
        _write_failure_evidence(run, spec, failure, durations)
        run.append_event("run_interrupted", stage=stage)
        raise
    except BaseException as exc:  # noqa: BLE001 - preserve every failure as evidence
        failure = _failure_record(stage, exc, "failed")
        run.set_status("failed", stage=stage, error=failure)
        _write_failure_evidence(run, spec, failure, durations)
        run.append_event("run_failed", stage=stage, error_type=type(exc).__name__)
        raise


def _test_stage_delay() -> None:
    """Optional internal test hook to hold a run open between stages.

    Inert unless ``NOGRAPH_BASELINE_TEST_STAGE_DELAY_SECONDS`` is set.  It lets
    the automated suite deliver SIGINT/SIGTERM/SIGKILL deterministically and
    verify retained partial evidence and unfinished state.
    """
    raw = os.environ.get("NOGRAPH_BASELINE_TEST_STAGE_DELAY_SECONDS", "")
    if not raw:
        return
    try:
        seconds = float(raw)
    except ValueError:
        return
    if seconds > 0:
        time.sleep(seconds)


def _sha256(path: Path) -> str:
    from .data import sha256_file

    return sha256_file(path)


def _now() -> str:
    from .data import iso_now

    return iso_now()


def _load_demand(spec: RunSpec, demand_path: Path) -> Any:
    from .data import load_demand

    return load_demand(
        spec.data_name, mode=spec.mode, demand_path=demand_path
    )


def _load_coverage(
    spec: RunSpec,
    demand: Any,
    graph_path: Optional[Path],
    mask_bundle_path: Optional[Path],
) -> coverage.CoverageMask:
    if mask_bundle_path is not None:
        return coverage.load_mask_bundle(
            mask_bundle_path, spec.data_name, demand.key_array
        )
    return coverage.load_graph_coverage(
        spec.data_name, demand.key_array, graph_path=graph_path
    )


def _nodes_frame(demand: Any) -> "Any":
    import pandas as pd

    frame = pd.DataFrame(demand.key_array, columns=list(demand.key_columns))
    frame.insert(0, "node_index", np.arange(demand.node_count, dtype=np.int64))
    return frame


def _save_masks(run: artifacts.RunDirectory, stats: ridge.TrainingStats, cov: coverage.CoverageMask) -> None:
    arrays: Dict[str, np.ndarray] = {
        "constant_train27": np.asarray(stats.constant_mask, dtype=bool),
        "nonzero_activity_train27": np.asarray(stats.activity, dtype=np.float64),
        "has_nonself_neighbor": np.asarray(cov.mask, dtype=bool),
    }
    for name, mask in stats.activity_groups.items():
        arrays[f"activity_{name}"] = np.asarray(mask, dtype=bool)
    run.save_npz("masks.npz", **arrays)


def _resolve_runs_root(spec: RunSpec, repo_root: Path) -> Path:
    """Resolve the output root for the declared execution purpose."""
    if spec.runs_root:
        return Path(spec.runs_root)
    return artifacts.default_runs_root(repo_root, spec.purpose)


def _validate_purpose(spec: RunSpec, repo_root: Path, runs_root: Path) -> None:
    """Reject unknown purposes and development output inside formal records.

    Paths are resolved (including symlink aliases) before any directory is
    created, so a development invocation can never write into the formal
    ``research/runs`` namespace.
    """
    if spec.purpose not in artifacts.PURPOSES:
        raise RunError(
            f"unknown execution purpose {spec.purpose!r}; expected one of "
            f"{', '.join(artifacts.PURPOSES)}"
        )
    if spec.purpose != "development":
        return
    formal_root = artifacts.formal_runs_root(repo_root)
    if artifacts.is_within(runs_root, formal_root):
        raise RunError(
            "development output root resolves inside the formal "
            f"experiment namespace {formal_root}: {runs_root}"
        )


def _save_model_artifacts(
    run: artifacts.RunDirectory,
    spec: RunSpec,
    stats: ridge.TrainingStats,
    candidates: Sequence[Mapping[str, Any]],
    selected: Mapping[str, Any],
    x_validation: np.ndarray,
    x_test: np.ndarray,
) -> None:
    # Every accepted backend must supply the shared payload schema; fail here
    # rather than halfway through writing a corrupt model artifact.
    ridge.validate_model_payload(selected, label=f"selected {spec.ridge_backend}")
    run.save_npz(
        "models/SharedRidge.npz",
        W=np.asarray(selected["W"], dtype=np.float64),
        b=np.asarray(selected["b"], dtype=np.float64),
        node_mean=np.asarray(stats.mean, dtype=np.float64),
        node_std=np.asarray(stats.std, dtype=np.float64),
        node_effective_std=np.asarray(stats.effective_std, dtype=np.float64),
        constant_mask=np.asarray(stats.constant_mask, dtype=bool),
        centered_x_mean=np.asarray(selected["centered_x_mean"], dtype=np.float64),
        centered_y_mean=np.asarray(selected["centered_y_mean"], dtype=np.float64),
        scalar=np.array(
            [
                float(selected["lambda"]),
                float(selected["alpha"]),
                float(selected["M"]),
                float(selected["objective"]),
            ],
            dtype=np.float64,
        ),
        std_ddof=np.array([0], dtype=np.int64),
    )
    # Losing-candidate parameters and validation predictions are omitted by
    # default; every candidate's scalar score row remains in selection.json.
    if spec.retain_candidates:
        for candidate in candidates:
            label = f"{float(candidate['lambda']):g}"
            run.save_npz(
                f"candidates/{label}/parameters.npz",
                W=np.asarray(candidate["W"], dtype=np.float64),
                b=np.asarray(candidate["b"], dtype=np.float64),
                scalar=np.array(
                    [
                        float(candidate["lambda"]),
                        float(candidate["alpha"]),
                        float(candidate["M"]),
                        float(candidate["objective"]),
                    ],
                    dtype=np.float64,
                ),
            )
            run.save_npy(
                f"candidates/{label}/validation.npy",
                np.asarray(candidate["validation_predictions"], dtype=np.float64),
            )


def _save_predictions(
    run: artifacts.RunDirectory,
    predictions_by_split: Mapping[str, Mapping[str, np.ndarray]],
) -> None:
    for split, methods in predictions_by_split.items():
        for method, pred in methods.items():
            run.save_npy(f"predictions/{method}/{split}.npy", np.asarray(pred))


def _failure_record(stage: str, exc: BaseException, state: str) -> Dict[str, Any]:
    return {
        "stage": stage,
        "state": state,
        "exception_type": type(exc).__name__,
        "message": str(exc),
        "traceback": "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ),
    }


def _write_failure_evidence(
    run: artifacts.RunDirectory,
    spec: RunSpec,
    failure: Mapping[str, Any],
    durations: Mapping[str, float],
) -> None:
    try:
        run.write_json(
            "failure.json",
            {
                "run_id": spec.run_id,
                "dataset": spec.data_name,
                "failure": dict(failure),
                "timings_seconds": dict(durations),
                "peak_memory": measure_peak_rss(),
                "completed_artifacts": [
                    path.relative_to(run.path).as_posix()
                    for path in run.iter_files()
                ],
            },
        )
    except Exception:  # pragma: no cover - evidence writing must not mask the cause
        pass


def check_unfinished(run_dir: Path) -> Dict[str, Any]:
    """Classify a run directory's terminal state without inferring success."""
    run_dir = Path(run_dir)
    status_path = run_dir / "status.json"
    if not status_path.exists():
        return {"run_dir": str(run_dir), "state": "missing", "finished": False}
    status = json.loads(status_path.read_text(encoding="utf-8"))
    state = status.get("state")
    return {
        "run_dir": str(run_dir),
        "state": state,
        "finished": state in ("success", "failed", "interrupted"),
        "unfinished": state not in ("success", "failed", "interrupted"),
        "status": status,
    }


def _summary_text(
    spec: RunSpec,
    demand: Any,
    references: Mapping[str, Any],
    ridge_selection: Mapping[str, Any],
    *,
    coverage_prov: Mapping[str, Any],
    measurements: Mapping[str, Any],
) -> str:
    lines = [
        f"# Run {spec.run_id}",
        "",
        f"- Dataset: `{spec.data_name}/{spec.mode}`",
        f"- Protocol: `{protocol.PROTOCOL_VERSION}`",
        f"- Purpose: `{spec.purpose}`"
        + (
            " (development output; not scientific acceptance evidence)"
            if spec.purpose == "development"
            else " (formal experiment)"
        ),
        f"- Nodes: {demand.node_count}",
        f"- Seed: {spec.seed} (CPU, NumPy backend `{spec.ridge_backend}`)",
        f"- NaiveRef: `{references['NaiveRef']}` (validation MSE, frozen)",
        f"- NaiveRef6: `{references['NaiveRef6']}`",
        f"- Selected SharedRidge lambda: {ridge_selection['selected_lambda']}",
        f"- Non-self neighbour coverage: {coverage_prov.get('covered_nodes')} nodes "
        f"from `{coverage_prov.get('source')}`",
        "",
        "## Measured costs",
        "",
        f"- Total: {measurements['totals_seconds']['total']:.3f} s",
        f"- Data reading: {measurements['totals_seconds']['data_reading']:.3f} s",
        f"- Fitting: {measurements['totals_seconds']['fitting']:.3f} s",
        f"- Inference: {measurements['totals_seconds']['inference']:.3f} s",
        f"- Peak RSS: {measurements['peak_memory'].get('bytes')} bytes "
        f"({measurements['peak_memory'].get('native_value')} "
        f"{measurements['peak_memory'].get('native_unit')})",
        "",
        "## Status",
        "",
        "A successful run records evidence only. It does not assert scientific",
        "acceptance, packaging, Git inclusion or backup completion.",
        "",
    ]
    return "\n".join(lines)
