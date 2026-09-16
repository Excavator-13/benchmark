# Implementation Verification

- Change: repair-graph-forecasting-pipeline
- Schema: spec-driven
- Verdict: BLOCKED
- Verified revision: `107bceee73823d7d68f497299e1a8fa0a80ac2ba` (implementation worktree was clean before this report; this report is the verifier's only change)

## Summary

OpenSpec validation and all 32 standard-library preparation/notebook tests pass. Source and test inspection found implementation paths for every normative scenario and no confirmed implementation deviation. Independent verification cannot reach a reliable overall verdict because the available Python 3.9.6 runtime has none of NumPy, PyTorch, PyArrow, or the PyTorch graph packages; no documented `.venv-graph`/`.venv-pinned` environment or generated graph artifacts are present. Consequently the loader, recurrence, experiment, checkpoint, real-data integration, CPU smoke, and conditional CUDA evidence could not be executed against the current revision.

The repository's `MACOS_SETUP.md` describes earlier results, but its referenced `not_in_origin/graph_method_apply_acceptance.md` is absent. Those historical claims are not treated as current independent evidence.

## Checks

| Command or inspection | Result | Notes |
| --------------------- | ------ | ----- |
| `openspec status --change "repair-graph-forecasting-pipeline" --json` | PASS | Schema `spec-driven`; all four artifacts complete. |
| `openspec instructions apply --change "repair-graph-forecasting-pipeline" --json` | PASS | 16/16 tasks checked; all declared context files loaded. |
| `openspec validate "repair-graph-forecasting-pipeline" --type change --strict --json --no-interactive` | PASS | One change validated with zero issues. |
| `git status --short --branch` and `git rev-parse HEAD` | PASS | Implementation worktree clean at `107bceee73823d7d68f497299e1a8fa0a80ac2ba` before report creation. |
| `python3 -m unittest benchmark/graph_method/tests/test_prepare_graph_data.py -v` | PASS | 32/32 tests pass, including root/alternate-CWD CLI checks, path mapping, schema generation, error handling, multiplicity, and notebook delegation. |
| `python3 -m unittest discover -s benchmark/graph_method/tests -v` | BLOCKED | 32 tests pass; four test modules fail during collection because `numpy` and `torch` are missing. |
| Active/interpreter environment inspection | BLOCKED | System Python 3.9.6 lacks NumPy; Conda base lacks PyArrow and the graph stack; other registered Conda environments lack PyTorch/PyArrow/graph dependencies. No project virtual environment exists. |
| Real-data integration and all-14-artifact inspection | BLOCKED | `benchmark/graph_method/data` is absent and the runtime cannot read Parquet or construct temporal graph signals. |
| One-epoch CPU smoke and conditional CUDA smoke | BLOCKED | `benchmark/graph_method/results` is absent; PyTorch is unavailable, so CPU execution and CUDA availability cannot be checked. |
| Implementation/test/documentation inspection | PASS (static) | Relevant paths and focused tests exist; static shape alone is not sufficient executable evidence for blocked scenarios below. |

## Requirement Coverage

| Requirement / scenario | Evidence | Result |
| ---------------------- | -------- | ------ |
| EvolveGCN-H recurrence / First snapshot uses learned initial state | `models/evolvegcnh.py:116-123`; focused test at `tests/test_evolvegcnh.py:53` | BLOCKED: test cannot import PyTorch. |
| EvolveGCN-H recurrence / Later snapshot uses prior evolved state | Explicit `previous_weight` path at `models/evolvegcnh.py:95-123`; two-snapshot test at `tests/test_evolvegcnh.py:67` | BLOCKED: test cannot import PyTorch. |
| Initial weight trainability / Backpropagation reaches initial weight | Registered parameter at `models/evolvegcnh.py:56`; gradient test at `tests/test_evolvegcnh.py:117` | BLOCKED: test cannot import PyTorch. |
| Explicit boundaries / State carries within one traversal | `main.py:538-584` initializes once and threads state; runner test at `tests/test_main.py:431` | BLOCKED: test cannot import runtime dependencies. |
| Explicit boundaries / State resets between traversals | `main.py:430-458` and fresh `run_split` state; reset test at `tests/test_main.py:441` | BLOCKED: test cannot import runtime dependencies. |
| Device-following state / CUDA sequence execution | Snapshot movement at `main.py:527-535`; CUDA tests at `tests/test_evolvegcnh.py:206` and `tests/test_main.py:380` | BLOCKED: PyTorch/CUDA runtime unavailable. |
| All combinations / Prepare default from fresh checkout | Module-relative mapping and directory creation at `prepare_graph_data.py:150-164,326-346`; synthetic creation test passed | BLOCKED: real `r0/rate` Parquet preparation and load could not run. |
| All combinations / Prepare every supported combination | CLI defaults at `prepare_graph_data.py:383-391`; opt-in integration test at `tests/test_generated_datasets.py:121` | BLOCKED: PyArrow/graph runtime and generated artifacts unavailable. |
| All combinations / Reject unsupported names | Passing CLI/programmatic tests at `tests/test_prepare_graph_data.py:59-83` | PASS. |
| Source semantics / Context-qualified endpoints remain distinct | Passing compound/single-context tests at `tests/test_prepare_graph_data.py:252-281` | PASS. |
| Source semantics / Exact source multiplicity is not discarded | Passing duplicate-row test at `tests/test_prepare_graph_data.py:245`; grouping at `prepare_graph_data.py:268-301` | PASS. |
| Source semantics / Snapshot exposes aligned weights | Loader constructs aligned arrays at `dataset.py:292-320`; loader test at `tests/test_dataset.py:291` | BLOCKED: loader test cannot import NumPy/graph runtime. |
| Temporal windows / Construct multi-step forecast sample | Formula at `dataset.py:248-289`; shape/count tests at `tests/test_dataset.py:46-73` | BLOCKED: loader test cannot import NumPy/graph runtime. |
| Temporal windows / Reject impossible window | Validation at `dataset.py:240-262`; tests at `tests/test_dataset.py:76-94` | BLOCKED: loader test cannot import NumPy/graph runtime. |
| Integrity / Graph endpoint has no matching signal node | Passing unmatched-endpoint test at `tests/test_prepare_graph_data.py:311`; check at `prepare_graph_data.py:286-295` | PASS. |
| Integrity / Generated edge and weight counts differ | Validation at `dataset.py:185-197`; test at `tests/test_dataset.py:117` | BLOCKED: loader test cannot import runtime dependencies. |
| Chronological roles / Validation improvement saves checkpoint | Validation-only branch at `main.py:779-791`; instrumented test at `tests/test_main.py:513` | BLOCKED: experiment test cannot import runtime dependencies. |
| Chronological roles / Final test isolated from selection | Test traversal after restore at `main.py:795-804`; access-count tests at `tests/test_main.py:480-555` | BLOCKED: experiment test cannot import runtime dependencies. |
| Chronological roles / Empty split rejected | Split validation at `main.py:305-327`; tests at `tests/test_main.py:304-343` | BLOCKED: experiment test cannot import runtime dependencies. |
| Configured device / Requested CUDA completes consistently | Central movement at `main.py:527-584`; CUDA runner/checkpoint tests exist | BLOCKED: no CUDA-capable PyTorch environment. |
| Configured device / Unavailable device fails early | `main.py:243-263`; tests at `tests/test_main.py:976-1000` | BLOCKED: experiment module cannot import in the available runtime. |
| Single seed / Requested seed honored | Single config/run and seed-keyed path at `main.py:266-275,713-718,749-818`; test at `tests/test_main.py:668` | BLOCKED: experiment test cannot import runtime dependencies. |
| Single seed / Identical deterministic CPU runs | Determinism setup at `main.py:278-291`; repeated-run test at `tests/test_main.py:680` | BLOCKED: no PyTorch CPU runtime. |
| Portable checkpoints / Restore on another device class | State-dict payload and explicit `map_location` at `main.py:616-705`; CPU/CUDA tests at `tests/test_main.py:717-772` | BLOCKED: no PyTorch runtime or CUDA device. |
| Portable checkpoints / Configuration mismatch reported | Config comparison at `main.py:680-695`; mismatch test at `tests/test_main.py:774` | BLOCKED: checkpoint tests cannot import PyTorch. |
| Public contract / Follow documented graph workflow | README commands at `README.md:105-155`; preparation help/subset tests pass | BLOCKED: documented training command and real preprocessing cannot execute without dependencies. |
| Public contract / Inspect EvolveGCN-H CLI help | Parser uses `--model_name` and scopes `hidden_dim` at `main.py:147-214`; README agrees | BLOCKED: `main.py --help` imports missing runtime dependencies before parsing. |

## Findings

### V-001: Graph runtime dependencies are unavailable for verification

- Category: environment
- Severity: high
- Requirement: All EvolveGCN-H recurrence scenarios; loader/runtime portions of graph-forecast-data-pipeline; all graph-forecast-experiments execution scenarios
- Evidence: `python3 -m unittest discover -s benchmark/graph_method/tests -v` passes the 32 standard-library tests but reports four collection errors: `ModuleNotFoundError: No module named 'numpy'` for dataset/main/integration tests and `No module named 'torch'` for recurrence tests. Environment probes found no installed interpreter containing NumPy, PyArrow, PyTorch, PyTorch Geometric, and PyTorch Geometric Temporal together. The documented project virtual environments and generated data/results directories are absent.
- Expected: The focused graph suite, real-data checks for all fourteen combinations, one-epoch CPU smoke, and conditional CUDA checks execute against the current revision in a compatible dependency environment.
- Actual: Only the standard-library preparation/notebook subset can execute, leaving core behavior without current executable evidence.
- Repair guidance: Recreate or provide the path to a compatible environment described in `MACOS_SETUP.md`; then rerun the complete focused suite, opt-in shipped-data integration, one-epoch CPU smoke, and CUDA checks when CUDA is available. No implementation change is prescribed by this finding.
- Acceptance checks: `.venv-pinned/bin/python -m pytest benchmark/graph_method/tests -q`; `JOB_SDF_INTEGRATION=1 .venv-pinned/bin/python -m unittest discover -s benchmark/graph_method/tests -p "test_generated_datasets.py"`; `.venv-pinned/bin/python benchmark/graph_method/main.py --data_name r0 --mode rate --model_name EvolveGCNH --num_epochs 1`; rerun the CUDA-marked tests on CUDA or record their explicit skip reason.
- Repair status: blocked
- Repair notes: None.
- Reverification notes: First verification run. Resume once a compatible graph runtime is available; preserve this finding ID.
