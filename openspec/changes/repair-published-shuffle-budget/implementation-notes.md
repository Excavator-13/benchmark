# Implementation Notes

Diagnostic follow-up: see [evidence/diagnosis-20261019.md](evidence/diagnosis-20261019.md). Confirmed missing pip evidence, Windows resource-module assumptions, and CRLF patch reconstruction failure. Isolated torch import succeeds; original DLL failure remains unexplained. No implementation fixes or matrix retries in this follow-up.

- Change: `repair-published-shuffle-budget`
- Schema/store: `spec-driven`, repo-local
- Implementation root: `C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark`
- Updated: 2026-10-19, Asia/Shanghai
- Revision: `02f7d19b0912decc964510ad8991c3364e7df957` plus dirty implementation/tests/README; unrelated dirty research records predate apply and were not edited by this workflow.
- Progress: **10/15 tasks checked; paused at the user's requested failure boundary.** Task 2.3 has shared legacy-audit fixture coverage but not the complete historical-run acceptance evidence; 4.2/4.3/4.4/4.5 remain unchecked. These notes are a partial handoff, not completion evidence for 4.5 or an independent verification verdict.
- Immediate blocker: the first published r2/seed0 graph preparation failed loading `torch/lib/c10.dll` with `WinError 1114` during environment capture. No published graph swaps or model training occurred in that probe. Full suites also showed failures before being interrupted. Do not automatically retry or raise the shuffle budget.

## Current repair follow-up (supersedes the immediate-blocker diagnosis above)

User-authorized Windows/environment repairs are implemented; see
[evidence/repair-followup.md](evidence/repair-followup.md) for exact changes,
commands, failures, final focused reruns and remaining coverage limitations.
Pip 24.0 was bootstrapped offline; native Windows memory is shared by baseline,
skeleton and graph preparation; source-patch LF handling and deterministic test
repositories are fixed; readiness preserves original failure and pause evidence
when cleanup fails. POSIX signal tests explicitly skip on Windows.

Full skeleton: 127 tests with one new legacy-fixture failure, subsequently fixed
and passed in a focused rerun. Full baseline: 287 tests with Windows assumptions
reported; final affected 29-test rerun passes with 3 explicit skips. Neither full
suite is relabeled PASS. New v1-contract saved-run recompute passes without input
mutation; original archived v1 evidence remains untested.

**Paused again:** fresh serial r2 probe `repair-shuffle-v2-20261020-02` failed at
source_capture, WinError1114/c10.dll, 5.5722 s, zero graphs completed. No parallel
suite was active. Isolated torch and fixture training succeed, so preparation
child environment/import sequence remains unresolved. No retries, nine-graph
matrix or formal training followed. Progress remains 10/15; no independent
verification or T002 acceptance claimed. No Python workers remained on inspection.

## Implementation Map

