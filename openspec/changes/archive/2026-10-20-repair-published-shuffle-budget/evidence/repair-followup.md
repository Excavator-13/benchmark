# Windows/environment repair follow-up

User authorized the diagnosed repairs. No formal training, research record edits,
commits, pushes or archive actions are part of this follow-up.

## Implementation

- Bootstrapped pip 24.0 offline using `.venv-pinned/Scripts/python.exe -B -m ensurepip --upgrade`; existing setuptools retained. New runs can capture real `pip freeze` evidence. Historical artifacts are unchanged.
- Both source-capture implementations write temporary patches with explicit LF and apply them with `git -c core.autocrlf=false apply`. Git commit bytes are the reconstruction base; byte mismatches still use full-content fallback. No global Git configuration changed.
- `benchmark/nograph_baseline/artifacts.py:windows_peak_rss` provides native `GetProcessMemoryInfo.PeakWorkingSetSize` bytes. Both baseline and skeleton use it; graph preparation delegates to the skeleton measurement and labels its graph-worker scope. No optional torch dependency added to baseline.
- Readiness preserves the original failure and paused manifest even when owned-worker termination fails. Cleanup error, PID and possible-running state are retained. Watchdog timeout remains a TimeoutError with cleanup failure chained.
- Test repositories explicitly fix LF and local Git conversion settings. Tests require clean-reference behavior in disposable repositories, without assuming the user's dirty/CRLF checkout contains a byte-clean runtime file. Windows lacks the tested POSIX child SIGINT/SIGTERM semantics: those two tests explicitly skip there, while the hard-kill unfinished-state test remains enabled. No scientific or numerical tolerance changes.

## Checks so far

All commands run at repository root with `PYTHONUTF8=1` and `.venv-pinned/Scripts/python.exe -B`.

- Focused skeleton memory/source-capture/readiness tests: 5 passed in 2.651 s before adding native-peak and termination-failure regression tests. Full suite below covers the final tests.
- `openspec/changes/repair-published-shuffle-budget/run_tests.py baseline --label baseline-repair-03`: 287 tests, 803.904 s, 9 failures, 1 error, 6 skips. Full original result retained. Original fold comparisons and no-torch minimal-dependency smoke pass. Failures exposed additional Windows memory, LF fixture and POSIX signal assumptions. This process had loaded test definitions before the subsequent fixture repairs.
- Final focused baseline rerun: `SourceCaptureDeltaTests`, `RepairRegressionTests`, `RunnerArtifactTests.test_source_and_environment_capture`, `RunnerArtifactTests.test_measurements_record_real_units_and_settings`, and two POSIX signal tests; 29 tests, 72.404 s, zero failures/errors, 3 skips (two POSIX-only signals and permission behavior). Log: `baseline-repair-focused-final.log`. Earlier unsuccessful focused logs remain retained.
- `run_tests.py skeleton --label skeleton-repair-04`: running at time of this entry; no verdict yet.

The final focused baseline command adds `benchmark/nograph_baseline/tests` to
sys.path, loads the named tests with unittest.defaultTestLoader, and writes an
exclusive UTF-8 log. No full-suite pass is inferred from focused reruns.

Original DLL cause remains unproven: isolated torch import succeeds. Subsequent
workloads are serial. A fresh published r2 graph probe is still required.

## Final checks and pause

- Full skeleton harness `run_tests.py skeleton --label skeleton-repair-04`: 127 tests, 2101.199 s, one failure, zero errors, four Windows symlink-privilege skips. Sole failure was the newly added legacy fixture using the function-bound v2 default despite patching module constants. The fixture now explicitly supplies v1 10E/100E and scalar proposals. Production checks correctly rejected the contradictory evidence.
- Final focused legacy test `benchmark.graph_value_skeleton.tests.test_prepared.PreparedTest.test_legacy_saved_run_recomputes_under_current_defaults`: one test OK, 22.142 s, evidence `legacy-recompute-final.log`. It generates legacy-contract fixture evidence, independently trains, then checks saved evidence under current defaults without mutation. This is newly generated fixture evidence, not an original archived v1 run.
- The baseline full-run failures were followed by the 29-test successful focused rerun. No final complete baseline/skeleton suite PASS is claimed; full-suite logs retain the earlier failures. Original minimal-dependency/no-torch smoke succeeded in the full baseline run.
- Serial published probe command: `.venv-pinned/Scripts/python.exe -B -m benchmark.graph_value_skeleton.readiness --run-id repair-shuffle-v2-20261020-02 --probe-only` (`PYTHONUTF8=1`). Driver pins CPU thread variables. First worker failed after 5.5722 s at source_capture/environment import with WinError1114 loading torch/lib/c10.dll. No demand/graph/shuffle work reached; zero completed members. Driver retained paused manifest. Evidence `r2-probe-repair*`; original scratch directory unchanged.
- This serial reproduction weakens concurrency as the sole explanation for the original DLL failure. Isolated import and full fixture suite torch execution work, but the preparation child still fails. No package reinstall or import-order workaround attempted at this blocker. No further probes or model runs scheduled; process inspection showed no remaining Python workers.
- `git diff --check` passed apart from informational LF/CRLF checkout warnings after trailing whitespace cleanup. No commit/push or research acceptance occurred.

Next work is to isolate the preparation child's import sequence/environment DLL
failure. Candidate readiness remains incomplete; do not raise shuffle budgets,
claim speedup, start formal training or infer predictive quality from this run.
