# 标准目录与记录模板

## 目录

```text
RESEARCH.md
research/
  roadmap.md
  state.md
  decisions.md
  phases/
    P01/
      plan.md
      protocol.md
  runs/
    <run-id>/
      summary.md
      provenance.json
      commands.log
      scripts/
      inputs/
      outputs/
  archives/
    index.md
    <run-id>.tar.gz
    <run-id>.tar.gz.sha256
    migrations/
      <migration-id>.md
```

树中列出的是运行时按需取用的材料，不是每个 run 都必须齐备的清单；无相关内容时不建立空 phase、run 或 migration。

`RESEARCH.md` 是稳定入口，链接到 state、roadmap 和 archive index，说明各记录的职责。当前工作详情仅放 state。是否建新 run 与是否保存整套实验材料是两个判断：建 run 取决于是否存在独立的科研问题，保存整套实验材料取决于这项工作本身是不是一次实验（新预测、改变条件或受控干预）。指标重算、结果比较、旧结果对齐等核验可以只是一份报告，写明被检查对象、来源版本、命令、结果与容差，归属被检查的实验或对应验证流程即可；有独立科研问题的分析保留自己的问题、来源版本、步骤、结果与限制，但不必复制整套实验来源和环境。项目允许增加领域专用材料；这些核心职责和路径保持一致。

`protocol.md` 仅在阶段有需要冻结的实验定义时建立。代码、原始数据和通用指南保留各自职责，不要求搬进 research。大型结果可使用已确定的外部存储，archive index 需记录持久位置、内容校验及恢复方法；不因目录规范而自动上传。

推荐 ID：阶段 `P01`，任务 `P01-T001`，建议/决定 `D001`，运行 `<日期>-<主题>-<序号>`。已有稳定身份保留为 legacy ID 并映射到新 ID；不靠重命名伪造新运行。

## 权威记录

| 记录 | 负责维护 | 不承担的职责 |
| --- | --- | --- |
| roadmap | 研究问题、假设、阶段目标、进入/退出条件 | 当前正在执行哪个命令 |
| phase plan | 阶段状态、任务状态、依赖、验收和计划修订 | 覆盖已运行的协议快照 |
| state | 当前阶段/任务的指针、本轮范围、恢复点、下一动作、未决事项链接 | 再维护一份所有任务的状态表 |
| decisions | 建议的来源、接受情况、决定和计划变更理由 | 代替执行证据 |
| run summary/provenance | 实际执行过程、条件、结果、失败及限制 | 声称后来的提交或备份已发生 |
| archive index | 封存位置、校验、入库和备份的当前核验记录 | 更改运行条件和原始结果 |

状态记录附更新时间。其他文件引用的状态如果是摘要，明确其截至时间并链接权威来源。冲突时核对实际证据、最新明确决定和更新时序，不能仅凭文件名或 HEAD 推断。

## 最小模板

模板中的示例日期、ID 和占位内容需按事实填写。缺失记为未知或不适用，不猜测。

### RESEARCH.md

```markdown
# Research

先读 [当前状态](research/state.md)，再读其指向的阶段计划和证据。

- [总计划](research/roadmap.md)
- [建议与决定](research/decisions.md)
- [归档索引](research/archives/index.md)

任务和阶段状态以 phase plan 为准；state 提供当前工作位置。
运行来源为历史代码身份，无需随 HEAD 更新。
```

### phase plan

```markdown
# P01: 阶段名称

更新时间：YYYY-MM-DDTHH:MM:SS+TZ
阶段状态：active
目标：...
完成条件：...
协议：[protocol](protocol.md)，版本 ...（或不适用）

| ID | 任务 | 状态 | 依赖 | 验收 | 证据/恢复记录 |
| --- | --- | --- | --- | --- | --- |
| P01-T001 | ... | todo | ... | ... | ... |

## 计划修订

- 日期 / decision ID / 变更及原因 / 对已有运行的影响。
```

阶段状态：`planned / active / completed / cancelled`。任务状态：`todo / in_progress / blocked / paused / done / cancelled`。`blocked` 写明具体条件和解除办法；`paused` 表示主动暂停；`cancelled` 保留原因和决定链接。`done` 要有验收依据，阶段 `completed` 要逐项核对阶段完成条件。延期任务仍保留身份和历史。

### state

