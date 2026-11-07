# Implementation Verification

- Change: add-occupation-skill-graph-audit
- Schema: spec-driven
- Verdict: FAIL
- Verified at: 2026-11-07T12:16:19Z
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark`
- Verified revision: `67c25073460a7e90bae2e9b8de3dd73de602196b`; clean input worktree. Only verifier-owned report/state files were added by this workflow.

## Summary

Four confirmed implementation deviations remain: lazy mapping exposes positional indices as skill identities; loss of RSS monitoring permits successful completion and can invalidate the artifact inventory; a symlinked scratch root bypasses protected-output checks; saved-only checking accepts missing code/environment provenance and an empty source record. All are pending. Do not archive this implementation yet.

Strict OpenSpec validation and all three suites pass: 80 new fixture tests, 287 no-graph tests (2 skipped), and 153 published-graph tests (2 skipped). Independent score oracles and held-out/row-order/precision probes also pass. Passing tests do not cover the four defects below. No published-data construction, research-purpose execution, formal prediction experiment, dataset edit, research-record update, commit or push was performed.

Full published-scale runtime/RSS, Linux/Windows native monitoring and cross-platform near-tie behavior remain unmeasured. These are disclosed limits, not additional confirmed defects or a claim of research acceptance.

## Verification Basis

| Path or scope | Revision / content fingerprint / file inventory |
| ------------- | ---------------------------------------------- |
| `proposal.md`, `design.md`, `tasks.md`, `specs/occupation-skill-graph/spec.md` in this change | Read current files returned by `openspec instructions apply`; all 14 checked tasks treated as claims |
| `research/phases/P02/t009-graph-protocol.md` | Read-only controlling protocol, `P2-occupation-skill-graph-v1` |
| `benchmark/occupation_skill_graph/`, reused no-graph utilities, dependency pins, README and old compatibility packages | Current committed implementation and tests inspected; inventory includes all repository inputs |
| `implementation-notes.md` | Read in full; apply-owned claims, not independent acceptance evidence |
| `verification-state.json` | Script-generated full repository inventory: 2,436 files; SHA-256 `550ba4c8c10f163640e4532b5e129b8225b3b8a26b75e3a07f0ce4ffc261c1b0` |
| Execution environment | macOS arm64; conda `job-sdf-baseline`; Python 3.11.17, NumPy 1.26.4, pandas 2.2.3, PyArrow 17.0.0 |

Full verification, with no reused prior independent evidence: no previous verification report or snapshot exists. The initial baseline comparison returned exit 2 solely for the absent legacy state; this does not block establishing the baseline. Planning and implementation share one root. No explicit exclusions; the script automatically excludes workflow handoff/report/state files and uses Git tracked plus non-ignored untracked files. Ignored scratch/cache/test outputs are outside this inventory.

Commands executed from the repository root:

```sh
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py capture --root /Users/watuji/da_chuang/repos/benchmark --output /tmp/osg-verify-before.json
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py compare openspec/changes/add-occupation-skill-graph-audit/verification-state.json /tmp/osg-verify-before.json
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py capture --root /Users/watuji/da_chuang/repos/benchmark --output /tmp/osg-verify-after.json
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py compare /tmp/osg-verify-before.json /tmp/osg-verify-after.json
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py capture --root /Users/watuji/da_chuang/repos/benchmark --output /tmp/osg-verify-final.json
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py compare /tmp/osg-verify-before.json /tmp/osg-verify-final.json
```

Before/after and post-suite final comparisons: exit 0, `changed: false`; all generated snapshots have the SHA-256 above. The final generated snapshot is copied to the change's `verification-state.json`. The inventory records inputs, not proof that every inventoried file passed a check. Temporary logs are convenience evidence only; decisive observations and reproductions are recorded here.

## Apply Handoff Review

The handoff correctly identifies the change and implementation project. Its revision statement is stale: implementation originally described as dirty at `af2756f` is now committed in `67c2507`. Inspection of `git diff af2756f..HEAD` locates the new package and README changes; it confirms the old three benchmark packages have no implementation changes.

| Reminder | Disposition |
| -------- | ----------- |
| No published construction, research runs, dataset/history changes or research acceptance | Confirmed for this verification: fixtures only; worktree inventory unchanged |
| Largest apply measurement is 52 x 300; full 2,335-skill costs unknown | Retained limitation; no extrapolated budget sufficiency claim |
| RSS is sampled; macOS native probe used; other native branches unexercised | Sampled units/scope confirmed; preflight, timeout and over-budget tests pass. Post-preflight monitor failure is covered by V-002 |
| Cross-platform bitwise equality is not claimed | Applicable limitation; exact-tie fixture behavior and current-environment reproducibility confirmed |
| Trend eligibility is descriptive; unknown remains unknown; opposing signs retained | Confirmed by `test_trends.py`, including explicit ±1 correlations, null reasons, common zeros and unchanged graph hashes |
| Scores are priors; no freezing, predictive benefit or T010 integration | Confirmed in README, protocol, report fields and code inspection |
| Checker shares pure functions; hand-calculated tests are its independent oracle | Confirmed; extra independent 19-skill oracle agrees on 111 Jaccard and 109 cosine union edges. Source removal succeeds with unchanged input bytes on an ordinary build |
| Status/progress intentionally excluded from immutable inventory | Acceptable mutable-record design: terminal status checked directly; incomplete status rejected. A different supervisor-record ordering problem is covered by V-002 |
| Published region IDs 0..6; full published targets not loaded | Assertion code inspected and identity-range behavior checked; actual published target preflight remains later research work |
| Research purpose requires separate execution; fixture injection refused | Rejection branches and path resolver tested; no research execution invoked |

## Checks

All evidence below was obtained this round.

| Command or inspection | Result | Notes |
| --------------------- | ------ | ----- |
| `openspec status --change add-occupation-skill-graph-audit --json` and `openspec instructions apply --change add-occupation-skill-graph-audit --json` | PASS | Local repo, `spec-driven`, required artifacts present, 14/14 tasks checked |
| `openspec validate add-occupation-skill-graph-audit --type change --strict --json --no-interactive` | PASS | Valid, no issues |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/occupation_skill_graph/tests -v` | PASS | 80 tests, 4.711 s; real Parquet, public CLI build/check, arithmetic, invalid data, budgets, collisions, corrupt scientific payloads and source removal |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/nograph_baseline/tests` | PASS | 287 tests, 47.059 s; 2 skipped |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/graph_value_skeleton/tests` | PASS | 153 tests, 194.705 s; 2 skipped |
| `git diff af2756f46470f3ab5803e00cc8fedb53c27e5adc..HEAD -- benchmark/nograph_baseline benchmark/graph_value_skeleton benchmark/graph_method` | PASS | Empty; compares implementation commits, not merely an already-clean worktree |
| Independent dense small oracle, seed 743, 19 skills x 5 occupations | PASS | Plain set Jaccard, direct dot/norm cosine, independent Python sorting/union agree with builder edges and scores within 1e-12; 111/109 edges |
| Combined held-out perturbation and row permutation | PASS | Real Parquet fixtures with held-out 0 vs 999 and row seed 17: training identity, both graph payload hashes, numerical structural summaries and trend array hashes identical; source-file hashes differ. Only file-identity metadata excluded from numerical summary comparison |
| Native-precision fixture with demand `2**24+1` | PASS | Loader preserves 16,777,217.0; float32 would yield 16,777,216.0 |
| Ordinary fixture build, removal of all four source Parquets, saved-only check | PASS | `status: ok`, `input_modified: false`; numeric arrays load without pickle |
| Non-dense directed expansion probe | FAIL | V-001: returns indices 0/1/2 instead of IDs 1/4/7 |
| RSS monitor available once, unsupported thereafter, actual isolated fixture worker | FAIL | V-002: exit 0, succeeded, 57 probe calls, sampled peak 0; final supervisor says completed; saved-only check fails supervisor checksum |
| Scratch-root symlink into protected research directory of temporary checkout | FAIL | V-003: resolver accepts `checkout/research/runs` |
| Remove mandatory provenance from otherwise valid saved fixture, update inventory consistently | FAIL | V-004: checker accepts empty code/environment records, missing `environment.txt`, and then empty `artifacts/source.json` |

