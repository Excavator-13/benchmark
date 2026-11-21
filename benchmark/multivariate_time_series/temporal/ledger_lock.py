"""Injectable ledger-lock contracts and a disposable test backend.

The production Windows named-mutex backend is intentionally out of scope for
stage A.  ``FileTestLedgerLock`` exists only for isolated tests and uses an
exclusive sidecar file so independent processes can exercise the transaction
boundary without loading deployment configuration.
"""

from __future__ import annotations

import json
import os
import time
import uuid
import ctypes
import ctypes.wintypes
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Protocol


def canonical_ledger_path(path: Path) -> Path:
    """Return the only path identity supported by the stage-A test backend."""
    return Path(path).resolve(strict=False)


def ledger_sidecar_path(path: Path) -> Path:
    canonical = canonical_ledger_path(path)
    return canonical.with_name(f".{canonical.name}.ledger.lock")


@dataclass(frozen=True, slots=True)
class LedgerPathBinding:
    ledger_path: Path
    sidecar_path: Path

    @classmethod
    def from_path(cls, path: Path) -> "LedgerPathBinding":
        canonical = canonical_ledger_path(path)
        return cls(canonical, canonical.with_name(f".{canonical.name}.ledger.lock"))


class AcquireStatus(str, Enum):
    ACQUIRED = "acquired"
    ABANDONED = "abandoned"
    TIMEOUT = "timeout"
    WAIT_FAILED = "wait_failed"
    UNKNOWN = "unknown"


class ReleaseStatus(str, Enum):
    RELEASED = "released"
    FAILED = "release_failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AcquireResult:
    status: AcquireStatus
    detail: str = ""


@dataclass(frozen=True)
class ReleaseResult:
    status: ReleaseStatus
    detail: str = ""
    errors: tuple[BaseException, ...] = ()


class LedgerWriteLock(Protocol):
    ledger_path: Path

    def binding_matches(self, binding: LedgerPathBinding) -> bool:
        ...

    def acquire(self, *, timeout: Optional[float] = None,
                binding: Optional[LedgerPathBinding] = None) -> AcquireResult:
        ...

    def release(self, *, binding: Optional[LedgerPathBinding] = None) -> ReleaseResult:
        ...


class NoopLedgerWriteLock:
    """Explicit serial test injection; never a production default."""

    def __init__(self, ledger_path: Optional[Path] = None):
        canonical = (
            None if ledger_path is None else canonical_ledger_path(ledger_path)
        )
        self._ledger_path = canonical
        self._binding_ledger_path = canonical

    @property
    def ledger_path(self) -> Optional[Path]:
        return self._ledger_path

    def bind_to(self, ledger_path: Path) -> None:
        if self._ledger_path is not None:
            if self._ledger_path != canonical_ledger_path(ledger_path):
                raise ValueError("Noop lock is already bound to another ledger")
            return
        canonical = canonical_ledger_path(ledger_path)
        self._ledger_path = canonical
        self._binding_ledger_path = canonical

    def binding_matches(self, binding: LedgerPathBinding) -> bool:
        return (
            self._ledger_path is not None
            and self._binding_ledger_path == binding.ledger_path
            and self._ledger_path == self._binding_ledger_path
            and LedgerPathBinding.from_path(self._ledger_path) == binding
        )

    def acquire(self, *, timeout: Optional[float] = None,
                binding: Optional[LedgerPathBinding] = None) -> AcquireResult:
        if binding is not None and not self.binding_matches(binding):
            return AcquireResult(AcquireStatus.UNKNOWN, "Noop binding changed")
        return AcquireResult(AcquireStatus.ACQUIRED)

    def release(self, *, binding: Optional[LedgerPathBinding] = None) -> ReleaseResult:
        if binding is not None and not self.binding_matches(binding):
            return ReleaseResult(ReleaseStatus.UNKNOWN, "Noop binding changed")
        return ReleaseResult(ReleaseStatus.RELEASED)


