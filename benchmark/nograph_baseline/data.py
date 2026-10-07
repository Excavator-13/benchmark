"""Canonical demand loading, validation and descriptive audits.

The loader reproduces the diagnostic arithmetic of the v2 run exactly:
rows are sorted by their canonical key columns, the 36 monthly values become a
``float32`` array, and every audit is derived from that identity-aligned array.
Full 36-month diagnostics are descriptive only and never feed grouping,
fitting or selection.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import protocol
from .protocol import N_MONTHS, TRAIN_OBSERVATION_MONTHS

MONTH_COLUMN_PATTERN = re.compile(r"^\d{4}-\d{2}$")


class DemandError(ValueError):
    """Raised when the demand source violates the protocol contract."""


@dataclass
class DemandData:
    """Validated, canonically ordered demand values for one dataset."""

    data_name: str
    mode: str
    key_columns: Tuple[str, ...]
    keys: List[Tuple[int, ...]]
    key_array: np.ndarray  # int64 [N, K]
    signal: np.ndarray  # float32 [N, 36]
    audit: Dict[str, Any]
    source_path: str
    source_sha256: str
    n_months: int = N_MONTHS

    @property
    def node_count(self) -> int:
        return int(self.key_array.shape[0])

    @property
    def context_columns(self) -> Tuple[str, ...]:
        return self.key_columns[:-1]

    @property
    def skill_ids(self) -> np.ndarray:
        return self.key_array[:, -1]

    def signal_for_months(self, month_indices: Sequence[int]) -> np.ndarray:
        """Return ``float32`` values restricted to selected month indices."""
        index = np.asarray(list(month_indices), dtype=np.int64)
        return np.ascontiguousarray(self.signal[:, index])

    def input_windows(self, starts: Sequence[int]) -> np.ndarray:
        """Return stacked ``[windows, nodes, L]`` true-history inputs."""
        return np.stack(
            [
                self.signal[:, start : start + protocol.INPUT_LENGTH]
                for start in starts
            ]
        )

    def target_windows(self, starts: Sequence[int]) -> np.ndarray:
        """Return stacked ``[windows, nodes, H]`` observed targets."""
        offset = protocol.INPUT_LENGTH
        return np.stack(
            [
                self.signal[:, start + offset : start + offset + protocol.HORIZON]
                for start in starts
            ]
        )

    def identity_payload(self) -> Dict[str, Any]:
        """Canonical identity metadata saved with every run."""
        return {
            "dataset": self.data_name,
            "mode": self.mode,
            "key_columns": list(self.key_columns),
            "nodes": self.node_count,
            "node_keys_sha256": node_keys_sha256(self.key_array),
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
        }


def sha256_file(path: Path) -> str:
    """Return the hex SHA256 of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def node_keys_sha256(key_array: np.ndarray) -> str:
    """Hash the canonical ordered node keys.

    A fixed little-endian int64 encoding keeps the digest stable across
    platforms and independent of pandas/NumPy object pickling.
    """
    array = np.ascontiguousarray(np.asarray(key_array, dtype="<i8"))
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def _validated_key_array(
    raw: Any, key_columns: Sequence[str], data_name: str
) -> np.ndarray:
    """Validate and narrow node keys in their native representation.

    Fractional, nonfinite, non-numeric or out-of-int64-range keys are rejected
    before any narrowing conversion, so a lossy cast can never fabricate a
    valid identity.
    """
    values = np.asarray(raw)
    if values.ndim != 2 or values.shape[1] != len(key_columns):
        raise DemandError(
            f"{data_name}: keys must have shape [N, {len(key_columns)}], "
            f"got {values.shape}"
        )
    if np.issubdtype(values.dtype, np.bool_):
        raise DemandError(f"{data_name}: node key columns must be numeric, not boolean")
    if np.issubdtype(values.dtype, np.integer):
        info = np.iinfo(np.int64)
        if values.size:
            minimum = int(values.min())
            maximum = int(values.max())
            if minimum < info.min or maximum > info.max:
                raise DemandError(
                    f"{data_name}: node key outside the int64 range: "
                    f"{minimum}..{maximum}"
                )
        return np.ascontiguousarray(values.astype(np.int64, copy=False))
    if np.issubdtype(values.dtype, np.floating):
        floating = values.astype(np.float64, copy=False)
        if not np.isfinite(floating).all():
            raise DemandError(f"{data_name}: node key contains nonfinite values")
        if not np.equal(floating, np.floor(floating)).all():
            raise DemandError(f"{data_name}: node key contains non-integer values")
        # The valid int64 range is asymmetric: [-2**63, 2**63).  The inclusive
        # maximum must not be rounded to float(np.iinfo(int64).max) == 2**63,
        # which would let exactly 2**63 narrow to a different identity.
        upper_exclusive = float(2**63)
        lower_inclusive = float(-(2**63))
        if (floating >= upper_exclusive).any() or (floating < lower_inclusive).any():
            raise DemandError(
                f"{data_name}: node key outside the int64 range "
                "[-9223372036854775808, 9223372036854775807]"
            )
        narrowed = floating.astype(np.int64)
        if not np.equal(narrowed.astype(np.float64), floating).all():
            raise DemandError(
                f"{data_name}: node key identity changed during int64 narrowing"
            )
        return np.ascontiguousarray(narrowed)
    raise DemandError(
        f"{data_name}: node key columns must be integer or floating numeric, "
        f"got dtype {values.dtype}"
    )


