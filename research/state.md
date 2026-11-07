# 当前状态

更新时间：2026-11-07，Asia/Shanghai。
当前阶段：[P02](phases/P02/plan.md)，按用户接受的 [D037](decisions.md#d037-中期后图收益检验融合强度与跨粒度关系的路线候选) 恢复研究计划推进；阶段尚未验收结束。任务状态以阶段计划为准。
当前任务：P02-T006 已完成代码、实验、OpenSpec 独立验证和研究侧收尾，等待用户检查本地提交；P02-T009 由其他成员负责，本轮不介入。
当前执行者：Codex；正确基线 `91ea3d6df8360998d9d2b1ed36ab764322ee26f3`，新分支 `p02-t006-gru-lstm-v2`。
本次范围：仅实现并验证 P02/T006 的 E13 工作流和 GRU/LSTM 对比；不修改 T009。
本次 run：[p02-t006-gru-lstm-v2-20261107](runs/p02-t006-gru-lstm-v2-20261107/summary.md)。

## 恢复位置

- 最后完成步骤：代码入口、smoke、r0/count 成本样本、候选学习率和三 seed GRU/LSTM 对比完成；OpenSpec 独立验证 PASS 并归档。
- 已有研究证据：[P01 阶段汇总](analyses/p01-t008-stage-summary-20261018-01/report.md)、[T003 判定与诊断](reports/p02-t003-20261022-01/report.md)、[正式 run 材料核验](analyses/p02-t003-formal-artifacts-20261022-01/report.md)。既有任务验收保持原结论，新路线没有产生新实验结果。
- 结论边界：冻结条件下未检出同时通过自身与打乱对照的图收益；正式材料确认欠拟合，训练预算与尺度各自的因果作用尚未经新条件实验验证。自适应门控、边选择及跨粒度新图尚未实现或验证。
- 条件边界：本次只覆盖 [P02 新协议](phases/P02/protocol.md) `P2-effective-training-L6-H3-v1` 的 `r0/count` 预实验；不把结果推广到其他粒度或普遍模型排名。
- 委托状态：[DELEGATION](../DELEGATION.md) 为 `closed`；归档 verification 为 PASS。
- 产物保存位置：run 元数据、指标和摘要在 [v2 run](runs/p02-t006-gru-lstm-v2-20261107/summary.md)；OpenSpec 归档在 `openspec/changes/archive/2026-11-07-add-effective-temporal-training/`；训练 checkpoint 保留在本地运行目录，未 push 或远程备份。

## 下一可执行动作

检查工作树后创建本地提交；不 push、不创建 Pull Request，直到用户检查完成。

验收：严格 OpenSpec validation PASS；归档 verification PASS；提交父基线仍为 `91ea3d6`。

## 相关材料与未决事项

- 执行设备尚未选定，Mac／Windows 的已知配置与限制见方案报告；协议已给出 CPU 资源档位和停止线。设备实时可用性与新配置耗时留到 T006 启动前实测，不冒称已经测得，不阻止本次方案交接。
- 中期报告：[初稿](reports/midterm-20261023-01/report.md)与[材料来源说明](reports/midterm-20261023-01/README.md)；D035 的报告截点继续保留，新路线是后续安排。
- PPT：[第 11、12 页修改指导](reports/midterm-ppt-future-plan-20261031-01/revision-guide.md)已交付另一个对话，实际编辑及渲染验收未在研究记录中确认；不作为启动 T005 的前置条件。
- 题目保留建议 [D036](decisions.md#d036-中期报告保留现有题目的建议) 仍为 `proposed`，本次路线接受不自动升级为题目决定。
