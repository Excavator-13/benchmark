## Why

P02-T006 的独立入口已经交付 r0 预实验，但最佳权重快照会随 CPU 训练继续变化，且测试只覆盖起点 27，未覆盖协议要求的 24..27。现有软件也不足以生成协议规定的学习有效性、独立重复、成本与可重算证据；旧归档 PASS 覆盖的是较窄的软件范围，不能代替完整研究验收。

## What Changes

- 修复模型及优化器最佳快照的存储别名问题，区分验证选择的 best checkpoint 与恢复用 last checkpoint。
- 按现有协议验证 r0/region/r2 count 身份，保留训练期 RMS、完整窗口梯度累积和独立状态；正确评估四个滚动测试窗口。
- 拆分训练／验证选择、学习有效性检查与最终测试报告。提供有限学习率选择、a/b 配对、诊断计算和保存证据的接口，不让测试标签进入训练接口。
- 补齐可重算预测／标签／掩码、来源和条件身份、紧凑只读检查、预检／资源停止／成本及轮边界恢复支持。
- 用小型合成数据、临时 Parquet 和可控时钟／资源采样 fixture 验证软件；交付准确 CLI 文档及研究侧执行交接说明。

## Capabilities

### New Capabilities

- `recurrent-forecasting-entry`: 将上一轮仅存在于归档 delta 的同名 capability 建立到当前规格体系，完整规定修复后的独立时序入口、选择／报告边界、诊断、保存与软件就绪验证。

### Modified Capabilities

无。`openspec/specs/` 当前不存在 `recurrent-forecasting-entry`；本变更使用原归档的准确名称，以 ADDED 方式补齐，不改旧归档或把它误作已存在的主规格。现有 `nograph-baseline-entry`、`graph-forecast-experiments` 和 `graph-value-skeleton` 的行为保持各自契约。

## Impact

实现范围为 `benchmark/multivariate_time_series/effective_temporal_training.py`、相邻专用辅助模块／测试及 README 对应入口说明；复用 `benchmark/nograph_baseline` 的数据、主切分、参照、指标和覆盖注释接口，保持后者既有行为。跨平台进程树 RSS／资源检查需要明确依赖与测量方式，优先使用 psutil；仅为此入口声明依赖，不改变旧环境约束。

**BREAKING**：新输出使用显式实现／产物格式身份与完整 `test_starts`；旧单窗口结果和缺少恢复状态的 checkpoint 不得伪装成新格式或作为可恢复的正式协议证据。原 CLI 模块位置保留；训练和测试报告分离的迁移方式必须在文档说明。

本 change 的 apply／verify 只执行软件测试和临时 development smoke，不读取真实 demand 文件、不启动正式训练、不创建 `research/runs/` 产物、不执行跨粒度实验矩阵、不替用户决定 `learning_ready` 或 T006 完成。研究状态／协议／决定／索引和委托指针的维护、原 Windows 材料回收、正式重跑、研究验收与保存均由研究侧另行处理；本变更不改 T009、旧 run、封存包、历史归档或主规格。规划阶段只写本 change 工件；后续主规格同步依归档流程另行执行。
