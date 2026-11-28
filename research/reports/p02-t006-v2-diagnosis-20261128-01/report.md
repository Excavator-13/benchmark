# P02-T006 v2 r0/GRU section-5 readiness 诊断

类型：saved-evidence diagnosis。所属任务：P02-T006。
日期：2026-11-28，Asia/Shanghai。执行者：本会话 Codex。
对象：冻结的 v2 r0/GRU selection、seed 0/1/2 的 a/b 轨迹和已有 Ridge 验证证据。

## 结论

section-5 诊断结果为 `fail`，`learning_ready=false`。**唯一未通过门是预算末段稳定性。** 每个 seed 的 `(b160-b200)/max(1e-12,b160)` 为：seed 0 `0.1612265`（16.12%），seed 1 `0.1540161`（15.40%），seed 2 `0.1798565`（17.99%）。协议要求至少 2/3 个 seed 不超过 1%，本次 0/3 通过。结果仍明显受延长预算影响，不能进入四窗口测试。

其余已评估门均通过：三条 a 轨迹都有确定学习，验证 MSE 下降及超过 Zero 基线的验证 MAE 改善达到要求；六条轨迹完整且数值有限；三个 seed 的 a/b 对比均通过，预测最大绝对差和归一化 MAE 差都为 0；冻结 selection、数据、节点、协议和 Ridge 来源身份相符。diagnostic 报告记录 `test_scores_used=false`。

## 证据与记账

- 机器诊断：[diagnose JSON](../p02-t006-execution-20261108-01/diagnose-r0-gru-v2-20261128-01.json)
- 冻结配置：[selection JSON](../p02-t006-execution-20261108-01/blocks/p02-t006-r0-gru-v2-20261128-01/selection.json)
- a/b 运行记录：[seed 0/1/2 轨迹目录](../)
- Ridge 来源：[Ridge validation JSON](../p02-t006-execution-20261108-01/ridge-r0-validation.json)
- 累计预算：[batch ledger](../p02-t006-execution-20261108-01/ledger.json)

截至诊断完成，原 batch ledger 中 measured/replayed 合计 784.5547 秒，保守扣除 900 秒，有效累计 1,684.5547 秒，剩余 41,515.4453 秒。diagnose 阶段计入约 0.5222 秒。本诊断没有读取测试期数据。

首次调用显式传入 ledger 时，CLI 将 batch ID 默认成 `p02-t006` 并在 batch 身份校验时拒绝，未开始诊断。正式诊断调用省略该参数，流程从输入 runs 内绑定的原 ledger/batch 身份进行记账并成功产出报告。

## 停止点与下一步

按 [P02 v2 协议](../../phases/P02/protocol-v2.md) 的冻结预算规则，本次 v2 r0/GRU 块止于预算末段门失败。没有启动测试、图比较、其他模型/数据组或额外轮数。T006 恢复为 `blocked`。任何改变固定预算或科学条件的后续尝试，都需要先形成并接受版本化研究决定；不能由本次软件或 saved-evidence 诊断自动扩展。
