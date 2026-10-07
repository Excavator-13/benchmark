# Implementation Notes

- Change: `add-nograph-baseline-ridge`
- Schema: `spec-driven`
- Store: local (no OpenSpec store registered; nearest root `/Users/watuji/da_chuang/repos/benchmark`)
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark`
- Updated: 2026-10-07T16:42+08:00
- Implementation revision: `a0fdab4268e5e17b0c96453efd53f01a245f01cc`, dirty working tree (new `benchmark/nograph_baseline/`, modified `README.md` and `tasks.md`, new `research/runs/<run_id>/` evidence). Runtime sources need not match current HEAD.
- Progress: 32/32 tasks complete. Ready for independent verification; no verification has been performed here.

These notes help the verifier locate evidence. They are not an acceptance
authority and do not prove conformance.

## Implementation Map

| Task / requirement / scenario | Code and tests | Decisions / context |
| --- | --- | --- |
| 1.1 package, stable commands, dependency list | `cli.py`, `_worker.py`, `__main__.py`, `requirements.txt`; `tests/test_protocol.py::CliSurfaceTests`; `tests/test_runner_cli.py::CliEndToEndTests::test_public_help_via_subprocess` | Public commands `run`/`recompute`/`compare`/`align-v2`; the isolated worker is a private module so help does not advertise it |
| 1.2 canonical demand loading and audits | `data.py::load_demand`/`build_audit`; `tests/test_data.py::CanonicalIdentityTests` | `float32` signal, ascending `(context, skill)` sort, monthly columns must equal 2021-01..2023-12 exactly |
| 1.3 calendar/window metadata and split assertions | `protocol.py::build_window_metadata`/`validate_split_assertions`; `tests/test_protocol.py::SplitTests`; `tests/test_data.py::WindowConstructionTests` | Omitted starts 19/20/22/23; pairwise-disjoint target months |
| 1.4 frozen training statistics and activity/constant masks | `ridge.py::compute_training_stats`; `tests/test_preprocessing.py` | 27 unique observation months, `ddof=0`, constant std → 1; regression test for the 33-vs-27 month defect |
| 1.5 five naïve methods and frozen references | `baselines.py`; `tests/test_baselines.py` | `SeasonalNaive12` uses target month `t-12`; table-order ties; `NaiveRef6` excludes extra-history |
| 1.6 pure NumPy SharedRidge fit | `ridge.py::fit_numpy`/`build_design`; `tests/test_ridge.py::NumpyFitTests` (independent augmented least-squares check) | One `W[6,3]`/`b[3]`, `M = 19·N`, unregularized intercept, protocol mean-loss objective |
| 1.7 validation-only lambda selection, optional sklearn, clipped reports | `ridge.py::fit_candidates`/`select_lambda`/`fit_sklearn`; `tests/test_ridge.py::CandidateSelectionTests`, `OptionalSklearnTests`; `tests/test_runner_cli.py::RunnerArtifactTests::test_clipped_report_is_separate_and_never_selects` | Ties choose the larger lambda; `alpha = lambda*M`; validation labels inverse-transformed to original units; sklearn test skipped (not installed) |
| 1.8 evaluation-only coverage annotation | `coverage.py`; `tests/test_coverage.py`; `tests/test_runner_cli.py::CoverageInvarianceTests` | Both non-self endpoints covered, self-loops excluded, unmatched endpoints fail, predictions invariant to the annotation |
| 1.9 original-unit metrics and diagnostics | `metrics.py`; `tests/test_metrics.py` | Overall RMSE from all squared errors; empty groups JSON `null`; equal-weight activity MAE; zero reference gain unavailable; per-node training-mean-ranked table |
| 1.10 versioned artifacts and source capture | `artifacts.py`, `runner.py`; `tests/test_runner_cli.py::RunnerArtifactTests` | Atomic writes; `.npy`/`.npz` load with `allow_pickle=False`; git/untracked/environment capture; immutable manifest excludes itself and `events.jsonl` |
| 1.11 isolated CPU execution, timing, RSS, failures | `runner.py`, `cli.py`, `_worker.py`; `tests/test_runner_cli.py::RunnerArtifactTests::test_measurements_record_real_units_and_settings`, `FailureAndInterruptionTests` | Fresh subprocess with BLAS threads pinned before NumPy import; exclusive run IDs; partial evidence retained; unfinished state detectable |
| 1.12 recompute/compare/align-v2 | `checks.py`; `tests/test_runner_cli.py::CheckCommandTests` | Each check reserves a new run directory, hashes its inputs and leaves inputs unchanged |
| 1.13 README section | `README.md` §4.5; `tests/test_runner_cli.py::CliEndToEndTests::test_readme_commands_match_the_parser` | Documents the CPU environment, both datasets, repetition and checks; states outputs are unsealed and not backed up |
| 2.1 data/window suite on r0 and region fixtures | `tests/test_data.py` | Both schemas; no production graph files |
| 2.2 adversarial preprocessing | `tests/test_preprocessing.py::TrainingStatisticsTests` | Overlap-weighted vs unique-month estimates differ; constant nodes stay finite |
| 2.3 fitting/selection adversarial tests | `tests/test_ridge.py::CandidateSelectionTests` | Conflicting MAE/MSE winners, exact ties, changed test labels cannot alter selection |
| 2.4 analytic metrics and saved-only recomputation | `tests/test_metrics.py`, `tests/test_runner_cli.py::CheckCommandTests::test_recompute_without_source_access_and_preserves_inputs` | Recompute deletes the fixture sources first |
| 2.5 minimal-dependency smoke, both schemas | `tests/test_runner_cli.py::CliEndToEndTests::test_minimal_dependency_smoke_for_both_schemas`; `evidence/test-2.5-minimal-dependency.log` | `sitecustomize.py` blocks sklearn/torch/PyG/DGL/graph_method in parent and worker; fixture coverage paths used |
| 2.6 artifact/failure tests | `tests/test_runner_cli.py::FailureAndInterruptionTests`; `evidence/test-2.6-failure-interruption.log` | Existing-ID rejection, malformed source, SIGINT, SIGTERM, SIGKILL unfinished state, fixtures unchanged |
| 2.7 same-seed fixture runs and compare | `tests/test_runner_cli.py::CheckCommandTests::test_compare_two_same_seed_runs` | Zero prediction differences; no seed-variance report |
| 2.8 Parquet/environment/optional backend | `evidence/environment-check.txt`; `tests/test_runner_cli.py::EnvironmentTests`; `tests/test_ridge.py::OptionalSklearnTests` | `job-sdf-baseline` reads Parquet; Python 3.11.17, NumPy 1.26.4, pandas 2.2.3, PyArrow 17.0.0; sklearn absent so its test is skipped |
| 3.1–3.8 formal runs and checks | `research/runs/` run IDs in `implementation.md` §3; `evidence/run-*.log`, `evidence/check-*.log` | Complete formal artifact sets for both datasets, independent same-seed repetitions, saved-only recomputation, comparison and v2 alignment |
| 4.1 implementation evidence document | `openspec/changes/add-nograph-baseline-ridge/implementation.md` | Claims link to retained logs, hashes and run directories |
| 4.2 requirement/evidence mapping | this file | |
| 4.3 write-scope and handoff check | `git status --porcelain`; protected-path checks in §"Scope check" below | Graph source, research records, archives, `DELEGATION.md`, main specs unchanged; no run writers active |

### Requirement → scenario coverage

| Spec requirement | Scenarios and evidence |
| --- | --- |
| Independent CPU entry follows the research protocol | Minimal dependency environment → `test_minimal_dependency_smoke_for_both_schemas` (worker `environment.json` records `sklearn: null`); Unsupported configuration → `test_supported_datasets_and_modes_are_enforced` (argparse rejects `r2`/`rate` before fitting) |
| Demand identity and observations are validated | Valid data out of order → `test_shuffled_parquet_preserves_key_value_alignment`; Source is invalid → `test_duplicate_keys_rejected`, `test_non_integer_keys_rejected`, `test_missing_month_rejected`, `test_extra_month_rejected`, `test_negative_values_rejected`, `test_nonfinite_values_rejected` |
| Fixed windows isolate target months and preserve rolling origins | Protocol split → `SplitTests`, `test_all_starts_and_omissions_accounted_for`; Second test origin → `test_second_test_origin_uses_then_observed_history`, `test_later_test_origin_uses_observed_july_history` |
| All naïve methods and frozen references are reported | Validation MSE ties → `test_exact_tie_uses_protocol_table_order`; Seasonal extra history → `test_seasonal_naive_uses_last_year_same_month`, `test_seasonal_reference_is_labeled_extra_history` |
| Normalization counts training observation months exactly once | Overlap-weighted difference → `test_exactly_27_unique_observations`; Future values change → `test_later_values_do_not_change_statistics_or_fits`; Constant node → `test_constant_node_effective_std_is_one_and_finite` |
| Ridge parameters shared and selected on validation | Test labels cannot affect selection → `test_changed_test_labels_do_not_change_selection`, `test_selected_candidate_scores_match_reported_validation_metrics`; Lambda tie → `test_exact_mse_tie_selects_larger_lambda`; Sum-loss backend → `test_sklearn_matches_numpy` (skipped) and `alpha = lambda*M` assertions in `test_all_five_candidates_record_validation_scores` |
| Metrics use common fixed masks and original units | Window RMSE differs → `test_overall_rmse_is_not_mean_of_window_rmse`; Activity boundaries and empty group → `test_four_activity_boundaries`, `test_empty_activity_group_is_excluded`, formal runs report zero-count groups as `null` |
| Neighbour coverage is an evaluation annotation | Same skill in two regions → `test_same_skill_in_two_regions_is_context_qualified`; invariance → `CoverageInvarianceTests` |
| Each run saves recoverable and recomputable evidence | Independently recomputed → `p01-r0-recompute-*`, `p01-region-recompute-*`; Interrupted or collides → `FailureAndInterruptionTests` |
| Same-seed CPU repetition without artificial seed variance | Same seed twice → `p01-*-repeat-check-001` (max prediction difference 0.0, MAE relative difference 0.0); fixture version `test_compare_two_same_seed_runs` |
| Runtime costs are actual measurements | Formal CPU run finishes → `measurements.json` in each run (stage durations, peak RSS with native unit, execution settings) |
| Formal results align with immutable v2 diagnostics | `p01-r0-alignment-001`, `p01-region-alignment-001` (409 fields, 0 discrepancies each); Legacy value differs → `test_align_v2_preserves_and_explains_discrepancy` |
| Both datasets produce complete formal artifacts | `Execute both supported datasets` → four formal runs with 72 manifest files each, five naïve reports plus selected `SharedRidge`, saved-only metrics and measured costs |

## Checks Run

| Command | Working directory / setup | Result / evidence | Run time or revision |
| --- | --- | --- | --- |
| `python -m unittest discover -s benchmark/nograph_baseline/tests` | repo root, `job-sdf-baseline` | 94 tests OK, 1 skipped (sklearn absent); `evidence/self-tests.log` | 2026-10-07, revision `a0fdab4` |
| `python -m unittest ... -k minimal_dependency` | repo root | OK; `evidence/test-2.5-minimal-dependency.log` | 2026-10-07 |
| `python -m unittest ... -k FailureAndInterruption` | repo root | OK (SIGINT/SIGTERM/SIGKILL, collision, malformed source); `evidence/test-2.6-failure-interruption.log` | 2026-10-07 |
| `python -m unittest ... -k CheckCommand` | repo root | OK; `evidence/test-2.4-2.7-checks.log` | 2026-10-07 |
| Parquet/environment probe | repo root | Exits 0; records interpreter/versions and reads both demand tables; `evidence/environment-check.txt` | 2026-10-07 |
| `run --data-name r0 … --run-id p01-r0-sharedridge-001` | repo root, inputs `dataset/demand/r0.parquet`, `dataset/graph/r0.parquet` | `success`; 72 manifest files; λ=1e-4, `NaiveRef`/`NaiveRef6`=`LastValue`; `evidence/run-3.1-r0-primary.log` | 2026-10-07 |
| `run --data-name r0 … --run-id p01-r0-sharedridge-repeat-001` | fresh directory, identical conditions | `success`; identical identity/selection records; `evidence/run-3.2-r0-repeat.log` | 2026-10-07 |
| `recompute` (r0 primary and repeat) | saved artifacts only | both `ok`, max normalized difference 0.0; `evidence/check-3.3-r0-recompute-*.log` | 2026-10-07 |
| `compare` (r0 primary vs repeat) | saved artifacts only | `ok`; max prediction absolute difference 0.0, max MAE relative difference 0.0; `evidence/check-3.3-r0-compare.log` | 2026-10-07 |
| `align-v2` (r0) | vs `research/runs/phase1-20261006-v2-01/naive-baselines.log` | `ok`; 409 fields, 0 discrepancies; reference unchanged; `evidence/check-3.4-r0-align-v2.log` | 2026-10-07 |
| `run --data-name region … --run-id p01-region-sharedridge-001` | repo root, region inputs | `success`; 72 manifest files; λ=1e-4, `NaiveRef`/`NaiveRef6`=`LastValue`; `evidence/run-3.5-region-primary.log` | 2026-10-07 |
| `run --data-name region … --run-id p01-region-sharedridge-repeat-001` | fresh directory, identical conditions | `success`; identical identity/selection records; `evidence/run-3.6-region-repeat.log` | 2026-10-07 |
| `recompute` (region primary and repeat) | saved artifacts only | both `ok`, max normalized difference 2.43e-16; `evidence/check-3.7-region-recompute-*.log` | 2026-10-07 |
| `compare` (region primary vs repeat) | saved artifacts only | `ok`; max prediction absolute difference 0.0, max MAE relative difference 0.0; `evidence/check-3.7-region-compare.log` | 2026-10-07 |
| `align-v2` (region) | vs the sealed v2 log | `ok`; 409 fields, 0 discrepancies; reference unchanged; `evidence/check-3.8-region-align-v2.log` | 2026-10-07 |

Historical note: an earlier implementation revision (before the two fixes in
`implementation.md` §5) produced the removed r0 directories. No rejected result
is presented as current; the run IDs above refer to the corrected runs only.

### Scope check (task 4.3)

`git status --porcelain` at 2026-10-07T16:42+08:00 contains exactly:
`M README.md`, `M openspec/changes/add-nograph-baseline-ridge/tasks.md`,
new `benchmark/nograph_baseline/`, new change `evidence/` and `implementation.md`,
and 12 new `research/runs/p01-*` directories. `benchmark/graph_method`,
`research/phases`, `research/roadmap.md`, `research/state.md`,
`research/decisions.md`, `research/archives`, `experiments_archive`,
`DELEGATION.md`, `openspec/specs` and `openspec/config.yaml` all report zero
changes. No run writer or background job is active. Sealing, packaging, commits,
pushes, archive-index updates and research acceptance remain pending outside this
change.

## Verification Reminders

- **Region saved-run recomputation is not bit-exact.** `p01-region-recompute-*`
  reports a normalized maximum difference of 2.43e-16, confined to
  `TrainMean27` fields. Cause: the sealed v2 arithmetic computes `TrainMean27`
  metrics from a `numpy.broadcast_to` view, whose `astype` yields a
  non-contiguous buffer; saving/loading materializes a contiguous array and
  changes pairwise-summation grouping by one ULP. This is below the declared
  `1e-12` diagnostic tolerance. Confirm by reading
  `research/runs/p01-region-recompute-primary-001/report.json`
  (`max_difference_path`) and comparing with
  `research/runs/p01-region-sharedridge-001/metrics.json`.
- **Optional sklearn backend is unverified at runtime.** scikit-learn is not
  installed in `job-sdf-baseline`, so
  `tests/test_ridge.py::OptionalSklearnTests` is skipped and no formal run used
  `--ridge-backend sklearn`. The code path is lazy-imported and its
  `alpha = lambda*M` metadata assertions are covered indirectly for the NumPy
  backend.
- **Selection-vs-report consistency is a fragile invariant.** Two apply-time
  defects (33-month normalization, standardized validation targets) were fixed
  and are now covered by
  `test_selected_candidate_scores_match_reported_validation_metrics` and
  `test_candidate_scores_use_original_unit_validation_targets`. Re-run the suite
  after any change to `ridge.fit_candidates`, `TrainingStats`, or
  `metrics.split_report`.
- **Interruption tests rely on an internal hook.**
  `NOGRAPH_BASELINE_TEST_STAGE_DELAY_SECONDS` must stay inert by default; if it
  is removed, `FailureAndInterruptionTests.test_sigterm_*`/`test_sigkill_*` lose
  their deterministic window.
- **Coverage evidence is mandatory for formal runs.** A missing graph file
  raises `CoverageError`; the verifier should confirm no run silently treated all
  nodes as isolated. Formal runs recorded coverage from
  `dataset/graph/{r0,region}.parquet` with the source hashes listed in
  `implementation.md` §3.
- **`research/runs/` is unsealed and unbacked-up.** `.gitignore` does not exclude
  it, but presence on disk is not Git inclusion or backup. Do not treat the
  `success` status as archival.
- **Apply did not create `verification.md` and did not set a verdict.** Any
  `PASS`/`FAIL`, residual-finding or acceptance decision belongs to
  `openspec-e13-verify-change` and research-side acceptance, not here.
- Unresolved planning or environment blockers: none identified.
