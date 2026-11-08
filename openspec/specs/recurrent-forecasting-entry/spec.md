# recurrent-forecasting-entry Specification

## Purpose

This capability provides a reproducible, resumable, protocol-isolated recurrent forecasting entry point for comparing GRU and LSTM models on Job-SDF demand sequences while keeping split boundaries and test evaluation auditable.

## Requirements

### Requirement: Validated protocol inputs
The runner SHALL reject unsupported models, non-finite learning rates, non-positive epochs, layers, hidden sizes, node chunks, or gradient limits before creating checkpoints or summaries.

#### Scenario: Invalid configuration
- **WHEN** a user supplies an invalid model or non-finite/non-positive training option
- **THEN** the runner exits with a clear validation error and leaves no checkpoint for that run

### Requirement: Count-safe L6/H3 windows
The runner SHALL validate that every requested window start and count fits within the supplied sequence and SHALL record the resolved training, validation, and test window identities in run metadata.

#### Scenario: Window exceeds sequence
- **WHEN** a caller requests more L6/H3 windows than the sequence can contain
- **THEN** the runner raises a validation error before training begins

### Requirement: Resumable identity-bound training
The runner SHALL support resuming from a checkpoint that matches the protocol, model architecture, data shape, and resolved configuration, restoring optimizer state and continuing from the saved epoch.

#### Scenario: Resume compatible checkpoint
- **WHEN** a user resumes with matching protocol and configuration identity
- **THEN** training continues from the saved epoch and updates the same run manifest atomically

#### Scenario: Resume incompatible checkpoint
- **WHEN** a user resumes from a checkpoint with a different protocol, model, or data identity
- **THEN** the runner rejects it before changing the run outputs

### Requirement: Test-label isolation
The runner SHALL avoid reading test labels during training and SHALL evaluate test metrics only after selecting and restoring the best validation checkpoint.

#### Scenario: Test labels withheld
- **WHEN** training and validation are executed
- **THEN** test labels are not accessed for updates or checkpoint selection, and test metrics appear only in the final summary

### Requirement: Auditable summaries
The runner SHALL emit finite metrics, selected epoch, resume provenance, split identities, and checkpoint identity in machine-readable output using atomic writes.

#### Scenario: Completed run summary
- **WHEN** a run completes successfully
- **THEN** its summary contains the resolved protocol, data identity, checkpoint identity, validation selection, and finite validation/test metrics
