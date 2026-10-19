# Implementation Verification

- Change: add-graph-value-skeleton
- Schema: spec-driven
- Verdict: FAIL
- Verified at: 2026-10-18T08:58:47Z
- Implementation roots: /Users/watuji/da_chuang/repos/benchmark
- Verified revision: e83cb540d4be9950d79233b29b393155e5cae505; dirty worktree, including the entirely untracked new package and change directory.

## Summary

Independent verification found seven implementation findings: three high, three medium and one low. The shuffled branch trains on the original graph (V-001), graph/shuffled prediction omits graph messages in three of four test windows (V-002), and saved-only validation accepts damaged required evidence (V-003). Additional defects allow a run to pass comparison against itself (V-004), allow a repository-root override to defeat the development destination boundary (V-005), omit the required final runtime-source consistency check (V-006), and omit the failing context identity from shuffle diagnostics (V-007).

Strict OpenSpec validation succeeds. All 93 new tests pass, as do 287 existing P01 tests (two optional skips) and 32 old graph-preparation tests. These results do not establish the missing behavioral coverage: independent executable probes reproduce V-001 through V-005 and V-007. V-006 follows from tracing the complete source-capture and final-verification paths. No code, tests, planning artifacts, task checkboxes or apply notes were changed.

No formal run, full research comparison, archive, commit, push or research acceptance was performed. Real region/r2 training and real published shuffling remain unmeasured, as allowed by the bounded implementation scope. Fixture readiness does not establish predictive benefit or graph temporal validity.

Next action: `$openspec-e13-fix-change add-graph-value-skeleton`, then independent re-verification. This report is not archive authorization.

## Verification Basis

The initial snapshot was captured before implementation inspection and executable checks. It includes every regular file in the scopes reproduced below, with path names included in the digest, so additions and deletions change the inventory fingerprint. Git revision supplies the committed baseline; the content manifest also covers dirty and untracked implementation/planning files. Existing verification report: absent at entry. The workflow-owned `implementation-notes.md` and `verification.md` are deliberately excluded.

| Path or scope | Revision / content fingerprint / file inventory |
| ------------- | ---------------------------------------------- |
| All covered scopes | 406 path/content entries; aggregate SHA256 `cb32c90c398756a3a1737d4c03aa52ef50054322f5224ea06ebe67a419a6d328` |
| openspec/changes/add-graph-value-skeleton/proposal.md | `010fd1379bf35a7b780fd60e5345777084cc8a37992a6b0f6639b38aea5c8eb7` |
| openspec/changes/add-graph-value-skeleton/design.md | `a388961c0890a34bc969497908904b37d6d15a28cf6c2c4278d7fdd4954613d7` |
| openspec/changes/add-graph-value-skeleton/tasks.md | `40c8a760c7f90e9db7593edf06a338df93be0493520fc2e5314f4357c86e04e6` |
| openspec/changes/add-graph-value-skeleton/specs/graph-value-skeleton/spec.md | `72bb7e382ac6e231bd36b556e9b308073d2ab9aa6f3e0982c1b72e27f83982de` |
| benchmark/graph_value_skeleton/model.py | `9a9019abb3ae9f7b4df6b284631658c74eff69bcc85f45328db329cda8f2aac1` |
| benchmark/graph_value_skeleton/runner.py | `bf8e788cdea121d29f83d287c3427514fff04fb3ec090573dfe81dbdc6bdf4b7` |
| benchmark/graph_value_skeleton/checks.py | `371be1dd378d99bab92f66afc88e6020d1f3b02fe0aa0e2e4fb7f079020d82b2` |
| benchmark/graph_value_skeleton/config.py | `c5f365d7c09247961f3a6267e377774a218a659b0525bb53afbcccab46ba4ac9` |
| README.md | `213a5869c7d7a6141a344eb7bebaf020467e6c8e9f2655e4558323bd69b804b3` |
| research/archives/migrations/20261008-evidence-maintenance.md | `e9a8339dedd05417ac11adec77b7bbb0f50ea6d0424f8f4d68c78b67ce070fe6` (clean tracked supplemental context) |
| research/decisions.md | `da8eef36f6fe5ca4f8dfce0fba378905376c74a2a4ad4302f62e5edf2442889d` (clean tracked supplemental context) |

Both the 406-entry initial manifest and supplemental context hashes were recomputed at the end of checks and were unchanged. The supplemental decisions/policy-origin documents were clean tracked files at the recorded revision. Scope attribution: pre-existing dirty research state/plan and delegation-pointer status were visible in Git status; this workflow did not read the pointer or modify those files. The P02 plan is included as design context, not as an OpenSpec progress mirror.

Reproduce the initial inventory and digest from the implementation root:

```bash
python - <<'PY'
import pathlib,hashlib,json,subprocess
root=pathlib.Path.cwd()
scopes=['benchmark','openspec/changes/add-graph-value-skeleton','openspec/specs','openspec/config.yaml','README.md','.gitignore','AGENTS.md','research/phases/P01','research/phases/P02/plan.md','research/decisions']
manifest={}
for scope in scopes:
 p=root/scope
 for f in sorted(p.rglob('*') if p.is_dir() else [p]):
  if not f.is_file() or '__pycache__' in f.parts or f.suffix=='.pyc' or f.name in ('verification.md','implementation-notes.md'):continue
  manifest[str(f.relative_to(root))]=hashlib.sha256(f.read_bytes()).hexdigest()
payload=json.dumps(manifest,sort_keys=True,separators=(',',':'))
print(json.dumps({'revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'scopes':scopes,'manifest':manifest,'manifest_sha256':hashlib.sha256(payload.encode()).hexdigest()},sort_keys=True))
PY
```

