# Implementation Verification

- Change: add-resumable-training-checkpoints
- Schema: spec-driven
- Verdict: PASS
- Verified at: 2026-10-20 15:40:39 UTC
- Implementation roots: C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark
- Verified revision: 2ca56dd68fb72ff632f9612dc1dbbc6eee66b723 plus fingerprinted dirty worktree
- Scope: Independent bounded fixture verification. No formal training, D-drive mutation, commit or push.

## Summary

All 14 named normative scenarios have sufficient current evidence, and all three initial findings are independently verified resolved. Current self/graph/shuffled process matrices run all 200 epochs with interruptions after 37/113/200 and public-CLI finalization recovery; current/best parameters, Adam, history, RNG and predictions agree exactly. Saved-only checks, historical compatibility and ancestry rejection pass.

This PASS establishes checkpoint capability on the recorded implementation basis. It does not claim formal r2 completion or research acceptance. Next: `$openspec-e13-archive-change add-resumable-training-checkpoints`, then research-side acceptance and authorized rollout. Relevant edits require reverification.

Environment limits: this Windows account cannot create symbolic links (WinError1314). All four affected existing path assertions independently pass using actual directory junctions in isolated temporary fixtures; original symbolic-link creation is not claimed passed. Actual controller CIM/live-worker inspection requires sufficient OS access at rollout, remains mandatory and fails closed; it was not bypassed here.

## Verification Basis

Final sorted inventory covers all skeleton Python runtime/tests, baseline runtime package, controller, dependency manifests, protocol, documentation, OpenSpec configuration and planning. SHA-256 uses actual bytes. Exclude workflow-owned implementation-notes.md and verification.md. Unrelated research records are outside runtime identity and this basis.

Initial inventory had 43 paths. Repairs changed checkpoints.py, checks.py, test_batch_recovery.py and controller, added test_checkpoint_repairs.py, and completed tasks.md. Affected coverage was independently rerun. Final inventory extends baseline/configuration scope; this extension does not imply those baseline files were newly implemented.

Reproduce with pinned Python: inventory every `benchmark/graph_value_skeleton/**/*.py` excluding caches, `benchmark/nograph_baseline/*.py`, all change files except the two workflow-owned reports, and the explicit remaining paths below; sort repository-relative POSIX names and compare `hashlib.sha256(path.read_bytes()).hexdigest()`. Names detect additions/deletions; archive relocation may change planning paths but must preserve bytes. Final comparison must match this full set.

