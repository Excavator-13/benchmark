## Why

P01-T004 needs a reusable, independently auditable CPU baseline before graph experiments resume. Existing v2 diagnostics report five naive methods but do not provide a shared Ridge implementation or the complete saved artifacts needed to reconstruct predictions and metrics.

## What Changes

- Add an independent CPU entry for `r0/count` and `region/count`, with NumPy, pandas and PyArrow as its only required third-party dependencies and optional scikit-learn support.
- Implement canonical node identity, data validation, the fixed L=6/H=3 split, five naive methods, validation-selected `NaiveRef`/`NaiveRef6`, and explicitly named `SharedRidge` under `P1-count-L6-H3-v3`.
- Freeze each node's normalization on the 27 unique training-observation months; fit shared parameters on training samples and select lambda exclusively by validation MSE in original units.
- Report original-unit aggregate, window, horizon, context, activity and neighbor-group metrics, counts, negative predictions and baseline-relative comparisons. Preserve raw Ridge outputs and label any clipped outputs separately.
- Save self-contained run directories with provenance, identities, predictions/labels, masks, fitted parameters, selection evidence, measured timings/memory and terminal status; provide independent metric recomputation and same-seed comparison commands.
- Add minimal CPU documentation and automated tests, then produce one formal run per dataset and a second same-seed execution per dataset for repeatability evidence during implementation.
- Compare new naive results against immutable v2 diagnostic JSON lines and record and explain discrepancies.

### Non-Goals

No changes to `benchmark/graph_method/**`; no EvolveGCN-H repair, graph-model training, gating or graph-benefit method. No `r2/count` (T006), internal backtests (T007), rate/log1p/weighted-training variants or claims of scientific acceptance. No edits to existing research records, `DELEGATION.md`, sealed runs or main `openspec/specs/`. Future run tasks write only fresh `research/runs/<run_id>/` directories; packaging, archive-index updates, commits and pushes belong to separately authorized research work. This proposal workflow creates planning artifacts only and executes no experiments.

## Capabilities

### New Capabilities

- `nograph-baseline-entry`: Reusable CPU forecasting, protocol-bound evaluation and recoverable run evidence for the two count datasets.

One new capability keeps the entry's data, fitting, evaluation and persistence contract together. Existing `graph-forecast-experiments` and `graph-forecast-data-pipeline` require graph snapshots, tensor devices and graph checkpoints; extending them would couple this independent entry to unrelated runtime contracts. Their identity and split conventions remain consistent with this proposal.

### Modified Capabilities

None.

## Impact

Add `benchmark/nograph_baseline/`, a local minimal dependency declaration and CPU tests; add a scoped README usage section during implementation. Existing traditional and graph CLIs and ignore rules need no change. Formal output uses the unignored `research/runs/` location, which alone does not establish archival or backup completion.

The sole normative source is [第一阶段实验协议：可信数据与 baseline](../../../research/phases/P01/protocol.md) sections 3-6; scope and acceptance context come from [P01：建立可信研究底座](../../../research/phases/P01/plan.md) and [第一阶段执行指导：诊断与 baseline 操作](../../../research/phases/P01/execution-guide.md). Neighbor masks use context-qualified non-self endpoint coverage from raw graph Parquet strictly for reporting; no graph inputs reach forecasting or selection. The recommended environment is `job-sdf-baseline` (Python 3.11, NumPy 1.26.4, pandas 2.2.3, PyArrow 17.0.0), independent of root CUDA/DGL requirements.
