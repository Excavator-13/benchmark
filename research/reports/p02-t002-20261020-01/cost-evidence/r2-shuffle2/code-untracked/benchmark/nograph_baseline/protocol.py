"""Fixed ``P1-count-L6-H3-v3`` constants, calendar metadata and split checks.

Everything scientific in this package derives from this module.  The values are
copied from ``research/phases/P01/protocol.md`` sections 3-6; the protocol file
itself is snapshotted into every run directory rather than re-interpreted here.
Only the three required third-party packages are imported.

The default main split remains the only implicit behavior.  The two development
backtest folds ``A`` and ``B`` of ``research/phases/P01/t007-backtest-guide.md``
sections 2-5 are explicit immutable :class:`SplitDefinition` objects; nothing
here mutates a module global when a fold is selected, so one process can run
main, A and B alternately without leaking state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

__all__ = [
    "PROTOCOL_VERSION",
    "INPUT_LENGTH",
    "HORIZON",
    "N_MONTHS",
    "N_WINDOWS",
    "MONTHS",
    "TRAIN_OBSERVATION_MONTHS",
    "TRAIN_OBSERVATION_MONTH_COUNT",
    "SPLITS",
    "OMITTED_STARTS",
    "ALL_STARTS",
    "LAMBDA_CANDIDATES",
    "NAIVE_METHODS",
    "NAIVE_REF6_METHODS",
    "ACTIVITY_GROUP_NAMES",
    "ACTIVITY_GROUP_BOUNDS",
    "MODEL_NAME",
    "CLIPPED_MODEL_NAME",
    "SUPPORTED_DATASETS",
    "SUPPORTED_MODES",
    "CHECKS",
    "MODULE_DIR",
    "REPO_ROOT",
    "DATASET_DIR",
    "DEMAND_DIR",
    "GRAPH_DIR",
    "RUNS_DIR",
    "PROTOCOL_PATH",
    "FOLD_NAMES",
    "FOLD_A",
    "FOLD_B",
    "MAIN_SPLIT",
    "SPLIT_DEFINITIONS",
    "SplitDefinition",
    "ProtocolError",
    "month_labels",
    "month_column",
    "month_columns",
    "context_columns",
    "node_key_columns",
    "window_input_months",
    "window_target_months",
    "window_forecast_origin",
    "windows_for_split",
    "build_window_metadata",
    "validate_split_assertions",
    "validate_split_definition",
    "resolve_split",
    "fold_names",
    "validate_dataset_mode",
    "demand_path",
    "graph_path",
]

PROTOCOL_VERSION = "P1-count-L6-H3-v3"

INPUT_LENGTH = 6
HORIZON = 3
N_MONTHS = 36
N_WINDOWS = N_MONTHS - INPUT_LENGTH - HORIZON + 1  # 28 unit-stride windows

MONTHS: Tuple[str, ...] = tuple(
    f"{year}-{month:02d}" for year in (2021, 2022, 2023) for month in range(1, 13)
)
#: The 27 unique normalization/TrainMean27 observation months (2021-01..2023-03).
TRAIN_OBSERVATION_MONTH_COUNT = 27
TRAIN_OBSERVATION_MONTHS: Tuple[str, ...] = MONTHS[:TRAIN_OBSERVATION_MONTH_COUNT]

#: Split name -> the window start indices that belong to it (main split).
SPLITS: Mapping[str, Tuple[int, ...]] = {
    "train": tuple(range(19)),
    "validation": (21,),
    "test": (24, 25, 26, 27),
}

ALL_STARTS: Tuple[int, ...] = tuple(range(N_WINDOWS))
OMITTED_STARTS: Tuple[int, ...] = tuple(
    start for start in ALL_STARTS if not any(start in starts for starts in SPLITS.values())
)

#: Preset lambda candidates for the shared Ridge model.
LAMBDA_CANDIDATES: Tuple[float, ...] = (1e-4, 1e-3, 1e-2, 1e-1, 1.0)

#: Protocol reporting order; also the exact-tie break order for reference choice.
NAIVE_METHODS: Tuple[str, ...] = (
    "Zero",
    "LastValue",
    "WindowMean6",
    "TrainMean27",
    "SeasonalNaive12",
)
NAIVE_REF6_METHODS: Tuple[str, ...] = tuple(
    name for name in NAIVE_METHODS if name != "SeasonalNaive12"
)

ACTIVITY_GROUP_NAMES: Tuple[str, ...] = ("inactive", "low", "medium", "high")
#: (lower exclusive, upper inclusive) per group; the inactive group is ``== 0``.
ACTIVITY_GROUP_BOUNDS: Mapping[str, Tuple[float, float]] = {
    "inactive": (0.0, 0.0),
    "low": (0.0, 1.0 / 3.0),
    "medium": (1.0 / 3.0, 2.0 / 3.0),
    "high": (2.0 / 3.0, 1.0),
}

MODEL_NAME = "SharedRidge"
CLIPPED_MODEL_NAME = "SharedRidgeNonnegative"

#: Dataset name -> context id column(s) preceding ``skill_id``.
SUPPORTED_DATASETS: Mapping[str, Tuple[str, ...]] = {
    "r0": ("r0_id",),
    "r2": ("r2_id",),
    "region": ("region_id",),
}
SUPPORTED_MODES: Tuple[str, ...] = ("count",)
CHECKS: Tuple[str, ...] = ("recompute", "compare", "align-v2")

MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parents[1]
DATASET_DIR = REPO_ROOT / "dataset"
DEMAND_DIR = DATASET_DIR / "demand"
GRAPH_DIR = DATASET_DIR / "graph"
RUNS_DIR = REPO_ROOT / "research" / "runs"
PROTOCOL_PATH = REPO_ROOT / "research" / "phases" / "P01" / "protocol.md"

#: Fixed omission reason codes from the T007 guide and the design table.
TRAIN_VALIDATION_OVERLAP = "train_validation_target_overlap"
VALIDATION_EVAL_OVERLAP = "validation_eval_target_overlap"
OVERLAPS_EVAL_TARGETS = "overlaps_eval_targets"
OUTSIDE_FOLD = "outside_fold"

#: The two explicit development backtest folds (guide section 2).
FOLD_NAMES: Tuple[str, ...] = ("A", "B")


class ProtocolError(ValueError):
    """Raised when a request or constructed window set violates the protocol."""


def month_labels() -> List[str]:
    """Return the 36 canonical ``YYYY-MM`` labels in chronological order."""
    return list(MONTHS)


def month_column(index: int) -> str:
    """Return the ``YYYY-MM`` column name for a 0-based month index."""
    if not 0 <= index < N_MONTHS:
        raise ProtocolError(f"month index {index} is outside 0..{N_MONTHS - 1}")
    return MONTHS[index]


def month_columns() -> List[str]:
    """Return the month columns that a demand table must contain."""
    return list(MONTHS)


def context_columns(data_name: str) -> Tuple[str, ...]:
    """Return the context id columns for a supported dataset."""
    try:
        return SUPPORTED_DATASETS[data_name]
    except KeyError as exc:
        raise ProtocolError(
            f"unsupported dataset {data_name!r}; supported: {sorted(SUPPORTED_DATASETS)}"
        ) from exc


def node_key_columns(data_name: str) -> Tuple[str, ...]:
    """Return the canonical node key columns (context ids then ``skill_id``)."""
    return context_columns(data_name) + ("skill_id",)


def validate_dataset_mode(data_name: str, mode: str) -> None:
    """Reject any dataset/mode outside this protocol before fitting."""
    if data_name not in SUPPORTED_DATASETS:
        raise ProtocolError(
            f"unsupported dataset {data_name!r}; supported: {sorted(SUPPORTED_DATASETS)}"
        )
    if mode not in SUPPORTED_MODES:
        raise ProtocolError(
            f"unsupported mode {mode!r}; supported: {list(SUPPORTED_MODES)}"
        )


def window_input_months(start: int) -> Tuple[str, ...]:
    """Return the six input month labels for a window start index."""
    _validate_start(start)
    return tuple(MONTHS[start : start + INPUT_LENGTH])


def window_target_months(start: int) -> Tuple[str, ...]:
    """Return the three target month labels for a window start index."""
    _validate_start(start)
    return tuple(MONTHS[start + INPUT_LENGTH : start + INPUT_LENGTH + HORIZON])


def window_forecast_origin(start: int) -> str:
    """Return the forecast origin label (last observed input month)."""
    _validate_start(start)
    return MONTHS[start + INPUT_LENGTH - 1]


@dataclass(frozen=True)
class SplitDefinition:
    """Immutable description of the main split or one fixed development fold.

    A definition is the single source for window starts, fitting statistics,
    split naming, method order and folded artifact names.  Instances are frozen
    so a run cannot mutate its chosen split; validation re-derives every fixed
    value and rejects a hand-modified definition.
    """

    name: str
    fold: Optional[str]
    fitting_month_count: int
    train_starts: Tuple[int, ...]
    validation_starts: Tuple[int, ...]
    evaluation_starts: Tuple[int, ...]
    evaluation_split: str
    omitted_starts: Tuple[int, ...]
    omitted_reasons: Tuple[Tuple[int, str], ...]
    outside_fold_starts: Tuple[int, ...]
    naive_methods: Tuple[str, ...]

    @property
    def is_main(self) -> bool:
        """Whether this is the unchanged default main split."""
        return self.fold is None

    @property
    def fitting_observation_months(self) -> Tuple[str, ...]:
        """The unique fitting observations, starting at 2021-01."""
        return MONTHS[: self.fitting_month_count]

    @property
    def evaluation_splits(self) -> Tuple[str, ...]:
        """The two reported evaluation splits (validation and test/eval)."""
        return ("validation", self.evaluation_split)

    @property
    def split_names(self) -> Tuple[str, ...]:
        """Every predictive split name for this definition."""
        return ("train", "validation", self.evaluation_split)

    @property
    def scope_label(self) -> str:
        """Fitting-scope label used in masks and diagnostics."""
        return "train27" if self.is_main else f"fit{self.fitting_month_count}"

    @property
    def train_mean_method(self) -> str:
        """The frozen training-mean method name for this fitting scope."""
        return f"TrainMean{self.fitting_month_count}"

    @property
    def train_mean_column(self) -> str:
        """The node-error fitting-mean column name."""
        return f"train_mean{self.fitting_month_count}"

    @property
    def activity_group_names(self) -> Tuple[str, ...]:
        """Activity group identifiers, prefixed with the fitting scope for folds."""
        if self.is_main:
            return ACTIVITY_GROUP_NAMES
        return tuple(f"{self.scope_label}_{name}" for name in ACTIVITY_GROUP_NAMES)

    @property
    def constant_group_names(self) -> Tuple[str, ...]:
        """Constant/nonconstant diagnostic group identifiers."""
        return (
            f"constant_{self.scope_label}",
            f"nonconstant_{self.scope_label}",
        )

    @property
    def nonzero_activity_key(self) -> str:
        """Saved mask key for the continuous fitting-scope activity fraction."""
        return f"nonzero_activity_{self.scope_label}"

    @property
    def constant_mask_key(self) -> str:
        """Saved mask key for the fitting-scope constant-node mask."""
        return f"constant_{self.scope_label}"

    @property
    def activity_mask_keys(self) -> Tuple[str, ...]:
        """Saved mask keys for the four activity groups."""
        return tuple(f"activity_{name}" for name in self.activity_group_names)

    @property
    def evaluation_role(self) -> str:
        """Role name of the second evaluation split in saved window metadata."""
        return self.evaluation_split

    def starts_for(self, split: str) -> Tuple[int, ...]:
        """Return the fixed window starts for a split of this definition."""
        if split == "train":
            return self.train_starts
        if split == "validation":
            return self.validation_starts
        if split == self.evaluation_split:
            return self.evaluation_starts
        raise ProtocolError(
            f"unknown split {split!r} for {self.name}; expected "
            f"{list(self.split_names)}"
        )

    def target_months_for(self, split: str) -> Tuple[str, ...]:
        """Return the sorted unique target months for a split."""
        return tuple(
            sorted(
                {
                    month
                    for start in self.starts_for(split)
                    for month in window_target_months(start)
                }
            )
        )

    @property
    def eval_target_months(self) -> Tuple[str, ...]:
        """The sorted unique evaluation target months."""
        return self.target_months_for(self.evaluation_split)

    @property
    def naive_ref6_methods(self) -> Tuple[str, ...]:
        """The four NaiveRef6 candidates in protocol table order."""
        return tuple(
            name for name in self.naive_methods if name != "SeasonalNaive12"
        )

    def omitted_reason_map(self) -> Dict[int, str]:
        """Return the fixed omission reason per omitted start."""
        return {int(start): str(reason) for start, reason in self.omitted_reasons}

    def role_for_start(self, start: int) -> str:
        """Return the single saved role of a window start."""
        _validate_start(start)
        if start in self.train_starts:
            return "train"
        if start in self.validation_starts:
            return "validation"
        if start in self.evaluation_starts:
            return self.evaluation_role
        if start in self.outside_fold_starts:
            return OUTSIDE_FOLD
        return "omitted"

    def reason_for_start(self, start: int) -> Optional[str]:
        """Return the saved omission/outside reason, or ``None`` for a split."""
        role = self.role_for_start(start)
        if role == "omitted":
            return self.omitted_reason_map().get(int(start), "omitted")
        if role == OUTSIDE_FOLD:
            return OUTSIDE_FOLD
        return None

    def to_payload(self) -> Dict[str, object]:
        """The fold identity payload shared by config, provenance and selection."""
        if self.is_main:
            raise ProtocolError("the main split has no fold identity payload")
        return {
            "fold": self.fold,
            "fitting_observation_months": list(self.fitting_observation_months),
            "fitting_month_count": self.fitting_month_count,
            "train_starts": list(self.train_starts),
            "validation_starts": list(self.validation_starts),
            "eval_starts": list(self.evaluation_starts),
            "omitted_starts": list(self.omitted_starts),
            "omitted_reasons": {
                str(start): reason
                for start, reason in self.omitted_reason_map().items()
            },
            "outside_fold_starts": list(self.outside_fold_starts),
            "eval_target_months": list(self.eval_target_months),
            "train_mean_method": self.train_mean_method,
            "evaluation_splits": list(self.evaluation_splits),
            "evidence_role": "development_backtest",
        }

    def validate(self) -> None:
        """Raise :class:`ProtocolError` unless every fixed value still matches."""
        validate_split_definition(self)


MAIN_SPLIT = SplitDefinition(
    name="main",
    fold=None,
    fitting_month_count=27,
    train_starts=tuple(range(19)),
    validation_starts=(21,),
    evaluation_starts=(24, 25, 26, 27),
    evaluation_split="test",
    omitted_starts=(19, 20, 22, 23),
    omitted_reasons=(
        (19, TRAIN_VALIDATION_OVERLAP),
        (20, TRAIN_VALIDATION_OVERLAP),
        (22, VALIDATION_EVAL_OVERLAP),
        (23, VALIDATION_EVAL_OVERLAP),
    ),
    outside_fold_starts=(),
    naive_methods=NAIVE_METHODS,
)

FOLD_A = SplitDefinition(
    name="A",
    fold="A",
    fitting_month_count=18,
    train_starts=tuple(range(10)),
    validation_starts=(12,),
    evaluation_starts=(15,),
    evaluation_split="eval",
    omitted_starts=(10, 11, 13, 14, 16, 17),
    omitted_reasons=(
        (10, TRAIN_VALIDATION_OVERLAP),
        (11, TRAIN_VALIDATION_OVERLAP),
        (13, VALIDATION_EVAL_OVERLAP),
        (14, VALIDATION_EVAL_OVERLAP),
        (16, OVERLAPS_EVAL_TARGETS),
        (17, OVERLAPS_EVAL_TARGETS),
    ),
    outside_fold_starts=tuple(range(18, 28)),
    naive_methods=(
        "Zero",
        "LastValue",
        "WindowMean6",
        "TrainMean18",
        "SeasonalNaive12",
    ),
)

FOLD_B = SplitDefinition(
    name="B",
    fold="B",
    fitting_month_count=21,
    train_starts=tuple(range(13)),
    validation_starts=(15,),
    evaluation_starts=(18,),
    evaluation_split="eval",
    omitted_starts=(13, 14, 16, 17, 19, 20),
    omitted_reasons=(
        (13, TRAIN_VALIDATION_OVERLAP),
        (14, TRAIN_VALIDATION_OVERLAP),
        (16, VALIDATION_EVAL_OVERLAP),
        (17, VALIDATION_EVAL_OVERLAP),
        (19, OVERLAPS_EVAL_TARGETS),
        (20, OVERLAPS_EVAL_TARGETS),
    ),
    outside_fold_starts=tuple(range(21, 28)),
    naive_methods=(
        "Zero",
        "LastValue",
        "WindowMean6",
        "TrainMean21",
        "SeasonalNaive12",
    ),
)

SPLIT_DEFINITIONS: Mapping[str, SplitDefinition] = {
    "main": MAIN_SPLIT,
    "A": FOLD_A,
    "B": FOLD_B,
}

#: Fixed expected values used by :func:`validate_split_definition`.
_EXPECTED_SPLITS: Mapping[str, Mapping[str, object]] = {
    "main": {
        "name": "main",
        "fold": None,
        "fitting_month_count": 27,
        "train": tuple(range(19)),
        "validation": (21,),
        "evaluation": (24, 25, 26, 27),
        "evaluation_split": "test",
        "omitted": (19, 20, 22, 23),
        "reasons": {
            19: TRAIN_VALIDATION_OVERLAP,
            20: TRAIN_VALIDATION_OVERLAP,
            22: VALIDATION_EVAL_OVERLAP,
            23: VALIDATION_EVAL_OVERLAP,
        },
        "outside": (),
        "targets": {
            "train": tuple(MONTHS[6:27]),
            "validation": tuple(MONTHS[27:30]),
            "test": tuple(MONTHS[30:36]),
        },
    },
    "A": {
        "name": "A",
        "fold": "A",
        "fitting_month_count": 18,
        "train": tuple(range(10)),
        "validation": (12,),
        "evaluation": (15,),
        "evaluation_split": "eval",
        "omitted": (10, 11, 13, 14, 16, 17),
        "reasons": {
            10: TRAIN_VALIDATION_OVERLAP,
            11: TRAIN_VALIDATION_OVERLAP,
            13: VALIDATION_EVAL_OVERLAP,
            14: VALIDATION_EVAL_OVERLAP,
            16: OVERLAPS_EVAL_TARGETS,
            17: OVERLAPS_EVAL_TARGETS,
        },
        "outside": tuple(range(18, 28)),
        "targets": {
            "train": tuple(MONTHS[6:18]),
            "validation": tuple(MONTHS[18:21]),
            "eval": tuple(MONTHS[21:24]),
        },
    },
    "B": {
        "name": "B",
        "fold": "B",
        "fitting_month_count": 21,
        "train": tuple(range(13)),
        "validation": (15,),
        "evaluation": (18,),
        "evaluation_split": "eval",
        "omitted": (13, 14, 16, 17, 19, 20),
        "reasons": {
            13: TRAIN_VALIDATION_OVERLAP,
            14: TRAIN_VALIDATION_OVERLAP,
            16: VALIDATION_EVAL_OVERLAP,
            17: VALIDATION_EVAL_OVERLAP,
            19: OVERLAPS_EVAL_TARGETS,
            20: OVERLAPS_EVAL_TARGETS,
        },
        "outside": tuple(range(21, 28)),
        "targets": {
            "train": tuple(MONTHS[6:21]),
            "validation": tuple(MONTHS[21:24]),
            "eval": tuple(MONTHS[24:27]),
        },
    },
}


def fold_names() -> Tuple[str, ...]:
    """Return the supported explicit fold names."""
    return FOLD_NAMES


def resolve_split(fold: Optional[str]) -> SplitDefinition:
    """Resolve an explicit ``A``/``B`` fold or the default main split.

    ``None`` (or the documented internal value ``"main"``) resolves to the
    unchanged main split.  Every other value fails before fitting or run
    directory reservation.
    """
    if fold is None:
        return MAIN_SPLIT
    if isinstance(fold, str) and fold == "main":
        return MAIN_SPLIT
    if isinstance(fold, str) and fold in FOLD_NAMES:
        return SPLIT_DEFINITIONS[fold]
    raise ProtocolError(
        f"unknown fold {fold!r}; supported explicit folds are {list(FOLD_NAMES)} "
        "(omit the option for the default main split)"
    )


def windows_for_split(
    split: str, definition: Optional[SplitDefinition] = None
) -> Tuple[int, ...]:
    """Return the window starts assigned to a split name."""
    return (definition or MAIN_SPLIT).starts_for(split)


def _validate_start(start: int) -> None:
    if not 0 <= start < N_WINDOWS:
        raise ProtocolError(f"window start {start} is outside 0..{N_WINDOWS - 1}")


def build_window_metadata(
    definition: Optional[SplitDefinition] = None,
) -> Dict[str, object]:
    """Describe all 28 windows, splits, omissions and forecast origins.

    The main split keeps the historical payload exactly (no fold/eval field).
    A fold payload lists every start's single role (train, validation, eval,
    omitted or outside_fold) plus its reason and months; listing later window
    metadata never constructs or predicts those windows.
    """
    definition = MAIN_SPLIT if definition is None else definition
    windows = []
    for start in ALL_STARTS:
        entry = {
            "start": start,
            "input_months": list(window_input_months(start)),
            "target_months": list(window_target_months(start)),
            "forecast_origin": window_forecast_origin(start),
        }
        if definition.is_main:
            entry["split"] = next(
                (
                    name
                    for name, starts in SPLITS.items()
                    if start in starts
                ),
                None,
            )
        else:
            entry["role"] = definition.role_for_start(start)
            entry["reason"] = definition.reason_for_start(start)
        windows.append(entry)
    if definition.is_main:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "input_length": INPUT_LENGTH,
            "horizon": HORIZON,
            "n_windows": N_WINDOWS,
            "all_starts": list(ALL_STARTS),
            "splits": {name: list(starts) for name, starts in SPLITS.items()},
            "omitted_starts": list(OMITTED_STARTS),
            "windows": windows,
        }
    return {
        "protocol_version": PROTOCOL_VERSION,
        "input_length": INPUT_LENGTH,
        "horizon": HORIZON,
        "n_windows": N_WINDOWS,
        "all_starts": list(ALL_STARTS),
        "fold": definition.fold,
        "fitting_observation_months": list(definition.fitting_observation_months),
        "fitting_month_count": definition.fitting_month_count,
        "splits": {
            "train": list(definition.train_starts),
            "validation": list(definition.validation_starts),
            definition.evaluation_split: list(definition.evaluation_starts),
        },
        "omitted_starts": list(definition.omitted_starts),
        "omitted_reasons": {
            str(start): reason
            for start, reason in definition.omitted_reason_map().items()
        },
        "outside_fold_starts": list(definition.outside_fold_starts),
        "eval_target_months": list(definition.eval_target_months),
        "evaluation_splits": list(definition.evaluation_splits),
        "windows": windows,
    }


def _definition_problems(definition: SplitDefinition) -> List[str]:
    """Return every structural and fixed-value problem of a definition."""
    problems: List[str] = []
    key = "main" if definition.fold is None else definition.fold
    expected = _EXPECTED_SPLITS.get(key)
    if expected is None:
        return [f"unknown split definition {definition!r}"]
    label = f"split {key}"

    def expect(field: str, actual: object, wanted: object) -> None:
        if actual != wanted:
            problems.append(f"{label}: {field} is {actual!r}, expected {wanted!r}")

    expect("name", definition.name, expected["name"])
    expect("fold", definition.fold, expected["fold"])
    expect(
        "fitting_month_count",
        definition.fitting_month_count,
        expected["fitting_month_count"],
    )
    expect("train starts", tuple(definition.train_starts), expected["train"])
    expect(
        "validation starts",
        tuple(definition.validation_starts),
        expected["validation"],
    )
    expect(
        "evaluation starts",
        tuple(definition.evaluation_starts),
        expected["evaluation"],
    )
    expect("evaluation split", definition.evaluation_split, expected["evaluation_split"])
    expect("omitted starts", tuple(definition.omitted_starts), expected["omitted"])
    expect(
        "omitted reasons",
        {int(start): str(reason) for start, reason in definition.omitted_reasons},
        expected["reasons"],
    )
    expect("outside-fold starts", tuple(definition.outside_fold_starts), expected["outside"])

    expected_methods = (
        "Zero",
        "LastValue",
        "WindowMean6",
        f"TrainMean{int(expected['fitting_month_count'])}",
        "SeasonalNaive12",
    )
    expect("naive method order", tuple(definition.naive_methods), expected_methods)

    # Every start 0..27 must have exactly one role; roles must be exhaustive.
    roles: Dict[int, str] = {}
    role_starts = {
        "train": definition.train_starts,
        "validation": definition.validation_starts,
        definition.evaluation_split: definition.evaluation_starts,
        "omitted": definition.omitted_starts,
        OUTSIDE_FOLD: definition.outside_fold_starts,
    }
    for role, starts in role_starts.items():
        for start in starts:
            if not 0 <= int(start) < N_WINDOWS:
                problems.append(f"{label}: {role} start {start} is outside 0..27")
                continue
            if int(start) in roles:
                problems.append(
                    f"{label}: start {start} has roles {roles[int(start)]} and {role}"
                )
            roles[int(start)] = role
    missing_roles = sorted(set(ALL_STARTS) - set(roles))
    if missing_roles:
        problems.append(f"{label}: starts without a role: {missing_roles}")

    # Split targets must be pairwise disjoint and exactly the fixed months.
    targets = {
        name: set(definition.target_months_for(name))
        for name in definition.split_names
        if name != "train"
    }
    targets["train"] = set(definition.target_months_for("train"))
    for left, right in (
        ("train", "validation"),
        ("train", definition.evaluation_split),
        ("validation", definition.evaluation_split),
    ):
        overlap = targets[left] & targets[right]
        if overlap:
            problems.append(
                f"{label}: target months overlap between {left} and {right}: "
                f"{sorted(overlap)}"
            )
    for name, wanted in expected["targets"].items():
        if tuple(sorted(targets[name])) != tuple(wanted):
            problems.append(
                f"{label}: {name} target months are {sorted(targets[name])}, "
                f"expected {list(wanted)}"
            )

    # The fitting period starts at 2021-01 and covers every training input and
    # target month exactly; it is a prefix of the 36-month calendar.
    count = definition.fitting_month_count
    if not 0 < count <= N_MONTHS:
        problems.append(f"{label}: fitting month count {count} is outside 1..36")
    else:
        fitting_months = set(definition.fitting_observation_months)
        for start in definition.train_starts:
            if not 0 <= int(start) < N_WINDOWS:
                continue
            for month in window_input_months(int(start)) + window_target_months(int(start)):
                if month not in fitting_months:
                    problems.append(
                        f"{label}: training window {start} month {month} is outside "
                        f"the fitting period 2021-01..{MONTHS[count - 1]}"
                    )
        first_month = min(
            window_input_months(int(start))[0]
            for start in definition.train_starts
            if 0 <= int(start) < N_WINDOWS
        )
        if first_month != MONTHS[0]:
            problems.append(
                f"{label}: fitting inputs start at {first_month}, expected {MONTHS[0]}"
            )
    return problems


def validate_split_definition(definition: SplitDefinition) -> None:
    """Reject a hand-modified split description before any computation."""
    if not isinstance(definition, SplitDefinition):
        raise ProtocolError(
            f"expected a SplitDefinition, got {type(definition).__name__}"
        )
    problems = _definition_problems(definition)
    if problems:
        raise ProtocolError("; ".join(problems))


def validate_split_assertions(
    definition: Optional[SplitDefinition] = None,
) -> None:
    """Assert the fixed main split or explicit A/B split and target isolation.

    Raises :class:`ProtocolError` on any inconsistency so that a run can never
    silently continue with a different scientific configuration.
    """
    validate_split_definition((MAIN_SPLIT if definition is None else definition))


def demand_path(data_name: str) -> Path:
    """Default demand Parquet path for a dataset."""
    validate_dataset_mode(data_name, "count")
    return DEMAND_DIR / f"{data_name}.parquet"


def graph_path(data_name: str) -> Path:
    """Default raw graph Parquet path used only for coverage annotation."""
    validate_dataset_mode(data_name, "count")
    return GRAPH_DIR / f"{data_name}.parquet"


def expected_train_sample_count(
    node_count: int, definition: Optional[SplitDefinition] = None
) -> int:
    """Return ``M = train window count * N`` for the shared Ridge design."""
    definition = MAIN_SPLIT if definition is None else definition
    return len(definition.train_starts) * int(node_count)


def activity_group_bounds() -> Mapping[str, Tuple[float, float]]:
    """Return a copy of the four fixed activity-group boundaries."""
    return dict(ACTIVITY_GROUP_BOUNDS)


def is_finite_number(value: float) -> bool:
    """Return whether ``value`` is a finite float."""
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def as_serializable_months(months: Sequence[str]) -> List[str]:
    """Return month labels as a plain list for JSON output."""
    return [str(month) for month in months]
