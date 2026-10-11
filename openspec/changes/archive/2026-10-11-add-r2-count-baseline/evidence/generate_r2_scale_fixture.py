#!/usr/bin/env python
"""Generate the reproducible ``r2/count`` scale fixture for development cost checks.

This script is development/implementation evidence for the OpenSpec change
``add-r2-count-baseline``.  It writes a fixed-seed synthetic count demand table
with a ``52 x 2335 x 36`` ``(r2_id, skill_id, month)`` grid (121,420 unique
context-qualified nodes) plus a deterministic context-internal coverage graph
that deliberately leaves some skills isolated.

Properties relied on by the evidence:

* only NumPy, pandas and PyArrow are imported: no graph library, no GPU library;
* the output directory is never allowed to resolve inside ``research/runs`` and
  the large fixture is expected to live under the ignored ``scratch/`` tree or a
  system temporary directory, never in Git;
* the generation command, seed, dimensions and input SHA256 digests are written
  to ``manifest.json`` next to the tables and printed to stdout.

The synthetic data is engineering evidence only.  It is not real ``r2`` demand,
not a formal scientific run and not a cost measurement of the real dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

DEFAULT_CONTEXTS = 52
DEFAULT_SKILLS = 2335
DEFAULT_MONTHS = 36
DEFAULT_SEED = 20261011
#: Skills per context joined by a non-self in-context edge; the rest stay isolated.
DEFAULT_COVERED_SKILLS = 2000
MANIFEST_VERSION = "r2-scale-fixture-v1"


def month_labels(months: int) -> List[str]:
    """Return the canonical ``YYYY-MM`` labels for 2021-01..2023-12."""
    labels = [
        f"{year}-{month:02d}"
        for year in (2021, 2022, 2023)
        for month in range(1, 13)
    ]
    return labels[:months]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _refuse_formal_namespace(output_dir: Path, repo_root: Path) -> None:
    """Fail closed if the fixture would land in the formal research namespace."""
    resolved = output_dir.resolve()
    formal = (repo_root / "research" / "runs").resolve()
    if resolved == formal or formal in resolved.parents:
        raise SystemExit(
            f"refusing to write a synthetic fixture inside the formal experiment "
            f"namespace {formal}: {resolved}"
        )


def canonical_keys(contexts: int, skills: int) -> np.ndarray:
    """Return the full ``(r2_id, skill_id)`` grid in ascending key order."""
    return np.array(
        [(context, skill) for context in range(contexts) for skill in range(skills)],
        dtype=np.int64,
    )


def build_signal(node_count: int, months: int, seed: int) -> np.ndarray:
    """Return the fixed-seed integer-valued count signal as float64 ``[N, months]``."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 40, size=(node_count, months)).astype(np.float64)


def write_demand(path: Path, keys: np.ndarray, signal: np.ndarray, months: Sequence[str]) -> Path:
    import pandas as pd

    frame = pd.DataFrame(
        {"r2_id": keys[:, 0], "skill_id": keys[:, 1]}
    )
    for index, month in enumerate(months):
        frame[month] = signal[:, index]
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def build_graph_rows(contexts: int, skills: int, covered_skills: int) -> List[Tuple[int, int, int]]:
    """Pair adjacent covered skills inside each context; leave the tail isolated."""
    limit = min(covered_skills, skills)
    return [
        (context, skill, skill + 1)
        for context in range(contexts)
        for skill in range(0, limit - 1, 2)
    ]


