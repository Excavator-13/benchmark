## Context

See `proposal.md` for motivation and `specs/nograph-baseline-entry/spec.md` for the contract. The sole scientific authority is [第一阶段实验协议：可信数据与 baseline](../../../research/phases/P01/protocol.md), sections 3-6 (`P1-count-L6-H3-v3`). [P01：建立可信研究底座](../../../research/phases/P01/plan.md) assigns this scope to T004 and retains Ridge results even if they do not improve on naive rules. [第一阶段执行指导：诊断与 baseline 操作](../../../research/phases/P01/execution-guide.md), sections 2 and 7, supplies environment and implementation context rather than a second protocol.

Observed code has a graph-dependent runner and a separate traditional runner importing statsmodels/Prophet and using older paths. Neither is a suitable dependency for this entry. There is no project-wide Python packaging/test configuration. `.gitignore` excludes graph results but not `research/runs/`. The v2 diagnostic log contains aggregate identity information and naive scores, not complete saved node keys or predictions. Its scientific definitions agree with v3; v3 changed record layout only.

## Goals / Non-Goals

**Goals:** Separate scientific operations from command handling and evidence writing; make training/selection information boundaries inspectable; run the full default path using three required third-party packages; allow evaluation directly from saved numeric artifacts.

**Non-Goals:** No abstraction for all benchmark model families, graph snapshots, GPU execution, online refitting or configurable scientific protocols. No automatic packaging, research acceptance, research-record maintenance, commit/push or main-spec sync. Only new run directories may be written under `research/` during future run tasks. This turn creates planning files only.

## Decisions

### 1. One capability with a separate module boundary

Use the flat capability `nograph-baseline-entry`. Data identity, selection, metrics and persistence are parts of one user's end-to-end baseline workflow. Splitting them into generic platform capabilities would add reuse promises absent from T004. Extending graph capabilities would bring tensor/device/checkpoint obligations to a graph-independent tool.

Add `benchmark/nograph_baseline/` with lightweight `__init__.py`, `__main__.py` and these responsibilities:

| Module | Responsibility |
| --- | --- |
| `cli.py` | Parse commands; launch one isolated CPU worker per run; resolve repository paths from module location |
| `data.py` | Validate/sort demand Parquet; build node identities, observation arrays and audit data |
| `protocol.py` | Fixed protocol constants, calendar/window metadata and split assertions |
| `baselines.py` | Five naive predictions and validation-only reference selection |
| `ridge.py` | Training statistics, shared fitting, validation-only lambda selection and prediction |
| `metrics.py` | Pure original-unit metric reductions and fixed-mask reporting |
| `coverage.py` | Evaluation-only neighbor-mask loading/derivation and identity checks |
| `artifacts.py` | Versioned manifests, provenance, safe numeric I/O, atomic writes and status |
| `runner.py` | Order operations, time stages and pass bounded inputs to fit/select/evaluate |
| `checks.py` | Saved-run recomputation, same-seed comparison and immutable v2 alignment |
| `tests/` | Standard-library unittest suite with small synthetic Parquet fixtures |

Use a local `requirements.txt` listing only NumPy/pandas/PyArrow and document optional sklearn separately. No import, call or mutation of `benchmark/graph_method/**`. Avoid graph/traditional runner reuse; reproduce only the small protocol-specific identity rules here. Tests use `python -m unittest discover -s benchmark/nograph_baseline/tests` from the repository root, without installing pytest or reading production graph files.

### 2. Stable commands and explicit reporting annotation

Canonical module interface from the repository root:

```bash
conda activate job-sdf-baseline
python -m benchmark.nograph_baseline run --data-name r0 --mode count --seed 0 --run-id p01-r0-sharedridge-001
python -m benchmark.nograph_baseline run --data-name region --mode count --seed 0 --run-id p01-region-sharedridge-001
python -m benchmark.nograph_baseline recompute --run-dir research/runs/p01-r0-sharedridge-001 --run-id p01-r0-recompute-001
python -m benchmark.nograph_baseline compare --run-a research/runs/p01-r0-sharedridge-001 --run-b research/runs/p01-r0-sharedridge-repeat-001 --run-id p01-r0-repeat-check-001
python -m benchmark.nograph_baseline align-v2 --run-dir research/runs/p01-r0-sharedridge-001 --reference research/runs/phase1-20261006-v2-01/naive-baselines.log --run-id p01-r0-alignment-001
```

Require a single safe path-component run ID; reject traversal and existing directories. `run` always executes all five naive methods and SharedRidge. Accept `--ridge-backend {numpy,sklearn}` (default numpy), optional `--clip-nonnegative`, and an optional `--neighbor-mask` for a prevalidated mask bundle. Do not expose window sizes, ratios, lambda grids or arbitrary dataset/mode values for this protocol. Defaults for demand sources, protocol and outputs derive from module location; fixture injection is a reusable API/testing facility, not a second public scientific configuration.

Without a supplied mask, formal runs read `dataset/graph/<data-name>.parquet` only to annotate evaluation: validate context IDs and endpoint membership, exclude self-loops, mark both fully qualified endpoints of non-self rows. Save the source hash and the resulting mask. A supplied mask contains canonical node keys, a boolean mask, definition and source SHA256 provenance; validate exact key alignment and record bundle hash. All model APIs accept demand values only. Synthetic API masks let CPU tests complete without graph files. Missing coverage evidence is a recorded failure for a formal run, never an all-isolated default. This satisfies graph-free forecasting while retaining mandatory neighbor-group reporting; the raw table is not graph-model data or a runtime graph-library dependency.

`recompute`, `compare` and `align-v2` reserve their own new run directories with check-type manifests, linked input-run/artifact hashes, commands, status and reports. They leave formal input runs unchanged. They are analysis evidence, not additional model configurations. Examples are future commands, not experiments executed during propose.

### 3. Demand-to-selection data flow

1. Reserve an exclusive output directory; snapshot protocol/configuration and capture provenance before fitting.
2. Validate source keys, all monthly columns and native count values; sort by context then skill. Record actual counts rather than asserting README's historical 2,324 skills. Check finite integer IDs and unique keys. Audit grid completeness using the actual context and skill sets.
3. Preserve the diagnostic arithmetic path: demand signals and naive predictions use float32; error arrays and metric reduction use float64. Validate conversion remains finite and record dtypes. Ridge training/solving uses float64 converted from the same identity-aligned signal. Dtype choice is implementation metadata, not a new scientific protocol.
4. Build window starts 0..27 and exact train/validation/test/omitted membership. Store inputs/targets/origins; assert target-month sets are disjoint and exactly four starts are omitted. Test origins are June, July, August and September 2023, with their then-observed true inputs.
5. Compute frozen statistics and activity masks directly on `signal[:, :27]`, never on flattened windows. Record actual standard deviations, effective standard deviations, constant mask and 27-month range. Full-36-month diagnostics are descriptive only.
6. Prepare training pairs `[19*N,6]` and `[19*N,3]` using a recorded window-major/node-major ordering. Select naive references and SharedRidge candidates using only the validation slice. Fit/selection APIs do not receive test targets. Loading the source table does not authorize passing its future labels to selection.
7. Freeze the selected model/reference records before constructing the test evaluation payload; predict each test origin independently with unchanged training statistics and parameters. Save primary validation and test predictions and gold arrays. SeasonalNaive12 is needed only for validation/test here, where last-year target values precede the origin; do not use negative indexing to invent seasonal training predictions.
8. Build evaluation-only coverage masks and compute all required reports. Gold arrays, fixed masks and model outputs share canonical keys. Save terminal artifacts/status only after completeness checks.

Alternative: use the graph loader's snapshots. Rejected because this would require generated graph artifacts and PyG dependencies and make the training-only statistics harder to isolate. No streamed caches or parallel preprocessing until measured costs justify them.

