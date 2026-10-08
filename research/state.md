# 当前状态

更新时间：2026-10-08。
当前阶段：[P01](phases/P01/plan.md)，阶段状态与任务状态以该计划为准。
当前任务：P01-T011 历史整理已完成；本轮仅做文件整理与保存，没有启动下一项科研任务。任务状态以阶段计划为准，不镜像 OpenSpec 任务表。
当前执行者：本轮整理与保存由 Codex 完成，本地分支 `xzs`，没有执行实验。T011 整理提交 `77598faef8d90bff621456786ca27b045b3122fb` 已正常 push 至 `origin/xzs`；此前 skill/T010 及 T004 的保存身份见归档索引，不随当前 HEAD 更新。
本次授权范围：用户要求完成剩余清理，该删的删、该整理的整理；ignored 文件不删除，可以整理。按 D012 删除三项旧预览/探针，迁移历史核验、探索、参考源码、notebook、GPU 旧指南与本地论文，修复活跃入口。沿用此前提交与推送授权；不启动实验、重新打包或恢复演练。
本轮 run：无；研究维护与 Git 保存不创建实验 run。

## 恢复位置

- 第二轮清理按 [D012](decisions.md#d012-完成剩余历史与参考材料整理)完成：三个旧预览/探针删除；195 个 tracked 文件原样归入开发历史、探索历史与上游参考，活跃链接及 GPU 指导已更新。本地论文移入 ignored 文献目录，ignored 内容不删除。旧/新路径及历史脚本限制见[映射](archives/migrations/20261008-legacy-cleanup.md)，保存事实见[索引](archives/index.md#t011-历史整理2026-10-08)。
- 2026-10-08：按 [D010](decisions.md#d010-采用实验记录与保存减负政策)采用 `P01-records-v2`，已更新协议 §6.1/§9、计划和执行指导；科学版本仍为 v3。研究论证与执行说明见[review §9](reviews/20261008-maintenance-and-protocol.md#9-采用与执行记录2026-10-08)，新版 skill 已完成，本轮不改 skill。
- 第一轮整理见[记录](archives/migrations/20261008-evidence-maintenance.md)：24 个包和 88 个可读入口原样保留，移除一致的忽略展开副本与缓存；删除 T004 sidecar，全成员哈希清单改为位置/提交/大小/数量与排除声明。检查需要完整输入，按需在独立目录从包展开；`verify` 工具已支持 schema v2 与历史 v1，恢复核验仍仅按明确请求执行。整套减负工作已提交并 push，保存事实见[索引](archives/index.md#t010-软件变更保存事实2026-10-08)。
- `reduce-baseline-evidence-overhead` 已[归档独立 PASS](../openspec/changes/archive/2026-10-08-reduce-baseline-evidence-overhead/verification.md)，五项发现均为 verified-resolved。研究侧在记录更新前比对全部报告基准，主规格为预期 delta 同步；按 [D011](decisions.md#d011-t010-记录减负研究侧验收)接受 T010 并关闭 [DELEGATION](../DELEGATION.md)。报告分轮验证证据与可选 sklearn 限制保留，不重跑全套；科研记录的后续更新不回写历史报告。
- 当前软件已落实 formal/development 输出隔离、单份 `--report` 检查及旧参数别名、相关脏源码恢复、固定来源引用、默认候选产物减量和 Git 包索引兼容；当前入口见[执行指导 §7](phases/P01/execution-guide.md#7-当前可复用-baseline-入口)与[索引](archives/index.md)。没有新增正式科研 run 或封存包，临时软件 fixture 不作为新科学结论。
- T004 已按 [D008](decisions.md#d008-t004-baseline-研究侧验收)接受，旧变更归档 PASS 和核验方法仍保留。科研依据是四个 `-002` 模型执行及八个关联检查；两组 NaiveRef/NaiveRef6 均为 LastValue、Ridge lambda=1e-4、同 seed 预测差为 0，总体测试误差高于 LastValue，不宣称改善。成本、来源与保存事实见[索引](archives/index.md#t004-baseline-运行2026-10-07)。
- 2026-10-08 清理前只读进程列表未发现本地 baseline/封存进程（搜索自身除外）；本轮未启动实验，未核验历史远端 GPU 状态。旧包、包内内容、可读入口和 OpenSpec 历史报告原样保留；当前精简目录不再用于原报告的完整展开证据指纹。取消的远端恢复检查不续跑。

## 下一可执行动作

本次减负与授权清理均已结束，无在途委托；不追加 Git 回执或恢复检查。没有把已确认保留的历史、参考、ignored 文件列为继续清理的待办。

科研接续：保持阶段计划已有顺序，准备 P01-T006 的 `r2/count` 同流程扩展范围，再接内部回测；P01-T005 的 EvolveGCN-H 受控诊断在底座通过后也已满足依赖。新实现/实验仍按具体授权与 OpenSpec 流程执行，研究侧先登记新的委托；本轮未启动。

## 待处理事项

- [D005](decisions.md#d005-补存分层分析的可复查过程)：新 baseline 分层证据已补，旧 EvolveGCN 两个 seed 的分层过程及交叉分布仍未补存。
- [D006](decisions.md#d006-明确主要改善目标)：完整任务或预定节点组的主张范围仍未决定，不按当前测试结果切换目标。
- [D007](decisions.md#d007-检验低活跃节点与邻居信息的假设)：交叉分布与公平对照仍待执行。
- T002 的剩余图审计/解释，以及 T005-T008 的科研工作见阶段计划；P01 尚未完成。
- T004 已封存、提交/push；远端恢复未核验，用户取消检查，不列为待补任务。
- D009 的长期建议由 D010 接续，T010 已按 D011 接受并完成主体提交/push；第二轮清理已按 D012 完成，历史路径由迁移映射解释。远端恢复未核验，不安排默认检查；后续保存状态记录的提交身份从 Git 历史追溯。
