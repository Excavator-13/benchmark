"""Read historical self-run summaries; no training or scientific metric recomputation."""
from pathlib import Path
import json
import re
import statistics


ROOT = Path(__file__).resolve().parents[3]
BATCHES = {
    "r0": "p02-t002-r0-20261022-01",
    "region": "p02-t002-region-20261022-01",
    "r2": "p02-t002-r2-20261020-02",
}


def main():
    result = {"kind": "historical_cost_summary", "new_training_executed": False, "datasets": {}}
    for dataset, batch in BATCHES.items():
        rows = []
        for seed in (0, 1, 2):
            for repeat in ("a", "b"):
                path = ROOT / "research" / "runs" / f"{batch}-{dataset}-self-s{seed}-{repeat}" / "summary.md"
                content = path.read_text()
                def field(pattern):
                    match = re.search(pattern, content)
                    if not match:
                        raise ValueError(f"Missing cost field: {path}, {pattern}")
                    return float(match.group(1))
                rows.append({
                    "source": path.relative_to(ROOT).as_posix(),
                    "total_seconds": field(r"- Total: ([\d.]+) s"),
                    "training_validation_seconds": field(r"- Training \+ validation: ([\d.]+) s"),
                    "peak_rss_bytes": int(field(r"- Peak RSS: ([\d.]+) bytes")),
                })
        result["datasets"][dataset] = {
            "runs": rows,
            "total_seconds_range": [min(row["total_seconds"] for row in rows), max(row["total_seconds"] for row in rows)],
            "median_training_validation_seconds": statistics.median(row["training_validation_seconds"] for row in rows),
            "max_peak_rss_bytes": max(row["peak_rss_bytes"] for row in rows),
            "historical_complete_training_passes": 200,
            "historical_optimizer_steps": 200,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
