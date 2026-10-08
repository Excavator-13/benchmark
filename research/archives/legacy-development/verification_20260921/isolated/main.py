"""Graph-based skill-demand forecasting entry point.

Running this module performs exactly one seeded experiment: it loads the
prepared graph dataset for the requested granularity/mode, splits the temporal
snapshots chronologically into train/validation/test partitions, selects the
best checkpoint by validation loss only, and finally evaluates that checkpoint
once on the test partition.

Importing this module has no side effects; every side effect lives behind
:func:`main` or the functions it calls.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F
import torch_geometric_temporal.nn.recurrent as R
from tqdm import tqdm

from dataset import DatasetLoader, GraphDatasetError
from models.evolvegcnh import EvolveGCNH
from prepare_graph_data import GRANULARITIES, MODES

MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = MODULE_DIR / "results"

#: Every graph model the CLI advertises.
MODEL_NAMES: Tuple[str, ...] = (
    "A3TGCN",
    "DCRNN",
    "DyGrEncoder",
    "EvolveGCNH",
    "EvolveGCNO",
    "GCLSTM",
    "GConvGRU",
    "GConvLSTM",
    "LRGCN",
    "MPNNLSTM",
    "TGCN",
)

#: Models whose recurrent state the runner carries explicitly as ``(H, C)``.
_HIDDEN_AND_CELL_MODELS = ("GCLSTM", "GConvLSTM", "LRGCN")
#: Models whose recurrent state the runner carries explicitly as ``H``.
_HIDDEN_ONLY_MODELS = ("A3TGCN", "DCRNN", "GConvGRU", "TGCN")

CHECKPOINT_FORMAT_VERSION = 1
CHECKPOINT_FILENAME = "checkpoint.pt"
LEGACY_CHECKPOINT_FILENAME = "model.pt"
METRICS_FILENAME = "metrics.json"

#: Architecture-defining checkpoint fields that must match a requested configuration.
CHECKPOINT_CONFIG_KEYS: Tuple[str, ...] = (
    "model_name",
    "num_nodes",
    "node_features",
    "hidden_dim",
    "window_size",
    "pred_length",
)

DEFAULT_LEARNING_RATE = 0.01
#: Declared numerical tolerance for repeated deterministic CPU runs.
DETERMINISM_TOLERANCE = 1e-6


class SplitValidationError(ValueError):
    """Raised when the configured split ratios cannot produce three partitions."""


class CheckpointError(ValueError):
    """Raised when a checkpoint is missing, stale, or incompatible."""


@dataclass(frozen=True)
class ExperimentConfig:
    """Everything one invocation needs; mirrors the command-line options."""

    data_name: str = "r0"
    mode: str = "rate"
    model_name: str = "EvolveGCNH"
    device: str = "cpu"
    seed: int = 0
    window_size: int = 6
    hidden_dim: int = 32
    pred_length: int = 3
    num_epochs: int = 500
    train_ratio: float = 0.83
    eval_ratio: float = 0.04
    data_dir: Optional[Path] = None
    results_dir: Path = field(default_factory=lambda: DEFAULT_RESULTS_DIR)

    def __post_init__(self) -> None:
        for name in ("window_size", "pred_length", "hidden_dim", "num_epochs"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer, got {value!r}")

    def architecture(self, num_nodes: int, node_features: int = 1) -> Dict[str, Any]:
        """Return the architecture-defining fields used to rebuild a model."""
        return {
            "model_name": self.model_name,
            "num_nodes": int(num_nodes),
            "node_features": int(node_features),
            "hidden_dim": self.hidden_dim,
            "window_size": self.window_size,
            "pred_length": self.pred_length,
        }


@dataclass
class SplitResult:
    """Aggregate outcome of traversing one temporal partition."""

    loss: float
    predictions: List[torch.Tensor] = field(default_factory=list)
    golds: List[torch.Tensor] = field(default_factory=list)
    optimizer_steps: int = 0


@dataclass
class LoadedCheckpoint:
    """A reconstructed model plus the metadata stored alongside its parameters."""

    model: "GraphForecaster"
    config: Dict[str, Any]
    seed: int
    best_val_loss: float


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Run one reproducible graph-based skill-demand forecasting experiment. "
            "Prepare data first with prepare_graph_data.py."
        ),
        # Reject abbreviations so the documented --model_name is the only spelling
        # that selects a model (a bare --model must not silently match it).
        allow_abbrev=False,
    )
    parser.add_argument(
        "--data_name",
        type=str,
        default="r0",
        choices=list(GRANULARITIES),
        help="granularity to forecast (default: r0)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="rate",
        choices=list(MODES),
        help="public data mode: count reads dataset/demand, rate reads dataset/proportion (default: rate)",
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="EvolveGCNH",
        choices=list(MODEL_NAMES),
        help="graph forecasting model (default: EvolveGCNH)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="torch device such as cpu or cuda:0 (default: cpu)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="single random seed for this run; it also names the result directory (default: 0)",
    )
    parser.add_argument(
        "--window_size",
        type=int,
        default=6,
        help="number of lagged observations in each input snapshot (default: 6)",
    )
    parser.add_argument(
        "--hidden_dim",
        type=int,
        default=32,
        help=(
            "hidden size for the model families that consume it (A3TGCN, DCRNN, DyGrEncoder, "
            "GCLSTM, GConvGRU, GConvLSTM, LRGCN, MPNNLSTM, TGCN); EvolveGCNH and EvolveGCNO "
            "derive their square graph-convolution weight from --window_size and ignore it"
        ),
    )
    parser.add_argument(
        "--pred_length",
        type=int,
        default=3,
        help="forecast horizon produced by each snapshot (default: 3)",
    )
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=500,
        help="number of training epochs (default: 500)",
    )
    return parser


def parse_config(argv: Optional[Sequence[str]] = None) -> ExperimentConfig:
    """Parse command-line arguments into an :class:`ExperimentConfig`."""
    args = build_parser().parse_args(argv)
    return ExperimentConfig(
        data_name=args.data_name,
        mode=args.mode,
        model_name=args.model_name,
        device=args.device,
        seed=args.seed,
        window_size=args.window_size,
        hidden_dim=args.hidden_dim,
        pred_length=args.pred_length,
        num_epochs=args.num_epochs,
    )


# --------------------------------------------------------------------------- #
# Runtime environment
# --------------------------------------------------------------------------- #


def resolve_device(name: str) -> torch.device:
    """Resolve a device string, failing before training when it is unusable."""
    try:
        device = torch.device(name)
    except (RuntimeError, ValueError) as exc:
        raise RuntimeError(f"unsupported device {name!r}; use 'cpu' or 'cuda[:index]'") from exc
    if device.type == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError(
                f"requested device {name!r} is unavailable: no CUDA device is visible to PyTorch"
            )
        device_count = torch.cuda.device_count()
        if device.index is not None and not 0 <= device.index < device_count:
            raise RuntimeError(
                f"requested device {name!r} is unavailable: only {device_count} CUDA device(s) present"
            )
    elif device.type != "cpu":
        raise RuntimeError(
            f"unsupported device {name!r}; this experiment supports 'cpu' and 'cuda[:index]'"
        )
    return device


def set_seed(seed: int, device: Optional[torch.device] = None) -> None:
    """Seed Python, NumPy, PyTorch CPU, and every available CUDA generator."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if device is not None and device.type == "cuda":
        torch.cuda.manual_seed(seed)


