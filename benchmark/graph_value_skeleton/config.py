"""Explicit execution axes, purpose-scoped output roots and run identity.

The public entry never selects a method by mutating a module global: the method,
model seed, shuffle seed (shuffled only) and purpose are resolved into one
immutable :class:`RunConfig`.  Development output can only land in the ignored
``scratch/graph-value-skeleton`` root or a validated temporary root; formal
output can only resolve to ``research/runs/<run-id>`` and is never executed by
implementation/verification checks.
"""

from __future__ import annotations

import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from benchmark.nograph_baseline import artifacts as nb_artifacts
from benchmark.nograph_baseline import protocol as p01

from . import protocol

__all__ = [
    "ConfigError",
    "RunConfig",
    "resolve_config",
    "resolve_output_root",
    "validate_run_destination",
    "development_roots",
    "protected_project_roots",
    "validate_implementation_root",
    "computational_identity",
]


class ConfigError(ValueError):
    """Raised when axes, purpose or destination violate the frozen contract."""


def development_roots(repo_root: Path) -> Sequence[Path]:
    """Return the allowed development parent roots (ignored scratch, temp)."""
    return (Path(repo_root) / "scratch", Path(tempfile.gettempdir()))


def protected_project_roots() -> Sequence[Path]:
    """Return authoritative project locations that no execution may write.

    These are anchored to the checked-out project, never to a user-supplied
    ``--repo-root`` override, so rebasing the "repository root" onto a research
    tree cannot turn that tree into an allowed scratch location.
    """
    root = protocol.REPO_ROOT
    return (
        root / "research",
        root / "experiments_archive",
        root / "dataset",
        root / "references",
        root / ".git",
        root / "benchmark",
    )


def validate_implementation_root(repo_root: Path) -> Path:
    """Reject an implementation-root override into a protected project tree."""
    resolved = Path(repo_root).expanduser().resolve()
    if not resolved.is_dir():
        raise ConfigError(f"implementation root is not an existing directory: {resolved}")
    for protected in protected_project_roots():
        if nb_artifacts.is_within(resolved, protected):
            raise ConfigError(
                f"implementation root {resolved} resolves inside the protected "
                f"location {Path(protected).resolve()}"
            )
    return resolved


def resolve_output_root(
    repo_root: Path,
    purpose: str,
    output_root: Optional[Path] = None,
) -> Path:
    """Resolve and validate the output root for one explicit purpose.

    Development output must resolve inside the repository's ignored ``scratch``
    tree or the system temporary directory; a symlink or ``..`` sequence that
    lands anywhere else (formal runs, research records, dataset, source tree) is
    rejected before any directory is created.  Formal output has no override and
    always resolves to ``research/runs``.
    """
    protocol.validate_purpose(purpose)
    repo_root = validate_implementation_root(Path(repo_root))
    if purpose == protocol.PURPOSE_FORMAL:
        if output_root is not None:
            raise ConfigError(
                "formal output has no root override; it always resolves to "
                f"{(repo_root / 'research' / 'runs').as_posix()}"
            )
        return repo_root / "research" / "runs"
    candidate = (
        Path(output_root)
        if output_root is not None
        else repo_root / "scratch" / "graph-value-skeleton"
    )
    resolved = candidate.expanduser().resolve()
    allowed = [Path(root).expanduser().resolve() for root in development_roots(repo_root)]
    if not any(nb_artifacts.is_within(resolved, root) for root in allowed):
        raise ConfigError(
            "development output must resolve inside the ignored scratch tree "
            f"({allowed[0]}) or the system temporary directory ({allowed[1]}); "
            f"got {candidate} -> {resolved}"
        )
    forbidden = [
        Path(repo_root) / "research",
        Path(repo_root) / "experiments_archive",
        Path(repo_root) / "dataset",
        Path(repo_root) / "references",
        Path(repo_root) / ".git",
        *protected_project_roots(),
    ]
    for path in forbidden:
        if nb_artifacts.is_within(resolved, path):
            raise ConfigError(
                f"development output may not resolve inside {path}: {resolved}"
            )
    return resolved


def validate_run_destination(output_root: Path, run_id: str) -> Path:
    """Validate a fresh run ID and prove the final directory stays inside root."""
    try:
        nb_artifacts.validate_run_id(run_id)
    except nb_artifacts.ArtifactError as exc:
        raise ConfigError(str(exc)) from exc
    root = Path(output_root)
    candidate = root / run_id
    resolved = candidate.resolve()
    if not nb_artifacts.is_within(resolved, root.resolve()):
        raise ConfigError(
            f"run ID {run_id!r} escapes the output root {root}: {resolved}"
        )
    return candidate


@dataclass(frozen=True)
class RunConfig:
    """Resolved, immutable configuration for one skeleton execution."""

    data_name: str
    method: str
    model_seed: int
    shuffle_seed: Optional[int]
    purpose: str
    run_id: str
    output_root: str
    repo_root: str
    demand_path: Optional[str] = None
    graph_path: Optional[str] = None
    published: bool = True
    command: Sequence[str] = field(default_factory=tuple)
    launcher_cwd: Optional[str] = None
    run_type: str = "run"

    def __post_init__(self) -> None:
        protocol.validate_dataset_name(self.data_name)
        protocol.validate_method(self.method)
        protocol.validate_model_seed(self.model_seed)
        protocol.validate_shuffle_seed(self.method, self.shuffle_seed)
        protocol.validate_purpose(self.purpose)
        validate_run_destination(Path(self.output_root), self.run_id)

    @property
    def run_dir(self) -> Path:
        return Path(self.output_root) / self.run_id

    @property
    def model_method(self) -> str:
        return self.method

    @property
    def method_name(self) -> str:
        return self.method

    @property
    def split_masks_scope(self) -> str:
        return "train27"

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["command"] = list(self.command)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RunConfig":
        known = set(cls.__dataclass_fields__)
        filtered = {key: value for key, value in payload.items() if key in known}
        if "command" in filtered:
            filtered["command"] = tuple(filtered["command"] or ())
        return cls(**filtered)

    def computational_identity(self) -> Dict[str, Any]:
        return computational_identity(
            data_name=self.data_name,
            method=self.method,
            model_seed=self.model_seed,
            shuffle_seed=self.shuffle_seed,
        )


