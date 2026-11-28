# P02-T006 v2 r0/GRU seed 0/b 执行记录

类型：experiment。所属任务：P02-T006。
日期：2026-11-28，Asia/Shanghai。执行者：本会话 Codex，Windows 11 本机 CPU。
科学版本：`P2-effective-training-L6-H3-v2`。

## 执行结果

按冻结 selection 使用 GRU、seed 0、学习率 `1e-3`、confirmation/b。formal fresh preflight 全部通过，沿用原 batch `p02-t006-effective-20261108-01` 和 ledger `f93290f346bc47e9914be45203c5edc3`。轨迹完成 200 epochs / 3,800 updates，状态 `completed`，拟合未使用测试标签。

第 10 轮成本门通过。样本时间为 18.76584 秒，epoch 6–10 完整耗时中位数为 0.24869 秒，完整拟合保守估计为 148.9532 秒；单次投影及剩余批次预算投影均通过。

验证 MSE 为 206,599.6338，MAE 为 109.6180，与 seed 0/a 的保存指标完全相同。完整的 a/b 预测差和归一化 MAE 重复门尚未运行，不在此单凭相同指标宣称配对通过。

## 证据与累计记账

- formal fresh preflight：[JSON](../p02-t006-execution-20261108-01/preflight-r0-gru-v2-20261128-07.json)
- 正式 run：[summary](../../runs/p02-t006-r0-gru-v2-s0-b-20261128-01/summary.md)、[report](../../runs/p02-t006-r0-gru-v2-s0-b-20261128-01/report.json)、[cost](../../runs/p02-t006-r0-gru-v2-s0-b-20261128-01/cost.json)、[provenance](../../runs/p02-t006-r0-gru-v2-s0-b-20261128-01/provenance.json)、[history](../../runs/p02-t006-r0-gru-v2-s0-b-20261128-01/history.json)
- 原 batch ledger：[ledger.json](../p02-t006-execution-20261108-01/ledger.json)

截至本 run 完成，ledger measured/replayed 累计 595.4214 秒，保守预算扣除 900 秒，有效累计 1,495.4214 秒，剩余 41,704.5786 秒。

自动生成的 summary 末尾含 “Development evidence” 通用提示语，与 `purpose=formal`、完整 protocol controls 及机器报告元数据冲突；此处以正式 run 的机器身份字段为准，模板提示不代表 development 运行。

## 当前边界与下一步

目前 seed 0/b 已完成，但 seed 1/b、seed 2/b、完整 section-5 readiness 诊断和四窗口测试仍未完成。下一步以冻结条件运行 seed 1/b，并在拟合前执行 fresh preflight。测试仍须等待完整重复与学习有效性门通过。
