## Context

动机见 [proposal.md](proposal.md)。权威来源按 P02 计划 §2–§5 → D023/D007/D006/D015 → P01 协议 §3、§4.2、§5.1、§6–§6.2 → 现有代码与规范的顺序读取。科学版本 `P1-count-L6-H3-v3`、政策 `P01-records-v2` 不变；本设计仅实现 P02-T001，不接受 P02-T002/T003 的实验或科学结论。

已读实现约束：

- `nograph_baseline/protocol.py` 已有不可变 `MAIN_SPLIT`、28 窗口、固定月份和四组边界；A/B 是无图内部回测，本入口只使用 main，不借用折配置。
- `data.py` 校验整数键、有限非负 count，按数值键稳定排序并生成 float32 `[N,36]`；`node_keys_sha256()` 使用 little-endian int64，窗口为 `[W,N,L/H]`。`baselines.py` 提供五朴素方法与验证 MSE/表序平局选参照；`metrics.py` 使用 float64 误差累加，空组 null，RMSE 从全部平方误差计算。
- `runner.py`/`cli.py` 有独立 worker、来源记录、purpose 和成本模式；`checks.py` 有保存后重算/比较及 1e-12/1e-6 容差，但依赖 SharedRidge 方法/产物，不可把新模型直接伪装成 Ridge。`coverage.py` 的邻居掩码统计非自环边的两端，不是消息方向。
- `prepare_graph_data.py` 先将 ID 转整数、按整数 tuple 排序，再把 `(context,row_id)` 和 `(context,col_id)` 分别映射为 source、target；旧 JSON 的 edge_weights 保存重复行 multiplicity。新包只复用身份语义，不使用旧 weighted 数据管道。
- `nograph-baseline-entry` 要求无 torch 路径及 Ridge 标准化；`graph-forecast-data-pipeline` 要求旧导出保留 multiplicity。两者不修改。新能力使用冻结的原始 count GRU，不把 Ridge 的标准化或旧图的权重规则扩展过来。
- `.gitignore` 已忽略 `/scratch/`；README §4.5 是现有无图入口。新包和 README 新章节独立加入，不编辑研究文档。

本轮对源 Parquet 作只读结构核对（没有训练、预测或创建 run），事实如下；apply 必须以测试/运行断言再确认：

| 数据 | demand 节点 | context id | skill id | graph 有向行数 |
| --- | ---: | --- | --- | ---: |
| r0 | 2335 | `{0}` | `0..2334` | 60804 |
| region | 16345 | `0..6` | `0..2334` | 218840 |
| r2 | 121420 | `0..51` | `0..2334` | 321374 |

Demand 列为 `<ctx>_id,skill_id,2021-01..2023-12`（36 月），各表是完整上下文×技能网格。Graph 列仅 `<ctx>_id,row_id,col_id`，没有 weight/frequency；端点是上下文内 skill_id 值。各表无重复行、无自环，反向边覆盖率 1.0；每条边的两个节点属于同一上下文，故全局邻接块对角。全局索引在这些已确认稠密网格上为 `context_ordinal*2335+skill_id`；不能对任意 fixture 或未来数据不加验证套此公式。

本轮只读环境核对：默认 `python` 是 3.13.2，`find_spec("torch")` 为 None；`conda run -n job-sdf-baseline python` 指向 `/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python`，版本 3.11.17，torch 2.14.1（`torch.version.cuda=None`、CUDA unavailable），NumPy 1.26.4、pandas 2.2.3、PyArrow 17.0.0。后续环境检查与实际命令必须记录这些精确版本，不依赖默认解释器。

## Goals / Non-Goals

**Goals:** 数值身份与 P01 一致；同一编码器/预算下三方法可配对；方向、零消息、参数量和保度打乱能以小 fixture 证伪；保存材料足以脱离源数据重算，独立重复可判断；CPU 开销可测。

**Non-Goals:** 不引入门控、剪枝、边学习、额外图参数、log/标准化/裁剪新配置、GPU、A/B 图回测或新图来源；不运行完整研究比较，不以软件测试判断 §6.2 收益；不改研究记录、旧 run/封存包/已有归档，不读写委托指针，不 commit/push。正式运行另行授权。

## Decisions

### D1. 独立包与 P01 数值契约

