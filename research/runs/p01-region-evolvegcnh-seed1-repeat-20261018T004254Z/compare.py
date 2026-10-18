import hashlib
import json
import os
from pathlib import Path

import numpy as np
import torch

run = Path(os.environ['T005_RUN']).resolve()
output = run / 'outputs/count/region/EvolveGCNH/1'
assert json.loads((run / 'status.json').read_text())['status'] == 'succeeded'
assert not (run / 'comparison.json').exists(), 'Comparison already exists; preserve the original report'
old_record = json.loads((run / 'original-results.json').read_text())['1']
old = Path(old_record['path'])
for name, expected in old_record['files'].items():
    assert hashlib.sha256((old / name).read_bytes()).hexdigest() == expected, 'Old result changed: ' + name
groups = np.load(run / 'identity-and-groups.npz')
keys = groups['node_keys']

def tensors(folder, stem, count):
    values = [torch.load(folder / (stem + '_%d.pt' % i), map_location='cpu', weights_only=True).numpy()
              for i in range(count)]
    result = np.stack(values).astype(np.float64)
    assert result.shape == (count, len(keys), 3) and np.isfinite(result).all()
    return result

def basic(pred, gold):
    error = pred - gold
    return {'MAE': float(np.mean(np.abs(error))), 'MSE': float(np.mean(error ** 2)),
            'RMSE': float(np.sqrt(np.mean(error ** 2))), 'elements': int(error.size),
            'negative_prediction_fraction': float(np.mean(pred < 0))}

def report(pred, gold, reference):
    activity = {}
    for name in ('inactive', 'low', 'medium', 'high'):
        mask = groups[name]
        row = {'nodes': int(mask.sum()), 'status': 'ok' if mask.any() else 'empty'}
        if mask.any():
            row.update(basic(pred[:, mask], gold[:, mask]))
            ref_mae = basic(reference[:, mask], gold[:, mask])['MAE']
            row['NaiveRef_MAE'] = ref_mae
            row['relative_MAE_gain'] = (ref_mae - row['MAE']) / ref_mae if ref_mae else None
        activity[name] = row
    return {
        'overall': basic(pred, gold),
        'windows': [basic(pred[i], gold[i]) for i in range(len(pred))],
        'horizons': [basic(pred[:, :, h], gold[:, :, h]) for h in range(3)],
        'activity_groups': activity,
        'balanced_activity_group_MAE': float(np.mean([row['MAE'] for row in activity.values() if row['status'] == 'ok'])),
        'neighbor_groups': {name: basic(pred[:, groups[name]], gold[:, groups[name]])
                            for name in ('has_neighbor', 'isolated')},
        'contexts': {str(context): basic(pred[:, keys[:, 0] == context], gold[:, keys[:, 0] == context])
                     for context in np.unique(keys[:, 0])},
        'nonnegative_clipped_diagnostic': basic(np.maximum(pred, 0), gold),
    }

new_pred = tensors(output, 'pred', 4)
new_gold = tensors(output, 'gold', 4)
old_pred = tensors(old, 'pred', 4)
old_gold = tensors(old, 'gold', 4)
canonical = np.load(run / 'test-gold.npy').astype(np.float64)
assert np.array_equal(new_gold, old_gold) and np.array_equal(new_gold, canonical)
naive = np.load(run / 'test-naive.npz')
selected = json.loads((run / 'naive-selection.json').read_text())['NaiveRef']
reference = naive[selected]
new_metrics = basic(new_pred, new_gold)
old_metrics = basic(old_pred, old_gold)
for folder, metrics in ((output, new_metrics), (old, old_metrics)):
    recorded = json.loads((folder / 'metrics.json').read_text())
    assert all(abs(recorded[name] - metrics[name]) <= 0.01 for name in ('MAE', 'RMSE'))
relative_mae = abs(new_metrics['MAE'] - old_metrics['MAE']) / max(1, new_metrics['MAE'], old_metrics['MAE'])
val_pred = tensors(output, 'validation_pred', 1)
val_gold = tensors(output, 'validation_gold', 1)
assert np.array_equal(val_gold, np.load(run / 'validation-gold.npy').astype(np.float64))
val_reference = np.load(run / 'validation-naive.npz')[selected]
result = {
    'basis': 'saved predictions only; float64 recomputation', 'source_data_read': False, 'model_refit': False,
    'same_seed': 1, 'CUDA_relative_MAE_tolerance': 1e-4,
    'relative_MAE_difference': relative_mae, 'within_MAE_tolerance': relative_mae <= 1e-4,
    'max_absolute_prediction_difference': float(np.max(np.abs(new_pred - old_pred))),
    'per_window_max_absolute_prediction_difference': [float(np.max(np.abs(new_pred[i] - old_pred[i]))) for i in range(4)],
    'exact_prediction_match': bool(np.array_equal(new_pred, old_pred)), 'labels_identical': True,
    'old_seed1': report(old_pred, old_gold, reference),
    'new_seed1': report(new_pred, new_gold, reference),
    'validation': report(val_pred, val_gold, val_reference),
    'test_naive_baselines': {name: report(naive[name], new_gold, reference) for name in naive.files},
    'limits': ['Environment comparability requires condition-review.md',
               'MAE tolerance alone does not prove predictions or execution conditions are identical',
               'Node groups and overlapping windows are not independent trials'],
}
(run / 'comparison.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
print(json.dumps({name: result[name] for name in ('relative_MAE_difference', 'within_MAE_tolerance',
      'max_absolute_prediction_difference', 'exact_prediction_match', 'labels_identical')}, indent=2))