PyArrow emitted sandbox-denied CPU-cache discovery warnings; Parquet operations and tests completed. This does not explain or excuse the reproduced implementation defects.

## Requirement Coverage

Requirement numbers below follow specification order (R1–R9); scenario names are verbatim. Paths are relative to `benchmark/occupation_skill_graph/` unless specified otherwise.

| Requirement / scenario | Evidence | Result |
| ---------------------- | -------- | ------ |
| R1: Construction uses only canonical occupational training observations / Held-out values cannot affect graphs | `data.py` projects keys + 27 months; `test_data.CanonicalLoadingTests`; extra full scientific-payload comparison above | PASS |
| R1 / Row order cannot affect semantics | Canonical key sorting; real shuffled non-dense Parquets; graph, structure and trend identities compared | PASS |
| R1 / Invalid source fails before construction | `ValidationTests`: duplicate/fractional keys, incomplete grid, missing/extra month, negative/NaN values; `execute_build` loads source before candidate construction; published-range and unsupported source/mode/fold/version rejection inspected/exercised | PASS |
| R2: Two explicit relation scores preserve inactive skills / Hand-computable candidate differences | `scores.py`; `HandScoreTests`: 1/2 vs 1/sqrt(2), disjoint supports, inactive skill, symmetry and scaling; independent dense oracle | PASS |
| R3: Sparsification is deterministic and retains explicit weights / Ties and asymmetric selections | `SparsificationTests`: 13 tied skills, ascending canonical indices correspond to sorted numeric IDs, one-sided union, no loops/duplicates/zero edges, union degree >10; independent oracle | PASS |
| R3 / Empty relations remain explicit | All-zero and disjoint fixture tests; complete node table, empty edge arrays, null summaries | PASS |
| R4: A shared relation maps within target contexts without changing population / Same graph in distinct contexts | Key-only loading/population checks pass; counts and scores preserved; `MappedContext.directed_pairs()` fails actual non-dense node identity probe | FAIL, V-001 |
| R4 / Population mismatch is explicit | `test_mapping.py`: missing/extra/duplicate skill and incomplete grids fail; value projection limited to keys | PASS |
| R5: Structural diagnostics expose coverage and score degeneracy / Dense equal supports are visible | `test_structure.py`: 78 full-score pairs for 13 skills, cutoff ties, components, isolates, all-skill/active denominators, overlap and zero-variance reasons; summary paths inspected | PASS |
| R6: Trends are diagnostic and insufficient histories remain unknown / Sparse and constant histories | `test_trends.py`: reason priority, per-context reason codes, null statistics and unchanged graph bytes; 27-month input/26 differences inspected | PASS |
| R6 / Occupational heterogeneity | Explicit +1/-1 correlation fixture, independent expected counts/min/max/common-zero fraction; unknown contexts not counted as zero/negative | PASS |
| R7: CPU costs and incomplete work are observable and bounded / Resource limit or interruption | Timeout, over-RSS, cancellation, nonzero worker, no-retry and post-stage failure tests pass; construction/mapping/trend durations, byte RSS scope and dimensions saved. Monitoring loss remains unbounded while success is published | FAIL, V-002 |
| R8: Artifacts are exclusive self-contained and checkable without source data / Self-contained saved check | Ordinary source-removed fixture succeeds without modifying bytes; fixture CLI and numeric rederivation pass. Mandatory provenance omissions accepted; degraded-monitor artifact gets invalid inventory | FAIL, V-002 and V-004 |
| R8 / Corruption or collision | Existing tests reject corrupt score/count/key/incomplete status, obey 1e-12 tolerance and refuse overwrites/internal report paths. Missing environment/code/source evidence is not semantically rejected after valid re-inventory | FAIL, V-004 |
| R9: Development and research acceptance remain separate / Fixture readiness | Public CLI fixture build/check, old help/imports and compatibility suites; README and constraints inspected; no research run or published construction invoked | PASS for exercised fixture workflow; research acceptance not performed |
| R9 / Unsafe output override | Direct/traversal and ordinary alias cases pass existing tests; scratch-root alias itself bypasses protected-directory exclusion | FAIL, V-003 |

