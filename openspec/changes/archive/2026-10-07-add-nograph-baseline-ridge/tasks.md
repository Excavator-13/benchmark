## 1. Implementation

- [x] 1.1 Add `benchmark/nograph_baseline/` package, stable run/check subcommands and local NumPy/pandas/PyArrow dependency list; verify public help, supported r0/region count choices, safe run IDs and module-relative default paths without graph imports.
- [x] 1.2 Implement canonical demand loading and audits; verify shuffled synthetic Parquet preserves key/value alignment and rejects duplicate/invalid IDs, missing/extra months and negative/nonfinite values.
- [x] 1.3 Implement the fixed calendar/window metadata and split assertions; verify 28 starts, train 0..18, validation 21, test 24..27, omissions 19/20/22/23 and pairwise-disjoint target-month sets.
- [x] 1.4 Implement frozen per-node training statistics and activity/constant masks; verify exactly 27 unique observations, ddof=0, effective std=1 for constant nodes, all four fixed boundaries and invariance to post-March-2023 values.
- [x] 1.5 Implement all five naive methods and frozen NaiveRef/NaiveRef6 selection; verify validation MSE/table-order ties, per-target last-year seasonal values, extra-history labeling and frozen TrainMean27 behavior.
- [x] 1.6 Implement pure NumPy SharedRidge fitting and inverse transformation; verify one W[6,3]/b[3], M=19*N, unregularized intercept and the protocol mean-loss objective on an independently calculated small numerical fixture.
- [x] 1.7 Implement validation-only lambda selection and optional lazy sklearn backend; verify all five validation MSE/MAE records, larger-lambda ties, alpha=lambda*M metadata, absence of test labels in selection and separate optional clipped reports.
- [x] 1.8 Implement evaluation-only context-qualified non-self coverage and provenance-bearing mask loading; verify exact identity alignment, both endpoint coverage, self-loop exclusion, unmatched-endpoint errors and unchanged predictions when only coverage annotations change.
- [x] 1.9 Implement original-unit metrics and diagnostic contributions; verify global/window/horizon/context/activity/neighbor metrics, counts, empty groups, training-all-zero reporting, negative ratio, equal-weight activity MAE, zero-reference gain handling and complete per-node error tables.
- [x] 1.10 Implement versioned artifact writing and source capture; verify protocol/config/command/hash/environment/code-diff/untracked-source capture, numeric arrays readable with allow_pickle=False, canonical identities and reconstructable parameters under the specified layout.
- [x] 1.11 Implement isolated CPU execution, stage timing, normalized process peak RSS and failure/interruption handling; verify measured durations/memory units, saved execution settings, exclusive run creation, retained partial files and incomplete hard-termination state.
- [x] 1.12 Implement saved-run recompute, same-seed comparison and v2 JSON-line alignment commands; verify each writes a new check-type run, hashes its inputs, preserves input runs and reports differences and diagnostic identity-evidence limits.
- [x] 1.13 Add minimal README commands for the CPU environment, both datasets, repetition and saved-result checks; verify examples match help and require neither root CUDA requirements nor generated graph data, and document unsealed/unbacked-up output status.

## 2. Self-Tests

