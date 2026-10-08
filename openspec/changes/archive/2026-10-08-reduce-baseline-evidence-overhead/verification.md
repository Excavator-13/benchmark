# Implementation Verification

- Change: reduce-baseline-evidence-overhead
- Schema: spec-driven
- Verdict: PASS
- Verified at: 2026-10-08T08:42:36Z
- Implementation roots: /Users/watuji/da_chuang/repos/benchmark
- Verified revision: `715d44de43d14b0dcc5dfc525955689af9e0cc00`, with dirty implementation, documentation, planning and pre-existing research-maintenance changes.

## Summary

Independent incremental reverification is **PASS**. This round is limited to V-003, as requested; V-001, V-002, V-004 and V-005 retain their earlier independent verified-resolved status. V-003 is now verified-resolved: the exact saved patch restores ordinarily modified or deleted files even when another path's diff driver fails, and that failing path has exact saved fallback bytes. All seven V-003 regression tests and five independent recovery fixtures pass. No actionable finding remains.

Strict OpenSpec validation passes again. This round ran seven focused tests in 0.900 seconds, with no failures or skips, plus independent mixed-driver modification/deletion, binary, non-patch external-diff and staged/unstaged/untracked/protocol recovery fixtures. The full suite and unrelated scenarios were not rerun. The earlier independent evidence is retained separately: 192 tests in 24.681 seconds (190 passed, two optional scikit-learn skips), 17 repair tests, both dataset fixture schemas, authenticated legacy T004 checks and region same-seed/source-removal evidence. Prior independent v1/v2 archive fixture evidence also remains applicable; archive utility/index/package/report fingerprints are unchanged. The overall verdict combines that prior scenario coverage with this round's V-003 evidence; it does not claim a new full-suite execution.

Only this report was edited. No implementation, test, planning, task, handoff, main-spec, delegation or research-record edits were made. No real-data model experiment, full-corpus restoration, package export, sealing, commit, push, archive or research acceptance was performed. This round used disposable Git/source fixtures only; historical T004 authentication/check results below are earlier evidence, not checks repeated this round. Optional scikit-learn execution remains unverified and is nonblocking for the required NumPy backend.

## Verification Basis

All paths below are relative to the implementation root. Scope fingerprints cover sorted path inventories and file contents, including relevant dirty/untracked planning, code, tests and configuration. The initial scope fingerprints and individual-file hashes were rechecked after executable verification and were unchanged. HEAD also remained unchanged. Compared with the previous verification, only the baseline implementation/test scope changed; planning, configuration, protocol, archive utility/index/packages, readable run entries and historical archived reports have the same fingerprints. The previous report and all repair notes were read before updating this report.

| Path or scope | Revision / content fingerprint / file inventory |
| --- | --- |
| Git HEAD | `715d44de43d14b0dcc5dfc525955689af9e0cc00` |
| `benchmark/nograph_baseline/` | `d8f594c5e0d8a3c980cd74af6daa27f7855e083815e56755701575132bebde53` |
| Selected change planning, including hidden metadata, excluding handoff/report | `b0f4b0b83416bc2d989570edb116b953e353919e830bb4659bed544d83b5ef58` |
| `openspec/specs/nograph-baseline-entry/` | `777d1144eea995c8d23c666d2eff7575cdc92d7167af4387dcd203b7ce0742c9` |
| Versioned/readable `research/runs/` inventory | `be9809be1621cd94e662f81ab2558718509dab3f6f1cc96d4fd4d40a405a343c` |
| `research/archives/`, including utility, index, manifest and packages | `0cc9b5da8cce2dfa871171ec7eda58f6c8c48b568c29e66b83d07cd5de0b69de` |
| Existing `openspec/changes/archive/` | `bfb77419d5757049aecafa0f3f96165b136445c0fb220a1eadd7b26a64f379eb` |
| `README.md` | `2665b7675d5ebbb8542fbfd44bb6db99f1a69c8685048db54bf929bf69919da2` |
| `.gitignore` | `9be98aec44ac556ad700c4204bef0bb61024db159183233af706ad3110d6961e` |
| `openspec/config.yaml` | `2a791b0ccc50e2c2ebbb3ba28692a4ad0e4b6ab94ed2151375ac404d7056e89a` |
| `research/phases/P01/protocol.md` | `8d469cbe24f9f016c25c8b5afa2ca53bd4a001272e2f39e6f8abe6a071a067f9` |
| Root `requirements.txt` | `34e6005f98b5e3ad96f92ac55151780e1cc67f802474c305d939ae3c56127d7f` |

Reproduce the scope fingerprints from the root using zsh:

```zsh
for scope in benchmark/nograph_baseline openspec/changes/reduce-baseline-evidence-overhead openspec/specs/nograph-baseline-entry research/runs research/archives; do
  print -r -- "$scope"
  rg --files --hidden "$scope" | LC_ALL=C sort | while IFS= read -r f; do
    case "$f" in */__pycache__/*|*/implementation-notes.md|*/verification.md) continue;; esac
    shasum -a 256 "$f"
  done | shasum -a 256
done
shasum -a 256 README.md .gitignore openspec/config.yaml research/phases/P01/protocol.md requirements.txt
```

Each scope digest is SHA256 of the exact `shasum -a 256` output records, sorted by repository-relative path. Path names participate in the digest, detecting additions/deletions. `rg` respects the recorded ignore configuration; bytecode caches and ignored disposable outputs are outside the basis. Workflow-owned implementation notes and this report are excluded from scope fingerprints. The archived-report fingerprint uses the same sorted-file/hash pipeline on `openspec/changes/archive/` without those exclusions. A later archive moves the selected planning directory; compare its contents using the original path labels or recompute the pre-move basis before moving it.

