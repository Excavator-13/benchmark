# Implementation Notes

- Change: `add-graph-value-skeleton`
- Schema: `spec-driven`
- Store: local (`openspec/changes/` in `/Users/watuji/da_chuang/repos/benchmark`; no registered store)
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark`
- Updated: 2026-10-18T16:47:00+08:00 (Asia/Shanghai)
- Implementation revision: `e83cb540d4be9950d79233b29b393155e5cae505` (branch `xzs`) with a dirty worktree. HEAD does not contain the new package: `benchmark/graph_value_skeleton/` is untracked and `README.md` is modified. `DELEGATION.md`, `research/phases/P02/plan.md` and `research/state.md` were already modified by the research-side turn before this apply session and were not edited here.
- Progress: 33/33 tasks complete; no pause. Independent verification has not been performed and no verdict is claimed.

## What was implemented

New package `benchmark/graph_value_skeleton/`:

| File | Role |
| --- | --- |
| `protocol.py` | Frozen P02 constants, published expectations, seed profiles, parameter counts, protocol/policy identity helpers |
| `config.py` | Explicit method/model-seed/shuffle-seed axes, purpose-scoped output roots, run-ID escape checks, computational identity |
| `data.py` | P01 demand reuse, published demand assertions, dense-offset proof, masks, naive-reference block |
| `graph.py` | Context-qualified endpoint mapping, published graph assertions, multiplicity audit, context layout |
| `model.py` | Per-node `GRU(1,32)`, shared `Linear(32,3)`, incoming-neighbour mean (exact zero message), parameter measurement |
| `shuffle.py` | Context-local degree-preserving directed double-edge swaps, PCG64/SeedSequence, audit, explicit failures |
| `training.py` | Determinism pinning, 200-epoch Adam training with chunked global-MSE gradient accumulation, validation-MSE selection |
| `artifacts.py` | Exclusive run directory, scoped source capture, environment capture, peak RSS |
| `runner.py` | Stage orchestration, complete artifacts, status/failure evidence, summary |
| `checks.py` | Saved-only `recompute`, same-condition `compare`, `summarize-shuffled`, exclusive reports |
| `cli.py`, `__main__.py`, `_worker.py` | Public entry, pinned-thread isolated worker, report commands |
| `requirements.txt` | CPU-only pinned dependencies (torch 2.14.1, NumPy 1.26.4, pandas 2.2.3, PyArrow 17.0.0) |
| `tests/` | 10 test modules + fixtures (93 tests) |

`README.md` gained only a new `### 4.6` entry chapter (+121 lines, 0 removed lines); no existing
chapter, research record, P01 source file, protocol, old run, archive or dataset was modified.

## Implementation map

