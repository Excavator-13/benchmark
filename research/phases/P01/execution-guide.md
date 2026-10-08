# 第一阶段执行指导：诊断与 baseline 操作

编写日期：2026-10-06。

这份指导落实[实验协议](protocol.md)。研究方向见[路线图](../../roadmap.md)，当前任务见[阶段计划](plan.md)，下一动作见[当前状态](../../state.md)。首轮第 3 至 5 节诊断及 T004 baseline 已完成；现有入口见第 7 节。第 3 至 5 节保留诊断方法，使用新报告目录，不覆盖旧证据。

协议以 `protocol.md` 第 3 至 6 节的 `P1-count-L6-H3-v3` 为唯一科学来源；保存政策为 `P01-records-v2`。科学计算与 v2 一致。本页的命令是操作示例，不代表本轮执行了实验。

## 1. 这一轮只要做成什么

先完成下面三个结果：

1. `r0/count` 和 `region/count` 的五项朴素基线、技能/上下文网格审计，以及预定活跃度分层结果。
2. 按正确上下文统计图覆盖与重复次数，确认原来的边权解释是否适用。
3. 有 PyTorch 环境时，核对归档 EvolveGCN-H 的标签、指标和逐窗口误差。

前两项可以在 Mac 上用 CPU 完成，不需要 PyG、图预处理 JSON 或 GPU。第三项只读现有张量，不训练模型。先不要补新 seed、改 GCN 层数或加入门控。

首轮得到的是诊断日志；共享 Ridge 的可复用入口和完整预测保存随后已由 T004 验收。新的模型改造和实验仍按阶段计划及具体授权执行。

## 2. 检查仓库和建立轻量环境

### 2.1 从仓库根目录开始

本机路径如下；换电脑时替换为实际克隆目录：

```bash
cd /Users/watuji/da_chuang/repos/benchmark
git status --short --branch
git rev-parse HEAD
ls dataset/demand/r0.parquet dataset/demand/region.parquet
ls dataset/graph/r0.parquet dataset/graph/region.parquet
ls experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/results/count/region/EvolveGCNH/0/metrics.json
ls experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/results/count/region/EvolveGCNH/1/metrics.json
```

不要在当前工作目录切回旧提交来做本轮诊断。原始 Parquet 和归档张量可以直接检查；需要重做旧训练时，再单独准备对应提交的克隆或 worktree。

### 2.2 使用独立的 CPU 环境

本机 base 的 pandas 实测为不完整的 namespace 包（`__file__ is None`，无 `read_parquet`），也未安装 PyArrow，因此这台 Mac 必须先建立并核验独立环境。其他机器只有通过实际 Parquet 读取检查后才能复用已有环境；仅能 `import pandas` 不足以证明可用。

```bash
conda create -n job-sdf-baseline python=3.11
conda activate job-sdf-baseline
python -m pip --version
python -m pip install --no-cache-dir numpy==1.26.4 pandas==2.2.3 pyarrow==17.0.0
python -c 'import sys, numpy, pandas, pyarrow; from pathlib import Path; assert Path(sys.prefix).name == "job-sdf-baseline"; assert callable(pandas.read_parquet); print(sys.executable); print(numpy.__version__, pandas.__version__, pyarrow.__version__); print(pandas.read_parquet("dataset/demand/r0.parquet", columns=["skill_id"]).shape)'
```

这些是新诊断环境的建议版本，不是旧 GPU 实验的环境复现。安装始终使用激活环境的 `python -m pip`，`--no-cache-dir` 避免本轮依赖用户 pip 缓存目录权限。暂不安装仓库整个 `requirements.txt`，其中的 CUDA wheel、DGL 和图扩展不是本轮基线所需。

默认共享 Ridge 使用 NumPy，无需 sklearn；可选 sklearn 后端按需要安装。归档张量核对需要 PyTorch，见第 5 节。若下载失败先处理网络或软件源，不能把安装失败解释为模型不能在 Mac 上运行。

### 2.3 创建独立分析报告目录

