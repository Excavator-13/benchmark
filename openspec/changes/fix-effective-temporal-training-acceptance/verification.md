# Implementation Verification

- Change: fix-effective-temporal-training-acceptance
- Schema: spec-driven
- Verdict: FAIL
- Verified at: 2026-11-08T11:54:31+08:00
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark` (also planning root)
- Verified revision: `7d2d85d5aaa8b010de9a74549b66a9ea9b58716b`; clean implementation/planning worktree during checks. This verification updates only this report and generated state.

## Summary

V-001 through V-009 are independently **verified-resolved** for their recorded defects. Two new implementation findings remain pending: the formal RSS stopping line can be raised above the frozen 8 GiB limit (V-010), and stages connected to a live batch ledger run successfully after its 12-hour budget is exhausted (V-011). Software readiness therefore remains FAIL.

Strict OpenSpec validation passed. The full current recurrent suite passed **120 tests in 60.059 s**, including the repair regressions, on the recorded CPU environment with host process-monitor access. Additional independent probes confirmed both the repaired behavior and the remaining failures. The prior independent 287-test baseline regression (2 skipped) remains applicable and was reused: baseline code/tests, dependencies, scientific definitions and execution environment are unchanged. Repair-owned claimed results were not substituted for independent evidence.

All runs used small synthetic/temporary development evidence. Formal eligibility/control checks were pure fixture calls; no formal fit/report execution, real demand/graph read, experiment matrix, research-state edit, archive, commit or push occurred. Native Windows monitoring and real hardware cost/learning-readiness acceptance remain outside this software verification.

## Verification Basis

| Path or scope | Revision / content fingerprint / file inventory |
| ------------- | ---------------------------------------------- |
| All apply context files: proposal, design, tasks and delta spec | Read current files; snapshot confirms byte-identical to previous independent basis. All 19 checked tasks remain claims, not evidence. |
| Recurrent entry, temporal helpers, dedicated tests and README §4.7 | Current repair commit `7d2d85d`; changed code/tests inspected and complete recurrent suite independently rerun. |
| Reused baseline helpers/tests, P01/P02 scientific definitions, dependencies and controlling files | Unchanged in scripted input comparison; previous baseline regression evidence retained. |
| `verification-state.json` | Generated inventory: 601 files; SHA-256 `67dc7fe78d4853d738978b09e20b047e4a0dd774ed4a91960f8c754422c76934`. |

Incremental verification from the prior state: its SHA-256 `71cdac4d10f436eb09f76a17c2b019de53c3765d41baa90c7013d6882c001511` matched the prior report before comparison. Script comparison exited 1 (changed): repairs touched README, temporal runtime/helpers and dedicated fixtures/tests, adding `test_temporal_repairs.py`; planning, baseline code/tests and dependencies were unchanged. Because changes span diagnostics, training cancellation, cost accounting and recovery, all recurrent tests and all nine finding scopes were rechecked, with nearby resource-control probes added. Reuse is limited to still-applicable independent baseline evidence; all changed behavior was checked this round.

Snapshot commands use the same root/exclusions as the previous basis:

```sh
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py capture \
  --root /Users/watuji/da_chuang/repos/benchmark \
  --exclude 'dataset/**' --exclude 'experiments_archive/**' \
  --exclude 'research/archives/**' --exclude 'research/runs/**' \
  --exclude 'research/analyses/**' --exclude 'research/reports/**' \
  --exclude 'references/**' --output /tmp/e13-temporal-reverify-before.json
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py compare \
  openspec/changes/fix-effective-temporal-training-acceptance/verification-state.json \
  /tmp/e13-temporal-reverify-before.json
# Capture again with identical arguments and --output /tmp/e13-temporal-reverify-after.json.
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py compare \
  /tmp/e13-temporal-reverify-before.json /tmp/e13-temporal-reverify-after.json
