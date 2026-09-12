# 在 Apple Silicon macOS 上复现 graph-method 测试的环境记录

`requirements.txt` 锁定的是 `torch==1.13.1+cu117`，那是 Linux/Windows 的 CUDA wheel，
在 arm64 macOS 上**装不上**；而 PyTorch Geometric 的原生扩展
（`torch_scatter` / `torch_sparse`）也没有为 torch 1.13.1 + arm64 macOS 提供预编译包。

这份文档记录一次实际跑通的做法、踩到的坑、以及怎么干净删除，供下次在本机临时需要跑
`benchmark/graph_method` 时直接照抄。机器环境：macOS 26.6.2 / arm64 / 系统 Python 之外
只用到 `/opt/homebrew/Caskroom/miniconda/base` 里的 Python 3.13.2。

> 本文件是**本机复现笔记**，不是项目的正式依赖声明；项目的锁定依赖仍以 `requirements.txt` 为准。

---

## 0. 结论速览

| | 环境 A（推荐） | 环境 B（最接近锁定版本） |
|---|---|---|
| Python | 3.13.2 | 3.8.20（uv 下载的独立解释器） |
| torch | 2.7.0（CPU） | 2.3.0（CPU） |
| torch_geometric | 2.4.0 | 2.4.0 |
| torch_geometric_temporal | 0.54.0 | 0.54.0 |
| torch_scatter / torch_sparse | 2.1.2 / 0.6.18 | 2.1.2 / 0.6.18 |
| numpy / pandas / pyarrow | 2.5.3 / 3.0.5 / 25.0.1 | 1.22.4 / 1.3.5 / 14.0.1 |
| 用途 | 日常跑测试、跑实验（装得最顺） | 验证 Python 3.8 + 锁定数据/图库版本 |
| 测试结果 | 136 passed / 6 skipped（共 142） | 136 passed / 6 skipped（共 142） |

要点：

1. **不要用 conda**：本机 conda 需要写 `~/Library/Caches/conda-anaconda-tos/`，当前用户没有权限，
   `conda create` 会直接报 `CondaToSPermissionError`。
2. **用 `uv`**，并且把 uv 的解释器目录与缓存目录都指到仓库内，绕开不可写的 `~/Library/...`。
3. PyG 扩展用 data.pyg.org 上与 torch 版本匹配的预编译 wheel（macOS 上是 universal2，含 arm64）。
4. `torch_geometric_temporal==0.54.0` 必须用 `--no-deps` 单独装，否则它的元数据会把 pandas 拉到 1.3.5。

---

## 1. 环境 A：Python 3.13 + torch 2.7（日常使用）

```bash
cd /path/to/benchmark

# 关键：~/Library/Caches/pip 当前用户不可写，必须把 pip 缓存放进仓库
export PIP_CACHE_DIR="$PWD/.pip-cache"

# 用系统/conda 里任意一个 Python 3.12+ 建 venv
/opt/homebrew/Caskroom/miniconda/base/bin/python -m venv .venv-graph
.venv-graph/bin/python -m pip install --upgrade pip setuptools wheel

# 基础依赖（numpy/pandas/pyarrow 不锁版本，用 py3.13 能装的即可）
.venv-graph/bin/python -m pip install numpy pandas pyarrow pytest "torch==2.7.0"

# PyG 原生扩展：走 data.pyg.org 为 torch 2.7.0 预编译的 macOS universal2 wheel
.venv-graph/bin/python -m pip install torch_scatter torch_sparse \
    -f https://data.pyg.org/whl/torch-2.7.0+cpu.html

# PyG 必须是 2.4.0（原因见第 3 节第 5 条）
.venv-graph/bin/python -m pip install "torch_geometric==2.4.0"

# tgt 0.54.0：先装它要的 decorator，再用 --no-deps 装本体
.venv-graph/bin/python -m pip install "decorator==4.4.2"
.venv-graph/bin/python -m pip install --no-deps "torch_geometric_temporal==0.54.0"
```

自检：

```bash
.venv-graph/bin/python -c "
import torch, torch_geometric, torch_geometric_temporal, torch_scatter, torch_sparse
print(torch.__version__, torch_geometric.__version__, torch_geometric_temporal.__version__)
from torch_geometric_temporal.nn.recurrent import EvolveGCNO, GConvGRU, TGCN, A3TGCN, DCRNN, DyGrEncoder, GCLSTM, GConvLSTM, LRGCN, MPNNLSTM
print('tgt imports OK')
"
```

