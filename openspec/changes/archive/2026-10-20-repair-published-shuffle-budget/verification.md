# Implementation Verification

- Change: repair-published-shuffle-budget
- Schema: spec-driven
- Verdict: PASS
- Verified at: 2026-10-20 14:02 Asia/Shanghai
- Implementation roots: C:/Users/Lenovo/Documents/大创参考论文/JODBSDFres/benchmark
- Verified revision: dc9933081e396f3d6c92c801c2f080954de464ec plus the fingerprinted dirty worktree
- Verification boundary: independent review/tests; no implementation, test, planning, task or apply-note edits by verifier

## Summary

All mandatory scenarios have executable or direct static evidence; strict OpenSpec validation succeeds. Independent baseline: 287 tests, zero failures/errors, eight explicit environment skips. Independent skeleton: 134 tests, zero failures/errors, four explicit symlink-privilege skips. Independently rechecked all 18 published artifacts, nine regeneration pairs and 360 context timings with all input files unchanged. V-001/V-002/V-003 are verified-resolved.

This is implementation verification and development graph readiness, not research acceptance, formal-model completion, evidence of mixing or predictive benefit. The next workflow is `$openspec-e13-archive-change repair-published-shuffle-budget`. PASS applies only to the recorded basis; relevant edits require reverification.

Residual environment limits: Windows denies symlink creation, POSIX signal delivery is unavailable, optional sklearn is absent, and one file-permission probe cannot restrict this user. Those branches are explicit skips, not passes. A real controlled watchdog triggered on time and retained the original timeout/termination error; taskkill could not terminate its owned child in this restricted tool environment. The harmless five-second child exited naturally and was joined. Production use must honor paused/worker_may_be_running and arrange permitted termination when cleanup is denied. No source/path protection or scientific tolerance was relaxed.

## Verification Basis

The initial 62-file snapshot was taken before executable review. Since then the only changed initial inputs were README.md, checks.py, prepared.py, test_prepared.py and tasks.md; all affected runtime/test behavior was rechecked by the final complete skeleton run and independent published saved checks. No initial inventory entry disappeared. Final planning has 15/15 checked tasks; handoff/report files are excluded from content fingerprints by workflow policy.

Each group fingerprint is SHA-256 of UTF-8 `json.dumps({repo_relative_posix_path: sha256(file_bytes)}, sort_keys=True, separators=(',', ':'))`. Both inventory additions/deletions and byte changes alter the digest. Sorted inventories are specified below; the recorded counts disambiguate the scopes.

| Scope | Files | Inventory/content SHA-256 |
| --- | ---: | --- |
| `benchmark/graph_value_skeleton` | 33 | `05effc777d0c539e0696b6e046299a877fc7d193c8ea3a75fa5155f741929d67` |
| `benchmark/nograph_baseline` | 24 | `9d03ceec387b4b2851aa234f36814cd5e963bb0f2347f253b77a1c0bc9ba9274` |
| `decisive_evidence` | 7 | `0249cfb8eb4cf2af7cff8ff1cec766663801a69743f829def299998ed3a21bd6` |
| `independent_saved_reports` | 19 | `f801e26b70c67e1aab4f889158f7ab0ed3abeb946d12bd4ef79cb050bbab7d58` |
| `planning` | 5 | `cf5021f45ef27f5598baac771c65feee825d4cc2b6e1aba35dd253f1782695b8` |
| `published_matrix` | 38 | `b8786d28bb388753f55bf2523b691971e4ae16fe75a07805bca0c670a388805b` |
| `support` | 5 | `d47f2f5f92370fd7d9e3c6d9dff824ce01e5a79c1d6fcd339af1ff8ffa8b2e5d` |

Scope inventories:
- The two benchmark package groups contain all recursive `*.py` files and their `requirements.txt`, excluding `__pycache__`. Thus runtime, tests and fixture helpers are covered.
- Planning contains proposal.md, design.md, tasks.md, .openspec.yaml and all specs/**/*.md within this change.
- Support contains README.md, requirements.txt, openspec/config.yaml, and this change's run_tests.py and benchmark_membership.py.
- Decisive evidence contains this change's evidence/{independent-baseline-20261020-01.json, independent-baseline-20261020-01.log, independent-skeleton-20261020-01.json, independent-skeleton-20261020-01.log, published-readiness-accepted.json, protected-final-regressions.json, membership.json}.
- Published matrix contains scratch/graph-value-skeleton/repair-shuffle-v2-20261020-06/{readiness.json,status.json}, each of its 18 member checksums.json, and each original report path named by readiness.json. The checksum manifests transitively identify nine required artifact files; verification additionally hashed all 38 files in every member directory before/after.
- Independent saved reports contains all 19 JSON files in scratch/graph-value-skeleton/independent-published-check-20261020-01. Its summary SHA-256 is c3e7035067cfcd1a33db4c93656de094bef89f3c4105b3b26ef2581f1ec2267b.

