# 第一阶段执行指导：诊断与 baseline 操作

编写日期：2026-10-06。

这份指导落实[实验协议](protocol.md)。研究方向见[路线图](../../roadmap.md)，当前任务见[阶段计划](plan.md)，下一动作见[当前状态](../../state.md)。首轮第 3 至 5 节诊断已完成，开发从第 7 节接续；重跑诊断使用新 run ID。

协议以 `protocol.md` 第 3 至 6 节的 `P1-count-L6-H3-v3` 为唯一来源。v3 仅改变记录布局，科学计算与 v2 一致。下面的命令没有在本次迁移中执行。

## 1. 这一轮只要做成什么

先完成下面三个结果：

1. `r0/count` 和 `region/count` 的五项朴素基线、技能/上下文网格审计，以及预定活跃度分层结果。
2. 按正确上下文统计图覆盖与重复次数，确认原来的边权解释是否适用。
3. 有 PyTorch 环境时，核对归档 EvolveGCN-H 的标签、指标和逐窗口误差。

前两项可以在 Mac 上用 CPU 完成，不需要 PyG、图预处理 JSON 或 GPU。第三项只读现有张量，不训练模型。先不要补新 seed、改 GCN 层数或加入门控。

这轮得到的是诊断日志。共享 Ridge 的可复用入口、完整预测保存和后续模型改造仍是待实现工作。

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

共享 Ridge 实现阶段再加入 sklearn；归档张量核对需要 PyTorch，见第 5 节。若下载失败先处理网络或软件源，不能把安装失败解释为模型不能在 Mac 上运行。

### 2.3 创建独立诊断目录

以下块启用遇错停止和管道错误检测。目录已经存在时会停止；重新开始请更换 `JOB_SDF_PHASE1_RUN_ID`，不要覆盖此前记录。

```bash
set -e
set -o pipefail
export JOB_SDF_PHASE1_RUN_ID=phase1-20261006-v3-01
export JOB_SDF_PHASE1_OUTPUT="research/runs/${JOB_SDF_PHASE1_RUN_ID}"
mkdir -p research/runs
mkdir "$JOB_SDF_PHASE1_OUTPUT"
cp research/phases/P01/protocol.md "$JOB_SDF_PHASE1_OUTPUT/protocol.md"
cp research/phases/P01/execution-guide.md "$JOB_SDF_PHASE1_OUTPUT/execution-guide.md"
git rev-parse HEAD > "$JOB_SDF_PHASE1_OUTPUT/git-commit.txt"
git status --short > "$JOB_SDF_PHASE1_OUTPUT/git-status.txt"
git diff HEAD -- research > "$JOB_SDF_PHASE1_OUTPUT/planning-diff.patch"
python -m pip freeze > "$JOB_SDF_PHASE1_OUTPUT/environment.txt"
shasum -a 256 dataset/demand/r0.parquet dataset/demand/region.parquet dataset/graph/r0.parquet dataset/graph/region.parquet > "$JOB_SDF_PHASE1_OUTPUT/source-sha256.txt"
shasum -a 256 "$JOB_SDF_PHASE1_OUTPUT/protocol.md" "$JOB_SDF_PHASE1_OUTPUT/execution-guide.md" > "$JOB_SDF_PHASE1_OUTPUT/planning-sha256.txt"
```

重新打开终端后，激活环境、返回仓库根目录，并重新设置上述两个环境变量指向已经创建的目录。无需再次执行 `mkdir`。

旧图 CLI 的 `benchmark/graph_method/results/` 被 Git 忽略，新运行使用 `research/runs/`。正式入口还需保存 provenance、实际命令/脚本和输入/输出身份；本页一次性诊断不代替该入口。未被忽略不等于已入库或备份。

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
python -m pip freeze > "$JOB_SDF_PHASE1_OUTPUT/environment-after-torch.txt"
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

## 7. 再下一步：开发一个可复用的轻量 baseline 入口

上面的诊断通过后，再提出第一项实现工作。建议范围仅包含：