def write_graph(path: Path, rows: Sequence[Tuple[int, int, int]]) -> Path:
    import pandas as pd

    frame = pd.DataFrame(list(rows), columns=["r2_id", "row_id", "col_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def verify_fixture(
    demand_path: Path,
    graph_path: Path,
    *,
    contexts: int,
    skills: int,
    months: Sequence[str],
) -> Dict[str, Any]:
    """Read the written tables back and assert the documented grid contract."""
    import pandas as pd

    demand = pd.read_parquet(demand_path)
    expected_columns = ["r2_id", "skill_id", *months]
    if list(demand.columns) != expected_columns:
        raise SystemExit(
            f"demand columns {list(demand.columns)} != {expected_columns}"
        )
    expected_nodes = contexts * skills
    if len(demand) != expected_nodes:
        raise SystemExit(f"demand rows {len(demand)} != {expected_nodes}")
    keys = demand[["r2_id", "skill_id"]].to_numpy(dtype=np.int64)
    if pd.DataFrame(keys).duplicated().any():
        raise SystemExit("demand contains duplicate (r2_id, skill_id) identities")
    order = np.lexsort((keys[:, 1], keys[:, 0]))
    if not np.array_equal(keys[order], canonical_keys(contexts, skills)):
        raise SystemExit("demand keys are not the complete canonical r2 grid")
    if demand[list(months)].to_numpy().min() < 0:
        raise SystemExit("demand contains negative counts")

    graph = pd.read_parquet(graph_path)
    expected_graph_columns = ["r2_id", "row_id", "col_id"]
    if list(graph.columns) != expected_graph_columns:
        raise SystemExit(
            f"graph columns {list(graph.columns)} != {expected_graph_columns}"
        )
    endpoints = np.concatenate(
        [
            graph[["r2_id", "row_id"]].to_numpy(dtype=np.int64),
            graph[["r2_id", "col_id"]].to_numpy(dtype=np.int64),
        ]
    )
    known = {tuple(int(value) for value in row) for row in keys}
    unknown = [endpoint for endpoint in endpoints.tolist() if tuple(endpoint) not in known]
    if unknown:
        raise SystemExit(f"graph has {len(unknown)} endpoints outside the demand grid")
    covered = {
        (int(context), int(skill))
        for context, skill in graph[["r2_id", "row_id"]].to_numpy(dtype=np.int64)
    } | {
        (int(context), int(skill))
        for context, skill in graph[["r2_id", "col_id"]].to_numpy(dtype=np.int64)
    }
    return {
        "nodes": int(len(demand)),
        "unique_node_keys": int(len({tuple(int(v) for v in row) for row in keys})),
        "expected_grid_nodes": int(expected_nodes),
        "grid_complete": bool(len(demand) == expected_nodes),
        "months": list(months),
        "graph_rows": int(len(graph)),
        "covered_nodes": int(len(covered)),
        "isolated_nodes": int(expected_nodes - len(covered)),
        "dtype": str(demand[list(months)].to_numpy().dtype),
        "value_min": float(demand[list(months)].to_numpy().min()),
        "value_max": float(demand[list(months)].to_numpy().max()),
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "fixture output directory (default: <repo>/scratch/r2-scale-fixture; "
            "must not resolve inside research/runs)"
        ),
    )
    parser.add_argument("--contexts", type=int, default=DEFAULT_CONTEXTS)
    parser.add_argument("--skills", type=int, default=DEFAULT_SKILLS)
    parser.add_argument("--months", type=int, default=DEFAULT_MONTHS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--covered-skills",
        type=int,
        default=DEFAULT_COVERED_SKILLS,
        help="skills per context paired by an in-context non-self edge",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.months != DEFAULT_MONTHS:
        raise SystemExit(
            f"this fixture is defined for {DEFAULT_MONTHS} protocol months, "
            f"got {args.months}"
        )
    repo_root = Path(__file__).resolve().parents[4]
    output_dir = (
        Path(args.output_dir) if args.output_dir else repo_root / "scratch" / "r2-scale-fixture"
    )
    _refuse_formal_namespace(output_dir, repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    months = month_labels(args.months)
    keys = canonical_keys(args.contexts, args.skills)
    signal = build_signal(len(keys), args.months, args.seed)
    demand_path = write_demand(output_dir / "demand" / "r2.parquet", keys, signal, months)
    graph_rows = build_graph_rows(args.contexts, args.skills, args.covered_skills)
    graph_path = write_graph(output_dir / "graph" / "r2.parquet", graph_rows)

    verification = verify_fixture(
        demand_path,
        graph_path,
        contexts=args.contexts,
        skills=args.skills,
        months=months,
    )
    manifest: Dict[str, Any] = {
        "manifest_version": MANIFEST_VERSION,
        "synthetic": True,
        "purpose": "development",
        "generation_command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "seed": int(args.seed),
        "contexts": int(args.contexts),
        "skills_per_context": int(args.skills),
        "covered_skills_per_context": int(args.covered_skills),
        "demand_path": str(demand_path),
        "demand_sha256": _sha256_file(demand_path),
        "demand_bytes": int(demand_path.stat().st_size),
        "graph_path": str(graph_path),
        "graph_sha256": _sha256_file(graph_path),
        "graph_bytes": int(graph_path.stat().st_size),
        "verification": verification,
        "run_command_hint": [
            "python",
            "-m",
            "benchmark.nograph_baseline",
            "run",
            "--data-name",
            "r2",
            "--mode",
            "count",
            "--seed",
            "0",
            "--run-id",
            "<fresh-run-id>",
            "--purpose",
            "development",
            "--ridge-backend",
            "numpy",
            "--demand-path",
            str(demand_path),
            "--graph-path",
            str(graph_path),
        ],
        "notes": [
            "synthetic development fixture; not real r2 data",
            "not a formal run and not a scientific conclusion",
            "expected Ridge training samples M = 19 * nodes = "
            f"{19 * verification['nodes']}",
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
