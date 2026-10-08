"""Protocol constants, split assertions, CLI surface and run-ID safety."""

from __future__ import annotations

import unittest
from pathlib import Path

from benchmark.nograph_baseline import cli, protocol
from benchmark.nograph_baseline.artifacts import ArtifactError, validate_run_id


class SplitTests(unittest.TestCase):
    def test_calendar_has_36_continuous_months(self) -> None:
        self.assertEqual(len(protocol.MONTHS), 36)
        self.assertEqual(protocol.MONTHS[0], "2021-01")
        self.assertEqual(protocol.MONTHS[-1], "2023-12")
        self.assertEqual(protocol.TRAIN_OBSERVATION_MONTHS[0], "2021-01")
        self.assertEqual(protocol.TRAIN_OBSERVATION_MONTHS[-1], "2023-03")

    def test_window_count_and_split_membership(self) -> None:
        self.assertEqual(protocol.N_WINDOWS, 28)
        self.assertEqual(protocol.SPLITS["train"], tuple(range(19)))
        self.assertEqual(protocol.SPLITS["validation"], (21,))
        self.assertEqual(protocol.SPLITS["test"], (24, 25, 26, 27))
        self.assertEqual(protocol.OMITTED_STARTS, (19, 20, 22, 23))

    def test_target_months_are_pairwise_disjoint_and_expected(self) -> None:
        protocol.validate_split_assertions()
        targets = {
            name: {
                month
                for start in starts
                for month in protocol.window_target_months(start)
            }
            for name, starts in protocol.SPLITS.items()
        }
        self.assertFalse(targets["train"] & targets["validation"])
        self.assertFalse(targets["train"] & targets["test"])
        self.assertFalse(targets["validation"] & targets["test"])
        self.assertEqual(
            sorted(targets["validation"]), ["2023-04", "2023-05", "2023-06"]
        )
        self.assertEqual(
            sorted(targets["test"]),
            [
                "2023-07",
                "2023-08",
                "2023-09",
                "2023-10",
                "2023-11",
                "2023-12",
            ],
        )

    def test_second_test_origin_uses_then_observed_history(self) -> None:
        start = 25
        self.assertEqual(
            list(protocol.window_input_months(start)),
            ["2023-02", "2023-03", "2023-04", "2023-05", "2023-06", "2023-07"],
        )
        self.assertEqual(
            list(protocol.window_target_months(start)),
            ["2023-08", "2023-09", "2023-10"],
        )
        self.assertEqual(protocol.window_forecast_origin(start), "2023-07")

    def test_window_metadata_lists_splits_and_omissions(self) -> None:
        metadata = protocol.build_window_metadata()
        self.assertEqual(metadata["n_windows"], 28)
        self.assertEqual(metadata["omitted_starts"], [19, 20, 22, 23])
        self.assertEqual(len(metadata["windows"]), 28)
        omitted = [
            window for window in metadata["windows"] if window["split"] is None
        ]
        self.assertEqual([window["start"] for window in omitted], [19, 20, 22, 23])


class CliSurfaceTests(unittest.TestCase):
    def test_help_lists_stable_commands(self) -> None:
        parser = cli.build_parser()
        help_text = parser.format_help()
        for command in ("run", "recompute", "compare", "align-v2"):
            self.assertIn(command, help_text)
        self.assertNotIn("_worker-run", help_text)

    def test_supported_datasets_and_modes_are_enforced(self) -> None:
        parser = cli.build_parser()
        run_help = parser._subparsers._group_actions[0].choices["run"].format_help()
        self.assertIn("{r0,region}", run_help)
        self.assertIn("{count}", run_help)
        with self.assertRaises(SystemExit):
            parser.parse_args(["run", "--data-name", "r2", "--run-id", "x"])
        with self.assertRaises(SystemExit):
            parser.parse_args(
                ["run", "--data-name", "r0", "--mode", "rate", "--run-id", "x"]
            )

    def test_module_relative_default_paths(self) -> None:
        self.assertEqual(
            protocol.DEMAND_DIR, protocol.REPO_ROOT / "dataset" / "demand"
        )
        self.assertEqual(
            protocol.GRAPH_DIR, protocol.REPO_ROOT / "dataset" / "graph"
        )
        self.assertEqual(
            protocol.RUNS_DIR, protocol.REPO_ROOT / "research" / "runs"
        )
        self.assertEqual(
            protocol.demand_path("r0"), protocol.DEMAND_DIR / "r0.parquet"
        )
        self.assertEqual(
            protocol.graph_path("region"), protocol.GRAPH_DIR / "region.parquet"
        )
        self.assertTrue(protocol.PROTOCOL_PATH.name == "protocol.md")

    def test_run_id_safety(self) -> None:
        for good in ("p01-r0-sharedridge-001", "a", "A.b_c-9"):
            self.assertEqual(validate_run_id(good), good)
        for bad in ("", ".", "..", "a/b", "../escape", "has space", "-leading"):
            with self.assertRaises(ArtifactError):
                validate_run_id(bad)


if __name__ == "__main__":
    unittest.main()
