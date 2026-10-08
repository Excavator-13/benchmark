# Implementation Verification

- Change: add-nograph-baseline-ridge
- Schema: spec-driven
- Verdict: PASS
- Verified at: 2026-10-07T10:14:55Z
- Implementation roots: /Users/watuji/da_chuang/repos/benchmark
- Verified revision: a0fdab4268e5e17b0c96453efd53f01a245f01cc, with dirty/untracked implementation, README, task state and run evidence.

## Summary

Independent reverification is **PASS**. V-002 now validates complete method/gain report structures, including required null fields and empty/unavailable statuses. The valid six-node zero-reference fixture returns ok; deleting its null gain, changing unavailable to ok, or deleting an empty group's null MAE each returns mismatch without source access or refitting. No actionable findings remain.

V-001 through V-008 are verified-resolved. The CPU suite ran 147 tests in 8.559 s: 145 passed, two optional sklearn tests skipped. Strict OpenSpec validation passed. All 24 existing run manifests authenticate; all formal and historical evidence remains byte-identical to the previous verification. The four -002 model runs and eight linked checks satisfy the formal command/provenance gap. All eight canonical analysis commands were replayed with the current checker into temporary directories and passed. Each dataset's same-revision pair is bit-identical: maximum absolute prediction difference 0. Prior independent scientific audits remain applicable because the scientific code, source data and formal artifacts are unchanged.

The repaired statistics change cross-revision floating-point reductions slightly without changing scientific definitions, lambda=1e-4 or either LastValue reference. Measured old/new test-prediction differences are 7.275957614183426e-12 absolute / 3.532905505454063e-15 normalized for r0, and 3.637978807091713e-12 / 8.881784197001252e-15 for region. These are separate from the same-revision repetition result and far below 1e-6. Optional real-sklearn execution remains explicitly unverified and is not required for the three-dependency default path.

Only verification.md was changed. No implementation/test/planning/task/handoff/research edits, new formal model experiment, dependency installation, packaging, commit, push, archive or scientific acceptance were performed. All executable verification outputs were confined to temporary fixtures/check directories.

## Verification Basis

The initial snapshot was captured before implementation inspection/checks; the final snapshot is identical. Relative to the previous verification at 2026-10-07T10:03:57Z, only checks.py and tests/test_runner_cli.py changed in the implementation scope. Planning, configuration, protocol, source data, legacy evidence, formal evidence and apply evidence are unchanged, with no added run directories. All paths are relative to the implementation root; inventories detect additions/deletions and content hashes include relevant dirty/untracked files.

| Scope | Files | Inventory SHA256 | Content SHA256 |
| --- | ---: | --- | --- |
| planning | 5 | `0f0e324e12aa638e516fa2668c2d27463a71bd40b927e08ea4757822c0910240` | `77f9703172db73931b0a496db31314642b329b8782495e850bb6cb3cde2053cf` |
| implementation | 23 | `4569ca88208b4527334add6bcda230e42d0da68261f7a4bcfe6984336ab94574` | `bd5041a07c25b757cb79db86e8a12bc88e62615cd5a09b8cb6ba42ef83a74f43` |
| configuration | 4 | `c67a0274af4e626cd75201920ef72843ad9942968655df1b0336eca11d16eae9` | `20e56ab03112a44c5172948bee392ee36ee0b4ee5566a165375153dfc9db9670` |
| protocol | 4 | `2b178cf7f080f55d0296db7a60e41566a23386aadab7cb45c7fa685f9743581d` | `290b21e5edcfc174a3976384dd7c22ef4a893cf960cbaf7bfdac1ac2fd6b78c3` |
| legacy_evidence | 13 | `a3262daa622774a0319cd57280753c9f2777a2fa51b3c760d043a4f0ef895b5f` | `7363a1f203f6390b3aca01b7d242fa68f88528a4b4e9fac8743abc6f1ac8d724` |
| formal_evidence | 780 | `db042f6104247130bca08595cf192b82e29254b4f32c4d5dc52cffc4fc64276a` | `0dd5e80a29d0e9767eb7ed981f33b66932ffead3b14c45aadc494227dc945fb5` |
| apply_evidence | 17 | `bea35342a65d588b2213e16c9c51256db301107eda318b612fca2b80e1ca3aed` | `494b50d030a843ed9cbddea19cefe5b9f7d6bc555bc3e1e94fb6bef4dae5a5d0` |
| source_data | 4 | `a479dd0b05af34d341f4a8d9774ed94cf7770d4fbbcf9ef2779678a9d6def569` | `1e72dc57eec6146013dcdc5fe0a6b7565d33a726943523dbd00196b5f7f1810c` |

Reproduce the snapshot from the repository root with this exact read-only command:

