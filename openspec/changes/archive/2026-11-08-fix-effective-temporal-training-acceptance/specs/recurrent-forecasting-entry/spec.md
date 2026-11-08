## Purpose

Provide a protocol-isolated CPU GRU/LSTM entry whose selected weights, rolling-window evaluation, diagnostic evidence, saved results and recovery state agree with the existing P02 effective-training protocol. Establish software readiness through fixtures while leaving real-data execution and scientific acceptance to research work.

## ADDED Requirements

### Requirement: Protocol-isolated recurrent training

The entry SHALL support GRU and LSTM for r0/count, region/count and r2/count under `P2-effective-training-L6-H3-v1`, using P02 protocol sections 1–7 and its inherited P01 definitions as the scientific authority. It SHALL preserve the legacy runners and T009 behavior. It SHALL validate finite nonnegative observations, exactly 36 continuous months from 2021-01 through 2023-12, unique context-qualified integer node keys and canonical ascending order before fitting. It SHALL retain node, month, dataset and demand-content identities. Unsupported models, datasets, modes or protocol settings SHALL fail explicitly rather than silently changing the protocol.

#### Scenario: Canonical identity across supported schemas
- **WHEN** temporary r0, region or r2 Parquet rows arrive out of order with skills repeated across contexts
- **THEN** the entry preserves distinct context-qualified nodes, sorts them canonically and aligns observations, predictions and saved keys

#### Scenario: Invalid input fails before fitting
- **WHEN** a model or mode is unsupported, keys are duplicated, months are missing or values are negative or nonfinite
- **THEN** the entry reports the offending condition before fitting or publishing a successful checkpoint

### Requirement: Training-only RMS preprocessing

The entry SHALL compute one scalar `max(1, sqrt(sum(y^2)/(N*27)))` in float64 over all nodes and the 27 unique training observation months only. It SHALL freeze and record that scale and its input identity, divide inputs and targets by it, use CPU float32 model arithmetic and inverse-transform predictions without changing node or horizon loss weights. Node/window recurrent states SHALL reset independently. Per-node normalization or validation/test-dependent scaling SHALL NOT substitute for this definition.

#### Scenario: Held-out observations change
- **WHEN** validation/test observations change while training observations and seed remain fixed
- **THEN** RMS, initialized parameters and training-only update trajectories remain unchanged

#### Scenario: Constant zero and independent state
- **WHEN** the fixture contains all-zero training observations and repeated identical windows
- **THEN** scale is 1, numerical outputs remain finite and each window prediction is independent of prior window evaluation order

### Requirement: Full-window optimization and immutable checkpoint selection

Each protocol fit SHALL perform 100 epochs with 19 updates per epoch in training-start order 0..18, accumulating all node/horizon errors for a complete window with denominator `N*3` before one optimizer step. It SHALL use the protocol's Adam defaults, selected learning rate and complete-gradient L2 clipping at 1, and record pre-clip norms, clipping events and update counts. It SHALL evaluate initialization and every epoch on validation original-unit MSE, selecting only step>0 and the earliest exact tie. Selected model and optimizer state SHALL be immutable snapshots corresponding to the same epoch; subsequent updates SHALL NOT alter them. Fixed-parameter reevaluation of the restored best checkpoint SHALL reproduce its saved validation metrics within documented CPU tolerance no greater than 1e-6. Shorter fixture budgets SHALL be labeled development overrides and SHALL NOT qualify as complete protocol trajectories.

#### Scenario: Best epoch precedes final epoch
- **WHEN** a controlled trajectory improves early and subsequently worsens
- **THEN** final restoration and saved best weights reproduce the early checkpoint, its matching optimizer state and validation score rather than the last epoch

#### Scenario: Uneven chunks preserve global weighting
- **WHEN** node counts do not divide the configured chunk size and contexts differ in size
- **THEN** an update agrees with the complete-window global-mean reference within the declared tolerance, with exactly one step per window and clipping after all chunks

### Requirement: Selection and readiness precede four-window test reporting

The fitting interface SHALL receive only training and validation observations/targets. Learning-rate selection SHALL compare exactly `{1e-3, 3e-3}` on seed 0 by best validation original-unit MSE, prefer the smaller rate on an exact tie, retain both score records and reuse the winning seed-0 trajectory as repetition a. Independent a/b identities for seeds 0/1/2 SHALL be supported without treating different seeds as same-seed repetition or using b to choose configurations. No command SHALL automatically schedule the remaining real-data matrix.

Final testing SHALL be an explicit report operation after selection and required validation diagnostics/repetition evidence are frozen. It SHALL restore the selected weights, freeze parameters/preprocessing, evaluate all starts 24,25,26,27 with L6/H3 and then-observed true history, and save predictions/labels as `[4,N,3]`. Training starts SHALL be 0..18, validation 21 and omitted starts 19,20,22,23; test target-month multiplicities SHALL remain 1,2,3,3,2,1. Test scores SHALL NOT select learning rate, checkpoint, seed, clipping rule or readiness. Failed or incomplete validation gates SHALL prevent a successful formal test report.

