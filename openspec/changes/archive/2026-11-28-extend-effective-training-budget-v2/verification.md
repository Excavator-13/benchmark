# Implementation Verification

- Change: extend-effective-training-budget-v2
- Schema: spec-driven
- Verdict: **PASS**
- Verified at: 2026-11-27 (Asia/Shanghai)
- Implementation and planning root: `E:\大创\benchmark`
- Verified revision: `4993778f0fb2a11cbfc0339ad265f489479a1d3c` with the current uncommitted implementation, tests, README and task updates

## Summary

All ten findings are verified resolved. Preflight refused the Windows aliases of the deferred-bill file without modifying the ledger. RSS sampling during normal worker exit preserved the completed run and terminal bill. OpenSpec strict validation and all 68 targeted regressions passed. Verification used synthetic and temporary inputs.

## Verification Basis

| Path or scope | Revision / content fingerprint / file inventory |
| --- | --- |
| Repository root and in-repository OpenSpec change | Same before/after inventory of 2,495 Git-tracked or non-ignored files |
| [verification-state.json](verification-state.json) | SHA-256 `8ccfc900c933a9337e155ebf6cfbb18825b631ad73bc9dd1688f3d8a7d5456cf` |
| `research/phases/P02/protocol-v2.md` | LF-normalized SHA-256 `c454954e9443cc363ebf94a23809d8ee003ecdc7844b693d38cb5f304db283d0` |
| `research/phases/P02/protocol.md` | LF-normalized SHA-256 `2f583a3a7f771cfe82c36eb8983e37bfadf65c7c1ee62355d97bdae34872a5f2`, matching the inherited identity declared by v2 |

Incremental verification matched the previous snapshot hash `f8c4cbef32e64973a1c736f0c7fbe66232d4a286b9551ae85984ff8e99619971` and found three modified inputs. They were `temporal/cli.py`, `temporal/resources.py` and `tests/test_temporal_cli.py`. The four OpenSpec artifacts, protocol documents, README, training engine, saved-evidence validators and baseline implementation retained their prior hashes. This run targeted the CLI, fit/controller billing, preflight, recovery and live budget checks. Previous independent evidence covers the frozen scientific controls, optimizer behavior, exact 200-epoch completeness, saved-array comparisons and baseline behavior. The staged synthetic chain was rerun because it exercises the changed public controller and watchdog.

OpenSpec 1.16.1 resolved the change and its four context files from the repository-local planning root when run outside the sandbox. The sandbox presented the installed schema file and its directory under different canonical paths, which caused the initial schema-resolution error. Escalated test runs also avoided Windows access failures in sandbox-created temporary directories.

The verification host used Windows 11 build 26200, Python 3.13.0, NumPy 2.4.2, pandas 3.1.1, PyArrow 26.0.1, PyTorch 2.6.0 and psutil 7.2.2.

Snapshot commands, from the repository root:

```powershell
# $snapshotDir is a temporary directory outside the repository.
$snapshot = '.agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py'
$state = 'openspec/changes/extend-effective-training-budget-v2/verification-state.json'
python $snapshot capture --root . --output (Join-Path $snapshotDir 'before.json')
python $snapshot compare $state (Join-Path $snapshotDir 'before.json')
python $snapshot capture --root . --output (Join-Path $snapshotDir 'after.json')
python $snapshot compare (Join-Path $snapshotDir 'before.json') (Join-Path $snapshotDir 'after.json')
```

The prior-to-current comparison returned exit 1 with three modified files. The before/after comparison returned exit 0 and `changed: false`. The after snapshot was copied to `verification-state.json`. The script used its standard workflow-file exclusions and Git inventory with no additional exclusion flags.

## Apply Handoff Review

- The handoff identifies the selected change, repository and current HEAD. OpenSpec reports 12 of 12 tasks checked. Its Windows takeover interruption predates the lock repair. The Windows takeover case passed again in this run. This run used affected tests and prior full-suite evidence. [implementation-notes.md](implementation-notes.md)
- The targeted suite includes the staged synthetic chain, public old or damaged checkpoint refusals, and recovery after a real worker is interrupted. The previous equal-array scientific-version refusal remains applicable because the saved-only validators and their fixture are unchanged.
- The recorded 900-second preparation debit, fresh preflight and fresh v2 initialization belong to the post-PASS research handoff. The software probes used temporary ledgers. Git inventory showed changes confined to the temporal package and tests, the staged entry, README and the OpenSpec change. The historical records, research protocols, T009 and legacy runners had no worktree edits.

