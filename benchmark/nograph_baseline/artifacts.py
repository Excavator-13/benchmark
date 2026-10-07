"""Versioned, self-contained run directories and provenance capture.

Every run reserves a fresh exclusive directory under ``research/runs/<run_id>``
and refuses to overwrite an existing one.  JSON and numeric artifacts are
written atomically (same-directory temporary file + rename) and numeric arrays
are always loadable with ``allow_pickle=False``.  Git and environment capture
record explicit failures instead of guessing identities.
"""

from __future__ import annotations

import contextlib
import functools
import io
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from . import protocol
from .data import sha256_file, iso_now

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
IMMUTABLE_MANIFEST_EXCLUSIONS = ("artifacts-sha256.json", "events.jsonl")


class ArtifactError(RuntimeError):
    """Raised when evidence cannot be written or validated."""


class RunExistsError(FileExistsError):
    """Raised when a run ID collides with an existing directory."""


def validate_run_id(run_id: str) -> str:
    """Validate a single safe path-component run ID."""
    if not isinstance(run_id, str) or not run_id:
        raise ArtifactError("run ID must be a nonempty string")
    if run_id in (".", "..") or "/" in run_id or "\\" in run_id:
        raise ArtifactError(f"run ID {run_id!r} must be a single path component")
    if not RUN_ID_PATTERN.match(run_id):
        raise ArtifactError(
            f"run ID {run_id!r} must match {RUN_ID_PATTERN.pattern}"
        )
    return run_id


def runs_root(repo_root: Optional[Path] = None) -> Path:
    """Return the default runs root for a repository root."""
    if repo_root is None:
        return protocol.RUNS_DIR
    return Path(repo_root) / "research" / "runs"


