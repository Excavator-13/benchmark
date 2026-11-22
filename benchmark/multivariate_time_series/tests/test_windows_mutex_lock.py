import math
import unittest
from pathlib import Path
from threading import Event, Thread, current_thread
from unittest.mock import patch

from benchmark.multivariate_time_series.temporal import windows_mutex_lock
from benchmark.multivariate_time_series.temporal.ledger_lock import (
    AcquireStatus,
    LedgerPathBinding,
    ReleaseStatus,
)
from benchmark.multivariate_time_series.temporal.windows_mutex_lock import (
    CallFailed,
    CallSucceeded,
    CallUncertain,
    CreateFailedClean,
    CreateOpened,
    CreateUncertain,
    MutexHandle,
    WaitNotOwned,
    WaitOwned,
    WaitUncertain,
    WindowsMutexLedgerLock,
    map_wait_status,
    timeout_to_wait_ms,
)


class HostileInt(int):
    def __int__(self):
        raise AssertionError("int conversion must not be called")

    def __hash__(self):
        raise AssertionError("hash must not be called")

    def __eq__(self, other):
        raise AssertionError("custom equality must not be called")


class MapWaitStatusTests(unittest.TestCase):
    def test_wait_object_zero_maps_to_acquired(self):
        self.assertIs(map_wait_status(0x00000000), AcquireStatus.ACQUIRED)

    def test_wait_abandoned_maps_to_abandoned(self):
        self.assertIs(map_wait_status(0x00000080), AcquireStatus.ABANDONED)

    def test_wait_timeout_maps_to_timeout(self):
        self.assertIs(map_wait_status(0x00000102), AcquireStatus.TIMEOUT)

    def test_wait_failed_maps_to_wait_failed(self):
        self.assertIs(map_wait_status(0xFFFFFFFF), AcquireStatus.WAIT_FAILED)

    def test_other_integer_maps_to_unknown(self):
        self.assertIs(map_wait_status(1), AcquireStatus.UNKNOWN)

    def test_invalid_types_map_to_unknown_without_custom_operations(self):
        invalid_codes = (
            False,
            True,
            HostileInt(0),
            None,
            "0",
            b"\x00",
            0.0,
            object(),
        )
        for code in invalid_codes:
            with self.subTest(code_type=type(code).__name__):
                self.assertIs(map_wait_status(code), AcquireStatus.UNKNOWN)

    def test_non_int_object_does_not_invoke_custom_methods(self):
        class WaitCode:
            def __init__(self):
                self.int_calls = 0
                self.hash_calls = 0
                self.eq_calls = 0

            def __int__(self):
                self.int_calls += 1
                return 0

            def __hash__(self):
                self.hash_calls += 1
                return 0

            def __eq__(self, other):
                self.eq_calls += 1
                return False

        code = WaitCode()
        self.assertIs(map_wait_status(code), AcquireStatus.UNKNOWN)
        self.assertEqual(code.int_calls, 0)
        self.assertEqual(code.hash_calls, 0)
        self.assertEqual(code.eq_calls, 0)


