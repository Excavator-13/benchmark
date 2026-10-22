## Why

A reboot interrupted the first formal r2 fit after 7042.593 seconds with no persisted model/Adam state or epoch history. The existing controller heartbeat cannot identify completed epochs. Long runs need recoverable epoch boundaries without changing the scientific experiment.

## What Changes

- Persist atomic, integrity-checked checkpoints after fully validated epochs, including model, Adam, RNG, history, selected state and cumulative timing.
- Expose epoch progress separately from completion, with measured timings and remaining-work estimates.
- Support explicit resume into a fresh run identity with exact computation/input/environment identity checks and preserved source evidence.
- Make r2 orchestration recover verified completed fits and explicitly resume eligible checkpoints; publish only after all original checks pass.
- Prove resumed and uninterrupted 200-epoch execution equivalence before research execution.

## Capabilities

### New Capabilities

### Modified Capabilities

- `graph-value-skeleton`: durable epoch checkpoints, explicit safe resume and progress evidence.

## Impact

Training, runner/config/CLI, evidence checks, tests, README and r2 orchestration. No new dependency or changed model, data, split, optimizer, selection, epochs or tolerance. The old interrupted run has no checkpoint and cannot be resumed.
