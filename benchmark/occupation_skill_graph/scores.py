"""Blockwise support-Jaccard and demand-composition cosine candidates.

Only the upper triangle of each candidate score matrix is retained in a compact
ragged form.  Scores are streamed a row block at a time, the deterministic
top-``k`` selections are extracted immediately, and the final undirected union
keeps the original canonical ``float64`` score for every retained pair.  No
full ``N x N`` matrix, random tie-breaking or candidate expansion is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from . import protocol

__all__ = [
    "ScoreError",
    "CandidateGraph",
    "compute_candidate",
    "jaccard_pair",
    "cosine_pair",
    "select_top_k",
    "diagnostics_unchanged",
]


class ScoreError(ValueError):
    """Raised when a similarity score violates its mathematical contract."""


@dataclass
class CandidateGraph:
    """One deterministic sparse candidate graph and its immediate diagnostics."""

    name: str
    top_k: int
    selection_index: np.ndarray  # int64 [S, k], -1 padding
    selection_score: np.ndarray  # float64 [S, k], 0 padding
    cutoff_score: np.ndarray  # float64 [S]
    cutoff_tied_candidates: np.ndarray  # int64 [S]
    boundary_tie: np.ndarray  # bool [S]
    edge_index: np.ndarray  # int64 [E, 2] canonical a < b
    edge_score: np.ndarray  # float64 [E]
    edge_direction: np.ndarray  # int8 [E] 1=a->b, 2=b->a, 3=both
    degree: np.ndarray  # int64 [S]
    pre_sparsification: Dict[str, Any]
    tie_summary: Dict[str, Any]

    @property
    def n_nodes(self) -> int:
        return int(self.selection_index.shape[0])

    @property
    def n_edges(self) -> int:
        return int(self.edge_index.shape[0])

    def arrays(self) -> Dict[str, np.ndarray]:
        """Return the complete numeric payload for one candidate."""
        return {
            "selection_index": self.selection_index,
            "selection_score": self.selection_score,
            "cutoff_score": self.cutoff_score,
            "cutoff_tied_candidates": self.cutoff_tied_candidates,
            "boundary_tie": self.boundary_tie,
            "edge_index": self.edge_index,
            "edge_score": self.edge_score,
            "edge_direction": self.edge_direction,
            "degree": self.degree,
        }

    def identity_hashes(self) -> Dict[str, str]:
        from .data import array_sha256

        return {name: array_sha256(value) for name, value in self.arrays().items()}


def jaccard_pair(x: np.ndarray, support: np.ndarray, i: int, j: int) -> float:
    """Direct Jaccard score for one pair; empty union is zero."""
    intersection = int(np.count_nonzero(support[i] & support[j]))
    union = int(np.count_nonzero(support[i] | support[j]))
    return 0.0 if union == 0 else float(intersection / union)


def cosine_pair(profiles: np.ndarray, i: int, j: int) -> float:
    """Direct cosine score for one pair; zero vectors score zero."""
    left = np.asarray(profiles[i], dtype=np.float64)
    right = np.asarray(profiles[j], dtype=np.float64)
    left_norm = float(np.sqrt(np.dot(left, left)))
    right_norm = float(np.sqrt(np.dot(right, right)))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    value = float(np.dot(left, right) / (left_norm * right_norm))
    return max(0.0, min(1.0, value))


def _filled_row(upper: List[np.ndarray], index: int) -> np.ndarray:
    """Assemble one symmetric score row from the compact upper triangle."""
    size = len(upper)
    row = np.empty(size, dtype=np.float64)
    if index:
        row[:index] = [upper[left][index - left - 1] for left in range(index)]
    row[index] = 0.0
    row[index + 1 :] = upper[index]
    return row


def _selection_for_row(
    row: np.ndarray, top_k: int
) -> Tuple[np.ndarray, np.ndarray, float, int, bool, int]:
    """Return deterministic top-k indices/scores and cutoff-tie diagnostics."""
    size = row.shape[0]
    positive = row > 0.0
    count = int(np.count_nonzero(positive))
    indices_out = np.full(top_k, -1, dtype=np.int64)
    scores_out = np.zeros(top_k, dtype=np.float64)
    if count == 0:
        return indices_out, scores_out, 0.0, 0, False, 0
    candidate_index = np.flatnonzero(positive)
    candidate_scores = row[candidate_index]
    order = np.lexsort((candidate_index, -candidate_scores))
    ordered_index = candidate_index[order]
    ordered_scores = candidate_scores[order]
    retained = min(top_k, count)
    indices_out[:retained] = ordered_index[:retained]
    scores_out[:retained] = ordered_scores[:retained]
    cutoff = float(ordered_scores[retained - 1])
    tied = int(np.count_nonzero(candidate_scores == cutoff))
    boundary = bool(count > top_k and ordered_scores[top_k] == cutoff)
    return indices_out, scores_out, cutoff, tied, boundary, count


def _validate_scores(block: np.ndarray, name: str, tolerance: float = 1e-12) -> np.ndarray:
    if not np.isfinite(block).all():
        raise ScoreError(f"{name}: nonfinite candidate scores")
    if block.size:
        minimum = float(block.min())
        maximum = float(block.max())
        if minimum < -tolerance or maximum > 1.0 + tolerance:
            raise ScoreError(
                f"{name}: candidate scores outside [0, 1] beyond rounding "
                f"tolerance: min={minimum} max={maximum}"
            )
    return np.clip(block, 0.0, 1.0)


def _score_upper(
    *,
    name: str,
    x: np.ndarray,
    support: np.ndarray,
    block_size: int,
    progress: Optional[Callable[[str, int, int], None]] = None,
) -> Tuple[List[np.ndarray], Dict[str, Any]]:
    """Compute the compact upper triangle for one candidate."""
    n_skills = int(x.shape[0])
    upper: List[np.ndarray] = [
        np.empty(max(n_skills - index - 1, 0), dtype=np.float64)
        for index in range(n_skills)
    ]
    if name == "jaccard":
        support_counts = support.sum(axis=1, dtype=np.int64)
        for start in range(0, n_skills, block_size):
            end = min(start + block_size, n_skills)
            block_support = np.asarray(support[start:end], dtype=np.int64)
            rest_support = np.asarray(support[start:], dtype=np.int64)
            intersection = block_support @ rest_support.T
            union = (
                support_counts[start:end, None]
                + support_counts[None, start:]
                - intersection
            )
            block = np.zeros(intersection.shape, dtype=np.float64)
            nonempty = union > 0
            block[nonempty] = intersection[nonempty] / union[nonempty]
            block = _validate_scores(block, name)
            for offset in range(end - start):
                index = start + offset
                upper[index][:] = block[offset, offset + 1 :]
            if progress is not None:
                progress("construct", end, n_skills)
    elif name == "cosine":
        totals = x.sum(axis=1)
        denominator = np.where(totals > 0, totals, 1.0)
        profiles = x / denominator[:, None]
        profiles[totals == 0, :] = 0.0
        norms = np.sqrt(np.einsum("ij,ij->i", profiles, profiles))
        normalized = profiles / np.where(norms > 0, norms, 1.0)[:, None]
        normalized[norms == 0, :] = 0.0
        for start in range(0, n_skills, block_size):
            end = min(start + block_size, n_skills)
            block = normalized[start:end] @ normalized[start:].T
            block = _validate_scores(block, name)
            for offset in range(end - start):
                index = start + offset
                upper[index][:] = block[offset, offset + 1 :]
            if progress is not None:
                progress("construct", end, n_skills)
    else:  # pragma: no cover - protocol restricts names
        raise ScoreError(f"unsupported candidate {name!r}")

    pair_slots = n_skills * (n_skills - 1) // 2
    positive_parts: List[np.ndarray] = []
    positive_pairs = 0
    positive_sum = 0.0
    maximum = 0.0
    for values in upper:
        positive = values[values > 0.0]
        if positive.size:
            positive_parts.append(positive)
            positive_pairs += int(positive.size)
            positive_sum += float(positive.sum())
            maximum = max(maximum, float(positive.max()))
    positive_values = (
        np.concatenate(positive_parts) if positive_parts else np.empty(0, dtype=np.float64)
    )
    if positive_values.size:
        quantiles = np.quantile(positive_values, [0.0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0])
        histogram, edges = np.histogram(positive_values, bins=np.linspace(0.0, 1.0, 11))
        summary: Dict[str, Any] = {
            "status": "ok",
            "positive_pairs": int(positive_pairs),
            "zero_score_pairs": int(pair_slots - positive_pairs),
            "pair_slots": int(pair_slots),
            "density": float(positive_pairs / pair_slots) if pair_slots else None,
            "density_denominator": "unordered distinct skill pairs N*(N-1)/2",
            "score_min": float(positive_values.min()),
            "score_max": float(positive_values.max()),
            "score_mean": float(positive_values.mean()),
            "score_median": float(np.median(positive_values)),
            "score_std": float(positive_values.std(ddof=0)),
            "score_quantiles": {
                label: float(value)
                for label, value in zip(
                    ("0", "25", "50", "75", "90", "99", "100"), quantiles
                )
            },
            "score_histogram": {
                "bins": [float(value) for value in edges],
                "counts": [int(value) for value in histogram],
            },
            "full_score_pairs": int(np.count_nonzero(positive_values == 1.0)),
            "full_score_fraction_of_positive": float(
                np.mean(positive_values == 1.0)
            ),
            "max_score_pair_count": int(np.count_nonzero(positive_values == maximum)),
            "max_score_fraction_of_positive": float(
                np.mean(positive_values == maximum)
            ),
            "null_reasons": {},
        }
    else:
        summary = {
            "status": "null",
            "positive_pairs": 0,
            "zero_score_pairs": int(pair_slots),
            "pair_slots": int(pair_slots),
            "density": 0.0 if pair_slots else None,
            "density_denominator": "unordered distinct skill pairs N*(N-1)/2",
            "score_min": None,
            "score_max": None,
            "score_mean": None,
            "score_median": None,
            "score_std": None,
            "score_quantiles": None,
            "score_histogram": None,
            "full_score_pairs": 0,
            "full_score_fraction_of_positive": None,
            "max_score_pair_count": 0,
            "max_score_fraction_of_positive": None,
            "null_reasons": {
                "score_summary": "no positive pre-sparsification pair score"
            },
        }
    return upper, summary


def compute_candidate(
    name: str,
    x: np.ndarray,
    support: np.ndarray,
    *,
    top_k: int = protocol.TOP_K,
    block_size: int = protocol.SCORE_BLOCK_SIZE,
    progress: Optional[Callable[[str, int, int], None]] = None,
) -> CandidateGraph:
    """Build one deterministic top-k candidate and its undirected union."""
    if name not in protocol.CANDIDATES:
        raise ScoreError(f"unsupported candidate {name!r}")
    values = np.ascontiguousarray(np.asarray(x, dtype=np.float64))
    supports = np.ascontiguousarray(np.asarray(support, dtype=bool))
    if values.ndim != 2 or supports.shape != values.shape:
        raise ScoreError(
            f"candidate {name}: x and support must share shape [S, C], got "
            f"{values.shape} and {supports.shape}"
        )
    if not np.isfinite(values).all():
        raise ScoreError(f"candidate {name}: x contains nonfinite values")
    if (values < 0).any():
        raise ScoreError(f"candidate {name}: x contains negatives")
    if not np.array_equal(supports, values > 0):
        raise ScoreError(f"candidate {name}: support is not exactly x > 0")
    n_skills = int(values.shape[0])
    upper, pre_summary = _score_upper(
        name=name,
        x=values,
        support=supports,
        block_size=block_size,
        progress=progress,
    )

    selection_index = np.full((n_skills, top_k), -1, dtype=np.int64)
    selection_score = np.zeros((n_skills, top_k), dtype=np.float64)
    cutoff_score = np.zeros(n_skills, dtype=np.float64)
    cutoff_tied = np.zeros(n_skills, dtype=np.int64)
    boundary_tie = np.zeros(n_skills, dtype=bool)
    pair_map: Dict[Tuple[int, int], int] = {}
    for index in range(n_skills):
        row = _filled_row(upper, index)
        (
            selected_index,
            selected_score,
            cutoff,
            tied,
            boundary,
            _count,
        ) = _selection_for_row(row, top_k)
        selection_index[index] = selected_index
        selection_score[index] = selected_score
        cutoff_score[index] = cutoff
        cutoff_tied[index] = tied
        boundary_tie[index] = boundary
        if selected_index[0] < 0:
            continue
        for rank in range(top_k):
            neighbor = int(selected_index[rank])
            if neighbor < 0:
                break
            if neighbor == index:
                raise ScoreError(f"candidate {name}: self selection at {index}")
            left, right = (index, neighbor) if index < neighbor else (neighbor, index)
            score = float(upper[left][right - left - 1])
            if not np.isfinite(score) or score <= 0.0:
                raise ScoreError(
                    f"candidate {name}: selection has nonpositive/nonfinite score"
                )
            if abs(score - float(selected_score[rank])) > 0.0:
                raise ScoreError(
                    f"candidate {name}: selection score disagrees with canonical "
                    f"compact score for pair ({index}, {neighbor})"
                )
            direction = 1 if index == left else 2
            pair_map[(left, right)] = pair_map.get((left, right), 0) | direction

    pairs = sorted(pair_map)
    if pairs:
        edge_index = np.asarray(pairs, dtype=np.int64)
        edge_direction = np.asarray(
            [pair_map[pair] for pair in pairs], dtype=np.int8
        )
        edge_score = np.asarray(
            [float(upper[a][b - a - 1]) for a, b in pairs], dtype=np.float64
        )
    else:
        edge_index = np.empty((0, 2), dtype=np.int64)
        edge_direction = np.empty(0, dtype=np.int8)
        edge_score = np.empty(0, dtype=np.float64)
    if edge_index.size:
        if (edge_index[:, 0] >= edge_index[:, 1]).any():
            raise ScoreError(f"candidate {name}: non-canonical edge orientation")
        if np.unique(edge_index, axis=0).shape[0] != edge_index.shape[0]:
            raise ScoreError(f"candidate {name}: duplicate undirected edge")
        if (edge_score <= 0).any() or not np.isfinite(edge_score).all():
            raise ScoreError(f"candidate {name}: zero or nonfinite edge score")
    degree = np.bincount(edge_index.reshape(-1), minlength=n_skills).astype(np.int64)

    tie_summary = {
        "top_k": int(top_k),
        "boundary_tie_nodes": int(np.count_nonzero(boundary_tie)),
        "boundary_tie_node_fraction": (
            float(np.mean(boundary_tie)) if n_skills else None
        ),
        "nodes_with_multiple_cutoff_candidates": int(
            np.count_nonzero(cutoff_tied > 1)
        ),
        "max_cutoff_tied_candidates": int(cutoff_tied.max()) if n_skills else 0,
        "affected_by_exact_tie_at_cutoff": int(np.count_nonzero(boundary_tie)),
        "tie_break_rule": "descending score, then ascending numeric skill id",
        "union_degree_bound": None,
        "union_degree_bound_reason": (
            "union of one-sided top-k selections can exceed k at a node"
        ),
        "max_degree": int(degree.max()) if n_skills else 0,
        "min_degree": int(degree.min()) if n_skills else 0,
    }
    return CandidateGraph(
        name=name,
        top_k=int(top_k),
        selection_index=selection_index,
        selection_score=selection_score,
        cutoff_score=cutoff_score,
        cutoff_tied_candidates=cutoff_tied,
        boundary_tie=boundary_tie,
        edge_index=edge_index,
        edge_score=edge_score,
        edge_direction=edge_direction,
        degree=degree,
        pre_sparsification=pre_summary,
        tie_summary=tie_summary,
    )


def select_top_k(row: np.ndarray, top_k: int = protocol.TOP_K) -> Tuple[np.ndarray, np.ndarray]:
    """Public deterministic top-k selection over one score row (fixture helper)."""
    indices, scores, _cutoff, _tied, _boundary, _count = _selection_for_row(
        np.asarray(row, dtype=np.float64), top_k
    )
    keep = indices >= 0
    return indices[keep], scores[keep]


def diagnostics_unchanged(
    before: Dict[str, Any], after: Dict[str, Any]
) -> bool:
    """Return whether every graph payload identity hash is unchanged."""
    return dict(before) == dict(after)
