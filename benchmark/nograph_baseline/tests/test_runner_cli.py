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
from pathlib import Path

import numpy as np

import nb_fixtures as fx
from benchmark.nograph_baseline import artifacts, checks, cli, protocol, runner

REPO_ROOT = protocol.REPO_ROOT


def _tree_hash(root: Path) -> dict:
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return result


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
            "protocol.md",
            "config.json",
            "command.json",
            "provenance.json",
            "git-commit.txt",
            "git-status.txt",
            "git-diff.patch",
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
        for method in protocol.NAIVE_METHODS + (protocol.MODEL_NAME,):
            for split in ("validation", "test"):
                self.assertTrue(
                    (self.run_dir / "predictions" / method / f"{split}.npy").exists()
                )
        for name in protocol.LAMBDA_CANDIDATES:
            label = f"{name:g}"
            self.assertTrue(
                (self.run_dir / "candidates" / label / "parameters.npz").exists()
            )
            self.assertTrue(
                (self.run_dir / "candidates" / label / "validation.npy").exists()
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
        environment = fx.read_json(self.run_dir / "environment.json")
        self.assertEqual(environment["packages"]["numpy"], np.__version__)
        self.assertTrue(environment["numpy_blas_config"])
        self.assertIn("numpy", environment["pip_freeze"])
        code_manifest = fx.read_json(self.run_dir / "code-untracked" / "manifest.json")
        self.assertFalse(code_manifest["tracked_by_git"])
        self.assertTrue(code_manifest["files"])

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
        result = checks.command_recompute(
            run_dir=run_dir,
            run_id="recompute-001",
            runs_root=self.root / "runs",
            repo_root=REPO_ROOT,
            command=["python", "-m", "benchmark.nograph_baseline", "recompute"],
        )
        self.assertEqual(result["status"], "ok")
        report = result["report"]
        self.assertFalse(report["source_data_read"])
        self.assertFalse(report["model_refit"])
        for comparison in report["comparisons"].values():
            self.assertEqual(comparison["status"], "ok")
            self.assertEqual(comparison["max_normalized_difference"], 0.0)
        self.assertEqual(before, _tree_hash(run_dir))
        check_dir = Path(result["run_dir"])
        provenance = fx.read_json(check_dir / "provenance.json")
        self.assertIn("input_artifacts", provenance["inputs"])

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
        result = checks.command_compare(
            run_a=run_a,
            run_b=run_b,
            run_id="compare-001",
            runs_root=self.root / "runs",
            repo_root=REPO_ROOT,
            command=["python", "-m", "benchmark.nograph_baseline", "compare"],
        )
        self.assertEqual(result["status"], "ok")
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
        result = checks.command_align_v2(
            run_dir=run_dir,
            reference=log,
            run_id="align-001",
            runs_root=self.root / "runs",
            repo_root=REPO_ROOT,
            command=["python", "-m", "benchmark.nograph_baseline", "align-v2"],
        )
        self.assertEqual(result["status"], "ok")
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
            run_id="align-002",
            runs_root=self.root / "runs",
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
        runs_root = self.root / "chk" / "runs"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "benchmark.nograph_baseline",
                "recompute",
                "--run-dir",
                str(run_dir),
                "--run-id",
                "chk-recompute",
                "--runs-root",
                str(runs_root),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        command = fx.read_json(runs_root / "chk-recompute" / "command.json")
        self.assertEqual(command["argv"][0], sys.executable)
        self.assertEqual(
            command["argv"][1:4],
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
        for flag in ("--data-name", "--seed", "--run-id", "--ridge-backend"):
            self.assertIn(flag, run_help)


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

    def _compare(self, a: Path, b: Path, run_id: str) -> dict:
        return checks.command_compare(
            run_a=a,
            run_b=b,
            run_id=run_id,
            runs_root=self.checks_root,
            repo_root=REPO_ROOT,
            command=["probe", "compare"],
        )

    def _recompute(self, run_dir: Path, run_id: str) -> dict:
        return checks.command_recompute(
            run_dir=run_dir,
            run_id=run_id,
            runs_root=self.checks_root,
            repo_root=REPO_ROOT,
            command=["probe", "recompute"],
        )

    def _align(self, run_dir: Path, reference: Path, run_id: str) -> dict:
        return checks.command_align_v2(
            run_dir=run_dir,
            reference=reference,
            run_id=run_id,
            runs_root=self.checks_root,
            repo_root=REPO_ROOT,
            command=["probe", "align-v2"],
        )

    def _mutate_json(self, run_dir: Path, relative: str, mutator) -> None:
        payload = fx.read_json(run_dir / relative)
        mutator(payload)
        (run_dir / relative).write_text(json.dumps(payload), encoding="utf-8")

    def test_compare_valid_pair_still_ok(self) -> None:
        result = self._compare(self.run_dir, self.run_dir, "adv-compare-valid")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["report"]["identity_evidence_complete"])
        self.assertTrue(all(result["report"]["identity_checks"].values()))
        for value in result["report"]["identity_checks"].values():
            self.assertIsInstance(value, bool)

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

    def _recompute(self, run_dir: Path, run_id: str) -> dict:
        return checks.command_recompute(
            run_dir=run_dir,
            run_id=run_id,
            runs_root=self.checks_root,
            repo_root=REPO_ROOT,
            command=["probe", "recompute"],
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
        report = result["report"]
        self.assertGreater(report["comparisons"]["test"]["null_fields"], 0)
        self.assertEqual(report["stored_semantic_problems"], [])
        self.assertEqual(report["recomputed_semantic_problems"], [])
        self.assertEqual(report["gain_semantic_problems"], [])

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


if __name__ == "__main__":
    unittest.main()
