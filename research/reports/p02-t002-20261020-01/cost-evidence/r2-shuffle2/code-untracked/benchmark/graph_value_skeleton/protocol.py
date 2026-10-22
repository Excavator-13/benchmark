"""Fixed P02 skeleton constants, publication expectations and version anchors.

The scientific protocol is unchanged: this package only implements P02-T001 on
top of ``P1-count-L6-H3-v3`` and ``P01-records-v2``.  Everything in this module
is frozen; a run asserts these values instead of accepting them from the
command line.  Nothing here mutates a ``benchmark.nograph_baseline`` module
global, so one process can resolve ``self``/``graph``/``shuffled`` requests
alternately.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from benchmark.nograph_baseline import protocol as p01

__all__ = [
    "SCIENTIFIC_PROTOCOL_VERSION",
    "RECORDS_POLICY",
    "SKELETON_VERSION",
    "TASK_ID",
    "CHANGE_NAME",
    "DESIGN_DECISION",
    "METHODS",
    "METHOD_GRAPH",
    "METHOD_SELF",
    "METHOD_SHUFFLED",
    "SHUFFLE_SEEDS",
    "DEVELOPMENT_MODEL_SEEDS",
    "FINAL_MODEL_SEEDS",
    "MODEL_SEEDS",
    "PURPOSES",
    "PURPOSE_DEVELOPMENT",
    "PURPOSE_FORMAL",
    "INPUT_LENGTH",
    "HORIZON",
    "N_MONTHS",
    "N_WINDOWS",
    "HIDDEN_DIM",
    "EPOCHS",
    "ADAM",
    "SHUFFLE_ALGORITHM",
    "SHUFFLE_VERSION",
    "SHUFFLE_ACCEPT_FACTOR",
    "SHUFFLE_ATTEMPT_LIMIT_FACTOR",
    "MODEL_DEFINITION",
    "PARAMETER_COUNTS",
    "PUBLISHED_DEMAND",
    "PUBLISHED_GRAPH_ROWS",
    "PUBLISHED_CONTEXT_STRIDE",
    "NAIVE_METHODS",
    "NAIVE_REF_PUBLISHED",
    "MODEL_METHOD_NAMES",
    "PACKAGE_DIR",
    "REPO_ROOT",
    "DEMAND_DIR",
    "GRAPH_DIR",
    "FORMAL_RUNS_DIR",
    "DEVELOPMENT_ROOT",
    "PROTOCOL_PATH",
    "POLICY_SOURCES",
    "published_demand_spec",
    "published_graph_rows",
    "validate_dataset_name",
    "validate_method",
    "validate_model_seed",
    "validate_shuffle_seed",
    "validate_purpose",
    "seed_profile",
    "window_metadata",
    "protocol_identity",
    "policy_identity",
]

SCIENTIFIC_PROTOCOL_VERSION = p01.PROTOCOL_VERSION
RECORDS_POLICY = "P01-records-v2"
SKELETON_VERSION = "P02-skeleton-v1"
TASK_ID = "P02-T001"
CHANGE_NAME = "add-graph-value-skeleton"
DESIGN_DECISION = "D023"

METHOD_SELF = "self"
METHOD_GRAPH = "graph"
METHOD_SHUFFLED = "shuffled"
METHODS: Tuple[str, ...] = (METHOD_SELF, METHOD_GRAPH, METHOD_SHUFFLED)

SHUFFLE_SEEDS: Tuple[int, ...] = (0, 1, 2)

#: Development model seeds (0..2) are not a schedule; final seeds are 0..4.
DEVELOPMENT_MODEL_SEEDS: Tuple[int, ...] = (0, 1, 2)
FINAL_MODEL_SEEDS: Tuple[int, ...] = (0, 1, 2, 3, 4)
MODEL_SEEDS: Tuple[int, ...] = FINAL_MODEL_SEEDS

PURPOSE_FORMAL = "formal"
PURPOSE_DEVELOPMENT = "development"
PURPOSES: Tuple[str, ...] = (PURPOSE_DEVELOPMENT, PURPOSE_FORMAL)

INPUT_LENGTH = p01.INPUT_LENGTH
HORIZON = p01.HORIZON
N_MONTHS = p01.N_MONTHS
N_WINDOWS = p01.N_WINDOWS
TRAIN_STARTS: Tuple[int, ...] = p01.MAIN_SPLIT.train_starts
VALIDATION_STARTS: Tuple[int, ...] = p01.MAIN_SPLIT.validation_starts
TEST_STARTS: Tuple[int, ...] = p01.MAIN_SPLIT.evaluation_starts

HIDDEN_DIM = 32
EPOCHS = 200
#: Only values not expanded in the frozen design table; identical for all methods.
ADAM: Mapping[str, Any] = {
    "lr": 1e-3,
    "betas": (0.9, 0.999),
    "eps": 1e-8,
    "weight_decay": 0.0,
    "amsgrad": False,
}
LOSS = "mean_squared_error_on_raw_counts"
PREPROCESSING = "none: raw counts feed the encoder and the loss"
NO_SCHEDULER = True
NO_EARLY_STOPPING = True
NO_GRADIENT_CLIPPING = True

SHUFFLE_ALGORITHM = "context-local-directed-double-edge-swap"
SHUFFLE_VERSION = "dds-v2"
SHUFFLE_ACCEPT_FACTOR = 10
SHUFFLE_ATTEMPT_LIMIT_FACTOR = 500
SHUFFLE_PROPOSAL_BATCH = 4096
SHUFFLE_CONTRACTS = {
    "dds-v1": {"accept_target_factor": 10, "attempt_limit_factor": 100, "proposal_batch_size": 1},
    "dds-v2": {"accept_target_factor": 10, "attempt_limit_factor": 500, "proposal_batch_size": 4096},
}


def shuffle_contract(version):
    """Return a copy of a recognized, immutable-by-caller work contract."""
    if version not in SHUFFLE_CONTRACTS:
        raise ValueError(f"unsupported shuffle version {version!r}")
    return dict(SHUFFLE_CONTRACTS[version])

MODEL_DEFINITION = (
    "single-layer unidirectional bias-enabled GRU(1,32) shared across nodes; "
    "zero hidden state per node per window; shared Linear(32,3) head; graph and "
    "shuffled branches add the unweighted mean of distinct incoming neighbour "
    "hidden states before the head; no graph-specific trainable tensor"
)
#: Architectural counts asserted by tests and re-measured in every run.
PARAMETER_COUNTS: Mapping[str, int] = {"gru": 3360, "head": 99, "total": 3459}

#: Published demand identity (re-asserted on every published-data execution).
PUBLISHED_DEMAND: Mapping[str, Mapping[str, Any]] = {
    "r0": {"nodes": 2335, "contexts": (0,), "skills": (0, 2334), "months": 36},
    "region": {"nodes": 16345, "contexts": tuple(range(7)), "skills": (0, 2334), "months": 36},
    "r2": {"nodes": 121420, "contexts": tuple(range(52)), "skills": (0, 2334), "months": 36},
}
PUBLISHED_GRAPH_ROWS: Mapping[str, int] = {
    "r0": 60804,
    "region": 218840,
    "r2": 321374,
}
#: The dense published grid proves ``context_ordinal*2335 + skill_id``.
PUBLISHED_CONTEXT_STRIDE = 2335
PUBLISHED_SKILL_COUNT = 2335

NAIVE_METHODS: Tuple[str, ...] = p01.NAIVE_METHODS
NAIVE_REF_PUBLISHED = "LastValue"

#: Model method -> saved prediction/metric key (the method axis is explicit).
MODEL_METHOD_NAMES: Mapping[str, str] = {
    METHOD_SELF: METHOD_SELF,
    METHOD_GRAPH: METHOD_GRAPH,
    METHOD_SHUFFLED: METHOD_SHUFFLED,
}

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = p01.REPO_ROOT
DEMAND_DIR = p01.DEMAND_DIR
GRAPH_DIR = p01.GRAPH_DIR
FORMAL_RUNS_DIR = REPO_ROOT / "research" / "runs"
DEVELOPMENT_ROOT = REPO_ROOT / "scratch" / "graph-value-skeleton"
PROTOCOL_PATH = p01.PROTOCOL_PATH
#: (label, repository-relative path) documents whose content identifies the
#: scientific protocol and record policy actually in force.
POLICY_SOURCES: Tuple[Tuple[str, str], ...] = (
    ("scientific_protocol", "research/phases/P01/protocol.md"),
    ("records_policy", "AGENTS.md"),
    ("records_policy_origin", "research/archives/migrations/20261008-evidence-maintenance.md"),
)


class ProtocolError(ValueError):
    """Raised when fixed P02 axes or publication expectations are violated."""


def validate_dataset_name(data_name: str) -> str:
    try:
        p01.validate_dataset_mode(data_name, "count")
    except p01.ProtocolError as exc:
        raise ProtocolError(str(exc)) from exc
    return data_name


def validate_method(method: str) -> str:
    if method not in METHODS:
        raise ProtocolError(
            f"unsupported method {method!r}; supported: {list(METHODS)}"
        )
    return method


def validate_model_seed(model_seed: Any) -> int:
    if isinstance(model_seed, bool) or not isinstance(model_seed, int):
        raise ProtocolError(f"model seed must be an integer, got {model_seed!r}")
    if model_seed not in MODEL_SEEDS:
        raise ProtocolError(
            f"model seed {model_seed} is outside the frozen profiles "
            f"development={list(DEVELOPMENT_MODEL_SEEDS)} "
            f"final={list(FINAL_MODEL_SEEDS)}"
        )
    return model_seed


def validate_shuffle_seed(method: str, shuffle_seed: Optional[Any]) -> Optional[int]:
    """Shuffled requires a 0/1/2 seed; self/graph must not carry one."""
    if method == METHOD_SHUFFLED:
        if shuffle_seed is None:
            raise ProtocolError("method 'shuffled' requires --shuffle-seed 0|1|2")
        if isinstance(shuffle_seed, bool) or not isinstance(shuffle_seed, int):
            raise ProtocolError(
                f"shuffle seed must be an integer, got {shuffle_seed!r}"
            )
        if shuffle_seed not in SHUFFLE_SEEDS:
            raise ProtocolError(
                f"shuffle seed {shuffle_seed} is outside {list(SHUFFLE_SEEDS)}"
            )
        return shuffle_seed
    if shuffle_seed is not None:
        raise ProtocolError(
            f"method {method!r} must not carry a shuffle seed (got {shuffle_seed})"
        )
    return None


def validate_purpose(purpose: str) -> str:
    if purpose not in PURPOSES:
        raise ProtocolError(
            f"unsupported purpose {purpose!r}; supported: {list(PURPOSES)}"
        )
    return purpose


def seed_profile(model_seed: int) -> Dict[str, bool]:
    """Describe which frozen seed profile(s) contain a model seed (not a run)."""
    validate_model_seed(model_seed)
    return {
        "development": model_seed in DEVELOPMENT_MODEL_SEEDS,
        "final": model_seed in FINAL_MODEL_SEEDS,
    }


def window_metadata() -> Dict[str, Any]:
    """Return the unchanged main-split 28-window metadata."""
    return p01.build_window_metadata(p01.MAIN_SPLIT)


def published_demand_spec(data_name: str) -> Mapping[str, Any]:
    validate_dataset_name(data_name)
    if data_name not in PUBLISHED_DEMAND:
        raise ProtocolError(
            f"no published demand expectation is defined for {data_name!r}"
        )
    return PUBLISHED_DEMAND[data_name]


def published_graph_rows(data_name: str) -> int:
    validate_dataset_name(data_name)
    return PUBLISHED_GRAPH_ROWS[data_name]


def protocol_identity(protocol_path: Optional[Path] = None) -> Dict[str, Any]:
    """Identify the scientific protocol version and the exact content in force."""
    from benchmark.nograph_baseline.data import sha256_file

    path = Path(protocol_path) if protocol_path is not None else PROTOCOL_PATH
    return {
        "version": SCIENTIFIC_PROTOCOL_VERSION,
        "path": _display_path(path),
        "sha256": sha256_file(path) if path.is_file() else None,
        "available": path.is_file(),
    }


def policy_identity(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Identify the record policy name and the content of its source records."""
    from benchmark.nograph_baseline.data import sha256_file

    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    sources: Dict[str, Any] = {}
    for label, relative in POLICY_SOURCES:
        path = root / relative
        sources[label] = {
            "path": relative,
            "sha256": sha256_file(path) if path.is_file() else None,
            "available": path.is_file(),
        }
    return {"name": RECORDS_POLICY, "sources": sources}


def _display_path(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except (OSError, ValueError):
        return str(path)


def model_seed_profile_names(model_seed: int) -> Sequence[str]:
    profile = seed_profile(model_seed)
    return tuple(name for name, included in profile.items() if included)
