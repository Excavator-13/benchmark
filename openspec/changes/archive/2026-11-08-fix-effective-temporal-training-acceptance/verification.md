# Implementation Verification

- Change: fix-effective-temporal-training-acceptance
- Schema: spec-driven
- Verdict: PASS
- Verified at: 2026-11-08T12:37:41+08:00
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark` (also planning root)
- Verified revision: `ca4d5e2949b4376296a6d97d9b916ed05e341bbf`; implementation unchanged since the independent runtime checks; main-spec sync is uncommitted. This verification refresh changes only report/state.

## Summary

Independent software verification **PASS**. All eleven findings V-001 through V-011 are **verified-resolved**; no actionable finding or mandatory evidence gap remains on this basis. Formal fit/resume now reject RSS limits above 8 GiB at public and worker boundaries; effective development resource overrides remain incomplete across resume generations. Live select/diagnose/report/recompute/compare stages refuse exhausted batches, cancel at bounded operations, preserve failure/pause evidence and bill consumed work. Offline saved checks remain usable and inputs remain unchanged.

Strict change validation and all 6 main-spec validations passed after sync. The unchanged complete recurrent suite previously independently passed **129 tests in 63.203 s** with host process-monitor access. Still-applicable prior independent synthetic probes confirmed exact/conservative formal limits, rejection of relaxed/invalid controls, pre-work refusal, protection against explicit-fresh-ledger bypass, refresh of another stage's budget charges, complete billing and offline checking. Prior independent unchanged baseline regression evidence is reused: **287 tests passed, 2 skipped**, 43.662 s. Repair-owned claimed runs were not substituted for independent checks.

This PASS establishes software readiness only. Verification used synthetic/temporary development evidence and pure formal control/eligibility fixtures; no real demand/graph read, formal experiment, matrix, research-state edit, archive, commit or push occurred. Native Windows execution, actual hardware capacity/cost and real-data learning-readiness/research acceptance remain outside this software decision. Cancellation in live saved stages is cooperative between bounded units; a native file/array operation completes before its next checkpoint, as documented.

## Verification Basis

| Path or scope | Revision / content fingerprint / file inventory |
| ------------- | ---------------------------------------------- |
| Current proposal, design, tasks and delta spec from apply context | All read in the preceding verification; unchanged in the current comparison. 19/19 checked tasks are claims rather than acceptance evidence. |
| Recurrent entry/helpers/tests and README §4.7 | Repair commit `ca4d5e2`; runtime/docs/tests unchanged since their independent full-suite check; earlier repair inspection and runtime evidence retained. |
| Reused baseline helpers/tests, dependencies, P01/P02 scientific definitions and controlling artifacts | Unchanged in scripted comparison; relevant interpreter/environment unchanged. Prior independent baseline evidence remains applicable. |
| Synced `openspec/specs/recurrent-forecasting-entry/spec.md` | New main specification; Purpose and all 10 requirements / 21 scenarios exactly match the verified delta; only document title and canonical Requirements heading differ. |
| `verification-state.json` | Script-generated 603-file inventory; SHA-256 `07c08f7f7476cc27c1e599be523b6376a0b33f6a68ccd0a90849557322bdf68f`. |

Incremental verification after main-spec synchronization from the immediately preceding independent PASS state SHA-256 `cdad8f52c7ab6d1e686de6d2db1c3d091ce77386c3794d1cdca50201a45ccb96`, confirmed to match the report before comparison. Script comparison exited 1 and found exactly one added file: `openspec/specs/recurrent-forecasting-entry/spec.md`; no implementation, test, dependency, delta, proposal, design or task file changed. The new main spec is the verified delta with only its title/Requirements header converted to main-spec form. Exact comparison establishes that all requirement/scenario bodies and Purpose are preserved, and all 6 main specs plus the active change pass strict validation. Therefore all prior independent 129-test temporal, 287-test baseline and Appendix A boundary-probe results remain applicable on the same interpreter/environment. No runtime tests were rerun for this documentation-only refresh. All 11 resolved findings and full coverage matrix remain supported; the newly synchronized main-spec content has direct equivalence/validation evidence.

Snapshots use the same root/exclusions as the prior basis:

```sh
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py capture \
  --root /Users/watuji/da_chuang/repos/benchmark \
  --exclude 'dataset/**' --exclude 'experiments_archive/**' \
  --exclude 'research/archives/**' --exclude 'research/runs/**' \
  --exclude 'research/analyses/**' --exclude 'research/reports/**' \
  --exclude 'references/**' --output /tmp/e13-temporal-post-sync-before.json
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py compare \
  openspec/changes/fix-effective-temporal-training-acceptance/verification-state.json \
  /tmp/e13-temporal-post-sync-before.json
# Capture with identical arguments and --output /tmp/e13-temporal-post-sync-after.json.
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py compare \
  /tmp/e13-temporal-post-sync-before.json /tmp/e13-temporal-post-sync-after.json
