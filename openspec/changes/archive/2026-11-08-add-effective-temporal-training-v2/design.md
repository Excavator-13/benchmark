# Design

## Context

The v1 runner already owns deterministic CPU setup, training-only RMS scaling, L6/H3 forecasting, validation-selected checkpoints, and comparison summaries. Its public helpers currently construct windows without validating the requested count, and `train` builds test arrays before the optimization loop. Checkpoints contain model and optimizer state but no resumable epoch/best-state contract.

## Goals / Non-Goals

**Goals:**

- Preserve the v1 protocol and legacy runner boundary while adding strict input validation.
- Make resume explicit, identity-bound, and atomic.
- Keep test data access after validation selection and make split/checkpoint provenance inspectable.

**Non-Goals:**

- Changing the model architecture, optimizer family, split lengths, or research conclusions.
- Re-running the archived comparison or modifying T009 records.

## Decisions

1. **Extend the existing module and API.** The v1 entry point is already the isolated owner of this behavior; a second runner would duplicate protocol logic. Add validation and resume state to the same module, keeping existing calls compatible by default.
2. **Use a manifest identity fingerprint.** Build a canonical identity from protocol version, model configuration, data shape/source, and split metadata. Resume checks this identity before loading tensors or writing output.
3. **Resume at epoch boundaries.** Save the current epoch, optimizer state, selected validation state, and progress atomically after each completed epoch. A resumed run starts at the next epoch and preserves the prior best checkpoint.
4. **Defer test materialization.** Construct training and validation windows before the loop. Construct the test window only after restoring the selected validation state, so the training path cannot consume test labels.
5. **Fail before output creation.** Validate all CLI and API options before creating the run directory or checkpoint files.

## Risks / Trade-offs

- [Risk] Existing checkpoints lack the v2 resume fields. → Treat them as loadable only for inference when protocol identity is present; reject them for resume with a clear error.
- [Risk] A crash during a checkpoint write could leave partial output. → Use temporary files plus `os.replace` for JSON and checkpoint artifacts.
- [Risk] Resume configuration drift can silently invalidate comparisons. → Compare canonical manifest identity and fail before mutation.

## Migration Plan

No migration is required for existing archived runs. New runs use the extended manifest and can be resumed with the new CLI option. If a v1 run must be continued, start a fresh v2 run from the same source and record the new run identity.
