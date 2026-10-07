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
| 变更名 | `add-nograph-baseline-ridge` |
| 研究任务 | P01-T004 |
| 登记时间 | 2026-10-07T16:20+08:00 |
| 委派给 | OpenSpec e13 流程（propose → apply → verify-change → archive-change），由用户在其会话中执行；研究侧不代跑 |
| 结束判据 | 变更目录已归档，且 `openspec/changes/archive/*-add-nograph-baseline-ridge/verification.md` 为 `Verdict: PASS`、Verification Basis 与当前仓库实现一致；该实现覆盖 T004 验收要素：不依赖 PyG/PyTorch 的可复用入口（`r0/count` 与 `region/count`）、训练期 2021-01..2023-03 标准化、仅用验证集原始单位 MSE 选 λ、预测/标签/节点身份/参数/配置保存、指标可独立重算、活跃度与有邻居/无邻居分组、同 seed 重复一致、耗时与峰值内存记录 |
| 研究侧收尾 | 更新 [阶段计划](research/phases/P01/plan.md) 的 T004 状态与证据链接；按需更新 [state](research/state.md) 的恢复位置与下一动作（不镜像变更级进度）；若 apply/verify 产出正式 run，在 [归档索引](research/archives/index.md) 登记封存/提交/备份状态；判断结果是否影响 D005/D006 待决建议。不代跑工作流、不改代码、不移目录、不 commit/push |
| 上次核对 | 2026-10-07T16:10+08:00：`openspec/changes/` 无在途变更；仅存遗留归档 `2026-09-16-repair-graph-forecasting-pipeline`（`Verdict: BLOCKED`，早于委托机制，未登记为委托） |
| 回收记录 | — |
