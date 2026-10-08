# nograph-baseline-entry Specification

## Purpose

Provide an independent CPU entry for protocol-defined naive baselines and shared Ridge forecasting, with recoverable predictions, auditable selection and measured reproducibility on r0/count and region/count.

## Requirements

### Requirement: Independent CPU entry follows the research protocol
The entry SHALL support `r0/count` and `region/count` through a stable documented command or module interface. It SHALL use sections 3-6 of `research/phases/P01/protocol.md` (`P1-count-L6-H3-v3`) as the sole normative scientific definition. It SHALL be importable and runnable with only NumPy, pandas and PyArrow as installed third-party dependencies. It SHALL NOT import modules under `benchmark/graph_method`, require PyTorch/PyG/DGL/CUDA dependencies, or require generated graph data for forecasting. Optional scikit-learn support SHALL NOT be required by the default execution path. CPU automated tests SHALL run without GPU or repository graph data.

#### Scenario: Minimal dependency environment
- **WHEN** only NumPy, pandas and PyArrow are installed in a Python environment
- **THEN** the public entry imports, displays help and executes all five naive methods and shared Ridge on valid fixture data without importing graph or GPU packages

#### Scenario: Unsupported scientific configuration
- **WHEN** a user requests r2, rate mode or a split outside this protocol
- **THEN** the entry rejects it with the supported configuration before fitting instead of silently running a different protocol

### Requirement: Demand identity and observations are validated
The entry SHALL read `dataset/demand/r0.parquet` or `dataset/demand/region.parquet`, sort ascending by `(r0_id, skill_id)` or `(region_id, skill_id)`, and retain the keys with every saved prediction identity. It SHALL require a nonempty set of unique finite integer node keys, exactly 36 continuous monthly columns from 2021-01 through 2023-12, and finite nonnegative counts. It SHALL audit node/skill/context counts, context-skill grid completeness, monthly nonzero fractions, training-27-month and full-36-month all-zero fractions, constant nodes, value ranges and per-context results. Full-period descriptive audits SHALL NOT affect grouping, fitting or selection.

#### Scenario: Valid data arrives out of order
- **WHEN** valid r0 or region rows are shuffled
- **THEN** canonical keys, aligned signals, labels and predictions use the same ascending key order

#### Scenario: Source is invalid
- **WHEN** keys are duplicated or invalid, monthly columns are missing or extra, or counts are negative or nonfinite
- **THEN** execution fails before fitting with the dataset and validation failure recorded

### Requirement: Fixed windows isolate target months and preserve rolling origins
The entry SHALL construct all 28 unit-stride windows with L=6 and H=3. It SHALL use training starts 0..18, validation start 21 and test starts 24..27, and omit exactly starts 19, 20, 22 and 23. Target-month sets SHALL be pairwise disjoint across splits: training 2021-07..2023-03, validation 2023-04..2023-06 and test 2023-07..2023-12. It SHALL save all starts, omissions, input/target months and forecast origins. Each naive and Ridge prediction SHALL be independent of hidden state from other windows. Later test origins SHALL use then-observed true history with model parameters and normalization frozen after training.

#### Scenario: Protocol split is constructed
- **WHEN** 36 monthly observations are windowed with L=6 and H=3
- **THEN** there are 19 training, 1 validation and 4 test windows, exactly 4 omitted windows, and no target month belongs to multiple splits

#### Scenario: Second test origin uses known history
- **WHEN** predicting the test window starting at 25
- **THEN** its input is 2023-02..2023-07 and its targets are 2023-08..2023-10, with July's true observation available as input and no refitting on validation or test observations

### Requirement: All naive methods and frozen references are reported
The entry SHALL report Zero, LastValue, WindowMean6, TrainMean27 and SeasonalNaive12. Zero SHALL predict zero; LastValue SHALL repeat the last input value; WindowMean6 SHALL repeat the mean of the six inputs; TrainMean27 SHALL repeat the frozen per-node mean over 2021-01..2023-03; SeasonalNaive12 SHALL use the preceding year's same month for each target. It SHALL select `NaiveRef` from all five using validation MSE, breaking exact ties in this listed order, and freeze the choice before test evaluation. It SHALL select `NaiveRef6` identically from the first four, and label SeasonalNaive12 and any reference using it as extra-history references. TrainMean27 SHALL be identified as frozen training statistics, not new prediction-time history. Test rankings SHALL NOT change reference selection.