```

Before/after comparison exited 0, `changed: false`. Final generated snapshot copied only after the prior state comparison. Exclusions omit datasets, historical evidence/report/archive trees and unrelated references; current relevant code, tests, scientific protocols, dependencies, configuration and planning remain covered. Git ignores handle caches/scratch; workflow handoff/report/state files are automatically excluded. Inventory hashes identify inputs and do not themselves prove behavior.

## Apply Handoff Review


`implementation-notes.md` identifies the correct project/change but remains at its original apply revision (`fa45639` plus dirty implementation). It is stale about current revision and some corrected behavior; current code and repair notes were checked directly. Repair notes below are preserved verbatim as claims/history; their commands are not this verifier's results.

| Reminder | Current disposition |
| -------- | ------------------- |
| No real-data/formal execution; no research acceptance | Confirmed for this verification; no scientific acceptance/task completion claimed. Apply's historical action claims are not independent evidence. |
| Formal reporting only partially exercised | Full formal run remains intentionally outside scope. Current pure fixture eligibility accepts all six a/b members and rejects unrelated/changed evidence; refusal sentinel is checked before test arrays (V-004 resolved). |
| Host memory near startup threshold | Environment-dependent; CLI fixtures use development-only resource readings. No assertion of real formal capacity. Host psutil access was used for the retained independent suite. |
| Missing coverage optional and explicit | Confirmed: no implicit all-isolated mask; supplied context-qualified masks/counts covered by current regression suite. |
| Ridge external and identity checked | Confirmed for mandatory identity/preprocessing/selection omission/mismatch paths; V-003 resolved. External scientific evidence must still be supplied by research execution. |
| Diagnostics inside block and latest pointer | Stale/inapplicable after repair. Diagnose now emits one external report and leaves consumed evidence unchanged (V-001 resolved). README now documents explicit `--diagnostics` report consumption. |
| Cost/monitor tests and platform limits | macOS CLI controller plus injected failure/clock tests independently pass. Timing, cancellation, frozen RSS control and live-stage budget behavior independently verified; V-005/V-007/V-010/V-011 resolved. Windows native execution not performed. |
| Batch default and explicit formal ledger | Default confirmed; recovery now enforces bound ledger identity and trajectory time (V-006 resolved). Live stage budget refusal/cancellation, billing and offline behavior verified (V-011 resolved). |
| README numbering | §4.7 retained; original §4.6 unchanged. Current descriptions of stage/recovery changes read and compared with CLI. |

## Checks

`PY` = `/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python`, from repository root. Environment independently reconfirmed: Python 3.11.17, NumPy 1.26.4, torch 2.14.1, pandas 2.2.3, PyArrow 17.0.0, psutil 7.2.2.

| Command or inspection | Result | Notes |
| --------------------- | ------ | ----- |
| `openspec status --change fix-effective-temporal-training-acceptance --json` / `openspec instructions apply --change fix-effective-temporal-training-acceptance --json` | Complete / all_done | Repo-local, no store; 19/19 tasks. |
| `openspec validate fix-effective-temporal-training-acceptance --type change --strict --json --no-interactive` | PASS | 1/1 valid, no issues. |
| `$PY -m unittest discover -s benchmark/multivariate_time_series/tests` | REUSED: independent PASS, 129 tests, 63.203 s | Immediately preceding independent host-access run; macOS sandbox denies required psutil monitoring. Includes all 9 new stage-limit regressions and prior repair/CLI/resource/recovery suites. |
| `$PY -m unittest discover -s benchmark/nograph_baseline/tests` | REUSED: independent PASS, 287 tests, 2 skipped, 43.662 s | Relevant code/tests/dependencies and interpreter conditions unchanged. |
| `$PY /tmp/e13_temporal_third_probe.py` (exact script in Appendix A) | REUSED: independent PASS | Both public formal control paths; injected RSS breach; exhausted metrics not entered; fresh explicit ledger cannot replace exhausted linked ledger; refresh observes another charge; active time=43201.1 s; offline pass with unchanged inputs. |
| Changed code/tests and README review | REUSED: independent PASS | Traced effective limits to controller/worker; development/inherited overrides to formal selection/report blockers; all five live stages to pre-entry, bounded-work and publication checks; pause output ownership and billing inspected. |
| Main-spec exact comparison and `openspec validate --specs --strict --json --no-interactive` | PASS | All 10 requirements / 21 scenarios and Purpose match the verified delta; all 6 specs valid, no warnings/errors (length suggestions are informational). |
| Snapshot before/after comparison | Identical | No relevant inputs changed during verification. |

## Requirement Coverage

Scenario references are from the unchanged delta and equivalent synchronized main spec. Runtime evidence below comes from retained independent tests/probes; the present refresh adds exact main-spec equivalence and strict validation evidence. No new behavior or acceptance criterion was introduced by synchronization.

| Requirement / scenario | Evidence | Result |
| ---------------------- | -------- | ------ |
| Protocol-isolated recurrent training / Canonical identity across supported schemas; Invalid input fails before fitting | `CanonicalIdentityTests`, CLI schema/encoder chain, `data.py` unchanged; invalid keys/months/values/config fixture rejection. | PASS, including formal resource controls; V-010 resolved. |
| Training-only RMS / Held-out observations change; Constant zero and independent state | `TrainingRmsTests`, held-out trajectory perturbation, zero/order-independent prediction tests. | PASS |
| Full-window optimization / Best epoch precedes final epoch; Uneven chunks preserve global weighting | Best snapshot/tie/reproduction tests; context boundary spy and multi-chunk full-window reference, 19 updates; cancellation code inspected around backward/step. | PASS; V-008 resolved |
| Selection and reporting / Test labels inaccessible during selection; Learning-rate tie and missing repeat | Selection/identity threshold fixtures, fit/select/diagnose sentinel, new missing b and frozen winner binding tests. | PASS; V-002 resolved |
| Selection and reporting / Four rolling windows have unequal errors | Four-window `[4,N,3]` arithmetic/month multiplicities, all-six-member pure eligibility, unrelated/fingerprint rejection and pre-array refusal sentinel. | PASS; V-004 resolved |
| Learning diagnostics / Gates pass and fail independently; Incomplete or all-zero evidence | All old boundary/Zero/tail/a-b tests plus both-role full histories, condition/environment/source checks and required Ridge field omission/corruption tests; independent probes. | PASS; V-002/V-003 resolved |
| Auditable outputs / Source data unavailable to reviewer | Saved-only dependency/source-access guards, all report groups/windows/horizons/clipped metrics; corruption of all five sample-count fields. | PASS; V-009 resolved |
| Auditable outputs / Collision or failed seed | Existing exclusive-output, failed candidate/seed, provenance/patch and summary retention tests; deterministic parent invariance. | PASS |
| Saved-only checks / Identical outputs conceal condition mismatch; Checks cannot overwrite inputs | Compare identity-before-numbers tests; diagnose input byte snapshots, existing/alias/inside-input rejection, failure envelopes and subprocess with torch/pandas/Arrow/psutil blocked. | PASS; V-001/V-011 resolved, including live/offline checks and unchanged inputs. |
| Resource preflight / Controlled resource or time breach | Initial stop=0 updates, mid-epoch previous-checkpoint preservation, controller termination, setup/final-write stops, inherited 3500+200 s fit limit. RssControlTests and LiveStageBudgetTests plus Appendix A: formal bounds, inherited development controls, all five exhausted stages, injected mid-stage/publication crossing, full billing, ledger bypass/refresh and offline checks. | PASS; V-005/V-006/V-007/V-010/V-011 resolved. |
| Resource costs / Sample resumes without double fitting | Same-trajectory continuation, setup/diagnostic/publication-inclusive timing and separate measured/estimated/unknown-block fields. | PASS; measured continuation/estimates, enforced RSS/batch controls; V-007/V-010/V-011 resolved. |
| Atomic recovery / Interrupted matches uninterrupted; Legacy or damaged checkpoint | Numeric/best/validation equality and parent byte invariance; atomic-publication fault, legacy/truncated checks; current/parent source/environment and missing/replaced/wrong/exhausted ledger tests. | PASS; V-006 resolved |
| Software/research boundary / Development invocation targets formal namespace | CLI/output alias tests and diagnose external-output namespace guard; development default and migration help. | PASS |
| Software/research boundary / Independent software verification completes | Retained independent 129-test run and baseline regression/probes; current main-spec equivalence, strict validation and snapshot. | PASS for software readiness only; no research acceptance inferred. |
| Design/tasks beyond scenarios | Context-local chunks, explicit frozen diagnostics, snapshot independence, complete timing, read-only checker behavior, README sequencing and legacy limitations inspected. | PASS; promised behavior and resource-control repairs verified; legacy runners/scientific protocol unchanged. |

## Findings

No pending findings. Stable resolved IDs and repair notes are retained below. Repair notes are preserved verbatim as repair-workflow history; current independent evidence is stated separately. Prior counterexamples and the superseded failing probe script have been replaced by current results.

### V-001: Diagnose modifies consumed evidence and bypasses report isolation

- Category: implementation
- Severity: high
- Requirement: Saved-only checks reject incompatible evidence; scenario “Checks cannot overwrite inputs”; design §5 and task 4.4.
- Evidence: Current full-suite regression and still-applicable prior independent probes: `SavedEvidenceRepairTests.test_diagnose_writes_one_report_and_keeps_all_inputs_identical` and dependency-blocked subprocess pass; current `diagnostics.run_diagnose` validates inputs/destinations, writes one external success/incomplete/failure envelope, and runner consumes explicit frozen JSON.
- Expected: Mandatory protocol behavior and complete, independently checkable evidence.
- Actual: Original counterexample corrected; required rejection/pause/success behavior verified on the current basis.
- Repair status: verified-resolved
- Repair notes: Moved saved-only execution into `temporal/diagnostics.py`; `cli.py` dispatches without importing runner/model dependencies. Diagnose now validates resolved destinations, keeps all consumed block/run/Ridge inputs unchanged, and writes one exclusive external envelope including failures. `runner.py` consumes an explicit frozen diagnose JSON and no longer creates input-local diagnostics or a latest pointer; README and CLI fixtures updated. `tests/test_temporal_repairs.py` checks byte snapshots for success/incomplete/invalid destinations and aliases, failure-report retention, and a subprocess with torch/pandas/Arrow/psutil imports blocked. Invalid previously unrelated-winner fixtures now assert failure. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Retained independent full recurrent suite and affected-path inspection/probes remain applicable; this refresh additionally verified main-spec equivalence and validation. Earlier unchanged supporting probes are retained only where applicable, as stated in the verification basis.

### V-002: Readiness can pass unrelated selections and incomplete or incompatible b trajectories

- Category: implementation
- Severity: high
- Requirement: Learning diagnostics implement the existing gates; Selection and readiness precede four-window test reporting; Saved-only checks reject incompatible evidence; P02 §§4–6.
- Evidence: Current full-suite regression and still-applicable prior independent probes: Both-role complete/finiteness, frozen winner/rate/condition/source/environment/split checks traced. `test_each_selection_and_trajectory_perturbation_prevents_readiness` passes; independent valid control=pass, changed selected rate=fail and missing b history=incomplete.
- Expected: Mandatory protocol behavior and complete, independently checkable evidence.
- Actual: Original counterexample corrected; required rejection/pause/success behavior verified on the current basis.
- Repair status: verified-resolved
- Repair notes: `diagnostics.py` now checks both a/b complete finite histories, all required fixed-score blocks, effective protocol controls, recomputed condition identities, full configurations and source/environment/split/data identities across required runs. A separate identity gate binds seed-0 a to the actual frozen winner-as-a and learning rate. Synthetic fixtures now carry valid full protocol configs/identities. New regressions independently perturb selected rate/winner, b history/nonfinite values/controls/protocol/environment, cross-seed data/config and condition IDs; none returns ready; valid boundary fixtures still pass. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Retained independent full recurrent suite and affected-path inspection/probes remain applicable; this refresh additionally verified main-spec equivalence and validation. Earlier unchanged supporting probes are retained only where applicable, as stated in the verification basis.

### V-003: Missing Ridge identity is accepted as compatible evidence

- Category: implementation
- Severity: medium
- Requirement: Learning diagnostics implement the existing gates, including baseline node/month/source/preprocessing/selection/split compatibility and incomplete missing evidence.
- Evidence: Current full-suite regression and still-applicable prior independent probes: Every required Ridge identity/split/month/preprocessing/selection omission and corruption in `test_ridge_required_fields_cannot_be_missing_or_corrupt` prevents readiness; independent identity-free Ridge=incomplete; valid fixture passes.
- Expected: Mandatory protocol behavior and complete, independently checkable evidence.
- Actual: Original counterexample corrected; required rejection/pause/success behavior verified on the current basis.
- Repair status: verified-resolved
- Repair notes: `diagnostics.py` requires Ridge data/key/dataset identities and validation-start/month identity; validates the inherited training-only 27-month per-node standardization (ddof=0, constant std=1), validation original-unit MSE lambda selection and larger-lambda tie rule. Both supported key-hash names normalize to the same check. README documents the evidence schema. Regression cases independently omit/corrupt each identity, split/month, preprocessing and selection field; compatible Ridge remains valid without a neural-beats-Ridge condition. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Retained independent full recurrent suite and affected-path inspection/probes remain applicable; this refresh additionally verified main-spec equivalence and validation. Earlier unchanged supporting probes are retained only where applicable, as stated in the verification basis.

### V-004: Formal report eligibility excludes valid repetitions and reads test arrays before the gate

- Category: implementation
- Severity: high
- Requirement: Selection and readiness precede four-window test reporting; independent seeds 0/1/2 a/b; post-report test repetition checks; design §1/P02 §§4–5.
- Evidence: Current full-suite regression and still-applicable prior independent probes: All six seed/repetition members accepted by the pure eligibility test and independent probe; unrelated path or changed evidence rejected. `test_failed_formal_gate_never_constructs_test_arrays` passes; runner checks before loading data/constructing arrays. No formal run performed.
- Expected: Mandatory protocol behavior and complete, independently checkable evidence.
- Actual: Original counterexample corrected; required rejection/pause/success behavior verified on the current basis.
- Repair status: verified-resolved
- Repair notes: `report.py` checks membership of each seed/repetition in frozen diagnostics, selected rate/effective config and its saved evidence fingerprint; it no longer equates every trajectory with the seed-0 directory. `runner.py` verifies prerequisites before loading demand or constructing report arrays, then reports the requested trajectory's own best. New pure eligibility tests accept all six linked a/b trajectories, reject unrelated/changed evidence, and keep the report-array sentinel untouched on refusal. Existing development report/compare regressions remain passing. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Retained independent full recurrent suite and affected-path inspection/probes remain applicable; this refresh additionally verified main-spec equivalence and validation. Earlier unchanged supporting probes are retained only where applicable, as stated in the verification basis.

### V-005: Resource breaches do not stop work until an epoch completes

- Category: implementation
- Severity: high
- Requirement: Resource preflight and cost limits are enforceable; design §6 explicitly requires monitoring/stopping beyond epoch-end checks.
- Evidence: Current full-suite regression and still-applicable prior independent probes: Cancellation checks traced through chunks/inference/backward/step/publication and controller loop. Current initial RSS breach stops before any update; mid-epoch test preserves preceding checkpoint byte-for-byte with 21 billed updates; controller termination test passes. The configurable-limit gap is also now resolved (V-010).
- Expected: Mandatory protocol behavior and complete, independently checkable evidence.
- Actual: Original counterexample corrected; required rejection/pause/success behavior verified on the current basis.
- Repair status: verified-resolved
- Repair notes: `engine.py`/`model.py` accept cancellation checks at bounded window/chunk/inference/backward/step/publication boundaries. `runner.py` records pauses without running further post-stop inference, retains the preceding complete checkpoint and bills partial work. `cli.py::supervise_worker` enforces sampled RSS/monitor-failure and time flags independently, terminating an unresponsive worker with a bounded wait. Initial RSS/monitor-failure fixtures now assert zero updates; a mid-epoch RSS regression asserts exactly 21 updates and byte-identical prior recovery; the controller termination fixture verifies retained ledger time. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Retained independent full recurrent suite and affected-path inspection/probes remain applicable; this refresh additionally verified main-spec equivalence and validation. Earlier unchanged supporting probes are retained only where applicable, as stated in the verification basis.

### V-006: Recovery does not enforce source/environment or inherited trajectory budgets

- Category: implementation
- Severity: high
- Requirement: Atomic recovery is separate from best-model selection; Resource preflight and cost limits; design §2 and P02 §6 (single-fit time cannot reset on resume).
- Evidence: Current full-suite regression and still-applicable prior independent probes: Current/parent source/environment, protocol and bound ledger/execution identity validation inspected. Missing/new/replaced/different-batch/exhausted/lost-time ledger cases reject; 3500+200 s resumes pause; numeric equivalence and parent invariance pass.
- Expected: Mandatory protocol behavior and complete, independently checkable evidence.
- Actual: Original counterexample corrected; required rejection/pause/success behavior verified on the current basis.
- Repair status: verified-resolved
- Repair notes: `checkpoints.py` binds source/environment and ledger/batch/execution references into last state. `recovery.py` validates those bindings and current runtime conditions before child reservation, requires the inherited ledger path/ID/batch and completed measured entries, and inherits all trajectory execution time. `runner.py` retains billing.json time floors and parent-chain IDs (including partial work), checks inherited single-fit time, and gives children the prior complete recovery state. Tests reject changed current/parent source/environment, missing/new/replaced/different-batch ledgers, lost measured time and exhausted budgets; 3500+200 seconds pauses at the 3600-second trajectory limit. Existing deterministic resume and parent-byte invariance tests pass. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Retained independent full recurrent suite and affected-path inspection/probes remain applicable; this refresh additionally verified main-spec equivalence and validation. Earlier unchanged supporting probes are retained only where applicable, as stated in the verification basis.

### V-007: Cost samples omit checkpoint/diagnostic time and setup, and active billing ends too early

- Category: implementation
- Severity: high
- Requirement: Resource preflight and cost limits; epochs 6..10 **complete-epoch** median, sample <=15 min including setup/I/O/diagnostics, cumulative active work including checks; P02 §6/design §6.
- Evidence: Current full-suite regression and still-applicable prior independent probes: Complete timing now includes fixed scores/publication; measured setup/sample and final-write/termination billing tests pass. Independent 2 s/publish probe now reports median=2 s, sample=20 s and positive estimate=57.2 s (11-epoch development budget), rather than zeros. Additional setup probe in suite gives setup=4 s/sample=25 s. Live stage enforcement is also now resolved (V-011).
- Expected: Mandatory protocol behavior and complete, independently checkable evidence.
- Actual: Original counterexample corrected; required rejection/pause/success behavior verified on the current basis.
- Repair status: verified-resolved
- Repair notes: `engine.py` measures complete epochs through fixed-score diagnostics and atomic checkpoint publication; runner measures setup and passes actual elapsed sample time to the cost gate. `epoch-timing.json` retains post-publication durations for recovery. Fit billing lasts through final outputs/failures; the controller persists a shared ledger identity before launching and heartbeats active elapsed time through termination. Linked live-batch select/diagnose/report/recompute/compare work is accounted outside consumed evidence; offline saved checks still work without their original ledger. Delay-injection regressions verify setup=4 s, sample=25 s and median=2 s for the controlled example, sample/setup stop, final-write timeout/full billing, saved-check billing and terminated-worker billing, while same-trajectory continuation still passes. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Retained independent full recurrent suite and affected-path inspection/probes remain applicable; this refresh additionally verified main-spec equivalence and validation. Earlier unchanged supporting probes are retained only where applicable, as stated in the verification basis.

### V-008: Training chunks can cross context boundaries

- Category: implementation
- Severity: medium
- Requirement: Protocol-isolated/full-window optimization; design §3 explicitly says chunks must not merge contexts; task 2.1 and P02 §3.
- Evidence: Current full-suite regression and still-applicable prior independent probes: Context-aware chunks used by actual training; unequal 2+3-node spy yields separate batches, and chunk sizes 2/3/20 match the N*3 full-window update reference with exactly 19 updates.
- Expected: Mandatory protocol behavior and complete, independently checkable evidence.
- Actual: Original counterexample corrected; required rejection/pause/success behavior verified on the current basis.
- Repair status: verified-resolved
- Repair notes: `engine.py::chunk_ranges` accepts context identities and training supplies canonical `FitArrays.node_keys[:,0]`; chunks stay within each context while retaining the N*3 denominator, complete-gradient clipping and one step/window. An unequal 2+3-node multi-context spy asserts unmixed batches, and different chunk sizes agree with the full-window update reference with 19 updates. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Retained independent full recurrent suite and affected-path inspection/probes remain applicable; this refresh additionally verified main-spec equivalence and validation. Earlier unchanged supporting probes are retained only where applicable, as stated in the verification basis.

### V-009: Recompute accepts false saved sample counts

- Category: implementation
- Severity: medium
- Requirement: Auditable and independently recomputable outputs; “Source data are unavailable to a reviewer,” including sample/group counts and all four windows; task 4.4.
- Evidence: Current full-suite regression and still-applicable prior independent probes: `checks._recompute_report_metrics` derives all five counts from validated arrays/keys and four starts; each independently corrupted count fails recompute with inputs unchanged, and restored report passes.
- Expected: Mandatory protocol behavior and complete, independently checkable evidence.
- Actual: Original counterexample corrected; required rejection/pause/success behavior verified on the current basis.
- Repair status: verified-resolved
- Repair notes: `checks.py` derives all five sample-count fields from validated prediction/gold shapes and canonical keys, and requires all four protocol test starts. The regression independently corrupts windows/nodes/horizon/elements/per-window-elements, checks a non-pass report with unchanged inputs, then restores the valid report and confirms saved-only recomputation passes. Other numeric metrics remain derived from arrays/masks rather than copied counts. Validation: the full recurrent suite passed 119 tests (96.176 s) before the final billing hardening; the final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_repairs test_temporal_resources_recovery test_temporal_cli` passed 45 tests (41.285 s). Host psutil access was used for controller/resource suites because macOS sandbox monitoring is denied. Baseline regression `.../job-sdf-baseline/bin/python -m unittest discover -s benchmark/nograph_baseline/tests` passed 287 tests, 2 skipped (45.286 s). Strict OpenSpec validation passed. All executions used synthetic/temporary development evidence; independent reverification remains required.
- Reverification notes: Retained independent full recurrent suite and affected-path inspection/probes remain applicable; this refresh additionally verified main-spec equivalence and validation. Earlier unchanged supporting probes are retained only where applicable, as stated in the verification basis.

