"""Run orchestration: stages, fixed training, complete evidence and status.

One execution loads and asserts the dataset, loads and audits the graph,
builds (or retrieves) the shuffled control, freezes references, runs exactly
200 epochs of the frozen skeleton, selects the validation-MSE checkpoint, then
writes every artifact needed for a saved-only recomputation.  Failed or
interrupted executions keep partial evidence and an explicit terminal state;
an uncatchable termination leaves ``running``, which ``check_unfinished``
classifies as unfinished instead of inferring success.
"""

from __future__ import annotations

import json
import hashlib
import uuid
import os
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from benchmark.nograph_baseline import baselines
from benchmark.nograph_baseline import metrics as p01_metrics
from benchmark.nograph_baseline import protocol as p01

from . import artifacts, data, graph as gvs_graph, model as gvs_model, shuffle as gvs_shuffle, training
from . import protocol
from . import checkpoints
from .config import RunConfig, resolve_output_root

__all__ = [
    "RunError",
    "RunInterrupted",
    "execute_run",
    "check_unfinished",
    "summary_text",
    "MODEL_METHOD_KEY",
]

MODEL_METHOD_KEY = "model"
#: One canonical identity for an empty message graph (the self branch), shared by
#: graph-audit, provenance and the final source manifest.
EMPTY_MESSAGE_EDGES_SHA256 = "<empty: self branch propagates no message>"


def _message_edges_sha256(message_edges: np.ndarray) -> str:
    return (
        gvs_graph.edge_set_sha256(message_edges)
        if message_edges.shape[0]
        else EMPTY_MESSAGE_EDGES_SHA256
    )


class RunError(RuntimeError):
    """Raised when a run cannot complete its protocol obligations."""


class RunInterrupted(RuntimeError):
    """Raised after SIGINT/SIGTERM so partial evidence can be finalized."""


@dataclass
class _Counters:
    durations: Dict[str, float]
    stage: str