Reproduce each group by building the inventory above, reading file bytes, and applying the exact JSON/hash algorithm. After archive, relocate the change-root prefix consistently when comparing planning/support/evidence inventory names; runtime hashes remain unchanged. Missing scratch evidence must be reported as missing, not regenerated under old identifiers.

## Apply Handoff Review

Read the final implementation-notes.md: selected change/root/revision agree with disk; task-to-evidence mapping is complete. Earlier partial/failing notes are retained separately and do not override final independent results. Every reminder was reviewed:
1. Independent V-001/V-002/V-003 resolution: confirmed by full-suite and artifact checks below.
2. Saved authenticity boundary: confirmed; structural identity/invariants are checked, no historical-authenticity proof is claimed.
3. Platform skips: confirmed from both independent JSON/logs; remain disclosed limits.
4. Fresh Windows CLI/DLL import order: independent fresh CLI preparation and public CLI self/graph/shuffled fixtures pass; torch loads before pandas/Arrow on the Windows preparation path.
5. Real cleanup-denial branch: independently reproduced with harmless sleep child; original timeout and cleanup failure retained. Mocked matrix tests also verify paused state, stop scheduling, cleanup_error, PID and worker_may_be_running.
6. Performance claims: set/dense benchmark inspected, complete suite independently verifies exact backend/stream equality. Dense was slower; tuple/set retained. No unsupported speedup, mixing or benefit claim.
7. Local scratch/provenance storage: evidence has resolvable paths/checksums; no sealing/backup claim.
8. Research handoff: no model scheduler implemented by this change. Notes retain full 200 epochs, identity/numerical failure pause, complete-dataset-only quality assessment and the user's stricter 18:23:51 deadline; research acceptance/cost scheduling remains separate.

Protected final evidence reports 640 pre-existing research/dataset/archive files unchanged and zero formal T002 runs. This is a bounded prior inventory, not proof about every possible new file; end-to-end tests separately verify no research run/state mutation. No research records or delegation pointer were read/written by this verification workflow itself.

## Checks

| Command or inspection | Result | Notes |
| --- | --- | --- |
| Local OpenSpec 1.14.3 status/apply instructions | all_done, 15/15 | Verified on final tasks |
| `node scratch/t002-tools/openspec-cli/node_modules/@fission-ai/openspec/bin/openspec.js validate repair-published-shuffle-budget --type change --strict --json --no-interactive` | PASS | valid=true, zero issues, rerun after fixes |
| `.venv-pinned/Scripts/python.exe -B openspec/changes/repair-published-shuffle-budget/run_tests.py baseline --label independent-baseline-20261020-01` | PASS | 287 tests, 0 failures/errors, 8 skips; 439.547s harness |
| Same harness, `skeleton --label independent-skeleton-20261020-01` | PASS | 134 tests, 0 failures/errors, 4 skips; 831.281s harness / 828.638s unittest |
| Independent 18-member saved-check loop | PASS | Own exclusive external reports; current generator equality; original report/checksum hashes match; all 38 member files unchanged each; 9 matching pairs, 360 timings, 94.969s |
| Small independent no-model empty-context fixture | PASS | region context0 measured 0.0053s, context1 exactly 0.0s; build_model forbidden |
| Real Windows watchdog with five-second sleep child, max_seconds=1 | Expected timeout/error evidence | Trigger 1.094s; denied termination disclosed, child joined after natural exit |
| Scoped static source and tests | PASS | Ordered proposals, finite work, source identity, strict versioning, degree/locality, no fallback, independent training, repeat/recompute thresholds and scientific non-goals traced |

All Python commands ran with PYTHONUTF8=1. Full suites used BLAS threads=1 and the pinned Python 3.11.17 runtime (torch2.14.1+cpu, numpy1.26.4, pandas2.2.3, pyarrow17.0.0). Baseline ran before skeleton; skeleton overlapped development graph-only readiness, never a model-cost measurement. Expected negative-test CLI messages are not suite failures.

## Requirement Coverage

Every normative requirement and all 12 scenarios from the delta spec are enumerated below.