#### Scenario: Validation MSE ties
- **WHEN** two naive candidates have equal validation MSE
- **THEN** the earlier method in the protocol table is selected regardless of their validation MAE or test results, and the full score table and tie decision are saved

#### Scenario: Seasonal prediction uses extra history
- **WHEN** predicting targets 2023-04, 2023-05 and 2023-06
- **THEN** SeasonalNaive12 predicts values from 2022-04, 2022-05 and 2022-06 respectively, is marked as extra history, and is excluded from NaiveRef6

### Requirement: Normalization counts training observation months exactly once
The entry SHALL compute each node's mean and ddof=0 standard deviation from precisely the 27 observations 2021-01..2023-03, with each month counted once and constant-node standard deviation replaced by 1. It SHALL freeze these statistics and apply the same node statistics to both inputs and targets. It SHALL NOT fit statistics from training targets alone, duplicated values in overlapping windows, or validation/test months. TrainMean27 and activity grouping SHALL use the same unique training observation range.

#### Scenario: Overlapping training windows have unequal month multiplicities
- **WHEN** a node's training series produces different statistics if flattened across overlapping windows
- **THEN** the saved normalization equals the mean and ddof=0 standard deviation of its unique 27 observations and differs from the overlap-weighted estimate

#### Scenario: Future values change
- **WHEN** values after 2023-03 change while the first 27 months stay fixed
- **THEN** normalization, frozen training means, activity masks and training-only fitted candidate parameters remain unchanged

#### Scenario: Constant training node
- **WHEN** a node has zero variance in its 27 training observations
- **THEN** its stored effective standard deviation is 1 and standardized inputs and targets remain finite

### Requirement: Ridge parameters are shared and selected exclusively on validation
The entry SHALL report the model as `SharedRidge` and fit one 6x3 weight matrix and three unregularized biases shared across every node and all 19 training windows. It SHALL minimize `(1/M) * sum_m ||x_m W + b - y_m||_2^2 + lambda * ||W||_F^2`, where M=19 times the node count, using standardized training samples. It SHALL fit candidates at lambda `1e-4, 1e-3, 1e-2, 1e-1, 1`, inverse-transform validation predictions and select only by validation original-unit MSE, breaking exact ties toward the larger lambda. It SHALL record each candidate's validation MSE/MAE, sample count, objective, solver/backend, normalization and selection decision. A sum-loss backend using alpha SHALL use and record `alpha=lambda*M`. Test targets SHALL NOT be supplied to fitting or selection; selection SHALL be finalized before test evaluation. It SHALL retain raw inverse-transformed outputs as primary; optional nonnegative-clipped outputs SHALL be separately labeled and SHALL NOT select lambda.

#### Scenario: Test labels cannot affect selection
- **WHEN** the selector is invoked without access to test labels and validation MSE favors a candidate different from validation MAE
- **THEN** it selects the validation-MSE winner; subsequently changing test labels does not change candidate parameters, selected lambda or reference identities

#### Scenario: Lambda scores tie
- **WHEN** multiple Ridge candidates have exactly equal validation original-unit MSE
- **THEN** the larger lambda is selected and the recorded selection table explains the tie

#### Scenario: Sum-loss backend is used
- **WHEN** a backend defines its regularization coefficient against an unaveraged residual sum
- **THEN** it receives alpha=lambda*M and saves lambda, alpha and M rather than treating lambda as alpha

