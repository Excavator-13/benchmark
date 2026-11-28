# Implementation Notes

- Change: extend-effective-training-budget-v2
- Schema: spec-driven
- Store: local
- Implementation roots: `E:\大创\benchmark`
- Updated: 2026-11-27 (Asia/Shanghai)
- Implementation revision: `4993778f0fb2a11cbfc0339ad265f489479a1d3c`; worktree dirty with this change's implementation and handoff files
- Progress: 12/12 tasks complete; implementation complete and ready for independent verification

## Implementation Map

| Task / requirement / scenario | Code and tests | Decisions / context |
| ----------------------------- | -------------- | ------------------- |
| 1.1 v2 controls and formal-length refusal | `benchmark/multivariate_time_series/temporal/protocol.py`, `cli.py`, public entry, `test_temporal_data.py`, `test_temporal_cli.py`, `test_temporal_selection_diagnostics.py` | Current profile is v2 with 200 epochs, 3,800 updates, diagnostics at 10/50/100/200, and tail cutoff 160. Formal shorter requests fail before worker creation. Development overrides remain incomplete. |
| 1.2 dual-document identity | `protocol.py`, `artifacts.py`, `runner.py`, `checkpoints.py`, `selection.py`, `recovery.py`, `checks.py`, `diagnostics.py` | Identity payload orders `protocol-v2.md` then inherited `protocol.md`. Current v2 LF-normalized SHA256 is `c454954e9443cc363ebf94a23809d8ee003ecdc7844b693d38cb5f304db283d0`. Inherited LF-normalized SHA256 is `2f583a3a7f771cfe82c36eb8983e37bfadf65c7c1ee62355d97bdae34872a5f2`, matching the research declaration. CRLF checkout bytes normalize to Git blob bytes for protocol identities. No research protocol was edited. |
| 2.1 complete diagnostics | `engine.py`, `diagnostics.py`, `tests/temporal_fixtures.py`, `test_temporal_selection_diagnostics.py` | Exact ordered 200-epoch history, complete score blocks, exact diagnostic epoch/update boundaries, finite nonnegative metrics, and 100-epoch incompleteness are checked. |
| 2.2 tail stability | `diagnostics.py`, `test_temporal_selection_diagnostics.py` | New minima are `b160` and `b200`. Fixtures cover reversed v1/v2 decisions, the exact 1% edge, both-zero behavior, and 2/3 aggregation. |
| 2.3 version compatibility | `protocol.py`, `selection.py`, `diagnostics.py`, `checks.py`, `checkpoints.py`, `recovery.py`, `test_temporal_selection_diagnostics.py`, `test_temporal_artifacts_checks.py` | Saved v1 evidence is explicitly rejected with runner references `3bd9fa4` and `bf5abed8`. Numerically equal arrays do not permit cross-version comparison. |
| 3.1 ledger accounting and validation | `resources.py`, `runner.py`, `recovery.py`, `cli.py`, `test_temporal_resources_recovery.py` | Ledger format stays additive at version 1. Published debits are mirrored in a registry, and entry/registry mismatch fails closed. Forecasts remain nonbinding. |
| 3.2 public debit operation | `cli.py`, `resources.py`, `test_temporal_cli.py`, `test_temporal_resources_recovery.py` | `budget-debit` requires an existing matching batch ledger. Stable identical replay is idempotent and changed reuse is rejected without data or worker access. |
| 3.3 effective budget gates | `resources.py`, `runner.py`, `recovery.py`, `cli.py`, `test_temporal_resources_recovery.py`, `test_temporal_repairs.py` | Measured/replayed seconds plus debits govern fit, controller, resume, preflight and saved-stage limits. Forecast formula is `1.3*(setup + 2*200*t)`. Synthetic debit-only exhaustion stops fit and live recompute. |
| 3.4 preflight/helper metering | `resources.py`, `runner.py`, `cli.py`, `test_temporal_cli.py`, `test_temporal_resources_recovery.py` | Standalone preflight bills a supplied existing ledger once on pass and failure. Internal fit preflight bypasses independent billing. `record_helper_cost` records a unique measured operation. |
| 4.1 synthetic integration and regressions | `tests/temporal_fixtures.py`, temporal test suite | The staged development flow exercises fit/select/diagnose/report/recompute/compare with synthetic data, and same-v2 interruption/resume is independently tested. Full temporal suite was attempted. Its worker-lock takeover test is interrupted by a Windows temporary-path `FileExistsError` followed by `KeyboardInterrupt`; this lock test does not touch changed accounting logic. Other affected groups pass in focused runs. |
| 4.2 README and help | `README.md`, `cli.py`, `runner.py`, `test_temporal_cli.py` | README §4.7 documents v2 controls, dual identity, b160/b200, debit registration, accounting labels, historical limits and helper metering. `--help`, debit help, and `--version` were checked against parser behavior. |
| 4.3 implementation handoff and scope | This file | Research-owned ledger, run artifacts, protocols, T009 and legacy runners were not used or modified. Independent verification and research acceptance remain separate. |

## Checks Run