新包直接 import 无图 `protocol`、`data`、`baselines`、`metrics`、必要的纯 CPU coverage 工具。新包的 config、writer、checker 适配放本包；不修改 P01 常量或给其导入路径增加 torch。先固定小 fixture 的 P01 节点键哈希、float32 输入/标签逐元素值、窗口元数据、五朴素预测/分数、参照选择、掩码与指标作为回归依据。实际发布数据重验 NaiveRef 为 LastValue；fixture 按验证 MSE 选择，不强迫任意 fixture 的赢家为 LastValue；发布身份与既定参照不符时明确失败，不静默重选。

替代方案：复制常量/计算易漂移；复用整个 Ridge runner 会错误应用标准化与方法列表；改 P01 包默认行为会破坏旧契约，均否决。

### D2. 每节点 GRU 的向量化与确定性

数学定义为对每个窗口和节点 `h(v,0)=0`，`h(v,t)=GRU_theta(x(v,t),h(v,t-1))`，t=1..6；`x` 为原始 count 标量，最终 `h_v` 为 `[N,32]`。同一时序编码器的 theta 在节点间共享，递归隐状态按节点独立；“每节点独立”指计算轨迹与状态独立，不能把 N 当时间轴或拼接节点。以 batch 维承载节点的单层、单向、bias=True GRU(1,32)，无 dropout；head 为共享 Linear(32,3)。窗口间与 train/validation/test 间均重新置零，不预热、不在线更新。用逐节点循环同权重 oracle 对照向量化结果，并测试扰动另一节点在编码器阶段不影响本节点；图消息后允许影响入邻居目标。

CPU float32 模型与原始预测，指标转 float64；固定 Python/NumPy/torch 模型 seed、torch deterministic algorithms、CPU intra/inter-op 线程为 1，BLAS 环境在线程库导入前固定为 1，排序后做聚合。模型 RNG 与打乱 RNG 分离，配对模型 seed 使三分支初始 state_dict 相同，但各自独立训练和选择 checkpoint，不共享训练后的权重。

替代方案：为 N 节点各学习一套权重使容量随网格规模变化且偏离同一编码器；跨节点共享一个隐藏状态混合身份；状态跨窗口延续改变 L6 信息预算；GPU/随机归约增加环境差异，均不采用。

### D3. 节点映射和图加载

以 P01 canonical keys 建立整数 tuple→index 映射，`row_id` 为 source skill，`col_id` 为 target skill，前缀为本行上下文，未知端点、非整数键、缺列一律在训练前失败。对已发布数据重新断言上表规模、稠密完整网格及月份；验证每个索引等于 `context_ordinal*2335+skill_id`，再与 `prepare_graph_data.build_graph_dataset()` 的节点键和端点结果交叉对照（小 fixture 足够，不生成全量旧 JSON）。整数 2/10、打乱行序、多上下文重复技能的 fixture 锁定数值排序，不默认字符串字典序等于整数序。普通小 fixture 允许非稠密键，必须使用映射正确解析。

替代方案：直接把 row_id/col_id 当全局 index 会混上下文；字符串拼接排序会交换 2 和 10；未经断言使用 offset 会接受错误网格，均否决。

### D4. 入边二值均值与 multiplicity

边 `(u,v)` 对目标 v 聚合 `sum h_u / in_degree(v)`，再做 `h'_v=h_v+message_v`。只用 torch 内建 CPU 张量操作（排序的 source/target、index_add 或等价确定性稀疏归约），不引入 PyG/CUDA 扩展。邻居集合不含自己，发布图预期无自环；发现自环时明确拒绝，不把它加到残差中重复计算。重复行先记录 raw/unique/duplicate 行数、multiplicity 分布/最大值，再按唯一的上下文有向边聚合，每边权重 1；multiplicity 仅审计，不作频率或均值权重。记录无可区分边强弱的 frequency 列。

非对称 fixture 如 `0→1,2→1,1→2` 且各节点不同 h，必须得到 `m_1=(h_0+h_2)/2,m_2=h_1,m_0=0`；与出边算法有意给出不同答案。不要用真实对称图作为唯一方向证据。固定评估邻居掩码使用 P01 原发布图两端覆盖语义，所有方法同一份，不随 shuffled 的邻接重新计算。

