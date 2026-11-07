"""Train-only r2 loading, canonical identities and published assertions.

The loader reads the source schema and only the identity columns plus the 27
training month columns.  Values are forwarded at their native precision and
converted once to ``float64``; the source is never narrowed to the old
``float32`` diagnostic signal.  Held-out month columns are named by schema
inspection but their values are never read, so held-out perturbations cannot
affect the training arrays or their canonical content identity.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from . import protocol

__all__ = [
    "SourceError",
    "TrainingData",
    "TargetKeyData",
    "load_training",
    "training_from_arrays",
    "load_target_keys",
    "target_keys_from_arrays",
    "sha256_file",
    "array_sha256",
    "canonical_key_sha256",
    "grid_keys",
    "validate_integer_keys",
    "validate_complete_grid",
    "assert_published_training",
    "assert_published_target",
    "training_content_identity",
]


class SourceError(ValueError):
    """Raised when a source or target table violates the protocol contract."""


# ---------------------------------------------------------------------------
# canonical hashing and validation helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    """Return the hex SHA256 of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_array_bytes(array: np.ndarray) -> bytes:
    """Return dtype, shape and C-order little-endian bytes for a numeric array."""
    values = np.ascontiguousarray(np.asarray(array))
    if values.dtype.byteorder == ">":
        values = values.astype(values.dtype.newbyteorder("<"))
    elif values.dtype.byteorder == "=" and values.dtype.itemsize > 1:
        # Normalise the native marker so the digest is platform independent.
        values = values.astype(values.dtype.newbyteorder("<"))
    header = f"{values.dtype.str}|{','.join(str(dim) for dim in values.shape)}|".encode(
        "ascii"
    )
    return header + values.tobytes(order="C")


def array_sha256(array: np.ndarray) -> str:
    """Hash a numeric array's canonical bytes without pickling."""
    return hashlib.sha256(_canonical_array_bytes(array)).hexdigest()


def canonical_key_sha256(key_array: np.ndarray) -> str:
    """Hash canonical ordered integer keys as little-endian int64."""
    values = np.ascontiguousarray(np.asarray(key_array, dtype="<i8"))
    return hashlib.sha256(values.tobytes(order="C")).hexdigest()


def grid_keys(contexts: np.ndarray, skills: np.ndarray) -> np.ndarray:
    """Return the canonical context-major ``(context, skill)`` key grid."""
    return np.stack(
        np.meshgrid(
            np.asarray(contexts, dtype=np.int64),
            np.asarray(skills, dtype=np.int64),
            indexing="ij",
        ),
        axis=-1,
    ).reshape(-1, 2)


def validate_integer_keys(raw: Any, key_columns: Sequence[str], label: str) -> np.ndarray:
    """Validate integer keys in their native representation.

    Fractional, nonfinite, non-numeric and out-of-int64-range values are rejected
    before any narrowing conversion so a lossy cast cannot fabricate a valid
    identity.
    """
    values = np.asarray(raw)
    if values.ndim != 2 or values.shape[1] != len(key_columns):
        raise SourceError(
            f"{label}: keys must have shape [N, {len(key_columns)}], got {values.shape}"
        )
    if np.issubdtype(values.dtype, np.bool_):
        raise SourceError(f"{label}: key columns must be numeric, not boolean")
    if np.issubdtype(values.dtype, np.integer):
        info = np.iinfo(np.int64)
        if values.size:
            minimum = int(values.min())
            maximum = int(values.max())
            if minimum < info.min or maximum > info.max:
                raise SourceError(
                    f"{label}: key outside the int64 range: {minimum}..{maximum}"
                )
        return np.ascontiguousarray(values.astype(np.int64, copy=False))
    if np.issubdtype(values.dtype, np.floating):
        floating = values.astype(np.float64, copy=False)
        if not np.isfinite(floating).all():
            raise SourceError(f"{label}: key contains nonfinite values")
        if not np.equal(floating, np.floor(floating)).all():
            raise SourceError(f"{label}: key contains non-integer values")
        upper_exclusive = float(2**63)
        lower_inclusive = float(-(2**63))
        if (floating >= upper_exclusive).any() or (floating < lower_inclusive).any():
            raise SourceError(
                f"{label}: key outside the int64 range "
                "[-9223372036854775808, 9223372036854775807]"
            )
        narrowed = floating.astype(np.int64)
        if not np.equal(narrowed.astype(np.float64), floating).all():
            raise SourceError(f"{label}: key identity changed during int64 narrowing")
        return np.ascontiguousarray(narrowed)
    raise SourceError(
        f"{label}: key columns must be integer or floating numeric, got dtype "
        f"{values.dtype}"
    )


