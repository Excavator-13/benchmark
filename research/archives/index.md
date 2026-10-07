# 实验与归档索引

更新日期：2026-10-07。研究交接见[当前状态](../state.md)，任务验收见[阶段计划](../phases/P01/plan.md)。运行成功、已封存、已入库和已备份分别记录。

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
- 历史说明前半是指南，末尾才是实际执行；旧源码修复报告见[首次核验](../../not_in_origin/verification_20260921/REPORT.md)和[修复后核验](../../not_in_origin/fix_verification_20260921/REPORT.md)。它们不替代当前版本核验。

### 第一阶段诊断的范围

执行于 2026-10-06，运行源码基准 `341e7f8362904bc3a504736335ee6407c112843c`，协议 v2。两个数据集验证选定 LastValue；图无频率列且邻居覆盖约 13.4%；旧 gold 与当前标签逐元素一致，指标可复算。

这是诊断产物，没有共享 Ridge 或正式实验完整预测/参数。13 个文件保持与旧包内容一致；没有追溯添加 provenance.json 或命令日志。未来新运行使用 skill 模板。

包 SHA256：`4c9a08f3e65139afb7353bbcb47de70c7afef9dcf98f81f50e7d42b79cb58dad`。

在仓库根目录核验：

```bash
shasum -a 256 -c experiments_archive/phase1/phase1-20261006-v2-01.tar.gz.sha256
python3 research/archives/migrations/verify_20261006.py
```

旧摘要中的“未推送”描述封存时状态，保持不变。旧 `planning-sha256.txt` 使用原目录路径；迁移后的内容核验由上述脚本按映射完成，不改写封存清单。

## T004 baseline 运行（2026-10-07）

