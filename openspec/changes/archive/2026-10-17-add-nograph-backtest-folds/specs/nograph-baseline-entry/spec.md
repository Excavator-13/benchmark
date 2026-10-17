## MODIFIED Requirements

### Requirement: Independent CPU entry follows the research protocol
The entry SHALL support `r0/count`, `region/count` and `r2/count` through a stable documented command or module interface. It SHALL use sections 3-6 and 8 of `research/phases/P01/protocol.md` (`P1-count-L6-H3-v3`) as the sole normative scientific definition. It SHALL be importable and runnable with only NumPy, pandas and PyArrow as installed third-party dependencies. It SHALL NOT import modules under `benchmark/graph_method`, require PyTorch/PyG/DGL/CUDA dependencies, or require generated graph data for forecasting. Optional scikit-learn support SHALL NOT be required by the default execution path. CPU automated tests SHALL run without GPU or repository graph data. Adding r2 support SHALL preserve r0/region scientific behavior and saved-result formats without changing the scientific protocol version or record policy `P01-records-v2`.


The entry SHALL expose `--fold A|B` for all three datasets, using sections 2-5 of `research/phases/P01/t007-backtest-guide.md` for exact fold enumeration and artifacts. Omission SHALL preserve main-split behavior and existing output field/file schemas. Invalid explicit fold selection through the CLI or programmatic interface SHALL fail before fitting or run-directory reservation. Scientific version and record policy SHALL remain unchanged.

#### Scenario: Minimal dependency environment
- **WHEN** only NumPy, pandas and PyArrow are installed in a Python environment
- **THEN** the public entry imports, displays help and executes all five naive methods and shared Ridge on valid fixture data for each supported dataset without importing graph or GPU packages

#### Scenario: Supported r2 count request
- **WHEN** a user requests r2/count with valid demand and coverage evidence
- **THEN** the same public entry accepts it and applies the fixed protocol, validation-only selection, common activity/neighbor masks and complete saved-result contract

#### Scenario: Unsupported scientific configuration
- **WHEN** a user requests a dataset outside r0/region/r2, rate mode or a split outside the default main split and fixed A/B folds
- **THEN** the entry rejects it with the supported configuration before fitting instead of silently running a different protocol

#### Scenario: Explicit and omitted folds
- **WHEN** a supported count dataset is run with A, B or no fold selection
- **THEN** the entry selects the exact requested fold or the unchanged default main split using the same CPU dependency environment


### Requirement: Demand identity and observations are validated
The entry SHALL read `dataset/demand/r0.parquet`, `dataset/demand/region.parquet` or `dataset/demand/r2.parquet`, sort ascending by `(r0_id, skill_id)`, `(region_id, skill_id)` or `(r2_id, skill_id)` respectively, and retain the keys with every saved prediction identity. It SHALL require a nonempty set of unique finite integer node keys, exactly 36 continuous monthly columns from 2021-01 through 2023-12, and finite nonnegative counts. It SHALL audit node/skill/context counts, context-skill grid completeness, monthly nonzero fractions, training-27-month and full-36-month all-zero fractions, constant nodes, value ranges and per-context results. Full-period descriptive audits SHALL NOT affect grouping, fitting or selection.


For fold runs, every retained 27-month audit value SHALL be explicitly identified as a main-protocol descriptive diagnostic over 2021-01..2023-03, including nested per-context values. Fold statistics SHALL use a distinct fit18/fit21 namespace. Main-protocol and full-period diagnostics SHALL NOT supply fold fitting, grouping or selection.

#### Scenario: Valid data arrives out of order
- **WHEN** valid r0, region or r2 rows are shuffled
- **THEN** canonical keys, aligned signals, labels and predictions use the same ascending key order for that dataset

#### Scenario: Source is invalid
- **WHEN** keys are duplicated or invalid, the dataset's context key is missing, monthly columns are missing or extra, or counts are negative or nonfinite
- **THEN** execution fails before fitting with the dataset and validation failure recorded

#### Scenario: Multiple r2 contexts share skill IDs
- **WHEN** r2 demand contains the same skill in multiple r2 contexts and a context-skill combination is absent
- **THEN** identities remain distinct by r2_id, the grid audit reports the missing combination and actual counts, and no merging or silent filling changes the prediction population

