# Tasks

- [x] Remove eager optional imports that block GRU/LSTM startup.
- [x] Add configurable GRU/LSTM hidden size and layer count with device-safe states.
- [x] Fix checkpoint path handling and reload the validation-selected checkpoint for final testing.
- [x] Make the CLI honor `--seed` and provide a reproducible GRU/LSTM runner.
- [x] Run three seeds per model on the same `r0/count` protocol and record MSE/MAE.
- [x] Run the formal `openspec` strict validation and independent E13 verification when the CLI is available.
