# Implementation Verification

- Change: add-graph-value-skeleton
- Schema: spec-driven
- Verdict: PASS
- Verified at: 2026-10-19T10:41:02Z
- Implementation roots: /Users/watuji/da_chuang/repos/benchmark
- Verified revision: 785a32db38c61fbeeae12ddbda58a656fffb0515 with eight dirty implementation/test files listed below; report also dirty at entry from repair notes. Current content hashes, not HEAD alone, identify this basis.

## Summary

Independent verification passes. V-003 is now verified-resolved; all eight recorded findings are resolved and no actionable findings remain. The saved-audit checker rejects the original five cases and all seven later counterexamples, while valid self/graph/shuffled evidence, including empty contexts, remains accepted.

The current run is scoped to the two changed files (checks.py and tests/test_checks.py) against the previous 408-entry manifest. Strict OpenSpec validation, all14 checker tests (including 25 audit mutations through the CLI handler) and all7 end-to-end tests pass. Independent probes reject20 ordinary audit mutations and eight empty-context mutations with bytewise-unchanged inputs. Three previously failing cases also exit1 through actual subprocess CLI calls. Compare and shuffled summary independently reject the damaged audit via their shared validation.

All16 normative requirements and33 scenarios have current or fingerprint-retained evidence below. Prior full-suite/P01/preparation/numerical/source-lifecycle evidence is retained for unchanged areas; those complete commands were not rerun in this focused run. The final manifest comparison confirms no relevant input changed during verification.

Residual limits: full region/r2 published-data training and real published shuffling remain unmeasured. Published-graph construction time is unknown. These are disclosed scope limits; this software PASS does not establish predictive benefit or research acceptance. No formal run or published-data training was executed. Only verification.md was edited; all new execution artifacts are synthetic development fixtures in system temp.

Next action: $openspec-e13-archive-change add-graph-value-skeleton. This PASS applies only to the recorded current content/inventory basis; relevant changes require re-verification.

## Verification Basis

A content/inventory snapshot was captured before code inspection and executable checks. The following is its relevant-scope projection. Both path additions/deletions and content edits change the digest. Final comparison found the same 408 entries and hashes. Workflow-owned implementation-notes.md and verification.md are excluded.

Compared with the preceding focused verification at 2026-10-19T09:58:38Z (SHA256 99c85c0b87431027e8186ddd1ef96c67af460402ae6d6130867ad3ea6266ea99), exactly two entries changed: benchmark/graph_value_skeleton/checks.py and tests/test_checks.py. No paths were added/deleted. The current manifest was captured before implementation inspection/checks in /tmp/gvs-verify5-basis.json. Planning, dependencies, shuffle/model/training/artifact code, P01/old graph code and all other entries match that snapshot. Against the preceding complete verification at 2026-10-19T09:38:46Z, only the audit checker, its tests and the already-reverified public shuffle hash helper differ. This bounds the current rerun scope; prior independent evidence for unchanged behavior is retained, with all33 scenarios assessed below.

| Path or scope | Revision / content fingerprint / file inventory |
| ------------- | ---------------------------------------------- |
| Implementation and context scopes below | 408 entries; SHA256 8cd683cbbdb0b10896caf0c4de8c2617ba243708def4996254af882ee72f732f |
| Git baseline | 785a32db38c61fbeeae12ddbda58a656fffb0515 plus the dirty-file fingerprints below; planning artifacts unchanged |
| proposal.md | 010fd1379bf35a7b780fd60e5345777084cc8a37992a6b0f6639b38aea5c8eb7 |
| design.md | a388961c0890a34bc969497908904b37d6d15a28cf6c2c4278d7fdd4954613d7 |
| tasks.md | 40c8a760c7f90e9db7593edf06a338df93be0493520fc2e5314f4357c86e04e6 |
| specs/graph-value-skeleton/spec.md | 72bb7e382ac6e231bd36b556e9b308073d2ab9aa6f3e0982c1b72e27f83982de |

Dirty implementation/test files present at entry (all covered by the aggregate inventory):

| Path | Current SHA256 |
| ---- | -------------- |
| benchmark/graph_value_skeleton/checks.py | 7def67d3066698536658ad68d4bf5a7617ef3b68a3e97287ef5b6df46df564ca |
| benchmark/graph_value_skeleton/cli.py | a7d4ecd29711cdff83858f1680d45907df8e7b98abf4d47ac7f7bfcb5bb72db8 |
| benchmark/graph_value_skeleton/config.py | 9f99c046be55c3b04303769d35e570caadfa1f28851e45e73b45572048f1ae91 |
| benchmark/graph_value_skeleton/runner.py | 4e5a03bed2e59cd901af88f65cc4a120cb68ea46bc568bb5d4512cefc152b972 |
| benchmark/graph_value_skeleton/shuffle.py | 3296612c4a2dc4ccc793128be77394892612d9c45ea4919965ce9ee33b8fc754 |
| benchmark/graph_value_skeleton/tests/test_checks.py | ff997abfcb8431b5ae8e97d7e3c82cb76b74241fc1075883491ce3d6b618196c |
| benchmark/graph_value_skeleton/tests/test_config_cli.py | 0dca2a0dcd6ca49e7167e747aa18e3e1898e138da6628fb6627b224dc35bb30a |
| benchmark/graph_value_skeleton/tests/test_shuffle.py | 38077b75c7660b37d764e03bcc91ce8ec8c5730b7054df6e527b99e679e3316a |

Reproduce from the implementation root. This covers code/tests/configuration, planning, P01 scientific/policy sources and project context. Git supplies committed history; the manifest also fingerprints current dirty/untracked nonignored inputs. An ignored source added inside these implementation scopes must be included explicitly before treating a future basis as complete.

```bash
python - <<'PY'
import pathlib,hashlib,json,subprocess
root=pathlib.Path.cwd()
scopes=['benchmark','openspec/changes/add-graph-value-skeleton','openspec/specs','openspec/config.yaml','README.md','.gitignore','AGENTS.md','research/phases/P01','research/phases/P02/plan.md','research/decisions.md','research/archives/migrations/20261008-evidence-maintenance.md']
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],text=True).split('\0')
paths=sorted(set(p for p in paths if p and any(p==s or p.startswith(s+'/') for s in scopes) and pathlib.Path(p).name not in {'verification.md','implementation-notes.md'}))
manifest={p:hashlib.sha256((root/p).read_bytes()).hexdigest() if (root/p).is_file() else 'MISSING' for p in paths}
payload=json.dumps(manifest,sort_keys=True,separators=(',',':'))
print(json.dumps({'revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'entries':len(manifest),'manifest_sha256':hashlib.sha256(payload.encode()).hexdigest(),'manifest':manifest},sort_keys=True))
PY
```

Published input identities below were independently checked on the preceding complete verification at 2026-10-19T09:38:46Z and are retained as historical evidence; published inputs were not reopened in this focused run:

| Dataset | Demand SHA256 | Graph SHA256 |
| ------- | ------------- | ------------ |
| r0 | fc8ebd497f3100f76bc92078529535055a34c281857d61a8d7bd8034898c6946 | c49bc2ecfddd24ddc7a6c6654fdc7bf2e908820139a987f99a115c11b583aa5b |
| region | 27a946c787efcd5f1d2b25ca35bebd1392320d9b10920e771405a664db5e4a3f | c0bed3290be3691fbb07c4834c96e8d567e1f54cdfb2120d8a0846a86b64d87c |
| r2 | 4ada154773b8678ae7d25b42e36a8309a51490bbe9fe059f015bb61724ed4c3c | 4cc1f399dd9061920179ade34d018fcbd58c3e00bb40f303b91e9aba99f9e12c |

During the preceding complete verification, P01 scratch capture was regenerated and compared against its saved arrays/JSON. Its claimed pre-implementation creation chronology remains a historical apply claim, not independently established Git evidence. Equality and the independent array oracle were rerun on the previous basis. Their code/configuration is unchanged and that evidence is retained; no numerical capture was regenerated in this focused run. Scratch outputs are disposable; appendices provide reproductions.

## Apply Handoff Review

implementation-notes.md correctly identifies this change and project. Its revision e83cb54, untracked-package/dirty-state description, 93-test count and original completion claims are historical, not a current checkout description. HEAD includes the package and first repairs; the prior independently executed complete suite had107 tests; the current package has109 tests after the earlier two-test addition, but the full109-test suite was not rerun here. The latest repair contains eight dirty implementation/test files; its exact contents are fingerprinted above. The existing report's repair notes were read as claims and preserved below; the latest V-003 claims were independently rechecked; earlier finding dispositions are retained against unchanged relevant code and refreshed end-to-end coverage.

The reminder dispositions below retain the preceding independent verification where no relevant code/input changed. This run refreshes saved-only/repeat/summary/fixture paths with checker/end-to-end suites and independent audit probes; historical published/numerical/source-lifecycle evidence was not rerun.

