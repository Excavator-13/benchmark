# P02-T006 v2 Windows fresh preflight

类型：formal preflight / handoff。所属任务：P02-T006。
日期：2026-11-28，Asia/Shanghai。执行者：本会话研究侧 Codex。
对象：首个 v2 r0/GRU 候选的执行前预检；无 worker 启动。

## 命令与结果

在用户选定的当前 Windows 本机，从仓库根目录调用正式预检：

```powershell
python -m benchmark.multivariate_time_series.effective_temporal_training preflight `
  --data-name r0 --data dataset/demand/r0.parquet --model GRU --seed 0 `
  --purpose formal `
  --run-id p02-t006-r0-gru-v2-s0-lr1e3-a-20261128-01 `
  --block-id p02-t006-r0-gru-v2-20261128-01 `
  --output-root research/runs `
  --batch-id p02-t006-effective-20261108-01 `
  --ledger research/reports/p02-t006-execution-20261108-01/ledger.json `
  --out research/reports/p02-t006-execution-20261108-01/preflight-r0-gru-v2-20261128-01.json
```

最终机器可读结果见 [preflight JSON](../p02-t006-execution-20261108-01/preflight-r0-gru-v2-20261128-01.json)，状态为 `fail`。数据身份、v2 与继承 v1 协议身份、依赖、源码、单线程环境、输出身份、worker lock、磁盘空间、RSS 监测和累计预算均通过。唯一失败项为可用内存：预检测得 3,980,029,952 bytes（约 3.71 GiB），低于协议最低 6 GiB；磁盘可用 66,015,195,136 bytes（约 61.47 GiB）。依赖为 Python 3.13.0、NumPy 2.4.2、pandas 3.1.1、PyArrow 26.0.1、PyTorch 2.6.0+cpu、psutil 7.2.2。

随后只读复查的可用内存为 3.68 GiB，一项前台进程占用约 8.97 GiB。没有关闭进程或修改系统状态。原 ledger 新增本次 standalone preflight 的 4.0556873 秒失败计费，保留 batch/ledger ID、900 秒预算扣除及全部历史记录；累计 measured/replayed 为 73.932004091 秒，保守扣除为 900 秒，有效累计为 973.932004091 秒，剩余 42,226.067995909 秒。

## 停止与恢复

按协议资源门停止在预检阶段；没有启动正式拟合、读取测试期、创建 run 输出或重试成本样本。T006 仍为 `blocked`。待当前 Windows 可用内存达到至少 6 GiB 后，用新的预检报告路径重新运行 fresh preflight；只有全部门通过后，才进入首候选 10 轮真实成本样本。