def execute_run(config: RunConfig) -> Dict[str, Any]:
    """Execute one skeleton run inside the current (isolated) process."""
    # Re-validate the destination in the worker before any directory is created.
    protocol.validate_dataset_name(config.data_name)
    protocol.validate_method(config.method)
    protocol.validate_model_seed(config.model_seed)
    protocol.validate_shuffle_seed(config.method, config.shuffle_seed)
    protocol.validate_purpose(config.purpose)
    repo_root = Path(config.repo_root)
    if config.purpose == protocol.PURPOSE_FORMAL:
        expected = repo_root / "research" / "runs"
        if Path(config.output_root) != expected:
            raise RunError(
                f"formal output root must be {expected}, got {config.output_root}"
            )
        root = expected
    else:
        root = resolve_output_root(
            repo_root, config.purpose, Path(config.output_root)
        )
    if root.as_posix() != Path(config.output_root).as_posix():
        raise RunError(
            f"resolved output root {root} does not match the configured root "
            f"{config.output_root}"
        )
    run = artifacts.run_directory(root, config.run_id, config.run_type).reserve()
    durations: Dict[str, float] = {}
    stage = "init"
    total_started = time.perf_counter()
    failure: Optional[Dict[str, Any]] = None
    try:
        run.set_status(
            "running", stage=stage, purpose=config.purpose, method=config.method
        )
        _write_config(run, config)
        run.write_json(
            "command.json",
            {
                "argv": list(config.command),
                "python": sys.executable,
                "cwd": os.getcwd(),
                "launcher_cwd": config.launcher_cwd,
                "module": "benchmark.graph_value_skeleton",
                "replayable": bool(config.command),
            },
        )
        stage = "determinism"
        execution_settings = training.configure_determinism(config.model_seed)

        stage = "source_capture"
        source = artifacts.capture_source(
            run,
            repo_root,
            protocol_path=protocol.PROTOCOL_PATH,
        )
        stage = "environment"
        environment = artifacts.capture_environment(repo_root)
        run.write_json("environment.json", environment)
        artifacts.write_environment_snapshot(run, environment)
        if environment.get("gpu_available"):
            run.append_event(
                "gpu_available_not_used",
                note="execution is CPU-only; no CUDA tensor is created",
            )

        stage = "demand_read"
        started = time.perf_counter()
        dataset = data.load_dataset(
            config.data_name,
            demand_path=Path(config.demand_path) if config.demand_path else None,
            published=config.published,
        )
        durations["demand_read"] = time.perf_counter() - started

        stage = "graph_read"
        started = time.perf_counter()
        graph_published = config.graph_path is None
        graph = gvs_graph.load_graph(
            config.data_name,
            dataset.key_array,
            graph_path=Path(config.graph_path) if config.graph_path else None,
            published=graph_published,
        )
        coverage = data.load_neighbor_coverage(dataset, Path(graph.source_path))
        masks = data.build_masks(dataset, coverage)
        durations["graph_read"] = time.perf_counter() - started

        stage = "shuffle"
        started = time.perf_counter()
        shuffled: Optional[gvs_shuffle.ShuffledGraph] = None
        if config.method == protocol.METHOD_SHUFFLED:
            from . import prepared
            if config.shuffle_artifact:
                shuffled, generation = prepared.load(Path(config.shuffle_artifact),
                    keys=dataset.key_array, source_edges=graph.edges, data_name=config.data_name,
                    shuffle_seed=config.shuffle_seed, require_current_generator=True)
            else:
                shuffled = gvs_shuffle.shuffle_graph(
                    config.data_name, dataset.key_array, graph.edges, int(config.shuffle_seed),
                    progress=lambda payload: run.write_json('shuffle-progress.json', payload))
                generation = {'generator': prepared.generator_identity()}
            run.write_json('shuffle-preparation.json', {'artifact_path': config.shuffle_artifact,
                'reused': config.shuffle_artifact is not None, 'generation': generation,
                'read_or_generate_seconds': time.perf_counter() - started})
            message_edges = shuffled.edges
        elif config.method == protocol.METHOD_GRAPH:
            message_edges = graph.edges
        else:
            message_edges = np.zeros((0, 2), dtype=np.int64)
        durations["shuffle"] = time.perf_counter() - started

        stage = "naive_reference"
        started = time.perf_counter()
        (
            validation_naive,
            naive_scores,
            references,
            frozen_train_mean,
        ) = data.naive_reference_block(dataset)
        durations["naive_reference"] = time.perf_counter() - started

        stage = "mask_artifacts"
        started = time.perf_counter()
        _write_dataset_artifacts(run, dataset, graph, shuffled, masks, message_edges)
        durations["artifact_write"] = time.perf_counter() - started

        stage = "model_init"
        model = gvs_model.build_model(config.model_seed)
        measured_counts = gvs_model.parameter_counts(model)
        _assert_parameter_counts(measured_counts)
        signature = gvs_model.parameter_signature(model)
        if gvs_model.graph_only_parameter_names(model):
            raise RunError(
                "graph-only trainable parameters exist: "
                f"{gvs_model.graph_only_parameter_names(model)}"
            )

        stage = "training"
        started = time.perf_counter()
        # The training adjacency is the method's actual message graph: the
        # original graph for `graph`, the shuffled graph for `shuffled`, and no
        # edges for `self`.  Evaluation masks still come from the original graph.
        layout = gvs_graph.context_layout(dataset.key_array, message_edges)
        chunks = training.build_chunks(layout, node_count=dataset.node_count)
        if config.method == protocol.METHOD_SELF:
            chunks = [
                training.Chunk(
                    window_index=chunk.window_index,
                    window_start=chunk.window_start,
                    context=chunk.context,
                    node_indices=chunk.node_indices,
                    aggregation=gvs_model.GraphAggregation.identity(
                        int(chunk.node_indices.numel()), label="self"
                    ),
                    element_count=chunk.element_count,
                )
                for chunk in chunks
            ]
        training_edge_identity = _verify_training_edges(chunks, message_edges)
        train_inputs = dataset.input_windows(protocol.TRAIN_STARTS)
        train_targets = dataset.target_windows(protocol.TRAIN_STARTS)
        validation_inputs = dataset.input_windows(protocol.VALIDATION_STARTS)
        validation_targets = dataset.target_windows(protocol.VALIDATION_STARTS)
        validation_aggregation = (
            None
            if config.method == protocol.METHOD_SELF
            else gvs_model.GraphAggregation.from_edges(
                message_edges,
                dataset.node_count,
                label=f"{config.method} validation",
            )
        )
        test_aggregation = (
            None
            if config.method == protocol.METHOD_SELF
            else gvs_model.GraphAggregation.from_edges(
                message_edges, dataset.node_count, label=f"{config.method} test"
            )
        )
        # Recovery identity uses executing bytes, not mutable Git bookkeeping.
        # Commit changes alone do not change the computation being resumed.
        layout_hash = hashlib.sha256()
        for chunk in chunks:
            layout_hash.update(json.dumps([chunk.window_index, chunk.window_start,
                chunk.context, chunk.element_count]).encode())
            for tensor in (chunk.node_indices, chunk.aggregation.source, chunk.aggregation.target):
                layout_hash.update(tensor.numpy().tobytes())
        environment_keys = ('python_version', 'python_version_info', 'platform', 'system',
            'machine', 'processor', 'cpu_count', 'packages', 'torch', 'graph_extensions',
            'gpu_available', 'numpy_blas_config', 'thread_environment')
        identity = json.loads(json.dumps({
            'computation': config.computational_identity(), 'purpose': config.purpose,
            'source': {key: value.get('sha256') for key, value in source['files'].items()},
            'protocol': source.get('protocol', {}).get('sha256'),
            'environment': {key: environment.get(key) for key in environment_keys},
            'execution': execution_settings, 'dataset': dataset.identity_payload(),
            'source_edges': gvs_graph.edge_set_sha256(graph.edges),
            'message_edges': _message_edges_sha256(message_edges),
            'masks': masks.hashes(), 'chunks': layout_hash.hexdigest(),
        }, sort_keys=True))
        lineage = [uuid.uuid4().hex]
        resume_state = None
        recovery = {'schema': 1, 'run_id': config.run_id, 'ancestry': lineage,
                    'parent_checkpoint': None, 'completed_epoch_at_start': 0}
        if config.resume_from:
            resume_path = Path(config.resume_from)
            checkpoint_dir = resume_path if resume_path.is_dir() else resume_path.parent
            parent_status = checkpoint_dir.parent / 'status.json'
            if parent_status.exists() and json.loads(parent_status.read_text(encoding='utf-8')).get('state') == 'success':
                raise RunError('Successful runs are complete; resume requires an unfinished attempt')
            payload, manifest, raw = checkpoints.load(config.resume_from, identity)
            resume_state = payload['state']
            lineage = [*payload['lineage'], *lineage]
            recovery.update(ancestry=lineage, parent_checkpoint=manifest['sha256'],
                            completed_epoch_at_start=resume_state['epoch'])
            # Copy the validated parent input, not a reference to mutable parent files.
            run.write_bytes('recovery/input.npz', raw)
            run.write_json('recovery/input-manifest.json', manifest)
            # A crash during finalization must itself remain recoverable.
            run.write_bytes('checkpoints/' + manifest['file'], raw)
            run.write_json('checkpoints/latest.json', {**manifest, 'previous': None})
        run.write_json('recovery.json', recovery)
        epoch_durations = []
        checkpoint_io = 0.0
        progress = {'completed_epoch': recovery['completed_epoch_at_start'],
                    'checkpoint': recovery['parent_checkpoint'],
                    'remaining_seconds_estimate': None, 'estimate_samples': 0}

        def report_progress(detail):
            run.write_json('training-progress.json', {**progress, **detail,
                'updated_at': artifacts.now(), 'attempt_wall_seconds': time.perf_counter() - total_started,
                'checkpoint_io_seconds_this_attempt': checkpoint_io, 'completion': False})

        def commit_epoch(state, epoch_seconds):
            nonlocal checkpoint_io
            io_started = time.perf_counter()
            manifest = checkpoints.publish(run.path / 'checkpoints', state, identity, lineage)
            checkpoint_io += time.perf_counter() - io_started
            epoch_durations.append(epoch_seconds + time.perf_counter() - io_started)
            recent = epoch_durations[-5:]
            progress.update(completed_epoch=state['epoch'], checkpoint=manifest['sha256'],
                training_seconds=state['training_seconds'], validation_seconds=state['validation_seconds'],
                last_epoch_seconds=epoch_durations[-1], estimate_samples=len(recent),
                remaining_seconds_estimate=(200-state['epoch']) * (sum(recent)/len(recent)),
                optimizer_steps=state['epoch'])
            report_progress({'stage': 'epoch_committed'})

        run.set_status('running', stage='training', purpose=config.purpose, method=config.method)
        report_progress({'stage': 'training_ready'})
        result = training.train(
            model,
            train_inputs=train_inputs,
            train_targets=train_targets,
            validation_inputs=validation_inputs,
            validation_targets=validation_targets,
            chunks=chunks,
            validation_aggregation=validation_aggregation,
            node_count=dataset.node_count,
            resume_state=resume_state,
            checkpoint_callback=commit_epoch,
            progress_callback=report_progress,
        )
        durations["training"] = result.training_seconds - (resume_state['training_seconds'] if resume_state else 0.)
        durations["validation"] = result.validation_seconds - (resume_state['validation_seconds'] if resume_state else 0.)
        durations['cumulative_training'] = result.training_seconds
        durations['cumulative_validation'] = result.validation_seconds
        durations['checkpoint_io_this_attempt'] = checkpoint_io
        durations["training_total"] = time.perf_counter() - started

        stage = "selection"
        started = time.perf_counter()
        _write_selection_artifacts(
            run,
            config,
            dataset,
            graph,
            shuffled,
            masks,
            references,
            naive_scores,
            result,
            measured_counts,
            signature,
            execution_settings,
            training_edge_identity,
        )
        durations["selection_write"] = time.perf_counter() - started

        stage = "selected_inference"
        started = time.perf_counter()
        test_inputs = dataset.input_windows(protocol.TEST_STARTS)
        test_targets = dataset.target_windows(protocol.TEST_STARTS)
        validation_predictions, test_predictions = training.selected_predictions(
            model,
            result.selected_state,
            validation_inputs=validation_inputs,
            test_inputs=test_inputs,
            validation_aggregation=validation_aggregation,
            test_aggregation=test_aggregation,
        )
        durations["selected_inference"] = time.perf_counter() - started
        # The selected checkpoint is the one whose parameters were saved.
        selected_model = gvs_model.build_model(config.model_seed, torch_seed=False)
        gvs_model.load_state_arrays(selected_model, gvs_model.state_arrays(model))
        run.save_npz(
            "models/selected.npz",
            **gvs_model.state_arrays(selected_model),
            parameter_count_gru=np.array([measured_counts["gru"]], dtype=np.int64),
            parameter_count_head=np.array([measured_counts["head"]], dtype=np.int64),
            parameter_count_graph_only=np.array(
                [measured_counts["graph_only"]], dtype=np.int64
            ),
            parameter_count_total=np.array([measured_counts["total"]], dtype=np.int64),
            parameter_names=np.array(sorted(signature)),
            named_tensor_map=np.array(
                json.dumps(
                    {
                        name: "torch GRU/Linear parameter"
                        for name in sorted(signature)
                    },
                    sort_keys=True,
                )
            ),
        )

        stage = "metrics_output"
        started = time.perf_counter()
        test_naive = baselines.naive_predictions(
            dataset.signal,
            protocol.TEST_STARTS,
            frozen_train_mean=frozen_train_mean,
            train_mean_method=p01.MAIN_SPLIT.train_mean_method,
        )
        metrics_payload = _build_metrics(
            config=config,
            dataset=dataset,
            masks=masks,
            references=references,
            validation_gold=validation_targets,
            test_gold=test_targets,
            validation_naive=validation_naive,
            test_naive=test_naive,
            validation_model=validation_predictions,
            test_model=test_predictions,
            coverage_source=coverage.provenance.get("source"),
        )
        run.write_json("metrics.json", metrics_payload)
        _write_prediction_artifacts(
            run,
            validation_gold=validation_targets,
            test_gold=test_targets,
            validation_naive=validation_naive,
            test_naive=test_naive,
            validation_model=validation_predictions,
            test_model=test_predictions,
            method=config.method,
        )
        durations["metrics_output"] = time.perf_counter() - started

        stage = "source_verification"
        captured = source.get("protocol") if isinstance(source, Mapping) else None
        captured_protocol_sha = (
            captured.get("sha256") if isinstance(captured, Mapping) else None
        )
        manifest = artifacts.source_manifest(
            demand_path=Path(dataset.demand.source_path),
            demand_sha256=dataset.demand.source_sha256,
            protocol_path=protocol.PROTOCOL_PATH,
            protocol_sha256=captured_protocol_sha or "<unavailable>",
            graph_path=Path(graph.source_path),
            graph_sha256=graph.source_sha256,
        )
        manifest["node_keys_sha256"] = dataset.identity_payload()["node_keys_sha256"]
        manifest["graph_edges_sha256"] = gvs_graph.edge_set_sha256(graph.edges)
        manifest["message_edges_sha256"] = _message_edges_sha256(message_edges)
        # Revisit every captured execution-source file and the captured protocol
        # identity, so a mid-run edit cannot finish under stale provenance.
        captured_mismatches = artifacts.verify_captured_source(source, repo_root)
        mismatches = artifacts.verify_source_hashes(manifest) + captured_mismatches
        manifest["captured_source_verification"] = {
            "files_checked": len(
                (source.get("files") or {}) if isinstance(source, Mapping) else {}
            ),
            "protocol_checked": captured_protocol_sha is not None,
            "mismatches": list(captured_mismatches),
        }
        manifest["captured_runtime_sources"] = {
            relative: {
                "path": str(Path(repo_root) / relative),
                "sha256": entry.get("sha256"),
            }
            for relative, entry in (source.get("files") or {}).items()
            if isinstance(entry, Mapping) and entry.get("sha256")
        }
        run.write_json("source-sha256.json", manifest)
        if mismatches:
            run.append_event("source_hash_mismatch", mismatches=mismatches)
            raise RunError(
                "source files changed during the run: " + "; ".join(mismatches)
            )

        stage = "provenance"
        run.write_json(
            "provenance.json",
            _provenance_payload(
                config=config,
                dataset=dataset,
                graph=graph,
                shuffled=shuffled,
                masks=masks,
                message_edges=message_edges,
                training_edge_identity=training_edge_identity,
                references=references,
                measured_counts=measured_counts,
                environment=environment,
                source=source,
                execution_settings=execution_settings,
                recovery=recovery,
            ),
        )

        stage = "measurements"
        durations["total"] = time.perf_counter() - total_started
        measurements = _measurements_payload(
            config=config,
            dataset=dataset,
            graph=graph,
            message_edges=message_edges,
            result=result,
            durations=durations,
            environment=environment,
            execution_settings=execution_settings,
        )
        run.write_json("measurements.json", measurements)

        stage = "summary"
        run.write_text(
            "summary.md",
            summary_text(
                config=config,
                dataset=dataset,
                graph=graph,
                shuffled=shuffled,
                references=references,
                result=result,
                measurements=measurements,
            ),
        )
        run.set_status(
            "success",
            stage="complete",
            purpose=config.purpose,
            method=config.method,
            model_seed=config.model_seed,
            shuffle_seed=config.shuffle_seed,
            total_seconds=durations["total"],
            nodes=dataset.node_count,
            edges=int(message_edges.shape[0]),
            selected_epoch=result.selected_epoch,
        )
        run.finalize_artifacts_manifest()
        run.append_event(
            "run_success",
            nodes=dataset.node_count,
            method=config.method,
            selected_epoch=result.selected_epoch,
        )
        return {
            "run_id": config.run_id,
            "run_dir": str(run.path),
            "status": "success",
            "state": "success",
            "selected_epoch": result.selected_epoch,
        }
    except KeyboardInterrupt as exc:
        failure = _failure_record(stage, exc, "interrupted")
        run.set_status("interrupted", stage=stage, error=failure)
        _write_failure_evidence(run, config, failure, durations)
        run.append_event("run_interrupted", stage=stage)
        raise RunInterrupted(f"interrupted during {stage}") from exc
    except RunInterrupted as exc:
        failure = _failure_record(stage, exc, "interrupted")
        run.set_status("interrupted", stage=stage, error=failure)
        _write_failure_evidence(run, config, failure, durations)
        run.append_event("run_interrupted", stage=stage)
        raise
    except BaseException as exc:  # noqa: BLE001 - preserve every failure as evidence
        if isinstance(exc, gvs_shuffle.ShuffleError):
            run.write_json('shuffle-failure.json', exc.diagnostics)
        failure = _failure_record(stage, exc, "failed")
        run.set_status("failed", stage=stage, error=failure)
        _write_failure_evidence(run, config, failure, durations)
        run.append_event("run_failed", stage=stage, error_type=type(exc).__name__)
        raise


