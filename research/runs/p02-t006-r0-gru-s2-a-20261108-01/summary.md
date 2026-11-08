# p02-t006-r0-gru-s2-a-20261108-01

- operation: fit
- purpose: formal
- encoder: GRU, seed 2, learning rate 0.003
- protocol controls complete: True
- dataset: r0 (2335 nodes)
- demand source: dataset/demand/r0.parquet
- status: completed
- completed epochs: 100 / 100
- selected checkpoint: epoch 100 (updates 1900)
- best validation MSE / MAE: 212087 / 114.046
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
- measured sample seconds: 3.0033495419993415
- steady-state median epoch seconds: 0.11107904199889163
- estimated full fit seconds: 31.252909382210966

Development evidence is software evidence only; it is not research acceptance, a formal run or a scientific conclusion.