| Task / requirement / scenario | Code and tests | Decisions / context |
| --- | --- | --- |
| 1.1 pre-change P01 evidence | `scratch/graph-value-skeleton/p01_capture.py` (ignored) → `scratch/graph-value-skeleton/p01-baseline/{capture.json,arrays.npz,oracle.json}` | P01-only capture before new computation; independent loop oracle `ok` for r0/region/r2; max normalized metric difference 2.15e-16; float32-accumulating `WindowMean6`/`TrainMean27` recorded as the only natural-variation numeric field |
| 1.2 package, fixtures, P01 identity | `data.py`, `tests/fixtures.py`, `test_p01_identity.py::test_demand_identity_matches_p01`, `::test_invalid_fixture_inputs_rejected` | `from_fixture` delegates to P01 `from_arrays`; keys/SHA256/float32 signals/all 28 window inputs+labels are elementwise equal |
| 1.3 published demand assertions | `data.assert_published_demand`, `assert_dense_published_offsets`; `test_graph_mapping.py::test_published_demand_assertions_positive_and_negative`, `::test_dense_offset_formula_proven_on_published_grids`, `::test_real_published_schema_is_readable_read_only` | Full-size expectations (2335/16345/121420, contexts `{0}`/`0..6`/`0..51`, skills `0..2334`) asserted only for published paths; fixtures bypass full-size checks; real files checked read-only (see integrated evidence below) |
| 2.1 mapping | `graph.load_graph`, `canonical_edge_array`, `context_layout`; `test_mapping_matches_prepare_graph_data`, `test_invalid_endpoints_and_columns_fail` | Compared against `prepare_graph_data.build_graph_dataset` on a non-dense multi-context fixture with skills 2/10; row→col is source→target; unknown/non-integer/missing/weight-column endpoints fail |
| 2.2 published graph structure and multiplicity | `graph.load_graph`; `test_published_graph_assertions`, `test_multiplicity_audited_not_weighted`, `test_self_loops_rejected` | Exact row counts, semantic columns, no duplicates/self-loops, symmetry 1.0 and block diagonal for published; fixture duplicates audited then collapsed to binary edges; self-loops always rejected |
| 2.3 fixed masks | `data.load_neighbor_coverage`, `build_masks`; `test_shared_masks_match_p01` | Reuses `ridge.compute_training_stats` and P01 coverage elementwise; all methods share the same masks; shuffled adjacency never redefines evaluation groups |
| 3.1 encoder | `model.SkeletonModel`, `predict_windows`, `encode_windows`; `test_model.py::EncoderTest` | Batch dimension carries nodes; per-node loop oracle within 1e-6 normalized; perturbing another node leaves hidden state bitwise equal; window/split state resets |
| 3.2 propagation | `model.aggregate_incoming_mean`, `GraphAggregation`; `test_asymmetric_direction_oracle`, `test_duplicate_rows_do_not_weight_a_neighbour`, `test_isolated_and_empty_graph_exact_equality` | `0→1,2→1,1→2` oracle; outgoing implementation differs; zero in-degree and empty graph use `torch.where` selection for exact equality; self-loop aggregation rejected |
| 3.3 parameters / seeds | `parameter_signature`, `parameter_counts`, `graph_only_parameter_names`; `test_no_graph_parameter_capacity`, `test_three_methods_share_initial_parameters`, `test_shuffle_does_not_consume_model_rng`, `test_training_state_is_independent_per_model` | Measured GRU 3360 + head 99 = 3459, graph-only empty; same model seed gives identical initial state dicts; shuffle uses NumPy PCG64 and leaves torch RNG untouched |
| 3.4 CPU runtime | `training.configure_determinism`, `artifacts.capture_environment`; `test_determinism_settings`, `test_real_cpu_forward_backward_without_graph_extensions` | Threads 1/1, deterministic algorithms on, five BLAS variables pinned to `1`; real GRU forward/backward under blocked `torch_geometric`/`dgl`/`torch_scatter`/`torch_sparse`; environment records Python 3.11.17, torch 2.14.1, CUDA unavailable |
| 4.1 swap algorithm | `shuffle._swap_edges`, `swap_context_edges`; `test_preserves_degrees_and_changes_every_context`, `test_each_accepted_swap_preserves_degrees` | Accept 10·E per context, attempt limit 100·E; per-node in/out degrees preserved after each tested accept factor; nonempty contexts change |
| 4.2 audit and reproducibility | `shuffle.shuffle_graph`; `test_reproducible_across_row_order_and_seed`, `test_reproducible_across_process_hash_seed`, `test_empty_context_recorded_and_unsupported_seed_rejected`, `test_failures_are_explicit_and_never_return_the_original` | Same seed reproduces across row order and `PYTHONHASHSEED` subprocesses; empty contexts explicit; single-edge/no-legal-swap, exhausted budget and unchanged-final-graph fail rather than returning the original |
| 4.3 seeds and shuffled control | `shuffle.SHUFFLE_SEEDS`, `checks.command_summarize_shuffled`; `test_summarize_shuffled_averages_three_members`, `test_summarize_rejects_incomplete_or_mixed_members`, `test_summarize_rejects_incompatible_graph_identity`; end-to-end summary per schema | Seeds 0/1/2 only; control is arithmetic mean of three independently trained member MAEs; averaged-prediction MAE recorded only as a contrast; missing/duplicate/mixed members fail |
| 5.1 axes and CLI | `config.resolve_config`, `cli.build_parser`, `test_method_and_seed_axes`, `test_help_surface`, `test_cli_passes_every_axis_to_the_worker`, `test_worker_spec_round_trips_through_launch` | Shuffled requires seed and other methods forbid it; seeds outside 0..4 and purposes outside development/formal fail before reservation; method/seed axes flow through the spec to the worker |
| 5.2 training budget | `training.train`, `build_chunks`; `test_chunked_gradient_equals_full_batch`, `test_unequal_context_sizes_are_element_weighted`, `test_chunks_follow_ascending_window_then_context`, `test_exactly_200_epochs_and_steps` | Chunks follow ascending window then context with complete context adjacency; chunked grads equal full-batch within 1e-6; exactly one optimizer step per epoch and 200 steps total |
| 5.3 selection and isolation | `training.train`, `_earliest_minimum`, `selected_predictions`; `test_selection_uses_validation_mse_not_mae`, `test_exact_tie_selects_earliest_epoch`, `test_test_labels_are_not_accepted_by_training`, `test_test_targets_do_not_affect_selection` | Validation MSE decides; earliest epoch on exact tie; MAE winner may differ; training/selection APIs contain no test argument; perturbing only test targets leaves history/selection bitwise identical |
| 5.4 naive references | `data.naive_reference_block`; `test_naive_reference_matches_p01`, `test_zero_reference_gain_is_unavailable` | Exactly P01 predictions/scores/table-order ties; published runs assert NaiveRef=LastValue; zero reference yields unavailable gain with reason (confirmed on real r0 smoke) |
| 5.5 destinations | `config.resolve_output_root`, `validate_run_destination`; `test_development_destination_whitelist`, `test_run_id_cannot_escape`, `test_formal_resolution_is_path_only` | Development root must resolve inside `scratch/` or system temp (symlink resolved); run IDs cannot traverse; formal resolves only `research/runs` and is never executed |
| 6.1 provenance | `artifacts.capture_source`, `capture_environment`, `runner._provenance_payload`; `test_config_and_provenance`, `test_source_capture_scope`, `SourceCaptureScopeTest`, `test_source_content_change_fails_the_run` | Temporary Git fixture proves only runtime modules are captured (unrelated research/tests/caches excluded); missing Git identity disclosed with `code-untracked/` fallback; a mid-run source content change fails the run before success |
| 6.2 complete artifacts | `runner.execute_run`, `_write_dataset_artifacts`, `_write_selection_artifacts`, `_write_prediction_artifacts`; `ArtifactCompletenessTest` | All D9 files present; arrays load with `allow_pickle=False`; shapes `[1,N,3]`/`[4,N,3]`; selected NPZ reload reproduces saved validation predictions exactly; history has 200 rows |
| 6.3 metrics | `metrics.split_report` reuse; `test_metrics.py` | Independent loop oracle for overall/window/horizon/context/activity/constant/neighbor/counts/contributions/gains; overall RMSE is not mean window RMSE; multiplicities 1/2/3/3/2/1; empty groups null/zero; zero reference unavailable |
| 6.4 recompute | `checks.command_recompute`, `recompute_run`, `_validate_loaded`; `test_recompute_reads_saved_evidence_only`, `test_recompute_detects_corrupt_evidence`, `test_recompute_reports_failure_for_missing_artifacts` | Source loading, training and forward blocked during recompute; 1e-12 normalized tolerance; eight tamper classes fail; inputs byte-identical; one exclusive report only |
| 6.5 compare | `checks.command_compare`, `compare_predictions`, `_condition_identity`; `test_same_seed_repeat_compare_passes`, `test_compare_rejects_numeric_mismatch`, `test_compare_rejects_condition_mismatch_with_identical_predictions` | Strict identity conditions (data/graph/method/seeds/protocol/policy/code/environment/masks); MAE and elementwise normalized prediction differences ≤1e-6; max absolute difference recorded; environment mismatch fails with byte-identical predictions |
| 6.6 reports | `checks.validate_report_destination`, `_write_report`, envelope; `test_report_destination_is_exclusive_and_scoped` | One exclusive JSON report; scratch/temp only; rejects existing files, input directories, research paths and symlink escapes; failure reports are single and do not create check-run sidecars |
| 6.7 costs | `artifacts.measure_peak_rss`, `runner._measurements_payload`; `test_measurements_are_measured_and_scoped`, `PeakMemoryTest` | Stage timings incl. graph read, shuffle, training, validation, selected inference and total; Darwin bytes / Linux KiB×1024 conversion tested; native unit/method/scope/machine/N/E/epochs recorded; fixture vs published cost scope labeled |
| 6.8 lifecycle | `RunDirectory` (reused exclusive writer), `check_unfinished`, failure paths; `LifecycleTest` | Collision does not overwrite; graph failure and KeyboardInterrupt keep stage evidence and terminal status; leftover `running` classified unfinished; success does not touch `research/runs` |
| 7.1 fixture matrix | `test_end_to_end.py::EndToEndMatrixTest` | r0/region/r2 × self/graph/shuffled(0/1/2), full 200 epochs, CPU; identity/masks/params/history/selected/artifacts/metrics/costs/status checked; one public CLI→worker run per method |
| 7.2 repeats and summary | `test_each_method_recomputes_and_repeats`, `test_shuffled_members_are_distinct_and_summarized`, `test_no_research_records_or_benefit_claims` | Two same-seed runs per method recompute and compare `ok`; three shuffled members summarised per schema; reports in temp; `research/runs` and `research/state.md` snapshot unchanged; no benefit claims |
| 7.3 suite + regressions | exact commands below | New suite 93 tests OK; existing P01 suite 287 tests OK (2 skipped); old `prepare_graph_data` suite 32 tests OK |
| 7.4 real-data smoke decision | Ignored scratch evidence below | One bounded published r0 self development smoke (two 200-epoch runs + recompute + compare) and read-only published integration for all three datasets; region/r2 training intentionally not executed (cost) and recorded as such |
| 8.1 README | `README.md` §4.6 | New chapter only; commands cross-checked against actual `--help` and fixture/real CLI executions |
| 9.1/9.2 | this file | A01–A18 index and read-only scope audit below |