`git diff --exit-code -- research/runs 'research/archives/*.tar.gz' openspec/changes/archive` returned zero with no output. Pre-existing sidecar removals, schema-v2 metadata and research-maintenance edits were present before verification and were not attributed to this implementation. Scientific source datasets are outside the new fixture verification basis; their historical scientific acceptance is evidenced by the preserved archived report, not a new scientific audit.

## Apply Handoff Review

Read `implementation-notes.md` in full and the repair-owned notes for V-001 through V-005 in the previous report, including V-003's latest repair. The apply handoff still identifies the correct change, project, schema and HEAD, but predates the repairs: its 175-test count and original producer descriptions are historical. The latest repair adds two mixed-driver regression methods and retains proven per-path patches in the actual saved patch. Its claimed 194-test full-suite result was not independently rerun or adopted as evidence this round. No apply or repair claimed result was copied as independent evidence. Reminder dispositions unrelated to V-003 below retain the earlier verification evidence.

| Reminder / material claim | Disposition and independent evidence |
| --- | --- |
| Check consumers must migrate from `run_dir` to `report_path`; models retain `run_dir` | Confirmed by CLI/API code and `CheckReportContractTests`, including exclusive one-file output and aliases. |
| Current checker source is dirty; large scoped patches may be omitted with a reason | Confirmed for current tracked changes; envelope tests pass and the 20000-byte limit is explicit. V-004 rechecked: untracked source is explicitly scoped-dirty; unavailable Git scope is unknown rather than clean. |
| Purpose/retention do not affect scientific comparison conditions | Confirmed by `_semantic_config`, purpose/retention parity tests, adversarial identity tests and both-schema same-seed fixture evidence. Protocol byte hashes remain strict. |
| `source-sha256.json` compatibility; `source_capture` replaces `untracked_source` | Confirmed in current producer/validator code, new fixture checks and authenticated legacy saved inputs. V-001 rechecked: clean protocol is referenced without a copy; dirty/untracked/outside-repository/non-Git protocols retain exact bytes. |
| `code-untracked/manifest.json` appears only when content is saved | Confirmed in earlier source fixtures and current V-003 reconstruction probes. Failed/non-patch diff fallback preserves exact bytes; mixed-driver cases now retain the other path's proven patch. V-003 verified-resolved. |
| T004 exact run-set validation is keyed on `task_id == P01-T004` | Confirmed by real index inspection and synthetic rejection of an incomplete T004 run set; other fixture task IDs can declare smaller sets. This matches the T004-specific utility scope. |
| `_restore_package` reads each member into memory | Confirmed by inspection. Larger-package memory demand is a residual limit, not a new acceptance requirement. |
| Rerun the suite; ad-hoc `/tmp` harnesses are not durable evidence | Earlier focused/full suites and legacy/region checks remain recorded evidence. This user-requested V-003 round independently ran seven focused methods and five recovery fixtures; no full suite was rerun. The mixed-driver reproduction is preserved below. |
| No new scientific run, input-data reread by checks, or automatic maintenance | Confirmed for this verification through temporary fixture execution, saved-only checks after fixture demand/graph removal, protected-path diff and call-site inspection. Apply's historical full-corpus verify claim was not rerun because design/task 1.1 specify small fixtures. No assertion is made about unobservable past process actions. |
| Default report root is asserted without polluting repository reports | Confirmed by parser/root-function checks; explicit temporary alias outputs exercised. |
| Failure input immutability is less broadly tested than success | Current malformed-status/metrics, permission, destination and CLI tests pass; original CLI status failure now retains one report with unchanged inputs. V-002 verified-resolved. |
| Optional scikit-learn unavailable | Confirmed by two explicit skips; default three-dependency backend is exercised. |
| Latest V-003 repair claims reconstructable patch proof | Confirmed by independently applying the exact persisted patch to the recorded fixed base and overlaying only saved fallback files. Modification/deletion mixed with driver failure and retained single-file conditions recover every scoped path. No repair note was removed or rewritten. |

## Checks

`NBPY` below denotes `/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python`. Additional probes were executed as heredoc Python commands from the repository root, producing only temporary fixtures/reports. No harness code file was added.

### Current Round: V-003 Only

| Command or inspection | Result | Notes |
| --- | --- | --- |
| Strict OpenSpec validation, same command as below | PASS | One valid change, zero issues. |
| Seven focused `RepairRegressionTests` methods listed below | PASS | Seven tests in 0.900 s; no failures or skips. Actual base-plus-saved-evidence assertions inspected. |
| Independent mixed-driver modification recovery | PASS | Saved patch 123 bytes; `good.py` restored by patch, `broken.py` by `code-untracked/broken.py`; both SHA256 values match. Explicit driver error retained; no unrecoverable paths. |
| Independent deletion plus another path's driver failure | PASS | Saved patch 132 bytes; `good.py` absent after apply, `broken.py` restored by saved copy; both recorded states match. |
| Independent binary and successful non-patch external diff | PASS | Binary patch 222 bytes applies and matches SHA256; junk output leaves zero patch bytes and exact fallback content. |
| Independent ordinary scoped recovery | PASS | Saved patch 550 bytes plus untracked fallback reconstruct staged, unstaged, deleted and untracked runtime, dirty protocol and clean referenced source (six paths). Unrelated file omitted; clean source not copied. |
| Initial/final fingerprints and protected-path diff | PASS | All recorded scopes, individual files and HEAD unchanged during checks; sealed packages, readable runs and archived reports unchanged. |

Reproduce the focused invocation from the repository root:

