# Job-SDF 修复独立核验报告

> 后续状态：用户授权修复后，相关问题已写入正式源码并完成小规模复核，见 [修复后报告](../fix_verification_20260921/REPORT.md)。下文保留首次诊断结果及历史证据；其中隔离替换脚本针对修复前源码，不适用于当前版本。

日期：2026-09-21。被核验提交：`f697544`。结论：**核心修复有效，但当前交付版本不能整体验收通过。**

原代码在本机 CPU 和 CUDA 上均能进入真实数据训练，但无法完成 checkpoint 保存／恢复。绕过这些兼容问题后，EvolveGCN-H 的递推、梯度、验证选模、设备迁移、复现性和最终输出均能运行；另发现多步预测的目标月份跨集合重叠，影响评估独立性。

本次是核验任务。**原模型、训练入口、数据加载器、预处理代码与原有测试均未修改**；兼容改动只保存在本目录的隔离副本中，不代表原版本已经修好。原始失败日志、隔离副本、差异、运行结果均保留。

## 范围与资源

- 诊断依据：用户指定的 `rescopy/benchmark/bug.md`，共 17 项。OpenSpec、Mac 记录及服务器指南作为修复声明与历史资料核对，没有执行其中的租机或 500 epoch 指令。
- 使用现有 `D:/conda-envs/JOBSDF/python.exe`：Python 3.8.20、PyTorch 1.13.1 / CUDA 11.7、PyG 2.4.0、PyG Temporal 0.54.0、NumPy 1.22.4、pandas 1.3.5、PyArrow 14.0.1。
- 原生扩展为 scatter 2.1.1+pt113cu117、sparse 0.6.17+pt113cu117，与 requirements.txt 的 2.1.2／0.6.18 有差异；因此不声称验证了该依赖清单的逐项原样安装。完整环境见 `environment.json`。
- GPU：RTX 4060 Laptop，8 GiB。真实模型只训练最小数据 r0：2,335 节点、60,804 边、36 个月；窗口 6、预测 3、seed 17，每次 3 epoch。
- 真实数据准备／加载检查覆盖 r0 和 region 的 rate、count 共 4 组；region 没有训练。其他 5 个大粒度及全部 14 组完整生成未执行。
- 11 种 CLI 模型各做 CPU、CUDA 的 32 节点、2 快照、2 epoch 小样本前后向检查，共 22 组；这不是这些模型在真实数据上的效果复现。
- r0 两次 CUDA 实跑的 PyTorch 活跃张量峰值均约 **61.6 MiB**，该数值不包含 CUDA 上下文、缓存、驱动与桌面占用。没有显存不足。

## 原版本的实测结果

| 检查 | 结果 |
|---|---|
| 直接运行原始完整 unittest suite | Windows 临时目录清理用例导致 runner 崩溃；原始日志 `unit-tests-initial.log` |
| 仅显式跳过上述已复现崩溃用例，再跑原始 suite | 165 项：140 通过、1 失败、19 错误、5 跳过；`original-unit-tests.json` |
| 原始 r0/rate CPU CLI，1 epoch | 首次保存 checkpoint 失败；`r0-rate-cpu-initial.log` |
| 原始 r0/rate CUDA CLI，计划 2 epoch | 首次保存 checkpoint 失败，未完成 2 epoch；`r0-rate-cuda-initial.log` |
| 原始 EvolveGCN-H 层测试 | 15 项通过，包括真实 CUDA 递推及反向传播 |
| 隔离兼容副本的 suite | 165 项：161 通过、0 失败、0 错误、4 跳过；`compat-unit-tests.json` |

原版本的 19 个测试错误主要由同一个 checkpoint 读取缺陷引发，不能解读成 19 个独立模型错误。5 个跳过项为：2 个 opt-in 真实数据集成用例、2 个本机有 CUDA 因而不适用的“CUDA 不可用”用例、1 个已单独复现的 Windows 清理崩溃用例。隔离副本修好最后一项后只剩 4 个跳过；真实数据另外进行了上述 4 组检查。

