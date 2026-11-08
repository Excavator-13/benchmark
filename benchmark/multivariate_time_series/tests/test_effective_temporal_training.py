import json
import unittest
from unittest import mock
from pathlib import Path

import numpy as np

import benchmark.multivariate_time_series.effective_temporal_training as ett

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

    def test_window_count_rejects_overrun(self):
        with self.assertRaises(ValueError):
            make_windows(self.values, 28, 2)

    def test_invalid_config_rejected(self):
        with self.assertRaisesRegex(ValueError, "learning_rate"):
            Config(learning_rate=float("nan"))
        with self.assertRaisesRegex(ValueError, "epochs"):
            Config(epochs=0)

    def test_test_window_is_deferred_until_after_validation(self):
        calls = []
        original = ett.make_windows

        def guarded(values, start, count=1):
            calls.append(int(start))
            return original(values, start, count)

        with mock.patch.object(ett, "make_windows", side_effect=guarded):
            train(self.values, Config(epochs=1, hidden_size=3, node_chunk=4), Path("scratch") / "deferred-test")
        self.assertEqual(calls[:2], [0, 21])
        self.assertEqual(calls[-1], 27)

    def test_resume_matches_uninterrupted_run(self):
        root = Path("scratch") / "resume-effective-temporal-training"
        direct = root / "direct"
        resumed = root / "resumed"
        for path in (direct, resumed):
            if path.exists():
                import shutil
                shutil.rmtree(path)
        cfg1 = Config(epochs=1, hidden_size=3, node_chunk=4, seed=4)
        train(self.values, cfg1, resumed)
        train(self.values, Config(epochs=2, hidden_size=3, node_chunk=4, seed=4), resumed,
              resume_from=resumed / "checkpoint.pt")
        direct_out = train(self.values, Config(epochs=2, hidden_size=3, node_chunk=4, seed=4), direct)
        resumed_out = json.loads((resumed / "summary.json").read_text())
        self.assertEqual(resumed_out["identity_digest"], direct_out["identity_digest"])
        self.assertEqual(resumed_out["metrics"], direct_out["metrics"])
        self.assertEqual(resumed_out["current_epoch"], 2)

    def test_resume_preserves_latest_state_when_best_epoch_is_earlier(self):
        root = Path("scratch") / "resume-effective-temporal-training-late-best"
        if root.exists():
            import shutil
            shutil.rmtree(root)
        values = np.random.default_rng(0).normal(size=(2, 36))
        resumed = root / "resumed"
        direct = root / "direct"
        first = train(values, Config(epochs=10, hidden_size=8, node_chunk=2, seed=0), resumed)
        self.assertLess(first["selected_epoch"], first["current_epoch"])
        train(values, Config(epochs=11, hidden_size=8, node_chunk=2, seed=0), resumed,
              resume_from=resumed / "checkpoint.pt")
        direct_out = train(values, Config(epochs=11, hidden_size=8, node_chunk=2, seed=0), direct)
        resumed_out = json.loads((resumed / "summary.json").read_text())
        self.assertEqual(resumed_out["metrics"], direct_out["metrics"])
        self.assertEqual(resumed_out["selected_epoch"], direct_out["selected_epoch"])
        self.assertEqual(resumed_out["current_epoch"], direct_out["current_epoch"])

    def test_resume_rejects_identity_mismatch_without_mutation(self):
        root = Path("scratch") / "resume-mismatch"
        if root.exists():
            import shutil
            shutil.rmtree(root)
        train(self.values, Config(epochs=1, hidden_size=3, node_chunk=4), root)
        before = (root / "summary.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "identity"):
            train(self.values, Config(epochs=2, hidden_size=3, node_chunk=4, learning_rate=2e-3), root,
                  resume_from=root / "checkpoint.pt")
        self.assertEqual(before, (root / "summary.json").read_bytes())


if __name__ == "__main__":
    unittest.main()