| Path | SHA-256 |
| --- | --- |
| `.gitattributes` | `ba6a4818318e971708a6ab10b8b70730d49dc68a044d6c92a3178e7d44b378ba` |
| `README.md` | `54a8c6d64b3931510cfca233895f59e25fe66b0b5acd8b346f124724416601ed` |
| `benchmark/graph_value_skeleton/__init__.py` | `d3d0f19ad2195bb8a35542e6b06c596649f60b043ccd47acd44625977db4b996` |
| `benchmark/graph_value_skeleton/__main__.py` | `7653fa96fd36e656ed801f751ad8e2f332d07c33c8d51ac485c5d7cf2498f62f` |
| `benchmark/graph_value_skeleton/_worker.py` | `9248c4a35d9af22d5622a5921de7d39d4510ce77c6e1acfd31168089fc4932b8` |
| `benchmark/graph_value_skeleton/artifacts.py` | `a05b58786d6c4ac5fe22dc618ba7b425aeee5110a454977f4afd12418613bc53` |
| `benchmark/graph_value_skeleton/checkpoints.py` | `1d8fd80660224d38af8084618f2495fa8e66bbf9f9cac3415edea328f10796c0` |
| `benchmark/graph_value_skeleton/checks.py` | `7ef80c6bca83c0b612310748f4d713fc44483a8981bfedf882c573975cc95c47` |
| `benchmark/graph_value_skeleton/cli.py` | `eb6fc8260983af939a10a0a391a8755a005ca4528e81bd129d55bca24e9285e5` |
| `benchmark/graph_value_skeleton/config.py` | `8ff24265bdc6d419260531373084431023ff5025dad6561150e19c38b77c00e1` |
| `benchmark/graph_value_skeleton/data.py` | `f6446ddea52f602f3690ab29a7340f15d2f0b8a7d91b56887da849689793f5b0` |
| `benchmark/graph_value_skeleton/graph.py` | `0e37fcdc503438c74ecad16d7be2832af0b180c30931261ca8dc448715bd4abf` |
| `benchmark/graph_value_skeleton/model.py` | `7167b866dfda91ad36ad66c215f01b83a62edcff51f4e076eb7f5578a8464c2d` |
| `benchmark/graph_value_skeleton/prepared.py` | `277cb86e54c49a7bd55710955690c5401207ef356b8f64b6e86552ce1e8d4372` |
| `benchmark/graph_value_skeleton/protocol.py` | `fa9e113e84593ed55c9e0a19082ba1984c523beae13015a36ae7e89de3b17267` |
| `benchmark/graph_value_skeleton/readiness.py` | `327d1ef9b023bc093630e90d10166ca37b85ddf87313c8ea8516e4a032eb6783` |
| `benchmark/graph_value_skeleton/requirements.txt` | `db1cd89fe2014c2462fa099062726a64e76090c5d29ffc4bf4775e49fab4bb2d` |
| `benchmark/graph_value_skeleton/runner.py` | `21b5b6ab36fbab581f6d999acd4aaf6b1d70400f2a39acd339ddbdf2ed812fb8` |
| `benchmark/graph_value_skeleton/shuffle.py` | `c0f3a2beb1b0a43b3130864cae8027cf5c409cdeeb19ed04f3ed779ddf5c22be` |
| `benchmark/graph_value_skeleton/tests/__init__.py` | `27b1f062f50cb17d8fbb9ee992ffbbc1ba10a5a233389ce6b659feb82e505e53` |
| `benchmark/graph_value_skeleton/tests/checkpoint_worker.py` | `c1b9a1803c51d31bbc97c46073d6a895f73a18344c9645866bdd72229760f10f` |
| `benchmark/graph_value_skeleton/tests/fixtures.py` | `b78236d94e57105fc3f97bae47754c13919749c6bb371348e84fd56697083448` |
| `benchmark/graph_value_skeleton/tests/test_artifacts.py` | `f018ff08ff4c7e8ac2225aa33b507cbe3dc880128cd9136cdfecfa0d84160724` |
| `benchmark/graph_value_skeleton/tests/test_atomic_writes.py` | `77dd8418543a44da377fccef553b2b5bb93bb9f78e72e0f8414a72b9b4ec70b1` |
| `benchmark/graph_value_skeleton/tests/test_batch_recovery.py` | `e54fe359930e8eb9c8c7461fce94d3b5cf9307b482832df8375e9e99bf688344` |
| `benchmark/graph_value_skeleton/tests/test_checkpoint_repairs.py` | `d1f60ee2757e33fb73d763edf82e756f4b3a4924382ca47d38c0323a164c77af` |
| `benchmark/graph_value_skeleton/tests/test_checkpoints.py` | `1d5b819cf5f8835de58b9dba501e9c551b9692c33acfb537800b403ce28b46ef` |
| `benchmark/graph_value_skeleton/tests/test_checks.py` | `34f85f8dc65ef1b37fc159d80b211373be59170fee0ae87901cc8869902876c9` |
| `benchmark/graph_value_skeleton/tests/test_config_cli.py` | `7a3035194e47b284b3c93a1c2ea0a89d8be0d52ae9244e94b9c3242411e8da0c` |
| `benchmark/graph_value_skeleton/tests/test_end_to_end.py` | `ec2f211c6be49635c9bacfa1f75fc9499517d0cc1a3f0b9afdec972c37c089b9` |
| `benchmark/graph_value_skeleton/tests/test_graph_mapping.py` | `87c7a249859f87df5d2542d3764fa5ade1dd7a50c4f736a2f77ed5c3bb3e65db` |
| `benchmark/graph_value_skeleton/tests/test_metrics.py` | `99eb1b19a23dca158d6f25d1a823ae76315b372e7a05df273e6164193ec4b9b3` |
| `benchmark/graph_value_skeleton/tests/test_model.py` | `faffbac843f149eb1dc0f6e9f8f57c36cc17653bdec8cf1b98d2ba03d3a7ce69` |
| `benchmark/graph_value_skeleton/tests/test_p01_identity.py` | `4938f2910005d999e58b4257a2bb71d9139793bf0a61395558bafff8c43b3f7f` |
| `benchmark/graph_value_skeleton/tests/test_prepared.py` | `c3defed3c5c8c7c0a5bd662c4e62c8c6a988db189b5d81e50f034ba4a12aaecb` |
| `benchmark/graph_value_skeleton/tests/test_readiness.py` | `7c2e09d8bbc830b5d35574fa2e2963ede9f95340ef02125612dc08c7937f8f2e` |
| `benchmark/graph_value_skeleton/tests/test_shuffle.py` | `ec5d981d9194f7dbba3d6bd4d891b33d4a011be9bb7721d9bc244f41c7af5ccc` |
| `benchmark/graph_value_skeleton/tests/test_shuffle_v2.py` | `c09c5d6e6d423ed7966783f38f3fdce0831a6d09e65c279ef18d7265aa7b93bc` |
| `benchmark/graph_value_skeleton/tests/test_training.py` | `17f3c7e7f7a515b2b6e2f4220d8297ab9158c4222669b7979579b92614ecc6ff` |
| `benchmark/graph_value_skeleton/training.py` | `62692dabd5cfbb5eb52fded6e2e98c20f156a34666cde38e97e5b2afefacb36b` |
| `benchmark/nograph_baseline/__init__.py` | `92d002701a50eee29dba7be96aaf74f291d3586bedf2399e0529258e8c6af0ee` |
| `benchmark/nograph_baseline/__main__.py` | `72db178365f943df31e992dbc551c3b7acb1f993158a7c90f29f1de2ef8bc230` |
| `benchmark/nograph_baseline/_worker.py` | `0e07b3ce8e55c0e3034604d960d1f3d3e05bf22a5712d95d9c02b4fde273756e` |
| `benchmark/nograph_baseline/artifacts.py` | `102ced0ef2ac276cbccb26876a874dec8ac04d5649184be90e38c88ecf52ca86` |
| `benchmark/nograph_baseline/baselines.py` | `baf74b772c39dda9d018e85452e7828d26a2bde8bc8f37472fa6fca51982f8d9` |
| `benchmark/nograph_baseline/checks.py` | `385d84b7c023aa9c9faf0c3627ad657e09a992a10dab0a0654d00e2a356ebaaa` |
| `benchmark/nograph_baseline/cli.py` | `113f8ac025e551bb51f08d96ed12449094fa56dfdec70fa1afbdbe0216116f97` |
| `benchmark/nograph_baseline/coverage.py` | `ef21625e4de01569b8e28e80da55a8becb911d78e5b54fcf955eb21a5395e467` |
| `benchmark/nograph_baseline/data.py` | `86d088ab3f3b6a14daeb72dd2698e00e3acd65764fc414e6b5208f71af11aba4` |
| `benchmark/nograph_baseline/metrics.py` | `b17ee51ca49fed1647260ca85b0b91c2778578380ec3f345a58ae9897ff7781c` |
| `benchmark/nograph_baseline/protocol.py` | `d653c2fbf0d20bc5c2af990e4fc31615409c7abeebab37692197bda02a6becd4` |
| `benchmark/nograph_baseline/requirements.txt` | `01c3cd1fb29f635ab6737db9c1f5d5216ce044f731a6672aa7e46e40a7e4c643` |
| `benchmark/nograph_baseline/ridge.py` | `de39b94636bded57b43f203caaefb0167ed5615f850628244ee3a55def509704` |
| `benchmark/nograph_baseline/runner.py` | `9b023c593e3f997ca588384d7377c4a6af96480d9bbd6ebbab0510a6cd5f5932` |
| `openspec/changes/add-resumable-training-checkpoints/.openspec.yaml` | `ff4326f8b42dcf8851877f4f3989c7fecb8f97d8154686d7d74b7281b70e6b9b` |
| `openspec/changes/add-resumable-training-checkpoints/design.md` | `9a1ce3abedf914a7f5bb400e9505913bc62be056c0b7837e24c4acb0dc32083d` |
| `openspec/changes/add-resumable-training-checkpoints/proposal.md` | `528e2d161090aeccde61d6a948664fb41416d3f2e7cc2e7574520ffd8e6dbeb8` |
| `openspec/changes/add-resumable-training-checkpoints/specs/graph-value-skeleton/spec.md` | `5a52bae78e8f70ce71b5a6621388151c2a03d944f0020efa406f94b46cca94c9` |
| `openspec/changes/add-resumable-training-checkpoints/tasks.md` | `e153cb7c69ef03087893ff1f80d10c4a6bbb374b71e3487b44b2d105bd45b030` |
| `openspec/config.yaml` | `e9caf830990b4f7277d6f43a2b24d118382ac5e4061a3308f35f2a04e3109c55` |
| `requirements.txt` | `af0bb62eb2b00c698820ff29f4f2b48434121ec8c4b781d4da160607c3daa38b` |
| `research/phases/P01/protocol.md` | `2dcf0af81bb76dd35a1c1add4738e9e8e3c8474f9fc143101e9d59c0d8e8921c` |
| `research/phases/P02/t002_r2_batch.py` | `d517e2a660ec278d0ecd5937f26cd60693a3abdc4c2618fe3e036cb31fd29cda` |