### Requirement: Metrics use common fixed masks and original units
The entry SHALL report validation MSE/MAE and overall test MAE/RMSE, with RMSE equal to the square root of mean squared error over all window-node-horizon elements. It SHALL report per-window, per-horizon, per-context, activity-group and neighbor-group MAE/RMSE with node and evaluated-element counts, negative-prediction ratios, absolute/squared error contributions for activity groups and constant/large-demand diagnostics, and equal-weight activity-group MAE. The four activity masks SHALL be fixed by the training-27-month nonzero fraction: zero, (0,1/3], (1/3,2/3], (2/3,1]. Training-all-zero nodes SHALL be explicitly reported. Empty groups SHALL have zero counts and explicit unavailable metrics, excluded from equal-weight MAE. All methods SHALL use exactly the same saved masks. The main test aggregation SHALL retain overlapping target-month multiplicities 1,2,3,3,2,1, without treating them as independent samples. Activity/context relative MAE gains SHALL use frozen specified references, with undefined gain when reference MAE is zero.

#### Scenario: Window RMSE values differ
- **WHEN** test windows have different mean squared errors
- **THEN** overall RMSE is recomputed from all squared errors and is not the arithmetic mean of the window RMSE values

#### Scenario: Activity boundaries and an empty group
- **WHEN** training activities include 0, 1/3 and 2/3 and one group is empty
- **THEN** boundary nodes enter their protocol groups, all methods share those masks, the empty group is marked explicitly and equal-weight MAE averages only nonempty groups

### Requirement: Neighbor coverage is an evaluation annotation
Formal runs SHALL report nodes with and without non-self neighbors using context-qualified endpoint membership in the corresponding raw graph Parquet or a validated identity-aligned mask with source provenance. Both ends of non-self rows SHALL count as covered, self-loops SHALL NOT supply a neighbor, and unmatched endpoints SHALL fail validation. The annotation SHALL be fixed for all methods, saved with node keys and source hashes, and SHALL NOT influence predictions, normalization, fitting or selection. In-memory fixture masks SHALL support tests without graph files. Missing coverage evidence SHALL NOT silently classify every node as isolated or qualify an incomplete run as a successful formal run.

#### Scenario: Same skill occurs in two regions
- **WHEN** a non-self edge exists in only one region and a self-loop exists in the other
- **THEN** only the correctly qualified edge endpoints receive the neighbor mask and forecasting results do not depend on the annotation

### Requirement: Each run saves recoverable and independently recomputable evidence
Formal model experiments SHALL create fresh exclusive `research/runs/<run_id>/` directories by default and refuse overwriting existing executions. They SHALL record scientific protocol `P1-count-L6-H3-v3` and record policy `P01-records-v2`, resolved configuration and exact command, fixed source/input identities, code commit and relevant execution differences including necessary used untracked source, environment/machine/CPU details, canonical node keys, window identities/splits, predictions and labels, all metrics/masks, selected fitted parameters/preprocessing statistics, complete candidate score/selection records, timings/device and status. Committed runtime source and protocol SHALL be located by fixed commit and repository-relative path without repeated copies; relevant uncommitted execution content SHALL be recoverable from saved patches/files. Unrelated documentation, test and cache changes SHALL NOT be included in execution-source snapshots. Unavailable identity evidence SHALL be explicit and SHALL NOT be invented. Numeric outputs SHALL load without graph libraries or Python-object pickle. Saved predictions/labels/identities/masks SHALL suffice to independently recompute every reported metric and relative comparison without fitting or rereading source data. Losing-candidate full parameters and predictions SHALL be omitted by default and retained only with an explicit option, while every candidate's validation scores and selection reasons remain saved. Failures and interruptions SHALL preserve available evidence, errors and incomplete status, including detectable unfinished state after uncatchable termination. Success SHALL NOT imply scientific acceptance, packaging, Git inclusion or backup completion, and SHALL NOT automatically trigger any of those operations or recovery checks.

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

### Requirement: Same-seed CPU repetition is measured without artificial seed variance
Each dataset's formal evidence SHALL include two independent CPU executions with the same seed, inputs, protocol, configuration and recorded execution conditions in separate run directories. Comparison SHALL record prediction maximum absolute difference, prediction numerical agreement, metric differences and the protocol MAE relative difference `abs(MAE_a-MAE_b)/max(1,MAE_a,MAE_b)`, requiring the CPU difference to be at most 1e-6. Agreement checks for predictions and other error metrics SHALL use a documented CPU relative tolerance no greater than 1e-6 with explicit handling of near-zero values. The entry SHALL NOT manufacture seed variance for deterministic naive methods or deterministic shared Ridge.

