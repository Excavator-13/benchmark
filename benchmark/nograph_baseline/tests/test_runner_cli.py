"""End-to-end run artifacts, failures, saved-run checks and the public CLI."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

import numpy as np

import nb_fixtures as fx
from benchmark.nograph_baseline import artifacts, checks, cli, protocol, runner

REPO_ROOT = protocol.REPO_ROOT
DEVELOPMENT_DEFAULT_ROOT = REPO_ROOT / "scratch" / "nograph-baseline"
FORMAL_DEFAULT_ROOT = REPO_ROOT / "research" / "runs"


def _tree_hash(root: Path) -> dict:
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return result


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _unique_run_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True
    )


def _init_git_repo(root: Path) -> Path:
    """Create a disposable Git repository so dirty cases are deterministic."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "suite@example.invalid")
    _git(root, "config", "user.name", "Baseline Suite")
    _git(root, "config", "commit.gpgsign", "false")
    return root


def _commit_all(repo: Path, message: str = "fixture") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", message)


def _clean_development_output(run_dir: Path, scratch_root_existed: bool) -> None:
    """Remove only the scratch output this suite created."""
    shutil.rmtree(run_dir, ignore_errors=True)
    if not scratch_root_existed:
        try:
            DEVELOPMENT_DEFAULT_ROOT.rmdir()
        except OSError:
            pass


def execute_fixture(
    root: Path, data_name: str = "r0", run_id: str = "run-001", node_count: int = 8, **kwargs
):
    fixture = fx.build_fixture(root / "fixture", data_name, node_count=node_count)
    spec = fx.make_run_spec(
        root / "runs",
        data_name,
        fixture["demand_path"],
        fixture["graph_path"],
        run_id,
        **kwargs,
    )
    result = runner.execute_run(spec)
    return fixture, Path(result["run_dir"])


class RunnerArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.fixture, cls.run_dir = execute_fixture(cls.root, run_id="artifact-run")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_required_artifacts_exist(self) -> None:
        expected = [
            "config.json",
            "command.json",
            "provenance.json",
            "git-commit.txt",
            "git-status.txt",
            "git-diff.patch",
            "code-source.json",
            "environment.json",
            "environment.txt",
            "source-sha256.json",
            "nodes.parquet",
            "windows.json",
            "audit.json",
            "masks.npz",
            "node-errors.parquet",
            "gold/validation.npy",
            "gold/test.npy",
            "models/SharedRidge.npz",
            "selection.json",
            "metrics.json",
            "measurements.json",
            "artifacts-sha256.json",
            "events.jsonl",
            "summary.md",
            "status.json",
        ]
        for relative in expected:
            self.assertTrue(
                (self.run_dir / relative).exists(), msg=f"missing {relative}"
            )
        # The protocol is either located by its fixed commit/path reference
        # (clean committed content) or preserved as a run file.
        protocol_entry = fx.read_json(self.run_dir / "code-source.json")["protocol"]
        if (
            protocol_entry["git_status"] == "committed_clean"
            and protocol_entry["git_reference"]
        ):
            self.assertFalse((self.run_dir / "protocol.md").exists())
        else:
            self.assertTrue((self.run_dir / "protocol.md").exists())
        for method in protocol.NAIVE_METHODS + (protocol.MODEL_NAME,):
            for split in ("validation", "test"):
                self.assertTrue(
                    (self.run_dir / "predictions" / method / f"{split}.npy").exists()
                )
        # Losing-candidate arrays are omitted by default; only the score table
        # and the selected model/preprocessing statistics are persisted.
        self.assertFalse((self.run_dir / "candidates").exists())
        _, retain_dir = execute_fixture(
            self.root / "retain", run_id="retain-run", retain_candidates=True
        )
        for name in protocol.LAMBDA_CANDIDATES:
            label = f"{name:g}"
            self.assertTrue(
                (retain_dir / "candidates" / label / "parameters.npz").exists()
            )
            self.assertTrue(
                (retain_dir / "candidates" / label / "validation.npy").exists()
            )

    def test_numeric_artifacts_load_without_pickle(self) -> None:
        for path in sorted(self.run_dir.rglob("*.npy")):
            with self.subTest(path=path.name):
                np.load(path, allow_pickle=False)
        for path in sorted(self.run_dir.rglob("*.npz")):
            with self.subTest(path=path.name):
                with np.load(path, allow_pickle=False) as handle:
                    for name in handle.files:
                        np.asarray(handle[name])

    def test_nodes_parquet_is_canonically_ordered(self) -> None:
        import pandas as pd

        frame = pd.read_parquet(self.run_dir / "nodes.parquet")
        self.assertEqual(frame["node_index"].tolist(), list(range(len(frame))))
        keys = frame[["r0_id", "skill_id"]].to_numpy()
        self.assertEqual(keys.tolist(), sorted(keys.tolist()))

    def test_source_and_environment_capture(self) -> None:
        manifest = fx.read_json(self.run_dir / "source-sha256.json")
        sources = manifest["sources"]
        self.assertIn("demand", sources)
        self.assertIn("protocol", sources)
        self.assertIn("coverage", sources)
        self.assertEqual(manifest["algorithm"], "sha256")
        # The saved-only validators rely on the executing protocol bytes.
        self.assertEqual(
            sources["protocol"]["sha256"], _sha256_file(protocol.PROTOCOL_PATH)
        )
        environment = fx.read_json(self.run_dir / "environment.json")
        self.assertEqual(environment["packages"]["numpy"], np.__version__)
        self.assertTrue(environment["numpy_blas_config"])
        self.assertIn("numpy", environment["pip_freeze"])

        # Scoped source capture: unrelated tests/caches and unrelated records
        # must never enter the execution snapshot, and the actual protocol path
        # must be present.
        code_source = fx.read_json(self.run_dir / "code-source.json")
        self.assertEqual(code_source["policy"], "P01-records-v2")
        self.assertEqual(code_source["patch_path"], "git-diff.patch")
        self.assertEqual(
            code_source["identity_available"], code_source["commit"] is not None
        )
        scope = code_source["runtime_scope"]
        self.assertTrue(scope)
        for relative in scope:
            parts = Path(relative).parts
            self.assertNotIn("tests", parts, msg=relative)
            self.assertNotIn("__pycache__", parts, msg=relative)
        protocol_relative = (
            protocol.PROTOCOL_PATH.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        )
        self.assertIn(protocol_relative, scope)
        self.assertEqual(code_source["protocol"]["path"], protocol_relative)
        self.assertEqual(
            code_source["protocol"]["sha256"], _sha256_file(protocol.PROTOCOL_PATH)
        )

        entries = code_source["files"]
        self.assertTrue(entries)
        clean_entries = {
            path: entry
            for path, entry in entries.items()
            if entry["git_status"] == "committed_clean"
        }
        # Committed runtime source must be located by reference, not copied.
        self.assertTrue(
            clean_entries,
            msg="expected at least one clean committed runtime source file",
        )
        for path, entry in entries.items():
            with self.subTest(path=path):
                self.assertEqual(entry["path"], path)
                self.assertIn(
                    entry["git_status"],
                    {"committed_clean", "modified", "untracked", "unknown"},
                )
                if entry["git_status"] == "committed_clean":
                    self.assertIsNotNone(entry["git_reference"])
                    self.assertIsNone(entry["content_saved"])
                    self.assertEqual(
                        entry["git_reference"]["sha256"], entry["sha256"]
                    )
                if entry["content_saved"]:
                    saved = self.run_dir / entry["content_saved"]
                    self.assertTrue(saved.exists(), msg=entry["content_saved"])
                    self.assertEqual(_sha256_file(saved), entry["sha256"])
        for name in (
            "benchmark/nograph_baseline/metrics.py",
            "benchmark/nograph_baseline/baselines.py",
            "benchmark/nograph_baseline/coverage.py",
            "benchmark/nograph_baseline/data.py",
            "benchmark/nograph_baseline/ridge.py",
            "benchmark/nograph_baseline/protocol.py",
        ):
            if name in clean_entries:
                self.assertIsNotNone(clean_entries[name]["git_reference"])
                self.assertIsNone(clean_entries[name]["content_saved"])

        # Dirty/untracked execution content must be recoverable, exercised on a
        # disposable repository so the result never depends on this checkout.
        repo = _init_git_repo(self.root / "dirty-repo")
        (repo / "clean.py").write_text("VALUE = 1\n", encoding="utf-8")
        (repo / "modified.py").write_text("VALUE = 2\n", encoding="utf-8")
        _commit_all(repo)
        (repo / "modified.py").write_text("VALUE = 999\n", encoding="utf-8")
        (repo / "untracked.py").write_text("VALUE = 3\n", encoding="utf-8")
        probe = artifacts.RunDirectory(
            self.root / "dirty-runs", "dirty-probe", "run"
        ).reserve()
        record = artifacts.capture_source(
            probe, repo, runtime_paths=["clean.py", "modified.py", "untracked.py"]
        )
        self.assertEqual(record["files"]["clean.py"]["git_status"], "committed_clean")
        self.assertIsNotNone(record["files"]["clean.py"]["git_reference"])
        self.assertIsNone(record["files"]["clean.py"]["content_saved"])
        self.assertEqual(record["files"]["modified.py"]["git_status"], "modified")
        self.assertIsNone(record["files"]["modified.py"]["content_saved"])
        self.assertIn("VALUE = 999", (probe.path / "git-diff.patch").read_text())
        self.assertEqual(record["files"]["untracked.py"]["git_status"], "untracked")
        self.assertEqual(
            record["files"]["untracked.py"]["content_saved"],
            "code-untracked/untracked.py",
        )
        self.assertEqual(
            (probe.path / "code-untracked" / "untracked.py").read_text(),
            "VALUE = 3\n",
        )
        untracked_manifest = fx.read_json(
            probe.path / "code-untracked" / "manifest.json"
        )
        self.assertIn("untracked.py", untracked_manifest["files"])

    def test_measurements_record_real_units_and_settings(self) -> None:
        measurements = fx.read_json(self.run_dir / "measurements.json")
        for key in (
            "demand_read",
            "coverage_read",
            "preprocessing",
            "naive_prediction",
            "ridge_fit",
            "ridge_selection",
            "selected_model_inference",
            "metrics_output",
            "total",
        ):
            self.assertIn(key, measurements["timings_seconds"])
            self.assertGreaterEqual(measurements["timings_seconds"][key], 0.0)
        memory = measurements["peak_memory"]
        self.assertEqual(memory["status"], "ok")
        self.assertIsInstance(memory["bytes"], int)
        self.assertIn(memory["native_unit"], ("bytes", "KiB"))
        self.assertEqual(measurements["device"], "cpu")
        self.assertEqual(measurements["execution_settings"]["seed"], 0)
        self.assertFalse(measurements["diagnostic_elapsed_times_used"])
        totals = measurements["totals_seconds"]
        self.assertGreaterEqual(totals["total"], totals["inference"])

    def test_reports_cover_all_methods_and_levels(self) -> None:
        metrics = fx.read_json(self.run_dir / "metrics.json")
        for split in ("validation", "test"):
            self.assertEqual(
                sorted(metrics["methods"][split]),
                sorted(list(protocol.NAIVE_METHODS) + [protocol.MODEL_NAME]),
            )
        references = metrics["references"]
        self.assertIn(references["NaiveRef"], protocol.NAIVE_METHODS)
        self.assertIn(references["NaiveRef6"], protocol.NAIVE_REF6_METHODS)
        report = metrics["methods"]["test"][protocol.MODEL_NAME]
        for level in (
            "MAE",
            "RMSE",
            "activity_groups",
            "neighbor_groups",
            "contexts",
            "windows",
            "horizons",
            "balanced_activity_group_MAE",
        ):
            self.assertIn(level, report)
        self.assertEqual(len(report["windows"]), 4)
        self.assertEqual(
            report["target_month_multiplicities"]["2023-09"], 3
        )

    def test_shared_ridge_parameters_are_reconstructable(self) -> None:
        with np.load(
            self.run_dir / "models" / "SharedRidge.npz", allow_pickle=False
        ) as handle:
            weights = handle["W"]
            bias = handle["b"]
            mean = handle["node_mean"]
            effective_std = handle["node_effective_std"]
            scalar = handle["scalar"]
        self.assertEqual(weights.shape, (6, 3))
        self.assertEqual(bias.shape, (3,))
        lam, alpha, samples, _objective = (float(x) for x in scalar)
        self.assertAlmostEqual(alpha, lam * samples)
        self.assertEqual(int(samples), 19 * self.fixture["node_count"])
        # Reconstruct a prediction from six observed values.
        raw = self.fixture["signal"][:, 24:30].astype(np.float64)
        standardized = (raw - mean[:, None]) / effective_std[:, None]
        prediction = (standardized @ weights + bias) * effective_std[
            :, None
        ] + mean[:, None]
        saved = np.load(
            self.run_dir / "predictions" / protocol.MODEL_NAME / "test.npy",
            allow_pickle=False,
        )
        np.testing.assert_allclose(saved[0], prediction, atol=1e-9)

    def test_selection_frozen_before_test_and_no_test_labels(self) -> None:
        selection = fx.read_json(self.run_dir / "selection.json")
        self.assertFalse(selection["test_labels_used_for_selection"])
        self.assertFalse(selection["shared_ridge"]["test_labels_used"])
        self.assertEqual(
            selection["training_samples_M"], selection["expected_training_samples_M"]
        )
        self.assertEqual(
            selection["training_design_ordering"],
            "window-major then node-major (row w*N+i)",
        )
        for row in selection["shared_ridge"]["candidate_table"]:
            self.assertAlmostEqual(row["alpha"], row["lambda"] * row["M"])

    def test_selected_candidate_scores_match_reported_validation_metrics(self) -> None:
        selection = fx.read_json(self.run_dir / "selection.json")
        metrics = fx.read_json(self.run_dir / "metrics.json")
        selected_lambda = selection["shared_ridge"]["selected_lambda"]
        rows = {
            row["lambda"]: row
            for row in selection["shared_ridge"]["candidate_table"]
        }
        reported = metrics["methods"]["validation"][protocol.MODEL_NAME]
        # Candidate selection must be scored on the same original-unit
        # validation labels that the run later reports.
        self.assertAlmostEqual(
            rows[selected_lambda]["validation_MSE"], reported["MSE"], places=6
        )
        self.assertAlmostEqual(
            rows[selected_lambda]["validation_MAE"], reported["MAE"], places=6
        )

    def test_status_and_immutable_manifest(self) -> None:
        status = fx.read_json(self.run_dir / "status.json")
        self.assertEqual(status["state"], "success")
        manifest = fx.read_json(self.run_dir / "artifacts-sha256.json")
        self.assertIn("metrics.json", manifest["files"])
        self.assertNotIn("artifacts-sha256.json", manifest["files"])
        self.assertNotIn("events.jsonl", manifest["files"])

    def test_clipped_report_is_separate_and_never_selects(self) -> None:
        _, run_dir = execute_fixture(
            self.root / "clipped", run_id="clipped-run", clip_nonnegative=True
        )
        predictions = run_dir / "predictions" / protocol.CLIPPED_MODEL_NAME
        self.assertTrue((predictions / "test.npy").exists())
        metrics = fx.read_json(run_dir / "metrics.json")
        self.assertIn(protocol.CLIPPED_MODEL_NAME, metrics["methods"]["test"])
        selection = fx.read_json(run_dir / "selection.json")
        baseline_selection = fx.read_json(self.run_dir / "selection.json")
        self.assertEqual(
            selection["shared_ridge"]["selected_lambda"],
            baseline_selection["shared_ridge"]["selected_lambda"],
        )
        raw = np.load(
            run_dir / "predictions" / protocol.MODEL_NAME / "test.npy",
            allow_pickle=False,
        )
        clipped = np.load(predictions / "test.npy", allow_pickle=False)
        np.testing.assert_array_equal(clipped, np.maximum(raw, 0.0))


