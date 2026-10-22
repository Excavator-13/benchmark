"""Frozen encoder, propagation operator, parameter isomorphism and CPU runtime.

Covers tasks 3.1-3.4: vectorization equivalence, per-node/window state reset,
asymmetric incoming-mean direction, exact isolated/empty-graph equality, the
3459-parameter isomorphism, RNG separation and a CPU-only forward/backward run
with graph extensions unavailable.
"""

from __future__ import annotations

import unittest
from unittest import mock

import numpy as np
import torch

from benchmark.graph_value_skeleton import model as gvs_model
from benchmark.graph_value_skeleton import protocol
from benchmark.graph_value_skeleton import shuffle as gvs_shuffle
from benchmark.graph_value_skeleton import training
from benchmark.graph_value_skeleton.tests import fixtures


def normalized(a: torch.Tensor, b: torch.Tensor) -> float:
    difference = (a - b).abs()
    scale = torch.maximum(
        torch.ones_like(difference), torch.maximum(a.abs(), b.abs())
    )
    return float((difference / scale).max())


class EncoderTest(unittest.TestCase):
    def setUp(self) -> None:
        training.configure_determinism(0)
        self.model = gvs_model.build_model(0)
        rng = np.random.default_rng(7)
        self.inputs = torch.as_tensor(
            rng.uniform(0.0, 40.0, size=(5, protocol.INPUT_LENGTH)), dtype=torch.float32
        )

    def test_vectorization_equals_per_node_loop(self) -> None:
        batch = self.model.encode(self.inputs)
        self.assertEqual(tuple(batch.shape), (5, protocol.HIDDEN_DIM))
        looped = torch.cat(
            [self.model.encode(self.inputs[index : index + 1]) for index in range(5)],
            dim=0,
        )
        self.assertLessEqual(normalized(batch, looped), 1e-6)
        predictions = self.model.head(batch)
        looped_predictions = torch.cat(
            [
                self.model.head(self.model.encode(self.inputs[index : index + 1]))
                for index in range(5)
            ],
            dim=0,
        )
        self.assertLessEqual(normalized(predictions, looped_predictions), 1e-6)
        self.assertEqual(tuple(predictions.shape), (5, protocol.HORIZON))

    def test_node_inputs_are_isolated(self) -> None:
        baseline = self.model.encode(self.inputs)
        perturbed = self.inputs.clone()
        perturbed[1] = perturbed[1] + 17.0
        after = self.model.encode(perturbed)
        self.assertTrue(torch.equal(baseline[0], after[0]))
        self.assertTrue(torch.equal(baseline[2], after[2]))
        self.assertFalse(torch.equal(baseline[1], after[1]))

    def test_window_and_split_state_reset(self) -> None:
        window_a = self.inputs[:2]
        window_b = self.inputs[:2] + 3.0
        first = self.model.encode(window_a)
        self.model.encode(window_b)
        second = self.model.encode(window_a)
        self.assertTrue(torch.equal(first, second))
        # Evaluating one window alone matches evaluating it after another window.
        alone = gvs_model.predict_windows(
            self.model, window_b.unsqueeze(0)
        )
        after = gvs_model.predict_windows(
            self.model, torch.stack([window_a, window_b])
        )
        self.assertLessEqual(normalized(alone[0], after[1]), 1e-6)

    def test_batched_graph_predictions_match_per_window_oracle(self) -> None:
        training.configure_determinism(0)
        model = gvs_model.build_model(0)
        inputs = (
            torch.arange(4 * 3 * 6, dtype=torch.float32).reshape(4, 3, 6) / 10.0
        )
        for edges in ([[0, 1], [2, 1], [1, 2]], [], [[0, 1]]):
            with self.subTest(edges=edges):
                aggregation = gvs_model.GraphAggregation.from_edges(edges, 3)
                batched = gvs_model.predict_windows(model, inputs, aggregation)
                oracle = torch.stack(
                    [
                        gvs_model.predict(model, inputs[window], aggregation)
                        for window in range(4)
                    ]
                )
                self.assertLessEqual(normalized(batched, oracle), 1e-6)
                self_prediction = gvs_model.predict_windows(model, inputs)
                if not edges:
                    self.assertTrue(torch.equal(batched, self_prediction))
                    continue
                for window in range(4):
                    if edges == [[0, 1]]:
                        self.assertTrue(
                            torch.equal(batched[window, 0], self_prediction[window, 0])
                        )
                        self.assertTrue(
                            torch.equal(batched[window, 2], self_prediction[window, 2])
                        )
                        self.assertFalse(
                            torch.equal(batched[window, 1], self_prediction[window, 1])
                        )
                    else:
                        self.assertFalse(
                            torch.equal(batched[window], self_prediction[window])
                        )

    def test_three_methods_share_initial_parameters(self) -> None:
        states = {}
        for method in protocol.METHODS:
            model = gvs_model.build_model(3)
            states[method] = {
                name: tensor.clone() for name, tensor in model.state_dict().items()
            }
        reference = states[protocol.METHOD_SELF]
        for method in protocol.METHODS:
            for name, tensor in states[method].items():
                self.assertTrue(torch.equal(reference[name], tensor), name)


