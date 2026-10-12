## 1. 入口与身份映射

- [x] 1.1 在 `protocol.py` 注册 `"r2": ("r2_id",)` 并更新 CLI 描述，保持 choices 派生；更新 `test_protocol.py`，验证三种数据可解析、r2 默认 demand/graph 路径和节点键正确，未知数据/rate/协议外切分仍拒绝，科学与记录版本不变。
- [x] 1.2 为 `tests/nb_fixtures.py` 增加可指定上下文数/技能数的 r2 键和 build_fixture 分支，复用 write_demand/write_graph 的协议列；通过 fixture 测试证明生成 r2_id、跨上下文同 skill_id 不合并，原 r0/region fixture 语义不变。

## 2. r2 审计、数值边界与完整产物

- [x] 2.1 在 `test_data.py` 增加 r2 乱序/多上下文/完整及缺项网格、全零/常数/活跃度边界用例；验证规范排序、节点/技能/上下文计数、月非零率、训练27月与全36月审计、每上下文结果，缺项仅报告不补行；负例验证缺 r2_id、重复/非整数/非有限键、月份缺失/额外和负/非有限 count 在拟合前失败。
- [x] 2.2 在 `test_coverage.py` 增加 r2 raw graph 和 provenance-bearing mask 用例；验证上下文内非自环双端覆盖、自环不供邻居、共用掩码，以及未知上下文/端点、缺 r2_id、mask 数据名/键/语义/来源错误的拒绝；输入均为临时合成数据，不依赖仓库图文件。
- [x] 2.3 在 `test_runner_cli.py` 通过真实公共 CLI 运行两个独立小 r2 development fixture；验证五基线与 SharedRidge、19/1/4窗口、27月 ddof=0 标准化、M=19*N、全部五 lambda 验证分数及仅按验证MSE选模/平局规则、固定分组与完整 gold/predictions/nodes/windows/masks/models/selection/metrics/audit/node-errors/measurements/provenance/status，数组用 allow_pickle=False 加载，输出 schema 与 r0/region 一致且不在 research/runs。
- [x] 2.4 增加 r2 信息边界和图注释不变性测试：训练期后值改变不影响训练统计/活动掩码/候选参数，仅测试标签改变不影响 lambda 与 NaiveRef/NaiveRef6，有效覆盖改变不影响预测/选模；如具体测试暴露二元假设，只窄改相关模块并用该失败用例证明修复，不改协议算法。

## 3. 保存结果检查与负例

- [x] 3.1 为上述 r2 development 结果执行 recompute 和同 seed compare；测试禁止拟合及原始 demand/graph 读取，验证全部聚合/窗口/horizon/上下文/活跃度/邻居指标和相对收益可重算，记录预测最大绝对差与协议MAE相对差不超过1e-6，单份排他报告及输入前后内容身份相同。
- [x] 3.2 用合成信号及独立 NumPy 公式生成 r2 的 v2-format JSONL 和匹配 demand hash 的 source-sha256.txt，补 align-v2 正例；验证身份/划分/五基线及全部窗口/horizon/activity/balanced指标和冻结参考在既有1e-12容差内，检查不读取原始数据，参考前后字节不变，证据明确为 fixture。
- [x] 3.3 补 r2 检查负例：临时参考只有 r0/region、参考缺来源 manifest、来源身份不符、保存身份/掩码不符、预测/指标超差、报告碰撞及路径在输入内；验证既有 failed/mismatch/limited 语义、相应非零退出和安全目的地失败报告，禁止把缺参考/缺身份宣称为对齐成功，不放宽容差。

## 4. 文档、最小依赖与回归

- [x] 4.1 更新 README §4.5 和 execution-guide.md 当前入口 §7，列出三种count粒度、r2_id、r2 development 示例及检查参考范围，明确正式 r2 run 需另行授权；用文档 smoke 及人工核对确认命令与当前CLI一致，T004历史两组范围保留，protocol.md规范正文不改。
- [x] 4.2 扩展现有最小依赖 smoke 到 r2，在仅NumPy/pandas/PyArrow且阻断图库/GPU库导入的CPU环境运行 help 和完整小fixture入口；验证无新增必需依赖，不使用GPU、PyTorch/PyG/DGL或仓库图数据。
- [x] 4.3 在可用CPU baseline环境运行 `python -m unittest discover -s benchmark/nograph_baseline/tests`，记录准确命令/环境/通过与可选跳过项；核验r0/region数值、身份、旧保存schema、检查报告和development隔离的现有回归通过，不运行真实正式实验、不改旧产物或解封旧包。

## 5. r2 规模 development 成本证据与实现交接

- [x] 5.1 提供可复现的固定seed规模fixture生成脚本（本变更开发证据目录），将 `52 x 2335 x 36` 合成需求和上下文内覆盖写入临时/ignored目录；核验121420唯一节点、r2_id/skill_id网格、输入哈希与生成命令，脚本不导入图库、不写research/runs，不保留大数据进Git。
- [x] 5.2 使用公共入口、独立CPU worker和显式 `--purpose development` / NumPy后端完成一次该规模执行；保存可复查的命令、状态、输入尺寸/身份、环境、读取/拟合/推理/总耗时及峰值RSS单位/测量方法，核验全部模型与关键产物完整且 M=2306980。标记synthetic development，仅报告实测成本，不称为真实r2数据成本/正式run或科学结论，不设虚构性能阈值。
- [x] 5.3 在本变更 `implementation-notes.md` 汇总修改文件、任务对应测试、检查报告和规模成本证据路径/复现方法/限制，核验主规格Purpose已包含r2且delta覆盖旧r2拒绝规则及身份/检查/产物要求；记录范围检查证明协议、既有research/runs、封存包和OpenSpec历史归档未改。不写verification PASS、不改研究任务状态或DELEGATION.md、不commit/push，交给独立verify工作流。
