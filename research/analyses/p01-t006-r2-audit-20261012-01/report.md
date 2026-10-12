# T006 r2/count 数据与图审计、baseline 与成本

- 分析 ID：`p01-t006-r2-audit-20261012-01`
- 所属任务：P01-T006；协议 `P1-count-L6-H3-v3`，记录政策 `P01-records-v2`
- 输入身份：`dataset/demand/r2.parquet` = `4ada154773b8678ae7d25b42e36a8309a51490bbe9fe059f015bb61724ed4c3c`、`dataset/graph/r2.parquet` = `4cc1f399dd9061920179ade34d018fcbd58c3e00bb40f303b91e9aba99f9e12c`（见 [source-sha256.txt](source-sha256.txt)）
- 执行代码：仓库 `1f3e5b1`（[git-commit.txt](git-commit.txt)）
- 脚本与结果：[r2_structure_audit.py](r2_structure_audit.py)、[r2-structure.json](r2-structure.json)、[r2-structure.log](r2-structure.log)
- 环境：Python 3.11.17、NumPy 1.26.4、pandas 2.2.3、PyArrow 17.0.0，本机 macOS arm64 CPU（`job-sdf-baseline`）

## 身份与活跃度（r2）

| 指标 | 值 |
| --- | ---: |
| 任务节点数 | 121,420 |
| 技能数 | 2,335 |
| 上下文数（`r2_id`） | 52 |
| 上下文×技能网格 | 完整（52×2,335 = 121,420） |
| 训练 27 月全零节点 | 54,207（44.64%） |
| 完整 36 月全零（仅描述） | 41.84% |
| 训练常数节点 | 54,207 |
| 活跃度分组 inactive / low / medium / high | 54,207 / 31,364 / 10,557 / 25,292 |
| 值域 | 0 – 见 JSON（非负、有限） |

与已完成的正式 run 的 `audit.json` 一致（节点、技能、网格完整性三项比对通过）。

## 图结构（r2，上下文限定）

| 指标 | 值 |
| --- | ---: |
| 有向行数 / 去重后有向边 | 321,374 / 321,374 |
| 精确重复行 | 0 |
| 自环 | 0 |
| 非自环有向边 | 321,374 |
| 无向边 | 160,687 |
| **反向边比例** | **1.0**（完全对称，方向不携带信息） |
| 有邻居节点 | 10,193 |
| 孤立节点 | 111,227 |
| 邻居覆盖率 | **8.3948%** |
| 覆盖节点无向度：min / p25 / p50 / p75 / max | 1 / 4 / 14 / 44 / 270 |

与正式 run 的 `coverage.json` 一致（覆盖节点数、节点数与图源 SHA256 三项比对通过）。与 `r0`（314/2,335，覆盖 13.45%，覆盖度最低 18）、`region`（2,185/16,345，13.37%）相比，r2 覆盖更低，且覆盖节点里有大量低度节点（859 个度=1、1,357 个度=2–3）。

跨上下文技能投影（**仅用于解释历史预分析，不是预测图**）：314 个技能、30,402 个技能对，每对有向行数均值 10.57、中位数 8、最大 90，全部为偶数，计数=2 占比 21.88% —— 与历史[多粒度共现图统计分析](../../archives/legacy-exploration/多粒度共现图统计分析.md)的 r2 行逐项吻合，再次说明其"权重"是跨场景对称重复计数，不是共现频率。

## baseline 与同 seed 重复

正式 run（`--purpose formal`，seed 0）：

| Run | 状态 | Lambda | Val MSE (LastValue) | Test MAE / RMSE (LastValue) | Test MAE / RMSE (SharedRidge) |
| --- | --- | --- | ---: | ---: | ---: |
| `p01-r2-sharedridge-001` | success | 1e-4 | 2323.30 | 6.140083 / 85.597475 | 8.669351 / 167.690727 |
| `p01-r2-sharedridge-repeat-001` | success | 1e-4 | 2323.30 | 6.140083 / 85.597475 | 8.669351 / 167.690727 |

- `NaiveRef = NaiveRef6 = LastValue`（验证 MSE 选定，测试前冻结）。`WindowMean6` 的测试 MAE 6.135036 略低，但协议禁止按测试排名更换参照。
- `SharedRidge` 总体测试 MAE/RMSE 均差于 `LastValue`，与 r0/region 结论方向一致；不宣称改善。负预测比例 1.15%（r0/region 为 0）。
- 分组（LastValue，测试）：high 组 25,292 节点 MAE 27.672、占 99.83% 平方误差；inactive 组 MAE 0.0436；有邻居 10,193 节点 MAE 5.348，孤立 111,227 节点 MAE 6.213。

## 检查证据

| 检查 | 报告 | 结果 |
| --- | --- | --- |
| primary 重算 | [p01-r2-recompute-primary-001.json](../../reports/nograph-baseline/p01-r2-recompute-primary-001.json) | ok；`source_data_read=false`、`model_refit=false`；test 4,572 / validation 4,320 字段，最大归一化差 3.73e-16；node-errors 最大 8.80e-16 |
| repeat 重算 | [p01-r2-recompute-repeat-001.json](../../reports/nograph-baseline/p01-r2-recompute-repeat-001.json) | ok |
| 同 seed 比较 | [p01-r2-repeat-check-001.json](../../reports/nograph-baseline/p01-r2-repeat-check-001.json) | ok；全部预测最大绝对差 0.0、MAE 相对差 0.0、7,890 指标字段最大归一化差 0.0（容差 1e-6）；身份检查全通过 |

## 实测成本（本机 CPU，仅代表记录的本地条件）

| Run | demand 读 | coverage 读 | 预处理 | Ridge 拟合 | 选模+推理 | 指标写出 | 总计 | 峰值 RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `-001` | 0.246 s | 0.231 s | 0.091 s | 0.462 s | 0.019 s | 0.914 s | **2.950 s** | 1,293,303,808 bytes |
| repeat | — | — | — | — | — | — | **2.217 s** | 1,299,087,360 bytes |

线程环境为 `OMP/MKL/OPENBLAS/NUMEXPR/VECLIB_MAXIMUM_THREADS=1`，设备 CPU，未用 GPU。

## 限制

- 未运行 `align-v2`：该检查要求参考含被检查数据的记录；历史封存 v2 诊断日志只有 r0/region，r2 没有可对齐的参考，伪造一个属于新范围。协议不把对齐列为图收益或本任务验收条件。
- 测试窗口已被查看过，分组指标是描述性诊断；`SharedRidge` 劣于 `LastValue` 的结论不构成图收益证据，图收益仍按 P02 的公平对照判断。
- 图构建时间来源仍未决（T002/D015），上述固定评测期结果不能升级为严格历史/跨时间主张。
- `WindowMean6` 在测试 MAE 上略优于选定参照，仅作事实记录，不改变参照选择。