```

Before/after comparison exited 0, `changed: false`; final script-generated snapshot copied to `verification-state.json` only after comparing the old state. Exclusions omit datasets, historical evidence/report/archive trees and unrelated references. Relevant current code, tests, scientific protocols, dependencies, configuration and planning remain covered. Git ignores handle scratch/caches; workflow reports/handoffs/states are automatically excluded. The inventory identifies inputs rather than proving coverage.

## Apply Handoff Review

`implementation-notes.md` identifies the correct project/change but remains at its original apply revision (`fa45639` plus dirty implementation). It is stale about current revision and some corrected behavior; current code and repair notes were checked directly. Repair notes below are preserved verbatim as claims/history; their commands are not this verifier's results.

| Reminder | Current disposition |
| -------- | ------------------- |
| No real-data/formal execution; no research acceptance | Confirmed for this verification; no scientific acceptance/task completion claimed. Apply's historical action claims are not independent evidence. |
| Formal reporting only partially exercised | Full formal run remains intentionally outside scope. Current pure fixture eligibility accepts all six a/b members and rejects unrelated/changed evidence; refusal sentinel is checked before test arrays (V-004 resolved). |
| Host memory near startup threshold | Environment-dependent; CLI fixtures use development-only resource readings. No assertion of real formal capacity. Host psutil access used for this round's suite. |
| Missing coverage optional and explicit | Confirmed: no implicit all-isolated mask; supplied context-qualified masks/counts covered by current regression suite. |
| Ridge external and identity checked | Confirmed for mandatory identity/preprocessing/selection omission/mismatch paths; V-003 resolved. External scientific evidence must still be supplied by research execution. |
| Diagnostics inside block and latest pointer | Stale/inapplicable after repair. Diagnose now emits one external report and leaves consumed evidence unchanged (V-001 resolved). README now documents explicit `--diagnostics` report consumption. |
| Cost/monitor tests and platform limits | macOS CLI controller plus injected failure/clock tests independently pass. Timing omission and delayed stopping repaired; new threshold/live-stage budget gaps are V-010/V-011. Windows native execution not performed. |
| Batch default and explicit formal ledger | Default confirmed; recovery now enforces bound ledger identity and trajectory time (V-006 resolved). Live check-stage budget enforcement remains V-011. |
| README numbering | §4.7 retained; original §4.6 unchanged. Current descriptions of stage/recovery changes read and compared with CLI. |

## Checks

`PY` = `/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python`, run from repository root. Same recorded environment as previous independent checks: Python 3.11.17, NumPy 1.26.4, torch 2.14.1, pandas 2.2.3, PyArrow 17.0.0, psutil 7.2.2.

| Command or inspection | Result | Notes |
| --------------------- | ------ | ----- |
| `openspec status --change fix-effective-temporal-training-acceptance --json` and `openspec instructions apply --change fix-effective-temporal-training-acceptance --json` | Complete / all_done | Repo-local change; no store. |
| `openspec validate fix-effective-temporal-training-acceptance --type change --strict --json --no-interactive` | PASS | 1/1 valid; no issues. |
| `$PY -m unittest discover -s benchmark/multivariate_time_series/tests` | PASS: 120 tests, 60.059 s | Current independent run outside sandbox for psutil/macOS monitoring; all repair/CLI/resource/recovery tests included. |
| `$PY -m unittest discover -s benchmark/nograph_baseline/tests` | REUSED: prior independent PASS, 287 tests, 2 skipped, 43.662 s | Baseline source/tests/dependencies and interpreter conditions unchanged; repair does not edit these helpers. |
| Appendix A independent fixture probes | Repairs confirmed; 2 new failures | Valid readiness passes; wrong rate fails; missing b/Ridge is incomplete; all six report members eligible; initial RSS breach stops at 0 updates; checkpoint timing included. Remaining failures detailed below. |
| Changed-code/test review | Complete for affected scope | Traced public flags to controller/worker watchdogs, live-ledger decorator, frozen diagnostics membership, recovery identities, complete-epoch timing and sample-count recomputation. |
| Snapshot comparison before/after checks | Identical | No relevant inputs changed during verification. |

## Requirement Coverage

Scenario references are from the unchanged delta spec. Evidence is from this round's full recurrent suite unless explicitly marked reused.

| Requirement / scenario | Evidence | Result |
| ---------------------- | -------- | ------ |
| Protocol-isolated recurrent training / Canonical identity across supported schemas; Invalid input fails before fitting | `CanonicalIdentityTests`, CLI schema/encoder chain, `data.py` unchanged; invalid keys/months/values/config fixture rejection. | PASS for data/model behavior; formal resource-control exception V-010. |
| Training-only RMS / Held-out observations change; Constant zero and independent state | `TrainingRmsTests`, held-out trajectory perturbation, zero/order-independent prediction tests. | PASS |
| Full-window optimization / Best epoch precedes final epoch; Uneven chunks preserve global weighting | Best snapshot/tie/reproduction tests; context boundary spy and multi-chunk full-window reference, 19 updates; cancellation code inspected around backward/step. | PASS; V-008 resolved |
| Selection and reporting / Test labels inaccessible during selection; Learning-rate tie and missing repeat | Selection/identity threshold fixtures, fit/select/diagnose sentinel, new missing b and frozen winner binding tests. | PASS; V-002 resolved |
| Selection and reporting / Four rolling windows have unequal errors | Four-window `[4,N,3]` arithmetic/month multiplicities, all-six-member pure eligibility, unrelated/fingerprint rejection and pre-array refusal sentinel. | PASS; V-004 resolved |
| Learning diagnostics / Gates pass and fail independently; Incomplete or all-zero evidence | All old boundary/Zero/tail/a-b tests plus both-role full histories, condition/environment/source checks and required Ridge field omission/corruption tests; independent probes. | PASS; V-002/V-003 resolved |
| Auditable outputs / Source data unavailable to reviewer | Saved-only dependency/source-access guards, all report groups/windows/horizons/clipped metrics; corruption of all five sample-count fields. | PASS; V-009 resolved |
| Auditable outputs / Collision or failed seed | Existing exclusive-output, failed candidate/seed, provenance/patch and summary retention tests; deterministic parent invariance. | PASS |
| Saved-only checks / Identical outputs conceal condition mismatch; Checks cannot overwrite inputs | Compare identity-before-numbers tests; diagnose input byte snapshots, existing/alias/inside-input rejection, failure envelopes and subprocess with torch/pandas/Arrow/psutil blocked. | PASS for saved-evidence contract; V-001 resolved. Live batch stopping is separately V-011. |
| Resource preflight / Controlled resource or time breach | Initial stop=0 updates, mid-epoch previous-checkpoint preservation, controller termination, setup/final-write stops, inherited 3500+200 s fit limit. New public RSS/live-stage probes. | FAIL: V-010/V-011; original V-005/V-006/V-007 defects resolved. |
| Resource costs / Sample resumes without double fitting | Same-trajectory continuation, setup/diagnostic/publication-inclusive timing and separate measured/estimated/unknown-block fields. | PASS for measured continuation/estimates; V-007 resolved. Global stopping remains V-010/V-011. |
| Atomic recovery / Interrupted matches uninterrupted; Legacy or damaged checkpoint | Numeric/best/validation equality and parent byte invariance; atomic-publication fault, legacy/truncated checks; current/parent source/environment and missing/replaced/wrong/exhausted ledger tests. | PASS; V-006 resolved |
| Software/research boundary / Development invocation targets formal namespace | CLI/output alias tests and diagnose external-output namespace guard; development default and migration help. | PASS |
| Software/research boundary / Independent software verification completes | Current 120-test run, reused unchanged baseline regression, independent probes and current state. | FAIL: pending V-010/V-011 prevent software readiness; no research acceptance inferred. |
| Design/tasks beyond scenarios | Context-local chunks, explicit frozen diagnostics, snapshot independence, complete timing, read-only checker behavior, README sequencing and legacy limitations inspected. | Original promised repairs confirmed; remaining resource-control requirements are not waived. |

## Findings

V-001…V-009 retain their IDs and repair notes but are resolved. V-010/V-011 are new confirmed implementation defects, not reopenings of the corrected earlier reproductions.

### V-001: Diagnose modifies consumed evidence and bypasses report isolation

- Category: implementation
- Severity: high
- Requirement: Saved-only checks reject incompatible evidence; scenario “Checks cannot overwrite inputs”; design §5 and task 4.4.
- Evidence: Original deviation recorded at prior basis `7ca4f43`; current independent evidence: `SavedEvidenceRepairTests.test_diagnose_writes_one_report_and_keeps_all_inputs_identical` and dependency-blocked subprocess pass; current `diagnostics.run_diagnose` validates inputs/destinations, writes one external success/incomplete/failure envelope, and runner consumes explicit frozen JSON.
- Expected: The originally specified acceptance behavior, with mandatory evidence complete and protocol behavior enforced.
- Actual: The recorded original counterexample is corrected on the current basis.
- Repair status: verified-resolved
- Repair notes: Moved saved-only execution into `temporal/diagnostics.py`; `cli.py` dispatches without importing runner/model dependencies. Diagnose now validates resolved destinations, keeps all consumed block/run/Ridge inputs unchanged, and writes one exclusive external envelope including failures. `runner.py` consumes an explicit frozen diagnose JSON and no longer creates input-local diagnostics or a latest pointer; README and CLI fixtures updated. `tests/test_temporal_repairs.py` checks byte snapshots for success/incomplete/invalid destinations and aliases, failure-report retention, and a subprocess with torch/pandas/Arrow/psutil imports blocked. Invalid previously unrelated-winner fixtures now assert failure. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Independently rechecked this round as above; repair-owned validation claims are retained only as handoff history.

### V-002: Readiness can pass unrelated selections and incomplete or incompatible b trajectories

- Category: implementation
- Severity: high
- Requirement: Learning diagnostics implement the existing gates; Selection and readiness precede four-window test reporting; Saved-only checks reject incompatible evidence; P02 §§4–6.
- Evidence: Original deviation recorded at prior basis `7ca4f43`; current independent evidence: Both-role complete/finiteness, frozen winner/rate/condition/source/environment/split checks traced. `test_each_selection_and_trajectory_perturbation_prevents_readiness` passes; independent valid control=pass, changed selected rate=fail and missing b history=incomplete.
- Expected: The originally specified acceptance behavior, with mandatory evidence complete and protocol behavior enforced.
- Actual: The recorded original counterexample is corrected on the current basis.
- Repair status: verified-resolved
- Repair notes: `diagnostics.py` now checks both a/b complete finite histories, all required fixed-score blocks, effective protocol controls, recomputed condition identities, full configurations and source/environment/split/data identities across required runs. A separate identity gate binds seed-0 a to the actual frozen winner-as-a and learning rate. Synthetic fixtures now carry valid full protocol configs/identities. New regressions independently perturb selected rate/winner, b history/nonfinite values/controls/protocol/environment, cross-seed data/config and condition IDs; none returns ready; valid boundary fixtures still pass. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Independently rechecked this round as above; repair-owned validation claims are retained only as handoff history.

### V-003: Missing Ridge identity is accepted as compatible evidence

- Category: implementation
- Severity: medium
- Requirement: Learning diagnostics implement the existing gates, including baseline node/month/source/preprocessing/selection/split compatibility and incomplete missing evidence.
- Evidence: Original deviation recorded at prior basis `7ca4f43`; current independent evidence: Every required Ridge identity/split/month/preprocessing/selection omission and corruption in `test_ridge_required_fields_cannot_be_missing_or_corrupt` prevents readiness; independent identity-free Ridge=incomplete; valid fixture passes.
- Expected: The originally specified acceptance behavior, with mandatory evidence complete and protocol behavior enforced.
- Actual: The recorded original counterexample is corrected on the current basis.
- Repair status: verified-resolved
- Repair notes: `diagnostics.py` requires Ridge data/key/dataset identities and validation-start/month identity; validates the inherited training-only 27-month per-node standardization (ddof=0, constant std=1), validation original-unit MSE lambda selection and larger-lambda tie rule. Both supported key-hash names normalize to the same check. README documents the evidence schema. Regression cases independently omit/corrupt each identity, split/month, preprocessing and selection field; compatible Ridge remains valid without a neural-beats-Ridge condition. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Independently rechecked this round as above; repair-owned validation claims are retained only as handoff history.

### V-004: Formal report eligibility excludes valid repetitions and reads test arrays before the gate

- Category: implementation
- Severity: high
- Requirement: Selection and readiness precede four-window test reporting; independent seeds 0/1/2 a/b; post-report test repetition checks; design §1/P02 §§4–5.
- Evidence: Original deviation recorded at prior basis `7ca4f43`; current independent evidence: All six seed/repetition members accepted by the pure eligibility test and independent probe; unrelated path or changed evidence rejected. `test_failed_formal_gate_never_constructs_test_arrays` passes; runner checks before loading data/constructing arrays. No formal run performed.
- Expected: The originally specified acceptance behavior, with mandatory evidence complete and protocol behavior enforced.
- Actual: The recorded original counterexample is corrected on the current basis.
- Repair status: verified-resolved
- Repair notes: `report.py` checks membership of each seed/repetition in frozen diagnostics, selected rate/effective config and its saved evidence fingerprint; it no longer equates every trajectory with the seed-0 directory. `runner.py` verifies prerequisites before loading demand or constructing report arrays, then reports the requested trajectory's own best. New pure eligibility tests accept all six linked a/b trajectories, reject unrelated/changed evidence, and keep the report-array sentinel untouched on refusal. Existing development report/compare regressions remain passing. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Independently rechecked this round as above; repair-owned validation claims are retained only as handoff history.

### V-005: Resource breaches do not stop work until an epoch completes

- Category: implementation
- Severity: high
- Requirement: Resource preflight and cost limits are enforceable; design §6 explicitly requires monitoring/stopping beyond epoch-end checks.
- Evidence: Original deviation recorded at prior basis `7ca4f43`; current independent evidence: Cancellation checks traced through chunks/inference/backward/step/publication and controller loop. Current initial RSS breach stops before any update; mid-epoch test preserves preceding checkpoint byte-for-byte with 21 billed updates; controller termination test passes. Separate configurable-limit gap is new V-010.
- Expected: The originally specified acceptance behavior, with mandatory evidence complete and protocol behavior enforced.
- Actual: The recorded original counterexample is corrected on the current basis.
- Repair status: verified-resolved
- Repair notes: `engine.py`/`model.py` accept cancellation checks at bounded window/chunk/inference/backward/step/publication boundaries. `runner.py` records pauses without running further post-stop inference, retains the preceding complete checkpoint and bills partial work. `cli.py::supervise_worker` enforces sampled RSS/monitor-failure and time flags independently, terminating an unresponsive worker with a bounded wait. Initial RSS/monitor-failure fixtures now assert zero updates; a mid-epoch RSS regression asserts exactly 21 updates and byte-identical prior recovery; the controller termination fixture verifies retained ledger time. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Independently rechecked this round as above; repair-owned validation claims are retained only as handoff history.

### V-006: Recovery does not enforce source/environment or inherited trajectory budgets

- Category: implementation
- Severity: high
- Requirement: Atomic recovery is separate from best-model selection; Resource preflight and cost limits; design §2 and P02 §6 (single-fit time cannot reset on resume).
- Evidence: Original deviation recorded at prior basis `7ca4f43`; current independent evidence: Current/parent source/environment, protocol and bound ledger/execution identity validation inspected. Missing/new/replaced/different-batch/exhausted/lost-time ledger cases reject; 3500+200 s resumes pause; numeric equivalence and parent invariance pass.
- Expected: The originally specified acceptance behavior, with mandatory evidence complete and protocol behavior enforced.
- Actual: The recorded original counterexample is corrected on the current basis.
- Repair status: verified-resolved
- Repair notes: `checkpoints.py` binds source/environment and ledger/batch/execution references into last state. `recovery.py` validates those bindings and current runtime conditions before child reservation, requires the inherited ledger path/ID/batch and completed measured entries, and inherits all trajectory execution time. `runner.py` retains billing.json time floors and parent-chain IDs (including partial work), checks inherited single-fit time, and gives children the prior complete recovery state. Tests reject changed current/parent source/environment, missing/new/replaced/different-batch ledgers, lost measured time and exhausted budgets; 3500+200 seconds pauses at the 3600-second trajectory limit. Existing deterministic resume and parent-byte invariance tests pass. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Independently rechecked this round as above; repair-owned validation claims are retained only as handoff history.

### V-007: Cost samples omit checkpoint/diagnostic time and setup, and active billing ends too early

- Category: implementation
- Severity: high
- Requirement: Resource preflight and cost limits; epochs 6..10 **complete-epoch** median, sample <=15 min including setup/I/O/diagnostics, cumulative active work including checks; P02 §6/design §6.
- Evidence: Original deviation recorded at prior basis `7ca4f43`; current independent evidence: Complete timing now includes fixed scores/publication; measured setup/sample and final-write/termination billing tests pass. Independent 2 s/publish probe now reports median=2 s, sample=20 s and positive estimate=57.2 s (11-epoch development budget), rather than zeros. Additional setup probe in suite gives setup=4 s/sample=25 s. Live stage enforcement is new V-011, separate from repaired measurement/billing omission.
- Expected: The originally specified acceptance behavior, with mandatory evidence complete and protocol behavior enforced.
- Actual: The recorded original counterexample is corrected on the current basis.
- Repair status: verified-resolved
- Repair notes: `engine.py` measures complete epochs through fixed-score diagnostics and atomic checkpoint publication; runner measures setup and passes actual elapsed sample time to the cost gate. `epoch-timing.json` retains post-publication durations for recovery. Fit billing lasts through final outputs/failures; the controller persists a shared ledger identity before launching and heartbeats active elapsed time through termination. Linked live-batch select/diagnose/report/recompute/compare work is accounted outside consumed evidence; offline saved checks still work without their original ledger. Delay-injection regressions verify setup=4 s, sample=25 s and median=2 s for the controlled example, sample/setup stop, final-write timeout/full billing, saved-check billing and terminated-worker billing, while same-trajectory continuation still passes. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Independently rechecked this round as above; repair-owned validation claims are retained only as handoff history.

### V-008: Training chunks can cross context boundaries

- Category: implementation
- Severity: medium
- Requirement: Protocol-isolated/full-window optimization; design §3 explicitly says chunks must not merge contexts; task 2.1 and P02 §3.
- Evidence: Original deviation recorded at prior basis `7ca4f43`; current independent evidence: Context-aware chunks used by actual training; unequal 2+3-node spy yields separate batches, and chunk sizes 2/3/20 match the N*3 full-window update reference with exactly 19 updates.
- Expected: The originally specified acceptance behavior, with mandatory evidence complete and protocol behavior enforced.
- Actual: The recorded original counterexample is corrected on the current basis.
- Repair status: verified-resolved
- Repair notes: `engine.py::chunk_ranges` accepts context identities and training supplies canonical `FitArrays.node_keys[:,0]`; chunks stay within each context while retaining the N*3 denominator, complete-gradient clipping and one step/window. An unequal 2+3-node multi-context spy asserts unmixed batches, and different chunk sizes agree with the full-window update reference with 19 updates. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Independently rechecked this round as above; repair-owned validation claims are retained only as handoff history.

### V-009: Recompute accepts false saved sample counts

- Category: implementation
- Severity: medium
- Requirement: Auditable and independently recomputable outputs; “Source data are unavailable to a reviewer,” including sample/group counts and all four windows; task 4.4.
- Evidence: Original deviation recorded at prior basis `7ca4f43`; current independent evidence: `checks._recompute_report_metrics` derives all five counts from validated arrays/keys and four starts; each independently corrupted count fails recompute with inputs unchanged, and restored report passes.
- Expected: The originally specified acceptance behavior, with mandatory evidence complete and protocol behavior enforced.
- Actual: The recorded original counterexample is corrected on the current basis.
- Repair status: verified-resolved
- Repair notes: `checks.py` derives all five sample-count fields from validated prediction/gold shapes and canonical keys, and requires all four protocol test starts. The regression independently corrupts windows/nodes/horizon/elements/per-window-elements, checks a non-pass report with unchanged inputs, then restores the valid report and confirms saved-only recomputation passes. Other numeric metrics remain derived from arrays/masks rather than copied counts. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Independently rechecked this round as above; repair-owned validation claims are retained only as handoff history.

### V-010: Formal calls can raise the frozen RSS stopping line

- Category: implementation
- Severity: high
- Requirement: Resource preflight and cost limits are enforceable (8 GiB stopping line); Protocol-isolated recurrent training (unsupported protocol settings fail explicitly); Software readiness (formal requires complete controls).
- Evidence: Public `fit`/`resume --memory-limit-bytes` is passed to both controller and worker watchdogs without a formal bound. `cli.py:313` rejects formal availability-reading injections but never validates this stopping-line override; `runner.py:370` uses it verbatim. `FitConfig.complete_protocol` excludes the limit. Appendix A parses a formal fit with limit=17179869184 (16 GiB): request accepted, protocol controls complete=true, and the actual Watchdog returns `ok` for RSS=8 GiB+1.
- Expected: Formal protocol controls enforce an RSS stopping line no higher than 8 GiB, and reject an unsupported relaxation before work; development overrides must be explicitly classified rather than silently qualifying as complete protocol evidence.
- Actual: A syntactically valid formal request can silently disable the mandated 8 GiB stop until the caller's larger threshold. Prompt cancellation at the configured threshold does not enforce the frozen threshold.
- Repair guidance: Validate resource stopping controls at the public/formal boundary and worker entry, enforce the frozen upper bound, and make effective resource controls/override status auditable. Preserve lower conservative limits if permitted by the existing contract; do not change scientific/resource protocol thresholds.
- Acceptance checks: Pure formal control fixtures for default, 8 GiB, greater-than-8-GiB and invalid values, through both fit/resume public paths; invalid relaxation must reject before worker/output creation. Inject RSS=8 GiB+1 through the accepted formal control path and require a stop. Development overrides must not be misclassified as complete protocol controls. No real memory allocation/formal experiment required.
- Repair status: addressed-awaiting-verification
- Repair notes: Validated RSS controls in `protocol.resource_controls`, public fit/resume preflight and worker `run_fit`: positive integers only, formal upper bound 8 GiB, conservative lower formal limits accepted. Effective limits and development override/inherited override classification are saved in config/report/status/summary; resume, formal selection and report cannot promote incomplete resource controls. Updated README. `test_temporal_stage_limits.RssControlTests` covers both public paths (default/exact/lower/raised/invalid), rejection before preflight/worker/output, worker validation, injected 8 GiB+1 breach without allocation, development audit fields and two resume generations. Final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_stage_limits`: 9 tests passed (4.509 s). Full recurrent suite under host process-monitor access: 127 tests passed (91.514 s; includes the first 7 new regressions); two subsequently added cases also pass in the final 9-test run. Strict OpenSpec validation and `git diff --check` pass. Only synthetic/temp development executions and pure formal control fixtures; no formal experiment or high-RSS allocation.
- Reverification notes: New finding from affected resource-control inspection; no formal command was executed and no high-RSS allocation was made.

