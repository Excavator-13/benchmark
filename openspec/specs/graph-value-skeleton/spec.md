# graph-value-skeleton Specification

## Purpose

Provide an independently checkable CPU implementation of the frozen P02 temporal skeleton, real-graph and degree-preserving shuffled controls, while preserving P01 data and evaluation identity and recoverable saved evidence. Software readiness establishes implementation behavior for later authorized research comparisons and does not establish predictive benefit or research acceptance.

## Requirements

### Requirement: P01 data and split identity is preserved
The entry SHALL support only r0/count, region/count and r2/count on the main P1-count-L6-H3-v3 split with record policy P01-records-v2. It SHALL use canonical numeric context/skill node ordering and the same float32 raw observations, input tensors, labels, node-key SHA256 encoding and window metadata as nograph-baseline-entry. It SHALL require exactly 36 continuous months 2021-01..2023-12, unique valid integer keys and finite nonnegative counts. Windows SHALL be L=6/H=3 with all 28 starts described, train 0..18, validation 21, test 24..27 and omissions 19/20/22/23; split target sets SHALL be disjoint. Later test inputs SHALL use then-observed true history without parameter refitting. Published-data execution SHALL reassert 2335/16345/121420 nodes, skills 0..2334 and contexts {0}/0..6/0..51 respectively, and SHALL reject incompatible published identity rather than silently alter the population. Small fixtures SHALL support the same schemas without requiring those full sizes.

#### Scenario: Shared identity oracle
- **WHEN** both entries consume the same out-of-order multi-context fixture including numeric identifiers 2 and 10
- **THEN** canonical keys and SHA256, float32 inputs/labels and all 28 window-role/month records are identical, integer ordering places 2 before 10, and no context's skill is merged with another

#### Scenario: Published data assertions
- **WHEN** an execution loads the published demand tables
- **THEN** the exact expected node/context/skill counts, dense complete grids, month columns and valid values are asserted and recorded, and any discrepancy fails before training

#### Scenario: Invalid scope or input
- **WHEN** rate mode, an A/B graph fold, unsupported data, invalid keys, duplicate identities, missing months or negative/nonfinite counts are supplied
- **THEN** the entry returns nonzero before training instead of substituting another scope or silently repairing the data

### Requirement: Graph endpoints retain context and numeric node identity
The entry SHALL interpret each graph row as `(context,row_id)` source to `(context,col_id)` target, where row_id/col_id are skill identifiers rather than global node indices. Endpoints SHALL resolve through the same canonical integer-key ordering as prepare_graph_data and the P01 entry. Unknown endpoints or invalid schema SHALL fail before training. Published graph inputs SHALL reassert only context/row_id/col_id columns, no independent weight/frequency column, edge counts 60804/218840/321374 for r0/region/r2, no duplicate rows or self-loops, complete reverse-edge symmetry and context block isolation. The dense mapping `context_ordinal*2335+skill_id` SHALL be proven against canonical key lookup before use; arbitrary small non-dense fixtures SHALL resolve by their actual keys.

#### Scenario: Context-qualified mapping
- **WHEN** two contexts share skill IDs and rows arrive in arbitrary order
- **THEN** both source and target indices match the existing preparation semantics, every edge stays within its context, and numeric-key and independently checked dense-offset mappings agree where the grid assumptions hold

#### Scenario: Unmatched endpoint
- **WHEN** a graph row refers to a context-qualified node absent from demand
- **THEN** execution fails naming the unmatched endpoint without generating a partially mapped training graph

### Requirement: The temporal encoder has independent node and window states
Every method SHALL encode each node's six raw monthly counts using the same single-layer unidirectional GRU temporal function with hidden dimension 32 and independent zero initial state for each node/window. Encoder weights SHALL be shared across nodes; hidden trajectories SHALL NOT be shared across nodes or carried between windows or splits. A shared Linear(32,3) head SHALL produce three raw predictions. Vectorization SHALL be equivalent to applying the same encoder separately to each node, and SHALL NOT treat node order as temporal recurrence. Methods self, graph and shuffled SHALL be trained independently under paired model seeds with matching initial learned parameters.

