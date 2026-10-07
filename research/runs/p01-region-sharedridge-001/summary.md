# Run p01-region-sharedridge-001

- Dataset: `region/count`
- Protocol: `P1-count-L6-H3-v3`
- Nodes: 16345
- Seed: 0 (CPU, NumPy backend `numpy`)
- NaiveRef: `LastValue` (validation MSE, frozen)
- NaiveRef6: `LastValue`
- Selected SharedRidge lambda: 0.0001
- Non-self neighbour coverage: 2185 nodes from `raw_graph_parquet`

## Measured costs

- Total: 0.630 s
- Data reading: 0.159 s
- Fitting: 0.061 s
- Inference: 0.001 s
- Peak RSS: 311033856 bytes (311033856 bytes)

## Status

A successful run records evidence only. It does not assert scientific
acceptance, packaging, Git inclusion or backup completion.
