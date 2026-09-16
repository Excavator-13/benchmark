## Context

See `proposal.md` for motivation and the three capability specs for behavioral contracts. The graph path currently consists of one notebook, a monolithic `main.py`, and a local EvolveGCN-H layer. `main.py` imports a nonexistent `dataset` module. The notebook assumes nonexistent `dataset/rate` and `dataset/count` directories, processes only `company`, and writes below a directory it does not create. The shipped time-series directories are `dataset/proportion` and `dataset/demand`; all seven names are present in those directories and in `dataset/graph`.

The shipped graph Parquet schemas contain the granularity's context ID columns plus `row_id` and `col_id`; they do not contain a `frequency` or `weight` column. Consequently, row multiplicity can be preserved, but a cross-context count cannot safely be labeled source co-occurrence frequency. This distinction matters for compound granularities, where the same skill pair under different context IDs represents different graph nodes.

The repository pins Python 3.8-era PyTorch and PyTorch Geometric packages but has no test configuration, and those packages are not installed in the current planning environment. The implementation must therefore be verified later in the pinned environment; this design does not infer unobserved library behavior from a live runtime.

## Goals / Non-Goals

**Goals:**

- Define stable data and checkpoint formats that fail early on incompatible or malformed input.
- Keep temporal state ownership visible in the sequence runner so train, validation, and test boundaries are reviewable.
- Make the default documented `r0`/`rate`/`EvolveGCNH` workflow executable from a fresh checkout while retaining all currently advertised graph models.
- Add tests at data-contract, model-state, experiment-loop, and end-to-end smoke levels.

**Non-Goals:**

- Reconstruct a true co-occurrence frequency field that is absent from the shipped Parquet schema.
- Change the source Parquet files, forecasting metrics, default split ratios, or published benchmark values.
- Redesign third-party recurrent layers or make `hidden_dim` alter EvolveGCN-H's paper-defined square graph-convolution weight dimension.
- Guarantee bit-for-bit equality across different hardware, CUDA, driver, or dependency versions.

## Decisions

### 1. Put preprocessing logic in a testable Python entry point

Add an importable CLI module under `benchmark/graph_method/` and reduce `data_process.ipynb` to a thin documented caller of that module. Repository and output paths derive from the module location, not the process working directory. The CLI accepts a subset or defaults to all seven granularities and both modes, with `count -> dataset/demand` and `rate -> dataset/proportion`. It creates `benchmark/graph_method/data/<mode>/` before writing.

Each generated JSON document uses an explicit version and fields equivalent to:

```json
{
  "schema_version": 1,
  "data_name": "r0",
  "mode": "rate",
  "node_keys": [[0, 12]],
  "features": [[0.1]],
  "edges": [[0, 1]],
  "edge_weights": [1.0]
}
```

`node_keys` are ordered arrays of all context IDs followed by the skill ID; arrays avoid delimiter collisions in composite string keys. Time columns are recognized and chronologically sorted, producing a time-by-node `features` matrix. Graph endpoints are built from the same context IDs plus `row_id` or `col_id`.

Exact duplicate fully qualified directed rows may be grouped into one edge with weight equal to the row count. Reverse directions and rows belonging to different context IDs remain separate. This preserves source adjacency multiplicity without repeating the existing analysis mistake of dropping context columns before grouping. If a future source adds a documented weight column, supporting it requires a deliberate schema update rather than guessing its name.

Alternative considered: load Parquet directly in training and remove preprocessing. This would reduce generated files, but it would leave the requested preprocessing workflow unresolved and couple every experiment startup to expensive Parquet conversion. A testable preparer plus versioned artifact keeps responsibilities separate.

### 2. Add a repository-owned temporal graph loader

Add `benchmark/graph_method/dataset.py` with a loader that resolves the versioned JSON for the requested mode and granularity, validates it, and creates the temporal signal type expected by the pinned graph library. Change the call to accept both `lags` and `pred_length`.

