# Implementation Verification

- Change: add-r2-count-baseline
- Schema: spec-driven
- Verdict: PASS
- Verified at: 2026-10-11T10:16:29Z
- Implementation roots: /Users/watuji/da_chuang/repos/benchmark
- Verified revision: `57275e7b6490a420c3fb110de7ce5f228206cfa6`, with dirty implementation, tests, documentation and main-spec Purpose; selected change directory untracked.

## Summary

Independent verification passed. All scenarios in the selected delta have sufficient evidence, strict OpenSpec validation succeeded, and no actionable finding remains. The full CPU suite ran independently: 238 tests in 29.569 seconds, OK with two optional scikit-learn skips. A newly generated 52 x 2335 x 36 synthetic fixture reproduced the recorded input hashes and completed through the public CLI and isolated NumPy worker. Its saved results passed independent aggregate arithmetic and saved-only recomputation.

This verdict establishes software readiness only. No real r2 demand/graph analysis, formal research experiment, package restoration, sealing, archive, research acceptance, commit or push was performed. Existing research runs, archives, protocol, phase plan, state and delegation pointer were not edited. Only this report was added to the repository. Verification commands created disposable fixtures, runs and a check report under `/private/tmp/r2-verification.H0QxCJ`.

Residual limits: optional scikit-learn execution was not tested because it is not installed; the required NumPy backend was tested. Scale timing is one synthetic development execution on macOS arm64, not a real r2 cost or predictive conclusion. Temporary evidence can be removed by system cleanup; commands and decisive observations are retained below. Main-spec behavioral synchronization remains the archive workflow's action, as planned.

## Verification Basis

The initial snapshot was captured before implementation inspection and executable checks. Its 40-file inventory, contents and Git revision were rechecked after checks and were identical. Fingerprints cover all baseline implementation/tests/dependency configuration, selected planning and small scale-evidence files, main spec, entry documentation and scientific protocol. The workflow-owned handoff/report and bytecode caches are excluded. Real datasets, historical packages and unrelated modules are outside the implementation acceptance basis for this synthetic-only change.

| Path or scope | Revision / content fingerprint / file inventory |
| --- | --- |
| Git HEAD | `57275e7b6490a420c3fb110de7ce5f228206cfa6` |
| Ordered inventory below, compact JSON serialization | SHA256 `b5ab05176e3ac41b52b9e11f728f3a603f0181b3bcef57d497c65c6c920ff2ba`; 40 files, unchanged initially/finally |
| Independently generated synthetic demand | SHA256 `e09134fad7b29498bf3d8afe74af541876b251edd6d29a618b43871e5ebb9a26`; 3,379,697 bytes |
| Independently generated synthetic graph | SHA256 `517d029328e254e9f82c4b28c53f03c38a7f42becfad48e6a5015f3dbe981ae9`; 22,040 bytes |
| Temporary independent scale-run inventory/content | SHA256 `bb2c5ae6db1f404b5546eacf44936b77e3ceca50b63f91950779f93bf89fd05a`; 40 files; identical before/after recompute |

Individual file inventory (repository-relative paths):