def configure_determinism(device: torch.device) -> List[str]:
    """Enable deterministic behavior where supported and report what is not."""
    notes: List[str] = []
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except TypeError:  # pragma: no cover - older PyTorch without warn_only
        try:
            torch.use_deterministic_algorithms(True)
        except Exception as exc:  # pragma: no cover - backend dependent
            notes.append(f"deterministic algorithms could not be enabled: {exc}")
    if device.type == "cuda":
        notes.append("CUDA kernels may remain nondeterministic regardless of seeding")
    return notes


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #


def load_dataset(config: ExperimentConfig):
    """Load the validated weighted temporal snapshots for ``config``."""
    loader = DatasetLoader(config.data_name, config.mode, data_dir=config.data_dir)
    return loader.get_dataset(lags=config.window_size, pred_length=config.pred_length)


def split_sizes(snapshot_count: int, train_ratio: float, eval_ratio: float) -> Tuple[int, int, int]:
    """Return chronological ``(train, validation, test)`` sizes or raise."""
    if isinstance(snapshot_count, bool) or not isinstance(snapshot_count, int) or snapshot_count <= 0:
        raise SplitValidationError(f"snapshot_count must be a positive integer, got {snapshot_count!r}")
    if not 0.0 < train_ratio < 1.0:
        raise SplitValidationError(f"train_ratio must be in (0, 1), got {train_ratio!r}")
    if not 0.0 < eval_ratio < 1.0:
        raise SplitValidationError(f"eval_ratio must be in (0, 1), got {eval_ratio!r}")
    if train_ratio + eval_ratio >= 1.0:
        raise SplitValidationError(
            f"train_ratio={train_ratio} plus eval_ratio={eval_ratio} must leave room for a test split"
        )

    train_count = int(train_ratio * snapshot_count)
    eval_count = int(eval_ratio * snapshot_count)
    test_count = snapshot_count - train_count - eval_count
    if min(train_count, eval_count, test_count) < 1:
        raise SplitValidationError(
            f"train_ratio={train_ratio} and eval_ratio={eval_ratio} over {snapshot_count} "
            f"snapshots produce empty partitions (train={train_count}, validation={eval_count}, "
            f"test={test_count}); adjust the ratios or provide more history"
        )
    return train_count, eval_count, test_count


