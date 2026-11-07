# Run: p02-t006-gru-lstm-20261107

类型：experiment
所属任务：P02-T006
目的：在相同 Job-SDF `r0/count` 配置下比较新的 GRU 与 LSTM 实现。
运行状态：succeeded（代码、训练检查和正式 e13-openspec 独立验证完成）
开始/结束时间：2026-11-07；具体命令时间见日志文件时间戳

## 协议

- 数据：`repo/benchmark/dataset/demand/r0.parquet`，`count` 粒度
- 输入长度：6 个月；预测长度：3 个月；label length：1
- 训练/验证/测试窗口：19 / 1 / 4
- hidden size：256；循环层数：2；epochs：20；batch size：1；patience：3
- CPU；seed：2、3、4（由 `--seed 2 --itr 3` 生成）
- checkpoint：按验证损失选择，测试只在训练结束后执行

## 结果

| Model | MSE（seed 2/3/4） | MSE mean ± sd | MAE（seed 2/3/4） | MAE mean ± sd |
| --- | --- | ---: | --- | ---: |
| GRU | 3309058.00 / 3432487.75 / 3512487.25 | 3418011.00 ± 102484.38 | 321.1655 / 326.2797 / 329.1536 | 325.5329 ± 4.0461 |
| LSTM | 3306367.50 / 3303263.50 / 3281752.00 | 3297127.67 ± 13405.86 | 318.3917 / 319.8380 / 318.0060 | 318.7453 ± 0.9658 |

在这组小规模、单数据粒度预实验中，LSTM 的平均 MSE 和 MAE 均低于 GRU；这不能推出 LSTM 在其他粒度、seed 或预算下普遍更优。

## 证据

- 原始日志：[gru.log](gru.log)、[lstm.log](lstm.log)
- 汇总：[metrics.json](metrics.json)
- 运行脚本：`benchmark/multivariate_time_series/run_gru_lstm.sh`
- checkpoint：`scratch/p02_t006_checkpoints_repeat/`
- 环境：Anaconda Python 3.13.5，PyTorch 2.10.0+cpu，pandas 2.2.3，pyarrow 19.0.0

## 限制

- P02 计划由用户口述重建，远端最新 P02 文件本轮无法获取。
- OpenSpec 1.16.1 已安装；strict validation 和独立 e13-openspec verification 已 PASS。
- 本 run 没有覆盖 `region`、`r2` 或 GPU；不处理 P02/T009。
