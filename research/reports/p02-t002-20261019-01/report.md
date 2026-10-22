# P02-T002 批次 p02-t002-20261019-01

任务：P02-T002。用户于 2026-10-19 授权成本试跑、冻结开发矩阵的 90 次正式训练、核验和研究记录维护；未授权封存、commit/push 或 T003/T004。执行脚本：[t002_batch.py](../../phases/P02/t002_batch.py)；冻结条件与恢复命令见[执行入口](../../phases/P02/t002-execution.md)。

## 环境与数据预检

[preflight.json](preflight.json) 为 `ok`，记录实际解释器、四项主依赖版本、源码 SHA256 与 Git 基准、三组发布 demand/graph 文件哈希及节点断言。[manifest.json](manifest.json) 固定 90 个唯一 run ID。初次预检脚本错误地假定 namespace 包存在 `benchmark/__init__.py`，在训练前失败；修正编排脚本后通过。原失败保留在 `preflight-attempt1.json`；冻结计算源码未修改。

本批次为 Windows、Python 3.11.17、torch 2.14.1+cpu（包元数据为 2.14.1）、NumPy 1.26.4、pandas 2.2.3、PyArrow 17.0.0。历史验收环境为 macOS，故本批次是新环境内的受控比较，不声称跨机器逐位复现。官方 wheel 和 Python 发行包下载时核对发布方 SHA256；系统 Python 与旧 JOBSDF 环境未修改。

## 环境验证范围与差异

执行六个现有测试模块：`test_model`、`test_training`、`test_graph_mapping`、`test_shuffle`、`test_p01_identity`、`test_metrics`。原始日志：[environment-tests.log](environment-tests.log)。57 项中 55 项通过，两项失败保留原状，未改测试或冻结实现：

1. `CpuRuntimeTest.test_real_cpu_forward_backward_without_graph_extensions`：CPU 前向/反向已完成，最后的环境断言要求版本字符串严格等于 `2.14.1`；Windows CPU wheel 返回 `2.14.1+cpu`，`torch.version.cuda=None`。
2. `EncoderTest.test_window_and_split_state_reset`：同形状的状态复位严格相等；单窗口与双窗口合批预测的逐位相等断言失败。诊断最大绝对及归一化差均为 `2.9802322387695312e-08`，小于已有 `1e-6` 数值口径；同形状独立调用预测严格相等。见 [environment-diagnostics.json](environment-diagnostics.json)。这是批量形状改变的舍入差异，未发现跨窗口状态泄漏；正式同条件重复仍须逐对通过原检查器。

这不是“57 项全部通过”。成本试跑与正式同 seed 重复须在原入口及原检查器下继续验证；若超出协议容差或任何检查失败，停止批次并保留失败证据。

## 运行与验收

成本试跑已结束：r0/self 成功，r2/shuffled(seed 0) 在打乱阶段失败；正式训练 0/90。控制器及等待调度均停止，状态见 [controller-status.json](controller-status.json) 和 [scheduler.json](scheduler.json)。本批次未生成成功的 `cost.json` 或 `cost-confirmation.json`，不得启动正式矩阵。

r0 的 200 epoch 训练成功，入口总耗时 251.35 秒，含启动的端到端耗时 257.58 秒；进程树 RSS 采样峰值 448,540,672 bytes，worker 生命周期 PeakWorkingSetSize 407,105,536 bytes。[指标重算](cost-evidence/cost-r0-recompute.json) 为 `ok`。该运行是成本证据，不算正式对照。

r2 在约 211.89 秒后失败：上下文 `[12]` 在 2,240,800 次尝试内仅成功 194,445 次，未达到 224,080 次目标。未进入训练；进程树 RSS 采样峰值 665,735,168 bytes。[失败记录](cost-evidence/p02-t002-20261019-01-cost-r2-shuffled0-s0-cost/failure.json)和[终端日志](cost-evidence/p02-t002-20261019-01-cost-r2-shuffled0-s0-cost.log)保留。不能将失败当作打乱对照，也不能用于收益判定。

关键成本/失败记录与执行源码副本已从 scratch 按字节复制到 `cost-evidence/`，清单为 [cost-evidence-manifest.json](cost-evidence-manifest.json)。r0 的完整预测仍在原 scratch 成本目录，尚未持久化为正式 run；不对它提出正式科学结论。原失败现场不覆盖，后续修复使用新批次。

下一步是[实现修复交接](../../phases/P02/t002-repair-handoff.md)。本机 OpenSpec CLI 1.4.1 不支持技能前置要求的 `context --json`，本轮未创建变更，委托未开启。研究侧候选建议见 D026。最终仍需 90 份正式重算、45 份重复比较、18 份打乱图汇总均为 `ok`，才能接受 T002 完成。

原入口在 Windows 上的峰值内存为 `unsupported_platform`；编排器以 Windows `GetProcessMemoryInfo` 记录每个观察到的 PID 的生命周期 PeakWorkingSetSize，以及每 0.5 秒采样的进程树 RSS 峰值。后者是采样值，不冒称精确并发峰值。

T002 不做图收益门槛判定；收益与诊断属于 T003。发布图构建时间未知，结论范围继续受 D015 限定。

## 用户暂停与保存状态

2026-10-19 用户要求暂停并总结。成本控制器与等待调度均已退出；不自动恢复或重试。任务仍因真实图打乱问题 `blocked`，恢复位置由研究 state 与交接指向。

批次环境、编排脚本、90 个预定身份、预检、诊断、成本/失败证据已保存到本机；没有正式 run、没有模型收益验收、没有封存、commit 或 push。产物提交与备份状态见[索引](../../archives/index.md#p02-t002-成本预检批次2026-10-19)；未核验远端恢复。