以下块启用遇错停止和管道错误检测。目录已经存在时会停止；更换分析 ID，不覆盖此前记录。第 3 至 5 节只做已有数据与结果的分析，不创建完整实验 run。临时探索可将路径换为忽略的 `scratch/`；支持科研判断的报告保存到下面的持久分析位置。

```bash
set -e
set -o pipefail
export JOB_SDF_PHASE1_ANALYSIS_ID=p01-diagnostic-YYYYMMDD-01
export JOB_SDF_PHASE1_OUTPUT="research/analyses/${JOB_SDF_PHASE1_ANALYSIS_ID}"
mkdir -p research/analyses
mkdir "$JOB_SDF_PHASE1_OUTPUT"
git rev-parse HEAD > "$JOB_SDF_PHASE1_OUTPUT/git-commit.txt"
shasum -a 256 dataset/demand/r0.parquet dataset/demand/region.parquet dataset/graph/r0.parquet dataset/graph/region.parquet > "$JOB_SDF_PHASE1_OUTPUT/source-sha256.txt"
```

重新打开终端后，激活环境、返回仓库根目录，并重新设置上述两个环境变量指向已经创建的目录。无需再次执行 `mkdir`。

报告中注明问题、输入位置/身份、科学协议与保存政策、执行命令/步骤、使用本指导的固定 commit 和路径。指导或分析脚本有影响计算的未提交修改时，保存该部分内容或 patch；无需复制全部规划和环境。新模型实验使用 `research/runs/`；本页分析不替代正式预测材料。未被忽略不等于已入库或备份。

## 3. 先算五个朴素基线并审计节点构成

以下一次性诊断不导入图模型。它按规范节点键排序，核对月份、节点身份和数值，采用当前修复版的 `19 / 1 / 4` 窗口划分，输出验证和测试指标。运行前需已设置第 2 节的输出目录。

