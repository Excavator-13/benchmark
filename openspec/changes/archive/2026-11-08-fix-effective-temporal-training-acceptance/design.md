## Context

动机见 [proposal.md](proposal.md)。当前 260 行入口的关键位置为：`train()` 同时接收 36 月数组、训练和测试；`best` 对 CPU state_dict 只做 detach/cpu；测试构造 `make_windows(arr,27,1)`；`load_checkpoint()` 只检查版本并加载权重；`compare()` 丢失实际 source 参数。现有三个测试覆盖 RMS、训练窗口和 checkpoint 可加载性，没有验证“最佳轮早于末轮”、四测试窗口、同条件重复或恢复等价性。

可复用基础包括 `benchmark/nograph_baseline/data.py` 的 `load_demand`／`from_arrays` 和规范键、`protocol.py` 的 MAIN_SPLIT／月份、`metrics.py` 的 `[windows,nodes,horizon]` 归约、`baselines.py` 的五项朴素参照及 `coverage.py` 的带身份覆盖掩码。它们使用 P01 条件；只复用兼容的数据／主切分／评价逻辑，神经模型采用 P02 RMS，不调用旧 runner 取得逐节点缩放后的神经输入。现有 checks 读取 baseline 专属产物格式，不能把神经结果冒充其格式直接传入。

主规格尚无 `recurrent-forecasting-entry`，但旧归档已有同名 delta。本变更以 ADDED 建立同名 capability 并保留原核心契约，同时补齐已存在研究协议的软件支持；不修订科学协议。

## Goals / Non-Goals

**Goals:** 将选择权重、恢复状态、验证诊断和测试报告组成可以分别复核的软件接口；让未来研究执行者能够获得完整协议证据。规格中的每个门槛和停止行为都可由小型 fixture／注入的时间与资源信号验证。

**Non-Goals:** 真实数据训练、机器实时成本校准、重算原 Windows 结果、修订 T006 状态或验收旧实验；图传播、alpha 搜索、T009 和新研究路线；把某个测试成绩写成新的科学结论。独立验证的 PASS 只描述软件，不要求 fixture 学会真实任务。

## Decisions

### 1. 保留模块入口，分离执行阶段

保留 `python -m benchmark.multivariate_time_series.effective_temporal_training`，新增明确的 `preflight`、`fit`、`select`、`diagnose`、`report`、`recompute`、`compare`、`resume` 操作。将训练核心、产物／检查、资源控制拆到相邻专用模块，避免把旧 `train(values36)` 扩成隐式全流程。旧调用方式给出迁移错误和帮助；不保留自动训练后立即测试的兼容路径。

数据适配层验证完整表后，向 fit 只传训练历史和验证输入／目标；测试数组只在 report 路径构造。select 只读两个 seed-0 候选分数并产出冻结的 selection.json，记录相同初始化身份及胜出轨迹。a/b 用独立执行 ID、repeat role 和共享 condition ID 表达；seed-0 的候选胜者通过链接复用为 a，不复制为第二次拟合。命令一次只执行明确指定的轨迹或检查，不实现自动跑完 r0→region→r2 的控制器。

report 在 formal 模式先验证 selection 与完整 validation diagnose 记录，绑定它们的内容身份，再读测试数据、恢复所选模型并写四窗口报告。development 可用短轨迹验证报告路径，但必须标明协议不完整、不能生成 formal-ready 结论。采用结构分离，优于仅记录 `test_labels_used=false` 而仍把测试标签传进 train 的方式。

### 2. 深复制 best，单独保存 last

最佳模型张量显式 clone，优化器状态完整深复制，验证精确平局不更新 best。初始化分数只供诊断。保存 best 时绑定 epoch、step、所选验证分数与预处理，并在加载后重新评分核对。last 是每个完整 epoch 的真实末态，包含继续训练需要的模型／优化器、Python/NumPy/torch RNG、history、下一窗口=0、已完成步数、best 副本与累计成本引用，不能拿 best 冒充 last。

