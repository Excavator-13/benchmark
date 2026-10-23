#!/usr/bin/env python3
"""P02-T003 失败后诊断：实现、尺度与图语义的已交付证据汇总。

门槛判定见 `gate.py`。本脚本只读取：

- 三组 T002 批次的 `checks/*.json`（recompute 与 three-graph average）；
- 90 个 run 的 `summary.md`（选中 epoch 与验证 MSE）；
- 当前检出的骨架实现源码（核对检查记录的文件指纹）。

它不访问 D 盘训练根、不重算预测、不训练模型。产出 `diagnose.json`，并由
`report.md` 解释；脚本本身不下结论。

    python3 -B research/reports/p02-t003-20261022-01/diagnose.py
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = Path(__file__).resolve().parent

BATCHES: Dict[str, Dict[str, str]] = {
    "r0": {
        "dir": "research/reports/p02-t002-r0-20261022-01",
    },
    "region": {
        "dir": "research/reports/p02-t002-region-20261022-01",
    },
    "r2": {
        "dir": "research/reports/p02-t002-r2-20261020-02",
    },
}

MODEL_SEEDS = (0, 1, 2)
BASELINES = ("LastValue", "SeasonalNaive12", "TrainMean27", "WindowMean6", "Zero")
ACTIVITY_GROUPS = ("inactive", "low", "medium", "high")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def contract() -> Dict[str, Any]:
    """Read frozen constants from the skeleton protocol module text."""
    path = ROOT / "benchmark/graph_value_skeleton/protocol.py"
    text = path.read_text(encoding="utf-8")
    found: Dict[str, Any] = {}
    for name, pattern in (
        ("hidden_dim", r"HIDDEN_DIM = (\d+)"),
        ("epochs", r"EPOCHS = (\d+)"),
        ("learning_rate", r'"lr": ([0-9.eE+-]+)'),
        ("loss", r'LOSS = "([^"]+)"'),
        ("preprocessing", r'PREPROCESSING = "([^"]+)"'),
        ("no_early_stopping", r"NO_EARLY_STOPPING = (\w+)"),
    ):
        match = re.search(pattern, text)
        found[name] = match.group(1) if match else None
    p01 = ROOT / "benchmark/nograph_baseline/protocol.py"
    p01_text = p01.read_text(encoding="utf-8")
    for name in ("INPUT_LENGTH", "HORIZON"):
        match = re.search(rf"{name} = (\d+)", p01_text)
        found[name.lower()] = int(match.group(1)) if match else None
    found["epochs_source"] = "benchmark/graph_value_skeleton/protocol.py"
    found["optimizer_steps_per_epoch"] = (
        "one full-batch Adam step per epoch (see training.py loop)"
    )
    found["parameter_count_expected"] = 3459
    found["parameter_count_breakdown"] = {"gru": 3360, "head": 99}
    return found


def implementation_identity() -> Dict[str, Any]:
    """Compare check-recorded source hashes with the current checkout.

    Recorded hashes come from the Windows checkout at run time, so a file that
    differs only by CRLF/LF is reported as `normalized_match` rather than a
    content difference.
    """
    result: Dict[str, Any] = {}
    for dataset, config in BATCHES.items():
        checks = sorted((ROOT / config["dir"] / "checks").glob("*graph-s0-a-recompute.json"))
        if not checks:
            result[dataset] = {"error": "no graph check"}
            continue
        check = load(checks[0])
        files = check["checker"]["source"]["files"]
        commit = check["checker"]["source"].get("commit")
        raw_matches: List[str] = []
        normalized_matches: List[str] = []
        mismatches: List[str] = []
        for name, recorded in sorted(files.items()):
            path = ROOT / name
            if not path.is_file():
                mismatches.append(f"{name}: missing in checkout")
                continue
            payload = path.read_bytes()
            if sha256_bytes(payload) == recorded:
                raw_matches.append(name)
                normalized_matches.append(name)
                continue
            normalized = payload.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            if sha256_bytes(normalized) == recorded:
                normalized_matches.append(name)
            else:
                mismatches.append(f"{name}: content differs")
        result[dataset] = {
            "recorded_source_commit": commit,
            "check_file": str(checks[0].relative_to(ROOT)),
            "file_count": len(files),
            "raw_match_count": len(raw_matches),
            "normalized_match_count": len(normalized_matches),
            "mismatches": mismatches,
            "raw_matches": raw_matches,
            "normalized_only_matches": sorted(
                set(normalized_matches) - set(raw_matches)
            ),
        }
    return result


def convergence() -> Dict[str, Any]:
    pattern = re.compile(r"Selected epoch: (\d+) \(validation MSE ([\d.eE+-]+)\)")
    dataset_pattern = re.compile(r"Dataset: `([^`]+)`")
    method_pattern = re.compile(r"Method: `([^`]+)`")
    seed_pattern = re.compile(r"Model seed: (\d+)")
    runs: List[Dict[str, Any]] = []
    for path in sorted((ROOT / "research/runs").glob("p02-t002-*/summary.md")):
        text = path.read_text(encoding="utf-8")
        match = pattern.search(text)
        dataset = dataset_pattern.search(text)
        method = method_pattern.search(text)
        seed = seed_pattern.search(text)
        if not (match and dataset and method and seed):
            continue
        runs.append(
            {
                "run_id": path.parent.name,
                "dataset": dataset.group(1).split("/")[0],
                "method": method.group(1),
                "model_seed": int(seed.group(1)),
                "selected_epoch": int(match.group(1)),
                "selected_validation_mse": float(match.group(2)),
            }
        )
    per_dataset: Dict[str, Dict[str, Any]] = {}
    for dataset in BATCHES:
        subset = [run for run in runs if run["dataset"] == dataset]
        per_dataset[dataset] = {
            "run_count": len(subset),
            "selected_epochs": sorted({run["selected_epoch"] for run in subset}),
            "at_budget_end": sum(
                1 for run in subset if run["selected_epoch"] == 200
            ),
            "selected_validation_mse_by_method": {
                method: sorted(
                    round(run["selected_validation_mse"], 3)
                    for run in subset
                    if run["method"] == method
                )
                for method in ("self", "graph", "shuffled")
            },
        }
    return {
        "run_count": len(runs),
        "budget_epochs": 200,
        "selected_epoch_counts": {
            str(epoch): sum(1 for run in runs if run["selected_epoch"] == epoch)
            for epoch in sorted({run["selected_epoch"] for run in runs})
        },
        "at_budget_end": sum(1 for run in runs if run["selected_epoch"] == 200),
        "per_dataset": per_dataset,
    }


def metrics_from_check(path: Path) -> Dict[str, Any]:
    result = load(path)["result"]["recomputed_methods"]["test"]
    methods = sorted(set(result) - set(BASELINES))
    if len(methods) != 1:
        raise SystemExit(f"{path.name}: unexpected methods {methods}")
    return {"own_method": methods[0], "metrics": result}


def _group_table(
    table: Dict[str, Dict[str, Dict[str, Any]]], family: str, group: str
) -> Dict[str, Any]:
    return {
        method: values[family][group]["MAE"]
        for method, values in table.items()
        if group in values.get(family, {})
    }


def scale_and_signal() -> Dict[str, Any]:
    datasets: Dict[str, Any] = {}
    for dataset, config in BATCHES.items():
        checks = ROOT / config["dir"] / "checks"
        per_seed: List[Dict[str, Any]] = []
        for seed in MODEL_SEEDS:
            graph_check = load(
                sorted(checks.glob(f"*-graph-s{seed}-a-recompute.json"))[0]
            )["result"]["recomputed_methods"]["test"]
            self_check = load(
                sorted(checks.glob(f"*-self-s{seed}-a-recompute.json"))[0]
            )["result"]["recomputed_methods"]["test"]
            summary = load(sorted(checks.glob(f"*-s{seed}-a-shuffled-summary.json"))[0])[
                "result"
            ]
            per_seed.append(
                {
                    "model_seed": seed,
                    "graph": graph_check["graph"],
                    "self": self_check["self"],
                    "baselines": {
                        name: graph_check[name] for name in BASELINES
                    },
                    "control_test_MAE": summary["control_test_MAE"],
                }
            )
        # Seed-mean scalars.
        def seed_mean(selector) -> float:
            return sum(selector(item) for item in per_seed) / len(per_seed)

        graph_mae = seed_mean(lambda item: item["graph"]["MAE"])
        graph_rmse = seed_mean(lambda item: item["graph"]["RMSE"])
        self_mae = seed_mean(lambda item: item["self"]["MAE"])
        last_mae = seed_mean(lambda item: item["baselines"]["LastValue"]["MAE"])
        last_rmse = seed_mean(lambda item: item["baselines"]["LastValue"]["RMSE"])
        zero_mae = seed_mean(lambda item: item["baselines"]["Zero"]["MAE"])
        zero_rmse = seed_mean(lambda item: item["baselines"]["Zero"]["RMSE"])
        window_mae = seed_mean(lambda item: item["baselines"]["WindowMean6"]["MAE"])
        control_mae = seed_mean(lambda item: item["control_test_MAE"])

        group_rows: Dict[str, Dict[str, Dict[str, float]]] = {}
        for group in ACTIVITY_GROUPS:
            row = {
                "Zero": seed_mean(
                    lambda item, g=group: item["baselines"]["Zero"][
                        "activity_groups"
                    ][g]["MAE"]
                ),
                "graph": seed_mean(
                    lambda item, g=group: item["graph"]["activity_groups"][g]["MAE"]
                ),
                "self": seed_mean(
                    lambda item, g=group: item["self"]["activity_groups"][g]["MAE"]
                ),
                "LastValue": seed_mean(
                    lambda item, g=group: item["baselines"]["LastValue"][
                        "activity_groups"
                    ][g]["MAE"]
                ),
                "WindowMean6": seed_mean(
                    lambda item, g=group: item["baselines"]["WindowMean6"][
                        "activity_groups"
                    ][g]["MAE"]
                ),
            }
            row["graph_over_zero"] = row["graph"] / row["Zero"]
            row["graph_over_lastvalue"] = row["graph"] / row["LastValue"]
            row["graph_error_contribution_fraction"] = seed_mean(
                lambda item, g=group: item["graph"]["activity_groups"][g][
                    "absolute_error_contribution_fraction"
                ]
            )
            row["nodes"] = per_seed[0]["graph"]["activity_groups"][group]["nodes"]
            group_rows[group] = row

        neighbor_rows: Dict[str, Dict[str, float]] = {}
        for group in ("no_nonself_neighbor", "has_nonself_neighbor"):
            node_count = per_seed[0]["graph"]["neighbor_groups"][group]["nodes"]
            neighbor_rows[group] = {
                "nodes": node_count,
                "graph": seed_mean(
                    lambda item, g=group: item["graph"]["neighbor_groups"][g]["MAE"]
                ),
                "self": seed_mean(
                    lambda item, g=group: item["self"]["neighbor_groups"][g]["MAE"]
                ),
                "LastValue": seed_mean(
                    lambda item, g=group: item["baselines"]["LastValue"][
                        "neighbor_groups"
                    ][g]["MAE"]
                ),
                "Zero": seed_mean(
                    lambda item, g=group: item["baselines"]["Zero"]["neighbor_groups"][
                        g
                    ]["MAE"]
                ),
            }
        coverage_nodes = neighbor_rows["has_nonself_neighbor"]["nodes"]
        all_nodes = sum(row["nodes"] for row in neighbor_rows.values())
        neighbor_rows["coverage_fraction"] = coverage_nodes / all_nodes

        horizon_rows: Dict[str, Dict[str, float]] = {}
        for horizon in ("h1", "h2", "h3"):
            horizon_rows[horizon] = {
                "Zero": seed_mean(
                    lambda item, h=horizon: item["baselines"]["Zero"]["horizons"][h][
                        "MAE"
                    ]
                ),
                "graph": seed_mean(
                    lambda item, h=horizon: item["graph"]["horizons"][h]["MAE"]
                ),
                "self": seed_mean(
                    lambda item, h=horizon: item["self"]["horizons"][h]["MAE"]
                ),
                "LastValue": seed_mean(
                    lambda item, h=horizon: item["baselines"]["LastValue"]["horizons"][
                        h
                    ]["MAE"]
                ),
            }

        window_rows = [
            {
                "start": window["start"],
                "forecast_origin": window["forecast_origin"],
                "graph": window["MAE"],
                "elements": window["elements"],
            }
            for window in per_seed[0]["graph"]["windows"]
        ]

        datasets[dataset] = {
            "seed_mean": {
                "graph_MAE": graph_mae,
                "graph_RMSE": graph_rmse,
                "self_MAE": self_mae,
                "self_RMSE": seed_mean(lambda item: item["self"]["RMSE"]),
                "control_MAE": control_mae,
                "LastValue_MAE": last_mae,
                "LastValue_RMSE": last_rmse,
                "WindowMean6_MAE": window_mae,
                "Zero_MAE": zero_mae,
                "Zero_RMSE": zero_rmse,
                "graph_over_Zero_MAE": graph_mae / zero_mae,
                "graph_over_Zero_RMSE": graph_rmse / zero_rmse,
                "graph_over_LastValue_MAE": graph_mae / last_mae,
                "graph_over_LastValue_RMSE": graph_rmse / last_rmse,
                "graph_minus_self_relative": (graph_mae - self_mae) / self_mae,
                "graph_minus_control_relative": (graph_mae - control_mae) / control_mae,
                "graph_minus_Zero_relative": (graph_mae - zero_mae) / zero_mae,
            },
            "negative_prediction_ratio_seed0": {
                "graph": per_seed[0]["graph"]["negative_prediction_ratio"],
                "LastValue": per_seed[0]["baselines"]["LastValue"][
                    "negative_prediction_ratio"
                ],
                "Zero": per_seed[0]["baselines"]["Zero"]["negative_prediction_ratio"],
            },
            "group_rows": group_rows,
            "neighbor_rows": neighbor_rows,
            "horizon_rows": horizon_rows,
            "window_MAE_seed0": window_rows,
            "seed_spread": {
                "graph_MAE": {
                    str(item["model_seed"]): item["graph"]["MAE"]
                    for item in per_seed
                },
                "self_MAE": {
                    str(item["model_seed"]): item["self"]["MAE"]
                    for item in per_seed
                },
                "control_MAE": {
                    str(item["model_seed"]): item["control_test_MAE"]
                    for item in per_seed
                },
            },
        }
    return datasets


def main() -> int:
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "script": "diagnose.py",
        "script_sha256": sha256_file(Path(__file__)),
        "protocol": "P1-count-L6-H3-v3",
        "contract": contract(),
        "implementation_identity": implementation_identity(),
        "convergence": convergence(),
        "scale_and_signal": scale_and_signal(),
        "inputs": {
            dataset: str((ROOT / config["dir"]).relative_to(ROOT))
            for dataset, config in BATCHES.items()
        },
        "scope_note": (
            "只读已交付 checks 与 run summary；预测数组、模型权重与训练历史仍在"
            " Windows D 执行根，未在本机核验，故不对预测分布作直接统计。"
        ),
    }
    out = REPORT_DIR / "diagnose.json"
    with out.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    print("wrote", out)
    print("convergence:", payload["convergence"]["at_budget_end"], "of",
          payload["convergence"]["run_count"], "at epoch 200")
    for dataset, values in payload["scale_and_signal"].items():
        mean = values["seed_mean"]
        print(
            dataset,
            "graph/Zero MAE={:.4f}".format(mean["graph_over_Zero_MAE"]),
            "graph/LastValue MAE={:.4f}".format(mean["graph_over_LastValue_MAE"]),
            "graph-self={:.2%}".format(mean["graph_minus_self_relative"]),
            "coverage={:.2%}".format(values["neighbor_rows"]["coverage_fraction"]),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
