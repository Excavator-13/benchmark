# Tasks

## 1. Protocol runner

- [x] 1.1 Add the isolated recurrent training module and CLI with GRU/LSTM selection, L6/H3 split construction, training-only RMS scaling, deterministic CPU setup, and actionable input validation; verify `python -m ... --help` and invalid-model rejection.
- [x] 1.2 Implement full-window loss accumulation, gradient clipping, validation-only checkpoint selection, resumable checkpoint manifest, and atomic JSON summaries; verify with a synthetic fixture that test labels are not read during training.

## 2. Comparison and research evidence

- [x] 2.1 Add deterministic unit/smoke tests for scaling, window boundaries, state reset, metrics, and checkpoint identity; verify the targeted test command passes.
- [x] 2.2 Run the approved r0/count GRU and LSTM comparison with at least three seeds when data and cost preflight pass; save raw logs, environment, provenance, metrics, and comparison summary under a new run ID.
- [x] 2.3 Update the P02 protocol, T005 report handoff, and research state with actual implementation and run identities, explicitly preserving T009 ownership; verify links and status fields resolve.

## 3. Independent acceptance

- [x] 3.1 Run strict OpenSpec validation and independent e13 verification, resolve findings, and preserve implementation notes and verification evidence; verify the final report is PASS before archive.

## Workflow follow-up

- Archive the change only after independent verification is PASS.
- Commit the completed local work on `p02-t006-gru-lstm-v2`; do not push or create a Pull Request in this turn.