| Command | Working directory / setup | Result / evidence | Run time or revision |
| ------- | ------------------------- | ----------------- | -------------------- |
| `python -m compileall -q benchmark\multivariate_time_series\temporal benchmark\multivariate_time_series\effective_temporal_training.py benchmark\multivariate_time_series\tests` | `E:\大创\benchmark` | Passed | 2026-11-27 |
| `python -m unittest discover -s benchmark\multivariate_time_series\tests -p test_temporal_selection_diagnostics.py -v` | `E:\大创\benchmark`; workspace temp writes enabled | Passed, 26 tests including complete 200-epoch synthetic fit | 2026-11-27 |
| `python -m unittest discover -s benchmark\multivariate_time_series\tests -p test_temporal_cli.py -v` | `E:\大创\benchmark`; workspace temp writes enabled | Passed, 11 tests including formal 100-epoch refusal, debit replay, preflight pass/failure billing and version output | 2026-11-27 |
| `python -m unittest discover -s benchmark\multivariate_time_series\tests -p test_temporal_resources_recovery.py -k budget_debit -v` | `E:\大创\benchmark`; workspace temp writes enabled | Passed, 2 tests covering ledger debit and fit exhaustion | 2026-11-27 |
| `python -m unittest discover -s benchmark\multivariate_time_series\tests -p test_temporal_resources_recovery.py -k interrupted_and_resumed -v` | `E:\大创\benchmark`; workspace temp writes enabled | Passed, deterministic interrupted same-v2 resume | 2026-11-27 |
| `python -m unittest discover -s benchmark\multivariate_time_series\tests -p test_temporal_resources_recovery.py -k replay_and_failed_work -v` | `E:\大创\benchmark`; workspace temp writes enabled | Passed, replay and failure costs remain charged | 2026-11-27 |
| `python -m unittest discover -s benchmark\multivariate_time_series\tests -p test_temporal_resources_recovery.py -k exhausted_or_mismatched_parent -v` | `E:\大创\benchmark`; workspace temp writes enabled | Passed, exhausted or mismatched parent recovery refused | 2026-11-27 |
| `python -m unittest discover -s benchmark\multivariate_time_series\tests -p test_temporal_repairs.py -k recovery_rejects_environment_source_and_ledger_replacement -v` | `E:\大创\benchmark`; workspace temp writes enabled | Passed | 2026-11-27 |
| `python -m unittest discover -s benchmark\multivariate_time_series\tests -p test_temporal_repairs.py -k debit_exhaustion -v` | `E:\大创\benchmark`; workspace temp writes enabled | Passed, live saved-evidence stage stopped with debit-only exhaustion | 2026-11-27 |
| `python -m unittest discover -s benchmark\multivariate_time_series\tests -p test_temporal_artifacts_checks.py -k identical_arrays_from_v1_and_v2 -v` | `E:\大创\benchmark`; workspace temp writes enabled | Passed, identical arrays rejected across scientific versions | 2026-11-27 |
| `python -m unittest discover -s benchmark\multivariate_time_series\tests -p "test_temporal*.py" -v` | `E:\大创\benchmark`; workspace temp writes enabled | Not fully clean. Tests passed through report/recovery cases, then the existing worker-lock takeover test hit `FileExistsError` in Windows `Path.mkdir` followed by `KeyboardInterrupt`. Resume and recovery tests were run separately and passed. | 2026-11-27 |
| `python -m unittest discover -s benchmark\nograph_baseline\tests -v` | `E:\大创\benchmark`; workspace temp writes enabled | Passed, 287 tests, 3 skipped due unavailable file-permission behavior | 2026-11-27 |
| `python -m benchmark.multivariate_time_series.effective_temporal_training --help` | `E:\大创\benchmark` | Passed; lists current staged operations including `budget-debit` | 2026-11-27 |
| `python -m benchmark.multivariate_time_series.effective_temporal_training budget-debit --help` | `E:\大创\benchmark` | Passed; required ledger, batch, debit ID, seconds and reason match parser | 2026-11-27 |
| `python -m benchmark.multivariate_time_series.effective_temporal_training --version` | `E:\大创\benchmark` | Passed; prints `P2-effective-training-L6-H3-v2` | 2026-11-27 |
| `git diff --check` | `E:\大创\benchmark` | Passed | 2026-11-27 |

## Verification Reminders

- Independent verification should rerun the full temporal suite. The worker-lock takeover case remains the only known environment interruption in the full run. Its preflight calls used a local Git identity stub during the focused attempt, but Windows interrupted a path check while claiming the stale lock. No lock implementation behavior was changed.
- Verify the full synthetic staged chain and the version-mismatch error paths in saved checks and checkpoints. Real demand data, the continuing research ledger, historical runs and formal outputs were not inputs.
- After independent PASS and research-side acceptance, register the single `p02-t006-v1-unmetered-preparation` debit for 900 seconds on the continuing research ledger, run fresh v2 preflight against that ledger, then start v2 trajectories from initialization. Do not resume v1 checkpoints. This apply turn did not execute that research-side step.
- No verification verdict is recorded here. Run `$openspec-e13-verify-change extend-effective-training-budget-v2` before archive or research acceptance.