| Path | SHA256 |
| --- | --- |
| `benchmark/nograph_baseline/__init__.py` | `d9c569ef793ad4575f7fef38f798f059687e3fd118a471b4d091bfec74c17d78` |
| `benchmark/nograph_baseline/__main__.py` | `2ecea709492803226e52714799d7c861eb97af44100beeca58f3b7942fed2cfa` |
| `benchmark/nograph_baseline/_worker.py` | `6b8add701f414edbf1931af2b29cab2231f8460043db7c88285ae5e400ca967b` |
| `benchmark/nograph_baseline/artifacts.py` | `c116fb5b6ab019a0d5fc74f7528586ec599cb84f785983c4e7ba2173ad30c62d` |
| `benchmark/nograph_baseline/baselines.py` | `a19d4e6465dd864f68e98dc61e803c342cb055955cc33583835142884ff98d2e` |
| `benchmark/nograph_baseline/checks.py` | `7787003efb085f4059196e501a6bf9610e81f068b8db2c407c5b15c76dde563c` |
| `benchmark/nograph_baseline/cli.py` | `47e8428e67f90f7f30e0285a97d2c376ce472899df6380119a124d15e9ba8049` |
| `benchmark/nograph_baseline/coverage.py` | `fad3fa9302e9da44a3cc348977c5f2beaae0951a188cb4cdb983ef0b53177b22` |
| `benchmark/nograph_baseline/data.py` | `9f0409031b87620806f8b8a61e09d20c8d309d87327cedc15ae832aae0670214` |
| `benchmark/nograph_baseline/metrics.py` | `67af0a0cd0b26534d34dcbd66db9ef7c324a7d4f57abb3c91ed14d5faa3e8ab7` |
| `benchmark/nograph_baseline/protocol.py` | `06e38d9d04d7209f6c6142d2f188d8201c81d3aa5544b718bfc99081336fca77` |
| `benchmark/nograph_baseline/requirements.txt` | `afd59d6cb60e3f57c3d888b18ccbcd5e25ed3c912d2df2e4d65e772c10298290` |
| `benchmark/nograph_baseline/ridge.py` | `5fdfe38a4e79cef23ed7d50f206f7d5d074eba5f7ea17e6733ff260f284c09b2` |
| `benchmark/nograph_baseline/runner.py` | `01ff3a1bd2c0036b7006f970a816be97bff236afb8195f9704489df515d166e9` |
| `benchmark/nograph_baseline/tests/nb_fixtures.py` | `1a17434cb6df00803e3935bb93991e684ae0c796fbcb9f0ddc6896e3686d710d` |
| `benchmark/nograph_baseline/tests/test_baselines.py` | `6f8692842f8fa1f8c631a5316ebe391cf6b26547a9fc39c35ab33d5dfc65d949` |
| `benchmark/nograph_baseline/tests/test_coverage.py` | `3cd7fbfcf4199799d9ae7de7933263cba7b7c885779f3a4b490bf0e077149e25` |
| `benchmark/nograph_baseline/tests/test_data.py` | `96486d36afb845698d8a8983418e8b3e39b86cdc3e1b1cc9b0b7410dce4b8894` |
| `benchmark/nograph_baseline/tests/test_metrics.py` | `fc591ccb3825edace0be9e6da62432e8d4bf6e026d68e6c5c3319f60469f5850` |
| `benchmark/nograph_baseline/tests/test_preprocessing.py` | `e9296df4b7d4cf75f84526bd766d92324f745eadf1f191111e7c3a95bbde1246` |
| `benchmark/nograph_baseline/tests/test_protocol.py` | `625fdf38ff54beb94502486b93db8301dda71fa96a0c7d705df1856ceeb7c0dd` |
| `benchmark/nograph_baseline/tests/test_ridge.py` | `48ef0ed86d7a876c05cce988c7c695acb01804b66f791d7e5b09af35e4e8b280` |
| `benchmark/nograph_baseline/tests/test_runner_cli.py` | `0f364a4e239bf2d323d13db12831036462be38246c9b4b92c300f71ad9f11b97` |
| `openspec/changes/add-r2-count-baseline/.openspec.yaml` | `3ae9e70fc0101b2a700cedadfa7b02caa5799fdfd1db033999469c527448c6b2` |
| `openspec/changes/add-r2-count-baseline/design.md` | `ebb3b9b2643ee796776c5482a8db75a78d878240d0e438501c8f3a1e618ffecd` |
| `openspec/changes/add-r2-count-baseline/evidence/generate_r2_scale_fixture.py` | `ec2e726abda304b8d88005d4c7e7bd2b8f61cf9e5f0ee71344d88962d16c0cde` |
| `openspec/changes/add-r2-count-baseline/evidence/scale-fixture-generation.log` | `d324aab34990975e7e3315dfc8cb3ff16b72255900de04ff7044b07ace6010c3` |
| `openspec/changes/add-r2-count-baseline/evidence/scale-fixture-manifest.json` | `d324aab34990975e7e3315dfc8cb3ff16b72255900de04ff7044b07ace6010c3` |
| `openspec/changes/add-r2-count-baseline/evidence/scale-run-cost.json` | `1e7aab41cbd7243c605879386f65b8d41441dd32e18153c6dc3ea2b010101ef5` |
| `openspec/changes/add-r2-count-baseline/evidence/scale-run.log` | `6614a2f863278756f7ec0ef89f8dc61043bcdd0f51993e94f2524503f3cdadd8` |
| `openspec/changes/add-r2-count-baseline/evidence/test-4.3-full-suite.log` | `f655aec141c72d6df2d3c2407c10beeb54f780d8709de1a46fab2c9b96d9de19` |
| `openspec/changes/add-r2-count-baseline/proposal.md` | `a7c6d8874e1037441563f03af26768db5500eb6c676acd8937f5eda53838f536` |
| `openspec/changes/add-r2-count-baseline/specs/nograph-baseline-entry/spec.md` | `ba140fc432ef91a1f79a9d2109888066c73af01b08af133fd56872f26b3dc73d` |
| `openspec/changes/add-r2-count-baseline/tasks.md` | `4391d806cdc9c84a11fceb9b99f3cb6431f32cd9f8261237e48fa95698bd02dc` |
| `openspec/specs/nograph-baseline-entry/spec.md` | `e0823698ccec8201fe6d1fa279176ad1f8e4d1ccdeea2000d68cefed02c17b58` |
| `openspec/config.yaml` | `2a791b0ccc50e2c2ebbb3ba28692a4ad0e4b6ab94ed2151375ac404d7056e89a` |
| `README.md` | `a84268fea884bccbabec8e73f9d8062cd7e4655b3cd7827bfe33eebcbc0c9ae0` |
| `research/phases/P01/execution-guide.md` | `7debab6eed9d3eb1ef021c05332034d4e34103f03430c21b96d1e3d955032b56` |
| `research/phases/P01/protocol.md` | `b510beb0da9a482507072f78282d06bcf9dc93c3758dd7f16b1f8c326ba1d61a` |
| `requirements.txt` | `34e6005f98b5e3ad96f92ac55151780e1cc67f802474c305d939ae3c56127d7f` |