## Checks

| Command or inspection | Result | Notes |
| --- | --- | --- |
| `openspec status --change "extend-effective-training-budget-v2" --json` and `openspec instructions apply --change "extend-effective-training-budget-v2" --json` | Pass outside the sandbox | Both selected the repository-local `spec-driven` change. Apply listed the proposal, design, delta spec and tasks and reported `all_done`. |
| `openspec validate "extend-effective-training-budget-v2" --type change --strict --json --no-interactive` | Pass | Exit 0, one valid item, zero issues. |
| `python -m compileall -q benchmark/multivariate_time_series/temporal benchmark/multivariate_time_series/effective_temporal_training.py benchmark/multivariate_time_series/tests` and `git diff --check` | Pass | Both exited 0. |
| With `PYTHONPATH=benchmark/multivariate_time_series/tests`, `python -m unittest -v test_temporal_cli test_temporal_resources_recovery test_temporal_repairs.RuntimeRepairTests test_temporal_stage_limits` | Pass outside the sandbox | Exit 0, 68 tests. Includes the staged CLI, both Windows repair cases, real controller interruption and recovery, stale-lock takeover, and budget enforcement. |
| Public synthetic r2/GRU fit with `--monitor-interval 0.05` and a trace of the real RSS sampler | Pass | Three runs observed `NoSuchProcess` after child exit 0. In each run the CLI returned 0, both status files recorded `completed`, and the bill was `finished`. See V-010. |
| Previous independent `python -m unittest discover -s benchmark/multivariate_time_series/tests -v` | Reused for unaffected behavior | 151 tests passed on the prior snapshot. The frozen controls, engine, long trajectory and saved-evidence comparisons remain covered. |
| Previous independent `python -m unittest discover -s benchmark/nograph_baseline/tests -q` | Reused | 287 tests ran with 3 skips. The baseline code and tests did not change. |
| Public `preflight --out` against the literal deferred-bill path and Windows filename aliases | Pass | All five spellings were refused with exit 2. Ledger bytes stayed identical, 1,000 effective seconds remained readable, and no deferred bill appeared. A distinct destination wrote a passing report and one measured entry. See V-008. |
| Previous public `fit --help` and `resume --help` comparison with README §4.7 | Reused | README and both argument definitions are unchanged. CLI parser tests ran again. |
| Prior independent preflight with each protocol source redirected to a missing scratch path | Reused | Each check identified the absent document. The repaired ledger and controller paths did not change the protocol checks. |

## Requirement Coverage