#### Scenario: Vectorization equivalence
- **WHEN** a nonconstant multi-node input is encoded both in a node batch and by a per-node loop using identical parameters
- **THEN** hidden states and outputs agree within normalized float32 tolerance 1e-6, and changing another node's input leaves the first node's pre-message hidden state unchanged

#### Scenario: State reset
- **WHEN** a window is evaluated alone or after a different window or split
- **THEN** its encoder output is identical under the same parameters and input, and later windows do not inherit hidden state

### Requirement: Graph messages are unweighted incoming-neighbor means
For each directed unique edge `(u,v)`, the graph and shuffled branches SHALL send h_u to v, compute the arithmetic mean over distinct incoming neighbors, and use `h'_v=h_v+mean_in(h_u)` before the shared output head. Self SHALL use h_v directly. The aggregation SHALL introduce no direction reversal, undirected conversion, learned weights or degree normalization beyond the incoming mean. Multiplicity SHALL be audited as raw/unique/duplicate counts and distribution, SHALL NOT be called observed frequency, and SHALL NOT weight the binary adjacency. Self-loops SHALL be rejected explicitly. Published symmetry SHALL NOT replace asymmetric direction tests.

#### Scenario: Asymmetric direction oracle
- **WHEN** distinct hidden states use directed edges 0→1, 2→1 and 1→2
- **THEN** the messages are exactly zero at 0, `(h_0+h_2)/2` at 1 and h_1 at 2 within arithmetic tolerance, and an outgoing-neighbor implementation fails this oracle

#### Scenario: Duplicate rows do not weight a neighbor
- **WHEN** a valid fixture repeats one fully qualified edge three times and supplies another incoming edge once
- **THEN** the audit reports that multiplicity and the target receives the equal mean of the two distinct source states, leaving the existing weighted preparation capability unchanged

### Requirement: Isolated nodes preserve exact same-parameter self output
A node with zero incoming degree SHALL receive an exactly zero message without division by zero. With identical encoder/head parameters, input and initial states, graph and self outputs for such a node SHALL be elementwise exactly equal, including when it has outgoing edges. An empty graph SHALL yield elementwise equality for every node. This is an operator equality under identical parameters; independently trained method checkpoints SHALL NOT be required to make identical isolated-node predictions.

#### Scenario: No incoming edge
- **WHEN** self and graph operators use the same parameters and inputs on a fixture containing an out-only node and an isolated node
- **THEN** those zero-in-degree nodes' messages are exactly zero and their predictions pass exact elementwise equality without NaN

#### Scenario: Empty graph
- **WHEN** the same-parameter operators receive no edges
- **THEN** the entire graph prediction tensor equals the self tensor elementwise

### Requirement: Graph propagation has no additional learned capacity
The three methods SHALL have identical trainable parameter names, shapes and counts, consisting only of the temporal encoder and shared output head. No graph-specific trainable tensor SHALL exist. The configured bias-enabled GRU(1,32) and Linear(32,3) SHALL total 3459 trainable parameters independent of node/edge counts. Actual measured per-component and total counts SHALL be asserted and saved in runtime metadata and implementation notes rather than only inferred from this specification.

#### Scenario: Parameter isomorphism
- **WHEN** self, graph and shuffled models are constructed at different fixture node/edge sizes
- **THEN** learned tensor signatures are identical, counts are GRU=3360, head=99 and total=3459, and the graph-only trainable parameter set is empty

