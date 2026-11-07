"""Structural summaries, connected components and candidate overlap.

Every statistic here is a description of the constructed population.  None of
it is used to select edges, weights or candidates, and none of it is evidence
of predictive benefit.  Empty and zero-variance statistics are represented as
JSON ``null`` with an explicit reason instead of a fabricated zero.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from . import protocol
from .data import TrainingData, array_sha256
from .scores import CandidateGraph

__all__ = [
    "pearson_association",
    "distribution_summary",
    "connected_components",
    "candidate_structure",
    "candidate_overlap",
    "graph_payload_hashes",
]


def pearson_association(x: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    """Pearson correlation with explicit null reasons."""
    left = np.asarray(x, dtype=np.float64)
    right = np.asarray(y, dtype=np.float64)
    if left.shape != right.shape:
        raise ValueError(f"association arrays differ in shape: {left.shape} {right.shape}")
    count = int(left.size)
    if count < 2:
        return {
            "status": "null",
            "n": count,
            "r": None,
            "reason": "fewer than two observations",
        }
    left_centered = left - left.mean()
    right_centered = right - right.mean()
    left_ss = float(np.dot(left_centered, left_centered))
    right_ss = float(np.dot(right_centered, right_centered))
    if left_ss == 0.0 or right_ss == 0.0:
        return {
            "status": "null",
            "n": count,
            "r": None,
            "reason": "zero variance in one or both series",
        }
    value = float(np.dot(left_centered, right_centered) / np.sqrt(left_ss * right_ss))
    value = max(-1.0, min(1.0, value))
    return {"status": "ok", "n": count, "r": value, "reason": None}


def distribution_summary(values: Sequence[float]) -> Dict[str, Any]:
    """Quantile/summary record for a possibly empty numeric sample."""
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return {
            "status": "null",
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std": None,
            "quantiles": None,
            "reason": "empty sample",
        }
    quantiles = np.quantile(array, [0.0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0])
    return {
        "status": "ok",
        "count": int(array.size),
        "min": float(array.min()),
        "max": float(array.max()),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "std": float(array.std(ddof=0)),
        "quantiles": {
            label: float(value)
            for label, value in zip(
                ("0", "25", "50", "75", "90", "99", "100"), quantiles
            )
        },
    }


def connected_components(
    n_nodes: int, edge_index: np.ndarray
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Label connected components with union-find; isolated skills count."""
    parent = np.arange(n_nodes, dtype=np.int64)
    rank = np.zeros(n_nodes, dtype=np.int8)

    def find(node: int) -> int:
        root = node
        while parent[root] != root:
            root = int(parent[root])
        while parent[node] != node:
            next_node = int(parent[node])
            parent[node] = root
            node = next_node
        return root

    edges = np.asarray(edge_index, dtype=np.int64).reshape(-1, 2)
    for left, right in edges:
        root_left = find(int(left))
        root_right = find(int(right))
        if root_left == root_right:
            continue
        if rank[root_left] < rank[root_right]:
            root_left, root_right = root_right, root_left
        parent[root_right] = root_left
        if rank[root_left] == rank[root_right]:
            rank[root_left] += 1
    roots = np.asarray([find(index) for index in range(n_nodes)], dtype=np.int64)
    unique_roots, labels = np.unique(roots, return_inverse=True)
    sizes = np.bincount(labels, minlength=unique_roots.size).astype(np.int64)
    summary = {
        "components": int(unique_roots.size),
        "isolated_nodes": int(np.count_nonzero(sizes == 1)),
        "largest_component": int(sizes.max()) if sizes.size else 0,
        "largest_component_fraction": (
            float(sizes.max() / n_nodes) if sizes.size and n_nodes else None
        ),
        "component_size_distribution": {
            "count": int(sizes.size),
            "min": int(sizes.min()) if sizes.size else None,
            "max": int(sizes.max()) if sizes.size else None,
            "mean": float(sizes.mean()) if sizes.size else None,
            "sizes_descending": [int(value) for value in np.sort(sizes)[::-1][:20]],
        },
        "algorithm": "union-find including isolate skills as size-1 components",
    }
    return labels.astype(np.int64), summary


def _coverage(
    mask: np.ndarray, degree: np.ndarray, label: str, denominator: str
) -> Dict[str, Any]:
    selected = np.asarray(mask, dtype=bool)
    count = int(np.count_nonzero(selected))
    isolated = int(np.count_nonzero(degree[selected] == 0))
    covered = count - isolated
    return {
        "label": label,
        "denominator": denominator,
        "nodes": count,
        "covered_nodes": covered,
        "isolated_nodes": isolated,
        "coverage_fraction": (float(covered / count) if count else None),
        "reason": None if count else "empty denominator",
    }


