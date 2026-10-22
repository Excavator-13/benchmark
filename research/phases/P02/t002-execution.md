# P02-T002 执行记录与恢复入口

2026-10-19 用户授权启动 T002，包括成本试跑、冻结配置下的正式对照运行、产物核验与研究记录维护。不包含封存、commit、push，也不扩展到 T003/T004。

## 范围与停止点

按 [P02 计划](plan.md) §4：`r0/region/r2` × 模型 seed `0,1,2` × `self/graph/shuffled(0,1,2)` × 重复 `a,b`，共 90 次正式训练。200 epoch、原始 count、GRU hidden 32、Adam 与验证 MSE 选模沿用实现冻结值。完成全部运行、逐次指标重算、45 对重复比较、18 组三图平均后验收 T002；不根据中间测试成绩调整预算或范围。

## 执行时环境准备（Windows 历史记录）

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

## 收尾与后续入口

2026-10-22：已按 [D031](../../decisions.md#d031-p02-t002-研究侧验收与收尾)完成研究侧交付验收；当前入口为 [T002 收尾报告](../../reports/p02-t002-closeout-20261022-01/report.md)，任务状态以 [P02 计划](plan.md)为准。本文上述命令及环境描述保存原执行接口，不是当前启动指令；不要重复运行旧控制器。

后续经用户授权进入 T003，直接利用已交付 checks 中的指标作门槛判定及诊断；本轮未启动 T003/T004，不自动重训、访问外部执行根或改动科学配置。材料位置、字节转换和完整数组的访问限制见收尾报告；提交/保存事实见[索引](../../archives/index.md#p02-t002-收尾交付与-pr-合入2026-10-22)。

## 历史证据入口

- [原成本失败](../../reports/p02-t002-20261019-01/report.md)及[修复交接](t002-repair-handoff.md)：D026 的依据。
- [修复后成本与暂停](../../reports/p02-t002-20261020-01/report.md)：D027 的依据。
- r2 旧中断批次：D028 对应的旧现场按原执行记录留 D；独立旧报告未随当前 Git 交付，已知中断事实见 [r2 重启报告](../../reports/p02-t002-r2-20261020-02/report.md)，不将缺失路径作为恢复入口。
- [r2 检查点验收与重启](../../reports/p02-t002-r2-20261020-02/report.md)：D029 的执行记录。
- [region/r0 组合交接](../../reports/p02-t002-remaining-20261022-01/report.md)：D030 的执行记录。