```bash
python - <<'PY' | tee "$JOB_SDF_PHASE1_OUTPUT/naive-baselines.log"
import json
import platform
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

MONTHS = [f"{year}-{month:02d}" for year in (2021, 2022, 2023)
          for month in range(1, 13)]
CONTEXTS = {"r0": ["r0_id"], "region": ["region_id"]}
SPLITS = {"train": list(range(19)), "validation": [21],
          "test": list(range(24, 28))}
L, H = 6, 3
PROTOCOL = "P1-count-L6-H3-v3"

def metrics(pred, gold):
    error = pred.astype(np.float64) - gold.astype(np.float64)
    mse = float(np.square(error).mean())
    return {"MAE": float(np.abs(error).mean()), "MSE": mse,
            "RMSE": float(np.sqrt(mse))}

print(json.dumps({"machine": platform.machine(), "system": platform.system(),
                  "numpy": np.__version__, "pandas": pd.__version__,
                  "protocol": PROTOCOL}))
reference_skills = None
for name, context in CONTEXTS.items():
    started = time.perf_counter()
    frame = pd.read_parquet(Path("dataset/demand") / f"{name}.parquet")
    keys = context + ["skill_id"]
    assert all(column in frame for column in keys + MONTHS)
    actual_months = sorted(column for column in frame if column[:4].isdigit())
    assert actual_months == MONTHS, (name, actual_months)
    assert not frame.duplicated(keys).any(), f"{name}: duplicate node identity"
    ids = frame[keys].to_numpy(dtype=np.float64)
    assert np.isfinite(ids).all() and np.equal(ids, np.floor(ids)).all()
    frame = frame.sort_values(keys, kind="stable").reset_index(drop=True)
    signal = frame[MONTHS].to_numpy(dtype=np.float32)
    assert signal.shape[1] == 36 and signal.shape[0] > 0
    assert np.isfinite(signal).all() and (signal >= 0).all()
    skills = sorted(frame["skill_id"].unique().tolist())
    if reference_skills is not None:
        assert skills == reference_skills, f"{name}: skill set differs from r0"
    reference_skills = skills
    context_counts = {key: int(frame[key].nunique()) for key in context}
    joint_contexts = len(frame[context].drop_duplicates())
    expected_nodes = joint_contexts * len(skills)
    activity = (signal[:, :27] > 0).mean(axis=1)
    groups = {
        "inactive": activity == 0,
        "low": (activity > 0) & (activity <= 1 / 3),
        "medium": (activity > 1 / 3) & (activity <= 2 / 3),
        "high": activity > 2 / 3,
    }
    assert np.stack(list(groups.values())).sum(axis=0).tolist() == [1] * len(frame)
    train_mean = signal[:, :27].mean(axis=1, keepdims=True)
    print(json.dumps({"dataset": name, "skill_id_nunique": len(skills),
                      "context_id_counts": context_counts,
                      "joint_contexts": joint_contexts,
                      "context_cartesian_size": math.prod(context_counts.values()),
                      "expected_context_skill_nodes": expected_nodes,
                      "is_complete_context_skill_grid": len(frame) == expected_nodes,
                      "train_observation_months": MONTHS[:27],
                      "train_all_zero_fraction": float((activity == 0).mean()),
                      "full_36_month_all_zero_fraction_diagnostic_only":
                          float((signal == 0).all(axis=1).mean()),
                      "activity_group_counts": {k: int(v.sum()) for k, v in groups.items()}},
                     sort_keys=True))

    target_sets = {
        split: {MONTHS[k] for start in starts
                for k in range(start + L, start + L + H)}
        for split, starts in SPLITS.items()
    }
    assert target_sets["train"].isdisjoint(target_sets["validation"])
    assert target_sets["train"].isdisjoint(target_sets["test"])
    assert target_sets["validation"].isdisjoint(target_sets["test"])
    print(json.dumps({"dataset": name, "mode": "count", "nodes": len(frame),
                      "split_windows": SPLITS,
                      "target_months": {k: sorted(v) for k, v in target_sets.items()}},
                     sort_keys=True))

    validation_mse = {}
    for split in ("validation", "test"):
        starts = SPLITS[split]
        x = np.stack([signal[:, s:s + L] for s in starts])
        gold = np.stack([signal[:, s + L:s + L + H] for s in starts])
        predictions = {
            "Zero": np.zeros_like(gold),
            "LastValue": np.repeat(x[:, :, -1:], H, axis=2),
            "WindowMean6": np.repeat(x.mean(axis=2, keepdims=True), H, axis=2),
            "TrainMean27": np.broadcast_to(train_mean[None, :, :], gold.shape),
            "SeasonalNaive12": np.stack([signal[:, s + L - 12:s + L + H - 12]
                                         for s in starts]),
        }
        for model, pred in predictions.items():
            assert pred.shape == gold.shape
            group_metrics = {
                key: {"nodes": int(mask.sum()),
                      **metrics(pred[:, mask, :], gold[:, mask, :])}
                for key, mask in groups.items() if mask.any()
            }
            balanced_mae = float(np.mean([row["MAE"] for row in group_metrics.values()]))
            windows = [
                {"forecast_origin": MONTHS[s + L - 1],
                 "target_months": MONTHS[s + L:s + L + H],
                 **metrics(pred[i], gold[i])}
                for i, s in enumerate(starts)
            ]
            horizons = {f"h{h + 1}": metrics(pred[:, :, h], gold[:, :, h])
                        for h in range(H)}
            print(json.dumps({"dataset": name, "split": split, "model": model,
                              **metrics(pred, gold), "windows": windows,
                              "horizons": horizons, "activity_groups": group_metrics,
                              "balanced_activity_group_MAE": balanced_mae}, sort_keys=True))
            if split == "validation":
                validation_mse[model] = metrics(pred, gold)["MSE"]
        if split == "validation":
            order = list(predictions)
            choose = lambda names: min(names, key=lambda key: (validation_mse[key], order.index(key)))
            print(json.dumps({"dataset": name, "reference_selection": "validation MSE",
                              "NaiveRef": choose(order),
                              "NaiveRef6": choose([key for key in order if key != "SeasonalNaive12"]),
                              "SeasonalNaive12_information_budget": "extra 12-month history"},
                             sort_keys=True))
    print(json.dumps({"dataset": name,
                      "elapsed_seconds": time.perf_counter() - started}))
PY
```