### V-010: Formal calls can raise the frozen RSS stopping line

- Category: implementation
- Severity: high
- Requirement: Resource preflight and cost limits are enforceable (8 GiB stopping line); Protocol-isolated recurrent training (unsupported protocol settings fail explicitly); Software readiness (formal requires complete controls).
- Evidence: `protocol.resource_controls`, `cli._preflight_request` and worker `runner.run_fit` now reject invalid or formal >8 GiB limits before execution output. The current 129-test run covers both public paths, worker validation, default/exact/lower/raised/invalid limits, audit fields, formal selection/report constraints and two resume generations. Appendix A independently accepts exact/lower limits, rejects 8 GiB+1/zero/negative limits for fit and resume, and observes watchdog breach at RSS=8 GiB+1.
- Expected: Mandatory protocol behavior and complete, independently checkable evidence.
- Actual: Original counterexample corrected; required rejection/pause/success behavior verified on the current basis.
- Repair status: verified-resolved
- Repair notes: Validated RSS controls in `protocol.resource_controls`, public fit/resume preflight and worker `run_fit`: positive integers only, formal upper bound 8 GiB, conservative lower formal limits accepted. Effective limits and development override/inherited override classification are saved in config/report/status/summary; resume, formal selection and report cannot promote incomplete resource controls. Updated README. `test_temporal_stage_limits.RssControlTests` covers both public paths (default/exact/lower/raised/invalid), rejection before preflight/worker/output, worker validation, injected 8 GiB+1 breach without allocation, development audit fields and two resume generations. Final focused command `PYTHONPATH=benchmark/multivariate_time_series/tests /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest test_temporal_stage_limits`: 9 tests passed (4.509 s). Full recurrent suite under host process-monitor access: 127 tests passed (91.514 s; includes the first 7 new regressions); two subsequently added cases also pass in the final 9-test run. Strict OpenSpec validation and `git diff --check` pass. Only synthetic/temp development executions and pure formal control fixtures; no formal experiment or high-RSS allocation.
- Reverification notes: Retained independent full recurrent suite and affected-path inspection/probes remain applicable; this refresh additionally verified main-spec equivalence and validation. Earlier unchanged supporting probes are retained only where applicable, as stated in the verification basis.

