# Design

1. Import optional dataset/model modules only when the selected experiment needs them. GRU/LSTM startup must not require `sktime`, M4, `hypnettorch`, or `reformer_pytorch`.
2. Construct recurrent hidden and cell states with the input tensor's device and dtype. The projection layer uses the configured hidden size and emits `enc_in` channels.
3. Add `--rnn_hidden_size` and `--rnn_layers` to `run.py`. Respect `--seed` and derive subsequent iteration seeds as `seed + iteration`.
4. During training, compute train and validation loss only. `EarlyStopping` saves the best validation checkpoint. `test(..., test=1)` reloads that checkpoint once training ends.
5. Use one shell entry point to run GRU and LSTM with identical data and budget. Preserve raw logs and a machine-readable metric summary under the research run directory.