def _verify_training_edges(
    chunks: Sequence[training.Chunk], message_edges: np.ndarray
) -> Dict[str, Any]:
    """Prove every training window used the method's actual message graph."""
    expected = gvs_graph.canonical_edge_array(message_edges)
    chunk_edges = training.chunk_global_edges(chunks)
    expected_windows = list(range(len(protocol.TRAIN_STARTS)))
    if sorted(chunk_edges) != expected_windows:
        raise RunError(
            "training chunks do not cover exactly the 19 training windows: "
            f"{sorted(chunk_edges)}"
        )
    for window_index, window_edges in sorted(chunk_edges.items()):
        if not np.array_equal(window_edges, expected):
            raise RunError(
                "training chunk edges differ from the method message graph at "
                f"window index {window_index}: {window_edges.shape[0]} chunk "
                f"edges vs {expected.shape[0]} message edges"
            )
    return {
        "method": "chunk-local edges converted to canonical global indices",
        "edges_sha256": gvs_graph.edge_set_sha256(expected),
        "edge_count": int(expected.shape[0]),
        "windows_verified": len(chunk_edges),
        "matches_message_edges": True,
    }


def _assert_parameter_counts(counts: Mapping[str, int]) -> None:
    expected = protocol.PARAMETER_COUNTS
    measured = {
        "gru": int(counts.get("gru", 0)),
        "head": int(counts.get("head", 0)),
        "total": int(counts.get("total", 0)),
    }
    if measured != dict(expected):
        raise RunError(
            f"measured trainable parameter counts {measured} != frozen {dict(expected)}"
        )
    if int(counts.get("graph_only", 0)) != 0:
        raise RunError(
            f"graph-only trainable parameters exist: {counts.get('graph_only')}"
        )


