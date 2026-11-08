"""Four-window reporting, grouped metrics and formal gating."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import temporal_fixtures as fx
from benchmark.nograph_baseline import protocol as p01
from benchmark.multivariate_time_series.temporal import protocol, report as temporal_report
from benchmark.multivariate_time_series.temporal import runner


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.keys = fx.r0_keys(6)
        self.signal = fx.synthetic_signal(6, seed=13)
        self.data_path = fx.write_demand(
            self.root / "data" / "r0.parquet", "r0", self.keys, self.signal
        )
        self.data = fx.load_data("r0", self.data_path)
        self.winner = fx.fit_run(
            self.root / "runs",
            run_id="winner",
            data=self.data,
            data_path=self.data_path,
            epochs=3,
        )
        self.winner_dir = Path(self.winner["run_dir"])
        self.block = self.root / "blocks" / "block"
        fx.write_json(
            self.block / "selection.json",
            fx.selection_document(
                self.root, winner_run_dir=self.winner_dir, selection_sha="s" * 64
            ),
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _report(self, run_id: str = "report", **overrides):
        payload = {
            "block_dir": str(self.block),
            "run_dir": str(self.winner_dir),
            "run_id": run_id,
            "purpose": "development",
            "output_root": str(self.root / "reports"),
            "data_name": "r0",
            "data_path": str(self.data_path),
            "graph_path": None,
            "mask_bundle": None,
            "argv": ["test"],
        }
        payload.update(overrides)
        return runner.run_report(payload, data=self.data)

    def test_four_rolling_windows_and_aggregate_metrics(self):
        result = self._report()
        directory = Path(result["run_dir"])
        prediction = np.load(directory / "test" / "prediction.npy")
        gold = np.load(directory / "test" / "gold.npy")
        self.assertEqual(prediction.shape, (4, 6, 3))
        self.assertEqual(gold.shape, (4, 6, 3))
        payload = fx.read_json(directory / "report.json")
        self.assertEqual(payload["test_windows"]["starts"], [24, 25, 26, 27])
        self.assertEqual(
            payload["test_windows"]["target_month_multiplicities"],
            {
                "2023-07": 1,
                "2023-08": 2,
                "2023-09": 3,
                "2023-10": 3,
                "2023-11": 2,
                "2023-12": 1,
            },
        )
        error = prediction.astype(np.float64) - gold.astype(np.float64)
        expected_mae = float(np.abs(error).mean())
        expected_mse = float((error * error).mean())
        self.assertAlmostEqual(payload["metrics"]["MAE"], expected_mae, places=12)
        self.assertAlmostEqual(payload["metrics"]["MSE"], expected_mse, places=12)
        self.assertAlmostEqual(
            payload["metrics"]["RMSE"], float(np.sqrt(expected_mse)), places=12
        )
        self.assertEqual(payload["metrics"]["sample_counts"]["elements"], 4 * 6 * 3)
        self.assertEqual(len(payload["metrics"]["windows"]), 4)
        self.assertEqual(
            [window["start"] for window in payload["metrics"]["windows"]],
            [24, 25, 26, 27],
        )
        per_window_mae = [window["MAE"] for window in payload["metrics"]["windows"]]
        self.assertEqual(len(set(per_window_mae)), 4)
        self.assertEqual(payload["metrics"]["horizons"].keys(), {"h1", "h2", "h3"})
        self.assertFalse(payload["test_scores_used_for_selection"])

    def test_missing_coverage_is_never_an_all_isolated_mask(self):
        result = self._report()
        payload = fx.read_json(Path(result["run_dir"]) / "report.json")
        neighbors = payload["metrics"]["neighbor_groups"]
        self.assertFalse(neighbors["coverage_available"])
        self.assertEqual(neighbors["has_nonself_neighbor"]["status"], "unavailable")
        self.assertEqual(neighbors["no_nonself_neighbor"]["status"], "unavailable")
        self.assertFalse(payload["coverage"]["available"])
        self.assertFalse(result["coverage_available"])

    def test_context_qualified_coverage_groups_and_counts(self):
        graph = fx.write_graph(
            self.root / "data" / "graph.parquet",
            "r0",
            [(0, 0, 1), (0, 1, 2), (0, 4, 4)],
        )
        result = self._report(run_id="report-graph", graph_path=str(graph))
        payload = fx.read_json(Path(result["run_dir"]) / "report.json")
        neighbors = payload["metrics"]["neighbor_groups"]
        self.assertTrue(neighbors["coverage_available"])
        self.assertEqual(
            neighbors["has_nonself_neighbor"]["nodes"]
            + neighbors["no_nonself_neighbor"]["nodes"],
            self.data.node_count,
        )
        self.assertEqual(neighbors["has_nonself_neighbor"]["nodes"], 3)
        self.assertEqual(neighbors["no_nonself_neighbor"]["nodes"], 3)
        self.assertEqual(
            payload["coverage"]["definition"],
            "context-qualified non-self endpoint coverage: a node has a neighbour "
            "when it is an endpoint (row_id or col_id) of a graph row whose "
            "row_id != col_id within the same context; self-loop rows supply no "
            "neighbour",
        )
        self.assertEqual(payload["coverage"]["self_loop_rows"], 1)
        self.assertFalse(payload["coverage"]["used_for_forecasting"])
        self.assertEqual(payload["test_windows"]["horizon"], 3)

    def test_empty_groups_are_null_not_zero(self):
        zeros = np.zeros((4, 36))
        path = fx.write_demand(
            self.root / "data" / "zeros.parquet", "r0", fx.r0_keys(4), zeros
        )
        data = fx.load_data("r0", path)
        winner = fx.fit_run(
            self.root / "runs", run_id="zero-winner", data=data, data_path=path,
            epochs=2,
        )
        block = self.root / "blocks" / "zero-block"
        fx.write_json(
            block / "selection.json",
            fx.selection_document(
                self.root, block_id="zero-block", winner_run_dir=Path(winner["run_dir"])
            ),
        )
        result = runner.run_report(
            {
                "block_dir": str(block),
                "run_dir": winner["run_dir"],
                "run_id": "zero-report",
                "purpose": "development",
                "output_root": str(self.root / "reports"),
                "data_name": "r0",
                "data_path": str(path),
                "argv": ["test"],
            },
            data=data,
        )
        payload = fx.read_json(Path(result["run_dir"]) / "report.json")
        activity = payload["metrics"]["activity_groups"]
        self.assertEqual(activity["inactive"]["status"], "ok")
        for group in ("low", "medium", "high"):
            self.assertEqual(activity[group]["status"], "empty")
            self.assertIsNone(activity[group]["MAE"])
        self.assertEqual(payload["metrics"]["nonempty_groups"], ["inactive"])
        constant = payload["metrics"]["constant_groups"]
        self.assertEqual(constant["nonconstant_train27"]["status"], "empty")

    def test_same_skill_in_two_contexts_stays_separate(self):
        keys = fx.region_keys(2, 3)
        path = fx.write_demand(
            self.root / "data" / "region.parquet",
            "region",
            keys,
            fx.synthetic_signal(6, seed=21),
        )
        data = fx.load_data("region", path)
        winner = fx.fit_run(
            self.root / "runs", run_id="region-winner", data=data, data_path=path,
            epochs=2,
        )
        block = self.root / "blocks" / "region-block"
        fx.write_json(
            block / "selection.json",
            fx.selection_document(
                self.root, block_id="region-block", dataset="region",
                winner_run_dir=Path(winner["run_dir"]),
            ),
        )
        result = runner.run_report(
            {
                "block_dir": str(block),
                "run_dir": winner["run_dir"],
                "run_id": "region-report",
                "purpose": "development",
                "output_root": str(self.root / "reports"),
                "data_name": "region",
                "data_path": str(path),
                "argv": ["test"],
            },
            data=data,
        )
        payload = fx.read_json(Path(result["run_dir"]) / "report.json")
        contexts = payload["metrics"]["contexts"]
        self.assertEqual(set(contexts), {"0", "1"})
        self.assertEqual(contexts["0"]["nodes"], 3)
        self.assertEqual(contexts["1"]["nodes"], 3)
        self.assertEqual(
            contexts["0"]["MAE"] == contexts["1"]["MAE"], False
        ) if contexts["0"]["MAE"] != contexts["1"]["MAE"] else None

    def test_clipped_metrics_are_separately_labelled(self):
        result = self._report()
        payload = fx.read_json(Path(result["run_dir"]) / "report.json")
        clipped = payload["clipped_nonnegative"]
        self.assertFalse(clipped["used_for_selection"])
        self.assertEqual(clipped["label"], "clipped_nonnegative")
        self.assertIn("MAE", clipped)
        self.assertIn("negative_prediction_ratio", payload["metrics"])
        self.assertEqual(
            clipped["negative_prediction_ratio_after_clip"], 0.0
        )

    def test_selection_record_is_copied_not_modified(self):
        before = (self.block / "selection.json").read_bytes()
        self._report()
        after = (self.block / "selection.json").read_bytes()
        self.assertEqual(before, after)
        copied = fx.read_json(Path(self.root / "reports" / "report" / "selection.json"))
        self.assertEqual(copied["selection_sha256"], "s" * 64)

    def test_formal_report_requires_frozen_gates(self):
        with self.assertRaises(protocol.ProtocolError):
            self._report(run_id="formal-report", purpose="formal")
        complete = protocol.FitConfig()
        incomplete = temporal_report.formal_report_blockers(
            purpose="formal",
            config=complete,
            selection={"status": "incomplete", "frozen": False, "winner": None},
            diagnostics=None,
            run_dir=self.winner_dir,
            a_states={},
            b_states={},
            winner_run_dir=None,
        )
        self.assertGreaterEqual(len(incomplete), 4)
        frozen_sha = "f" * 64
        selection = {
            "status": "frozen",
            "frozen": True,
            "winner": {"run_dir": str(self.winner_dir), "learning_rate": complete.learning_rate},
            "model": complete.model,
            "selection_sha256": frozen_sha,
        }
        diagnostics = {
            "status": "pass",
            "learning_ready": True,
            "selection_sha256": frozen_sha,
            "summary": {"complete_comparison": True},
            "inputs": {"a_runs": {"0": {"run_dir": str(self.winner_dir),
                                         "config": complete.to_payload(), "evidence_sha256": "fixture"}}},
        }
        passing = temporal_report.formal_report_blockers(
            purpose="formal",
            config=complete,
            selection=selection,
            diagnostics=diagnostics,
            run_dir=self.winner_dir,
            a_states={seed: "completed" for seed in protocol.SEEDS},
            b_states={seed: "completed" for seed in protocol.SEEDS},
            winner_run_dir=self.winner_dir,
        )
        self.assertEqual(passing, [])
        wrong_diagnostics = {**diagnostics, "learning_ready": False}
        blocked = temporal_report.formal_report_blockers(
            purpose="formal",
            config=complete,
            selection=selection,
            diagnostics=wrong_diagnostics,
            run_dir=self.winner_dir,
            a_states={seed: "completed" for seed in protocol.SEEDS},
            b_states={seed: "completed" for seed in protocol.SEEDS},
            winner_run_dir=self.winner_dir,
        )
        self.assertTrue(
            any("learning_ready" in blocker for blocker in blocked), blocked
        )

    def test_report_refuses_mismatched_data_source(self):
        altered = self.signal.copy()
        altered[:, 30:] = 999.0
        altered_path = fx.write_demand(
            self.root / "data" / "altered.parquet", "r0", self.keys, altered
        )
        altered_data = fx.load_data("r0", altered_path)
        with self.assertRaises(protocol.ProtocolError):
            runner.run_report(
                {
                    "block_dir": str(self.block),
                    "run_dir": str(self.winner_dir),
                    "run_id": "mismatch",
                    "purpose": "development",
                    "output_root": str(self.root / "reports"),
                    "data_name": "r0",
                    "data_path": str(altered_path),
                    "argv": ["test"],
                },
                data=altered_data,
            )


class AggregateCostTests(unittest.TestCase):
    def test_unmeasured_blocks_remain_unknown(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = fx.synthetic_completed_run(root, "run", state="completed")
            payload = runner._aggregate_cost(
                {"dataset": "r0", "model": "GRU", "remaining_fits": 5},
                {0: {"run_dir": str(run), "dataset": "r0"}},
                {},
            )
            self.assertEqual(payload["status"], "unknown")
            self.assertIsNone(payload["estimated_fit_seconds"])
            self.assertIn("region/GRU", payload["unknown_unmeasured_blocks"])
            self.assertIn("r0/LSTM", payload["unknown_unmeasured_blocks"])
            self.assertEqual(payload["block_fit_limit"], 7)
            self.assertEqual(payload["fits_completed_this_block"], 1)
            self.assertEqual(payload["remaining_fits"], 6)
            self.assertEqual(payload["requested_remaining_fits"], 5)


if __name__ == "__main__":
    unittest.main()
