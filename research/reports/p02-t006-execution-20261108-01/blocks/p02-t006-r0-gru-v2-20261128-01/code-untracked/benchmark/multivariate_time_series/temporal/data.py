"""Protocol data adapter: canonical demand identity and stage-scoped arrays.

The adapter reuses the validated P01 loader for node keys, month columns,
nonnegative finite values, duplicate rejection and canonical ascending order.
The canonical training-only RMS scalar and the L6/H3 windows are built here.

The central boundary of this module is that a fit receives **only** training and
validation observations.  :meth:`TemporalData.fit_arrays` slices at the fit
observation boundary (2023-06, month index 30); the four rolling test windows
exist only in :meth:`TemporalData.report_arrays`, which the explicit report
stage calls after selection and diagnostics are frozen.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

from benchmark.nograph_baseline import data as p01_data
from benchmark.nograph_baseline import protocol as p01
from benchmark.nograph_baseline.data import DemandData

from . import protocol


@dataclass(frozen=True)
class FitArrays:
    """Training/validation-only arrays handed to the fitting interface."""

    train_inputs: np.ndarray  # [19, N, 6]
    train_targets: np.ndarray  # [19, N, 3]
    validation_inputs: np.ndarray  # [1, N, 6]
    validation_targets: np.ndarray  # [1, N, 3]
    preprocessing_values: np.ndarray  # [N, 27] float64 training observations
    node_keys: np.ndarray  # int64 [N, K]
    key_columns: Tuple[str, ...]
    observation_months: Tuple[str, ...]
    dataset: str
    mode: str

    @property
    def node_count(self) -> int:
        return int(self.train_inputs.shape[1])

    @property
    def train_starts(self) -> Tuple[int, ...]:
        return tuple(p01.MAIN_SPLIT.train_starts)

    @property
    def validation_starts(self) -> Tuple[int, ...]:
        return tuple(p01.MAIN_SPLIT.validation_starts)

    def assert_no_test_labels(self) -> None:
        """Raise when a fit array contains a test target month or boundary slip."""
        boundary = protocol.fit_observation_month_count()
        expected = tuple(p01.MONTHS[:boundary])
        if tuple(self.observation_months) != expected:
            raise protocol.ProtocolError(
                "fit observations must stop at the last validation month "
                f"{expected[-1]}, got {tuple(self.observation_months)}"
            )
        test_months = {
            month
            for start in p01.MAIN_SPLIT.evaluation_starts
            for month in p01.window_target_months(start)
        }
        leaked = test_months & set(self.observation_months)
        if leaked:
            raise protocol.ProtocolError(
                f"fit arrays contain test target months {sorted(leaked)}"
            )


@dataclass(frozen=True)
class ReportArrays:
    """The four rolling test windows built only by the explicit report stage."""

    test_inputs: np.ndarray  # [4, N, 6]
    test_targets: np.ndarray  # [4, N, 3]
    starts: Tuple[int, ...]
    node_keys: np.ndarray


class TemporalData:
    """Validated demand values plus the stage-scoped array builders."""

    def __init__(self, demand: DemandData):
        protocol.validate_dataset(demand.data_name)
        protocol.validate_mode(demand.mode)
        if demand.signal.shape != (demand.node_count, p01.N_MONTHS):
            raise protocol.ProtocolError(
                f"{demand.data_name}: expected [N, {p01.N_MONTHS}] observations, "
                f"got {demand.signal.shape}"
            )
        self.demand = demand
        self.dataset = demand.data_name
        self.mode = demand.mode
        self.signal = np.ascontiguousarray(demand.signal.astype(np.float64))
        self.node_keys = np.ascontiguousarray(demand.key_array)
        self.key_columns = tuple(demand.key_columns)
        protocol.validate_split()

    # -- identity ----------------------------------------------------------
    @property
    def node_count(self) -> int:
        return int(self.node_keys.shape[0])

    @property
    def keys_sha256(self) -> str:
        return p01_data.node_keys_sha256(self.node_keys)

    def identity(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset,
            "mode": self.mode,
            "key_columns": list(self.key_columns),
            "nodes": self.node_count,
            "months": len(p01.MONTHS),
            "node_keys_sha256": self.keys_sha256,
            "source_path": self.demand.source_path,
            "source_sha256": self.demand.source_sha256,
            "source_kind": (
                "in_memory_fixture"
                if self.demand.source_path.startswith("<")
                else "parquet"
            ),
        }

    def provenance(self) -> Dict[str, Any]:
        """Demand-content identity recorded in provenance and comparison."""
        return self.identity()

    # -- stage-scoped arrays ----------------------------------------------
    def fit_arrays(self) -> FitArrays:
        """Return training/validation arrays only; never the test labels."""
        boundary = protocol.fit_observation_month_count()
        months = tuple(p01.MONTHS[:boundary])
        train_starts = tuple(p01.MAIN_SPLIT.train_starts)
        validation_starts = tuple(p01.MAIN_SPLIT.validation_starts)
        train_inputs = _stack(self.signal, train_starts, 0, p01.INPUT_LENGTH)
        train_targets = _stack(
            self.signal, train_starts, p01.INPUT_LENGTH, p01.HORIZON
        )
        validation_inputs = _stack(
            self.signal, validation_starts, 0, p01.INPUT_LENGTH
        )
        validation_targets = _stack(
            self.signal, validation_starts, p01.INPUT_LENGTH, p01.HORIZON
        )
        arrays = FitArrays(
            train_inputs=train_inputs,
            train_targets=train_targets,
            validation_inputs=validation_inputs,
            validation_targets=validation_targets,
            preprocessing_values=np.ascontiguousarray(
                self.signal[:, : p01.TRAIN_OBSERVATION_MONTH_COUNT]
            ),
            node_keys=self.node_keys.copy(),
            key_columns=self.key_columns,
            observation_months=months,
            dataset=self.dataset,
            mode=self.mode,
        )
        arrays.assert_no_test_labels()
        return arrays

    def report_arrays(self) -> ReportArrays:
        """Build the four rolling test windows (report stage only)."""
        starts = tuple(p01.MAIN_SPLIT.evaluation_starts)
        if starts != (24, 25, 26, 27):
            raise protocol.ProtocolError(
                f"the main split no longer fixes test starts 24..27: {starts}"
            )
        highest = max(start + p01.INPUT_LENGTH + p01.HORIZON for start in starts)
        if highest > self.signal.shape[1]:
            raise protocol.ProtocolError(
                f"test windows need {highest} months, data has {self.signal.shape[1]}"
            )
        return ReportArrays(
            test_inputs=_stack(self.signal, starts, 0, p01.INPUT_LENGTH),
            test_targets=_stack(
                self.signal, starts, p01.INPUT_LENGTH, p01.HORIZON
            ),
            starts=starts,
            node_keys=self.node_keys.copy(),
        )

    # -- preprocessing and masks ------------------------------------------
    def training_rms(self) -> Dict[str, Any]:
        values = self.signal[:, : p01.TRAIN_OBSERVATION_MONTH_COUNT]
        square_sum = float(np.sum(values * values, dtype=np.float64))
        elements = int(values.size)
        scale = protocol.normalization_scale(square_sum, elements)
        return {
            "definition": (
                "s = max(1, sqrt(sum(y[v,t]^2) / (N*27))) over all nodes and the "
                "27 unique training observation months 2021-01..2023-03"
            ),
            "scale": scale,
            "square_sum": square_sum,
            "elements": elements,
            "nodes": self.node_count,
            "months": list(protocol.train_observation_months()),
            "dtype": "float64",
            "input_identity": {
                "dataset": self.dataset,
                "source_sha256": self.demand.source_sha256,
                "node_keys_sha256": self.keys_sha256,
                "train_month_count": p01.TRAIN_OBSERVATION_MONTH_COUNT,
            },
        }

    def training_masks(self) -> Dict[str, np.ndarray]:
        """Training-period activity and constant masks from observed demand."""
        values = self.signal[:, : p01.TRAIN_OBSERVATION_MONTH_COUNT]
        activity = (values > 0).mean(axis=1).astype(np.float64)
        groups = p01_data.activity_group_masks(activity)
        constant = values.std(axis=1, ddof=0) == 0
        masks: Dict[str, np.ndarray] = {
            f"activity_{name}": np.ascontiguousarray(mask)
            for name, mask in groups.items()
        }
        masks["nonzero_activity_train27"] = activity
        masks["constant_train27"] = np.ascontiguousarray(constant)
        masks["nonconstant_train27"] = np.ascontiguousarray(~constant)
        return masks

    def context_values(self) -> np.ndarray:
        """Return the first context id per node (single-context schemas only)."""
        if self.node_keys.shape[1] < 2:
            raise protocol.ProtocolError("node keys need a context id and skill_id")
        return self.node_keys[:, 0]


def _stack(
    signal: np.ndarray, starts: Sequence[int], offset: int, width: int
) -> np.ndarray:
    return np.ascontiguousarray(
        np.stack(
            [signal[:, start + offset : start + offset + width] for start in starts]
        ).astype(np.float64)
    )


def load_temporal_data(
    data_name: str,
    *,
    mode: str = "count",
    demand_path: Optional[Path] = None,
    months: Optional[Sequence[str]] = None,
) -> TemporalData:
    """Load and validate a demand Parquet table for the P02 entry."""
    protocol.validate_dataset(data_name)
    protocol.validate_mode(mode)
    demand = p01_data.load_demand(
        data_name, mode=mode, demand_path=demand_path, months=months
    )
    return TemporalData(demand)


def from_arrays(
    data_name: str,
    keys: Sequence[Sequence[int]],
    signal: np.ndarray,
    *,
    mode: str = "count",
    source_path: str = "<in-memory fixture>",
    source_sha256: str = "in-memory",
) -> TemporalData:
    """Build validated values in memory (fixtures only, never formal data)."""
    protocol.validate_dataset(data_name)
    protocol.validate_mode(mode)
    demand = p01_data.from_arrays(
        data_name,
        keys,
        signal,
        mode=mode,
        source_path=source_path,
        source_sha256=source_sha256,
    )
    return TemporalData(demand)


def naive_validation_baselines(arrays: FitArrays) -> Dict[str, Any]:
    """Compute the five P01 naive baselines over the validation window only.

    Everything is derived from training/validation observations, so the fit
    stage can save the Zero comparison without ever constructing a test window.
    """
    from benchmark.nograph_baseline import metrics as p01_metrics

    inputs = np.asarray(arrays.validation_inputs, dtype=np.float64)
    targets = np.asarray(arrays.validation_targets, dtype=np.float64)
    observations = np.asarray(arrays.preprocessing_values, dtype=np.float64)
    start = int(arrays.validation_starts[0])
    seasonal_begin = start + p01.INPUT_LENGTH - 12
    if seasonal_begin < 0:
        raise protocol.ProtocolError(
            "SeasonalNaive12 needs twelve months of history before the validation "
            f"window; start {start} would begin at {seasonal_begin}"
        )
    train_mean27 = observations.mean(axis=1, keepdims=True)
    predictions = {
        "Zero": np.zeros_like(targets),
        "LastValue": np.repeat(inputs[:, :, -1:], p01.HORIZON, axis=2),
        "WindowMean6": np.repeat(inputs.mean(axis=2, keepdims=True), p01.HORIZON, axis=2),
        "TrainMean27": np.broadcast_to(train_mean27[None, :, :], targets.shape),
        "SeasonalNaive12": observations[
            None, :, seasonal_begin : seasonal_begin + p01.HORIZON
        ],
    }
    scores: Dict[str, Any] = {}
    for name, prediction in predictions.items():
        record = p01_metrics.error_metrics(prediction, targets)
        scores[name] = {
            "MSE": float(record["MSE"]),
            "MAE": float(record["MAE"]),
            "elements": int(record["elements"]),
        }
    return {
        "stage": "fit",
        "test_labels_used": False,
        "split": "validation",
        "starts": list(arrays.validation_starts),
        "validation_target_months": list(
            p01.MAIN_SPLIT.target_months_for("validation")
        ),
        "information_budget": {
            "SeasonalNaive12": "twelve months of pre-window history",
        },
        "scores": scores,
    }