def _write_config(run: artifacts.RunDirectory, config: RunConfig) -> None:
    run.write_json(
        "config.json",
        {
            "protocol_version": protocol.SCIENTIFIC_PROTOCOL_VERSION,
            "skeleton_version": protocol.SKELETON_VERSION,
            "records_policy": protocol.RECORDS_POLICY,
            "task": protocol.TASK_ID,
            "change": protocol.CHANGE_NAME,
            "design_decision": protocol.DESIGN_DECISION,
            "spec": config.to_dict(),
            "computational": config.computational_identity(),
            "parameter_counts_expected": dict(protocol.PARAMETER_COUNTS),
            "model_definition": protocol.MODEL_DEFINITION,
            "seed_profile": protocol.seed_profile(config.model_seed),
            "evidence_role": (
                "development (not scientific acceptance)"
                if config.purpose == protocol.PURPOSE_DEVELOPMENT
                else "formal (requires separate research authorization)"
            ),
        },
    )


def _write_dataset_artifacts(
    run: artifacts.RunDirectory,
    dataset: data.SkeletonDataset,
    graph: gvs_graph.GraphData,
    shuffled: Optional[gvs_shuffle.ShuffledGraph],
    masks: data.MaskBundle,
    message_edges: np.ndarray,
) -> None:
    import pandas as pd

    frame = pd.DataFrame(dataset.key_array, columns=list(dataset.key_columns))
    frame.insert(0, "node_index", np.arange(dataset.node_count, dtype=np.int64))
    run.save_dataframe("nodes.parquet", frame)
    run.write_json("windows.json", protocol.window_metadata())
    run.save_npz("masks.npz", **masks.arrays())
    audit = dict(dataset.audit)
    audit["masks"] = {
        **masks.payload,
        "array_sha256": masks.hashes(),
    }
    audit["identity"] = dataset.identity_payload()
    run.write_json("audit.json", audit)
    graph_audit = dict(graph.audit)
    graph_audit["message_edges"] = {
        "method": "self/graph/shuffled selection",
        "edges": int(message_edges.shape[0]),
        "edges_sha256": _message_edges_sha256(message_edges),
        "binary_unique_directed": True,
    }
    run.save_npy("graph/source-edges.npy", graph.edges)
    run.save_npy("graph/edges.npy", message_edges)
    if shuffled is not None:
        graph_audit["shuffle"] = shuffled.audit
    run.write_json("graph-audit.json", graph_audit)


