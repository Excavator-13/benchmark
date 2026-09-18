# 第一次租 GPU 云服务器运行 EvolveGCN

这份指南的目标有两层：

1. 先用 **`region + count + 1 epoch`** 确认仓库里的 EvolveGCN-H 能在 GPU 上完整跑通。
2. 环境无误后，对同一个 `region` 粒度用 seed 0 和 1 分别跑完 500 epoch，得到可与原论文做量级对照的 MAE/RMSE。

全程只预处理一个粒度的 `count` 数据，不生成全部 14 组数据，也不跑其他模型。

最简流程就是：

```text
租机 -> SSH 登录 -> 检查 GPU -> clone 代码 -> 建独立 Python 环境
     -> 只预处理 region/count -> 跑 1 epoch 自检 -> 跑 2 个完整 seed
     -> 汇总指标 -> 与论文做量级对照 -> 下载结果 -> 停机/释放
```

---

## 1. 租什么样的机器

按量计费即可，不需要包月。建议选择：

| 项目 | 建议 | 说明 |
|---|---|---|
| GPU | 1 张 NVIDIA GPU，推荐 24 GB 显存 | A10 24G、RTX 3090/4090 等；不用租多卡。12 GB 可能能跑，但首次租机不建议为省一点费用承担 OOM 风险 |
| CPU / 内存 | 4-8 vCPU，32 GB 内存 | 预处理和 JSON 加载也会用 CPU 内存；16 GB 可能够，32 GB 更稳妥 |
| 硬盘 | 50 GB 或以上 | 代码和原始数据约 220 MB，主要空间会被 Conda、PyTorch、pip 缓存、生成数据和结果占用 |
| 系统 | x86_64 Linux，Ubuntu 20.04/22.04 | 不要选 Windows，也不要选 ARM 机型 |
| 镜像 | 优先选 PyTorch 2.3 / Python 3.8 / CUDA 12.1 | 没有完全一致的镜像也没关系，下面会新建独立环境 |
| 网络 | 能访问 GitHub、PyPI、PyTorch 和 `data.pyg.org` | 安装依赖需要下载数 GB 文件 |

CUDA 镜像的版本不必与 Python 环境里的 CUDA 运行库字面相同。PyTorch wheel 会自带 CUDA 运行库，关键是宿主机上的 NVIDIA 驱动要够新。本指南使用 CUDA 12.1 wheel，`nvidia-smi` 显示的驱动版本建议不低于 525.60.13。

> 不要只根据 GPU 型号判断性价比。这段代码是按时间快照串行遍历的，还要保留整个训练序列的反向传播图，所以“显存够不够”比峰值算力更重要。GPU 利用率不一定一直很高，这不代表程序没有使用 GPU。

### 创建实例时的注意事项

1. 选择“按量/按时计费”。
2. 配置 SSH 密钥或强密码，记下公网 IP、SSH 端口和登录用户名。
3. 只需放行 SSH 端口（通常是 22），本次不需要开 Jupyter 或其他公网端口。
4. 留意平台的“关机”和“释放”区别：有些平台关机后仍收 GPU 费用，或者仍收系统盘费用。

---

## 2. SSH 登录后先做检查

在你自己的电脑终端执行（将用户名、IP 和端口换成平台提供的值）：

```bash
ssh -p 22 ubuntu@1.2.3.4
```

登录服务器后执行：

```bash
nvidia-smi
uname -m
df -h
free -h
command -v conda || true
python --version || true
python3 --version || true
python -m pip --version || true
```

预期：

- `nvidia-smi` 能显示 GPU 名称、显存和驱动版本。如果这一步失败，先在云平台确认实例确实挂载了 GPU，不要继续安装 Python 包。
- `uname -m` 应该输出 `x86_64`。
- Python、pip 和 Conda **是否自带取决于你选的镜像**。深度学习镜像通常自带，纯 Ubuntu 镜像通常只有系统 Python，甚至没有 pip。

不要在系统 Python 上使用 `sudo pip install`。下面会为项目建一个可删除的独立环境。

---

## 3. 下载代码

当前已修复的图预测代码在该 fork 的 `my-change` 分支：

```bash
git clone --branch my-change --single-branch \
  https://github.com/Excavator-13/benchmark.git
cd benchmark
git status --short --branch
```

