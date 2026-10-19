本清单由显式 apply 执行；条目状态以复选框为准，完成后由独立 verify 复核。验收编号 A01–A18 对应 [design.md](design.md) 的“研究侧归档后将逐条核对的验收清单”。所有模型检查使用 development/fixture，正式运行、科学比较和研究接受不在清单内。

## 1. 先固定 P01 数值契约与数据身份依据

- [x] 1.1 在实现新计算前，使用当前 P01 纯数值模块为 r0/region/r2 schema 的确定性小 fixture 保存预变更依据到临时/ignored scratch：canonical keys/sha256、float32信号、L6/H3输入和标签、28窗口元数据、五朴素预测/验证分数/参照、训练27月活跃度/常数/邻居掩码与全部指标；用独立数组oracle核对并记录命令、输入生成规则、容差与自然变化字段清单，不创建正式run。（A03/A09/A10）
- [x] 1.2 建立 `benchmark/graph_value_skeleton/` 包、独立依赖文件及小型多上下文fixture注入设施；复用P01的protocol/data/baselines/metrics/coverage而不改原公共默认行为，验证新包fixture身份与1.1逐元素/哈希/元数据一致，并测试非法key、月份、值、rate、A/B图折及不支持dataset拒绝。（A01/A03/A09/A16）
- [x] 1.3 实现发布数据结构断言，与fixture路径明确区分：三组demand节点2335/16345/121420、36月、技能0..2334、上下文{0}/0..6/0..51及完整网格；用小型模拟表测试断言正负例，真实文件只读核对按需记录，不作为全量测试依赖。（A01）

## 2. 图加载、节点映射与固定分组

- [x] 2.1 实现上下文整数tuple→canonical index查找，row_id作为source、col_id作为target；以2/10、多上下文同skill、乱序和非稠密fixture对照P01排序及旧prepare_graph_data结果，证明发布稠密网格offset公式，测试缺列、非整数/未知端点/跨上下文索引失败。（A02/A03）
- [x] 2.2 实现发布图schema/行数60804/218840/321374、无weight/frequency、无重复/自环、反向对称率1和块对角断言；通用fixture加载记录raw/unique/duplicate/multiplicity分布后构造唯一二值有向边，自环明确失败，测试重复行仅审计不加权及结构断言负例。（A02/A06）
- [x] 2.3 从training27与原始发布图固定活动/常数/上下文/有无邻居掩码，保存其身份；fixture验证0、1/3、2/3边界与空组、P01两端非自环覆盖语义，self/graph/shuffled共享完全相同掩码且打乱邻接不重定义评估组。（A09/A10）

## 3. 编码器、入边传播与参数断言

- [x] 3.1 实现raw-count GRU(1,32)、共享Linear(32,3)、每节点/每窗口独立零隐状态的向量化路径；以同权重逐节点loop作oracle，验证normalized误差≤1e-6、节点输入扰动隔离、窗口/split重置、[N,32]与[N,3]形状。（A04）
- [x] 3.2 实现self与图残差入邻域非加权均值及shuffled共用算子，只使用CPU内建张量操作；非对称`0→1,2→1,1→2`和重复边fixture验证方向/均值，零入度和空图同参数输出要求逐元素相等，拒绝出边/额外自环贡献与非有限值。（A06）
- [x] 3.3 为三方法实测并断言相同trainable tensor names/shapes/count：GRU3360、head99、合计3459且graph-only参数为空；用不同N/E测试计数不变，验证同model seed初始参数相同、shuffle RNG不消耗模型RNG、模型训练状态彼此独立，将实测计数留给运行元数据与implementation-notes。（A05）
- [x] 3.4 在新worker固定CPU、Python/NumPy/torch种子、deterministic algorithms、intra/inter-op及BLAS线程=1；在GPU/PyG/CUDA扩展不可导入条件下测试真实GRU与聚合前后向可执行，记录实际Python3.11.17/torch2.14.1/NumPy1.26.4/pandas2.2.3/PyArrow17.0.0环境，默认3.13不作替代。（A14/A16）

## 4. 保度打乱与三个seed对照