## Checks run

| Command | Working directory / setup | Result / evidence | Time / revision |
| --- | --- | --- | --- |
| `PYTHONPATH=. conda run -n job-sdf-baseline python scratch/graph-value-skeleton/p01_capture.py` | repo root; P01 modules only | `{"oracle": {"r0": "ok", "r2": "ok", "region": "ok"}}`; `scratch/graph-value-skeleton/p01-baseline/{capture.json,arrays.npz,oracle.json}`; max normalized metric difference 2.15e-16 | pre-package implementation, 2026-10-18 |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/graph_value_skeleton/tests -v` | repo root; pinned CPU env | `Ran 93 tests ... OK`; log `scratch/graph-value-skeleton/logs/new-suite.log` | 93.0 s, worktree state above |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/nograph_baseline/tests -v` | repo root; no graph imports; torch not required by that entry | `Ran 287 tests ... OK (skipped=2)`; log `scratch/graph-value-skeleton/logs/p01-suite.log` | 40.3 s |
| `conda run -n job-sdf-baseline python -m unittest benchmark.graph_method.tests.test_prepare_graph_data -v` | repo root | `Ran 32 tests ... OK`; log `scratch/graph-value-skeleton/logs/graph-prep.log` | 0.08 s |
| `PYTHONPATH=. conda run -n job-sdf-baseline python scratch/graph-value-skeleton/published_integration.py` | repo root; read-only published files, no training | `scratch/graph-value-skeleton/published-integration.json`: r0 2335 nodes/60804 edges, region 16345/218840, r2 121420/321374; raw rows equal unique edges; symmetry 1.0; block diagonal true; published NaiveRef=LastValue | 2.9 s |
| `conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton run --data-name r0 --method self --model-seed 0 --purpose development --output-root scratch/graph-value-skeleton/published-smoke --run-id smoke-r0-self-s0-a` (and `-b`) | repo root; published r0 demand+graph; fresh worker per run | Both `success`; selected epoch 200; parameters 3459; NaiveRef=LastValue; test MAE self 1159.09 vs LastValue 189.88 (implementation observation only, no tuning or benefit claim); measured total 20.56 s / 21.8 s; peak RSS 494,501,888 bytes (`worker process lifetime`); test-window target multiplicities 1,2,3,3,2,1 | 2026-10-18, two runs |
| `conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton recompute --run-dir scratch/graph-value-skeleton/published-smoke/smoke-r0-self-s0-a --report scratch/graph-value-skeleton/reports/published-r0-a-recompute.json` | saves-only check | `status: ok`; max normalized metric difference 0.0; input bytes unchanged | 2026-10-18 |
| `conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton compare --run-a ...-a --run-b ...-b --report scratch/graph-value-skeleton/reports/published-r0-repeat.json` | two independent published r0 executions | `status: ok`; max absolute prediction difference 0.0 on validation and test; condition identity identical | 2026-10-18 |
| `conda run -n job-sdf-baseline python -m benchmark.graph_value_skeleton --help` / `run --help` / `summarize-shuffled --help` | repo root | CLI surface matches README §4.6 (methods, seeds, purpose, run-id, output-root; three-directory summary) | 2026-10-18 |

