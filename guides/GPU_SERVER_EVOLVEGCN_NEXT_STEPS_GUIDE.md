# EvolveGCN-H `region/count` 结果诊断与下一轮实验

本指南接续 [GPU_SERVER_EVOLVEGCN_GUIDE.md](GPU_SERVER_EVOLVEGCN_GUIDE.md)。先分析已完成的两次运行，再决定是否增加 seed 或调整实验。命令从仓库根目录执行；Python 命令使用上一份指南建立的 `job-sdf` 环境，不需要在本地电脑安装训练环境。

现有结果来自提交 `950a1d8febbf992b8bda061d35f03107d0b18478`。两个 seed 都完成了 500 epoch；指标如下：

| Seed | MAE | RMSE | 最佳验证 epoch |
|---|---:|---:|---:|
| 0 | 41.08 | 238.96 | 366 |
| 1 | 96.18 | 579.50 | 461 |

seed 1 的误差主要出现在前两个测试窗口。两次运行的 `gold_*.pt` 完全相同；接下来要分辨这是模型相对简单基线也表现不佳、同 seed 复跑不稳定，还是不同初始化导致的稳定差异。

## 1. 准备环境和原始结果

如果原 GPU 服务器还在，继续使用原仓库和环境。如果已经释放，按上一份指南的第 2 至 6 节建立环境，并在**新克隆的仓库**中检出记录的提交；不要把新版本代码与旧结果混在一次对照中。

```bash
cd ~/benchmark
conda activate job-sdf
git rev-parse HEAD
python -c 'import torch; print(torch.__version__, torch.cuda.is_available())'
```

提交应为 `950a1d8febbf992b8bda061d35f03107d0b18478`，PyTorch 应能看到 CUDA。

如果新克隆仓库的 HEAD 不同，在新克隆目录中执行以下命令后再次核对：

```bash
git switch --detach 950a1d8febbf992b8bda061d35f03107d0b18478
git rev-parse HEAD
```

开始训练和诊断前，在同一终端设置与第一次运行相同的条件：

```bash
export CUBLAS_WORKSPACE_CONFIG=:4096:8
mkdir -p diagnostics
```

确认两份旧结果都在默认路径：

```bash
ls benchmark/graph_method/results/count/region/EvolveGCNH/{0,1}/metrics.json
ls benchmark/graph_method/data/count/region.json
```

如果服务器上只有下载回来的结果包，先将它解压到独立目录，并指定原结果路径；不要覆盖仓库中的同名结果目录：

```bash
mkdir -p diagnostics/original-archive
tar -xzf evolvegcn-region-count-results.tar.gz -C diagnostics/original-archive
export EVOLVEGCN_ORIGINAL_ROOT=diagnostics/original-archive/benchmark/graph_method/results/count/region/EvolveGCNH
```

若使用已解压的 `evolvegcn-region-count-results/` 目录，则改用：

```bash
export EVOLVEGCN_ORIGINAL_ROOT=evolvegcn-region-count-results/benchmark/graph_method/results/count/region/EvolveGCNH
```

环境变量未设置时，下面的脚本读取仓库内的默认结果目录。如果缺少生成数据，只准备这一组，不必准备全部 14 组：

```bash
python benchmark/graph_method/prepare_graph_data.py --mode count --data_name region
```

## 2. 对齐标签并计算简单基线

这里的基线是：在每个预测起点，取输入窗口最后一个月的真实需求量，作为未来三个月的预测。它只用该起点已经可见的信息。每个测试窗口均有 16,345 个节点和 3 个预测步长；四个窗口的目标月份互相重叠，因此逐窗口数字应与总体数字一起看。