- [x] 2.1 Run the data/window unittest suite on synthetic r0 and region fixtures; retain test output proving canonical identity, rolling true-history inputs, all omitted starts and split target isolation without production graph files.
- [x] 2.2 Run adversarial preprocessing tests where target-only and overlap-weighted estimates differ; retain evidence that means/std/masks use unique training months and constant nodes remain finite.
- [x] 2.3 Run fitting/selection tests with conflicting validation MAE/MSE winners, exact ties and changed test labels; retain evidence of shared objective correctness, alpha scaling and no test-driven selection or refitting.
- [x] 2.4 Run analytic metric fixtures and saved-only recomputation with source-file access disabled; retain evidence for non-averaged overall RMSE, all group/horizon/context reports, contributions, gains and all methods' common masks.
- [x] 2.5 Run a minimal three-dependency environment smoke test with imports of sklearn/PyTorch/PyG/DGL and graph-method modules blocked; verify import/help and full fixture runs for both dataset schemas succeed on CPU with injected fixture coverage masks and no repository graph data.
- [x] 2.6 Run end-to-end artifact/failure tests including existing-ID rejection, malformed source, SIGINT/SIGTERM and unfinished status; retain logs showing fresh outputs, preserved partial artifacts and no changes to fixtures or prior runs.
- [x] 2.7 Run two independent same-seed fixture executions and the compare command; retain matching identity/config/selection records, prediction maximum absolute differences and protocol CPU relative-MAE checks at <=1e-6 without seed-variance reports.
- [x] 2.8 Verify `job-sdf-baseline` actually reads Parquet and record Python/package versions; run the complete CPU unittest suite and, if sklearn is installed, the optional backend equivalence test, reporting optional-test skips explicitly without requiring sklearn for the default path.

## 3. Formal Dataset Runs and Saved Evidence

These tasks run only after implementation/self-tests. Each task writes exclusively to fresh `research/runs/<run_id>/` directories; no prior research record, sealed run, index or main spec is edited. Choose unused run IDs and preserve failed/interrupted attempts. No task packages, commits, pushes or uploads artifacts.

- [x] 3.1 Execute one formal `r0/count` CPU run at seed 0 with the NumPy backend; verify success and all required snapshots/provenance/identities, five naive reports, selected SharedRidge, saved predictions/labels/masks/parameters and measured read/fit/inference durations and peak memory.
- [x] 3.2 Execute an independent `r0/count` same-seed repetition in a fresh directory under identical conditions; verify a complete second formal artifact set and matching source/protocol/configuration/environment identities.
- [x] 3.3 Recompute r0 primary and repetition metrics from saved outputs only and compare their predictions/metrics in fresh check runs; verify all metric levels, maximum absolute prediction difference and the CPU <=1e-6 agreement criterion, retaining any disagreement investigation.
- [x] 3.4 Align r0 naive outputs/identity evidence/splits against immutable v2 JSON lines in a fresh check run; verify both references remain LastValue for unchanged sources, all compared fields/tolerances are recorded and every discrepancy is explained without editing legacy evidence.
- [x] 3.5 Execute one formal `region/count` CPU run at seed 0 with the NumPy backend; verify success and the complete required artifact set, all five naive methods, selected SharedRidge, frozen masks and actual stage/memory measurements.
- [x] 3.6 Execute an independent `region/count` same-seed repetition in a fresh directory under identical conditions; verify a complete second formal artifact set and matching source/protocol/configuration/environment identities.
- [x] 3.7 Recompute region primary and repetition metrics from saved outputs only and compare predictions/metrics in fresh check runs; verify all metric levels, maximum absolute prediction difference and the CPU <=1e-6 agreement criterion, retaining any disagreement investigation.
- [x] 3.8 Align region naive outputs/identity evidence/splits against immutable v2 JSON lines in a fresh check run; verify both references remain LastValue for unchanged sources, all comparisons/findings are preserved and no diagnostic time is presented as the new entry's measured cost.

## 4. Independent Verification Preparation

- [x] 4.1 Write `implementation.md` in this change directory with changed file paths, test commands/results, both formal/repeat run IDs, check-run paths, hashes, measured environment/costs and limitations; verify every claim links to retained evidence and no scientific acceptance or independent PASS is asserted.
- [x] 4.2 Map every delta requirement/scenario to implementation and test/run evidence in the implementation notes; verify an independent reviewer can locate saved-only metric checks, selection leakage tests, two-dataset completeness and any remaining findings without chat history.
- [x] 4.3 Check the implementation/run write scope and prepare the handoff; verify graph-method source, existing research records, legacy archives, DELEGATION.md and main specs are unchanged, all run writers have exited, and sealing/backup/research acceptance remain explicitly pending outside this change. Do not run independent verification as part of this task.
