# P01-T007 训练期内部两折无图回测

所属任务：P01-T007。日期：2026-10-17。
科学协议：`P1-count-L6-H3-v3`；保存政策：`P01-records-v2`。
执行指导：[T007 两折回测指导](../../phases/P01/t007-backtest-guide.md)。

## 1. 问题与设计

问题：无图 baseline（五项朴素规则与共享 Ridge）在训练观察期内部换两个预测起点重新拟合后，MAE 收益方向是否一致？

设计按协议 §8 与 T007 指导 §2 固定，不按结果调整：

| 折 | 拟合观察期 | 训练起点 | 验证起点 | 验证目标 | 开发评估起点 | 评估目标 |
| --- | --- | --- | --- | --- | --- | --- |
| A | 2021-01..2022-06（18 月） | 0..9 | 12 | 2022-07..09 | 15 | 2022-10..12 |
| B | 2021-01..2022-09（21 月） | 0..12 | 15 | 2022-10..12 | 18 | 2023-01..03 |

每折重新构造窗口、折内标准化、`TrainMean18`/`TrainMean21` 与 `fit18`/`fit21` 活跃度分组；`NaiveRef`/`NaiveRef6` 与共享 Ridge 的 `lambda` 只用折内验证 MSE 选择。评估 split 命名 `eval`，不计算 2023-07..12。两折是开发证据，不是额外盲测，也不替代主评测。

## 2. 执行身份与输入

- 实现 commit：`e9195006dc402d2ce6fb5afb3a164dfef699200c`（运行时代码与测试已提交；各 run 的 `git-commit.txt` 与 `code-source.json` 记录同一提交）。
- 环境：`/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline`，Python 3.11.17、NumPy 1.26.4、pandas 2.2.3、PyArrow 17.0.0；CPU arm64、10 核；BLAS 线程固定为 1。
- 数据（各 run 的 `source-sha256.json` 记录，12 个 run 一致）：

| 数据 | demand SHA256 | 图 SHA256（仅覆盖注释） | 节点键 SHA256 |
| --- | --- | --- | --- |
| `r0` | `fc8ebd497f3100f76bc92078529535055a34c281857d61a8d7bd8034898c6946` | `c49bc2ecfddd24ddc7a6c6654fdc7bf2e908820139a987f99a115c11b583aa5b` | `8928c4f21d4585d4dc79811e72d0c733649fa525ef900fb8db25328d7f9cb6fa` |
| `region` | `27a946c787efcd5f1d2b25ca35bebd1392320d9b10920e771405a664db5e4a3f` | `c0bed3290be3691fbb07c4834c96e8d567e1f54cdfb2120d8a0846a86b64d87c` | `ebb131183fa8a52b48287ee751471781e7fba0baa03466810533740f003a2d86` |
| `r2` | `4ada154773b8678ae7d25b42e36a8309a51490bbe9fe059f015bb61724ed4c3c` | `4cc1f399dd9061920179ade34d018fcbd58c3e00bb40f303b91e9aba99f9e12c` | `7d26eaa0f02b5b2263a6fda849d4257cc107371df02e18b0f0d9cc1155ab0a58` |

12 个正式 run（seed 0，`--purpose formal`，均为 `success`）：

| 数据 | A 折 | A 折重复 | B 折 | B 折重复 |
| --- | --- | --- | --- | --- |
| `r0` | `p01-r0-backtest-a-001` | `p01-r0-backtest-a-repeat-001` | `p01-r0-backtest-b-001` | `p01-r0-backtest-b-repeat-001` |
| `region` | `p01-region-backtest-a-001` | `p01-region-backtest-a-repeat-001` | `p01-region-backtest-b-001` | `p01-region-backtest-b-repeat-001` |
| `r2` | `p01-r2-backtest-a-001` | `p01-r2-backtest-a-repeat-001` | `p01-r2-backtest-b-001` | `p01-r2-backtest-b-repeat-001` |

运行命令模式（完整步骤见指导 §7）：

```bash
python -m benchmark.nograph_baseline run --data-name r2 --mode count --seed 0 \
    --fold A --run-id p01-r2-backtest-a-001 --purpose formal
```

