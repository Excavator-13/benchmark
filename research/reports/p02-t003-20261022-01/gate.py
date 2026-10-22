#!/usr/bin/env python3
"""P02-T003 §6.2 门槛判定：读取 T002 三组已交付 checks，计算配对 seed 收益。

只读取 `research/reports/` 下三组 T002 批次的检查输出（recompute 与
three-graph average），不访问训练根、不重算预测、不训练模型。判定规则来自
`research/phases/P01/protocol.md` §6.2 #1–#5：

1. 同 seed 重复的归一化 MAE 差 ≤ 1e-6（CPU）；
2. 开发筛查使用 seed 0,1,2 的配对误差；
3. 收益 gain_s = (MAE_ref_s - MAE_candidate_s)/MAE_ref_s，要求 ≥2/3 seed 为正
   且收益中位数 ≥1%；
4. 真实图必须相对自身分支与三图平均打乱对照都满足上述门槛；
5. 整体改善还要求真实图总体 RMSE 的跨 seed 均值相对 LastValue 恶化 ≤1%。

参考值取每个 repeat 的重复 a/b；门槛只在两个 repeat 都通过时记为整体通过，
避免按 repeat 挑选。用法：

    python3 -B research/reports/p02-t003-20261022-01/gate.py [--out gate.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = Path(__file__).resolve().parent

BATCHES: Dict[str, Dict[str, str]] = {
    "r0": {
        "dir": "research/reports/p02-t002-r0-20261022-01",
        "batch": "p02-t002-r0-20261022-01",
        "result": "research/reports/p02-t002-r0-20261022-01/result.md",
    },
    "region": {
        "dir": "research/reports/p02-t002-region-20261022-01",
        "batch": "p02-t002-region-20261022-01",
        "result": "research/reports/p02-t002-region-20261022-01/result.md",
    },
    "r2": {
        "dir": "research/reports/p02-t002-r2-20261020-02",
        "batch": "p02-t002-r2-20261020-02",
        "result": "research/reports/p02-t002-r2-20261020-02/result.md",
    },
}

METHODS = ("self", "graph", "shuffled0", "shuffled1", "shuffled2")
GRAPH_SEEDS = (0, 1, 2)
MODEL_SEEDS = (0, 1, 2)
REPEATS = ("a", "b")
BASELINES = ("LastValue", "SeasonalNaive12", "TrainMean27", "WindowMean6", "Zero")

TOLERANCE_REPEAT = 1e-6
GATE_MIN_POSITIVE = 2  # 2/3
GATE_MEDIAN_MIN = 0.01  # 1%
RMSE_DETERIORATION_MAX = 0.01  # 1%

GROUP_FAMILIES = (
    "activity_groups",
    "neighbor_groups",
    "horizons",
    "constant_groups",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def pick_method(result: Dict[str, Any], expected: str) -> str:
    methods = sorted(set(result["recomputed_methods"]["test"]) - set(BASELINES))
    allowed = "shuffled" if expected.startswith("shuffled") else expected
    if methods != [allowed]:
        raise SystemExit(
            f"unexpected recomputed methods {methods}, expected [{allowed!r}]"
        )
    return methods[0]


def normalized_repeat_diff(mae_a: float, mae_b: float) -> float:
    return abs(mae_a - mae_b) / max(1.0, mae_a, mae_b)


def median(values: List[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if n % 2:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


def gate(gains: List[float]) -> Dict[str, Any]:
    positives = sum(1 for value in gains if value > 0)
    med = median(gains)
    return {
        "gains": gains,
        "positive_count": positives,
        "seed_count": len(gains),
        "median_gain": med,
        "min_positive_required": GATE_MIN_POSITIVE,
        "median_required": GATE_MEDIAN_MIN,
        "pass": positives >= GATE_MIN_POSITIVE and med >= GATE_MEDIAN_MIN,
    }


def gain(reference: float, candidate: float) -> Optional[float]:
    if reference == 0:
        return None
    return (reference - candidate) / reference


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPORT_DIR / "gate.json"))
    args = parser.parse_args()

    inputs: Dict[str, Dict[str, Any]] = {}
    per_dataset: Dict[str, Any] = {}
    errors: List[str] = []

    for dataset, config in BATCHES.items():
        batch_dir = ROOT / config["dir"]
        checks_dir = batch_dir / "checks"
        files = sorted(checks_dir.glob("*.json"))
        if len(files) != 51:
            errors.append(f"{dataset}: expected 51 check files, found {len(files)}")
        inputs[dataset] = {
            "batch": config["batch"],
            "batch_dir": config["dir"],
            "checks_dir": str(checks_dir.relative_to(ROOT)),
            "check_file_count": len(files),
            "check_sha256": {
                path.name: sha256_file(path) for path in files
            },
        }

        # MAE / RMSE per method, model seed, repeat.
        overall: Dict[str, Dict[str, Dict[str, float]]] = {
            repeat: {method: {} for method in METHODS} for repeat in REPEATS
        }
        rmse: Dict[str, Dict[str, Dict[str, float]]] = {
            repeat: {method: {} for method in ("graph", "self", "LastValue")}
            for repeat in REPEATS
        }
        group_mae: Dict[str, Dict[str, Dict[str, Dict[str, float]]]] = {
            repeat: {method: {} for method in METHODS} for repeat in REPEATS
        }
        control: Dict[str, Dict[int, float]] = {repeat: {} for repeat in REPEATS}
        repeat_diffs: List[Dict[str, Any]] = []
        status_problems: List[str] = []

        for repeat in REPEATS:
            for method in METHODS:
                for seed in MODEL_SEEDS:
                    pattern = f"*-{method}-s{seed}-{repeat}-recompute.json"
                    matches = sorted(checks_dir.glob(pattern))
                    if len(matches) != 1:
                        errors.append(
                            f"{dataset}: {pattern} matched {len(matches)} files"
                        )
                        continue
                    check = load(matches[0])
                    if check.get("status") != "ok" or check.get("errors"):
                        status_problems.append(
                            f"{matches[0].name}: status={check.get('status')} "
                            f"errors={check.get('errors')}"
                        )
                    result = check["result"]
                    name = pick_method(result, method)
                    metrics = result["recomputed_methods"]["test"][name]
                    overall[repeat][method][seed] = metrics["MAE"]
                    if method in ("graph", "self"):
                        rmse[repeat][method][seed] = metrics["RMSE"]
                    rmse[repeat]["LastValue"][seed] = result["recomputed_methods"][
                        "test"
                    ]["LastValue"]["RMSE"]
                    for family in GROUP_FAMILIES:
                        for group, payload in metrics.get(family, {}).items():
                            group_mae[repeat][method].setdefault(family, {}).setdefault(
                                group, {}
                            )[seed] = payload["MAE"]
                    zero = metrics.get("training_all_zero_group")
                    if zero and zero.get("status") == "ok":
                        group_mae[repeat][method].setdefault(
                            "training_all_zero_group", {}
                        ).setdefault("all_zero", {})[seed] = zero["MAE"]

            # Three-graph average control per model seed.
            for seed in MODEL_SEEDS:
                pattern = f"*-s{seed}-{repeat}-shuffled-summary.json"
                matches = sorted(checks_dir.glob(pattern))
                if len(matches) != 1:
                    errors.append(
                        f"{dataset}: {pattern} matched {len(matches)} files"
                    )
                    continue
                summary = load(matches[0])
                if summary.get("status") != "ok" or summary.get("errors"):
                    status_problems.append(
                        f"{matches[0].name}: status={summary.get('status')}"
                    )
                payload = summary["result"]
                if payload.get("member_identity_retained") is not True:
                    status_problems.append(
                        f"{matches[0].name}: member identity not retained"
                    )
                if payload.get("weakest_graph_selected") is not False:
                    status_problems.append(
                        f"{matches[0].name}: weak graph selected flag present"
                    )
                if payload.get("model_seed") != seed or payload.get(
                    "dataset"
                ) != dataset:
                    status_problems.append(
                        f"{matches[0].name}: identity mismatch"
                    )
                control[repeat][seed] = payload["control_test_MAE"]

        # Repeat consistency (#1) and per-seed reproducibility.
        for method in METHODS:
            for seed in MODEL_SEEDS:
                a = overall["a"][method].get(seed)
                b = overall["b"][method].get(seed)
                if a is None or b is None:
                    continue
                repeat_diffs.append(
                    {
                        "method": method,
                        "model_seed": seed,
                        "mae_a": a,
                        "mae_b": b,
                        "normalized_difference": normalized_repeat_diff(a, b),
                        "pass": normalized_repeat_diff(a, b) <= TOLERANCE_REPEAT,
                    }
                )

        dataset_gate: Dict[str, Any] = {
            "overall": {},
            "rmse": {},
            "repeat_consistency": {
                "tolerance": TOLERANCE_REPEAT,
                "max_normalized_difference": max(
                    (item["normalized_difference"] for item in repeat_diffs),
                    default=None,
                ),
                "pairs": repeat_diffs,
                "pass": all(item["pass"] for item in repeat_diffs),
            },
            "status_problems": status_problems,
            "groups": {},
        }

        for repeat in REPEATS:
            seeds = {
                seed: {
                    "self": overall[repeat]["self"][seed],
                    "graph": overall[repeat]["graph"][seed],
                    "shuffled": {
                        str(seed_index): overall[repeat][f"shuffled{seed_index}"][seed]
                        for seed_index in GRAPH_SEEDS
                    },
                    "control_three_graph_average": control[repeat][seed],
                    "self_minus_graph": overall[repeat]["self"][seed]
                    - overall[repeat]["graph"][seed],
                    "control_minus_graph": control[repeat][seed]
                    - overall[repeat]["graph"][seed],
                }
                for seed in MODEL_SEEDS
            }
            gains_self = [
                gain(seeds[seed]["self"], seeds[seed]["graph"]) for seed in MODEL_SEEDS
            ]
            gains_control = [
                gain(seeds[seed]["control_three_graph_average"], seeds[seed]["graph"])
                for seed in MODEL_SEEDS
            ]
            if any(value is None for value in gains_self + gains_control):
                errors.append(f"{dataset}/{repeat}: zero reference MAE")
                gains_self = [value for value in gains_self if value is not None]
                gains_control = [
                    value for value in gains_control if value is not None
                ]
            dataset_gate["overall"][repeat] = {
                "seeds": seeds,
                "gate_vs_self": gate(gains_self),
                "gate_vs_shuffled": gate(gains_control),
            }
            # Per-group gates (derived control = mean of the three shuffled MAEs).
            group_names: Dict[str, set] = {}
            for method in METHODS:
                for family, values in group_mae[repeat][method].items():
                    for group in values:
                        group_names.setdefault(family, set()).add(group)
            for family, names in sorted(group_names.items()):
                for group in sorted(names):
                    refs_self = []
                    refs_control = []
                    ok = True
                    for seed in MODEL_SEEDS:
                        try:
                            mae_self = group_mae[repeat]["self"][family][group][seed]
                            mae_graph = group_mae[repeat]["graph"][family][group][seed]
                            shuffled = [
                                group_mae[repeat][f"shuffled{index}"][family][group][
                                    seed
                                ]
                                for index in GRAPH_SEEDS
                            ]
                        except KeyError:
                            ok = False
                            break
                        mean_shuffled = sum(shuffled) / len(shuffled)
                        value_self = gain(mae_self, mae_graph)
                        value_control = gain(mean_shuffled, mae_graph)
                        if value_self is None or value_control is None:
                            ok = False
                            break
                        refs_self.append(value_self)
                        refs_control.append(value_control)
                    if not ok:
                        continue
                    dataset_gate["groups"].setdefault(repeat, {}).setdefault(
                        family, {}
                    )[group] = {
                        "gate_vs_self": gate(refs_self),
                        "gate_vs_shuffled": gate(refs_control),
                    }
            # RMSE constraint (#5): cross-seed mean vs LastValue.
            graph_rmse = [rmse[repeat]["graph"][seed] for seed in MODEL_SEEDS]
            ref_rmse = [rmse[repeat]["LastValue"][seed] for seed in MODEL_SEEDS]
            graph_mean = sum(graph_rmse) / len(graph_rmse)
            ref_mean = sum(ref_rmse) / len(ref_rmse)
            deterioration = (
                (graph_mean - ref_mean) / ref_mean if ref_mean else None
            )
            dataset_gate["rmse"][repeat] = {
                "graph_rmse_per_seed": graph_rmse,
                "reference_rmse_per_seed": ref_rmse,
                "graph_cross_seed_mean": graph_mean,
                "reference_cross_seed_mean": ref_mean,
                "relative_deterioration": deterioration,
                "allowed": RMSE_DETERIORATION_MAX,
                "pass": deterioration is not None
                and deterioration <= RMSE_DETERIORATION_MAX,
            }
            dataset_gate["overall"][repeat]["graph_vs_self_relative_gap"] = (
                (overall[repeat]["graph"][0] - overall[repeat]["self"][0])
                / overall[repeat]["self"][0]
            )

        comparisons = {}
        for repeat in REPEATS:
            comparisons[repeat] = {
                "vs_self": dataset_gate["overall"][repeat]["gate_vs_self"]["pass"],
                "vs_shuffled": dataset_gate["overall"][repeat]["gate_vs_shuffled"][
                    "pass"
                ],
                "rmse": dataset_gate["rmse"][repeat]["pass"],
            }
            comparisons[repeat]["all"] = all(comparisons[repeat].values())
        dataset_gate["gate"] = {
            "per_repeat": comparisons,
            "pass": all(comparisons[repeat]["all"] for repeat in REPEATS),
            "requires": f">= {GATE_MIN_POSITIVE}/3 positive seeds and median gain "
            f">= {GATE_MEDIAN_MIN:.0%} in both comparisons, RMSE deterioration "
            f"<= {RMSE_DETERIORATION_MAX:.0%}, in both repeats",
        }
        per_dataset[dataset] = dataset_gate

    verdict = {
        "datasets": {
            dataset: per_dataset[dataset]["gate"]["pass"] for dataset in BATCHES
        },
        "overall": all(
            per_dataset[dataset]["gate"]["pass"] for dataset in BATCHES
        ),
        "errors": errors,
    }

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "script": "gate.py",
        "script_sha256": sha256_file(Path(__file__)),
        "protocol": "P1-count-L6-H3-v3",
        "thresholds": {
            "repeat_normalized_diff_max": TOLERANCE_REPEAT,
            "min_positive_seeds": GATE_MIN_POSITIVE,
            "seed_count": len(MODEL_SEEDS),
            "median_gain_min": GATE_MEDIAN_MIN,
            "rmse_relative_deterioration_max": RMSE_DETERIORATION_MAX,
        },
        "inputs": inputs,
        "datasets": per_dataset,
        "verdict": verdict,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    print(f"wrote {out_path}")
    for dataset in BATCHES:
        overall = per_dataset[dataset]["overall"]["a"]
        print(
            dataset,
            "vs_self_median={:.4%}".format(overall["gate_vs_self"]["median_gain"]),
            "vs_self_pos={}/3".format(overall["gate_vs_self"]["positive_count"]),
            "vs_shuf_median={:.4%}".format(
                overall["gate_vs_shuffled"]["median_gain"]
            ),
            "vs_shuf_pos={}/3".format(
                overall["gate_vs_shuffled"]["positive_count"]
            ),
            "rmse_deterioration={:.2%}".format(
                per_dataset[dataset]["rmse"]["a"]["relative_deterioration"]
            ),
            "gate_pass=",
            per_dataset[dataset]["gate"]["pass"],
        )
    if errors:
        print("errors:")
        for error in errors:
            print(" -", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