#### Scenario: Distinct audit scopes
- **WHEN** a fold node has different activity or constant status in its fitting period and the first 27 months
- **THEN** both audit scopes are labeled unambiguously and fold reports use only the fold-fitting masks


### Requirement: Fixed windows isolate target months and preserve rolling origins
The entry SHALL construct all 28 unit-stride windows with L=6 and H=3. Without fold selection it SHALL use training starts 0..18, validation start 21 and test starts 24..27, and omit exactly starts 19, 20, 22 and 23. For that main split, target-month sets SHALL be pairwise disjoint across splits: training 2021-07..2023-03, validation 2023-04..2023-06 and test 2023-07..2023-12. It SHALL save all starts, omissions, input/target months and forecast origins. Each naive and Ridge prediction SHALL be independent of hidden state from other windows. Later test origins SHALL use then-observed true history with model parameters and normalization frozen after training.


Fold A SHALL use fitting observations 2021-01..2022-06 (18 months), training starts 0..9 with target union 2021-07..2022-06, validation start 12 targeting 2022-07..09, and eval start 15 targeting 2022-10..12. Starts 10,11 SHALL be omitted at the train/validation boundary; 13,14 at the validation/eval boundary; 16,17 for overlap with eval targets; 18..27 SHALL be outside_fold.

Fold B SHALL use fitting observations 2021-01..2022-09 (21 months), training starts 0..12 with target union 2021-07..2022-09, validation start 15 targeting 2022-10..12, and eval start 18 targeting 2023-01..03. Starts 13,14 SHALL be omitted at the train/validation boundary; 16,17 at the validation/eval boundary; 19,20 for overlap with eval targets; 21..27 SHALL be outside_fold.

Each fold SHALL validate exact start sets, fitting range, omitted starts/reasons and pairwise disjoint train/validation/eval target-month sets in code. Every start 0..27 SHALL have exactly one saved role: train, validation, eval, omitted or outside_fold; input/target months and forecast origin SHALL be saved for every role. Historical targets SHALL be allowed as later observed inputs. Fold prediction/evaluation SHALL NOT compute main-test results for 2023-07..12 or call eval test.

#### Scenario: Protocol split is constructed
- **WHEN** 36 monthly observations are windowed with L=6 and H=3 without fold selection
- **THEN** there are 19 training, 1 validation and 4 test windows, exactly 4 omitted windows, and no target month belongs to multiple splits

#### Scenario: Second test origin uses known history
- **WHEN** predicting the test window starting at 25
- **THEN** its input is 2023-02..2023-07 and its targets are 2023-08..2023-10, with July's true observation available as input and no refitting on validation or test observations

#### Scenario: Fold A enumeration
- **WHEN** A is constructed
- **THEN** its 10 train windows, validation input 2022-01..06, eval input 2022-04..09, six omitted starts and ten outside-fold starts match the fixed definition with disjoint split targets

#### Scenario: Fold B enumeration
- **WHEN** B is constructed
- **THEN** its 13 train windows, validation input 2022-04..09, eval input 2022-07..12, six omitted starts and seven outside-fold starts match the fixed definition with disjoint split targets

#### Scenario: Invalid fold structure
- **WHEN** constructed fold data have an altered start, fitting range, wrong omission reason, missing role or overlapping split targets
- **THEN** code validation fails rather than relying on CLI conventions


### Requirement: All naive methods and frozen references are reported
For the default main split the entry SHALL report Zero, LastValue, WindowMean6, TrainMean27 and SeasonalNaive12. Zero SHALL predict zero; LastValue SHALL repeat the last input value; WindowMean6 SHALL repeat the mean of the six inputs; TrainMean27 SHALL repeat the frozen per-node mean over 2021-01..2023-03; SeasonalNaive12 SHALL use the preceding year's same month for each target. It SHALL select `NaiveRef` from all five using validation MSE, breaking exact ties in this listed order, and freeze the choice before test evaluation. It SHALL select `NaiveRef6` identically from the first four, and label SeasonalNaive12 and any reference using it as extra-history references. TrainMean27 SHALL be identified as frozen training statistics, not new prediction-time history. Test rankings SHALL NOT change reference selection.