| Reminder | Current disposition |
| -------- | ------------------- |
| 1. Region/r2 real training not executed | Confirmed limitation; all-three actual demand/graph/coverage/mask/reference loading passed read-only on the preceding complete basis. Full 200-epoch fixture paths pass for every schema/method. No full region/r2 training inferred. |
| 2. Real published shuffle not executed | Confirmed limitation; fixture construction, actual shuffled training adjacency and gradient oracles pass. Non-dense context RNG now matches D6 (V-008 resolved). No real shuffle cost claim. |
| 3. Formal purpose never executed | Honored; formal paths resolved only in tests. No formal directory was created. |
| 4. Reports restricted to ignored scratch/temp | Confirmed: research/OpenSpec/nested-root bypasses now reject; authoritative scratch/temp destinations remain valid (V-005 resolved). |
| 5. Disposable pre-change evidence | All 69 numeric arrays and keys/windows/scores/references/metrics match exactly; independent oracle maximum normalized metric difference 2.1488072019659114e-16. |
| 6. Installed graph extensions unused | Real CPU forward/backward import-blocking tests pass; actual workers record CPU-only runtime. Installed availability is not treated as a dependency. |
| 7. Physical Parquet index column | Actual published loading confirms the three semantic graph columns; pandas restores the physical index. |
| 8. Published r0 self worse than LastValue | Existing saved outputs still show MAE 1159.0853960817612 vs 189.8750892219843. Historical observation only; no fresh real training or tuning. |
| 9. Published r0 selected epoch 200 | Both existing smoke histories/selections confirm epoch 200. Current fixture budget/selection tests rerun. |
| 10. Dirty source identity | Historical for the original apply runs; the current repair includes dirty implementation files covered by the content manifest. Temporary Git-source tests verify dirty/untracked capture. Final captured-runtime/protocol rehash now executes and rejects changed sources (V-006 resolved). |
| 11. Fixture temporary roots | Honored. Suite and independent probe artifacts use system temp. Unsafe-path probes resolve only and create nothing. |

## Checks

Current commands ran from the implementation root in conda job-sdf-baseline. Logs are disposable: /tmp/gvs-verify5-focused.log, /tmp/gvs-verify5-e2e.log, /tmp/gvs-verify5-audit.log and /tmp/gvs-verify5-extra.log. Probes are reproduced in Appendices H–K. Nonfatal PyArrow sandbox sysctl diagnostics did not prevent any check; no dependency installation or network access was needed.

| Command or inspection | Result | Notes |
| --------------------- | ------ | ----- |
| openspec status / instructions apply --change add-graph-value-skeleton --json | Complete planning; 33/33 task claims | Current context files, handoff and prior report reviewed; checkboxes are claims |
| openspec validate add-graph-value-skeleton --type change --strict --json --no-interactive | PASS | valid=true, issues=[] |
| Content/inventory comparison with previous verification | Exactly2 changed files, no additions/deletions | checks.py and tests/test_checks.py; unchanged coverage retained |
| conda run -n job-sdf-baseline python -m unittest benchmark.graph_value_skeleton.tests.test_checks -v | 14 tests OK, 30.207s | Source/training/forward prohibition; existing array/history tamper cases; 25 audit mutations checked via API and CLI handler; valid empty context; compare/summary/report rules |
| conda run -n job-sdf-baseline python -m unittest benchmark.graph_value_skeleton.tests.test_end_to_end -v | 7 tests OK, 61.983s | All schema/method/shuffle-seed fixture paths, fresh repeat pairs, three-member summaries and public CLI workers |
| Appendices H/I/J: fresh two-context full-budget fixture, saved-copy corruption | All20 invalid copies fail | Five original cases, seven later cases and eight fraction type/range/value cases; valid baseline ok; inputs unchanged |
| Actual subprocess public CLI on changed fraction, coherent false overlap and reduced work budget | Each exits1, status=failed | Exactly one requested report per call; inputs unchanged |
| Appendix K: mixed empty/nonempty fixture for shuffle seeds0/1/2 | All3 valid saved checks pass; all8 corruptions fail | Required null/zero/count/rejection schema; inputs unchanged |
| Appendix K: compare and summarize-shuffled on corrupted audit | Both fail with changed_fraction discrepancy | Uses a genuine distinct repeat and seed0/1/2 members; all input bytes unchanged |
| Affected-code trace | PASS V-003 | Saved-set overlap/fractions, frozen10/100 budgets, rejection sums, required aggregate, node hash and empty schema validated without regenerating graphs/model forward |
| Final basis comparison / git diff --check | Unchanged408-entry basis / PASS | Only workflow-owned verification.md edited by verification |

Retained independent observations for unchanged areas (not commands rerun here):

| Earlier check / basis | Retained result | Why applicable |
| --------------------- | --------------- | -------------- |
| Complete new suite at 2026-10-19T09:38:46Z | 107 tests OK, 104.601s | All changes since then are checker/tests plus the already-reverified shuffle hash wrapper; affected checker and all e2e paths rerun above |
| Checker/shuffle and e2e at 2026-10-19T09:58:38Z | 25 focused tests OK; 7 e2e OK | Shuffle.py is now byte-identical to that verified basis |
| P01 with torch/graph imports prohibited; Appendix C | 287 tests OK, 2 optional skips; torch_imported=false | P01 source/dependencies/configuration unchanged; default Python numeric environment limitation (numpy.random absent) remains historical, with no claim of repair |
| Existing graph preparation suite | 32 tests OK | Old preparation code/tests unchanged; weighted duplicate-row export remains covered |
| Published demand/graph integration; Appendix B | Expected nodes/edges, symmetry1, isolation and LastValue reference for all3 datasets | Loading/assertion/source identity code unchanged; published inputs not reopened here |
| P01 baseline regeneration and independent oracle; Appendix D | 69 arrays exact; keys/windows/scores/references/metrics exact; oracle maximum normalized difference2.1488072019659114e-16 | Numerical/data/protocol modules and planning unchanged |
| Independent training adjacency and multi-window propagation; Appendix A | All19 actual shuffled training graphs match saved edges; all4 windows match graph oracle | Runner/model/training code unchanged; all schema/method e2e checks rerun |
| Source lifecycle and parameter reload tests | Runtime edit/removal/protocol mismatch reject; selected NPZ reload reproduces predictions | Artifact/source/model code and tests unchanged |
| Root-override and RNG probes; Appendices F/G | Protected roots reject; context17 uses [0,17] and matches oracle | Config/CLI/shuffle sources unchanged; prior findings remain resolved |
| README/parser/scope inspection | Additive new chapter, no scientific/research acceptance or historical evidence mutation | README/planning/project scope fingerprints unchanged |

No full109-test new suite, P01/preparation regression, published-input integration or P01 numerical capture was repeated in this focused run. No unknown result is presented as a fresh pass.

## Requirement Coverage

All16 normative requirements and all33 named scenarios are enumerated below. Current checker/end-to-end and independent audit evidence refreshes affected coverage. Other entries retain the preceding independent observations because their implementation/configuration/planning fingerprints are identical; retaining them does not claim that every old command was rerun. Implementation/test paths are relative to benchmark/graph_value_skeleton/ unless qualified otherwise. Additional design constraints are assessed alongside the scenarios rather than silently added as new spec requirements.

