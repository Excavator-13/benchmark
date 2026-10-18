# Run p01-r0-backtest-b-001

- Dataset: `r0/count`
- Protocol: `P1-count-L6-H3-v3`
- Purpose: `formal` (formal experiment)
- Fold: `B` (`TrainMean21`, 21 fitting months)
- Fitting observations: `2021-01`..`2022-09`
- Evaluation splits: `validation` and `eval` (eval targets 2023-01, 2023-02, 2023-03)
- Evidence role: `development_backtest` (development backtest, not a blind test or main evaluation)
- Nodes: 2335
- Seed: 0 (CPU, NumPy backend `numpy`)
- NaiveRef: `TrainMean21` (validation MSE, frozen)
- NaiveRef6: `TrainMean21`
- Selected SharedRidge lambda: 1.0
- Non-self neighbour coverage: 314 nodes from `raw_graph_parquet`

## Measured costs

- Total: 0.491 s
- Data reading: 0.058 s
- Fitting: 0.006 s
- Inference: 0.000 s
- Peak RSS: 144490496 bytes (144490496 bytes)

## Status

A successful run records evidence only. It does not assert scientific
acceptance, packaging, Git inclusion or backup completion.
