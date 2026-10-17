# Run p01-r0-backtest-a-001

- Dataset: `r0/count`
- Protocol: `P1-count-L6-H3-v3`
- Purpose: `formal` (formal experiment)
- Fold: `A` (`TrainMean18`, 18 fitting months)
- Fitting observations: `2021-01`..`2022-06`
- Evaluation splits: `validation` and `eval` (eval targets 2022-10, 2022-11, 2022-12)
- Evidence role: `development_backtest` (development backtest, not a blind test or main evaluation)
- Nodes: 2335
- Seed: 0 (CPU, NumPy backend `numpy`)
- NaiveRef: `LastValue` (validation MSE, frozen)
- NaiveRef6: `LastValue`
- Selected SharedRidge lambda: 0.1
- Non-self neighbour coverage: 314 nodes from `raw_graph_parquet`

## Measured costs

- Total: 0.517 s
- Data reading: 0.059 s
- Fitting: 0.004 s
- Inference: 0.000 s
- Peak RSS: 141312000 bytes (141312000 bytes)

## Status

A successful run records evidence only. It does not assert scientific
acceptance, packaging, Git inclusion or backup completion.
