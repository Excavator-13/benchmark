# Run p02-t002-r2-20261020-02-r2-shuffled1-s1-b

- Task: `P02-T001` (add-graph-value-skeleton)
- Dataset: `r2/count`
- Method: `shuffled` (shuffle seed 1)
- Model seed: 1
- Protocol: `P1-count-L6-H3-v3`; skeleton `P02-skeleton-v1`; policy `P01-records-v2`
- Purpose: `formal` (formal experiment; requires separate authorization)
- Nodes: 121420
- Source graph: 321374 unique directed edges (321374 raw rows)
- Message edges: 321374
- Selected epoch: 200 (validation MSE 34719.897715)
- NaiveRef: `LastValue` (validation MSE, frozen)
- Trainable parameters: 3459 (GRU 3360 + head 99)

## Measured costs

- Total: 2044.683 s
- Data/graph reading: 2.708 s
- Shuffling: 3.260 s
- Training + validation: 2026.764 s
- Selected inference: 2.490 s
- Peak RSS: 2744254464 bytes (2744254464 bytes, scope worker process lifetime)
- Cost scope: development measurement on published data

## Status

A successful run records implementation evidence only. It does not
assert scientific acceptance, predictive benefit, packaging, Git
inclusion or backup completion. The published graph construction
cutoff time is unknown, so fixed-evaluation-period results are not
strictly historical.