| Requirement / scenario | Evidence | Result |
| --- | --- | --- |
| Protocol-isolated training / canonical identity across supported schemas and invalid input before fitting | `data.py`, parser choices, `test_temporal_data.CanonicalIdentityTests` and formal 100-epoch CLI negative check. The stage-boundary tests also verified held-out data isolation. | Pass. |
| Protocol-isolated training / inherited protocol identity changes | `protocol.protocol_document_identities`, `resources.preflight`, provenance validators and checkpoint loaders. Verified ordered paths and SHA-256 values, both missing-document refusals, and a mutated saved inherited identity. | Pass. |
| Full-window optimization / early immutable best and uneven global chunk weighting | `engine.py` and `test_temporal_engine` cover earliest tie, matching optimizer state, CPU reevaluation and whole-window weighting. | Early-best and uneven-context reference tests passed. |
| Full-window optimization / formal or saved 100-epoch refusal | CLI rejects the formal request at control validation. `diagnostics` exact history and fixed score checks, `test_complete_100_epoch_artifact_is_incomplete_for_v2`. | Pass. |
| Learning diagnostics / independent thresholds, missing or zero evidence, old and new tail intervals | `diagnostics.py` and `DiagnosticsGateTests` exercise the 160/200 minima, 1% and 2-of-3 boundaries, both-zero rule, mismatched Ridge identity, repetition and missing evidence. `LongTrajectoryTests` checks 200 epochs, 3,800 updates and fixed score blocks. | Pass. |
| Auditable outputs / source unavailable, collision and failed seed, historical evidence | `artifacts.py`, `checks.py` and `runner.py` capture source/protocol/config identities, publish exclusive results and recompute saved arrays. `test_temporal_artifacts_checks` covers source isolation, collision, failure retention and four windows. Current Git inventory confirms no historical edits. | Pass. |
| Saved-only checks / hidden condition mismatch, destination refusal, equal outputs across versions | `checks.py` validates provenance before comparison, requires a destination outside inputs, and records failures. `test_temporal_artifacts_checks` covers unchanged evidence, same arrays with different identities, and post-report test differences. | Pass. |
| Resources / controlled breach and continuation after the sample | `FitResourceTests` covers stop, monitor failure, cost refusal and the same trajectory after the sample. Prior `AggregateCostTests` verified that unmeasured blocks stay unknown. `ResumeCliTests` interrupts a real synthetic worker and verifies the terminal bill with direct and deferred publication. The synchronized and repeated real-worker probes cover normal-exit RSS sampling. | Pass. Active-worker resource failures still pause. V-010 is resolved. |
| Resources / old spending plus debit exhaustion | `FitResourceTests` and `RuntimeRepairTests` cover fit, in-flight fit, controller and saved evidence, including an independent Windows reader during billing. | The controller stopped and the bill was recoverable after the Windows sharing violation. V-005 is resolved. |
| Resources / repeated or malformed debit registration | `LedgerAndWatchdogTests` and `CliContractTests` passed malformed ledger, duplicate identities, stable legacy replay and debit-preserving stale heartbeat. | Pass. |
| Resources / one worker and conflicting controllers | `ResumeCliTests` exercises shared-ledger `fit`, `resume` and `preflight` across output roots. `PreflightTests.test_worker_lock_conflict_and_stale_takeover` checks active and dead owners. | Pass. V-006 is resolved. |
| Resources / public preflight metering and helper interface | README §4.7, `resources.account_stage`, `record_helper_cost` and CLI tests cover ledger aliases, pass/fail metering and the helper. The Windows reproductions cover the literal reserved file, trailing dot, trailing space, verbatim spelling and named stream. | V-008 is resolved. |
| Recovery / interrupted vs uninterrupted, damaged checkpoint, cross-version continuation | `CheckpointTests`, `ResumeTests` and `ResumeCliTests` cover atomic publication, failed and replayed cost, resuming in a different root, and missing, damaged and v1 refusals. Real synthetic workers resumed under new identities after controller interruption and either direct or deferred billing. | Pass. V-007 is resolved. |
| Task 4.2 / README and help match the implemented staged operations | README §4.7 matches `fit --help` and `resume --help` for training, setup and shared flags. Formal resume validates the inherited 200-epoch configuration. | V-009 is resolved. |

## Findings

Prior findings and repair notes are retained for reference.

### V-001 — A stale ledger writer can erase a published debit

- Category: implementation
- Severity: high
- Requirement: Resource preflight and cost limits are enforceable, including preservation of debits and measured history. Atomic recovery also requires debits to remain effective through controller termination.
- Evidence: `resources.py:344`, `:353`, `:388` and `cli.py:541`. `Ledger` loads once and replaces the whole file from its in-memory payload. The controller retains a ledger object and computes its budget base once.
- Expected: A heartbeat or final bill preserves published debits and accounts for current effective spending when enforcing the cumulative limit.
- Actual: With ledger A, call `record(execution_id="fit", run_id="fit", seconds=10, status="running")`. Open ledger B for the same file and register `prep` for 900 seconds. Confirm a fresh load shows 910 effective seconds. On ledger A call `record` for the same fit execution with 11 seconds. A fresh load returns 11 effective seconds and zero debits. Both the debit entry and registry record disappear.
- Repair guidance: Ensure ledger mutations preserve the latest validated history under independent writers, and have controller/worker budget checks use current effective usage.
- Acceptance checks: Replay the two-instance sequence and assert 911 effective seconds, one 900-second debit and preserved identity. Exercise registration during a controlled run and verify exhaustion and final billing retain the debit.
- Repair status: verified-resolved
- Repair notes: `temporal/resources.py` serializes reload, validation and atomic publication under a cross-process file lock. `temporal/cli.py` uses the latest totals after billing, and `temporal/runner.py` refreshes while fitting and before projection and final publication. `LedgerAndWatchdogTests.test_stale_heartbeat_preserves_a_concurrently_registered_debit` verified 911 effective seconds and the original identity. `RuntimeRepairTests` verified controller termination with final billing intact and worker pause at the prior complete epoch. A temporary four-process stress check retained all four writers' final totals after 400 updates.
- Reverification notes: The stale-heartbeat test preserved one 900-second debit, the ledger identity and 911 effective seconds. The controller and worker in-flight debit tests also passed.

