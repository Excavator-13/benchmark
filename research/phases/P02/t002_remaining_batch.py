"""Execute one remaining T002 dataset with the verified r2 orchestration core.

Region and r0 run sequentially in separate fresh batches. This adapter changes
dataset routing and publication scope, never training or saved-result check code.
"""
from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('t002_verified_core', Path(__file__).with_name('t002_r2_batch.py'))
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
DATASET = None
ORIGINAL_SCHEDULE = core.schedule
ORIGINAL_VERIFY = core.verify_frozen
GROUP = 'p02-t002-remaining-20261022-01'
BATCHES = {'region': 'p02-t002-region-20261022-01', 'r0': 'p02-t002-r0-20261022-01'}


def schedule(batch):
    assert DATASET in ('region', 'r0')
    return [{**a, 'dataset': DATASET, 'run_id': a['run_id'].replace('-r2-', f'-{DATASET}-')}
            for a in ORIGINAL_SCHEDULE(batch)]


def prepared_identity():
    return {str(seed): {p.name: core.digest(p) for p in sorted(
        (core.PREPARED / f'{DATASET}-shuffle{seed}-a').iterdir()) if p.is_file()}
        for seed in range(3)}


def verify_frozen(saved):
    ORIGINAL_VERIFY(saved)
    p = core.read(saved / 'preflight.json')
    assert p['dataset_name'] == DATASET, 'Wrong dataset preflight'
    assert p['adapter_sha256'] == core.digest(__file__), 'Dataset adapter changed'


def configure(dataset):
    global DATASET
    assert dataset in ('region', 'r0')
    DATASET = dataset
    core.schedule = schedule
    core.prepared_identity = prepared_identity
    core.verify_frozen = verify_frozen


def prepare(saved, batch, previous=None):
    assert not (saved / 'preflight.json').exists(), 'Fresh batch required'
    assert sys.version_info[:2] == (3, 11)
    versions = core.runtime_versions()
    assert all(versions[name].split('+')[0] == value for name, value in core.EXPECTED.items())
    import torch
    from benchmark.graph_value_skeleton import data, graph, protocol, prepared, training, artifacts, checks
    execution = training.configure_determinism(0)
    environment = artifacts.capture_environment(ROOT)
    assert torch.version.cuda is None
    assert protocol.EPOCHS == 200 and protocol.HIDDEN_DIM == 32
    assert tuple(protocol.DEVELOPMENT_MODEL_SEEDS) == (0, 1, 2)
    assert tuple(protocol.SHUFFLE_SEEDS) == (0, 1, 2)
    free = shutil.disk_usage(ROOT).free
    assert free > 8 * 1024**3, 'Need at least 8 GiB free'
    dataset = data.load_dataset(DATASET)
    original = graph.load_graph(DATASET, dataset.key_array)
    masks = data.build_masks(dataset, data.load_neighbor_coverage(dataset, Path(original.source_path)))
    graphs = {}
    for seed in range(3):
        shuffled, provenance = prepared.load(core.PREPARED / f'{DATASET}-shuffle{seed}-a',
            keys=dataset.key_array, source_edges=original.edges, data_name=DATASET,
            shuffle_seed=seed, require_current_generator=True)
        graphs[str(seed)] = shuffled.identity_payload()
        del shuffled, provenance
    axes = schedule(batch)
    assert len(axes) == 30 and len({a['run_id'] for a in axes}) == 30
    assert all(not (ROOT / 'research/runs' / a['run_id']).exists() for a in axes)
    source_command = (
        'import torch,json; from pathlib import Path; '
        'from benchmark.graph_value_skeleton import runner,artifacts; '
        'print(json.dumps({p: artifacts.sha256_file(Path.cwd()/p) '
        'for p in artifacts.runtime_source_paths(Path.cwd())},sort_keys=True))')
    source = json.loads(subprocess.check_output([sys.executable, '-B', '-c', source_command], cwd=ROOT, text=True))
    payload = {'task': 'P02-T002', 'batch': batch, 'dataset_name': DATASET, 'status': 'ok',
        'created_at': core.now(), 'root': str(ROOT), 'python': sys.executable, 'python_version': sys.version,
        'versions': versions, 'source': core.identities(), 'controller_sha256': core.digest(core.__file__),
        'adapter_sha256': core.digest(__file__), 'prepared_files': prepared_identity(), 'prepared_graphs': graphs,
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'nodes': dataset.node_count, 'disk_free_bytes': free,
        'inputs': {f'dataset/{kind}/{DATASET}.parquet': core.digest(ROOT / f'dataset/{kind}/{DATASET}.parquet')
                   for kind in ('demand', 'graph')},
        'reuse_identity': {'dataset': dataset.identity_payload(), 'masks': masks.hashes(),
            'graph': original.identity_payload(),
            'message_edges': {'self': '<empty: self branch propagates no message>',
                'graph': graph.edge_set_sha256(original.edges),
                **{seed: value['edges_sha256'] for seed, value in graphs.items()}},
            'source': source, 'protocol_sha256': core.digest(protocol.PROTOCOL_PATH),
            'runtime': checks._environment_identity(environment), 'execution': execution}}
    del original, dataset
    gc.collect()
    core.write(saved / 'preflight.json', payload)
    core.write(saved / 'manifest.json', {'batch': batch, 'dataset_name': DATASET,
        'formal_count': 30, 'schedule': axes, 'frozen_epochs': 200, 'concurrent_training_processes': 1,
        'checks': {'recompute': 30, 'repeat_compare': 15, 'three_graph_average': 6}})
    core.write(saved / 'recovery-plan.json', {'previous_batch': str(previous) if previous else None,
        'slots': core.recovery_plan(batch, previous)})
    core.write(saved / 'cost-confirmation.json', {'status': 'accepted', 'created_at': core.now(),
        'basis': 'User requested region and r0 after reviewing region 3-5h rough projection from completed r2.',
        'scope': f'{DATASET}: 30 fits x 200 epochs and 51 checks; sequential CPU, unchanged science',
        'estimated_seconds': None, 'estimate_kind': 'Unmeasured dataset; calibrate from actual epochs',
        'deadline_utc': None, 'epochs': 200, 'scientific_configuration_changed': False})
    print(json.dumps({'preflight': 'ok', 'dataset': DATASET, 'formal_count': 30}), flush=True)


