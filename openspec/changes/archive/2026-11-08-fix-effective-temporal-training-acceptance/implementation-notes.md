# Implementation Notes

- Change: fix-effective-temporal-training-acceptance
- Schema: spec-driven (spec-driven artifacts: proposal, specs, design, tasks)
- Store: local (no registered OpenSpec store; repo-local change root)
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark`
- Updated: 2026-11-08T11:05:00+08:00
- Implementation revision: `fa45639f7dacc31e7d4a85035bee862d2028cc9b` with a dirty
  worktree (README and the public entry modified; `temporal/` package and the
  new fixture suite untracked). No commit or push was made by this apply.
- Progress: 19/19 tasks implemented; all checks below were run in this session.

## Implementation Map

| Task / requirement / scenario | Code and tests | Decisions / context |
| ----------------------------- | -------------- | ------------------- |
| 1.1 staged operations, development default, migration error, path aliases | `benchmark/multivariate_time_series/temporal/cli.py`, `benchmark/multivariate_time_series/effective_temporal_training.py`; `tests/test_temporal_cli.py::CliContractTests`, `tests/test_effective_temporal_training.py::PublicSurfaceTests` | `preflight|fit|select|diagnose|report|recompute|compare|resume`; legacy `train/compare/load_checkpoint` raise a migration error; unknown first argument exits 2 with help; development output resolving into `research/runs/` is rejected before any directory exists |
| 1.2 canonical r0/region/r2 identity, month calendar, training-only RMS | `temporal/data.py`; `tests/test_temporal_data.py::CanonicalIdentityTests`, `TrainingRmsTests` | Reuses P01 `load_demand`/`from_arrays`, `MAIN_SPLIT` and months; rejects duplicates, missing/extra months, negatives, non-finite values; canonical ascending keys keep identical skills in different contexts distinct |
| 1.3 fit receives only train/validation; test labels built by report only | `temporal/data.py::FitArrays.assert_no_test_labels`, `runner.run_fit`, `runner.run_report`; `tests/test_temporal_data.py::StageBoundaryTests` | fit observation slice stops at 2023-06 (month 30); sentinel test patches `TemporalData.report_arrays` to raise while fit, select and diagnose run |
| 2.1 complete-window N*3 updates, 19 updates/epoch, chunk order, Adam + full-gradient clip | `temporal/engine.py::squared_error_sum`, `_train_epoch`; `tests/test_temporal_engine.py::WindowOptimizationTests` | Contiguous canonical chunks, one step per window, pre-clip norm/clip flag recorded per update; uneven chunk matches the complete-window reference within 1e-6; all-zero training gives scale 1 with finite, order-independent repeated-window predictions |
| 2.2 deep-copied best snapshot, earliest tie, init not selectable, reproducible restore | `temporal/engine.py::BestSnapshot/_maybe_select/_finish`, `temporal/model.py::deepcopy_state`; `tests/test_temporal_engine.py::BestSnapshotTests` | Controlled "early best, later worse" hook proves later steps do not mutate saved model/optimizer; an exact-tie unit check keeps the earliest step>0; restored best reproduces saved validation metrics exactly |
| 3.1 seed-0 two-rate selection, smaller-rate tie, winner-as-a link, a/b identities | `temporal/selection.py`; `tests/test_temporal_selection_diagnostics.py::SelectionTests` | Exactly two screening seed-0 candidates over `{1e-3,3e-3}`; b never selects; failed candidates are retained but leave the selection `incomplete` |
| 3.2 init/10/50/100/best fixed-parameter scores, full history, mixed-parameter loss label | `temporal/engine.py::_fit_diagnostics/_record_score`, `runner.run_fit`; `tests/test_temporal_selection_diagnostics.py::LongTrajectoryTests`, `tests/test_temporal_engine.py::test_diagnostic_node_scores_and_history` | 100-epoch development override trajectory records all diagnostic nodes; `protocol_controls.complete=false` labels the override |
| 3.3 P02 §5 gates, zero denominators, b80/b100, a/b bound, appendix | `temporal/diagnostics.py`, `runner.run_diagnose`; `tests/test_temporal_selection_diagnostics.py::DiagnosticsGateTests` | Threshold edges at exactly 10%/5%/1%; zero Zero-MAE is `incomplete` (all-zero diagnostic), missing evidence never passes; Ridge compatibility is identity-checked and required for readiness |
| 4.1 explicit report, formal prechecks, four windows 24..27 | `temporal/report.py`, `runner.run_report`; `tests/test_temporal_report.py::ReportTests` | Test arrays `[4,N,3]`, target multiplicities 1,2,3,3,2,1; formal blockers computed before reserving output; development report labelled `development_incomplete` |
| 4.2 inherited metrics, raw + separately-labelled clipped, groups/counts, coverage identity | `temporal/report.py::build_report`; `tests/test_temporal_report.py` (coverage, empty groups, same-skill-two-contexts, clipped) | Missing coverage stays `unavailable` and is never converted to an all-isolated mask; empty groups report `null` metrics with `status=empty` |
| 4.3 format-v2 exclusive output, statuses, real data source, provenance, readable entries | `temporal/artifacts.py`, `runner._write_preamble`; `tests/test_temporal_artifacts_checks.py::ArtifactIdentityTests` | Collisions refused and existing evidence unchanged; provenance captures scoped runtime source, `git-diff.patch`, protocol SHA256, environment/threads; `.gitignore` untouched (generic policy test) |
| 4.4 saved-only recompute/compare, identity before numbers, exclusive report | `temporal/checks.py`; `tests/test_temporal_artifacts_checks.py::CompareIdentityTests`, `RecomputeTests` | recompute/compare import no torch/pandas and read no demand/graph data (tested with those modules blocked); identical predictions cannot hide seed/protocol/environment/source mismatches; destinations inside inputs are refused; comparing two completed report runs bounds validation and test predictions |
| 5.1 machine-readable preflight, single worker lock, thread setup, dependency/resource checks | `temporal/resources.py`, `temporal/cli.py::_run_stage`; `tests/test_temporal_resources_recovery.py::PreflightTests`, `tests/test_temporal_cli.py::PreflightCliTests` | Preflight works without real data; dependency and resource failures are explicit; stale lock requires `--takeover-stale`; formal purpose rejects injected resource readings |
| 5.2 watchdog, persistent ledger, 10-epoch cost gate, estimation and stop lines | `temporal/resources.py` (`Watchdog`, `Ledger`, `cost_gate`), `runner` hooks; `tests/test_temporal_resources_recovery.py::LedgerAndWatchdogTests`, `FitResourceTests` | Independent sampler thread reacts at epoch boundaries; measured/estimated/replayed fields separated; sample resumes the same trajectory; unmeasured blocks stay `unknown` |
| 5.3 atomic last checkpoint, independent of best, legacy/corrupt rejection | `temporal/checkpoints.py`; `tests/test_temporal_resources_recovery.py::CheckpointTests` | Temp file + fsync + rename; publication failure keeps the previous complete version; legacy (no format version), truncated and best-as-last payloads are all rejected |
| 5.4 parent-linked resume with inherited budget | `temporal/recovery.py`, `runner.run_fit(operation=resume)`; `tests/test_temporal_resources_recovery.py::ResumeTests` | Mid-epoch interruption resumes from the last complete epoch; final parameters/best/validation match uninterrupted training; parent directory bytes unchanged; exhausted budget and mismatched data are refused |
| 6.1 CLI chain, three schemas, two encoders, short development smoke, saved-only checks, baseline regression | `tests/test_temporal_cli.py::DevelopmentChainTests`, `tests/test_effective_temporal_training.py::StagedChainTests`; baseline suite run unchanged | All outputs in temporary directories; no real data matrix or `research/runs/` artifact created |
| 6.2 README section and research-side handoff | `README.md` §4.7; this file (materials list below) | Existing §4.6 numbering preserved because archived records reference it |
| 6.3 strict validation and evidence package | `openspec validate ... --strict --json --no-interactive` below | Change valid, 0 issues; acceptance limited to software readiness |

## Checks Run

| Command | Working directory / setup | Result / evidence | Run time or revision |
| ------- | ------------------------- | ----------------- | -------------------- |
| `python -m unittest discover -s benchmark/multivariate_time_series/tests` | repo root, `/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python` (Python 3.11.17, torch 2.14.1, numpy 1.26.4, pandas 2.2.3, pyarrow 17.0.0, psutil 7.2.2); no real demand/graph files | 103 tests, all pass (≈53 s); exercises r0/region/r2 Parquet fixtures, the CLI chain, resource/recovery failures and saved-only checks | 2026-11-08, revision `fa45639` + dirty worktree |
| `python -m unittest discover -s benchmark/nograph_baseline/tests` | same environment | 287 tests, all pass, 2 skipped (≈44 s); reused P01 helpers and baseline entry unchanged | 2026-11-08 |
| `python -m benchmark.multivariate_time_series.effective_temporal_training --help` | repo root | exit 0, lists `preflight fit select diagnose report recompute compare resume`; no data needed | 2026-11-08 |
| `python -m ... fit --data-name r0 ... --purpose development --output-root <research/runs>` | fixture Parquet | nonzero exit, no directory created in `research/runs/` (also via symlink alias) | 2026-11-08 |
| `openspec validate fix-effective-temporal-training-acceptance --type change --strict --json --no-interactive` | repo root | `valid: true`, `issues: []`, 1/1 passed | 2026-11-08 |

## Verification Reminders

- **No real-data or formal execution happened.** No formal `fit`, no
  `research/runs/` output, no sealed material, no research-state edit, no commit
  or push. `learning_ready` was never computed from real results.
- **Formal report path is only partially exercised.** The formal refusal path is
  tested through `report.formal_report_blockers` and a formal request on a
  development trajectory; a full 100-epoch hidden-32 formal trajectory was not
  run (that would create formal evidence outside this change's scope).
- **Machine resource reality.** This host measured 5.95–6.05 GiB available
  memory, i.e. at or just below the protocol's 6 GiB startup threshold. CLI
  rehearsal tests therefore inject development-only
  `--memory-available-bytes`/`--disk-free-bytes`; a formal preflight on this
  machine may legitimately fail while other applications are running.
- **Coverage evidence is optional and explicit.** `report` without `--graph` or
  `--mask-bundle` records neighbor metrics as `unavailable`; a verifier should
  confirm this is the intended reading of "missing coverage must not become an
  all-isolated mask".
- **Ridge evidence is external.** `diagnose --ridge` expects an
  identity-checked JSON record (dataset, data SHA256, node-keys SHA256,
  validation starts, selection record, validation MAE/MSE). Without it
  readiness stays `incomplete` by design.
- **Diagnostics identity**: each `diagnose` reserves a fresh
  `<block>/diagnostics/<diagnostics-id>/` directory and updates the
  `<block>/latest-diagnostics.json` pointer; a repeated id is refused, and the
  compact `--report` path is exclusive. `report` follows the pointer unless
  `--diagnostics` names an explicit execution. Confirm this evidence ownership
  and pointer semantics.
- **Cost gate measurements are real-time on POSIX.** Stop/pause behavior is
  exercised with injected setup time, sampler failures and RSS breaches; the
  controller-side `subprocess` monitor and Windows path are not exercised on
  this macOS host.
- **Block/batch ledger defaults** to `p02-t006`; a research-side formal batch
  must pass its own `--batch-id` and `--ledger`.
- **README numbering**: the new entry is §4.7 so the existing §4.6
  (graph-value skeleton) reference in `research/archives/index.md` stays valid.

## Research-Side Handoff (task 6.2)

Preflight/run materials the research side must supply before a real block (none
of these were read or created by this change):

1. Environment: dedicated CPU environment (e.g. `job-sdf-baseline`) with
   NumPy, pandas, PyArrow, a CPU torch build and psutil; single-thread settings
   are applied by the CLI before torch import.
2. Authoritative inputs: the P02 protocol
   (`research/phases/P02/protocol.md`), the dataset demand Parquet for the block
   (`dataset/demand/{r0,region,r2}.parquet`), and — only for neighbor diagnostics
   — the raw graph Parquet (`dataset/graph/<name>.parquet`) or a validated mask
   bundle. `--data` may point at a relocated copy; the actual source SHA256 is
   recorded and compared.
3. External evidence: an identity-checked Ridge validation JSON
   (`--ridge`) if neural vs Ridge compatibility must count towards readiness.
4. Batch identity: `--batch-id`, `--ledger` path (persistent active-time ledger),
   and the cumulative budget already consumed by earlier blocks.
5. Authorization: explicit formal-purpose authorization, the block order
   `r0 → region → r2` and `GRU → LSTM`, and at most 7 fits per block (2
   screening + 2 extra seeds a + 3 b). No command schedules that matrix.
6. Commands: `preflight` (fail-fast, machine-readable) then `fit` (two seed-0
   candidates), `select`, `fit` for a seeds 1/2 and b seeds 0/1/2, `diagnose`,
   and only after frozen selection + passing gates, `report`; then `recompute`
   and `compare` from saved evidence. Exact flags are in README §4.7; `--help`
   is authoritative.
7. Outputs and hand-back: development rehearsal writes ignored
   `scratch/effective-temporal/`; formal evidence writes `research/runs/<id>/`
   where only `summary.md`, `provenance.json`, `command.json` and `report.json`
   are Git-readable under the existing generic policy. The complete arrays,
   `weights/best.pt`, `recovery/last.pt` and `arrays-sha256.json` stay local and
   must be delivered/sealed by the research side, together with the
   `diagnose` report and cost records.
8. Still unknown on this machine: real per-block timings (steady-state
   epoch 6..10 medians), actual single-fit cost, whether 12 h cumulative budget
   suffices, and whether real trajectories pass the §5 learning gates.
