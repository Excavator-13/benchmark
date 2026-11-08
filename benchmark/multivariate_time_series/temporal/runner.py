"""Stage runners: fit/resume, select, diagnose and report artifact assembly.

These functions are the only place where a run directory is written.  They are
usable in-process (tests inject data, clock, sampler and checkpoint publication)
and are what the CLI worker subprocess calls for a real fit.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

import numpy as np

from benchmark.nograph_baseline import protocol as p01

from . import artifacts, checkpoints, checks, data as temporal_data, diagnostics as temporal_diagnostics
from . import engine as temporal_engine
from . import model as temporal_model
from . import protocol, recovery, report as temporal_report, resources, selection as temporal_selection

PauseRequest = temporal_engine.PauseRequest


class RunnerError(protocol.ProtocolError):
    """Raised when a stage request cannot be executed."""


def _clock() -> Callable[[], float]:
    return time.monotonic


def _run_paths(request: Mapping[str, Any], purpose: str, repo: Optional[Path]) -> Path:
    root = Path(request["output_root"]) if request.get("output_root") else artifacts.default_root(
        purpose, repo
    )
    return root / str(request["run_id"])


def _write_preamble(
    run: Any,
    *,
    request: Mapping[str, Any],
    purpose: str,
    operation: str,
    dataset_document: Mapping[str, Any],
    config_payload: Mapping[str, Any],
    protocol_controls: Mapping[str, Any],
    roles: Mapping[str, Any],
    condition: Mapping[str, Any],
    data_identity: Mapping[str, Any],
    config_extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    config_doc: Dict[str, Any] = {
        "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
        "scientific_version": protocol.SCIENTIFIC_VERSION,
        "run_id": run.run_id,
        "operation": operation,
        "purpose": purpose,
        "dataset": dict(dataset_document),
        "config": dict(config_payload),
        "protocol_controls": dict(protocol_controls),
        "roles": dict(roles),
        "condition": dict(condition),
        "split": protocol.split_payload(),
    }
    if config_extra:
        config_doc.update(config_extra)
    run.write_json("config.json", config_doc)
    artifacts.write_command(run, request.get("argv") or [], operation=operation)
    source_record = artifacts.capture_source(run)
    environment = artifacts.write_environment(run)
    provenance = artifacts.provenance_payload(
        purpose=purpose,
        operation=operation,
        config=config_payload,
        roles=roles,
        data_identity=data_identity,
        source_record=source_record,
        environment=environment,
        extra=(
            {"parent": config_extra.get("parent")}
            if config_extra and config_extra.get("parent")
            else None
        ),
    )
    run.write_json("provenance.json", provenance)
    return {"config": config_doc, "provenance": provenance, "environment": environment}


def _dataset_document(temporal: temporal_data.TemporalData) -> Dict[str, Any]:
    return {
        "name": temporal.dataset,
        "mode": temporal.mode,
        "key_columns": list(temporal.key_columns),
        "nodes": temporal.node_count,
    }


def _condition(
    config: protocol.FitConfig, temporal: temporal_data.TemporalData
) -> Dict[str, Any]:
    identity = temporal.identity()
    return protocol.condition_identity(
        config,
        dataset=temporal.dataset,
        mode=temporal.mode,
        data_sha256=identity["source_sha256"],
        keys_sha256=identity["node_keys_sha256"],
        protocol_sha256=protocol.protocol_content_sha256(),
    )


def _fit_report(
    *,
    result: temporal_engine.FitResult,
    config: protocol.FitConfig,
    recovery_sha256: Optional[str],
    cost: Mapping[str, Any],
) -> Dict[str, Any]:
    best = result.best
    return {
        "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
        "scientific_version": protocol.SCIENTIFIC_VERSION,
        "kind": "fit-summary",
        "status": result.status,
        "purpose": None,
        "protocol_controls": {
            "complete": config.complete_protocol,
            "deviations": config.deviations(),
        },
        "config": config.to_payload(),
        "selected_epoch": best["epoch"],
        "selected_updates": best["updates"],
        "validation": {
            "best": {
                "MSE": best["validation"]["MSE"],
                "MAE": best["validation"]["MAE"],
                "epoch": best["epoch"],
            },
            "initial": result.initial_validation,
        },
        "history_epochs": len(result.history),
        "total_updates": result.updates,
        "parameter_count": result.parameter_count,
        "preprocessing_scale": result.scale,
        "reproduction": (result.scores.get("best") or {}).get("reproduction"),
        "recovery_sha256": recovery_sha256,
        "cost": dict(cost),
        "paused": result.pause,
        "warnings": list(result.warnings),
    }


def _fit_summary_text(
    *,
    run_id: str,
    operation: str,
    purpose: str,
    config: protocol.FitConfig,
    result: temporal_engine.FitResult,
    data_identity: Mapping[str, Any],
    cost: Mapping[str, Any],
) -> str:
    best = result.best
    lines = [
        f"# {run_id}",
        "",
        f"- operation: {operation}",
        f"- purpose: {purpose}",
        f"- encoder: {config.model}, seed {config.seed}, learning rate "
        f"{config.learning_rate:g}",
        f"- protocol controls complete: {config.complete_protocol}",
        f"- dataset: {data_identity.get('dataset')} "
        f"({data_identity.get('nodes')} nodes)",
        f"- demand source: {data_identity.get('source_path')}",
        f"- status: {result.status}",
        f"- completed epochs: {result.completed_epoch} / {config.epochs}",
        f"- selected checkpoint: epoch {best['epoch']} "
        f"(updates {best['updates']})",
        f"- best validation MSE / MAE: {best['validation']['MSE']:.6g} / "
        f"{best['validation']['MAE']:.6g}",
        f"- training-only RMS scale: {result.scale:.6g}",
        f"- test labels used during fit: no",
        "",
        "## Evidence",
        "",
        "- per-epoch validation history: `history.json`",
        "- fixed-parameter scores (init/10/50/100/best): `scores.json`",
        "- update/clip records: `gradients.json`",
        "- validation predictions/labels: `validation/`",
        "- selected weights: `weights/best.pt`",
        "- recoverable last state: `recovery/last.pt`",
        "- cost sample and estimate: `cost.json`",
        "",
        "## Cost sample",
        "",
        f"- status: {cost.get('status')}",
        f"- measured sample seconds: {cost.get('sample_measured_seconds')}",
        f"- steady-state median epoch seconds: "
        f"{cost.get('steady_state_median_seconds')}",
        f"- estimated full fit seconds: {cost.get('estimate_seconds')}",
        "",
        "Development evidence is software evidence only; it is not research "
        "acceptance, a formal run or a scientific conclusion.",
    ]
    if result.pause:
        lines.insert(6, f"- paused: {result.pause.get('reason')} "
                       f"({result.pause.get('detail')})")
    return "\n".join(lines) + "\n"


def run_fit(
    request: Mapping[str, Any],
    *,
    data: Optional[temporal_data.TemporalData] = None,
    clock: Optional[Callable[[], float]] = None,
    sampler: Optional[Callable[[], Mapping[str, Any]]] = None,
    after_update: Optional[Callable[[Any, int, int], None]] = None,
    publish: Optional[Callable[[Path, Mapping[str, Any]], str]] = None,
    repo: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run one fit or resume stage and persist a complete format-v2 run."""
    purpose = protocol.validate_purpose(str(request["purpose"]))
    operation = str(request.get("operation", "fit"))
    if operation not in {"fit", "resume"}:
        raise RunnerError(f"operation {operation!r} is not a fitting stage")
    config = protocol.FitConfig.from_payload(request["config"])
    if purpose == "formal":
        protocol.require_formal_controls(config)
    roles = protocol.Roles(**request.get("roles", {})).validate()
    if roles.candidate_role == "screening":
        if config.seed != 0:
            raise RunnerError(
                "learning-rate screening candidates must use seed 0; "
                f"requested seed {config.seed}"
            )
        if roles.repeat_role != "a":
            raise RunnerError("a screening candidate is repetition a, never b")
    if roles.repeat_role == "b" and roles.candidate_role == "screening":
        raise RunnerError("repetition b never chooses a configuration")
    clock = clock or _clock()
    started = clock()
    parent: Optional[Dict[str, Any]] = None
    restore: Optional[temporal_engine.RestoreState] = None
    condition_extra: Dict[str, Any] = {}
    if operation == "resume":
        parent_dir = Path(request["parent_dir"])
        parent = recovery.load_parent(
            parent_dir, ledger_path=Path(request["ledger_path"]) if request.get("ledger_path") else None
        )
        parent_config = parent["parent_config"]
        if parent_config.to_payload() != config.to_payload():
            raise RunnerError(
                "resume configuration must equal the parent trajectory configuration"
            )
        restore = recovery.build_restore_state(parent["payload"])
        condition_extra = {
            "parent": {
                "run_id": parent["parent_config_doc"].get("run_id"),
                "run_dir": str(parent_dir.resolve()),
                "recovery_sha256": parent["recovery_sha256"],
                "completed_epoch": parent["completed_epoch"],
            }
        }
        config = parent_config
    if data is None:
        data_path = request.get("data_path")
        data = temporal_data.load_temporal_data(
            str(request["data_name"]),
            demand_path=Path(data_path) if data_path else None,
        )
    identity = data.identity()
    condition = _condition(config, data)
    if operation == "resume" and parent is not None:
        parent_condition = (parent["parent_config_doc"].get("condition") or {}).get(
            "condition_id"
        )
        if parent_condition != condition["condition_id"]:
            raise RunnerError(
                "resume data/protocol identity no longer matches the parent condition; "
                "a changed dataset is a new condition, not a recovery"
            )
    run = artifacts.reserve_run(
        str(request["run_id"]),
        purpose=purpose,
        operation=operation,
        output_root=Path(request["output_root"]) if request.get("output_root") else None,
        repo=repo,
    )
    ledger: Optional[resources.Ledger] = None
    watchdog: Optional[resources.Watchdog] = None
    cost_payload: Dict[str, Any] = {
        "status": "not_measured",
        "reason": "cost sample does not apply to this short development trajectory",
    }
    recovery_sha: Optional[str] = None
    execution_elapsed = 0.0
    try:
        _write_preamble(
            run,
            request=request,
            purpose=purpose,
            operation=operation,
            dataset_document=_dataset_document(data),
            config_payload=config.to_payload(),
            protocol_controls={
                "complete": config.complete_protocol,
                "deviations": config.deviations(),
            },
            roles=roles.to_payload(),
            condition=condition,
            data_identity=identity,
            config_extra=condition_extra or None,
        )
        run.save_npy(protocol.RUN_DIRECTORY_FILES["keys"], data.node_keys)
        run.write_json(
            protocol.RUN_DIRECTORY_FILES["months"],
            {
                "months": list(p01.MONTHS),
                "train_observation_months": list(protocol.train_observation_months()),
                "fit_observations_stop_at": p01.MONTHS[
                    protocol.fit_observation_month_count() - 1
                ],
            },
        )
        run.write_json(protocol.RUN_DIRECTORY_FILES["splits"], protocol.split_payload())
        preprocessing = data.training_rms()
        run.write_json(protocol.RUN_DIRECTORY_FILES["preprocessing"], preprocessing)
        masks = data.training_masks()
        run.save_npz(protocol.RUN_DIRECTORY_FILES["masks"], **masks)
        fit_arrays = data.fit_arrays()
        baselines = temporal_data.naive_validation_baselines(fit_arrays)
        baselines["identity"] = {
            "dataset": identity["dataset"],
            "source_sha256": identity["source_sha256"],
            "node_keys_sha256": identity["node_keys_sha256"],
            "split": protocol.split_payload(),
        }
        run.write_json(protocol.RUN_DIRECTORY_FILES["baselines"], baselines)
        if request.get("ledger_path"):
            ledger = resources.Ledger(
                Path(request["ledger_path"]),
                batch_id=str(request.get("batch_id", "p02-t006")),
            )
        setup_seconds = float(request.get("setup_seconds", 0.0))
        interval = float(
            request.get("monitor_interval", protocol.MONITOR_INTERVAL_SECONDS)
        )
        watchdog = resources.Watchdog(
            sampler=sampler
            or (lambda: resources.sample_process_tree_rss(os.getpid())),
            clock=clock,
            interval=interval,
            limit_bytes=int(
                request.get("memory_limit_bytes", protocol.MEMORY_STOP_BYTES)
            ),
            started_at=started,
        )
        watchdog.sample_once()
        watchdog.start()
        publish_fn = publish or checkpoints.publish_last

        def on_epoch_complete(trajectory: temporal_engine.Trajectory) -> None:
            nonlocal recovery_sha
            if trajectory.best is None:
                return
            payload = checkpoints.last_payload(
                config,
                trajectory,
                condition=condition,
                data_identity=identity,
                best=trajectory.best.manifest(),
                best_model_state=trajectory.best.model_state,
                best_optimizer_state=trajectory.best.optimizer_state,
                scale=trajectory.best.scale,
                ledger=ledger.payload_view() if ledger is not None else None,
            )
            recovery_sha = publish_fn(
                run.path / protocol.RUN_DIRECTORY_FILES["last_recovery"], payload
            )
            run.append_event(
                "recovery_published",
                epoch=trajectory.completed_epoch,
                sha256=recovery_sha,
            )

        def after_epoch(trajectory: temporal_engine.Trajectory) -> None:
            nonlocal cost_payload
            reason = watchdog.pause_reason() if watchdog is not None else None
            if reason is not None:
                raise PauseRequest("resource_stop", reason)
            elapsed = max(0.0, float(clock() - started))
            if elapsed > protocol.FIT_SECONDS:
                raise PauseRequest(
                    "fit_timeout",
                    {
                        "elapsed_seconds": elapsed,
                        "limit_seconds": protocol.FIT_SECONDS,
                    },
                )
            if (
                ledger is not None
                and ledger.active_seconds() + elapsed > protocol.BATCH_SECONDS
            ):
                raise PauseRequest(
                    "batch_timeout",
                    {
                        "active_seconds": ledger.active_seconds(),
                        "elapsed_seconds": elapsed,
                        "limit_seconds": protocol.BATCH_SECONDS,
                    },
                )
            if (
                trajectory.completed_epoch == protocol.COST_SAMPLE_EPOCHS
                and config.epochs > protocol.COST_SAMPLE_EPOCHS
            ):
                cost_payload = resources.cost_gate(
                    trajectory.history,
                    epochs=config.epochs,
                    setup_seconds=setup_seconds,
                    spent_seconds=elapsed,
                    remaining_fits=int(request.get("remaining_fits", 1)),
                    batch_active_seconds=(
                        ledger.active_seconds() if ledger is not None else 0.0
                    ),
                )
                run.write_json(protocol.RUN_DIRECTORY_FILES["cost"], cost_payload)
                if cost_payload["status"] != "ok":
                    raise PauseRequest(
                        "cost_stop",
                        {
                            "reason": cost_payload.get("reasons"),
                            "estimate_seconds": cost_payload.get("estimate_seconds"),
                        },
                    )

        hooks = temporal_engine.Hooks(
            on_epoch_complete=on_epoch_complete,
            after_epoch=after_epoch,
            after_update=after_update,
            clock=clock,
        )
        result = temporal_engine.run_trajectory(
            fit_arrays, config, hooks=hooks, restore=restore
        )
        execution_elapsed = max(0.0, float(clock() - started))
        if watchdog is not None:
            run.write_json("monitor.json", watchdog.payload())
        if ledger is not None:
            ledger.record(
                execution_id=f"{run.run_id}@{time.strftime('%Y%m%dT%H%M%S')}",
                run_id=run.run_id,
                seconds=execution_elapsed,
                kind="measured",
                status=result.status,
                note=(
                    "resumed execution; any discarded partial-epoch work from the "
                    "parent execution is billed separately there"
                    if operation == "resume"
                    else None
                ),
            )
        reproduction = (result.scores.get("best") or {}).get("reproduction") or {}
        usable = reproduction.get("status") == "pass"
        if not usable:
            result.warnings.append(
                "restored best checkpoint did not reproduce its saved validation "
                "metrics within 1e-6"
            )
        run.write_json(
            protocol.RUN_DIRECTORY_FILES["history"],
            {
                "epochs": result.history,
                "initial_validation": result.initial_validation,
                "note": (
                    "validation history covers every completed epoch; online train "
                    "loss is a mixed-parameter cumulative value"
                ),
            },
        )
        run.write_json(protocol.RUN_DIRECTORY_FILES["scores"], result.scores)
        run.write_json(
            protocol.RUN_DIRECTORY_FILES["gradients"],
            {
                "grad_clip_norm": float(config.grad_clip),
                "clip_definition": (
                    "complete-gradient L2 norm clip after all node chunks of one "
                    "training window, before the single Adam step"
                ),
                "updates_per_epoch": protocol.UPDATES_PER_EPOCH,
                "total_updates": int(result.updates),
                "clipped_updates": int(
                    sum(1 for record in result.update_records if record.get("clipped"))
                ),
                "updates": result.update_records,
            },
        )
        run.save_npy(
            protocol.RUN_DIRECTORY_FILES["validation_prediction"],
            result.validation_prediction,
        )
        run.save_npy(
            protocol.RUN_DIRECTORY_FILES["validation_gold"],
            result.validation_targets,
        )
        run.write_json(
            protocol.RUN_DIRECTORY_FILES["validation_metrics"],
            {
                "best": {
                    "MSE": float(result.best["validation"]["MSE"]),
                    "MAE": float(result.best["validation"]["MAE"]),
                    "epoch": int(result.best["epoch"]),
                    "updates": int(result.best["updates"]),
                },
                "reevaluated": result.validation_metrics,
                "reproduction": reproduction,
                "initial": result.initial_validation,
                "history_epochs": len(result.history),
            },
        )
        run.write_json(
            protocol.RUN_DIRECTORY_FILES["fit_diagnostics"], result.fit_diagnostics
        )
        best_payload = checkpoints.best_payload(
            config,
            best=result.best,
            model_state=result.best_model_state,
            optimizer_state=result.best_optimizer_state,
            scale=result.scale,
            condition=condition,
            parameter_report={
                "observed": int(result.parameter_count),
                "protocol_expected": protocol.PARAMETER_COUNTS[config.model],
                "matches_protocol_architecture": (
                    int(result.parameter_count)
                    == protocol.PARAMETER_COUNTS[config.model]
                ),
            },
        )
        checkpoints.save_best(run.path / protocol.RUN_DIRECTORY_FILES["best_weights"], best_payload)
        cost_file = run.path / protocol.RUN_DIRECTORY_FILES["cost"]
        if not cost_file.exists():
            if result.completed_epoch == config.epochs:
                run.write_json(
                    protocol.RUN_DIRECTORY_FILES["cost"],
                    {
                        "status": "not_measured",
                        "reason": (
                            "short development trajectory below the 10-epoch cost "
                            "sample; steady-state cost remains unknown"
                        ),
                        "sample_epochs": protocol.COST_SAMPLE_EPOCHS,
                        "measurements": {},
                        "unknown": ["steady-state epoch 6..10 timing not measured"],
                    },
                )
            else:
                run.write_json(
                    protocol.RUN_DIRECTORY_FILES["cost"],
                    {
                        "status": "paused_before_cost_gate",
                        "reason": result.pause,
                        "measurements": {},
                        "unknown": ["cost sample is incomplete"],
                    },
                )
        fit_report = _fit_report(
            result=result, config=config, recovery_sha256=recovery_sha, cost=cost_payload
        )
        fit_report["purpose"] = purpose
        if not usable:
            fit_report["status"] = "failed"
            run.write_json("report.json", fit_report)
            artifacts.write_summary(
                run,
                _fit_summary_text(
                    run_id=run.run_id,
                    operation=operation,
                    purpose=purpose,
                    config=config,
                    result=result,
                    data_identity=identity,
                    cost=cost_payload,
                ),
            )
            run.set_status(
                "failed",
                detail="best checkpoint reproduction failed",
                reproduction=reproduction,
            )
            raise RunnerError(
                "the restored best checkpoint did not reproduce its saved "
                f"validation metrics: {reproduction}"
            )
        run.write_json("report.json", fit_report)
        artifacts.write_summary(
            run,
            _fit_summary_text(
                run_id=run.run_id,
                operation=operation,
                purpose=purpose,
                config=config,
                result=result,
                data_identity=identity,
                cost=cost_payload,
            ),
        )
        artifacts.write_array_manifest(run, protocol.RECOMPUTE_ARRAYS)
        detail = None
        if result.pause:
            detail = result.pause
        run.set_status(
            result.status,
            detail=detail,
            completed_epoch=result.completed_epoch,
            selected_epoch=result.best["epoch"],
            recovery_sha256=recovery_sha,
            protocol_controls_complete=config.complete_protocol,
        )
        return {
            "run_id": run.run_id,
            "run_dir": str(run.path),
            "status": result.status,
            "paused": result.pause,
            "selected_epoch": result.best["epoch"],
            "validation": result.best["validation"],
            "completed_epoch": result.completed_epoch,
            "recovery_sha256": recovery_sha,
            "cost": cost_payload,
            "report_path": str(run.path / "report.json"),
        }
    except BaseException as exc:
        execution_elapsed = max(0.0, float(clock() - started))
        if watchdog is not None:
            watchdog.stop()
            try:
                run.write_json("monitor.json", watchdog.payload())
            except Exception:  # pragma: no cover - best effort on failure
                pass
        if ledger is not None and execution_elapsed > 0:
            ledger.record(
                execution_id=f"{run.run_id}@{time.strftime('%Y%m%dT%H%M%S')}",
                run_id=run.run_id,
                seconds=execution_elapsed,
                kind="measured",
                status="failed",
                note=f"failed execution: {type(exc).__name__}",
            )
        try:
            run.write_json(
                "report.json",
                {
                    "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
                    "scientific_version": protocol.SCIENTIFIC_VERSION,
                    "kind": "fit-summary",
                    "status": "failed",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                    "elapsed_seconds": execution_elapsed,
                },
            )
            run.set_status(
                "failed",
                detail={"type": type(exc).__name__, "message": str(exc)},
            )
        except Exception:  # pragma: no cover - best effort on failure
            pass
        raise
    finally:
        if watchdog is not None:
            watchdog.stop()