### V-002 — The public resume command cannot reach recovery validation

- Category: implementation
- Severity: high
- Requirement: Atomic recovery, including same-v2 continuation and actionable historical or corrupt-checkpoint refusal.
- Evidence: `cli.py:167`, `:314`, `:391`. The parser supplies fit flags only to `fit`. The shared stage handler immediately asks the resume namespace for those flags. The base revision also accessed fit-only flags before loading the parent, later in the handler.
- Expected: `resume` uses the parent configuration and resumes compatible interrupted v2 work, or produces a specific refusal for missing, damaged or historical evidence.
- Actual: Run `python -m benchmark.multivariate_time_series.effective_temporal_training resume --data-name r0 --parent scratch/verify-v2-absent-parent --run-id verify-v2-resume --output-root scratch/verify-v2-absent-output`. It exits 1 with `AttributeError: 'Namespace' object has no attribute 'model'`, before inspecting the parent path. The same parser path serves valid and historical parents.
- Repair guidance: Use parent-derived controls for resume and retain early formal-control validation for fit. Validate parent identity and remaining budget before starting a worker.
- Acceptance checks: Run the documented resume CLI with an interrupted same-v2 synthetic fixture, a v1 fixture and a missing or damaged parent. Verify a parent-linked continuation in the first case and actionable refusals for the others.
- Repair status: verified-resolved
- Repair notes: `temporal/cli.py` validates the parent and inherits its controls, ledger and batch before worker creation. `temporal/recovery.py` provides a fresh-initialization message for historical evidence. `ResumeCliTests` continued a synthetic run under a different output root and checked the parent link, byte preservation and missing, truncated and v1 refusals. `ResumeTests` also passed.
- Reverification notes: The public CLI resumed at the next complete-epoch boundary with the parent's configuration and original ledger. The missing, truncated and v1 cases produced specific refusals and preserved ledger bytes. The v1 message included runner `3bd9fa4` and the fresh-initialization instruction.

### V-003 — Ledger loading accepts an unbound ledger and duplicate debit identities

- Category: implementation
- Severity: medium
- Requirement: Resource preflight and cost limits are enforceable, including registration only on an existing matching ledger and refusal of conflicting debit identity/value.
- Evidence: `resources.py:275`, `:311`, `:327` and `cli.py:814`. Batch validation is conditional on the stored batch being truthy. Debit comparison builds dictionaries that overwrite earlier duplicates by ID.
- Expected: Registration requires a stored batch and ledger identity. Loading rejects repeated or conflicting debit identities before calculating totals or changing the file.
- Actual: Write `{"version":1,"entries":[]}` to a temporary file and invoke `budget-debit --ledger <file> --batch-id arbitrary --debit-id prep --seconds 900 --reason fixture`. It reports success while the stored batch and ledger identifiers remain absent. Separately, create a valid 900-second debit and insert a copy of its entry with `seconds=1` before the original. A fresh load accepts the duplicate and reports 901 debited seconds.
- Repair guidance: Validate required identities and debit uniqueness on existing files. Preserve valid v1 ledgers with their existing IDs and no debit registry.
- Acceptance checks: These two malformed fixtures fail closed without altering their bytes. A valid legacy ledger loads, and identical debit replay leaves one debit and preserves both identities.
- Repair status: verified-resolved
- Repair notes: `temporal/resources.py` validates stored batch and ledger identities along with unique execution IDs and unique debit IDs in both entries and registry. `LedgerAndWatchdogTests` checked byte preservation for malformed fixtures and identical replay on a legacy-format ledger. `CliContractTests.test_budget_debit_cli_requires_existing_matching_ledger_and_is_idempotent` also rejected an unbound ledger through the public command.
- Reverification notes: The malformed ledger and duplicate identity tests rejected their fixtures without modification. The public registration test also refused the unbound ledger and confirmed that repeating an identical debit preserves the batch and ledger IDs.

