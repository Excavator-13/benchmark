# 当前状态

更新时间：2026-10-19。
当前阶段：[P01](phases/P01/plan.md) 已完成；[P02](phases/P02/plan.md) 进行中，任务状态以 P02 计划为准。
当前工作：P02-T001（实现骨架与打乱图）已 `done`——`add-graph-value-skeleton` 归档 [`Verdict: PASS`](../openspec/changes/archive/2026-10-19-add-graph-value-skeleton/verification.md)，研究侧按 [D025](decisions.md#d025-p02-t001-实现研究侧验收与委托回收) 接受实现就绪，[DELEGATION](../DELEGATION.md) 已 `closed`。P02-T002（开发对照运行）未启动，等待用户授权。
当前执行者：研究侧；无在跑实验、无外部执行。
本次授权范围：研究侧记录维护、委托回收，以及用户 2026-10-19 明确要求的 commit 与 push；不包含 P02-T002 正式运行、封存或恢复核验。
本轮 run：无。

## 恢复位置

- 2026-10-19：T001 实现与 `graph-value-skeleton` 主规格已归档并通过独立验证（基准 commit 加 8 个脏文件指纹核对一致）；研究侧回收完成，无正式 run 写入 `research/runs/`。后续由 P02-T002 接手，正式比较前须先统一确认一次成本（P02 计划 §4）。
- 保存事实见[索引](archives/index.md#p02-t001-骨架实现证据2026-10-19)；未封存与备份未核验的条目保持原状，本轮不追补核验。

## 下一可执行动作

- P02-T002 需用户另行授权。启动时按 P02 计划 §4 固定方法轴（自身/真实图/打乱图）、seeds `0,1,2`、`r0`/`region`/`r2`，同 seed 至少两次重复；入口命令与产物契约见 [README §4.6](../README.md) 与[实现说明](../openspec/changes/archive/2026-10-19-add-graph-value-skeleton/implementation-notes.md)，正式 run 写 `research/runs/<run-id>/`（`--purpose formal`），开发冒烟仅写 `scratch/`。
- 预算与冻结项只能在本阶段正式比较开始前统一调整并记录，不得按中间结果修改；发布图构建时间未知，图相关结论只作固定评测期证据，严格历史/跨时间主张仍缺时间相符的图证据（[D015](decisions.md#d015-发布图使用范围与重建时机)）。

## 待处理事项

- [D005](decisions.md#d005-补存分层分析的可复查过程)（`proposed`）：旧 EvolveGCN 两个 seed 的分层过程、训练需求占比与活跃度交叉分布仍未补存；新 baseline 部分已补。
