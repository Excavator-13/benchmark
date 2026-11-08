"""Public entry surface: helpers, migration errors and an in-process chain."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

import temporal_fixtures as fx
from benchmark.multivariate_time_series import effective_temporal_training as entry
from benchmark.multivariate_time_series.temporal import checks, protocol, runner


class PublicSurfaceTests(unittest.TestCase):
    def test_versions_and_config_alias(self):
        self.assertEqual(entry.PROTOCOL_VERSION, "P2-effective-training-L6-H3-v1")
        self.assertEqual(entry.SCIENTIFIC_VERSION, protocol.SCIENTIFIC_VERSION)
        self.assertEqual(entry.ARTIFACT_FORMAT_VERSION, 2)
        self.assertIs(entry.Config, protocol.FitConfig)

    def test_training_rms_helper_uses_the_training_only_definition(self):
        values = np.zeros((2, 27))
        values[0, 0], values[0, 1] = 3.0, 4.0
        self.assertAlmostEqual(entry.training_rms(values), 1.0)
        values[1, 0] = 40.0
        expected = np.sqrt((9 + 16 + 1600) / 54)
        self.assertAlmostEqual(entry.training_rms(values), float(expected))
        changed = values.copy()
        self.assertAlmostEqual(
            entry.training_rms(values), entry.training_rms(changed)
        )
        with self.assertRaises(ValueError):
            entry.training_rms(np.zeros((2, 36)))

    def test_make_windows_helper_keeps_the_l6_h3_offsets(self):
        values = np.arange(3 * 36, dtype=np.float64).reshape(3, 36)
        inputs, targets = entry.make_windows(values, 24, count=4)
        self.assertEqual(inputs.shape, (3, 4, 6))
        self.assertEqual(targets.shape, (3, 4, 3))
        np.testing.assert_array_equal(inputs[:, 0], values[:, 24:30])
        np.testing.assert_array_equal(targets[:, 3], values[:, 33:36])

    def test_lazy_model_import_keeps_protocol_parameter_counts(self):
        for kind, expected in (("GRU", 3459), ("LSTM", 4579)):
            model = entry.RecurrentForecaster(kind, protocol.HIDDEN_SIZE, 1)
            self.assertEqual(
                sum(parameter.numel() for parameter in model.parameters()), expected
            )
        with self.assertRaises(AttributeError):
            entry.NotARealName

    def test_legacy_calls_are_rejected_with_migration_guidance(self):
        for call in (
            lambda: entry.train(np.zeros((2, 36)), entry.Config(), Path("x")),
            lambda: entry.compare(np.zeros((2, 36)), ("GRU",), (0,), Path("x")),
            lambda: entry.load_checkpoint(Path("x.pt"), None),
        ):
            with self.assertRaises(entry.LegacyInvocationError) as context:
                call()
            self.assertIn("staged", str(context.exception))
            self.assertIn("report", str(context.exception))

    def test_main_returns_usage_status_for_unknown_operation(self):
        self.assertEqual(entry.main(["not-an-operation"]), 2)
        self.assertEqual(entry.main(["--help"]), 0)


class StagedChainTests(unittest.TestCase):
    """One fit -> select -> diagnose -> report -> recompute/compare chain."""

    def test_development_chain_in_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_path = fx.write_demand(
                root / "r0.parquet",
                "r0",
                fx.r0_keys(3),
                fx.synthetic_signal(3, seed=4),
            )
            data = fx.load_data("r0", data_path)
            low = fx.fit_run(
                root / "runs",
                run_id="cand-1e-3",
                data=data,
                data_path=data_path,
                epochs=1,
                candidate_role="screening",
            )
            high = fx.fit_run(
                root / "runs",
                run_id="cand-3e-3",
                data=data,
                data_path=data_path,
                learning_rate=3e-3,
                epochs=1,
                candidate_role="screening",
            )
            selection = runner.run_select(
                {
                    "block_id": "chain-block",
                    "purpose": "development",
                    "output_root": str(root / "blocks"),
                    "candidates": [low["run_dir"], high["run_dir"]],
                    "argv": ["test"],
                }
            )
            block = Path(selection["block_dir"])
            a_run = fx.fit_run(
                root / "runs", run_id="a0", data=data, data_path=data_path, epochs=1
            )
            b_run = fx.fit_run(
                root / "runs",
                run_id="b0",
                data=data,
                data_path=data_path,
                epochs=1,
                repeat_role="b",
            )
            diagnosis = runner.run_diagnose(
                {
                    "block_dir": str(block),
                    "purpose": "development",
                    "a_runs": {0: a_run["run_dir"]},
                    "b_runs": {0: b_run["run_dir"]},
                    "report_path": str(root / "diagnose.json"),
                    "argv": ["test"],
                }
            )
            self.assertEqual(diagnosis["status"], "incomplete")
            report = runner.run_report(
                {
                    "block_dir": str(block),
                    "run_dir": selection["selection"]["winner"]["run_dir"],
                    "run_id": "report",
                    "purpose": "development",
                    "output_root": str(root / "runs"),
                    "data_name": "r0",
                    "data_path": str(data_path),
                    "argv": ["test"],
                },
                data=data,
            )
            self.assertEqual(report["status"], "development_incomplete")
            recompute = checks.run_recompute(
                run_dir=Path(report["run_dir"]),
                report_path=root / "recompute.json",
                argv=["test"],
            )
            self.assertEqual(recompute["status"], "pass")
            compare = checks.run_compare(
                run_a=Path(a_run["run_dir"]),
                run_b=Path(b_run["run_dir"]),
                report_path=root / "compare.json",
                argv=["test"],
            )
            self.assertEqual(compare["status"], "pass")
            for relative in (
                "test/prediction.npy",
                "test/gold.npy",
                "report.json",
                "provenance.json",
                "summary.md",
            ):
                self.assertTrue(
                    (Path(report["run_dir"]) / relative).is_file(), relative
                )
            self.assertEqual(
                torch.load(
                    Path(report["run_dir"]) / "weights" / "best.pt",
                    weights_only=False,
                )["kind"],
                "best",
            )


if __name__ == "__main__":
    unittest.main()