def run_preflight(request: Mapping[str, Any]) -> Dict[str, Any]:
    return resources.preflight(
        purpose=str(request["purpose"]),
        operation=str(request.get("operation", "preflight")),
        data_name=request.get("data_name"),
        model=str(request.get("model", "GRU")),
        seed=int(request.get("seed", 0)),
        data_path=Path(request["data_path"]) if request.get("data_path") else None,
        run_id=request.get("run_id"),
        output_root=Path(request["output_root"]) if request.get("output_root") else None,
        ledger_path=Path(request["ledger_path"]) if request.get("ledger_path") else None,
        lock_path=Path(request["lock_path"]) if request.get("lock_path") else None,
        recovery_path=Path(request["recovery_path"]) if request.get("recovery_path") else None,
        dependencies_missing=request.get("dependencies_missing"),
        memory_available_bytes=request.get("memory_available_bytes"),
        disk_free_bytes=request.get("disk_free_bytes"),
        psutil_available=request.get("psutil_available"),
        data_identity=request.get("data_identity"),
    )


def run_select(request: Mapping[str, Any], *, repo: Optional[Path] = None) -> Dict[str, Any]:
    purpose = protocol.validate_purpose(str(request["purpose"]))
    candidates = [
        temporal_selection.load_candidate(Path(path))
        for path in request["candidates"]
    ]
    first = candidates[0]
    block = artifacts.reserve_block(
        str(request["block_id"]),
        purpose=purpose,
        operation="select",
        output_root=Path(request["output_root"]) if request.get("output_root") else None,
        repo=repo,
    )
    try:
        payload = temporal_selection.build_selection(
            candidates,
            block_id=block.run_id,
            purpose=purpose,
            model=first.model,
            dataset=first.dataset,
            mode=first.mode,
        )
        block.write_json(protocol.RUN_DIRECTORY_FILES["selection"], payload)
        artifacts.write_command(block, request.get("argv") or [], operation="select")
        environment = artifacts.write_environment(block)
        provenance = artifacts.provenance_payload(
            purpose=purpose,
            operation="select",
            config={"candidates": [candidate.config for candidate in candidates]},
            roles={"kind": "selection", "seed": 0},
            data_identity={
                "dataset": first.dataset,
                "mode": first.mode,
                "source_sha256": first.data_sha256,
                "node_keys_sha256": first.keys_sha256,
            },
            source_record=artifacts.capture_source(block),
            environment=environment,
        )
        block.write_json("provenance.json", provenance)
        report = {
            "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
            "scientific_version": protocol.SCIENTIFIC_VERSION,
            "kind": "selection-report",
            "block_id": block.run_id,
            "purpose": purpose,
            "status": payload["status"],
            "winner": payload["winner"],
            "tie": payload["tie"],
            "candidates": payload["candidates"],
            "eliminated": payload["eliminated"],
            "winner_as_a": payload["winner_as_a"],
            "selection_sha256": payload["selection_sha256"],
            "test_scores_used": False,
            "b_used_for_selection": False,
        }
        block.write_json("report.json", report)
        lines = [
            f"# selection {block.run_id}",
            "",
            f"- purpose: {purpose}",
            f"- dataset/encoder: {first.dataset}/{first.model}",
            f"- candidate learning rates: {list(protocol.LR_CANDIDATES)}",
            f"- selection metric: best validation original-unit MSE",
            f"- status: {payload['status']}",
        ]
        if payload["winner"]:
            lines += [
                f"- winner: learning rate {payload['winner']['learning_rate']:g} "
                f"({payload['winner']['run_id']})",
                f"- winner validation MSE: {payload['winner']['validation_MSE']:.6g}",
                f"- exact tie: {payload['tie']}",
                "- winner reused as repetition a by link (not refitted)",
            ]
        else:
            lines.append("- no completed candidate: selection is incomplete")
        lines += [
            "- test scores used: no",
            "- repetition b used for selection: no",
            "- automatic matrix scheduling: none",
        ]
        artifacts.write_summary(block, "\n".join(lines) + "\n")
        block.set_status(
            "selection_frozen" if payload["status"] == "frozen" else "selection_incomplete",
            selection_sha256=payload["selection_sha256"],
        )
        return {
            "block_id": block.run_id,
            "block_dir": str(block.path),
            "status": payload["status"],
            "selection": payload,
            "report_path": str(block.path / "report.json"),
        }
    except BaseException as exc:
        try:
            block.set_status(
                "failed", detail={"type": type(exc).__name__, "message": str(exc)}
            )
        except Exception:  # pragma: no cover - best effort
            pass
        raise


