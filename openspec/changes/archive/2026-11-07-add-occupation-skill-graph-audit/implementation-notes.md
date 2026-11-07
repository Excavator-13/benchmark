# Implementation Notes

- Change: add-occupation-skill-graph-audit
- Schema: spec-driven
- Store: local (repository root)
- Implementation roots: `/Users/watuji/da_chuang/repos/benchmark`
- Updated: 2026-11-07T20:05:30+08:00
- Implementation revision: baseline commit `af2756f46470f3ab5803e00cc8fedb53c27e5adc` plus a dirty worktree (`README.md` modified, `benchmark/occupation_skill_graph/` untracked). No implementation commit was created.
- Progress: 14/14 tasks complete.

These are apply-owned notes for the independent verification model. They are not a
verification report, do not set a verdict and do not establish scientific
acceptance.

## Implementation Map

| Task / requirement / scenario | Code and tests | Decisions / context |
| ----------------------------- | -------------- | ------------------- |
| 1.1, R1 canonical training inputs, held-out isolation, row order, separate file/content identities | `benchmark/occupation_skill_graph/protocol.py`, `data.py`; `tests/test_data.py` | Reads only key columns and the 27 training months through Parquet column projection; values validated natively and retained as `float64`; canonical grid is sorted by `(r2_id, skill_id)`; file SHA256 is separate from the protocol/month/key/observation content SHA256. |
| 1.2, R1 published assertions, grid/key/month/value rejection, unsupported scope | `data.py` (`assert_published_training`, `validate_scope`); `tests/test_data.py` | Published r2 requires occupations `0..51`, skills `0..2334`, 121,420 rows and exactly the 36 continuous month columns. Fixtures accept non-dense IDs. Fold/rate/other-source/other-version requests fail before graph work. Old nograph constants and its `float32` loader are untouched. |
| 2.1, R2 Jaccard and cosine | `scores.py` (`jaccard_pair`, `cosine_pair`, `_score_upper`); `tests/test_scores.py` | Blockwise scoring with compact upper-triangle storage. Jaccard uses integer support intersections/unions (empty union zero). Cosine uses normalized demand profiles; zero-demand vectors score zero. Scores are clamped only within `1e-12` rounding tolerance. |
| 2.2, R3 deterministic top-10 and undirected union | `scores.py` (`compute_candidate`, `_selection_for_row`, `select_top_k`); `tests/test_scores.py` | Selection sorts by `(-score, skill_id)`; exact cutoff ties are counted, not randomized. Union keeps canonical `a < b` pairs, original canonical `float64` scores and one-sided/both direction flags. Degree is recomputed from the union; the report never claims a degree bound of 10. |
| 2.3, R5 structural summaries and overlap | `structure.py` (`candidate_structure`, `connected_components`, `candidate_overlap`, `pearson_association`, `distribution_summary`); `tests/test_structure.py` | Includes zero-demand skills, support counts, pre-sparsification density/score histogram/full-score concentration, cutoff ties, final edges/isolates, degree/weight distributions, components, all-skill vs training-active coverage and degree associations with total demand/breadth. Empty/zero-variance statistics are `null` with reasons. Union-find avoids graph dependencies. |
| 3.1, R4 key-only target mapping and lazy expansion | `mapping.py` (`load_target_keys` is in `data.py`; `validate_target_population`, `mapping_descriptor`, `iter_context_edges`); `tests/test_mapping.py` | Target tables are read with only `(<context>_id, skill_id)` columns. Every context must contain exactly the source skill set; absent/extra/duplicate keys fail. Mapping stores target keys once plus per-context counts and a descriptor; `iter_context_edges` yields one context at a time over shared edge/score arrays, with both directions and no cross-context edges. |
| 3.2, R6 diagnostic trends | `trends.py` (`compute_trends`, `candidate_trend_summary`); `tests/test_trends.py` | Blockwise over union edges and every source occupation. 26 first differences; Pearson only when both endpoints have >=12 positive months and both variances are nonzero. `trend_reason_codes` is `0` eligible, `1` `history_insufficient`, `2` `constant_difference`; insufficient is checked first. Per-edge counts, correlation summaries, common-zero fractions and candidate aggregates are saved. Graph payload hashes are checked before/after diagnostics. |
| 4.1, R8 exclusive artifacts, checksums, terminal states | `artifacts.py`, `layout.py`, `runner.py`; `tests/test_artifacts_runner.py` | Run directory reserved exclusively; numeric payloads are ordinary `.npy` (no object pickles); command/protocol/provenance/environment/report/summary and an `artifacts-sha256.json` inventory are written. Mutable status/progress are excluded from the immutable inventory. A report and `succeeded` status appear only after payload and audit writes. Injected post-stage failures retain completed arrays and a `failed` status with no report. |
| 4.2, R7 isolated worker, limits, progress, RSS | `supervisor.py`, `_worker.py`, `runner.py`, `artifacts.py`; `tests/test_supervisor.py` | Worker pins single-thread BLAS variables before numerical imports. Supervisor reserves output, samples `artifacts/progress.json`, enforces separate construction/trend stage deadlines and a sampled RSS limit, and records CPU thread settings. Defaults are 1800 s per construction/trend stage and 2 GiB. POSIX uses `libproc`/`/proc` native probes, Windows uses `GetProcessMemoryInfo`; `ps` is only a fallback. No automatic retry; timeout, RSS, cancellation and hard-kill produce non-success/interrupted evidence. |
| 4.3, R9 build/check CLI and path safety | `cli.py`, `paths.py`; `tests/test_cli.py`, `tests/test_compatibility.py` | `build` supports explicit development fixture mode and explicit research purpose. Development output defaults to `scratch/occupation-skill-graph/<id>`; overrides must resolve inside ignored scratch or system temp and are refused inside project source/research/dataset/history, including when the checkout is under a temp root and through symlinks/traversal. Research output is always a fresh `research/runs/<id>` and cannot be redirected or combined with fixture injection. CLI help imports no NumPy/pandas/pyarrow/torch. |
| 4.4, R8 saved-only checker | `checks.py`; `tests/test_checks.py` | Recomputes identities, scores, selections, union edges, structure, mapping counts and trends from saved observations only. Verifies inventory, dimensions, exact keys/counts/null reasons and `1e-12` numeric agreement; rejects corrupt arrays, contradictory report counts, key changes, incomplete status and missing artifacts. Writes one exclusive external report and re-hashes the input tree before/after. |
| 5.1 README usage | `README.md` section 4.7 | Documents requirements, graph-score semantics, fixture build/check commands, artifacts, defaults, development/research separation and the separate research acceptance/real-data audit/T010 steps. The documented commands were executed successfully in the pinned CPU environment. |
| 5.2 fixture and compatibility checks | `benchmark/occupation_skill_graph/tests/`; old suites | New suite: 80 tests OK. Old no-graph suite: 287 tests OK (2 skipped). Old graph-value skeleton suite: 153 tests OK (2 skipped). Old help/imports remain available; old packages have no Git diff. |
| 5.3 this handoff | `implementation-notes.md` | Maps requirements/tasks to files, records checks and limitations, and avoids any claim of graph freezing, research acceptance or predictive benefit. |

