# p02-t006-r0-gru-s0-lr1e3-a-20261108-01

- operation: fit
- purpose: formal
- encoder: GRU, seed 0, learning rate 0.001
- protocol controls complete: True
- dataset: r0 (2335 nodes)
- demand source: dataset/demand/r0.parquet
- status: completed
- completed epochs: 100 / 100
- selected checkpoint: epoch 100 (updates 1900)
- best validation MSE / MAE: 432772 / 115.153
- training-only RMS scale: 3505.72
- test labels used during fit: no

## Evidence

- per-epoch validation history: `history.json`
- fixed-parameter scores (init/10/50/100/best): `scores.json`
- update/clip records: `gradients.json`
- validation predictions/labels: `validation/`
- selected weights: `weights/best.pt`
- recoverable last state: `recovery/last.pt`
- cost sample and estimate: `cost.json`

## Cost sample

- status: ok
- measured sample seconds: 3.2952644580000197
- steady-state median epoch seconds: 0.11125033300049836
- estimated full fit seconds: 31.648374788030925

Development evidence is software evidence only; it is not research acceptance, a formal run or a scientific conclusion.
