## Context

See `proposal.md` for motivation and the delta spec for acceptance. `checks.py` reserves RunDirectory objects and snapshots Git before writing reports; `artifacts.capture_git` captures the whole repository diff, while `capture_untracked_source` copies all untracked baseline files including tests. `runner.py` copies the protocol and writes five candidate parameter/prediction pairs. Existing CPU tests in `test_runner_cli.py` assert these old layouts and contain substantial saved-input adversarial coverage; `nb_fixtures.py` supplies temporary r0/region fixtures. Reuse those tests and numeric logic.

Research-side maintenance has adopted the policy, ignored `scratch/`, reduced the T004 index to schema v2 and removed sidecars/redundant expanded files. All 24 original packages and 88 readable entries are unchanged. `seal_20261007_baseline.py` currently assumes schema v1 and is explicitly marked unusable in current recovery guidance pending this change. P01 scientific computation remains v3; a protocol-file hash is still a byte identity rather than a semantic compatibility token.

## Goals / Non-Goals

**Goals:** Reduce duplicated evidence at existing producer boundaries while keeping the current scientific algorithms, measured execution identities and saved-only validators. Define a small, readable report schema and retain old saved-model readability.

**Non-Goals:** Real-data experiments, scientific protocol changes, shared content-addressed storage, databases, rewriting archives/history, moving legacy research directories, modifying skills or research delegation/status records, commits/pushes and automatic recovery verification.

## Decisions

### 1. Purpose and retention are explicit execution options

Add `purpose` to RunSpec and worker config, with CLI `--purpose formal|development` defaulting to formal. Resolve default development root to `<repo>/scratch/nograph-baseline`; explicit temporary roots remain usable. Resolve paths before validating that development output does not fall inside `<repo>/research/runs`, including symlink aliases. Preserve reservation/collision/status handling for model executions. The explicit purpose avoids guessing scientific intent from whether a dataset is a fixture. Existing default model calls remain formal and numerically unchanged.

Add `--retain-candidates` / corresponding RunSpec flag, default false. `_save_model_artifacts` always saves the selected model and statistics, and iterates candidate arrays only when requested. `selection.json` always retains all scalar validation rows and tie decisions. Keep in-memory fitting/selection unchanged; optional retention affects persistence only.

### 2. Checks have one report output

Replace `_check_run` and RunDirectory finalization with a small exclusive JSON report writer; keep recomputation/comparison/alignment routines and failure evidence. A report includes version, kind, creation time, command, input IDs/paths/consumed-file identities, checker commit and relevant source identities, tolerances, status, differences and recomputed metrics where applicable. Do not add a separate environment, config, provenance or recomputed-metrics file. Checker identity with unavailable/dirty details must be honest; it must not claim a clean commit when code differs. A small related patch can be included when needed, without a copied source directory.

CLI `--report PATH` is the primary output choice. Keep old `--run-id ID` and `--runs-root ROOT` check flags as aliases for `<ROOT>/<ID>.json`, defaulting to `research/reports/nograph-baseline/`. Make `--report` and `--run-id` mutually exclusive; require one. Preserve run-ID validation for alias paths. Public command results and CLI JSON identify `report_path` rather than promising a `run_dir`. Programmatic check functions accept an explicit report path and retain documented legacy keyword aliases without RunDirectory output.

Resolve output and input paths and reject any output inside either input before writing; reject existing outputs including symlinks. Reserve/report writes must use exclusive creation with complete JSON publication rather than silently replacing a destination. A collision must leave bytes intact. Missing/invalid input after a safe output choice produces failure JSON and a nonzero exit; an output error produces no new output. Do not weaken validators, tolerance limits or protocol/hash mismatch rejection. Reuse existing legacy source-manifest interpretation, not a new parallel loader.

### 3. Preserve relevant source content through fixed references or patches

Use the existing Git helper with explicit path scopes covering imported baseline runtime `.py` files, `benchmark/__init__.py` when relevant, and the actual protocol path. Exclude `tests/`, caches and unrelated research records. Capture staged and unstaged execution differences against the same base (`git diff HEAD -- <paths>`), relevant deletions and necessary untracked runtime files; base commit plus saved patch/files must reconstruct the used code. Record scoped dirtiness separately from optional whole-repository dirty information so unrelated documents do not force source copies.

Committed protocol/source files get commit/path/hash references. Preserve uncommitted protocol contents, including a protocol override outside the repository. Keep source hashes consumable by old saved-only validators; a reference is valid only if it matches the executing bytes. When Git is unavailable, explicitly record failure and save available relevant content as fallback. Do not claim complete provenance from a hash or guessed HEAD. No shared snapshot store is needed.

### 4. Archive verification reads schema v2 from Git

Dispatch the existing explicit `verify` utility on index schema. Schema v1 retains current package, sidecar and historical member checks. Schema v2 obtains each expected blob from the recorded commit/path and compares it with the package, retaining task/time/exclusion information without regenerating hash lists. Git reads are local; failure to resolve identity is an explicit verification failure, not a reason to fetch or guess current HEAD.

Inspect all requested tar member paths/types/counts/uniqueness before extracting. Restore only into a fresh temporary root and do not use existing runs. No external SHA256 table is needed for the Git-backed source. Document that separately exporting a package outside Git requires its own external SHA256; a manual command is sufficient and no new export framework is needed. Keep historical `seal` collision refusal; it is not a new general-purpose packaging pipeline and cannot rewrite existing packages.

### 5. Validate software with fixtures and retain applicable historical science

Exercise both schemas on temporary r0/region CPU fixtures, two same-seed executions, all three checks and optional candidate persistence. Keep the existing malformed/missing/mismatch and scientific protocol tests, updating output expectations. Test provenance in a small disposable Git repository with unrelated dirty records, staged runtime changes and untracked runtime source. Test archive schemas using small synthetic packages and local Git commits, never the current full corpus or a network restore; inspect the external-export checksum instructions without exporting scientific evidence.

The accepted T004 scientific evidence remains in its immutable packages. It establishes historical scientific acceptance, not proof of the changed software behavior. New fixture execution establishes format/software behavior without creating real-data research runs. Independent verification remains a separate workflow and inspects every delta scenario.

## Risks / Trade-offs

- Check output-path metadata changes can affect scripts; documented alias flags and old-input support preserve the common invocation while explaining the new `report_path` return.
- Source scoping can omit an imported execution dependency; derive the explicit runtime set from imports and test reconstruction with staged/unstaged/untracked cases rather than excluding all dirty source indiscriminately.
- New and old protocol text differs in hash despite the same scientific version; preserve strict comparison identity behavior and document the difference instead of inventing semantic equivalence.
- The reduced index is incompatible with the old helper until implemented; current research guidance already states this limitation, and task order fixes that helper early.
- Reduced candidate persistence prevents inspecting losers later; explicit opt-in retains their arrays, while default selection remains auditable from scores and selected outputs.

## Migration Plan

Implement against current mutable artifacts; do not modify main specs before independent PASS. Fix archive helper compatibility, then source/model persistence, report output and CLI aliases. Update README/tests together. Retain immutable T004 packages and readable entries byte-for-byte. Write apply-owned implementation notes identifying changed scopes and fixture evidence for independent verification. After independent PASS, archive with spec synchronization and let research-side acceptance update current recovery instructions. If an output API needs rollback, Git code history supplies it; do not restore old output by overwriting evidence or repopulating the 24 old directories.
