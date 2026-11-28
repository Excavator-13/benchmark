# P02-T006 v2 r0/GRU seed 2/a 执行记录

类型：experiment。所属任务：P02-T006。
日期：2026-11-28，Asia/Shanghai。执行者：本会话 Codex，Windows 11 本机 CPU。
科学版本：`P2-effective-training-L6-H3-v2`。

## 执行结果

按冻结 selection 使用 GRU、seed 2、学习率 `1e-3`、confirmation/a。formal fresh preflight 全部通过，沿用原 batch `p02-t006-effective-20261108-01` 与 ledger `f93290f346bc47e9914be45203c5edc3`。轨迹完成 200 epochs / 3,800 updates，status 为 `completed`，没有恢复或重启。拟合没有使用测试标签。

第 10 轮真实成本门通过。样本时间为 25.5384 秒，epoch 6–10 完整耗时中位数为 0.74876 秒，v2 单次完整拟合保守估计为 412.6618 秒；含样本成本的单次投影为 438.2002 秒，低于 3,600 秒上限。剩余矩阵批次投影为 2,941.12 秒，低于 12 小时上限。RSS 监测在完整运行中工作正常。

最终 selected checkpoint 为 epoch 200。验证 MSE 为 206,192.2089，MAE 为 107.0046。保存指标与固定权重重评的差为 0，report reproduction 状态为 pass，容差 1e-6。

## 证据与累计记账

- formal fresh preflight：[JSON](../p02-t006-execution-20261108-01/preflight-r0-gru-v2-20261128-06.json)
- 正式 run：[summary](../../runs/p02-t006-r0-gru-v2-s2-a-20261128-01/summary.md)、[report](../../runs/p02-t006-r0-gru-v2-s2-a-20261128-01/report.json)、[cost](../../runs/p02-t006-r0-gru-v2-s2-a-20261128-01/cost.json)、[provenance](../../runs/p02-t006-r0-gru-v2-s2-a-20261128-01/provenance.json)、[history](../../runs/p02-t006-r0-gru-v2-s2-a-20261128-01/history.json)
- 原 batch ledger：[ledger.json](../p02-t006-execution-20261108-01/ledger.json)

截至本 run 完成，ledger measured/replayed 累计 527.0635 秒，v2 保守预算扣除 900 秒，有效累计 1,427.0635 秒，剩余 41,772.9365 秒。

自动生成的 summary 末尾含 “Development evidence” 通用提示语，与本 run 的 `purpose=formal`、完整 protocol controls 和机器报告冲突。研究侧以 command、config、provenance、status、report 和 cost 元数据确定运行身份；该模板措辞不解释为开发运行。

## 当前边界与下一步

seed 2/a 完成后，三个 a 轨迹均已存在。尚未运行 section-5 learning readiness 总诊断，也未生成四窗口测试。下一步按 v2 矩阵补做 seed 0/b，并在其后继续 seed 1/b 和 seed 2/b；所需 b 证据齐全后才执行 saved-evidence 诊断，只有诊断通过才允许测试阶段。