`git status` 应显示当前是 `my-change` 分支。仓库已直接包含本次所需的 `dataset/demand/region.parquet` 和 `dataset/graph/region.parquet`，不用再单独下载数据集。

> 如果你后面把本地改动 push 到了其他仓库或分支，这里应换成那个 URL 和分支。直接 clone 原始上游仓库不会包含当前分支的修复。

---

## 4. 创建 Python 3.8 环境

### 情况 A：服务器已有 Conda（推荐）

```bash
conda create -n job-sdf python=3.8 -y
conda activate job-sdf
python --version
python -m pip --version
```

如果 `conda activate` 提示需要初始化 shell，执行：

```bash
conda init bash
source ~/.bashrc
conda activate job-sdf
```

### 情况 B：服务器没有 Conda

先确认 `uname -m` 是 `x86_64`，然后以当前用户安装 Miniconda，不需要 `sudo`：

```bash
wget -O /tmp/miniconda.sh \
  https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash /tmp/miniconda.sh -b -p "$HOME/miniconda3"
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda create -n job-sdf python=3.8 -y
conda activate job-sdf
python --version
python -m pip --version
```

此后每次重新 SSH 登录，如果 `conda` 命令不存在，先执行：

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate job-sdf
```

---

## 5. 安装试跑所需的最小依赖

确认终端前面已显示 `(job-sdf)`，并且当前目录是仓库根目录，然后按顺序执行：

```bash
python -m pip install --upgrade pip setuptools wheel

# PyTorch 2.3.0 + CUDA 12.1。本次不需要 torchvision/torchaudio。
python -m pip install \
  torch==2.3.0 \
  --index-url https://download.pytorch.org/whl/cu121

# 数据读取和运行时基础依赖。
python -m pip install \
  numpy==1.22.4 \
  pandas==1.3.5 \
  pyarrow==14.0.1 \
  tqdm==4.64.0 \
  decorator==4.4.2 \
  cython

# PyG 的原生扩展必须与 torch 2.3.0 + cu121 严格匹配。
python -m pip install \
  torch_scatter==2.1.2 \
  torch_sparse==0.6.18 \
  -f https://data.pyg.org/whl/torch-2.3.0+cu121.html

python -m pip install torch_geometric==2.4.0

# 这个老版包的依赖元数据会尝试重新解析旧 pandas，所以在依赖装齐后禁止它再解析。
python -m pip install --no-deps torch_geometric_temporal==0.54.0

# 确认已安装包没有缺失或冲突的依赖。
python -m pip check
```

### 为什么不直接执行 `pip install -r requirements.txt`

根目录的 `requirements.txt` 是旧的 CUDA 11.7 锁定环境，其中有 `torch==1.13.1+cu117` 和 `dgl==1.1.2+cu117`。这些带 `+cu117` 的 wheel 不在默认 PyPI 索引中，而且 DGL、Transformers、NLTK 等不是这次 EvolveGCN-H 冒烟测试所需的。上面的命令只安装这条运行路径必须的包，并且显式指定 CUDA wheel 来源。

`torch_geometric` 要保持在 2.4.0。它如果被升级到过新版本，可能与 `torch_geometric_temporal==0.54.0` 的旧导入路径不兼容。

---

## 6. 确认 Python 真的看到 GPU

先做一次完整导入和 CUDA 自检：

```bash
python - <<'PY'
import torch
import torch_geometric
import torch_geometric_temporal
import torch_scatter
import torch_sparse

print("torch:", torch.__version__)
print("torch CUDA runtime:", torch.version.cuda)
print("torch_geometric:", torch_geometric.__version__)
print("torch_geometric_temporal:", torch_geometric_temporal.__version__)
print("CUDA available:", torch.cuda.is_available())
print("GPU count:", torch.cuda.device_count())
if not torch.cuda.is_available():
    raise SystemExit("ERROR: PyTorch cannot see a CUDA GPU")
print("GPU 0:", torch.cuda.get_device_name(0))

from torch_geometric_temporal.nn.recurrent import EvolveGCNO
print("graph imports OK")
PY
```

必须看到：

```text
CUDA available: True
GPU count: 1
GPU 0: ...
graph imports OK
```

可再跑本地 EvolveGCN-H 层的小型单元测试：

```bash
python -m unittest discover \
  -s benchmark/graph_method/tests \
  -p 'test_evolvegcnh.py'