| Task / scenario | Code and tests | Result and context |
| --- | --- | --- |
| 1.1 finite version contract | `protocol.py`, `config.py`, `tests/test_shuffle_v2.py`, README prepared-controls chapter | Candidate `dds-v2`: 10E successes / 500E attempts / 4096 proposal pairs; known v1 contract retained. Candidate not accepted for published readiness. |
| 1.2 sequential optimization | `shuffle.py`, scalar oracle in `tests/test_shuffle_v2.py` | Exact canonical edges, attempt/accept/rejection counts agree across buffer sizes 1, 7, 4096 and non-power-of-two edge counts. |
| 1.3 membership comparison | `benchmark_membership.py`, `evidence/membership.json` | Published r2/context12 source, bounded target 1E. Three set trials 0.210–0.218 s; dense trials 0.235–0.244 s; identical 257385 attempts / 22408 successes and hashes. Default remains set; no full-shuffle/training speed claim. |
| 1.4 failure/progress | `ShuffleError.diagnostics`, `_swap_edges`, `shuffle_graph`, `runner.py`, `prepared.py` | Context and at-most-100000-proposal snapshots; prior-context audits; failing target/limit/counts/elapsed/reason. Fixture failure/interruption paths pass; actual Windows hard kill leaves detectable unfinished status. |
| 2.1/2.2 graph-only preparation/check | `prepared.py`, CLI commands, `tests/test_prepared.py` | Exclusive development outputs; numeric non-pickle arrays; provenance/checksums; canonical/degree/locality/audit checks. Corruption, mismatches and incomplete statuses reject; saved-only check does not mutate input. Windows graph-preparation peak working set has a separate native measurement implementation. |
| 2.3 partial legacy compatibility | `checks.validate_shuffle_audit`, `protocol.shuffle_contract`, legacy scalar fixture | Shared audit oracle now dispatches v1/v2, rejects unknown or contradictory factors. Legacy audit fixture passes. A full historical saved-run recompute has not yet been demonstrated; leave task unchecked. |
| 3.1/3.2 graph reuse | `RunConfig.shuffle_artifact`, worker serialization, `runner.py`, `prepared.load`, `tests/test_prepared.py` | Source/node/seed/generator mismatch fails before training without fallback. Fresh/reused fixture fits independently complete 200 epochs, compare at existing tolerance and recompute after external graph directory is hidden. Per-run `shuffle-preparation.json` retains actual generation metadata; path/hit/read timing are outside computational identity. |
| 3.3 platform assumptions | `test_model.py`, `test_artifacts.py` | Real torch version remains recorded, accepted pinned suffix +cpu. Cross-batch-shape equivalence uses existing normalized 1e-6; exact same-shape and isolated/empty-graph assertions retained. |
| 4.1 watchdog driver | `readiness.py`, `tests/test_readiness.py`, README | r2/0 first, two fresh copies per condition, 600 s elapsed / 60 s no-progress defaults; failure stops scheduling and writes paused manifest. Driver does not schedule models. |

## Checks Run

All commands ran at the implementation root using the existing `.venv-pinned` Python 3.11.17 CPU environment. `evidence/pause-summary.json` records exact invocations, results, interrupted suites and source/test SHA256 at pause.

| Command | Setup | Result / evidence |
| --- | --- | --- |
| `.venv-pinned/Scripts/python.exe -B -m unittest benchmark.graph_value_skeleton.tests.test_shuffle_v2 benchmark.graph_value_skeleton.tests.test_shuffle -v` | Existing environment | 16 tests OK, 4.193 s; exact stdout was returned by tool. |
| `.venv-pinned/Scripts/python.exe -B openspec/changes/repair-published-shuffle-budget/benchmark_membership.py` | Existing environment | Six bounded backend executions passed exact count/hash agreement; `evidence/membership.json`. |
| `.venv-pinned/Scripts/python.exe -B -m unittest benchmark.graph_value_skeleton.tests.test_prepared benchmark.graph_value_skeleton.tests.test_shuffle_v2 benchmark.graph_value_skeleton.tests.test_readiness benchmark.graph_value_skeleton.tests.test_model -v` | `PYTHONUTF8=1` | **28 tests OK**, 162.699 s; `evidence/targeted-tests.log`. PowerShell stderr redirection marked the shell command as a native error despite unittest's final OK; judge the retained test output, not that shell exit. |
| `.venv-pinned/Scripts/python.exe -B openspec/changes/repair-published-shuffle-budget/run_tests.py skeleton --label skeleton-v2` | `PYTHONUTF8=1` | Interrupted after failures; partial `evidence/skeleton-v2.log`. No final suite verdict or success JSON. |
| `.venv-pinned/Scripts/python.exe -B openspec/changes/repair-published-shuffle-budget/run_tests.py baseline --label baseline-regression-02` | `PYTHONUTF8=1` | Interrupted after failures; partial `evidence/baseline-regression-02.log`. Baseline runtime/tests were not modified. |
| `.venv-pinned/Scripts/python.exe -B -m benchmark.graph_value_skeleton.readiness --run-id repair-shuffle-v2-20261019-01` | `PYTHONUTF8=1`; driver pins thread environment | First member failed before graph work: `WinError1114`, c10.dll initialization, elapsed 6.48 s; `evidence/r2-probe-*`, complete original directory under ignored scratch. **0/18 completed**, no canonical published result hash. |