def validate_complete_grid(
    key_array: np.ndarray, key_columns: Sequence[str], label: str
) -> Tuple[np.ndarray, np.ndarray]:
    """Validate unique integer keys and a complete context x skill grid.

    Returns the sorted unique context and skill identities.  The grid check is
    exact: every context x skill pair appears exactly once.
    """
    contexts = np.unique(key_array[:, 0])
    skills = np.unique(key_array[:, -1])
    if contexts.size == 0 or skills.size == 0:
        raise SourceError(f"{label}: source has no context or skill identity")
    expected = int(contexts.size) * int(skills.size)
    if key_array.shape[0] != expected:
        raise SourceError(
            f"{label}: incomplete context x skill grid: {key_array.shape[0]} rows "
            f"for {contexts.size} contexts x {skills.size} skills = {expected}"
        )
    if np.unique(key_array, axis=0).shape[0] != key_array.shape[0]:
        raise SourceError(f"{label}: duplicate key identity")
    # Sorted canonical order plus the exact Cartesian count and no duplicates
    # proves every pair is present exactly once.
    expected_keys = np.stack(
        np.meshgrid(contexts, skills, indexing="ij"), axis=-1
    ).reshape(-1, 2)
    if not np.array_equal(key_array, expected_keys):
        raise SourceError(f"{label}: keys are not the complete canonical grid")
    return contexts, skills


def assert_published_training(contexts: np.ndarray, skills: np.ndarray, label: str) -> None:
    """Assert the frozen published r2 occupation/skill identities."""
    contexts_tuple = tuple(int(value) for value in contexts)
    if contexts_tuple != protocol.EXPECTED_OCCUPATION_IDS:
        raise SourceError(
            f"{label}: published occupation ids must be 0..51, got "
            f"{contexts_tuple[:3]}..{contexts_tuple[-3:]}"
        )
    skills_tuple = tuple(int(value) for value in skills)
    if skills_tuple != protocol.EXPECTED_SKILL_IDS:
        raise SourceError(
            f"{label}: published skill ids must be 0..2334, got "
            f"{skills_tuple[:3]}..{skills_tuple[-3:]}"
        )
    rows = len(contexts_tuple) * len(skills_tuple)
    if rows != protocol.EXPECTED_NODES:
        raise SourceError(
            f"{label}: published grid must have {protocol.EXPECTED_NODES} rows, "
            f"got {rows}"
        )


#: Published target context identities observed in the immutable demand files.
PUBLISHED_TARGET_CONTEXT_IDS: Mapping[str, Tuple[int, ...]] = {
    "r0": (0,),
    "region": tuple(range(7)),
    "r2": tuple(range(52)),
}


def assert_published_target(
    data_name: str, contexts: np.ndarray, skills: np.ndarray, label: str
) -> None:
    """Assert the published target identity ranges for one target table."""
    expected_contexts = PUBLISHED_TARGET_CONTEXT_IDS.get(data_name)
    if expected_contexts is None:  # pragma: no cover - protocol restricts names
        raise SourceError(f"{label}: unsupported target {data_name!r}")
    contexts_tuple = tuple(int(value) for value in contexts)
    skills_tuple = tuple(int(value) for value in skills)
    if contexts_tuple != expected_contexts:
        raise SourceError(
            f"{label}: published {data_name} context ids must be "
            f"{expected_contexts[0]}..{expected_contexts[-1]}, got "
            f"{contexts_tuple[:3]}..{contexts_tuple[-3:]}"
        )
    if skills_tuple != protocol.EXPECTED_SKILL_IDS:
        raise SourceError(
            f"{label}: published target skill ids must be 0..2334, got "
            f"{skills_tuple[:3]}..{skills_tuple[-3:]}"
        )