```

这组测试中包含 CUDA 前向传播和反向传播检查。在 GPU 正常可用时，CUDA 用例不应该被 skip。

---

## 7. 为什么选 `region + count`

仓库中 7 种粒度都有 36 个月的序列，但“粒度-技能”节点数量差异很大：

| 代码 | 论文中的含义 | 时间序列行数 | 是否适合这次云 GPU 实验 |
|---|---|---:|---|
| `r0` | 整体劳动力市场 | 2,335 | 最小，但只有一个市场上下文，粒度过粗，对比价值较低 |
| `region` | 7 个地区 | 16,345 | **推荐：第二小，有实际粒度含义，论文也明确在 GPU 上跑此粒度** |
| `r1` | 14 个 L1 职业大类 | 32,690 | 也有对比价值，但节点数是 `region` 的 2 倍 |
| `r2` | 52 个 L2 职业子类 | 121,420 | 资源消耗明显增大，首次租机不优先 |
| `r1-region` | 地区 x L1 职业 | 228,830 | 较大，不建议作为第一次完整实验 |
| `r2-region` | 地区 x L2 职业 | 849,940 | 论文都改用 CPU，本次不跑 |
| `company` | 521 家公司 | 1,216,535 | 论文都改用 CPU，本次不跑 |

原论文的 GNN 主表预测的是**技能需求量**，对应仓库的 `count -> dataset/demand`，不是 `rate -> dataset/proportion`。因此要与论文数值对照，必须用 `count`。

### 只准备 `region + count`

一定带上两个参数。如果都不写，脚本会生成 7 种粒度 x 2 种模式的全部 14 组数据。

```bash
python benchmark/graph_method/prepare_graph_data.py \
  --mode count \
  --data_name region
```

成功后检查产物：

```bash
ls -lh benchmark/graph_method/data/count/region.json
```

这一步主要是 CPU 数据处理，`nvidia-smi` 里 GPU 没有负载是正常的。

---

## 8. 第一阶段：先跑 1 epoch 冒烟测试

开另一个 SSH 窗口可以实时看 GPU：

```bash
watch -n 1 nvidia-smi
```

原窗口用 seed 999 执行冒烟命令。专门使用 999，是为了不覆盖稍后正式运行的 seed 0/1 结果。

```bash
time python benchmark/graph_method/main.py \
  --data_name region \
  --mode count \
  --model_name EvolveGCNH \
  --device cuda:0 \
  --seed 999 \
  --window_size 6 \
  --pred_length 3 \
  --num_epochs 1
```

这条命令会完整经过：加载数据、按时间切分训练/验证/测试集、训练 1 个 epoch、保存验证集最优 checkpoint、恢复 checkpoint，以及在测试集上输出 RMSE/MAE。

只要进程没有报错、RMSE/MAE 是有限数，并且以下目录中有 `checkpoint.pt`、`metrics.json`、`pred_<n>.pt` 和 `gold_<n>.pt`，冒烟测试就通过了：

```bash
find benchmark/graph_method/results/count/region/EvolveGCNH/999 \
  -maxdepth 1 -type f -print | sort
cat benchmark/graph_method/results/count/region/EvolveGCNH/999/metrics.json
```

`time` 最后输出的 `real` 是本次总耗时。1 epoch 还包含启动、加载和最终测试的固定开销，所以不能直接精确乘以 500；但可以用 `real x 500 x 2` 作为两个 seed 耗时的保守上界，并结合云平台每小时价格估算预算。

1 epoch 的指标不用与论文比较。只有它通过后，才继续下一节的完整实验。

---

## 9. 第二阶段：跑完 `region` 粒度

### 为什么跑两个 seed

当前代码的一次调用只跑一个 seed。原仓库释放的图模型实现会自动跑 seed 0 和 1，而论文图模型表以 `均值 ± 波动` 展示数值。因此这里显式分别调用 seed 0 和 1，既保留每次结果，也能计算一个简单汇总。

### 在 tmux 里运行

500 epoch x 2 会比冒烟测试长很多，不要直接放在普通 SSH 会话中。

```bash
tmux new -s evolvegcn
conda activate job-sdf
cd ~/benchmark
mkdir -p logs
set -o pipefail
```

如果仓库不在 `~/benchmark`，将 `cd` 换成实际路径。接着在 tmux 中执行：

```bash
for seed in 0 1; do
  echo "===== region/count seed ${seed} started at $(date) ====="
  python benchmark/graph_method/main.py \
    --data_name region \
    --mode count \
    --model_name EvolveGCNH \
    --device cuda:0 \
    --seed "${seed}" \
    --window_size 6 \
    --pred_length 3 \
    --num_epochs 500 \
    2>&1 | tee "logs/evolvegcnh-region-count-seed-${seed}.log"
  status=$?
  if [ "${status}" -ne 0 ]; then
    echo "seed ${seed} failed with exit code ${status}; stop here"
    break
  fi
  echo "===== seed ${seed} finished at $(date) ====="
