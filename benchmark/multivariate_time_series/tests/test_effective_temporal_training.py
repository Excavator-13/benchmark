import json
import unittest
from pathlib import Path

import numpy as np

from benchmark.multivariate_time_series.effective_temporal_training import (
    Config, RecurrentForecaster, load_checkpoint, make_windows, train, training_rms,
)


class EffectiveTemporalTrainingTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(7)
        self.values = np.abs(rng.normal(10, 2, size=(8, 36)))

    def test_rms_uses_training_period_only(self):
        base = self.values.copy()
        altered = base.copy()
        altered[:, 27:] = 10_000
        self.assertEqual(training_rms(base[:, :27]), training_rms(altered[:, :27]))

    def test_window_boundaries(self):
        x, y = make_windows(self.values, 0, 19)
        self.assertEqual(x.shape, (8, 19, 6))
        self.assertEqual(y.shape, (8, 19, 3))
        np.testing.assert_array_equal(x[:, 0], self.values[:, :6])
        np.testing.assert_array_equal(y[:, -1], self.values[:, 24:27])

    def test_model_and_manifest(self):
        td = Path("scratch") / "test-effective-temporal-training"
        td.mkdir(parents=True, exist_ok=True)
        for child in td.iterdir():
            if child.is_file():
                child.unlink()
        out = train(self.values, Config(model="LSTM", seed=2, epochs=2, hidden_size=4, layers=1, node_chunk=3), td)
        self.assertEqual(out["protocol_version"], "P2-effective-training-L6-H3-v1")
        self.assertTrue((td / "checkpoint.pt").exists())
        self.assertEqual(set(out["metrics"]), {"val", "test"})
        self.assertEqual(json.loads((td / "summary.json").read_text())["config"]["model"], "LSTM")
        restored = RecurrentForecaster("LSTM", 4, 1)
        manifest = load_checkpoint(td / "checkpoint.pt", restored)
        self.assertEqual(manifest["config"]["model"], "LSTM")


if __name__ == "__main__":
    unittest.main()
