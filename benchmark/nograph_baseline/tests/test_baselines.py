"""The five na\u00efve methods and frozen reference selection."""

from __future__ import annotations

import unittest

import numpy as np

import nb_fixtures as fx
from benchmark.nograph_baseline import baselines, protocol


class NaiveMethodTests(unittest.TestCase):
    def setUp(self) -> None:
        self.signal = fx.synthetic_signal(5, seed=8)
        self.starts = protocol.SPLITS["validation"]
        self.predictions = baselines.naive_predictions(self.signal, self.starts)
        self.inputs = np.stack(
            [self.signal[:, s : s + 6] for s in self.starts]
        )
        self.targets = np.stack(
            [self.signal[:, s + 6 : s + 9] for s in self.starts]
        )

    def test_all_five_methods_present_with_expected_shapes(self) -> None:
        self.assertEqual(
            list(self.predictions), list(protocol.NAIVE_METHODS)
        )
        for prediction in self.predictions.values():
            self.assertEqual(prediction.shape, self.targets.shape)

    def test_zero_lastvalue_and_windowmean(self) -> None:
        np.testing.assert_array_equal(
            self.predictions["Zero"], np.zeros_like(self.targets)
        )
        np.testing.assert_allclose(
            self.predictions["LastValue"],
            np.repeat(self.inputs[:, :, -1:], 3, axis=2),
        )
        np.testing.assert_allclose(
            self.predictions["WindowMean6"],
            np.repeat(self.inputs.mean(axis=2, keepdims=True), 3, axis=2),
        )

    def test_trainmean27_is_frozen_training_statistic(self) -> None:
        frozen = baselines.train_mean27(self.signal)
        expected = np.broadcast_to(frozen[None, :, :], self.targets.shape)
        np.testing.assert_allclose(self.predictions["TrainMean27"], expected)
        # Changing post-March-2023 values must not move TrainMean27.
        changed = self.signal.copy()
        changed[:, 27:] = 12345.0
        np.testing.assert_array_equal(
            baselines.train_mean27(changed), frozen
        )

    def test_seasonal_naive_uses_last_year_same_month(self) -> None:
        seasonal = self.predictions["SeasonalNaive12"]
        for window_index, start in enumerate(self.starts):
            for horizon in range(protocol.HORIZON):
                target_index = start + protocol.INPUT_LENGTH + horizon
                np.testing.assert_allclose(
                    seasonal[window_index, :, horizon],
                    self.signal[:, target_index - 12],
                )
        # For validation start 21 the target months are 2023-04..06.
        self.assertEqual(
            list(protocol.window_target_months(21)),
            ["2023-04", "2023-05", "2023-06"],
        )


class ReferenceSelectionTests(unittest.TestCase):
    def test_exact_tie_uses_protocol_table_order(self) -> None:
        scores = {
            "Zero": 10.0,
            "LastValue": 1.0,
            "WindowMean6": 1.0,
            "TrainMean27": 5.0,
            "SeasonalNaive12": 0.5,
        }
        selection = baselines.select_references(scores)
        self.assertEqual(selection["NaiveRef"], "SeasonalNaive12")
        self.assertEqual(selection["NaiveRef6"], "LastValue")
        self.assertIn("LastValue", selection["NaiveRef6_ties"])
        self.assertIn("WindowMean6", selection["NaiveRef6_ties"])

    def test_seasonal_reference_is_labeled_extra_history(self) -> None:
        scores = {
            "Zero": 10.0,
            "LastValue": 4.0,
            "WindowMean6": 3.0,
            "TrainMean27": 5.0,
            "SeasonalNaive12": 0.1,
        }
        selection = baselines.select_references(scores)
        self.assertEqual(selection["NaiveRef"], "SeasonalNaive12")
        self.assertTrue(selection["NaiveRef_uses_extra_history"])
        self.assertFalse(selection["NaiveRef6_uses_extra_history"])
        self.assertEqual(selection["NaiveRef6"], "WindowMean6")
        self.assertTrue(
            selection["SeasonalNaive12_excluded_from_NaiveRef6"]
        )
        self.assertEqual(
            selection["information_budget"]["SeasonalNaive12"],
            "extra 12-month history",
        )

    def test_selection_uses_validation_mse_only(self) -> None:
        # WindowMean6 wins validation MSE even though LastValue wins MAE.
        scores = {"Zero": 5.0, "LastValue": 2.0, "WindowMean6": 1.5,
                  "TrainMean27": 3.0, "SeasonalNaive12": 4.0}
        selection = baselines.select_references(scores)
        self.assertEqual(selection["NaiveRef"], "WindowMean6")
        self.assertEqual(selection["selection_metric"], "validation MSE")
        self.assertTrue(selection["frozen_before_test_evaluation"])

    def test_validation_mse_matches_sealed_arithmetic(self) -> None:
        rng = np.random.default_rng(0)
        pred = rng.integers(0, 10, size=(2, 4, 3)).astype(np.float32)
        gold = rng.integers(0, 10, size=(2, 4, 3)).astype(np.float32)
        error = pred.astype(np.float64) - gold.astype(np.float64)
        self.assertEqual(baselines.mse(pred, gold), float(np.square(error).mean()))
        self.assertEqual(baselines.mae(pred, gold), float(np.abs(error).mean()))


if __name__ == "__main__":
    unittest.main()
