# Tasks

## 1. Checkpoint format and publication

- [x] 1.1 Implement versioned object-free checkpoint codec for model, Adam, RNG, history, selection and timing state; verify round-trip and malformed-key/shape/dtype/nonfinite rejection tests with pickle disabled.
- [x] 1.2 Implement generation digest manifests, atomic publication, bounded Windows retries and two-generation retention; verify injected interruption at each publication stage preserves the previous committed checkpoint.
- [x] 1.3 Document checkpoint schema and durability limits; verify documented artifact layout matches codec fixtures.

## 2. Training continuation and progress

- [x] 2.1 Refactor training to expose validated epoch state and restore it before the next update; verify full 200-epoch fixture histories, current/best weights and Adam counters match continuous execution, including ties and epoch-200 finalization.
- [x] 2.2 Add committed-epoch and bounded chunk/stage progress with cumulative work, separate checkpoint I/O and measured rolling ETA; verify no false completion, no downtime inflation and explicit unavailable estimates.
- [x] 2.3 Document epoch-boundary recovery and timing semantics; verify progress examples against fixture output.

## 3. Public resume and evidence compatibility

- [x] 3.1 Add explicit resume input through CLI/config/worker/runner, strict computation/input/runtime/source identity checks and self-contained fresh-run lineage; verify compatible recovery, fresh-ID enforcement, source immutability and mismatch rejection before updates.
- [x] 3.2 Extend saved-only evidence checks for new lineage while retaining historical run readability and scientific condition identity; verify ancestry-overlap rejection and original repeat/recompute tolerances with old and new fixtures.
- [x] 3.3 Document public commands and missing-checkpoint behavior in the existing user documentation; verify the documented small-fixture resume command in a fresh process.

## 4. Batch restart integration

- [x] 4.1 Add fresh-batch recovery ledger, validated completed-slot reuse and eligible checkpoint continuation to the r2 controller; verify a bounded simulated matrix covers completed, resumable and no-checkpoint slots without mutating old evidence.
- [x] 4.2 Add live ownership checks, stale-record handling, measured progress diagnostics and explicit configurable runtime limits; verify duplicate ownership rejection, stale reboot recovery, pause on failure and absence of completion before all original gates.
- [x] 4.3 Update controller execution guidance with recovery planning, ETA uncertainty and success-only publication rules; verify documented dry-run/recovery-plan output and unchanged 30-fit/51-check matrix.

## 5. Integrated readiness evidence

- [x] 5.1 Run real subprocess interruption/recovery through 200 epochs on bounded self, graph and shuffled fixtures, including multiple interruptions and finalization; retain comparisons of history, parameters, Adam, selected epoch and predictions at normalized 1e-6 and saved-only 1e-12.
- [x] 5.2 Run relevant graph skeleton and baseline regression checks plus strict OpenSpec validation; record commands, outcomes, remaining limitations and source/evidence identities in implementation-notes.md for independent verification. Do not launch formal r2 during implementation validation.

## Workflow follow-up

- Obtain independent verification through openspec-e13-verify-change; repair findings through the fix workflow and reverify if necessary.
- Archive only after a current independent PASS. Research-side acceptance closes the delegation and updates recovery records.
- After acceptance, synchronize the accepted source to D, preflight identities/storage/ownership, start a fresh authorized r2 batch, monitor measured cost and pause on failure. Preserve the old interrupted batch.
- Commit and push after all authorized r2 fits and checks succeed; formal execution is not an implementation task or prerequisite for archiving this checkpoint capability.
