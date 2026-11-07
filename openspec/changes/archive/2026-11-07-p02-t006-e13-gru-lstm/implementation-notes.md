# Implementation Notes

- Change: `p02-t006-e13-gru-lstm`
- Schema: E13/spec-driven-compatible handoff (manual because `openspec` is unavailable)
- Implementation root: `E:\大创\repo\benchmark-my-change`
- Updated: 2026-11-07
- Revision: no Git worktree; local files are dirty/uncommitted
- Progress: 6/6 tasks complete; strict validation and independent verification passed after installing OpenSpec 1.16.1

## Implementation map

| Requirement | Code / evidence | Notes |
| --- | --- | --- |
| Minimal GRU/LSTM startup | `benchmark/multivariate_time_series/data_provider/data_loader.py`, `exp/exp_basic.py` | Optional dependencies are loaded only when needed |
| Configurable recurrent models | `models/GRU.py`, `models/LSTM.py`, `run.py` | `--rnn_hidden_size` and `--rnn_layers` are wired through |
| Validation-only checkpoint selection | `exp/exp_long_term_forecasting.py`, `run.py` | Test evaluation occurs after training and reloads `checkpoint.pth` |
| Reproducible comparison | `run_gru_lstm.sh`, `research/runs/p02-t006-gru-lstm-20261107/` | Three seeds, same protocol, logs and metrics summary |

## Checks run

| Command | Result |
| --- | --- |
| `python -m py_compile run.py ...` | passed |
| `python run.py --help` | passed; GRU/LSTM, recurrent arguments and seed are visible |
| GRU/LSTM forward shape smoke test | passed; output shape `[2, 3, 4]` for both |
| Three-seed GRU/LSTM training | passed on CPU; logs under `research/runs/p02-t006-gru-lstm-20261107/` |
| Earlier `openspec validate ...` attempt | blocked before installation; superseded by the passing command below |
| `openspec validate p02-t006-e13-gru-lstm --type change --strict --json --no-interactive` | passed; valid change, zero issues |
| One-epoch GRU/LSTM verification smoke test | passed; both models loaded validation-selected checkpoints and produced final test metrics |

## Verification reminders

- Re-run strict E13 validation and independent verification after installing/providing the project `openspec` CLI.
- The comparison covers only `r0/count`, 6-month input, 3-month horizon, 20 epochs, and one CPU environment.
- The shell runner's default data path points to the sibling `benchmark` data checkout; pass an explicit fifth argument when data is stored elsewhere.
