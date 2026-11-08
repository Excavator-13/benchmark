"""Format-v2 artifacts, provenance identity and saved-only checks."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import temporal_fixtures as fx
from benchmark.nograph_baseline import artifacts as nb_artifacts
from benchmark.multivariate_time_series.temporal import artifacts, checks, protocol
from benchmark.multivariate_time_series.temporal import runner


def _clone_run(source: Path, target: Path, *, config=None, provenance=None) -> Path:
    shutil.copytree(source, target)
    if config is not None:
        document = fx.read_json(target / "config.json")
        config(document)
        fx.write_json(target / "config.json", document)
    if provenance is not None:
        document = fx.read_json(target / "provenance.json")
        provenance(document)
        fx.write_json(target / "provenance.json", document)
    return target


class ArtifactIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.keys = fx.r0_keys(4)
        self.signal = fx.synthetic_signal(4, seed=3)
        self.data_path = fx.write_demand(
            self.root / "data" / "r0.parquet", "r0", self.keys, self.signal
        )
        self.data = fx.load_data("r0", self.data_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _fit(self, run_id: str, *, output_root: Path = None, **kwargs):
        return fx.fit_run(
            self.root / "runs",
            run_id=run_id,
            data=self.data,
            data_path=self.data_path,
            output_root=output_root,
            **kwargs,
        )

    def test_existing_run_identity_is_never_overwritten(self):
        first = self._fit("collision")
        before = fx.tree_digest(Path(first["run_dir"]))
        with self.assertRaises(nb_artifacts.RunExistsError):
            self._fit("collision")
        after = fx.tree_digest(Path(first["run_dir"]))
        self.assertEqual(before, after)

    def test_development_output_inside_formal_namespace_is_rejected(self):
        formal = artifacts.repo_root() / "research" / "runs"
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.check_development_namespace(
                "development", formal / "sneaky-run"
            )
        alias = self.root / "alias"
        alias.mkdir()
        (alias / "linked").symlink_to(formal, target_is_directory=True)
        with self.assertRaises(artifacts.ArtifactError):
            artifacts.check_development_namespace(
                "development", alias / "linked" / "sneaky-run"
            )
        self.assertFalse((formal / "sneaky-run").exists())
        with self.assertRaises(artifacts.ArtifactError):
            self._fit("formal-sneak", output_root=formal)
        self.assertFalse((formal / "formal-sneak").exists())

    def test_format_v2_readable_entries_and_array_manifest(self):
        result = self._fit("format")
        directory = Path(result["run_dir"])
        for name in ("provenance.json", "command.json", "report.json", "summary.md"):
            self.assertTrue((directory / name).is_file(), name)
        manifest = fx.read_json(directory / "arrays-sha256.json")
        for relative in protocol.RECOMPUTE_ARRAYS:
            if (directory / relative).is_file():
                self.assertIn(relative, manifest["arrays"])
                self.assertEqual(
                    manifest["arrays"][relative]["sha256"],
                    __import__("hashlib").sha256(
                        (directory / relative).read_bytes()
                    ).hexdigest(),
                )
        command = fx.read_json(directory / "command.json")
        self.assertEqual(command["module"], "benchmark.multivariate_time_series.effective_temporal_training")
        provenance = fx.read_json(directory / "provenance.json")
        self.assertEqual(provenance["data"]["source_kind"], "parquet")
        self.assertEqual(provenance["data"]["source_sha256"], self.data.identity()["source_sha256"])
        self.assertEqual(provenance["artifact_format_version"], 2)
        self.assertEqual(provenance["purpose"], "development")
        self.assertIn("git-diff.patch", provenance["source"]["patch_path"])
        self.assertTrue(provenance["environment"]["determinism"]["deterministic_algorithms"])

    def test_relevant_source_difference_is_captured_as_a_patch(self):
        import subprocess

        repo = self.root / "git-repo"
        relative = "benchmark/multivariate_time_series/temporal/engine.py"
        target = repo / relative
        target.parent.mkdir(parents=True)
        target.write_text("VALUE = 1\n", encoding="utf-8")
        for command in (
            ["git", "init", "-q"],
            ["git", "add", "."],
            ["git", "-c", "user.email=a@b", "-c", "user.name=test", "commit", "-qm", "seed"],
        ):
            subprocess.run(command, cwd=str(repo), check=True, capture_output=True)
        target.write_text("VALUE = 2\n", encoding="utf-8")
        run = nb_artifacts.RunDirectory(self.root / "runs", "diff", "test").reserve()
        record = nb_artifacts.capture_source(
            run, repo, runtime_paths=[relative], protocol_path=None
        )
        self.assertGreater(record["patch_bytes"], 0)
        self.assertEqual(record["files"][relative]["git_status"], "modified")
        patch = (run.path / "git-diff.patch").read_text(encoding="utf-8")
        self.assertIn("VALUE = 2", patch)
        self.assertIn("+VALUE = 2", patch)
        self.assertFalse(record["unrecoverable_paths"])

    def test_generic_ignore_policy_is_not_extended(self):
        gitignore = (artifacts.repo_root() / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/research/runs/*/**", gitignore)
        self.assertIn("!/research/runs/*/summary.md", gitignore)
        self.assertIn("!/research/runs/*/provenance.json", gitignore)
        self.assertIn("!/research/runs/*/command.json", gitignore)
        self.assertIn("!/research/runs/*/report.json", gitignore)
        self.assertNotIn("effective-temporal", gitignore)

    def test_comparison_preserves_the_actual_data_source(self):
        base = self._fit("base")
        altered = self.signal.copy()
        altered[:, 30:] = 999.0
        altered_path = fx.write_demand(
            self.root / "data" / "altered.parquet", "r0", self.keys, altered
        )
        altered_data = fx.load_data("r0", altered_path)
        other = fx.fit_run(
            self.root / "runs",
            run_id="altered",
            data=altered_data,
            data_path=altered_path,
        )
        left = np.load(Path(base["run_dir"]) / "validation" / "prediction.npy")
        right = np.load(Path(other["run_dir"]) / "validation" / "prediction.npy")
        np.testing.assert_array_equal(left, right)
        result = checks.run_compare(
            run_a=Path(base["run_dir"]),
            run_b=Path(other["run_dir"]),
            report_path=self.root / "compare-source.json",
            argv=["test"],
        )
        self.assertEqual(result["status"], "failed")
        fields = [mismatch["field"] for mismatch in result["result"]["mismatches"]]
        self.assertIn("data.source_sha256", fields)
        self.assertEqual(result["result"]["comparisons"], [])


class CompareIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.keys = fx.r0_keys(4)
        self.data_path = fx.write_demand(
            self.root / "data" / "r0.parquet", "r0", self.keys,
            fx.synthetic_signal(4, seed=6),
        )
        self.data = fx.load_data("r0", self.data_path)
        self.first = fx.fit_run(
            self.root / "runs", run_id="repeat-a", data=self.data,
            data_path=self.data_path,
        )
        self.second = fx.fit_run(
            self.root / "runs", run_id="repeat-b", data=self.data,
            data_path=self.data_path, repeat_role="b",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _compare(self, left: Path, right: Path, name: str):
        return checks.run_compare(
            run_a=Path(left),
            run_b=Path(right),
            report_path=self.root / name,
            argv=["test"],
        )

    def test_identical_runs_pass_the_same_seed_bound(self):
        result = self._compare(self.first["run_dir"], self.second["run_dir"], "ok.json")
        self.assertEqual(result["status"], "pass")
        comparison = result["result"]["comparisons"][0]
        self.assertEqual(comparison["normalized_MAE_difference"], 0.0)
        self.assertEqual(comparison["max_absolute_prediction_difference"], 0.0)
        self.assertEqual(result["result"]["test_comparison"]["status"], "not_applicable")

    def test_identical_predictions_cannot_hide_a_seed_mismatch(self):
        clone = _clone_run(
            Path(self.first["run_dir"]),
            self.root / "runs" / "seed-clone",
            config=lambda document: document["config"].__setitem__("seed", 1),
        )
        result = self._compare(self.first["run_dir"], clone, "seed.json")
        self.assertEqual(result["status"], "failed")
        fields = [mismatch["field"] for mismatch in result["result"]["mismatches"]]
        self.assertIn("config.seed", fields)

    def test_protocol_and_environment_mismatches_are_specific(self):
        protocol_clone = _clone_run(
            Path(self.first["run_dir"]),
            self.root / "runs" / "protocol-clone",
            provenance=lambda document: document["protocol"].__setitem__(
                "sha256", "f" * 64
            ),
        )
        result = self._compare(self.first["run_dir"], protocol_clone, "protocol.json")
        self.assertEqual(result["status"], "failed")
        fields = [mismatch["field"] for mismatch in result["result"]["mismatches"]]
        self.assertIn("protocol.sha256", fields)
        environment_clone = _clone_run(
            Path(self.first["run_dir"]),
            self.root / "runs" / "environment-clone",
            provenance=lambda document: document["environment"].__setitem__(
                "platform", "different-platform"
            ),
        )
        result = self._compare(
            self.first["run_dir"], environment_clone, "environment.json"
        )
        self.assertEqual(result["status"], "failed")
        fields = [mismatch["field"] for mismatch in result["result"]["mismatches"]]
        self.assertIn("environment.platform", fields)

    def test_destinations_inside_inputs_are_rejected(self):
        inside = Path(self.first["run_dir"]) / "report.json"
        before = inside.read_bytes()
        with self.assertRaises(checks.CheckError):
            self._compare(self.first["run_dir"], self.second["run_dir"], str(inside))
        self.assertEqual(before, inside.read_bytes())
        existing = self.root / "existing.json"
        existing.write_text("{}", encoding="utf-8")
        with self.assertRaises(checks.CheckError):
            self._compare(self.first["run_dir"], self.second["run_dir"], "existing.json")
        self.assertEqual(existing.read_text(encoding="utf-8"), "{}")

    def test_failed_execution_is_reported_without_being_dropped(self):
        def broken_publish(path, payload):
            raise OSError("disk full during publication")

        failed_root = self.root / "failed-runs"
        with self.assertRaises(OSError):
            fx.fit_run(
                failed_root,
                run_id="failed",
                data=self.data,
                data_path=self.data_path,
                publish=broken_publish,
            )
        directory = failed_root / "failed"
        status = fx.read_json(directory / "status.json")
        self.assertEqual(status["state"], "failed")
        report = fx.read_json(directory / "report.json")
        self.assertEqual(report["status"], "failed")
        result = self._compare(directory, Path(self.first["run_dir"]), "failed.json")
        self.assertEqual(result["status"], "failed")
        self.assertTrue((self.root / "failed.json").is_file())


class RecomputeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.keys = fx.r0_keys(5)
        self.data_path = fx.write_demand(
            self.root / "data" / "r0.parquet", "r0", self.keys,
            fx.synthetic_signal(5, seed=8),
        )
        self.data = fx.load_data("r0", self.data_path)
        self.winner = fx.fit_run(
            self.root / "runs", run_id="winner", data=self.data,
            data_path=self.data_path, epochs=2,
        )
        self.block = self.root / "blocks" / "block"
        fx.write_json(
            self.block / "selection.json",
            fx.selection_document(
                self.root, winner_run_dir=Path(self.winner["run_dir"])
            ),
        )
        self.report = runner.run_report(
            {
                "block_dir": str(self.block),
                "run_dir": self.winner["run_dir"],
                "run_id": "report",
                "purpose": "development",
                "output_root": str(self.root / "reports"),
                "data_name": "r0",
                "data_path": str(self.data_path),
                "argv": ["test"],
            },
            data=self.data,
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_report_metrics_recompute_from_saved_arrays_only(self):
        result = checks.run_recompute(
            run_dir=Path(self.report["run_dir"]),
            report_path=self.root / "recompute.json",
            argv=["test"],
        )
        self.assertEqual(result["status"], "pass", result["result"]["comparison"])
        report = fx.read_json(self.root / "recompute.json")
        self.assertEqual(report["result"]["test"]["shape"], [4, 5, 3])
        self.assertEqual(report["result"]["test"]["elements"], 60)
        self.assertIn("neighbor_groups", report["result"]["test"])
        self.assertEqual(report["tolerances"]["diagnostic_relative"], 1e-12)

    def test_compare_after_reporting_also_bounds_test_predictions(self):
        second = fx.fit_run(
            self.root / "runs",
            run_id="winner-b",
            data=self.data,
            data_path=self.data_path,
            epochs=2,
            repeat_role="b",
        )
        second_block = self.root / "blocks" / "block-b"
        fx.write_json(
            second_block / "selection.json",
            fx.selection_document(
                self.root,
                block_id="block-b",
                winner_run_dir=Path(second["run_dir"]),
            ),
        )
        second_report = runner.run_report(
            {
                "block_dir": str(second_block),
                "run_dir": second["run_dir"],
                "run_id": "report-b",
                "purpose": "development",
                "output_root": str(self.root / "reports"),
                "data_name": "r0",
                "data_path": str(self.data_path),
                "argv": ["test"],
            },
            data=self.data,
        )
        result = checks.run_compare(
            run_a=Path(self.report["run_dir"]),
            run_b=Path(second_report["run_dir"]),
            report_path=self.root / "compare-reports.json",
            argv=["test"],
        )
        self.assertEqual(result["status"], "pass")
        labels = [row["label"] for row in result["result"]["comparisons"]]
        self.assertEqual(labels, ["validation", "test"])
        test_row = result["result"]["comparisons"][1]
        self.assertEqual(test_row["normalized_MAE_difference"], 0.0)
        self.assertEqual(test_row["max_absolute_prediction_difference"], 0.0)

    def test_recompute_needs_no_torch_pandas_or_source_data(self):
        with mock.patch.dict(
            sys.modules, {"torch": None, "pandas": None, "pyarrow": None}
        ):
            result = checks.run_recompute(
                run_dir=Path(self.report["run_dir"]),
                report_path=self.root / "recompute-blind.json",
                argv=["test"],
            )
        self.assertEqual(result["status"], "pass")
        with mock.patch(
            "pandas.read_parquet", side_effect=AssertionError("source data read")
        ):
            result = checks.run_recompute(
                run_dir=Path(self.winner["run_dir"]),
                report_path=self.root / "recompute-fit.json",
                argv=["test"],
            )
        self.assertEqual(result["status"], "pass")

    def test_tampered_saved_metric_fails_recompute(self):
        report_path = Path(self.report["run_dir"]) / "report.json"
        payload = fx.read_json(report_path)
        payload["metrics"]["MAE"] = payload["metrics"]["MAE"] + 1.0
        fx.write_json(report_path, payload)
        result = checks.run_recompute(
            run_dir=Path(self.report["run_dir"]),
            report_path=self.root / "tampered.json",
            argv=["test"],
        )
        self.assertEqual(result["status"], "fail")
        report = fx.read_json(self.root / "tampered.json")
        paths = [difference["path"] for difference in report["result"]["comparison"]["differences"]]
        self.assertIn("MAE", paths)

    def test_recompute_destination_cannot_replace_inputs(self):
        destination = Path(self.report["run_dir"]) / "report.json"
        before = destination.read_bytes()
        with self.assertRaises(checks.CheckError):
            checks.run_recompute(
                run_dir=Path(self.report["run_dir"]),
                report_path=destination,
                argv=["test"],
            )
        self.assertEqual(before, destination.read_bytes())


if __name__ == "__main__":
    unittest.main()
