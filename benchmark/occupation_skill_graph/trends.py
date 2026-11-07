"""Diagnostic occupational trend correlations on selected shared edges.

For every retained shared edge and every source occupation the audit forms the
26 first differences of the 27 training months.  Pearson correlation is
reported only when both endpoints have at least 12 positive-demand months and
both difference variances are nonzero.  Otherwise the value is JSON ``null``
with ``history_insufficient`` or ``constant_difference`` reason, with
insufficient history taking priority.  Correlations never alter graph edges,
weights or candidate selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import protocol
from .data import array_sha256
from .structure import distribution_summary

__all__ = [
    "TrendError",
    "TrendResult",
    "compute_trends",
    "candidate_trend_summary",
    "trend_payload_hashes",
]

REASON_INSUFFICIENT = "history_insufficient"
REASON_CONSTANT = "constant_difference"


class TrendError(ValueError):
    """Raised when trend inputs violate the diagnostic contract."""


@dataclass
class TrendResult:
    """Per-union-edge trend diagnostics and their aggregate summary."""

    observations_shape: Tuple[int, int, int]
    edge_index: np.ndarray
    eligible_counts: np.ndarray
    insufficient_counts: np.ndarray
    constant_counts: np.ndarray
    reason_codes: np.ndarray
    positive_counts: np.ndarray
    zero_counts: np.ndarray
    negative_counts: np.ndarray
    common_zero_months: np.ndarray
    common_zero_fraction: np.ndarray
    mean_context_common_zero_fraction: np.ndarray
    correlation_min: np.ndarray
    correlation_max: np.ndarray
    correlation_mean: np.ndarray
    correlation_median: np.ndarray
    correlation_std: np.ndarray
    global_summary: Dict[str, Any]
    graph_payload_sha256: Dict[str, str]

    @property
    def n_edges(self) -> int:
        return int(self.edge_index.shape[0])

    def arrays(self) -> Dict[str, np.ndarray]:
        return {
            "trend_edge_index": self.edge_index,
            "trend_eligible_counts": self.eligible_counts,
            "trend_insufficient_counts": self.insufficient_counts,
            "trend_constant_counts": self.constant_counts,
            "trend_reason_codes": self.reason_codes,
            "trend_positive_counts": self.positive_counts,
            "trend_zero_counts": self.zero_counts,
            "trend_negative_counts": self.negative_counts,
            "trend_common_zero_months": self.common_zero_months,
            "trend_common_zero_fraction": self.common_zero_fraction,
            "trend_mean_context_common_zero_fraction": (
                self.mean_context_common_zero_fraction
            ),
            "trend_correlation_min": self.correlation_min,
            "trend_correlation_max": self.correlation_max,
            "trend_correlation_mean": self.correlation_mean,
            "trend_correlation_median": self.correlation_median,
            "trend_correlation_std": self.correlation_std,
        }

    def identity_hashes(self) -> Dict[str, str]:
        return {name: array_sha256(value) for name, value in self.arrays().items()}


def _correlation_block(
    feature_a: np.ndarray, feature_b: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Return Pearson r and squared-norm products for [B, D] blocks."""
    centered_a = feature_a - feature_a.mean(axis=1, keepdims=True)
    centered_b = feature_b - feature_b.mean(axis=1, keepdims=True)
    sum_a = np.einsum("ij,ij->i", centered_a, centered_a)
    sum_b = np.einsum("ij,ij->i", centered_b, centered_b)
    numerator = np.einsum("ij,ij->i", centered_a, centered_b)
    product = sum_a * sum_b
    result = np.full(numerator.shape, np.nan, dtype=np.float64)
    computable = product > 0
    result[computable] = numerator[computable] / np.sqrt(product[computable])
    result = np.clip(result, -1.0, 1.0)
    return result, product