def _write_selection_artifacts(
    run: artifacts.RunDirectory,
    config: RunConfig,
    dataset: data.SkeletonDataset,
    graph: gvs_graph.GraphData,
    shuffled: Optional[gvs_shuffle.ShuffledGraph],
    masks: data.MaskBundle,
    references: Mapping[str, Any],
    naive_scores: Mapping[str, float],
    result: training.TrainingResult,
    measured_counts: Mapping[str, int],
    signature: Mapping[str, Sequence[int]],
    execution_settings: Mapping[str, Any],
    training_edge_identity: Mapping[str, Any],
) -> None:
    run.write_json(
        "training-history.json",
        {
            "run_id": config.run_id,
            "method": config.method,
            "model_seed": config.model_seed,
            "shuffle_seed": config.shuffle_seed,
            "epochs": result.epochs,
            "rows": result.history,
            "selected_epoch": result.selected_epoch,
            "selected_validation_MSE": result.selected_validation_mse,
            "selection": result.selection_payload,
            "measurement_timing": {
                "train": (
                    "train_MSE/MAE are reduced over the epoch's pre-update "
                    "training pass (all 19 windows and all nodes/horizons)"
                ),
                "validation": (
                    "validation_MSE/MAE are measured after the epoch's single "
                    "optimizer step"
                ),
            },
        },
    )
    run.write_json(
        "selection.json",
        {
            "run_id": config.run_id,
            "method": config.method,
            "model_seed": config.model_seed,
            "shuffle_seed": config.shuffle_seed,
            "naive_references": dict(references),
            "naive_validation_scores": dict(naive_scores),
            "training": {
                **result.selection_payload,
                "selected_reason": (
                    "lowest validation MSE over all 200 epochs; on an exact "
                    "validation-MSE tie the earliest epoch is selected"
                ),
            },
            "parameter_counts_measured": dict(measured_counts),
            "parameter_counts_expected": dict(protocol.PARAMETER_COUNTS),
            "parameter_signature": {
                name: list(shape) for name, shape in signature.items()
            },
            "graph_only_trainable_parameters": [],
            "model_seed_torch_map_location": "cpu",
            "execution_settings": dict(execution_settings),
            "shuffle": (
                dict(shuffled.identity_payload()) if shuffled is not None else None
            ),
            "graph_identity": {
                "source_edges_sha256": gvs_graph.edge_set_sha256(graph.edges),
                "source_path": graph.source_path,
                "source_sha256": graph.source_sha256,
            },
            "training_edges": dict(training_edge_identity),
            "mask_sha256": masks.hashes(),
            "test_labels_used_for_selection": False,
            "test_labels_available_to_training": False,
            "selection_frozen_before_test_evaluation": True,
            "dataset_identity": dataset.identity_payload(),
        },
    )