def _validated_demand_values(
    raw: Any, expected_months: Sequence[str], data_name: str
) -> np.ndarray:
    """Validate native count values, then produce the ``float32`` signal.

    The diagnostic protocol stores demand as ``float32``, but validation runs on
    the original float64 values first so that a negative native count which
    underflows to ``-0.0`` at float32 cannot be accepted as nonnegative.
    """
    try:
        native = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise DemandError(
            f"{data_name}: demand month columns must be numeric: {exc}"
        ) from exc
    if native.ndim != 2 or native.shape[1] != len(expected_months):
        raise DemandError(
            f"{data_name}: expected {len(expected_months)} month columns, "
            f"got {native.shape}"
        )
    if not np.isfinite(native).all():
        raise DemandError(f"{data_name}: demand values contain NaN or infinity")
    if (native < 0).any():
        raise DemandError(f"{data_name}: demand values contain negatives")
    signal = native.astype(np.float32)
    # Post-conversion check: finite and aligned after narrowing.
    if signal.shape != native.shape or not np.isfinite(signal).all():
        raise DemandError(
            f"{data_name}: demand values are not finite after float32 conversion"
        )
    return np.ascontiguousarray(signal)


def load_demand(
    data_name: str,
    *,
    mode: str = "count",
    demand_path: Optional[Path] = None,
    months: Optional[Sequence[str]] = None,
) -> DemandData:
    """Read, validate and canonically order a demand Parquet table."""
    import pandas as pd

    protocol.validate_dataset_mode(data_name, mode)
    if mode != "count":
        raise DemandError(f"only count mode is implemented, got {mode!r}")
    key_columns = protocol.node_key_columns(data_name)
    expected_months = tuple(months) if months is not None else protocol.MONTHS
    path = Path(demand_path) if demand_path is not None else protocol.demand_path(data_name)
    if not path.exists():
        raise DemandError(f"demand source does not exist: {path}")
    source_sha256 = sha256_file(path)

    frame = pd.read_parquet(path)
    actual_month_columns = sorted(
        str(column) for column in frame.columns if MONTH_COLUMN_PATTERN.match(str(column))
    )
    missing = [month for month in expected_months if month not in actual_month_columns]
    extra = [month for month in actual_month_columns if month not in expected_months]
    if missing or extra:
        raise DemandError(
            f"{data_name}: month columns mismatch: missing={missing} extra={extra}"
        )

    missing_keys = [column for column in key_columns if column not in frame.columns]
    if missing_keys:
        raise DemandError(
            f"{data_name}: missing node key column(s) {missing_keys}; "
            f"actual columns: {list(frame.columns)}"
        )

    if frame.empty:
        raise DemandError(f"{data_name}: demand source has no rows")

    # Validate node identity before sorting so invalid rows are reported by key.
    # Keys are validated in their native representation so that narrowing to
    # int64 cannot turn a fractional or out-of-range key into valid data.
    identity = frame[list(key_columns)]
    if identity.duplicated().any():
        duplicated = identity[identity.duplicated()].head(5).to_dict("records")
        raise DemandError(f"{data_name}: duplicate node identity, examples: {duplicated}")
    _validated_key_array(identity.to_numpy(), key_columns, data_name)

    frame = frame.sort_values(list(key_columns), kind="stable").reset_index(drop=True)
    # Validate the native float64 values before the float32 diagnostic cast so
    # that a tiny negative count cannot underflow into an accepted -0.0.
    signal = _validated_demand_values(
        frame[list(expected_months)].to_numpy(), expected_months, data_name
    )

    key_array = _validated_key_array(
        frame[list(key_columns)].to_numpy(), key_columns, data_name
    )
    keys = [tuple(int(value) for value in row) for row in key_array.tolist()]
    audit = build_audit(
        data_name=data_name,
        mode=mode,
        key_columns=key_columns,
        key_array=key_array,
        signal=signal,
    )
    return DemandData(
        data_name=data_name,
        mode=mode,
        key_columns=key_columns,
        keys=keys,
        key_array=key_array,
        signal=signal,
        audit=audit,
        source_path=str(path),
        source_sha256=source_sha256,
        n_months=len(expected_months),
    )