# ---------------------------------------------------------------------------
# training data
# ---------------------------------------------------------------------------


def _training_content_identity(
    *,
    months: Sequence[str],
    contexts: np.ndarray,
    skills: np.ndarray,
    observations: np.ndarray,
) -> Dict[str, Any]:
    """Hash the canonical training identity, never the held-out months."""
    digest = hashlib.sha256()
    digest.update(protocol.SCIENTIFIC_PROTOCOL_VERSION.encode("utf-8"))
    digest.update(b"\0")
    digest.update(",".join(months).encode("ascii"))
    digest.update(b"\0")
    digest.update(
        canonical_key_sha256(grid_keys(contexts, skills)).encode("ascii")
    )
    digest.update(b"\0")
    digest.update(_canonical_array_bytes(np.asarray(observations, dtype="<f8")))
    return {
        "algorithm": "sha256",
        "scope": (
            "protocol version + 27 training month labels + canonical context ids "
            "+ canonical skill ids + float64 training observations"
        ),
        "sha256": digest.hexdigest(),
        "includes_protocol_version": True,
        "includes_training_months": True,
        "includes_held_out_months": False,
        "months": list(months),
    }


def training_content_identity(
    *,
    months: Sequence[str],
    contexts: np.ndarray,
    skills: np.ndarray,
    observations: np.ndarray,
) -> Dict[str, Any]:
    """Public canonical training-content identity helper."""
    return _training_content_identity(
        months=months,
        contexts=contexts,
        skills=skills,
        observations=observations,
    )


@dataclass
class TrainingData:
    """Validated, canonically ordered r2 training observations."""

    source_data_name: str
    mode: str
    contexts: np.ndarray  # int64 [C]
    skills: np.ndarray  # int64 [S]
    observations: np.ndarray  # float64 [C, S, 27]
    key_columns: Tuple[str, ...]
    source_path: str
    source_sha256: str
    source_size_bytes: int
    source_schema: Dict[str, Any]
    file_identity: Dict[str, Any]
    content_identity: Dict[str, Any]
    fixture: bool
    published_assertions: Optional[Dict[str, Any]] = None
    native_dtypes: Dict[str, str] = field(default_factory=dict)

    @property
    def n_contexts(self) -> int:
        return int(self.contexts.shape[0])

    @property
    def n_skills(self) -> int:
        return int(self.skills.shape[0])

    @property
    def n_nodes(self) -> int:
        return self.n_skills

    @property
    def n_months(self) -> int:
        return int(self.observations.shape[2])

    @property
    def x(self) -> np.ndarray:
        """Training demand summed over the 27 unique months, ``[S, C]``."""
        return np.ascontiguousarray(self.observations.sum(axis=2).T)

    @property
    def support(self) -> np.ndarray:
        """Occupational support ``x > 0``, ``[S, C]``."""
        return np.ascontiguousarray(self.x > 0)

    @property
    def totals(self) -> np.ndarray:
        """Per-skill total training demand, ``[S]``."""
        return np.ascontiguousarray(self.x.sum(axis=1))

    @property
    def profiles(self) -> np.ndarray:
        """Demand composition ``x / sum(x)`` with zero vectors kept zero."""
        totals = self.totals
        denominator = np.where(totals > 0, totals, 1.0)
        profiles = self.x / denominator[:, None]
        profiles[totals == 0, :] = 0.0
        return np.ascontiguousarray(profiles)

    @property
    def occupational_support_counts(self) -> np.ndarray:
        """Per-skill count of occupations with positive training demand."""
        return np.ascontiguousarray(self.support.sum(axis=1, dtype=np.int64))

    def identity_payload(self) -> Dict[str, Any]:
        """Identity metadata saved with every build."""
        return {
            "source_data_name": self.source_data_name,
            "mode": self.mode,
            "key_columns": list(self.key_columns),
            "dimensions": {
                "occupations": self.n_contexts,
                "skills": self.n_skills,
                "training_months": self.n_months,
            },
            "fixture": self.fixture,
            "published_assertions": self.published_assertions,
            "file_identity": self.file_identity,
            "training_content_identity": self.content_identity,
            "node_keys_sha256": canonical_key_sha256(
                grid_keys(self.contexts, self.skills)
            ),
        }


