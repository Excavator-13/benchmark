# T006 首个真实执行块：r0/GRU

制定日期：2026-11-08。所属任务：P02-T006。用户已授权从当前交接点开始执行；本轮先完成 r0/GRU 块，遇协议停止条件即保存并交接，不启动 T007 或 T009。

执行后恢复提示：本指导对应的首块已按预算末段门失败停止，实际证据见[执行报告](../../reports/p02-t006-execution-20261108-01/report.md)。下列命令保留为本批执行身份，不得覆盖已有输出或直接补跑剩余拟合；当前下一动作以 [state](../../state.md) 为准。

科学定义以 [P02 协议](protocol.md) 为准，软件入口见 [README §4.7](../../../README.md#47-p02-effective-recurrent-entry-benchmarkmultivariate_time_series)。本页只固定执行位置，不改预算／门槛。

## 条件与保存位置

- 设备：本机 macOS arm64，CPU 确定性单线程；解释器 `/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python`。
- 源码基准：`bf5abed8a17403c1a5a87955c39d835d8df902ab`；实际执行源码和环境以 runner 的 provenance 为准。
- 数据：`dataset/demand/r0.parquet`；节点、月历及内容身份以机器可读 preflight 为准。邻居分组使用 `dataset/graph/r0.parquet`，不作为自身模型输入。
- batch：`p02-t006-effective-20261108-01`；ledger：`research/reports/p02-t006-execution-20261108-01/ledger.json`。这是修复后新批次，既有旧预实验与软件 fixture 不冒充本批轨迹；本批失败／重复／检查均保留并累计，不因恢复重置。
- 报告和 Ridge 验证参照：[执行目录](../../reports/p02-t006-execution-20261108-01/)。Ridge 从已接受旧包的 JSON 直接派生，检查实际需求 hash；不解包覆盖、不重新拟合。
- formal 输出：`research/runs/<run-id>/`，每次新身份。所有参数沿用 100 epoch、hidden32、L6/H3、学习率候选 `{1e-3,3e-3}`；不传开发模式资源注入值。

## 准确启动命令

以下从仓库根执行；Python 路径可直接替换命令首项。预检失败不得启动训练。

```sh
/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m benchmark.multivariate_time_series.effective_temporal_training preflight --data-name r0 --data dataset/demand/r0.parquet --model GRU --seed 0 --purpose formal --run-id p02-t006-r0-gru-s0-lr1e3-a-20261108-01 --output-root research/runs --batch-id p02-t006-effective-20261108-01 --ledger research/reports/p02-t006-execution-20261108-01/ledger.json --out research/reports/p02-t006-execution-20261108-01/preflight-r0-gru-01.json

/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m benchmark.multivariate_time_series.effective_temporal_training fit --data-name r0 --data dataset/demand/r0.parquet --model GRU --seed 0 --learning-rate 1e-3 --candidate-role screening --repeat-role a --run-id p02-t006-r0-gru-s0-lr1e3-a-20261108-01 --purpose formal --output-root research/runs --batch-id p02-t006-effective-20261108-01 --ledger research/reports/p02-t006-execution-20261108-01/ledger.json --remaining-fits 7
```

fit 内在第 10 轮发布 `cost.json`，按实测样本检查整个剩余块预算；通过后在同一进程、同一轨迹继续至 100 轮。不能用 `--epochs 10` 冒充正式拟合后再重启。之后第二个候选仅改为学习率 `3e-3`、新 ID `p02-t006-r0-gru-s0-lr3e3-a-20261108-01`、剩余拟合数 6。

选择：`select --block-id p02-t006-r0-gru-20261108-01 --purpose formal --output-root research/reports/p02-t006-execution-20261108-01/blocks --candidate <lr1e3目录> --candidate <lr3e3目录>`。只读验证 MSE 冻结学习率，胜出 seed0 链接复用为 a。

再做所选学习率的 a seeds1/2 和 b seeds0/1/2，每次新 run ID、同设备／源码／环境／ledger，剩余拟合数依次 5/4/3/2/1。诊断使用 `diagnose --block <block目录> --a-run 0=<胜者> --a-run 1=<s1-a> --a-run 2=<s2-a> --b-run 0=<s0-b> --b-run 1=<s1-b> --b-run 2=<s2-b> --ridge research/reports/p02-t006-execution-20261108-01/ridge-r0-validation.json --purpose formal --report <新报告路径>`；实际 argv 由各阶段保存。

验证期门槛通过后，report 对每条被链接的 a/b 轨迹生成四窗口报告，使用冻结 diagnostics 和实际 graph；之后用保存材料 recompute／compare。检查或成本超限即暂停，不更换有利 seed、不加候选或自动扩图比较。

## 停止、恢复与交接

协议资源和有效性停止条件照旧。若受运行沙箱限制而无法采样真实 RSS，使用获授权的主机进程监测权限；不伪造监测 pass。软件异常保留原现场，交给对应软件流程，不临时改训练代码绕过。

保存 run ID、退出码、预检、cost、selection、a/b 检查、diagnose、恢复 checkpoint／parent 和未决问题；state 指到最后成功步骤。报告只在[执行报告](../../reports/p02-t006-execution-20261108-01/report.md)叙述，后续模型／粒度另按其成本门展开。

编写时已读当前 CLI 和资源控制实现并运行首个真实预检；完整训练链与后续报告尚未实机完成。Windows 执行和传输未在本指导实机核验。
