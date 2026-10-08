## MODIFIED Requirements

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

### Requirement: Both supported datasets produce complete formal artifacts
Formal scientific evidence SHALL include completed end-to-end model executions for `r0/count` and `region/count`, independent same-seed repetitions and linked metric-recomputation, diagnostic-alignment and measurement evidence. Every completed formal model execution SHALL contain all five naive methods and validation-selected shared Ridge with the preceding identity, selection, grouping and provenance outputs. Checks SHALL use linked reports rather than independent experiment directories. Packaging, commits, pushes, research-record updates and main-spec synchronization SHALL remain outside model/check tasks. A record-format maintenance change SHALL reuse applicable accepted historical formal evidence and validate the changed behavior using temporary CPU fixtures; it SHALL NOT require rerunning accepted scientific experiments merely to change their saved format or relabel fixture evidence as a new scientific result.

#### Scenario: Execute both supported datasets end to end
- **WHEN** the documented CPU entry executes authorized r0/count and region/count experiments in separate fresh directories
- **THEN** each produces the required artifacts, all five naive reports, selected SharedRidge results, independently recomputable metrics and measured cost records

#### Scenario: Existing scientific acceptance survives record-format maintenance
- **WHEN** maintenance changes output retention and check organization without changing scientific computation
- **THEN** historical formal evidence remains unchanged and applicable, new behavior is exercised on temporary fixtures for both supported schemas and same-seed repetition, and no new real-data experiment is required

## ADDED Requirements

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
