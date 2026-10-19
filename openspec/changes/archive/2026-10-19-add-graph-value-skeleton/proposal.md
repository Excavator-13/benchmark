## Why

P02-T001（“实现骨架与打乱图”）需要把 P02 计划 §2–§5 与 D023 冻结的简单时序骨架落实为可独立检查的 CPU 入口，为后续研究比较提供实现底座。现有无图入口只有朴素基线与 SharedRidge，旧图入口的模型和依赖均不能直接承担此公平对照。

## What Changes

- 新建独立 `benchmark.graph_value_skeleton` 包：每节点独立状态的 GRU(1,32) 编码最近 6 月原始 count，共享 Linear(32,3) 输出；`self`、`graph`、`shuffled` 分别独立训练，图传播不增加可学习参数。
- 读取上下文限定发布图，复用既有端点→规范节点的整数键语义；以入邻域二值非加权均值作残差消息，孤立节点消息严格为零。
- 实现上下文内保持有向入/出度的双边交换，固定打乱 seed 0/1/2；按每个模型 seed 的三图平均 MAE 提供对照，不选择最弱图或平均预测替代平均 MAE。
- 复用 P01 数据、主切分、固定分组、朴素参照和指标数值契约；提供固定 200 epoch/Adam 的训练、验证原始单位 MSE 选 checkpoint、完整训练与选择记录、实际参数量与成本。
- 新入口显式区分方法、模型 seed、打乱 seed 和 development/formal purpose；提供完整可重算产物、只读重算与同 seed 重复比较。默认 development，实现/独立验证只使用 fixture 与 development 检查，不执行正式比较。
- 增加 CPU fixture 测试与 README 新入口章节；保留发布图构建时间未知的限制，软件就绪不代表图收益已证明。

## Capabilities

### New Capabilities

- `graph-value-skeleton`: 冻结 GRU 三分支、上下文入边聚合与保度打乱、P01 身份一致性、训练/产物/只读检查、CPU 与 purpose 边界。

### Modified Capabilities

无。`nograph-baseline-entry` 的公开行为、无 torch 依赖路径及旧保存格式保持原样；`graph-forecast-data-pipeline` 的旧 weighted 导出语义也不修改，新包单独定义二值聚合。

## Impact

- 实现预计新增 `benchmark/graph_value_skeleton/{__init__,__main__,protocol,data,graph,model,shuffle,training,runner,artifacts,checks,cli,_worker}.py`、独立依赖文件与 `tests/`；复用 `benchmark.nograph_baseline` 的纯数值/数据模块。必要适配和共享胶水放新包，不反向给无图入口引入 torch，不改旧图生成器。
- 新包运行时固定 conda `job-sdf-baseline`：Python 3.11.17、torch 2.14.1 CPU-only、NumPy 1.26.4、pandas 2.2.3、PyArrow 17.0.0；不引入 PyG、CUDA 或 torch-scatter/torch-sparse。
- 产品/使用文档仅在 `README.md` 新增入口章节；`research/` 记录、任务状态与协议正文不在实现范围。implementation-notes 与后续 verification 属于本 change 的工作流材料。
- 科学协议 `P1-count-L6-H3-v3`、政策 `P01-records-v2`、主切分、主评测、选模口径、§6.2 门槛与冻结配置不变；不修改旧 run、`experiments_archive/`、封存包或已有归档。
- 本轮只创建规划；不运行实验、不生成正式 run、不写实现代码、不 commit/push、不封存；OpenSpec 流程不读写 `DELEGATION.md`。后续 apply/verify 的 development 检查也不得代跑 P02-T002 的研究比较。
- 委托结束依据是后续归档 verification 的 `Verdict: PASS` 且 Verification Basis 与当前实现一致；研究侧另行判断实现接受。本 change 的软件检查不替代研究验收或 §6.2 科学判定。