Proposal/design/task review found no separate planning contradiction. Isolated package, CPU arithmetic, fixed protocol, deterministic top-10 union, shared trend computation, lazy storage, no old pipeline changes and separate later research acceptance are implemented. Task 3.1 is incomplete at actual identity expansion; 4.2 at continued enforcement; 4.3 at scratch-root symlink handling; 4.4 at provenance completeness. Tasks remain untouched by verification.

## Findings

### V-001: Lazy edge expansion emits positional indices as non-dense skill IDs

- Category: implementation
- Severity: medium
- Requirement: R4, “Same graph in distinct contexts”; design decision 2 and task 3.1 require exact non-dense identities.
- Evidence: `benchmark/occupation_skill_graph/mapping.py:55` uses `self.edges` directly in context-qualified pairs; `source_skills` is available but unused for conversion. With context 2, skills `[1,4,7]` and indexed edges `[[0,1],[1,2]]`, observed pairs are `[[2,0,2,1],[2,1,2,2],[2,1,2,0],[2,2,2,1]]`. The saved checker checks expansion counts, not these endpoint identities (`checks.py:498`). Existing mapping test checks context columns only.
- Expected: `[[2,1,2,4],[2,4,2,7],[2,4,2,1],[2,7,2,4]]`, unchanged scores and both directions, with every endpoint in target keys.
- Actual: Endpoint 0 is absent from the target; other endpoints refer to different skills. For empty edges the same API returns shape `(0,2)` instead of its nonempty four-column context-qualified schema.
- Repair guidance: Translate shared positional endpoints through the canonical skill table when exposing context-qualified node identities, preserve aligned scores/directions and a consistent empty schema; check endpoint identities as well as counts.
- Acceptance checks: Reproduction A below returns expected ID pairs; verify each pair is in canonical target keys for multiple non-dense contexts, scores align, no cross-context pair exists, and empty expansion has four columns. Rerun mapping/checker/CLI fixtures.
- Repair status: addressed-awaiting-verification
- Repair notes: Reproduced before edits with the strengthened mapping tests: non-dense endpoints were positional IDs and empty expansion had two columns. Updated benchmark/occupation_skill_graph/mapping.py to translate indices through source_skills and return an empty (0,4) schema; checks.py now validates expanded endpoint identities, contexts and aligned scores. test_mapping.py asserts exact pairs and target-key membership in both non-dense contexts, both directions, score order and empty schema. Original reproduction A now returns [[2,1,2,4],[2,4,2,7],[2,4,2,1],[2,7,2,4]] and (0,4). Focused mapping/checker/CLI/runner/supervisor checks passed (55 tests); final command conda run --no-capture-output -n job-sdf-baseline python -m unittest discover -s benchmark/occupation_skill_graph/tests -v passed all 94 tests in 7.637 s, including checker/CLI fixtures and old-interface compatibility probes. Independent reverification remains required.
- Reverification notes: Independently reproduced this round; published dense zero-based IDs mask the defect.

