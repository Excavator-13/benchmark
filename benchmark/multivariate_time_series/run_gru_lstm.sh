#!/usr/bin/env bash
set -euo pipefail

# Run GRU and LSTM with exactly the same Job-SDF forecasting protocol.
# Usage: bash run_gru_lstm.sh [dataset_name] [use_gpu] [seed] [iterations] [data_root]
dataset_name="${1:-r0}"
use_gpu="${2:-0}"
seed="${3:-2}"
iterations="${4:-3}"
data_root="${5:-../../dataset/demand/}"

for model_name in GRU LSTM
do
  python run.py \
    --task_name long_term_forecast \
    --is_training 1 \
    --model_id "${dataset_name}_gru_lstm" \
    --model "${model_name}" \
    --data "job_demand_${dataset_name}" \
    --root_path "${data_root}" \
    --data_path "${dataset_name}.parquet" \
    --features M \
    --seq_len 6 \
    --label_len 1 \
    --pred_len 3 \
    --rnn_hidden_size 256 \
    --rnn_layers 2 \
    --train_epochs 20 \
    --batch_size 1 \
    --num_workers 0 \
    --use_gpu "${use_gpu}" \
    --seed "${seed}" \
    --task_mode '' \
    --des 'gru_lstm_comparison' \
    --itr "${iterations}"
done
