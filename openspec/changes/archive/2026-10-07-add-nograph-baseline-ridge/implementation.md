# Implementation: add-nograph-baseline-ridge

- Change: `add-nograph-baseline-ridge`
- Schema: `spec-driven`
- Protocol: `P1-count-L6-H3-v3` (`research/phases/P01/protocol.md` sections 3–6)
- Updated: 2026-10-07T16:42+08:00
- Repository revision during runs: `a0fdab4268e5e17b0c96453efd53f01a245f01cc` (dirty working tree: new implementation, README section, run evidence)
- Implementation root: `/Users/watuji/da_chuang/repos/benchmark`

This document records implementation evidence only. It does **not** assert
scientific acceptance, packaging, Git inclusion, backup completion or an
independent verification PASS. Sealing, archive-index updates, commits, pushes
and research acceptance remain outside this change.

## 1. Changed and added files

| Path | Purpose |
| --- | --- |
| `benchmark/nograph_baseline/__init__.py`, `__main__.py` | Package entry point (`python -m benchmark.nograph_baseline`) |
| `benchmark/nograph_baseline/protocol.py` | Fixed `P1-count-L6-H3-v3` constants, calendar/window metadata, split assertions, module-relative paths |
| `benchmark/nograph_baseline/data.py` | Canonical demand loading, validation and descriptive audits |
| `benchmark/nograph_baseline/baselines.py` | Five naïve methods, frozen `NaiveRef`/`NaiveRef6` selection |
| `benchmark/nograph_baseline/ridge.py` | Frozen training statistics, shared NumPy Ridge fit, optional sklearn backend, validation-only lambda selection |
| `benchmark/nograph_baseline/metrics.py` | Original-unit metric reductions, fixed-mask reports, per-node error tables |
| `benchmark/nograph_baseline/coverage.py` | Evaluation-only context-qualified non-self coverage and mask bundles |
| `benchmark/nograph_baseline/artifacts.py` | Exclusive run directories, atomic writers, git/environment/source capture |
| `benchmark/nograph_baseline/runner.py` | Stage orchestration, timing, peak RSS, failure/interruption status |
| `benchmark/nograph_baseline/checks.py` | `recompute`, `compare`, `align-v2` saved-run analysis |
| `benchmark/nograph_baseline/cli.py` | Public commands and isolated CPU worker launcher |
| `benchmark/nograph_baseline/_worker.py` | Private isolated-worker entry point |
| `benchmark/nograph_baseline/requirements.txt` | NumPy/pandas/PyArrow only; sklearn optional and separate |
| `benchmark/nograph_baseline/tests/` | Standard-library `unittest` suite with synthetic Parquet fixtures |
| `README.md` | Section 4.5 CPU baseline usage, dependency, command and unsealed-output notes |
| `openspec/changes/add-nograph-baseline-ridge/evidence/` | Retained test and run logs (this change) |

No file under `benchmark/graph_method/**`, `research/**` (other than new
`research/runs/<run_id>/` directories), `experiments_archive/**`,
`DELEGATION.md` or `openspec/specs/**` was modified.

## 2. Tests

Command (repository root, `job-sdf-baseline`):

```bash
python -m unittest discover -s benchmark/nograph_baseline/tests
```

Result: **94 tests run, OK, 1 skipped** (optional scikit-learn backend is not
installed). Full verbose output:
`openspec/changes/add-nograph-baseline-ridge/evidence/self-tests.log`.

Focused logs:

| Evidence | Path |
| --- | --- |
| Minimal three-dependency smoke, both schemas, blocked sklearn/torch/PyG/DGL/graph_method | `evidence/test-2.5-minimal-dependency.log` |
| Existing-ID rejection, malformed source, SIGINT/SIGTERM/SIGKILL, unfinished state | `evidence/test-2.6-failure-interruption.log` |
| Saved-only recompute, same-seed compare, v2 alignment | `evidence/test-2.4-2.7-checks.log` |
| Environment and Parquet read check | `evidence/environment-check.txt` |

