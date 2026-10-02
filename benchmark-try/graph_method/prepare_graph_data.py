"""Repository-owned graph-data preparation CLI for the Job-SDF graph method.

This module converts the shipped Job-SDF time-series and co-occurrence Parquet
files into the versioned JSON artifacts consumed by
:mod:`benchmark.graph_method.dataset`.  It is importable, executable, and
independent of the caller's working directory: every repository path is derived
from this file's location.

Usage (from anywhere)::

    python benchmark/graph_method/prepare_graph_data.py --mode rate --data_name r0

Running it without ``--data_name``/``--mode`` prepares all seven granularities in
both modes.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

SCHEMA_VERSION = 1

#: Shipped granularities.  Naming matches the files under ``dataset/``.
GRANULARITIES: Tuple[str, ...] = (
    "r0",
    "r1",
    "r2",
    "r1-region",
    "r2-region",
    "region",
    "company",
)

#: Public CLI mode -> shipped source directory under ``dataset/``.
MODE_TO_SOURCE: Mapping[str, str] = {
    "count": "demand",
    "rate": "proportion",
}

MODES: Tuple[str, ...] = tuple(MODE_TO_SOURCE)

#: Context identifier columns for each granularity.  A graph node is the ordered
#: concatenation of these identifiers followed by the skill identifier.
CONTEXT_COLUMNS: Mapping[str, Tuple[str, ...]] = {
    "r0": ("r0_id",),
    "r1": ("r1_id",),
    "r2": ("r2_id",),
    "r1-region": ("r1_id", "region_id"),
    "r2-region": ("r2_id", "region_id"),
    "region": ("region_id",),
    "company": ("company_id",),
}

SKILL_COLUMN = "skill_id"
ROW_COLUMN = "row_id"
COLUMN_COLUMN = "col_id"

#: Time slices are stored as ``YYYY-MM`` columns.
TIME_COLUMN_PATTERN = re.compile(r"^\d{4}-\d{2}$")

MODULE_DIR = Path(__file__).resolve().parent
#: Repository root, derived from this module's location rather than the cwd.
REPO_ROOT = MODULE_DIR.parents[1]
DATASET_DIR = REPO_ROOT / "dataset"
#: Default destination for generated artifacts.
DEFAULT_OUTPUT_DIR = MODULE_DIR / "data"

REGENERATION_HINT = (
    "regenerate it with "
    "`python benchmark/graph_method/prepare_graph_data.py "
    "--mode <rate|count> --data_name <granularity>`"
)


class GraphDataError(ValueError):
    """Raised when preparation input is malformed or inconsistent."""


def time_columns(columns: Iterable[Any]) -> List[str]:
    """Return the ``YYYY-MM`` columns in chronological order."""
    return sorted(str(column) for column in columns if TIME_COLUMN_PATTERN.match(str(column)))


def _frame_columns(frame: Any) -> List[Any]:
    """Column labels of a pandas ``DataFrame`` or any mapping-like stand-in."""
    columns = getattr(frame, "columns", None)
    if columns is None:
        columns = frame.keys()
    return list(columns)


def _column_values(frame: Any, column: Any) -> List[Any]:
    series = frame[column]
    tolist = getattr(series, "tolist", None)
    return list(tolist()) if callable(tolist) else list(series)


def _as_int(value: Any, label: str) -> int:
    try:
        as_float = float(value)
    except (TypeError, ValueError) as exc:
        raise GraphDataError(f"{label} must be numeric, got {value!r}") from exc
    if not math.isfinite(as_float) or as_float != int(as_float):
        raise GraphDataError(f"{label} must be a finite integer, got {value!r}")
    return int(as_float)


def _as_float(value: Any, label: str) -> float:
    try:
        as_float = float(value)
    except (TypeError, ValueError) as exc:
        raise GraphDataError(f"{label} must be numeric, got {value!r}") from exc
    if not math.isfinite(as_float):
        raise GraphDataError(f"{label} must be finite, got {value!r}")
    return as_float


def _require_columns(frame: Any, required: Sequence[str], data_name: str, kind: str) -> None:
    available = {str(column) for column in _frame_columns(frame)}
    missing = [column for column in required if column not in available]
    if missing:
        raise GraphDataError(
            f"{data_name}: {kind} data is missing required column(s) {missing}; "
            f"available columns are {sorted(available)}"
        )


def _check_lengths(columns: Mapping[str, Sequence[Any]], data_name: str, kind: str) -> int:
    lengths = {name: len(values) for name, values in columns.items()}
    if len(set(lengths.values())) > 1:
        raise GraphDataError(f"{data_name}: {kind} columns have mismatched lengths {lengths}")
    return next(iter(lengths.values()), 0)


def validate_names(data_name: str, mode: str) -> None:
    """Fail fast on unsupported granularity/mode names, listing accepted values."""
    if data_name not in GRANULARITIES:
        raise GraphDataError(
            f"unsupported data_name {data_name!r}; accepted values are {list(GRANULARITIES)}"
        )
    if mode not in MODES:
        raise GraphDataError(f"unsupported mode {mode!r}; accepted values are {list(MODES)}")


def source_paths(data_name: str, mode: str, dataset_dir: Path | None = None) -> Tuple[Path, Path]:
    """Return ``(time_series_path, graph_path)`` for a granularity/mode pair."""
    validate_names(data_name, mode)
    base = Path(dataset_dir) if dataset_dir is not None else DATASET_DIR
    return (
        base / MODE_TO_SOURCE[mode] / f"{data_name}.parquet",
        base / "graph" / f"{data_name}.parquet",
    )


def output_path(data_name: str, mode: str, output_dir: Path | None = None) -> Path:
    """Return the generated-artifact path for a granularity/mode pair."""
    validate_names(data_name, mode)
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    return base / mode / f"{data_name}.json"


def _read_parquet(path: Path):
    """Read a Parquet file, reporting a clear error when it cannot be read."""
    if not path.is_file():
        raise FileNotFoundError(
            f"required source file {path} does not exist; expected the shipped Job-SDF dataset"
        )
    try:
        import pandas as pd  # imported lazily so path/CLI validation needs no pandas
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise GraphDataError(
            "reading Parquet sources requires pandas; install the pinned requirements"
        ) from exc
    return pd.read_parquet(path)


def build_graph_dataset(
    data_frame: Any,
    graph_frame: Any,
    data_name: str,
    mode: str,
) -> Dict[str, Any]:
    """Build the versioned JSON payload for one granularity/mode pair.

    ``data_frame`` holds the time series (context columns, ``skill_id`` and
    ``YYYY-MM`` slices) and ``graph_frame`` holds directed co-occurrence rows
    (the same context columns plus ``row_id``/``col_id``).  Both may be pandas
    ``DataFrame`` objects or any mapping of column name to a value sequence.

    Node identity is the ordered tuple of all context identifiers followed by
    the skill identifier, so the same skill pair under different contexts stays
    distinct.  Exact duplicate fully qualified directed rows are grouped into a
    single edge whose weight counts the source rows, preserving multiplicity
    without inventing a frequency value that the shipped schema does not carry.
    """
    validate_names(data_name, mode)
    context_columns = list(CONTEXT_COLUMNS[data_name])

    _require_columns(data_frame, context_columns + [SKILL_COLUMN], data_name, "time-series")
    _require_columns(
        graph_frame,
        context_columns + [ROW_COLUMN, COLUMN_COLUMN],
        data_name,
        "graph",
    )

    time_names = time_columns(_frame_columns(data_frame))
    if not time_names:
        raise GraphDataError(
            f"{data_name}: time-series data has no 'YYYY-MM' time columns; "
            f"available columns are {sorted(str(c) for c in _frame_columns(data_frame))}"
        )

    data_columns = {
        column: _column_values(data_frame, column)
        for column in context_columns + [SKILL_COLUMN]
    }
    row_count = _check_lengths(data_columns, data_name, "time-series")

    # --- nodes: context-qualified, unique, canonically ordered -------------
    rows_by_key: List[Tuple[Tuple[int, ...], int]] = []
    seen_keys: set = set()
    for row in range(row_count):
        key = tuple(
            _as_int(data_columns[column][row], f"{data_name}: column {column!r} row {row}")
            for column in context_columns
        ) + (_as_int(data_columns[SKILL_COLUMN][row], f"{data_name}: column 'skill_id' row {row}"),)
        if key in seen_keys:
            raise GraphDataError(
                f"{data_name}: duplicate node {list(key)} in the {mode} time series"
            )
        seen_keys.add(key)
        rows_by_key.append((key, row))

    if not rows_by_key:
        raise GraphDataError(f"{data_name}: the {mode} time series contains no nodes")

    # Sorting makes the artifact canonical: it does not depend on source row order.
    rows_by_key.sort(key=lambda item: item[0])
    node_keys: List[List[int]] = [list(key) for key, _ in rows_by_key]
    node_index: Dict[Tuple[int, ...], int] = {
        key: position for position, (key, _) in enumerate(rows_by_key)
    }
    ordered_rows = [row for _, row in rows_by_key]
    node_count = len(node_keys)

    # --- features: chronological, time-major, finite ------------------------
    features: List[List[float]] = []
    for time_name in time_names:
        values = _column_values(data_frame, time_name)
        if len(values) != row_count:
            raise GraphDataError(
                f"{data_name}: time column {time_name!r} has {len(values)} values, "
                f"expected {row_count}"
            )
        features.append(
            [
                _as_float(values[ordered_rows[node]], f"{data_name}: column {time_name!r} row {ordered_rows[node]}")
                for node in range(node_count)
            ]
        )

    # --- edges: mapped, directed, multiplicity preserving -------------------
    graph_columns = {
        column: _column_values(graph_frame, column)
        for column in context_columns + [ROW_COLUMN, COLUMN_COLUMN]
    }
    graph_rows = _check_lengths(graph_columns, data_name, "graph")

    row_context = [_as_int_list(graph_columns, context_columns, row, data_name) for row in range(graph_rows)]

    edge_counts: Dict[Tuple[int, int], int] = {}
    for row in range(graph_rows):
        prefix = row_context[row]
        source_key = prefix + (
            _as_int(graph_columns[ROW_COLUMN][row], f"{data_name}: column 'row_id' row {row}"),
        )
        target_key = prefix + (
            _as_int(graph_columns[COLUMN_COLUMN][row], f"{data_name}: column 'col_id' row {row}"),
        )
        if source_key not in node_index:
            raise GraphDataError(
                f"{data_name}: graph endpoint {list(source_key)} has no matching node "
                f"in the {mode} time series"
            )
        if target_key not in node_index:
            raise GraphDataError(
                f"{data_name}: graph endpoint {list(target_key)} has no matching node "
                f"in the {mode} time series"
            )
        pair = (node_index[source_key], node_index[target_key])
        edge_counts[pair] = edge_counts.get(pair, 0) + 1

    ordered_edges = sorted(edge_counts.items())
    edges = [[source, target] for (source, target), _ in ordered_edges]
    edge_weights = [float(count) for _, count in ordered_edges]

    return {
        "schema_version": SCHEMA_VERSION,
        "data_name": data_name,
        "mode": mode,
        "node_keys": node_keys,
        "features": features,
        "edges": edges,
        "edge_weights": edge_weights,
    }


def _as_int_list(
    columns: Mapping[str, Sequence[Any]],
    context_columns: Sequence[str],
    row: int,
    data_name: str,
) -> Tuple[int, ...]:
    return tuple(
        _as_int(columns[column][row], f"{data_name}: column {column!r} row {row}")
        for column in context_columns
    )


def write_graph_dataset(payload: Mapping[str, Any], destination: Path) -> Path:
    """Write ``payload`` to ``destination``, creating parent directories first."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    return destination