## 仍需处理的问题

### V-002 / 高：PyTorch 1.13.1 无法安全读取当前 checkpoint 的浮点元数据

位置：[main.py:625](C:/Users/Lenovo/Documents/大创参考论文/rescopy/cocopyres/benchmark/benchmark/graph_method/main.py:625)、[main.py:666](C:/Users/Lenovo/Documents/大创参考论文/rescopy/cocopyres/benchmark/benchmark/graph_method/main.py:666)。

保存时 `best_val_loss` 是 Python float，加载时使用 `weights_only=True`。本机 1.13.1 的受限反序列化器不支持其 pickle `BINFLOAT` 操作码，报 `Unsupported operand 71`。该问题与 CUDA、训练规模和中文路径无关：在 `BytesIO` 中仅保存 `{'best_val_loss': 0.25}` 就能复现。模型即使训练并保存成功，也会在最终恢复阶段失败。

隔离验证将该值存成 float64 标量张量，读取后仍由现有 `float(...)` 转回数值，保持 `weights_only=True`。正式修复应明确元数据格式／版本以及历史 checkpoint 的兼容策略，或采用明确验证过的新版 PyTorch 环境。不能仅认为改到英文目录即可解决。

证据：`minimal_reproductions.py`、`minimal-reproductions.json`、`test-main-initial.log`、`isolated/main.diff`。

### V-003 / 高：旧版 PyTorch 在当前 Windows 中文路径下保存失败

位置：[main.py:644](C:/Users/Lenovo/Documents/大创参考论文/rescopy/cocopyres/benchmark/benchmark/graph_method/main.py:644)、[main.py:812](C:/Users/Lenovo/Documents/大创参考论文/rescopy/cocopyres/benchmark/benchmark/graph_method/main.py:812)。

目录实际已经创建，但 `torch.save(payload, path)` 的旧版文件写入器报 `Parent directory ... does not exist`。当前项目父目录含中文。CPU、CUDA 原始命令都在此失败；保存一个单元素张量也可独立复现。

隔离副本用 Python `Path.open('wb')` 打开文件，再把文件对象交给 `torch.save`，验证能够保存与恢复。checkpoint、预测、gold 三处都要处理，只改 checkpoint 仍会在后续输出阶段遇到问题。

证据：两个 `r0-rate-*-initial.log`、`minimal-reproductions.json`。此项是本次 Windows／PyTorch 版本组合的兼容缺陷，不表示所有平台都失败。

### V-004 / 高：相邻多步窗口按快照切分，导致目标月份重叠

位置：[dataset.py:270](C:/Users/Lenovo/Documents/大创参考论文/rescopy/cocopyres/benchmark/benchmark/graph_method/dataset.py:270)、[main.py:349](C:/Users/Lenovo/Documents/大创参考论文/rescopy/cocopyres/benchmark/benchmark/graph_method/main.py:349)。

36 个月先按窗口 6、预测 3 生成 28 个快照，再按 0.83／0.04／剩余切为 23／1／4。快照索引虽然不相交，每个快照覆盖的目标月份却相交：

| 集合 | 实际被作为标签的月份 |
|---|---|
| train | 2021-07 至 2023-07 |
| validation | 2023-06、2023-07、2023-08 |
| test | 2023-07 至 2023-12 |

因此训练标签与测试标签共同包含 2023-07，验证标签与测试标签共同包含 2023-07、2023-08。实际张量也满足 `signal[22].y[:, 2] == signal[24].y[:, 0]`，并非仅由文档推算。

同事已修复“每个 epoch 直接遍历测试集选模”，但这不足以保证测试数据独立：模型训练已经接触第一段测试目标，验证选模又接触前两个月的测试目标。隔离兼容改动没有改变这一问题，所以下表指标只能作运行证据。