def _validate_training_values(raw: Any, label: str) -> np.ndarray:
    """Validate native nonnegative finite values, then retain float64."""
    try:
        native = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise SourceError(f"{label}: training month columns must be numeric: {exc}") from exc
    if native.ndim != 2 or native.shape[1] != protocol.N_TRAIN_MONTHS:
        raise SourceError(
            f"{label}: expected {protocol.N_TRAIN_MONTHS} training month columns, "
            f"got {native.shape}"
        )
    if not np.isfinite(native).all():
        raise SourceError(f"{label}: training values contain NaN or infinity")
    if (native < 0).any():
        raise SourceError(f"{label}: training values contain negatives")
    return np.ascontiguousarray(native)


def _source_schema(path: Path) -> Dict[str, Any]:
    """Inspect the Parquet schema without reading any month values."""
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(path)
    schema = parquet.schema_arrow
    names = list(schema.names)
    month_columns = sorted(
        name for name in names if protocol.MONTH_COLUMN_PATTERN.match(str(name))
    )
    expected = list(protocol.MONTHS)
    missing = [month for month in expected if month not in month_columns]
    extra = [month for month in month_columns if month not in expected]
    if missing or extra:
        raise SourceError(
            f"{path}: source month columns mismatch: missing={missing} extra={extra}"
        )
    return {
        "path": str(path),
        "column_names": names,
        "month_columns": month_columns,
        "training_month_columns": list(protocol.TRAIN_MONTHS),
        "held_out_month_columns": list(protocol.MONTHS[protocol.N_TRAIN_MONTHS :]),
        "row_count": int(parquet.metadata.num_rows),
        "row_groups": int(parquet.metadata.num_row_groups),
    }


