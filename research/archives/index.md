# 实验与归档索引

更新日期：2026-10-08。研究交接见[当前状态](../state.md)，任务验收见[阶段计划](../phases/P01/plan.md)。运行成功、已封存、已入库和已备份分别记录。

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