| Requirement / scenario | Implementation and independent evidence | Result |
| --- | --- | --- |
| Finite versioned work, unchanged 10E target; larger finite budget completes former failure | protocol/shuffle; scalar/backend tests; all18 artifacts exact 10E and <=500E. r2 seed0 context12 completes 224080 accepted in2581117 attempts, above old2240800 ceiling, below11204000 | PASS |
| Sequential semantics under buffered proposals | test_shuffle_v2 independent scalar oracle across 17-edge non-power-of-two fixture, three seeds, batch sizes1/7/4096, set/dense; counters/final canonical edges exact | PASS |
| Decisive failure/progress identities and rejection evidence; budget exhaustion | ShuffleV2Test failure accounting/previous context/progress tests and test_shuffle failure attribution; runner/prepared terminal branches inspected; no training on graph failure | PASS |
| User interruption preserves latest recovery point and refuses partial artifact | PreparedTest failure/interruption, saved loader non-success rejection; catchable terminal status and hard-kill unfinished marker source trace; ReadinessTest stop-scheduling/cleanup cases | PASS |
| Graph-only preparation and complete canonical evidence; prepare before models | Fresh CLI test and no-build-model fixture tests, exclusive collision/unsafe destination rejection; all18 graph-only artifacts have arrays/audits/provenance/checksums/status; no training output | PASS |
| Saved corruption fails read-only checking, one external exclusive report | PreparedTest count/hash/version/seed/status/numeric/missing/provenance/timing corruption; checks report exclusivity/path tests and static protection trace; all18 independent checks immutable | PASS |
| Reuse identity checks and independent model-seed/repetition training | config/runner/prepared; mismatch test forbids train/regeneration and rejects self/graph option; same-condition reuse external path remains metadata; 200-epoch independent fixture fits | PASS |
| Mismatch cannot regenerate or fall back | PreparedTest keys/source/dataset/seed/current-generator mismatch branches and runner mismatch test with training/shuffle forbidden | PASS |
| Self-contained saved evidence after external directory unavailable | PreparedTest fresh/reused independent fits, repeat comparison under1e-6, renamed preparation then recompute under1e-12; full end-to-end saved-only checks prohibit source reads/model forward | PASS |
| Strict legacy/new version dispatch | Genuine scalar v1 audit/full saved fixture recomputation, omitted batch accepted, explicit contradictory batch rejected; v2 factors/batch checks; unknown versions/budgets fail | PASS |
| Complete published preflight | Matrix06 18 artifacts, datasets r0/region/r2 × seeds0/1/2 × independent a/b, nine identical canonical pairs, 360 context timings, counters/degrees/locality/overlap/hashes independently checked | PASS |
| Partial matrix cannot authorize successful handoff | ReadinessTest first failure/elapsed/idle/cleanup stops scheduling and preserves paused/incomplete metadata; source never schedules models; historical incomplete matrix04/05 not substituted for final06 | PASS |

Additional proposal/design/task constraints: optional dense backend stayed bounded and unselected after slower measured trials; real Windows atomic sharing lock recovers within finite retry while permanent failure preserves old/new bytes; complete torch suffix retained, exact reset/isolated/empty equality and fixed1e-6/1e-12 thresholds preserved; baseline no-torch all-schema CLI smoke actually executed; no epochs/GRU/Adam/masks/benefit gates changed; source/runtime identities retained; no formal matrix or research scheduling added.

## Findings

### V-001: Saved graph checks accept missing mandatory generation provenance

- Category: implementation
- Severity: medium
- Requirement: specs/graph-value-skeleton/spec.md, “Shuffled graphs can be prepared and checked without model training” requires complete generation provenance; “Saved artifact corruption fails read-only checking” requires missing/inconsistent identities to fail. Design decisions 3/4 require generator/environment provenance and rejection of unknown/incompatible identities.
- Evidence: prepared.py load hashes source.json and environment.json but never parses/validates their identities; provenance.generator is only compared under require_current_generator=True. In independent small-fixture saved-read checks, source.json={}, environment.json={}, and provenance.generator={} each returned status=ok when their byte checksums matched. The public check path calls load without require_current_generator.
- Expected: Artifacts lacking mandatory source/runtime/generator identity fields fail read-only checking with a decisive reason, even when the checksum manifest accurately records those incomplete bytes. Saved checking may validate recorded supported identities without requiring the current generator or proving authenticity.
- Actual: Empty identity records pass as completed, valid prepared artifacts. Empty source/environment also bypass the reuse path's current-generator comparison.
- Repair guidance: Validate the required saved provenance schema and consistency among generator/source/environment records before accepting a prepared artifact. Preserve saved-only operation and recognized historical-version checking; do not introduce an unsupported authenticity guarantee or demand current-source equality for ordinary saved checks.
- Acceptance checks: Small graph-only fixtures with each missing/empty mandatory identity record, matching updated checksums, must fail check-shuffle without input mutation. An intact artifact must still pass; compatible reuse and historical-version checks must retain their documented behavior.
- Repair status: verified-resolved
- Repair notes: prepared._validate_generation_records now requires generator source hashes, scientific protocol identity, Python/package metadata and agreement with saved source/environment records; no current-source read. Added eight actual saved-byte mutation cases with matching checksums and input immutability assertions. verification-fix-focused.json/log: 12 tests pass, 31.235 s; intact saved check also passes. Full suites and independent confirmation remain pending.
- Reverification notes: Independently reran the complete 134-test skeleton suite. Actual saved-byte empty/missing/inconsistent provenance cases now fail with decisive generation-provenance reasons and unchanged inputs; intact fixture and all 18 published artifacts pass saved checks. Resolved.

