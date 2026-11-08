# Design

## Context

The correct baseline is `91ea3d6df8360998d9d2b1ed36ab764322ee26f3`. Its P02 protocol defines L6/H3 windows, training-only RMS scaling, full-window updates, validation checkpoint selection, CPU determinism, and finite candidate choices. The existing multivariate time-series runner is legacy code and must remain behaviorally compatible.

## Goals / Non-Goals

**Goals:**

- Add a separate, testable runner whose configuration and outputs map directly to the P02 protocol.
- Make GRU/LSTM state handling, scaling, split boundaries, checkpoint identity, and comparison statistics explicit.
- Support small synthetic fixtures for deterministic software verification before real data runs.

**Non-Goals:**

- Replacing the legacy `run.py` or changing graph models.
- Implementing T007/T009 or making a graph-benefit claim.
- Expanding the learning-rate search beyond the finite protocol candidates.

## Decisions

- **Separate module and CLI:** keeps the frozen legacy runner import-compatible and makes protocol identity visible in one entry point. Editing the legacy runner directly was rejected because it could silently change historical experiments.
- **Torch Dataset-free window tensors:** materialize only the selected 27-month training, 3-month validation, and 6-month test windows for the current data group. This makes full-window accumulation and state reset auditable and avoids worker nondeterminism.
- **Explicit checkpoint manifest:** save model, optimizer, scale, split, seed, source commit, and protocol version in one manifest. Inferring identity from directory names was rejected because it permits incompatible resumes.
- **JSONL progress plus final JSON:** progress is append-only and final summaries are atomic. A single mutable log was rejected because interrupted runs would be hard to audit.

## Risks / Trade-offs

- [Risk] Large `r2` tensors can exceed local memory. → Enforce a node-chunk option, CPU single-thread defaults, and preflight memory estimates; stop before allocation when limits fail.
- [Risk] Existing data files are ignored and may be absent in a clean clone. → Fail with an actionable input error and record the exact data path; use synthetic fixtures for software tests.
- [Risk] CPU and library versions change floating-point results. → Record environment, torch threads, deterministic mode, and source commit in every run.

## Migration Plan

Run the new CLI in a new run directory, review its JSON summary and verification logs, then update P02 research records. Existing legacy results and T009 records remain untouched.
