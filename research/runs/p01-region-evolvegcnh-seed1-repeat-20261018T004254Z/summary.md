# Run: p01-region-evolvegcnh-seed1-repeat-20261018T004254Z

所属任务：P01-T005。状态：succeeded。
开始与结束：见 status.json。科学协议与保存政策：见 provenance.json。

## 实际过程

原服务器、源码、依赖与设备核对结论：见 condition-review.md（T4 / 驱动 535.216.01 / torch 2.3.0+cu121；pip freeze 与归档旧清单逐字节一致；显存上报 16384 MiB 与旧记录 15360 MiB 差 1 GiB，无法确认同一物理 GPU）。
准确步骤：guide.md §2–§9；§5–§7 的 Python 从 guide.md 提取为 preflight.py / train.py / compare.py 后执行，代码逐字相同，实际命令见 execution-notes.md。
首个 run p01-region-evolvegcnh-seed1-repeat-20261018T003044Z 在 §6 成本测量行失败（torch 2.3 reset_peak_memory_stats 未初始化 CUDA），按指导保留并换本 run；指导 §6 已补 torch.cuda.init()（2026-10-18 注）。
执行到哪里、退出码、耗时/内存：training.log、training-exit.txt（exit 0）、cost.json。

## 结果与证据

选中 epoch / 验证 MSE：selection.json；完整轨迹：training-trace.jsonl（1000 条）。
总体 MAE/RMSE、负预测、逐窗口/horizon/分组：comparison.json；测试 MAE/RMSE = 96.18077182769775 / 579.5045937857179，与归档旧 seed 1 的 metrics.json 逐位一致。
同 seed 归一化 MAE 差 0.0、预测最大绝对差 0.0、exact_prediction_match=true、labels_identical=true：comparison.json。
checkpoint 与预测/标签：outputs/count/region/EvolveGCNH/1/。

## 限制和下一动作

发布图构建时间未知，结果只解释为带此限制的固定评测；两次 GPU 采集记录显存上报相差 1 GiB，无法确认同一物理 GPU（但依赖、源码、数据逐字节一致且预测逐张量相同）。
只说明本次同 seed 复跑与归档结果一致，不由单个 seed 估计初始化方差或稳定平均性能；模型仍差于 LastValue（测试 MAE 96.18 vs 35.31）。
下一项：研究侧验收与索引；是否补 seed 2/3/4 或做干预另行确定。