```bash
PYTHONPATH=benchmark/nograph_baseline/tests:. /opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python -m unittest \
  test_runner_cli.RepairRegressionTests.test_mixed_driver_multi_file_recovers_every_path \
  test_runner_cli.RepairRegressionTests.test_mixed_driver_deletion_and_failure_recovers_every_path \
  test_runner_cli.RepairRegressionTests.test_ordinary_modified_and_deleted_runtime_reconstruct_from_patch \
  test_runner_cli.RepairRegressionTests.test_binary_marked_runtime_source_reconstructs_from_patch \
  test_runner_cli.RepairRegressionTests.test_external_non_patch_diff_falls_back_to_saved_content \
  test_runner_cli.RepairRegressionTests.test_failed_git_diff_preserves_modified_runtime_content \
  test_runner_cli.RepairRegressionTests.test_failed_git_diff_reports_unrecoverable_deletion -v
```

Independent fixtures read `code-source.json` back from disk, checked out its recorded commit in a new recovery tree, applied only its saved patch, overlaid only its saved content and asserted every SHA256/deletion state. These checks did not use an ephemeral proof patch or current working-tree files as recovery inputs. The failed-diff deletion regression records the explicit unavailable-content limitation; it does not assert that an unusable deletion patch applies.

### Prior Independent Checks

The following table preserves the 08:30:36Z round and earlier retained checks. Its mixed-driver failure is historical and superseded by the current passing evidence above; other scenarios were not rerun this round.

| Command or inspection | Result | Notes |
| --- | --- | --- |
| `openspec status --change reduce-baseline-evidence-overhead --json` and `openspec instructions apply --change reduce-baseline-evidence-overhead --json` | PASS | Repo-local `spec-driven`; all context files present. 9/9 checked tasks treated as claims. |
| `openspec validate reduce-baseline-evidence-overhead --type change --strict --json --no-interactive` | PASS | One valid change, zero issues. |
| Test setup | Available | Focused invocation uses the test directory on `PYTHONPATH` for its top-level `nb_fixtures` helper. No outstanding environment blocker. |
| `PYTHONPATH=benchmark/nograph_baseline/tests:. $NBPY -m unittest test_runner_cli.RepairRegressionTests -v` | PASS | 17 tests in 4.014 s; inspected actual reconstruction assertions and real Git/fixture setup. |
| `$NBPY -m unittest discover -s benchmark/nograph_baseline/tests -v` | PASS | 192 tests, 24.681 s, two optional sklearn skips. PyArrow prints sandbox CPU-cache sysctl warnings; tests succeed. |
| Disposable Git source reconstruction | PASS for ordinary diff | Base commit + saved patch/files reconstruct clean, staged, unstaged, deleted, untracked runtime and dirty protocol byte-for-byte. Unrelated dirty records excluded; clean source not copied. |
| Completed fixture with clean committed protocol override | PASS: V-001 resolved | Original probe now retains the fixed protocol reference and no `protocol.md` copy. Four non-clean protocol cases retain exact bytes in repair tests. |
| CLI recompute on malformed `status.json` | PASS: V-002 resolved | Original probe returns rc 1 with a valid failed report; input unchanged. Related malformed/permission/destination cases pass. |
| Single-file real Git external-diff failure | PASS | `false` driver: exact fallback bytes survive, path is listed in `patch_unusable_paths`, recovery SHA256 matches. |
| Single-file successful external diff output `b/used.py` | PASS | Non-patch output rejected by actual apply/hash proof; exact fallback bytes survive with explicit limitation; recovery SHA256 matches. |
| Single-file ordinary `used.py -diff` attribute | PASS | `--binary` produces `GIT binary patch`; applying the run-owned patch to fixed base restores the actual execution SHA256 without a content copy. |
| Multiple modified files with one failing diff driver | FAIL: V-003 | Aggregate diff rc 128, saved patch empty. `broken.py` has an exact fallback; `good.py` has no fallback and its separately validated patch is not saved. Only `broken.py` reconstructs to its recorded execution SHA256. |
| Checker source identity with untracked runtime launcher | PASS: V-004 resolved | Original probe now identifies untracked scoped source as dirty. Clean/modified/untracked/unavailable-Git matrix passes. |
| Historical T004 saved-only checks and `alpha`/`beta` aliases | PASS: V-005 resolved | Three existing temporary legacy copies authenticate against sealed member contents. Recompute/compare/align return `ok`, explicit declared IDs are correct, three reports only, input bytes unchanged. No package restoration performed. |
| Extra region/count same-seed probe | PASS | Two four-region CPU fixtures; all 12 method/split prediction arrays bit-identical. Compare/recompute remain `ok` after fixture demand/graph files are deleted. |
| Small Git-backed schema-v2 archive fixtures | Prior independent PASS retained | Utility/index/package fingerprint unchanged. Previously verified clean three-member package including embedded-exclusion files, identity/count/T004-set rejection, all specified unsafe members and absent sidecars/hash table remain applicable. |
| Small historical schema-v1 fixture | Prior independent PASS retained | Utility fingerprint unchanged. Previously exercised historical checksum/sidecar/member/basis validation and sidecar corruption using synthetic corpus constants changed only in memory. |
| Archive collision probe | Prior independent PASS retained | Utility/package fingerprint unchanged. Previously confirmed reserved fixture target refuses before source inventory or writes. |
| README/parser and maintenance call-site inspection | PASS except documented behavior findings | Purpose, candidate option, explicit/legacy report paths, migration API and external export SHA256 are documented. No model/check call invokes sealing, export, commit, push or restoration. |
| Protected-path diff and final fingerprint comparison | PASS | Original packages, readable entries and archived reports unchanged. Recorded verification inputs did not change during checks. |

## Requirement Coverage

Every normative scenario in the delta spec is listed. A passing sub-behavior does not waive a parent requirement's confirmed defect.

