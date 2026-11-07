"""Key-only target population checks and lazy per-context edge expansion.

The shared undirected relation is lifted into every target context with an
unchanged score and both directions.  Target demand values are never read and
no duplicated per-context edge arrays are written; an implicit mapping
descriptor plus per-context counts is enough for later inspection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Sequence, Tuple

import numpy as np

from . import protocol
from .data import TargetKeyData, array_sha256, canonical_key_sha256

__all__ = [
    "MappingError",
    "MappedContext",
    "validate_target_population",
    "mapping_descriptor",
    "iter_context_edges",
    "target_mapping_report",
]


class MappingError(ValueError):
    """Raised when a target identity cannot carry the shared source relation."""


@dataclass
class MappedContext:
    """One lazily expanded target context; arrays are shared, not copied."""

    data_name: str
    context_id: int
    edges: np.ndarray  # int64 [E, 2] positional indices into source_skills
    scores: np.ndarray  # float64 [E]
    source_skills: np.ndarray  # int64 [S] canonical target skill ids

    @property
    def undirected_edges(self) -> int:
        return int(self.edges.shape[0])

    @property
    def directed_edges(self) -> int:
        return int(self.edges.shape[0] * 2)

    def node_key(self, skill_id: int) -> Tuple[int, int]:
        """Return the canonical target node identity for a shared skill."""
        return (int(self.context_id), int(skill_id))

    def directed_pairs(self) -> np.ndarray:
        """Expand the shared relation to both directions for this context."""
        if self.edges.size == 0:
            return np.empty((0, 4), dtype=np.int64)
        skill_pairs = self.source_skills[self.edges]
        forward = np.stack(
            [
                np.full(self.edges.shape[0], self.context_id, dtype=np.int64),
                skill_pairs[:, 0],
                np.full(self.edges.shape[0], self.context_id, dtype=np.int64),
                skill_pairs[:, 1],
            ],
            axis=1,
        )
        backward = np.stack(
            [
                np.full(self.edges.shape[0], self.context_id, dtype=np.int64),
                skill_pairs[:, 1],
                np.full(self.edges.shape[0], self.context_id, dtype=np.int64),
                skill_pairs[:, 0],
            ],
            axis=1,
        )
        return np.concatenate([forward, backward], axis=0)


def _skill_set(values: np.ndarray) -> Tuple[int, ...]:
    return tuple(int(value) for value in np.sort(np.unique(values)))


def validate_target_population(
    target: TargetKeyData, source_skill_ids: Sequence[int]
) -> Dict[str, Any]:
    """Require every target context to contain exactly the source skill set."""
    source_skills = _skill_set(np.asarray(source_skill_ids, dtype=np.int64))
    target_skills = _skill_set(target.skills)
    if target_skills != source_skills:
        missing = sorted(set(source_skills) - set(target_skills))
        extra = sorted(set(target_skills) - set(source_skills))
        raise MappingError(
            f"target {target.data_name}: skill population mismatch; "
            f"missing={missing[:5]} extra={extra[:5]}"
        )
    per_context: Dict[str, Dict[str, Any]] = {}
    for context in target.contexts:
        mask = target.key_array[:, 0] == context
        context_skills = _skill_set(target.key_array[mask, 1])
        if context_skills != source_skills:
            missing = sorted(set(source_skills) - set(context_skills))
            extra = sorted(set(context_skills) - set(source_skills))
            raise MappingError(
                f"target {target.data_name}: context {int(context)} does not "
                f"contain exactly the source skill set; missing={missing[:5]} "
                f"extra={extra[:5]}"
            )
        per_context[str(int(context))] = {
            "skills": int(len(context_skills)),
            "keys": int(np.count_nonzero(mask)),
        }
    return {
        "status": "ok",
        "data_name": target.data_name,
        "contexts": int(target.n_contexts),
        "skills": int(target.n_skills),
        "source_skills_sha256": array_sha256(
            np.asarray(source_skills, dtype=np.int64)
        ),
        "target_skills_sha256": array_sha256(
            np.asarray(target_skills, dtype=np.int64)
        ),
        "per_context": per_context,
        "checked": "exact source skill set in every target context",
    }


def mapping_descriptor(
    target: TargetKeyData, edge_index: np.ndarray, edge_score: np.ndarray
) -> Dict[str, Any]:
    """Describe the shared-edge -> target-context mapping without duplication."""
    edges = np.asarray(edge_index, dtype=np.int64).reshape(-1, 2)
    scores = np.asarray(edge_score, dtype=np.float64)
    if edges.shape[0] != scores.shape[0]:
        raise MappingError(
            "edge index and edge score arrays have different lengths: "
            f"{edges.shape[0]} and {scores.shape[0]}"
        )
    undirected = int(edges.shape[0])
    directed = int(undirected * 2)
    return {
        "data_name": target.data_name,
        "mapping": (
            "each shared undirected edge {a,b} is reused inside every target "
            "context c as both (c,a)->(c,b) and (c,b)->(c,a) with unchanged score"
        ),
        "contexts": int(target.n_contexts),
        "skills": int(target.n_skills),
        "undirected_edges_per_context": undirected,
        "directed_expansions_per_context": directed,
        "total_undirected_context_edges": int(undirected * target.n_contexts),
        "total_directed_expansions": int(directed * target.n_contexts),
        "cross_context_edges": 0,
        "target_demand_filtering": False,
        "target_value_columns_read": False,
        "target_keys_sha256": canonical_key_sha256(target.key_array),
        "shared_edge_pairs_sha256": array_sha256(edges),
        "shared_edge_scores_sha256": array_sha256(scores),
        "context_ids": [int(value) for value in target.contexts],
        "per_context_undirected_edges": [undirected] * int(target.n_contexts),
        "per_context_directed_expansions": [directed] * int(target.n_contexts),
        "duplicated_edge_arrays_saved": False,
    }


def iter_context_edges(
    target: TargetKeyData,
    edge_index: np.ndarray,
    edge_score: np.ndarray,
) -> Iterator[MappedContext]:
    """Yield one lazy context expansion at a time, referencing shared arrays."""
    edges = np.ascontiguousarray(np.asarray(edge_index, dtype=np.int64).reshape(-1, 2))
    scores = np.ascontiguousarray(np.asarray(edge_score, dtype=np.float64))
    if edges.shape[0] != scores.shape[0]:
        raise MappingError("edge index and score lengths differ")
    skills = np.ascontiguousarray(np.asarray(target.skills, dtype=np.int64))
    for context in target.contexts:
        yield MappedContext(
            data_name=target.data_name,
            context_id=int(context),
            edges=edges,
            scores=scores,
            source_skills=skills,
        )


def target_mapping_report(
    target: TargetKeyData,
    population: Dict[str, Any],
    descriptor: Dict[str, Any],
) -> Dict[str, Any]:
    """Assemble the saved mapping report for one target identity."""
    return {
        "data_name": target.data_name,
        "identity": target.identity,
        "population": population,
        "descriptor": descriptor,
        "key_columns": list(target.key_columns),
        "source_path": target.source_path,
        "source_file_sha256": target.source_sha256,
        "target_keys_sha256": canonical_key_sha256(target.key_array),
        "contexts": int(target.n_contexts),
        "skills": int(target.n_skills),
        "lazy_expansion": (
            "mapping.iter_context_edges yields one context at a time and shares "
            "the source edge and score arrays"
        ),
    }
