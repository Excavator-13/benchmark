"""Recurrent model, determinism setup and immutable state snapshots.

The only model architecture this protocol permits is a shared single-layer
unidirectional GRU/LSTM with hidden size 32 over one input feature, followed by
a shared ``Linear(32, 3)`` head reading the last output hidden state.  For LSTM
the cell state is never used as the output representation and the saturation
diagnostic is computed on the output hidden sequence, not ``c_n``.
"""

from __future__ import annotations

import copy
import random
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

import numpy as np
import torch
from torch import nn

from . import protocol

INPUT_SIZE = 1


class RecurrentForecaster(nn.Module):
    """Shared GRU/LSTM reading one L6 window and predicting three horizons."""

    def __init__(self, model: str, hidden_size: int = protocol.HIDDEN_SIZE,
                 layers: int = protocol.LAYERS):
        super().__init__()
        kind = protocol.validate_model(str(model).upper())
        self.kind = kind
        self.hidden_size = int(hidden_size)
        self.layers = int(layers)
        recurrent = nn.GRU if kind == "GRU" else nn.LSTM
        self.rnn = recurrent(
            input_size=INPUT_SIZE,
            hidden_size=self.hidden_size,
            num_layers=self.layers,
            batch_first=True,
            dropout=0.0,
            bias=True,
        )
        self.head = nn.Linear(self.hidden_size, protocol.p01.HORIZON)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output, _ = self.rnn(x)
        return self.head(output[:, -1, :])

    def hidden_sequence(self, x: torch.Tensor) -> torch.Tensor:
        """Return the output hidden sequence ``[B, L, H]`` (never LSTM ``c_n``)."""
        output, _ = self.rnn(x)
        return output


def set_determinism(seed: int, threads: int = 1) -> None:
    """Fix every random source and the CPU thread/determinism settings."""
    if int(threads) != 1:
        raise protocol.ProtocolError(
            "the frozen protocol runs CPU single-thread; threads must be 1"
        )
    random.seed(int(seed))
    np.random.seed(int(seed))
    torch.manual_seed(int(seed))
    torch.set_num_threads(1)
    try:
        if torch.get_num_interop_threads() != 1:
            torch.set_num_interop_threads(1)
    except RuntimeError:  # pragma: no cover - already started parallel work
        pass
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def build_model(config: protocol.FitConfig) -> RecurrentForecaster:
    """Build the model with default PyTorch initialization under the seed."""
    set_determinism(config.seed, config.threads)
    return RecurrentForecaster(config.model, config.hidden_size, config.layers).to(
        dtype=torch.float32
    )


def build_optimizer(
    model: nn.Module, learning_rate: float
) -> torch.optim.Adam:
    return torch.optim.Adam(
        model.parameters(),
        lr=float(learning_rate),
        betas=protocol.ADAM_BETAS,
        eps=protocol.ADAM_EPS,
        weight_decay=protocol.WEIGHT_DECAY,
        amsgrad=protocol.AMSGRAD,
    )


def parameter_count(model: nn.Module) -> int:
    return int(sum(p.numel() for p in model.parameters()))


def parameter_count_report(model: nn.Module, kind: str) -> Dict[str, Any]:
    """Return the observed/protocol parameter counts for one model instance.

    The protocol architecture (hidden 32, one layer) must match exactly; a
    labelled development override may use a smaller fixture architecture.
    """
    expected = protocol.PARAMETER_COUNTS[protocol.validate_model(kind)]
    observed = parameter_count(model)
    return {
        "model": kind,
        "observed": observed,
        "protocol_expected": expected,
        "matches_protocol_architecture": observed == expected,
    }


def clone_state_dict(model: nn.Module) -> Dict[str, torch.Tensor]:
    """Return an independent CPU copy of every model tensor."""
    return {
        name: tensor.detach().to(device="cpu", dtype=torch.float32).clone()
        for name, tensor in model.state_dict().items()
    }


def deepcopy_state(value: Any) -> Any:
    """Deep-copy an optimizer/RNG state, cloning every tensor.

    ``Optimizer.state_dict()`` keeps live references to the moment estimates, so
    a plain ``{...}`` copy of the best epoch changes on later ``step()`` calls.
    This helper is what makes the best checkpoint immutable.
    """
    if isinstance(value, Mapping):
        return {key: deepcopy_state(item) for key, item in value.items()}
    if isinstance(value, list):
        return [deepcopy_state(item) for item in value]
    if isinstance(value, tuple):
        return tuple(deepcopy_state(item) for item in value)
    if torch.is_tensor(value):
        return value.detach().to("cpu").clone()
    return copy.deepcopy(value)


def random_states() -> Dict[str, Any]:
    """Capture Python, NumPy and torch RNG states for recovery."""
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch.get_rng_state().clone(),
    }


def restore_random_states(states: Mapping[str, Any]) -> None:
    random.setstate(states["python"])
    np.random.set_state(states["numpy"])
    torch.set_rng_state(states["torch"])


def predict(
    model: nn.Module,
    inputs: np.ndarray,
    scale: float,
    node_chunk: int,
    *,
    collect_hidden_stats: bool = False,
    check_stop: Optional[Callable[[], None]] = None,
) -> Tuple[np.ndarray, Optional[float]]:
    """Predict original-unit values for ``[windows, nodes, 6]`` inputs.

    Each window is a fresh sequence, so every window prediction is independent
    of the order in which windows are evaluated.
    """
    values = np.asarray(inputs, dtype=np.float64)
    if values.ndim != 3 or values.shape[2] != protocol.p01.INPUT_LENGTH:
        raise ValueError(f"inputs must be [windows, nodes, 6], got {values.shape}")
    if int(node_chunk) <= 0:
        raise ValueError("node_chunk must be positive")
    windows, nodes, _ = values.shape
    scaled = (values / float(scale)).astype(np.float32)
    result = np.empty(
        (windows, nodes, protocol.p01.HORIZON), dtype=np.float64
    )
    saturated = 0
    hidden_elements = 0
    model.eval()
    with torch.no_grad():
        for window in range(windows):
            for begin in range(0, nodes, int(node_chunk)):
                from . import resources
                resources.check_stage_budget()
                if check_stop is not None:
                    check_stop()
                end = min(nodes, begin + int(node_chunk))
                tensor = torch.from_numpy(scaled[window, begin:end]).unsqueeze(-1)
                prediction = model(tensor) * float(scale)
                result[window, begin:end] = prediction.to(torch.float64).numpy()
                if collect_hidden_stats:
                    hidden = model.hidden_sequence(tensor)
                    saturated += int((hidden.abs() > 0.99).sum().item())
                    hidden_elements += int(hidden.numel())
    fraction = saturated / hidden_elements if hidden_elements else None
    return result, fraction
