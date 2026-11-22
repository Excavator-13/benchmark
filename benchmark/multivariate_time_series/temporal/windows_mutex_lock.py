"""Pure wait helpers for the Windows mutex backend."""

from __future__ import annotations

from math import isfinite

from .ledger_lock import AcquireStatus


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
