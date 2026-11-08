"""Synthetic regressions for independent findings V-010 and V-011."""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import temporal_fixtures as fx
from benchmark.multivariate_time_series.temporal import (
    artifacts, checks, cli, diagnostics, engine, protocol, resources, runner, selection,
)


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class RssControlTests(unittest.TestCase):
    def command(self, operation, root, limit=None):
        command = [operation, '--data-name', 'r0', '--run-id', 'pure-control',
                   '--purpose', 'formal', '--output-root', str(root)]
        if operation == 'resume':
            command += ['--parent', str(root/'unread-parent')]
        if limit is not None:
            command += ['--memory-limit-bytes', str(limit)]
        return command

    def test_formal_public_fit_and_resume_accept_default_and_conservative_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'uncreated'
            for operation in ('fit', 'resume'):
                for limit in (None, protocol.MEMORY_STOP_BYTES, protocol.MEMORY_STOP_BYTES-1):
                    with self.subTest(operation=operation, limit=limit):
                        args = cli.build_parser().parse_args(self.command(operation, root, limit))
                        accepted = cli._preflight_request(args, operation=operation)['resource_controls']
                        self.assertTrue(accepted['complete'])
                        dog = resources.Watchdog(
                            sampler=lambda: {'rss_bytes': protocol.MEMORY_STOP_BYTES+1},
                            limit_bytes=accepted['rss_stop_bytes'])
                        self.assertEqual(dog.sample_once()['status'], 'breach')
            self.assertFalse(root.exists())

    def test_invalid_public_controls_reject_before_worker_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'uncreated'
            for operation in ('fit', 'resume'):
                for limit in (protocol.MEMORY_STOP_BYTES+1, 0, -1, 'invalid'):
                    with self.subTest(operation=operation, limit=limit), \
                         patch.object(cli.subprocess, 'Popen') as spawn, \
                         patch.object(runner, 'run_preflight') as preflight, \
                         contextlib.redirect_stdout(io.StringIO()), \
                         contextlib.redirect_stderr(io.StringIO()):
                        if limit == 'invalid':
                            with self.assertRaises(SystemExit) as rejected:
                                cli.main(self.command(operation, root, limit))
                            self.assertEqual(rejected.exception.code, cli.EXIT_USAGE)
                        else:
                            self.assertNotEqual(cli.main(self.command(operation, root, limit)), cli.EXIT_OK)
                        spawn.assert_not_called()
                        preflight.assert_not_called()
                        self.assertFalse(root.exists())

    def test_worker_boundary_and_development_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for operation in ('fit', 'resume'):
                for limit in (protocol.MEMORY_STOP_BYTES+1, 0, -1, True, float('nan'), '8GiB'):
                    with self.subTest(operation=operation, limit=limit), \
                         patch.object(artifacts, 'reserve_run') as reserve:
                        with self.assertRaises(protocol.ProtocolError):
                            runner.run_fit({'purpose': 'formal', 'operation': operation,
                                            'memory_limit_bytes': limit})
                        reserve.assert_not_called()
            for limit in (protocol.MEMORY_STOP_BYTES-1, protocol.MEMORY_STOP_BYTES+1):
                controls = protocol.resource_controls('development', limit)
                self.assertTrue(controls['development_override'])
                self.assertFalse(controls['complete'])
            # A real tiny development fit also records the effective resource
            # override in configuration, fit report, status and readable summary.
            request = {'purpose': 'development', 'run_id': 'dev', 'operation': 'fit',
                       'config': protocol.FitConfig(epochs=1, hidden_size=4).to_payload(),
                       'output_root': str(root), 'memory_limit_bytes': 16*protocol.GIB}
            result = runner.run_fit(request, data=fx.in_memory('r0', 4, seed=3),
                                    sampler=lambda: {'rss_bytes': 0})
            directory = Path(result['run_dir'])
            for filename in ('config.json', 'report.json'):
                controls = fx.read_json(directory/filename)['protocol_controls']
                self.assertFalse(controls['complete'])
                self.assertTrue(controls['resources']['development_override'])
                self.assertEqual(controls['resources']['rss_stop_bytes'], 16*protocol.GIB)
            self.assertFalse(fx.read_json(directory/'status.json')['protocol_controls_complete'])
            self.assertIn('protocol controls complete: False', (directory/'summary.md').read_text())


    def test_resume_and_selection_cannot_launder_development_resource_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = fx.in_memory('r0', 4, seed=3)
            request = {'purpose': 'development', 'run_id': 'parent', 'operation': 'fit',
                       'config': protocol.FitConfig(epochs=4, hidden_size=4).to_payload(),
                       'output_root': str(root), 'memory_limit_bytes': 16*protocol.GIB}
            stop_epoch = 2
            def interrupt(trajectory, epoch, window):
                if epoch == stop_epoch and window == 1:
                    raise engine.PauseRequest('synthetic_boundary')
            parent = runner.run_fit(request, data=data, sampler=lambda: {'rss_bytes': 0}, after_update=interrupt)
            for name in ('child', 'grandchild'):
                stop_epoch += 1
                resumed = runner.run_fit({**request, 'run_id': name, 'operation': 'resume',
                                          'memory_limit_bytes': protocol.MEMORY_STOP_BYTES,
                                          'parent_dir': parent['run_dir']},
                                         data=data, sampler=lambda: {'rss_bytes': 0}, after_update=interrupt)
                controls = fx.read_json(Path(resumed['run_dir'])/'config.json')['protocol_controls']
                self.assertFalse(controls['complete'])
                self.assertTrue(controls['resources']['inherited_development_override'])
                parent = resumed
            candidates = []
            for index, lr in enumerate(protocol.LR_CANDIDATES):
                directory = fx.synthetic_completed_run(root/'candidates', f'candidate-{index}',
                                                        learning_rate=lr, candidate_role='screening')
                document = fx.read_json(directory/'config.json')
                document['protocol_controls']['complete'] = False
                fx.write_json(directory/'config.json', document)
                candidates.append(selection.load_candidate(directory))
            with self.assertRaises(selection.SelectionError):
                selection.validate_candidates(candidates, purpose='formal')


class LiveStageBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledger = resources.Ledger(self.root/'ledger.json', batch_id='p02-t006')
        self.directory = fx.synthetic_completed_run(self.root/'inputs', 'saved')
        config = fx.read_json(self.directory/'config.json')
        config['budget'] = self.ledger.payload_view()
        fx.write_json(self.directory/'config.json', config)
        self.snapshot = fx.tree_digest(self.root/'inputs')

    def spend(self, seconds):
        self.ledger.record(execution_id='previous', run_id='earlier', seconds=seconds)

    def test_all_five_exhausted_live_stages_skip_work_and_retain_failure(self):
        self.spend(protocol.BATCH_SECONDS)
        stages = (
            ('recompute', lambda dest: checks.run_recompute(run_dir=self.directory, report_path=dest, argv=[]),
             checks, '_recompute_fit_metrics'),
            ('compare', lambda dest: checks.run_compare(run_a=self.directory, run_b=self.directory,
                                                       report_path=dest, argv=[]), checks, 'run_identity'),
            ('diagnose', lambda dest: diagnostics.run_diagnose({
                'purpose': 'development', 'block_dir': str(self.directory),
                'a_runs': {0: str(self.directory)}, 'report_path': str(dest)}), diagnostics, 'build_diagnostics'),
            ('select', lambda dest: runner.run_select({
                'purpose': 'development', 'candidates': [str(self.directory)]*2,
                'block_id': 'selection', 'output_root': str(self.root/'outputs')}), selection, 'load_candidate'),
            ('report', lambda dest: runner.run_report({
                'purpose': 'development', 'block_dir': str(self.directory), 'run_dir': str(self.directory),
                'run_id': 'test-report', 'output_root': str(self.root/'outputs')}), selection, 'load_selection'),
        )
        for name, invoke, module, work in stages:
            with self.subTest(stage=name), patch.object(module, work) as entered:
                result = invoke(self.root/f'{name}.json')
                entered.assert_not_called()
                self.assertIn(result['status'], ('failed', 'paused'))
                saved = fx.read_json(Path(result['report_path']))
                self.assertIn(saved['status'], ('failed', 'paused'))
                self.assertEqual(saved['accounting']['mode'], 'live-batch')
                self.assertEqual(fx.tree_digest(self.root/'inputs'), self.snapshot)
        entries = resources.Ledger(self.ledger.path, batch_id='p02-t006').payload['entries']
        self.assertEqual(len(entries), 6)
        self.assertTrue(all(entry['status'] == 'paused' for entry in entries if entry['execution_id'] != 'previous'))

    def test_mid_stage_crossing_cancels_next_saved_operation_and_bills_failure(self):
        self.spend(protocol.BATCH_SECONDS-2)
        clock = Clock()
        original = checks.load_npy
        entered = []
        def slow_read(*args, **kwargs):
            entered.append(str(args[0]))
            clock.value += 3.0
            return original(*args, **kwargs)  # cancellation point, before np.load
        destination = self.root/'mid-stage.json'
        with patch.object(resources.time, 'monotonic', clock), \
             patch.object(checks, 'load_npy', side_effect=slow_read), \
             patch.object(checks.np, 'load') as native:
            result = checks.run_recompute(run_dir=self.directory, report_path=destination, argv=[])
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(entered), 1)
        native.assert_not_called()
        self.assertIn('BatchBudgetExceeded', destination.read_text())
        self.assertEqual(resources.Ledger(self.ledger.path, batch_id='p02-t006').active_seconds(), protocol.BATCH_SECONDS+1)
        self.assertEqual(fx.tree_digest(self.root/'inputs'), self.snapshot)

    def test_final_publication_overrun_invalidates_only_own_report(self):
        self.spend(protocol.BATCH_SECONDS-2)
        clock = Clock()
        original = checks.write_report
        def delayed(*args, **kwargs):
            published = original(*args, **kwargs)
            clock.value += 3
            return published
        destination = self.root/'late.json'
        with patch.object(resources.time, 'monotonic', clock), patch.object(checks, 'write_report', side_effect=delayed):
            result = checks.run_compare(run_a=self.directory, run_b=self.directory, report_path=destination, argv=[])
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(fx.read_json(destination)['status'], 'failed')
        self.assertEqual(resources.Ledger(self.ledger.path, batch_id='p02-t006').active_seconds(), protocol.BATCH_SECONDS+1)
        self.assertEqual(fx.tree_digest(self.root/'inputs'), self.snapshot)

    def test_selection_crossing_cannot_leave_a_frozen_selection(self):
        self.spend(protocol.BATCH_SECONDS-2)
        clock = Clock()
        candidates = []
        for index, lr in enumerate(protocol.LR_CANDIDATES):
            directory = fx.synthetic_completed_run(self.root/'inputs', f'candidate-{index}',
                                                    learning_rate=lr, candidate_role='screening')
            config = fx.read_json(directory/'config.json')
            config['budget'] = self.ledger.payload_view()
            fx.write_json(directory/'config.json', config)
            candidates.append(str(directory))
        before = fx.tree_digest(self.root/'inputs')
        original = artifacts.write_summary
        def delayed(*args, **kwargs):
            result = original(*args, **kwargs)
            clock.value += 3
            return result
        with patch.object(artifacts, 'write_summary', side_effect=delayed):
            result = runner.run_select({'purpose': 'development', 'candidates': candidates,
                                        'block_id': 'crossing-selection',
                                        'output_root': str(self.root/'outputs'), 'accounting_clock': clock})
        self.assertEqual(result['status'], 'paused')
        document = fx.read_json(Path(result['block_dir'])/'selection.json')
        self.assertFalse(document['frozen'])
        self.assertEqual(document['status'], 'paused')
        self.assertEqual(fx.tree_digest(self.root/'inputs'), before)
        # Both the attempted success summary and the retained pause summary count.
        self.assertEqual(resources.Ledger(self.ledger.path, batch_id='p02-t006').active_seconds(), protocol.BATCH_SECONDS+4)

    def test_exhausted_live_checks_preserve_bad_destinations_and_offline_copies_work(self):
        self.spend(protocol.BATCH_SECONDS)
        sentinel = self.root/'existing.json'
        sentinel.write_text('untouched')
        for destination in (sentinel, self.directory/'forbidden.json'):
            with self.assertRaises(checks.CheckError):
                checks.run_recompute(run_dir=self.directory, report_path=destination, argv=[])
        self.assertEqual(sentinel.read_text(), 'untouched')
        self.ledger.path.unlink()  # original machine's ledger is unavailable
        result = checks.run_compare(run_a=self.directory, run_b=self.directory,
                                    report_path=self.root/'offline.json', argv=[])
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['accounting']['mode'], 'offline')
        self.assertEqual(fx.read_json(self.root/'offline.json')['accounting']['mode'], 'offline')
        self.assertFalse(self.ledger.path.exists())
        self.assertEqual(fx.tree_digest(self.root/'inputs'), self.snapshot)


if __name__ == '__main__':
    unittest.main()