Supplemental hashes: `sha256sum research/decisions.md research/archives/migrations/20261008-evidence-maintenance.md` (or `shasum -a 256` on macOS).

Additional execution inputs independently checked:

| Input | SHA256 / identity |
| ----- | ----------------- |
| r0 demand | `fc8ebd497f3100f76bc92078529535055a34c281857d61a8d7bd8034898c6946` |
| r0 graph | `c49bc2ecfddd24ddc7a6c6654fdc7bf2e908820139a987f99a115c11b583aa5b` |
| region demand | `27a946c787efcd5f1d2b25ca35bebd1392320d9b10920e771405a664db5e4a3f` |
| region graph | `c0bed3290be3691fbb07c4834c96e8d567e1f54cdfb2120d8a0846a86b64d87c` |
| r2 demand | `4ada154773b8678ae7d25b42e36a8309a51490bbe9fe059f015bb61724ed4c3c` |
| r2 graph | `4cc1f399dd9061920179ade34d018fcbd58c3e00bb40f303b91e9aba99f9e12c` |
| scratch P01 capture generator | `6907ca79d77c87580a88a3da2d45dfda5a16ef4f0ec4db855115eb89ed2f96a8` |
| scratch P01 baseline arrays.npz | `be7c267bef51bee705489006771b5370bc64a4e855b14814099d254bf9c4c615` |
| scratch P01 baseline capture.json | `61e9d5ac6ee33dfbcc990d577283ac2dba2a980415e0a36f8d129df5ced64eb8` |
| scratch P01 baseline oracle.json | `562c2ac48b9d9e7eda27041379133377e9de815e7944777e29ff39acbc1a94df` |

Scratch evidence is disposable. Its claimed pre-change creation time cannot be established independently from Git; current P01 source is unchanged from the recorded revision, and the numeric identity was independently regenerated and compared, rather than accepting that chronology as proof.

## Apply Handoff Review

Read `implementation-notes.md` in full. It correctly names this change, implementation root, schema and dirty revision. The implementation map is current as a location guide; its passing test claims were rerun. Its broad completion claims are insufficient because the current tests miss V-001 through V-007.

Each numbered reminder has the following disposition:

| Reminder | Disposition |
| -------- | ----------- |
| 1. Region/r2 real training not executed | Confirmed limitation. Independently reran actual demand/graph/coverage/mask/reference loading for all three datasets; fixture suite runs full 200-epoch paths. No full region/r2 training was added. |
| 2. Real published shuffle not executed | Confirmed limitation. Fixture shuffle invariants/reproducibility pass; correct training use is contradicted by V-001. No real shuffle cost or accuracy inferred. |
| 3. Formal purpose never executed | Honored. Formal destination resolution only is covered by tests; no formal worker was started. |
| 4. Check reports restricted to scratch/temp | Ordinary-root checks pass, but the claimed boundary is incomplete: V-005 reproduces an override bypass. |
| 5. Disposable pre-change evidence | Confirmed current availability and exact regeneration of 23 arrays per schema plus keys/windows/scores/references/metrics. Independent loop oracle maximum normalized difference: 2.1488072019659114e-16. |
| 6. Installed graph extensions unused | Confirmed with CPU forward/backward import-blocking tests and saved worker environment. Presence is not treated as a dependency. |
| 7. Physical Parquet index column | Confirmed by actual PyArrow schema and pandas semantic-column checks for all three graph files. |
| 8. Published r0 self worse than LastValue | The existing saved metrics show the stated observation; no benefit or tuning conclusion made. This observation is not a readiness criterion. |
| 9. Published r0 selected epoch 200 | Existing saved history/selection support the claim; independently rerun fixture selection tests pass. No early stopping added or assumed. |
| 10. Dirty source identity | Confirmed. HEAD alone does not identify the new package; this report fingerprints actual contents. Source capture saves dirty/untracked runtime files, but its final source-change guard misses runtime files (V-006). |
| 11. Fixture temporary roots | Confirmed. Suite workers and independent probe artifacts use system temp. Path-bypass probe performed resolution only and created nothing in research. |

A further handoff assertion, “mid-run source content change fails,” is only tested by changing the demand Parquet in `test_artifacts.py:556`; it does not cover changes to captured runtime source files. This gap is V-006.

## Checks

Commands ran from the implementation root. Pinned execution runtime observed in fixture artifacts: Python 3.11.17, torch 2.14.1 CPU (`cuda_version=None`), NumPy 1.26.4, pandas 2.2.3, PyArrow 17.0.0; worker BLAS and torch threads are 1.