### Requirement: Shuffled graphs preserve directed degrees and change edges reproducibly
The entry SHALL build shuffled graphs by directed two-edge endpoint swaps independently inside each context. Each accepted swap and final graph SHALL preserve every node's incoming and outgoing degrees and edge count, introduce no self-loops/duplicate edges/cross-context edges, and retain all node identities. For each nonempty context the final edge set SHALL differ from the original. The algorithm/version, seed, deterministic work budget, attempts/accepted swaps and per-context changed-edge counts/fractions and overlap SHALL be saved. Given the same source identity and shuffle seed, shuffled edge sets SHALL reproduce independent of model seed, run ID, source row order and process hash iteration order. Empty contexts SHALL be explicitly empty; nonempty unshufflable graphs, exhausted budgets or unchanged final graphs SHALL fail rather than return an original graph labeled shuffled. Preserving reverse-edge symmetry SHALL NOT be an additional constraint.

#### Scenario: Reproducible context-local swaps
- **WHEN** a multi-context swappable fixture is shuffled twice with the same shuffle seed and different input row order/model seed
- **THEN** canonical resulting edge arrays are identical, every original per-node in/out degree matches exactly, no context mixes, and each nonempty context records a nonzero edge-set symmetric difference

#### Scenario: No legal changed control
- **WHEN** a nonempty fixture has no legal endpoint swap or the declared attempt budget cannot achieve the required accepted swaps and changed final graph
- **THEN** execution returns nonzero with the context and reason and does not mark an unchanged graph as successful

### Requirement: Shuffled control averages all three graph MAEs per model seed
The shuffled control SHALL use exactly shuffle seeds 0,1,2 and train independently for each graph at each requested model seed. A saved-only control summary SHALL compute `(MAE_0+MAE_1+MAE_2)/3` for the same dataset, model seed, split, source published graph, code/environment, training configuration and fixed-mask identity, retaining the three individual MAEs and execution identities. The three shuffle seed identities SHALL be distinct; differences in resulting shuffled-graph identities and learned results SHALL be permitted by this summary rather than treated as repeat-condition mismatches. It SHALL NOT select the weakest graph or substitute MAE of averaged predictions. Missing/duplicate seeds or incompatible members SHALL fail. This summary SHALL provide evidence for the unchanged P01 §6.2 comparison, without declaring predictive benefit.

#### Scenario: Complete three-graph control
- **WHEN** three compatible members with shuffle seeds 0/1/2 and model seed s have MAEs 1, 2 and 6
- **THEN** the control MAE is 3 with all three member identities retained, independently of their ranking or the error of averaged predictions

#### Scenario: Incomplete or mixed control
- **WHEN** a member is missing, a seed is repeated, or a member differs in model seed, source/configuration or mask identity
- **THEN** summary fails without filling a member from another model seed or reporting an available-subset mean

### Requirement: Training budget and validation selection are fixed across methods
Each completed model execution SHALL train for exactly 200 epochs with Adam and hidden dimension 32, using raw-count inputs/labels, squared-error training and original-unit validation MSE checkpoint selection. All methods SHALL use the same resolved optimizer settings, loss weighting, batch/state rules and budget. Each epoch SHALL cover exactly the 19 training windows and all nodes/horizons with equal element weighting. All 200 training and validation MSE/MAE records, selected epoch and reason SHALL be saved; exact validation-MSE ties SHALL select the earliest epoch. Test labels SHALL NOT enter fitting or checkpoint selection, and test evaluation SHALL follow frozen selection. Development model seeds SHALL be 0,1,2 and final seeds 0..4; these profiles SHALL NOT automatically schedule runs or authorize formal evidence. No test-driven search, branch-specific budget, early stopping, clipping or preprocessing search SHALL be added.

#### Scenario: Complete budget and MSE winner
- **WHEN** a development fixture execution completes and validation MAE favors a different epoch from validation MSE
- **THEN** history has exactly 200 epochs, each covers 19*N*3 loss elements, the validation-MSE winner is saved with its parameters, and test performance does not change that choice

#### Scenario: Test isolation and ties
- **WHEN** only test targets change or validation MSE scores tie exactly across epochs
- **THEN** trained epoch candidates and validation scores remain unchanged, selection uses the earliest MSE minimum, and test labels never reach the training/selection interface

