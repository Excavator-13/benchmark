# Implementation Verification

- Change: add-nograph-backtest-folds
- Schema: spec-driven
- Verdict: PASS
- Verified at: 2026-10-17T15:45:01+08:00
- Implementation roots: /Users/watuji/da_chuang/repos/benchmark
- Verified revision: 4dbc1e785a772838d8674bd187e1b353d771ee4f，dirty worktree；以本报告的路径/内容清单为准。

## Summary

本报告已在获授权的主规格同步后重新验证并更新 basis。同步仅改变主规格内容；其余 36 项实现、测试、配置、文档与规划输入保持不变。同步后重新执行严格 change 校验、完整 287 项 discovery 和三 schema 预变更契约比较，全部满足原验收条件。先前同会话 E1/E2 的数值探针证据针对完全相同的实现，按原执行时间保留，未冒称同步后重跑。

独立复验通过。原 V-001..V-004 全部 verified-resolved（同步后完整测试再次覆盖），未发现新的可行动偏差。严格 OpenSpec 校验通过；完整 CPU discovery 287 项，285 通过、2 项因缺少可选 sklearn 跳过；三 schema 主切分预变更契约比较 0 differences。A/B × r0/region/r2 六组独立 development 重复、saved-only recompute/compare、312 项基本数值断言和 9940 项分组/收益数值断言均通过。

验证阶段只更新 verification.md；主规格同步是此前单独获授权的 sync 阶段，归档移动由后续 archive 阶段执行。所有实际折运行使用临时 fixture + development；formal 折能力通过静态根解析/配置/序列化核验，且完整 suite 使用内存 guard 禁止 formal A/B execute_run。未改代码、测试、规划、勾选、implementation-notes、研究记录或既有 run/package/archive；未执行正式科研实验、提交/推送、封存/恢复。按用户 AGENTS.md 的会话启动要求只读 DELEGATION.md，未进入研究侧工作流或写回。此 PASS 只证明本清单对应实现就绪，不构成 T007 实验验收、归档或委托回收。

限制：可选 sklearn 后端动态测试未执行，alpha=lambda*M 的共用标量和后端静态公式已核对；未新增依赖。小 fixture 不能证明真实数据表现或跨折科学收益；继承的 r2-scale 成本记录按既有开发证据复用，不伪称当前新测量。

## Verification Basis

| Path or scope | Revision / content fingerprint / file inventory |
| --- | --- |
| Git HEAD / root | 4dbc1e785a772838d8674bd187e1b353d771ee4f；/Users/watuji/da_chuang/repos/benchmark；dirty worktree |
| 主清单 | 37 个文件，聚合 SHA256 `52d8623d3116b52c997df7d4531d74b77953e02ad31284e7f8195714ac37dc79`；下方完整 path→SHA256 |
| 实现/测试范围 | benchmark/nograph_baseline/ 递归全部非缓存文件；包括新增 untracked test_folds.py、requirements.txt 和既有全部测试 |
| 规划范围 | 当前 changeRoot 递归全部文件，排除 workflow-owned verification.md / implementation-notes.md；覆盖 proposal/design/tasks/delta spec/.openspec.yaml |
| 其他规范/配置/入口 | openspec/specs/nograph-baseline-entry/；AGENTS.md、README.md、.gitignore、openspec/config.yaml、research/phases/P01/{protocol,t007-backtest-guide,execution-guide}.md |
| 预变更对照材料 | scratch/prechange-contract/ 递归全部非缓存文件，122 文件，聚合 SHA256 `db63d4f5be333bb917e1fe414e27e2ecdc782bb0db6b3402723e2af54fcb4141`；与上次报告指纹一致。只运行 compare，未重捕获 baseline |
| 继承的 r2-scale 开发记录 I | 另列 4 文件，聚合 SHA256 `b8df3ed1c43290f13e97011d0bd031a7b91843163385d373ea20c442830ffe6d`；补充只读 basis；历史成本不会成为当前实现的新成本断言 |
| 最终比较 | 主范围重新枚举：路径、37 个指纹、HEAD 不变；参考材料重新枚举 122 文件、聚合不变；4 个历史参考指纹不变，无新增/删除/变更 |

聚合算法为 SHA256(json.dumps(path_to_sha256, sort_keys=True, separators=(',', ':')).encode())；路径为实现根相对 POSIX 路径。每次必须重新递归枚举上述范围来检测新增/删除，排除 __pycache__ 及 .pyc；主范围再排除当前工作流的两个 handoff/report 文件。清单中的 dirty/untracked 内容均按实际文件计算，不能只检查 HEAD。归档移动规划目录时，按所选 changeRoot 对应原逻辑路径比较规划内容。预变更 baseline 位于忽略的本地 scratch；缺失时须承认缺少该项证据，不得用当前代码重捕获后称作预变更依据。

主清单：