class FileTestLedgerLock:
    """Disposable cross-process handle lock for tests only.

    The lock file is stable for its lifetime.  Windows uses an exclusive
    CreateFile handle and other platforms use fcntl; process exit closes the handle
    and releases the OS lock.  Owner metadata never decides ownership.
    """

    def __init__(self, ledger_path: Path, *, poll_interval: float = 0.01,
                 publish_owner: bool = True, before_open_signal: Optional[Path] = None,
                 before_open_release: Optional[Path] = None,
                 contention_event=None):
        self._binding = LedgerPathBinding.from_path(ledger_path)
        self._binding_invalid = False
        self.poll_interval = float(poll_interval)
        self.token = uuid.uuid4().hex
        self.publish_owner = bool(publish_owner)
        self.before_open_signal = (
            None if before_open_signal is None else Path(before_open_signal)
        )
        self.before_open_release = (
            None if before_open_release is None else Path(before_open_release)
        )
        self.contention_event = contention_event
        self._handle = None
        self._owned = False
        self._created_by_handle = False
        self._held_binding = None

    def __setattr__(self, name, value):
        if name in {
            "ledger_path", "path", "_binding", "_canonical_ledger_path",
            "_canonical_sidecar_path", "_binding_ledger_path", "_binding_sidecar_path",
        } and "_binding" in self.__dict__:
            object.__setattr__(self, "_binding_invalid", True)
            raise AttributeError("file test lock binding is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if name in {
            "ledger_path", "path", "_binding", "_canonical_ledger_path",
            "_canonical_sidecar_path", "_binding_ledger_path", "_binding_sidecar_path",
        }:
            object.__setattr__(self, "_binding_invalid", True)
            raise AttributeError("file test lock binding is immutable")
        object.__delattr__(self, name)

    @property
    def ledger_path(self) -> Path:
        return self._binding.ledger_path

    @property
    def path(self) -> Path:
        return self._binding.sidecar_path

    def _binding_snapshot(self):
        try:
            binding = self._binding
            if (self._binding_invalid
                    or LedgerPathBinding.from_path(binding.ledger_path) != binding):
                return None
        except Exception:
            return None
        return binding

    def binding_matches(self, binding: LedgerPathBinding) -> bool:
        snapshot = self._binding_snapshot()
        return snapshot is not None and binding == snapshot

    def _read_owner(self) -> Optional[dict]:
        if self._handle is not None:
            try:
                self._handle.seek(0)
                text = self._handle.read()
                return json.loads(text) if text else None
            except (OSError, ValueError):
                return None
        return None

    def _try_os_lock(self, sidecar_path: Path) -> bool:
        if os.name == "nt":
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateFileW.argtypes = [
                ctypes.wintypes.LPCWSTR, ctypes.wintypes.DWORD,
                ctypes.wintypes.DWORD, ctypes.c_void_p, ctypes.wintypes.DWORD,
                ctypes.wintypes.DWORD, ctypes.wintypes.HANDLE,
            ]
            kernel32.CreateFileW.restype = ctypes.wintypes.HANDLE
            try:
                raw = kernel32.CreateFileW(
                    str(sidecar_path), 0xC0000000, 0, None, 4, 0x80, None,
                )
                created = ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS
                raw_value = raw.value if hasattr(raw, "value") else int(raw)
                if raw_value in (-1, ctypes.c_void_p(-1).value):
                    return False
                try:
                    fd = __import__("msvcrt").open_osfhandle(raw_value, os.O_RDWR)
                    self._handle = os.fdopen(fd, "r+", encoding="utf-8")
                except Exception:
                    kernel32.CloseHandle(raw_value)
                    raise
                self._created_by_handle = created
                return True
            except OSError:
                return False
        import fcntl
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    def _unlock_os(self) -> None:
        if self._handle is None:
            return
        if os.name == "nt":
            return
        else:
            import fcntl
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)

    def _publish(self, state: str) -> bool:
        if not self.publish_owner:
            return True
        try:
            self._handle.seek(0)
            self._handle.truncate()
            json.dump({"version": 1, "state": state, "token": self.token},
                      self._handle, sort_keys=True)
            self._handle.flush()
            os.fsync(self._handle.fileno())
            return True
        except OSError:
            return False

    def acquire(self, *, timeout: Optional[float] = None,
                binding: Optional[LedgerPathBinding] = None) -> AcquireResult:
        if self._owned:
            return AcquireResult(AcquireStatus.WAIT_FAILED, "nested acquisition")
        timeout = 5.0 if timeout is None else float(timeout)
        if timeout < 0:
            return AcquireResult(AcquireStatus.WAIT_FAILED, "negative timeout")
        actual_binding = self._binding_snapshot()
        if (actual_binding is None
                or (binding is not None and binding != actual_binding)):
            return AcquireResult(AcquireStatus.UNKNOWN, "lock binding changed or is invalid")
        binding = actual_binding if binding is None else binding
        sidecar_path = binding.sidecar_path
        deadline = time.monotonic() + timeout
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        if self.before_open_signal is not None:
            try:
                self.before_open_signal.write_text("ready", encoding="utf-8")
                if self.before_open_release is not None:
                    while (not self.before_open_release.exists()
                           and time.monotonic() < deadline):
                        time.sleep(self.poll_interval)
                    if not self.before_open_release.exists():
                        return AcquireResult(
                            AcquireStatus.WAIT_FAILED,
                            "before-open test gate timed out",
                        )
            except OSError as exc:
                return AcquireResult(AcquireStatus.WAIT_FAILED, str(exc))
        if os.name != "nt":
            try:
                try:
                    fd = os.open(
                        str(sidecar_path), os.O_CREAT | os.O_EXCL | os.O_RDWR,
                    )
                    self._created_by_handle = True
                except FileExistsError:
                    fd = os.open(str(sidecar_path), os.O_RDWR)
                    self._created_by_handle = False
                self._handle = os.fdopen(fd, "r+", encoding="utf-8")
            except OSError as exc:
                return AcquireResult(AcquireStatus.WAIT_FAILED, str(exc))
        while True:
            try:
                if self._binding_snapshot() != binding:
                    if self._handle is not None:
                        self._handle.close()
                        self._handle = None
                    return AcquireResult(
                        AcquireStatus.UNKNOWN,
                        "lock binding changed before acquisition",
                    )
                acquired = self._try_os_lock(sidecar_path)
                if not acquired and self.contention_event is not None:
                    self.contention_event.set()
                if acquired:
                    if self._binding_snapshot() != binding:
                        self._unlock_os()
                        self._handle.close()
                        self._handle = None
                        return AcquireResult(
                            AcquireStatus.UNKNOWN,
                            "lock binding changed after acquisition",
                        )
                    prior = self._read_owner()
                    if self._created_by_handle and prior is None:
                        status = AcquireStatus.ACQUIRED
                    else:
                        if (isinstance(prior, dict)
                                and prior.get("version") == 1
                                and isinstance(prior.get("state"), str)
                                and prior.get("state") in {"released", "held"}
                                and isinstance(prior.get("token"), str)
                                and bool(prior.get("token"))):
                            status = (AcquireStatus.ACQUIRED
                                      if prior["state"] == "released"
                                      else AcquireStatus.ABANDONED)
                        else:
                            self._unlock_os()
                            self._handle.close()
                            self._handle = None
                            return AcquireResult(
                                AcquireStatus.UNKNOWN,
                                "owner metadata missing or damaged",
                            )
                    if not self._publish("held"):
                        self._unlock_os()
                        self._handle.close()
                        self._handle = None
                        return AcquireResult(AcquireStatus.UNKNOWN, "owner metadata write failed")
                    self._owned = True
                    self._held_binding = binding
                    return AcquireResult(status)
            except OSError as exc:
                if self._handle is not None and time.monotonic() >= deadline:
                    self._handle.close()
                    self._handle = None
                    return AcquireResult(AcquireStatus.WAIT_FAILED, str(exc))
            except Exception as exc:  # pragma: no cover - defensive boundary
                if self._handle is not None:
                    self._handle.close()
                    self._handle = None
                return AcquireResult(AcquireStatus.UNKNOWN, f"{type(exc).__name__}: {exc}")
            if time.monotonic() >= deadline:
                if self._handle is not None:
                    self._handle.close()
                    self._handle = None
                return AcquireResult(AcquireStatus.TIMEOUT, "lock wait timed out")
            time.sleep(self.poll_interval)

    def release(self, *, binding: Optional[LedgerPathBinding] = None) -> ReleaseResult:
        if not self._owned:
            return ReleaseResult(ReleaseStatus.UNKNOWN, "lock is not owned")
        handle = self._handle
        snapshot = self._binding_snapshot()
        binding_valid = (
            snapshot is not None and snapshot == self._held_binding
            and (binding is None or binding == self._held_binding)
        )
        published = False
        publish_error = None
        unlock_error = None
        close_error = None
        try:
            if binding_valid:
                try:
                    published = self._publish("released")
                except BaseException as exc:
                    publish_error = exc
            try:
                self._unlock_os()
            except BaseException as exc:
                unlock_error = exc
        finally:
            try:
                if handle is None:
                    raise OSError("owned lock has no handle")
                handle.close()
            except BaseException as exc:
                close_error = exc
            self._handle = None
            self._owned = False
            self._held_binding = None
        if publish_error is not None or unlock_error is not None or close_error is not None:
            details = []
            if publish_error is not None:
                details.append(
                    f"publish {type(publish_error).__name__}: {publish_error}"
                )
            if unlock_error is not None:
                details.append(
                    f"unlock {type(unlock_error).__name__}: {unlock_error}"
                )
            if close_error is not None:
                details.append(
                    f"close {type(close_error).__name__}: {close_error}"
                )
            errors = tuple(error for error in (publish_error, unlock_error, close_error)
                           if error is not None)
            return ReleaseResult(ReleaseStatus.FAILED, "; ".join(details), errors)
        if not binding_valid:
            return ReleaseResult(ReleaseStatus.UNKNOWN, "lock binding changed while owned")
        if not published:
            return ReleaseResult(ReleaseStatus.FAILED, "owner metadata release failed")
        return ReleaseResult(ReleaseStatus.RELEASED)
