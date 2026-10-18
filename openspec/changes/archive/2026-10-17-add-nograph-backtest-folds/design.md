## Context

动机见 [proposal.md](proposal.md)。规范来源为 T007 指导 §2–§5、协议 §3–§6/§8；科学版本 `P1-count-L6-H3-v3`、保存政策 `P01-records-v2` 不变。本工作流不读写委托指针，委托归属 P01-T007 由用户明确提供。

已读实现的约束：

- `protocol.py` 的 `SPLITS`、`OMITTED_STARTS`、`TRAIN_OBSERVATION_MONTH_COUNT`、方法列表和校验均固定主切分；`expected_train_sample_count()` 固定 19*N。
- `ridge.TrainingStats`、`compute_training_stats()` 和 `baselines.train_mean27()` 固定前 27 月；朴素均值保留 float32 累加以对齐既有结果，Ridge 标准化使用 float64。
- `runner.RunSpec` 经 CLI → JSON worker 传递；`execute_run()` 及掩码/模型/summary 写出逻辑固定 validation/test、TrainMean27 和 train27 字段。目前评估设计与标签在选模前已构造，但未传入选择器；折路径将延迟 eval 目标材料到选择冻结之后。
- `data.build_audit()` 的顶层和 per-context 均含 27 月诊断；`metrics.constant_group_masks()`、`node_error_table()` 和默认活跃度名称也携带主协议假设，不能只改 runner。
- `checks.py` 从保存材料重算，校验指标 schema、null/空组、节点表、来源与环境；但 consumed-input 列表、预测循环、均值路径和节点表重算固定 test/TrainMean27。`compare` 已校验数据、seed、后端、协议文件身份等，需要保留这些校验并增加明确 fold 身份。
- 当前规范 `nograph-baseline-entry` 将多项行为无条件写成主切分，因此 delta 修改这些完整 requirement，保留既有场景并加折场景；不用新 capability 回避旧规范冲突。

## Goals / Non-Goals

**Goals:**

- 用同一切分描述驱动计算、命名、序列化和复核，避免相同折在多个模块被重新推导。
- 主切分内部也可使用描述对象，但对外保持原文件集合、JSON 字段、NPZ 键、Parquet 列、数值和旧 run 读取路径；折字段仅在折路径写出。
- 保留足够保存状态，使 checker 不依赖源 Parquet、当前工作区数据或重训。

**Non-Goals:**

- 不开放任意月份或自定义切分；不增加 purpose、科学版本、模型族或图预测路径。
- 不把 27 月/36 月描述性审计或邻居注释变为回测时可用的预测特征；邻居覆盖仍只是披露来源与时间限制的评估注释。
- 不维护研究任务状态、委托回收、实验收益报告或正式运行。唯一计划中的研究目录文档编辑是用户点名的执行指导 §7 入口说明，不扩展到 state/plan/decisions/index/协议正文。

## Decisions

### 1. 固定、不可变的 split definition

在 `protocol.py` 定义一个不可变切分描述及解析函数，包含 fold（内部 main/A/B）、拟合月份、split 起点、评估 split 名、省略原因、outside_fold 起点和方法顺序。沿用原常量与默认公共函数的主切分语义，必要时增加可选参数/兼容包装；禁止通过修改模块全局常量切换折，以支持同一进程交替运行 main/A/B。

| 描述 | 拟合月数 | train | validation | 输出评估 split / 起点 | omitted（原因依次为训练边界、验证边界、评估重叠） | outside_fold |
| --- | --- | --- | --- | --- | --- | --- |
| main | 27 | 0..18 | 21 | test / 24..27 | 19,20；22,23（维持原格式） | 无 |
| A | 18 | 0..9 | 12 | eval / 15 | 10,11；13,14；16,17 | 18..27 |
| B | 21 | 0..12 | 15 | eval / 18 | 13,14；16,17；19,20 | 21..27 |

固定原因代码建议为 `train_validation_target_overlap`、`validation_eval_target_overlap`、`overlaps_eval_targets`；outside_fold 与 omitted 分开。折 `windows.json` 给 0..27 每项加 role 和 reason，保留 input_months/target_months/forecast_origin。列出后期窗口的月份元数据不等于构造其标签或运行预测。

校验同时覆盖：精确起点与月份、全部 28 个角色互斥且穷尽、拟合期从 2021-01 开始且包含完整训练输入/目标、train/validation/eval 目标两两不交、省略原因与枚举一致。代码校验用于程序入口和保存元数据读取；不只在 argparse 中检查。

选择显式 `--fold {A,B}`，缺省内部解析 main；`RunSpec` 增加可选 fold，worker 完整传递。主切分 `to_dict()` 等输出省略新增空 fold 字段，避免 `asdict()` 无条件新增字段导致兼容回归。旧输入缺 fold 时解析为 main；未知显式值立即失败。

替代方案：只在 CLI 替换常量容易串折且不能保护程序入口；另写回测脚本会复制选模/保存逻辑，现有 checker 仍无法复核，均不采用。