def temporal_signal_split(
    data_iterator: Any,
    train_ratio: float = 0.83,
    eval_ratio: float = 0.04,
) -> Tuple[Any, Any, Any]:
    r"""Split a weighted temporal signal into chronological partitions.

    Arg types:
        * **data_iterator** *(Signal Iterator)* - Weighted temporal snapshots exposing
          ``snapshot_count`` and slice indexing.
        * **train_ratio** *(float)* - Fraction of leading snapshots reserved for training.
        * **eval_ratio** *(float)* - Fraction of snapshots reserved for validation, taken
          immediately after the training block.

    Return types:
        * **(train_iterator, eval_iterator, test_iterator)** *(tuple of Signal Iterators)* -
          Three disjoint, chronological partitions. Every partition is non-empty or a
          :class:`SplitValidationError` is raised before any training happens.
    """
    train_count, eval_count, _ = split_sizes(data_iterator.snapshot_count, train_ratio, eval_ratio)
    train_iterator = data_iterator[0:train_count]
    eval_iterator = data_iterator[train_count : train_count + eval_count]
    test_iterator = data_iterator[train_count + eval_count :]
    return train_iterator, eval_iterator, test_iterator


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #


class GraphForecaster(torch.nn.Module):
    """Wrap one advertised recurrent graph layer with a forecast head.

    Recurrent state is passed in and returned explicitly as a mapping with
    ``h``/``c``/``weight`` entries; the module never keeps traversal state of
    its own, so a traversal always starts from :meth:`initial_state`.
    """

    def __init__(
        self,
        model_name: str,
        num_nodes: int,
        node_features: int,
        hidden_dim: int,
        window_size: int,
        pred_length: int,
    ):
        super(GraphForecaster, self).__init__()
        if model_name not in MODEL_NAMES:
            raise ValueError(f"unknown model_name {model_name!r}; expected one of {list(MODEL_NAMES)}")
        self.model_name = model_name
        self.num_nodes = int(num_nodes)
        self.node_features = int(node_features)
        self.hidden_dim = int(hidden_dim)
        self.window_size = int(window_size)
        self.pred_length = int(pred_length)

        periods = self.window_size
        if model_name == "A3TGCN":
            self.recurrent = R.A3TGCN(self.node_features, hidden_dim, periods)
            self.linear = torch.nn.Linear(hidden_dim, pred_length)
        elif model_name == "DCRNN":
            self.recurrent = R.DCRNN(periods, hidden_dim, 1)
            self.linear = torch.nn.Linear(hidden_dim, pred_length)
        elif model_name == "DyGrEncoder":
            self.recurrent = R.DyGrEncoder(
                conv_out_channels=periods,
                conv_num_layers=1,
                conv_aggr="mean",
                lstm_out_channels=hidden_dim,
                lstm_num_layers=1,
            )
            self.linear = torch.nn.Linear(hidden_dim, pred_length)
        elif model_name == "EvolveGCNH":
            self.recurrent = EvolveGCNH(self.num_nodes, periods)
            self.linear = torch.nn.Linear(periods, pred_length)
        elif model_name == "EvolveGCNO":
            self.recurrent = R.EvolveGCNO(periods)
            self.linear = torch.nn.Linear(periods, pred_length)
        elif model_name == "GCLSTM":
            self.recurrent = R.GCLSTM(periods, hidden_dim, 1)
            self.linear = torch.nn.Linear(hidden_dim, pred_length)
        elif model_name == "GConvGRU":
            self.recurrent = R.GConvGRU(periods, hidden_dim, 1)
            self.linear = torch.nn.Linear(hidden_dim, pred_length)
        elif model_name == "GConvLSTM":
            self.recurrent = R.GConvLSTM(periods, hidden_dim, 1)
            self.linear = torch.nn.Linear(hidden_dim, pred_length)
        elif model_name == "LRGCN":
            self.recurrent = R.LRGCN(periods, hidden_dim, 1, 1)
            self.linear = torch.nn.Linear(hidden_dim, pred_length)
        elif model_name == "MPNNLSTM":
            self.recurrent = R.MPNNLSTM(periods, hidden_dim, self.num_nodes, 1, 0.5)
            self.linear = torch.nn.Linear(2 * hidden_dim + periods, pred_length)
        elif model_name == "TGCN":
            self.recurrent = R.TGCN(periods, hidden_dim)
            self.linear = torch.nn.Linear(hidden_dim, pred_length)
        else:  # pragma: no cover - guarded above
            raise ValueError(f"unknown model_name {model_name!r}")

    def initial_state(self) -> Dict[str, Optional[torch.Tensor]]:
        """Return a fresh recurrent state for one traversal.

        Any state kept inside a third-party layer is reset here so nothing
        survives from a previous epoch or partition.
        """
        self._reset_layer_state()
        return {"h": None, "c": None, "weight": None}

    def _reset_layer_state(self) -> None:
        """Clear traversal state that a third-party layer keeps on itself."""
        recurrent = self.recurrent
        reset = getattr(recurrent, "reinitialize_weight", None)
        if callable(reset):
            reset()
            return
        state = getattr(recurrent, "weight", None)
        if state is None:
            return
        if isinstance(state, torch.nn.Parameter) or "weight" in getattr(recurrent, "_buffers", {}):
            # A genuine learnable parameter or buffer: never traversal state.
            return
        # EvolveGCN-O in the pinned release keeps its evolved weight in a plain
        # ``weight`` attribute and exposes no reset hook; clearing it restores the
        # layer's own "start from initial_weight" behavior for the next traversal.
        recurrent.weight = None

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_weight: torch.Tensor,
        state: Optional[Mapping[str, Optional[torch.Tensor]]] = None,
    ) -> Tuple[torch.Tensor, Dict[str, Optional[torch.Tensor]]]:
        """Run one snapshot and return ``(forecast, next_state)``."""
        state = state or {}
        h = state.get("h")
        c = state.get("c")
        weight = state.get("weight")
        next_h, next_c, next_weight = None, None, weight
        name = self.model_name

        if name in _HIDDEN_ONLY_MODELS:
            if name == "A3TGCN":
                # A3TGCN consumes [batch, nodes, periods] and shares one H across periods.
                next_h = self.recurrent(
                    x.view(x.shape[0], 1, x.shape[1]), edge_index, edge_weight, h
                )
            else:
                next_h = self.recurrent(x, edge_index, edge_weight, h)
            output = self.linear(F.relu(next_h))
        elif name == "MPNNLSTM":
            output = self.linear(F.relu(self.recurrent(x, edge_index, edge_weight)))
        elif name == "EvolveGCNO":
            output = self.linear(F.relu(self.recurrent(x, edge_index, edge_weight)))
        elif name == "EvolveGCNH":
            raw, next_weight = self.recurrent(x, edge_index, edge_weight, weight)
            output = self.linear(F.relu(raw))
        elif name in _HIDDEN_AND_CELL_MODELS:
            if name == "LRGCN":
                # LRGCN's third positional argument is a relation type, not an edge
                # weight; this single-relation configuration uses relation 0.
                edge_type = torch.zeros_like(edge_index[0])
                next_h, next_c = self.recurrent(x, edge_index, edge_type, h, c)
            else:
                next_h, next_c = self.recurrent(x, edge_index, edge_weight, h, c)
            output = self.linear(F.relu(next_h))
        elif name == "DyGrEncoder":
            raw, next_h, next_c = self.recurrent(x, edge_index, edge_weight, h, c)
            output = self.linear(F.relu(raw))
        else:  # pragma: no cover - constructor guards the model list
            raise ValueError(f"unknown model_name {name!r}")

        return output, {"h": next_h, "c": next_c, "weight": next_weight}


