## MODIFIED Requirements

### Requirement: Protocol-isolated recurrent training

The entry SHALL support GRU and LSTM for r0/count, region/count and r2/count under `P2-effective-training-L6-H3-v2`, using `research/phases/P02/protocol-v2.md` and its explicitly inherited immutable v1 sections 1–7 / P01 definitions as the scientific authority. The current formal entry SHALL use v2 by default and SHALL NOT silently reinterpret v1 artifacts as v2. Scientific version and the content identities of both v2 and its inherited v1 document SHALL be bound into effective conditions, provenance and recovery checks. It SHALL preserve the legacy runners and T009 behavior. It SHALL validate finite nonnegative observations, exactly 36 continuous months from 2021-01 through 2023-12, unique context-qualified integer node keys and canonical ascending order before fitting. It SHALL retain node, month, dataset and demand-content identities. Unsupported models, datasets, modes or protocol settings SHALL fail explicitly rather than silently changing the protocol.

#### Scenario: Canonical identity across supported schemas
- **WHEN** temporary r0, region or r2 Parquet rows arrive out of order with skills repeated across contexts
- **THEN** the entry preserves distinct context-qualified nodes, sorts them canonically and aligns observations, predictions and saved keys

#### Scenario: Invalid input fails before fitting
- **WHEN** a model or mode is unsupported, keys are duplicated, months are missing or values are negative or nonfinite
- **THEN** the entry reports the offending condition before fitting or publishing a successful checkpoint

#### Scenario: Inherited protocol identity changes
- **WHEN** either the v2 protocol or its inherited v1 document is missing or differs from the bound execution identity
- **THEN** formal preflight or recovery rejects the mismatch explicitly rather than publishing complete v2 evidence


### Requirement: Full-window optimization and immutable checkpoint selection

Each protocol fit SHALL perform 200 epochs (3,800 updates) with 19 updates per epoch in training-start order 0..18, accumulating all node/horizon errors for a complete window with denominator `N*3` before one optimizer step. It SHALL use the protocol's Adam defaults, selected learning rate and complete-gradient L2 clipping at 1, and record pre-clip norms, clipping events and update counts. It SHALL evaluate initialization and every epoch on validation original-unit MSE, selecting only step>0 and the earliest exact tie. Selected model and optimizer state SHALL be immutable snapshots corresponding to the same epoch; subsequent updates SHALL NOT alter them. Fixed-parameter reevaluation of the restored best checkpoint SHALL reproduce its saved validation metrics within documented CPU tolerance no greater than 1e-6. Shorter fixture budgets SHALL be labeled development overrides and SHALL NOT qualify as complete protocol trajectories.

#### Scenario: Best epoch precedes final epoch
- **WHEN** a controlled trajectory improves early and subsequently worsens
- **THEN** final restoration and saved best weights reproduce the early checkpoint, its matching optimizer state and validation score rather than the last epoch

#### Scenario: Uneven chunks preserve global weighting
- **WHEN** node counts do not divide the configured chunk size and contexts differ in size
- **THEN** an update agrees with the complete-window global-mean reference within the declared tolerance, with exactly one step per window and clipping after all chunks

#### Scenario: A 100-epoch invocation cannot pass v2 formal controls
- **WHEN** a request supplies 100 epochs under formal purpose or a saved trajectory stops at epoch 100
- **THEN** the request is rejected or the saved trajectory is incomplete for v2, and it cannot unlock final testing


### Requirement: Learning diagnostics implement the existing gates

The entry SHALL save fixed-parameter original-unit train/validation scores at initialization, epochs 10/50/100/200 and the selected checkpoint, distinguish online mixed-parameter loss from fixed-checkpoint MSE, and retain complete per-epoch validation histories. A saved-evidence diagnostic operation SHALL implement v2 section 2 and inherited v1 section 5 without changing its thresholds: finite complete trajectories; at least 2/3 a seeds with train-MSE reduction >=10% and validation-MSE reduction >=5% from initialization; at least 2/3 with validation-MAE improvement >=5% over Zero; at least 2/3 with `(b160-b200)/max(1e-12,b160) <= 1%`, including the both-zero rule; and independent same-condition a/b validation MAE difference `abs(a-b)/max(1,a,b) <= 1e-6` for every required pair. It SHALL require exactly the ordered 200-epoch trajectory and report the 160/200 boundaries with their corresponding best-validation minima, per-gate evidence, maximum prediction differences, explicit missing/incompatible evidence and a computed `learning_ready` only when all requirements are satisfied. Zero denominators SHALL be reported as unavailable/all-zero diagnostics, not as a passed improvement gate.

Input/target quantiles, hidden-output saturation fraction `abs(h)>0.99`, prediction scale/negative fraction and validation-input-zeroing changes SHALL be recorded as diagnostics without selecting configurations. Zero, LastValue and compatible validation-selected Ridge validation scores SHALL be reported alongside neural scores; baseline compatibility SHALL include node, month, source-data, preprocessing/selection and split identities. Missing compatible evidence SHALL remain incomplete. Computed readiness SHALL NOT declare research acceptance, graph benefit or full convergence.

