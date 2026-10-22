# Proposal

## Why

P02-T002 is blocked before r2 training: context 12 exhausted `100E` proposals before completing the required `10E` accepted swaps. The current Python loop allocates a NumPy pair on every attempt, discards rejection diagnostics on failure, and rebuilds identical shuffled graphs for every model execution.

## What Changes

- Introduce a versioned, finite shuffle budget, initially testing `500E` attempts while retaining exactly `10E` successful swaps per nonempty context; require all nine published dataset/shuffle-seed combinations to pass before accepting the candidate.
- Generate proposals in fixed batches and consume them sequentially against the evolving adjacency, retaining uniform edge-pair proposals, rejection rules and directed-degree invariants.
- Save structured failure/progress audits and provide graph-only preparation/checking, so all controls can be validated before any model training.
- Add immutable prepared shuffle artifacts that compatible model executions can reuse; retain independent training for every model seed and repetition.
- Verify same-seed regeneration and fixture/cached-run equivalence; align CPU-version suffix and cross-batch float32 tests with existing contracts.
- Document actionable pause conditions and evidence handoff without adding training early stopping or changing scientific thresholds.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `graph-value-skeleton`: Versioned finite shuffle execution, recoverable failure diagnostics, graph-only preparation and checked artifact reuse, with real published-graph readiness evidence.

## Impact

Changes concern `benchmark/graph_value_skeleton/{shuffle,protocol,cli,runner,checks,artifacts}.py`, configuration as needed, their tests, and the existing README chapter. Use the current pinned CPU runtime with no additional graph/GPU/compiler dependency. OpenSpec 1.14.3 is installed only in ignored `scratch/t002-tools/openspec-cli`; the global installation stays untouched.

The implementation workflow may generate development graph artifacts and fixture evidence, but does not run the formal 90-model matrix or edit research records. Research-side acceptance and cost confirmation follow independent verification and archive. Preserve historical failed runs, scientific settings, 200 epochs, three-graph arithmetic mean, CPU repeat tolerance, all nodes/masks and P01 compatibility. The user's conditional pause request is retained in D026 and must be carried into the research-side resumption.