Current process evidence: `C:/Users/Lenovo/AppData/Local/Temp/gvs-cp-process-ksf1pe8b/evidence.json`, SHA-256 `6e7c0a0904f8b45b3cc618010d1ce46d912d26c01f95e9c0b1c8a446aa883d77`. Its directory retains all continuous/interrupted/resumed artifacts and15 saved-only reports:9 successful recomputes,3 valid independent comparisons,3 intentionally failed ancestry comparisons. This is local temporary evidence, not sealed or backed-up research output; the command below recreates it.

## Apply Handoff Review

Read proposal/design/spec/tasks and current implementation-notes.md, including final repair evidence and remaining reminders. Change/root/revision match; final CLI status reports14/14 checked tasks, evaluated as claims rather than evidence.

| Reminder / claim | Disposition |
| --- | --- |
| Earlier process results predate repairs | Superseded by independent final current process matrix,664.204s |
| Malformed state, complete Adam/current/best/RNG, exact ties | Confirmed by independent focused14 tests and final process matrix |
| Copied parent recovery, lineage and source immutability | ParentLineageTest and real three-method ancestry rejection; process test hashes source run before/after continuation |
| Public CLI, epoch200 and mismatch before update | All three finalizations pass; changed seed fails under Adam.step trap before new checkpoint |
| Historical successful evidence without recovery | Three current legacy-copy recomputes pass; separate from stricter completed-slot reuse gate |
| Genuine worker source/runtime compatibility | Actual new public-CLI worker vs prepare-equivalent isolated capture: dataset/masks/graph/source/protocol/runtime/execution all match,25 source paths; formal predicate exercised via in-memory purpose label only |
| Prepared generator semantics unchanged | shuffle.py/graph.py/protocol.py unchanged from initial basis; graph/prepared regressions are supplementary apply evidence |
| Cumulative timings, separate attempt wall, no false completion | Real fixture assertions confirm monotonic accumulated work, unfinished completion=false, zero new training/validation at epoch200 and exact parent cumulative times |
| Windows symbolic links/CIM | Environment limits retained; independent4-method actual junction fallback passes; live-worker rollout inspection not waived |
| Broad baseline and nearby regressions | Apply reports100 baseline,44 training/config/atomic/model/identity,33 checks/artifacts and46 graph/shuffle/prepared/readiness passes. Reviewed supplementary evidence, not relabeled verifier-owned runs |
| Historical D ledger | Apply reports30 fresh slots/zero reuse/resume. Independent bounded ledger verifies missing checkpoint→fresh and old bytes unchanged; no D rollout here |
| Archive, research acceptance, D synchronization, publication | Remain workflow follow-up and are not claimed complete |