Reproduce the repository fingerprint from the implementation root:

```bash
python3 -c 'import pathlib,hashlib,json,subprocess; root=pathlib.Path.cwd(); scopes=["benchmark/nograph_baseline","openspec/changes/add-r2-count-baseline","openspec/specs/nograph-baseline-entry/spec.md","openspec/config.yaml","README.md","research/phases/P01/execution-guide.md","research/phases/P01/protocol.md","requirements.txt"]; rows=[]
for s in scopes:
 p=root/s
 for f in sorted(p.rglob("*") if p.is_dir() else [p]):
  if f.is_file() and "__pycache__" not in f.parts and f.name not in ("verification.md","implementation-notes.md"):
   rows.append([str(f.relative_to(root)),hashlib.sha256(f.read_bytes()).hexdigest()])
print(json.dumps({"revision":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"inventory":rows,"aggregate_sha256":hashlib.sha256(json.dumps(rows,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()},indent=2))'
```

Paths participate in the inventory and digest, detecting additions and deletions as well as modified contents, including relevant dirty/untracked files. The aggregate is SHA256 of `json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode()` in the listed scope order, with sorted files within each scope. After archiving, substitute the actual archived change directory for traversal and normalize its relative labels back to `openspec/changes/add-r2-count-baseline/` for comparison. Do not treat the change's move or expected main-spec synchronization as silently covered by a pre-archive fingerprint.

The temporary run digest uses sorted `[run-relative path, SHA256]` records and the same compact JSON encoding, including every file in that run. It is auxiliary execution evidence, not a required persistent implementation input. `git status --short research/runs research/archives openspec/changes/archive research/phases/P01/protocol.md research/state.md research/phases/P01/plan.md DELEGATION.md` was empty before/after checks. This establishes current versioned scope, not unobservable claims about past execution activity.