### V-011: Live batch stages ignore the exhausted cumulative budget

- Category: implementation
- Severity: high
- Requirement: Resource preflight and cost limits are enforceable; P02 §6 cumulative 12 h includes checks and requires pausing at the limit.
- Evidence: Current `LiveStageBudgetTests` passes all five exhausted stages without entering core work, injected mid-read and final-publication crossing, owned-output invalidation/selection revocation, full pause/failure billing, destination isolation and offline behavior. Appendix A independently refuses exhausted recompute without entering metrics, prevents a fresh explicit ledger from replacing an exhausted linked ledger, detects another execution's charge on refresh, bills 43201.1 total seconds and passes offline comparison with input digests unchanged.
- Expected: Mandatory protocol behavior and complete, independently checkable evidence.
- Actual: Original counterexample corrected; required rejection/pause/success behavior verified on the current basis.
- Repair status: verified-resolved
- Repair notes: Replaced accounting-only stage wrapper with a context-local live batch guard: check before entering all five stages, heartbeat/reload ledger during work, cancel between saved reads, 1 MiB hash blocks, metric units, seeds/history and inference chunks, and check final publication time. Every exit bills full elapsed work including failure publication. Exhaustion retains external failed check reports or paused fresh run/block evidence; a late publication overrun invalidates only output created by that invocation and revokes its frozen selection. Existing/aliased input destinations remain protected. Reports/returns distinguish live-batch from offline; missing original ledgers permit independent offline checks, while explicit live ledger requests require an existing ledger and cannot replace other linked budget checks. Changes span resources/artifacts/checks/diagnostics/model/selection/report/runner and README. `test_temporal_stage_limits.LiveStageBudgetTests` covers all five exhausted stages, no core work entry, injected mid-read cancellation, final-publication crossing, full ledger billing (including pause summary), selection revocation, unchanged input digests, existing/inside-input destination refusal and offline checking. Final focused suite: 9 tests passed (4.509 s). Full recurrent suite with host psutil access: 127 tests passed (91.514 s); two later-added regressions passed in the final focused suite. Earlier sandbox-only broader attempt encountered known macOS process-monitor denial; host run resolves it. Strict OpenSpec validation and `git diff --check` pass. Cancellation is cooperative between bounded units; a running native array/file operation completes before the next checkpoint. No real-data execution or research record changes.
- Reverification notes: Retained independent full recurrent suite and affected-path inspection/probes remain applicable; this refresh additionally verified main-spec equivalence and validation. Earlier unchanged supporting probes are retained only where applicable, as stated in the verification basis.