### 4. Pure NumPy default; optional sklearn with equivalent regularization

For each lambda, center the standardized training matrices over their M rows, solve

```text
W = solve(Xc.T @ Xc + (lambda*M)*I6, Xc.T @ Yc)
b = mean(Y) - mean(X) @ W
```

The intercept is unregularized. Positive lambda makes the small six-feature system suitable for deterministic CPU linear algebra. Save W `[6,3]` and b `[3]`, M, centered training means and the objective. M is `19*N`, currently expected as 44,365 for r0 and 310,555 for region, recalculated from validated data. This is a shared fit, not N separate fits. Each sample's objective sums three horizon errors; do not divide alpha by H.

Pure NumPy is the required default because the user requires the complete entry to run with only NumPy/pandas/PyArrow. A sklearn-only default would contradict that acceptance condition. Optional sklearn uses a lazy import, `Ridge(alpha=lambda*M, fit_intercept=True, solver="svd")`, with no random solver. Transpose sklearn's coefficient array to the persisted `[6,3]` convention. Save backend/version, lambda, M and effective alpha for every candidate in both backends; explicitly call the NumPy term `lambda*M` an equivalent sum-loss regularizer. Test equivalence against NumPy when sklearn is installed; missing optional sklearn yields an actionable error only if requested.

Record inverse-transformed validation MSE/MAE for all five lambdas. Minimize `(validation_MSE, -lambda)` for exact ties. Naive references minimize `(validation_MSE, protocol_table_order)`. No approximate-tie epsilon, test score or clipped score enters selection. Keep all candidate W/b and validation prediction arrays as small audit evidence. Raw selected validation/test outputs are primary; clipping is an optional separately named `SharedRidgeNonnegative` report sharing the frozen selected lambda.

### 5. Metric semantics and masks

For arrays `[windows,nodes,3]`, use float64 errors. MAE is mean absolute error, MSE is mean squared error, RMSE is sqrt(MSE), and negative ratio is count(pred<0)/element_count. Slice the same arrays for each window, horizon, context and mask. Store MSE as well as MAE/RMSE to audit the reductions. Save node counts and element counts, and mark empty metrics with JSON null plus an explicit empty status, never NaN.

Four activity masks partition the training-only nonzero fraction at 0, 1/3 and 2/3. Save counts and mask arrays once and reference them from every method. Report inactive nodes as the training-all-zero group. Equal-weight activity MAE averages nonempty group MAEs. Store absolute/squared error sums and contribution fractions for activity and constant groups. For the protocol's descriptive large-demand audit, save per-node training means and absolute/squared error contributions in a complete training-mean-ranked table (ties by canonical key). This exposes large-demand nodes without inventing a threshold or a fifth comparison group; it neither selects nodes for training nor replaces the four prespecified groups.

Relative MAE improvement is `(MAE_ref-MAE_model)/MAE_ref` for validation-selected NaiveRef, with NaiveRef6 reported separately for six-input comparisons. A zero reference MAE has null improvement and a reason. Test month multiplicities remain 1,2,3,3,2,1; do not add a month-balanced primary metric or treat duplicate targets as independent trials. No statistical-significance or graph-benefit claim is part of T004.

### 6. Versioned output layout and source capture

Each formal output directory has schema-versioned JSON with relative numeric artifact paths and declared axes/dtypes:

```text
research/runs/<run_id>/
  protocol.md                    # immutable run snapshot
  config.json, command.json
  provenance.json                # run ID/type, source/code identities, timestamps
  git-commit.txt, git-status.txt, git-diff.patch
  code-untracked/                # copies of used untracked source, hash manifest
  environment.json, environment.txt, source-sha256.json
  nodes.parquet                  # node_index and ordered integer key columns
  windows.json                   # 28 starts, all months/origins, splits and omissions
  audit.json, masks.npz           # activity/constant/coverage and saved diagnostics
  node-errors.parquet            # per-method/split/node training mean and error contributions
  gold/validation.npy, gold/test.npy
  predictions/<method>/validation.npy, predictions/<method>/test.npy
  models/SharedRidge.npz          # W, b, node mean/std and centered fit statistics
  candidates/<lambda>/parameters.npz, candidates/<lambda>/validation.npy
  selection.json                 # naive/lambda scores, ties, alpha=M*lambda
  metrics.json, measurements.json
  artifacts-sha256.json           # numeric outputs and snapshots, no self-hash
  events.jsonl, summary.md, status.json
```