Environment actually used: Python 3.11.17, PyTorch 2.14.1 (`torch.version.cuda=None`,
`cuda_available=False`), NumPy 1.26.4, pandas 2.2.3, PyArrow 17.0.0, macOS Darwin.
`torch_geometric 2.8.0.post1`, `torch_scatter 2.1.2` and `torch_sparse 0.6.18` are present in the
environment but are never imported by the new entry (availability recorded with `find_spec`; tests
block their import during the real forward/backward). Default `python` 3.13 was not used.

## Acceptance checklist evidence index (A01–A18)

| ID | Status | Evidence |
| --- | --- | --- |
| A01 | Covered | `data.assert_published_demand`; `test_published_demand_assertions_positive_and_negative`, `test_dense_offset_formula_proven_on_published_grids`; real read-only counts in `published-integration.json` and the published r0 smoke |
| A02 | Covered | `graph.load_graph` published branch; `test_published_graph_assertions`, `test_invalid_endpoints_and_columns_fail`; real counts/symmetry/block diagonal above |
| A03 | Covered | `test_demand_identity_matches_p01`, `test_mapping_matches_prepare_graph_data`, `test_integer_order_places_2_before_10`; pre-change oracle |
| A04 | Covered | `test_model.py::EncoderTest` (loop/vectorized ≤1e-6, node/window isolation), shapes in artifacts |
| A05 | Covered | `test_no_graph_parameter_capacity`, `test_three_methods_share_initial_parameters`, `test_training_state_is_independent_per_model`; every run records measured 3360/99/3459 and empty graph-only set |
| A06 | Covered | `test_asymmetric_direction_oracle`, `test_duplicate_rows_do_not_weight_a_neighbour`, `test_isolated_and_empty_graph_exact_equality` |
| A07 | Covered | `test_shuffle.py` (degrees after each accept factor, change per context, same-seed reproducibility across row order and hash seed, explicit failures); e2e member graph hashes distinct |
| A08 | Covered | `test_summarize_shuffled_averages_three_members` + rejection tests; e2e summary per schema; control = mean of member MAEs, averaged-prediction MAE only a contrast |
| A09 | Covered | `test_demand_identity_matches_p01`, `test_naive_reference_matches_p01`; 28-window metadata equality; published r0 smoke NaiveRef=LastValue |
| A10 | Covered | `test_shared_masks_match_p01`, `test_metrics.py`, e2e shared mask hashes; metrics include overall/window/horizon/context/activity/constant/neighbor/counts/negative ratio/contributions/balanced MAE/empty groups/zero-reference gains |
| A11 | Covered | `test_training.py` (200 epochs, one step/epoch, MSE selection, earliest tie, test isolation); history/selection artifacts; published r0 selected epoch 200 |
| A12 | Covered | `ArtifactCompletenessTest`, `SourceCaptureScopeTest`, `PeakMemoryTest`; published r0 `provenance.json`/`source.json`/`environment.json`/`measurements.json` |
| A13 | Covered | `test_recompute_reads_saved_evidence_only` (source/training/forward blocked), eight tamper classes, `test_report_destination_is_exclusive_and_scoped`; published r0 recompute `ok` |
| A14 | Covered | `test_same_seed_repeat_compare_passes`, `test_compare_rejects_numeric_mismatch`, condition-mismatch test; e2e repeats per method; published r0 repeat compare `ok` with 0.0 max absolute difference |
| A15 | Covered | `AxisValidationTest`, `CliSurfaceTest`, interleaved-method global snapshot; destination/symlink/traversal tests; purpose does not change computational identity |
| A16 | Covered | `CpuRuntimeTest`; environment records exact versions/flags; new suite 93 OK; P01 suite 287 OK; old graph-prep suite 32 OK |
| A17 | Covered | `test_measurements_are_measured_and_scoped`, `PeakMemoryTest`, e2e measurements; published r0 measured cost/RSS above; fixture cost scope labeled synthetic |
| A18 | Covered | README diff is +121/−0 lines; scope audit below shows no research record, protocol, old-run, archive, dataset or P01-source edits; no commit, push, formal run, sealing or delegation-pointer edit |