```bash
set -o pipefail
python - <<'PY' 2>&1 | tee diagnostics/analysis.txt
import json
import os
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path.cwd() / "benchmark/graph_method"))
import main

root = Path(os.environ.get(
    "EVOLVEGCN_ORIGINAL_ROOT",
    "benchmark/graph_method/results/count/region/EvolveGCNH",
))
config = main.ExperimentConfig(data_name="region", mode="count", window_size=6, pred_length=3)
_, _, test = main.temporal_signal_split(main.load_dataset(config))
snapshots = list(test)
assert len(snapshots) == 4, f"expected 4 test windows, got {len(snapshots)}"

def load_tensor(path):
    return torch.load(path, map_location="cpu", weights_only=True)

all_golds = []
for seed in (0, 1):
    folder = root / str(seed)
    recorded = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
    checkpoint = load_tensor(folder / "checkpoint.pt")
    assert checkpoint["seed"] == seed
    assert checkpoint["config"]["model_name"] == "EvolveGCNH"
    assert checkpoint["config"]["window_size"] == 6
    assert checkpoint["config"]["pred_length"] == 3

    predictions = []
    golds = []
    baseline = []
    print(f"\nseed {seed}, best validation MSE={checkpoint['best_val_loss'].item():.3f}")
    print("window  target start  model MAE  model RMSE  baseline MAE  baseline RMSE  pred mean  negative %")
    for i, snapshot in enumerate(snapshots):
        pred = load_tensor(folder / f"pred_{i}.pt")
        gold = load_tensor(folder / f"gold_{i}.pt")
        assert pred.shape == gold.shape == snapshot.y.shape
        assert torch.equal(gold, snapshot.y), f"seed {seed}, window {i}: saved gold differs from dataset"
        assert torch.isfinite(pred).all()
        last_value = snapshot.x[:, -1:].expand_as(gold).clone()
        predictions.append(pred)
        golds.append(gold)
        baseline.append(last_value)
        model_row = main.regression_metrics([pred], [gold])
        baseline_row = main.regression_metrics([last_value], [gold])
        print(f"{i:>6}  {['2023-07', '2023-08', '2023-09', '2023-10'][i]:>12}  "
              f"{model_row['MAE']:>9.2f}  {model_row['RMSE']:>10.2f}  "
              f"{baseline_row['MAE']:>12.2f}  {baseline_row['RMSE']:>13.2f}  "
              f"{pred.mean().item():>9.2f}  {(pred < 0).float().mean().item() * 100:>10.1f}")

    all_golds.append(golds)
    model_total = main.regression_metrics(predictions, golds)
    baseline_total = main.regression_metrics(baseline, golds)
    for key in ("MAE", "RMSE"):
        assert abs(model_total[key] - recorded[key]) < 0.01, (seed, key, model_total, recorded)
    print("model total:", model_total)
    print("last-month baseline total:", baseline_total)
    for horizon in range(3):
        model_mae = torch.stack([(p[:, horizon] - g[:, horizon]).abs().mean()
                                 for p, g in zip(predictions, golds)]).mean().item()
        print(f"horizon {horizon + 1} model MAE: {model_mae:.2f}")

assert all(torch.equal(a, b) for a, b in zip(*all_golds)), "seeds have different test labels"
print("\nBoth seeds have identical test labels.")
PY
```

如果标签或重算指标断言失败，先检查是否用了不同提交、不同预处理产物或混合了别次实验的结果。若模型不如最后一个月基线，先调查模型与数据；增加 seed 只会更准确地量化当前问题。

## 3. 在独立目录复跑 seed 1

这一步用于检查**相同 seed、相同代码和同一块 GPU**是否给出近似相同的结果。原始运行使用 Tesla T4；如果新服务器换了 GPU 型号，结果只能用于检查跨设备表现，不能严格判定原环境的可复现性。原 CLI 的结果路径只由模式、粒度、模型和 seed 决定，直接再运行 `--seed 1` 会覆盖旧文件。下面通过相同训练函数指定独立结果目录。

在 `tmux` 中运行；保持 `CUBLAS_WORKSPACE_CONFIG` 已导出。脚本会拒绝覆盖已有复跑目录：

```bash
set -o pipefail
python - <<'PY' 2>&1 | tee diagnostics/seed-1-repeat.log
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path.cwd() / "benchmark/graph_method"))
import main

config = main.ExperimentConfig(
    data_name="region", mode="count", model_name="EvolveGCNH",
    device="cuda:0", seed=1, window_size=6, pred_length=3,
    num_epochs=500, results_dir=Path("diagnostics/repeat-results"),
)
output = main.result_dir(config)
if output.exists():
    raise SystemExit(f"refusing to overwrite {output}")
device = main.resolve_device(config.device)
print("commit should be 950a1d8febbf992b8bda061d35f03107d0b18478")
print("torch", torch.__version__, "GPU", torch.cuda.get_device_name(device))
print("output", output)
dataset = main.load_dataset(config)
train, validation, test = main.temporal_signal_split(dataset, config.train_ratio, config.eval_ratio)
metrics = main.train_experiment(config, train, validation, test, device=device)
print(json.dumps(metrics, indent=2))
PY
```

复跑后比较指标、预测和标签：

