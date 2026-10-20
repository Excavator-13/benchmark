"""Bounded Windows sharing failures preserve old bytes until atomic recovery."""
import ctypes
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from benchmark.nograph_baseline import artifacts


class AtomicWriteTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.run = artifacts.RunDirectory(Path(self.temporary.name), 'atomic', 'test').reserve()
        self.run.write_text('progress.json', 'old')

    def denied(self):
        error = PermissionError('fixture sharing denial')
        error.winerror = 5
        return error

    def test_transient_retries_same_bytes_and_records_recovery(self):
        replace = os.replace
        with mock.patch.object(artifacts.sys, 'platform', 'win32'), \
             mock.patch.object(artifacts.os, 'replace', side_effect=[self.denied(), self.denied(), None]) as call, \
             mock.patch.object(artifacts.time, 'sleep') as pause:
            self.run.write_text('progress.json', 'new')
        self.assertEqual(call.call_count, 3)
        self.assertEqual(call.call_args_list[0], call.call_args_list[-1])
        self.assertEqual(pause.call_count, 2)
        # Mocked replace did not move; use its source to establish saved bytes.
        source, target = call.call_args.args
        self.assertEqual(Path(source).read_bytes(), b'new')
        self.assertEqual(Path(target).read_bytes(), b'old')
        replace(source, target)
        self.assertIn('atomic_replace_recovered', self.run.events_path.read_text())

    def test_permanent_denial_is_bounded_and_preserves_checkpoint(self):
        with mock.patch.object(artifacts.sys, 'platform', 'win32'), \
             mock.patch.object(artifacts.os, 'replace', side_effect=self.denied()) as call, \
             mock.patch.object(artifacts.time, 'sleep') as pause:
            with self.assertRaises(PermissionError):
                self.run.write_text('progress.json', 'new')
        self.assertEqual(call.call_count, 8)
        self.assertLess(sum(c.args[0] for c in pause.call_args_list), 1.1)
        self.assertEqual((self.run.path/'progress.json').read_bytes(), b'old')
        self.assertEqual(list(self.run.path.glob('.tmp-*'))[0].read_bytes(), b'new')

    def test_other_errors_are_not_retried(self):
        with mock.patch.object(artifacts.os, 'replace', side_effect=OSError('disk error')) as call:
            with self.assertRaises(OSError):
                self.run.write_text('progress.json', 'new')
        self.assertEqual(call.call_count, 1)

    @unittest.skipUnless(os.name == 'nt', 'requires Windows sharing modes')
    def test_real_windows_reader_lock_recovers_after_release(self):
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        target = self.run.path/'progress.json'
        handle = kernel.CreateFileW(str(target), 0x80000000, 3, None, 3, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        # A live reader sharing reads/writes but not deletion reproduces WinError5/32.
        with self.assertRaises(PermissionError):
            source = self.run.path/'probe.tmp'
            source.write_bytes(b'probe')
            os.replace(source, target)
        timer = threading.Timer(0.08, lambda: kernel.CloseHandle(handle))
        timer.start()
        try:
            self.run.write_text('progress.json', 'new')
        finally:
            timer.join()
        self.assertEqual(target.read_bytes(), b'new')
        self.assertIn('atomic_replace_recovered', self.run.events_path.read_text())
