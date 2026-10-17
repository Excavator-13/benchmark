# Run p01-region-backtest-b-001

- Dataset: `region/count`
- Protocol: `P1-count-L6-H3-v3`
- Purpose: `formal` (formal experiment)
- Fold: `B` (`TrainMean21`, 21 fitting months)
- Fitting observations: `2021-01`..`2022-09`
- Evaluation splits: `validation` and `eval` (eval targets 2023-01, 2023-02, 2023-03)
- Evidence role: `development_backtest` (development backtest, not a blind test or main evaluation)
- Nodes: 16345
- Seed: 0 (CPU, NumPy backend `numpy`)
- NaiveRef: `TrainMean21` (validation MSE, frozen)
- NaiveRef6: `TrainMean21`
- Selected SharedRidge lambda: 0.001
- Non-self neighbour coverage: 2185 nodes from `raw_graph_parquet`

## Measured costs

- Total: 0.728 s
- Data reading: 0.160 s
- Fitting: 0.041 s
- Inference: 0.001 s
- Peak RSS: 279986176 bytes (279986176 bytes)

## Status

A successful run records evidence only. It does not assert scientific
acceptance, packaging, Git inclusion or backup completion.
