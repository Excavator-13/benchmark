"""Saved-only checker rejection of corrupt, contradictory and incomplete evidence."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from benchmark.occupation_skill_graph import artifacts, checks, runner
from benchmark.occupation_skill_graph.tests import fixtures as fx


class SavedCheckCorruptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.fixture = fx.standard_fixture(cls.root / "data")
        cls.spec = fx.build_spec(
            cls.root,
            fixture=cls.fixture,
            run_id="golden",
            output_root=cls.root / "output",
        )
        runner.execute_build(cls.spec)
        cls.golden = cls.root / "output" / "golden"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        self.case = Path(tempfile.mkdtemp(dir=self.root))
        self.run_dir = self.case / "run"
        shutil.copytree(self.golden, self.run_dir)
        self.report_path = self.case / "check.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.case, ignore_errors=True)

    def _check(self):
        return checks.check_artifact(
            self.run_dir,
            self.report_path,
            repo_root=self.root,
            command=["fixture-check"],
        )

    def _rehash(self, relative: str) -> None:
        manifest_path = self.run_dir / "artifacts-sha256.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][relative] = artifacts.sha256_file(self.run_dir / relative)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    def _rewrite_array(self, relative: str, array: np.ndarray) -> None:
        np.save(self.run_dir / relative, array)
        self._rehash(relative)

    def test_golden_artifact_passes(self) -> None:
        result = self._check()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["report"]["errors"]), 0)

    def test_missing_payload_is_rejected(self) -> None:
        (self.run_dir / "artifacts/candidates/jaccard/edge_score.npy").unlink()
        result = self._check()
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["report"]["errors"])

    def test_corrupt_score_checksum_is_rejected(self) -> None:
        path = self.run_dir / "artifacts/candidates/jaccard/edge_score.npy"
        array = np.load(path)
        array[0] = array[0] + 1.0
        np.save(path, array)
        result = self._check()
        self.assertEqual(result["status"], "failed")
        self.assertIn("checksum", json.dumps(result["report"]["errors"]))

    def test_one_e_minus_thirteen_score_difference_passes(self) -> None:
        relative = "artifacts/candidates/jaccard/edge_score.npy"
        array = np.load(self.run_dir / relative)
        array[0] = array[0] + 1e-13
        self._rewrite_array(relative, array)
        result = self._check()
        self.assertEqual(result["status"], "ok")

    def test_one_e_minus_nine_score_difference_fails(self) -> None:
        relative = "artifacts/candidates/jaccard/edge_score.npy"
        array = np.load(self.run_dir / relative)
        array[0] = array[0] + 1e-9
        self._rewrite_array(relative, array)
        result = self._check()
        self.assertEqual(result["status"], "failed")


    def test_corrupt_degree_count_fails(self) -> None:
        relative = "artifacts/candidates/jaccard/degree.npy"
        degree = np.load(self.run_dir / relative)
        degree[0] = degree[0] + 1
        self._rewrite_array(relative, degree)
        result = self._check()
        self.assertEqual(result["status"], "failed")

    def test_contradictory_report_count_fails(self) -> None:
        relative = "report.json"
        report = json.loads((self.run_dir / relative).read_text())
        report["candidates"]["jaccard"]["post_sparsification"]["edges"] += 1
        (self.run_dir / relative).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n"
        )
        self._rehash(relative)
        result = self._check()
        self.assertEqual(result["status"], "failed")

    def test_corrupt_key_identity_fails(self) -> None:
        relative = "artifacts/skills.npy"
        skills = np.load(self.run_dir / relative)
        skills = skills[::-1].copy()
        self._rewrite_array(relative, skills)
        result = self._check()
        self.assertEqual(result["status"], "failed")

    def test_incomplete_status_fails(self) -> None:
        status_path = self.run_dir / "artifacts/status.json"
        status = json.loads(status_path.read_text())
        status["state"] = "failed"
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
        result = self._check()
        self.assertEqual(result["status"], "failed")
        self.assertIn("not 'succeeded'", json.dumps(result["report"]["errors"]))

    def test_missing_report_is_incomplete(self) -> None:
        (self.run_dir / "report.json").unlink()
        result = self._check()
        self.assertEqual(result["status"], "failed")

    def test_existing_report_is_not_overwritten(self) -> None:
        self.report_path.write_text("existing\n")
        with self.assertRaises(Exception):
            self._check()
        self.assertEqual(self.report_path.read_text(), "existing\n")

    def test_checker_does_not_modify_input_bytes(self) -> None:
        before = {
            path.relative_to(self.run_dir).as_posix(): artifacts.sha256_file(path)
            for path in sorted(self.run_dir.rglob("*"))
            if path.is_file()
        }
        result = self._check()
        self.assertEqual(result["status"], "ok")
        after = {
            path.relative_to(self.run_dir).as_posix(): artifacts.sha256_file(path)
            for path in sorted(self.run_dir.rglob("*"))
            if path.is_file()
        }
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
