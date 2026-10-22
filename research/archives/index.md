# 实验与归档索引

更新日期：2026-10-18。研究交接见[当前状态](../state.md)，任务验收见[阶段计划](../phases/P01/plan.md)。运行成功、已封存、已入库和已备份分别记录。

## 已有运行

| Run / legacy ID | 类型与目的 | 摘要/执行结果 | 保存状态与身份 | 备份核验 |
| --- | --- | --- | --- | --- |
| `1st_try_in_phase_fix_origin` | experiment；修复版 `region/count` EvolveGCN-H，seed 0/1 各 500 epoch | [实际执行记录](../../experiments_archive/1st_try_in_phase_fix_origin/what_we_did_this_time.md#本次实际执行记录与指南的差异与结果)；两运行完成 | 预测、标签、checkpoint、日志已入库 `5918872`；历史无统一 SHA256 清单 | `origin/xzs` 已确认包含该历史；2026-10-06 远端引用核验，未逐文件取回 GPU 产物 |
| `phase1-20261006-v2-01` | audit；两组朴素基线、身份/图审计及旧结果对齐 | [原样摘要](../runs/phase1-20261006-v2-01/summary.md)；诊断通过 | [封存包](../../experiments_archive/phase1/phase1-20261006-v2-01.tar.gz)与 [SHA256](../../experiments_archive/phase1/phase1-20261006-v2-01.tar.gz.sha256)入库 `4470bd4`；13 个展开文件入库 `f66959b` 并原样迁入标准 runs | 2026-10-06 从远端目标提交取回归档包，SHA256 和本地包一致；已核验可读取 |

### 首次 GPU 实验的范围

源码基准为 `950a1d8febbf992b8bda061d35f03107d0b18478`，机器为 Tesla T4。依赖和设备条件见历史目录的 logs。

- seed 0：MAE 41.080686，RMSE 238.957775。
- seed 1：MAE 96.180772，RMSE 579.504594。
- 没有同 seed 复跑，不能由两个运行认定初始化方差或稳定平均性能。
- 历史说明前半是指南，末尾才是实际执行；旧源码修复报告见[首次核验](legacy-development/verification_20260921/REPORT.md)和[修复后核验](legacy-development/fix_verification_20260921/REPORT.md)。它们不替代当前版本核验。

### 第一阶段诊断的范围

执行于 2026-10-06，运行源码基准 `341e7f8362904bc3a504736335ee6407c112843c`，协议 v2。两个数据集验证选定 LastValue；图无频率列且邻居覆盖约 13.4%；旧 gold 与当前标签逐元素一致，指标可复算。

这是诊断产物，没有共享 Ridge 或正式实验完整预测/参数。13 个文件保持与旧包内容一致；没有追溯添加 provenance.json 或命令日志。未来新运行使用 skill 模板。

包 SHA256：`4c9a08f3e65139afb7353bbcb47de70c7afef9dcf98f81f50e7d42b79cb58dad`。

在仓库根目录核验：

```bash
shasum -a 256 -c experiments_archive/phase1/phase1-20261006-v2-01.tar.gz.sha256
```

旧摘要中的“未推送”描述封存时状态，保持不变。旧 `planning-sha256.txt` 使用原目录路径；首次标准化的内容核验由 `verify_20261006.py` 按当时映射完成，不改写封存清单。该脚本包含相对旧基准的全工作树不变断言，后续实现与整理已超出其适用时点，不能作为当前 HEAD 的全仓库检查，限制见[本次映射](migrations/20261008-legacy-cleanup.md)。

## T004 baseline 运行（2026-10-07）

所属任务：P01-T004；协议 `P1-count-L6-H3-v3`。研究验收见 [D008](../decisions.md#d008-t004-baseline-研究侧验收)，独立实现核验见 [PASS 报告](../../openspec/changes/archive/2026-10-07-add-nograph-baseline-ridge/verification.md)。以 `-002` 的四个模型 run 和八个检查为本次验收依据；`-001` 保留为历史版本。

以下 24 个 run 的共同保存状态：**sealed，包与可读入口已提交并 push 至 origin/xzs**。实现提交 `8273c07a84c879a8f7bdbb61f987f3c94e863e59`，证据与科研记录提交 `b72770873f11a66478c3556973393882be501bd8`；当时 push 成功且独立读取远端引用一致。远端恢复未核验，用户取消检查，不作为待办。每个包位于 `research/archives/<run-id>.tar.gz`；位置、大小、成员数量、保存包的 Git commit 与排除项见 [包索引](p01-baseline-20261007-manifest.json)。

2026-10-08 按 [D010](../decisions.md#d010-采用实验记录与保存减负政策) 整理：24 个包字节与上述提交一致，88 个 summary/provenance/command/report 可读入口原样保留；24 个包外 sidecar 删除，包外全成员哈希清单改为简洁索引，692 个一致的忽略展开副本移除。需要数组时从包展开到独立目录。新索引与整理记录已随本次减负工作提交/push，保存身份见下文 T010；既有包的历史保存事实不变。过程见[整理记录](migrations/20261008-evidence-maintenance.md)。

封存排除任意深度 `__pycache__/`、`.DS_Store`、`._*`；包内 artifact 哈希清单另排除自身和 `events.jsonl`，后两者仍在包中。排除声明是来源信息，随新索引保留。包在 Git 中以其保存提交定位内容，无需包外 SHA256 或全成员哈希表；导出到 Git 外交付时再提供包外 SHA256。

### 当前实验依据与历史模型运行

每个模型 run 含五项朴素基线及共享 Ridge，74 个文件，其中 72 个为清单成员。primary/repeat 均为 seed 0；它们是同条件重复，不是不同初始化样本。

| 数据 / 版本 | Primary 摘要与 Run ID | Repeat 摘要与 Run ID | 执行结果（2026-10-07） | 证据角色 |
| --- | --- | --- | --- | --- |
| r0 / 001 | [p01-r0-sharedridge-001](../runs/p01-r0-sharedridge-001/summary.md) | [p01-r0-sharedridge-repeat-001](../runs/p01-r0-sharedridge-repeat-001/summary.md) | 两运行 success/complete | 修复前历史，保留原样 |
| region / 001 | [p01-region-sharedridge-001](../runs/p01-region-sharedridge-001/summary.md) | [p01-region-sharedridge-repeat-001](../runs/p01-region-sharedridge-repeat-001/summary.md) | 两运行 success/complete | 修复前历史，保留原样 |
| r0 / 002 | [p01-r0-sharedridge-002](../runs/p01-r0-sharedridge-002/summary.md) | [p01-r0-sharedridge-repeat-002](../runs/p01-r0-sharedridge-repeat-002/summary.md) | 两运行 success/complete，同条件预测最大绝对差 0 | 本次研究验收依据 |
| region / 002 | [p01-region-sharedridge-002](../runs/p01-region-sharedridge-002/summary.md) | [p01-region-sharedridge-repeat-002](../runs/p01-region-sharedridge-repeat-002/summary.md) | 两运行 success/complete，同条件预测最大绝对差 0 | 本次研究验收依据 |

### 关联开发与分析检查（旧格式）

每行列出两个旧格式 check run，属于关联检查，不是 16 次独立模型实验；链接是不可改写的输出报告。封存时 16 个状态文件均为 success/complete（现位于包内）；`-002` 的四个重算、两个重复性检查及两个 v2 对齐均为 ok。原始输入与命令见可读 `provenance.json`/`command.json`。新政策不再要求检查拥有完整 run。

| 检查 | r0 Run ID / 报告 | region Run ID / 报告 | 证据角色 |
| --- | --- | --- | --- |
| primary 重算 / 001 | [p01-r0-recompute-primary-001](../runs/p01-r0-recompute-primary-001/report.json) | [p01-region-recompute-primary-001](../runs/p01-region-recompute-primary-001/report.json) | 历史 |
| repeat 重算 / 001 | [p01-r0-recompute-repeat-001](../runs/p01-r0-recompute-repeat-001/report.json) | [p01-region-recompute-repeat-001](../runs/p01-region-recompute-repeat-001/report.json) | 历史 |
| 同 seed 比较 / 001 | [p01-r0-repeat-check-001](../runs/p01-r0-repeat-check-001/report.json) | [p01-region-repeat-check-001](../runs/p01-region-repeat-check-001/report.json) | 历史 |
| v2 对齐 / 001 | [p01-r0-alignment-001](../runs/p01-r0-alignment-001/report.json) | [p01-region-alignment-001](../runs/p01-region-alignment-001/report.json) | 历史 |
| primary 重算 / 002 | [p01-r0-recompute-primary-002](../runs/p01-r0-recompute-primary-002/report.json) | [p01-region-recompute-primary-002](../runs/p01-region-recompute-primary-002/report.json) | 本次验收；saved-only，不读源数据、不重新拟合 |
| repeat 重算 / 002 | [p01-r0-recompute-repeat-002](../runs/p01-r0-recompute-repeat-002/report.json) | [p01-region-recompute-repeat-002](../runs/p01-region-recompute-repeat-002/report.json) | 本次验收；saved-only |
| 同 seed 比较 / 002 | [p01-r0-repeat-check-002](../runs/p01-r0-repeat-check-002/report.json) | [p01-region-repeat-check-002](../runs/p01-region-repeat-check-002/report.json) | 本次验收；所有方法与划分预测最大绝对差 0 |
| v2 对齐 / 002 | [p01-r0-alignment-002](../runs/p01-r0-alignment-002/report.json) | [p01-region-alignment-002](../runs/p01-region-alignment-002/report.json) | 本次验收；每组 411 字段、零差异 |

### 内容身份与恢复限制

2026-10-07T19:53+08:00 只读核对：780 个文件（排除 Python 缓存），内容合计 76,206,301 bytes；所有 24 个 `artifacts-sha256.json` 的 732 个成员逐文件 SHA256 一致。清单声明排除自身与 `events.jsonl`（共 48 文件）；这些仍包含在 PASS 报告的完整 formal_evidence 指纹中。

- 全集 inventory SHA256：`db042f6104247130bca08595cf192b82e29254b4f32c4d5dc52cffc4fc64276a`。
- 全集 content SHA256：`0dd5e80a29d0e9767eb7ed981f33b66932ffead3b14c45aadc494227dc945fb5`。
- 算法：报告的排序相对路径清单与 `path + NUL + file_SHA256 + newline` 聚合规则；是清理前完整展开目录的历史内容身份。原包外 SHA256/全成员表在保存提交的 Git 历史中，当前不重复维护。
- 运行代码基准：`a0fdab4268e5e17b0c96453efd53f01a245f01cc` 加执行时保存的 diff、未跟踪源码快照及来源清单。两版身份分别以各自 run 为准；后续修复的 checker 与运行时快照有差异，已由独立报告说明，不回写旧 run。
- 环境：本地 macOS arm64 CPU，Python 3.11.17、NumPy 1.26.4、pandas 2.2.3、PyArrow 17.0.0；线程设置与完整环境在各模型目录。sklearn 未安装，实际可选后端未验证。
- 产物定位：模型包内包含 `predictions/`、`gold/`、`models/`、`candidates/`、节点/窗口身份、分组掩码、配置/协议/来源/命令、`metrics.json`、`node-errors.parquet` 与 `measurements.json`。包内 `artifacts-sha256.json` 原样保留；当前展开目录仅有可读入口。
- 封存核验：24 个包合计 41,446,332 bytes；排除缓存和系统元数据，所有成员为各 run 下的普通文件，拒绝绝对路径、父目录跳转、链接与重复成员。在新的临时目录解包后核对全部 780 文件 SHA256，并与核验报告的全集内容指纹一致；封存前后原目录身份一致。
- 2026-10-07 保存收尾按当时协议与 [D009](../decisions.md#d009-约束证据数量与-git-保存边界)执行，未删改原始 run。2026-10-08 后续整理按 D010 移除一致的展开副本，保留包与入口；历史报告仍描述其原核验时点，当前目录不再用于重算旧 formal_evidence 全集指纹。

需要完整模型证据时，按指定 Git 提交与包路径定位，只展开所需包到新的空目录，不覆盖已有 run。例如在仓库根目录，下面创建独立临时目录并展开一个模型包：

```bash
P01_RESTORE_DIR=$(mktemp -d)
tar -xzf research/archives/p01-r0-sharedridge-002.tar.gz -C "$P01_RESTORE_DIR"
```

输出为 `$P01_RESTORE_DIR/p01-r0-sharedridge-002/`，将此路径作为 checker 的输入。按包内配置/协议与来源身份重算，不直接覆盖已有 run。`command.json` 记录原机器的绝对路径，须映射到实际位置；这是按需展开说明，不是本轮实际恢复核验或全新环境重训验证。

`seal_20261007_baseline.py verify` 已支持当前 schema v2：由索引的固定 Git commit/path 核对包内容身份，检查成员安全、数量与排除声明，再恢复到新的临时位置；不依赖 sidecar 或全成员哈希表。历史 schema v1 的 checksum 验证仍支持。`seal` 是旧 v1 封存功能，仍拒绝覆盖已有产物，不要在精简目录重新 seal。该工具只在明确请求核验时运行，本轮未执行；按需展开可使用上面的单包说明。历史完整元数据仍能从 `b727708...` 查阅。

当前 `recompute`、`compare`、`align-v2` 对完整/已展开模型输入写单份 `--report PATH` JSON（返回 `report_path`），不生成新实验目录或改写输入。旧 `--run-id`/`--runs-root` 检查参数映射为单份报告路径。若原目录只有可读入口，先按实际需要在独立目录展开所需包；不将展开/重算安排成默认恢复检查。命令见[执行指导 §7](../phases/P01/execution-guide.md#7-当前可复用-baseline-入口)。

## T010 软件变更保存事实（2026-10-08）

`reduce-baseline-evidence-overhead` 已在[OpenSpec 目录归档](../../openspec/changes/archive/2026-10-08-reduce-baseline-evidence-overhead/verification.md)，独立报告 PASS；研究侧按 [D011](../decisions.md#d011-t010-记录减负研究侧验收)核对基准并接受。没有新增正式科研 run 或封存包；适用的 T004 历史科学证据保留，格式/软件行为由临时 fixture 与独立报告证明，不把 fixture 当新预测结论。

用户随后明确要求提交、推送整轮减负工作。保存提交：`b701585eab9671c9c3aaddf36ece5b0b75acd76a`（58 个文件变更，包含维护者的 skill 修改、协议/当前说明、已验收实现/测试、主规格、OpenSpec 完整归档、包外元数据清理与研究侧收尾）。2026-10-08 正常 `git push origin xzs` 成功，目标为 `git@github.com:Excavator-13/benchmark.git` 的 `xzs`，push 回报 `715d44d..b701585`。没有独立远端取回或恢复核验，不因此追加检查；既有 T004 包的保存身份保留。

本次仅检查提交范围、沿用当前实现仍匹配的独立 PASS，并执行 Git 保存；未重跑测试、实验、封存或恢复检查。后续本页/state 的保存事实更新作为普通文档提交，其自身身份从 Git 历史追溯，不继续生成回执或改写封存材料。

## T011 历史整理（2026-10-08）

按 [D012](../decisions.md#d012-完成剩余历史与参考材料整理)完成剩余清理；旧/新路径见[迁移记录](migrations/20261008-legacy-cleanup.md)。开发历史见[入口](legacy-development/README.md)，探索历史见[入口](legacy-exploration/README.md)，上游参考及本地文献见[说明](../../references/README.md)。

195 个 tracked 文件与整理前 `e36e374` 的对应内容逐字节一致，删除范围仅三个失效探针/预览；活跃链接/锚点检查通过，当前指导示例仅做语法检查，`git diff --check` 通过。dataset、运行实现（除移走两份历史探索来源）、封存包、run 与 OpenSpec 归档不变，不运行实验、完整测试或恢复演练。本地 PDF 原样改位置并继续忽略，其他 ignored 内容不删除；PDF 本身不随 Git 备份。

迁移与入口更新保存于 `77598faef8d90bff621456786ca27b045b3122fb`，2026-10-08 正常 `git push origin xzs` 成功，回报 `e36e374..77598fa`；没有独立远端取回或恢复核验。既有内容可从原 Git 路径追溯。没有新 run、封存包或哈希清单，也不把纯路径变化当作新软件行为验证。本页与 state 的保存状态更新随普通文档提交同步，自身提交身份从 Git 历史追溯，不继续新增回执。

## T002 分析与检查产物（2026-10-11）

所属任务 P01-T002，按 [D013](../decisions.md#d013-优先收尾-t002-的候选范围) 收尾、[D014](../decisions.md#d014-t002-数据与图语义审计研究侧验收) 接受。四项产物位于 `research/analyses/`，各自含 report、脚本或准确命令、结果 JSON/log 与输入身份文件（`source-sha256.txt`、`git-commit.txt`，探针另含 `environment.txt`）：

| 产物 | 内容 |
| --- | --- |
| [p01-t002-graph-semantics-20261011-01](../analyses/p01-t002-graph-semantics-20261011-01/report.md) | 场景内入/出度、无向邻居度、反向边比例、覆盖与场景边数 |
| [p01-t002-graph-time-source-20261011-01](../analyses/p01-t002-graph-time-source-20261011-01/report.md) | 图构建时间来源查证与固定图历史回测限制 |
| [p01-t002-big-demand-cross-20261011-01](../analyses/p01-t002-big-demand-cross-20261011-01/report.md) | 训练期大需求 × 活跃度 × 邻居覆盖 × 误差贡献交叉 |
| [p01-t002-adjacency-probe-20261011-01](../analyses/p01-t002-adjacency-probe-20261011-01/report.md) | GConvGRU/GConvLSTM（`K=1`）与 EvolveGCNH 的邻接敏感性 |

保存状态：随 2026-10-11 文档提交入库（提交身份从 Git 历史追溯）；**未封存，异地备份与远端恢复未核验**。不是实验 run，不作封存，不修改既有 24 个 T004 包、旧 run、可读入口或 OpenSpec 归档。需要完整模型数组时仍按上文展开旧包。探针依赖装在本机 conda 环境 `job-sdf-baseline`（torch 2.14.1、torch-geometric 2.8.0.post1、torch_sparse/torch_scatter 源码编译、torch_geometric_temporal 0.56.2），不是归档 GPU 实验环境。

## T006 r2/count 实现证据（2026-10-11）

所属任务 P01-T006。OpenSpec 变更 `add-r2-count-baseline` 已归档，独立报告为 [`Verdict: PASS`](../../openspec/changes/archive/2026-10-11-add-r2-count-baseline/verification.md)；研究侧按 [D017](../decisions.md#d017-t006-r2count-实现研究侧验收与委托回收) 接受其实现就绪证据，并关闭 [DELEGATION](../../DELEGATION.md) 指针。

回收时只读核对：活跃变更目录已不存在；按报告 40 文件清单重算 SHA256（变更目录映射到归档路径），39 个与当前工作区实现一致，无缺失；唯一差异是主规格 `openspec/specs/nograph-baseline-entry/spec.md`，即报告明确排除在 pre-archive 指纹外的归档同步。

证据性质与限制：`r2/count` 的入口/检查/成本证据来自临时 fixture 与 `--purpose development` 运行（合成 121,420 节点、52 上下文，读取/拟合/推理合计约 2.1 秒），**不是真实 r2 实验、成本或预测结论**；可选 sklearn 未执行。真实 `r2` 审计、正式 run、产物保存与实测成本随后于 2026-10-12 完成，见下节。没有新 run、封存包或备份核验；既有 24 个 T004 包、旧 run、旧 OpenSpec 归档与科学协议未改。

保存状态：实现、测试、文档、主规格与归档变更目录随 `7f6b5e4e66d0457a9151f47456c178cac082ca96` 提交并 push `origin/xzs`（此前在报告核验时未提交）。**未封存，备份与远端恢复未核验**；提交身份从 Git 历史追溯。

## T006 r2/count 运行与保存（2026-10-12）

所属任务 P01-T006；研究侧验收见 [D018](../decisions.md#d018-t006-r2count-研究侧验收)，审计与分析见 [r2 审计报告](../analyses/p01-t006-r2-audit-20261012-01/report.md)。两个正式 run 均为 `--purpose formal`、seed 0、本机 CPU（`job-sdf-baseline`）：

| Run ID | 执行结果 | 保存包 | 包内成员 | 包外 SHA256 |
| --- | --- | --- | ---: | --- |
| `p01-r2-sharedridge-001` | success | `research/archives/p01-r2-sharedridge-001.tar.gz`（27,627,768 bytes） | 40 | 不需要（包在 Git 内，内容身份为保存它的提交） |
| `p01-r2-sharedridge-repeat-001` | success | `research/archives/p01-r2-sharedridge-repeat-001.tar.gz`（27,627,856 bytes） | 40 | 同上 |

- 打包排除 `__pycache__/`、`.DS_Store`、`._*`；核验方式：解包到新的临时目录后 `diff -r` 与 `research/runs/<run-id>/` 一致（内容与成员数 40 均相同）。包在 Git 内，内容身份由保存它的提交承担，提交身份从 Git 历史追溯，不另建包外清单或 sidecar。
- 可读入口 `summary.md`、`provenance.json`、`command.json` 随 run 目录入库；`predictions/`、`gold/`、`node-errors.parquet`、`masks.npz`、`nodes.parquet`、`models/` 等展开数组**仅保留在本机**并被 `.gitignore` 忽略，需要时按上面的包在独立目录展开。
- 关联 saved-only 检查报告（入 Git）：`research/reports/nograph-baseline/p01-r2-recompute-primary-001.json`、`p01-r2-recompute-repeat-001.json`、`p01-r2-repeat-check-001.json`。
- 备份状态：包与可读入口随 2026-10-12 的 push 到 `origin/xzs`；**未做独立远端取回或恢复核验**。原始 run 源码身份见各 run 的 `provenance.json`（固定 commit 加相关差异）。

## T007 内部两折回测实现证据（2026-10-17）

所属任务 P01-T007。OpenSpec 变更 `add-nograph-backtest-folds` 已归档，独立报告为 [`Verdict: PASS`](../../openspec/changes/archive/2026-10-17-add-nograph-backtest-folds/verification.md)；研究侧按 [D020](../decisions.md#d020-t007-内部两折回测实现研究侧验收) 接受其实现就绪证据，并关闭 [DELEGATION](../../DELEGATION.md) 指针。

回收时只读核对：活跃变更目录已不存在；按报告 37 文件主清单重算 SHA256（5 个规划文件映射到归档路径）后 37/37 一致，无缺失；报告聚合指纹仅因路径映射不同。另核对 `research/phases/P01/protocol.md` 未改、主切分常量与默认路径保持、`research/runs/` 无正式 fold run、旧 run/封存包/`experiments_archive/`/既有 OpenSpec 归档未改；本机按报告同款 formal-fold guard 复跑 287 项测试，285 通过、2 项 sklearn 跳过。回收核对后执行指导 §7 只做过一次记录性入口文字更新。

证据性质与限制：折入口、产物、`recompute`/`compare` 与 `align-v2` 拒绝来自临时 fixture 与 `--purpose development` 运行（报告 E1/E2），**不是真实数据的折实验结果、收益或成本结论**；可选 sklearn 后端动态未执行；继承的 r2-scale 成本记录是旧测量。正式 fold run 与保存尚未获授权。

保存状态：实现、测试、文档、主规格与归档变更目录随本次记录提交入库并 push `origin/xzs`；该提交同时包含本索引条目，提交身份从 Git 历史追溯。**未封存，备份与远端恢复未核验**。没有新增 run、封存包或备份核验；既有 T004/T006 包、旧 run、旧 OpenSpec 归档与科学协议未改。

## T007 内部两折回测运行与保存（2026-10-17）

所属任务 P01-T007；研究侧验收见 [D021](../decisions.md#d021-t007-内部两折回测研究侧验收)，分析见[两折报告](../analyses/p01-t007-backtest-20261017-01/report.md)。12 个正式 run 均 seed 0、`--purpose formal`、运行代码 commit `e9195006dc402d2ce6fb5afb3a164dfef699200c`、`success`；同 seed 主/重复各一组。

| 数据 | A 折 | A 折重复 | B 折 | B 折重复 | 每组大小 |
| --- | --- | --- | --- | --- | --- |
| `r0` | `p01-r0-backtest-a-001` | `p01-r0-backtest-a-repeat-001` | `p01-r0-backtest-b-001` | `p01-r0-backtest-b-repeat-001` | 约 1.5 MB |
| `region` | `p01-region-backtest-a-001` | `p01-region-backtest-a-repeat-001` | `p01-region-backtest-b-001` | `p01-region-backtest-b-repeat-001` | 约 7.9 MB |
| `r2` | `p01-r2-backtest-a-001` | `p01-r2-backtest-a-repeat-001` | `p01-r2-backtest-b-001` | `p01-r2-backtest-b-repeat-001` | 约 45 MB |

- 结果摘要：`eval` gain 相对当折 NaiveRef 为 `r0` -19.77% / +3.18%、`region` -11.85% / +1.70%、`r2` -30.41% / +5.12%（A/B）；折间平均均负，未满足协议 §6.2 的跨时间正收益条件。Ridge 在六组都不是评估 MAE 最小方法；主评测三组仍显著为负。完整表与限制见分析报告。
- 检查：6 组同 seed `compare` 均 `ok`，预测与指标差 0；12 份 `recompute` 均 `ok`，`source_data_read=false`、`model_refit=false`、最大差 0；fold `align-v2` 按预期失败并留下报告。19 份检查报告位于 `research/reports/nograph-baseline/`（12 recompute、6 repeat-check、1 align-v2 拒绝）。
- 保存状态：12 个 run 的 `summary.md`、`provenance.json`、`command.json`，19 份检查报告与两折分析报告随本次记录提交并 push `origin/xzs`；提交身份从 Git 历史追溯。完整预测、标签、模型、掩码、节点误差与 run 目录其余文件仍**仅在本机**（约 217 MB），已加入 `.gitignore` 的 fold run 规则，不上传；**未封存，未做异地备份或恢复核验**。后续需要完整数组或封存时另行处理。
- 身份：运行代码 commit `e9195006dc402d2ce6fb5afb3a164dfef699200c`；三组 demand 与节点键 SHA256 见分析报告 §2，12 个 run 一致。

没有新增封存包；既有 T004/T006 包、旧 run、旧 OpenSpec 归档与科学协议未改。

## T005 原服务器受控复跑（2026-10-18）

所属任务 P01-T005；[执行指导](../phases/P01/t005-evolvegcnh-guide.md)；研究侧验收见 [D022](../decisions.md#d022-t005-受控复跑研究侧验收)。

| 项目 | 值 |
| --- | --- |
| run ID | `p01-region-evolvegcnh-seed1-repeat-20261018T004254Z` |
| 状态 / 退出码 | `succeeded` / `exit 0` |
| 条件 | 源码基准 `950a1d8febbf992b8bda061d35f03107d0b18478`；`region/count`、`EvolveGCNH`、seed 1、500 epoch、L6/H3、原始 count |
| 设备与环境 | Tesla T4 / 驱动 `535.216.01` / CUDA 12.2 / torch `2.3.0+cu121` / Python 3.8.20；`pip freeze` 与归档旧清单逐字节一致；显存上报 `16384 MiB`（旧记录 `15360 MiB`），无法确认同一物理 GPU |
| 选模 | 验证 MSE，选中 epoch `461`，`best_validation_MSE = 70053.0625`；重载验证 MSE 相同（MAE 55.239 / RMSE 264.675） |
| 测试指标 | MAE `96.18077182769775` / RMSE `579.5045937857179`；float64 重算 MAE `96.18076957532733` |
| 与旧 seed 1 比较 | `exact_prediction_match=true`、最大绝对预测差 `0.0`、归一化 MAE 差 `0.0`、`labels_identical=true`；负预测比例两侧同为 `0.16100234526358723` |
| 成本 | 加载 1.33 s；训练+测试 80.34 s；峰值 RSS 1,197,146,112 bytes；峰值 CUDA allocated 298,932,224 / reserved 329,252,864 bytes |
| 证据 | `condition-review.md`、`comparison.json`、`selection.json`、`cost.json`、`status.json`、`environment.json`、`inputs.json`、`pip-freeze.txt`、`nvidia-smi.txt`、`training-trace.jsonl`（1,000 条）、`outputs/count/region/EvolveGCNH/1/` |

- 保存状态：整目录已取回本机 `research/runs/p01-region-evolvegcnh-seed1-repeat-20261018T004254Z/`（4.3 MB），含 checkpoint、测试/验证预测与标签。随本次记录提交入库并 push `origin/xzs`，提交身份从 Git 历史追溯（同一提交包含本条目）。**未封存，备份与远端恢复未核验**。
- 入库范围：与本项目批量 run 的"可读入口入库、数组留本机"不同，本 run 体积小且预测/checkpoint 就是复现证据，故整目录入库、不新增忽略规则；与 T004/T006/T007 的减量政策不冲突（那些对象是数十至数百 MB 的批量产物）。
- 首个尝试 `p01-region-evolvegcnh-seed1-repeat-20261018T003044Z` 在 §6 成本测量行失败（`torch.cuda.reset_peak_memory_stats` 未初始化 CUDA），`status.json=failed`、无训练产物；保留在服务器 `~/t005-runs/`，未取回本机。指导 §6 已按 2026-10-18 实机诊断补 `torch.cuda.init()`，该改动只影响成本统计起点。
- 限制：单 seed 的一次同条件重复，不是初始化方差或稳定平均性能的估计；模型仍差于 `NaiveRef=LastValue`（测试 MAE 96.18 vs 35.31）；发布图构建时间未知；显存上报差异未解释。以上限制不因逐张量一致而消失。

## T008 阶段汇总（2026-10-18）

所属任务 P01-T008；研究侧验收见 [D023](../decisions.md#d023-t008-阶段验收与-p02-骨架范围)。[P01 阶段汇总](../analyses/p01-t008-stage-summary-20261018-01/report.md) 综合 T001–T007 的已接受结果与限制，不新增预测或指标计算；[P02 计划](../phases/P02/plan.md) 记录冻结配置与骨架，但 P02 未启动。

- 保存状态：随本次记录提交入库并 push `origin/xzs`，提交身份从 Git 历史追溯。**未封存，备份与远端恢复未核验**。这不是实验 run，无包、无新增预测，因此没有独立的内容身份或包外校验。
- 内容：逐任务证据表、七项阶段完成条件判定、进入第二阶段的四个条件（"自身时序学习基线"为有条件满足）、P01 未证明事项清单。
- 边界：P02 的实现变更名 `add-graph-value-skeleton` 只是预登记，未调用任何 OpenSpec 流程、未改代码、未运行新实验。

## P02-T001 骨架实现证据（2026-10-19）

所属任务 P02-T001。OpenSpec 变更 `add-graph-value-skeleton` 已归档，独立报告为 [`Verdict: PASS`](../../openspec/changes/archive/2026-10-19-add-graph-value-skeleton/verification.md)（2026-10-19T10:41:02Z）；研究侧按 [D025](../decisions.md#d025-p02-t001-实现研究侧验收与委托回收) 接受实现就绪证据，并关闭 [DELEGATION](../../DELEGATION.md) 指针。

回收时只读核对：活跃变更目录已不存在；报告 Verification Basis 为 `785a32db38c61fbeeae12ddbda58a656fffb0515` 加 8 个脏实现/测试文件的内容哈希，按报告逐个重算 8/8 与当前工作区一致；另核对 `research/runs/` 无正式 run，旧 run、封存包、`experiments_archive/`、既有 OpenSpec 归档与科学协议未改；`openspec/specs/graph-value-skeleton/spec.md` 与归档 delta 仅差主规格头部与 `Requirements` 标题。

口径：`nn.GRU(1,32)` 逐节点编码 + 共享 `nn.Linear(32,3)`；自身分支为空聚合；图分支 `h + mean_{distinct N_in(v)} h_u`，孤立节点零消息逐元素等于自身分支；参数量 GRU 3,360 + head 99 = 3,459、graph-only 参数为空；打乱图为场景内保入/出度双边交换（seed 0/1/2，三成员 MAE 平均）；200 epoch、Adam、hidden 32、验证 MSE 选模；复用 P01 数据/窗口/掩码/`NaiveRef=LastValue` 身份。

证据性质与限制：实现行为来自合成 fixture 与 `--purpose development` 运行，另有一次限定范围的发布 `r0` 自身分支冒烟；**不是真实 `region`/`r2` 训练、发布图真实打乱或成本结论**，也不构成图收益主张；发布图构建时间仍未知。正式 P02-T002 对照运行与统一成本确认尚未获授权。

保存状态：本次收尾分两次提交入库并 push `origin/xzs`——`785a32d`（实现包 14 个模块、10 个测试模块、`README` §4.6 与 OpenSpec 规划/归档前工件）与 `57a733f`（归档目录、`graph-value-skeleton` 主规格、8 个验证修复实现/测试文件与本次研究记录）；上述提交已在本次 push 中同批到达远端。**未封存，备份与远端恢复未核验**。没有新增 run 或封存包。

## P02-T002 成本预检批次（2026-10-19）

产物为 `p02-t002-20261019-01` 的环境/数据预检、90 次预定执行清单、编排脚本、平台差异诊断、成本与失败记录；[批次报告](../reports/p02-t002-20261019-01/report.md)为执行事实入口，[执行指导](../phases/P02/t002-execution.md)及[修复交接](../phases/P02/t002-repair-handoff.md)为恢复接口。没有正式 run，用户已要求暂停，无后台继续执行。

持久位置：`research/reports/p02-t002-20261019-01/`，含按字节复制的关键成本/失败证据及来源副本，复制身份见 `cost-evidence-manifest.json`；完整成本探针仍在忽略的 `scratch/graph-value-skeleton/p02-t002-20261019-01/cost-runs/`。独立运行环境在忽略的 `.venv-pinned/` 与 `.uv-python/`，不是需入库的科学结果。

保存状态：本机已写入；本批次产物尚未 commit/push，未封存，异地备份与远端恢复未核验。本次没有执行 Git 或备份写入。该状态描述交付产物，不单独追踪记录文件自身提交。

## P02-T002 修复验收与限时成本交付（2026-10-20）

产物为`repair-published-shuffle-budget`实现/独立验收交付，以及`p02-t002-20261020-01`真实r2短程成本诊断；[报告](../reports/p02-t002-20261020-01/report.md)为事实入口，[D027](../decisions.md#d027-发布图修复验收与限时成本门)记录研究侧软件接受与自动暂停决定。没有正式拟合完成，不构成图收益证据。

持久位置：实现规划、源码/证据指纹与独立报告保存在`openspec/changes/archive/2026-10-20-repair-published-shuffle-budget/`，主规格已同步；成本脚本、结构化决定与按字节复制的关键证据保存在`research/reports/p02-t002-20261020-01/`。复制清单为[cost-evidence-manifest.json](../reports/p02-t002-20261020-01/cost-evidence-manifest.json)，记录原位置、文件大小及SHA256；大型数组和完整原诊断仍在忽略的`scratch/graph-value-skeleton/p02-t002-20261020-01/`。图预生成与独立检查的原scratch路径及校验和由归档变更的就绪证据引用。

保存状态：用户随后授权记录预测并提交推送；本次修复差异、验收归档目录、新成本交付及预测汇总随本次提交入库，提交身份从Git历史追溯，推送目标为`origin/FJWP2T002`。执行源码身份仍按各报告记录的历史commit与实际字节定位。未封存，异地备份与远端恢复未独立核验；没有启动新的备份检查。此条描述交付产物，记录文件自身不另补提交回执。

## P02-T002 r2独立执行批次（2026-10-20）

产物为`p02-t002-r2-20261020-01`的独立执行副本及原拟合尝试；授权与范围见D028。2026-10-22 收尾核对：旧独立报告未随当前 Git 交付，原中断事实见后续 [r2 重启报告](../reports/p02-t002-r2-20261020-02/report.md)，旧路径不再作为恢复入口。执行根为`D:/research-runs/JODBSDFres/benchmark-r2-20261020-01`，原记录说明 C 仓库和 D 旧现场保留，本机未实机核验；这是经用户选择建立的运行副本，不是备份恢复核验。

保存状态（启动时）：新产物已在本机D盘写入，批次`research/reports/p02-t002-r2-20261020-01/`保存预检/清单/心跳/核验报告；完整正式数组在副本`research/runs/<run-id>/`，按既有政策留本地。C盘仅保存启动入口、控制器与研究记录。运行中尚未入库，成功分支才提交并push到`origin/FJWP2T002`；实际回执看D盘`publication.json`，没有回执不得称为已推送。不强推；未封存，异地备份及远端恢复未核验。

## my-change PR 合入（2026-10-11 接手记录）

用户告知此前已向 `my-change` 发起 PR。本轮只读本地 Git：合并提交 `7cbfe561285b1118c09e3e2510e1e2d711fe7432` 记录 PR #9（`Excavator-13/xzs`），提交时间为 2026-10-08，父提交为 `341e7f8` 与 `98e9fbe`。本地 `xzs`、`my-change` 和缓存的 `origin/my-change` 均指向该合并提交；缓存的 `origin/xzs` 为 `98e9fbe`。合并提交与 `98e9fbe` 的文件树差异为空，后者含此前维护、T010/T011 及保存状态记录。

这是本地合并历史及缓存引用的证据，未联网核验当前远端状态、PR 页面或产物恢复。既有封存包、运行源码身份与历史备份核验记录保持原样；没有新 run、封存、commit/push 或恢复检查。

## 远端核验记录

- 位置：`origin`，`git@github.com:Excavator-13/benchmark.git`，分支 `xzs`。
- 目标提交：`f66959b3dd868ba97a330cf46147212b83a4524b`，包含旧归档历史、原样诊断展开副本与当时两份记录文档。
- 首次 `git push -u origin xzs` 成功，建立上游；`git ls-remote --heads origin xzs` 独立读取远端引用与目标提交相等。
- 2026-10-06T18:13:45+08:00 核验：从 `https://raw.githubusercontent.com/Excavator-13/benchmark/f66959b3dd868ba97a330cf46147212b83a4524b/experiments_archive/phase1/phase1-20261006-v2-01.tar.gz` 取回 38,838 字节；SHA256 与本地一致，`cmp` 逐字节相等。不是全新 clone 或完整重训恢复测试。
- 组织入库提交：`b094cf13f47f2622f2771f0d766212b0b34fadba`。2026-10-06T18:18:00+08:00 独立读取 `origin/xzs` 指向该提交；从该提交取回 `RESEARCH.md`，与本地 918 字节逐字节一致。组织正文已核验可读。
- 后续收尾记录通过独立文档提交保存；自身最终 commit 从 Git 历史查证，不为记录自身的 push 反复改写索引。

## 新记录的保存与恢复

模型实验、改变条件的受控诊断和回测使用 `research/runs/<run-id>/`，按[协议 §6.1](../phases/P01/protocol.md#61-实验记录与产物保存)保留完整科学材料。检查使用关联报告，独立分析使用问题/过程/结果记录，维护使用文档与 Git 历史；临时开发产物在忽略的 `scratch/` 或系统临时目录。保存形式可为文件或必要的包，不默认要求封存。

已提交来源以固定 commit 与相对路径定位，相关未提交内容保留可恢复材料。需要封存时确认没有写入进程、拒绝覆盖并声明排除项；Git 内包以提交定位，Git 外包保留包外 SHA256。恢复遵循执行时内容，不用当前协议替代旧快照；追加分析放外部报告并链接旧实验，仅新实验创建新 run。大型产物另定持久位置，不擅自上传。

按已知事实更新本页的位置、身份与提交/备份状态；未核验写未核验，不自动成为检查待办。Git 与恢复核验遵循具体授权，本页不改封存摘要或独立报告，也不把存储动作作为科学验收条件。

目录历史和迁移验收见[迁移报告](migrations/20261006-standardize-research.md)。

## P02-T002 检查点验收及 r2 重启（2026-10-20）

产物：已独立PASS的检查点实现/测试、归档变更`2026-10-20-add-resumable-training-checkpoints`及r2新批次`p02-t002-r2-20261020-02`。[报告](../reports/p02-t002-r2-20261020-02/report.md)保留当时的执行入口；D029 接受软件就绪。最新保存事实见下方“T002 收尾交付与 PR 合入”条目。

启动时保存事实：实现/验收记录在 C 工作区并已同步 D，原20-01现场保留；正式数组及运行期 JSON 留 D。此为历史启动状态，后续入库已由下方收尾条目更新；不封存，异地备份和远端恢复未核验。

## P02-T002 r2交付与region/r0新执行（2026-10-22）

r2 交付入库身份与三组最新保存事实统一见下方收尾条目；启动过程及当时本地推送回执的观测保留在[组合执行报告](../reports/p02-t002-remaining-20261022-01/report.md)。当前 Git 内的 publication.json 是发布前快照，不能代替 Windows 最终本地回执。

region/r0 产物：[组合报告](../reports/p02-t002-remaining-20261022-01/report.md)、调度适配器、两组执行批次及可读 run；已入库，具体身份与限制见下方收尾条目，不再将本条启动时的“准备预检/启动”作为当前保存状态。

## P02-T002 收尾交付与 PR 合入（2026-10-22）

对象：三组正式开发对照执行交付及本轮研究侧验收报告。执行结果、条件可比性、清理选择和访问限制只在[收尾报告](../reports/p02-t002-closeout-20261022-01/report.md)叙述；研究接受决定见 D031，任务状态见 P02 计划。

已核对的本地 Git 入库事实：

- r2 可读 run、检查、控制器与检查点验收交付由 `815f1cc6a546ef81a4deb005dc12b5f70a8c5501` 保存。
- region/r0 可读 run、检查及组合调度交付由 `3060af19c7e6c27508edc24c35f1ef599ea533fa` 保存；两项交付均在当前分支祖先历史中。
- 当前 `xzs` 的接手提交 `4e5e04466a7ee88238374f52ca20c57a3d08fe33` 是 PR #13（`Excavator-13/FJWP2T002`）的合并提交；本轮核对父提交为 `02f7d19b0912decc964510ad8991c3364e7df957` 与上述 region/r0 交付提交，合并后的树与后者相同。用户已说明 PR 完成，本轮未联网核验 PR 页面或远端最新引用。

存储：Git 保存可读 run/原始检查和执行材料；完整数组、模型、训练历史、检查点及源码捕获按原执行报告仍留 Windows D 独立执行根，本机未实机核验。检查回执中的历史 SHA256 对应 Windows CRLF 字节，当前检出报告为 LF，转换关系在收尾报告明示，未改写原回执。未封存，异地备份及远端恢复未核验。

本轮验收、清理判断及用户随后要求的结果概览产物随本次授权的文档提交入库，提交身份从 Git 历史追溯；未 push、封存、备份或执行恢复操作。此状态描述交付产物，不另给索引/state 等记录文件维护提交回执，也不追加仅记录本提交自身哈希的提交。

## P02-T003 门槛判定与诊断（2026-10-22）

对象：T003 的 §6.2 门槛判定、失败诊断及可复核脚本/输出。判定与诊断内容、材料限制只在其[报告](../reports/p02-t003-20261022-01/report.md)叙述；研究接受见 [D032](../decisions.md#d032-p02-t003-门槛未通过与诊断验收)，任务状态见 [P02 计划](../phases/P02/plan.md)。

存储：报告、`gate.py`/`gate.json` 与 `diagnose.py`/`diagnose.json` 随 2026-10-22 文档提交入库，并于同日推送至 `origin/xzs`，提交身份从 Git 历史追溯；输入为已在 Git 中的 153 份 T002 checks 与 90 个 run summary。完整预测、模型权重与逐 epoch 训练历史仍按原执行报告留在 Windows D 根，本机未核验。未封存、未做异地备份或恢复核验；本页不记录该提交自身哈希，也不追加仅重述该提交的后续提交。

## P02-T003 上游论文数值核查（2026-10-22）

对象：缓存的 Job-SDF 论文表格解析与 GNN 附录表核查。内容、数字与边界只在[分析报告](../analyses/p02-t003-upstream-paper-tables-20261022-01/report.md)叙述；同目录含 [extract_tables.py](../analyses/p02-t003-upstream-paper-tables-20261022-01/extract_tables.py) 与 [tables.json](../analyses/p02-t003-upstream-paper-tables-20261022-01/tables.json)。

存储：论文 PDF 位于 `references/literature/Job-SDF-NeurIPS2024.pdf`，ignored、不随 Git 同步，本记录只以 PDF SHA256（`80db643…`，见 report 与 tables.json）定位。分析报告、脚本与解析结果随 2026-10-22 文档提交入库并推送至 `origin/xzs`，提交身份从 Git 历史追溯。未封存、未做备份或恢复核验。
