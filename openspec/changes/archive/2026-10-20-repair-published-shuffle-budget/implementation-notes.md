# Implementation Notes

- Change: `repair-published-shuffle-budget`; schema: `spec-driven`; store: local.
- Root: `C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark`.
- Updated: 2026-10-20, Asia/Shanghai.
- Revision: `dc9933081e396f3d6c92c801c2f080954de464ec` plus dirty runtime/tests/README and evidence. Earlier evidence keeps its captured historical revision. No commit/push by this workflow.
- Progress: 15/15 implementation tasks complete. Final published matrix, protected-file check and both full independent suites pass with explicit environment skips. Independent whole-change verdict remains the verifier's responsibility.

## Implementation Map

| Tasks / requirements | Code/tests | Evidence / decisions |
| --- | --- | --- |
| 1.1/1.2 finite sequential version | protocol.py, shuffle.py, test_shuffle_v2.py | dds-v2:10E accepted/500E attempts/4096 buffered ordered proposals. Scalar oracle, exact decision/count/edge equality, empty/exhausted/unchanged contexts. |
| 1.3 membership backend | benchmark_membership.py; evidence/membership.json | Three bounded context12 set trials0.210-0.218s vs dense0.235-0.244s; identical257385 attempts/22408 successes/hash. Keep tuple/set. No full-work speedup claim. |
| 1.4 failure/progress | shuffle.py, runner.py, prepared.py and tests | Context boundaries and at most100000 consumed proposals between snapshots; failure counts/identity/context/elapsed survive; unfinished artifacts reject. |
| 2.1/2.2 graph-only preparation/checking | prepared.py, cli.py, test_prepared.py | Exclusive development outputs, non-pickle canonical arrays, audit/checksums, saved-only invariants, no model creation. V-001 requires recorded source/generator/environment fields and consistency without current-source reads. V-003 retains per-context swap times in measurements only. |
| 2.3 strict historical checks | checks.py, protocol.py, test_prepared.py | Genuine scalar v1 fixture and full v1-contract saved-run recompute under v2 defaults, inputs unchanged. V-002 allows legacy batch omission; explicit batch must be exact integer1 for v1,4096 for v2. |
| 3.1/3.2 reuse | config.py, cli.py, runner.py, prepared.py and tests | Mismatch fails before training, no fallback. Fresh/reused independent200epoch fixture fits compare1e-6 and recompute1e-12 without external graph directory. Cache path/hit/time excluded from semantic identity; actual source/runtime retained. |
| 3.3 numeric/platform tests | test_model.py, test_artifacts.py | Preserve full torch+cpu metadata, normalized1e-6 only across batch shapes; exact same-shape/isolated/empty contracts retained. |
| 4.1 watchdogs | readiness.py, test_readiness.py | 600s elapsed/60s no-progress, stop on failure, retain original reason plus any cleanup failure. No model scheduling. |
| 4.2 r2 first probe | evidence/r2-probe-dll-fixed.json; evidence/dll-resolution-20261020.md | Two results match;52 contexts. Context12:224080 successes/2581117 attempts vs old2240800 and candidate11204000 ceilings. |
| 4.3 all published graph seeds | evidence/published-readiness-accepted.json; scratch/graph-value-skeleton/repair-shuffle-v2-20261020-06 | 18/18,9 matching canonical pairs,360 per-context timing records; strict saved checks pass. All result hashes equal matrix05. dds-v2 candidate10E/500E/4096 now passes development readiness; no historical timing backfill. |
| Platform integration | baseline artifacts.py/runner.py, skeleton artifacts.py/cli.py and tests | Native Windows memory, proven LF patch reconstruction, offline ensurepip, torch-before-Arrow import order, bounded same-temp atomic retry. P01 gains no torch dependency. |

## Checks Run

Repository-root commands use `.venv-pinned/Scripts/python.exe -B`, PYTHONUTF8=1. Readiness and independent runners pin BLAS threads1. Runtime:Python3.11.17/torch2.14.1+cpu/numpy1.26.4/pandas2.2.3/pyarrow17.0.0; pip24 bootstrapped offline only into this venv.