### Requirement: Metrics and references use common P01 masks and arithmetic
All methods SHALL share the same canonical training-27-month activity masks and the same original published-graph P01 nonself-neighbor coverage mask; shuffled evaluation SHALL NOT redefine those groups. Activity SHALL use zero, (0,1/3], (1/3,2/3], (2/3,1] nonzero fractions over 2021-01..2023-03. Reports SHALL include original-unit overall MAE/MSE/RMSE, per-window/horizon/context/activity/neighbor results, negative-prediction ratio, counts, training-zero/constant diagnostics and equal-weight nonempty activity MAE. Overall RMSE SHALL be sqrt of MSE over all elements, with main target-month multiplicities 1/2/3/3/2/1 retained. Empty groups SHALL have explicit empty status, null metrics and zero counts. The five P01 naive methods, their validation MSE table and table-order tie decisions SHALL be preserved; published-data NaiveRef SHALL remain LastValue and inconsistent reference/data identity SHALL fail explicitly. Zero-reference gains SHALL be unavailable with a reason.

#### Scenario: Masks and empty group
- **WHEN** self, graph and all shuffled graphs evaluate a fixture with activity-boundary nodes and an empty group
- **THEN** every saved evaluation mask matches the P01 oracle elementwise, boundary membership/counts are exact, empty metrics are null with zero counts, and balanced MAE excludes that group

#### Scenario: Independent metric oracle
- **WHEN** a fixture has negative predictions and unequal window MSE values
- **THEN** float64 error reductions, negative ratios, all grouped counts and frozen-reference gains match an independent oracle, and overall RMSE is not the mean of window RMSEs

### Requirement: Each execution saves complete recoverable evidence
Each execution SHALL reserve an exclusive non-overwriting directory and record purpose/task, code commit and relevant uncommitted execution content, scientific/policy versions and locatable contents, demand/graph content identity, parsed configuration, dependencies/environment/CPU/thread settings, exact commands/steps, stage timings/peak memory and terminal status. Completed evidence SHALL include predictions and labels with canonical node/time/split identity, fixed masks, selected numerical parameters and actual parameter counts, explicit raw-count preprocessing identity, complete training/validation selection history and reasons, graph/shuffle audits and all reported metrics. Numeric arrays SHALL load without Python-object pickle or graph libraries. Committed sources SHALL be located by fixed commit/path; only necessary dirty/untracked execution content SHALL be captured, excluding unrelated research records/tests/caches. Failures and interruptions SHALL retain available evidence and an explicit failed/interrupted/unfinished state, never fabricated success.

#### Scenario: Complete saved execution
- **WHEN** a small development fixture completes
- **THEN** all required provenance/configuration/status/identity/graph/model/array/mask/history/measurement fields exist, validation and test arrays have shapes [1,N,3] and [4,N,3], and all reported metrics are recoverable from saved numeric evidence

#### Scenario: Collision or interrupted execution
- **WHEN** the same run ID is requested again or a worker fails/is interrupted
- **THEN** existing output is not replaced and available evidence retains the actual failure stage and terminal state or detectable unfinished state

### Requirement: Saved-only checks are read-only and decisive
Recomputation SHALL use only saved evidence, without source demand/graph reads, training or model forward calls, and SHALL recompute every reported validation/test aggregate, grouping, count and relative comparison in the metrics output. Training-history score rows SHALL be retained and checked for structural and selection consistency; recomputation SHALL NOT claim to independently recover every epoch's score without its predictions. Numeric metric agreement SHALL use normalized tolerance `abs(a-b)/max(1,abs(a),abs(b))<=1e-12`; identity, schema, dimensions, mask values, null/empty status and counts SHALL agree exactly. Missing, contradictory, nonfinite or damaged evidence SHALL fail. Recompute, repeat comparison and shuffled summary SHALL produce only one exclusive requested JSON report containing input identities, checker source identity, exact command, tolerances, status and decisive differences; inputs SHALL remain bytewise unchanged. Reports SHALL NOT overwrite existing files or be placed inside any input directory.