| Requirement / scenario | Evidence | Result |
| ---------------------- | -------- | ------ |
| R01 P01 identity — Shared identity oracle | data.py delegates to P01; test_p01_identity, numeric 2/10 multi-context mapping tests; Appendix D exact float32/key/hash/window equality | PASS |
| R01 — Published data assertions | assert_published_demand, dense-grid/offset positive and negative tests; actual all-three published read-only load | PASS |
| R01 — Invalid scope or input | Invalid values/keys/duplicates/months/unsupported mode/fold tests; loader/CLI errors precede training | PASS |
| R02 Endpoints — Context-qualified mapping | graph.load_graph integer tuple lookup; non-dense 2/10 fixture versus prepare_graph_data; published schema/count/symmetry/block tests | PASS |
| R02 — Unmatched endpoint | test_invalid_endpoints_and_columns_fail; identifies absent qualified endpoint before training | PASS |
| R03 Independent states — Vectorization equivalence | EncoderTest loop oracle and node perturbation; independent paired models; GRU(1,32), Linear(32,3) | PASS |
| R03 — State reset | Fresh zeros in encode; batched graph/per-window oracle, split/reset tests; selected four-window prediction reload | PASS; V-002 resolved |
| R04 Incoming means — Asymmetric direction oracle | PropagationTest 0→1,2→1,1→2, plus production multi-window path and Appendix A | PASS |
| R04 — Duplicate rows do not weight a neighbor | graph loader audits multiplicity then unique binary adjacency; two-source equal mean; unchanged old weighted-export regression | PASS |
| R05 Isolated equality — No incoming edge | Exact same-parameter equality for out-only/isolated nodes; zero message selection avoids division by zero | PASS |
| R05 — Empty graph | PropagationTest plus multi-window empty-graph oracle | PASS |
| R06 Capacity — Parameter isomorphism | Parameter signatures, varied N/E, paired independent initial states; measured GRU3360/head99/total3459/graph0 in artifacts and notes | PASS |
| R07 Shuffle — Reproducible context-local swaps | test_shuffle exact directed degrees after accepts/final, changed per-context sets, row order/hash subprocess/model-seed independence; all19 actual training graphs now correct | PASS; D6/V-008 resolved |
| R07 — No legal changed control | Empty/single-edge/no-swap/budget/unchanged-final cases; nontrivial and later-context errors name context and reason | PASS; V-007 resolved |
| R08 Three-graph MAE — Complete three-graph control | MAE1/2/6→3 arithmetic test, retains identities; fixture seed0/1/2 separate full trainings and summaries; actual training edges verified | PASS |
| R08 — Incomplete or mixed control | Missing/duplicate/mixed model seed/config/masks/source/environment rejected; condition projection inspected | PASS |
| R09 Fixed training — Complete budget and MSE winner | Full-batch/chunk-gradient oracle, unequal contexts and actual shuffled chunks; Adam/raw-count settings; 200 epochs/steps/history; validation-MSE winner | PASS; selected history scores now checked against saved validation metrics |
| R09 — Test isolation and ties | Training/selection APIs exclude test targets; strict-less update/earliest minimum; inference follows frozen checkpoint | PASS |
| R10 Metrics — Masks and empty group | Original graph coverage and train27 masks shared across all methods; boundary/empty/balanced metric tests; e2e mask hash equality | PASS |
| R10 — Independent metric oracle | Float64 independent reductions for windows/horizons/context/activity/neighbor/constant, negative ratio/counts/contributions/gains; pooled RMSE and 1/2/3/3/2/1 multiplicity | PASS |
| R11 Recoverable evidence — Complete saved execution | ArtifactCompletenessTest required files/shapes/model reload/history/provenance; scoped source capture and final captured-source verification | PASS; artifact creation retained, saved audit checker reverified |
| R11 — Collision or interrupted execution | LifecycleTest exclusive collision, failed stage/partial evidence, interrupt state, leftover running→unfinished | PASS |
| R12 Saved-only — Source and model access disabled | Source load/training/forward disabled in tests; all metrics/gains recompute at1e-12; independent whole-tree before/after equality | PASS valid-input path |
| R12 — Corrupt saved evidence | Checker tests reject old array/history corruption and all25 audit mutations; Appendices H–K reject all28 independent audit corruptions; three actual CLI failures; compare/summary share validation | PASS; V-003 resolved |
| R13 CPU repetition — Independent repeated fixture | Two fresh repeats per method pass at1e-6; same/alias/copied execution identity now rejects | PASS; V-004 resolved |
| R13 — Mismatch cannot pass by identical predictions | Strict method/seeds/data/graph/protocol/policy/source/environment/mask/config identity; numeric and near-zero mismatch checks | PASS |
| R14 Axes/purpose — Default development invocation | Default labeled scratch, CLI temp workers; formal resolution path-only | PASS |
| R14 — Invalid axes or unsafe destination | Axis errors and research/symlink/OpenSpec-root protection pass; safe scratch/temp defaults preserved | PASS; V-005 resolved |
| R14 — Interleaved methods in one process | Immutable configs, no P01 global mutation; computational identity excludes purpose/run metadata | PASS |
| R15 CPU compatibility — CPU-only complete path | Pinned exact worker runtime, real CPU GRU/aggregation backward with extensions disabled, all methods/checks/CLI matrix | PASS |
| R15 — Existing no-torch regression | Explicit prohibited torch import P01 suite, torch absent from sys.modules; original source/formats unchanged; 32 preparation tests | PASS compatibility; default interpreter environment limitation recorded above |
| R16 Costs/acceptance — Measured development cost | Worker-owned stage timing/RSS/environment/N/E/200 epochs, Darwin/Linux unit checks, synthetic cost labeling | PASS |
| R16 — Software readiness handoff | Additive README/help, exact commands, formal authorization/time limitation, no benefit claim or research-state changes | PASS software workflow boundary; research acceptance remains separate |

Design acceptance mapping: A01–A11 have current or fingerprint-retained behavior evidence, including D6/context-ID derivation and independent shuffled training. A12 artifact/source evidence and A13 saved-only corruption checking pass; V-003 is now resolved using current independent probes. A14–A18 have current repeat/summary evidence plus fingerprint-retained path/compatibility/cost/scope evidence. No scientific acceptance is claimed. The planning checkboxes and historical apply claims do not waive any findings.

## Findings

All findings below are verified-resolved; there are no pending findings. Evidence/Actual/repair guidance preserve the earlier diagnoses as historical context. Current status and repair acceptance are stated in Reverification notes. All repair notes supplied at entry are preserved verbatim. Earlier test counts within those repair notes describe their original runs.
### V-001: Shuffled models train on the original graph

- Category: implementation
- Severity: high
- Requirement: Specs “Shuffled control averages all three graph MAEs per model seed,” “Graph messages are unweighted incoming-neighbor means,” fixed training; design D6/D7; A07/A08/A11/A12.
- Evidence: `runner.py:147` selects `message_edges=shuffled.edges`, but `runner.py:191` constructs training layout from `graph.edges`. Only self chunks are replaced. Appendix A observes the actual chunks passed to the real 200-epoch training call: training edges equal the original eight-edge fixture, not saved shuffled edges; validation uses the shuffled edges.
- Expected: Each shuffle-seed model fits with that same shuffled adjacency throughout training, validation and selected inference; saved graph identity describes the graph actually used.
- Actual: Every shuffled model fits against the original adjacency while validation/checkpoint selection and saved graph identity use a different graph. Its three-member mean is not the specified trained shuffled control.
- Repair guidance: Construct training chunks from the method's actual message edges while continuing to derive evaluation masks from the original graph. Establish actual training-edge identity, not just saved hashes.
- Acceptance checks: On a changed multi-context shuffle, convert every chunk's local edges back to canonical global indices and match the saved shuffled graph for every training window. Verify gradients/updates against the shuffled-adjacency oracle and show the original-adjacency oracle differs; rerun full fixtures.
- Repair status: verified-resolved
- Repair notes: `runner.py` now builds the training layout and chunks from the method's actual `message_edges` (original graph for graph, shuffled graph for shuffled, empty for self); `training.chunk_global_edges` converts every chunk's local edges back to canonical global indices, and the run asserts all 19 windows equal the message graph and records `training_edges` in `selection.json` and `provenance.graph_used`. Tests: `test_training.py::ShuffledTrainingTest::test_chunks_use_the_shuffled_adjacency_for_every_window` (per-window conversion plus chunk-gradient oracle equals the shuffled full-batch gradient and differs from the original-adjacency oracle) and `::test_runner_trains_with_the_saved_shuffled_graph`; artifact assertions in `test_artifacts.py`. Probe: 19/19 windows equal saved shuffled edges, saved differs from original, recorded SHA matches. `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/graph_value_skeleton/tests -v` -> 102 tests OK.
- Reverification notes: 2026-10-19 verified-resolved. Independently observed all19 windows of the real200-epoch region/shuffled training call, mapped local source/target through each chunk's node indices and compared to saved shuffled edges: every window matches, and saved graph differs from original. test_training::ShuffledTrainingTest additionally checks chunk gradients against the shuffled full-batch oracle within1e-6 and confirms the original-graph oracle differs. Selection/provenance training-edge identities match. Full102-test suite passes.

### V-002: Graph propagation disappears after the first test window