替代方案：出边、无向化、带 multiplicity 权重、GCN 度归一化或可学习 attention 都改变冻结算子；旧 weighted 导出仍符合其原规范，但不作为本能力输入，均不采用。

### D5. 零消息、参数同构与相等的适用条件

无入边节点初始化消息为精确 0，避免除零；使用相同编码器/head 参数、相同输入与零初始状态比较 `self`/`graph`，孤立节点预测要求逐元素相等（非 allclose）。此断言是同参数算子契约；分别训练后的两个模型参数不同，不承诺它们的孤立节点预测相等。空图下整个输出也必须逐元素相等。

模型可学习张量集合仅 GRU+head，图相关对象为非参数数据/buffer；测试三方法 parameter names/shapes/numel 一致且 graph-only 参数集合为空。所选标准 GRU 的预期计数：GRU `96+3072+96+96=3360`，head `32*3+3=99`，总计 **3459**，与 N、E 无关。这是架构计算值，尚非实现测量值；后续以 `sum(p.numel() for p in parameters if requires_grad)` 实测断言 3459 并写入运行元数据、implementation-notes，若不符先修复而非改冻结设计。

替代方案：加可学习投影/归一化/门控或单独的图 head 破坏参数同构；用容差掩盖零度 NaN 或仅比较 independently trained 输出均不能验证本断言，否决。

### D6. 上下文内有向保度双边交换

从已去重、无自环、按上下文及 source/target 排序的边集出发。每个上下文对两条不同边 `(a,b),(c,d)` 提议 `(a,d),(c,b)`；拒绝自环、重复边、无变化提议，原子替换两边。有向入/出度逐节点精确保持，不强制保持对称性（冻结条件只有入/出度，额外对称约束改变零假设）。上下文排序固定，使用 NumPy PCG64 + `SeedSequence([shuffle_seed,context_id])` 派生本地 RNG，不依赖 Python hash 或 set 遍历顺序，图构造不消费模型 RNG。

实现层固定工作量为每个非空上下文接受 `10*E_ctx` 次交换，最多尝试 `100*E_ctx` 次；记录算法版本、目标/实际接受数、尝试数、拒绝原因、源/结果边集哈希、交集比例、对称差边数/比例和每上下文结果。最后逐节点检查入/出度、上下文、边数、无自环/重复，以及每个非空上下文最终边集确实不同。空上下文记录空；非空但不可交换、达到上限未完成目标或最终回到原集合则明确失败，不能返回原图伪称 shuffled。工作量与变化量是实现审计，不以“10E”宣称随机图已混合或设新的收益门槛。

打乱 seed 固定 0/1/2；给定数据与打乱 seed 的图在所有模型 seed 与重复执行中相同。每个 `(dataset,model_seed,shuffle_seed)` 独立训练一次；三图平均对照为 `(MAE_0+MAE_1+MAE_2)/3`。只读汇总要求三成员齐全且模型 seed、数据/配置/掩码一致；缺失/重复 seed 失败。输出三项与平均，不能先平均预测、取最大 MAE、按图测试分数重试/选图。

替代方案：全局端点置换可能跨上下文且不保度；单边随机重连破坏度；保持无向度并不证明逐节点有向入/出度；挑最弱打乱图违反 §6.2 #4，均否决。

### D7. 训练与选模只补实现细节

三方法共用 200 epoch、hidden 32、Adam；补足未在冻结表中展开的实施值：lr=1e-3、betas=(0.9,0.999)、eps=1e-8、weight_decay=0、无 scheduler/early stopping/梯度裁剪。原始 count 输入/标签、原始单位均方损失，主输出不裁剪；不继承 Ridge 标准化，不增加尺度搜索。每 epoch 逻辑训练集为 19*N*3 个元素，按窗口起点升序和上下文升序分块前向/反传，每块 squared_error_sum 除以全局元素数累积梯度，epoch 末仅一次 optimizer.step；分块保留完整上下文邻接，等价全逻辑 batch 的平均 MSE，避免按上下文大小重新加权或每块各自 step。固定 chunk/累加次序并记元数据。