### V-002: Monitor loss permits success and mutates an inventoried supervisor record

- Category: implementation
- Severity: medium
- Requirement: R7 monitored RSS enforcement and non-success failure evidence; R8 self-consistent saved evidence; design decisions 5–6; task 4.2.
- Evidence: `supervisor.py:192` writes `monitor_degraded` but continues; `supervisor.py:225` overwrites that record with `completed`. Reproduction B gives the preflight one valid measurement, then returns unsupported for every worker sample. An actual isolated fixture build returned 0 with `state: succeeded`, 57 probe calls and `observed_peak_rss_bytes: 0`. `artifacts/supervisor.json` ended with `status: completed`. The worker's manifest had already inventoried an intermediate supervisor record; the subsequent saved-only check failed its checksum (`4758e080…` recorded vs `c17a8803…` final in this run).
- Expected: If RSS enforcement becomes unavailable while a worker is alive, preserve an explicit non-success monitor failure and completed-stage evidence; no completed artifact may contain an inventory invalidated by later supervisor writes. A process that has already exited need not be measurable.
- Actual: Computation can run to success without any worker RSS observation; degraded evidence is overwritten. The successful result can immediately fail saved-only checking.
- Repair guidance: Handle loss of monitoring explicitly for a live worker and preserve the reason in the terminal evidence. Coordinate supervisor-record mutability and inventory publication so successful outputs remain checkable without edits.
- Acceptance checks: Reproduction B must produce nonzero/non-success with a durable monitoring-failure reason and no completed manifest. Exercise both unsupported and unavailable samples after preflight, distinguish exited-worker races, retain completed stages, and verify an ordinary successful supervised fixture passes its saved check.
- Repair status: addressed-awaiting-verification
- Repair notes: Reproduced before edits using actual isolated fixture workers: both unsupported and unavailable post-preflight probes returned successful builds. Updated supervisor.py to stop a live worker on any missing RSS sample, recheck process exit to distinguish exit races, and retain rss_monitor_failure plus the measurement and completed-stage evidence in terminal status/supervisor records. Termination/cancellation removes any worker-published completion manifest. artifacts.py excludes the mutable supervisor record from immutable inventory; checks.py directly requires a present supervisor record to show successful completion. test_supervisor.py adds real-worker coverage for both monitor failure statuses, saved completed source evidence, an exited-worker race, and a normal supervised build followed by saved-only checking. Original reproduction B now exits 1 after two probes with terminated/rss_monitor_failure and a durable injected-loss reason; its saved check rejects the non-success state. Focused 55-test run and final 94-test suite passed; ordinary supervised and exit-race outputs pass their saved checks. No independent resolution claimed.
- Reverification notes: Independently reproduced with a real fixture worker and injected monitor, not a mocked build result.