- [x] 4.1 实现各上下文内有向双边交换、canonical排序和PCG64/SeedSequence本地RNG；固定目标10*E接受交换、最多100*E尝试并记录算法版本，测试每次/最终逐节点入出度、边数、无跨上下文/自环/重复保持，且非空上下文最终边集变化。（A07）
- [x] 4.2 保存原图/结果边集哈希、每上下文尝试/接受/拒绝、交集/对称差及比例，测试同shuffle seed在不同进程hash迭代、输入边行序/model seed/run ID下生成相同图；覆盖空上下文、不可交换、预算耗尽、最终回原图的显式失败，不默默改seed重试或返回原图。（A07）
- [x] 4.3 支持且限制shuffle seed0/1/2，按每model seed的三图分别独立训练保存；实现保存后`summarize-shuffled`命令，fixture以MAE1/2/6验证平均为3，且与MAE(平均预测)明确区分，测试缺项、重复seed、错model seed/data/config/mask拒绝并保留三成员身份。（A08/A13）

## 5. 固定训练、选模、方法与purpose入口

- [x] 5.1 实现统一解析配置与公开`run`入口，显式`--data-name`、`--method self|graph|shuffled`、`--model-seed`、`--shuffle-seed`、`--purpose`、fresh`--run-id`；验证shuffled必需seed且其他方法禁止、开发0/1/2与最终0..4的seed配置、同进程交替调用不改P01全局常量，CLI→worker所有轴完整传递。（A11/A15）
- [x] 5.2 实现200epoch、Adam(lr1e-3,betas0.9/0.999,eps1e-8,weight_decay0)、raw-count均方损失；以完整上下文按窗口/上下文升序分块累积全局19*N*3平均loss梯度、每epoch一次step，无scheduler/early-stop/裁剪。小fixture核对全逻辑batch梯度oracle、元素权重、step/epoch数及三方法相同预算。（A04/A11）
- [x] 5.3 实现每epoch原始单位训练MSE/MAE与更新后验证MSE/MAE记录（明确测量时点）、最低验证MSE选checkpoint、精确平局最早epoch，完整200行history与选择理由；测试验证MAE与MSE冲突只按MSE、仅扰动测试目标不影响训练候选/验证/选择，训练和选择API不接收test标签。（A11）
- [x] 5.4 复用五朴素基线的训练均值/预测/验证MSE/表序平局规则，发布数据确认NaiveRef=LastValue并在不符时失败；fixture仍按自身验证结果选择，用1.1证明数值身份和零参照gain处理不变。（A09/A10）
- [x] 5.5 实现development默认ignored scratch/临时根白名单、resolve/symlink校验、run-id防逃逸、独占不覆盖；仅测试formal解析到research/runs而不执行正式run，测试指向research/runs/其他研究记录/已有归档的覆盖和symlink拒绝、purpose不影响计算配置。（A15/A18）

## 6. 完整产物、只读检查与成本

- [x] 6.1 实现design D9的配置/命令/目的任务、科学与政策版本及内容身份、数据/图/节点身份、执行源码commit/path与必要dirty/untracked内容、环境/线程来源记录；在临时Git fixture验证只捕获运行相关源文件而不包含无关研究改动/测试/缓存，缺身份显式披露，源内容变动失败。（A12）
- [x] 6.2 保存nodes/windows/masks/audit/graph-audit和实际边、validation/test原始预测及gold、五朴素预测、raw-count预处理说明、selected数值参数NPZ、实际参数计数、selection/history与全部metrics；fixture验证allow_pickle=False读取、[1,N,3]/[4,N,3]形状、参数可重载、完整字段及200行记录。（A05/A10/A11/A12）
- [x] 6.3 复用P01 float64指标归约，核对总体/窗口/horizon/上下文/活跃度/常数/邻居/全零组、等权组MAE、负预测比例、节点及元素数、误差贡献、相对参照gain与空组；独立oracle覆盖总体RMSE非窗口均值、月份重复1/2/3/3/2/1、空组null和zero-reference。（A10）
- [x] 6.4 实现`recompute`只读全部保存指标/身份/schema复核，数值normalized容差1e-12且非数值身份精确；禁用源Parquet读、training、forward后测试仍成功，输入前后逐文件字节相同；覆盖改坏key/hash/窗口角色/shape/mask/count/null/非有限值/缺指标的非零失败报告。（A13）
- [x] 6.5 实现`compare`同seed重复检查：严格核对data/graph/两类seed/method/协议政策内容/代码/环境/配置/掩码，计算normalized MAE≤1e-6和逐元素/其他误差指标≤1e-6并保存预测最大绝对差；fixture测试near-zero、超差、各项条件不符即使预测相等仍失败，输入不变。（A14）
- [x] 6.6 统一recompute/compare/summarize-shuffled的单独占JSON报告，包含输入身份、checker代码身份、准确命令、结果/容差/差异；测试已有report、写入input目录、开发report越过scratch/临时根（含symlink）拒绝，有效目标的失败仅保留一份failure report且无附带check-run。（A08/A13/A15）
- [x] 6.7 在新CPU worker实测demand/graph read、shuffle、training/validation、selected inference、输出与总耗时和ru_maxrss；验证Darwin bytes/Linux KiB转换、native值/单位/bytes/方法/作用域/机器CPU/N/E/epoch记录，fixture与真实成本分开标注，不写未测成本承诺。（A17）
- [x] 6.8 实现exclusive目录状态生命周期与失败/中断可用证据，测试碰撞不覆盖、失败阶段及剩余文件保留、interrupted和running遗留识别unfinished；不会由success触发归档/commit/备份/科学接受。（A12/A18）