每 epoch 更新后验证，记录训练累积时的原始单位 MSE/MAE及更新后的验证 MSE/MAE（两种测量时点明确命名），200 epoch 全部跑完；仅最低验证 MSE 选 checkpoint，精确平局选最早 epoch，保存完整 200 行与选择理由。checkpoint 固定后才执行测试指标计算；测试标签不得进入训练/选择 API。开发模型 seed 为 0/1/2，最终为 0..4，模型 seed 单独显式传入；可报告 seed profile，不能因模型 seed 不同改变预算。实现检查用少量 fixture 执行，不在 apply 跑完整研究矩阵。

替代方案：按验证 MAE、测试成绩、提前终止或不同分支学习率选择均改变选模/预算；按节点任意 batch 会截断邻居消息；每块独立更新会改变优化定义，均否决。上述新增实施值须在正式比较前固定于解析配置，不能按中途成绩修改科学冻结条件。

### D8. 显式方法/两类 seed 与两层 purpose

公开新入口拟为 `python -m benchmark.graph_value_skeleton run --data-name r0|region|r2 --method self|graph|shuffled --model-seed <int> --purpose development|formal --run-id <fresh-id>`。shuffled 必须额外给 `--shuffle-seed 0|1|2`，其他方法禁止该参数；不以修改模块全局常量切方法。方法/模型 seed/打乱 seed/重复 ID 都写配置，run-id 只是唯一身份，不负责解析配置。

purpose 默认 development，写已忽略 `scratch/graph-value-skeleton/<run-id>/`；只允许经过 resolve/symlink 检查的 ignored scratch 或系统临时输出根，拒绝 research/runs、其他研究目录、旧归档及可逃逸 ID。formal 显式选择才定位仓库 `research/runs/<run-id>/`，测试仅测路径解析，不在仓库创建正式目录。两者计算一致，均 exclusive 创建、不覆盖。formal 是软件可用入口；运行权限仍须研究侧另行授权，本变更不自动调度它。

替代方案：复用旧入口 formal 默认不适合此次开发隔离；把方法写进全局配置或仅靠目录名会串状态/丢失轴身份；给 development 任意目录覆盖会绕过边界，均否决。

### D9. 完整产物与来源

development 也使用完整软件产物契约（标注非科学接受证据），fixture 的来源明确标为 synthetic。拟定布局：

| 文件/目录 | 作用 |
| --- | --- |
| `config.json`, `command.json`, `provenance.json` | 目的、P02-T001/后续实际任务、三条变换轴、解析配置、版本、执行代码与数据/图身份、准确命令/cwd |
| `source.json` 与必要 patch/未跟踪执行源码 | 固定 commit/path 引用，必要的未提交实现内容；科学协议和政策内容可定位，不保存无关研究文档差异 |
| `environment.json`, `measurements.json`, `status.json` | Python/torch/依赖/CPU/OS/线程、耗时/峰值 RSS、成功失败中断/unfinished |
| `nodes.parquet`, `windows.json`, `masks.npz`, `audit.json` | canonical 键/哈希、28 窗口全部角色/月身份、固定训练27月/发布图掩码、数据审计 |
| `graph-audit.json`, `graph/edges.npy` | source/target、二值/multiplicity/方向、实际图与源身份、打乱算法/seed/度及改边审计 |
| `gold/{validation,test}.npy`, `predictions/<method>/{validation,test}.npy` | `[1,N,3]` / `[4,N,3]` 标签及原始预测；五朴素方法也保存，允许共享 gold |
| `models/selected.npz`, `selection.json`, `training-history.json` | 纯数值 named tensor 参数、实际参数量、epoch/验证分数/平局理由、全部200 epoch、NaiveRef 表与 LastValue 身份 |
| `metrics.json`, `summary.md` | 完整指标、相对冻结参照结果、限制，不能写实验收益结论 |

参数保存为可无 pickle 加载的 NPZ named tensors（键名到参数名映射显式记录），重算不需要加载 torch 模型；raw-count preprocessing 明确 `none`，固定分组用的训练统计另存。所有参数/图/输入的实际内容身份可定位；启动前后检查源内容未变。仅运行所需源码/协议有未提交内容时保存相应差异或文件，不能把工作区全部 diff（含研究记录）打包；缺少来源身份必须披露，不伪造 clean 状态。

失败/中断保留已经形成的配置/状态、错误阶段、可用产物及成本；不可捕获终止残留 running 由检查器判 unfinished，不推断成功。成功不自动 commit/归档/备份。正式存储记录与研究接受留给后续研究流程。

