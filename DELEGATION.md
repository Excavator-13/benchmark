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
| 变更名 | `add-r2-count-baseline`（拟用名；若 propose 采用其他名字，研究侧更新本表） |
| 研究任务 | P01-T006 |
| 登记时间 | 2026-10-11 |
| 委派给 | OpenSpec e13 流程（propose → apply → verify-change → archive-change），由用户在其会话中执行；研究侧不代跑 |
| 结束判据 | 活跃变更目录已不存在；`openspec/changes/archive/*-add-r2-count-baseline/verification.md` 为 `Verdict: PASS`，Verification Basis 与当前实现一致。覆盖 T006 的实现验收：`r2/count` 可经同一无图入口运行，含身份/活跃度/图审计、五项朴素基线、训练期标准化、验证选模、固定活跃度与邻居分组、完整产物、重算/同条件重复检查与成本记录；不改变科学协议与选模/分组/收益门槛，不改 `r0`/`region` 历史结果、旧封存包或包内内容 |
| 研究侧收尾 | 依据归档独立报告作 P01-T006 研究接受判断，更新阶段计划、state、索引与执行指导的入口说明。若正式 `r2/count` run 尚未获用户授权，只把 PASS 作为实现证据，不把它当实验验收；不代跑工作流、不改代码、不封存、不 commit/push、不做恢复核验；关闭本指针 |
| 上次核对 | 2026-10-11（回收）：活跃变更目录已不存在；归档 `2026-10-11-add-r2-count-baseline/verification.md` 为 `Verdict: PASS`。按报告 40 文件清单重算 SHA256（变更目录路径映射到归档位置），39 个与当前工作区实现一致，无缺失文件；唯一差异是主规格 `openspec/specs/nograph-baseline-entry/spec.md`（报告已明示归档时的主规格同步不计入 pre-archive 指纹，diff 为 r2 delta 的预期同步）。 |
| 回收记录 | 2026-10-11：按 [D017](research/decisions.md#d017-t006-r2count-实现研究侧验收与委托回收)接受 T006 的实现就绪证据，更新阶段计划、state、索引与执行指导入口说明，关闭本指针。T006 改为 `in_progress`：真实 `r2` 身份/活跃度/图审计、正式 run 与产物保存、实测成本仍需用户另行授权；实现 PASS 不是实验验收。实现/测试/文档/主规格与归档变更目录仍未提交，没有新增科研 run、封存或恢复核验。不代跑工作流、不改代码。 |

### 建议变更范围（供 propose 参考，不构成研究验收）

- 在无图 baseline 入口加入 `r2/count`：上下文列 `r2_id`，沿用现有读取、标准化、五项基线、共享 Ridge、验证选模、固定分组与产物格式。
- 同步 CLI `--data-name` choices、检查命令、README/执行指导入口与对应测试（含原先断言 `r2` 被拒的测试）。
- 保持 `r0`/`region` 行为与产物不变；不新增科学协议、不改收益门槛。
- 正式 `r2/count` 运行与保存需用户单独授权；实现与独立验证本身不启动正式科研 run。
