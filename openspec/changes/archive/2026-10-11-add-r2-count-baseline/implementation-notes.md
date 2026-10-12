# Implementation Notes

- Change: `add-r2-count-baseline`
- Schema: `spec-driven`
- Store: local (no registered store; nearest repo-local `openspec/` root)
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark`
- Updated: 2026-10-11T18:12:00+0800
- Implementation revision: `57275e7b6490a420c3fb110de7ce5f228206cfa6`, dirty working tree (README, `cli.py`, `protocol.py`, five test modules, main spec, execution guide modified; change dir untracked; `scratch/` data is gitignored). No commits or pushes were made.
- Progress: 15/15 tasks complete (5.3 is this handoff).

This is an apply-owned handoff, not a verification verdict. It records what was
implemented, what was actually executed, and what the independent verifier
should probe. It does not authorize deferred behavior or weaker acceptance.

## Implementation Map

The only production-code change is the dataset mapping plus CLI help/description
text. `data.py`, `coverage.py`, `runner.py`, `ridge.py`, `metrics.py`,
`artifacts.py` and `checks.py` required **no** r2-specific branch: the r2 tests
exercised the generic context-column path and passed unchanged.

| Task / requirement / scenario | Code and tests | Decisions / context |
| --- | --- | --- |
| 1.1 r2 registration; three datasets parse; r2 default paths and node keys; unknown data/rate/split rejected; versions unchanged | `benchmark/nograph_baseline/protocol.py` (`SUPPORTED_DATASETS["r2"] = ("r2_id",)`), `benchmark/nograph_baseline/cli.py` (description lists three granularities); `tests/test_protocol.py::CliSurfaceTests` | choices stay derived from the mapping (`{r0,r2,region}`); `P1-count-L6-H3-v3` and counts-only mode unchanged; `validate_split_assertions`/`windows_for_split` still reject out-of-protocol splits |
| 1.2 r2 fixture keys and `build_fixture` branch; cross-context `skill_id` not merged; r0/region fixtures unchanged | `tests/nb_fixtures.py` (`r2_keys`, r2 branch with `contexts`/`skills`); `tests/test_data.py::FixtureGridTests` | r2 branch is explicit; r0/region key generation, graph rows and signal layout untouched. Default r2 graph = non-self edge in context 0, self-loop in context 1, isolated tail |
| 2.1 r2 shuffle/multi-context/complete+sparse grid, zero/constant/activity boundaries, pre-fit rejection | `tests/test_data.py::R2DemandAuditTests` | sparse grid is reported (`is_complete_context_skill_grid=False`, `expected_context_skill_nodes`) and never filled; rows 7 late-activity case separates train-27 from full-36 audits |
| 2.2 r2 raw-graph and provenance-bearing mask coverage; context qualification; invalid evidence rejected | `tests/test_coverage.py::R2CoverageTests` | same-skill-two-contexts, self-loop-only, unknown context/endpoint, missing `r2_id` column, mask dataset/schema/keys/semantics/provenance failures |
| 2.3 two independent small r2 development runs through the real public CLI | `tests/test_runner_cli.py::R2DevelopmentRunTests` (`_public_run_argv` subprocess helper) | worktrees: two CLI runs (`r2-cli-alpha/beta`) + one r0 CLI run for schema comparison; verifies artifacts, `allow_pickle=False` loads, windows 19/1/4, `M=19*N`, all five lambda scores, validation-MSE selection with larger-lambda tie break, shared masks, ddof=0 27-month normalization, r2 identity/gold alignment, and identical artifact path set + collapsed JSON schema paths vs r0 |
| 2.4 information boundaries and coverage invariance | `tests/test_runner_cli.py::R2InformationBoundaryTests` | post-training value changes leave normalization/activity/candidate W,b unchanged (validation targets do move); test-target-only changes leave the whole `selection.json` unchanged; coverage changes leave predictions/selection unchanged while neighbor metrics move. No production fix was required |
| 3.1 r2 recompute + same-seed compare on saved evidence | `tests/test_runner_cli.py::R2DevelopmentRunTests.test_recompute_r2_saved_metrics_without_source_or_refit`, `test_compare_two_same_seed_r2_runs` | recompute runs with the demand/graph files temporarily unlinked (restored in `finally`) and asserts `source_data_read=False`, `model_refit=False`, zero normalized differences, r2 contexts/windows/horizons/activity/neighbor recomputed; compare asserts identity checks, `masks_equal`, ≤1e-6 diffs and unchanged input bytes |
| 3.2 r2 align-v2 positive with an independent v2-format reference | `tests/test_runner_cli.py::R2AlignV2Tests.test_r2_reference_aligns_without_reading_source_data`; `_write_v2_log` test helper | `_write_v2_log` now derives `context_id_counts`/`joint_contexts`/`context_cartesian_size`/grid flags from the supplied keys instead of hardcoding one context — identical results for r0/region, correct for multi-context r2. Reference is computed from raw signal with independent NumPy formulas; alignment runs after the source files are deleted; 1e-12 tolerance and byte-stable reference |
| 3.3 r2 check negatives and safe destinations | `tests/test_runner_cli.py::R2AlignV2Tests` (no-r2 reference, missing manifest → `limited`, source identity mismatch, metric perturbation) and `R2CheckContractTests` (identity/mask mismatch, prediction/metric beyond tolerance, report collision, report inside input, CLI nonzero for failed/mismatch/limited) | `failed`/`mismatch`/`limited` semantics, nonzero CLI exit, failure reports retained, no tolerance relaxation, inputs byte-identical |
| 4.1 documentation of the three granularities, `r2_id`, r2 development example, check-reference scope, authorization | `README.md` §4.5 (three datasets, context keys, r2 development example, expanded **Check reports** + new **r2 authorization** paragraph); `research/phases/P01/execution-guide.md` §7 | T004 two-dataset history and `protocol.md` normative text left untouched; formal r2 run explicitly requires separate authorization |
| 4.2 minimal-dependency smoke extended to r2 | `tests/test_runner_cli.py::CliEndToEndTests.test_minimal_dependency_smoke_for_all_schemas` (renamed from `..._both_schemas`) | blocker `sitecustomize.py` blocks sklearn/torch/PyG/DGL/graph_method in parent and worker; r2 nodes.parquet checked for `r2_id`; no new required dependency, no GPU or repo graph data |
| 4.3 full CPU baseline regression | `evidence/test-4.3-full-suite.log` | see Checks Run |
| 5.1 reproducible fixed-seed scale fixture | `evidence/generate_r2_scale_fixture.py`; `evidence/scale-fixture-generation.log`; `evidence/scale-fixture-manifest.json`; data under `scratch/r2-scale-fixture/` (gitignored) | seed 20261011, `52 x 2335 x 36`, 121,420 unique nodes, complete grid, 52,000 in-context edges covering 104,000 nodes / 17,420 isolated; refuses any output inside `research/runs`; only NumPy/pandas/PyArrow |
| 5.2 r2-scale development cost measurement | `evidence/scale-run.log`; `evidence/scale-run-cost.json`; full run under `scratch/r2-scale-run/r2-scale-dev-001/` | public entry, independent `_worker` process, `--purpose development --ridge-backend numpy`, explicit fixture paths and `--runs-root scratch/...`; `M=2,306,980`; synthetic and explicitly not real r2 cost or a formal run |
| 5.3 implementation handoff | this file | main spec Purpose already lists `r2/count`; the delta MODIFIED/RENAMED block carries the r2 behavior and the replacement of the old r2-rejection scenario until archive sync |

## Checks Run

Environment for every Python check: conda env `job-sdf-baseline`, Python 3.11.17,
NumPy 1.26.4, pandas 2.2.3, PyArrow 17.0.0, macOS 27.0.1 arm64, 10 CPUs, 16 GB
RAM. Working directory `/Users/watuji/da_chuang/repos/benchmark` unless noted.
BLAS thread variables are pinned to 1 by the CLI/worker.

| Command | Working directory / setup | Result / evidence | Run time or revision |
| --- | --- | --- | --- |
| `python -m unittest discover -s benchmark/nograph_baseline/tests -p test_protocol.py` | job-sdf-baseline | OK, 11 tests | this session, dirty HEAD `57275e7` |
| `... -p test_data.py` | job-sdf-baseline | OK, 38 tests | this session |
| `... -p test_coverage.py` | job-sdf-baseline | OK, 26 tests | this session |
| `... -p test_runner_cli.py` | job-sdf-baseline | OK, 122 tests | this session |
| `python -m unittest discover -s benchmark/nograph_baseline/tests -v` (task 4.3) | job-sdf-baseline | **OK, 238 tests, 35.077 s, skipped=2**; log `evidence/test-4.3-full-suite.log`. Skips are `test_ridge.OptionalSklearnTests` (`optional scikit-learn backend is not installed`) — expected, sklearn is optional | this session |
| `python openspec/changes/add-r2-count-baseline/evidence/generate_r2_scale_fixture.py` | job-sdf-baseline; writes `scratch/r2-scale-fixture/` | exit 0; 121,420 nodes / grid complete; demand sha256 `e09134fad7b29498bf3d8afe74af541876b251edd6d29a618b43871e5ebb9a26` (3,379,697 B), graph sha256 `517d029328e254e9f82c4b28c53f03c38a7f42becfad48e6a5015f3dbe981ae9` (22,040 B); log `evidence/scale-fixture-generation.log` | this session, seed 20261011 |
| `python -m benchmark.nograph_baseline run --data-name r2 --mode count --seed 0 --run-id r2-scale-dev-001 --purpose development --ridge-backend numpy --demand-path scratch/r2-scale-fixture/demand/r2.parquet --graph-path scratch/r2-scale-fixture/graph/r2.parquet --runs-root scratch/r2-scale-run` (task 5.2) | job-sdf-baseline; `/usr/bin/time -p`; independent worker | exit 0, status `success`; wall 2.56 s (`real`), worker total 2.339 s; demand_read 0.137 s, coverage_read 0.075 s, preprocessing 0.111 s, naive 0.012 s, ridge_fit 0.487 s, inference 0.008 s, metrics_output 0.925 s; peak RSS **1,300,463,616 bytes** (`resource.getrusage(RUSAGE_SELF).ru_maxrss`, native unit bytes on Darwin); `M=2,306,980 == expected`; all artifacts present; `evidence/scale-run.log`, `evidence/scale-run-cost.json` | this session |
| `openspec validate add-r2-count-baseline` | repo root | `Change 'add-r2-count-baseline' is valid` | this session |
| Scope check: `git status --short research/phases/P01/protocol.md research/runs research/archives openspec/changes/archive` and `find research/runs -newermt "2026-10-11 17:50" -type f` | repo root | all empty: protocol text, existing `research/runs`, sealed `research/archives/*.tar.gz` (mtimes 2026-10-08) and historical OpenSpec archives unchanged | this session |

Not run (honestly unexecuted): the optional scikit-learn backend, any formal
`r2` run, any real `r2.parquet` analysis, research-record updates, sealing,
commits or pushes. `dataset/demand/r2.parquet` and `dataset/graph/r2.parquet`
exist but were never opened by this implementation or its checks.

## Verification Reminders

- **Real CLI, real worker.** `R2DevelopmentRunTests` launches
  `python -m benchmark.nograph_baseline run` as a subprocess, so the r2 path is
  exercised through argparse, the spec JSON hand-off and `_worker`, not just
  `runner.execute_run`.
- **Schema comparison is structural.** `test_output_schema_matches_r0` compares
  the artifact file set and JSON key paths with list indices and context keys
  (`r0_id`/`r2_id`/digit keys) collapsed. It checks shape, not values; the value
  checks live in the other methods.
- **`_write_v2_log` changed.** The test helper now computes audit context fields
  from the supplied keys. For r0/region this is numerically identical to the old
  hardcoded single-context values, but it is shared by several pre-existing
  align-v2 tests — re-run those when auditing the diff.
- **Test-order sensitivity in 3.1.** `test_recompute_r2_saved_metrics_without_source_or_refit`
  unlinks the class-level fixture demand/graph files and restores them in a
  `finally` block to prove no source read. Refactors must preserve the restore.
- **No production fix in 2.4.** The invariance tests passed against unmodified
  data/coverage/runner/check code; there is no failing r2 case that required a
  narrow module fix, and none was invented. If a verifier expects a code change
  there, the expectation should be reconciled with this evidence.
- **Scale evidence is synthetic and outside Git.** The full 121,420-node run and
  fixture live under gitignored `scratch/`; only the small generator, manifest,
  logs and cost record are in the change directory. Reproduce with the generator
  command above, then the documented run command; deleting `scratch/` removes
  the raw run but not the recorded hashes/costs.
- **Main spec not yet synced.** `openspec/specs/nograph-baseline-entry/spec.md`
  still shows the old r0/region-only requirement text and the "requests r2 …
  rejects" scenario; the change delta MODIFIED/RENAMED block supersedes it and
  archive sync is intentionally deferred. Its Purpose already includes
  `r2/count`.
- **Tolerances unchanged.** recompute/compare keep 1e-6 and align-v2 keeps
  1e-12; the new tests assert these values rather than relaxing them.
- **Environment.** Python checks require the `job-sdf-baseline` conda env (the
  repo's default `python` has no PyArrow) and no GPU, PyTorch/PyG/DGL, or
  repository graph data. The heavy scale run peaked at ~1.21 GiB RSS.
- **No research bookkeeping touched.** `DELEGATION.md`, `research/state.md`, the
  phase plan and research task status were not modified; software evidence here
  is not P01-T006 research acceptance.