```bash
ruby -rdigest -rjson -e 'scopes = {"planning" => ["openspec/changes/add-nograph-baseline-ridge/.openspec.yaml", "openspec/changes/add-nograph-baseline-ridge/proposal.md", "openspec/changes/add-nograph-baseline-ridge/design.md", "openspec/changes/add-nograph-baseline-ridge/tasks.md", *Dir.glob("openspec/changes/add-nograph-baseline-ridge/specs/**/*.md")], "implementation" => Dir.glob("benchmark/nograph_baseline/**/*"), "configuration" => ["README.md", ".gitignore", "openspec/config.yaml", "AGENTS.md"], "protocol" => ["research/phases/P01/protocol.md", "research/phases/P01/plan.md", "research/phases/P01/execution-guide.md", "research/archives/index.md"], "legacy_evidence" => Dir.glob("research/runs/phase1-20261006-v2-01/*"), "formal_evidence" => Dir.glob("research/runs/p01-*/**/*"), "apply_evidence" => Dir.glob("openspec/changes/add-nograph-baseline-ridge/evidence/**/*"), "source_data" => ["dataset/demand/r0.parquet", "dataset/demand/region.parquet", "dataset/graph/r0.parquet", "dataset/graph/region.parquet"]}; out = scopes.transform_values { |paths| files = paths.select { |p| File.file?(p) && !p.split("/").include?("__pycache__") }.sort; {count: files.size, inventory_sha256: Digest::SHA256.hexdigest(files.join("\n")+"\n"), content_sha256: Digest::SHA256.hexdigest(files.map { |p| p + "\0" + Digest::SHA256.file(p).hexdigest + "\n" }.join)} }; puts JSON.pretty_generate(out)'
```

The inventory hash is SHA256 of sorted relative paths joined with newlines and a final newline. The content hash is SHA256 of concatenated `path + NUL + file_SHA256 + newline` records in that order. Python bytecode caches are excluded. Workflow-owned `verification.md`, `implementation-notes.md` and the apply evidence narrative `implementation.md` are excluded from these fingerprints. Their claims were separately reviewed, not treated as acceptance evidence.

Planning scope includes change metadata, proposal, design, tasks and every delta spec. Configuration includes README, ignore rules, OpenSpec config and AGENTS.md. Formal evidence includes all 24 current `research/runs/p01-*` directories, including saved runtime source copies. The previous FAIL report and all repair-owned notes were read before updating this report.

`git diff --name-only HEAD -- benchmark/graph_method research/phases research/archives research/roadmap.md research/state.md research/decisions.md experiments_archive DELEGATION.md openspec/specs openspec/config.yaml` returned no changed protected paths. Current dirty/untracked changes are the implementation and its permitted documentation/evidence scope. This establishes current scope, not reconstruction of previously deleted historical attempts.

The historical subset (all research/runs/p01-*-001 files, excluding __pycache__) still contains 388 files and has content SHA256 `35f4d81f01765fc550fcb6cf65c07d1cf5462c19f15eeb8b8a2a158baece2d50`, identical to the prior verification. Compute that subset using the same path/NUL/file-hash/newline algorithm with Dir.glob("research/runs/p01-*-001/**/*"). New -002 evidence is included in the full formal_evidence scope above.

## Apply Handoff Review

Read implementation-notes.md and implementation.md from disk. Both identify this change, project root and HEAD correctly. The retained apply handoff is unchanged and describes the original 94-test/one-skip revision and -001 evidence. Its task count, run IDs, manifest counts and no-prior-verification wording are historical claims, not current acceptance evidence. New -002 evidence was located through the preserved repair notes and independently checked.

| Handoff reminder | Disposition |
| --- | --- |
| Region recomputation differs by about 2.43e-16 | Confirmed for -002 as well: method metrics maximum normalized difference 2.433473899736726e-16, gains 0, node errors 7.309841539855388e-16, below 1e-12. |
| Optional sklearn runtime unverified | Still absent; both real-backend tests skipped. V-006's deterministic payload defect remains resolved, but no numerical/equivalence/optional end-to-end success is claimed. |
| Selection/report consistency after normalization and validation-unit fixes | Regression suite passes; new formal candidate scores, exact 27-month statistics, shared objective/normal equations and validation-only winner independently verified. |
| Internal interruption delay must be inert by default | Default remains inert; SIGINT/SIGTERM/SIGKILL and unfinished-state tests pass again. |
| Mandatory coverage evidence | Missing evidence/unknown endpoints reject, supplied definition/provenance checks pass, annotations do not affect forecasts. Independently derived raw masks match all new formal masks. V-004/V-005 resolved. |
| Outputs are unsealed and unbacked-up | All current p01 directories remain untracked; no packaging/backup/research-record work performed. Run success is not archival or scientific acceptance. |
| Apply did not set a verification verdict | Confirmed historical ownership information; this workflow owns the report and verdict. |
| No unresolved planning/environment blockers | No blocking planning conflict found. Optional sklearn absence is nonblocking for the required path. V-002 now independently resolved. |

Preserved runtime sources intentionally identify their execution revision. Every -002 source snapshot differs from current implementation only in checks.py and tests/test_runner_cli.py, the checker-only repair independently inspected this round. Scientific production modules, protocol snapshots and actual source hashes are unchanged. Historical -001 records still have their original incomplete commands; they are retained prior evidence, not the conformant formal evidence claimed by this verification. The existing -002 IDs satisfy V-007 without modifying them; no new model run is needed for this checker-only repair.