def prepare_dataset(
    data_name: str,
    mode: str,
    output_dir: Path | None = None,
    dataset_dir: Path | None = None,
) -> Path:
    """Prepare one granularity/mode pair and return the written artifact path."""
    data_path, graph_path = source_paths(data_name, mode, dataset_dir=dataset_dir)
    data_frame = _read_parquet(data_path)
    graph_frame = _read_parquet(graph_path)
    payload = build_graph_dataset(data_frame, graph_frame, data_name, mode)
    return write_graph_dataset(payload, output_path(data_name, mode, output_dir=output_dir))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prepare_graph_data.py",
        description=(
            "Prepare versioned graph-forecasting JSON artifacts from the shipped "
            "Job-SDF Parquet files. Defaults to every supported combination."
        ),
    )
    parser.add_argument(
        "--data_name",
        nargs="+",
        choices=list(GRANULARITIES),
        default=None,
        metavar="GRANULARITY",
        help=f"granularities to prepare (default: all of {list(GRANULARITIES)})",
    )
    parser.add_argument(
        "--mode",
        nargs="+",
        choices=list(MODES),
        default=None,
        metavar="MODE",
        help=f"public modes to prepare (default: all of {list(MODES)}); "
        "count reads dataset/demand, rate reads dataset/proportion",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=None,
        help=f"destination root (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the preparation CLI and return a process exit code."""
    args = build_parser().parse_args(argv)
    data_names = list(args.data_name) if args.data_name else list(GRANULARITIES)
    modes = list(args.mode) if args.mode else list(MODES)
    for mode in modes:
        for data_name in data_names:
            destination = prepare_dataset(data_name, mode, output_dir=args.output_dir)
            print(f"prepared {data_name} ({mode}) -> {destination}")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    raise SystemExit(main())
