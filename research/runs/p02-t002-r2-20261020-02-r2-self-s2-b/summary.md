# Run p02-t002-r2-20261020-02-r2-self-s2-b

- Task: `P02-T001` (add-graph-value-skeleton)
- Dataset: `r2/count`
- Method: `self`
- Model seed: 2
- Protocol: `P1-count-L6-H3-v3`; skeleton `P02-skeleton-v1`; policy `P01-records-v2`
- Purpose: `formal` (formal experiment; requires separate authorization)
- Nodes: 121420
- Source graph: 321374 unique directed edges (321374 raw rows)
- Message edges: 0
- Selected epoch: 200 (validation MSE 34725.387928)
- NaiveRef: `LastValue` (validation MSE, frozen)
- Trainable parameters: 3459 (GRU 3360 + head 99)

## Measured costs

- Total: 2064.549 s
- Data/graph reading: 2.669 s
- Shuffling: 0.000 s
- Training + validation: 2049.913 s
- Selected inference: 2.425 s
- Peak RSS: 2305769472 bytes (2305769472 bytes, scope worker process lifetime)
- Cost scope: development measurement on published data

## Status

A successful run records implementation evidence only. It does not
assert scientific acceptance, predictive benefit, packaging, Git
inclusion or backup completion. The published graph construction
cutoff time is unknown, so fixed-evaluation-period results are not
strictly historical.
