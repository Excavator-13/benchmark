"""Diagnostic first-difference correlations and explicit null reasons."""

from __future__ import annotations

import unittest

import numpy as np

from benchmark.occupation_skill_graph import protocol, scores, trends
from benchmark.occupation_skill_graph.tests import fixtures as fx


def _observations() -> np.ndarray:
    values = np.zeros((2, 3, protocol.N_TRAIN_MONTHS), dtype=np.float64)
    base = np.array(
        [
            0,
            0,
            0,
            1,
            3,
            6,
            10,
            15,
            21,
            28,
            36,
            45,
            55,
            66,
            78,
            91,
            105,
            120,
            136,
            153,
            171,
            190,
            210,
            231,
            253,
            276,
            300,
        ],
        dtype=np.float64,
    )
    # Occupation 0: both series increase together (r=1) with common zeros.
    values[0, 0, :] = base
    values[0, 1, :] = 2.0 * base
    # Occupation 0, skill 2: constant demand -> constant differences.
    values[0, 2, :] = 5.0
    # Occupation 1: skill 1 opposes skill 0 (r=-1).
    values[1, 0, :] = base
    values[1, 1, :] = 301.0 - base
    # Occupation 1, skill 2: only five positive months -> insufficient history.
    values[1, 2, :5] = 5.0
    return values


class TrendDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.observations = _observations()
        self.edges = np.array([[0, 1], [1, 2]], dtype=np.int64)

    def test_opposing_signs_and_reasons(self) -> None:
        result = trends.compute_trends(self.observations, self.edges)
        # Edge 0-1: one positive and one negative eligible occupation.
        self.assertEqual(int(result.eligible_counts[0]), 2)
        self.assertEqual(result.reason_codes[0].tolist(), [0, 0])
        self.assertEqual(int(result.positive_counts[0]), 1)
        self.assertEqual(int(result.negative_counts[0]), 1)
        self.assertEqual(int(result.zero_counts[0]), 0)
        self.assertAlmostEqual(float(result.correlation_min[0]), -1.0)
        self.assertAlmostEqual(float(result.correlation_max[0]), 1.0)
        # In occupation 0 both series share the first three zero months.
        self.assertEqual(int(result.common_zero_months[0]), 3)
        self.assertAlmostEqual(float(result.common_zero_fraction[0]), 3.0 / 54.0)
        # Edge 1-2: constant differences in occupation 0 and insufficient
        # history in occupation 1; neither is counted as zero correlation.
        self.assertEqual(int(result.eligible_counts[1]), 0)
        self.assertEqual(int(result.insufficient_counts[1]), 1)
        self.assertEqual(int(result.constant_counts[1]), 1)
        self.assertEqual(result.reason_codes[1].tolist(), [2, 1])
        self.assertEqual(int(result.positive_counts[1]), 0)
        self.assertEqual(int(result.zero_counts[1]), 0)
        self.assertEqual(int(result.negative_counts[1]), 0)
        self.assertTrue(np.isnan(result.correlation_mean[1]))
        self.assertEqual(result.global_summary["eligible_context_count"], 2)
        self.assertEqual(result.global_summary["positive_correlations"], 1)
        self.assertEqual(result.global_summary["negative_correlations"], 1)

    def test_insufficient_history_has_priority(self) -> None:
        result = trends.compute_trends(self.observations, self.edges)
        summary = trends.candidate_trend_summary(
            result, np.array([0, 1], dtype=np.int64), "jaccard"
        )
        self.assertEqual(summary["unknown_edges"], 1)
        self.assertEqual(summary["insufficient_context_count"], 1)
        self.assertEqual(summary["constant_context_count"], 1)
        self.assertEqual(summary["null_reasons"]["unknown_edges"], (
            "eligible count is zero; correlation remains unknown"
        ))
        self.assertEqual(summary["per_edge_correlation_mean"]["status"], "ok")
        self.assertEqual(summary["per_edge_correlation_mean"]["count"], 1)

    def test_graph_bytes_are_unchanged(self) -> None:
        training = fx.training_fixture([0, 1], [0, 1, 2], self.observations)
        graph = scores.compute_candidate("jaccard", training.x, training.support)
        before = graph.identity_hashes()
        trends.compute_trends(self.observations, graph.edge_index)
        after = graph.identity_hashes()
        self.assertEqual(before, after)

    def test_no_eligible_edge_remains_unknown(self) -> None:
        observations = np.zeros((1, 2, protocol.N_TRAIN_MONTHS), dtype=np.float64)
        observations[0, 0, -7:] = 1.0
        observations[0, 1, -7:] = 1.0
        result = trends.compute_trends(observations, np.array([[0, 1]]))
        self.assertEqual(result.global_summary["status"], "null")
        summary = trends.candidate_trend_summary(
            result, np.array([0], dtype=np.int64), "cosine"
        )
        self.assertEqual(summary["unknown_edges"], 1)
        self.assertEqual(
            summary["null_reasons"]["correlation_summary"],
            "no eligible edge-context observation",
        )

    def test_constant_differences_are_null_not_zero(self) -> None:
        observations = np.ones((1, 2, protocol.N_TRAIN_MONTHS), dtype=np.float64)
        result = trends.compute_trends(observations, np.array([[0, 1]]))
        self.assertEqual(int(result.constant_counts[0]), 1)
        self.assertEqual(result.reason_codes[0].tolist(), [2])
        self.assertEqual(int(result.eligible_counts[0]), 0)
        self.assertEqual(int(result.zero_counts[0]), 0)
        self.assertTrue(np.isnan(result.correlation_mean[0]))


if __name__ == "__main__":
    unittest.main()
