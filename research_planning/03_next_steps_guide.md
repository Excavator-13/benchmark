# 当前下一步操作指导：先取得可核对的基础证据

编写日期：2026-10-06。

这份指导落实[第一阶段规划](02_phase_one_plan.md)的最先几步。科研全貌见[路线图](01_research_roadmap.md)。以下命令供后续执行；本次文档编写没有安装依赖、运行数据诊断或训练模型。

## 1. 这一轮只要做成什么

先完成下面三个结果：

1. `r0/count` 和 `region/count` 的 Zero、LastValue、WindowMean6 基线。
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

已有满足依赖的环境可以直接使用。否则建议新建轻量环境，避免修改旧训练环境：

```bash
conda create -n job-sdf-baseline python=3.11
conda activate job-sdf-baseline
python -m pip install numpy==1.26.4 pandas==2.2.3 pyarrow==17.0.0
python -c 'import sys, numpy, pandas, pyarrow; print(sys.executable); print(numpy.__version__, pandas.__version__, pyarrow.__version__)'
```

这些是新诊断环境的建议版本，不是旧 GPU 实验的环境复现。暂不安装仓库整个 `requirements.txt`，其中的 CUDA wheel、DGL 和图扩展不是本轮基线所需。

共享 Ridge 实现阶段再加入 sklearn；归档张量核对需要 PyTorch，见第 5 节。若下载失败先处理网络或软件源，不能把安装失败解释为模型不能在 Mac 上运行。

### 2.3 创建独立诊断目录

以下块启用遇错停止和管道错误检测。目录已经存在时会停止；重新开始请更换 `JOB_SDF_PHASE1_RUN_ID`，不要覆盖此前记录。

```bash
set -e
set -o pipefail
export JOB_SDF_PHASE1_RUN_ID=phase1-20261006-01
export JOB_SDF_PHASE1_OUTPUT="benchmark/graph_method/results/phase1/${JOB_SDF_PHASE1_RUN_ID}"
mkdir -p benchmark/graph_method/results/phase1
mkdir "$JOB_SDF_PHASE1_OUTPUT"
git rev-parse HEAD > "$JOB_SDF_PHASE1_OUTPUT/git-commit.txt"
git status --short > "$JOB_SDF_PHASE1_OUTPUT/git-status.txt"
python -m pip freeze > "$JOB_SDF_PHASE1_OUTPUT/environment.txt"
shasum -a 256 dataset/demand/r0.parquet dataset/demand/region.parquet dataset/graph/r0.parquet dataset/graph/region.parquet > "$JOB_SDF_PHASE1_OUTPUT/source-sha256.txt"
```

重新打开终端后，激活环境、返回仓库根目录，并重新设置上述两个环境变量指向已经创建的目录。无需再次执行 `mkdir`。

## 3. 先算三个朴素基线

以下一次性诊断不导入图模型。它按规范节点键排序，核对月份、节点身份和数值，采用当前修复版的 `19 / 1 / 4` 窗口划分，输出验证和测试指标。运行前需已设置第 2 节的输出目录。

```bash
python - <<'PY' | tee "$JOB_SDF_PHASE1_OUTPUT/naive-baselines.log"
import json
import platform
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

def metrics(pred, gold):
    error = pred.astype(np.float64) - gold.astype(np.float64)
    return {"MAE": float(np.abs(error).mean()),
            "RMSE": float(np.sqrt(np.square(error).mean()))}

print(json.dumps({"machine": platform.machine(), "system": platform.system(),
                  "numpy": np.__version__, "pandas": pd.__version__}))
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

    for split in ("validation", "test"):
        starts = SPLITS[split]
        x = np.stack([signal[:, s:s + L] for s in starts])
        gold = np.stack([signal[:, s + L:s + L + H] for s in starts])
        predictions = {
            "Zero": np.zeros_like(gold),
            "LastValue": np.repeat(x[:, :, -1:], H, axis=2),
            "WindowMean6": np.repeat(x.mean(axis=2, keepdims=True), H, axis=2),
        }
        for model, pred in predictions.items():
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
                              "horizons": horizons}, sort_keys=True))
    print(json.dumps({"dataset": name,
                      "elapsed_seconds": time.perf_counter() - started}))
PY
```

检查输出：

- `r0` 预计 2,335 节点，`region` 预计 16,345 节点；若不同，先核对数据版本。
- 验证目标是 2023-04 至 2023-06，测试目标是 2023-07 至 2023-12。
- 四个测试窗口分别从 2023-07、08、09、10 开始预测未来 3 月。
- 所有指标有限，基线无需训练或随机初始化。

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

若端点断言失败，先调查 ID 映射和数据版本。若发现权重解释不同，更新研究假设，不直接开始学习原设想的阈值。

## 5. 有条件时核对归档预测

### 5.1 PyTorch 只用于读取已有张量

在已有 PyTorch 环境中可以直接执行。若使用新建的 Mac CPU 环境，可选安装：

```bash
python -m pip install torch==2.3.1
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
- 三种朴素基线与[第二份文档定义的共享 Ridge](02_phase_one_plan.md#52-共享-ridge主要的稳定学习参照)。
- 验证选 lambda、训练期标准化、原始单位评估。
- 独立结果目录、预测与标签保存、配置与数据校验和、分组指标和耗时。
- 关键协议检查：目标月不跨划分、标签对齐、标准化只拟合训练期、指标可重算、重复运行结果一致。

当前仓库没有这个入口。不要执行 `--model_name Ridge` 或 `--learning_rate ...`，当前图 CLI 不支持它们。后续可以创建一个范围明确的 OpenSpec change，再实现和验证；本次只创建规划文档。

正式入口完成后，把 `r2/count` 加入同一流程。随后再做训练期内部回测，检查主 baseline 对不同时间起点是否稳定；不把多个重叠窗口当成独立实验。

## 8. 什么时候恢复 GPU 实验

当归档比较已对齐，且决定需要回答 EvolveGCN-H 的重复性问题时，参照[原下一轮 GPU 指南](../guides/(2)GPU_SERVER_EVOLVEGCN_NEXT_STEPS_GUIDE.md)第 3 节。

需要注意该指南的原结果默认目录与当前归档位置不同。在保存有这些归档文件的机器上设置：

```bash
export EVOLVEGCN_ORIGINAL_ROOT="$(pwd)/experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/results/count/region/EvolveGCNH"
```

复跑训练应使用原提交 `950a1d8febbf992b8bda061d35f03107d0b18478` 的独立仓库、原条件和新输出目录。归档目录需要同步到服务器后才能在那里使用；不要假定本机路径在服务器上存在。

同 seed 的近似重复结果先核对成功，再补其他 seed。同设备条件无法恢复时，明确记录差异，将新实验作为新环境结果。状态预热、输入归一化和学习率调整另建实验，不覆盖原始结果。

## 9. 第一轮结束时留下什么

本轮独立目录应包含：`git-commit.txt`、`git-status.txt`、`environment.txt`、`source-sha256.txt`、`naive-baselines.log`、`graph-audit.log`。执行第 5 节后另外有 `environment-after-torch.txt` 和 `archive-comparison.log`。

结束时记录三个判断：哪种便宜方法提供了可用参照；发布图能支持怎样的权重解释；旧 EvolveGCN-H 结果是否与当前任务标签一致。记录未完成项，不用结论填补缺失实验。

完成这些后，项目就有了进入共享 Ridge 实现和图收益验证的具体起点。此时仍不需要扩大到所有模型或所有粒度。
