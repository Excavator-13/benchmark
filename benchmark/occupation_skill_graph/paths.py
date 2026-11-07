"""Output-root and report-path safety rules.

Development evidence may be written only into the repository's ignored
``scratch/`` tree or into system temporary storage.  Project source, research,
dataset and historical paths are rejected even when the checkout itself lives
under a system temporary root.  Research output is a fresh ``research/runs/<id>``
directory and cannot be redirected through a CLI override.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from . import protocol

__all__ = [
    "PathError",
    "is_within",
    "system_temp_root",
    "system_temp_roots",
    "development_root",
    "research_root",
    "resolve_output_root",
    "resolve_report_path",
]


class PathError(ValueError):
    """Raised when an output or report path violates the evidence boundary."""


def is_within(child: Path, parent: Path) -> bool:
    """Return True when ``child`` resolves inside ``parent`` (alias aware)."""
    try:
        resolved_child = Path(child).expanduser().resolve()
        resolved_parent = Path(parent).expanduser().resolve()
    except OSError:  # pragma: no cover - unreadable path component
        return False
    return resolved_child == resolved_parent or resolved_parent in resolved_child.parents


def system_temp_roots() -> tuple[Path, ...]:
    """Return the resolved system temporary roots accepted for development output."""
    roots = {Path(tempfile.gettempdir()).resolve()}
    for candidate in ("/tmp", "/var/tmp", "/private/tmp", "/private/var/tmp"):
        try:
            path = Path(candidate).resolve()
        except OSError:  # pragma: no cover - unusual platform
            continue
        if path.is_dir():
            roots.add(path)
    return tuple(sorted(roots))


def system_temp_root() -> Path:
    """Return the primary resolved system temporary directory."""
    return Path(tempfile.gettempdir()).resolve()


def development_root(repo_root: Path) -> Path:
    """Return the default ignored development root for a checkout."""
    return (Path(repo_root) / "scratch" / "occupation-skill-graph").resolve()


def research_root(repo_root: Path) -> Path:
    """Return the formal research run namespace for a checkout."""
    return (Path(repo_root) / "research" / "runs").resolve()


def resolve_output_root(
    *,
    purpose: str,
    output_root: Optional[Path],
    repo_root: Path,
) -> Path:
    """Resolve and validate the output root for one explicit purpose."""
    repo = Path(repo_root).expanduser().resolve()
    if purpose == protocol.RESEARCH_PURPOSE:
        if output_root is not None:
            raise PathError(
                "research purpose always writes a fresh research/runs/<run-id> "
                "directory; --output-root is development-only"
            )
        return research_root(repo)
    if purpose != protocol.DEVELOPMENT_PURPOSE:
        raise PathError(
            f"unsupported purpose {purpose!r}; supported: {list(protocol.PURPOSES)}"
        )
    candidate = (
        Path(output_root).expanduser()
        if output_root is not None
        else development_root(repo)
    )
    resolved = candidate.resolve()
    # Protected destinations must be checked independently of the scratch
    # alias, including protected trees which themselves point outside the repo.
    for name in ("research", "dataset", "benchmark", "source", "history"):
        if is_within(resolved, repo / name):
            raise PathError(f"development output {resolved} resolves inside protected {name}")
    scratch = (repo / "scratch").resolve()
    if is_within(resolved, repo):
        # Do not let resolving scratch redefine which project subtree is safe.
        if not resolved.is_relative_to(repo / "scratch"):
            raise PathError(
                f"development output {resolved} is inside the project checkout "
                "but outside the ignored scratch tree; project source, research, "
                "dataset and historical paths are refused"
            )
        return resolved
    for temporary in system_temp_roots():
        if is_within(resolved, temporary):
            return resolved
    raise PathError(
        f"development output {resolved} must resolve inside the ignored "
        f"scratch tree {scratch} or a system temporary directory "
        f"{list(system_temp_roots())}"
    )


def resolve_report_path(
    report_path: Path, *, input_directory: Optional[Path] = None
) -> Path:
    """Resolve an external report path and reject input-internal destinations."""
    destination = Path(report_path).expanduser()
    resolved = destination.resolve()
    if input_directory is not None and is_within(resolved, input_directory):
        raise PathError(
            f"report path {resolved} resolves inside the checked input "
            f"{Path(input_directory).resolve()}; checks write only external reports"
        )
    if resolved.exists():
        raise PathError(
            f"report destination already exists and will not be replaced: {resolved}"
        )
    parent = resolved.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PathError(
                f"cannot create report parent directory {parent}: {exc}"
            ) from exc
    if not os.access(parent, os.W_OK):
        raise PathError(f"report parent directory is not writable: {parent}")
    return resolved
