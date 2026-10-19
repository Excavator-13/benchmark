"""Fixed 200-epoch budget, chunked global-MSE gradients and MSE selection.

Covers tasks 5.2 and 5.3.
"""

from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import torch

from benchmark.graph_value_skeleton import graph as gvs_graph
from benchmark.graph_value_skeleton import model as gvs_model
from benchmark.graph_value_skeleton import protocol
from benchmark.graph_value_skeleton import runner
from benchmark.graph_value_skeleton import shuffle as gvs_shuffle
from benchmark.graph_value_skeleton import training
from benchmark.graph_value_skeleton.tests import fixtures


def _prepare(fixture, *, method="graph"):
    dataset, graph = fixtures.load_fixture(fixture)
    layout = gvs_graph.context_layout(dataset.key_array, graph.edges)
    chunks = training.build_chunks(layout, node_count=dataset.node_count)
    if method == "self":
        chunks = [
            training.Chunk(
                window_index=chunk.window_index,
                window_start=chunk.window_start,
                context=chunk.context,
                node_indices=chunk.node_indices,
                aggregation=gvs_model.GraphAggregation.identity(
                    int(chunk.node_indices.numel()), label="self"
                ),
                element_count=chunk.element_count,
            )
            for chunk in chunks
        ]
    return dataset, graph, chunks


def _full_batch_gradient(model, dataset, aggregation, chunks):
    """One forward/backward over every window and node with full adjacency."""
    model.zero_grad(set_to_none=True)
    inputs = dataset.input_windows(protocol.TRAIN_STARTS)
    targets = dataset.target_windows(protocol.TRAIN_STARTS)
    total = len(protocol.TRAIN_STARTS) * dataset.node_count * protocol.HORIZON
    loss = 0.0
    for index in range(inputs.shape[0]):
        x = torch.as_tensor(inputs[index], dtype=torch.float32)
        y = torch.as_tensor(targets[index], dtype=torch.float32)
        prediction = model(x, aggregation)
        loss = loss + torch.square(prediction - y).sum() / float(total)
    loss.backward()
    return {
        name: parameter.grad.detach().clone()
        for name, parameter in model.named_parameters()
    }


