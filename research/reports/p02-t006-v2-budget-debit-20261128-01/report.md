# P02-T006 v2 保守预算扣除登记

类型：budget accounting / handoff。所属任务：P02-T006。
日期：2026-11-28，Asia/Shanghai。执行者：本会话研究侧 Codex。
依据：[P02 v2 协议 §4](../../phases/P02/protocol-v2.md)、[软件就绪验收](../p02-t006-software-closeout-20261128-01/report.md)。

## 操作与结果

沿用原 batch `p02-t006-effective-20261108-01` 和 ledger `research/reports/p02-t006-execution-20261108-01/ledger.json`，通过公开 `budget-debit` CLI 登记 900 秒 v2 保守准备成本。稳定 debit ID 为 `p02-t006-v2-preparation-20261128`，理由明确标注为历史准备／只读辅助工作的保守预算扣除，不是实测训练耗时。

命令：

```powershell
python -m benchmark.multivariate_time_series.effective_temporal_training budget-debit `
  --ledger research/reports/p02-t006-execution-20261108-01/ledger.json `
  --batch-id p02-t006-effective-20261108-01 `
  --debit-id p02-t006-v2-preparation-20261128 `
  --seconds 900 `
  --reason "Conservative prior preparation and read-only auxiliary work allowance per P02 v2 protocol, not measured training time"
```

CLI 返回 `registered`。操作前 ledger 有 7 条执行记录，累计 measured/replayed 为 69.876316791 秒，没有预算扣除。操作后保留原 ledger ID `f93290f346bc47e9914be45203c5edc3` 和所有历史记录，新增一条 900 秒 `budget-debit`；有效累计为 969.876316791 秒，剩余批次预算为 42230.123683209 秒。实际 ledger 更新记录时间为 `2026-11-28T15:32:59+08:00`。

## 范围与下一动作

本步只修改原 ledger 的预算记账。没有启动 worker、读取真实需求数据、运行预检或生成训练产物。T006 仍 `blocked`，v1 失败结果及历史预算保留。

下一步为选定正式执行环境后运行 v2 fresh preflight，并按其结果决定是否能进入首候选 10 轮真实成本门。预检与成本样本尚未执行，不能视为已满足正式拟合条件。
