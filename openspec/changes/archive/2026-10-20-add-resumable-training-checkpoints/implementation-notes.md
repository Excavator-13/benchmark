# Implementation Notes

- Change: add-resumable-training-checkpoints
- Schema: spec-driven; store: local
- Implementation root: C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark
- Updated: 2026-10-20; implementation revision: 2ca56dd plus dirty tracked/untracked implementation; unrelated research launch/reboot records predate this change.
- Progress: 14/14 implementation tasks complete after bounded repairs; independent reverification running. No formal training started.

## Implementation Map

| Tasks / requirement | Code and tests | Decisions |
| --- | --- | --- |
| 1.1–1.3 durable numeric checkpoints | checkpoints.py; tests/test_checkpoints.py CodecTest; README §4.6 | Object-free typed tree and numeric NPZ, SHA256 manifest published last, retain two generations, common Windows retry writer |
| 2.1–2.3 state continuation/progress | training.py, runner.py; CodecTest tie test and ProcessRecoveryTest; README | Restore full Adam/current/best/history/RNG, strict validated boundary, 200 total, observational chunk progress, cumulative vs attempt timing |
| 3.1–3.3 public recovery/evidence | config.py, cli.py, runner.py, checks.py; checkpoint_worker.py and ProcessRecoveryTest | Fresh output enforced by existing reservation; strict source/runtime/input/layout checks; self-contained parent copy; ancestry bound to provenance; historical compatibility |
| 4.1–4.3 controller | research/phases/P02/t002_r2_batch.py; tests/test_batch_recovery.py; README | Read-only recovery plan, fresh ledger, success reuse gated by recompute, OS lock plus live workers, configurable watchdogs, unchanged 30/51 gate |
| 5.1–5.2 integration | ProcessRecoveryTest, existing training/checks/artifact/baseline suites | Real process exit 73 after epochs 37/113/200; final recovery uses public CLI |

Paths above are under benchmark/graph_value_skeleton unless explicitly qualified.

## Checks Run

All commands run from implementation root using `.venv-pinned/Scripts/python.exe -B`, `PYTHONUTF8=1`, torch before Arrow on Windows.

| Command / check | Result / evidence |
| --- | --- |
| `-m unittest benchmark.graph_value_skeleton.tests.test_checkpoints.CodecTest -v` | Initial 3 codec tests passed; strict key/shape/dtype/nonfinite/RNG/Adam rejection, integrity/identity and publication faults |
| `-m unittest benchmark.graph_value_skeleton.tests.test_checkpoints.CodecTest.test_restore_best_before_cut_and_exact_ties -v` | PASS; tie selects epoch 1 across cut 37, exactly 163 remaining updates |
| `-m unittest benchmark.graph_value_skeleton.tests.test_checkpoints.ProcessRecoveryTest -v` | Initial 3-method process matrix PASS, 569.550s; C:/Users/Lenovo/AppData/Local/Temp/gvs-cp-process-y8gwaypi/evidence.json. This is historical within this apply: later lineage/provenance/timing improvements require current rerun below |
| `-m unittest benchmark.graph_value_skeleton.tests.test_checkpoints benchmark.graph_value_skeleton.tests.test_batch_recovery -v` | Current rerun running; public CLI, historical compatibility, mismatch rejection added |
| `-m unittest benchmark.graph_value_skeleton.tests.test_batch_recovery -q` | 7 tests PASS, including OS lock, stale release, matrix recovery, failure pause, runtime/stall stop and unavailable ETA |
| Baseline protocol/metrics/baselines/data/coverage/preprocessing | 100 tests PASS; invoke unittest with `sys.path.insert(0,'benchmark/nograph_baseline/tests')` because nb_fixtures uses bare import |
| Training + config CLI suite | Initial 22 tests: 20 pass, two errors WinError 1314 creating symlinks; these are environment limitations, not waived coverage |
| Training/config CLI/atomic/model/P01 identity excluding the two symlink methods | Current check running; no symlink implementation changed |
| Existing `test_checks` and `test_artifacts` | Current check running |
| Strict OpenSpec validate | PASS, no issues; rerun for final basis |
| D old batch read-only recovery plan | 30 fresh slots, zero reusable successes/checkpoints; original D source/evidence untouched |

## Verification Reminders