Measured cross-revision node_std differences are 1.8189894035458565e-12 for r0 and 9.094947017729282e-13 for region. Test-prediction differences are slightly larger than the approximate value in the user's note (recorded in Summary), still negligible relative to the declared criterion. New statistics match an independent contiguous float64 reduction over exactly the first 27 unique months. The narrative's previously removed/reused earlier attempts remain unavailable and outside the present evidence basis.

## Checks

Interpreter: `/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python` (Python 3.11.17; NumPy 1.26.4, pandas 2.2.3, PyArrow 17.0.0; sklearn absent).

| Command or inspection | Result | Notes |
| --- | --- | --- |
| `openspec status --change add-nograph-baseline-ridge --json`; `openspec instructions apply --change add-nograph-baseline-ridge --json` | Resolved | Local spec-driven change; all context files present; 32/32 task checkboxes. No apply workflow executed. |
| `openspec validate add-nograph-baseline-ridge --type change --strict --json --no-interactive` | PASS | valid=true, issues=[]. Structural check only. |
| `python -B -m unittest discover -s benchmark/nograph_baseline/tests -v` | PASS | 147 tests in 8.559 s; 145 passed, two optional sklearn skips. Includes every normative fixture scenario, minimal dependencies, interruption, replay and seven new null/schema/semantic regressions. |
| All 24 run manifests and historical subset hashes | PASS | Zero file-hash mismatches. Each -002 model directory has 74 files, 72 in the hash manifest and two declared exclusions. Historical 388-file content hash unchanged. |
| Formal source, environment, command and code capture | PASS | All twelve -002 commands start with recorded interpreter/-m/module/subcommand and parse. Scientific model sources/protocol/data remain unchanged; only checker and checker tests differ from the recorded execution revision. Prior source/environment audits retained by fingerprints; optional sklearn absent. |
| Replay all eight recorded -002 analysis commands | PASS | Each command executed from recorded cwd with only new temporary run ID/output root; exit 0. Source formal directories unchanged. Model command replay is covered by the fresh fixture test; no new production model execution. |
| Current saved-only recomputation of four -002 model runs | PASS for intact reports | r0 metrics/gains/node errors 0; region method metrics 2.433473899736726e-16, gains 0, node errors 7.309841539855388e-16. |
| Current comparison of the two -002 same-seed pairs | PASS | All identity predicates true; prediction maximum absolute difference 0 for every method/split and metric differences 0. |
| Current v2 alignment for both new primary runs | PASS | 411 compared fields, zero discrepancies each; canonical sources match and original reference hash unchanged. |
| Independent new formal scientific audit | PASS | Canonical keys, raw gold, masks, exactly 27-month mean/std, constant effective std, all five naive predictions, shared-W/b reconstruction, candidate alpha/sample counts/objective/normal equations and selected winner verified. |
| Independent all-level metrics and gains | PASS for present reports | 1,716 numeric checks per r0 run, 2,472 per region run; maximum normalized differences 2.0019799835458697e-16 and 2.433473899736726e-16. Also verifies empty/null statuses on actual saved outputs. |
| New formal measurements | PASS | Per-run stage durations and resource peak RSS; bytes 143278080, 146374656, 307396608, 309379072. Measured costs, not extrapolated promises. |
| Prior V-001 condition mutations | PASS | Independent changed BLAS/OS/CPU/python_version probes now mismatch. Required-condition absence regression passes. Valid actual pairs remain ok. |
| Prior V-002 finite-field/nonfinite probes | PASS | Independent deleted finite gain, deleted method report and NaN node-MAE probes now mismatch; suite also covers nonfinite method metrics. |
| V-002 required-null/status probes | PASS | Valid original fixture ok; deleted null gain, unavailable-to-ok status and deleted empty-group null MAE each mismatch. Empty-to-ok status and numeric-as-string also reject. Sources removed and load_demand/fit_candidates guarded against calls. |
| Adjacent report-structure probes | PASS | Direct complete-schema comparisons reject list-length mismatch, an extra null field and a boolean replacing a number. A supplemental fixture probe used an incorrect per_horizon key and stopped before the check; this was a probe error, corrected with the direct structural checks. |
| V-003/V-004 regression coverage | PASS | Source identity mismatch/limited reference, known/unknown self-loops, context qualification and ordinary endpoints rerun successfully. |
| V-005/V-008 independent probes | PASS | Contradictory text-only coverage definition rejects; native/API 2**63 keys reject before narrowing with zero warnings. Valid range/definition/provenance regression tests pass. |
| V-006 payload contract | PASS for original defect | Producer/validator/writer fields match; real optional backend tests remain skipped. |
| Scope and final snapshot | PASS | Protected-path diff empty; initial/final scope fingerprints identical. |

PyArrow's sandbox-restricted sysctl warnings did not prevent any read/write or check. Independent scientific checks read source tables only to establish identities, normalization and reconstruct predictions; saved-only checks and their replays did not read demand/graph sources or refit.

Evidence freshness: this round reran strict validation, the complete CPU suite, all 24 manifests, eight recorded analysis commands, V-002 fixture/structural probes, source-snapshot comparisons, direct pair prediction/numeric-metric comparisons and scope fingerprints. Prior independent raw-source/normalization/model/all-level metric audits and V-005/V-008 manual probes were retained from the previous verification, with unchanged relevant code and evidence fingerprints; their regression tests passed again. Pair metrics differ only in run_id metadata; numeric differences are zero.