### V-004 — Preflight output can replace the ledger it just billed

- Category: implementation
- Severity: high
- Requirement: Preserve cumulative spending, published debits and batch/ledger identity while metering public preflight.
- Evidence: `cli.py:361` writes `--out` after the metered call. It does not check whether the output resolves to the ledger path.
- Expected: Preflight preserves the ledger and refuses an output destination that would replace it.
- Actual: In a temporary ledger with 100 measured seconds and a 900-second debit, run `preflight --ledger <file> --batch-id verification --out <same file> --memory-available-bytes 17179869184 --disk-free-bytes 17179869184`. It returns exit 0 and replaces the ledger with a preflight JSON object lacking `ledger_id` and `entries`.
- Repair guidance: Validate the output destination before publishing. Protect identical resolved paths and aliases of the ledger file.
- Acceptance checks: Exercise identical path, relative-path alias and supported filesystem aliases. Verify refusal preserves the ledger identity, entries and debit registry. Verify distinct output paths still bill one measured execution.
- Repair status: verified-resolved
- Repair notes: `temporal/cli.py` checks resolved paths and existing file identity before preflight metering and creates the output exclusively. `PreflightCliTests.test_preflight_output_cannot_alias_ledger` checked identical and relative paths, supported links, byte preservation and a single measured bill for a distinct destination. Standalone pass/fail billing also passed.
- Reverification notes: The alias and standalone pass/fail billing tests passed. Aliased destinations preserved the ledger bytes, and a distinct output path produced a single measured preflight entry.

### V-005 — A Windows ledger reader can abort controller enforcement and billing

- Category: implementation
- Severity: high
- Requirement: Resource limits are enforceable during controlled resource or time breaches. Failed or interrupted work must retain its measured cost.
- Evidence: `temporal/resources.py:358` reads without taking the mutation lock. At line 385, the writer replaces the ledger while another Windows reader can have it open. `temporal/cli.py:528` bills before evaluating budget or terminating the process, including another write in its `finally`.
- Expected: Ordinary concurrent reads and ledger publication preserve cumulative billing. A publication or monitor failure stops the active worker and retains recoverable billing evidence.
- Actual: Create a temporary ledger with 43,100 measured seconds, a running fit billed 10 seconds, and a published 900-second debit. Within `with path.open("r", encoding="utf-8"):`, call `cli.supervise_worker` with a fake running process, a clean watchdog and a clock returning 11 seconds. Both write attempts hit Windows `PermissionError` with WinError 5. The controller invoked `terminate` zero times and the persisted fit remained `running` at 10 seconds. A normal `Ledger.record` call reproduced the same sharing violation independently.
- Repair guidance: Coordinate project ledger readers with atomic publication on Windows. Preserve bounded error handling so a failed accounting write cannot release the controller while leaving its worker running.
- Acceptance checks: Hold a ledger read open across controller billing on Windows. Verify the controller reaches a bounded outcome, stops an over-budget worker, retains measured and debited totals, and records a terminal or recoverable billing state. Exercise the overlap with actual independent reader and writer processes.
- Repair status: verified-resolved
- Repair notes: `temporal/resources.py` serializes ledger reads and atomic publication under the same cross-process lock. `temporal/cli.py` stops and reaps the worker on billing failure, then attempts the terminal bill. If a reader still blocks replacement, a separate JSON file retains the bill for the next ledger load and write. The Windows subprocess regression held the ledger open during supervision, verified worker termination and unchanged ledger bytes, then recovered 44,011 effective seconds, including the 900-second debit and the 11-second paused fit. A second regression verified coordinated project readers and writers across independent processes. `python -m unittest discover -s benchmark/multivariate_time_series/tests -v` passed all 151 tests.
- Reverification notes: Both Windows subprocess tests passed in the independent run. With the ledger held open, one worker stop was observed, the main ledger bytes were preserved, and deferred billing retained the 900-second debit and 11-second paused fit for 44,011 effective seconds. Coordinated project readers and writers serialized across separate processes. V-007 covers an interruption of the controller itself.