## Read-only scope audit (task 9.2)

`git status --porcelain` at the end of apply:

```
 M DELEGATION.md                      # pre-existing research-side change, not edited by apply
 M README.md                          # apply: new §4.6 only (+121/-0)
 M research/phases/P02/plan.md        # pre-existing research-side change, not edited by apply
 M research/state.md                  # pre-existing research-side change, not edited by apply
?? benchmark/graph_value_skeleton/    # apply: new package + tests + requirements
?? openspec/changes/add-graph-value-skeleton/  # planning artifacts + these notes
```

- `git status --porcelain -- benchmark/nograph_baseline benchmark/graph_method dataset research/runs research/phases/P01 experiments_archive` is empty: no P01 source, graph preparation, dataset, old run, protocol or archive was modified.
- `git diff -U0 -- README.md | grep -c '^-'` is 0: the README change is purely additive.
- No commit, push, seal, backup, formal-purpose execution or `DELEGATION.md` edit was performed by this apply.
- All model/check outputs were written under ignored `scratch/` or system temporary directories; the automated suites assert that `research/runs` and `research/state.md` are unchanged.

## Verification reminders

1. **Region/r2 real training was not executed.** Only the published r0 self path completed 200 epochs; region/r2 full training was judged too costly for an implementation check. Published demand/graph assertions, coverage and masks for all three real datasets were executed read-only (`published-integration.json`). Fixtures cover the full 200-epoch path for r0/region/r2 × three methods × three shuffle seeds. Do not infer region/r2 cost or accuracy from r0.
2. **Real published shuffle was not executed.** Fixtures prove degree preservation, per-context change, reproducibility and explicit failures. The frozen budget for real r2 would require ~3,213,740 accepted swaps, so no real shuffled run was attempted.
3. **Formal purpose was never executed.** Only path resolution was tested. Running `--purpose formal` writes `research/runs/<run-id>/` and requires separate research authorization; verification and implementation must not run it.
4. **Report destinations are restricted to ignored scratch or system temp.** This is stricter than P01's `research/reports/`. Recompute/compare/summarize reports for formal runs would also be rejected by this policy; that is intentional for this change, not a bug to "fix" during verification.
5. **Pre-change evidence is disposable.** `scratch/graph-value-skeleton/` is ignored. If it is cleaned, regenerate with the recorded command in this file; the in-repo tests re-derive the same P01 identity live rather than depending on the scratch files.
6. **PyG/torch-scatter/torch-sparse are installed but unused.** The environment records availability via `find_spec`; the tests block their import while running the real GRU/aggregation forward/backward. Their presence must not be read as a dependency.
7. **Published graph Parquet carries a physical `__index_level_0__` column** that pandas reconstructs as the index. The loader therefore sees exactly `context + row_id + col_id`; the test asserts the semantic columns and records the artifact.
8. **The published r0 self run is worse than LastValue** (test MAE 1159.09 vs 189.88). This is an implementation observation with the frozen 200-epoch/raw-count settings; no tuning, selection-on-test or benefit claim was made. Do not read implementation readiness as a scientific result.
9. **Selected epoch on published r0 is 200**, i.e. the last epoch had the best validation MSE. Early stopping is intentionally absent.
10. **Source identity refers to a dirty worktree.** The recorded commit `e83cb54` predates the new package, so the verifier must use `source.json` SHA256 entries, `git-diff.patch` and `code-untracked/` content, not the commit alone, to establish the exact implementation content. A later archive `Verdict: PASS` must have a Verification Basis matching this working-tree implementation.
11. **Fixture runs use system temporary roots.** Automated runs never write into `research/`; a verifier should likewise write reports to `scratch/graph-value-skeleton/` or a temporary directory.
