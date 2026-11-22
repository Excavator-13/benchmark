"""Wait helpers and lifecycle adapter for an explicitly injected mutex API."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from math import isfinite
from pathlib import Path
from threading import Lock, Thread, current_thread
from typing import Callable, Protocol

from .ledger_lock import (
    AcquireResult,
    AcquireStatus,
    LedgerPathBinding,
    LedgerWriteLock,
    ReleaseResult,
    ReleaseStatus,
)


_WAIT_OBJECT_0 = 0x00000000
_WAIT_ABANDONED = 0x00000080
_WAIT_TIMEOUT = 0x00000102
_WAIT_FAILED = 0xFFFFFFFF
_MAX_FINITE_WAIT_MS = 0xFFFFFFFE


def map_wait_status(code: object) -> AcquireStatus:
    """Map an exact built-in integer wait result to the lock protocol status."""
    if type(code) is not int:
        return AcquireStatus.UNKNOWN
    if code == _WAIT_OBJECT_0:
        return AcquireStatus.ACQUIRED
    if code == _WAIT_ABANDONED:
        return AcquireStatus.ABANDONED
    if code == _WAIT_TIMEOUT:
        return AcquireStatus.TIMEOUT
    if code == _WAIT_FAILED:
        return AcquireStatus.WAIT_FAILED
    return AcquireStatus.UNKNOWN


def timeout_to_wait_ms(timeout: object) -> int | None:
    """Convert seconds to finite Win32 milliseconds, rounding down."""
    if type(timeout) is int:
        if 0 <= timeout <= _MAX_FINITE_WAIT_MS // 1000:
            return timeout * 1000
        return None

    if type(timeout) is not float or not isfinite(timeout) or timeout < 0:
        return None

    numerator, denominator = timeout.as_integer_ratio()
    wait_ms = (numerator * 1000) // denominator
    if wait_ms > _MAX_FINITE_WAIT_MS:
        return None
    return wait_ms


@dataclass(frozen=True, slots=True, eq=False)
class MutexHandle:
    """Identity credential issued by a trusted facade."""

    _issuer: object


@dataclass(frozen=True, slots=True)
class CreateOpened:
    """One handle was delivered without initial mutex ownership."""

    handle: MutexHandle


@dataclass(frozen=True, slots=True)
class CreateFailedClean:
    """Creation failed with no resources left for the caller to clean up."""

    detail: str = ""


@dataclass(frozen=True, slots=True)
class CreateUncertain:
    handle: MutexHandle | None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class WaitOwned:
    code: int


@dataclass(frozen=True, slots=True)
class WaitNotOwned:
    code: int
    detail: str = ""


@dataclass(frozen=True, slots=True)
class WaitUncertain:
    detail: str = ""


@dataclass(frozen=True, slots=True)
class CallSucceeded:
    pass


@dataclass(frozen=True, slots=True)
class CallFailed:
    detail: str = ""


@dataclass(frozen=True, slots=True)
class CallUncertain:
    detail: str = ""


CreateResult = CreateOpened | CreateFailedClean | CreateUncertain
WaitResult = WaitOwned | WaitNotOwned | WaitUncertain
CallResult = CallSucceeded | CallFailed | CallUncertain


class MutexApi(Protocol):
    @property
    def handle_issuer(self) -> object: ...

    def _issue_handle(self, resource: object) -> MutexHandle: ...

    def owns_handle(self, handle: MutexHandle) -> bool: ...

    def create_or_open_mutex(self, name: str) -> CreateResult: ...

    def wait_for_single_object(self, handle: MutexHandle, *, timeout_ms: int) -> WaitResult: ...

    def release_mutex(self, handle: MutexHandle) -> CallResult: ...

    def close_handle(self, handle: MutexHandle) -> CallResult: ...


class MutexSecurityVerifier(Protocol):
    def verify(self, handle: MutexHandle) -> bool: ...


class _State(Enum):
    IDLE = auto()
    ACQUIRING = auto()
    HELD = auto()
    RELEASING = auto()
    CLEANUP_UNCERTAIN = auto()


class _Outcome(Enum):
    NOT_ATTEMPTED = "not_attempted"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class _StageResult:
    stage: str
    reason_code: str
    detail: str = ""
    exception: BaseException | None = None


@dataclass(slots=True)
class _Operation:
    binding: LedgerPathBinding
    thread: Thread
    handle: MutexHandle | None = None
    create_started: bool = False
    ownership: str = "not_acquired"
    wait_thread: Thread | None = None
    owner_thread: Thread | None = None
    abandoned: bool = False
    release_outcome: _Outcome = _Outcome.NOT_ATTEMPTED
    close_outcome: _Outcome = _Outcome.NOT_ATTEMPTED
    stage_results: list[_StageResult] = field(default_factory=list)

    @property
    def handle_known(self) -> bool:
        return self.handle is not None

    @property
    def close_attempted(self) -> bool:
        return self.close_outcome is not _Outcome.NOT_ATTEMPTED


class WindowsMutexLedgerLock(LedgerWriteLock):
    """Ledger lock with no default facade or security verifier."""

    def __init__(
        self,
        ledger_path: Path,
        *,
        mutex_name: str,
        api: MutexApi,
        security_verifier: MutexSecurityVerifier | None,
    ) -> None:
        self._binding = LedgerPathBinding.from_path(ledger_path)
        self._mutex_name = mutex_name
        self._api = api
        self._issuer = api.handle_issuer
        if type(self._issuer) is not object:
            raise ValueError("mutex facade issuer must be an identity object")
        self._security_verifier = security_verifier
        self._state_lock = Lock()
        self._state = _State.IDLE
        self._operation: _Operation | None = None
        self._last_operation: _Operation | None = None

    @property
    def ledger_path(self) -> Path:
        return self._binding.ledger_path

    def binding_matches(self, binding: LedgerPathBinding) -> bool:
        return type(binding) is LedgerPathBinding and binding == self._binding

    def _record(
        self,
        operation: _Operation,
        stage: str,
        reason: str,
        detail: str = "",
        exception: BaseException | None = None,
    ) -> None:
        with self._state_lock:
            operation.stage_results.append(_StageResult(stage, reason, detail, exception))

    def _settle(self, operation: _Operation, state: _State) -> None:
        with self._state_lock:
            self._last_operation = operation
            self._operation = operation if state is _State.CLEANUP_UNCERTAIN else None
            self._state = state

    def acquire(
        self,
        *,
        timeout: float | None = None,
        binding: LedgerPathBinding | None = None,
    ) -> AcquireResult:
        operation = _Operation(self._binding, current_thread())
        try:
            with self._state_lock:
                if self._state is not _State.IDLE:
                    reason = (
                        "reuse_blocked"
                        if self._state is _State.CLEANUP_UNCERTAIN
                        else "acquire_busy"
                    )
                    return AcquireResult(AcquireStatus.WAIT_FAILED, reason)
                self._operation = operation
                self._state = _State.ACQUIRING
            return self._acquire(operation, timeout, binding)
        except BaseException as error:
            with self._state_lock:
                active = self._operation is operation
            if active:
                self._finish_interrupted(operation, error)
            raise

    def _acquire(
        self,
        operation: _Operation,
        timeout: float | None,
        binding: LedgerPathBinding | None,
    ) -> AcquireResult:
        try:
            if self._binding is not operation.binding or (
                binding is not None and not self.binding_matches(binding)
            ):
                return self._reject_acquire(operation, "binding", "binding_invalid", AcquireStatus.UNKNOWN)
        except Exception as error:
            return self._reject_acquire(
                operation, "binding", "binding_invalid", AcquireStatus.UNKNOWN, error
            )
        timeout_ms = timeout_to_wait_ms(timeout)
        if timeout_ms is None:
            return self._reject_acquire(operation, "timeout", "timeout_invalid", AcquireStatus.WAIT_FAILED)

        opened = self._create(operation)
        if opened is not None:
            return opened
        handle = operation.handle
        assert handle is not None
        if not self._verify_security(operation, handle):
            return self._failed_acquire(operation, AcquireStatus.UNKNOWN)
        status = self._wait(operation, handle, timeout_ms)
        if status not in (AcquireStatus.ACQUIRED, AcquireStatus.ABANDONED):
            return self._failed_acquire(operation, status)
        with self._state_lock:
            self._state = _State.HELD
        return AcquireResult(status)

    def _reject_acquire(
        self,
        operation: _Operation,
        stage: str,
        reason: str,
        status: AcquireStatus,
        exception: Exception | None = None,
    ) -> AcquireResult:
        self._record(operation, stage, reason, exception=exception)
        self._settle(operation, _State.IDLE)
        return AcquireResult(status, reason)

    def _create(self, operation: _Operation) -> AcquireResult | None:
        with self._state_lock:
            operation.create_started = True
        try:
            result = self._api.create_or_open_mutex(self._mutex_name)
        except BaseException as error:
            self._record(operation, "create", "create_exception", exception=error)
            if not isinstance(error, Exception):
                raise
            return self._failed_acquire(operation, AcquireStatus.UNKNOWN, uncertain=True)

        kind = type(result)
        if kind is CreateFailedClean:
            detail = getattr(result, "detail", None)
            if type(detail) is str:
                self._record(operation, "create", "create_failed_clean", detail)
                self._settle(operation, _State.IDLE)
                return AcquireResult(AcquireStatus.WAIT_FAILED, "create_failed_clean")

        if kind is CreateOpened or kind is CreateUncertain:
            missing = object()
            handle = getattr(result, "handle", missing)
            detail = getattr(result, "detail", None) if kind is CreateUncertain else ""
            if handle is not missing and (kind is CreateOpened or handle is not None):
                if not self._confirm_handle(operation, handle):
                    return self._failed_acquire(operation, AcquireStatus.UNKNOWN, uncertain=True)
                if kind is CreateOpened:
                    self._record(operation, "create", "create_opened")
                    return None
            if kind is CreateUncertain and handle is not missing and type(detail) is str:
                self._record(operation, "create", "create_uncertain", detail)
                return self._failed_acquire(operation, AcquireStatus.UNKNOWN, uncertain=True)

        self._record(operation, "create", "create_result_invalid")
        return self._failed_acquire(operation, AcquireStatus.UNKNOWN, uncertain=True)

    def _confirm_handle(self, operation: _Operation, handle: object) -> bool:
        if type(handle) is not MutexHandle or not hasattr(handle, "_issuer"):
            reason = "handle_invalid"
        elif handle._issuer is not self._issuer:
            reason = "handle_foreign"
        else:
            try:
                owned = self._api.owns_handle(handle)
            except BaseException as error:
                self._record(operation, "create", "handle_check_exception", exception=error)
                if not isinstance(error, Exception):
                    raise
                return False
            if owned is True:
                with self._state_lock:
                    operation.handle = handle
                return True
            reason = "handle_unregistered" if owned is False else "handle_check_invalid"
        self._record(operation, "create", reason)
        return False

    def _verify_security(self, operation: _Operation, handle: MutexHandle) -> bool:
        verifier = self._security_verifier
        if verifier is None:
            self._record(operation, "security", "security_missing")
            return False
        try:
            verified = verifier.verify(handle)
        except BaseException as error:
            self._record(operation, "security", "security_exception", exception=error)
            if not isinstance(error, Exception):
                raise
            return False
        if verified is True:
            self._record(operation, "security", "security_verified")
            return True
        reason = "security_rejected" if verified is False else "security_result_invalid"
        self._record(operation, "security", reason)
        return False

    def _wait(
        self, operation: _Operation, handle: MutexHandle, timeout_ms: int
    ) -> AcquireStatus:
        with self._state_lock:
            operation.wait_thread = operation.thread
            operation.ownership = "possibly_owned"
        try:
            result = self._api.wait_for_single_object(handle, timeout_ms=timeout_ms)
        except BaseException as error:
            self._record(operation, "wait", "wait_exception", exception=error)
            if not isinstance(error, Exception):
                raise
            return AcquireStatus.UNKNOWN

        kind = type(result)
        if kind is WaitOwned:
            status = map_wait_status(getattr(result, "code", None))
            if status in (AcquireStatus.ACQUIRED, AcquireStatus.ABANDONED):
                with self._state_lock:
                    operation.ownership = "owned"
                    operation.owner_thread = operation.thread
                    operation.abandoned = status is AcquireStatus.ABANDONED
                    operation.stage_results.append(_StageResult("wait", status.value))
                return status
        if kind is WaitNotOwned:
            status = map_wait_status(getattr(result, "code", None))
            detail = getattr(result, "detail", None)
            if type(detail) is str and status in (AcquireStatus.TIMEOUT, AcquireStatus.WAIT_FAILED):
                reason = "wait_timeout" if status is AcquireStatus.TIMEOUT else "wait_failed"
                with self._state_lock:
                    operation.ownership = "not_acquired"
                    operation.stage_results.append(_StageResult("wait", reason, detail))
                return status
        if kind is WaitUncertain:
            detail = getattr(result, "detail", None)
            if type(detail) is str:
                self._record(operation, "wait", "wait_uncertain", detail)
                return AcquireStatus.UNKNOWN
        self._record(operation, "wait", "wait_result_invalid")
        return AcquireStatus.UNKNOWN

    def _failed_acquire(
        self, operation: _Operation, status: AcquireStatus, *, uncertain: bool = False
    ) -> AcquireResult:
        cause = operation.stage_results[-1]
        uncertain = uncertain or operation.ownership == "possibly_owned"
        if operation.handle is not None:
            self._close(operation)
            uncertain = uncertain or operation.close_outcome is not _Outcome.SUCCEEDED
        result = AcquireResult(
            AcquireStatus.UNKNOWN if uncertain else status,
            f"{cause.stage}/{cause.reason_code}; close={operation.close_outcome.value}",
        )
        self._settle(operation, _State.CLEANUP_UNCERTAIN if uncertain else _State.IDLE)
        return result

    def release(self, *, binding: LedgerPathBinding | None = None) -> ReleaseResult:
        thread = current_thread()
        operation = None
        try:
            with self._state_lock:
                if self._state is not _State.HELD:
                    reason = "reuse_blocked" if self._state is _State.CLEANUP_UNCERTAIN else "not_held"
                    return ReleaseResult(ReleaseStatus.UNKNOWN, reason)
                held = self._operation
                assert held is not None
                if held.owner_thread is not thread:
                    held.stage_results.append(_StageResult("release", "wrong_thread"))
                    return ReleaseResult(ReleaseStatus.UNKNOWN, "wrong_thread")
                operation = held
                self._state = _State.RELEASING
            return self._release(operation, binding)
        except BaseException as error:
            with self._state_lock:
                active = operation is not None and self._operation is operation
            if active:
                self._finish_interrupted(operation, error)
            raise

    def _release(
        self, operation: _Operation, binding: LedgerPathBinding | None
    ) -> ReleaseResult:
        if self._binding is not operation.binding or binding is not None:
            try:
                matches = self._binding is operation.binding and self.binding_matches(binding)
            except Exception as error:
                matches = False
                self._record(operation, "release", "release_binding_invalid", exception=error)
            else:
                if not matches:
                    self._record(operation, "release", "release_binding_invalid")
            if not matches:
                with self._state_lock:
                    self._state = _State.HELD
                return ReleaseResult(ReleaseStatus.UNKNOWN, "release_binding_invalid")

        start = len(operation.stage_results)
        self._release_handle(operation)
        self._close(operation)
        release, close = operation.release_outcome, operation.close_outcome
        if release is _Outcome.SUCCEEDED and close is _Outcome.SUCCEEDED:
            result = ReleaseResult(ReleaseStatus.RELEASED)
            self._settle(operation, _State.IDLE)
            return result

        status = (
            ReleaseStatus.UNKNOWN
            if _Outcome.UNKNOWN in (release, close)
            else ReleaseStatus.FAILED
        )
        cleanup = operation.stage_results[start:]
        errors = tuple(item.exception for item in cleanup if item.exception is not None)
        reasons = ", ".join(item.reason_code for item in cleanup)
        result = ReleaseResult(status, f"{reasons}; close={close.value}", errors)
        self._settle(operation, _State.CLEANUP_UNCERTAIN)
        return result

    def _release_handle(self, operation: _Operation) -> None:
        self._handle_call(operation, "release", lambda handle: self._api.release_mutex(handle))

    def _close(self, operation: _Operation) -> None:
        self._handle_call(operation, "close", lambda handle: self._api.close_handle(handle))

    def _handle_call(
        self,
        operation: _Operation,
        stage: str,
        call: Callable[[MutexHandle], CallResult],
    ) -> None:
        attr = "release_outcome" if stage == "release" else "close_outcome"
        with self._state_lock:
            handle = operation.handle
            if handle is None or getattr(operation, attr) is not _Outcome.NOT_ATTEMPTED:
                return
            setattr(operation, attr, _Outcome.UNKNOWN)
        try:
            result = call(handle)
        except BaseException as error:
            with self._state_lock:
                if stage == "release":
                    operation.ownership = "possibly_owned"
                operation.stage_results.append(_StageResult(
                    stage, f"{stage}_exception", exception=error
                ))
            if not isinstance(error, Exception):
                raise
            return

        outcome, reason, detail = self._interpret_call(stage, result)
        with self._state_lock:
            setattr(operation, attr, outcome)
            if stage == "release" and outcome is _Outcome.SUCCEEDED:
                operation.ownership = "released"
            elif stage == "release" and outcome is _Outcome.UNKNOWN:
                operation.ownership = "possibly_owned"
            operation.stage_results.append(_StageResult(stage, reason, detail))

    @staticmethod
    def _interpret_call(stage: str, result: object) -> tuple[_Outcome, str, str]:
        kind = type(result)
        if kind is CallSucceeded:
            return _Outcome.SUCCEEDED, f"{stage}_succeeded", ""
        if kind is CallFailed or kind is CallUncertain:
            detail = getattr(result, "detail", None)
            if type(detail) is str:
                if kind is CallFailed:
                    return _Outcome.FAILED, f"{stage}_failed", detail
                return _Outcome.UNKNOWN, f"{stage}_uncertain", detail
        return _Outcome.UNKNOWN, f"{stage}_result_invalid", ""

    def _finish_interrupted(self, operation: _Operation, original: BaseException) -> None:
        with self._state_lock:
            if self._state is _State.HELD:
                self._state = _State.RELEASING
        if not any(item.exception is original for item in operation.stage_results):
            self._record(operation, "lifecycle", "lifecycle_interrupted", exception=original)
        try:
            if (
                operation.ownership == "owned"
                and operation.owner_thread is current_thread()
                and operation.release_outcome is _Outcome.NOT_ATTEMPTED
            ):
                try:
                    self._release_handle(operation)
                except BaseException:
                    # The call already recorded this secondary interruption.
                    pass
        finally:
            try:
                if operation.handle_known and not operation.close_attempted:
                    self._close(operation)
            except BaseException:
                # Keep the original interruption as the one the caller receives.
                pass
            finally:
                self._settle(
                    operation,
                    _State.CLEANUP_UNCERTAIN if operation.create_started else _State.IDLE,
                )
