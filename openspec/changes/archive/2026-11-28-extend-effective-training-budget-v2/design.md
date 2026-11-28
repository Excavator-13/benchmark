## Context

See proposal.md for motivation and specs/recurrent-forecasting-entry/spec.md for the behavior contract. Research authority is the already-written `research/phases/P02/protocol-v2.md` plus its immutable inherited `protocol.md`. Implementation must consume these documents without editing them.

Inspection found a single current scientific profile in `temporal/protocol.py`, not an existing version registry. Training, cost estimates, checkpoint validation and CLI defaults import it. `diagnostics.py` additionally hardcodes `10/50/100` score keys and b80/b100 names. `artifacts.py` captures one protocol file. `resources.Ledger` version 1 stores stable batch/ledger identities and replacement-by-execution-ID entries; only measured/replayed kinds count, while estimated entries intentionally do not. Cost/recovery/live saved-stage guards all depend on this accounting.

## Goals / Non-Goals

**Goals:** Keep the existing staged architecture and enforce one coherent current v2 formal contract through training, validation diagnostics, saved reporting, recovery and budget enforcement. Preserve every historical file and the existing ledger lineage.

**Non-Goals:** A general hyperparameter/protocol registry, dual-version training, automatic matrix execution, optimization/normalization changes, new graphs, or historical evidence migration. No real-data reads/fits or research-record edits during apply/verify.

## Decisions

### 1. Adopt one current profile, and fail closed on historical execution

Move the current constants to scientific v2: EPOCHS=200, TOTAL_UPDATES=3800, DIAGNOSTIC_EPOCHS=(10,50,100,200), BUDGET_TAIL_EPOCH=160. Bind the v2 path and inherited v1 path/hash explicitly, with an ordered document identity payload used by provenance, effective condition and recovery checks. Verify the inherited hash declared by research; do not merely hash whatever mutable file happens to be present. Snapshot both documents through the existing source capture mechanism.

A general per-run version registry would preserve more legacy operations but would multiply configuration and gate dispatch for this bounded revision. Use current v2 training only. Saved-only loading must inspect saved scientific/document identity before treating a run as current: if an operation supports a historical artifact without changing its semantics, retain the original version; otherwise return an explicit incompatibility with the v1 runner reference (`3bd9fa4` or its run-source baseline `bf5abed8`). Mixed-version readiness/selection/report/compare and v1-to-v2 resume are always refused. Do not synthesize absent inherited identities for old artifacts.

Retain artifact format 2 if additive document metadata plus explicit scientific-version checks fully discriminate the new evidence. Do not silently accept missing v2 bindings under the existing format number.

### 2. Derive completeness and gate labels from frozen controls

Keep epoch-order, fixed-score completeness, immutable best-model restoration and report membership validation in their existing layers. Replace hardcoded diagnostic score lists and text with the frozen diagnostic epochs, while still requiring the exact complete 200-epoch history for formal readiness. Extra history must not substitute for the requested trajectory, and 100-epoch development artifacts must stay incomplete.

Calculate the tail from the first 160 and all 200 ordered records, output `b160`, `b200`, comparison boundaries and the relative improvement. Do not preserve misleading b80/b100 field names for new minima. Keep both-zero handling, exact threshold boundaries, at-least-two-seed aggregation, full a/b requirements, compatible baselines and explicit missing evidence.

Keep every optimizer step, selected-checkpoint rule and test access boundary unchanged. Diagnostic epoch 100 is saved on the same trajectory, not selected as a separate training-budget candidate. Cost projection uses the requested frozen 200 epochs and still measures complete epochs 6..10 within the same fit.

### 3. Make conservative budget debits distinct from forecasts and measurements

Add an explicit ledger entry kind such as `budget-debit` with stable debit ID, positive finite seconds, reason and timestamp. Expose a public `budget-debit` operation accepting `--ledger`, `--batch-id`, `--debit-id`, `--seconds` and `--reason`; it requires an existing matching ledger and no training/data access. Registration with identical identity/value/reason is idempotent; conflicting reuse is refused. Normal measured heartbeats cannot replace a debit, and registration cannot replace measured history. Validate entry kinds and amounts when loading to avoid unknown or malformed costs being ignored.

Report measured/replayed execution, debits, nonbinding forecasts and effective budget used separately. Define effective budget used as measured+replayed+debits. Preserve current estimated semantics. Route every remaining-budget check (preflight/controller watchdog, worker cost sample, resume, saved-stage guard and termination billing) through effective budget used; changing only one projection would leave a bypass. Keep original ledger ID, batch ID and old entries intact. This is a small additive ledger extension; do not rewrite the real ledger during software work.

Research will explicitly register a one-time debit ID `p02-t006-v1-unmetered-preparation` for 900 seconds on the continuing real ledger after software readiness and before v2 execution. That conservative debit is not a claim about actual training time. No debit is automatically added per fit or per resumed identity.

Account standalone public preflight against a supplied existing ledger with a unique measured execution ID and a finally path, including failure. Internal preflight already enclosed by a fit/controller must not be independently billed. Document a narrow measured-cost recording helper for research-side auxiliary operations, so future preparation does not require invented durations; keep such helper calls independent of scientific inputs and distinguish them from debit registration.

### 4. Use behavior-focused synthetic verification

Use tiny synthetic data for one complete 200-epoch trajectory and the full staged fixture path; most boundary cases can use saved synthetic evidence. Preserve early-best degradation/restoration and uneven-context global-loss tests. Add fixtures where 80→100 and 160→200 give opposite decisions, a complete 100-epoch artifact fails v2, inherited protocol identity changes, v1 arrays match v2 numerically, and cross-version resume is requested.

For accounting, load a preexisting temporary ledger, register the same debit twice, reject a conflicting/invalid debit, and demonstrate cost exhaustion caused by debits in both fit and live saved-stage entry points. Verify unchanged IDs/old entries and no double billing of internal preflight. No real research ledger, demand files, weights or historical outputs are test inputs.

## Risks / Trade-offs

- [More epochs still fail the tail gate] → Software declares readiness only; research must stop on failure without automatic budget expansion.
- [Some existing tests contain literal 100/80 and scores that turn negative past 100] → Update fixture construction to valid 200-epoch finite nonnegative histories; keep explicit historical fixtures labeled v1 for incompatibility tests.
- [A second protocol document is hashed but omitted from recovery or report membership] → Carry the same ordered identity payload through all condition consumers and test mutation of each member.
- [A debit is counted in cost projection but bypassed by a live check or lost on resume] → Centralize effective budget arithmetic and cover controller, recovery and saved-stage failure paths.
- [Historical operations become unavailable through the latest entry] → Fail with a precise version error and the original runner reference; never modify/reinterpret old results.

## Migration Plan

1. Implement and independently verify with synthetic fixtures; capture actual source basis and limitations. Preserve v1 research document bytes and all historical outputs.
2. Document actual CLI defaults, the debit command, separate measured/debited totals, and the version refusal behavior in README §4.7 and implementation notes.
3. After archived independent PASS, research accepts software readiness, registers the conservative debit once on the existing ledger, runs fresh preflight, and starts new v2 identities from initialization. Research owns this step and no software command schedules it.
4. Rollback means restoring the prior source version and keeping new v2 artifacts separate. Do not relabel checkpoints, remove budget debits or reset consumed cost to restore a former configuration.