```json
{
  ".gitignore": "cb0c94674955b3b98bc662156078e52bb5ffe061d238f9e9879a4cd8f0b4320a",
  "AGENTS.md": "d6b7bb0481e9bae726e6fa91aadb1dcddb9e716f00d1a06954afad73215c77ad",
  "README.md": "6cec354c8b08aed9d4c04e884ee58afd0539bec93f3a1e3937eaf3cc7b395f00",
  "benchmark/nograph_baseline/__init__.py": "d9c569ef793ad4575f7fef38f798f059687e3fd118a471b4d091bfec74c17d78",
  "benchmark/nograph_baseline/__main__.py": "2ecea709492803226e52714799d7c861eb97af44100beeca58f3b7942fed2cfa",
  "benchmark/nograph_baseline/_worker.py": "6b8add701f414edbf1931af2b29cab2231f8460043db7c88285ae5e400ca967b",
  "benchmark/nograph_baseline/artifacts.py": "c116fb5b6ab019a0d5fc74f7528586ec599cb84f785983c4e7ba2173ad30c62d",
  "benchmark/nograph_baseline/baselines.py": "90030ee66ddd71ef18677dc6195fde06ae3574b6298b5ac070a977372e5d293a",
  "benchmark/nograph_baseline/checks.py": "2e3107dbd39a5a3973fecb95c76e3190a72adc72ba94046e536af2c6d6320af3",
  "benchmark/nograph_baseline/cli.py": "ba127970287be4a170eeb576af658cca4e8fee53a4bcc2d75e02d3d1868daf76",
  "benchmark/nograph_baseline/coverage.py": "fad3fa9302e9da44a3cc348977c5f2beaae0951a188cb4cdb983ef0b53177b22",
  "benchmark/nograph_baseline/data.py": "790dd78339e6b7f5476a34a9d272e4fbef1be21075a5b57691e7dff22871cc63",
  "benchmark/nograph_baseline/metrics.py": "476040954e611cafeb05eea71731cd43209ef7601455999f6772c0e21ebf127c",
  "benchmark/nograph_baseline/protocol.py": "7b941e0f097ccd3b3f1a02337fab497dbbdadae3d478cce74011ea5f8591d73b",
  "benchmark/nograph_baseline/requirements.txt": "afd59d6cb60e3f57c3d888b18ccbcd5e25ed3c912d2df2e4d65e772c10298290",
  "benchmark/nograph_baseline/ridge.py": "663c78c60792b696cb08380256a4b098aadb5df1021aca4a7433a8e06437cd5e",
  "benchmark/nograph_baseline/runner.py": "4a068b7aaf30a1eeb51e730a8e3767e2903b25e9be70b745348e9ccc7acb8570",
  "benchmark/nograph_baseline/tests/nb_fixtures.py": "1a17434cb6df00803e3935bb93991e684ae0c796fbcb9f0ddc6896e3686d710d",
  "benchmark/nograph_baseline/tests/test_baselines.py": "6f8692842f8fa1f8c631a5316ebe391cf6b26547a9fc39c35ab33d5dfc65d949",
  "benchmark/nograph_baseline/tests/test_coverage.py": "3cd7fbfcf4199799d9ae7de7933263cba7b7c885779f3a4b490bf0e077149e25",
  "benchmark/nograph_baseline/tests/test_data.py": "96486d36afb845698d8a8983418e8b3e39b86cdc3e1b1cc9b0b7410dce4b8894",
  "benchmark/nograph_baseline/tests/test_folds.py": "da58b1304228bd331784e073f22e2ca74824afa19ffb04c76c27d8c060637751",
  "benchmark/nograph_baseline/tests/test_metrics.py": "fc591ccb3825edace0be9e6da62432e8d4bf6e026d68e6c5c3319f60469f5850",
  "benchmark/nograph_baseline/tests/test_preprocessing.py": "e9296df4b7d4cf75f84526bd766d92324f745eadf1f191111e7c3a95bbde1246",
  "benchmark/nograph_baseline/tests/test_protocol.py": "625fdf38ff54beb94502486b93db8301dda71fa96a0c7d705df1856ceeb7c0dd",
  "benchmark/nograph_baseline/tests/test_ridge.py": "48ef0ed86d7a876c05cce988c7c695acb01804b66f791d7e5b09af35e4e8b280",
  "benchmark/nograph_baseline/tests/test_runner_cli.py": "0f364a4e239bf2d323d13db12831036462be38246c9b4b92c300f71ad9f11b97",
  "openspec/changes/add-nograph-backtest-folds/.openspec.yaml": "4c39792c289debca8ac94a151082057ea2a2931a0cf9910b40c425e493bd3ab9",
  "openspec/changes/add-nograph-backtest-folds/design.md": "123d037fe199a69e59aaee3c8bd1bc677cadc39699cded0bd0a8aeed50036597",
  "openspec/changes/add-nograph-backtest-folds/proposal.md": "84380ec7f7db6c6667d37fcd73f7ad1beef5e81ee9942d4808f99e218fff1bab",
  "openspec/changes/add-nograph-backtest-folds/specs/nograph-baseline-entry/spec.md": "3adff696bcd6469727db5b998da7019b3733d106fe3a91143b2934dfe2a1c0ae",
  "openspec/changes/add-nograph-backtest-folds/tasks.md": "2831d3f91db0c7ac86db0583468dd6be5c6316494ac8bb347c23f6a2ed85d69a",
  "openspec/config.yaml": "2a791b0ccc50e2c2ebbb3ba28692a4ad0e4b6ab94ed2151375ac404d7056e89a",
  "openspec/specs/nograph-baseline-entry/spec.md": "09e697a56bcb76b415e65b1b2048b0ed8063fb4dd34f85ce38785440413e4396",
  "research/phases/P01/execution-guide.md": "9431666c9f7e68a5a8b0dbabc280323ae8029f87d71e60225227beb54a430b5c",
  "research/phases/P01/protocol.md": "b510beb0da9a482507072f78282d06bcf9dc93c3758dd7f16b1f8c326ba1d61a",
  "research/phases/P01/t007-backtest-guide.md": "275b595c513b6385cbdb6eece45852e2f5a503303c73c959a14cfffdcef8a37f"
}
```

继承参考 I（只读、未运行 archived 工作流）：

```json
{
  "openspec/changes/archive/2026-10-11-add-r2-count-baseline/evidence/generate_r2_scale_fixture.py": "ec2e726abda304b8d88005d4c7e7bd2b8f61cf9e5f0ee71344d88962d16c0cde",
  "openspec/changes/archive/2026-10-11-add-r2-count-baseline/evidence/scale-fixture-manifest.json": "d324aab34990975e7e3315dfc8cb3ff16b72255900de04ff7044b07ace6010c3",
  "openspec/changes/archive/2026-10-11-add-r2-count-baseline/evidence/scale-run-cost.json": "1e7aab41cbd7243c605879386f65b8d41441dd32e18153c6dc3ea2b010101ef5",
  "openspec/changes/archive/2026-10-11-add-r2-count-baseline/verification.md": "196444c59f8b436463904c74effd1be01406dfa81f5f6eb6e9eb6da360db6fe4"
}
```

复现主清单：对上表实现、主规范、changeRoot 三个目录 rglob('*')，保留 is_file 且非缓存/排除文件；加上“其他规范/配置/入口”列出的单文件；逐文件 SHA256 并构造相对路径对象。参考清单同法对 scratch/prechange-contract/ 完整递归。同步后开始快照及最终对照副本为 `/tmp/fold-postsync-verify-nc9bqd7j/basis.json`、references.json、inherited.json；它们是可删除的临时核验材料，主实现依据已完整记入本报告。

## Apply Handoff Review