A/B SHALL substitute `TrainMean18`/`TrainMean21` in the same five-method order, using the frozen per-node mean over the fold fitting observations. Predictions, parameters and metadata SHALL name the method with the fitting month count. NaiveRef SHALL use all five fold validation MSEs; NaiveRef6 SHALL use the first four with the substituted name, excluding SeasonalNaive12. Both SHALL freeze before eval with the existing exact-tie table order. Complete validation scores and both selection reasons SHALL be saved; eval rankings SHALL NOT influence selection.

#### Scenario: Validation MSE ties
- **WHEN** two naive candidates have equal validation MSE
- **THEN** the earlier method in the protocol table is selected regardless of their validation MAE or test results, and the full score table and tie decision are saved

#### Scenario: Seasonal prediction uses extra history
- **WHEN** predicting targets 2023-04, 2023-05 and 2023-06
- **THEN** SeasonalNaive12 predicts values from 2022-04, 2022-05 and 2022-06 respectively, is marked as extra history, and is excluded from NaiveRef6

#### Scenario: Fold reference ties and naming
- **WHEN** fold validation scores tie while eval favors another candidate
- **THEN** table order selects the validation winner, its reason is saved, TrainMean is named for its actual 18/21 months and eval does not change either reference


### Requirement: Normalization counts training observation months exactly once
For the default main split the entry SHALL compute each node's mean and ddof=0 standard deviation from precisely the 27 observations 2021-01..2023-03, with each month counted once and constant-node standard deviation replaced by 1. It SHALL freeze these statistics and apply the same node statistics to both inputs and targets. It SHALL NOT fit statistics from training targets alone, duplicated values in overlapping windows, or validation/test months. TrainMean27 and activity grouping SHALL use the same unique training observation range.


Each fold SHALL independently compute mean, ddof=0 standard deviation, constant-node mask, frozen mean and activity from exactly its unique fitting observations, including the earliest six input months: first 18 months for A and first 21 for B. It SHALL freeze and apply the same node mean/effective-standard-deviation pair to inputs and targets, replacing constant effective standard deviation with 1. Fold validation/eval observations and main-protocol 27-month masks SHALL NOT enter these statistics.

#### Scenario: Overlapping training windows have unequal month multiplicities
- **WHEN** a node's training series produces different statistics if flattened across overlapping windows
- **THEN** the saved normalization equals the mean and ddof=0 standard deviation of its unique 27 observations and differs from the overlap-weighted estimate

#### Scenario: Future values change
- **WHEN** values after 2023-03 change while the first 27 months stay fixed
- **THEN** normalization, frozen training means, activity masks and training-only fitted candidate parameters remain unchanged

#### Scenario: Constant training node
- **WHEN** a node has zero variance in its 27 training observations
- **THEN** its stored effective standard deviation is 1 and standardized inputs and targets remain finite

#### Scenario: Fold cutoff and unique months
- **WHEN** a fold fixture has constant nodes and overlap-weighted statistics differ from unique-month statistics
- **THEN** saved statistics match the unique 18/21-month oracle with ddof=0 and constant effective standard deviation 1

#### Scenario: Post-fitting values change
- **WHEN** all observations after a fold fitting cutoff change while fitting observations stay fixed
- **THEN** normalization, frozen mean, activity/constant masks, training design and every training-only fitted candidate parameter stay unchanged, even if validation scores or selections subsequently change


### Requirement: Ridge parameters are shared and selected exclusively on validation
The entry SHALL report the model as `SharedRidge` and fit one 6x3 weight matrix and three unregularized biases shared across every node and the selected definition's training windows (19 by default, 10 for A, 13 for B). It SHALL minimize `(1/M) * sum_m ||x_m W + b - y_m||_2^2 + lambda * ||W||_F^2`, where M equals the selected training-window count times the node count, using standardized training samples. It SHALL fit candidates at lambda `1e-4, 1e-3, 1e-2, 1e-1, 1`, inverse-transform validation predictions and select only by validation original-unit MSE, breaking exact ties toward the larger lambda. It SHALL record each candidate's validation MSE/MAE, sample count, objective, solver/backend, normalization and selection decision. A sum-loss backend using alpha SHALL use and record `alpha=lambda*M`. Test targets SHALL NOT be supplied to fitting or selection; selection SHALL be finalized before test evaluation. It SHALL retain raw inverse-transformed outputs as primary; optional nonnegative-clipped outputs SHALL be separately labeled and SHALL NOT select lambda.


