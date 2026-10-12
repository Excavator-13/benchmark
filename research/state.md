# 当前状态

更新时间：2026-10-12。
当前阶段：[P01](phases/P01/plan.md)，阶段状态与任务状态以该计划为准。
当前任务：P01-T006 `r2/count` 已按 [D018](decisions.md#d018-t006-r2count-研究侧验收) 研究侧接受并标为 done；下一科学任务为 P01-T007 训练期内部两折无图回测，T005 与 T008 保留。任务状态以阶段计划为准，不镜像 OpenSpec 任务表。
当前执行者：本轮按用户授权完成 T006 的 r2 审计、两个正式 run、重算/同 seed 检查与成本记录。本地分支 `xzs` 在本轮更新前 HEAD 为 `1f3e5b1`；产物入库与备份状态见[索引](archives/index.md)。
本次授权范围：用户授权继续完成 T006，包括真实 r2 数据与图审计、正式 `r2/count` run 与产物保存、实测成本。本轮执行两个 seed 0 正式 run、三项 saved-only 检查与 r2 结构审计；未改代码、未改科学协议、未做远端恢复核验。
本轮 run：`p01-r2-sharedridge-001`、`p01-r2-sharedridge-repeat-001`（seed 0，`--purpose formal`）。

## 恢复位置

- 2026-10-12：T006 完成并接受（[D018](decisions.md#d018-t006-r2count-研究侧验收)）。r2 审计：121,420 节点、52 上下文、网格完整、训练 27 月全零 44.64%、邻居覆盖 8.3948%、图完全对称（反向边比例 1.0）。两个正式 run 均 success；`NaiveRef=LastValue`（测试 MAE 6.140083 / RMSE 85.597475），SharedRidge 8.669351 / 167.690727 总体较差；同 seed 预测最大绝对差 0、7,890 指标字段归一化差 0；重算 `source_data_read=false`、`model_refit=false`。成本 2.950 s / 2.217 s，峰值 RSS 1.293 / 1.299 GB。产物保存状态见[索引](archives/index.md#t006-r2count-运行与保存2026-10-12)。
- 2026-10-11：T006 委托回收（[D017](decisions.md#d017-t006-r2count-实现研究侧验收与委托回收)）。`openspec/changes/add-r2-count-baseline` 已归档为 `openspec/changes/archive/2026-10-11-add-r2-count-baseline/`，`verification.md` 为 PASS；按报告 40 文件基准重算，39 个与当前实现一致，唯一差异是报告已排除在 pre-archive 指纹外的主规格归档同步。研究侧接受实现就绪，[DELEGATION](../DELEGATION.md) 关闭为 `closed`，T006 改为 `in_progress`：真实 r2 审计、正式 run/产物与实测成本仍需授权。产物入库与备份状态见[索引](archives/index.md#t006-r2count-实现证据2026-10-11)。
- 2026-10-11：用户接受 [D006](decisions.md#d006-明确主要改善目标)、[D007](decisions.md#d007-检验低活跃节点与邻居信息的假设) 和 [D015](decisions.md#d015-发布图使用范围与重建时机)。当前计划与协议已同步采用说明：完整任务主要评价，先作自身/真实图/打乱图公平对照，达到既有门槛后才推进复杂模块；发布图用于带时间限制的固定评测，暂缓重建。既有科学计算定义、数值门槛和 T006 -> T007 顺序保留；没有新执行或委托。T002 摘要的平方误差占比与高活跃/大需求集合解释勘误见 D006，历史产物不改。
- 2026-10-11：T002 四项收尾完成并接受（[D014](decisions.md#d014-t002-数据与图语义审计研究侧验收)）。产物在 `research/analyses/p01-t002-graph-semantics-20261011-01/`、`p01-t002-graph-time-source-20261011-01/`、`p01-t002-big-demand-cross-20261011-01/`、`p01-t002-adjacency-probe-20261011-01/`。关键结果：图完全对称（反向边比例 1.0）、邻居覆盖 13.45% / 13.37%；图构建时间来源未决；训练 top10% 大需求节点占训练需求 76% / 83% 且 92–96% 孤立，覆盖节点仅承担 5.42% 训练需求；`K=1` 的 `GConvGRU`/`GConvLSTM` 输出与邻接无关（空图与真实图逐元素相同），`EvolveGCNH` 确认使用邻接。四项随 2026-10-11 文档提交入库（提交身份从 Git 历史追溯），未封存、未做异地备份；探针依赖装在本机 `job-sdf-baseline` 环境，不是归档 GPU 环境。
- 2026-10-11：本地 Git 记录显示 PR #9 已于 2026-10-08 合入 `my-change`；合并提交 `7cbfe56` 的文件树与 `98e9fbe` 完全一致，工作区在本轮记录更新前干净。仅合并没有新增实现或科学条件变化，不要求重跑历史验收或更新运行来源 commit。未联网核验当前远端引用；保存事实见[索引](archives/index.md#my-change-pr-合入2026-10-11-接手记录)。
- 2026-10-11：[D013](decisions.md#d013-优先收尾-t002-的候选范围) 已按用户确认接受，T002 收尾范围与顺序固定为：复用首轮审计与 T004 `-002` 产物 -> 场景内入/出度、无向邻居度、反向边比例与场景边数 -> 图构建时间来源 -> 用训练 27 月预先固定规则的大需求×活跃度×邻居覆盖交叉 -> EvolveGCN-H/GConvLSTM/GConvGRU 邻接敏感性独立检查。第 5 项授权安装 `torch`/`torch_geometric_temporal` 在 CPU 上做关联报告，不改正式模型、不参数化 `main.py`，本轮不登记 DELEGATION；源码确认 `benchmark/graph_method/main.py` 对 GConvGRU/GConvLSTM 传 `K=1`；探针随后确认该配置与邻接无关，见 D014。底座 -> `r2` -> 内部回测顺序、协议与主张范围不变，接受本建议不启动正式实验或封存。
- 第二轮清理按 [D012](decisions.md#d012-完成剩余历史与参考材料整理)完成：三个旧预览/探针删除；195 个 tracked 文件原样归入开发历史、探索历史与上游参考，活跃链接及 GPU 指导已更新。本地论文移入 ignored 文献目录，ignored 内容不删除。旧/新路径及历史脚本限制见[映射](archives/migrations/20261008-legacy-cleanup.md)，保存事实见[索引](archives/index.md#t011-历史整理2026-10-08)。
- 2026-10-08：按 [D010](decisions.md#d010-采用实验记录与保存减负政策)采用 `P01-records-v2`，已更新协议 §6.1/§9、计划和执行指导；科学版本仍为 v3。研究论证与执行说明见[review §9](reviews/20261008-maintenance-and-protocol.md#9-采用与执行记录2026-10-08)，新版 skill 已完成，本轮不改 skill。
- 第一轮整理见[记录](archives/migrations/20261008-evidence-maintenance.md)：24 个包和 88 个可读入口原样保留，移除一致的忽略展开副本与缓存；删除 T004 sidecar，全成员哈希清单改为位置/提交/大小/数量与排除声明。检查需要完整输入，按需在独立目录从包展开；`verify` 工具已支持 schema v2 与历史 v1，恢复核验仍仅按明确请求执行。整套减负工作已提交并 push，保存事实见[索引](archives/index.md#t010-软件变更保存事实2026-10-08)。
- `reduce-baseline-evidence-overhead` 已[归档独立 PASS](../openspec/changes/archive/2026-10-08-reduce-baseline-evidence-overhead/verification.md)，五项发现均为 verified-resolved。研究侧在记录更新前比对全部报告基准，主规格为预期 delta 同步；按 [D011](decisions.md#d011-t010-记录减负研究侧验收)接受 T010 并关闭 [DELEGATION](../DELEGATION.md)。报告分轮验证证据与可选 sklearn 限制保留，不重跑全套；科研记录的后续更新不回写历史报告。
- 当前软件已落实 formal/development 输出隔离、单份 `--report` 检查及旧参数别名、相关脏源码恢复、固定来源引用、默认候选产物减量和 Git 包索引兼容；当前入口见[执行指导 §7](phases/P01/execution-guide.md#7-当前可复用-baseline-入口)与[索引](archives/index.md)。没有新增正式科研 run 或封存包，临时软件 fixture 不作为新科学结论。
- T004 已按 [D008](decisions.md#d008-t004-baseline-研究侧验收)接受，旧变更归档 PASS 和核验方法仍保留。科研依据是四个 `-002` 模型执行及八个关联检查；两组 NaiveRef/NaiveRef6 均为 LastValue、Ridge lambda=1e-4、同 seed 预测差为 0，总体测试误差高于 LastValue，不宣称改善。成本、来源与保存事实见[索引](archives/index.md#t004-baseline-运行2026-10-07)。
- 2026-10-08 清理前只读进程列表未发现本地 baseline/封存进程（搜索自身除外）；本轮未启动实验，未核验历史远端 GPU 状态。旧包、包内内容、可读入口和 OpenSpec 历史报告原样保留；当前精简目录不再用于原报告的完整展开证据指纹。取消的远端恢复检查不续跑。

## 下一可执行动作

在途委托：无（[DELEGATION](../DELEGATION.md) 为 `closed`）。T002、T004、T006 已接受；P01 仍 active，T005、T007、T008 未完成。

- 下一可执行动作：P01-T007 训练期内部两折无图回测——按协议 §8 在训练观察期内重构造窗口与预处理，检查收益跨起点；按已接受顺序在 T006 之后进行。T005 的 EvolveGCN-H 受控复跑保留。启动前确认授权与入口。
- 规划后续：T008 冻结具体开发/最终比较数据与骨架，采用 D006/D007/D015；公平对照未执行，复杂模块未启动，严格时间主张所需的图来源仍未满足。
- 保存事实：各批次产物的入库与备份状态见[索引](archives/index.md)；记录文件自身不声明提交状态，其提交身份从版本历史追溯。探针环境仍为本机 CPU conda 环境。

T008 对 T002 的依赖已满足，其余依赖仍待 T005–T007。

## 待处理事项

- [D013](decisions.md#d013-优先收尾-t002-的候选范围)：已接受；四项收尾已按 [D014](decisions.md#d014-t002-数据与图语义审计研究侧验收) 完成并接受。图构建时间未决与 `K=1` 无邻居传播是已记录的结论/限制，不是未收尾项。
- [D005](decisions.md#d005-补存分层分析的可复查过程)：新 baseline 分层证据已补，旧 EvolveGCN 两个 seed 的分层过程及交叉分布仍未补存。
- [D006](decisions.md#d006-明确主要改善目标)：已接受完整任务主要评价；具体开发/最终比较数据与配置仍待 T008 冻结。分组用于解释，不事后替换主目标。
- [D007](decisions.md#d007-检验低活跃节点与邻居信息的假设)：已接受检验路线；T002 已保存交叉分布，公平对照仍待执行，接受规划不等于机制假设成立。
- [D015](decisions.md#d015-发布图使用范围与重建时机)：已接受发布图使用边界及暂缓重建。构建时间仍未知；严格历史/跨时间主张须有时间相符的图证据，暂未启动相关工作。
- [D016](decisions.md#d016-委派-t006-r2count-扩展给-openspec)：已按 [D017](decisions.md#d017-t006-r2count-实现研究侧验收与委托回收) 回收，委托 `closed`；实现 PASS 只证明软件就绪，不是 T006 实验验收。
- [D018](decisions.md#d018-t006-r2count-研究侧验收)：T006 已接受并完成；r2 baseline、审计、重复性、重算与成本见决定正文与[索引](archives/index.md#t006-r2count-运行与保存2026-10-12)。
- T005、T007、T008 的科研工作见阶段计划；P01 尚未完成（T002、T004、T006 已完成）。
- T004 已封存、提交/push；远端恢复未核验，用户取消检查，不列为待补任务。
- D009 的长期建议由 D010 接续，T010 已按 D011 接受并完成主体提交/push；第二轮清理已按 D012 完成，历史路径由迁移映射解释。远端恢复未核验，不安排默认检查；后续保存状态记录的提交身份从 Git 历史追溯。
