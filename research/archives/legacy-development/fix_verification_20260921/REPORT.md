# 修复后的验证结果

2026-09-21：本次已直接修改正式源码，V-002 至 V-005 已修复。另修复实跑发现的 EvolveGCN-H TopK 同分节点在 CPU／CUDA 上选择不同的问题。工作基线提交为 `51cd0e3`，改动尚未提交。

## 修改

- `benchmark/graph_method/main.py`：checkpoint 格式升级为 2，验证损失保存为 float64 标量张量，继续使用 `weights_only=True`。旧格式／损坏文件给出 `CheckpointError` 和重跑提示。checkpoint、pred、gold 使用 Python 文件对象读写，支持旧版 PyTorch 的 Windows 中文路径。
- 时间切分在两个边界各省略 `pred_length - 1` 个窗口，保留名义测试期及验证快照数量，从训练数中扣除间隔。默认 36 个月、输入 6、预测 3 时，由 23/1/4 改为 **19/1/4**，另省略 4 个窗口。历史不足会在训练前报错。
- `models/evolvegcnh.py`：保留可学习的 TopK 投影、tanh 分数、加权特征和梯度；同分时按节点顺序稳定排序，准确选择 `in_channels` 个节点形成 GRU 输入。避免大量 count 分数饱和后，不同设备选择不同节点；也避免浮点比例向上取整后多选节点再裁切。
- 测试修复：临时目录删除前先恢复 cwd；CPU 模型测试显式 `.to('cpu')`。新增目标时间隔离、预测起点信息可用性、边界间隔不足、单步预测、中文路径完整输出、旧格式读取、元数据校验、GPU→CPU checkpoint、饱和 TopK 跨设备等回归测试。
- README、服务器指南和两份 OpenSpec 规格同步了新切分、checkpoint 格式与 TopK 行为。

## 验证

环境使用现有 `D:/conda-envs/JOBSDF/python.exe`：Python 3.8.20、PyTorch 1.13.1 / CUDA 11.7、PyG 2.4.0、PyG Temporal 0.54.0，RTX 4060 Laptop 8 GiB。其余环境版本与先前核验一致，未安装或修改全局依赖。

| 检查 | 结果 |
|---|---|
| `python -m unittest discover -s benchmark/graph_method/tests -v` | **176 项：172 通过、4 跳过、0 失败／错误**，见 `unit-tests.log` |
| `openspec validate --specs --strict --no-interactive` | 3 份规格全部通过，见 `openspec-validation.log` |
| r0 真实 Parquet 重新准备、加载 | rate／count 均通过，2,335 节点、60,804 边、28 个原始窗口 |
| 正式 CLI 子进程，仓库外 cwd，真实中文输出路径 | 5 次运行完成：rate CPU 两次、count CPU 一次、rate CUDA 一次、count CUDA 一次；每次仅 3 epoch |
| 输出完整性 | 每次 checkpoint.pt、4 个 pred、4 个 gold、metrics.json 可加载；重算指标与保存指标完全一致，gold 对应新切分的测试标签 |
| checkpoint 跨设备恢复 | 每个真实运行都在另一设备重新载入并评估；参数映射正常，预测通过数值容差检查 |
| CPU 可复现性 | 同 seed 的两次 rate 运行指标和全部预测逐元素相同，见 `repeatability.json` |
| 目标月份及可用历史 | 实际窗口标签编码检查通过，目标集合不相交，前一集合标签在后一集合首次预测时已可观测，见 `target-periods.json` |
| Git 补丁格式 | `git diff --check` 通过 |

4 个跳过项是 2 个全部真实数据的 opt-in 集成用例，以及 2 个要求 CUDA 不可用的错误路径用例。本机有 CUDA，实际 CUDA 测试均执行。本次仅重新准备／训练 r0，没有执行公司等大粒度或 500 epoch 论文复现。

新的目标月份：

| 集合 | 时间范围 |
|---|---|
| train | 2021-07 至 2023-03 |
| validation | 2023-04 至 2023-06 |
| test | 2023-07 至 2023-12 |

## TopK 额外问题的定位证据

第一次正式 CLI 验证中，一个 count checkpoint 在 CPU 和 GPU 上的预测最大绝对差达到 33,644.74。`pooling-probe.json` 记录同一个图有 57 个节点的分数都为 1，但两种设备选出的节点不同；稳定排序的隔离探针把该 checkpoint 的差异降到 0.0254。随后将稳定选择正式写入本地模型，并重新执行了完整测试与新 CLI 训练。

最终实跑使用不同 CPU／CUDA seed（202609221／202609222）区分结果目录，所以不能直接把两次训练的指标当作同 seed 的设备比较。跨设备检查针对的是每次运行自己的同一个 checkpoint：rate 最大绝对预测差约 2.98e-8；count 最大约 0.426，满足 `rtol=1e-4, atol=1e-2`。不同设备的浮点计算不保证逐位相同；新增饱和同分测试要求节点汇总本身在 CPU／GPU 上完全相同。

最终证据在 `cli-runs.json`、`final-verification.log` 和 `runs/final-*`。较早的 `verification.log`、`runs/count-cpu` 等保留了定位过程，不能作为最终结果。`source-hashes.json` 记录最终模型／入口／加载器版本。

## 使用

从仓库根目录快速自查，例如使用一个尚未占用的 seed：

```powershell
& 'D:/conda-envs/JOBSDF/python.exe' benchmark/graph_method/prepare_graph_data.py --data_name r0 --mode rate
& 'D:/conda-envs/JOBSDF/python.exe' benchmark/graph_method/main.py --data_name r0 --mode rate --model_name EvolveGCNH --device cuda:0 --seed 202609223 --num_epochs 3
```

完整小规模核验脚本为 `verify_fixed.py`，直接运行正式 CLI，不修改／替换训练函数。为保护已有结果，脚本拒绝覆盖先前运行目录；再次使用时需给它更换 seed 和结果标签。

**旧 checkpoint 需要重新训练。旧时间切分和旧 TopK 行为下的指标不能与本次结果直接比较。** 本轮证明修复后的运行正确性与小规模稳定性；3 epoch 的输出不代表模型已收敛或论文效果已复现。