def from_arrays(
    data_name: str,
    keys: Sequence[Sequence[int]],
    signal: np.ndarray,
    *,
    mode: str = "count",
    source_path: str = "<in-memory fixture>",
    source_sha256: str = "in-memory",
) -> DemandData:
    """Build a validated :class:`DemandData` from in-memory arrays.

    This is the reusable fixture-injection facility used by tests; it enforces
    the same identity and value contract as :func:`load_demand`.
    """
    protocol.validate_dataset_mode(data_name, mode)
    key_columns = protocol.node_key_columns(data_name)
    key_array = _validated_key_array(np.asarray(keys), key_columns, data_name)
    values = _validated_demand_values(np.asarray(signal), protocol.MONTHS, data_name)
    if values.shape[0] != key_array.shape[0]:
        raise DemandError(f"{data_name}: keys and signal have different row counts")
    # Canonical ascending order by key columns.
    order = np.lexsort(
        tuple(
            key_array[:, column]
            for column in range(key_array.shape[1] - 1, -1, -1)
        )
    )
    key_array = np.ascontiguousarray(key_array[order])
    values = np.ascontiguousarray(values[order])
    if np.unique(key_array, axis=0).shape[0] != key_array.shape[0]:
        raise DemandError(f"{data_name}: duplicate node identity in fixture keys")
    audit = build_audit(
        data_name=data_name,
        mode=mode,
        key_columns=key_columns,
        key_array=key_array,
        signal=values,
    )
    return DemandData(
        data_name=data_name,
        mode=mode,
        key_columns=key_columns,
        keys=[tuple(int(value) for value in row) for row in key_array.tolist()],
        key_array=key_array,
        signal=values,
        audit=audit,
        source_path=source_path,
        source_sha256=source_sha256,
    )


