# P02-T006 v2 r0/GRU seed 1/a 执行与恢复

类型：experiment / recovery。所属任务：P02-T006。
日期：2026-11-28，Asia/Shanghai。执行者：本会话 Codex，Windows 11 本机 CPU。
科学版本：`P2-effective-training-L6-H3-v2`。

## 执行与中断

按冻结 selection 使用 GRU、seed 1、学习率 `1e-3`、confirmation/a。正式 fresh preflight 通过，数据、v2 与继承 v1 协议、源码、单线程、资源、输出身份和累计预算均匹配。

父 run `p02-t006-r0-gru-v2-s1-a-20261128-01` 的 10 轮真实成本样本通过，样本 16.44495 秒，epoch 6–10 中位数 0.60864 秒，v2 单次拟合保守估计 330.11 秒。轨迹在账本原子替换遇到 Windows `WinError 5` 后暂停，完成 epoch 144 / 2,736 updates。ledger 对该尝试计费 78.69952 秒，父 run 状态和现场保留。

通过官方 recovery loader 只读验证 `recovery/last.pt` 为 v2 `last` checkpoint，记录完整 144 epochs、2,736 updates 且包含 best 状态。按协议以新身份 `p02-t006-r0-gru-v2-s1-a-resume-20261128-01` 从 epoch 145 恢复。恢复 run 完成到 epoch 200 / 3,800 updates，runner 返回 exit 0；父 run 未改写。

## 结果与成本

最终 checkpoint 为 epoch 200。验证 MSE 为 202,343.2705，验证 MAE 为 112.3347；从初始化到 best checkpoint 的验证改善及固定权重重评结果保存在 resume report。reproduction 检查通过，saved 与 reevaluated MSE/MAE 差均为 0，容差为 1e-6。拟合阶段未使用测试标签。

父 run 与恢复 run 合计计费 126.0325 秒，低于 60 分钟单次上限。原 batch/ledger 保留 ID `f93290f346bc47e9914be45203c5edc3` / `p02-t006-effective-20261108-01`；截至恢复完成，ledger measured/replayed 累计 363.4575 秒，预算扣除 900 秒，有效累计 1,263.4575 秒，剩余 41,936.5425 秒。

## 证据位置

- 父 run：[status](../../runs/p02-t006-r0-gru-v2-s1-a-20261128-01/status.json)、[cost](../../runs/p02-t006-r0-gru-v2-s1-a-20261128-01/cost.json)、[epoch timing](../../runs/p02-t006-r0-gru-v2-s1-a-20261128-01/epoch-timing.json)、[最后恢复点](../../runs/p02-t006-r0-gru-v2-s1-a-20261128-01/recovery/last.pt)
- 恢复 run：[summary](../../runs/p02-t006-r0-gru-v2-s1-a-resume-20261128-01/summary.md)、[report](../../runs/p02-t006-r0-gru-v2-s1-a-resume-20261128-01/report.json)、[provenance](../../runs/p02-t006-r0-gru-v2-s1-a-resume-20261128-01/provenance.json)、[最终恢复点](../../runs/p02-t006-r0-gru-v2-s1-a-resume-20261128-01/recovery/last.pt)
- 本次 formal preflight：[JSON](../p02-t006-execution-20261108-01/preflight-r0-gru-v2-20261128-05.json)
- 持续账本：[ledger.json](../p02-t006-execution-20261108-01/ledger.json)

resume 的 `purpose` 与 protocol controls 均为 formal 且完整，但自动生成的 summary 与 cost 文件含有 “Development evidence” 和 “short development trajectory” 的通用措辞。这与正式父 run、恢复配置和 report 元数据不符；恢复本身没有新的 10 轮 cost sample，成本以父 fit 的已通过样本和 ledger 的实测收费为准。摘要模板不一致已记录，不把它解释为运行被标为 development。

## 当前状态与下一步

seed 1/a v2 轨迹完成。没有运行学习有效性总诊断或生成测试。下一步按有限矩阵运行 seed 2/a confirmation，并在拟合前对新身份做 fresh preflight；随后还需完成 seeds 0/1/2 的 b 重复和相应诊断。
