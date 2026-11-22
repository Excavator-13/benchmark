"""Verify an explicitly supplied deployment candidate in memory."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from .config_snapshot_candidate_parser import ParsedEnvelope, parse_envelope
from .config_snapshot_candidate_verifier import (
    CandidateVerificationSnapshot,
    validate_candidate,
)
from .ledger_lock import require_deployment_config


class CandidateAdapterError(ValueError):
    """A deployment candidate failure identified by its stage code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _verify(
    provider: Callable[[], bytes | None] | None,
    validators: Mapping[str, Callable[[ParsedEnvelope, Mapping[str, Any]], Any]],
    validation_context: dict[str, Any],
) -> CandidateVerificationSnapshot | CandidateAdapterError:
    if provider is None:
        return CandidateAdapterError("provider_missing")

    # Box the result so a returned None can be classified separately from a
    # provider exception without inspecting the gate's exception.
    try:
        (raw_envelope,) = require_deployment_config(lambda: (provider(),))
    except Exception:
        return CandidateAdapterError("provider_failed")
    if raw_envelope is None:
        return CandidateAdapterError("provider_missing")
    if type(raw_envelope) is not bytes:
        return CandidateAdapterError("invalid_provider_result")

    try:
        parsed = parse_envelope(raw_envelope)
    except Exception:
        return CandidateAdapterError("parse_failed")

    try:
        return validate_candidate(parsed, validators, validation_context)
    except Exception:
        return CandidateAdapterError("verification_failed")


def verify_deployment_candidate(
    provider: Callable[[], bytes | None] | None,
    validators: Mapping[str, Callable[[ParsedEnvelope, Mapping[str, Any]], Any]],
    validation_context: dict[str, Any],
) -> CandidateVerificationSnapshot:
    """Return the immutable verification snapshot without granting permissions.

    Public failures omit internal input frames and exception chains. The
    caller's own traceback frames are outside this cleanup boundary.
    """
    result = _verify(provider, validators, validation_context)
    if not isinstance(result, CandidateAdapterError):
        return result

    del provider, validators, validation_context
    try:
        raise result from None
    except CandidateAdapterError:
        # A caller handling an exception can still supply implicit context.
        result.__context__ = None
        raise
