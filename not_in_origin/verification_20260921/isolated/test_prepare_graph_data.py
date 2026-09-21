"""Unit tests for :mod:`prepare_graph_data` (tasks 1.1 and 1.2).

These tests are deliberately standard-library only: they use plain mappings as
stand-in "data frames" so that CLI, path, and data-contract behavior can be
verified without pandas or the graph libraries installed.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import prepare_graph_data as prep  # noqa: E402


def time_series(**overrides):
    """A minimal valid ``r0`` time series with three months."""
    frame = {
        "r0_id": [0, 0, 1],
        "skill_id": [10, 11, 10],
        "2021-01": [1.0, 2.0, 3.0],
        "2021-02": [1.5, 2.5, 3.5],
        "2021-03": [2.0, 3.0, 4.0],
    }
    frame.update(overrides)
    return frame


def graph(**overrides):
    frame = {"r0_id": [0, 0], "row_id": [10, 11], "col_id": [11, 10]}
    frame.update(overrides)
    return frame


class CliValidationTests(unittest.TestCase):
    """Task 1.1: CLI validation."""

    def test_defaults_cover_every_supported_combination(self):
        args = prep.build_parser().parse_args([])
        self.assertIsNone(args.data_name)
        self.assertIsNone(args.mode)
        self.assertEqual(list(prep.GRANULARITIES), ["r0", "r1", "r2", "r1-region", "r2-region", "region", "company"])
        self.assertEqual(set(prep.MODES), {"count", "rate"})
        self.assertEqual(prep.MODE_TO_SOURCE, {"count": "demand", "rate": "proportion"})

    def test_unsupported_granularity_lists_accepted_values(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            prep.main(["--data_name", "nope"])
        self.assertEqual(caught.exception.code, 2)
        for name in prep.GRANULARITIES:
            self.assertIn(name, stderr.getvalue())

    def test_unsupported_mode_lists_accepted_values(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            prep.main(["--mode", "frequency"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("count", stderr.getvalue())
        self.assertIn("rate", stderr.getvalue())

    def test_explicit_subset_is_accepted(self):
        args = prep.build_parser().parse_args(["--data_name", "r0", "company", "--mode", "rate"])
        self.assertEqual(args.data_name, ["r0", "company"])
        self.assertEqual(args.mode, ["rate"])

    def test_validate_names_rejects_programmatic_misuse(self):
        with self.assertRaises(prep.GraphDataError) as caught:
            prep.validate_names("bogus", "rate")
        self.assertIn("r0", str(caught.exception))
        with self.assertRaises(prep.GraphDataError):
            prep.source_paths("r0", "bogus")

    def test_cli_runs_from_any_working_directory(self):
        """The documented CLI must work from the repository root and elsewhere."""
        script = MODULE_DIR / "prepare_graph_data.py"
        self.assertTrue(script.is_file())
        for cwd in (prep.REPO_ROOT, Path(tempfile.gettempdir())):
            with self.subTest(cwd=str(cwd)):
                help_run = subprocess.run(
                    [sys.executable, str(script), "--help"],
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(help_run.returncode, 0, help_run.stderr)
                self.assertIn("--data_name", help_run.stdout)

                bad_run = subprocess.run(
                    [sys.executable, str(script), "--data_name", "bogus"],
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(bad_run.returncode, 2)
                self.assertIn("r0", bad_run.stderr)


class PathResolutionTests(unittest.TestCase):
    """Task 1.1: module-relative repository paths."""

    def test_paths_are_module_relative_and_absolute(self):
        self.assertTrue(prep.REPO_ROOT.is_absolute())
        self.assertEqual(prep.REPO_ROOT, MODULE_DIR.parents[1])
        self.assertEqual(prep.DATASET_DIR, prep.REPO_ROOT / "dataset")
        self.assertEqual(
            prep.output_path("r0", "rate"),
            prep.DEFAULT_OUTPUT_DIR / "rate" / "r0.json",
        )

    def test_mode_maps_to_shipped_source_directories(self):
        data_path, graph_path = prep.source_paths("r0", "rate")
        self.assertEqual(data_path, prep.REPO_ROOT / "dataset" / "proportion" / "r0.parquet")
        self.assertEqual(graph_path, prep.REPO_ROOT / "dataset" / "graph" / "r0.parquet")
        data_path, _ = prep.source_paths("company", "count")
        self.assertEqual(data_path, prep.REPO_ROOT / "dataset" / "demand" / "company.parquet")

    def test_sources_exist_for_every_supported_combination(self):
        for mode in prep.MODES:
            for name in prep.GRANULARITIES:
                data_path, graph_path = prep.source_paths(name, mode)
                with self.subTest(mode=mode, name=name):
                    self.assertTrue(data_path.is_file(), data_path)
                    self.assertTrue(graph_path.is_file(), graph_path)

    def test_paths_do_not_depend_on_working_directory(self):
        original = os.getcwd()
        self.addCleanup(os.chdir, original)
        expected = prep.output_path("r0", "rate")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                self.assertEqual(prep.output_path("r0", "rate"), expected)
                self.assertEqual(prep.source_paths("r0", "rate")[0], prep.DATASET_DIR / "proportion" / "r0.parquet")
            finally:
                os.chdir(original)

    def test_context_columns_cover_every_granularity(self):
        self.assertEqual(prep.CONTEXT_COLUMNS["r1-region"], ("r1_id", "region_id"))
        self.assertEqual(prep.CONTEXT_COLUMNS["r2-region"], ("r2_id", "region_id"))
        self.assertEqual(prep.CONTEXT_COLUMNS["region"], ("region_id",))
        self.assertEqual(prep.CONTEXT_COLUMNS["company"], ("company_id",))
        self.assertEqual(set(prep.CONTEXT_COLUMNS), set(prep.GRANULARITIES))


class OutputDirectoryTests(unittest.TestCase):
    """Task 1.1: generated-data directories are created automatically."""

    def _run(self, argv):
        stdout = io.StringIO()
        with mock.patch.object(prep, "_read_parquet", side_effect=self._frame), redirect_stdout(stdout):
            code = prep.main(argv)
        return code, stdout.getvalue()

    @staticmethod
    def _frame(path):
        return graph() if Path(path).parent.name == "graph" else time_series()

    def test_prepare_dataset_creates_missing_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "not" / "created" / "yet"
            destination = root / "rate" / "r0.json"
            with mock.patch.object(prep, "_read_parquet", side_effect=self._frame):
                written = prep.prepare_dataset("r0", "rate", output_dir=root)
            self.assertEqual(written, destination)
            self.assertTrue(destination.is_file())
            payload = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], prep.SCHEMA_VERSION)

    def test_cli_writes_one_file_per_requested_combination(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(
                ["--output_dir", tmp, "--data_name", "r0", "--mode", "rate", "count"]
            )
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / "rate" / "r0.json").is_file())
            self.assertTrue((Path(tmp) / "count" / "r0.json").is_file())
            self.assertIn("prepared r0 (rate)", output)


class PayloadContractTests(unittest.TestCase):
    """Task 1.2: versioned JSON generation."""

    def build(self, data=None, edges=None, **kwargs):
        return prep.build_graph_dataset(data or time_series(), edges or graph(), "r0", "rate")

    def test_payload_shape_and_order(self):
        payload = self.build()
        self.assertEqual(
            list(payload),
            [
                "schema_version",
                "data_name",
                "mode",
                "node_keys",
                "features",
                "edges",
                "edge_weights",
            ],
        )
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["data_name"], "r0")
        self.assertEqual(payload["mode"], "rate")

    def test_node_keys_are_ordered_context_qualified_arrays(self):
        payload = self.build()
        self.assertEqual(payload["node_keys"], [[0, 10], [0, 11], [1, 10]])
        self.assertEqual(len(payload["node_keys"]), len(set(map(tuple, payload["node_keys"]))))

    def test_features_are_chronological_and_time_major(self):
        unsorted = time_series()
        unordered = {
            "r0_id": unsorted["r0_id"],
            "skill_id": unsorted["skill_id"],
            "2021-03": unsorted["2021-03"],
            "2021-01": unsorted["2021-01"],
            "2021-02": unsorted["2021-02"],
        }
        payload = prep.build_graph_dataset(unordered, graph(), "r0", "rate")
        self.assertEqual(payload["features"], [[1.0, 2.0, 3.0], [1.5, 2.5, 3.5], [2.0, 3.0, 4.0]])

    def test_edges_are_mapped_directed_indices_with_aligned_weights(self):
        payload = self.build()
        self.assertEqual(payload["edges"], [[0, 1], [1, 0]])
        self.assertEqual(payload["edge_weights"], [1.0, 1.0])
        self.assertEqual(len(payload["edges"]), len(payload["edge_weights"]))
        for source, target in payload["edges"]:
            self.assertLess(source, len(payload["node_keys"]))
            self.assertLess(target, len(payload["node_keys"]))

    def test_reverse_edges_stay_separate(self):
        payload = self.build(edges={"r0_id": [0, 0], "row_id": [10, 11], "col_id": [11, 10]})
        self.assertEqual(payload["edges"], [[0, 1], [1, 0]])

    def test_duplicate_rows_preserve_exact_multiplicity(self):
        rows = {"r0_id": [0, 0, 0], "row_id": [10, 10, 11], "col_id": [11, 11, 10]}
        payload = self.build(edges=rows)
        self.assertEqual(payload["edges"], [[0, 1], [1, 0]])
        self.assertEqual(payload["edge_weights"], [2.0, 1.0])
        self.assertEqual(sum(payload["edge_weights"]), len(rows["row_id"]))

    def test_compound_context_keeps_same_skill_pair_distinct(self):
        data = {
            "r1_id": [0, 0, 1, 1],
            "region_id": [0, 1, 0, 1],
            "skill_id": [10, 10, 10, 10],
            "2021-01": [1.0, 2.0, 3.0, 4.0],
            "2021-02": [5.0, 6.0, 7.0, 8.0],
            "2021-03": [9.0, 10.0, 11.0, 12.0],
        }
        edges = {"r1_id": [0, 0], "region_id": [0, 1], "row_id": [10, 10], "col_id": [10, 10]}
        payload = prep.build_graph_dataset(data, edges, "r1-region", "rate")
        self.assertEqual(
            payload["node_keys"],
            [[0, 0, 10], [0, 1, 10], [1, 0, 10], [1, 1, 10]],
        )
        self.assertEqual(payload["edges"], [[0, 0], [1, 1]])
        self.assertEqual(payload["edge_weights"], [1.0, 1.0])

    def test_same_skill_with_different_context_is_not_merged(self):
        data = {
            "r0_id": [0, 1],
            "skill_id": [10, 10],
            "2021-01": [1.0, 2.0],
            "2021-02": [3.0, 4.0],
            "2021-03": [5.0, 6.0],
        }
        edges = {"r0_id": [0, 1], "row_id": [10, 10], "col_id": [10, 10]}
        payload = prep.build_graph_dataset(data, edges, "r0", "rate")
        self.assertEqual(payload["node_keys"], [[0, 10], [1, 10]])
        self.assertEqual(payload["edges"], [[0, 0], [1, 1]])

    def test_missing_time_series_column_is_reported(self):
        broken = time_series()
        del broken["skill_id"]
        with self.assertRaises(prep.GraphDataError) as caught:
            prep.build_graph_dataset(broken, graph(), "r0", "rate")
        self.assertIn("skill_id", str(caught.exception))

    def test_missing_graph_column_is_reported(self):
        broken = graph()
        del broken["col_id"]
        with self.assertRaises(prep.GraphDataError) as caught:
            prep.build_graph_dataset(time_series(), broken, "r0", "rate")
        self.assertIn("col_id", str(caught.exception))

    def test_missing_time_columns_are_reported(self):
        stripped = {"r0_id": [0], "skill_id": [10]}
        with self.assertRaises(prep.GraphDataError) as caught:
            prep.build_graph_dataset(stripped, graph(), "r0", "rate")
        self.assertIn("time column", str(caught.exception).lower())

    def test_duplicate_nodes_are_rejected(self):
        duplicated = time_series()
        duplicated["r0_id"] = [0, 0, 0]
        duplicated["skill_id"] = [10, 10, 11]
        with self.assertRaises(prep.GraphDataError) as caught:
            prep.build_graph_dataset(duplicated, graph(), "r0", "rate")
        self.assertIn("duplicate node", str(caught.exception))

    def test_unmatched_endpoint_is_rejected_with_dataset_context(self):
        unmatched = {"r0_id": [0], "row_id": [10], "col_id": [999]}
        with self.assertRaises(prep.GraphDataError) as caught:
            prep.build_graph_dataset(time_series(), unmatched, "r0", "rate")
        message = str(caught.exception)
        self.assertIn("r0", message)
        self.assertIn("999", message)

    def test_non_finite_features_are_rejected(self):
        broken = time_series()
        broken["2021-02"] = [1.0, float("nan"), 3.0]
        with self.assertRaises(prep.GraphDataError) as caught:
            prep.build_graph_dataset(broken, graph(), "r0", "rate")
        self.assertIn("finite", str(caught.exception))

    def test_non_integer_identifiers_are_rejected(self):
        broken = time_series()
        broken["r0_id"] = [0, 1.5, 1]
        with self.assertRaises(prep.GraphDataError):
            prep.build_graph_dataset(broken, graph(), "r0", "rate")

    def test_generation_is_deterministic(self):
        first = json.dumps(self.build(), sort_keys=True)
        shuffled = {
            "r0_id": [1, 0, 0],
            "skill_id": [10, 11, 10],
            "2021-01": [3.0, 2.0, 1.0],
            "2021-02": [3.5, 2.5, 1.5],
            "2021-03": [4.0, 3.0, 2.0],
        }
        second = json.dumps(prep.build_graph_dataset(shuffled, graph(), "r0", "rate"), sort_keys=True)
        self.assertEqual(first, second)


class NotebookTests(unittest.TestCase):
    """Task 1.4: the notebook is a thin caller of the tested preparer."""

    def setUp(self):
        self.notebook = json.loads(
            (MODULE_DIR / "data_process.ipynb").read_text(encoding="utf-8")
        )
        self.code = "\n".join(
            "".join(cell["source"])
            for cell in self.notebook["cells"]
            if cell["cell_type"] == "code"
        )

    def test_notebook_contains_no_hard_coded_transformation(self):
        compile(self.code, "data_process.ipynb", "exec")
        self.assertIn("prepare_graph_data", self.code)
        for forbidden in ("read_parquet", "json.dump", "set_index", "for data_name in ['company']"):
            self.assertNotIn(forbidden, self.code)

    def _run_notebook(self, cwd):
        calls = []
        fake = types.ModuleType("prepare_graph_data")
        fake.main = lambda argv=None: calls.append(argv)
        original_cwd = os.getcwd()
        original_path = list(sys.path)
        os.chdir(cwd)
        try:
            with mock.patch.dict(sys.modules, {"prepare_graph_data": fake}):
                exec(compile(self.code, "data_process.ipynb", "exec"), {"__name__": "__main__"})
        finally:
            os.chdir(original_cwd)
            sys.path[:] = original_path
        return calls

    def test_notebook_prepares_every_combination_from_the_module_directory(self):
        self.assertEqual(self._run_notebook(MODULE_DIR), [[]])

    def test_notebook_prepares_every_combination_from_the_repository_root(self):
        self.assertEqual(self._run_notebook(prep.REPO_ROOT), [[]])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
