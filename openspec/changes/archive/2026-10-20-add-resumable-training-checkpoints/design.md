# Design

## Context

See proposal.md for motivation. `training.py` retains current weights, Adam and selection history only in memory; `runner.py` writes training results after all epochs. CLI workers reserve fresh directories. The r2 controller observes process heartbeats but not epochs, uses a four-hour per-fit watchdog and has no recovery mapping. Existing numeric evidence forbids pickle. Windows file replacement can encounter transient sharing violations.

## Goals / Non-Goals

**Goals:** Make validated epoch boundaries recoverable and observable, retaining scientific and provenance identities across explicit fresh attempts. Support finalization recovery from epoch 200 and distinguish elapsed work from downtime.

**Non-Goals:** Mid-epoch recovery, budget/model/graph changes, automatic startup at Windows boot, migration of absent checkpoints, extra formal datasets or cloud infrastructure. Formal training remains 200 epochs on CPU with one thread.

## Decisions

### Commit epoch generations atomically

Introduce a separate versioned checkpoint codec. Store named numeric model tensors, Adam slots/scalars, Python/NumPy/torch CPU RNG states, history, selected weights/epoch/MSE and timings in object-free NPZ; encode structured metadata as UTF-8 bytes. Load with `allow_pickle=False`, validate exact keys, shapes, dtypes, finite numeric state and consistent counters. Avoid torch pickle serialization, which conflicts with the artifact contract.

Write a new immutable generation through flushed temporary files and atomic replacement with bounded Windows sharing retries. Publish an atomic manifest pointer last, including the generation SHA256 and byte size. Retain the previous committed generation; remove older generations only after successful publication. Hashing belongs outside the hashed payload. Failure injection must cover each publication boundary. Flush is best effort under OS durability guarantees; arbitrary storage hardware failure is not guaranteed recoverable.

### Capture only complete validated epochs

Add a training state boundary after Adam update, validation, strict-less-than best selection and history append. Save current weights as well as best weights: best-only recovery changes optimization. Capture RNG at this boundary and restore it last after allocations/model construction on recovery. Start the loop at completed_epoch + 1; epoch 200 only runs finalization. Persist cumulative training/validation seconds separately from checkpoint I/O and each attempt's process wall time. Never replay part of an epoch as if it were committed.

### Explicit fresh-attempt resume with strict identity

Thread `--resume-from` through CLI, worker specification, configuration and runner. Validate schema, complete state and SHA256, source/runtime/dependency identities, frozen scientific configuration, data, source/message edges, fixed masks, windows and ordered chunks before an optimizer step. Ignore only operational fields such as output directory and new run ID when comparing computation identity. Do not allow purpose changes to bypass formal path policy.

Copy the chosen generation and manifest into the new run, recording original run and ancestry checksums. The new run must remain interpretable without its parent directory. Never overwrite the parent. Existing success runs remain readable; resume is for incomplete attempts and finalization recovery. Missing state fails explicitly. Record ancestry separately from scientific condition identity, and reject overlapping ancestry when checking independent repetitions.

### Publish evidence rather than heartbeat-derived success

After each committed checkpoint, atomically write progress with completed epoch, optimizer step count, checkpoint digest, cumulative work and recent epoch duration. Estimate remaining epochs using a rolling window of observed full epochs; report sample count and unavailable ETA before observations. Add bounded chunk/stage progress so a long first epoch is distinguishable from no forward movement; chunk progress is observational and never a recovery point. Separate status, progress and final success manifests.

### Recover the batch through a new attempt ledger

Extend `research/phases/P02/t002_r2_batch.py` with explicit recovery input and matrix-slot-to-attempt mapping. Verify success artifacts and saved-only checks before reusing completed fits. Resume a compatible committed checkpoint or start a fresh replacement when none exists, always under new IDs and logs. Check live PID identity and an exclusive controller ownership lock; stale PID records alone are not ownership. Keep the old batch untouched and place recovery records in a new batch.

Use epoch/stage progress for diagnosis and measured runtime forecasts. Make per-fit timeout explicit/configurable instead of treating the old short-sample forecast or four-hour default as evidence of a hang. Pause on nonfinite state, validation failure, stalled progress or breached configured bound, with last checkpoint and reason. Preserve the original 30-fit/51-check matrix and success-only publication gate. No automatic retry loop may conceal repeated failures.

### Validate on small complete fixtures before formal rollout

Use real subprocess interruption and fresh-process recovery across the full 200 epochs on bounded self, graph and shuffled fixtures. Include selection before interruption, exact ties, multiple interruptions and epoch-200 finalization. Compare history, current/best parameters, Adam slots and predictions; tolerate only the existing normalized 1e-6, with saved-only 1e-12 checks. Test malformed states, identity changes, atomic failures, ancestry conflicts, controller stale ownership and completed-slot reuse. Run the relevant baseline regressions and independent OpenSpec verification. No formal r2 job is a substitute for these checks.

## Risks / Trade-offs

- Checkpoint I/O adds overhead → record I/O separately, keep two committed generations and measure on fixtures and first real epochs.
- A crash within a long first epoch still loses that epoch → expose chunk progress; defer partial-gradient recovery because it substantially increases state complexity.
- Strict identities can reject checkpoints after code changes → fail safely, retain source bytes and restart a fresh attempt rather than silently mixing implementations.
- New source identities can affect prepared graph validation → keep checkpoint schema separate from graph-generation protocol; prove semantic compatibility or regenerate explicitly, never bypass an identity gate.
- Windows replacement failures and low C-drive space → bounded retries and D-drive execution; report errors without publishing incomplete generations.
- Old cost estimates were not representative → derive new forecasts from actual epoch observations, displaying uncertainty rather than promising a completion time.

## Migration Plan

Implement and test on C using small fixtures. Obtain current independent verification and archive through the OpenSpec workflow. Research-side acceptance then closes the delegation. Synchronize the accepted source and controller into the authorized D execution copy, preflight source/environment/input/prepared graph identities and disk capacity, and start a new r2 batch. Preserve the old interrupted batch. If rollout fails, pause and retain its checkpoint and diagnosis; rollback must never make a new checkpoint readable by an incompatible old codec. Commit and push successful experiment results only under the existing completion authorization.
