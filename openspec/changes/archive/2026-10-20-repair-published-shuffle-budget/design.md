# Design

## Context

See proposal.md for motivation and specs/graph-value-skeleton/spec.md for the added contracts. The current generator uses sorted Python edge tuples, a PCG64 stream derived from shuffle seed/context IDs and a sequential swap loop. `runner.py` generates a graph for each shuffled run; the frozen matrix has 54 such runs but nine distinct graph conditions. `checks.py` currently compares audit fields directly to the latest module constants, so merely bumping those constants would reject historical audits.

The pinned Python 3.11 CPU environment already works. Two known test failures are an exact torch version string without its valid `+cpu` suffix and exact equality across different GRU batch shapes; same-shape reset is exact and cross-shape difference was below the existing 1e-6 contract. Full r2 model cost remains unmeasured. Published graph timestamps remain unknown.

## Goals / Non-Goals

**Goals:** remove repeated allocation overhead and redundant graph generation; retain deterministic, auditable sequential swap semantics; establish graph-only readiness before model scheduling; make failures informative and preserve saved-check compatibility.

**Non-Goals:** change the GRU, optimizer, epochs, thread/device policy, training chunking, masks, metrics or benefit thresholds; introduce a new null-model sampler, prove mixing, infer graph benefit, run formal experiments, edit research records during apply, or modify historical evidence.

## Decisions

### 1. A versioned finite candidate budget with unchanged successful work

Use a new `dds-v2` identity with candidate `accept_factor=10`, `attempt_factor=500`, and fixed proposal batch size 4096. The initial candidate is chosen for margin over the observed sub-10% acceptance; it is not a measured guarantee. Freeze it only when all nine published members and independent regenerations pass. If any member cannot complete, retain failure and pause this candidate rather than silently raise the limit, reduce successful swaps, skip contexts or start training. Any subsequent candidate needs an explicit recorded design/version change before retesting the entire graph matrix.

Keep uniform ordered edge-index sampling, including proposals that will be rejected. Generate an integer `[4096,2]` buffer and consume each row in order. Validate each proposal against the current edge set and apply one accepted swap immediately. Buffer prefetch is not an attempt; count only consumed proposals and stop exactly on the `10E`th success. Test stream equivalence with the old scalar reference under the same budget, including a non-power-of-two edge count. This avoids changing the Markov transition through legal-only resampling or simultaneous swaps.

Initially retain tuple/set membership so the main optimization is isolated. Compare a bounded active-node boolean adjacency against that backend using identical proposal streams; adopt it only if measured runtime improves without changing decisions or excessive allocation. Active-node compaction must be a bijection restoring original node IDs and retaining all isolated nodes in artifact keys. No new compiler dependency or unsafe full-global adjacency is introduced.

### 2. Structured failure and periodic progress

Extend shuffle errors with JSON-safe diagnostics. At a bounded consumed-proposal interval (at most 100,000 proposals) and every context boundary, publish progress containing identities, context, accepted/attempted/target/limit, rejection categories and elapsed time. Keep successful context audits if a later context fails. The graph-preparation command and model runner save this payload on error before their terminal status. Atomic replacement is allowed only for an owned progress/status file; completed artifacts are immutable and exclusive.

Process interruption leaves an explicit interrupted state where catchable, otherwise a running marker that loaders classify as unfinished. No partial graph may be accepted for training. Checkpointing is diagnostic only; this change does not resume an interrupted swap chain from partial RNG state.

### 3. Explicit graph preparation and checking

Add public commands:

```text
prepare-shuffle --data-name r0 --shuffle-seed 0 --run-id <fresh-id> [--output-root <development-root>]
check-shuffle --artifact-dir <prepared-dir> --report <exclusive-external-json>
run ... --method shuffled --shuffle-seed 0 --shuffle-artifact <prepared-dir>
```

Use existing path validation, exclusive reservation, source capture and CPU environment recording. Preparation reads canonical dataset keys and validated source graph, never invokes model initialization, training or inference, and writes `nodes.npy`, `source-edges.npy`, `edges.npy`, `shuffle-audit.json`, generation provenance, byte-checksum manifest and final status. All numeric arrays load with `allow_pickle=False`. The artifact identity includes dataset, node-key hash, canonical source/result hashes, shuffle seed, algorithm version, budget, proposal batch identity and generator/environment provenance. Location is not part of the graph identity.

`check-shuffle` uses saved artifact contents only and writes one exclusive report outside the input. Recheck canonical uniqueness, valid endpoint bounds, no self-loop/cross-context, full per-node in/out degrees, all context/count/audit/hash contracts, changed-edge claims and checksum/status consistency. Existing shape-only or hash-only checking is insufficient. The checker cannot prove that an arbitrary forged artifact ran the algorithm; reproducibility comes from independent regeneration evidence.

