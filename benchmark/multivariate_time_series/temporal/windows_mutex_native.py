"""Bridge injected mutex observations to creation and closure credentials."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from struct import calcsize
from threading import Lock
from typing import Protocol

from .windows_mutex_lock import (
    CallFailed,
    CallResult,
    CallSucceeded,
    CallUncertain,
    CreateFailedClean,
    CreateOpened,
    CreateResult,
    CreateUncertain,
    MutexHandle,
)


_HANDLE_MAX = (1 << (8 * calcsize("P"))) - 1
_ERROR_ALREADY_EXISTS = 183
_CREATE_OPENED_TYPE = CreateOpened


class NativeCallEntered(Enum):
    NO = auto()
    YES = auto()
    UNKNOWN = auto()


class ErrorEvidence(Enum):
    UNKNOWN = auto()


@dataclass(frozen=True, slots=True)
class KnownLastError:
    value: int


@dataclass(frozen=True, slots=True)
class CreateObservation:
    native_call_entered: NativeCallEntered
    native_return_known: bool
    raw_handle_known: bool
    raw_handle: int | None
    last_error_evidence: KnownLastError | ErrorEvidence


def _is_dword(value: object) -> bool:
    return type(value) is int and 0 <= value <= 0xFFFFFFFF


def _valid_create(observation: object) -> bool:
    if type(observation) is not CreateObservation:
        return False
    try:
        entered = observation.native_call_entered
        returned = observation.native_return_known
        handle_known = observation.raw_handle_known
        handle = observation.raw_handle
        error = observation.last_error_evidence
    except AttributeError:
        return False
    if (
        entered is not NativeCallEntered.NO
        and entered is not NativeCallEntered.YES
        and entered is not NativeCallEntered.UNKNOWN
    ):
        return False
    if type(returned) is not bool or type(handle_known) is not bool:
        return False
    if handle_known:
        if not returned or type(handle) is not int or not 0 <= handle <= _HANDLE_MAX:
            return False
    elif handle is not None:
        return False
    if error is not ErrorEvidence.UNKNOWN:
        if type(error) is not KnownLastError or not _is_dword(getattr(error, "value", None)):
            return False
        if not returned:
            return False
    return not returned or entered is NativeCallEntered.YES


def _preserves_create_evidence(earlier: CreateObservation, later: CreateObservation) -> bool:
    return (
        (earlier.native_call_entered is NativeCallEntered.UNKNOWN
         or earlier.native_call_entered is later.native_call_entered)
        and (not earlier.native_return_known or later.native_return_known)
        and (not earlier.raw_handle_known or earlier.raw_handle == later.raw_handle)
        and (earlier.last_error_evidence is ErrorEvidence.UNKNOWN
             or earlier.last_error_evidence == later.last_error_evidence)
    )


class CreateEvidence:
    """Per-call facts recorded by the observer before it can raise.

    NO certifies a completed pre-call failure. Until entry is confirmed, the
    observer uses UNKNOWN for a call that may already have started.
    """

    __slots__ = ("_observation",)

    def __init__(self) -> None:
        self._observation: CreateObservation | None = None

    @property
    def observation(self) -> CreateObservation | None:
        return self._observation

    def record(self, observation: CreateObservation) -> None:
        if not _valid_create(observation):
            raise ValueError("invalid create observation")
        previous = self._observation
        if previous is not None and not _preserves_create_evidence(previous, observation):
            raise ValueError("create observation contradicts prior evidence")
        self._observation = observation


class CloseOutcome(Enum):
    SUCCEEDED = auto()
    FAILED = auto()
    UNKNOWN = auto()


@dataclass(frozen=True, slots=True)
class CloseDiagnostic:
    stage: str
    reason: str
    exception: BaseException | None = None


@dataclass(frozen=True, slots=True)
class CloseObservation:
    outcome: CloseOutcome
    raw_bool: int | None
    last_error: int | None = None
    diagnostic: CloseDiagnostic | None = None
    native_call_entered: NativeCallEntered = field(kw_only=True)


def _valid_call_entry(value: object) -> bool:
    return (
        value is NativeCallEntered.NO
        or value is NativeCallEntered.YES
        or value is NativeCallEntered.UNKNOWN
    )


def _is_bool32(value: object) -> bool:
    return type(value) is int and -(1 << 31) <= value < (1 << 31)


def _close_outcome(raw_bool: int | None) -> CloseOutcome:
    if raw_bool is None:
        return CloseOutcome.UNKNOWN
    return CloseOutcome.FAILED if raw_bool == 0 else CloseOutcome.SUCCEEDED


def _valid_close(observation: object) -> bool:
    if type(observation) is not CloseObservation:
        return False
    try:
        entered = observation.native_call_entered
        raw_bool = observation.raw_bool
        last_error = observation.last_error
        diagnostic = observation.diagnostic
        if not _valid_call_entry(entered):
            return False
        if raw_bool is not None and (entered is not NativeCallEntered.YES or not _is_bool32(raw_bool)):
            return False
        if observation.outcome is not _close_outcome(raw_bool):
            return False
        if last_error is not None and (raw_bool != 0 or not _is_dword(last_error)):
            return False
        if diagnostic is None:
            return True
        return (
            type(diagnostic) is CloseDiagnostic
            and type(diagnostic.stage) is str
            and type(diagnostic.reason) is str
            and (diagnostic.exception is None or isinstance(diagnostic.exception, BaseException))
        )
    except AttributeError:
        return False


class CloseEvidence:
    """Per-call entry, BOOL and last-error evidence from the trusted boundary."""

    __slots__ = ("_native_call_entered", "_raw_bool", "_last_error")

    def __init__(self) -> None:
        self._native_call_entered = NativeCallEntered.UNKNOWN
        self._raw_bool: int | None = None
        self._last_error: int | None = None

    @property
    def native_call_entered(self) -> NativeCallEntered:
        return self._native_call_entered

    @property
    def raw_bool(self) -> int | None:
        return self._raw_bool

    @property
    def last_error(self) -> int | None:
        return self._last_error

    def record_native_call_entered(self, entered: NativeCallEntered) -> None:
        if not _valid_call_entry(entered) or (
            self._native_call_entered is not NativeCallEntered.UNKNOWN
            and self._native_call_entered is not entered
        ):
            raise ValueError("invalid or conflicting close entry evidence")
        self._native_call_entered = entered

    def record_return(self, raw_bool: int) -> None:
        if self._native_call_entered is not NativeCallEntered.YES or not _is_bool32(raw_bool) or (
            self._raw_bool is not None and self._raw_bool != raw_bool
        ):
            raise ValueError("invalid or conflicting close BOOL")
        self._raw_bool = raw_bool

    def record_last_error(self, value: int) -> None:
        if self._raw_bool != 0 or not _is_dword(value) or (
            self._last_error is not None and self._last_error != value
        ):
            raise ValueError("invalid or conflicting close last-error")
        self._last_error = value


class CreateObserver(Protocol):
    """Observe one named create/open with no initial ownership."""

    def __call__(
        self, *, name: str, desired_access: int, security_descriptor: object,
        evidence: CreateEvidence,
    ) -> CreateObservation: ...


class CloseObserver(Protocol):
    """Observe one close and record entry only when the underlying call is confirmed."""

    def __call__(self, raw_handle: int, *, evidence: CloseEvidence) -> CloseObservation: ...


class _CloseState(Enum):
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    UNKNOWN = auto()


@dataclass(slots=True)
class _CloseAttempt:
    evidence: CloseEvidence = field(default_factory=CloseEvidence)
    state: _CloseState = _CloseState.IN_PROGRESS
    observation: CloseObservation | None = None
    diagnostics: list[CloseDiagnostic] = field(default_factory=list)


@dataclass(slots=True)
class _Resource:
    create_evidence: CreateEvidence = field(default_factory=CreateEvidence)
    raw_handle: int | None = None
    existing: bool | None = None
    credential: MutexHandle | None = None
    published: bool = False
    delivery_uncertain: bool = False
    close: _CloseAttempt | None = None
    diagnostics: list[CloseDiagnostic] = field(default_factory=list)

    @property
    def close_state(self) -> _CloseState:
        return _CloseState.NOT_STARTED if self.close is None else self.close.state

    @property
    def close_attempted(self) -> bool:
        return self.close is not None


class ObservedMutexCreateCloseFacade:
    """Creation and closure only, with explicit observation providers."""

    def __init__(
        self,
        *,
        observe_create_mutex: CreateObserver,
        observe_close_handle: CloseObserver,
        desired_access: int,
        security_descriptor: object,
    ) -> None:
        if not _is_dword(desired_access):
            raise ValueError("desired_access must be a DWORD")
        if security_descriptor is None:
            raise ValueError("security_descriptor must be provided")
        self._observe_create_mutex = observe_create_mutex
        self._observe_close_handle = observe_close_handle
        self._desired_access = desired_access
        self._security_descriptor = security_descriptor
        self._issuer = object()
        self._lock = Lock()
        self._registered: dict[int, _Resource] = {}
        self._retained: dict[int, _Resource] = {}

    @property
    def handle_issuer(self) -> object:
        return self._issuer

    def _issue_handle(self, resource: _Resource) -> MutexHandle:
        credential = MutexHandle(self._issuer)
        with self._lock:
            resource.credential = credential
            self._registered[id(credential)] = resource
        return credential

    def _lookup(self, handle: MutexHandle) -> _Resource | None:
        # Caller holds the registration lock.
        if type(handle) is not MutexHandle or getattr(handle, "_issuer", None) is not self._issuer:
            return None
        resource = self._registered.get(id(handle))
        if resource is None or resource.credential is not handle:
            return None
        if not resource.published or resource.close_attempted:
            return None
        return resource

    def owns_handle(self, handle: MutexHandle) -> bool:
        with self._lock:
            return self._lookup(handle) is not None

    def create_or_open_mutex(self, name: str) -> CreateResult:
        if type(name) is not str or not name or "\x00" in name:
            return CreateFailedClean("invalid_mutex_name")

        resource = _Resource()
        stage = "observe_create"
        try:
            observation = self._observe_create_mutex(
                name=name, desired_access=self._desired_access,
                security_descriptor=self._security_descriptor, evidence=resource.create_evidence,
            )
            if not _valid_create(observation):
                return self._create_failure(resource, "invalid_create_observation", allow_clean=False)
            previous = resource.create_evidence.observation
            if previous is not None and not _preserves_create_evidence(previous, observation):
                return self._create_failure(resource, "conflicting_create_evidence", allow_clean=False)
            resource.create_evidence.record(observation)
            self._record_handle(resource)

            if resource.raw_handle is None:
                return self._create_failure(resource, "create_handle_unconfirmed")
            if resource.existing is None:
                return self._create_failure(resource, "create_origin_unconfirmed")

            stage = "register"
            credential = self._issue_handle(resource)
            stage = "construct_result"
            result = CreateOpened(credential)
            stage = "publish"
            return self._publish(resource, credential, result)
        except BaseException as error:
            self._record_create_diagnostic(resource, stage, "create_exception", error)
            if resource.published:
                with self._lock:
                    resource.delivery_uncertain = True
                if isinstance(error, Exception):
                    return CreateUncertain(None, "create_delivery_unconfirmed")
                raise

            self._record_handle(resource)
            try:
                cleaned = self._discard_private_handle(resource)
            except BaseException:
                if isinstance(error, Exception):
                    # An interruption during cleanup takes priority over an ordinary failure.
                    raise
                cleaned = False
            if not isinstance(error, Exception):
                raise
            if cleaned:
                return CreateFailedClean("create_exception_cleaned")
            return CreateUncertain(None, "create_exception")

    def _publish(
        self, resource: _Resource, expected_credential: MutexHandle, result: CreateOpened
    ) -> CreateOpened:
        with self._lock:
            if type(result) is not _CREATE_OPENED_TYPE:
                raise ValueError("invalid create result type")
            credential = getattr(result, "handle", None)
            if (
                type(credential) is not MutexHandle
                or getattr(credential, "_issuer", None) is not self._issuer
                or credential is not expected_credential
                or resource.credential is not credential
                or self._registered.get(id(credential)) is not resource
                or resource.close_attempted
                or resource.published
            ):
                raise ValueError("create result has no valid pending credential")
            # Claim through the registry after publication, even if delivery is interrupted.
            resource.published = True
        return result

    def _record_handle(self, resource: _Resource) -> None:
        observation = resource.create_evidence.observation
        if observation is None or observation.raw_handle is None or observation.raw_handle == 0:
            return
        error = observation.last_error_evidence
        with self._lock:
            resource.raw_handle = observation.raw_handle
            if type(error) is KnownLastError:
                resource.existing = error.value == _ERROR_ALREADY_EXISTS

    def _record_create_diagnostic(
        self, resource: _Resource, stage: str, reason: str, error: BaseException | None = None
    ) -> None:
        with self._lock:
            resource.diagnostics.append(CloseDiagnostic(stage, reason, error))
            self._retained[id(resource)] = resource

    def _create_failure(
        self, resource: _Resource, reason: str, *, allow_clean: bool = True
    ) -> CreateResult:
        self._record_create_diagnostic(resource, "observe_create", reason)
        self._record_handle(resource)
        cleaned = self._discard_private_handle(resource)
        observation = resource.create_evidence.observation
        if allow_clean and observation is not None:
            if observation.native_call_entered is NativeCallEntered.NO:
                return CreateFailedClean("create_not_entered")
            if observation.raw_handle == 0 and type(observation.last_error_evidence) is KnownLastError:
                return CreateFailedClean(f"create_returned_null:{observation.last_error_evidence.value}")
            if cleaned:
                return CreateFailedClean(f"{reason}:closed")
        return CreateUncertain(None, reason)

    def _discard_private_handle(self, resource: _Resource) -> bool:
        if resource.raw_handle is None:
            return False
        self._close_once(resource, published=False)
        with self._lock:
            return resource.close_state is _CloseState.SUCCEEDED

    def close_handle(self, handle: MutexHandle) -> CallResult:
        with self._lock:
            resource = self._lookup(handle)
        if resource is None:
            return CallUncertain("close_credential_unavailable")
        return self._close_once(resource, published=True)

    def _close_once(self, resource: _Resource, *, published: bool) -> CallResult:
        attempt = _CloseAttempt()
        observation = None
        dispatch_started = False
        try:
            with self._lock:
                if resource.published is not published or resource.close_attempted:
                    return CallUncertain("close_already_claimed")
                raw_handle = resource.raw_handle
                assert raw_handle is not None
                # The same assignment claims closure and disables credential lookup.
                resource.close = attempt
            observer = self._observe_close_handle
            # The observer owns entry confirmation once dispatch may have begun.
            dispatch_started = True
            observation = observer(raw_handle, evidence=attempt.evidence)
            return self._settle_close(resource, attempt, observation)
        except BaseException as error:
            with self._lock:
                claimed = resource.close is attempt
            if not claimed:
                raise
            try:
                if not dispatch_started:
                    attempt.evidence.record_native_call_entered(NativeCallEntered.NO)
                result = self._settle_close(resource, attempt, observation, error)
            except BaseException as settling_error:
                with self._lock:
                    attempt.diagnostics.append(CloseDiagnostic("settle", "close_settle_exception", settling_error))
                    self._retained[id(resource)] = resource
                if isinstance(error, Exception):
                    raise
            if not isinstance(error, Exception):
                raise
            return result

    def _settle_close(
        self, resource: _Resource, attempt: _CloseAttempt, observation: object,
        error: BaseException | None = None,
    ) -> CallResult:
        evidence = attempt.evidence
        diagnostic = None
        if _valid_close(observation) and (
            evidence.native_call_entered is NativeCallEntered.UNKNOWN
            or evidence.native_call_entered is observation.native_call_entered
        ) and (
            evidence.raw_bool is None or evidence.raw_bool == observation.raw_bool
        ) and (evidence.last_error is None or evidence.last_error == observation.last_error):
            final = observation
        else:
            if error is None or observation is not None:
                diagnostic = CloseDiagnostic("validate", "close_observation_invalid")
            final = CloseObservation(
                _close_outcome(evidence.raw_bool), evidence.raw_bool, evidence.last_error,
                diagnostic, native_call_entered=evidence.native_call_entered,
            )
        with self._lock:
            attempt.observation = final
            if error is not None:
                if final.raw_bool is not None:
                    reason = "close_exception"
                elif final.native_call_entered is NativeCallEntered.NO:
                    reason = "close_not_entered"
                elif final.native_call_entered is NativeCallEntered.YES:
                    reason = "close_return_unconfirmed"
                else:
                    reason = "close_entry_or_return_unconfirmed"
                attempt.diagnostics.append(CloseDiagnostic("close", reason, error))
            if final.diagnostic is not None:
                attempt.diagnostics.append(final.diagnostic)
            if final.outcome is CloseOutcome.SUCCEEDED:
                attempt.state = _CloseState.SUCCEEDED
                if resource.credential is not None:
                    key = id(resource.credential)
                    if self._registered.get(key) is resource:
                        del self._registered[key]
            elif final.outcome is CloseOutcome.FAILED:
                attempt.state = _CloseState.FAILED
            else:
                attempt.state = _CloseState.UNKNOWN
            if attempt.state is not _CloseState.SUCCEEDED or attempt.diagnostics:
                self._retained[id(resource)] = resource

        if final.outcome is CloseOutcome.SUCCEEDED:
            return CallSucceeded()
        if final.outcome is CloseOutcome.FAILED:
            detail = "close_returned_zero"
            if final.last_error is not None:
                detail += f":{final.last_error}"
            return CallFailed(detail)
        return CallUncertain("close_result_unconfirmed")
