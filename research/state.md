# 当前状态

更新时间：2026-11-28，Asia/Shanghai。
当前阶段：[P02](phases/P02/plan.md)，尚未验收结束。
当前任务：P02-T006，状态与验收以阶段计划为准；T009 由其他成员负责，本轮未介入。
当前执行者：本会话完成 P02-T006 v2 r0/GRU 的筛选、三 seed a/b 轨迹和 section-5 诊断；当前无人执行，无本会话后台实验。
本次授权范围：完成 seed 2/b 并运行冻结的 saved-evidence readiness 诊断；末段稳定性门失败后按协议停止，未访问测试期或追加轮数。

## 恢复位置

- 首个 v1 r0/GRU 块按协议停止，实际结果与未完成证据见[执行报告](reports/p02-t006-execution-20261108-01/report.md)；首批可读交付已随本地提交保存，身份从 Git 历史追溯。
- [D040](decisions.md#d040-t006-r0gru-预算末段失败与固定预算修订候选)已接受；[v2 协议](phases/P02/protocol-v2.md)冻结新预算、诊断区间、有限矩阵与连续记账，v1 内容不变。
- `extend-effective-training-budget-v2` 已归档并独立 PASS，研究侧接受软件就绪；验收及适用范围见[回收报告](reports/p02-t006-software-closeout-20261128-01/report.md)。委托指针已关闭。
- 原 batch/ledger 已登记 900 秒 v2 保守准备成本扣除。seed 0 的 `1e-3` 与 `3e-3` 候选均完成 200 轮且成本门通过；selection 已按验证 MSE 冻结 `1e-3`，胜者轨迹链接复用为 seed 0 repetition a。完整执行记录见[研究报告](reports/p02-t006-v2-execution-20261128-01/report.md)。T006 为 `in_progress`，T009 未介入。
- seed 1/a 在同一 Windows 环境完成 v2 的 200 轮轨迹；账本原子替换错误导致 epoch 144 暂停，已由合规新身份恢复并复验 checkpoint。细节见[seed 1/a 执行与恢复报告](reports/p02-t006-v2-execution-20261128-02/report.md)。
- seed 2/a confirmation 已按冻结 `1e-3` 条件完成 v2 200 轮，成本门和 checkpoint 重评均通过，证据见[seed 2/a 执行报告](reports/p02-t006-v2-execution-20261128-03/report.md)。
- seed 0/b 与 seed 1/b 均已完成 v2 200 轮，成本门通过；各自验证摘要指标与同 seed a 轨迹相同，完整配对判定见[section-5 诊断报告](reports/p02-t006-v2-diagnosis-20261128-01/report.md)。单独执行报告见 [seed 0/b](reports/p02-t006-v2-execution-20261128-04/report.md) 和 [seed 1/b](reports/p02-t006-v2-execution-20261128-05/report.md)。
- seed 2/b 已完成，六条 a/b 轨迹齐全。section-5 诊断中除预算末段门外均通过；b160→b200 改善分别为 16.12%、15.40%、17.99%，均超过 1% 阈值，`learning_ready=false`。详见[诊断报告](reports/p02-t006-v2-diagnosis-20261128-01/report.md)。按 v2 固定预算停止，未运行测试或额外轮数；T006 → `blocked`。
- 软件实现与验收文件仍在本机工作区，未提交；封存、异地备份与恢复核验未做。保存对象见[归档索引](archives/index.md#p02-t006-v2-条件与软件验收2026-11-28)。

## 下一可执行动作

动作：审阅并决定是否接受 D041 的固定 400 轮 r0/GRU 有界跟进候选。
前置条件：D041 当前为 `proposed`；v2 协议及失败证据保持原样。未经新决定接受和新版本软件独立验证，不启动该候选。
后续研究验收：若候选被接受，先版本化协议、完成软件实现与独立 PASS，再按原账本/12 小时总上限重新预检和逐块成本门；T006 完整范围及 T007 前置不变。

## 待处理事项

- T006 的 v2 r0/GRU 块因预算末段门未通过而停止；learning_ready=false，测试未生成。不得将 v1 checkpoint 拼接为 v2，也不得绕过版本化决定扩展预算。
- 完整模型与数组仍仅在本机，未封存；原生 Windows 和旧 Windows 完整产物仍未在本轮核验。
