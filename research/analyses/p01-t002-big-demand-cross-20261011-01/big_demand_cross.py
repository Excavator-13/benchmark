#!/usr/bin/env python3
"""T002 large-demand x activity x neighbour-coverage cross analysis.

Pre-specified grouping rules (fixed before running, see report.md):

* ``large_demand`` primary rule: within each dataset, the nodes in the top 10% of
  total demand over the fixed 27 training observation months
  (2021-01..2023-03), taking ``ceil(0.10 * N)`` nodes in canonical node order on
  ties.  Top 1% and top 5% are reported as clearly labelled descriptive
  sensitivity only.
* activity groups: protocol section 4.1, ``activity = mean(train27 > 0)`` with the
  four fixed bins.
* neighbour coverage: context-qualified undirected degree > 0 from the raw graph.

Error contributions are read from the sealed T004 ``-002`` packages
(``node-errors.parquet``) without extracting or modifying them.  No model is
retrained and no test result is used to choose a group.
"""

from __future__ import annotations

import io
import json
import math
import tarfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTEXTS = {"r0": ["r0_id"], "region": ["region_id"]}
MONTHS = [f"{year}-{month:02d}" for year in (2021, 2022, 2023) for month in range(1, 13)]
TRAIN_MONTHS = MONTHS[:27]
METHODS = ("LastValue", "SharedRidge")
SPLIT = "test"
PRIMARY_FRACTION = 0.10
SENSITIVITY_FRACTIONS = (0.01, 0.05)


def load_demand(name: str, context: list[str]) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    frame = pd.read_parquet(REPO_ROOT / "dataset" / "demand" / f"{name}.parquet")
    frame = frame.sort_values(context + ["skill_id"], kind="stable").reset_index(drop=True)
    signal = frame[MONTHS].to_numpy(dtype=np.float64)
    activity = (signal[:, : len(TRAIN_MONTHS)] > 0).mean(axis=1)
    return frame, signal, activity


def load_neighbour_covered(name: str, context: list[str], frame: pd.DataFrame) -> np.ndarray:
    graph = pd.read_parquet(REPO_ROOT / "dataset" / "graph" / f"{name}.parquet")
    covered = set()
    for ctx, row, col in zip(graph[context[0]], graph["row_id"], graph["col_id"]):
        if row != col:
            covered.add((ctx, row))
            covered.add((ctx, col))
    keys = list(zip(frame[context[0]].tolist(), frame["skill_id"].tolist()))
    return np.array([key in covered for key in keys], dtype=bool)


def load_node_errors(name: str) -> pd.DataFrame:
    package = REPO_ROOT / "research" / "archives" / f"p01-{name}-sharedridge-002.tar.gz"
    member = f"p01-{name}-sharedridge-002/node-errors.parquet"
    with tarfile.open(package) as archive:
        handle = archive.extractfile(member)
        return pd.read_parquet(handle)


def load_test_gold_totals(name: str) -> np.ndarray:
    """Per-node total gold over the 4 test windows x 3 horizons (descriptive only)."""
    package = REPO_ROOT / "research" / "archives" / f"p01-{name}-sharedridge-002.tar.gz"
    member = f"p01-{name}-sharedridge-002/gold/test.npy"
    with tarfile.open(package) as archive:
        handle = archive.extractfile(member)
        gold = np.load(io.BytesIO(handle.read()))
    assert gold.ndim == 3 and gold.shape[0] == 4 and gold.shape[2] == 3, gold.shape
    return gold.astype(np.float64).sum(axis=(0, 2))


def group_labels(activity: np.ndarray) -> list[str]:
    labels = []
    for value in activity:
        if value == 0:
            labels.append("inactive")
        elif value <= 1 / 3:
            labels.append("low")
        elif value <= 2 / 3:
            labels.append("medium")
        else:
            labels.append("high")
    return labels


def summarise(cell_mask: np.ndarray, signal: np.ndarray, covered: np.ndarray,
              error: pd.DataFrame, gold_total: np.ndarray) -> dict:
    train_total = signal[:, : len(TRAIN_MONTHS)].sum(axis=1)
    absolute = error["absolute_error_sum"].to_numpy()
    squared = error["squared_error_sum"].to_numpy()
    elements = error["elements"].to_numpy()
    return {
        "nodes": int(cell_mask.sum()),
        "train_demand_share": float(train_total[cell_mask].sum() / train_total.sum()),
        "test_gold_share_descriptive_only": float(
            gold_total[cell_mask].sum() / gold_total.sum()
        ),
        "test_elements": int(elements[cell_mask].sum()),
        "test_absolute_error_sum": float(absolute[cell_mask].sum()),
        "test_squared_error_sum": float(squared[cell_mask].sum()),
        "absolute_error_contribution_fraction": float(absolute[cell_mask].sum() / absolute.sum()),
        "squared_error_contribution_fraction": float(squared[cell_mask].sum() / squared.sum()),
        "test_MAE": float(absolute[cell_mask].sum() / elements[cell_mask].sum()),
        "covered_nodes_in_cell": int(covered[cell_mask].sum()),
        "mean_train_total": float(train_total[cell_mask].mean()),
    }


