# Run p01-region-backtest-a-001

- Dataset: `region/count`
- Protocol: `P1-count-L6-H3-v3`
- Purpose: `formal` (formal experiment)
- Fold: `A` (`TrainMean18`, 18 fitting months)
- Fitting observations: `2021-01`..`2022-06`
- Evaluation splits: `validation` and `eval` (eval targets 2022-10, 2022-11, 2022-12)
- Evidence role: `development_backtest` (development backtest, not a blind test or main evaluation)
- Nodes: 16345
- Seed: 0 (CPU, NumPy backend `numpy`)
- NaiveRef: `LastValue` (validation MSE, frozen)
- NaiveRef6: `LastValue`
- Selected SharedRidge lambda: 0.1
- Non-self neighbour coverage: 2185 nodes from `raw_graph_parquet`

## Measured costs

- Total: 0.724 s
- Data reading: 0.162 s
- Fitting: 0.034 s
- Inference: 0.001 s
- Peak RSS: 271220736 bytes (271220736 bytes)

## Status

A successful run records evidence only. It does not assert scientific
acceptance, packaging, Git inclusion or backup completion.
