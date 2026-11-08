"""Format-v2 run directories, provenance capture and readable entries.

Every execution reserves a fresh non-overwriting directory.  Development output
lives under the ignored ``scratch/`` root and is rejected, after resolving path
aliases, when it would land inside ``research/runs/``.  Formal output keeps the
existing generic Git ignore policy: only ``summary.md``, ``provenance.json``,
``command.json`` and ``report.json`` are versioned readable entries, so this
module never adds a per-run ignore exception.

Saved-only checks import this module; nothing here imports torch or pandas at
module import time.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from benchmark.nograph_baseline import artifacts as nb_artifacts
from benchmark.nograph_baseline import protocol as p01
from benchmark.nograph_baseline.data import iso_now, sha256_file

from . import protocol

MODULE_RELATIVE = "benchmark/multivariate_time_series"


class ArtifactError(RuntimeError):
    """Raised when output identity or evidence cannot be established."""


RunExistsError = nb_artifacts.RunExistsError
RunDirectory = nb_artifacts.RunDirectory


def repo_root() -> Path:
    return p01.REPO_ROOT


def formal_root(repo: Optional[Path] = None) -> Path:
    return Path(repo or repo_root()) / "research" / "runs"


def development_root(repo: Optional[Path] = None) -> Path:
    return Path(repo or repo_root()) / "scratch" / "effective-temporal"


def blocks_root(purpose: str, repo: Optional[Path] = None) -> Path:
    root = formal_root(repo) if purpose == "formal" else development_root(repo)
    return root / "blocks"


def default_root(purpose: str, repo: Optional[Path] = None) -> Path:
    protocol.validate_purpose(purpose)
    return formal_root(repo) if purpose == "formal" else development_root(repo)


def is_within(child: Path, parent: Path) -> bool:
    return nb_artifacts.is_within(child, parent)


def check_development_namespace(purpose: str, target: Path, repo: Optional[Path] = None) -> Path:
    """Reject a development output that resolves inside ``research/runs/``."""
    protocol.validate_purpose(purpose)
    resolved = Path(target).expanduser().resolve()
    if purpose == "development" and is_within(resolved, formal_root(repo)):
        raise ArtifactError(
            "development output "
            f"{target} resolves inside the formal namespace {formal_root(repo)}; "
            "development evidence must stay under an ignored scratch root"
        )
    return resolved


def validate_run_id(run_id: str) -> str:
    try:
        return nb_artifacts.validate_run_id(run_id)
    except nb_artifacts.ArtifactError as exc:
        raise ArtifactError(str(exc)) from exc


def reserve_run(
    run_id: str,
    *,
    purpose: str,
    operation: str,
    output_root: Optional[Path] = None,
    repo: Optional[Path] = None,
) -> nb_artifacts.RunDirectory:
    """Reserve a fresh exclusive run directory for one execution."""
    protocol.validate_purpose(purpose)
    validate_run_id(run_id)
    root = Path(output_root) if output_root is not None else default_root(purpose, repo)
    target = Path(root) / run_id
    check_development_namespace(purpose, target, repo)
    run = nb_artifacts.RunDirectory(root, run_id, run_type=f"effective-temporal-{operation}")
    run.reserve()
    run.write_json(
        "status.json",
        {
            "run_id": run_id,
            "run_type": f"effective-temporal-{operation}",
            "state": "running",
            "purpose": purpose,
            "operation": operation,
            "updated": iso_now(),
        },
    )
    from . import resources
    resources.register_stage_output(run)
    return run


def reserve_block(
    block_id: str,
    *,
    purpose: str,
    operation: str,
    output_root: Optional[Path] = None,
    repo: Optional[Path] = None,
) -> nb_artifacts.RunDirectory:
    """Reserve a fresh exclusive block directory (selection/diagnostics)."""
    protocol.validate_purpose(purpose)
    validate_run_id(block_id)
    root = (
        Path(output_root)
        if output_root is not None
        else blocks_root(purpose, repo)
    )
    target = Path(root) / block_id
    check_development_namespace(purpose, target, repo)
    run = nb_artifacts.RunDirectory(root, block_id, run_type=f"effective-temporal-block-{operation}")
    run.reserve()
    run.write_json(
        "status.json",
        {
            "block_id": block_id,
            "run_type": f"effective-temporal-block-{operation}",
            "state": "running",
            "purpose": purpose,
            "operation": operation,
            "updated": iso_now(),
        },
    )
    from . import resources
    resources.register_stage_output(run)
    return run


def set_status(run: nb_artifacts.RunDirectory, state: str, **extra: Any) -> Dict[str, Any]:
    return run.set_status(state, **extra)


def runtime_source_paths(repo: Optional[Path] = None) -> List[str]:
    """Return the repository source files actually used by this entry.

    The scope is this entry's package, the reused P01 helper modules that were
    imported at runtime, the public module and both protocol documents.  Tests,
    caches and unrelated graph/baseline code are excluded.
    """
    root = Path(repo or repo_root()).resolve()
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
            relative = resolved.relative_to(root).as_posix()
        except ValueError:
            continue
        if relative == "benchmark/__init__.py":
            found.add(relative)
        elif relative.startswith(MODULE_RELATIVE + "/"):
            found.add(relative)
        elif relative.startswith("benchmark/nograph_baseline/"):
            found.add(relative)
    for name in sorted(
        path.name
        for path in (root / MODULE_RELATIVE).glob("*.py")
        if path.is_file()
    ):
        found.add(f"{MODULE_RELATIVE}/{name}")
    for name in sorted(
        path.name
        for path in (root / MODULE_RELATIVE / "temporal").glob("*.py")
        if path.is_file()
    ):
        found.add(f"{MODULE_RELATIVE}/temporal/{name}")
    for name in ("data.py", "protocol.py", "metrics.py", "coverage.py", "baselines.py", "artifacts.py"):
        relative = f"benchmark/nograph_baseline/{name}"
        if (root / relative).is_file():
            found.add(relative)
    deleted, deleted_error = nb_artifacts.git_command(
        root, ["ls-files", "--deleted", "--", MODULE_RELATIVE]
    )
    if deleted_error is None:
        for line in (deleted or "").splitlines():
            relative = line.strip()
            if relative.endswith(".py") and "/tests/" not in f"/{relative}":
                found.add(relative)
    return sorted(found)


def capture_source(run: nb_artifacts.RunDirectory, repo: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(repo or repo_root())
    return nb_artifacts.capture_source(
        run,
        root,
        protocol_path=protocol.P02_PROTOCOL_PATH,
        runtime_paths=runtime_source_paths(root),
    )


def capture_environment() -> Dict[str, Any]:
    """Capture interpreter, packages, CPU/thread settings and determinism flags."""
    import pandas
    import pyarrow

    packages: Dict[str, Optional[str]] = {
        "numpy": np.__version__,
        "pandas": pandas.__version__,
        "pyarrow": pyarrow.__version__,
    }
    try:
        import torch

        packages["torch"] = torch.__version__
        determinism = {
            "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
            "num_threads": int(torch.get_num_threads()),
            "default_dtype": str(torch.get_default_dtype()),
        }
    except ImportError:  # pragma: no cover - torch is required for fitting
        packages["torch"] = None
        determinism = {"deterministic_algorithms": None, "num_threads": None}
    try:
        import psutil

        packages["psutil"] = psutil.__version__
    except ImportError:  # pragma: no cover - optional for saved-only checks
        packages["psutil"] = None
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
        "packages": packages,
        "thread_environment": thread_variables,
        "determinism": determinism,
        "device": "cpu",
        "threads": 1,
        "repo_root": str(repo_root()),
    }


def write_environment(run: nb_artifacts.RunDirectory) -> Dict[str, Any]:
    environment = capture_environment()
    run.write_json("environment.json", environment)
    return environment


def write_command(run: nb_artifacts.RunDirectory, argv: Sequence[str], **extra: Any) -> Dict[str, Any]:
    payload = {
        "argv": [str(item) for item in argv],
        "cwd": str(Path.cwd()),
        "module": "benchmark.multivariate_time_series.effective_temporal_training",
        "python": sys.executable,
        "created": iso_now(),
    }
    payload.update(extra)
    run.write_json("command.json", payload)
    return payload


def write_summary(run: nb_artifacts.RunDirectory, text: str) -> Path:
    return run.write_text("summary.md", text)


def write_array_manifest(
    run: nb_artifacts.RunDirectory, relative_paths: Iterable[str]
) -> Dict[str, Any]:
    """Record the arrays that an independent recomputation consumes."""
    entries: Dict[str, Any] = {}
    for relative in relative_paths:
        path = run.path / relative
        if path.is_file():
            entries[relative] = {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
    payload = {
        "format_version": protocol.ARTIFACT_FORMAT_VERSION,
        "generated": iso_now(),
        "algorithm": protocol.HASH_ALGORITHM,
        "arrays": entries,
        "required_for_recompute": [
            relative
            for relative in protocol.RECOMPUTE_ARRAYS
            if (run.path / relative).is_file()
        ],
    }
    run.write_json("arrays-sha256.json", payload)
    return payload


def provenance_payload(
    *,
    purpose: str,
    operation: str,
    config: Mapping[str, Any],
    roles: Mapping[str, Any],
    data_identity: Optional[Mapping[str, Any]],
    source_record: Mapping[str, Any],
    environment: Mapping[str, Any],
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    protocol_sha = protocol.protocol_content_sha256()
    payload: Dict[str, Any] = {
        "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
        "scientific_version": protocol.SCIENTIFIC_VERSION,
        "generated": iso_now(),
        "purpose": purpose,
        "operation": operation,
        "protocol": {
            "path": str(protocol.P02_PROTOCOL_PATH),
            "sha256": protocol_sha,
            "version": protocol.SCIENTIFIC_VERSION,
        },
        "config": dict(config),
        "roles": dict(roles),
        "data": dict(data_identity) if data_identity is not None else None,
        "source": dict(source_record),
        "environment": dict(environment),
    }
    if extra:
        payload.update(extra)
    return payload


def safe_json(payload: Any) -> Any:
    """Convert NumPy scalars/arrays into JSON-serialisable values."""
    if isinstance(payload, Mapping):
        return {str(key): safe_json(value) for key, value in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [safe_json(value) for value in payload]
    if isinstance(payload, np.ndarray):
        return safe_json(payload.tolist())
    if isinstance(payload, (np.floating,)):
        return float(payload)
    if isinstance(payload, (np.integer,)):
        return int(payload)
    if isinstance(payload, (np.bool_,)):
        return bool(payload)
    return payload


def write_json(run: nb_artifacts.RunDirectory, relative: str, payload: Any) -> Path:
    return run.write_json(relative, safe_json(payload))


def write_json_atomic(path: Path, payload: Any) -> Path:
    """Atomically replace one JSON document (status updates, block records)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(safe_json(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return path


def read_json(path: Path) -> Any:
    if not Path(path).exists():
        raise ArtifactError(f"required artifact is missing: {path}")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def readable_entry_text(summary: str) -> str:
    return summary if summary.endswith("\n") else summary + "\n"