The retained numerical audit used independently calculated float64 errors, MAE/MSE/sqrt(MSE), all saved mask/context/window/horizon slices, negative ratios, error sums/contributions and balanced nonempty-group MAE. It checked gains against model/reference MAEs with null handling for unavailable/zero references. Candidate W/b satisfy the centered shared Ridge normal equations with alpha=lambda*M; original-unit validation scores determine the same lambda winner. The current executable V-002 probes additionally establish the shipped checker's rejection of malformed null/status evidence.

## Requirement Coverage

R1-R13 refer to delta requirements in document order; S1-S23 enumerate every scenario. PASS below is scoped to the stated check, not the overall change verdict.

| Requirement / scenario | Evidence | Result |
| --- | --- | --- |
| R1 Independent CPU entry follows the research protocol | cli/protocol/local dependencies; blocked-import smoke for both schemas; README commands | Required NumPy path PASS; V-006 payload defect resolved, actual optional sklearn runtime unverified. |
| S1 Minimal dependency environment | test_minimal_dependency_smoke_for_both_schemas rerun, including worker | PASS |
| S2 Unsupported scientific configuration | argparse r2/rate rejection; fixed protocol constants and no split overrides | PASS |
| R2 Demand identity and observations are validated | data.py; source/key/column/audit tests; independent production key check | PASS: native/API validation including exclusive int64 upper bound; V-008 resolved. |
| S3 Valid data arrives out of order | test_shuffled_parquet_preserves_key_value_alignment; actual saved sorted keys | PASS |
| S4 Source is invalid | Duplicate/month/nonfinite/negative/native-underflow tests rerun; native/API int64 upper-bound rejection | PASS |
| R3 Fixed windows isolate target months and preserve rolling origins | protocol.py/data windows; exact 19/1/4 splits and disjoint targets in saved outputs | PASS; no test data passed to fitting/selection. |
| S5 Protocol split is constructed | SplitTests and all-starts/omissions checks | PASS |
| S6 Second test origin uses known history | Two rolling-history tests and source-derived test labels | PASS |
| R4 All naive methods and frozen references are reported | baselines.py; five production outputs; all v2 metric comparisons; frozen table-order references | PASS |
| S7 Validation MSE ties | test_exact_tie_uses_protocol_table_order | PASS |
| S8 Seasonal prediction uses extra history | Seasonal value/label tests and metadata; NaiveRef6 excludes SeasonalNaive12 | PASS |
| R5 Normalization counts training observation months exactly once | compute_training_stats; adversarial tests; saved mean/std exactly match unique first 27 observations | PASS |
| S9 Overlapping training windows have unequal month multiplicities | test_exactly_27_unique_observations, target-only/overlap comparisons | PASS |
| S10 Future values change | test_later_values_do_not_change_statistics_or_fits; fit/selection signature tracing | PASS |
| S11 Constant training node | Constant-node finite-standardization test; stored effective std | PASS |
| R6 Ridge parameters shared and selected exclusively on validation | Independent augmented least-squares fixture; 6x3 W/3 b; M=19*N; production candidate scores and lambda winner | NumPy scientific behavior PASS; V-006 schema defect resolved; optional solver execution remains unverified. |
| S12 Test labels cannot affect selection | MSE-versus-MAE fixture and API tracing; original-unit candidate regression tests | PASS: fit/selector receive training/validation only. |
| S13 Lambda scores tie | test_exact_mse_tie_selects_larger_lambda | PASS |
| S14 Sum-loss backend is used | NumPy sum-form normal equations and all five alpha=lambda*M checks | NumPy scaling PASS. Optional sklearn alpha=M*lambda and payload inspected; actual optional numerical test skipped. |
| R7 Metrics use common fixed masks and original units | metrics.py; retained independent group/context/window/horizon/error-sum/gain calculations; current null/status fixtures | PASS; required nulls/statuses preserved and malformed reports reject (V-002 resolved). |
| S15 Window RMSE values differ | Analytic test plus independent global sqrt(mean square) calculation | PASS |
| S16 Activity boundaries and an empty group | Four-boundary and empty-group tests; all methods share saved masks | PASS |
| R8 Neighbor coverage is an evaluation annotation | Context-qualified tests, production coverage sources and forecast-invariance tests | PASS: V-004/V-005 resolved; raw coverage matches new saved masks, semantic ID/canonical text and provenance validate. |
| S17 Same skill occurs in two regions | test_same_skill_in_two_regions_is_context_qualified; annotation invariance | PASS for valid endpoints |
| R9 Each run saves recoverable and independently recomputable evidence | Atomic numeric outputs, masks/identities/models, provenance and interruption suite | PASS; formal/check command provenance and complete null/status recomputation validation resolved. |
| S18 Metrics are independently recomputed | Saved-array reductions, all four current formal recomputations and source-disabled fixture mutations | PASS; intact reports succeed, missing null metric/gain fields and contradictory statuses reject. |
| S19 Run is interrupted or collides | Existing-ID rejection, SIGINT/SIGTERM/SIGKILL and unfinished-state tests | PASS for current runtime behavior |
| R10 Same-seed CPU repetition without artificial seed variance | Actual two-pair comparisons and same-seed fixture test | PASS: both new formal pairs bit-identical; differing/missing BLAS/OS/CPU condition evidence rejects (V-001 resolved). |
| S20 Same seed is executed twice | All-method array maximum absolute differences 0; metric differences 0 | PASS for actual same-condition pairs |
| R11 Runtime costs are actual measurements | runner perf_counter/resource implementation, four measurements and environments | PASS on recorded macOS CPU; no extrapolated promise |
| S21 A formal CPU run finishes | Four measured stage/RSS records, native-unit assertions | PASS |
| R12 Formal results align with immutable v2 diagnostics | Independent v2 field reductions/source identity checks; discrepancy fixture | PASS: current numerical/source alignment and mismatch/missing-source cases; V-003 resolved. |
| S22 Legacy naive value differs | test_align_v2_preserves_and_explains_discrepancy; immutable log fingerprint | PASS for differing metric values |
| R13 Both datasets produce complete formal artifacts | Four authenticated model runs plus eight check runs, all methods and measured evidence | PASS; existing -002 formal/repeat/check artifact sets complete and current analysis-command replays pass. |
| S23 Execute both supported datasets end to end | Actual -002 r0 and region pairs, source copies, manifests and retained reconstructed predictions | Required NumPy formal execution/provenance PASS; checker-only repair passes current saved-evidence checks. |

