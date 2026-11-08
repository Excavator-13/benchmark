"""Command line for the staged P02 recurrent entry.

The module path is unchanged, but the command surface is now explicit:
``preflight``, ``fit``, ``select``, ``diagnose``, ``report``, ``recompute``,
``compare`` and ``resume``.  The legacy implicit train-then-test invocation is
rejected with a migration message instead of silently changing the protocol.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from . import protocol

MODULE = "benchmark.multivariate_time_series.effective_temporal_training"
SUBCOMMANDS = protocol.OPERATIONS + ("_worker",)
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_PAUSED = 3
EXIT_INCOMPLETE = 4

MIGRATION_MESSAGE = (
    "this entry no longer supports the implicit train-then-test invocation.\n"
    "The protocol is now staged: use `fit` (training/validation only), then\n"
    "`select`, `diagnose` and finally `report` for the four test windows.\n"
    "Old `--run-dir/--model compare` calls and old checkpoints cannot be reused.\n"
    "Run `python -m %s --help` for the accepted commands." % MODULE
)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--purpose", choices=list(protocol.PURPOSES), default="development")
    parser.add_argument("--output-root", type=Path, default=None)


def _add_data(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    parser.add_argument(
        "--data-name", choices=list(protocol.DATASETS), required=required
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="demand Parquet table; defaults to the protocol dataset path",
    )


def _add_config(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", choices=list(protocol.MODELS), default="GRU")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--epochs", type=int, default=protocol.EPOCHS)
    parser.add_argument("--hidden-size", type=int, default=protocol.HIDDEN_SIZE)
    parser.add_argument("--layers", type=int, default=protocol.LAYERS)
    parser.add_argument("--node-chunk", type=int, default=2048)
    parser.add_argument("--grad-clip", type=float, default=protocol.GRAD_CLIP_NORM)
    parser.add_argument("--threads", type=int, default=1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=MODULE,
        description=(
            "P02 effective GRU/LSTM entry. Stages: preflight, fit (train/validation "
            "only), select (frozen learning rate), diagnose (section-5 gates), "
            "report (four rolling test windows), recompute/compare (saved evidence), "
            "resume (parent-linked recovery). Development is the default purpose."
        ),
        epilog=(
            "Execution evidence is software evidence only; formal research runs, "
            "acceptance, sealing and Git actions stay research-side decisions."
        ),
    )
    parser.add_argument("--version", action="version", version=protocol.SCIENTIFIC_VERSION)
    subparsers = parser.add_subparsers(dest="operation", metavar="operation")

    preflight = subparsers.add_parser(
        "preflight", help="machine-readable preflight (works without real data)"
    )
    _add_common(preflight)
    _add_data(preflight)
    preflight.add_argument("--model", choices=list(protocol.MODELS), default="GRU")
    preflight.add_argument("--seed", type=int, default=0)
    preflight.add_argument("--run-id", default=None)
    preflight.add_argument("--block-id", default=None)
    preflight.add_argument("--ledger", type=Path, default=None)
    preflight.add_argument("--batch-id", default="p02-t006")
    preflight.add_argument("--lock", type=Path, default=None)
    preflight.add_argument("--recovery", type=Path, default=None)
    preflight.add_argument("--dependencies-missing", nargs="*", default=None)
    preflight.add_argument("--memory-available-bytes", type=int, default=None)
    preflight.add_argument("--disk-free-bytes", type=int, default=None)
    preflight.add_argument(
        "--psutil-available",
        dest="psutil_available",
        action="store_true",
        default=None,
    )
    preflight.add_argument(
        "--psutil-unavailable", dest="psutil_available", action="store_false"
    )
    preflight.add_argument("--out", type=Path, default=None)
    preflight.set_defaults(handler="preflight")

    fit = subparsers.add_parser(
        "fit", help="fit one training/validation trajectory in a single worker"
    )
    _add_common(fit)
    _add_data(fit, required=True)
    _add_config(fit)
    fit.add_argument("--run-id", required=True)
    fit.add_argument(
        "--candidate-role",
        choices=list(protocol.CANDIDATE_ROLES),
        default="confirmation",
    )
    fit.add_argument("--repeat-role", choices=list(protocol.REPEAT_ROLES), default="a")
    fit.add_argument("--ledger", type=Path, default=None)
    fit.add_argument("--batch-id", default="p02-t006")
    fit.add_argument("--remaining-fits", type=int, default=1)
    fit.add_argument(
        "--monitor-interval",
        type=float,
        default=protocol.MONITOR_INTERVAL_SECONDS,
    )
    fit.add_argument(
        "--memory-limit-bytes", type=int, default=protocol.MEMORY_STOP_BYTES
    )
    fit.add_argument("--setup-seconds", type=float, default=0.0)
    fit.add_argument("--takeover-stale", action="store_true")
    fit.add_argument(
        "--memory-available-bytes",
        type=int,
        default=None,
        help="development-only injected preflight memory reading (software rehearsal)",
    )
    fit.add_argument(
        "--disk-free-bytes",
        type=int,
        default=None,
        help="development-only injected preflight disk reading (software rehearsal)",
    )
    fit.set_defaults(handler="fit")

    resume = subparsers.add_parser(
        "resume", help="resume a parent trajectory from its last complete epoch"
    )
    _add_common(resume)
    _add_data(resume, required=True)
    resume.add_argument("--parent", type=Path, required=True)
    resume.add_argument("--run-id", required=True)
    resume.add_argument("--ledger", type=Path, default=None)
    resume.add_argument("--batch-id", default="p02-t006")
    resume.add_argument("--remaining-fits", type=int, default=1)
    resume.add_argument(
        "--monitor-interval",
        type=float,
        default=protocol.MONITOR_INTERVAL_SECONDS,
    )
    resume.add_argument(
        "--memory-limit-bytes", type=int, default=protocol.MEMORY_STOP_BYTES
    )
    resume.add_argument("--takeover-stale", action="store_true")
    resume.add_argument("--memory-available-bytes", type=int, default=None)
    resume.add_argument("--disk-free-bytes", type=int, default=None)
    resume.set_defaults(handler="resume")

    select = subparsers.add_parser(
        "select", help="freeze the seed-0 learning-rate selection"
    )
    _add_common(select)
    select.add_argument(
        "--candidate",
        dest="candidates",
        type=Path,
        action="append",
        required=True,
        help="seed-0 screening run directory; supply exactly two",
    )
    select.add_argument("--block-id", required=True)
    select.set_defaults(handler="select")

    diagnose = subparsers.add_parser(
        "diagnose", help="run the saved-evidence section-5 learning gates"
    )
    _add_common(diagnose)
    diagnose.add_argument("--block", type=Path, required=True)
    diagnose.add_argument(
        "--a-run",
        dest="a_runs",
        action="append",
        default=[],
        metavar="SEED=PATH",
        help="repetition a run for one seed (repeat for seeds 0,1,2)",
    )
    diagnose.add_argument(
        "--b-run",
        dest="b_runs",
        action="append",
        default=[],
        metavar="SEED=PATH",
        help="repetition b run for one seed",
    )
    diagnose.add_argument(
        "--ridge",
        type=Path,
        default=None,
        help="JSON Ridge validation evidence with identity fields",
    )
    diagnose.add_argument("--ledger", type=Path, default=None)
    diagnose.add_argument("--remaining-fits", type=int, default=None)
    diagnose.add_argument("--dataset", default=None)
    diagnose.add_argument("--model", choices=list(protocol.MODELS), default=None)
    diagnose.add_argument("--report", type=Path, required=True, dest="report_path")
    diagnose.add_argument(
        "--diagnostics-id",
        default=None,
        help="optional label retained for command compatibility; report path is the output identity",
    )
    diagnose.set_defaults(handler="diagnose")

    report = subparsers.add_parser(
        "report", help="explicit four-window test report after selection"
    )
    _add_common(report)
    _add_data(report, required=True)
    report.add_argument("--block", type=Path, required=True)
    report.add_argument("--run", type=Path, required=True, dest="run_dir")
    report.add_argument("--run-id", required=True)
    report.add_argument("--graph", type=Path, default=None)
    report.add_argument("--mask-bundle", type=Path, default=None)
    report.add_argument(
        "--diagnostics",
        type=Path,
        default=None,
        help="frozen diagnose JSON report; required for formal reporting",
    )
    report.set_defaults(handler="report")

    recompute = subparsers.add_parser(
        "recompute", help="recompute saved metrics without source data or fitting"
    )
    recompute.add_argument("--run-dir", type=Path, required=True)
    recompute.add_argument("--report", type=Path, required=True, dest="report_path")
    recompute.set_defaults(handler="recompute")

    compare = subparsers.add_parser(
        "compare", help="same-condition repeat comparison from saved evidence"
    )
    compare.add_argument("--run-a", type=Path, required=True)
    compare.add_argument("--run-b", type=Path, required=True)
    compare.add_argument("--report", type=Path, required=True, dest="report_path")
    compare.set_defaults(handler="compare")

    worker = subparsers.add_parser("_worker")
    worker.add_argument("--request", type=Path, required=True)
    worker.set_defaults(handler="_worker")
    return parser


def _emit(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))


def _default_root(args: argparse.Namespace) -> Path:
    from . import artifacts

    return Path(args.output_root) if args.output_root else artifacts.default_root(
        args.purpose
    )


def _ledger_path(args: argparse.Namespace) -> Optional[Path]:
    if getattr(args, "ledger", None):
        return Path(args.ledger)
    root = _default_root(args)
    return root / "ledger.json"


def _lock_path(args: argparse.Namespace) -> Path:
    return _default_root(args) / "locks" / f"{args.batch_id}.lock"


def _data_path(args: argparse.Namespace) -> Optional[Path]:
    return Path(args.data) if getattr(args, "data", None) else None


def _config_payload(args: argparse.Namespace) -> Dict[str, Any]:
    return protocol.FitConfig(
        model=args.model,
        seed=args.seed,
        learning_rate=args.learning_rate,
        epochs=args.epochs,
        hidden_size=args.hidden_size,
        layers=args.layers,
        node_chunk=args.node_chunk,
        grad_clip=args.grad_clip,
        threads=args.threads,
    ).validate().to_payload()


def _preflight_request(args: argparse.Namespace, *, operation: str) -> Dict[str, Any]:
    controls = protocol.resource_controls(
        args.purpose, getattr(args, "memory_limit_bytes", protocol.MEMORY_STOP_BYTES)
    )
    memory = getattr(args, "memory_available_bytes", None)
    disk = getattr(args, "disk_free_bytes", None)
    if args.purpose == "formal" and (memory is not None or disk is not None):
        raise protocol.ProtocolError(
            "resource-value injection exists only for development software "
            "rehearsal; a formal preflight must measure the machine"
        )
    return {
        "resource_controls": controls,
        "purpose": args.purpose,
        "operation": operation,
        "data_name": getattr(args, "data_name", None),
        "model": getattr(args, "model", "GRU"),
        "seed": getattr(args, "seed", 0),
        "data_path": str(_data_path(args)) if _data_path(args) else None,
        "run_id": getattr(args, "run_id", None),
        "output_root": str(args.output_root) if args.output_root else None,
        "ledger_path": str(_ledger_path(args)) if _ledger_path(args) else None,
        "lock_path": str(_lock_path(args)) if getattr(args, "batch_id", None) else None,
        "recovery_path": str(getattr(args, "recovery", None) or "") or None,
        "dependencies_missing": getattr(args, "dependencies_missing", None),
        "memory_available_bytes": memory,
        "disk_free_bytes": disk,
        "psutil_available": getattr(args, "psutil_available", None),
    }


def _handle_preflight(args: argparse.Namespace) -> int:
    from . import runner

    request = _preflight_request(args, operation="preflight")
    if getattr(args, "lock", None):
        request["lock_path"] = str(args.lock)
    record = runner.run_preflight(request)
    _emit(record)
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return EXIT_OK if record["status"] == "pass" else EXIT_FAIL


def _worker_environment() -> Dict[str, str]:
    environment = dict(os.environ)
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        environment[name] = "1"
    return environment


def _run_stage(args: argparse.Namespace, operation: str) -> int:
    stage_started = time.monotonic()
    from . import artifacts, resources, runner, recovery
    root = _default_root(args)
    lock_path = _lock_path(args)
    preflight_request = _preflight_request(args, operation=operation)
    if operation == "resume":
        preflight_request["recovery_path"] = str(
            Path(args.parent) / protocol.RUN_DIRECTORY_FILES["last_recovery"]
        )
    preflight = runner.run_preflight(preflight_request)
    if preflight["status"] != "pass":
        _emit({"status": "fail", "stage": "preflight", "preflight": preflight})
        return EXIT_FAIL
    lock = resources.WorkerLock(
        lock_path,
        {
            "run_id": args.run_id,
            "batch_id": args.batch_id,
            "operation": operation,
            "purpose": args.purpose,
        },
    )
    state = lock.acquire(takeover_stale=bool(getattr(args, "takeover_stale", False)))
    if state["status"] != "acquired":
        _emit({"status": "conflict", "stage": "worker_lock", "lock": state})
        return EXIT_FAIL
    request: Dict[str, Any] = {
        "run_id": args.run_id,
        "purpose": args.purpose,
        "operation": operation,
        "data_name": args.data_name,
        "data_path": str(_data_path(args)) if _data_path(args) else None,
        "output_root": str(root),
        "config": _config_payload(args),
        "roles": {
            "candidate_role": getattr(args, "candidate_role", "confirmation"),
            "repeat_role": getattr(args, "repeat_role", "a"),
        },
        "ledger_path": str(_ledger_path(args)) if _ledger_path(args) else None,
        "batch_id": args.batch_id,
        "remaining_fits": int(getattr(args, "remaining_fits", 1)),
        "monitor_interval": float(
            getattr(args, "monitor_interval", protocol.MONITOR_INTERVAL_SECONDS)
        ),
        "memory_limit_bytes": int(
            getattr(args, "memory_limit_bytes", protocol.MEMORY_STOP_BYTES)
        ),
        "setup_seconds": float(getattr(args, "setup_seconds", 0.0)),
        "argv": [sys.executable, "-m", MODULE, *sys.argv[1:]],
    }
    if operation == "resume":
        parent = Path(args.parent)
        parent_config = artifacts.read_json(
            parent / protocol.RUN_DIRECTORY_FILES["config"]
        )
        request["config"] = parent_config["config"]
        request["roles"] = parent_config.get("roles") or request["roles"]
        request["parent_dir"] = str(parent.resolve())
        provenance = artifacts.read_json(
            parent / protocol.RUN_DIRECTORY_FILES["provenance"]
        )
        request["data_name"] = parent_config["dataset"]["name"]
        source_path = (provenance.get("data") or {}).get("source_path") or ""
        if request["data_path"] is None and not str(source_path).startswith("<"):
            request["data_path"] = source_path
    ledger = resources.Ledger(
        _ledger_path(args), batch_id=args.batch_id
    ) if _ledger_path(args) else None
    if ledger is not None and ledger.active_seconds() >= protocol.BATCH_SECONDS:
        _emit(
            {
                "status": "paused",
                "stage": "batch_budget",
                "reason": "the cumulative batch budget is exhausted",
                "active_seconds": ledger.active_seconds(),
                "limit_seconds": protocol.BATCH_SECONDS,
            }
        )
        lock.release()
        return EXIT_PAUSED
    inherited_fit_seconds = 0.0
    if operation == "resume":
        try:
            inherited = recovery.load_parent(Path(args.parent), ledger_path=_ledger_path(args), batch_id=args.batch_id)
            inherited_fit_seconds = inherited["fit_spent_seconds"]
        except Exception:
            lock.release()
            raise
    request["execution_id"] = f"{args.run_id}@{uuid.uuid4().hex}"
    request["controller_managed"] = True
    request["controller_started_at"] = stage_started
    if ledger is not None:
        # Persist one ledger identity before the worker can open the same file.
        ledger.record(execution_id=request["execution_id"], run_id=args.run_id,
                      seconds=max(0.0, time.monotonic() - stage_started), status="running")
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="effective-temporal-", delete=False
    )
    try:
        json.dump(request, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        handle.close()
        command = [sys.executable, "-m", MODULE, "_worker", "--request", handle.name]
        watchdog = None
        timeout_reason: Optional[Dict[str, Any]] = None
        try:
            process = subprocess.Popen(  # noqa: S603 - fixed interpreter and module
                command,
                cwd=str(artifacts.repo_root()),
                env=_worker_environment(),
            )
            watchdog = resources.Watchdog(
                sampler=lambda: resources.sample_process_tree_rss(process.pid),
                interval=request["monitor_interval"],
                limit_bytes=request["memory_limit_bytes"],
            )
            watchdog.sample_once()
            watchdog.start()
            code, timeout_reason = supervise_worker(
                process, watchdog=watchdog, ledger=ledger, request=request,
                started=stage_started, inherited_fit_seconds=inherited_fit_seconds)
        finally:
            if watchdog is not None:
                watchdog.stop()
        run_dir = root / args.run_id
        pause_reason = (
            watchdog.pause_reason()
            if watchdog is not None and watchdog.pause_reason() is not None
            else timeout_reason
        )
        if pause_reason is not None:
            _mark_controller_pause(run_dir, pause_reason)
            code = EXIT_PAUSED
        return _report_stage_result(run_dir, code)
    finally:
        lock.release()
        try:
            os.unlink(handle.name)
        except OSError:
            pass


def supervise_worker(process, *, watchdog, ledger, request, started,
                     inherited_fit_seconds=0.0, clock=time.monotonic, sleeper=time.sleep):
    """Enforce sampled stops independently and persist cost even on termination."""
    base = sum(float(entry["seconds"]) for entry in ledger.payload["entries"]
               if entry["execution_id"] != request["execution_id"] and entry["kind"] in {"measured", "replayed"}) if ledger is not None else 0.0
    reason = None
    def bill(status="running"):
        elapsed = max(0.0, clock() - started)
        if ledger is not None:
            ledger.record(execution_id=request["execution_id"], run_id=request["run_id"],
                          seconds=elapsed, status=status)
        return elapsed
    try:
        while process.poll() is None:
            elapsed = bill()
            reason = watchdog.pause_reason()
            if reason is None and inherited_fit_seconds + elapsed > protocol.FIT_SECONDS:
                reason = {"reason": "single fit exceeded the 60 min wall-clock limit",
                          "elapsed_seconds": inherited_fit_seconds + elapsed}
            if reason is None and base + elapsed > protocol.BATCH_SECONDS:
                reason = {"reason": "cumulative batch budget exhausted", "active_seconds": base + elapsed}
            if reason is not None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                break
            sleeper(min(0.5, request["monitor_interval"]))
        return process.wait(), reason
    finally:
        bill("paused" if reason else "finished")


def _mark_controller_pause(run_dir: Path, reason: Mapping[str, Any]) -> None:
    from . import artifacts

    status_path = run_dir / protocol.RUN_DIRECTORY_FILES["status"]
    if not status_path.exists():
        return
    status_doc = artifacts.read_json(status_path)
    status_doc.update(
        {
            "state": "paused",
            "detail": {"stop": dict(reason)},
            "updated": datetime.datetime.now()
            .astimezone()
            .isoformat(timespec="seconds"),
        }
    )
    artifacts.write_json_atomic(status_path, status_doc)


def _report_stage_result(run_dir: Path, code: int) -> int:
    from . import artifacts

    report_path = run_dir / "report.json"
    summary: Dict[str, Any] = {"run_dir": str(run_dir), "exit_code": code}
    if report_path.exists():
        report = artifacts.read_json(report_path)
        summary.update(
            {
                "status": report.get("status"),
                "selected_epoch": report.get("selected_epoch"),
                "validation": report.get("validation"),
                "error": report.get("error"),
            }
        )
    _emit(summary)
    if code == 0:
        return EXIT_OK
    if code == EXIT_PAUSED:
        return EXIT_PAUSED
    if code == EXIT_USAGE:
        return EXIT_USAGE
    return EXIT_FAIL


def _handle_worker(args: argparse.Namespace) -> int:
    from . import runner

    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    try:
        result = runner.run_fit(request)
    except protocol.ProtocolError as exc:
        _emit({"status": "fail", "kind": "protocol", "error": str(exc)})
        return EXIT_USAGE
    except Exception as exc:
        _emit(
            {
                "status": "fail",
                "kind": type(exc).__name__,
                "error": str(exc),
            }
        )
        return EXIT_FAIL
    _emit(result)
    return EXIT_OK if result["status"] == "completed" else EXIT_PAUSED


def _parse_seed_runs(values: Sequence[str], label: str) -> Dict[int, str]:
    parsed: Dict[int, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(
                f"{label} must be given as SEED=PATH, for example 0=scratch/run-a0"
            )
        seed, path = value.split("=", 1)
        try:
            seed_value = int(seed)
        except ValueError as exc:
            raise SystemExit(f"{label} seed {seed!r} is not an integer") from exc
        if seed_value in parsed:
            raise SystemExit(f"{label} seed {seed_value} was supplied twice")
        parsed[seed_value] = path
    return parsed


def _handle_select(args: argparse.Namespace) -> int:
    from . import runner

    if len(args.candidates) != 2:
        _emit(
            {
                "status": "failed",
                "reason": (
                    "select needs exactly two seed-0 screening candidates "
                    f"({list(protocol.LR_CANDIDATES)}); got {len(args.candidates)}"
                ),
            }
        )
        return EXIT_USAGE
    try:
        result = runner.run_select(
            {
                "block_id": args.block_id,
                "purpose": args.purpose,
                "output_root": str(args.output_root) if args.output_root else None,
                "candidates": [str(path) for path in args.candidates],
                "argv": [sys.executable, "-m", MODULE, *sys.argv[1:]],
            }
        )
    except Exception as exc:
        _emit({"status": "failed", "error": str(exc)})
        return EXIT_FAIL
    _emit(
        {
            "block_dir": result["block_dir"],
            "status": result["status"],
            "winner": (result["selection"] or {}).get("winner"),
        }
    )
    return EXIT_OK if result["status"] == "frozen" else EXIT_INCOMPLETE


def _handle_diagnose(args: argparse.Namespace) -> int:
    from . import diagnostics

    try:
        a_runs = _parse_seed_runs(args.a_runs, "--a-run")
        b_runs = _parse_seed_runs(args.b_runs, "--b-run")
    except SystemExit as exc:
        _emit({"status": "failed", "reason": str(exc)})
        return EXIT_USAGE
    try:
        result = diagnostics.run_diagnose(
            {
                "block_dir": str(args.block),
                "purpose": args.purpose,
                "a_runs": a_runs,
                "b_runs": b_runs,
                "ridge_path": str(args.ridge) if args.ridge else None,
                "report_path": str(args.report_path),
                "diagnostics_id": args.diagnostics_id,
                "ledger_path": str(args.ledger) if args.ledger else None,
                "remaining_fits": args.remaining_fits,
                "dataset": args.dataset,
                "model": args.model,
                "argv": [sys.executable, "-m", MODULE, *sys.argv[1:]],
            }
        )
    except Exception as exc:
        _emit({"status": "failed", "error": str(exc)})
        return EXIT_FAIL
    _emit(
        {
            "report_path": result["report_path"],
            "status": result["status"],
            "learning_ready": result["learning_ready"],
        }
    )
    if result["status"] == "pass":
        return EXIT_OK
    if result["status"] == "incomplete":
        return EXIT_INCOMPLETE
    return EXIT_FAIL


def _handle_report(args: argparse.Namespace) -> int:
    from . import runner

    try:
        result = runner.run_report(
            {
                "block_dir": str(args.block),
                "run_dir": str(args.run_dir),
                "run_id": args.run_id,
                "purpose": args.purpose,
                "output_root": str(args.output_root) if args.output_root else None,
                "data_name": args.data_name,
                "data_path": str(_data_path(args)) if _data_path(args) else None,
                "graph_path": str(args.graph) if args.graph else None,
                "mask_bundle": str(args.mask_bundle) if args.mask_bundle else None,
                "diagnostics_dir": str(args.diagnostics) if args.diagnostics else None,
                "argv": [sys.executable, "-m", MODULE, *sys.argv[1:]],
            }
        )
    except Exception as exc:
        _emit({"status": "failed", "error": str(exc)})
        return EXIT_FAIL
    _emit(result)
    return EXIT_OK if result["status"] == "completed" else EXIT_INCOMPLETE


def _handle_recompute(args: argparse.Namespace) -> int:
    from . import checks

    try:
        result = checks.run_recompute(
            run_dir=args.run_dir,
            report_path=args.report_path,
            argv=[sys.executable, "-m", MODULE, *sys.argv[1:]],
        )
    except Exception as exc:
        _emit({"status": "failed", "error": str(exc)})
        return EXIT_FAIL
    _emit(
        {
            "report_path": result["report_path"],
            "status": result["status"],
        }
    )
    return EXIT_OK if result["status"] == "pass" else EXIT_FAIL


def _handle_compare(args: argparse.Namespace) -> int:
    from . import checks

    try:
        result = checks.run_compare(
            run_a=args.run_a,
            run_b=args.run_b,
            report_path=args.report_path,
            argv=[sys.executable, "-m", MODULE, *sys.argv[1:]],
        )
    except Exception as exc:
        _emit({"status": "failed", "error": str(exc)})
        return EXIT_FAIL
    _emit(
        {
            "report_path": result["report_path"],
            "status": result["status"],
        }
    )
    return EXIT_OK if result["status"] == "pass" else EXIT_FAIL


HANDLERS = {
    "preflight": _handle_preflight,
    "fit": lambda args: _run_stage(args, "fit"),
    "resume": lambda args: _run_stage(args, "resume"),
    "select": _handle_select,
    "diagnose": _handle_diagnose,
    "report": _handle_report,
    "recompute": _handle_recompute,
    "compare": _handle_compare,
    "_worker": _handle_worker,
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not arguments:
        parser.print_help()
        return EXIT_OK
    if arguments[0] in {"-h", "--help"}:
        parser.print_help()
        return EXIT_OK
    if arguments[0] not in SUBCOMMANDS:
        print(MIGRATION_MESSAGE, file=sys.stderr)
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    from . import resources

    resources.configure_threads()
    args = parser.parse_args(arguments)
    handler = HANDLERS[args.handler]
    try:
        return handler(args)
    except protocol.ProtocolError as exc:
        _emit({"status": "fail", "kind": "protocol", "error": str(exc)})
        return EXIT_USAGE
    except SystemExit as exc:
        _emit({"status": "fail", "reason": str(exc)})
        return EXIT_USAGE
    except Exception as exc:
        _emit(
            {
                "status": "fail",
                "kind": type(exc).__name__,
                "error": str(exc),
            }
        )
        return EXIT_FAIL