### V-006 — Separate output roots bypass one-worker exclusion for a shared batch

- Category: implementation
- Severity: high
- Requirement: Resource preflight must detect an active controller and enforce one worker for the batch, including parent-linked recovery using the inherited ledger.
- Evidence: `temporal/cli.py:306` derives the worker lock solely from the output root and batch name. At line 399, resume correctly inherits the ledger and batch but still derives its lock from the new output root. Both preflight and controller acquisition use that root-specific lock.
- Expected: Two invocations using the same batch and ledger share a controller exclusion boundary, including when resuming under a different output root.
- Actual: Create one temporary ledger for batch `verification`. Acquire the lock returned by `cli._lock_path` for root A. Run public `preflight` with the same ledger and batch and root B. Preflight returned exit 0 and `checks.worker_lock.status = "pass"`. Acquiring the controller lock for root B also returned `acquired` while A was still held.
- Repair guidance: Tie conflict detection and final lock acquisition to a stable shared batch identity that follows the inherited ledger across output roots. Keep independent batches able to use independent locks.
- Acceptance checks: Hold a batch controller lock in one root. Verify fit and public resume in a second root with the same ledger and batch refuse before worker creation. Verify a distinct batch can acquire its own lock and that a stale lock can be recovered without disturbing an active controller.
- Repair status: verified-resolved
- Repair notes: `temporal/cli.py` derives the worker lock from the resolved ledger path, including on inherited resume. Public preflight checks that lock even when an additional lock path is supplied. `temporal/resources.py` serializes takeover and release, and checks Windows process liveness without sending a console event. Public CLI tests verified cross-root fit, preflight and resume refusals, preservation of the live lock, acquisition by a separate batch and successful resume after release. The stale-takeover regression and the full 151-test recurrent suite passed on Windows.
- Reverification notes: The independent public CLI test refused cross-root fit, preflight and resume while the shared batch lock was held. It confirmed byte preservation of the live lock, acquisition by a separate batch, and successful same-v2 resume after release. The Windows active-owner and stale-takeover regression passed.

### V-007 — A controller interruption leaves the fit bill running and prevents recovery

- Category: implementation
- Severity: high
- Requirement: Resource limits include failed and interrupted work. Atomic recovery resumes an interrupted same-v2 trajectory from its last complete epoch with the accumulated cost.
- Evidence: `temporal/cli.py:510` stops the worker on `BaseException`. The final bill at `cli.py:584` is reachable only when the supervision loop exits normally. `temporal/recovery.py:130` rejects a `running` bill even after the worker and controller lock are gone.
- Expected: A handled controller interruption stops and reaps the child, charges execution through termination, and leaves a terminal bill or recoverable deferred bill. A valid same-v2 checkpoint remains resumable subject to the remaining budget.
- Actual: Run the public `fit` handler via `cli.main` with three synthetic r0 nodes, a temporary ledger holding 100 measured seconds and a 900-second debit, and the normal worker subprocess. Wrap `cli.supervise_worker` to supply a `sleeper` that raises `KeyboardInterrupt` 0.2 seconds after observing `<output root>/fit/recovery/last.pt`. The worker exited 1 and the lock was released. The checkpoint remained present, the ledger entry stayed `running` at 17.66 seconds, the interruption occurred at 17.88 seconds, and the debit remained 900 seconds. A new subprocess running `resume --data-name r0 --parent <output root>/fit --output-root <new root> --run-id after-interrupt` returned exit 2 and `inherited active-time entry is incomplete or unverifiable`. A clock-controlled probe independently left a `running` three-second bill with no deferred bill after interruption at four seconds.
- Repair guidance: Finalize or defer billing when a controller interruption stops the worker. Preserve the interruption outcome and the last usable checkpoint.
- Acceptance checks: Interrupt the public synthetic fit controller after its first complete-epoch checkpoint. Confirm the child exits, the lock is released, the ledger retains the debit and elapsed execution, and public `resume` can continue under a new output identity. Repeat with final ledger publication blocked and confirm deferred billing is recoverable.
- Repair status: verified-resolved
- Repair notes: `temporal/cli.py` stops and reaps the child before measuring and publishing the interrupted execution's paused bill. If terminal publication fails, the deferred bill retains that elapsed time. The public synthetic test in `tests/test_temporal_cli.py` passed with immediate publication and with an injected final publication failure. Both runs released the worker lock, retained the checkpoint and 900-second debit, and resumed under a new run ID. The Windows regression with an independent reader holding the ledger also passed. `python -m unittest discover -s benchmark/multivariate_time_series/tests -v` passed all 152 tests.
- Reverification notes: Independently ran `ResumeCliTests.test_interrupted_controller_bills_real_worker_and_allows_resume` with both publication paths. In each case the child was reaped before terminal metering, the controller returned pause, the lock was released, and the paused bill retained full elapsed time plus the existing 900-second debit. Public resume succeeded across a new output root and preserved the parent bytes. The deferred file was consumed during resume. The separate Windows ledger-reader regression also passed.

