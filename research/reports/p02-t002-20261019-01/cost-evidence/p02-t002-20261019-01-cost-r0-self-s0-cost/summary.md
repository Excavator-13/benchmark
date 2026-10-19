# Run p02-t002-20261019-01-cost-r0-self-s0-cost

- Task: `P02-T001` (add-graph-value-skeleton)
- Dataset: `r0/count`
- Method: `self`
- Model seed: 0
- Protocol: `P1-count-L6-H3-v3`; skeleton `P02-skeleton-v1`; policy `P01-records-v2`
- Purpose: `development` (development output; not scientific acceptance evidence)
- Nodes: 2335
- Source graph: 60804 unique directed edges (60804 raw rows)
- Message edges: 0
- Selected epoch: 200 (validation MSE 15976315.572087)
- NaiveRef: `LastValue` (validation MSE, frozen)
- Trainable parameters: 3459 (GRU 3360 + head 99)

## Measured costs

- Total: 251.346 s
- Data/graph reading: 0.991 s
- Shuffling: 0.000 s
- Training + validation: 235.262 s
- Selected inference: 0.113 s
- Peak RSS: None bytes (None None, scope process)
- Cost scope: development measurement on published data

## Status

A successful run records implementation evidence only. It does not
assert scientific acceptance, predictive benefit, packaging, Git
inclusion or backup completion. The published graph construction
cutoff time is unknown, so fixed-evaluation-period results are not
strictly historical.
