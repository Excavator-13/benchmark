# Implementation Verification

- Change: fix-effective-temporal-training-acceptance
- Schema: spec-driven
- Verdict: FAIL
- Verified at: 2026-11-08T11:17:26+08:00
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark` (also the planning root)
- Verified revision: `7ca4f43e588db7adf5b2a6eb751d8918d592346e`; clean implementation/planning worktree throughout the checks. Only this report and its generated state were added by verification.

## Summary

Nine implementation findings remain pending. The corrected immutable best snapshot, training-only RMS, four-window arithmetic, ordinary saved-only comparison and deterministic short recovery work in the existing fixtures. However, readiness accepts incompatible/incomplete evidence, diagnostics modify inputs, formal reporting excludes required repetitions, resource stopping is deferred to epoch boundaries, recovery can reset budgets and omit condition checks, cost estimates omit checkpoint/diagnostic time, context chunk boundaries are not respected, and recomputation trusts reported sample counts.

Strict OpenSpec validation passed. The recurrent suite passed all 103 tests outside the macOS sandbox; the baseline suite passed 287 tests with 2 skips. Passing those suites does not cover the counterexamples below. All additional executions used small synthetic development fixtures and temporary directories. No real demand/graph dataset, real experiment matrix, formal training/report execution, research-state change, archive, commit or push was performed. Pure formal eligibility functions were exercised with fixtures, as in the existing suite. This is a software verdict only.

## Verification Basis

| Path or scope | Revision / content fingerprint / file inventory |
| ------------- | ---------------------------------------------- |
| Current proposal, design, tasks and `specs/recurrent-forecasting-entry/spec.md` | All apply `contextFiles` read; 19 checked tasks treated as claims, not evidence |
| `benchmark/multivariate_time_series/effective_temporal_training.py`, `temporal/*.py`, dedicated tests and README §4.7 | Current files at `7ca4f43`; source traced beyond the apply map |
| Reused `benchmark/nograph_baseline` data, split, metrics, coverage, artifacts and baseline helpers | Current source inspected and full dedicated regression run |
| `research/phases/P02/protocol.md`, inherited P01 definitions | Read-only scientific authority, especially P02 §§3–7; no research-maintainer workflow invoked |
| Repository-wide controlling files, dependencies, skills and change planning | Generated inventory of 600 files; full paths/hashes in `verification-state.json` |

First independent verification: no earlier report/state existed, so no evidence was reused. Full requirement coverage was established, with additional focused counterexamples where the existing tests asserted a narrower behavior. The apply handoff's revision statement is stale: it describes dirty `fa45639`, while the implementation is now committed at `7ca4f43`. Its paths and command setup still locate the implementation correctly; its results were independently rerun.

`verification-state.json` SHA-256: `71cdac4d10f436eb09f76a17c2b019de53c3765d41baa90c7013d6882c001511`.

Snapshot commands, run before and after checks with identical roots/exclusions:

```sh
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py capture \
  --root /Users/watuji/da_chuang/repos/benchmark \
  --exclude 'dataset/**' --exclude 'experiments_archive/**' \
  --exclude 'research/archives/**' --exclude 'research/runs/**' \
  --exclude 'research/analyses/**' --exclude 'research/reports/**' \
  --exclude 'references/**' --output /tmp/e13-temporal-before.json
# Repeat capture with --output /tmp/e13-temporal-after.json.
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py compare \
  /tmp/e13-temporal-before.json /tmp/e13-temporal-after.json
```

Comparison exited 0, `changed: false`; final generated JSON copied to `verification-state.json`. Exclusions omit real datasets, historical experiment/evidence/report trees and unrelated references. Controlling P01/P02 protocol files, current planning, code, tests, configuration and dependencies remain included. Git ignores exclude ordinary caches/scratch; the script automatically excludes workflow handoffs/reports/states. The snapshot is input identity, not coverage proof.

## Apply Handoff Review

`implementation-notes.md` identifies the correct change/project. Reminder dispositions:

| Reminder | Disposition |
| -------- | ----------- |
| No real-data/formal execution; no research acceptance | Confirmed for this verification: only temporary synthetic development executions and pure eligibility checks; no scientific acceptance claimed. The apply's historical execution statement is not independent evidence. |
| Formal report partially exercised | Confirmed limitation. Full formal execution intentionally not run. Pure positive eligibility counterexample exposes V-004; existing refusal-only tests are insufficient. |
| Host memory near 6 GiB; development resource injections | Environmental context, not a software defect. CLI fixtures rerun successfully outside sandbox; no conclusion about real formal capacity. |
| Missing coverage explicitly unavailable | Confirmed by `ReportTests` and source: no implicit all-isolated mask. Acceptable for an unavailable diagnostic; supplied mask identity/group counts tested. |
| Ridge external and identity checked | External ownership confirmed; claimed complete compatibility checking disproved by V-003. |
| Diagnostics owned beneath block and mutable latest pointer | Behavior confirmed, but violates the explicit read-only/single-report requirement: V-001. This is an implementation deviation, not permission to waive the spec. |
| POSIX timing; controller and Windows not exercised | macOS CLI controller exercised by suite. Injected RSS/cost failures and clock probes expose V-005/V-007; native Windows behavior remains unverified. |
| Batch ledger defaults to p02-t006; formal user supplies batch/ledger | Default confirmed. Supplying a different ledger bypasses inherited cost: V-006; caller convention cannot enforce mandatory recovery inheritance. |
| README §4.7 preserves §4.6 numbering | Confirmed. README command surface exists, but diagnostics/recovery claims overstate implementation (V-001/V-006). |

## Checks

Commands run from repository root. `PY` below denotes `/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python` (Python 3.11.17; NumPy 1.26.4, torch 2.14.1, pandas 2.2.3, PyArrow 17.0.0, psutil 7.2.2).

| Command or inspection | Result | Notes |
| --------------------- | ------ | ----- |
| `openspec status --change fix-effective-temporal-training-acceptance --json` and `openspec instructions apply --change fix-effective-temporal-training-acceptance --json` | Complete planning, all_done | Repo-local root; no store selection needed |
| `openspec validate fix-effective-temporal-training-acceptance --type change --strict --json --no-interactive` | PASS | 1/1 valid; no issues |
| `$PY -m unittest discover -s benchmark/multivariate_time_series/tests` | PASS, 103 tests, 57.058 s | Rerun outside sandbox after approval. Initial sandbox run had 9 failures/2 errors from denied psutil sysctl monitoring and downstream paused candidates; those are not counted as implementation findings. |
| `$PY -m unittest discover -s benchmark/nograph_baseline/tests` | PASS, 287 tests, 2 skipped, 43.662 s | Sandbox Arrow CPU-query warnings did not fail tests |
| Additional synthetic probes, reproducible from Appendix A | Confirmed counterexamples V-001…V-009 | Initial pass control, then independent perturbations; no model fitting for diagnostics; injected clocks/RSS for resource/recovery probes |
| Source, tests, public help and README inspection | Partial conformance | All eight commands present; no scheduler; formal positive eligibility, recovery identity and complete cost accounting missing as detailed below |
| Before/after input snapshots | Identical | No relevant input changed during checks |

## Requirement Coverage

Scenario titles below refer to the current delta spec. Passing evidence is retained per scenario, without treating a passing portion as passing the whole requirement.

| Requirement / scenario | Evidence | Result |
| ---------------------- | -------- | ------ |
| Protocol-isolated recurrent training / **Canonical identity across supported schemas** | `data.py::TemporalData`, inherited loader; `CanonicalIdentityTests.test_three_schemas_out_of_order_keep_context_qualified_keys`; region/LSTM and r2/GRU CLI fixtures | PASS |
| Protocol-isolated recurrent training / **Invalid input fails before fitting** | `CanonicalIdentityTests` duplicate/missing/negative/nonfinite/unsupported cases; config and CLI rejection tests | PASS for covered input cases |
| Training-only RMS preprocessing / **Held-out observations change** | `TrainingRmsTests` and `StageBoundaryTests.test_held_out_perturbation_leaves_training_unchanged`; `engine.Trajectory` uses `[N,27]` preprocessing only | PASS |
| Training-only RMS preprocessing / **Constant zero and independent state** | `WindowOptimizationTests` all-zero scale and reordered-window prediction tests; model forward supplies no carried state | PASS |
| Full-window optimization and immutable checkpoint selection / **Best epoch precedes final epoch** | `BestSnapshotTests` controlled early optimum, optimizer/model independence, exact tie and restored score checks | PASS |
| Full-window optimization and immutable checkpoint selection / **Uneven chunks preserve global weighting** | `WindowOptimizationTests` complete-window reference, 19 update ordering and full-gradient clipping; `LongTrajectoryTests` 100-epoch small fixture | Global weighting PASS; context-local chunk constraint FAIL, V-008 |
| Selection and readiness precede four-window test reporting / **Test labels are inaccessible during selection** | `FitArrays.assert_no_test_labels`; `StageBoundaryTests.test_test_labels_unreachable_during_fit_select_and_diagnose` | PASS for fit/select/diagnose; report gate ordering deviates, V-004 |
| Selection and readiness precede four-window test reporting / **Four rolling windows have unequal errors** | `ReportTests.test_four_rolling_windows_and_aggregate_metrics`; starts/months, `[4,N,3]`, multiplicities and aggregate RMSE inspected | Arithmetic PASS; formal eligible seed/repeat reporting FAIL, V-004 |
| Selection and readiness precede four-window test reporting / **Learning-rate tie and missing repeat** | `SelectionTests` ties/missing/role/failed-candidate cases; diagnostics missing b pair case | Ordinary behavior PASS; selection is not bound to supplied readiness runs, V-002 |
| Learning diagnostics implement the existing gates / **Gates pass and fail independently** | `DiagnosticsGateTests` 10%/5%/1%/1e-6 boundary, two-of-three, zero and budget-tail checks | Numeric formulas PASS; complete identity/trajectory enforcement FAIL, V-002/V-003 |
| Learning diagnostics implement the existing gates / **Incomplete or all-zero evidence** | Existing missing a history/pair/baseline and Zero denominator tests; Appendix A deletes b histories and Ridge identities | Existing cases PASS; mandatory missing b/Ridge evidence can still PASS, V-002/V-003 |
| Auditable and independently recomputable outputs / **Source data are unavailable to a reviewer** | `RecomputeTests` source access and torch/pandas import guards; arrays, context/activity/neighbor/horizon/window/clipped metrics inspected | Normal metrics PASS; saved sample counts trusted rather than recomputed, V-009 |
| Auditable and independently recomputable outputs / **Collision or failed seed** | `ArtifactIdentityTests` collision/provenance/source-diff tests; failed candidate/seed and summary retention tests | PASS for covered fixtures; source/environment provenance is captured but not enforced in readiness/recovery, V-002/V-006 |
| Saved-only checks reject incompatible evidence / **Identical outputs conceal a condition mismatch** | `CompareIdentityTests` and `checks._identity_mismatches` seed/data/protocol/config/environment-first checks | compare PASS for covered mismatches; diagnose condition checks FAIL, V-002/V-003 |
| Saved-only checks reject incompatible evidence / **Checks cannot overwrite inputs** | Existing recompute/compare destination tests; Appendix A puts diagnose report inside a consumed a-run | recompute/compare PASS; diagnose FAIL, V-001 |
| Resource preflight and cost limits are enforceable / **Controlled resource or time breach** | `PreflightTests`, `LedgerAndWatchdogTests`, `FitResourceTests`; initial RSS breach, timing and cumulative recovery probes | Detection/ordinary refusal PASS; timely stop, complete estimates and inherited budgets FAIL, V-005/V-006/V-007 |
| Resource preflight and cost limits are enforceable / **A sample resumes without double fitting** | `FitResourceTests.test_cost_sample_continues_the_same_trajectory`, `LongTrajectoryTests`; per-block unknown costs retained | Same trajectory PASS; sample timing/remaining cost is understated, V-007 |
| Atomic recovery is separate from best-model selection / **Interrupted execution matches uninterrupted training** | `ResumeTests` parameter/best/validation equality and parent byte invariance; atomic publication failure test | Numerical/atomic behavior PASS; condition and time-budget inheritance FAIL, V-006 |
| Atomic recovery is separate from best-model selection / **Legacy or damaged checkpoint** | `CheckpointTests` and preflight corrupt recovery fixture; kind/version/missing required fields inspected | Legacy/truncated/best-as-last rejection PASS; source/environment mismatches are not checked, V-006 |
| Software readiness stays separate from research execution / **Development invocation targets the formal namespace** | `CliContractTests` direct/symlink output alias rejection; development default and formal-control checks | PASS for fit/select/report namespace guards; diagnose bypasses normal reservation/namespace contract, V-001 |
| Software readiness stays separate from research execution / **Independent software verification completes** | 103 + 287 fixture/regression tests; Appendix A independent counterexamples; current report/state | FAIL: software readiness not established; no real scientific conclusion or task acceptance |
| Promised work outside isolated scenarios | Design §§1–6, tasks 2.1/3.3/4.4/5.2/5.4/6.2; README help and handoff | Context chunking, read-only diagnostics, resource/cost enforcement and recovery claims contradicted by findings below; no legacy runner/T009 changes attributed to this implementation commit |

## Findings

All findings are new, category `implementation`, and `pending`. No earlier repair notes exist.

### V-001: Diagnose modifies consumed evidence and bypasses report isolation

- Category: implementation
- Severity: high
- Requirement: Saved-only checks reject incompatible evidence; scenario “Checks cannot overwrite inputs”; design §5 and task 4.4.
- Evidence: `runner.py:801` `run_diagnose` creates `<input block>/diagnostics/<id>/`, writes multiple files and overwrites `latest-diagnostics.json`. Unlike recompute/compare, it never calls `checks.reject_destination` against consumed runs/block/Ridge. Appendix A observed both `block_changed=true` and `report_inside_run_created=true` when `--report` targeted an a-run. Missing block input raises `SelectionError` with no external failure report. `cli.py:628` imports runner, which imports torch and later captures pandas/Arrow environment, despite the saved-only check contract.
- Expected: Read saved inputs without modification, publish one exclusive compact report outside all consumed directories, reject bad destinations before side effects, retain failure report at a usable destination. Reporting should consume explicitly identified frozen diagnostics rather than require mutating the selection input.
- Actual: Multiple input-local outputs and a mutable pointer are part of normal execution; an external report can also be written inside an input; errors can omit the required report.
- Repair guidance: Make diagnose follow the same destination validation/read-only failure-envelope contract as the other saved checks; reconcile downstream diagnostics consumption and README accordingly within the existing spec.
- Acceptance checks: Snapshot all consumed inputs before/after success, incomplete input, existing report and inside-input destinations (including aliases). Inputs must remain byte-identical; only one valid external report may be created. Exercise saved-only execution with model/source-data interfaces unavailable and required dependencies blocked as appropriate.
- Repair status: addressed-awaiting-verification
- Repair notes: Moved saved-only execution into `temporal/diagnostics.py`; `cli.py` dispatches without importing runner/model dependencies. Diagnose now validates resolved destinations, keeps all consumed block/run/Ridge inputs unchanged, and writes one exclusive external envelope including failures. `runner.py` consumes an explicit frozen diagnose JSON and no longer creates input-local diagnostics or a latest pointer; README and CLI fixtures updated. `tests/test_temporal_repairs.py` checks byte snapshots for success/incomplete/invalid destinations and aliases, failure-report retention, and a subprocess with torch/pandas/Arrow/psutil imports blocked. Invalid previously unrelated-winner fixtures now assert failure. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Appendix A `diagnose_writes_inputs`, `diagnose_missing_input`; existing tests assert pointer behavior but do not authorize it.

### V-002: Readiness can pass unrelated selections and incomplete or incompatible b trajectories

- Category: implementation
- Severity: high
- Requirement: Learning diagnostics implement the existing gates; Selection and readiness precede four-window test reporting; Saved-only checks reject incompatible evidence; P02 §§4–6.
- Evidence: `diagnostics.py:45` drops environment/source/split identity from loaded evidence; `gate_completeness:127` checks only a histories; `gate_repetition:477` compares a/b condition IDs and selected fields but not protocol/environment/full effective settings or b history completeness. `build_diagnostics:744` uses selection only for model/dataset/hash, without binding winner learning rate and winner-as-a. Appendix A starting with the suite's passing saved fixtures still returns `pass` after (independently) changing the selected learning rate to 3e-3 while all runs use 1e-3, deleting every b history and setting their controls incomplete, or changing b0 protocol SHA/environment.
- Expected: Readiness must establish the frozen configuration/winner link, all required complete finite trajectories and matching data/protocol/effective execution conditions before interpreting gate numbers.
- Actual: `learning_ready=true` is possible for the counterexamples. Condition IDs that exclude source/environment cannot substitute for those checks; actual protocol hashes are available but ignored in repetition checks.
- Repair guidance: Validate saved evidence against selection and recomputed effective identities; check all required trajectories and same-condition execution metadata, while retaining explicit incomplete/failure reasons.
- Acceptance checks: Add focused saved fixtures for each independent perturbation above, swapped seed-0 winner, cross-seed data/config differences and b nonfinite/missing histories. None may return ready; valid same-condition fixtures must still pass all numeric boundary checks.
- Repair status: addressed-awaiting-verification
- Repair notes: `diagnostics.py` now checks both a/b complete finite histories, all required fixed-score blocks, effective protocol controls, recomputed condition identities, full configurations and source/environment/split/data identities across required runs. A separate identity gate binds seed-0 a to the actual frozen winner-as-a and learning rate. Synthetic fixtures now carry valid full protocol configs/identities. New regressions independently perturb selected rate/winner, b history/nonfinite values/controls/protocol/environment, cross-seed data/config and condition IDs; none returns ready; valid boundary fixtures still pass. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Appendix A `wrong_selected_learning_rate`, `missing_b_trajectories`, `different_b_protocol_environment` all observed `pass`.

### V-003: Missing Ridge identity is accepted as compatible evidence

- Category: implementation
- Severity: medium
- Requirement: Learning diagnostics implement the existing gates, including baseline node/month/source/preprocessing/selection/split compatibility and incomplete missing evidence.
- Evidence: `diagnostics.py:626` compares dataset/data/key fields only **if present**; split/month/preprocessing can also be absent; any nonempty selection object is accepted. Appendix A supplies only `{"selection":{"anything":true},"validation":{"MAE":6,"MSE":36}}`; overall diagnostics returns `pass`. The result claims node/month/source/split compatibility although none was supplied.
- Expected: Required compatibility evidence must exist and be validated, with missing fields explicitly incomplete. Neural and Ridge scalers may differ, but each must have the documented compatible definition and selection conditions.
- Actual: Omission bypasses validation and unlocks readiness.
- Repair guidance: Require and validate the stated baseline identity/selection/preprocessing fields; do not infer compatibility from absence or an arbitrary selection object.
- Acceptance checks: Independently omit or corrupt each required identity, split/month, preprocessing and selection field; all incomplete/incompatible cases must remain non-ready; compatible Ridge still need not beat the neural model.
- Repair status: addressed-awaiting-verification
- Repair notes: `diagnostics.py` requires Ridge data/key/dataset identities and validation-start/month identity; validates the inherited training-only 27-month per-node standardization (ddof=0, constant std=1), validation original-unit MSE lambda selection and larger-lambda tie rule. Both supported key-hash names normalize to the same check. README documents the evidence schema. Regression cases independently omit/corrupt each identity, split/month, preprocessing and selection field; compatible Ridge remains valid without a neural-beats-Ridge condition. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Appendix A `ridge_without_identity=pass`; the existing mismatch test only supplies an explicitly incorrect field, missing the omission path.

### V-004: Formal report eligibility excludes valid repetitions and reads test arrays before the gate

- Category: implementation
- Severity: high
- Requirement: Selection and readiness precede four-window test reporting; independent seeds 0/1/2 a/b; post-report test repetition checks; design §1/P02 §§4–5.
- Evidence: `report.py:255` requires every formal `run_dir` to equal the seed-0 screening winner directory. A pure eligibility fixture with full protocol config seed 1, passing diagnostics and every a/b state completed is rejected solely as “not the selected winner.” The same rule rejects every b directory, preventing formal test repetition comparisons. Separately `runner.py:1064` calls `data.report_arrays()` before evaluating/raising formal blockers at lines 1083–1098.
- Expected: Frozen learning rate governs each required seed/repetition; each eligible trajectory reports its own selected checkpoint after validating its membership/conditions and frozen readiness evidence. Failed prerequisites must be checked before constructing test labels.
- Actual: Only the original seed-0 a trajectory can formally report, and even a refused request has already constructed test arrays.
- Repair guidance: Validate the requested trajectory against the selected block/required a/b evidence and its own best checkpoint, rather than equating it with the screening winner; move formal prerequisite checks before test array construction.
- Acceptance checks: Pure fixture eligibility for seeds 0/1/2 a/b must accept valid linked trajectories and reject unrelated ones. A report-array access sentinel must remain untouched on failed prerequisites. Development fixtures should report both repetitions and compare their test evidence without formal research output.
- Repair status: addressed-awaiting-verification
- Repair notes: `report.py` checks membership of each seed/repetition in frozen diagnostics, selected rate/effective config and its saved evidence fingerprint; it no longer equates every trajectory with the seed-0 directory. `runner.py` verifies prerequisites before loading demand or constructing report arrays, then reports the requested trajectory's own best. New pure eligibility tests accept all six linked a/b trajectories, reject unrelated/changed evidence, and keep the report-array sentinel untouched on refusal. Existing development report/compare regressions remain passing. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Appendix A `seed1_formal_blockers`; existing tests cover refusal and development report comparison, not positive multi-repetition formal eligibility. No formal execution was run.

### V-005: Resource breaches do not stop work until an epoch completes

- Category: implementation
- Severity: high
- Requirement: Resource preflight and cost limits are enforceable; design §6 explicitly requires monitoring/stopping beyond epoch-end checks.
- Evidence: `resources.py:386` watchdog records a flag; `runner.py:390` checks it only in `after_epoch`, after recovery publication. `engine.py:318` never checks it between windows/chunks. `cli.py:461` controller loop only terminates on fit timeout, never on its watchdog's RSS/monitor-failure flag. Appendix A starts with an already sampled RSS of `8 GiB + 1`, yet performs 19 updates and completes epoch 1 before pausing.
- Expected: Once a sampled breach or monitoring failure is known, stop the affected computation promptly and retain the preceding complete recovery point; the stop cannot depend on finishing a potentially long epoch.
- Actual: An entire epoch continues even when the violation was known before its first update; controller sampling does not enforce its own flags.
- Repair guidance: Connect independent monitoring to a bounded cancellation/stop path for ongoing training and controller work. Preserve last complete recovery and account discarded partial work; do not publish a newly completed over-limit epoch as the only reaction.
- Acceptance checks: Inject RSS/monitor failure before training and during a multi-window/slow epoch; assert no further bounded work after detection, correct previous recovery preservation and consumed cost. Exercise the controller path as well as the helper watchdog.
- Repair status: addressed-awaiting-verification
- Repair notes: `engine.py`/`model.py` accept cancellation checks at bounded window/chunk/inference/backward/step/publication boundaries. `runner.py` records pauses without running further post-stop inference, retains the preceding complete checkpoint and bills partial work. `cli.py::supervise_worker` enforces sampled RSS/monitor-failure and time flags independently, terminating an unresponsive worker with a bounded wait. Initial RSS/monitor-failure fixtures now assert zero updates; a mid-epoch RSS regression asserts exactly 21 updates and byte-identical prior recovery; the controller termination fixture verifies retained ledger time. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Appendix A `initial_rss_breach` observed 19 updates; existing resource test explicitly expects epoch-boundary delay and therefore does not establish the spec's stop behavior.

### V-006: Recovery does not enforce source/environment or inherited trajectory budgets

- Category: implementation
- Severity: high
- Requirement: Atomic recovery is separate from best-model selection; Resource preflight and cost limits; design §2 and P02 §6 (single-fit time cannot reset on resume).
- Evidence: `recovery.py:50` checks saved parent/checkpoint config, data and condition but never compares source/environment with current execution. `condition_identity` excludes both. Budget checks use the caller's `ledger_path`, with a nonexistent file treated as a fresh 12 hours; stored checkpoint ledger references are not enforced. Appendix A's exhausted original ledger raises `RecoveryError`, but changing only the path gives 43,200 remaining seconds. Changing parent provenance's source and torch version still loads. `runner.py:253,395` and the CLI reset the fit clock per child; injected parent=3500 s plus child=200 s completes even though the trajectory consumed 3700 s against a 3600 s limit.
- Expected: Same effective source/environment, inherited ledger/batch identity and spent single-trajectory and cumulative active budgets, validated before recovery executes. A new ID or ledger path must not reset time.
- Actual: These recovery conditions are accepted or reset independently of the saved checkpoint's references.
- Repair guidance: Bind source/environment and ledger/batch identity to recoverable state; compare current conditions and inherit measured parent-chain fit/batch time. Reject missing/replaced/unverifiable budget evidence instead of treating it as unused allowance.
- Acceptance checks: Source/environment mismatch must reject before creating a child; new/missing/different-batch ledger must not bypass exhausted budget; 3500+200 s must stop/refuse under the 3600 s trajectory limit. Retain current deterministic resume equivalence and parent-byte invariance tests.
- Repair status: addressed-awaiting-verification
- Repair notes: `checkpoints.py` binds source/environment and ledger/batch/execution references into last state. `recovery.py` validates those bindings and current runtime conditions before child reservation, requires the inherited ledger path/ID/batch and completed measured entries, and inherits all trajectory execution time. `runner.py` retains billing.json time floors and parent-chain IDs (including partial work), checks inherited single-fit time, and gives children the prior complete recovery state. Tests reject changed current/parent source/environment, missing/new/replaced/different-batch ledgers, lost measured time and exhausted budgets; 3500+200 seconds pauses at the 3600-second trajectory limit. Existing deterministic resume and parent-byte invariance tests pass. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Appendix A `fresh_ledger_resets_budget`, `resume_accepts_different_environment_source`, `single_fit_time_resets_on_resume`; no source code or real environment was changed for these probes.

### V-007: Cost samples omit checkpoint/diagnostic time and setup, and active billing ends too early

- Category: implementation
- Severity: high
- Requirement: Resource preflight and cost limits; epochs 6..10 **complete-epoch** median, sample <=15 min including setup/I/O/diagnostics, cumulative active work including checks; P02 §6/design §6.
- Evidence: `engine.py:389` measures epoch duration through validation, before `_record_score` and `on_epoch_complete` publication. `runner.py:349` sets setup from an optional request defaulting to zero instead of measuring it. At epoch 10 `cost_gate` gets no `sample_seconds`, so `resources.py:522` sums the incomplete epoch durations rather than elapsed setup/sample time. Appendix A's publisher advances an injected clock 2 s per checkpoint: after 11 epochs clock=22 s, while `cost.json` reports sample=0, median=0 and estimated fit=0. `runner.py:449` records ledger time before final checkpoint/array/report writes; report/select/diagnose/check time is not billed by this ledger. A controller termination can also bypass worker end-of-fit recording entirely.
- Expected: Measure setup and complete epoch/sample work, use those measurements in stop decisions, and retain all active execution cost (including failed/interrupted work and required checks) without relying on successful worker return.
- Actual: A supposedly conservative estimate can be zero despite measured checkpoint work; ledger omissions undercount the batch budget.
- Repair guidance: Define end-to-end timing boundaries around the promised work, use elapsed sample time and real setup measurements, and persist/bill active work through final publication and interruption paths. Preserve measured/estimated distinction and per-block unknowns.
- Acceptance checks: Inject setup, diagnostic, checkpoint and final-write delays separately; verify sample limit/epoch median/fit estimate and total ledger charge include them. Terminate a fixture worker and verify its active time survives. Retain same-trajectory sample continuation.
- Repair status: addressed-awaiting-verification
- Repair notes: `engine.py` measures complete epochs through fixed-score diagnostics and atomic checkpoint publication; runner measures setup and passes actual elapsed sample time to the cost gate. `epoch-timing.json` retains post-publication durations for recovery. Fit billing lasts through final outputs/failures; the controller persists a shared ledger identity before launching and heartbeats active elapsed time through termination. Linked live-batch select/diagnose/report/recompute/compare work is accounted outside consumed evidence; offline saved checks still work without their original ledger. Delay-injection regressions verify setup=4 s, sample=25 s and median=2 s for the controlled example, sample/setup stop, final-write timeout/full billing, saved-check billing and terminated-worker billing, while same-trajectory continuation still passes. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Appendix A `checkpoint_timing_excluded`; existing cost tests inject scalar setup but do not show measured production timing includes it.

### V-008: Training chunks can cross context boundaries

- Category: implementation
- Severity: medium
- Requirement: Protocol-isolated/full-window optimization; design §3 explicitly says chunks must not merge contexts; task 2.1 and P02 §3.
- Evidence: `engine.py:144` `chunk_ranges` knows only total node count/chunk size. `squared_error_sum` uses it without node/context keys. For canonical contexts of sizes 2 and 3 and chunk size 3, Appendix A observes model batches `[1,1,2]`, `[2,2]`, merging the tail/head of distinct contexts.
- Expected: Visit canonical contexts in order and chunk within each context while accumulating all contributions with denominator N*3 before one clip/step.
- Actual: Global contiguous chunks preserve sorting and approximate numerical weighting but violate the deliberate context boundary constraint.
- Repair guidance: Pass/derive context boundaries and chunk within each context; preserve global denominator, full-gradient clip and exactly one update per window.
- Acceptance checks: Unequal multi-context fixture with a chunk size crossing a boundary must never mix contexts; retain global-reference update agreement and 19-update order tests.
- Repair status: addressed-awaiting-verification
- Repair notes: `engine.py::chunk_ranges` accepts context identities and training supplies canonical `FitArrays.node_keys[:,0]`; chunks stay within each context while retaining the N*3 denominator, complete-gradient clipping and one step/window. An unequal 2+3-node multi-context spy asserts unmixed batches, and different chunk sizes agree with the full-window update reference with 19 updates. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Appendix A `chunks_cross_contexts`; existing uneven-chunk numerical tests do not assert context membership.

### V-009: Recompute accepts false saved sample counts

- Category: implementation
- Severity: medium
- Requirement: Auditable and independently recomputable outputs; “Source data are unavailable to a reviewer,” including sample/group counts and all four windows; task 4.4.
- Evidence: `checks.py:446` assigns `recomputed["sample_counts"]` directly from saved `report.json`. Appendix A generates a real small development report containing 48 test elements, changes only `metrics.sample_counts.elements` to 999999 and runs saved-only recompute; it returns `pass`.
- Expected: Derive counts from saved arrays/keys/windows and compare them with reported counts; inconsistent evidence must not pass independent recomputation.
- Actual: The same untrusted count is compared with itself, so a false required report field passes.
- Repair guidance: Recompute sample counts from validated array dimensions and audit other fields copied from the report rather than independently established.
- Acceptance checks: Independently corrupt every sample-count field and verify non-pass reports while inputs stay unchanged; valid `[4,N,3]` reports must reproduce all counts/metrics without source/model access.
- Repair status: addressed-awaiting-verification
- Repair notes: `checks.py` derives all five sample-count fields from validated prediction/gold shapes and canonical keys, and requires all four protocol test starts. The regression independently corrupts windows/nodes/horizon/elements/per-window-elements, checks a non-pass report with unchanged inputs, then restores the valid report and confirms saved-only recomputation passes. Other numeric metrics remain derived from arrays/masks rather than copied counts. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Appendix A `recompute_accepts_false_sample_count`: actual=48, claimed=999999, status=pass.

## Next Action

Run `$openspec-e13-fix-change fix-effective-temporal-training-acceptance` for pending implementation findings, then independently verify again. No planning ambiguity is needed to explain these counterexamples. Do not archive on this basis. Native Windows monitoring and real-data/real-cost/learning-readiness acceptance remain outside this software verification and cannot be inferred from eventual fixture success.

## Appendix A: Reproducible Independent Probes

The Python block below is the exact additional verification script (not an implementation test or acceptance waiver). Copy it to `/tmp/e13_temporal_probes.py`, run from repository root with the `PY` interpreter above. It imports existing synthetic fixture helpers, writes only temporary development artifacts, and cleans fixture directories. Output paths vary; decisive statuses/counts are recorded with each finding. No dependency on the original temporary script is needed.

<!-- BEGIN INDEPENDENT PROBE -->

```python
import copy
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'benchmark/multivariate_time_series/tests'))
import temporal_fixtures as fx
from test_temporal_selection_diagnostics import DiagnosticsGateTests
from benchmark.multivariate_time_series.temporal import checks, diagnostics, engine, protocol, recovery, report, resources, runner

out = {}
with tempfile.TemporaryDirectory(prefix='e13-temporal-') as temp:
    root = Path(temp)
    case = DiagnosticsGateTests()
    case.setUp()
    try:
        a, b = case._all_pass()
        ridge = case._compatible_ridge()
        selection = fx.selection_document(root)
        def diagnose(aa=a, bb=b, rr=ridge, ss=selection):
            return diagnostics.build_diagnostics(selection=ss, block_id='block', a_runs=aa, b_runs=bb, ridge=rr)
        out['diagnostics_control'] = diagnose()['status']
        out['ridge_without_identity'] = diagnose(rr={'selection': {'anything': True}, 'validation': {'MAE': 6., 'MSE': 36.}})['status']
        wrong = copy.deepcopy(selection)
        wrong['winner']['learning_rate'] = .003
        wrong['winner']['run_dir'] = '/unrelated-winner'
        out['wrong_selected_learning_rate'] = diagnose(ss=wrong)['status']
        short_b = copy.deepcopy(b)
        for evidence in short_b.values():
            evidence['history'] = {'epochs': []}
            evidence['protocol_controls'] = {'complete': False}
        out['missing_b_trajectories'] = diagnose(bb=short_b)['status']
        path = Path(b[0]['run_dir']) / 'provenance.json'
        saved = fx.read_json(path)
        saved['protocol']['sha256'] = 'changed-protocol'
        saved['environment'] = {'packages': {'torch': 'different'}, 'machine': 'other'}
        fx.write_json(path, saved)
        changed_b = dict(b)
        changed_b[0] = diagnostics.load_run_evidence(path.parent)
        out['different_b_protocol_environment'] = diagnose(bb=changed_b)['status']

        block = root / 'block'
        block.mkdir()
        fx.write_json(block / 'selection.json', selection)
        before = fx.tree_digest(block)
        inside = Path(a[0]['run_dir']) / 'checker-output.json'
        result = runner.run_diagnose({'block_dir': str(block), 'a_runs': {s: e['run_dir'] for s,e in a.items()}, 'b_runs': {s: e['run_dir'] for s,e in b.items()}, 'report_path': str(inside), 'diagnostics_id': 'probe', 'purpose': 'development'})
        out['diagnose_writes_inputs'] = {'report_inside_run_created': inside.exists(), 'block_changed': before != fx.tree_digest(block), 'status': result['status']}
        missing_report = root / 'missing-input-error.json'
        try:
            runner.run_diagnose({'block_dir': str(root / 'missing'), 'report_path': str(missing_report)})
        except Exception as error:
            out['diagnose_missing_input'] = {'error': type(error).__name__, 'failure_report_written': missing_report.exists()}
    finally:
        case.tearDown()

    sel = fx.selection_document(root, winner_run_dir=root / 'seed0')
    diag = {'status': 'pass', 'learning_ready': True, 'selection_sha256': sel['selection_sha256'], 'summary': {'complete_comparison': True}}
    states = {s: 'completed' for s in protocol.SEEDS}
    out['seed1_formal_blockers'] = report.formal_report_blockers(purpose='formal', config=protocol.FitConfig(seed=1), selection=sel, diagnostics=diag, run_dir=root/'seed1', a_states=states, b_states=states, winner_run_dir=root/'seed0')

    data = fx.in_memory('r0', 4, seed=3)
    breach = fx.fit_run(root, run_id='initial-rss-breach', data=data, epochs=2, sampler=lambda: {'rss_bytes': protocol.MEMORY_STOP_BYTES + 1})
    out['initial_rss_breach'] = {'status': breach['status'], 'completed_epoch': breach['completed_epoch'], 'updates': fx.read_json(Path(breach['run_dir'])/'gradients.json')['total_updates']}
    def interrupt(trajectory, epoch, window):
        if epoch == 2 and window == 2:
            raise engine.PauseRequest('fixture_interrupt', {})
    ledger_path = root / 'ledger.json'
    parent_result = fx.fit_run(root, run_id='parent', data=data, epochs=3, sampler=lambda: {'rss_bytes': 0}, after_update=interrupt, ledger_path=ledger_path)
    parent = Path(parent_result['run_dir'])
    ledger = resources.Ledger(ledger_path, batch_id='p02-t006')
    ledger.record(execution_id='spent', run_id='earlier', seconds=protocol.BATCH_SECONDS)
    try:
        recovery.load_parent(parent, ledger_path=ledger_path)
    except Exception as error:
        out['exhausted_original_ledger'] = type(error).__name__
    accepted = recovery.load_parent(parent, ledger_path=root/'new-ledger.json')
    out['fresh_ledger_resets_budget'] = accepted['remaining_batch_seconds']
    provenance = fx.read_json(parent / 'provenance.json')
    provenance['environment']['packages']['torch'] = 'incompatible'
    provenance['source'] = {'commit': 'different', 'runtime_sha256': 'different'}
    fx.write_json(parent / 'provenance.json', provenance)
    out['resume_accepts_different_environment_source'] = recovery.load_parent(parent)['completed_epoch']

    class Clock:
        value = 0.
        def __call__(self): return self.value
    clock = Clock()
    def slow_publish(path, payload):
        from benchmark.multivariate_time_series.temporal import checkpoints
        clock.value += 2.
        return checkpoints.publish_last(path, payload)
    timed = fx.fit_run(root, run_id='checkpoint-timing', data=data, epochs=11, sampler=lambda: {'rss_bytes': 0}, publish=slow_publish, clock=clock)
    cost = fx.read_json(Path(timed['run_dir'])/'cost.json')
    out['checkpoint_timing_excluded'] = {'clock_seconds': clock.value, 'sample_measured_seconds': cost['sample_measured_seconds'], 'epoch_median_seconds': cost['steady_state_median_seconds'], 'estimated_fit_seconds': cost['estimate_seconds']}

    clock1 = Clock()
    clock1.value = 0.
    def stop_near_limit(trajectory, epoch, window):
        if epoch == 2 and window == 2:
            clock1.value = 3500.
            raise engine.PauseRequest('fixture_interrupt', {})
    budget_ledger = root / 'fit-budget.json'
    timed_parent = fx.fit_run(root, run_id='near-fit-limit', data=data, epochs=3, clock=clock1, sampler=lambda: {'rss_bytes': 0}, after_update=stop_near_limit, ledger_path=budget_ledger)
    clock2 = Clock()
    clock2.value = 0.
    def resumed_work(trajectory, epoch, window):
        if epoch == 2 and window == 0:
            clock2.value = 200.
    timed_child = fx.fit_run(root, run_id='past-fit-limit', data=data, operation='resume', parent_dir=Path(timed_parent['run_dir']), clock=clock2, sampler=lambda: {'rss_bytes': 0}, after_update=resumed_work, ledger_path=budget_ledger)
    out['single_fit_time_resets_on_resume'] = {'parent_seconds': clock1.value, 'child_seconds': clock2.value, 'limit': protocol.FIT_SECONDS, 'child_status': timed_child['status']}

    import numpy as np
    import torch
    calls = []
    class Spy(torch.nn.Module):
        def forward(self, inputs):
            calls.append(inputs[:, 0, 0].tolist())
            return inputs[:, 0, :].expand(-1, 3)
    contexts = np.asarray([1., 1., 2., 2., 2.])
    engine.squared_error_sum(Spy(), np.repeat(contexts[:, None], 6, axis=1), np.zeros((5, 3)), 1., 3, 15)
    out['chunks_cross_contexts'] = calls

    count_fit = fx.fit_run(root, run_id='count-fit', data=data, epochs=1, sampler=lambda: {'rss_bytes': 0})
    count_block = root / 'count-block'
    fx.write_json(count_block/'selection.json', fx.selection_document(root, winner_run_dir=Path(count_fit['run_dir'])))
    count_report = runner.run_report({'purpose': 'development', 'block_dir': str(count_block), 'run_dir': count_fit['run_dir'], 'run_id': 'count-report', 'output_root': str(root)}, data=data)
    report_dir = Path(count_report['run_dir'])
    doc = fx.read_json(report_dir/'report.json')
    actual_count = doc['metrics']['sample_counts']['elements']
    doc['metrics']['sample_counts']['elements'] = 999999
    fx.write_json(report_dir/'report.json', doc)
    checked = checks.run_recompute(run_dir=report_dir, report_path=root/'count-check.json', argv=['fixture'])
    out['recompute_accepts_false_sample_count'] = {'actual_elements': actual_count, 'claimed_elements': 999999, 'status': checked['status']}

print(json.dumps(out, indent=2, sort_keys=True))
```
<!-- END INDEPENDENT PROBE -->
