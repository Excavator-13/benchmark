# Implementation Verification

- Change: add-occupation-skill-graph-audit
- Schema: spec-driven
- Verdict: PASS
- Verified at: 2026-11-07T12:29:20Z
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark`
- Verified revision: `3039f9c1176ccfcfb156b6aafdf7a92456530a6d`; clean input worktree. This verification updates only this report and its generated state.

## Summary

Independent incremental verification passes. V-001 through V-004 are verified-resolved: non-dense target endpoints use actual skill IDs; monitoring loss stops a live worker and preserves failure evidence; scratch-root aliases cannot authorize protected output; saved-only checking rejects missing or contradictory provenance. No actionable findings remain.

Strict OpenSpec validation passes. All 94 occupation-skill graph fixture tests pass, and the four original independent reproductions now produce the required outcomes. Unaffected prior independent evidence remains applicable, including both old benchmark suites, the mathematical oracle, held-out isolation and source precision checks. This is software readiness evidence only; no published-data construction, research-purpose execution, formal prediction experiment, research-record modification, commit or push occurred.

Residual limits are unchanged: published-scale runtime/RSS, native Linux/Windows monitoring and cross-platform near-tie behavior remain unmeasured. Sampled RSS is not an OS allocation cap. Research acceptance, real-data audit and T010 integration remain separate actions.

## Verification Basis

| Path or scope | Revision / content fingerprint / file inventory |
| ------------- | ---------------------------------------------- |
| Current proposal, design, tasks and occupation-skill-graph spec | Every context file returned by OpenSpec read again; planning unchanged from prior independent verification |
| Protocol, README, dependency/configuration files, data/scoring/structure/trend implementations | Unchanged in script-generated input comparison; prior behavior and conditions still applicable |
| Changed implementation | `benchmark/occupation_skill_graph/{artifacts,checks,mapping,paths,supervisor}.py`; diff from prior verified revision inspected |
| Changed tests | `benchmark/occupation_skill_graph/tests/test_{checks,cli,mapping,supervisor}.py`; new assertions inspected, not treated as proof until executed |
| Apply handoff and repair notes | `implementation-notes.md` read again; all four repair-owned notes in this report preserved verbatim |
| Saved previous state | SHA-256 `550ba4c8c10f163640e4532b5e129b8225b3b8a26b75e3a07f0ce4ffc261c1b0`; matched prior report before comparison |
| Current `verification-state.json` | 2,436-file generated inventory; SHA-256 `bc801a7e3816dfb0bced00be6c4a491fb7571795f98f2fd635bb8de2bda6fb8b` |
| Current execution environment | Darwin arm64; conda `job-sdf-baseline`; Python 3.11.17, NumPy 1.26.4, pandas 2.2.3, PyArrow 17.0.0, confirmed this round |

Incremental scope: the saved-state comparison returned exit 1 with exactly the nine implementation/test paths above modified, no additions/deletions and no scope change. The full package suite and original reproductions exercise all affected behavior, including end-to-end CLI builds, saved provenance checking, normal and failed supervision, mapping and path validation. Broader old suites were not rerun: their implementation, tests, dependencies, configuration and scientific behavior are unchanged; current old-interface probes also pass. Prior failures were retained until independently rechecked.

Planning and implementation share one root. No explicit exclusions. The script uses Git tracked plus non-ignored untracked files and automatically excludes workflow handoff/report/state files; ignored caches/scratch outputs are outside the inventory. Commands from repository root:

```sh
shasum -a 256 openspec/changes/add-occupation-skill-graph-audit/verification-state.json
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py capture --root /Users/watuji/da_chuang/repos/benchmark --output /tmp/osg-reverify-before.json
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py compare openspec/changes/add-occupation-skill-graph-audit/verification-state.json /tmp/osg-reverify-before.json
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py capture --root /Users/watuji/da_chuang/repos/benchmark --output /tmp/osg-reverify-after.json
python3 .agents/skills/openspec-e13-verify-change/scripts/verification_snapshot.py compare /tmp/osg-reverify-before.json /tmp/osg-reverify-after.json
```

Before/after comparison returned exit 0, `changed: false`; both current captures have the current SHA-256 above. Only after comparing the old baseline was the generated after-state copied into `verification-state.json`. The snapshot identifies inputs, not proof that every inventoried file was tested. Temporary logs are supplementary; decisive results and durable reproduction commands are recorded here.

## Apply Handoff Review

The handoff identifies this change and project correctly. Its dirty-worktree revision and 80-test counts are stale: current repair revision is `3039f9c`, and the independently rerun suite contains 94 tests. Repair details are in the preserved finding notes, not in an edited apply handoff.

| Reminder | Current disposition |
| -------- | ------------------- |
| Fixtures only; no published construction or research acceptance | Confirmed for this round; only temporary fixtures and verifier-owned files created |
| Largest apply measurement 52 x 300; full published-scale cost unknown | Retained limitation; no new performance sufficiency claim |
| Sampled RSS; macOS probe; other native platforms unexercised | Units/scope inspected; current timeout/RSS/cancellation, monitor-loss, completed-stage retention and exit-race tests pass; V-002 resolved |
| No cross-platform bitwise equality claim | Retained limitation; unchanged math and current exact-tie fixtures pass |
| Trend eligibility descriptive; unknowns and opposing signs retained | Current trend tests pass; prior independent numerical evidence retained |
| Scores are priors; no graph freeze, predictive benefit or T010 integration | README/protocol unchanged; report/CLI fixtures retain separate acceptance semantics |
| Checker shares pure functions; independent arithmetic oracle needed | Prior direct 19-skill oracle retained (111 Jaccard/109 cosine union edges); unchanged mathematics, current hand-score tests pass |
| Mutable status/progress excluded from immutable inventory | Still acceptable with direct status checking; repaired supervisor record is also mutable and directly checked when present; normal supervised saved check passes |
| Published region range 0..6; full target preflight not executed | Assertion behavior remains covered; actual published identity preflight stays later research work |
| Research purpose requires separate execution and rejects fixture injection | Current rejection/path/CLI tests pass; no research execution invoked |

## Checks

| Command or inspection | Result | Notes |
| --------------------- | ------ | ----- |
| `openspec status --change add-occupation-skill-graph-audit --json`; `openspec instructions apply --change add-occupation-skill-graph-audit --json` | PASS, this round | Local `spec-driven` change; artifacts present; 14/14 tasks checked, treated as claims |
| `openspec validate add-occupation-skill-graph-audit --type change --strict --json --no-interactive` | PASS, this round | Valid, no issues |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/occupation_skill_graph/tests -v` | PASS, this round | 94 tests, 7.258 s, exit 0; includes 14 additional tests and current old help/import compatibility probes |
| `git diff 67c25073460a7e90bae2e9b8de3dd73de602196b..HEAD -- README.md benchmark/nograph_baseline benchmark/graph_value_skeleton benchmark/graph_method` | PASS, this round | Empty; snapshot also confirms dependencies/configuration unchanged |
| Original reproduction A below | PASS, this round | Actual pairs `[[2,1,2,4],[2,4,2,7],[2,4,2,1],[2,7,2,4]]`; empty shape `(0,4)` |
| Original reproduction B below | PASS, this round | `launch` returns 1 after two probe calls; `terminated/rss_monitor_failure`, durable injected-loss reason; saved checker rejects terminated state |
| Original reproduction C below | PASS, this round | Expected exit 1 with `PathError`: destination resolves inside protected research; no directory reserved |
| Original reproduction D below | PASS, this round | Source-removed intact artifact `ok`; missing environment/code and subsequent mutation rejected for absent `environment.txt` |
| Isolated provenance regression cases in `test_checks.py` | PASS, this round | Separately confirms empty code/environment objects, missing snapshot, empty source, contradictory baseline/target/environment and missing recovery content are rejected with input bytes unchanged; avoids masking individual defects behind reproduction D's first omission |
| Supervision and output regression cases | PASS, this round | Unsupported and unavailable probes fail; completed source evidence retained; exited-worker race and ordinary successful supervised build both pass saved-only checking; aliases to research/dataset/benchmark/source/history rejected for explicit/default output |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/nograph_baseline/tests` | PASS, reused | Prior independent run at `67c2507`: 287 tests, 47.059 s, 2 skipped; unchanged relevant inputs/conditions |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/graph_value_skeleton/tests` | PASS, reused | Prior independent run at `67c2507`: 153 tests, 194.705 s, 2 skipped; unchanged relevant inputs/conditions |
| Independent dense small oracle, seed 743, 19 skills x 5 occupations | PASS, reused | Plain set Jaccard/direct dot-norm cosine and separate Python top-10 union agreed within 1e-12; 111/109 edges; score code unchanged |
| Combined held-out perturbation/row-order and native precision probes | PASS, reused | Real Parquet held-out 0 vs 999 with row seed 17 preserved training/graph/structure/trend identities apart from file metadata; 16,777,217.0 preserved instead of float32's 16,777,216.0; data/math unchanged |