## Non-obvious decisions

- The compact upper triangle stores one canonical score per unordered pair. Selection rows are assembled from that canonical storage, so the two directions can never disagree because of a separately computed matrix product.
- The checker deliberately reuses the pure scoring/trend functions on saved observations; independent hand calculations in `test_scores.py` and `test_trends.py` provide the oracle checks.
- Published mode accepts no source overrides at all; fixtures are reachable only through the explicit `--fixture` flag and all three target paths. This prevents a small fixture from silently taking published-population assertions.
- The immutable checksum inventory excludes `artifacts/status.json` and `artifacts/progress.json` because they must change after the inventory is written. The checker validates the terminal status directly and validates every immutable payload through the inventory.
- Trend reason codes are saved per edge and context so a null correlation can be audited as insufficient history or constant difference, not merely inferred from aggregate counts.

## Checks Run

| Command | Working directory / setup | Result / evidence | Run time or revision |
| ------- | ------------------------- | ----------------- | -------------------- |
| `python -m unittest discover -s benchmark/occupation_skill_graph/tests` | repository root; `job-sdf-baseline` (Python 3.11.17, NumPy 1.26.4, pandas 2.2.3, PyArrow 17.0.0) | 80 tests, `OK`, about 4–5 s. Covers tasks 1.1–5.2. | 2026-11-07, revision above |
| `python -m unittest discover -s benchmark/nograph_baseline/tests` | repository root; same environment | 287 tests, `OK` (2 skipped), 43.659 s. Old loader/runner behavior unchanged. | 2026-11-07, revision above |
| `python -m unittest discover -s benchmark/graph_value_skeleton/tests` | repository root; same environment (torch available) | 153 tests, `OK` (2 skipped), 217.648 s; log `/tmp/gvs-tests.log`. | 2026-11-07, revision above |
| New CLI help: `python -m benchmark.occupation_skill_graph --help`, `... build --help`, `... check --help` | repository root | Exit 0; no numerical/ML import at help time (asserted by `tests/test_cli.py`). | 2026-11-07 |
| Old help: `python -m benchmark.nograph_baseline --help`, `python -m benchmark.graph_value_skeleton --help` | repository root | Exit 0; command surfaces retained. | 2026-11-07 |
| README fixture snippet, build and check commands | repository root | Exit 0; run at `scratch/osg-runs/fixture-audit`; check report `scratch/osg-runs/check-fixture-audit.json` status `ok`. | 2026-11-07 |
| Large synthetic fixture build (52 occupations x 300 skills, 27 months; not published data) | repository root; direct `runner.execute_build` | Succeeded; construction 0.045 s, mapping 0.031 s, trends 0.116 s, peak RSS 196,018,176 bytes; checker status `ok` at `scratch/osg-probe/large-check.json`. | 2026-11-07 |
| `openspec validate "add-occupation-skill-graph-audit" --type change` | repository root | `Change ... is valid`. | 2026-11-07 |
| `git diff -- benchmark/nograph_baseline benchmark/graph_value_skeleton benchmark/graph_method` | repository root | Empty; no old package edits. | revision above |

