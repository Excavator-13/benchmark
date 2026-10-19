"""Complete saved evidence, provenance scope, costs and lifecycle states.

Covers tasks 6.1, 6.2, 6.7 and 6.8.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from benchmark.graph_value_skeleton import artifacts
from benchmark.graph_value_skeleton import data as gvs_data
from benchmark.graph_value_skeleton import graph as gvs_graph
from benchmark.graph_value_skeleton import model as gvs_model
from benchmark.graph_value_skeleton import protocol
from benchmark.graph_value_skeleton import runner
from benchmark.graph_value_skeleton import training
from benchmark.graph_value_skeleton.tests import fixtures
from benchmark.nograph_baseline import protocol as p01

REQUIRED_FILES = (
    "config.json",
    "command.json",
    "provenance.json",
    "source.json",
    "environment.json",
    "environment.txt",
    "measurements.json",
    "status.json",
    "nodes.parquet",
    "windows.json",
    "masks.npz",
    "audit.json",
    "graph-audit.json",
    "graph/edges.npy",
    "gold/validation.npy",
    "gold/test.npy",
    "models/selected.npz",
    "selection.json",
    "training-history.json",
    "metrics.json",
    "summary.md",
    "artifacts-sha256.json",
    "events.jsonl",
)


class ArtifactCompletenessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(tempfile.mkdtemp(prefix="gvs-artifacts-"))
        cls.fixture = fixtures.build_fixture(cls.root, "r0")
        cls.config = fixtures.make_config(
            cls.root, cls.fixture, method="graph", run_id="graph-s0"
        )
        cls.result = runner.execute_run(cls.config)
        cls.run_dir = Path(cls.result["run_dir"])
        cls.dataset, cls.graph = fixtures.load_fixture(cls.fixture)

    def test_required_artifacts_exist(self) -> None:
        for relative in REQUIRED_FILES:
            with self.subTest(relative=relative):
                self.assertTrue((self.run_dir / relative).is_file(), relative)
        for split in ("validation", "test"):
            for method in (*protocol.NAIVE_METHODS, "graph"):
                self.assertTrue(
                    (self.run_dir / "predictions" / method / f"{split}.npy").is_file()
                )
        status = fixtures.read_json(self.run_dir / "status.json")
        self.assertEqual(status["state"], "success")
        self.assertEqual(status["method"], "graph")
        manifest = fixtures.read_json(self.run_dir / "artifacts-sha256.json")
        for relative, digest in manifest["files"].items():
            self.assertEqual(digest, artifacts.sha256_file(self.run_dir / relative))

    def test_config_and_provenance(self) -> None:
        config = fixtures.read_json(self.run_dir / "config.json")
        self.assertEqual(config["protocol_version"], protocol.SCIENTIFIC_PROTOCOL_VERSION)
        self.assertEqual(config["skeleton_version"], protocol.SKELETON_VERSION)
        self.assertEqual(config["records_policy"], protocol.RECORDS_POLICY)
        self.assertEqual(config["task"], protocol.TASK_ID)
        self.assertEqual(config["change"], protocol.CHANGE_NAME)
        spec = config["spec"]
        for key in ("data_name", "method", "model_seed", "shuffle_seed", "purpose", "run_id"):
            self.assertIn(key, spec)
        self.assertEqual(spec["method"], "graph")
        self.assertEqual(spec["purpose"], "development")
        self.assertEqual(
            config["computational"], self.config.computational_identity()
        )
        provenance = fixtures.read_json(self.run_dir / "provenance.json")
        self.assertEqual(provenance["task"], protocol.TASK_ID)
        self.assertEqual(provenance["change"], protocol.CHANGE_NAME)
        self.assertEqual(provenance["design_decision"], protocol.DESIGN_DECISION)
        self.assertEqual(provenance["purpose"], "development")
        self.assertEqual(
            provenance["scientific_protocol"]["version"], "P1-count-L6-H3-v3"
        )
        self.assertIsNotNone(provenance["scientific_protocol"]["sha256"])
        self.assertEqual(provenance["records_policy"]["name"], "P01-records-v2")
        for label, record in provenance["records_policy"]["sources"].items():
            self.assertTrue(record["available"], label)
            self.assertIsNotNone(record["sha256"], label)
        self.assertEqual(
            provenance["demand"]["node_keys_sha256"],
            gvs_graph.node_keys_sha256(self.dataset.key_array),
        )
        self.assertEqual(provenance["demand"]["source_kind"], "fixture")
        self.assertEqual(
            provenance["graph"]["edges_sha256"],
            gvs_graph.edge_set_sha256(self.graph.edges),
        )
        self.assertEqual(
            provenance["graph_used"]["message_edges_sha256"],
            gvs_graph.edge_set_sha256(self.graph.edges),
        )
        self.assertEqual(provenance["parameter_counts_measured"]["total"], 3459)
        self.assertFalse(provenance["scientific_acceptance"])
        self.assertTrue(
            provenance["implementation_readiness_does_not_establish_predictive_benefit"]
        )
        command = fixtures.read_json(self.run_dir / "command.json")
        self.assertEqual(Path(command["python"]), Path(__import__("sys").executable))
        self.assertEqual(command["module"], "benchmark.graph_value_skeleton")

    def test_source_capture_scope(self) -> None:
        source = fixtures.read_json(self.run_dir / "source.json")
        self.assertTrue(source["identity_available"])
        self.assertIsNotNone(source["commit"])
        self.assertTrue(source["runtime_scope"])
        for relative in source["runtime_scope"]:
            self.assertTrue(relative.startswith("benchmark/"), relative)
            self.assertNotIn("/tests/", f"/{relative}")
            self.assertNotIn("research/", relative)
        for mandatory in (
            "benchmark/graph_value_skeleton/runner.py",
            "benchmark/graph_value_skeleton/model.py",
            "benchmark/nograph_baseline/data.py",
            "benchmark/nograph_baseline/protocol.py",
        ):
            self.assertIn(mandatory, source["runtime_scope"])
        # Uncommitted execution content is retained and hashes agree.
        for relative, entry in source["files"].items():
            if entry["content_saved"]:
                saved = self.run_dir / entry["content_saved"]
                self.assertTrue(saved.is_file(), relative)
                self.assertEqual(artifacts.sha256_file(saved), entry["sha256"])
        self.assertEqual(source["unrecoverable_paths"], [])
        self.assertTrue((self.run_dir / "git-diff.patch").is_file())
        self.assertTrue((self.run_dir / "git-commit.txt").is_file())

    def test_environment_records_pinned_runtime(self) -> None:
        environment = fixtures.read_json(self.run_dir / "environment.json")
        self.assertEqual(environment["python_version_info"][:3], [3, 11, 17])
        self.assertEqual(environment["packages"]["numpy"], "1.26.4")
        self.assertEqual(environment["packages"]["pandas"], "2.2.3")
        self.assertEqual(environment["packages"]["pyarrow"], "17.0.0")
        self.assertEqual(environment["packages"]["torch"], __import__('torch').__version__)
        self.assertIn(environment["packages"]["torch"], ("2.14.1", "2.14.1+cpu"))
        self.assertFalse(environment["gpu_available"])
        self.assertEqual(environment["torch"]["intra_op_threads"], 1)
        for variable in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        ):
            self.assertEqual(environment["thread_environment"][variable], "1", variable)
        for name, record in environment["graph_extensions"].items():
            self.assertFalse(record["used_by_this_entry"], name)
            self.assertFalse(record["imported_in_this_process"], name)

    def test_dataset_graph_and_mask_artifacts(self) -> None:
        import pandas as pd

        nodes = pd.read_parquet(self.run_dir / "nodes.parquet")
        self.assertEqual(len(nodes), self.dataset.node_count)
        self.assertEqual(nodes["node_index"].tolist(), list(range(len(nodes))))
        windows = fixtures.read_json(self.run_dir / "windows.json")
        self.assertEqual(windows, protocol.window_metadata())
        self.assertEqual(len(windows["windows"]), 28)
        self.assertEqual(
            [row["split"] for row in windows["windows"]].count("train"), 19
        )
        self.assertEqual(
            windows["splits"]["validation"], list(protocol.VALIDATION_STARTS)
        )
        audit = fixtures.read_json(self.run_dir / "audit.json")
        self.assertEqual(audit["masks"]["scope"], "train27 (2021-01..2023-03)")
        self.assertFalse(audit["masks"]["recomputed_from_shuffled_adjacency"])
        for name, digest in audit["masks"]["array_sha256"].items():
            with np.load(self.run_dir / "masks.npz", allow_pickle=False) as handle:
                self.assertEqual(
                    gvs_data.array_sha256(np.asarray(handle[name])), digest
                )
        graph_audit = fixtures.read_json(self.run_dir / "graph-audit.json")
        self.assertEqual(graph_audit["direction"], "row_id -> col_id (source -> target); incoming edges are aggregated")
        self.assertFalse(graph_audit["multiplicity"]["weights_edges"])
        self.assertEqual(graph_audit["self_loop_rows"], 0)
        self.assertNotIn("shuffle", graph_audit)
        edges = np.load(self.run_dir / "graph/edges.npy", allow_pickle=False)
        source_edges = np.load(self.run_dir / "graph/source-edges.npy", allow_pickle=False)
        np.testing.assert_array_equal(edges, source_edges)
        np.testing.assert_array_equal(edges, self.graph.edges)

    def test_predictions_gold_and_parameters(self) -> None:
        gold = {
            split: np.load(self.run_dir / "gold" / f"{split}.npy", allow_pickle=False)
            for split in ("validation", "test")
        }
        self.assertEqual(gold["validation"].shape, (1, self.dataset.node_count, 3))
        self.assertEqual(gold["test"].shape, (4, self.dataset.node_count, 3))
        np.testing.assert_array_equal(
            gold["test"], self.dataset.target_windows(protocol.TEST_STARTS)
        )
        for split in ("validation", "test"):
            for method in (*protocol.NAIVE_METHODS, "graph"):
                prediction = np.load(
                    self.run_dir / "predictions" / method / f"{split}.npy",
                    allow_pickle=False,
                )
                self.assertEqual(prediction.shape, gold[split].shape)
                self.assertTrue(np.isfinite(prediction).all())
        with np.load(self.run_dir / "models/selected.npz", allow_pickle=False) as handle:
            parameters = {name: np.asarray(handle[name]) for name in handle.files}
        counts = {
            name: int(parameters[name].reshape(-1)[0])
            for name in (
                "parameter_count_gru",
                "parameter_count_head",
                "parameter_count_graph_only",
                "parameter_count_total",
            )
        }
        self.assertEqual(
            counts,
            {
                "parameter_count_gru": 3360,
                "parameter_count_head": 99,
                "parameter_count_graph_only": 0,
                "parameter_count_total": 3459,
            },
        )
        names = [str(name) for name in parameters["parameter_names"].tolist()]
        self.assertEqual(
            sum(int(parameters[name].size) for name in names), 3459
        )
        # Reload without torch pickles and reproduce the saved validation output.
        training.configure_determinism(0)
        reloaded = gvs_model.build_model(0, torch_seed=False)
        gvs_model.load_state_arrays(reloaded, {name: parameters[name] for name in names})
        aggregation = gvs_model.GraphAggregation.from_edges(
            self.graph.edges, self.dataset.node_count
        )
        import torch

        reproduced = gvs_model.predict_windows(
            reloaded,
            torch.as_tensor(
                self.dataset.input_windows(protocol.VALIDATION_STARTS),
                dtype=torch.float32,
            ),
            aggregation,
        ).numpy()
        saved = np.load(
            self.run_dir / "predictions/graph/validation.npy", allow_pickle=False
        )
        np.testing.assert_allclose(reproduced, saved, rtol=0, atol=0)
        test_inputs = torch.as_tensor(
            self.dataset.input_windows(protocol.TEST_STARTS), dtype=torch.float32
        )
        reproduced_test = gvs_model.predict_windows(
            reloaded, test_inputs, aggregation
        ).numpy()
        saved_test = np.load(
            self.run_dir / "predictions/graph/test.npy", allow_pickle=False
        )
        np.testing.assert_array_equal(reproduced_test, saved_test)
        self_prediction = gvs_model.predict_windows(
            reloaded, test_inputs, None
        ).numpy()
        for window in range(len(protocol.TEST_STARTS)):
            self.assertFalse(
                np.array_equal(saved_test[window], self_prediction[window]),
                f"graph window {window} must apply its incoming messages",
            )

    def test_history_selection_and_metrics(self) -> None:
        history = fixtures.read_json(self.run_dir / "training-history.json")
        self.assertEqual(history["epochs"], 200)
        self.assertEqual(len(history["rows"]), 200)
        best = min(
            history["rows"],
            key=lambda row: (
                row["validation_MSE_original_units_after_update"],
                row["epoch"],
            ),
        )
        self.assertEqual(history["selected_epoch"], best["epoch"])
        selection = fixtures.read_json(self.run_dir / "selection.json")
        self.assertEqual(selection["training"]["selected_epoch"], history["selected_epoch"])
        self.assertEqual(selection["method"], "graph")
        self.assertFalse(selection["test_labels_used_for_selection"])
        self.assertTrue(selection["selection_frozen_before_test_evaluation"])
        self.assertEqual(selection["parameter_counts_measured"]["total"], 3459)
        self.assertEqual(selection["graph_only_trainable_parameters"], [])
        self.assertEqual(
            selection["training_edges"]["edges_sha256"],
            gvs_graph.edge_set_sha256(self.graph.edges),
        )
        self.assertEqual(selection["training_edges"]["windows_verified"], 19)
        self.assertTrue(selection["training_edges"]["matches_message_edges"])
        provenance = fixtures.read_json(self.run_dir / "provenance.json")
        self.assertEqual(
            provenance["graph_used"]["training_edges"]["edges_sha256"],
            gvs_graph.edge_set_sha256(self.graph.edges),
        )
        self.assertIn("NaiveRef", selection["naive_references"])
        metrics = fixtures.read_json(self.run_dir / "metrics.json")
        self.assertEqual(metrics["method"], "graph")
        self.assertEqual(metrics["dataset"], "r0")
        for split in ("validation", "test"):
            self.assertEqual(
                set(metrics["methods"][split]),
                set(protocol.NAIVE_METHODS) | {"graph"},
            )
            self.assertEqual(metrics["methods"][split]["graph"]["dataset"], "r0")
        self.assertIn("graph", metrics["relative_gains"]["test"])
        self.assertEqual(
            metrics["references"]["NaiveRef"], selection["naive_references"]["NaiveRef"]
        )

    def test_measurements_are_measured_and_scoped(self) -> None:
        measurements = fixtures.read_json(self.run_dir / "measurements.json")
        for key in (
            "demand_read",
            "graph_read",
            "shuffle",
            "training",
            "validation",
            "training_total",
            "selected_inference",
            "metrics_output",
            "total",
        ):
            self.assertIn(key, measurements["timings_seconds"])
            self.assertGreaterEqual(measurements["timings_seconds"][key], 0.0)
        self.assertEqual(measurements["device"], "cpu")
        self.assertEqual(measurements["input"]["nodes"], self.dataset.node_count)
        self.assertEqual(measurements["input"]["source_edges"], self.graph.edge_count)
        self.assertEqual(measurements["input"]["epochs"], 200)
        self.assertEqual(measurements["input"]["training_windows"], 19)
        memory = measurements["peak_memory"]
        self.assertIn(memory["method"], ("resource.getrusage(RUSAGE_SELF).ru_maxrss",
                                       "GetProcessMemoryInfo.PeakWorkingSetSize"))
        self.assertEqual(memory["scope"], "worker process lifetime")
        self.assertIn(memory["native_unit"], ("bytes", "KiB"))
        self.assertIsNotNone(memory["bytes"])
        self.assertEqual(measurements["cost_scope"]["fixture"], True)
        self.assertFalse(measurements["cost_scope"]["is_scientific_evidence"])
        self.assertEqual(measurements["threads"]["torch_intra_op"], 1)
        summary = (self.run_dir / "summary.md").read_text(encoding="utf-8")
        self.assertIn("development output; not scientific acceptance evidence", summary)
        self.assertIn("does not", summary)


class PeakMemoryTest(unittest.TestCase):
    def test_native_peak_is_measured(self) -> None:
        memory = artifacts.measure_peak_rss()
        self.assertEqual(memory['status'], 'ok')
        self.assertGreater(memory['bytes'], 0)
        self.assertEqual(memory['scope'], 'worker process lifetime')

    def test_darwin_linux_and_unsupported_unit_conversion(self) -> None:
        from types import SimpleNamespace

        resource = SimpleNamespace(RUSAGE_SELF=0, getrusage=mock.Mock(
            return_value=SimpleNamespace(ru_maxrss=1234)))
        with mock.patch.dict("sys.modules", {"resource": resource}):
            self._check_posix_units()

    def _check_posix_units(self):
        from types import SimpleNamespace

        with mock.patch("platform.system", return_value="Darwin"), mock.patch(
            "resource.getrusage", return_value=SimpleNamespace(ru_maxrss=1234)
        ):
            darwin = artifacts.measure_peak_rss()
        self.assertEqual(darwin["native_value"], 1234)
        self.assertEqual(darwin["native_unit"], "bytes")
        self.assertEqual(darwin["bytes"], 1234)
        self.assertEqual(darwin["scope"], "worker process lifetime")
        with mock.patch("platform.system", return_value="Linux"), mock.patch(
            "resource.getrusage", return_value=SimpleNamespace(ru_maxrss=1234)
        ):
            linux = artifacts.measure_peak_rss()
        self.assertEqual(linux["native_unit"], "KiB")
        self.assertEqual(linux["bytes"], 1234 * 1024)
        with mock.patch("platform.system", return_value="OtherPOSIX"):
            unsupported = artifacts.measure_peak_rss()
        self.assertEqual(unsupported["status"], "unsupported_platform")
        self.assertIsNone(unsupported["bytes"])


class LifecycleTest(unittest.TestCase):
    def test_collision_does_not_overwrite(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-collision-"))
        fixture = fixtures.build_fixture(root, "r0")
        config = fixtures.make_config(root, fixture, method="self", run_id="same")
        runner.execute_run(config)
        status_before = (config.run_dir / "status.json").read_bytes()
        with self.assertRaises(artifacts.RunExistsError):
            runner.execute_run(config)
        self.assertEqual((config.run_dir / "status.json").read_bytes(), status_before)

    def test_failure_keeps_stage_evidence(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-failure-"))
        fixture = fixtures.build_fixture(
            root,
            "r0",
            graph_rows=[(0, 0, 0)],  # a self-loop must fail before training
        )
        config = fixtures.make_config(root, fixture, method="graph", run_id="bad-graph")
        with self.assertRaises(gvs_graph.GraphError):
            runner.execute_run(config)
        status = fixtures.read_json(config.run_dir / "status.json")
        self.assertEqual(status["state"], "failed")
        self.assertEqual(status["stage"], "graph_read")
        failure = fixtures.read_json(config.run_dir / "failure.json")
        self.assertEqual(failure["failure"]["stage"], "graph_read")
        self.assertIn("self-loop", failure["failure"]["message"])
        self.assertTrue((config.run_dir / "config.json").is_file())
        self.assertTrue((config.run_dir / "environment.json").is_file())
        self.assertIn("config.json", failure["completed_artifacts"])
        self.assertFalse((config.run_dir / "metrics.json").exists())
        self.assertTrue(runner.check_unfinished(config.run_dir)["finished"])

    def test_interruption_is_recorded(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-interrupt-"))
        fixture = fixtures.build_fixture(root, "r0")
        config = fixtures.make_config(root, fixture, method="self", run_id="interrupted")

        def interrupted(*args, **kwargs):
            raise KeyboardInterrupt("test interruption")

        with mock.patch.object(training, "train", side_effect=interrupted):
            with self.assertRaises(runner.RunInterrupted):
                runner.execute_run(config)
        status = fixtures.read_json(config.run_dir / "status.json")
        self.assertEqual(status["state"], "interrupted")
        self.assertTrue((config.run_dir / "failure.json").is_file())
        self.assertIn("graph-audit.json", [path.name for path in config.run_dir.iterdir()])

    def test_unfinished_detection(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-unfinished-"))
        run_dir = root / "left-behind"
        run_dir.mkdir()
        (run_dir / "status.json").write_text(
            json.dumps({"state": "running"}), encoding="utf-8"
        )
        result = runner.check_unfinished(run_dir)
        self.assertTrue(result["unfinished"])
        self.assertFalse(result["finished"])
        missing = runner.check_unfinished(root / "does-not-exist")
        self.assertEqual(missing["state"], "missing")
        self.assertFalse(missing["finished"])

    def test_success_does_not_touch_research_runs(self) -> None:
        before = sorted(
            path.name for path in (protocol.REPO_ROOT / "research" / "runs").iterdir()
        )
        root = Path(tempfile.mkdtemp(prefix="gvs-noscope-"))
        fixture = fixtures.build_fixture(root, "r0")
        config = fixtures.make_config(root, fixture, method="self", run_id="no-research")
        runner.execute_run(config)
        after = sorted(
            path.name for path in (protocol.REPO_ROOT / "research" / "runs").iterdir()
        )
        self.assertEqual(before, after)


class SourceCaptureScopeTest(unittest.TestCase):
    """Scoped source capture in a temporary Git repository (task 6.1)."""

    def _git(self, root: Path, *args: str) -> None:
        import subprocess

        subprocess.run(
            ["git", *args], cwd=str(root), check=True, capture_output=True, text=True
        )

    def _temp_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="gvs-git-"))
        self._git(root, "init")
        self._git(root, "config", "core.autocrlf", "false")
        self._git(root, "config", "user.email", "test@example.com")
        self._git(root, "config", "user.name", "Test")
        (root / "benchmark" / "graph_value_skeleton").mkdir(parents=True)
        (root / "research" / "phases" / "P01").mkdir(parents=True)
        (root / "benchmark" / "__init__.py").write_text("", encoding="utf-8", newline="\n")
        (root / "benchmark" / "graph_value_skeleton" / "__init__.py").write_text(
            "VALUE = 1\n", encoding="utf-8", newline="\n"
        )
        (root / "benchmark" / "graph_value_skeleton" / "runner.py").write_text(
            "RUNNER = 1\n", encoding="utf-8", newline="\n"
        )
        (root / "research" / "phases" / "P01" / "protocol.md").write_text(
            "# protocol\n", encoding="utf-8", newline="\n"
        )
        (root / "research" / "state.md").write_text("# state\n", encoding="utf-8", newline="\n")
        (root / "benchmark" / "graph_value_skeleton" / "tests").mkdir()
        (root / "benchmark" / "graph_value_skeleton" / "tests" / "test_x.py").write_text(
            "def test(): pass\n", encoding="utf-8", newline="\n"
        )
        self._git(root, "add", ".")
        self._git(root, "commit", "-m", "initial")
        return root

    def test_capture_scope_excludes_unrelated_records_tests_and_caches(self) -> None:
        root = self._temp_repo()
        # Unrelated research change, an execution-source change and new content.
        (root / "research" / "state.md").write_text("# changed state\n", encoding="utf-8", newline="\n")
        (root / "benchmark" / "graph_value_skeleton" / "runner.py").write_text(
            "RUNNER = 2\n", encoding="utf-8", newline="\n"
        )
        (root / "benchmark" / "graph_value_skeleton" / "new_module.py").write_text(
            "NEW = 1\n", encoding="utf-8", newline="\n"
        )
        (root / "benchmark" / "graph_value_skeleton" / "tests" / "test_y.py").write_text(
            "def test(): pass\n", encoding="utf-8", newline="\n"
        )
        cache = root / "benchmark" / "graph_value_skeleton" / "__pycache__"
        cache.mkdir()
        (cache / "runner.pyc").write_bytes(b"cache")
        runtime = [
            "benchmark/__init__.py",
            "benchmark/graph_value_skeleton/__init__.py",
            "benchmark/graph_value_skeleton/runner.py",
            "benchmark/graph_value_skeleton/new_module.py",
        ]
        run = artifacts.RunDirectory(root / "runs", "source-scope", "run").reserve()
        record = artifacts.capture_source(
            run,
            root,
            protocol_path=root / "research" / "phases" / "P01" / "protocol.md",
            runtime_paths=runtime,
        )
        self.assertEqual(record["runtime_scope"], runtime)
        self.assertEqual(record["commit"] is not None, True)
        self.assertTrue(record["scoped_dirty"])
        modified = record["files"]["benchmark/graph_value_skeleton/runner.py"]
        self.assertEqual(modified["git_status"], "modified")
        patch = (run.path / "git-diff.patch").read_text(encoding="utf-8")
        self.assertIn("benchmark/graph_value_skeleton/runner.py", patch)
        self.assertNotIn("research/state.md", patch)
        self.assertNotIn("tests/test_y.py", patch)
        new_entry = record["files"]["benchmark/graph_value_skeleton/new_module.py"]
        self.assertEqual(new_entry["git_status"], "untracked")
        self.assertEqual(new_entry["content_saved"], "code-untracked/benchmark/graph_value_skeleton/new_module.py")
        self.assertTrue(
            (run.path / "code-untracked/benchmark/graph_value_skeleton/new_module.py").is_file()
        )
        self.assertFalse((run.path / "code-untracked/research/state.md").exists())
        self.assertFalse((run.path / "code-untracked/benchmark/graph_value_skeleton/tests").exists())
        self.assertFalse(list(run.path.rglob("*.pyc")))
        protocol_entry = record["protocol"]
        self.assertEqual(protocol_entry["git_status"], "committed_clean")
        self.assertEqual(protocol_entry["git_reference"]["path"], "research/phases/P01/protocol.md")

    def test_missing_git_identity_is_disclosed_with_content_fallback(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-nogit-"))
        (root / "benchmark" / "graph_value_skeleton").mkdir(parents=True)
        (root / "benchmark" / "graph_value_skeleton" / "runner.py").write_text(
            "RUNNER = 1\n", encoding="utf-8", newline="\n"
        )
        run = artifacts.RunDirectory(root / "runs", "no-git", "run").reserve()
        record = artifacts.capture_source(
            run,
            root,
            protocol_path=root / "protocol.md",
            runtime_paths=["benchmark/graph_value_skeleton/runner.py"],
        )
        self.assertFalse(record["identity_available"])
        self.assertIsNone(record["commit"])
        self.assertIn("commit", record["errors"])
        entry = record["files"]["benchmark/graph_value_skeleton/runner.py"]
        self.assertEqual(entry["git_status"], "unknown")
        self.assertTrue(entry["unavailable_reason"])
        self.assertIn("not a git repository", entry["unavailable_reason"])
        self.assertEqual(entry["content_saved"], "code-untracked/benchmark/graph_value_skeleton/runner.py")
        self.assertTrue((run.path / entry["content_saved"]).is_file())
        self.assertEqual(
            (run.path / "git-commit.txt").read_text(encoding="utf-8"), "UNAVAILABLE\n"
        )

    def test_source_content_change_fails_the_run(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-source-change-"))
        fixture = fixtures.build_fixture(root, "r0")
        config = fixtures.make_config(root, fixture, method="self", run_id="source-change")
        demand_path = Path(fixture["demand_path"])
        original_bytes = demand_path.read_bytes()

        def mutate_source(*args, **kwargs):
            with open(demand_path, "ab") as handle:
                handle.write(b"\0")

        with mock.patch.object(
            runner, "_write_prediction_artifacts", side_effect=mutate_source
        ):
            try:
                with self.assertRaises(runner.RunError) as context:
                    runner.execute_run(config)
            finally:
                demand_path.write_bytes(original_bytes)
        self.assertIn("source files changed", str(context.exception))
        status = fixtures.read_json(config.run_dir / "status.json")
        self.assertEqual(status["state"], "failed")
        self.assertEqual(status["stage"], "source_verification")
        events = (config.run_dir / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("source_hash_mismatch", events)


    def test_captured_source_verification_detects_changes(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-verify-source-"))
        runtime = root / "runtime.py"
        runtime.write_text("v1\n", encoding="utf-8", newline="\n")
        protocol_file = root / "protocol.md"
        protocol_file.write_text("# protocol\n", encoding="utf-8", newline="\n")
        source = {
            "files": {"runtime.py": {"sha256": artifacts.sha256_file(runtime)}},
            "protocol": {
                "path": "protocol.md",
                "sha256": artifacts.sha256_file(protocol_file),
            },
        }
        self.assertEqual(artifacts.verify_captured_source(source, root), [])
        runtime.write_text("v2\n", encoding="utf-8", newline="\n")
        self.assertTrue(
            any(
                "runtime source changed" in message
                for message in artifacts.verify_captured_source(source, root)
            )
        )
        runtime.unlink()
        self.assertTrue(
            any(
                "runtime source disappeared" in message
                for message in artifacts.verify_captured_source(source, root)
            )
        )
        runtime.write_text("v1\n", encoding="utf-8", newline="\n")
        protocol_file.write_text("# changed\n", encoding="utf-8", newline="\n")
        self.assertTrue(
            any(
                "protocol source changed" in message
                for message in artifacts.verify_captured_source(source, root)
            )
        )
        missing_identity = {"files": {}, "protocol": {"path": "protocol.md", "sha256": None}}
        self.assertTrue(
            any(
                "protocol identity is unavailable" in message
                for message in artifacts.verify_captured_source(missing_identity, root)
            )
        )

    def test_runtime_source_change_fails_final_verification(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-runtime-change-"))
        fixture = fixtures.build_fixture(root, "r0")
        probe = root / "runtime_probe.py"
        probe.write_text("v1\n", encoding="utf-8", newline="\n")
        real_capture = artifacts.capture_source

        def capture(run, repo_root, **kwargs):
            record = real_capture(run, repo_root, **kwargs)
            record["files"][str(probe)] = {
                "path": str(probe),
                "sha256": artifacts.sha256_file(probe),
                "git_status": "untracked",
            }
            return record

        def mutate(*args, **kwargs):
            probe.write_text("v2\n", encoding="utf-8", newline="\n")

        config = fixtures.make_config(
            root, fixture, method="self", run_id="runtime-change"
        )
        with mock.patch.object(
            artifacts, "capture_source", side_effect=capture
        ), mock.patch.object(
            runner, "_write_prediction_artifacts", side_effect=mutate
        ):
            with self.assertRaises(runner.RunError) as context:
                runner.execute_run(config)
        self.assertIn("runtime source changed", str(context.exception))
        status = fixtures.read_json(config.run_dir / "status.json")
        self.assertEqual(status["state"], "failed")
        self.assertEqual(status["stage"], "source_verification")

    def test_protocol_identity_change_fails_final_verification(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-protocol-change-"))
        fixture = fixtures.build_fixture(root, "r0")
        real_capture = artifacts.capture_source

        def capture(run, repo_root, **kwargs):
            record = real_capture(run, repo_root, **kwargs)
            record["protocol"]["sha256"] = "0" * 64
            return record

        config = fixtures.make_config(
            root, fixture, method="self", run_id="protocol-change"
        )
        with mock.patch.object(artifacts, "capture_source", side_effect=capture):
            with self.assertRaises(runner.RunError) as context:
                runner.execute_run(config)
        self.assertIn("protocol source changed", str(context.exception))
        status = fixtures.read_json(config.run_dir / "status.json")
        self.assertEqual(status["state"], "failed")
        self.assertEqual(status["stage"], "source_verification")


if __name__ == "__main__":
    unittest.main()
