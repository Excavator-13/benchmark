## 1. Data Preparation and Loading

- [x] 1.1 Add an importable graph-data preparation CLI with the seven supported granularities, `count -> demand` and `rate -> proportion` mappings, module-relative repository paths, and automatic output-directory creation; verify CLI validation and path behavior with standard-library unit tests run from both the repository root and another working directory.
- [x] 1.2 Implement versioned JSON generation with ordered context-qualified node keys, chronological finite feature values, mapped directed edges, and aligned weights that preserve exact fully qualified row multiplicity; verify synthetic tests cover compound-context separation, duplicate rows, reverse edges, missing columns, duplicate nodes, and unmatched endpoints.
- [x] 1.3 Add `benchmark/graph_method/dataset.py` to validate generated schema version 1 and construct static weighted temporal snapshots from `lags` and `pred_length`; verify tests assert snapshot count and `[nodes, lags]`/`[nodes, pred_length]` shapes plus failures for invalid windows, indices, values, and edge/weight lengths.
- [x] 1.4 Replace the notebook's hard-coded transformation with a thin call to the tested preparer and run the preparer against the shipped `r0` `rate` data from a clean generated-data directory to verify the default artifact is created and loadable.

## 2. EvolveGCN-H Recurrence

- [x] 2.1 Refactor the local EvolveGCN-H layer to accept an optional previous weight and return the next weight without storing mutable `self.weight` or using `.data`; verify a two-snapshot unit test proves the second GRU call receives the first call's evolved weight.
- [x] 2.2 Preserve the registered initial-weight parameter as the first recurrent state and verify backpropagation produces a finite non-null gradient for it while `state_dict` contains learned parameters but no transient evolved weight.
- [x] 2.3 Add CPU and conditional CUDA tests for explicit recurrent-state device placement and independent traversal initialization; verify state carries within a traversal but a new traversal begins from the initial parameter.

## 3. Experiment Lifecycle

- [x] 3.1 Refactor `benchmark/graph_method/main.py` behind a `main()` guard with testable argument parsing, model construction, and validated three-way chronological splitting, and pass both window and prediction lengths to the loader; verify imports have no training side effects and split tests cover non-empty and invalid partitions.
- [x] 3.2 Implement one shared split runner that moves every snapshot tensor to the configured device and carries each model's state only within the split, including resetting third-party EvolveGCN-O where supported; verify mocked CPU/CUDA placement tests and per-model shape/state smoke tests cover every advertised graph model available in the pinned environment.
- [x] 3.3 Change the epoch loop to train only on the training split and checkpoint only on validation loss, then restore the best checkpoint and traverse test once for predictions, gold values, RMSE, and MAE; verify an instrumented test records validation accesses during selection and zero test accesses before final evaluation.
- [x] 3.4 Remove the hard-coded two-seed loop and seed Python, NumPy, PyTorch CPU, and available CUDA generators before model construction; verify `--seed 17` executes one result directory and repeated deterministic CPU test runs match within the declared tolerance.
- [x] 3.5 Replace full-model serialization with a versioned `checkpoint.pt` payload containing `model_state_dict`, reconstruction configuration, seed, and best validation loss, loaded with explicit `map_location`; verify round-trip, cross-device mapping, incompatible-configuration, and legacy-`model.pt` error-path tests.

## 4. Documentation and End-to-End Verification

- [x] 4.1 Update CLI help, the temporal split docstring, and `README.md` to use `--model_name`, explain model-specific `hidden_dim` applicability, correct the Conda command, document the preparation CLI, and describe the observed context-qualified graph schema without claiming a frequency column; verify every documented graph command is accepted with `--help` or a no-training validation path.
- [x] 4.2 Run the complete graph-method unit suite in the pinned dependency environment and verify data-contract, recurrence, selection-isolation, device, seed, and checkpoint tests all pass without modifying source Parquet files or legacy results.
- [x] 4.3 Generate all fourteen shipped granularity/mode artifacts, load each with the default window and prediction lengths, and verify every artifact passes schema/integrity checks and yields non-empty train, validation, and test splits.
- [x] 4.4 Run a one-epoch CPU smoke experiment for the documented default `r0`/`rate`/`EvolveGCNH` command and verify it writes a validation-selected checkpoint, final test predictions/golds, and finite RMSE/MAE; additionally run the same smoke check on CUDA when available and record an explicit skip when it is not.
