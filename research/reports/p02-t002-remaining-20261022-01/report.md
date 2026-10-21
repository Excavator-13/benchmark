# P02-T002：region 与 r0 执行交接

日期：2026-10-22，Asia/Shanghai。任务：P02-T002。组合身份：`p02-t002-remaining-20261022-01`。

## 范围与冻结条件

用户在查看region粗略耗时后要求“把region和r0一起办了吧”。按D030依次执行region、r0，各30次正式拟合和51项检查，共60次200epoch拟合及102项检查。每组模型seed0/1/2，自身/真实图/三张打乱图，每条件独立重复a/b。各组30重算、15重复比较、6三图汇总，容差分别为1e-12及归一化1e-6。科学配置、CPU单线程、GRU hidden32、Adam、最早验证MSE平分选模和数据边界保持原协议。不同数据组之间不当作相同条件重复。

r2已于2026-10-21 23:36:58完成30次200epoch及51项检查，23:37:08推送成功，提交`815f1cc6a546ef81a4deb005dc12b5f70a8c5501`、分支`origin/FJWP2T002`。完成证据保留于D的`research/reports/p02-t002-r2-20261020-02/`，不重新训练或修改。整个T002仍需研究侧验收，执行完成不等于图收益判断；本批次不启动T003/T004。

## 执行位置与比较条件

继续使用已授权D运行根`D:/research-runs/JODBSDFres/benchmark-r2-20261020-01`，C原仓库保留。实际源码基准为D的`815f1cc`，加本次研究调度适配器；固定C的`.venv-pinned/Scripts/python.exe`。训练运行包、生成器和协议字节不改；每组preflight核对运行源码、依赖、输入、图、磁盘与活进程。调度脚本及差异随批次保存。

复用D内已验收`repair-shuffle-v2-20261020-06/graphs/region-shuffle{0,1,2}-a`、`r0-shuffle{0,1,2}-a`，preflight重新校验真实节点/源边、当前生成器及完整审计，不重写图。每组条件在同机、同环境内部可比，saved-only及独立重复检查给出最终证据。r2只是成本规模参考，数据差异不允许将跨组指标直接解释为同条件收益。

## 命令与运行机制

[适配器](../../phases/P02/t002_remaining_batch.py)复用已验证的r2控制器锁、watchdog、冻结身份、检查、进度及恢复调度，覆写数据路由/预检/汇总/发布。新适配器不改变训练实现。先region后r0，均使用新身份：`p02-t002-region-20261022-01`、`p02-t002-r0-20261022-01`。

在D根、显式UTF-8控制台执行（Windows PowerShell脚本保存UTF-8 BOM）：

```powershell
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$env:PYTHONUTF8='1'
# 固定解释器绝对路径见launch.ps1；依次执行以下四个公开调度命令。
python -B research/phases/P02/t002_remaining_batch.py prepare --data-name region --batch p02-t002-region-20261022-01
python -B research/phases/P02/t002_remaining_batch.py prepare --data-name r0 --batch p02-t002-r0-20261022-01
python -B research/phases/P02/t002_remaining_batch.py run --data-name region --batch p02-t002-region-20261022-01
python -B research/phases/P02/t002_remaining_batch.py run --data-name r0 --batch p02-t002-r0-20261022-01 --push-on-success
```

任一步失败就停止后续调度。每组`progress.json`及`controller.json`、各run的`training-progress.json`和`checkpoints/latest.json`为恢复权威，`monitor/`保存命令/退出/耗时。两组共享同一OS所有权锁，始终最多一个训练worker。单fit24小时上限、30分钟无阶段进展暂停；`STOP_NOW`/`STOP_AFTER_CURRENT`沿用原机制。部分epoch不计恢复点；意外中断后新批次显式`--recover-from`，保留旧身份，不能覆盖旧run。恢复分支不作为独立重复。

两组各51项检查全部通过才允许发布：只提交本次适配器/测试、两组批次及60个run可读记录与必要研究记录；不收纳旧历史换行差异和完整数组。完成后推送`origin/FJWP2T002`，回执在r0批次`publication.json`；推送失败保留本地结果，不强推。数组仍留D，无封存或外部租机。

## 预检与成本

适配器/原控制器共12项定向回归通过（2.100秒），覆盖两组完整互斥矩阵、公开CLI/预生成图路由、六汇总及精确51检查门、缺失任一组拒绝发布、源码变更拒绝、旧恢复/锁/失败/看门狗行为。首次测试因临时ROOT不包含脚本路径导致测试夹具异常，修正测试路径后全通过，训练实现未改。真实数据预检和正式启动待执行，完成后在下方写事实。

region粗估3～5小时、r0按节点规模粗估约半小时量级，均不是当前数据实测；预留启动/检查与速度波动，先按组合约4～7小时规划，首几个epoch后校准。r2最近epoch外推与实际整fit曾明显波动，不将短样本ETA当作承诺，也不因此减epoch或调参。无固定截止授权；异常或无有效进展自动暂停告知。

## 当前执行与保存

2026-10-22 00:15两组真实数据/三张预生成图/环境/源码/磁盘/活进程预检均通过，单组manifest各30个唯一run。00:15:34启动region首项`p02-t002-region-20261022-01-region-shuffled0-s0-a`，queue wrapper PID14504、控制器PID23908、worker启动器PID32028；r0尚未运行，队列会在region全通过后继续。实际启动脚本为组合目录内UTF-8 BOM的`launch.ps1`，`launch.json`保存回执，`queue.json`保存两组调度状态。当前PID仅为启动事实，实时须重新检查。

实时以D的两组progress与group launch日志为准；C只保留交接入口。实现、指令和验收材料成功分支才提交推送；当前未声称本批次成功或已推送。未封存，异地备份与远端恢复未核验。

首段实测（00:16:33）：region首项已提交20/200epoch，正在epoch21，133训练chunks；最近epoch约1.87秒，五epoch滚动估计剩余372.7秒（约6.2分钟）。已保存checkpoint，累计写入0.67秒；首段速度快于此前按r2规模粗估，但完整fit、其他方法及r0尚未测量，不据此承诺整批完成时间。
