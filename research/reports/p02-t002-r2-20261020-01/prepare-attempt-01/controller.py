"""Sequential r2-only formal batch through the frozen public CLI.

Run prepare, then run, from an independent repository with adequate free disk.
No training code is patched. Interrupted/failed IDs are never reused. The
controller writes durable progress and stops scheduling on any failed check.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[variable] = '1'
os.environ['PYTHONUTF8'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
EXPECTED = {'numpy': '1.26.4', 'pandas': '2.2.3', 'pyarrow': '17.0.0', 'torch': '2.14.1'}
PREPARED = ROOT / 'scratch/graph-value-skeleton/repair-shuffle-v2-20261020-06/graphs'
WRITER = None


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, payload):
    # Reuse the independently verified Windows atomic replacement retries.
    writer = WRITER(Path(path).parent, 'controller-writer', 'orchestration')
    writer.path = Path(path).parent
    return writer.write_json(Path(path).name, payload)


def identities():
    files = []
    for package in ('graph_value_skeleton', 'nograph_baseline'):
        files += [p for p in (ROOT / 'benchmark' / package).rglob('*.py')
                  if 'tests' not in p.parts and '__pycache__' not in p.parts]
    files += [ROOT / 'benchmark/__init__.py', ROOT / 'research/phases/P01/protocol.md']
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(files)}


def schedule(batch):
    axes = []
    for seed in range(3):
        for method, shuffle in [('shuffled', 0), ('shuffled', 1), ('shuffled', 2),
                                ('self', None), ('graph', None)]:
            for repeat in ('a', 'b'):
                label = method + (str(shuffle) if shuffle is not None else '')
                axes.append({'dataset': 'r2', 'method': method, 'shuffle_seed': shuffle,
                    'model_seed': seed, 'repeat': repeat,
                    'run_id': f'{batch}-r2-{label}-s{seed}-{repeat}'})
    return axes


def prepared_identity():
    return {str(seed): {p.name: digest(p) for p in sorted((PREPARED / f'r2-shuffle{seed}-a').iterdir())
                        if p.is_file()} for seed in range(3)}


def runtime_versions():
    return {name: importlib.metadata.version(name) for name in EXPECTED}


def verify_frozen(saved):
    preflight = read(saved / 'preflight.json')
    assert preflight['status'] == 'ok'
    assert preflight['source'] == identities(), 'Runtime source or protocol changed'
    assert preflight['versions'] == runtime_versions(), 'Runtime packages changed'
    assert preflight['python'] == sys.executable, 'Interpreter changed'
    assert preflight['controller_sha256'] == digest(__file__), 'Controller changed'
    assert preflight['prepared_files'] == prepared_identity(), 'Prepared graph changed'
    for relative, expected in preflight['inputs'].items():
        assert digest(ROOT / relative) == expected, f'Input changed: {relative}'


def prepare(saved, batch):
    assert not (saved / 'preflight.json').exists(), 'Fresh batch required'
    assert sys.version_info[:2] == (3, 11)
    versions = runtime_versions()
    assert all(versions[name].split('+')[0] == value for name, value in EXPECTED.items())
    import torch
    from benchmark.graph_value_skeleton import data, graph, protocol, prepared
    assert torch.version.cuda is None
    assert protocol.EPOCHS == 200 and protocol.HIDDEN_DIM == 32
    assert tuple(protocol.DEVELOPMENT_MODEL_SEEDS) == (0, 1, 2)
    assert tuple(protocol.SHUFFLE_SEEDS) == (0, 1, 2)
    free = shutil.disk_usage(ROOT).free
    assert free > 8 * 1024**3, 'Need at least 8 GiB free before starting'
    dataset = data.load_dataset('r2')
    original = graph.load_graph('r2', dataset.key_array)
    graph_results = {}
    for seed in range(3):
        shuffled, provenance = prepared.load(PREPARED / f'r2-shuffle{seed}-a',
            keys=dataset.key_array, source_edges=original.edges,
            data_name='r2', shuffle_seed=seed, require_current_generator=True)
        graph_results[str(seed)] = shuffled.identity_payload()
        del shuffled, provenance
    axes = schedule(batch)
    assert len(axes) == 30 and len({a['run_id'] for a in axes}) == 30
    for axis in axes:
        assert not (ROOT / 'research/runs' / axis['run_id']).exists(), 'Run ID already exists'
    payload = {'task': 'P02-T002', 'batch': batch, 'status': 'ok', 'created_at': now(),
        'root': str(ROOT), 'python': sys.executable, 'python_version': sys.version,
        'versions': versions, 'source': identities(), 'controller_sha256': digest(__file__),
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'prepared_files': prepared_identity(), 'prepared_graphs': graph_results,
        'nodes': dataset.node_count, 'disk_free_bytes': free,
        'inputs': {f'dataset/{kind}/r2.parquet': digest(ROOT / f'dataset/{kind}/r2.parquet')
                   for kind in ('demand', 'graph')}}
    del original, dataset
    gc.collect()
    write(saved / 'preflight.json', payload)
    write(saved / 'manifest.json', {'batch': batch, 'formal_count': 30, 'schedule': axes,
        'checks': {'recompute': 30, 'repeat_compare': 15, 'three_graph_average': 6},
        'frozen_epochs': 200, 'concurrent_training_processes': 1})
    write(saved / 'cost-confirmation.json', {'status': 'accepted', 'created_at': now(),
        'basis': 'User authorized r2 after reviewing 11.90h shuffled/rough 20h all-r2 forecast and removed the old deadline.',
        'scope': 'r2 only, 30 complete fits and 51 saved-result checks',
        'historical_cost': 'research/reports/p02-t002-20261020-01/cost-decision.json',
        'historical_cost_sha256': digest(ROOT / 'research/reports/p02-t002-20261020-01/cost-decision.json'),
        'estimated_seconds': 20 * 3600, 'estimate_kind': 'short-sample extrapolation; self/graph unmeasured',
        'deadline_utc': None, 'epochs': 200, 'scientific_configuration_changed': False})
    print(json.dumps({'preflight': 'ok', 'formal_count': 30, 'root': str(ROOT)}), flush=True)


class Controller:
    def __init__(self, saved, scratch, batch, push_on_success=False):
        self.saved, self.scratch, self.batch = saved, scratch, batch
        self.completed, self.timings = [], []
        self.active = None
        self.push_on_success = push_on_success

    def progress(self, **extra):
        seconds = sum(t['seconds'] for t in self.timings)
        per_method = {}
        for item in self.timings:
            per_method.setdefault(item['method'], []).append(item['seconds'])
        estimates = {key: sum(values)/len(values) for key, values in per_method.items()}
        # Preserve the prior rough estimate for unmeasured branches.
        default = estimates.get('shuffled', 2400.)
        remaining = sum(estimates.get(a['method'], default)
            for a in schedule(self.batch) if a['run_id'] not in self.completed)
        if self.active:
            remaining = max(0., remaining - self.active.get('elapsed_seconds', 0.))
        payload = {'task': 'P02-T002', 'batch': self.batch, 'status': 'running',
            'pid': os.getpid(), 'root': str(ROOT), 'updated_at': now(),
            'completed_verified_fits': len(self.completed), 'total_fits': 30,
            'completed': self.completed, 'active': self.active,
            'completed_fit_worker_wall_seconds': seconds,
            'remaining_training_seconds_estimate': remaining,
            'estimated_finish_utc': (datetime.now(timezone.utc) + timedelta(seconds=remaining)).isoformat(),
            'forecast_limitations': 'Excludes remaining checks/startup; unmeasured methods use shuffled estimate or 2400s/fit.',
            **extra}
        write(self.saved / 'progress.json', payload)

    def invoke(self, arguments, name, training=False):
        verify_frozen(self.saved)
        if (self.saved / 'STOP_AFTER_CURRENT').exists():
            raise RuntimeError('STOP_AFTER_CURRENT requested; stopped at process boundary')
        assert shutil.disk_usage(ROOT).free > 1024**3, 'Free disk below 1 GiB'
        log = self.scratch / 'logs' / f'{name}.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, '-B', '-m', 'benchmark.graph_value_skeleton', *map(str, arguments)]
        started = time.monotonic()
        monitor = {'name': name, 'command': command, 'cwd': str(ROOT), 'started_at': now()}
        print(f'{now()} START {name}', flush=True)
        with log.open('x', encoding='utf-8') as stream:
            child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            monitor['child_pid'] = child.pid
            self.active = {**monitor, 'elapsed_seconds': 0.}
            self.progress()
            try:
                while child.poll() is None:
                    elapsed = time.monotonic() - started
                    self.active['elapsed_seconds'] = elapsed
                    self.progress()
                    if (self.saved / 'STOP_NOW').exists() or elapsed > (4*3600 if training else 1800):
                        cleanup = subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                            capture_output=True, text=True, errors='replace', timeout=30)
                        monitor['cleanup'] = {'returncode': cleanup.returncode,
                            'stdout': cleanup.stdout, 'stderr': cleanup.stderr}
                        monitor['worker_may_be_running'] = cleanup.returncode != 0
                        raise RuntimeError('Stop/operational watchdog; see monitor cleanup evidence')
                    time.sleep(15)
            except BaseException:
                if child.poll() is None and 'cleanup' not in monitor:
                    try:
                        cleanup = subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                            capture_output=True, text=True, errors='replace', timeout=30)
                        monitor['cleanup'] = {'returncode': cleanup.returncode,
                            'stdout': cleanup.stdout, 'stderr': cleanup.stderr}
                        monitor['worker_may_be_running'] = cleanup.returncode != 0
                    except Exception as cleanup_error:
                        monitor['cleanup_error'] = str(cleanup_error)
                        monitor['worker_may_be_running'] = True
                monitor.update(elapsed_seconds=time.monotonic()-started,
                               exit_code=child.poll(), finished_at=now())
                write(self.saved / 'monitor' / f'{name}.json', monitor)
                raise
        monitor.update(elapsed_seconds=time.monotonic()-started, exit_code=child.returncode,
                       finished_at=now(), log=log.relative_to(ROOT).as_posix())
        write(self.saved / 'monitor' / f'{name}.json', monitor)
        self.active = None
        assert child.returncode == 0, f'{name}: exit {child.returncode}, see {log}'
        print(f'{now()} DONE {name} ({monitor["elapsed_seconds"]:.1f}s)', flush=True)
        return monitor

    def check(self, arguments, name):
        original = self.scratch / 'checks' / f'{name}.json'
        persistent = self.saved / 'checks' / f'{name}.json'
        assert not original.exists() and not persistent.exists()
        self.invoke([*arguments, '--report', original], name)
        assert read(original)['status'] == 'ok', original
        persistent.parent.mkdir(parents=True, exist_ok=True)
        with persistent.open('xb') as stream:
            stream.write(original.read_bytes())
        assert digest(persistent) == digest(original)
        write(self.saved / 'check-copies' / f'{name}.json', {
            'source': original.relative_to(ROOT).as_posix(),
            'saved': persistent.relative_to(ROOT).as_posix(), 'sha256': digest(persistent)})

    def run(self):
        assert read(self.saved / 'cost-confirmation.json')['status'] == 'accepted'
        axes = read(self.saved / 'manifest.json')['schedule']
        assert axes == schedule(self.batch)
        assert not (self.saved / 'controller.json').exists(), 'No duplicate or automatic resume'
        write(self.saved / 'controller.json', {'pid': os.getpid(), 'started_at': now(),
            'root': str(ROOT), 'command': [sys.executable, *sys.argv],
            'controller_sha256': digest(__file__), 'push_on_success': self.push_on_success})
        for axis in axes:
            rid = axis['run_id']
            directory = ROOT / 'research/runs' / rid
            assert not directory.exists(), 'Never overwrite or retry an existing run'
            args = ['run', '--data-name', 'r2', '--method', axis['method'],
                '--model-seed', str(axis['model_seed']), '--purpose', 'formal', '--run-id', rid]
            if axis['shuffle_seed'] is not None:
                args += ['--shuffle-seed', str(axis['shuffle_seed']), '--shuffle-artifact',
                         PREPARED / f'r2-shuffle{axis["shuffle_seed"]}-a']
            monitor = self.invoke(args, rid, training=True)
            assert read(directory / 'status.json')['state'] == 'success'
            measurements = read(directory / 'measurements.json')
            assert measurements['input']['epochs'] == 200
            assert len(read(directory / 'training-history.json')['rows']) == 200
            self.check(['recompute', '--run-dir', directory], rid + '-recompute')
            if axis['repeat'] == 'b':
                self.check(['compare', '--run-a', directory.with_name(rid[:-1]+'a'),
                            '--run-b', directory], rid[:-1]+'repeat')
            self.completed.append(rid)
            self.timings.append({'method': axis['method'], 'run_id': rid,
                                 'seconds': monitor['elapsed_seconds']})
            write(self.saved / 'timings.json', self.timings)
            self.progress()
        for seed in range(3):
            for repeat in ('a', 'b'):
                members = [ROOT / 'research/runs' / f'{self.batch}-r2-shuffled{s}-s{seed}-{repeat}'
                           for s in range(3)]
                self.check(['summarize-shuffled', '--run-dirs', *members],
                           f'{self.batch}-r2-s{seed}-{repeat}-shuffled-summary')
        checks = list((self.saved / 'checks').glob('*.json'))
        assert len(checks) == 51 and all(read(p)['status'] == 'ok' for p in checks)
        verify_frozen(self.saved)
        completion = {'status': 'r2_ready_for_research_acceptance', 'batch': self.batch,
            'completed_at': now(), 'formal_fits': 30, 'successful_checks': 51,
            'remaining_T002_scope': 'r0 and region are not run by this batch',
            'no_T003_or_graph_benefit_verdict': True}
        write(self.saved / 'completion.json', completion)
        total = sum(item['seconds'] for item in self.timings)
        result = ('# r2 execution result\n\n'
            f'Batch: {self.batch}\n\n'
            f'Completed at: {completion["completed_at"]}\n\n'
            '30 formal fits completed at 200 epochs each; all 51 saved-result checks passed '
            '(30 recomputes, 15 same-condition repeat comparisons, 6 three-graph averages).\n\n'
            f'Total fitted-worker wall time: {total:.3f} seconds. See timings.json for individual measurements.\n\n'
            'This completes the r2 execution block only. Full P02-T002 acceptance still requires '
            'r0 and region. No graph-benefit or T003 verdict is made. Expanded arrays remain '
            'local in this D: execution repository; Git contains readable run records and checks.\n')
        writer = WRITER(self.saved.parent, self.saved.name, 'orchestration')
        writer.write_text('result.md', result)
        self.progress(status='complete_r2', active=None)
        if self.push_on_success:
            self.publish()

    def publish(self):
        # Only this completed batch, its controller, and its readable run records.
        # The original C: repository and unrelated work are never staged here.
        paths = [str(self.saved.relative_to(ROOT)), str(Path(__file__).relative_to(ROOT)),
                 '.gitattributes', 'research/state.md', 'research/decisions.md',
                 'research/phases/P02/plan.md', 'research/phases/P02/t002-execution.md',
                 'research/archives/index.md']
        for rid in self.completed:
            for name in ('summary.md', 'provenance.json', 'command.json'):
                path = ROOT / 'research/runs' / rid / name
                assert path.is_file()
                paths.append(path.relative_to(ROOT).as_posix())
        assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).strip()
        publication = {'status': 'publishing', 'started_at': now(),
                       'remote': 'origin', 'branch': 'FJWP2T002'}
        write(self.saved / 'publication.json', publication)
        try:
            subprocess.run(['git', 'add', '--', *paths], check=True)
            subprocess.run(['git', 'commit', '-m', f'Complete verified r2 batch {self.batch}'], check=True)
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
            subprocess.run(['git', 'push', 'origin', 'HEAD:refs/heads/FJWP2T002'], check=True, timeout=180)
            publication.update(status='pushed', commit=commit, finished_at=now())
        except Exception as exc:
            publication.update(status='publication_failed', error=str(exc), finished_at=now())
            raise
        finally:
            # Local receipt only; never create a self-referential receipt commit.
            write(self.saved / 'publication.json', publication)


def main():
    global WRITER
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run'))
    parser.add_argument('--batch', default='p02-t002-r2-20261020-01')
    parser.add_argument('--push-on-success', action='store_true')
    args = parser.parse_args()
    import torch  # Windows: load before Arrow/pandas.
    from benchmark.nograph_baseline.artifacts import RunDirectory, validate_run_id
    WRITER = RunDirectory
    validate_run_id(args.batch)
    saved = ROOT / 'research/reports' / args.batch
    scratch = ROOT / 'scratch/graph-value-skeleton' / args.batch
    saved.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    temp = scratch / 'temp'
    temp.mkdir(exist_ok=True)
    os.environ['TMP'] = os.environ['TEMP'] = str(temp)
    controller = Controller(saved, scratch, args.batch, args.push_on_success)
    try:
        if args.mode == 'prepare':
            prepare(saved, args.batch)
        else:
            controller.run()
    except BaseException as exc:
        controller.progress(status='paused', error=f'{type(exc).__name__}: {exc}',
                            traceback=traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