| Command / check | Result / evidence |
| --- | --- |
| `-m benchmark.graph_value_skeleton.readiness --run-id repair-shuffle-v2-20261020-05` |18/18 successful; nine matching canonical pairs. Later V003 found absent context timing metadata, so not final accepted readiness. |
| `-m benchmark.graph_value_skeleton.readiness --run-id repair-shuffle-v2-20261020-06` |18/18 success with all context timing records,9 identical regeneration pairs and unchanged numerical generator; evidence/published-readiness-accepted.json. |
| V001/V002 focused regressions plus scalar/atomic tests | evidence/verification-fix-focused.json and log:12 tests,0 failures/errors,31.235s. Before repair, added regression methods reproduced13 failing subcases. |
| `-m unittest benchmark.graph_value_skeleton.tests.test_atomic_writes -v` |4 tests pass0.266s; real Windows CreateFileW sharing denial/release. evidence/atomic-write-repair.md documents bounded policy. |
| `run_tests.py baseline --label independent-baseline-20261020-01` |287 tests,0 failures/errors,8 explicit skips,439.547s; evidence/independent-baseline-20261020-01.json/log. Includes no-torch all-schema CLI compatibility. |
| `run_tests.py skeleton --label independent-skeleton-20261020-01` |134 tests,0 failures/errors,4 explicit skips,831.281s harness wall time (unittest828.638s); evidence/independent-skeleton-20261020-01.json/log. Complete after baseline, with graph-only matrix concurrent; no model-cost measurement concurrent. |
| V003 timing fix |evidence/verification-fix-timings.json/log:4 tests pass,34.781s; missing/negative/nonfinite context time rejection and separation from graph semantic identity. |
| Independent published saved checks |scratch/graph-value-skeleton/independent-published-check-20261020-01/summary.json:18 pass,9 pairs,360 timings,each38 files unchanged; summary SHA256 c3e7035067cfcd1a33db4c93656de094bef89f3c4105b3b26ef2581f1ec2267b. |
| Protected pre-existing inventory |evidence/protected-final-regressions.json:640 files unchanged, formal T002 runs0. Limited prior inventory, not a new-file scan. |

Earlier failed/partial suite verdicts remain in [historical notes](evidence/historical-implementation-notes-20261020.md), [repair follow-up](evidence/repair-followup.md), [DLL investigation](evidence/dll-resolution-20261020.md). They are not current full-suite passes. Failed matrix04, its WinError5 checkpoint and temp file remain untouched. The locking process is unknown; a Windows sharing mechanism was reproduced without attributing it to a scanner/editor.

## Verification Reminders

- Independent verification must resolve V001/V002/V003 and review the whole change. Repair checks cannot declare PASS.
- Saved checks validate recorded identity structure/invariants, not arbitrary forged history authenticity. Ordinary saved checks never require current generator equality; reuse additionally requires current numerical source/runtime identity.
- Exact WinError1314 symlink-privilege failures are explicit skips, never passes. Baseline also skips optional sklearn (2), POSIX signals (2), and a user-permission probe (1), plus symlink cases (3). Skeleton skips4 symlink cases. No protection/tolerance relaxed; these paths remain unverified here.
- Fresh Windows CLI regression passes in the full suite; an in-process test alone may hide the torch/Arrow DLL import-order defect.
- A real controlled Windows watchdog test preserves TimeoutError and cleanup failure, but automatic taskkill cannot terminate the child in this restricted tool environment. The harmless child exited naturally and was joined; no child remains. Actual cleanup denial is surfaced as paused/worker_may_be_running, never success. Operational termination may require reviewed tool escalation.
- No comparable completed v1 published timing exists; graph costs do not establish training speed, mixing or predictive benefit.
- Scratch artifacts are local/ignored, addressed by retained evidence manifests. No sealing or backup/recovery check requested/performed.

## Research-side Handoff (not implemented here)

Model scheduling controls are **not implemented by this change**. After current independent PASS, archive and separate research acceptance, use a new cost/batch identity; never restart old failed batch p02-t002-20261019-01. Measure fresh r0/r2 costs before formal scheduling.

The design's24h default is superseded this session by the user's stricter deadline2026-10-20 18:23:51 Asia/Shanghai (five hours from13:23:51, earlier than18:30). Use observed work with extrapolation uncertainty; node ratios are not measured runtimes. Pause on invariant/checksum/identity/reproducibility/nonfinite failures. Resource/deadline interruptions remain incomplete, resume only with fresh IDs/full200epochs; no scientific budget reduction.

Quality pause occurs only after a complete dataset block with all methods/seeds/repetitions, independently fit three-shuffle arithmetic means and unchanged P02 gates. No interim test tuning/stopping. A partial matrix cannot complete T002/T003. No predictive-benefit or T002-completion claim is made.

Independent commands: run_tests.py baseline --label <fresh>; run_tests.py skeleton --label <fresh>; check-shuffle --artifact-dir <each matrix06 member> --report <fresh external report>; local CLI validate repair-published-shuffle-budget --type change --strict --json --no-interactive. Use the current verifier report for exact independent observations and evidence fingerprints.

Current measured graph-only worker ranges (six per dataset):r0 20.8-22.6s,region28.4-29.4s,r2 46.8-50.8s; maximum r2 process peak working set550211584 bytes via GetProcessMemoryInfo. Data/source identities, per-context measurements and reports are in published-readiness-accepted.json and its resolvable member paths; all18 result hashes agree with matrix05.