```bash
python - <<'PY' | tee diagnostics/seed-1-compare.txt
import json
import os
from pathlib import Path

import torch

original = Path(os.environ.get(
    "EVOLVEGCN_ORIGINAL_ROOT",
    "benchmark/graph_method/results/count/region/EvolveGCNH",
)) / "1"
repeat = Path("diagnostics/repeat-results/count/region/EvolveGCNH/1")
for label, folder in (("original", original), ("repeat", repeat)):
    print(label, json.loads((folder / "metrics.json").read_text(encoding="utf-8")))
for i in range(4):
    a = torch.load(original / f"pred_{i}.pt", map_location="cpu", weights_only=True)
    b = torch.load(repeat / f"pred_{i}.pt", map_location="cpu", weights_only=True)
    ga = torch.load(original / f"gold_{i}.pt", map_location="cpu", weights_only=True)
    gb = torch.load(repeat / f"gold_{i}.pt", map_location="cpu", weights_only=True)
    assert torch.equal(ga, gb), f"window {i}: test labels changed"
    print(f"window {i}: exact prediction match={torch.equal(a, b)}, "
          f"max absolute difference={(a - b).abs().max().item():.6g}")
PY
```

若同 seed 的误差或预测相差明显，先核对提交、数据、依赖、GPU 和 `CUBLAS_WORKSPACE_CONFIG`，再调查 CUDA 算子的确定性。即使逐元素不完全相同，只要差异极小，也不能据此认定复跑失败。

## 4. 决定是否补充 seed

只有完成前两步后才增加 seed。若同 seed 稳定，而 seed 0/1 仍差异很大，补充 seed 2、3、4 可以估计初始化带来的波动。下面的循环遇到已有 seed 目录就停止，避免覆盖：

```bash
set -o pipefail
for seed in 2 3 4; do
  output="benchmark/graph_method/results/count/region/EvolveGCNH/${seed}"
  if [ -e "$output" ]; then
    echo "refusing to overwrite ${output}"
    break
  fi
  python benchmark/graph_method/main.py \
    --data_name region --mode count --model_name EvolveGCNH \
    --device cuda:0 --seed "${seed}" \
    --window_size 6 --pred_length 3 --num_epochs 500 \
    2>&1 | tee "diagnostics/seed-${seed}.log"
  status=$?
  if [ "$status" -ne 0 ]; then
    echo "seed ${seed} failed with exit code ${status}"
    break
  fi
done
```

五次运行都完成后，汇总逐次和逐窗口指标：

```bash
python - <<'PY' | tee diagnostics/five-seed-summary.txt
import json
import os
import statistics
from pathlib import Path

import torch

original = Path(os.environ.get(
    "EVOLVEGCN_ORIGINAL_ROOT",
    "benchmark/graph_method/results/count/region/EvolveGCNH",
))
new = Path("benchmark/graph_method/results/count/region/EvolveGCNH")
metrics = []
for seed in range(5):
    folder = (original if seed < 2 else new) / str(seed)
    row = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
    metrics.append(row)
    window_mae = []
    for i in range(4):
        pred = torch.load(folder / f"pred_{i}.pt", map_location="cpu", weights_only=True)
        gold = torch.load(folder / f"gold_{i}.pt", map_location="cpu", weights_only=True)
        window_mae.append((pred - gold).abs().mean().item())
    print(f"seed {seed}: MAE={row['MAE']:.2f}, RMSE={row['RMSE']:.2f}, "
          f"window MAE={[round(value, 2) for value in window_mae]}")
for key in ("MAE", "RMSE"):
    values = [row[key] for row in metrics]
    print(f"{key}: mean={statistics.fmean(values):.2f}, "
          f"population std={statistics.pstdev(values):.2f}")
PY
```

同时保留第 2 节的基线结果。原论文的 Region 数值可作量级参照；当前修复版修改了目标时间切分、checkpoint 选择和 EvolveGCN-H 递归语义，论文中的 `±` 也不一定与这里按 seed 计算的标准差同义。

如果同 seed 稳定但前两个测试窗口持续异常，再设计**单独标记的**状态预热或验证窗口敏感性实验。当前实现只有一个验证窗口，且每次测试遍历从初始递归状态开始；这些都是值得检查的假设，不能仅凭本次结果确定根因。任何改变切分、状态边界或指标口径的实验都应另存目录，并与本指南的原设定结果分开报告。

## 5. 保存诊断结果

`diagnostics/analysis.txt`、`seed-1-repeat.log`、`seed-1-compare.txt` 和复跑的 `.pt` 文件是判断下一步的核心证据。完成后可将 `diagnostics/` 打包并按上一份指南的方法下载：

```bash
tar -czf evolvegcn-region-count-diagnostics.tar.gz diagnostics
```

如果还跑了 seed 2 至 4，也把各自的 `benchmark/graph_method/results/count/region/EvolveGCNH/<seed>` 目录加入归档。保留原来的 seed 0/1 结果包，不覆盖它。