---

## 2. 环境 B：Python 3.8.20 + 锁定版本（最接近 requirements.txt）

`conda create -p .venv-pinned python=3.8` 在本机会失败（见第 3 节第 2 条），
改用 `uv` 下载独立 CPython 3.8，并把所有 uv 目录也放在仓库内：

```bash
cd /path/to/benchmark

# 先把 uv 装进环境 A（uv 只是一个静态二进制，不需要单独装）
.venv-graph/bin/python -m pip install uv

# 让 uv 不要碰 ~/Library
export UV_PYTHON_INSTALL_DIR="$PWD/.uv-python"
export UV_CACHE_DIR="$PWD/.uv-cache"
export UV_TOOL_DIR="$PWD/.uv-tools"

UV=.venv-graph/bin/uv
PY="$PWD/.venv-pinned/bin/python"

$UV venv --python 3.8 "$PWD/.venv-pinned"     # 下载 CPython 3.8.20 到 .uv-python

$UV pip install --python "$PY" "numpy==1.22.4" "pandas==1.3.5" "pyarrow==14.0.1" pytest
$UV pip install --python "$PY" "torch==2.3.0"          # 为什么不是 1.13.1：见第 3 节第 3 条
$UV pip install --python "$PY" "torch_geometric==2.4.0"
$UV pip install --python "$PY" \
    --find-links https://data.pyg.org/whl/torch-2.3.0+cpu.html \
    "torch_scatter==2.1.2" "torch_sparse==0.6.18"
$UV pip install --python "$PY" --no-deps \
    "torch_geometric_temporal==0.54.0" "decorator==4.4.2"
```

> 注意：torch 2.3.0 是**最后一个支持 Python 3.8** 的版本，data.pyg.org 为它提供了
> cp38 的 `macosx_11_0_universal2` wheel，所以这条路能走通。
> 这里唯一偏离 `requirements.txt` 的是 torch 的构建方式（2.3.0 CPU vs 1.13.1+cu117），
> 因为 CUDA 在 Apple Silicon 上不存在。

---

## 3. 踩过的坑（下次直接跳过）

1. **`~/Library/Caches/pip` 不可写**
   报错形如 `The directory '/Users/<you>/Library/Caches/pip' ... is not owned or is not writable`，
   pip 会禁用缓存甚至失败。解决：`export PIP_CACHE_DIR="$PWD/.pip-cache"`。

2. **conda 不可用**
   `conda create` 报 `CondaToSPermissionError: Unable to read/write path
   (~/Library/Caches/conda-anaconda-tos/...)`。当前用户对该目录没有权限，
   除非修权限或加 `sudo`，所以直接用 `uv` 更省事。

3. **torch 1.13.1 的 PyG 扩展编译失败**
   - `torch==1.13.1+cu117` 只有 Linux/Windows wheel，macOS 装不了。
   - PyPI 上 `torch==1.13.1` 有 cp38 的 `macosx_11_0_arm64` wheel，可以装；
     但 `torch_scatter==2.1.2` / `torch_sparse==0.6.18` 在该组合下没有 arm64 wheel，
     源码编译会因 torch 1.13 的 `c10/util/Optional.h` 与当前 clang/libc++ 不兼容而失败
     （报错落在 `csrc/cpu/scatter_cpu.cpp`，`531 warnings and 1 error generated`）。
   - 结论：在 arm64 macOS 上把 torch 抬到 2.3.0 换取官方 universal2 wheel。

4. **`torch_geometric_temporal==0.54.0` 的元数据很旧**
   它声明 `pandas<=1.3.5`、`decorator==4.4.2`、`cython`、`torch-sparse`、`torch-scatter`。
   直接 `pip install` 会在 Python 3.13 上去构建老 pandas 并失败
   （`ModuleNotFoundError: No module named 'pkg_resources'`）。
   解决：依赖装齐后 `--no-deps` 装本体。

5. **PyG 不能升到 2.8**
   tgt 0.54.0 里 `nn/attention/tsagcn.py` 仍然 `from torch_geometric.utils.to_dense_adj import ...`，
   PyG 2.8 已把该子模块路径移除，导入会 `ModuleNotFoundError`。所以 PyG 固定 2.4.0。

