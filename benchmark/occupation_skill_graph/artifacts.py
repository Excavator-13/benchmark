"""Exclusive self-contained evidence directories, provenance and costs.

Run directories are reserved exclusively and never overwritten.  Payload arrays
are written atomically as ordinary ``.npy`` files (never object pickles).  The
checksum inventory deliberately excludes the mutable progress/status records;
the checker verifies every scientific payload listed there.
"""

from __future__ import annotations

import functools
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from benchmark.nograph_baseline import artifacts as nb_artifacts
from benchmark.nograph_baseline import data as nb_data
from benchmark.nograph_baseline import protocol as p01

from . import protocol
from .data import array_sha256, sha256_file

__all__ = [
    "ArtifactError",
    "RunExistsError",
    "RunDirectory",
    "validate_run_id",
    "iso_now",
    "runtime_source_paths",
    "capture_source",
    "capture_environment",
    "write_environment_snapshot",
    "checker_source_identity",
    "measure_peak_rss",
    "process_rss_bytes",
    "monitor_preflight",
    "finalize_manifest",
    "verify_manifest",
    "write_status",
    "read_status",
    "write_progress",
    "read_progress",
    "write_exclusive_json",
    "load_npy",
    "array_sha256",
    "sha256_file",
]

ArtifactError = nb_artifacts.ArtifactError
RunExistsError = nb_artifacts.RunExistsError
RunDirectory = nb_artifacts.RunDirectory
validate_run_id = nb_artifacts.validate_run_id
iso_now = nb_data.iso_now

#: Mutable or self-referential files are not part of the immutable inventory.
MANIFEST_EXCLUSIONS: Tuple[str, ...] = (
    protocol.MANIFEST_FILE,
    "events.jsonl",
    protocol.STATUS_FILE,
    protocol.PROGRESS_FILE,
)

#: Launcher files are not necessarily imported by the worker itself.
LAUNCHER_FILES: Tuple[str, ...] = (
    "__init__.py",
    "__main__.py",
    "_worker.py",
    "cli.py",
    "runner.py",
    "supervisor.py",
    "checks.py",
)

UTILITY_FILES: Tuple[str, ...] = (
    "benchmark/nograph_baseline/protocol.py",
    "benchmark/nograph_baseline/data.py",
    "benchmark/nograph_baseline/artifacts.py",
)


def runtime_source_paths(repo_root: Path) -> List[str]:
    """Repo-relative execution source paths actually used by this entry."""
    repo_root = Path(repo_root).resolve()
    found: set = set()
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        try:
            resolved = Path(filename).resolve()
        except OSError:  # pragma: no cover - unreadable module path
            continue
        if resolved.suffix != ".py" or not resolved.is_file():
            continue
        if "tests" in resolved.parts or "__pycache__" in resolved.parts:
            continue
        try:
            relative = resolved.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        if relative.startswith("benchmark/occupation_skill_graph/"):
            found.add(relative)
    for name in LAUNCHER_FILES:
        relative = f"benchmark/occupation_skill_graph/{name}"
        if (repo_root / relative).is_file():
            found.add(relative)
    for relative in UTILITY_FILES:
        if (repo_root / relative).is_file():
            found.add(relative)
    if (repo_root / "benchmark/__init__.py").is_file():
        found.add("benchmark/__init__.py")
    return sorted(found)