## Checks

Use `.venv-pinned/Scripts/python.exe -B`, PYTHONUTF8=1, one-thread numerical environment and torch before Arrow on Windows.

| Command / inspection | Result | Notes |
| --- | --- | --- |
| Local CLI status/instructions apply | Ready; final14/14 checked | Repo-local spec-driven context reviewed |
| `node scratch/t002-tools/openspec-cli/node_modules/@fission-ai/openspec/bin/openspec.js validate add-resumable-training-checkpoints --type change --strict --json --no-interactive`, telemetry disabled | PASS | valid=true,0 issues after repairs |
| `-m unittest benchmark.graph_value_skeleton.tests.test_checkpoint_repairs.StrictScalarTest benchmark.graph_value_skeleton.tests.test_checkpoint_repairs.ParentLineageTest benchmark.graph_value_skeleton.tests.test_checkpoint_repairs.CompletedQualificationTest benchmark.graph_value_skeleton.tests.test_batch_recovery.BatchRecoveryTest benchmark.graph_value_skeleton.tests.test_checkpoints.CodecTest -v` | PASS14 tests,24.750s | Current state/codec/lineage/identity/ownership/recovery/watchdog/ETA gates |
| `-m unittest benchmark.graph_value_skeleton.tests.test_checkpoints.ProcessRecoveryTest -v` | PASS1 integrated test,664.204s | Three full200epoch methods,37/113/200 cuts, public CLI, exact state/prediction agreement |
| Genuine CLI worker vs isolated preflight capture | PASS | Seven identity groups/25 source files match; compatible qualification accepted without disk mutations |
| Real self/graph progress/timing assertion loop | PASS | Monotonic accumulated work, no false success, measured ETA, zero new work at epoch200; parent cumulative timing exact |
| Four existing path methods with junction substitution using scratch/checkpoint-junction-checks.py logic, isolated copied fixtures | PASS4 tests,16.482s | Actual directory junctions, original assertions, all links removed by os.rmdir; no retraining |
| First junction retry reused old fixture tree | Fixture collision corrected | FileExistsError for previous tampered/copy-execution; independent fresh copy rerun passes, no implementation defect |
| Code/design trace | PASS | Non-pickle NPZ, manifest-last/two generations, RNG restored last, next epoch only, strict-less ties, identity,30-fit/51-check success gate |

