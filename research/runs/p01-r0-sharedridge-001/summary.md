# Run p01-r0-sharedridge-001

- Dataset: `r0/count`
- Protocol: `P1-count-L6-H3-v3`
- Nodes: 2335
- Seed: 0 (CPU, NumPy backend `numpy`)
- NaiveRef: `LastValue` (validation MSE, frozen)
- NaiveRef6: `LastValue`
- Selected SharedRidge lambda: 0.0001
- Non-self neighbour coverage: 314 nodes from `raw_graph_parquet`

## Measured costs

- Total: 0.379 s
- Data reading: 0.058 s
- Fitting: 0.008 s
- Inference: 0.000 s
- Peak RSS: 144244736 bytes (144244736 bytes)

## Status

A successful run records evidence only. It does not assert scientific
acceptance, packaging, Git inclusion or backup completion.
