"""Exercise Ledger writes with an injected mutex facade and disposable files."""

import json
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from benchmark.multivariate_time_series.temporal import resources
from benchmark.multivariate_time_series.temporal.windows_mutex_lock import (
    CallFailed,
    CreateOpened,
    WaitNotOwned,
    WindowsMutexLedgerLock,
)
from benchmark.multivariate_time_series.tests.test_windows_mutex_lock import FakeMutexApi


class WindowsMutexLedgerIntegrationTests(unittest.TestCase):
    def setUp(self):
        worktree = Path(__file__).resolve().parents[3]
        directory = worktree / f".mutex-ledger-test-{uuid4().hex}"
        directory.mkdir()
        self.addCleanup(self.remove_fixture, directory)
        self.path = directory / "ledger.json"
        self.path.write_text(
            json.dumps({
                "version": 1,
                "batch_id": "mutex-integration",
                "ledger_id": "temporary-ledger",
                "entries": [],
            }),
            encoding="utf-8",
        )
        self.api = FakeMutexApi()
        self.lock = WindowsMutexLedgerLock(
            self.path, mutex_name="integration-fake", api=self.api, security_verifier=self.api
        )

        original_load = resources.Ledger._load

        def observe_constructor_load(ledger, **kwargs):
            self.api.calls.append(("constructor_load", kwargs.get("binding")))
            return original_load(ledger, **kwargs)

        with patch.object(resources.Ledger, "_load", observe_constructor_load):
            self.ledger = resources.Ledger(
                self.path, batch_id="mutex-integration", write_lock=self.lock, lock_timeout=0.125
            )
        self.assertEqual(self.api.calls, [("constructor_load", None)])
        self.api.calls.clear()

    @staticmethod
    def remove_fixture(directory):
        for path in directory.iterdir():
            path.unlink()
        directory.rmdir()

    def observe_transaction(self):
        stack = self.enterContext(ExitStack())

        def trace(target, method, event):
            original = getattr(target, method)

            def observed(*args, **kwargs):
                result = original(*args, **kwargs)
                self.api.calls.append((event,))
                return result

            stack.enter_context(patch.object(target, method, observed))

        trace(self.lock, "acquire", "acquire_returned")
        trace(self.ledger, "_load", "transaction_load")
        trace(self.ledger, "_validated_entries", "entries_validated")
        trace(self.ledger, "_parse_json", "json_validated")
        original_replace = resources.os.replace

        def observe_publish(source, destination):
            self.assertEqual(destination, self.path)
            self.assertEqual(source.parent, self.path.parent)
            original_replace(source, destination)
            self.api.calls.append(("published",))

        stack.enter_context(patch.object(resources.os, "replace", observe_publish))

    def record(self, execution_id="run-1"):
        return self.ledger.record(execution_id=execution_id, run_id="test-run", seconds=3.0)

    def debit(self):
        return self.ledger.register_debit(debit_id="debit-1", seconds=2.0, reason="test debit")

    def assert_trace(self, *stages):
        self.assertEqual([call[0] for call in self.api.calls], list(stages))
        for event, *arguments in self.api.calls:
            if event in ("owns", "security", "wait", "release", "close"):
                self.assertIs(arguments[0], self.api.handle)
            if event == "wait":
                self.assertEqual(arguments[1], 125)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def assert_write_trace(self):
        self.assert_trace(
            "create", "owns", "security", "wait", "acquire_returned",
            "json_validated", "transaction_load", "entries_validated",
            "json_validated", "published", "release", "close",
        )

    def test_record_and_register_debit_publish_during_owned_intervals(self):
        self.observe_transaction()
        self.assertEqual(self.record()["execution_id"], "run-1")
        self.assert_write_trace()

        first_handle = self.api.handle
        self.assertNotIn(id(first_handle), self.api._registered)
        self.api.calls.clear()
        self.api.handle = self.api._issue_handle(object())
        self.api.results["create"] = CreateOpened(self.api.handle)

        self.assertEqual(self.debit()["debit_id"], "debit-1")
        self.assertIsNot(self.api.handle, first_handle)
        self.assert_write_trace()
        self.assertNotIn(id(self.api.handle), self.api._registered)

        entries = json.loads(self.path.read_bytes())["entries"]
        self.assertEqual(
            [(entry["execution_id"], entry["kind"], entry["seconds"]) for entry in entries],
            [("run-1", "measured", 3.0), ("debit-1", "budget-debit", 2.0)],
        )

    def assert_wait_rejects_write(self, wait_code, status, write):
        self.api.results["wait"] = WaitNotOwned(wait_code)
        before = self.path.read_bytes()
        self.observe_transaction()

        with self.assertRaisesRegex(resources.ResourceError, f"acquisition failed: {status}:"):
            write()

        self.assert_trace("create", "owns", "security", "wait", "close", "acquire_returned")
        self.assertNotIn(id(self.api.handle), self.api._registered)
        self.assertEqual(self.path.read_bytes(), before)

    def test_timeout_closes_without_reloading_or_publishing_record(self):
        self.assert_wait_rejects_write(0x102, "timeout", self.record)

    def test_wait_failure_closes_without_reloading_or_publishing_debit(self):
        self.assert_wait_rejects_write(0xFFFFFFFF, "wait_failed", self.debit)

    def test_release_failure_preserves_publication_and_refuses_further_access(self):
        self.api.results["release"] = CallFailed("injected release failure")
        self.observe_transaction()

        with self.assertRaisesRegex(resources.ResourceError, "transaction outcome is uncertain"):
            self.record()

        self.assert_write_trace()
        self.assertNotIn(id(self.api.handle), self.api._registered)
        published = self.path.read_bytes()
        entries = json.loads(published)["entries"]
        self.assertEqual([entry["execution_id"] for entry in entries], ["run-1"])
        self.assertEqual(entries[0]["seconds"], 3.0)

        self.api.calls.clear()
        with self.assertRaisesRegex(resources.ResourceError, "state is uncertain; query refused"):
            self.ledger.active_seconds()
        self.assert_trace()
        for write in (lambda: self.record("run-2"), self.debit):
            with self.assertRaisesRegex(resources.ResourceError, "acquisition failed: wait_failed: reuse_blocked"):
                write()
        self.assert_trace("acquire_returned", "acquire_returned")
        self.assertEqual(self.path.read_bytes(), published)