PyArrow CPU-cache discovery warnings reflect the local sandbox; all required fixture checks completed. Original reproductions were rerun directly from the stored command bodies using `conda run --no-capture-output -n job-sdf-baseline python -c <body>`; C's exception is the required rejection, not a failed verification check.

## Requirement Coverage

R1–R9 follow specification order; scenario names are verbatim. All 16 scenarios retain sufficient current or still-applicable prior independent evidence. Paths are relative to `benchmark/occupation_skill_graph/` unless stated otherwise.

| Requirement / scenario | Evidence | Result |
| ---------------------- | -------- | ------ |
| R1: Construction uses only canonical occupational training observations / Held-out values cannot affect graphs | Current `test_data.CanonicalLoadingTests`, unchanged projection/27-month path; prior independent graph/structure/trend comparison and native-precision probe retained | PASS |
| R1 / Row order cannot affect semantics | Current canonical-loading/sparsification tests; prior real non-dense shuffled-Parquet numerical comparison retained | PASS |
| R1 / Invalid source fails before construction | Current duplicate/fractional-key, incomplete-grid, missing/extra-month, negative/nonfinite, published-range and unsupported scope fixtures; source-before-construct ordering unchanged | PASS |
| R2: Two explicit relation scores preserve inactive skills / Hand-computable candidate differences | Current hand-score/zero/disjoint/symmetry/scaling tests; unchanged mathematics and prior independent 19-skill oracle | PASS |
| R3: Sparsification is deterministic and retains explicit weights / Ties and asymmetric selections | Current 13-way tied neighborhood, one-sided union, no loop/duplicate/zero edge, degree >10 and canonical row-order fixtures; prior independent oracle retained | PASS |
| R3 / Empty relations remain explicit | Current all-zero/disjoint fixtures; complete population, empty edges and null summaries | PASS |
| R4: A shared relation maps within target contexts without changing population / Same graph in distinct contexts | Original A; current multiple non-dense context exact endpoint/target-key membership/score/direction/empty-schema tests; checker now validates actual expanded identities | PASS; V-001 resolved |
| R4 / Population mismatch is explicit | Current missing/extra/duplicate/incomplete target-grid fixtures and key-only projection tests | PASS |
| R5: Structural diagnostics expose coverage and score degeneracy / Dense equal supports are visible | Current 78-full-score-pair fixture, tie/degree consequences, components/isolates, all-skill/active denominators, overlap and zero-variance reasons; structure code unchanged | PASS |
| R6: Trends are diagnostic and insufficient histories remain unknown / Sparse and constant histories | Current null-reason priority, per-context reason codes, common zeros and unchanged graph-payload tests; prior independent numerical evidence retained | PASS |
| R6 / Occupational heterogeneity | Current explicit +1/-1 fixture, min/max/counts and unknown handling; unchanged 26-first-difference implementation | PASS |
| R7: CPU costs and incomplete work are observable and bounded / Resource limit or interruption | Original B; current timeout, over-RSS, both monitor-loss statuses, completed-stage retention, cancellation, no-retry, hard-kill and exit-race tests; durations/dimensions/byte units preserved | PASS; V-002 resolved |
| R8: Artifacts are exclusive self-contained and checkable without source data / Self-contained saved check | Original D intact source-removed output passes; current normal supervised/exit-race checks and provenance consistency tests; non-pickle numeric reload/input preservation maintained | PASS; V-002/V-004 resolved |
| R8 / Corruption or collision | Current checksum, score/count/key, incomplete status, exclusive reports/runs and 1e-13 acceptance/1e-9 rejection fixtures; individually re-inventoried missing/contradictory provenance cases rejected | PASS; V-004 resolved |
| R9: Development and research acceptance remain separate / Fixture readiness | Current public fixture CLI build/check, old help/import probes and research-injection rejection; unchanged README/old pipeline plus prior full compatibility suites | PASS for software; separate research acceptance not performed |
| R9 / Unsafe output override | Original C; current explicit/default scratch-root aliases, direct/traversal/symlink and temporary-checkout fixtures; ordinary scratch/external temporary paths still accepted | PASS; V-003 resolved |