| Requirement / scenario | Evidence | Result |
| --- | --- | --- |
| Recoverable evidence / Metrics are independently recomputed | Saved-only new and authenticated legacy recompute; complete method/window/horizon/context/group/gain/null/node-error tests; region source-removal probe | PASS |
| Recoverable evidence / Run is interrupted or collides | `FailureAndInterruptionTests`: collision, malformed source, SIGINT, SIGTERM, SIGKILL and unfinished status | PASS |
| Recoverable evidence / Committed execution sources are reused | Source references/reconstruction and original end-to-end clean protocol override probe now pass; no duplicate clean protocol file | PASS, V-001 resolved |
| Recoverable evidence / Runtime source or protocol is uncommitted | Current V-003 ordinary staged/unstaged/deleted/untracked/protocol, binary and mixed-driver reconstruction; exact saved evidence restores every scoped path | PASS, V-003 resolved |
| Recoverable evidence / Git identity is unavailable | Prior non-Git fallback evidence retained; current single-file and mixed-driver failure preserve exact available modified content and explicit errors | PASS, V-003 resolved |
| Recoverable evidence / Candidate retention is reduced by default | `CandidateRetentionDeltaTests` for r0 and region: five scalar rows/winner, no candidate directory, selected-model reconstruction, full prediction/metric parity | PASS |
| Recoverable evidence / Candidate arrays are explicitly requested | Both schemas: five parameter/validation array pairs, unchanged selection and outputs; CLI RunSpec/worker wiring | PASS |
| Both datasets / Execute both supported datasets end to end | Preserved archived T004 independent PASS covers historical scientific runs; current minimal-dependency CPU tests cover both fixture schemas, all naive/Ridge outputs and measured records | PASS under maintenance scope; no new real-data experiment |
| Both datasets / Existing scientific acceptance survives record-format maintenance | Scientific producers unchanged apart from persistence/purpose; protected packages/report unchanged; both-schema fixtures, r0 suite repetition and extra region repetition | PASS |
| Development namespace / Development fixture runs | `PurposeDeltaTests`: ignored default scratch output, labeling, no formal directory, r0/region scientific parity | PASS |
| Development namespace / Development output points at formal records | Direct and symlink alias rejection before reservation; explicit temporary roots allowed | PASS |
| Compact reports / Three saved-only check commands | One-file envelopes, commands, tolerances, consumed hashes, embedded recomputation, honest checker state and explicit execution IDs pass on new/legacy layouts | PASS, V-004/V-005 resolved |
| Compact reports / Report collision or output inside an input | All three commands reject existing and symlink outputs and outputs inside either run; exclusive `O_EXCL`; reference replacement refused | PASS |
| Compact reports / Invalid saved evidence | Mismatch/missing-array/null/source-identity/tolerance tests plus malformed status/metrics and unreadable-input failure reports pass | PASS, V-002 resolved |
| Compact reports / Legacy command flags are reused | Three-command legacy aliases, default root function, region recompute alias, CLI `report_path` metadata | PASS |
| Compact reports / Output flag choices conflict | Parser mutual exclusion and programmatic rejection; no output | PASS |
| Git-backed metadata / Explicit schema-v2 verification without sidecars | Local Git fixture, fixed blob comparison, three safe members, fresh temporary restoration, no sidecars/member-hash table | PASS |
| Git-backed metadata / Unsafe or changed package | Synthetic identity/count and all specified unsafe-member cases reject; `_restore_package` scans complete member inventory before writing | PASS |
| Git-backed metadata / Historical schema-v1 metadata is supplied | Synthetic old checksum-bearing corpus exercises existing dispatch, checksum, sidecar, member table and content-basis validation; invalid sidecar rejected | PASS, fixture corpus constants adjusted in memory only |
| Git-backed metadata / Exclusion declarations are retained | Real index preserves package exclusions, separate embedded exclusions, `task_id`, `sealed_at`; fixture allows embedded-exclusion files while rejecting package-excluded members | PASS |
| Git-backed metadata / Package is separately exported outside Git | Design explicitly permits documentation-only manual checksum instruction/no export framework; README requires external SHA256; originals untouched | PASS by inspection; no export requested/performed |

Parent requirement and design constraints were additionally traced in earlier verification: formal defaults/exclusive identities, scientific version and record policy, canonical node/window identities, environment/measurements, pickle-free arrays, complete selection records, unfinished evidence and absence of automatic maintenance are established by producer inspection and suite coverage. Check protocol-hash and environment mismatch rejection retain earlier adversarial-test evidence. All 21 normative scenarios have evidence in this incremental matrix; only V-003's affected recovery coverage was rerun this round. Task 2.2's recoverability defect is resolved; no planning contradiction or environment blocker remains.

## Findings

All findings are verified-resolved. Resolved entries retain their original Evidence/Actual descriptions and repair-owned notes for history; their current status and Reverification notes describe the independently checked behavior. V-003 retains its ID because it is the same missing-recoverable-content defect. This round rechecked V-003 only.

### V-001: Clean committed protocol is still copied into every model run