替代方案：只存 metrics 不能复核；只存 state_dict pickle 不能独立数值读取；复制整个仓库/diff 违反政策且捕获无关记录；每次保存所有落选 checkpoint 没有必要，保留选择分数及被选参数即可。

### D10. 只读重算与同 seed 重复是两种检查

`recompute --run-dir ... --report ...` 仅读保存的预测/标签/节点/窗口/掩码/选择及配置，复算 validation/test 全部已报告总体、逐窗口/horizon/上下文/活跃度/常数/邻居、等权活跃度 MAE、负预测比例、样本数与收益。所有方法使用同一份 training27 和发布图掩码，空组为 null/status=empty/count=0；总体 RMSE=`sqrt(total_squared_error/elements)`。浮点归约复算容差为 `abs(a-b)/max(1,abs(a),abs(b))<=1e-12`；schema/键/shape/dtype/角色/计数/掩码/null 状态须精确一致，非有限数立即失败。

`compare --run-a ... --run-b ... --report ...` 是两个独立同 seed 执行的重复检查，不是 self 与 graph 的方法比较。先严格核对同 dataset、demand/graph/节点身份、协议与政策的可定位内容、方法、两类 seed、预算/实现配置、固定掩码、来源代码、CPU 环境与执行条件；仅 run-id、目录、时间/成本等执行特有值可不同。再计算协议 MAE 差 `abs(MAE_a-MAE_b)/max(1,MAE_a,MAE_b)<=1e-6`；逐元素预测与其他误差指标用同一 max(1,abs(a),abs(b)) 归一化差 <=1e-6，并独立记录预测最大绝对差（不能把“最大绝对差”误当归一化 MAE 判据）。身份不符即使预测相同也失败；超差先调查执行条件。

另提供 `summarize-shuffled --run-dirs <seed0-dir> <seed1-dir> <seed2-dir> --report ...`，只读重算各成员 MAE 后按模型 seed 构造三图平均；汇总允许 shuffle_seed、结果图身份和对应训练结果不同，要求原始发布图身份、模型 seed、代码/环境、其余训练配置和固定掩码相同。比较与汇总的 required method 集合不能用交集掩盖缺项。全部检查只写一份独占报告，含输入/必要内容身份、checker 源码身份、命令、容差、状态/差异；不得写输入目录或覆盖已有报告，开发报告也只在 scratch/临时路径。重算/汇总不读取源 Parquet、不训练、不调用模型前向。重算覆盖 `metrics.json` 所有报告值与汇总值；history 的200行分数作为执行记录保存并检查结构/选择一致性，不宣称在没有全部epoch参数/预测时独立重算每一epoch分数。

替代方案：重训重算混淆执行波动；只比较总 MAE 会漏掉掩码/数组错误；将不同 seed/方法的差异视作重复通过或只比较共同指标会假阳性，均否决。

### D11. 精确 CPU 运行时与可复现命令

独立 requirements 固定 `torch==2.14.1` 及现有三包精确版本，环境记录 Python 3.11.17 与 CPU build。执行前检查 torch 设备/版本，不自动安装 GPU 包或转默认 3.13。以下为**待实现后的命令契约**，本轮未运行这些入口；README 必须与最终 help 对齐：

```bash
conda run -n job-sdf-baseline python --version
conda run -n job-sdf-baseline python -m unittest discover -s benchmark/graph_value_skeleton/tests -v
conda run -n job-sdf-baseline python -m unittest discover -s benchmark/nograph_baseline/tests -v
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton run --data-name r0 --method graph --model-seed 0 --purpose development --run-id probe-r0-graph-s0-a
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton run --data-name r0 --method graph --model-seed 0 --purpose development --run-id probe-r0-graph-s0-b
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton run --data-name r0 --method shuffled --shuffle-seed 0 --model-seed 0 --purpose development --run-id probe-r0-shuf0-s0-a
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton recompute --run-dir scratch/graph-value-skeleton/probe-r0-graph-s0-a --report scratch/graph-value-skeleton/reports/probe-r0-recompute.json
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton compare --run-a scratch/graph-value-skeleton/probe-r0-graph-s0-a --run-b scratch/graph-value-skeleton/probe-r0-graph-s0-b --report scratch/graph-value-skeleton/reports/probe-r0-repeat.json
```

