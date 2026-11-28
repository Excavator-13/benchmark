# P02-T006 v2 软件就绪验收与委托回收

类型：software acceptance / handoff。所属任务：P02-T006。
核对日期：2026-11-28，Asia/Shanghai。执行者：本会话研究侧 Codex。
对象：`extend-effective-training-budget-v2` 归档交付；本轮只读核对 OpenSpec 证据及当前身份，不重跑软件验证或正式实验。

## 验收结论

**接受软件就绪，关闭 OpenSpec 委托。** 活跃变更目录已移除，归档 `2026-11-28-extend-effective-training-budget-v2` 存在，最终 [独立验证报告](../../../openspec/changes/archive/2026-11-28-extend-effective-training-budget-v2/verification.md) 的 Verdict 为 `PASS`。归档任务清单 12 项均完成。验证报告记载 OpenSpec strict validation 通过，修复后 68 项定向回归通过，并复用适用的 151 项 recurrent suite 与 287 项 baseline suite 证据。

委托结束判据的第二部分也满足。报告标注验证基准为 `4993778f0fb2a11cbfc0339ad265f489479a1d3c` 加当时的未提交实现、测试、README 与任务更新。只读比对显示 v2 主协议、继承的 v1 协议、README、改动中的 CLI 和资源账本代码、CLI 回归测试，以及归档前的五个 OpenSpec 变更工件，均与验证快照中的内容指纹一致。验证状态文件 SHA-256 为 `8ccfc900c933a9337e155ebf6cfbb18825b631ad73bc9dd1688f3d8a7d5456cf`，与验证报告记录相符。归档时同步的主规格包含该变更内容；研究协议身份保持不变。

因此，软件交付满足 v2 软件交接要求，可以作为后续研究执行的软件基线。验证使用合成与临时输入，不能证明真实数据上的学习有效性、真实机器成本或 T006 研究验收。

## 研究侧边界与下一步

P02-T006 仍未完成，状态保持 `blocked`。解除当前执行阻塞需按 v2 规则在正式执行前，将 900 秒保守准备成本扣除登记到原 batch/ledger，完成所选机器上的新预检及首候选真实成本门，再以新 v2 身份从初始化开始训练。v1 失败结论、旧预算消耗和身份继续保留；本轮没有修改真实 ledger、启动真实数据运行、放行测试或介入 T009。

后续研究仍须完成 v2 规定的有限矩阵、学习有效性、a/b 重复和适用的四窗口测试与可重算证据，并逐块按研究协议验收。软件 PASS 不替代这些判据。

## 证据范围与保存

- OpenSpec 独立验证：[verification.md](../../../openspec/changes/archive/2026-11-28-extend-effective-training-budget-v2/verification.md)
- 归档变更和任务清单：[归档目录](../../../openspec/changes/archive/2026-11-28-extend-effective-training-budget-v2/)
- 科学条件：[P02 v2 协议](../../phases/P02/protocol-v2.md)
- 研究任务状态：[P02 计划](../../phases/P02/plan.md)

实现与验收记录当前在本机 Git 工作区，未提交；封存、异地备份与恢复核验未做。
