# Proposal

## Why

P02/T006 needs a reproducible pure-temporal training path that follows the new P02 protocol rather than the legacy all-window runner. The current baseline has GRU/LSTM model files but no protocol-isolated RMS preprocessing, full-window gradient accumulation, checkpoint identity, or controlled comparison entry point.

## What Changes

- Add a protocol-isolated CPU training runner for GRU and LSTM on Job-SDF demand data.
- Implement training-period RMS scaling, L6/H3 window construction, full-window gradient accumulation, gradient clipping, validation-only checkpoint selection, and resumable checkpoint metadata.
- Expose finite learning-rate, seed, model, dataset, and resource options with machine-readable run summaries and comparison metrics.
- Add tests and a documented command for a small deterministic fixture.

## Capabilities

### New Capabilities

- `recurrent-forecasting-entry`: Provides reproducible protocol-isolated GRU/LSTM training and comparison artifacts.

### Modified Capabilities

- None.

## Impact

Adds a new implementation and CLI under `benchmark/multivariate_time_series`, tests, and research run artifacts. Existing legacy runner behavior remains unchanged. The implementation uses the already declared PyTorch, NumPy, pandas, and PyArrow dependencies and does not alter P02/T009.
