# Run p01-r2-sharedridge-001

- Dataset: `r2/count`
- Protocol: `P1-count-L6-H3-v3`
- Purpose: `formal` (formal experiment)
- Nodes: 121420
- Seed: 0 (CPU, NumPy backend `numpy`)
- NaiveRef: `LastValue` (validation MSE, frozen)
- NaiveRef6: `LastValue`
- Selected SharedRidge lambda: 0.0001
- Non-self neighbour coverage: 10193 nodes from `raw_graph_parquet`

## Measured costs

- Total: 2.950 s
- Data reading: 0.477 s
- Fitting: 0.462 s
- Inference: 0.007 s
- Peak RSS: 1293303808 bytes (1293303808 bytes)

## Status

A successful run records evidence only. It does not assert scientific
acceptance, packaging, Git inclusion or backup completion.
