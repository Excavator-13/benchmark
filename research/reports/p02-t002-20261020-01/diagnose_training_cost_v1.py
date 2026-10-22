"""Observe frozen training without counting an interrupted diagnostic as a fit.

Run only after implementation acceptance, without concurrent heavy processes.
No loss/score affects the stop decision; the requested budget remains 200 epochs.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path.cwd().resolve()
if not (ROOT / 'benchmark/graph_value_skeleton/runner.py').is_file():
    raise SystemExit('Run from the implementation repository root')
sys.path.insert(0, str(ROOT))
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'
import torch  # Windows: import before pandas/Arrow.
from benchmark.graph_value_skeleton import artifacts, runner, training
from benchmark.graph_value_skeleton.config import resolve_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--deadline-utc', required=True)
    parser.add_argument('--dataset', choices=('r0', 'region', 'r2'), default='r2')
    parser.add_argument('--method', choices=('self', 'graph', 'shuffled'), default='self')
    parser.add_argument('--shuffle-artifact')
    args = parser.parse_args()
    deadline = datetime.fromisoformat(args.deadline_utc).astimezone(timezone.utc)
    config = resolve_config(data_name=args.dataset, method=args.method,
        model_seed=0, shuffle_seed=0 if args.method == 'shuffled' else None,
        run_id=args.run_id, output_root=args.output_root.resolve(), repo_root=ROOT,
        shuffle_artifact=args.shuffle_artifact,
        command=[sys.executable, *sys.argv], launcher_cwd=Path.cwd())
    # Exactly six fits share this dataset/method (three model seeds, two repeats).
    # For shuffled, this deliberately counts seed0 only, omitting seeds1/2.
    observed = {'purpose': 'incomplete operational cost diagnostic',
        'formal_run': False, 'requested_epochs': 200, 'steps_observed': 0,
        'validated_completed_epochs_at_least': 0,
        'dataset': args.dataset, 'method': args.method,
        'deadline_utc': deadline.isoformat(), 'command': [sys.executable, *sys.argv],
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'intervals_seconds': [], 'forecast_fit_count': 6,
        'forecast_scope': 'only this dataset/method/shuffle-seed; other fits and checks omitted',
        'limitation': 'short serial sample, extrapolation assumes stable epoch cost; not a completed fit'}
    evidence = config.run_dir / 'cost-observation.json'

    def save():
        temporary = evidence.with_suffix('.tmp')
        temporary.write_text(json.dumps(observed, indent=2), encoding='utf-8')
        os.replace(temporary, evidence)

    original_train = training.train
    original_step = torch.optim.Adam.step
    last_step = None

    def wrapped_train(*positional, **keywords):
        observed.update(chunks_per_epoch=len(keywords['chunks']),
                        nodes=keywords['node_count'])
        save()
        return original_train(*positional, **keywords)

    def wrapped_step(optimizer, *positional, **keywords):
        nonlocal last_step
        result = original_step(optimizer, *positional, **keywords)
        current = time.perf_counter()
        observed['steps_observed'] += 1
        observed['validated_completed_epochs_at_least'] = observed['steps_observed'] - 1
        if last_step is not None:
            observed['intervals_seconds'].append(current - last_step)
        last_step = current
        remaining = max(0., (deadline - datetime.now(timezone.utc)).total_seconds())
        observed['seconds_until_deadline'] = remaining
        observed['process_peak_memory'] = artifacts.measure_peak_rss()
        if observed['intervals_seconds']:
            fastest = min(observed['intervals_seconds'])
            observed.update(fastest_interval_seconds=fastest,
                projected_seconds_six_fits=fastest * 200 * 6,
                projected_seconds_six_fits_at_twice_speed=fastest * 200 * 6 / 2)
        save()
        print(json.dumps(observed), flush=True)
        if observed['steps_observed'] >= 3:
            misses = observed['projected_seconds_six_fits_at_twice_speed'] > remaining
            observed.update(stop_reason=('deadline infeasible even at twice measured speed'
                                         if misses else 'bounded diagnostic sample complete'),
                            forecast_infeasible=misses)
            save()
            raise runner.RunInterrupted(observed['stop_reason'])
        return result

    training.train = wrapped_train
    torch.optim.Adam.step = wrapped_step
    try:
        runner.execute_run(config)
    except runner.RunInterrupted:
        status = json.loads((config.run_dir / 'status.json').read_text(encoding='utf-8'))
        assert status['state'] == 'interrupted', status
        assert not (config.run_dir / 'models' / 'selected.npz').exists()
        print('Diagnostic preserved as interrupted; no completed model or formal result.', flush=True)
    finally:
        training.train = original_train
        torch.optim.Adam.step = original_step


if __name__ == '__main__':
    main()
