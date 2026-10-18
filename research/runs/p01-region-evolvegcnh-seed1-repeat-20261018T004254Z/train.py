import datetime
import hashlib
import json
import os
import resource
import sys
import time
import traceback
from pathlib import Path

import torch

repo = Path(os.environ['T005_REPO']).resolve()
run = Path(os.environ['T005_RUN']).resolve()
sys.path.insert(0, str(repo / 'benchmark/graph_method'))
import main

def write(name, value):
    (run / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

assert json.loads((run / 'preflight.json').read_text())['status'] == 'passed'
assert (run / 'condition-review.md').is_file(), 'Write the environment review first'
assert not (run / 'status.json').exists(), 'Already attempted; use a new run ID'
assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
inputs = json.loads((run / 'inputs.json').read_text())
for name, record in inputs.items():
    path = Path(name) if Path(name).is_absolute() else repo / name
    checksum = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            checksum.update(chunk)
    assert checksum.hexdigest() == record['sha256'], 'Input/source changed since preflight: ' + name

config = main.ExperimentConfig(data_name='region', mode='count', model_name='EvolveGCNH',
                               device='cuda:0', seed=1, window_size=6,
                               pred_length=3, num_epochs=500, results_dir=run / 'outputs')
output = main.result_dir(config)
assert not output.exists(), 'Refusing to overwrite ' + str(output)
parsed = dict(config.__dict__)
parsed['results_dir'] = str(config.results_dir)
parsed['data_dir'] = None
parsed['learning_rate'] = main.DEFAULT_LEARNING_RATE
parsed['optimizer'] = 'Adam'
parsed['input_scale'] = 'raw count'
write('config.json', parsed)
write('status.json', {'status': 'running', 'started_at': now()})
write('provenance.json', {
    'task_id': 'P01-T005', 'run_id': run.name, 'source_commit': json.loads((run / 'preflight.json').read_text())['source_commit'],
    'scientific_protocol': 'P1-count-L6-H3-v3', 'records_policy': 'P01-records-v2',
    'protocol_snapshot': 'protocol.md', 'executed_commands': 'guide.md sections 5-7',
    'inputs': 'inputs.json', 'environment': 'environment.json', 'condition_review': 'condition-review.md',
    'config': 'config.json', 'training_trace': 'training-trace.jsonl',
    'limitations': ['Published graph construction cutoff unknown; fixed-period evidence only'],
})
started = now()
clock_start = time.perf_counter()
trace = []
original_run_split = main.run_split

try:
    device = main.resolve_device(config.device)
    torch.cuda.init()
    torch.cuda.reset_peak_memory_stats(device)
    load_start = time.perf_counter()
    dataset = main.load_dataset(config)
    train, validation, test = main.temporal_signal_split(dataset, config.train_ratio, config.eval_ratio)
    load_seconds = time.perf_counter() - load_start

    def recorded_run_split(model, iterator, device, **kwargs):
        result = original_run_split(model, iterator, device, **kwargs)
        if iterator is train or iterator is validation:
            row = {'stage': 'train' if iterator is train else 'validation',
                   'epoch': len(trace) // 2 + 1, 'MSE': result.loss,
                   'optimizer_steps': result.optimizer_steps}
            trace.append(row)
            with (run / 'training-trace.jsonl').open('a') as handle:
                handle.write(json.dumps(row, allow_nan=False) + '\n')
        return result

    main.run_split = recorded_run_split
    torch.cuda.synchronize(device)
    train_start = time.perf_counter()
    metrics = main.train_experiment(config, train, validation, test, device=device)
    torch.cuda.synchronize(device)
    training_and_test_seconds = time.perf_counter() - train_start
    main.run_split = original_run_split

    validation_rows = [row for row in trace if row['stage'] == 'validation']
    assert len(validation_rows) == 500 and len(trace) == 1000
    selected = min(validation_rows, key=lambda row: row['MSE'])
    restored = main.load_checkpoint(output / 'checkpoint.pt', device)
    assert abs(restored.best_val_loss - selected['MSE']) <= 1e-8
    result = original_run_split(restored.model, validation, device, collect_predictions=True)
    for i, (pred, gold) in enumerate(zip(result.predictions, result.golds)):
        torch.save(pred, output / ('validation_pred_%d.pt' % i))
        torch.save(gold, output / ('validation_gold_%d.pt' % i))
    write('selection.json', {'criterion': 'validation MSE', 'tie_rule': 'first minimum',
                              'selected_epoch': selected['epoch'], 'best_validation_MSE': selected['MSE'],
                              'reloaded_validation_MSE': result.loss,
                              'reloaded_validation_metrics': main.regression_metrics(result.predictions, result.golds)})
    torch.cuda.synchronize(device)
    write('cost.json', {
        'load_seconds': load_seconds, 'training_and_test_seconds': training_and_test_seconds,
        'total_seconds_including_extra_validation': time.perf_counter() - clock_start,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'peak_cuda_allocated_bytes': torch.cuda.max_memory_allocated(device),
        'peak_cuda_reserved_bytes': torch.cuda.max_memory_reserved(device),
        'device': torch.cuda.get_device_name(device), 'RSS_unit_basis': 'Linux ru_maxrss in KiB',
    })
    write('status.json', {'status': 'succeeded', 'started_at': started, 'ended_at': now()})
    print(json.dumps(metrics, indent=2))
    print('Output:', output)
except BaseException as error:
    main.run_split = original_run_split
    write('status.json', {'status': 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
                          'started_at': started, 'ended_at': now(), 'error': repr(error)})
    traceback.print_exc()
    raise
