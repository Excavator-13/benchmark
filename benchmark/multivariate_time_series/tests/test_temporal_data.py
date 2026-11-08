"""Canonical identity, validation rejection and the fit/report data boundary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import temporal_fixtures as fx
from benchmark.nograph_baseline.data import DemandError
from benchmark.multivariate_time_series.temporal import data as td
from benchmark.multivariate_time_series.temporal import protocol, runner


class CanonicalIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_three_schemas_out_of_order_keep_context_qualified_keys(self):
        cases = {
            "r0": (fx.r0_keys(5), 5),
            "region": (fx.region_keys(3, 4), 12),
            "r2": (fx.r2_keys(4, 3), 12),
        }
        for data_name, (keys, expected) in cases.items():
            with self.subTest(dataset=data_name):
                signal = fx.synthetic_signal(len(keys), seed=3)
                path = fx.write_demand(
                    self.root / f"{data_name}.parquet",
                    data_name,
                    keys,
                    signal,
                    shuffle_seed=7,
                )
                data = fx.load_data(data_name, path)
                self.assertEqual(data.node_count, expected)
                key_array = data.node_keys.tolist()
                self.assertEqual(key_array, sorted(key_array))
                # Identical skills across different contexts stay distinct nodes.
                skills = [row[-1] for row in key_array]
                if data_name == "r0":
                    self.assertEqual(len(set(skills)), len(skills))
                    self.assertTrue(all(row[0] == 0 for row in key_array))
                else:
                    self.assertLess(len(set(skills)), len(skills))
                self.assertEqual(len({tuple(row) for row in key_array}), expected)
                np.testing.assert_allclose(
                    data.signal, np.asarray(signal, dtype=np.float32), rtol=0, atol=0
                )
                self.assertEqual(data.identity()["source_sha256"], fx.load_data(
                    data_name, path
                ).identity()["source_sha256"])

    def test_duplicate_keys_rejected(self):
        keys = [(0, 0), (0, 0), (0, 1)]
        path = fx.write_demand(
            self.root / "dup.parquet", "r0", keys, fx.synthetic_signal(3)
        )
        with self.assertRaises(DemandError):
            fx.load_data("r0", path)

    def test_missing_month_rejected(self):
        keys = fx.r0_keys(3)
        path = fx.write_demand(
            self.root / "missing.parquet",
            "r0",
            keys,
            fx.synthetic_signal(3),
            drop_month="2023-12",
        )
        with self.assertRaises(DemandError):
            fx.load_data("r0", path)

    def test_negative_and_nonfinite_values_rejected(self):
        for name, mutate in (
            ("negative", lambda signal: _set(signal, 0, 5, -1.0)),
            ("nan", lambda signal: _set(signal, 1, 7, float("nan"))),
            ("inf", lambda signal: _set(signal, 2, 8, float("inf"))),
        ):
            with self.subTest(case=name):
                signal = fx.synthetic_signal(3)
                mutate(signal)
                path = fx.write_demand(
                    self.root / f"{name}.parquet", "r0", fx.r0_keys(3), signal
                )
                with self.assertRaises(DemandError):
                    fx.load_data("r0", path)

    def test_unsupported_protocol_settings_rejected(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.validate_model("TRANSFORMER")
        with self.assertRaises(protocol.ProtocolError):
            protocol.validate_dataset("r9")
        with self.assertRaises(protocol.ProtocolError):
            protocol.validate_mode("share")
        with self.assertRaises(protocol.ProtocolError):
            protocol.FitConfig(learning_rate=0.5).validate()
        with self.assertRaises(protocol.ProtocolError):
            protocol.FitConfig(epochs=101).validate()
        with self.assertRaises(protocol.ProtocolError):
            protocol.FitConfig(threads=2).validate()
        with self.assertRaises(protocol.ProtocolError):
            protocol.FitConfig(node_chunk=0).validate()
        with self.assertRaises(protocol.ProtocolError):
            protocol.FitConfig(diagnostic_epochs=(5,)).validate()


class TrainingRmsTests(unittest.TestCase):
    def test_rms_definition_matches_float64_formula(self):
        signal = np.zeros((2, 36), dtype=np.float64)
        signal[0, 0], signal[0, 1] = 1.0, 2.0
        signal[1, 0], signal[1, 1] = 3.0, 4.0
        data = td.from_arrays("r0", [(0, 0), (0, 1)], signal)
        record = data.training_rms()
        expected = max(1.0, np.sqrt((1 + 4 + 9 + 16) / (2 * 27)))
        self.assertAlmostEqual(record["scale"], float(expected), places=12)
        self.assertEqual(record["elements"], 54)
        self.assertEqual(record["months"], list(protocol.train_observation_months()))
        self.assertIn("2021-01", record["months"])
        self.assertIn("2023-03", record["months"])

    def test_scale_floor_is_one_for_zero_training_values(self):
        signal = np.zeros((3, 36))
        data = td.from_arrays("r0", fx.r0_keys(3), signal)
        self.assertEqual(data.training_rms()["scale"], 1.0)


class StageBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.keys = fx.r0_keys(6)
        self.signal = fx.synthetic_signal(6, seed=5)
        self.path = fx.write_demand(
            self.root / "r0.parquet", "r0", self.keys, self.signal
        )
        self.data = fx.load_data("r0", self.path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_fit_arrays_never_include_test_months(self):
        arrays = self.data.fit_arrays()
        self.assertEqual(arrays.train_inputs.shape, (19, 6, protocol.p01.INPUT_LENGTH))
        self.assertEqual(arrays.validation_inputs.shape, (1, 6, protocol.p01.INPUT_LENGTH))
        self.assertEqual(arrays.observation_months[-1], "2023-06")
        test_months = {
            month
            for start in protocol.p01.MAIN_SPLIT.evaluation_starts
            for month in protocol.p01.window_target_months(start)
        }
        self.assertFalse(test_months & set(arrays.observation_months))
        report = self.data.report_arrays()
        self.assertEqual(report.test_targets.shape, (4, 6, 3))
        self.assertEqual(report.starts, (24, 25, 26, 27))

    def test_held_out_perturbation_leaves_training_unchanged(self):
        altered = self.signal.copy()
        altered[:, 27:] = 10_000.0
        altered_path = fx.write_demand(
            self.root / "r0-altered.parquet", "r0", self.keys, altered
        )
        altered_data = fx.load_data("r0", altered_path)
        base = fx.fit_run(self.root / "base", run_id="base", data=self.data, data_path=self.path)
        other = fx.fit_run(
            self.root / "altered",
            run_id="altered",
            data=altered_data,
            data_path=altered_path,
        )
        base_pre = fx.read_json(Path(base["run_dir"]) / "preprocessing.json")
        other_pre = fx.read_json(Path(other["run_dir"]) / "preprocessing.json")
        self.assertEqual(base_pre["scale"], other_pre["scale"])
        import torch

        left = torch.load(
            Path(base["run_dir"]) / "weights" / "best.pt", weights_only=False
        )
        right = torch.load(
            Path(other["run_dir"]) / "weights" / "best.pt", weights_only=False
        )
        self.assertEqual(left["manifest"]["epoch"], right["manifest"]["epoch"])
        for name, tensor in left["model_state"].items():
            self.assertTrue(
                torch.equal(tensor, right["model_state"][name]),
                f"held-out perturbation changed training tensor {name}",
            )
        self.assertNotAlmostEqual(
            left["manifest"]["validation"]["MSE"],
            right["manifest"]["validation"]["MSE"],
        )

    def test_test_labels_unreachable_during_fit_select_and_diagnose(self):
        sentinel = AssertionError("test labels must not be read before report")
        with mock.patch.object(td.TemporalData, "report_arrays", side_effect=sentinel):
            base = fx.fit_run(self.root / "runs", run_id="sentinel-base", data=self.data,
                              data_path=self.path)
            candidate_low = fx.fit_run(
                self.root / "runs",
                run_id="sentinel-low",
                data=self.data,
                data_path=self.path,
                learning_rate=1e-3,
                candidate_role="screening",
            )
            candidate_high = fx.fit_run(
                self.root / "runs",
                run_id="sentinel-high",
                data=self.data,
                data_path=self.path,
                learning_rate=3e-3,
                candidate_role="screening",
            )
            selection_result = runner.run_select(
                {
                    "block_id": "sentinel-block",
                    "purpose": "development",
                    "output_root": str(self.root / "blocks"),
                    "candidates": [candidate_low["run_dir"], candidate_high["run_dir"]],
                    "argv": ["test"],
                }
            )
            repeat = fx.fit_run(
                self.root / "runs",
                run_id="sentinel-b",
                data=self.data,
                data_path=self.path,
                repeat_role="b",
            )
            diagnosis = runner.run_diagnose(
                {
                    "block_dir": selection_result["block_dir"],
                    "purpose": "development",
                    "a_runs": {0: base["run_dir"]},
                    "b_runs": {0: repeat["run_dir"]},
                    "report_path": str(self.root / "diagnose.json"),
                    "argv": ["test"],
                }
            )
        self.assertEqual(base["status"], "completed")
        self.assertEqual(selection_result["status"], "frozen")
        self.assertIn(diagnosis["status"], {"incomplete", "failed", "pass"})


def _set(signal: np.ndarray, row: int, column: int, value: float) -> None:
    signal[row, column] = value


if __name__ == "__main__":
    unittest.main()
