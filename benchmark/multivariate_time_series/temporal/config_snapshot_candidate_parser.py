"""Strict JSON parsing primitives for ConfigSnapshotCandidate envelopes."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


_JSON_WHITESPACE = " \t\r\n"
_MAX_INTEGER_DIGITS = 4300
# Each conversion stays below Python's minimum configurable digit limit.
_INTEGER_CHUNK_DIGITS = 500


class CandidateParseError(ValueError):
    """An input-safe error with a path of zero-based member or array indices."""

    def __init__(self, code: str, field_path: str = "") -> None:
        self.code = code
        self.field_path = field_path
        location = field_path or "/"
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class ParsedEnvelope:
    """Parsed envelope plus the exact source bytes needed by later validators."""

    value: dict[str, Any]
    raw_envelope: bytes
    payload_raw_bytes: bytes | None


@dataclass(frozen=True)
class _ObjectPairs:
    pairs: list[tuple[str, Any]]


def parse_envelope(raw_envelope: bytes) -> ParsedEnvelope:
    """Parse one strict UTF-8 JSON object without losing source payload bytes."""

    field_path = ""
    try:
        return _parse_envelope(raw_envelope)
    except CandidateParseError as error:
        code, field_path = error.code, error.field_path
    except UnicodeDecodeError:
        code = "invalid_utf8"
    except (ValueError, TypeError):
        code = "invalid_json"
    except RecursionError:
        code = "nesting_too_deep"

    # The initial raise can inherit the caller's active exception. Clear that
    # implicit context before a bare re-raise propagates the sanitized error.
    del raw_envelope
    try:
        raise CandidateParseError(code, field_path) from None
    except CandidateParseError as error:
        error.__context__ = None
        raise


def _parse_envelope(raw_envelope: bytes) -> ParsedEnvelope:
    if not isinstance(raw_envelope, bytes):
        raise CandidateParseError("invalid_input_type")
    if bytes.startswith(raw_envelope, b"\xef\xbb\xbf"):
        raise CandidateParseError("utf8_bom")

    source = bytes.decode(raw_envelope, "utf-8", errors="strict")
    decoder = json.JSONDecoder(
        object_pairs_hook=_ObjectPairs,
        parse_constant=_reject_non_standard_number,
        parse_float=_parse_finite_float,
        parse_int=_parse_integer,
    )
    start = _skip_whitespace(source, 0)
    parsed, end = decoder.raw_decode(source, start)

    if _skip_whitespace(source, end) != len(source):
        raise CandidateParseError("trailing_content")
    if not isinstance(parsed, _ObjectPairs):
        raise CandidateParseError("non_object_root")

    _check_duplicate_keys(parsed, "")
    value = _fold_objects(parsed)
    payload_span = _top_level_member_span(source, start, "payload")
    payload_raw_bytes = None
    if payload_span is not None:
        payload_start, payload_end = payload_span
        payload_raw_bytes = source[payload_start:payload_end].encode("utf-8")

    return ParsedEnvelope(
        value=value,
        raw_envelope=raw_envelope,
        payload_raw_bytes=payload_raw_bytes,
    )


def _reject_non_standard_number(value: str) -> None:
    raise CandidateParseError("non_standard_number")


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise CandidateParseError("non_finite_number")
    return parsed


def _parse_integer(value: str) -> int:
    negative = value.startswith("-")
    digit_start = 1 if negative else 0
    digit_count = len(value) - digit_start
    if digit_count > _MAX_INTEGER_DIGITS:
        raise CandidateParseError("integer_too_long")
    if digit_count <= _INTEGER_CHUNK_DIGITS:
        return int(value)

    parsed = 0
    for start in range(digit_start, len(value), _INTEGER_CHUNK_DIGITS):
        chunk = value[start : start + _INTEGER_CHUNK_DIGITS]
        parsed = parsed * 10 ** len(chunk) + int(chunk)
    return -parsed if negative else parsed


def _check_duplicate_keys(value: Any, path: str) -> None:
    if isinstance(value, _ObjectPairs):
        seen: set[str] = set()
        for index, (key, child) in enumerate(value.pairs):
            child_path = f"{path}/{index}"
            if key in seen:
                raise CandidateParseError("duplicate_key", child_path)
            seen.add(key)
            _check_duplicate_keys(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_duplicate_keys(child, f"{path}/{index}")


def _fold_objects(value: Any) -> Any:
    if isinstance(value, _ObjectPairs):
        return {key: _fold_objects(child) for key, child in value.pairs}
    if isinstance(value, list):
        return [_fold_objects(child) for child in value]
    return value


def _top_level_member_span(
    source: str, object_start: int, member_name: str
) -> tuple[int, int] | None:
    position = _skip_whitespace(source, object_start + 1)
    if source[position] == "}":
        return None

    while True:
        key_start = position
        key_end = _scan_string(source, key_start)
        key = json.loads(source[key_start:key_end])
        position = _skip_whitespace(source, key_end)
        position = _skip_whitespace(source, position + 1)  # colon
        value_start = position
        value_end = _scan_value(source, value_start)
        if key == member_name:
            return value_start, value_end

        position = _skip_whitespace(source, value_end)
        if source[position] == "}":
            return None
        position = _skip_whitespace(source, position + 1)  # comma


def _scan_value(source: str, start: int) -> int:
    first = source[start]
    if first == '"':
        return _scan_string(source, start)
    if first == "{":
        position = _skip_whitespace(source, start + 1)
        if source[position] == "}":
            return position + 1
        while True:
            key_end = _scan_string(source, position)
            position = _skip_whitespace(source, key_end)
            position = _skip_whitespace(source, position + 1)  # colon
            position = _skip_whitespace(source, _scan_value(source, position))
            if source[position] == "}":
                return position + 1
            position = _skip_whitespace(source, position + 1)  # comma
    if first == "[":
        position = _skip_whitespace(source, start + 1)
        if source[position] == "]":
            return position + 1
        while True:
            position = _skip_whitespace(source, _scan_value(source, position))
            if source[position] == "]":
                return position + 1
            position = _skip_whitespace(source, position + 1)  # comma
    position = start
    while position < len(source) and source[position] not in ",]}" + _JSON_WHITESPACE:
        position += 1
    return position


def _scan_string(source: str, start: int) -> int:
    position = start + 1
    while position < len(source):
        character = source[position]
        if character == "\\":
            position += 2
            continue
        if character == '"':
            return position + 1
        position += 1
    return len(source)


def _skip_whitespace(source: str, position: int) -> int:
    while position < len(source) and source[position] in _JSON_WHITESPACE:
        position += 1
    return position