## Requirement Coverage

All14 named scenarios (2+3+3+2+2+2) and the additional normative prepared/scientific identity clause are covered.

| Requirement / scenario | Implementation and decisive evidence | Result |
| --- | --- | --- |
| Durable checkpoints / Interruption during checkpoint publication | CodecTest injects both atomic write boundaries, previous manifest remains loadable, two-generation retention; checkpoints.publish generation then manifest | PASS |
| Durable checkpoints / Complete training state | Codec/validate_state roundtrip and malformed rejection; real exact current/best tensors, Adam slots/counters, RNG, history; cumulative timings retained | PASS |
| Explicit continuation / Compatible interrupted run | Real fresh37→113→200 subprocesses, copied parent NPZ/manifest, unique lineage, unchanged source byte inventory; restore RNG after allocations | PASS |
| Explicit continuation / Invalid recovery input | Codec/StrictScalar reject corrupt/malformed states; strict full identity dictionary inspected; process changed-seed fails before Adam.step/new checkpoint | PASS |
| Explicit continuation / No historical checkpoint | Bounded controller ledger maps absent checkpoint to fresh ID without old-byte changes; explicit missing resume fails rather than silently restarts; historical D plan supplementary | PASS |
| Scientific continuation / Interrupted and continuous comparison | Three current matrices array-exact parameters/best/Adam/history/RNG/predictions; compare normalized1e-6 and recompute1e-12 pass; exact-tie fixture selects epoch1 across cut37,163 remaining updates | PASS |
| Scientific continuation / Last epoch recovery | Three public-CLI epoch200 finalizations; no epoch201, optimizer/history exact and new measured training/validation zero; loop completed+1 | PASS |
| Scientific continuation / Shared ancestry repetition | Three real sibling comparisons reject; ParentLineageTest rejects invented/missing/reordered copied-parent prefix; ancestry absent from condition identity | PASS |
| Measured progress / Progress before finalization | Real interrupted status running, completion=false, committed epoch/digest/step/observed ETA; manifest remains recovery authority if crash occurs between publish and progress write | PASS |
| Measured progress / Resumed timing | perf_counter work added to restored values, downtime excluded; cumulative monotonic, finalization zero new train/validation, attempt wall/I/O separate; ETA unavailable explicitly before observation | PASS |
| Auditable batch / Restart after reboot | Bounded reuse/resume/fresh ledger immutable old bytes, duplicate OS lock/stale release, fail-closed live worker;11 qualification mismatches reject, genuine identity accepts; duplicate effective ID rejects | PASS |
| Auditable batch / Failed recovery or check | First failed check stops scheduling/completion; watchdog kills owned child and records cleanup; finish requires6 summaries/exactly51ok reports, frozen identity and original30 slots | PASS |
| Rollout readiness / Independent readiness gate | Current independent equivalence/invalid-state/controller verification; planning requires archive/research acceptance/preflight before formal restart; no formal fit used as check | PASS |
| Rollout readiness / Historical evidence compatibility | Three current no-recovery legacy copies recompute; no checkpoint invented; saved ancestry path no model forward; condition identity and prepared generator semantics unchanged | PASS |

