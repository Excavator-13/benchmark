# P02/T006 GRU/LSTM rerun

Correct baseline: `91ea3d6df8360998d9d2b1ed36ab764322ee26f3`

Protocol: `P2-effective-training-L6-H3-v1`, r0/count, training-only RMS, CPU single-thread, 100 epochs, hidden size 32, one recurrent layer, learning-rate candidates `{1e-3, 3e-3}` selected by validation MSE. Both models selected `3e-3`.

| Model | Test MSE mean ± sample SD | Test MAE mean ± sample SD |
| --- | ---: | ---: |
| GRU | 1282996.056 ± 27724.494 | 197.965 ± 12.812 |
| LSTM | 1241212.691 ± 87709.327 | 190.061 ± 6.454 |

Seed-level metrics, provenance, checkpoints, and candidate logs are in this directory. The result is limited to the r0/count pre-experiment and does not establish a universal model ranking. P02/T009 was not modified or run.