| Command or inspection | Result | Notes |
| --------------------- | ------ | ----- |
| `openspec status --change add-graph-value-skeleton --json` | Complete planning | repo-local, spec-driven, 33/33 task claims; not behavior evidence |
| `openspec instructions apply --change add-graph-value-skeleton --json` | all_done | All returned context files and handoff read |
| `openspec validate add-graph-value-skeleton --type change --strict --json --no-interactive` | PASS | No structural issues |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/graph_value_skeleton/tests -v` | 93 tests OK, 83.440 s | Includes schema/method/three-shuffle-seed matrix, 200 epochs, CLI workers, repetitions and saved checks; does not detect findings below |
| `python -m unittest discover -s benchmark/nograph_baseline/tests -v` | Environment failure | Default Python lacks usable numeric dependencies: `numpy.random` absent; 200 tests ran, 157 errors, two skips. Not attributed to this change. |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/nograph_baseline/tests -v` | 287 tests OK, two skips, 45.299 s | Established runtime regression passes |
| P01 suite with torch/graph-extension imports disabled; Appendix C | 287 tests OK, two skips, 38.944 s | `torch_imported=false`; no graph-free dependency regression. This is an import-blocked pinned environment, not a claim that the broken default environment was repaired. |
| `conda run -n job-sdf-baseline python -m unittest benchmark.graph_method.tests.test_prepare_graph_data -v` | 32 tests OK | Includes unchanged duplicate-row weighted export |
| Actual published integration; Appendix B | PASS | Nodes/edges: r0 2335/60804, region 16345/218840, r2 121420/321374; duplicate count 0, symmetry 1, context isolation true; all published NaiveRef=LastValue |
| P01 baseline regeneration; Appendix D | PASS | All 69 arrays exact, plus JSON identity/metrics exact; independent loop oracle passes |
| Independent window/training/corruption/repetition probes; Appendix A | Confirmed failures | V-001, V-002, V-003, V-004 |
| Root-override path probe; Appendix B | Confirmed failure | V-005; no destination reserved or written |
| Runtime source lifecycle trace | Confirmed missing guard | V-006; capture at runner:109, final manifest at runner:331 checks only demand/protocol/graph |
| Non-swappable context-17 probe; Appendix E | Confirmed diagnostic failure | V-007 |
| README diff and actual CLI parser/help | Scope/docs conform, behavior caveats below | README +121/-0, new §4.6 only; numerical and path promises need implementation repair |
| Final source/planning snapshot comparison and scope audit | Unchanged | No tracked implementation or research modifications by verification; only this report added |

PyArrow printed nonfatal sandbox CPU-cache/sysctl diagnostics; the affected commands completed successfully. No dependency installation or external mutation was needed.

## Requirement Coverage

All 16 normative requirements and all 33 named scenarios in `specs/graph-value-skeleton/spec.md` were considered. “PASS component” means the stated component was verified; it does not override a failed end-to-end requirement.

Implementation/test paths below are relative to `benchmark/graph_value_skeleton/` unless qualified otherwise.