def run_diagnose(request: Mapping[str, Any]) -> Dict[str, Any]:
    """Run the section-5 gates and reserve a fresh diagnostics execution identity."""
    block_dir = Path(request["block_dir"])
    selection_payload = temporal_selection.load_selection(block_dir)
    a_runs: Dict[int, Dict[str, Any]] = {}
    b_runs: Dict[int, Dict[str, Any]] = {}
    for seed, path in (request.get("a_runs") or {}).items():
        a_runs[int(seed)] = temporal_diagnostics.load_run_evidence(Path(path))
    for seed, path in (request.get("b_runs") or {}).items():
        b_runs[int(seed)] = temporal_diagnostics.load_run_evidence(Path(path))
    ridge = None
    if request.get("ridge_path"):
        ridge = artifacts.read_json(Path(request["ridge_path"]))
    payload = temporal_diagnostics.build_diagnostics(
        selection=selection_payload,
        block_id=block_dir.name,
        a_runs=a_runs,
        b_runs=b_runs,
        ridge=ridge,
    )
    diagnostics_id = str(
        request.get("diagnostics_id")
        or "diagnostics-" + time.strftime("%Y%m%dT%H%M%S")
    )
    diagnostics_root = block_dir / "diagnostics"
    diagnostics_run = artifacts.RunDirectory(
        diagnostics_root, diagnostics_id, run_type="effective-temporal-diagnostics"
    )
    diagnostics_run.reserve()
    diagnostics_run.write_json(protocol.RUN_DIRECTORY_FILES["diagnostics"], payload)
    diagnostics_run.write_json("cost.json", _aggregate_cost(request, a_runs, b_runs))
    artifacts.write_command(
        diagnostics_run, request.get("argv") or [], operation="diagnose"
    )
    reference = a_runs.get(0) or next(iter(a_runs.values()), None)
    artifacts.write_environment(diagnostics_run)
    provenance = artifacts.provenance_payload(
        purpose=str(request.get("purpose", "development")),
        operation="diagnose",
        config={"learning_rate_candidates": list(protocol.LR_CANDIDATES)},
        roles={"kind": "diagnostics", "block_id": block_dir.name},
        data_identity=(
            {
                "dataset": reference.get("dataset"),
                "mode": reference.get("mode"),
                "source_sha256": reference.get("data_sha256"),
                "node_keys_sha256": reference.get("keys_sha256"),
            }
            if reference
            else None
        ),
        source_record=artifacts.capture_source(diagnostics_run),
        environment=artifacts.read_json(diagnostics_run.path / "environment.json"),
    )
    diagnostics_run.write_json("provenance.json", provenance)
    status = "pass" if payload["status"] == "pass" else (
        "failed" if payload["status"] == "fail" else "incomplete"
    )
    result = {
        "block_id": payload["block_id"],
        "diagnostics_id": diagnostics_id,
        "status": payload["status"],
        "learning_ready": payload["learning_ready"],
        "gates": {
            name: {
                "status": gate["status"],
                "passing_seeds": gate.get("passing_seeds"),
                "failing_seeds": gate.get("failing_seeds"),
                "incomplete_seeds": gate.get("incomplete_seeds"),
                "reasons": gate.get("reasons"),
            }
            for name, gate in payload["gates"].items()
        },
        "summary": payload["summary"],
        "incomplete_reasons": payload["incomplete_reasons"],
        "diagnostics_sha256": payload["diagnostics_sha256"],
    }
    diagnostics_run.write_json("report.json", result)
    artifacts.write_summary(
        diagnostics_run,
        "\n".join(
            [
                f"# diagnostics {diagnostics_id}",
                "",
                f"- block: {block_dir.name}",
                f"- status: {payload['status']}",
                f"- learning_ready: {payload['learning_ready']}",
                f"- selection sha256: {selection_payload.get('selection_sha256')}",
                f"- diagnostics sha256: {payload['diagnostics_sha256']}",
                "",
                "`learning_ready` is a computed software state; it is not research "
                "acceptance, graph benefit or a convergence claim.",
            ]
        )
        + "\n",
    )
    artifacts.write_json_atomic(
        block_dir / "latest-diagnostics.json",
        {
            "diagnostics_id": diagnostics_id,
            "run_dir": str(diagnostics_run.path.resolve()),
            "diagnostics_sha256": payload["diagnostics_sha256"],
            "selection_sha256": selection_payload.get("selection_sha256"),
            "status": payload["status"],
            "learning_ready": payload["learning_ready"],
        },
    )
    diagnostics_run.set_status(
        status,
        diagnostics_status=payload["status"],
        learning_ready=payload["learning_ready"],
        block_id=block_dir.name,
    )
    tolerances = {
        "learning_train_reduction": protocol.LEARNING_TRAIN_REDUCTION,
        "learning_validation_reduction": protocol.LEARNING_VAL_REDUCTION,
        "zero_mae_improvement": protocol.ZERO_MAE_IMPROVEMENT,
        "budget_tail_relative": protocol.BUDGET_TAIL_RELATIVE,
        "repetition_normalized_mae": protocol.REPETITION_TOLERANCE,
    }
    inputs = {
        "block_dir": str(block_dir.resolve()),
        "diagnostics_dir": str(diagnostics_run.path.resolve()),
        "selection_sha256": selection_payload.get("selection_sha256"),
        "a_runs": {str(seed): evidence["run_dir"] for seed, evidence in a_runs.items()},
        "b_runs": {str(seed): evidence["run_dir"] for seed, evidence in b_runs.items()},
    }
    envelope = checks.envelope(
        "diagnose",
        argv=request.get("argv") or [],
        inputs=inputs,
        tolerances=tolerances,
        status=status,
        result=result,
        errors=payload["incomplete_reasons"][:10] if status != "pass" else [],
    )
    written = checks.finish(Path(request["report_path"]), envelope)
    return {
        **written,
        "learning_ready": payload["learning_ready"],
        "diagnostics_dir": str(diagnostics_run.path),
        "diagnostics_path": str(
            diagnostics_run.path / protocol.RUN_DIRECTORY_FILES["diagnostics"]
        ),
        "diagnostics_id": diagnostics_id,
    }


