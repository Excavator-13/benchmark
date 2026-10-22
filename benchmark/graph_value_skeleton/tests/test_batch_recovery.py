"""Bounded orchestration tests: no formal data or training required."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import torch
from benchmark.graph_value_skeleton import checkpoints, protocol

spec = importlib.util.spec_from_file_location('r2batch', protocol.REPO_ROOT / 'research/phases/P02/t002_r2_batch.py')
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class BatchRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='gvs-batch-recovery-'))
        from benchmark.nograph_baseline.artifacts import RunDirectory
        self.root_patch = mock.patch.object(batch, 'ROOT', self.root)
        self.root_patch.start()
        batch.WRITER = RunDirectory
        self.addCleanup(self.root_patch.stop)

    def test_matrix_plan_and_checkpoint_integrity(self):
        old = self.root / 'research/reports/old'
        batch.write(old / 'manifest.json', {'schedule': batch.schedule('old')})
        axes = batch.schedule('old')
        success = self.root / 'research/runs' / axes[0]['run_id']
        batch.write(success / 'status.json', {'state': 'success'})
        interrupted = self.root / 'research/runs' / axes[1]['run_id']
        checkpoints.publish(interrupted / 'checkpoints', {'epoch': 4}, {}, ['parent'])
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        plan = batch.recovery_plan('new', old)
        self.assertEqual(len(plan), 30)
        self.assertEqual([p['action'] for p in plan[:3]], ['reuse', 'resume', 'fresh'])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        with self.assertRaises(AssertionError):
            batch.recovery_plan('old', old)

    def test_ownership_duplicate_and_stale_release(self):
        path = self.root / 'lock'
        with batch.Ownership(path):
            with self.assertRaises(RuntimeError):
                with batch.Ownership(path):
                    pass
        with batch.Ownership(path):
            self.assertTrue(path.exists())

    def test_completed_reuse_and_failure_stops_scheduling(self):
        saved = self.root / 'research/reports/new'
        scratch = self.root / 'scratch/new'
        axes = batch.schedule('new')
        plan = [{**a, 'action': 'reuse', 'effective_run_id': a['run_id'].replace('new-', 'old-')} for a in axes]
        batch.write(saved / 'manifest.json', {'schedule': axes})
        batch.write(saved / 'cost-confirmation.json', {'status': 'accepted'})
        batch.write(saved / 'recovery-plan.json', {'slots': plan})
        batch.write(saved / 'preflight.json', {'reuse_identity': {'execution': {}}})
        controller = batch.Controller(saved, scratch, 'new')
        with mock.patch.object(batch, 'qualify_completed') as qualify, mock.patch.object(controller, 'check') as check, mock.patch.object(controller, 'fit') as fit, mock.patch.object(controller, 'finish') as finish:
            controller.run()
            self.assertEqual(check.call_count, 45)
            self.assertEqual(qualify.call_count, 30)
            fit.assert_not_called()
            finish.assert_called_once()
        (saved / 'controller.json').unlink()
        controller = batch.Controller(saved, scratch, 'new')
        with mock.patch.object(batch, 'qualify_completed'), mock.patch.object(controller, 'check', side_effect=RuntimeError('failed recompute')) as check:
            with self.assertRaisesRegex(RuntimeError, 'failed recompute'):
                controller.run()
            self.assertEqual(check.call_count, 1)
        self.assertFalse((saved / 'completion.json').exists())

    def test_completion_gate_rejects_missing_checks(self):
        controller = batch.Controller(self.root / 'saved', self.root / 'scratch', 'new')
        controller.effective = {a['run_id']: a['run_id'] for a in batch.schedule('new')}
        with mock.patch.object(controller, 'check') as check:
            with self.assertRaises(AssertionError):
                controller.finish()
            self.assertEqual(check.call_count, 6)
        self.assertFalse((self.root / 'saved/completion.json').exists())

    def test_forecast_unavailable_until_all_methods_observed(self):
        controller = batch.Controller(self.root / 'saved', self.root / 'scratch', 'new')
        controller.progress()
        self.assertIsNone(batch.read(self.root / 'saved/progress.json')['remaining_training_seconds_estimate'])
        controller.active = {'method': 'shuffled', 'epoch_progress': {'estimate_samples': 1, 'last_epoch_seconds': 20}}
        controller.progress()
        self.assertEqual(batch.read(self.root / 'saved/progress.json')['measured_fit_seconds_by_method'], {'shuffled': 4000})

    def test_runtime_and_stall_watchdogs_stop_owned_process(self):
        for label, fit_bound, stall_bound in (('runtime', 5, 1000), ('stall', 1000, 5)):
            controller = batch.Controller(self.root / label, self.root / f'{label}-scratch', 'new',
                                          fit_timeout=fit_bound, stall_timeout=stall_bound)
            child = mock.Mock(pid=1234)
            child.poll.return_value = None
            usage = mock.Mock(free=10*1024**3)
            cleanup = mock.Mock(returncode=0, stdout='', stderr='')
            with mock.patch.object(batch, 'verify_frozen'), mock.patch.object(batch.shutil, 'disk_usage', return_value=usage), \
                 mock.patch.object(batch.subprocess, 'Popen', return_value=child), \
                 mock.patch.object(batch.subprocess, 'run', return_value=cleanup) as stop, \
                 mock.patch.object(batch.time, 'monotonic', side_effect=[0, 20, 20, 20]):
                with self.assertRaisesRegex(RuntimeError, 'stalled progress'):
                    controller.invoke(['run'], 'owned', training=True)
                self.assertEqual(stop.call_args.args[0], ['taskkill', '/PID', '1234', '/T', '/F'])
            monitor = batch.read(self.root / label / 'monitor/owned.json')
            self.assertFalse(monitor['worker_may_be_running'])

    def test_live_worker_inspection_fails_closed(self):
        if os.name != 'nt':
            self.skipTest('Windows inspection path')
        with mock.patch.object(batch.subprocess, 'check_output', return_value=json.dumps(
                [{'ProcessId': 123, 'CommandLine': 'python -m benchmark.graph_value_skeleton._worker'}])):
            with self.assertRaisesRegex(AssertionError, 'Live worker'):
                batch.assert_no_live_workers()
        with mock.patch.object(batch.subprocess, 'check_output', return_value=json.dumps(
                [{'ProcessId': 123, 'CommandLine': None}])):
            with self.assertRaisesRegex(AssertionError, 'Cannot inspect'):
                batch.assert_no_live_workers()