class TimeoutToWaitMsTests(unittest.TestCase):
    def test_rejects_non_builtin_types_without_invoking_custom_methods(self):
        class CustomTimeout:
            def unexpected_call(self, *args):
                raise AssertionError("rejected inputs must not be used")

            __int__ = __float__ = __index__ = unexpected_call
            __eq__ = __lt__ = __hash__ = unexpected_call

        class FloatSubclass(float):
            def as_integer_ratio(self):
                raise AssertionError("float subclasses must not be used")

        for timeout in (None, False, True, "0", HostileInt(0), FloatSubclass(0), CustomTimeout()):
            with self.subTest(input_type=type(timeout).__name__):
                self.assertIsNone(timeout_to_wait_ms(timeout))

    def test_rejects_negative_values(self):
        for timeout in (-1, -0.0005):
            with self.subTest(timeout=timeout):
                self.assertIsNone(timeout_to_wait_ms(timeout))

    def test_zero_and_positive_submillisecond_values_use_zero_wait(self):
        for timeout in (0, 0.0, -0.0, math.nextafter(0.0, 1.0), 0.0005):
            with self.subTest(timeout=timeout):
                wait_ms = timeout_to_wait_ms(timeout)
                self.assertIs(type(wait_ms), int)
                self.assertEqual(wait_ms, 0)

    def test_floors_the_exact_binary_float_value(self):
        self.assertEqual(timeout_to_wait_ms(0.125), 125)
        self.assertEqual(timeout_to_wait_ms(0.1259765625), 125)
        # This float is slightly below 9 ms even though float multiplication rounds to 9.
        self.assertEqual(timeout_to_wait_ms(0.009), 8)

    def test_integer_seconds_at_the_finite_limit_and_beyond(self):
        self.assertEqual(timeout_to_wait_ms(4_294_967), 4_294_967_000)
        self.assertIsNone(timeout_to_wait_ms(4_294_968))
        self.assertIsNone(timeout_to_wait_ms(10**400))

    def test_rejects_nonfinite_values(self):
        for timeout in (math.nan, math.inf, -math.inf):
            with self.subTest(timeout=timeout):
                self.assertIsNone(timeout_to_wait_ms(timeout))

    def test_float_boundary_where_floored_milliseconds_reach_infinite(self):
        # The nearest float to 0xFFFFFFFF ms in seconds lies below the threshold.
        last_finite = 4_294_967.295
        first_rejected = math.nextafter(last_finite, math.inf)
        self.assertEqual(timeout_to_wait_ms(4_294_967.2945), 0xFFFFFFFE)
        self.assertEqual(timeout_to_wait_ms(last_finite), 0xFFFFFFFE)
        self.assertIsNone(timeout_to_wait_ms(first_rejected))


class FakeMutexApi:
    def __init__(self):
        self._issuer = object()
        self._registered = {}
        self.calls = []
        self.handle = self._issue_handle(object())
        self.results = {
            "create": CreateOpened(self.handle),
            "security": True,
            "wait": WaitOwned(0),
            "release": CallSucceeded(),
            "close": CallSucceeded(),
        }

    @property
    def handle_issuer(self):
        return self._issuer

    def _issue_handle(self, resource):
        handle = MutexHandle(self._issuer)
        self._registered[id(handle)] = (handle, resource)
        return handle

    def _step(self, stage, *args, default=None):
        self.calls.append((stage, *args))
        result = self.results.get(stage, default)
        if isinstance(result, BaseException):
            raise result
        return result(*args) if callable(result) else result

    def owns_handle(self, handle):
        registered = self._registered.get(id(handle))
        valid = registered is not None and registered[0] is handle
        return self._step("owns", handle, default=valid)

    def create_or_open_mutex(self, name):
        return self._step("create", name)

    def verify(self, handle):
        return self._step("security", handle)

    def wait_for_single_object(self, handle, *, timeout_ms):
        return self._step("wait", handle, timeout_ms)

    def release_mutex(self, handle):
        return self._step("release", handle)

    def close_handle(self, handle):
        result = self._step("close", handle)
        if type(result) is CallSucceeded:
            self._registered.pop(id(handle), None)
        return result