已读取当前 implementation-notes.md、既有 verification.md 和全部 contextFiles。交接的 change/schema/project/HEAD 均匹配；它不提供当前完整 dirty 文件身份，本轮独立快照补足。旧 implementation map 的“283 tests”属于修复前结果，现由其 repair section 和本轮 287 项结果取代；任务勾选及 apply/fix 通过声明不作为独立证据。

| Reminder / claim | Disposition / independent evidence |
| --- | --- |
| No formal fold run；formal 能力静态验证 | 当前代码确认，V-004 verified-resolved；完整无排除 suite 在禁止 formal 折的 guard 下通过；历史失败事实保留在 finding |
| 使用既有预变更材料，不重新 capture | 确认；独立检查 capture_contract.py 的字段值排除清单，E3 compare 0 differences；排除仅自然变化值，字段仍须存在 |
| 严格折身份；main 删除方法保持旧 mismatch | F inconsistent/eval-trace/missing-method tests 与 R adversarial tests 当前全部通过；V-001 修复后的语义负例亦通过 |
| align-v2 在参考读取前拒绝 fold | F/E1 A/B 正常、伪造、缺失、畸形参考；E1 额外禁止参考解析/读字节，V-003 verified-resolved |
| audit 27/36 月只描述；fit18/21 用于拟合/分组 | data.build_fold_audit / runner 数据流与 F audit tests 确认；E1/E2 与原始 prefix/保存掩码一致 |
| 只有 fixture 软件证据，不作科学/真实成本结论 | 遵守；保留 inherited scale 记录为旧测量，不启动新 formal/真实数据实验 |
| optional sklearn 不存在 | 本环境确认，两项 optional tests 跳过；默认 NumPy 实际可运行，静态 alpha 公式确认 |
| None fold 序列化省略；main 不增加空字段 | F serialization/alternation/main schema tests、E3 三 schema 契约确认 |
| main node-errors 列不变；时间/测量值自然变化 | F.FoldMainRegressionTests、E3 文件/字段/列/数组与数值比较确认 |
| 不 commit/push/封存/恢复/研究记账，既有 research 脏文件不归因本变更 | 本验证阶段仅写 verification.md；此前主规格同步独立获授权，测试中合成 Git 仓库操作限临时 fixture；README §4.5 / guide §7 与 help 核对一致 |
| Repair V-001..V-004 | 全部独立静态/动态重验，细节见 Findings，保留原 Repair notes |

## Checks

使用 `/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python`（3.11.17；NumPy 1.26.4、pandas 2.2.3、PyArrow 17.0.0）。没有安装依赖。PyArrow 的沙箱 sysctl CPU-cache 探测告警未阻止任何测试或 Parquet 操作。

| Command or inspection | Result | Notes |
| --- | --- | --- |
| openspec status --change add-nograph-backtest-folds --json；openspec instructions apply --change add-nograph-backtest-folds --json | Ready | spec-driven，context 完整；25/25 只是实现声明 |
| openspec validate add-nograph-backtest-folds --type change --strict --json --no-interactive | PASS | valid=true，0 issues |
| 完整 unittest discovery，使用下方内存 guard，无排除 | PASS | Ran 287 tests in 53.740s，OK (skipped=2)，0 failures/errors；285 passed |
| python -B scratch/prechange-contract/capture_contract.py compare scratch/prechange-contract/baseline | PASS | 0 difference(s)，r0/region/r2 主契约 |
| E1: python -B /tmp/fold-reverify-probe.py | PASS | 六组 fold/schema 独立重复，clip+retain；312 个统计/数组/候选 alpha/MAE/MSE/RMSE 断言；saved-only recompute/compare、消费指纹、输入树不变；V-001/V-003 独立反例拒绝 |
| E2: python -B /tmp/fold-reverify-groups.py | PASS | 在 E1 保存数组上独立重算 9940 个分组/常数/邻居/context/horizon/window/平衡 MAE/收益数值，126 个空组、64 个零参照收益记录；六组均覆盖七种方法及 validation/eval |
| python -B -m benchmark.nograph_baseline run --help | PASS | --fold {A,B}，purpose formal/development；入口文档一致 |
| git diff --check -- benchmark/nograph_baseline README.md research/phases/P01/execution-guide.md | PASS | 无 whitespace error |
| 规范、设计、25 个 task 声明、依赖/计算/保存/检查器数据流检查 | PASS | 11 个 requirement 和 61 个 scenario 全部列于下表，无独立新增科研要求 |
| 初/终 basis 重新枚举与内容比较 | PASS | 主清单/预变更材料/继承参考/HEAD 不变 |

完整 suite 复现（Python 为上述解释器；不写测试文件）：

```python
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path('benchmark/nograph_baseline/tests').resolve()))
from benchmark.nograph_baseline import runner
original = runner.execute_run
def guarded(spec):
    if spec.fold in ('A', 'B') and spec.purpose != 'development':
        raise RuntimeError('formal fold execution forbidden during verification')
    return original(spec)
runner.execute_run = guarded
suite = unittest.defaultTestLoader.discover('benchmark/nograph_baseline/tests')
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful()
```

suite 原始日志：`/tmp/fold-reverify-lp0zzy2q/suite.log`；summary：suite-summary.json。首次测试结束后的 JSON summary 导出因 TestCase skip 对象不可序列化失败；原始 suite 已成功完成，随后仅修复临时摘要导出，没有据此重跑或更改测试。独立 E1 脚本首次对 model key 的假设错误（mean，实际 node_mean），更正临时 probe 后在新 probe2 目录完整运行；该诊断脚本错误不归因实现。

E1/E2 当前输出：`/tmp/fold-reverify-lp0zzy2q/probe2/summary.json`、group-summary.json，以及同目录单份 checker reports。重现 E1：用 F._boundary_signal(8)/F._write_signal_demand 构造 r0、fx.build_fixture(seed=23) 构造 region/r2；A/B 各两次 `_run(... purpose='development', clip_nonnegative=True, retain_candidates=True)`；禁用 data.load_demand、coverage.load_graph_coverage、ridge.fit_numpy/fit_candidates 后逐 run 重算并逐 pair compare；按 Findings 重建矛盾副本和参考拒绝反例。E2 从这些保存数组独立做 float64 误差归约及按 mask/context 切片，按 `(ref_MAE-model_MAE)/ref_MAE` 核对收益。无需保留临时目录即可按这些步骤重现。

