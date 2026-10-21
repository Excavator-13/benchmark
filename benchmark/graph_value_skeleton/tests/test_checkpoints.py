"""Failure boundaries, strict state validation and fresh-process equivalence."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import torch
import numpy as np
from benchmark.graph_value_skeleton import checkpoints as cp, model, training, protocol, checks
from benchmark.graph_value_skeleton.tests import fixtures
from benchmark.graph_value_skeleton.tests.test_training import _prepare


class CodecTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix='gvs-cp-codec-'))
        fixture = fixtures.build_fixture(cls.root, 'r0')
        dataset, graph, chunks = _prepare(fixture)
        training.configure_determinism(0)
        cls.model = model.build_model(0)
        class Stop(Exception):
            pass
        def capture(state, seconds):
            cls.state = cp.decode(cp.encode(state))
            raise Stop()
        with mock.patch.object(training, 'protocol', protocol):
            try:
                training.train(cls.model, train_inputs=dataset.input_windows(protocol.TRAIN_STARTS),
                    train_targets=dataset.target_windows(protocol.TRAIN_STARTS),
                    validation_inputs=dataset.input_windows(protocol.VALIDATION_STARTS),
                    validation_targets=dataset.target_windows(protocol.VALIDATION_STARTS), chunks=chunks,
                    validation_aggregation=model.GraphAggregation.from_edges(graph.edges, dataset.node_count),
                    node_count=dataset.node_count, checkpoint_callback=capture)
            except Stop:
                pass

    def optimizer(self):
        return torch.optim.Adam(self.model.parameters(), **protocol.ADAM)

    def test_roundtrip_and_rejection(self):
        cp.validate_state(self.state, self.model, self.optimizer())
        for mutate in (
            lambda s: s.update(extra=True),
            lambda s: s['model'].update(bogus=torch.zeros(1)),
            lambda s: s['model'].__setitem__(next(iter(s['model'])), torch.zeros(1)),
            lambda s: s['model'].__setitem__(next(iter(s['model'])), next(iter(s['model'].values())).double()),
            lambda s: s.update(best_epoch=0),
            lambda s: s.update(history=[]),
            lambda s: s['optimizer']['state'][0].update(step=torch.tensor(2.)),
            lambda s: s['rng'].update(torch=torch.ones(2)),
            lambda s: s.update(training_seconds=float('nan')),
        ):
            state = copy.deepcopy(self.state)
            mutate(state)
            with self.assertRaises(cp.CheckpointError):
                cp.validate_state(state, self.model, self.optimizer())
        with self.assertRaises(cp.CheckpointError):
            cp.encode({'bad': np.array([object()])})
        with self.assertRaises(cp.CheckpointError):
            cp.encode({'bad': np.array([np.nan])})
        with self.assertRaises(cp.CheckpointError):
            cp.decode(b'broken')

    def test_publication_failure_boundaries_and_retention(self):
        for failure_at in (1, 2):
            directory = self.root / f'atomic-{failure_at}'
            first = cp.publish(directory, self.state, {'id': 1}, ['first'])
            original = cp.atomic_bytes
            calls = 0
            def fail(path, raw):
                nonlocal calls
                calls += 1
                if calls == failure_at:
                    raise OSError('injected publication interruption')
                original(path, raw)
            with mock.patch.object(cp, 'atomic_bytes', side_effect=fail):
                with self.assertRaises(OSError):
                    cp.publish(directory, self.state, {'id': 1}, ['first'])
            self.assertEqual(cp.load(directory)[1], first)
            cp.publish(directory, self.state, {'id': 1}, ['first'])
            cp.publish(directory, self.state, {'id': 1}, ['first'])
            self.assertEqual(len(list(directory.glob('epoch-*.npz'))), 2)

    def test_integrity_and_identity(self):
        directory = self.root / 'integrity'
        manifest = cp.publish(directory, self.state, {'id': 1}, ['first'])
        with self.assertRaisesRegex(cp.CheckpointError, 'identity mismatch'):
            cp.load(directory, {'id': 2})
        (directory / manifest['file']).write_bytes(b'corrupt')
        with self.assertRaisesRegex(cp.CheckpointError, 'integrity mismatch'):
            cp.load(directory)

    def test_restore_best_before_cut_and_exact_ties(self):
        fixture = fixtures.build_fixture(self.root / 'ties', 'r0')
        dataset, graph, chunks = _prepare(fixture)
        kwargs = dict(train_inputs=np.zeros_like(dataset.input_windows(protocol.TRAIN_STARTS)),
            train_targets=np.zeros_like(dataset.target_windows(protocol.TRAIN_STARTS)),
            validation_inputs=np.zeros_like(dataset.input_windows(protocol.VALIDATION_STARTS)),
            validation_targets=np.zeros_like(dataset.target_windows(protocol.VALIDATION_STARTS)),
            chunks=chunks, validation_aggregation=None, node_count=dataset.node_count)
        zero = model.build_model(0)
        with torch.no_grad():
            for p in zero.parameters():
                p.zero_()
        captured = None
        class Stop(Exception):
            pass
        def cut(state, seconds):
            nonlocal captured
            if state['epoch'] == 37:
                captured = cp.decode(cp.encode(state))
                raise Stop()
        with self.assertRaises(Stop):
            training.train(zero, **kwargs, checkpoint_callback=cut)
        self.assertEqual(captured['best_epoch'], 1)
        updates = 0
        original = torch.optim.Adam.step
        def step(opt, *args, **kw):
            nonlocal updates
            updates += 1
            return original(opt, *args, **kw)
        with mock.patch.object(torch.optim.Adam, 'step', step):
            result = training.train(model.build_model(1), **kwargs, resume_state=captured)
        self.assertEqual(updates, 163)
        self.assertEqual(result.selected_epoch, 1)
        self.assertEqual(result.selected_validation_mse, 0.)
        self.assertEqual(len(result.history), 200)


def assert_nested_equal(test, left, right):
    if isinstance(left, (torch.Tensor, np.ndarray)):
        np.testing.assert_array_equal(np.asarray(left), np.asarray(right))
    elif isinstance(left, dict):
        test.assertEqual(set(left), set(right))
        for key in left:
            assert_nested_equal(test, left[key], right[key])
    elif isinstance(left, (tuple, list)):
        test.assertEqual(len(left), len(right))
        for a, b in zip(left, right):
            assert_nested_equal(test, a, b)
    else:
        test.assertEqual(left, right)


class ProcessRecoveryTest(unittest.TestCase):
    def test_full_200_epoch_multiple_interruptions(self):
        root = Path(tempfile.mkdtemp(prefix='gvs-cp-process-'))
        evidence = []
        for method in ('self', 'graph', 'shuffled'):
            directory = root / method
            directory.mkdir()
            def execute(rid, cut=None, resume=None, expected=0, public=False):
                args = [sys.executable, '-B', '-m',
                    'benchmark.graph_value_skeleton.tests.checkpoint_worker',
                    str(directory), method, rid]
                if cut:
                    args += ['--cut', str(cut)]
                if resume:
                    args += ['--resume', str(directory / 'runs' / resume / 'checkpoints')]
                if public:
                    args += ['--public']
                result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', timeout=240)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                return directory / 'runs' / rid
            continuous = execute('continuous')
            first = execute('cut37', cut=37, expected=73)
            before = {p.relative_to(first).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in first.rglob('*') if p.is_file()}
            second = execute('cut113', cut=113, resume='cut37', expected=73)
            at200 = execute('cut200', cut=200, resume='cut113', expected=73)
            resumed = execute('resumed', resume='cut200', public=True)
            after = {p.relative_to(first).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in first.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            a = cp.load(continuous / 'checkpoints')[0]['state']
            b = cp.decode((resumed / 'recovery/input.npz').read_bytes())['state']
            for key in ('epoch', 'model', 'optimizer', 'history', 'best_epoch', 'best_mse', 'best_state', 'rng'):
                assert_nested_equal(self, a[key], b[key])
            for split in ('validation', 'test'):
                np.testing.assert_array_equal(np.load(continuous / f'predictions/{method}/{split}.npy'),
                                              np.load(resumed / f'predictions/{method}/{split}.npy'))
            for rid, path in (('continuous', continuous), ('resumed', resumed)):
                report = checks.command_recompute(run_dir=path, repo_root=protocol.REPO_ROOT,
                    command=['test'], report_path=root / f'{method}-{rid}-recompute.json')
                self.assertEqual(report['status'], 'ok', report)
            # An independent run agrees, while sibling continuation must be rejected.
            report = checks.command_compare(run_a=continuous, run_b=resumed, repo_root=protocol.REPO_ROOT,
                command=['test'], report_path=root / f'{method}-compare.json')
            self.assertEqual(report['status'], 'ok', report)
            # Historical successful runs remain readable without recovery metadata.
            legacy = directory / 'legacy'
            import shutil
            shutil.copytree(continuous, legacy)
            (legacy / 'recovery.json').unlink()
            provenance = json.loads((legacy / 'provenance.json').read_text())
            provenance.pop('recovery', None)
            (legacy / 'provenance.json').write_text(json.dumps(provenance))
            report = checks.command_recompute(run_dir=legacy, repo_root=protocol.REPO_ROOT,
                command=['test'], report_path=root / f'{method}-legacy.json')
            self.assertEqual(report['status'], 'ok', report)
            # Changed identities fail without publishing a new epoch.
            if method == 'self':
                from dataclasses import replace
                from benchmark.graph_value_skeleton import runner
                fixture = fixtures.build_fixture(directory / 'fixture', 'r0')
                config = fixtures.make_config(directory, fixture, method=method, model_seed=1, run_id='mismatch')
                config = replace(config, resume_from=str(first / 'checkpoints'))
                with mock.patch.object(torch.optim.Adam, 'step', side_effect=AssertionError('must not update')):
                    with self.assertRaisesRegex(cp.CheckpointError, 'identity mismatch'):
                        runner.execute_run(config)
                self.assertFalse((directory / 'runs/mismatch/checkpoints/latest.json').exists())
            sibling = execute('sibling', resume='cut200')
            report = checks.command_compare(run_a=resumed, run_b=sibling, repo_root=protocol.REPO_ROOT,
                command=['test'], report_path=root / f'{method}-ancestry.json')
            self.assertNotEqual(report['status'], 'ok')
            evidence.append({'method': method, 'epochs': 200, 'cuts': [37, 113, 200],
                             'exact_numeric_agreement': True, 'recompute': 'ok', 'independent_compare': 'ok'})
        (root / 'evidence.json').write_text(json.dumps(evidence, indent=2))
        print(f'CHECKPOINT_EVIDENCE={root}', flush=True)
