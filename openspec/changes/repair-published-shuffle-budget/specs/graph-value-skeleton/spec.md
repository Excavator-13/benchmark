# Spec Delta

## ADDED Requirements

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
