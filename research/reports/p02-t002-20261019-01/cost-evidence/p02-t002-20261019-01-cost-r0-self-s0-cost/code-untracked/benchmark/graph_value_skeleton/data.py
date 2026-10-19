"""P01-identical demand identity, publication assertions and fixed masks.

Demand loading, validation, canonical ordering and the float32 signal are
delegated to ``benchmark.nograph_baseline.data`` so the new entry cannot drift
from P01.  Published-data executions re-assert the frozen node/context/skill
grid and the dense-context offset formula *before* any graph mapping or
training; small in-memory fixtures follow the same schemas without those sizes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from benchmark.nograph_baseline import baselines
from benchmark.nograph_baseline import coverage as p01_coverage
from benchmark.nograph_baseline import data as p01_data
from benchmark.nograph_baseline import protocol as p01
from benchmark.nograph_baseline import ridge as p01_ridge

from . import protocol

__all__ = [
    "DatasetError",
    "SkeletonDataset",
    "MaskBundle",
    "load_dataset",
    "from_fixture",
    "assert_published_demand",
    "assert_dense_published_offsets",
    "load_neighbor_coverage",
    "build_masks",
    "array_sha256",
]


class DatasetError(ValueError):
    """Raised when demand identity or published structure violates P01."""


@dataclass
class SkeletonDataset:
    """A validated demand table plus its publication status."""

    demand: p01_data.DemandData
    published: bool
    audit: Dict[str, Any]
    publication: Optional[Dict[str, Any]]

    @property
    def data_name(self) -> str:
        return self.demand.data_name

    @property
    def signal(self) -> np.ndarray:
        return self.demand.signal

    @property
    def key_array(self) -> np.ndarray:
        return self.demand.key_array

    @property
    def key_columns(self) -> Tuple[str, ...]:
        return self.demand.key_columns

    @property
    def node_count(self) -> int:
        return self.demand.node_count

    @property
    def context_values(self) -> np.ndarray:
        return self.key_array[:, 0]

    @property
    def skill_values(self) -> np.ndarray:
        return self.key_array[:, -1]

    def input_windows(self, starts: Sequence[int]) -> np.ndarray:
        """Return ``float32 [windows, nodes, L]`` true-history inputs."""
        return self.demand.input_windows(starts)

    def target_windows(self, starts: Sequence[int]) -> np.ndarray:
        """Return ``float32 [windows, nodes, H]`` observed targets."""
        return self.demand.target_windows(starts)

    def identity_payload(self) -> Dict[str, Any]:
        payload = self.demand.identity_payload()
        payload["source_kind"] = "published" if self.published else "fixture"
        payload["published_assertions"] = self.publication
        return payload


@dataclass
class MaskBundle:
    """The fixed P01 masks every method shares."""

    activity: np.ndarray  # float64 [N]
    activity_groups: Dict[str, np.ndarray]  # bool [N]
    constant_mask: np.ndarray  # bool [N]
    neighbor_mask: np.ndarray  # bool [N]
    payload: Dict[str, Any]

    def arrays(self) -> Dict[str, np.ndarray]:
        arrays: Dict[str, np.ndarray] = {
            "nonzero_activity_train27": np.asarray(self.activity, dtype=np.float64),
            "constant_train27": np.asarray(self.constant_mask, dtype=bool),
            "has_nonself_neighbor": np.asarray(self.neighbor_mask, dtype=bool),
        }
        for name, mask in self.activity_groups.items():
            arrays[f"activity_{name}"] = np.asarray(mask, dtype=bool)
        return arrays

    def hashes(self) -> Dict[str, str]:
        return {name: array_sha256(array) for name, array in self.arrays().items()}


def array_sha256(array: np.ndarray) -> str:
    """Hash an array's canonical bytes (no pickling, platform independent)."""
    values = np.ascontiguousarray(np.asarray(array))
    digest = hashlib.sha256()
    digest.update(str(values.dtype).encode("ascii"))
    digest.update(b"\0")
    digest.update(",".join(str(dim) for dim in values.shape).encode("ascii"))
    digest.update(b"\0")
    digest.update(values.tobytes(order="C"))
    return digest.hexdigest()