Scope and completed-task review again checked README's "recompute every metric" promise, the optional backend, fresh run reservation and protected paths. No r2/rate/backtest/graph-training/gating implementation was found. The design's earlier-than-selection construction of test inputs/labels does occur, but tracing shows no test labels enter optimization or selection; it is not reported as scientific leakage.

## Findings

### V-001: Recorded execution conditions now participate in repeat comparison

- Category: implementation
- Severity: high
- Requirement: R10; design Decision 7; task 1.12.
- Evidence: checks.py:135-161 includes BLAS, full Python version, OS platform, processor, CPU count, packages, pip freeze and thread settings, plus required-presence checks. Independent copies changing numpy_blas_config, platform, processor, cpu_count or python_version all return mismatch.
- Expected: Require matching recorded execution conditions and complete source/environment evidence.
- Actual: Original environment-condition omissions and coverage predicate defect are fixed; both actual -002 pairs return ok with all boolean identity predicates true.
- Repair guidance: No remaining repair for this finding.
- Acceptance checks: Changed/missing condition regression tests and independent mutations pass; valid pairs have prediction maximum absolute difference 0.
- Repair status: verified-resolved
- Repair notes: checks.py: extended _ENVIRONMENT_IDENTITY_FIELDS from six fields to the recorded execution condition set (python_version, python_version_info, platform, system, machine, processor, cpu_count, packages, optional_packages, numpy_blas_config, pip_freeze, thread_environment), keeping invocation paths and timestamps out. Added _missing_environment_fields and the boolean environment_condition_complete predicate; absent/null condition fields are listed in missing_evidence so they are incomplete rather than agreement. Tests: test_compare_rejects_different_blas_os_or_cpu_conditions (numpy_blas_config, platform, processor, cpu_count, python_version), test_compare_requires_condition_fields_present, test_compare_valid_pair_still_ok. All five temporary-copy mutations now return mismatch; removing numpy_blas_config returns mismatch with environment_condition_complete=false; the current r0/region pairs remain ok.
- Reverification notes: Rechecked both positive formal pairs and five distinct negative environment mutations; the original finding is resolved.

### V-002: Recompute still ignores required null metrics and unavailable gain status