#### Scenario: Source and model access disabled
- **WHEN** a completed fixture is recomputed with source-data loading, training and forward functions disabled
- **THEN** every reported metric/gain is reproduced within 1e-12, only the requested report is written and input file bytes remain unchanged

#### Scenario: Corrupt saved evidence
- **WHEN** a label shape, node hash, mask, window role, metric key/count/null status or saved finite value is corrupted
- **THEN** the check returns nonzero and a safe failure report identifies the discrepancy without repairing inputs or using source data

### Requirement: Same-seed CPU repetition meets the protocol tolerance
Repeat comparison SHALL require two distinct independent executions with the same dataset/content/node/graph identity, method, model and shuffle seeds, protocol/policy contents, resolved training configuration, code identity and CPU execution environment. Differences only in run ID, output location, timestamps and measured costs SHALL be permitted as execution metadata. It SHALL compute `abs(MAE_a-MAE_b)/max(1,MAE_a,MAE_b)` and require <=1e-6, record prediction maximum absolute difference, and check elementwise normalized prediction differences and other error metrics at tolerance <=1e-6 using max(1,abs(a),abs(b)) near zero. Nonfinite values or identity/condition mismatches SHALL fail even when aggregate MAE happens to agree. Software-readiness checks SHALL exercise at least two same-seed CPU executions per method on fixtures; later scientific comparisons retain the protocol's repeat requirements.

#### Scenario: Independent repeated fixture
- **WHEN** two fresh same-seed CPU fixture executions have matching conditions
- **THEN** their normalized MAE difference is <=1e-6 and the report records prediction maximum absolute difference and full numerical agreement checks

#### Scenario: Mismatch cannot pass by identical predictions
- **WHEN** dataset/content, method, model seed, shuffle seed, graph, protocol contents, masks, code or environment differ
- **THEN** comparison rejects the mismatched condition explicitly even if predictions and MAE are identical

### Requirement: Explicit execution axes and purpose protect development outputs
The new public entry SHALL expose method self|graph|shuffled, model seed, and a separate shuffle seed required only for shuffled and limited to 0/1/2. Switching methods/seeds SHALL NOT mutate module global constants. Purpose SHALL default to development with output in ignored scratch/graph-value-skeleton or a validated ignored/temporary root; no development execution or check SHALL write research/runs or other research records, old runs, packages or archives, including through root overrides, symlinks or path traversal. Explicit formal purpose SHALL resolve fresh research/runs/<run-id> output, require separate research authorization before use, and SHALL NOT be run by implementation or independent verification. Purpose SHALL NOT alter scientific computation. Both purposes SHALL refuse overwrites.

#### Scenario: Default development invocation
- **WHEN** a valid fixture request omits purpose
- **THEN** labeled development evidence is written only under ignored scratch or a validated temporary root, with no formal directory created

#### Scenario: Invalid axes or unsafe destination
- **WHEN** self/graph is given a shuffle seed, shuffled lacks one, an unsupported seed/purpose is supplied, or development output resolves into research/runs through a symlink or override
- **THEN** the request fails before directory reservation or training

#### Scenario: Interleaved methods in one process
- **WHEN** valid configurations for self, graph and shuffled are resolved alternately
- **THEN** each retains its explicit method and two seed identities and P01 module constants remain unchanged

### Requirement: Pure CPU runtime and existing graph-free compatibility are maintained
The new entry SHALL run training, graph aggregation, shuffling and checks on CPU without GPU, CUDA-only packages, torch-scatter/torch-sparse, PyG or DGL. It SHALL document and record an exact reproducible runtime and commands. Existing nograph-baseline-entry SHALL retain its NumPy/pandas/PyArrow-only imports, help, tests, predictions, public behavior and saved formats without requiring torch; existing graph preparation SHALL retain its weighted export semantics. Software tests SHALL use small fixtures independent of full repository datasets.

#### Scenario: CPU-only complete path
- **WHEN** the pinned CPU runtime executes the fixture suite with GPU and graph extension imports unavailable
- **THEN** all three methods, complete training/selection, shuffling and saved-result checks run without those packages and record the actual runtime versions