检查输出：

- `r0` 预计 2,335 节点，`region` 预计 16,345 节点；若不同，先核对数据版本。
- 检查真实技能数、上下文数和 `is_complete_context_skill_grid`；全零比例需读输出，不能由行数倍数推测。
- 验证目标是 2023-04 至 2023-06，测试目标是 2023-07 至 2023-12。
- 四个测试窗口分别从 2023-07、08、09、10 开始预测未来 3 月。
- 所有指标有限，基线无需训练或随机初始化。

TrainMean27 使用固定的 2021-01 至 2023-03 均值；SeasonalNaive12 对每个目标月读取去年同月，属于额外历史参照。NaiveRef 与 NaiveRef6 的选择仅依赖验证 MSE，分别对应实用门槛和 6 月输入预算的参照。分组仅使用训练 27 月；完整 36 月全零率仅作描述。

这一轮报告所有预定基线，不根据测试排名临时添加大量规则。整体 RMSE 是平均平方误差的平方根，不是四个窗口 RMSE 的均值。

## 4. 核对图的身份、覆盖与权重

此脚本读取原始图，不生成图 JSON。它按正确上下文检查端点，并计算不含自环的邻居覆盖。它统计的是精确行重复次数，不是广告共现频率。

```bash
python - <<'PY' | tee "$JOB_SDF_PHASE1_OUTPUT/graph-audit.log"
import json
from pathlib import Path

import pandas as pd

CONTEXTS = {"r0": ["r0_id"], "region": ["region_id"]}
for name, context in CONTEXTS.items():
    data = pd.read_parquet(Path("dataset/demand") / f"{name}.parquet")
    graph = pd.read_parquet(Path("dataset/graph") / f"{name}.parquet")
    keys = context + ["skill_id"]
    edge_keys = context + ["row_id", "col_id"]
    assert all(column in graph for column in edge_keys)
    assert not graph[edge_keys].isna().any().any()
    assert not data[keys].isna().any().any()
    assert not data.duplicated(keys).any()
    node_index = pd.MultiIndex.from_frame(data[keys])

    def endpoints(rows):
        source = rows[context + ["row_id"]].rename(columns={"row_id": "skill_id"})
        target = rows[context + ["col_id"]].rename(columns={"col_id": "skill_id"})
        return pd.concat([source, target], ignore_index=True).drop_duplicates()

    all_endpoints = pd.MultiIndex.from_frame(endpoints(graph)[keys])
    unmatched = int((~all_endpoints.isin(node_index)).sum())
    assert unmatched == 0, (name, "unmatched graph endpoints", unmatched)
    counts = graph.groupby(edge_keys, sort=False).size()
    neighbor_rows = graph.loc[graph["row_id"] != graph["col_id"]]
    covered = len(endpoints(neighbor_rows))
    multiplicity = {str(int(weight)): int(number)
                    for weight, number in counts.value_counts().sort_index().items()}
    result = {
        "dataset": name, "graph_columns": list(graph.columns),
        "task_nodes": len(data), "directed_source_rows": len(graph),
        "unique_context_directed_edges": len(counts),
        "exact_duplicate_rows": len(graph) - len(counts),
        "source_self_loop_rows": int((graph["row_id"] == graph["col_id"]).sum()),
        "nodes_with_nonself_neighbors": covered,
        "isolated_task_nodes": len(data) - covered,
        "neighbor_coverage": covered / len(data),
        "exact_multiplicity_distribution": multiplicity,
        "has_named_frequency_column": any(c.lower() in ("weight", "frequency", "freq")
                                          for c in graph.columns),
    }
    print(json.dumps(result, sort_keys=True))
PY
```

重点读三个字段：