def _build_metrics(
    *,
    config: RunConfig,
    dataset: data.SkeletonDataset,
    masks: data.MaskBundle,
    references: Mapping[str, Any],
    validation_gold: np.ndarray,
    test_gold: np.ndarray,
    validation_naive: Mapping[str, np.ndarray],
    test_naive: Mapping[str, np.ndarray],
    validation_model: np.ndarray,
    test_model: np.ndarray,
    coverage_source: Optional[str],
) -> Dict[str, Any]:
    activity_masks = dict(masks.activity_groups)
    constant_masks = p01_metrics.constant_group_masks(
        masks.constant_mask, scope="train27"
    )
    context_masks_map = p01_metrics.context_masks(dataset.context_values)
    neighbor_masks = p01_metrics.neighbor_group_masks(masks.neighbor_mask)
    reports: Dict[str, Dict[str, Any]] = {"validation": {}, "test": {}}
    for split, starts, gold, naive, model_prediction in (
        (
            "validation",
            protocol.VALIDATION_STARTS,
            validation_gold,
            validation_naive,
            validation_model,
        ),
        (
            "test",
            protocol.TEST_STARTS,
            test_gold,
            test_naive,
            test_model,
        ),
    ):
        predictions = dict(naive)
        predictions[config.method] = model_prediction
        for name, pred in predictions.items():
            report = p01_metrics.split_report(
                pred,
                gold,
                starts=starts,
                activity_masks=activity_masks,
                constant_masks=constant_masks,
                context_masks_map=context_masks_map,
                neighbor_masks=neighbor_masks,
                group_names=p01.ACTIVITY_GROUP_NAMES,
                inactive_group_name="inactive",
            )
            report["method"] = name
            report["split"] = split
            report["dataset"] = config.data_name
            report["nonself_neighbor_coverage_source"] = coverage_source
            reports[split][name] = report
    relative: Dict[str, Any] = {}
    reference_names = [
        name
        for name in (references.get("NaiveRef"), references.get("NaiveRef6"))
        if name is not None
    ]
    for split in ("validation", "test"):
        relative[split] = p01_metrics.baseline_relative_comparison(
            reports[split],
            activity_groups=p01.ACTIVITY_GROUP_NAMES,
            context_names=list(context_masks_map),
            neighbor_names=list(neighbor_masks),
            model_names=[config.method],
            reference_names=reference_names,
        )
    return {
        "protocol_version": protocol.SCIENTIFIC_PROTOCOL_VERSION,
        "skeleton_version": protocol.SKELETON_VERSION,
        "records_policy": protocol.RECORDS_POLICY,
        "dataset": config.data_name,
        "mode": "count",
        "run_id": config.run_id,
        "purpose": config.purpose,
        "method": config.method,
        "model_method": config.method,
        "model_seed": config.model_seed,
        "shuffle_seed": config.shuffle_seed,
        "references": dict(references),
        "relative_gains": relative,
        "methods": reports,
        "activity_groups": list(p01.ACTIVITY_GROUP_NAMES),
        "constant_groups": ["constant_train27", "nonconstant_train27"],
        "neighbor_groups": ["has_nonself_neighbor", "no_nonself_neighbor"],
        "contexts": list(context_masks_map),
        "aggregation_note": (
            "overall RMSE = sqrt(mean squared error over all window-node-horizon "
            "elements), never the mean of window RMSE values; test target-month "
            "multiplicities are 1,2,3,3,2,1 and are not independent samples; "
            "shuffled member MAEs are averaged arithmetically, never the MAE of "
            "averaged predictions"
        ),
        "evidence_role": (
            "development (not scientific acceptance)"
            if config.purpose == protocol.PURPOSE_DEVELOPMENT
            else "formal (requires separate research authorization)"
        ),
    }


def _write_prediction_artifacts(
    run: artifacts.RunDirectory,
    *,
    validation_gold: np.ndarray,
    test_gold: np.ndarray,
    validation_naive: Mapping[str, np.ndarray],
    test_naive: Mapping[str, np.ndarray],
    validation_model: np.ndarray,
    test_model: np.ndarray,
    method: str,
) -> None:
    run.save_npy("gold/validation.npy", validation_gold)
    run.save_npy("gold/test.npy", test_gold)
    run.write_json("gold/dtype.json", {"dtype": str(validation_gold.dtype)})
    for split, naive, model_prediction in (
        ("validation", validation_naive, validation_model),
        ("test", test_naive, test_model),
    ):
        for name, pred in naive.items():
            run.save_npy(f"predictions/{name}/{split}.npy", pred)
        run.save_npy(f"predictions/{method}/{split}.npy", model_prediction)