For time index `t`, a snapshot uses `features[t:t+lags]` transposed to `[nodes, lags]` and targets `features[t+lags:t+lags+pred_length]` transposed to `[nodes, pred_length]`. This yields `T - lags - pred_length + 1` snapshots. Static edge indices and weights are reused across snapshots. Validation covers positive lengths, sufficient history, finite values, node-key uniqueness, endpoint membership during preparation, index bounds, and edge/weight alignment.

Alternative considered: keep the loader's current one-argument call and hard-code a three-step target. That would continue to make `--pred_length` misleading and fail for any non-default horizon.

### 3. Make EvolveGCN-H weight state an explicit value

Change the local layer contract conceptually to:

```python
output, next_weight = layer(x, edge_index, edge_weight, previous_weight)
```

When `previous_weight` is `None`, the layer passes the registered `initial_weight` parameter directly to the GRU; it never uses `.data` or `detach()`. Otherwise it passes the prior snapshot's returned weight. The layer does not retain `self.weight`. The experiment wrapper carries `next_weight` through a traversal and discards it at the traversal boundary.

This design deliberately does not register the evolved weight as a parameter or persistent buffer. It is sequence-local activation state, contains an autograd history during training, and should not enter `state_dict`. Only the learnable initial weight and module parameters belong in checkpoints.

Alternative considered: retain a mutable `self.weight` and add reset/save hooks, as in the reference copy under `evolvegcn_in_torch-geometric-temporal/`. That API is easy to call incorrectly, can retain a freed autograd graph across epochs, can leak validation state into testing, and still makes model serialization semantics ambiguous.

### 4. Centralize split traversal and state boundaries

Refactor `main.py` behind a `main()` guard into configuration, model construction, snapshot movement, split traversal, checkpoint, and metric functions. A single split runner moves every snapshot tensor to the selected device, initializes model state once, processes snapshots chronologically, and returns aggregate loss plus optional predictions/targets. Training enables gradients and performs one optimizer step per epoch; validation and testing use evaluation mode and no gradients.

Every training epoch, validation pass, and final test pass starts with empty recurrent state. EvolveGCN-H then carries weight only within that pass. Existing hidden/cell state models continue to carry their state through the same normalized runner. For third-party EvolveGCN-O, call its public reset hook at each traversal boundary if its API retains internal weight state.

Validation is run after each training epoch and solely controls the best checkpoint. No test iterator is created or traversed inside the epoch loop. After training, reconstruct the best model and traverse test exactly once to produce predictions, gold tensors, RMSE, and MAE. Each partition must contain at least one snapshot.

Alternative considered: warm validation and test state by replaying earlier splits. Although defensible for some online protocols, the present windows already contain lag history, and replay introduces a second evaluation protocol not described by this benchmark. Independent split initialization is simpler, prevents accidental state leakage, and matches the specs.

### 5. Treat one invocation as one seeded experiment

Remove the outer `range(2)` loop. Before dataset iteration and model construction, seed `random`, NumPy, PyTorch CPU, and all available CUDA generators. Configure deterministic backend behavior where supported and report unsupported deterministic operations clearly. The requested seed remains unchanged and determines the result directory.

Multiple-seed studies should invoke the program repeatedly from an external script. Adding a second `--num_runs` control was rejected because it is unnecessary to repair the current contract and would complicate result caching and seed derivation.

### 6. Store parameters and reconstruction metadata, not Python objects

Write a checkpoint payload containing a format version, `model_state_dict`, architecture-defining configuration (`model_name`, node/input dimensions, `hidden_dim`, window size, prediction length), and experiment metadata such as seed and best validation loss. Restore by validating metadata, reconstructing the model, loading its state dictionary, and passing the requested device as `map_location`.

Use a new checkpoint filename such as `checkpoint.pt`; do not overwrite or attempt to transparently migrate legacy pickled `model.pt` files. Completed legacy result directories must produce an actionable incompatibility message or be rerun explicitly. Metrics and prediction filenames remain stable.

Alternative considered: keep `torch.save(model)` and only add `map_location`. That fixes one device symptom but preserves dependency on the original Python module path and bypasses explicit configuration validation.

### 7. Keep the CLI stable and make documentation truthful