## Apply Handoff Review

Read `implementation-notes.md` in full. It identifies the selected change, schema, project and current HEAD correctly. Its file map matches the current diff. Its previous test/cost results were treated as claims and independently checked; the new test run and new cost measurement are reported separately.

| Reminder | Disposition and independent evidence |
| --- | --- |
| Real CLI and real worker | Confirmed: `R2DevelopmentRunTests.setUpClass` launches two separate public CLI runs; CLI hands a RunSpec to `_worker`. Full suite and fresh scale CLI run passed. |
| Schema comparison is structural | Confirmed: `test_output_schema_matches_r0` compares path sets and collapsed JSON key paths, while separate identity/gold/statistics/selection tests verify values. No numerical conclusion is inferred from schema equality alone. |
| Shared `_write_v2_log` helper changed | Confirmed: context counts derive from keys. Predictions, scores and references derive from raw signal and independent NumPy formulas; its `metrics` argument is unused. Existing r0/region alignment tests and new r2 alignment tests passed in the full suite. |
| Source removal must restore class fixture | Confirmed: r2 recompute test restores demand and graph in `finally`; the full suite passed in its actual discovery order. Alignment also succeeds after source removal. |
| No production fix was needed for information boundaries | Confirmed: only the dataset mapping and CLI text differ in production code. Post-training statistics/candidate invariance, test-only selection invariance and coverage invariance tests passed. |
| Scale evidence is synthetic and outside Git | Confirmed: retained original scratch cost/status/source records match the small cost file and fixture hashes. Independently regenerated fixture hashes match, and a fresh development run completed outside research/runs. Generator and reproduction commands inspected. |
| Main spec not yet synchronized | Confirmed/inapplicable as a defect: only Purpose is changed there; the selected MODIFIED/RENAMED delta replaces the old r2 rejection and two-dataset behavior. Strict validation passes. Archive synchronization is deliberately deferred. |
| Tolerances unchanged | Confirmed: checks use 1e-6 normalized CPU tolerance and align-v2 uses 1e-12; positive/negative tests passed. Scale recomputation maximum normalized test difference was 2.96e-16. |
| Baseline conda environment and optional dependencies | Confirmed: job-sdf-baseline has Python 3.11.17, NumPy 1.26.4, pandas 2.2.3 and PyArrow 17.0.0. Dependency-blocker tests exercised all three schemas and public help/worker without sklearn/graph/GPU imports. Two optional sklearn tests skipped. |
| Research bookkeeping remains separate | Confirmed by protected-path status checks and execution destinations; no research-side record was written and no scientific acceptance inferred. |

No mandatory handoff reminder remains unverified. This was the first verification report; no prior finding IDs or repair notes existed.

## Checks

Commands ran from the implementation root. `PY` below denotes `/opt/homebrew/Caskroom/miniconda/base/envs/job-sdf-baseline/bin/python`; invocations used `conda run -n job-sdf-baseline python`. `VERIFY_ROOT` denotes `/private/tmp/r2-verification.H0QxCJ`, created with `mktemp -d /private/tmp/r2-verification.XXXXXX`.

