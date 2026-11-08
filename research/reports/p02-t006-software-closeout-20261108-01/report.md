# P02-T006 软件修复委托回收与研究验收边界

类型：check / handoff。所属任务：P02-T006。
核对日期：2026-11-08，Asia/Shanghai。执行者：本会话研究侧 Codex。
对象：`fix-effective-temporal-training-acceptance` 的归档交付；不执行新的独立软件验证或正式实验。

## 1. 结束判据与适用基准

活跃变更目录已不存在，交付位于 [归档目录](../../../openspec/changes/archive/2026-11-08-fix-effective-temporal-training-acceptance/)。其 [verification.md](../../../openspec/changes/archive/2026-11-08-fix-effective-temporal-training-acceptance/verification.md) 为 `Verdict: PASS`，验证时间为 2026-11-08T12:37:41+08:00，实现基准为 `ca4d5e2949b4376296a6d97d9b916ed05e341bbf`，已包含主规格同步后的验证刷新。

本轮只读核对方法：读取 [verification-state.json](../../../openspec/changes/archive/2026-11-08-fix-effective-temporal-training-acceptance/verification-state.json) 的文件清单，用 Python `hashlib.sha256(Path(...).read_bytes())` 对比当前文件；将其中活跃 change 前缀映射到日期归档前缀，其余路径不变。清单 603 项全部一致，其中 5 项仅有归档路径变化，没有内容差异。清单自身 SHA256 为 `07c08f7f7476cc27c1e599be523b6376a0b33f6a68ccd0a90849557322bdf68f`，与验证报告记录相同。核对前工作树干净；本轮之后的研究记录编辑不改变实现、测试、依赖或科学计算定义，不回写原验证清单。

据此，两条委托结束判据满足，已有独立验证仍适用于当前软件交付。使用已有验证，不重复训练或重跑测试。

## 2. 已交付软件与验证证据

当前入口及契约见 [README §4.7](../../../README.md#47-p02-effective-recurrent-entry-benchmarkmultivariate_time_series) 和 [主规格](../../../openspec/specs/recurrent-forecasting-entry/spec.md)。交付覆盖不可变 best 快照、独立 last 恢复状态、四个滚动测试窗口、训练／选择与测试报告分离、学习有效性诊断、a/b 身份及重复核对、可重算产物、资源／成本控制和原子恢复。

独立报告记录 recurrent suite 129 tests 通过，baseline regression 287 tests 通过、2 skipped；另有资源控制、预算绕过拒绝、离线只读检查等独立边界探针，所有 V-001 至 V-011 均为 verified-resolved。这里引用它们作为软件就绪证据，不把其 synthetic/temporary fixture 结果解释为真实研究结果。

[implementation-notes.md](../../../openspec/changes/archive/2026-11-08-fix-effective-temporal-training-acceptance/implementation-notes.md) 保留最初 apply 交接，其中 revision、诊断输出位置和部分监测描述已过时。使用最终 verification 的修复后判定、当前 README 和实现；尤其 diagnose 现为单个外部独占报告，report 显式接收冻结的 `--diagnostics`，不沿用旧的输入内诊断目录或 latest 指针说明。

## 3. 旧 r0 预实验的限制与可比性

旧运行 [p02-t006-gru-lstm-v2-20261107](../../runs/p02-t006-gru-lstm-v2-20261107/summary.md) 的摘要、指标和原归档保留不变。旧实现的 best CPU 张量未 clone，后续更新可能改变所保存权重；测试仅使用起点 27，没有覆盖主协议 24..27；学习有效性和完整 a/b 证据未由旧交付建立。

可比性结论：**不能将旧指标作为修复后完整协议的正式对照或同条件重复证据**。旧结果只能定位为历史 r0 预实验，不能据此认定 GRU 已有效学习、LSTM 更优、三粒度任务完成或 T007 的前置门槛通过。本轮没有回收原 Windows checkpoint、重算旧指标或生成替代数值；本机旧 run 的完整数组／权重未核验。

软件修复不改变科学版本 `P2-effective-training-L6-H3-v1`，但改变实际执行与产物格式；后续真实实验须使用新执行身份，不能覆盖旧 run 或伪装成原轨迹继续训练。

## 4. 尚未完成的研究工作与下一动作

当前交付没有真实数据新运行。T006 仍需按 [P02 协议](../../phases/P02/protocol.md) 分块执行和研究侧验收；具体状态与接受决定见 [P02 计划](../../phases/P02/plan.md) 和 [D039](../../decisions.md#d039-t006-软件修复研究侧验收与完成状态纠正)。不得以本次软件 PASS 自动放行 T007。

下一可执行动作是准备首个 r0/GRU 执行块的精确指导与输入清单，而非直接启动训练。前置条件如下：

- 明确执行机器及 CPU 依赖环境，提供实际 demand、节点／月份身份及兼容的 Ridge 验证记录。原始 graph 或身份对齐 mask 用于邻居分组；缺失应明确记录，不能把 unavailable 视为完整分组证据。
- 选择新的 run／block／batch ID 和持久化 ledger，厘清已有消耗的计费范围；先按真实环境预检，再在授权启动后取得首个候选的成本样本，不能使用 fixture 时间预测真实成本。
- 后续范围沿用 `r0 → region → r2`、每组 `GRU → LSTM`；每块两个 seed-0 学习率候选，赢家复用为 a，再做 a 的 seeds 1/2 和 b 的 seeds 0/1/2。逐块按协议成本门放行，不预先自动排满矩阵。
- 冻结选择并通过验证期诊断后才生成四窗口测试报告，之后做保存材料的 recompute 和 a/b compare；失败或成本超限保留诊断和恢复位置，不扩搜索或放宽门槛。

上述内容是后续研究执行的范围与条件，不是本轮启动正式实验的授权。本轮不启动设备、不安装依赖、不跑真实训练、不改 T009，也不 commit/push。保存事实见 [索引](../../archives/index.md#p02-t006-软件修复交付与旧预实验限制2026-11-08)。

## 5. 核验范围

已核对归档判据、已有验证报告与文件身份；软件行为测试直接复用适用的独立证据。真实设备内存／磁盘是否达标、实际训练成本、原生 Windows 执行及真实 `learning_ready` 未在本轮核验。live saved-stage 的取消发生于有界操作间，原生文件／数组操作完成后才到下一检查点；该限制已由独立报告和 README 披露。