For folds, candidate validation scores SHALL use only the fold validation targets and frozen fold statistics. Eval targets SHALL NOT enter fitting or selection, which SHALL finish before eval evaluation. The complete lambda score table SHALL record the validation-MSE and larger-lambda tie reasons. Fold selection SHALL retain `test_labels_used_for_selection=false` as the existing explicit non-use flag.

#### Scenario: Test labels cannot affect selection
- **WHEN** the selector is invoked without access to test labels and validation MSE favors a candidate different from validation MAE
- **THEN** it selects the validation-MSE winner; subsequently changing test labels does not change candidate parameters, selected lambda or reference identities

#### Scenario: Lambda scores tie
- **WHEN** multiple Ridge candidates have exactly equal validation original-unit MSE
- **THEN** the larger lambda is selected and the recorded selection table explains the tie

#### Scenario: Sum-loss backend is used
- **WHEN** a backend defines its regularization coefficient against an unaveraged residual sum
- **THEN** it receives alpha=lambda*M and saves lambda, alpha and M rather than treating lambda as alpha

#### Scenario: Fold eval labels cannot select
- **WHEN** only fold eval targets change
- **THEN** fitted candidates, validation scores, selected lambda and naive references remain unchanged

#### Scenario: Fold sample count and lambda tie
- **WHEN** A/B validation lambda scores tie
- **THEN** the larger tied lambda wins with a saved reason, M is 10*N/13*N respectively, and a sum-loss backend uses alpha=lambda*M


### Requirement: Metrics use common fixed masks and original units
For the default main split the entry SHALL report validation MSE/MAE and overall test MAE/RMSE, with RMSE equal to the square root of mean squared error over all window-node-horizon elements. It SHALL report per-window, per-horizon, per-context, activity-group and neighbor-group MAE/RMSE with node and evaluated-element counts, negative-prediction ratios, absolute/squared error contributions for activity groups and constant/large-demand diagnostics, and equal-weight activity-group MAE. For the main split the four activity masks SHALL be fixed by the training-27-month nonzero fraction: zero, (0,1/3], (1/3,2/3], (2/3,1]. Training-all-zero nodes SHALL be explicitly reported. Empty groups SHALL have zero counts and explicit unavailable metrics, excluded from equal-weight MAE. All methods SHALL use exactly the same saved masks. The main test aggregation SHALL retain overlapping target-month multiplicities 1,2,3,3,2,1, without treating them as independent samples. Activity/context relative MAE gains SHALL use frozen specified references, with undefined gain when reference MAE is zero.


Fold metrics SHALL expose validation and eval only, each with overall MAE/MSE/RMSE, per-window, per-horizon, per-context, activity-group, constant-node and neighbor/non-neighbor metrics, counts, error contributions, negative-prediction ratios and equal-weight activity-group MAE. Activity SHALL be the fraction of fold fitting observations with demand > 0, using the same four boundaries. Saved group identifiers SHALL carry fit18/fit21 (for example `fit18_inactive`); constant groups SHALL also identify fitting scope. All methods SHALL share these fold masks. Empty groups SHALL retain unavailable metrics and zero counts and be excluded from balanced MAE. Eval gains SHALL compare SharedRidge and separately labeled optional clipped output with validation-frozen NaiveRef/NaiveRef6, overall and in existing activity/context/neighbor/window comparisons, with explicitly undefined gains for zero reference MAE. Fold aggregation notes SHALL describe actual eval windows rather than main-test multiplicities.

#### Scenario: Window RMSE values differ
- **WHEN** test windows have different mean squared errors
- **THEN** overall RMSE is recomputed from all squared errors and is not the arithmetic mean of the window RMSE values