| 字段 | 后续决策 |
| --- | --- |
| `exact_multiplicity_distribution` | 若只有权重 1，不能直接按发布频率筛选强边 |
| `neighbor_coverage` | 判断图只作用于少量节点，还是覆盖大部分预测任务 |
| `isolated_task_nodes` | 后续分别报告无邻居与有邻居节点，避免图收益被混淆 |

若端点断言失败，先调查 ID 映射和数据版本。后续边过滤按“过滤弱边、保留强边”的方向设计；这里先确认边分数能否区分强弱。若发现权重解释不同，先修正分数的定义，再研究可学习阈值或软门控。

## 5. 有条件时核对归档预测

### 5.1 PyTorch 只用于读取已有张量

在已有 PyTorch 环境中可以直接执行。若使用新建的 Mac CPU 环境，可选安装：

```bash
python -m pip install --no-cache-dir torch==2.3.1
python -c 'import torch; print(torch.__version__)'
python -c 'import torch; print(torch.__version__)'
```

这里只读取张量，不需要 `torch_geometric_temporal`，也不试图用这个环境重训旧 GPU 实验。第 3、4 节不依赖这一步，安装未完成时可以先完成它们。

### 5.2 重算并对齐同一测试任务

```bash
python - <<'PY' | tee "$JOB_SDF_PHASE1_OUTPUT/archive-comparison.log"
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

MONTHS = [f"{year}-{month:02d}" for year in (2021, 2022, 2023)
          for month in range(1, 13)]
frame = pd.read_parquet("dataset/demand/region.parquet")
assert not frame.duplicated(["region_id", "skill_id"]).any()
frame = frame.sort_values(["region_id", "skill_id"], kind="stable")
signal = frame[MONTHS].to_numpy(dtype=np.float32)
assert signal.shape == (16345, 36)
assert np.isfinite(signal).all()
starts = list(range(24, 28))
expected = np.stack([signal[:, s + 6:s + 9] for s in starts])
last_value = np.stack([np.repeat(signal[:, s + 5:s + 6], 3, axis=1)
                       for s in starts])
root = Path("experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/"
            "results/count/region/EvolveGCNH")

def load(path):
    with path.open("rb") as handle:
        tensor = torch.load(handle, map_location="cpu", weights_only=True)
    assert isinstance(tensor, torch.Tensor) and torch.isfinite(tensor).all()
    return tensor.detach().cpu().numpy()

def metrics(pred, gold):
    error = pred.astype(np.float64) - gold.astype(np.float64)
    return {"MAE": float(np.abs(error).mean()),
            "RMSE": float(np.sqrt(np.square(error).mean()))}

reference = None
for seed in (0, 1):
    folder = root / str(seed)
    assert len(list(folder.glob("pred_*.pt"))) == 4
    assert len(list(folder.glob("gold_*.pt"))) == 4
    pred = np.stack([load(folder / f"pred_{i}.pt") for i in range(4)])
    gold = np.stack([load(folder / f"gold_{i}.pt") for i in range(4)])
    assert pred.shape == gold.shape == expected.shape
    assert np.array_equal(gold, expected), f"seed {seed}: raw-data label mismatch"
    if reference is not None:
        assert np.array_equal(reference, gold), "seeds have different labels"
    reference = gold
    recorded = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
    recalculated = metrics(pred, gold)
    for key in ("MAE", "RMSE"):
        assert abs(recalculated[key] - recorded[key]) < 0.01, (seed, key)
    print(json.dumps({"seed": seed, "recorded": recorded,
                      "recalculated": recalculated,
                      "last_value": metrics(last_value, gold),
                      "negative_prediction_fraction": float((pred < 0).mean()),
                      "horizons": {f"h{h + 1}": metrics(pred[:, :, h], gold[:, :, h])
                                   for h in range(3)}}, sort_keys=True))
    for i, start in enumerate(starts):
        print(json.dumps({"seed": seed, "window": i,
                          "target_months": MONTHS[start + 6:start + 9],
                          "model": metrics(pred[i], gold[i]),
                          "last_value": metrics(last_value[i], gold[i])}, sort_keys=True))
print("Both seeds match canonical raw-data test labels.")
PY
```

