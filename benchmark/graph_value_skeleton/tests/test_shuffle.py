"""Degree-preserving directed shuffle: invariants, reproducibility, failures.

Covers tasks 4.1 and 4.2 (and the seed restriction of 4.3).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import numpy as np

from benchmark.graph_value_skeleton import graph as gvs_graph
from benchmark.graph_value_skeleton import protocol
from benchmark.graph_value_skeleton import shuffle as gvs_shuffle
from benchmark.graph_value_skeleton.tests import fixtures


def degrees(key_array: np.ndarray, edges: np.ndarray) -> tuple:
    node_count = int(key_array.shape[0])
    incoming = np.bincount(edges[:, 1], minlength=node_count) if edges.size else np.zeros(node_count, dtype=np.int64)
    outgoing = np.bincount(edges[:, 0], minlength=node_count) if edges.size else np.zeros(node_count, dtype=np.int64)
    return incoming, outgoing


class ShuffleInvariantTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="gvs-shuffle-"))
        self.fixture = fixtures.build_fixture(self.root, "region")
        self.dataset, self.graph = fixtures.load_fixture(self.fixture)

    def test_preserves_degrees_and_changes_every_context(self) -> None:
        for seed in protocol.SHUFFLE_SEEDS:
            with self.subTest(seed=seed):
                shuffled = gvs_shuffle.shuffle_graph(
                    "region", self.dataset.key_array, self.graph.edges, seed
                )
                self.assertEqual(shuffled.edge_count, self.graph.edge_count)
                source_degree = degrees(self.dataset.key_array, self.graph.edges)
                result_degree = degrees(self.dataset.key_array, shuffled.edges)
                np.testing.assert_array_equal(source_degree[0], result_degree[0])
                np.testing.assert_array_equal(source_degree[1], result_degree[1])
                self.assertEqual(
                    shuffled.edges.tolist(),
                    gvs_graph.canonical_edge_array(shuffled.edges).tolist(),
                )
                self.assertEqual(
                    shuffled.edges.shape[0],
                    np.unique(shuffled.edges, axis=0).shape[0],
                )
                self.assertFalse(
                    bool((shuffled.edges[:, 0] == shuffled.edges[:, 1]).any())
                )
                layout = gvs_graph.context_layout(
                    self.dataset.key_array, shuffled.edges
                )
                self.assertEqual(layout.contexts, [(0,), (1,)])
                nonempty = [
                    entry for entry in shuffled.audit["contexts"] if not entry["empty"]
                ]
                self.assertEqual(len(nonempty), 2)
                for entry in nonempty:
                    self.assertGreater(entry["changed_edges"], 0)
                    self.assertEqual(
                        entry["intersection_edges"] + entry["changed_edges"],
                        entry["edge_count"],
                    )
                    self.assertEqual(
                        entry["symmetric_difference_edges"],
                        2 * entry["changed_edges"],
                    )
                    self.assertGreater(entry["accepted"], 0)
                    self.assertLessEqual(entry["attempts"], entry["attempt_limit"])
                self.assertEqual(
                    shuffled.audit["totals"]["accepted"],
                    sum(entry["accepted"] for entry in shuffled.audit["contexts"]),
                )
                self.assertEqual(shuffled.audit["shuffle_seed"], seed)
                self.assertFalse(shuffled.audit["model_rng_consumed"])
                self.assertFalse(shuffled.audit["process_hash_iteration_used"])
                self.assertFalse(shuffled.audit["preserves_reverse_edge_symmetry"])

    def test_each_accepted_swap_preserves_degrees(self) -> None:
        layout = gvs_graph.context_layout(self.dataset.key_array, self.graph.edges)
        context = layout.contexts[0]
        local = self.graph.edges[layout.edge_indices[context]]
        inverse = {
            int(value): index
            for index, value in enumerate(layout.node_indices[context].tolist())
        }
        local_edges = [
            (inverse[int(source)], inverse[int(target)]) for source, target in local.tolist()
        ]
        baseline = self._local_degrees(local_edges)
        for accept_factor in (1, 2, 5, 10):
            result = gvs_shuffle.swap_context_edges(
                local_edges, seed_sequence=(0, int(context[0])), accept_factor=accept_factor
            )
            self.assertEqual(result["accepted"], accept_factor * len(local_edges))
            self.assertEqual(
                self._local_degrees(
                    [tuple(row) for row in result["result_edges"].tolist()]
                ),
                baseline,
            )

    def _local_degrees(self, edges) -> tuple:
        node_count = len({node for edge in edges for node in edge})
        incoming = [0] * (max(node for edge in edges for node in edge) + 1)
        outgoing = [0] * len(incoming)
        for source, target in edges:
            outgoing[source] += 1
            incoming[target] += 1
        return tuple(incoming), tuple(outgoing)

    def test_reproducible_across_row_order_and_seed(self) -> None:
        other_root = Path(tempfile.mkdtemp(prefix="gvs-shuffle-order-"))
        other = fixtures.build_fixture(other_root, "region", row_order_seed=99)
        other_dataset, other_graph = fixtures.load_fixture(other)
        np.testing.assert_array_equal(
            self.dataset.key_array, other_dataset.key_array
        )
        np.testing.assert_array_equal(self.graph.edges, other_graph.edges)
        first = gvs_shuffle.shuffle_graph(
            "region", self.dataset.key_array, self.graph.edges, 1
        )
        second = gvs_shuffle.shuffle_graph(
            "region", other_dataset.key_array, other_graph.edges, 1
        )
        np.testing.assert_array_equal(first.edges, second.edges)
        self.assertEqual(
            first.audit["result_edges_sha256"], second.audit["result_edges_sha256"]
        )
        self.assertEqual(
            first.audit["source_edges_sha256"], second.audit["source_edges_sha256"]
        )
        # A different shuffle seed produces a different control graph.
        third = gvs_shuffle.shuffle_graph(
            "region", self.dataset.key_array, self.graph.edges, 2
        )
        self.assertNotEqual(
            first.audit["result_edges_sha256"], third.audit["result_edges_sha256"]
        )

    def test_reproducible_across_process_hash_seed(self) -> None:
        script = (
            "import json,sys;"
            "from benchmark.graph_value_skeleton import data, graph, shuffle;"
            "ds=data.load_dataset('region', demand_path=sys.argv[1], published=False);"
            "g=graph.load_graph('region', ds.key_array, graph_path=sys.argv[2], published=False);"
            "s=shuffle.shuffle_graph('region', ds.key_array, g.edges, 2);"
            "print(s.audit['result_edges_sha256'])"
        )
        expected = gvs_shuffle.shuffle_graph(
            "region", self.dataset.key_array, self.graph.edges, 2
        ).audit["result_edges_sha256"]
        hashes = set()
        for hash_seed in ("1", "271828"):
            environment = dict(os.environ)
            environment["PYTHONHASHSEED"] = hash_seed
            environment["PYTHONPATH"] = str(protocol.REPO_ROOT)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    script,
                    str(self.fixture["demand_path"]),
                    str(self.fixture["graph_path"]),
                ],
                cwd=str(protocol.REPO_ROOT),
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            hashes.add(completed.stdout.strip())
        self.assertEqual(hashes, {expected})

    def test_empty_context_recorded_and_unsupported_seed_rejected(self) -> None:
        keys = [(context, skill) for context in (0, 1, 2) for skill in range(4)]
        signal = np.arange(len(keys) * 36, dtype=np.float32).reshape(len(keys), 36)
        rows = [
            (context, source, target)
            for context in (0, 1)
            for source, target in fixtures.CONTEXT_EDGES["r2"]
        ]
        root = Path(tempfile.mkdtemp(prefix="gvs-shuffle-empty-"))
        fixture = fixtures.build_fixture(
            root, "r2", keys=keys, signal=signal, graph_rows=rows
        )
        dataset, graph = fixtures.load_fixture(fixture)
        shuffled = gvs_shuffle.shuffle_graph(
            "r2", dataset.key_array, graph.edges, 0
        )
        empty = [entry for entry in shuffled.audit["contexts"] if entry["empty"]]
        self.assertEqual(len(empty), 1)
        self.assertEqual(empty[0]["context"], [2])
        with self.assertRaises(gvs_shuffle.ShuffleError):
            gvs_shuffle.shuffle_graph(
                "r2", dataset.key_array, graph.edges, 3
            )

    def test_failures_are_explicit_and_never_return_the_original(self) -> None:
        keys = [(0, skill) for skill in range(6)]
        signal = np.ones((6, 36), dtype=np.float32)
        root = Path(tempfile.mkdtemp(prefix="gvs-shuffle-fail-"))
        dataset = gvs_data_fixture("r0", keys, signal)
        # A single-edge context cannot be swapped.
        one = gvs_graph.from_arrays("r0", dataset.key_array, [(0, 0, 1)])
        with self.assertRaises(gvs_shuffle.ShuffleError) as context:
            gvs_shuffle.shuffle_graph("r0", dataset.key_array, one.edges, 0)
        self.assertIn("no legal endpoint swap", str(context.exception))
        # Exhausted attempt budget fails instead of silently retrying.
        two = gvs_graph.from_arrays("r0", dataset.key_array, [(0, 0, 1), (0, 2, 3)])
        with self.assertRaises(gvs_shuffle.ShuffleError) as context:
            gvs_shuffle.shuffle_graph(
                "r0", dataset.key_array, two.edges, 0,
                accept_factor=10, attempt_factor=1,
            )
        self.assertIn("budget exhausted", str(context.exception))
        # An even number of accepted swaps on a two-edge graph returns to the
        # original, which must fail rather than be labelled shuffled.
        with self.assertRaises(gvs_shuffle.ShuffleError) as context:
            gvs_shuffle.shuffle_graph(
                "r0", dataset.key_array, two.edges, 0,
                accept_factor=2, attempt_factor=100,
            )
        self.assertIn("equals the original", str(context.exception))


    def test_failure_diagnostics_name_the_failing_context(self) -> None:
        keys = [(17, skill) for skill in range(3)] + [(23, skill) for skill in range(3)]
        signal = np.arange(len(keys) * 36, dtype=np.float32).reshape(len(keys), 36) + 1.0
        dataset = gvs_data_fixture("r2", keys, signal)
        single = gvs_graph.from_arrays(
            "r2", dataset.key_array, [(17, 0, 1), (23, 0, 1)]
        )
        with self.assertRaises(gvs_shuffle.ShuffleError) as context:
            gvs_shuffle.shuffle_graph("r2", dataset.key_array, single.edges, 0)
        message = str(context.exception)
        self.assertIn("context [17]", message)
        self.assertIn("single edge", message)
        # A successful earlier context must not hide the later failing context.
        multi_keys = [(1, skill) for skill in range(4)] + [(17, skill) for skill in range(2)]
        multi_signal = (
            np.arange(len(multi_keys) * 36, dtype=np.float32).reshape(len(multi_keys), 36)
            + 1.0
        )
        multi_dataset = gvs_data_fixture("r2", multi_keys, multi_signal)
        rows = [
            (1, source, target)
            for source, target in fixtures.CONTEXT_EDGES["region"]
        ] + [(17, 0, 1)]
        multi = gvs_graph.from_arrays("r2", multi_dataset.key_array, rows)
        with self.assertRaises(gvs_shuffle.ShuffleError) as context:
            gvs_shuffle.shuffle_graph("r2", multi_dataset.key_array, multi.edges, 0)
        self.assertIn("context [17]", str(context.exception))
        # Budget exhaustion and unchanged-final failures also name the context.
        swap_keys = [(17, skill) for skill in range(4)]
        swap_signal = np.ones((4, 36), dtype=np.float32)
        swap_dataset = gvs_data_fixture("r2", swap_keys, swap_signal)
        two = gvs_graph.from_arrays(
            "r2", swap_dataset.key_array, [(17, 0, 1), (17, 2, 3)]
        )
        with self.assertRaises(gvs_shuffle.ShuffleError) as context:
            gvs_shuffle.shuffle_graph(
                "r2", swap_dataset.key_array, two.edges, 0,
                accept_factor=10, attempt_factor=1,
            )
        self.assertIn("context [17]", str(context.exception))
        self.assertIn("budget exhausted", str(context.exception))
        with self.assertRaises(gvs_shuffle.ShuffleError) as context:
            gvs_shuffle.shuffle_graph(
                "r2", swap_dataset.key_array, two.edges, 0,
                accept_factor=2, attempt_factor=100,
            )
        self.assertIn("context [17]", str(context.exception))
        self.assertIn("equals the original", str(context.exception))


    def test_rng_uses_context_id_not_ordinal(self) -> None:
        # Replicates the Appendix F probe: one context 17 with keys 0..6 and raw
        # global edges 0..5, all inside that context.
        keys = np.array([[17, skill] for skill in range(7)], dtype=np.int64)
        edges = np.array(fixtures.CONTEXT_EDGES["r0"], dtype=np.int64)
        seen = []
        original = gvs_shuffle._swap_edges

        def observe(local_edges, **kwargs):
            seen.append(
                {
                    "context": list(kwargs["context"]),
                    "seed_sequence": list(kwargs["seed_sequence"]),
                }
            )
            return original(local_edges, **kwargs)

        with mock.patch.object(gvs_shuffle, "_swap_edges", side_effect=observe):
            shuffled = gvs_shuffle.shuffle_graph("r2", keys, edges, 0)
        self.assertEqual([entry["context"] for entry in seen], [[17]])
        self.assertEqual([entry["seed_sequence"] for entry in seen], [[0, 17]])
        self.assertEqual(
            shuffled.audit["seed_derivation"],
            "PCG64(SeedSequence([shuffle_seed, context_id...]))",
        )
        self.assertEqual(
            shuffled.audit["contexts"][-1]["seed_sequence"], [0, 17]
        )
        # Context-ID oracle on the canonicalized local edges (identity mapping
        # because the only context owns nodes 0..6).
        expected_local = original(
            [tuple(int(v) for v in row) for row in edges.tolist()],
            seed_sequence=[0, 17],
            accept_factor=10,
            attempt_factor=100,
            context=[17],
        )["result_edges"]
        np.testing.assert_array_equal(shuffled.edges, expected_local)
        ordinal_local = original(
            [tuple(int(v) for v in row) for row in edges.tolist()],
            seed_sequence=[0, 1],
            accept_factor=10,
            attempt_factor=100,
            context=[17],
        )["result_edges"]
        self.assertFalse(np.array_equal(expected_local, ordinal_local))

    def test_each_nonconsecutive_context_uses_its_own_id(self) -> None:
        keys = np.array(
            [[3, skill] for skill in range(4)] + [[17, skill] for skill in range(4)],
            dtype=np.int64,
        )
        rows = [(3, a, b) for a, b in fixtures.CONTEXT_EDGES["region"]] + [
            (17, a, b) for a, b in fixtures.CONTEXT_EDGES["region"]
        ]
        graph = gvs_graph.from_arrays("r2", keys, rows)
        seen = []
        original = gvs_shuffle._swap_edges

        def observe(local_edges, **kwargs):
            seen.append(list(kwargs["seed_sequence"]))
            return original(local_edges, **kwargs)

        with mock.patch.object(gvs_shuffle, "_swap_edges", side_effect=observe):
            gvs_shuffle.shuffle_graph("r2", keys, graph.edges, 1)
        self.assertEqual(seen, [[1, 3], [1, 17]])

    def test_empty_earlier_context_still_uses_its_own_id(self) -> None:
        keys = np.array(
            [[0, 0]] + [[17, skill] for skill in range(7)], dtype=np.int64
        )
        rows = [(17, a, b) for a, b in fixtures.CONTEXT_EDGES["r0"]]
        graph = gvs_graph.from_arrays("r2", keys, rows)
        seen = []
        original = gvs_shuffle._swap_edges

        def observe(local_edges, **kwargs):
            seen.append(list(kwargs["seed_sequence"]))
            return original(local_edges, **kwargs)

        with mock.patch.object(gvs_shuffle, "_swap_edges", side_effect=observe):
            shuffled = gvs_shuffle.shuffle_graph("r2", keys, graph.edges, 0)
        self.assertEqual(seen, [[0, 0], [0, 17]])
        empty = [entry for entry in shuffled.audit["contexts"] if entry["empty"]]
        self.assertEqual(len(empty), 1)
        self.assertEqual(empty[0]["context"], [0])
        self.assertEqual(empty[0]["seed_sequence"], [0, 0])

    def test_swap_helper_canonicalizes_input_order(self) -> None:
        given = [
            tuple(int(v) for v in row) for row in fixtures.CONTEXT_EDGES["r0"]
        ]
        first = gvs_shuffle.swap_context_edges(
            given, seed_sequence=[0, 17], context=[17]
        )
        second = gvs_shuffle.swap_context_edges(
            sorted(given), seed_sequence=[0, 17], context=[17]
        )
        np.testing.assert_array_equal(
            first["result_edges"], second["result_edges"]
        )


def gvs_data_fixture(data_name, keys, signal):
    from benchmark.graph_value_skeleton import data as gvs_data

    return gvs_data.from_fixture(data_name, keys, signal)


if __name__ == "__main__":
    unittest.main()