#### Scenario: Activity boundaries and an empty group
- **WHEN** training activities include 0, 1/3 and 2/3 and one group is empty
- **THEN** boundary nodes enter their protocol groups, all methods share those masks, the empty group is marked explicitly and equal-weight MAE averages only nonempty groups

#### Scenario: Fold masks and balanced metrics
- **WHEN** later demand changes a node's main 27-month grouping and a fold group is empty
- **THEN** all fold methods retain fit18/fit21 masks, empty groups are explicit and balanced MAE averages the nonempty fold groups

#### Scenario: Eval grid and zero reference
- **WHEN** a fold report includes a comparison with zero reference MAE
- **THEN** both validation/eval grids are complete, no test split is emitted and the gain is unavailable with a reason


### Requirement: Each run saves recoverable and independently recomputable evidence
Formal model experiments SHALL create fresh exclusive `research/runs/<run_id>/` directories by default and refuse overwriting existing executions. They SHALL record scientific protocol `P1-count-L6-H3-v3` and record policy `P01-records-v2`, resolved configuration and exact command, fixed source/input identities, code commit and relevant execution differences including necessary used untracked source, environment/machine/CPU details, canonical node keys, window identities/splits, predictions and labels, all metrics/masks, selected fitted parameters/preprocessing statistics, complete candidate score/selection records, timings/device and status. Committed runtime source and protocol SHALL be located by fixed commit and repository-relative path without repeated copies; relevant uncommitted execution content SHALL be recoverable from saved patches/files. Unrelated documentation, test and cache changes SHALL NOT be included in execution-source snapshots. Unavailable identity evidence SHALL be explicit and SHALL NOT be invented. Numeric outputs SHALL load without graph libraries or Python-object pickle. Saved predictions/labels/identities/masks SHALL suffice to independently recompute every reported metric and relative comparison without fitting or rereading source data. Losing-candidate full parameters and predictions SHALL be omitted by default and retained only with an explicit option, while every candidate's validation scores and selection reasons remain saved. Failures and interruptions SHALL preserve available evidence, errors and incomplete status, including detectable unfinished state after uncatchable termination. Success SHALL NOT imply scientific acceptance, packaging, Git inclusion or backup completion, and SHALL NOT automatically trigger any of those operations or recovery checks.


For folds both config.json and provenance.json SHALL record fold A/B, fitting observation months/count, train/validation/eval starts, omitted starts with reasons, outside-fold starts, eval target months and `evidence_role=development_backtest`. Fold runs SHALL use only existing formal/development purposes: separately authorized formal output defaults to research/runs; development output remains implementation evidence outside that namespace regardless of evidence_role.

windows.json SHALL describe all 28 roles and their months. selection.json SHALL include normalization/fitting months, TrainMean18/TrainMean21, all five naive validation MSEs, both reference reasons, every Ridge candidate score and selection reason, and `test_labels_used_for_selection=false`. Predictions SHALL use `predictions/<method>/validation.npy` and `predictions/<method>/eval.npy`, with shared `gold/validation.npy` and `gold/eval.npy`; fold test arrays SHALL NOT be written. Saved fold means, statistics and identity-aligned activity/constant/neighbor masks SHALL suffice to recompute all reported metrics, gains and node errors. audit.json or an accompanying fold-audit.json SHALL explicitly scope every main-protocol 27-month diagnostic. node-errors.parquet SHALL include fitting-specific frozen mean, activity, activity group and constant status with canonical keys and validation/eval errors.

#### Scenario: Metrics are independently recomputed
- **WHEN** an evaluator has only a completed run directory and the documented numeric-loading environment
- **THEN** saved predictions, labels, identities and masks reproduce aggregate/window/horizon/context/group metrics and gains without reading source data or invoking training

#### Scenario: Run is interrupted or collides
- **WHEN** execution fails or is interrupted after reserving its directory, or a subsequent invocation requests the same run ID
- **THEN** completed artifacts remain available with failure/interrupted or unfinished status, and the subsequent invocation refuses replacement