## Requirement Coverage

F=test_folds.py；R=test_runner_cli.py；P=test_protocol.py；S=test_preprocessing.py；B=test_baselines.py；D=test_data.py；M=test_metrics.py；G=test_ridge.py，均位于 benchmark/nograph_baseline/tests/。E1/E2 见 Checks；E3=预变更契约 compare；I=继承的 archived r2-scale 记录。引用的所有 suite 用例均本轮重新执行（仅两项 optional sklearn SKIP）。需求行覆盖 SHALL 正文，子行覆盖该规范的每个场景。

| Requirement / scenario | Evidence | Result |
| --- | --- | --- |
| **R1 Independent CPU entry follows the research protocol** | cli.py / runner.RunSpec, execute_run / protocol.resolve_split; F.FoldCliAndSpecTests, FoldEndToEndCliTests; dependency imports inspected | PASS |
| R1.1 Minimal dependency environment | F.FoldEndToEndCliTests 六个公开 CLI/worker development run；默认路径无 sklearn，静态 imports 无 graph/GPU 模块 | PASS |
| R1.2 Supported r2 count request | R.R2DevelopmentRunTests；F.FoldEndToEndCliTests；E1 r2 A/B | PASS |
| R1.3 Unsupported scientific configuration | P.CliSurfaceTests；F.test_unknown_programmatic_fold_fails_before_reservation / test_fold_help_and_invalid_value | PASS |
| R1.4 Explicit and omitted folds | F.FoldCliAndSpecTests / FoldEndToEndCliTests；E3 默认三 schema 契约 | PASS |
| **R2 Demand identity and observations are validated** | data.load_demand, build_audit, build_fold_audit; D canonical/validation/r2 audit tests, F scoped audit tests | PASS |
| R2.1 Valid data arrives out of order | D.CanonicalIdentityTests；R.R2DevelopmentRunTests.test_r2_identity_and_gold_alignment；F CLI canonical-key 检查 | PASS |
| R2.2 Source is invalid | D.NativeValidationTests / CanonicalIdentityTests；R.FailureAndInterruptionTests | PASS |
| R2.3 Multiple r2 contexts share skill IDs | D.R2DemandAuditTests；R.R2DevelopmentRunTests；E1 r2 重复技能、独立 context | PASS |
| R2.4 Distinct audit scopes | F.test_fold_audit_scopes_main_and_full_period_diagnostics / test_fold_groups_before_and_after_main_scope_differ | PASS |
| **R3 Fixed windows isolate target months and preserve rolling origins** | protocol.SplitDefinition / validate_split_definition / build_window_metadata; P.SplitTests, F.FoldDefinitionTests; runner dataflow | PASS |
| R3.1 Protocol split is constructed | P.test_window_count_and_split_membership / test_target_months_are_pairwise_disjoint_and_expected；E3 | PASS |
| R3.2 Second test origin uses known history | P.test_second_test_origin_uses_then_observed_history；S future perturbation tests | PASS |
| R3.3 Fold A enumeration | F.test_fold_a_fixed_definition / test_fold_window_metadata_lists_every_role_and_reason；A fit18, train0..9, validation12, eval15 | PASS |
| R3.4 Fold B enumeration | F.test_fold_b_fixed_definition / test_fold_window_metadata_lists_every_role_and_reason；B fit21, train0..12, validation15, eval18 | PASS |
| R3.5 Invalid fold structure | F.test_modified_definitions_fail_validation / test_overlapping_target_months_fail / test_historical_target_months_are_allowed_as_inputs | PASS |
| **R4 All naive methods and frozen references are reported** | baselines.train_mean / naive_predictions / select_references; runner._selection_payload; B and F naive/reference tests | PASS |
| R4.1 Validation MSE ties | B.ReferenceSelectionTests.test_exact_tie_uses_protocol_table_order / test_selection_uses_validation_mse_only | PASS |
| R4.2 Seasonal prediction uses extra history | B.test_seasonal_naive_uses_last_year_same_month / test_seasonal_reference_is_labeled_extra_history；F seasonal input oracle | PASS |
| R4.3 Fold reference ties and naming | F.test_reference_ties_use_fold_table_order / test_train_mean_names_and_values / test_only_eval_targets_change_selection_is_unchanged | PASS |
| **R5 Normalization counts training observation months exactly once** | ridge.compute_training_stats / TrainingStats / build_design; S and F.FoldFittingStatisticsTests; E1 prefix oracle | PASS |
| R5.1 Overlapping training windows have unequal month multiplicities | S.test_exactly_27_unique_observations / test_train_mean27_uses_unique_training_months | PASS |
| R5.2 Future values change | S.test_later_values_do_not_change_statistics_or_fits；R.R2InformationBoundaryTests | PASS |
| R5.3 Constant training node | S.test_constant_node_effective_std_is_one_and_finite | PASS |
| R5.4 Fold cutoff and unique months | F.test_mean_std_ddof0_constant_and_activity_match_oracle / test_inputs_and_targets_share_fold_statistics；E1 | PASS |
| R5.5 Post-fitting values change | F.test_post_fitting_values_leave_statistics_and_training_parameters；每个 candidate W/b 和训练设计均检查 | PASS |
| **R6 Ridge parameters are shared and selected exclusively on validation** | ridge.fit_numpy / fit_candidates / select_lambda / fit_sklearn; runner selection-before-eval; G, F information-boundary tests | PASS |
| R6.1 Test labels cannot affect selection | G.CandidateSelectionTests；R.R2InformationBoundaryTests.test_test_only_changes_preserve_lambda_and_naive_references | PASS |
| R6.2 Lambda scores tie | G.test_exact_mse_tie_selects_larger_lambda；F candidate tie | PASS |
| R6.3 Sum-loss backend is used | ridge.fit_sklearn 静态 alpha=float(lam)*samples、fit_intercept=True、保存 alpha/M；NumPy scalar/alpha 测试和 E1。可选 sklearn 动态两项跳过，未声称执行后端 | PASS（静态公式；可选后端动态未执行） |
| R6.4 Fold eval labels cannot select | F.test_only_eval_targets_change_selection_is_unchanged / test_eval_targets_are_not_constructed_before_selection | PASS |
| R6.5 Fold sample count and lambda tie | F.test_fold_candidate_scores_use_fold_validation_and_M / test_selection_records_full_fold_contract；E1 双折 M=10*N/13*N 与所有 alpha | PASS |
| **R7 Metrics use common fixed masks and original units** | metrics.split_report / baseline_relative_comparison / node_error_table; M and F metric tests; E1/E2 independent numerical evidence | PASS |
| R7.1 Window RMSE values differ | M.test_overall_rmse_is_not_mean_of_window_rmse；E1/E2 sqrt(mean(error²)) | PASS |
| R7.2 Activity boundaries and an empty group | S.test_four_activity_boundaries；M.GroupedReportTests | PASS |
| R7.3 Fold masks and balanced metrics | F fold-group/main-scope tests；E2 逐组掩码、非空组 MAE 平均、126 个 empty group records | PASS |
| R7.4 Eval grid and zero reference | F.test_fold_metrics_use_fold_groups_and_no_test；M zero reference tests；E2 64 个零参照收益记录为 unavailable/null | PASS |
| **R8 Each run saves recoverable and independently recomputable evidence** | runner serializers / artifacts.py exclusivity, source capture, status / checks.command_recompute; R/F artifact and retention suites; E1/E3 | PASS |
| R8.1 Metrics are independently recomputed | R.CheckCommandTests / R2DevelopmentRunTests；F.test_recompute_fold_without_source_or_refit；E1 全六种 schema/fold saved-only | PASS |
| R8.2 Run is interrupted or collides | R.FailureAndInterruptionTests / RunnerArtifactTests | PASS |
| R8.3 Committed execution sources are reused | R.SourceCaptureDeltaTests.test_clean_tracked_files_are_referenced_not_copied；RepairRegressionTests committed protocol | PASS |
| R8.4 Runtime source or protocol is uncommitted | R.SourceCaptureDeltaTests；RepairRegressionTests patch/binary/mixed/fallback；全部临时合成 Git fixture | PASS |
| R8.5 Git identity is unavailable | R.test_unavailable_git_identity_saves_content_fallback；RepairRegressionTests | PASS |
| R8.6 Candidate retention is reduced by default | R.CandidateRetentionDeltaTests；F 六 CLI 默认候选保留契约 | PASS |
| R8.7 Candidate arrays are explicitly requested | R.CandidateRetentionDeltaTests；E1 六组 retain_candidates + clip 的产物读取 | PASS |
| R8.8 Complete fold evidence | F.FoldRunArtifactTests / FoldEndToEndCliTests；E1/E2 完整开发保存、指标、分组及节点表重算 | PASS |
| R8.9 Fold purposes | F.test_fold_purpose_rules_and_no_formal_start 全部执行通过；root/spec/purpose/payload 静态断言，development formal-root/symlink 负例；V-004 已复验 | PASS |
| **R9 Formal results align with immutable v2 diagnostics** | checks.command_align_v2 / parse_v2_reference; R main/r2 align suites, F fold tests; E1 refusal-before-reference-access | PASS |
| R9.1 Legacy naive value differs | R.CheckAdversarialTests；R2AlignV2Tests.test_metric_discrepancy_is_preserved_without_tolerance_relaxation | PASS |
| R9.2 Independent r2 fixture reference | R.R2AlignV2Tests.test_r2_reference_aligns_without_reading_source_data | PASS |
| R9.3 Reference contains no r2 records | R.R2AlignV2Tests.test_reference_without_r2_records_fails_with_a_report；limited/source mismatch tests | PASS |
| R9.4 Fold alignment rejection | F.test_align_v2_rejects_every_fold / test_align_v2_rejects_fold_before_reference_access；E1 双折 missing/malformed 且禁止参考解析，V-003 已复验 | PASS |
| **R10 Supported datasets produce complete formal artifacts** | runner/artifacts.py; R/F end-to-end and purpose tests, E1/E3; README §4.5 / execution-guide §7; no new scientific acceptance | PASS |
| R10.1 Execute both supported datasets end to end | R.CliEndToEndTests / RunnerArtifactTests；E3 r0/region 完整 main fixture；保留既有证据，不重跑真实 formal 实验 | PASS |
| R10.2 Separately authorized r2 experiment | R.R2DevelopmentRunTests / PurposeDeltaTests；E3 r2；formal 默认根/能力静态验证，实际科研运行保持独立授权 | PASS |
| R10.3 Existing scientific acceptance survives record-format maintenance | E3 三 schema 文件/字段/列/NPZ/数值契约 0 differences；旧 main checks；未改旧 run/package/archive | PASS |
| R10.4 r2 software readiness is independently verified | R r2 development/isolation/check/align suites；E1 r2 A/B；继承的 r2-scale measurement 已记录于 I（121420 节点、development、2.339s、RSS 1300463616 bytes），本轮不把旧成本当新测量 | PASS |
| R10.5 Implementation readiness only | 全套 F/E1/E2/E3；V-001..004 verified-resolved；仅实现就绪，未归档/研究验收/回收委托 | PASS |
| **R11 Saved-result checks produce exclusive compact reports** | checks.resolve_saved_split / _validate_saved_* / command_recompute, compare, align_v2 / exclusive report helpers; R/F adversarial suites and E1 | PASS |
| R11.1 Three saved-only check commands | R.CheckReportContractTests.test_three_checks_write_exactly_one_envelope；F fold checks；E1 consumed hashes/input unchanged，V-002 已复验 | PASS |
| R11.2 Report collision or output inside an input | R.CheckReportContractTests；F.test_corrupt_fold_masks_node_columns_and_collision | PASS |
| R11.3 Invalid saved evidence | R.CheckAdversarialTests / RepairRegressionTests / R2CheckContractTests；F corrupt/conflict/semantic tests；E1 反例均拒绝 | PASS |
| R11.4 Legacy command flags are reused | R.test_legacy_run_id_alias_writes_root_id_json；F.test_previous_report_alias_is_single_exclusive_json | PASS |
| R11.5 Output flag choices conflict | R.test_report_and_legacy_run_id_are_mutually_exclusive | PASS |
| R11.6 r2 recomputation and repetition | R.test_recompute_r2_saved_metrics_without_source_or_refit / test_compare_two_same_seed_r2_runs；E1 r2 双折重复及实际消费指纹 | PASS |
| R11.7 r2 identities or predictions disagree | R.R2CheckContractTests / R2AlignV2Tests；身份/源条件/数值差异均拒绝，容差未放宽 | PASS |
| R11.8 Saved-only fold recomputation and repeat | F saved-only/repeat；E1 六组独立双运行、源数据/图读取与 fit 函数禁止后 recompute/compare ok，输入树不变 | PASS |
| R11.9 Fold mismatch | F.test_compare_rejects_fold_dataset_content_and_seed_mismatches：A/B 与 main/fold | PASS |
| R11.10 Data mismatch | 同一测试：不同 dataset 和同名不同 demand hash（预测相同） | PASS |
| R11.11 Seed mismatch | 同一测试：seed0/1，确定性预测不能替代 seed 身份 | PASS |
| R11.12 Inconsistent fold evidence | F inconsistency/corruption/semantic tests；E1 双折 activity/组矛盾及 ddof=1 均 failed；V-001 已复验 | PASS |
| R11.13 Historical main schema | F.FoldMainRegressionTests；R main recompute/compare/align success/limited/failure；E3 旧 main 契约仍可读取 | PASS |

