# T002 邻接敏感性检查：GConvGRU / GConvLSTM / EvolveGCN-H

- 检查 ID：`p01-t002-adjacency-probe-20261011-01`
- 所属任务：P01-T002（D013 第 5 条）；协议依据 §4.3
- 问题：`benchmark/graph_method/main.py` 当前构造的 `GConvGRU`、`GConvLSTM`（都传 `K=1`）和 `EvolveGCNH`，其输出是否真的依赖邻接？
- 执行代码身份：仓库 `7cbfe561285b1118c09e3e2510e1e2d711fe7432`；`main.py`、`models/evolvegcnh.py` 的 SHA256 见 [source-sha256.txt](source-sha256.txt)。
- 检查脚本：[adjacency_sensitivity.py](adjacency_sensitivity.py)；结果 [adjacency-probe.json](adjacency-probe.json)、[adjacency-probe.log](adjacency-probe.log)；环境 [environment.txt](environment.txt)。

## 环境（新增，只用于本检查）

| 组件 | 版本 |
| --- | --- |
| Python | 3.11.17（conda 环境 `job-sdf-baseline`，CPU） |
| torch | 2.14.1 |
| torch-geometric | 2.8.0.post1 |
| torch_sparse / torch_scatter | 0.6.18 / 2.1.2（本机源码编译，因为 arm64 无预编译 wheel） |
| torch_geometric_temporal | 0.56.2（`--no-deps` 安装；包内 `__version__` 自报 0.54.0） |

用户已授权安装 `torch`/`torch_geometric_temporal` 用于本检查。该环境是**新建的 CPU 探针环境**，不是 T004 baseline 或归档 GPU 实验（Tesla T4、`job-sdf`）的环境，也不参与复现它们的数值。

## 方法

- 固定的 32 节点图与固定输入：`x = randn(32,6)` 加逐节点偏移，确保没有两行相同（非退化输入）。
- 5 种邻接：`base_random`（96 条随机边）、`ring`、`ring_shifted`（保持边数、改变邻居）、`empty`（无边）、`star`；`edge_weight` 全为 1。
- 每次遍历前调用 `initial_state()` 重置递归状态，`model.eval()` 关闭 Dropout，固定 seed 重建参数，`torch.no_grad()`。
- 同时检查**递归层输出**（GConvLSTM 的 `h` 和 `c`）与 `GraphForecaster` 的**完整预测头输出**。
- 对照：同一邻接重复两次；`K=2` 正对照（单独标注配置，不修改仓库代码）。
- 容差：`1e-6`。

## 结果（层输出相对 `base_random` 的最大绝对差）

| 模型 / 配置 | ring | ring_shifted | empty | star | 同邻接重复 |
| --- | ---: | ---: | ---: | ---: | ---: |
| GConvGRU `K=1`（仓库配置） | 0 | 0 | 0 | 0 | 0 |
| GConvLSTM `K=1`（仓库配置） | 0 | 0 | 0 | 0 | 0 |
| GConvGRU `K=2`（正对照） | 1.458 | 1.387 | 1.404 | 1.428 | 0 |
| GConvLSTM `K=2`（正对照） | 1.275 | 1.538 | 1.386 | 1.249 | 0 |
| EvolveGCNH（仓库模型） | 2.028 | 2.474 | 3.101 | 3.400 | — |

完整预测头输出：

| 检查 | 最大绝对差 |
| --- | ---: |
| GConvGRU `K=1`：5 种邻接 vs `base_random` | 0（全部） |
| GConvGRU `K=1`：同邻接重复 | 0 |
| GConvLSTM `K=1`：`base` vs `ring_shifted` | 0 |
| EvolveGCNH：`base` vs `ring_shifted` | 0.6958 |

配置核对：`GConvGRU`/`GConvLSTM` 实例的 `K` 为 1（`K=2` 正对照为 2）；每个 `ChebConv` 的切比雪夫线性项数 `len(lins)` 在 `K=1` 时为 1、`K=2` 时为 2，与源码 `main.py:444,447` 传入的 `K=1` 一致。

## 结论

1. **当前仓库配置的 `GConvLSTM`、`GConvGRU` 不使用邻接。** 连空图与真实图都给出逐元素完全相同的层输出和预测输出，符合 `K=1` 只保留零阶项的行为；按协议 §4.3 应标记为**无邻居传播配置**（不能当作"图模型会比自身分支更强"的依据）。
2. **探针本身有效。** `K=2` 正对照在所有替换邻接下都产生约 1.2–1.5 的层输出差异，证明本方法能检测到邻接被使用；同邻接重复为精确 0，排除随机性混淆。
3. **`EvolveGCNH` 使用邻接。** 层输出差异 2.0–3.4、完整预测差异 0.70，说明其图卷积确实读取邻接。
4. 这只证明**配置会/不会使用邻接**，不证明真实图有预测收益，也不证明 `K=2` 更好；图的预测价值仍由 P02 的公平对照（自身分支 / 真实图 / 结构打乱图）决定。

## 限制

- 32 节点合成图上的一次性检查，不是完整训练或完整预测评测，不产生新预测结论，也不写入任何正式 run 或封存包。
- 未修改 `main.py`、未参数化 `K`、未开始多 seed 比较；`K=2` 只是本检查内的正对照。
- 本检查环境与归档 GPU 实验环境不同，结论只针对"当前安装版本 + 当前仓库配置"的行为；换版本或换配置需重做。
- 未覆盖其它声称使用图的模型（A3TGCN、DCRNN、GCLSTM、LRGCN、MPNNLSTM、TGCN、DyGrEncoder、EvolveGCNO），协议 §4.3 只要求优先覆盖这三个。

## 对 T002 的覆盖

本项完成 D013 第 5 条：在固定参数、非退化输入与相同初始递归状态下比较了原邻接与替换邻接，保存了同邻接重复对照、数值容差、层输出与完整预测输出，并把 `K=1` 标为无邻居传播配置。未改正式模型、未训练、未登记 OpenSpec 委托。
