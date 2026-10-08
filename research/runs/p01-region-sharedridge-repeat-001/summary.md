# Run p01-region-sharedridge-repeat-001

- Dataset: `region/count`
- Protocol: `P1-count-L6-H3-v3`
- Nodes: 16345
- Seed: 0 (CPU, NumPy backend `numpy`)
- NaiveRef: `LastValue` (validation MSE, frozen)
- NaiveRef6: `LastValue`
- Selected SharedRidge lambda: 0.0001
- Non-self neighbour coverage: 2185 nodes from `raw_graph_parquet`

## Measured costs

- Total: 0.645 s
- Data reading: 0.160 s
- Fitting: 0.059 s
- Inference: 0.001 s
- Peak RSS: 324665344 bytes (324665344 bytes)

## Status

A successful run records evidence only. It does not assert scientific
acceptance, packaging, Git inclusion or backup completion.