def capture_source(
    run: RunDirectory,
    repo_root: Path,
    *,
    protocol_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Capture scoped execution-source provenance and recoverable dirty content."""
    return nb_artifacts.capture_source(
        run,
        Path(repo_root),
        protocol_path=Path(protocol_path)
        if protocol_path is not None
        else protocol.PROTOCOL_PATH,
        runtime_paths=runtime_source_paths(repo_root),
    )


def capture_environment(repo_root: Path) -> Dict[str, Any]:
    """Capture interpreter, package, OS/CPU, BLAS and thread facts."""
    environment = nb_artifacts.capture_environment(Path(repo_root))
    environment["occupation_skill_graph"] = {
        "protocol_version": protocol.SCIENTIFIC_PROTOCOL_VERSION,
        "task_id": protocol.TASK_ID,
        "top_k": protocol.TOP_K,
        "score_block_size": protocol.SCORE_BLOCK_SIZE,
        "trend_block_size": protocol.TREND_BLOCK_SIZE,
        "min_positive_months": protocol.MIN_POSITIVE_MONTHS,
    }
    environment["thread_settings"] = {
        name: os.environ.get(name)
        for name in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        )
    }
    return environment


def write_environment_snapshot(run: RunDirectory, environment: Mapping[str, Any]) -> None:
    nb_artifacts.write_environment_snapshot(run, environment)


def checker_source_identity(repo_root: Path, *, patch_limit: int = 20000) -> Dict[str, Any]:
    """Honest checker source identity embedded in a check report."""
    repo_root = Path(repo_root)
    commit, commit_error = nb_artifacts.git_command(repo_root, ["rev-parse", "HEAD"])
    commit = commit.strip() if commit else None
    status, status_error = nb_artifacts.git_command(repo_root, ["status", "--porcelain"])
    runtime = runtime_source_paths(repo_root)
    status_map, scoped_status_error = nb_artifacts.scoped_git_status(repo_root, runtime)
    errors: Dict[str, str] = {}
    if commit_error:
        errors["commit"] = commit_error
    if status_error:
        errors["status"] = status_error
    if scoped_status_error:
        errors["scoped_status"] = scoped_status_error
    files: Dict[str, str] = {}
    dirty: List[str] = []
    untracked: List[str] = []
    for relative in runtime:
        absolute = repo_root / relative
        if not absolute.is_file():
            continue
        files[relative] = sha256_file(absolute)
        code = (status_map or {}).get(relative)
        if code == "??":
            untracked.append(relative)
        elif code is not None:
            dirty.append(relative)
    patch = ""
    if dirty:
        patch_text, patch_error = nb_artifacts.git_command(
            repo_root, ["diff", "HEAD", "--", *dirty]
        )
        if patch_error:
            errors["scoped_patch"] = patch_error
        patch = patch_text or ""
    patch_bytes = len(patch.encode("utf-8"))
    included = bool(patch) and patch_bytes <= patch_limit
    state_available = scoped_status_error is None
    scoped_files = sorted({*dirty, *untracked})
    return {
        "policy": "P02-T009-v1",
        "commit": commit,
        "identity_available": commit is not None,
        "whole_repository_dirty": (
            bool(status.strip()) if status is not None else None
        ),
        "scoped_state_available": state_available,
        "scoped_dirty": bool(scoped_files) if state_available else None,
        "files": files,
        "scoped_files": scoped_files if state_available else None,
        "patch_eligible_files": dirty if state_available else None,
        "untracked_files": untracked if state_available else None,
        "patch_included": included,
        "source_patch": patch if included else None,
        "patch_bytes": patch_bytes,
        "patch_omitted_reason": (
            None
            if included or not patch
            else f"scoped patch exceeds the {patch_limit} byte embedding limit"
        ),
        "errors": errors,
    }


def measure_peak_rss() -> Dict[str, Any]:
    """Measure this process's lifetime peak resident set in bytes."""
    if os.name == "nt":  # pragma: no cover - exercised on Windows
        return nb_artifacts.windows_peak_rss()
    import resource

    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        native_value = int(usage)
        native_unit = "bytes"
        bytes_value = int(usage)
    else:
        native_value = int(usage)
        native_unit = "KiB"
        bytes_value = int(usage) * 1024
    return {
        "bytes": bytes_value,
        "native_value": native_value,
        "native_unit": native_unit,
        "method": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
        "scope": "worker process lifetime",
        "status": "ok",
    }


def _macos_process_rss(pid: int) -> Dict[str, Any]:
    """Sample RSS through the native libproc task-info call on macOS."""
    import ctypes as c

    class TaskInfo(c.Structure):
        _fields_ = [
            ("virtual_size", c.c_uint64),
            ("resident_size", c.c_uint64),
            ("total_user", c.c_uint64),
            ("total_system", c.c_uint64),
            ("threads_user", c.c_uint64),
            ("threads_system", c.c_uint64),
            ("policy", c.c_int32),
            ("faults", c.c_int32),
            ("pageins", c.c_int32),
            ("cow_faults", c.c_int32),
            ("messages_sent", c.c_int32),
            ("messages_received", c.c_int32),
            ("syscalls_mach", c.c_int32),
            ("syscalls_unix", c.c_int32),
            ("csw", c.c_int32),
            ("threadnum", c.c_int32),
            ("numrunning", c.c_int32),
            ("priority", c.c_int32),
        ]

    try:
        libproc = c.CDLL("/usr/lib/libproc.dylib")
    except OSError as exc:  # pragma: no cover - unusual macOS
        return {
            "status": "unsupported",
            "bytes": None,
            "reason": f"libproc unavailable: {exc}",
            "method": "proc_pidinfo(PROC_PIDTASKINFO)",
            "scope": "worker process resident set size, sampled",
        }
    libproc.proc_pidinfo.argtypes = [
        c.c_int,
        c.c_int,
        c.c_uint64,
        c.c_void_p,
        c.c_int,
    ]
    libproc.proc_pidinfo.restype = c.c_int
    info = TaskInfo()
    written = libproc.proc_pidinfo(
        int(pid), 4, 0, c.byref(info), c.sizeof(info)
    )
    if written <= 0:
        return {
            "status": "unavailable",
            "bytes": None,
            "reason": "proc_pidinfo returned no task info",
            "method": "proc_pidinfo(PROC_PIDTASKINFO)",
            "scope": "worker process resident set size, sampled",
        }
    return {
        "status": "ok",
        "bytes": int(info.resident_size),
        "native_value": int(info.resident_size),
        "native_unit": "bytes",
        "method": "proc_pidinfo(PROC_PIDTASKINFO).pti_resident_size",
        "scope": "worker process resident set size, sampled",
    }


def _linux_process_rss(pid: int) -> Dict[str, Any]:
    """Sample RSS from /proc without spawning a helper process."""
    path = Path(f"/proc/{int(pid)}/status")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "status": "unavailable",
            "bytes": None,
            "reason": f"cannot read {path}: {exc}",
            "method": "/proc/<pid>/status VmRSS",
            "scope": "worker process resident set size, sampled",
        }
    for line in text.splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            if len(parts) >= 2:
                native = int(parts[1])
                return {
                    "status": "ok",
                    "bytes": native * 1024,
                    "native_value": native,
                    "native_unit": "KiB",
                    "method": "/proc/<pid>/status VmRSS",
                    "scope": "worker process resident set size, sampled",
                }
    return {
        "status": "unavailable",
        "bytes": None,
        "reason": "VmRSS is absent from /proc status",
        "method": "/proc/<pid>/status VmRSS",
        "scope": "worker process resident set size, sampled",
    }