#### Scenario: Existing no-torch regression
- **WHEN** the existing no-graph entry and tests execute in their original environment without torch
- **THEN** imports/help and fixture results remain compatible and no new graph dependency is required

### Requirement: Costs and readiness remain separate from scientific acceptance
Every execution SHALL record measured data/graph reading, shuffling, training/validation, selected inference and total elapsed times, process peak resident memory with native and byte units/method/scope, environment and input dimensions. Synthetic fixture and real-data development measurements SHALL be labeled distinctly and SHALL NOT be presented as formal scientific evidence or unmeasured performance promises. Usage documentation SHALL be limited to a new README entry chapter, including development/check commands, explicit formal authorization and published-graph time limitations. Implementation readiness SHALL NOT change scientific versions, split/evaluation/selection rules, §6.2 thresholds or frozen configurations, initiate formal research runs, update research records, mutate historical evidence, or declare predictive benefit. A later archived independent `Verdict: PASS` with Verification Basis matching the current implementation SHALL be evidence for a separate research-side implementation acceptance decision.

#### Scenario: Measured development cost
- **WHEN** a fixture or optionally authorized real-data development smoke completes in a fresh CPU worker
- **THEN** its own durations and peak RSS with correct units and input identity are saved, with no inferred formal performance or graph-benefit claim

#### Scenario: Software readiness handoff
- **WHEN** implementation checks and later independent verification complete
- **THEN** their evidence maps to the design acceptance checklist, while research acceptance, formal experiments and the unchanged §6.2 benefit decision remain separate

### Requirement: Shuffle work is finite and versioned without reducing the swap target
Every nonempty context SHALL complete exactly `10E` accepted swaps within a finite, versioned attempt ceiling frozen before formal comparison. Proposals SHALL remain uniform ordered edge-index pairs consumed sequentially against the evolving graph. Existing degree, identity, locality, uniqueness, changed-edge and seed contracts SHALL remain in force. Reaching the ceiling SHALL fail explicitly.

#### Scenario: Larger finite budget completes a previously exhausted control
- **WHEN** a swappable control exceeds the historical attempt ceiling but finishes within the selected new ceiling
- **THEN** it records the new algorithm/budget identity, exactly `10E` accepted swaps, actual attempts and all preserved invariants

#### Scenario: Optimization preserves sequential semantics
- **WHEN** batched proposals and an independent scalar reference consume the same ordered proposal stream on a fixture
- **THEN** accepted/rejected decisions, counts and canonical final edges agree exactly; proposals are never applied simultaneously against stale adjacency

### Requirement: Shuffle failures retain decisive progress and rejection evidence
Graph preparation and failed model runs SHALL retain source/node/seed/version identities, completed-context audits and the failing context's attempts, accepted count, target, ceiling, rejection counts, elapsed time and reason. Progress SHALL be observable during long contexts. Failure or cancellation SHALL preserve a non-success status and SHALL NOT publish a reusable completed artifact.

#### Scenario: Budget exhaustion is diagnosable
- **WHEN** a context exhausts its attempt budget
- **THEN** the process returns nonzero, rejection counts plus accepted count equal attempted proposals, previous contexts remain inspectable and no model training starts

#### Scenario: User interruption preserves the recovery point
- **WHEN** graph preparation is interrupted between progress checkpoints
- **THEN** the latest checkpoint and interrupted or detectably unfinished status remain available, and later training rejects that artifact

### Requirement: Shuffled graphs can be prepared and checked without model training
The public entry SHALL support graph-only preparation for one dataset and shuffle seed and read-only checking of a saved prepared artifact. Preparation SHALL use development output protections and refuse overwrites. Artifacts SHALL contain canonical node keys, source/result edges, complete shuffle audit, generation provenance and byte checksums in non-pickle numeric/JSON formats. Preparation and checking SHALL NOT initialize, fit or evaluate a model.

