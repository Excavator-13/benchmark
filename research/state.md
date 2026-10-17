# 当前状态

更新时间：2026-10-17。
当前阶段：[P01](phases/P01/plan.md)，阶段状态与任务状态以该计划为准。
当前工作：P01-T007 训练期内部两折无图回测已完成，并按 [D021](decisions.md#d021-t007-内部两折回测研究侧验收) 接受为 `done`。12 个正式 fold run（`r0`/`region`/`r2` × A/B 与同 seed 重复）均 `success`，检查与跨折对照完整；三组折间平均 MAE gain 均为负（-8.30% / -5.07% / -12.64%），未满足 §6.2 跨时间正收益条件，Ridge 在六组都不是评估 MAE 最小的规则。T006 已按 [D018](decisions.md#d018-t006-r2count-研究侧验收) 接受；T005 因服务器暂时无法开机暂缓；T008 仅剩 T005 依赖。
当前执行者：本轮运行 12 个正式 fold run、19 份检查、跨折分析与记录更新，并按用户授权提交与推送；未连接服务器，远端 GPU、环境与进程状态未核验。
本次授权范围：正式 fold run、检查、分析、记录更新与 commit/push；不包含封存或恢复核验。
本轮 run：12 个 fold run（见[索引](archives/index.md#t007-内部两折回测运行与保存2026-10-17)）；结果见[两折报告](analyses/p01-t007-backtest-20261017-01/report.md)。可读入口与检查报告随本次记录入库；完整数组仅在本机。

## 恢复位置

- 2026-10-17：T007 结果保存。12 个 run 的 `summary.md`/`provenance.json`/`command.json`、19 份检查报告与两折分析报告随本次记录提交并 push `origin/xzs`；完整数组与 run 目录其余内容已按新增 fold run 忽略规则仅留本机（约 217 MB）。未封存，备份与远端恢复未核验；`.gitignore` 只新增 fold run 规则，未改实现或科学协议。
- 2026-10-17：T007 两折正式运行与验收（[D021](decisions.md#d021-t007-内部两折回测研究侧验收)）。12 个 run 均 success、commit `e919500`、三组数据身份一致；`eval` gain 相对当折 NaiveRef 为 `r0` -19.77% / +3.18%、`region` -11.85% / +1.70%、`r2` -30.41% / +5.12%（A/B），折间平均均负，未满足 §6.2 跨时间条件；Ridge 在六组都不是评估 MAE 最小方法。6 组同 seed 重复预测与指标差 0；12 份 recompute `source_data_read=false`、`model_refit=false`、差 0；fold `align-v2` 按预期拒绝。报告见[两折分析](analyses/p01-t007-backtest-20261017-01/report.md)，保存状态见[索引](archives/index.md#t007-内部两折回测运行与保存2026-10-17)。
- 2026-10-17：T007 实现回收（[D020](decisions.md#d020-t007-内部两折回测实现研究侧验收)）。`openspec/changes/add-nograph-backtest-folds` 已归档为 `openspec/changes/archive/2026-10-17-add-nograph-backtest-folds/`，`verification.md` 为 PASS；把 5 个规划文件映射到归档路径后，报告 37 文件主清单 37/37 单文件 SHA256 一致，无缺失；本机按同款 formal-fold guard 复跑 287 项，285 通过、2 项 sklearn 跳过。确认 `protocol.md` 未改、主切分常量与默认路径保持、`research/runs/` 无正式 fold run、旧 run/封存包/归档未改。研究侧接受实现就绪，DELEGATION 关闭，T007 改为 `in_progress`：正式 fold run、产物与跨折收益仍需授权。保存状态见[索引](archives/index.md#t007-内部两折回测实现证据2026-10-17)。
- 2026-10-13：按 [D019](decisions.md#d019-委派-t007-内部两折回测实现并登记范围)整理 T007：两折固定为 A 拟合 `2021-01..2022-06`（18 月）/验证 `2022-07..09`/开发评估 `2022-10..12`，B 拟合 `2021-01..2022-09`（21 月）/验证 `2022-10..12`/开发评估 `2023-01..03`；覆盖 `r0`/`region`/`r2`，折内活跃度分组用各折拟合观察期。指导见 [T007 执行指导](phases/P01/t007-backtest-guide.md)，实现登记为 `add-nograph-backtest-folds` 委托。本轮未运行 baseline、未改代码、未创建 OpenSpec 变更；T007 仍 `todo`。
- 2026-10-13：完成 [T005 原服务器受控复跑指导](phases/P01/t005-evolvegcnh-guide.md)，集中整理环境/源码/数据核对、唯一输出目录、原 API seed 1 复跑、逐 epoch 选模记录、验证预测、成本、saved-only 重算/分组/重复性比较及取回交接。文档命令通过 Bash/Python 3.8 语法检查；数据核对与 saved-only 比较段用原始数据、归档预测及临时 fixture 检查通过，未拟合或推理模型，不构成新科研结果。用户初称原服务器仍保留，随后表示该服务器暂时无法开机，T005 暂缓；本轮未连接或核验它，GPU 训练段尚未实机核验，未启动实验、未修改运行实现或科学协议。T005 保持 `todo`；准备指导不等于开始实验。
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

在途委托：无（[DELEGATION](../DELEGATION.md) 为 `closed`）。T002、T004、T006、T007 已完成；T005 暂缓，T008 未完成。P01 仍 active。

- 下一准备动作：T007 已完成，不再排 fold run。P01 剩余可推进的是 T008（阶段汇总、骨架与数据冻结）；计划仍列 T005 为 T008 依赖，T005 等服务器恢复，或在用户明确同意调整依赖后先做 T008 的其余部分。
- 暂缓：P01-T005 等用户服务器恢复后再继续；[T005 指导](phases/P01/t005-evolvegcnh-guide.md)已备。
- 规划后续：T008 冻结具体开发/最终比较数据与骨架，采用 D006/D007/D015；公平对照未执行，复杂模块未启动，严格时间主张所需的图来源仍未满足。
- 保存事实：各批次产物的入库与备份状态见[索引](archives/index.md)；记录文件自身不声明提交状态，其提交身份从版本历史追溯。探针环境仍为本机 CPU conda 环境。

T008 对 T002、T004、T006、T007 的依赖已满足，仅 T005 因服务器暂缓。

## 待处理事项

- [D013](decisions.md#d013-优先收尾-t002-的候选范围)：已接受；四项收尾已按 [D014](decisions.md#d014-t002-数据与图语义审计研究侧验收) 完成并接受。图构建时间未决与 `K=1` 无邻居传播是已记录的结论/限制，不是未收尾项。
- [D005](decisions.md#d005-补存分层分析的可复查过程)：新 baseline 分层证据已补，旧 EvolveGCN 两个 seed 的分层过程及交叉分布仍未补存。
- [D006](decisions.md#d006-明确主要改善目标)：已接受完整任务主要评价；具体开发/最终比较数据与配置仍待 T008 冻结。分组用于解释，不事后替换主目标。
- [D007](decisions.md#d007-检验低活跃节点与邻居信息的假设)：已接受检验路线；T002 已保存交叉分布，公平对照仍待执行，接受规划不等于机制假设成立。
- [D015](decisions.md#d015-发布图使用范围与重建时机)：已接受发布图使用边界及暂缓重建。构建时间仍未知；严格历史/跨时间主张须有时间相符的图证据，暂未启动相关工作。
- [D016](decisions.md#d016-委派-t006-r2count-扩展给-openspec)：已按 [D017](decisions.md#d017-t006-r2count-实现研究侧验收与委托回收) 回收，委托 `closed`；实现 PASS 只证明软件就绪，不是 T006 实验验收。
- [D018](decisions.md#d018-t006-r2count-研究侧验收)：T006 已接受并完成；r2 baseline、审计、重复性、重算与成本见决定正文与[索引](archives/index.md#t006-r2count-运行与保存2026-10-12)。
- [D019](decisions.md#d019-委派-t007-内部两折回测实现并登记范围)：已按 [D020](decisions.md#d020-t007-内部两折回测实现研究侧验收) 回收，委托 `closed`；实现 PASS 只证明软件就绪，不是 T007 实验验收。
- [D020](decisions.md#d020-t007-内部两折回测实现研究侧验收)：T007 实现已接受；实验已按 [D021](decisions.md#d021-t007-内部两折回测研究侧验收) 完成。
- [D021](decisions.md#d021-t007-内部两折回测研究侧验收)：T007 两折回测已完成并接受；三组折间平均 gain 均负，未满足跨时间条件，不宣称改善。
- T005、T008 的科研工作见阶段计划；P01 尚未完成（T002、T004、T006、T007 已完成；T005 暂缓）。
- T004 已封存、提交/push；远端恢复未核验，用户取消检查，不列为待补任务。
- D009 的长期建议由 D010 接续，T010 已按 D011 接受并完成主体提交/push；第二轮清理已按 D012 完成，历史路径由迁移映射解释。远端恢复未核验，不安排默认检查；后续保存状态记录的提交身份从 Git 历史追溯。
