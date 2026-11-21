"""Serial debit API checks using only disposable, isolated version-1 ledgers.

These tests do not enable formal accounting or establish concurrent safety.
Run this module alone with the standard-library unittest runner.
"""

from __future__ import annotations

import copy
import json
import unittest
import uuid
from pathlib import Path
from unittest import mock

from benchmark.multivariate_time_series.temporal import protocol, resources
from benchmark.multivariate_time_series.temporal.ledger_lock import NoopLedgerWriteLock

_LedgerClass = resources.Ledger


def _test_ledger(*args, **kwargs):
    kwargs["write_lock"] = NoopLedgerWriteLock()
    return _LedgerClass(*args, **kwargs)


class DebitApiTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[3]
        token = uuid.uuid4().hex
        self.path = self.root / f".p02-t006-debit-api-{token}-ledger.json"
        self._created = {self.path, self.path.with_suffix(self.path.suffix + ".tmp")}
        self.addCleanup(self._cleanup_files)

    def _cleanup_files(self):
        paths = set(self._created)
        for path in self._created:
            paths.update(path.parent.glob(f".{path.name}.ledger-write-*.tmp"))
        for path in paths:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def ledger(self, name="ledger"):
        if name == "ledger":
            path = self.path
        else:
            path = self.root / f".p02-t006-debit-api-{uuid.uuid4().hex}-{name}.json"
            self._created.add(path)
            self._created.add(path.with_suffix(path.suffix + ".tmp"))
        ledger = _test_ledger(path, batch_id="isolated-test")
        ledger.record(execution_id="initial", run_id="test", seconds=2)
        return ledger

    def write_payload(self, path, payload):
        path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8", errors="surrogatepass",
        )

    def debit(self, ledger, **changes):
        arguments = dict(debit_id="debit-1", seconds=7, reason="approved test bound")
        arguments.update(changes)
        return ledger.register_debit(**arguments)

    def test_first_record_preserves_constructor_identity(self):
        ledger = _test_ledger(self.path, batch_id="isolated-test")
        identity = ledger.payload["ledger_id"]
        self.assertFalse(self.path.exists())
        with mock.patch.object(resources.uuid, "uuid4", side_effect=AssertionError):
            ledger.record(execution_id="first", run_id="test", seconds=1)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["ledger_id"], identity)
        self.assertEqual(saved["version"], 1)

    def test_unpersisted_empty_ledger_remains_queryable(self):
        ledger = _test_ledger(self.path, batch_id="isolated-test")
        identity = ledger.payload["ledger_id"]
        self.assertFalse(self.path.exists())
        self.assertEqual(ledger.active_seconds(), 0)
        self.assertEqual(ledger.estimated_seconds(), 0)
        self.assertEqual(ledger.debited_seconds(), 0)
        self.assertEqual(ledger.effective_used_seconds(), 0)
        self.assertEqual(ledger.remaining_seconds(), protocol.BATCH_SECONDS)
        self.assertEqual(ledger.remaining_effective_seconds(), protocol.BATCH_SECONDS)
        self.assertEqual(ledger.payload_view()["entries"], 0)
        self.assertEqual(ledger.payload["ledger_id"], identity)
        self.assertFalse(self.path.exists())

    def test_debit_requires_existing_ledger_without_creating_history(self):
        ledger = _test_ledger(self.path, batch_id="isolated-test")
        identity = ledger.payload["ledger_id"]
        with self.assertRaises(resources.ResourceError):
            self.debit(ledger)
        self.assertFalse(self.path.exists())
        ledger.record(execution_id="first", run_id="test", seconds=0)
        self.assertEqual(ledger.payload["ledger_id"], identity)
        self.debit(ledger)

    def test_registered_fields_and_verbatim_identity_and_reason(self):
        ledger = self.ledger()
        entry = self.debit(ledger, debit_id=" debit-1 ", reason="  approved reason  ")
        self.assertEqual(entry["execution_id"], " debit-1 ")
        self.assertEqual(entry["debit_id"], " debit-1 ")
        self.assertEqual(entry["run_id"], " debit-1 ")
        self.assertEqual(entry["reason"], "  approved reason  ")
        self.assertEqual(entry["kind"], "budget-debit")
        self.assertEqual(entry["status"], "registered")
        self.assertIsInstance(entry["seconds"], float)
        self.assertEqual(entry["seconds"], 7.0)
        self.assertTrue(entry["recorded"])
        self.assertEqual(ledger.payload["updated"], entry["recorded"])
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["entries"][-1], entry)

    def test_identical_debit_returns_original_without_writing_or_timestamping(self):
        ledger = self.ledger()
        original = self.debit(ledger)
        before = self.path.read_bytes()
        modified = self.path.stat().st_mtime_ns
        with mock.patch.object(ledger, "_write", side_effect=AssertionError), \
                mock.patch.object(resources, "iso_now", side_effect=AssertionError):
            repeated = self.debit(ledger, seconds=7.0)
        self.assertEqual(repeated, original)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.path.stat().st_mtime_ns, modified)

    def test_idempotent_lookup_reloads_intervening_writes(self):
        ledger = self.ledger()
        original = self.debit(ledger)
        other = _test_ledger(self.path, batch_id="isolated-test")
        other.record(execution_id="later", run_id="test", seconds=3)
        before = self.path.read_bytes()
        self.assertEqual(self.debit(ledger), original)
        self.assertIn("later", {entry["execution_id"] for entry in ledger.payload["entries"]})
        self.assertEqual(self.path.read_bytes(), before)

    def test_conflicting_amount_or_reason_is_refused(self):
        ledger = self.ledger()
        self.debit(ledger)
        before = self.path.read_bytes()
        for changes in ({"seconds": 8}, {"reason": "different"},
                        {"reason": "approved test bound "}):
            with self.subTest(changes=changes):
                with self.assertRaises(resources.ResourceError):
                    self.debit(ledger, **changes)
                self.assertEqual(self.path.read_bytes(), before)

    def test_debit_cannot_reuse_any_ordinary_execution_identity(self):
        for kind in ("measured", "estimated", "replayed"):
            with self.subTest(kind=kind):
                ledger = self.ledger(kind)
                ledger.record(execution_id="debit-1", run_id="test", seconds=3, kind=kind)
                before = ledger.path.read_bytes()
                with self.assertRaises(resources.ResourceError):
                    self.debit(ledger)
                self.assertEqual(ledger.path.read_bytes(), before)

    def test_record_cannot_replace_debit(self):
        ledger = self.ledger()
        self.debit(ledger)
        before = self.path.read_bytes()
        for kind in ("measured", "estimated", "replayed"):
            with self.subTest(kind=kind):
                with self.assertRaises(resources.ResourceError):
                    ledger.record(execution_id="debit-1", run_id="other", seconds=4, kind=kind)
                self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_debit_inputs_do_not_write(self):
        ledger = self.ledger()
        before = self.path.read_bytes()
        invalid = [
            {"debit_id": value} for value in (None, 1, "", " \t")
        ] + [
            {"reason": value} for value in (None, 1, "", " \t")
        ] + [
            {"seconds": value} for value in
            (None, True, False, "7", 0, -1, float("nan"), float("inf"),
             float("-inf"), 10 ** 400)
        ]
        for index, changes in enumerate(invalid):
            with self.subTest(case=index):
                with self.assertRaises(resources.ResourceError):
                    self.debit(ledger, **changes)
                self.assertEqual(self.path.read_bytes(), before)

    def test_queries_keep_active_estimated_debit_and_effective_separate(self):
        ledger = self.ledger()
        ledger.record(execution_id="measured", run_id="test", seconds=10)
        ledger.record(execution_id="failed", run_id="test", seconds=5, status="failed")
        ledger.record(execution_id="replay", run_id="test", seconds=2, kind="replayed")
        ledger.record(execution_id="estimate", run_id="test", seconds=100, kind="estimated")
        self.debit(ledger)
        self.assertEqual(ledger.active_seconds(), 19)
        self.assertEqual(ledger.estimated_seconds(), 100)
        self.assertEqual(ledger.debited_seconds(), 7)
        self.assertEqual(ledger.effective_used_seconds(), 26)
        self.assertEqual(ledger.remaining_seconds(), protocol.BATCH_SECONDS - 19)
        self.assertEqual(ledger.remaining_effective_seconds(), protocol.BATCH_SECONDS - 26)
        self.assertEqual(ledger.remaining_seconds(20), 1)
        self.assertEqual(ledger.remaining_effective_seconds(20), 0)
        self.assertEqual(ledger.remaining_effective_seconds(30), 4)
        self.assertEqual(set(ledger.payload_view()), {
            "version", "batch_id", "path", "ledger_id", "active_seconds",
            "estimated_seconds", "entries",
        })

    def test_queries_use_current_persisted_snapshot(self):
        ledger = self.ledger()
        stale = _test_ledger(self.path, batch_id="isolated-test")
        self.debit(ledger)
        self.assertEqual(stale.debited_seconds(), 7)
        self.assertEqual(stale.effective_used_seconds(), 9)
        current = _test_ledger(self.path, batch_id="isolated-test")
        self.assertEqual(current.debited_seconds(), 7)

    def test_composite_queries_read_and_validate_one_snapshot(self):
        ledger = self.ledger()
        self.debit(ledger)
        for operation in (
            "effective_used_seconds", "remaining_effective_seconds", "payload_view"
        ):
            with self.subTest(operation=operation):
                original_load = ledger._load
                original_validate = ledger._validated_entries
                with mock.patch.object(ledger, "_load", wraps=original_load) as load, \
                        mock.patch.object(
                            ledger, "_validated_entries", wraps=original_validate
                        ) as validate:
                    getattr(ledger, operation)()
                self.assertEqual(load.call_count, 1)
                self.assertEqual(validate.call_count, 1)

    def test_all_queries_fail_after_write_result_becomes_uncertain(self):
        operations = (
            "active_seconds", "estimated_seconds", "debited_seconds",
            "effective_used_seconds", "remaining_seconds",
            "remaining_effective_seconds", "payload_view",
        )
        for writer in ("record", "debit"):
            with self.subTest(writer=writer):
                ledger = self.ledger(writer)
                real_replace = resources.os.replace

                def uncertain_replace(source, destination):
                    real_replace(source, destination)
                    raise OSError("simulated unknown commit result")

                with mock.patch.object(resources.os, "replace", side_effect=uncertain_replace):
                    with self.assertRaises(OSError):
                        if writer == "record":
                            ledger.record(
                                execution_id="uncertain", run_id="test", seconds=1
                            )
                        else:
                            self.debit(ledger)
                before = ledger.path.read_bytes()
                for operation in operations:
                    with self.subTest(writer=writer, operation=operation):
                        with self.assertRaises(resources.ResourceError):
                            getattr(ledger, operation)()
                self.assertEqual(ledger.path.read_bytes(), before)

    def test_all_queries_reject_disappeared_or_replaced_ledger(self):
        operations = (
            "active_seconds", "estimated_seconds", "debited_seconds",
            "effective_used_seconds", "remaining_seconds",
            "remaining_effective_seconds", "payload_view",
        )
        for operation in operations:
            for corruption in ("missing", "ledger_id", "missing_ledger_id",
                               "batch_id", "missing_batch_id", "json"):
                with self.subTest(operation=operation, corruption=corruption):
                    ledger = self.ledger(f"{operation}-{corruption}")
                    if corruption == "missing":
                        ledger.path.unlink()
                    elif corruption == "json":
                        ledger.path.write_text("{", encoding="utf-8")
                    elif corruption in ("ledger_id", "batch_id"):
                        payload = copy.deepcopy(ledger.payload)
                        payload[corruption] = "replacement"
                        self.write_payload(ledger.path, payload)
                    else:
                        payload = copy.deepcopy(ledger.payload)
                        payload.pop("ledger_id" if corruption == "missing_ledger_id" else "batch_id")
                        self.write_payload(ledger.path, payload)
                    before = None if not ledger.path.exists() else ledger.path.read_bytes()
                    with self.assertRaises(resources.ResourceError):
                        getattr(ledger, operation)()
                    self.assertEqual(
                        None if not ledger.path.exists() else ledger.path.read_bytes(), before
                    )

    def test_queries_reject_malformed_or_unknown_ordinary_entries(self):
        corruptions = {
            "nondict": lambda entry: None,
            "missing_execution_id": lambda entry: entry.pop("execution_id"),
            "missing_run_id": lambda entry: entry.pop("run_id"),
            "missing_kind": lambda entry: entry.pop("kind"),
            "missing_seconds": lambda entry: entry.pop("seconds"),
            "missing_status": lambda entry: entry.pop("status"),
            "missing_recorded": lambda entry: entry.pop("recorded"),
            "missing_note": lambda entry: entry.pop("note"),
            "unknown_kind": lambda entry: entry.update(kind="mystery"),
            "nonnumeric_seconds": lambda entry: entry.update(seconds="broken"),
            "negative_seconds": lambda entry: entry.update(seconds=-1),
            "nan_seconds": lambda entry: entry.update(seconds=float("nan")),
            "negative_infinite_seconds": lambda entry: entry.update(seconds=float("-inf")),
        }
        operations = (
            "active_seconds", "estimated_seconds", "debited_seconds",
            "effective_used_seconds", "remaining_seconds",
            "remaining_effective_seconds", "payload_view",
        )
        for operation in operations:
            for name, corrupt in corruptions.items():
                with self.subTest(operation=operation, corruption=name):
                    ledger = self.ledger(f"{operation}-{name}")
                    payload = copy.deepcopy(ledger.payload)
                    entry = payload["entries"][0]
                    if name == "nondict":
                        payload["entries"][0] = 1
                    else:
                        corrupt(entry)
                    self.write_payload(ledger.path, payload)
                    before = ledger.path.read_bytes()
                    with self.assertRaises(resources.ResourceError):
                        query_ledger = _test_ledger(
                            ledger.path, batch_id="isolated-test"
                        )
                        getattr(query_ledger, operation)()
                    self.assertEqual(ledger.path.read_bytes(), before)

    def test_two_instances_reload_before_each_serial_write(self):
        first = self.ledger()
        second = _test_ledger(self.path, batch_id="isolated-test")
        first.record(execution_id="first", run_id="test", seconds=3)
        second.record(execution_id="second", run_id="test", seconds=5)
        self.debit(first)
        second.record(execution_id="third", run_id="test", seconds=11)
        first.register_debit(debit_id="debit-2", seconds=13, reason="another bound")
        saved = _test_ledger(self.path, batch_id="isolated-test")
        self.assertEqual({entry["execution_id"] for entry in saved.payload["entries"]},
                         {"initial", "first", "second", "third", "debit-1", "debit-2"})
        self.assertEqual(saved.active_seconds(), 21)
        self.assertEqual(saved.debited_seconds(), 20)

    def test_separate_unpersisted_identities_cannot_overwrite_first_creator(self):
        first = _test_ledger(self.path, batch_id="isolated-test")
        second = _test_ledger(self.path, batch_id="isolated-test")
        self.assertNotEqual(first.payload["ledger_id"], second.payload["ledger_id"])
        first.record(execution_id="first", run_id="test", seconds=1)
        before = self.path.read_bytes()
        with self.assertRaises(resources.ResourceError):
            second.record(execution_id="second", run_id="test", seconds=2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_disappeared_ledger_is_not_recreated_by_either_api(self):
        for api in ("record", "debit"):
            with self.subTest(api=api):
                ledger = self.ledger(api)
                ledger.path.unlink()
                with self.assertRaises(resources.ResourceError):
                    if api == "record":
                        ledger.record(execution_id="later", run_id="test", seconds=1)
                    else:
                        self.debit(ledger)
                self.assertFalse(ledger.path.exists())
                self.assertFalse(ledger.path.with_suffix(".json.tmp").exists())
                self.assertEqual(
                    list(ledger.path.parent.glob(f".{ledger.path.name}.ledger-write-*.tmp")), [],
                )

    def test_replaced_or_missing_identity_is_refused_by_both_apis(self):
        changes = [
            ("ledger_id", "replacement"), ("ledger_id", None), ("ledger_id", ""),
            ("batch_id", "other"), ("batch_id", None), ("batch_id", ""),
            ("version", 2), ("entries", None),
        ]
        for api in ("record", "debit"):
            for index, (key, value) in enumerate(changes):
                with self.subTest(api=api, key=key, value=value):
                    ledger = self.ledger(f"{api}-{index}")
                    payload = copy.deepcopy(ledger.payload)
                    if value is None:
                        payload.pop(key)
                    else:
                        payload[key] = value
                    self.write_payload(ledger.path, payload)
                    before = ledger.path.read_bytes()
                    with self.assertRaises(resources.ResourceError):
                        if api == "record":
                            ledger.record(execution_id="later", run_id="test", seconds=1)
                        else:
                            self.debit(ledger)
                    self.assertEqual(ledger.path.read_bytes(), before)

    def test_unreadable_or_malformed_state_fails_closed(self):
        for api in ("record", "debit"):
            for index, text in enumerate(("{", "[]", "null")):
                with self.subTest(api=api, text=text):
                    ledger = self.ledger(f"{api}-{index}")
                    ledger.path.write_text(text, encoding="utf-8")
                    with self.assertRaises(resources.ResourceError):
                        if api == "record":
                            ledger.record(execution_id="later", run_id="test", seconds=1)
                        else:
                            self.debit(ledger)
                    self.assertEqual(ledger.path.read_text(encoding="utf-8"), text)
        ledger = self.ledger("unreadable")
        before = ledger.path.read_bytes()
        with mock.patch.object(Path, "read_text", side_effect=PermissionError("test denial")):
            with self.assertRaises(resources.ResourceError):
                self.debit(ledger)
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id="later", run_id="test", seconds=1)
        self.assertEqual(ledger.path.read_bytes(), before)

    def test_query_rejects_unreadable_ledger_as_resource_error(self):
        ledger = self.ledger()
        before = ledger.path.read_bytes()
        with mock.patch.object(Path, "read_text", side_effect=PermissionError("test denial")):
            with self.assertRaises(resources.ResourceError):
                ledger.active_seconds()
        self.assertEqual(ledger.path.read_bytes(), before)

    def test_failed_first_write_does_not_allow_empty_history_retry(self):
        ledger = _test_ledger(self.path, batch_id="isolated-test")
        with mock.patch.object(resources.os, "replace", side_effect=OSError("test failure")):
            with self.assertRaises(OSError):
                ledger.record(execution_id="first", run_id="test", seconds=1)
        self.assertFalse(self.path.exists())
        residuals = list(self.path.parent.glob(f".{self.path.name}.ledger-write-*.tmp"))
        self.assertEqual(len(residuals), 1)
        self.addCleanup(lambda: self.assertTrue(all(not path.exists() for path in residuals)))
        # Run the existing cleanup first, then verify it covered the unique temp name.
        self.addCleanup(self._cleanup_files)
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id="retry", run_id="test", seconds=1)
        with self.assertRaises(resources.ResourceError):
            self.debit(ledger)
        self.assertFalse(self.path.exists())

    def test_replace_then_error_leaves_instance_closed_for_both_apis(self):
        real_replace = resources.os.replace

        def uncertain_replace(source, destination):
            real_replace(source, destination)
            raise OSError("simulated unknown commit result")

        for api in ("record", "debit"):
            with self.subTest(api=api):
                ledger = self.ledger(api)
                with mock.patch.object(resources.os, "replace", side_effect=uncertain_replace):
                    with self.assertRaises(OSError):
                        if api == "record":
                            ledger.record(execution_id="later", run_id="test", seconds=1)
                        else:
                            self.debit(ledger)
                before = ledger.path.read_bytes()
                committed = json.loads(before)
                expected_id = "later" if api == "record" else "debit-1"
                self.assertIn(expected_id, {entry["execution_id"] for entry in committed["entries"]})
                with self.assertRaises(resources.ResourceError):
                    ledger.record(execution_id="retry", run_id="test", seconds=1)
                with self.assertRaises(resources.ResourceError):
                    self.debit(ledger)
                self.assertEqual(ledger.path.read_bytes(), before)

    def test_ambiguous_debits_are_not_repaired_or_overwritten(self):
        corruptions = ("duplicate", "ordinary-collision", "debit_id", "run_id",
                       "seconds", "reason", "status", "recorded")
        for case in corruptions:
            with self.subTest(case=case):
                ledger = self.ledger(case)
                self.debit(ledger)
                payload = copy.deepcopy(ledger.payload)
                entry = payload["entries"][-1]
                if case == "duplicate":
                    payload["entries"].append(copy.deepcopy(entry))
                elif case == "ordinary-collision":
                    ordinary = copy.deepcopy(payload["entries"][0])
                    ordinary["execution_id"] = "debit-1"
                    metadata = {
                        "version": 1,
                        "value": resources.Ledger._encode_execution_id("debit-1"),
                    }
                    ordinary[resources.Ledger._EXECUTION_IDENTITY] = metadata
                    ordinary[resources.Ledger._EXECUTION_IDENTITY_DIGEST] = (
                        resources.Ledger._identity_digest(metadata)
                    )
                    payload["entries"].append(ordinary)
                else:
                    entry[case] = None
                self.write_payload(ledger.path, payload)
                before = ledger.path.read_bytes()
                invalid = _test_ledger(ledger.path, batch_id="isolated-test")
                with self.assertRaises(resources.ResourceError):
                    invalid.debited_seconds()
                with self.assertRaises(resources.ResourceError):
                    self.debit(ledger)
                another = _test_ledger(ledger.path, batch_id="isolated-test")
                with self.assertRaises(resources.ResourceError):
                    another.record(execution_id="later", run_id="test", seconds=1)
                self.assertEqual(ledger.path.read_bytes(), before)

    def test_ordinary_record_input_conversion_remains_permissive(self):
        ledger = self.ledger()
        cases = (("3.5", 3.5), (-4, 0), (True, 1), (False, 0),
                 (float("nan"), 0), ("nan", 0), (float("-inf"), 0),
                 (float("inf"), float("inf")))
        for index, (value, expected) in enumerate(cases):
            with self.subTest(case=index):
                entry = ledger.record(execution_id=f"case-{index}", run_id="",
                                      seconds=value, status="custom", note="kept")
                self.assertEqual(entry["seconds"], expected)
                self.assertEqual(entry["status"], "custom")
                self.assertEqual(entry["note"], "kept")
        ledger.record(execution_id="", run_id="", seconds=0)
        ledger.record(execution_id=["legacy"], run_id="", seconds=0)

    def test_empty_run_id_and_status_remain_queryable_and_writable(self):
        ledger = self.ledger()
        first = ledger.record(
            execution_id="empty-fields", run_id="", seconds=4, status=""
        )
        self.assertEqual(first["run_id"], "")
        self.assertEqual(first["status"], "")
        self.assertEqual(ledger.active_seconds(), 6)
        ledger.record(execution_id="next", run_id="", seconds=1, status="")
        self.assertEqual(ledger.active_seconds(), 7)

    def test_json_serializable_unhashable_execution_id_replaces_by_identity(self):
        ledger = self.ledger()
        identity = {"worker": ["run", 3], "replica": {"name": "a"}}
        first = ledger.record(
            execution_id=identity, run_id="", seconds=4, status=""
        )
        self.assertEqual(first["execution_id"], identity)
        self.assertEqual(ledger.active_seconds(), 6)
        replacement_id = {"replica": {"name": "a"}, "worker": ["run", 3]}
        second = ledger.record(
            execution_id=replacement_id, run_id="", seconds=7, status=""
        )
        self.assertEqual(second["execution_id"], replacement_id)
        self.assertEqual(ledger.active_seconds(), 9)
        matching = [
            entry for entry in ledger.payload["entries"]
            if resources.Ledger._same_execution_id(entry["execution_id"], identity)
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["seconds"], 7)

    def test_positive_infinite_seconds_are_counted_and_exhaust_balance(self):
        ledger = self.ledger()
        ledger.record(execution_id="unbounded", run_id="test", seconds=float("inf"))
        self.assertEqual(ledger.active_seconds(), float("inf"))
        self.assertEqual(ledger.effective_used_seconds(), float("inf"))
        self.assertEqual(ledger.remaining_seconds(100), 0)
        self.assertEqual(ledger.remaining_effective_seconds(100), 0)

    def test_ordinary_record_exceptions_are_not_wrapped_or_reordered(self):
        ledger = self.ledger()
        before = self.path.read_bytes()
        sentinel = RuntimeError("original conversion exception")

        class BadFloat:
            def __float__(self):
                raise sentinel

        with mock.patch.object(ledger, "_reload_for_write", side_effect=AssertionError):
            with self.assertRaises(resources.ResourceError):
                ledger.record(execution_id="x", run_id="test", seconds=BadFloat(), kind="bad")
            with self.assertRaises(ValueError):
                ledger.record(execution_id="x", run_id="test", seconds="bad")
            with self.assertRaises(TypeError):
                ledger.record(execution_id="x", run_id="test", seconds=None)
            with self.assertRaises(RuntimeError) as caught:
                ledger.record(execution_id="x", run_id="test", seconds=BadFloat())
            self.assertIs(caught.exception, sentinel)
        self.assertEqual(self.path.read_bytes(), before)

    def test_ordinary_same_id_replaces_instead_of_accumulating(self):
        ledger = self.ledger()
        ledger.record(execution_id="initial", run_id="new", seconds="8", status="running")
        result = ledger.record(execution_id="initial", run_id="new", seconds=3,
                               status="failed", note="final")
        self.assertEqual(len(ledger.payload["entries"]), 1)
        self.assertEqual({key: ledger.payload["entries"][0][key] for key in result}, result)
        self.assertEqual(ledger.active_seconds(), 3)
        self.assertEqual(result["status"], "failed")

    def test_existing_ordinary_duplicate_ids_keep_head_replacement_semantics(self):
        ledger = self.ledger()
        payload = copy.deepcopy(ledger.payload)
        payload["entries"].append(copy.deepcopy(payload["entries"][0]))
        self.write_payload(self.path, payload)
        result = ledger.record(execution_id="initial", run_id="test", seconds=5)
        self.assertEqual(len(ledger.payload["entries"]), 1)
        self.assertEqual({key: ledger.payload["entries"][0][key] for key in result}, result)
        self.assertEqual(ledger.active_seconds(), 5)

    def test_tuple_and_list_execution_ids_are_distinct(self):
        ledger = self.ledger()
        tuple_id = ("job", 1)
        list_id = ["job", 1]
        tuple_entry = ledger.record(execution_id=tuple_id, run_id="test", seconds=3)
        list_entry = ledger.record(execution_id=list_id, run_id="test", seconds=5)
        self.assertIsInstance(tuple_entry["execution_id"], tuple)
        self.assertIsInstance(list_entry["execution_id"], list)
        self.assertEqual(ledger.active_seconds(), 10)
        self.assertEqual(len(ledger.payload["entries"]), 3)
        self.assertEqual(ledger.payload["entries"][1]["execution_id"], tuple_id)
        self.assertEqual(ledger.payload["entries"][2]["execution_id"], list_id)

    def test_reopened_ledger_retains_tuple_list_identity_and_replacement(self):
        ledger = self.ledger()
        ledger.record(execution_id=("job", 1), run_id="test", seconds=3)
        ledger.record(execution_id=["job", 1], run_id="test", seconds=5)
        reopened = _test_ledger(self.path, batch_id="isolated-test")
        tuple_entry, list_entry = reopened.payload["entries"][1:]
        self.assertEqual(tuple_entry["execution_id"], ("job", 1))
        self.assertEqual(list_entry["execution_id"], ["job", 1])
        reopened.record(execution_id=("job", 1), run_id="test", seconds=7)
        self.assertEqual(reopened.active_seconds(), 14)
        reopened.record(execution_id=["job", 1], run_id="test", seconds=11)
        self.assertEqual(reopened.active_seconds(), 20)
        self.assertEqual(len(reopened.payload["entries"]), 3)
        again = _test_ledger(self.path, batch_id="isolated-test")
        self.assertEqual(again.payload["entries"][1]["execution_id"], ("job", 1))
        self.assertEqual(again.payload["entries"][2]["execution_id"], ["job", 1])

    def test_unhashable_and_nested_python_ids_replace_after_reopen(self):
        identities = (
            ["job", 1],
            {"job": [1, {"role": "a"}]},
            {1: ("job", [2, 3])},
            {2: "job", 10: ("nested", {3: "a", 11: "b"})},
            ("job", {"nested": (1, 2)}),
            None,
        )
        for index, identity in enumerate(identities):
            with self.subTest(identity=identity):
                ledger = self.ledger(f"typed-{index}")
                ledger.record(execution_id=identity, run_id="test", seconds=3)
                reopened = _test_ledger(ledger.path, batch_id="isolated-test")
                self.assertEqual(reopened.payload["entries"][-1]["execution_id"], identity)
                reopened.record(execution_id=copy.deepcopy(identity), run_id="test", seconds=7)
                self.assertEqual(reopened.active_seconds(), 9)
                self.assertEqual(len(reopened.payload["entries"]), 2)

    def test_internal_identity_preserves_python_scalar_and_dictionary_equality(self):
        ledger = self.ledger()
        ledger.record(execution_id=True, run_id="test", seconds=3)
        ledger.record(execution_id=1.0, run_id="test", seconds=5)
        self.assertEqual(ledger.active_seconds(), 7)
        self.assertEqual(len(ledger.payload["entries"]), 2)
        ledger.record(execution_id={1: "job"}, run_id="test", seconds=7)
        ledger.record(execution_id={"1": "job"}, run_id="test", seconds=11)
        self.assertEqual(ledger.active_seconds(), 25)
        self.assertEqual(len(ledger.payload["entries"]), 4)
        self.assertEqual(ledger.payload["entries"][-2]["execution_id"], {1: "job"})
        self.assertEqual(ledger.payload["entries"][-1]["execution_id"], {"1": "job"})

    def test_target_unhashable_duplicate_ids_are_removed_together(self):
        for index, identity in enumerate((["job", 1], {"job": (1, 2)}, ("job", 1))):
            with self.subTest(identity=identity):
                ledger = self.ledger(f"duplicates-{index}")
                ledger.record(execution_id=identity, run_id="test", seconds=3)
                payload = copy.deepcopy(ledger.payload)
                payload["entries"].append(copy.deepcopy(payload["entries"][-1]))
                self.write_payload(ledger.path, payload)
                reopened = _test_ledger(ledger.path, batch_id="isolated-test")
                reopened.record(execution_id=identity, run_id="test", seconds=7)
                self.assertEqual(reopened.active_seconds(), 9)
                self.assertEqual(len(reopened.payload["entries"]), 2)

    def test_unrelated_duplicate_ids_block_record_and_debit_writes(self):
        for operation in ("record", "new-debit", "repeat-debit"):
            with self.subTest(operation=operation):
                ledger = self.ledger(operation)
                original_debit = self.debit(ledger)
                payload = copy.deepcopy(ledger.payload)
                payload["entries"].append(copy.deepcopy(payload["entries"][0]))
                self.write_payload(ledger.path, payload)
                before = ledger.path.read_bytes()
                with mock.patch.object(ledger, "_write", side_effect=AssertionError):
                    with self.assertRaises(resources.ResourceError):
                        if operation == "record":
                            ledger.record(execution_id="b", run_id="test", seconds=1)
                        elif operation == "new-debit":
                            self.debit(ledger, debit_id="another-debit")
                        else:
                            ledger.register_debit(
                                debit_id=original_debit["debit_id"],
                                seconds=original_debit["seconds"],
                                reason=original_debit["reason"],
                            )
                self.assertEqual(ledger.path.read_bytes(), before)

    def test_target_duplicates_do_not_exempt_other_duplicate_identities(self):
        ledger = self.ledger()
        ledger.record(execution_id=["b"], run_id="test", seconds=3)
        payload = copy.deepcopy(ledger.payload)
        payload["entries"].extend(copy.deepcopy(payload["entries"]))
        self.write_payload(self.path, payload)
        before = self.path.read_bytes()
        with self.assertRaises(resources.ResourceError):
            ledger.record(execution_id=["b"], run_id="test", seconds=7)
        self.assertEqual(self.path.read_bytes(), before)

    def test_empty_fields_and_infinite_seconds_remain_replaceable_after_query(self):
        ledger = self.ledger()
        identity = ("job", 1)
        ledger.record(execution_id=identity, run_id="", status="", seconds=float("inf"))
        self.assertEqual(ledger.active_seconds(), float("inf"))
        self.assertEqual(ledger.remaining_seconds(), 0)
        ledger.record(execution_id=identity, run_id="", status="", seconds=3)
        self.assertEqual(ledger.active_seconds(), 5)
        self.assertEqual(len(ledger.payload["entries"]), 2)
        reopened = _test_ledger(self.path, batch_id="isolated-test")
        reopened.record(execution_id=identity, run_id="", status="", seconds=7)
        self.assertEqual(reopened.active_seconds(), 9)

    def test_malformed_internal_execution_identity_is_rejected(self):
        for index, corruption in enumerate(("version", "encoding", "mismatch", "kind")):
            with self.subTest(corruption=corruption):
                ledger = self.ledger(f"bad-identity-{index}")
                ledger.record(execution_id=("job", 1), run_id="test", seconds=3)
                payload = copy.deepcopy(ledger.payload)
                entry = payload["entries"][-1]
                metadata = entry[resources.Ledger._EXECUTION_IDENTITY]
                if corruption == "version":
                    metadata["version"] = True
                elif corruption == "encoding":
                    metadata["value"] = ["tuple", None]
                elif corruption == "mismatch":
                    metadata["value"] = ["scalar", "other-id"]
                else:
                    entry["kind"] = []
                self.write_payload(ledger.path, payload)
                before = ledger.path.read_bytes()
                with self.assertRaises(resources.ResourceError):
                    ledger.active_seconds()
                with self.assertRaises(resources.ResourceError):
                    ledger.record(execution_id="b", run_id="test", seconds=1)
                self.assertEqual(ledger.path.read_bytes(), before)

    def test_legacy_or_mixed_entries_without_identity_metadata_are_rejected(self):
        identity_field = resources.Ledger._EXECUTION_IDENTITY
        digest_field = resources.Ledger._EXECUTION_IDENTITY_DIGEST
        for style in ("legacy", "mixed"):
            for operation in ("query", "record", "debit"):
                with self.subTest(style=style, operation=operation):
                    ledger = self.ledger(f"{style}-{operation}")
                    ledger.record(execution_id=("job", 1), run_id="test", seconds=3)
                    payload = json.loads(ledger.path.read_text(encoding="utf-8"))
                    entries = payload["entries"] if style == "legacy" else payload["entries"][-1:]
                    for entry in entries:
                        entry.pop(identity_field)
                        entry.pop(digest_field)
                    self.write_payload(ledger.path, payload)
                    before = ledger.path.read_bytes()
                    with mock.patch.object(ledger, "_write", side_effect=AssertionError):
                        with self.assertRaises(resources.ResourceError):
                            if operation == "query":
                                ledger.active_seconds()
                            elif operation == "record":
                                # Even the target ID cannot repair unknown legacy types.
                                ledger.record(execution_id=("job", 1), run_id="test", seconds=7)
                            else:
                                self.debit(ledger)
                    with self.assertRaises(resources.ResourceError):
                        _test_ledger(ledger.path, batch_id="isolated-test")
                    self.assertEqual(ledger.path.read_bytes(), before)

    def test_single_identity_field_corruption_blocks_queries_and_writes(self):
        corruptions = (
            "missing_metadata", "missing_digest", "missing_version", "missing_value",
            "unknown_version", "unknown_tag", "bad_structure", "projection",
            "tuple_to_list", "list_to_tuple", "nested_tuple_to_list", "digest",
        )
        for corruption in corruptions:
            for operation in ("query", "record", "debit"):
                with self.subTest(corruption=corruption, operation=operation):
                    ledger = self.ledger(f"{corruption}-{operation}")
                    identity = ["job", 1] if corruption == "list_to_tuple" else ("job", (1, 2))
                    ledger.record(execution_id=identity, run_id="test", seconds=3)
                    payload = json.loads(ledger.path.read_text(encoding="utf-8"))
                    entry = payload["entries"][-1]
                    field = resources.Ledger._EXECUTION_IDENTITY
                    digest_field = resources.Ledger._EXECUTION_IDENTITY_DIGEST
                    metadata = entry[field]
                    if corruption == "missing_metadata":
                        entry.pop(field)
                    elif corruption == "missing_digest":
                        entry.pop(digest_field)
                    elif corruption == "missing_version":
                        metadata.pop("version")
                    elif corruption == "missing_value":
                        metadata.pop("value")
                    elif corruption == "unknown_version":
                        metadata["version"] = 2
                    elif corruption == "unknown_tag":
                        metadata["value"][0] = "unknown"
                    elif corruption == "bad_structure":
                        metadata["value"] = ["tuple", {}]
                    elif corruption == "projection":
                        entry["execution_id"] = ["changed"]
                    elif corruption == "tuple_to_list":
                        metadata["value"][0] = "list"
                    elif corruption == "list_to_tuple":
                        metadata["value"][0] = "tuple"
                    elif corruption == "nested_tuple_to_list":
                        metadata["value"][1][1][0] = "list"
                    else:
                        entry[digest_field] = "0" * 64
                    self.write_payload(ledger.path, payload)
                    before = ledger.path.read_bytes()
                    with mock.patch.object(ledger, "_write", side_effect=AssertionError):
                        with self.assertRaises(resources.ResourceError):
                            if operation == "query":
                                ledger.effective_used_seconds()
                            elif operation == "record":
                                ledger.record(execution_id="b", run_id="test", seconds=7)
                            else:
                                self.debit(ledger)
                    self.assertEqual(ledger.path.read_bytes(), before)

    def test_unknown_identity_tags_are_rejected_even_with_matching_digest(self):
        ledger = self.ledger()
        payload = copy.deepcopy(ledger.payload)
        metadata = payload["entries"][0][resources.Ledger._EXECUTION_IDENTITY]
        metadata["value"] = ["unknown", "initial"]
        payload["entries"][0][resources.Ledger._EXECUTION_IDENTITY_DIGEST] = (
            resources.Ledger._identity_digest(metadata)
        )
        self.write_payload(self.path, payload)
        with self.assertRaises(resources.ResourceError):
            ledger.active_seconds()

    def test_nested_nan_execution_ids_are_refused_before_writing(self):
        identities = (
            float("nan"),
            [float("nan")],
            ("job", [float("nan")]),
            {"job": {"role": float("nan")}},
            {float("nan"): "job"},
        )
        for index, identity in enumerate(identities):
            with self.subTest(case=index):
                ledger = self.ledger(f"nan-{index}")
                before = ledger.path.read_bytes()
                for attempt in range(2):
                    with self.subTest(attempt=attempt):
                        with mock.patch.object(ledger, "_write", side_effect=AssertionError):
                            with self.assertRaisesRegex(resources.ResourceError, "NaN"):
                                ledger.record(execution_id=identity, run_id="test", seconds=1)
                        self.assertEqual(ledger.path.read_bytes(), before)
                        self.assertEqual(ledger.active_seconds(), 2)
                        reopened = _test_ledger(ledger.path, batch_id="isolated-test")
                        self.assertEqual(reopened.active_seconds(), 2)
                ledger.record(execution_id="safe", run_id="test", seconds=3)
                ledger.record(execution_id="safe", run_id="test", seconds=5)
                self.assertEqual(ledger.active_seconds(), 7)

    def test_nan_id_is_refused_without_creating_a_new_ledger(self):
        ledger = _test_ledger(self.path, batch_id="isolated-test")
        with mock.patch.object(ledger, "_write", side_effect=AssertionError):
            with self.assertRaisesRegex(resources.ResourceError, "NaN"):
                ledger.record(execution_id=[float("nan")], run_id="test", seconds=1)
        self.assertFalse(self.path.exists())
        self.assertEqual(ledger.active_seconds(), 0)
        ledger.record(execution_id="safe", run_id="test", seconds=1)
        self.assertEqual(ledger.active_seconds(), 1)

    def test_record_public_return_shape_excludes_internal_identity_fields(self):
        ledger = self.ledger()
        for identity in ("job", ("job", 1), ["job", 1], {"job": 1}):
            with self.subTest(identity=identity):
                result = ledger.record(execution_id=identity, run_id="", status="", seconds=3)
                self.assertEqual(set(result), {
                    "execution_id", "run_id", "seconds", "kind", "status", "recorded", "note",
                })
                self.assertEqual(result["execution_id"], identity)
                self.assertIsNot(result, ledger.payload["entries"][-1])
                persisted = json.loads(ledger.path.read_text(encoding="utf-8"))["entries"][-1]
                self.assertIn(resources.Ledger._EXECUTION_IDENTITY, persisted)
                self.assertIn(resources.Ledger._EXECUTION_IDENTITY_DIGEST, persisted)
                self.assertEqual(ledger.active_seconds(), 2 + 3 * len(ledger.payload["entries"][1:]))

    def test_nonserializable_set_id_raises_typeerror_in_json_write(self):
        for index, identity in enumerate(({"job"}, ["job", {1}], {"job": {1}})):
            with self.subTest(case=index):
                ledger = self.ledger(f"set-{index}")
                before = ledger.path.read_bytes()
                original_write = ledger._write
                with mock.patch.object(ledger, "_write", wraps=original_write) as write:
                    with self.assertRaises(TypeError) as caught:
                        ledger.record(execution_id=identity, run_id="test", seconds=1)
                self.assertEqual(write.call_count, 1)
                # assertRaises clears the traceback; the writer's invocation
                # and the JSON encoder's message identify the failure phase.
                self.assertIn("set", str(caught.exception))
                self.assertEqual(ledger.path.read_bytes(), before)
                self.assertTrue(ledger._write_uncertain)

    def test_surrogate_pair_and_unicode_scalar_ids_stay_distinct_after_reopen(self):
        pair = "\ud83d\ude00"
        scalar = "\U0001f600"
        self.assertNotEqual(pair, scalar)
        self.assertNotEqual(
            resources.Ledger._canonical_identity({"text": pair}),
            resources.Ledger._canonical_identity({"text": scalar}),
        )
        ledger = self.ledger()
        for identity, seconds in ((pair, 3), (scalar, 5)):
            result = ledger.record(execution_id=identity, run_id="test", seconds=seconds)
            self.assertEqual(result["execution_id"], identity)
            self.assertEqual(set(result), {
                "execution_id", "run_id", "seconds", "kind", "status", "recorded", "note",
            })
        self.assertEqual(ledger.active_seconds(), 10)
        self.assertEqual(len(ledger.payload["entries"]), 3)
        digests = [
            entry[resources.Ledger._EXECUTION_IDENTITY_DIGEST]
            for entry in ledger.payload["entries"][1:]
        ]
        self.assertNotEqual(*digests)
        reopened = _test_ledger(self.path, batch_id="isolated-test")
        self.assertEqual([entry["execution_id"] for entry in reopened.payload["entries"][1:]],
                         [pair, scalar])
        self.assertEqual(reopened.active_seconds(), 10)
        reopened.record(execution_id=pair, run_id="test", seconds=7)
        self.assertEqual(reopened.active_seconds(), 14)
        reopened.record(execution_id=scalar, run_id="test", seconds=11)
        self.assertEqual(reopened.active_seconds(), 20)
        again = _test_ledger(self.path, batch_id="isolated-test")
        self.assertEqual(again.active_seconds(), 20)
        self.assertEqual([entry["execution_id"] for entry in again.payload["entries"][1:]],
                         [pair, scalar])
        public_disk_entries = json.loads(self.path.read_text(
            encoding="utf-8", errors="surrogatepass",
        ))["entries"][1:]
        self.assertEqual([entry["execution_id"] for entry in public_disk_entries],
                         [pair, scalar])

    def test_surrogate_pair_and_unicode_scalar_dictionary_keys_stay_distinct(self):
        pair_id = {"\ud83d\ude00": "job"}
        scalar_id = {"\U0001f600": "job"}
        self.assertNotEqual(pair_id, scalar_id)
        ledger = self.ledger()
        ledger.record(execution_id=pair_id, run_id="test", seconds=3)
        ledger.record(execution_id=scalar_id, run_id="test", seconds=5)
        self.assertEqual(ledger.active_seconds(), 10)
        reopened = _test_ledger(self.path, batch_id="isolated-test")
        self.assertEqual([entry["execution_id"] for entry in reopened.payload["entries"][1:]],
                         [pair_id, scalar_id])
        reopened.record(execution_id=pair_id, run_id="test", seconds=7)
        self.assertEqual(reopened.active_seconds(), 14)
        reopened.record(execution_id=scalar_id, run_id="test", seconds=11)
        self.assertEqual(reopened.active_seconds(), 20)
        again = _test_ledger(self.path, batch_id="isolated-test")
        self.assertEqual(len(again.payload["entries"]), 3)
        self.assertEqual([entry["execution_id"] for entry in again.payload["entries"][1:]],
                         [pair_id, scalar_id])
        self.assertEqual(again.active_seconds(), 20)

    def test_one_dictionary_preserves_both_keys_and_nested_codepoint_sequences(self):
        pair = "\ud83d\ude00"
        scalar = "\U0001f600"
        identity = {
            pair: ("job", [pair, scalar]),
            scalar: {"nested": {pair: 1, scalar: 2}},
        }
        ledger = self.ledger()
        result = ledger.record(execution_id=identity, run_id="test", seconds=3)
        self.assertEqual(result["execution_id"], identity)
        self.assertEqual(ledger.active_seconds(), 5)
        reopened = _test_ledger(self.path, batch_id="isolated-test")
        restored = reopened.payload["entries"][-1]["execution_id"]
        self.assertEqual(restored, identity)
        self.assertEqual(len(restored), 2)
        self.assertEqual(len(restored[scalar]["nested"]), 2)
        reopened.record(execution_id=copy.deepcopy(identity), run_id="test", seconds=7)
        self.assertEqual(reopened.active_seconds(), 9)
        self.assertEqual(len(reopened.payload["entries"]), 2)

    def test_duplicate_json_members_before_or_after_valid_values_block_all_paths(self):
        for level in ("root", "entry", "metadata", "digest", "extra", "escaped-name"):
            for bad_first in (True, False):
                for operation in ("query", "record", "debit"):
                    with self.subTest(level=level, bad_first=bad_first, operation=operation):
                        ledger = self.ledger(f"dup-{level}-{bad_first}-{operation}")
                        text = ledger.path.read_text(encoding="utf-8").rstrip()
                        if level == "root":
                            bad = '"version": null'
                            text = ("{" + bad + ", " + text[1:] if bad_first
                                    else text[:-1] + ", " + bad + "}")
                        elif level == "extra":
                            members = ['"member": null', '"member": 1']
                            if not bad_first:
                                members.reverse()
                            text = '{"unused": {' + ", ".join(members) + "}, " + text[1:]
                        elif level == "escaped-name":
                            members = ['"member": null', r'"\u006dember": 1']
                            if not bad_first:
                                members.reverse()
                            text = '{"unused": {' + ", ".join(members) + "}, " + text[1:]
                        else:
                            if level == "entry":
                                valid = '"execution_id": "initial"'
                                bad = '"execution_id": {}'
                            elif level == "metadata":
                                # The first version member is inside identity metadata.
                                valid = '"version": 1'
                                bad = '"version": null'
                            else:
                                digest_field = resources.Ledger._EXECUTION_IDENTITY_DIGEST
                                digest = ledger.payload["entries"][0][digest_field]
                                valid = json.dumps(digest_field) + ": " + json.dumps(digest)
                                bad = json.dumps(digest_field) + ": null"
                            self.assertIn(valid, text)
                            members = (bad, valid) if bad_first else (valid, bad)
                            text = text.replace(valid, ", ".join(members), 1)
                        ledger.path.write_text(text, encoding="utf-8")
                        before = ledger.path.read_bytes()
                        with mock.patch.object(ledger, "_write", side_effect=AssertionError):
                            with self.assertRaisesRegex(resources.ResourceError,
                                                        "duplicate JSON member"):
                                if operation == "query":
                                    ledger.effective_used_seconds()
                                elif operation == "record":
                                    ledger.record(execution_id="b", run_id="test", seconds=1)
                                else:
                                    self.debit(ledger)
                        self.assertEqual(ledger.path.read_bytes(), before)
                        with self.assertRaisesRegex(resources.ResourceError,
                                                    "duplicate JSON member"):
                            _test_ledger(ledger.path, batch_id="isolated-test")

    def test_matching_identity_digest_does_not_hide_duplicate_json_metadata(self):
        for operation in ("query", "record", "debit"):
            with self.subTest(operation=operation):
                ledger = self.ledger(operation)
                text = ledger.path.read_text(encoding="utf-8")
                text = text.replace('"version": 1', '"version": null, "version": 1', 1)
                # Demonstrate that last-member-wins parsing would see an intact
                # identity and its matching digest, despite the duplicate name.
                entry = json.loads(text)["entries"][0]
                metadata = entry[resources.Ledger._EXECUTION_IDENTITY]
                self.assertEqual(resources.Ledger._identity_digest(metadata),
                                 entry[resources.Ledger._EXECUTION_IDENTITY_DIGEST])
                ledger.path.write_text(text, encoding="utf-8")
                before = ledger.path.read_bytes()
                with self.assertRaisesRegex(resources.ResourceError, "duplicate JSON member"):
                    if operation == "query":
                        ledger.active_seconds()
                    elif operation == "record":
                        ledger.record(execution_id="b", run_id="test", seconds=1)
                    else:
                        self.debit(ledger)
                self.assertEqual(ledger.path.read_bytes(), before)

    def test_invalid_string_codepoint_encoding_is_resource_error(self):
        for index, codepoints in enumerate(([True], [-1], [0x110000], [1.5], ["65"], {})):
            with self.subTest(codepoints=codepoints):
                ledger = self.ledger(f"bad-codepoints-{index}")
                payload = copy.deepcopy(ledger.payload)
                entry = payload["entries"][0]
                metadata = {"version": 1, "value": ["string", codepoints]}
                entry[resources.Ledger._EXECUTION_IDENTITY] = metadata
                entry[resources.Ledger._EXECUTION_IDENTITY_DIGEST] = (
                    resources.Ledger._identity_digest(metadata)
                )
                self.write_payload(ledger.path, payload)
                with self.assertRaises(resources.ResourceError):
                    ledger.active_seconds()

    def test_prewrite_duplicate_nan_note_members_are_rejected_without_state_loss(self):
        ledger = self.ledger("nan-note")
        before = ledger.path.read_bytes()
        first_nan = float("nan")
        second_nan = float("nan")
        self.assertIsNot(first_nan, second_nan)
        with self.assertRaisesRegex(resources.ResourceError, "duplicate JSON member"):
            ledger.record(
                execution_id="nan-note",
                run_id="test",
                seconds=3,
                note={first_nan: "first", second_nan: "second"},
            )
        self.assertEqual(ledger.path.read_bytes(), before)
        self.assertFalse(ledger._write_uncertain)
        self.assertEqual(ledger.active_seconds(), 2)
        ledger.record(execution_id="safe-after-reject", run_id="test", seconds=3)
        self.assertEqual(ledger.active_seconds(), 5)
        reopened = _test_ledger(ledger.path, batch_id="isolated-test")
        self.assertEqual(reopened.active_seconds(), 5)


if __name__ == "__main__":
    unittest.main()
