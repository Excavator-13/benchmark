"""The five protocol na\"ive baselines and frozen reference selection.

The arithmetic here intentionally matches the sealed v2 diagnostic:
demand signals and na\"ive predictions stay ``float32`` and only the error
arrays are widened to ``float64``.  This is what makes the new entry's na\"ive
metrics align with ``research/runs/phase1-20261006-v2-01/naive-baselines.log``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np

from . import protocol


def train_mean27(signal: np.ndarray) -> np.ndarray:
    """Return the frozen per-node mean over the 27 training observations.

    Computed with ``float32`` accumulation, exactly as in the v2 diagnostic, so
    ``TrainMean27`` predictions reproduce the sealed log.
    """
    values = np.asarray(signal)
    if values.ndim != 2 or values.shape[1] != protocol.N_MONTHS:
        raise ValueError(
            f"signal must have shape [N, {protocol.N_MONTHS}], got {values.shape}"
        )
    return values[:, :protocol.TRAIN_OBSERVATION_MONTH_COUNT].mean(axis=1, keepdims=True)


def naive_predictions(
    signal: np.ndarray,
    starts: Sequence[int],
    *,
    frozen_train_mean: np.ndarray | None = None,
) -> Dict[str, np.ndarray]:
    """Return all five na\"ive predictions as ``[windows, nodes, H]`` arrays."""
    values = np.asarray(signal)
    offset = protocol.INPUT_LENGTH
    horizon = protocol.HORIZON
    x = np.stack([values[:, start : start + offset] for start in starts])
    gold = np.stack(
        [values[:, start + offset : start + offset + horizon] for start in starts]
    )
    if frozen_train_mean is None:
        frozen_train_mean = train_mean27(values)
    predictions: Dict[str, np.ndarray] = {
        "Zero": np.zeros_like(gold),
        "LastValue": np.repeat(x[:, :, -1:], horizon, axis=2),
        "WindowMean6": np.repeat(x.mean(axis=2, keepdims=True), horizon, axis=2),
        "TrainMean27": np.broadcast_to(
            np.asarray(frozen_train_mean)[None, :, :], gold.shape
        ),
        "SeasonalNaive12": np.stack(
            [
                values[
                    :,
                    start + offset - 12 : start + offset - 12 + horizon,
                ]
                for start in starts
            ]
        ),
    }
    return predictions


def validation_mse(
    predictions: Mapping[str, np.ndarray], gold: np.ndarray
) -> Dict[str, float]:
    """Return per-method original-unit validation MSE (float64 reduction)."""
    return {
        name: mse(pred, gold) for name, pred in predictions.items()
    }


def mse(pred: np.ndarray, gold: np.ndarray) -> float:
    """Mean squared error with the v2 float64 error arithmetic."""
    error = pred.astype(np.float64) - gold.astype(np.float64)
    return float(np.square(error).mean())


def mae(pred: np.ndarray, gold: np.ndarray) -> float:
    """Mean absolute error with the v2 float64 error arithmetic."""
    error = pred.astype(np.float64) - gold.astype(np.float64)
    return float(np.abs(error).mean())


def select_references(
    scores: Mapping[str, float],
    *,
    order: Sequence[str] = protocol.NAIVE_METHODS,
    ref6_candidates: Sequence[str] = protocol.NAIVE_REF6_METHODS,
) -> Dict[str, Any]:
    """Select ``NaiveRef``/``NaiveRef6`` by validation MSE with table-order ties."""
    missing = [name for name in order if name not in scores]
    if missing:
        raise ValueError(f"missing validation MSE for {missing}")

    def choose(names: Sequence[str]) -> Tuple[str, List[Dict[str, Any]]]:
        table = [
            {
                "method": name,
                "validation_MSE": float(scores[name]),
                "table_order": list(order).index(name),
            }
            for name in names
        ]
        table.sort(key=lambda row: (row["validation_MSE"], row["table_order"]))
        winner = table[0]
        tied = [
            row["method"]
            for row in table
            if row["validation_MSE"] == winner["validation_MSE"]
        ]
        return winner["method"], table, tied

    naive_ref, ref_table, ref_ties = choose(order)
    naive_ref6, ref6_table, ref6_ties = choose(ref6_candidates)
    extra_history = {
        "SeasonalNaive12": "extra 12-month history",
    }
    return {
        "selection_metric": "validation MSE",
        "table_order": list(order),
        "NaiveRef": naive_ref,
        "NaiveRef6": naive_ref6,
        "NaiveRef_uses_extra_history": naive_ref == "SeasonalNaive12",
        "NaiveRef6_uses_extra_history": naive_ref6 == "SeasonalNaive12",
        "validation_MSE_table": ref_table,
        "NaiveRef_ties": ref_ties,
        "NaiveRef6_validation_MSE_table": ref6_table,
        "NaiveRef6_ties": ref6_ties,
        "information_budget": extra_history,
        "SeasonalNaive12_excluded_from_NaiveRef6": True,
        "frozen_before_test_evaluation": True,
    }


def negative_ratio(pred: np.ndarray) -> float:
    """Return ``count(pred < 0) / element_count``."""
    values = np.asarray(pred)
    return float((values < 0).sum()) / float(values.size) if values.size else 0.0