- Category: implementation
- Severity: medium
- Requirement: Recoverable evidence / Committed execution sources are reused; design decision 3.
- Evidence: `benchmark/nograph_baseline/runner.py:169` unconditionally copies every existing protocol to `protocol.md` at line 172, before scoped source capture. A completed temporary r0 fixture with a committed clean protocol returned success, recorded `git_status: committed_clean` plus its fixed reference, and still contained byte-identical `protocol.md`.
- Expected: Clean committed runtime/protocol content is referenced by fixed commit/path without a duplicate source/protocol file.
- Actual: Protocol content is always duplicated. Helper-only clean-reference tests miss the end-to-end copy.
- Repair guidance: Apply protocol retention at the producer boundary so clean committed content uses its fixed reference; preserve actual dirty/outside-Git protocol content and saved-only source-manifest compatibility.
- Acceptance checks: Execute completed fixtures with clean committed, tracked-dirty, untracked, outside-repository and unavailable-Git protocols. Assert no clean protocol copy, exact recovery in other cases, and unchanged protocol byte identity/numerics.
- Repair status: verified-resolved
- Repair notes: `benchmark/nograph_baseline/runner.py`: scoped source capture now runs before the protocol snapshot, and `protocol.md` is written only when the scoped protocol entry is not a clean committed reference (a `protocol_referenced` event records the fixed commit/path instead). `protocol_sha256`/`source-sha256.json` are unchanged. Regression tests: `RepairRegressionTests.test_clean_committed_protocol_is_referenced_without_a_copy` (completed fixture with a clean committed override has no `protocol.md`, has a valid `git_reference`, and keeps the executing protocol hash) and `test_dirty_untracked_outside_and_unavailable_protocols_are_preserved` (tracked-dirty, untracked, outside-repository and unavailable-Git protocols still produce exact `protocol.md` content); `RunnerArtifactTests.test_required_artifacts_exist` now asserts the conditional protocol artifact rather than always requiring it. Reproduced the verifier's clean-protocol probe: `protocol.md` absent. Full suite: `Ran 189 tests ... OK (skipped=2)`.
- Reverification notes: 2026-10-08T08:19:35Z: original completed clean-protocol probe now records a valid reference and has no `protocol.md`. Both protocol repair tests pass: dirty, untracked, outside-repository and non-Git protocol content survives exactly, and saved-only protocol hashes remain compatible. Verified-resolved.

### V-002: Malformed saved status fails without the required report

- Category: implementation
- Severity: medium
- Requirement: Compact reports / Invalid saved evidence; failed checks with a usable output destination retain a report and return nonzero.
- Evidence: `benchmark/nograph_baseline/checks.py:706` parses `status.json` before the exception-to-report block at line 710. CLI recompute with `status.json` containing `{invalid` returned rc 1 and `JSONDecodeError`; the valid new report path did not exist. Input bytes were unchanged. Input hashing also occurs outside the failure-report blocks in all three commands.
- Expected: Invalid saved evidence at a safe destination leaves one informative failure report and a nonzero result.
- Actual: Malformed status escapes directly to the CLI, leaving no report.
- Repair guidance: Ensure input parsing/identity acquisition failures are within the failure-report contract after destination validation; retain available identities and decisive error information without weakening destination safety.
- Acceptance checks: Reproduce malformed status and unreadable consumed-input errors for relevant commands. Require nonzero results, one valid failed report, unchanged inputs, and continued no-output behavior for unsafe destinations/collisions.
- Repair status: verified-resolved
- Repair notes: `benchmark/nograph_baseline/checks.py`: consumed-input hashing and status/metrics parsing moved inside the failure-report block for recompute, compare and align-v2; destination validation still precedes it, so unsafe destinations and collisions still produce no output. Regression tests: `RepairRegressionTests.test_malformed_status_writes_one_failure_report` (recompute and compare, malformed `status.json` -> one `status: failed` report with a `JSONDecodeError` entry and unchanged input tree), `test_malformed_status_cli_returns_nonzero_with_a_report` (CLI rc != 0, `report_path` in stdout, report on disk), `test_malformed_metrics_still_writes_an_align_failure_report`, `test_unreadable_consumed_input_writes_a_failure_report` (chmod 0 consumed input -> `PermissionError` failure report), `test_unsafe_destination_still_produces_no_output`. Reproduced the verifier's CLI probe: rc 1 with a valid `status: failed` report. Full suite: `Ran 189 tests ... OK (skipped=2)`.
- Reverification notes: 2026-10-08T08:19:35Z: original malformed-status CLI probe returns rc 1, valid JSON failure report and unchanged input bytes. Recompute/compare malformed status, align malformed metrics, unreadable consumed input and unsafe destination regression tests pass. Verified-resolved.

### V-003: Modified runtime can still lack a reconstructable patch or fallback