### V-008 — Preflight can write a report to the reserved deferred billing path

- Category: implementation
- Severity: medium
- Requirement: Public preflight preserves the batch ledger and usable cumulative billing evidence. The batch retains debit and measured costs across execution and recovery.
- Evidence: `temporal/cli.py:364` compares the resolved output with `Ledger.bookkeeping_paths` and uses `samefile()` only when both files exist. On this Windows host `Path.resolve()` retains a trailing dot or space on a nonexistent filename, while the subsequent `open("x")` creates the file without that suffix. `temporal/resources.py:495` tries to load any file at the resulting deferred-bill path.
- Expected: Preflight rejects a report destination reserved for batch bookkeeping and leaves the ledger usable for subsequent preflight, debit registration, fit and resume.
- Actual: On Windows, create a fresh temporary `ledger.json` for batch `fixture`, record 100 measured seconds and register a 900-second debit. Before any deferred bill exists, invoke `preflight --ledger <temp>/ledger.json --batch-id fixture --out "<temp>/ledger.json.pending-bill.json." --memory-available-bytes 17179869184 --disk-free-bytes 17179869184`. Exit is 0, the file at `<temp>/ledger.json.pending-bill.json` has `kind: preflight`, and the next `Ledger(path, 'fixture', require_existing=True)` raises `ResourceError: invalid deferred fit bill`. A fresh fixture with a trailing space in place of the final dot has the same result. The literal reserved filename is refused with exit 2, leaves ledger bytes unchanged and creates no deferred bill.
- Repair guidance: Validate report destinations using the target filesystem's filename semantics before metering or publication. Preserve valid output paths and exclusive file creation.
- Acceptance checks: Pass the literal path, a trailing dot and a trailing space through public preflight on Windows with a fresh ledger for each attempt. Verify rejection, unchanged ledger bytes and a readable ledger. Verify a distinct report destination still produces one measured entry and a usable report.
- Repair status: verified-resolved
- Repair notes: `temporal/cli.py` applies Win32 filename normalization before checking reserved paths or metering. The check also compares verbatim path spellings and an NTFS stream's backing file. The Windows CLI regression in `tests/test_temporal_cli.py` used a fresh ledger for each case and verified exit 2, identical ledger bytes, no deferred bill, and 1,000 effective seconds on reload. The existing distinct-destination test still produced one measured entry and a usable report.
- Reverification notes: The independent public CLI probe returned exit 2 for all five spellings, including the original trailing-dot and trailing-space reproductions. Each refusal left the ledger byte-identical, created no deferred bill and preserved 1,000 effective seconds on reload. A distinct report path wrote a passing JSON report and added exactly one measured preflight entry.

### V-009 — README lists fit-only controls as resume arguments