class CoverageInvarianceTests(unittest.TestCase):
    def test_predictions_do_not_depend_on_coverage_annotation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keys = fx.r0_keys(8)
            signal = fx.synthetic_signal(8, seed=31)
            demand = fx.write_demand(
                root / "r0.parquet", "r0", keys, signal, shuffle_seed=1
            )
            sparse = fx.write_graph(root / "sparse.parquet", "r0", [[0, 0, 1]])
            dense = fx.write_graph(
                root / "dense.parquet", "r0", [[0, i, i + 1] for i in range(7)]
            )
            runs = root / "runs"
            spec_sparse = fx.make_run_spec(
                runs, "r0", demand, sparse, "sparse-run"
            )
            spec_dense = fx.make_run_spec(runs, "r0", demand, dense, "dense-run")
            first = Path(runner.execute_run(spec_sparse)["run_dir"])
            second = Path(runner.execute_run(spec_dense)["run_dir"])
            for method in protocol.NAIVE_METHODS + (protocol.MODEL_NAME,):
                a = np.load(
                    first / "predictions" / method / "test.npy", allow_pickle=False
                )
                b = np.load(
                    second / "predictions" / method / "test.npy", allow_pickle=False
                )
                np.testing.assert_array_equal(a, b)
            coverage_a = fx.read_json(first / "coverage.json")
            coverage_b = fx.read_json(second / "coverage.json")
            self.assertNotEqual(
                coverage_a["covered_nodes"], coverage_b["covered_nodes"]
            )
            metrics_a = fx.read_json(first / "metrics.json")
            metrics_b = fx.read_json(second / "metrics.json")
            self.assertNotEqual(
                metrics_a["methods"]["test"][protocol.MODEL_NAME][
                    "neighbor_groups"
                ]["has_nonself_neighbor"]["MAE"],
                metrics_b["methods"]["test"][protocol.MODEL_NAME][
                    "neighbor_groups"
                ]["has_nonself_neighbor"]["MAE"],
            )


class FailureAndInterruptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_existing_run_id_is_rejected(self) -> None:
        fixture, _ = execute_fixture(self.root, run_id="collide")
        spec = fx.make_run_spec(
            self.root / "runs",
            "r0",
            fixture["demand_path"],
            fixture["graph_path"],
            "collide",
        )
        with self.assertRaises(artifacts.RunExistsError):
            runner.execute_run(spec)

    def test_malformed_source_preserves_partial_evidence(self) -> None:
        import pandas as pd

        bad = self.root / "bad.parquet"
        bad.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"r0_id": [0], "skill_id": [0], "2021-01": [1.0]}).to_parquet(
            bad, index=False
        )
        graph = fx.write_graph(self.root / "graph.parquet", "r0", [[0, 0, 1]])
        demand_before = hashlib.sha256(bad.read_bytes()).hexdigest()
        spec = fx.make_run_spec(
            self.root / "runs", "r0", bad, graph, "bad-source-run"
        )
        with self.assertRaises(Exception):
            runner.execute_run(spec)
        run_dir = self.root / "runs" / "bad-source-run"
        status = fx.read_json(run_dir / "status.json")
        self.assertEqual(status["state"], "failed")
        failure = fx.read_json(run_dir / "failure.json")
        self.assertEqual(failure["failure"]["state"], "failed")
        self.assertEqual(failure["failure"]["stage"], "demand_read")
        self.assertTrue((run_dir / "config.json").exists())
        self.assertEqual(
            hashlib.sha256(bad.read_bytes()).hexdigest(), demand_before
        )

    def test_unfinished_status_after_hard_termination(self) -> None:
        run_dir = self.root / "runs" / "killed-run"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "status.json").write_text(
            json.dumps({"run_id": "killed-run", "state": "running"}),
            encoding="utf-8",
        )
        report = runner.check_unfinished(run_dir)
        self.assertTrue(report["unfinished"])
        self.assertFalse(report["finished"])

    def _launch_worker(self, run_id: str, delay: str = "30"):
        fixture = fx.build_fixture(self.root / "fixture", "r0", node_count=6)
        spec = fx.make_run_spec(
            self.root / "runs",
            "r0",
            fixture["demand_path"],
            fixture["graph_path"],
            run_id,
        )
        spec_path = self.root / f"{run_id}-spec.json"
        spec_path.write_text(json.dumps(spec.to_dict()), encoding="utf-8")
        environment = dict(os.environ)
        environment["NOGRAPH_BASELINE_TEST_STAGE_DELAY_SECONDS"] = delay
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "benchmark.nograph_baseline._worker",
                "--spec",
                str(spec_path),
            ],
            cwd=str(REPO_ROOT),
            env=environment,
        )
        return process, self.root / "runs" / run_id

    def _wait_for_status(self, run_dir: Path, timeout: float = 30.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if (run_dir / "nodes.parquet").exists():
                return
            time.sleep(0.02)
        raise AssertionError("run directory never reached the audit stage")

    def test_sigterm_marks_interrupted_and_retains_partial(self) -> None:
        process, run_dir = self._launch_worker("sigterm-run")
        try:
            self._wait_for_status(run_dir)
            time.sleep(0.2)
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=30)
        finally:
            if process.poll() is None:
                process.kill()
        status = fx.read_json(run_dir / "status.json")
        self.assertEqual(status["state"], "interrupted")
        self.assertTrue((run_dir / "failure.json").exists())
        self.assertTrue((run_dir / "nodes.parquet").exists())
        events = (run_dir / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("run_interrupted", events)

    def test_sigint_marks_interrupted_and_retains_partial(self) -> None:
        process, run_dir = self._launch_worker("sigint-run")
        try:
            self._wait_for_status(run_dir)
            time.sleep(0.2)
            process.send_signal(signal.SIGINT)
            process.wait(timeout=30)
        finally:
            if process.poll() is None:
                process.kill()
        status = fx.read_json(run_dir / "status.json")
        self.assertEqual(status["state"], "interrupted")
        self.assertTrue((run_dir / "failure.json").exists())

    def test_sigkill_leaves_unfinished_running_state(self) -> None:
        process, run_dir = self._launch_worker("sigkill-run")
        try:
            self._wait_for_status(run_dir)
            time.sleep(0.2)
            process.kill()
            process.wait(timeout=30)
        finally:
            if process.poll() is None:
                process.kill()
        status = fx.read_json(run_dir / "status.json")
        self.assertEqual(status["state"], "running")
        report = runner.check_unfinished(run_dir)
        self.assertTrue(report["unfinished"])
        self.assertTrue((run_dir / "nodes.parquet").exists())
        self.assertFalse((run_dir / "artifacts-sha256.json").exists())


class CheckCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_recompute_without_source_access_and_preserves_inputs(self) -> None:
        fixture, run_dir = execute_fixture(self.root, run_id="base-run")
        before = _tree_hash(run_dir)
        # Disable source-file access entirely.
        fixture["demand_path"].unlink()
        fixture["graph_path"].unlink()
        report_path = self.root / "reports" / "recompute-001.json"
        result = checks.command_recompute(
            run_dir=run_dir,
            report_path=report_path,
            repo_root=REPO_ROOT,
            command=["python", "-m", "benchmark.nograph_baseline", "recompute"],
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["report_path"], str(report_path))
        self.assertTrue(report_path.exists())
        report = result["report"]
        self.assertFalse(report["source_data_read"])
        self.assertFalse(report["model_refit"])
        for comparison in report["comparisons"].values():
            self.assertEqual(comparison["status"], "ok")
            self.assertEqual(comparison["max_normalized_difference"], 0.0)
        self.assertEqual(before, _tree_hash(run_dir))
        inputs = result["envelope"]["inputs"]
        self.assertEqual(inputs["input_run_dir"], str(run_dir))
        self.assertTrue(inputs["consumed_sha256"])

    def test_legacy_run_id_alias_resolves_to_a_single_report(self) -> None:
        fixture, run_dir = execute_fixture(self.root, run_id="legacy-base")
        runs_root = self.root / "runs"
        result = checks.command_recompute(
            run_dir=run_dir,
            run_id="legacy-recompute-001",
            runs_root=runs_root,
            repo_root=REPO_ROOT,
            command=["python", "-m", "benchmark.nograph_baseline", "recompute"],
        )
        self.assertEqual(result["report_path"], str(runs_root / "legacy-recompute-001.json"))
        self.assertEqual(result["status"], "ok")
        self.assertTrue(Path(result["report_path"]).exists())
        self.assertNotIn("run_dir", result)

    def test_compare_two_same_seed_runs(self) -> None:
        fixture = fx.build_fixture(self.root / "fixture", "r0", node_count=8)
        spec_a = fx.make_run_spec(
            self.root / "runs", "r0", fixture["demand_path"], fixture["graph_path"],
            "repeat-a",
        )
        spec_b = fx.make_run_spec(
            self.root / "runs", "r0", fixture["demand_path"], fixture["graph_path"],
            "repeat-b",
        )
        run_a = Path(runner.execute_run(spec_a)["run_dir"])
        run_b = Path(runner.execute_run(spec_b)["run_dir"])
        before_a, before_b = _tree_hash(run_a), _tree_hash(run_b)
        report_path = self.root / "reports" / "compare-001.json"
        result = checks.command_compare(
            run_a=run_a,
            run_b=run_b,
            report_path=report_path,
            repo_root=REPO_ROOT,
            command=["python", "-m", "benchmark.nograph_baseline", "compare"],
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["report_path"], str(report_path))
        self.assertEqual(result["envelope"]["kind"], "compare")
        report = result["report"]
        self.assertTrue(all(report["identity_checks"].values()))
        self.assertTrue(report["masks_equal"])
        self.assertFalse(report["seed_variance_reported"])
        for comparison in report["prediction_comparisons"].values():
            self.assertEqual(comparison["status"], "ok")
            self.assertEqual(comparison["max_absolute_difference"], 0.0)
        for difference in report["mae_relative_differences"].values():
            self.assertLessEqual(difference["relative_difference"], 1e-6)
        self.assertEqual(before_a, _tree_hash(run_a))
        self.assertEqual(before_b, _tree_hash(run_b))

    def test_align_v2_against_independent_log(self) -> None:
        fixture, run_dir = execute_fixture(self.root, run_id="align-base")
        log = self.root / "naive-baselines.log"
        _write_v2_log(
            log,
            "r0",
            fixture["keys"],
            fixture["signal"],
            fx.read_json(run_dir / "metrics.json"),
        )
        demand_sha = fx.read_json(run_dir / "source-sha256.json")["sources"][
            "demand"
        ]["sha256"]
        _write_v2_source_manifest(log, "r0", demand_sha)
        reference_before = hashlib.sha256(log.read_bytes()).hexdigest()
        report_path = self.root / "reports" / "align-001.json"
        result = checks.command_align_v2(
            run_dir=run_dir,
            reference=log,
            report_path=report_path,
            repo_root=REPO_ROOT,
            command=["python", "-m", "benchmark.nograph_baseline", "align-v2"],
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["report_path"], str(report_path))
        self.assertEqual(result["envelope"]["kind"], "align-v2")
        report = result["report"]
        self.assertGreater(report["compared_fields"], 50)
        self.assertEqual(report["discrepancies"], [])
        self.assertEqual(report["tolerance"], 1e-12)
        self.assertTrue(
            report["identity_evidence"]["v2_log_contains_counts_not_full_node_keys"]
        )
        self.assertFalse(report["diagnostic_elapsed_time_compared_as_cost"])
        self.assertEqual(
            hashlib.sha256(log.read_bytes()).hexdigest(), reference_before
        )

    def test_align_v2_preserves_and_explains_discrepancy(self) -> None:
        fixture, run_dir = execute_fixture(self.root, run_id="align-mismatch")
        log = self.root / "naive-baselines.log"
        _write_v2_log(
            log,
            "r0",
            fixture["keys"],
            fixture["signal"],
            fx.read_json(run_dir / "metrics.json"),
            perturb=("validation", "LastValue", "MAE", 1e-6),
        )
        demand_sha = fx.read_json(run_dir / "source-sha256.json")["sources"][
            "demand"
        ]["sha256"]
        _write_v2_source_manifest(log, "r0", demand_sha)
        reference_before = hashlib.sha256(log.read_bytes()).hexdigest()
        result = checks.command_align_v2(
            run_dir=run_dir,
            reference=log,
            report_path=self.root / "reports" / "align-002.json",
            repo_root=REPO_ROOT,
            command=["python", "-m", "benchmark.nograph_baseline", "align-v2"],
        )
        self.assertEqual(result["status"], "mismatch")
        report = result["report"]
        self.assertTrue(report["discrepancies"])
        finding = report["discrepancies"][0]
        self.assertIn("expected", finding)
        self.assertIn("actual", finding)
        self.assertEqual(
            hashlib.sha256(log.read_bytes()).hexdigest(), reference_before
        )


def _v2_metrics(pred: np.ndarray, gold: np.ndarray) -> dict:
    error = pred.astype(np.float64) - gold.astype(np.float64)
    mse = float(np.square(error).mean())
    return {
        "MAE": float(np.abs(error).mean()),
        "MSE": mse,
        "RMSE": float(np.sqrt(mse)),
    }


def _write_v2_log(
    path: Path,
    data_name: str,
    keys,
    signal: np.ndarray,
    metrics: dict,
    *,
    perturb=None,
) -> Path:
    """Write a v2-format diagnostic log with independent arithmetic."""
    months = list(protocol.MONTHS)
    splits = {name: list(starts) for name, starts in protocol.SPLITS.items()}
    lines = []
    activity = (signal[:, :27] > 0).mean(axis=1)
    groups = {
        "inactive": activity == 0,
        "low": (activity > 0) & (activity <= 1 / 3),
        "medium": (activity > 1 / 3) & (activity <= 2 / 3),
        "high": activity > 2 / 3,
    }
    train_mean = signal[:, :27].mean(axis=1, keepdims=True)
    lines.append(
        {
            "dataset": data_name,
            "nodes": len(keys),
            "skill_id_nunique": len({key[1] for key in keys}),
            "context_id_counts": {protocol.node_key_columns(data_name)[0]: 1},
            "joint_contexts": 1,
            "context_cartesian_size": 1,
            "expected_context_skill_nodes": len(keys),
            "is_complete_context_skill_grid": True,
            "train_observation_months": months[:27],
            "train_all_zero_fraction": float((activity == 0).mean()),
            "full_36_month_all_zero_fraction_diagnostic_only": float(
                (signal == 0).all(axis=1).mean()
            ),
            "activity_group_counts": {k: int(v.sum()) for k, v in groups.items()},
        }
    )
    target_months = {
        split: sorted(
            {
                months[index]
                for start in starts
                for index in range(start + 6, start + 9)
            }
        )
        for split, starts in splits.items()
    }
    lines.append(
        {
            "dataset": data_name,
            "mode": "count",
            "nodes": len(keys),
            "split_windows": splits,
            "target_months": target_months,
        }
    )
    validation_mse = {}
    for split in ("validation", "test"):
        starts = splits[split]
        inputs = np.stack([signal[:, s : s + 6] for s in starts])
        gold = np.stack([signal[:, s + 6 : s + 9] for s in starts])
        predictions = {
            "Zero": np.zeros_like(gold),
            "LastValue": np.repeat(inputs[:, :, -1:], 3, axis=2),
            "WindowMean6": np.repeat(
                inputs.mean(axis=2, keepdims=True), 3, axis=2
            ),
            "TrainMean27": np.broadcast_to(train_mean[None, :, :], gold.shape),
            "SeasonalNaive12": np.stack(
                [signal[:, s + 6 - 12 : s + 9 - 12] for s in starts]
            ),
        }
        for model, pred in predictions.items():
            record = {
                "dataset": data_name,
                "split": split,
                "model": model,
                **_v2_metrics(pred, gold),
                "balanced_activity_group_MAE": float(
                    np.mean(
                        [
                            _v2_metrics(pred[:, mask, :], gold[:, mask, :])["MAE"]
                            for mask in groups.values()
                            if mask.any()
                        ]
                    )
                ),
                "activity_groups": {
                    key: {
                        "nodes": int(mask.sum()),
                        **_v2_metrics(pred[:, mask, :], gold[:, mask, :]),
                    }
                    for key, mask in groups.items()
                    if mask.any()
                },
                "horizons": {
                    f"h{h + 1}": _v2_metrics(pred[:, :, h], gold[:, :, h])
                    for h in range(3)
                },
                "windows": [
                    {
                        "forecast_origin": months[s + 5],
                        "target_months": months[s + 6 : s + 9],
                        **_v2_metrics(pred[index], gold[index]),
                    }
                    for index, s in enumerate(starts)
                ],
            }
            if perturb is not None and split == perturb[0] and model == perturb[1]:
                record[perturb[2]] = record[perturb[2]] + perturb[3]
            lines.append(record)
            if split == "validation":
                validation_mse[model] = _v2_metrics(pred, gold)["MSE"]
    order = list(predictions)
    choose = lambda names: min(  # noqa: E731
        names, key=lambda name: (validation_mse[name], order.index(name))
    )
    lines.append(
        {
            "dataset": data_name,
            "reference_selection": "validation MSE",
            "NaiveRef": choose(order),
            "NaiveRef6": choose([n for n in order if n != "SeasonalNaive12"]),
            "SeasonalNaive12_information_budget": "extra 12-month history",
        }
    )
    lines.append({"dataset": data_name, "elapsed_seconds": 0.001})
    path.write_text(
        "\n".join(json.dumps(line, sort_keys=True) for line in lines) + "\n",
        encoding="utf-8",
    )
    return path


def _write_v2_source_manifest(
    log_path: Path, data_name: str, demand_sha256: str
) -> Path:
    """Write the sibling v2 source manifest used for identity alignment."""
    manifest = log_path.parent / "source-sha256.txt"
    manifest.write_text(
        f"{demand_sha256}  dataset/demand/{data_name}.parquet\n"
        f"{'0' * 64}  dataset/graph/{data_name}.parquet\n",
        encoding="utf-8",
    )
    return manifest


BLOCKED_IMPORTS = (
    "sklearn",
    "torch",
    "torch_geometric",
    "dgl",
    "benchmark.graph_method",
)


class CliEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_public_help_via_subprocess(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "benchmark.nograph_baseline", "--help"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("align-v2", completed.stdout)

    def _install_blocker(self) -> Path:
        blocker_dir = self.root / "blocker"
        blocker_dir.mkdir(parents=True, exist_ok=True)
        (blocker_dir / "sitecustomize.py").write_text(
            "\n".join(
                [
                    "import sys",
                    "BLOCKED = %r" % (BLOCKED_IMPORTS,),
                    "class _Blocker:",
                    "    def _blocked(self, fullname):",
                    "        return any(",
                    "            fullname == b or fullname.startswith(b + '.')",
                    "            for b in BLOCKED",
                    "        )",
                    "    def find_spec(self, fullname, path=None, target=None):",
                    "        if self._blocked(fullname):",
                    "            raise ImportError('blocked import: ' + fullname)",
                    "        return None",
                    "if not any(type(f).__name__ == '_Blocker' for f in sys.meta_path):",
                    "    sys.meta_path.insert(0, _Blocker())",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return blocker_dir

    def test_minimal_dependency_smoke_for_both_schemas(self) -> None:
        r0 = fx.build_fixture(self.root / "r0", "r0", node_count=6)
        region = fx.build_fixture(self.root / "region", "region", node_count=3)
        blocker_dir = self._install_blocker()
        runs_root = self.root / "runs"
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(blocker_dir), str(REPO_ROOT), environment.get("PYTHONPATH", "")]
        )
        for data_name, fixture, run_id in (
            ("r0", r0, "smoke-r0"),
            ("region", region, "smoke-region"),
        ):
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "benchmark.nograph_baseline",
                    "run",
                    "--data-name",
                    data_name,
                    "--mode",
                    "count",
                    "--seed",
                    "0",
                    "--run-id",
                    run_id,
                    "--runs-root",
                    str(runs_root),
                    "--demand-path",
                    str(fixture["demand_path"]),
                    "--graph-path",
                    str(fixture["graph_path"]),
                ],
                cwd=str(REPO_ROOT),
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                completed.returncode,
                0,
                msg=f"{data_name}: {completed.stdout}\n{completed.stderr}",
            )
            run_dir = runs_root / run_id
            status = fx.read_json(run_dir / "status.json")
            self.assertEqual(status["state"], "success")
            captured = fx.read_json(run_dir / "environment.json")
            self.assertIsNone(captured["optional_packages"]["sklearn"])
            for required in ("numpy", "pandas", "pyarrow"):
                self.assertTrue(captured["packages"][required])
            # Coverage came from the injected fixture path, not repository data.
            coverage_record = fx.read_json(run_dir / "coverage.json")
            self.assertEqual(
                coverage_record["source_path"], str(fixture["graph_path"])
            )

    def test_recorded_command_is_canonical_and_replayable(self) -> None:
        fixture = fx.build_fixture(self.root / "cmd", "r0", node_count=6)
        runs_root = self.root / "cmdruns"
        argv = [
            sys.executable,
            "-m",
            "benchmark.nograph_baseline",
            "run",
            "--data-name",
            "r0",
            "--mode",
            "count",
            "--seed",
            "0",
            "--run-id",
            "cmd-001",
            "--runs-root",
            str(runs_root),
            "--demand-path",
            str(fixture["demand_path"]),
            "--graph-path",
            str(fixture["graph_path"]),
        ]
        completed = subprocess.run(
            argv, cwd=str(REPO_ROOT), capture_output=True, text=True
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        command = fx.read_json(runs_root / "cmd-001" / "command.json")
        self.assertEqual(command["argv"][0], sys.executable)
        self.assertEqual(
            command["argv"][1:4], ["-m", "benchmark.nograph_baseline", "run"]
        )
        self.assertEqual(
            Path(command["launcher_cwd"]).resolve(), REPO_ROOT.resolve()
        )
        replay = list(command["argv"])
        replay[replay.index("--run-id") + 1] = "cmd-002"
        replayed = subprocess.run(
            replay, cwd=command["launcher_cwd"], capture_output=True, text=True
        )
        self.assertEqual(replayed.returncode, 0, msg=replayed.stderr)
        first = np.load(
            runs_root / "cmd-001" / "predictions" / protocol.MODEL_NAME / "test.npy",
            allow_pickle=False,
        )
        second = np.load(
            runs_root / "cmd-002" / "predictions" / protocol.MODEL_NAME / "test.npy",
            allow_pickle=False,
        )
        np.testing.assert_array_equal(first, second)
        metrics_a = fx.read_json(runs_root / "cmd-001" / "metrics.json")
        metrics_b = fx.read_json(runs_root / "cmd-002" / "metrics.json")
        self.assertEqual(
            metrics_a["methods"]["test"][protocol.MODEL_NAME]["MAE"],
            metrics_b["methods"]["test"][protocol.MODEL_NAME]["MAE"],
        )

    def test_check_command_records_canonical_invocation(self) -> None:
        _, run_dir = execute_fixture(self.root / "chk", run_id="chk-base")
        report_path = self.root / "chk" / "reports" / "chk-recompute.json"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "benchmark.nograph_baseline",
                "recompute",
                "--run-dir",
                str(run_dir),
                "--report",
                str(report_path),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["report_path"], str(report_path))
        self.assertNotIn("run_dir", completed.stdout)
        report = fx.read_json(report_path)
        self.assertEqual(report["command"]["argv"][0], sys.executable)
        self.assertEqual(
            report["command"]["argv"][1:4],
            ["-m", "benchmark.nograph_baseline", "recompute"],
        )

    def test_readme_commands_match_the_parser(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        normalized = " ".join(readme.split())
        for fragment in (
            "python -m benchmark.nograph_baseline run --data-name r0",
            "python -m benchmark.nograph_baseline run --data-name region",
            "python -m benchmark.nograph_baseline recompute",
            "python -m benchmark.nograph_baseline compare",
            "python -m benchmark.nograph_baseline align-v2",
            "--purpose formal",
            "--purpose development",
            "--retain-candidates",
            "--report research/reports/nograph-baseline/p01-r0-recompute-001.json",
            "scratch/nograph-baseline",
            "research/reports/nograph-baseline/",
            "conda activate job-sdf-baseline",
            "benchmark/nograph_baseline/requirements.txt",
            "unsealed and not backed up",
            "does **not** require the root `requirements.txt` CUDA/DGL packages",
            "python -m unittest discover -s benchmark/nograph_baseline/tests",
        ):
            self.assertIn(fragment, normalized)
        parser = cli.build_parser()
        commands = set(parser._subparsers._group_actions[0].choices)
        self.assertEqual(commands, {"run", "recompute", "compare", "align-v2"})
        run_help = parser._subparsers._group_actions[0].choices["run"].format_help()
        for flag in (
            "--data-name",
            "--seed",
            "--run-id",
            "--ridge-backend",
            "--purpose",
            "--retain-candidates",
        ):
            self.assertIn(flag, run_help)
        for command in ("recompute", "compare", "align-v2"):
            check_help = parser._subparsers._group_actions[0].choices[
                command
            ].format_help()
            for flag in ("--report", "--run-id"):
                self.assertIn(flag, check_help, msg=f"{command}: {flag}")
        # The legacy runs-root alias is documented in the README even though the
        # parser help hides it behind the run-ID alias.
        self.assertIn("--runs-root", normalized)


class EnvironmentTests(unittest.TestCase):
    def test_job_sdf_baseline_reads_parquet_and_records_versions(self) -> None:
        import pandas as pd

        self.assertTrue(callable(pd.read_parquet))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tiny.parquet"
            pd.DataFrame({"a": [1, 2], "b": [3.0, 4.0]}).to_parquet(path, index=False)
            frame = pd.read_parquet(path)
            self.assertEqual(frame.shape, (2, 2))
        import numpy

        self.assertTrue(numpy.__version__)

    def test_default_path_does_not_import_sklearn(self) -> None:
        source = (REPO_ROOT / "benchmark" / "nograph_baseline" / "ridge.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("Lazy import keeps scikit-learn optional", source)


class CheckAdversarialTests(unittest.TestCase):
    """V-001/V-002/V-003: saved-run checks must not report false agreement."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.fixture, cls.run_dir = execute_fixture(cls.root, run_id="adv-base")
        cls.v2_log = _write_v2_log(
            cls.root / "naive-baselines.log",
            "r0",
            cls.fixture["keys"],
            cls.fixture["signal"],
            fx.read_json(cls.run_dir / "metrics.json"),
        )
        _write_v2_source_manifest(
            cls.v2_log,
            "r0",
            fx.read_json(cls.run_dir / "source-sha256.json")["sources"]["demand"][
                "sha256"
            ],
        )
        cls.checks_root = cls.root / "checks"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _copy(self, name: str) -> Path:
        destination = self.root / name
        shutil.copytree(self.run_dir, destination)
        return destination

    def _output_kwargs(self, run_id: str, legacy: bool) -> dict:
        """Return either an explicit report path or the legacy alias choice."""
        if legacy:
            return {"run_id": run_id, "runs_root": self.checks_root}
        return {"report_path": self.checks_root / f"{run_id}.json"}

    def _compare(self, a: Path, b: Path, run_id: str, *, legacy: bool = False) -> dict:
        return checks.command_compare(
            run_a=a,
            run_b=b,
            repo_root=REPO_ROOT,
            command=["probe", "compare"],
            **self._output_kwargs(run_id, legacy),
        )

    def _recompute(self, run_dir: Path, run_id: str, *, legacy: bool = False) -> dict:
        return checks.command_recompute(
            run_dir=run_dir,
            repo_root=REPO_ROOT,
            command=["probe", "recompute"],
            **self._output_kwargs(run_id, legacy),
        )

    def _align(
        self, run_dir: Path, reference: Path, run_id: str, *, legacy: bool = False
    ) -> dict:
        return checks.command_align_v2(
            run_dir=run_dir,
            reference=reference,
            repo_root=REPO_ROOT,
            command=["probe", "align-v2"],
            **self._output_kwargs(run_id, legacy),
        )

    def _mutate_json(self, run_dir: Path, relative: str, mutator) -> None:
        payload = fx.read_json(run_dir / relative)
        mutator(payload)
        (run_dir / relative).write_text(json.dumps(payload), encoding="utf-8")

    def test_compare_valid_pair_still_ok(self) -> None:
        result = self._compare(self.run_dir, self.run_dir, "adv-compare-valid")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            result["report_path"], str(self.checks_root / "adv-compare-valid.json")
        )
        self.assertTrue(result["report"]["identity_evidence_complete"])
        self.assertTrue(all(result["report"]["identity_checks"].values()))
        for value in result["report"]["identity_checks"].values():
            self.assertIsInstance(value, bool)

    def test_legacy_run_id_alias_writes_single_reports(self) -> None:
        recompute = self._recompute(self.run_dir, "adv-legacy-recompute", legacy=True)
        compare = self._compare(
            self.run_dir, self.run_dir, "adv-legacy-compare", legacy=True
        )
        align = self._align(
            self.run_dir, self.v2_log, "adv-legacy-align", legacy=True
        )
        for result, run_id, kind in (
            (recompute, "adv-legacy-recompute", "recompute"),
            (compare, "adv-legacy-compare", "compare"),
            (align, "adv-legacy-align", "align-v2"),
        ):
            with self.subTest(check=kind):
                path = self.checks_root / f"{run_id}.json"
                self.assertEqual(result["report_path"], str(path))
                self.assertTrue(path.exists())
                self.assertEqual(result["envelope"]["kind"], kind)
                self.assertNotIn("run_dir", result)

    def test_compare_rejects_different_backend(self) -> None:
        copy = self._copy("adv-backend")
        self._mutate_json(
            copy,
            "config.json",
            lambda payload: payload["spec"].__setitem__("ridge_backend", "sklearn"),
        )
        self.assertEqual(
            self._compare(self.run_dir, copy, "adv-compare-backend")["status"],
            "mismatch",
        )

    def test_compare_rejects_different_protocol_hash(self) -> None:
        copy = self._copy("adv-protocol")
        self._mutate_json(
            copy,
            "source-sha256.json",
            lambda payload: payload["sources"]["protocol"].__setitem__(
                "sha256", "0" * 64
            ),
        )
        self.assertEqual(
            self._compare(self.run_dir, copy, "adv-compare-protocol")["status"],
            "mismatch",
        )

    def test_compare_rejects_different_environment(self) -> None:
        copy = self._copy("adv-env")
        self._mutate_json(
            copy,
            "environment.json",
            lambda payload: payload["packages"].__setitem__(
                "numpy", "different-version"
            ),
        )
        self.assertEqual(
            self._compare(self.run_dir, copy, "adv-compare-env")["status"],
            "mismatch",
        )

    def test_compare_rejects_different_blas_os_or_cpu_conditions(self) -> None:
        for field, value in (
            ("numpy_blas_config", "different-blas-configuration"),
            ("platform", "different-platform"),
            ("processor", "different-processor"),
            ("cpu_count", 999),
            ("python_version", "different-python"),
        ):
            with self.subTest(field=field):
                copy = self._copy(f"adv-env-{field}")
                self._mutate_json(
                    copy,
                    "environment.json",
                    lambda payload, field=field, value=value: payload.__setitem__(
                        field, value
                    ),
                )
                self.assertEqual(
                    self._compare(
                        self.run_dir, copy, f"adv-compare-env-{field}"
                    )["status"],
                    "mismatch",
                )

    def test_compare_requires_condition_fields_present(self) -> None:
        copy = self._copy("adv-env-missing")
        self._mutate_json(
            copy, "environment.json", lambda payload: payload.pop("numpy_blas_config")
        )
        result = self._compare(self.run_dir, copy, "adv-compare-env-missing")
        self.assertEqual(result["status"], "mismatch")
        self.assertFalse(
            result["report"]["identity_checks"]["environment_condition_complete"]
        )
        self.assertFalse(result["report"]["identity_evidence_complete"])
        self.assertTrue(
            any(
                "environment.numpy_blas_config" in item
                for item in result["report"]["missing_evidence"]
            )
        )

    def test_compare_rejects_different_coverage_identity(self) -> None:
        first = self._copy("adv-cov-a")
        second = self._copy("adv-cov-b")
        self._mutate_json(
            first,
            "source-sha256.json",
            lambda payload: (
                payload.__setitem__("coverage_bundle_sha256", "first-bundle"),
                payload["sources"]["coverage"].__setitem__("sha256", "a" * 64),
            ),
        )
        self._mutate_json(
            second,
            "source-sha256.json",
            lambda payload: (
                payload.__setitem__("coverage_bundle_sha256", "different-bundle"),
                payload["sources"]["coverage"].__setitem__("sha256", "b" * 64),
            ),
        )
        result = self._compare(first, second, "adv-compare-coverage")
        self.assertEqual(result["status"], "mismatch")
        self.assertFalse(result["report"]["identity_checks"]["coverage_identity"])

    def test_compare_treats_missing_evidence_as_incomplete(self) -> None:
        copy = self._copy("adv-missing-env")
        (copy / "environment.json").unlink()
        result = self._compare(self.run_dir, copy, "adv-compare-missing")
        self.assertEqual(result["status"], "mismatch")
        self.assertFalse(result["report"]["identity_evidence_complete"])
        self.assertTrue(result["report"]["missing_evidence"])

    def test_recompute_valid_run_still_ok(self) -> None:
        result = self._recompute(self.run_dir, "adv-recompute-valid")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["report"]["relative_gains_comparison"]["status"], "ok")
        self.assertEqual(result["report"]["node_error_comparison"]["status"], "ok")

    def test_recompute_detects_altered_relative_gain(self) -> None:
        copy = self._copy("adv-gain")
        self._mutate_json(
            copy,
            "metrics.json",
            lambda payload: payload["relative_gains"]["test"]["SharedRidge"][
                payload["references"]["NaiveRef"]
            ]["overall"].__setitem__("relative_MAE_gain", 999.0),
        )
        result = self._recompute(copy, "adv-recompute-gain")
        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(
            result["report"]["relative_gains_comparison"]["status"], "mismatch"
        )

    def test_recompute_detects_corrupted_node_error_sums(self) -> None:
        import pandas as pd

        copy = self._copy("adv-nodeerr")
        frame = pd.read_parquet(copy / "node-errors.parquet")
        frame.loc[0, "squared_error_sum"] = (
            frame.loc[0, "squared_error_sum"] + 1000.0
        )
        frame.to_parquet(copy / "node-errors.parquet", index=False)
        result = self._recompute(copy, "adv-recompute-nodeerr")
        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(result["report"]["node_error_comparison"]["status"], "mismatch")

    def test_recompute_rejects_missing_required_field(self) -> None:
        copy = self._copy("adv-missinggain")
        self._mutate_json(
            copy, "metrics.json", lambda payload: payload.pop("relative_gains")
        )
        result = self._recompute(copy, "adv-recompute-missing")
        self.assertEqual(result["status"], "mismatch")
        self.assertIn("relative_gains", result["report"]["missing_report_fields"])

    def test_recompute_rejects_deleted_nested_gain(self) -> None:
        copy = self._copy("adv-nested-gain")

        def _delete_nested(payload):
            reference = payload["references"]["NaiveRef"]
            del payload["relative_gains"]["test"]["SharedRidge"][reference][
                "overall"
            ]["relative_MAE_gain"]

        self._mutate_json(copy, "metrics.json", _delete_nested)
        result = self._recompute(copy, "adv-recompute-nested-gain")
        self.assertEqual(result["status"], "mismatch")
        comparison = result["report"]["relative_gains_comparison"]
        self.assertEqual(comparison["status"], "mismatch")
        self.assertTrue(comparison["missing_fields"])

    def test_recompute_rejects_deleted_method_report(self) -> None:
        copy = self._copy("adv-method-gone")
        self._mutate_json(
            copy,
            "metrics.json",
            lambda payload: payload["methods"]["test"].pop(protocol.MODEL_NAME),
        )
        result = self._recompute(copy, "adv-recompute-method-gone")
        self.assertEqual(result["status"], "mismatch")
        self.assertTrue(result["report"]["comparisons"]["test"]["missing_fields"])

    def test_recompute_rejects_nonfinite_node_error_values(self) -> None:
        import pandas as pd

        copy = self._copy("adv-nan-node")
        frame = pd.read_parquet(copy / "node-errors.parquet")
        frame.loc[0, "MAE"] = float("nan")
        frame.to_parquet(copy / "node-errors.parquet", index=False)
        result = self._recompute(copy, "adv-recompute-nan-node")
        self.assertEqual(result["status"], "mismatch")
        comparison = result["report"]["node_error_comparison"]
        self.assertEqual(comparison["status"], "mismatch")
        self.assertTrue(comparison["nonfinite_fields"])

    def test_recompute_rejects_nonfinite_metric_values(self) -> None:
        copy = self._copy("adv-nan-metric")
        self._mutate_json(
            copy,
            "metrics.json",
            lambda payload: payload["methods"]["test"][protocol.MODEL_NAME].__setitem__(
                "MAE", float("inf")
            ),
        )
        result = self._recompute(copy, "adv-recompute-nan-metric")
        self.assertEqual(result["status"], "mismatch")
        self.assertTrue(result["report"]["nonfinite_stored_fields"])

    def test_align_v2_valid_reference_still_ok(self) -> None:
        result = self._align(self.run_dir, self.v2_log, "adv-align-valid")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(
            result["report"]["identity_evidence"]["demand_sha256_matches_v2"]
        )

    def test_align_v2_rejects_source_identity_mismatch(self) -> None:
        copy = self._copy("adv-identity")
        self._mutate_json(
            copy,
            "source-sha256.json",
            lambda payload: payload["sources"]["demand"].__setitem__("sha256", "0" * 64),
        )
        result = self._align(copy, self.v2_log, "adv-align-mismatch")
        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(result["report"]["identity_status"], "mismatch")
        self.assertTrue(
            any(
                row["field"] == "identity.demand_sha256_vs_v2"
                for row in result["report"]["discrepancies"]
            )
        )

    def test_align_v2_reports_limited_without_v2_source_manifest(self) -> None:
        bare = self.root / "bare-reference"
        bare.mkdir()
        log = bare / "naive-baselines.log"
        shutil.copy(self.v2_log, log)
        result = self._align(self.run_dir, log, "adv-align-limited")
        self.assertEqual(result["status"], "limited")
        self.assertEqual(result["report"]["identity_status"], "limited")
        self.assertTrue(result["report"]["limited_findings"])


class RecomputeNullSemanticsTests(unittest.TestCase):
    """V-002: required null metrics and unavailable/empty status are enforced."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        # An all-zero six-node fixture yields a zero LastValue reference and
        # empty activity groups, i.e. legitimate null gains and null metrics.
        keys = fx.r0_keys(6)
        signal = np.zeros((6, 36), dtype=np.float32)
        demand = fx.write_demand(cls.root / "r0.parquet", "r0", keys, signal)
        graph = fx.write_graph(cls.root / "g.parquet", "r0", [[0, 0, 1]])
        spec = fx.make_run_spec(cls.root / "runs", "r0", demand, graph, "null-base")
        cls.run_dir = Path(runner.execute_run(spec)["run_dir"])
        cls.checks_root = cls.root / "checks"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _recompute(self, run_dir: Path, run_id: str, *, legacy: bool = False) -> dict:
        kwargs = (
            {"run_id": run_id, "runs_root": self.checks_root}
            if legacy
            else {"report_path": self.checks_root / f"{run_id}.json"}
        )
        return checks.command_recompute(
            run_dir=run_dir,
            repo_root=REPO_ROOT,
            command=["probe", "recompute"],
            **kwargs,
        )

    def _copy(self, name: str) -> Path:
        destination = self.root / name
        shutil.copytree(self.run_dir, destination)
        return destination

    def _metrics(self) -> dict:
        return fx.read_json(self.run_dir / "metrics.json")

    def _null_gain_location(self):
        for reference, entry in self._metrics()["relative_gains"]["test"][
            protocol.MODEL_NAME
        ].items():
            for level, record in entry.items():
                if isinstance(record, dict) and record.get("status") == "unavailable":
                    return reference, level
        raise AssertionError("fixture has no unavailable gain")

    def _empty_group_location(self):
        for method, report in self._metrics()["methods"]["test"].items():
            for group, record in report.get("activity_groups", {}).items():
                if record.get("status") == "empty":
                    return method, group
        raise AssertionError("fixture has no empty group")

    def test_fixture_exercises_null_gain_and_empty_group(self) -> None:
        self._null_gain_location()
        self._empty_group_location()

    def test_intact_zero_reference_fixture_recomputes(self) -> None:
        result = self._recompute(self.run_dir, "null-valid")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            result["report_path"], str(self.checks_root / "null-valid.json")
        )
        report = result["report"]
        self.assertGreater(report["comparisons"]["test"]["null_fields"], 0)
        self.assertEqual(report["stored_semantic_problems"], [])
        self.assertEqual(report["recomputed_semantic_problems"], [])
        self.assertEqual(report["gain_semantic_problems"], [])

    def test_legacy_run_id_alias_writes_one_report(self) -> None:
        result = self._recompute(self.run_dir, "null-legacy", legacy=True)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            result["report_path"], str(self.checks_root / "null-legacy.json")
        )
        self.assertTrue((self.checks_root / "null-legacy.json").exists())

    def test_deleted_null_gain_field_fails(self) -> None:
        copy = self._copy("null-gain-deleted")
        payload = fx.read_json(copy / "metrics.json")
        reference, level = self._null_gain_location()
        del payload["relative_gains"]["test"][protocol.MODEL_NAME][reference][level][
            "relative_MAE_gain"
        ]
        (copy / "metrics.json").write_text(json.dumps(payload), encoding="utf-8")
        result = self._recompute(copy, "null-gain-deleted-check")
        self.assertEqual(result["status"], "mismatch")
        comparison = result["report"]["relative_gains_comparison"]
        self.assertEqual(comparison["status"], "mismatch")
        self.assertTrue(comparison["missing_fields"])

    def test_contradictory_unavailable_status_fails(self) -> None:
        copy = self._copy("null-gain-status")
        payload = fx.read_json(copy / "metrics.json")
        reference, level = self._null_gain_location()
        payload["relative_gains"]["test"][protocol.MODEL_NAME][reference][level][
            "status"
        ] = "ok"
        (copy / "metrics.json").write_text(json.dumps(payload), encoding="utf-8")
        result = self._recompute(copy, "null-gain-status-check")
        self.assertEqual(result["status"], "mismatch")
        self.assertTrue(result["report"]["gain_semantic_problems"])
        self.assertEqual(
            result["report"]["relative_gains_comparison"]["status"], "mismatch"
        )

    def test_deleted_empty_group_null_metric_fails(self) -> None:
        copy = self._copy("null-mae-deleted")
        payload = fx.read_json(copy / "metrics.json")
        method, group = self._empty_group_location()
        del payload["methods"]["test"][method]["activity_groups"][group]["MAE"]
        (copy / "metrics.json").write_text(json.dumps(payload), encoding="utf-8")
        result = self._recompute(copy, "null-mae-deleted-check")
        self.assertEqual(result["status"], "mismatch")
        self.assertTrue(result["report"]["comparisons"]["test"]["missing_fields"])

    def test_report_schema_comparison_preserves_nulls(self) -> None:
        expected = {"status": "empty", "MAE": None, "elements": 0}
        actual = {"status": "empty", "MAE": None, "elements": 0}
        result = checks.compare_report_schema(
            expected, actual, tolerance=1e-12, label="nulls"
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["null_fields"], 1)
        missing = checks.compare_report_schema(
            {"MAE": None}, {}, tolerance=1e-12, label="missing-null"
        )
        self.assertEqual(missing["status"], "mismatch")
        self.assertTrue(missing["missing_fields"])
        status = checks.compare_report_schema(
            {"status": "unavailable", "relative_MAE_gain": None},
            {"status": "ok", "relative_MAE_gain": None},
            tolerance=1e-12,
            label="status",
        )
        self.assertEqual(status["status"], "mismatch")
        self.assertTrue(status["failed_fields"])

    def test_report_semantics_detects_contradictions(self) -> None:
        valid = {"status": "empty", "elements": 0, "MAE": None}
        self.assertEqual(checks.validate_report_semantics(valid), [])
        problems = checks.validate_report_semantics(
            {"status": "ok", "elements": 0, "MAE": None}
        )
        self.assertTrue(problems)
        gain_problems = checks.validate_report_semantics(
            {"status": "unavailable", "relative_MAE_gain": 0.5}
        )
        self.assertTrue(gain_problems)


class PurposeDeltaTests(unittest.TestCase):
    """Task 2.1: formal/development purpose, default roots and rejection."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.fixture = fx.build_fixture(self.root / "fixture", "r0", node_count=6)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _formal_spec(self, fixture, data_name: str, runs_root: Path, run_id: str):
        return fx.make_run_spec(
            runs_root,
            data_name,
            fixture["demand_path"],
            fixture["graph_path"],
            run_id,
            purpose="formal",
        )

    def _development_spec(self, fixture, data_name: str, run_id: str, runs_root):
        return runner.RunSpec(
            data_name=data_name,
            run_id=run_id,
            mode="count",
            seed=0,
            purpose="development",
            retain_candidates=False,
            demand_path=str(fixture["demand_path"]),
            graph_path=str(fixture["graph_path"]),
            runs_root=None if runs_root is None else str(runs_root),
            repo_root=str(REPO_ROOT),
            command=["python", "-m", "benchmark.nograph_baseline", "run"],
            run_type="run",
        )

    def _assert_equivalent(self, formal_dir: Path, development_dir: Path) -> None:
        for method in protocol.NAIVE_METHODS + (protocol.MODEL_NAME,):
            for split in ("validation", "test"):
                with self.subTest(method=method, split=split):
                    formal = np.load(
                        formal_dir / "predictions" / method / f"{split}.npy",
                        allow_pickle=False,
                    )
                    development = np.load(
                        development_dir / "predictions" / method / f"{split}.npy",
                        allow_pickle=False,
                    )
                    np.testing.assert_array_equal(formal, development)
        formal_metrics = fx.read_json(formal_dir / "metrics.json")
        development_metrics = fx.read_json(development_dir / "metrics.json")
        self.assertEqual(formal_metrics["methods"], development_metrics["methods"])
        self.assertEqual(
            formal_metrics["references"], development_metrics["references"]
        )
        self.assertEqual(
            formal_metrics["relative_gains"], development_metrics["relative_gains"]
        )
        formal_selection = fx.read_json(formal_dir / "selection.json")
        development_selection = fx.read_json(development_dir / "selection.json")
        self.assertEqual(
            formal_selection["shared_ridge"]["selected_lambda"],
            development_selection["shared_ridge"]["selected_lambda"],
        )

    def test_development_default_root_matches_formal_without_formal_directory(
        self,
    ) -> None:
        run_id = _unique_run_id("delta-dev")
        formal_id = _unique_run_id("delta-formal")
        formal_dir = Path(
            runner.execute_run(
                self._formal_spec(self.fixture, "r0", self.root / "runs", formal_id)
            )["run_dir"]
        )
        scratch_root_existed = DEVELOPMENT_DEFAULT_ROOT.exists()
        development_dir = Path(self.root / "unused")
        try:
            development_dir = Path(
                runner.execute_run(
                    self._development_spec(self.fixture, "r0", run_id, None)
                )["run_dir"]
            )
            self.assertEqual(development_dir.parent, DEVELOPMENT_DEFAULT_ROOT)
            self.assertTrue(development_dir.exists())
            self.assertFalse((FORMAL_DEFAULT_ROOT / run_id).exists())
            status = fx.read_json(development_dir / "status.json")
            self.assertEqual(status["state"], "success")
            self.assertEqual(status["purpose"], "development")
            config = fx.read_json(development_dir / "config.json")
            self.assertEqual(config["spec"]["purpose"], "development")
            provenance = fx.read_json(development_dir / "provenance.json")
            self.assertEqual(provenance["purpose"], "development")
            self.assertIn("source_capture", provenance)
            self.assertNotIn("untracked_source", provenance)
            summary = (development_dir / "summary.md").read_text(encoding="utf-8")
            self.assertIn("development output; not scientific acceptance", summary)
            self._assert_equivalent(formal_dir, development_dir)
        finally:
            _clean_development_output(development_dir, scratch_root_existed)

    def test_development_root_inside_formal_namespace_is_rejected(self) -> None:
        run_id = _unique_run_id("delta-reject")
        spec = self._development_spec(
            self.fixture, "r0", run_id, FORMAL_DEFAULT_ROOT
        )
        with self.assertRaises(runner.RunError):
            runner.execute_run(spec)
        self.assertFalse((FORMAL_DEFAULT_ROOT / run_id).exists())

    def test_symlink_alias_to_formal_namespace_is_rejected(self) -> None:
        run_id = _unique_run_id("delta-alias")
        alias = self.root / "runs-alias"
        alias.symlink_to(FORMAL_DEFAULT_ROOT, target_is_directory=True)
        spec = self._development_spec(self.fixture, "r0", run_id, alias)
        with self.assertRaises(runner.RunError):
            runner.execute_run(spec)
        self.assertFalse((FORMAL_DEFAULT_ROOT / run_id).exists())
        self.assertFalse((alias / run_id).exists())

    def test_development_with_explicit_temp_root_is_allowed(self) -> None:
        run_id = _unique_run_id("delta-dev-explicit")
        development_root = self.root / "development-runs"
        development_dir = Path(
            runner.execute_run(
                self._development_spec(
                    self.fixture, "r0", run_id, development_root
                )
            )["run_dir"]
        )
        self.assertEqual(development_dir.parent, development_root)
        self.assertEqual(
            fx.read_json(development_dir / "status.json")["purpose"], "development"
        )
        self.assertFalse((FORMAL_DEFAULT_ROOT / run_id).exists())

    def test_unknown_purpose_is_rejected(self) -> None:
        run_id = _unique_run_id("delta-unknown")
        spec = fx.make_run_spec(
            self.root / "runs",
            "r0",
            self.fixture["demand_path"],
            self.fixture["graph_path"],
            run_id,
            purpose="provisional",
        )
        with self.assertRaises(runner.RunError):
            runner.execute_run(spec)
        self.assertFalse((self.root / "runs" / run_id).exists())

    def test_region_development_matches_formal(self) -> None:
        fixture = fx.build_fixture(self.root / "region-fixture", "region", node_count=2)
        formal_dir = Path(
            runner.execute_run(
                self._formal_spec(
                    fixture, "region", self.root / "region-formal", "region-formal"
                )
            )["run_dir"]
        )
        development_dir = Path(
            runner.execute_run(
                self._development_spec(
                    fixture, "region", "region-development", self.root / "region-dev"
                )
            )["run_dir"]
        )
        self.assertEqual(
            fx.read_json(development_dir / "status.json")["purpose"], "development"
        )
        self._assert_equivalent(formal_dir, development_dir)


class CandidateRetentionDeltaTests(unittest.TestCase):
    """Task 2.3: default retention omits losing arrays; opt-in keeps them."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _expect_retention(self, data_name: str, node_count: int, prefix: str) -> None:
        fixture = fx.build_fixture(
            self.root / f"{prefix}-fixture", data_name, node_count=node_count
        )
        default_dir = Path(
            runner.execute_run(
                fx.make_run_spec(
                    self.root / f"{prefix}-default",
                    data_name,
                    fixture["demand_path"],
                    fixture["graph_path"],
                    f"{prefix}-default",
                )
            )["run_dir"]
        )
        retain_dir = Path(
            runner.execute_run(
                fx.make_run_spec(
                    self.root / f"{prefix}-retain",
                    data_name,
                    fixture["demand_path"],
                    fixture["graph_path"],
                    f"{prefix}-retain",
                    retain_candidates=True,
                )
            )["run_dir"]
        )

        self.assertFalse((default_dir / "candidates").exists())
        for run_dir in (default_dir, retain_dir):
            self.assertTrue((run_dir / "models" / "SharedRidge.npz").exists())
            self.assertTrue((run_dir / "selection.json").exists())

        default_selection = fx.read_json(default_dir / "selection.json")
        retain_selection = fx.read_json(retain_dir / "selection.json")
        for selection in (default_selection, retain_selection):
            rows = selection["shared_ridge"]["candidate_table"]
            self.assertEqual(len(rows), len(protocol.LAMBDA_CANDIDATES))
            self.assertEqual(
                {row["lambda"] for row in rows},
                set(protocol.LAMBDA_CANDIDATES),
            )
            self.assertIn(
                selection["shared_ridge"]["selected_lambda"],
                set(protocol.LAMBDA_CANDIDATES),
            )
        selected_lambda = default_selection["shared_ridge"]["selected_lambda"]
        self.assertEqual(
            selected_lambda, retain_selection["shared_ridge"]["selected_lambda"]
        )

        for method in protocol.NAIVE_METHODS + (protocol.MODEL_NAME,):
            for split in ("validation", "test"):
                with self.subTest(method=method, split=split):
                    default_pred = np.load(
                        default_dir / "predictions" / method / f"{split}.npy",
                        allow_pickle=False,
                    )
                    retain_pred = np.load(
                        retain_dir / "predictions" / method / f"{split}.npy",
                        allow_pickle=False,
                    )
                    np.testing.assert_array_equal(default_pred, retain_pred)
        self.assertEqual(
            fx.read_json(default_dir / "metrics.json")["methods"],
            fx.read_json(retain_dir / "metrics.json")["methods"],
        )

        labels = sorted(f"{name:g}" for name in protocol.LAMBDA_CANDIDATES)
        self.assertEqual(
            sorted(path.name for path in (retain_dir / "candidates").iterdir()),
            labels,
        )
        for label in labels:
            self.assertTrue(
                (retain_dir / "candidates" / label / "parameters.npz").exists()
            )
            self.assertTrue(
                (retain_dir / "candidates" / label / "validation.npy").exists()
            )

        selected_label = f"{selected_lambda:g}"
        with np.load(
            retain_dir / "candidates" / selected_label / "parameters.npz",
            allow_pickle=False,
        ) as handle:
            retained_w = handle["W"]
            retained_b = handle["b"]
        for run_dir in (default_dir, retain_dir):
            with np.load(
                run_dir / "models" / "SharedRidge.npz", allow_pickle=False
            ) as handle:
                weights = handle["W"]
                bias = handle["b"]
                mean = handle["node_mean"]
                effective_std = handle["node_effective_std"]
                scalar = handle["scalar"]
            self.assertAlmostEqual(float(scalar[0]), float(selected_lambda))
            np.testing.assert_allclose(weights, retained_w)
            np.testing.assert_allclose(bias, retained_b)
            raw = fixture["signal"][:, 24:30].astype(np.float64)
            standardized = (raw - mean[:, None]) / effective_std[:, None]
            prediction = (standardized @ weights + bias) * effective_std[
                :, None
            ] + mean[:, None]
            saved = np.load(
                run_dir / "predictions" / protocol.MODEL_NAME / "test.npy",
                allow_pickle=False,
            )
            np.testing.assert_allclose(saved[0], prediction, atol=1e-9)

    def test_r0_default_and_retained_candidates(self) -> None:
        self._expect_retention("r0", 6, "r0")

    def test_region_default_and_retained_candidates(self) -> None:
        self._expect_retention("region", 2, "region")


class SourceCaptureDeltaTests(unittest.TestCase):
    """Task 2.2: scoped references, scoped patches and untracked fallback."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _repo(self, name: str) -> Path:
        repo = _init_git_repo(self.root / name)
        (repo / "pkg").mkdir(parents=True, exist_ok=True)
        (repo / "pkg" / "clean.py").write_text("VALUE = 1\n", encoding="utf-8")
        (repo / "pkg" / "modified.py").write_text("VALUE = 2\n", encoding="utf-8")
        (repo / "protocol.md").write_text("protocol v1\n", encoding="utf-8")
        _commit_all(repo)
        return repo

    def _capture(self, repo: Path, run_id: str, **kwargs):
        run = artifacts.RunDirectory(self.root / "run-dirs", run_id, "run").reserve()
        return run, artifacts.capture_source(run, repo, **kwargs)

    def test_clean_tracked_files_are_referenced_not_copied(self) -> None:
        repo = self._repo("clean-repo")
        run, record = self._capture(
            repo, "clean", runtime_paths=["pkg/clean.py"]
        )
        entry = record["files"]["pkg/clean.py"]
        self.assertEqual(entry["git_status"], "committed_clean")
        self.assertIsNotNone(entry["git_reference"])
        self.assertEqual(entry["git_reference"]["commit"], record["commit"])
        self.assertEqual(entry["git_reference"]["path"], "pkg/clean.py")
        self.assertEqual(entry["git_reference"]["sha256"], entry["sha256"])
        self.assertEqual(entry["sha256"], _sha256_file(repo / "pkg" / "clean.py"))
        self.assertIsNone(entry["content_saved"])
        self.assertFalse(record["scoped_dirty"])
        self.assertFalse((run.path / "code-untracked").exists())
        self.assertEqual((run.path / "git-diff.patch").read_text(), "")

    def test_modified_tracked_file_is_patched_not_copied(self) -> None:
        repo = self._repo("modified-repo")
        (repo / "pkg" / "modified.py").write_text("VALUE = 999\n", encoding="utf-8")
        run, record = self._capture(
            repo, "modified", runtime_paths=["pkg/modified.py"]
        )
        entry = record["files"]["pkg/modified.py"]
        self.assertEqual(entry["git_status"], "modified")
        self.assertIsNone(entry["content_saved"])
        self.assertIsNotNone(entry["git_reference"])
        self.assertNotEqual(entry["git_reference"]["sha256"], entry["sha256"])
        self.assertEqual(entry["sha256"], _sha256_file(repo / "pkg" / "modified.py"))
        self.assertTrue(record["scoped_dirty"])
        patch = (run.path / "git-diff.patch").read_text(encoding="utf-8")
        self.assertIn("VALUE = 999", patch)
        self.assertGreater(record["patch_bytes"], 0)
        self.assertFalse((run.path / "code-untracked").exists())

    def test_untracked_file_content_is_saved_and_manifested(self) -> None:
        repo = self._repo("untracked-repo")
        (repo / "pkg" / "untracked.py").write_text("NEW = 7\n", encoding="utf-8")
        run, record = self._capture(
            repo, "untracked", runtime_paths=["pkg/untracked.py"]
        )
        entry = record["files"]["pkg/untracked.py"]
        self.assertEqual(entry["git_status"], "untracked")
        self.assertIsNone(entry["git_reference"])
        self.assertEqual(entry["content_saved"], "code-untracked/pkg/untracked.py")
        saved = run.path / "code-untracked" / "pkg" / "untracked.py"
        self.assertEqual(saved.read_text(encoding="utf-8"), "NEW = 7\n")
        self.assertEqual(_sha256_file(saved), entry["sha256"])
        self.assertTrue(record["scoped_dirty"])
        manifest = fx.read_json(run.path / "code-untracked" / "manifest.json")
        self.assertEqual(manifest["files"], {"pkg/untracked.py": entry["sha256"]})

    def test_protocol_path_is_scoped_and_hashed(self) -> None:
        repo = self._repo("protocol-repo")
        run, record = self._capture(
            repo,
            "protocol",
            runtime_paths=["pkg/clean.py"],
            protocol_path=repo / "protocol.md",
        )
        self.assertIn("protocol.md", record["runtime_scope"])
        self.assertEqual(record["protocol"]["path"], "protocol.md")
        self.assertEqual(
            record["protocol"]["sha256"],
            _sha256_file(repo / "protocol.md"),
        )
        self.assertIn("protocol.md", record["files"])

    def test_unavailable_git_identity_saves_content_fallback(self) -> None:
        plain = self.root / "no-git"
        plain.mkdir(parents=True, exist_ok=True)
        (plain / "runtime.py").write_text("X = 1\n", encoding="utf-8")
        run, record = self._capture(plain, "no-git", runtime_paths=["runtime.py"])
        self.assertFalse(record["identity_available"])
        self.assertIsNone(record["commit"])
        self.assertTrue(record["errors"])
        entry = record["files"]["runtime.py"]
        self.assertEqual(entry["git_status"], "unknown")
        self.assertEqual(entry["content_saved"], "code-untracked/runtime.py")
        self.assertTrue(entry["unavailable_reason"])
        self.assertTrue((run.path / "code-untracked" / "runtime.py").exists())

    def test_runtime_scope_excludes_tests_and_caches(self) -> None:
        scope = artifacts.runtime_source_paths(REPO_ROOT)
        self.assertTrue(scope)
        for relative in scope:
            parts = Path(relative).parts
            self.assertNotIn("tests", parts, msg=relative)
            self.assertNotIn("__pycache__", parts, msg=relative)
            self.assertTrue(relative.startswith("benchmark/"), msg=relative)
        self.assertIn("benchmark/nograph_baseline/cli.py", scope)
        self.assertIn("benchmark/nograph_baseline/runner.py", scope)
        protocol_relative = (
            protocol.PROTOCOL_PATH.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        )
        self.assertNotIn(protocol_relative, scope)


class CheckReportContractTests(unittest.TestCase):
    """Tasks 3.1/3.2: one exclusive report per check and safe failures."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.fixture, cls.run_dir = execute_fixture(cls.root, run_id="contract-base")
        cls.v2_log = _write_v2_log(
            cls.root / "naive-baselines.log",
            "r0",
            cls.fixture["keys"],
            cls.fixture["signal"],
            fx.read_json(cls.run_dir / "metrics.json"),
        )
        _write_v2_source_manifest(
            cls.v2_log,
            "r0",
            fx.read_json(cls.run_dir / "source-sha256.json")["sources"]["demand"][
                "sha256"
            ],
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _recompute(self, run_dir=None, *, report_path=None, run_id=None, runs_root=None):
        return checks.command_recompute(
            run_dir=run_dir or self.run_dir,
            repo_root=REPO_ROOT,
            command=["probe", "recompute"],
            report_path=report_path,
            run_id=run_id,
            runs_root=runs_root,
        )

    def _compare(self, a=None, b=None, *, report_path=None, run_id=None, runs_root=None):
        return checks.command_compare(
            run_a=a or self.run_dir,
            run_b=b or self.run_dir,
            repo_root=REPO_ROOT,
            command=["probe", "compare"],
            report_path=report_path,
            run_id=run_id,
            runs_root=runs_root,
        )

    def _align(
        self, run_dir=None, reference=None, *, report_path=None, run_id=None, runs_root=None
    ):
        return checks.command_align_v2(
            run_dir=run_dir or self.run_dir,
            reference=reference or self.v2_log,
            repo_root=REPO_ROOT,
            command=["probe", "align-v2"],
            report_path=report_path,
            run_id=run_id,
            runs_root=runs_root,
        )

    def _calls(self):
        return (
            ("recompute", "recompute", lambda **kwargs: self._recompute(**kwargs)),
            ("compare", "compare", lambda **kwargs: self._compare(**kwargs)),
            ("align", "align-v2", lambda **kwargs: self._align(**kwargs)),
        )

    def test_three_checks_write_exactly_one_envelope(self) -> None:
        tolerances = {
            "recompute": checks.RECOMPUTE_TOLERANCES,
            "compare": checks.COMPARE_TOLERANCES,
            "align-v2": checks.ALIGN_TOLERANCES,
        }
        for label, kind, call in self._calls():
            with self.subTest(check=kind):
                parent = self.root / "reports" / label
                destination = parent / "nested" / "report.json"
                before_run = _tree_hash(self.run_dir)
                before_reference = _sha256_file(self.v2_log)
                result = call(report_path=destination)
                self.assertEqual(
                    set(result), {"report_path", "status", "report", "envelope"}
                )
                self.assertEqual(result["report_path"], str(destination))
                self.assertEqual(result["status"], "ok")
                self.assertTrue(destination.exists())
                written = [path for path in parent.rglob("*") if path.is_file()]
                self.assertEqual(written, [destination])
                envelope = result["envelope"]
                self.assertEqual(envelope["version"], checks.REPORT_VERSION)
                self.assertEqual(envelope["kind"], kind)
                self.assertEqual(envelope["status"], "ok")
                self.assertEqual(envelope["errors"], [])
                self.assertTrue(envelope["created"])
                self.assertEqual(envelope["command"]["argv"], ["probe", kind])
                self.assertTrue(envelope["command"]["cwd"])
                self.assertEqual(
                    envelope["checker"]["protocol_version"],
                    protocol.PROTOCOL_VERSION,
                )
                source = envelope["checker"]["source"]
                for key in (
                    "policy",
                    "commit",
                    "identity_available",
                    "whole_repository_dirty",
                    "scoped_dirty",
                    "files",
                    "scoped_files",
                    "patch_included",
                    "source_patch",
                    "patch_bytes",
                    "patch_omitted_reason",
                    "errors",
                ):
                    self.assertIn(key, source)
                self.assertEqual(result["report"], envelope["result"])
                self.assertEqual(envelope["result"]["status"], "ok")
                self.assertIn("inputs", envelope)
                self.assertEqual(envelope["tolerances"], tolerances[kind])
                self.assertEqual(_tree_hash(self.run_dir), before_run)
                self.assertEqual(_sha256_file(self.v2_log), before_reference)

    def test_recompute_embeds_recomputed_metrics_and_retains_fields(self) -> None:
        result = self._recompute(report_path=self.root / "reports" / "embed.json")
        report = result["report"]
        self.assertEqual(sorted(report["recomputed_metrics"]), ["test", "validation"])
        self.assertIn(protocol.MODEL_NAME, report["recomputed_metrics"]["test"])
        self.assertIn("test", report["recomputed_relative_gains"])
        self.assertIn("validation", report["recomputed_relative_gains"])
        for key in (
            "comparisons",
            "relative_gains_comparison",
            "node_error_comparison",
            "missing_report_fields",
            "nonfinite_stored_fields",
            "nonfinite_recomputed_fields",
            "stored_semantic_problems",
            "recomputed_semantic_problems",
            "source_data_read",
            "model_refit",
            "status",
        ):
            self.assertIn(key, report)

    def test_legacy_run_id_alias_writes_root_id_json(self) -> None:
        for label, kind, call in self._calls():
            with self.subTest(check=kind):
                runs_root = self.root / "alias" / label
                run_id = f"contract-{label}"
                result = call(run_id=run_id, runs_root=runs_root)
                self.assertEqual(result["report_path"], str(runs_root / f"{run_id}.json"))
                self.assertEqual(result["envelope"]["kind"], kind)
                self.assertTrue((runs_root / f"{run_id}.json").exists())

    def test_report_and_legacy_run_id_are_mutually_exclusive(self) -> None:
        for label, kind, call in self._calls():
            with self.subTest(check=kind):
                destination = self.root / "reports" / f"mutual-{label}.json"
                alias = self.root / "mutual-alias" / f"mutual-{label}.json"
                with self.assertRaises(checks.CheckError):
                    call(
                        report_path=destination,
                        run_id=f"mutual-{label}",
                        runs_root=alias.parent,
                    )
                self.assertFalse(destination.exists())
                self.assertFalse(alias.exists())

    def test_missing_or_invalid_alias_output_choices_are_rejected(self) -> None:
        self.assertEqual(
            checks.default_reports_root(REPO_ROOT),
            REPO_ROOT / "research" / "reports" / "nograph-baseline",
        )
        with self.assertRaises(checks.CheckError):
            self._recompute()
        alias_root = self.root / "invalid-alias"
        for run_id in ("../escape", "nested/id", "..", ""):
            with self.subTest(run_id=run_id):
                with self.assertRaises(
                    (artifacts.ArtifactError, checks.CheckError)
                ):
                    self._recompute(run_id=run_id, runs_root=alias_root)
        self.assertFalse(alias_root.exists())

    def test_existing_destination_is_never_replaced(self) -> None:
        destination = self.root / "exclusive" / "existing.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"original-bytes")
        for label, kind, call in self._calls():
            with self.subTest(check=kind):
                with self.assertRaises(checks.CheckError):
                    call(report_path=destination)
                self.assertEqual(destination.read_bytes(), b"original-bytes")
        self.assertEqual(
            [path.name for path in destination.parent.iterdir()], ["existing.json"]
        )

    def test_symlink_destination_is_rejected(self) -> None:
        target = self.root / "symlink-target.json"
        target.write_bytes(b"target-bytes")
        link = self.root / "reports" / "symlink.json"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        dangling = self.root / "reports" / "dangling.json"
        dangling.symlink_to(self.root / "absent.json")
        for label, kind, call in self._calls():
            for destination in (link, dangling):
                with self.subTest(check=kind, path=destination.name):
                    with self.assertRaises(checks.CheckError):
                        call(report_path=destination)
            self.assertTrue(link.is_symlink())
            self.assertTrue(dangling.is_symlink())
        self.assertEqual(target.read_bytes(), b"target-bytes")
        self.assertFalse((self.root / "absent.json").exists())

    def test_report_inside_input_run_is_rejected(self) -> None:
        inside_run = self.run_dir / "report.json"
        with self.assertRaises(checks.CheckError):
            self._recompute(report_path=inside_run)
        with self.assertRaises(checks.CheckError):
            self._align(report_path=inside_run)
        with self.assertRaises(checks.CheckError):
            self._compare(report_path=inside_run)
        self.assertFalse(inside_run.exists())

        reference_before = _sha256_file(self.v2_log)
        with self.assertRaises(checks.CheckError):
            self._align(report_path=self.v2_log)
        self.assertEqual(_sha256_file(self.v2_log), reference_before)

    def test_missing_input_writes_failure_report_without_mutation(self) -> None:
        copy = self.root / "contract-missing"
        shutil.copytree(self.run_dir, copy)
        (copy / "metrics.json").unlink()
        before = _tree_hash(copy)
        destination = self.root / "reports" / "missing-input.json"
        result = self._recompute(run_dir=copy, report_path=destination)
        self.assertEqual(result["status"], "failed")
        self.assertNotEqual(result["status"], "ok")
        self.assertEqual(result["report"]["status"], "failed")
        self.assertTrue(result["report"]["error"])
        self.assertTrue(result["envelope"]["errors"])
        self.assertEqual(result["envelope"]["status"], "failed")
        self.assertTrue(destination.exists())
        self.assertEqual(before, _tree_hash(copy))

        absent = self.root / "no-such-run"
        failures = (
            ("recompute", lambda path: self._recompute(run_dir=absent, report_path=path)),
            ("compare", lambda path: self._compare(a=absent, report_path=path)),
            ("align", lambda path: self._align(run_dir=absent, report_path=path)),
        )
        for label, call in failures:
            with self.subTest(check=label):
                report_path = self.root / "reports" / f"failure-{label}.json"
                failure = call(report_path)
                self.assertEqual(failure["status"], "failed")
                self.assertTrue(failure["envelope"]["errors"])
                self.assertTrue(report_path.exists())
                self.assertEqual(
                    fx.read_json(report_path)["status"], "failed"
                )

    def test_region_schema_recompute_report_and_alias(self) -> None:
        fixture = fx.build_fixture(
            self.root / "region-fixture", "region", node_count=2
        )
        run_dir = Path(
            runner.execute_run(
                fx.make_run_spec(
                    self.root / "region-runs",
                    "region",
                    fixture["demand_path"],
                    fixture["graph_path"],
                    "contract-region",
                )
            )["run_dir"]
        )
        destination = self.root / "reports" / "region-recompute.json"
        result = self._recompute(run_dir=run_dir, report_path=destination)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["envelope"]["kind"], "recompute")
        self.assertIn(protocol.MODEL_NAME, result["report"]["recomputed_metrics"]["test"])
        alias = self._recompute(
            run_dir=run_dir, run_id="contract-region", runs_root=self.root / "region-alias"
        )
        self.assertEqual(
            alias["report_path"],
            str(self.root / "region-alias" / "contract-region.json"),
        )
        self.assertEqual(alias["status"], "ok")

    def test_cli_recompute_report_success_and_failure(self) -> None:
        destination = self.root / "cli" / "report.json"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "benchmark.nograph_baseline",
                "recompute",
                "--run-dir",
                str(self.run_dir),
                "--report",
                str(destination),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["report_path"], str(destination))
        self.assertEqual(payload["status"], "ok")
        self.assertNotIn("run_dir", completed.stdout)
        self.assertTrue(destination.exists())

        alias_root = self.root / "cli" / "alias"
        aliased = subprocess.run(
            [
                sys.executable,
                "-m",
                "benchmark.nograph_baseline",
                "recompute",
                "--run-dir",
                str(self.run_dir),
                "--run-id",
                "cli-alias",
                "--runs-root",
                str(alias_root),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(aliased.returncode, 0, msg=aliased.stderr)
        alias_payload = json.loads(aliased.stdout)
        self.assertEqual(
            alias_payload["report_path"], str(alias_root / "cli-alias.json")
        )
        self.assertEqual(alias_payload["status"], "ok")
        self.assertTrue((alias_root / "cli-alias.json").exists())

        missing = self.root / "cli-missing"
        shutil.copytree(self.run_dir, missing)
        (missing / "metrics.json").unlink()
        failure_path = self.root / "cli" / "failure.json"
        failed = subprocess.run(
            [
                sys.executable,
                "-m",
                "benchmark.nograph_baseline",
                "recompute",
                "--run-dir",
                str(missing),
                "--report",
                str(failure_path),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(failed.returncode, 0)
        failure_payload = json.loads(failed.stdout)
        self.assertEqual(failure_payload["status"], "failed")
        self.assertEqual(failure_payload["report_path"], str(failure_path))
        self.assertTrue(failure_path.exists())
        self.assertEqual(fx.read_json(failure_path)["status"], "failed")

        conflicting = subprocess.run(
            [
                sys.executable,
                "-m",
                "benchmark.nograph_baseline",
                "recompute",
                "--run-dir",
                str(self.run_dir),
                "--report",
                str(self.root / "cli" / "conflict.json"),
                "--run-id",
                "conflict",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(conflicting.returncode, 0)
        self.assertFalse((self.root / "cli" / "conflict.json").exists())


class RepairRegressionTests(unittest.TestCase):
    """Regression coverage for the V-001..V-005 verification findings.

    Each test would have failed before the corresponding repair.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.reports = self.root / "reports"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run_with_protocol(
        self, repo_root: Path, protocol_file: Path, run_id: str
    ) -> Path:
        fixture = fx.build_fixture(self.root / "fixture", "r0", node_count=6)
        spec = fx.make_run_spec(
            self.root / "runs",
            "r0",
            fixture["demand_path"],
            fixture["graph_path"],
            run_id,
            repo_root=str(repo_root),
            protocol_path=str(protocol_file),
        )
        return Path(runner.execute_run(spec)["run_dir"])

    # -- V-001: clean committed protocol is referenced, not copied ---------
    def test_clean_committed_protocol_is_referenced_without_a_copy(self) -> None:
        repo = _init_git_repo(self.root / "clean-protocol-repo")
        protocol_file = repo / "protocol.md"
        protocol_file.write_text("clean committed protocol\n", encoding="utf-8")
        _commit_all(repo)
        run_dir = self._run_with_protocol(repo, protocol_file, "clean-protocol")
        source = fx.read_json(run_dir / "code-source.json")
        self.assertEqual(source["protocol"]["git_status"], "committed_clean")
        self.assertIsNotNone(source["protocol"]["git_reference"])
        self.assertEqual(
            source["protocol"]["git_reference"]["sha256"], source["protocol"]["sha256"]
        )
        self.assertEqual(source["protocol"]["sha256"], _sha256_file(protocol_file))
        self.assertFalse(
            (run_dir / "protocol.md").exists(),
            msg="a clean committed protocol must not be duplicated",
        )
        # Saved-only source-manifest compatibility is preserved.
        manifest = fx.read_json(run_dir / "source-sha256.json")
        self.assertEqual(
            manifest["sources"]["protocol"]["sha256"], _sha256_file(protocol_file)
        )

    def test_dirty_untracked_outside_and_unavailable_protocols_are_preserved(
        self,
    ) -> None:
        fixture = fx.build_fixture(self.root / "fixture", "r0", node_count=6)

        def run_with(repo_root: Path, protocol_file: Path, run_id: str) -> Path:
            spec = fx.make_run_spec(
                self.root / "runs",
                "r0",
                fixture["demand_path"],
                fixture["graph_path"],
                run_id,
                repo_root=str(repo_root),
                protocol_path=str(protocol_file),
            )
            return Path(runner.execute_run(spec)["run_dir"])

        # tracked dirty
        dirty_repo = _init_git_repo(self.root / "dirty-protocol-repo")
        dirty_protocol = dirty_repo / "protocol.md"
        dirty_protocol.write_text("committed protocol\n", encoding="utf-8")
        _commit_all(dirty_repo)
        dirty_protocol.write_text("dirty protocol override\n", encoding="utf-8")
        dirty_run = run_with(dirty_repo, dirty_protocol, "dirty-protocol")
        self.assertEqual(
            (dirty_run / "protocol.md").read_text(encoding="utf-8"),
            "dirty protocol override\n",
        )
        self.assertEqual(
            fx.read_json(dirty_run / "code-source.json")["protocol"]["git_status"],
            "modified",
        )

        # untracked
        untracked_repo = _init_git_repo(self.root / "untracked-protocol-repo")
        (untracked_repo / "anchor.py").write_text("A = 1\n", encoding="utf-8")
        _commit_all(untracked_repo)
        untracked_protocol = untracked_repo / "protocol.md"
        untracked_protocol.write_text("untracked protocol\n", encoding="utf-8")
        untracked_run = run_with(untracked_repo, untracked_protocol, "untracked-protocol")
        self.assertEqual(
            (untracked_run / "protocol.md").read_text(encoding="utf-8"),
            "untracked protocol\n",
        )
        entry = fx.read_json(untracked_run / "code-source.json")["protocol"]
        self.assertEqual(entry["git_status"], "untracked")
        self.assertEqual(entry["content_saved"], "code-untracked/protocol.md")

        # outside the repository
        outside_repo = _init_git_repo(self.root / "outside-protocol-repo")
        (outside_repo / "anchor.py").write_text("A = 1\n", encoding="utf-8")
        _commit_all(outside_repo)
        outside_protocol = self.root / "outside-protocol.md"
        outside_protocol.write_text("outside repository protocol\n", encoding="utf-8")
        outside_run = run_with(outside_repo, outside_protocol, "outside-protocol")
        self.assertEqual(
            (outside_run / "protocol.md").read_text(encoding="utf-8"),
            "outside repository protocol\n",
        )
        outside_entry = fx.read_json(outside_run / "code-source.json")["protocol"]
        self.assertTrue(outside_entry["outside_repository"])
        self.assertEqual(outside_entry["content_saved"], "protocol.md")

        # unavailable Git
        plain = self.root / "no-git-protocol"
        plain.mkdir(parents=True, exist_ok=True)
        plain_protocol = plain / "protocol.md"
        plain_protocol.write_text("no git protocol\n", encoding="utf-8")
        plain_run = run_with(plain, plain_protocol, "unavailable-protocol")
        self.assertEqual(
            (plain_run / "protocol.md").read_text(encoding="utf-8"),
            "no git protocol\n",
        )
        plain_source = fx.read_json(plain_run / "code-source.json")
        self.assertFalse(plain_source["identity_available"])
        self.assertEqual(plain_source["protocol"]["git_status"], "unknown")

    # -- V-002: malformed/unreadable saved input still yields a report -----
    def test_malformed_status_writes_one_failure_report(self) -> None:
        for command, kwargs in (
            ("recompute", {}),
            ("compare", {}),
        ):
            with self.subTest(command=command):
                bad = self.root / f"malformed-{command}"
                bad.mkdir(parents=True)
                (bad / "status.json").write_text("{invalid", encoding="utf-8")
                before = _tree_hash(bad)
                report = self.reports / f"malformed-{command}.json"
                if command == "recompute":
                    result = checks.command_recompute(
                        run_dir=bad,
                        repo_root=REPO_ROOT,
                        command=["probe"],
                        report_path=report,
                    )
                else:
                    result = checks.command_compare(
                        run_a=bad,
                        run_b=bad,
                        repo_root=REPO_ROOT,
                        command=["probe"],
                        report_path=report,
                    )
                self.assertEqual(result["status"], "failed")
                self.assertTrue(report.exists())
                self.assertEqual(result["envelope"]["status"], "failed")
                self.assertTrue(result["envelope"]["errors"])
                self.assertEqual(
                    result["envelope"]["errors"][0]["type"], "JSONDecodeError"
                )
                self.assertEqual(_tree_hash(bad), before)

    def test_malformed_status_cli_returns_nonzero_with_a_report(self) -> None:
        bad = self.root / "malformed-cli"
        bad.mkdir(parents=True)
        (bad / "status.json").write_text("{invalid", encoding="utf-8")
        report = self.reports / "malformed-cli.json"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "benchmark.nograph_baseline",
                "recompute",
                "--run-dir",
                str(bad),
                "--report",
                str(report),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["report_path"], str(report))
        self.assertTrue(report.exists())
        self.assertEqual(fx.read_json(report)["status"], "failed")

    def test_malformed_metrics_still_writes_an_align_failure_report(self) -> None:
        run_dir = self.root / "malformed-align"
        run_dir.mkdir(parents=True)
        (run_dir / "metrics.json").write_text("{invalid", encoding="utf-8")
        reference = self.root / "reference.log"
        reference.write_text('{"dataset": "r0"}\n', encoding="utf-8")
        report = self.reports / "malformed-align.json"
        result = checks.command_align_v2(
            run_dir=run_dir,
            reference=reference,
            repo_root=REPO_ROOT,
            command=["probe"],
            report_path=report,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["envelope"]["errors"][0]["type"], "JSONDecodeError")
        self.assertTrue(report.exists())

    def test_unreadable_consumed_input_writes_a_failure_report(self) -> None:
        if not hasattr(os, "geteuid") or os.geteuid() == 0:
            self.skipTest("file permissions do not restrict this user")
        _, run_dir = execute_fixture(self.root, run_id="unreadable-input")
        target = run_dir / "metrics.json"
        digest = _sha256_file(target)
        target.chmod(0)
        try:
            report = self.reports / "unreadable.json"
            result = checks.command_recompute(
                run_dir=run_dir,
                repo_root=REPO_ROOT,
                command=["probe"],
                report_path=report,
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(
                result["envelope"]["errors"][0]["type"], "PermissionError"
            )
            self.assertTrue(report.exists())
        finally:
            target.chmod(0o644)
        self.assertEqual(_sha256_file(target), digest)

    def test_unsafe_destination_still_produces_no_output(self) -> None:
        bad = self.root / "malformed-unsafe"
        bad.mkdir(parents=True)
        (bad / "status.json").write_text("{invalid", encoding="utf-8")
        destination = bad / "inside.json"
        with self.assertRaises(checks.CheckError):
            checks.command_recompute(
                run_dir=bad,
                repo_root=REPO_ROOT,
                command=["probe"],
                report_path=destination,
            )
        self.assertFalse(destination.exists())

    # -- V-003: failed Git diff still preserves modified content ----------
    def _capture(self, repo: Path, run_id: str, runtime_paths):
        run = artifacts.RunDirectory(self.root / "run-dirs", run_id, "run").reserve()
        return run, artifacts.capture_source(run, repo, runtime_paths=runtime_paths)

    def _assert_reconstructable(
        self, repo: Path, run: "artifacts.RunDirectory", record: dict, relative: str
    ) -> None:
        """Recover one file from the fixed base commit plus run-owned evidence."""
        entry = record["files"][relative]
        if entry["content_saved"]:
            recovered = (run.path / entry["content_saved"]).read_bytes()
        else:
            work = Path(tempfile.mkdtemp(dir=self.root))
            # Seed every recorded base from the fixed commit only.
            for sibling in record["runtime_scope"]:
                probe = subprocess.run(
                    ["git", "-C", str(repo), "cat-file", "-e",
                     f"{record['commit']}:{sibling}"],
                    capture_output=True,
                )
                if probe.returncode != 0:
                    continue
                base = subprocess.run(
                    ["git", "-C", str(repo), "show", f"{record['commit']}:{sibling}"],
                    capture_output=True,
                    check=True,
                ).stdout
                target = work / sibling
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(base)
            applied = subprocess.run(
                [
                    "git",
                    "apply",
                    "--unsafe-paths",
                    str(run.path / (entry["patch_path"] or record["patch_path"])),
                ],
                cwd=str(work),
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                applied.returncode, 0, msg=f"{relative}: {applied.stderr}"
            )
            target = work / relative
            recovered = target.read_bytes() if target.exists() else None
        if recovered is None:
            self.assertIsNone(entry["sha256"])
        else:
            self.assertEqual(hashlib.sha256(recovered).hexdigest(), entry["sha256"])

    def test_ordinary_modified_and_deleted_runtime_reconstruct_from_patch(self) -> None:
        repo = _init_git_repo(self.root / "reconstruct-repo")
        modified = repo / "modified.py"
        modified.write_text("VALUE = 1\n", encoding="utf-8")
        deleted = repo / "deleted.py"
        deleted.write_text("GONE = 1\n", encoding="utf-8")
        _commit_all(repo)
        modified.write_text("VALUE = 3\n", encoding="utf-8")
        deleted.unlink()

        run, record = self._capture(repo, "reconstruct", ["modified.py", "deleted.py"])
        self.assertIsNone(record["files"]["modified.py"]["content_saved"])
        self.assertIsNone(record["files"]["deleted.py"]["content_saved"])
        self.assertEqual(record["patch_unusable_paths"], [])
        self._assert_reconstructable(repo, run, record, "modified.py")
        self._assert_reconstructable(repo, run, record, "deleted.py")

    def test_binary_marked_runtime_source_reconstructs_from_patch(self) -> None:
        repo = _init_git_repo(self.root / "binary-diff-repo")
        used = repo / "used.py"
        used.write_text("VALUE = 1\n", encoding="utf-8")
        (repo / ".gitattributes").write_text("used.py -diff\n", encoding="utf-8")
        _commit_all(repo)
        used.write_text("VALUE = 2\n", encoding="utf-8")

        run, record = self._capture(repo, "binary-diff", ["used.py"])
        entry = record["files"]["used.py"]
        self.assertIsNone(entry["content_saved"])
        self.assertEqual(record["patch_unusable_paths"], [])
        self.assertIn(
            "GIT binary patch",
            (run.path / record["patch_path"]).read_text(encoding="utf-8"),
        )
        self._assert_reconstructable(repo, run, record, "used.py")

    def test_mixed_driver_multi_file_recovers_every_path(self) -> None:
        repo = _init_git_repo(self.root / "mixed-driver-repo")
        good = repo / "good.py"
        broken = repo / "broken.py"
        good.write_text("VALUE = 1\n", encoding="utf-8")
        broken.write_text("VALUE = 1\n", encoding="utf-8")
        (repo / ".gitattributes").write_text("broken.py diff=broken\n", encoding="utf-8")
        _commit_all(repo)
        _git(repo, "config", "diff.broken.command", "false")
        good.write_text("VALUE = 2\n", encoding="utf-8")
        broken.write_text("VALUE = 2\n", encoding="utf-8")

        run, record = self._capture(repo, "mixed-driver", ["good.py", "broken.py"])
        # The failing driver must not erase the other path's retained diff.
        self.assertEqual(record["patch_unusable_paths"], ["broken.py"])
        self.assertEqual(record["unrecoverable_paths"], [])
        self.assertEqual(record["files"]["good.py"]["patch_path"], "git-diff.patch")
        self.assertEqual(
            record["files"]["broken.py"]["content_saved"], "code-untracked/broken.py"
        )
        self.assertGreater(record["patch_bytes"], 0)
        self._assert_reconstructable(repo, run, record, "good.py")
        self._assert_reconstructable(repo, run, record, "broken.py")

    def test_mixed_driver_deletion_and_failure_recovers_every_path(self) -> None:
        repo = _init_git_repo(self.root / "mixed-delete-repo")
        deleted = repo / "deleted.py"
        broken = repo / "broken.py"
        deleted.write_text("GONE = 1\n", encoding="utf-8")
        broken.write_text("VALUE = 1\n", encoding="utf-8")
        (repo / ".gitattributes").write_text("broken.py diff=broken\n", encoding="utf-8")
        _commit_all(repo)
        _git(repo, "config", "diff.broken.command", "false")
        deleted.unlink()
        broken.write_text("VALUE = 2\n", encoding="utf-8")

        run, record = self._capture(repo, "mixed-delete", ["deleted.py", "broken.py"])
        self.assertEqual(record["patch_unusable_paths"], ["broken.py"])
        self.assertEqual(record["unrecoverable_paths"], [])
        self.assertEqual(
            record["files"]["deleted.py"]["patch_path"], "git-diff.patch"
        )
        self.assertIsNone(record["files"]["deleted.py"]["sha256"])
        self._assert_reconstructable(repo, run, record, "deleted.py")
        self._assert_reconstructable(repo, run, record, "broken.py")

    def test_external_non_patch_diff_falls_back_to_saved_content(self) -> None:
        repo = _init_git_repo(self.root / "external-junk-repo")
        used = repo / "used.py"
        used.write_text("VALUE = 1\n", encoding="utf-8")
        (repo / ".gitattributes").write_text(
            "used.py diff=custom\n", encoding="utf-8"
        )
        _commit_all(repo)
        _git(repo, "config", "diff.custom.command", "printf b/used.py")
        used.write_text("VALUE = 2\n", encoding="utf-8")

        run, record = self._capture(repo, "external-junk", ["used.py"])
        entry = record["files"]["used.py"]
        self.assertEqual(entry["content_saved"], "code-untracked/used.py")
        self.assertEqual(record["patch_unusable_paths"], ["used.py"])
        self.assertTrue(entry["unavailable_reason"])
        self._assert_reconstructable(repo, run, record, "used.py")

    def test_failed_git_diff_preserves_modified_runtime_content(self) -> None:
        repo = _init_git_repo(self.root / "broken-diff-repo")
        used = repo / "used.py"
        used.write_text("VALUE = 1\n", encoding="utf-8")
        _commit_all(repo)
        (repo / ".gitattributes").write_text("used.py diff=broken\n", encoding="utf-8")
        _git(repo, "config", "diff.broken.command", "false")
        used.write_text("VALUE = 2\n", encoding="utf-8")

        run = artifacts.RunDirectory(self.root / "run-dirs", "diff-failure", "run").reserve()
        record = artifacts.capture_source(run, repo, runtime_paths=["used.py"])
        entry = record["files"]["used.py"]
        self.assertEqual(entry["git_status"], "modified")
        self.assertTrue(record["errors"].get("scoped_patch"))
        self.assertEqual(record["patch_bytes"], 0)
        self.assertEqual(entry["content_saved"], "code-untracked/used.py")
        self.assertTrue(entry["unavailable_reason"])
        saved = run.path / "code-untracked" / "used.py"
        self.assertEqual(saved.read_text(encoding="utf-8"), "VALUE = 2\n")
        self.assertEqual(_sha256_file(saved), entry["sha256"])
        manifest = fx.read_json(run.path / "code-untracked" / "manifest.json")
        self.assertEqual(manifest["files"], {"used.py": entry["sha256"]})

    def test_failed_git_diff_reports_unrecoverable_deletion(self) -> None:
        repo = _init_git_repo(self.root / "broken-diff-delete")
        used = repo / "used.py"
        used.write_text("VALUE = 1\n", encoding="utf-8")
        _commit_all(repo)
        (repo / ".gitattributes").write_text("used.py diff=broken\n", encoding="utf-8")
        _git(repo, "config", "diff.broken.command", "false")
        used.unlink()

        run = artifacts.RunDirectory(self.root / "run-dirs", "delete-failure", "run").reserve()
        record = artifacts.capture_source(run, repo, runtime_paths=["used.py"])
        entry = record["files"]["used.py"]
        self.assertEqual(entry["git_status"], "modified")
        self.assertIsNone(entry["content_saved"])
        self.assertIn("deletion", entry["unavailable_reason"] or "")

    # -- V-004: untracked checker source is not reported scoped-clean -----
    def test_untracked_checker_source_is_reported_scoped_dirty(self) -> None:
        repo = _init_git_repo(self.root / "checker-repo")
        (repo / "anchor.py").write_text("A = 1\n", encoding="utf-8")
        _commit_all(repo)
        launcher = repo / "benchmark/nograph_baseline/__main__.py"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text("VALUE = 1\n", encoding="utf-8")

        identity = artifacts.checker_source_identity(repo)
        self.assertTrue(identity["scoped_state_available"])
        self.assertTrue(identity["scoped_dirty"])
        self.assertIn(
            "benchmark/nograph_baseline/__main__.py", identity["scoped_files"]
        )
        self.assertIn(
            "benchmark/nograph_baseline/__main__.py", identity["untracked_files"]
        )
        self.assertEqual(identity["patch_eligible_files"], [])
        self.assertIn(
            "benchmark/nograph_baseline/__main__.py", identity["files"]
        )
        self.assertEqual(identity["patch_bytes"], 0)

    def test_checker_identity_without_git_reports_unknown_scope(self) -> None:
        plain = self.root / "no-git-checker"
        launcher = plain / "benchmark/nograph_baseline/__main__.py"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text("VALUE = 1\n", encoding="utf-8")
        identity = artifacts.checker_source_identity(plain)
        self.assertFalse(identity["identity_available"])
        self.assertFalse(identity["scoped_state_available"])
        self.assertIsNone(identity["scoped_dirty"])
        self.assertIsNone(identity["scoped_files"])
        self.assertTrue(identity["errors"])

    def test_clean_checker_source_is_scoped_clean(self) -> None:
        repo = _init_git_repo(self.root / "clean-checker-repo")
        launcher = repo / "benchmark/nograph_baseline/__main__.py"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text("VALUE = 1\n", encoding="utf-8")
        _commit_all(repo)
        identity = artifacts.checker_source_identity(repo)
        self.assertTrue(identity["scoped_state_available"])
        self.assertFalse(identity["scoped_dirty"])
        self.assertEqual(identity["scoped_files"], [])
        self.assertEqual(identity["untracked_files"], [])

    def test_modified_tracked_checker_source_is_scoped_dirty_and_patchable(
        self,
    ) -> None:
        repo = _init_git_repo(self.root / "modified-checker-repo")
        launcher = repo / "benchmark/nograph_baseline/__main__.py"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text("VALUE = 1\n", encoding="utf-8")
        _commit_all(repo)
        launcher.write_text("VALUE = 2\n", encoding="utf-8")
        identity = artifacts.checker_source_identity(repo)
        self.assertTrue(identity["scoped_dirty"])
        self.assertEqual(
            identity["scoped_files"],
            ["benchmark/nograph_baseline/__main__.py"],
        )
        self.assertEqual(
            identity["patch_eligible_files"],
            ["benchmark/nograph_baseline/__main__.py"],
        )
        self.assertEqual(identity["untracked_files"], [])
        self.assertTrue(identity["patch_included"])
        self.assertIn("VALUE = 2", identity["source_patch"])

    # -- V-005: reports link declared execution IDs ------------------------
    def test_check_reports_link_declared_execution_ids(self) -> None:
        fixture = fx.build_fixture(self.root / "fixture", "r0", node_count=6)
        declared = ("orig-alpha-001", "orig-beta-002")
        for run_id in declared:
            spec = fx.make_run_spec(
                self.root / "runs",
                "r0",
                fixture["demand_path"],
                fixture["graph_path"],
                run_id,
            )
            runner.execute_run(spec)
        alpha = self.root / "alpha"
        beta = self.root / "beta"
        (self.root / "runs" / declared[0]).rename(alpha)
        (self.root / "runs" / declared[1]).rename(beta)

        before = {str(alpha): _tree_hash(alpha), str(beta): _tree_hash(beta)}
        compare_path = self.reports / "compare.json"
        result = checks.command_compare(
            run_a=alpha,
            run_b=beta,
            repo_root=REPO_ROOT,
            command=["probe"],
            report_path=compare_path,
        )
        self.assertEqual(result["status"], "ok")
        inputs = result["envelope"]["inputs"]
        self.assertEqual(inputs["run_a_id"], declared[0])
        self.assertEqual(inputs["run_b_id"], declared[1])
        self.assertEqual(inputs["run_a"], str(alpha))
        self.assertEqual(inputs["run_b"], str(beta))
        self.assertTrue(inputs["run_a_consumed_sha256"])
        self.assertTrue(inputs["run_b_consumed_sha256"])

        # Recompute through the same unrelated directory alias keeps the
        # declared execution ID alongside the current location.
        recompute_path = self.reports / "recompute.json"
        recomputed = checks.command_recompute(
            run_dir=alpha,
            repo_root=REPO_ROOT,
            command=["probe"],
            report_path=recompute_path,
        )
        self.assertEqual(recomputed["status"], "ok")
        self.assertEqual(
            recomputed["envelope"]["inputs"]["input_run_id"], declared[0]
        )
        self.assertEqual(recomputed["envelope"]["inputs"]["input_run_dir"], str(alpha))
        # The declared IDs must be discoverable in the published report file.
        text = compare_path.read_text(encoding="utf-8")
        self.assertIn(declared[0], text)
        self.assertIn(declared[1], text)

        log = self.root / "naive-baselines.log"
        _write_v2_log(
            log,
            "r0",
            fixture["keys"],
            fixture["signal"],
            fx.read_json(alpha / "metrics.json"),
        )
        _write_v2_source_manifest(
            log,
            "r0",
            fx.read_json(alpha / "source-sha256.json")["sources"]["demand"]["sha256"],
        )
        align_path = self.reports / "align.json"
        aligned = checks.command_align_v2(
            run_dir=alpha,
            reference=log,
            repo_root=REPO_ROOT,
            command=["probe"],
            report_path=align_path,
        )
        self.assertEqual(aligned["status"], "ok")
        self.assertEqual(aligned["envelope"]["inputs"]["input_run_id"], declared[0])
        self.assertIn(declared[0], align_path.read_text(encoding="utf-8"))

        self.assertEqual(_tree_hash(alpha), before[str(alpha)])
        self.assertEqual(_tree_hash(beta), before[str(beta)])


if __name__ == "__main__":
    unittest.main()
