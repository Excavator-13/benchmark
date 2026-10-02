"""Audit saved Region forecasts without importing or rerunning the model."""

import hashlib
import json
import re
import statistics
import tarfile
from pathlib import Path

import fitz
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RESULTS = ROOT / 'benchmark/benchmark-try/graph_method/results/count/region/EvolveGCNH'


def load(path):
    with path.open('rb') as handle:
        return torch.load(handle, map_location='cpu', weights_only=True)


def metrics(pred, gold):
    error = np.asarray(pred, dtype=np.float64) - np.asarray(gold, dtype=np.float64)
    return {'MAE': float(np.abs(error).mean()), 'RMSE': float(np.sqrt((error ** 2).mean()))}


def main():
    payload = json.loads((ROOT / 'benchmark/benchmark-try/graph_method/data/count/region.json').read_text(encoding='utf-8'))
    features = np.array(payload['features'], dtype=np.float32)
    keys = np.array(payload['node_keys'])
    gold = np.stack([load(RESULTS / '0' / f'gold_{i}.pt').numpy() for i in range(4)])
    starts = []
    for target in gold:
        matches = [i for i in range(features.shape[0] - 2) if np.array_equal(features[i:i + 3].T, target)]
        assert len(matches) == 1, matches
        starts.append(matches[0])
    report = {'shape': list(gold.shape), 'target_start_month_indices': starts, 'runs': {}, 'baselines': {}}
    for seed in (0, 1):
        directory = RESULTS / str(seed)
        pred = np.stack([load(directory / f'pred_{i}.pt').numpy() for i in range(4)])
        other_gold = np.stack([load(directory / f'gold_{i}.pt').numpy() for i in range(4)])
        assert np.array_equal(gold, other_gold)
        assert np.isfinite(pred).all()
        checkpoint = load(directory / 'checkpoint.pt')
        published = json.loads((directory / 'metrics.json').read_text())
        recomputed = metrics(pred, gold)
        assert all(np.isclose(published[k], recomputed[k], rtol=1e-6) for k in published)
        error = pred.astype(np.float64) - gold
        squared = error ** 2
        ordered = np.sort(squared.ravel())[::-1]
        high = gold >= np.quantile(gold, 0.99)
        subsets = {}
        for name, lower, upper in [('zero', 0, 1), ('1_to_9', 1, 10), ('10_to_99', 10, 100), ('100_to_999', 100, 1000), ('1000_plus', 1000, np.inf)]:
            mask = (gold >= lower) & (gold < upper)
            subsets[name] = {'n': int(mask.sum()), **metrics(pred[mask], gold[mask]), 'squared_error_share': float(squared[mask].sum() / squared.sum())}
        top_nodes = np.argsort(squared.sum(axis=(0, 2)))[-10:][::-1]
        diagnostics = {
            'stored_metrics': published, 'recomputed_metrics': recomputed,
            'checkpoint_config': checkpoint['config'], 'checkpoint_seed': checkpoint['seed'],
            'best_val_loss': float(checkpoint['best_val_loss']),
            'snapshot_metrics': [metrics(p, g) for p, g in zip(pred, gold)],
            'horizon_metrics': [metrics(pred[:, :, h], gold[:, :, h]) for h in range(3)],
            'prediction_mean': float(pred.mean()), 'gold_mean': float(gold.mean()),
            'prediction_min': float(pred.min()), 'prediction_max': float(pred.max()),
            'negative_prediction_fraction': float((pred < 0).mean()),
            'bias': float(error.mean()), 'subsets': subsets,
            'largest_1pct_errors_squared_share': float(ordered[:int(np.ceil(ordered.size * 0.01))].sum() / ordered.sum()),
            'highest_1pct_gold_squared_share': float(squared[high].sum() / squared.sum()),
            'region_metrics': {str(region): metrics(pred[:, keys[:, 0] == region, :], gold[:, keys[:, 0] == region, :]) for region in np.unique(keys[:, 0])},
            'top_error_nodes': [{'key': keys[i].tolist(), 'squared_error_share': float(squared[:, i, :].sum() / squared.sum()), 'pred_mean': float(pred[:, i, :].mean()), 'gold_mean': float(gold[:, i, :].mean())} for i in top_nodes],
        }
        for name in ['structural_breaks_index', 'low_frequency_index']:
            indices = json.loads((ROOT / f'benchmark/dataset/{name}/region.json').read_text())
            diagnostics[name + '_metadata'] = {'type': type(indices).__name__, 'length': len(indices)}
            # Published indices refer to original row order; avoid assuming alignment.
        duplicate = ROOT / f'benchmark/benchmark-try/benchmark/graph_method/results/count/region/EvolveGCNH/{seed}'
        diagnostics['duplicate_files_identical'] = all(hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256((duplicate / p.name).read_bytes()).digest() for p in directory.iterdir() if p.is_file())
        report['runs'][str(seed)] = diagnostics
    for name, pred in {
        'zero': np.zeros_like(gold),
        'last_observation': np.stack([np.repeat(features[s-1, :, None], 3, axis=1) for s in starts]),
        'last_6_month_mean': np.stack([np.repeat(features[s-6:s].mean(axis=0)[:, None], 3, axis=1) for s in starts]),
        'seasonal_12_month': np.stack([features[s-12:s-9].T for s in starts]),
    }.items():
        report['baselines'][name] = metrics(pred, gold)
    report['summary'] = {k: {'mean': statistics.mean([report['runs'][str(s)]['stored_metrics'][k] for s in (0, 1)]), 'population_std': statistics.pstdev([report['runs'][str(s)]['stored_metrics'][k] for s in (0, 1)]), 'sample_std': statistics.stdev([report['runs'][str(s)]['stored_metrics'][k] for s in (0, 1)])} for k in ('MAE', 'RMSE')}
    archive = next(ROOT.parents[1].glob('evolvegcn*.tar.gz'))
    with tarfile.open(archive) as tf:
        report['archive_environment'] = {m.name: tf.extractfile(m).read().decode('utf-8', errors='replace') for m in tf.getmembers() if m.isfile() and m.name.startswith('logs/') and not m.name.endswith('.log')}
        report['logs'] = {}
        for seed in (0, 1):
            name = f'logs/evolvegcnh-region-count-seed-{seed}.log'
            log = tf.extractfile(name).read().decode('utf-8', errors='replace')
            values = re.findall(r'best_val_loss=([0-9.]+)', log)
            epochs = re.findall(r'(\d+)/500', log)
            report['logs'][str(seed)] = {'reached_epoch': max(map(int, epochs)) if epochs else None, 'first_best_val_loss': float(values[0]) if values else None, 'last_best_val_loss': float(values[-1]) if values else None, 'unique_best_val_losses': len(set(values)), 'tail': log[-1500:]}
    paper = next(ROOT.parents[1].glob('NeurIPS*.pdf'))
    document = fitz.open(paper)
    for i in (3, 16, 17, 20, 21):
        (OUT / f'paper_page_{i+1}.txt').write_text(document[i].get_text(), encoding='utf-8')
    document[20].get_pixmap(matrix=fitz.Matrix(1.7, 1.7)).save(OUT / 'paper_table9.png')
    (OUT / 'analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['shape', 'target_start_month_indices', 'summary', 'baselines', 'logs']}, ensure_ascii=False, indent=2))
    print('Run diagnostics:', json.dumps({s: {k: v for k, v in run.items() if k not in ['subsets', 'top_error_nodes', 'region_metrics']} for s, run in report['runs'].items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