## Verification Reminders

- No published-data construction, prediction training, dataset edit, research-record edit or `research/runs` output was performed. The published paths and research purpose are documented but were not executed; a verifier should not treat fixture evidence as real-data auditing.
- Full 2,335-skill published-scale construction was not run. The largest synthetic measurement used 52 x 300 skills. Full-scale runtime, peak RSS, block timings and near-tie boundary behavior remain unmeasured; do not claim the 30-minute/2 GiB defaults are sufficient at full scale without a separate research-side run.
- The memory limit is a sampled supervisor observation, not an OS hard allocation cap. Overshoot between samples is possible; the report and status say so. Native RSS probes are exercised on macOS (`proc_pidinfo`); Linux `/proc` and Windows `GetProcessMemoryInfo` branches are implemented but not exercised in this environment. The `ps` fallback would fail under the current sandbox policy.
- Cross-platform bitwise equality is not claimed. Near-tie rankings and floating-point score summaries can differ at the last bits across BLAS/platform combinations; exact-tie semantics are proved only in the pinned environment.
- Trend eligibility is a descriptive convention, not significance or reliability. Common shocks, short histories and low counts can produce unstable correlations; no eligible context means unknown, never zero-filled. Opposing signs are retained.
- Candidate scores are relation priors only. No graph was frozen, no candidate was accepted, and no predictive benefit or T010 integration was demonstrated.
- The checker rederives from saved arrays and uses the same pure functions as the builder. Hand-calculated score/trend tests are the independent oracle; the checker does not reopen source Parquet and cannot detect a source file that changed after the build (it validates recorded identities and saved content only).
- `artifacts-sha256.json` intentionally excludes mutable `artifacts/status.json` and `artifacts/progress.json`; the checker reads the terminal status but does not hash it. A verifier should confirm that this exclusion is acceptable under the change's evidence rules.
- The published `region` target range is taken from the immutable shipped file (`region_id` 0..6). Published-mode assertions were unit-tested by range, but the full published target grids were not loaded in this environment.
- Research purpose with published inputs is rejected in fixture mode and requires a separate research authorization; only its rejection branches were exercised.
