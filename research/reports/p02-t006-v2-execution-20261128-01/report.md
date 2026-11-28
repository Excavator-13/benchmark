# P02-T006 v2 r0/GRU 首个候选执行记录

类型：experiment。所属任务：P02-T006。
日期：2026-11-28，Asia/Shanghai。执行者：本会话 Codex，当前 Windows 11 本机 CPU。
科学版本：`P2-effective-training-L6-H3-v2`。

## 执行范围

完成 seed 0、学习率 `1e-3`、角色 screening/a 的第一个 v2 正式候选。使用通过的 Windows fresh preflight、原 batch `p02-t006-effective-20261108-01` 和 ledger `f93290f346bc47e9914be45203c5edc3`。v1 结果未续训或覆盖，训练期间没有使用测试标签。

首次启动在 epoch 0 前因 sandbox 对 Windows 临时目录的访问被拒而失败，留下独立 failed run `p02-t006-r0-gru-v2-s0-lr1e3-a-20261128-01`，并将 10.69 秒计入 ledger。该运行没有训练轮次。随后使用主机权限重新 fresh preflight，通过后以新身份 `p02-t006-r0-gru-v2-s0-lr1e3-a-20261128-02` 运行完整轨迹，保留第一次失败现场。

## 正式运行结果

最终 run 状态为 `completed`，完成全部 200 epoch 和 3,800 次更新，selected checkpoint 为 epoch 200。验证 MSE 为 206,599.6338，验证 MAE 为 109.6180。初始验证 MSE 为 16,863,986.0912，初始验证 MAE 为 1,279.1244。数据为 r0/count，2,335 nodes；使用训练数据计算的 RMS scale 为 3,505.72。源码基准 commit 为 `4993778f0fb2a11cbfc0339ad265f489479a1d3c`，运行环境及文件身份详见 run provenance。

第 10 轮成本门通过，样本覆盖 epoch 1–10，样本时间 16.838 秒。epoch 6–10 完整 epoch 时间中位数为 0.57215 秒，v2 单次完整拟合保守估计为 312.04 秒。单次预算投影 328.88 秒，低于 3,600 秒门槛；七次拟合矩阵投影 3,187.30 秒，低于剩余批次预算。RSS 监测和 8 GiB 停止线由正式 runner 执行，运行正常结束。

## 证据位置与账本

- 正式 run：[summary](../../runs/p02-t006-r0-gru-v2-s0-lr1e3-a-20261128-02/summary.md)、[report](../../runs/p02-t006-r0-gru-v2-s0-lr1e3-a-20261128-02/report.json)、[cost](../../runs/p02-t006-r0-gru-v2-s0-lr1e3-a-20261128-02/cost.json)、[provenance](../../runs/p02-t006-r0-gru-v2-s0-lr1e3-a-20261128-02/provenance.json)、[history](../../runs/p02-t006-r0-gru-v2-s0-lr1e3-a-20261128-02/history.json)
- 成本门预检：[本次通过的 fresh preflight](../p02-t006-execution-20261108-01/preflight-r0-gru-v2-20261128-03.json)
- 失败启动：[epoch 0 前失败的 run](../../runs/p02-t006-r0-gru-v2-s0-lr1e3-a-20261128-01/report.json)
- 原 batch ledger：[ledger.json](../p02-t006-execution-20261108-01/ledger.json)

完成后 ledger 共有 13 条记录，measured/replayed 累计 176.9635 秒，另有 900 秒保守预算扣除，有效累计为 1,076.9635 秒，剩余 42,123.0365 秒。

## 第二候选与学习率选择

随后在同一 Windows 主机和原 batch/ledger 上重新预检，通过后运行 seed 0、学习率 `3e-3`、screening/a 候选 `p02-t006-r0-gru-v2-s0-lr3e3-a-20261128-01`。轨迹完成 200 epoch / 3,800 updates，selected checkpoint 为 epoch 70；验证 MSE 为 243,982.3691，MAE 为 125.6994。第 10 轮成本样本为 10.8082 秒，epoch 6–10 的中位数为 0.22135 秒，完整拟合保守估计为 126.15 秒。单次成本门与剩余批次投影均通过。

通过正式 saved-evidence `select` 按验证原始单位 MSE 比较两候选后，筛选冻结为学习率 `1e-3`。胜者为 run `p02-t006-r0-gru-v2-s0-lr1e3-a-20261128-02`，验证 MSE 206,599.6338；`3e-3` 候选以 MSE 较高被淘汰。未读取测试数据，seed 0 胜者按协议作为 repetition a 链接复用，没有重新拟合。

- 第二候选：[run report](../../runs/p02-t006-r0-gru-v2-s0-lr3e3-a-20261128-01/report.json)、[cost](../../runs/p02-t006-r0-gru-v2-s0-lr3e3-a-20261128-01/cost.json)、[provenance](../../runs/p02-t006-r0-gru-v2-s0-lr3e3-a-20261128-01/provenance.json)
- 冻结选择：[selection.json](../p02-t006-execution-20261108-01/blocks/p02-t006-r0-gru-v2-20261128-01/selection.json)、[selection report](../p02-t006-execution-20261108-01/blocks/p02-t006-r0-gru-v2-20261128-01/report.json)

第二候选与 selection 完成后，原 ledger 共 16 条记录，measured/replayed 累计 236.9174 秒，保守扣除 900 秒，有效累计为 1,136.9174 秒，剩余 42,063.0826 秒。

## 限制与下一动作

已冻结的 seed 0 学习率选择只是有限矩阵的筛选结果，不代表学习有效性、a/b 重复或 T006 的研究验收。下一步按选择结果补 seed 1/2 的 a 和 seed 0/1/2 的 b。没有生成四窗口测试或访问测试期。

两个生成的 `summary.md` 末尾均含有通用的 “Development evidence” 提示语，与它们的 `purpose=formal`、正式完整控制及 `status=completed` 元数据不一致。该文字是摘要模板标签，与 run 的 formal 配置和机器报告矛盾，故此处以 command、config、provenance、status、report 和 cost 文件作为身份及结果依据；模板措辞问题单独披露。