- 不依赖 PyG 的规范数据读取、节点身份和时间划分。
- 五种朴素基线及验证选定的参照，与[协议定义的共享 Ridge](protocol.md#52-共享-ridge主要的稳定学习参照)。
- 验证选 lambda、训练期标准化、原始单位评估。
- 独立结果目录、预测与标签保存、协议快照与数据校验和、预定活跃度组及等权组指标、耗时和归档。
- 关键协议检查：目标月不跨划分、标签对齐、标准化只拟合训练期、指标可重算、重复运行结果一致。

当前仓库没有这个入口。不要执行 `--model_name Ridge` 或 `--learning_rate ...`，当前图 CLI 不支持它们。后续可以创建一个范围明确的 OpenSpec change，再实现和验证；本次只创建规划文档。

正式入口完成后，把 `r2/count` 加入同一流程。随后再做训练期内部回测，检查主 baseline 对不同时间起点是否稳定；不把多个重叠窗口当成独立实验。

## 8. 什么时候恢复 GPU 实验

当归档比较已对齐，且决定需要回答 EvolveGCN-H 的重复性问题时，参照[原下一轮 GPU 指南](../../../guides/(2)GPU_SERVER_EVOLVEGCN_NEXT_STEPS_GUIDE.md)第 3 节。

需要注意该指南的原结果默认目录与当前归档位置不同。在保存有这些归档文件的机器上设置：

```bash
export EVOLVEGCN_ORIGINAL_ROOT="$(pwd)/experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/results/count/region/EvolveGCNH"
```

复跑训练应使用原提交 `950a1d8febbf992b8bda061d35f03107d0b18478` 的独立仓库、原条件和新输出目录。归档目录需要同步到服务器后才能在那里使用；不要假定本机路径在服务器上存在。

同 seed 的近似重复结果先核对成功，再补其他 seed。同设备条件无法恢复时，明确记录差异，将新实验作为新环境结果。状态预热、输入归一化和学习率调整另建实验，不覆盖原始结果。

## 9. 第一轮结束时留下什么

本轮独立目录应包含：协议与操作指导快照、`git-commit.txt`、`git-status.txt`、`planning-diff.patch`、`environment.txt`、`source-sha256.txt`、`planning-sha256.txt`、`naive-baselines.log`、`graph-audit.log`。执行第 5 节后另外有 `environment-after-torch.txt` 和 `archive-comparison.log`。

先在运行目录写入 `summary.md`，记录协议版本、成功/失败/中断状态、完成步骤及未完成项。失败日志同样保留；成功运行需明确技能/上下文与全零率、验证选定的两项参照、图覆盖及归档比较是否通过。

小规模第一阶段使用全量包和校验文件入库，打包前停止往运行目录写入。下面会拒绝覆盖同名归档：

```bash
export JOB_SDF_PHASE1_ARCHIVE="research/archives/${JOB_SDF_PHASE1_RUN_ID}.tar.gz"
mkdir -p research/archives
python - <<'PY'
import os
from pathlib import Path

output = Path(os.environ["JOB_SDF_PHASE1_OUTPUT"])
archive = Path(os.environ["JOB_SDF_PHASE1_ARCHIVE"])
assert output.is_dir() and (output / "summary.md").is_file()
assert output == Path("research/runs") / os.environ["JOB_SDF_PHASE1_RUN_ID"]
assert not archive.exists() and not Path(str(archive) + ".sha256").exists()
PY
shasum -a 256 -c "$JOB_SDF_PHASE1_OUTPUT/source-sha256.txt"
shasum -a 256 -c "$JOB_SDF_PHASE1_OUTPUT/planning-sha256.txt"
COPYFILE_DISABLE=1 tar -czf "$JOB_SDF_PHASE1_ARCHIVE" -C research/runs "$JOB_SDF_PHASE1_RUN_ID"
tar -tzf "$JOB_SDF_PHASE1_ARCHIVE"
shasum -a 256 "$JOB_SDF_PHASE1_ARCHIVE" > "${JOB_SDF_PHASE1_ARCHIVE}.sha256"
shasum -a 256 -c "${JOB_SDF_PHASE1_ARCHIVE}.sha256"
git add -- "$JOB_SDF_PHASE1_ARCHIVE" "${JOB_SDF_PHASE1_ARCHIVE}.sha256"
git diff --cached --stat -- "$JOB_SDF_PHASE1_ARCHIVE" "${JOB_SDF_PHASE1_ARCHIVE}.sha256"
git commit -m "Archive ${JOB_SDF_PHASE1_RUN_ID}" -- "$JOB_SDF_PHASE1_ARCHIVE" "${JOB_SDF_PHASE1_ARCHIVE}.sha256"
```

这些是后续操作，本次迁移不运行它们。封存前确认没有写入进程，commit/push 按当时授权执行。包的入库 commit、备份位置和核验时间写在[外部索引](../../archives/index.md)，不为此改写摘要。解包核验使用新的临时目录，避免覆盖现有运行。取回后使用运行内快照；正式实验还需保存预测、标签、参数和 provenance。

结束时记录三个判断：验证选定的便宜方法能提供怎样的参照；发布图能支持怎样的权重解释；旧 EvolveGCN-H 结果是否与当前任务标签一致。按协议第 6 节解释结果，不按测试排名更换参照；更新阶段计划与 state。

完成这些后，项目就有了进入共享 Ridge 实现和图收益验证的具体起点。此时仍不需要扩大到所有模型或所有粒度。