### 2. 折内冻结统计与选模

`compute_training_stats()` 接收解析后的拟合范围，返回该范围的均值、原始/有效标准差、常数掩码、activity、掩码及月数身份。原 `train_mean27()` 与默认字段访问保留兼容入口；新增通用拟合均值路径，折内 float32 TrainMean 与 float64 标准化的算术延续现有实现。

先从唯一的前 18/21 月计算统计，再只用 train 起点构造训练样本；样本数 A 为 10*N，B 为 13*N。输入和目标共用统计；常数判定为原始 std==0，有效 std=1。activity 为同一范围的 `(demand > 0).mean()`，使用原四组边界。

折内方法顺序是 Zero、LastValue、WindowMean6、TrainMean18/21、SeasonalNaive12；NaiveRef6 排除最后一项。SeasonalNaive12 只用于验证/评估预测，使用每个目标月 t-12 的已知历史，不对早期训练窗口强行生成季节预测。

沿用 Ridge 候选 `1e-4,1e-3,1e-2,1e-1,1`、截距不正则化和 `alpha=lambda*M`。先完成所有候选验证分数并冻结两种参照与 lambda，再构造/评估 eval 标签和预测；eval 目标不进入拟合/选择接口。输入允许使用此前已发生的训练或验证目标月。保留非负裁剪和候选保留选项的既有语义。

替代方案：沿用 27 月统计或先拟合主模型再截预测不满足折重拟合；按训练窗口重复计数或仅训练目标拟合会改变协议，均排除。

### 3. 折产物扩展，主产物原样序列化

fold 分支使用统一的折身份载荷，在 config/provenance 中一致记录 fold、拟合月份/count、train/validation/eval 起点、omitted+reason、outside_fold、eval 目标月份和 `evidence_role=development_backtest`。purpose 仍为 formal/development；development 的科学接受标记保持 false，evidence_role 不能把冒烟变成科研证据。

| 保存位置 | 折路径规划 |
| --- | --- |
| `selection.json` | normalization 拟合月份；拟合月数和 TrainMean 名称；五项朴素验证 MSE；NaiveRef/NaiveRef6 分数表、并列项和文字/结构化选择理由；Ridge 全候选 MSE/MAE、选中理由、M/alpha；`test_labels_used_for_selection=false` |
| `models/TrainMean18.npz` / `TrainMean21.npz` | 对应 `train_mean18` / `train_mean21` 数组和实际拟合月数；不以 TrainMean27 作为折产物别名 |
| `models/SharedRidge.npz` | 沿用选中 W/b、预处理统计和 scalar 结构，记录真实 M；折月份身份由关联元数据定位 |
| `masks.npz` | `nonzero_activity_fit18`、`activity_fit18_inactive/low/medium/high`、`constant_fit18`，B 替换 fit21；邻居掩码定义不变 |
| `metrics.json` | `methods.validation` / `methods.eval`；分组键 `fit18_inactive` 等，常数组 `constant_fit18` / `nonconstant_fit18`；等权组名称列表及全零组指向同名折组；对应 relative_gains；真实折聚合说明 |
| `node-errors.parquet` | 保留键/误差列，折均值列 `train_mean18/21`、activity 列 `activity_fit18/21`、组列 `activity_group_fit18/21`、常数列 `constant_fit18/21`；仍按拟合均值降序和规范键稳定排序 |
| `predictions/<method>/` 与 `gold/` | 仅 `validation.npy`、`eval.npy`，形状各 `[1,N,3]`；主 split 继续 `[1,N,3]` 与 `[4,N,3]` 的 validation/test |
| `audit.json` | 折内 `fit18` / `fit21` 统计单列；保留的旧审计整体放在 `main_protocol_diagnostics` 命名空间，标明 27 月范围与 descriptive_only（含嵌套 per-context），原 36 月诊断标签继续明确 |

`metrics.py` 的分组、等权平均、全零组引用、相对收益和节点表必须接收一致的折组名/统计，不能只替换 mask 键而仍查询 `inactive` 导致漏组。保留空组/null/零参照的原语义；总体 RMSE 始终是所有评估元素平方误差均值的平方根。

不强制新增全局 run schema 或重写旧 run。main 分支保留现有 audit 原结构、TrainMean27、train27 掩码/节点列、test 文件及既有 JSON 字段，不增加 fold/eval 空字段。summary、measurements 的描述也要反映实际 split，不能遗漏其 test 固定文案。`artifacts.py` 的非覆盖、来源捕获和序列化通道继续复用，仅确需时调整来源包含范围，不改归档工具。

替代方案：统一把所有旧产物改成 generic fit/test/eval 命名会破坏旧字段；采用仅折扩展，接受少量兼容分支以保留既有下游读取能力。

### 4. 保存材料解析与检查器