Retain `--model_name` as the canonical graph CLI option and update the README's graph example to use it. Keep `--hidden_dim` because several other supported models consume it, but state in help and documentation that EvolveGCN-H and EvolveGCN-O derive their convolution dimension from `window_size`. Correct the Conda command to `conda create -n Job-SDF python=3.8`, document the preprocessing CLI, and fix the split helper's argument/return documentation.

Update the dataset description to match the observed graph schema: context-qualified endpoint rows, with no standalone frequency column in the shipped files. Describe generated edge weights as preserving fully qualified row multiplicity, not as recovered source frequencies.

Adding `--model` as a second alias was considered but rejected: no released graph implementation currently accepts it, and correcting the sole misleading README example avoids maintaining two spellings.

### 8. Disposition of the reported issues

| # | Decision | Design response |
|---|---|---|
| 1 | Fix | Add the missing repository-owned dataset loader and import-safe entry point. |
| 2 | Fix | Map public modes to `demand`/`proportion` and use module-relative paths. |
| 3 | Fix | Default preprocessing covers all seven shipped granularities. |
| 4 | Fix | Create generated-data parent directories before writes. |
| 5 | Fix | Return and carry the GRU-produced weight across snapshots. |
| 6 | Fix | Pass `initial_weight` through autograd without `.data`. |
| 7 | Fix | Use validation loss, never test loss, for checkpoint selection. |
| 8 | Fix | Traverse the existing validation split every epoch. |
| 9 | Fix | Use one device-placement path for train, validation, and test. |
| 10 | Fix | Honor one requested seed and initialize every relevant random source. |
| 11 | Reframe and fix contract | The claimed frequency field is absent and cross-context repetitions are not valid proof of frequency. Preserve fully qualified row multiplicity explicitly and correct the README instead of fabricating values. |
| 12 | Fix | Remove mutable model-owned evolved state; keep sequence state explicit and transient. |
| 13 | Fix | Save versioned state-dictionary payloads and load with `map_location`. |
| 14 | Fix | Document the implemented `--model_name` option consistently. |
| 15 | Fix | Correct the Conda environment command. |
| 16 | Clarify | Retain `hidden_dim` for models that use it and explicitly mark it inapplicable to EvolveGCN variants. |
| 17 | Fix | Correct the split helper documentation to three iterators and both ratios. |

## Risks / Trade-offs

- [Grouping exact duplicate directed rows changes storage shape] -> Test numerical equivalence between repeated unit edges and the chosen grouped representation under the pinned graph convolution; retain repeated entries if equivalence is not guaranteed.
- [Legacy generated JSON lacks schema and edge weights] -> Reject it with a regeneration command rather than silently defaulting values.
- [Legacy full-object checkpoints cannot use the new loader] -> Keep them untouched, use a new filename, and require an explicit rerun for reproducible results.
- [Full-sequence backpropagation retains recurrent state history] -> The dataset has a short monthly timeline; monitor memory in smoke tests and only introduce truncated backpropagation as a separately specified change if needed.
- [CUDA kernels can remain nondeterministic] -> Enable supported deterministic controls, record device/dependency context, and scope reproducibility assertions to supported configurations and numerical tolerance.
- [Refactoring the shared runner can regress less-used model branches] -> Add parametrized or table-driven shape/state smoke coverage for each advertised model whose pinned dependency implementation is available.
- [Notebook JSON edits are hard to review] -> Keep all logic in the Python module and make the notebook contain only a minimal call plus visible instructions.

## Migration Plan

1. Add the preparer, loader, and data-contract tests; generate one small synthetic artifact and then smoke-check the shipped default combination.
2. Introduce explicit EvolveGCN-H state and its gradient/state-boundary tests before switching the experiment loop.
3. Refactor training, validation, testing, device movement, seeding, and checkpoint handling; verify CPU behavior, then CUDA when available.
4. Update the notebook and README only after their commands match the tested entry points.
5. Regenerate graph JSON artifacts with schema version 1. Leave old unversioned generated files and `model.pt` checkpoints untouched until the user explicitly removes them.
6. Rollback consists of reverting code/document changes and selecting the prior artifact paths; source Parquet data and existing result files are never mutated by the migration.