class GradientTest(unittest.TestCase):
    def _compare(self, fixture) -> None:
        dataset, graph, chunks = _prepare(fixture)
        training.configure_determinism(0)
        model = gvs_model.build_model(0)
        aggregation = gvs_model.GraphAggregation.from_edges(
            graph.edges, dataset.node_count, label="full"
        )
        full = _full_batch_gradient(model, dataset, aggregation, chunks)
        # Accumulated chunk gradient.
        training.configure_determinism(0)
        chunked_model = gvs_model.build_model(0)
        chunked_model.zero_grad(set_to_none=True)
        inputs = dataset.input_windows(protocol.TRAIN_STARTS)
        targets = dataset.target_windows(protocol.TRAIN_STARTS)
        total = len(protocol.TRAIN_STARTS) * dataset.node_count * protocol.HORIZON
        for chunk in chunks:
            x = torch.as_tensor(inputs[chunk.window_index], dtype=torch.float32).index_select(
                0, chunk.node_indices
            )
            y = torch.as_tensor(targets[chunk.window_index], dtype=torch.float32).index_select(
                0, chunk.node_indices
            )
            prediction = chunked_model(x, chunk.aggregation)
            (torch.square(prediction - y).sum() / float(total)).backward()
        for name, parameter in chunked_model.named_parameters():
            difference = (parameter.grad - full[name]).abs()
            scale = torch.maximum(
                torch.ones_like(difference),
                torch.maximum(parameter.grad.abs(), full[name].abs()),
            )
            self.assertLessEqual(float((difference / scale).max()), 1e-6, name)

    def test_chunked_gradient_equals_full_batch(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-grad-"))
        self._compare(fixtures.build_fixture(root, "region"))

    def test_unequal_context_sizes_are_element_weighted(self) -> None:
        keys = [(0, skill) for skill in range(4)] + [(1, skill) for skill in range(2)]
        signal = np.arange(len(keys) * 36, dtype=np.float32).reshape(len(keys), 36) + 1.0
        rows = [
            (0, 0, 1), (0, 1, 2), (0, 2, 3), (0, 3, 0), (0, 0, 2), (0, 1, 3),
            (1, 0, 1), (1, 1, 0),
        ]
        root = Path(tempfile.mkdtemp(prefix="gvs-grad-unequal-"))
        fixture = fixtures.build_fixture(root, "r2", keys=keys, signal=signal, graph_rows=rows)
        self._compare(fixture)

    def test_chunks_follow_ascending_window_then_context(self) -> None:
        fixture = fixtures.build_fixture(
            Path(tempfile.mkdtemp(prefix="gvs-chunks-")), "region"
        )
        dataset, graph, chunks = _prepare(fixture)
        self.assertEqual(len(chunks), len(protocol.TRAIN_STARTS) * 2)
        ordered = [(chunk.window_index, chunk.context) for chunk in chunks]
        self.assertEqual(ordered, sorted(ordered))
        self.assertEqual(
            sum(chunk.element_count for chunk in chunks),
            len(protocol.TRAIN_STARTS) * dataset.node_count * protocol.HORIZON,
        )


class BudgetAndSelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(tempfile.mkdtemp(prefix="gvs-train-"))
        cls.fixture = fixtures.build_fixture(cls.root, "r0")
        cls.dataset, cls.graph, cls.chunks = _prepare(cls.fixture)
        training.configure_determinism(0)
        cls.model = gvs_model.build_model(0)
        cls.result, cls.steps = cls._run()

    @classmethod
    def _run(cls):
        counter = {"steps": 0}

        class CountingAdam(torch.optim.Adam):
            def step(self, closure=None):
                counter["steps"] += 1
                return super().step(closure)

        with mock.patch.object(torch.optim, "Adam", CountingAdam):
            result = training.train(
                cls.model,
                train_inputs=cls.dataset.input_windows(protocol.TRAIN_STARTS),
                train_targets=cls.dataset.target_windows(protocol.TRAIN_STARTS),
                validation_inputs=cls.dataset.input_windows(protocol.VALIDATION_STARTS),
                validation_targets=cls.dataset.target_windows(protocol.VALIDATION_STARTS),
                chunks=cls.chunks,
                validation_aggregation=gvs_model.GraphAggregation.from_edges(
                    cls.graph.edges, cls.dataset.node_count
                ),
                node_count=cls.dataset.node_count,
            )
        return result, counter["steps"]

    def test_exactly_200_epochs_and_steps(self) -> None:
        self.assertEqual(len(self.result.history), protocol.EPOCHS)
        self.assertEqual(self.steps, protocol.EPOCHS)
        self.assertEqual(self.result.epochs, 200)
        for index, row in enumerate(self.result.history):
            self.assertEqual(row["epoch"], index + 1)
            self.assertEqual(row["optimizer_step"], index + 1)
            self.assertEqual(
                row["train_elements"],
                len(protocol.TRAIN_STARTS) * self.dataset.node_count * protocol.HORIZON,
            )
            self.assertIsInstance(row["validation_MSE_original_units_after_update"], float)
        self.assertEqual(self.result.selection_payload["optimizer"]["steps_per_epoch"], 1)
        self.assertIsNone(self.result.selection_payload["scheduler"])
        self.assertFalse(self.result.selection_payload["early_stopping"])
        self.assertIsNone(self.result.selection_payload["gradient_clipping"])
        self.assertEqual(self.result.selection_payload["optimizer"]["lr"], 1e-3)
        self.assertEqual(self.result.selection_payload["optimizer"]["betas"], [0.9, 0.999])
        self.assertEqual(self.result.selection_payload["optimizer"]["eps"], 1e-8)
        self.assertEqual(self.result.selection_payload["optimizer"]["weight_decay"], 0.0)

    def test_selection_uses_validation_mse_not_mae(self) -> None:
        history = self.result.history
        mse_epoch = min(
            history, key=lambda row: (row["validation_MSE_original_units_after_update"], row["epoch"])
        )["epoch"]
        self.assertEqual(self.result.selected_epoch, mse_epoch)
        mae_epoch = min(
            history, key=lambda row: (row["validation_MAE_original_units_after_update"], row["epoch"])
        )["epoch"]
        # The MAE winner is allowed to differ; selection must still follow MSE.
        self.assertEqual(
            self.result.selected_epoch,
            training._earliest_minimum(history),
        )
        self.assertEqual(self.result.selection_payload["selected_is_earliest_minimum"], True)
        if mae_epoch != mse_epoch:
            self.assertNotEqual(self.result.selected_epoch, mae_epoch)
        self.assertEqual(
            self.result.selected_validation_mse,
            history[self.result.selected_epoch - 1][
                "validation_MSE_original_units_after_update"
            ],
        )

    def test_exact_tie_selects_earliest_epoch(self) -> None:
        rows = [
            {"epoch": 1, "validation_MSE_original_units_after_update": 4.0},
            {"epoch": 2, "validation_MSE_original_units_after_update": 2.0},
            {"epoch": 3, "validation_MSE_original_units_after_update": 2.0},
            {"epoch": 4, "validation_MSE_original_units_after_update": 3.0},
        ]
        self.assertEqual(training._earliest_minimum(rows), 2)
        self.assertEqual(self.result.selection_payload["tie_break"], "earliest epoch on an exact validation-MSE tie")

    def test_test_labels_are_not_accepted_by_training(self) -> None:
        signature = inspect.signature(training.train)
        for name in signature.parameters:
            self.assertNotIn("test", name)
        self.assertNotIn("test", inspect.signature(training.selected_predictions).parameters)
        self.assertFalse(self.result.selection_payload["test_labels_used_for_selection"])
        self.assertFalse(self.result.selection_payload["test_labels_available_to_training"])

    def test_budget_is_not_configurable(self) -> None:
        with self.assertRaises(training.TrainingError):
            training.train(
                self.model,
                train_inputs=self.dataset.input_windows(protocol.TRAIN_STARTS),
                train_targets=self.dataset.target_windows(protocol.TRAIN_STARTS),
                validation_inputs=self.dataset.input_windows(protocol.VALIDATION_STARTS),
                validation_targets=self.dataset.target_windows(protocol.VALIDATION_STARTS),
                chunks=self.chunks,
                validation_aggregation=None,
                epochs=5,
                node_count=self.dataset.node_count,
            )


class TestTargetIsolationTest(unittest.TestCase):
    """Perturbing only test targets cannot change training or selection."""

    def test_test_targets_do_not_affect_selection(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-isolation-"))
        fixture = fixtures.build_fixture(root, "r0")
        dataset, graph, chunks = _prepare(fixture)
        aggregation = gvs_model.GraphAggregation.from_edges(
            graph.edges, dataset.node_count
        )

        def run_once():
            training.configure_determinism(0)
            model = gvs_model.build_model(0)
            result = training.train(
                model,
                train_inputs=dataset.input_windows(protocol.TRAIN_STARTS),
                train_targets=dataset.target_windows(protocol.TRAIN_STARTS),
                validation_inputs=dataset.input_windows(protocol.VALIDATION_STARTS),
                validation_targets=dataset.target_windows(protocol.VALIDATION_STARTS),
                chunks=chunks,
                validation_aggregation=aggregation,
                node_count=dataset.node_count,
            )
            validation, test = training.selected_predictions(
                model,
                result.selected_state,
                validation_inputs=dataset.input_windows(protocol.VALIDATION_STARTS),
                test_inputs=dataset.input_windows(protocol.TEST_STARTS),
                validation_aggregation=aggregation,
                test_aggregation=aggregation,
            )
            return result, test

        first, test_prediction = run_once()
        test_targets = dataset.target_windows(protocol.TEST_STARTS)
        perturbed_targets = test_targets + np.float32(1000.0)
        self.assertFalse(np.array_equal(test_targets, perturbed_targets))
        second, test_prediction_again = run_once()
        self.assertEqual(first.selected_epoch, second.selected_epoch)
        self.assertEqual(first.history, second.history)
        np.testing.assert_array_equal(test_prediction, test_prediction_again)
        for name, tensor in first.selected_state.items():
            self.assertTrue(torch.equal(tensor, second.selected_state[name]))


class ShuffledTrainingTest(unittest.TestCase):
    """The shuffled branch must train on the shuffled adjacency (V-001)."""

    def test_chunks_use_the_shuffled_adjacency_for_every_window(self) -> None:
        fixture = fixtures.build_fixture(
            Path(tempfile.mkdtemp(prefix="gvs-shuffled-train-")), "region"
        )
        dataset, graph = fixtures.load_fixture(fixture)
        shuffled = gvs_shuffle.shuffle_graph(
            "region", dataset.key_array, graph.edges, 0
        )
        self.assertFalse(np.array_equal(shuffled.edges, graph.edges))
        layout = gvs_graph.context_layout(dataset.key_array, shuffled.edges)
        chunks = training.build_chunks(layout, node_count=dataset.node_count)
        per_window = training.chunk_global_edges(chunks)
        self.assertEqual(sorted(per_window), list(range(len(protocol.TRAIN_STARTS))))
        for window, edges in per_window.items():
            np.testing.assert_array_equal(edges, shuffled.edges, err_msg=f"window {window}")
        inputs = dataset.input_windows(protocol.TRAIN_STARTS)
        targets = dataset.target_windows(protocol.TRAIN_STARTS)
        total = len(protocol.TRAIN_STARTS) * dataset.node_count * protocol.HORIZON
        training.configure_determinism(0)
        chunked_model = gvs_model.build_model(0)
        chunked_model.zero_grad(set_to_none=True)
        for chunk in chunks:
            x = torch.as_tensor(
                inputs[chunk.window_index], dtype=torch.float32
            ).index_select(0, chunk.node_indices)
            y = torch.as_tensor(
                targets[chunk.window_index], dtype=torch.float32
            ).index_select(0, chunk.node_indices)
            prediction = chunked_model(x, chunk.aggregation)
            (torch.square(prediction - y).sum() / float(total)).backward()
        shuffled_aggregation = gvs_model.GraphAggregation.from_edges(
            shuffled.edges, dataset.node_count
        )
        training.configure_determinism(0)
        shuffled_full = _full_batch_gradient(
            gvs_model.build_model(0), dataset, shuffled_aggregation, chunks
        )
        original_aggregation = gvs_model.GraphAggregation.from_edges(
            graph.edges, dataset.node_count
        )
        training.configure_determinism(0)
        original_full = _full_batch_gradient(
            gvs_model.build_model(0), dataset, original_aggregation, chunks
        )
        differs = False
        for name, parameter in chunked_model.named_parameters():
            difference = (parameter.grad - shuffled_full[name]).abs()
            scale = torch.maximum(
                torch.ones_like(difference),
                torch.maximum(parameter.grad.abs(), shuffled_full[name].abs()),
            )
            self.assertLessEqual(float((difference / scale).max()), 1e-6, name)
            original_difference = (shuffled_full[name] - original_full[name]).abs()
            original_scale = torch.maximum(
                torch.ones_like(original_difference),
                torch.maximum(shuffled_full[name].abs(), original_full[name].abs()),
            )
            if float((original_difference / original_scale).max()) > 1e-6:
                differs = True
        self.assertTrue(
            differs,
            "the original-adjacency gradient must differ from the shuffled oracle",
        )

    def test_runner_trains_with_the_saved_shuffled_graph(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-shuffled-runner-"))
        fixture = fixtures.build_fixture(root, "region")
        _, original = fixtures.load_fixture(fixture)
        seen = {}
        real_train = training.train

        def observe(model, **kwargs):
            seen["chunks"] = kwargs["chunks"]
            return real_train(model, **kwargs)

        config = fixtures.make_config(
            root, fixture, method="shuffled", shuffle_seed=0, run_id="shuffled-training"
        )
        with mock.patch.object(training, "train", side_effect=observe):
            result = runner.execute_run(config)
        run_dir = Path(result["run_dir"])
        saved = np.load(run_dir / "graph/edges.npy", allow_pickle=False)
        self.assertFalse(np.array_equal(saved, original.edges))
        per_window = training.chunk_global_edges(seen["chunks"])
        for window, edges in per_window.items():
            np.testing.assert_array_equal(edges, saved, err_msg=f"window {window}")
        selection = fixtures.read_json(run_dir / "selection.json")
        provenance = fixtures.read_json(run_dir / "provenance.json")
        expected = gvs_graph.edge_set_sha256(saved)
        self.assertEqual(selection["training_edges"]["edges_sha256"], expected)
        self.assertEqual(
            provenance["graph_used"]["training_edges"]["edges_sha256"], expected
        )
        self.assertEqual(provenance["graph_used"]["message_edges_sha256"], expected)


if __name__ == "__main__":
    unittest.main()
