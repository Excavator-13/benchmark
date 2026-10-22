# P02-T002：检查点验收与 r2 重启批次

批次：`p02-t002-r2-20261020-02`。更新：2026-10-21 00:25，Asia/Shanghai。

## 验收与条件可比性

研究侧按 D029 接受检查点恢复能力。[独立报告](../../../openspec/changes/archive/2026-10-20-add-resumable-training-checkpoints/verification.md)为 PASS，归档前核对 63 项当前文件指纹全部一致，三项发现均已验证解决。三种方法各自连续训练及37→113→200 epoch中断恢复的当前进程矩阵通过（664.204秒）；参数、Adam、RNG、完整历史和预测精确一致，最后epoch恢复不增加优化更新。独立14项定向测试与4项junction路径断言通过。原Windows符号链接创建受账户权限限制，未声称原symlink创建测试通过。主规格普通校验5/5通过；额外strict全规格校验仅因已有长需求文本警告失败，本次六项新增需求及变更strict校验通过，不改旧需求消除警告。

该软件验收不等于r2或T002完成。科学条件仍为原CPU单线程、GRU(1,32)+Linear(32,3)、3459参数、Adam、19训练窗口、200总epoch、验证MSE最早平分选模；重算1e-12、独立重复归一化1e-6。检查点保存当前和最佳模型、优化器、随机状态、历史、累计实际训练/验证耗时，以manifest最后发布；最多保留最近两代。只恢复完整验证过的epoch，部分epoch的工作需要重做；共享训练祖先的分支不计独立重复。

与旧诊断为有条件可比：科学配置、输入、图生成语义、依赖保持不变，新增持久检查点/观测与存储开销，不沿用旧短样本成本作为实测值。预生成图的生成器源码未改，D预检仍须重新核对实际输入和完整图身份。

## 原中断与新范围

原批次`p02-t002-r2-20261020-01`首项在7042.593秒后退出，0/30完成，无模型/Adam/RNG检查点，不能恢复旧epoch。新批次保留原run、日志、进度和图字节，以新的30个run身份从头训练。原证据不覆盖、不重新标记成功。D历史106个文件与C副本的差异只涉及换行，保留其现有字节并排除本轮同步/发布清单。

沿用D028及用户继续执行授权：只做r2的30次200epoch独立拟合和51项检查（30重算、15重复比较、6三图汇总），不做r0/region、T003/T004或图收益判断；成功后提交推送`origin/FJWP2T002`，数组留D盘，无封存/云资源授权。

## 执行与恢复接口

执行根：`D:/research-runs/JODBSDFres/benchmark-r2-20261020-01`。基准HEAD：`2ca56dd68fb72ff632f9612dc1dbbc6eee66b723`加本次已验证源码差异；源码材料由各worker provenance及批次preflight保留。固定解释器为C原仓库`.venv-pinned/Scripts/python.exe`，临时文件和训练输出均在D盘。C仅保存本报告入口，实时权威在D。

```powershell
& 'C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark/.venv-pinned/Scripts/python.exe' -B research/phases/P02/t002_r2_batch.py prepare --batch p02-t002-r2-20261020-02 --recover-from research/reports/p02-t002-r2-20261020-01
& 'C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark/.venv-pinned/Scripts/python.exe' -B research/phases/P02/t002_r2_batch.py run --batch p02-t002-r2-20261020-02 --push-on-success
```

预检核对源码、固定依赖、输入、预生成图、磁盘、OS所有权锁和活worker。当前旧批次映射预计30 fresh、0 reuse、0 resume；以`recovery-plan.json`实际记录为准。以后再次中断须另建批次、显式`--recover-from`，由身份门和saved-only核验决定复用/恢复，不能重跑同名run。

`progress.json`为控制器心跳及完成数，`research/runs/<id>/training-progress.json`为逐epoch/阶段进度，`checkpoints/latest.json`为已提交恢复点；心跳不代表epoch完成。`controller.json`/`launch.json`记录实际PID与命令，`monitor/`保存子进程退出证据。单fit24小时上限、30分钟无阶段进展暂停；任一身份/非有限/重算/重复失败即停。`STOP_NOW`终止所拥有worker并暂停，`STOP_AFTER_CURRENT`在进程边界停止。不降低epoch或用测试成绩早停。

首次完整epoch后才外推单fit；所有剩余方法有实测前整批ETA明确不可用。旧约20小时预测已被首次近两小时仍未完成的事实削弱，不能继续当作可靠完成承诺。按当前epoch与检查点I/O逐步校准，异常或无有效进展先暂停报告。

## 当前执行

2026-10-21 00:22:51 Asia/Shanghai实际启动首项`p02-t002-r2-20261020-02-r2-shuffled0-s0-a`。控制器PID10380，worker启动器PID17516，wrapper PID10312；这些仅为历史启动身份，实时须复核。00:24检查为running、0/30，epoch1 training阶段、988 chunks，checkpoint=null；未完成首epoch，不能声称已保存恢复点或有可靠ETA。后台不依赖聊天持续占用，异常按watchdog暂停。

D同步28文件成功，原中断现场50文件字节不变，回执`rollout.json`；preflight为ok，恢复映射30fresh。首次直接启动在活进程检查处因PowerShell输出编码与Python UTF-8不符而暂停，未建正式run；`startup-encoding-failure.json`及原日志保留。一次不带BOM的UTF-8 wrapper亦未启动Python，诊断保留。最终使用带UTF-8 BOM脚本并显式设置`[Console]::OutputEncoding`，真实活进程检查通过并启动训练；没有修改独立验收的运行源码。成功启动证据为`launch-utf8-bom.json`/`launch-utf8-bom.ps1`/`controller-utf8-bom.stdout.log`和`controller.json`。直接CLI命令需要由同样的UTF-8控制台运行。

只有`completion.json`存在且30次及51项门全部通过才能声称r2完成。

首次epoch成本观测（00:25:40）：已完成2epoch，正在epoch3，最近epoch39.749秒，剩余197/198epoch尺度的fit估计由进度文件给出7833.200秒（约2小时11分），只含训练/验证/checkpoint观测，不含后续检查。累计checkpoint写入0.0727秒。前两个epoch样本不足，暂不据此给整批完成承诺；self/graph仍无本批次完整测量。已有已提交checkpoint摘要`acb86fbe4f1c32893fa69fa4b666838e4408a5673c489117164910aaf7a52ea9`，当前恢复点随D的latest.json更新；此摘要为当时观测，不要求后续保持不变。

保存：验收实现及记录在C本地工作区，并已同步D；正式数组只留D。成功分支才提交推送，具体身份从Git历史及D的`publication.json`读取，不为回执另补提交。未封存，异地备份和远端恢复未核验。