每个 run 的 `windows.json` 角色数与指导一致：A 折训练 10 窗口、省略 6 窗口、验证 1、eval 1、折外 10；B 折训练 13、省略 6、验证 1、eval 1、折外 7。

## 3. 折内选模

`NaiveRef` 与 `NaiveRef6` 只由折内验证 MSE 决定；共享 Ridge 的 `lambda` 只由折内验证 MSE 决定，`test_labels_used_for_selection=false`。完整五项验证 MSE 与 Ridge 候选表在各 run 的 `selection.json`。

| 数据 | 折 | NaiveRef | NaiveRef6 | 验证 MSE (ref) | 验证 MSE (Ridge) | 选中 lambda | M |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `r0` | A | LastValue | LastValue | 334,910.23 | 414,543.28 | 0.1 | 23,350 |
| `r0` | B | TrainMean21 | TrainMean21 | 393,486.41 | 465,247.78 | 1.0 | 30,355 |
| `region` | A | LastValue | LastValue | 17,670.18 | 23,275.42 | 0.1 | 163,450 |
| `region` | B | TrainMean21 | TrainMean21 | 17,464.82 | 18,078.66 | 0.001 | 212,485 |
| `r2` | A | LastValue | LastValue | 2,769.95 | 4,056.66 | 1.0 | 1,214,200 |
| `r2` | B | LastValue | LastValue | 1,798.67 | 2,921.16 | 1.0 | 1,578,460 |

观察：Ridge 的验证 MSE 在六组中都高于当折 `NaiveRef`；选模仍按协议执行，没有据评估或主评测结果调整 `lambda`。`NaiveRef` 在 A 折三组均为 LastValue，在 B 折 `r0`/`region` 变为 TrainMean21、`r2` 仍为 LastValue。

## 4. 开发评估结果

评估指标为原始单位的 `eval` 总体 MAE/RMSE。收益定义为 `gain = (MAE_ref - MAE_Ridge) / MAE_ref`；负值表示 Ridge 更差。

| 数据 | 折 | NaiveRef | MAE ref | MAE Ridge | gain | RMSE ref | RMSE Ridge | RMSE 变化 | 等权组 MAE ref | 等权组 MAE Ridge | 负预测比例 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `r0` | A | LastValue | 161.203 | 193.080 | -19.77% | 674.846 | 674.213 | -0.09% | 47.067 | 56.197 | 0.81% |
| `r0` | B | TrainMean21 | 297.182 | 287.722 | +3.18% | 1,193.633 | 1,139.489 | -4.54% | 85.096 | 82.458 | 0.014% |
| `region` | A | LastValue | 29.887 | 33.428 | -11.85% | 140.272 | 138.788 | -1.06% | 12.693 | 14.109 | 1.85% |
| `region` | B | TrainMean21 | 46.145 | 45.358 | +1.70% | 235.343 | 226.122 | -3.92% | 18.939 | 18.655 | 1.08% |
| `r2` | A | LastValue | 5.089 | 6.637 | -30.41% | 42.411 | 58.915 | +38.91% | 6.437 | 8.293 | 0.68% |
| `r2` | B | LastValue | 8.009 | 7.599 | +5.12% | 76.726 | 69.656 | -9.21% | 9.823 | 9.342 | 0.10% |

同折 `eval` 上全部方法的 MAE，用于判断 Ridge 是否真的更强：

| 数据 | 折 | Zero | LastValue | WindowMean6 | TrainMean<fit> | SeasonalNaive12 | SharedRidge |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `r0` | A | 842.201 | **161.203** | 201.259 | 175.527 | 211.845 | 193.080 |
| `r0` | B | 910.068 | 358.163 | 283.297 | 297.182 | **202.401** | 287.722 |
| `region` | A | 120.315 | **29.887** | 34.140 | 31.315 | 38.637 | 33.428 |
| `region` | B | 130.010 | 53.445 | 43.722 | 46.145 | **35.392** | 45.358 |
| `r2` | A | 16.196 | **5.089** | 5.776 | 6.305 | 7.495 | 6.637 |
| `r2` | B | 17.501 | 8.009 | 6.864 | 7.499 | **6.729** | 7.599 |

