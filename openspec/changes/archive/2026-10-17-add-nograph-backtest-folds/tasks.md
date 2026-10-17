## 1. 固定默认主切分回归依据

- [x] 1.1 在改计算代码前，用确定性小 fixture 为 r0/region/r2 各保存一次无 fold 的 development 主切分参考契约到临时目录；核对文件集合、JSON 字段、NPZ 键/dtype、Parquet 列、选模、预测与指标，记录命令和自然变化字段的值排除清单，产出后续回归可用的预变更依据。

## 2. 固定折描述、代码校验与入口

- [x] 2.1 在 `protocol.py` 增加不可变 main/A/B 切分描述、解析函数及默认兼容包装；用 `tests/test_protocol.py` 验证 A 的 fit18/train 0..9/validation 12/eval 15、B 的 fit21/train 0..12/validation 15/eval 18，以及原主常量与默认调用不变。
- [x] 2.2 实现精确起点、拟合观察期、目标月份两两隔离、omitted 原因与 outside_fold 的代码校验及全部 28 个窗口角色/月份元数据；测试逐项枚举、省略集合 A=10,11,13,14,16,17 与 B=13,14,16,17,19,20，修改起点/拟合范围/原因/角色或制造重叠时均失败，并允许合法历史目标作输入。
- [x] 2.3 在 `cli.py` 和 `runner.RunSpec`/worker 配置通道增加 `--fold {A,B}`；测试公开 parser、程序入口和 worker 的 A/B 传递、未知值在预留目录前失败、缺省 main 序列化不新增空 fold 字段，以及同进程 main/A/B 交替调用不串状态。

## 3. 折内统计、朴素基线与 Ridge

- [x] 3.1 参数化 `ridge.py` 的唯一拟合月统计并保留默认 27 月兼容入口；以独立数组 oracle 验证 A 前 18/B 前 21 月的 mean/std(ddof=0)、常数 effective_std=1、输入/目标共用统计、activity 边界及掩码分区，且修改拟合后值不改变统计或训练设计。
- [x] 3.2 在 `baselines.py` 实现按拟合月数冻结的均值和动态方法顺序，保留 TrainMean27 的默认 float32 算术；测试 TrainMean18/TrainMean21 名称/数值、五方法预测、SeasonalNaive12 的 t-12 历史、NaiveRef6 候选排除和朴素验证 MSE 精确平局按表顺序。
- [x] 3.3 将 `runner.py` 的训练/验证设计和 Ridge 适配到切分描述，以实际窗口数计算 M；测试 A=10*N、B=13*N、全部五个 lambda 的原始单位验证分数、平局取较大 lambda 与 `alpha=lambda*M`，并保留现有后端和裁剪语义。
- [x] 3.4 将折 eval 目标构造与模型评估置于折内参照/lambda 选择冻结之后；测试仅扰动 eval 目标不改变候选参数、验证分数、lambda 或 NaiveRef/NaiveRef6；扰动所有拟合后值时只要求统计与训练参数不变，允许验证驱动选择变化。

## 4. 折产物、指标和审计

- [x] 4.1 在 config/provenance/windows 写入一致的折载荷与全部 28 个角色，selection 写入拟合期、TrainMean 名、五项验证 MSE、两种参照的理由、完整 Ridge 候选分数/理由及 `test_labels_used_for_selection=false`；fixture 断言字段与 A/B 月份完全一致，含省略原因与 eval 目标月份。
- [x] 4.2 写出 `models/TrainMean18.npz` / `TrainMean21.npz`、实际拟合统计、`activity_fit18_*` / `activity_fit21_*`、`nonzero_activity_fit18/21` 和 `constant_fit18/21` 掩码；测试无 pickle 加载、节点身份对齐，且 fold 文件/键不冒用 TrainMean27/train27。
- [x] 4.3 参数化 `metrics.py` 的组名、常数组、全零组引用、等权 MAE 和相对收益；以 fixture/oracle 核对 validation/eval 两个 split 的总体 MAE/MSE/RMSE、逐窗口/horizon/上下文/活跃度/常数/邻居组、样本计数、误差贡献、负预测比例和 eval 对两个冻结参照的收益，包括空组、零参照及 fit18/fit21 名称。
- [x] 4.4 扩展节点误差表的拟合均值、activity/group/constant 列和稳定排序，折 audit 显式区分 fit18/fit21 与主 27 月诊断的顶层/嵌套来源范围；测试一个折内/27 月状态不同的节点，节点表、掩码和指标一致，27/36 月诊断不参与分组或选模。
- [x] 4.5 统一写出 validation/eval 的预测和 gold，更新 summary、聚合说明和 measurements 的 split 描述；A/B fixture 验证各数组形状 `[1,N,3]`、所有六种方法及可选裁剪产物，且不存在 test split/文件或主测试期计算，窗口月份元数据仍完整。
- [x] 4.6 保持两种 purpose 的存储规则并给折元数据标记 development_backtest；通过输出根解析/序列化的单元测试验证 formal 默认 research/runs、development 在临时/忽略路径且拒绝 formal 命名空间（含 symlink），不启动正式 fold run，也不增加第三种 purpose。

