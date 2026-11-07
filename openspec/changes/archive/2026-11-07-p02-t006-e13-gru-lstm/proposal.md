# Proposal: P02/T006 E13 recurrent-model workflow

## Problem

The multivariate forecasting entry point could not run the GRU/LSTM comparison reliably because unrelated optional model dependencies were imported eagerly. The recurrent models also used fixed output dimensions, did not expose their recurrent capacity through the CLI, and the training loop evaluated the test set every epoch.

## Scope

- Make the long-term forecasting entry point usable for GRU and LSTM with the installed minimal dependencies.
- Add explicit hidden-size and layer-count configuration.
- Select checkpoints from validation loss and evaluate the test set only after training.
- Run a controlled three-seed comparison on Job-SDF `r0/count`.

## Non-goals

- No changes to P02/T009.
- No claim that either recurrent model is universally better.
- No changes to the original `benchmark-main` copy or to the scientific definition of the P01 protocol.