#### Scenario: Same seed is executed twice
- **WHEN** two runs on the same CPU environment use identical inputs, protocol and seed
- **THEN** their predictions and metrics agree under the documented tolerance, the protocol relative MAE difference is at most 1e-6, and prediction maximum absolute difference is saved in linked comparison evidence

### Requirement: Runtime costs are actual measurements
For each dataset and execution the entry SHALL record separate elapsed data-reading, fitting and inference durations, total duration and process peak resident memory with units and measurement method. It SHALL identify machine, operating system, CPU, device, Python/package/linear-algebra versions and execution settings. It SHALL NOT present diagnostic elapsed times, estimates or unmeasured promises as the new formal entry's measured performance.

#### Scenario: A formal CPU run finishes
- **WHEN** a dataset's formal execution completes
- **THEN** its own measured stage durations and peak resident bytes are saved with environment and machine information

### Requirement: Formal results align with immutable v2 diagnostics
The entry SHALL compare both datasets' canonical identity evidence, split metadata, all five naive validation/test metrics, window/horizon/activity results and reference choices against `research/runs/phase1-20261006-v2-01/naive-baselines.log`. It SHALL record the reference hash, compared fields, tolerances and differences. Since the old log contains counts rather than full node keys, identity alignment SHALL also be checked against the same hashed sources and canonical ordering and SHALL NOT claim that full identities were recovered from the log alone. Any discrepancy SHALL be preserved and explained as a finding; it SHALL NOT rewrite old logs or change the protocol to force agreement.

#### Scenario: Legacy naive value differs
- **WHEN** a new naive metric differs from the v2 reference beyond the declared numerical tolerance
- **THEN** the new run records the expected/actual values and investigation outcome while the original log remains byte-for-byte unchanged

### Requirement: Both supported datasets produce complete formal artifacts
Formal scientific evidence SHALL include completed end-to-end model executions for `r0/count` and `region/count`, independent same-seed repetitions and linked metric-recomputation, diagnostic-alignment and measurement evidence. Every completed formal model execution SHALL contain all five naive methods and validation-selected shared Ridge with the preceding identity, selection, grouping and provenance outputs. Checks SHALL use linked reports rather than independent experiment directories. Packaging, commits, pushes, research-record updates and main-spec synchronization SHALL remain outside model/check tasks. A record-format maintenance change SHALL reuse applicable accepted historical formal evidence and validate the changed behavior using temporary CPU fixtures; it SHALL NOT require rerunning accepted scientific experiments merely to change their saved format or relabel fixture evidence as a new scientific result.

#### Scenario: Execute both supported datasets end to end
- **WHEN** the documented CPU entry executes authorized r0/count and region/count experiments in separate fresh directories
- **THEN** each produces the required artifacts, all five naive reports, selected SharedRidge results, independently recomputable metrics and measured cost records

#### Scenario: Existing scientific acceptance survives record-format maintenance
- **WHEN** maintenance changes output retention and check organization without changing scientific computation
- **THEN** historical formal evidence remains unchanged and applicable, new behavior is exercised on temporary fixtures for both supported schemas and same-seed repetition, and no new real-data experiment is required

### Requirement: Development invocations stay outside the formal experiment namespace
The entry SHALL expose an explicit formal/development purpose with formal as the default. Formal output SHALL continue to default to `research/runs/`; development output SHALL default to ignored `scratch/nograph-baseline/` and be labeled as development rather than scientific acceptance evidence. Development invocations SHALL NOT create directories inside the repository's `research/runs/` namespace, including via output overrides. Temporary fixture roots outside that namespace SHALL remain supported. Both purposes SHALL enforce non-overwrite behavior and preserve the scientific computation; changing purpose SHALL NOT change fitting, reference selection or reported metric definitions.