这里使用 float64 重算，与原实验 float32 聚合允许小数值差异，所以核对容差为 0.01。这个容差用于核对保存指标，不是今后认定模型改善的阈值。

若断言失败，先查节点顺序、数据版本、窗口定义和文件完整性，不急着解释模型性能。若断言通过，才把归档结果与第 3 节基线放在同一张表里。

## 6. 读完日志后怎么决定

| 观察 | 立即行动 |
| --- | --- |
| 标签或重算指标不一致 | 暂停新训练，修复比较口径 |
| 图的边权几乎相同 | 暂缓发布频率阈值方案，先定义可检验的边分数 |
| 图覆盖很低 | 在后续实验中单列有邻居、无邻居节点，并保留自身分支 |
| 朴素基线已优于部分 EvolveGCN-H 运行 | 先建立共享 Ridge，再诊断尺度、优化与递归状态 |
| seed 0/1 差距大，但原运行未做同 seed 复跑 | 先准备受控复跑，不把差距直接解释为初始化方差 |
| 无图 baseline 稳定且图数据清楚 | 开始实现静态图对照，检验真实图是否带来额外收益 |

即使修复版弱于简单方法，科研也不需要停止；需要调整的是证据与方法顺序。模型修复的正确性、预测能力和新模块贡献是三个不同问题。

## 7. 当前可复用 baseline 入口