def load_training(
    path: Optional[Path] = None,
    *,
    fixture: bool = False,
    source: str = protocol.SOURCE_DATA_NAME,
    mode: str = protocol.MODE,
    fold: Optional[str] = None,
    protocol_version: str = protocol.SCIENTIFIC_PROTOCOL_VERSION,
) -> TrainingData:
    """Read, validate and canonically order the r2 training observations."""
    protocol.validate_scope(
        source=source, mode=mode, fold=fold, protocol_version=protocol_version
    )
    if source != protocol.SOURCE_DATA_NAME:
        raise SourceError(f"only {protocol.SOURCE_DATA_NAME!r} is implemented")
    source_path = Path(path) if path is not None else protocol.demand_path(source)
    if not source_path.exists():
        raise SourceError(f"training source does not exist: {source_path}")

    import pandas as pd

    source_sha256 = sha256_file(source_path)
    source_size = int(source_path.stat().st_size)
    schema = _source_schema(source_path)
    key_columns = tuple(protocol.SOURCE_KEY_COLUMNS)
    missing_keys = [name for name in key_columns if name not in schema["column_names"]]
    if missing_keys:
        raise SourceError(
            f"{source_path}: missing key column(s) {missing_keys}; "
            f"actual columns: {schema['column_names']}"
        )

    # Read only identity and training columns; held-out values are not loaded.
    frame = pd.read_parquet(
        source_path, columns=list(key_columns) + list(protocol.TRAIN_MONTHS)
    )
    if frame.empty:
        raise SourceError(f"{source_path}: training source has no rows")
    native_dtypes = {str(name): str(dtype) for name, dtype in frame.dtypes.items()}

    identity = frame[list(key_columns)]
    if identity.duplicated().any():
        examples = identity[identity.duplicated()].head(5).to_dict("records")
        raise SourceError(f"{source_path}: duplicate node identity, examples: {examples}")
    validate_integer_keys(identity.to_numpy(), key_columns, str(source_path))

    frame = frame.sort_values(list(key_columns), kind="stable").reset_index(drop=True)
    values = _validate_training_values(
        frame[list(protocol.TRAIN_MONTHS)].to_numpy(), str(source_path)
    )
    key_array = validate_integer_keys(
        frame[list(key_columns)].to_numpy(), key_columns, str(source_path)
    )
    contexts, skills = validate_complete_grid(key_array, key_columns, str(source_path))

    published_assertions: Optional[Dict[str, Any]] = None
    if not fixture:
        assert_published_training(contexts, skills, str(source_path))
        published_assertions = {
            "published": True,
            "occupation_ids": [int(contexts[0]), int(contexts[-1])],
            "skill_ids": [int(skills[0]), int(skills[-1])],
            "rows": int(key_array.shape[0]),
        }

    observations = np.ascontiguousarray(
        values.reshape(contexts.size, skills.size, protocol.N_TRAIN_MONTHS)
    )
    content_identity = _training_content_identity(
        months=protocol.TRAIN_MONTHS,
        contexts=contexts,
        skills=skills,
        observations=observations,
    )
    file_identity = {
        "path": str(source_path),
        "sha256": source_sha256,
        "size_bytes": source_size,
        "schema": schema,
        "native_dtypes": native_dtypes,
        "read_columns": list(key_columns) + list(protocol.TRAIN_MONTHS),
        "held_out_values_read": False,
    }
    return TrainingData(
        source_data_name=source,
        mode=mode,
        contexts=contexts,
        skills=skills,
        observations=observations,
        key_columns=key_columns,
        source_path=str(source_path),
        source_sha256=source_sha256,
        source_size_bytes=source_size,
        source_schema=schema,
        file_identity=file_identity,
        content_identity=content_identity,
        fixture=fixture,
        published_assertions=published_assertions,
        native_dtypes=native_dtypes,
    )


