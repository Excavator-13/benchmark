"""Exclusive run directories, scoped source capture and environment identity.

Run directories are created exclusively and never overwritten.  Provenance
captures only the execution-relevant source scope (the new package, the P01
numeric modules it imports and the scientific protocol), never unrelated
research records, tests or caches.  Clean committed files are located by fixed
commit and path; tracked modifications are retained as a patch that is proven to
reconstruct the executing bytes; necessary untracked content is copied.  A
missing Git identity is disclosed rather than fabricated.
"""

from __future__ import annotations

import functools
import io
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from benchmark.nograph_baseline import artifacts as nb_artifacts
from benchmark.nograph_baseline import protocol as p01
from benchmark.nograph_baseline.data import sha256_file

from . import protocol

__all__ = [
    "ArtifactError",
    "RunExistsError",
    "RunDirectory",
    "validate_run_id",
    "runtime_source_paths",
    "capture_source",
    "capture_environment",
    "checker_source_identity",
    "write_environment_snapshot",
    "measure_peak_rss",
    "source_manifest",
    "verify_source_hashes",
    "verify_captured_source",
    "now",
]

ArtifactError = nb_artifacts.ArtifactError
RunExistsError = nb_artifacts.RunExistsError
RunDirectory = nb_artifacts.RunDirectory
validate_run_id = nb_artifacts.validate_run_id
SOURCE_PATCH_LIMIT = nb_artifacts.SOURCE_PATCH_LIMIT


def now() -> str:
    from benchmark.nograph_baseline.data import iso_now

    return iso_now()


def run_directory(output_root: Path, run_id: str, run_type: str = "run") -> RunDirectory:
    validate_run_id(run_id)
    return RunDirectory(Path(output_root), run_id, run_type)


def runtime_source_paths(repo_root: Path) -> List[str]:
    """Return repo-relative paths of the execution source actually used.

    The scope is every imported ``benchmark`` runtime module (excluding tests
    and caches), the full new package (including entry points a worker does not
    import), ``benchmark/__init__.py`` and the academic protocol file is handled
    separately.  Unrelated research records never enter the scope.
    """
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
            relative = resolved.relative_to(repo_root)
        except ValueError:
            continue
        posix = relative.as_posix()
        if not posix.startswith("benchmark/"):
            continue
        found.add(posix)
    package_prefix = "benchmark/graph_value_skeleton/"
    for path in sorted((repo_root / "benchmark" / "graph_value_skeleton").glob("*.py")):
        found.add(package_prefix + path.name)
    if (repo_root / "benchmark/__init__.py").is_file():
        found.add("benchmark/__init__.py")
    # Tracked deletions inside the new package are part of the scoped difference.
    deleted, deleted_error = nb_artifacts.git_command(
        repo_root, ["ls-files", "--deleted", "--", "benchmark/graph_value_skeleton"]
    )
    if deleted_error is None:
        for line in (deleted or "").splitlines():
            relative = line.strip()
            if (
                relative.endswith(".py")
                and "/tests/" not in f"/{relative}"
                and "__pycache__" not in relative
            ):
                found.add(relative)
    return sorted(found)


def _git_bytes(repo_root: Path, args: Sequence[str]) -> Tuple[Optional[bytes], Optional[str]]:
    return nb_artifacts.git_bytes(repo_root, args)


def _source_entry(
    repo_root: Path,
    relative: str,
    *,
    commit: Optional[str],
    porcelain_code: Optional[str],
    scoped_status_error: Optional[str],
) -> Dict[str, Any]:
    absolute = repo_root / relative
    entry: Dict[str, Any] = {
        "path": relative,
        "sha256": sha256_file(absolute) if absolute.is_file() else None,
        "git_status": "unknown",
        "git_reference": None,
        "content_saved": None,
        "patch_path": None,
        "unavailable_reason": None,
    }
    if scoped_status_error is not None:
        entry["unavailable_reason"] = scoped_status_error
        return entry
    if commit is None:
        entry["unavailable_reason"] = "Git commit identity is unavailable"
        return entry
    if porcelain_code is None:
        entry["git_status"] = "committed_clean"
    elif porcelain_code == "??":
        entry["git_status"] = "untracked"
        # Untracked content has no committed base to locate; it is copied whole
        # by the caller rather than looked up in the commit.
        return entry
    else:
        entry["git_status"] = "modified"
    committed, show_error = _git_bytes(repo_root, ["show", f"{commit}:{relative}"])
    if show_error is not None:
        entry["git_status"] = "unknown"
        entry["unavailable_reason"] = show_error
        return entry
    entry["git_reference"] = {
        "commit": commit,
        "path": relative,
        "sha256": nb_artifacts.sha256_bytes(committed or b""),
    }
    if (
        entry["git_status"] == "committed_clean"
        and entry["git_reference"]["sha256"] != entry["sha256"]
    ):
        entry["git_status"] = "modified"
        entry["unavailable_reason"] = (
            "working-tree bytes differ from the recorded commit despite a clean "
            "Git status"
        )
    return entry


