# p02-t006-r0-gru-v2-s2-a-20261128-01

- operation: fit
- purpose: formal
- encoder: GRU, seed 2, learning rate 0.001
- protocol controls complete: True
- dataset: r0 (2335 nodes)
- demand source: dataset\demand\r0.parquet
- status: completed
- completed epochs: 200 / 200
- selected checkpoint: epoch 200 (updates 3800)
- best validation MSE / MAE: 206192 / 107.005
- training-only RMS scale: 3505.72
- test labels used during fit: no

## Evidence

- per-epoch validation history: `history.json`
- fixed-parameter scores (init/10/50/100/200/best): `scores.json`
- update/clip records: `gradients.json`
- validation predictions/labels: `validation/`
- selected weights: `weights/best.pt`
- recoverable last state: `recovery/last.pt`
- cost sample and estimate: `cost.json`

## Cost sample

- status: ok
- measured sample seconds: 25.538380599999073
- steady-state median epoch seconds: 0.7487617000006139
- estimated full fit seconds: 412.661802280321

Development evidence is software evidence only; it is not research acceptance, a formal run or a scientific conclusion.