proposal/design/tasks 额外约束：科学版本 P1-count-L6-H3-v3 与 P01-records-v2 未变；无第三 purpose/新依赖/图预测路径；不做旧 run 迁移。28 个窗口全部保存月份/角色，预测仅为所选 validation/eval；正常主输出保持原 schema。折审计和分组、节点表、summary/measurement 名称一致；formal 默认 research/runs 与 development_backtest 身份使用静态能力证明。窗口新增测试集中在 test_folds.py，虽未放入计划点名的 test_protocol.py，但完整 discovery 已覆盖精确集合、原因及非法结构。README/执行指导包含所需作用域与授权说明。所有 25 个 task 声明在当前范围内已核验，无缺失的强制行为；任务状态及研究状态未改。

## Post-sync Reverification

- Verified at: 2026-10-17T15:45:01+08:00
- Trigger: archive 内联同步更新 openspec/specs/nograph-baseline-entry/spec.md，该文件处于验证清单内；用户明确授权“同步主规格、独立复验后归档”。archive 移动暂停，独立 verify 完成后才可恢复。
- Basis delta: 主规格 SHA256 从 `a5646824185c649c90bde8dc3b39caf59ddf71465286c7be0ddc9aabf7ecd006` 变为 `09e697a56bcb76b415e65b1b2048b0ed8063fb4dd34f85ce38785440413e4396`；其余 36 文件指纹、规划与运行实现、HEAD 不变。同步后检查前完整快照与检查后重新枚举的 37 文件一致；上方主清单/聚合值现已反映同步后的内容。
- Spec inspection: 11 个 delta requirement 的正文与全部 61 个 scenario 在主规格逐块精确匹配；其余 5 个 requirement 与 13 个 scenario 及 Purpose 原样保留。主规格共 16 requirements / 74 scenarios，无 delta 操作标题。归档侧复核所有 delta capability 均已同步。
- Apply handoff: 相同 change/project/HEAD，当前 implementation-notes 内容未改；全部提醒沿原 Requirement Coverage 与当前测试复核，四项 finding 保持 verified-resolved，无新增 pending finding。

