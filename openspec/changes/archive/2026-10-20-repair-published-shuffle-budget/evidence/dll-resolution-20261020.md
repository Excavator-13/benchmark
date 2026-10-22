# DLL resolution and subsequent readiness pause

Date: 2026-10-20, Asia/Shanghai. Implementation remains dirty on base
02f7d19b0912decc964510ad8991c3364e7df957. No independent verification verdict.

## Reproduction and repair

Fresh `.venv-pinned/Scripts/python.exe -B -c` processes tested these sequences:
torch alone and numpy then torch succeed; pandas then torch and pyarrow then
torch fail with WinError1114 loading c10.dll; torch then numpy/pandas/pyarrow
succeeds. See `dll-import-order.json`. This establishes import-order sensitivity
in this runtime, not the identity of an individual conflicting transitive DLL.

`cli._handle_prepare` imports torch on Windows before config imports the
pandas/Arrow data modules. It retains all runtime evidence and does not create a
model. P01 has no new torch dependency. Thread environment setup still precedes
these imports. README documents the behavior.

Regression command at repository root, PYTHONUTF8=1: `.venv-pinned/Scripts/python.exe
-B -c <unittest loader for test_prepared, test_readiness, test_config_cli>`.
The exclusive UTF-8 log is `dll-repair-targeted.log`: 24 tests, zero assertion
failures, two errors from existing WinError1314 symlink restrictions. The new
`PreparedTest.test_prepare_in_fresh_cli_process` succeeds in a fresh process,
checks completed artifact validation and absence of model/training artifacts.
In-process preparation, fresh/reused independent training, legacy saved-run
recompute, corruption and readiness cleanup paths also succeed. The two OS
errors are not labeled passes.

Task2.3 is now checked: current run includes legacy scalar v1 audit validation
and full v1-contract fixture saved-run recomputation under v2 defaults without
input mutation, plus unknown/contradictory audit rejection. Evidence is generated
fixture evidence; no claim about checking original archived v1 runs is made.

## Published probe succeeds

Exact command: `.venv-pinned/Scripts/python.exe -B -m
benchmark.graph_value_skeleton.readiness --run-id repair-shuffle-v2-20261020-03
--probe-only` (PYTHONUTF8=1; driver pins thread variables).

Both r2/seed0 independent graph workers succeed and saved-only checks pass.
Worker times 49.0 and 47.0 s; matching canonical result hash
`ad3e9775af9ed369a487f75c3891871f41260d22fc8746c1b4986dbbee173cc0`.
First worker measures shuffle 33.9837995 s, total stages 42.5976025 s,
548773888 bytes process peak working set through GetProcessMemoryInfo.
All 52 contexts complete. Context12 completes exactly 224080 accepted swaps in
2581117 proposals (old ceiling2240800, candidate ceiling11204000), preserving
invariants. It retains 15095/22408 source edges; overlap does not prove mixing.
There is no comparable completed v1 timing, so no full-work speedup claim.

Evidence: `r2-probe-dll-fixed.json` copies the readiness manifest with two
members, check paths/hashes and measurements. Originals are under
`scratch/graph-value-skeleton/repair-shuffle-v2-20261020-03/` including checks,
audits, progress, environment and source. Task4.2 checked after this success.

## New failure and automatic pause

Full-matrix command: `.venv-pinned/Scripts/python.exe -B -m
benchmark.graph_value_skeleton.readiness --run-id repair-shuffle-v2-20261020-04`.
First worker fails after26.1036 s while replacing its owned progress.json:
PermissionError WinError5, `.tmp-yz4gi6dr` -> `progress.json`. It has entered
shuffle; no DLL error recurs. The completed-candidate manifest has zero members
and state paused. No retry or subsequent matrix member is scheduled. The temp
file and previous checkpoint remain in the original directory. No reusable
complete graph from this failed attempt is accepted.

Evidence: `matrix-progress-write*` copies log, worker status, previous checkpoint
and paused manifest. Original directory is
`scratch/graph-value-skeleton/repair-shuffle-v2-20261020-04/`.
The direct failing call is RunDirectory.write_bytes -> os.replace; a transient
file lock, scanner or permissions cause has not been proven. No automatic
filesystem retry policy is introduced in this session. No Python workers remain
on inspection. Task4.3 remains unfinished; all nine conditions have not passed.

Protected research/dataset/archive hashes are compared in
`protected-after-readiness.json` against `protected-before-readiness.json`.
No formal training, research record changes, commit/push, or archive action.
Progress:12/15 checked; tasks4.3/4.4/4.5 remain unchecked. Existing full-suite
logs and their later focused fixes retain their original verdicts. Next work:
investigate the Windows atomic progress replacement failure and a bounded,
evidence-preserving retry policy; then retry in fresh IDs only if authorized.