def load_dataset(
    data_name: str,
    *,
    demand_path: Optional[Path] = None,
    published: Optional[bool] = None,
) -> SkeletonDataset:
    """Load a demand table and assert published structure when applicable."""
    protocol.validate_dataset_name(data_name)
    path = Path(demand_path) if demand_path is not None else p01.demand_path(data_name)
    if published is None:
        published = path.resolve() == p01.demand_path(data_name).resolve()
    try:
        demand = p01_data.load_demand(
            data_name, mode="count", demand_path=path
        )
    except (p01_data.DemandError, p01.ProtocolError) as exc:
        raise DatasetError(str(exc)) from exc
    publication = None
    audit = dict(demand.audit)
    if published:
        publication = assert_published_demand(demand, data_name)
        audit["published_structure"] = publication
    return SkeletonDataset(
        demand=demand, published=bool(published), audit=audit, publication=publication
    )


def from_fixture(
    data_name: str,
    keys: Sequence[Sequence[int]],
    signal: np.ndarray,
    *,
    source_path: str = "<in-memory fixture>",
    source_sha256: str = "in-memory",
) -> SkeletonDataset:
    """Build a validated fixture dataset through P01's identity contract."""
    protocol.validate_dataset_name(data_name)
    try:
        demand = p01_data.from_arrays(
            data_name,
            keys,
            signal,
            mode="count",
            source_path=source_path,
            source_sha256=source_sha256,
        )
    except (p01_data.DemandError, p01.ProtocolError) as exc:
        raise DatasetError(str(exc)) from exc
    return SkeletonDataset(
        demand=demand, published=False, audit=dict(demand.audit), publication=None
    )


def assert_published_demand(
    demand: p01_data.DemandData, data_name: str
) -> Dict[str, Any]:
    """Re-assert the frozen published demand grid or fail before training."""
    spec = protocol.published_demand_spec(data_name)
    key_array = np.asarray(demand.key_array, dtype=np.int64)
    problems: List[str] = []
    nodes = int(key_array.shape[0])
    if nodes != spec["nodes"]:
        problems.append(f"node count {nodes} != {spec['nodes']}")
    if key_array.shape[1] != len(protocol.p01.node_key_columns(data_name)):
        problems.append(
            f"key columns {key_array.shape[1]} != "
            f"{len(protocol.p01.node_key_columns(data_name))}"
        )
    if demand.signal.shape != (nodes, spec["months"]) or demand.n_months != spec["months"]:
        problems.append(
            f"month grid {demand.signal.shape} != ({nodes}, {spec['months']})"
        )
    contexts = tuple(int(value) for value in np.unique(key_array[:, 0]))
    if contexts != tuple(spec["contexts"]):
        problems.append(
            f"context ids {contexts[:5]}...{contexts[-3:]} != {spec['contexts'][:5]}..."
            f"{spec['contexts'][-3:]}"
        )
    skills = tuple(int(value) for value in np.unique(key_array[:, 1]))
    first, last = spec["skills"]
    expected_skills = tuple(range(first, last + 1))
    if skills != expected_skills:
        problems.append(
            f"skill ids are not the complete range {first}..{last}"
        )
    expected_nodes = len(contexts) * len(expected_skills)
    if nodes != expected_nodes:
        problems.append(
            f"complete grid needs {expected_nodes} nodes, got {nodes}"
        )
    # Every context/skill pair must occur exactly once.
    unique_keys = np.unique(key_array, axis=0)
    if unique_keys.shape[0] != nodes:
        problems.append(
            f"{nodes - unique_keys.shape[0]} duplicate context/skill identities"
        )
    if not np.isfinite(demand.signal).all():
        problems.append("demand signal contains nonfinite values")
    if (demand.signal < 0).any():
        problems.append("demand signal contains negative counts")
    if problems:
        raise DatasetError(
            f"{data_name}: published demand structure violated: " + "; ".join(problems)
        )
    dense = assert_dense_published_offsets(key_array)
    return {
        "dataset": data_name,
        "nodes": nodes,
        "contexts": list(contexts),
        "skill_range": [first, last],
        "skill_count": len(expected_skills),
        "months": int(spec["months"]),
        "complete_grid": True,
        "unique_keys": int(nodes),
        "finite_nonnegative": True,
        "dense_offset": dense,
    }