- Category: implementation
- Severity: medium
- Requirement: R7 explicit empty/unavailable metrics and undefined zero-reference gains; R9/S18 complete saved-only recomputation; design Decisions 2 and 5; tasks 1.12/2.4.
- Evidence: checks.py:324 compare_report_schema compares complete structures; checks.py:461 validate_report_semantics checks null/status contradictions; command_recompute applies them to method and gain reports. Independent reproduction of the previous six-node fixture returns ok intact and mismatch for each of the three previously false-success mutations. The suite's new all-zero fixture also passes all focused regressions.
- Expected: Require the null-valued metric/gain field and correct empty/unavailable semantic status when the saved arrays show an empty group or zero/unavailable reference. Missing or contradictory mandatory report fields must produce non-success.
- Actual: Missing finite/null fields, whole-method omissions, nonfinite values and contradictory empty/unavailable statuses reject. Legitimate null metrics and undefined zero-reference gains remain null. All four intact -002 reports recompute within 1e-12.
- Repair guidance: No remaining repair; preserve existing formal evidence for this checker-only change.
- Acceptance checks: A valid zero-reference/empty-group fixture succeeds. Separately deleting its null gain, deleting an empty group's null MAE, or changing unavailable/empty status to ok must fail. Existing finite-field/NaN tests and four intact -002 recomputations stay passing; source access/refitting remains unnecessary.
- Repair status: verified-resolved
- Repair notes: checks.py (checker only; no model or formal evidence was rerun): added compare_report_schema, which walks the complete report structure - dictionary key sets (ignoring the harness metadata keys method/split/dataset/nonself_neighbor_coverage_source), list lengths, nulls, booleans, status strings and finite numbers within the normalized tolerance - so a required null-valued field that was deleted from the stored report is now reported in missing_fields instead of being dropped by finite-number flattening. command_recompute uses it for both the method reports and relative gains, with the recomputed structure as reference and the stored report as the validated side. Added validate_report_semantics, which checks null/status consistency (empty status must have zero elements and null MAE/MSE/RMSE/negative ratio; ok status must have non-null metrics and elements; balanced_activity_group_MAE must be null exactly when the activity status is empty; relative_MAE_gain must be null exactly when a zero-reference gain status is unavailable) for stored methods, recomputed reports and stored gains, reported as report_semantics. Tests: new RecomputeNullSemanticsTests uses a saved-only all-zero six-node fixture (zero LastValue reference, empty activity groups, 204 legitimate null fields) and covers intact ok, deleted null gain, changed unavailable->ok status and deleted empty-group null MAE; direct unit tests cover compare_report_schema null preservation and validate_report_semantics contradictions. Existing finite/NaN regressions were updated to the missing_fields naming. Checks: `python -m unittest discover -s benchmark/nograph_baseline/tests` -> 147 tests OK, 2 optional sklearn skips. All four intact -002 model runs still recompute ok with zero missing/extra fields and no semantic problems (r0 max normalized difference 0.0; region 2.433473899736726e-16). This round changed only checks.py, its tests and this report; no run writer was executed.
- Reverification notes: Resolved at 2026-10-07T10:14:55Z. The prior three probes now mismatch; their paths appear in missing_fields or failed_fields, and the changed gain status produces a semantic finding. The intact fixture passes with sources removed and source-loader/fitter calls guarded. Empty-to-ok and numeric-as-string fixture mutations reject; direct adjacent structure/type probes reject. All four formal recomputations and the 147-test suite pass. No new model execution or formal-evidence modification was needed.

### V-003: v2 identity mismatch affects alignment outcome

- Category: implementation
- Severity: medium
- Requirement: R12 immutable diagnostic identity alignment.
- Evidence: Current source-mismatch, missing-v2-manifest and valid-reference tests pass. Both new primary alignments compare 411 fields without discrepancies and declared source hashes match the immutable v2 sources.
- Expected: Contradictory identity prevents success; missing evidence is explicitly limited.
- Actual: The original false-success source-mismatch behavior remains repaired.
- Repair guidance: No remaining repair.
- Acceptance checks: Mismatch/limited/valid-reference regressions pass; formal alignment and reference immutability authenticate.
- Repair status: verified-resolved
- Repair notes: checks.py: command_align_v2 now appends source-identity checks to the compared fields and folds them into discrepancies and the final status. A contradictory v2-vs-run demand SHA256 yields status mismatch with an identity finding; a reference without source-sha256.txt yields explicit status limited (and a nonzero CLI exit) instead of success; reference integrity is also checked. The run source manifest is read tolerantly. Tests: test_align_v2_rejects_source_identity_mismatch, test_align_v2_reports_limited_without_v2_source_manifest, test_align_v2_valid_reference_still_ok. Current r0/region alignments remain ok (411 compared fields, 0 discrepancies).
- Reverification notes: Previously resolved behavior rechecked in the complete current suite and new formal evidence.

### V-004: Self-loop endpoints validate before coverage exclusion

- Category: implementation
- Severity: medium
- Requirement: R8 endpoint membership and non-self neighbor coverage.
- Evidence: Raw coverage tests rerun: unknown skill/context self-loops raise CoverageError; known self-loops supply no neighbors. Independent raw-graph mask derivation equals every new formal saved mask.
- Expected: Validate context-qualified endpoints before excluding valid self-loops.
- Actual: The original membership bypass is repaired.
- Repair guidance: No remaining repair.
- Acceptance checks: Unknown/valid self-loop, ordinary-edge, context qualification and forecast-invariance tests pass.
- Repair status: verified-resolved
- Repair notes: coverage.py: load_graph_coverage now resolves both context-qualified endpoints of every graph row before deciding whether the row is a self-loop, so an unknown endpoint referenced only by a self-loop raises CoverageError while valid self-loops still supply no neighbour. Tests: test_coverage.test_unknown_self_loop_endpoint_fails_validation (unknown skill and unknown context), test_valid_self_loop_excluded_while_edges_cover_both_ends.
- Reverification notes: Current full-suite and production mask checks confirm resolution.

### V-005: Supplied coverage bundles declare protocol semantics

