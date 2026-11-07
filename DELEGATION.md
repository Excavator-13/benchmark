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
- 本文件不改变任何 skill 的行为；`.agents/skills/` 下的 skill 通过各自的更新流程维护，并对各自的流程保持权威。

## 当前委托

| 字段 | 值 |
| --- | --- |
| Status | `closed` |
| 变更名 | `add-occupation-skill-graph-audit` |
| 研究任务 | P02-T009（见 [P02 计划](research/phases/P02/plan.md) §3.1） |
| 登记时间 | 2026-11-07 |
| 委派给 | OpenSpec；本轮完整提案，后续 apply → 独立 verify → archive；研究侧不代跑 |
| 结束判据 | 本文件 §结束判据两条；独立验证覆盖构图协议的训练期边界、两个分数、全零／平分、稀疏化、共享图映射、趋势未知、预算终态与来源证据；旧 runner 定义不变 |
| 研究侧收尾 | 核对归档 PASS 与当前实现后接受软件就绪并关闭指针，更新 T009 证据与 state；随后按 D039 在本机预检、构造并审计两候选，依据实际结构／成本／限制决定冻结或修订，另存分析证据。软件 PASS 不代表 T009 完成，不启动预测训练，不封存、commit 或 push |
| 上次核对 | 2026-11-07：活跃变更不存在、归档独立 PASS、当前相关实现与验证依据一致；详见[研究侧回收核对](research/reports/p02-t009-software-acceptance-20261107-01/report.md) |
| 回收记录 | 按 D040 接受软件就绪并关闭。T009 保持进行中，真实源／目标预检、构图、审计和冻结未执行；D039 后续授权保留，本轮在回收处结束，无代码修改、训练、封存、commit 或 push |