- Category: implementation
- Severity: high
- Requirement: Specs independent node/window states and unweighted incoming-neighbor means; state-reset scenario; design D2/D4; A04/A06/A09.
- Evidence: `model.py:290` flattens W×N rows, then `model.py:297` applies unchanged node indices0..N-1 only once. Appendix A compares W=4,N=3 graph predictions with independent per-window `model.predict`: max absolute differences by window are [2.9802322387695312e-08, 0.19285818934440613, 0.32453444600105286, 0.4341992139816284]. Windows1/2/3 are exactly equal to same-parameter self predictions.
- Expected: Each window independently applies the complete incoming-neighbor mean to its own N hidden states. Batched graph predictions agree with a per-window graph oracle within1e-6.
- Actual: Only test start24 uses graph propagation; starts25–27 silently use self propagation for both graph and shuffled methods. Evaluating those windows alone changes their graph output.
- Repair guidance: Apply adjacency separately to each window or expand correctly offset edges for all windows, preserving per-window independence and exact zero-message behavior.
- Acceptance checks: Nonconstant asymmetric W=4 oracle for graph and shuffled; compare batched versus per-window predictions across every window, including empty graph/out-only/isolated cases. Recompute full saved test predictions against the selected model and correct operator.
- Repair status: verified-resolved
- Repair notes: `model.predict_windows` now reshapes hidden states to `[W, N, 32]` and applies the aggregation to each window independently before the shared head, with explicit input-shape validation. Tests: `test_model.py::EncoderTest::test_batched_graph_predictions_match_per_window_oracle` compares batched graph predictions with a per-window `model.predict` oracle for asymmetric, empty and out-only edges and checks every window; `test_artifacts.py::test_predictions_gold_and_parameters` reloads the selected NPZ and reproduces saved test predictions exactly while asserting every test window differs from self predictions. Probe: max abs differences by window `[2.98e-8, 5.96e-8, 1.19e-7, 2.38e-7]`, all <=1e-6, no window equals self. Full fixture suite 102 tests OK.
- Reverification notes: 2026-10-19 verified-resolved. Independent asymmetric four-window batched-vs-per-window max absolute differences are [2.9802322387695312e-08,5.960464477539063e-08,1.1920928955078125e-07,2.384185791015625e-07], all within normalized1e-6; all four windows differ from self. Reran batched graph/empty/out-only oracle and selected-NPZ saved test prediction reload tests. Production predict_windows applies adjacency separately to every window.

### V-003: Saved-only validation still accepts incomplete or inconsistent graph/shuffle audits

- Category: implementation
- Severity: medium
- Requirement: Specs “Saved-only checks are read-only and decisive”, especially “Missing, contradictory, nonfinite or damaged evidence SHALL fail”; “Shuffled graphs preserve directed degrees and change edges reproducibly” requires per-context changed counts/fractions and overlap; design D6 fixed10*E/100*E budgets, rejection reasons and overlap auditing; A07/A12/A13.
- Evidence: Appendix H's five old cases now fail. Appendix I creates a fresh completed region/shuffled fixture and alters only graph-audit.json in seven separate saved copies: negative changed_fraction, missing changed_fraction, false overlap counts/fractions, missing rejections, more rejections than attempts, accept_target_factor=1 with matching context targets/accepted totals, and missing top-level changed_edges. Every copy returns status=ok, errors=[], with bytewise-unchanged input files. Public recompute on changed_fraction=-1 exits0. Independent set arithmetic on saved arrays shows E=6, removed/added4, intersection2 and symmetric difference8; the checker accepts removed/added1, intersection5 and difference2 with matching false fractions. checks.py:1000 validates factors only as nonnegative counts; checks.py:1140–1183 checks internal arithmetic/budgets against these untrusted factors without comparing overlap to saved edge sets or factors to frozen constants; checks.py:1199 makes rejections optional and does not reconcile their sum; changed/intersection/symmetric-difference fractions and the aggregate changed count are never validated.
- Expected: Complete required audit records must agree with saved canonical nodes and source/message edge sets, and with the frozen algorithm/work budget. Derived changed/added/intersection/symmetric-difference counts and fractions must match saved set arithmetic; rejection counts must be present, nonnegative and sum with accepted swaps to attempts. Required aggregates must agree with per-context values. Empty-context records must obey their empty schema. All checks remain saved-only and read-only.
- Actual: Context inventory, local hashes, exact count types and basic per-context/totals relations are repaired, but contradictory or missing required audit values can still produce a successful report. Current focused/e2e tests pass because they do not exercise these remaining cases.
- Repair guidance: Finish the existing shared audit validator using saved-edge set arithmetic for overlap/changes and their fractions, require and reconcile rejection accounting and aggregate changes, and compare declared work factors/targets with the frozen constants. Apply the corresponding required-field/zero/null rules to empty contexts. Do not regenerate graphs, retrain, read source data or use model forward during checks.
- Acceptance checks: Keep every Appendix H case failing; make every Appendix I mutation fail with a nonzero public CLI exit and one exclusive failure report. Add coverage for missing/invalid derived fractions and aggregates, mutually consistent but false overlap counts, impossible/missing rejection accounting and coherent non-frozen budgets. Valid self/graph/shuffled runs, including mixed empty/nonempty contexts, must keep passing; compare/summary must use the same validation; input bytes remain unchanged. Rerun checker/shuffle and end-to-end suites; no need to repeat unaffected P01/preparation training checks if their fingerprints still match.
- Repair status: verified-resolved
- Repair notes: `checks.py::_validate_saved_audit_evidence` now validates the shuffle audit against saved-edge set arithmetic and the frozen algorithm: derived `changed_edges`/`added_edges`/`intersection_edges`/`symmetric_difference_edges` must equal the removed/added/intersection/symmetric-difference sets reconstructed from `graph/source-edges.npy` and `graph/edges.npy`; `changed_fraction`, `intersection_fraction` and `symmetric_difference_fraction` must be present, finite, within [0,1] and match saved-set arithmetic within 1e-12; `accept_target_factor`/`attempt_limit_factor` must equal the frozen 10/100 constants and targets/limits must match them; rejections are mandatory, exact nonnegative integer counts whose sum plus accepted swaps equals attempts; the top-level `changed_edges` aggregate must equal the per-context sum; empty contexts require null `changed_fraction`, zero derived counts and an empty rejection record; the shuffle node-key hash must match provenance. Tests: `test_checks.py::test_recompute_detects_damaged_shuffle_audit` now covers 25 mutations including all Appendix H/I cases (negative/missing changed fraction, coherent false overlap, missing/inconsistent rejections, lowered work budget, missing top-level changed aggregate); `test_recompute_cli_exits_nonzero_for_damaged_shuffle_audit` runs every mutation through the public CLI and requires nonzero; `test_valid_shuffled_run_with_empty_context_recomputes` keeps valid mixed empty/nonempty contexts passing. Probe: all twelve Appendix H/I mutations return `failed` with bytewise-unchanged inputs; valid recompute remains `ok`. Full suite 109 tests OK; P01 287 OK (2 skips); graph preparation 32 OK.
- Reverification notes: 2026-10-19T10:41:02Z: verified-resolved. The five Appendix H and seven Appendix I counterexamples now fail. Independent probes also reject eight invalid fraction values/types (NaN/Inf/bool/null/string/out-of-range/wrong finite value), while valid baseline succeeds. Actual subprocess CLI changed-fraction/coherent-overlap/reduced-budget cases each exit1 with one failure report and unchanged inputs. A separate mixed empty/nonempty fixture passes for shuffle seeds0/1/2 and rejects eight corrupted empty-context records. Genuine repeat comparison and three-member summary both reject a negative audit fraction. All14 checker tests (25 mutation cases via API and CLI handler) and all7 e2e tests pass. Code inspection confirms saved-set arithmetic, frozen work factors, required fractions/aggregate and rejection accounting; no source-data read, graph regeneration, training or model forward occurs in these checks. Probe roots: /var/folders/4p/qcjpbnz56m15bct40fb6pnn00000gn/T/gvs-audit-independent-y_pn3rd6 and /var/folders/4p/qcjpbnz56m15bct40fb6pnn00000gn/T/gvs-audit-extra-kn3p5t_8.

### V-004: Repeat comparison accepts a run compared with itself

- Category: implementation
- Severity: medium
- Requirement: Specs “Same-seed CPU repetition meets the protocol tolerance” requires two distinct independent executions; independent repeated fixture scenario; A14.
- Evidence: `checks.py:959` loads both paths without rejecting identical resolved directories or execution identity. Appendix A calls `command_compare(run_a=run,run_b=run,...)` and obtains `status: ok`, reporting the identical directory for both inputs.
- Expected: Same-run and aliased/copy-equivalent execution identities cannot establish an independent repeat.
- Actual: A single execution can satisfy the software comparison command's apparent repetition check with trivially zero error.
- Repair guidance: Reject the same resolved run and duplicate saved execution identity before treating numerical agreement as repeat evidence.
- Acceptance checks: Same path, symlink alias, and copied directory retaining the same execution identity fail; two genuinely separate same-condition fixture executions pass at1e-6.
- Repair status: verified-resolved
- Repair notes: `checks.command_compare` rejects a pair whose resolved directories are identical and a pair whose saved provenance declares the same execution `run_id`, before numerical agreement is considered. Test: `test_checks.py::test_compare_rejects_self_alias_and_copied_execution` (same path, symlink alias and copied run all fail) while `test_same_seed_repeat_compare_passes` still passes for two genuine executions. Probe: same/alias/copied -> `failed`; two independent fixture runs -> `ok` at 1e-6.
- Reverification notes: 2026-10-19 verified-resolved. Independent same-directory, symlink alias and copied directory retaining the same saved execution identity all return failed. Reran fresh same-seed comparisons for each method successfully. Inspected rejection before numerical comparison.

### V-005: Repository-root overrides bypass the ignored development output boundary

