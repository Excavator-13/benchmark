"""Metric reductions, fixed groups, empty groups and zero-reference gains.

Covers task 6.3 with an independent loop oracle over the saved-style arrays.
"""

from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from benchmark.graph_value_skeleton import data as gvs_data
from benchmark.graph_value_skeleton import protocol
from benchmark.graph_value_skeleton.tests import fixtures
from benchmark.nograph_baseline import coverage as p01_coverage
from benchmark.nograph_baseline import metrics as p01_metrics
from benchmark.nograph_baseline import protocol as p01


def _oracle(pred, gold, mask=None) -> dict:
    values_p = np.asarray(pred, dtype=np.float64)
    values_g = np.asarray(gold, dtype=np.float64)
    if mask is not None:
        values_p = values_p[:, np.asarray(mask, dtype=bool), :]
        values_g = values_g[:, np.asarray(mask, dtype=bool), :]
    errors = [
        values_p[w, n, h] - values_g[w, n, h]
        for w in range(values_p.shape[0])
        for n in range(values_p.shape[1])
        for h in range(values_p.shape[2])
    ]
    elements = len(errors)
    if elements == 0:
        return {"MAE": None, "MSE": None, "RMSE": None, "elements": 0, "status": "empty"}
    absolute = sum(abs(value) for value in errors)
    squared = sum(value * value for value in errors)
    mse = squared / elements
    negative = sum(
        1
        for w in range(values_p.shape[0])
        for n in range(values_p.shape[1])
        for h in range(values_p.shape[2])
        if values_p[w, n, h] < 0
    )
    return {
        "MAE": absolute / elements,
        "MSE": mse,
        "RMSE": math.sqrt(mse),
        "negative_prediction_ratio": negative / elements,
        "elements": elements,
        "absolute_error_sum": absolute,
        "squared_error_sum": squared,
        "status": "ok",
    }


class MetricsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = fixtures.build_fixture(
            Path(tempfile.mkdtemp(prefix="gvs-metrics-")), "region"
        )
        cls.dataset, cls.graph = fixtures.load_fixture(cls.fixture)
        coverage = p01_coverage.load_graph_coverage(
            "region", cls.dataset.key_array, graph_path=cls.fixture["graph_path"]
        )
        cls.masks = gvs_data.build_masks(cls.dataset, coverage)
        # Deterministic predictions with negatives and unequal window errors.
        starts = protocol.TEST_STARTS
        gold = cls.dataset.target_windows(starts).astype(np.float64)
        rng = np.random.default_rng(31)
        noise = rng.normal(0.0, 3.0, size=gold.shape)
        pred = gold + noise
        pred[:, 0, :] -= 25.0
        cls.pred = pred.astype(np.float32)
        cls.gold = gold.astype(np.float32)
        cls.activity_masks = dict(cls.masks.activity_groups)
        cls.constant_masks = p01_metrics.constant_group_masks(
            cls.masks.constant_mask, scope="train27"
        )
        cls.context_masks = p01_metrics.context_masks(cls.dataset.context_values)
        cls.neighbor_masks = p01_metrics.neighbor_group_masks(cls.masks.neighbor_mask)
        cls.report = p01_metrics.split_report(
            cls.pred,
            cls.gold,
            starts=starts,
            activity_masks=cls.activity_masks,
            constant_masks=cls.constant_masks,
            context_masks_map=cls.context_masks,
            neighbor_masks=cls.neighbor_masks,
            group_names=p01.ACTIVITY_GROUP_NAMES,
            inactive_group_name="inactive",
        )

    def test_overall_matches_independent_oracle(self) -> None:
        expected = _oracle(self.pred, self.gold)
        for field in ("MAE", "MSE", "RMSE", "negative_prediction_ratio"):
            self.assertLessEqual(
                abs(self.report[field] - expected[field])
                / max(1.0, abs(expected[field])),
                1e-12,
                field,
            )
        self.assertEqual(self.report["status"], "ok")
        self.assertEqual(self.report["elements"], expected["elements"])
        self.assertGreater(self.report["negative_prediction_ratio"], 0.0)

    def test_overall_rmse_is_not_mean_window_rmse(self) -> None:
        window_rmse = [row["RMSE"] for row in self.report["windows"]]
        self.assertNotAlmostEqual(
            self.report["RMSE"], float(np.mean(window_rmse)), places=6
        )
        pooled = math.sqrt(
            sum(row["squared_error_sum"] for row in self.report["windows"])
            / sum(row["elements"] for row in self.report["windows"])
        )
        self.assertAlmostEqual(self.report["RMSE"], pooled, places=12)

    def test_windows_horizons_and_multiplicities(self) -> None:
        self.assertEqual(len(self.report["windows"]), 4)
        for index, row in enumerate(self.report["windows"]):
            expected = _oracle(self.pred[index : index + 1], self.gold[index : index + 1])
            self.assertEqual(row["start"], protocol.TEST_STARTS[index])
            self.assertLessEqual(abs(row["MAE"] - expected["MAE"]), 1e-12)
        for horizon in range(3):
            expected = _oracle(
                self.pred[:, :, horizon : horizon + 1],
                self.gold[:, :, horizon : horizon + 1],
            )
            actual = self.report["horizons"][f"h{horizon + 1}"]
            self.assertLessEqual(abs(actual["MAE"] - expected["MAE"]), 1e-12)
        self.assertEqual(
            self.report["target_month_multiplicities"],
            {
                "2023-07": 1,
                "2023-08": 2,
                "2023-09": 3,
                "2023-10": 3,
                "2023-11": 2,
                "2023-12": 1,
            },
        )

    def test_group_counts_and_masks(self) -> None:
        total = 0
        for name in p01.ACTIVITY_GROUP_NAMES:
            expected = _oracle(self.pred, self.gold, self.activity_masks[name])
            actual = self.report["activity_groups"][name]
            self.assertGreater(actual["nodes"], 0)
            self.assertEqual(actual["elements"], expected["elements"])
            self.assertLessEqual(abs(actual["MAE"] - expected["MAE"]), 1e-12)
            total += actual["nodes"]
        self.assertEqual(total, self.dataset.node_count)
        for name, mask in self.constant_masks.items():
            expected = _oracle(self.pred, self.gold, mask)
            self.assertLessEqual(
                abs(self.report["constant_groups"][name]["MAE"] - expected["MAE"]),
                1e-12,
            )
        for name, mask in self.context_masks.items():
            expected = _oracle(self.pred, self.gold, mask)
            self.assertLessEqual(
                abs(self.report["contexts"][name]["MAE"] - expected["MAE"]), 1e-12
            )
        for name, mask in self.neighbor_masks.items():
            actual = self.report["neighbor_groups"][name]
            if not mask.any():
                self.assertEqual(actual["status"], "empty")
                self.assertIsNone(actual["MAE"])
                self.assertEqual(actual["elements"], 0)
            else:
                expected = _oracle(self.pred, self.gold, mask)
                self.assertLessEqual(abs(actual["MAE"] - expected["MAE"]), 1e-12)
        # Contributions sum to one over the full population.
        contributions = [
            self.report["activity_groups"][name]["absolute_error_contribution_fraction"]
            for name in p01.ACTIVITY_GROUP_NAMES
        ]
        self.assertAlmostEqual(float(np.sum(contributions)), 1.0, places=12)

    def test_balanced_activity_mae_excludes_empty_groups(self) -> None:
        values = [
            self.report["activity_groups"][name]["MAE"]
            for name in p01.ACTIVITY_GROUP_NAMES
        ]
        self.assertAlmostEqual(
            self.report["balanced_activity_group_MAE"], float(np.mean(values)), places=12
        )
        self.assertEqual(self.report["excluded_empty_groups"], [])
        empty = p01_metrics.masked_group_metrics(
            self.pred,
            self.gold,
            {"inactive": np.zeros(self.dataset.node_count, dtype=bool)},
        )
        balanced = p01_metrics.balanced_activity_mae(
            {"inactive": empty["inactive"]},
            group_names=p01.ACTIVITY_GROUP_NAMES,
        )
        self.assertIsNone(balanced["balanced_activity_group_MAE"])
        self.assertEqual(balanced["status"], "empty")
        self.assertEqual(balanced["excluded_empty_groups"], ["inactive"])
        self.assertEqual(empty["inactive"]["status"], "empty")
        self.assertEqual(empty["inactive"]["elements"], 0)
        self.assertIsNone(empty["inactive"]["MAE"])

    def test_relative_gain_and_zero_reference(self) -> None:
        reports = {
            "model": {"MAE": 4.0, "activity_groups": {}, "contexts": {}, "neighbor_groups": {}, "windows": []},
            "Zero": {"MAE": 5.0, "activity_groups": {}, "contexts": {}, "neighbor_groups": {}, "windows": []},
            "Perfect": {"MAE": 0.0, "activity_groups": {}, "contexts": {}, "neighbor_groups": {}, "windows": []},
        }
        comparison = p01_metrics.baseline_relative_comparison(
            reports,
            activity_groups=(),
            context_names=(),
            neighbor_names=(),
            model_names=["model"],
            reference_names=["Zero", "Perfect"],
        )
        self.assertAlmostEqual(comparison["model"]["Zero"]["overall"]["relative_MAE_gain"], 0.2)
        self.assertIsNone(comparison["model"]["Perfect"]["overall"]["relative_MAE_gain"])
        self.assertEqual(
            comparison["model"]["Perfect"]["overall"]["status"],
            p01_metrics.UNAVAILABLE_STATUS,
        )
        gain = p01_metrics.relative_gain(None, 3.0)
        self.assertIsNone(gain["relative_MAE_gain"])
        self.assertEqual(gain["status"], p01_metrics.UNAVAILABLE_STATUS)


if __name__ == "__main__":
    unittest.main()
