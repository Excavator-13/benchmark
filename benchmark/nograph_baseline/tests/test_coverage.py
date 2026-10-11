"""Evaluation-only neighbour coverage annotation and mask bundle validation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import nb_fixtures as fx
from benchmark.nograph_baseline import coverage, protocol


class GraphCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.keys = fx.r0_keys(5)
        self.key_array = np.asarray(self.keys, dtype=np.int64)
        self.rows = [[0, 0, 1], [0, 1, 2], [0, 2, 2], [0, 3, 3]]
        self.graph_path = fx.write_graph(self.root / "r0.parquet", "r0", self.rows)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_both_endpoints_covered_and_self_loops_excluded(self) -> None:
        result = coverage.load_graph_coverage(
            "r0", self.key_array, graph_path=self.graph_path
        )
        np.testing.assert_array_equal(
            result.mask, np.array([True, True, True, False, False])
        )
        self.assertEqual(result.provenance["self_loop_rows"], 2)
        self.assertEqual(result.provenance["directed_source_rows"], 4)
        self.assertEqual(result.provenance["covered_nodes"], 3)
        self.assertFalse(result.provenance["used_for_forecasting"])

    def test_unmatched_endpoint_fails_validation(self) -> None:
        bad = fx.write_graph(self.root / "bad.parquet", "r0", [[0, 0, 99]])
        with self.assertRaises(coverage.CoverageError):
            coverage.load_graph_coverage("r0", self.key_array, graph_path=bad)

    def test_unknown_self_loop_endpoint_fails_validation(self) -> None:
        # Before V-004 this row was accepted because the self-loop check ran
        # before endpoint membership.
        bad = fx.write_graph(self.root / "selfloop-bad.parquet", "r0", [[0, 999, 999]])
        with self.assertRaises(coverage.CoverageError):
            coverage.load_graph_coverage("r0", self.key_array, graph_path=bad)
        bad_context = fx.write_graph(
            self.root / "selfloop-context.parquet", "r0", [[7, 0, 0]]
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_graph_coverage("r0", self.key_array, graph_path=bad_context)

    def test_valid_self_loop_excluded_while_edges_cover_both_ends(self) -> None:
        path = fx.write_graph(
            self.root / "mixed.parquet", "r0", [[0, 3, 3], [0, 0, 1]]
        )
        result = coverage.load_graph_coverage("r0", self.key_array, graph_path=path)
        self.assertEqual(result.provenance["self_loop_rows"], 1)
        np.testing.assert_array_equal(
            result.mask, np.array([True, True, False, False, False])
        )

    def test_missing_coverage_evidence_is_an_error(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.load_graph_coverage(
                "r0", self.key_array, graph_path=self.root / "absent.parquet"
            )

    def test_same_skill_in_two_regions_is_context_qualified(self) -> None:
        keys = np.asarray([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=np.int64)
        rows = [[0, 0, 1], [1, 1, 1]]  # edge only in region 0, self-loop in region 1
        path = fx.write_graph(self.root / "region.parquet", "region", rows)
        result = coverage.load_graph_coverage("region", keys, graph_path=path)
        np.testing.assert_array_equal(
            result.mask, np.array([True, True, False, False])
        )


class MaskBundleTests(unittest.TestCase):
    SOURCE_SHA = "a" * 64

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.key_array = np.asarray(fx.r0_keys(4), dtype=np.int64)
        self.mask = np.array([True, False, True, False])

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _valid_provenance(self) -> dict:
        return {
            "definition": "verified context-qualified non-self coverage",
            "source": "raw_graph_parquet",
            "source_path": "dataset/graph/r0.parquet",
            "source_sha256": self.SOURCE_SHA,
        }

    def test_round_trip_with_exact_identity_alignment(self) -> None:
        path = self.root / "mask.npz"
        record = coverage.save_mask_bundle(
            path, "r0", self.key_array, self.mask, self._valid_provenance()
        )
        self.assertIn("bundle_sha256", record)
        loaded = coverage.load_mask_bundle(path, "r0", self.key_array)
        np.testing.assert_array_equal(loaded.mask, self.mask)
        self.assertEqual(loaded.provenance["source"], "mask_bundle")
        # The bundle hash authenticates bytes; the recorded source hash keeps
        # the scientific derivation traceable.
        self.assertEqual(loaded.provenance["bundle_sha256"], record["bundle_sha256"])
        self.assertEqual(loaded.provenance["source_sha256"], self.SOURCE_SHA)
        self.assertEqual(loaded.provenance["dataset"], "r0")

    def test_wrong_node_keys_are_rejected(self) -> None:
        path = self.root / "mask.npz"
        coverage.save_mask_bundle(
            path, "r0", self.key_array, self.mask, self._valid_provenance()
        )
        other = np.asarray(fx.r0_keys(4), dtype=np.int64)
        other[0, 1] = 99
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(path, "r0", other)

    def test_missing_bundle_is_an_error(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(self.root / "absent.npz", "r0", self.key_array)

    def _write_raw_bundle(self, path: Path, *, metadata, mask=None, keys=None) -> Path:
        with open(path, "wb") as handle:
            np.savez(
                handle,
                mask=np.array([True, False, True, False], dtype=bool)
                if mask is None
                else mask,
                node_keys=self.key_array if keys is None else keys,
                metadata=np.array(json.dumps(metadata)),
            )
        return path

    def test_bundle_without_metadata_is_rejected(self) -> None:
        path = self.root / "anon.npz"
        with open(path, "wb") as handle:
            np.savez(handle, mask=self.mask, node_keys=self.key_array)
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(path, "r0", self.key_array)

    def test_missing_source_provenance_is_rejected(self) -> None:
        path = self._write_raw_bundle(
            self.root / "noprov.npz",
            metadata={
                "dataset": "r0",
                "key_columns": ["r0_id", "skill_id"],
                "definition": "d",
                "provenance": {"source": "raw_graph_parquet"},
            },
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(path, "r0", self.key_array)

    def test_save_without_source_hash_is_rejected(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.save_mask_bundle(
                self.root / "bad.npz",
                "r0",
                self.key_array,
                self.mask,
                {"definition": "fixture"},
            )

    def test_wrong_dataset_or_schema_is_rejected(self) -> None:
        wrong_dataset = self._write_raw_bundle(
            self.root / "wrongds.npz",
            metadata={
                "dataset": "region",
                "key_columns": ["r0_id", "skill_id"],
                "definition": "d",
                "provenance": {"source_sha256": self.SOURCE_SHA},
            },
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(wrong_dataset, "r0", self.key_array)
        wrong_schema = self._write_raw_bundle(
            self.root / "wrongschema.npz",
            metadata={
                "dataset": "r0",
                "key_columns": ["skill_id"],
                "definition": "d",
                "provenance": {"source_sha256": self.SOURCE_SHA},
            },
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(wrong_schema, "r0", self.key_array)
        empty_definition = self._write_raw_bundle(
            self.root / "emptydef.npz",
            metadata={
                "dataset": "r0",
                "key_columns": ["r0_id", "skill_id"],
                "definition": "",
                "provenance": {"source_sha256": self.SOURCE_SHA},
            },
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(empty_definition, "r0", self.key_array)

    def test_non_boolean_mask_is_rejected(self) -> None:
        path = self._write_raw_bundle(
            self.root / "nonbool.npz",
            metadata={
                "dataset": "r0",
                "key_columns": ["r0_id", "skill_id"],
                "definition": coverage.COVERAGE_DEFINITION,
                "provenance": {"source_sha256": self.SOURCE_SHA},
            },
            mask=np.array([1, 0, 1, 0]),
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(path, "r0", self.key_array)

    def _metadata(self, definition, definition_id=None) -> dict:
        metadata = {
            "dataset": "r0",
            "key_columns": ["r0_id", "skill_id"],
            "definition": definition,
            "provenance": {
                "source": "raw_graph_parquet",
                "source_path": "dataset/graph/r0.parquet",
                "source_sha256": self.SOURCE_SHA,
            },
        }
        if definition_id is not None:
            metadata["definition_id"] = definition_id
        return metadata

    def test_contradictory_definition_is_rejected(self) -> None:
        path = self._write_raw_bundle(
            self.root / "contradictory.npz",
            metadata=self._metadata(
                "self-loops count as neighbours; ignore contexts"
            ),
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(path, "r0", self.key_array)

    def test_non_string_or_empty_definition_is_rejected(self) -> None:
        for name, definition in (("numdef", 123), ("emptydef2", "   ")):
            with self.subTest(definition=definition):
                path = self._write_raw_bundle(
                    self.root / f"{name}.npz", metadata=self._metadata(definition)
                )
                with self.assertRaises(coverage.CoverageError):
                    coverage.load_mask_bundle(path, "r0", self.key_array)

    def test_wrong_definition_id_is_rejected(self) -> None:
        path = self._write_raw_bundle(
            self.root / "wrongid.npz",
            metadata=self._metadata(
                coverage.COVERAGE_DEFINITION, definition_id="some-other-coverage"
            ),
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(path, "r0", self.key_array)

    def test_canonical_definition_representations_are_accepted(self) -> None:
        by_text = self._write_raw_bundle(
            self.root / "bytext.npz",
            metadata=self._metadata(coverage.COVERAGE_DEFINITION),
        )
        loaded = coverage.load_mask_bundle(by_text, "r0", self.key_array)
        np.testing.assert_array_equal(loaded.mask, self.mask)
        self.assertEqual(
            loaded.provenance["definition_id"], coverage.COVERAGE_DEFINITION_ID
        )
        by_id = self._write_raw_bundle(
            self.root / "byid.npz",
            metadata=self._metadata(
                "human-readable note", definition_id=coverage.COVERAGE_DEFINITION_ID
            ),
        )
        loaded = coverage.load_mask_bundle(by_id, "r0", self.key_array)
        np.testing.assert_array_equal(loaded.mask, self.mask)

    def test_saved_bundle_records_canonical_definition(self) -> None:
        path = self.root / "saved.npz"
        coverage.save_mask_bundle(
            path,
            "r0",
            self.key_array,
            self.mask,
            {
                "definition": "contradictory caller text",
                "source_sha256": self.SOURCE_SHA,
            },
        )
        loaded = coverage.load_mask_bundle(path, "r0", self.key_array)
        self.assertEqual(loaded.provenance["definition"], coverage.COVERAGE_DEFINITION)
        self.assertEqual(
            loaded.provenance["definition_id"], coverage.COVERAGE_DEFINITION_ID
        )


class R2CoverageTests(unittest.TestCase):
    """P01-T006: r2 coverage stays context-qualified and provenance-checked."""

    SOURCE_SHA = "b" * 64

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.key_array = np.asarray(fx.r2_keys(2, 3), dtype=np.int64)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_non_self_edge_covers_both_ends_only_in_its_context(self) -> None:
        rows = [[0, 0, 1], [1, 1, 1]]  # edge in context 0, self-loop in context 1
        path = fx.write_graph(self.root / "r2.parquet", "r2", rows)
        result = coverage.load_graph_coverage("r2", self.key_array, graph_path=path)
        # (0, 0) and (0, 1) are covered; the same skill in context 1 is not.
        np.testing.assert_array_equal(
            result.mask, np.array([True, True, False, False, False, False])
        )
        self.assertEqual(result.provenance["self_loop_rows"], 1)
        self.assertEqual(result.provenance["non-self rows used"], 1)
        self.assertEqual(result.provenance["covered_nodes"], 2)
        self.assertEqual(result.provenance["key_columns"], ["r2_id", "skill_id"])
        self.assertEqual(result.provenance["nodes"], 6)
        self.assertFalse(result.provenance["used_for_forecasting"])
        groups = coverage.coverage_groups(result.mask)
        self.assertEqual(int(groups["has_nonself_neighbor"].sum()), 2)
        self.assertEqual(int(groups["no_nonself_neighbor"].sum()), 4)

    def test_self_loop_alone_never_supplies_a_neighbour(self) -> None:
        rows = [[0, 0, 0], [1, 2, 2]]
        path = fx.write_graph(self.root / "selfloops.parquet", "r2", rows)
        result = coverage.load_graph_coverage("r2", self.key_array, graph_path=path)
        self.assertEqual(result.provenance["self_loop_rows"], 2)
        self.assertFalse(result.mask.any())

    def test_unknown_context_or_endpoint_fails_validation(self) -> None:
        unknown_context = fx.write_graph(
            self.root / "context.parquet", "r2", [[7, 0, 1]]
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_graph_coverage(
                "r2", self.key_array, graph_path=unknown_context
            )
        unknown_endpoint = fx.write_graph(
            self.root / "endpoint.parquet", "r2", [[0, 0, 99]]
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_graph_coverage(
                "r2", self.key_array, graph_path=unknown_endpoint
            )

    def test_graph_without_r2_id_column_fails_validation(self) -> None:
        # A table using another dataset's context column cannot qualify r2 keys.
        wrong_columns = fx.write_graph(
            self.root / "wrong-cols.parquet", "r0", [[0, 0, 1]]
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_graph_coverage(
                "r2", self.key_array, graph_path=wrong_columns
            )

    def test_mask_bundle_round_trip_records_r2_provenance(self) -> None:
        path = self.root / "r2-mask.npz"
        mask = np.array([True, False, True, False, False, True])
        record = coverage.save_mask_bundle(
            path,
            "r2",
            self.key_array,
            mask,
            {
                "definition": coverage.COVERAGE_DEFINITION,
                "source": "raw_graph_parquet",
                "source_path": "dataset/graph/r2.parquet",
                "source_sha256": self.SOURCE_SHA,
            },
        )
        loaded = coverage.load_mask_bundle(path, "r2", self.key_array)
        np.testing.assert_array_equal(loaded.mask, mask)
        self.assertEqual(loaded.provenance["dataset"], "r2")
        self.assertEqual(loaded.provenance["key_columns"], ["r2_id", "skill_id"])
        self.assertEqual(loaded.provenance["source_sha256"], self.SOURCE_SHA)
        self.assertEqual(loaded.provenance["bundle_sha256"], record["bundle_sha256"])
        self.assertEqual(loaded.covered, 3)

    def _write_raw_bundle(self, path: Path, *, metadata, mask=None, keys=None) -> Path:
        with open(path, "wb") as handle:
            np.savez(
                handle,
                mask=np.array([True, False, True, False, False, True], dtype=bool)
                if mask is None
                else mask,
                node_keys=self.key_array if keys is None else keys,
                metadata=np.array(json.dumps(metadata)),
            )
        return path

    def _metadata(self, **overrides) -> dict:
        metadata = {
            "dataset": "r2",
            "key_columns": ["r2_id", "skill_id"],
            "definition": coverage.COVERAGE_DEFINITION,
            "provenance": {
                "source": "raw_graph_parquet",
                "source_path": "dataset/graph/r2.parquet",
                "source_sha256": self.SOURCE_SHA,
            },
        }
        metadata.update(overrides)
        return metadata

    def test_mask_bundle_wrong_dataset_or_schema_is_rejected(self) -> None:
        wrong_dataset = self._write_raw_bundle(
            self.root / "wrongds.npz", metadata=self._metadata(dataset="region")
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(wrong_dataset, "r2", self.key_array)
        wrong_schema = self._write_raw_bundle(
            self.root / "wrongschema.npz",
            metadata=self._metadata(key_columns=["region_id", "skill_id"]),
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(wrong_schema, "r2", self.key_array)

    def test_mask_bundle_wrong_keys_missing_provenance_or_semantics_fail(self) -> None:
        other_keys = np.asarray(fx.r2_keys(2, 3), dtype=np.int64)
        other_keys[0, 1] = 99
        wrong_keys = self._write_raw_bundle(
            self.root / "wrongkeys.npz", metadata=self._metadata(), keys=other_keys
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(wrong_keys, "r2", self.key_array)
        no_source = self._write_raw_bundle(
            self.root / "nosource.npz",
            metadata=self._metadata(provenance={"source": "raw_graph_parquet"}),
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(no_source, "r2", self.key_array)
        bad_semantics = self._write_raw_bundle(
            self.root / "semantics.npz",
            metadata=self._metadata(
                definition="self-loops count as neighbours; ignore contexts"
            ),
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(bad_semantics, "r2", self.key_array)
        wrong_id = self._write_raw_bundle(
            self.root / "wrongid.npz",
            metadata=self._metadata(definition_id="some-other-coverage"),
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.load_mask_bundle(wrong_id, "r2", self.key_array)


if __name__ == "__main__":
    unittest.main()
