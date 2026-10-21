# Run p02-t002-r0-20261022-01-r0-self-s2-a

- Task: `P02-T001` (add-graph-value-skeleton)
- Dataset: `r0/count`
- Method: `self`
- Model seed: 2
- Protocol: `P1-count-L6-H3-v3`; skeleton `P02-skeleton-v1`; policy `P01-records-v2`
- Purpose: `formal` (formal experiment; requires separate authorization)
- Nodes: 2335
- Source graph: 60804 unique directed edges (60804 raw rows)
- Message edges: 0
- Selected epoch: 200 (validation MSE 15975356.257551)
- NaiveRef: `LastValue` (validation MSE, frozen)
- Trainable parameters: 3459 (GRU 3360 + head 99)

## Measured costs

- Total: 55.322 s
- Data/graph reading: 0.352 s
- Shuffling: 0.000 s
- Training + validation: 47.860 s
- Selected inference: 0.027 s
- Peak RSS: 416415744 bytes (416415744 bytes, scope worker process lifetime)
- Cost scope: development measurement on published data

## Status

A successful run records implementation evidence only. It does not
assert scientific acceptance, predictive benefit, packaging, Git
inclusion or backup completion. The published graph construction
cutoff time is unknown, so fixed-evaluation-period results are not
strictly historical.