- Category: implementation
- Severity: medium
- Requirement: R8; design Decision 2; supplied definition/provenance contract.
- Evidence: coverage.py now requires a nonempty string plus the stable COVERAGE_DEFINITION_ID or a supported canonical definition text. An independent text-only bundle declaring self-loop neighbors/ignored contexts now raises CoverageError; definition-id/text/provenance/schema/native-bool tests pass.
- Expected: Require protocol context-qualified non-self coverage declaration, aligned identity and original-source provenance.
- Actual: Anonymous/incorrect definition/provenance/schema/dtype bundles reject. The stable semantic ID is authoritative for ID-bearing bundles; text-only bundles must use canonical semantics. The saver emits the canonical ID/text.
- Repair guidance: No remaining repair for this finding.
- Acceptance checks: Contradictory text-only definition, wrong ID, empty/non-string definition and missing provenance reject; canonical ID/text representations round-trip; annotation invariance passes.
- Repair status: verified-resolved
- Repair notes: coverage.py: added COVERAGE_DEFINITION_ID and ACCEPTED_COVERAGE_DEFINITIONS. save_mask_bundle always writes the protocol's canonical definition text and identifier (caller text is not trusted), still requiring a 64-hex source SHA256. load_mask_bundle now rejects non-string or empty definitions, rejects a definition_id other than the protocol identifier, and rejects a definition that is neither the canonical text nor paired with the canonical id, so a self-loop-counting or context-ignoring definition fails. Tests: test_contradictory_definition_is_rejected, test_non_string_or_empty_definition_is_rejected, test_wrong_definition_id_is_rejected, test_canonical_definition_representations_are_accepted, test_saved_bundle_records_canonical_definition, plus the existing dataset/schema/source/dtype rejections.
- Reverification notes: Independently reran the prior contradictory-definition probe and inspected the explicitly tested ID-or-canonical-text contract; no different scientific coverage definition is introduced.

### V-006: Optional backend supplies the shared serialization payload

