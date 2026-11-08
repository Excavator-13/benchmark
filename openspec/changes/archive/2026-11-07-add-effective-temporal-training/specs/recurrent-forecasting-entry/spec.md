# Spec Delta

## Purpose

This capability provides a reproducible, protocol-isolated recurrent forecasting entry point for comparing GRU and LSTM models on Job-SDF demand sequences while preserving validation-only model selection and auditable run provenance.

## ADDED Requirements

### Requirement: Protocol-isolated recurrent training

The entry point SHALL run GRU or LSTM training with explicit dataset, L6/H3 window, RMS scaling, seed, optimizer, and CPU resource settings without changing the legacy runner's behavior.

#### Scenario: Valid GRU run

- **WHEN** a user supplies a supported dataset, `GRU`, finite seed, and protocol options
- **THEN** the runner trains and emits a machine-readable summary containing the resolved configuration and source identity

#### Scenario: Unsupported model

- **WHEN** a user supplies a model other than `GRU` or `LSTM`
- **THEN** the runner exits with a clear validation error before creating a training checkpoint

### Requirement: Training-only RMS preprocessing

The runner SHALL compute one scalar RMS scale from the training observation period only, apply it to inputs and targets, and record the scale and training-month identity in the run metadata.

#### Scenario: Validation and test isolation

- **WHEN** validation or test months contain values outside the training range
- **THEN** the recorded scale remains unchanged and no validation or test value contributes to its computation

### Requirement: Full-window optimization and checkpoint selection

The runner SHALL accumulate loss over all nodes and horizons in each training window before one optimizer update, clip the complete model gradient before stepping, and select checkpoints only by validation loss.

#### Scenario: Test labels are withheld during training

- **WHEN** training and validation complete
- **THEN** the test split is evaluated only after the selected validation checkpoint is loaded, and its labels do not affect updates or checkpoint choice

### Requirement: Auditable comparison outputs

The runner SHALL write finite metrics, per-seed provenance, checkpoint metadata, and a GRU/LSTM comparison summary containing mean and sample standard deviation for MSE and MAE.

#### Scenario: Repeated seeds

- **WHEN** at least three seeds complete for both models under the same resolved protocol
- **THEN** the comparison reports each seed, mean, sample standard deviation, and any failed run without silently dropping failures
