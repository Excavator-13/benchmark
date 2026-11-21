"""Stage-A ledger transaction lock tests.

Only disposable ledgers and the test-only file lock backend are used here.
"""

from __future__ import annotations

import copy
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

from benchmark.multivariate_time_series.temporal import resources
from benchmark.multivariate_time_series.temporal.ledger_lock import (
    AcquireResult,
    AcquireStatus,
    FileTestLedgerLock,
    ledger_sidecar_path,
    NoopLedgerWriteLock,
    ReleaseResult,
    ReleaseStatus,
)


def _spawn_writer(path, cwd, operation, identity, ready, start, contending, result):
    os.chdir(cwd)
    try:
        ledger = resources.Ledger(
            Path(path), batch_id="isolated-lock-test",
            write_lock=FileTestLedgerLock(Path(path), contention_event=contending),
        )
        ready.set()
        if not start.wait(timeout=10):
            raise TimeoutError("writer start event timed out")
        if operation == "record":
            ledger.record(execution_id=identity, run_id="worker", seconds=1)
        else:
            ledger.register_debit(debit_id=identity, seconds=1, reason="worker debit")
        result.send({"ok": True})
    except BaseException as exc:
        result.send({"ok": False, "error": repr(exc)})
    finally:
        result.close()


def _spawn_holder(path, ready):
    lock = FileTestLedgerLock(Path(path))
    acquired = lock.acquire(timeout=10)
    ready.send(acquired.status.value)
    ready.close()
    # A holder killed while waiting on a shared multiprocessing.Event can leave
    # that Event's condition bookkeeping unusable.  Wait only on a local event;
    # the pipe above proves ownership before the parent kills this process.
    threading.Event().wait(timeout=10)
    os._exit(0)


def _spawn_contender(path, marker_path, contending, entered, leave, result):
    lock = FileTestLedgerLock(Path(path), contention_event=contending)
    acquired = lock.acquire(timeout=10)
    if acquired.status not in (AcquireStatus.ACQUIRED, AcquireStatus.ABANDONED):
        result.send({"status": acquired.status.value})
        result.close()
        return
    marker = Path(marker_path)
    try:
        marker.open("x").close()
        overlap = 1
    except FileExistsError:
        overlap = 2
    entered.set()
    if not leave.wait(timeout=10):
        raise TimeoutError("critical-section release event timed out")
    if marker.exists():
        marker.unlink()
    released = lock.release()
    result.send({"status": acquired.status.value, "overlap": overlap,
                 "release": released.status.value})
    result.close()


class ScriptedLock:
    def __init__(self, acquire_status=AcquireStatus.ACQUIRED,
                 release_status=ReleaseStatus.RELEASED, release_error=None):
        self.acquire_status = acquire_status
        self.release_status = release_status
        self.release_error = release_error
        self.acquires = 0
        self.releases = 0
        self.active = False
        self.ledger_path = None

    def acquire(self, *, timeout=None, binding=None):
        self.acquires += 1
        if self.acquire_status in (AcquireStatus.ACQUIRED, AcquireStatus.ABANDONED):
            self.active = True
        return AcquireResult(self.acquire_status, "scripted")

    def release(self, *, binding=None):
        self.releases += 1
        if self.release_error is not None:
            raise self.release_error
        if self.release_status is ReleaseStatus.RELEASED:
            self.active = False
        return ReleaseResult(self.release_status, "scripted")

    def binding_matches(self, binding):
        try:
            return (
                self.ledger_path is not None
                and binding.ledger_path
                == resources.canonical_ledger_path(self.ledger_path)
            )
        except Exception:
            return False


