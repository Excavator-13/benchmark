# P02-T006 v2 r0/GRU seed 1/b 执行记录

类型：experiment。所属任务：P02-T006。
日期：2026-11-28，Asia/Shanghai。执行者：本会话 Codex，Windows 11 本机 CPU。
科学版本：`P2-effective-training-L6-H3-v2`。

## 执行结果

按冻结 selection 使用 GRU、seed 1、学习率 `1e-3`、confirmation/b。formal fresh preflight 全部通过，沿用原 batch `p02-t006-effective-20261108-01` 和 ledger `f93290f346bc47e9914be45203c5edc3`。轨迹正常完成 200 epochs / 3,800 updates，状态 `completed`，拟合未使用测试标签。

第 10 轮成本门通过。样本时间为 16.31595 秒，epoch 6–10 完整耗时中位数为 0.51153 秒，完整拟合保守估计为 280.1818 秒。单次和批次预算投影均通过。

验证 MSE 为 202,343.2705，MAE 为 112.3347，与 seed 1/a 的验证摘要指标相同。完整配对预测差和归一化 MAE 门仍要由后续 compare/diagnose 工作流判定。

## 证据与累计记账

- formal fresh preflight：[JSON](../p02-t006-execution-20261108-01/preflight-r0-gru-v2-20261128-08.json)
- 正式 run：[summary](../../runs/p02-t006-r0-gru-v2-s1-b-20261128-01/summary.md)、[report](../../runs/p02-t006-r0-gru-v2-s1-b-20261128-01/report.json)、[cost](../../runs/p02-t006-r0-gru-v2-s1-b-20261128-01/cost.json)、[provenance](../../runs/p02-t006-r0-gru-v2-s1-b-20261128-01/provenance.json)、[history](../../runs/p02-t006-r0-gru-v2-s1-b-20261128-01/history.json)
- 原 batch ledger：[ledger.json](../p02-t006-execution-20261108-01/ledger.json)

截至本 run 完成，ledger measured/replayed 累计 722.8313 秒，保守预算扣除 900 秒，有效累计 1,622.8313 秒，剩余 41,577.1687 秒。

自动生成的 summary 末尾含 “Development evidence” 通用提示语，与 `purpose=formal`、完整 protocol controls 和机器报告元数据冲突；以 formal run 身份字段为准，模板提示不代表 development 运行。

## 当前边界与下一步

seed 1/b 已完成。仍需运行 seed 2/b，之后再用冻结的 selection、三个 a/b 配对和既有 Ridge 证据执行 section-5 readiness 诊断。只有诊断门通过后才允许生成四窗口测试报告。