Proposal/design/task review remains coherent: fixed protocol, isolated CPU package, independent candidates, deterministic top-10 union, shared diagnostic trends, lazy mapping, no old pipeline edits and later research acceptance. The repairs complete affected tasks 3.1 and 4.2–4.4 without revising task checkboxes or planning artifacts. No new planning finding was identified.

## Findings

All four existing findings are verified-resolved. Repair-owned notes below are preserved verbatim; prior failure descriptions are superseded by the current rechecks.

### V-001: Lazy edge expansion emits positional indices as non-dense skill IDs

- Category: implementation
- Severity: medium
- Requirement: R4, “Same graph in distinct contexts”; task 3.1.
- Evidence: `mapping.py:55` now indexes `source_skills` and keeps empty shape `(0,4)`; original A returns exact expected IDs; current mapping/checker/CLI tests pass.
- Expected: Exact context-qualified skill identities in both directions with aligned scores and stable empty schema.
- Actual: Expected endpoint identities, membership and score order observed in both non-dense contexts; checker compares endpoints as well as counts.
- Repair status: verified-resolved
- Repair notes: Reproduced before edits with the strengthened mapping tests: non-dense endpoints were positional IDs and empty expansion had two columns. Updated benchmark/occupation_skill_graph/mapping.py to translate indices through source_skills and return an empty (0,4) schema; checks.py now validates expanded endpoint identities, contexts and aligned scores. test_mapping.py asserts exact pairs and target-key membership in both non-dense contexts, both directions, score order and empty schema. Original reproduction A now returns [[2,1,2,4],[2,4,2,7],[2,4,2,1],[2,7,2,4]] and (0,4). Focused mapping/checker/CLI/runner/supervisor checks passed (55 tests); final command conda run --no-capture-output -n job-sdf-baseline python -m unittest discover -s benchmark/occupation_skill_graph/tests -v passed all 94 tests in 7.637 s, including checker/CLI fixtures and old-interface compatibility probes. Independent reverification remains required.
- Reverification notes: Independently rechecked at `3039f9c` this round; original reproduction and affected regression tests establish resolution. No additional repair remains for this finding.