def _provenance_payload(
    *,
    config: RunConfig,
    dataset: data.SkeletonDataset,
    graph: gvs_graph.GraphData,
    shuffled: Optional[gvs_shuffle.ShuffledGraph],
    masks: data.MaskBundle,
    message_edges: np.ndarray,
    training_edge_identity: Mapping[str, Any],
    references: Mapping[str, Any],
    measured_counts: Mapping[str, int],
    environment: Mapping[str, Any],
    source: Mapping[str, Any],
    execution_settings: Mapping[str, Any],
    recovery: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "run_id": config.run_id,
        "recovery": dict(recovery) if recovery is not None else None,
        "run_type": config.run_type,
        "purpose": config.purpose,
        "task": protocol.TASK_ID,
        "change": protocol.CHANGE_NAME,
        "design_decision": protocol.DESIGN_DECISION,
        "dataset": config.data_name,
        "mode": "count",
        "method": config.method,
        "model_seed": config.model_seed,
        "shuffle_seed": config.shuffle_seed,
        "seed_profile": protocol.seed_profile(config.model_seed),
        "scientific_protocol": protocol.protocol_identity(),
        "records_policy": protocol.policy_identity(Path(config.repo_root)),
        "skeleton_version": protocol.SKELETON_VERSION,
        "model_definition": protocol.MODEL_DEFINITION,
        "preprocessing": protocol.PREPROCESSING,
        "parameter_counts_measured": dict(measured_counts),
        "created": artifacts.now(),
        "git": {
            "commit": source.get("commit"),
            "dirty": source.get("whole_repository_dirty"),
            "scoped_dirty": source.get("scoped_dirty"),
            "identity_available": source.get("identity_available"),
            "errors": source.get("errors"),
            "scope": "source.json",
        },
        "demand": dataset.identity_payload(),
        "graph": graph.identity_payload(),
        "graph_used": {
            "method": config.method,
            "propagates_messages": config.method != protocol.METHOD_SELF,
            "shuffled": shuffled is not None,
            "message_edges": int(message_edges.shape[0]),
            "message_edges_sha256": _message_edges_sha256(message_edges),
            "shuffle_identity": (
                shuffled.identity_payload() if shuffled is not None else None
            ),
            "training_edges": dict(training_edge_identity),
        },
        "masks": {
            **masks.payload,
            "array_sha256": masks.hashes(),
        },
        "naive_reference": {
            "NaiveRef": references.get("NaiveRef"),
            "NaiveRef6": references.get("NaiveRef6"),
            "published_expected": protocol.NAIVE_REF_PUBLISHED,
            "published_identity_checked": bool(dataset.published),
            "selection_metric": "validation MSE",
        },
        "environment": {
            "python_version": environment.get("python_version"),
            "packages": environment.get("packages"),
            "torch": environment.get("torch"),
            "graph_extensions": environment.get("graph_extensions"),
            "platform": environment.get("platform"),
            "machine": environment.get("machine"),
            "cpu_count": environment.get("cpu_count"),
            "thread_environment": environment.get("thread_environment"),
            "gpu_available": environment.get("gpu_available"),
            "execution_settings": dict(execution_settings),
        },
        "source_capture": {
            "file": "source.json",
            "commit": source.get("commit"),
            "scoped_dirty": source.get("scoped_dirty"),
            "patch_path": source.get("patch_path"),
            "patch_bytes": source.get("patch_bytes"),
            "unrecoverable_paths": source.get("unrecoverable_paths"),
        },
        "scientific_acceptance": False,
        "evidence_role": (
            "development (not scientific acceptance evidence)"
            if config.purpose == protocol.PURPOSE_DEVELOPMENT
            else "formal (requires separate research authorization)"
        ),
        "implementation_readiness_does_not_establish_predictive_benefit": True,
    }


