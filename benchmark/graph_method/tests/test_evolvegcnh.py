"""Unit tests for the local EvolveGCN-H layer (tasks 2.1, 2.2 and 2.3)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import torch  # noqa: E402

from models.evolvegcnh import EvolveGCNH  # noqa: E402

CUDA_AVAILABLE = torch.cuda.is_available()
CUDA_REASON = "CUDA is not available in this environment"


def make_layer(num_of_nodes=64, in_channels=4):
    torch.manual_seed(0)
    return EvolveGCNH(num_of_nodes, in_channels)


def make_batch(num_of_nodes=64, in_channels=4):
    X = torch.randn(num_of_nodes, in_channels)
    edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 0]], dtype=torch.long)
    edge_weight = torch.ones(edge_index.shape[1])
    return X, edge_index, edge_weight


class RecordingGRU:
    """Wrap a GRU so tests can observe the hidden state passed into each call."""

    def __init__(self, layer):
        self.layer = layer
        self.received = []
        self._original = layer.recurrent_layer.forward
        layer.recurrent_layer.forward = self._record

    def _record(self, input, hx):
        self.received.append(hx.detach().clone())
        return self._original(input, hx)

    def restore(self):
        self.layer.recurrent_layer.forward = self._original


class RecurrenceTests(unittest.TestCase):
    """Task 2.1: the weight evolves across snapshots."""

    def test_first_snapshot_uses_initial_weight(self):
        layer = make_layer()
        X, edge_index, edge_weight = make_batch()
        recorder = RecordingGRU(layer)
        self.addCleanup(recorder.restore)

        _, next_weight = layer(X, edge_index, edge_weight, previous_weight=None)

        self.assertEqual(len(recorder.received), 1)
        torch.testing.assert_close(
            recorder.received[0].squeeze(0), layer.initial_weight.detach()
        )
        self.assertEqual(tuple(next_weight.shape), (4, 4))

    def test_second_snapshot_receives_first_evolved_weight(self):
        layer = make_layer()
        X, edge_index, edge_weight = make_batch()
        recorder = RecordingGRU(layer)
        self.addCleanup(recorder.restore)

        _, first_weight = layer(X, edge_index, edge_weight, previous_weight=None)
        _, second_weight = layer(X, edge_index, edge_weight, previous_weight=first_weight)

        self.assertEqual(len(recorder.received), 2)
        torch.testing.assert_close(recorder.received[1].squeeze(0), first_weight.detach())
        self.assertFalse(
            torch.allclose(first_weight.detach(), layer.initial_weight.detach()),
            "the GRU must actually evolve the weight",
        )
        self.assertFalse(torch.allclose(second_weight.detach(), first_weight.detach()))

    def test_third_snapshot_chains_from_the_second(self):
        layer = make_layer()
        X, edge_index, edge_weight = make_batch()
        recorder = RecordingGRU(layer)
        self.addCleanup(recorder.restore)

        _, first = layer(X, edge_index, edge_weight)
        _, second = layer(X, edge_index, edge_weight, previous_weight=first)
        _, _ = layer(X, edge_index, edge_weight, previous_weight=second)

        torch.testing.assert_close(recorder.received[2].squeeze(0), second.detach())

    def test_layer_does_not_store_mutable_weight(self):
        layer = make_layer()
        X, edge_index, edge_weight = make_batch()
        self.assertFalse(hasattr(layer, "weight"))
        layer(X, edge_index, edge_weight)
        self.assertFalse(hasattr(layer, "weight"))

    def test_forward_returns_evolved_weight_every_call(self):
        layer = make_layer()
        X, edge_index, edge_weight = make_batch()
        result = layer(X, edge_index, edge_weight)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        X_out, weight = result
        self.assertEqual(tuple(X_out.shape), (64, 4))
        self.assertEqual(tuple(weight.shape), (4, 4))


class GradientAndStateDictTests(unittest.TestCase):
    """Task 2.2: the initial weight stays trainable and out of transient state."""

    def test_backpropagation_reaches_initial_weight(self):
        layer = make_layer()
        X, edge_index, edge_weight = make_batch()

        keys_before = set(layer.state_dict())

        output, weight = layer(X, edge_index, edge_weight)
        loss = output.pow(2).mean() + weight.pow(2).mean()
        loss.backward()

        gradient = layer.initial_weight.grad
        self.assertIsNotNone(gradient, "initial_weight must receive a gradient")
        self.assertTrue(torch.isfinite(gradient).all())
        self.assertGreater(float(gradient.abs().sum()), 0.0)

        self.assertEqual(set(layer.state_dict()), keys_before)

    def test_state_dict_has_no_transient_evolved_weight(self):
        layer = make_layer()
        X, edge_index, edge_weight = make_batch()
        _, weight = layer(X, edge_index, edge_weight)

        state = layer.state_dict()
        self.assertIn("initial_weight", state)
        self.assertNotIn("weight", state)
        self.assertFalse(
            any(
                key == "weight" or key.endswith(".weight_evolved")
                for key in state
            )
        )
        # The evolved weight is activation state, never a saved tensor.
        self.assertFalse(any(torch.equal(value, weight.detach()) for value in state.values()))

    def test_parameter_is_registered_for_the_optimizer(self):
        layer = make_layer()
        names = [name for name, _ in layer.named_parameters()]
        self.assertIn("initial_weight", names)
        optimizer = torch.optim.Adam(layer.parameters(), lr=0.01)
        self.assertTrue(any(parameter is layer.initial_weight for group in optimizer.param_groups for parameter in group["params"]))

    def test_training_updates_initial_weight(self):
        layer = make_layer()
        X, edge_index, edge_weight = make_batch()
        before = layer.initial_weight.detach().clone()
        optimizer = torch.optim.SGD(layer.parameters(), lr=0.5)

        output, _ = layer(X, edge_index, edge_weight)
        output.pow(2).mean().backward()
        optimizer.step()

        self.assertFalse(torch.allclose(before, layer.initial_weight.detach()))


class StateBoundaryTests(unittest.TestCase):
    """Task 2.3: explicit state boundaries and device placement."""

    def test_new_traversal_starts_from_initial_parameter(self):
        layer = make_layer()
        X, edge_index, edge_weight = make_batch()
        recorder = RecordingGRU(layer)
        self.addCleanup(recorder.restore)

        _, first = layer(X, edge_index, edge_weight)
        layer(X, edge_index, edge_weight, previous_weight=first)
        # A new traversal passes None again and must begin from the parameter.
        torch.testing.assert_close(recorder.received[1].squeeze(0), first.detach())
        layer(X, edge_index, edge_weight, previous_weight=None)
        torch.testing.assert_close(
            recorder.received[2].squeeze(0), layer.initial_weight.detach()
        )

    def test_initial_state_is_the_parameter(self):
        layer = make_layer()
        self.assertIs(layer.initial_state(), layer.initial_weight)

    def test_recurrent_state_follows_cpu_device(self):
        layer = make_layer().to("cpu")
        X, edge_index, edge_weight = make_batch()
        _, weight = layer(X, edge_index, edge_weight)
        self.assertEqual(weight.device.type, "cpu")
        self.assertEqual(layer.initial_weight.device.type, "cpu")

    def test_model_moves_between_devices_with_its_initial_state(self):
        layer = make_layer()
        moved = layer.to("cpu")
        self.assertIs(moved, layer)
        self.assertEqual(layer.initial_state().device.type, "cpu")

    @unittest.skipUnless(CUDA_AVAILABLE, CUDA_REASON)
    def test_recurrent_state_follows_cuda_device(self):
        layer = make_layer().to("cuda")
        X, edge_index, edge_weight = make_batch()
        X, edge_index, edge_weight = X.to("cuda"), edge_index.to("cuda"), edge_weight.to("cuda")
        _, weight = layer(X, edge_index, edge_weight)
        self.assertEqual(weight.device.type, "cuda")
        self.assertEqual(layer.initial_state().device.type, "cuda")

    @unittest.skipUnless(CUDA_AVAILABLE, CUDA_REASON)
    def test_cuda_backpropagation_reaches_initial_weight(self):
        layer = make_layer().to("cuda")
        X, edge_index, edge_weight = make_batch()
        X, edge_index, edge_weight = X.to("cuda"), edge_index.to("cuda"), edge_weight.to("cuda")
        output, _ = layer(X, edge_index, edge_weight)
        output.pow(2).mean().backward()
        self.assertIsNotNone(layer.initial_weight.grad)
        self.assertTrue(torch.isfinite(layer.initial_weight.grad).all())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