粗体为当折评估 MAE 最小的方法。**Ridge 在六组中都不是评估 MAE 最小的方法**：A 折是 LastValue，B 折是 SeasonalNaive12。B 折相对 `NaiveRef` 的小幅正收益，主要来自该折验证选出的参照（`r0`/`region` 为 TrainMean21）在评估期表现变差，而不是 Ridge 超过了同折所有便宜规则。

## 5. 分折与分组

`fit18`/`fit21` 四组的评估 MAE 收益（Ridge 相对当折 `NaiveRef`）：

| 数据 | 折 | inactive | low | medium | high |
| --- | --- | ---: | ---: | ---: | ---: |
| `r0` | A | -59.67% | +15.25% | -7.74% | -19.80% |
| `r0` | B | -24.51% | -6.16% | -0.69% | +3.19% |
| `region` | A | -20.07% | +8.25% | -0.84% | -12.04% |
| `region` | B | -74.46% | -3.19% | -2.94% | +1.75% |
| `r2` | A | -24.27% | +5.02% | +3.60% | -32.63% |
| `r2` | B | -50.27% | -9.49% | -5.89% | +5.65% |

B 折的总体正收益由 high 组驱动；同一折的 inactive 组大幅变差。A 折的 high 组在 `r0`/`region`/`r2` 都变差。分组只用于解释，不把某一组的改善升级为整体改善。

## 6. 跨折判断

按 §6.2 的跨时间稳健性要求，检查两个合法开发回测的平均 MAE 收益是否为正：

| 数据 | A 折 gain | B 折 gain | 折间平均 | 两折都为正 |
| --- | ---: | ---: | ---: | --- |
| `r0` | -19.77% | +3.18% | -8.30% | 否 |
| `region` | -11.85% | +1.70% | -5.07% | 否 |
| `r2` | -30.41% | +5.12% | -12.64% | 否 |

结论：三组数据的折间平均 MAE 收益都为负，**跨时间稳健性条件未满足**。两折的收益方向相反，且参照不同（A 折三组与 B 折 `r2` 的 NaiveRef 为 LastValue，B 折 `r0`/`region` 为 TrainMean21），所以不能把 B 折的小幅正值解释为跨起点一致的收益。协议没有要求正收益才能完成 T007；这里记录的是“没有稳定收益”的证据。

## 7. 主评测对照

主评测 2023-07..12 已由 T004/T006 的正式 run 保存，本轮不重跑，仅作对照：

| 数据 | 来源 run | NaiveRef | 测试 MAE ref | 测试 MAE Ridge | gain | 测试 RMSE ref | 测试 RMSE Ridge |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `r0` | `p01-r0-sharedridge-002` | LastValue | 189.875 | 274.765 | -44.71% | 925.262 | 1,579.910 |
| `region` | `p01-region-sharedridge-002` | LastValue | 35.310 | 47.598 | -34.80% | 193.847 | 326.191 |
| `r2` | `p01-r2-sharedridge-001` | LastValue | 6.140 | 8.669 | -41.19% | 85.597 | 167.691 |

主评测与两折的方向也不一致：主评测三组都大幅为负，B 折小幅为正。这进一步说明不能把单个起点的正收益当作稳定证据。

## 8. 重复性、重算与检查

- 同 seed 重复：6 组主/重复 run 的 `compare` 均为 `ok`；全部方法的预测最大绝对差 0、指标字段最大归一化差 0、MAE 相对差 0。比较字段数 `r0` 1,608、`region` 2,328、`r2` 7,728。
- saved-only 重算：12 个 `recompute` 报告均为 `ok`；`source_data_read=false`、`model_refit=false`，指标与节点表最大归一化差 0。节点表行数 `r0` 28,020、`region` 196,140、`r2` 1,457,040。
- `align-v2` 负例：对 `p01-r0-backtest-a-001` 运行后按预期失败（exit 1），报告 `status=failed`，错误为 `align-v2 rejects fold run A: the immutable v2 reference has no fold records, ...`，未伪造折参考。
- 检查报告位于 `research/reports/nograph-baseline/`：12 份 recompute、6 份 repeat-check、1 份 align-v2 拒绝报告。