## Next Action

Current-basis independent verification passed. The change is eligible for `$openspec-e13-archive-change fix-effective-temporal-training-acceptance`. Relevant implementation/planning edits require verification again. This report authorizes no formal research execution or research acceptance.

## Appendix A: Current Independent Boundary Probes

Save this exact script to `/tmp/e13_temporal_third_probe.py` and run from repository root with the `PY` interpreter above. It uses synthetic saved fixtures, temporary development outputs and injected resource/clock values. Formal arguments are parsed and validated only; no formal fit/resume is executed. Expected outcomes: accepted exact/lower formal RSS controls stop at 8 GiB+1, relaxed/invalid controls reject; exhausted recompute=`failed` with no metrics entry; explicit fresh-ledger selection=`paused`; refreshed batch total=43201.1 s and failure; offline compare=`pass` and inputs unchanged.

```python
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path[:0] = [str(Path.cwd()), str(Path.cwd()/'benchmark/multivariate_time_series/tests')]
import temporal_fixtures as fx
from benchmark.multivariate_time_series.temporal import checks, cli, protocol, resources, runner, selection

out = {'formal_rss': {}}
for op in ('fit', 'resume'):
    rows = []
    for limit in (protocol.MEMORY_STOP_BYTES, protocol.MEMORY_STOP_BYTES-1, protocol.MEMORY_STOP_BYTES+1, 0, -1):
        command = [op, '--data-name', 'r0', '--run-id', 'pure-control', '--purpose', 'formal', '--memory-limit-bytes', str(limit)]
        if op == 'resume':
            command += ['--parent', '/tmp/unused-e13-parent']
        args = cli.build_parser().parse_args(command)
        try:
            controls = cli._preflight_request(args, operation=op)['resource_controls']
        except protocol.ProtocolError:
            assert limit <= 0 or limit > protocol.MEMORY_STOP_BYTES
            rows.append({'limit': limit, 'accepted': False})
        else:
            assert 0 < limit <= protocol.MEMORY_STOP_BYTES and controls['complete']
            sample = resources.Watchdog(sampler=lambda: {'rss_bytes': protocol.MEMORY_STOP_BYTES+1}, limit_bytes=controls['rss_stop_bytes']).sample_once()
            assert sample['status'] == 'breach'
            rows.append({'limit': limit, 'accepted': True, 'sample': sample['status']})
    out['formal_rss'][op] = rows

class Clock:
    value = 0.
    def __call__(self): return self.value

with tempfile.TemporaryDirectory(prefix='e13-third-') as tmp:
    root = Path(tmp)
    run = fx.synthetic_completed_run(root/'inputs', 'saved')
    ledger = resources.Ledger(root/'ledger.json', batch_id='p02-t006')
    ledger.record(execution_id='previous', run_id='prior', seconds=protocol.BATCH_SECONDS)
    document = fx.read_json(run/'config.json')
    document['budget'] = ledger.payload_view()
    fx.write_json(run/'config.json', document)
    before = fx.tree_digest(root/'inputs')
    with patch.object(checks, '_recompute_fit_metrics', side_effect=AssertionError('must not enter')) as work:
        result = checks.run_recompute(run_dir=run, report_path=root/'exhausted.json', argv=[])
        assert not work.called and result['status'] == 'failed'
    out['exhausted_recompute'] = {'status': result['status'], 'work_entered': work.called, 'report': fx.read_json(root/'exhausted.json')['status']}
    # A second, fresh explicit ledger must not replace the linked exhausted one.
    fresh = resources.Ledger(root/'fresh.json', batch_id='p02-t006')
    fresh.record(execution_id='fresh', run_id='fresh', seconds=0)
    with patch.object(selection, 'load_candidate', side_effect=AssertionError('must not enter')) as work:
        result = runner.run_select({'purpose':'development', 'block_id':'guarded', 'candidates':[str(run)]*2, 'output_root':str(root/'outputs'), 'ledger_path':str(fresh.path)})
        assert not work.called and result['status'] == 'paused'
    out['fresh_explicit_cannot_bypass_linked_budget'] = result['status']
    # Crossing caused by another recorded stage must be seen on guard refresh.
    clock = Clock()
    ledger = resources.Ledger(ledger.path, batch_id='p02-t006')
    other_spent = sum(e['seconds'] for e in ledger.payload['entries'] if e['execution_id'] != 'previous')
    ledger.record(execution_id='previous', run_id='prior', seconds=protocol.BATCH_SECONDS-10-other_spent)
    def changed_budget(*args, **kwargs):
        current = resources.Ledger(ledger.path, batch_id='p02-t006')
        current.record(execution_id='other', run_id='other', seconds=10)
        clock.value = 1.1
        resources.check_stage_budget()
        raise AssertionError('guard did not refresh')
    with patch.object(resources.time, 'monotonic', clock), patch.object(checks, '_recompute_fit_metrics', side_effect=changed_budget):
        result = checks.run_recompute(run_dir=run, report_path=root/'refreshed.json', argv=[])
    assert result['status'] == 'failed'
    live = resources.Ledger(ledger.path, batch_id='p02-t006')
    assert abs(live.active_seconds()-(protocol.BATCH_SECONDS+1.1)) < 1e-7
    out['live_refresh'] = {'status': result['status'], 'active_seconds':live.active_seconds()}
    ledger.path.unlink()
    result = checks.run_compare(run_a=run, run_b=run, report_path=root/'offline.json', argv=[])
    assert result['status']=='pass' and result['accounting']['mode']=='offline'
    assert fx.tree_digest(root/'inputs')==before
    out['offline'] = {'status': result['status'], 'mode':result['accounting']['mode'], 'inputs_unchanged':True}
print(json.dumps(out, indent=2, sort_keys=True))
```
