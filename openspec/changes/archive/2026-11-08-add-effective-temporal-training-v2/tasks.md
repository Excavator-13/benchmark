# Tasks

## 1. Runner hardening

- [x] 1.1 Add shared configuration and dataset validation for finite learning rates, positive architecture/resource values, and model identity; verify invalid API and CLI inputs fail before run outputs are created.
- [x] 1.2 Make L6/H3 window construction count-safe and record explicit train/validation/test split metadata; verify boundary and over-request tests.
- [x] 1.3 Refactor training to defer test-window materialization until after validation checkpoint selection and restore; verify a guarded test-label fixture is never read during updates or selection.

## 2. Resumable and auditable state

- [x] 2.1 Extend checkpoint manifests with canonical data/config identity, epoch progress, best validation state, and resume provenance; verify incompatible checkpoints are rejected without mutating outputs.
- [x] 2.2 Add resume controls to the API and CLI, atomically persist epoch checkpoints and summaries, and verify a resumed run reaches the same deterministic result as an uninterrupted run.
- [x] 2.3 Extend focused tests and user-facing help for resume, split metadata, and finite metrics; verify the targeted unittest suite and CLI help pass.

## 3. Integration acceptance

- [x] 3.1 Run strict OpenSpec validation and the focused regression suite, inspect generated manifests/checkpoints, and record implementation notes for independent e13 verification.

## Workflow follow-up

- Archive the change only after independent verification is PASS.
- Preserve the archived v1 change and T009 ownership; do not rerun the research comparison unless separately authorized.


