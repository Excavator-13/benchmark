"""Fail-closed verification for parsed ConfigSnapshotCandidate envelopes."""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .config_snapshot_candidate_parser import (
    CandidateParseError,
    ParsedEnvelope,
    parse_envelope,
)


class CandidateVerificationError(ValueError):
    """A sanitized candidate verification failure."""

    def __init__(self, code: str, field_path: str = "/") -> None:
        self.code = code
        self.field_path = field_path
        super().__init__(f"{code} at {field_path or '/'}")


class _VerificationFailure(Exception):
    def __init__(self, code: str, field_path: str = "/") -> None:
        self.code = code
        self.field_path = field_path


@dataclass(frozen=True, slots=True)
class CandidateVerificationSnapshot:
    """Immutable verified envelope and decoded provider payload snapshot."""

    envelope: Mapping[str, Any]
    payload: Mapping[str, Any]
    payload_bytes: bytes
    raw_envelope: bytes


_ENVELOPE_FIELDS = {
    "payload",
    "provider_id",
    "revision",
    "digest",
    "validity",
    "source_identity_claim",
    "revocation",
    "attestation",
}
_DIGEST_FIELDS = {"algorithm", "value"}
_VALIDITY_FIELDS = {"not_before", "expires_at"}
_REVOCATION_FIELDS = {
    "status",
    "checked_at",
    "valid_until",
    "authority_identity_claim",
    "proof",
}
_PAYLOAD_FIELDS = {"schema_version", "provider_id", "target", "ledger", "mutex", "acl", "wait"}
_TARGET_FIELDS = {"host_identity", "service_sid"}
_LEDGER_FIELDS = {"path"}
_MUTEX_FIELDS = {"name", "scope"}
_ACL_FIELDS = {"ledger", "mutex"}
_ACL_POLICY_FIELDS = {"owner_sid", "inheritance_enabled", "entries"}
_ACL_ENTRY_FIELDS = {"sid", "access", "rights"}
_WAIT_STRATEGIES = {"fail_fast", "bounded_poll"}
_VALIDATORS = (
    "attestation",
    "revocation",
    "host_identity",
    "sid",
    "acl",
    "path",
    "mutex",
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _fail(code: str, field_path: str = "/") -> None:
    raise _VerificationFailure(code)


def _object(value: Any, fields: set[str], code: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        _fail(code)


def _string_fields(value: Mapping[str, Any], fields: tuple[str, ...], code: str) -> None:
    if any(not isinstance(value[field], str) for field in fields):
        _fail(code)


def _validate_acl_policy(value: Any, code: str) -> None:
    _object(value, _ACL_POLICY_FIELDS, code)
    if not isinstance(value["owner_sid"], str):
        _fail(code)
    if not isinstance(value["inheritance_enabled"], bool):
        _fail(code)
    entries = value["entries"]
    if not isinstance(entries, list):
        _fail(code)
    for entry in entries:
        _object(entry, _ACL_ENTRY_FIELDS, code)
        if not isinstance(entry["sid"], str):
            _fail(code)
        if not isinstance(entry["access"], str) or entry["access"] not in {"allow", "deny"}:
            _fail(code)
        rights = entry["rights"]
        if not isinstance(rights, list) or any(not isinstance(right, str) for right in rights):
            _fail(code)


def _validate_wait(value: Any) -> None:
    if not isinstance(value, dict) or not isinstance(value.get("strategy"), str):
        _fail("invalid_wait")
    if value["strategy"] not in _WAIT_STRATEGIES:
        _fail("invalid_wait")
    strategy = value["strategy"]
    if strategy == "fail_fast":
        _object(value, {"strategy"}, "invalid_wait")
        return
    _object(value, {"strategy", "timeout_ms", "poll_interval_ms"}, "invalid_wait")
    timeout_ms = value["timeout_ms"]
    poll_interval_ms = value["poll_interval_ms"]
    if (
        isinstance(timeout_ms, bool)
        or not isinstance(timeout_ms, int)
        or timeout_ms <= 0
        or isinstance(poll_interval_ms, bool)
        or not isinstance(poll_interval_ms, int)
        or poll_interval_ms <= 0
        or poll_interval_ms > timeout_ms
    ):
        _fail("invalid_wait")


def _identity_claim(value: Any, code: str) -> None:
    if not isinstance(value, dict) or not value:
        _fail(code)
    if not all(isinstance(key, str) for key in value):
        _fail(code)


def _timestamp(value: Any, code: str) -> datetime:
    try:
        if not isinstance(value, str):
            _fail(code)
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            _fail(code)
        return parsed.astimezone(timezone.utc)
    except Exception:
        _fail(code)


def _utc_now(value: Any) -> datetime:
    try:
        if type(value) is not datetime or type(value.tzinfo) is not timezone:
            _fail("invalid_validation_clock")
        utc_value = value.astimezone(timezone.utc)
        return datetime(
            utc_value.year,
            utc_value.month,
            utc_value.day,
            utc_value.hour,
            utc_value.minute,
            utc_value.second,
            utc_value.microsecond,
            tzinfo=timezone.utc,
        )
    except Exception:
        _fail("invalid_validation_clock")


def _copy_context_value(value: Any, active_containers: set[int]) -> Any:
    value_type = type(value)
    if (
        value is None
        or value_type is bool
        or value_type is int
        or value_type is float
        or value_type is str
        or value_type is bytes
    ):
        return value

    if value_type is dict:
        identity = id(value)
        if identity in active_containers:
            _fail("invalid_validation_context")
        active_containers.add(identity)
        copied = {}
        for key, child in value.items():
            if type(key) is not str:
                _fail("invalid_validation_context")
            copied[key] = _copy_context_value(child, active_containers)
        active_containers.remove(identity)
        return copied

    if value_type is list or value_type is tuple:
        identity = id(value)
        if identity in active_containers:
            _fail("invalid_validation_context")
        active_containers.add(identity)
        copied_items = [
            _copy_context_value(child, active_containers) for child in value
        ]
        active_containers.remove(identity)
        return copied_items if value_type is list else tuple(copied_items)

    _fail("invalid_validation_context")


def _capture_validation_context(value: Any) -> tuple[dict[str, Any], datetime]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        _fail("invalid_validation_context")
    if "now" not in value:
        _fail("invalid_validation_clock")

    active_containers = {id(value)}
    context_snapshot = {}
    for key, child in value.items():
        if key == "now":
            now = _utc_now(child)
            context_snapshot[key] = now
        else:
            context_snapshot[key] = _copy_context_value(child, active_containers)
    return context_snapshot, now


def _copy_callback_context(context_snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        if key == "now"
        else _copy_context_value(value, set())
        for key, value in context_snapshot.items()
    }


def _decode_canonical_base64(value: Any, code: str) -> bytes:
    if not isinstance(value, str) or not value:
        _fail(code)
    try:
        encoded = value.encode("ascii")
        decoded = base64.b64decode(encoded, validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError):
        _fail(code)
    if not decoded or base64.b64encode(decoded).decode("ascii") != value:
        _fail(code)
    return decoded


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _verify_candidate(
    parsed: ParsedEnvelope,
    validators: Mapping[str, Callable[[ParsedEnvelope, Mapping[str, Any]], Any]],
    validation_context: dict[str, Any],
) -> CandidateVerificationSnapshot:
    """Check the approved envelope and payload bytes before injected policies."""
    context_snapshot, now = _capture_validation_context(validation_context)

    if not isinstance(parsed, ParsedEnvelope) or not isinstance(parsed.raw_envelope, bytes):
        _fail("invalid_parsed_envelope")
    raw_envelope = memoryview(parsed.raw_envelope).tobytes()
    authoritative = parse_envelope(raw_envelope)
    candidate = authoritative.value
    _object(candidate, _ENVELOPE_FIELDS, "invalid_envelope_fields")

    provider_id = candidate["provider_id"]
    revision = candidate["revision"]
    if provider_id != "P02/T006" or not isinstance(provider_id, str):
        _fail("invalid_provider_id")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        _fail("invalid_revision")

    _object(candidate["digest"], _DIGEST_FIELDS, "invalid_digest")
    digest = candidate["digest"]
    if digest["algorithm"] != "sha256":
        _fail("invalid_digest_algorithm")
    if not isinstance(digest["value"], str) or _SHA256_RE.fullmatch(digest["value"]) is None:
        _fail("invalid_digest_value")

    _object(candidate["validity"], _VALIDITY_FIELDS, "invalid_validity")
    not_before = _timestamp(candidate["validity"]["not_before"], "invalid_validity")
    expires_at = _timestamp(candidate["validity"]["expires_at"], "invalid_validity")
    if not_before >= expires_at:
        _fail("invalid_validity")
    if now < not_before or now >= expires_at:
        _fail("candidate_outside_validity")

    _identity_claim(candidate["source_identity_claim"], "invalid_source_identity_claim")
    _object(candidate["revocation"], _REVOCATION_FIELDS, "invalid_revocation")
    revocation = candidate["revocation"]
    if not isinstance(revocation["status"], str) or not revocation["status"]:
        _fail("invalid_revocation_status")
    checked_at = _timestamp(revocation["checked_at"], "invalid_revocation")
    valid_until = _timestamp(revocation["valid_until"], "invalid_revocation")
    if checked_at > now or now >= valid_until or valid_until < checked_at:
        _fail("invalid_revocation")
    _identity_claim(revocation["authority_identity_claim"], "invalid_revocation_authority")
    _decode_canonical_base64(revocation["proof"], "invalid_revocation_proof")
    _decode_canonical_base64(candidate["attestation"], "invalid_attestation")
    payload_bytes = _decode_canonical_base64(candidate["payload"], "invalid_payload_base64")

    actual_digest = hashlib.sha256(payload_bytes).hexdigest()
    if actual_digest != digest["value"]:
        _fail("payload_digest_mismatch")

    try:
        payload_parsed = parse_envelope(payload_bytes)
    except Exception:
        _fail("invalid_provider_payload_json")
    payload = payload_parsed.value
    _object(payload, _PAYLOAD_FIELDS, "invalid_provider_payload_fields")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        _fail("invalid_provider_schema_version")
    if payload["provider_id"] != "P02/T006" or payload["provider_id"] != provider_id:
        _fail("provider_id_mismatch")
    _object(payload["target"], _TARGET_FIELDS, "invalid_target")
    _string_fields(payload["target"], ("host_identity", "service_sid"), "invalid_target")
    _object(payload["ledger"], _LEDGER_FIELDS, "invalid_ledger")
    _string_fields(payload["ledger"], ("path",), "invalid_ledger")
    _object(payload["mutex"], _MUTEX_FIELDS, "invalid_mutex")
    _string_fields(payload["mutex"], ("name", "scope"), "invalid_mutex")
    _object(payload["acl"], _ACL_FIELDS, "invalid_acl")
    _validate_acl_policy(payload["acl"]["ledger"], "invalid_acl_policy")
    _validate_acl_policy(payload["acl"]["mutex"], "invalid_acl_policy")
    _validate_wait(payload["wait"])

    if not isinstance(validators, Mapping):
        _fail("validators_unavailable")
    for name in _VALIDATORS:
        validator = validators.get(name)
        if not callable(validator):
            _fail("validator_unavailable")
        validator_input = ParsedEnvelope(
            value=copy.deepcopy(authoritative.value),
            raw_envelope=authoritative.raw_envelope,
            payload_raw_bytes=authoritative.payload_raw_bytes,
        )
        validator_context = _copy_callback_context(context_snapshot)
        try:
            accepted = validator(validator_input, validator_context)
        except Exception:
            _fail("validator_failed")
        if accepted is not True:
            _fail("validator_failed")

    return CandidateVerificationSnapshot(
        envelope=_freeze(authoritative.value),
        payload=_freeze(payload),
        payload_bytes=payload_bytes,
        raw_envelope=authoritative.raw_envelope,
    )


def _raise_public_error(code: str, field_path: str) -> None:
    try:
        raise CandidateVerificationError(code, field_path) from None
    except CandidateVerificationError as error:
        error.__cause__ = None
        error.__context__ = None
        error.__suppress_context__ = True
        raise


def validate_candidate(
    parsed: ParsedEnvelope,
    validators: Mapping[str, Callable[[ParsedEnvelope, Mapping[str, Any]], Any]],
    validation_context: dict[str, Any],
) -> CandidateVerificationSnapshot:
    """Verify using an isolated raw-byte parse and expose sanitized failures.

    ``validation_context`` must be an exact built-in ``dict`` with built-in
    ``str`` keys. Its ``now`` value must be an exact built-in ``datetime``
    using an exact ``datetime.timezone`` instance. Other values may only be
    exact built-in ``None``, ``bool``, ``int``, ``float``, ``str``, ``bytes``,
    ``dict``, ``list`` or ``tuple`` values, with built-in string keys in every
    nested dictionary. Cyclic containers are rejected. Errors sanitize
    verifier frames and exception chains, but cannot clear data held in
    caller-owned traceback frames.
    """
    try:
        snapshot = _verify_candidate(parsed, validators, validation_context)
    except _VerificationFailure as failure:
        code, field_path = failure.code, failure.field_path
    except CandidateParseError:
        code, field_path = "invalid_envelope", "/"
    except Exception:
        code, field_path = "verification_failed", "/"
    else:
        return snapshot

    del parsed, validators, validation_context
    _raise_public_error(code, field_path)