同目录临时写入、flush/fsync 后原子替换 last checkpoint；写失败保留前一完整版本。恢复在新输出目录建立 parent 链，验证数据、源码、协议内容、环境、有效配置和预算一致，恢复最后完整轮。轮内中断会重放部分计算，ledger 计入已耗费及重放时间。新格式标记 `artifact_format_version=2`，旧无格式 checkpoint 不得自动升级为可恢复状态。测试比较中断恢复与不间断轨迹，而不只检查能否 load_state_dict。

### 3. 复用规范数据和评价，显式冻结比较条件

用 baseline 数据适配器保留 `(context_id,skill_id)` 与 36 月身份；MAIN_SPLIT 供应 starts／月历。梯度 chunk 依规范上下文顺序，不跨上下文拼接来隐含定义后续图训练规则；自身模型仍累积全部节点后一次 step。神经参数固定为协议定义，RMS float64、模型 float32、指标 float64。

预测／标签统一 `[W,N,3]`，测试 W=4。复用纯指标与固定分组、覆盖注释辅助函数；Coverage 来源或注入 mask 必须与节点键及数据集一致，不能默认全部孤立。五个朴素参照可在验证数据计算；Ridge 使用显式提供、经身份检查的已有 baseline 结果和验证选择记录，或在未来研究授权下由既有 baseline 入口另行生成。本 change 不增加另一套 Ridge 搜索。神经 RMS 与 Ridge 原协议逐节点标准化分别记录，兼容性判定针对各自正确条件，不要求二者使用同一预处理。

### 4. 诊断是可重算数据，研究验收是另一动作

保存 step0、10/50/100 及 best 的固定参数训练／验证分数和全部验证历史。在线 train_loss 明确标 mixed-parameter。诊断按现有 §5 精确计算阈值，对每个 gate 输出所用字段、分母处理、per-seed 与汇总状态；缺失记录为 incomplete，不能靠 test 补齐。初始化零 MSE 的相对降低不可定义，保留 unavailable，不宣称降低达标。所有 seed 的有限性、覆盖与 a/b 身份先检查；b 不进入配置搜索和初始化方差。

输入／目标分位数、隐输出饱和、负预测／输出尺度、输入置零变化是诊断附表；饱和检查对 GRU/LSTM 的输出隐状态使用同一定义，不把 LSTM cell state 当输出。LastValue/Zero/Ridge 验证分数连同兼容性证据进入附表。输出的 `learning_ready` 是软件按冻结协议计算的状态，不能更改 phase plan 或替代研究侧接受。

### 5. 小型入口入库约定不等于完整产物已交付

每个新执行保存 `provenance.json`、`command.json`、`report.json`、`summary.md` 作为现有忽略政策允许的可读入口，其余 JSON／数组／checkpoint 留在完整执行目录。provenance 捕获此入口及实际使用的辅助源码、相关差异和协议内容身份，避免套用只捕获 baseline runtime 的固定 allowlist；comparison 逐 seed 传递实际 demand 身份。

完整目录包含 config/selection/windows/history/diagnostics/preflight/cost/status、keys/months/masks、validation 和 test 的 gold/prediction、selected 与 recovery 权重及关联 baseline 身份。格式清单明确哪些文件参与重算、重复比较或恢复。数值数组使用无对象 NPY/NPZ；检查不加载模型 checkpoint，也不要求 torch 才能重算指标。现有 baseline checks 的只读、独占单 JSON 报告模式可借鉴，但新增神经格式适配器，不能放宽 baseline checks 的校验。

recompute/compare/diagnose 从保存材料生成紧凑报告，不再读 demand/graph 或重训；失败保留可用报告。比较先检查同条件身份，再比数值；验证与报告后的测试分别核对 a/b。输出与输入隔离，使用 exclusive create，路径先 resolve 后检查命名空间。完整 checkpoint 和数组实际交付、封存或备份由研究侧决定，本 change 不新建逐 run 忽略例外。