#### Scenario: Committed execution sources are reused
- **WHEN** runtime source and protocol match their recorded commit while unrelated records or tests are dirty
- **THEN** their commit/path references locate exact contents without copied source/protocol files or unrelated patches

#### Scenario: Runtime source or protocol is uncommitted
- **WHEN** a used implementation file or protocol has tracked modifications or necessary untracked content
- **THEN** the run saves recoverable relevant changes and actual content identities, including protocol content when uncommitted, and omits unrelated files and caches

#### Scenario: Git identity is unavailable
- **WHEN** execution sources are not in a readable Git repository or Git inspection fails
- **THEN** provenance identifies the limitation and preserves relevant available execution content without claiming a fixed commit or a clean source state

#### Scenario: Candidate retention is reduced by default
- **WHEN** the five Ridge lambdas are evaluated with default retention
- **THEN** all five validation score records and the selection decision remain saved, the selected model/preprocessing and reported predictions remain recoverable, and losing-candidate parameter/prediction files are absent

#### Scenario: Candidate arrays are explicitly requested
- **WHEN** execution enables the documented candidate-retention option
- **THEN** candidate parameter and validation prediction files are saved in addition to the required selected-model evidence without changing fitting, selection or metrics

#### Scenario: Complete fold evidence
- **WHEN** a temporary A or B development fixture finishes
- **THEN** complete metadata, all window roles, selection, validation/eval arrays, masks, grouped metrics and node errors agree on the 18/21-month fitting scope and permit saved-only recomputation

#### Scenario: Fold purposes
- **WHEN** purpose and output destination are resolved for a fold
- **THEN** only formal/development are accepted, formal retains the research/runs default with development_backtest metadata and development retains its formal-namespace rejection, without changing computation


### Requirement: Formal results align with immutable v2 diagnostics
For main-split runs the entry SHALL compare each supported dataset's canonical identity evidence, split metadata, all five naive validation/test metrics, window/horizon/activity results and reference choices against an explicitly supplied immutable v2-format diagnostic reference containing that dataset. `research/runs/phase1-20261006-v2-01/naive-baselines.log` SHALL remain the historical reference for r0 and region; r2 support SHALL NOT add records to or rewrite it. The entry SHALL record the reference hash, compared fields, tolerances and differences. Since the reference log contains counts rather than full node keys, identity alignment SHALL also be checked against the same hashed sources and canonical ordering and SHALL NOT claim that full identities were recovered from the log alone. Any discrepancy SHALL be preserved and explained as a finding; it SHALL NOT rewrite old logs or change the protocol to force agreement. Missing dataset records SHALL fail explicitly; missing source identity SHALL retain the existing limited outcome rather than be claimed as a successful alignment. Temporary r2 fixture references SHALL establish software compatibility only.


align-v2 SHALL reject every fold run with a nonzero result and a compact failure report explaining that the existing v2 reference has no fold records. It SHALL NOT map eval to test, construct a synthetic fold reference, or accept one to bypass rejection.

#### Scenario: Legacy naive value differs
- **WHEN** a new naive metric differs from the v2 reference beyond the declared numerical tolerance
- **THEN** the new run records the expected/actual values and investigation outcome while the original log remains byte-for-byte unchanged

#### Scenario: Independent r2 fixture reference
- **WHEN** align-v2 consumes a saved r2 development fixture and an independently computed v2-format r2 reference with matching demand source identity
- **THEN** it compares identity counts, canonical-source evidence, splits, all five naive results and references with the existing diagnostic tolerance and produces a linked report without rereading source demand/graph data

#### Scenario: Reference contains no r2 records
- **WHEN** align-v2 receives an r2 result and a reference containing only r0/region
- **THEN** it returns nonzero with a failure report naming the missing r2 reference and leaves input results and reference unchanged

#### Scenario: Fold alignment rejection
- **WHEN** align-v2 receives A or B with a main-split reference or a fabricated fold reference
- **THEN** it fails with a fold-specific missing-reference explanation, leaves inputs unchanged and writes only the requested safe failure report