| Command or inspection | Result | Notes |
| --- | --- | --- |
| openspec status / instructions apply --change add-nograph-backtest-folds --json | Ready | 同一 repo-local root、spec-driven、25/25 task claims；无阻塞 artifact |
| openspec validate --specs --strict --json --no-interactive | PASS | 4 specs passed，0 failed；仅长正文 INFO 提示，无 error/warning |
| openspec validate add-nograph-backtest-folds --type change --strict --json --no-interactive | PASS | valid=true，0 issues |
| 完整 unittest discovery；原 formal 折 guard；无排除 | PASS | Ran 287 tests；285 passed、2 optional sklearn skips，0 failures/errors，54.558s。观测到的直接 A/B execute_run 调用仅 development；公开 CLI/worker 用例也显式 development |
| python -B scratch/prechange-contract/capture_contract.py compare scratch/prechange-contract/baseline | PASS | 同步后重跑，0 difference(s)；未重新 capture 参考 |
| git diff --check -- openspec/specs/nograph-baseline-entry/spec.md | PASS | 无空白错误 |
| 主清单、参考清单、继承参考与 HEAD 开始/结束比较 | PASS | 37 主文件 inventory/内容、122 预变更参考、4 个继承参考均稳定 |

本轮 suite 日志 `/tmp/fold-postsync-verify-nc9bqd7j/suite.log`；结构化结果 `/tmp/fold-postsync-verify-nc9bqd7j/suite-summary.json`。重现沿 Checks 中完整 discovery guard 脚本，及上述严格校验、预变更 compare；不需要任何正式折执行。312 与 9940 项独立数值断言及 E1/E2 反例报告仍为同步前同会话执行证据；对应运行代码/测试/协议未变，且本轮完整 suite 已重新覆盖全部强制场景及修复项。保留原始 Finding Evidence、Repair notes 与首次 Reverification notes。

- Verdict: PASS

## Findings

以下保留首次失败证据和修复方原始 Repair notes，以免丢失历史；Evidence/Actual/Reproduction 中描述的是修复前状态及行号。当前状态与本轮结果以 Repair status / Reverification notes 为准，四项均 verified-resolved，没有 pending finding。

### V-001: recompute 接受自相矛盾的折分组与标准化元数据