- Category: implementation
- Severity: medium
- Requirement: Recoverable evidence / Runtime source or protocol is uncommitted; Git identity is unavailable; design decision 3 requires fallback when inspection fails.
- Evidence: Previous binary/non-patch single-file conditions now reconstruct correctly. Current `benchmark/nograph_baseline/artifacts.py:505` generates the aggregate patch, which is replaced with an empty string on a scoped Git failure (line 510). `_patch_reproduces` at line 522 regenerates and proves a separate per-file patch that is not persisted. If that proof succeeds, line 612 skips fallback even when the aggregate patch is empty. In a disposable repository with modified `good.py` and `broken.py`, only `broken.py` uses a failing external diff driver. Aggregate diff exits 128, `patch_bytes=0`, `patch_unusable_paths=['broken.py']`; `good.py` records differing current/base hashes and `content_saved=null`. After recovering from the fixed commit plus every run-owned patch/copy, `broken.py` matches its execution SHA256 but `good.py` remains old and does not match.
- Expected: Actual relevant modified execution bytes are reconstructable from the recorded fixed base plus saved patch/files; unusable diff output must not replace recoverable content.
- Actual: Validation proves an ephemeral per-file patch, while recovery has only the different aggregate patch. A failure on one scoped file therefore leaves another modified execution file without its necessary bytes or an applicable saved patch.
- Repair guidance: Tie reconstruction proof to the exact evidence retained in the run. On aggregate failure, preserve all modified paths that cannot be reconstructed from that saved evidence, or retain the proven per-file patches. Keep scope/exclusions, clean-reference reuse and explicit limitations intact.
- Acceptance checks: Add mixed-driver multi-file cases: one failing external diff file together with another ordinarily modified file, and a deletion with another driver failure. Recover every scoped path using only fixed base plus the exact saved patch/files and compare content or deletion state. Retain single-file binary, external non-patch, nonzero-diff, ordinary staged/unstaged/deletion/untracked/protocol checks.
- Repair status: verified-resolved
- Repair notes: `benchmark/nograph_baseline/artifacts.py` `capture_source`: the saved patch is now built from proven per-path evidence instead of one aggregate `git diff`, so a failing driver on one path cannot erase another path's retained diff. Each changed path gets its own `git diff --binary HEAD -- <path>`; a `_reconstruct_from_patch` proof seeds the recorded base blob (`git show <commit>:<path>`) in a temporary directory, applies that patch with `git apply --unsafe-paths`, and requires the result (or the file's absence, for a deletion) to hash to the recorded `sha256`. Proven patches are concatenated into the persisted `git-diff.patch`, so the retained patch reconstructs exactly the paths it claims; a path whose diff cannot be proven is preserved at `code-untracked/<path>` with an explicit `unavailable_reason`. Each entry records `patch_path` when the saved patch recovers it; the record exposes `patch_unusable_paths`, `patch_errors` and `unrecoverable_paths`. Source scope/exclusions and clean-reference reuse are unchanged. Regression tests reconstruct from the fixed commit base plus the exact saved patch/files and compare SHA256 or deletion state: `RepairRegressionTests.test_mixed_driver_multi_file_recovers_every_path` (`good.py` patched, `broken.py` saved), `test_mixed_driver_deletion_and_failure_recovers_every_path` (deletion patched, failing path saved), `test_ordinary_modified_and_deleted_runtime_reconstruct_from_patch`, `test_binary_marked_runtime_source_reconstructs_from_patch`, `test_external_non_patch_diff_falls_back_to_saved_content`, plus the retained single-file `test_failed_git_diff_preserves_modified_runtime_content`/`test_failed_git_diff_reports_unrecoverable_deletion`. Independent probes: the verifier's exact mixed reproduction now recovers both paths (`good.py` via the saved patch, `broken.py` via saved copy) and records the failing driver in `errors.scoped_patch`; single-file broken/junk, binary `-diff`, ordinary multi-file and deletion-plus-driver-failure variants all recover every scoped path. A live-repo fixture run's saved patch reconstructs all four changed paths to their recorded SHA256 with no copies. Full suite: `Ran 194 tests ... OK (skipped=2)` (~24.3 s).
- Reverification notes: 2026-10-08T08:30:36Z: prior single-file failures were repaired, but independent mixed-driver recovery failed for `good.py` despite 17 repair tests and 192 suite tests passing with two optional skips. 2026-10-08T08:42:36Z: latest repair independently verified. `capture_source` at `artifacts.py:595-620` retains each proven path patch, then writes their concatenation at lines 651-654. Seven V-003 tests pass in 0.900 s. Five independent fixtures recover every recorded path from the fixed commit plus the exact saved patch/files, including the original mixed-driver reproduction and deletion-plus-failure. The original reproduction now saves 123 patch bytes for `good.py` and exact fallback bytes for `broken.py`; both recovered hashes match. V-003 verified-resolved. Full suite and other findings were not rerun; repair notes preserved verbatim.

### V-004: Untracked checker source is reported as scoped-clean

- Category: implementation
- Severity: medium
- Requirement: Compact reports require honest checker source identity/version; design decision 2 forbids claiming a clean commit when checker content differs.
- Evidence: `benchmark/nograph_baseline/artifacts.py:633` excludes porcelain `??` from `dirty_paths`; `scoped_dirty` is derived solely from that list at line 652. A repository with a committed anchor and an untracked `benchmark/nograph_baseline/__main__.py` returned a fixed commit, this runtime file's SHA256, `scoped_dirty: false` and `scoped_files: []`, although Git explicitly reported the runtime file as untracked and the commit did not contain it.
- Expected: Used untracked checker source is clearly identified as differing from the recorded commit; any unavailable identity/state is explicit. A report need not copy checker sources.
- Actual: A report's scoped cleanliness claim contradicts the source it identifies. Whole-repository dirtiness does not correct a false scoped-clean claim.
- Repair guidance: Account for untracked scoped runtime files when identifying checker dirtiness, keeping patch eligibility separate from source-state reporting.
- Acceptance checks: Generate checker identities/reports with clean tracked, modified tracked, untracked and unavailable-Git runtime sources. Assert accurate scoped state and fixed-reference limitations.
- Repair status: verified-resolved
- Repair notes: `benchmark/nograph_baseline/artifacts.py` `checker_source_identity`: porcelain `??` runtime files now count toward the scoped source state; `scoped_files` unions tracked modifications with untracked files, `scoped_dirty` reflects that union, and patch eligibility is reported separately as `patch_eligible_files` (tracked modifications only) with `untracked_files` listed. When scoped Git status itself fails, `scoped_state_available` is false and `scoped_dirty`/`scoped_files`/`patch_eligible_files`/`untracked_files` are null instead of claiming a clean scope. Regression tests: `RepairRegressionTests.test_untracked_checker_source_is_reported_scoped_dirty`, `test_modified_tracked_checker_source_is_scoped_dirty_and_patchable`, `test_clean_checker_source_is_scoped_clean`, `test_checker_identity_without_git_reports_unknown_scope`. Reproduced the verifier's untracked-launcher probe: `scoped_dirty True`, file listed in `scoped_files`/`untracked_files`, `patch_eligible_files == []`. Full suite: `Ran 189 tests ... OK (skipped=2)`.
- Reverification notes: 2026-10-08T08:19:35Z: original untracked-launcher probe now returns `scoped_dirty=true`, lists the launcher in `scoped_files` and `untracked_files`, and leaves it outside `patch_eligible_files`. Clean/modified/untracked/non-Git checker regression tests pass; unavailable scope reports null cleanliness. Verified-resolved.