def build_model(config: ExperimentConfig, num_nodes: int, node_features: int = 1) -> GraphForecaster:
    """Construct the configured model without touching random state."""
    return GraphForecaster(
        model_name=config.model_name,
        num_nodes=num_nodes,
        node_features=node_features,
        hidden_dim=config.hidden_dim,
        window_size=config.window_size,
        pred_length=config.pred_length,
    )


# --------------------------------------------------------------------------- #
# Split execution
# --------------------------------------------------------------------------- #


def _to_device(tensor: Optional[torch.Tensor], device: torch.device) -> Optional[torch.Tensor]:
    """Single seam through which every snapshot tensor reaches the device."""
    return tensor if tensor is None else tensor.to(device)


def move_snapshot(snapshot: Any, device: torch.device) -> Any:
    """Move every tensor of ``snapshot`` to ``device`` in place and return it."""
    snapshot.x = _to_device(snapshot.x, device)
    snapshot.edge_index = _to_device(snapshot.edge_index, device)
    snapshot.edge_attr = _to_device(snapshot.edge_attr, device)
    snapshot.y = _to_device(snapshot.y, device)
    return snapshot


def run_split(
    model: GraphForecaster,
    iterator: Iterable[Any],
    device: torch.device,
    *,
    training: bool = False,
    optimizer: Optional[torch.optim.Optimizer] = None,
    collect_predictions: bool = False,
) -> SplitResult:
    """Traverse one temporal partition with a shared, device-consistent runner.

    Every snapshot tensor is moved to ``device``, recurrent state starts fresh
    for this traversal and is carried only between chronological snapshots, and
    training performs exactly one optimizer step for the whole traversal.
    """
    model.train(training)
    state = model.initial_state()
    accumulated: Any = None
    snapshots = 0
    predictions: List[torch.Tensor] = []
    golds: List[torch.Tensor] = []

    with (torch.enable_grad() if training else torch.no_grad()):
        for snapshot in iterator:
            snapshot = move_snapshot(snapshot, device)
            y_hat, state = model(snapshot.x, snapshot.edge_index, snapshot.edge_attr, state)
            loss = torch.mean((y_hat - snapshot.y) ** 2)
            if training:
                accumulated = loss if accumulated is None else accumulated + loss
            else:
                value = float(loss.detach())
                accumulated = value if accumulated is None else accumulated + value
            snapshots += 1
            if collect_predictions:
                predictions.append(y_hat.detach().cpu())
                golds.append(snapshot.y.detach().cpu())

    if snapshots == 0:
        raise SplitValidationError("a temporal partition contained no snapshots")

    steps = 0
    if training:
        mean_loss = accumulated / snapshots
        if optimizer is not None:
            optimizer.zero_grad()
            mean_loss.backward()
            optimizer.step()
            steps = 1
        return SplitResult(float(mean_loss.detach()), predictions, golds, steps)
    return SplitResult(float(accumulated) / snapshots, predictions, golds, steps)