The suite writes only to temporary directories and to fixture paths; it does not
read repository graph data and does not need a GPU.

## 3. Formal runs and check runs

All directories are under `research/runs/`.

| Task | Run ID | Kind | Report status |
| --- | --- | --- | --- |
| 3.1 | `p01-r0-sharedridge-001` | formal r0/count | success |
| 3.2 | `p01-r0-sharedridge-repeat-001` | r0 same-seed repetition | success |
| 3.3 | `p01-r0-recompute-primary-001` | recompute check | ok (max normalized difference 0.0) |
| 3.3 | `p01-r0-recompute-repeat-001` | recompute check | ok (max normalized difference 0.0) |
| 3.3 | `p01-r0-repeat-check-001` | compare check | ok (max prediction abs diff 0.0; max MAE relative diff 0.0) |
| 3.4 | `p01-r0-alignment-001` | align-v2 check | ok (409 fields compared, 0 discrepancies) |
| 3.5 | `p01-region-sharedridge-001` | formal region/count | success |
| 3.6 | `p01-region-sharedridge-repeat-001` | region same-seed repetition | success |
| 3.7 | `p01-region-recompute-primary-001` | recompute check | ok (max normalized difference 2.43e-16) |
| 3.7 | `p01-region-recompute-repeat-001` | recompute check | ok (max normalized difference 2.43e-16) |
| 3.7 | `p01-region-repeat-check-001` | compare check | ok (max prediction abs diff 0.0; max MAE relative diff 0.0) |
| 3.8 | `p01-region-alignment-001` | align-v2 check | ok (409 fields compared, 0 discrepancies) |

Each formal run directory contains the documented layout (protocol snapshot,
config/command, provenance, git files, `code-untracked/`, environment, source
hashes, `nodes.parquet`, `windows.json`, `audit.json`, `masks.npz`,
`node-errors.parquet`, gold labels, predictions for all five naïve methods and
`SharedRidge`, candidate parameters, `selection.json`, `metrics.json`,
`measurements.json`, `artifacts-sha256.json`, `events.jsonl`, `summary.md`,
`status.json`); 72 files are covered by the immutable artifact manifest.

### Selection and headline metrics

| Run | Nodes | M = 19·N | `NaiveRef` | `NaiveRef6` | Selected λ | Ridge validation MSE | Ridge test MAE | LastValue test MAE |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| `p01-r0-sharedridge-001` | 2335 | 44365 | LastValue | LastValue | 1e-4 | 375887.195826 | 274.765431 | 189.875089 |
| `p01-r0-sharedridge-repeat-001` | 2335 | 44365 | LastValue | LastValue | 1e-4 | 375887.195826 | 274.765431 | 189.875089 |
| `p01-region-sharedridge-001` | 16345 | 310555 | LastValue | LastValue | 1e-4 | 18138.518071 | 47.598353 | 35.309850 |
| `p01-region-sharedridge-repeat-001` | 16345 | 310555 | LastValue | LastValue | 1e-4 | 18138.518071 | 47.598353 | 35.309850 |

Both datasets select the validation-MSE winner and retain the Ridge result even
though it does not beat `LastValue` on the test period; the protocol requires
retaining that evidence rather than dropping it.

### Source and reference hashes

