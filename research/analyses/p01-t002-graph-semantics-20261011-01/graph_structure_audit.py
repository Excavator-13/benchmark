#!/usr/bin/env python3
"""T002 graph-structure audit: per-context degree, directionality, reverse edges.

Reads only the shipped, read-only ``dataset/demand/*.parquet`` and
``dataset/graph/*.parquet`` files.  It does not build graph JSON, train a model,
or write anywhere except the analysis directory it is invoked from.

Question (protocol P1-count-L6-H3-v3 section 4.2): under the context-qualified
node definition (context id + skill_id), what are the per-context edge counts,
in/out/undirected neighbour degree distributions, self-loops, reverse-edge
ratio, and neighbour coverage?  A clearly labelled cross-context skill
projection is reported only to explain the legacy pre-analysis; it is not the
forecasting graph.

Usage:
    python graph_structure_audit.py            # prints JSON lines + summary
"""

from __future__ import annotations

import hashlib
import json
import platform
import tarfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTEXTS = {"r0": ["r0_id"], "region": ["region_id"]}
MONTHS = [f"{year}-{month:02d}" for year in (2021, 2022, 2023) for month in range(1, 13)]
DEGREE_BUCKETS = [(0, 0), (1, 1), (2, 3), (4, 7), (8, 15), (16, 31), (32, 63), (64, 10**9)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def packaged_json(name: str, relative: str) -> dict | None:
    """Read one JSON member from the sealed T004 package without extracting it."""
    package = REPO_ROOT / "research" / "archives" / f"p01-{name}-sharedridge-002.tar.gz"
    if not package.exists():
        return None
    member = f"p01-{name}-sharedridge-002/{relative}"
    with tarfile.open(package) as archive:
        handle = archive.extractfile(member)
        return json.loads(handle.read().decode("utf-8")) if handle is not None else None


def degree_summary(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=np.int64)
    summary = {
        "nodes": int(values.size),
        "mean": float(values.mean()) if values.size else None,
        "median": float(np.median(values)) if values.size else None,
        "max": int(values.max()) if values.size else None,
        "quantiles": {
            "p50": float(np.quantile(values, 0.50)) if values.size else None,
            "p90": float(np.quantile(values, 0.90)) if values.size else None,
            "p99": float(np.quantile(values, 0.99)) if values.size else None,
            "max": int(values.max()) if values.size else None,
        },
    }
    summary["histogram"] = {
        f"{lo}" if lo == hi else f"{lo}-{hi if hi < 10**9 else 'inf'}": int(
            ((values >= lo) & (values <= hi)).sum()
        )
        for lo, hi in DEGREE_BUCKETS
    }
    return summary


def audit_dataset(name: str, context: list[str]) -> dict:
    demand = pd.read_parquet(REPO_ROOT / "dataset" / "demand" / f"{name}.parquet")
    graph = pd.read_parquet(REPO_ROOT / "dataset" / "graph" / f"{name}.parquet")
    keys = context + ["skill_id"]
    assert not demand.duplicated(keys).any(), f"{name}: duplicate node identity"
    assert not graph[context + ["row_id", "col_id"]].isna().any().any()
    demand = demand.sort_values(keys, kind="stable").reset_index(drop=True)

    skill_set = set(demand["skill_id"].unique().tolist())
    context_values = {column: sorted(demand[column].unique().tolist()) for column in context}

    # Context-qualified node keys, canonical order matches demand row order.
    node_keys = list(
        zip(*[demand[column].tolist() for column in context], demand["skill_id"].tolist())
    )
    node_index = {key: position for position, key in enumerate(node_keys)}

    edges = list(zip(*[graph[column].tolist() for column in context],
                      graph["row_id"].tolist(), graph["col_id"].tolist()))
    endpoint_ok = all(
        tuple(edge[: len(context)]) + (edge[-2],) in node_index
        and tuple(edge[: len(context)]) + (edge[-1],) in node_index
        for edge in edges
    )
    assert endpoint_ok, f"{name}: unmatched graph endpoint"
    assert all(skill in skill_set for skill in graph["row_id"]) and all(
        skill in skill_set for skill in graph["col_id"]
    ), f"{name}: graph skill outside demand skill set"

    directed = {(edge[: len(context)], edge[-2], edge[-1]) for edge in edges}
    nonself = [edge for edge in directed if edge[-2] != edge[-1]]
    self_loops = len(directed) - len(nonself)
    reverse_present = sum(
        1 for edge in nonself if (edge[0], edge[-1], edge[-2]) in directed
    )

    out_degree = np.zeros(len(node_keys), dtype=np.int64)
    in_degree = np.zeros(len(node_keys), dtype=np.int64)
    undirected_degree = np.zeros(len(node_keys), dtype=np.int64)

    undirected_pairs = set()
    for edge in nonself:
        ctx, source, target = edge
        out_degree[node_index[ctx + (source,)]] += 1
        in_degree[node_index[ctx + (target,)]] += 1
        undirected_pairs.add((ctx, min(source, target), max(source, target)))

    undirected_neighbours = {position: set() for position in range(len(node_keys))}
    for ctx, low, high in undirected_pairs:
        low_pos = node_index[ctx + (low,)]
        high_pos = node_index[ctx + (high,)]
        undirected_neighbours[low_pos].add(high_pos)
        undirected_neighbours[high_pos].add(low_pos)
    for position, neighbours in undirected_neighbours.items():
        undirected_degree[position] = len(neighbours)

    covered = undirected_degree > 0

    # Per-scene (per-context) breakdown.
    context_breakdown = {}
    for ctx_tuple in sorted({edge[0] for edge in directed}):
        scene = [edge for edge in directed if edge[0] == ctx_tuple]
        scene_nonself = [edge for edge in scene if edge[-2] != edge[-1]]
        scene_pairs = {(ctx_tuple, min(edge[-2], edge[-1]), max(edge[-2], edge[-1]))
                       for edge in scene_nonself}
        scene_reverse = sum(
            1 for edge in scene_nonself if (edge[0], edge[-1], edge[-2]) in directed
        )
        scene_nodes = [
            position
            for position, key in enumerate(node_keys)
            if key[: len(context)] == ctx_tuple
        ]
        context_breakdown[str(ctx_tuple)] = {
            "task_nodes": len(scene_nodes),
            "directed_edge_rows_unique": len(scene),
            "self_loop_rows": len(scene) - len(scene_nonself),
            "nonself_directed_edges": len(scene_nonself),
            "undirected_unique_edges": len(scene_pairs),
            "edges_with_reverse_present": scene_reverse,
            "reverse_edge_ratio": scene_reverse / len(scene_nonself) if scene_nonself else None,
            "covered_nodes": int(covered[scene_nodes].sum()),
            "isolated_nodes": int((~covered[scene_nodes]).sum()),
        }

    # Cross-context skill projection, only to explain the legacy pre-analysis.
    projected_pairs = set()
    projected_row_counts: dict[tuple[int, int], int] = {}
    for edge in directed:
        low, high = min(edge[-2], edge[-1]), max(edge[-2], edge[-1])
        projected_pairs.add((low, high))
        projected_row_counts[(low, high)] = projected_row_counts.get((low, high), 0) + 1
    projected_counts = np.array(list(projected_row_counts.values()), dtype=np.int64)
    projected_nodes = sorted({skill for pair in projected_pairs for skill in pair})

    existing_coverage = packaged_json(name, "coverage.json")

    result = {
        "dataset": name,
        "context_columns": context,
        "task_nodes": len(node_keys),
        "context_count": int(np.prod([len(v) for v in context_values.values()])),
        "skill_count": len(skill_set),
        "graph_columns": list(graph.columns),
        "graph_directed_rows": len(graph),
        "graph_unique_directed_rows": len(directed),
        "exact_duplicate_rows": len(graph) - len(directed),
        "self_loop_unique_edges": self_loops,
        "nonself_directed_edges": len(nonself),
        "nonself_undirected_edges": len(undirected_pairs),
        "edges_with_reverse_present": reverse_present,
        "reverse_edge_ratio": reverse_present / len(nonself) if nonself else None,
        "covered_nodes": int(covered.sum()),
        "isolated_nodes": int((~covered).sum()),
        "neighbor_coverage": float(covered.mean()),
        "out_degree_all_nodes": degree_summary(out_degree),
        "in_degree_all_nodes": degree_summary(in_degree),
        "undirected_degree_all_nodes": degree_summary(undirected_degree),
        "undirected_degree_covered_nodes_only": degree_summary(undirected_degree[covered]),
        "sink_nodes_with_in_degree_zero_but_covered": int(
            ((in_degree == 0) & covered).sum()
        ),
        "source_nodes_with_out_degree_zero_but_covered": int(
            ((out_degree == 0) & covered).sum()
        ),
        "per_context": context_breakdown,
        "cross_context_skill_projection_legacy_explanation_only": {
            "is_forecasting_graph": False,
            "distinct_skills_in_projection": len(projected_nodes),
            "distinct_undirected_skill_pairs": len(projected_pairs),
            "directed_rows_per_pair": {
                "mean": float(projected_counts.mean()) if projected_counts.size else None,
                "median": float(np.median(projected_counts)) if projected_counts.size else None,
                "max": int(projected_counts.max()) if projected_counts.size else None,
                "min": int(projected_counts.min()) if projected_counts.size else None,
                "all_even_counts": bool(((projected_counts % 2) == 0).all()),
                "share_equal_to_two": float((projected_counts == 2).mean())
                if projected_counts.size else None,
            },
            "note": (
                "contexts are dropped and directions are summed here; the count per "
                "unordered skill pair is the number of directed (row_id, col_id) rows "
                "across all contexts. For a single-context dataset this is exactly 2 "
                "because both directions are shipped, so it is a symmetric duplicate "
                "count, not an advertising co-occurrence frequency."
            ),
        },
        "consistency_with_existing_coverage_json": {
            "saved_covered_nodes": existing_coverage.get("covered_nodes") if existing_coverage else None,
            "matches": bool(existing_coverage and existing_coverage["covered_nodes"] == int(covered.sum())),
        },
    }
    return result


def main() -> None:
    started = time.perf_counter()
    sources = {}
    for name in CONTEXTS:
        for kind in ("demand", "graph"):
            path = REPO_ROOT / "dataset" / kind / f"{name}.parquet"
            sources[str(path.relative_to(REPO_ROOT))] = sha256(path)

    output = {
        "analysis_id": "p01-t002-graph-semantics-20261011-01",
        "question": "context-qualified graph degree, directionality and coverage",
        "protocol": "P1-count-L6-H3-v3",
        "records_policy": "P01-records-v2",
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "sources_sha256": sources,
        "results": {},
    }
    for name, context in CONTEXTS.items():
        output["results"][name] = audit_dataset(name, context)

    destination = Path(__file__).resolve().parent / "graph-structure.json"
    destination.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"wrote": str(destination), "elapsed_seconds": time.perf_counter() - started}))
    for name, result in output["results"].items():
        print(json.dumps({
            "dataset": name,
            "task_nodes": result["task_nodes"],
            "nonself_undirected_edges": result["nonself_undirected_edges"],
            "reverse_edge_ratio": result["reverse_edge_ratio"],
            "covered_nodes": result["covered_nodes"],
            "isolated_nodes": result["isolated_nodes"],
            "coverage": result["neighbor_coverage"],
            "matches_saved_coverage": result["consistency_with_existing_coverage_json"]["matches"],
            "undirected_degree_covered": result["undirected_degree_covered_nodes_only"]["quantiles"],
            "legacy_projected_pairs": result[
                "cross_context_skill_projection_legacy_explanation_only"
            ]["distinct_undirected_skill_pairs"],
        }, sort_keys=True))


if __name__ == "__main__":
    main()
