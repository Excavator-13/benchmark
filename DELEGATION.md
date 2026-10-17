# 委托指针（科研记录 ↔ OpenSpec 变更）

本文件只保存一件事：当前有没有研究任务被委托给一个 OpenSpec 变更，以及回收时欠哪些研究侧收尾。
它不记录任务进度、不替代 [research/state.md](research/state.md)、不替代阶段计划，也不替代变更目录里的工件。

规则（稳定政策）见 [AGENTS.md](AGENTS.md)。本文件的**唯一写入者是 research-maintainer（研究侧会话）**；
OpenSpec 的 propose / apply / verify / fix / archive 既不读也不写它，也不负责更新它。

## 状态

| 取值 | 含义 | r-m 启动时该做什么 |
| --- | --- | --- |
| `none` | 没有在途委托 | 什么也不做 |
| `open` | 已委派给某个变更，OpenSpec 侧可能仍在工作 | 只读核对结束判据；结果为"未结束"就只提醒，为"已结束"就做研究侧收尾并关闭 |
| `closed` | 已回收且研究侧收尾完成 | 什么也不做 |

`open` 的两种观察结果**只观察、不单独存状态**（存了就是多一个要维护的字段）：

1. **未结束** → 只提醒用户（例如"`openspec/changes/<变更名>` 仍在，未归档"）。不代跑 apply/verify/fix/archive，不改代码、不移目录、不 commit/push。
2. **已结束但尚未回收** → 按"研究侧收尾"字段更新科研记录，然后把 `Status` 改为 `closed` 并填 `Recycle record`。

## 结束判据（只读，两条都满足才算结束）

1. `openspec/changes/<变更名>` 已不存在；
2. `openspec/changes/archive/*-<变更名>/verification.md` 存在，`Verdict: PASS`，且其 Verification Basis 与当前实现一致。

第 2 条不满足或无法比对时，记为"未结束/存疑"，不推断完成。
归档目录加日期前缀，所以登记时**只记变更名，不记路径**。

## 边界

- 同时最多一条在途委托。历史由 Git 承担，不在本文件另存一份。
- 本文件是指针，不是进度表：不要把 `tasks.md` 的勾选状态镜像到这里、`research/state.md` 或阶段计划。
  研究任务状态以阶段计划为准，变更级进度以变更目录为准；OpenSpec 的 PASS 是研究验收的**证据**，不是验收本身。
- 研究侧收尾属于常规记录维护；若收尾包含需要新授权的动作（正式运行实验、封存、commit、push），只报告并等待授权。
- 本文件不改变任何 skill；`.agents/skills/` 下的 skill 保持未修改，并对各自的流程保持权威。

## 当前委托

| 字段 | 值 |
| --- | --- |
| Status | `closed` |
| 变更名 | `add-nograph-backtest-folds` |
| 研究任务 | P01-T007 |
| 登记时间 | 2026-10-13 |
| 委派给 | OpenSpec e13 流程（propose → apply → verify-change → archive-change），由用户在其会话中执行；研究侧不代跑 |
| 结束判据 | 活跃变更目录已不存在；`openspec/changes/archive/*-add-nograph-backtest-folds/verification.md` 为 `Verdict: PASS`，Verification Basis 与当前实现一致。覆盖 T007 的实现验收：按 [T007 指导](research/phases/P01/t007-backtest-guide.md) §2–§5 在 `benchmark.nograph_baseline` 增加折 A/B 调度，每折重建窗口、折内标准化与 `TrainMean<fit>`、折内活跃度分组，验证与开发评估分别命名 `validation`/`eval`，产物记录折与角色，`recompute`/`compare` 支持 fold run，`align-v2` 明确拒绝 fold run；主切分与 `r0`/`region`/`r2` 既有行为回归不变；不改变科学协议、主切分、主评测、选模/分组/收益门槛，不改旧 run、封存包或归档 |
| 研究侧收尾 | 依据归档独立报告作 P01-T007 实现就绪判断，更新阶段计划、state、索引与执行指导入口说明。若正式 fold run 尚未获用户授权，只把 PASS 作为实现证据，不把它当实验验收；不代跑工作流、不改代码、不封存、不 commit/push、不做恢复核验；关闭本指针 |
| 上次核对 | 2026-10-17（回收）：活跃变更目录已不存在；归档 `2026-10-17-add-nograph-backtest-folds/verification.md` 为 `Verdict: PASS`。按报告 37 文件主清单重算单文件 SHA256（5 个规划文件映射到归档路径），37/37 一致，无缺失；报告聚合指纹仅因路径映射不同。确认 `research/phases/P01/protocol.md` 未改、主切分常量与默认路径保持、`research/runs/` 无正式 fold run、旧 run/封存包/`experiments_archive/`/既有 OpenSpec 归档未改；本机按报告同款 formal-fold guard 复跑 287 项，285 通过、2 项 sklearn 跳过，0 失败/错误。回收后按收尾在 execution-guide §7 做过一次记录性入口文字更新 |
| 回收记录 | 2026-10-17：按 [D020](research/decisions.md#d020-t007-内部两折回测实现研究侧验收) 接受 T007 实现就绪证据，T007 改为 `in_progress`，更新阶段计划、state、索引与执行指导入口说明，关闭本指针。正式 fold run（`r0`/`region`/`r2` × A/B）、产物保存与跨折收益判断仍待用户另行授权；实现 PASS 不是实验验收。没有代跑工作流、改实现、封存或做恢复核验；本轮 commit/push 由用户明确授权，提交身份从 Git 历史追溯，不在本指针声明提交状态 |