### V-005: Comparison reports omit input execution IDs

- Category: implementation
- Severity: low
- Requirement: Compact reports require input execution IDs/locations; task 3.1 explicitly includes input IDs.
- Evidence: `benchmark/nograph_baseline/checks.py:1113` initializes only input paths/hashes; parsed statuses at lines 1123-1124 contribute state strings at lines 1357-1358, not run IDs. An `ok` comparison through temporary `alpha`/`beta` aliases of authenticated T004 model copies contained neither `p01-r0-sharedridge-001` nor `p01-r0-sharedridge-002`, although their status documents expose those IDs.
- Expected: Each report links the actual execution identity in addition to its current input location and consumed-content identities.
- Actual: Moving/aliasing inputs to names unrelated to their IDs leaves an otherwise successful comparison report without either execution ID. Recompute already has an explicit `input_run_id` field.
- Repair guidance: Include available declared execution IDs for comparison inputs; review all report kinds for the same mandatory envelope field. Keep missing/invalid identities explicit and retain compatibility with old saved runs.
- Acceptance checks: Check each report kind against runs relocated/aliased under names unrelated to their IDs. Assert actual IDs plus locations/hashes and unchanged input bytes.
- Repair status: verified-resolved
- Repair notes: `benchmark/nograph_baseline/checks.py`: compare now publishes `run_a_id`/`run_b_id` (and their status states) from the parsed status documents alongside `run_a`/`run_b` locations and consumed hashes; align-v2 publishes `input_run_id` from the saved `metrics.json`; recompute already published `input_run_id`. Missing IDs remain explicit nulls. Regression tests: `RepairRegressionTests.test_check_reports_link_declared_execution_ids` (two valid runs renamed to `alpha`/`beta`; compare, recompute and align-v2 envelopes carry the declared IDs while locations and consumed hashes are retained and input trees stay unchanged). Re-ran the authenticated legacy T004 copies (`p01-r0-sharedridge-001`/`-002`): compare report inputs now contain both real run IDs, reports remain single-file and inputs unchanged. Reproduced the verifier's alias probe: previously absent, now present. Full suite: `Ran 189 tests ... OK (skipped=2)`.
- Reverification notes: 2026-10-08T08:19:35Z: authenticated old T004 runs exposed through `alpha`/`beta` aliases now publish exact `run_a_id`/`run_b_id`; recompute and align include the exact declared input ID too. All three checks return ok, produce one report each, and leave input trees byte-identical. Renamed new-format fixture regression also passes. Verified-resolved.

## Original Finding Reproduction

These preserved probes describe the initial verification conditions. Their original defects now pass; V-003's mixed-driver condition and current successful result are reproduced separately below. Run from the repository root in the documented CPU environment. The probes use temporary fixtures and do not edit repository inputs.

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python - <<'PY'
import json, subprocess, sys, tempfile
from pathlib import Path
from benchmark.nograph_baseline import artifacts, runner
from benchmark.nograph_baseline.tests import nb_fixtures as fx
with tempfile.TemporaryDirectory(prefix='e13-findings-') as tmp:
    t = Path(tmp)
    invalid = t / 'invalid'; invalid.mkdir()
    (invalid / 'status.json').write_text('{invalid')
    report = t / 'failure.json'
    proc = subprocess.run([sys.executable, '-m', 'benchmark.nograph_baseline',
        'recompute', '--run-dir', str(invalid), '--report', str(report)],
        capture_output=True, text=True)
    print('V-002:', proc.returncode, report.exists(), proc.stderr.strip())
    repo = t / 'repo'; repo.mkdir()
    def git(*args):
        return subprocess.run(['git', '-C', str(repo), *args],
            check=True, capture_output=True)
    git('init', '-q')
    proto = repo / 'protocol.md'; proto.write_text('clean fixture protocol\n')
    src = repo / 'used.py'; src.write_text('VALUE = 1\n')
    git('add', '.')
    git('-c', 'user.name=fixture', '-c', 'user.email=fixture@example.test',
        'commit', '-qm', 'fixture')
    f = fx.build_fixture(t / 'fixture', 'r0', node_count=6)
    spec = fx.make_run_spec(t / 'runs', 'r0', f['demand_path'], f['graph_path'],
        'clean-protocol', repo_root=str(repo), protocol_path=str(proto))
    output = Path(runner.execute_run(spec)['run_dir'])
    source = fx.read_json(output / 'code-source.json')
    print('V-001:', source['protocol']['git_status'],
        (output / 'protocol.md').exists())
    (repo / '.gitattributes').write_text('used.py diff=broken\n')
    git('config', 'diff.broken.command', 'false')
    src.write_text('VALUE = 2\n')
    run = artifacts.RunDirectory(t / 'runs', 'diff-failure', 'run').reserve()
    capture = artifacts.capture_source(run, repo, runtime_paths=['used.py'])
    print('V-003:', capture['errors'], capture['patch_bytes'],
        capture['files']['used.py']['content_saved'])
    launcher = repo / 'benchmark/nograph_baseline/__main__.py'
    launcher.parent.mkdir(parents=True); launcher.write_text('VALUE = 1\n')
    identity = artifacts.checker_source_identity(repo)
    print('V-004:', identity['scoped_dirty'], identity['scoped_files'],
        identity['files'])