def process_rss_bytes(pid: int) -> Dict[str, Any]:
    """Sample one process's resident set size with platform-aware units."""
    if os.name == "nt":  # pragma: no cover - exercised on Windows
        return _windows_process_rss(pid)
    if sys.platform == "darwin":  # pragma: no cover - macOS branch
        native = _macos_process_rss(pid)
        if native.get("status") == "ok":
            return native
        # Fall back to ps only when the native call is unavailable.
    if sys.platform.startswith("linux"):
        native = _linux_process_rss(pid)
        if native.get("status") == "ok":
            return native
    try:
        completed = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(int(pid))],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "unsupported",
            "bytes": None,
            "reason": f"ps unavailable: {type(exc).__name__}: {exc}",
            "method": "ps -o rss=",
            "scope": "worker process resident set size, sampled",
        }
    text = (completed.stdout or "").strip()
    if completed.returncode != 0 or not text:
        return {
            "status": "unavailable",
            "bytes": None,
            "reason": (completed.stderr or "ps returned no RSS").strip(),
            "method": "ps -o rss=",
            "scope": "worker process resident set size, sampled",
        }
    try:
        native = int(text.split()[0])
    except (ValueError, IndexError) as exc:
        return {
            "status": "unavailable",
            "bytes": None,
            "reason": f"unparseable ps output {text!r}: {exc}",
            "method": "ps -o rss=",
            "scope": "worker process resident set size, sampled",
        }
    return {
        "status": "ok",
        "bytes": int(native) * 1024,
        "native_value": int(native),
        "native_unit": "KiB",
        "method": "ps -o rss= (POSIX KiB converted to bytes)",
        "scope": "worker process resident set size, sampled",
    }