- Category: implementation
- Severity: medium
- Requirement: Specs explicit execution axes/purpose protect development outputs, including root overrides; unsafe-destination scenario; design D8/D10; A15/A18.
- Evidence: Appendix G sets repo_root to the existing implementation-root/openspec/changes/add-graph-value-skeleton directory. resolve_config accepts a development run at that directory's scratch/graph-value-skeleton/resolution-only-probe; validate_report_destination accepts scratch/resolution-only-report.json there. git check-ignore --no-index returns1 with no ignored paths for both. Neither path exists and neither was created. config.development_roots and checks.validate_report_destination still derive allowed scratch from the unvalidated root override; validate_implementation_root only rejects a finite list of protected subtrees.
- Expected: Development runs and reports must resolve under the authoritative ignored scratch tree or a validated temporary/ignored root. A supported repository-root override cannot make an arbitrary unignored source/planning directory an allowed destination.
- Actual: The original research-root bypass now rejects, but the same whitelist-rebasing mechanism accepts unignored directories within OpenSpec planning. This violates the ignored/temporary output boundary despite passing the added protected-tree tests.
- Repair guidance: Anchor scratch eligibility to the actual implementation checkout/ignore policy, independently of arbitrary root rebasing; preserve legitimate temporary fixture roots. Reject unsupported nested overrides before reservation or report creation. Do not create outputs in OpenSpec/research to test the rejection.
- Acceptance checks: Appendix G must reject both run and report resolution before writing. Check nested OpenSpec and other existing nonignored directories plus aliases. Existing research/source/symlink rejection tests, authoritative default scratch and legitimate system-temp destinations must remain valid.
- Repair status: verified-resolved
- Repair notes: `config.py` now accepts an implementation-root override only when it resolves to the authoritative checkout or a system temporary directory, and `development_roots` is anchored to the authoritative ignored `scratch` tree plus the system temp root instead of any override-implied scratch. Development defaults for a temporary root stay inside that temp root; run and report destinations must resolve inside the authoritative scratch or temp. `checks.validate_report_destination` uses the authoritative scratch root. Test: `test_config_cli.py::AxisValidationTest::test_implementation_root_override_cannot_rebase_protected_trees` now covers the OpenSpec root and the nested change directory (run and report paths reject, nothing created), authoritative-scratch and temp report acceptance, and the temporary-root default. Probe: Appendix G override returns `ConfigError` for the run and `CheckError` for the report; no `scratch` directory is created. Full suite 107 tests OK.
- Reverification notes: Latest run2026-10-19 verified-resolved. Independent path-only probes reject both run and report roots under research, openspec and the nested change directory; errors occur before any directory/report is created. Authoritative scratch and legitimate system-temp defaults/report destinations still resolve. Focused/full suites rerun symlink/protected-tree/escape/overwrite cases. Inspected anchoring to protocol.REPO_ROOT/scratch independently of overrides.

### V-006: Final source verification omits captured runtime files

- Category: implementation
- Severity: medium
- Requirement: Design D9 explicitly requires source contents unchanged at startup/end; complete recoverable execution evidence; task6.1; A12.
- Evidence: Full lifecycle trace: `runner.py:109` captures runtime file SHA256 entries in `source.json`; `runner.py:331` creates the final verification manifest using only demand, protocol and graph paths; `artifacts.source_manifest` and `verify_source_hashes` do not include or revisit captured runtime-file entries. There is no other runtime rehash before `success`. The scientific protocol digest passed to the final manifest is also computed at that final stage rather than compared with its captured startup identity. Existing “source content change” test at `test_artifacts.py:556` changes demand bytes only.
- Expected: The source identities governing the actual execution are checked against their startup snapshot before success, including runtime files and the captured protocol identity.
- Actual: The implementation captures runtime source once but never checks it again. A runtime-source change is outside the final guard; the stated startup/end contract is missing. No actual concurrent source edit was performed during verification.
- Repair guidance: Recheck the captured execution-source inventory/content and captured protocol identity at completion; retain failure evidence and identify any changed/missing source rather than reporting success under stale provenance.
- Acceptance checks: In an isolated temporary source fixture, change/remove a captured runtime file or change the protocol between capture and finalization; each must fail at source verification. Unchanged sources succeed; unrelated research edits remain outside the captured execution scope.
- Repair status: verified-resolved
- Repair notes: `artifacts.verify_captured_source` rehashes every captured runtime file and the captured protocol identity; `runner.py` runs it at `source_verification`, uses the startup-captured protocol digest in the final manifest instead of a fresh computation, and records `captured_source_verification`/`captured_runtime_sources` in `source-sha256.json` before success. Tests: `test_artifacts.py::SourceCaptureScopeTest::test_captured_source_verification_detects_changes`, `::test_runtime_source_change_fails_final_verification` (mid-run runtime-file edit fails the run) and `::test_protocol_identity_change_fails_final_verification`; the existing demand-change failure test still passes. Probe reports changed/missing runtime and protocol sources.
- Reverification notes: 2026-10-19 verified-resolved. Runner now rechecks startup-captured runtime SHA256 entries and protocol identity before success. Reran tests for unchanged runtime, changed/removed captured runtime, wrong captured protocol identity, actual runtime mutation during the lifecycle and demand mutation. Changed-source runs terminate failed at source_verification. Scoped source-capture tests still exclude unrelated research/tests/caches. The protocol lifecycle test injects a wrong startup identity; it does not modify the real protocol.

### V-007: Shuffle failures omit the failing context identity

- Category: implementation
- Severity: low
- Requirement: Specs shuffled-graph scenario “No legal changed control” requires failure with context and reason; design D6; A07.
- Evidence: Appendix E supplies only context17 and one edge. Error is `context has a single edge (1); no legal endpoint swap exists`, with no17. `shuffle_graph` calls `_swap_edges` without adding its current context to exceptions; the general budget-exhaustion/unchanged messages likewise contain no context identifier.
- Expected: A failure names the actual context and the reason; this matters when processing52 contexts.
- Actual: Execution does fail correctly, but the diagnostic cannot identify which context failed.
- Repair guidance: Preserve the original reason and add the concrete context identity at the per-context shuffle boundary.
- Acceptance checks: Single-edge, no-legal-swap, budget-exhausted and unchanged-final fixtures using nontrivial/multiple context IDs fail with the correct context and reason, without seed retries or returning the original graph.
- Repair status: verified-resolved
- Repair notes: `shuffle.py` derives a stable context label and includes it in every per-context failure (single edge, exhausted attempt budget, unchanged final edge set) without changing the original reason, seed or failure behavior. Test: `test_shuffle.py::test_failure_diagnostics_name_the_failing_context` covers a single-edge context 17, a later failing context after a valid earlier context, budget exhaustion and unchanged-final failure. Probe: `context [17] has a single edge (1); no legal endpoint swap exists`.
- Reverification notes: 2026-10-19 verified-resolved. Independent context17 single-edge reproduction now reports 'context [17] has a single edge (1); no legal endpoint swap exists'. Reran later-context, exhausted-budget and unchanged-final context diagnostics; all preserve context/reason and failure behavior.

### V-008: Shuffle RNG uses context ordinal instead of the designed context ID

- Category: implementation
- Severity: low
- Requirement: design.md D6 requires PCG64 with SeedSequence([shuffle_seed,context_id]); tasks4.1/A07. Specs permit small non-dense context-qualified fixtures.
- Evidence: shuffle.py:247 passes seed_sequence=(int(shuffle_seed),int(ordinal)). Appendix F uses one swappable context with ID17 and shuffle seed0, observes [0,0], and obtains a different final graph from the unchanged swap algorithm run with the designed [0,17] seed sequence. Actual edges: [[0,2],[0,3],[1,0],[2,1],[3,2],[3,5],[4,5],[5,4]]; context-ID oracle: [[0,3],[0,4],[1,2],[2,5],[3,1],[3,2],[4,5],[5,0]].
- Expected: Each context's local RNG uses its actual context ID as specified by D6, independent of that context's ordinal position.
- Actual: Non-dense context IDs use a different random stream. Current published IDs start at0 and are contiguous, so this finding does not imply a difference for those current published grids.
- Repair guidance: Make RNG derivation agree with the frozen D6 context-ID rule while retaining sorted canonical edges, local NumPy RNG, fixed work budgets, invariant checks and explicit failures.
- Acceptance checks: Appendix F must observe [0,17] and match the context-ID oracle. Include multiple/nonconsecutive context IDs and an empty earlier context; verify local stream identity, directed degrees, reproducibility and unchanged published contiguous-ID behavior.
- Repair status: verified-resolved
- Repair notes: `shuffle.context_seed_sequence` now derives `SeedSequence([shuffle_seed, context_id...])` from the actual context ID(s), the audit records each context's `seed_sequence` with the updated derivation string, and `_swap_edges` canonicalizes its incoming local edge list before proposing swaps so the Appendix F oracle (which passes an unsorted edge array) matches the production canonical stream without weakening row-order independence. Contiguous published context IDs keep their previous streams. Tests: `test_shuffle.py::test_rng_uses_context_id_not_ordinal` (observes `[0,17]`, matches the context-ID oracle and differs from the ordinal `[0,1]` stream), `::test_each_nonconsecutive_context_uses_its_own_id` (`[1,3]`, `[1,17]`), `::test_empty_earlier_context_still_uses_its_own_id` (`[0,0]`, `[0,17]` with an empty earlier context) and `::test_swap_helper_canonicalizes_input_order`. Probe: Appendix F observes `[0,17]` and matches the context-ID oracle. Full suite 107 tests OK.
- Reverification notes: Latest run2026-10-19 verified-resolved. Independent Appendix F observes seed_sequence=[0,17] for context17 and resulting edges exactly match the designed context-ID oracle. Reran nonconsecutive contexts3/17, empty earlier context and row-order tests. Local helper canonicalizes input before swaps, preserving production canonical ordering and contiguous published-context streams; degree/budget/reproducibility regressions pass.