- Category: implementation
- Severity: medium
- Requirement: Optional backend support; design Decision 4; R9 model persistence; task 1.7.
- Evidence: fit_sklearn returns both centered means required by MODEL_PARAMETER_KEYS and the artifact writer; static return-schema and actual NumPy contract tests pass again.
- Expected: Producer and writer contracts agree; optional backend records alpha=lambda*M.
- Actual: The original deterministic missing-field defect is resolved. sklearn remains absent, so actual optional numerical equivalence/end-to-end tests skip.
- Repair guidance: No remaining repair for the original missing-field defect; run optional tests when a suitable environment is available.
- Acceptance checks: Required NumPy contract/serialization passes. Optional real-backend tests exist but remain skipped, not counted as successful runtime evidence.
- Repair status: verified-resolved
- Repair notes: ridge.py: fit_sklearn now computes and returns centered_x_mean/centered_y_mean, and both solvers are wrapped in the new validate_model_payload contract (MODEL_PARAMETER_KEYS); runner._save_model_artifacts validates the selected payload before writing, so an incompatible optional backend fails before partial artifacts. Tests: ModelPayloadContractTests (numpy payload contract, legacy sklearn-shaped payload rejected, static AST check that fit_sklearn's returned dict declares every contract key) and the sklearn-skipped end-to-end artifact test. scikit-learn remains absent here, so the optional end-to-end and numerical-equivalence tests are skipped (2 skips).
- Reverification notes: Resolution remains scoped to the original schema defect. No mocked sklearn success or actual optional solver validation is claimed.

### V-007: Fresh formal and linked check evidence records canonical commands

- Category: implementation
- Severity: medium
- Requirement: R9 exact-command provenance; R13 complete formal/repeat/check evidence; tasks 3.1-3.8.
- Evidence: Four -002 model runs and eight new linked checks record [recorded interpreter,'-m','benchmark.nograph_baseline',subcommand,...]. Each model contains 74 files (72 hashed artifacts plus two excluded files), current source capture, protocol/source/config/environment/arrays/models/selection/measurements/status. All eight recorded check commands replayed successfully into temporary new IDs.
- Expected: Conformant two-dataset formal and same-seed evidence with complete exact command/provenance, while preserving historical runs.
- Actual: New primary/repeat runs for both datasets, recompute for all four, compare for both pairs and both primary alignments are complete and authentic. Same-revision differences are 0. Historical -001 files remain unchanged.
- Repair guidance: No new model runs are needed for this resolved finding; preserve both revisions.
- Acceptance checks: Canonical argv/parser/source/manifests, fresh fixture model-command replay, all eight saved analysis-command replays and new formal scientific audits pass.
- Repair status: verified-resolved
- Repair notes: Produced the required fresh formal and linked analysis evidence with the corrected public CLI, preserving every historical run (old -001 directories were not modified). New model runs: p01-r0-sharedridge-002, p01-r0-sharedridge-repeat-002, p01-region-sharedridge-002, p01-region-sharedridge-repeat-002 (all status=success, 74-file artifact sets). Fresh linked checks: p01-r0-recompute-primary-002, p01-r0-recompute-repeat-002, p01-r0-repeat-check-002 (compare ok, all identity predicates true, max prediction absolute difference 0.0), p01-r0-alignment-002 (411 fields, 0 discrepancies); p01-region-recompute-primary-002, p01-region-recompute-repeat-002, p01-region-repeat-check-002 (ok, identity true, max prediction difference 0.0), p01-region-alignment-002 (411 fields, 0 discrepancies). Every new record's command.json argv is [interpreter, '-m', 'benchmark.nograph_baseline', <subcommand>, options] with launcher_cwd recorded and is replayable. Code fix remains as previously reported (_canonical_command, launcher_cwd, cwd_differs_from_launcher); fixture replay test still passes. Note for reverification: scientific results are unchanged (λ=1e-4, LastValue references) but the repaired statistics path shifts frozen node_std and SharedRidge predictions by at most ~1.8e-12 absolute (~1e-16 relative) versus the pre-repair runs; each revision's same-seed pairs are bit-identical (max prediction difference 0.0), far inside the 1e-6 CPU criterion.
- Reverification notes: Formal evidence gap remains closed by -002 IDs without patching historical commands. Corrected scientific outputs were independently reconstructed in the preceding verification and are unchanged. All eight recorded analysis commands replay successfully with the current checker; V-002 is now resolved.

### V-008: Native float keys reject the exclusive int64 upper bound

- Category: implementation
- Severity: medium
- Requirement: R2/S4 native identity/value validation; design Decision 3.
- Evidence: data.py validates floating keys against [-2**63,2**63) before casting and then verifies round-trip identity. Independent native-Parquet/API 2**63 probes both raise DemandError with zero cast warnings; valid-range/underflow/fractional tests pass.
- Expected: Reject invalid native identities before lossy narrowing while retaining valid key values.
- Actual: The original tiny-negative/fractional cases and exact upper-bound overflow are repaired; all new formal keys match sorted raw sources.
- Repair guidance: No remaining repair.
- Acceptance checks: API/native upper endpoint rejects; -2**63 and largest valid representable float keys retain identity; production canonical keys unchanged.
- Repair status: verified-resolved
- Repair notes: data.py: floating node keys now validate against the asymmetric int64 range with an exclusive upper bound (floating >= float(2**63) or floating < float(-(2**63)) is rejected) instead of comparing abs() to the rounded float(np.iinfo(int64).max)==2**63, and a post-cast round-trip identity check rejects any key that changes during narrowing. The integer-dtype path keeps its exact int64/uint64 bounds check. Tests: test_int64_upper_bound_float_key_is_rejected (float(2**63) and above), test_int64_lower_bound_and_representable_keys_are_accepted (-(2**63) and the largest representable float), test_native_int64_upper_bound_key_is_rejected. Both API and native-Parquet 2**63 probes now raise DemandError without a narrowing warning; valid production keys are unchanged.
- Reverification notes: Independently reran native-Parquet and API boundary probes; full current identity regression suite passes.

## Reproduction Guide

All probes use the dedicated interpreter from Checks and TemporaryDirectory copies/fixtures. Never alter -001, -002 or legacy reference directories. The original V-002 reproduction is retained as a passing rejection check, without production data, GPU or graph libraries:

```python
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from benchmark.nograph_baseline import checks, runner
from benchmark.nograph_baseline.tests import nb_fixtures as fx

with TemporaryDirectory() as temp:
    root = Path(temp)
    fixture = fx.build_fixture(root / "fixture", node_count=6)
    spec = fx.make_run_spec(
        root / "runs", "r0", fixture["demand_path"],
        fixture["graph_path"], "fixture",
    )
    saved = Path(runner.execute_run(spec)["run_dir"])
    for case in ("missing-null-gain", "wrong-status", "missing-empty-MAE"):
        copied = Path(shutil.copytree(saved, root / case))
        document = json.loads((copied / "metrics.json").read_text())
        if case == "missing-empty-MAE":
            group = document["methods"]["test"]["SharedRidge"]["activity_groups"]["low"]
            assert group["elements"] == 0 and group["MAE"] is None
            del group["MAE"]
        else:
            references = document["relative_gains"]["test"]["SharedRidge"]
            group = next(iter(references.values()))["activity_groups"]["inactive"]
            assert group["reference_MAE"] == 0 and group["relative_MAE_gain"] is None
            if case == "missing-null-gain":
                del group["relative_MAE_gain"]
            else:
                group["status"] = "ok"
        (copied / "metrics.json").write_text(json.dumps(document))
        result = checks.command_recompute(
            run_dir=copied, run_id=case, runs_root=root / "checks",
            repo_root=Path.cwd(), command=["independent verification"],
        )
        print(case, result["status"])  # each now prints mismatch
```

Observed after repair: the valid original fixture returns ok and each mutated copy returns mismatch with a field/semantic finding. This round additionally removed the fixture's demand/graph files before recomputation and guarded data.load_demand/ridge.fit_candidates against calls. For the missing-null-gain case, the reference MAE is 0.0 while SharedRidge MAE is 0.013976833701896584; protocol gain remains explicitly undefined.

Previously failing finite-gain/method deletion, NaN node-MAE, BLAS/OS/CPU differences, contradictory text-only coverage definition and native/API 2**63 keys now reject in independent probes. Recorded -002 analysis commands replay successfully with new temporary run IDs/output roots, and fixture model-command replay remains passing.

## Next Action

Use `$openspec-e13-archive-change add-nograph-baseline-ridge` next. This PASS applies only to the recorded verification basis; relevant edits require independent reverification before archive.

The four -002 model runs close V-007 and contain correct scientific outputs. The checker-only V-002 repair is independently resolved without new model experiments; preserve all existing runs and use fresh IDs for any retained corrected analysis evidence. If fitting/normalization/prediction code changes, affected formal evidence must be reconsidered.

Optional real-sklearn execution remains unverified; research acceptance, sealing, archival status, commits and backup remain outside this verification. Archive was not invoked by this turn.