def compute_trends(
    observations: np.ndarray,
    edge_index: np.ndarray,
    *,
    min_positive_months: int = protocol.MIN_POSITIVE_MONTHS,
    block_size: int = protocol.TREND_BLOCK_SIZE,
    progress: Optional[Any] = None,
) -> TrendResult:
    """Compute per-edge/per-occupation diagnostic correlations blockwise."""
    values = np.asarray(observations, dtype=np.float64)
    if values.ndim != 3 or values.shape[2] != protocol.N_TRAIN_MONTHS:
        raise TrendError(
            f"observations must have shape [C, S, {protocol.N_TRAIN_MONTHS}], "
            f"got {values.shape}"
        )
    if not np.isfinite(values).all() or (values < 0).any():
        raise TrendError("observations must be finite and nonnegative")
    edges = np.ascontiguousarray(np.asarray(edge_index, dtype=np.int64).reshape(-1, 2))
    if edges.size and (edges[:, 0] >= edges[:, 1]).any():
        raise TrendError("trend edges must be canonical ordered pairs")
    n_contexts = int(values.shape[0])
    n_edges = int(edges.shape[0])
    eligible = np.zeros(n_edges, dtype=np.int64)
    insufficient = np.zeros(n_edges, dtype=np.int64)
    constant = np.zeros(n_edges, dtype=np.int64)
    reason_codes = np.zeros((n_edges, n_contexts), dtype=np.int8)
    positive = np.zeros(n_edges, dtype=np.int64)
    zero = np.zeros(n_edges, dtype=np.int64)
    negative = np.zeros(n_edges, dtype=np.int64)
    common_zero_months = np.zeros(n_edges, dtype=np.int64)
    common_zero_fraction_sum = np.zeros(n_edges, dtype=np.float64)
    correlation_min = np.full(n_edges, np.nan, dtype=np.float64)
    correlation_max = np.full(n_edges, np.nan, dtype=np.float64)
    correlation_mean = np.full(n_edges, np.nan, dtype=np.float64)
    correlation_median = np.full(n_edges, np.nan, dtype=np.float64)
    correlation_std = np.full(n_edges, np.nan, dtype=np.float64)

    global_values: List[np.ndarray] = []
    global_positive = 0
    global_zero = 0
    global_negative = 0
    global_eligible = 0
    global_insufficient = 0
    global_constant = 0

    for start in range(0, n_edges, block_size):
        end = min(start + block_size, n_edges)
        block_edges = edges[start:end]
        block_size_actual = int(block_edges.shape[0])
        left = block_edges[:, 0]
        right = block_edges[:, 1]
        correlations = np.full((block_size_actual, n_contexts), np.nan, dtype=np.float64)
        block_eligible = np.zeros(block_size_actual, dtype=np.int64)
        block_insufficient = np.zeros(block_size_actual, dtype=np.int64)
        block_constant = np.zeros(block_size_actual, dtype=np.int64)
        block_reason = np.zeros((block_size_actual, n_contexts), dtype=np.int8)
        block_positive = np.zeros(block_size_actual, dtype=np.int64)
        block_zero = np.zeros(block_size_actual, dtype=np.int64)
        block_negative = np.zeros(block_size_actual, dtype=np.int64)
        block_common_zero = np.zeros(block_size_actual, dtype=np.int64)
        block_common_zero_fraction = np.zeros(block_size_actual, dtype=np.float64)
        for context in range(n_contexts):
            left_series = values[context, left, :]
            right_series = values[context, right, :]
            positive_left = (left_series > 0).sum(axis=1)
            positive_right = (right_series > 0).sum(axis=1)
            too_sparse = (positive_left < min_positive_months) | (
                positive_right < min_positive_months
            )
            left_diff = np.diff(left_series, axis=1)
            right_diff = np.diff(right_series, axis=1)
            correlation, product = _correlation_block(left_diff, right_diff)
            is_constant = (~too_sparse) & (product <= 0)
            is_eligible = (~too_sparse) & (~is_constant)
            correlations[is_eligible, context] = correlation[is_eligible]
            block_insufficient += too_sparse.astype(np.int64)
            block_constant += is_constant.astype(np.int64)
            block_reason[too_sparse, context] = 1
            block_reason[is_constant, context] = 2
            block_eligible += is_eligible.astype(np.int64)
            block_positive += (is_eligible & (correlation > 0)).astype(np.int64)
            block_zero += (is_eligible & (correlation == 0)).astype(np.int64)
            block_negative += (is_eligible & (correlation < 0)).astype(np.int64)
            both_zero = ((left_series == 0) & (right_series == 0)).sum(axis=1)
            block_common_zero += both_zero.astype(np.int64)
            block_common_zero_fraction += both_zero.astype(np.float64) / float(
                protocol.N_TRAIN_MONTHS
            )

        valid = ~np.isnan(correlations)
        counts = valid.sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            minimum = np.where(valid, correlations, np.inf).min(axis=1)
            maximum = np.where(valid, correlations, -np.inf).max(axis=1)
            total = np.where(valid, correlations, 0.0).sum(axis=1)
            mean = np.divide(
                total,
                counts,
                out=np.full(block_size_actual, np.nan),
                where=counts > 0,
            )
            deviation = np.where(valid, (correlations - mean[:, None]) ** 2, 0.0).sum(
                axis=1
            )
            std = np.sqrt(
                np.divide(
                    deviation,
                    counts,
                    out=np.full(block_size_actual, np.nan),
                    where=counts > 0,
                )
            )
            minimum = np.where(counts > 0, minimum, np.nan)
            maximum = np.where(counts > 0, maximum, np.nan)
            sorted_correlations = np.sort(correlations, axis=1)
            lower_index = np.maximum((counts - 1) // 2, 0)
            upper_index = np.maximum(counts // 2, 0)
            rows = np.arange(block_size_actual)
            lower = sorted_correlations[rows, lower_index]
            upper = sorted_correlations[rows, upper_index]
            median = np.where(counts > 0, (lower + upper) / 2.0, np.nan)
        eligible[start:end] = block_eligible
        insufficient[start:end] = block_insufficient
        constant[start:end] = block_constant
        reason_codes[start:end, :] = block_reason
        positive[start:end] = block_positive
        zero[start:end] = block_zero
        negative[start:end] = block_negative
        common_zero_months[start:end] = block_common_zero
        correlation_min[start:end] = minimum
        correlation_max[start:end] = maximum
        correlation_mean[start:end] = mean
        correlation_median[start:end] = median
        correlation_std[start:end] = std
        common_zero_fraction_sum[start:end] = block_common_zero_fraction
        if valid.any():
            global_values.append(correlations[valid])
        global_positive += int(block_positive.sum())
        global_zero += int(block_zero.sum())
        global_negative += int(block_negative.sum())
        global_eligible += int(block_eligible.sum())
        global_insufficient += int(block_insufficient.sum())
        global_constant += int(block_constant.sum())
        if progress is not None:
            progress("trends", end, n_edges)

    common_zero_fraction = (
        common_zero_months.astype(np.float64)
        / float(n_contexts * protocol.N_TRAIN_MONTHS)
    )
    mean_context_common_zero_fraction = (
        common_zero_fraction_sum / float(n_contexts)
    )
    if global_values:
        flattened = np.concatenate(global_values)
        global_summary: Dict[str, Any] = {
            "status": "ok",
            "eligible_context_count": int(global_eligible),
            "insufficient_context_count": int(global_insufficient),
            "constant_context_count": int(global_constant),
            "positive_correlations": int(global_positive),
            "zero_correlations": int(global_zero),
            "negative_correlations": int(global_negative),
            "correlation_min": float(flattened.min()),
            "correlation_max": float(flattened.max()),
            "correlation_mean": float(flattened.mean()),
            "correlation_median": float(np.median(flattened)),
            "correlation_std": float(flattened.std(ddof=0)),
            "null_reasons": {},
        }
    else:
        global_summary = {
            "status": "null",
            "eligible_context_count": 0,
            "insufficient_context_count": int(global_insufficient),
            "constant_context_count": int(global_constant),
            "positive_correlations": 0,
            "zero_correlations": 0,
            "negative_correlations": 0,
            "correlation_min": None,
            "correlation_max": None,
            "correlation_mean": None,
            "correlation_median": None,
            "correlation_std": None,
            "null_reasons": {
                "correlation_summary": "no eligible edge-context observation"
            },
        }
    global_summary.update(
        {
            "min_positive_months": int(min_positive_months),
            "first_difference_length": protocol.FIRST_DIFFERENCE_LENGTH,
            "context_count": int(n_contexts),
            "common_zero_month_fraction_of_all_context_months": (
                float(common_zero_months.sum())
                / float(max(n_edges, 1) * n_contexts * protocol.N_TRAIN_MONTHS)
            ),
            "eligibility_rule": (
                "at least 12 positive-demand months at both endpoints and "
                "nonzero first-difference variance at both endpoints; a "
                "descriptive convention, not a significance or reliability test"
            ),
            "insufficient_reason": REASON_INSUFFICIENT,
            "constant_reason": REASON_CONSTANT,
            "graph_selection_influence": False,
            "reason_codes": {
                "0": "eligible",
                "1": REASON_INSUFFICIENT,
                "2": REASON_CONSTANT,
            },
        }
    )
    return TrendResult(
        observations_shape=(n_contexts, int(values.shape[1]), int(values.shape[2])),
        edge_index=edges,
        eligible_counts=eligible,
        insufficient_counts=insufficient,
        constant_counts=constant,
        reason_codes=reason_codes,
        positive_counts=positive,
        zero_counts=zero,
        negative_counts=negative,
        common_zero_months=common_zero_months,
        common_zero_fraction=common_zero_fraction,
        mean_context_common_zero_fraction=mean_context_common_zero_fraction,
        correlation_min=correlation_min,
        correlation_max=correlation_max,
        correlation_mean=correlation_mean,
        correlation_median=correlation_median,
        correlation_std=correlation_std,
        global_summary=global_summary,
        graph_payload_sha256={},
    )


def candidate_trend_summary(
    result: TrendResult, positions: np.ndarray, candidate_name: str
) -> Dict[str, Any]:
    """Summarize one candidate's subset of the shared trend computation."""
    index = np.asarray(positions, dtype=np.int64)
    eligible = result.eligible_counts[index]
    insufficient = result.insufficient_counts[index]
    constant = result.constant_counts[index]
    positive = int(result.positive_counts[index].sum())
    zero = int(result.zero_counts[index].sum())
    negative = int(result.negative_counts[index].sum())
    with_eligible = eligible > 0
    means = result.correlation_mean[index][with_eligible]
    mins = result.correlation_min[index][with_eligible]
    maxs = result.correlation_max[index][with_eligible]
    medians = result.correlation_median[index][with_eligible]
    common_zero = result.common_zero_months[index]
    context_count = int(result.observations_shape[0])
    months = int(result.observations_shape[2])
    edge_count = int(index.size)
    return {
        "candidate": candidate_name,
        "edges": edge_count,
        "eligible_context_count": int(eligible.sum()),
        "insufficient_context_count": int(insufficient.sum()),
        "constant_context_count": int(constant.sum()),
        "edges_with_eligible_context": int(np.count_nonzero(with_eligible)),
        "unknown_edges": int(np.count_nonzero(~with_eligible)),
        "positive_correlations": positive,
        "zero_correlations": zero,
        "negative_correlations": negative,
        "common_zero_month_count": int(common_zero.sum()),
        "common_zero_fraction": (
            float(common_zero.sum()) / float(edge_count * context_count * months)
            if edge_count
            else None
        ),
        "common_zero_fraction_reason": (
            None if edge_count else "candidate has no retained edge"
        ),
        "per_edge_correlation_mean": distribution_summary(means),
        "per_edge_correlation_min": distribution_summary(mins),
        "per_edge_correlation_max": distribution_summary(maxs),
        "per_edge_correlation_median": distribution_summary(medians),
        "null_reasons": {
            "correlation_summary": (
                None if with_eligible.any() else "no eligible edge-context observation"
            ),
            "unknown_edges": "eligible count is zero; correlation remains unknown",
        },
        "eligibility_rule": result.global_summary["eligibility_rule"],
        "insufficient_reason": REASON_INSUFFICIENT,
        "constant_reason": REASON_CONSTANT,
        "graph_selection_influence": False,
        "interpretation": (
            "diagnostic occupational heterogeneity only; not significance, "
            "reliability or predictive benefit"
        ),
    }


def trend_payload_hashes(result: TrendResult) -> Dict[str, str]:
    """Hash saved trend arrays for inventory and integrity checks."""
    return result.identity_hashes()
