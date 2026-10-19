# T002 发布图打乱预算修复交接

2026-10-19。研究任务 P02-T002。此文件为研究侧交接材料，不是 OpenSpec proposal，不登记已启动委托；[DELEGATION](../../../DELEGATION.md) 仍为 `closed`。

## 已确认问题

实际命令、来源身份、配置、环境、失败堆栈与监控见[批次报告](../../reports/p02-t002-20261019-01/report.md)及其 `cost-evidence/`。在锁定 Windows CPU 环境执行真实 `r2`、shuffle seed 0、model seed 0，打乱阶段上下文 `[12]` 报：

```text
attempt budget exhausted: accepted 194445 of 224080 swaps within 2240800 attempts
```

未进入 r2 训练；没有正式 run。现实现要求每个非空上下文成功交换 `10E`，最多尝试 `100E`；该上下文在实际随机序列下不能在上限内完成目标。错误按设计显式抛出，不能当作打乱对照成功，也不能据此推断真实图无收益。原 T001 验收明确未测试真实发布图打乱，本次发现补充了这个范围的证据。

## 拟交接给 OpenSpec 的范围

建议变更名：`repair-published-shuffle-budget`（仅候选名，尚未创建）。

1. 先检查 `shuffle.py` 中拒绝条件、实际上下文结构与接受率，确认原因；不要预先假定单纯扩大上限就能让全部发布图成功。
2. 保留场景内入/出度、边数与节点身份，无自环/重复/跨场景边，保留每非空上下文最终边集改变、成功交换目标 `10E`、seed `0/1/2`、三图平均以及失败显式化。不得减少目标或跳过难打乱上下文来完成任务。
3. 根据发布图预检确定可完成且有限、确定性的尝试预算或等价的合法抽样策略；所有数据/方法/seed 在正式比较前统一冻结并版本化。若改变预算或抽样路径，更新算法/配置身份与相关规格、文档、检查器及来源记录，不回写旧成本失败。
4. 在不训练模型的情况下，实测 `r0/region/r2 × shuffle seed 0/1/2` 全部 9 张图；报告各上下文尝试/成功次数、拒绝分类、度保持、改变边比例和原/结果边身份；验证相同 seed 可复现。不要只依靠合成 fixture 通过来接受发布图就绪。
5. 调整确实与平台相关的测试：CPU torch 版本应在保留真实环境身份的同时接受合法 `+cpu` 后缀；不同 batch shape 的等价性用已有 `1e-6` 数值口径，同形状状态复位/重复继续严格验证。不要因为本次失败而放松正式同条件重复门槛。
6. 保留 CLI 的 purpose 与输出限制、全部 200 epoch、原始 count、编码器/头/参数量、优化器/选模、主切分/掩码/指标和科学门槛。可补充 Windows 成本记录，但无需把该项混入核心修复。
7. 用仓库 OpenSpec apply → 独立 verify → archive；归档 PASS 后由研究侧验收、回收委托，重新做成本确认，用新批次/run 身份执行 T002。不要在实现/验证流程启动正式训练。

## 工具前置条件

本机 `C:\Users\Lenovo\AppData\Roaming\npm\openspec.cmd` 为 1.4.1，`context --json` 报 `unknown command 'context'`。仓库 `.agents/skills/openspec-e13-propose/SKILL.md` 要求先解析 context，失败时停止，不能回退到 cwd 自行创建 change。本轮因此没有创建 OpenSpec 工件，也未开启委托。

下一执行者应先使 CLI 支持仓库技能的 context/status/instructions 接口，或在已支持的环境启动流程；研究侧必须在真正调用工作流前登记委托。此文件不授权迁移环境、commit/push 或正式运行之外的外部写入。

## 本地运行环境

仓库 `.venv-pinned/Scripts/python.exe` 已可用：Python 3.11.17；主依赖锁定。无需重复安装。预检和诊断报告保留；原始 scratch 成本 run 不覆盖。修复实现变更后，旧批次的源码冻结检查会主动拒绝继续，需建立新批次及新预检。

原成本控制器和等待调度均已退出；不要按旧批次 `continue` 命令重启。它的成本失败状态和独占 scheduler lock 是实际失败现场，不是仍在后台运行的标志。
