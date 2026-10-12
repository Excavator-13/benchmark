## RENAMED Requirements

- FROM: `### Requirement: Both supported datasets produce complete formal artifacts`
- TO: `### Requirement: Supported datasets produce complete formal artifacts`

## MODIFIED Requirements

### Requirement: Independent CPU entry follows the research protocol
The entry SHALL support `r0/count`, `region/count` and `r2/count` through a stable documented command or module interface. It SHALL use sections 3-6 of `research/phases/P01/protocol.md` (`P1-count-L6-H3-v3`) as the sole normative scientific definition. It SHALL be importable and runnable with only NumPy, pandas and PyArrow as installed third-party dependencies. It SHALL NOT import modules under `benchmark/graph_method`, require PyTorch/PyG/DGL/CUDA dependencies, or require generated graph data for forecasting. Optional scikit-learn support SHALL NOT be required by the default execution path. CPU automated tests SHALL run without GPU or repository graph data. Adding r2 support SHALL preserve r0/region scientific behavior and saved-result formats without changing the scientific protocol version or record policy `P01-records-v2`.

#### Scenario: Minimal dependency environment
- **WHEN** only NumPy, pandas and PyArrow are installed in a Python environment
- **THEN** the public entry imports, displays help and executes all five naive methods and shared Ridge on valid fixture data for each supported dataset without importing graph or GPU packages

#### Scenario: Supported r2 count request
- **WHEN** a user requests r2/count with valid demand and coverage evidence
- **THEN** the same public entry accepts it and applies the fixed protocol, validation-only selection, common activity/neighbor masks and complete saved-result contract

#### Scenario: Unsupported scientific configuration
- **WHEN** a user requests a dataset outside r0/region/r2, rate mode or a split outside this protocol
- **THEN** the entry rejects it with the supported configuration before fitting instead of silently running a different protocol

### Requirement: Demand identity and observations are validated
The entry SHALL read `dataset/demand/r0.parquet`, `dataset/demand/region.parquet` or `dataset/demand/r2.parquet`, sort ascending by `(r0_id, skill_id)`, `(region_id, skill_id)` or `(r2_id, skill_id)` respectively, and retain the keys with every saved prediction identity. It SHALL require a nonempty set of unique finite integer node keys, exactly 36 continuous monthly columns from 2021-01 through 2023-12, and finite nonnegative counts. It SHALL audit node/skill/context counts, context-skill grid completeness, monthly nonzero fractions, training-27-month and full-36-month all-zero fractions, constant nodes, value ranges and per-context results. Full-period descriptive audits SHALL NOT affect grouping, fitting or selection.

#### Scenario: Valid data arrives out of order
- **WHEN** valid r0, region or r2 rows are shuffled
- **THEN** canonical keys, aligned signals, labels and predictions use the same ascending key order for that dataset

#### Scenario: Source is invalid
- **WHEN** keys are duplicated or invalid, the dataset's context key is missing, monthly columns are missing or extra, or counts are negative or nonfinite
- **THEN** execution fails before fitting with the dataset and validation failure recorded

#### Scenario: Multiple r2 contexts share skill IDs
- **WHEN** r2 demand contains the same skill in multiple r2 contexts and a context-skill combination is absent
- **THEN** identities remain distinct by r2_id, the grid audit reports the missing combination and actual counts, and no merging or silent filling changes the prediction population

### Requirement: Neighbor coverage is an evaluation annotation
Formal runs SHALL report nodes with and without non-self neighbors using context-qualified endpoint membership in the corresponding raw graph Parquet or a validated identity-aligned mask with source provenance. Both ends of non-self rows SHALL count as covered, self-loops SHALL NOT supply a neighbor, and unmatched endpoints SHALL fail validation. The annotation SHALL be fixed for all methods, saved with node keys and source hashes, and SHALL NOT influence predictions, normalization, fitting or selection. In-memory fixture masks SHALL support tests without graph files. Missing coverage evidence SHALL NOT silently classify every node as isolated or qualify an incomplete run as a successful formal run. r2 coverage SHALL qualify endpoints using r2_id and skill_id, with the same validation and annotation semantics as r0/region.

#### Scenario: Same skill occurs in two regions
- **WHEN** a non-self edge exists in only one region and a self-loop exists in the other
- **THEN** only the correctly qualified edge endpoints receive the neighbor mask and forecasting results do not depend on the annotation

#### Scenario: Same skill occurs in two r2 contexts
- **WHEN** a fixture has a non-self edge in one r2 context and only a self-loop for the same skill in another
- **THEN** both endpoints of the non-self edge alone receive coverage, all methods use the same saved neighbor masks, and changing valid coverage leaves predictions and selection unchanged

#### Scenario: Invalid r2 coverage evidence
- **WHEN** r2 coverage references an unknown context or skill, omits r2_id, or a supplied mask has incorrect dataset, keys, definition or provenance
- **THEN** execution fails with the coverage validation error rather than assigning coverage across contexts or defaulting to isolated nodes

