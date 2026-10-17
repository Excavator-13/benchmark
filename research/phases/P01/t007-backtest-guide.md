# T007：训练期内部两折无图回测

编写日期：2026-10-13。所属任务：P01-T007，任务状态以 [plan.md](plan.md) 为准。
科学协议：[protocol.md](protocol.md)，`P1-count-L6-H3-v3`；保存政策：`P01-records-v2`。

本页把协议 §8 的两折开发回测落成可执行步骤：先给无图入口补 fold 支持并独立验证，再在授权后运行 `r0`/`region`/`r2` 两个折，最后按证据作 T007 验收。用户 2026-10-13 的决定：T007 覆盖三组 count；每折活跃度分组用该折拟合观察期；实现登记为 OpenSpec 委托。本页命令尚未执行；本轮没有启动 run、没有创建 OpenSpec 变更、没有修改实现。

## 1. 这一轮回答什么，做到哪里停止

问题：在训练观察期内部换两个预测起点重新拟合后，无图 baseline 的收益方向是否一致？

范围：

- 数据：`r0/count`、`region/count`、`r2/count`，只用原始 count，不混 `rate`。
- 方法：五项朴素基线与共享 Ridge，沿用协议 §5 的定义、`lambda` 候选、验证选模和分组边界。
- 每折：重新构造窗口、重新计算标准化与 `TrainMean<拟合月数>`，用折内验证选 `NaiveRef`/`NaiveRef6` 与 `lambda`，再在开发评估目标上计算指标。
- 不运行图模型；不使用发布图（[D015](../../decisions.md#d015-发布图使用范围与重建时机)）。T007 全程本机 CPU，不需要 GPU 或云服务器。

停止点：

1. `benchmark.nograph_baseline` 的 fold 支持经 OpenSpec 独立验证 PASS，并由研究侧接受为实现就绪；
2. 三组数据 × 两折的正式 run 完成，检查、重复性与成本记录齐全；
3. 跨折收益对照报告完成，按本页第 9 节给出 T007 验收决定。

不包含：T008 的骨架/范围选择、主评测重跑、T005 的 EvolveGCN-H 复跑、任何图分支实验。

## 2. 两折的固定定义

协议 §8 的两折，月份与窗口起点由本页固定：

| 折 | 拟合观察期 | 训练起点 | 训练→验证间省略 | 验证起点 | 验证目标 | 验证→评估间省略 | 评估起点 | 评估目标 | 评估之后 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 2021-01..2022-06（18 月） | 0..9 | 10, 11 | 12 | 2022-07..09 | 13, 14 | 15 | 2022-10..12 | 16, 17 省略；18..27 不参与 |
| B | 2021-01..2022-09（21 月） | 0..12 | 13, 14 | 15 | 2022-10..12 | 16, 17 | 18 | 2023-01..03 | 19, 20 省略；21..27 不参与 |

窗口起点仍是 0..27，`L=6`、`H=3`、步长 1 月。各折具体月份：

- A 折训练目标 `2021-07..2022-06`（10 个窗口）；验证窗口输入 `2022-01..06`，目标 `2022-07..09`；评估窗口输入 `2022-04..09`，目标 `2022-10..12`。
- B 折训练目标 `2021-07..2022-09`（13 个窗口）；验证窗口输入 `2022-04..09`，目标 `2022-10..12`；评估窗口输入 `2022-07..12`，目标 `2023-01..03`。

要点：

- 每折内部，训练/验证/评估的目标月份两两不相交；省略 10/11（或 13/14 等）边界窗口的理由与主协议相同，都是避免同一目标月跨划分。
- 折内输入可以包含已发生的拟合期目标月，这不是泄漏；协议保证的是目标月隔离和起点信息可用。
- 两折是**开发证据**，不是额外盲测，也不是独立同分布的重复试验。主评测仍是 2023-07..12，不能被折结果替换。
- A 折评估目标 `2022-10..12` 和 B 折评估目标 `2023-01..03` 都落在主协议训练标签范围内；这是折设计决定的开发对照，不能用来宣称最终测试表现。
- 每折的拟合观察期都从 `2021-01` 开始、包含最早的 6 个输入月份；标准化、`TrainMean` 与折内活跃度都只用该折拟合观察期，不共享主协议的 27 月统计量。

## 3. 现状：主入口还没有 fold 调度

`benchmark/nograph_baseline` 目前只实现主协议切分：

- `protocol.py` 把 `train=0..18`、`validation=(21,)`、`test=(24..27)`、`TRAIN_OBSERVATION_MONTH_COUNT=27` 写死，`validate_split_assertions()` 只接受这一组；
- `ridge.compute_training_stats()` 固定用前 27 个月算均值/标准差与活跃度；
- `baselines.train_mean27()` 固定用 27 月均值，产物名也是 `TrainMean27`；
- `runner.py` 固定构造 validation/test 两个 split，产物路径为 `gold/validation.npy`、`gold/test.npy`；
- `checks.py` 的 `recompute`/`compare` 按 validation/test 硬编码，`align-v2` 只认主切分参考；
- `tests/test_protocol.py` 断言主切分的窗口集合与目标月份。

所以 T007 不能只加一个命令行参数就运行。需要给入口增加 fold A/B 调度、折内统计、`eval` 划分和相应产物，并让检查命令识别 fold run。一次性分析脚本不作为首选：协议 §6.1 要求时间回测保存足以重算的完整产物；没有入口支持时，`recompute`/`compare` 不能复核，独立验证也会退化。

## 4. 实现委托的范围与产物契约

变更名建议 `add-nograph-backtest-folds`，登记在 [DELEGATION](../../../DELEGATION.md)。实现由用户在 OpenSpec 侧执行 propose → apply → verify-change → archive-change；研究侧只读核对结束判据，不代跑。

功能语义（参数名由实现决定，但必须具备以下行为）：

- 默认（不选折）继续是主切分；`r0`/`region`/`r2` 的行为、产物与既有 run 完全不变；
- 选择 A 或 B 时，使用第 2 节的窗口与拟合观察期，重新计算标准化、`TrainMean<18|21>` 和折内活跃度分组；
- 折内验证与开发评估分别命名 `validation` 与 `eval`，**不得把 eval 叫 test**；fold run 不计算 2023-07..12；
- fold run 用 `--purpose formal` 写入 `research/runs/`（§6.1 的时间回测需要完整记录），run 元数据标记 `evidence_role=development_backtest`；development 输出只用于实现期冒烟，不构成科研证据。

产物必须记录：

- `config.json`/`provenance.json`：`fold`、拟合观察期、训练/验证/评估窗口起点、省略起点及理由、`evidence_role`、`eval` 目标月份；
- `windows.json`：本折全部窗口的角色与月份，不接受只列 train/validation/test 的旧格式；
- `selection.json`：折内标准化观察期（A 18 月 / B 21 月）、`TrainMean<fit>` 名称、五项验证 MSE、`NaiveRef`/`NaiveRef6` 选择理由、共享 Ridge 各 `lambda` 的验证 MSE 与选中理由、`test_labels_used_for_selection=false`；
- `metrics.json`：`validation` 与 `eval` 两个 split 的总体 MAE/MSE/RMSE、逐窗口、逐 horizon、折内活跃度分组（`fit18`/`fit21`）、常数节点组、邻居/非邻居组、逐上下文组、负预测比例、等权分组 MAE，以及 `eval` 相对 `NaiveRef`/`NaiveRef6` 的收益；
- 预测与标签：`predictions/<method>/validation.npy`、`predictions/<method>/eval.npy`、`gold/validation.npy`、`gold/eval.npy`；
- `audit.json` 或附带 `fold-audit.json`：凡是用主协议 27 月算的字段显式标注，不能与折内 `fit18`/`fit21` 分组同名混用；
- `node-errors.parquet` 带折内活跃度与分组列。

检查命令：

- `recompute` 必须能对 fold run 从保存产物重算，且不读源数据、不重训；
- `compare` 只比较同一数据、同一折、同一 seed 的两个 run；折或数据不一致要显式失败；
- `align-v2` 必须明确拒绝 fold run（既有 v2 参考只有主切分记录，不能伪造折参考）。

测试与文档：折窗口枚举与目标隔离断言、折内统计/命名、fixture 端到端 run、`recompute`/`compare` 正例、`align-v2` 拒绝、主切分回归；README §4.5 与执行指导 §7 的入口说明。

边界（与 T006 相同）：

- 不改协议正文、主切分、主评测、选模指标、分组边界和收益门槛；科学版本保持 `P1-count-L6-H3-v3`；
- 不改 `r0`/`region`/`r2` 既有 run、封存包、OpenSpec 归档；
- 实现与独立验证只用 fixture/development 冒烟，不启动正式 fold run；正式运行与保存需用户另行授权；
- 变更目录不读也不写 `DELEGATION.md`，不维护研究任务状态。

## 5. 登记、独立验证与回收

- 研究侧已把 `add-nograph-backtest-folds` 登记为 [DELEGATION](../../../DELEGATION.md) 的在途委托。
- 用户侧按 OpenSpec e13 流程执行 propose → apply → verify-change → archive-change。
- 研究侧之后只读核对：活跃变更目录已不存在，归档 `verification.md` 为 `Verdict: PASS` 且 Verification Basis 与当前实现一致。
- 满足后按归档报告作实现就绪判断、更新记录并关闭指针。PASS 只是实现证据，不是 T007 实验验收；若正式 fold run 尚未获授权，T007 仍为 `todo`。
- 2026-10-17：实现已归档 PASS 并按 [D020](../../decisions.md#d020-t007-内部两折回测实现研究侧验收) 回收；两折正式 run（12 个）已完成并按 [D021](../../decisions.md#d021-t007-内部两折回测研究侧验收) 接受，结果见[两折分析报告](../../analyses/p01-t007-backtest-20261017-01/report.md)。本页命令保留为复现清单。

## 6. 正式运行前准备

环境与身份：

```bash
conda activate job-sdf-baseline
cd /Users/watuji/da_chuang/repos/benchmark
python -m pip install --no-cache-dir -r benchmark/nograph_baseline/requirements.txt
git status --short --branch
git rev-parse HEAD
python -c 'import sys, numpy, pandas, pyarrow; print(sys.executable); print(numpy.__version__, pandas.__version__, pyarrow.__version__)'
shasum -a 256 dataset/demand/r0.parquet dataset/demand/region.parquet dataset/demand/r2.parquet
```

- 正式 run 自己记录执行 commit、影响计算的 diff/patch、配置与环境；不要为本任务改动主协议或旧 run。
- 先用 `--purpose development` 对 `r0` 的 A/B 各跑一次冒烟，确认产物结构、`eval` 命名和检查命令可用；冒烟结果留在忽略的 `scratch/nograph-baseline/`，不进 `research/runs/`，也不作科研证据。
- run ID 规则：`p01-<dataset>-backtest-a-001`、`p01-<dataset>-backtest-a-repeat-001`，B 同理；目录已存在时换新 ID，不覆盖。
- 不启用 `--retain-candidates`（默认已保存选中模型与全部候选验证分数）；不启用 `--clip-nonnegative`（裁剪结果如需要，另作标记，不混入主对照）。

## 7. 正式 run

主 run 与同 seed 重复 run 各 6 个。下面的命令块在 fold 参数名与 `--fold` 一致时可直接执行；若实现采用其他入口名，以 README 为准，不凭本页虚构参数。

```bash
set -euo pipefail
cd /Users/watuji/da_chuang/repos/benchmark
for dataset in r0 region r2; do
  for fold in a b; do
    case "$fold" in
      a) FOLD="A" ;;
      b) FOLD="B" ;;
    esac
    probe="p01-${dataset}-backtest-${fold}-001"
    repeat="p01-${dataset}-backtest-${fold}-repeat-001"
    test ! -e "research/runs/$probe"
    test ! -e "research/runs/$repeat"
    python -m benchmark.nograph_baseline run --data-name "$dataset" --mode count \
      --seed 0 --fold "$FOLD" --run-id "$probe" --purpose formal
    python -m benchmark.nograph_baseline run --data-name "$dataset" --mode count \
      --seed 0 --fold "$FOLD" --run-id "$repeat" --purpose formal
  done
done
```

每个 run 完成后立即检查：

- `status.json` 为 `succeeded`；
- `metrics.json` 同时有 `validation` 与 `eval`，没有 `test`；
- `windows.json` 的窗口集合与本页第 2 节一致（A：0..9、12、15；B：0..12、15、18）；
- `selection.json` 的标准化观察期与 `TrainMean<fit>` 与折一致（A `TrainMean18`，B `TrainMean21`）；
- `provenance.json`/`config.json` 的 `evidence_role=development_backtest`，`fold` 正确。

任何一项不符就停止后续 run，先修实现或产物，不把不符的 run 当作本折证据。

## 8. 检查、重复性与跨折对照

### 8.1 重算与同 seed 重复

对每个 run：

```bash
python -m benchmark.nograph_baseline recompute \
    --run-dir research/runs/<run-id> \
    --report "research/reports/nograph-baseline/<run-id>-recompute-001.json"
```

对每一组主/重复 run：

```bash
python -m benchmark.nograph_baseline compare \
    --run-a research/runs/<run-id> \
    --run-b research/runs/<run-id>-repeat-001 \
    --report "research/reports/nograph-baseline/<run-id>-repeat-check-001.json"
```

容差：CPU 相对 MAE 差不超过 `1e-6`；同时记录预测最大绝对差。确定性方法没有 seed 方差，两个 run 的差异按执行重复性处理，不叫初始化方差。

`align-v2` 负例：对任一 fold run 运行 `align-v2` 应显式失败（无折参考），把失败输出保存到检查报告；这是预期行为，不是缺陷。

### 8.2 跨折收益对照

对每组数据的两折，用各自 `eval` split 的 `NaiveRef` 与 `SharedRidge` 计算：

- `gain_fold = (MAE_NaiveRef - MAE_SharedRidge) / MAE_NaiveRef`；`MAE_NaiveRef = 0` 时不计算，并明确记录。
- 表列：dataset、fold、NaiveRef、`MAE_ref`、`MAE_ridge`、`gain_fold`、`RMSE_ref`、`RMSE_ridge`、RMSE 变化。
- 再给每个 dataset 的折间平均 `gain` 与两折符号。
- 同时列出主评测 2023-07..12 的既有 `gain`（T004/T006 已保存，不重跑），仅作对照，不是 T007 验收对象。

下面的脚本按第 4 节的产物契约读取；若实现字段名不同，以变更后的契约为准改字段名，不改计算口径。

```bash
python - <<'PY'
import json
from pathlib import Path

RUNS = Path("research/runs")
rows = []
for dataset in ("r0", "region", "r2"):
    for fold in ("a", "b"):
        run_id = f"p01-{dataset}-backtest-{fold}-001"
        metrics = json.loads((RUNS / run_id / "metrics.json").read_text(encoding="utf-8"))
        assert "eval" in metrics["methods"], run_id
        assert "test" not in metrics["methods"], run_id
        reference = metrics["references"]["NaiveRef"]
        ref = metrics["methods"]["eval"][reference]
        ridge = metrics["methods"]["eval"]["SharedRidge"]
        assert ref["MAE"] > 0, run_id
        rows.append({
            "dataset": dataset, "fold": fold.upper(), "run_id": run_id,
            "NaiveRef": reference,
            "MAE_ref": ref["MAE"], "MAE_ridge": ridge["MAE"],
            "gain": (ref["MAE"] - ridge["MAE"]) / ref["MAE"],
            "RMSE_ref": ref["RMSE"], "RMSE_ridge": ridge["RMSE"],
            "RMSE_change": (ridge["RMSE"] - ref["RMSE"]) / ref["RMSE"],
        })
for row in rows:
    print(json.dumps(row, sort_keys=True))
for dataset in ("r0", "region", "r2"):
    gains = [row["gain"] for row in rows if row["dataset"] == dataset]
    print(json.dumps({"dataset": dataset, "folds": len(gains),
                      "mean_gain": sum(gains) / len(gains),
                      "all_positive": all(gain > 0 for gain in gains),
                      "signs": ["+" if gain > 0 else "-" for gain in gains]}))
PY
```

若产物里还有折内分组、常数节点组、邻居组或上下文组，把同样口径的分组 `gain` 一并列表；分组结论只在预注册分组达到门槛时成立，并同时报告完整网格。

## 9. 如何判断结果，何时算 T007 完成

T007 完成条件（同时满足）：

1. fold 实现经归档 PASS 并由研究侧接受；主切分与旧 run 回归通过；
2. 三组数据 × A/B 的主 run 全部 `succeeded`，产物满足第 4 节契约，`recompute` 通过；
3. 每组数据的两折都只按折内验证 MSE 选 `NaiveRef` 与 `lambda`，选模记录可复查；
4. 同 seed 重复 run 的 MAE 相对差不超过 `1e-6`，预测最大差记录在案；
5. 两折 `eval` 的 gain 表、折间平均、主评测对照与成本记录完成；
6. 运行与保存位置、限制写入分析报告、[索引](../../archives/index.md)、阶段计划与 state。

解释规则：

- 跨时间稳健性按协议 §6.2：至少两个合法开发回测的平均 MAE 收益为正。报告两折符号与均值；一折正一折负时，不宣称跨起点稳健。
- 整体改善还要求 RMSE 跨 seed 均值恶化不超过 1%；T007 没有随机 seed，RMSE 按 run 记录报告。
- 两折不是独立盲测，不能给出显著性主张；不把折间一致解释成时间泛化。
- 不因结果不理想重定义折、换验证起点或事后挑参照；需要新设计时另立协议。
- 发布图未参与，T007 不提供任何图收益证据；D015 的时间限制不变。

| 观察 | 判断与下一动作 |
| --- | --- |
| 重算不符、窗口/折/`TrainMean` 与定义不一致 | 先修执行与产物，不解释模型 |
| 两折 `gain` 都为正，均值也正 | 记录跨起点一致，作为 T008 的开发证据；仍不宣称最终测试 |
| 一折正一折负或均值接近 0 | 保留并限定为主评测期证据；T008 决定是否扩大折或换设计 |
| 两折都为负 | 保留；无图 baseline 不占优不阻塞后续图收益验证（协议 §9） |
| RMSE 明显恶化但 MAE 改善 | 按 §6.2 检查整体改善条件，不只看 MAE |
| 同 seed 重复超出容差 | 先查环境、线程数、源码与保存产物，不并入模型方差 |

## 10. 保存、交接与记录更新

- 12 个 run 目录留在 `research/runs/`；检查报告在 `research/reports/nograph-baseline/`；跨折分析报告建议放 `research/analyses/p01-t007-backtest-<日期>-01/report.md`。
- `summary.md` 由 run 自动生成；分析报告写问题、输入身份、折定义、命令、结果表、限制。
- [索引](../../archives/index.md)记录 run 的保存、提交与备份状态；本轮不追加，等实际 run 形成产物。
- 阶段计划与 state 在 T007 真正完成时才改状态；本轮保持 `todo`。
- 不自动封存、commit、push；授权后按 `P01-records-v2` 与相关流程执行。
- 交接清单：12 个 run ID、跨折报告路径、分析报告路径、检查报告、成本与限制。

## 编写时的检查范围

2026-10-13：本轮只读核对协议 §8、阶段计划、代码硬编码位置与测试，并用 Python 算术核对两折窗口、拟合观察期和目标月份隔离；未运行 baseline、未改实现、未创建 OpenSpec 变更、未连接服务器。T005 因用户服务器暂时无法开机而暂缓，与本页无关。
