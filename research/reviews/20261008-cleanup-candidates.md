# 仓库清理候选清单

日期：2026-10-08。状态：**部分首批整理已执行，其余仍为候选**。
与[协议减负方案](20261008-maintenance-and-protocol.md)配套。本清单主要回答与本次证据膨胀无关、仍可整理的东西；baseline 冗余展开副本在主报告另述。

后续执行：已清理下列 16 个 `.DS_Store` 与两个 baseline 缓存目录（22 文件）；根目录历史 skill 建议已迁至 [reviews](20261008-research-maintainer-redesign.md)。下表是原候选盘点，不代表这些路径仍存在。用途未确认的预览/探针、notebook、个人配置与文献保留；第二轮迁移未启动。精确事实见[整理记录](../archives/migrations/20261008-evidence-maintenance.md)。新版政策仅取消 T004 的 24 个包外 sidecar 和全成员哈希清单，其他历史封存包/校验仍保留。

大小为本机 `du` 近似占用，非精确内容字节数。“未发现引用”限于本轮仓库文本搜索，不保证外部机器/人工操作没有依赖。Git 跟踪情况是当前事实，不代表历史上是否曾存在。

## 1. 可以直接作为删除候选

| 文件/文件夹 | 当前 Git 状态 / 大小 | 理由与处理条件 |
| --- | --- | --- |
| 下文列出的 16 个 `.DS_Store` | ignored / 小文件 | Finder 元数据，不承载科研或代码内容；只清展开目录，封存包不改 |
| `benchmark/nograph_baseline/__pycache__/` | ignored / 300 KiB | Python 字节码缓存，可再生成 |
| `benchmark/nograph_baseline/tests/__pycache__/` | ignored / 244 KiB | 测试字节码缓存，可再生成 |
| `not_in_origin/test_r0.py` | tracked / 4 KiB 量级 | 一次性打印图表字段/ID 的探针，硬编码旧 `/Users/watuji/大创/代码仓库/...`。当前记录/代码中未发现调用；现有规范数据审计已覆盖其主要用途。若无个人用途，可从当前树移除 |
| `not_in_origin/preview_dataset.py` | tracked / 4 KiB 量级 | 通用前五行预览，硬编码 `/Users/watuji/MyGitDev/benchmark/`。无当前流程引用；不必为了留一个失效脚本再维护工具。若仍常用，改相对路径后迁到工具目录 |
| `not_in_origin/dataset_preview.txt` | tracked / 28 KiB | 旧数据前几行的生成预览，可重生成；搜索到的脚本是生成者，没有发现当前科研记录依赖此预览。若不承担独有观察依据，可从当前树移除 |

tracked 候选删除属于普通当前树修改，内容仍可从既有 Git 历史追溯；不需要为这些临时工具另外封存实验包。

16 个现存 `.DS_Store` 的精确路径：

```text
.DS_Store
benchmark/.DS_Store
benchmark/graph_method/.DS_Store
benchmark/multivariate_time_series/.DS_Store
benchmark/predygae/.DS_Store
benchmark/predygae/code/.DS_Store
dataset/.DS_Store
not_in_origin/.DS_Store
openspec/.DS_Store
openspec/changes/.DS_Store
experiments_archive/1st_try_in_phase_fix_origin/benchmark/.DS_Store
experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/.DS_Store
experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/results/.DS_Store
experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/results/count/.DS_Store
experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/results/count/region/.DS_Store
experiments_archive/1st_try_in_phase_fix_origin/benchmark/graph_method/results/count/region/EvolveGCNH/.DS_Store
```

## 2. 可以退出当前工作区，需先明确用途