done
```

按 `Ctrl-b`，松开后再按 `d` 可退出 tmux 界面，运行不会中断。重新 SSH 登录后查看：

```bash
tmux attach -t evolvegcn
```

查看已经完成的结果和日志：

```bash
cat benchmark/graph_method/results/count/region/EvolveGCNH/0/metrics.json
cat benchmark/graph_method/results/count/region/EvolveGCNH/1/metrics.json
tail -n 30 logs/evolvegcnh-region-count-seed-0.log
tail -n 30 logs/evolvegcnh-region-count-seed-1.log
```

### 汇总两个 seed

```bash
python - <<'PY'
import json
import statistics
from pathlib import Path

root = Path("benchmark/graph_method/results/count/region/EvolveGCNH")
runs = []
for seed in (0, 1):
    path = root / str(seed) / "metrics.json"
    with path.open(encoding="utf-8") as handle:
        metrics = json.load(handle)
    runs.append(metrics)
    print(f"seed {seed}: MAE={metrics['MAE']:.6f}, RMSE={metrics['RMSE']:.6f}")

for name in ("MAE", "RMSE"):
    values = [run[name] for run in runs]
    print(
        f"{name}: mean={statistics.fmean(values):.6f}, "
        f"population_std={statistics.pstdev(values):.6f}"
    )
PY
```

### 与原论文对照

论文附录的“skill demand series with GNN-based methods”表中，EvolveGCN-H 在 Region 粒度的数值是：

| 指标 | 论文报告值 |
|---|---:|
| MAE | 30.07 ± 22.97 |
| RMSE | 166.34 ± 127.04 |

这些数值只适合做**量级和趋势对照**，不应要求当前分支精确复现，原因是：

- 论文文字说数据按 9:1:2 划分，释放代码实际在窗口化后按 0.83/0.04/剩余部分切分；当前分支保留了后一种代码口径。
- 原实现在每个 epoch 内直接用测试集选 checkpoint，当前分支已改为只用验证集选模型，最后才访问一次测试集。
- 当前分支修复了 EvolveGCN-H 权重在时间快照间的递归、梯度和状态边界，所以模型语义已不同于原始 bug 版实现。
- 论文描述的图边权是共现频次，但公开 Parquet 文件没有独立的 frequency 列。当前预处理只能保留文件实际提供的完整上下文和重复行信息。

因此，你可以检查当前结果是否在合理量级、两个 seed 是否差异过大，但不要用“小数点后必须一样”作为成功标准。

---

## 10. 常见问题

### `nvidia-smi: command not found` 或无法显示 GPU

这是实例/镜像/驱动问题，还不是 Python 问题。检查是否租了 GPU 实例、GPU 是否已挂载，以及是否选了 NVIDIA CUDA 或深度学习镜像。

### `torch.cuda.is_available()` 是 `False`

先比较：

```bash
nvidia-smi
python -m pip show torch
python -c 'import torch; print(torch.__version__, torch.version.cuda)'
```

- `nvidia-smi` 也失败：先修复云平台的 GPU/驱动环境。
- `nvidia-smi` 正常，但 `torch.version.cuda` 是 `None`：装成了 CPU 版 PyTorch。重新执行本文第 5 节中带 `cu121` 索引的 PyTorch 安装命令。
- 两者都正常却仍为 `False`：检查平台是否需要在容器设置中单独开启 GPU，或重建为平台推荐的 CUDA 12.1 镜像。

### 安装 `torch_scatter` / `torch_sparse` 时开始编译或报 `No matching distribution`

这两个包不应在小云机上从源码编译。检查：

```bash
python --version
python -c 'import torch; print(torch.__version__, torch.version.cuda)'
```

应当分别是 Python 3.8.x 和 `2.3.0+cu121 / 12.1`。然后原样使用 `https://data.pyg.org/whl/torch-2.3.0+cu121.html` 重装，不要去掉 `-f`。