def top_mask(train_total: np.ndarray, fraction: float) -> np.ndarray:
    count = max(1, math.ceil(fraction * train_total.size))
    order = np.lexsort((np.arange(train_total.size), -train_total))
    mask = np.zeros(train_total.size, dtype=bool)
    mask[order[:count]] = True
    return mask


def audit(name: str, context: list[str]) -> dict:
    frame, signal, activity = load_demand(name, context)
    covered = load_neighbour_covered(name, context, frame)
    labels = group_labels(activity)
    train_total = signal[:, : len(TRAIN_MONTHS)].sum(axis=1)
    primary = top_mask(train_total, PRIMARY_FRACTION)

    node_errors = load_node_errors(name)
    gold_total = load_test_gold_totals(name)
    assert set(node_errors["node_index"]) == set(range(len(frame))), f"{name}: node index mismatch"
    assert node_errors["method"].nunique() == 6 and node_errors["split"].nunique() == 2
    assert len(gold_total) == len(frame)

    result: dict = {
        "dataset": name,
        "nodes": int(len(frame)),
        "primary_rule": f"top {PRIMARY_FRACTION:.0%} of train-27 total demand",
        "large_demand_nodes": int(primary.sum()),
        "train_demand_share_of_large_demand": float(train_total[primary].sum() / train_total.sum()),
        "activity_group_counts": {
            label: int(sum(1 for value in labels if value == label))
            for label in ("inactive", "low", "medium", "high")
        },
        "covered_nodes": int(covered.sum()),
        "methods": {},
        "sensitivity_top_fractions": {},
    }

    for fraction in SENSITIVITY_FRACTIONS:
        mask = top_mask(train_total, fraction)
        result["sensitivity_top_fractions"][f"{fraction:.0%}"] = {
            "nodes": int(mask.sum()),
            "train_demand_share": float(train_total[mask].sum() / train_total.sum()),
            "covered_nodes": int(covered[mask].sum()),
            "overlap_with_primary": int((mask & primary).sum()),
        }

    for method in METHODS:
        subset = node_errors[
            (node_errors["method"] == method) & (node_errors["split"] == SPLIT)
        ].sort_values("node_index")
        assert len(subset) == len(frame), (name, method, len(subset))
        cell = lambda mask: summarise(mask, signal, covered, subset, gold_total)  # noqa: E731
        method_result = {
            "overall": cell(np.ones(len(frame), dtype=bool)),
            "large_demand": {
                "large": cell(primary),
                "rest": cell(~primary),
            },
            "large_demand_x_neighbour": {},
            "large_demand_x_activity": {},
            "neighbour_x_activity": {},
        }
        for demand_label, demand_mask in (("large", primary), ("rest", ~primary)):
            for cover_label, cover_mask in (("covered", covered), ("isolated", ~covered)):
                method_result["large_demand_x_neighbour"][f"{demand_label}|{cover_label}"] = cell(
                    demand_mask & cover_mask
                )
        for demand_label, demand_mask in (("large", primary), ("rest", ~primary)):
            for activity_label in ("inactive", "low", "medium", "high"):
                mask = np.array([label == activity_label for label in labels]) & demand_mask
                if mask.any():
                    method_result["large_demand_x_activity"][f"{demand_label}|{activity_label}"] = (
                        cell(mask)
                    )
        for cover_label, cover_mask in (("covered", covered), ("isolated", ~covered)):
            for activity_label in ("inactive", "low", "medium", "high"):
                mask = np.array([label == activity_label for label in labels]) & cover_mask
                if mask.any():
                    method_result["neighbour_x_activity"][f"{cover_label}|{activity_label}"] = (
                        cell(mask)
                    )
        result["methods"][method] = method_result
    return result


def main() -> None:
    output = {
        "analysis_id": "p01-t002-big-demand-cross-20261011-01",
        "protocol": "P1-count-L6-H3-v3",
        "records_policy": "P01-records-v2",
        "split": SPLIT,
        "error_input": "research/archives/p01-<data>-sharedridge-002.tar.gz::node-errors.parquet",
        "note": (
            "test errors are descriptive diagnostics only; groups are fixed from "
            "training-period demand and never chosen from test results"
        ),
        "results": {name: audit(name, context) for name, context in CONTEXTS.items()},
    }
    destination = Path(__file__).resolve().parent / "big-demand-cross.json"
    destination.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"wrote": str(destination)}))
    for name, result in output["results"].items():
        print("=====", name)
        print("primary top10% nodes:", result["large_demand_nodes"],
              "train demand share:", round(result["train_demand_share_of_large_demand"], 4))
        for method, values in result["methods"].items():
            print(" ", method, "overall MAE", round(values["overall"]["test_MAE"], 4))
            for key, cell in values["large_demand_x_neighbour"].items():
                print("   ", key, "n", cell["nodes"], "train_demand_share",
                      round(cell["train_demand_share"], 4), "abs_contrib",
                      round(cell["absolute_error_contribution_fraction"], 4),
                      "sq_contrib", round(cell["squared_error_contribution_fraction"], 4),
                      "MAE", round(cell["test_MAE"], 4))


if __name__ == "__main__":
    main()