class RunDirectory:
    """A reserved run directory with atomic writers and an event log."""

    def __init__(self, root: Path, run_id: str, run_type: str):
        validate_run_id(run_id)
        self.root = Path(root)
        self.run_id = run_id
        self.run_type = run_type
        self.path = self.root / run_id
        self.events_path = self.path / "events.jsonl"
        self._created = False

    # -- lifecycle ---------------------------------------------------------
    def reserve(self) -> "RunDirectory":
        """Create the run directory exclusively; refuse to reuse an ID."""
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.path.mkdir(exist_ok=False)
        except FileExistsError as exc:
            raise RunExistsError(
                f"run directory already exists and will not be overwritten: {self.path}"
            ) from exc
        self._created = True
        self.append_event(
            "run_reserved", run_id=self.run_id, run_type=self.run_type
        )
        self.set_status("running")
        return self

    def append_event(self, event: str, **fields: Any) -> None:
        """Append one JSON line to the append-only event log."""
        record = {"time": iso_now(), "event": event, "run_id": self.run_id}
        record.update(fields)
        line = json.dumps(record, sort_keys=True, ensure_ascii=False)
        with open(self.events_path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def set_status(self, state: str, **extra: Any) -> Dict[str, Any]:
        """Atomically write the terminal/current status record."""
        payload: Dict[str, Any] = {
            "run_id": self.run_id,
            "run_type": self.run_type,
            "state": state,
            "updated": iso_now(),
        }
        payload.update(extra)
        self.write_json("status.json", payload)
        return payload

    # -- paths and writers -------------------------------------------------
    def path_for(self, relative: str) -> Path:
        return self.path / relative

    def write_bytes(self, relative: str, data: bytes) -> Path:
        target = self.path_for(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="wb", dir=str(target.parent), prefix=".tmp-", delete=False
        )
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        os.replace(handle.name, target)
        return target

    def write_text(self, relative: str, text: str) -> Path:
        return self.write_bytes(relative, text.encode("utf-8"))

    def write_json(self, relative: str, payload: Any) -> Path:
        text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        return self.write_text(relative, text + "\n")

    def save_npy(self, relative: str, array: np.ndarray) -> Path:
        target = self.path_for(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="wb", dir=str(target.parent), prefix=".tmp-", delete=False
        )
        try:
            np.save(handle, np.ascontiguousarray(np.asarray(array)))
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        os.replace(handle.name, target)
        return target

    def save_npz(self, relative: str, **arrays: np.ndarray) -> Path:
        target = self.path_for(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="wb", dir=str(target.parent), prefix=".tmp-", delete=False
        )
        try:
            np.savez(handle, **{key: np.asarray(value) for key, value in arrays.items()})
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        os.replace(handle.name, target)
        return target

    def save_dataframe(self, relative: str, frame: "Any") -> Path:
        target = self.path_for(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="wb", dir=str(target.parent), prefix=".tmp-", delete=False
        )
        handle.close()
        frame.to_parquet(handle.name, index=False)
        os.replace(handle.name, target)
        return target

    def copy_file(self, source: Path, relative: str) -> Path:
        return self.write_bytes(relative, Path(source).read_bytes())

    # -- manifests ---------------------------------------------------------
    def iter_files(self) -> Iterable[Path]:
        for path in sorted(self.path.rglob("*")):
            if path.is_file() and not path.name.startswith(".tmp-"):
                yield path

    def finalize_artifacts_manifest(self) -> Dict[str, Any]:
        """Hash all terminal artifacts except the manifest itself and events."""
        entries: Dict[str, str] = {}
        for path in self.iter_files():
            relative = path.relative_to(self.path).as_posix()
            if relative in IMMUTABLE_MANIFEST_EXCLUSIONS:
                continue
            entries[relative] = sha256_file(path)
        payload = {
            "run_id": self.run_id,
            "run_type": self.run_type,
            "generated": iso_now(),
            "algorithm": "sha256",
            "excluded": list(IMMUTABLE_MANIFEST_EXCLUSIONS),
            "files": entries,
        }
        self.write_json("artifacts-sha256.json", payload)
        return payload


def git_command(repo_root: Path, args: Sequence[str]) -> Tuple[Optional[str], Optional[str]]:
    """Run a git command, returning ``(stdout, error)``.

    A failure is returned as an explicit error string rather than being
    silently treated as an empty/guessed identity.
    """
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        return None, f"git {' '.join(args)} exited {completed.returncode}: {message}"
    return completed.stdout, None


def capture_git(repo_root: Path) -> Dict[str, Any]:
    """Capture commit, working-tree status and tracked differences."""
    commit, commit_error = git_command(repo_root, ["rev-parse", "HEAD"])
    status, status_error = git_command(repo_root, ["status", "--short"])
    diff, diff_error = git_command(repo_root, ["diff", "HEAD"])
    untracked, untracked_error = git_command(
        repo_root, ["ls-files", "--others", "--exclude-standard"]
    )
    errors = {
        "commit": commit_error,
        "status": status_error,
        "diff": diff_error,
        "untracked": untracked_error,
    }
    dirty = None
    if status is not None:
        dirty = bool(status.strip())
    return {
        "commit": commit.strip() if commit else None,
        "status": status,
        "diff": diff if diff is not None else "",
        "untracked_files": [line for line in (untracked or "").splitlines() if line],
        "dirty": dirty,
        "errors": {key: value for key, value in errors.items() if value},
        "identity_available": commit is not None,
    }


def capture_untracked_source(
    run: RunDirectory, repo_root: Path, scope: str = "benchmark/nograph_baseline"
) -> Dict[str, Any]:
    """Copy used untracked implementation files and hash them.

    The implementation may run before it is committed, so working-tree source
    is itself part of the run provenance.
    """
    untracked, error = git_command(
        repo_root, ["ls-files", "--others", "--exclude-standard", "--", scope]
    )
    if error is not None:
        return {"scope": scope, "error": error, "files": {}}
    files: Dict[str, str] = {}
    copied: List[str] = []
    for line in (untracked or "").splitlines():
        line = line.strip()
        if not line:
            continue
        source = repo_root / line
        if not source.is_file():
            continue
        relative = Path("code-untracked") / line
        run.copy_file(source, relative.as_posix())
        files[line] = sha256_file(source)
        copied.append(line)
    run.write_json(
        "code-untracked/manifest.json",
        {
            "scope": scope,
            "tracked_by_git": False,
            "files": files,
            "copied": sorted(copied),
        },
    )
    return {"scope": scope, "files": files, "copied": sorted(copied), "error": None}


def capture_environment(repo_root: Path) -> Dict[str, Any]:
    """Capture interpreter, package, OS/CPU and thread configuration facts."""
    import numpy
    import pandas

    try:
        import pyarrow
    except ImportError:  # pragma: no cover - pyarrow is required
        pyarrow = None

    optional: Dict[str, str] = {}
    try:
        import sklearn

        optional["sklearn"] = getattr(sklearn, "__version__", "unknown")
    except ImportError:
        optional["sklearn"] = None

    pip_freeze, pip_error = _pip_freeze()
    blas_text, blas_error = _numpy_blas_config()
    thread_variables = {
        name: os.environ.get(name)
        for name in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        )
    }
    return {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "python_version_info": list(sys.version_info[:3]),
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "packages": {
            "numpy": numpy.__version__,
            "pandas": pandas.__version__,
            "pyarrow": getattr(pyarrow, "__version__", None),
        },
        "optional_packages": optional,
        "pip_freeze": pip_freeze,
        "pip_freeze_error": pip_error,
        "numpy_blas_config": blas_text,
        "numpy_blas_config_error": blas_error,
        "thread_environment": thread_variables,
        "repo_root": str(repo_root),
    }


