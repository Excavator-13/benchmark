# P02-T006 v2 Windows fresh preflight — 通过

类型：formal preflight / handoff。所属任务：P02-T006。
日期：2026-11-28，Asia/Shanghai。执行者：本会话研究侧 Codex。
对象：首个 v2 r0/GRU 候选的重新预检；没有启动 worker。

## 命令与结果

沿用原 batch 与 ledger，使用独立的新报告路径执行 formal preflight：

```powershell
python -m benchmark.multivariate_time_series.effective_temporal_training preflight `
  --data-name r0 --data dataset/demand/r0.parquet --model GRU --seed 0 `
  --purpose formal `
  --run-id p02-t006-r0-gru-v2-s0-lr1e3-a-20261128-01 `
  --block-id p02-t006-r0-gru-v2-20261128-01 `
  --output-root research/runs `
  --batch-id p02-t006-effective-20261108-01 `
  --ledger research/reports/p02-t006-execution-20261108-01/ledger.json `
  --out research/reports/p02-t006-execution-20261108-01/preflight-r0-gru-v2-20261128-02.json
```

结果为 `pass`，完整机器报告见[preflight JSON](../p02-t006-execution-20261108-01/preflight-r0-gru-v2-20261128-02.json)。v2 与继承 v1 文档、r0 数据及节点身份、源码基准、依赖、单线程配置、fresh 输出身份、worker lock、预算和 RSS 监测均通过。可用内存为 20,857,896,960 bytes（19.43 GiB），高于 6 GiB 门槛；磁盘可用 66,008,801,280 bytes（61.48 GiB），高于 5 GiB 门槛。预检记录环境为 Windows/Python 3.13.0、NumPy 2.4.2、pandas 3.1.1、PyArrow 26.0.1、PyTorch 2.6.0+cpu、psutil 7.2.2。

本次 standalone preflight 实测约 1.0685 秒并计入原 ledger。ledger ID 仍为 `f93290f346bc47e9914be45203c5edc3`，batch 仍为 `p02-t006-effective-20261108-01`；当前 measured/replayed 合计 75.0010 秒，保守预算扣除 900 秒，有效累计 975.0010 秒，剩余 42,224.9990 秒。

## 停止点与下一步

这是成功的执行前预检，不代表真实训练成本样本已经完成。没有创建训练 run 输出或 worker，也没有访问测试期。下一步需在同一 Windows 主机、源码和环境身份下，以新 v2 身份启动 seed 0、学习率 `1e-3` 的 formal 候选，并在同一轨迹上完成前 10 轮真实成本样本。按协议成本与资源门继续或停止；不得改用 v1 checkpoint。
