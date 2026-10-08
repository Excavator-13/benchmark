## Why

T004 produced 8 model executions and 16 checks with 780 files because checks, source snapshots and losing Ridge candidates received full experiment retention. P01 now accepts `P01-records-v2`: preserve scientific reproducibility while recording checks as reports and identifying Git-saved packages by their commits.

## What Changes

- Distinguish formal model execution from development invocation; keep independent execution identities and complete formal prediction evidence, with disposable development output outside the formal namespace.
- Replace mandatory check-type RunDirectory creation with an exclusive JSON report at an explicit output path. Retain saved-only recomputation, repeat comparison, immutable v2 alignment, input identities, tolerances and nonzero failure results.
- **BREAKING**: Check output/return metadata changes to report paths. Retain old `--run-id`/`--runs-root` check flags as documented compatibility aliases that resolve to a single report, without generating a legacy run directory.
- Reference committed runtime source and protocol at fixed commit/path; save only relevant dirty patches and necessary untracked runtime files. Keep unavailable provenance explicit.
- Preserve selected Ridge parameters and preprocessing plus every candidate's validation scores; omit losing candidate parameter/prediction files by default and offer explicit retention when needed.
- Adapt the T004 archive utility to schema v2, whose Git identity and exclusion declarations replace sidecars/full member hash tables; continue accepting historical schema v1. No automatic sealing, Git action or restoration follows model/check commands.
- Update baseline documentation and focused tests; do not modify historical packages, readable run entries or archived verification reports, rerun accepted scientific experiments, or change scientific rules.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `nograph-baseline-entry`: Proportionate formal evidence, compact check reports, recoverable relevant source references, optional losing-candidate retention, development output isolation and Git-backed archive metadata compatibility. Scientific forecasting/selection/grouping requirements remain unchanged.

## Impact

`benchmark/nograph_baseline/{runner,artifacts,checks,cli,_worker,protocol}.py`, nearby CPU tests and `README.md`; `research/archives/seal_20261007_baseline.py` consumes the schema-v2 package index already written by research maintenance. The existing `scratch/` ignore policy supplies development storage. No new dependencies or scientific datasets/models are introduced. Main specs sync only after independent verification; research acceptance and mutable research records remain research-side responsibilities.