def _pip_freeze() -> Tuple[Optional[str], Optional[str]]:
    return _pip_freeze_cached()


@functools.lru_cache(maxsize=1)
def _pip_freeze_cached() -> Tuple[Optional[str], Optional[str]]:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if completed.returncode != 0:
        return None, completed.stderr.strip() or "pip freeze failed"
    return completed.stdout, None


def _numpy_blas_config() -> Tuple[Optional[str], Optional[str]]:
    return _numpy_blas_config_cached()


@functools.lru_cache(maxsize=1)
def _numpy_blas_config_cached() -> Tuple[Optional[str], Optional[str]]:
    import warnings

    import numpy

    buffer = io.StringIO()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(
                io.StringIO()
            ):
                numpy.show_config()
    except Exception as exc:  # pragma: no cover - platform dependent
        return None, f"{type(exc).__name__}: {exc}"
    return buffer.getvalue(), None


def write_git_snapshot(run: RunDirectory, git: Mapping[str, Any]) -> None:
    """Persist the captured git evidence in its documented text files."""
    commit = git.get("commit")
    run.write_text(
        "git-commit.txt",
        (commit + "\n") if commit else "UNAVAILABLE\n",
    )
    status = git.get("status")
    run.write_text(
        "git-status.txt",
        status if status is not None else "UNAVAILABLE\n",
    )
    run.write_text("git-diff.patch", str(git.get("diff") or ""))


def write_environment_snapshot(run: RunDirectory, environment: Mapping[str, Any]) -> None:
    """Persist ``pip freeze`` output as ``environment.txt``."""
    freeze = environment.get("pip_freeze")
    if freeze is None:
        run.write_text(
            "environment.txt",
            f"pip freeze unavailable: {environment.get('pip_freeze_error')}\n",
        )
    else:
        run.write_text("environment.txt", str(freeze))


def source_manifest(
    *,
    demand_path: Path,
    demand_sha256: str,
    protocol_path: Path,
    protocol_sha256: str,
    coverage_path: Optional[Path],
    coverage_sha256: Optional[str],
    reference_path: Optional[Path] = None,
    reference_sha256: Optional[str] = None,
    extra: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """Build the versioned ``source-sha256.json`` record."""
    sources: Dict[str, Any] = {
        "demand": {"path": str(demand_path), "sha256": demand_sha256},
        "protocol": {"path": str(protocol_path), "sha256": protocol_sha256},
    }
    if coverage_path is not None:
        sources["coverage"] = {
            "path": str(coverage_path),
            "sha256": coverage_sha256,
        }
    if reference_path is not None:
        sources["reference"] = {
            "path": str(reference_path),
            "sha256": reference_sha256,
        }
    if extra:
        for key, value in extra.items():
            sources[key] = {"path": None, "sha256": value}
    return {
        "run_id": None,
        "generated": iso_now(),
        "algorithm": "sha256",
        "sources": sources,
    }


def verify_source_hashes(manifest: Mapping[str, Any]) -> List[str]:
    """Re-hash every recorded source and return mismatch descriptions."""
    mismatches: List[str] = []
    for name, entry in manifest.get("sources", {}).items():
        path = entry.get("path")
        expected = entry.get("sha256")
        if not path or not expected:
            continue
        candidate = Path(path)
        if not candidate.exists():
            mismatches.append(f"{name}: source disappeared: {path}")
            continue
        actual = sha256_file(candidate)
        if actual != expected:
            mismatches.append(
                f"{name}: hash changed {expected} -> {actual} for {path}"
            )
    return mismatches
