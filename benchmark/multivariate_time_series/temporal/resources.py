"""Machine-readable preflight, single-worker locking, watchdog, ledger and cost.

The controller runs one CPU worker, sets BLAS/torch thread variables before the
worker imports torch, samples the worker process-tree RSS at intervals <= 5 s
with psutil and persists an active-time ledger that survives pauses and resumes.
The watchdog is an independent thread: a breach is recorded continuously and the
training loop reacts at the next complete epoch boundary, so a run never stops
mid-epoch with an ambiguous recovery state.
"""

from __future__ import annotations

import importlib.util
import json
import os
import statistics
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from benchmark.nograph_baseline.data import iso_now

from . import artifacts, protocol

THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)
REQUIRED_DEPENDENCIES = ("numpy", "pandas", "pyarrow", "torch", "psutil")


class ResourceError(RuntimeError):
    """Raised when resource evidence or a controller limit cannot be honoured."""


def configure_threads() -> Dict[str, str]:
    """Set every BLAS/torch thread variable before the worker imports torch."""
    for name in THREAD_VARIABLES:
        os.environ[name] = "1"
    return {name: os.environ[name] for name in THREAD_VARIABLES}


def dependency_report(
    missing: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Return per-dependency availability; ``missing`` injects a fixture failure."""
    injected = set(missing or ())
    found: Dict[str, Any] = {}
    for name in REQUIRED_DEPENDENCIES:
        present = name not in injected and importlib.util.find_spec(name) is not None
        found[name] = {"status": "pass" if present else "fail", "available": present}
    return found


def resource_availability(
    *,
    memory_available_bytes: Optional[int] = None,
    disk_free_bytes: Optional[int] = None,
    psutil_available: Optional[bool] = None,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Return the section-6 startup resource check."""
    memory = memory_available_bytes
    disk = disk_free_bytes
    psutil_present = (
        psutil_available
        if psutil_available is not None
        else importlib.util.find_spec("psutil") is not None
    )
    if memory is None or disk is None:
        try:
            import psutil

            if memory is None:
                memory = int(psutil.virtual_memory().available)
            if disk is None:
                target = Path(output_path) if output_path is not None else Path.cwd()
                root = target
                while not root.exists() and root != root.parent:
                    root = root.parent
                disk = int(psutil.disk_usage(str(root)).free)
        except Exception as exc:  # pragma: no cover - psutil absent
            return {
                "status": "fail",
                "reason": f"resource measurement is unavailable: {type(exc).__name__}: {exc}",
                "memory_available_bytes": memory,
                "disk_free_bytes": disk,
                "psutil_available": psutil_present,
            }
    checks = {
        "available_memory": {
            "value": memory,
            "minimum": protocol.AVAILABLE_MEMORY_MIN_BYTES,
            "status": "pass"
            if memory is not None and memory >= protocol.AVAILABLE_MEMORY_MIN_BYTES
            else "fail",
        },
        "free_disk": {
            "value": disk,
            "minimum": protocol.DISK_FREE_MIN_BYTES,
            "status": "pass"
            if disk is not None and disk >= protocol.DISK_FREE_MIN_BYTES
            else "fail",
        },
        "rss_monitoring": {
            "value": psutil_present,
            "status": "pass" if psutil_present else "fail",
            "reason": None if psutil_present else "psutil is required for RSS sampling",
        },
    }
    failed = [name for name, check in checks.items() if check["status"] != "pass"]
    return {
        "status": "pass" if not failed else "fail",
        "checks": checks,
        "failed": failed,
        "memory_available_bytes": memory,
        "disk_free_bytes": disk,
        "psutil_available": psutil_present,
        "memory_stop_bytes": protocol.MEMORY_STOP_BYTES,
        "monitor_interval_seconds": protocol.MONITOR_INTERVAL_SECONDS,
    }


# -- locking ----------------------------------------------------------------
def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # pragma: no cover - another user's process
        return True
    except OSError:  # pragma: no cover - platform dependent
        return False
    return True


def inspect_lock(path: Path) -> Dict[str, Any]:
    """Return the current owner state of a worker lock file."""
    path = Path(path)
    if not path.exists():
        return {"status": "free", "path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "stale",
            "path": str(path),
            "reason": f"lock file is unreadable: {type(exc).__name__}: {exc}",
        }
    pid = int(payload.get("pid", 0))
    alive = _pid_alive(pid)
    return {
        "status": "held" if alive else "stale",
        "path": str(path),
        "owner": payload,
        "pid": pid,
        "pid_alive": alive,
    }


class WorkerLock:
    """One-process worker lock with explicit PID identity and stale handling."""

    def __init__(self, path: Path, owner: Mapping[str, Any]):
        self.path = Path(path)
        self.owner = dict(owner)
        self.acquired = False
        self.state: Dict[str, Any] = {}

    def acquire(self, *, takeover_stale: bool = False) -> Dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        current = inspect_lock(self.path)
        if current["status"] == "held":
            self.state = {
                **current,
                "status": "conflict",
                "owner_status": current.get("status"),
                "reason": (
                    "another controller holds the worker lock "
                    f"(pid {current.get('pid')}); one worker only"
                ),
            }
            return self.state
        if current["status"] == "stale":
            if not takeover_stale:
                self.state = {
                    **current,
                    "status": "conflict",
                    "owner_status": current.get("status"),
                    "reason": (
                        "the worker lock records a dead owner; remove the stale "
                        "lock explicitly with --takeover-stale before starting"
                    ),
                }
                return self.state
            try:
                self.path.unlink()
            except FileNotFoundError:  # pragma: no cover - race
                pass
        payload = {
            **self.owner,
            "pid": os.getpid(),
            "created": iso_now(),
        }
        try:
            descriptor = os.open(
                self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644
            )
        except FileExistsError:
            current = inspect_lock(self.path)
            self.state = {
                **current,
                "status": "conflict",
                "owner_status": current.get("status"),
                "reason": "another controller acquired the worker lock concurrently",
            }
            return self.state
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.acquired = True
        self.state = {"status": "acquired", "path": str(self.path), "owner": payload}
        return self.state

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            current = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = None
        if current is not None and int(current.get("pid", -1)) != os.getpid():
            self.acquired = False
            return
        try:
            self.path.unlink()
        except FileNotFoundError:  # pragma: no cover
            pass
        self.acquired = False

    def __enter__(self) -> "WorkerLock":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.release()


# -- ledger -----------------------------------------------------------------
class Ledger:
    """Persistent batch active-time ledger.

    Paused wall-clock time with no worker process is never counted: only
    measured execution durations (including failed, interrupted and replayed
    work) accumulate.
    """

    VERSION = 1

    def __init__(self, path: Path, batch_id: str):
        self.path = Path(path)
        self.batch_id = batch_id
        self.payload = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("version") != self.VERSION:
                raise ResourceError(
                    f"{self.path}: ledger version {payload.get('version')!r} is not "
                    f"{self.VERSION}"
                )
            payload.setdefault("entries", [])
            if payload.get("batch_id") and payload["batch_id"] != self.batch_id:
                raise ResourceError(
                    f"{self.path}: ledger belongs to batch {payload['batch_id']!r}, "
                    f"not {self.batch_id!r}"
                )
            return payload
        return {
            "version": self.VERSION,
            "batch_id": self.batch_id,
            "created": iso_now(),
            "entries": [],
        }

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)

    def record(
        self,
        *,
        execution_id: str,
        run_id: str,
        seconds: float,
        kind: str = "measured",
        status: str = "completed",
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        if kind not in {"measured", "estimated", "replayed"}:
            raise ResourceError(f"unsupported ledger entry kind {kind!r}")
        seconds = max(0.0, float(seconds))
        entry = {
            "execution_id": execution_id,
            "run_id": run_id,
            "seconds": seconds,
            "kind": kind,
            "status": status,
            "recorded": iso_now(),
            "note": note,
        }
        self.payload["entries"].append(entry)
        self.payload["updated"] = entry["recorded"]
        self._write()
        return entry

    def active_seconds(self) -> float:
        """Measured + replayed execution seconds (estimates never count)."""
        return float(
            sum(
                entry["seconds"]
                for entry in self.payload["entries"]
                if entry["kind"] in {"measured", "replayed"}
            )
        )

    def estimated_seconds(self) -> float:
        return float(
            sum(
                entry["seconds"]
                for entry in self.payload["entries"]
                if entry["kind"] == "estimated"
            )
        )

    def remaining_seconds(self, limit: float = protocol.BATCH_SECONDS) -> float:
        return max(0.0, float(limit) - self.active_seconds())

    def payload_view(self) -> Dict[str, Any]:
        return {
            "version": self.VERSION,
            "batch_id": self.batch_id,
            "path": str(self.path),
            "active_seconds": self.active_seconds(),
            "estimated_seconds": self.estimated_seconds(),
            "entries": len(self.payload["entries"]),
        }


# -- watchdog ---------------------------------------------------------------
def sample_process_tree_rss(root_pid: int) -> Dict[str, Any]:
    """Sample the RSS of one process and all descendants via psutil."""
    import psutil

    process = psutil.Process(root_pid)
    total = int(process.memory_info().rss)
    processes = 1
    for child in process.children(recursive=True):
        try:
            total += int(child.memory_info().rss)
            processes += 1
        except psutil.Error:  # pragma: no cover - process exited mid-walk
            continue
    return {
        "status": "ok",
        "rss_bytes": total,
        "processes": processes,
        "root_pid": int(root_pid),
        "timestamp": iso_now(),
    }


class Watchdog:
    """Independent RSS/active-time sampler reacting at epoch boundaries."""

    def __init__(
        self,
        *,
        sampler: Callable[[], Mapping[str, Any]],
        clock: Callable[[], float] = time.monotonic,
        interval: float = protocol.MONITOR_INTERVAL_SECONDS,
        limit_bytes: int = protocol.MEMORY_STOP_BYTES,
        started_at: Optional[float] = None,
    ):
        if interval <= 0 or interval > protocol.MONITOR_INTERVAL_SECONDS:
            raise ResourceError(
                "the monitor interval must be positive and at most "
                f"{protocol.MONITOR_INTERVAL_SECONDS} s"
            )
        self.sampler = sampler
        self.clock = clock
        self.interval = float(interval)
        self.limit_bytes = int(limit_bytes)
        self.started_at = clock() if started_at is None else started_at
        self.samples: List[Dict[str, Any]] = []
        self.breach: Optional[Dict[str, Any]] = None
        self.monitor_failure: Optional[Dict[str, Any]] = None
        self.peak_rss_bytes = 0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def sample_once(self) -> Dict[str, Any]:
        """Take one sample; record breach or monitor failure, never raise."""
        timestamp = self.clock()
        try:
            sample = dict(self.sampler())
        except Exception as exc:  # monitoring failure must pause, not crash
            self.monitor_failure = {
                "reason": "process monitoring failed",
                "error": f"{type(exc).__name__}: {exc}",
                "at": timestamp,
            }
            return {"status": "monitor_failure", **self.monitor_failure}
        rss = int(sample.get("rss_bytes", 0))
        sample.update(
            {
                "sampled_at": timestamp,
                "active_seconds": max(0.0, timestamp - self.started_at),
                "limit_bytes": self.limit_bytes,
            }
        )
        self.samples.append(sample)
        self.peak_rss_bytes = max(self.peak_rss_bytes, rss)
        if rss > self.limit_bytes:
            self.breach = {
                "reason": "process-tree RSS exceeded the 8 GiB stopping line",
                "rss_bytes": rss,
                "limit_bytes": self.limit_bytes,
                "at": timestamp,
                "active_seconds": sample["active_seconds"],
            }
            return {"status": "breach", **self.breach}
        return {"status": "ok", **sample}

    def _loop(self) -> None:  # pragma: no cover - timing dependent
        while not self._stop.wait(self.interval):
            self.sample_once()
            if self.breach is not None or self.monitor_failure is not None:
                return

    def start(self) -> "Watchdog":
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def pause_reason(self) -> Optional[Dict[str, Any]]:
        if self.monitor_failure is not None:
            return dict(self.monitor_failure)
        if self.breach is not None:
            return dict(self.breach)
        return None

    def payload(self) -> Dict[str, Any]:
        return {
            "interval_seconds": self.interval,
            "limit_bytes": self.limit_bytes,
            "samples": self.samples,
            "peak_rss_bytes": self.peak_rss_bytes,
            "breach": self.breach,
            "monitor_failure": self.monitor_failure,
        }


# -- cost gate --------------------------------------------------------------
def steady_state_seconds(history: Sequence[Mapping[str, Any]]) -> Optional[float]:
    """Median complete-epoch wall time over epochs 6..10, or ``None``."""
    observed = {
        int(record["epoch"]): float(record["wall_seconds"])
        for record in history
        if int(record.get("epoch", -1)) in protocol.STEADY_STATE_EPOCHS
        and isinstance(record.get("wall_seconds"), (int, float))
    }
    if len(observed) != len(protocol.STEADY_STATE_EPOCHS):
        return None
    return float(statistics.median(observed[epoch] for epoch in protocol.STEADY_STATE_EPOCHS))


def estimate_fit_seconds(
    steady_seconds: float, *, setup_seconds: float, epochs: int = protocol.EPOCHS
) -> float:
    """Return ``1.3 * (setup + 2*epochs*t)`` (protocol section 6)."""
    return float(
        protocol.COST_RESERVE_FACTOR
        * (max(0.0, float(setup_seconds)) + 2.0 * float(epochs) * float(steady_seconds))
    )


def cost_gate(
    history: Sequence[Mapping[str, Any]],
    *,
    epochs: int = protocol.EPOCHS,
    setup_seconds: float = 0.0,
    spent_seconds: float = 0.0,
    sample_seconds: Optional[float] = None,
    remaining_fits: int = 1,
    batch_active_seconds: float = 0.0,
) -> Dict[str, Any]:
    """Evaluate the 10-epoch sample, single-fit and cumulative batch limits."""
    sample_epochs = [
        record for record in history if int(record.get("epoch", -1)) <= protocol.COST_SAMPLE_EPOCHS
    ]
    measured_sample = (
        sample_seconds
        if sample_seconds is not None
        else sum(float(record.get("wall_seconds", 0.0)) for record in sample_epochs)
    )
    steady = steady_state_seconds(history)
    estimate = (
        estimate_fit_seconds(steady, setup_seconds=setup_seconds, epochs=epochs)
        if steady is not None
        else None
    )
    checks: Dict[str, Any] = {}
    reasons: List[str] = []
    checks["sample_complete"] = {
        "value": len(sample_epochs),
        "required": protocol.COST_SAMPLE_EPOCHS,
        "status": "pass"
        if len(sample_epochs) >= protocol.COST_SAMPLE_EPOCHS
        else "incomplete",
    }
    if len(sample_epochs) < protocol.COST_SAMPLE_EPOCHS:
        reasons.append(
            f"cost sample needs {protocol.COST_SAMPLE_EPOCHS} complete epochs, found "
            f"{len(sample_epochs)}; the block is paused before continuing"
        )
    checks["sample_duration"] = {
        "value": measured_sample,
        "limit": protocol.COST_SAMPLE_SECONDS,
        "status": "pass"
        if measured_sample <= protocol.COST_SAMPLE_SECONDS
        else "fail",
    }
    if measured_sample > protocol.COST_SAMPLE_SECONDS:
        reasons.append(
            f"10-epoch sample {measured_sample:.1f}s exceeds "
            f"{protocol.COST_SAMPLE_SECONDS}s"
        )
    if steady is None:
        checks["steady_state"] = {
            "status": "incomplete",
            "reason": "median epoch 6..10 timing is unavailable",
        }
        reasons.append("steady-state epoch 6..10 timing is unavailable")
    else:
        checks["steady_state"] = {
            "status": "pass",
            "median_epoch_seconds": steady,
            "epochs": list(protocol.STEADY_STATE_EPOCHS),
        }
    if estimate is None:
        checks["single_fit"] = {"status": "incomplete"}
        checks["batch"] = {"status": "incomplete"}
    else:
        checks["single_fit"] = {
            "value": spent_seconds + estimate,
            "estimated_seconds": estimate,
            "spent_seconds": spent_seconds,
            "limit": protocol.FIT_SECONDS,
            "status": "pass"
            if spent_seconds + estimate <= protocol.FIT_SECONDS
            else "fail",
        }
        if spent_seconds + estimate > protocol.FIT_SECONDS:
            reasons.append(
                f"estimated single-fit cost {spent_seconds + estimate:.1f}s exceeds "
                f"{protocol.FIT_SECONDS}s"
            )
        projected = batch_active_seconds + remaining_fits * estimate
        checks["batch"] = {
            "projected_seconds": projected,
            "active_seconds": batch_active_seconds,
            "remaining_fits": int(remaining_fits),
            "estimated_seconds": estimate,
            "limit": protocol.BATCH_SECONDS,
            "status": "pass" if projected <= protocol.BATCH_SECONDS else "fail",
        }
        if projected > protocol.BATCH_SECONDS:
            reasons.append(
                f"projected block cost {projected:.1f}s plus spent "
                f"{batch_active_seconds:.1f}s exceeds {protocol.BATCH_SECONDS}s"
            )
    statuses = [check["status"] for check in checks.values()]
    if any(status == "fail" for status in statuses):
        status = "fail"
    elif any(status == "incomplete" for status in statuses):
        status = "incomplete"
    else:
        status = "ok"
    return {
        "status": status,
        "epochs": int(epochs),
        "sample_epochs": protocol.COST_SAMPLE_EPOCHS,
        "sample_measured_seconds": measured_sample,
        "steady_state_median_seconds": steady,
        "setup_seconds": max(0.0, float(setup_seconds)),
        "estimate_seconds": estimate,
        "estimate_definition": (
            "1.3 * (setup + 2*epochs*t), t = median complete-epoch wall time over "
            "epochs 6..10"
        ),
        "spent_seconds": spent_seconds,
        "remaining_fits": int(remaining_fits),
        "batch_active_seconds": batch_active_seconds,
        "batch_limit_seconds": protocol.BATCH_SECONDS,
        "fit_limit_seconds": protocol.FIT_SECONDS,
        "checks": checks,
        "measured": {"sample_seconds": measured_sample, "epoch_median_seconds": steady},
        "estimated": {"fit_seconds": estimate},
        "unknown": (
            []
            if steady is not None
            else ["steady-state cost is unknown until epochs 6..10 are measured"]
        ),
        "reasons": reasons,
    }


# -- preflight --------------------------------------------------------------
def preflight(
    *,
    purpose: str,
    operation: str = "fit",
    data_name: Optional[str] = None,
    model: str = "GRU",
    seed: int = 0,
    data_path: Optional[Path] = None,
    run_id: Optional[str] = None,
    output_root: Optional[Path] = None,
    ledger_path: Optional[Path] = None,
    lock_path: Optional[Path] = None,
    recovery_path: Optional[Path] = None,
    dependencies_missing: Optional[Sequence[str]] = None,
    memory_available_bytes: Optional[int] = None,
    disk_free_bytes: Optional[int] = None,
    psutil_available: Optional[bool] = None,
    thread_environment: Optional[Mapping[str, Optional[str]]] = None,
    data_identity: Optional[Mapping[str, Any]] = None,
    repo: Optional[Path] = None,
) -> Dict[str, Any]:
    """Return the machine-readable preflight record.

    The check path never requires real demand data: without a supplied source the
    data identity is explicitly ``not_supplied`` (a failing condition only for a
    formal fit), so ``--help`` and inspection commands stay usable offline.
    """
    protocol.validate_purpose(purpose)
    checks: Dict[str, Any] = {}
    root = Path(repo or artifacts.repo_root())
    protocol_sha = protocol.protocol_content_sha256()
    checks["protocol"] = {
        "status": "pass" if protocol_sha else "fail",
        "path": str(protocol.P02_PROTOCOL_PATH),
        "sha256": protocol_sha,
        "version": protocol.SCIENTIFIC_VERSION,
        "reason": None if protocol_sha else "the P02 protocol document is missing",
    }
    commit, commit_error = _git_commit(root)
    checks["source"] = {
        "status": "pass" if commit else "fail",
        "commit": commit,
        "dirty": None,
        "reason": commit_error,
    }
    environment = artifacts.capture_environment()
    checks["environment"] = {
        "status": "pass",
        "packages": environment["packages"],
        "python": environment["python_version_info"],
        "device": environment["device"],
    }
    dependencies = dependency_report(dependencies_missing)
    failed_dependencies = [
        name for name, entry in dependencies.items() if entry["status"] != "pass"
    ]
    checks["dependencies"] = {
        "status": "pass" if not failed_dependencies else "fail",
        "detail": dependencies,
        "missing": failed_dependencies,
    }
    env_threads = dict(thread_environment or {name: os.environ.get(name) for name in THREAD_VARIABLES})
    bad_threads = {
        name: value for name, value in env_threads.items() if str(value) != "1"
    }
    checks["threads"] = {
        "status": "pass" if not bad_threads else "fail",
        "environment": env_threads,
        "required": 1,
        "reason": None
        if not bad_threads
        else (
            "CPU single-thread settings are not established; run the entry point "
            "through its own CLI, which sets BLAS/torch thread variables to 1"
        ),
    }
    if data_identity is not None:
        checks["data"] = {
            "status": "pass",
            "identity": dict(data_identity),
        }
    elif data_path is not None:
        try:
            from . import data as temporal_data

            temporal = temporal_data.load_temporal_data(
                data_name or "", demand_path=Path(data_path)
            )
            checks["data"] = {"status": "pass", "identity": temporal.identity()}
        except Exception as exc:
            checks["data"] = {
                "status": "fail",
                "reason": f"{type(exc).__name__}: {exc}",
            }
    else:
        checks["data"] = {
            "status": "not_supplied" if purpose == "development" else "fail",
            "reason": (
                "no demand source was supplied; an inspection preflight does not "
                "require real data, a formal fit does"
            ),
        }
    if run_id is not None:
        output = (Path(output_root) if output_root is not None else artifacts.default_root(purpose, root)) / run_id
        try:
            artifacts.validate_run_id(run_id)
            artifacts.check_development_namespace(purpose, output, root)
            exists = output.exists()
            checks["output"] = {
                "status": "pass" if not exists else "fail",
                "path": str(output),
                "resolved": str(Path(output).resolve()),
                "fresh": not exists,
                "reason": None if not exists else "output identity already exists",
            }
        except Exception as exc:
            checks["output"] = {
                "status": "fail",
                "path": str(output),
                "reason": f"{type(exc).__name__}: {exc}",
            }
    else:
        checks["output"] = {
            "status": "not_applicable",
            "reason": "no run identity was requested",
        }
    if lock_path is not None:
        state = inspect_lock(Path(lock_path))
        checks["worker_lock"] = {
            "status": "pass" if state["status"] in {"free", "stale"} else "fail",
            "state": state,
            "reason": None
            if state["status"] in {"free", "stale"}
            else "another controller already owns the single worker lock",
        }
    else:
        checks["worker_lock"] = {
            "status": "not_applicable",
            "reason": "no worker lock was requested",
        }
    checks["resources"] = resource_availability(
        memory_available_bytes=memory_available_bytes,
        disk_free_bytes=disk_free_bytes,
        psutil_available=psutil_available,
        output_path=output_root,
    )
    if recovery_path is not None:
        checks["recovery"] = _check_recovery(Path(recovery_path), ledger_path)
    else:
        checks["recovery"] = {
            "status": "not_applicable",
            "reason": "this operation does not resume a parent trajectory",
        }
    failing = [
        name
        for name, check in checks.items()
        if check.get("status") in {"fail"}
    ]
    return {
        "kind": "preflight",
        "generated": iso_now(),
        "status": "pass" if not failing else "fail",
        "operation": operation,
        "purpose": purpose,
        "request": {
            "data_name": data_name,
            "model": model,
            "seed": int(seed),
            "run_id": run_id,
            "output_root": str(output_root) if output_root is not None else None,
        },
        "checks": checks,
        "failing_checks": failing,
        "scientific_version": protocol.SCIENTIFIC_VERSION,
        "protocol_sha256": protocol_sha,
        "thresholds": {
            "available_memory_bytes": protocol.AVAILABLE_MEMORY_MIN_BYTES,
            "free_disk_bytes": protocol.DISK_FREE_MIN_BYTES,
            "rss_stop_bytes": protocol.MEMORY_STOP_BYTES,
            "monitor_interval_seconds": protocol.MONITOR_INTERVAL_SECONDS,
        },
    }


def _git_commit(root: Path) -> tuple[Optional[str], Optional[str]]:
    from benchmark.nograph_baseline import artifacts as nb_artifacts

    commit, error = nb_artifacts.git_command(root, ["rev-parse", "HEAD"])
    return (commit.strip() if commit else None), error


def _check_recovery(
    recovery_path: Path, ledger_path: Optional[Path]
) -> Dict[str, Any]:
    try:
        from . import checkpoints

        payload = checkpoints.load_last(Path(recovery_path))
        remaining: Optional[float] = None
        if ledger_path is not None and Path(ledger_path).exists():
            ledger_payload = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
            active = sum(
                float(entry.get("seconds", 0.0))
                for entry in ledger_payload.get("entries", [])
                if entry.get("kind") in {"measured", "replayed"}
            )
            remaining = max(0.0, protocol.BATCH_SECONDS - active)
        usable = remaining is None or remaining > 0
        return {
            "status": "pass" if usable else "fail",
            "completed_epoch": payload.get("completed_epoch"),
            "updates": payload.get("updates"),
            "remaining_batch_seconds": remaining,
            "reason": None
            if usable
            else "the cumulative batch budget is exhausted; recovery cannot resume",
        }
    except Exception as exc:
        return {"status": "fail", "reason": f"{type(exc).__name__}: {exc}"}
