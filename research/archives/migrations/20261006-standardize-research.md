# 2026-10-06 科研记录规范化

类型：组织迁移；关联任务 P01-T009；依据：[D004](../../decisions.md#d004-按-skill-规范化并提交推送)。
迁移前基准：`f66959b3dd868ba97a330cf46147212b83a4524b`，用户授权保存当前状态后已首次 push 至 `origin/xzs`。
当前状态：组织迁移 `succeeded`，任务 P01-T009 已完成；组织提交已入库、push 并核验远端可读。

## 路径与职责映射

| 旧材料 | 标准位置 | 处理方式 |
| --- | --- | --- |
| `research_planning/01_research_roadmap.md` | `research/roadmap.md` | 迁移、修复链接，移除实时任务状态职责 |
| `research_planning/02_phase_one_plan.md` | `research/phases/P01/protocol.md`、`plan.md` | 原科学定义迁入协议；任务和验收状态由新 plan 维护，保留工作包映射 |
| `research_planning/03_next_steps_guide.md` | `research/phases/P01/execution-guide.md` | 活跃操作指南使用新路径和 v3；旧快照不改 |
| `research_planning/04_progress_and_decisions.md` | `research/state.md`、`decisions.md`、`plan.md` | 拆分执行位置、决定/探索和任务状态，事实仍引用封存证据 |
| `experiments_archive/README.md` | `research/archives/index.md` | 建立标准权威索引，旧位置仅保留导航 |
| `experiments_phase1/phase1-20261006-v2-01/` | `research/runs/phase1-20261006-v2-01/` | 13 个文件仅移动路径，逐字节保持原样 |
| 既有 `experiments_archive/` GPU 材料、包和校验 | 原路径 | legacy 封存来源保持不变，由标准索引引用 |
| 无统一入口 | `RESEARCH.md`、`AGENTS.md` | 为用户及新 agent 建立接手入口，README 增加链接 |

旧进展记录中已接受的两项决定保留为 D001、D002；用户后续要求作为 D004 记录替代依据。分层数字在 D005 摘录，仍标待归档探索，不伪装已完成的新分析。

## 协议兼容性

当前布局协议升级为 `P1-count-L6-H3-v3`，仅改变存储路径与外部状态维护。输入 L/H、时间划分、节点身份、标准化、基线定义、指标和收益门槛与 v2 完全一致。旧 v2 快照保持原内容；不为组织迁移重新训练或重算科研结果。

## 验收

检查脚本：[verify_20261006.py](verify_20261006.py)。它只读核对归档 SHA256、13 个内容文件、相对链接/标题、协议科学段落和指南脚本语法；不运行实验或改写文件。

2026-10-06 组织核验通过：包和校验文件、13 个展开内容均原样；科学定义与收益门槛相等；活跃链接/标题与文档空白通过；4 个 Python 和 9 个 shell 示例语法通过，未执行实验；代码、数据、OpenSpec 及历史 GPU 证据没有变化。链接数量随收尾记录新增而变化，最终以检查脚本输出为准。

首次 push 后独立读取 `origin/xzs` 指向 `f66959b`；从该远端提交取回旧诊断包，SHA256 和本地逐字节比较一致。

组织提交为 `b094cf13f47f2622f2771f0d766212b0b34fadba`。push 成功后独立读取 `origin/xzs` 与其一致；2026-10-06T18:18:00+08:00 取回该提交的 RESEARCH.md，与本地逐字节相等。此报告随后保存收尾事实，其自身最终 commit 无需写入正文。

本次组织工作已完成；第一阶段整体仍 active，下一科研动作是 P01-T004 的范围明确的 proposal，未在本轮启动实现或训练。

## 保留的历史限制

旧运行内相对链接、哈希清单和命令仍描述原目录。复现原快照时应按包内布局恢复，或使用本映射核验内容。检查脚本有意不把历史快照当活跃导航修改。

历史 GPU 实验没有统一 provenance 与校验清单；当前不追溯补造。旧核验报告和通用指南仍在原路径，代码、数据、OpenSpec 记录和模型 API 不迁移。全新 clone 的完整恢复尚未执行。