## Findings

All initial findings are closed by current independent checks. Original Evidence/Actual are retained as pre-repair history; repair-owned notes below are preserved verbatim.

### V-001: Saved ancestry is not bound to the copied parent checkpoint lineage

- Category: implementation
- Severity: medium
- Requirement: “Continuation preserves scientific execution” / Shared ancestry repetition; explicit continuation self-contained lineage; design requires original ancestry checksums.
- Evidence: checks._recovery_ancestry validates declared recovery against provenance and checks copied raw byte hash/size/epoch, but never decodes that copied payload to compare its lineage. Independent reproduction encoded parent payload lineage=['real-parent'], then declared ancestry=['invented-parent','invented-child']; the helper returned the invented ancestry without error.
- Expected: A resumed run's ancestry prefix must match the exact copied parent payload lineage, with one fresh unique child identity; corrupt or inconsistent lineage must fail before it can establish independent repetition.
- Actual: Mutually agreeing recovery.json/provenance can omit or replace parent ancestry while the parent checksum remains valid.
- Repair guidance: Bind saved recovery lineage to the integrity-checked copied payload; check epoch/schema/recorded parent identity consistency without external parent access or model forward calls. Retain historical no-recovery compatibility.
- Acceptance checks: Real parent/sibling branches still reject overlap; changed/missing/reordered parent lineage with matching declared provenance fails recompute/compare; copied parent bytes remain self-contained/read-only.
- Repair status: verified-resolved
- Repair notes: checks._recovery_ancestry now decodes the copied object-free parent payload and checks exact schema/epoch and ancestry prefix; copied-execution error priority preserved. ParentLineageTest reproductions failed before repair and pass after. Post-repair saved-only checks on all three method process fixtures: 9 recomputes pass and 3 sibling comparisons reject (gvs-cp-process-9fc4frsu/post-repair).
- Reverification notes: Current independent ParentLineageTest passes for valid copied prefix and rejects invented, missing and reordered prefixes. All three current real process branches pass recompute and reject resumed siblings. Original Evidence/Actual above describe the pre-repair defect.

### V-002: Strict state validation accepts booleans in epoch counters and timings

