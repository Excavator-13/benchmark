"""Isolated CPU worker supervisor with stage deadlines and RSS monitoring.

The supervisor reserves the exclusive output directory, launches a fresh worker
with single-thread BLAS settings already in the environment, samples progress and
process RSS, and preserves a non-success terminal state on timeout, memory
overshoot, cancellation or worker death.  It never retries automatically.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import artifacts, protocol, runner

__all__ = [
    "SupervisorError",
    "launch",
]

BLAS_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)

WORKER_MODULE = "benchmark.occupation_skill_graph._worker"
BUILD_STAGES = frozenset(("starting", "source", "construct", "targets", "finalize"))
TREND_STAGE = "trends"


class SupervisorError(RuntimeError):
    """Raised when monitoring or worker launching cannot be enforced."""


def _worker_environment() -> Dict[str, str]:
    environment = dict(os.environ)
    for variable in BLAS_VARIABLES:
        environment[variable] = "1"
    return environment


def _stage_limit(spec: runner.BuildSpec, stage: str) -> float:
    if stage == TREND_STAGE:
        return float(spec.trend_timeout_seconds)
    return float(spec.build_timeout_seconds)


def _write_supervisor_record(
    run: artifacts.RunDirectory, payload: Dict[str, Any]
) -> None:
    try:
        run.write_json("artifacts/supervisor.json", payload)
    except OSError:  # pragma: no cover - evidence best effort on cancellation
        pass


def _terminate(process: subprocess.Popen, *, grace_seconds: float = 5.0) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
    except OSError:  # pragma: no cover - process race
        return
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:  # pragma: no cover - process race
            pass
        try:
            process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:  # pragma: no cover - unkillable process
            pass


def launch(
    spec: runner.BuildSpec,
    *,
    worker_argv: Optional[Sequence[str]] = None,
    probe: Optional[Callable[[int], Dict[str, Any]]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> int:
    """Reserve output, launch one worker and enforce the recorded limits."""
    probe = probe or artifacts.process_rss_bytes
    preflight = probe(os.getpid())
    if preflight.get("status") != "ok":
        raise SupervisorError(
            "process RSS monitoring is unavailable; refusing to launch because "
            "the recorded memory limit could not be enforced: "
            f"{preflight.get('reason')}"
        )
    run = runner.reserve_run_directory(spec)
    spec_path: Optional[Path] = None
    process: Optional[subprocess.Popen] = None
    cancelled = False
    observed_peak_rss = 0
    termination_reason: Optional[str] = None
    termination_detail: Dict[str, Any] = {}

    def _cancel(signum: int, _frame: Any) -> None:
        nonlocal cancelled
        cancelled = True
        if process is not None and process.poll() is None:
            try:
                process.send_signal(signum)
            except (OSError, ValueError):  # pragma: no cover - process race
                pass

    previous = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, _cancel)
        except (ValueError, OSError):  # pragma: no cover - non-main thread
            pass
    try:
        spec_payload = spec.to_dict()
        spec_payload["run_reserved"] = True
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", prefix="osg-spec-", delete=False
        )
        try:
            json.dump(spec_payload, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        spec_path = Path(handle.name)
        argv = (
            list(worker_argv)
            if worker_argv is not None
            else [
                sys.executable,
                "-m",
                WORKER_MODULE,
                "--spec",
                str(spec_path),
            ]
        )
        started = time.monotonic()
        _write_supervisor_record(run, {"status": "running", "limits": spec.limits()})
        process = subprocess.Popen(
            argv,
            cwd=str(Path(spec.repo_root)),
            env=_worker_environment(),
        )
        try:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    cancelled = True
                    _terminate(process)
                    break
                returncode = process.poll()
                if returncode is not None:
                    break
                progress = artifacts.read_progress(run.path)
                now_epoch = time.time()
                now_monotonic = time.monotonic()
                stage = str(progress.get("stage")) if progress else "starting"
                stage_started = None
                if progress and progress.get("stage_started_epoch") is not None:
                    try:
                        stage_started = float(progress["stage_started_epoch"])
                    except (TypeError, ValueError):
                        stage_started = None
                if stage_started is not None:
                    elapsed = now_epoch - stage_started
                else:
                    elapsed = now_monotonic - started
                limit = _stage_limit(spec, stage)
                rss = probe(process.pid)
                if rss.get("status") == "ok" and rss.get("bytes") is not None:
                    observed_peak_rss = max(observed_peak_rss, int(rss["bytes"]))
                    if int(rss["bytes"]) > int(spec.max_rss_bytes):
                        termination_reason = "rss_limit_exceeded"
                        termination_detail = {
                            "observed_bytes": int(rss["bytes"]),
                            "limit_bytes": int(spec.max_rss_bytes),
                            "measurement": rss,
                        }
                        _terminate(process)
                        break
                else:
                    # A missing sample is harmless only if the worker exited
                    # during the probe; a live process must remain enforceable.
                    if process.poll() is not None:
                        break
                    termination_reason = "rss_monitor_failure"
                    termination_detail = {"stage": stage, "measurement": rss}
                    _terminate(process)
                    break
                if elapsed > limit:
                    termination_reason = (
                        "trend_stage_timeout"
                        if stage == TREND_STAGE
                        else "construction_stage_timeout"
                    )
                    termination_detail = {
                        "stage": stage,
                        "elapsed_seconds": float(elapsed),
                        "limit_seconds": float(limit),
                    }
                    _terminate(process)
                    break
                if returncode is not None:
                    break
                time.sleep(float(spec.monitor_interval_seconds))
        except BaseException:
            _terminate(process)
            raise
        returncode = process.wait() if process is not None else 1
        supervisor_record = {
            "status": "terminated" if termination_reason else (
                "interrupted" if cancelled else "completed"
            ),
            "reason": termination_reason or ("cancellation" if cancelled else None),
            "detail": termination_detail,
            "worker_returncode": int(returncode),
            "worker_pid": int(process.pid) if process is not None else None,
            "observed_peak_rss_bytes": int(observed_peak_rss),
            "observed_peak_rss_scope": "sampled worker resident set size",
            "limits": spec.limits(),
            "thread_environment": {
                name: _worker_environment().get(name) for name in BLAS_VARIABLES
            },
            "time": artifacts.iso_now(),
        }
        _write_supervisor_record(run, supervisor_record)
        if termination_reason is not None:
            (run.path / protocol.MANIFEST_FILE).unlink(missing_ok=True)
            artifacts.write_status(
                run,
                "terminated",
                stage=(termination_detail.get("stage") or "unknown"),
                reason=termination_reason,
                detail=termination_detail,
                observed_peak_rss_bytes=int(observed_peak_rss),
                worker_returncode=int(returncode),
                completed_stages=(
                    artifacts.read_progress(run.path) or {}
                ).get("completed_stages", []),
            )
            print(
                f"worker terminated: {termination_reason} "
                f"{json.dumps(termination_detail, sort_keys=True)}",
                file=sys.stderr,
            )
            return 1
        if cancelled:
            (run.path / protocol.MANIFEST_FILE).unlink(missing_ok=True)
            artifacts.write_status(
                run,
                "interrupted",
                stage="unknown",
                reason="cancellation",
                observed_peak_rss_bytes=int(observed_peak_rss),
                worker_returncode=int(returncode),
            )
            return 130
        status = None
        try:
            status = artifacts.read_status(run.path)
        except artifacts.ArtifactError:
            status = None
        if returncode != 0 or not isinstance(status, dict) or status.get("state") != "succeeded":
            if returncode == 0:
                artifacts.write_status(
                    run,
                    "failed",
                    stage=(status or {}).get("stage", "unknown"),
                    reason="worker_exited_without_success_evidence",
                    worker_returncode=int(returncode),
                )
            elif status is None or status.get("state") != "failed":
                # A nonzero worker exit after it wrote a success status (for
                # example a hard kill between the status write and process exit)
                # must never remain published as success.
                artifacts.write_status(
                    run,
                    "failed",
                    stage=(status or {}).get("stage", "unknown"),
                    reason=(
                        "worker_hard_killed_after_success_status"
                        if isinstance(status, dict)
                        and status.get("state") == "succeeded"
                        else "worker_exited_nonzero"
                    ),
                    worker_returncode=int(returncode),
                )
            return int(returncode) if returncode != 0 else 1
        return 0
    finally:
        for signum, handler in previous.items():
            try:
                signal.signal(signum, handler)
            except (ValueError, OSError):  # pragma: no cover - non-main thread
                pass
        if spec_path is not None:
            try:
                os.unlink(spec_path)
            except OSError:  # pragma: no cover - best effort cleanup
                pass
