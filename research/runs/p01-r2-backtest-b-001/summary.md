# Run p01-r2-backtest-b-001

- Dataset: `r2/count`
- Protocol: `P1-count-L6-H3-v3`
- Purpose: `formal` (formal experiment)
- Fold: `B` (`TrainMean21`, 21 fitting months)
- Fitting observations: `2021-01`..`2022-09`
- Evaluation splits: `validation` and `eval` (eval targets 2023-01, 2023-02, 2023-03)
- Evidence role: `development_backtest` (development backtest, not a blind test or main evaluation)
- Nodes: 121420
- Seed: 0 (CPU, NumPy backend `numpy`)
- NaiveRef: `LastValue` (validation MSE, frozen)
- NaiveRef6: `LastValue`
- Selected SharedRidge lambda: 1.0
- Non-self neighbour coverage: 10193 nodes from `raw_graph_parquet`

## Measured costs

- Total: 2.015 s
- Data reading: 0.377 s
- Fitting: 0.330 s
- Inference: 0.009 s
- Peak RSS: 1164181504 bytes (1164181504 bytes)

## Status

A successful run records evidence only. It does not assert scientific
acceptance, packaging, Git inclusion or backup completion.