#### Scenario: Test labels are inaccessible during selection
- **WHEN** fitting, learning-rate selection and validation readiness checks run with a test-access sentinel
- **THEN** none requests test labels, and only the later explicit report operation accesses them

#### Scenario: Four rolling windows have unequal errors
- **WHEN** a fixture gives different errors at test starts 24..27
- **THEN** saved starts, months and arrays cover every window, MAE/MSE aggregate all `4*N*3` elements and RMSE is the square root of aggregate MSE

#### Scenario: Learning-rate tie and missing repeat
- **WHEN** seed-0 candidate scores tie or validation repetition evidence is missing
- **THEN** the smaller learning rate wins the tie, and missing repetition remains explicitly incomplete and cannot unlock a formal test report

### Requirement: Learning diagnostics implement the existing gates

The entry SHALL save fixed-parameter original-unit train/validation scores at initialization, epochs 10/50/100 and the selected checkpoint, distinguish online mixed-parameter loss from fixed-checkpoint MSE, and retain complete per-epoch validation histories. A saved-evidence diagnostic operation SHALL implement P02 section 5 without changing its thresholds: finite complete trajectories; at least 2/3 a seeds with train-MSE reduction >=10% and validation-MSE reduction >=5% from initialization; at least 2/3 with validation-MAE improvement >=5% over Zero; at least 2/3 with `(b80-b100)/max(1e-12,b80) <= 1%`, including the both-zero rule; and independent same-condition a/b validation MAE difference `abs(a-b)/max(1,a,b) <= 1e-6` for every required pair. It SHALL report per-gate evidence, maximum prediction differences, explicit missing/incompatible evidence and a computed `learning_ready` only when all requirements are satisfied. Zero denominators SHALL be reported as unavailable/all-zero diagnostics, not as a passed improvement gate.

Input/target quantiles, hidden-output saturation fraction `abs(h)>0.99`, prediction scale/negative fraction and validation-input-zeroing changes SHALL be recorded as diagnostics without selecting configurations. Zero, LastValue and compatible validation-selected Ridge validation scores SHALL be reported alongside neural scores; baseline compatibility SHALL include node, month, source-data, preprocessing/selection and split identities. Missing compatible evidence SHALL remain incomplete. Computed readiness SHALL NOT declare research acceptance, graph benefit or full convergence.

#### Scenario: Gates pass and fail independently
- **WHEN** saved fixtures place each threshold just below, at or above its limit
- **THEN** diagnostics report the exact per-seed and aggregate outcomes, including failing budget/repetition gates despite favorable test-free model scores

#### Scenario: Incomplete or all-zero evidence
- **WHEN** histories, a/b pairs or compatible baselines are missing, or Zero validation MAE is zero
- **THEN** diagnostics identify the missing/all-zero condition and do not report readiness as passed or remove an unfavorable seed

### Requirement: Auditable and independently recomputable outputs

Each execution SHALL reserve a fresh non-overwriting output identity, record scientific and artifact-format versions, exact command/configuration, seed/repetition/candidate roles, source commit plus recoverable relevant runtime differences, source/protocol content identities, demand identity, preprocessing, canonical keys, split/month identities, machine/dependency/CPU/thread settings, status and linked artifacts. Comparison mode SHALL preserve the actual data source rather than substituting an array placeholder. Validation and final test predictions/labels, training-fixed activity and context-qualified neighbor masks with source provenance, selected parameters and all candidate validation scores/reasons SHALL suffice for independent recomputation. Raw original-unit MAE/MSE/RMSE, window/horizon/context/activity/neighbor results, sample counts, negative ratios and separately labeled nonnegative-clipped diagnostics SHALL follow the inherited P01 definitions. Missing coverage SHALL NOT silently become an all-isolated mask. Failed/incomplete executions SHALL retain status and available evidence and SHALL NOT be dropped from summaries; complete comparisons SHALL report per-seed metrics and mean/sample SD.

#### Scenario: Source data are unavailable to a reviewer
- **WHEN** a completed fixture result is checked after demand/graph files and model-fitting interfaces become inaccessible
- **THEN** saved arrays, keys, masks and metadata still reproduce every reported metric, including all four test windows and group counts

#### Scenario: Collision or failed seed
- **WHEN** an output already exists or one requested seed fails
- **THEN** existing artifacts are preserved, the collision is rejected, and summaries retain the failed/incomplete seed without claiming a complete successful comparison

### Requirement: Saved-only checks reject incompatible evidence

Recompute, same-seed compare and readiness diagnostics SHALL read only saved evidence and write one exclusive compact JSON report to an explicit destination outside input directories. Reports SHALL identify consumed inputs, checker identity, tolerances, decisive differences and pass/fail/incomplete status; checks SHALL NOT retrain, read original demand/graph data or modify inputs. Same-seed comparison SHALL reject differing data contents, canonical keys, split/protocol content, model, seed, selected learning rate, effective configuration or execution conditions even when predictions happen to match. After final reporting it SHALL also compare test predictions and normalized test MAE with the same repetition bound. A usable destination SHALL retain a failure report and a nonzero exit on failed/incomplete checks.

