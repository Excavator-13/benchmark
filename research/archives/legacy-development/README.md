# 早期开发与核验历史

- [原始缺陷记录](bug.md)：研究起点中的 17 项问题。
- [首次核验](verification_20260921/REPORT.md)：报告、脚本、隔离源码、日志和小规模运行输出整体保留。
- [修复后核验](fix_verification_20260921/REPORT.md)：包含 final 核验及此前探针，原始输出均保留。
- [旧 GPU 下一轮指南](GPU_SERVER_EVOLVEGCN_NEXT_STEPS_GUIDE.md)：针对提交 `950a1d8febbf992b8bda061d35f03107d0b18478` 的历史方案，不代表后续实验已执行。当前复跑约束见[执行指导 §8](../../phases/P01/execution-guide.md#8-什么时候恢复-gpu-实验)。

以上内容原样迁入，历史报告不替代当前软件验证。脚本保留旧目录推导、Windows 绝对路径及会写入原报告目录的行为，不是可直接在此目录重跑的维护入口；复查应从 Git 取原布局到独立工作区。旧 GPU 指南引用的前篇 `GPU_SERVER_EVOLVEGCN_GUIDE.md` 原本就未入库，本次不补造环境安装说明。

历史命令与路径通过[迁移映射](../migrations/20261008-legacy-cleanup.md)解释；已封存的 GPU 结果仍在原 `experiments_archive/`。
