# P02-T009 软件就绪回收核对

类型：check / 软件研究侧验收。日期：2026-11-07，Asia/Shanghai。
对象：OpenSpec `add-occupation-skill-graph-audit`。本轮只读核对实现与证据，更新研究记录；未运行构图、预测或软件测试，不改归档报告。

## 核对依据和结果

- 活跃变更目录已不存在；[归档验证](../../../openspec/changes/archive/2026-11-07-add-occupation-skill-graph-audit/verification.md)为 `Verdict: PASS`，验证时间为 2026-11-07T12:29:20Z，验证实现基准为 `3039f9c1176ccfcfb156b6aafdf7a92456530a6d`。
- 当前接收提交为 `4bacc5e621d8ff16240d2021a55cac064cd24f2d`。与验证基准的 Git diff 只有 OpenSpec 归档移动、验证记录／状态及主规格同步；`benchmark/`、README 和构图协议无差异。
- [归档 verification-state.json](../../../openspec/changes/archive/2026-11-07-add-occupation-skill-graph-audit/verification-state.json)的 SHA256 为 `bc801a7e3816dfb0bced00be6c4a491fb7571795f98f2fd635bb8de2bda6fb8b`，与 PASS 报告记载一致。
- 对该清单中 `benchmark/occupation_skill_graph/`、`benchmark/nograph_baseline/`、`benchmark/graph_value_skeleton/`、`benchmark/graph_method/` 下的源码／测试，以及 README、忽略规则、构图协议和依赖／配置作当前字节 SHA256 比对：105/105 一致。当前新包没有清单之外的 Git tracked／非忽略 untracked 文件。
- 清单中的 5 个提案／设计／任务／规格／元数据路径已随归档移动；按同一变更名映射到归档位置后逐字节哈希一致。主规格的 Requirements 正文与归档 delta 的 ADDED Requirements 正文一致。目录移动不是实现变化。

核对使用 Python 标准库 json/hashlib 读取既有清单并计算所列路径当前字节；使用 `git ls-files --cached --others --exclude-standard benchmark/occupation_skill_graph` 检查额外文件，使用 `git diff --name-status 3039f9c1176ccfcfb156b6aafdf7a92456530a6d HEAD` 区分归档移动与实现修改。未重新生成完整验证清单，未重新执行独立验证。

## 验收范围

采用上述独立验证的行为证据：当前新包 fixture 全套、四项原始发现的独立重现均通过，V-001 至 V-004 全为 verified-resolved，无未决发现。旧两套 benchmark 测试的既有证据由验证者按适用输入复用，本轮不将其写成自己新跑的测试。

该证据覆盖训练期数据与原生精度、两个关系分数、全零／确定性平分、共享映射与非连续技能身份、趋势未知及异质性、资源／监控失败、路径边界、自包含产物和只读检查。实现以新增独立包为主，旧预测／数据入口保持原行为。

[原实现说明](../../../openspec/changes/archive/2026-11-07-add-occupation-skill-graph-audit/implementation-notes.md)的基准／测试计数是 apply 时的历史交接，后续修复与验证以归档 PASS 报告为准，不修改旧交接去伪造同步时间。

研究接受决定见 [D040](../../decisions.md#d040-t009-构图审计软件就绪验收与委托回收)。这份核对只支持软件就绪，不冻结真实图，不代表 T009 或 P02 完成。

## 剩余研究工作与限制

完整发布数据的源／三目标身份预检、两候选构图、结构／趋势／成本审计及冻结决定尚未执行。真实规模耗时／RSS、原生 Linux／Windows 监控和跨平台近似平分行为仍未实测；抽样 RSS 不是操作系统硬内存上限。

下一动作按 [构图协议](../../phases/P02/t009-graph-protocol.md)和 README 新入口，在已接受软件上开展 D039 授权范围内的本机真实审计，使用唯一 run ID、1800 秒阶段限时与 2 GiB RSS 停止线。首次完整执行用于测量成本，不引用 fixture 耗时冒充预计完成时间。训练和新图预测收益仍留到 T006/T007/T010。

本轮在软件回收处结束；无本轮 run、无后台 worker、无新图或预测结果。保存事实见[归档索引](../../archives/index.md#p02-t009-构图审计软件交付与研究侧回收2026-11-07)。
