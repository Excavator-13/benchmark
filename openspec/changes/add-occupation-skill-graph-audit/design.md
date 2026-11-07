## Context

See proposal.md for motivation and the new occupation-skill-graph specification for behavior. The research definition is `research/phases/P02/t009-graph-protocol.md` (`P2-occupation-skill-graph-v1`). Design is required because bounded pairwise computation, target identity and durable evidence cross several new modules.

Observed implementation at baseline `91ea3d6df8360998d9d2b1ed36ab764322ee26f3`:

- `benchmark/nograph_baseline/data.py` canonically sorts keys but casts demand to float32 and creates full-36-month diagnostics. Calling that loader directly would violate the new source precision and audit boundary.
- `benchmark/graph_value_skeleton/graph.py` accepts published context-qualified binary edges and explicitly forbids weight/frequency columns. Its model aggregates unweighted means. These contracts remain authoritative for that entry.
- `benchmark/graph_method/prepare_graph_data.py` handles published graph export, not demand-derived global skill relations. Its context column definitions are reusable conventions, not a reason to modify its behavior.
- `benchmark/nograph_baseline/requirements.txt` already pins NumPy 1.26.4, pandas 2.2.3 and PyArrow 17.0.0. Existing artifact utilities demonstrate exclusive directories, code-content capture and platform-specific RSS measurement.
- Read-only Parquet schema inspection found separate r1/r2 keys; no explicit parent mapping was found. Construction does not need that mapping.

## Goals / Non-Goals

**Goals:** Keep source identity, pure graph mathematics, diagnostics and execution storage separate so fixture oracles can test each. Keep the new entry usable without torch or graph packages and avoid duplicated target-edge storage.

**Non-Goals:** No old pipeline refactor, new forecasting adapter, weighted aggregation, graph shuffle generator, hierarchy reconstruction, automatic graph acceptance or resume/restart engine. Completed-stage evidence survives interruption; a later attempt uses a fresh identity rather than resuming an undocumented partial calculation.

## Decisions

### 1. Add an isolated package

Add `benchmark/occupation_skill_graph/` with `__main__.py`, `cli.py`, source/identity loading, pure score/sparsification, mapping, audit, artifacts/checker and worker orchestration modules, with fixture tests under its own tests directory. Final internal module grouping can stay small. Reuse safe utilities by import only where they do not introduce torch or full-period data reads. Existing source modules and scientific constants need no edits; add a README section for the new entry.

Alternative: extend graph-value-skeleton. Rejected because its published binary graph, raw-count training and accepted historical formats would acquire unrelated branches. The current change exports explicit scores but never feeds them into that runner.

### 2. Make train-only reading explicit

Inspect Parquet schema, project r2 identity and the 27 training columns, validate native values and canonical integer keys, then form float64 observations `[occupation, skill, month]`. Keep skill and occupation IDs explicit rather than assuming dense offsets in fixtures. Published mode asserts the protocol's expected sets. Source file hashes and normalized numerical training hashes are separate, allowing held-out perturbation tests without false provenance equality claims.

For targets, read only identity columns and verify exact per-context skill membership. Use the same canonical key hash encoding as existing entries, tested against an independent small oracle. Store target keys and a shared edge mapping descriptor, with a lazy per-context index iterator for checking. No target value loading is necessary in this batch.

Alternative: reuse load_demand wholesale. Rejected because narrowing and full-period diagnostics would become hidden scientific decisions. Existing loaders remain unchanged.

### 3. Use blockwise scores and deterministic union graphs

Compute x, binary support, per-skill totals and normalized profiles once. Stream blocks of 256 source skills against the complete skill set. Jaccard intersections use integer support arithmetic, not boolean matrix multiplication with ambiguous counting semantics. Cosine uses normalized float64 vectors. For each row discard self/nonpositive values and stable-sort by `(-score, skill_id)`, retaining up to 10; full row sorting is adequate for 2,335 skills and handles boundary ties correctly. Count all positive unordered pairs and collect pre-sparsification score summaries while streaming, without saving every pair.

Canonicalize the union to pairs with smaller ID first and retrieve their original scores. Save both outgoing selections and final edges. Exact-tie diagnostics expose ID-dependent choices. All-zero global skills remain in nodes with zero degree. A skill with zero demand in one occupation can still have global relations based on other occupations; local zeros do not trigger mapping filters.

Alternative: a dense unrestricted graph or many k candidates. Rejected for cost and search scope. Union top-k can create hubs; that is measured, not hidden behind a claimed maximum degree of 10.

### 4. Audit without using trends to select edges

