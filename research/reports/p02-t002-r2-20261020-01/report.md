# P02-T002：r2正式执行批次

更新时间：2026-10-20，Asia/Shanghai。所属任务：P02-T002。
批次身份：`p02-t002-r2-20261020-01`。

## 授权与范围

用户在查看[历史成本预测](../p02-t002-20261020-01/report.md#r2训练时长预测汇总)后明确要求运行r2，表示时间足够；本批次不再适用D027的五小时/18:23:51截止。随后授权在D盘建立独立副本、保留C盘原仓库，并要求成功完成后推送更新。接受范围见D028。

仅运行r2：模型seed0/1/2×自身/真实图/三张打乱图×两次重复，共30次正式拟合；全部使用原200epoch、GRU hidden32、Adam、raw count、CPU单线程及验证MSE选模。三图独立拟合后平均MAE，不挑选图。每次完成重算，重复b后立即同条件比较，最后汇总三图；合计30份recompute、15份compare、6份summarize报告。全部通过才写入`completion.json`并提交推送；该完成文件只说明r2执行块就绪，不替代整个T002验收，不启动T003/T004。

## 运行位置与来源

- 原仓库：`C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark`，原数据、旧运行和证据保留。
- 执行副本：`D:/research-runs/JODBSDFres/benchmark-r2-20261020-01`，从`2ca56dd`建立独立Git副本，按字节复制当前版本化文件；计算源码与已验收指纹相同。新控制器及研究记录作为本批次差异保存，不修改训练实现。
- 解释器：原仓库`.venv-pinned/Scripts/python.exe`，固定Python3.11与原依赖；工作目录及临时文件在D盘，不重新安装或改变包版本。
- 复用图：执行副本内`scratch/graph-value-skeleton/repair-shuffle-v2-20261020-06/graphs/r2-shuffle{0,1,2}-a`；预检重验完整保存证据、实际节点/源边、seed和当前生成器身份，不重新生成或覆盖旧图。
- 正式产物：执行副本`research/runs/<run-id>/`；完整数组留在D盘，按现有保存政策仅推送可读记录和检查报告。该副本不等于已核验异地备份。

相对历史诊断属于有条件可比：数据、配置、源码、依赖保持一致，存储盘与工作目录改变；旧诊断并非完整拟合，不作为成功重复。批次内部两次重复由同机同环境、来源检查及CPU归一化差≤1e-6验证，指标重算≤1e-12。没有放松门槛。

## 控制与恢复

[控制器](../../phases/P02/t002_r2_batch.py)只编排公开CLI，不包裹Adam、不改训练计算。先执行`prepare`，成功后再执行`run --push-on-success`。运行脚本SHA、解释器、源码、依赖、输入和图文件身份保存在`preflight.json`；每个子进程前核对，失败即暂停后续任务。同名run或检查存在即拒绝，不自动重试、不覆盖。正式30次清单在`manifest.json`，实时状态以`progress.json`为准，PID与命令见`controller.json`，准确子进程命令与耗时见`monitor/`。

仓库根命令（固定解释器，使用D盘副本工作目录）：

```powershell
& 'C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark/.venv-pinned/Scripts/python.exe' -B research/phases/P02/t002_r2_batch.py prepare --batch p02-t002-r2-20261020-01
& 'C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark/.venv-pinned/Scripts/python.exe' -B research/phases/P02/t002_r2_batch.py run --batch p02-t002-r2-20261020-01 --push-on-success
```

顺序运行，一次只有一个训练worker；每15秒写控制器心跳和当前进程耗时。训练实现未输出逐epoch持久进度，不能把心跳换算为已完成epoch。每次完成后更新基于实测worker wall的剩余时间；未测方法暂用打乱图均值或初始40分钟/次，检查开销另计，预测不是截止承诺。参考粗估约20小时，实际以完整执行测量为准。

启动要求可用磁盘≥8GiB，后续子进程前要求≥1GiB。单次拟合超过4小时、单次检查超过30分钟或`STOP_NOW`请求触发运行级watchdog；尝试仅终止所拥有进程树，终止拒绝会保留`worker_may_be_running`，不把它写成已退出。`STOP_AFTER_CURRENT`在下一子进程边界停止。控制器异常、非有限训练、身份/复现/重算失败均停止后续调度；训练中断不计完成，不依赖中间loss或测试成绩调参/早停。

运行期间实时JSON和数组以D盘为权威；C盘本报告是启动交接入口，不保证镜像每个心跳。成功后`result.md`、`completion.json`和51份检查作为r2完成证据；仅在成功分支提交本批次与可读run记录并push至`origin/FJWP2T002`。推送失败保留本地结果与`publication.json`，不覆盖远端、不强推。不会为本地push回执再新增回执提交。

## 当前执行

2026-10-20 19:08:51 Asia/Shanghai已启动隐藏后台控制器，解释器启动器PID17668，实际控制器PID4076；19:08:55启动首项`p02-t002-r2-20261020-01-r2-shuffled0-s0-a`。预检为ok，正式拟合尚未完成。实时以D盘`progress.json`和`controller.json`核对PID与状态，不凭历史PID认定仍在运行。

首次准备检查因可选的`benchmark/__init__.py`不存在而失败，未创建正式run；已修正控制器的可选文件清单，保留`prepare-attempt-01/failure.json`及当时控制器字节，再完整预检通过。训练实现与科学配置未改。控制器写入重试的事件日志目录已在启动时建立，避免诊断专用直接replace的旧问题。来源/保存状态见[索引](../../archives/index.md)。
