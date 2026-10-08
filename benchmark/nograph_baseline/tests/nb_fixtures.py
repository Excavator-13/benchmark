"""Synthetic Parquet and in-memory fixtures for the CPU unittest suite.

No production graph data is required: tests write their own small demand and
graph tables under a temporary directory and inject fixture coverage masks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from benchmark.nograph_baseline import data as nb_data
from benchmark.nograph_baseline import protocol
from benchmark.nograph_baseline.runner import RunSpec

MONTHS = list(protocol.MONTHS)


def r0_keys(skills: int) -> List[Tuple[int, int]]:
    return [(0, skill) for skill in range(skills)]


def region_keys(regions: int, skills: int) -> List[Tuple[int, int]]:
    return [
        (region, skill) for region in range(regions) for skill in range(skills)
    ]


def synthetic_signal(
    node_count: int,
    seed: int = 0,
    *,
    zero_rows: Sequence[int] = (),
    constant_rows: Sequence[int] = (),
    constant_value: float = 5.0,
    max_value: int = 40,
) -> np.ndarray:
    """Build a deterministic ``float32 [N, 36]`` count signal."""
    rng = np.random.default_rng(seed)
    signal = rng.integers(0, max_value, size=(node_count, len(MONTHS))).astype(
        np.float32
    )
    for row in zero_rows:
        signal[row, :] = 0.0
    for row in constant_rows:
        signal[row, :] = float(constant_value)
    return signal


def write_demand(
    path: Path,
    data_name: str,
    keys: Sequence[Sequence[int]],
    signal: np.ndarray,
    *,
    shuffle_seed: Optional[int] = None,
) -> Path:
    """Write a demand Parquet table, optionally shuffling the rows."""
    import pandas as pd

    key_columns = list(protocol.node_key_columns(data_name))
    frame = pd.DataFrame(np.asarray(keys, dtype=np.int64), columns=key_columns)
    for index, month in enumerate(MONTHS):
        frame[month] = np.asarray(signal, dtype=np.float64)[:, index]
    if shuffle_seed is not None:
        frame = frame.sample(frac=1.0, random_state=shuffle_seed).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def write_graph(
    path: Path,
    data_name: str,
    rows: Sequence[Sequence[int]],
) -> Path:
    """Write a raw context-qualified graph Parquet table."""
    import pandas as pd

    context = list(protocol.context_columns(data_name))
    frame = pd.DataFrame(
        np.asarray(rows, dtype=np.int64), columns=context + ["row_id", "col_id"]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def make_demand(
    data_name: str,
    keys: Sequence[Sequence[int]],
    signal: np.ndarray,
) -> nb_data.DemandData:
    return nb_data.from_arrays(data_name, keys, signal)


def make_run_spec(
    runs_root: Path,
    data_name: str,
    demand_path: Path,
    graph_path: Path,
    run_id: str,
    **overrides: Any,
) -> RunSpec:
    payload: Dict[str, Any] = {
        "data_name": data_name,
        "run_id": run_id,
        "mode": "count",
        "seed": 0,
        "ridge_backend": "numpy",
        "demand_path": str(demand_path),
        "graph_path": str(graph_path),
        "runs_root": str(runs_root),
        "repo_root": str(protocol.REPO_ROOT),
        "command": ["python", "-m", "benchmark.nograph_baseline", "run"],
        "run_type": "run",
    }
    payload.update(overrides)
    return RunSpec.from_dict(payload)


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_fixture(
    root: Path,
    data_name: str = "r0",
    *,
    node_count: int = 12,
    seed: int = 0,
    zero_rows: Sequence[int] = (0,),
    constant_rows: Sequence[int] = (1, 2),
    shuffle_seed: Optional[int] = 7,
    graph_rows: Optional[Sequence[Sequence[int]]] = None,
) -> Dict[str, Any]:
    """Create a complete demand+graph fixture and return its description."""
    if data_name == "r0":
        keys = r0_keys(node_count)
        context = [0]
    else:
        keys = region_keys(node_count, 2)
        context = list(range(node_count))
    signal = synthetic_signal(
        len(keys), seed, zero_rows=zero_rows, constant_rows=constant_rows
    )
    demand_path = write_demand(
        root / f"{data_name}.parquet", data_name, keys, signal, shuffle_seed=shuffle_seed
    )
    if graph_rows is None:
        if data_name == "r0":
            graph_rows = [
                [context[0], 0, 1],
                [context[0], 1, 2],
                [context[0], 2, 2],
            ]
        else:
            # Region fixtures have only two skills; keep every endpoint valid.
            graph_rows = [
                [context[0], 0, 1],
                [context[0], 1, 1],
            ]
    graph_path = write_graph(root / f"{data_name}-graph.parquet", data_name, graph_rows)
    return {
        "data_name": data_name,
        "keys": keys,
        "signal": signal,
        "demand_path": demand_path,
        "graph_path": graph_path,
        "graph_rows": graph_rows,
        "node_count": len(keys),
    }