#### Scenario: Identical outputs conceal a condition mismatch
- **WHEN** saved runs have identical predictions but different seeds, data hashes or protocol contents
- **THEN** same-seed comparison fails with the specific mismatch rather than accepting numerical equality

#### Scenario: Checks cannot overwrite inputs
- **WHEN** a check targets an existing report or any path inside a consumed run
- **THEN** it rejects the destination without changing the report or input evidence

### Requirement: Resource preflight and cost limits are enforceable

Before a protocol block runs, machine-readable preflight SHALL cover source/protocol/data/environment identities, CPU-only deterministic single-thread settings, dependencies, one-worker/conflicting-controller checks, fresh output/recovery identity and resource availability. It SHALL implement P02 section 6: available memory >=6 GiB, output-disk free >=5 GiB, worker-process-tree RSS sampled at intervals <=5 s with an 8 GiB stopping line, initial 10-epoch cost sample <=15 min, fit <=60 min and cumulative active batch <=12 h including failed/interrupted/replayed work. A persistent ledger SHALL distinguish measured and estimated durations and retain cumulative cost across recoveries. The same candidate trajectory SHALL continue after its sample rather than restarting a duplicate fit. Per-block `cost.json` SHALL use epochs 6..10's measured complete-epoch median and the specified conservative estimate/reserve, remaining fit count and spent budget; insufficient samples, failed monitors or exceeded limits SHALL pause the block. Different model/dataset blocks SHALL require their own measurement; no automatic matrix expansion is permitted.

#### Scenario: Controlled resource or time breach
- **WHEN** an injected clock/resource sampler crosses a limit or monitoring fails
- **THEN** execution stops the affected block, preserves the last complete recovery point and records the reason and consumed budget instead of proceeding

#### Scenario: A sample resumes without double fitting
- **WHEN** a candidate completes its 10-epoch sample within the limits and passes the cost check
- **THEN** continuation retains the same trajectory and already-consumed budget, and estimates for unmeasured encoders/datasets remain unknown

### Requirement: Atomic recovery is separate from best-model selection

The entry SHALL publish complete epoch-boundary recovery state atomically, containing last model/optimizer, preprocessing, configuration/data/source/protocol identity, completed epoch/update and next-window position, random states, history, best snapshot and cumulative ledger references. Best-model reporting SHALL use the independent best snapshot. Resume SHALL use a new execution identity linked to the parent, validate matching effective conditions and remaining budget, and restart only from the last complete epoch; partial-epoch replay SHALL count toward cost. Old, corrupt or mismatched checkpoints SHALL fail explicitly without overwriting the parent or silently restarting. Atomic publication failures SHALL preserve the previous valid recovery state and incomplete status.

#### Scenario: Interrupted execution matches uninterrupted training
- **WHEN** a short deterministic fixture is interrupted inside an epoch and resumed from its preceding completed epoch
- **THEN** final parameters, best selection and validation outputs agree with uninterrupted execution within tolerance, with the replay cost retained

#### Scenario: Legacy or damaged checkpoint
- **WHEN** recovery requests a legacy checkpoint missing identity/random/position state or a truncated new checkpoint
- **THEN** it fails with an actionable incompatibility/corruption reason and leaves all existing evidence unchanged

### Requirement: Software readiness stays separate from research execution

The entry SHALL expose explicit development/formal purpose, default to development and place development outputs under ignored scratch or temporary roots. It SHALL reject development paths inside `research/runs/`, including resolved path aliases, and label shortened/synthetic evidence as software evidence. Public help and documentation SHALL describe actual accepted commands, environment, train/select/diagnose/report/check/resume sequencing, failure behavior, output formats and legacy limitations. Formal operation SHALL require explicit purpose and complete protocol controls; purpose SHALL NOT alter scientific calculations.

Implementation and independent verification for this change SHALL use only small synthetic or temporary fixtures, including all three dataset schemas and injected resource/time failures. They SHALL NOT read real demand datasets, execute real-data candidate/repeat matrices, create formal research outputs, edit research plans/protocols/decisions/indexes, alter T009 or historical evidence, or declare T006 complete. A current-basis independent PASS SHALL establish software readiness only. Formal experiment authorization, actual costs, learning-readiness acceptance, historical-result qualification and research task status SHALL remain research-side responsibilities.

#### Scenario: Development invocation targets the formal namespace
- **WHEN** development output resolves inside `research/runs/`
- **THEN** the entry rejects it before creating output or starting a worker

#### Scenario: Independent software verification completes
- **WHEN** the regression, fixture integration, saved-only checks and resource/recovery failure tests pass
- **THEN** software readiness can be reported without real-data execution, new scientific conclusions or research-task acceptance