### 6. 控制器监测资源，训练核心可注入时钟

使用此入口专用依赖声明提供 psutil，控制层启动一个 CPU worker，启动前设置 BLAS／torch 线程和确定性选项；进程树采样支持 Windows 与 macOS。preflight 用排他锁／PID 身份校验避免相同执行根并发控制器，记录其他可识别冲突，监测无法建立则不放行。初始化检查内存／磁盘，运行中独立 watchdog 每 <=5 s 采 RSS 和活跃时间，不能只在 epoch 末检查。

持久化 batch ledger 绑定单独 batch ID，不把暂停期间无进程的等待时间计入 active time，也不因新 child execution 清零。按协议用完整 epoch 6..10 中位数 t 计算 `1.3*(setup + 2*100*t)` 的保守单拟合界，再与剩余拟合次数和累计已用时间核对。10 轮样本保留同一模型轨迹；放行后继续 11..100，暂停可从完整轮恢复。每个 dataset×model 独立测量，预算和停止线严格沿用协议。估计值与测得值分字段。

测试用可注入 clock/sampler 和小型 worker 验证超时／RSS／监测失败／发布失败／恢复预算，不靠真占满内存或长时间等待制造超限。实现会提供资源能力，本轮不测真实设备是否满足它。

### 7. 软件验证与研究交接分开

测试使用临时小型 r0/region/r2 Parquet 和合成数组；受控分数／历史验证每个门槛，不强求随机合成任务达到真实 `learning_ready`。CPU smoke 可短预算运行，标 development。核心回归包括 CPU best 别名、四测试窗口、测试访问哨兵、非均匀 chunk 更新、全部有效性阈值、来源传递、保存后重算、身份拒绝、原子恢复与资源失败。相关既有 baseline 测试用于确认辅助接口复用未改变旧行为，不重跑历史实验。

README 增加本入口的专用环境、准确命令和格式迁移说明，并在 change 的实现交接中列出研究侧接手所需材料及仍未知的真实设备／成本。apply 不写科研计划、协议、决定、索引或委托指针；verify 独立检查软件证据。研究侧后续核对 current-basis 归档 PASS 后，自行决定研究状态修订、正式运行范围和接受与否。

## Risks / Trade-offs

- [软件支持范围大于两个局部 bug] → 完整协议的软件缺口已有明确证据，按数据、选择、诊断、产物、资源分步实现；验收只依小型 fixture，不搭建通用实验调度平台。
- [旧归档有 PASS，主规格却缺失] → 以同名 ADDED 补齐，并在软件验证说明旧 PASS 的覆盖边界；保留历史归档原字节。
- [数据 loader 的完整性审计可读取全部月份] → 允许适配器检查数据合法性，但训练／选择接口不接收测试标签，测试值不得影响筛选或配置；用访问哨兵和测试值扰动回归验证。
- [跨平台监测和依赖版本不同] → 版本／测量方法进入环境身份，监测失败暂停；a/b 不跨环境冒充重复。
- [完整 arrays/checkpoint 不随现有 Git 忽略政策自动同步] → provenance/summary 列明确切位置与必需文件；研究侧另行交付和记录保存事实，不把 Git 中有摘要当完整证据。
- [真实任务可能仍未达到有效性门槛] → 软件就绪不承诺研究通过，不增加搜索预算或更改门槛。

## Migration Plan

1. 在新实现与格式中修复入口，用 fixture 验证并记录格式／源码身份；不给旧结果回填新指标。
2. 文档明确旧自动 train/test 命令迁移到分阶段操作，拒绝无必要状态的旧 checkpoint 恢复；保留旧材料只读。
3. 独立验证后按 OpenSpec 流程归档／同步新 capability；不改原归档。研究侧接手时单独处理旧 r0 结果局限、T006 的 done 冲突和正式执行授权。
4. 若回退软件，依 Git 回退实现及文档；新格式产物保持原身份，不降级解释为旧格式或覆盖旧 run。