- Category: implementation
- Severity: medium
- Requirement: delta spec “Saved-result checks produce exclusive compact reports” 正文与 “Inconsistent fold evidence”；design §4 保存身份交叉校验；折统计协议 ddof=0 与 activity 分组定义。
- Evidence: checks.py:968 的 _validate_saved_masks 只检查键名；:1232 仅补 shape 检查；:1619 起分别使用保存 activity 和组布尔掩码，不核对二者关系。独立 probe 的 inconsistent-masks.json 返回 status=ok，node_error_comparison 为 112 行、failed_fields=0、categorical_mismatches=0，但该节点 activity_fit18=0.0 且仍在 fit18_high。另一副本只将 selection.json.normalization.ddof 从 0 改为 1，inconsistent-ddof.json 同样 status=ok。_validate_fold_selection:980 未检查 ddof。
- Expected: 仅凭保存材料可判定的固定折科学语义矛盾应产生非零失败及明确字段说明；不需读取源数据或重训。
- Actual: checker 将连续 activity、布尔组和 normalization 记录当作互不约束的数据，重算相同错误材料后报告成功。
- Reproduction: 用 F._write_signal_demand(root, F._boundary_signal(8)) 生成临时 r0 fixture，以 F._run(..., fold="A", purpose="development") 保存完整 run；复制 run。修改 masks.npz 的 nonzero_activity_fit18[1]=0，保持 activity_fit18_high[1]=True 及其他组不变；把 node-errors.parquet 中 node_index==1 所有行的 activity_fit18 同步改为 0，不改 activity_group_fit18（fit18_high）。调用 command_recompute 保存新报告，当前为 ok。独立复制原 run，仅将 selection.json.normalization.ddof=1，重算也为 ok。
- Repair guidance: 对折保存证据增加语义校验：activity 有限且属于合法范围、拟合月分数/阈值与组掩码一致、四组互斥穷尽、掩码类型/身份有效；校验明确保存的固定 normalization 规则（至少 ddof=0）。保留旧 main 兼容语义，不引入源数据依赖。
- Acceptance checks: A/B 正常 saved-only recompute 继续通过；上述两种反例及边界 0、1/3、2/3、1、非法 activity/重叠缺组用独立目的地明确失败，CLI 返回非零；输入树不变；全套及三 schema 主切分契约回归仍通过。
- Repair status: verified-resolved
- Repair notes: checks.py 新增 `_validate_fold_mask_semantics`：activity 必须为有限浮点、位于 [0,1]、为 1/拟合月数的整数倍，四组布尔掩码必须由 activity 按固定边界导出、逐节点恰好分区，常量掩码与 activity 同形且为 bool；`_validate_fold_selection` 另校验 `ddof=0`、`constant_node_std=1.0`、`applied_to_inputs_and_targets=true`、`activity_scope=fit18/21`。test_folds.py 新增 `test_recompute_rejects_contradictory_fold_masks`（activity/组矛盾并同步 node-errors、重叠/缺失组、9/18 错组、NaN/1.2/-0.1、整数 activity、非 bool 组/常量掩码、ddof=1/constant_std=2/applied=false，均使用独立目的地；另一副本经 CLI 返回 1）与 `test_fold_boundary_activity_values_are_accepted`（0、1/3、2/3、1 正常 recompute ok）。主分支持续通过：`python -m unittest discover -s benchmark/nograph_baseline/tests -p test_folds.py` 49 tests OK；guard 下全套 287 tests OK、2 optional sklearn skips；三 schema 预变更契约 compare 0 differences。
- Reverification notes: 2026-10-17 本轮重新审查 _validate_fold_mask_semantics / _validate_fold_selection，并独立重建 A/B 两折 activity[1]=0 但保留 high 组、同步 node-errors 的原反例，两者均 failed，分别说明 fit18/fit21 activity mask 边界矛盾；ddof=1 两折均 failed 并点名 normalization.ddof。F 新增完整非法分数/分组/dtype/常数 std/applied/合法边界及 CLI 非零用例全部通过，E1 输入树不变。verified-resolved。

### V-002: compare 报告未记录实际读取的折元数据与均值指纹

- Category: implementation
- Severity: medium
- Requirement: delta spec “Saved-result checks produce exclusive compact reports” 中 “Reports SHALL identify the actual consumed fold-specific arrays, masks, means and metadata”；design §4、tasks 5.1/5.3。
- Evidence: checks.py:1777 的 COMPARE_CONSUMED_INPUTS 固定为七项；:1820 构建 run_a/run_b_consumed_sha256 后，:1843 读取 windows.json，resolve_saved_split 又读取 provenance.json 并由 _validate_saved_mean:941 打开 TrainMean18/21.npz。独立 A/A-repeat compare.json 为 ok，但两侧 consumed 清单均只含 config/environment/masks/metrics/selection/source-sha256/status，缺少 windows.json、provenance.json 和 models/TrainMean18.npz。预测另有 hashes，不补足这些遗漏。
- Expected: 报告能定位并指纹化当前比较实际依赖的保存证据，包含决定 fold 验证通过与否的文件。
- Actual: 数值比较成功报告的证据身份不完整，不能从该报告审计实际读取的是哪份折窗口/来源/均值材料。
- Reproduction: 两个相同 fixture/fold/seed 的 development run 调用 command_compare，检查 JSON envelope 的 inputs.run_a_consumed_sha256 / run_b_consumed_sha256；以上三个路径缺失。B 同理应为 TrainMean21。
- Repair guidance: 根据实际解析后的身份构造消费清单，或记录 resolver 实际读取的文件；A/B 分别记录正确的均值文件与窗口/来源元数据，保留主切分报告兼容及现有失败报告安全性。
- Acceptance checks: A/B 各一组重复比较，断言两侧清单含这些文件及正确 SHA256；正常比较继续 ok；故意破坏已消费元数据时明确失败且留下安全报告，输入不变。
- Repair status: verified-resolved
- Repair notes: checks.py 用 `_compare_consumed_inputs(identity)` 替换固定 COMPARE_CONSUMED_INPUTS，并在两侧身份解析后计算 consumed SHA256；清单现含 windows.json、provenance.json 及对应 models/TrainMean18.npz、TrainMean21.npz（main 为 TrainMean27.npz），保留原 config/environment/masks/metrics/selection/source/status。test_folds.py 的 `test_compare_consumed_inputs_include_fold_metadata_and_mean` 对 A、B 各一组同 seed 重复比较断言这些文件存在且 SHA256 与磁盘一致，并验证 provenance 折标签冲突时输出单份 failed 安全报告且两侧输入树不变。guard 下全套 287 tests OK、2 skips。
- Reverification notes: 2026-10-17 本轮沿 command_compare → resolve_saved_split → _compare_consumed_inputs 追踪，并对 E1 的 A/B × r0/region/r2 六组独立重复比较逐侧核对 windows.json、provenance.json、models/TrainMean18/21.npz 的实际 SHA256，全部完全相等，status=ok、输入树不变。F 的 provenance 冲突安全失败报告用例重新通过。verified-resolved。