class PropagationTest(unittest.TestCase):
    def test_asymmetric_direction_oracle(self) -> None:
        hidden = torch.tensor(
            [
                [1.0, 2.0, 3.0, 4.0],
                [10.0, 20.0, 30.0, 40.0],
                [100.0, 200.0, 300.0, 400.0],
                [0.5, 0.25, 0.125, 0.0625],
            ],
            dtype=torch.float32,
        )
        aggregation = gvs_model.GraphAggregation.from_edges(
            [[0, 1], [2, 1], [1, 2]], hidden.shape[0], label="asymmetric"
        )
        result = aggregation.apply(hidden)
        expected = hidden.clone()
        expected[1] = hidden[1] + (hidden[0] + hidden[2]) / 2.0
        expected[2] = hidden[2] + hidden[1]
        expected[0] = hidden[0]
        self.assertTrue(torch.allclose(result, expected, rtol=0, atol=1e-6))
        # An outgoing-neighbour implementation gives a different answer.
        outgoing = gvs_model.GraphAggregation.from_edges(
            [[1, 0], [1, 2], [2, 1]], hidden.shape[0], label="outgoing"
        ).apply(hidden)
        self.assertFalse(torch.allclose(result, outgoing, rtol=0, atol=1e-6))
        self.assertTrue(torch.equal(result[3], hidden[3]))

    def test_duplicate_rows_do_not_weight_a_neighbour(self) -> None:
        keys = [(0, skill) for skill in range(3)]
        signal = np.ones((3, 36), dtype=np.float32)
        rows = [(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 2, 1)]
        from benchmark.graph_value_skeleton import data as gvs_data
        from benchmark.graph_value_skeleton import graph as gvs_graph

        dataset = gvs_data.from_fixture("r0", keys, signal)
        graph = gvs_graph.from_arrays("r0", dataset.key_array, rows)
        self.assertEqual(graph.unique_edges, 2)
        self.assertEqual(graph.multiplicity["distribution"], {"1": 1, "3": 1})
        hidden = torch.tensor(
            [[0.0, 2.0], [100.0, 100.0], [4.0, 6.0]], dtype=torch.float32
        )
        aggregation = gvs_model.GraphAggregation.from_edges(
            graph.edges, hidden.shape[0], label="deduplicated"
        )
        result = aggregation.apply(hidden)
        self.assertTrue(
            torch.allclose(
                result[1], hidden[1] + (hidden[0] + hidden[2]) / 2.0, atol=0, rtol=0
            )
        )

    def test_self_loops_rejected(self) -> None:
        with self.assertRaises(gvs_model.ModelError):
            gvs_model.GraphAggregation.from_edges([[0, 0]], 2, label="loop")

    def test_isolated_and_empty_graph_exact_equality(self) -> None:
        training.configure_determinism(1)
        model = gvs_model.build_model(1)
        rng = np.random.default_rng(11)
        inputs = torch.as_tensor(rng.uniform(0.0, 9.0, (4, 6)), dtype=torch.float32)
        graph_only = gvs_model.GraphAggregation.from_edges([[0, 1]], 4, label="out-only")
        self_prediction = model(inputs, None)
        graph_prediction = model(inputs, graph_only)
        # Node 0 has only an outgoing edge and node 3 is isolated: residual 0.
        self.assertTrue(torch.equal(graph_prediction[0], self_prediction[0]))
        self.assertTrue(torch.equal(graph_prediction[3], self_prediction[3]))
        self.assertFalse(torch.equal(graph_prediction[1], self_prediction[1]))
        empty = gvs_model.GraphAggregation.from_edges([], 4, label="empty")
        self.assertTrue(torch.equal(model(inputs, empty), self_prediction))
        # The operator itself returns the identical hidden tensor.
        hidden = model.encode(inputs)
        self.assertTrue(torch.equal(empty.apply(hidden), hidden))

    def test_no_graph_parameter_capacity(self) -> None:
        signatures = {}
        counts = {}
        for node_count, edges in ((4, [[0, 1]]), (12, [[0, 1], [2, 3], [5, 6]])):
            training.configure_determinism(5)
            model = gvs_model.build_model(5)
            signatures[node_count] = gvs_model.parameter_signature(model)
            counts[node_count] = gvs_model.parameter_counts(model)
            self.assertEqual(
                gvs_model.graph_only_parameter_names(model), []
            )
            self.assertEqual(
                counts[node_count],
                {"gru": 3360, "head": 99, "graph_only": 0, "total": 3459},
            )
        self.assertEqual(signatures[4], signatures[12])
        self.assertEqual(protocol.PARAMETER_COUNTS["total"], 3459)

    def test_shuffle_does_not_consume_model_rng(self) -> None:
        training.configure_determinism(2)
        before = torch.random.get_rng_state().clone()
        fixture = fixtures.build_fixture(
            __import__("pathlib").Path(
                __import__("tempfile").mkdtemp(prefix="gvs-rng-")
            ),
            "region",
        )
        dataset, graph = fixtures.load_fixture(fixture)
        gvs_shuffle.shuffle_graph("region", dataset.key_array, graph.edges, 0)
        after = torch.random.get_rng_state()
        self.assertTrue(torch.equal(before, after))
        model_after_shuffle = gvs_model.build_model(2)
        training.configure_determinism(2)
        model_direct = gvs_model.build_model(2)
        for name, tensor in model_direct.state_dict().items():
            self.assertTrue(torch.equal(tensor, model_after_shuffle.state_dict()[name]))

    def test_training_state_is_independent_per_model(self) -> None:
        training.configure_determinism(4)
        first = gvs_model.build_model(4)
        second = gvs_model.build_model(4)
        snapshot = {name: tensor.clone() for name, tensor in second.state_dict().items()}
        optimizer = torch.optim.Adam(first.parameters(), lr=1e-3)
        inputs = torch.ones(3, 6)
        loss = torch.square(first(inputs, None)).mean()
        loss.backward()
        optimizer.step()
        for name, tensor in second.state_dict().items():
            self.assertTrue(torch.equal(tensor, snapshot[name]))


