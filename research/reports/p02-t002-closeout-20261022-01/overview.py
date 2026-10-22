"""Describe delivered T002 test metrics; no fitting, selection or protocol changes."""

import json
from collections import Counter
from statistics import mean, median

from audit import BATCHES, ROOT, read


def overview(dataset, batch):
    checks = ROOT / "research/reports" / batch / "checks"
    rows, selected_epochs = [], Counter()
    for file in checks.glob("*-recompute.json"):
        selected_epochs[str(read(file)["result"]["validated"]["selected_epoch"])] += 1
    for seed in range(3):
        for repeat in ("a", "b"):
            row = {"seed": seed, "repeat": repeat}
            for method in ("self", "graph"):
                report = read(checks / f"{batch}-{dataset}-{method}-s{seed}-{repeat}-recompute.json")
                methods = report["result"]["recomputed_methods"]["test"]
                for name in (method, "LastValue"):
                    row[name + "_MAE"] = methods[name]["MAE"]
                    row[name + "_RMSE"] = methods[name]["RMSE"]
            report = read(checks / f"{batch}-{dataset}-s{seed}-{repeat}-shuffled-summary.json")
            row["shuffled_MAE"] = report["result"]["control_test_MAE"]
            for reference in ("self", "shuffled"):
                value = row[reference + "_MAE"]
                row["graph_gain_vs_" + reference] = (value - row["graph_MAE"]) / value
            rows.append(row)
    primary = [row for row in rows if row["repeat"] == "a"]
    return {
        "rows": rows,
        "mean_over_seeds_repeat_a": {
            key: mean(row[key] for row in primary)
            for key in primary[0] if key.endswith(("_MAE", "_RMSE"))
        },
        "median_paired_gain_repeat_a": {
            reference: median(row["graph_gain_vs_" + reference] for row in primary)
            for reference in ("self", "shuffled")
        },
        "selected_epoch_counts_all_30_fits": dict(selected_epochs),
    }


if __name__ == "__main__":
    print(json.dumps({
        "scope": "descriptive overview requested after T002 acceptance; not a complete T003 diagnosis",
        "aggregation": "seeds 0/1/2, repeat a; b retained separately, not treated as extra seeds; shuffled is mean of three graph MAEs",
        "datasets": {d: overview(d, b) for d, b in BATCHES.items()},
    }, ensure_ascii=False, indent=2))
