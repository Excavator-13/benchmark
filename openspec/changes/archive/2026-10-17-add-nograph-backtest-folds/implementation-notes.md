# Implementation Notes

- Change: `add-nograph-backtest-folds`
- Schema: `spec-driven`
- Store: local repo (`/Users/watuji/da_chuang/repos/benchmark/openspec`; `openspec store list` has no registered stores)
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark`
- Updated: 2026-10-17T11:55:44+08:00
- Implementation revision: `4dbc1e785a772838d8674bd187e1b353d771ee4f`, dirty worktree (documented above); no commit, push, seal or restore action was performed.
- Progress: 25/25 tasks complete (apply session); independent verification not performed here.

## Implementation Map

| Task / requirement / scenario | Code and tests | Decisions / context |
| --- | --- | --- |
| 1.1 pre-change main-split contract | `scratch/prechange-contract/capture_contract.py`; stored baseline at `scratch/prechange-contract/baseline/` (gitignored) | Captured before editing computation code with deterministic r0/region/r2 fixtures (8/8-node r0+region, 3x2 r2 grid, seed 0). Compares file set, JSON field paths, NPZ keys/dtypes/shapes, Parquet columns/dtypes/values, predictions, selection, metrics. Natural-variation value exclusions are encoded in `VALUE_EXCLUSIONS` (run IDs, timestamps, Git fields, command/launcher/runs paths, demand/graph paths, source capture, coverage source path, timings/peak memory); excluded fields still have to exist. |
| 2.1 immutable main/A/B split definitions | `protocol.SplitDefinition`, `MAIN_SPLIT`, `FOLD_A`, `FOLD_B`, `SPLIT_DEFINITIONS`, `resolve_split`, `fold_names`; `tests/test_folds.py::FoldDefinitionTests` | One frozen description drives starts, fitting months, split naming, method order and mask names. Defaults and `protocol.SPLITS`/`OMITTED_STARTS` are unchanged. |
| 2.2 code validation, roles and months | `protocol.validate_split_definition`, `validate_split_assertions(definition)`, `build_window_metadata(definition)`, `_EXPECTED_SPLITS`; `FoldDefinitionTests` | Exact starts, fitting count, omitted reason codes, outside-fold starts and target unions are re-derived and compared to fixed values. Every start 0..27 must have exactly one role. Historical targets remain legal as later inputs. Main `windows.json` keeps its original schema (no fold/role fields). |
| 2.3 `--fold {A,B}` CLI/spec/worker channel | `cli.build_parser` run `--fold`, `runner.RunSpec.fold`, `RunSpec.to_dict`; `FoldCliAndSpecTests`, `FoldRunArtifactTests` | `None` resolves to main and is omitted from `config.json` spec, so main serialization adds no empty fold field. Unknown explicit folds fail in `execute_run` before the run directory is reserved (argparse also rejects them). The worker passes the JSON spec unchanged. |
| 3.1 unique fitting-month statistics | `ridge.compute_training_stats(..., definition=...)`, `TrainingStats.fitting_month_count`/`train_mean_method`; `FoldFittingStatisticsTests` | Statistics use `MONTHS[:fitting_month_count]` once (18/21/27), ddof=0, constant effective std 1; activity uses the same range. `train_mean_float32` keeps the existing float32 arithmetic; `train_mean27_float32` remains an alias for the main compatibility path. |
| 3.2 dynamic naive methods and frozen means | `baselines.train_mean(signal, month_count)`, `naive_predictions(..., train_mean_method=...)`, `select_references(order=..., ref6_candidates=...)`; `FoldNaiveAndRidgeTests` | Fold method order is Zero, LastValue, WindowMean6, TrainMean18/21, SeasonalNaive12; NaiveRef6 excludes SeasonalNaive12 and ties use protocol table order. `train_mean27()` remains the default wrapper. |
| 3.3 fold design, M and lambda selection | `runner.execute_run`, `protocol.expected_train_sample_count(node_count, definition)`; `FoldNaiveAndRidgeTests`, `FoldRunArtifactTests` | M is the actual training-window count times N (A 10*N, B 13*N); `alpha=lambda*M`; all five lambdas record original-unit validation MSE/MAE; exact validation MSE ties select the larger lambda. |
| 3.4 eval built only after selection freezes | `runner.execute_run` (validation design/naive/Ridge selection first, then `_standardized_inputs` + eval targets/predictions), `_selection_payload`; `FoldInformationIsolationTests` | Changing only fold eval targets leaves `selection.json`, candidate parameters, validation predictions and references byte-identical. Changing all post-cutoff values leaves statistics, frozen means, masks, training design and every candidate W/b unchanged (validation-driven selection may then change, as allowed). |
| 4.1 fold metadata and selection record | `runner._selection_payload`, config/provenance/windows/metrics writes; `FoldRunArtifactTests` | Fold payload appears consistently in `config.json` (spec + fold block), `provenance.json`, `metrics.json` and `selection.json`; `windows.json` lists all 28 roles/reasons. Selection adds fitting months/count, TrainMean name, five naive MSEs, both reference reasons, full Ridge candidate table and `test_labels_used_for_selection=false`. Main keeps the historical schema. |
| 4.2 fitted mean and fold masks | `runner._save_train_mean`, `runner._save_masks`, `metrics.constant_group_masks(scope=...)`; `FoldRunArtifactTests` | Fold writes `models/TrainMean18.npz`/`TrainMean21.npz` with `train_mean<count>` and `train_observation_month_count`; no `TrainMean27`/`train27` name is reused. Masks are `constant_fit18/21`, `nonzero_activity_fit18/21`, `activity_fit18/21_{inactive,low,medium,high}` plus the unchanged neighbor mask. Arrays load with `allow_pickle=False` and are node-identity aligned. |
| 4.3 fold metrics and gains | `metrics.split_report(group_names=..., inactive_group_name=...)`, `metrics.baseline_relative_comparison(activity_groups=...)`; `FoldRunArtifactTests` | Validation/eval only; fold-prefixed activity groups, constant groups, counts, error contributions, negative ratios, equal-weight MAE and eval gains against both frozen references; empty groups and zero references keep their existing null/unavailable semantics. |
| 4.4 node errors and scoped audit | `metrics.node_error_table(train_mean_column=..., activity/group/constant columns)`, `data.build_fold_audit`; `FoldRunArtifactTests` | Fold node-errors add `train_mean18/21`, `activity_fit18/21`, `activity_group_fit18/21`, `constant_fit18/21`; main columns are unchanged. Fold audit puts fit18/fit21 statistics at the top level and every retained 27-month value (including nested per-context) under `main_protocol_diagnostics` with 27-month scope and descriptive-only markers; the signal fixture has nodes whose fold and main 27-month status differ. |
| 4.5 predictions/gold/summary/measurements | `runner._save_predictions`, gold writes, `runner._summary_text`, measurements stage description; `FoldRunArtifactTests` | Fold saves `predictions/<method>/{validation,eval}.npy` and `gold/{validation,eval}.npy` only, shapes `[W,N,3]`; no test split/file and no 2023-07..12 computation. Summary/measurements state the fold, fitting scope, TrainMean name, validation/eval naming and `development_backtest` role. |
| 4.6 purposes and evidence role | `runner._validate_purpose`, `artifacts.default_runs_root`; `FoldRunArtifactTests` | Only `formal`/`development` remain. Formal fold output defaults to `research/runs` and records `evidence_role=development_backtest`; development stays in ignored scratch and is rejected inside the formal namespace, including a symlink alias. No formal fold run was started. |
| 5.1 saved-split identity resolver | `checks.resolve_saved_split`, `_validate_fold_windows`, `_validate_main_windows`, `_validate_saved_methods/_mean/_masks`, `_validate_fold_selection`; `FoldCheckTests` | Config/provenance/metrics/selection/windows fold labels must all exist, agree and match the fixed definition; fitting count, windows, roles/reasons, methods, mean key, mask keys and selection fields are cross-checked. A historical main run resolves only with a valid main window record; eval evidence without fold metadata, unknown labels, conflicts or missing fields fail instead of falling back. |
| 5.2 saved-only fold recompute | `checks.command_recompute`, `_recompute_consumed_inputs`, `_compare_node_error_tables`; `FoldCheckTests` | Recompute reads only saved artifacts, derives validation/eval, fold group names, mean path and node columns from the resolved identity, and reproduces metrics/gains/node errors. Test mocks `data.load_demand` and Ridge fitting to raise; the report records fold, eval splits, mean artifact and consumed mask keys. Main behavior is preserved. |
| 5.3 fold-aware compare | `checks.command_compare`; `FoldCheckTests` | Explicit fold identity, equal evaluation splits and full method-set equality (no intersection masking) are required in addition to dataset, demand content, seed, source/protocol/environment/coverage/selection checks. Same-fold/same-seed repetition returns `ok` with zero prediction difference and relative MAE <= 1e-6. |
| 5.4 compare negative cases | `FoldCheckTests.test_compare_rejects_fold_dataset_content_and_seed_mismatches`, `test_compare_does_not_mask_missing_methods_with_an_intersection` | A-vs-B, main-vs-fold, different dataset, same dataset with different demand content (out-of-fold month changed; predictions asserted identical), and different seed all fail decisively. A removed method report makes `methods_equal` false instead of being hidden by an intersection. |
| 5.5 align-v2 fold rejection | `checks.command_align_v2`; `FoldCheckTests.test_align_v2_rejects_every_fold` | The run fold is resolved first; A/B raise a fold-specific "no fold records" failure before the reference is consulted. A fabricated fold reference cannot bypass it. Inputs (run tree and reference bytes) are unchanged and no eval→test mapping is produced. Main success/limited behavior is covered by the existing suite. |
| 5.6 corrupt/conflicting fold evidence | `FoldCheckTests.test_corrupt_fold_masks_node_columns_and_collision`, `test_inconsistent_fold_evidence_fails_without_main_fallback`, `test_previous_report_alias_is_single_exclusive_json` | Missing mask keys, missing arrays, corrupted node group columns, unknown/conflicting labels, wrong fitting counts/reasons/TrainMean and missing fold metadata produce one failure or mismatch report as appropriate. Report collision and report-inside-input are rejected; input trees are byte-identical before/after; legacy `--run-id`/`--runs-root` alias still writes one exclusive JSON. |
| 6.1 A/B × r0/region/r2 end-to-end | `FoldEndToEndCliTests` | Six public-CLI development runs (`--runs-root` temp) finish `success`, write the full fold contract, canonical node keys, fit18/fit21 groups, validation/eval names, and never write under `research/runs`. |
| 6.2 main-split regression | `scratch/prechange-contract/capture_contract.py compare`, `FoldMainRegressionTests`; existing 238-test suite | No-fold r0/region/r2 runs reproduce the pre-change file set, JSON fields, NPZ keys/dtypes, Parquet columns and prediction/selection/metric values with **0 differences**. Main still uses `TrainMean27`/`train27`/`validation`+`test` and has no fold fields; saved main runs remain readable by recompute/compare/align-v2. |
| 6.3 full CPU suite | `python -m unittest discover -s benchmark/nograph_baseline/tests -v` | 283 tests pass, 2 skipped (optional scikit-learn backend absent). No GPU/graph fixture, no new required dependency, no formal fold run. |
| 7.1 entry documentation | `README.md` §4.5, `research/phases/P01/execution-guide.md` §7 | Documents `--fold A|B`, both fitting scopes, validation/eval naming, formal vs development/evidence role, recompute/compare/align-v2 behavior, the separate authorization for formal fold runs, and unchanged main entry. Commands match `run --help` (`--fold {A,B}`). |

## Checks Run

| Command | Working directory / setup | Result / evidence | Run time or revision |
| --- | --- | --- | --- |
| `python -m unittest discover -s benchmark/nograph_baseline/tests -v` | repo root; `job-sdf-baseline` conda env (Python 3.11.17, NumPy 1.26.4, pandas 2.2.3, PyArrow 17.0.0), before any code edit | 238 tests OK, 2 skipped (pre-change baseline) | 2026-10-17, `4dbc1e7` working tree |
| `python scratch/prechange-contract/capture_contract.py capture scratch/prechange-contract/baseline` | repo root; same env; before editing computation code | Captured r0/region/r2 main-split fixture runs and `contract.json`; baseline at `scratch/prechange-contract/baseline/` (ignored) | pre-change |
| `python scratch/prechange-contract/capture_contract.py compare scratch/prechange-contract/baseline` | repo root; same env; after all implementation edits | `0 difference(s)` for the three datasets (file set, JSON fields, NPZ keys/dtypes, Parquet columns, predictions, selection, metrics) | post-change, `4dbc1e7` + dirty tree |
| `python -m unittest discover -s benchmark/nograph_baseline/tests -p 'test_folds.py'` | repo root; same env; after the V-001..V-004 repairs | **49 tests OK** | repair session |
| Full discovery under a guard that raises on formal A/B `execute_run` | repo root; same env; guard wraps `runner.execute_run` | **287 tests OK, skipped=2**; observed fold executions only `A/development` and `B/development`; no formal A/B execution | repair session, 51.9 s |
| `python -m unittest discover -s benchmark/nograph_baseline/tests -v` | repo root; same env; after implementation and docs (pre-repair) | 283 tests OK, skipped=2; log `/tmp/fold-final-tests.log`; skips are the two optional scikit-learn tests | pre-repair, 53.3 s |
| `python -m benchmark.nograph_baseline run --help` | repo root; same env | Shows `--fold {A,B}` with the documented help text; other stable flags unchanged | final |
| `openspec validate add-nograph-backtest-folds` | repo root | `Change 'add-nograph-backtest-folds' is valid` | final |
| Manual smoke script (runner + `checks.command_recompute/compare/align_v2`) on temporary r0 fixtures | repo root; same env | Main/A/B runs succeeded; main and fold recompute/compare returned `ok`; A-vs-B and main-vs-fold returned `mismatch`; fold `align-v2` returned `failed` with the no-fold-records message | during apply; superseded by `test_folds.py` |

The pre-change baseline and the comparison script live under the intentionally
ignored `scratch/` tree; they are implementation evidence for this apply, not a
committed research record. The fixture demand/graph files, reports and run
directories all came from temporary directories.

## Repair Changes (fix workflow)

- V-001: added `checks._validate_fold_mask_semantics` (activity is finite,
  within [0,1], an integer multiple of 1/fitting_month_count, and each boolean
  activity mask exactly matches the protocol groups derived from it; groups
  partition every node; mask dtypes/shapes are valid) plus fixed normalization
  checks in `_validate_fold_selection` (`ddof=0`, `constant_node_std=1.0`,
  applied to inputs and targets, fold activity scope). New tests in
  `test_folds.py` cover the reported activity/group contradiction, the
  ddof=1 contradiction, legal 0/1/3/2/3/1 boundaries, overlapping/missing
  groups, wrong boundary placement, non-finite/out-of-range/integer activity,
  wrong mask dtypes, and a nonzero CLI exit.
- V-002: `command_compare` now derives
  `_compare_consumed_inputs(identity)` after resolving each run, so
  `windows.json`, `provenance.json` and `models/TrainMean18/21.npz` (or the main
  `TrainMean27.npz`) are hashed in the report. Tests assert both sides include
  those files with their exact SHA256; a consumed provenance contradiction
  yields one safe failure report without mutating either input.
- V-003: `command_align_v2` reads the run's metrics/windows, resolves and
  rejects A/B before checking reference existence or parsing it. Tests cover
  A/B with valid, fabricated, missing and unparseable references; all report
  the fold/no-fold-records reason, and missing/malformed reference errors no
  longer mask it.
- V-004: removed the temp-root formal fold execution from `test_folds.py`;
  `test_fold_purpose_rules_and_no_formal_start` now checks formal root
  resolution, `RunSpec` serialization, purpose validation and the fold payload's
  `evidence_role` without calling `execute_run`. The invalid-fold test also uses
  `purpose="development"`. Full discovery was re-run under a guard that raises on
  any formal A/B `execute_run`: 287 tests OK, 2 optional sklearn skips, no
  formal fold execution observed.

## Verification Reminders

- No formal fold run was started and nothing under `research/runs/` was written
  or changed. Every executable fold run in the suite uses a temporary fixture
  with `--purpose development`; formal fold capability is covered only by
  static root/spec/serialization/purpose assertions. Formal fold
  execution/saving still needs separate user authorization.
- The pre-change contract baseline is gitignored under
  `scratch/prechange-contract/`. It cannot be recaptured meaningfully after this
  change; use the stored runs plus the documented exclusion list when auditing
  main-split preservation.
- Fold identity validation is intentionally strict in `checks.py`: any fold
  block/eval trace requires complete, consistent metadata from all writers.
  Historical main runs keep the previous mismatch semantics for a deleted
  method report (rather than becoming a parse failure); verify both paths when
  reviewing the resolver.
- `align-v2` rejects a fold run before inspecting the supplied reference, so a
  malformed/missing reference on a fold input still yields the fold-specific
  failure rather than a reference error. This is intentional.
- Fold `audit.json` retains the complete 27-month/per-context and 36-month
  diagnostics inside `main_protocol_diagnostics` (descriptive only). They must
  not be consumed as fold fitting/grouping/selection inputs; fold statistics are
  `fit18`/`fit21`, and node-errors/metrics use only the saved fold masks.
- Numeric evidence comes from small fixtures (6-8 nodes, 3x2 r2). Cross-fold
  scientific interpretation and real-data cost measurements are outside this
  change; the T007 guide owns the authorized formal runs.
- Optional scikit-learn is not installed in this environment, so the two
  `OptionalSklearnTests` were skipped. Fold runs share the candidate/Ridge
  payload path, but the sklearn fold path was not exercised here.
- `RunSpec.to_dict()` omits `fold` only when it is `None`; explicitly recorded
  `main` is not produced by the CLI. Keep main config/windows free of fold/eval
  fields when touching serialization.
- Main node-errors Parquet columns are unchanged; fold-only extra columns must
  not leak into main outputs. Measurement timing values and timestamps vary
  naturally and are excluded from the pre-change value comparison.
- No commit, push, seal, restore or research-record update was performed. The
  pre-existing dirty research/DELEGATION files were not edited by this apply
  beyond the two authorized entry-document sections (README §4.5 and execution
  guide §7).
