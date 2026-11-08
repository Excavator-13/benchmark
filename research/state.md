# 当前状态

更新时间：2026-11-08，Asia/Shanghai。
当前阶段：[P02](phases/P02/plan.md)，阶段尚未验收结束。
当前任务：P02-T006，状态与验收以阶段计划为准；P02-T009 由其他成员负责，本轮不介入。
当前执行者：Codex 研究侧，完成软件委托回收；本轮未启动实验，其他外部进程未核验。
本次授权范围：按用户“OpenSpec 那边做完了，你看看”核对交付并完成约定的研究侧收尾；不执行 apply、verify、fix、archive 或正式实验。
本轮 run：无；旧 r0 预实验保留原身份，当前适用限制见[软件收尾报告](reports/p02-t006-software-closeout-20261108-01/report.md)。

## 恢复位置

- 最后完成步骤：核对归档独立 PASS 与当前文件身份，按 [D039](decisions.md#d039-t006-软件修复研究侧验收与完成状态纠正) 接受软件就绪；[DELEGATION](../DELEGATION.md) 已回收关闭。
- 当前入口：[README §4.7](../README.md#47-p02-effective-recurrent-entry-benchmarkmultivariate_time_series)；软件证据见[归档 verification](../openspec/changes/archive/2026-11-08-fix-effective-temporal-training-acceptance/verification.md)。初始 implementation-notes 的过时描述及使用顺序见收尾报告。
- 剩余工作：在 [P02 协议](phases/P02/protocol.md) 下取得真实成本、有限选择、学习有效性和独立重复证据，完成适用的测试报告／重算及研究验收；本次软件就绪不放行 T007。
- 结论边界：旧 r0 预实验不能证明完整协议下的有效学习或模型排名；既有图收益／欠拟合结论与历史身份不变，仍不能据此宣称新训练条件已有图收益。
- 保存事实：实现／验收交付与旧实验材料分别见[归档索引](archives/index.md#p02-t006-软件修复交付与旧预实验限制2026-11-08)。

## 下一可执行动作

动作：准备首个 r0/GRU 执行块的准确指导与输入／条件清单，使用现行 CLI，不直接复制原 apply 交接里的过时命令。
前置条件：明确执行设备、真实数据身份、兼容 Ridge 验证证据、邻居分组来源及新 batch／ledger 的计费范围；要求和逐块顺序见[收尾报告 §4](reports/p02-t006-software-closeout-20261108-01/report.md#4-尚未完成的研究工作与下一动作)。
验收：指导可据文件恢复执行，明确预检、成本门、失败停止及回传材料；正式训练须有相应授权，软件回收本身不启动训练。

## 相关事项

- 真实设备是否满足资源门槛、实际训练耗时和原生 Windows 路径未在本轮核验；旧 Windows 完整实验产物仍未回收核验。
- [D036](decisions.md#d036-中期报告保留现有题目的建议) 仍为 proposed；本次不改变题目或中期报告截点。
