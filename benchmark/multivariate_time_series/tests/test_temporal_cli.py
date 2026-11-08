"""CLI surface: staged operations, migration errors and a development chain."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

import temporal_fixtures as fx
from benchmark.multivariate_time_series.temporal import protocol

MODULE = "benchmark.multivariate_time_series.effective_temporal_training"
REPO_ROOT = Path(__file__).resolve().parents[3]


def run_cli(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", MODULE, *arguments],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


class CliContractTests(unittest.TestCase):
    def test_help_lists_every_staged_operation_without_data(self):
        completed = run_cli("--help")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for operation in protocol.OPERATIONS:
            self.assertIn(operation, completed.stdout)

    def test_legacy_invocation_is_rejected_with_migration_message(self):
        completed = run_cli(
            "--data", "dataset/demand/r0.parquet", "--run-dir", "scratch/legacy"
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("staged", completed.stderr)
        self.assertIn("fit", completed.stderr)
        self.assertIn("select", completed.stderr)
        self.assertIn("report", completed.stderr)

    def test_invalid_option_and_value_are_usage_errors(self):
        completed = run_cli("fit", "--nonsense")
        self.assertEqual(completed.returncode, 2)
        completed = run_cli(
            "fit",
            "--data-name", "r9",
            "--run-id", "x",
        )
        self.assertEqual(completed.returncode, 2)

    def test_development_output_alias_into_formal_namespace_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = fx.write_demand(
                root / "r0.parquet", "r0", fx.r0_keys(3), fx.synthetic_signal(3, seed=2)
            )
            formal = REPO_ROOT / "research" / "runs"
            completed = run_cli(
                "fit",
                "--data-name", "r0",
                "--data", str(data),
                "--model", "GRU",
                "--seed", "0",
                "--epochs", "1",
                "--hidden-size", "4",
                "--node-chunk", "3",
                "--run-id", "e13-cli-alias",
                "--purpose", "development",
                "--output-root", str(formal),
                "--memory-available-bytes", str(16 * protocol.GIB),
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse((formal / "e13-cli-alias").exists())
            link = root / "linked"
            link.symlink_to(formal, target_is_directory=True)
            completed = run_cli(
                "fit",
                "--data-name", "r0",
                "--data", str(data),
                "--model", "GRU",
                "--seed", "0",
                "--epochs", "1",
                "--hidden-size", "4",
                "--node-chunk", "3",
                "--run-id", "e13-cli-alias-2",
                "--purpose", "development",
                "--output-root", str(link),
                "--memory-available-bytes", str(16 * protocol.GIB),
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse((formal / "e13-cli-alias-2").exists())


class DevelopmentChainTests(unittest.TestCase):
    """One temporary r0/GRU chain through every staged CLI operation."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.report_dir = self.root / "reports"
        self.data = fx.write_demand(
            self.root / "r0.parquet",
            "r0",
            fx.r0_keys(4),
            fx.synthetic_signal(4, seed=31),
        )
        self.common = [
            "--data-name", "r0",
            "--data", str(self.data),
            "--model", "GRU",
            "--epochs", "1",
            "--hidden-size", "4",
            "--layers", "1",
            "--node-chunk", "3",
            "--purpose", "development",
            "--output-root", str(self.root / "runs"),
            "--memory-available-bytes", str(16 * protocol.GIB),
        ]

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _fit(self, run_id: str, seed: int, learning_rate: float, role: str,
             candidate: str) -> subprocess.CompletedProcess:
        completed = run_cli(
            "fit",
            *self.common,
            "--seed", str(seed),
            "--learning-rate", str(learning_rate),
            "--run-id", run_id,
            "--candidate-role", candidate,
            "--repeat-role", role,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return completed

    def test_staged_development_chain_and_saved_only_checks(self):
        self._fit("cand-low", 0, 1e-3, "a", "screening")
        self._fit("cand-high", 0, 3e-3, "a", "screening")
        self._fit("a0", 0, 1e-3, "a", "confirmation")
        self._fit("b0", 0, 1e-3, "b", "confirmation")
        select = run_cli(
            "select",
            "--candidate", str(self.root / "runs" / "cand-low"),
            "--candidate", str(self.root / "runs" / "cand-high"),
            "--block-id", "cli-block",
            "--purpose", "development",
            "--output-root", str(self.root / "blocks"),
        )
        self.assertEqual(select.returncode, 0, select.stdout + select.stderr)
        block = self.root / "blocks" / "cli-block"
        self.assertTrue((block / "selection.json").is_file())
        diagnose = run_cli(
            "diagnose",
            "--block", str(block),
            "--a-run", f"0={self.root / 'runs' / 'a0'}",
            "--b-run", f"0={self.root / 'runs' / 'b0'}",
            "--purpose", "development",
            "--report", str(self.report_dir / "diagnose.json"),
        )
        self.assertEqual(
            diagnose.returncode, 1, diagnose.stdout + diagnose.stderr
        )
        self.assertTrue((self.report_dir / "diagnose.json").is_file())
        first_report = fx.read_json(self.report_dir / "diagnose.json")
        self.assertEqual(first_report["status"], "failed")
        self.assertFalse((block / "latest-diagnostics.json").exists())
        self.assertFalse((block / "diagnostics").exists())
        second = run_cli(
            "diagnose",
            "--block", str(block),
            "--a-run", f"0={self.root / 'runs' / 'a0'}",
            "--b-run", f"0={self.root / 'runs' / 'b0'}",
            "--purpose", "development",
            "--diagnostics-id", "second-diagnostics",
            "--report", str(self.report_dir / "diagnose-2.json"),
        )
        self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
        self.assertTrue((self.report_dir / "diagnose-2.json").exists())
        collision = run_cli(
            "diagnose",
            "--block", str(block),
            "--a-run", f"0={self.root / 'runs' / 'a0'}",
            "--purpose", "development",
            "--diagnostics-id", "second-diagnostics",
            "--report", str(self.report_dir / "diagnose-2.json"),
        )
        self.assertEqual(collision.returncode, 1, collision.stdout + collision.stderr)

        report = run_cli(
            "report",
            "--data-name", "r0",
            "--data", str(self.data),
            "--block", str(block),
            "--run", str(self.root / "runs" / "cand-low"),
            "--run-id", "cli-report",
            "--purpose", "development",
            "--output-root", str(self.root / "runs"),
        )
        self.assertEqual(report.returncode, 4, report.stdout + report.stderr)
        report_dir = self.root / "runs" / "cli-report"
        payload = fx.read_json(report_dir / "report.json")
        self.assertEqual(payload["test_windows"]["starts"], [24, 25, 26, 27])
        self.assertEqual(payload["status"], "development_incomplete")
        self.assertFalse(payload["protocol_complete"])

        recompute = run_cli(
            "recompute",
            "--run-dir", str(report_dir),
            "--report", str(self.report_dir / "recompute.json"),
        )
        self.assertEqual(recompute.returncode, 0, recompute.stdout + recompute.stderr)
        compare = run_cli(
            "compare",
            "--run-a", str(self.root / "runs" / "a0"),
            "--run-b", str(self.root / "runs" / "b0"),
            "--report", str(self.report_dir / "compare.json"),
        )
        self.assertEqual(compare.returncode, 0, compare.stdout + compare.stderr)
        self.assertEqual(fx.read_json(self.report_dir / "compare.json")["status"], "pass")

    def test_region_and_r2_with_the_second_encoder(self):
        cases = [
            ("region", fx.region_keys(2, 2), "LSTM"),
            ("r2", fx.r2_keys(2, 2), "GRU"),
        ]
        for data_name, keys, model in cases:
            with self.subTest(dataset=data_name, model=model):
                data = fx.write_demand(
                    self.root / f"{data_name}.parquet",
                    data_name,
                    keys,
                    fx.synthetic_signal(len(keys), seed=17),
                )
                completed = run_cli(
                    "fit",
                    "--data-name", data_name,
                    "--data", str(data),
                    "--model", model,
                    "--epochs", "1",
                    "--hidden-size", "4",
                    "--node-chunk", "3",
                    "--run-id", f"cli-{data_name}-{model.lower()}",
                    "--purpose", "development",
                    "--output-root", str(self.root / "runs"),
                    "--memory-available-bytes", str(16 * protocol.GIB),
                )
                self.assertEqual(
                    completed.returncode, 0, completed.stdout + completed.stderr
                )
                config = fx.read_json(
                    self.root / "runs" / f"cli-{data_name}-{model.lower()}" / "config.json"
                )
                self.assertEqual(config["dataset"]["name"], data_name)
                self.assertEqual(config["config"]["model"], model)
                provenance = fx.read_json(
                    self.root / "runs" / f"cli-{data_name}-{model.lower()}" / "provenance.json"
                )
                self.assertEqual(provenance["data"]["dataset"], data_name)
                self.assertEqual(
                    provenance["data"]["key_columns"],
                    list(fx.p01.node_key_columns(data_name)),
                )


class PreflightCliTests(unittest.TestCase):
    def test_formal_preflight_rejects_injected_resource_readings(self):
        completed = run_cli(
            "preflight",
            "--purpose", "formal",
            "--run-id", "formal-preflight",
            "--memory-available-bytes", str(16 * protocol.GIB),
        )
        self.assertEqual(completed.returncode, 2, completed.stdout)
        self.assertIn("development software", completed.stdout + completed.stderr)

    def test_preflight_is_machine_readable_without_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            completed = run_cli(
                "preflight",
                "--purpose", "development",
                "--run-id", "cli-preflight",
                "--output-root", temporary,
                "--memory-available-bytes", str(16 * protocol.GIB),
                "--disk-free-bytes", str(10 * protocol.GIB),
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["checks"]["data"]["status"], "not_supplied")
            self.assertEqual(payload["checks"]["threads"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
