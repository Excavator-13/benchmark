"""Key-only target population checks and lazy per-context expansion."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from benchmark.occupation_skill_graph import data as osg_data
from benchmark.occupation_skill_graph import mapping
from benchmark.occupation_skill_graph.tests import fixtures as fx


class TargetMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.skills = np.array([1, 4, 7], dtype=np.int64)
        self.edges = np.array([[0, 1], [1, 2]], dtype=np.int64)
        self.scores = np.array([0.5, 0.25], dtype=np.float64)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_two_contexts_receive_identical_relations(self) -> None:
        target = fx.target_fixture("r2", [2, 5], self.skills)
        population = mapping.validate_target_population(target, self.skills)
        self.assertEqual(population["status"], "ok")
        descriptor = mapping.mapping_descriptor(target, self.edges, self.scores)
        self.assertEqual(descriptor["undirected_edges_per_context"], 2)
        self.assertEqual(descriptor["directed_expansions_per_context"], 4)
        self.assertEqual(descriptor["cross_context_edges"], 0)
        seen = []
        for context in mapping.iter_context_edges(target, self.edges, self.scores):
            seen.append(context.context_id)
            np.testing.assert_array_equal(context.edges, self.edges)
            np.testing.assert_array_equal(context.scores, self.scores)
            directed = context.directed_pairs()
            self.assertEqual(directed.shape, (4, 4))
            self.assertTrue((directed[:, 0] == context.context_id).all())
            self.assertTrue((directed[:, 2] == context.context_id).all())
            self.assertEqual(context.node_key(4), (context.context_id, 4))
        self.assertEqual(seen, [2, 5])
        self.assertFalse(descriptor["duplicated_edge_arrays_saved"])
        self.assertFalse(descriptor["target_value_columns_read"])

    def test_missing_skill_is_explicit(self) -> None:
        target = fx.target_fixture("r0", [0], [1, 4])
        with self.assertRaises(mapping.MappingError):
            mapping.validate_target_population(target, self.skills)

    def test_extra_skill_is_explicit(self) -> None:
        target = fx.target_fixture("r0", [0], [1, 4, 7, 10])
        with self.assertRaises(mapping.MappingError):
            mapping.validate_target_population(target, self.skills)

    def test_duplicate_target_key_is_rejected(self) -> None:
        path = fx.write_target_table(
            self.root / "duplicate.parquet", "r0", [0], [1, 4]
        )
        import pandas as pd

        frame = pd.read_parquet(path)
        frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
        frame.to_parquet(path, index=False)
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_target_keys("r0", path, fixture=True)

    def test_incomplete_target_grid_is_rejected(self) -> None:
        import pandas as pd

        path = fx.write_target_table(
            self.root / "incomplete.parquet", "region", [0, 1], [1, 4]
        )
        frame = pd.read_parquet(path)
        frame = frame[~((frame["region_id"] == 1) & (frame["skill_id"] == 4))]
        frame.to_parquet(path, index=False)
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_target_keys("region", path, fixture=True)

    def test_target_values_are_not_requested(self) -> None:
        path = fx.write_target_table(
            self.root / "values.parquet", "r2", [2, 5], self.skills
        )
        import pandas as pd

        original = pd.read_parquet
        requested: list[list[str]] = []

        def wrapper(*args, **kwargs):
            requested.append(list(kwargs.get("columns", [])))
            return original(*args, **kwargs)

        with mock.patch("pandas.read_parquet", side_effect=wrapper):
            target = osg_data.load_target_keys("r2", path, fixture=True)
        self.assertTrue(requested)
        self.assertEqual(
            set(requested[0]), set(("r2_id", "skill_id"))
        )
        self.assertFalse(target.identity["value_columns_read"])

    def test_target_row_order_does_not_change_identity(self) -> None:
        first = fx.write_target_table(
            self.root / "first.parquet", "r2", [2, 5], self.skills
        )
        second = fx.write_target_table(
            self.root / "second.parquet",
            "r2",
            [2, 5],
            self.skills,
            row_order_seed=9,
        )
        left = osg_data.load_target_keys("r2", first, fixture=True)
        right = osg_data.load_target_keys("r2", second, fixture=True)
        np.testing.assert_array_equal(left.key_array, right.key_array)
        self.assertEqual(
            left.identity["sha256"], right.identity["sha256"]
        )

    def test_target_value_columns_do_not_filter_edges(self) -> None:
        # Target values are deliberately unusable NaNs; mapping still lifts every
        # shared edge because target demand never enters the mapping.
        target = fx.target_fixture("r2", [2, 5], self.skills)
        descriptor = mapping.mapping_descriptor(target, self.edges, self.scores)
        self.assertEqual(descriptor["undirected_edges_per_context"], 2)
        self.assertEqual(descriptor["total_directed_expansions"], 8)


if __name__ == "__main__":
    unittest.main()