class Controller(core.Controller):
    def fit(self, axis, directory):
        assert axis['dataset'] == DATASET
        assert not directory.exists(), 'Never overwrite an existing run'
        rid = axis['run_id']
        args = ['run', '--data-name', DATASET, '--method', axis['method'],
                '--model-seed', str(axis['model_seed']), '--purpose', 'formal', '--run-id', rid]
        if axis['shuffle_seed'] is not None:
            args += ['--shuffle-seed', str(axis['shuffle_seed']), '--shuffle-artifact',
                     core.PREPARED / f'{DATASET}-shuffle{axis["shuffle_seed"]}-a']
        if axis['action'] == 'resume':
            from benchmark.graph_value_skeleton import checkpoints
            checkpoint = ROOT / 'research/runs' / axis['source_run'] / 'checkpoints'
            _, manifest, _ = checkpoints.load(checkpoint)
            assert manifest['sha256'] == axis['checkpoint_sha256']
            args += ['--resume-from', checkpoint]
        monitor = self.invoke(args, rid, training=True)
        assert core.read(directory / 'status.json')['state'] == 'success'
        assert core.read(directory / 'measurements.json')['input']['epochs'] == 200
        assert len(core.read(directory / 'training-history.json')['rows']) == 200
        p = core.read(directory / 'training-progress.json')
        monitor['full_fit_seconds_estimate'] = p['last_epoch_seconds'] * 200 if p.get('estimate_samples') else None
        return monitor

    def finish(self):
        assert len(self.completed) == 30 and len(set(self.effective.values())) == 30
        for seed in range(3):
            for repeat in ('a', 'b'):
                members = [ROOT / 'research/runs' / self.effective[
                    f'{self.batch}-{DATASET}-shuffled{s}-s{seed}-{repeat}'] for s in range(3)]
                self.check(['summarize-shuffled', '--run-dirs', *members],
                           f'{self.batch}-{DATASET}-s{seed}-{repeat}-shuffled-summary')
        reports = list((self.saved / 'checks').glob('*.json'))
        assert len(reports) == 51 and all(core.read(p)['status'] == 'ok' for p in reports)
        verify_frozen(self.saved)
        completion = {'status': f'{DATASET}_ready_for_research_acceptance', 'batch': self.batch,
            'dataset': DATASET, 'completed_at': core.now(), 'formal_fits': 30, 'successful_checks': 51,
            'no_T003_or_graph_benefit_verdict': True}
        core.write(self.saved / 'completion.json', completion)
        writer = core.WRITER(self.saved.parent, self.saved.name, 'orchestration')
        writer.write_text('result.md', f'# {DATASET} execution result\n\n30 fits at 200 epochs and all 51 checks passed.\n\n'
            f'Total worker wall: {sum(t["seconds"] for t in self.timings):.3f}s.\n\n'
            'Full T002 remains subject to research acceptance; no graph-benefit/T003 decision.\n')
        self.progress(status=f'complete_{DATASET}', active=None)
        if self.push_on_success:
            self.publish()

    def publish(self):
        assert DATASET == 'r0', 'Publish only after both datasets finish'
        paths = [Path(__file__).relative_to(ROOT).as_posix(),
            'research/phases/P02/test_t002_remaining_batch.py', 'research/state.md', 'research/decisions.md',
            'research/phases/P02/plan.md', 'research/phases/P02/t002-execution.md', 'research/archives/index.md',
            f'research/reports/{GROUP}']
        for dataset, batch in BATCHES.items():
            saved = ROOT / 'research/reports' / batch
            completion = core.read(saved / 'completion.json')
            assert completion['dataset'] == dataset and completion['formal_fits'] == 30 and completion['successful_checks'] == 51
            reports = list((saved / 'checks').glob('*.json'))
            assert len(reports) == 51 and all(core.read(p)['status'] == 'ok' for p in reports)
            paths.append(saved.relative_to(ROOT).as_posix())
            effective = core.read(saved / 'effective-runs.json')
            assert len(effective) == 30 and len(set(effective.values())) == 30
            for rid in effective.values():
                for name in ('summary.md', 'provenance.json', 'command.json'):
                    p = ROOT / 'research/runs' / rid / name
                    assert p.is_file()
                    paths.append(p.relative_to(ROOT).as_posix())
        assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).strip()
        publication = {'status': 'publishing', 'started_at': core.now(), 'remote': 'origin', 'branch': 'FJWP2T002'}
        core.write(self.saved / 'publication.json', publication)
        try:
            subprocess.run(['git', 'add', '--', *paths], check=True)
            subprocess.run(['git', 'commit', '-m', 'Complete verified region and r0 T002 batches'], check=True)
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
            subprocess.run(['git', 'push', 'origin', 'HEAD:refs/heads/FJWP2T002'], check=True, timeout=180)
            publication.update(status='pushed', commit=commit, finished_at=core.now())
        except Exception as exc:
            publication.update(status='publication_failed', error=str(exc), finished_at=core.now())
            raise
        finally:
            core.write(self.saved / 'publication.json', publication)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'run', 'plan'))
    parser.add_argument('--data-name', choices=('region', 'r0'), required=True)
    parser.add_argument('--batch', required=True)
    parser.add_argument('--recover-from', type=Path)
    parser.add_argument('--push-on-success', action='store_true')
    args = parser.parse_args()
    configure(args.data_name)
    import torch  # Windows DLL ordering: torch before Arrow.
    from benchmark.nograph_baseline.artifacts import RunDirectory, validate_run_id
    core.WRITER = RunDirectory
    validate_run_id(args.batch)
    if args.mode == 'plan':
        print(json.dumps(core.recovery_plan(args.batch, args.recover_from), indent=2))
        return
    saved = ROOT / 'research/reports' / args.batch
    scratch = ROOT / 'scratch/graph-value-skeleton' / args.batch
    saved.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    temp = scratch / 'temp'
    temp.mkdir(exist_ok=True)
    os.environ['TMP'] = os.environ['TEMP'] = str(temp)
    controller = Controller(saved, scratch, args.batch, args.push_on_success)
    try:
        with core.Ownership(ROOT / 'scratch/r2-controller.lock'):
            core.assert_no_live_workers()
            if args.mode == 'prepare':
                prepare(saved, args.batch, args.recover_from)
            else:
                controller.run()
    except BaseException as exc:
        controller.progress(status='paused', error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