### V-003: A symlinked scratch root authorizes development output inside research

- Category: implementation
- Severity: medium
- Requirement: R9 “Unsafe output override”; design decision 5; task 4.3.
- Evidence: `paths.py:98` resolves `scratch` and treats everything below its target as allowed, before applying any independent protected-directory exclusion. Reproduction C constructs only a disposable checkout: `scratch -> research`; resolving development output `scratch/runs` returns `checkout/research/runs` without raising. The resolved result is demonstrably inside protected research.
- Expected: Reject a development output resolving into source/research/dataset/history even when the scratch root itself is an alias and the checkout is under temporary storage; reject before reservation.
- Actual: The protected destination is accepted as scratch. This affects both an override below that alias and the default development root.
- Repair guidance: Apply protected destination rules independently of scratch-root alias resolution; keep legitimate scratch and external temporary output working.
- Acceptance checks: Reproduction C must raise `PathError`; verify default and explicit output below scratch aliases to research/dataset/source/history, plus existing direct/traversal/symlink and temporary-checkout cases. Do not create probes inside actual project research directories.
- Repair status: addressed-awaiting-verification
- Repair notes: Reproduced before edits in disposable temporary checkouts: scratch aliases to research, dataset, benchmark/source and history were accepted. Updated paths.py to reject protected resolved destinations independently of scratch resolution and to require an actual scratch subtree for outputs inside the checkout. test_cli.py covers both default and explicit roots below aliases to research/dataset/benchmark/source/history, asserts no protected output was reserved, and retains ordinary scratch, external temporary, direct/traversal/symlink and temporary-checkout checks. Original reproduction C now raises PathError for the protected research destination (expected nonzero). Focused 55-test run and final 94-test suite, including public CLI fixtures, passed. Only fake checkouts were used for protected-directory probes.
- Reverification notes: Confirmed entirely in a temporary fake checkout; no project symlink or research output was created.