### 导入 `torch_geometric_temporal` 时报 `to_dense_adj` 等模块错误

通常是 `torch_geometric` 装得过新。确认并降回 2.4.0：

```bash
python -m pip install --force-reinstall --no-deps torch_geometric==2.4.0
```

### 运行时提示找不到 `region.json`

说明没有成功做第 7 节的数据准备，或者下载了错误的仓库分支。在仓库根目录重新执行：

```bash
python benchmark/graph_method/prepare_graph_data.py --mode count --data_name region
```

### CUDA out of memory

先用 `nvidia-smi` 确认是否有其他进程占显存。这个运行器不提供 batch size 参数，而且完整训练遍历会保留时间序列的反向传播图。如果空闲 GPU 仍 OOM：

- 只是检查环境时，可以用下面的缩小命令；
- 要跑第 9 节的可对照实验时，不要改 `window_size=6` 和 `pred_length=3`，而应换 24 GB 或更大显存的实例。

```bash
python benchmark/graph_method/main.py \
  --data_name region --mode count --model_name EvolveGCNH \
  --device cuda:0 --seed 999 --num_epochs 1 --window_size 3 --pred_length 1
```

缩小命令的结果与论文设定不同，不能放入对比表。

### GPU 利用率不高

`region` 仍是相对小的数据，而且数据加载、Python 循环、checkpoint 读写也在 CPU 上完成。只要命令使用了 `--device cuda:0`，第 6 节显示 CUDA 可用，且程序成功产生结果，就不必追求 `nvidia-smi` 全程 100%。

---

## 11. 保存结果并结束计费

先记录软硬件环境，然后连同两个 seed 的结果和日志一起打包：

```bash
mkdir -p logs
python -m pip freeze > logs/pip-freeze.txt
nvidia-smi > logs/nvidia-smi.txt
git rev-parse HEAD > logs/git-commit.txt

tar -czf evolvegcn-region-count-results.tar.gz \
  benchmark/graph_method/results/count/region/EvolveGCNH/0 \
  benchmark/graph_method/results/count/region/EvolveGCNH/1 \
  logs
```

然后在你自己的电脑上执行：

```bash
scp -P 22 ubuntu@1.2.3.4:~/benchmark/evolvegcn-region-count-results.tar.gz .
```

检查文件已下载后：

1. 退出 SSH。
2. 回到云平台控制台，按平台的计费规则停止或释放实例。
3. 如果以后不再用，同时删除付费数据盘、快照和弹性公网 IP。
4. 释放前确认没有其他需要保留的数据；释放实例通常不可恢复。

---

## 最短命令清单

已经有 Conda 且网络正常时，真正的主线命令就是：

```bash
nvidia-smi
git clone --branch my-change --single-branch https://github.com/Excavator-13/benchmark.git
cd benchmark

conda create -n job-sdf python=3.8 -y
conda activate job-sdf
python -m pip install --upgrade pip setuptools wheel
python -m pip install torch==2.3.0 --index-url https://download.pytorch.org/whl/cu121
python -m pip install numpy==1.22.4 pandas==1.3.5 pyarrow==14.0.1 tqdm==4.64.0 decorator==4.4.2 cython
python -m pip install torch_scatter==2.1.2 torch_sparse==0.6.18 -f https://data.pyg.org/whl/torch-2.3.0+cu121.html
python -m pip install torch_geometric==2.4.0
python -m pip install --no-deps torch_geometric_temporal==0.54.0
python -m pip check

python benchmark/graph_method/prepare_graph_data.py --mode count --data_name region

# 先自检：成功后再跑下面的 500 epoch。
time python benchmark/graph_method/main.py \
  --data_name region --mode count --model_name EvolveGCNH \
  --device cuda:0 --seed 999 --window_size 6 --pred_length 3 --num_epochs 1

# 完整实验：建议在 tmux 中执行。
for seed in 0 1; do
  python benchmark/graph_method/main.py \
    --data_name region --mode count --model_name EvolveGCNH \
    --device cuda:0 --seed "${seed}" \
    --window_size 6 --pred_length 3 --num_epochs 500
done

cat benchmark/graph_method/results/count/region/EvolveGCNH/0/metrics.json
cat benchmark/graph_method/results/count/region/EvolveGCNH/1/metrics.json
```