#### Scenario: Gates pass and fail independently
- **WHEN** saved fixtures place each threshold just below, at or above its limit
- **THEN** diagnostics report the exact per-seed and aggregate outcomes, including failing budget/repetition gates despite favorable test-free model scores

#### Scenario: Incomplete or all-zero evidence
- **WHEN** histories, a/b pairs or compatible baselines are missing, or Zero validation MAE is zero
- **THEN** diagnostics identify the missing/all-zero condition and do not report readiness as passed or remove an unfavorable seed

#### Scenario: Old and new tail intervals disagree
- **WHEN** a 200-epoch saved fixture passes the 80-to-100 comparison but fails the 160-to-200 comparison, or vice versa
- **THEN** readiness uses only the frozen v2 160-to-200 interval, reports the correct minima and retains the same 1% and 2/3 thresholds


### Requirement: Auditable and independently recomputable outputs

Each execution SHALL reserve a fresh non-overwriting output identity, record scientific and artifact-format versions, exact command/configuration, seed/repetition/candidate roles, source commit plus recoverable relevant runtime differences, source/protocol content identities including both v2 and its inherited v1 document, demand identity, preprocessing, canonical keys, split/month identities, machine/dependency/CPU/thread settings, status and linked artifacts. Comparison mode SHALL preserve the actual data source rather than substituting an array placeholder. Validation and final test predictions/labels, training-fixed activity and context-qualified neighbor masks with source provenance, selected parameters and all candidate validation scores/reasons SHALL suffice for independent recomputation. Raw original-unit MAE/MSE/RMSE, window/horizon/context/activity/neighbor results, sample counts, negative ratios and separately labeled nonnegative-clipped diagnostics SHALL follow the inherited P01 definitions. Missing coverage SHALL NOT silently become an all-isolated mask. Failed/incomplete executions SHALL retain status and available evidence and SHALL NOT be dropped from summaries; complete comparisons SHALL report per-seed metrics and mean/sample SD.

#### Scenario: Source data are unavailable to a reviewer
- **WHEN** a completed fixture result is checked after demand/graph files and model-fitting interfaces become inaccessible
- **THEN** saved arrays, keys, masks and metadata still reproduce every reported metric, including all four test windows and group counts

#### Scenario: Collision or failed seed
- **WHEN** an output already exists or one requested seed fails
- **THEN** existing artifacts are preserved, the collision is rejected, and summaries retain the failed/incomplete seed without claiming a complete successful comparison

#### Scenario: Historical evidence remains historical
- **WHEN** v2 outputs are published alongside existing v1 runs and frozen reports
- **THEN** existing files remain unchanged, new identities identify v2 explicitly, and no old scores or partial repeats are promoted into a complete v2 comparison


### Requirement: Saved-only checks reject incompatible evidence

Recompute, same-seed compare and readiness diagnostics SHALL read only saved evidence and write one exclusive compact JSON report to an explicit destination outside input directories. Reports SHALL identify consumed inputs, checker identity, tolerances, decisive differences and pass/fail/incomplete status; checks SHALL NOT retrain, read original demand/graph data or modify inputs. Same-seed comparison SHALL reject differing scientific versions, inherited protocol identities, data contents, canonical keys, split/protocol content, model, seed, selected learning rate, effective configuration or execution conditions even when predictions happen to match. After final reporting it SHALL also compare test predictions and normalized test MAE with the same repetition bound. A usable destination SHALL retain a failure report and a nonzero exit on failed/incomplete checks.

A saved-only operation that does not support a historical scientific version SHALL return an explicit non-success with an actionable version incompatibility and the original runner reference. It SHALL NOT infer the current protocol from matching shapes, epoch count or equal predictions, overwrite the old verdict, or upgrade v1 evidence into v2. Mixed-version selection, diagnostics and formal reporting SHALL fail before reading test observations.

#### Scenario: Identical outputs conceal a condition mismatch
- **WHEN** saved runs have identical predictions but different seeds, data hashes or protocol contents
- **THEN** same-seed comparison fails with the specific mismatch rather than accepting numerical equality

#### Scenario: Checks cannot overwrite inputs
- **WHEN** a check targets an existing report or any path inside a consumed run
- **THEN** it rejects the destination without changing the report or input evidence

#### Scenario: Equal arrays from different scientific versions
- **WHEN** v1 and v2 evidence contains identical saved predictions
- **THEN** mixed-version comparison or readiness refuses the scientific mismatch without mutating either input or treating numerical equality as compatibility


### Requirement: Resource preflight and cost limits are enforceable