- Category: implementation
- Severity: low
- Requirement: Durable validated epoch checkpoints; design requires exact keys/shapes/dtypes/consistent counters and malformed-state rejection.
- Evidence: On a genuine captured epoch1 state, validate_state accepted history[0].epoch=True and optimizer_step=True, best_epoch=True, and training_seconds=True. Python bool/int equality and isinstance(...,(int,float)) permit them.
- Expected: Epoch/optimizer/best selection counters are exact integers and timing values are real numeric values excluding booleans; malformed schema fails before restoration/update.
- Actual: Invalid JSON/numeric types are accepted as valid checkpoint state.
- Repair guidance: Require exact scalar types for state/history counters and timing domains, including best_epoch/best_mse and related manifest counters where applicable; preserve genuine encoded state.
- Acceptance checks: Add bool/float counter and bool timing/selection-state mutations; all reject as CheckpointError before model/optimizer/RNG mutation, valid roundtrip still passes.
- Repair status: verified-resolved
- Repair notes: checkpoints.validate_state/load now require exact scalar types for history/best counters, scores, timings and manifest/payload schemas. StrictScalarTest failed before repair and passes after; CodecTest 4 tests pass including roundtrip and cut37 exact tie recovery.
- Reverification notes: Current independent StrictScalarTest rejects malformed bool/float counters, bool timings/selection. Four CodecTest methods and genuine multi-process state restore pass. Original Evidence/Actual above describe the pre-repair defect.

### V-003: Completed-slot reuse lacks requested scientific and current identity validation

- Category: implementation
- Severity: high
- Requirement: Auditable r2 batch recovery requires each original matrix slot mapped to eligible validated attempts; design requires completed-fit validation and frozen execution/input identities before reuse.
- Evidence: Controller.run reuse branch calls only recompute before accepting effective_run_id. recovery_plan determines reuse solely from status=success and old manifest slot labels; neither branch checks actual saved dataset/method/seeds/purpose, computation, source/runtime/input/message-graph/mask identity against the requested new slot/preflight. A copied real r0/self successful fixture with its saved training.py source hash replaced by0 still returns command_recompute status=ok (historical numeric recomputation need not compare current code). A bounded orchestration reproduction assigned all30 requested slots one wrong effective run and reached finish with mocked generic check calls; no slot-specific qualification occurs. Real repeat checks would catch identical aliases, but do not establish compatibility with the requested r2 slot/current execution basis.
- Expected: A completed run is reusable only after saved numeric validation plus exact match to requested slot and frozen new-batch scientific/source/runtime/input/graph/mask identities; incompatible success must pause, never silently count as the requested fit.
- Actual: Internally consistent older/different-axis successes can be selected without a current-batch compatibility check. Existing repeat comparison only compares its pair, not the expected slot.
- Repair guidance: Add an explicit completed-run qualification gate using saved evidence and frozen requested identity, without mutating the old evidence or weakening historical recompute support. Prevent duplicate effective-run mapping where independent slots are required; preserve non-resumable/fresh mapping semantics.
- Acceptance checks: Simulated/real saved fixture successes with wrong dataset, method/model/shuffle seed, purpose, data/graph/mask/source/runtime identity must fail before slot completion/scheduling. Compatible completed pairs remain reusable; no old evidence bytes change; original30-fit/51-check success gate remains.
- Repair status: verified-resolved
- Repair notes: Controller qualifies completed reuse against the requested slot/purpose/computation and frozen source/runtime/data/source graph/message graph/masks/protocol/execution identities before recompute; duplicate effective mappings reject. Preflight captures isolated worker source scope. CompletedQualificationTest covers compatible metadata and 11 mismatches; controller 7 regressions pass. Full focused command (3 repair classes plus test_batch_recovery): 10 tests PASS in 6.093s.
- Reverification notes: Current CompletedQualificationTest accepts compatible identity and rejects 11 wrong-axis/purpose/source/runtime/input/graph/mask/message mutations. Controller invokes qualification before recompute and rejects duplicate effective IDs. Independent genuine public-CLI worker matches all seven prepare-equivalent identity groups and 25 source paths. qualify_completed accepts after only an in-memory purpose-label adaptation to formal; saved evidence unchanged, no formal worker launched. Original Evidence/Actual above describe the pre-repair defect.