def training_from_arrays(
    contexts: Sequence[int],
    skills: Sequence[int],
    observations: np.ndarray,
    *,
    fixture: bool = True,
    source_path: str = "<in-memory fixture>",
    source_sha256: str = "in-memory",
) -> TrainingData:
    """Build validated :class:`TrainingData` directly from canonical arrays.

    This is the fixture-injection facility used by tests and by the CLI's
    explicit ``--fixture`` mode.  It enforces the same key, grid and value
    contract as :func:`load_training`.
    """
    context_values = np.asarray(contexts)
    skill_values = np.asarray(skills)
    if context_values.ndim != 1 or skill_values.ndim != 1:
        raise SourceError("contexts and skills must be one-dimensional")
    if np.issubdtype(context_values.dtype, np.floating) and not np.equal(
        context_values, np.floor(context_values)
    ).all():
        raise SourceError("context ids must be integers")
    if np.issubdtype(skill_values.dtype, np.floating) and not np.equal(
        skill_values, np.floor(skill_values)
    ).all():
        raise SourceError("skill ids must be integers")
    raw_contexts = context_values.astype(np.int64)
    raw_skills = skill_values.astype(np.int64)
    if np.unique(raw_contexts).size != raw_contexts.size:
        raise SourceError("context ids must be unique")
    if np.unique(raw_skills).size != raw_skills.size:
        raise SourceError("skill ids must be unique")
    context_order = np.argsort(raw_contexts, kind="stable")
    skill_order = np.argsort(raw_skills, kind="stable")
    context_array = np.ascontiguousarray(raw_contexts[context_order])
    skill_array = np.ascontiguousarray(raw_skills[skill_order])
    values = np.asarray(observations, dtype=np.float64)
    expected = (context_array.size, skill_array.size, protocol.N_TRAIN_MONTHS)
    if values.shape != expected:
        raise SourceError(
            f"observations must have shape {expected}, got {values.shape}"
        )
    if not np.isfinite(values).all():
        raise SourceError("observations contain NaN or infinity")
    if (values < 0).any():
        raise SourceError("observations contain negatives")
    values = np.ascontiguousarray(
        values[np.ix_(context_order, skill_order)]
    )
    content_identity = _training_content_identity(
        months=protocol.TRAIN_MONTHS,
        contexts=context_array,
        skills=skill_array,
        observations=values,
    )
    schema = {
        "path": source_path,
        "column_names": list(protocol.SOURCE_KEY_COLUMNS)
        + list(protocol.MONTHS),
        "month_columns": list(protocol.MONTHS),
        "training_month_columns": list(protocol.TRAIN_MONTHS),
        "held_out_month_columns": list(protocol.MONTHS[protocol.N_TRAIN_MONTHS :]),
        "row_count": int(context_array.size * skill_array.size),
        "row_groups": None,
    }
    file_identity = {
        "path": source_path,
        "sha256": source_sha256,
        "size_bytes": None,
        "schema": schema,
        "native_dtypes": {},
        "read_columns": list(protocol.SOURCE_KEY_COLUMNS)
        + list(protocol.TRAIN_MONTHS),
        "held_out_values_read": False,
    }
    return TrainingData(
        source_data_name=protocol.SOURCE_DATA_NAME,
        mode=protocol.MODE,
        contexts=context_array,
        skills=skill_array,
        observations=values,
        key_columns=protocol.SOURCE_KEY_COLUMNS,
        source_path=source_path,
        source_sha256=source_sha256,
        source_size_bytes=0,
        source_schema=schema,
        file_identity=file_identity,
        content_identity=content_identity,
        fixture=fixture,
        published_assertions=None,
        native_dtypes={},
    )


# ---------------------------------------------------------------------------
# target key-only data
# ---------------------------------------------------------------------------


@dataclass
class TargetKeyData:
    """Validated target identity keys for one predicted context granularity."""

    data_name: str
    contexts: np.ndarray  # int64 [C]
    skills: np.ndarray  # int64 [S]
    key_array: np.ndarray  # int64 [C*S, 2] canonical
    key_columns: Tuple[str, ...]
    source_path: str
    source_sha256: str
    source_size_bytes: int
    identity: Dict[str, Any]
    fixture: bool
    passed_skills: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int64))

    @property
    def n_contexts(self) -> int:
        return int(self.contexts.shape[0])

    @property
    def n_skills(self) -> int:
        return int(self.skills.shape[0])

    @property
    def n_keys(self) -> int:
        return int(self.key_array.shape[0])

    def identity_payload(self) -> Dict[str, Any]:
        return {
            "data_name": self.data_name,
            "key_columns": list(self.key_columns),
            "contexts": int(self.n_contexts),
            "skills": int(self.n_skills),
            "keys": int(self.n_keys),
            "keys_sha256": canonical_key_sha256(self.key_array),
            "identity": self.identity,
            "fixture": self.fixture,
            "passed_skills_sha256": array_sha256(self.passed_skills),
        }


