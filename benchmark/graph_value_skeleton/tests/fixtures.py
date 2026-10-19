"""Deterministic small fixtures for the graph-value-skeleton test suite.

No full published dataset is required.  Fixtures are written as real Parquet
tables so the public entry reads them through the same loader path as published
data, while ``published=False`` keeps the full-size assertions out of the unit
suite.  The grids are multi-context where the schema allows it, deliberately
non-symmetric, activity-boundary-rich and swappable for the shuffled control.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from benchmark.graph_value_skeleton import data as gvs_data
from benchmark.graph_value_skeleton import graph as gvs_graph
from benchmark.graph_value_skeleton import protocol
from benchmark.graph_value_skeleton.config import RunConfig, resolve_config

SIGNAL_SEED = 20261018

#: schema -> (context ids, skills)
SCHEMAS: Dict[str, Tuple[Tuple[int, ...], int]] = {
    "r0": ((0,), 7),
    "region": ((0, 1), 4),
    "r2": ((0, 1), 4),
}

#: schema -> per-context directed edges (local skill ids).  All are asymmetric
#: and leave at least one legal double-edge swap; r0 keeps node 6 isolated so
#: both neighbour groups are nonempty there.
CONTEXT_EDGES: Dict[str, List[Tuple[int, int]]] = {
    "r0": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0), (0, 2), (3, 5)],
    "region": [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3)],
    "r2": [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3)],
}


def keys_for(data_name: str) -> List[Tuple[int, int]]:
    contexts, skills = SCHEMAS[data_name]
    return [(context, skill) for context in contexts for skill in range(skills)]


def graph_rows_for(data_name: str) -> List[Tuple[int, int, int]]:
    contexts, _ = SCHEMAS[data_name]
    return [
        (context, source, target)
        for context in contexts
        for source, target in CONTEXT_EDGES[data_name]
    ]


def signal_for(node_count: int, *, seed: int = SIGNAL_SEED) -> np.ndarray:
    """Boundary-rich ``float32 [N, 36]`` counts (all four activity groups)."""
    rng = np.random.default_rng(seed)
    signal = rng.integers(0, 40, size=(node_count, len(protocol.p01.MONTHS))).astype(
        np.float32
    )
    signal[0, :] = 0.0
    signal[1, :] = 5.0
    signal[2, :] = 0.0
    signal[2, :9] = np.float32(7)
    signal[3, :] = 0.0
    signal[3, :18] = np.float32(3)
    return signal


def write_demand(
    path: Path,
    data_name: str,
    keys: Sequence[Sequence[int]],
    signal: np.ndarray,
    *,
    row_order_seed: Optional[int] = None,
) -> Path:
    import pandas as pd

    key_columns = list(protocol.p01.node_key_columns(data_name))
    frame = pd.DataFrame(np.asarray(keys, dtype=np.int64), columns=key_columns)
    for index, month in enumerate(protocol.p01.MONTHS):
        frame[month] = np.asarray(signal, dtype=np.float64)[:, index]
    if row_order_seed is not None:
        frame = frame.sample(frac=1.0, random_state=row_order_seed).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def write_graph(
    path: Path,
    data_name: str,
    rows: Sequence[Sequence[int]],
    *,
    row_order_seed: Optional[int] = None,
) -> Path:
    import pandas as pd

    columns = list(protocol.p01.context_columns(data_name)) + ["row_id", "col_id"]
    frame = pd.DataFrame(np.asarray(rows, dtype=np.int64), columns=columns)
    if row_order_seed is not None:
        frame = frame.sample(frac=1.0, random_state=row_order_seed).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def build_fixture(
    root: Path,
    data_name: str = "r0",
    *,
    graph_rows: Optional[Sequence[Sequence[int]]] = None,
    demand_seed: int = SIGNAL_SEED,
    row_order_seed: Optional[int] = None,
    keys: Optional[Sequence[Sequence[int]]] = None,
    signal: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Write one demand+graph fixture pair and return its description."""
    keys = list(keys) if keys is not None else keys_for(data_name)
    signal = (
        np.asarray(signal)
        if signal is not None
        else signal_for(len(keys), seed=demand_seed)
    )
    demand_path = write_demand(
        root / f"{data_name}-demand.parquet",
        data_name,
        keys,
        signal,
        row_order_seed=row_order_seed,
    )
    rows = list(graph_rows) if graph_rows is not None else graph_rows_for(data_name)
    graph_path = write_graph(
        root / f"{data_name}-graph.parquet",
        data_name,
        rows,
        row_order_seed=row_order_seed,
    )
    return {
        "data_name": data_name,
        "keys": keys,
        "signal": signal,
        "demand_path": demand_path,
        "graph_path": graph_path,
        "graph_rows": rows,
        "node_count": len(keys),
    }


def load_fixture(fixture: Dict[str, Any]) -> Tuple[gvs_data.SkeletonDataset, gvs_graph.GraphData]:
    dataset = gvs_data.load_dataset(
        fixture["data_name"], demand_path=fixture["demand_path"], published=False
    )
    graph = gvs_graph.load_graph(
        fixture["data_name"],
        dataset.key_array,
        graph_path=fixture["graph_path"],
        published=False,
    )
    return dataset, graph


def make_config(
    root: Path,
    fixture: Dict[str, Any],
    *,
    method: str,
    model_seed: int = 0,
    shuffle_seed: Optional[int] = None,
    purpose: str = protocol.PURPOSE_DEVELOPMENT,
    run_id: str = "fixture-run",
    command: Sequence[str] = ("test",),
    repo_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
) -> RunConfig:
    return resolve_config(
        data_name=fixture["data_name"],
        method=method,
        model_seed=model_seed,
        shuffle_seed=shuffle_seed,
        run_id=run_id,
        purpose=purpose,
        repo_root=Path(repo_root) if repo_root is not None else protocol.REPO_ROOT,
        output_root=output_root if output_root is not None else root / "runs",
        demand_path=str(fixture["demand_path"]),
        graph_path=str(fixture["graph_path"]),
        command=list(command),
        launcher_cwd=root,
    )


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def unique_edges(fixture: Dict[str, Any]) -> np.ndarray:
    """Canonical in-memory edges via the new loader (used by unit tests)."""
    _, graph = load_fixture(fixture)
    return graph.edges
