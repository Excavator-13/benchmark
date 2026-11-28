"""Evaluation-only neighbour coverage annotation.

Both endpoints of every non-self graph row count as having a neighbour within
the same context; self-loop rows supply no neighbour; unmatched endpoints fail
validation.  A prevalidated identity-aligned mask bundle can be supplied
instead of the raw graph Parquet.  The annotation never influences
predictions, normalization, fitting or selection.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np

from . import protocol
from .data import sha256_file

COVERAGE_DEFINITION = (
    "context-qualified non-self endpoint coverage: a node has a neighbour when "
    "it is an endpoint (row_id or col_id) of a graph row whose row_id != col_id "
    "within the same context; self-loop rows supply no neighbour"
)
MASK_DEFINITION = (
    "context-qualified non-self endpoint coverage supplied as a prevalidated "
    "identity-aligned boolean mask"
)
#: Stable identifier for the only coverage semantics this protocol accepts.
#: A supplied mask must declare this id (or the exact canonical definition
#: text); a self-loop-counting or context-ignoring definition is rejected.
COVERAGE_DEFINITION_ID = "p1-count-L6-H3-context-qualified-nonself-endpoints-v1"
#: Accepted definition texts for compatibility with metadata-only bundles.
ACCEPTED_COVERAGE_DEFINITIONS = (COVERAGE_DEFINITION, MASK_DEFINITION)

ROW_COLUMN = "row_id"
COLUMN_COLUMN = "col_id"


class CoverageError(ValueError):
    """Raised when coverage evidence is missing or inconsistent."""


@dataclass
class CoverageMask:
    """A validated boolean neighbour mask plus its provenance."""

    mask: np.ndarray  # bool [N]
    provenance: Dict[str, Any]

    @property
    def covered(self) -> int:
        return int(self.mask.sum())

    @property
    def uncovered(self) -> int:
        return int((~self.mask).sum())


def coverage_groups(mask: np.ndarray) -> Dict[str, np.ndarray]:
    """Return the two fixed neighbour-group masks."""
    covered = np.asarray(mask, dtype=bool)
    return {"has_nonself_neighbor": covered, "no_nonself_neighbor": ~covered}


def _key_index(key_array: np.ndarray) -> Dict[Tuple[int, ...], int]:
    return {
        tuple(int(value) for value in row): index
        for index, row in enumerate(key_array.tolist())
    }


def load_graph_coverage(
    data_name: str,
    key_array: np.ndarray,
    *,
    graph_path: Optional[Path] = None,
) -> CoverageMask:
    """Derive the neighbour mask from the raw context-qualified graph table."""
    import pandas as pd

    context = protocol.context_columns(data_name)
    key_columns = protocol.node_key_columns(data_name)
    path = Path(graph_path) if graph_path is not None else protocol.graph_path(data_name)
    if not path.exists():
        raise CoverageError(
            f"{data_name}: missing coverage evidence at {path}; a formal run "
            "requires the raw graph table or a validated mask bundle"
        )
    source_sha256 = sha256_file(path)
    frame = pd.read_parquet(path)
    required = list(context) + [ROW_COLUMN, COLUMN_COLUMN]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise CoverageError(
            f"{data_name}: graph table is missing column(s) {missing}; "
            f"actual columns: {list(frame.columns)}"
        )
    endpoints = frame[required].to_numpy(dtype=np.float64)
    if not np.isfinite(endpoints).all():
        raise CoverageError(f"{data_name}: graph table contains nonfinite endpoints")
    if not np.equal(endpoints, np.floor(endpoints)).all():
        raise CoverageError(f"{data_name}: graph table contains non-integer endpoints")

    index = _key_index(key_array)
    mask = np.zeros(key_array.shape[0], dtype=bool)
    source_rows = int(frame.shape[0])
    self_loop_rows = 0
    matched_rows = 0
    unmatched_examples: List[Dict[str, Any]] = []
    context_values = frame[list(context)].to_numpy(dtype=np.int64)
    row_ids = frame[ROW_COLUMN].to_numpy(dtype=np.int64)
    col_ids = frame[COLUMN_COLUMN].to_numpy(dtype=np.int64)
    for position in range(source_rows):
        context_key = tuple(int(value) for value in context_values[position])
        left = context_key + (int(row_ids[position]),)
        right = context_key + (int(col_ids[position]),)
        # Validate context-qualified membership of every endpoint first, so a
        # self-loop cannot hide an unknown node reference from validation.
        left_index = index.get(left)
        right_index = index.get(right)
        if left_index is None or right_index is None:
            if len(unmatched_examples) < 5:
                unmatched_examples.append(
                    {
                        "row": position,
                        "endpoint": list(left if left_index is None else right),
                    }
                )
            continue
        if left == right:
            # A valid self-loop supplies no neighbour; both endpoints are the
            # same known node.
            self_loop_rows += 1
            continue
        mask[left_index] = True
        mask[right_index] = True
        matched_rows += 1
    if unmatched_examples:
        raise CoverageError(
            f"{data_name}: {len(unmatched_examples)}+ graph endpoints do not match "
            f"canonical demand node keys, examples: {unmatched_examples}"
        )
    provenance = {
        "definition": COVERAGE_DEFINITION,
        "source": "raw_graph_parquet",
        "source_path": str(path),
        "source_sha256": source_sha256,
        "graph_columns": list(frame.columns),
        "directed_source_rows": source_rows,
        "self_loop_rows": self_loop_rows,
        "non-self rows used": matched_rows,
        "covered_nodes": int(mask.sum()),
        "nodes": int(mask.shape[0]),
        "coverage_fraction": float(mask.mean()) if mask.size else None,
        "key_columns": list(key_columns),
        "node_keys_sha256": hashlib.sha256(
            np.ascontiguousarray(key_array, dtype="<i8").tobytes()
        ).hexdigest(),
        "used_for_forecasting": False,
    }
    return CoverageMask(mask=mask, provenance=provenance)


def build_fixture_coverage(
    data_name: str, key_array: np.ndarray, mask: np.ndarray
) -> CoverageMask:
    """Build an in-memory coverage mask for CPU tests without graph files."""
    key_array = np.asarray(key_array, dtype=np.int64)
    values = np.asarray(mask, dtype=bool)
    if values.shape != (key_array.shape[0],):
        raise CoverageError(
            f"fixture mask shape {values.shape} does not match {key_array.shape[0]} nodes"
        )
    provenance = {
        "definition": COVERAGE_DEFINITION,
        "source": "in_memory_fixture",
        "source_path": "<fixture>",
        "source_sha256": None,
        "covered_nodes": int(values.sum()),
        "nodes": int(values.shape[0]),
        "coverage_fraction": float(values.mean()) if values.size else None,
        "key_columns": list(protocol.node_key_columns(data_name)),
        "used_for_forecasting": False,
        "fixture": True,
    }
    return CoverageMask(mask=values, provenance=provenance)


def _is_sha256_hex(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value.lower()
    )


def save_mask_bundle(path: Path, data_name: str, key_array: np.ndarray, mask: np.ndarray, provenance: Mapping[str, Any]) -> Dict[str, Any]:
    """Write an identity-aligned mask bundle that can be reloaded without pickle.

    The supplied provenance must record the SHA256 of the original coverage
    source; a bundle without traceable derivation is refused.
    """
    key_array = np.asarray(key_array, dtype=np.int64)
    values = np.asarray(mask, dtype=bool)
    provenance = dict(provenance)
    if not _is_sha256_hex(provenance.get("source_sha256")):
        raise CoverageError(
            "mask bundle provenance must record the 64-hex SHA256 of the "
            "original coverage source"
        )
    # The stored definition is always the protocol's canonical semantics; any
    # caller-supplied text is not trusted as the accepted definition.
    metadata = {
        "dataset": data_name,
        "key_columns": list(protocol.node_key_columns(data_name)),
        "definition": COVERAGE_DEFINITION,
        "definition_id": COVERAGE_DEFINITION_ID,
        "provenance": provenance,
        "nodes": int(key_array.shape[0]),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        np.savez(
            handle,
            mask=values,
            node_keys=key_array,
            metadata=np.array(json.dumps(metadata, sort_keys=True)),
        )
    record = dict(metadata)
    record["path"] = str(path)
    record["bundle_sha256"] = sha256_file(path)
    return record


def load_mask_bundle(path: Path, data_name: str, key_array: np.ndarray) -> CoverageMask:
    """Load and validate a prevalidated identity-aligned mask bundle.

    A bundle accepted for a formal run must declare its dataset, canonical key
    schema, coverage definition and the SHA256 of the original coverage source.
    The bundle's own hash authenticates its bytes but cannot replace that
    provenance. In-memory synthetic masks use
    :func:`build_fixture_coverage` instead of a bundle.
    """
    path = Path(path)
    if not path.exists():
        raise CoverageError(f"neighbour mask bundle does not exist: {path}")
    bundle_sha256 = sha256_file(path)
    with np.load(path, allow_pickle=False) as handle:
        missing_arrays = [
            name for name in ("mask", "node_keys", "metadata") if name not in handle
        ]
        if missing_arrays:
            raise CoverageError(
                f"{path}: mask bundle is missing required array(s) {missing_arrays}"
            )
        raw_mask = handle["mask"]
        raw_keys = handle["node_keys"]
        raw_metadata = handle["metadata"]
    if raw_mask.dtype != np.bool_:
        raise CoverageError(
            f"{path}: mask array must be boolean, got dtype {raw_mask.dtype}"
        )
    if not np.issubdtype(raw_keys.dtype, np.integer):
        raise CoverageError(
            f"{path}: node_keys array must be integer, got dtype {raw_keys.dtype}"
        )
    values = np.asarray(raw_mask, dtype=bool)
    bundle_keys = np.asarray(raw_keys, dtype=np.int64)
    try:
        metadata = json.loads(str(raw_metadata))
    except json.JSONDecodeError as exc:
        raise CoverageError(f"{path}: metadata is not valid JSON: {exc}") from exc
    if not isinstance(metadata, dict):
        raise CoverageError(f"{path}: metadata must be a JSON object")
    required_metadata = ("dataset", "key_columns", "definition", "provenance")
    missing_metadata = [name for name in required_metadata if not metadata.get(name)]
    if missing_metadata:
        raise CoverageError(
            f"{path}: mask bundle metadata must declare {missing_metadata}"
        )
    if metadata["dataset"] != data_name:
        raise CoverageError(
            f"{path}: mask bundle declares dataset {metadata['dataset']!r}, "
            f"expected {data_name!r}"
        )
    expected_key_columns = list(protocol.node_key_columns(data_name))
    if list(metadata["key_columns"]) != expected_key_columns:
        raise CoverageError(
            f"{path}: mask bundle key columns {metadata['key_columns']} do not "
            f"match {expected_key_columns}"
        )
    definition = metadata["definition"]
    definition_id = metadata.get("definition_id")
    if not isinstance(definition, str) or not definition.strip():
        raise CoverageError(
            f"{path}: mask bundle definition must be a nonempty string"
        )
    if definition_id is not None:
        if definition_id != COVERAGE_DEFINITION_ID:
            raise CoverageError(
                f"{path}: mask bundle definition_id {definition_id!r} is not the "
                f"protocol coverage definition {COVERAGE_DEFINITION_ID!r}"
            )
    elif definition not in ACCEPTED_COVERAGE_DEFINITIONS:
        raise CoverageError(
            f"{path}: mask bundle definition is not the protocol's "
            "context-qualified non-self endpoint semantics"
        )
    bundle_provenance = metadata["provenance"]
    if not isinstance(bundle_provenance, dict):
        raise CoverageError(f"{path}: mask bundle provenance must be a JSON object")
    source_sha256 = bundle_provenance.get("source_sha256")
    if not _is_sha256_hex(source_sha256):
        raise CoverageError(
            f"{path}: mask bundle provenance must record the 64-hex SHA256 of "
            "the original coverage source"
        )
    expected = np.asarray(key_array, dtype=np.int64)
    if bundle_keys.shape != expected.shape:
        raise CoverageError(
            f"{path}: mask bundle key shape {bundle_keys.shape} != {expected.shape}"
        )
    if not np.array_equal(bundle_keys, expected):
        raise CoverageError(
            f"{path}: mask bundle node keys do not exactly match canonical demand keys"
        )
    if values.shape != (expected.shape[0],):
        raise CoverageError(
            f"{path}: mask length {values.shape} != {expected.shape[0]} nodes"
        )
    provenance = dict(bundle_provenance)
    provenance.update(
        {
            "source": "mask_bundle",
            "source_path": bundle_provenance.get("source_path"),
            "source_sha256": source_sha256,
            "bundle_path": str(path),
            "bundle_sha256": bundle_sha256,
            "definition": metadata["definition"],
            "definition_id": COVERAGE_DEFINITION_ID,
            "dataset": data_name,
            "key_columns": expected_key_columns,
            "covered_nodes": int(values.sum()),
            "nodes": int(values.shape[0]),
            "coverage_fraction": float(values.mean()) if values.size else None,
            "used_for_forecasting": False,
        }
    )
    return CoverageMask(mask=values, provenance=provenance)