6. **`--no-build-isolation` 也救不了 1.13**
   PyG 扩展在 build 时需要 `import torch`，用 `--no-build-isolation`（先装 setuptools/wheel）
   可以越过构建隔离，但真正的失败是 C++ 头文件不兼容，不是构建隔离问题。

7. **CUDA / MPS**
   本机 `torch.cuda.is_available()` 为 `False`，所有 CUDA 测试会以
   "CUDA is not available in this environment" 显式 skip；这是预期行为。
   `main.py` 只支持 `cpu` 和 `cuda[:index]`，不接受 `mps`。

---

## 4. 怎么跑

```bash
cd /path/to/benchmark

# 单元测试套件（快环境）
.venv-graph/bin/python -m pytest benchmark/graph_method/tests -q
# 或
.venv-graph/bin/python -m unittest discover -s benchmark/graph_method/tests

# 同一套测试，在 Python 3.8 + 锁定数据/图库版本下
.venv-pinned/bin/python -m pytest benchmark/graph_method/tests -q

# 依赖真实 parquet 的集成检查（约 2.5 分钟，会加载全部 14 个组合，内存占用较高）
# 用 JOB_SDF_DATA_DIR 指向已生成的 data 目录可跳过重新生成
JOB_SDF_INTEGRATION=1 JOB_SDF_DATA_DIR="$PWD/benchmark/graph_method/data" \
  .venv-pinned/bin/python -m unittest discover \
  -s benchmark/graph_method/tests -p "test_generated_datasets.py"

# 生成全部 14 个粒度/模式产物（约 1.6 分钟，产物 1.3G）
.venv-graph/bin/python benchmark/graph_method/prepare_graph_data.py

# 默认文档命令的单 epoch 冒烟
.venv-graph/bin/python benchmark/graph_method/main.py \
    --data_name r0 --mode rate --model_name EvolveGCNH --num_epochs 1
```

测试相关的环境变量：

| 变量 | 作用 |
|---|---|
| `PIP_CACHE_DIR` | 把 pip 缓存放进仓库，绕开不可写的 `~/Library/Caches/pip` |
| `UV_PYTHON_INSTALL_DIR` / `UV_CACHE_DIR` / `UV_TOOL_DIR` | 让 uv 只写仓库内目录 |
| `JOB_SDF_INTEGRATION=1` | 启用 `tests/test_generated_datasets.py` 的真实数据集成测试 |
| `JOB_SDF_DATA_DIR=<dir>` | 让集成测试校验已有产物，而不是重新生成到临时目录 |

---

## 5. 怎么删

环境与产物都已在 `.gitignore` 里，不会进 git。不用时直接删：

```bash
cd /path/to/benchmark

# 两个虚拟环境 + uv 的解释器/缓存 + pip 缓存
rm -rf .venv-graph .venv-pinned .uv-python .uv-cache .uv-tools .pip-cache

# 测试缓存（pytest 会在自己的目录里写 .gitignore，删掉无副作用，下次运行会自动重建）
rm -rf .pytest_cache

# 生成的数据产物与实验结果（重跑 prepare_graph_data.py / main.py 即可恢复）
rm -rf benchmark/graph_method/data benchmark/graph_method/results
```

删除后想再跑，就照第 1 节（环境 A）或第 2 节（环境 B）重建；
只跑测试用环境 A 就够了，环境 B 仅用于验证 Python 3.8 + 锁定版本。

---

## 6. 版本记录

环境 A（`.venv-graph`，Python 3.13.2）：

```
numpy==2.5.3
pandas==3.0.5
pyarrow==25.0.1
pytest==9.1.1
torch==2.7.0
torch_scatter==2.1.2
torch_sparse==0.6.18
torch_geometric==2.4.0
decorator==4.4.2
torch_geometric_temporal==0.54.0
--find-links https://data.pyg.org/whl/torch-2.7.0+cpu.html
```

环境 B（`.venv-pinned`，Python 3.8.20）：

```
numpy==1.22.4
pandas==1.3.5
pyarrow==14.0.1
torch==2.3.0
torch_scatter==2.1.2
torch_sparse==0.6.18
torch_geometric==2.4.0
decorator==4.4.2
torch_geometric_temporal==0.54.0
--find-links https://data.pyg.org/whl/torch-2.3.0+cpu.html
```

同样内容另见 `requirements-macos.txt`（环境 A 可直接 `pip install -r`，但
`torch_geometric_temporal` 仍需按第 1 节用 `--no-deps` 单独装）。