## 9. 成本

本机 CPU、单线程 BLAS、15:55 前后执行；范围只代表本机条件。

| 数据 | 总耗时（4 个 run） | 峰值 RSS | 主要阶段（A 折首 run） |
| --- | --- | --- | --- |
| `r0` | 0.491–0.517 s | 141–144 MB | 读取 0.059 s、拟合 0.004 s、推理 0.0002 s |
| `region` | 0.724–0.728 s | 269–281 MB | 读取 0.162 s、拟合 0.034 s、推理 0.001 s |
| `r2` | 1.897–2.015 s | 994–1,164 MB | 读取 0.387 s、拟合 0.266 s、推理 0.009 s |

分阶段耗时与峰值内存的原始字段在各 run 的 `measurements.json`。两折的窗口数少于主协议（A 10 训练窗、B 13，主协议 19），所以 r2 折 run 比主协议 r2 run（约 2.95 s）略快；不对跨设备或历史成本作推断。

## 10. 解释与限制

- 两折都是开发证据，不是额外盲测，也不是独立同分布的重复试验；每次评估只有一个 3 个月窗口，不能给出显著性主张。
- B 折评估目标 2023-01..03 与 A 折评估目标 2022-10..12 都落在主协议训练标签范围内；折设计如此，只用于开发对照。
- 每折的 `NaiveRef` 由该折验证 MSE 选出，折间参照可能不同；本报告中 A 折为 LastValue，B 折 `r0`/`region` 为 TrainMean21。跨折比较的是各自参照下的收益，不是同一个 baseline 的收益。
- 共享 Ridge 是确定性方法，没有 seed 方差；同 seed 重复只检验执行重复性，不作为初始化方差。
- 无图范围：没有运行图模型，不提供图收益证据；发布图构建时间仍未知（D015）。
- `r2` 训练期全零比例高、数值尺度小，原始 MAE 的组间权重与 `r0`/`region` 不同；跨粒度不直接比较原始 MAE 大小。
- 本轮未执行可选 sklearn 后端；`alpha=lambda*M` 的 NumPy 路径已由 run 与检查验证。

## 11. 结论与下一动作

- T007 的执行与证据要求已满足：两折各自重建窗口与预处理，折内选模，评估、分组、重复性、重算、拒绝路径与成本均有记录。
- 科学结论是否定的：在 `r0`/`region`/`r2` 三组上，共享 Ridge 相对当折 `NaiveRef` 的 MAE 收益在 A 折为负、B 折小幅为正，折间平均为负；§6.2 的跨时间稳健性条件未满足。Ridge 在六组评估中都不是 MAE 最小的方法；主评测也显著为负。
- 不宣称改善，也不因结果不理想改折、换参照或重定义收益。T008 应把共享 Ridge 视为可重复但总体不占优的参照，不应把它当作已证明有收益的骨架；图收益验证仍需按 D006/D007 另行设计。
- T005 仍因服务器暂无法开机而暂缓，与本报告无关。

## 12. 保存状态

- 12 个 run 目录位于 `research/runs/`，合计约 217 MB；完整预测、标签、模型、掩码、节点误差与元数据均在本机，未封存。
- 19 份检查报告位于 `research/reports/nograph-baseline/`；本报告位于 `research/analyses/p01-t007-backtest-20261017-01/`。
- 12 个 run 的 `summary.md`、`provenance.json`、`command.json`，19 份检查报告与本报告随本次记录提交并 push `origin/xzs`；完整预测、标签、模型、掩码、节点误差与 run 目录其余文件仅在本机（约 217 MB），并按 `.gitignore` 的 fold run 规则忽略。未封存，未做异地备份或恢复核验；运行代码身份为 `e9195006dc402d2ce6fb5afb3a164dfef699200c`，数据与节点键身份见第 2 节。
