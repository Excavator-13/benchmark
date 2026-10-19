# P02-T002 执行记录与恢复入口

2026-10-19 用户授权启动 T002，包括成本试跑、冻结配置下的正式对照运行、产物核验与研究记录维护。不包含封存、commit、push，也不扩展到 T003/T004。

## 范围与停止点

按 [P02 计划](plan.md) §4：`r0/region/r2` × 模型 seed `0,1,2` × `self/graph/shuffled(0,1,2)` × 重复 `a,b`，共 90 次正式训练。200 epoch、原始 count、GRU hidden 32、Adam 与验证 MSE 选模沿用实现冻结值。完成全部运行、逐次指标重算、45 对重复比较、18 组三图平均后验收 T002；不根据中间测试成绩调整预算或范围。

## 本机准备

- 本机为 Windows；首次检查仅发现 Python 3.14.2（torch 2.10.0+cpu、NumPy 2.4.2、pandas 3.0.5，缺 PyArrow）和 Python 3.10.11，未找到可直接调用的 conda。验收时的 macOS 环境不在本机。
- 在仓库忽略目录建立独立 Python 3.11 环境，安装 `benchmark/graph_value_skeleton/requirements.txt` 锁定的四项依赖。不修改系统 Python。
- 环境差异作为新批次身份保存；本批次内部重复必须保持同一依赖、设备与源码。不将其称为原 macOS 数值复现。
- Windows 无 `resource.getrusage`；原入口如实记录 `unsupported_platform`。批次监控另存 worker 的 Windows `peak_wset` 和进程树采样 RSS，不改计算源码。
- 入口内部任务常量仍为实现任务 `P02-T001`；本清单将本批次 run 明确关联至研究任务 `P02-T002`，不为记录标签修改冻结实现。

## 保存与检查

正式 run 使用 `research/runs/<run-id>/`；预检、成本试跑与原始检查报告先写 `scratch/`。现有检查器仅允许 scratch/temp 输出，成功报告按字节复制到 `research/reports/` 持久保留，记录原输出路径和 SHA256；不更改检查器策略。

批次脚本为 [t002_batch.py](t002_batch.py)，批次 ID 为 `p02-t002-20261019-01`。预检、运行清单、成本和检查结果位于 [批次报告目录](../../reports/p02-t002-20261019-01/)。已有成功或失败 run 均不覆盖；恢复只跳过已有且成功并通过核验的执行，失败项须使用新身份。

仓库根目录命令（PowerShell）：

```powershell
& .\.venv-pinned\Scripts\python.exe research/phases/P02/t002_batch.py preflight --batch p02-t002-20261019-01
& .\.venv-pinned\Scripts\python.exe research/phases/P02/t002_batch.py cost --batch p02-t002-20261019-01
# 成本审阅通过并保存 cost-confirmation.json 后执行：
& .\.venv-pinned\Scripts\python.exe research/phases/P02/t002_batch.py formal --batch p02-t002-20261019-01
```

不在已有控制器运行时重复启动。`controller.json` 保存控制器 PID，`progress.json` 保存最近 run；结束状态以 `controller-status.json`、各 run `status.json` 和检查报告联合判断。正式完成需 `progress.json` 为 `complete` 且全部 153 份检查报告 `ok`，再由研究侧验收并更新任务状态。

## 当前恢复点

用户于 2026-10-19 要求暂停并总结。成本试跑已结束，真实 r2 打乱 seed 0 的交换尝试预算耗尽，批次控制器与等待调度均已退出。T002 `blocked`，正式训练尚未开始。证据见[批次报告](../../reports/p02-t002-20261019-01/report.md)。本轮不再运行；用户恢复后按[修复交接](t002-repair-handoff.md)处理。旧批次不重启，修复后使用新批次、新预检和新成本确认；仍保留原训练预算与验收标准。
