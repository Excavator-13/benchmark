## Why

The graph-based forecasting path cannot run from a fresh checkout and, even when its missing data loader is supplied externally, its EvolveGCN-H state handling and test-set model selection make the reported results unreliable. The repository needs one coherent repair that restores an executable data-to-metrics workflow while preserving the meaning of the published graph data and experiment controls.

## What Changes

- Provide a repository-owned graph dataset preparation and loading path for every shipped granularity (`r0`, `r1`, `r2`, `r1-region`, `r2-region`, `region`, and `company`) and both public CLI modes (`count` and `rate`).
- Resolve data paths relative to the repository, create generated-data directories, validate node/edge mappings, and construct lag/forecast snapshots with explicit edge weights.
- Preserve fully qualified graph endpoints and source-row multiplicity as explicit, aligned edge weights. The current Parquet files contain context identifiers plus endpoints but no documented frequency column, so the repair will not reinterpret occurrences across different contexts as co-occurrence frequency or invent unavailable values.
- Make EvolveGCN-H carry the GRU-produced weight state across snapshots, keep the learnable initial weight in autograd, and expose explicit sequence-state initialization so state cannot leak across epochs or dataset splits.
- Select checkpoints on validation loss, reserve the test split for one final evaluation, and use consistent device placement for every split.
- Honor the requested seed, seed all relevant random sources, and remove the hard-coded two-seed override.
- Save reconstructable `state_dict` checkpoints with configuration metadata and load them with an explicit device mapping.
- Align CLI help and README commands with the implementation, document the scope of `hidden_dim`, correct the environment setup command, and correct the temporal split contract.
- Add focused data, model-state, checkpoint, reproducibility, and smoke tests for the repaired graph forecasting workflow.

## Capabilities

### New Capabilities

- `graph-forecast-data-pipeline`: Prepare all shipped graph/time-series combinations and load validated, weighted temporal snapshots with configurable input and forecast lengths.
- `evolvegcn-h-recurrence`: Evolve graph-convolution weights recurrently within a sequence while preserving gradients and enforcing explicit state boundaries.
- `graph-forecast-experiments`: Run reproducible graph forecasting experiments with validation-only model selection, device-consistent execution, portable checkpoints, and accurate CLI/documentation contracts.

### Modified Capabilities

None. The project has no existing OpenSpec capabilities.

## Impact

- Affected implementation: `benchmark/graph_method/data_process.ipynb`, a repository-owned preprocessing entry point and dataset loader under `benchmark/graph_method/`, `benchmark/graph_method/models/evolvegcnh.py`, and `benchmark/graph_method/main.py`.
- Affected data contract: generated graph JSON gains explicit edge weights and qualified endpoint semantics while retaining the existing `count`/`rate` CLI vocabulary and all seven dataset names.
- Affected artifacts: result checkpoints become parameter/configuration payloads rather than pickled model objects; previously generated `model.pt` files are not assumed to be forward-compatible.
- Affected documentation and tests: graph-running instructions in `README.md` and new focused tests for the graph method.
- No new runtime dependency is required beyond packages already listed in `requirements.txt`; test tooling should use the standard library where practical.