| Command or inspection | Result | Notes |
| --- | --- | --- |
| `openspec status --change add-r2-count-baseline --json`; `openspec instructions apply --change add-r2-count-baseline --json` | Complete inputs | Repo-local spec-driven, correct implementation root; all four context artifacts read, 15 checked tasks treated as claims. |
| `openspec validate add-r2-count-baseline --type change --strict --json --no-interactive` | PASS | One valid change, zero issues. |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/nograph_baseline/tests -p test_protocol.py` | PASS | 11 tests, 0.002 s. Unknown dataset/rate rejection output is expected. |
| `conda run -n job-sdf-baseline python -m unittest discover -s benchmark/nograph_baseline/tests` | PASS | 238 tests, 29.569 s, skipped=2 (optional sklearn). Includes r2 cases, unchanged r0/region arithmetic, failures/interruption, source capture, purpose/retention and compact-check regressions. |
| `$PY openspec/changes/add-r2-count-baseline/evidence/generate_r2_scale_fixture.py --output-dir "$VERIFY_ROOT/fixture"` | PASS | Fixed seed 20261011; 121420 unique nodes, 52 contexts, 2335 skills, 36 months; 52000 in-context graph rows, 104000 covered nodes, 17420 isolated. Input hashes match apply evidence. |
| Fresh scale run command below | PASS | Success, development, NumPy, separate CPU worker; M=2306980; five candidate scores, selected lambda=1.0, all five naive methods and SharedRidge saved. |
| Independent inspection/arithmetic on fresh scale artifacts | PASS | Canonical distinct r2 keys, complete grid, 1/4 validation/test window shapes, all six predictions finite; independently calculated float64 MAE/RMSE agree within 1e-12. All npy/npz outputs load with allow_pickle=False; 40 files. |
| `$PY -m benchmark.nograph_baseline recompute --run-dir "$VERIFY_ROOT/runs/r2-scale-verify-001" --report "$VERIFY_ROOT/reports/scale-recompute.json"` | PASS | Status ok; validation 4320 compared fields, max normalized difference 0; test 4572 fields, maximum 2.9568628066608753e-16; relative gains/node errors ok; source_data_read=false, model_refit=false. Run inventory/content digest unchanged. |
| Original scale evidence consistency | PASS | Original scratch measurements/status equal `evidence/scale-run-cost.json`; saved demand/node-key identity and actual demand/graph hashes agree. This validates retained apply evidence without adopting its timing as a new measurement. |
| Production/test/doc diff and protocol inspection | PASS | Production changes confined to r2 mapping and CLI description. Generic identity/coverage/selection/check paths traced; protocol scientific text unchanged, no required dependency added. README/execution guide describe r2_id, development, reference scope and separate formal authorization; historical two-dataset text retained. |
| Initial/final fingerprint, protected-path status, `git diff --check` | PASS | All acceptance-basis files and HEAD unchanged during verification; protected-path status and whitespace check empty. |

Fresh scale reproduction (use a new temporary root/run ID when repeating):

```bash
$PY -m benchmark.nograph_baseline run \
  --data-name r2 --mode count --seed 0 --run-id r2-scale-verify-001 \
  --purpose development --ridge-backend numpy \
  --demand-path "$VERIFY_ROOT/fixture/demand/r2.parquet" \
  --graph-path "$VERIFY_ROOT/fixture/graph/r2.parquet" \
  --runs-root "$VERIFY_ROOT/runs"