### V-002: Monitor loss permits success and mutates an inventoried supervisor record

- Category: implementation
- Severity: medium
- Requirement: R7 bounded execution and R8 self-consistent saved evidence; task 4.2.
- Evidence: `supervisor.py` terminates a live worker on missing RSS samples, preserves `rss_monitor_failure` and removes completion inventory on termination; mutable supervisor evidence is excluded from immutable inventory and checked directly. Original B and current real-worker tests pass.
- Expected: Live monitor loss fails explicitly; completed-stage evidence survives; ordinary successful artifacts remain checkable.
- Actual: Original B returns 1 with terminated state and durable reason. Both unavailable/unsupported samples, completed source retention, exit races and ordinary supervised saved checks pass.
- Repair status: verified-resolved
- Repair notes: Reproduced before edits using actual isolated fixture workers: both unsupported and unavailable post-preflight probes returned successful builds. Updated supervisor.py to stop a live worker on any missing RSS sample, recheck process exit to distinguish exit races, and retain rss_monitor_failure plus the measurement and completed-stage evidence in terminal status/supervisor records. Termination/cancellation removes any worker-published completion manifest. artifacts.py excludes the mutable supervisor record from immutable inventory; checks.py directly requires a present supervisor record to show successful completion. test_supervisor.py adds real-worker coverage for both monitor failure statuses, saved completed source evidence, an exited-worker race, and a normal supervised build followed by saved-only checking. Original reproduction B now exits 1 after two probes with terminated/rss_monitor_failure and a durable injected-loss reason; its saved check rejects the non-success state. Focused 55-test run and final 94-test suite passed; ordinary supervised and exit-race outputs pass their saved checks. No independent resolution claimed.
- Reverification notes: Independently rechecked at `3039f9c` this round; original reproduction and affected regression tests establish resolution. No additional repair remains for this finding.