- Current reruns must finish before claiming tasks complete. Initial process matrix predates final code changes.
- Independently test malformed checkpoints, restored exact ties, copied parent recovery, epoch-200 finalization, ancestry overlap and public CLI forwarding; no formal datasets needed.
- Existing successful pre-change evidence without recovery metadata must remain readable; new recovery evidence must not be silently dropped or used as independent repetition.
- Source capture includes all package Python files. Prepared generator scope remains shuffle.py/graph.py/protocol.py, which are unchanged.
- Controller live-worker inspection on Windows uses CIM; this sandbox denies CIM. Actual D preflight needs authorized escalation; never skip the ownership check. Existing symlink tests require Windows privileges; do not call them passed.
- Controller plan must run against D authoritative batch, not C report which lacks runtime manifest. Initial C plan command failed FileNotFoundError for this reason; D read-only plan passed.
- First aggregate baseline command had an import error due to missing nb_fixtures path; corrected invocation passed all 100 tests.
- D rollout, research-side acceptance, archive and push are workflow follow-up; none is performed yet.


## Final Apply and Repair Evidence (supersedes pending rows above)

- Final pre-repair process matrix: 11 tests PASS in 570.857s; evidence at C:/Users/Lenovo/AppData/Local/Temp/gvs-cp-process-9fc4frsu/evidence.json. Includes public CLI finalization, historical metadata-free recompute, mismatch-before-update and exact parameter/Adam/history/RNG/prediction agreement across self/graph/shuffled at cuts37/113/200.
- Independent initial FAIL identified V-001/V-002/V-003. Fix workflow reproduced V-001/V-002 with failing new regressions, repaired all three and updated only repair-owned report fields; verdict remains independently owned. Source runtime fixed for reverification.
- Repair regression command: -m unittest benchmark.graph_value_skeleton.tests.test_checkpoint_repairs.StrictScalarTest benchmark.graph_value_skeleton.tests.test_checkpoint_repairs.ParentLineageTest benchmark.graph_value_skeleton.tests.test_checkpoint_repairs.CompletedQualificationTest benchmark.graph_value_skeleton.tests.test_batch_recovery -q: 10 tests PASS in6.093s. Scope: exact bool/float rejection, copied payload ancestry binding,11 completed-slot identity mismatches and compatible metadata, controller ownership/recovery/watchdogs/gates.
- CodecTest:4 tests PASS in22.939s after repairs, including epoch37 exact tie restore and163 remaining updates.
- Current saved-only post-repair check of process-matrix fixtures:9 recomputes PASS and3 shared-ancestry comparisons reject; reports under gvs-cp-process-9fc4frsu/post-repair. No forward call/source demand read.
- Existing training/config/atomic/model/P01 identity aggregate:44 tests PASS in128.613s, excluding two original Windows symlink-creation methods which fail WinError1314 even under authorized unsandboxed execution.
- Existing checks/artifacts aggregate:35 methods,33 PASS; two original methods stop at symlink creation WinError1314,717.419s. These are not implementation assertion failures. Original symbol-link tests are explicitly not claimed passed.
- Junction fallback: -B scratch/checkpoint-junction-checks.py: all4 affected path methods PASS in13.615s using Windows directory junctions instead of symbolic links; resolves protected targets, rejects aliases/copies, enforces report destination. Existing completed small fixtures reused; all created junctions removed with os.rmdir, target directories untouched.
- Baseline protocol/metrics/baselines/data/coverage/preprocessing:100 tests PASS in4.777s with test directory on sys.path.
- Strict OpenSpec validation after repairs:PASS,0 issues.
- Public CLI missing checkpoint command exits1 with explicit CheckpointError and no training.
- D read-only old-batch plan remains30 fresh slots,0 resume/0 reuse; no old checkpoint can be invented.
- Additional graph mapping/metrics/shuffle/shuffle-v2/prepared/readiness regression:46 tests PASS in295.597s. Expected CLI error-path output was followed by unittest OK. Independent current ProcessRecoveryTest running separately to establish final code basis; verifier owns its final outcome.

### Remaining Verification Reminders

Independent report owns resolution/PASS. Four original symbolic-link creation checks remain unavailable on this Windows account, with equivalent directory-junction assertions passed; this is the explicit environment limit. No runtime path policy changed. Confirm completed-slot source capture against an actual fresh worker (isolated capture excludes controller-only imports). Formal D rollout must use new batch IDs, current archive acceptance and live-worker checks. No experiment completion, archive or push is claimed by these notes.