建议按目标月份边界分组，并丢弃跨越边界的预测窗口；或按预测长度设置必要的窗口间隔。划分后要同时检查目标日期不相交、预测时点可用信息以及三个集合非空，不能直接在只有 1 个快照的验证集上机械删两条。允许验证／测试输入使用此前已知历史，与这里标签跨集合重复是不同问题。

证据：`temporal-overlap.json`，包含实际目标月份和两个张量等式检查。

### V-005 / 中：两个测试存在平台适配问题

- [test_prepare_graph_data.py:139](C:/Users/Lenovo/Documents/大创参考论文/rescopy/cocopyres/benchmark/benchmark/graph_method/tests/test_prepare_graph_data.py:139)：进入临时目录后，仅用 `addCleanup` 注册退出目录；该 cleanup 晚于 `TemporaryDirectory` 的删除动作。Windows 无法删除当前工作目录，Python 3.8 的清理／异常格式化最终递归崩溃。隔离副本改为在 `finally` 中先恢复 cwd。
- [test_main.py:276](C:/Users/Lenovo/Documents/大创参考论文/rescopy/cocopyres/benchmark/benchmark/graph_method/tests/test_main.py:276)：全模型 CPU 测试构建模型后未 `.to('cpu')`；PyG Temporal 0.54.0 的 A3TGCN 在发现 GPU 时把 attention 参数初始化在 CUDA 上。正式训练入口已有 `.to(device)`，所以这是测试设置错误，不能据此断言正式 CPU 训练必然失败。隔离修正后，11 模型在两种设备上均完成 2 epoch。

## 对原 bug.md 的 17 项逐项判断

“已修复”指对应具体缺陷已找到实现及测试证据，不等于全部实验结果已经可信。

| 编号 | 原问题 | 本轮判断与证据 |
|---|---|---|
| 1 | DatasetLoader 不存在 | 已修复；可导入并加载真实 r0／region 数据 |
| 2 | 读取不存在的 rate/count 目录 | 已修复；分别映射 proportion／demand，4 组实际准备成功 |
| 3 | 只准备 company，默认 r0 不匹配 | 已修复；r0 两模式成功，7 粒度选项和源文件存在性通过；未全量生成 14 组 |
| 4 | 输出目录未创建 | 已修复；从缺失目录准备成功；V-003 是随后 torch.save 的独立兼容问题 |
| 5 | 丢弃 GRU 新权重 | 已修复；第二、第三快照使用前一快照返回的权重，测试通过 |
| 6 | `.data` 截断初始权重梯度 | 已修复；CPU／CUDA 层测试通过，真实训练初始权重梯度有限且非零 |
| 7 | 用测试集选择最优模型 | 直接选模逻辑已修复；实跑调用顺序为 train/validation 重复 3 次后 test 1 次；整体仍有 V-004 的目标重叠 |
| 8 | eval_dataset 未使用 | 已修复；每 epoch 验证，保存值等于三次验证损失最小值 |
| 9 | 各阶段设备不一致 | EvolveGCN-H 路径已修复；原始 CUDA runner／层测试通过，兼容副本完成 GPU 全流程 |
| 10 | 覆盖 seed 且不播种 | 已修复；seed 17 保留，两个真实 CPU 运行的指标和 4 份预测逐元素完全一致 |
| 11 | 预处理丢弃共现频率 | 已澄清数据语义并保存可观察权重；公开 Parquet 没有频率列，只能保留同上下文的重复行贡献，不能声称恢复论文频次 |
| 12 | 临时权重不注册／跨遍历累积 | 已修复；状态由 runner 显式传递、每个遍历重置，checkpoint 保存可学习初始权重、不保存瞬时演化状态 |
| 13 | 保存整个模型，跨设备不可移植 | 已改为 state_dict＋配置且有 map_location，但当前保存／加载仍被 V-002、V-003 阻断，不能判整项通过 |
| 14 | README 参数名不一致 | 已修复；文档与 CLI 使用 model_name，解析及文档测试通过 |
| 15 | Conda 创建命令错误 | 文档语法已修复为 conda create -n Job-SDF python=3.8；本轮使用现有环境，未新建环境 |
| 16 | hidden_dim 对 EvolveGCNH 不生效 | 按约定通过文档澄清：维度来自 window_size，不声称 hidden_dim 生效；未改变模型定义 |
| 17 | split docstring 返回值错误 | 已修复；文档与实现均返回 train、validation、test |

