## 1. 规范数据与阶段边界

- [ ] 1.1 将入口拆为明确的 preflight/fit/select/diagnose/report/recompute/compare/resume 操作，默认 development，保留模块路径并为旧调用提供迁移错误；用 CLI help／非法选项／路径别名测试验证不在 research/runs 下生成 development 输出。
- [ ] 1.2 复用规范数据与 MAIN_SPLIT 接口，保留 r0/region/r2 节点键、月历、需求来源和训练期 RMS；用三类临时 Parquet 的乱序、重复键、缺月、负值／非有限值和 held-out 扰动测试验证规范排序、拒绝行为与训练独立性。
- [ ] 1.3 将拟合接口限制为训练／验证数据，测试数组仅由 report 构造；用测试标签访问哨兵验证 fit、select、validation diagnose 都不读取测试标签。

## 2. 优化与最佳快照修复

- [ ] 2.1 保持完整窗口 N*3 权重、规范上下文 chunk 顺序、19 updates/epoch、Adam／全梯度裁剪及逐窗口状态重置，保存 update／clip 记录；用不均匀 chunk 与完整窗口参考更新比较、窗口乱序推断和配置测试验证。
- [ ] 2.2 为 best 模型张量和优化器状态建立独立深复制快照，按验证 MSE 和最早平局选择、记录初始化但不选 step0；用“早期最优、后期变差”的受控 CPU 回归验证后续更新不改变 best，恢复后分数与保存 epoch 一致。

## 3. 有限选择、重复身份与诊断

- [ ] 3.1 实现只读 seed-0 两学习率选择、较小学习率平局规则、winner-as-a 链接和三个 seed 的独立 a/b 条件身份，禁止自动矩阵排程；用候选平局、缺候选、错误 repeat／seed／条件及失败记录 fixture 验证。
- [ ] 3.2 保存初始化、10/50/100 和 best 的固定参数 train/validation 分数、完整验证历史及混合参数在线 loss 标签；用短 smoke 和受控完整 history fixture 验证数据字段、固定参数评分与 development 不完整标记。
- [ ] 3.3 实现 P02 §5 全部门槛与 per-seed／汇总诊断、输入置零／尺度／饱和附表及 Zero/LastValue/Ridge 兼容证据；用阈值边界、零分母、b80/b100、缺 history／baseline、a/b 超限和身份不符 fixture 验证 pass/fail/incomplete，不接触真实数据或研究状态。

## 4. 四窗口报告与完整证据

- [ ] 4.1 实现显式 report 阶段及 formal 前置证据检查，恢复 best 后评估 starts 24..27；用误差不同的四窗口 fixture 验证 [4,N,3] 数组、目标月份重复权重、全量 MAE/MSE/RMSE 和缺门槛时 formal 拒绝。
- [ ] 4.2 复用既有指标与带身份覆盖／训练期分组逻辑，保存原始及独立标注的裁剪结果、window/horizon/context/activity/neighbor 指标和计数；用非对称误差、空组及相同 skill 跨上下文 fixture 验证，缺覆盖不得默认为孤立。
- [ ] 4.3 实现格式 v2 的排他输出、候选／seed 状态、真实数据 source 传递、源码／差异／协议／环境 provenance、可读入口与完整数组清单；用碰撞、失败 seed、compare source 和相关源码差异 fixture 验证，保持现有通用忽略规则且不修改旧 run。
- [ ] 4.4 实现神经结果专用 saved-only recompute/compare 和紧凑独占 JSON 报告，先检查条件再计算预测差与归一化 MAE；封禁 demand/graph 读取和模型拟合后验证全部指标可重算，以及 seed／数据／协议／环境错配、输入内输出和报告覆盖拒绝。

## 5. 预检、成本与恢复

- [ ] 5.1 声明专用 CPU／psutil 依赖并实现机器可读 preflight、单 worker／冲突锁及启动前线程控制；用依赖缺失、可控资源不足、PID／锁冲突和有效 fixture 验证明确 pass/fail，帮助和检查路径不得要求真实数据。
- [ ] 5.2 实现独立 watchdog、持久化 batch active-time ledger、10 轮成本门、epochs 6..10 中位数保守估计和协议单次／累计停止线；用注入 clock/sampler 验证 RSS／监测失败／超时暂停、失败与重放计费、未测块保持未知及成本样本继续同轨迹。
- [ ] 5.3 实现与 best 分离的 last 原子 checkpoint，包含模型／优化器／RNG／轮步／history／best／条件／成本引用；用发布中断 fixture 验证前一完整版本保留，旧格式／损坏／错条件在恢复前拒绝。
- [ ] 5.4 实现新身份 parent-linked 轮边界恢复与累计预算继承；用轮内中断后重放的短 CPU fixture 对照不间断执行，验证最终参数／best／分数一致、原目录不变和耗尽预算不被重置。

## 6. 集成验证与交接文档

- [ ] 6.1 用三种临时数据 schema 和两编码器覆盖 CLI 阶段串联、短 development smoke、独立重复和 saved-only 检查，并运行受影响的既有 baseline 回归测试；记录实际命令／结果，只在 scratch／临时目录输出，不运行真实数据矩阵。
- [ ] 6.2 更新 README 专用环境、准确操作顺序、产物／检查／恢复契约和旧格式限制；在 implementation-notes 中交付研究侧预检／运行所需命令与材料清单，核对命令 help 和 fixture 可执行性，不编辑研究计划／协议／决定／索引或委托指针。
- [ ] 6.3 执行 `openspec validate fix-effective-temporal-training-acceptance --type change --strict --json --no-interactive`，整理当前源码基准、规格覆盖和 fixture 证据供独立 e13 验证；验收仅为软件就绪，不宣称真实 learning_ready、T006 完成或图收益，不自动开始正式实验、归档、commit 或 push。