## Reproduction Appendices

Run each Python block from the implementation root using the pinned interpreter, for example conda run -n job-sdf-baseline python -c '<block>' with proper shell quoting. These are disposable verification probes, not added repository tests. Only synthetic temporary run copies are corrupted. Path probes resolve destinations without creating them.

### Appendix A: Current behavioral and damaged-evidence probes

Observed root on the preceding full run (Appendix A was not rerun here): /var/folders/4p/qcjpbnz56m15bct40fb6pnn00000gn/T/gvs-independent-reverify-2oh8r8ma. Persistence is not required.

```python
import json,tempfile,shutil,hashlib
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
from benchmark.graph_value_skeleton import model,training,runner,checks,protocol,config,shuffle
from benchmark.graph_value_skeleton.tests import fixtures
training.configure_determinism(0)
m=model.build_model(0)
x=torch.arange(4*3*6,dtype=torch.float32).reshape(4,3,6)/10
agg=model.GraphAggregation.from_edges([[0,1],[2,1],[1,2]],3)
actual=model.predict_windows(m,x,agg)
oracle=torch.stack([model.predict(m,w,agg) for w in x])
print('WINDOW_ORACLE',json.dumps({'max_abs_by_window':(actual-oracle).abs().amax(dim=(1,2)).tolist(),'exact_self_by_window':[torch.equal(actual[i],model.predict_windows(m,x)[i]) for i in range(4)]}))
root=Path(tempfile.mkdtemp(prefix='gvs-independent-reverify-'))
fx=fixtures.build_fixture(root/'fixture','region')
dataset,source=fixtures.load_fixture(fx)
seen={}
original_train=training.train
def observe(m,**kw):
 edges={}
 for c in kw['chunks']:
  nodes=c.node_indices.numpy()
  pair=np.column_stack([nodes[c.aggregation.source.numpy()],nodes[c.aggregation.target.numpy()]])
  edges.setdefault(c.window_index,[]).extend(pair.tolist())
 seen['edges']={w:sorted(rows) for w,rows in edges.items()}
 return original_train(m,**kw)
conf=fixtures.make_config(root,fx,method='shuffled',shuffle_seed=0,run_id='shuffle-probe')
with patch.object(training,'train',side_effect=observe):
 out=runner.execute_run(conf)
run=Path(out['run_dir'])
saved=np.load(run/'graph/edges.npy',allow_pickle=False)
print('SHUFFLED_TRAINING',json.dumps({'windows':len(seen['edges']),'all_match_saved':all(rows==saved.tolist() for rows in seen['edges'].values()),'saved_differs_original':not np.array_equal(saved,source.edges)}))
def tree(p):
 return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
before=tree(run)
result=checks.command_recompute(run_dir=run,repo_root=protocol.REPO_ROOT,command=['independent-reverify','valid'],report_path=root/'valid.json')
assert result['status']=='ok',result
assert tree(run)==before
print('VALID_RECOMPUTE',result['status'],'UNCHANGED',True)
for case in ['nan-parameter','missing-graph','history-validation-count','missing-graph-audit','selected-score-contradiction','fractional-count']:
 d=root/case
 shutil.copytree(run,d)
 if case=='nan-parameter':
  path=d/'models/selected.npz'
  with np.load(path,allow_pickle=False) as f: arrays={k:f[k].copy() for k in f.files}
  arrays['head.weight'][0,0]=np.nan
  np.savez(path,**arrays)
 elif case=='missing-graph': (d/'graph/edges.npy').unlink()
 elif case=='missing-graph-audit': (d/'graph-audit.json').unlink()
 elif case=='fractional-count':
  path=d/'training-history.json';obj=json.loads(path.read_text())
  obj['rows'][0]['validation_elements']+=0.5
  path.write_text(json.dumps(obj))
 elif case=='selected-score-contradiction':
  path=d/'training-history.json';obj=json.loads(path.read_text())
  epoch=obj['selected_epoch']
  obj['rows'][epoch-1]['validation_MSE_original_units_after_update']=-1
  obj['selected_validation_MSE']=-1
  path.write_text(json.dumps(obj))
  path=d/'selection.json';obj=json.loads(path.read_text());obj['training']['selected_validation_MSE']=-1;path.write_text(json.dumps(obj))
 else:
  path=d/'training-history.json';obj=json.loads(path.read_text());obj['rows'][0]['validation_elements']=0;path.write_text(json.dumps(obj))
 result=checks.command_recompute(run_dir=d,repo_root=protocol.REPO_ROOT,command=['independent-reverify',case],report_path=root/(case+'-report.json'))
 print('CORRUPTION',json.dumps({'case':case,'status':result['status'],'errors':result['envelope']['errors']}))
for label,path in [('same',run),('alias',root/'alias'),('copied',root/'copied')]:
 if label=='alias': path.symlink_to(run,target_is_directory=True)
 if label=='copied': shutil.copytree(run,path)
 r=checks.command_compare(run_a=run,run_b=path,repo_root=protocol.REPO_ROOT,command=['independent-reverify',label],report_path=root/(label+'.json'))
 print('SAME_EXECUTION',label,r['status'])
wrong_root=protocol.REPO_ROOT/'research'
for name,fn in [('config',lambda: config.resolve_config(data_name='r0',method='self',model_seed=0,shuffle_seed=None,run_id='path-probe',repo_root=wrong_root)),('report',lambda:checks.validate_report_destination(wrong_root,wrong_root/'scratch/probe.json'))]:
 try: print('ROOT_OVERRIDE',name,'ACCEPTED',str(fn()))
 except Exception as e: print('ROOT_OVERRIDE',name,type(e).__name__,str(e))
try: shuffle.shuffle_graph('r2',np.array([[17,0],[17,1]],dtype=np.int64),np.array([[0,1]],dtype=np.int64),0)
except Exception as e: print('CONTEXT_ERROR',str(e))
print('PROBE_ROOT',root)

```

### Appendix B: Published input integration
Current published integration is read-only; no real-data training.

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

### Appendix E: Context-qualified shuffle diagnostic
```python
import json
import numpy as np
from benchmark.graph_value_skeleton import shuffle
try:
 shuffle.shuffle_graph('r2',np.array([[17,0],[17,1]],dtype=np.int64),np.array([[0,1]],dtype=np.int64),0)
except Exception as e:
 print(json.dumps({'type':type(e).__name__,'message':str(e),'context_17_named':'17' in str(e)}))

```

### Appendix F: Context-ID RNG derivation oracle

```python
import json,numpy as np
from unittest.mock import patch
from benchmark.graph_value_skeleton import shuffle
from benchmark.graph_value_skeleton.tests import fixtures
keys=np.array([[17,s] for s in range(7)],dtype=np.int64)
edges=np.array(fixtures.CONTEXT_EDGES['r0'],dtype=np.int64)
seen=[]
original=shuffle._swap_edges
def observe(local_edges,**kwargs):
 seen.append({'context':list(kwargs['context']),'seed_sequence':list(kwargs['seed_sequence'])})
 return original(local_edges,**kwargs)
with patch.object(shuffle,'_swap_edges',side_effect=observe):
 out=shuffle.shuffle_graph('r2',keys,edges,0)
expected=original([tuple(row) for row in edges.tolist()],seed_sequence=[0,17],accept_factor=10,attempt_factor=100,context=[17])
print(json.dumps({'observed':seen,'required_seed_sequence':[0,17],'actual_edges':out.edges.tolist(),'context_id_oracle_edges':expected['result_edges'].tolist(),'matches_context_id_oracle':np.array_equal(out.edges,expected['result_edges'])}))

```

### Appendix G: Root overrides and safe defaults (resolution only)