def _reconstruct_from_patch(
    repo_root: Path, commit: str, patch_text: str, paths: Sequence[str]
) -> Dict[str, Optional[str]]:
    """Prove that a patch reconstructs the executing content from the commit."""
    if not patch_text.strip() or not paths:
        return {}
    with tempfile.TemporaryDirectory(prefix="gvs-patch-check-") as temporary:
        root = Path(temporary)
        for relative in paths:
            base, error = _git_bytes(repo_root, ["show", f"{commit}:{relative}"])
            if error is not None:
                continue
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base or b"")
        patch_file = root / ".check.patch"
        patch_file.write_text(patch_text, encoding="utf-8", newline="\n")
        applied = subprocess.run(
            ["git", "-c", "core.autocrlf=false", "apply", "--unsafe-paths", str(patch_file)],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if applied.returncode != 0:
            return {}
        return {
            relative: (
                sha256_file(root / relative) if (root / relative).exists() else None
            )
            for relative in paths
        }


def capture_source(
    run: RunDirectory,
    repo_root: Path,
    *,
    protocol_path: Optional[Path] = None,
    runtime_paths: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Record scoped execution source and recoverable dirty content."""
    repo_root = Path(repo_root)
    runtime = list(runtime_paths) if runtime_paths is not None else runtime_source_paths(repo_root)
    commit_text, commit_error = nb_artifacts.git_command(repo_root, ["rev-parse", "HEAD"])
    commit = commit_text.strip() if commit_text else None
    whole_status, whole_error = nb_artifacts.git_command(repo_root, ["status", "--porcelain"])
    status_map, scoped_error = nb_artifacts.scoped_git_status(repo_root, runtime)
    errors: Dict[str, str] = {}
    if commit_error:
        errors["commit"] = commit_error
    if whole_error:
        errors["status"] = whole_error
    if scoped_error:
        errors["scoped_status"] = scoped_error
    files: Dict[str, Dict[str, Any]] = {}
    candidates: List[str] = []
    for relative in runtime:
        absolute = repo_root / relative
        code = (status_map or {}).get(relative)
        if not absolute.is_file() and code is None:
            continue
        entry = _source_entry(
            repo_root,
            relative,
            commit=commit,
            porcelain_code=code,
            scoped_status_error=scoped_error,
        )
        files[relative] = entry
        if entry["git_status"] == "committed_clean":
            continue
        if entry["git_status"] == "modified":
            candidates.append(relative)
        elif absolute.is_file():
            saved = (Path("code-untracked") / relative).as_posix()
            run.copy_file(absolute, saved)
            entry["content_saved"] = saved
    retained_patches: List[str] = []
    patch_unusable: List[str] = []
    unrecoverable: List[str] = []
    for relative in candidates:
        entry = files[relative]
        expected = entry["sha256"]
        patch_text, patch_error = nb_artifacts.git_command(
            repo_root, ["diff", "--binary", "HEAD", "--", relative]
        )
        if patch_error is not None:
            errors[f"patch:{relative}"] = patch_error
        elif (patch_text or "").strip():
            if commit is not None:
                proof = _reconstruct_from_patch(
                    repo_root, commit, patch_text or "", [relative]
                )
                if proof.get(relative, "<missing>") == expected:
                    retained_patches.append(patch_text or "")
                    entry["patch_path"] = "git-diff.patch"
                    continue
        absolute = repo_root / relative
        if absolute.is_file():
            saved = (Path("code-untracked") / relative).as_posix()
            run.copy_file(absolute, saved)
            entry["content_saved"] = saved
            entry["unavailable_reason"] = (
                entry["unavailable_reason"]
                or "no reconstructable patch; executing content saved under code-untracked"
            )
        else:
            unrecoverable.append(relative)
            entry["unavailable_reason"] = (
                entry["unavailable_reason"]
                or "executing deletion cannot be captured without an applicable patch"
            )
        patch_unusable.append(relative)
    patch = "".join(retained_patches)
    run.write_text("git-diff.patch", patch)
    protocol_file = Path(protocol_path) if protocol_path is not None else protocol.PROTOCOL_PATH
    try:
        protocol_relative = protocol_file.resolve().relative_to(repo_root.resolve()).as_posix()
    except (OSError, ValueError):
        protocol_relative = None
    protocol_entry: Optional[Dict[str, Any]]
    if protocol_relative is not None:
        protocol_entry = files.get(protocol_relative)
        if protocol_entry is None:
            protocol_entry = _source_entry(
                repo_root,
                protocol_relative,
                commit=commit,
                porcelain_code=(status_map or {}).get(protocol_relative),
                scoped_status_error=scoped_error,
            )
        if protocol_entry.get("git_status") in ("modified", "untracked", "unknown") and protocol_file.is_file():
            # The executing protocol content is not locatable by commit alone;
            # retain it so the scientific/policy content identity survives.
            run.copy_file(protocol_file, "protocol.md")
            protocol_entry["content_saved"] = "protocol.md"
    else:
        protocol_entry = {
            "path": str(protocol_file),
            "sha256": sha256_file(protocol_file) if protocol_file.is_file() else None,
            "git_status": "unknown",
            "git_reference": None,
            "content_saved": (
                "protocol.md" if protocol_file.is_file() else None
            ),
            "patch_path": None,
            "unavailable_reason": "protocol path is outside the Git working tree",
        }
        if protocol_file.is_file():
            run.copy_file(protocol_file, "protocol.md")
    status_text, status_error = nb_artifacts.git_command(repo_root, ["status", "--short"])
    run.write_text(
        "git-commit.txt", (commit + "\n") if commit else "UNAVAILABLE\n"
    )
    run.write_text(
        "git-status.txt", status_text if status_text is not None else "UNAVAILABLE\n"
    )
    if status_error:
        errors["git_status_text"] = status_error
    record = {
        "policy": protocol.RECORDS_POLICY,
        "generated": now(),
        "runtime_scope": runtime,
        "commit": commit,
        "identity_available": commit is not None,
        "whole_repository_dirty": (
            bool(whole_status.strip()) if whole_status is not None else None
        ),
        "scoped_dirty": any(
            entry["git_status"] in ("modified", "untracked") for entry in files.values()
        ),
        "files": files,
        "protocol": protocol_entry,
        "patch_path": "git-diff.patch",
        "patch_bytes": len(patch.encode("utf-8")),
        "patch_unusable_paths": sorted(patch_unusable),
        "unrecoverable_paths": sorted(unrecoverable),
        "errors": errors,
        "scope_note": (
            "only execution-relevant benchmark runtime modules and the academic "
            "protocol are captured; unrelated research records, tests and caches "
            "are outside the scope"
        ),
    }
    if protocol_file.is_file() and protocol_entry.get("content_saved") == "protocol.md":
        run.copy_file(protocol_file, "protocol.md")
    run.write_json("source.json", record)
    if any(entry["content_saved"] for entry in files.values()):
        run.write_json(
            "code-untracked/manifest.json",
            {
                "tracked_by_git": False,
                "files": {
                    relative: entry["sha256"]
                    for relative, entry in files.items()
                    if entry["content_saved"]
                },
            },
        )
    return record


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


@functools.lru_cache(maxsize=1)
def _numpy_blas_config_cached() -> Tuple[Optional[str], Optional[str]]:
    import warnings

    import numpy

    buffer = io.StringIO()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with contextlib_redirect(buffer):
                numpy.show_config()
    except Exception as exc:  # pragma: no cover - platform dependent
        return None, f"{type(exc).__name__}: {exc}"
    return buffer.getvalue(), None


class contextlib_redirect:
    """Small stdout/stderr redirect used only for ``numpy.show_config``."""

    def __init__(self, buffer: io.StringIO) -> None:
        import contextlib

        self._contexts = (
            contextlib.redirect_stdout(buffer),
            contextlib.redirect_stderr(io.StringIO()),
        )

    def __enter__(self) -> None:
        for context in self._contexts:
            context.__enter__()

    def __exit__(self, *exc_info: Any) -> None:
        for context in reversed(self._contexts):
            context.__exit__(*exc_info)


def _optional_imports() -> Dict[str, Any]:
    """Record graph-extension availability without importing or using them."""
    import importlib.util

    available: Dict[str, Any] = {}
    for name in ("torch_geometric", "dgl", "torch_scatter", "torch_sparse"):
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError):
            spec = None
        available[name] = {
            "available": spec is not None,
            "imported_in_this_process": name in sys.modules,
            "used_by_this_entry": False,
        }
    return available


def capture_environment(repo_root: Path) -> Dict[str, Any]:
    """Capture interpreter, package, CPU/OS and thread determinism facts."""
    import numpy
    import pandas
    import pyarrow
    import torch

    freeze, freeze_error = _pip_freeze_cached()
    blas, blas_error = _numpy_blas_config_cached()
    try:
        interop_threads: Any = torch.get_num_interop_threads()
    except RuntimeError:  # pragma: no cover - already parallelized
        interop_threads = None
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
            "pyarrow": pyarrow.__version__,
            "torch": torch.__version__,
        },
        "torch": {
            "version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "cuda_available": bool(torch.cuda.is_available()),
            "device_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
            "intra_op_threads": int(torch.get_num_threads()),
            "inter_op_threads": interop_threads,
            "deterministic_algorithms_enabled": bool(
                torch.are_deterministic_algorithms_enabled()
            ),
            "deterministic_algorithms_warn_only": bool(
                torch.is_deterministic_algorithms_warn_only_enabled()
            ),
        },
        "graph_extensions": _optional_imports(),
        "gpu_available": bool(torch.cuda.is_available()),
        "pip_freeze": freeze,
        "pip_freeze_error": freeze_error,
        "numpy_blas_config": blas,
        "numpy_blas_config_error": blas_error,
        "thread_environment": {
            name: os.environ.get(name)
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS",
            )
        },
        "repo_root": str(repo_root),
    }


def write_environment_snapshot(run: RunDirectory, environment: Mapping[str, Any]) -> None:
    freeze = environment.get("pip_freeze")
    run.write_text(
        "environment.txt",
        str(freeze)
        if freeze is not None
        else f"pip freeze unavailable: {environment.get('pip_freeze_error')}\n",
    )


def checker_source_identity(
    repo_root: Path, *, patch_limit: int = SOURCE_PATCH_LIMIT
) -> Dict[str, Any]:
    """Return the honest checker source identity embedded in a check report."""
    repo_root = Path(repo_root)
    commit_text, commit_error = nb_artifacts.git_command(repo_root, ["rev-parse", "HEAD"])
    commit = commit_text.strip() if commit_text else None
    whole_status, status_error = nb_artifacts.git_command(repo_root, ["status", "--porcelain"])
    runtime = runtime_source_paths(repo_root)
    status_map, scoped_error = nb_artifacts.scoped_git_status(repo_root, runtime)
    errors: Dict[str, str] = {}
    if commit_error:
        errors["commit"] = commit_error
    if status_error:
        errors["status"] = status_error
    if scoped_error:
        errors["scoped_status"] = scoped_error
    files: Dict[str, str] = {}
    dirty_paths: List[str] = []
    untracked_paths: List[str] = []
    for relative in runtime:
        absolute = repo_root / relative
        if not absolute.is_file():
            continue
        files[relative] = sha256_file(absolute)
        code = (status_map or {}).get(relative)
        if code == "??":
            untracked_paths.append(relative)
        elif code is not None:
            dirty_paths.append(relative)
    patch = ""
    if dirty_paths:
        patch_text, patch_error = nb_artifacts.git_command(
            repo_root, ["diff", "HEAD", "--", *dirty_paths]
        )
        if patch_error:
            errors["scoped_patch"] = patch_error
        patch = patch_text or ""
    patch_bytes = len(patch.encode("utf-8"))
    included = bool(patch) and patch_bytes <= patch_limit
    return {
        "policy": protocol.RECORDS_POLICY,
        "commit": commit,
        "identity_available": commit is not None,
        "whole_repository_dirty": (
            bool(whole_status.strip()) if whole_status is not None else None
        ),
        "scoped_state_available": scoped_error is None,
        "scoped_dirty": (
            bool(dirty_paths or untracked_paths) if scoped_error is None else None
        ),
        "files": files,
        "scoped_files": (
            sorted({*dirty_paths, *untracked_paths}) if scoped_error is None else None
        ),
        "patch_eligible_files": dirty_paths if scoped_error is None else None,
        "untracked_files": untracked_paths if scoped_error is None else None,
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


def verify_captured_source(
    source: Mapping[str, Any], repo_root: Path
) -> List[str]:
    """Recheck every captured execution-source and protocol identity.

    The startup snapshot in ``source.json`` names the execution-relevant runtime
    files and the scientific protocol.  Rehashing them before success detects a
    mid-run edit or removal instead of reporting success under stale provenance.
    Unrelated research files are outside this captured scope and are never
    checked here.
    """
    mismatches: List[str] = []
    repo_root = Path(repo_root)
    files = source.get("files") if isinstance(source, Mapping) else None
    if isinstance(files, Mapping):
        for relative, entry in files.items():
            if not isinstance(entry, Mapping):
                continue
            expected = entry.get("sha256")
            if not expected:
                continue
            path = Path(repo_root) / relative
            if not path.is_file():
                mismatches.append(f"runtime source disappeared: {relative}")
                continue
            actual = sha256_file(path)
            if actual != expected:
                mismatches.append(
                    f"runtime source changed: {relative} ({expected} -> {actual})"
                )
    protocol_entry = source.get("protocol") if isinstance(source, Mapping) else None
    if isinstance(protocol_entry, Mapping):
        expected = protocol_entry.get("sha256")
        recorded_path = protocol_entry.get("path")
        if expected is None:
            mismatches.append("captured protocol identity is unavailable")
        elif not recorded_path:
            mismatches.append("captured protocol path is unavailable")
        else:
            candidate = Path(recorded_path)
            path = candidate if candidate.is_absolute() else repo_root / candidate
            if not path.is_file():
                mismatches.append(f"protocol source disappeared: {recorded_path}")
            else:
                actual = sha256_file(path)
                if actual != expected:
                    mismatches.append(
                        f"protocol source changed: {recorded_path} "
                        f"({expected} -> {actual})"
                    )
    else:
        mismatches.append("captured protocol entry is unavailable")
    return mismatches


def measure_peak_rss() -> Dict[str, Any]:
    """Return normalized process peak RSS with native unit, method and scope."""
    if platform.system() == "Windows":
        return nb_artifacts.windows_peak_rss()
    try:
        import resource
    except ImportError:  # pragma: no cover - non-POSIX
        return {
            "bytes": None,
            "native_value": None,
            "native_unit": None,
            "method": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
            "scope": "process",
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
            "scope": "process",
            "status": "unsupported_platform",
            "reason": f"peak RSS unit for {system} is not defined",
        }
    return {
        "bytes": native * factor,
        "native_value": native,
        "native_unit": unit,
        "method": "resource.getrusage(RUSAGE_SELF).ru_maxrss",
        "scope": "worker process lifetime",
        "status": "ok",
    }




def source_manifest(
    *,
    demand_path: Path,
    demand_sha256: str,
    protocol_path: Path,
    protocol_sha256: str,
    graph_path: Optional[Path],
    graph_sha256: Optional[str],
) -> Dict[str, Any]:
    def entry(path: Optional[Path], digest: Optional[str]) -> Dict[str, Any]:
        if path is None:
            return {"path": None, "sha256": None, "verified": False, "reason": "not supplied"}
        exists = Path(path).is_file()
        return {
            "path": str(path),
            "sha256": digest if exists else None,
            "verified": bool(exists),
            "reason": (
                None
                if exists
                else "in-memory fixture placeholder; no source file to re-hash"
            ),
        }

    sources: Dict[str, Any] = {
        "demand": entry(demand_path, demand_sha256),
        "protocol": entry(protocol_path, protocol_sha256),
    }
    if graph_path is not None:
        sources["graph"] = entry(graph_path, graph_sha256)
    return {
        "generated": now(),
        "algorithm": "sha256",
        "sources": sources,
    }


def verify_source_hashes(manifest: Mapping[str, Any]) -> List[str]:
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
