#!/usr/bin/env python3
"""T006 r2/count data and graph audit (context-qualified, read-only).

Reads ``dataset/demand/r2.parquet`` and ``dataset/graph/r2.parquet`` plus the
completed formal run's ``coverage.json`` for cross-checking.  Reports node
identity/grid facts, per-context edge counts, reverse-edge ratio, in/out and
undirected neighbour degree distributions, and the clearly labelled
cross-context skill projection kept only to explain the legacy pre-analysis.

Usage: python r2_structure_audit.py
"""

from __future__ import annotations

import hashlib
import json
import platform
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_NAME = "r2"
CONTEXT = ["r2_id"]
MONTHS = [f"{year}-{month:02d}" for year in (2021, 2022, 2023) for month in range(1, 13)]
TRAIN_MONTHS = MONTHS[:27]
RUN_DIR = REPO_ROOT / "research" / "runs" / "p01-r2-sharedridge-001"
DEGREE_BUCKETS = [(0, 0), (1, 1), (2, 3), (4, 7), (8, 15), (16, 31), (32, 63), (64, 10**9)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def degree_summary(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=np.int64)
    return {
        "nodes": int(values.size),
        "min": int(values.min()) if values.size else None,
        "mean": float(values.mean()) if values.size else None,
        "median": float(np.median(values)) if values.size else None,
        "p25": float(np.quantile(values, 0.25)) if values.size else None,
        "p75": float(np.quantile(values, 0.75)) if values.size else None,
        "max": int(values.max()) if values.size else None,
        "histogram": {
            f"{lo}" if lo == hi else f"{lo}-{hi if hi < 10**9 else 'inf'}": int(
                ((values >= lo) & (values <= hi)).sum()
            )
            for lo, hi in DEGREE_BUCKETS
        },
    }


def main() -> None:
    started = time.perf_counter()
    demand = pd.read_parquet(REPO_ROOT / "dataset" / "demand" / f"{DATA_NAME}.parquet")
    graph = pd.read_parquet(REPO_ROOT / "dataset" / "graph" / f"{DATA_NAME}.parquet")
    keys = CONTEXT + ["skill_id"]
    assert not demand.duplicated(keys).any()
    demand = demand.sort_values(keys, kind="stable").reset_index(drop=True)
    signal = demand[MONTHS].to_numpy(dtype=np.float64)

    node_keys = list(zip(demand["r2_id"].tolist(), demand["skill_id"].tolist()))
    node_index = {key: position for position, key in enumerate(node_keys)}
    assert len(node_index) == len(node_keys) == len(demand)

    edges = list(zip(graph["r2_id"].tolist(), graph["row_id"].tolist(), graph["col_id"].tolist()))
    assert all((e[0], e[1]) in node_index and (e[0], e[2]) in node_index for e in edges)
    directed = {(e[0], e[1], e[2]) for e in edges}
    nonself = [e for e in directed if e[1] != e[2]]
    self_loops = len(directed) - len(nonself)
    reverse_present = sum(1 for e in nonself if (e[0], e[2], e[1]) in directed)

    out_degree = np.zeros(len(node_keys), dtype=np.int64)
    in_degree = np.zeros(len(node_keys), dtype=np.int64)
    neighbours = defaultdict(set)
    undirected_pairs = set()
    for ctx, source, target in nonself:
        out_degree[node_index[(ctx, source)]] += 1
        in_degree[node_index[(ctx, target)]] += 1
        low, high = min(source, target), max(source, target)
        undirected_pairs.add((ctx, low, high))
        neighbours[node_index[(ctx, low)]].add(node_index[(ctx, high)])
        neighbours[node_index[(ctx, high)]].add(node_index[(ctx, low)])
    undirected_degree = np.array([len(neighbours[pos]) for pos in range(len(node_keys))], dtype=np.int64)
    covered = undirected_degree > 0

    per_context = {}
    for ctx in sorted({e[0] for e in directed}):
        scene = [e for e in directed if e[0] == ctx]
        scene_nonself = [e for e in scene if e[1] != e[2]]
        positions = [pos for pos, key in enumerate(node_keys) if key[0] == ctx]
        per_context[str(ctx)] = {
            "task_nodes": len(positions),
            "nonself_directed_edges": len(scene_nonself),
            "undirected_unique_edges": len({(min(e[1], e[2]), max(e[1], e[2])) for e in scene_nonself}),
            "self_loop_rows": len(scene) - len(scene_nonself),
            "reverse_edge_ratio": (
                sum(1 for e in scene_nonself if (e[0], e[2], e[1]) in directed) / len(scene_nonself)
                if scene_nonself else None
            ),
            "covered_nodes": int(covered[positions].sum()),
            "isolated_nodes": int((~covered[positions]).sum()),
        }

    projected_rows_per_pair: dict[tuple[int, int], int] = {}
    projected_pairs = set()
    for _, source, target in directed:
        low, high = min(source, target), max(source, target)
        projected_pairs.add((low, high))
        projected_rows_per_pair[(low, high)] = projected_rows_per_pair.get((low, high), 0) + 1
    projected_counts = np.array(list(projected_rows_per_pair.values()), dtype=np.int64)

    activity = (signal[:, : len(TRAIN_MONTHS)] > 0).mean(axis=1)
    groups = {
        "inactive": activity == 0,
        "low": (activity > 0) & (activity <= 1 / 3),
        "medium": (activity > 1 / 3) & (activity <= 2 / 3),
        "high": activity > 2 / 3,
    }
    context_counts = {"r2_id": int(demand["r2_id"].nunique())}
    run_coverage = json.loads((RUN_DIR / "coverage.json").read_text(encoding="utf-8"))
    run_audit = json.loads((RUN_DIR / "audit.json").read_text(encoding="utf-8"))

    output = {
        "analysis_id": "p01-t006-r2-audit-20261012-01",
        "task": "P01-T006",
        "protocol": "P1-count-L6-H3-v3",
        "records_policy": "P01-records-v2",
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "sources_sha256": {
            "dataset/demand/r2.parquet": sha256(REPO_ROOT / "dataset" / "demand" / "r2.parquet"),
            "dataset/graph/r2.parquet": sha256(REPO_ROOT / "dataset" / "graph" / "r2.parquet"),
        },
        "identity": {
            "task_nodes": len(node_keys),
            "skill_count": int(demand["skill_id"].nunique()),
            "context_counts": context_counts,
            "joint_contexts": int(demand[CONTEXT].drop_duplicates().shape[0]),
            "grid_expected": int(demand["r2_id"].nunique() * demand["skill_id"].nunique()),
            "grid_complete": bool(len(demand) == demand["r2_id"].nunique() * demand["skill_id"].nunique()),
            "months": MONTHS,
            "value_range": {"min": float(signal.min()), "max": float(signal.max())},
            "train_all_zero_fraction": float((activity == 0).mean()),
            "full_36_month_all_zero_fraction_diagnostic_only": float((signal == 0).all(axis=1).mean()),
            "constant_node_count_train27": int((signal[:, : len(TRAIN_MONTHS)].std(axis=1) == 0).sum()),
            "activity_group_counts": {name: int(mask.sum()) for name, mask in groups.items()},
            "matches_run_audit": {
                "nodes": run_audit["nodes"] == len(node_keys),
                "skills": run_audit["skill_id_nunique"] == int(demand["skill_id"].nunique()),
                "grid_complete": bool(run_audit["is_complete_context_skill_grid"]),
            },
        },
        "graph": {
            "graph_columns": list(graph.columns),
            "directed_rows": len(graph),
            "unique_directed_edges": len(directed),
            "exact_duplicate_rows": len(graph) - len(directed),
            "self_loop_unique_edges": self_loops,
            "nonself_directed_edges": len(nonself),
            "nonself_undirected_edges": len(undirected_pairs),
            "edges_with_reverse_present": reverse_present,
            "reverse_edge_ratio": reverse_present / len(nonself) if nonself else None,
            "covered_nodes": int(covered.sum()),
            "isolated_nodes": int((~covered).sum()),
            "neighbor_coverage": float(covered.mean()),
            "in_degree_all_nodes": degree_summary(in_degree),
            "out_degree_all_nodes": degree_summary(out_degree),
            "undirected_degree_all_nodes": degree_summary(undirected_degree),
            "undirected_degree_covered_nodes_only": degree_summary(undirected_degree[covered]),
            "per_context": per_context,
            "matches_run_coverage": {
                "covered_nodes": run_coverage["covered_nodes"] == int(covered.sum()),
                "nodes": run_coverage["nodes"] == len(node_keys),
                "graph_source_sha256": run_coverage["source_sha256"]
                == sha256(REPO_ROOT / "dataset" / "graph" / "r2.parquet"),
            },
        },
        "cross_context_skill_projection_legacy_explanation_only": {
            "is_forecasting_graph": False,
            "distinct_skills_in_projection": len({s for pair in projected_pairs for s in pair}),
            "distinct_undirected_skill_pairs": len(projected_pairs),
            "directed_rows_per_pair": {
                "min": int(projected_counts.min()),
                "mean": float(projected_counts.mean()),
                "median": float(np.median(projected_counts)),
                "max": int(projected_counts.max()),
                "all_even_counts": bool(((projected_counts % 2) == 0).all()),
                "share_equal_to_two": float((projected_counts == 2).mean()),
            },
        },
        "elapsed_seconds": time.perf_counter() - started,
    }

    destination = Path(__file__).resolve().parent / "r2-structure.json"
    destination.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"wrote": str(destination), "elapsed_seconds": output["elapsed_seconds"]}))
    print(json.dumps({
        "nodes": output["identity"]["task_nodes"],
        "contexts": output["identity"]["joint_contexts"],
        "train_all_zero": output["identity"]["train_all_zero_fraction"],
        "covered": output["graph"]["covered_nodes"],
        "coverage": output["graph"]["neighbor_coverage"],
        "reverse_edge_ratio": output["graph"]["reverse_edge_ratio"],
        "covered_degree": output["graph"]["undirected_degree_covered_nodes_only"],
        "matches_run": output["graph"]["matches_run_coverage"],
        "projection": output["cross_context_skill_projection_legacy_explanation_only"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