| Requirement / scenario | Evidence | Result |
| ---------------------- | -------- | ------ |
| R01 P01 identity — Shared identity oracle | `data.py` delegates to unchanged P01; `test_p01_identity.py`, `test_graph_mapping.py::test_mapping_matches_prepare_graph_data`; all windows/float32 arrays/hashes; Appendix D | PASS |
| R01 — Published data assertions | `assert_published_demand`, dense offsets, positive/negative mock-sized tables; actual all-three published loading in Appendix B | PASS |
| R01 — Invalid scope or input | `test_invalid_fixture_inputs_rejected`, `test_help_surface`, CLI invalid axes; finite/nonnegative, duplicates, month and unsupported mode/fold checks traced before training | PASS |
| R02 Endpoints — Context-qualified mapping | `graph.load_graph`, `context_layout`; non-dense 2/10 multi-context oracle against old preparation; dense offset all grids; published schema/count/duplicate/self-loop/symmetry assertions | PASS |
| R02 — Unmatched endpoint | `test_invalid_endpoints_and_columns_fail`; error names endpoint before graph construction; context tuple lookup inspected | PASS |
| R03 Independent states — Vectorization equivalence | `model.encode`; `EncoderTest` per-node loop and node perturbation; fresh zero state, GRU(1,32), Linear(32,3), independent model construction | PASS encoder; graph window path fails V-002 |
| R03 — State reset | Existing reset test exercises self only. Appendix A evaluates graph windows alone versus batched and finds differing graph outputs after window 0 | FAIL V-002 |
| R04 Incoming means — Asymmetric direction oracle | Single-window operator oracle `0→1,2→1,1→2` passes in `PropagationTest`; production multi-window path only propagates to first N flattened rows | FAIL end-to-end V-002; operator PASS |
| R04 — Duplicate rows do not weight a neighbor | `graph.load_graph` unique edges with multiplicity distribution; fixture 3+1 duplicates gets equal two-source mean; old weighted export regression passes | PASS component |
| R05 Isolated equality — No incoming edge | `test_isolated_and_empty_graph_exact_equality`; out-only and isolated nodes exact same-parameter outputs, no division by zero | PASS |
| R05 — Empty graph | Same test; identity aggregation returns hidden tensor, exact output equality | PASS |
| R06 Capacity — Parameter isomorphism | `parameter_signature/counts`; independent sizes/seeds, no graph trainables; runtime selection/NPZ measured GRU3360 + head99 = 3459 | PASS |
| R07 Shuffle — Reproducible context-local swaps | `shuffle.py`, `test_shuffle.py`: exact directed degrees, changed per-context sets, fixed 10E/100E budgets, PCG64, audit/overlap, reordered rows/hash subprocesses/model-seed/run-ID independence | PASS construction; training use fails V-001 |
| R07 — No legal changed control | Single-edge, exhausted budget and unchanged final edge-set rejection tests pass; Appendix E shows rejection omits actual context identity required by the scenario | FAIL diagnostics V-007 |
| R08 Three-graph MAE — Complete three-graph control | `command_summarize_shuffled`; MAEs1/2/6→3 test, distinct seeds/member identities retained; saved-only summary on full fixture members | PASS arithmetic; members incorrectly trained, V-001 |
| R08 — Incomplete or mixed control | Missing/duplicate/mixed model seed/config/mask/source/environment member rejection in `test_checks.py`; identity projection excludes only allowed shuffled axes | PASS |
| R09 Fixed training — Complete budget and MSE winner | `training.train`, full-batch/chunk gradient oracle with unequal context sizes; 200 epochs/steps/history; exact Adam settings and raw-count loss; validation-MSE min selection traced | FAIL branch conformance V-001; budget/selection PASS |
| R09 — Test isolation and ties | Training interface excludes test labels; test input inference follows frozen selection; strict-less update and earliest-minimum helper; isolation test perturbs a separate target array rather than feeding it to training, so interface/code trace supplies the substantive isolation evidence | PASS selection component |
| R10 Metrics — Masks and empty group | `build_masks` uses original graph and train27 regardless of method; e2e identical mask hashes; boundary0,1/3,2/3; empty null/zero, balanced group exclusion tests | PASS |
| R10 — Independent metric oracle | `test_metrics.py` float64 loop oracle for overall/windows/horizons/groups/negative ratio/counts/error contributions; RMSE pooled, multiplicities1/2/3/3/2/1; P01 naive selection/tie/gains regression | PASS arithmetic; affected predictions V-002 |
| R11 Recoverable evidence — Complete saved execution | `ArtifactCompletenessTest`: all required files, shapes[1,N,3]/[4,N,3], pickle-free arrays, selected model reload; source-capture Git fixture tests. Graph used in training contradicts recorded graph (V-001); final runtime-source check absent (V-006) | FAIL V-001/V-006 |
| R11 — Collision or interrupted execution | `LifecycleTest`: exclusive collision leaves bytes, failed graph stage retained, interrupt recorded, running classified unfinished | PASS |
| R12 Saved-only — Source and model access disabled | `test_recompute_reads_saved_evidence_only` blocks source/training/forward, whole-tree before/after hashes equal; metrics/gains all recompute at1e-12; exclusive single report | PASS normal evidence |
| R12 — Corrupt saved evidence | Eight existing tamper cases fail, but Appendix A accepts NaN selected parameter, missing actual graph and validation_elements=0 in history; validator/manifest coverage inspected | FAIL V-003 |
| R13 CPU repetition — Independent repeated fixture | E2e two runs per method and comparison tolerances pass; near-zero/numeric mismatch checks inspected; Appendix A can instead pass one run against itself | FAIL independent-execution requirement V-004 |
| R13 — Mismatch cannot pass by identical predictions | `test_compare_rejects_condition_mismatch_with_identical_predictions`; dataset/graph/model/shuffle/protocol/policy/mask/source/environment condition projection inspected; nonfinite prediction/numeric mismatch rejects | PASS conditions for distinct valid runs |
| R14 Axes/purpose — Default development invocation | Config defaults to development scratch; real CLI fixture workers use temp, no formal outputs; ordinary output-root/symlink/run-ID rejection tests | PASS default |
| R14 — Invalid axes or unsafe destination | Method/shuffle/model-seed/purpose validation and ordinary unsafe destinations reject before reserve; actual public root override makes research/scratch acceptable | FAIL V-005 |
| R14 — Interleaved methods in one process | `test_interleaved_methods_do_not_mutate_module_globals`; immutable config and independent computational identity; purpose does not change math | PASS |
| R15 CPU compatibility — CPU-only complete path | Full fixture suite in exact CPU runtime; blocked-extension real forward/backward and no graph extension imports in CLI workers. Full paths execute, but produce incorrect graph training/prediction behavior | PASS execution/dependencies; FAIL behavior V-001/V-002 |
| R15 — Existing no-torch regression | 287-test original suite passes with explicit torch/extension import prohibition, torch absent from sys.modules; old preparation 32 tests; unchanged old source and formats | PASS |
| R16 Costs/acceptance — Measured development cost | Fresh CLI worker artifacts record durations, CPU/thread/environment/N/E/epochs, native and byte RSS; Darwin/Linux conversion unit tests; fixture labels; no unmeasured region/r2 cost claims | PASS |
| R16 — Software readiness handoff | README additive chapter and command surface checked; P01 versions/frozen rules unchanged; no scientific or research acceptance claimed; report FAIL preserves independent handoff | PASS boundary; readiness not achieved |

Design acceptance index: A01–A03 and A05 pass; A04/A06 have production-window failures V-002; A07 has diagnostic V-007; A08 and A11 are undermined by V-001; A09–A10 numeric contracts pass; A12 fails V-001/V-006; A13 fails V-003; A14 fails V-004; A15 fails V-005; A16 runtime/compatibility passes with graph behavior failures already listed; A17 measured costs pass; A18 workflow scope is preserved. Completed tasks are treated as claims, not acceptance evidence.

## Findings

### V-001: Shuffled models train on the original graph

