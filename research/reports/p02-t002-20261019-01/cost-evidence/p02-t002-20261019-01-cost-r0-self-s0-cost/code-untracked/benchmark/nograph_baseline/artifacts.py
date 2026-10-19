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

#: Explicit execution purposes.  Formal output is scientific evidence material;
#: development output is disposable and must stay outside the formal namespace.
PURPOSES = ("formal", "development")

#: A scoped execution patch larger than this is summarized by byte count in a
#: check report instead of being embedded verbatim.
SOURCE_PATCH_LIMIT = 20000


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
    """Return the default formal runs root for a repository root."""
    if repo_root is None:
        return protocol.RUNS_DIR
    return Path(repo_root) / "research" / "runs"


def formal_runs_root(repo_root: Path) -> Path:
    """Return the formal experiment namespace for a repository root."""
    return Path(repo_root) / "research" / "runs"


def development_runs_root(repo_root: Path) -> Path:
    """Return the ignored development output root for a repository root."""
    return Path(repo_root) / "scratch" / "nograph-baseline"


def default_runs_root(repo_root: Path, purpose: str = "formal") -> Path:
    """Return the default output root for one explicit execution purpose."""
    if purpose == "development":
        return development_runs_root(repo_root)
    return formal_runs_root(repo_root)


def is_within(child: Path, parent: Path) -> bool:
    """Return True when ``child`` resolves inside ``parent`` (alias aware)."""
    try:
        resolved_child = Path(child).expanduser().resolve()
        resolved_parent = Path(parent).expanduser().resolve()
    except OSError:  # pragma: no cover - unreadable path component
        return False
    return resolved_child == resolved_parent or resolved_parent in resolved_child.parents



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