| 文件/文件夹 | 当前状态 / 大小 | 发现与建议 |
| --- | --- | --- |
| `metrics/multi_result.ipynb` | tracked / 12 KiB | 已读取 JSON 中四个代码 cell，未执行。它是上游批量结果汇总器，无输出，硬编码 `/data/chenxi/research/conference/NeurIPS24/...`；旧 SMAPE/RRMSE 等口径不能直接充当当前协议的评价。未发现当前调用。若未来不复查上游表，移除当前树；若要复查，迁到 `references/upstream/metrics/` 并标注旧口径 |
| `evolvegcn_in_torch-geometric-temporal/` | tracked / 12 KiB，两个 Python 文件 | 当前模型从安装的 `torch_geometric_temporal` 导入相应模块，未发现运行路径导入这份根目录副本；但[归档修复设计](../../openspec/changes/archive/2026-09-16-repair-graph-forecasting-pipeline/design.md)明确引用它。推荐迁到 `references/upstream/evolvegcn/`，留下旧路径映射；不能称为无引用垃圾。若彻底放弃源码对照，才考虑只在 Git 历史保留 |
| `guides/(2)GPU_SERVER_EVOLVEGCN_NEXT_STEPS_GUIDE.md` | tracked / 16 KiB | 仍被[当前执行指导 §8](../phases/P01/execution-guide.md#8-什么时候恢复-gpu-实验)引用；其第 3 行链接的 `GPU_SERVER_EVOLVEGCN_GUIDE.md` 在仓库中不存在。可将仍有用的 GPU 环境/复跑指引并入当前指导，原文件归入历史或退出当前树；先修活跃引用，不能直接删整个 guides |
| `research-maintainer-redesign.md` | untracked / 12 KiB | 此前讨论的建议，有用但部分已被 skill 更新与本次审查覆盖。可移到 `research/reviews/` 与本报告并列并标明历史提案；不覆盖、不作为已接受政策 |
| `not_in_origin/NeurIPS-2024-job-sdf-a-multi-granularity-dataset-for-job-skill-demand-forecasting-and-benchmarking-Paper-Datasets_and_Benchmarks_Track.pdf` | ignored / 428 KiB 量级 | 正在研究的数据集论文，属于文献资料。可移入文献管理器或固定 literature 位置；不当作无用文件删除，当前路线图涉及该本地 PDF 的观察 |
| `.vscode/settings.json` | ignored / 4 KiB 量级 | 仅本机 conda/editor 设置。可保留个人工作配置；只在本人不再使用时删除，不属于科研垃圾 |

以上路径是整理建议，不要求这次都新增目录。只删除确认无用的几项也能收拢根目录；保留参考资料时再创建对应目录。

## 3. 适合归类，不能整批删除

| 现有材料 | 近似占用 | 整理方向 / 保留依据 |
| --- | --- | --- |
| `not_in_origin/verification_20260921/` | 1.6 MiB | 早期软件缺陷复现与核验，包含小规模真实运行；可归到 `research/archives/legacy-development/`。已被 archive index 引用，报告、脚本和关键输出共同构成修复历史，不能整批删掉 |
| `not_in_origin/fix_verification_20260921/` | 2.2 MiB | 修复后核验，报告区分 final 运行与此前探针；同样可归到开发历史。现在保留 legacy 内容。未来要去除其中重复探针，先按报告依赖筛选，不把所有 `.pt` 视为缓存 |
| `not_in_origin/bug.md` | 小型文档 | 原始 17 项缺陷记录，被 roadmap 引用；可随修复历史归类，不应清掉研究起点 |
| `not_in_origin/四象限分析.md`、`not_in_origin/多粒度共现图统计分析.md`、`not_in_origin/figures/` 六张图 | 图共 844 KiB | 两份报告是已有探索，当前 roadmap 已解释其局限；图被报告引用。建议归到 `research/archives/legacy-exploration/`，保持报告/图相对关系，明确不作为当前机制验证 |
| `benchmark/graph_method/cooccurrence_analysis.py`、`quadrant_analysis.py` | 小型脚本 | 上述历史探索来源，有上下文合并/全月份分组等口径问题。可与历史报告收拢，避免误当当前正式分析入口；`cooccurrence_analysis.py` 被 roadmap 点名。迁移需修活跃引用和相对数据路径，或明确仅保存历史来源 |

迁移时修复当前入口、roadmap、archive index 与指南的链接；已封存包与已归档 OpenSpec 工件保持原文字，通过一份简短旧/新路径映射解释。纯文件整理不需要生成科研 run。

## 4. 不列为本轮清理对象

`dataset/`、其他 baseline 框架、`figs/` 中 README 使用的原论文图、`experiments_archive/` 中真实 500-epoch seed 0/1 结果及旧诊断包、已归档 OpenSpec 变更、现有封存包/校验、`.agents/skills/`、`.git/` 均不能因为当前阶段暂时没用就整批删除。

`.pip-cache/`、`.pytest_cache/`、`.uv-*`、`.venv-*` 虽出现在忽略规则中，本轮未发现仓库内现存目录，不能把不存在的缓存当成待清理项。

## 5. 最实用的一次整理范围

首批可选择：清理 16 个 `.DS_Store` 与两个缓存目录；从当前树去掉确认不再使用的三个旧预览/探针文件；处理旧 notebook；把根目录的历史 skill 建议放回 reviews。需要保留的文献、参考源码、GPU 指南和科学历史可以随后归类，不阻塞首批整理。

这些改动主要减少目录噪声，不会显著节省存储。最大本地空间收益来自 baseline 已封存产物的冗余展开副本，处理办法见主报告；最大秩序收益来自今后只给实际实验建立完整记录。