### V-003: align-v2 在识别并拒绝折前读取参考文件

- Category: implementation
- Severity: medium
- Requirement: delta spec “Formal results align with immutable v2 diagnostics” 的每个折明确拒绝；design §4 明确要求“解析 run 身份后优先拒绝 A/B”；tasks 5.5。交接提醒还明确承诺缺失/畸形参考也返回折原因。
- Evidence: checks.py:2232 先检查 reference.exists()，:2235–2238 先 hash/parse reference，:2252 后才判断 identity["is_fold"]。独立 A 和 B 各使用不存在的 missing-reference.log，均返回 failed，错误为 “v2 reference log does not exist: ...”，没有 fold/no fold records 原因；align-missing-A.json / align-missing-B.json 已保留。
- Expected: 对合法保存的 A/B run，先基于其身份拒绝，并说明既有 v2 没有折记录；不靠参考存在或可解析才能做拒绝。
- Actual: 参考的缺失/读取/解析错误可以提前遮蔽折拒绝；代码注释和交接声明的顺序与当前实现不符。
- Reproduction: 使用任意完整 A/B development fixture，调用 command_align_v2(run_dir=..., reference=不存在路径, report_path=新安全路径)。当前报告无折原因。现有 F.test_align_v2_rejects_every_fold 仅提供存在且可解析的参考，未覆盖此顺序。
- Repair guidance: 在参考访问前解析并拒绝 fold；保留安全目的地、单份失败 JSON、明确非零结果及主切分 reference 成功/缺失/limited 行为。
- Acceptance checks: A/B 分别配有效 main、伪造 fold、不存在、不可解析参考，均先给 fold/no fold records 原因且不读取参考内容；run/reference 输入不变；main 既有 align suite 通过。
- Repair status: verified-resolved
- Repair notes: checks.py 的 `command_align_v2` 先读取 run 的 metrics/windows、解析并交叉验证保存身份；发现 A/B 立即以 fold/no-fold-records 原因失败，之后才检查参考存在性、哈希与解析。test_folds.py 扩展 `test_align_v2_rejects_every_fold` 覆盖 A/B × 有效主参考、伪造 fold 参考，并新增 `test_align_v2_rejects_fold_before_reference_access` 覆盖 A/B × 不存在与不可解析参考：均不出现 reference does not exist / invalid JSON line，missing 文件未被创建，malformed 参考字节与 run 树不变；main 既有 align suite 保持通过（guard 全套 287 tests OK）。
- Reverification notes: 2026-10-17 本轮确认身份解析和 fold 拒绝位于 reference.exists/hash/parse 之前；E1 对 A/B 各测缺失与畸形参考，额外禁止 parse_v2_reference 和参考 read_bytes，均给出 fold/no-fold-records 原因，输入树不变；F 的有效主参考/伪造参考用例及 R 主切分 success/limited/missing suites 全部通过。verified-resolved。

### V-004: 新增用途测试实际执行未经授权的 formal 折 run

- Category: implementation
- Severity: medium
- Requirement: delta spec “Supported datasets produce complete formal artifacts” 的 A/B 软件就绪只用 temporary/development，implementation/independent verification SHALL NOT initiate formal fold runs；proposal scope、design §5、task 4.6 指定以根解析/序列化单测覆盖 formal 能力。
- Evidence: test_folds.py:898 的 test_fold_purpose_rules_and_no_formal_start 在 :937–946 调用 _run(... fold="A", purpose="formal", runs_root=root/"formal-temp")；_run:39–62 实际执行 runner.execute_run。临时根使其不写 research/runs，但没有将 purpose 改成 development，也没有阻止拟合/运行。implementation-notes 的提醒已承认该 temp-root formal 执行，与“no formal fold run”声明冲突。
- Expected: 验证 formal 默认根/配置/元数据能力可使用解析与序列化测试；所有实际新折执行必须为 development。
- Actual: 常规全量 unittest discovery 会触发一次正式 purpose 折执行；测试名称和文件头声称不启动 formal，但行为相反。
- Reproduction: 静态追踪上述 test → _run → execute_run 即可确定；本轮出于授权边界排除了这一个测试，没有启动该 formal run。其余 safe purpose 行为已用 execute_run 全程禁用的检查补充验证。
- Repair guidance: 将实际 formal 执行替换为不拟合、不 reserve run 的 root/config/serialization 测试；实际 fixture 完成产物仍使用 development。不要把临时目录作为 formal 授权的替代。修复交接说明，使其准确反映测试行为与历史事实。
- Acceptance checks: 审查所有新增 A/B 调用的 purpose；在禁止 formal A/B execute_run 的 guard 下，无排除地运行完整 discovery；formal 默认 research/runs 和 development_backtest 标记由安全静态/序列化证据覆盖，development 命名空间及 symlink 负例保留。
- Repair status: verified-resolved
- Repair notes: test_folds.py 删除临时根 formal 折 `execute_run`；`test_fold_purpose_rules_and_no_formal_start` 改为不执行 run 的 formal 默认根、`RunSpec` 序列化、`_validate_purpose` 与 fold payload `evidence_role=development_backtest` 静态断言；未知 fold 测试改用 `purpose=development`。在禁止 formal A/B `execute_run` 的 guard 下运行无排除完整 discovery：287 tests OK、2 optional sklearn skips，观测到的 A/B 执行仅为 development；implementation-notes 的 formal 声明已同步更正。未启动任何 formal fold run。
- Reverification notes: 2026-10-17 本轮静态确认原 formal execute_run 调用已删除；formal_spec 仅供序列化/根解析/_validate_purpose/to_payload 使用。未知 fold 测试为 development。对 runner.execute_run 加禁止任何非 development A/B 调用的内存 guard，无排除完整 discovery 287 tests、285 passed、2 optional sklearn skips（suite.log，53.740s），原用途测试也通过；六次公开 CLI/worker 折调用参数亦显式 development。当前交接说明与实现一致；原报告已记录的历史行为不被追溯改写。verified-resolved。

下一步：`$openspec-e13-archive-change add-nograph-backtest-folds`。本 PASS 仅适用于记录的 Verification Basis；相关实现、配置、测试或规划发生修改后需要独立重新验证。归档和研究侧接受/委托回收是后续独立动作。