def load_block_diagnostics(block_dir: Path) -> Optional[Dict[str, Any]]:
    """Read the latest diagnostics evidence for a block (explicit pointer first)."""
    block_dir = Path(block_dir)
    pointer = block_dir / "latest-diagnostics.json"
    if pointer.exists():
        record = artifacts.read_json(pointer)
        target = Path(record["run_dir"]) / protocol.RUN_DIRECTORY_FILES["diagnostics"]
        if target.exists():
            return artifacts.read_json(target)
    legacy = block_dir / protocol.RUN_DIRECTORY_FILES["diagnostics"]
    if legacy.exists():
        return artifacts.read_json(legacy)
    return None


def _aggregate_cost(
    request: Mapping[str, Any],
    a_runs: Mapping[int, Mapping[str, Any]],
    b_runs: Mapping[int, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Aggregate per-run measurements into the block ``cost.json`` record."""
    estimates: List[float] = []
    measured: List[float] = []
    fits = 0
    for evidence in list(a_runs.values()) + list(b_runs.values()):
        fits += 1
        path = Path(evidence["run_dir"]) / protocol.RUN_DIRECTORY_FILES["cost"]
        if not path.exists():
            continue
        payload = artifacts.read_json(path)
        estimate = payload.get("estimate_seconds")
        steady = payload.get("steady_state_median_seconds")
        if isinstance(estimate, (int, float)):
            estimates.append(float(estimate))
        if isinstance(steady, (int, float)):
            measured.append(float(steady))
    dataset = (request.get("dataset") or request.get("data_name") or
               next(iter(a_runs.values()), {}).get("dataset"))
    model = request.get("model")
    ledger_active = None
    if request.get("ledger_path") and Path(request["ledger_path"]).exists():
        ledger_payload = artifacts.read_json(Path(request["ledger_path"]))
        ledger_active = float(
            sum(
                float(entry.get("seconds", 0.0))
                for entry in ledger_payload.get("entries", [])
                if entry.get("kind") in {"measured", "replayed"}
            )
        )
    known_blocks = {f"{dataset}/{model}"} if dataset and model else set()
    unknown = sorted(
        f"{name}/{kind}"
        for name in protocol.DATASETS
        for kind in protocol.MODELS
        if f"{name}/{kind}" not in known_blocks
    )
    return {
        "status": "measured" if estimates else "unknown",
        "dataset": dataset,
        "model": model,
        "fits_completed_this_block": fits,
        "block_fit_limit": protocol.MAX_FITS_PER_BLOCK,
        "remaining_fits": max(0, protocol.MAX_FITS_PER_BLOCK - fits),
        "requested_remaining_fits": request.get("remaining_fits"),
        "measured_steady_state_epoch_seconds": measured,
        "estimated_fit_seconds": max(estimates) if estimates else None,
        "estimate_definition": (
            "1.3 * (setup + 2*100*t) with t the epoch 6..10 median; measured and "
            "estimated values are separate fields"
        ),
        "batch_active_seconds": ledger_active,
        "batch_limit_seconds": protocol.BATCH_SECONDS,
        "unknown_unmeasured_blocks": unknown,
        "note": (
            "each dataset x encoder block needs its own measurement; no automatic "
            "matrix expansion is permitted"
        ),
    }


def run_report(
    request: Mapping[str, Any],
    *,
    data: Optional[temporal_data.TemporalData] = None,
    repo: Optional[Path] = None,
) -> Dict[str, Any]:
    """Explicit four-window test report after selection and diagnostics."""
    purpose = protocol.validate_purpose(str(request["purpose"]))
    block_dir = Path(request["block_dir"])
    winner_dir = Path(request["run_dir"])
    selection_payload = temporal_selection.load_selection(block_dir)
    diagnostics_dir = (
        Path(request["diagnostics_dir"]) if request.get("diagnostics_dir") else block_dir
    )
    diagnostics_payload = load_block_diagnostics(diagnostics_dir)
    winner_config_doc = checks.run_config(winner_dir)
    winner_config = protocol.FitConfig.from_payload(winner_config_doc["config"])
    if purpose == "formal":
        protocol.require_formal_controls(winner_config)
    data_name = winner_config_doc["dataset"]["name"]
    if data is None:
        data_path = request.get("data_path")
        data = temporal_data.load_temporal_data(
            data_name, demand_path=Path(data_path) if data_path else None
        )
    winner_provenance = artifacts.read_json(winner_dir / "provenance.json")
    winner_data = winner_provenance.get("data") or {}
    identity = data.identity()
    if identity["source_sha256"] != winner_data.get("source_sha256") or identity[
        "node_keys_sha256"
    ] != winner_data.get("node_keys_sha256"):
        raise temporal_report.ReportError(
            "the test data source or canonical node keys differ from the selected "
            "trajectory; the report would describe a different condition"
        )
    arrays = data.report_arrays()
    masks = checks.load_npz(winner_dir / protocol.RUN_DIRECTORY_FILES["masks"])
    coverage = temporal_report.coverage_masks(
        data_name,
        arrays.node_keys,
        graph_path=Path(request["graph_path"]) if request.get("graph_path") else None,
        mask_bundle=Path(request["mask_bundle"]) if request.get("mask_bundle") else None,
    )
    best_payload = checkpoints.load_best(
        winner_dir / protocol.RUN_DIRECTORY_FILES["best_weights"],
        expected_config=winner_config,
    )
    a_states: Dict[int, str] = {}
    b_states: Dict[int, str] = {}
    if diagnostics_payload:
        for seed, entry in ((diagnostics_payload.get("inputs") or {}).get("a_runs") or {}).items():
            a_states[int(seed)] = str(entry.get("state"))
        for seed, entry in ((diagnostics_payload.get("inputs") or {}).get("b_runs") or {}).items():
            b_states[int(seed)] = str(entry.get("state"))
    blockers = temporal_report.formal_report_blockers(
        purpose=purpose,
        config=winner_config,
        selection=selection_payload,
        diagnostics=diagnostics_payload,
        run_dir=winner_dir,
        a_states=a_states,
        b_states=b_states,
        winner_run_dir=Path(selection_payload["winner"]["run_dir"])
        if selection_payload.get("winner")
        else None,
    )
    if purpose == "formal" and blockers:
        raise temporal_report.ReportError(
            "a formal test report is refused: " + "; ".join(blockers)
        )
    condition = winner_config_doc.get("condition") or {}
    run = artifacts.reserve_run(
        str(request["run_id"]),
        purpose=purpose,
        operation="report",
        output_root=Path(request["output_root"]) if request.get("output_root") else None,
        repo=repo,
    )
    try:
        _write_preamble(
            run,
            request=request,
            purpose=purpose,
            operation="report",
            dataset_document=_dataset_document(data),
            config_payload=winner_config.to_payload(),
            protocol_controls={
                "complete": winner_config.complete_protocol,
                "deviations": winner_config.deviations(),
            },
            roles=winner_config_doc.get("roles") or {},
            condition=condition,
            data_identity=identity,
            config_extra={
                "selection": {
                    "block_id": block_dir.name,
                    "selection_sha256": selection_payload.get("selection_sha256"),
                    "winner_run_id": (selection_payload.get("winner") or {}).get("run_id"),
                },
                "diagnostics": (
                    {
                        "block_id": diagnostics_payload.get("block_id"),
                        "diagnostics_sha256": diagnostics_payload.get(
                            "diagnostics_sha256"
                        ),
                        "status": diagnostics_payload.get("status"),
                        "learning_ready": diagnostics_payload.get("learning_ready"),
                    }
                    if diagnostics_payload
                    else None
                ),
                "parent": {
                    "run_id": winner_config_doc.get("run_id"),
                    "run_dir": str(winner_dir.resolve()),
                },
                "formal_blockers": blockers,
            },
        )
        prediction = temporal_report.predict_test(
            best_payload, winner_config, arrays.test_inputs, float(best_payload["scale"])
        )
        coverage_mask = coverage.mask if coverage is not None else None
        coverage_provenance = coverage.provenance if coverage is not None else None
        activity_masks = {
            name: np.asarray(value, dtype=bool)
            for name, value in masks.items()
            if name.startswith("activity_")
        }
        constant_masks = {
            name: np.asarray(masks[name], dtype=bool)
            for name in ("constant_train27", "nonconstant_train27")
            if name in masks
        }
        report_payload = temporal_report.build_report(
            prediction=prediction,
            gold=arrays.test_targets,
            starts=arrays.starts,
            key_array=arrays.node_keys,
            activity_masks=activity_masks,
            constant_masks=constant_masks,
            coverage=coverage_mask,
            coverage_provenance=coverage_provenance,
            scale=float(best_payload["scale"]),
            protocol_complete=winner_config.complete_protocol,
            purpose=purpose,
        )
        report_payload["selection"] = {
            "selection_sha256": selection_payload.get("selection_sha256"),
            "winner_run_id": (selection_payload.get("winner") or {}).get("run_id"),
            "selected_learning_rate": (selection_payload.get("winner") or {}).get(
                "learning_rate"
            ),
        }
        report_payload["diagnostics"] = (
            {
                "diagnostics_sha256": diagnostics_payload.get("diagnostics_sha256"),
                "status": diagnostics_payload.get("status"),
                "learning_ready": diagnostics_payload.get("learning_ready"),
            }
            if diagnostics_payload
            else None
        )
        report_payload["formal_blockers"] = blockers
        run.save_npy(
            protocol.RUN_DIRECTORY_FILES["test_prediction"], prediction
        )
        run.save_npy(
            protocol.RUN_DIRECTORY_FILES["test_gold"],
            np.asarray(arrays.test_targets),
        )
        run.write_json(
            protocol.RUN_DIRECTORY_FILES["test_windows"],
            report_payload["test_windows"],
        )
        run.write_json("report.json", report_payload)
        run.save_npy(protocol.RUN_DIRECTORY_FILES["keys"], arrays.node_keys)
        run.write_json(protocol.RUN_DIRECTORY_FILES["months"], {
            "months": list(p01.MONTHS),
            "train_observation_months": list(protocol.train_observation_months()),
        })
        run.write_json(protocol.RUN_DIRECTORY_FILES["splits"], protocol.split_payload())
        run.copy_file(
            winner_dir / protocol.RUN_DIRECTORY_FILES["preprocessing"],
            protocol.RUN_DIRECTORY_FILES["preprocessing"],
        )
        combined_masks: Dict[str, np.ndarray] = {
            name: np.asarray(value) for name, value in masks.items()
        }
        if coverage_mask is not None:
            combined_masks["has_nonself_neighbor"] = np.asarray(coverage_mask, dtype=bool)
            combined_masks["no_nonself_neighbor"] = np.asarray(~coverage_mask, dtype=bool)
        run.save_npz(protocol.RUN_DIRECTORY_FILES["masks"], **combined_masks)
        run.write_json(
            "coverage.json",
            report_payload["coverage"],
        )
        for relative in (
            "validation/prediction.npy",
            "validation/gold.npy",
            "validation/metrics.json",
            "history.json",
            "scores.json",
            "baselines.json",
            "fit-diagnostics.json",
            "weights/best.pt",
        ):
            source = winner_dir / relative
            if source.is_file():
                run.copy_file(source, relative)
        for relative in ("selection.json", "diagnostics.json"):
            source = (
                diagnostics_dir / relative
                if relative == "diagnostics.json" and diagnostics_payload
                else block_dir / relative
            )
            if source.is_file():
                run.copy_file(source, relative)
        artifacts.write_array_manifest(run, protocol.RECOMPUTE_ARRAYS)
        lines = [
            f"# test report {run.run_id}",
            "",
            f"- purpose: {purpose}",
            f"- dataset/encoder: {data_name}/{winner_config.model}",
            f"- selected run: {winner_config_doc.get('run_id')}",
            f"- test starts: {list(arrays.starts)}",
            f"- array shape: {list(prediction.shape)}",
            f"- target-month multiplicities: "
            f"{report_payload['test_windows']['target_month_multiplicities']}",
            f"- overall test MAE: {report_payload['metrics']['MAE']:.6g}",
            f"- overall test MSE: {report_payload['metrics']['MSE']:.6g}",
            f"- overall test RMSE: {report_payload['metrics']['RMSE']:.6g}",
            f"- neighbor coverage available: {coverage_mask is not None}",
            f"- protocol controls complete: {winner_config.complete_protocol}",
            f"- formal blockers: {blockers}",
            "",
            "Test scores are descriptive only and never select a configuration, "
            "checkpoint, clip rule or readiness state.",
        ]
        artifacts.write_summary(run, "\n".join(lines) + "\n")
        run.set_status(
            "completed" if winner_config.complete_protocol else "development_incomplete",
            protocol_controls_complete=winner_config.complete_protocol,
            selected_epoch=best_payload["manifest"]["epoch"],
            selection_sha256=selection_payload.get("selection_sha256"),
            diagnostics_sha256=(
                diagnostics_payload.get("diagnostics_sha256")
                if diagnostics_payload
                else None
            ),
        )
        return {
            "run_id": run.run_id,
            "run_dir": str(run.path),
            "status": "completed"
            if winner_config.complete_protocol
            else "development_incomplete",
            "report_path": str(run.path / "report.json"),
            "test_shape": list(prediction.shape),
            "formal_blockers": blockers,
            "coverage_available": coverage_mask is not None,
        }
    except BaseException as exc:
        try:
            run.write_json(
                "report.json",
                {
                    "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
                    "scientific_version": protocol.SCIENTIFIC_VERSION,
                    "kind": "test-report",
                    "status": "failed",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                },
            )
            run.set_status(
                "failed", detail={"type": type(exc).__name__, "message": str(exc)}
            )
        except Exception:  # pragma: no cover - best effort
            pass
        raise