在检查器中集中解析保存的切分身份，核对 config、provenance、windows、selection/metrics 的折信息和方法/掩码范围；缺少 fold 的历史主切分仅在窗口/格式确认为 main 时允许兼容读取。任何显式折或 eval 痕迹存在而信息缺失/冲突时失败，不能静默推断 main 或信任单一文件。

- recompute 根据保存身份解析两个输出 split、拟合均值路径、group/mask 名称和节点表列，读保存的预测/标签/键/掩码/均值，重算全部指标、收益与节点表。报告 consumed-input 身份列表随实际读取而变，包含折元数据；沿用 schema/null/非有限/误差容差检查。通过禁用源数据 loader 和 fit 函数的测试证明保存材料充分。
- compare 在读取身份后显式报告 dataset、demand content、fold、seed 一致性，A/B/main 的 fold 不同直接失败；继续检查已有配置、协议文件身份、coverage、节点、环境、选模及掩码等，不能仅凭版本字符串相同放宽。比较 validation 和实际评估 split，方法集合必须一致，不能只取交集掩盖缺失。相对 MAE `abs(a-b)/max(1,a,b)<=1e-6`，并保留原预测/其他指标容差与最大绝对差。
- align-v2 解析 run 身份后优先拒绝 A/B，明确“v2 参考没有 fold 记录”，不访问虚构 eval→test 映射；合法 report 目的地仍产生单一失败 JSON 和非零退出。主切分原数据记录缺失/limited/成功行为不变。

全部检查沿用现有 exclusive report、输入不修改、禁止 report 写入输入 run 和旧参数别名规则。测试验证输入树前后身份一致，不调用封存或恢复工具。

替代方案：从文件名猜折会接受不一致产物；用当前全局主常量重建保存 run 会失去执行时身份，均不采用。

### 5. 有限测试矩阵与证据边界

开始实现前，在临时目录以当前代码和确定性小 fixture 保存主切分参考契约（r0/region/r2），随后对同输入无 fold 调用比较文件集合、JSON schema、NPZ 键/dtype、节点表 schema、预测、分组、选择与指标；执行身份、耗时、来源 patch 等自然变化字段只排除其值，不排除其字段。也可补独立数值 oracle，避免修改后实现同时充当预期值。

单元测试覆盖 A/B 的精确窗口和负例校验、唯一拟合月统计、常数节点和边界 activity（A 用 0/6/12/18 个活跃月，B 用 0/7/14/21）、TrainMean 命名、验证 MSE 与 lambda/朴素平局。信息隔离分开测试：改所有拟合后值只要求统计与候选训练参数不变；仅改 eval 目标才要求验证分数和选择也不变，避免把允许的验证选模判成泄漏。

小型 fixture 端到端至少覆盖 A/B × 三种节点键，公开 CLI/worker 对 A/B 各跑一次 development；同折同数据同 seed 的重复与 recompute 正例，A/B/main、数据名、同名不同源内容、seed 不同的 compare 负例；align-v2 两折拒绝（含伪造参考），以及缺失/冲突折元数据、损坏掩码或节点分组列的重算失败。所有新增运行使用临时 fixture 和 `--purpose development`，输出/报告留在临时或忽略 scratch 路径；现有测试中的临时 schema 样例不构成正式实验。

后续 apply 的实现说明保存在 change 目录，记录命令、环境、fixture 身份、结果和限制。独立 verify 另行运行并记录当前实现的 Verification Basis；不得由 apply 自签 PASS。本轮不创建 verification 或实现报告。再后的归档与研究侧回收各由其相应工作流处理；当前请求不授权执行这些步骤。

## Risks / Trade-offs

- [main 字段被 dataclass/通用 writer 无意新增或改名] → 主切分参考契约先固定，fold-only 序列化分支，保留旧公共默认行为与全套测试。
- [折掩码正确但指标仍查询旧组名，或节点表重算仍读 TrainMean27] → 一个描述贯穿组名/均值路径，端到端对分组数、全零组、收益、节点表与 consumed-input 清单核对。
- [读全 36 月数据的审计被误当历史可用信息] → 27/36 月诊断显式隔离，绝不参与预测、统计或选模；只做主测试月份元数据枚举，不计算主测试结果。
- [邻居注释的发布图时间未知被解读为历史图证据] → 沿用仅评估注释和来源披露，预测仍完全无图，不增加严格历史图可用性主张。
- [旧 run 缺 fold 与损坏 fold 被混同] → 只对一致的 main 结构做缺省兼容，显式折线索冲突即失败。
- [测试产生科研输出或被解释成 T007 完成] → development/临时 fixture 路径限制，记录实现就绪证据；正式实验、保存和研究验收另行授权。

## Migration Plan

先固定 main 回归材料，再逐层接入切分描述、折统计/选模、保存与检查器，最后更新两处入口说明并执行 fixture/主切分回归。旧 run 不迁移，主规范仅在后续明确归档流程中同步。若实现验证失败，按 OpenSpec repair 流程修复当前变更，不修改既有证据以强行通过；不运行正式实验作为部署步骤。