class LedgerLockTests(unittest.TestCase):
    def setUp(self):
        self.worktree = Path(__file__).resolve().parents[2]
        self.root = (
            Path(__file__).resolve().parents[3]
            / f".p02-t006-ledger-lock-{uuid.uuid4().hex}"
        )
        self.root.mkdir()
        self._cleanup_checks = []
        self.addCleanup(self._cleanup_test_directory)
        self.path = self.root / "ledger.json"
        self.lock_path = FileTestLedgerLock(self.path).path

    def _cleanup_test_directory(self):
        # All uniquely named ledger-write temp files are within this test's root.
        shutil.rmtree(self.root)
        self.assertFalse(self.root.exists())
        for check in self._cleanup_checks:
            check()

    def ledger(self, lock=None):
        lock = lock or NoopLedgerWriteLock()
        if isinstance(lock, ScriptedLock):
            lock.ledger_path = resources.canonical_ledger_path(self.path)
        ledger = resources.Ledger(
            self.path, batch_id="isolated-lock-test", write_lock=lock,
        )
        ledger.record(execution_id="initial", run_id="test", seconds=2)
        return ledger

    def bind_scripted(self, lock):
        lock.ledger_path = resources.canonical_ledger_path(self.path)
        return lock

    def test_record_and_debit_share_one_lock_and_write_inside_it(self):
        lock = ScriptedLock()
        ledger = self.ledger(lock)
        self.assertEqual(lock.acquires, 1)
        observed = []
        original = ledger._write

        def checked_write(*args, **kwargs):
            observed.append(lock.active)
            return original(*args, **kwargs)

        ledger._write = checked_write
        ledger.record(execution_id="run", run_id="test", seconds=3)
        ledger.register_debit(debit_id="debit", seconds=4, reason="test")
        self.assertEqual(lock.acquires, 3)
        self.assertEqual(lock.releases, 3)
        self.assertEqual(observed, [True, True])
        self.assertEqual(ledger.active_seconds(), 5)
        self.assertEqual(ledger.debited_seconds(), 4)

    def test_unconfigured_lock_rejects_record_and_debit(self):
        ledger = resources.Ledger(self.path, batch_id="isolated-lock-test")
        before = ledger.payload
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id="unconfigured", run_id="test", seconds=1)
        with self.assertRaises(resources.ResourceError):
            ledger.register_debit(debit_id="unconfigured", seconds=1, reason="test")
        self.assertEqual(ledger.payload, before)

    def test_explicit_noop_is_only_a_test_injection(self):
        ledger = resources.Ledger(
            self.path, batch_id="isolated-lock-test",
            write_lock=NoopLedgerWriteLock(),
        )
        ledger.record(execution_id="explicit", run_id="test", seconds=1)
        self.assertEqual(ledger.active_seconds(), 1)

    def test_acquire_failure_states_fail_closed_without_read_modify_write(self):
        for status in (
            AcquireStatus.TIMEOUT, AcquireStatus.WAIT_FAILED, AcquireStatus.UNKNOWN,
        ):
            with self.subTest(status=status):
                lock = self.bind_scripted(ScriptedLock(acquire_status=status))
                ledger = self.ledger()
                ledger.write_lock = lock
                before = self.path.read_bytes()
                with self.assertRaises(resources.ResourceError):
                    ledger.record(execution_id="blocked", run_id="test", seconds=3)
                with self.assertRaises(resources.ResourceError):
                    ledger.register_debit(
                        debit_id="blocked-debit", seconds=3, reason="test"
                    )
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(lock.releases, 0)

    def test_release_failure_closes_instance_after_committed_write(self):
        lock = self.bind_scripted(ScriptedLock(release_status=ReleaseStatus.FAILED))
        ledger = self.ledger()
        ledger.write_lock = lock
        before = self.path.read_bytes()
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id="committed", run_id="test", seconds=3)
        self.assertNotEqual(self.path.read_bytes(), before)
        self.assertTrue(ledger._write_uncertain)
        with self.assertRaises(resources.ResourceError):
            ledger.active_seconds()

    def test_release_exception_after_business_success_poisoned_instance(self):
        lock = self.bind_scripted(ScriptedLock(release_error=RuntimeError("release exploded")))
        ledger = self.ledger()
        ledger.write_lock = lock
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id="release-success", run_id="test", seconds=3)
        self.assertTrue(ledger._write_uncertain)
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id="after", run_id="test", seconds=1)
        with self.assertRaises(resources.ResourceError):
            ledger.active_seconds()

    def test_release_exception_after_business_failure_preserves_original_error(self):
        lock = self.bind_scripted(ScriptedLock(release_error=RuntimeError("release exploded")))
        ledger = self.ledger()
        ledger.write_lock = lock
        original = ValueError("business write failed")
        ledger._write = lambda **kwargs: (_ for _ in ()).throw(original)
        with self.assertRaises(ValueError) as caught:
            ledger.record(execution_id="release-failure", run_id="test", seconds=3)
        self.assertIs(caught.exception, original)
        self.assertTrue(ledger._write_uncertain)
        with self.assertRaises(resources.ResourceError):
            ledger.register_debit(debit_id="after", seconds=1, reason="test")

    def test_unlock_failure_closes_handle_and_poison_writes(self):
        self.ledger()

        class FailingUnlockLock(FileTestLedgerLock):
            def __init__(self, path):
                super().__init__(path)
                self.close_called = False

            def _unlock_os(self):
                raise OSError("unlock failed")

            def acquire(self, *, timeout=None, binding=None):
                result = super().acquire(timeout=timeout, binding=binding)
                if result.status in (AcquireStatus.ACQUIRED, AcquireStatus.ABANDONED):
                    real_handle = self._handle
                    owner = self

                    class HandleProxy:
                        def __getattr__(self, name):
                            return getattr(real_handle, name)

                        def close(self):
                            owner.close_called = True
                            return real_handle.close()

                    self._handle = HandleProxy()
                return result

        lock = FailingUnlockLock(self.path)
        ledger = resources.Ledger(
            self.path, batch_id="isolated-lock-test", write_lock=lock,
        )
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id="unlock-failure", run_id="test", seconds=1)
        self.assertTrue(lock.close_called)
        self.assertIsNone(lock._handle)
        self.assertFalse(lock._owned)
        self.assertTrue(ledger._write_uncertain)
        with self.assertRaises(resources.ResourceError):
            ledger.register_debit(
                debit_id="after-unlock-failure", seconds=1, reason="blocked",
            )

    def test_abandoned_recovery_does_not_use_target_duplicate_replacement(self):
        lock = self.bind_scripted(ScriptedLock(acquire_status=AcquireStatus.ABANDONED))
        ledger = self.ledger()
        ledger.write_lock = lock
        payload = copy.deepcopy(ledger.payload)
        payload["entries"].append(copy.deepcopy(payload["entries"][0]))
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id="initial", run_id="test", seconds=7)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(lock.releases, 1)

    def test_normal_acquisition_retains_target_duplicate_replacement_exception(self):
        lock = self.bind_scripted(ScriptedLock())
        ledger = self.ledger(lock)
        payload = copy.deepcopy(ledger.payload)
        payload["entries"].append(copy.deepcopy(payload["entries"][0]))
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        ledger.record(execution_id="initial", run_id="test", seconds=7)
        self.assertEqual(ledger.active_seconds(), 7)

    def test_residual_temp_file_blocks_and_preserves_confirmed_state(self):
        lock = self.bind_scripted(ScriptedLock())
        ledger = self.ledger(lock)
        before = self.path.read_bytes()
        residual = self.path.parent / f".{self.path.name}.ledger-write-stale.tmp"
        residual.write_text("现场", encoding="utf-8")
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id="blocked", run_id="test", seconds=3)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse(ledger._write_uncertain)
        self.assertTrue(residual.exists())
        residual.unlink()
        ledger.record(execution_id="allowed", run_id="test", seconds=3)
        self.assertEqual(ledger.active_seconds(), 5)

    def test_file_backend_reports_timeout_then_abandoned_recovery(self):
        owner = FileTestLedgerLock(self.path)
        self.assertEqual(owner.acquire(timeout=1).status, AcquireStatus.ACQUIRED)
        self.assertEqual(owner._read_owner().get("state"), "held")
        waiting = FileTestLedgerLock(self.path, poll_interval=0.01)
        waiting_result = waiting.acquire(timeout=0.05)
        self.assertEqual(waiting_result.status, AcquireStatus.TIMEOUT, waiting_result.detail)
        self.assertEqual(owner.release().status, ReleaseStatus.RELEASED)
        self.lock_path.write_text("", encoding="utf-8")
        recovered = FileTestLedgerLock(self.path, poll_interval=0.01)
        result = recovered.acquire(timeout=1)
        self.assertEqual(result.status, AcquireStatus.UNKNOWN)
        self.assertTrue(self.lock_path.exists())

    def _child(self, code, *args, cwd=None):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[3])
        process = subprocess.Popen([
            sys.executable, "-c", code, *(str(arg) for arg in args),
        ], env=env, cwd=str(cwd or self.worktree))
        self.addCleanup(self._reap_child, process)
        return process

    @staticmethod
    def _reap_child(process):
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)

    @staticmethod
    def _wait_file(path, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return True
            time.sleep(0.02)
        return False

    @staticmethod
    def _wait_child(process, timeout=10):
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            raise AssertionError("spawned test process did not terminate")

    def _spawn_process(self, context, target, *args):
        process = context.Process(target=target, args=args)
        process.start()
        self.addCleanup(self._reap_spawn, process)
        return process

    @staticmethod
    def _reap_spawn(process):
        if process.is_alive():
            process.kill()
        process.join(timeout=5)
        if process.is_alive():
            raise AssertionError("spawn process did not terminate")
        process.close()

    def _receive(self, pipe):
        self.assertTrue(pipe.poll(10), "spawn result pipe timed out")
        return pipe.recv()

    def _run_spawn_writers(self, paths_and_operations):
        context = multiprocessing.get_context("spawn")
        start = context.Event()
        events = []
        pipes = []
        processes = []
        holder = FileTestLedgerLock(self.path)
        for path_arg, operation, identity in paths_and_operations:
            ready, contending = context.Event(), context.Event()
            reader, writer = context.Pipe(duplex=False)
            self.addCleanup(reader.close)
            self.addCleanup(writer.close)
            processes.append(self._spawn_process(
                context, _spawn_writer, path_arg, str(self.worktree), operation,
                identity, ready, start, contending, writer,
            ))
            writer.close()
            events.append((ready, contending))
            pipes.append(reader)
        try:
            self.assertTrue(all(ready.wait(10) for ready, _ in events))
            self.assertEqual(holder.acquire(timeout=2).status, AcquireStatus.ACQUIRED)
            start.set()
            self.assertTrue(all(contending.wait(10) for _, contending in events))
            self.assertEqual(holder.release().status, ReleaseStatus.RELEASED)
            documents = [self._receive(pipe) for pipe in pipes]
            self.assertTrue(all(document["ok"] for document in documents), documents)
            for process in processes:
                process.join(timeout=10)
                self.assertFalse(process.is_alive())
                self.assertEqual(process.exitcode, 0)
        finally:
            start.set()
            if holder._owned:
                holder.release()

    def test_spawn_processes_preserve_all_interleaved_record_and_debit_ids(self):
        self.ledger()
        self._run_spawn_writers([
            (str(self.path), "record" if index % 2 == 0 else "debit",
             f"spawn-{'record' if index % 2 == 0 else 'debit'}-{index}")
            for index in range(4)
        ])
        reopened = resources.Ledger(self.path, batch_id="isolated-lock-test")
        ids = {entry["execution_id"] for entry in reopened.payload["entries"]}
        self.assertTrue({"spawn-record-0", "spawn-record-2"}.issubset(ids))
        self.assertTrue({"spawn-debit-1", "spawn-debit-3"}.issubset(ids))

    def test_spawn_relative_and_absolute_ledger_paths_share_one_sidecar(self):
        self.ledger()
        relative = os.path.relpath(self.path, start=self.worktree)
        self._run_spawn_writers([
            (str(self.path), "record", "alias-0"),
            (relative, "record", "alias-1"),
        ])
        reopened = resources.Ledger(self.path, batch_id="isolated-lock-test")
        ids = {entry["execution_id"] for entry in reopened.payload["entries"]}
        self.assertTrue({"initial", "alias-0", "alias-1"}.issubset(ids))

    def test_mismatched_injected_lock_rejects_record_and_debit_without_changes(self):
        other = self.root / "other-ledger.json"
        wrong_lock = FileTestLedgerLock(other)
        ledger = self.ledger()
        ledger.write_lock = wrong_lock
        before = self.path.read_bytes()
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id="wrong-record", run_id="test", seconds=1)
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(resources.ResourceError):
            ledger.register_debit(
                debit_id="wrong-debit", seconds=1, reason="mismatch"
            )
        self.assertEqual(self.path.read_bytes(), before)

    def test_unbound_injected_lock_rejects_record_and_debit_without_changes(self):
        class UnboundLock:
            def acquire(self, *, timeout=None):
                return AcquireResult(AcquireStatus.ACQUIRED, "unbound")

            def release(self):
                return ReleaseResult(ReleaseStatus.RELEASED, "unbound")

        confirmed = self.ledger()
        before = self.path.read_bytes()
        confirmed.write_lock = UnboundLock()
        with self.assertRaises(resources.ResourceError):
            confirmed.record(execution_id="unbound-record", run_id="test", seconds=1)
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(resources.ResourceError):
            confirmed.register_debit(
                debit_id="unbound-debit", seconds=1, reason="unbound"
            )
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_binding_is_rejected_before_constructor_reads_ledger(self):
        self.ledger()
        before = self.path.read_bytes()

        class NoPath:
            def acquire(self, *, timeout=None):
                return AcquireResult(AcquireStatus.ACQUIRED)

            def release(self):
                return ReleaseResult(ReleaseStatus.RELEASED)

        class DeclaredPath:
            def __init__(self, value):
                self.ledger_path = value

            def binding_matches(self, ledger_path):
                return True

            def acquire(self, *, timeout=None):
                return AcquireResult(AcquireStatus.ACQUIRED)

            def release(self):
                return ReleaseResult(ReleaseStatus.RELEASED)

        locks = (
            NoPath(),
            DeclaredPath(None),
            DeclaredPath(""),
            DeclaredPath(object()),
            DeclaredPath(self.root / "other-ledger.json"),
        )
        for lock in locks:
            reads = []
            original_read_text = Path.read_text

            def counted_read_text(path, *args, **kwargs):
                if Path(path) == self.path:
                    reads.append(path)
                return original_read_text(path, *args, **kwargs)

            with self.subTest(lock=type(lock).__name__):
                with mock.patch.object(Path, "read_text", new=counted_read_text):
                    with self.assertRaises(resources.ResourceError):
                        resources.Ledger(
                            self.path,
                            batch_id="isolated-lock-test",
                            write_lock=lock,
                        )
                self.assertEqual(reads, [])
                self.assertEqual(self.path.read_bytes(), before)

    def test_file_lock_binding_cannot_be_separated_from_sidecar(self):
        lock = FileTestLedgerLock(self.path)
        ledger = resources.Ledger(
            self.path, batch_id="isolated-lock-test", write_lock=lock,
        )
        ledger.record(execution_id="initial", run_id="test", seconds=1)
        before = self.path.read_bytes()
        other = self.root / "other-ledger.json"
        self.assertRaises(AttributeError, setattr, lock, "ledger_path", other)
        self.assertRaises(AttributeError, setattr, lock, "_canonical_ledger_path", other)
        for operation in (
            lambda: ledger.record(
                execution_id="tampered-path", run_id="test", seconds=1,
            ),
            lambda: ledger.register_debit(
                debit_id="tampered-path-debit", seconds=1, reason="tampered",
            ),
        ):
            with self.assertRaises(resources.ResourceError):
                operation()
        self.assertEqual(self.path.read_bytes(), before)

        sidecar_lock = FileTestLedgerLock(self.path)
        sidecar_ledger = resources.Ledger(
            self.path, batch_id="isolated-lock-test", write_lock=sidecar_lock,
        )
        before_sidecar = self.path.read_bytes()
        self.assertRaises(
            AttributeError, setattr, sidecar_lock, "_canonical_sidecar_path",
            ledger_sidecar_path(other),
        )
        for operation in (
            lambda: sidecar_ledger.record(
                execution_id="tampered-sidecar", run_id="test", seconds=1,
            ),
            lambda: sidecar_ledger.register_debit(
                debit_id="tampered-sidecar-debit", seconds=1, reason="tampered",
            ),
        ):
            with self.assertRaises(resources.ResourceError):
                operation()
        self.assertEqual(self.path.read_bytes(), before_sidecar)

    def test_write_uses_verified_lock_when_attribute_is_replaced_before_acquire(self):
        ledger = self.ledger()
        replacement = object()

        class SwapBeforeAcquire:
            def __init__(self, owner):
                self.owner = owner
                self.ledger_path = resources.canonical_ledger_path(owner.path)
                self.acquires = 0
                self.releases = 0

            def binding_matches(self, binding):
                self.owner.write_lock = replacement
                return binding.ledger_path == self.ledger_path

            def acquire(self, *, timeout=None, binding=None):
                self.acquires += 1
                return AcquireResult(AcquireStatus.TIMEOUT, "scripted replacement")

            def release(self, *, binding=None):
                self.releases += 1
                return ReleaseResult(ReleaseStatus.RELEASED)

        lock = SwapBeforeAcquire(ledger)
        before = self.path.read_bytes()
        ledger.write_lock = lock
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id="swap-before-acquire", run_id="test", seconds=1)
        self.assertEqual(lock.acquires, 1)
        self.assertEqual(lock.releases, 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_release_uses_the_same_verified_lock_after_attribute_replacement(self):
        ledger = self.ledger()
        replacement = object()
        lock = self.bind_scripted(ScriptedLock())
        original_acquire = lock.acquire

        def acquire_and_replace(*, timeout=None, binding=None):
            result = original_acquire(timeout=timeout, binding=binding)
            ledger.write_lock = replacement
            return result

        lock.acquire = acquire_and_replace
        ledger.write_lock = lock
        ledger.record(execution_id="swap-before-release", run_id="test", seconds=1)
        self.assertEqual(lock.acquires, 1)
        self.assertEqual(lock.releases, 1)
        self.assertEqual(ledger.payload["entries"][-1]["execution_id"], "swap-before-release")

    def test_file_lock_binding_change_during_acquire_fails_closed(self):
        self.ledger()
        other = self.root / "other-ledger.json"
        self.assertRaises(
            AttributeError,
            setattr,
            FileTestLedgerLock(self.path),
            "path",
            ledger_sidecar_path(other),
        )
        for index, operation in enumerate(("record", "debit")):
            gate = self.root / f"binding-gate-{index}"
            release = self.root / f"binding-release-{index}"
            lock = FileTestLedgerLock(
                self.path,
                before_open_signal=gate,
                before_open_release=release,
            )
            ledger = resources.Ledger(
                self.path, batch_id="isolated-lock-test", write_lock=lock,
            )
            before = self.path.read_bytes()
            errors = []

            def invoke():
                try:
                    if operation == "record":
                        ledger.record(
                            execution_id="binding-window-record",
                            run_id="test",
                            seconds=1,
                        )
                    else:
                        ledger.register_debit(
                            debit_id="binding-window-debit",
                            seconds=1,
                            reason="binding window",
                        )
                except BaseException as exc:  # pragma: no cover - asserted below
                    errors.append(exc)

            thread = threading.Thread(target=invoke)
            thread.start()
            try:
                self.assertTrue(self._wait_file(gate))
                self.assertRaises(
                    AttributeError, setattr, lock, "_canonical_sidecar_path",
                    ledger_sidecar_path(other),
                )
                release.write_text("go", encoding="utf-8")
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(len(errors), 1)
                self.assertIsInstance(errors[0], resources.ResourceError)
                self.assertEqual(self.path.read_bytes(), before)
            finally:
                release.write_text("go", encoding="utf-8")
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())

    def test_ledger_path_change_during_acquire_fails_closed(self):
        self.ledger()
        other = self.root / "other-ledger.json"
        for index, operation in enumerate(("record", "debit")):
            gate = self.root / f"ledger-path-gate-{index}"
            release = self.root / f"ledger-path-release-{index}"
            lock = FileTestLedgerLock(
                self.path,
                before_open_signal=gate,
                before_open_release=release,
            )
            ledger = resources.Ledger(
                self.path, batch_id="isolated-lock-test", write_lock=lock,
            )
            before = self.path.read_bytes()
            errors = []

            def invoke():
                try:
                    if operation == "record":
                        ledger.record(
                            execution_id="ledger-path-window-record",
                            run_id="test",
                            seconds=1,
                        )
                    else:
                        ledger.register_debit(
                            debit_id="ledger-path-window-debit",
                            seconds=1,
                            reason="ledger path window",
                        )
                except BaseException as exc:  # pragma: no cover - asserted below
                    errors.append(exc)

            thread = threading.Thread(target=invoke)
            thread.start()
            try:
                self.assertTrue(self._wait_file(gate))
                self.assertRaises(AttributeError, setattr, ledger, "path", other)
                self.assertRaises(AttributeError, setattr, ledger, "_path", other)
                self.assertRaises(AttributeError, setattr, ledger, "_path_binding", other)
                release.write_text("go", encoding="utf-8")
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(len(errors), 1)
                self.assertIsInstance(errors[0], resources.ResourceError)
                self.assertEqual(self.path.read_bytes(), before)
                self.assertFalse(other.exists())
            finally:
                release.write_text("go", encoding="utf-8")
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())

    def test_transaction_threads_one_binding_without_public_path_reads(self):
        for operation in ("record", "debit"):
            with self.subTest(operation=operation):
                lock = FileTestLedgerLock(self.path)
                ledger = self.ledger(lock)
                binding = ledger._capture_path_binding()
                observed = []
                methods = ("_load", "_reload_for_write", "_write")
                originals = {name: getattr(ledger, name) for name in methods}

                def checked(name):
                    def call(*args, **kwargs):
                        self.assertIs(kwargs["binding"], binding)
                        observed.append(name)
                        return originals[name](*args, **kwargs)
                    return call

                def public_path_read(_):
                    raise AssertionError("transaction reread a public path")

                with mock.patch.object(resources.Ledger, "path", property(public_path_read)), \
                     mock.patch.object(FileTestLedgerLock, "path", property(public_path_read)), \
                     mock.patch.object(FileTestLedgerLock, "ledger_path", property(public_path_read)), \
                     mock.patch.object(ledger, "_load", side_effect=checked("_load")), \
                     mock.patch.object(ledger, "_reload_for_write", side_effect=checked("_reload_for_write")), \
                     mock.patch.object(ledger, "_write", side_effect=checked("_write")), \
                     mock.patch.object(lock, "acquire", wraps=lock.acquire) as acquire, \
                     mock.patch.object(lock, "release", wraps=lock.release) as release:
                    if operation == "record":
                        ledger.record(execution_id="snapshot", run_id="test", seconds=1)
                    else:
                        ledger.register_debit(debit_id="snapshot-debit", seconds=1, reason="test")
                    self.assertIs(acquire.call_args.kwargs["binding"], binding)
                    self.assertIs(release.call_args.kwargs["binding"], binding)
                self.assertEqual(observed, ["_reload_for_write", "_load", "_write"])

    def test_dual_path_tampering_before_publication_preserves_original_bytes(self):
        for operation in ("record", "debit"):
            with self.subTest(operation=operation):
                ledger = self.ledger()
                before = self.path.read_bytes()
                other = self.root / "not-the-transaction-ledger.json"
                original_deepcopy = resources.copy.deepcopy

                def tampering_copy(value, *args, **kwargs):
                    for name in ("_path", "_path_binding"):
                        self.assertRaises(AttributeError, setattr, ledger, name, other)
                    return original_deepcopy(value, *args, **kwargs)

                with mock.patch.object(resources.copy, "deepcopy", side_effect=tampering_copy), \
                     mock.patch.object(resources.os, "replace", side_effect=AssertionError) as publish:
                    with self.assertRaises(resources.ResourceError):
                        if operation == "record":
                            ledger.record(execution_id="tamper", run_id="test", seconds=1)
                        else:
                            ledger.register_debit(debit_id="tamper", seconds=1, reason="test")
                    publish.assert_not_called()
                self.assertEqual(self.path.read_bytes(), before)
                self.assertFalse(other.exists())

    def test_path_change_after_publication_is_uncertain(self):
        for operation in ("record", "debit"):
            with self.subTest(operation=operation):
                ledger = self.ledger()
                before = self.path.read_bytes()
                replace = resources.os.replace
                other = self.root / "not-the-published-ledger.json"

                def publish_then_tamper(source, destination):
                    self.assertEqual(destination, self.path)
                    replace(source, destination)
                    self.assertRaises(AttributeError, setattr, ledger, "_path", other)
                    self.assertRaises(AttributeError, setattr, ledger, "_path_binding", other)

                with mock.patch.object(resources.os, "replace", side_effect=publish_then_tamper):
                    with self.assertRaises(resources.ResourceError):
                        if operation == "record":
                            ledger.record(execution_id="published", run_id="test", seconds=1)
                        else:
                            ledger.register_debit(debit_id="published-debit", seconds=1, reason="test")
                self.assertNotEqual(self.path.read_bytes(), before)
                self.assertTrue(ledger._write_uncertain)
                self.assertFalse(other.exists())

    def test_business_path_unlock_and_close_errors_are_all_retained(self):
        ledger = self.ledger()
        lock = FileTestLedgerLock(self.path)
        ledger.write_lock = lock
        business_error = ValueError("original business failure")
        unlock_error = OSError("original unlock failure")
        close_error = OSError("original close failure")
        before = self.path.read_bytes()
        real_acquire = lock.acquire

        def acquire_with_failing_close(**kwargs):
            result = real_acquire(**kwargs)
            real_handle = lock._handle

            class CloseFailure:
                def __getattr__(self, name):
                    return getattr(real_handle, name)

                def close(self):
                    real_handle.close()
                    raise close_error

            lock._handle = CloseFailure()
            return result

        def fail_business(**kwargs):
            for name in ("_path", "_path_binding"):
                self.assertRaises(AttributeError, setattr, ledger, name, self.root / "other.json")
            raise business_error

        with mock.patch.object(lock, "acquire", side_effect=acquire_with_failing_close), \
             mock.patch.object(lock, "_unlock_os", side_effect=unlock_error), \
             mock.patch.object(ledger, "_write", side_effect=fail_business):
            with self.assertRaises(ValueError) as caught:
                ledger.record(execution_id="failure", run_id="test", seconds=1)
        self.assertIs(caught.exception, business_error)

        def descendants(error):
            yield error
            if isinstance(error, BaseExceptionGroup):
                for child in error.exceptions:
                    yield from descendants(child)
            if error.__cause__ is not None:
                yield from descendants(error.__cause__)

        errors = list(descendants(caught.exception))
        self.assertIn(unlock_error, errors)
        self.assertIn(close_error, errors)
        self.assertTrue(any("path identity" in str(error) for error in errors))
        self.assertTrue(ledger._write_uncertain)
        self.assertIsNone(lock._handle)
        self.assertFalse(lock._owned)
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_publication_retains_unique_temp_and_blocks_reopened_writer(self):
        ledger = self.ledger(FileTestLedgerLock(self.path))
        before = self.path.read_bytes()
        with mock.patch.object(resources.os, "replace", side_effect=OSError("publish failed")):
            with self.assertRaises(OSError):
                ledger.record(execution_id="failed", run_id="test", seconds=1)
        residuals = list(self.root.glob(f".{self.path.name}.ledger-write-*.tmp"))
        self.assertEqual(len(residuals), 1)
        self.assertEqual(self.path.read_bytes(), before)
        reopened = resources.Ledger(
            self.path, batch_id="isolated-lock-test", write_lock=FileTestLedgerLock(self.path),
        )
        for operation in ("record", "debit"):
            with self.assertRaises(resources.ResourceError):
                if operation == "record":
                    reopened.record(execution_id="later", run_id="test", seconds=1)
                else:
                    reopened.register_debit(debit_id="later", seconds=1, reason="test")
        self.assertTrue(residuals[0].exists())
        self.assertEqual(self.path.read_bytes(), before)
        self._cleanup_checks.append(lambda: self.assertFalse(residuals[0].exists()))

    def test_spawn_waiters_take_over_after_abrupt_holder_exit_without_overlap(self):
        self.ledger()
        context = multiprocessing.get_context("spawn")
        reader, writer = context.Pipe(duplex=False)
        self.addCleanup(reader.close)
        self.addCleanup(writer.close)
        entered, leave = context.Event(), context.Event()
        holder = self._spawn_process(context, _spawn_holder, str(self.path), writer)
        writer.close()
        pipes, contenders, events = [], [], []
        try:
            self.assertEqual(self._receive(reader), "acquired")
            for _ in range(2):
                contending = context.Event()
                result_reader, result_writer = context.Pipe(duplex=False)
                self.addCleanup(result_reader.close)
                self.addCleanup(result_writer.close)
                contenders.append(self._spawn_process(
                    context, _spawn_contender, str(self.path), str(self.root / "critical"),
                    contending, entered, leave, result_writer,
                ))
                result_writer.close()
                pipes.append(result_reader)
                events.append(contending)
            self.assertTrue(all(event.wait(10) for event in events))
            holder.kill()
            holder.join(timeout=5)
            self.assertFalse(holder.is_alive())
            self.assertTrue(entered.wait(10))
            leave.set()
            results = [self._receive(pipe) for pipe in pipes]
            self.assertEqual([result["status"] for result in results].count("abandoned"), 1)
            self.assertEqual([result["status"] for result in results].count("acquired"), 1)
            self.assertTrue(all(result["overlap"] == 1 for result in results))
            self.assertTrue(all(result["release"] == "released" for result in results))
            for contender in contenders:
                contender.join(timeout=10)
                self.assertFalse(contender.is_alive())
                self.assertEqual(contender.exitcode, 0)
        finally:
            leave.set()

    def test_spawn_waiter_rechecks_file_created_during_initial_wait(self):
        self.ledger()
        waiter_code = r'''
import json, sys
from pathlib import Path
from benchmark.multivariate_time_series.temporal.ledger_lock import FileTestLedgerLock
lock = FileTestLedgerLock(
    Path(sys.argv[1]),
    before_open_signal=Path(sys.argv[2]),
    before_open_release=Path(sys.argv[3]),
)
result = lock.acquire(timeout=10)
Path(sys.argv[4]).write_text(json.dumps({"status": result.status.value}), encoding="utf-8")
if result.status.value in ("acquired", "abandoned"):
    lock.release()
'''
        holder_code = r'''
import os, sys, time
from pathlib import Path
from benchmark.multivariate_time_series.temporal.ledger_lock import FileTestLedgerLock
lock = FileTestLedgerLock(Path(sys.argv[1]))
result = lock.acquire(timeout=10)
Path(sys.argv[2]).write_text(result.status.value, encoding="utf-8")
while not Path(sys.argv[3]).exists():
    time.sleep(0.01)
os._exit(0)
'''
        waiter_gate = self.root / "race-waiter-gate"
        waiter_release = self.root / "race-waiter-release"
        waiter_result = self.root / "race-waiter-result"
        holder_ready = self.root / "race-holder-ready"
        holder_stop = self.root / "race-holder-stop"
        waiter = self._child(
            waiter_code, self.path, waiter_gate, waiter_release, waiter_result,
        )
        holder = None
        try:
            self.assertTrue(self._wait_file(waiter_gate))
            holder = self._child(holder_code, self.path, holder_ready, holder_stop)
            self.assertTrue(self._wait_file(holder_ready))
            waiter_release.write_text("go", encoding="utf-8")
            holder.kill()
            self._wait_child(holder)
            holder = None
            self.assertTrue(self._wait_file(waiter_result))
            result = json.loads(waiter_result.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "abandoned")
        finally:
            waiter_release.write_text("go", encoding="utf-8")
            if holder is not None:
                holder.kill()
                self._wait_child(holder)
            self._wait_child(waiter)

    def test_spawn_incomplete_owner_metadata_fails_closed_after_process_exit(self):
        holder_code = r'''
import os, sys, time
from pathlib import Path
from benchmark.multivariate_time_series.temporal.ledger_lock import FileTestLedgerLock
lock = FileTestLedgerLock(Path(sys.argv[1]), publish_owner=False)
result = lock.acquire(timeout=10)
Path(sys.argv[2]).write_text(result.status.value, encoding="utf-8")
while not Path(sys.argv[3]).exists(): time.sleep(0.01)
os._exit(0)
'''
        holder_ready = self.root / "holder-ready"
        holder_stop = self.root / "holder-stop"
        holder = self._child(holder_code, self.path, holder_ready, holder_stop)
        try:
            self.assertTrue(self._wait_file(holder_ready))
            holder_stop.write_text("stop", encoding="utf-8")
            self._wait_child(holder)
            recovered = FileTestLedgerLock(self.path)
            result = recovered.acquire(timeout=2)
            self.assertEqual(result.status, AcquireStatus.UNKNOWN)
            self.assertTrue(self.lock_path.exists())
        finally:
            holder_stop.write_text("stop", encoding="utf-8")
            self._wait_child(holder)

    def test_spawn_waiter_times_out_while_live_holder_remains(self):
        holder_code = r'''
import os, sys, time
from pathlib import Path
from benchmark.multivariate_time_series.temporal.ledger_lock import FileTestLedgerLock
lock = FileTestLedgerLock(Path(sys.argv[1]))
result = lock.acquire(timeout=10)
Path(sys.argv[2]).write_text(result.status.value, encoding="utf-8")
while not Path(sys.argv[3]).exists(): time.sleep(0.01)
os._exit(0)
'''
        holder_ready = self.root / "holder-ready"
        holder_stop = self.root / "holder-stop"
        holder = self._child(holder_code, self.path, holder_ready, holder_stop)
        try:
            self.assertTrue(self._wait_file(holder_ready))
            waiter_code = r'''
import json, sys
from pathlib import Path
from benchmark.multivariate_time_series.temporal.ledger_lock import FileTestLedgerLock
result = FileTestLedgerLock(Path(sys.argv[1])).acquire(timeout=0.2)
Path(sys.argv[2]).write_text(json.dumps({"status": result.status.value}), encoding="utf-8")
'''
            result_path = self.root / "timeout-result"
            waiter = self._child(waiter_code, self.path, result_path)
            self._wait_child(waiter)
            self.assertEqual(json.loads(result_path.read_text(encoding="utf-8"))["status"], "timeout")
            self.assertTrue(self.lock_path.exists())
        finally:
            holder_stop.write_text("stop", encoding="utf-8")
            self._wait_child(holder)

    def test_release_unknown_owner_does_not_delete_other_lock(self):
        first = FileTestLedgerLock(self.path)
        second = FileTestLedgerLock(self.path)
        self.assertEqual(first.acquire(timeout=1).status, AcquireStatus.ACQUIRED)
        self.assertEqual(second.release().status, ReleaseStatus.UNKNOWN)
        self.assertTrue(self.lock_path.exists())
        self.assertEqual(first.release().status, ReleaseStatus.RELEASED)


if __name__ == "__main__":
    unittest.main()
