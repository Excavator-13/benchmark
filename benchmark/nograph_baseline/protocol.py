"""Fixed ``P1-count-L6-H3-v3`` constants, calendar metadata and split checks.

Everything scientific in this package derives from this module.  The values are
copied from ``research/phases/P01/protocol.md`` sections 3-6; the protocol file
itself is snapshotted into every run directory rather than re-interpreted here.
Only the three required third-party packages are imported.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

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

#: Split name -> the window start indices that belong to it.
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


def windows_for_split(split: str) -> Tuple[int, ...]:
    """Return the window starts assigned to a split name."""
    try:
        return SPLITS[split]
    except KeyError as exc:
        raise ProtocolError(
            f"unknown split {split!r}; expected one of {sorted(SPLITS)}"
        ) from exc


def _validate_start(start: int) -> None:
    if not 0 <= start < N_WINDOWS:
        raise ProtocolError(f"window start {start} is outside 0..{N_WINDOWS - 1}")


def build_window_metadata() -> Dict[str, object]:
    """Describe all 28 windows, splits, omissions and forecast origins."""
    windows = []
    for start in ALL_STARTS:
        split = next(
            (name for name, starts in SPLITS.items() if start in starts), None
        )
        windows.append(
            {
                "start": start,
                "split": split,
                "input_months": list(window_input_months(start)),
                "target_months": list(window_target_months(start)),
                "forecast_origin": window_forecast_origin(start),
            }
        )
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


def validate_split_assertions() -> None:
    """Assert the fixed 0..18 / 21 / 24..27 split and target-month isolation.

    Raises :class:`ProtocolError` on any inconsistency so that a run can never
    silently continue with a different scientific configuration.
    """
    problems: List[str] = []
    if N_WINDOWS != 28:
        problems.append(f"expected 28 windows, got {N_WINDOWS}")
    if tuple(SPLITS["train"]) != tuple(range(19)):
        problems.append(f"unexpected train starts: {SPLITS['train']}")
    if tuple(SPLITS["validation"]) != (21,):
        problems.append(f"unexpected validation starts: {SPLITS['validation']}")
    if tuple(SPLITS["test"]) != (24, 25, 26, 27):
        problems.append(f"unexpected test starts: {SPLITS['test']}")
    if tuple(OMITTED_STARTS) != (19, 20, 22, 23):
        problems.append(f"unexpected omitted starts: {OMITTED_STARTS}")

    target_sets = {
        name: {month for start in starts for month in window_target_months(start)}
        for name, starts in SPLITS.items()
    }
    pairs = (("train", "validation"), ("train", "test"), ("validation", "test"))
    for left, right in pairs:
        overlap = target_sets[left] & target_sets[right]
        if overlap:
            problems.append(
                f"target months overlap between {left} and {right}: {sorted(overlap)}"
            )

    expected_targets = {
        "train": tuple(MONTHS[6:27]),
        "validation": tuple(MONTHS[27:30]),
        "test": tuple(MONTHS[30:36]),
    }
    for name, expected in expected_targets.items():
        if tuple(sorted(target_sets[name])) != expected:
            problems.append(
                f"{name} target months are {sorted(target_sets[name])}, expected {list(expected)}"
            )

    total_assigned = sum(len(starts) for starts in SPLITS.values())
    if total_assigned + len(OMITTED_STARTS) != N_WINDOWS:
        problems.append("split and omitted windows do not partition all windows")

    if problems:
        raise ProtocolError("; ".join(problems))


def demand_path(data_name: str) -> Path:
    """Default demand Parquet path for a dataset."""
    validate_dataset_mode(data_name, "count")
    return DEMAND_DIR / f"{data_name}.parquet"


def graph_path(data_name: str) -> Path:
    """Default raw graph Parquet path used only for coverage annotation."""
    validate_dataset_mode(data_name, "count")
    return GRAPH_DIR / f"{data_name}.parquet"


def expected_train_sample_count(node_count: int) -> int:
    """Return ``M = 19 * N`` for the shared Ridge training design."""
    return len(SPLITS["train"]) * int(node_count)


def activity_group_bounds() -> Mapping[str, Tuple[float, float]]:
    """Return a copy of the four fixed activity-group boundaries."""
    return dict(ACTIVITY_GROUP_BOUNDS)


def is_finite_number(value: float) -> bool:
    """Return whether ``value`` is a finite float."""
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def as_serializable_months(months: Sequence[str]) -> List[str]:
    """Return month labels as a plain list for JSON output."""
    return [str(month) for month in months]