def candidate_structure(
    graph: CandidateGraph, training: TrainingData
) -> Tuple[Dict[str, Any], np.ndarray]:
    """Build the structural audit for one candidate; return component labels."""
    x = training.x
    support = training.support
    totals = x.sum(axis=1)
    support_counts = support.sum(axis=1, dtype=np.int64)
    active = totals > 0
    n_nodes = int(x.shape[0])
    degree = graph.degree
    pair_slots = n_nodes * (n_nodes - 1) // 2
    labels, component_summary = connected_components(n_nodes, graph.edge_index)

    active_degree = degree[active]
    all_degree = degree
    associations = {
        "degree_vs_total_demand_all_skills": pearson_association(degree, totals),
        "degree_vs_total_demand_training_active": pearson_association(
            active_degree, totals[active]
        ),
        "degree_vs_occupational_breadth_all_skills": pearson_association(
            degree, support_counts
        ),
        "degree_vs_occupational_breadth_training_active": pearson_association(
            active_degree, support_counts[active]
        ),
        "interpretation": (
            "descriptive associations only; not predictive benefit"
        ),
    }
    zero_demand = np.flatnonzero(~active)
    structure: Dict[str, Any] = {
        "candidate": graph.name,
        "source_protocol_version": protocol.SCIENTIFIC_PROTOCOL_VERSION,
        "source_data_name": training.source_data_name,
        "source_training_content_sha256": training.content_identity["sha256"],
        "source_file_sha256": training.file_identity["sha256"],
        "top_k": int(graph.top_k),
        "cutoff_rule": "descending score, ascending numeric skill id for exact ties",
        "nodes": n_nodes,
        "training_months": int(training.n_months),
        "zero_demand_skills": {
            "count": int(zero_demand.size),
            "fraction": float(zero_demand.size / n_nodes) if n_nodes else None,
            "skill_ids": [int(training.skills[index]) for index in zero_demand],
            "denominator": "all source skills in the node table",
        },
        "occupational_support_counts": {
            "denominator": "occupation count in the source grid",
            "distribution": distribution_summary(support_counts.astype(np.float64)),
            "zero_support_skills": int(np.count_nonzero(support_counts == 0)),
        },
        "pre_sparsification": graph.pre_sparsification,
        "cutoff_ties": dict(graph.tie_summary),
        "post_sparsification": {
            "edges": int(graph.n_edges),
            "edge_density": (
                float(graph.n_edges / pair_slots) if pair_slots else None
            ),
            "pair_slots": int(pair_slots),
            "degree_distribution": distribution_summary(degree.astype(np.float64)),
            "weight_distribution": distribution_summary(graph.edge_score),
            "max_degree": int(degree.max()) if n_nodes else None,
            "min_degree": int(degree.min()) if n_nodes else None,
            "union_degree_not_bounded_by_top_k": True,
            "union_degree_bound_reason": (
                "the undirected union keeps a pair selected by either endpoint"
            ),
        },
        "coverage": {
            "all_source_skills": _coverage(
                np.ones(n_nodes, dtype=bool),
                degree,
                "all source skills",
                "every skill in the source node table",
            ),
            "training_active_skills": _coverage(
                active,
                degree,
                "skills with positive training demand",
                "skills with x > 0 in at least one occupation",
            ),
            "interpretation": "structural coverage only; not predictive benefit",
        },
        "components": component_summary,
        "associations": associations,
        "empty_graph": bool(graph.n_edges == 0),
        "null_reasons": {},
    }
    if graph.n_edges == 0:
        structure["null_reasons"]["weight_distribution"] = (
            "candidate has no retained edge"
        )
        structure["null_reasons"]["edge_density"] = (
            "no unordered pair slots" if pair_slots == 0 else None
        )
        if pair_slots:
            structure["null_reasons"]["edge_density"] = None
    for name, record in associations.items():
        if isinstance(record, dict) and record.get("status") == "null":
            structure["null_reasons"][name] = record["reason"]
    # Candidate edge payload identity is recorded so diagnostics can prove that
    # they did not alter graph bytes.
    structure["graph_payload_sha256"] = graph_payload_hashes(graph)
    return structure, labels


def candidate_overlap(
    left: CandidateGraph, right: CandidateGraph
) -> Dict[str, Any]:
    """Compare two candidate edge sets by canonical unordered pairs."""
    left_pairs = {tuple(int(v) for v in pair) for pair in left.edge_index}
    right_pairs = {tuple(int(v) for v in pair) for pair in right.edge_index}
    intersection = left_pairs & right_pairs
    union = left_pairs | right_pairs
    return {
        "candidate_a": left.name,
        "candidate_b": right.name,
        "a_edges": len(left_pairs),
        "b_edges": len(right_pairs),
        "shared_edges": len(intersection),
        "a_only_edges": len(left_pairs - right_pairs),
        "b_only_edges": len(right_pairs - left_pairs),
        "union_edges": len(union),
        "jaccard": (float(len(intersection) / len(union)) if union else None),
        "jaccard_reason": (
            None if union else "both candidate edge sets are empty"
        ),
        "comparison": "canonical undirected skill pairs; scores differ by candidate",
        "interpretation": "structural overlap only; not predictive benefit",
    }


def graph_payload_hashes(graph: CandidateGraph) -> Dict[str, str]:
    """Hash every graph payload that trend diagnostics must leave unchanged."""
    return graph.identity_hashes()
