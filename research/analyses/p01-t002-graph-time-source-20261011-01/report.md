# T002 图构建时间来源：可证明来源与未决限制

- 分析 ID：`p01-t002-graph-time-source-20261011-01`
- 所属任务：P01-T002（D013 第 4 条）
- 问题：发布图 `dataset/graph/*.parquet` 的时间来源能否确定？能否证明它在某个预测起点之前可获得？
- 输入身份：见 [source-sha256.txt](source-sha256.txt)（含全部 7 个粒度图文件）。执行记录为仓库 `7cbfe561285b1118c09e3e2510e1e2d711fe7432`（[git-commit.txt](git-commit.txt)）。
- 结论：**图构建/广告收集的截止时间在本仓库中无法确定**；发布文件本身不携带任何时间元数据，仓库也没有图构建代码。因此固定发布图不能被当作严格的时间点先验，详见下方限制。

## 已核对的材料与结果

| 材料 | 结论 |
| --- | --- |
| `dataset/graph/*.parquet`（7 个文件） | 列只有上下文 ID + `row_id` + `col_id`（加索引列），**没有时间列、没有 weight/frequency 列**；Parquet 键值元数据只有 `ARROW:schema` 与 `pandas`，无构建日期。 |
| `benchmark/graph_method/prepare_graph_data.py` | 只把已发布的图 Parquet 转成 JSON（`row_id`/`col_id`/上下文），不生成边、不读广告文本，仓库内没有"从广告构建图"的代码。 |
| `benchmark/graph_method/data_process.ipynb` | 只是 `prepare_graph_data.py` 的薄调用。 |
| `README.md` §3 | 只说明各目录含义和图列定义；未给广告收集期、图构建时间或阈值。 |
| Git 历史 | `dataset/graph/*` 只在仓库导入提交 `00583fc`（2026-05-15）出现一次，此后未改。这是**入库时间**，不是数据或图的构建时间。 |
| 本地论文 PDF（ignored，不在 Git） | 见下方引用；描述与发布文件不一致，且未给出截止月份。 |

## 论文中的说明（外部参考，本机副本）

以下引文取自本机 `references/literature/Job-SDF-NeurIPS2024.pdf`（NeurIPS 2024 版本，本地 ignored 文件，**不随 Git 同步**，其他机器可能没有该 PDF；引文由脚本解压 PDF 文本流得到，仅供记录，不能由仓库独立复核）。

- 正文（第 3–4 节之间）："Instead, we constructed a skill graph based on the co-occurrence of skills in job advertisements from the training data. This graph is included in our dataset. For detailed construction methods, please refer to the Appendix F."
- 附录 E（Skill Co-occurrence Graph…）："we construct a prior graph with co-occurrence frequency from the training data to include as a dataset component … The edge weight `e_{v,v'}` … is determined by the co-occurrence frequency of the node pair `(v, v')` in the job advertisement data for training `P_train`."
- 附录 E 续："… a set of triples `(skillID_1, skillID_2, frequency of co-occurrence)` … Each triple indicates how frequently two skills are mentioned or required together within the job advertisements in the training data."
- 第 3.2 节：训练/验证/测试按时间顺序以 `9:1:2` 划分（与本项目协议固定的 `19/1/4` 窗口划分不同，本项目划分已在其协议中单独说明）。

由此只能得到两个弱结论：论文**声称**图由训练期广告的技能共现构成；论文**没有**给出广告收集区间或图构建截止月份。

## 与发布数据的不一致

论文把图描述为带"共现频率"的三元组，但发布文件里没有频率/权重列，且 T002 图结构审计发现：`r0`、`region` 的精确重复行数为 0、反向边比例恰好为 1.0，即每条有向边只出现一次且必然伴随反向边。也就是说，发布组件只提供**无权的对称技能对**，论文所称的频率信息在发布版本中不可获得、也无法从该文件验证其构建规则。

## 限制（按协议 §4.2、§8 记录）

1. **图构建时间来源未决。** 无法确定图所用的广告截止月份，也无法证明它在任一给定预测起点之前可获得。不能写成"图严格不含未来信息"，也不能把论文"来自训练数据"的说法直接升级为对本仓库发布文件的验收。
2. **不能用于严格的历史回测解释。** 开发回测 A（拟合观察期截止 2022-06）和 B（截止 2022-09）若使用固定发布图，无法排除图包含这些起点之后的广告信息；跨时间稳健性主张因此先限制为固定评测期证据（协议 §6.2、§8）。
3. **不阻止无图工作。** 该缺失不要求自动重建图，也不阻止无图 baseline 与内部回测；它只限制图模型的"时间泛化"表述。
4. **本机论文副本不在 Git。** 上述引文来自 ignored 的本地 PDF；若后续要用它作为外部依据，应另行记录可独立获取的出处，而不是把它当作仓库内可复核证据。

## 对 T002 的覆盖

本项完成 D013 第 4 条：记录了可证明的仓库来源（无时间列、无构建代码、入库提交 2026-05-15）与未知的图构建截止时间，并给出协议要求的固定图历史回测限制。未重建图、未修改数据或协议；重建时间相符的图属于需要另行决定和授权的新实现。