- Category: implementation
- Severity: high
- Requirement: Specs “Shuffled control averages all three graph MAEs per model seed,” “Graph messages are unweighted incoming-neighbor means,” fixed training; design D6/D7; A07/A08/A11/A12.
- Evidence: `runner.py:147` selects `message_edges=shuffled.edges`, but `runner.py:191` constructs training layout from `graph.edges`. Only self chunks are replaced. Appendix A observes the actual chunks passed to the real 200-epoch training call: training edges equal the original eight-edge fixture, not saved shuffled edges; validation uses the shuffled edges.
- Expected: Each shuffle-seed model fits with that same shuffled adjacency throughout training, validation and selected inference; saved graph identity describes the graph actually used.
- Actual: Every shuffled model fits against the original adjacency while validation/checkpoint selection and saved graph identity use a different graph. Its three-member mean is not the specified trained shuffled control.
- Repair guidance: Construct training chunks from the method's actual message edges while continuing to derive evaluation masks from the original graph. Establish actual training-edge identity, not just saved hashes.
- Acceptance checks: On a changed multi-context shuffle, convert every chunk's local edges back to canonical global indices and match the saved shuffled graph for every training window. Verify gradients/updates against the shuffled-adjacency oracle and show the original-adjacency oracle differs; rerun full fixtures.
- Repair status: addressed-awaiting-verification
- Repair notes: `runner.py` now builds the training layout and chunks from the method's actual `message_edges` (original graph for graph, shuffled graph for shuffled, empty for self); `training.chunk_global_edges` converts every chunk's local edges back to canonical global indices, and the run asserts all 19 windows equal the message graph and records `training_edges` in `selection.json` and `provenance.graph_used`. Tests: `test_training.py::ShuffledTrainingTest::test_chunks_use_the_shuffled_adjacency_for_every_window` (per-window conversion plus chunk-gradient oracle equals the shuffled full-batch gradient and differs from the original-adjacency oracle) and `::test_runner_trains_with_the_saved_shuffled_graph`; artifact assertions in `test_artifacts.py`. Probe: 19/19 windows equal saved shuffled edges, saved differs from original, recorded SHA matches. `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/graph_value_skeleton/tests -v` -> 102 tests OK.
- Reverification notes: Reproduced independently; existing 93-test suite passes despite this defect.

### V-002: Graph propagation disappears after the first test window

- Category: implementation
- Severity: high
- Requirement: Specs independent node/window states and unweighted incoming-neighbor means; state-reset scenario; design D2/D4; A04/A06/A09.
- Evidence: `model.py:290` flattens W×N rows, then `model.py:297` applies unchanged node indices0..N-1 only once. Appendix A compares W=4,N=3 graph predictions with independent per-window `model.predict`: max absolute differences by window are [2.9802322387695312e-08, 0.19285818934440613, 0.32453444600105286, 0.4341992139816284]. Windows1/2/3 are exactly equal to same-parameter self predictions.
- Expected: Each window independently applies the complete incoming-neighbor mean to its own N hidden states. Batched graph predictions agree with a per-window graph oracle within1e-6.
- Actual: Only test start24 uses graph propagation; starts25–27 silently use self propagation for both graph and shuffled methods. Evaluating those windows alone changes their graph output.
- Repair guidance: Apply adjacency separately to each window or expand correctly offset edges for all windows, preserving per-window independence and exact zero-message behavior.
- Acceptance checks: Nonconstant asymmetric W=4 oracle for graph and shuffled; compare batched versus per-window predictions across every window, including empty graph/out-only/isolated cases. Recompute full saved test predictions against the selected model and correct operator.
- Repair status: addressed-awaiting-verification
- Repair notes: `model.predict_windows` now reshapes hidden states to `[W, N, 32]` and applies the aggregation to each window independently before the shared head, with explicit input-shape validation. Tests: `test_model.py::EncoderTest::test_batched_graph_predictions_match_per_window_oracle` compares batched graph predictions with a per-window `model.predict` oracle for asymmetric, empty and out-only edges and checks every window; `test_artifacts.py::test_predictions_gold_and_parameters` reloads the selected NPZ and reproduces saved test predictions exactly while asserting every test window differs from self predictions. Probe: max abs differences by window `[2.98e-8, 5.96e-8, 1.19e-7, 2.38e-7]`, all <=1e-6, no window equals self. Full fixture suite 102 tests OK.
- Reverification notes: Existing reset test covers only self; single-window direction tests cannot expose this path.

### V-003: Saved-only validation accepts missing or nonfinite required evidence

- Category: implementation
- Severity: high
- Requirement: Specs “Saved-only checks are read-only and decisive,” especially corrupt saved evidence and history structural consistency; design D9/D10; A12/A13.
- Evidence: Appendix A copies one completed fixture into isolated temp directories and independently (a) writes NaN into selected `head.weight[0,0]`, (b) removes `graph/edges.npy`, or (c) changes a history row's `validation_elements` to0. Each public checker function returns `status: ok` and no errors. `checks.py:618` checks parameter names/shapes/counts but not finite values; `load_run` never loads/validates graph arrays or the saved artifact manifest; `_validate_history` checks train count but not expected validation count.
- Expected: Required numeric parameters remain finite, saved actual graph evidence exists and matches its recorded identity, and all history counts match the declared validation shape/budget. Damaged evidence returns nonzero/failure report without repair/source/model access.
- Actual: A success report can accompany an unrecoverable selected model, absent actual graph evidence, or contradictory history counts.
- Repair guidance: Close the required saved-evidence validation gaps using saved artifacts/identities only. Validate finite parameters, required graph shape/content/hash and exact history count/selection consistency. Do not add training or forward calls to recomputation.
- Acceptance checks: All three Appendix A corruptions must fail with precise discrepancies and a single exclusive failure report; expand equivalent missing/nonfinite/identity/count coverage; retain bytewise input immutability and valid1e-12 recomputation.
- Repair status: addressed-awaiting-verification
- Repair notes: `checks.py` adds `_validate_saved_graph_evidence` (message/source edge arrays must exist, be canonical unique integer `[E,2]`, be in node range, match the provenance message/source hashes, and match the recorded training-edge identity), finite-value checks on every saved parameter tensor, and a `validation_elements == 1*N*3` history check. `test_checks.py::test_recompute_detects_corrupt_evidence` adds nan-parameter, missing-graph, missing-source-edges, message-edge-hash, graph-edge-content and validation-count cases; the three Appendix A corruptions now return `failed`. Valid fixture recomputation remains `ok` at 1e-12 with bytewise-unchanged inputs. Full fixture suite 102 tests OK.
- Reverification notes: All existing tamper tests pass; they omit these cases.

