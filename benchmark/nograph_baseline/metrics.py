"""Pure original-unit metric reductions and fixed-mask reporting.

Arrays are ``[windows, nodes, horizon]``.  Error arithmetic widens predictions
and labels to ``float64`` before reduction, matching the sealed v2 diagnostic.
Each reported group uses exactly the same saved mask for every method, and
empty groups are reported as explicit JSON ``null`` metrics rather than NaN.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from . import protocol

EMPTY_STATUS = "empty"
OK_STATUS = "ok"
UNAVAILABLE_STATUS = "unavailable"


def _reduce(
    absolute_sum: float,
    squared_sum: float,
    elements: int,
    negative_count: int,
) -> Dict[str, Any]:
    """Reduce error sums into the reporting record."""
    if elements <= 0:
        return {
            "MAE": None,
            "MSE": None,
            "RMSE": None,
            "negative_prediction_ratio": None,
            "elements": 0,
            "absolute_error_sum": 0.0,
            "squared_error_sum": 0.0,
            "status": EMPTY_STATUS,
        }
    mse = squared_sum / elements
    return {
        "MAE": absolute_sum / elements,
        "MSE": mse,
        "RMSE": float(np.sqrt(mse)),
        "negative_prediction_ratio": negative_count / elements,
        "elements": int(elements),
        "absolute_error_sum": float(absolute_sum),
        "squared_error_sum": float(squared_sum),
        "status": OK_STATUS,
    }


def error_metrics(pred: np.ndarray, gold: np.ndarray) -> Dict[str, Any]:
    """Return MAE/MSE/RMSE and negative ratio for aligned arrays."""
    p = np.asarray(pred)
    g = np.asarray(gold)
    if p.shape != g.shape:
        raise ValueError(f"prediction shape {p.shape} != gold shape {g.shape}")
    error = p.astype(np.float64) - g.astype(np.float64)
    absolute = np.abs(error)
    squared = np.square(error)
    return _reduce(
        float(absolute.sum()),
        float(squared.sum()),
        int(error.size),
        int((p < 0).sum()),
    )


def adds_error_contributions(
    record: Dict[str, Any], global_absolute: float, global_squared: float
) -> Dict[str, Any]:
    """Annotate a group record with its share of the global error sums."""
    if global_absolute > 0:
        record["absolute_error_contribution_fraction"] = (
            record["absolute_error_sum"] / global_absolute
        )
    else:
        record["absolute_error_contribution_fraction"] = None
    if global_squared > 0:
        record["squared_error_contribution_fraction"] = (
            record["squared_error_sum"] / global_squared
        )
    else:
        record["squared_error_contribution_fraction"] = None
    return record


def window_metrics(
    pred: np.ndarray, gold: np.ndarray, starts: Sequence[int]
) -> List[Dict[str, Any]]:
    """Return per-window metrics with forecast origin and target months."""
    records = []
    for index, start in enumerate(starts):
        record = error_metrics(pred[index], gold[index])
        record["start"] = int(start)
        record["forecast_origin"] = protocol.window_forecast_origin(start)
        record["target_months"] = list(protocol.window_target_months(start))
        records.append(record)
    return records


def horizon_metrics(pred: np.ndarray, gold: np.ndarray) -> Dict[str, Dict[str, Any]]:
    """Return per-horizon metrics keyed ``h1``..``hH``."""
    return {
        f"h{horizon + 1}": error_metrics(pred[:, :, horizon], gold[:, :, horizon])
        for horizon in range(pred.shape[2])
    }


def masked_group_metrics(
    pred: np.ndarray,
    gold: np.ndarray,
    masks: Mapping[str, np.ndarray],
    *,
    global_absolute: Optional[float] = None,
    global_squared: Optional[float] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return metrics per boolean node mask, using the same slices for all."""
    reports: Dict[str, Dict[str, Any]] = {}
    for name, mask in masks.items():
        node_mask = np.asarray(mask, dtype=bool)
        record = error_metrics(pred[:, node_mask, :], gold[:, node_mask, :])
        record["nodes"] = int(node_mask.sum())
        if global_absolute is not None and global_squared is not None:
            adds_error_contributions(record, global_absolute, global_squared)
        reports[name] = record
    return reports