同样模式支持 self、region、r2；打乱 seed 1/2 使用独立命令/目录。允许后续按需一次覆盖 r0/region/r2 的 development 冒烟批次，不据此执行全 seeds×methods×repeats 研究矩阵。开发/最终 seeds profile 仅定义允许的研究配置，不自动运行。无 torch 的现有无图测试在其原 Python 环境运行，以阻止反向依赖。

替代方案：未指明解释器的 `python`、宽泛 torch 版本或 PyG 扩展使本机路径不可复现；把环境探测成功当作 CPU 模型执行成功也不成立。

### D12. 成本测量与有限测试

每次执行用新 CPU worker 测量 demand/graph read、shuffle、training（含明确的 validation 子项）、selected inference、write/check 与总耗时；用 `resource.getrusage(RUSAGE_SELF).ru_maxrss`，记录 native 单位/数值及 bytes（Darwin bytes，Linux KiB×1024），记录机器/CPU、版本、线程、N/E、200 epoch 和峰值作用域。不预报训练速度；fixture 与真实数据成本明确区分。正式比较前统一确认成本属于后续研究动作，不自动改变 200 epoch。

测试以小的多上下文、非对称、可交换 fixture 为主，覆盖：P01 独立 oracle；整数排序/缺端点；GRU loop 等价/节点与窗口状态隔离；参数量/零消息；非加权方向/重复边；shuffle 的度/变化/可重复/失败；训练 loss/预算/验证 MSE 选择/平局/测试隔离；产物完备性与 tamper 失败；禁止源读取/训练/前向的重算；seed/方法/图/环境 mismatch；purpose/路径/symlink/覆盖拒绝；原无 torch 测试回归。端到端覆盖三 schema×三方法与 3 shuffle seed；fixture 同 seed 至少两次（各方法），不依赖全量数据。200 epoch 不在生产路径中缩短；辅助训练单元测试可用内部 toy 循环测局部逻辑，不能标作冻结模型完成运行。

替代方案：全量训练代替单元断言成本高且对称图抓不住方向；仅 mock torch/worker 不能证明端到端 CPU 可跑；为了快速检查偷偷减少公开 epoch 会模糊冻结预算，均否决。

### D13. 不改科学协议与验收归属

冻结原始 count、简单 GRU、共享 head、无额外图参数来自 P02/D023；其余身份、验证原始 MSE、主报告与门槛沿用 P01。新增 lr/批次/平局/归约顺序只将未展开的实施条件显式化且三方法一致，不改变科学版本。§6.2 仍为开发 ≥2/3 seed 正且中位收益≥1%，最终 ≥4/5 且中位≥1%及≥同 seed 重复差5倍；图相对自身和三图平均都需满足，总体 RMSE 跨 seed 均值相对参照恶化≤1%，零参照不计算 gain。当前能力仅保留足以判断的材料，不在实现验收中要求模型达到收益门槛；分组收益不能升级为整体主张。

发布图构建截止时间未知，按 D015 披露固定评测期限制，不声称无未来图信息或严格历史/时间泛化。研究侧在后续归档 PASS 且 Verification Basis 匹配当前实现后另行逐条接受；apply 只写 implementation-notes，独立 verify 不修代码、archive 按其工作流分别触发。

替代方案：为让模型过门槛改输入尺度、切分、选模指标/预算或只报有利分组会改变研究口径；把 OpenSpec PASS 当科学接受则越过职责，均否决。

## 研究侧归档后将逐条核对的验收清单

以下编号供 tasks 与 verification Evidence 对齐；每项须有可定位测试/断言、命令、输入身份与结果，不能只复述设计。

