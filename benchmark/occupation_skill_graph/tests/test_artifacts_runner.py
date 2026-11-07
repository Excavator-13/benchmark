"""Exclusive build artifacts, terminal states and completed-stage evidence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from benchmark.occupation_skill_graph import artifacts, checks, layout, protocol, runner
from benchmark.occupation_skill_graph.tests import fixtures as fx


class BuildArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.fixture = fx.standard_fixture(self.root / "data")
        self.output = self.root / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _spec(self, run_id: str = "run-1", **overrides):
        return fx.build_spec(
            self.root,
            fixture=self.fixture,
            run_id=run_id,
            output_root=self.output,
            **overrides,
        )

    def test_success_writes_self_contained_artifacts(self) -> None:
        result = runner.execute_build(self._spec())
        self.assertEqual(result["status"], "succeeded")
        run_dir = self.output / "run-1"
        report = json.loads((run_dir / "report.json").read_text())
        self.assertEqual(report["status"], "succeeded")
        self.assertTrue(report["graph_bytes_unchanged_by_diagnostics"])
        self.assertFalse(report["research_acceptance_performed"])
        self.assertFalse(report["graph_frozen"])
        self.assertFalse(report["predictive_benefit_claimed"])
        self.assertTrue((run_dir / "summary.md").is_file())
        self.assertTrue((run_dir / "protocol.md").is_file())
        self.assertTrue((run_dir / "command.json").is_file())
        self.assertTrue((run_dir / "provenance.json").is_file())
        self.assertTrue((run_dir / "artifacts-sha256.json").is_file())
        status = json.loads((run_dir / "artifacts/status.json").read_text())
        self.assertEqual(status["state"], "succeeded")
        # Every numeric payload reloads with pickles disabled.
        for relative in layout.required_payload_files():
            path = run_dir / relative
            self.assertTrue(path.is_file(), relative)
            if relative.endswith(".npy"):
                np.load(path, allow_pickle=False)
        manifest = json.loads((run_dir / "artifacts-sha256.json").read_text())
        problems = artifacts.verify_manifest(
            run_dir, manifest, required=layout.required_payload_files()
        )
        self.assertEqual(problems, [])
        protocol_hash = artifacts.sha256_file(run_dir / "protocol.md")
        self.assertEqual(report["protocol"]["sha256"], protocol_hash)

    def test_refuses_to_overwrite_existing_run(self) -> None:
        runner.execute_build(self._spec())
        with self.assertRaises(artifacts.RunExistsError):
            runner.execute_build(self._spec())

    def test_failure_after_source_retains_completed_stage(self) -> None:
        spec = self._spec(run_id="failed-source", fail_after_stage="source")
        with self.assertRaises(runner.InjectedFailure):
            runner.execute_build(spec)
        run_dir = self.output / "failed-source"
        status = json.loads((run_dir / "artifacts/status.json").read_text())
        self.assertEqual(status["state"], "failed")
        self.assertEqual(status["completed_stages"], ["source"])
        self.assertTrue((run_dir / "artifacts/observations.npy").is_file())
        self.assertFalse((run_dir / "artifacts/candidates/jaccard/edge_index.npy").is_file())
        self.assertFalse((run_dir / "report.json").exists())

    def test_failure_after_construct_retains_candidate_stage(self) -> None:
        spec = self._spec(run_id="failed-construct", fail_after_stage="construct")
        with self.assertRaises(runner.InjectedFailure):
            runner.execute_build(spec)
        run_dir = self.output / "failed-construct"
        status = json.loads((run_dir / "artifacts/status.json").read_text())
        self.assertEqual(status["completed_stages"], ["source", "construct"])
        self.assertTrue((run_dir / "artifacts/candidates/jaccard/edge_index.npy").is_file())
        self.assertTrue((run_dir / "artifacts/candidate-overlap.json").is_file())
        self.assertFalse((run_dir / "report.json").exists())

    def test_saved_check_rederives_science_without_sources(self) -> None:
        runner.execute_build(self._spec())
        run_dir = self.output / "run-1"
        report_path = self.root / "check.json"
        # Remove every fixture source; the checker must not reopen it.
        for path in self.fixture["target_paths"].values():
            path.unlink()
        self.fixture["source_path"].unlink()
        result = checks.check_artifact(
            run_dir,
            report_path,
            repo_root=self.root,
            command=["fixture-check"],
        )
        self.assertEqual(result["status"], "ok")
        payload = json.loads(report_path.read_text())
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["tolerances"]["numeric_rtol"], 1e-12)
        self.assertFalse(payload["tolerances"]["source_data_reopened"])
        self.assertFalse(payload["tolerances"]["input_modified"])

    def test_check_rejects_input_inside_report_path(self) -> None:
        runner.execute_build(self._spec())
        with self.assertRaises(Exception):
            checks.check_artifact(
                self.output / "run-1",
                self.output / "run-1" / "check.json",
                repo_root=self.root,
                command=["fixture-check"],
            )
        self.assertFalse((self.output / "run-1" / "check.json").exists())


if __name__ == "__main__":
    unittest.main()
