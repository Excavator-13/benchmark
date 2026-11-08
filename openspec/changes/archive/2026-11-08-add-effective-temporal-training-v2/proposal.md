# Proposal

## Why

The validated P02/T006 recurrent runner has a sound GRU/LSTM protocol, but its v1 entry point is difficult to resume safely and does not enforce all protocol boundaries at runtime. Window-count validation is incomplete, test labels are materialized before training, and the checkpoint format lacks an explicit resume path. These gaps make interrupted runs and malformed inputs less auditable than the surrounding research workflow requires.

## What Changes

- Harden L6/H3 window construction with count-aware bounds validation and explicit split metadata.
- Add a resumable training CLI/API that restores model, optimizer, epoch, and best validation state only from an identity-checked checkpoint.
- Keep test observations and labels out of the training phase; evaluate the test split only after validation checkpoint selection.
- Validate finite learning rates and positive model/resource settings before creating output files.
- Extend deterministic tests and machine-readable summaries to cover resume, malformed windows, and test-label isolation.

## Capabilities

### New Capabilities

- `recurrent-forecasting-entry`: Protocol-isolated, resumable GRU/LSTM training and comparison for P02/T006 demand sequences.

### Modified Capabilities

- None.

## Impact

Updates `benchmark/multivariate_time_series/effective_temporal_training.py` and its focused tests. The legacy experiment runner, existing archived v1 artifacts, and T009 ownership remain unchanged. No new runtime dependencies are required.
