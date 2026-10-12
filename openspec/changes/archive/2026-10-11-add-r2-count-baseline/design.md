## Context

动机见 [proposal.md](proposal.md)。D016 和 P01-T006 定义实现范围；科学规范仅来自 `research/phases/P01/protocol.md` §3–§6，版本 v3，记录政策 v2。本变更包含多模块验收、参考证据兼容和大规模成本检查，因此保留 design。

只读检查发现：

- `protocol.SUPPORTED_DATASETS` 只有 r0/region，`cli.build_parser` 的 choices 已从映射排序派生，但描述文本写死两组数据。
- `data.load_demand`、覆盖的 raw Parquet/mask 路径通过 `context_columns`/`node_key_columns` 获取身份；默认路径按数据名拼接。runner、指标、产物与 saved-only checks 的数据名和上下文处理没有检索到专门的 r0/region 分支。
- `tests/nb_fixtures.py` 的 demand/graph 写入器已使用协议列；阻塞来自映射和 `build_fixture` 的 r0/else-region 键生成。`test_protocol.py` 显式拒绝 r2，minimal-dependency smoke 当前只跑 r0/region。
- `align-v2` 按结果数据名索引 JSONL；缺失对应记录会失败，来源身份缺失会 limited。来源 manifest 按 `demand/<dataset>.parquet` 查找，不需新增 r2 特例。
- 现有 runner 保存阶段耗时和 `resource.getrusage` 峰值 RSS，CLI 使用独立 worker。大规模验证应走这条路径，而不是在已跑多个 fixture 的测试进程中声称测得单次峰值。
- 主规格含 r2 拒绝场景、二元身份/对齐说明和 `Both supported datasets...` 标题。OpenSpec 指令说明既有能力的 delta Purpose 被忽略；本轮仅直接更新主规格 Purpose 的粒度列表，行为变更仍由 delta 承载，归档时同步要求。

## Goals / Non-Goals

**Goals:** 用现有数据名映射贯通第三种上下文身份；用可独立核验的 fixture 证据覆盖入口、报告和成本；控制 r0/region 兼容性。

**Non-Goals:** 不引入通用数据注册框架、schema 升级或新科学配置。完整图结构研究审计不新增进 baseline：这里只复用既有上下文端点覆盖审计；不改变 T002 图语义/时间来源结论。软件 PASS 不改研究任务状态，不代替正式 r2 实验和保存。

## Decisions

### 1. 扩充唯一映射，保持公共接口和数值路径

在 `SUPPORTED_DATASETS` 添加 `"r2": ("r2_id",)`，保留 r0/region 条目及 count-only 限制。CLI 帮助列出三组数据，choices 保持自动派生。以真实入口和保存数组测试确认 data/coverage/runner/metrics/artifacts/checks 继承支持；只有发现可复现的二元假设才修改相应模块。

复用原有 19/1/4 划分、27 月统计、五项基线、五 lambda、验证原始单位 MSE 及平局规则、固定掩码、误差聚合和数值 dtype。r2 的 N 从审计得到，SharedRidge 的 M=19*N；不依赖预计行数验真。

另建 r2 runner 或复制数值算法会产生两套规范实现；改成插件注册系统则扩大这次窄范围的维护成本，均不采用。

### 2. 多上下文 fixture 暴露身份错误

增加 r2 键生成器，允许指定上下文数和技能数；扩充 `build_fixture` 的明确 r2 分支，保留既有 r0/region fixture 语义。写入器继续使用协议列，不添加平行的列名映射。

小 fixture 包含乱序行、跨上下文重复 skill_id、全零/常数节点和四组活跃度边界；合成图包含仅在一个上下文出现的非自环、另一上下文的自环和孤立节点。测试 demand 网格描述、排序、覆盖两端和共用掩码；改变训练期后的值不改变预处理或训练候选参数，单独改变测试标签不改变验证选模，改变有效图覆盖不改变预测。网格缺项属于审计结果，不把既有审计擅自升级为拒绝条件。

负例包括缺 r2_id、重复/非整数/非有限键、错误月份和负/非有限 count、未知图端点/上下文和错误 mask 身份。通过现有边界测试和新 r2 场景控制覆盖量，不复制整个数值测试套件。

### 3. 检查读取保存材料，参考日志明确其适用范围

