# 实验与归档索引

更新日期：2026-10-06。研究交接见[当前状态](../state.md)，任务验收见[阶段计划](../phases/P01/plan.md)。运行成功、已封存、已入库和已备份分别记录。

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

## 远端核验记录

- 位置：`origin`，`git@github.com:Excavator-13/benchmark.git`，分支 `xzs`。
- 目标提交：`f66959b3dd868ba97a330cf46147212b83a4524b`，包含旧归档历史、原样诊断展开副本与当时两份记录文档。
- 首次 `git push -u origin xzs` 成功，建立上游；`git ls-remote --heads origin xzs` 独立读取远端引用与目标提交相等。
- 2026-10-06T18:13:45+08:00 核验：从 `https://raw.githubusercontent.com/Excavator-13/benchmark/f66959b3dd868ba97a330cf46147212b83a4524b/experiments_archive/phase1/phase1-20261006-v2-01.tar.gz` 取回 38,838 字节；SHA256 与本地一致，`cmp` 逐字节相等。不是全新 clone 或完整重训恢复测试。
- 组织迁移尚未提交；此处不预先填写未来 commit。后续入库身份由 Git 历史及迁移记录追溯，无需记录索引自身的提交号。

## 新记录的保存与恢复

新 run 位于 `research/runs/<run-id>/`，新包及包外校验位于 `research/archives/`。按[协议第 6.1 节](../phases/P01/protocol.md#61-保存与归档)和 skill 保存来源、协议、配置、命令/脚本、输入/输出、摘要及必要参数。目录存在或未被忽略不等于入库。

结束并确认没有写入进程后再封存；失败/中断也保留。解包核验用新的临时目录，恢复遵循运行内快照，避免拿当前协议替代旧快照。后来分析使用新 run 并关联旧记录。大型产物另行确定持久存储，不擅自删预测或上传。

完成入库/备份后更新本页的真实位置、身份、核验时间和方法；未核验写明未核验。本页提供外部状态，不修改封存摘要。

目录历史和迁移验收见[迁移报告](migrations/20261006-standardize-research.md)。