```

The independent worker measured data reading 0.207257750 s (demand 0.135722750, coverage 0.071535000), Ridge fitting 0.460384542 s, selected-model inference 0.007479375 s and total 2.116456667 s. Peak resident memory was 1,280,212,992 bytes via `resource.getrusage(RUSAGE_SELF).ru_maxrss`, native bytes on Darwin. It records macOS 27.0.1 arm64, 10 CPUs, CPU device, Python/package and NumPy BLAS configuration, seed 0 and five BLAS thread variables set to 1. These are actual synthetic development observations without a performance threshold.

PyArrow emitted sandbox CPU-cache/NEON sysctl warnings. All Parquet operations and checks completed successfully; the warnings did not prevent any acceptance check. The deliberate interruption tests also print interruption messages.

## Requirement Coverage

The selected delta is authoritative for modified requirements and its renamed complete-artifact requirement. Unmodified scientific/persistence requirements are inherited from the main spec and are covered separately below. Every scenario in the selected delta is enumerated, including retained scenarios. Test paths below are under `benchmark/nograph_baseline/tests/`; implementations are under `benchmark/nograph_baseline/`. Results reflect the independent full-suite execution plus inspected assertions, not task checkboxes.

| Requirement / scenario | Evidence | Result |
| --- | --- | --- |
| Independent CPU entry / Minimal dependency environment | `protocol.SUPPORTED_DATASETS`, `cli.build_parser`; `test_runner_cli.CliEndToEndTests.test_minimal_dependency_smoke_for_all_schemas` and help tests block optional sklearn/graph/GPU imports in CLI and worker for r0/region/r2. | PASS |
| Independent CPU entry / Supported r2 count request | `R2DevelopmentRunTests`: two real public CLI executions, five naive + SharedRidge, fixed masks/selection/artifacts; independent scale worker. | PASS |
| Independent CPU entry / Unsupported scientific configuration | `test_protocol.CliSurfaceTests`, `validate_dataset_mode` and split assertions reject r3/rate/out-of-protocol split before fitting; scientific v3 and record-policy v2 retained. | PASS |
| Demand identity / Valid data arrives out of order | `data.load_demand` sorts mapped context/skill columns; `FixtureGridTests`, `R2DemandAuditTests.test_shuffled_multi_context_r2_is_canonically_ordered`, existing r0/region canonical tests and r2 saved gold/key alignment. | PASS |
| Demand identity / Source is invalid | `R2DemandAuditTests` exercise missing r2_id, duplicate/noninteger/nonfinite keys, missing/extra months, negative/nonfinite count; `runner.execute_run` loads demand before preprocessing/fitting; generic malformed-source status test passes. | PASS |
| Demand identity / Multiple r2 contexts share skill IDs | Sparse r2 grid test retains three actual nodes and reports expected four, context counts and per-context audits; full-grid/shared-skill ordering and saved r2_id tests pass. | PASS |
| Neighbor annotation / Same skill occurs in two regions | `coverage.load_graph_coverage`; existing `GraphCoverageTests.test_same_skill_in_two_regions_is_context_qualified` and `CoverageInvarianceTests`. | PASS |
| Neighbor annotation / Same skill occurs in two r2 contexts | `R2CoverageTests` prove both edge endpoints and self-loop exclusion; `R2DevelopmentRunTests` saved masks; `R2InformationBoundaryTests.test_valid_coverage_changes_leave_predictions_and_selection`. | PASS |
| Neighbor annotation / Invalid r2 coverage evidence | `R2CoverageTests` reject unknown context/endpoint, missing r2_id and wrong mask dataset/schema/keys/definition/provenance. Generic missing-evidence rejection remains. | PASS |
| Runtime costs / A formal CPU run finishes | Shared purpose-independent `runner.measure_peak_rss` and measurements path; `RunnerArtifactTests.test_measurements_record_real_units_and_settings` on temporary formal-purpose fixtures. No actual formal research run required or started. | PASS |
| Runtime costs / r2 scale development measurement | Generator, original retained scale records and fresh public CLI/worker execution; dimensions/hash, environment, read/fit/inference/total/RSS and development destination verified above. | PASS |
| v2 alignment / Legacy naive value differs | `CheckCommandTests.test_align_v2_preserves_and_explains_discrepancy`, existing adversarial alignment and new r2 perturbation tests preserve expected/actual and reference bytes. | PASS |
| v2 alignment / Independent r2 fixture reference | `R2AlignV2Tests.test_r2_reference_aligns_without_reading_source_data`; independent raw-signal NumPy prediction/metric/reference helper, matching source manifest, source files removed, >50 compared fields and 1e-12 tolerance. | PASS |
| v2 alignment / Reference contains no r2 records | r0-only temporary reference yields failed report naming r2 and CLI nonzero; reference and input run hashes unchanged. Missing manifest stays limited, source hash mismatch stays mismatch. | PASS |
| Complete artifacts / Execute both supported datasets end to end | Existing `RunnerArtifactTests`, `CheckCommandTests`, CLI/dependency tests exercise temporary r0/region runs and shared outputs. Historical scientific evidence is preserved; no rerun is required for this software change. | PASS |
| Complete artifacts / Separately authorized r2 experiment | Shared RunSpec purpose/artifact path inspected; r2 complete-artifact contract exercised in development and generic formal-purpose parity tested in `PurposeDeltaTests`. Scientific authorization is a separate research action, not a required new real experiment for readiness. | PASS |
| Complete artifacts / Existing scientific acceptance survives record-format maintenance | `PurposeDeltaTests`, `CandidateRetentionDeltaTests`, saved-schema/check regression tests; protected paths unchanged. Main scientific arithmetic is unchanged. | PASS |
| Complete artifacts / r2 software readiness is independently verified | Two development CLI runs, audits/numerics/masks/output/schema tests, saved-only checks/independent alignment, repeated-run comparison and newly measured full-scale development run. No research task acceptance recorded. | PASS |
| Compact saved checks / Three saved-only check commands | `checks` reads saved inputs without importing fitting routines; `CheckReportContractTests`, `R2DevelopmentRunTests`, `R2AlignV2Tests`; compact envelopes, source/command/tolerances and unchanged inputs; scale recompute. | PASS |
| Compact saved checks / Report collision or output inside an input | Generic destination tests plus `R2CheckContractTests.test_report_collision_and_inside_input_are_rejected`; collision retains original bytes, inside-input path produces no report. | PASS |
| Compact saved checks / Invalid saved evidence | `CheckAdversarialTests`, `RecomputeNullSemanticsTests`, `CheckReportContractTests` and r2 corruptions verify missing/malformed arrays/identity/metrics, retained safe failure reports and nonzero exits. | PASS |
| Compact saved checks / Legacy command flags are reused | Existing alias tests for all checks resolve one root/run-id.json report and no check experiment directory. Data-name independent output path code inspected. | PASS |
| Compact saved checks / Output flag choices conflict | `cli._add_report_output_options` mutually exclusive arguments; `CheckReportContractTests` exercise conflict and no output. | PASS |
| Compact saved checks / r2 recomputation and repetition | Source-removed r2 recompute reproduces aggregate/window/horizon/context/activity/neighbor metrics, gains and node errors; compare validates masks/conditions with max prediction and protocol MAE differences <=1e-6 and unchanged inputs. Full-scale recompute also passes. | PASS |
| Compact saved checks / r2 identities or predictions disagree | `R2CheckContractTests`: node identity and mask mismatches, prediction/metric perturbations, failed/mismatch/limited nonzero CLI; existing protocol/environment/backend/coverage mismatch tests pass. | PASS |

Inherited scientific/persistence scenarios relevant to the unchanged shared computation:

| Requirement / scenario | Evidence | Result |
| --- | --- | --- |
| Fixed windows / Protocol split is constructed | `test_protocol.SplitTests`, `test_data.WindowConstructionTests`, saved r2 windows verify 28 total, 19/1/4 used, four omitted and disjoint target months. | PASS |
| Fixed windows / Second test origin uses known history | Window construction tests verify true July input and August-October targets at start 25; independent stateless naive/Ridge functions receive observed windows. | PASS |
| Naive methods / Validation MSE ties | `test_baselines.ReferenceSelectionTests` verify protocol-table tie order and MSE-only selection; r2 test-label changes preserve both frozen references. | PASS |
| Naive methods / Seasonal prediction uses extra history | Independent SeasonalNaive12 arithmetic, `NaiveMethodTests` and reference labeling/NaiveRef6 exclusion tests. All five r2 predictions aligned to independent v2 reference. | PASS |
| Normalization / Overlapping training windows have unequal month multiplicities | `test_preprocessing.TrainingStatisticsTests`; r2 saved mean/std/effective std equal exactly unique first-27-month statistics with ddof=0. | PASS |
| Normalization / Future values change | `R2InformationBoundaryTests` change months after 27; frozen means/std/activity masks and every candidate W/b remain identical. | PASS |
| Normalization / Constant training node | Constant/all-zero fixtures; stored effective std=1, finite standardized values and reconstructable model tests. | PASS |
| Shared Ridge / Test labels cannot affect selection | `test_ridge.CandidateSelectionTests` distinguish validation MSE vs MAE; r2 test-only changes preserve entire selection.json, lambda and NaiveRef/NaiveRef6. | PASS |
| Shared Ridge / Lambda scores tie | Exact-tie candidate test chooses larger lambda; all five r2 score rows persist; one shared 6x3 W and 3-vector unregularized bias, M=19*N verified. | PASS |
| Shared Ridge / Sum-loss backend is used | NumPy normal equations explicitly add lambda*M to Gram matrix; `NumpyFitTests`, payload and candidate tests verify objective, alpha and M. Optional sklearn executable equivalence is skipped and not required by the default backend. | PASS for required backend |
| Metrics / Window RMSE values differ | `test_metrics.ErrorMetricTests.test_overall_rmse_is_not_mean_of_window_rmse`; independent full-scale aggregate RMSE and recompute pass. | PASS |
| Metrics / Activity boundaries and an empty group | r2 0/1/3/2/3 boundary tests, empty-group/null semantic tests, common masks and nonempty-group equal-weight averaging; target multiplicities and zero-reference undefined gain tests pass. | PASS |
| Recoverable evidence / Metrics are independently recomputed | Source-removed r2 and generic checks, all levels/gains/node-error output; fresh scale 8892 aggregate numeric fields checked, run bytes unchanged. | PASS |
| Recoverable evidence / Run is interrupted or collides | `FailureAndInterruptionTests` verify exclusive reservation, malformed source and SIGINT/SIGTERM/SIGKILL/unfinished evidence; purpose-independent run path inspected. | PASS |
| Recoverable evidence / Committed execution sources are reused | `SourceCaptureDeltaTests` and `RepairRegressionTests` verify commit/path references, scope and omission of unrelated content. | PASS |
| Recoverable evidence / Runtime source or protocol is uncommitted | Source and repair regression tests reconstruct tracked modifications/deletions/untracked/dirty protocol; current r2 mapping/CLI changes captured in source evidence. | PASS |
| Recoverable evidence / Git identity is unavailable | Non-Git/unavailable-diff/source tests preserve explicit limitations and recoverable content without asserting clean/fixed identity. | PASS |
| Recoverable evidence / Candidate retention is reduced by default | Candidate-retention and r2 artifact tests preserve five scores, selection, selected model/preprocessing and primary predictions; losing arrays absent by default. | PASS |
| Recoverable evidence / Candidate arrays are explicitly requested | Retention tests exercise explicit arrays, unchanged computation; r2 information-boundary tests load every retained candidate W/b. | PASS |
| Same-seed repetition / Same seed is executed twice | Two independent r2 CLI runs with same inputs/seed/config/environment; compare records prediction maximum absolute and normalized differences and protocol MAE relative difference <=1e-6, no fabricated seed variance. | PASS |
| Development purpose / Development fixture runs | `PurposeDeltaTests` verify default ignored scratch root and formal/development numerical parity; r2 development destination/config/provenance checked. | PASS |
| Development purpose / Development output points at formal records | Purpose tests reject direct and symlink-resolved overrides into research/runs before reservation/fitting; r2 uses same validation path. | PASS |

The unmodified main-spec requirement concerning the separately requested T004 Git-backed package maintenance utility is outside this change's delta, proposal and task scope. No archive-utility or package maintenance action was invoked. Its five package verification/export scenarios are not newly claimed as verified by this report, and do not impose a package restoration prerequisite on synthetic r2 software readiness. Static search confirms model/check modules have no call to that utility.

Proposal/design/tasks were also checked for promises outside scenarios: the explicit r2 fixture branch preserves r0/region generation; no new dependency/API/schema/numerical branch was introduced; docs/parser smoke passed; scientific protocol and legacy evidence are unchanged; scale generator reproduces fixed-seed dimensions and hashes outside the formal namespace; original and independently repeated cost evidence are clearly synthetic. All 15 checked task claims are supported within this implementation scope.

## Next Action

Run `$openspec-e13-archive-change add-r2-count-baseline` when ready to finalize the change. This PASS applies only to the recorded implementation/planning basis; relevant edits require re-verification. Research-side acceptance and delegation wrap-up remain separate from archive and software verification.

