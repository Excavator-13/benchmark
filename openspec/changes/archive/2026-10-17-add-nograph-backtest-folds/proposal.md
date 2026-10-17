## Why

研究任务 P01-T007 需要协议 `P1-count-L6-H3-v3` §8 的 A/B 两折开发回测，但当前无图 CPU 入口、统计量、产物和检查器均固定为主切分。补齐同一入口下的折调度及可重算证据，才能在另行授权正式运行前验证实现就绪。

## What Changes

- 增加显式 `--fold A|B`，严格采用 T007 指导 §2 的起点、月份、省略及不参与窗口；省略该参数继续使用原主切分与原产物格式。
- 各折独立重建训练窗口、标准化、共享 Ridge 和活跃度分组：A 使用前 18 月、`TrainMean18`、`fit18`；B 使用前 21 月、`TrainMean21`、`fit21`。保留原始单位验证 MSE、候选集、平局规则与分组边界。
- 折预测和指标仅包含 `validation`/`eval`，不运行主测试期。保存完整折窗口角色、拟合期、选择理由、预测/标签、折内掩码和节点误差；主协议 27 月描述性审计显式标记来源范围。
- 扩展保存产物检查：fold `recompute` 只读保存材料；`compare` 显式校验同数据身份、同折、同 seed，保留其他条件与数值容差；`align-v2` 明确拒绝 fold run，因为 v2 没有折参考。
- 保持 `formal`/`development` 两种 purpose。正式折输出默认位于 `research/runs/`，标记 `evidence_role=development_backtest`；实现和独立验证仅使用临时 fixture 与 development 输出。
- 增加 A/B 正负例、主切分字段/产物回归，规划更新 README §4.5 与执行指导 §7 的入口说明。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `nograph-baseline-entry`: 将现有主切分限定扩展为默认主切分及显式 A/B 折，覆盖折内统计、选模、指标、可重算产物、检查兼容和开发证据边界；其他既有语义保留。

## Impact

- 实现涉及 `benchmark/nograph_baseline/{protocol,ridge,baselines,runner,metrics,data,checks,cli}.py`，以及按需调整 `artifacts.py` 的来源/序列化衔接和现有 `tests/`；不增加第三方依赖或图模型路径。
- 文档修改范围为 `README.md` §4.5 与 `research/phases/P01/execution-guide.md` §7 的入口说明；其余研究记录、协议正文与任务状态不在实现范围。
- 不变更科学版本、保存政策、主切分/2023-07..12 主评测、候选和选模指标、分组边界或收益门槛。不修改旧 run、封存包、`experiments_archive/` 或已有 OpenSpec 归档。
- 本轮只创建规划；不读写 `DELEGATION.md`，不运行实验，不 commit/push、封存或恢复核验。后续实现/独立验证也不启动正式 fold run。
- 最终委托回收依据为后续归档 verification 的 `Verdict: PASS` 且 Verification Basis 与当前实现一致；研究侧另行判断实现接受及 T007 实验验收，规划不代替这些结论，也不镜像任务进度到研究记录。