def regression_metrics(
    predictions: Sequence[torch.Tensor],
    golds: Sequence[torch.Tensor],
) -> Dict[str, float]:
    """Return the benchmark's RMSE and MAE for aligned per-snapshot tensors."""
    if not predictions or len(predictions) != len(golds):
        raise ValueError("predictions and golds must be non-empty and aligned")
    squared = 0.0
    absolute = 0.0
    for prediction, gold in zip(predictions, golds):
        squared += float(torch.mean((prediction - gold) ** 2))
        absolute += float(torch.mean(torch.abs(prediction - gold)))
    count = len(predictions)
    return {"RMSE": math.sqrt(squared / count), "MAE": absolute / count}


# --------------------------------------------------------------------------- #
# Checkpoints
# --------------------------------------------------------------------------- #


def checkpoint_payload(
    model: GraphForecaster,
    config: ExperimentConfig,
    *,
    num_nodes: int,
    node_features: int = 1,
    best_val_loss: float,
) -> Dict[str, Any]:
    """Build the versioned, reconstructable checkpoint payload."""
    return {
        "format_version": CHECKPOINT_FORMAT_VERSION,
        "model_state_dict": model.state_dict(),
        "config": config.architecture(num_nodes, node_features),
        "seed": int(config.seed),
        "best_val_loss": torch.tensor(best_val_loss, dtype=torch.float64),
    }