The first baseline harness attempt could not discover its non-package tests directory. The harness was corrected, retaining that attempt's incomplete log; the second attempt actually ran the suite. An initial preparation test incorrectly read `epochs` from selection.json; it was corrected to training-history.json, and the subsequent 28-test run passed. Earlier non-UTF8 invocation exposed GBK diagnostic decoding errors; use PYTHONUTF8=1 for continuation. An initial model test still contained a second exact torch-version assertion; corrected as part of 3.3.

Observed full-skeleton failures: `test_measurements_are_measured_and_scoped` (existing POSIX-only resource expectation), `test_darwin_linux_and_unsupported_unit_conversion` (error), and `test_capture_scope_excludes_unrelated_records_tests_and_caches` (failure; cause uninvestigated). Observed baseline failures include `test_compare_consumed_inputs_include_fold_metadata_and_mean` for folds A/B and `test_compare_same_fold_same_seed`; causes uninvestigated. Do not classify these all as benign platform issues or claim either full suite passed.

The existing tests also attempt symlink creation unavailable under current Windows privilege (WinError1314). `run_tests.py` reports only that precise OS condition as an explicit skip; assertion errors are never skipped. Symlink branches are not verified in this environment. No production path protections were relaxed.

## Pause and Process State

After the first published preparation failure, scheduling paused automatically. At the user's previously requested failure boundary, the two remaining full-suite process trees were stopped: root PID39564 / worker33020 and root5552 / worker32960. Default-permission taskkill was denied; reviewed escalation terminated both. A transient child23688 was reported by taskkill; a subsequent Get-Process check found none of these PIDs. Both tool sessions finished with exit1. No automatic retry was scheduled and no formal training was launched.

The readiness driver itself retained `state=paused` and worker `state=failed`; inspect `scratch/graph-value-skeleton/repair-shuffle-v2-20261019-01/`. Full-suite logs stop mid-suite and are explicitly incomplete. Test fixture runs exist in system temporary storage; useful final output was copied into this change's evidence. No research records, delegation pointer, datasets or archived runs were edited during apply; no commits/pushes or archive action were performed.

## Verification Reminders / Next Implementation Work

1. Diagnose c10.dll initialization under the failed worker's environment before any retry. The failure occurred during a concurrent test load; this is context, not a proven cause. Preparation uses `capture_environment`, which imports torch even though graph generation itself does not train a model. Changing this capture behavior would need to retain the specified provenance contract.
2. Investigate the listed skeleton and baseline regression failures with complete diagnostic output. Do not weaken tests, drop requirements or label platform limitations as passes. Baseline source-capture/compare behavior is outside this implementation's code changes and must be understood before deciding whether more scope is necessary.
3. Actual watchdog hard-kill was not exercised on a long published worker. The sandbox denied default-permission taskkill for the full-suite roots; continuation must ensure owned-child termination can be performed and report a termination failure instead of claiming the process stopped. Fixture watchdog tests use controlled process doubles.
4. Finish task2.3 with genuine legacy saved-run evidence, then full regression completion, r2 probe and all nine graphs plus independent regenerations in fresh IDs. Never resume/overwrite this failed readiness run. Do not silently revise `500E` or reduce `10E` if a numerical graph failure appears.
5. The current artifact checker validates saved checksums and graph invariants; it does not establish generation authenticity for forged files. Independent regeneration is still required. Review provenance and all failure/interruption branches independently.
6. Check interruption/error consistency across model runner, preparation and Windows worker transport. Hard termination can only leave a detectable unfinished marker; it must never publish success.
7. No complete nine-graph readiness manifest, published model-cost measurement, full-suite success or independent verification exists. All performance numbers above describe bounded graph work or fixtures; no predictive-quality conclusion is supported.

## Research-side Follow-up (not implemented here)

After independent verify, archive and separate research acceptance, use a new cost/batch identity. Carry design.md's conservative pause policy into that controller: stop on identity/invariant/numerical failures, pause when measured progress estimates more than 24 hours remaining local cost, and consider predictive quality only at a fully completed dataset block with all methods/seeds/repetitions and the unchanged P02 gates. A failing complete block may pause remaining work but is not a final full-matrix conclusion. Preserve 200 epochs, validation-MSE selection and no training early stopping. No research model-scheduling controls were implemented by this change.