```python
import json,tempfile
from pathlib import Path
from benchmark.graph_value_skeleton import protocol,config,checks
for relative in ['research','openspec','openspec/changes/add-graph-value-skeleton']:
 root=protocol.REPO_ROOT/relative
 for kind,call in [('run',lambda:config.resolve_config(data_name='r0',method='self',model_seed=0,shuffle_seed=None,run_id='resolution-only-probe',repo_root=root)),('report',lambda:checks.validate_report_destination(root,root/'scratch/resolution-only-report.json'))]:
  try: print(json.dumps({'root':relative,'kind':kind,'unexpected_accepted':str(call())}))
  except (config.ConfigError,checks.CheckError) as exc: print(json.dumps({'root':relative,'kind':kind,'rejected':type(exc).__name__,'reason':str(exc)}))
temp=Path(tempfile.mkdtemp(prefix='gvs-path-verify-'))
for root in [protocol.REPO_ROOT,temp]:
 resolved=config.resolve_config(data_name='r0',method='self',model_seed=0,shuffle_seed=None,run_id='resolution-only-safe',repo_root=root)
 report=checks.validate_report_destination(root,temp/'safe-report.json')
 print(json.dumps({'allowed_root':str(root),'run':str(resolved.run_dir),'report':str(report),'created':resolved.run_dir.exists()}))

```

### Appendix H: Original graph/shuffle audit corruption — now rejected

A fresh full-budget development fixture is created in system temp; each corruption affects only an isolated saved copy. Current focused re-verification returns failed for every case, with unchanged inputs. The valid baseline succeeds. Current disposable root: /var/folders/4p/qcjpbnz56m15bct40fb6pnn00000gn/T/gvs-audit-independent-y_pn3rd6.

```python
import json,tempfile,shutil,hashlib
from pathlib import Path
from benchmark.graph_value_skeleton import runner,checks,protocol
from benchmark.graph_value_skeleton.tests import fixtures
root=Path(tempfile.mkdtemp(prefix='gvs-audit-independent-'))
fx=fixtures.build_fixture(root/'fixture','region')
conf=fixtures.make_config(root,fx,method='shuffled',shuffle_seed=0,run_id='valid')
run=Path(runner.execute_run(conf)['run_dir'])
def tree(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
for case in ['missing-context','wrong-context','negative-swaps','missing-context-result-hash','fractional-raw-count']:
 d=root/case
 shutil.copytree(run,d)
 path=d/'graph-audit.json'; obj=json.loads(path.read_text())
 if case=='missing-context': obj['shuffle']['contexts'].pop()
 elif case=='wrong-context': obj['shuffle']['contexts'][0]['context']=[999]
 elif case=='negative-swaps':obj['shuffle']['contexts'][0]['accepted']=-1
 elif case=='missing-context-result-hash':obj['shuffle']['contexts'][0].pop('result_edges_sha256')
 else:obj['raw_rows']+=0.5
 path.write_text(json.dumps(obj))
 before=tree(d)
 r=checks.command_recompute(run_dir=d,repo_root=protocol.REPO_ROOT,command=['independent-audit-probe',case],report_path=root/(case+'.json'))
 print(json.dumps({'case':case,'status':r['status'],'errors':r['envelope']['errors'],'inputs_unchanged':before==tree(d)}))
print('PROBE_ROOT',root)

```

The negative-swaps public CLI was also executed against the disposable run above:

```bash
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton recompute --run-dir /var/folders/4p/qcjpbnz56m15bct40fb6pnn00000gn/T/gvs-audit-independent-ynmswk_5/negative-swaps --report /var/folders/4p/qcjpbnz56m15bct40fb6pnn00000gn/T/gvs-audit-independent-ynmswk_5/negative-swaps-cli.json
```

Current observation: exit1, status=failed. Use a fresh report name on repetition; reports are exclusive.

### Appendix I: Shuffle-audit consistency counterexamples — now rejected

Run this standalone block in the pinned interpreter from the repository root. All five original and seven later mutations now fail with unchanged input bytes. The valid run is a synthetic development fixture with the full frozen training budget. Only disposable saved copies are changed.

```python
import json,tempfile,shutil,hashlib
from pathlib import Path
from benchmark.graph_value_skeleton import runner,checks,protocol
from benchmark.graph_value_skeleton.tests import fixtures
root=Path(tempfile.mkdtemp(prefix='gvs-audit-independent-'))
fx=fixtures.build_fixture(root/'fixture','region')
conf=fixtures.make_config(root,fx,method='shuffled',shuffle_seed=0,run_id='valid')
run=Path(runner.execute_run(conf)['run_dir'])
def tree(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}

valid=checks.command_recompute(run_dir=run,repo_root=protocol.REPO_ROOT,command=['independent-audit-probe','valid'],report_path=root/'valid.json')
print('VALID',valid['status'])
cases=['missing-context','wrong-context','negative-swaps','missing-context-result-hash','fractional-raw-count','changed-fraction','missing-changed-fraction','coherent-false-overlap','missing-rejections','inconsistent-rejections','lower-work-budget','missing-top-changed']
for case in cases:
 d=root/case
 shutil.copytree(run,d)
 path=d/'graph-audit.json'; obj=json.loads(path.read_text()); sh=obj['shuffle']; ctx=sh['contexts'][0]
 if case=='missing-context': sh['contexts'].pop()
 elif case=='wrong-context': ctx['context']=[999]
 elif case=='negative-swaps':ctx['accepted']=-1
 elif case=='missing-context-result-hash':ctx.pop('result_edges_sha256')
 elif case=='fractional-raw-count':obj['raw_rows']+=0.5
 elif case=='changed-fraction': ctx['changed_fraction']=-1.0
 elif case=='missing-changed-fraction': ctx.pop('changed_fraction')
 elif case=='coherent-false-overlap':
  e=ctx['edge_count']; print('REAL_OVERLAP',ctx['changed_edges'],ctx['intersection_edges'],e)
  ctx.update(changed_edges=1,added_edges=1,intersection_edges=e-1,symmetric_difference_edges=2,changed_fraction=1/e,intersection_fraction=(e-1)/e,symmetric_difference_fraction=1/e)
  sh['changed_edges']=sum(c['changed_edges'] for c in sh['contexts'])
 elif case=='missing-rejections':ctx.pop('rejections')
 elif case=='inconsistent-rejections':ctx['rejections']={'same_edge_index':ctx['attempts']+1}
 elif case=='lower-work-budget':
  sh['accept_target_factor']=1
  for c in sh['contexts']:c['target_accepted']=c['edge_count'];c['accepted']=c['edge_count']
  sh['totals']['accepted']=sum(c['accepted'] for c in sh['contexts'])
 elif case=='missing-top-changed':sh.pop('changed_edges')
 path.write_text(json.dumps(obj))
 before=tree(d)
 r=checks.command_recompute(run_dir=d,repo_root=protocol.REPO_ROOT,command=['independent-audit-probe',case],report_path=root/(case+'.json'))
 print(json.dumps({'case':case,'status':r['status'],'errors':r['envelope']['errors'],'inputs_unchanged':before==tree(d)}))
print('PROBE_ROOT',root)

```

On context0, independently construct sets from graph/source-edges.npy and graph/edges.npy, selecting endpoints whose saved nodes.parquet context is0. E=6, removed4, added4, intersection2 and symmetric difference8. The coherent-false-overlap case leaves both saved arrays/hashes unchanged while claiming removed1, added1, intersection5 and difference2 with matching fractions; it now fails with the actual saved-set values named in the report. This can be established without replaying shuffling or loading any source Parquet.

Public CLI confirmation of the negative fraction (current exit1, status=failed):

```bash
conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton recompute --run-dir /var/folders/4p/qcjpbnz56m15bct40fb6pnn00000gn/T/gvs-audit-independent-y_pn3rd6/changed-fraction --report /var/folders/4p/qcjpbnz56m15bct40fb6pnn00000gn/T/gvs-audit-independent-y_pn3rd6/changed-fraction-cli.json
```

Use the fresh root printed by the probe and a fresh report name on repetition.

### Appendix J: Current independent audit and public CLI assertions

Executed from the implementation root with PYTHONPATH=. conda run -n job-sdf-baseline python /tmp/gvs-verify5-audit.py. The temporary file is disposable; this block is its full reproducible content. It asserts20 rejections, valid baseline success, three nonzero actual CLI subprocess exits and bytewise input immutability.

