"""Context-qualified graph loading, endpoint mapping and structure audits.

Each graph row is ``(context, row_id) -> (context, col_id)`` where
``row_id``/``col_id`` are skill identifiers, not global node indices.  Endpoints
resolve through exactly the canonical integer-key ordering used by
``prepare_graph_data`` and the P01 entry.  Published graph inputs re-assert the
frozen row counts, column set, symmetry and context block isolation; arbitrary
small fixtures resolve by their actual (possibly non-dense) keys.

Duplicate rows are audited as multiplicity and then collapsed to unique binary
directed edges: multiplicity never weights the adjacency and is never called
observed frequency.  Self-loops are rejected explicitly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from benchmark.nograph_baseline import protocol as p01
from benchmark.nograph_baseline.data import sha256_file

from . import protocol

__all__ = [
    "GraphError",
    "GraphData",
    "ContextLayout",
    "ROW_COLUMN",
    "COLUMN_COLUMN",
    "FORBIDDEN_COLUMNS",
    "load_graph",
    "from_arrays",
    "context_layout",
    "edge_set_sha256",
    "canonical_edge_array",
    "node_keys_sha256",
]

ROW_COLUMN = "row_id"
COLUMN_COLUMN = "col_id"
FORBIDDEN_COLUMNS = ("weight", "frequency", "edge_weight", "edge_frequency")

_MULTIPLICITY_DISPLAY_LIMIT = 20


class GraphError(ValueError):
    """Raised when the graph table or its mapping violates the contract."""


@dataclass
class ContextLayout:
    """Per-context node and edge subsets for chunked training."""

    contexts: List[Tuple[int, ...]]
    node_indices: Dict[Tuple[int, ...], np.ndarray]
    edge_indices: Dict[Tuple[int, ...], np.ndarray]
    edge_source_local: Dict[Tuple[int, ...], np.ndarray]
    edge_target_local: Dict[Tuple[int, ...], np.ndarray]

    def payload(self) -> Dict[str, Any]:
        return {
            "contexts": [list(context) for context in self.contexts],
            "nodes_per_context": {
                str(list(context)): int(self.node_indices[context].shape[0])
                for context in self.contexts
            },
            "edges_per_context": {
                str(list(context)): int(self.edge_indices[context].shape[0])
                for context in self.contexts
            },
            "edge_local_offsets": (
                "local indices are positions in the ascending canonical node "
                "index array of that context"
            ),
        }


@dataclass
class GraphData:
    """Unique binary directed edges plus their audited source structure."""

    data_name: str
    published: bool
    source_path: str
    source_sha256: str
    node_count: int
    edges: np.ndarray  # int64 [E, 2] sorted unique (source, target)
    raw_rows: int
    unique_edges: int
    duplicate_rows: int
    multiplicity: Dict[str, Any]
    self_loop_rows: int
    symmetry_rate: float
    block_diagonal: bool
    columns: Tuple[str, ...]
    node_keys_sha256: str
    audit: Dict[str, Any] = field(default_factory=dict)
    publication: Optional[Dict[str, Any]] = None

    @property
    def edge_count(self) -> int:
        return int(self.edges.shape[0])

    def identity_payload(self) -> Dict[str, Any]:
        return {
            "dataset": self.data_name,
            "published": self.published,
            "source_kind": "published" if self.published else "fixture",
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "columns": list(self.columns),
            "node_keys_sha256": self.node_keys_sha256,
            "nodes": self.node_count,
            "raw_rows": self.raw_rows,
            "unique_edges": self.unique_edges,
            "duplicate_rows": self.duplicate_rows,
            "self_loop_rows": self.self_loop_rows,
            "edges_sha256": edge_set_sha256(self.edges),
            "symmetry_rate": self.symmetry_rate,
            "block_diagonal": self.block_diagonal,
        }


def canonical_edge_array(edges: Sequence[Sequence[int]]) -> np.ndarray:
    """Return unique int64 edges sorted lexicographically by (source, target)."""
    array = np.asarray(edges, dtype=np.int64)
    if array.size == 0:
        return np.zeros((0, 2), dtype=np.int64)
    if array.ndim != 2 or array.shape[1] != 2:
        raise GraphError(f"edges must have shape [E, 2], got {array.shape}")
    unique = np.unique(array, axis=0)
    return np.ascontiguousarray(unique.astype(np.int64))


def edge_set_sha256(edges: np.ndarray) -> str:
    """Hash a canonical edge set independent of source row order."""
    array = canonical_edge_array(edges)
    digest = hashlib.sha256()
    digest.update(b"int64-le:")
    digest.update(str(tuple(array.shape)).encode("ascii"))
    digest.update(b"\0")
    digest.update(np.ascontiguousarray(array.astype("<i8")).tobytes(order="C"))
    return digest.hexdigest()


def _validated_endpoint_array(
    frame: Any, columns: Sequence[str], data_name: str
) -> np.ndarray:
    """Validate integer endpoints before any narrowing conversion."""
    try:
        values = np.asarray(frame[list(columns)].to_numpy(dtype=np.float64))
    except (TypeError, ValueError) as exc:
        raise GraphError(
            f"{data_name}: graph endpoint columns must be numeric: {exc}"
        ) from exc
    if values.ndim != 2 or values.shape[1] != len(columns):
        raise GraphError(
            f"{data_name}: endpoint columns must be [rows, {len(columns)}], "
            f"got {values.shape}"
        )
    if not np.isfinite(values).all():
        raise GraphError(f"{data_name}: graph table contains nonfinite endpoints")
    if not np.equal(values, np.floor(values)).all():
        raise GraphError(f"{data_name}: graph table contains non-integer endpoints")
    if (values.astype(np.float64) > float(2**63 - 1)).any() or (
        values < float(-(2**63))
    ).any():
        raise GraphError(f"{data_name}: graph endpoint is outside the int64 range")
    return np.ascontiguousarray(values.astype(np.int64))


def _key_index(key_array: np.ndarray) -> Dict[Tuple[int, ...], int]:
    return {
        tuple(int(value) for value in row): index
        for index, row in enumerate(key_array.tolist())
    }


def load_graph(
    data_name: str,
    key_array: np.ndarray,
    *,
    graph_path: Optional[Path] = None,
    published: Optional[bool] = None,
) -> GraphData:
    """Read, validate and canonicalize a context-qualified graph table."""
    import pandas as pd

    protocol.validate_dataset_name(data_name)
    key_array = np.asarray(key_array, dtype=np.int64)
    context_columns = tuple(p01.context_columns(data_name))
    path = Path(graph_path) if graph_path is not None else p01.graph_path(data_name)
    if published is None:
        published = path.resolve() == p01.graph_path(data_name).resolve()
    if not path.exists():
        raise GraphError(f"{data_name}: graph source does not exist: {path}")
    try:
        frame = pd.read_parquet(path)
    except (OSError, ValueError) as exc:
        raise GraphError(f"{data_name}: cannot read graph source {path}: {exc}") from exc
    columns = tuple(str(column) for column in frame.columns)
    required = context_columns + (ROW_COLUMN, COLUMN_COLUMN)
    missing = [column for column in required if column not in columns]
    if missing:
        raise GraphError(
            f"{data_name}: graph table is missing column(s) {missing}; actual "
            f"columns: {list(columns)}"
        )
    forbidden = [
        column
        for column in columns
        if column not in required
        and (
            column.lower() in FORBIDDEN_COLUMNS
            or "weight" in column.lower()
            or "frequenc" in column.lower()
        )
    ]
    if forbidden:
        raise GraphError(
            f"{data_name}: graph table must not carry independent weight/"
            f"frequency column(s) {forbidden}"
        )
    extra = [column for column in columns if column not in required]
    if published and (extra or set(columns) != set(required)):
        raise GraphError(
            f"{data_name}: published graph columns must be exactly {list(required)}, "
            f"got {list(columns)}"
        )

    raw_rows = int(frame.shape[0])
    if raw_rows == 0:
        raise GraphError(f"{data_name}: graph source has no rows")
    endpoint_values = _validated_endpoint_array(
        frame, required, data_name
    )
    index = _key_index(key_array)
    context_width = len(context_columns)
    contexts = endpoint_values[:, :context_width]
    row_ids = endpoint_values[:, context_width]
    col_ids = endpoint_values[:, context_width + 1]

    source_keys: List[Tuple[int, ...]] = []
    target_keys: List[Tuple[int, ...]] = []
    source_indices = np.empty(raw_rows, dtype=np.int64)
    target_indices = np.empty(raw_rows, dtype=np.int64)
    unmatched: List[Dict[str, Any]] = []
    self_loops: List[Dict[str, Any]] = []
    for position in range(raw_rows):
        context_key = tuple(int(value) for value in contexts[position])
        left = context_key + (int(row_ids[position]),)
        right = context_key + (int(col_ids[position]),)
        left_index = index.get(left)
        right_index = index.get(right)
        if left_index is None or right_index is None:
            if len(unmatched) < 5:
                unmatched.append(
                    {
                        "row": position,
                        "column": ROW_COLUMN if left_index is None else COLUMN_COLUMN,
                        "endpoint": list(left if left_index is None else right),
                    }
                )
            continue
        if left == right:
            if len(self_loops) < 5:
                self_loops.append({"row": position, "endpoint": list(left)})
            continue
        source_keys.append(left)
        target_keys.append(right)
        source_indices[position] = left_index
        target_indices[position] = right_index
    if unmatched:
        raise GraphError(
            f"{data_name}: graph endpoint(s) do not match canonical demand nodes: "
            f"{unmatched}"
        )
    if self_loops:
        raise GraphError(
            f"{data_name}: self-loop rows are not allowed in the message graph: "
            f"{self_loops}"
        )

    pairs = np.stack([source_indices, target_indices], axis=1)
    unique, counts = np.unique(pairs, axis=0, return_counts=True)
    edges = np.ascontiguousarray(unique.astype(np.int64))
    unique_edges = int(edges.shape[0])
    duplicate_rows = int(raw_rows - unique_edges)
    multiplicity_counts = np.unique(counts, return_counts=True)
    multiplicity = {
        "distribution": {
            str(int(value)): int(number)
            for value, number in zip(multiplicity_counts[0], multiplicity_counts[1])
        },
        "max_multiplicity": int(counts.max()) if counts.size else 0,
        "duplicate_rows": duplicate_rows,
        "weights_edges": False,
        "is_observed_frequency": False,
        "binary_adjacency": True,
        "note": (
            "multiplicity is an audit of repeated source rows; each distinct "
            "context-qualified directed edge contributes exactly once to the "
            "incoming-neighbour mean"
        ),
    }

    edge_set = {(int(left), int(right)) for left, right in edges.tolist()}
    reverse_present = sum(
        1 for source, target in edge_set if (target, source) in edge_set
    )
    symmetry_rate = reverse_present / unique_edges
    context_of_node = {
        index_: tuple(int(value) for value in key_array[index_].tolist()[:-1])
        for index_ in range(key_array.shape[0])
    }
    cross_context = sum(
        1
        for source, target in edge_set
        if context_of_node[source] != context_of_node[target]
    )
    block_diagonal = cross_context == 0

    publication: Optional[Dict[str, Any]] = None
    if published:
        expected_rows = protocol.published_graph_rows(data_name)
        problems: List[str] = []
        if raw_rows != expected_rows:
            problems.append(f"row count {raw_rows} != {expected_rows}")
        if duplicate_rows != 0:
            problems.append(f"{duplicate_rows} duplicate rows")
        if symmetry_rate != 1.0:
            problems.append(f"reverse-edge symmetry rate {symmetry_rate} != 1.0")
        if not block_diagonal:
            problems.append(f"{cross_context} cross-context edges")
        if problems:
            raise GraphError(
                f"{data_name}: published graph structure violated: "
                + "; ".join(problems)
            )
        # Context block isolation must be exact: each context's node index range
        # is contiguous and edges never leave it.
        ordinals = {
            context: position
            for position, context in enumerate(
                sorted({context_of_node[index_] for index_ in range(key_array.shape[0])})
            )
        }
        bad_offset = 0
        for source, target in edge_set:
            for node in (source, target):
                context = context_of_node[node]
                expected_index = (
                    ordinals[context] * protocol.PUBLISHED_CONTEXT_STRIDE
                    + int(key_array[node, -1])
                )
                if expected_index != node:
                    bad_offset += 1
        if bad_offset:
            raise GraphError(
                f"{data_name}: {bad_offset} published edge endpoints violate the "
                "dense context offset formula"
            )
        publication = {
            "dataset": data_name,
            "raw_rows": raw_rows,
            "unique_edges": unique_edges,
            "duplicate_rows": duplicate_rows,
            "self_loop_rows": 0,
            "symmetry_rate": symmetry_rate,
            "block_diagonal": True,
            "cross_context_edges": 0,
            "columns": list(columns),
            "weight_or_frequency_column": False,
            "dense_offset_proven_endpoints": int(2 * unique_edges),
            "expected_rows": expected_rows,
        }

    audit = {
        "dataset": data_name,
        "source_kind": "published" if published else "fixture",
        "source_path": str(path),
        "source_sha256": sha256_file(path),
        "columns": list(columns),
        "raw_rows": raw_rows,
        "unique_edges": unique_edges,
        "duplicate_rows": duplicate_rows,
        "multiplicity": multiplicity,
        "self_loop_rows": 0,
        "rejected_self_loop_rows": len(self_loops),
        "symmetry_rate": symmetry_rate,
        "reverse_edge_symmetry_is_not_a_fixture_requirement": True,
        "block_diagonal": block_diagonal,
        "cross_context_edges": int(cross_context),
        "contexts": sorted(sorted(context) for context in set(context_of_node.values())),
        "direction": "row_id -> col_id (source -> target); incoming edges are aggregated",
        "publication": publication,
    }
    return GraphData(
        data_name=data_name,
        published=bool(published),
        source_path=str(path),
        source_sha256=sha256_file(path),
        node_count=int(key_array.shape[0]),
        edges=edges,
        raw_rows=raw_rows,
        unique_edges=unique_edges,
        duplicate_rows=duplicate_rows,
        multiplicity=multiplicity,
        self_loop_rows=0,
        symmetry_rate=float(symmetry_rate),
        block_diagonal=bool(block_diagonal),
        columns=columns,
        node_keys_sha256=node_keys_sha256(key_array),
        audit=audit,
        publication=publication,
    )


def from_arrays(
    data_name: str,
    key_array: np.ndarray,
    rows: Sequence[Sequence[int]],
    *,
    source_path: str = "<in-memory fixture>",
    source_sha256: str = "in-memory",
    published: bool = False,
) -> GraphData:
    """Build a fixture graph from already context-qualified integer rows."""
    import pandas as pd
    import tempfile

    context_columns = list(p01.context_columns(data_name))
    frame = pd.DataFrame(
        np.asarray(rows, dtype=np.int64),
        columns=context_columns + [ROW_COLUMN, COLUMN_COLUMN],
    )
    with tempfile.TemporaryDirectory(prefix="gvs-graph-fixture-") as temporary:
        path = Path(temporary) / f"{data_name}.parquet"
        frame.to_parquet(path, index=False)
        graph = load_graph(
            data_name, key_array, graph_path=path, published=published
        )
    graph.source_path = source_path
    graph.source_sha256 = source_sha256
    graph.audit["source_path"] = source_path
    graph.audit["source_sha256"] = source_sha256
    return graph


def node_keys_sha256(key_array: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(key_array, dtype="<i8"))
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def context_layout(key_array: np.ndarray, edges: np.ndarray) -> ContextLayout:
    """Split canonical nodes and edges into complete per-context subsets."""
    keys = np.asarray(key_array, dtype=np.int64)
    contexts = sorted({tuple(int(v) for v in row) for row in keys[:, :-1].tolist()})
    node_indices: Dict[Tuple[int, ...], np.ndarray] = {}
    global_to_local: Dict[int, int] = {}
    for context in contexts:
        members = np.array(
            [
                index
                for index, key in enumerate(keys.tolist())
                if tuple(int(v) for v in key[:-1]) == context
            ],
            dtype=np.int64,
        )
        node_indices[context] = members
        for local, global_index in enumerate(members.tolist()):
            global_to_local[int(global_index)] = local
    edge_source_local: Dict[Tuple[int, ...], np.ndarray] = {}
    edge_target_local: Dict[Tuple[int, ...], np.ndarray] = {}
    edge_indices: Dict[Tuple[int, ...], np.ndarray] = {}
    for context in contexts:
        members = set(int(value) for value in node_indices[context].tolist())
        selected: List[int] = []
        sources: List[int] = []
        targets: List[int] = []
        for position, (source, target) in enumerate(edges.tolist()):
            if int(source) in members and int(target) in members:
                selected.append(position)
                sources.append(global_to_local[int(source)])
                targets.append(global_to_local[int(target)])
            elif int(source) in members or int(target) in members:
                raise GraphError(
                    f"edge {source}->{target} crosses the context {context}"
                )
        edge_indices[context] = np.asarray(selected, dtype=np.int64)
        edge_source_local[context] = np.asarray(sources, dtype=np.int64)
        edge_target_local[context] = np.asarray(targets, dtype=np.int64)
    return ContextLayout(
        contexts=contexts,
        node_indices=node_indices,
        edge_indices=edge_indices,
        edge_source_local=edge_source_local,
        edge_target_local=edge_target_local,
    )