For unclipped naive models persist TrainMean27 statistics as well as labels/predictions. Shared arrays describe axes `[split_window,node_index,horizon]`; nodes and window metadata define identity unambiguously. `.npy`/`.npz` contain numeric arrays loaded with `allow_pickle=False`. `models/SharedRidge.npz` contains training node normalization and selected parameters sufficient to reconstruct predictions from six observed values. All methods' saved validation/test arrays and masks suffice to recompute every reported metric, error contribution and relative gain; the descriptive per-node table stores canonical identities and training means.

Capture commit with `git rev-parse HEAD`, tracked staged/unstaged differences against HEAD and working-tree status. Include contents/hashes of used untracked implementation files, since an implementation may run before it is committed. Source manifest includes demand, coverage source/mask, protocol snapshot and reference evidence where used. Record code scope and dirty state without updating commit identity later. Exclude generated output directories from source capture to prevent recursive provenance. Hash source files before reading and verify hashes remain unchanged after the run. Record Python executable, package versions, pip freeze, OS/CPU/machine, NumPy BLAS configuration and thread environment. Git/provenance failures are explicit, not guessed identities.

Alternative: reuse graph `.pt` outputs. Rejected because independent metric recovery must not require PyTorch. Existing ignores need no edits, and unignored files do not establish Git inclusion or a verified backup.

### 7. Repeatability and measurement in isolated workers

Use a fresh CPU subprocess per invocation so process-lifetime peak RSS is attributable to one dataset run and the same condition can be repeated. Set BLAS thread counts to 1 in the worker environment before NumPy import and record effective settings; seed Python and NumPy with the supplied seed without introducing randomized behavior. Each dataset gets one formal execution and another complete same-seed execution in an independent run directory, not several fake seed trials.

Compare identities, source/protocol hashes, solver/configuration and environment before comparing arrays. Record `max(abs(pred_a-pred_b))` per method/split and across all predictions. Require elementwise `abs(a-b) <= 1e-6*max(1,abs(a),abs(b))`, recording normalized maximum differences; use the same normalization for MAE/MSE/RMSE, and require the exact protocol MAE formula `abs(MAE_a-MAE_b)/max(1,MAE_a,MAE_b) <= 1e-6`. Shapes, keys, masks, selections and sample counts must match exactly. Report execution differences instead of interpreting disagreement as initialization variance. No promise of bitwise agreement across CPU/BLAS versions.

Measure monotonic wall-clock durations with `time.perf_counter`: demand read/validation, coverage read/annotation, preprocessing, naive prediction/statistic estimation, all-candidate Ridge fitting, validation selection, selected-model inference, metrics/output and total. Clearly define data-reading total, fitting total and inference total, noting TrainMean27 statistic estimation and zero optimization work for the other naive rules. Avoid including disk output as inference. Save per-method timings where applicable, worker exit code and CPU device.

Measure process peak RSS using standard-library `resource.getrusage(RUSAGE_SELF).ru_maxrss`: macOS reports bytes, Linux reports KiB, so normalize to bytes and retain native value/unit. This captures NumPy native allocations, unlike Python-only tracemalloc. Identify OS and measurement method; unsupported platforms fail the formal measurement check with a reason rather than supply an estimate. No throughput/time/memory target or extrapolation is asserted before measurement.

### 8. Failures, interruptions and evidence readiness

