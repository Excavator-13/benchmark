"""Frozen GRU encoder, shared head and incoming-neighbour mean propagation.

The temporal encoder is one single-layer unidirectional bias-enabled
``GRU(1, 32)`` whose weights are shared by every node.  Independent zero hidden
states are carried in the batch dimension for each node and window, so node
order is never treated as time.  ``self`` uses the hidden state directly; the
graph and shuffled branches add ``h'_v = h_v + mean_{u in N_in(v)} h_u`` with an
exactly zero message for zero in-degree nodes.  No graph-specific trainable
tensor exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import torch
from torch import nn

from . import protocol

__all__ = [
    "ModelError",
    "GraphAggregation",
    "SkeletonModel",
    "build_model",
    "aggregate_incoming_mean",
    "parameter_signature",
    "parameter_counts",
    "graph_only_parameter_names",
    "state_arrays",
    "load_state_arrays",
    "predict",
    "predict_windows",
    "encode_windows",
    "check_finite",
]


class ModelError(ValueError):
    """Raised when model inputs or propagation violate the frozen contract."""


def check_finite(tensor: torch.Tensor, label: str) -> torch.Tensor:
    if not torch.isfinite(tensor).all():
        raise ModelError(f"{label} contains non-finite values")
    return tensor


@dataclass(frozen=True)
class GraphAggregation:
    """Binary directed edges in one node subset, used for message propagation.

    ``source`` and ``target`` are local positions in the node axis of the same
    chunk, so a context chunk carries its complete adjacency.  The empty case is
    explicit and returns the hidden states unchanged.
    """

    source: torch.Tensor
    target: torch.Tensor
    node_count: int
    label: str

    def __post_init__(self) -> None:
        source = self.source
        target = self.target
        if source.dtype != torch.int64 or target.dtype != torch.int64:
            raise ModelError("aggregation indices must be int64 tensors")
        if source.ndim != 1 or target.ndim != 1 or source.shape != target.shape:
            raise ModelError(
                f"aggregation indices must be 1-D of equal length, got "
                f"{tuple(source.shape)} / {tuple(target.shape)}"
            )
        if source.numel():
            if int(source.min()) < 0 or int(source.max()) >= self.node_count:
                raise ModelError(f"{self.label}: source index outside the node axis")
            if int(target.min()) < 0 or int(target.max()) >= self.node_count:
                raise ModelError(f"{self.label}: target index outside the node axis")
            if bool((source == target).any()):
                raise ModelError(f"{self.label}: aggregation received a self-loop edge")

    @property
    def edge_count(self) -> int:
        return int(self.source.numel())

    @classmethod
    def from_edges(
        cls, edges: Any, node_count: int, *, label: str = "graph"
    ) -> "GraphAggregation":
        array = torch.as_tensor(edges, dtype=torch.int64)
        if array.numel() == 0:
            array = array.reshape(0, 2)
        if array.ndim != 2 or array.shape[1] != 2:
            raise ModelError(f"{label}: edges must be [E, 2], got {tuple(array.shape)}")
        return cls(
            source=array[:, 0].contiguous(),
            target=array[:, 1].contiguous(),
            node_count=int(node_count),
            label=label,
        )

    @classmethod
    def identity(cls, node_count: int, *, label: str = "self") -> "GraphAggregation":
        """An empty aggregation (the ``self`` branch)."""
        empty = torch.zeros(0, dtype=torch.int64)
        return cls(source=empty, target=empty.clone(), node_count=node_count, label=label)

    def apply(self, hidden: torch.Tensor) -> torch.Tensor:
        return aggregate_incoming_mean(hidden, self.source, self.target)

    def payload(self) -> Dict[str, Any]:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "direction": "source -> target",
            "aggregation": "unweighted mean over distinct incoming neighbours",
            "self_loops": 0,
        }


def aggregate_incoming_mean(
    hidden: torch.Tensor, source: torch.Tensor, target: torch.Tensor
) -> torch.Tensor:
    """Add the unweighted mean hidden state of distinct incoming neighbours.

    Only built-in CPU tensor operations are used.  A zero in-degree row keeps the
    original hidden state *by selection*, so ``graph`` and ``self`` outputs are
    elementwise identical for isolated nodes and for an empty graph.
    """
    node_count = int(hidden.shape[0])
    if source.numel() == 0:
        return hidden
    message = torch.zeros_like(hidden)
    message = message.index_add(0, target, hidden.index_select(0, source))
    degree = torch.zeros(node_count, dtype=hidden.dtype)
    degree = degree.index_add(
        0, target, torch.ones(int(target.numel()), dtype=hidden.dtype)
    )
    nonzero = degree > 0
    mean = message / degree.clamp_min(1.0).unsqueeze(1)
    return torch.where(nonzero.unsqueeze(1), hidden + mean, hidden)


class SkeletonModel(nn.Module):
    """GRU(1, 32) encoder plus a shared Linear(32, 3) head."""

    def __init__(self, *, hidden_dim: int = protocol.HIDDEN_DIM) -> None:
        super().__init__()
        if hidden_dim != protocol.HIDDEN_DIM:
            raise ModelError(
                f"hidden dimension is frozen at {protocol.HIDDEN_DIM}, got {hidden_dim}"
            )
        self.gru = nn.GRU(
            input_size=1,
            hidden_size=hidden_dim,
            num_layers=1,
            bias=True,
            batch_first=True,
            bidirectional=False,
            dropout=0.0,
        )
        self.head = nn.Linear(hidden_dim, protocol.HORIZON, bias=True)

    def encode(self, inputs: torch.Tensor) -> torch.Tensor:
        """Encode ``[M, L]`` raw counts to ``[M, 32]`` with fresh zero states."""
        if inputs.ndim != 2 or int(inputs.shape[1]) != protocol.INPUT_LENGTH:
            raise ModelError(
                f"encoder inputs must be [M, {protocol.INPUT_LENGTH}], got "
                f"{tuple(inputs.shape)}"
            )
        check_finite(inputs, "encoder inputs")
        node_windows = int(inputs.shape[0])
        x = inputs.reshape(node_windows, protocol.INPUT_LENGTH, 1)
        hidden = torch.zeros(
            1, node_windows, protocol.HIDDEN_DIM, dtype=x.dtype, device=x.device
        )
        output, _ = self.gru(x, hidden)
        return output[:, -1, :]

    def forward(
        self,
        inputs: torch.Tensor,
        aggregation: Optional[GraphAggregation] = None,
    ) -> torch.Tensor:
        hidden = self.encode(inputs)
        if aggregation is not None:
            if int(aggregation.node_count) != int(hidden.shape[0]):
                raise ModelError(
                    f"aggregation node count {aggregation.node_count} != "
                    f"{int(hidden.shape[0])} encoded nodes"
                )
            hidden = aggregation.apply(hidden)
        return check_finite(self.head(hidden), "model predictions")


def build_model(model_seed: int, *, torch_seed: bool = True) -> SkeletonModel:
    """Construct the frozen architecture under an explicit model seed."""
    if torch_seed:
        torch.manual_seed(int(model_seed))
    return SkeletonModel()


def parameter_signature(model: SkeletonModel) -> Dict[str, List[int]]:
    return {
        name: list(parameter.shape)
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    }


def parameter_counts(model: SkeletonModel) -> Dict[str, int]:
    """Measure trainable parameters by component and in total."""
    counts = {"gru": 0, "head": 0, "graph_only": 0, "total": 0}
    for name, parameter in model.named_parameters():
        if not parameter.requires_grad:
            continue
        number = int(parameter.numel())
        counts["total"] += number
        if name.startswith("gru."):
            counts["gru"] += number
        elif name.startswith("head."):
            counts["head"] += number
        else:
            counts["graph_only"] += number
    return counts


def graph_only_parameter_names(model: SkeletonModel) -> List[str]:
    return [
        name
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
        and not (name.startswith("gru.") or name.startswith("head."))
    ]


def state_arrays(model: SkeletonModel) -> Dict[str, Any]:
    """Return named CPU NumPy copies loadable without pickle."""
    import numpy as np

    return {
        name: np.asarray(parameter.detach().cpu().numpy())
        for name, parameter in model.state_dict().items()
    }


def load_state_arrays(model: SkeletonModel, arrays: Mapping[str, Any]) -> SkeletonModel:
    import numpy as np

    state = {
        name: torch.as_tensor(np.asarray(value))
        for name, value in arrays.items()
    }
    model.load_state_dict(state, strict=True)
    return model


def predict(
    model: SkeletonModel,
    inputs: torch.Tensor,
    aggregation: Optional[GraphAggregation] = None,
) -> torch.Tensor:
    with torch.no_grad():
        return model(inputs, aggregation)


def encode_windows(
    model: SkeletonModel, windows: torch.Tensor
) -> torch.Tensor:
    """Encode ``[W, N, L]`` window tensors to ``[W, N, 32]`` independently."""
    if windows.ndim != 3 or int(windows.shape[2]) != protocol.INPUT_LENGTH:
        raise ModelError(
            f"window inputs must be [W, N, {protocol.INPUT_LENGTH}], got "
            f"{tuple(windows.shape)}"
        )
    window_count, node_count = int(windows.shape[0]), int(windows.shape[1])
    flat = windows.reshape(window_count * node_count, protocol.INPUT_LENGTH)
    hidden = model.encode(flat)
    return hidden.reshape(window_count, node_count, protocol.HIDDEN_DIM)


def predict_windows(
    model: SkeletonModel,
    windows: torch.Tensor,
    aggregation: Optional[GraphAggregation] = None,
) -> torch.Tensor:
    """Predict ``[W, N, 3]`` for independent window tensors.

    Message propagation is applied to each window's own ``N`` hidden states.
    Flattening ``W*N`` rows and applying node indices ``0..N-1`` once would
    silently self-propagate every window after the first, so the aggregation is
    applied per window and the results are stacked.
    """
    with torch.no_grad():
        if windows.ndim != 3 or int(windows.shape[2]) != protocol.INPUT_LENGTH:
            raise ModelError(
                f"window inputs must be [W, N, {protocol.INPUT_LENGTH}], got "
                f"{tuple(windows.shape)}"
            )
        window_count, node_count = int(windows.shape[0]), int(windows.shape[1])
        flat = windows.reshape(window_count * node_count, protocol.INPUT_LENGTH)
        hidden = model.encode(flat).reshape(
            window_count, node_count, protocol.HIDDEN_DIM
        )
        if aggregation is not None:
            if int(aggregation.node_count) != node_count:
                raise ModelError(
                    f"aggregation node count {aggregation.node_count} != {node_count}"
                )
            hidden = torch.stack(
                [
                    aggregation.apply(hidden[window])
                    for window in range(window_count)
                ],
                dim=0,
            )
        predictions = model.head(
            hidden.reshape(window_count * node_count, protocol.HIDDEN_DIM)
        )
        check_finite(predictions, "window predictions")
        return predictions.reshape(window_count, node_count, protocol.HORIZON)