### V-004: Repeat comparison accepts a run compared with itself

- Category: implementation
- Severity: medium
- Requirement: Specs “Same-seed CPU repetition meets the protocol tolerance” requires two distinct independent executions; independent repeated fixture scenario; A14.
- Evidence: `checks.py:959` loads both paths without rejecting identical resolved directories or execution identity. Appendix A calls `command_compare(run_a=run,run_b=run,...)` and obtains `status: ok`, reporting the identical directory for both inputs.
- Expected: Same-run and aliased/copy-equivalent execution identities cannot establish an independent repeat.
- Actual: A single execution can satisfy the software comparison command's apparent repetition check with trivially zero error.
- Repair guidance: Reject the same resolved run and duplicate saved execution identity before treating numerical agreement as repeat evidence.
- Acceptance checks: Same path, symlink alias, and copied directory retaining the same execution identity fail; two genuinely separate same-condition fixture executions pass at1e-6.
- Repair status: addressed-awaiting-verification
- Repair notes: `checks.command_compare` rejects a pair whose resolved directories are identical and a pair whose saved provenance declares the same execution `run_id`, before numerical agreement is considered. Test: `test_checks.py::test_compare_rejects_self_alias_and_copied_execution` (same path, symlink alias and copied run all fail) while `test_same_seed_repeat_compare_passes` still passes for two genuine executions. Probe: same/alias/copied -> `failed`; two independent fixture runs -> `ok` at 1e-6.
- Reverification notes: Fresh-repeat tests alone do not test this rejection condition.

### V-005: Repository-root overrides bypass the development output boundary

- Category: implementation
- Severity: medium
- Requirement: Specs explicit execution axes/purpose protect development outputs, including root overrides; unsafe-destination scenario; design D8/D10; A15/A18.
- Evidence: Appendix B sets `repo_root=protocol.REPO_ROOT/'research'`. `resolve_config` accepts default development output at the real repository's `research/scratch/graph-value-skeleton/read-only-path-probe`. `validate_report_destination` accepts `research/scratch/gvs-read-only-probe.json`. `cli.py` exposes this via global `--repo-root`; both whitelist and forbidden roots are rebased onto the unvalidated override (`config.py:61`, `checks.py:108`). Neither path was created in verification.
- Expected: Development requests/checks cannot write research records or other prohibited locations through any supported root override.
- Actual: Choosing a nested “repository root” makes a prohibited real research directory appear to be allowed scratch, bypassing the intended pre-reservation rejection.
- Repair guidance: Validate the implementation root and enforce destination protections against the authoritative project/protected locations independently of user-controlled rebasing, while preserving legitimate temporary fixture use.
- Acceptance checks: Root overrides pointing into real research/runs/archives/source trees, plus symlink variants, must reject before reservation/report writing. Default and legitimate scratch/temp destinations still pass. Perform negative checks without writing research.
- Repair status: addressed-awaiting-verification
- Repair notes: `config.py` adds `protected_project_roots()` and `validate_implementation_root()`, anchored to the checked-out `protocol.REPO_ROOT` rather than the override, and applies them to `resolve_output_root`; `checks.validate_report_destination` applies the same authoritative protections independently of `repo_root`. Tests: `test_config_cli.py::AxisValidationTest::test_implementation_root_override_cannot_rebase_protected_trees` (research, research/runs, dataset, benchmark, experiments_archive, .git and a symlink alias reject; a legitimate temporary root still resolves) plus the rebased-root destination case in `test_checks.py`. Probe: `resolve_config` -> `ConfigError`, `validate_report_destination` -> `CheckError`, nothing created. Full fixture suite 102 tests OK.
- Reverification notes: Existing tests override output_root under the correct repo_root; they do not exercise this public root-axis bypass.

### V-006: Final source verification omits captured runtime files

- Category: implementation
- Severity: medium
- Requirement: Design D9 explicitly requires source contents unchanged at startup/end; complete recoverable execution evidence; task6.1; A12.
- Evidence: Full lifecycle trace: `runner.py:109` captures runtime file SHA256 entries in `source.json`; `runner.py:331` creates the final verification manifest using only demand, protocol and graph paths; `artifacts.source_manifest` and `verify_source_hashes` do not include or revisit captured runtime-file entries. There is no other runtime rehash before `success`. The scientific protocol digest passed to the final manifest is also computed at that final stage rather than compared with its captured startup identity. Existing “source content change” test at `test_artifacts.py:556` changes demand bytes only.
- Expected: The source identities governing the actual execution are checked against their startup snapshot before success, including runtime files and the captured protocol identity.
- Actual: The implementation captures runtime source once but never checks it again. A runtime-source change is outside the final guard; the stated startup/end contract is missing. No actual concurrent source edit was performed during verification.
- Repair guidance: Recheck the captured execution-source inventory/content and captured protocol identity at completion; retain failure evidence and identify any changed/missing source rather than reporting success under stale provenance.
- Acceptance checks: In an isolated temporary source fixture, change/remove a captured runtime file or change the protocol between capture and finalization; each must fail at source verification. Unchanged sources succeed; unrelated research edits remain outside the captured execution scope.
- Repair status: addressed-awaiting-verification
- Repair notes: `artifacts.verify_captured_source` rehashes every captured runtime file and the captured protocol identity; `runner.py` runs it at `source_verification`, uses the startup-captured protocol digest in the final manifest instead of a fresh computation, and records `captured_source_verification`/`captured_runtime_sources` in `source-sha256.json` before success. Tests: `test_artifacts.py::SourceCaptureScopeTest::test_captured_source_verification_detects_changes`, `::test_runtime_source_change_fails_final_verification` (mid-run runtime-file edit fails the run) and `::test_protocol_identity_change_fails_final_verification`; the existing demand-change failure test still passes. Probe reports changed/missing runtime and protocol sources.
- Reverification notes: Confirmed by complete static call/data-flow trace; no claim that the verifier observed a real concurrent source edit.