## 隔离兼容后的真实模型试跑

以下结果使用同一 r0 数据、seed 17、window_size 6、pred_length 3、3 epoch。仅修改 checkpoint 元数据表示和文件打开方式，模型公式、优化器、损失、窗口与 split 保持原实现。

| 模式／设备 | RMSE | MAE | 结论 |
|---|---:|---:|---|
| rate／CPU，运行 A | 0.291645907 | 0.275492571 | 流程完成 |
| rate／CPU，运行 B | 0.291645907 | 0.275492571 | 与 A 的指标和预测完全一致 |
| rate／CUDA | 0.291645907 | 0.275492571 | 流程完成 |
| count／CPU | 3793.204780 | 876.103180 | 流程完成 |
| count／CUDA | 3793.204780 | 876.103165 | 流程完成 |

每次保存了 checkpoint、4 个 pred、4 个 gold、metrics.json；重算保存文件的 RMSE／MAE 与报告值一致。每个训练遍历只有一次 optimizer step，三次训练均有有限且非零的 initial_weight 梯度。恢复在另一设备上也成功：rate 预测最大绝对差约 2.98e-8；count 约 0.0044，未要求不同设备逐位相同。

这些只有 3 epoch 的模型尚未证明预测能力。作为参照，“重复最后一个观测值”在同一测试切分上 rate RMSE 约 0.00134、count RMSE 约 925.26，均优于本次短训结果。不能把“能跑且有限”写成“复现论文效果”，更不能在修正 V-004 前将这些数字用于正式评估。

## 复核方式与交付

在仓库根目录运行：

```powershell
& 'D:/conda-envs/JOBSDF/python.exe' not_in_origin/verification_20260921/run_audit.py original
& 'D:/conda-envs/JOBSDF/python.exe' not_in_origin/verification_20260921/run_audit.py compat
& 'D:/conda-envs/JOBSDF/python.exe' not_in_origin/verification_20260921/run_audit.py real
& 'D:/conda-envs/JOBSDF/python.exe' not_in_origin/verification_20260921/minimal_reproductions.py
```

`original` 模式仅显式跳过已经复现的 Windows runner 崩溃项；报告失败由输出 JSON 的 `successful` 字段判断，脚本不将“完成核验”进程退出码当作“被测软件通过”。`compat`／`real` 模式在独立进程中载入保存的源码副本，将资源定位仍指向原数据目录；不覆盖原源码。复跑会更新本核验目录内的证据和同名试跑结果。

`isolated/main.diff` 是最小生产代码兼容建议；两个测试 diff 包含 cwd 清理、CPU placement 以及将故意损坏格式版本的 fixture 浮点元数据改成标量张量。它们只是隔离验证方案，并未应用到仓库主实现，亦未处理目标时间泄漏。

关键证据为 `original-unit-tests.json`、`compat-unit-tests.json`、`real-data-four-combinations.json`、`all-models-two-epochs.json`、`real-runs.json`、`cpu-repeatability.json`、`temporal-overlap.json` 和 `runs/`。前后源码 SHA-256 记录在 `source-sha256-before.json` 与 `source-sha256-after.json`。

原 OpenSpec 的 V-001“没有可用运行环境”在这台机器上已经解除。新的独立核验发现 V-002 至 V-005；不应把历史 verification.md 中的环境阻塞直接改写成“全部通过”。
