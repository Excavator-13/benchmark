"""Watchdogs stop the owned graph process and never progress to another member."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from benchmark.graph_value_skeleton import readiness


class ReadinessTest(unittest.TestCase):
    def test_elapsed_and_idle_watchdogs(self):
        directory=Path(tempfile.mkdtemp(prefix='gvs-watchdog-'))
        for max_seconds,idle_seconds in ((1,60),(600,1)):
            process=mock.Mock();process.poll.return_value=None
            clock=mock.Mock(side_effect=[0,0,2])
            with mock.patch.object(readiness,'stop_tree') as stop:
                with self.assertRaises(TimeoutError):
                    readiness.monitor(process,directory,max_seconds=max_seconds,
                        idle_seconds=idle_seconds,clock=clock,sleeper=lambda _:None)
                stop.assert_called_once_with(process)

    def test_watchdog_retains_timeout_when_termination_fails(self):
        process = mock.Mock()
        process.poll.return_value = None
        with mock.patch.object(readiness, 'stop_tree', side_effect=RuntimeError('denied')):
            with self.assertRaisesRegex(TimeoutError, 'per-graph elapsed limit') as raised:
                readiness.monitor(process, Path(tempfile.mkdtemp()), max_seconds=1,
                                  clock=mock.Mock(side_effect=[0, 0, 2]), sleeper=lambda _: None)
        self.assertIsInstance(raised.exception.__cause__, RuntimeError)

    def test_failed_worker_and_matrix_pause(self):
        directory=Path(tempfile.mkdtemp(prefix='gvs-readiness-'))
        process=mock.Mock();process.poll.return_value=1;process.returncode=1
        with self.assertRaises(RuntimeError): readiness.monitor(process,directory)
        with mock.patch.object(readiness.subprocess,'Popen',return_value=process) as popen, \
             mock.patch.object(readiness,'monitor',side_effect=TimeoutError('fixture timeout')), \
             mock.patch.object(readiness,'stop_tree'):
            with self.assertRaises(TimeoutError): readiness.run_matrix('paused',directory)
            self.assertEqual(popen.call_count,1)
            command=popen.call_args.args[0]
            self.assertIn('prepare-shuffle',command)
            self.assertNotIn('run',command)
        status=readiness.prepared.read_json(directory/'paused'/'status.json')
        self.assertEqual(status['state'],'paused')
        self.assertEqual(readiness.prepared.read_json(directory/'paused'/'readiness.json')['members'],[])

    def test_cleanup_failure_preserves_original_error_and_pause(self):
        directory = Path(tempfile.mkdtemp(prefix='gvs-cleanup-'))
        process = mock.Mock(pid=123)
        with mock.patch.object(readiness.subprocess, 'Popen', return_value=process), \
             mock.patch.object(readiness, 'monitor', side_effect=TimeoutError('original timeout')), \
             mock.patch.object(readiness, 'stop_tree', side_effect=RuntimeError('termination denied')):
            with self.assertRaisesRegex(TimeoutError, 'original timeout'):
                readiness.run_matrix('cleanup-failed', directory)
        manifest = readiness.prepared.read_json(directory/'cleanup-failed'/'readiness.json')
        self.assertEqual(manifest['state'], 'paused')
        self.assertIn('original timeout', manifest['reason'])
        self.assertIn('termination denied', manifest['cleanup_error'])
        self.assertTrue(manifest['worker_may_be_running'])
        self.assertEqual(manifest['worker_pid'], 123)
        self.assertEqual(readiness.prepared.read_json(
            directory/'cleanup-failed'/'status.json')['state'], 'paused')