### V-007: Shuffle failures omit the failing context identity

- Category: implementation
- Severity: low
- Requirement: Specs shuffled-graph scenario “No legal changed control” requires failure with context and reason; design D6; A07.
- Evidence: Appendix E supplies only context17 and one edge. Error is `context has a single edge (1); no legal endpoint swap exists`, with no17. `shuffle_graph` calls `_swap_edges` without adding its current context to exceptions; the general budget-exhaustion/unchanged messages likewise contain no context identifier.
- Expected: A failure names the actual context and the reason; this matters when processing52 contexts.
- Actual: Execution does fail correctly, but the diagnostic cannot identify which context failed.
- Repair guidance: Preserve the original reason and add the concrete context identity at the per-context shuffle boundary.
- Acceptance checks: Single-edge, no-legal-swap, budget-exhausted and unchanged-final fixtures using nontrivial/multiple context IDs fail with the correct context and reason, without seed retries or returning the original graph.
- Repair status: addressed-awaiting-verification
- Repair notes: `shuffle.py` derives a stable context label and includes it in every per-context failure (single edge, exhausted attempt budget, unchanged final edge set) without changing the original reason, seed or failure behavior. Test: `test_shuffle.py::test_failure_diagnostics_name_the_failing_context` covers a single-edge context 17, a later failing context after a valid earlier context, budget exhaustion and unchanged-final failure. Probe: `context [17] has a single edge (1); no legal endpoint swap exists`.
- Reverification notes: Reproduced with context17; failure-state behavior itself is intact.

## Reproduction Appendices

All snippets run in the implementation root as `conda run -n job-sdf-baseline python -c '<snippet>'` with actual newlines/proper shell quoting, or equivalently in that environment's interpreter. They are verification probes, not added repository tests. They write only temporary fixture/output/report artifacts except the path-only probes, which write nothing. No formal invocation is involved.

### Appendix A: Independent behavioral and damaged-evidence probes

Original probe artifacts: `/private/var/folders/4p/qcjpbnz56m15bct40fb6pnn00000gn/T/gvs-independent-verify-_3i9x4_p`. Their persistence is not required; rerun the complete snippet:

```python
import json,tempfile,shutil
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
from benchmark.graph_value_skeleton import model,training,runner,checks,protocol
from benchmark.graph_value_skeleton.tests import fixtures
training.configure_determinism(0)
m=model.build_model(0)
x=torch.arange(4*3*6,dtype=torch.float32).reshape(4,3,6)/10
agg=model.GraphAggregation.from_edges([[0,1],[2,1],[1,2]],3)
actual=model.predict_windows(m,x,agg)
oracle=torch.stack([model.predict(m,w,agg) for w in x])
selfpred=model.predict_windows(m,x)
print('WINDOW_ORACLE',json.dumps({'max_abs_by_window':(actual-oracle).abs().amax(dim=(1,2)).tolist(),'exact_self_by_window':[torch.equal(actual[i],selfpred[i]) for i in range(4)]}))
root=Path(tempfile.mkdtemp(prefix='gvs-independent-verify-'))
fx=fixtures.build_fixture(root/'fixture','r0')
dataset,source=fixtures.load_fixture(fx)
seen={}
original_train=training.train
def observe(model,**kw):
 c=kw['chunks'][0]
 seen['training_edges']=torch.stack([c.aggregation.source,c.aggregation.target],dim=1).numpy().tolist()
 seen['validation_edges']=torch.stack([kw['validation_aggregation'].source,kw['validation_aggregation'].target],dim=1).numpy().tolist()
 return original_train(model,**kw)
config=fixtures.make_config(root,fx,method='shuffled',shuffle_seed=0,run_id='shuffle-probe')
with patch.object(training,'train',side_effect=observe):
 out=runner.execute_run(config)
run=Path(out['run_dir'])
saved=np.load(run/'graph/edges.npy',allow_pickle=False)
print('SHUFFLED_TRAINING',json.dumps({'source_edges':source.edges.tolist(),'training_edges':seen['training_edges'],'saved_message_edges':saved.tolist(),'training_equals_original':seen['training_edges']==source.edges.tolist(),'training_equals_saved_shuffled':seen['training_edges']==saved.tolist(),'validation_equals_saved_shuffled':seen['validation_edges']==saved.tolist()}))
result=checks.command_compare(run_a=run,run_b=run,repo_root=protocol.REPO_ROOT,command=['independent-probe','same-run-compare'],report_path=root/'same-run-report.json')
print('SAME_RUN_COMPARE',json.dumps({'status':result['status'],'run_a':str(run),'run_b':str(run)}))
for case in ['nan-parameter','missing-graph','history-validation-count']:
 d=root/case
 shutil.copytree(run,d)
 if case=='nan-parameter':
  path=d/'models/selected.npz'
  with np.load(path,allow_pickle=False) as f: arrays={k:f[k].copy() for k in f.files}
  arrays['head.weight'][0,0]=np.nan
  np.savez(path,**arrays)
 elif case=='missing-graph':
  (d/'graph/edges.npy').unlink()
 else:
  path=d/'training-history.json'
  obj=json.loads(path.read_text())
  obj['rows'][0]['validation_elements']=0
  path.write_text(json.dumps(obj))
 result=checks.command_recompute(run_dir=d,repo_root=protocol.REPO_ROOT,command=['independent-probe',case],report_path=root/(case+'-report.json'))
 print('CORRUPTION',json.dumps({'case':case,'status':result['status'],'errors':result['envelope']['errors']}))
print('PROBE_ROOT',root)

```

