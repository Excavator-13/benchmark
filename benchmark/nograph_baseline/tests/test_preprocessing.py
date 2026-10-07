"""Frozen training statistics, activity/constant masks and their invariance."""

from __future__ import annotations

import unittest

import numpy as np

import nb_fixtures as fx
from benchmark.nograph_baseline import baselines, protocol, ridge


def _training_shape(values: np.ndarray) -> np.ndarray:
    """Return a ``[N, 36]`` signal whose first 27 values follow ``values``."""
    signal = np.zeros((values.shape[0], protocol.N_MONTHS), dtype=np.float32)
    signal[:, :27] = values.astype(np.float32)
    signal[:, 27:] = np.arange(9, dtype=np.float32)
    return signal


class TrainingStatisticsTests(unittest.TestCase):
    def test_exactly_27_unique_observations(self) -> None:
        # A single node whose first 27 values are 0..26.
        values = np.arange(27, dtype=np.float64).reshape(1, 27)
        signal = _training_shape(values)
        stats = ridge.compute_training_stats(signal)
        self.assertAlmostEqual(float(stats.mean[0]), 13.0)
        # Overlap-weighted estimate across the 19 training windows differs.
        starts = protocol.SPLITS["train"]
        flattened = np.concatenate([signal[0, s : s + 6] for s in starts])
        self.assertNotAlmostEqual(float(flattened.mean()), float(stats.mean[0]))
        expected_std = float(values[0].std(ddof=0))
        self.assertAlmostEqual(float(stats.std[0]), expected_std)
        # ddof=0: differs from the ddof=1 estimate.
        self.assertNotAlmostEqual(expected_std, float(values[0].std(ddof=1)))
        self.assertEqual(stats.ddof, 0)

    def test_constant_node_effective_std_is_one_and_finite(self) -> None:
        values = np.full((1, 27), 7.0)
        signal = _training_shape(values)
        stats = ridge.compute_training_stats(signal)
        self.assertTrue(bool(stats.constant_mask[0]))
        self.assertEqual(float(stats.effective_std[0]), 1.0)
        standardized = stats.standardize(signal[:, :6])
        self.assertTrue(np.isfinite(standardized).all())
        self.assertTrue(np.allclose(standardized, 0.0))

    def test_four_activity_boundaries(self) -> None:
        counts = [0, 1, 9, 10, 18, 19, 27]
        values = np.zeros((len(counts), 27), dtype=np.float64)
        for row, count in enumerate(counts):
            values[row, :count] = 1.0
        stats = ridge.compute_training_stats(_training_shape(values))
        groups = stats.activity_groups
        self.assertTrue(groups["inactive"][0])
        self.assertTrue(groups["low"][1])
        self.assertTrue(groups["low"][2], "activity == 1/3 is a low boundary")
        self.assertTrue(groups["medium"][3], "activity just above 1/3 is medium")
        self.assertTrue(groups["medium"][4], "activity == 2/3 is a medium boundary")
        self.assertTrue(groups["high"][5], "activity just above 2/3 is high")
        self.assertTrue(groups["high"][6])
        partition = np.stack(list(groups.values())).sum(axis=0)
        np.testing.assert_array_equal(partition, np.ones(len(counts)))

    def test_later_values_do_not_change_statistics_or_fits(self) -> None:
        signal_a = fx.synthetic_signal(6, seed=3)
        signal_b = signal_a.copy()
        signal_b[:, 27:] = 999.0
        stats_a = ridge.compute_training_stats(signal_a)
        stats_b = ridge.compute_training_stats(signal_b)
        for array_a, array_b in (
            (stats_a.mean, stats_b.mean),
            (stats_a.std, stats_b.std),
            (stats_a.activity, stats_b.activity),
            (stats_a.train_mean27_float32, stats_b.train_mean27_float32),
        ):
            np.testing.assert_array_equal(array_a, array_b)
        for name in protocol.ACTIVITY_GROUP_NAMES:
            np.testing.assert_array_equal(
                stats_a.activity_groups[name], stats_b.activity_groups[name]
            )
        starts = protocol.SPLITS["train"]
        x_a, y_a = ridge.build_design(signal_a, stats_a, starts)
        x_b, y_b = ridge.build_design(signal_b, stats_b, starts)
        np.testing.assert_array_equal(x_a, x_b)
        np.testing.assert_array_equal(y_a, y_b)
        fit_a = ridge.fit_numpy(x_a, y_a, 0.1)
        fit_b = ridge.fit_numpy(x_b, y_b, 0.1)
        np.testing.assert_array_equal(fit_a["W"], fit_b["W"])
        np.testing.assert_array_equal(fit_a["b"], fit_b["b"])

    def test_train_mean27_uses_unique_training_months(self) -> None:
        values = np.arange(27, dtype=np.float64).reshape(1, 27)
        signal = _training_shape(values)
        frozen = baselines.train_mean27(signal)
        self.assertAlmostEqual(float(frozen[0, 0]), 13.0)
        starts = protocol.SPLITS["train"]
        flattened = np.concatenate([signal[0, s : s + 6] for s in starts])
        self.assertNotAlmostEqual(float(flattened.mean()), float(frozen[0, 0]))


if __name__ == "__main__":
    unittest.main()