def build_audit(
    *,
    data_name: str,
    mode: str,
    key_columns: Tuple[str, ...],
    key_array: np.ndarray,
    signal: np.ndarray,
) -> Dict[str, Any]:
    """Build the descriptive audit record for validated demand values."""
    node_count = int(signal.shape[0])
    context_columns = list(key_columns[:-1])
    skill_ids = key_array[:, -1]
    unique_skills = np.unique(skill_ids)
    context_counts: Dict[str, int] = {
        column: int(len(np.unique(key_array[:, index])))
        for index, column in enumerate(context_columns)
    }
    joint_contexts = int(
        np.unique(key_array[:, : len(context_columns)], axis=0).shape[0]
    )
    cartesian = 1
    for count in context_counts.values():
        cartesian *= count
    expected_nodes = joint_contexts * len(unique_skills)

    train_count = protocol.TRAIN_OBSERVATION_MONTH_COUNT
    activity = (signal[:, :train_count] > 0).mean(axis=1)
    train_all_zero = activity == 0
    full_all_zero = (signal == 0).all(axis=1)
    train_std = signal[:, :train_count].astype(np.float64).std(axis=1, ddof=0)
    constant_nodes = train_std == 0

    groups = activity_group_masks(activity)
    per_context: Dict[str, Any] = {}
    for index, column in enumerate(context_columns):
        per_context[column] = {}
        for value in np.unique(key_array[:, index]):
            mask = key_array[:, index] == value
            per_context[column][str(int(value))] = {
                "nodes": int(mask.sum()),
                "train_all_zero_fraction": float(train_all_zero[mask].mean())
                if mask.any()
                else None,
                "full_36_month_all_zero_fraction": float(full_all_zero[mask].mean())
                if mask.any()
                else None,
                "mean_train_value": float(
                    signal[mask, :train_count].astype(np.float64).mean()
                )
                if mask.any()
                else None,
            }

    audit: Dict[str, Any] = {
        "dataset": data_name,
        "mode": mode,
        "key_columns": list(key_columns),
        "nodes": node_count,
        "skill_id_nunique": int(len(unique_skills)),
        "context_id_counts": context_counts,
        "joint_contexts": joint_contexts,
        "context_cartesian_size": cartesian,
        "expected_context_skill_nodes": expected_nodes,
        "is_complete_context_skill_grid": node_count == expected_nodes,
        "train_observation_months": list(TRAIN_OBSERVATION_MONTHS),
        "train_all_zero_fraction": float(train_all_zero.mean()),
        "full_36_month_all_zero_fraction_diagnostic_only": float(full_all_zero.mean()),
        "constant_node_count_train27": int(constant_nodes.sum()),
        "constant_node_fraction_train27": float(constant_nodes.mean()),
        "activity_group_counts": {
            name: int(mask.sum()) for name, mask in groups.items()
        },
        "monthly_nonzero_fraction": [
            float((signal[:, index] > 0).mean()) for index in range(signal.shape[1])
        ],
        "value_range": {
            "min": float(signal.min()),
            "max": float(signal.max()),
            "train27_min": float(signal[:, :train_count].min()),
            "train27_max": float(signal[:, :train_count].max()),
        },
        "per_context": per_context,
        "full_36_month_diagnostics_are_descriptive_only": True,
    }
    return audit


def activity_group_masks(activity: np.ndarray) -> Dict[str, np.ndarray]:
    """Return the four fixed training-activity masks in protocol order."""
    activity = np.asarray(activity, dtype=np.float64)
    masks = {
        "inactive": activity == 0,
        "low": (activity > 0) & (activity <= 1.0 / 3.0),
        "medium": (activity > 1.0 / 3.0) & (activity <= 2.0 / 3.0),
        "high": activity > 2.0 / 3.0,
    }
    stacked = np.stack(list(masks.values())).sum(axis=0)
    if not np.equal(stacked, 1).all():
        raise DemandError("activity masks do not partition the nodes")
    return masks


def iso_now() -> str:
    """Return a local ISO-8601 timestamp with offset."""
    from datetime import datetime

    return datetime.now().astimezone().isoformat(timespec="seconds")


def finite_or_none(value: float) -> Optional[float]:
    """Return ``value`` when finite, else ``None`` (JSON null)."""
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def dataclass_field_names(cls: Any) -> Tuple[str, ...]:
    """Expose dataclass field names (small helper for fixtures)."""
    return tuple(field.name for field in cls.__dataclass_fields__.values())
