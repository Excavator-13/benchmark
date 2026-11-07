"""Descriptive audit of saved T009 arrays; does not select or modify edges."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path.cwd()
RUN = ROOT / "research/runs/p02-t009-occupation-20261107-01"
OUT = Path(__file__).parent

def read(path):
    return json.loads(path.read_text())

def load(relative):
    return np.load(RUN / "artifacts" / relative, allow_pickle=False)

report = read(RUN / "report.json")
preflight = read(OUT / "preflight.json")
check = read(OUT / "check.json")
assert check["status"] == "ok" and not check["errors"]
assert preflight["source"] == report["source"]
for name, target in report["targets"].items():
    assert preflight["targets"][name]["population"] == target["population"]
skills = load("skills.npy")
support = load("support.npy")
active = np.any(support, axis=1)
unique_supports, group_sizes = np.unique(support[active], axis=0, return_counts=True)
union = load("trends/trend_edge_index.npy")
lookup = {tuple(pair): i for i, pair in enumerate(union.tolist())}
positive = load("trends/trend_positive_counts.npy")
negative = load("trends/trend_negative_counts.npy")
eligible = load("trends/trend_eligible_counts.npy")
result = {
    "run_id": report["run_id"],
    "preflight_run_identity_match": True,
    "check_status": check["status"],
    "manifest_sha256": hashlib.sha256((RUN / "artifacts-sha256.json").read_bytes()).hexdigest(),
    "active_skills": int(active.sum()),
    "all_occupations_support_skills": int(np.sum(support.sum(axis=1) == 52)),
    "unique_nonzero_support_patterns": int(len(unique_supports)),
    "identical_support_group_sizes_descending": sorted(group_sizes.tolist(), reverse=True)[:10],
    "candidate_overlap": report["candidate_overlap"],
    "candidates": {},
    "physical_run_bytes": sum(p.stat().st_size for p in RUN.rglob("*") if p.is_file()),
    "interpretation": "Descriptive counts only; signs are not significance tests. Tie-dependent means every selecting direction lies in a cut tie group, not that every alternate tie order changes the edge.",
}
for name in ("jaccard", "cosine"):
    prefix = f"candidates/{name}/"
    edges = load(prefix + "edge_index.npy")
    selection = load(prefix + "selection_index.npy")
    selection_score = load(prefix + "selection_score.npy")
    cutoff = load(prefix + "cutoff_score.npy")
    boundary = load(prefix + "boundary_tie.npy")
    uncertain = {}
    slots = 0
    for i in range(len(skills)):
        for j, score in zip(selection[i], selection_score[i]):
            if j < 0:
                continue
            key = tuple(sorted((i, int(j))))
            dependent = bool(boundary[i] and score == cutoff[i])
            slots += int(dependent)
            uncertain[key] = uncertain.get(key, True) and dependent
    ids = np.array([lookup[tuple(pair)] for pair in edges.tolist()])
    e, p, n = eligible[ids], positive[ids], negative[ids]
    trend = report["trends"][name]
    result["candidates"][name] = {
        "edges": len(edges),
        "boundary_tie_active_fraction": float(boundary.sum() / active.sum()),
        "tie_dependent_directed_slots": slots,
        "tie_dependent_union_edges": sum(uncertain.values()),
        "tie_dependent_union_edge_fraction": sum(uncertain.values()) / len(edges),
        "cutoff_score_one_skills": int(np.sum(cutoff == 1)),
        "edges_with_both_positive_and_negative_contexts": int(np.sum((p > 0) & (n > 0))),
        "both_sign_fraction_among_eligible_edges": float(np.sum((p > 0) & (n > 0)) / np.sum(e > 0)),
        "unknown_edge_fraction": float(np.mean(e == 0)),
        "eligible_edge_context_fraction": trend["eligible_context_count"] / (52 * len(edges)),
        "negative_fraction_of_eligible_contexts": trend["negative_correlations"] / trend["eligible_context_count"],
        "graph_hashes": read(RUN / "artifacts" / prefix / "graph-hashes.json")["payload"],
    }
with (OUT / "audit.json").open("w") as handle:
    json.dump(result, handle, indent=2)
print(json.dumps({k: v for k,v in result.items() if k != "candidates"}, indent=2))
for name, values in result["candidates"].items():
    print(name, json.dumps({k:v for k,v in values.items() if k not in ("structure", "trend", "graph_hashes")}, indent=2))
