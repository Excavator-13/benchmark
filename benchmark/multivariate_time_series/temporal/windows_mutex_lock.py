"""Pure status mapping helpers for the Windows mutex backend."""

from __future__ import annotations

from .ledger_lock import AcquireStatus


_WAIT_OBJECT_0 = 0x00000000
_WAIT_ABANDONED = 0x00000080
_WAIT_TIMEOUT = 0x00000102
_WAIT_FAILED = 0xFFFFFFFF


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