def git_bytes(repo_root: Path, args: Sequence[str]) -> Tuple[Optional[bytes], Optional[str]]:
    """Run a git command for byte-exact content, returning ``(stdout, error)``."""
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            check=False,
        )
    except (OSError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if completed.returncode != 0:
        message = (
            completed.stderr.decode("utf-8", "replace").strip()
            or completed.stdout.decode("utf-8", "replace").strip()
        )
        return None, f"git {' '.join(args)} exited {completed.returncode}: {message}"
    return completed.stdout, None


def sha256_bytes(data: bytes) -> str:
    """Return the SHA256 hex digest of an in-memory byte string."""
    import hashlib

    return hashlib.sha256(data).hexdigest()


def capture_git(repo_root: Path) -> Dict[str, Any]:
    """Capture commit, whole-repository status and untracked file names."""
    commit, commit_error = git_command(repo_root, ["rev-parse", "HEAD"])
    status, status_error = git_command(repo_root, ["status", "--short"])
    untracked, untracked_error = git_command(
        repo_root, ["ls-files", "--others", "--exclude-standard"]
    )
    errors = {
        "commit": commit_error,
        "status": status_error,
        "untracked": untracked_error,
    }
    dirty = None
    if status is not None:
        dirty = bool(status.strip())
    return {
        "commit": commit.strip() if commit else None,
        "status": status,
        "untracked_files": [line for line in (untracked or "").splitlines() if line],
        "dirty": dirty,
        "errors": {key: value for key, value in errors.items() if value},
        "identity_available": commit is not None,
    }


def runtime_source_paths(repo_root: Path) -> List[str]:
    """Return repo-relative paths of the execution source actually used.

    The set is derived from the imported baseline runtime modules (plus the
    launcher entry points), so ``tests/``, caches and unrelated research
    records are never part of an execution-source snapshot.
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
        if posix != "benchmark/__init__.py" and not posix.startswith(
            "benchmark/nograph_baseline/"
        ):
            continue
        found.add(posix)
    # The isolated worker does not import the launcher it was started from, but
    # those files remain part of the reconstructable execution content.
    for name in ("__init__.py", "__main__.py", "_worker.py", "cli.py"):
        relative = f"benchmark/nograph_baseline/{name}"
        if (repo_root / relative).is_file():
            found.add(relative)
    if (repo_root / "benchmark/__init__.py").is_file():
        found.add("benchmark/__init__.py")
    # Tracked runtime deletions are part of the scoped execution difference even
    # though the file no longer exists to be imported.
    deleted, deleted_error = git_command(
        repo_root, ["ls-files", "--deleted", "--", "benchmark/nograph_baseline"]
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


def scoped_git_status(
    repo_root: Path, paths: Sequence[str]
) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """Return one porcelain status per scoped path, or an explicit error."""
    if not paths:
        return {}, None
    output, error = git_command(
        repo_root, ["status", "--porcelain", "--", *paths]
    )
    if error is not None:
        return None, error
    mapping: Dict[str, str] = {}
    for line in (output or "").splitlines():
        if len(line) < 4:
            continue
        mapping[line[3:]] = line[:2]
    return mapping, None


def _source_entry(
    repo_root: Path,
    recorded: str,
    *,
    commit: Optional[str],
    porcelain_code: Optional[str],
    git_error: Optional[str],
    content_saved: Optional[str] = None,
    outside_repository: bool = False,
    unavailable_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Describe one execution-source file without copying clean content."""
    absolute = Path(recorded) if outside_repository else repo_root / recorded
    entry: Dict[str, Any] = {
        "path": recorded,
        "sha256": sha256_file(absolute) if absolute.is_file() else None,
        "git_status": "unknown",
        "git_reference": None,
        "content_saved": content_saved,
        "patch_path": None,
        "unavailable_reason": unavailable_reason,
        "outside_repository": outside_repository,
    }
    if git_error is not None:
        entry["unavailable_reason"] = git_error
        return entry
    if outside_repository:
        entry["unavailable_reason"] = (
            entry["unavailable_reason"]
            or "path is outside the resolved Git working tree"
        )
        return entry
    if commit is None:
        entry["unavailable_reason"] = (
            entry["unavailable_reason"] or "Git commit identity is unavailable"
        )
        return entry
    if porcelain_code is None:
        entry["git_status"] = "committed_clean"
    elif porcelain_code == "??":
        entry["git_status"] = "untracked"
    elif porcelain_code.strip():
        entry["git_status"] = "modified"
    else:
        entry["git_status"] = "committed_clean"
    if entry["git_status"] == "untracked":
        return entry
    committed, show_error = git_bytes(
        repo_root, ["show", f"{commit}:{recorded}"]
    )
    if show_error is not None:
        entry["git_status"] = "unknown"
        entry["unavailable_reason"] = show_error
        return entry
    entry["git_reference"] = {
        "commit": commit,
        "path": recorded,
        "sha256": sha256_bytes(committed or b""),
    }
    if (
        entry["git_status"] == "committed_clean"
        and entry["git_reference"]["sha256"] != entry["sha256"]
    ):
        # Git reports the path clean yet the bytes differ: never claim reuse.
        entry["git_status"] = "modified"
        entry["unavailable_reason"] = (
            "working-tree bytes differ from the recorded commit despite a clean "
            "Git status"
        )
    return entry


def capture_source(
    run: RunDirectory,
    repo_root: Path,
    *,
    protocol_path: Optional[Path] = None,
    runtime_paths: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Record scoped execution-source provenance and recoverable dirty content.

    Clean committed files are located by fixed commit and repository-relative
    path instead of being copied.  Scoped tracked modifications are saved as one
    patch, necessary untracked runtime/protocol contents are copied, and an
    unavailable Git identity is reported explicitly with a content fallback.
    """
    repo_root = Path(repo_root)
    runtime = list(runtime_paths) if runtime_paths is not None else runtime_source_paths(
        repo_root
    )
    commit, commit_error = git_command(repo_root, ["rev-parse", "HEAD"])
    commit = commit.strip() if commit else None
    whole_status, status_error = git_command(repo_root, ["status", "--porcelain"])
    errors: Dict[str, str] = {}
    if commit_error:
        errors["commit"] = commit_error
    if status_error:
        errors["status"] = status_error
    protocol_file = Path(protocol_path) if protocol_path is not None else None
    protocol_relative: Optional[str] = None
    if protocol_file is not None:
        try:
            protocol_relative = (
                protocol_file.resolve().relative_to(repo_root.resolve()).as_posix()
            )
        except (OSError, ValueError):
            protocol_relative = None
        if protocol_relative is not None and protocol_relative not in runtime:
            runtime = sorted({*runtime, protocol_relative})
    status_map, scoped_status_error = scoped_git_status(repo_root, runtime)
    if scoped_status_error:
        errors["scoped_status"] = scoped_status_error

    def _reconstruct_from_patch(
        patch_text: str, paths: Sequence[str]
    ) -> Dict[str, Optional[str]]:
        """Reconstruct paths from the fixed commit base plus ``patch_text``.

        Returns ``path -> sha256`` (``None`` when the patch deletes the path)
        for the paths the patch actually reconstructs.  An empty mapping means
        the supplied patch cannot be trusted to recover anything: path text in
        diff output is not proof that the output is an applicable patch.
        """
        if commit is None or not patch_text.strip() or not paths:
            return {}
        with tempfile.TemporaryDirectory(prefix="nograph-patch-check-") as temporary:
            root = Path(temporary)
            for relative in paths:
                base, base_error = git_bytes(
                    repo_root, ["show", f"{commit}:{relative}"]
                )
                if base_error is not None:
                    continue
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(base or b"")
            patch_file = root / ".check.patch"
            patch_file.write_text(patch_text, encoding="utf-8")
            applied = subprocess.run(
                ["git", "apply", "--unsafe-paths", str(patch_file)],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )
            if applied.returncode != 0:
                return {}
            reconstructed: Dict[str, Optional[str]] = {}
            for relative in paths:
                target = root / relative
                reconstructed[relative] = (
                    sha256_file(target) if target.exists() else None
                )
            return reconstructed

    def _save_fallback(
        entry: Dict[str, Any], relative: str, absolute: Path
    ) -> None:
        """Preserve executing bytes when no reconstructable patch is available."""
        if absolute.is_file():
            saved_relative = (Path("code-untracked") / relative).as_posix()
            run.copy_file(absolute, saved_relative)
            entry["content_saved"] = saved_relative
            fallback = "executing content saved under code-untracked"
        else:
            fallback = (
                "the executing deletion cannot be captured without an applicable patch"
            )
        entry["unavailable_reason"] = entry["unavailable_reason"] or (
            f"no reconstructable scoped patch is available for this path; {fallback}"
        )

    files: Dict[str, Dict[str, Any]] = {}
    scoped_dirty = False
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
            git_error=scoped_status_error,
        )
        files[relative] = entry
        if entry["git_status"] == "committed_clean":
            continue
        scoped_dirty = True
        if entry["git_status"] == "modified":
            # A tracked modification or deletion must be recovered from the
            # saved patch or from saved content.
            candidates.append(relative)
        elif absolute.is_file():
            # Untracked, ignored or identity-less content: save it outright.
            saved_relative = (Path("code-untracked") / relative).as_posix()
            run.copy_file(absolute, saved_relative)
            entry["content_saved"] = saved_relative

    # The saved patch is the concatenation of the per-path patches that are
    # proven to reconstruct their executing content (or deletion state) from
    # the recorded base.  A failing driver on one path therefore cannot make
    # another path's diff disappear from the retained evidence.
    retained_patches: List[str] = []
    patch_unusable_paths: List[str] = []
    unrecoverable_paths: List[str] = []
    patch_errors: Dict[str, str] = {}
    for relative in candidates:
        entry = files[relative]
        expected = entry["sha256"]
        file_patch, file_patch_error = git_command(
            repo_root, ["diff", "--binary", "HEAD", "--", relative]
        )
        if file_patch_error is not None:
            patch_errors[relative] = file_patch_error
        elif (file_patch or "").strip():
            proof = _reconstruct_from_patch(file_patch or "", [relative])
            if proof.get(relative, "<missing>") == expected:
                retained_patches.append(file_patch or "")
                entry["patch_path"] = "git-diff.patch"
                continue
        _save_fallback(entry, relative, repo_root / relative)
        patch_unusable_paths.append(relative)
        if not entry["content_saved"]:
            unrecoverable_paths.append(relative)
    patch = "".join(retained_patches)
    if patch_errors:
        first_path = sorted(patch_errors)[0]
        errors["scoped_patch"] = (
            f"{len(patch_errors)} scoped path diff(s) failed; "
            f"first: {patch_errors[first_path]}"
        )

    protocol_entry: Optional[Dict[str, Any]] = None
    if protocol_file is not None:
        if protocol_relative is not None:
            protocol_entry = files.get(protocol_relative)
        if protocol_entry is None:
            protocol_entry = _source_entry(
                repo_root,
                protocol_relative
                if protocol_relative is not None
                else protocol_file.as_posix(),
                commit=commit,
                porcelain_code=None,
                git_error=None,
                content_saved="protocol.md" if protocol_file.is_file() else None,
                outside_repository=protocol_relative is None,
                unavailable_reason=(
                    None
                    if protocol_file.is_file()
                    else f"protocol file is missing: {protocol_file}"
                ),
            )

    if patch:
        run.write_text("git-diff.patch", patch)
    else:
        run.write_text("git-diff.patch", "")
    record = {
        "policy": "P01-records-v2",
        "generated": iso_now(),
        "runtime_scope": runtime,
        "commit": commit,
        "identity_available": commit is not None,
        "whole_repository_dirty": (
            bool(whole_status.strip()) if whole_status is not None else None
        ),
        "scoped_dirty": scoped_dirty,
        "files": files,
        "protocol": protocol_entry,
        "patch_path": "git-diff.patch",
        "patch_bytes": len(patch.encode("utf-8")),
        "patch_unusable_paths": sorted(patch_unusable_paths),
        "patch_errors": patch_errors,
        "unrecoverable_paths": sorted(unrecoverable_paths),
        "errors": errors,
    }
    run.write_json("code-source.json", record)
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


def checker_source_identity(
    repo_root: Path, *, patch_limit: int = SOURCE_PATCH_LIMIT
) -> Dict[str, Any]:
    """Return the honest checker source identity embedded in a check report."""
    repo_root = Path(repo_root)
    commit, commit_error = git_command(repo_root, ["rev-parse", "HEAD"])
    commit = commit.strip() if commit else None
    whole_status, status_error = git_command(repo_root, ["status", "--porcelain"])
    runtime = runtime_source_paths(repo_root)
    status_map, scoped_status_error = scoped_git_status(repo_root, runtime)
    errors: Dict[str, str] = {}
    if commit_error:
        errors["commit"] = commit_error
    if status_error:
        errors["status"] = status_error
    if scoped_status_error:
        errors["scoped_status"] = scoped_status_error
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
            # Git explicitly reports this used runtime file as not in the
            # recorded commit; it is part of the scoped source state even
            # though it is not patch-eligible.
            untracked_paths.append(relative)
        elif code is not None:
            dirty_paths.append(relative)
    patch = ""
    if dirty_paths:
        patch_text, patch_error = git_command(
            repo_root, ["diff", "HEAD", "--", *dirty_paths]
        )
        if patch_error:
            errors["scoped_patch"] = patch_error
        patch = patch_text or ""
    patch_bytes = len(patch.encode("utf-8"))
    included = bool(patch) and patch_bytes <= patch_limit
    state_available = scoped_status_error is None
    scoped_files = sorted({*dirty_paths, *untracked_paths})
    return {
        "policy": "P01-records-v2",
        "commit": commit,
        "identity_available": commit is not None,
        "whole_repository_dirty": (
            bool(whole_status.strip()) if whole_status is not None else None
        ),
        "scoped_state_available": state_available,
        "scoped_dirty": bool(scoped_files) if state_available else None,
        "files": files,
        "scoped_files": scoped_files if state_available else None,
        "patch_eligible_files": dirty_paths if state_available else None,
        "untracked_files": untracked_paths if state_available else None,
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
    """Persist the committed identity and whole-repository status text.

    The scoped execution patch is written by :func:`capture_source`; this helper
    deliberately does not copy a whole-repository diff.
    """
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