### V-011: Live batch stages ignore the exhausted cumulative budget

- Category: implementation
- Severity: high
- Requirement: Resource preflight and cost limits are enforceable; P02 §6 cumulative 12 h includes checks and requires pausing at the limit.
- Evidence: `resources.py:869` `account_stage` finds live ledgers, calls the wrapped stage unconditionally at line 917 and records elapsed time afterward, without checking remaining budget or enforcing a stop. It wraps select/diagnose/report/recompute/compare. Appendix A creates a normal tiny saved fit linked to a live ledger, charges another 43200 s to exhaust it, then runs saved-only recompute. The metrics function executes, the report returns `pass`, and ledger time grows from about 43201.226 s to 43201.349 s despite limit=43200.
- Expected: Work participating in a live protocol batch pauses/refuses when its cumulative active budget is exhausted and cannot return successful protocol execution beyond that stop line. Truly offline independent checks may remain usable without an active original batch ledger.
- Actual: Only fit/controller paths enforce the time line. Decorated live stages merely account for the overrun after completing successful work, so later protocol stages continue beyond an already known exhaustion.
- Repair guidance: Enforce live batch budget before entering these stages and at bounded points during potentially long stages, retaining a clear non-success/pause report and billed consumed time. Keep offline checking and read-only evidence guarantees; make the live/offline distinction explicit rather than treating cost recording as enforcement.
- Acceptance checks: Link each affected stage to an already exhausted ledger and assert stage work is not entered and cannot report success; cross the limit with an injected clock during representative long stage work and verify prompt pause/failure, retained external failure evidence and complete billing. Offline copies must remain independently checkable and consumed inputs unchanged.
- Repair status: addressed-awaiting-verification
- Repair notes: Replaced accounting-only stage wrapper with a context-local live batch guard: check before entering all five stages, heartbeat/reload ledger during work, cancel between saved reads, 1 MiB hash blocks, metric units, seeds/history and inference chunks, and check final publication time. Every exit bills full elapsed work including failure publication. Exhaustion retains external failed check reports or paused fresh run/block evidence; a late publication overrun invalidates only output created by that invocation and revokes its frozen selection. Existing/aliased input destinations remain protected. Reports/returns distinguish live-batch from offline; missing original ledgers permit independent offline checks, while explicit live ledger requests require an existing ledger and cannot replace other linked budget checks. Changes span resources/artifacts/checks/diagnostics/model/selection/report/runner and README. `test_temporal_stage_limits.LiveStageBudgetTests` covers all five exhausted stages, no core work entry, injected mid-read cancellation, final-publication crossing, full ledger billing (including pause summary), selection revocation, unchanged input digests, existing/inside-input destination refusal and offline checking. Final focused suite: 9 tests passed (4.509 s). Full recurrent suite with host psutil access: 127 tests passed (91.514 s); two later-added regressions passed in the final focused suite. Earlier sandbox-only broader attempt encountered known macOS process-monitor denial; host run resolves it. Strict OpenSpec validation and `git diff --check` pass. Cancellation is cooperative between bounded units; a running native array/file operation completes before the next checkpoint. No real-data execution or research record changes.
- Reverification notes: New finding from added stage accounting; Appendix A reproduces it with synthetic evidence and an exhausted temporary ledger, not real elapsed hours.