Compute connected components and graph summaries with NumPy/standard-library traversal, avoiding graph dependencies. Degree associations use Pearson correlations with null/zero-variance reasons. Empty unions and denominators receive explicit null states where the statistic is undefined.

For the union of both candidate edge sets, process blocks of edges across the 52 occupations. Compute 27-month positive counts, common-zero fractions and 26 first differences. Apply the fixed 12-positive-month eligibility rule before variance checks. Save per-edge eligible/insufficient/constant counts and eligible correlation summaries, then summarize each candidate independently. One shared computation avoids duplicating trend work for overlapping edges. Context correlations with insufficient observations are missing, never zero-filled. Record positive/zero/negative counts and per-edge min/max so opposing context signs remain visible. These diagnostics do not alter graph arrays.

Alternative: multiply similarity by local trend or drop low-evidence edges. Rejected because that would make sparse histories determine relationship availability before the relation hypothesis is evaluated.

### 5. Supervise resources and retain explicit terminal states

Expose `python -m benchmark.occupation_skill_graph build` and `check`. Build launches an isolated CPU worker with recorded single-thread BLAS settings established before numerical imports. Supervisor observes stage progress, enforces construction/trend stage deadlines and worker RSS budgets, and preserves the latest stage record on cancellation or worker death. Use OS/standard-library measurement: platform-aware native peak RSS, with POSIX worker monitoring or Windows native process counters where supported. If memory enforcement is unavailable, fail preflight explicitly; do not claim an enforced limit. Record monitoring interval and scope; monitoring is sampled, not an OS hard allocation cap. Test the supervisor with lightweight injected worker/budget fixtures.

Development output defaults to ignored `scratch/occupation-skill-graph/<id>`; permitted override roots resolve only within ignored scratch or system temporary storage, excluding project source/research/dataset/history even if the checkout itself resides under a system temp directory. Explicit research purpose resolves fresh `research/runs/<id>` and is not invoked by implementation/verification. Fixture injection is an API/test facility; published mode cannot silently take fixture population assertions.

Each output directory is reserved exclusively. Save `command.json`, `provenance.json`, `report.json` and `summary.md`; put numeric evidence and internal progress/status under `artifacts/`. These readable names already fit the repository's generic research-run ignore policy; no per-run exceptions are necessary. Publish success only after payload hashes and all completed audits have been written. Failed or interrupted outputs retain whatever is durable, with stage/reason; unexpected termination leaves detectably unfinished status. No automatic restart or overwrite.

### 6. Keep evidence self-contained and checks read-only

Save training observations, x/profiles, source keys, target keys, selected edges/scores and trend summaries as non-object numeric arrays plus JSON. Embed the executed protocol contents and version/hash in provenance, record baseline commit and scoped execution differences, environment and artifact checksum inventory. Capture only relevant new package/used utility sources, not unrelated dirty research documents.

`check <artifact> --report <path>` verifies completion and inventory, independently validates identities and rederives candidate scores, selection, mapping and audit summaries from saved observations. It does not reopen source Parquet or write inside inputs. Numeric comparisons use normalized 1e-12; discrete structures and null reasons compare exactly. The checker's report names its own source identity and the checked manifest. A checksum match alone is insufficient: contradictions between valid arrays and report counts must fail.

Alternative: rely only on raw source paths and checksums. Rejected because it would not support later inspection when execution sources or data locations change.

## Risks / Trade-offs

- Common occupational supports can make Jaccard nearly tied → disclose score concentration, tie-boundary counts and degree/breadth associations; research acceptance can request a new protocol rather than silently tuning this one.
- Demand cosine may reflect broad occupations and popular skills → report demand/support associations and retain the separate Jaccard candidate; neither score implies forecast utility.
- Global relations can be unhelpful in specific occupations → report diagnostic sign heterogeneity and unknown evidence; actual controlled benefits remain T010.
- Platform numerical rounding can affect near-tie rankings → record numerical environment and exact-tie semantics, prove deterministic behavior in the pinned environment, and avoid claiming cross-platform bitwise equality.
- Sharing topology may spread noisy information to locally inactive skills → preserve population and disclose the hypothesis; this change does not start propagation or claim improvement.
- Polling may observe memory overshoot after allocation → record monitor resolution and native peak measurements, avoid dense replicated arrays, and never describe polling as a hard OS memory cap.

## Migration Plan

Add the isolated package and fixture suite, then document build/check commands. Run fixture and compatibility checks, record implementation notes for independent verification, and archive only through the existing workflow. There is no data migration or historical format conversion. Disabling use of the new entry rolls back its behavior without touching old runners. Complete published-data graph construction remains a later research-side audit after accepted software readiness.