def load_target_keys(
    data_name: str,
    path: Optional[Path] = None,
    *,
    fixture: bool = False,
    protocol_version: str = protocol.SCIENTIFIC_PROTOCOL_VERSION,
) -> TargetKeyData:
    """Read only a target table's identity columns and validate its grid."""
    protocol.validate_protocol_version(protocol_version)
    if data_name not in protocol.TARGET_DATA_NAMES:
        raise SourceError(
            f"unsupported target data name {data_name!r}; supported: "
            f"{list(protocol.TARGET_DATA_NAMES)}"
        )
    source_path = Path(path) if path is not None else protocol.target_demand_path(data_name)
    if not source_path.exists():
        raise SourceError(f"target source does not exist: {source_path}")
    import pandas as pd
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(source_path)
    names = list(parquet.schema_arrow.names)
    key_columns = tuple(protocol.TARGET_KEY_COLUMNS[data_name])
    missing = [name for name in key_columns if name not in names]
    if missing:
        raise SourceError(
            f"{source_path}: missing target key column(s) {missing}; "
            f"actual columns: {names}"
        )
    source_sha256 = sha256_file(source_path)
    source_size = int(source_path.stat().st_size)
    # Identity-only read: target demand values never enter mapping.
    frame = pd.read_parquet(source_path, columns=list(key_columns))
    if frame.empty:
        raise SourceError(f"{source_path}: target source has no rows")
    identity = frame[list(key_columns)]
    if identity.duplicated().any():
        examples = identity[identity.duplicated()].head(5).to_dict("records")
        raise SourceError(
            f"{source_path}: duplicate target identity, examples: {examples}"
        )
    validate_integer_keys(identity.to_numpy(), key_columns, str(source_path))
    frame = frame.sort_values(list(key_columns), kind="stable").reset_index(drop=True)
    key_array = validate_integer_keys(
        frame[list(key_columns)].to_numpy(), key_columns, str(source_path)
    )
    contexts, skills = validate_complete_grid(key_array, key_columns, str(source_path))
    if not fixture:
        assert_published_target(data_name, contexts, skills, str(source_path))
    identity_record = {
        "algorithm": "sha256",
        "scope": "canonical target context ids + canonical target skill ids",
        "sha256": canonical_key_sha256(key_array),
        "contexts": int(contexts.size),
        "skills": int(skills.size),
        "keys": int(key_array.shape[0]),
        "value_columns_read": False,
    }
    return TargetKeyData(
        data_name=data_name,
        contexts=contexts,
        skills=skills,
        key_array=key_array,
        key_columns=key_columns,
        source_path=str(source_path),
        source_sha256=source_sha256,
        source_size_bytes=source_size,
        identity=identity_record,
        fixture=fixture,
    )


def target_keys_from_arrays(
    data_name: str,
    contexts: Sequence[int],
    skills: Sequence[int],
    *,
    fixture: bool = True,
    source_path: str = "<in-memory fixture>",
    source_sha256: str = "in-memory",
) -> TargetKeyData:
    """Build validated :class:`TargetKeyData` from canonical identities."""
    if data_name not in protocol.TARGET_DATA_NAMES:
        raise SourceError(
            f"unsupported target data name {data_name!r}; supported: "
            f"{list(protocol.TARGET_DATA_NAMES)}"
        )
    context_array = np.ascontiguousarray(np.sort(np.asarray(contexts, dtype=np.int64)))
    skill_array = np.ascontiguousarray(np.sort(np.asarray(skills, dtype=np.int64)))
    if np.unique(context_array).size != context_array.size:
        raise SourceError("target context ids must be unique")
    if np.unique(skill_array).size != skill_array.size:
        raise SourceError("target skill ids must be unique")
    key_array = np.stack(
        np.meshgrid(context_array, skill_array, indexing="ij"), axis=-1
    ).reshape(-1, 2)
    identity_record = {
        "algorithm": "sha256",
        "scope": "canonical target context ids + canonical target skill ids",
        "sha256": canonical_key_sha256(key_array),
        "contexts": int(context_array.size),
        "skills": int(skill_array.size),
        "keys": int(key_array.shape[0]),
        "value_columns_read": False,
    }
    return TargetKeyData(
        data_name=data_name,
        contexts=context_array,
        skills=skill_array,
        key_array=np.ascontiguousarray(key_array.astype(np.int64)),
        key_columns=protocol.TARGET_KEY_COLUMNS[data_name],
        source_path=source_path,
        source_sha256=source_sha256,
        source_size_bytes=0,
        identity=identity_record,
        fixture=fixture,
    )