def computational_identity(
    *,
    data_name: str,
    method: str,
    model_seed: int,
    shuffle_seed: Optional[int],
) -> Dict[str, Any]:
    """Return the purpose/run-independent scientific computation identity.

    Differences in purpose, run ID, output root, command or timestamps are
    execution metadata and are deliberately absent, so two same-condition
    repeats agree here.
    """
    protocol.validate_dataset_name(data_name)
    protocol.validate_method(method)
    protocol.validate_model_seed(model_seed)
    protocol.validate_shuffle_seed(method, shuffle_seed)
    return {
        "data_name": data_name,
        "mode": "count",
        "method": method,
        "model_seed": int(model_seed),
        "shuffle_seed": shuffle_seed,
        "scientific_protocol_version": protocol.SCIENTIFIC_PROTOCOL_VERSION,
        "records_policy": protocol.RECORDS_POLICY,
        "skeleton_version": protocol.SKELETON_VERSION,
        "model": protocol.MODEL_DEFINITION,
        "hidden_dim": protocol.HIDDEN_DIM,
        "epochs": protocol.EPOCHS,
        "loss": protocol.LOSS,
        "preprocessing": protocol.PREPROCESSING,
        "adam": {
            "lr": float(protocol.ADAM["lr"]),
            "betas": [float(value) for value in protocol.ADAM["betas"]],
            "eps": float(protocol.ADAM["eps"]),
            "weight_decay": float(protocol.ADAM["weight_decay"]),
            "amsgrad": bool(protocol.ADAM["amsgrad"]),
        },
        "scheduler": None,
        "early_stopping": False,
        "gradient_clipping": None,
        "batch_rule": (
            "one epoch covers the 19 training windows and all nodes/horizons "
            "with equal element weighting; chunks follow ascending window then "
            "ascending context with complete per-context adjacency; one "
            "optimizer step per epoch after global mean-loss gradient accumulation"
        ),
        "shuffle": {
            "algorithm": protocol.SHUFFLE_ALGORITHM,
            "version": protocol.SHUFFLE_VERSION,
            "accept_target_factor": protocol.SHUFFLE_ACCEPT_FACTOR,
            "attempt_limit_factor": protocol.SHUFFLE_ATTEMPT_LIMIT_FACTOR,
            "seeds": list(protocol.SHUFFLE_SEEDS),
        },
        "parameter_counts": dict(protocol.PARAMETER_COUNTS),
        "input_length": protocol.INPUT_LENGTH,
        "horizon": protocol.HORIZON,
        "n_windows": protocol.N_WINDOWS,
        "splits": {
            "train": list(protocol.TRAIN_STARTS),
            "validation": list(protocol.VALIDATION_STARTS),
            "test": list(protocol.TEST_STARTS),
        },
        "selection_metric": "validation MSE (original units)",
        "tie_break": "earliest epoch",
        "masks_scope": "train27 activity/constant; published-graph nonself coverage",
        "naive_methods": list(protocol.NAIVE_METHODS),
    }


def _resolve_input_path(raw: Optional[str], base: Path) -> Optional[Path]:
    if raw is None:
        return None
    candidate = Path(raw)
    return candidate if candidate.is_absolute() else (base / candidate)


def resolve_config(
    *,
    data_name: str,
    method: str,
    model_seed: int,
    shuffle_seed: Optional[int],
    run_id: str,
    purpose: str = protocol.PURPOSE_DEVELOPMENT,
    repo_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    demand_path: Optional[str] = None,
    graph_path: Optional[str] = None,
    command: Sequence[str] = (),
    launcher_cwd: Optional[Path] = None,
) -> RunConfig:
    """Validate every axis and destination before any directory is reserved."""
    protocol.validate_dataset_name(data_name)
    protocol.validate_method(method)
    model_seed = protocol.validate_model_seed(model_seed)
    shuffle_seed = protocol.validate_shuffle_seed(method, shuffle_seed)
    protocol.validate_purpose(purpose)
    root = Path(repo_root) if repo_root is not None else protocol.REPO_ROOT
    base = Path(launcher_cwd) if launcher_cwd is not None else Path.cwd()
    resolved_demand = _resolve_input_path(demand_path, base)
    resolved_graph = _resolve_input_path(graph_path, base)
    published = resolved_demand is None or (
        resolved_demand.resolve() == p01.demand_path(data_name).resolve()
    )
    resolved_output = resolve_output_root(root, purpose, output_root)
    validate_run_destination(resolved_output, run_id)
    return RunConfig(
        data_name=data_name,
        method=method,
        model_seed=model_seed,
        shuffle_seed=shuffle_seed,
        purpose=purpose,
        run_id=run_id,
        output_root=resolved_output.as_posix(),
        repo_root=root.as_posix(),
        demand_path=(
            resolved_demand.as_posix() if resolved_demand is not None else None
        ),
        graph_path=resolved_graph.as_posix() if resolved_graph is not None else None,
        published=bool(published),
        command=tuple(command),
        launcher_cwd=(Path(launcher_cwd).as_posix() if launcher_cwd is not None else None),
    )