PY
```

The original V-005 probe uses any two valid same-condition saved model fixtures: give them different execution IDs, expose them via temporary `alpha`/`beta` aliases, call `command_compare(..., report_path=<new temporary path>)`, and compare the envelope with input `status.json` IDs. Current reports correctly retain both IDs. This verification used already-existing `/tmp/t004-restore/runs/` copies authenticated against sealed member contents; do not require those ephemeral copies or restore the full corpus for repair tests.

## Previous V-003 Reproduction

This preserved binary-marked probe failed in the previous verification. It was rechecked in the current run and now succeeds: the stored binary patch reconstructs the executing bytes with no content copy.

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python - <<'PY'
import subprocess, tempfile
from pathlib import Path
from benchmark.nograph_baseline import artifacts
with tempfile.TemporaryDirectory(prefix='e13-binary-diff-') as tmp:
    t = Path(tmp); repo = t / 'repo'; repo.mkdir()
    def git(*args):
        return subprocess.run(['git', '-C', str(repo), *args],
            check=True, capture_output=True)
    git('init', '-q')
    p = repo / 'used.py'; p.write_text('VALUE = 1\n')
    (repo / '.gitattributes').write_text('used.py -diff\n')
    git('add', '.')
    git('-c', 'user.name=fixture', '-c', 'user.email=fixture@example.test',
        'commit', '-qm', 'fixture')
    p.write_text('VALUE = 2\n')
    run = artifacts.RunDirectory(t / 'runs', 'binary', 'run').reserve()
    record = artifacts.capture_source(run, repo, runtime_paths=['used.py'])
    patch = run.path / record['patch_path']
    recovery = t / 'recovery'
    subprocess.run(['git', 'clone', '-q', str(repo), str(recovery)], check=True)
    result = subprocess.run(['git', '-C', str(recovery), 'apply', str(patch)],
        capture_output=True, text=True)
    print('patch:', repr(patch.read_text()))
    print('content_saved:', record['files']['used.py']['content_saved'],
        'errors:', record['errors'])
    print('git apply:', result.returncode, result.stderr.strip())
    print('recovered executing bytes:',
        (recovery / 'used.py').read_bytes() == p.read_bytes())
PY
```

The external-diff variant replaces the attribute with `used.py diff=custom` before committing and sets `git config diff.custom.command 'printf b/used.py'` in the fixture before modification. Current capture now retains exact fallback bytes and flags the path in `patch_unusable_paths`. This and the nonzero `false` driver variant were independently rechecked; single-file recovery SHA256 matches.

## Current V-003 Reproduction

This multi-file condition failed at 08:30:36Z because the saved aggregate patch was empty. It was independently rechecked in this V-003-only round and now succeeds: the saved patch contains `good.py`'s proven diff, and `broken.py` has exact fallback bytes. The probe below reproduces that condition.

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python - <<'PY'
import hashlib, subprocess, tempfile
from pathlib import Path
from benchmark.nograph_baseline import artifacts
with tempfile.TemporaryDirectory(prefix='e13-mixed-diff-') as tmp:
    t = Path(tmp); repo = t / 'repo'; repo.mkdir()
    def git(*args):
        return subprocess.run(['git', '-C', str(repo), *args],
            check=True, capture_output=True)
    git('init', '-q')
    for name in ('good.py', 'broken.py'):
        (repo / name).write_text('VALUE = 1\n')
    (repo / '.gitattributes').write_text('broken.py diff=broken\n')
    git('add', '.')
    git('-c', 'user.name=fixture', '-c', 'user.email=fixture@example.test',
        'commit', '-qm', 'base')
    git('config', 'diff.broken.command', 'false')
    for name in ('good.py', 'broken.py'):
        (repo / name).write_text('VALUE = 2\n')
    run = artifacts.RunDirectory(t / 'runs', 'mixed', 'run').reserve()
    record = artifacts.capture_source(run, repo,
        runtime_paths=['good.py', 'broken.py'])
    print('saved patch bytes:', record['patch_bytes'],
        'unusable paths:', record['patch_unusable_paths'])
    print('scoped patch error:', record['errors'].get('scoped_patch'))
    recovery = t / 'recovery'
    subprocess.run(['git', 'clone', '-q', str(repo), str(recovery)], check=True)
    patch = run.path / record['patch_path']
    if patch.stat().st_size:
        subprocess.run(['git', '-C', str(recovery), 'apply', str(patch)],
            check=True)
    for name, entry in record['files'].items():
        if entry['content_saved']:
            (recovery / name).write_bytes(
                (run.path / entry['content_saved']).read_bytes())
        digest = hashlib.sha256((recovery / name).read_bytes()).hexdigest()
        print(name, 'content_saved:', entry['content_saved'],
            'recovery matches execution:', digest == entry['sha256'])
PY
```

Previous result: aggregate patch size 0 and `good.py` recovery hash mismatch. Current independently observed result: saved patch size 123 bytes, unusable paths only `broken.py`, `good.py` has no copy but reconstructs from the saved patch, and `broken.py` reconstructs from its saved copy. Both recovered SHA256 values match; `unrecoverable_paths` is empty and the driver error remains explicit. A deletion variant (unlink `good.py` instead of modifying it) saves a 132-byte deletion patch, restores the required absence and also restores `broken.py`. Only temporary fixture repositories/output were produced.

## Next Action

Independent incremental verification passed; all five findings are verified-resolved. The next OpenSpec action is `$openspec-e13-archive-change reduce-baseline-evidence-overhead`. No archive or research acceptance was performed here. The PASS combines the retained earlier scenario evidence with this V-003-only round and applies only to the recorded verification basis; relevant edits require reverification.
