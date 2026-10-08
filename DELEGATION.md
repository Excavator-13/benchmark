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
| 变更名 | `reduce-baseline-evidence-overhead` |
| 研究任务 | P01-T010 |
| 登记时间 | 2026-10-08 |
| 委派给 | OpenSpec e13 流程（propose → apply → verify-change → archive-change），由用户在其会话中执行；研究侧不代跑 |
| 结束判据 | 活跃变更目录已不存在；`openspec/changes/archive/*-reduce-baseline-evidence-overhead/verification.md` 为 `Verdict: PASS`，Verification Basis 与当前实现一致。覆盖 D010：正式预测材料仍可独立重算、重复执行保留身份、开发输出可隔离、检查仅产生明确报告且不改输入、相关脏执行源码可恢复、落选候选默认只保留验证分数、Git 已覆盖来源可固定引用、schema v2 包索引保留排除声明且辅助工具不依赖 sidecar/全成员表、旧包及可读入口不改；不启动新科研实验或自动恢复演练 |
| 研究侧收尾 | 依据归档独立报告作 P01-T010 研究接受决定，更新 [阶段计划](research/phases/P01/plan.md)、[state](research/state.md) 恢复点及 review 的软件完成说明；更新 [索引](research/archives/index.md) 对旧工具限制及当前检查入口的说明。按实际产物记录位置与已知保存事实，不镜像变更任务表，不补做实验/封存/commit/push/恢复核验；关闭本指针 |
| 上次核对 | 2026-10-08：活跃变更目录已不存在；归档 `2026-10-08-reduce-baseline-evidence-overhead/verification.md` 为 PASS，V-001..V-005 均 verified-resolved。研究记录更新前按报告算法核对所有基准一致，规划按原路径标签计算、既有归档集合排除新归档；主规格为预期 delta 同步，方法与范围见 D011 |
| 回收记录 | 2026-10-08：按 [D011](research/decisions.md#d011-t010-记录减负研究侧验收)接受 P01-T010，更新阶段计划、state、review、索引、执行指导与当前协议的实现验收链接，解除旧工具兼容限制说明。没有新增正式科研 run/封存包；软件和本轮记录仍未提交/push，既有包保存事实保留。不代跑工作流、不改代码、不重跑测试/实验/恢复核验；第二轮迁移仍为可选候选，P01 科研未完成项保留 |
