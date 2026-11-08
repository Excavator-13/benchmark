"""Regression counterexamples from independent verification V-001 through V-009."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

import temporal_fixtures as fx
import test_temporal_selection_diagnostics as gate_tests
from benchmark.multivariate_time_series.temporal import (
    artifacts, checks, checkpoints, cli, diagnostics, engine, protocol,
    recovery, report, resources, runner,
)


class Clock:
    value = 0.0
    def __call__(self):
        return self.value


class SavedEvidenceRepairTests(unittest.TestCase):
    def setUp(self):
        self.case = gate_tests.DiagnosticsGateTests()
        self.case.setUp()
        self.root = self.case.root
        self.a, self.b = self.case._all_pass()
        self.selection = self.case._selection(self.a)
        self.ridge = self.case._compatible_ridge()
        self.block = self.root / 'block'
        fx.write_json(self.block / 'selection.json', self.selection)

    def tearDown(self):
        self.case.tearDown()

    def diagnose(self, a=None, b=None, selection=None, ridge=None):
        return diagnostics.build_diagnostics(
            selection=self.selection if selection is None else selection, block_id='block',
            a_runs=self.a if a is None else a, b_runs=self.b if b is None else b,
            ridge=self.ridge if ridge is None else ridge)

    def test_each_selection_and_trajectory_perturbation_prevents_readiness(self):
        self.assertTrue(self.diagnose()['learning_ready'])
        for change in ('lr', 'winner', 'b_history', 'b_nonfinite', 'b_controls', 'b_protocol',
                       'b_environment', 'cross_seed_data', 'cross_seed_config', 'condition'):
            with self.subTest(change=change):
                a, b, selection = copy.deepcopy(self.a), copy.deepcopy(self.b), copy.deepcopy(self.selection)
                if change == 'lr':
                    selection['winner']['learning_rate'] = .003
                elif change == 'winner':
                    selection['winner']['run_dir'] = str(self.root / 'unrelated')
                elif change == 'b_history':
                    b[0]['history'] = {'epochs': []}
                elif change == 'b_nonfinite':
                    b[0]['history']['epochs'][50]['validation_MSE'] = float('nan')
                elif change == 'b_controls':
                    b[0]['protocol_controls']['complete'] = False
                elif change == 'b_protocol':
                    b[0]['protocol_sha256'] = 'different'
                elif change == 'b_environment':
                    b[0]['environment']['packages']['torch'] = 'different'
                elif change == 'cross_seed_data':
                    a[1]['data_sha256'] = b[1]['data_sha256'] = 'different'
                elif change == 'cross_seed_config':
                    a[1]['config'] = b[1]['config'] = protocol.FitConfig(seed=1, node_chunk=7)
                else:
                    b[0]['condition_id'] = 'invented'
                selection['selection_sha256'] = protocol.content_sha256({k:v for k,v in selection.items() if k != 'selection_sha256'})
                result = self.diagnose(a=a, b=b, selection=selection)
                self.assertFalse(result['learning_ready'], result)
                self.assertNotEqual(result['status'], 'pass')

    def test_ridge_required_fields_cannot_be_missing_or_corrupt(self):
        cases = [('dataset',), ('data_sha256',), ('node_keys_sha256',),
                 ('split', 'validation_starts'), ('split', 'validation_target_months'),
                 ('preprocessing', 'definition'), ('preprocessing', 'ddof'),
                 ('preprocessing', 'training_months'), ('preprocessing', 'constant_node_std'),
                 ('selection', 'lambda'), ('selection', 'selected_on'),
                 ('selection', 'metric'), ('selection', 'tie_break')]
        for path in cases:
            for corrupt in (False, True):
                with self.subTest(path=path, corrupt=corrupt):
                    ridge = copy.deepcopy(self.ridge)
                    parent = ridge
                    for key in path[:-1]:
                        parent = parent[key]
                    if corrupt:
                        parent[path[-1]] = 'wrong'
                    else:
                        parent.pop(path[-1])
                    self.assertFalse(self.diagnose(ridge=ridge)['learning_ready'])
        self.assertTrue(self.diagnose()['learning_ready'])

    def test_diagnose_writes_one_report_and_keeps_all_inputs_identical(self):
        ridge = fx.write_json(self.root / 'ridge.json', self.ridge)
        request = {'block_dir': str(self.block), 'purpose': 'development',
                   'a_runs': {s: r['run_dir'] for s,r in self.a.items()},
                   'b_runs': {s: r['run_dir'] for s,r in self.b.items()}, 'ridge_path': str(ridge)}
        before = fx.tree_digest(self.root)
        destination = self.root / 'checks' / 'diagnose.json'
        result = diagnostics.run_diagnose({**request, 'report_path': str(destination)})
        self.assertEqual(result['status'], 'pass')
        after = fx.tree_digest(self.root)
        self.assertEqual({k:v for k,v in after.items() if k != 'checks/diagnose.json'}, before)
        aliases = self.root / 'alias'
        aliases.symlink_to(Path(self.a[0]['run_dir']), target_is_directory=True)
        for target in (destination, self.block/'out.json', Path(self.a[0]['run_dir'])/'out.json',
                       aliases/'out.json', ridge):
            with self.subTest(target=target):
                snapshot = fx.tree_digest(self.root)
                with self.assertRaises(checks.CheckError):
                    diagnostics.run_diagnose({**request, 'report_path': str(target)})
                self.assertEqual(fx.tree_digest(self.root), snapshot)
        missing = diagnostics.run_diagnose({'block_dir': str(self.root/'missing'),
                                            'report_path': str(self.root/'failure.json')})
        self.assertEqual(missing['status'], 'failed')
        self.assertTrue((self.root/'failure.json').is_file())
        incomplete = diagnostics.run_diagnose({**request, 'b_runs': {},
                                              'report_path': str(self.root/'incomplete.json')})
        self.assertEqual(incomplete['status'], 'incomplete')
        self.assertEqual(fx.tree_digest(self.block), {k.removeprefix('block/'):v for k,v in before.items() if k.startswith('block/')})

    def test_cli_diagnose_needs_no_model_or_data_dependencies(self):
        script = '''
import builtins, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'torch','pandas','pyarrow','psutil'}:
        raise ImportError('blocked dependency: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from benchmark.multivariate_time_series.temporal.cli import main
sys.exit(main(sys.argv[1:]))
'''
        ridge = fx.write_json(self.root/'ridge.json', self.ridge)
        args = [sys.executable, '-c', script, 'diagnose', '--block', str(self.block),
                '--ridge', str(ridge), '--report', str(self.root/'standalone.json')]
        for role, runs in (('--a-run', self.a), ('--b-run', self.b)):
            for seed, run in runs.items():
                args += [role, f'{seed}={run["run_dir"]}']
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_formal_eligibility_accepts_each_frozen_seed_and_repeat(self):
        diag = self.diagnose()
        states = {s:'completed' for s in protocol.SEEDS}
        for role, runs in (('a', self.a), ('b', self.b)):
            for seed, run in runs.items():
                with self.subTest(role=role, seed=seed):
                    kwargs = dict(purpose='formal', config=run['config'], selection=self.selection,
                                  diagnostics=diag, run_dir=Path(run['run_dir']), a_states=states,
                                  b_states=states, winner_run_dir=Path(self.a[0]['run_dir']),
                                  run_evidence_sha256=run['evidence_sha256'])
                    self.assertEqual(report.formal_report_blockers(**kwargs), [])
                    self.assertTrue(report.formal_report_blockers(**{**kwargs, 'run_dir': self.root/'unrelated'}))
                    self.assertTrue(report.formal_report_blockers(**{**kwargs, 'run_evidence_sha256': 'changed'}))


class RuntimeRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = fx.in_memory('r0', 4, seed=3)

    def tearDown(self):
        self.tmp.cleanup()

    def fit(self, run_id, **kwargs):
        return fx.fit_run(self.root/'runs', run_id=run_id, data=self.data,
                          sampler=lambda: {'rss_bytes':0}, **kwargs)

    def parent(self, run_id='parent', clock=None):
        def interrupt(t, epoch, window):
            if epoch == 2 and window == 2:
                if clock:
                    clock.value = 3500.
                raise engine.PauseRequest('fixture_interrupt')
        return self.fit(run_id, epochs=3, after_update=interrupt, clock=clock)

    def test_resource_stop_during_epoch_preserves_previous_recovery(self):
        snapshots = []
        def work(t, epoch, window):
            if epoch == 2 and window == 1:
                path = self.root/'runs'/'slow'/'recovery'/'last.pt'
                snapshots.append(path.read_bytes())
                with patch.object(resources, 'sample_process_tree_rss', return_value={'rss_bytes':protocol.MEMORY_STOP_BYTES+1}):
                    # Inject the actual watchdog's independently sampled signal.
                    watchdog[0].sample_once()
        watchdog = []
        original = resources.Watchdog
        def capture(**kw):
            kw['sampler'] = lambda: {'rss_bytes': protocol.MEMORY_STOP_BYTES+1 if snapshots else 0}
            obj = original(**kw)
            watchdog.append(obj)
            return obj
        with patch.object(resources, 'Watchdog', side_effect=capture):
            result = self.fit('slow', epochs=3, after_update=work)
        self.assertEqual(result['status'], 'paused')
        self.assertEqual(result['completed_epoch'], 1)
        path = Path(result['run_dir'])/'recovery'/'last.pt'
        self.assertEqual(path.read_bytes(), snapshots[0])
        gradients = fx.read_json(Path(result['run_dir'])/'gradients.json')
        self.assertEqual(gradients['total_updates'], 21)

    def test_recovery_rejects_environment_source_and_ledger_replacement(self):
        result = self.parent()
        parent = Path(result['run_dir'])
        before = fx.tree_digest(parent)
        ledger_path = self.root/'runs'/'ledger.json'
        recovery.load_parent(parent)
        for replacement in (self.root/'fresh.json', self.root/'different.json'):
            with self.assertRaises(recovery.RecoveryError):
                recovery.load_parent(parent, ledger_path=replacement)
        saved = fx.read_json(parent/'provenance.json')
        for field in ('source','environment'):
            changed = copy.deepcopy(saved)
            changed[field] = {'different':True}
            fx.write_json(parent/'provenance.json', changed)
            with self.assertRaises(recovery.RecoveryError):
                recovery.load_parent(parent)
        fx.write_json(parent/'provenance.json', saved)
        self.assertEqual(fx.tree_digest(parent), before)
        ledger_saved = ledger_path.read_bytes()
        ledger_path.unlink()
        with self.assertRaises(recovery.RecoveryError):
            recovery.load_parent(parent)
        ledger_path.write_bytes(ledger_saved)
        with self.assertRaises(recovery.RecoveryError):
            recovery.load_parent(parent, batch_id='different')
        changed = fx.read_json(ledger_path)
        changed['ledger_id'] = 'replacement'
        fx.write_json(ledger_path, changed)
        with self.assertRaises(recovery.RecoveryError):
            recovery.load_parent(parent)

    def test_parent_and_child_share_single_fit_time_limit(self):
        clock = Clock()
        parent = self.parent(clock=clock)
        child_clock = Clock()
        def work(t, epoch, window):
            if epoch == 2 and window == 0:
                child_clock.value = 200.
        child = self.fit('child', operation='resume', parent_dir=Path(parent['run_dir']),
                         clock=child_clock, after_update=work)
        self.assertEqual(child['status'], 'paused')
        self.assertEqual(child['paused']['reason'], 'fit_timeout')
        self.assertGreaterEqual(resources.Ledger(self.root/'runs'/'ledger.json', batch_id='p02-t006').active_seconds(), 3700.)

    def test_complete_epoch_cost_includes_diagnostics_setup_and_checkpoint(self):
        clock = Clock()
        def setup(run, **kw):
            clock.value += 3.
            return original_preamble(run, **kw)
        def fixed(t):
            clock.value += 1.
            return original_fixed(t)
        def publish(path, payload):
            clock.value += 2.
            return checkpoints.publish_last(path, payload)
        original_preamble, original_fixed = runner._write_preamble, engine.Trajectory.fixed_parameter_scores
        with patch.object(runner, '_write_preamble', side_effect=setup), patch.object(engine.Trajectory, 'fixed_parameter_scores', fixed):
            result = self.fit('timed', epochs=11, clock=clock, publish=publish)
        cost = fx.read_json(Path(result['run_dir'])/'cost.json')
        self.assertEqual(cost['setup_seconds'], 4.)
        self.assertEqual(cost['sample_measured_seconds'], 25.)  # setup 4 + ten checkpoints 20 + epoch-10 fixed score 1
        self.assertEqual(cost['steady_state_median_seconds'], 2.)
        self.assertGreater(cost['estimate_seconds'], 0.)
        ledger = resources.Ledger(self.root/'runs'/'ledger.json', batch_id='p02-t006')
        self.assertEqual(ledger.active_seconds(), clock.value)

    def test_controller_enforces_signal_and_bills_a_terminated_worker(self):
        clock = Clock()
        class Worker:
            terminated = False
            def poll(self): return -15 if self.terminated else None
            def terminate(self): self.terminated = True
            def wait(self, **kw): return -15
        worker = Worker()
        dog = resources.Watchdog(sampler=lambda: {'rss_bytes':0}, clock=clock)
        ledger = resources.Ledger(self.root/'controller-ledger.json', batch_id='batch')
        def advance(seconds):
            clock.value += 7.
            dog.monitor_failure = {'reason':'injected monitor failure'}
        code, reason = cli.supervise_worker(worker, watchdog=dog, ledger=ledger,
                                            request={'execution_id':'fixture','run_id':'worker','monitor_interval':1},
                                            started=0., clock=clock, sleeper=advance)
        self.assertTrue(worker.terminated)
        self.assertEqual(code, -15)
        self.assertIsNotNone(reason)
        self.assertEqual(resources.Ledger(ledger.path, batch_id='batch').active_seconds(), 7.)

    def test_context_chunks_never_mix_nodes_and_preserve_global_update(self):
        keys = [(0,0),(0,1),(1,0),(1,1),(1,2)]
        values = fx.synthetic_signal(5, seed=7)
        data = fx.temporal_data.from_arrays('region', keys, values)
        calls = []
        class Spy(torch.nn.Module):
            def forward(self, x):
                calls.append(x[:,0,0].tolist())
                return x[:,0,:].expand(-1,3)
        contexts = np.array([0.,0.,1.,1.,1.])
        engine.squared_error_sum(Spy(), np.repeat(contexts[:,None],6,axis=1), np.zeros((5,3)), 1.,3,15,contexts=contexts)
        self.assertEqual(calls, [[0.,0.],[1.,1.,1.]])
        arrays = data.fit_arrays()
        results = [engine.run_trajectory(arrays, protocol.FitConfig(epochs=1, hidden_size=4, node_chunk=chunk)) for chunk in (2,3,20)]
        for result in results:
            self.assertEqual(result.updates,19)
            for name,tensor in result.best_model_state.items():
                torch.testing.assert_close(tensor, results[0].best_model_state[name], rtol=1e-6, atol=1e-7)

    def test_recompute_rejects_each_corrupt_sample_count(self):
        fit = self.fit('counts', epochs=1)
        block = self.root/'block'
        fx.write_json(block/'selection.json', fx.selection_document(self.root, winner_run_dir=Path(fit['run_dir'])))
        result = runner.run_report({'purpose':'development', 'block_dir':str(block), 'run_dir':fit['run_dir'],
                                    'run_id':'test-report','output_root':str(self.root)}, data=self.data)
        directory = Path(result['run_dir'])
        saved = fx.read_json(directory/'report.json')
        for field in saved['metrics']['sample_counts']:
            corrupt = copy.deepcopy(saved)
            corrupt['metrics']['sample_counts'][field] = 999999
            fx.write_json(directory/'report.json', corrupt)
            before = fx.tree_digest(directory)
            check = checks.run_recompute(run_dir=directory, report_path=self.root/f'{field}.json', argv=[])
            self.assertNotEqual(check['status'], 'pass', field)
            self.assertEqual(fx.tree_digest(directory), before)
        fx.write_json(directory/'report.json', saved)
        self.assertEqual(checks.run_recompute(run_dir=directory, report_path=self.root/'valid.json', argv=[])['status'], 'pass')

    def test_failed_formal_gate_never_constructs_test_arrays(self):
        directory = fx.synthetic_completed_run(self.root, 'eligible-config')
        block = self.root/'block'
        fx.write_json(block/'selection.json', fx.selection_document(self.root, winner_run_dir=directory))
        with patch.object(self.data, 'report_arrays', side_effect=AssertionError('test access')) as sentinel:
            with self.assertRaises(report.ReportError):
                runner.run_report({'purpose':'formal','block_dir':str(block),'run_dir':str(directory),
                                   'run_id':'refused','output_root':str(self.root)}, data=self.data)
        sentinel.assert_not_called()
        self.assertFalse((self.root/'refused').exists())

    def test_setup_and_sample_deadlines_include_nontraining_work(self):
        clock = Clock()
        original = runner._write_preamble
        def slow_setup(*args, **kwargs):
            clock.value += protocol.COST_SAMPLE_SECONDS + 1
            return original(*args, **kwargs)
        with patch.object(runner, '_write_preamble', side_effect=slow_setup):
            result = self.fit('slow-setup', epochs=11, clock=clock)
        self.assertEqual(result['status'], 'paused')
        self.assertEqual(result['paused']['reason'], 'sample_timeout')
        self.assertEqual(result['completed_epoch'], 0)
        ledger = resources.Ledger(self.root/'runs'/'ledger.json', batch_id='p02-t006')
        self.assertEqual(ledger.active_seconds(), clock.value)

    def test_final_writes_are_billed_and_can_exhaust_fit_limit(self):
        clock = Clock()
        original = artifacts.write_array_manifest
        def slow_final(*args, **kwargs):
            clock.value += protocol.FIT_SECONDS + 1
            return original(*args, **kwargs)
        with patch.object(artifacts, 'write_array_manifest', side_effect=slow_final):
            result = self.fit('slow-final', epochs=1, clock=clock)
        self.assertEqual(result['status'], 'paused')
        self.assertEqual(result['paused']['reason'], 'fit_timeout')
        ledger = resources.Ledger(self.root/'runs'/'ledger.json', batch_id='p02-t006')
        self.assertEqual(ledger.active_seconds(), clock.value)

    def test_saved_check_active_time_reaches_linked_batch_ledger(self):
        result = self.fit('bill-check', epochs=1)
        directory = Path(result['run_dir'])
        ledger_path = self.root/'runs'/'ledger.json'
        before = resources.Ledger(ledger_path, batch_id='p02-t006').active_seconds()
        clock = Clock()
        original = checks.finish
        def delayed(*args, **kwargs):
            clock.value += 4.
            return original(*args, **kwargs)
        snapshot = fx.tree_digest(directory)
        with patch.object(resources.time, 'monotonic', clock), patch.object(checks, 'finish', side_effect=delayed):
            checked = checks.run_recompute(run_dir=directory, report_path=self.root/'checked.json', argv=[])
        self.assertEqual(checked['status'], 'pass')
        self.assertEqual(fx.tree_digest(directory), snapshot)
        self.assertEqual(resources.Ledger(ledger_path, batch_id='p02-t006').active_seconds()-before, 4.)

    def test_recovery_checks_current_source_environment_and_spent_time_floor(self):
        result = self.parent()
        parent = Path(result['run_dir'])
        before = fx.tree_digest(parent)
        current_environment = artifacts.capture_environment()
        current_environment['packages']['torch'] = 'different-current-version'
        with patch.object(artifacts, 'capture_environment', return_value=current_environment):
            with self.assertRaises(recovery.RecoveryError):
                recovery.load_parent(parent)
        with patch.object(protocol, 'sha256_file', return_value='different-current-source'):
            with self.assertRaises(recovery.RecoveryError):
                recovery.load_parent(parent)
        ledger_path = self.root/'runs'/'ledger.json'
        payload = fx.read_json(ledger_path)
        saved = copy.deepcopy(payload)
        for entry in payload['entries']:
            entry['seconds'] = 0.
        fx.write_json(ledger_path, payload)
        with self.assertRaises(recovery.RecoveryError):
            recovery.load_parent(parent)
        fx.write_json(ledger_path, saved)
        ledger = resources.Ledger(ledger_path, batch_id='p02-t006')
        ledger.record(execution_id='spent-other-work', run_id='earlier', seconds=protocol.BATCH_SECONDS)
        with self.assertRaises(recovery.RecoveryError):
            recovery.load_parent(parent)
        with self.assertRaises(recovery.RecoveryError):
            recovery.load_parent(parent, ledger_path=self.root/'fresh-budget.json')
        self.assertEqual(fx.tree_digest(parent), before)
