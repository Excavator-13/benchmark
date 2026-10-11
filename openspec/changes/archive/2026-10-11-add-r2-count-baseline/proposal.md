## Why

研究任务 P01-T006 已按 D016 委派 `r2/count` 入口扩展，但现有无图 CPU baseline 只允许 `r0/count` 和 `region/count`。将协议已定义的第三种粒度接入同一流程，才能在不改变科学定义的前提下检查身份、分组、预测保存与执行成本。

## What Changes

- 注册 `r2` 的上下文列 `r2_id`，支持按 `(r2_id, skill_id)` 排序的 count 需求数据；CLI choices 继续从协议映射派生，帮助文本同步。
- 复用现有身份/月历/网格/活跃度及上下文内图覆盖审计、五项朴素基线、SharedRidge、验证集选 lambda、固定分组、指标和产物格式。
- 为 r2 增加多上下文 fixture、端到端与负例测试，证明 recompute、compare、align-v2 支持相同保存格式；同时保持 r0/region 回归行为。
- 提供并实测 r2 规模的 development 成本路径，保存读取、拟合、推理、总耗时与峰值 RSS 的工程证据；不作为科研实验验收。
- 更新 README §4.5 和执行指导的当前入口说明；修订主规格的 Purpose、支持集合、身份要求、对齐和完整产物要求，解除 r2 拒绝规则。

科学定义唯一来源为 `research/phases/P01/protocol.md` §3–§6，科学版本保持 `P1-count-L6-H3-v3`，记录政策保持 `P01-records-v2`。不改协议正文、切分、标准化、选模、分组、指标或收益门槛；不改旧运行、封存包、历史 OpenSpec 归档。实现与验证仅用临时 fixture/development，不启动正式 r2 run、不生成科研结论或新封存包，不执行 commit/push。正式运行和保存留待研究侧另行授权；软件验证通过不等于 P01-T006 实验验收。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `nograph-baseline-entry`: 将既有 CPU count 入口扩到 r2，明确其上下文身份、保存结果检查、完整产物及 development 实测成本验收，同时保留原两组数据兼容性。

## Impact

- 预计修改 `benchmark/nograph_baseline/protocol.py`、`cli.py`、`tests/nb_fixtures.py`、`test_protocol.py`，并在 `test_data.py`、`test_coverage.py`、`test_runner_cli.py` 补针对覆盖。只有测试发现具体二元假设时才窄改 data/coverage/runner/checks/artifacts。
- 文档涉及 `README.md` §4.5、`research/phases/P01/execution-guide.md` 的当前入口说明；历史诊断说明保留其原范围。
- 无新必需依赖、公共参数、模型或产物 schema；默认路径仍仅依赖 NumPy/pandas/PyArrow，测试不依赖 GPU、PyTorch/PyG 或仓库图数据。
- 本变更目录只承载 OpenSpec 规划与后续实现证据，不维护研究任务状态或委托指针，也不读写 `DELEGATION.md`。
