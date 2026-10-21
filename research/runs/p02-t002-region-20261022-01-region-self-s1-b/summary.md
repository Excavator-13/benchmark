# Run p02-t002-region-20261022-01-region-self-s1-b

- Task: `P02-T001` (add-graph-value-skeleton)
- Dataset: `region/count`
- Method: `self`
- Model seed: 1
- Protocol: `P1-count-L6-H3-v3`; skeleton `P02-skeleton-v1`; policy `P01-records-v2`
- Purpose: `formal` (formal experiment; requires separate authorization)
- Nodes: 16345
- Source graph: 218840 unique directed edges (218840 raw rows)
- Message edges: 0
- Selected epoch: 200 (validation MSE 558519.790156)
- NaiveRef: `LastValue` (validation MSE, frozen)
- Trainable parameters: 3459 (GRU 3360 + head 99)

## Measured costs

- Total: 281.194 s
- Data/graph reading: 1.310 s
- Shuffling: 0.000 s
- Training + validation: 272.287 s
- Selected inference: 0.308 s
- Peak RSS: 709799936 bytes (709799936 bytes, scope worker process lifetime)
- Cost scope: development measurement on published data

## Status

A successful run records implementation evidence only. It does not
assert scientific acceptance, predictive benefit, packaging, Git
inclusion or backup completion. The published graph construction
cutoff time is unknown, so fixed-evaluation-period results are not
strictly historical.