两个小 r2 development 执行使用相同输入/seed/配置和独立新目录；recompute/compare/align-v2 写临时目录中的单份 `--report`，核对输入前后字节身份。重算与对齐时禁止读原始 demand/graph，检查时禁止拟合。比较沿用 CPU 1e-6，朴素诊断对齐沿用 1e-12；错误身份和指标扰动必须失败。

align-v2 的正例参考用原始合成信号和独立 NumPy 公式生成 v2 JSONL及同目录 `source-sha256.txt`，覆盖身份数量、窗口、全部五基线 validation/test/window/horizon/activity/balanced 指标与 NaiveRef/NaiveRef6。不能直接把新 runner 的 metrics 复制为 expected。参考和测量明确是软件 fixture 证据。

历史 v2 日志保持原样，不伪造 r2 历史记录。负例提供只有 r0/region 的临时日志并断言 r2 的明确失败；缺少来源 manifest 保留 limited，来源不符/数值超差保留失败。现有 r0/region 参考和历史保存格式继续可读，不解封或改写旧包来完成这次实现验收。

### 4. 成本路径采用可重复生成的全规模合成输入

采用保守规划假设：r2 规模证明使用固定 seed 的 `52 x 2335 x 36` 合成 count fixture（121420 节点、2306980 个 Ridge 训练样本），无需读取仓库数据或运行正式预测实验。生成 fixture 的小脚本放在本变更开发证据目录，明确生成规则、seed、输入哈希和尺寸；合成图使用可追溯的上下文内边并覆盖部分孤立节点，不导入图库。不要把完整大 fixture 纳入 Git。

先生成到系统临时目录/ignored scratch，然后以 `python -m benchmark.nograph_baseline run --data-name r2 --mode count --purpose development --ridge-backend numpy` 加显式 fixture 路径/新 run ID 运行一次独立 worker。保存命令、执行状态、环境、输入尺寸/身份、读取/拟合/推理/总耗时、峰值 RSS 的单位和方法及关键产物完整性。小 fixture 负责重复和完整检查，不要求昂贵全规模重复进入普通 unittest。

不设未经测量的性能阈值，也不把合成数据的时间称作真实 r2 成本。真实数据的非正式测量可在后续明确范围后补充，不是本变更的必要科研 run。只有实测发现无法完成的资源问题才考虑协议等价的分块优化；若需要扩展设计范围，先记录具体证据和待决问题。

### 5. 文档和规格保留历史含义

README §4.5 和执行指导 §7 的当前支持列表加入 r2、`r2_id`、development 示例与检查说明，并写明正式 r2 run 需另行授权。保留 T004 两组已接受证据和首轮诊断代码的历史范围，不批量替换所有“两组”文字，也不编辑协议 §6.1 的历史实现说明。

delta 扩充入口/需求身份/覆盖/检查与成本场景，明确正式证据条件与本次软件证明边界；用 RENAMED 将二元产物标题变为 `Supported datasets produce complete formal artifacts`，再提供完整 MODIFIED 块。其他未改变的科学要求沿用主规格。

## Risks / Trade-offs

- [相同 skill_id 被错误跨上下文对齐] -> 小 fixture 重用 skill_id，按 r2_id 保存节点、覆盖及逐上下文指标，并校验重算。
- [fixture 参考与实现同源造成虚假通过] -> 期望值由独立公式计算；扰动指标、身份、参考来源作反证。
- [完整规模保存和逐节点报告占内存/磁盘] -> 独立 development 测量，保留实际成功/失败与峰值；普通单测保持小规模，默认不保留落选候选数组。
- [Purpose 提前体现计划支持] -> 本轮仅摘要变更，行为仍以未归档 delta 为规划；不得将其宣称为实现已完成。
- [协议字节身份与科学版本不同步] -> 沿用原 compare 的身份检查；不因 v3 字符串相等而忽略协议文件差异。
- [实现证据被误当作任务完成] -> 证据显式 development/synthetic，apply 只记录实现说明，独立 verify 后的科研接受留给研究侧。

## Migration Plan

后续 apply 增加映射、fixture/测试和入口文档，再运行针对测试、CPU 全套回归及一次规模成本检查，记录证据路径/复现方法。无需数据转换、旧产物重写或包迁移。暂停使用新 r2 选项即可停止新增执行；已有执行材料不覆盖。独立 verify 和 archive 由用户另行启动，本工作流不开始实施、实验、归档或 Git 写入。