所属任务：P01-T004；协议 `P1-count-L6-H3-v3`。研究验收见 [D008](../decisions.md#d008-t004-baseline-研究侧验收)，独立实现核验见 [PASS 报告](../../openspec/changes/archive/2026-10-07-add-nograph-baseline-ridge/verification.md)。以 `-002` 的四个模型 run 和八个检查为本次验收依据；`-001` 保留为历史版本。

以下 24 个 run 的共同保存状态：**sealed，已提交并 push 至 origin/xzs**。实现提交 `8273c07a84c879a8f7bdbb61f987f3c94e863e59`，证据与科研记录提交 `b72770873f11a66478c3556973393882be501bd8`；push 成功，并独立读取远端引用确认为证据提交。远端恢复未核验，用户明确取消后续恢复检查，不作为今天收尾的前置条件。每个包位于 `research/archives/<run-id>.tar.gz`，配套 `.tar.gz.sha256`；实际路径、包 SHA256、字节数和完整成员哈希见 [封存清单](p01-baseline-20261007-manifest.json)。本地展开产物保留；Git 收纳封存包及 summary/provenance/command/report 可读记录，其余展开文件由精确忽略规则排除。

### 模型运行

每个模型 run 含五项朴素基线及共享 Ridge，74 个文件，其中 72 个为清单成员。primary/repeat 均为 seed 0；它们是同条件重复，不是不同初始化样本。

| 数据 / 版本 | Primary 摘要与 Run ID | Repeat 摘要与 Run ID | 执行结果（2026-10-07） | 证据角色 |
| --- | --- | --- | --- | --- |
| r0 / 001 | [p01-r0-sharedridge-001](../runs/p01-r0-sharedridge-001/summary.md) | [p01-r0-sharedridge-repeat-001](../runs/p01-r0-sharedridge-repeat-001/summary.md) | 两运行 success/complete | 修复前历史，保留原样 |
| region / 001 | [p01-region-sharedridge-001](../runs/p01-region-sharedridge-001/summary.md) | [p01-region-sharedridge-repeat-001](../runs/p01-region-sharedridge-repeat-001/summary.md) | 两运行 success/complete | 修复前历史，保留原样 |
| r0 / 002 | [p01-r0-sharedridge-002](../runs/p01-r0-sharedridge-002/summary.md) | [p01-r0-sharedridge-repeat-002](../runs/p01-r0-sharedridge-repeat-002/summary.md) | 两运行 success/complete，同条件预测最大绝对差 0 | 本次研究验收依据 |
| region / 002 | [p01-region-sharedridge-002](../runs/p01-region-sharedridge-002/summary.md) | [p01-region-sharedridge-repeat-002](../runs/p01-region-sharedridge-repeat-002/summary.md) | 两运行 success/complete，同条件预测最大绝对差 0 | 本次研究验收依据 |

### 关联分析检查

每行列出两个不同 run；链接是各自不可改写的输出报告。16 个状态文件均为 success/complete；`-002` 的四个重算、两个重复性检查及两个 v2 对齐均为 ok。原始输入 run 与精确命令见各检查目录的 `provenance.json`/`command.json`。

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
- 算法：报告的排序相对路径清单与 `path + NUL + file_SHA256 + newline` 聚合规则；是目录内容身份。各 tar 包另有包外 SHA256，见封存清单。
- 运行代码基准：`a0fdab4268e5e17b0c96453efd53f01a245f01cc` 加执行时保存的 diff、未跟踪源码快照及来源清单。两版身份分别以各自 run 为准；后续修复的 checker 与运行时快照有差异，已由独立报告说明，不回写旧 run。
- 环境：本地 macOS arm64 CPU，Python 3.11.17、NumPy 1.26.4、pandas 2.2.3、PyArrow 17.0.0；线程设置与完整环境在各模型目录。sklearn 未安装，实际可选后端未验证。
- 产物定位：模型目录包含 `predictions/`、`gold/`、`models/`、`candidates/`、节点/窗口身份、分组掩码、配置/协议/来源/命令、`metrics.json`、`node-errors.parquet` 与 `measurements.json`。单个目录成员核验依据为其 `artifacts-sha256.json`。
- 封存核验：24 个包合计 41,446,332 bytes；排除缓存和系统元数据，所有成员为各 run 下的普通文件，拒绝绝对路径、父目录跳转、链接与重复成员。在新的临时目录解包后核对全部 780 文件 SHA256，并与核验报告的全集内容指纹一致；封存前后原目录身份一致。
- 保存收尾按协议第 6.1 节与 [D009 当前产物保存决定](../decisions.md#d009-约束证据数量与-git-保存边界)执行。源码去重与 skill 长期改进仍待讨论；没有删改原始 run。

恢复完整证据时，在仓库根目录先校验包外 SHA256，再在空的临时目录解包核验。以下命令自动核验全部包并在新临时目录恢复 780 文件，不覆盖现有 run：

```bash
python3 research/archives/seal_20261007_baseline.py verify
```

新 clone 的展开目录仅含可读记录。需要持久展开模型产物时，先用上述命令核验，在新建空目录执行 `tar -xzf /absolute/path/to/research/archives/<run-id>.tar.gz -C /new/empty/directory`；输出为 `<run-id>/`。按运行内配置/协议与来源身份重算，不直接覆盖仓库中已有 run。`command.json` 记录原机器的绝对路径，恢复后须映射到实际位置；这不是全新环境重训验证。

## 远端核验记录

- 位置：`origin`，`git@github.com:Excavator-13/benchmark.git`，分支 `xzs`。
- 目标提交：`f66959b3dd868ba97a330cf46147212b83a4524b`，包含旧归档历史、原样诊断展开副本与当时两份记录文档。
- 首次 `git push -u origin xzs` 成功，建立上游；`git ls-remote --heads origin xzs` 独立读取远端引用与目标提交相等。
- 2026-10-06T18:13:45+08:00 核验：从 `https://raw.githubusercontent.com/Excavator-13/benchmark/f66959b3dd868ba97a330cf46147212b83a4524b/experiments_archive/phase1/phase1-20261006-v2-01.tar.gz` 取回 38,838 字节；SHA256 与本地一致，`cmp` 逐字节相等。不是全新 clone 或完整重训恢复测试。
- 组织入库提交：`b094cf13f47f2622f2771f0d766212b0b34fadba`。2026-10-06T18:18:00+08:00 独立读取 `origin/xzs` 指向该提交；从该提交取回 `RESEARCH.md`，与本地 918 字节逐字节一致。组织正文已核验可读。
- 后续收尾记录通过独立文档提交保存；自身最终 commit 从 Git 历史查证，不为记录自身的 push 反复改写索引。

## 新记录的保存与恢复

新 run 位于 `research/runs/<run-id>/`，新包及包外校验位于 `research/archives/`。按[协议第 6.1 节](../phases/P01/protocol.md#61-保存与归档)和 skill 保存来源、协议、配置、命令/脚本、输入/输出、摘要及必要参数。目录存在或未被忽略不等于入库。

结束并确认没有写入进程后再封存；失败/中断也保留。解包核验用新的临时目录，恢复遵循运行内快照，避免拿当前协议替代旧快照。后来分析使用新 run 并关联旧记录。大型产物另行确定持久存储，不擅自删预测或上传。

完成入库/备份后更新本页的真实位置、身份、核验时间和方法；未核验写明未核验。本页提供外部状态，不修改封存摘要。

目录历史和迁移验收见[迁移报告](migrations/20261006-standardize-research.md)。
