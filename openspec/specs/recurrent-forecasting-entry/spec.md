# recurrent-forecasting-entry Specification

## Purpose
This capability defines a reproducible long-term forecasting entry point for comparing recurrent models on the Job-SDF multivariate demand data under identical data, training, checkpoint, and evaluation rules.

## Requirements

### Requirement: Recurrent model comparison is configurable

The forecasting entry point SHALL expose GRU and LSTM as selectable models and SHALL accept explicit recurrent hidden-size, layer-count, and seed parameters.

#### Scenario: Select GRU or LSTM from the command line

- **WHEN** a user starts a long-term forecasting run with `--model GRU` or `--model LSTM`
- **THEN** the selected recurrent model starts without importing unrelated optional model dependencies

#### Scenario: Reproduce repeated runs

- **WHEN** a user supplies a base seed and more than one iteration
- **THEN** each iteration uses a deterministic seed derived from the base seed and iteration index

### Requirement: Checkpoint selection uses validation data

The training workflow SHALL select the checkpoint with the best validation loss and SHALL evaluate the test set only after training has finished.

#### Scenario: Finish training and test the selected checkpoint

- **WHEN** training completes or early stopping terminates the run
- **THEN** the final test evaluation reloads the checkpoint selected by validation loss

#### Scenario: Do not inspect test loss during training

- **WHEN** an epoch is in progress
- **THEN** the training log contains training and validation losses without using test loss for model selection

### Requirement: Recurrent outputs preserve the forecasting shape

The recurrent models SHALL return exactly `pred_len` future steps and `enc_in` output channels for a valid input sequence.

#### Scenario: Forward pass returns the requested horizon

- **WHEN** a recurrent model receives a batch with shape `[batch, seq_len, enc_in]`
- **THEN** it returns a tensor with shape `[batch, pred_len, enc_in]` on the input device and dtype