Before a protocol block runs, machine-readable preflight SHALL cover source/protocol/data/environment identities, CPU-only deterministic single-thread settings, dependencies, one-worker/conflicting-controller checks, fresh output/recovery identity and resource availability. It SHALL implement P02 section 6: available memory >=6 GiB, output-disk free >=5 GiB, worker-process-tree RSS sampled at intervals <=5 s with an 8 GiB stopping line, initial 10-epoch cost sample <=15 min, fit <=60 min and cumulative active batch <=12 h including failed/interrupted/replayed work. A persistent ledger SHALL distinguish measured and estimated durations and retain cumulative cost across recoveries. For v2 the conservative single-fit estimate SHALL be `1.3*(setup+2*200*t)`, where `t` is the median complete-epoch time over epochs 6..10. The same candidate trajectory SHALL continue after its sample rather than restarting a duplicate fit. Per-block `cost.json` SHALL use epochs 6..10's measured complete-epoch median and the specified conservative estimate/reserve, remaining fit count and spent budget; insufficient samples, failed monitors or exceeded limits SHALL pause the block. Different model/dataset blocks SHALL require their own measurement; no automatic matrix expansion is permitted.

Batch continuation across the scientific revision SHALL preserve the existing ledger ID, batch ID and all measured/replayed entries. The entry SHALL expose an explicit operation to add a positive, finite, reasoned conservative budget debit with a stable debit identity to an existing ledger. Repeating the same debit identity/value SHALL be idempotent; changing its value/reason or decreasing/removing a published debit SHALL be rejected. Such debits SHALL reduce remaining cumulative budget for preflight, fit/resume, cost projections and live saved-evidence stages, while remaining separately labeled from measured execution and nonbinding estimated forecasts. Unknown entry kinds, malformed or negative/nonfinite amounts SHALL fail closed. Legacy ledgers without debits SHALL remain loadable without regenerating their identities. Standalone preflight with a supplied existing ledger SHALL record its actual elapsed execution once; internal fit preflight SHALL NOT double-charge time already included in its controller accounting. Helpers SHALL have a documented measured-cost recording interface.

The current research continuation SHALL be able to register the v2 protocol's single 900-second preparation debit without modifying historical run inputs. Software fixtures SHALL demonstrate carry-forward of prior costs and exhaustion by debit alone; software work SHALL NOT write the real research ledger.

#### Scenario: Controlled resource or time breach
- **WHEN** an injected clock/resource sampler crosses a limit or monitoring fails
- **THEN** execution stops the affected block, preserves the last complete recovery point and records the reason and consumed budget instead of proceeding

#### Scenario: A sample resumes without double fitting
- **WHEN** a candidate completes its 10-epoch sample within the limits and passes the cost check
- **THEN** continuation retains the same trajectory and already-consumed budget, and estimates for unmeasured encoders/datasets remain unknown

#### Scenario: Old spending and a conservative debit leave insufficient budget
- **WHEN** an existing fixture ledger has prior v1 spending and a conservative preparation debit makes the proposed v2 work exceed 12 hours
- **THEN** the new work pauses or fails before training/test access, preserves ledger identity and old entries, and reports measured time and debited budget separately

#### Scenario: Debit registration is repeated or malformed
- **WHEN** a stable debit is registered twice or a caller tries to change it, use an unknown kind, or supply a negative or nonfinite amount
- **THEN** an identical registration does not double-charge and every invalid mutation is rejected without changing existing ledger entries


### Requirement: Atomic recovery is separate from best-model selection

The entry SHALL publish complete epoch-boundary recovery state atomically, containing last model/optimizer, preprocessing, configuration/data/source/protocol identity, completed epoch/update and next-window position, random states, history, best snapshot and cumulative ledger references. Best-model reporting SHALL use the independent best snapshot. Resume SHALL use a new execution identity linked to the parent, validate matching effective conditions and remaining budget, and restart only from the last complete epoch; partial-epoch replay SHALL count toward cost. Old, corrupt or mismatched checkpoints SHALL fail explicitly without overwriting the parent or silently restarting. Atomic publication failures SHALL preserve the previous valid recovery state and incomplete status.

Recovery SHALL require the v2 scientific version and both bound protocol documents; a v1 checkpoint SHALL NOT be extended or relabeled as a v2 trajectory. Repeated a/b evidence SHALL be newly initialized under v2, with only interrupted same-v2 trajectories eligible for parent-linked recovery. Budget debits SHALL remain effective across recovery and controller termination.

#### Scenario: Interrupted execution matches uninterrupted training
- **WHEN** a short deterministic fixture is interrupted inside an epoch and resumed from its preceding completed epoch
- **THEN** final parameters, best selection and validation outputs agree with uninterrupted execution within tolerance, with the replay cost retained

#### Scenario: Legacy or damaged checkpoint
- **WHEN** recovery requests a legacy checkpoint missing identity/random/position state or a truncated new checkpoint
- **THEN** it fails with an actionable incompatibility/corruption reason and leaves all existing evidence unchanged

#### Scenario: Cross-version continuation is requested
- **WHEN** a v1 100-epoch checkpoint is passed to the v2 resume operation
- **THEN** it rejects the scientific incompatibility before training, retains both parent evidence and cumulative ledger identity, and explains that v2 requires a fresh initialized trajectory