## 5. 保存产物检查与旧格式兼容

- [x] 5.1 在 `checks.py` 集中解析并交叉验证保存的 fold/拟合期/窗口/方法/掩码身份，按实际消费材料记录报告输入身份；测试一致 main 无 fold 字段可读，未知/缺失/冲突折标签、错误拟合月数或窗口不能回退 main。
- [x] 5.2 参数化 recompute 的 split、均值路径、掩码、收益和节点表重算；对 A/B 保存 fixture 禁用源需求/图读取和训练函数后重算全部指标/收益/节点表仍通过，并确认报告标记实际读取的 fold 数组、均值和元数据。
- [x] 5.3 扩展 compare 的显式 fold 身份与动态 split/method 检查并保留既有来源/协议文件/环境/coverage/seed/选择条件；A/B 各用两个同数据同 seed 的 development run 验证正例、预测最大绝对差和 CPU 相对 MAE <=1e-6，方法缺失不能被集合交集掩盖。
- [x] 5.4 增加 compare 负例：A 对 B、main 对 fold、不同 dataset、同 dataset 不同需求内容身份、不同 seed；验证每项非零返回且 failure report 指出对应身份差异，即使预测相同也拒绝。
- [x] 5.5 align-v2 优先识别并拒绝两种 fold；用正常 main 参考和伪造 fold 参考验证均非零返回且说明 v2 没有折记录，不生成 eval→test 映射，不改参考或 run，并保留 main 的既有成功/缺记录/limited 行为。
- [x] 5.6 对 fold 检查覆盖损坏/缺失数组、掩码、节点分组列、元数据冲突和 report 目的地冲突；验证有效目的地只写一份独占失败 JSON、旧 report 参数别名仍可用，输入目录逐文件身份前后不变，无源数据读取/重训或附带 check run。

## 6. 端到端与主切分集成回归

- [x] 6.1 用小型临时 fixture 覆盖 A/B × r0/region/r2 端到端保存契约，公开 CLI/worker 对 A/B 各完成一次 `--purpose development` 冒烟；核对规范节点键、全产物、选模、fit18/fit21 分组、validation/eval 命名和 succeeded 状态，输出/报告均不写 research/runs。
- [x] 6.2 对三种数据 schema 的无 fold development 调用与 1.1 的预变更依据比较，验证文件/字段/列/NPZ 键完全保留、预测/选模/指标符合既有数值容差，仍使用 TrainMean27/train27 和 validation/test；另用临时旧 main schema 验证 recompute/compare/align-v2 兼容，不修改旧 run 或调用封存/恢复工具。
- [x] 6.3 执行完整 CPU 测试 `python -m unittest discover -s benchmark/nograph_baseline/tests -v` 及必要定向 development 冒烟，汇总失败/跳过/依赖限制；验证现有与新增用例通过且没有新图/GPU/必需 sklearn 依赖，不运行任何正式 fold 实验。

## 7. 文档与独立验证交接

- [x] 7.1 更新 `README.md` §4.5 和 `research/phases/P01/execution-guide.md` §7 的折入口说明，给出 A/B development 命令、拟合范围、eval 命名、formal 的输出及 development_backtest 语义、recompute/compare/align-v2 行为；核对命令与 CLI help 一致，并明确正式运行/保存另行授权、旧主入口不变。
- [x] 7.2 按 apply 工作流在 change 目录保存实现说明：完成项与具体文件、验证命令/环境/fixture 身份、结果及限制，附主切分预变更对照证据；核对只编辑获准代码/测试与两处入口文档，不读写 DELEGATION、不维护研究状态、不 commit/push/封存/恢复、不镜像 tasks 进度到研究记录。

后续独立 verify、必要 fix 和 archive 按用户分别触发的 OpenSpec 工作流处理，不作为 apply 自行签发 PASS 的任务。委托结束判据是活跃变更已归档、归档 verification 的 `Verdict: PASS` 且 Verification Basis 与当前实现一致；这只提供实现就绪证据，研究侧另行接受并回收委托，正式实验与 T007 验收均不在本清单内。