## Next Action

Run `$openspec-e13-fix-change fix-effective-temporal-training-acceptance` for V-010/V-011, then independently verify again. There is no planning finding and no environment blocker. Do not archive this FAIL basis. Resolved findings need only affected rechecks if later repairs leave their behavior/evidence applicable.

## Appendix A: Current Independent Probes

Copy this exact script to `/tmp/e13_temporal_reverify.py` and run from repository root with the `PY` interpreter above. It uses existing synthetic fixture helpers and temporary development outputs. Formal arguments are parsed/inspected only; no formal execution occurs. Floating wall-clock billing values vary; decisive statuses/bounds are recorded above. This replaces the superseded first-round probe whose fixture/schema assumptions no longer match repaired inputs.

```python
import copy
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path[:0] = [str(Path.cwd()), str(Path.cwd()/'benchmark/multivariate_time_series/tests')]
import temporal_fixtures as fx
from test_temporal_selection_diagnostics import DiagnosticsGateTests
from benchmark.multivariate_time_series.temporal import checks, cli, diagnostics, engine, protocol, report, resources, runner

out = {}
case = DiagnosticsGateTests()
case.setUp()
try:
    a, b = case._all_pass()
    selection = case._selection(a)
    ridge = case._compatible_ridge()
    def diagnose(aa=a, bb=b, ss=selection, rr=ridge):
        return diagnostics.build_diagnostics(selection=ss, block_id='block', a_runs=aa, b_runs=bb, ridge=rr)
    control = diagnose()
    out['valid_readiness'] = control['status']
    wrong = copy.deepcopy(selection)
    wrong['winner']['learning_rate'] = .003
    wrong['selection_sha256'] = protocol.content_sha256({k:v for k,v in wrong.items() if k!='selection_sha256'})
    out['wrong_selected_rate'] = diagnose(ss=wrong)['status']
    broken_b = copy.deepcopy(b)
    broken_b[0]['history'] = {'epochs': []}
    out['missing_b_history'] = diagnose(bb=broken_b)['status']
    out['missing_ridge_identity'] = diagnose(rr={'selection': {'anything': True}, 'validation': {'MAE': 6., 'MSE':36.}})['status']
    states = {seed:'completed' for seed in protocol.SEEDS}
    out['all_six_report_members_eligible'] = all(not report.formal_report_blockers(purpose='formal', config=run['config'], selection=selection, diagnostics=control, run_dir=Path(run['run_dir']), a_states=states, b_states=states, winner_run_dir=Path(a[0]['run_dir']), run_evidence_sha256=run['evidence_sha256']) for run in [*a.values(), *b.values()])
finally:
    case.tearDown()

with tempfile.TemporaryDirectory(prefix='e13-reverify-') as tmp:
    root = Path(tmp)
    data = fx.in_memory('r0', 4, seed=3)
    stop = fx.fit_run(root, run_id='initial-stop', data=data, epochs=2, sampler=lambda:{'rss_bytes':protocol.MEMORY_STOP_BYTES+1})
    out['initial_rss_stop'] = {'status':stop['status'], 'updates': fx.read_json(Path(stop['run_dir'])/'gradients.json')['total_updates']}
    # Probe the accepted public control surface without executing formal work.
    args = cli.build_parser().parse_args(['fit','--data-name','r0','--run-id','pure-eligibility','--purpose','formal','--memory-limit-bytes',str(16*protocol.GIB)])
    preflight_request = cli._preflight_request(args, operation='fit')
    dog = resources.Watchdog(sampler=lambda:{'rss_bytes':protocol.MEMORY_STOP_BYTES+1}, limit_bytes=args.memory_limit_bytes)
    out['raised_formal_rss_limit'] = {'preflight_request_accepted':preflight_request['purpose']=='formal', 'protocol_controls_complete':protocol.FitConfig.from_payload(cli._config_payload(args)).complete_protocol, 'limit_bytes':args.memory_limit_bytes, 'sample_status':dog.sample_once()['status']}

    fit = fx.fit_run(root, run_id='saved-run', data=data, epochs=1, sampler=lambda:{'rss_bytes':0})
    directory = Path(fit['run_dir'])
    ledger = resources.Ledger(root/'ledger.json', batch_id='p02-t006')
    ledger.record(execution_id='budget-spent', run_id='earlier', seconds=protocol.BATCH_SECONDS)
    before = ledger.active_seconds()
    entered = []
    original = checks._recompute_fit_metrics
    def observe(path):
        entered.append(True)
        return original(path)
    with patch.object(checks, '_recompute_fit_metrics', side_effect=observe):
        checked = checks.run_recompute(run_dir=directory, report_path=root/'over-budget.json', argv=[])
    after = resources.Ledger(root/'ledger.json', batch_id='p02-t006').active_seconds()
    out['saved_stage_after_exhausted_batch'] = {'metrics_work_executed':bool(entered), 'status':checked['status'], 'batch_before':before, 'batch_after':after, 'limit':protocol.BATCH_SECONDS}

    class Clock:
        value = 0.
        def __call__(self): return self.value
    clock = Clock()
    def slow_publish(path, payload):
        from benchmark.multivariate_time_series.temporal import checkpoints
        clock.value += 2.
        return checkpoints.publish_last(path,payload)
    timed = fx.fit_run(root, run_id='timed', data=data, epochs=11, sampler=lambda:{'rss_bytes':0}, publish=slow_publish, clock=clock, ledger_path=root/'timing-ledger.json')
    cost = fx.read_json(Path(timed['run_dir'])/'cost.json')
    out['complete_epoch_timing'] = {'sample':cost['sample_measured_seconds'], 'median':cost['steady_state_median_seconds'], 'estimate':cost['estimate_seconds']}
print(json.dumps(out, indent=2, sort_keys=True))
```
