# Spec Delta

## ADDED Requirements

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
