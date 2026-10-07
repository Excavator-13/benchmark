"""Analytic metric reductions, grouped reports and per-node contributions."""

from __future__ import annotations

import unittest

import numpy as np

from benchmark.nograph_baseline import metrics, protocol


class ErrorMetricTests(unittest.TestCase):
    def test_mae_mse_rmse_and_negative_ratio(self) -> None:
        pred = np.array([[[-2.0, 0.0, 3.0]]])
        gold = np.array([[[0.0, 1.0, 1.0]]])
        record = metrics.error_metrics(pred, gold)
        self.assertAlmostEqual(record["MAE"], (2 + 1 + 2) / 3)
        self.assertAlmostEqual(record["MSE"], (4 + 1 + 4) / 3)
        self.assertAlmostEqual(record["RMSE"], np.sqrt((4 + 1 + 4) / 3))
        self.assertAlmostEqual(record["negative_prediction_ratio"], 1 / 3)
        self.assertEqual(record["elements"], 3)
        self.assertEqual(record["absolute_error_sum"], 5.0)
        self.assertEqual(record["squared_error_sum"], 9.0)
        self.assertEqual(record["status"], "ok")

    def test_empty_group_reports_null_metrics(self) -> None:
        pred = np.zeros((1, 0, 3))
        gold = np.zeros((1, 0, 3))
        record = metrics.error_metrics(pred, gold)
        self.assertIsNone(record["MAE"])
        self.assertIsNone(record["MSE"])
        self.assertIsNone(record["RMSE"])
        self.assertEqual(record["elements"], 0)
        self.assertEqual(record["status"], "empty")

    def test_overall_rmse_is_not_mean_of_window_rmse(self) -> None:
        pred = np.zeros((2, 1, 3))
        gold = np.zeros((2, 1, 3))
        gold[0, 0, :] = 0.0  # window 0: MSE 0
        gold[1, 0, :] = 8.0  # window 1: MSE 64
        window_reports = metrics.window_metrics(
            pred, gold, protocol.SPLITS["test"][:2]
        )
        overall = metrics.error_metrics(pred, gold)
        self.assertAlmostEqual(overall["MSE"], 32.0)
        self.assertAlmostEqual(overall["RMSE"], np.sqrt(32.0))
        naive_mean = float(np.mean([row["RMSE"] for row in window_reports]))
        self.assertNotAlmostEqual(overall["RMSE"], naive_mean)

    def test_horizon_metrics_per_horizon(self) -> None:
        pred = np.zeros((1, 2, 3))
        gold = np.zeros((1, 2, 3))
        gold[0, :, 1] = 4.0
        horizons = metrics.horizon_metrics(pred, gold)
        self.assertEqual(horizons["h1"]["MSE"], 0.0)
        self.assertEqual(horizons["h2"]["MSE"], 16.0)
        self.assertEqual(horizons["h3"]["MSE"], 0.0)


class GroupedReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pred = np.zeros((2, 5, 3))
        self.gold = np.zeros((2, 5, 3))
        self.gold[1, 4, :] = 6.0
        self.activity = {
            "inactive": np.array([True, False, False, False, False]),
            "low": np.array([False, True, False, False, False]),
            "medium": np.array([False, False, False, True, False]),
            "high": np.array([False, False, False, False, True]),
        }
        self.neighbor = {
            "has_nonself_neighbor": np.array([True, False, False, False, True]),
            "no_nonself_neighbor": np.array([False, True, True, True, False]),
        }

    def test_counts_contributions_and_equal_weight_mae(self) -> None:
        overall = metrics.error_metrics(self.pred, self.gold)
        reports = metrics.masked_group_metrics(
            self.pred,
            self.gold,
            self.activity,
            global_absolute=overall["absolute_error_sum"],
            global_squared=overall["squared_error_sum"],
        )
        self.assertEqual(reports["high"]["nodes"], 1)
        self.assertEqual(reports["high"]["elements"], 6)
        self.assertAlmostEqual(reports["high"]["MAE"], 3.0)
        self.assertAlmostEqual(reports["high"]["absolute_error_sum"], 18.0)
        self.assertAlmostEqual(reports["high"]["squared_error_sum"], 108.0)
        self.assertAlmostEqual(
            reports["high"]["absolute_error_contribution_fraction"], 1.0
        )
        balanced = metrics.balanced_activity_mae(reports)
        # inactive/low/medium are nonempty but have zero error; all four count.
        self.assertEqual(len(balanced["nonempty_groups"]), 4)
        self.assertAlmostEqual(
            balanced["balanced_activity_group_MAE"], (0 + 0 + 0 + 3.0) / 4
        )

    def test_empty_activity_group_is_excluded(self) -> None:
        reports = metrics.masked_group_metrics(self.pred, self.gold, self.activity)
        reports["low"] = dict(reports["low"])
        reports["low"].update(metrics.error_metrics(
            self.pred[:, :0, :], self.gold[:, :0, :]
        ))
        reports["low"]["nodes"] = 0
        balanced = metrics.balanced_activity_mae(reports)
        self.assertIn("low", balanced["excluded_empty_groups"])
        self.assertNotIn("low", balanced["nonempty_groups"])

    def test_neighbor_groups_partition_nodes(self) -> None:
        reports = metrics.masked_group_metrics(self.pred, self.gold, self.neighbor)
        self.assertEqual(
            reports["has_nonself_neighbor"]["nodes"]
            + reports["no_nonself_neighbor"]["nodes"],
            5,
        )

    def test_context_masks_keyed_by_context_value(self) -> None:
        masks = metrics.context_masks(np.array([0, 0, 1, 2, 2]))
        self.assertEqual(sorted(masks), ["0", "1", "2"])
        self.assertEqual(int(masks["0"].sum()), 2)
        self.assertEqual(int(masks["2"].sum()), 2)

    def test_relative_gain_zero_reference_is_unavailable(self) -> None:
        gain = metrics.relative_gain(0.0, 0.0)
        self.assertIsNone(gain["relative_MAE_gain"])
        self.assertEqual(gain["status"], "unavailable")
        self.assertIn("zero", gain["reason"])
        positive = metrics.relative_gain(90.0, 100.0)
        self.assertAlmostEqual(positive["relative_MAE_gain"], 0.1)

    def test_test_target_month_multiplicities(self) -> None:
        counts = metrics.target_month_multiplicities(protocol.SPLITS["test"])
        self.assertEqual(
            [counts[month] for month in sorted(counts)],
            [1, 2, 3, 3, 2, 1],
        )


