"""Repository-owned temporal graph loader for the Job-SDF graph method.

Loads the versioned JSON artifacts produced by
:mod:`benchmark.graph_method.prepare_graph_data`, validates them, and builds
weighted temporal snapshots for the pinned graph library.  As with the
preparer, every path is derived from this file's location so the loader behaves
the same from any working directory.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from torch_geometric_temporal.signal import StaticGraphTemporalSignal

SCHEMA_VERSION = 1

MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parents[1]
DEFAULT_DATA_DIR = MODULE_DIR / "data"

REGENERATION_HINT = (
    "regenerate it with "
    "`python benchmark/graph_method/prepare_graph_data.py "
    "--mode <rate|count> --data_name <granularity>`"
)

_REQUIRED_FIELDS = (
    "schema_version",
    "data_name",
    "mode",
    "node_keys",
    "features",
    "edges",
    "edge_weights",
)


class GraphDatasetError(ValueError):
    """Raised when a generated dataset is missing or structurally invalid."""


def dataset_path(data_name: str, mode: str, data_dir: Optional[Path] = None) -> Path:
    """Return the generated-artifact path for a granularity/mode pair."""
    base = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    return base / str(mode) / f"{data_name}.json"


def _as_float(value: Any, label: str) -> float:
    try:
        as_float = float(value)
    except (TypeError, ValueError) as exc:
        raise GraphDatasetError(f"{label} must be numeric, got {value!r}") from exc
    if not math.isfinite(as_float):
        raise GraphDatasetError(f"{label} must be finite, got {value!r}")
    return as_float


def _as_index(value: Any, label: str, node_count: int) -> int:
    try:
        as_float = float(value)
    except (TypeError, ValueError) as exc:
        raise GraphDatasetError(f"{label} must be numeric, got {value!r}") from exc
    if not math.isfinite(as_float) or as_float != int(as_float):
        raise GraphDatasetError(f"{label} must be a finite integer, got {value!r}")
    index = int(as_float)
    if not 0 <= index < node_count:
        raise GraphDatasetError(
            f"{label} is {index}, outside the valid node range [0, {node_count})"
        )
    return index


def validate_payload(payload: Any, source: Optional[Path] = None) -> Mapping[str, Any]:
    """Validate a generated payload and return it unchanged.

    Raises :class:`GraphDatasetError` on any structural, version, or integrity
    problem so that training never starts from malformed data.
    """
    origin = f" in {source}" if source is not None else ""

    if not isinstance(payload, Mapping):
        raise GraphDatasetError(f"generated dataset{origin} must be a JSON object")

    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise GraphDatasetError(
            f"generated dataset{origin} has schema_version={version!r}, "
            f"expected {SCHEMA_VERSION}; {REGENERATION_HINT}"
        )

    missing = [field for field in _REQUIRED_FIELDS if field not in payload]
    if missing:
        raise GraphDatasetError(f"generated dataset{origin} is missing field(s) {missing}")

    node_keys = payload["node_keys"]
    if not isinstance(node_keys, Sequence) or isinstance(node_keys, (str, bytes)):
        raise GraphDatasetError(f"'node_keys'{origin} must be a list")
    if len(node_keys) == 0:
        raise GraphDatasetError(f"generated dataset{origin} contains no nodes")
    seen = set()
    for position, key in enumerate(node_keys):
        if not isinstance(key, Sequence) or isinstance(key, (str, bytes)) or len(key) == 0:
            raise GraphDatasetError(f"'node_keys[{position}]'{origin} must be a non-empty list")
        canonical = tuple(int(_as_float(part, f"'node_keys[{position}]'{origin}")) for part in key)
        if canonical in seen:
            raise GraphDatasetError(
                f"generated dataset{origin} contains duplicate node key {list(canonical)}"
            )
        seen.add(canonical)
    node_count = len(node_keys)

    features = payload["features"]
    if not isinstance(features, Sequence) or isinstance(features, (str, bytes)):
        raise GraphDatasetError(f"'features'{origin} must be a list of time slices")
    if len(features) == 0:
        raise GraphDatasetError(f"generated dataset{origin} contains no time slices")
    for time_index, values in enumerate(features):
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            raise GraphDatasetError(f"'features[{time_index}]'{origin} must be a list")
        if len(values) != node_count:
            raise GraphDatasetError(
                f"'features[{time_index}]'{origin} has {len(values)} values, expected {node_count}"
            )
        for node_index, value in enumerate(values):
            _as_float(value, f"'features[{time_index}][{node_index}]'{origin}")

    edges = payload["edges"]
    if not isinstance(edges, Sequence) or isinstance(edges, (str, bytes)):
        raise GraphDatasetError(f"'edges'{origin} must be a list")
    weights = payload["edge_weights"]
    if not isinstance(weights, Sequence) or isinstance(weights, (str, bytes)):
        raise GraphDatasetError(f"'edge_weights'{origin} must be a list")
    if len(edges) != len(weights):
        raise GraphDatasetError(
            f"generated dataset{origin} has {len(edges)} edges but {len(weights)} edge weights"
        )
    for edge_index, edge in enumerate(edges):
        if not isinstance(edge, Sequence) or isinstance(edge, (str, bytes)) or len(edge) != 2:
            raise GraphDatasetError(
                f"'edges[{edge_index}]'{origin} must be a [source, target] pair"
            )
        _as_index(edge[0], f"'edges[{edge_index}][0]'{origin}", node_count)
        _as_index(edge[1], f"'edges[{edge_index}][1]'{origin}", node_count)
    for weight_index, weight in enumerate(weights):
        _as_float(weight, f"'edge_weights[{weight_index}]'{origin}")

    return payload


def load_payload(data_name: str, mode: str, data_dir: Optional[Path] = None) -> Mapping[str, Any]:
    """Read and validate the generated artifact for a granularity/mode pair."""
    path = dataset_path(data_name, mode, data_dir=data_dir)
    if not path.is_file():
        raise FileNotFoundError(
            f"generated graph dataset {path} does not exist; {REGENERATION_HINT}"
        )
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_payload(payload, source=path)


def _require_positive_length(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GraphDatasetError(f"{label} must be an integer, got {value!r}")
    if value <= 0:
        raise GraphDatasetError(f"{label} must be positive, got {value}")
    return value


def build_snapshots(
    payload: Mapping[str, Any],
    lags: int,
    pred_length: int,
) -> Tuple[List[np.ndarray], List[np.ndarray]]:
    """Slice a payload into ``[nodes, lags]`` inputs and ``[nodes, pred_length]`` targets.

    For time index ``t`` the input window is ``features[t : t + lags]`` and the
    target window is ``features[t + lags : t + lags + pred_length]``, each
    transposed to be node-major.  A dataset with ``T`` observations therefore
    yields ``T - lags - pred_length + 1`` snapshots.
    """
    lags = _require_positive_length(lags, "lags")
    pred_length = _require_positive_length(pred_length, "pred_length")

    features = validate_payload(payload)["features"]
    observations = len(features)
    if lags + pred_length > observations:
        raise GraphDatasetError(
            f"lags={lags} plus pred_length={pred_length} exceeds the "
            f"{observations} available observations"
        )

    matrix = np.asarray(features, dtype=np.float32)
    snapshot_count = observations - lags - pred_length + 1
    inputs = [
        np.ascontiguousarray(matrix[time : time + lags].T) for time in range(snapshot_count)
    ]
    targets = [
        np.ascontiguousarray(matrix[time + lags : time + lags + pred_length].T)
        for time in range(snapshot_count)
    ]
    return inputs, targets


def static_graph(payload: Mapping[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    """Return the ``[2, E]`` edge index and ``[E]`` weight arrays for a payload."""
    validate_payload(payload)
    edges = payload["edges"]
    if len(edges):
        edge_index = np.asarray(edges, dtype=np.int64).T
    else:
        edge_index = np.zeros((2, 0), dtype=np.int64)
    edge_weight = np.asarray(payload["edge_weights"], dtype=np.float32)
    return edge_index, edge_weight


class DatasetLoader:
    """Load validated, weighted temporal snapshots for one granularity/mode pair."""

    def __init__(self, data_name: str = "r0", mode: str = "rate", data_dir: Optional[Path] = None):
        self.data_name = data_name
        self.mode = mode
        self.data_dir = data_dir

    def get_dataset(self, lags: int = 6, pred_length: int = 3) -> StaticGraphTemporalSignal:
        """Build the static weighted temporal signal for ``lags``/``pred_length``."""
        payload = load_payload(self.data_name, self.mode, data_dir=self.data_dir)
        inputs, targets = build_snapshots(payload, lags=lags, pred_length=pred_length)
        edge_index, edge_weight = static_graph(payload)
        return StaticGraphTemporalSignal(edge_index, edge_weight, inputs, targets)