def _windows_process_rss(pid: int) -> Dict[str, Any]:  # pragma: no cover - Windows only
    import ctypes as c

    class Memory(c.Structure):
        _fields_ = [
            ("cb", c.c_ulong),
            ("PageFaultCount", c.c_ulong),
            ("PeakWorkingSetSize", c.c_size_t),
            ("WorkingSetSize", c.c_size_t),
            ("QuotaPeakPagedPoolUsage", c.c_size_t),
            ("QuotaPagedPoolUsage", c.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", c.c_size_t),
            ("QuotaNonPagedPoolUsage", c.c_size_t),
            ("PagefileUsage", c.c_size_t),
            ("PeakPagefileUsage", c.c_size_t),
        ]

    kernel = c.WinDLL("kernel32", use_last_error=True)
    psapi = c.WinDLL("psapi", use_last_error=True)
    kernel.OpenProcess.restype = c.c_void_p
    kernel.OpenProcess.argtypes = [c.c_ulong, c.c_int, c.c_ulong]
    psapi.GetProcessMemoryInfo.argtypes = [
        c.c_void_p,
        c.POINTER(Memory),
        c.c_ulong,
    ]
    psapi.GetProcessMemoryInfo.restype = c.c_int
    kernel.CloseHandle.argtypes = [c.c_void_p]
    handle = kernel.OpenProcess(0x0410, 0, int(pid))
    if not handle:
        return {
            "status": "unavailable",
            "bytes": None,
            "reason": f"OpenProcess failed: {c.get_last_error()}",
            "method": "GetProcessMemoryInfo.WorkingSetSize",
            "scope": "worker process resident set size, sampled",
        }
    try:
        memory = Memory()
        memory.cb = c.sizeof(memory)
        if not psapi.GetProcessMemoryInfo(handle, c.byref(memory), memory.cb):
            return {
                "status": "unavailable",
                "bytes": None,
                "reason": f"GetProcessMemoryInfo failed: {c.get_last_error()}",
                "method": "GetProcessMemoryInfo.WorkingSetSize",
                "scope": "worker process resident set size, sampled",
            }
        return {
            "status": "ok",
            "bytes": int(memory.WorkingSetSize),
            "native_value": int(memory.WorkingSetSize),
            "native_unit": "bytes",
            "method": "GetProcessMemoryInfo.WorkingSetSize",
            "scope": "worker process resident set size, sampled",
        }
    finally:
        kernel.CloseHandle(handle)


def monitor_preflight() -> Dict[str, Any]:
    """Verify that process RSS monitoring is available before launching."""
    result = process_rss_bytes(os.getpid())
    if result.get("status") != "ok":
        raise ArtifactError(
            "process RSS monitoring is unavailable; refusing to claim an "
            f"enforced memory limit: {result.get('reason')}"
        )
    return result


def finalize_manifest(run: RunDirectory) -> Dict[str, Any]:
    """Hash immutable payloads, excluding mutable progress/status records."""
    entries: Dict[str, str] = {}
    for path in run.iter_files():
        relative = path.relative_to(run.path).as_posix()
        if relative in MANIFEST_EXCLUSIONS:
            continue
        entries[relative] = sha256_file(path)
    payload = {
        "schema": "occupation-skill-graph-artifacts-v1",
        "run_id": run.run_id,
        "run_type": run.run_type,
        "generated": iso_now(),
        "algorithm": "sha256",
        "excluded": list(MANIFEST_EXCLUSIONS),
        "files": entries,
    }
    run.write_json(protocol.MANIFEST_FILE, payload)
    return payload


def verify_manifest(
    root: Path, manifest: Mapping[str, Any], *, required: Sequence[str] = ()
) -> List[str]:
    """Verify an inventory and directly check explicitly required payloads."""
    root = Path(root)
    problems: List[str] = []
    files = manifest.get("files")
    if not isinstance(files, Mapping):
        return ["checksum manifest has no files mapping"]
    for relative, expected in files.items():
        relative_path = Path(str(relative))
        if relative_path.is_absolute() or ".." in relative_path.parts:
            problems.append(f"unsafe artifact path in inventory: {relative}")
            continue
        path = root / relative_path
        if not path.is_file():
            problems.append(f"missing artifact: {relative}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            problems.append(
                f"checksum mismatch for {relative}: {expected} -> {actual}"
            )
    for relative in required:
        if relative in files:
            continue
        path = root / relative
        if not path.is_file():
            problems.append(f"required artifact is absent: {relative}")
        else:
            problems.append(f"required artifact is not in the inventory: {relative}")
    return problems


def write_status(run: RunDirectory, state: str, **extra: Any) -> Dict[str, Any]:
    """Write the replaceable internal terminal/current status record."""
    payload: Dict[str, Any] = {
        "schema": "occupation-skill-graph-status-v1",
        "run_id": run.run_id,
        "state": state,
        "updated": iso_now(),
    }
    payload.update(extra)
    run.write_json(protocol.STATUS_FILE, payload)
    return payload


def read_status(root: Path) -> Dict[str, Any]:
    path = Path(root) / protocol.STATUS_FILE
    if not path.is_file():
        raise ArtifactError(f"status record is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_progress(
    run: RunDirectory,
    *,
    stage: str,
    completed: int,
    total: Optional[int],
    stage_elapsed_seconds: float,
    stage_started_epoch: float,
    completed_stages: Sequence[str],
    **extra: Any,
) -> Dict[str, Any]:
    """Atomically replace the observable stage/block progress record."""
    payload: Dict[str, Any] = {
        "schema": "occupation-skill-graph-progress-v1",
        "run_id": run.run_id,
        "stage": stage,
        "completed": int(completed),
        "total": None if total is None else int(total),
        "stage_elapsed_seconds": float(stage_elapsed_seconds),
        "stage_started_epoch": float(stage_started_epoch),
        "completed_stages": list(completed_stages),
        "updated": iso_now(),
    }
    payload.update(extra)
    run.write_json(protocol.PROGRESS_FILE, payload)
    return payload


def read_progress(root: Path) -> Optional[Dict[str, Any]]:
    path = Path(root) / protocol.PROGRESS_FILE
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_exclusive_json(destination: Path, payload: Mapping[str, Any]) -> Path:
    """Publish one complete JSON document with exclusive creation."""
    destination = Path(destination)
    text = json.dumps(dict(payload), indent=2, sort_keys=True, ensure_ascii=False)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        descriptor = os.open(destination, flags, 0o644)
    except FileExistsError as exc:
        raise ArtifactError(
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


def load_npy(path: Path, *, expected_dtype: Optional[np.dtype] = None) -> np.ndarray:
    """Load a numeric array with pickles explicitly disabled."""
    array = np.load(Path(path), allow_pickle=False)
    if expected_dtype is not None and array.dtype != np.dtype(expected_dtype):
        raise ArtifactError(
            f"{path}: expected dtype {np.dtype(expected_dtype)}, got {array.dtype}"
        )
    return array