## 7. 端到端development冒烟与兼容回归

- [x] 7.1 用小型可交换、多上下文、非对称fixture覆盖r0/region/r2 schema×self/graph/shuffled（shuffle0/1/2），完整200epoch CPU端到端；检查身份/掩码/参数量/历史/selected/产物/metrics/成本/成功状态，至少一条每方法走公开CLI→独立worker，禁用GPU/扩展且不依赖全量数据。（A01–A12/A15–A17）
- [x] 7.2 对每方法至少两次同model seed独立CPU fixture执行，逐项只读recompute和repeat compare通过；对同model seed三shuffle成员汇总通过，所有报告在scratch/临时目录；以树快照验证research/runs未新增，检查证据不写研究任务状态或科学收益结论。（A08/A13–A15/A18）
- [x] 7.3 运行`conda run -n job-sdf-baseline python -m unittest discover -s benchmark/graph_value_skeleton/tests -v`；在现有无torch环境执行`python -m unittest discover -s benchmark/nograph_baseline/tests -v`，并对1.1预变更依据检查P01结果/产物兼容；运行旧prepare_graph_data定向fixture测试确认weighted导出不变，记录失败/跳过/环境限制。（A03/A16）
- [x] 7.4 若fixture之外仍有真实发布文件集成/成本疑点，至多执行一次覆盖r0/region/r2的定向development冒烟批次（每组固定model seed、所需方法范围先记入implementation-notes），使用完整200epoch、scratch产物与只读检查；无需真实训练时明确记录未执行及fixture已覆盖项。不得扩成P02-T002的全seed×方法×重复矩阵，不创建正式run。（A01/A02/A09/A15/A17/A18）

## 8. README新入口章节

- [x] 8.1 仅在README新增新包入口章节，列出精确CPU运行时、三方法/两seed轴、200epoch与验证MSE选择、development默认命令、repeat/recompute/summarize-shuffled命令、3seed平均MAE、formal另行授权、发布图时间未知和实现/科学接受区分；对照实际CLI help与fixture执行核对命令，保留现有入口章节与研究文档不改。（A08/A11/A15/A16/A18）

## 9. Implementation-notes与独立核对交接

- [x] 9.1 按apply技能在本change写`implementation-notes.md`，保存完成项/文件、准确命令、环境、fixture/可选真实冒烟输入身份、实测3459参数/成本/重复与重算结果、预变更数值对照和限制；附A01–A18逐条证据索引，未知或未执行项如实说明，不能自签独立verification PASS。（A01–A18）
- [x] 9.2 以只读diff/status核对最终实现编辑范围为新包/其测试依赖文件、README新章节和本change工作流材料；核对无研究记录/协议/旧run/已有归档改写、无正式运行/commit/push/封存/委托指针操作，将核对结果写implementation-notes，不镜像OpenSpec任务checkbox到研究记录。（A18）

后续独立verify、必要fix和archive由用户另行显式触发；不作为apply自签PASS任务。研究侧归档后依design验收清单逐项接受；委托结束依据是归档verification的`Verdict: PASS`且Verification Basis与当前实现一致，研究侧接受和正式研究比较仍为单独动作。