### Requirement: Runtime costs are actual measurements
For each dataset and execution the entry SHALL record separate elapsed data-reading, fitting and inference durations, total duration and process peak resident memory with units and measurement method. It SHALL identify machine, operating system, CPU, device, Python/package/linear-algebra versions and execution settings. It SHALL NOT present diagnostic elapsed times, estimates or unmeasured promises as the new formal entry's measured performance. r2 support SHALL provide a reproducible development measurement path at r2 data scale, with input dimensions, command, input identity and purpose recorded. Synthetic scale measurements SHALL identify synthetic inputs and SHALL NOT be presented as measured costs on the real r2 dataset or as formal scientific evidence.

#### Scenario: A formal CPU run finishes
- **WHEN** a dataset's formal execution completes
- **THEN** its own measured stage durations and peak resident bytes are saved with environment and machine information

#### Scenario: r2 scale development measurement
- **WHEN** the development entry executes a reproducibly generated r2 fixture with 52 contexts, 2335 skills per context and 36 months in a fresh CPU worker
- **THEN** its actual 121420-node execution records separate read/fit/inference and total durations, process peak RSS with units/method, environment and synthetic input identity, outside research/runs and without claiming a formal r2 experiment or predictive conclusion

### Requirement: Formal results align with immutable v2 diagnostics
The entry SHALL compare each supported dataset's canonical identity evidence, split metadata, all five naive validation/test metrics, window/horizon/activity results and reference choices against an explicitly supplied immutable v2-format diagnostic reference containing that dataset. `research/runs/phase1-20261006-v2-01/naive-baselines.log` SHALL remain the historical reference for r0 and region; r2 support SHALL NOT add records to or rewrite it. The entry SHALL record the reference hash, compared fields, tolerances and differences. Since the reference log contains counts rather than full node keys, identity alignment SHALL also be checked against the same hashed sources and canonical ordering and SHALL NOT claim that full identities were recovered from the log alone. Any discrepancy SHALL be preserved and explained as a finding; it SHALL NOT rewrite old logs or change the protocol to force agreement. Missing dataset records SHALL fail explicitly; missing source identity SHALL retain the existing limited outcome rather than be claimed as a successful alignment. Temporary r2 fixture references SHALL establish software compatibility only.

#### Scenario: Legacy naive value differs
- **WHEN** a new naive metric differs from the v2 reference beyond the declared numerical tolerance
- **THEN** the new run records the expected/actual values and investigation outcome while the original log remains byte-for-byte unchanged

#### Scenario: Independent r2 fixture reference
- **WHEN** align-v2 consumes a saved r2 development fixture and an independently computed v2-format r2 reference with matching demand source identity
- **THEN** it compares identity counts, canonical-source evidence, splits, all five naive results and references with the existing diagnostic tolerance and produces a linked report without rereading source demand/graph data

#### Scenario: Reference contains no r2 records
- **WHEN** align-v2 receives an r2 result and a reference containing only r0/region
- **THEN** it returns nonzero with a failure report naming the missing r2 reference and leaves input results and reference unchanged

### Requirement: Supported datasets produce complete formal artifacts
Formal scientific evidence SHALL include completed end-to-end model executions for each authorized supported dataset, independent same-seed repetitions and linked metric-recomputation, diagnostic-alignment and measurement evidence. Every completed formal model execution SHALL contain all five naive methods and validation-selected shared Ridge with the preceding identity, selection, grouping and provenance outputs. Checks SHALL use linked reports rather than independent experiment directories. Packaging, commits, pushes, research-record updates and main-spec synchronization SHALL remain outside model/check tasks. A record-format maintenance change SHALL reuse applicable accepted historical formal evidence and validate the changed behavior using temporary CPU fixtures; it SHALL NOT require rerunning accepted scientific experiments merely to change their saved format or relabel fixture evidence as a new scientific result. Adding r2 support SHALL be verified with temporary/development CPU evidence and SHALL NOT require new formal r2 executions or rerunning accepted r0/region experiments to establish software readiness. Formal r2 execution and research acceptance SHALL remain separately authorized research actions.

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

### Requirement: Saved-result checks produce exclusive compact reports
Recompute, compare and align-v2 SHALL accept an explicit report output path and write one exclusive JSON report, without full check-type run directories, source snapshots, environment copies, sidecars or artifact hash tables. Each report SHALL contain the check kind, input execution IDs/locations and necessary consumed-input identities, checker source identity/version, exact command, result/status, documented tolerances and decisive differences/errors. Recomputation details SHALL be carried within that report. Checks SHALL read only saved inputs and SHALL NOT fit models, read source demand/graph data, alter any input, overwrite an existing report or place output within an input run directory. Failed checks with a usable output destination SHALL retain a report and return nonzero. Legacy check `--run-id` and `--runs-root` arguments SHALL resolve to a single `<root>/<run-id>.json` report, with default root `research/reports/nograph-baseline/`; supplying both a report path and a legacy run ID SHALL fail before writing. Existing saved model-run schemas, including package-restored T004 runs, SHALL remain readable without changing their original files. Comparison SHALL preserve identity/condition mismatch rejection and the preexisting numerical tolerances; differing protocol file identities SHALL NOT silently be equated because scientific version strings agree. All three checks SHALL support saved r2 results with r2 context identity under the same report contract as r0/region.

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
