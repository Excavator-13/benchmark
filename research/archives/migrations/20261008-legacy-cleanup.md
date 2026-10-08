# 剩余历史与参考材料整理

日期：2026-10-08。所属任务：P01-T011；用户授权与范围见 [D012](../../decisions.md#d012-完成剩余历史与参考材料整理)。整理前 Git 基准为 `e36e374`，分支 `xzs`，工作区干净。

## 旧 / 新路径

| 旧路径 | 当前路径 |
| --- | --- |
| `not_in_origin/verification_20260921/` | `research/archives/legacy-development/verification_20260921/` |
| `not_in_origin/fix_verification_20260921/` | `research/archives/legacy-development/fix_verification_20260921/` |
| `not_in_origin/bug.md` | `research/archives/legacy-development/bug.md` |
| `guides/(2)GPU_SERVER_EVOLVEGCN_NEXT_STEPS_GUIDE.md` | `research/archives/legacy-development/GPU_SERVER_EVOLVEGCN_NEXT_STEPS_GUIDE.md` |
| `not_in_origin/四象限分析.md`、`多粒度共现图统计分析.md`、`figures/` | `research/archives/legacy-exploration/` 下同名文件/目录 |
| `benchmark/graph_method/cooccurrence_analysis.py`、`quadrant_analysis.py` | `research/archives/legacy-exploration/scripts/` 下同名文件 |
| `evolvegcn_in_torch-geometric-temporal/` | `references/upstream/evolvegcn/` |
| `metrics/multi_result.ipynb` | `references/upstream/metrics/multi_result.ipynb` |
| `not_in_origin/NeurIPS-2024-job-sdf-a-multi-granularity-dataset-for-job-skill-demand-forecasting-and-benchmarking-Paper-Datasets_and_Benchmarks_Track.pdf` | `references/literature/Job-SDF-NeurIPS2024.pdf`（本地 ignored） |

删除 `not_in_origin/test_r0.py`、`preview_dataset.py`、`dataset_preview.txt`：失效个人绝对路径的探针/生成预览，无当前调用；已有 Git 历史可追溯，不另建包。

## 内容与入口

按 Git 跟踪文件逐项搬移，保留核验目录的内部结构、报告/图关系及所有历史内容。当前 roadmap、archive index 与 GPU 指导更新为新入口；已归档 OpenSpec、run 快照与历史报告中的旧路径不改写，由本映射解释。

历史核验脚本仍有旧根目录推导、Windows 绝对路径与写回报告目录的行为；探索脚本保留原 dataset/figures 路径假设；上游 notebook 保留旧绝对路径和指标。各入口 README 已注明仅作历史/参考，不将它们误认作当前正式工具。旧 GPU 前篇指南原本缺失，仅保留已知条件，不补造环境。

`verify_20261006.py` 是首次标准化迁移的历史检查，含旧完整工作树不变断言；后续软件实施与本次组织迁移均超出其基准，不能在当前 HEAD 作为全仓库检查使用。第一次迁移的原记录与结果保留，不重跑或改造这个历史脚本。

本地 PDF 仅改位置/名称，继续忽略；`.vscode/`、缓存及其他 ignored 内容不删除。原目录若还有本机 ignored 内容可以继续存在，不做递归清空。dataset、当前运行实现、其他模型、README 原论文图、skills、封存包、run 与归档 OpenSpec 不变。

## 核对与保存

已核对：195 个迁移的 tracked 文件与整理前 Git 对应内容逐字节相同，删除范围仅上述三项；活跃链接/锚点和指导示例语法检查通过，PDF 新位置为 ignored，`git diff --check` 通过。ignored 文件没有删除，仅清除搬空的目录。不运行实验、完整测试或恢复演练，不生成 run、新包或哈希清单。提交/push 事实记录于[归档索引](../index.md#t011-历史整理2026-10-08)。