### Appendix B: Published input checks and output-root bypass

```python
import json
from pathlib import Path
from benchmark.graph_value_skeleton import data,graph,protocol,config,checks
out={}
for name in ('r0','region','r2'):
 ds=data.load_dataset(name)
 gr=graph.load_graph(name,ds.key_array)
 cov=data.load_neighbor_coverage(ds,Path(gr.source_path))
 masks=data.build_masks(ds,cov)
 _,scores,ref,_=data.naive_reference_block(ds)
 out[name]={'nodes':ds.node_count,'edges':gr.edge_count,'demand_sha256':ds.demand.source_sha256,'graph_sha256':gr.source_sha256,'node_keys_sha256':gr.node_keys_sha256,'duplicates':gr.duplicate_rows,'symmetry':gr.symmetry_rate,'block_diagonal':gr.block_diagonal,'NaiveRef':ref['NaiveRef'],'mask_hashes':masks.hashes()}
print('PUBLISHED',json.dumps(out,sort_keys=True))
wrong_root=protocol.REPO_ROOT/'research'
resolved=config.resolve_config(data_name='r0',method='self',model_seed=0,shuffle_seed=None,run_id='read-only-path-probe',repo_root=wrong_root)
report=checks.validate_report_destination(wrong_root,wrong_root/'scratch/gvs-read-only-probe.json')
print('ROOT_OVERRIDE',json.dumps({'run_dir':str(resolved.run_dir),'report':str(report),'research_destination_accepted':resolved.run_dir.is_relative_to(protocol.REPO_ROOT/'research'),'created':resolved.run_dir.exists()}))

```

### Appendix C: Existing regression with torch imports prohibited

```python
import importlib.abc,sys,unittest,json
class NoTorch(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'torch','torch_geometric','torch_scatter','torch_sparse','dgl'}:
   raise ImportError('disabled for independent no-torch verification: '+fullname)
sys.meta_path.insert(0,NoTorch())
suite=unittest.defaultTestLoader.discover('benchmark/nograph_baseline/tests')
result=unittest.TextTestRunner(verbosity=0).run(suite)
print(json.dumps({'torch_imported':'torch' in sys.modules,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}))
sys.exit(not result.wasSuccessful())

```

The two optional skips are the suite's existing sklearn-availability checks. Child workers invoked by the existing suite use the pinned interpreter; the parent regression process has the explicit import prohibition and reports `torch_imported=false`.

### Appendix D: Regenerated P01 numerical baseline

Uses the already-existing ignored capture generator as a fixture description, runs its independent array oracle again and compares the live P01 result to the original saved arrays/JSON. The new package's direct P01 identity is separately exercised by its in-repository tests.

```python
import runpy,tempfile,json
from pathlib import Path
import numpy as np
ns=runpy.run_path('scratch/graph-value-skeleton/p01_capture.py',run_name='verification_capture')
baseline=Path('scratch/graph-value-skeleton/p01-baseline')
saved_json=json.loads((baseline/'capture.json').read_text())
root=Path(tempfile.mkdtemp(prefix='gvs-p01-verify-'))
out={}
with np.load(baseline/'arrays.npz',allow_pickle=False) as saved:
 for name in ns['SCHEMAS']:
  captured,extras=ns['capture_schema'](name,root/name)
  checked=[]
  for key,value in extras['arrays'].items():
   np.testing.assert_array_equal(value,saved[key],err_msg=key)
   checked.append(key)
  old=saved_json['datasets'][name]
  assert captured['keys']==old['keys']
  assert captured['node_keys_sha256']==old['node_keys_sha256']
  assert captured['windows']==old['windows']
  assert captured['validation_scores']==old['validation_scores']
  assert captured['references']==old['references']
  assert captured['metrics']==old['metrics']
  result=ns['compare'](extras['oracle'],captured)
  assert result['status']=='ok',result
  out[name]={'exact_numeric_arrays':len(checked),'keys_windows_scores_references_metrics':'exact','independent_oracle':result}
print(json.dumps(out,sort_keys=True))

```

### Appendix E: Missing context diagnostic

```python
import json
import numpy as np
from benchmark.graph_value_skeleton import shuffle
try:
 shuffle.shuffle_graph('r2',np.array([[17,0],[17,1]],dtype=np.int64),np.array([[0,1]],dtype=np.int64),0)
except Exception as e:
 print(json.dumps({'type':type(e).__name__,'message':str(e),'context_17_named':'17' in str(e)}))

```