def _measurements_payload(
    *,
    config: RunConfig,
    dataset: data.SkeletonDataset,
    graph: gvs_graph.GraphData,
    message_edges: np.ndarray,
    result: training.TrainingResult,
    durations: Mapping[str, float],
    environment: Mapping[str, Any],
    execution_settings: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "run_id": config.run_id,
        "dataset": config.data_name,
        "method": config.method,
        "model_seed": config.model_seed,
        "shuffle_seed": config.shuffle_seed,
        "timings_seconds": dict(durations),
        "totals_seconds": {
            "data_reading": durations.get("demand_read", 0.0)
            + durations.get("graph_read", 0.0),
            "shuffling": durations.get("shuffle", 0.0),
            "training_and_validation": durations.get("training_total", 0.0),
            "training_forward_backward": durations.get("training", 0.0),
            "validation_scoring": durations.get("validation", 0.0),
            "selected_inference": durations.get("selected_inference", 0.0),
            "output_writing": durations.get("metrics_output", 0.0)
            + durations.get("artifact_write", 0.0)
            + durations.get("selection_write", 0.0),
            "total": durations.get("total", 0.0),
        },
        "peak_memory": artifacts.measure_peak_rss(),
        "device": "cpu",
        "input": {
            "nodes": dataset.node_count,
            "source_edges": graph.edge_count,
            "message_edges": int(message_edges.shape[0]),
            "epochs": result.epochs,
            "training_windows": len(protocol.TRAIN_STARTS),
            "training_chunks_per_epoch": result.chunk_count,
            "training_elements_per_epoch": result.total_elements,
        },
        "machine": {
            "platform": environment.get("platform"),
            "system": environment.get("system"),
            "machine": environment.get("machine"),
            "processor": environment.get("processor"),
            "cpu_count": environment.get("cpu_count"),
        },
        "threads": {
            "torch_intra_op": execution_settings.get("torch_intra_op_threads"),
            "torch_inter_op": execution_settings.get("torch_inter_op_threads"),
            "blas_environment": execution_settings.get("blas_thread_environment"),
        },
        "cost_scope": {
            "input_kind": "published_data" if dataset.published else "synthetic_fixture",
            "fixture": not dataset.published,
            "label": (
                "development measurement on published data"
                if dataset.published
                else "development measurement on a synthetic fixture"
            ),
            "is_formal_performance_evidence": False,
            "is_scientific_evidence": False,
        },
        "stage_definitions": {
            "demand_read": "read, validate and canonically order the demand source",
            "graph_read": "read, audit and map the graph; derive coverage and masks",
            "shuffle": "build the shuffled control (zero for self/graph)",
            "naive_reference": "five naive baselines and validation-MSE references",
            "artifact_write": "identity, mask and graph artifacts",
            "training": "200 epochs of chunked forward/backward and optimizer steps",
            "validation": "post-update validation scoring inside each epoch",
            "selection_write": "history and selection records",
            "selected_inference": "selected-checkpoint validation/test prediction",
            "metrics_output": "metric reduction and prediction/gold writing",
            "total": "whole worker execution",
        },
        "notes": [
            "durations and peak RSS are measured for this execution only",
            "no unmeasured performance or graph-benefit promise is recorded",
        ],
    }


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
    config: RunConfig,
    failure: Mapping[str, Any],
    durations: Mapping[str, float],
) -> None:
    try:
        run.write_json(
            "failure.json",
            {
                "run_id": config.run_id,
                "dataset": config.data_name,
                "method": config.method,
                "model_seed": config.model_seed,
                "shuffle_seed": config.shuffle_seed,
                "failure": dict(failure),
                "timings_seconds": dict(durations),
                "peak_memory": artifacts.measure_peak_rss(),
                "completed_artifacts": [
                    path.relative_to(run.path).as_posix()
                    for path in run.iter_files()
                ],
            },
        )
    except Exception:  # pragma: no cover - evidence writing must not mask cause
        pass


def summary_text(
    *,
    config: RunConfig,
    dataset: data.SkeletonDataset,
    graph: gvs_graph.GraphData,
    shuffled: Optional[gvs_shuffle.ShuffledGraph],
    references: Mapping[str, Any],
    result: training.TrainingResult,
    measurements: Mapping[str, Any],
) -> str:
    lines = [
        f"# Run {config.run_id}",
        "",
        f"- Task: `{protocol.TASK_ID}` ({protocol.CHANGE_NAME})",
        f"- Dataset: `{config.data_name}/count`",
        f"- Method: `{config.method}`"
        + (
            f" (shuffle seed {config.shuffle_seed})"
            if config.shuffle_seed is not None
            else ""
        ),
        f"- Model seed: {config.model_seed}",
        f"- Protocol: `{protocol.SCIENTIFIC_PROTOCOL_VERSION}`; skeleton "
        f"`{protocol.SKELETON_VERSION}`; policy `{protocol.RECORDS_POLICY}`",
        f"- Purpose: `{config.purpose}`"
        + (
            " (development output; not scientific acceptance evidence)"
            if config.purpose == protocol.PURPOSE_DEVELOPMENT
            else " (formal experiment; requires separate authorization)"
        ),
        f"- Nodes: {dataset.node_count}",
        f"- Source graph: {graph.edge_count} unique directed edges "
        f"({graph.raw_rows} raw rows)",
        f"- Message edges: {int(shuffled.edge_count) if shuffled is not None else graph.edge_count if config.method == protocol.METHOD_GRAPH else 0}",
        f"- Selected epoch: {result.selected_epoch} "
        f"(validation MSE {result.selected_validation_mse:.6f})",
        f"- NaiveRef: `{references.get('NaiveRef')}` (validation MSE, frozen)",
        f"- Trainable parameters: {protocol.PARAMETER_COUNTS['total']} "
        f"(GRU {protocol.PARAMETER_COUNTS['gru']} + head {protocol.PARAMETER_COUNTS['head']})",
        "",
        "## Measured costs",
        "",
        f"- Total: {measurements['totals_seconds']['total']:.3f} s",
        f"- Data/graph reading: {measurements['totals_seconds']['data_reading']:.3f} s",
        f"- Shuffling: {measurements['totals_seconds']['shuffling']:.3f} s",
        f"- Training + validation: "
        f"{measurements['totals_seconds']['training_and_validation']:.3f} s",
        f"- Selected inference: "
        f"{measurements['totals_seconds']['selected_inference']:.3f} s",
        f"- Peak RSS: {measurements['peak_memory'].get('bytes')} bytes "
        f"({measurements['peak_memory'].get('native_value')} "
        f"{measurements['peak_memory'].get('native_unit')}, scope "
        f"{measurements['peak_memory'].get('scope')})",
        f"- Cost scope: {measurements['cost_scope']['label']}",
        "",
        "## Status",
        "",
        "A successful run records implementation evidence only. It does not",
        "assert scientific acceptance, predictive benefit, packaging, Git",
        "inclusion or backup completion. The published graph construction",
        "cutoff time is unknown, so fixed-evaluation-period results are not",
        "strictly historical.",
        "",
    ]
    return "\n".join(lines)