### Requirement: Supported datasets produce complete formal artifacts
Formal scientific evidence SHALL include completed end-to-end model executions for each authorized supported dataset, independent same-seed repetitions and linked metric-recomputation, applicable diagnostic-alignment and measurement evidence. Every completed formal model execution SHALL contain all five naive methods and validation-selected shared Ridge with the preceding identity, selection, grouping and provenance outputs. Checks SHALL use linked reports rather than independent experiment directories. Packaging, commits, pushes, research-record updates and main-spec synchronization SHALL remain outside model/check tasks. A record-format maintenance change SHALL reuse applicable accepted historical formal evidence and validate the changed behavior using temporary CPU fixtures; it SHALL NOT require rerunning accepted scientific experiments merely to change their saved format or relabel fixture evidence as a new scientific result. Adding r2 support SHALL be verified with temporary/development CPU evidence and SHALL NOT require new formal r2 executions or rerunning accepted r0/region experiments to establish software readiness. Formal r2 execution and research acceptance SHALL remain separately authorized research actions.


A/B software readiness SHALL use only temporary CPU fixtures and development smoke runs, covering both folds and r0/region/r2 schemas, same-seed repetition, saved-only recomputation, mismatch rejection, fold alignment rejection and default main-split regression. Implementation/independent verification SHALL NOT initiate formal fold runs, rerun accepted experiments, alter old runs/packages/archives or declare T007 experimentally accepted. README section 4.5 and execution-guide section 7 SHALL document the fold entry, fitting scopes, validation/eval naming, purpose/evidence distinction and checks. Formal fold execution/saving and research acceptance SHALL require separate user authorization. Archived independent verification PASS with a Verification Basis matching current implementation SHALL be implementation-readiness evidence only; research acceptance and delegation wrap-up SHALL remain separate.

#### Scenario: Execute both supported datasets end to end
- **WHEN** the documented CPU entry executes authorized r0/count and region/count experiments in separate fresh directories
- **THEN** each produces the required artifacts, all five naive reports, selected SharedRidge results, independently recomputable metrics and measured cost records

#### Scenario: Separately authorized r2 experiment
- **WHEN** the documented CPU entry executes an r2/count formal experiment after separate research authorization in a fresh directory
- **THEN** it produces the same complete artifact, selection, grouping, provenance and cost contract, without changing accepted r0/region evidence

#### Scenario: Existing scientific acceptance survives record-format maintenance
- **WHEN** maintenance changes output retention and check organization without changing scientific computation
- **THEN** historical formal evidence remains unchanged and applicable, new behavior is exercised on temporary fixtures for both supported schemas and same-seed repetition, and no new real-data experiment is required

#### Scenario: r2 software readiness is independently verified
- **WHEN** temporary r2 development fixtures pass end-to-end auditing, all five naive methods, validation-selected SharedRidge, fixed grouping, complete output, saved-only checks and same-seed comparison, and an r2-scale development cost measurement is recorded
- **THEN** the evidence establishes implementation readiness without creating formal research/runs outputs, changing historical acceptance or declaring P01-T006 scientifically complete

#### Scenario: Implementation readiness only
- **WHEN** both folds satisfy the contract and default regression under independent fixture/development verification
- **THEN** readiness can be evidenced without formal fold runs or T007 acceptance, and research-side wrap-up later assesses the archived current-basis PASS


### Requirement: Saved-result checks produce exclusive compact reports
Recompute, compare and align-v2 SHALL accept an explicit report output path and write one exclusive JSON report, without full check-type run directories, source snapshots, environment copies, sidecars or artifact hash tables. Each report SHALL contain the check kind, input execution IDs/locations and necessary consumed-input identities, checker source identity/version, exact command, result/status, documented tolerances and decisive differences/errors. Recomputation details SHALL be carried within that report. Checks SHALL read only saved inputs and SHALL NOT fit models, read source demand/graph data, alter any input, overwrite an existing report or place output within an input run directory. Failed checks with a usable output destination SHALL retain a report and return nonzero. Legacy check `--run-id` and `--runs-root` arguments SHALL resolve to a single `<root>/<run-id>.json` report, with default root `research/reports/nograph-baseline/`; supplying both a report path and a legacy run ID SHALL fail before writing. Existing saved model-run schemas, including package-restored T004 runs, SHALL remain readable without changing their original files. Comparison SHALL preserve identity/condition mismatch rejection and the preexisting numerical tolerances; differing protocol file identities SHALL NOT silently be equated because scientific version strings agree. All three checks SHALL support saved main-split r2 results with r2 context identity under the same report contract as r0/region; for A/B, recompute and compare SHALL support all three datasets and align-v2 SHALL explicitly reject fold runs.