def balanced_activity_mae(
    activity_reports: Mapping[str, Mapping[str, Any]],
    group_names: Sequence[str] = protocol.ACTIVITY_GROUP_NAMES,
) -> Dict[str, Any]:
    """Average nonempty activity-group MAEs, excluding empty groups."""
    values = [
        float(activity_reports[name]["MAE"])
        for name in group_names
        if name in activity_reports
        and activity_reports[name]["status"] == OK_STATUS
        and activity_reports[name]["MAE"] is not None
    ]
    excluded = [
        name
        for name in group_names
        if name in activity_reports
        and activity_reports[name]["status"] != OK_STATUS
    ]
    return {
        "balanced_activity_group_MAE": float(np.mean(values)) if values else None,
        "nonempty_groups": [
            name
            for name in group_names
            if name in activity_reports
            and activity_reports[name]["status"] == OK_STATUS
        ],
        "excluded_empty_groups": excluded,
        "status": OK_STATUS if values else EMPTY_STATUS,
    }


def relative_gain(
    value: Optional[float], reference: Optional[float]
) -> Dict[str, Any]:
    """Return the protocol relative gain ``(ref - value) / ref``.

    A zero or unavailable reference yields a null gain with an explicit reason;
    the protocol forbids claiming improvement on MAE when the reference is 0.
    """
    if value is None or reference is None:
        return {
            "MAE": value,
            "reference_MAE": reference,
            "relative_MAE_gain": None,
            "status": UNAVAILABLE_STATUS,
            "reason": "MAE is unavailable for this group or reference",
        }
    reference = float(reference)
    value = float(value)
    if reference == 0.0:
        return {
            "MAE": value,
            "reference_MAE": reference,
            "relative_MAE_gain": None,
            "status": UNAVAILABLE_STATUS,
            "reason": "reference MAE is zero; the protocol does not define this gain",
        }
    return {
        "MAE": value,
        "reference_MAE": reference,
        "absolute_MAE_difference": reference - value,
        "relative_MAE_gain": (reference - value) / reference,
        "status": OK_STATUS,
    }


def _gain_block(
    model_reports: Mapping[str, Mapping[str, Any]],
    reference_reports: Mapping[str, Mapping[str, Any]],
    names: Iterable[str],
) -> Dict[str, Dict[str, Any]]:
    gains: Dict[str, Dict[str, Any]] = {}
    for name in names:
        model = model_reports.get(name)
        reference = reference_reports.get(name)
        if model is None or reference is None:
            continue
        gains[name] = relative_gain(model.get("MAE"), reference.get("MAE"))
    return gains


def baseline_relative_comparison(
    reports: Mapping[str, Mapping[str, Any]],
    *,
    activity_groups: Sequence[str] = protocol.ACTIVITY_GROUP_NAMES,
    context_names: Sequence[str],
    neighbor_names: Sequence[str],
    model_names: Sequence[str],
    reference_names: Sequence[str],
) -> Dict[str, Any]:
    """Build relative MAE gains for model outputs against frozen references."""
    comparison: Dict[str, Any] = {}
    for model in model_names:
        if model not in reports:
            continue
        entry: Dict[str, Any] = {}
        for reference in reference_names:
            if reference not in reports:
                continue
            model_report = reports[model]
            reference_report = reports[reference]
            entry[reference] = {
                "overall": relative_gain(
                    model_report.get("MAE"), reference_report.get("MAE")
                ),
                "activity_groups": _gain_block(
                    model_report.get("activity_groups", {}),
                    reference_report.get("activity_groups", {}),
                    activity_groups,
                ),
                "contexts": _gain_block(
                    model_report.get("contexts", {}),
                    reference_report.get("contexts", {}),
                    context_names,
                ),
                "neighbor_groups": _gain_block(
                    model_report.get("neighbor_groups", {}),
                    reference_report.get("neighbor_groups", {}),
                    neighbor_names,
                ),
                "windows": _gain_block(
                    {
                        str(row["start"]): row
                        for row in model_report.get("windows", [])
                    },
                    {
                        str(row["start"]): row
                        for row in reference_report.get("windows", [])
                    },
                    [str(row["start"]) for row in model_report.get("windows", [])],
                ),
            }
        comparison[model] = entry
    return comparison


def constant_group_masks(constant_mask: np.ndarray) -> Dict[str, np.ndarray]:
    """Return the constant / nonconstant diagnostic masks."""
    constant = np.asarray(constant_mask, dtype=bool)
    return {"constant_train27": constant, "nonconstant_train27": ~constant}


def neighbor_group_masks(neighbor_mask: np.ndarray) -> Dict[str, np.ndarray]:
    """Return the has-neighbor / no-neighbor evaluation masks."""
    covered = np.asarray(neighbor_mask, dtype=bool)
    return {
        "has_nonself_neighbor": covered,
        "no_nonself_neighbor": ~covered,
    }