| ID | 验收断言 |
| --- | --- |
| A01 | 三组 demand 路径/schema、36 月、2335/16345/121420 节点，skill/context 稠密完整网格与数值合法性重新断言 |
| A02 | graph 三路径、三列无 weight/frequency，60804/218840/321374 行、无重复/自环、对称率1、块对角；差异显式失败 |
| A03 | 整数排序、canonical node key sha256、窗口输入/标签值及元数据与 P01 相同；offset 公式经验证，2/10 排序与上下文 fixture 通过 |
| A04 | 每节点 raw-count L6 GRU hidden32、共享 head H3、状态不跨节点/窗口；loop 与 vectorized 等价 |
| A05 | self/graph/shuffled 独立训练、初始配对条件一致；实测 trainable tensor 集合/参数量相同且为3459，graph 额外参数为0 |
| A06 | 同参数无入边节点/空图预测逐元素相等；非对称 fixture 锁定 row→col 入边非加权均值；重复行审计不加权 |
| A07 | 每上下文双边交换保逐节点入/出度、无跨上下文/自环/重复、边集确实改变，同数据同 shuffle seed 可复现；失败不伪成功 |
| A08 | shuffle seeds 恰为0/1/2，每模型 seed 独立三次训练，保存三项 MAE并算术平均；缺项拒绝，不取最弱/均值预测 |
| A09 | L6/H3、28窗口、train0..18/validation21/test24..27、omitted19/20/22/23与滚动真历史，NaiveRef=LastValue 发布身份保持 |
| A10 | training27 四活跃组、发布图有/无邻居掩码所有方法逐元素相同；完整总体/窗口/horizon/上下文/分组/负预测/空组/样本数及等权MAE |
| A11 | 每模型200 epoch/Adam/hidden32；模型seeds开发0/1/2、最终0..4，原始单位MSE训练和验证选模、完整分数与平局理由、测试不参与 |
| A12 | §6.1 目的/任务、运行代码/相关dirty内容、版本/内容、数据、配置、环境/命令、状态、预测/标签/身份/掩码、被选参数与训练选模记录齐全可恢复 |
| A13 | 只读重算不读源数据/不训练/不前向，全部报告1e-12归一化容差内且身份精确；输入字节不变，损坏材料失败 |
| A14 | 同seed至少两次独立CPU执行，MAE归一化差≤1e-6，记录预测最大绝对差及逐元素容差；不同轴/来源/条件明确拒绝 |
| A15 | 显式method/model-seed/shuffle-seed、无全局切换；development默认只写ignored scratch/临时，formal另行授权，symlink/覆盖不能绕过 |
| A16 | Python3.11.17/torch2.14.1 CPU命令实际可跑，不依赖GPU/PyG扩展；原无torch入口/测试保持兼容 |
| A17 | 每次实测分阶段耗时、RSS单位/方法/作用域与环境；fixture/真实冒烟区分，不报告未经测量的成本或科学结果 |
| A18 | README仅新增入口章节；无研究记录/协议/旧run/已有归档改写，无正式研究矩阵；归档current-basis PASS供研究侧接受，不等于收益判定 |

## Risks / Trade-offs

- [原始大 count 导致饱和或数值异常] → 保持冻结 raw-count，非有限 loss/预测明确失败留证据，不自行标准化或改预算；诊断/科学配置修订另行决定。
- [有向双边交换不能保证充分混合] → 固定工作量、逐上下文变化与重叠报告；不声称均匀采样，不挑图，不静默回退。
- [全量 r2 的 CPU 训练成本尚未知] → 完整上下文分块、单worker实测；不能用成本估计替代事实或自行减少epoch。
- [向量化/分块归约浮点顺序不同] → 同环境同顺序、CPU确定性与独立重复；loop等价使用明确浮点容差，孤立零消息相等仍精确。
- [新来源采集误捕获无关研究改动] → 显式新包及实际依赖模块允许列表，仅捕获运行相关内容。

## Migration Plan

先冻结 P01 fixture 数值依据，再新增图映射、模型、shuffle、训练、产物/检查；通过 fixture 与按需 development 冒烟、原无图回归后仅更新 README 新章节与 implementation-notes。新能力为增量入口，无旧产物迁移或数据重生成；回退仅停用新入口，保留历史证据。后续 apply → 独立 verify-change → 必要 fix → archive-change 按各自新请求触发，不在本轮执行。

## Open Questions

- 尚无实现，实际参数量运行测量与同seed误差/完整200epoch成本仍待实现检查取得；3459为预期断言，不能冒称已测得。这些只影响实现证据，不更改科学口径。
- 发布图构建截止时间仍未知；不是本变更待解决的实现选择，沿用 D015 固定评测期限制。若未来要求严格历史主张，需另行研究范围和图来源决定，本变更不解决也不扩大科学主张。