#### Scenario: Prepare before scheduling models
- **WHEN** preparation is requested for a valid published dataset and shuffle seed
- **THEN** it creates a fresh development artifact with all graph identities and invariants checked, with no training history, model checkpoint or formal run directory

#### Scenario: Saved artifact corruption fails read-only checking
- **WHEN** a numeric array, audit count, checksum, dimension or identity is missing or inconsistent
- **THEN** checking returns nonzero, writes only one exclusive external report and leaves all artifact bytes unchanged

### Requirement: Prepared shuffle reuse requires exact scientific and graph identity
A shuffled model run SHALL optionally consume a completed prepared artifact only after validating checksums, canonical source/node identities, dataset, shuffle seed, supported generator version/budget and graph invariants against its current inputs. Incompatible or damaged artifacts SHALL fail before training without regeneration or fallback. Self/graph SHALL reject this option. Artifact location and cache-hit status SHALL be execution metadata.

#### Scenario: Reuse across independently trained model runs
- **WHEN** different model seeds or repetition IDs request the same compatible prepared graph
- **THEN** they use identical message edges while each independently initializes and completes its own frozen 200-epoch training; all three shuffled members are still required

#### Scenario: Mismatch cannot silently regenerate
- **WHEN** a valid artifact has a different source/node identity, dataset, shuffle seed or unsupported generator version
- **THEN** execution fails before training, retaining the reason and leaving the supplied artifact unchanged

### Requirement: Reused graphs leave self-contained and version-aware saved evidence
Completed runs using prepared graphs SHALL retain sufficient graph arrays and audits for existing saved-only checks without access to the preparation directory. Cached and freshly generated graphs with identical semantic identities SHALL satisfy the existing repeat comparison. Checkers SHALL validate historical `dds-v1` evidence under its recorded `10E`/`100E` contract, new evidence under its own frozen contract, and reject unknown versions.

#### Scenario: Remove external preparation after a run
- **WHEN** the preparation directory becomes unavailable after a completed fixture run
- **THEN** saved-only recomputation succeeds without external graph access or model forward calls

#### Scenario: Version dispatch is strict
- **WHEN** saved v1 and new-version fixture evidence are checked
- **THEN** each is validated against its own budget and audit rules; an altered budget, unsupported version or damaged audit fails rather than being relabeled

### Requirement: Published shuffle readiness includes all graph seeds and regeneration
Readiness for resuming T002 SHALL include development evidence for all `r0/region/r2` × shuffle seeds `0/1/2`, each independently regenerated with matching canonical result hashes. Reports SHALL retain per-context invariants, attempts, accepted/rejection counts, edge change/overlap, timings and source/result identities. Any failed member SHALL make readiness incomplete. This evidence SHALL NOT claim uniform mixing or predictive benefit.

#### Scenario: Full published graph preflight
- **WHEN** all nine graphs and their independent regenerations complete under the same frozen version
- **THEN** a manifest identifies every member, matching regeneration hashes and decisive invariant checks, with measured costs labeled development graph-only

#### Scenario: Partial matrix cannot authorize a successful handoff
- **WHEN** any published graph member fails, is interrupted or lacks reproducibility evidence
- **THEN** readiness remains failed or incomplete, the failed evidence is retained, and the workflow does not start formal model training

### Requirement: Durable validated epoch checkpoints
Training SHALL publish an integrity-checked, non-pickle checkpoint after each fully validated epoch, preserving current model, optimizer, RNG, complete history, best selection state and cumulative training timings. An incomplete write SHALL leave the previous committed checkpoint recoverable.

#### Scenario: Interruption during checkpoint publication
- **WHEN** a process stops before publishing its next checkpoint
- **THEN** the previous committed generation remains loadable and the partial generation is not treated as committed

#### Scenario: Complete training state
- **WHEN** a validated epoch is committed
- **THEN** recovery includes current and selected weights, Adam slots and step counters, Python/NumPy/CPU torch RNG state, history and elapsed training and validation time