#### Scenario: Development fixture runs
- **WHEN** a fixture model invocation selects development purpose without a root override
- **THEN** its labeled execution output appears under `scratch/nograph-baseline/`, no formal experiment directory is created, and its scientific predictions/metrics agree with the equivalent formal-purpose fixture

#### Scenario: Development output points at formal records
- **WHEN** development purpose requests an output root inside the repository's `research/runs/`
- **THEN** execution rejects it before creating an experiment directory or fitting

### Requirement: Saved-result checks produce exclusive compact reports
Recompute, compare and align-v2 SHALL accept an explicit report output path and write one exclusive JSON report, without full check-type run directories, source snapshots, environment copies, sidecars or artifact hash tables. Each report SHALL contain the check kind, input execution IDs/locations and necessary consumed-input identities, checker source identity/version, exact command, result/status, documented tolerances and decisive differences/errors. Recomputation details SHALL be carried within that report. Checks SHALL read only saved inputs and SHALL NOT fit models, read source demand/graph data, alter any input, overwrite an existing report or place output within an input run directory. Failed checks with a usable output destination SHALL retain a report and return nonzero. Legacy check `--run-id` and `--runs-root` arguments SHALL resolve to a single `<root>/<run-id>.json` report, with default root `research/reports/nograph-baseline/`; supplying both a report path and a legacy run ID SHALL fail before writing. Existing saved model-run schemas, including package-restored T004 runs, SHALL remain readable without changing their original files. Comparison SHALL preserve identity/condition mismatch rejection and the preexisting numerical tolerances; differing protocol file identities SHALL NOT silently be equated because scientific version strings agree.

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

### Requirement: Git-backed package metadata preserves exclusions without duplicate hash inventories
The T004 archive utility SHALL accept schema-v2 package indexes locating packages by fixed Git commit/path, package size/member count, and explicit exclusion declarations, without requiring or generating external package SHA256 sidecars or full member hash tables for Git-backed packages. It SHALL retain support for historical schema-v1 verification, including its existing checksums. Schema-v2 explicit verification SHALL compare package contents with their recorded Git identity and validate member safety, uniqueness and recorded counts before any restoration to a new temporary directory; it SHALL reject missing/changed packages, unsafe members and unresolvable Git identities without modifying packages, readable input entries or existing runs. Indexes SHALL preserve intentional package exclusions separately from exclusions in embedded artifact manifests; exclusion declarations SHALL NOT imply those embedded-manifest exclusions are absent from packages. Package export outside Git SHALL require an external SHA256. This utility SHALL run only as a separately requested maintenance action; model and check execution SHALL NOT invoke it. Existing sealed packages SHALL never be overwritten or reformatted.

#### Scenario: Explicit schema-v2 verification without sidecars
- **WHEN** a Git-backed schema-v2 index is verified with its recorded commit available and no sidecars/member hash table
- **THEN** package identity and safe member counts are verified from the fixed Git content and index, and restoration uses only a fresh temporary location while original packages and readable entries remain unchanged

#### Scenario: Unsafe or changed package
- **WHEN** a package differs from its recorded Git version, is missing, has duplicate/traversing/link members or a mismatched member count
- **THEN** verification fails before unsafe extraction or input mutation and reports the cause

#### Scenario: Historical schema-v1 metadata is supplied
- **WHEN** explicit verification receives the old checksum-bearing schema-v1 index and its packages/sidecars
- **THEN** the documented historical verification remains supported without rewriting that metadata or its packages

#### Scenario: Exclusion declarations are retained
- **WHEN** a Git-backed package index omits duplicate hash inventories
- **THEN** it still states package exclusions `__pycache__/`, `.DS_Store`, `._*`, separately identifies embedded-manifest exclusions `artifacts-sha256.json` and `events.jsonl`, and retains task and sealed-at provenance

#### Scenario: Package is separately exported outside Git
- **WHEN** an explicitly requested maintenance action exports a package to storage outside Git
- **THEN** it supplies external SHA256 identity for that exported byte content and never changes the original sealed package