- Category: implementation
- Severity: low
- Requirement: Task 4.2 requires README §4.7 and public help to describe the actual v2 controls and staged commands. The recovery requirement binds resume to the parent's effective conditions.
- Evidence: `README.md:772` lists `--epochs`, `--hidden-size`, `--layers`, `--node-chunk`, `--grad-clip`, `--threads` and `--setup-seconds` for both `fit` and `resume`. The resume parser at `temporal/cli.py:171` accepts none of those flags, and `_run_stage` loads training controls from the parent. `README.md:787` describes resume as rejecting a shorter epoch request.
- Expected: The README lists the controls accepted by each command and describes formal resume validation in terms of the inherited parent configuration.
- Actual: `python -m benchmark.multivariate_time_series.effective_temporal_training resume --parent scratch/verify-absent-parent --data-name r0 --run-id verify-parser --epochs 200` exits 2 with `unrecognized arguments: --epochs 200` before accessing the parent. `resume --help` omits the listed fit-only flags.
- Repair guidance: Align the README with the existing parser and parent-derived configuration for resume.
- Acceptance checks: Compare README §4.7 with `fit --help` and `resume --help`. The documented flags match each command and the formal resume description identifies which parent settings are validated.
- Repair status: verified-resolved
- Repair notes: README §4.7 assigns the training and setup flags to `fit` and describes the configuration, roles, ledger, and batch inherited by `resume`. It documents the matching-ledger and matching-batch requirements and validation of the inherited formal configuration, including its 200-epoch target. Compared the section with both public help outputs.
- Reverification notes: Independently compared both public help outputs with README §4.7 and traced parent configuration and ledger selection through `_run_stage`. The documented flags and inherited config checks match the implementation.

### V-010 — RSS sampling can mark a successful worker exit as a pause

- Category: implementation
- Severity: medium
- Requirement: Resource monitoring stops a run on a genuine breach or monitor failure. Auditable outputs retain an accurate and consistent execution status.
- Evidence: `temporal/resources.py:632` samples by worker PID and `resources.py:683` records `NoSuchProcess` as a monitoring failure. After the child exits, `temporal/cli.py:525` stops the watchdog, and `cli.py:528` can use its final sample failure to overwrite a completed run's state and return `EXIT_PAUSED`. The sampler and the post-supervision status conversion also exist at the checked-out HEAD. Introduction by this repair was not established.
- Expected: A successful child exit with a completed report returns success and retains completed status when a concurrent RSS sample observes that the process has already exited. Resource breaches and monitoring failures while the worker is active still pause the run.
- Actual: On Windows, the targeted regression suite produced exit 3 for the r2/GRU subcase even though the worker reported completion. Using `temporal_fixtures.write_demand` with `r2_keys(2, 2)` and `synthetic_signal(4, seed=17)`, run public `fit --data-name r2 --data <fixture> --model GRU --epochs 1 --hidden-size 4 --node-chunk 3 --monitor-interval 0.05 --memory-available-bytes 17179869184 --output-root <temporary root> --run-id <fresh id>`. The repeated run wrote `report.json` status `completed` and `status.json` state `paused` with `NoSuchProcess`. A separate traced run called `Popen.poll()` when the real sampler raised `NoSuchProcess` and observed exit 0. The CLI still returned 3.
- Repair guidance: Distinguish a worker disappearing after successful exit from a sampler failure while it is still active. Keep controller exit codes and persisted execution status consistent.
- Acceptance checks: Exercise a real worker with an RSS sample overlapping successful exit and check that the CLI returns 0 and both status outputs agree. Rerun the active-worker RSS-limit and monitoring-failure regressions and verify that both still pause.
- Repair status: verified-resolved
- Repair notes: The controller in `temporal/cli.py` checks the child exit code when psutil raises `NoSuchProcess`. `temporal/resources.py` treats a confirmed successful exit as the end of monitoring. A synchronized public CLI test in `tests/test_temporal_cli.py` exercised the race with a real synthetic worker and verified exit 0, completed report and run status, and a finished ledger entry. The active-worker RSS-limit and monitor-failure regressions still paused. `python -m unittest discover -s benchmark/multivariate_time_series/tests -v -k Cli -k DevelopmentChainTests -k RuntimeRepairTests.test_controller -k LedgerAndWatchdogTests -k FitResourceTests -k RssControlTests` passed all 36 tests.
- Reverification notes: The synchronized real-worker test passed independently. The original r2/GRU probe also observed a real `NoSuchProcess` with `Popen.poll()` returning 0 in each of three runs. Each CLI returned 0, both status files recorded `completed`, and the measured entry was `finished`. The independent active-worker RSS breach, monitor-failure and controller termination regressions passed.