### V-003: A symlinked scratch root authorizes development output inside research

- Category: implementation
- Severity: medium
- Requirement: R9 “Unsafe output override”; task 4.3.
- Evidence: `paths.py` checks protected resolved destinations independently of scratch; original C raises `PathError`; current alias tests cover default and explicit paths for five protected directories in disposable checkouts.
- Expected: Protected destinations are rejected before reservation through direct paths, traversal or symlinks.
- Actual: All tested protected aliases rejected; protected directories remain empty; legitimate scratch and external temporary outputs still work.
- Repair status: verified-resolved
- Repair notes: Reproduced before edits in disposable temporary checkouts: scratch aliases to research, dataset, benchmark/source and history were accepted. Updated paths.py to reject protected resolved destinations independently of scratch resolution and to require an actual scratch subtree for outputs inside the checkout. test_cli.py covers both default and explicit roots below aliases to research/dataset/benchmark/source/history, asserts no protected output was reserved, and retains ordinary scratch, external temporary, direct/traversal/symlink and temporary-checkout checks. Original reproduction C now raises PathError for the protected research destination (expected nonzero). Focused 55-test run and final 94-test suite, including public CLI fixtures, passed. Only fake checkouts were used for protected-directory probes.
- Reverification notes: Independently rechecked at `3039f9c` this round; original reproduction and affected regression tests establish resolution. No additional repair remains for this finding.

### V-004: Saved-only checking accepts missing reproducibility provenance

- Category: implementation
- Severity: medium
- Requirement: R8 mandatory reproducibility evidence and missing/contradictory evidence rejection; task 4.4.
- Evidence: `checks.py` requires environment/code/patch files, validates saved command/source/code/target/environment consistency and recovery declarations. Original D intact source-removed check passes; its corruptions fail; eight isolated re-inventoried provenance tests also pass.
- Expected: Reject missing/contradictory saved provenance while retaining source-free, read-only checks and historical execution identity.
- Actual: Missing environment snapshot, empty code/environment/source records, contradictory baseline/target/environment and absent recovery declarations rejected individually; numeric tolerances and input preservation remain valid.
- Repair status: verified-resolved
- Repair notes: Reproduced before edits with independently re-inventoried mutations: missing code/environment provenance or environment.txt, empty source.json, contradictory baseline/environment/target identities and absent recovery declarations were accepted. Updated checks.py to require environment.txt, code-source.json and git-diff.patch; validate mandatory provenance fields; compare redundant command/source/code/target identities; check baseline availability/references, scoped recovery evidence and patch byte counts; and validate saved dependency/thread/protocol facts against the environment snapshot. Historical claims are checked solely against saved records, without requiring live environment/source/Git-baseline matches. test_checks.py adds eight independently re-inventoried corruption cases with specific provenance errors and input-byte preservation checks, using a real repository code capture for the golden artifact. Original reproduction D now passes the intact source-removed artifact and rejects both mutations; separate regression cases isolate the empty source record and missing code/environment objects. Existing 1e-13 acceptance, 1e-9 rejection and source-removal cases pass. Focused 55-test run and final 94-test suite passed; openspec validate add-occupation-skill-graph-audit --type change --strict --json --no-interactive passed. Verdict remains owned by independent verification.
- Reverification notes: Independently rechecked at `3039f9c` this round; original reproduction and affected regression tests establish resolution. No additional repair remains for this finding.

## Reproduction Commands

Run from the repository root in the pinned CPU environment. The snippets use only disposable fixtures; they do not write implementation/tests or actual research outputs. Current observed results are recorded in Checks above; temporary directories are deleted after each probe.

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

Next action: `$openspec-e13-archive-change add-occupation-skill-graph-audit`. This PASS applies only to the recorded verification basis; relevant edits require re-verification. Archive does not itself establish research acceptance.