def context_masks(context_values: np.ndarray) -> Dict[str, np.ndarray]:
    """Return one mask per distinct context value, keyed by its string form."""
    values = np.asarray(context_values)
    masks: Dict[str, np.ndarray] = {}
    for value in np.unique(values):
        masks[str(value)] = values == value
    return masks


def node_error_table(
    pred: np.ndarray,
    gold: np.ndarray,
    *,
    method: str,
    split: str,
    node_keys: np.ndarray,
    key_columns: Sequence[str],
    train_mean27_values: np.ndarray,
    context_values: np.ndarray,
) -> "Any":
    """Build the complete per-node error contribution table.

    Rows are ordered by descending training mean with ties broken by the
    canonical ascending node key, so a large-demand audit needs no invented
    threshold.
    """
    import pandas as pd

    error = np.asarray(pred).astype(np.float64) - np.asarray(gold).astype(np.float64)
    absolute = np.abs(error).sum(axis=(0, 2))
    squared = np.square(error).sum(axis=(0, 2))
    elements = error.shape[0] * error.shape[2]
    node_count = error.shape[1]
    frame = pd.DataFrame(node_keys, columns=list(key_columns))
    frame["node_index"] = np.arange(node_count, dtype=np.int64)
    frame["method"] = method
    frame["split"] = split
    frame["context"] = np.asarray(context_values, dtype=np.int64)
    frame["train_mean27"] = np.asarray(train_mean27_values, dtype=np.float64)
    frame["absolute_error_sum"] = absolute
    frame["squared_error_sum"] = squared
    frame["elements"] = int(elements)
    frame["MAE"] = absolute / elements
    frame["MSE"] = squared / elements
    frame = frame.sort_values(
        ["method", "split", "train_mean27", *key_columns],
        ascending=[True, True, False] + [True] * len(key_columns),
        kind="stable",
    ).reset_index(drop=True)
    return frame


def combine_node_error_tables(frames: Sequence["Any"]) -> "Any":
    """Concatenate per-method node error tables in a stable order."""
    import pandas as pd

    if not frames:
        return pd.DataFrame()
    return pd.concat(list(frames), ignore_index=True)


def split_report(
    pred: np.ndarray,
    gold: np.ndarray,
    *,
    starts: Sequence[int],
    activity_masks: Mapping[str, np.ndarray],
    constant_masks: Mapping[str, np.ndarray],
    context_masks_map: Mapping[str, np.ndarray],
    neighbor_masks: Mapping[str, np.ndarray],
    group_names: Sequence[str] = protocol.ACTIVITY_GROUP_NAMES,
) -> Dict[str, Any]:
    """Compute every required report level for one method and split."""
    overall = error_metrics(pred, gold)
    global_absolute = overall["absolute_error_sum"]
    global_squared = overall["squared_error_sum"]
    activity = masked_group_metrics(
        pred,
        gold,
        activity_masks,
        global_absolute=global_absolute,
        global_squared=global_squared,
    )
    constant = masked_group_metrics(
        pred,
        gold,
        constant_masks,
        global_absolute=global_absolute,
        global_squared=global_squared,
    )
    contexts = masked_group_metrics(
        pred,
        gold,
        context_masks_map,
        global_absolute=global_absolute,
        global_squared=global_squared,
    )
    neighbors = masked_group_metrics(
        pred,
        gold,
        neighbor_masks,
        global_absolute=global_absolute,
        global_squared=global_squared,
    )
    report: Dict[str, Any] = dict(overall)
    report["activity_groups"] = activity
    report["constant_groups"] = constant
    report["contexts"] = contexts
    report["neighbor_groups"] = neighbors
    report["training_all_zero_group"] = {
        "group": "inactive",
        "nodes": activity.get("inactive", {}).get("nodes", 0),
        **{
            key: activity.get("inactive", {}).get(key)
            for key in ("MAE", "MSE", "RMSE", "status")
        },
    }
    report.update(balanced_activity_mae(activity, group_names))
    report["windows"] = window_metrics(pred, gold, starts)
    report["horizons"] = horizon_metrics(pred, gold)
    report["target_month_multiplicities"] = target_month_multiplicities(starts)
    report["aggregation_note"] = (
        "overall RMSE is sqrt(MSE over all window-node-horizon elements), "
        "not the mean of window RMSE values"
    )
    return report


def target_month_multiplicities(starts: Sequence[int]) -> Dict[str, int]:
    """Return how many test windows target each month (1,2,3,3,2,1)."""
    counts: Dict[str, int] = {}
    for start in starts:
        for month in protocol.window_target_months(start):
            counts[month] = counts.get(month, 0) + 1
    return counts