### V-004: Saved-only checking accepts missing reproducibility provenance

- Category: implementation
- Severity: medium
- Requirement: R8 mandatory code baseline/execution differences, environment, identities and rejection of missing/contradictory/incomplete evidence; design decision 6; task 4.4.
- Evidence: `checks.py:645`/`layout.required_payload_files()` do not require the environment snapshot; after parsing `provenance.json`, the checker validates protocol and selected training identity fields but not code/environment completeness. The required `artifacts/source.json` is inventoried but never semantically read. Reproduction D starts with an independently checked valid fixture; clears `provenance.code_source` and `.environment`, deletes `environment.txt` and its inventory entry, updates only changed-file checksums, and gets `status: ok`, `errors: []`. Replacing `artifacts/source.json` with `{}` and updating its checksum also returns `ok`.
- Expected: Reject missing mandatory execution/source identity and environment evidence, and reject contradictions among saved identity records, even when the checksum inventory is internally consistent. This requires no source Parquet reopening or authentication of historical claims.
- Actual: The checker reports success after the artifact loses its code identity, environment and source identity record. Checksums alone satisfy these parts of the contract.
- Repair guidance: Define and enforce required saved provenance fields/files, cross-check redundant saved identities and recoverability declarations, and keep checking source-free/read-only. Do not require the current working environment or original source files to match historical execution.
- Acceptance checks: Reproduction D mutations must fail with specific missing/contradictory-provenance errors; an intact source-removed artifact must continue to pass; existing numerical tolerance and input-preservation cases must remain valid.
- Repair status: addressed-awaiting-verification
- Repair notes: Reproduced before edits with independently re-inventoried mutations: missing code/environment provenance or environment.txt, empty source.json, contradictory baseline/environment/target identities and absent recovery declarations were accepted. Updated checks.py to require environment.txt, code-source.json and git-diff.patch; validate mandatory provenance fields; compare redundant command/source/code/target identities; check baseline availability/references, scoped recovery evidence and patch byte counts; and validate saved dependency/thread/protocol facts against the environment snapshot. Historical claims are checked solely against saved records, without requiring live environment/source/Git-baseline matches. test_checks.py adds eight independently re-inventoried corruption cases with specific provenance errors and input-byte preservation checks, using a real repository code capture for the golden artifact. Original reproduction D now passes the intact source-removed artifact and rejects both mutations; separate regression cases isolate the empty source record and missing code/environment objects. Existing 1e-13 acceptance, 1e-9 rejection and source-removal cases pass. Focused 55-test run and final 94-test suite passed; openspec validate add-occupation-skill-graph-audit --type change --strict --json --no-interactive passed. Verdict remains owned by independent verification.
- Reverification notes: Independently reproduced after first confirming the intact artifact passes with every source Parquet removed. These are missing saved evidence checks, not a demand for a forgery-proof artifact format.

## Reproduction Commands

Run from the repository root in the pinned CPU environment. The snippets use only disposable fixtures; they do not write implementation/tests or actual research outputs. The observations above are preserved here because temporary directories are deleted after each probe.

A — non-dense endpoint identities:

```sh
conda run --no-capture-output -n job-sdf-baseline python - <<'PY'
import numpy as np
from benchmark.occupation_skill_graph import mapping
from benchmark.occupation_skill_graph.tests import fixtures as fx
target = fx.target_fixture('r2', [2, 5], [1, 4, 7])
mapped = next(mapping.iter_context_edges(target, np.array([[0,1],[1,2]]), np.array([.5,.25])))
print(mapped.directed_pairs().tolist())
print(next(mapping.iter_context_edges(target, np.empty((0,2), dtype=np.int64), np.empty(0))).directed_pairs().shape)
PY
```

B — post-preflight monitor loss and saved inventory consistency:

```sh
conda run --no-capture-output -n job-sdf-baseline python - <<'PY'
import json, tempfile
from pathlib import Path
from benchmark.occupation_skill_graph import supervisor, checks
from benchmark.occupation_skill_graph.tests import fixtures as fx
repo = Path.cwd()
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    spec = fx.build_spec(root, fixture=fx.standard_fixture(root/'data'), monitor_interval_seconds=.01)
    spec.repo_root = str(repo)
    calls = [0]
    def probe(pid):
        calls[0] += 1
        if calls[0] == 1:
            return {'status':'ok', 'bytes':1024, 'method':'fixture'}
        return {'status':'unsupported', 'bytes':None, 'reason':'injected loss after preflight'}
    print('exit', supervisor.launch(spec, probe=probe), 'calls', calls[0])
    run = spec.run_directory
    print(json.loads((run/'artifacts/status.json').read_text())['state'])
    print(json.loads((run/'artifacts/supervisor.json').read_text()))
    checked = checks.check_artifact(run, root/'check.json', repo_root=repo, command=['probe'])
    print(checked['status'], checked['report']['errors'])
PY
```

C — protected destination via scratch-root symlink:

```sh
conda run --no-capture-output -n job-sdf-baseline python - <<'PY'
import tempfile
from pathlib import Path
from benchmark.occupation_skill_graph import paths
with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp).resolve()/'checkout'
    repo.mkdir()
    (repo/'research').mkdir()
    (repo/'scratch').symlink_to(repo/'research', target_is_directory=True)
    result = paths.resolve_output_root(purpose='development', output_root=repo/'scratch'/'runs', repo_root=repo)
    print(result, 'inside protected research:', result.is_relative_to(repo/'research'))
PY
```

D — missing saved provenance with a valid re-inventory:

```sh
conda run --no-capture-output -n job-sdf-baseline python - <<'PY'
import json, shutil, tempfile
from pathlib import Path
from benchmark.occupation_skill_graph import artifacts, checks, runner
from benchmark.occupation_skill_graph.tests import fixtures as fx
repo = Path.cwd()
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    spec = fx.build_spec(root, fixture=fx.standard_fixture(root/'data'))
    spec.repo_root = str(repo)
    runner.execute_build(spec)
    run = spec.run_directory
    shutil.rmtree(root/'data')
    def check(name):
        result = checks.check_artifact(run, root/(name+'.json'), repo_root=repo, command=['probe'])
        print(name, result['status'], result['report']['errors'])
    check('intact-source-removed')
    pp = run/'provenance.json'
    provenance = json.loads(pp.read_text())
    provenance['code_source'] = {}
    provenance['environment'] = {}
    pp.write_text(json.dumps(provenance))
    mp = run/'artifacts-sha256.json'
    manifest = json.loads(mp.read_text())
    (run/'environment.txt').unlink()
    del manifest['files']['environment.txt']
    manifest['files']['provenance.json'] = artifacts.sha256_file(pp)
    mp.write_text(json.dumps(manifest))
    check('missing-code-environment')
    sp = run/'artifacts/source.json'
    sp.write_text('{}')
    manifest['files']['artifacts/source.json'] = artifacts.sha256_file(sp)
    mp.write_text(json.dumps(manifest))
    check('empty-source-record')
PY
```

Next action: `$openspec-e13-fix-change add-occupation-skill-graph-audit`, then independent re-verification. This verdict applies only to the recorded input basis; it does not authorize archive or research acceptance.