| Artifact | SHA256 |
| --- | --- |
| `dataset/demand/r0.parquet` | `fc8ebd497f3100f76bc92078529535055a34c281857d61a8d7bd8034898c6946` |
| `dataset/demand/region.parquet` | `27a946c787efcd5f1d2b25ca35bebd1392320d9b10920e771405a664db5e4a3f` |
| `dataset/graph/r0.parquet` | `c49bc2ecfddd24ddc7a6c6654fdc7bf2e908820139a987f99a115c11b583aa5b` |
| `dataset/graph/region.parquet` | `c0bed3290be3691fbb07c4834c96e8d567e1f54cdfb2120d8a0846a86b64d87c` |
| `research/phases/P01/protocol.md` snapshot | `7c113c83d49f15f6…` (full hash in each run's `source-sha256.json`) |
| v2 reference log `research/runs/phase1-20261006-v2-01/naive-baselines.log` | `c425bbe165cd32a393f782b290c05f0f74423a695539cdb40fd1a091e25e8367` |

Both formal runs record `source-sha256.json` entries for demand, protocol and
coverage source; the four source hashes above are identical to
`research/runs/phase1-20261006-v2-01/source-sha256.txt`, so the v2 comparison
uses the same immutable sources. The v2 log was not modified
(`reference_unchanged: true`).

## 4. Measured environment and costs

Environment (`job-sdf-baseline`): Python 3.11.17, NumPy 1.26.4, pandas 2.2.3,
PyArrow 17.0.0, scikit-learn not installed; macOS `arm64`; BLAS threads pinned
to 1 before NumPy import.

| Run | data reading (s) | fitting (s) | inference (s) | total (s) | peak RSS (bytes) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `p01-r0-sharedridge-001` | 0.058 | 0.0079 | 0.0002 | 0.379 | 144244736 |
| `p01-r0-sharedridge-repeat-001` | 0.059 | 0.0081 | 0.0002 | 0.375 | 147144704 |
| `p01-region-sharedridge-001` | 0.159 | 0.0608 | 0.0010 | 0.630 | 311033856 |
| `p01-region-sharedridge-repeat-001` | 0.160 | 0.0587 | 0.0010 | 0.645 | 324665344 |

Peak RSS uses `resource.getrusage(RUSAGE_SELF).ru_maxrss` with the native unit
recorded (macOS reports bytes). Diagnostic elapsed times from the v2 run are not
compared with these measured costs.

## 5. Corrected defects found during implementation

1. **Normalization month range (fixed).** `compute_training_stats` initially used
   `N_MONTHS - HORIZON` (33) months instead of the 27 unique observations
   `2021-01..2023-03`. A regression test now asserts the exact 27-month
   `ddof=0` statistics and their difference from overlap-weighted estimates.
2. **Validation target units during lambda selection (fixed).** Candidate
   `validation_MSE`/`validation_MAE` compared original-unit predictions against
   **standardized** targets. Selection now inverse-transforms the validation
   labels first and records `validation_gold_units: "original"`. Regression
   tests assert candidate scores equal the reported original-unit validation
   metrics both at the unit level and from `metrics.json`.

Two r0/count directories produced before fix 2 (`p01-r0-sharedridge-001`,
`p01-r0-sharedridge-repeat-001`) held invalid selection evidence. They were
removed during apply and the same run IDs were re-created with the corrected
implementation; the run IDs above refer to the corrected runs only.

## 6. Limitations and open items

- The optional scikit-learn backend is skipped because scikit-learn is not
  installed in `job-sdf-baseline`; the equivalence test is present and will run
  when it is installed. The default NumPy path is complete.
- Region saved-run recomputation agrees with the primary run to a normalized
  2.43e-16, not bit-for-bit. The sealed v2 diagnostic computed `TrainMean27`
  metrics directly from a `numpy.broadcast_to` view; materializing the saved
  array changes the pairwise-summation grouping by one ULP. The difference is
  far below the declared 1e-12 diagnostic tolerance and is reported as `ok`.
- A private test-only environment variable
  `NOGRAPH_BASELINE_TEST_STAGE_DELAY_SECONDS` holds a run open between stages so
  the suite can deliver SIGINT/SIGTERM/SIGKILL deterministically. It is inert
  unless set.
- `research/runs/` output is unsealed and not backed up. Packaging,
  archive-index updates, commits, pushes and research acceptance are pending and
  explicitly outside this change.
- No independent verification has been performed. Task 4.3 and the verification
  handoff are in `implementation-notes.md`.