class CpuRuntimeTest(unittest.TestCase):
    def test_determinism_settings(self) -> None:
        settings = training.configure_determinism(0)
        self.assertEqual(settings["torch_intra_op_threads"], 1)
        self.assertEqual(settings["torch_inter_op_threads"], 1)
        self.assertTrue(settings["torch_deterministic_algorithms"])
        self.assertTrue(torch.are_deterministic_algorithms_enabled())
        for value in settings["blas_thread_environment"].values():
            self.assertEqual(value, "1")

    def test_real_cpu_forward_backward_without_graph_extensions(self) -> None:
        import torch.cuda

        if torch.cuda.is_available():  # pragma: no cover - pinned CPU env
            self.skipTest("this environment exposes CUDA; the pinned CPU runtime is required")
        blocked = {
            name: None
            for name in ("torch_geometric", "dgl", "torch_scatter", "torch_sparse")
        }
        with mock.patch.dict("sys.modules", blocked):
            training.configure_determinism(0)
            model = gvs_model.build_model(0)
            inputs = torch.rand(6, 6) * 10.0
            targets = torch.rand(6, 3)
            aggregation = gvs_model.GraphAggregation.from_edges(
                [[0, 1], [1, 2], [2, 0]], 6, label="cpu"
            )
            optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
            loss = torch.square(model(inputs, aggregation) - targets).mean()
            loss.backward()
            optimizer.step()
            self.assertTrue(bool(torch.isfinite(loss)))
            self.assertFalse(torch.cuda.is_available())
        import sys

        for name in ("torch_geometric", "dgl", "torch_scatter", "torch_sparse"):
            self.assertNotIn(name, sys.modules)
        from benchmark.graph_value_skeleton import artifacts

        environment = artifacts.capture_environment(protocol.REPO_ROOT)
        self.assertFalse(environment["gpu_available"])
        self.assertFalse(environment["torch"]["cuda_available"])
        for name, record in environment["graph_extensions"].items():
            # Availability is recorded truthfully; the entry never imports or uses
            # a graph extension (the blocked-import forward/backward above proves
            # the model path does not require any of them).
            self.assertFalse(record["used_by_this_entry"], name)
            self.assertFalse(record["imported_in_this_process"], name)
        self.assertEqual(environment["packages"]["torch"], torch.__version__)
        self.assertIn(environment["packages"]["torch"], ("2.14.1", "2.14.1+cpu"))
        self.assertEqual(environment["packages"]["numpy"], "1.26.4")
        self.assertEqual(environment["python_version_info"][:3], [3, 11, 17])


if __name__ == "__main__":
    unittest.main()
