"""Explicit four-window test reporting.

The report stage runs only after the selection and validation diagnostics are
frozen.  It restores the selected best weights, freezes preprocessing and
parameters, evaluates all four rolling test windows 24..27 with L6/H3 true
observed history and aggregates every metric over all ``4*N*3`` elements.
Nothing here can select a learning rate, checkpoint, seed, clip rule or
readiness state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

from benchmark.nograph_baseline import baselines as p01_baselines
from benchmark.nograph_baseline import coverage as p01_coverage
from benchmark.nograph_baseline import metrics as p01_metrics
from benchmark.nograph_baseline import protocol as p01

from . import model as temporal_model
from . import protocol

AGGREGATION_NOTE = (
    "overall RMSE is sqrt(MSE over all 4*N*3 test elements), not the mean of "
    "window RMSE values"
)


class ReportError(protocol.ProtocolError):
    """Raised when a report request cannot be honoured."""


def predict_test(
    best_payload: Mapping[str, Any],
    config: protocol.FitConfig,
    inputs: np.ndarray,
    scale: float,
) -> np.ndarray:
    """Restore the selected weights and predict the four test windows."""
    model = temporal_model.build_model(config)
    state = best_payload.get("model_state")
    if not isinstance(state, Mapping):
        raise ReportError("the selected checkpoint has no model_state")
    model.load_state_dict({name: tensor for name, tensor in state.items()})
    model.eval()
    prediction, _ = temporal_model.predict(
        model, inputs, float(scale), config.node_chunk
    )
    return prediction


def coverage_masks(
    data_name: str,
    key_array: np.ndarray,
    *,
    graph_path: Optional[Path] = None,
    mask_bundle: Optional[Path] = None,
) -> Optional[p01_coverage.CoverageMask]:
    """Load validated coverage evidence, or return ``None`` when absent."""
    if graph_path is None and mask_bundle is None:
        return None
    if graph_path is not None and mask_bundle is not None:
        raise ReportError("supply either a raw graph table or a mask bundle, not both")
    if graph_path is not None:
        return p01_coverage.load_graph_coverage(
            data_name, key_array, graph_path=Path(graph_path)
        )
    return p01_coverage.load_mask_bundle(
        Path(mask_bundle), data_name, key_array
    )


def build_report(
    *,
    prediction: np.ndarray,
    gold: np.ndarray,
    starts: Sequence[int],
    key_array: np.ndarray,
    activity_masks: Mapping[str, np.ndarray],
    constant_masks: Mapping[str, np.ndarray],
    coverage: Optional[np.ndarray],
    coverage_provenance: Optional[Mapping[str, Any]],
    scale: float,
    protocol_complete: bool,
    purpose: str,
) -> Dict[str, Any]:
    """Aggregate raw and separately-labelled clipped test metrics."""
    prediction = np.asarray(prediction, dtype=np.float64)
    gold = np.asarray(gold, dtype=np.float64)
    expected = (len(starts), key_array.shape[0], p01.HORIZON)
    if prediction.shape != expected or gold.shape != expected:
        raise ReportError(
            f"test arrays must be {expected} for four windows, got "
            f"{prediction.shape} and {gold.shape}"
        )
    activity = {
        name[len("activity_"):]: mask
        for name, mask in activity_masks.items()
        if name.startswith("activity_")
    }
    overall = p01_metrics.error_metrics(prediction, gold)
    global_absolute = overall["absolute_error_sum"]
    global_squared = overall["squared_error_sum"]
    contexts = p01_metrics.context_masks(key_array[:, 0])
    neighbor_report: Dict[str, Any]
    if coverage is None:
        neighbor_report = {
            "has_nonself_neighbor": {
                "status": "unavailable",
                "reason": (
                    "no context-qualified coverage evidence was supplied; missing "
                    "coverage is never converted into an all-isolated mask"
                ),
            },
            "no_nonself_neighbor": {
                "status": "unavailable",
                "reason": (
                    "no context-qualified coverage evidence was supplied; missing "
                    "coverage is never converted into an all-isolated mask"
                ),
            },
            "coverage_available": False,
        }
    else:
        neighbor_masks = p01_coverage.coverage_groups(coverage)
        neighbor_report = p01_metrics.masked_group_metrics(
            prediction,
            gold,
            neighbor_masks,
            global_absolute=global_absolute,
            global_squared=global_squared,
        )
        neighbor_report["coverage_available"] = True
    metrics: Dict[str, Any] = dict(overall)
    metrics["activity_groups"] = p01_metrics.masked_group_metrics(
        prediction,
        gold,
        activity,
        global_absolute=global_absolute,
        global_squared=global_squared,
    )
    metrics["constant_groups"] = p01_metrics.masked_group_metrics(
        prediction,
        gold,
        constant_masks,
        global_absolute=global_absolute,
        global_squared=global_squared,
    )
    metrics["contexts"] = p01_metrics.masked_group_metrics(
        prediction,
        gold,
        contexts,
        global_absolute=global_absolute,
        global_squared=global_squared,
    )
    metrics["neighbor_groups"] = neighbor_report
    metrics.update(
        p01_metrics.balanced_activity_mae(
            metrics["activity_groups"], tuple(activity.keys())
        )
    )
    metrics["windows"] = p01_metrics.window_metrics(prediction, gold, starts)
    metrics["horizons"] = p01_metrics.horizon_metrics(prediction, gold)
    metrics["target_month_multiplicities"] = p01_metrics.target_month_multiplicities(
        starts
    )
    metrics["aggregation_note"] = AGGREGATION_NOTE
    metrics["sample_counts"] = {
        "windows": int(len(starts)),
        "nodes": int(key_array.shape[0]),
        "horizon": int(p01.HORIZON),
        "elements": int(prediction.size),
        "per_window_elements": int(key_array.shape[0] * p01.HORIZON),
    }
    metrics["negative_prediction_ratio"] = p01_baselines.negative_ratio(prediction)
    clipped_prediction = np.maximum(prediction, 0.0)
    clipped = p01_metrics.error_metrics(clipped_prediction, gold)
    clipped["label"] = "clipped_nonnegative"
    clipped["definition"] = "prediction_clipped = max(prediction, 0)"
    clipped["used_for_selection"] = False
    clipped["negative_prediction_ratio_before_clip"] = metrics[
        "negative_prediction_ratio"
    ]
    clipped["negative_prediction_ratio_after_clip"] = p01_baselines.negative_ratio(
        clipped_prediction
    )
    return {
        "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
        "scientific_version": protocol.SCIENTIFIC_VERSION,
        "kind": "test-report",
        "purpose": purpose,
        "protocol_complete": bool(protocol_complete),
        "status": "complete" if protocol_complete else "development_incomplete",
        "preprocessing": {
            "scale": float(scale),
            "definition": "training-only RMS scalar; frozen before reporting",
            "per_node_scaling": False,
        },
        "test_windows": {
            "starts": [int(start) for start in starts],
            "input_months": [list(p01.window_input_months(int(start))) for start in starts],
            "target_months": [list(p01.window_target_months(int(start))) for start in starts],
            "forecast_origins": [p01.window_forecast_origin(int(start)) for start in starts],
            "input_length": p01.INPUT_LENGTH,
            "horizon": p01.HORIZON,
            "array_shape": list(prediction.shape),
            "target_month_multiplicities": metrics["target_month_multiplicities"],
            "true_observed_history": True,
        },
        "metrics": metrics,
        "clipped_nonnegative": clipped,
        "coverage": dict(coverage_provenance) if coverage_provenance else {
            "available": False,
            "reason": "no coverage evidence supplied",
        },
        "test_scores_used_for_selection": False,
        "note": (
            "test scores are descriptive only; they never select a learning rate, "
            "checkpoint, seed, clip rule or readiness state"
        ),
    }


def formal_report_blockers(
    *,
    purpose: str,
    config: protocol.FitConfig,
    selection: Mapping[str, Any],
    diagnostics: Optional[Mapping[str, Any]],
    run_dir: Path,
    a_states: Mapping[int, str],
    b_states: Mapping[int, str],
    winner_run_dir: Optional[Path],
    run_evidence_sha256: Optional[str] = None,
) -> List[str]:
    """Return every reason a *formal* test report must be refused."""
    blockers: List[str] = []
    if purpose != "formal":
        return blockers
    deviations = config.deviations()
    if deviations:
        blockers.append(
            "formal reporting requires complete protocol controls: "
            + ", ".join(deviations)
        )
    if selection.get("status") != "frozen" or not selection.get("frozen"):
        blockers.append(
            f"selection is not frozen (status {selection.get('status')!r})"
        )
    winner = selection.get("winner") or {}
    if not winner:
        blockers.append("selection has no winning candidate")
    elif winner.get("learning_rate") != config.learning_rate:
        blockers.append("trajectory learning rate differs from the frozen winner")
    if selection.get("model") != config.model:
        blockers.append("trajectory encoder differs from the frozen selection")
    members = []
    for role in ("a_runs", "b_runs"):
        entry = ((diagnostics or {}).get("inputs") or {}).get(role, {}).get(str(config.seed))
        if entry and entry.get("run_dir") and Path(entry["run_dir"]).resolve() == Path(run_dir).resolve():
            members.append(entry)
    if len(members) != 1:
        blockers.append("trajectory is not a unique required seed/repetition in frozen diagnostics")
    else:
        member = members[0]
        if member.get("config") != config.to_payload():
            blockers.append("trajectory effective configuration differs from frozen diagnostics")
        if not member.get("evidence_sha256") or (run_evidence_sha256 is not None and member["evidence_sha256"] != run_evidence_sha256):
            blockers.append("trajectory evidence differs from frozen diagnostics")
    if diagnostics is None:
        blockers.append("validation diagnostics evidence is missing")
    else:
        if diagnostics.get("status") != "pass":
            blockers.append(
                f"validation diagnostics status is {diagnostics.get('status')!r}; "
                "formal reporting needs all section-5 gates to pass"
            )
        if not diagnostics.get("learning_ready"):
            blockers.append(
                "learning_ready is false; formal reporting requires all section-5 "
                "gates"
            )
        if diagnostics.get("selection_sha256") != selection.get("selection_sha256"):
            blockers.append(
                "diagnostics were computed against a different frozen selection"
            )
    if diagnostics is not None:
        summary = diagnostics.get("summary") or {}
        if summary.get("complete_comparison") is not True:
            blockers.append(
                "validation repetition evidence is incomplete; formal reporting "
                "requires every a/b pair"
            )
    missing_a = [seed for seed in protocol.SEEDS if a_states.get(seed) != "completed"]
    missing_b = [seed for seed in protocol.SEEDS if b_states.get(seed) != "completed"]
    if missing_a:
        blockers.append(f"missing completed repetition a for seeds {missing_a}")
    if missing_b:
        blockers.append(f"missing completed repetition b for seeds {missing_b}")
    return blockers