```markdown
# 当前状态

更新时间：YYYY-MM-DDTHH:MM:SS+TZ
当前阶段：[P01](phases/P01/plan.md)
当前任务：P01-T001（状态以阶段计划为准）
当前执行者/会话：...（无人执行时明确写明）
本次授权范围：...
本轮 run：...（或无）

## 恢复位置

- 已完成到：...
- 现存产物与证据：...
- 最后成功步骤：...
- 仍在运行的进程/机器/会话及最近检查时间：...（或已确认无）
- 剩余工作/失败点：...

## 下一可执行动作

动作：...
前置条件：...
入口/命令/任务链接：...
验收：...

## 待处理事项

- 未决建议 ID、未核验归档、阻塞或材料矛盾的链接。
```

state 始终表示当前已核对的交接位置；每次接手、重要进度变化和收尾都更新。不要仅在最终报告中留恢复点。进程标识只是查证线索，不能凭过期 PID/tmux 名认定仍在运行。

### decisions

```markdown
# 建议与决定

## D001: 标题

提出日期：...
状态：proposed
来源：run/task/讨论；说明证据完整程度
观察与限制：...
建议及理由：...
影响的任务/协议/主张：...
决定与依据：尚未决定
后续变更：...
```

状态为 `proposed / accepted / rejected / superseded`。接受记录依据，例如明确的用户决定、既有协议预定分支或授权范围内的执行选择。区分“待决定”与“已接受但待执行”；后续推翻用 superseding decision 链接，保留历史理由。

### run summary

```markdown
# Run: <run-id>

类型：experiment / analysis / audit
所属任务：...
目的与待回答问题：...
运行状态：prepared / running / succeeded / failed / interrupted / unknown
开始/结束时间：...
协议版本和输入身份：见 provenance.json

## 实际过程

命令/脚本链接、执行到的步骤、耗时、偏离及失败原因。

## 结果与证据

输出位置、可重算的方法、验证记录。

## 解释与限制

事实、候选解释、不能推出的结论。

## 未完成项与新建议

剩余步骤、decision ID、关联任务。

本摘要描述截至结束/封存时的运行情况；后续入库和备份见外部归档索引。
```

### provenance.json

```json
{
  "schema_version": 1,
  "run_id": "<run-id>",
  "kind": "analysis",
  "task_id": "P01-T001",
  "started_at": null,
  "ended_at": null,
  "source": {
    "repository": null,
    "base_commit": null,
    "worktree_status_path": null,
    "relevant_diff_path": null,
    "executed_files_sha256_path": null
  },
  "protocol": {"version": null, "snapshot_path": null},
  "config_path": null,
  "environment_path": null,
  "input_manifest_path": null,
  "commands_path": "commands.log",
  "output_manifest_path": null,
  "limitations": []
}
```

路径以 run 目录为基准。`base_commit` 表示执行源码基准，不是归档 commit，也不是当前 HEAD。按实际执行需要保存相关源码差异、未跟踪脚本或内容哈希；配置和输入清单记录版本/路径/校验，环境记录实际设备和依赖。JSON 使用结构化 API 生成和读取。

字段按运行类型取用，不要求每轮填满全部字段。项目已有 runner 或流程生成 provenance 时，直接引用其输出并沿用其字段类型，不重新推导，也不另建一份。区分两种缺失：本次运行不适用的字段直接省略，不写占位值、也不改变既有字段类型；已定义为未知的字段保留 `null`，只在它影响复现或结论时才在 limitations 中说明。纯诊断或检查类运行只保留回答问题所必需的字段。

输入清单覆盖实际使用的数据或持久版本身份；输出清单记录必要文件的大小和哈希，不要求自行包含自身哈希。正式预测实验保存重算和恢复所需的预测、标签、节点/时间身份、参数及训练/选模记录。其他类型按问题保存必要过程和输出。

### archive index

```markdown
# 归档索引

| Run ID | 类型/任务 | 摘要 | 执行结果（截至） | 保存状态 | 产物与内容身份 | 入库依据 | 备份状态及核验时间 |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 恢复与限制

持久位置、恢复方法、缺失材料和后续分析链接。
```

保存状态用事实描述：mutable、sealed、已本地提交、外部存储已核验等。执行结果是 run summary 的带时间摘要；保存/备份状态由本索引维护。没有确认的远端状态写“未核验”，不同于已确认未推送。历史产物没有统一哈希清单时照实写明，不追溯补算来制造一致性；已封存包的内容身份跟着保存位置走——进 Git 的用提交号，放在 Git 之外的用包外 SHA256。
