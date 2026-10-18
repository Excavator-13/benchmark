import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

repo = Path(os.environ['T005_REPO']).resolve()
run = Path(os.environ['T005_RUN']).resolve()
old = Path(os.environ['T005_ORIGINAL']).resolve()
base = '950a1d8febbf992b8bda061d35f03107d0b18478'
sys.path.insert(0, str(repo / 'benchmark/graph_method'))
import main

def command(args):
    return subprocess.check_output(args, cwd=str(repo), text=True).strip()

def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()

def write(name, value):
    (run / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

freeze = command([sys.executable, '-m', 'pip', 'freeze'])
(run / 'pip-freeze.txt').write_text(freeze + '\n')
(run / 'git-status.txt').write_text(command(['git', 'status', '--short']) + '\n')
(run / 'git-commit.txt').write_text(command(['git', 'rev-parse', 'HEAD']) + '\n')
(run / 'nvidia-smi.txt').write_text(command(['nvidia-smi']) + '\n')
assert command(['git', 'rev-parse', 'HEAD']) == base, 'Wrong source commit'
assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'

sources = [
    'benchmark/graph_method/main.py', 'benchmark/graph_method/dataset.py',
    'benchmark/graph_method/prepare_graph_data.py',
    'benchmark/graph_method/models/__init__.py',
    'benchmark/graph_method/models/evolvegcnh.py',
    'dataset/demand/region.parquet', 'dataset/graph/region.parquet',
]
inputs = {}
for relative in sources:
    path = repo / relative
    assert command(['git', 'hash-object', str(path)]) == command(
        ['git', 'rev-parse', base + ':' + relative]), 'Changed source/input: ' + relative
    inputs[relative] = {'sha256': digest(path), 'bytes': path.stat().st_size}
generated = repo / 'benchmark/graph_method/data/count/region.json'
inputs[str(generated)] = {'sha256': digest(generated), 'bytes': generated.stat().st_size}
for name in ('guide.md', 'protocol.md'):
    path = run / name
    inputs[str(path)] = {'sha256': digest(path), 'bytes': path.stat().st_size}
write('inputs.json', inputs)

expected = {
    'torch': '2.3.0+cu121', 'torch-geometric': '2.4.0',
    'torch-geometric-temporal': '0.54.0', 'torch-scatter': '2.1.2+pt23cu121',
    'torch-sparse': '0.6.18+pt23cu121', 'numpy': '1.22.4',
    'pandas': '1.3.5', 'pyarrow': '14.0.1',
}
actual = {name: metadata.version(name) for name in expected}
assert torch.cuda.is_available(), 'No CUDA device'
device = torch.device('cuda:0')
gpu_name = torch.cuda.get_device_name(device)
environment = {
    'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
    'packages': actual, 'gpu': gpu_name, 'torch_cuda': torch.version.cuda,
    'cublas_workspace_config': os.environ['CUBLAS_WORKSPACE_CONFIG'],
}
write('environment.json', environment)
assert actual == expected, 'Core dependency versions differ; inspect saved environment'
assert 'T4' in gpu_name, 'GPU differs from old Tesla T4'

payload = json.loads(generated.read_text())
keys = np.asarray(payload['node_keys'], dtype=np.int64)
months = ['%04d-%02d' % (year, month)
          for year in range(2021, 2024) for month in range(1, 13)]
frame = pd.read_parquet(repo / 'dataset/demand/region.parquet')
assert [str(c) for c in frame.columns if str(c)[:4].isdigit()] == months
frame = frame.sort_values(['region_id', 'skill_id']).reset_index(drop=True)
assert not frame.duplicated(['region_id', 'skill_id']).any()
assert np.array_equal(keys, frame[['region_id', 'skill_id']].to_numpy())
values = frame[months].to_numpy(dtype=np.float64)
assert values.shape == (16345, 36)
assert np.isfinite(values).all() and (values >= 0).all()
assert np.array_equal(np.asarray(payload['features'], dtype=np.float32).T, values.astype(np.float32))
from prepare_graph_data import build_graph_dataset
assert payload == build_graph_dataset(
    frame, pd.read_parquet(repo / 'dataset/graph/region.parquet'), 'region', 'count'), 'Generated graph differs from source data'
activity = (values[:, :27] > 0).mean(axis=1)
edges = np.asarray(payload['edges'], dtype=np.int64).reshape(-1, 2)
covered = np.zeros(len(keys), dtype=bool)
nonself = edges[edges[:, 0] != edges[:, 1]]
covered[np.unique(nonself)] = True
masks = {
    'inactive': activity == 0,
    'low': (activity > 0) & (activity <= 1 / 3),
    'medium': (activity > 1 / 3) & (activity <= 2 / 3),
    'high': activity > 2 / 3,
    'has_neighbor': covered, 'isolated': ~covered,
}
assert int(covered.sum()) == 2185, 'Unexpected neighbor coverage'
np.savez_compressed(run / 'identity-and-groups.npz', node_keys=keys,
                    months=np.asarray(months), activity=activity, **masks)

config = main.ExperimentConfig(data_name='region', mode='count', model_name='EvolveGCNH',
                               device='cuda:0', seed=1, window_size=6,
                               pred_length=3, num_epochs=500)
dataset = main.load_dataset(config)
train, validation, test = main.temporal_signal_split(dataset, config.train_ratio, config.eval_ratio)
assert [part.snapshot_count for part in (train, validation, test)] == [19, 1, 4]
starts = {'train': list(range(19)), 'validation': [21], 'test': [24, 25, 26, 27]}
for name, part in [('train', train), ('validation', validation), ('test', test)]:
    for start, snapshot in zip(starts[name], part):
        assert np.array_equal(snapshot.x.numpy(), values[:, start:start + 6].astype(np.float32))
        assert np.array_equal(snapshot.y.numpy(), values[:, start + 6:start + 9].astype(np.float32))

naive_scores = {}
for name in ('validation', 'test'):
    positions = starts[name]
    gold = np.stack([values[:, start + 6:start + 9] for start in positions])
    predictions = {
        'Zero': np.zeros_like(gold),
        'LastValue': np.stack([np.repeat(values[:, start + 5:start + 6], 3, axis=1) for start in positions]),
        'WindowMean6': np.stack([np.repeat(values[:, start:start + 6].mean(axis=1, keepdims=True), 3, axis=1) for start in positions]),
        'TrainMean27': np.broadcast_to(values[:, :27].mean(axis=1)[None, :, None], gold.shape).copy(),
        'SeasonalNaive12': np.stack([values[:, start - 6:start - 3] for start in positions]),
    }
    np.save(run / (name + '-gold.npy'), gold.astype(np.float32))
    np.savez_compressed(run / (name + '-naive.npz'), **predictions)
    naive_scores[name] = {method: {'MSE': float(np.mean((pred - gold) ** 2)),
                                  'MAE': float(np.mean(np.abs(pred - gold)))}
                          for method, pred in predictions.items()}
selected = min(naive_scores['validation'], key=lambda method: naive_scores['validation'][method]['MSE'])
assert selected == 'LastValue'
write('naive-selection.json', {'criterion': 'validation MSE', 'NaiveRef': selected,
                               'scores': naive_scores})

old_identity = {}
canonical = np.load(run / 'test-gold.npy')
for seed in (0, 1):
    folder = old / str(seed)
    checkpoint = torch.load(folder / 'checkpoint.pt', map_location='cpu', weights_only=True)
    assert checkpoint['seed'] == seed
    assert checkpoint['config']['model_name'] == 'EvolveGCNH'
    assert checkpoint['config']['window_size'] == 6 and checkpoint['config']['pred_length'] == 3
    pred = [torch.load(folder / ('pred_%d.pt' % i), map_location='cpu', weights_only=True) for i in range(4)]
    gold = [torch.load(folder / ('gold_%d.pt' % i), map_location='cpu', weights_only=True) for i in range(4)]
    assert all(torch.isfinite(p).all() for p in pred)
    assert all(np.array_equal(g.numpy(), canonical[i]) for i, g in enumerate(gold))
    recalculated = main.regression_metrics(pred, gold)
    recorded = json.loads((folder / 'metrics.json').read_text())
    assert all(abs(recalculated[key] - recorded[key]) <= 0.01 for key in ('MAE', 'RMSE'))
    old_identity[str(seed)] = {
        'path': str(folder), 'recorded_metrics': recorded, 'recalculated': recalculated,
        'files': {p.name: digest(p) for p in sorted(folder.iterdir()) if p.is_file()},
    }
write('original-results.json', old_identity)
write('preflight.json', {'status': 'passed', 'source_commit': base, 'nodes': len(keys),
                       'splits': starts, 'activity_counts': {k: int(v.sum()) for k, v in masks.items()},
                       'environment_review_required': True})
print(json.dumps(environment, indent=2))
print('Preflight passed. Review the complete environment before training.')
