# 条件核对

- 原服务器保留情况及本次核对时间：用户陈述原云服务器保留；2026-10-18 08:05–08:31 (+08) 在 ~/benchmark 核对。无法证明物理机从未迁移。
- HEAD 与源码/原始数据检查：HEAD 950a1d8febbf992b8bda061d35f03107d0b18478，与指导基准一致；git status --short 仅未跟踪 evolvegcn-region-count-results.tar.gz 与 logs/。§5 预检 exit 0、preflight.json=passed：源码与两个 parquet 的 hash-object 逐文件比对、data/count/region.json 可由源数据重建且相等、16,345 节点 × 36 月、窗口数 [19,1,4]、逐窗口输入与标签逐元素相等、邻居覆盖 2,185、验证选定 NaiveRef=LastValue、旧 seed 0/1 结果重算与 metrics.json 一致。
- GPU 型号 / 驱动 / torch CUDA：Tesla T4；驱动 535.216.01；CUDA 12.2；torch 2.3.0+cu121。
- 同一物理 GPU 是否能确认：不能。两次 nvidia-smi 的 Bus-Id 都是 00000000:00:08.0（虚拟化直通常见值，不构成同一性证据）；显存上报 15360 MiB → 16384 MiB（差 1 GiB）；ECC 列显示 0 → Off。其余差异只有采集时间、温度 37→36C、功耗 11→10W。
- 完整 pip freeze 差异及 Python 版本限制：diff -u old-pip-freeze.txt pip-freeze.txt 无输出，依赖集与版本逐字节一致；8 项核心包断言通过。python 3.8.20、pip 25.0.1。限制：归档 freeze/nvidia-smi 是 2026-10-02 12:53 从该机采集的快照，不是原运行时刻的记录，故只能证明"环境自该快照以来未变"。
- 判断：可比旧条件（有条件）。理由：依赖集逐字节一致、设备型号/驱动/CUDA、源码与数据逐文件一致、预检全部断言通过。限制：无法确认同一物理 GPU；显存上报差 1 GiB 与 ECC 显示差异无法解释；旧运行确切 Python 补丁版本无记录。若同 seed 复跑超出 §7 的 1e-4 归一化 MAE 容差，先按这些平台差异排查，不并入初始化方差。