For folds recompute SHALL derive validation/eval splits, method names and fit18/fit21 mask/mean identities from validated saved metadata and reproduce all reported metrics, gains and node-error statistics from saved evidence only. Compare SHALL explicitly require the same dataset AND demand content identity, fold and seed, in addition to existing condition/identity checks and tolerances. Different folds, main-versus-fold, datasets, demand contents or seeds SHALL fail decisively even when deterministic predictions match. Historical runs without fold metadata SHALL resolve to main only with valid saved main-split evidence; contradictory, unknown or incomplete fold evidence SHALL fail rather than fall back. Reports SHALL identify the actual consumed fold-specific arrays, masks, means and metadata.

#### Scenario: Three saved-only check commands
- **WHEN** recompute, compare or align-v2 is called with a new explicit report path and valid saved inputs
- **THEN** only the requested report is produced, with linked inputs, checker source, command, tolerances and the complete applicable result, and input bytes remain unchanged

#### Scenario: Report collision or output inside an input
- **WHEN** the requested report already exists or resolves inside an input run
- **THEN** the command fails without replacing any report or input data

#### Scenario: Invalid saved evidence
- **WHEN** a saved input is missing required arrays, has an invalid identity, violates compare conditions or exceeds metric/alignment tolerances
- **THEN** the safe report records failure and decisive details, the command returns nonzero, and no check run or input mutation occurs

#### Scenario: Legacy command flags are reused
- **WHEN** a check uses a legacy run ID and optional root instead of an explicit report path
- **THEN** it produces one exclusive `<root>/<run-id>.json` report with documented report-path metadata and no experiment directory

#### Scenario: Output flag choices conflict
- **WHEN** a check supplies both an explicit report path and a legacy run ID
- **THEN** the command rejects the conflicting choice without creating output

#### Scenario: r2 recomputation and repetition
- **WHEN** recompute consumes complete r2 saved arrays/identities/masks and compare consumes two independent same-seed r2 development executions with matching conditions
- **THEN** recomputation reproduces all reported metrics and gains, comparison records prediction maximum absolute differences and protocol MAE relative differences within 1e-6, and both reports preserve r2_id identities and input bytes

#### Scenario: r2 identities or predictions disagree
- **WHEN** r2 saved identities/masks or compared source/conditions disagree, or saved predictions cause metrics to exceed the existing tolerance
- **THEN** checks retain decisive failure reports and return nonzero without relaxing tolerances, fitting models or rewriting inputs

#### Scenario: Saved-only fold recomputation and repeat
- **WHEN** source demand/graph reads and fitting are disabled and two matching same-fold development runs are checked
- **THEN** recompute reproduces all validation/eval metrics, gains and node errors and compare records prediction maximum absolute differences and protocol relative MAE differences under existing CPU tolerance 1e-6 without input mutation

#### Scenario: Fold mismatch
- **WHEN** compare receives A versus B or main versus a fold with identical data and seed
- **THEN** it returns nonzero with an explicit fold-identity failure report

#### Scenario: Data mismatch
- **WHEN** runs share fold and seed but differ in dataset or demand content identity
- **THEN** compare fails explicitly on the differing data identity

#### Scenario: Seed mismatch
- **WHEN** runs share data and fold but differ in seed
- **THEN** compare fails explicitly on seed identity even when predictions coincide

#### Scenario: Inconsistent fold evidence
- **WHEN** saved fold labels, fitting counts, windows, masks or method names contradict each other or required fold artifacts are absent
- **THEN** a nonzero failure report identifies the contradiction or missing evidence without using main defaults

#### Scenario: Historical main schema
- **WHEN** valid saved main evidence lacks the newly introduced fold fields
- **THEN** existing main checks and tolerances remain usable without rewriting the run