```python
import json,tempfile,shutil,hashlib
from pathlib import Path
from benchmark.graph_value_skeleton import runner,checks,protocol
from benchmark.graph_value_skeleton.tests import fixtures
root=Path(tempfile.mkdtemp(prefix='gvs-audit-independent-'))
fx=fixtures.build_fixture(root/'fixture','region')
conf=fixtures.make_config(root,fx,method='shuffled',shuffle_seed=0,run_id='valid')
run=Path(runner.execute_run(conf)['run_dir'])
def tree(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}

valid=checks.command_recompute(run_dir=run,repo_root=protocol.REPO_ROOT,command=['independent-audit-probe','valid'],report_path=root/'valid.json')
assert valid['status']=='ok',valid
print('VALID',valid['status'])
cases=['missing-context','wrong-context','negative-swaps','missing-context-result-hash','fractional-raw-count','changed-fraction','missing-changed-fraction','coherent-false-overlap','missing-rejections','inconsistent-rejections','lower-work-budget','missing-top-changed']
for case in cases:
 d=root/case
 shutil.copytree(run,d)
 path=d/'graph-audit.json'; obj=json.loads(path.read_text()); sh=obj['shuffle']; ctx=sh['contexts'][0]
 if case=='missing-context': sh['contexts'].pop()
 elif case=='wrong-context': ctx['context']=[999]
 elif case=='negative-swaps':ctx['accepted']=-1
 elif case=='missing-context-result-hash':ctx.pop('result_edges_sha256')
 elif case=='fractional-raw-count':obj['raw_rows']+=0.5
 elif case=='changed-fraction': ctx['changed_fraction']=-1.0
 elif case=='missing-changed-fraction': ctx.pop('changed_fraction')
 elif case=='coherent-false-overlap':
  e=ctx['edge_count']; print('REAL_OVERLAP',ctx['changed_edges'],ctx['intersection_edges'],e)
  ctx.update(changed_edges=1,added_edges=1,intersection_edges=e-1,symmetric_difference_edges=2,changed_fraction=1/e,intersection_fraction=(e-1)/e,symmetric_difference_fraction=1/e)
  sh['changed_edges']=sum(c['changed_edges'] for c in sh['contexts'])
 elif case=='missing-rejections':ctx.pop('rejections')
 elif case=='inconsistent-rejections':ctx['rejections']={'same_edge_index':ctx['attempts']+1}
 elif case=='lower-work-budget':
  sh['accept_target_factor']=1
  for c in sh['contexts']:c['target_accepted']=c['edge_count'];c['accepted']=c['edge_count']
  sh['totals']['accepted']=sum(c['accepted'] for c in sh['contexts'])
 elif case=='missing-top-changed':sh.pop('changed_edges')
 path.write_text(json.dumps(obj))
 before=tree(d)
 r=checks.command_recompute(run_dir=d,repo_root=protocol.REPO_ROOT,command=['independent-audit-probe',case],report_path=root/(case+'.json'))
 assert r['status']=='failed', (case,r)
 assert before==tree(d),case
 print(json.dumps({'case':case,'status':r['status'],'errors':r['envelope']['errors'],'inputs_unchanged':before==tree(d)}))
print('PROBE_ROOT',root)

import subprocess,sys
for case in ('changed-fraction','coherent-false-overlap','lower-work-budget'):
 d=root/case; before=tree(d); report=root/(case+'-cli.json')
 args=[sys.executable,'-m','benchmark.graph_value_skeleton','recompute','--run-dir',str(d),'--report',str(report)]
 done=subprocess.run(args,capture_output=True,text=True)
 envelope=json.loads(report.read_text())
 assert done.returncode!=0 and envelope['status']=='failed',(case,done.returncode,envelope)
 assert before==tree(d)
 print('CLI',json.dumps({'case':case,'exit':done.returncode,'status':envelope['status'],'inputs_unchanged':True}))
for index,(field,value) in enumerate([
 ('changed_fraction',float('nan')),('intersection_fraction',float('inf')),
 ('symmetric_difference_fraction',True),('intersection_fraction',None),
 ('changed_fraction',1.1),('symmetric_difference_fraction',-0.01),
 ('intersection_fraction','0.5'),('changed_fraction',0.0),
]):
 d=root/('fraction-type-'+str(index)); shutil.copytree(run,d)
 path=d/'graph-audit.json'; obj=json.loads(path.read_text()); obj['shuffle']['contexts'][0][field]=value;path.write_text(json.dumps(obj))
 before=tree(d); r=checks.command_recompute(run_dir=d,repo_root=protocol.REPO_ROOT,command=['independent-audit-type',field,str(value)],report_path=root/(d.name+'.json'))
 assert r['status']=='failed' and before==tree(d),(field,value,r)
 print('FRACTION_TYPE',json.dumps({'field':field,'value':str(value),'status':r['status'],'inputs_unchanged':True}))
print('ALL_20_CASES_REJECTED',True)

```

### Appendix K: Empty-context schema and shared checker acceptance

Executed with PYTHONPATH=. conda run -n job-sdf-baseline python /tmp/gvs-verify5-extra.py. Valid seed0/1/2 mixed-context runs pass. Eight isolated empty-context corruptions fail; compare on genuine distinct executions and summary with three seed members reject the same nonempty-context audit error. Every checked input is bytewise unchanged.

```python
import json,tempfile,shutil,hashlib
from pathlib import Path
import numpy as np
from benchmark.graph_value_skeleton import runner,checks,protocol
from benchmark.graph_value_skeleton.tests import fixtures
root=Path(tempfile.mkdtemp(prefix='gvs-audit-extra-'))
keys=[(0,s) for s in range(4)]+[(2,s) for s in range(4)]
signal=np.arange(len(keys)*36,dtype=np.float32).reshape(len(keys),36)+1
rows=[(0,s,t) for s,t in fixtures.CONTEXT_EDGES['region']]
fx=fixtures.build_fixture(root/'fixture','r2',keys=keys,signal=signal,graph_rows=rows)
runs={}
for seed in (0,1,2):
 cfg=fixtures.make_config(root,fx,method='shuffled',shuffle_seed=seed,run_id='seed'+str(seed))
 runs[seed]=Path(runner.execute_run(cfg)['run_dir'])
def tree(d):return {str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest() for p in d.rglob('*') if p.is_file()}
for seed,run in runs.items():
 before=tree(run)
 r=checks.command_recompute(run_dir=run,repo_root=protocol.REPO_ROOT,command=['empty-context-valid',str(seed)],report_path=root/('valid'+str(seed)+'.json'))
 assert r['status']=='ok' and before==tree(run),(seed,r)
print('MIXED_EMPTY_VALID_SEEDS',list(runs))
for case in ('fraction','missing-fraction','changed-count','intersection-count','difference-count','missing-rejections','rejections','fractional-count'):
 d=root/case;shutil.copytree(runs[0],d)
 p=d/'graph-audit.json';obj=json.loads(p.read_text());c=next(c for c in obj['shuffle']['contexts'] if c['empty'])
 if case=='fraction':c['changed_fraction']=0.0
 elif case=='missing-fraction':c.pop('changed_fraction')
 elif case=='changed-count':c['changed_edges']=1
 elif case=='intersection-count':c['intersection_edges']=1
 elif case=='difference-count':c['symmetric_difference_edges']=1
 elif case=='missing-rejections':c.pop('rejections')
 elif case=='rejections':c['rejections']={'same_edge_index':1}
 elif case=='fractional-count':c['accepted']=0.5
 p.write_text(json.dumps(obj));before=tree(d)
 r=checks.command_recompute(run_dir=d,repo_root=protocol.REPO_ROOT,command=['empty-context-bad',case],report_path=root/(case+'.json'))
 assert r['status']=='failed' and before==tree(d),(case,r)
 print('EMPTY_CORRUPTION',case,r['status'])
# Real distinct same-condition repeat for compare validation.
repeat_cfg=fixtures.make_config(root,fx,method='shuffled',shuffle_seed=0,run_id='repeat0')
repeat=Path(runner.execute_run(repeat_cfg)['run_dir'])
bad=root/'bad-repeat';shutil.copytree(repeat,bad)
p=bad/'graph-audit.json';obj=json.loads(p.read_text());obj['shuffle']['contexts'][0]['changed_fraction']=-1;p.write_text(json.dumps(obj))
before=(tree(runs[0]),tree(bad))
r=checks.command_compare(run_a=runs[0],run_b=bad,repo_root=protocol.REPO_ROOT,command=['shared-audit-compare'],report_path=root/'compare.json')
assert r['status']=='failed' and before==(tree(runs[0]),tree(bad)),r
assert 'changed_fraction' in json.dumps(r['envelope']['errors']),r
print('SHARED_COMPARE',r['status'])
summary_bad=root/'bad-member';shutil.copytree(runs[0],summary_bad)
p=summary_bad/'graph-audit.json';obj=json.loads(p.read_text());obj['shuffle']['contexts'][0]['changed_fraction']=-1;p.write_text(json.dumps(obj))
paths=[summary_bad,runs[1],runs[2]];before=[tree(d) for d in paths]
r=checks.command_summarize_shuffled(run_dirs=paths,repo_root=protocol.REPO_ROOT,command=['shared-audit-summary'],report_path=root/'summary.json')
assert r['status']=='failed' and before==[tree(d) for d in paths],r
assert 'changed_fraction' in json.dumps(r['envelope']['errors']),r
print('SHARED_SUMMARY',r['status'])
print('EXTRA_ROOT',root)

```