def save_checkpoint(
    path: Path,
    model: GraphForecaster,
    config: ExperimentConfig,
    *,
    num_nodes: int,
    node_features: int = 1,
    best_val_loss: float,
) -> Path:
    """Write a parameter/configuration payload rather than a pickled model."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = checkpoint_payload(
        model, config, num_nodes=num_nodes, node_features=node_features, best_val_loss=best_val_loss
    )
    with path.open("wb") as handle:
        torch.save(payload, handle)
    return path


def load_checkpoint(
    path: Path,
    device: torch.device,
    *,
    expected_config: Optional[Mapping[str, Any]] = None,
) -> LoadedCheckpoint:
    """Reconstruct a model from a checkpoint, mapping tensors to ``device``."""
    path = Path(path)
    if not path.is_file():
        legacy = path.with_name(LEGACY_CHECKPOINT_FILENAME)
        extra = ""
        if legacy.is_file():
            extra = (
                f"; found legacy {legacy.name}, which this version cannot load. "
                "Rerun the experiment to produce checkpoint.pt"
            )
        raise CheckpointError(f"checkpoint {path} does not exist{extra}")

    payload = torch.load(path, map_location=device, weights_only=True)
    if not isinstance(payload, Mapping):
        raise CheckpointError(f"checkpoint {path} is not a mapping payload")
    version = payload.get("format_version")
    if version != CHECKPOINT_FORMAT_VERSION:
        raise CheckpointError(
            f"checkpoint {path} has format_version={version!r}, expected "
            f"{CHECKPOINT_FORMAT_VERSION}; rerun the experiment"
        )
    for key in ("model_state_dict", "config", "seed", "best_val_loss"):
        if key not in payload:
            raise CheckpointError(f"checkpoint {path} is missing the {key!r} field")

    architecture = payload["config"]
    if not isinstance(architecture, Mapping):
        raise CheckpointError(f"checkpoint {path} has a non-mapping 'config' field")
    missing = [key for key in CHECKPOINT_CONFIG_KEYS if key not in architecture]
    if missing:
        raise CheckpointError(f"checkpoint {path} is missing configuration fields {missing}")

    if expected_config is not None:
        conflicts = {
            key: {"checkpoint": architecture.get(key), "requested": expected_config[key]}
            for key in CHECKPOINT_CONFIG_KEYS
            if key in expected_config and architecture.get(key) != expected_config[key]
        }
        if conflicts:
            raise CheckpointError(
                f"checkpoint {path} does not match the requested configuration: {conflicts}"
            )

    model = GraphForecaster(**{key: architecture[key] for key in CHECKPOINT_CONFIG_KEYS})
    model.load_state_dict(payload["model_state_dict"])
    model.to(device)
    return LoadedCheckpoint(
        model=model,
        config=dict(architecture),
        seed=int(payload["seed"]),
        best_val_loss=float(payload["best_val_loss"]),
    )


# --------------------------------------------------------------------------- #
# Experiment
# --------------------------------------------------------------------------- #


def result_dir(config: ExperimentConfig, results_dir: Optional[Path] = None) -> Path:
    """Return the result directory honored by the requested seed."""
    base = Path(results_dir) if results_dir is not None else config.results_dir
    return base / config.mode / config.data_name / config.model_name / str(config.seed)


#: Prediction artifacts written by a run; nothing else in a result directory matches.
_PREDICTION_ARTIFACT_PATTERN = re.compile(r"^(?:pred|gold)_(\d+)\.pt$")


def clear_prediction_artifacts(directory: Path) -> List[Path]:
    """Delete ``pred_<n>.pt``/``gold_<n>.pt`` left behind by an earlier run.

    The result directory is keyed by mode/granularity/model/seed only, so a rerun
    with a different window or forecast horizon would otherwise leave the previous
    run's higher-index predictions next to the new ones.  Only strict
    ``pred_<int>.pt``/``gold_<int>.pt`` names directly inside ``directory`` match.
    """
    directory = Path(directory)
    removed: List[Path] = []
    if not directory.is_dir():
        return removed
    for entry in sorted(directory.iterdir()):
        if entry.is_file() and _PREDICTION_ARTIFACT_PATTERN.match(entry.name):
            entry.unlink()
            removed.append(entry)
    return removed


def _first_snapshot(iterator: Any) -> Any:
    try:
        return iterator[0]
    except TypeError:
        return next(iter(iterator))


def train_experiment(
    config: ExperimentConfig,
    train_split: Any,
    eval_split: Any,
    test_split: Any,
    *,
    results_dir: Optional[Path] = None,
    device: Optional[torch.device] = None,
    progress: bool = True,
) -> Dict[str, float]:
    """Train on one seed, select by validation loss, and test exactly once."""
    device = resolve_device(config.device) if device is None else device
    directory = result_dir(config, results_dir=results_dir)
    directory.mkdir(parents=True, exist_ok=True)

    # Seed before anything random happens (model construction included).
    set_seed(config.seed, device)
    configure_determinism(device)

    num_nodes = int(_first_snapshot(train_split).x.shape[0])
    node_features = 1
    architecture = config.architecture(num_nodes, node_features)

    model = build_model(config, num_nodes, node_features).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=DEFAULT_LEARNING_RATE)

    best_val_loss = float("inf")
    epochs = tqdm(range(config.num_epochs), disable=not progress)
    for _ in epochs:
        run_split(model, train_split, device, training=True, optimizer=optimizer)
        validation = run_split(model, eval_split, device)
        if validation.loss < best_val_loss:
            best_val_loss = validation.loss
            save_checkpoint(
                directory / CHECKPOINT_FILENAME,
                model,
                config,
                num_nodes=num_nodes,
                node_features=node_features,
                best_val_loss=best_val_loss,
            )
            epochs.set_postfix(best_val_loss=f"{best_val_loss:.6f}")

    if not math.isfinite(best_val_loss):
        raise RuntimeError("no epoch produced a finite validation loss; nothing to evaluate")

    # Restore the validation-selected checkpoint, then traverse test exactly once.
    restored = load_checkpoint(
        directory / CHECKPOINT_FILENAME,
        device,
        expected_config=architecture,
    )
    model = restored.model

    test_result = run_split(model, test_split, device, collect_predictions=True)
    metrics = regression_metrics(test_result.predictions, test_result.golds)

    # Drop any prediction artifacts from a previous run in this directory so the
    # stored set always matches the metrics written below.
    clear_prediction_artifacts(directory)
    for time_index, (prediction, gold) in enumerate(
        zip(test_result.predictions, test_result.golds)
    ):
        with (directory / f"pred_{time_index}.pt").open("wb") as handle:
            torch.save(prediction, handle)
        with (directory / f"gold_{time_index}.pt").open("wb") as handle:
            torch.save(gold, handle)
    with (directory / METRICS_FILENAME).open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle)

    return metrics


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run one experiment and return a process exit code."""
    config = parse_config(argv)
    try:
        device = resolve_device(config.device)
        dataset = load_dataset(config)
        train_split, eval_split, test_split = temporal_signal_split(
            dataset, config.train_ratio, config.eval_ratio
        )
        metrics = train_experiment(
            config,
            train_split,
            eval_split,
            test_split,
            device=device,
        )
    except (SplitValidationError, GraphDatasetError, CheckpointError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess/tests
    raise SystemExit(main())