### Requirement: Explicit identity checked continuation
Resume SHALL be explicit, target a fresh run identity and validate checkpoint integrity, schema, source, runtime, scientific configuration, inputs, graph, masks and computation layout before training. It SHALL preserve the source run and record self-contained checkpoint lineage. Missing or incompatible state SHALL fail without silently starting over.

#### Scenario: Compatible interrupted run
- **WHEN** an explicit valid checkpoint is resumed into an unused run identity
- **THEN** training starts at the next epoch with restored state and leaves source artifacts unchanged

#### Scenario: Invalid recovery input
- **WHEN** checkpoint bytes are corrupt, state is malformed or any required identity differs
- **THEN** recovery fails before an optimizer update and records the reason

#### Scenario: No historical checkpoint
- **WHEN** the old interrupted r2 run is considered for continuation
- **THEN** it is reported as non-resumable and any replacement starts under a fresh identity

### Requirement: Continuation preserves scientific execution
Continuation SHALL preserve the original total 200 epochs, optimizer update order, earliest exact-tie validation selection and test isolation. Continuous and interrupted execution SHALL agree within existing repeat tolerance, and saved-only recomputation SHALL retain its existing tolerance. Continuations sharing training ancestry SHALL not count as independent repetitions.

#### Scenario: Interrupted and continuous comparison
- **WHEN** identical fixture fits run continuously and across one or more process interruptions
- **THEN** final parameters, optimizer state, epoch history, selected epoch and predictions agree within normalized 1e-6 and saved-only checks pass at 1e-12

#### Scenario: Last epoch recovery
- **WHEN** a valid epoch-200 checkpoint is recovered after finalization was interrupted
- **THEN** final artifacts are produced without executing epoch 201 or replaying an update

#### Scenario: Shared ancestry repetition
- **WHEN** a comparison attempts to count a resumed branch and its ancestor or sibling as independent repetitions
- **THEN** the independence check rejects the pair

### Requirement: Measured training progress
Runs SHALL expose completed validated epochs, committed checkpoint identity, cumulative timings, recent epoch duration and a remaining-time estimate based on measured work. Progress SHALL be distinguishable from successful completion; unavailable estimates SHALL be explicit and process downtime SHALL not count as training time.

#### Scenario: Progress before finalization
- **WHEN** an epoch checkpoint commits while training remains incomplete
- **THEN** progress identifies that epoch and checkpoint without publishing successful completion

#### Scenario: Resumed timing
- **WHEN** a fit resumes after machine downtime
- **THEN** reported training time accumulates actual work across attempts, reports attempt wall time separately and revises the estimate from observed epochs

### Requirement: Auditable r2 batch recovery
The r2 controller SHALL map each original matrix slot to fresh attempts, reuse completed fits only after validation, resume only eligible checkpoints and preserve old evidence. It SHALL prevent concurrent ownership, pause on failure and publish completion only after all 30 fits and 51 original checks succeed.

#### Scenario: Restart after reboot
- **WHEN** explicit recovery starts with stale process records and incomplete attempts
- **THEN** live ownership is checked, completed fits are validated and eligible continuations or fresh replacements receive new identities and recorded lineage

#### Scenario: Failed recovery or check
- **WHEN** a fit, recovery validation or required check fails
- **THEN** further scheduling pauses with an actionable diagnostic and no completion or success publication

### Requirement: Checkpoint rollout readiness
Checkpoint recovery SHALL pass independent verification before formal r2 restart. Existing successful historical runs without checkpoint metadata SHALL remain readable by saved-only checks; new recovery metadata SHALL not change scientific condition identity or prepared graph semantics.

#### Scenario: Independent readiness gate
- **WHEN** formal execution is prepared after this change
- **THEN** current independent verification covers recovery equivalence, invalid-state rejection and controller restart behavior before training starts

#### Scenario: Historical evidence compatibility
- **WHEN** existing successful pre-checkpoint evidence is checked
- **THEN** saved-only validation remains supported without inventing missing checkpoint state
