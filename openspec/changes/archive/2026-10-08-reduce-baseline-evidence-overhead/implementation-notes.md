# Implementation Notes

- Change: reduce-baseline-evidence-overhead
- Schema: spec-driven
- Store: local (nearest repo root `/Users/watuji/da_chuang/repos/benchmark`)
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark`
- Updated: 2026-10-08T07:47:47Z
- Implementation revision: HEAD `715d44de43d14b0dcc5dfc525955689af9e0cc00` with a dirty worktree (the implementation edits below plus pre-existing research-maintenance edits to `.gitignore`, `DELEGATION.md`, `research/archives/index.md`, the schema-v2 archive manifest and the deleted archive `.sha256` sidecars). No commits were made.
- Progress: 9/9 tasks complete. Nothing is deferred, narrowed, or carried as an exception.

## Scope Of Changes

| File | Change |
| --- | --- |
| `research/archives/seal_20261007_baseline.py` | `verify` dispatches on index `schema_version`: v1 path retained (sha256 + sidecar + full member table), new Git-backed v2 path (committed package blob at `storage_identity.commit`/`record.package`, declared exclusions, pre-extraction member safety/uniqueness/count checks, temp-only restore). `seal` stays schema v1 with its overwrite refusal. |
| `benchmark/nograph_baseline/artifacts.py` | `default_runs_root`/`formal_runs_root`/`development_runs_root`/`is_within`; `runtime_source_paths`; `scoped_git_status`; `capture_source` (replaces `capture_untracked_source`); `checker_source_identity`; `capture_git` no longer reads a whole-repo diff; `write_git_snapshot` writes only `git-commit.txt`/`git-status.txt`. |
| `benchmark/nograph_baseline/runner.py` | `RunSpec.purpose` + `retain_candidates`; `_resolve_runs_root`/`_validate_purpose` before reservation; `capture_source` wiring; `purpose` in status/provenance/summary; candidate arrays only when `retain_candidates`. |
| `benchmark/nograph_baseline/cli.py` | `run --purpose {formal,development}` + `--retain-candidates`; check subcommands get mutually exclusive `--report` / `--run-id` (+ documented `--runs-root`) and return JSON with `report_path`. |
| `benchmark/nograph_baseline/checks.py` | Single exclusive JSON report envelope (`_envelope`/`_failure_envelope`/`_write_report`/`_finish`, `resolve_report_path`, `_reject_unsafe_destination`); all three `command_*` rewritten to report output; recomputed metrics/gains embedded in the report; `purpose`/`retain_candidates` excluded from the compare semantic-config gate (persistence/output-root choices only). |
| `benchmark/nograph_baseline/tests/test_runner_cli.py` | Updated for the new layout/API and extended with the delta scenarios (task 4.2). |
| `README.md` | Section 4.5 rewritten: purpose, retention, provenance, report paths/aliases, schema-v2 recovery utility, external-SHA256 export note, no automatic packaging. |
| `openspec/changes/reduce-baseline-evidence-overhead/tasks.md` | Task checkboxes for completed work. |

Nothing under `research/runs/`, `research/archives/*.tar.gz`, `openspec/specs/`, `DELEGATION.md` or the research records was modified.

## Implementation Map

| Task / requirement / scenario | Code and tests | Decisions / context |
| --- | --- | --- |
| 1.1 schema-v2 archive verification | `research/archives/seal_20261007_baseline.py` (`verify`, `verify_v1`, `verify_v2`, `_restore_package`, `_package_exclusion`) | Package byte identity comes from the committed blob at `storage_identity.commit:<record.package>`; no sidecar or member hash table is read or written. Only a schema-v2 index whose `task_id` is `P01-T004` must cover exactly the 24 `RUN_IDS`; synthetic fixtures with another task id may use a smaller run set. `artifacts-sha256.json`/`events.jsonl` are permitted members (embedded-manifest exclusions) while `__pycache__`/`.DS_Store`/`._*` are rejected. |
| 2.1 purpose isolation | `runner.RunSpec.purpose`, `_resolve_runs_root`, `_validate_purpose`; `cli --purpose`; `artifacts.default_runs_root` | Rejection happens before `RunDirectory.reserve()`, so no directory is created. Paths are resolved (symlink aliases included) before comparison. Purpose only selects the root and labels the run. |
| 2.2 scoped provenance | `artifacts.runtime_source_paths`, `capture_source`, `scoped_git_status`, `_source_entry`, `checker_source_identity`; `runner` `source_capture` stage | Runtime set = imported baseline modules + launcher entry points + the actual protocol path, minus `tests/`/caches; tracked deletions within the scope are added. Clean committed files get `git_reference{commit,path,sha256}` and are not copied; scoped staged/unstaged changes (including deletions) go to one `git-diff.patch`; untracked/unknown files are copied to `code-untracked/`. `source-sha256.json` shape and semantics are unchanged so saved-only validators still work. |
| 2.3 candidate retention | `runner._save_model_artifacts`; `RunSpec.retain_candidates`; `cli --retain-candidates` | Selected model + preprocessing statistics always saved; `selection.json` keeps all five scalar candidate rows and the winner. Only the losing candidate arrays are gated by the flag. |
| 3.1 compact exclusive reports | `checks._write_report`, `_envelope`, `_failure_envelope`, `_finish`, `command_recompute/compare/align_v2` | `os.open(O_CREAT|O_EXCL)` publishes one complete JSON file; no check run directory, `status.json`, `summary.md`, source snapshot, environment copy or artifact manifest is produced. Recompute embeds `recomputed_metrics`/`recomputed_relative_gains`. Invalid saved input after a safe destination choice yields a `status: "failed"` report; an invalid destination yields nothing. |
| 3.2 report paths and aliases | `checks.resolve_report_path`, `_reject_unsafe_destination`; `cli._add_report_output_options`, `_check_output`, `_print_check_result` | `--report` and `--run-id` are mutually exclusive and one is required (argparse enforces it, `resolve_report_path` re-checks programmatically). Legacy alias resolves to `<runs_root>/<run_id>.json` with default root `research/reports/nograph-baseline/`. Existing/symlink destinations, paths inside input run directories, and a path equal to the align reference are rejected before any write. |
| 4.1 documentation | `README.md` section 4.5 | Documents every new flag, states that Git-external package export needs its own SHA256, and that sealing/Git/network/recovery actions are separately requested. No automatic pack/commit/push/restore sequence exists in the baseline package. |
| 4.2 test suite | `benchmark/nograph_baseline/tests/test_runner_cli.py` | Existing adversarial numeric/identity/null/tolerance coverage kept; layout/API expectations updated and delta scenarios added. |
| 4.3 handoff | this file | `openspec validate --strict` passes; T004 packages and readable entries verified unchanged. |

## Checks Run

| Command | Working directory / setup | Result / evidence | Run time or revision |
| --- | --- | --- | --- |
| `git worktree add --detach /tmp/nb-head-baseline HEAD` then `python -m unittest discover -s benchmark/nograph_baseline/tests -v` | pristine HEAD worktree | 147 tests, 2 skipped, **1 pre-existing failure** (`RunnerArtifactTests.test_source_and_environment_capture`: `code-untracked/manifest.json["files"]` is empty because the baseline files became tracked). Pre-change baseline only; the rewritten test now passes. The temporary worktree was removed. | HEAD `715d44d` |
| `python3 research/archives/seal_20261007_baseline.py verify` | repo root | `Verified 24 git-backed packages and restored 780 byte-identical files` (rc 0, ~1.0 s), using only the committed package blobs — the deleted `.sha256` sidecars are not required. | 2026-10-08 |
| `/tmp/v2fixture.py` (synthetic Git-backed schema-v2 fixture) | temp Git repo | clean package passes; rejects P01-T004 index with fewer than 24 runs, changed package bytes, missing package, member-count mismatch, unresolvable commit and unknown `schema_version`. | 2026-10-08 |
| `/tmp/v2members.py` (members committed into the fixture) | temp Git repo | rejects duplicate, `..`-traversing, absolute, symlink, hardlink, `__pycache__`, `.DS_Store` and `._*` members with explicit messages, before restoration. | 2026-10-08 |
| `/tmp/source_harness.py` | disposable Git repo + `artifacts.capture_source` | staged modification, unstaged deletion, untracked runtime file and dirty protocol are recoverable (patch or saved copy); a clean committed file gets a `git_reference` and no copy; an unrelated dirty research record and `tests/` never enter the scoped patch. | 2026-10-08 |
| `/tmp/nogit_harness.py` | non-Git temp dir | `identity_available: false`, `commit: null`, explicit errors, relevant content saved under `code-untracked/`; no invented commit or clean state. | 2026-10-08 |
| `/tmp/purpose_parity.py` | r0 and region fixtures | formal vs development predictions, `metrics.json` and `selection.json` identical for both dataset schemas; development status labelled `development`. | 2026-10-08 |
| `/tmp/smoke_runner2.py` | r0 fixture | development default root is `<repo>/scratch/nograph-baseline/<run_id>`; a development root inside `research/runs` (and via a symlink alias) is rejected with no directory created; unknown purpose rejected; formal default root is `<repo>/research/runs`. | 2026-10-08 |
| `/tmp/retention_parity.py` | r0 and region fixtures | default run has no `candidates/` directory; `--retain-candidates` produces 5 labelled `parameters.npz`/`validation.npy` pairs; predictions, candidate table and winner identical; 5 score rows in both. | 2026-10-08 |
| `/tmp/legacy_checks.py` (packages restored to a temp dir) | `p01-r0-sharedridge-001`, `-002`, `p01-r0-alignment-001` extracted from the sealed `.tar.gz` | `recompute` ok, `compare` ok with all identity checks true, `align-v2` ok over 411 compared fields; input trees byte-identical before/after; exactly one report file per command. Confirms legacy-layout saved runs stay readable. | 2026-10-08 |
| `/tmp/smoke_checks.py` | r0 fixture | report envelope keys, embedded recomputed metrics/gains, collision refusal, legacy alias, budget conflict, invalid alias id, destination inside input, missing-input failure report, `compare`, `align-v2`; input tree unchanged and exactly one output file per check. | 2026-10-08 |
| `/tmp/cli_e2e.py` | subprocess CLI, r0 fixture | `run --purpose development --retain-candidates` rc 0; `recompute --report` rc 0 with `report_path` in stdout; legacy alias rc 0 at `<root>/<id>.json`; missing input rc 1 with failure report; collision rc 1 with original bytes intact; conflicting flags rc 2 before any write; development root inside `research/runs` rc 1 with no directory; `compare` rc 0. | 2026-10-08 |
| `openspec validate reduce-baseline-evidence-overhead --strict` | repo root | `Change 'reduce-baseline-evidence-overhead' is valid`. | 2026-10-08 |
| `git status --porcelain -- research/runs 'research/archives/*.tar.gz'` | repo root | empty output: the 24 sealed packages and all readable run entries are byte-for-byte unchanged. | 2026-10-08 |
| `python -m unittest discover -s benchmark/nograph_baseline/tests -v` | repo root, post-change suite | `Ran 175 tests in 17.083s` / `OK (skipped=2)` — 0 failures, 0 errors. Run independently by the apply model after the test-update work; the two skips are the pre-existing optional-scikit-learn tests (not installed). | HEAD `715d44d`, dirty worktree |

### Suite composition

175 tests (was 147 at HEAD). 28 new delta methods: `PurposeDeltaTests` (6), `CandidateRetentionDeltaTests` (2, both schemas), `SourceCaptureDeltaTests` (6), `CheckReportContractTests` (11), plus legacy-alias coverage in three existing classes. The only removed assertions were four obsolete-layout expectations (`code-untracked/manifest.json` content, check-directory `provenance.json`, check `command.json`); no test method was removed and the 15 adversarial `status == "mismatch"` assertions, the null-semantics coverage, the tolerance checks and the identity-mismatch checks are intact.

### Known verification limits

- The live-worktree clean-reference assertion needs at least one clean committed runtime file (9 currently); the clean/modified/untracked/unknown matrix is additionally proven deterministically in disposable Git repositories.
- The CLI default legacy report root (`research/reports/nograph-baseline/`) is asserted through `checks.default_reports_root` rather than written end-to-end, to avoid polluting the repository; the alias itself is exercised with a temporary `--runs-root`.
- Byte-identical input preservation after a failure is asserted for `recompute`; `compare`/`align-v2` missing-input failures assert the failure report and non-ok status, while their successful cases assert unchanged input tree hashes.
- The optional scikit-learn backend remains uninstalled, so those two tests stay skipped (pre-existing environment limit, not dropped coverage).


## Verification Reminders

- `checks` no longer produce a check directory; any consumer expecting `result["run_dir"]` or a `provenance.json` inside a check output will not find one. Model runs still return `run_dir`.
- The checker identity in every report is honest but **dirty in this working tree** (`scoped_dirty: true` for the modified baseline files). When the scoped patch exceeds 20000 bytes the envelope sets `patch_included: false` with `patch_omitted_reason` and only `patch_bytes`; this is intentional and not a missing-identity claim.
- `compare` treats `purpose` and `retain_candidates` as non-scientific invocation/persistence fields (excluded from the semantic-config gate, alongside `run_type`). Every numeric, identity, environment, source and prediction comparison is unchanged and still strict.
- `source-sha256.json` is deliberately unchanged in shape; saved-only validators that consume `sources.protocol.sha256` still work. `provenance.json` now carries `source_capture` instead of `untracked_source`.
- `code-untracked/manifest.json` is written only when some content was actually saved.
- The archive utility's schema-v2 run-set check keys on `task_id == "P01-T004"`; a v2 index with a different task id verifies exactly the runs it declares. Confirm this is the intended coverage rule for the real index.
- `_restore_package` reads each member fully into memory before writing; package sizes here are ≤ ~8.8 MB compressed, but a much larger package would raise peak memory.
- The updated test suite is the primary evidence for the delta scenarios; re-run it rather than relying on the ad-hoc harnesses above, which live under `/tmp` and are not committed.
- No real-data experiment, no source-demand read for checks, no research-record edit, no commit and no push was performed.