### V-002: Legacy version dispatch ignores contradictory explicit batch identities

- Category: implementation
- Severity: low
- Requirement: Design decisions 1/5 and task 2.3 require explicit recognized version contracts and strict saved-version dispatch; unsupported or contradictory generation identities must fail without relabeling historical inputs.
- Evidence: checks.py validate_shuffle_audit checks proposal_batch_size only when the selected contract value is greater than one. Independent small-fixture v1 scalar generation followed by current validation accepted proposal_batch_size=4096, -7 and "bogus" with problems=[]. Historical omission and the correct explicit value 1 also passed.
- Expected: Genuine historical v1 evidence may omit the field; an explicitly recorded batch identity must be the exact supported integer 1 for v1, and 4096 for v2. Invalid/contradictory supplied identities fail.
- Actual: Any explicit v1 batch identity is ignored, including nonnumeric and impossible values.
- Repair guidance: Preserve legacy missing-field compatibility while validating a present v1 field against its recognized contract; keep strict exact-integer identity semantics for both supported versions.
- Acceptance checks: Validate untouched v1 without the field and v1 with integer 1 successfully; reject explicit v1 4096, -7, string, boolean or float values. Confirm existing v2 batch validation and unknown-version rejection.
- Repair status: verified-resolved
- Repair notes: checks.validate_shuffle_audit validates any explicit batch field as an exact integer matching its version; legacy omission remains allowed. Extended scalar-v1 regression with explicit 1 accepted and 4096/-7/string/bool/float rejected. Same focused 12-test run passes; full independent verification remains pending.
- Reverification notes: Independent complete skeleton suite passes genuine scalar-v1 omission/integer-1 success and explicit contradictory value rejection, plus full 200-epoch v1-contract saved-run recomputation under current defaults with input bytes unchanged. Resolved.

### V-003: Published readiness omits context-level elapsed timings

- Category: implementation
- Severity: medium
- Requirement: The published shuffle readiness requirement states that reports SHALL retain per-context invariants, attempts, accepted/rejection counts, edge change/overlap, timings and source/result identities.
- Evidence: repair-shuffle-v2-20261020-05/graphs/r2-shuffle0-a/measurements.json records demand_read=0.8518991s, graph_read=1.6459800s, shuffle=32.8004008s and total=44.0232126s, but no per-context timings. Its 52 successful shuffle-audit context records omit elapsed time. shuffle.py emits context elapsed_seconds in progress snapshots, while prepared.prepare overwrites progress.json at every callback; the final boundary payload does not preserve each context's elapsed time. Thus the completed manifest cannot recover context-level measured costs.
- Expected: The complete graph-only readiness report retains measured elapsed time for every context with a disclosed method; measurements remain execution metadata outside semantic graph identity.
- Actual: Only whole-stage/whole-worker costs survive a successful preparation.
- Repair guidance: Persist genuine timing measurements already emitted by each context and check their complete context inventory/finite nonnegative values. Do not synthesize historical measured values or add wallclock measurements to deterministic shuffle identity. Retain matrix 05 and produce fresh readiness evidence for timing-complete artifacts.
- Acceptance checks: Fixtures cover nonempty and empty contexts, valid complete timing inventory and missing/invalid records; all 18 fresh published executions retain measured context timings and pass read-only checks with matching regeneration graph hashes.
- Repair status: verified-resolved
- Repair notes: prepared.prepare now collects existing swap-progress elapsed values per context into measurements.context_timings (empty contexts zero swap work) outside deterministic audit/identity; load requires complete finite nonnegative measurements matching audit contexts. Added missing/negative/nonfinite mutation tests and identity separation assertions. verification-fix-timings.json/log: four focused tests pass, 34.781 s. Matrix06 launched fresh for actual measurements; matrix05 is retained without backfilling. Independent whole-change review remains pending.
- Reverification notes: Independent complete skeleton suite passes timing metadata and missing/negative/nonfinite rejection tests. Independently checked all 18 matrix06 artifacts: 360 valid timing records, nine matching result pairs, every input byte unchanged. Additional no-model region fixture verified a nonempty context measured 0.0053s and an empty context recorded exactly 0.0s; timing absent from scientific audit/identity. Matrix05 retained without invented timing. Resolved.
