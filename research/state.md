# 当前状态

更新时间：2026-10-18。
当前阶段：[P01](phases/P01/plan.md) 已完成；[P02](phases/P02/plan.md) 已启动，任务状态以 P02 计划为准。
当前工作：P02-T001（实现骨架与打乱图）已按 [AGENTS.md](../AGENTS.md) 在 [DELEGATION](../DELEGATION.md) 登记为 `open`，变更名 `add-graph-value-skeleton`，等待 OpenSpec 侧 propose → apply → verify → archive；P02 计划中 T001 仍为 `todo`，待归档 PASS 且研究侧接受实现就绪后再改状态。数据/切分/seeds/预算/门槛与骨架范围见 [D023](decisions.md#d023-t008-阶段验收与-p02-骨架范围)。
当前执行者：OpenSpec 侧（P02-T001 实现）；研究侧无在跑实验、无外部执行。
本次授权范围：研究侧记录维护与委托登记；不包含代跑 propose/apply/verify/archive、编辑实现、P02 正式运行或封存。
本轮 run：无。

## 恢复位置

- 2026-10-18：P01 收尾于[阶段汇总](analyses/p01-t008-stage-summary-20261018-01/report.md)与 [D023](decisions.md#d023-t008-阶段验收与-p02-骨架范围)；[P02 计划](phases/P02/plan.md)已建立，P02-T001 实现委托登记为 `open`（[DELEGATION](../DELEGATION.md)），变更目录尚未创建，研究侧未调用 OpenSpec 流程。
- 保存事实见[索引](archives/index.md)；未封存与备份未核验的条目保持原状，本轮不追补核验。

## 下一可执行动作

- 在 OpenSpec 侧以 `add-graph-value-skeleton` 执行 propose（范围按 P02 计划 §2 与 D023 的冻结骨架口径），随后 apply → verify-change → archive-change；该流程不读写 [DELEGATION](../DELEGATION.md)，研究侧也不代跑。
- 变更归档后，研究侧只读核对结束判据：`openspec/changes/add-graph-value-skeleton` 已不存在，`openspec/changes/archive/*-add-graph-value-skeleton/verification.md` 为 PASS 且与当前实现一致；完成即按 [DELEGATION](../DELEGATION.md) 的"研究侧收尾"回收并关闭指针。未完成只提醒用户。
- P02 冻结配置在正式比较开始前不得按中间结果修改；改冻结项先记录再运行。图相关结论只作固定评测期证据，严格历史/跨时间主张仍缺时间相符的图证据（[D015](decisions.md#d015-发布图使用范围与重建时机)）。

## 待处理事项

- [D005](decisions.md#d005-补存分层分析的可复查过程)（`proposed`）：旧 EvolveGCN 两个 seed 的分层过程、训练需求占比与活跃度交叉分布仍未补存；新 baseline 部分已补。