class WindowsMutexLedgerLockTests(unittest.TestCase):
    def setUp(self):
        self.binding = LedgerPathBinding.from_path(Path("synthetic-mutex-test-ledger"))
        self.api = FakeMutexApi()
        self.lock = self.make_lock(self.api, self.api)

    def make_lock(self, api, verifier):
        return WindowsMutexLedgerLock(
            self.binding.ledger_path, mutex_name="fake", api=api, security_verifier=verifier
        )

    def assert_calls(self, *expected):
        self.assertEqual([call[0] for call in self.api.calls], list(expected))
        for stage, value, *_ in self.api.calls:
            if stage != "create":
                self.assertIs(value, self.api.handle)

    def assert_blocked(self):
        count = len(self.api.calls)
        self.assertEqual(self.lock._state.name, "CLEANUP_UNCERTAIN")
        self.assertIs(self.lock.acquire(timeout=1).status, AcquireStatus.WAIT_FAILED)
        self.assertIs(self.lock.release().status, ReleaseStatus.UNKNOWN)
        self.assertEqual(len(self.api.calls), count)

    def start_worker(self, action):
        finished = Event()
        results = []

        def run():
            try:
                results.append(action())
            except BaseException as error:
                results.append(error)
            finally:
                finished.set()

        worker = Thread(target=run, daemon=True)
        worker.start()
        return worker, finished, results

    def worker_result(self, worker, finished, results):
        self.assertTrue(finished.wait(2), "worker did not complete")
        worker.join(2)
        self.assertFalse(worker.is_alive())
        if isinstance(results[0], BaseException):
            raise results[0]
        return results[0]

    def test_prechecks_use_full_binding_and_bounded_timeout(self):
        mismatched = LedgerPathBinding(self.binding.ledger_path, Path("different-sidecar"))
        self.assertEqual(self.lock.ledger_path, self.binding.ledger_path)
        self.assertIs(self.lock.binding_matches(self.binding), True)
        self.assertIs(self.lock.acquire(timeout=1, binding=mismatched).status, AcquireStatus.UNKNOWN)
        for timeout in (None, True, -1, math.inf, 4_294_968):
            with self.subTest(timeout=timeout):
                self.assertIs(self.lock.acquire(timeout=timeout).status, AcquireStatus.WAIT_FAILED)
        self.assertIs(self.lock.release().status, ReleaseStatus.UNKNOWN)
        self.assert_calls()
        self.assertEqual(self.lock._state.name, "IDLE")

    def test_acquired_and_abandoned_keep_same_handle_until_owner_releases(self):
        for code, expected in ((0, AcquireStatus.ACQUIRED), (128, AcquireStatus.ABANDONED)):
            with self.subTest(code=code):
                self.setUp()
                self.api.results["wait"] = WaitOwned(code)
                self.assertIs(
                    self.lock.acquire(timeout=0.125, binding=self.binding).status, expected
                )
                self.assert_calls("create", "owns", "security", "wait")
                self.assertEqual(self.api.calls[-1][2], 125)
                record = self.lock._operation
                self.assertIs(record.handle, self.api.handle)
                self.assertIs(record.owner_thread, current_thread())
                self.assertIs(record.abandoned, code == 128)
                self.assertIs(self.lock.acquire(timeout=1).status, AcquireStatus.WAIT_FAILED)
                self.assertIs(self.lock.release(binding=self.binding).status, ReleaseStatus.RELEASED)
                self.assert_calls("create", "owns", "security", "wait", "release", "close")
                self.assertEqual(self.lock._state.name, "IDLE")
                self.assertEqual(record.release_outcome.value, "succeeded")
                self.assertEqual(record.close_outcome.value, "succeeded")
                self.assertFalse(self.api._registered)

    def test_bad_release_binding_preserves_owner_and_handle(self):
        self.assertIs(self.lock.acquire(timeout=1).status, AcquireStatus.ACQUIRED)
        binding = LedgerPathBinding(self.binding.ledger_path, Path("different-sidecar"))
        self.assertIs(self.lock.release(binding=binding).status, ReleaseStatus.UNKNOWN)
        self.assert_calls("create", "owns", "security", "wait")
        self.assertEqual(self.lock._state.name, "HELD")
        self.assertIs(self.lock.release(binding=self.binding).status, ReleaseStatus.RELEASED)

    def test_release_diagnostics_only_report_the_current_cleanup(self):
        self.assertIs(self.lock.acquire(timeout=1).status, AcquireStatus.ACQUIRED)
        old_error = OSError("binding")
        with patch.object(self.lock, "binding_matches", side_effect=old_error):
            self.assertIs(self.lock.release(binding=self.binding).status, ReleaseStatus.UNKNOWN)
        close_error = OSError("close")
        self.api.results["close"] = close_error
        released = self.lock.release(binding=self.binding)
        self.assertIs(released.status, ReleaseStatus.UNKNOWN)
        self.assertNotIn("release_binding_invalid", released.detail)
        self.assertEqual(len(released.errors), 1)
        self.assertIs(released.errors[0], close_error)
        self.assertTrue(any(item.exception is old_error
                            for item in self.lock._last_operation.stage_results))

    def test_successful_release_allows_new_handle_on_same_instance(self):
        self.assertIs(self.lock.acquire(timeout=1).status, AcquireStatus.ACQUIRED)
        first_handle = self.api.handle
        self.assertIs(self.lock.release().status, ReleaseStatus.RELEASED)
        self.api.calls.clear()
        self.api.handle = self.api._issue_handle(object())
        self.api.results["create"] = CreateOpened(self.api.handle)
        self.assertIsNot(self.api.handle, first_handle)
        self.assertIs(self.lock.acquire(timeout=1).status, AcquireStatus.ACQUIRED)
        self.assertIs(self.lock.release().status, ReleaseStatus.RELEASED)
        self.assert_calls("create", "owns", "security", "wait", "release", "close")

    def test_only_clean_creation_failure_can_directly_recover(self):
        class CleanSubclass(CreateFailedClean):
            pass

        cases = (
            (CreateFailedClean("fake refusal"), "create_failed_clean", False),
            (CreateFailedClean(5), "create_result_invalid", True),
            (CleanSubclass(), "create_result_invalid", True),
            (CreateUncertain(None), "create_uncertain", True),
            (object(), "create_result_invalid", True),
            (RuntimeError("private"), "create_exception", True),
        )
        for result, reason, uncertain in cases:
            with self.subTest(reason=reason, result_type=type(result).__name__):
                self.setUp()
                self.api.results["create"] = result
                acquired = self.lock.acquire(timeout=1)
                self.assertIs(acquired.status, AcquireStatus.UNKNOWN if uncertain else AcquireStatus.WAIT_FAILED)
                self.assertIn(reason, acquired.detail)
                self.assertNotIn("private", acquired.detail)
                self.assert_calls("create")
                record = self.lock._last_operation
                self.assertFalse(record.handle_known)
                self.assertFalse(record.close_attempted)
                if isinstance(result, Exception):
                    self.assertIs(record.stage_results[0].exception, result)
                if uncertain:
                    self.assert_blocked()
                else:
                    self.assertEqual(self.lock._state.name, "IDLE")

    def test_known_handle_in_uncertain_or_malformed_create_is_closed_once(self):
        for malformed in (False, True):
            for close_result, outcome in (
                (CallSucceeded(), "succeeded"), (CallFailed(), "failed"),
                (CallUncertain(), "unknown"), (True, "unknown"),
                (OSError("close"), "unknown"),
            ):
                with self.subTest(malformed=malformed, close_outcome=outcome):
                    self.setUp()
                    self.api.results["create"] = CreateUncertain(
                        self.api.handle, None if malformed else "partial creation"
                    )
                    self.api.results["close"] = close_result
                    acquired = self.lock.acquire(timeout=1)
                    self.assertIs(acquired.status, AcquireStatus.UNKNOWN)
                    self.assert_calls("create", "owns", "close")
                    record = self.lock._last_operation
                    self.assertTrue(record.handle_known)
                    self.assertTrue(record.close_attempted)
                    self.assertEqual(record.close_outcome.value, outcome)
                    self.assertEqual(record.stage_results[0].reason_code,
                                     "create_result_invalid" if malformed else "create_uncertain")
                    if isinstance(close_result, Exception):
                        self.assertIs(record.stage_results[-1].exception, close_result)
                    self.assert_blocked()

    def test_foreign_unregistered_revoked_and_malformed_handles_are_not_used(self):
        class HostileHandle:
            def unexpected(self, *args):
                raise AssertionError("untrusted credential method invoked")

            __int__ = __hash__ = __eq__ = __getattr__ = unexpected

        for kind, reason, checks_issuer in (
            ("foreign", "handle_foreign", False),
            ("unregistered", "handle_unregistered", True),
            ("revoked", "handle_unregistered", True),
            ("missing_slot", "handle_invalid", False),
            ("hostile", "handle_invalid", False),
        ):
            with self.subTest(kind=kind):
                self.setUp()
                if kind == "foreign":
                    handle = FakeMutexApi().handle
                elif kind == "unregistered":
                    handle = MutexHandle(self.api.handle_issuer)
                elif kind == "revoked":
                    handle = self.api.handle
                    self.api.close_handle(handle)
                    self.api.calls.clear()
                elif kind == "missing_slot":
                    handle = object.__new__(MutexHandle)
                else:
                    handle = HostileHandle()
                self.api.results["create"] = CreateOpened(handle)
                acquired = self.lock.acquire(timeout=1)
                self.assertIs(acquired.status, AcquireStatus.UNKNOWN)
                self.assertIn(reason, acquired.detail)
                self.assertEqual([item[0] for item in self.api.calls],
                                 ["create", "owns"] if checks_issuer else ["create"])
                self.assertFalse(self.lock._last_operation.handle_known)
                self.assert_blocked()

    def test_ownership_check_must_return_exact_true(self):
        for verdict, reason in (
            (False, "handle_unregistered"), (1, "handle_check_invalid"),
            (OSError("private"), "handle_check_exception"),
        ):
            with self.subTest(reason=reason):
                self.setUp()
                self.api.results["owns"] = verdict
                acquired = self.lock.acquire(timeout=1)
                self.assertIs(acquired.status, AcquireStatus.UNKNOWN)
                self.assertIn(reason, acquired.detail)
                self.assert_calls("create", "owns")
                self.assert_blocked()

    def test_security_needs_exact_true_and_closes_without_waiting(self):
        for verdict, reason in (
            (None, "security_missing"), (False, "security_rejected"),
            (1, "security_result_invalid"), (OSError("private"), "security_exception"),
        ):
            for close_result in (CallSucceeded(), CallFailed(), CallUncertain(), OSError("close")):
                with self.subTest(reason=reason, close_type=type(close_result).__name__):
                    self.setUp()
                    self.api.results.update(security=verdict, close=close_result)
                    if verdict is None:
                        self.lock = self.make_lock(self.api, None)
                    acquired = self.lock.acquire(timeout=1)
                    self.assertIs(acquired.status, AcquireStatus.UNKNOWN)
                    self.assertIn(reason, acquired.detail)
                    if verdict is None:
                        self.assert_calls("create", "owns", "close")
                    else:
                        self.assert_calls("create", "owns", "security", "close")
                    self.assertEqual(self.lock._last_operation.ownership, "not_acquired")
                    if type(close_result) is CallSucceeded:
                        self.assertEqual(self.lock._state.name, "IDLE")
                    else:
                        self.assert_blocked()

    def test_confirmed_not_owned_wait_requires_successful_close(self):
        for code, status in ((258, AcquireStatus.TIMEOUT), (0xFFFFFFFF, AcquireStatus.WAIT_FAILED)):
            for close_result in (CallSucceeded(), CallFailed(), CallUncertain(), OSError("close")):
                with self.subTest(code=code, close_type=type(close_result).__name__):
                    self.setUp()
                    self.api.results.update(wait=WaitNotOwned(code), close=close_result)
                    acquired = self.lock.acquire(timeout=1)
                    self.assert_calls("create", "owns", "security", "wait", "close")
                    self.assertEqual(self.lock._last_operation.ownership, "not_acquired")
                    if type(close_result) is CallSucceeded:
                        self.assertIs(acquired.status, status)
                        self.assertEqual(self.lock._state.name, "IDLE")
                    else:
                        self.assertIs(acquired.status, AcquireStatus.UNKNOWN)
                        self.assert_blocked()

    def test_wait_uncertainty_survives_close_success(self):
        class OwnedSubclass(WaitOwned):
            pass

        for result in (
            WaitUncertain("private"), WaitUncertain(3), WaitOwned(50), WaitOwned(258),
            WaitOwned(False), WaitOwned(HostileInt(0)), WaitNotOwned(0), WaitNotOwned(258, False),
            object.__new__(WaitOwned), OwnedSubclass(0), 0, OSError("private"),
        ):
            with self.subTest(result_type=type(result).__name__):
                self.setUp()
                self.api.results["wait"] = result
                acquired = self.lock.acquire(timeout=1)
                self.assertIs(acquired.status, AcquireStatus.UNKNOWN)
                self.assertNotIn("private", acquired.detail)
                self.assert_calls("create", "owns", "security", "wait", "close")
                record = self.lock._last_operation
                self.assertEqual(record.ownership, "possibly_owned")
                self.assertIs(record.wait_thread, current_thread())
                self.assertTrue(record.handle_known)
                self.assertTrue(record.close_attempted)
                self.assertEqual(record.close_outcome.value, "succeeded")
                if isinstance(result, Exception):
                    self.assertIs(record.stage_results[-2].exception, result)
                self.assert_blocked()

    def test_wrong_thread_release_preserves_held_record_for_owner(self):
        self.assertIs(self.lock.acquire(timeout=1).status, AcquireStatus.ACQUIRED)
        record = self.lock._operation
        result = self.worker_result(*self.start_worker(self.lock.release))
        self.assertIs(result.status, ReleaseStatus.UNKNOWN)
        self.assert_calls("create", "owns", "security", "wait")
        self.assertEqual(self.lock._state.name, "HELD")
        self.assertIs(self.lock._operation, record)
        self.assertIs(record.owner_thread, current_thread())
        self.assertIs(self.lock.release().status, ReleaseStatus.RELEASED)
        self.assert_calls("create", "owns", "security", "wait", "release", "close")

    def test_release_and_close_outcomes_are_independent(self):
        class SuccessSubclass(CallSucceeded):
            pass

        cases = (
            (CallSucceeded(), "succeeded"), (CallFailed("private"), "failed"),
            (CallUncertain(), "unknown"), (True, "unknown"), (SuccessSubclass(), "unknown"),
            (CallFailed(3), "unknown"), (CallUncertain(3), "unknown"),
            (OSError("private"), "unknown"),
        )
        for release_result, release_outcome in cases:
            for close_result, close_outcome in cases:
                with self.subTest(release=type(release_result).__name__,
                                  close=type(close_result).__name__):
                    self.setUp()
                    self.assertIs(self.lock.acquire(timeout=1).status, AcquireStatus.ACQUIRED)
                    self.api.results.update(release=release_result, close=close_result)
                    released = self.lock.release()
                    self.assert_calls("create", "owns", "security", "wait", "release", "close")
                    record = self.lock._last_operation
                    self.assertEqual(record.release_outcome.value, release_outcome)
                    self.assertEqual(record.close_outcome.value, close_outcome)
                    self.assertNotIn("private", released.detail)
                    errors = [item for item in (release_result, close_result)
                              if isinstance(item, Exception)]
                    self.assertEqual(len(released.errors), len(errors))
                    for actual, expected in zip(released.errors, errors):
                        self.assertIs(actual, expected)
                    if release_outcome == close_outcome == "succeeded":
                        self.assertIs(released.status, ReleaseStatus.RELEASED)
                        self.assertEqual(self.lock._state.name, "IDLE")
                    else:
                        expected = (ReleaseStatus.UNKNOWN if "unknown" in (release_outcome, close_outcome)
                                    else ReleaseStatus.FAILED)
                        self.assertIs(released.status, expected)
                        self.assert_blocked()

    def test_concurrent_and_reentrant_calls_observe_transition(self):
        for stage, state, response in (
            ("create", "ACQUIRING", None), ("security", "ACQUIRING", True),
            ("wait", "ACQUIRING", WaitOwned(0)),
            ("release", "RELEASING", CallSucceeded()),
            ("close", "RELEASING", CallSucceeded()),
        ):
            with self.subTest(stage=stage):
                self.setUp()
                reached, proceed = Event(), Event()
                reentrant = []

                def callback(*args):
                    reentrant.append(self.lock.acquire(timeout=1).status)
                    reentrant.append(self.lock.release().status)
                    reached.set()
                    if not proceed.wait(2):
                        raise RuntimeError("test did not unblock facade")
                    return CreateOpened(self.api.handle) if stage == "create" else response

                def lifecycle():
                    acquired = self.lock.acquire(timeout=1)
                    return acquired.status, self.lock.release().status

                self.api.results[stage] = callback
                worker, finished, results = self.start_worker(lifecycle)
                try:
                    self.assertTrue(reached.wait(2), "facade did not reach test gate")
                    self.assertEqual(self.lock._state.name, state)
                    self.assertEqual(reentrant, [AcquireStatus.WAIT_FAILED, ReleaseStatus.UNKNOWN])
                    count = len(self.api.calls)
                    probe = self.start_worker(
                        lambda: (self.lock.acquire(timeout=1).status, self.lock.release().status)
                    )
                    self.assertEqual(self.worker_result(*probe),
                                     (AcquireStatus.WAIT_FAILED, ReleaseStatus.UNKNOWN))
                    self.assertEqual(len(self.api.calls), count)
                finally:
                    proceed.set()
                    worker.join(2)
                self.assertEqual(self.worker_result(worker, finished, results),
                                 (AcquireStatus.ACQUIRED, ReleaseStatus.RELEASED))

    def test_interruption_before_creation_restores_idle(self):
        interrupt = KeyboardInterrupt()
        with patch.object(windows_mutex_lock, "timeout_to_wait_ms", side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt) as raised:
                self.lock.acquire(timeout=1)
        self.assertIs(raised.exception, interrupt)
        self.assert_calls()
        self.assertEqual(self.lock._state.name, "IDLE")
        self.assertFalse(self.lock._last_operation.create_started)
        self.assertIs(self.lock.acquire(timeout=1).status, AcquireStatus.ACQUIRED)
        self.assertIs(self.lock.release().status, ReleaseStatus.RELEASED)

    def test_interruptions_across_facade_stages_attempt_close_at_most_once(self):
        for stage, calls, ownership in (
            ("create", ("create",), "not_acquired"),
            ("owns", ("create", "owns"), "not_acquired"),
            ("security", ("create", "owns", "security", "close"), "not_acquired"),
            ("wait", ("create", "owns", "security", "wait", "close"), "possibly_owned"),
            ("release", ("create", "owns", "security", "wait", "release", "close"), "possibly_owned"),
            ("close", ("create", "owns", "security", "wait", "release", "close"), "released"),
        ):
            with self.subTest(stage=stage):
                self.setUp()
                interrupt = SystemExit(3) if stage == "owns" else KeyboardInterrupt()

                def interrupt_stage(*args):
                    if stage == "close":
                        self.assertTrue(self.lock._operation.close_attempted)
                    raise interrupt

                self.api.results[stage] = interrupt_stage
                if stage in ("release", "close"):
                    self.assertIs(self.lock.acquire(timeout=1).status, AcquireStatus.ACQUIRED)
                    action = self.lock.release
                else:
                    action = lambda: self.lock.acquire(timeout=1)
                with self.assertRaises(type(interrupt)) as raised:
                    action()
                self.assertIs(raised.exception, interrupt)
                self.assert_calls(*calls)
                record = self.lock._last_operation
                self.assertEqual(record.ownership, ownership)
                self.assertIs(record.close_attempted, "close" in calls)
                if stage == "wait":
                    self.assertIs(record.wait_thread, current_thread())
                    self.assertEqual(record.close_outcome.value, "succeeded")
                elif stage == "close":
                    self.assertEqual(record.close_outcome.value, "unknown")
                self.assertTrue(any(item.exception is interrupt for item in record.stage_results))
                self.assert_blocked()

    def test_interruption_after_confirmed_wait_releases_then_closes_as_owner(self):
        for release_result in (CallSucceeded(), SystemExit(4)):
            with self.subTest(release_type=type(release_result).__name__):
                self.setUp()
                primary = KeyboardInterrupt()
                original_wait = self.lock._wait

                def interrupt_after_confirmed_wait(*args):
                    self.assertIs(original_wait(*args), AcquireStatus.ACQUIRED)
                    raise primary

                self.api.results["release"] = release_result
                with patch.object(self.lock, "_wait", side_effect=interrupt_after_confirmed_wait):
                    with self.assertRaises(KeyboardInterrupt) as raised:
                        self.lock.acquire(timeout=1)
                self.assertIs(raised.exception, primary)
                self.assert_calls("create", "owns", "security", "wait", "release", "close")
                self.assertIs(self.lock._last_operation.owner_thread, current_thread())
                if isinstance(release_result, BaseException):
                    self.assertIs(self.lock._last_operation.stage_results[-2].exception, release_result)
                self.assert_blocked()

    def test_close_diagnoses_secondary_failure_without_replacing_first_interrupt(self):
        for close_result, outcome in (
            (CallFailed(), "failed"), (OSError("close"), "unknown"), (SystemExit(4), "unknown"),
        ):
            with self.subTest(close_type=type(close_result).__name__):
                self.setUp()
                primary = KeyboardInterrupt()
                self.api.results["wait"] = primary

                def close(*args):
                    self.assertTrue(self.lock._operation.close_attempted)
                    if isinstance(close_result, BaseException):
                        raise close_result
                    return close_result

                self.api.results["close"] = close
                with self.assertRaises(KeyboardInterrupt) as raised:
                    self.lock.acquire(timeout=1)
                self.assertIs(raised.exception, primary)
                self.assert_calls("create", "owns", "security", "wait", "close")
                record = self.lock._last_operation
                self.assertEqual(record.ownership, "possibly_owned")
                self.assertEqual(record.close_outcome.value, outcome)
                self.assertIs(record.stage_results[-2].exception, primary)
                if isinstance(close_result, BaseException):
                    self.assertIs(record.stage_results[-1].exception, close_result)
                self.assert_blocked()


if __name__ == "__main__":
    unittest.main()
