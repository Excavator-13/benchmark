"""Exercise the create/close bridge with in-memory observations."""

import unittest
from dataclasses import replace
from struct import calcsize
from threading import Event, Thread
from unittest.mock import PropertyMock, patch

from benchmark.multivariate_time_series.temporal import windows_mutex_native as native
from benchmark.multivariate_time_series.temporal.windows_mutex_lock import (
    CallFailed,
    CallSucceeded,
    CallUncertain,
    CreateFailedClean,
    CreateOpened,
    CreateUncertain,
    MutexHandle,
)


ENTERED = native.NativeCallEntered
OUTCOME = native.CloseOutcome
UNKNOWN_ERROR = native.ErrorEvidence.UNKNOWN
RAW_HANDLE = 0x112345678 if calcsize("P") == 8 else 0x81234567


def created(raw_handle=RAW_HANDLE, last_error=0):
    error = UNKNOWN_ERROR if last_error is None else native.KnownLastError(last_error)
    return native.CreateObservation(ENTERED.YES, True, True, raw_handle, error)


def close_observation(outcome, raw_bool, last_error=None, *, entered=ENTERED.YES):
    return native.CloseObservation(outcome, raw_bool, last_error, native_call_entered=entered)


class FakeObservers:
    def __init__(self):
        self.create_calls = []
        self.close_calls = []
        self.create_result = created()
        self.close_result = close_observation(OUTCOME.SUCCEEDED, 1)
        self.descriptor = object()

    def observe_create(self, *, name, desired_access, security_descriptor, evidence):
        self.create_calls.append((name, desired_access, security_descriptor))
        if callable(self.create_result):
            return self.create_result(evidence)
        return self.create_result

    def observe_close(self, raw_handle, *, evidence):
        self.close_calls.append(raw_handle)
        if callable(self.close_result):
            return self.close_result(evidence)
        return self.close_result

    def facade(self):
        return native.ObservedMutexCreateCloseFacade(
            observe_create_mutex=self.observe_create,
            observe_close_handle=self.observe_close,
            desired_access=0x123,
            security_descriptor=self.descriptor,
        )


class ObservedMutexCreateCloseTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeObservers()
        self.facade = self.fake.facade()

    def open_handle(self):
        opened = self.facade.create_or_open_mutex("synthetic-name")
        self.assertIs(type(opened), CreateOpened)
        self.assertIs(self.facade.owns_handle(opened.handle), True)
        return opened.handle

    def retained_record(self):
        self.assertEqual(len(self.facade._retained), 1)
        return next(iter(self.facade._retained.values()))

    def assert_uncertain_create(self, result):
        self.assertIs(type(result), CreateUncertain)
        self.assertIsNone(result.handle)

    def test_known_handle_distinguishes_existing_from_other_valid_error_codes(self):
        for error in (183, 0, 5, 0xFFFFFFFF):
            with self.subTest(error=error):
                self.fake.create_result = created(last_error=error)
                handle = self.open_handle()
                self.assertIs(type(handle), MutexHandle)
                self.assertIs(handle._issuer, self.facade.handle_issuer)
                record = self.facade._registered[id(handle)]
                self.assertIs(record.existing, error == 183)
                self.assertEqual(record.create_evidence.observation.last_error_evidence.value, error)
                name, access, descriptor = self.fake.create_calls[-1]
                self.assertEqual((name, access), ("synthetic-name", 0x123))
                self.assertIs(descriptor, self.fake.descriptor)
                self.assertIs(type(self.facade.close_handle(handle)), CallSucceeded)
                self.assertEqual(self.fake.close_calls[-1], RAW_HANDLE)
                self.assertIs(self.facade.owns_handle(handle), False)
                self.assertNotIn(id(handle), self.facade._registered)

    def test_invalid_or_unnamed_input_never_enters_observer(self):
        for name in ("", "a\x00b", None, object()):
            with self.subTest(name_type=type(name).__name__):
                self.assertIs(type(self.facade.create_or_open_mutex(name)), CreateFailedClean)
        self.assertEqual(self.fake.create_calls, [])
        self.assertEqual(self.fake.close_calls, [])

    def test_valid_create_evidence_combinations_without_nonnull_handle(self):
        for observation, result_type in (
            (native.CreateObservation(ENTERED.NO, False, False, None, UNKNOWN_ERROR), CreateFailedClean),
            (native.CreateObservation(ENTERED.UNKNOWN, False, False, None, UNKNOWN_ERROR), CreateUncertain),
            (native.CreateObservation(ENTERED.YES, False, False, None, UNKNOWN_ERROR), CreateUncertain),
            (native.CreateObservation(ENTERED.YES, True, False, None, UNKNOWN_ERROR), CreateUncertain),
            (native.CreateObservation(ENTERED.YES, True, False, None, native.KnownLastError(0)), CreateUncertain),
            (created(0, None), CreateUncertain),
            (created(0, 0), CreateFailedClean),
            (created(0, 5), CreateFailedClean),
        ):
            with self.subTest(observation=observation):
                self.setUp()
                self.fake.create_result = observation
                result = self.facade.create_or_open_mutex("synthetic-name")
                self.assertIs(type(result), result_type)
                if result_type is CreateUncertain:
                    self.assertIsNone(result.handle)
                self.assertIs(self.retained_record().create_evidence.observation, observation)
                self.assertEqual(self.fake.close_calls, [])

    def test_malformed_create_evidence_never_supplies_a_handle(self):
        class IntSubclass(int):
            pass

        class ObservationSubclass(native.CreateObservation):
            pass

        class Pretender:
            def __getattr__(self, name):
                raise AssertionError("untrusted object inspected")

        cases = (
            replace(created(), native_call_entered=ENTERED.NO),
            replace(created(), native_return_known=False),
            replace(created(), native_return_known=1),
            replace(created(), raw_handle_known=False),
            replace(created(), raw_handle_known=1),
            replace(created(), raw_handle=True),
            replace(created(), raw_handle=IntSubclass(1)),
            replace(created(), raw_handle=-1),
            replace(created(), raw_handle=1 << (8 * calcsize("P"))),
            replace(created(), raw_handle=None),
            replace(created(), last_error_evidence=native.KnownLastError(True)),
            replace(created(), last_error_evidence=native.KnownLastError(-1)),
            replace(created(), last_error_evidence=native.KnownLastError(1 << 32)),
            replace(created(), last_error_evidence=0),
            ObservationSubclass(ENTERED.YES, True, True, RAW_HANDLE, UNKNOWN_ERROR),
            object.__new__(native.CreateObservation),
            Pretender(),
        )
        for observation in cases:
            with self.subTest(observation_type=type(observation).__name__):
                self.setUp()
                self.fake.create_result = observation
                self.assert_uncertain_create(self.facade.create_or_open_mutex("synthetic-name"))
                self.assertEqual(self.fake.close_calls, [])
                self.assertEqual(self.retained_record().diagnostics[0].reason, "invalid_create_observation")

    def test_malformed_or_conflicting_create_result_uses_only_independent_handle_evidence(self):
        for returned in (object(), created(RAW_HANDLE - 1), created(last_error=183)):
            with self.subTest(returned_type=type(returned).__name__):
                self.setUp()
                trusted = created()

                def observe(evidence):
                    evidence.record(trusted)
                    return returned

                self.fake.create_result = observe
                self.assert_uncertain_create(self.facade.create_or_open_mutex("synthetic-name"))
                self.assertEqual(self.fake.close_calls, [RAW_HANDLE])
                record = self.retained_record()
                self.assertIs(record.create_evidence.observation, trusted)
                self.assertEqual(record.close_state.name, "SUCCEEDED")
                self.assertIsNone(record.credential)

    def test_create_evidence_can_advance_but_cannot_erase_confirmed_facts(self):
        def observe(evidence):
            evidence.record(native.CreateObservation(ENTERED.YES, False, False, None, UNKNOWN_ERROR))
            evidence.record(native.CreateObservation(ENTERED.YES, True, False, None, UNKNOWN_ERROR))
            evidence.record(created(last_error=None))
            last = created(last_error=0)
            evidence.record(last)
            with self.assertRaises(ValueError):
                evidence.record(created(last_error=None))
            with self.assertRaises(ValueError):
                evidence.record(created(RAW_HANDLE - 1))
            self.assertIs(evidence.observation, last)
            return last

        self.fake.create_result = observe
        handle = self.open_handle()
        self.assertIs(type(self.facade.close_handle(handle)), CallSucceeded)
        self.assertEqual(self.fake.close_calls, [RAW_HANDLE])

    def test_unknown_error_preserves_nonnull_handle_for_internal_close(self):
        self.fake.create_result = created(last_error=None)
        for close, result_type in (
            (close_observation(OUTCOME.SUCCEEDED, 1), CreateFailedClean),
            (close_observation(OUTCOME.FAILED, 0), CreateUncertain),
            (close_observation(OUTCOME.UNKNOWN, None, entered=ENTERED.UNKNOWN), CreateUncertain),
        ):
            with self.subTest(close=close):
                self.facade = self.fake.facade()
                self.fake.close_calls.clear()
                self.fake.close_result = close
                result = self.facade.create_or_open_mutex("synthetic-name")
                self.assertIs(type(result), result_type)
                if result_type is CreateUncertain:
                    self.assertIsNone(result.handle)
                record = self.retained_record()
                self.assertEqual(record.raw_handle, RAW_HANDLE)
                self.assertIsNone(record.existing)
                self.assertEqual(self.fake.close_calls, [RAW_HANDLE])
                self.assertEqual(record.close_state.name, close.outcome.name)

    def test_create_exception_preserves_independent_evidence_and_ignores_exception_handle(self):
        for evidence_value, expected_calls, expected_type in (
            (None, [], CreateUncertain),
            (native.CreateObservation(ENTERED.YES, True, False, None, native.KnownLastError(0)),
             [], CreateUncertain),
            (created(last_error=None), [RAW_HANDLE], CreateFailedClean),
        ):
            with self.subTest(evidence=evidence_value):
                self.setUp()
                error = RuntimeError("create capture failed")
                error.raw_handle = RAW_HANDLE - 1

                def observe(evidence):
                    if evidence_value is not None:
                        evidence.record(evidence_value)
                    raise error

                self.fake.create_result = observe
                self.assertIs(type(self.facade.create_or_open_mutex("synthetic-name")), expected_type)
                self.assertEqual(self.fake.close_calls, expected_calls)
                record = self.retained_record()
                self.assertIs(record.create_evidence.observation, evidence_value)
                self.assertIs(record.diagnostics[0].exception, error)

    def test_prepublication_registration_and_result_errors_share_single_cleanup(self):
        for stage in ("register", "construct_result"):
            for close in (
                close_observation(OUTCOME.SUCCEEDED, 1),
                close_observation(OUTCOME.FAILED, 0, 6),
                close_observation(OUTCOME.UNKNOWN, None, entered=ENTERED.UNKNOWN),
            ):
                with self.subTest(stage=stage, close=close):
                    self.setUp()
                    self.fake.close_result = close
                    error = RuntimeError(stage)
                    credentials = []
                    original_issue = self.facade._issue_handle

                    def failing_issue(resource):
                        credentials.append(original_issue(resource))
                        raise error

                    def failing_result(credential):
                        credentials.append(credential)
                        raise error

                    if stage == "register":
                        failure = patch.object(self.facade, "_issue_handle", failing_issue)
                    else:
                        failure = patch.object(native, "CreateOpened", failing_result)
                    with failure:
                        result = self.facade.create_or_open_mutex("synthetic-name")
                    if close.outcome is OUTCOME.SUCCEEDED:
                        self.assertIs(type(result), CreateFailedClean)
                    else:
                        self.assert_uncertain_create(result)
                    self.assertEqual(len(credentials), 1)
                    handle = credentials[0]
                    self.assertFalse(self.facade.owns_handle(handle))
                    self.assertIs(type(self.facade.close_handle(handle)), CallUncertain)
                    self.assertEqual(self.fake.close_calls, [RAW_HANDLE])
                    record = self.retained_record()
                    self.assertIs(record.diagnostics[0].exception, error)
                    self.assertEqual(record.close_state.name, close.outcome.name)

    def test_publish_handoff_unknown_never_internally_closes_or_reissues(self):
        for error in (RuntimeError("handoff"), KeyboardInterrupt()):
            with self.subTest(error_type=type(error).__name__):
                self.setUp()
                original_publish = self.facade._publish
                constructed = []

                def interrupted_publish(record, expected_credential, result):
                    self.assertFalse(self.facade.owns_handle(result.handle))
                    constructed.append(original_publish(record, expected_credential, result))
                    raise error

                with patch.object(self.facade, "_publish", interrupted_publish):
                    if isinstance(error, Exception):
                        self.assert_uncertain_create(self.facade.create_or_open_mutex("synthetic-name"))
                    else:
                        with self.assertRaises(KeyboardInterrupt) as raised:
                            self.facade.create_or_open_mutex("synthetic-name")
                        self.assertIs(raised.exception, error)

                record = self.retained_record()
                self.assertTrue(record.delivery_uncertain)
                self.assertFalse(record.close_attempted)
                self.assertEqual(self.fake.close_calls, [])
                self.assertEqual(len(self.fake.create_calls), 1)
                # Simulate the recipient retaining the exact published credential.
                handle = constructed[0].handle
                self.assertIs(type(self.facade.close_handle(handle)), CallSucceeded)
                self.assertIs(type(self.facade.close_handle(handle)), CallUncertain)
                self.assertEqual(self.fake.close_calls, [RAW_HANDLE])

    def assert_publish_rejected(self, replacement, result_type=CreateFailedClean):
        pending = []
        calls_before = self.fake.close_calls.copy()

        def construct(credential):
            pending.append(credential)
            self.assertFalse(self.facade.owns_handle(credential))
            return replacement

        with patch.object(native, "CreateOpened", side_effect=construct):
            result = self.facade.create_or_open_mutex("synthetic-name")
        self.assertEqual(len(pending), 1)
        self.assertIs(type(result), result_type)
        if result_type is CreateUncertain:
            self.assertIsNone(result.handle)
        credential = pending[0]
        self.assertFalse(self.facade.owns_handle(credential))
        self.assertIs(type(self.facade.close_handle(credential)), CallUncertain)
        record = self.retained_record()
        self.assertIs(record.credential, credential)
        self.assertFalse(record.published)
        self.assertEqual(record.diagnostics[0].stage, "publish")
        self.assertEqual(self.fake.close_calls, [*calls_before, RAW_HANDLE])
        if result_type is CreateFailedClean:
            self.assertNotIn(id(credential), self.facade._registered)
        else:
            self.assertIs(self.facade._registered[id(credential)], record)

    def test_publish_rejects_invalid_result_without_probing_unknown_types(self):
        class UnknownResult:
            def __getattr__(self, name):
                raise AssertionError("unknown result inspected")

        class OpenedSubclass(CreateOpened):
            pass

        for replacement in (
            UnknownResult(),
            OpenedSubclass(MutexHandle(self.facade.handle_issuer)),
            object.__new__(CreateOpened),
            CreateOpened(object()),
        ):
            for close_outcome in (OUTCOME.SUCCEEDED, OUTCOME.FAILED, OUTCOME.UNKNOWN):
                with self.subTest(result=type(replacement).__name__, close=close_outcome):
                    self.setUp()
                    if close_outcome is OUTCOME.FAILED:
                        self.fake.close_result = close_observation(OUTCOME.FAILED, 0)
                    elif close_outcome is OUTCOME.UNKNOWN:
                        self.fake.close_result = close_observation(
                            OUTCOME.UNKNOWN, None, entered=ENTERED.UNKNOWN
                        )
                    result_type = (
                        CreateFailedClean if close_outcome is OUTCOME.SUCCEEDED else CreateUncertain
                    )
                    self.assert_publish_rejected(replacement, result_type)
                    self.assertIs(type(self.retained_record().diagnostics[0].exception), ValueError)

    def test_publish_rejects_foreign_and_unregistered_credentials(self):
        other_fake = FakeObservers()
        other_fake.create_result = created(RAW_HANDLE - 1)
        other = other_fake.facade()
        foreign = other.create_or_open_mutex("other-fake").handle
        for kind in ("foreign", "unregistered"):
            with self.subTest(kind=kind):
                self.setUp()
                credential = (
                    foreign if kind == "foreign" else MutexHandle(self.facade.handle_issuer)
                )
                self.assert_publish_rejected(CreateOpened(credential))
                self.assertFalse(self.facade.owns_handle(credential))
                self.assertIs(type(self.facade.close_handle(credential)), CallUncertain)
                self.assertEqual(self.fake.close_calls, [RAW_HANDLE])
                self.assertEqual(other_fake.close_calls, [])
                self.assertTrue(other.owns_handle(foreign))

    def test_publish_does_not_close_another_live_registry_resource(self):
        self.fake.create_result = created(RAW_HANDLE - 1)
        other = self.open_handle()
        other_record = self.facade._registered[id(other)]
        self.fake.create_result = created()
        self.assert_publish_rejected(CreateOpened(other))
        self.assertTrue(self.facade.owns_handle(other))
        self.assertIs(self.facade._registered[id(other)], other_record)
        self.assertFalse(other_record.close_attempted)

    def test_publish_rejects_revoked_credential_even_when_handle_number_is_reused(self):
        revoked = self.open_handle()
        self.assertIs(type(self.facade.close_handle(revoked)), CallSucceeded)
        self.assert_publish_rejected(CreateOpened(revoked))
        self.assertNotIn(id(revoked), self.facade._registered)
        self.assertFalse(self.facade.owns_handle(revoked))

    def test_publish_checks_pending_registry_still_points_to_original_resource(self):
        self.fake.create_result = created(RAW_HANDLE - 1)
        other = self.open_handle()
        other_record = self.facade._registered[id(other)]
        self.fake.create_result = created()
        pending = []

        def construct(credential):
            pending.append(credential)
            self.facade._registered[id(credential)] = other_record
            return CreateOpened(credential)

        with patch.object(native, "CreateOpened", side_effect=construct):
            result = self.facade.create_or_open_mutex("synthetic-name")
        self.assertIs(type(result), CreateFailedClean)
        credential = pending[0]
        self.assertFalse(self.facade.owns_handle(credential))
        self.assertIs(type(self.facade.close_handle(credential)), CallUncertain)
        self.assertTrue(self.facade.owns_handle(other))
        self.assertIs(self.facade._registered[id(credential)], other_record)
        self.assertFalse(other_record.close_attempted)
        self.assertFalse(self.retained_record().published)
        self.assertEqual(self.fake.close_calls, [RAW_HANDLE])

    def test_publish_already_claimed_pending_close_does_not_retry(self):
        for outcome, raw_bool in ((OUTCOME.SUCCEEDED, 1), (OUTCOME.FAILED, 0),
                                  (OUTCOME.UNKNOWN, None)):
            with self.subTest(outcome=outcome):
                self.setUp()
                self.fake.close_result = close_observation(outcome, raw_bool)
                pending = []

                def construct(credential):
                    pending.append(credential)
                    record = self.facade._registered[id(credential)]
                    self.facade._close_once(record, published=False)
                    return CreateOpened(credential)

                with patch.object(native, "CreateOpened", side_effect=construct):
                    result = self.facade.create_or_open_mutex("synthetic-name")
                if outcome is OUTCOME.SUCCEEDED:
                    self.assertIs(type(result), CreateFailedClean)
                    self.assertNotIn(id(pending[0]), self.facade._registered)
                else:
                    self.assert_uncertain_create(result)
                    self.assertIs(self.facade._registered[id(pending[0])], self.retained_record())
                self.assertFalse(self.facade.owns_handle(pending[0]))
                self.assertIs(type(self.facade.close_handle(pending[0])), CallUncertain)
                self.assertEqual(self.retained_record().close_state.name, outcome.name)
                self.assertFalse(self.retained_record().published)
                self.assertEqual(self.fake.close_calls, [RAW_HANDLE])

    def test_publish_activates_only_the_legitimate_pending_result(self):
        built = []

        def construct(credential):
            record = self.facade._registered[id(credential)]
            self.assertIs(record.credential, credential)
            self.assertFalse(record.published)
            self.assertFalse(self.facade.owns_handle(credential))
            result = CreateOpened(credential)
            built.append(result)
            return result

        with patch.object(native, "CreateOpened", side_effect=construct):
            opened = self.facade.create_or_open_mutex("synthetic-name")
        self.assertIs(opened, built[0])
        self.assertTrue(self.facade.owns_handle(opened.handle))
        self.assertTrue(self.facade._registered[id(opened.handle)].published)
        self.assertEqual(self.fake.close_calls, [])
        self.assertIs(type(self.facade.close_handle(opened.handle)), CallSucceeded)
        self.assertEqual(self.fake.close_calls, [RAW_HANDLE])

    def test_unregistered_foreign_and_old_credentials_cannot_close_reused_number(self):
        old = self.open_handle()
        other = self.fake.facade()
        foreign = other.create_or_open_mutex("another-test-name").handle
        for credential in (foreign, MutexHandle(self.facade.handle_issuer),
                           object.__new__(MutexHandle), RAW_HANDLE):
            self.assertFalse(self.facade.owns_handle(credential))
            self.assertIs(type(self.facade.close_handle(credential)), CallUncertain)
        self.assertEqual(self.fake.close_calls, [])
        self.assertIs(type(self.facade.close_handle(old)), CallSucceeded)
        new = self.open_handle()
        self.assertIsNot(new, old)
        self.assertFalse(self.facade.owns_handle(old))
        self.assertIs(type(self.facade.close_handle(old)), CallUncertain)
        self.assertIs(type(self.facade.close_handle(new)), CallSucceeded)
        self.assertEqual(self.fake.close_calls, [RAW_HANDLE, RAW_HANDLE])

    def test_close_observations_and_tombstones(self):
        cases = (
            (close_observation(OUTCOME.SUCCEEDED, -1), CallSucceeded, "SUCCEEDED"),
            (close_observation(OUTCOME.FAILED, 0, 0), CallFailed, "FAILED"),
            (close_observation(OUTCOME.FAILED, 0, None), CallFailed, "FAILED"),
            (close_observation(OUTCOME.UNKNOWN, None, entered=ENTERED.UNKNOWN), CallUncertain, "UNKNOWN"),
            (close_observation(OUTCOME.SUCCEEDED, 0), CallUncertain, "UNKNOWN"),
            (close_observation(OUTCOME.SUCCEEDED, True), CallUncertain, "UNKNOWN"),
            (close_observation(OUTCOME.SUCCEEDED, 1, 6), CallUncertain, "UNKNOWN"),
            (close_observation(OUTCOME.SUCCEEDED, 1 << 31), CallUncertain, "UNKNOWN"),
            (close_observation(OUTCOME.FAILED, 0, True), CallUncertain, "UNKNOWN"),
            (close_observation(OUTCOME.SUCCEEDED, 1, entered=ENTERED.NO), CallUncertain, "UNKNOWN"),
            (close_observation(OUTCOME.SUCCEEDED, 1, entered=ENTERED.UNKNOWN), CallUncertain, "UNKNOWN"),
            (close_observation(OUTCOME.SUCCEEDED, 1, entered=True), CallUncertain, "UNKNOWN"),
            (object.__new__(native.CloseObservation), CallUncertain, "UNKNOWN"),
        )
        for observation, result_type, state in cases:
            with self.subTest(result_type=result_type.__name__, state=state):
                self.setUp()
                self.fake.close_result = observation
                handle = self.open_handle()
                record = self.facade._registered[id(handle)]
                self.assertIs(type(self.facade.close_handle(handle)), result_type)
                self.assertEqual(record.close_state.name, state)
                self.assertFalse(self.facade.owns_handle(handle))
                if state != "SUCCEEDED":
                    self.assertIs(self.retained_record(), record)
                self.assertIs(type(self.facade.close_handle(handle)), CallUncertain)
                self.assertEqual(self.fake.close_calls, [RAW_HANDLE])

    def test_close_capture_exception_keeps_confirmed_bool_and_error(self):
        for raw_bool, last_error, expected in (
            (None, None, CallUncertain), (0, None, CallFailed),
            (0, 0, CallFailed), (0, 6, CallFailed), (-1, None, CallSucceeded),
        ):
            with self.subTest(raw_bool=raw_bool, last_error=last_error):
                self.setUp()
                error = OSError("capture")

                def close(evidence):
                    if raw_bool is not None:
                        evidence.record_native_call_entered(ENTERED.YES)
                        evidence.record_return(raw_bool)
                    if last_error is not None:
                        evidence.record_last_error(last_error)
                    raise error

                self.fake.close_result = close
                handle = self.open_handle()
                self.assertIs(type(self.facade.close_handle(handle)), expected)
                record = self.retained_record()
                expected_entry = ENTERED.UNKNOWN if raw_bool is None else ENTERED.YES
                self.assertIs(record.close.observation.native_call_entered, expected_entry)
                self.assertEqual(record.close.observation.raw_bool, raw_bool)
                self.assertEqual(record.close.observation.last_error, last_error)
                self.assertIs(record.close.diagnostics[0].exception, error)
                self.assertIs(type(self.facade.close_handle(handle)), CallUncertain)
                self.assertEqual(self.fake.close_calls, [RAW_HANDLE])

    def test_independent_close_evidence_survives_conflicting_return(self):
        def close(evidence):
            evidence.record_native_call_entered(ENTERED.YES)
            evidence.record_return(0)
            evidence.record_last_error(6)
            return close_observation(OUTCOME.SUCCEEDED, 1)

        self.fake.close_result = close
        handle = self.open_handle()
        self.assertIs(type(self.facade.close_handle(handle)), CallFailed)
        record = self.retained_record()
        self.assertIs(record.close.observation.native_call_entered, ENTERED.YES)
        self.assertEqual(record.close.observation.raw_bool, 0)
        self.assertEqual(record.close.observation.last_error, 6)
        self.assertEqual(record.close.diagnostics[0].reason, "close_observation_invalid")

    def test_close_evidence_rejects_conflicting_or_malformed_updates(self):
        def close(evidence):
            with self.assertRaises(ValueError):
                evidence.record_last_error(0)
            with self.assertRaises(ValueError):
                evidence.record_return(0)
            evidence.record_native_call_entered(ENTERED.YES)
            with self.assertRaises(ValueError):
                evidence.record_native_call_entered(ENTERED.NO)
            with self.assertRaises(ValueError):
                evidence.record_native_call_entered(ENTERED.UNKNOWN)
            with self.assertRaises(ValueError):
                evidence.record_native_call_entered(True)
            evidence.record_return(0)
            evidence.record_last_error(0)
            with self.assertRaises(ValueError):
                evidence.record_return(1)
            with self.assertRaises(ValueError):
                evidence.record_last_error(True)
            with self.assertRaises(ValueError):
                evidence.record_last_error(6)
            return close_observation(OUTCOME.FAILED, evidence.raw_bool, evidence.last_error)

        self.fake.close_result = close
        handle = self.open_handle()
        self.assertEqual(self.facade.close_handle(handle), CallFailed("close_returned_zero:0"))
        self.assertEqual(self.retained_record().close.observation.last_error, 0)
        self.assertEqual(self.fake.close_calls, [RAW_HANDLE])

    def test_close_claim_blocks_concurrent_and_reentrant_requests(self):
        handle = self.open_handle()
        record = self.facade._registered[id(handle)]
        entered, proceed, probed = Event(), Event(), Event()
        results, probe_results = [], []

        def close(evidence):
            if len(self.fake.close_calls) > 1:
                raise AssertionError("second close call")
            results.append(self.facade.close_handle(handle))
            entered.set()
            if not proceed.wait(3):
                raise RuntimeError("test did not release observer")
            return close_observation(OUTCOME.SUCCEEDED, 1)

        def owner():
            results.append(self.facade.close_handle(handle))

        def probe():
            probe_results.append(self.facade.owns_handle(handle))
            probe_results.append(self.facade.close_handle(handle))
            probed.set()

        self.fake.close_result = close
        worker = Thread(target=owner, daemon=True)
        concurrent = Thread(target=probe, daemon=True)
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            self.assertTrue(record.close_attempted)
            self.assertEqual(record.close_state.name, "IN_PROGRESS")
            concurrent.start()
            self.assertTrue(probed.wait(2))
            self.assertIs(probe_results[0], False)
            self.assertIs(type(probe_results[1]), CallUncertain)
        finally:
            proceed.set()
            worker.join(3)
            if concurrent.ident is not None:
                concurrent.join(3)
        self.assertFalse(worker.is_alive())
        self.assertFalse(concurrent.is_alive())
        self.assertEqual([type(result) for result in results], [CallUncertain, CallSucceeded])
        self.assertEqual(self.fake.close_calls, [RAW_HANDLE])

    def test_create_interrupt_preserves_primary_and_secondary_evidence(self):
        for observation in (None, created(last_error=None)):
            with self.subTest(observation=observation):
                self.setUp()
                primary = KeyboardInterrupt()
                secondary = SystemExit(2)

                def original(evidence):
                    if observation is not None:
                        evidence.record(observation)
                    raise primary

                def cleanup(evidence):
                    evidence.record_native_call_entered(ENTERED.YES)
                    evidence.record_return(0)
                    raise secondary

                self.fake.create_result = original
                self.fake.close_result = cleanup
                with self.assertRaises(KeyboardInterrupt) as raised:
                    self.facade.create_or_open_mutex("synthetic-name")
                self.assertIs(raised.exception, primary)
                record = self.retained_record()
                self.assertIs(record.create_evidence.observation, observation)
                self.assertIs(record.diagnostics[0].exception, primary)
                if observation is None:
                    self.assertEqual(self.fake.close_calls, [])
                else:
                    self.assertEqual(self.fake.close_calls, [RAW_HANDLE])
                    self.assertEqual(record.close_state.name, "FAILED")
                    self.assertIs(record.close.diagnostics[0].exception, secondary)

    def test_cleanup_interrupt_propagates_after_ordinary_registration_error(self):
        primary = RuntimeError("register")
        interrupt = KeyboardInterrupt()

        def cleanup(evidence):
            raise interrupt

        self.fake.close_result = cleanup
        with patch.object(self.facade, "_issue_handle", side_effect=primary):
            with self.assertRaises(KeyboardInterrupt) as raised:
                self.facade.create_or_open_mutex("synthetic-name")
        self.assertIs(raised.exception, interrupt)
        record = self.retained_record()
        self.assertIs(record.diagnostics[0].exception, primary)
        self.assertIs(record.close.diagnostics[0].exception, interrupt)
        self.assertEqual(self.fake.close_calls, [RAW_HANDLE])

    def test_close_interrupt_before_observer_entry_or_after_bool_never_retries(self):
        cases = ((None, False, "UNKNOWN"), (None, True, "UNKNOWN"),
                 (0, True, "FAILED"), (1, True, "SUCCEEDED"))
        for raw_bool, enter, state in cases:
            with self.subTest(raw_bool=raw_bool, enter=enter):
                self.setUp()
                handle = self.open_handle()
                record = self.facade._registered[id(handle)]
                interrupt = KeyboardInterrupt()

                def interrupted(evidence):
                    if raw_bool is not None:
                        evidence.record_native_call_entered(ENTERED.YES)
                        evidence.record_return(raw_bool)
                    raise interrupt

                def before_entry(raw_handle, *, evidence):
                    self.assertTrue(record.close_attempted)
                    self.assertFalse(self.facade.owns_handle(handle))
                    raise interrupt

                self.fake.close_result = interrupted
                if not enter:
                    self.facade._observe_close_handle = before_entry
                with self.assertRaises(KeyboardInterrupt) as raised:
                    self.facade.close_handle(handle)
                self.assertIs(raised.exception, interrupt)
                self.assertEqual(record.close_state.name, state)
                self.assertEqual(record.close.observation.raw_bool, raw_bool)
                self.assertIs(record.close.diagnostics[0].exception, interrupt)
                self.assertIs(type(self.facade.close_handle(handle)), CallUncertain)
                self.assertEqual(self.fake.close_calls, [RAW_HANDLE] if enter else [])

    def assert_unconfirmed_close(self, handle, interrupt, entered, close_calls, reason):
        record = self.retained_record()
        self.assertTrue(record.close_attempted)
        self.assertEqual(record.close_state.name, "UNKNOWN")
        self.assertIs(record.close.evidence.native_call_entered, entered)
        self.assertIs(record.close.observation.native_call_entered, entered)
        self.assertIsNone(record.close.observation.raw_bool)
        self.assertIsNone(record.close.observation.last_error)
        self.assertIs(record.close.diagnostics[0].exception, interrupt)
        self.assertEqual(record.close.diagnostics[0].reason, reason)
        self.assertEqual(self.fake.close_calls, close_calls)
        self.assertFalse(self.facade.owns_handle(handle))
        self.assertIs(type(self.facade.close_handle(handle)), CallUncertain)
        self.assertEqual(self.fake.close_calls, close_calls)

    def test_interrupt_before_observer_dispatch_confirms_no_entry(self):
        handle = self.open_handle()
        interrupt = KeyboardInterrupt()
        observer = PropertyMock(side_effect=interrupt)
        with patch.object(type(self.facade), "_observe_close_handle", observer, create=True):
            with self.assertRaises(KeyboardInterrupt) as raised:
                self.facade.close_handle(handle)
        self.assertIs(raised.exception, interrupt)
        observer.assert_called_once_with()
        self.assert_unconfirmed_close(handle, interrupt, ENTERED.NO, [], "close_not_entered")

    def test_interrupt_after_confirmed_entry_keeps_entry_without_bool(self):
        handle = self.open_handle()
        interrupt = KeyboardInterrupt()

        def close(evidence):
            evidence.record_native_call_entered(ENTERED.YES)
            raise interrupt

        self.fake.close_result = close
        with self.assertRaises(KeyboardInterrupt) as raised:
            self.facade.close_handle(handle)
        self.assertIs(raised.exception, interrupt)
        self.assert_unconfirmed_close(
            handle, interrupt, ENTERED.YES, [RAW_HANDLE], "close_return_unconfirmed"
        )

    def test_interrupt_inside_observer_without_entry_evidence_stays_unknown(self):
        handle = self.open_handle()
        interrupt = KeyboardInterrupt()

        def close(evidence):
            self.assertIs(evidence.native_call_entered, ENTERED.UNKNOWN)
            raise interrupt

        self.fake.close_result = close
        with self.assertRaises(KeyboardInterrupt) as raised:
            self.facade.close_handle(handle)
        self.assertIs(raised.exception, interrupt)
        self.assert_unconfirmed_close(
            handle, interrupt, ENTERED.UNKNOWN, [RAW_HANDLE], "close_entry_or_return_unconfirmed"
        )