Create directories exclusively before source processing. Atomically write JSON/arrays using same-directory temporary files and rename, keeping an append-only event log. Status transitions are `running` to `success`, `failed` or `interrupted`. The parent launcher records child failures/signals; the child records exception stage/traceback, completed artifacts and available measurements. On SIGINT/SIGTERM, flush available evidence and retain partial outputs. A SIGKILL or power failure can leave `running`; recovery checks classify that as unfinished with no inference of success. A rerun always takes a new run ID; no delete/reset/resume of a partial formal run in this scope.

Successful model execution requires complete formal artifacts; separate check directories record repeatability, metric recomputation and v2 alignment findings. Independent e13 verification consumes those artifacts and implementation notes, but remains separate from implementation and research acceptance. Do not create `verification.md` or declare PASS during apply. Stop writing input runs before research-side sealing; failed/interrupted runs are retained for that later process. No task performs tar packaging, archive-index updates, Git operations or remote upload.

### 9. Immutable v2 alignment

Parse every line of `research/runs/phase1-20261006-v2-01/naive-baselines.log` with JSON. Compare node/skill/context/group counts, training month range, all split indices/target months, NaiveRef/NaiveRef6 and every reported naive validation/test overall/window/horizon/activity/balanced metric. Require identities/counts/choices exactly; compare numerical fields using normalized tolerance 1e-12 for the matching diagnostic arithmetic and record maximum differences. The old log identifies r0 as 2,335 nodes and region as 16,345; both references are LastValue. Spot-check anchors:

| Dataset | LastValue validation MSE | LastValue test MAE | LastValue test RMSE |
| --- | ---: | ---: | ---: |
| r0/count | 397984.1727337616 | 189.8750892219843 | 925.2619140354782 |
| region/count | 19084.344447843378 | 35.30985010706638 | 193.84685312799166 |

The old log cannot prove row-level key equality by itself. Use its run's `source-sha256.txt`, canonical sort rule and independently saved new keys to establish source identity and ordering; record any unavailable evidence. Do not infer a matching identity list from matching aggregate metrics. Do not compare old elapsed diagnostic time to new stage timings as equal-cost implementations.

Findings are stored only in fresh analysis run directories with reference hash, expected/actual values, arithmetic/source differences and explanation. Unexplained differences block evidence readiness; explained differences are presented for independent verification and, if scientifically material, research-side acceptance rather than silently loosening tolerance or rewriting v2 evidence.

## Risks / Trade-offs

- [Float32 diagnostic means differ from float64 means] -> Keep the diagnostic naive path and record Ridge solver precision separately; preserve and explain every discrepancy.
- [Raw graph is needed for the mandatory reporting annotation] -> Keep it isolated in coverage code; support provenance-bearing masks and synthetic fixtures, and test forecast invariance to mask changes.
- [The protocol does not define a large-demand cutoff] -> Save complete per-node demand/error contributions; leave interpretation to research review without adding a threshold.
- [Working tree can contain uncommitted source] -> Save tracked diffs and used untracked source with hashes, never assume source commit equals current/future HEAD.
- [RSS and BLAS vary across systems] -> Use isolated processes and recorded native measurement units/settings; compare repetitions under matching conditions.
- [Hard termination prevents final status writes] -> Preserve unfinished manifests and partial evidence, reject overwrite and require a fresh run.

## Migration Plan

No existing data/spec migration is required. During apply, add the new package, local dependency list, tests and a narrow README section; validate in `job-sdf-baseline`, then produce both datasets' formal/repeat/check runs. Existing graph/traditional entry points and sealed archives remain untouched. Rollback consists of ceasing use of the new entry, while preserving generated run evidence. Main-spec sync/archive and research acceptance happen only in their later workflows.

## Open Questions

No unresolved question blocks planning. Research-side decisions about accepting Ridge as the next reference or interpreting its measured gains await formal results; this change retains results even without improvement. README's historical skill count is not an authoritative node count and is outside this change's broad documentation scope.