`benchmark.nograph_baseline` 已实现不依赖 PyG/PyTorch 的规范读取、五项朴素基线及共享 Ridge，T004 已研究侧验收。默认路径只需 NumPy、pandas、PyArrow；科学定义见[协议](protocol.md)。准确命令和可选参数见 [README](../../../README.md#45-graph-free-cpu-baseline-benchmarknograph_baseline)。

```bash
python -m benchmark.nograph_baseline --help
python -m benchmark.nograph_baseline run --data-name r0 --mode count --seed 0 --run-id p01-r0-NEW-ID
```

模型调用必须使用新的 run ID。此命令会执行模型，仅在相应实验已授权时运行。两组现有正式结果见[索引](../../archives/index.md#t004-baseline-运行2026-10-07)；数组已清理时，在独立空目录从包展开，不能对仅有可读入口的 run 目录直接重算。

记录减负已由 [T010 独立 PASS](../../../openspec/changes/archive/2026-10-08-reduce-baseline-evidence-overhead/verification.md)及 [D011 研究侧验收](../../decisions.md#d011-t010-记录减负研究侧验收)完成。模型默认 `--purpose formal`，临时开发显式使用 `--purpose development`（输出在忽略的 `scratch/nograph-baseline/`）；默认只保存被选模型与完整候选验证分数，研究需要完整候选数组时使用 `--retain-candidates`。已提交源码/协议用固定 commit 与路径定位，相关脏内容保存可恢复材料。

`recompute`、`compare`、`align-v2` 使用 `--report PATH` 生成一份不覆盖已有文件的 JSON 报告，返回 `report_path`；模型仍返回 `run_dir`。旧检查 `--run-id ID`/`--runs-root ROOT` 是单份 `<ROOT>/<ID>.json` 报告的兼容别名，默认报告根为 `research/reports/nograph-baseline/`，不再产生完整 check run。不能同时给 `--report` 和旧 run ID，报告路径不能在输入 run 内。以按需展开的旧包为输入也支持：

```bash
python -m benchmark.nograph_baseline recompute \
    --run-dir "$P01_RESTORE_DIR/p01-r0-sharedridge-002" \
    --report research/reports/nograph-baseline/p01-r0-recompute-NEW-ID.json
```

`P01_RESTORE_DIR` 的按需展开方法见[索引](../../archives/index.md#内容身份与恢复限制)。仅有可读入口的原目录不含数组，不能直接重算；报告保留输入执行身份、来源、命令、容差和结果/失败信息，不改输入、不重训。

科研接续按计划准备 `r2/count` 扩展，再做训练期内部回测；不把多个重叠窗口当作独立实验。旧图 CLI 不支持 `--model_name Ridge` 或 `--learning_rate ...`。

## 8. 什么时候恢复 GPU 实验

当归档比较已对齐，且决定需要回答 EvolveGCN-H 的重复性问题时，准备 T005 的受控复跑。原结果提交为 `950a1d8febbf992b8bda061d35f03107d0b18478`，GPU 为 Tesla T4，环境名为 `job-sdf`。优先保留原机器/环境；新机器需从历史日志核对依赖和设备，不能仅凭环境名认定条件相同。旧指南的前篇环境安装文档未入库，不能依赖其中缺失链接重建环境。

在独立仓库检出原提交，训练前确认代码、CUDA 和确定性条件；以下只是准备命令，不启动训练：

```bash
conda activate job-sdf
git rev-parse HEAD
python -c 'import torch; print(torch.__version__, torch.cuda.is_available())'
export CUBLAS_WORKSPACE_CONFIG=:4096:8
```

需要注意该指南的原结果默认目录与当前归档位置不同。在保存有这些归档文件的机器上设置：

```bash
export EVOLVEGCN_ORIGINAL_ROOT="$(pwd)/experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/results/count/region/EvolveGCNH"
```

归档目录需要同步到服务器后才能在那里使用；不要假定本机路径在服务器上存在。缺少生成数据时，只准备 `region/count`，先核对保存 gold 与任务标签、重算原指标并对齐 LastValue；不要为准备复跑生成全部 14 组数据。

复跑 seed 1 保持 L=6、H=3、500 epoch，使用新输出目录并拒绝覆盖。旧 CLI 按模式/粒度/模型/seed 决定默认路径，直接重跑会覆盖结果；应通过训练函数显式指定独立 `results_dir`。原提交下的训练及比较示例保留于[历史指南 §3](../../archives/legacy-development/GPU_SERVER_EVOLVEGCN_NEXT_STEPS_GUIDE.md#3-在独立目录复跑-seed-1)，读取原结果时使用上面的归档路径。实际执行仍需该实验的授权，并按当前协议保存来源、条件、预测/标签、参数、选模与日志，不照搬旧指南的默认打包收尾。

同 seed 的近似重复结果先核对成功，再决定是否补其他 seed。比较逐窗口预测最大差、标签一致性与总体指标，微小浮点差不直接等同于失败；明显差异先核对源码、数据、依赖、GPU 与确定性设置。同设备条件无法恢复时，明确记录差异，将新实验作为新环境结果。状态预热、输入归一化和学习率调整另建实验，不覆盖原始结果。

## 9. 第一轮结束时留下什么

第 3 至 5 节分析保留 `summary.md`、实际执行的日志和必要输入身份。摘要写明问题、脚本/指导来源、命令与步骤、成功/失败/中断状态、关键结果、容差和限制；使用可定位的已提交脚本时不另存全套源码/协议/环境。独立科学分析保留计算过程与表/图，普通指标检查保留简洁报告。

实际模型实验、改变条件的受控诊断和时间回测按[协议 §6.1](protocol.md#61-实验记录与产物保存)保留完整预测、标签、身份、分组、被选参数与选模记录。不同执行条件单独命名，原始 run 和封存内容不覆盖。

没有默认的“全量包 → 哈希清单 → commit/push → 恢复演练”流水线。需要打包时先确认没有写入进程并使用新路径，声明排除项；Git 内包由提交定位内容，Git 外包保存包外 SHA256。保存位置和已知提交/备份事实记在[外部索引](../../archives/index.md)，不回写包内摘要。Git、备份与恢复核验按具体授权执行。

结束时记录三个判断：验证选定的便宜方法能提供怎样的参照；发布图能支持怎样的权重解释；旧 EvolveGCN-H 结果是否与当前任务标签一致。按协议第 6 节解释结果，不按测试排名更换参照；更新阶段计划与 state。

T004 已完成，后续实验范围以阶段计划和具体授权为准。