def assert_dense_published_offsets(key_array: np.ndarray) -> Dict[str, Any]:
    """Prove ``context_ordinal*2335 + skill_id`` equals the canonical index.

    This formula is only accepted after this check on the complete published
    grid; arbitrary fixtures are resolved by their actual canonical keys.
    """
    keys = np.asarray(key_array, dtype=np.int64)
    contexts = [int(value) for value in np.unique(keys[:, 0])]
    ordinal = {context: index for index, context in enumerate(contexts)}
    expected = np.array(
        [
            ordinal[int(context)] * protocol.PUBLISHED_CONTEXT_STRIDE + int(skill)
            for context, skill in zip(keys[:, 0], keys[:, 1])
        ],
        dtype=np.int64,
    )
    canonical = np.arange(keys.shape[0], dtype=np.int64)
    if not np.array_equal(expected, canonical):
        mismatch = int(np.flatnonzero(expected != canonical)[0])
        raise DatasetError(
            "published dense offset formula fails at node "
            f"{mismatch}: expected {int(expected[mismatch])}, canonical "
            f"{int(canonical[mismatch])}"
        )
    return {
        "formula": "context_ordinal*2335 + skill_id",
        "stride": protocol.PUBLISHED_CONTEXT_STRIDE,
        "context_ordinals": {str(context): ordinal[context] for context in contexts},
        "proven_nodes": int(keys.shape[0]),
    }


def load_neighbor_coverage(
    dataset: SkeletonDataset, graph_path: Path
) -> p01_coverage.CoverageMask:
    """Use P01's unchanged context-qualified non-self endpoint coverage mask."""
    try:
        return p01_coverage.load_graph_coverage(
            dataset.data_name, dataset.key_array, graph_path=Path(graph_path)
        )
    except p01_coverage.CoverageError as exc:
        raise DatasetError(str(exc)) from exc


def build_masks(
    dataset: SkeletonDataset, coverage_mask: p01_coverage.CoverageMask
) -> MaskBundle:
    """Freeze the training-27 activity/constant masks and the graph coverage."""
    try:
        stats = p01_ridge.compute_training_stats(
            dataset.signal, definition=p01.MAIN_SPLIT
        )
    except p01_ridge.RidgeError as exc:  # pragma: no cover - shape guarded above
        raise DatasetError(str(exc)) from exc
    neighbor = np.asarray(coverage_mask.mask, dtype=bool)
    if neighbor.shape != (dataset.node_count,):
        raise DatasetError(
            f"neighbour mask shape {neighbor.shape} != {dataset.node_count} nodes"
        )
    payload = {
        "scope": "train27 (2021-01..2023-03)",
        "activity_definition": (
            "nonzero-month fraction over the 27 unique training observation "
            "months; groups inactive==0, low (0,1/3], medium (1/3,2/3], high "
            "(2/3,1]"
        ),
        "constant_definition": "float64 training-27 standard deviation == 0 (ddof=0)",
        "neighbor_definition": p01_coverage.COVERAGE_DEFINITION,
        "neighbor_definition_id": p01_coverage.COVERAGE_DEFINITION_ID,
        "neighbor_source": coverage_mask.provenance,
        "activity_group_counts": {
            name: int(mask.sum()) for name, mask in stats.activity_groups.items()
        },
        "constant_node_count": int(stats.constant_mask.sum()),
        "has_nonself_neighbor_count": int(neighbor.sum()),
        "shared_by_methods": list(protocol.METHODS),
        "recomputed_from_shuffled_adjacency": False,
        "train_observation_months": list(p01.TRAIN_OBSERVATION_MONTHS),
    }
    return MaskBundle(
        activity=np.asarray(stats.activity, dtype=np.float64),
        activity_groups={
            name: np.asarray(mask, dtype=bool)
            for name, mask in stats.activity_groups.items()
        },
        constant_mask=np.asarray(stats.constant_mask, dtype=bool),
        neighbor_mask=neighbor,
        payload=payload,
    )


def naive_reference_block(
    dataset: SkeletonDataset,
) -> Tuple[Dict[str, np.ndarray], Dict[str, float], Dict[str, Any], np.ndarray]:
    """Reuse the five P01 naive baselines and frozen reference selection."""
    frozen_mean = baselines.train_mean(
        dataset.signal, p01.MAIN_SPLIT.fitting_month_count
    )
    validation_predictions = baselines.naive_predictions(
        dataset.signal,
        protocol.VALIDATION_STARTS,
        frozen_train_mean=frozen_mean,
        train_mean_method=p01.MAIN_SPLIT.train_mean_method,
    )
    gold = dataset.target_windows(protocol.VALIDATION_STARTS)
    scores = baselines.validation_mse(validation_predictions, gold)
    references = baselines.select_references(scores)
    if dataset.published and references["NaiveRef"] != protocol.NAIVE_REF_PUBLISHED:
        raise DatasetError(
            "published data changed the frozen reference identity: NaiveRef is "
            f"{references['NaiveRef']!r}, expected {protocol.NAIVE_REF_PUBLISHED!r}"
        )
    return validation_predictions, scores, references, frozen_mean
