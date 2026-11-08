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
| Status | `open` |
| 变更名 | `fix-effective-temporal-training-acceptance` |
| 研究任务 | P02-T006 |
| 登记时间 | 2026-11-08 |
| 登记说明 | 研究侧补登记：前一轮已按用户要求创建提案，但遗漏了流程启动前的登记；本条记录实际补登记时间，不追写为事前登记 |
| 委派给 | E13/spec-driven-compatible 变更流程 |
| 结束判据 | 活跃变更目录已移除；对应归档 `verification.md` 为 `Verdict: PASS`，验证基准与实现一致 |
| 研究侧收尾 | 核对当前基准的独立 PASS 并判断软件就绪；依据新证据记录旧 r0 预实验的适用限制及 T006 研究验收缺口，更新阶段计划、state 和保存索引；明确后续正式实验范围与前置条件。软件 PASS 不代替 learning_ready 或 T006 研究验收，不自动启动正式实验、commit 或 push；不修改 T009 |
| 上次核对 | 2026-11-08：活跃变更目录仍存在，结束判据未满足；仅委托软件修复及 fixture/development 验证，正式实验与研究验收由研究侧负责 |
| 回收记录 | 尚未回收 |