class NodeErrorTableTests(unittest.TestCase):
    def test_table_is_training_mean_ranked_with_key_ties(self) -> None:
        pred = np.zeros((1, 4, 3))
        gold = np.zeros((1, 4, 3))
        gold[0, 0, :] = 2.0
        gold[0, 1, :] = 5.0
        gold[0, 3, :] = 1.0
        keys = np.array([[0, 1], [0, 3], [0, 0], [0, 2]])
        train_means = np.array([5.0, 5.0, 1.0, 9.0])
        frame = metrics.node_error_table(
            pred,
            gold,
            method="Zero",
            split="test",
            node_keys=keys,
            key_columns=["r0_id", "skill_id"],
            train_mean27_values=train_means,
            context_values=np.zeros(4, dtype=int),
        )
        # Descending training mean, ties by ascending canonical node key.
        self.assertEqual(frame["train_mean27"].tolist(), [9.0, 5.0, 5.0, 1.0])
        self.assertEqual(frame["skill_id"].tolist(), [2, 1, 3, 0])
        first = frame.iloc[0]
        self.assertEqual(first["skill_id"], 2)
        self.assertAlmostEqual(first["absolute_error_sum"], 3.0)
        self.assertAlmostEqual(first["squared_error_sum"], 3.0)
        self.assertEqual(first["elements"], 3)
        large = frame[frame["skill_id"] == 3].iloc[0]
        self.assertAlmostEqual(large["absolute_error_sum"], 15.0)
        self.assertAlmostEqual(large["squared_error_sum"], 75.0)


class SplitReportTests(unittest.TestCase):
    def test_split_report_exposes_every_required_level(self) -> None:
        pred = np.zeros((1, 4, 3))
        gold = np.zeros((1, 4, 3))
        gold[0, 3, :] = 2.0
        masks = {
            "inactive": np.array([True, False, False, False]),
            "low": np.array([False, True, False, False]),
            "medium": np.array([False, False, True, False]),
            "high": np.array([False, False, False, True]),
        }
        report = metrics.split_report(
            pred,
            gold,
            starts=[21],
            activity_masks=masks,
            constant_masks={
                "constant_train27": np.array([True, False, False, False]),
                "nonconstant_train27": np.array([False, True, True, True]),
            },
            context_masks_map={"0": np.ones(4, dtype=bool)},
            neighbor_masks={
                "has_nonself_neighbor": np.array([True, False, False, False]),
                "no_nonself_neighbor": np.array([False, True, True, True]),
            },
        )
        for level in (
            "MAE",
            "MSE",
            "RMSE",
            "negative_prediction_ratio",
            "activity_groups",
            "constant_groups",
            "contexts",
            "neighbor_groups",
            "windows",
            "horizons",
            "balanced_activity_group_MAE",
            "training_all_zero_group",
            "target_month_multiplicities",
        ):
            self.assertIn(level, report)
        self.assertEqual(report["training_all_zero_group"]["group"], "inactive")


if __name__ == "__main__":
    unittest.main()