### 4. Explicit immutable reuse instead of an implicit mutable cache

The optional `--shuffle-artifact` is resolved before training, permitted only for shuffled, and validated against the current canonical keys/source graph and requested seed/version. A bad artifact fails; there is no cache fallback or regeneration. Initial generation remains available when the option is omitted. Prepared-artifact paths may be shared across model seeds and repetitions; learned parameters and checkpoints may not be reused.

The runner writes its usual source and message edges and full audit into every run so recomputation never depends on the external artifact. Add generation provenance and hit/read duration as execution metadata. Separate semantic computational identity from artifact path, cache-hit flag and preparation timing, while retaining actual generator/code/environment identities; unknown or incompatible identities are rejected. Fixture runs from prepared and fresh paths must compare under the existing repeat tolerance and independently complete 200 epochs.

### 5. Strict version-aware checks and platform-correct tests

Introduce explicit recognized contracts for legacy `dds-v1` (`10E`, `100E`) and the new accepted version. Dispatch checks by saved version and validate its declared factors, seed derivation and audit schema; reject unknown versions and contradictory factors. Do not make historical v1 artifacts adopt v2 identities, loosen count checks, or change the generic 1e-12 recomputation and 1e-6 repeat tolerances.

Update only the two observed test assumptions: record/assert the complete real torch version and accept the pinned public version with legal CPU suffix; use existing normalized 1e-6 only for cross-batch-shape equivalence. Keep exact same-shape state reset, same-parameter isolated-node equality and empty-graph equality tests.

### 6. Readiness and pause handoff

Apply runs fixture tests first, then development graph-only probes starting with the previously failing r2/seed0 member, then all nine and independent regenerations in fresh directories. Save exact commands, runtime/source/data hashes, per-context audits, elapsed/peak-memory measurement method and a manifest of checks and matching regeneration hashes. Preserve graph-generation time separately from future cache-read/training cost. Do not make a speedup claim without comparable measurements.

The following are operational defaults for the research-side continuation, not training/scientific protocol changes:

- Any invariant, checksum, reproducibility, numerical-finiteness or environment identity failure stops scheduling immediately.
- During graph readiness, pause if one graph exceeds 10 minutes or 60 seconds pass without observable progress; retain failure/interruption evidence and report the actual stage. These watchdog times never enter RNG or accepted-swap identity.
- After implementation acceptance, measure fresh r0 and r2 model costs before scheduling the formal matrix. If measured progress projects more than 24 hours for the remaining local matrix, pause and report the estimate, inputs and uncertainty rather than automatically start a long batch. This estimate uses observed work and never treats node-count ratios as measured runtime.
- If resource pressure or user interruption occurs during a model run, stop safely and retain it as incomplete; a resumed attempt has a fresh ID and full 200 epochs. Do not count an interrupted fit as completed.
- Predictive quality is considered only at a complete dataset block (all methods, model seeds and repetitions, all 200 epochs and checked three-graph summaries). A complete block failing the unchanged P02 benefit gates is a conservative trigger to pause remaining datasets and inform the user; it is not a full-matrix conclusion. Do not tune/retrain from interim test scores or stop an epoch early because loss looks poor. If an aggregate is mathematically uninformative, report uncertainty rather than invent failure.

Apply/verification do not implement research batch scheduling or edit research records. Their handoff documents the controls above; research-side continuation wires them into a new batch after archived independent PASS. Existing failed batch `p02-t002-20261019-01` stays untouched.

## Risks / Trade-offs

- Low acceptance may persist → bounded candidate, all-member preflight, full failure audits and pause instead of an unbounded retry.
- Buffered NumPy sampling could change random-stream consumption → compare scalar and batched streams/decisions; version and record batch size; never promise v1 byte identity without evidence.
- Tuple membership may remain expensive → bounded benchmark of the optional active-node adjacency backend, with decision-by-decision equality oracle.
- Artifact reuse could bypass generation or obscure timing → strict graph/source/version validation, independent regeneration, self-contained run evidence and separate preparation/read costs.
- An unchanged edge set or high overlap may still occur → retain existing changed-edge failure and report overlap without claiming uniform mixing.
- Quality-based pause leaves an incomplete research matrix → explicitly report completed scope, preserve frozen gates, do not call T002/T003 done or generalize beyond the completed dataset.

## Migration Plan

1. Add new generation/version contracts, diagnostics, preparation/checking and reuse as an optional path; keep the old no-artifact CLI usable.
2. Validate fixtures and saved-check behavior, then generate the nine published graphs and independent copies in development storage.
3. Persist implementation notes and checks for independent verify and archive. Research-side acceptance then creates a new cost/batch identity and applies the pause policy.
4. Rollback means reverting the implementation/version default and abandoning the new prepared artifacts; original data and historical failed runs remain unchanged. Never mix v1/v2 members within one comparison or overwrite evidence.
