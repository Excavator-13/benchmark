"""Graph endpoint mapping, structure audits and publication assertions.

Covers tasks 1.3, 2.1 and 2.2: integer-tuple -> canonical index mapping against
the existing ``prepare_graph_data`` semantics, dense-offset proof, published
demand/graph assertions with positive and negative cases, and multiplicity audit
versus binary adjacency.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from benchmark.graph_method import prepare_graph_data
from benchmark.graph_value_skeleton import data as gvs_data
from benchmark.graph_value_skeleton import graph as gvs_graph
from benchmark.graph_value_skeleton import protocol
from benchmark.graph_value_skeleton.tests import fixtures
from benchmark.nograph_baseline import protocol as p01


def _frames(data_name: str, keys, signal, rows):
    import pandas as pd

    key_columns = list(p01.node_key_columns(data_name))
    data_frame = pd.DataFrame(np.asarray(keys, dtype=np.int64), columns=key_columns)
    for index, month in enumerate(p01.MONTHS):
        data_frame[month] = np.asarray(signal, dtype=np.float64)[:, index]
    graph_columns = list(p01.context_columns(data_name)) + ["row_id", "col_id"]
    graph_frame = pd.DataFrame(np.asarray(rows, dtype=np.int64), columns=graph_columns)
    return data_frame, graph_frame


class GraphMappingTest(unittest.TestCase):
    def test_mapping_matches_prepare_graph_data(self) -> None:
        # Non-dense skills 2/10 exercise integer (not string) ordering, and the
        # same skill repeats under two contexts.
        keys = [(0, 2), (0, 10), (1, 2), (1, 10), (0, 1), (1, 1)]
        signal = np.arange(len(keys) * 36, dtype=np.float32).reshape(len(keys), 36)
        rows = [(0, 2, 10), (0, 10, 2), (1, 10, 2), (1, 2, 1)]
        data_frame, graph_frame = _frames("r2", keys, signal, rows)
        payload = prepare_graph_data.build_graph_dataset(
            data_frame, graph_frame, "r2", "count"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            demand_path = fixtures.write_demand(
                root / "d.parquet", "r2", keys, signal, row_order_seed=3
            )
            graph_path = fixtures.write_graph(
                root / "g.parquet", "r2", rows, row_order_seed=5
            )
            dataset = gvs_data.load_dataset("r2", demand_path=demand_path, published=False)
            graph = gvs_graph.load_graph(
                "r2", dataset.key_array, graph_path=graph_path, published=False
            )
        self.assertEqual(dataset.key_array.tolist(), payload["node_keys"])
        expected_edges = [list(edge) for edge in payload["edges"]]
        self.assertEqual(graph.edges.tolist(), expected_edges)
        self.assertTrue(all(weight == 1.0 for weight in payload["edge_weights"]))
        self.assertEqual(graph.unique_edges, len(expected_edges))
        self.assertTrue(graph.block_diagonal)
        # numeric-key ordering, not string ordering
        self.assertEqual(dataset.key_array[:2, -1].tolist(), [1, 2])

    def test_invalid_endpoints_and_columns_fail(self) -> None:
        keys = [(0, 0), (0, 1), (1, 0), (1, 1)]
        signal = np.ones((len(keys), 36), dtype=np.float32)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            demand_path = fixtures.write_demand(root / "d.parquet", "r2", keys, signal)
            dataset = gvs_data.load_dataset("r2", demand_path=demand_path, published=False)
            cases = {
                "unknown": [(0, 0, 9)],
                "cross-context": [(0, 0, 1), (0, 1, 0)],  # skill 9 absent above
                "missing-column": None,
            }
            cases.pop("cross-context")
            for label, rows in cases.items():
                if rows is None:
                    continue
                with self.subTest(case=label):
                    graph_path = fixtures.write_graph(root / f"{label}.parquet", "r2", rows)
                    with self.assertRaises(gvs_graph.GraphError) as context:
                        gvs_graph.load_graph(
                            "r2", dataset.key_array, graph_path=graph_path, published=False
                        )
                    self.assertIn("endpoint", str(context.exception))
            # A skill valid only in context 0 used with context 1 is unmatched.
            graph_path = fixtures.write_graph(
                root / "cross.parquet", "r2", [(0, 0, 1), (1, 1, 0)]
            )
            graph = gvs_graph.load_graph(
                "r2", dataset.key_array, graph_path=graph_path, published=False
            )
            self.assertEqual(graph.edge_count, 2)
            # A non-integer endpoint is rejected.
            import pandas as pd

            frame = pd.DataFrame(
                [[0, 0.5, 1]], columns=["r2_id", "row_id", "col_id"]
            )
            path = root / "fractional.parquet"
            frame.to_parquet(path, index=False)
            with self.assertRaises(gvs_graph.GraphError):
                gvs_graph.load_graph(
                    "r2", dataset.key_array, graph_path=path, published=False
                )
            # Missing column / weight column are rejected.
            frame = pd.DataFrame([[0, 0, 1]], columns=["r2_id", "row_id", "col_id"])
            missing = root / "missing.parquet"
            frame.drop(columns=["col_id"]).to_parquet(missing, index=False)
            with self.assertRaises(gvs_graph.GraphError):
                gvs_graph.load_graph(
                    "r2", dataset.key_array, graph_path=missing, published=False
                )
            weighted = root / "weighted.parquet"
            frame.assign(weight=[1.0]).to_parquet(weighted, index=False)
            with self.assertRaises(gvs_graph.GraphError):
                gvs_graph.load_graph(
                    "r2", dataset.key_array, graph_path=weighted, published=False
                )

    def test_dense_offset_formula_proven_on_published_grids(self) -> None:
        for data_name, spec in protocol.PUBLISHED_DEMAND.items():
            with self.subTest(dataset=data_name):
                contexts = list(spec["contexts"])
                skills = range(spec["skills"][0], spec["skills"][1] + 1)
                keys = np.array(
                    [(context, skill) for context in contexts for skill in skills],
                    dtype=np.int64,
                )
                self.assertEqual(keys.shape[0], spec["nodes"])
                proof = gvs_data.assert_dense_published_offsets(keys)
                self.assertEqual(proof["proven_nodes"], spec["nodes"])
                self.assertEqual(proof["stride"], 2335)

    def test_published_demand_assertions_positive_and_negative(self) -> None:
        keys = [(0, skill) for skill in range(6)]
        signal = np.arange(6 * 36, dtype=np.float32).reshape(6, 36) + 1.0
        dataset = gvs_data.from_fixture("r0", keys, signal)
        small_spec = {
            "r0": {"nodes": 6, "contexts": (0,), "skills": (0, 5), "months": 36}
        }
        with mock.patch.dict(protocol.PUBLISHED_DEMAND, small_spec, clear=True):
            proof = gvs_data.assert_published_demand(dataset.demand, "r0")
            self.assertEqual(proof["nodes"], 6)
            self.assertTrue(proof["complete_grid"])
            self.assertEqual(proof["dense_offset"]["proven_nodes"], 6)
            with self.assertRaises(protocol.ProtocolError):
                gvs_data.assert_published_demand(dataset.demand, "region")
            bad_spec = dict(small_spec)
            bad_spec["r0"] = dict(small_spec["r0"], nodes=7)
            with mock.patch.dict(protocol.PUBLISHED_DEMAND, bad_spec, clear=True):
                with self.assertRaises(gvs_data.DatasetError) as context:
                    gvs_data.assert_published_demand(dataset.demand, "r0")
                self.assertIn("node count", str(context.exception))
            gap_spec = dict(small_spec)
            gap_spec["r0"] = dict(small_spec["r0"], skills=(0, 6))
            with mock.patch.dict(protocol.PUBLISHED_DEMAND, gap_spec, clear=True):
                with self.assertRaises(gvs_data.DatasetError):
                    gvs_data.assert_published_demand(dataset.demand, "r0")

    def test_real_published_schema_is_readable_read_only(self) -> None:
        import pyarrow.parquet as pq

        for data_name in ("r0", "region", "r2"):
            demand_path = p01.demand_path(data_name)
            graph_path = p01.graph_path(data_name)
            if not demand_path.exists() or not graph_path.exists():
                self.skipTest("published dataset files are not present")
            with self.subTest(dataset=data_name):
                demand_columns = list(pq.read_schema(demand_path).names)
                self.assertEqual(
                    set(demand_columns),
                    set(p01.node_key_columns(data_name)) | set(p01.MONTHS),
                )
                self.assertEqual(
                    len(demand_columns), len(p01.node_key_columns(data_name)) + len(p01.MONTHS)
                )
                # The published graph Parquet carries a pandas index artifact
                # (``__index_level_0__``) that pandas reconstructs as the index,
                # so the semantic columns are exactly the context + endpoints.
                physical = list(pq.read_schema(graph_path).names)
                semantic = {
                    column
                    for column in physical
                    if not column.startswith("__index_level_0__")
                }
                self.assertEqual(
                    semantic,
                    set(p01.context_columns(data_name)) | {"row_id", "col_id"},
                )
                import pandas as pd

                frame = pd.read_parquet(graph_path)
                self.assertEqual(
                    list(frame.columns),
                    list(p01.context_columns(data_name)) + ["row_id", "col_id"],
                )


class GraphAuditTest(unittest.TestCase):
    def test_multiplicity_audited_not_weighted(self) -> None:
        keys = [(0, skill) for skill in range(4)]
        signal = np.arange(4 * 36, dtype=np.float32).reshape(4, 36) + 1.0
        rows = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 2, 1)]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            demand_path = fixtures.write_demand(root / "d.parquet", "r0", keys, signal)
            graph_path = fixtures.write_graph(root / "g.parquet", "r0", rows)
            dataset = gvs_data.load_dataset("r0", demand_path=demand_path, published=False)
            graph = gvs_graph.load_graph(
                "r0", dataset.key_array, graph_path=graph_path, published=False
            )
        self.assertEqual(graph.raw_rows, 4)
        self.assertEqual(graph.unique_edges, 2)
        self.assertEqual(graph.duplicate_rows, 2)
        self.assertEqual(graph.multiplicity["distribution"], {"1": 1, "3": 1})
        self.assertFalse(graph.multiplicity["weights_edges"])
        self.assertFalse(graph.multiplicity["is_observed_frequency"])
        self.assertEqual(graph.edges.tolist(), [[0, 1], [2, 1]])
        self.assertEqual(graph.symmetry_rate, 0.0)
        self.assertTrue(graph.block_diagonal)
        self.assertFalse(graph.published)

    def test_self_loops_rejected(self) -> None:
        keys = [(0, skill) for skill in range(3)]
        signal = np.ones((3, 36), dtype=np.float32)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            demand_path = fixtures.write_demand(root / "d.parquet", "r0", keys, signal)
            dataset = gvs_data.load_dataset("r0", demand_path=demand_path, published=False)
            for rows in ([(0, 1, 1)], [(0, 0, 1), (0, 2, 2)]):
                with self.subTest(rows=rows):
                    graph_path = fixtures.write_graph(root / "g.parquet", "r0", rows)
                    with self.assertRaises(gvs_graph.GraphError) as context:
                        gvs_graph.load_graph(
                            "r0", dataset.key_array, graph_path=graph_path, published=False
                        )
                    self.assertIn("self-loop", str(context.exception))

    def test_published_graph_assertions(self) -> None:
        keys = [(0, skill) for skill in range(4)]
        signal = np.ones((4, 36), dtype=np.float32)
        rows = [(0, 0, 1), (0, 1, 0), (0, 2, 3), (0, 3, 2)]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            demand_path = fixtures.write_demand(root / "d.parquet", "r0", keys, signal)
            dataset = gvs_data.load_dataset("r0", demand_path=demand_path, published=False)
            graph_path = fixtures.write_graph(root / "g.parquet", "r0", rows)
            with mock.patch.dict(
                protocol.PUBLISHED_GRAPH_ROWS, {"r0": len(rows)}, clear=True
            ):
                graph = gvs_graph.load_graph(
                    "r0", dataset.key_array, graph_path=graph_path, published=True
                )
                self.assertEqual(graph.publication["symmetry_rate"], 1.0)
                self.assertTrue(graph.publication["block_diagonal"])
                self.assertFalse(graph.publication["weight_or_frequency_column"])
            # Wrong row count fails.
            with mock.patch.dict(
                protocol.PUBLISHED_GRAPH_ROWS, {"r0": len(rows) + 1}, clear=True
            ):
                with self.assertRaises(gvs_graph.GraphError):
                    gvs_graph.load_graph(
                        "r0", dataset.key_array, graph_path=graph_path, published=True
                    )
            # Asymmetric published graph fails the frozen symmetry expectation.
            asymmetric = fixtures.write_graph(
                root / "a.parquet", "r0", [(0, 0, 1), (0, 1, 2)]
            )
            with mock.patch.dict(
                protocol.PUBLISHED_GRAPH_ROWS, {"r0": 2}, clear=True
            ):
                with self.assertRaises(gvs_graph.GraphError) as context:
                    gvs_graph.load_graph(
                        "r0", dataset.key_array, graph_path=asymmetric, published=True
                    )
                self.assertIn("symmetry", str(context.exception))
            # A duplicate published row fails the frozen no-duplicate expectation.
            duplicated = fixtures.write_graph(
                root / "u.parquet", "r0", [(0, 0, 1), (0, 1, 0), (0, 2, 3), (0, 2, 3)]
            )
            with mock.patch.dict(
                protocol.PUBLISHED_GRAPH_ROWS, {"r0": 4}, clear=True
            ):
                with self.assertRaises(gvs_graph.GraphError):
                    gvs_graph.load_graph(
                        "r0", dataset.key_array, graph_path=duplicated, published=True
                    )

    def test_context_layout_is_complete_and_local(self) -> None:
        fixture = fixtures.build_fixture(Path(tempfile.mkdtemp(prefix="gvs-layout-")), "region")
        dataset, graph = fixtures.load_fixture(fixture)
        layout = gvs_graph.context_layout(dataset.key_array, graph.edges)
        self.assertEqual(len(layout.contexts), 2)
        covered_nodes = 0
        covered_edges = 0
        for context in layout.contexts:
            members = layout.node_indices[context]
            covered_nodes += members.shape[0]
            covered_edges += layout.edge_indices[context].shape[0]
            array = dataset.key_array[members]
            self.assertTrue((array[:, 0] == context[0]).all())
        self.assertEqual(covered_nodes, dataset.node_count)
        self.assertEqual(covered_edges, graph.edge_count)


if __name__ == "__main__":
    unittest.main()
