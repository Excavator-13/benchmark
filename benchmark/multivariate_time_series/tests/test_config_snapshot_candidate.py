import sys
import base64
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone, tzinfo
from unittest.mock import patch

from benchmark.multivariate_time_series.temporal import config_snapshot_candidate_parser
from benchmark.multivariate_time_series.temporal.config_snapshot_candidate_parser import (
    CandidateParseError,
    ParsedEnvelope,
    parse_envelope,
)
from benchmark.multivariate_time_series.temporal.config_snapshot_candidate_verifier import (
    CandidateVerificationError,
    validate_candidate,
)
from benchmark.multivariate_time_series.temporal import config_snapshot_candidate_verifier


class ConfigSnapshotCandidateParserTests(unittest.TestCase):
    def assert_parse_error(
        self, raw: bytes, code: str, field_path: str = ""
    ) -> None:
        with self.assertRaises(CandidateParseError) as caught:
            parse_envelope(raw)

        self.assert_safe_parse_error(caught.exception, code, field_path)

    def assert_safe_parse_error(
        self, error: CandidateParseError, code: str, field_path: str = ""
    ) -> None:
        self.assertEqual(vars(error), {"code": code, "field_path": field_path})
        self.assertEqual(error.args, (f"{code} at {field_path or '/'}",))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)

    def test_rejects_invalid_utf8(self) -> None:
        self.assert_parse_error(b'{"payload":"\xff"}', "invalid_utf8")

    def test_rejects_bom_trailing_content_and_non_object_roots(self) -> None:
        cases = [
            (b"\xef\xbb\xbf{}", "utf8_bom"),
            (b"{} {}", "trailing_content"),
            (b"[]", "non_object_root"),
            (b"null", "non_object_root"),
        ]
        for raw, code in cases:
            with self.subTest(raw=raw):
                self.assert_parse_error(raw, code)

    def test_accepts_each_ascii_json_whitespace_at_document_boundaries(self) -> None:
        for whitespace in (b" ", b"\t", b"\n", b"\r"):
            with self.subTest(whitespace=whitespace):
                raw = whitespace + b'{"payload": 42}' + whitespace
                parsed = parse_envelope(raw)
                self.assertEqual(parsed.value, {"payload": 42})
                self.assertIs(parsed.raw_envelope, raw)
                self.assertEqual(parsed.payload_raw_bytes, b"42")

    def test_rejects_other_whitespace_at_document_boundaries(self) -> None:
        for whitespace in ("\x0b", "\x0c", "\x1c", "\x85", "\xa0", "\u2003", "\u2028"):
            with self.subTest(whitespace=whitespace):
                encoded = whitespace.encode("utf-8")
                self.assert_parse_error(b" \t" + encoded + b"{}", "invalid_json")
                self.assert_parse_error(b"{}\r\n" + encoded, "trailing_content")

    def test_rejects_duplicate_decoded_keys_before_mapping_fold(self) -> None:
        cases = [
            (b'{"x":1,"x":2}', "/1"),
            (b'{"outer":{"x":1,"x":2}}', "/0/1"),
            (b'{"outer":[null,{"x":1,"x":2}]}', "/0/1/1"),
            (b'{"x":1,"\\u0078":2}', "/1"),
            (b'{"outer":{"x":1,"\\u0078":2}}', "/0/1"),
            ('{"outer":[{"📦":1,"\\ud83d\\udce6":2}]}'.encode("utf-8"), "/0/0/1"),
        ]
        with patch.object(config_snapshot_candidate_parser, "_fold_objects") as fold:
            for raw, field_path in cases:
                with self.subTest(raw=raw):
                    self.assert_parse_error(raw, "duplicate_key", field_path)
            fold.assert_not_called()

    def test_rejects_non_standard_or_non_finite_numbers(self) -> None:
        cases = [
            (b"NaN", "non_standard_number"),
            (b"Infinity", "non_standard_number"),
            (b"-Infinity", "non_standard_number"),
            (b"1e999", "non_finite_number"),
            (b"-1e999", "non_finite_number"),
        ]
        for number, code in cases:
            with self.subTest(number=number):
                self.assert_parse_error(b'{"number":' + number + b"}", code)

    def test_normalizes_oversized_integer(self) -> None:
        self.addCleanup(sys.set_int_max_str_digits, sys.get_int_max_str_digits())
        digits = b"1" * 4301
        for interpreter_limit in (0, sys.int_info.str_digits_check_threshold, 5000):
            sys.set_int_max_str_digits(interpreter_limit)
            for sign in (b"", b"-"):
                with self.subTest(interpreter_limit=interpreter_limit, sign=sign):
                    self.assert_parse_error(
                        b'{"payload":' + sign + digits + b"}", "integer_too_long"
                    )

    def test_accepts_integers_at_parser_limit(self) -> None:
        self.addCleanup(sys.set_int_max_str_digits, sys.get_int_max_str_digits())
        digits = b"9" * 4300
        magnitude = 10**4300 - 1
        for interpreter_limit in (0, sys.int_info.str_digits_check_threshold):
            sys.set_int_max_str_digits(interpreter_limit)
            for sign, expected in ((b"", magnitude), (b"-", -magnitude)):
                with self.subTest(interpreter_limit=interpreter_limit, sign=sign):
                    token = sign + digits
                    parsed = parse_envelope(b'{"payload":' + token + b"}")
                    self.assertEqual(parsed.value["payload"], expected)
                    self.assertEqual(parsed.payload_raw_bytes, token)

    def test_normalizes_excessive_nesting(self) -> None:
        depth = sys.getrecursionlimit() + 1
        raw = b'{"payload":' + b"[" * depth + b"0" + b"]" * depth + b"}"
        self.assert_parse_error(raw, "nesting_too_deep")

    def test_errors_do_not_carry_original_input(self) -> None:
        cases = [
            (b'{"payload": {"private-key": "private-value\xff"}}', "invalid_utf8", ""),
            (b'{"payload": {"private-key": "private-value",}}', "invalid_json", ""),
            (
                b'{"payload": {"private-key":"private-value","private-key":"other"}}',
                "duplicate_key",
                "/0/1",
            ),
        ]
        for raw, code, field_path in cases:
            with self.subTest(code=code):
                self.assert_parse_error(raw, code, field_path)

    def test_isolates_errors_during_caller_exception_handling(self) -> None:
        cases = [
            (b'{"payload":{"private-key":"private-value\xff"}}', "invalid_utf8", ""),
            (b'{"payload":{"private-key":"private-value",}}', "invalid_json", ""),
            (b'{"private-key":"private-value","private-key":0}', "duplicate_key", "/1"),
        ]
        for raw, code, field_path in cases:
            with self.subTest(code=code):
                caller_error = RuntimeError("caller failure")
                try:
                    raise caller_error
                except RuntimeError:
                    try:
                        parse_envelope(raw)
                    except CandidateParseError as error:
                        self.assert_safe_parse_error(error, code, field_path)
                        parser_frame = error.__traceback__.tb_next
                        self.assertIs(parser_frame.tb_frame.f_code, parse_envelope.__code__)
                        self.assertEqual(
                            parser_frame.tb_frame.f_locals,
                            {"code": code, "field_path": field_path},
                        )
                        self.assertIsNone(parser_frame.tb_next)
                    else:
                        self.fail("Expected CandidateParseError")
                    self.assertIs(sys.exception(), caller_error)

    def test_normalizes_internal_value_and_type_errors(self) -> None:
        raw = b'{"payload":"private-value"}'
        for error_type in (ValueError, TypeError):
            with self.subTest(error=error_type.__name__):
                with patch.object(
                    config_snapshot_candidate_parser,
                    "_top_level_member_span",
                    side_effect=error_type(raw),
                ):
                    self.assert_parse_error(raw, "invalid_json")

    def test_parses_one_document_and_preserves_exact_payload_source_bytes(self) -> None:
        raw = b' \n {"schema_version":1,"payload": { "x" : [1, 2] }} \t\r\n'

        parsed = parse_envelope(raw)

        self.assertEqual(
            parsed.value,
            {"schema_version": 1, "payload": {"x": [1, 2]}},
        )
        self.assertIs(parsed.raw_envelope, raw)
        self.assertEqual(parsed.payload_raw_bytes, b'{ "x" : [1, 2] }')

    def test_preserves_payload_after_multibyte_text_and_escaped_key(self) -> None:
        payload = r'{ "城市": "上海", "symbol": "\u2603", "items": ["🚀"] }'.encode("utf-8")
        prefix = r'{"说明":"编排","pay\u006coad" : '.encode("utf-8")
        raw = prefix + payload + b' ,"next":0}'

        parsed = parse_envelope(raw)

        self.assertEqual(
            parsed.value,
            {
                "说明": "编排",
                "payload": {"城市": "上海", "symbol": "☃", "items": ["🚀"]},
                "next": 0,
            },
        )
        self.assertIs(parsed.raw_envelope, raw)
        self.assertEqual(parsed.payload_raw_bytes, payload)

    def test_missing_top_level_payload_has_no_raw_token(self) -> None:
        for raw in (b"{}", b'{"outer":[{"payload":1},{"payload":2}]}'):
            with self.subTest(raw=raw):
                parsed = parse_envelope(raw)
                self.assertIs(parsed.raw_envelope, raw)
                self.assertIsNone(parsed.payload_raw_bytes)

    def test_null_payload_has_a_raw_token(self) -> None:
        parsed = parse_envelope(b'{"payload": null}')

        self.assertIsNone(parsed.value["payload"])
        self.assertEqual(parsed.payload_raw_bytes, b"null")


class ConfigSnapshotCandidateVerifierTests(unittest.TestCase):
    def payload_bytes(self):
        payload = {
            "schema_version": 1,
            "provider_id": "P02/T006",
            "target": {"host_identity": "synthetic-host", "service_sid": "synthetic-sid"},
            "ledger": {"path": "synthetic-ledger-path"},
            "mutex": {"name": "synthetic-mutex", "scope": "synthetic-scope"},
            "acl": {
                "ledger": {
                    "owner_sid": "synthetic-owner",
                    "inheritance_enabled": False,
                    "entries": [
                        {"sid": "synthetic-sid", "access": "allow", "rights": ["read"]}
                    ],
                },
                "mutex": {
                    "owner_sid": "synthetic-owner",
                    "inheritance_enabled": True,
                    "entries": [],
                },
            },
            "wait": {"strategy": "fail_fast"},
        }
        return json.dumps(payload, separators=(",", ":")).encode()

    def payload_value(self):
        return json.loads(self.payload_bytes())

    def encoded_payload(self, payload):
        return json.dumps(payload, separators=(",", ":")).encode()

    def envelope(self, payload_bytes=None, **changes):
        if payload_bytes is None:
            payload_bytes = self.payload_bytes()
        candidate = {
            "payload": base64.b64encode(payload_bytes).decode("ascii"),
            "provider_id": "P02/T006",
            "revision": 3,
            "digest": {
                "algorithm": "sha256",
                "value": hashlib.sha256(payload_bytes).hexdigest(),
            },
            "validity": {
                "not_before": "2026-11-01T00:00:00Z",
                "expires_at": "2026-12-01T00:00:00Z",
            },
            "source_identity_claim": {"host": "synthetic-host"},
            "revocation": {
                "status": "clear",
                "checked_at": "2026-11-14T00:00:00Z",
                "valid_until": "2026-11-16T00:00:00Z",
                "authority_identity_claim": {"authority": "test"},
                "proof": base64.b64encode(b"proof").decode("ascii"),
            },
            "attestation": base64.b64encode(b"attestation").decode("ascii"),
        }
        candidate.update(changes)
        return parse_envelope(json.dumps(candidate, separators=(",", ":")).encode())

    def validators(self, result=True, calls=None):
        def check(_parsed, _context):
            if calls is not None:
                calls.append("called")
            return result

        return {
            name: check
            for name in (
                "attestation", "revocation", "host_identity", "sid", "acl", "path", "mutex"
            )
        }

    def context(self):
        return {"now": datetime(2026, 11, 15, tzinfo=timezone.utc)}

    def test_accepts_exact_approved_envelope_and_payload_fields(self):
        calls = []
        parsed = self.envelope()

        result = validate_candidate(parsed, self.validators(calls=calls), self.context())

        self.assertIsNot(result, parsed)
        self.assertEqual(result.payload_bytes, self.payload_bytes())
        self.assertEqual(result.payload["provider_id"], "P02/T006")
        self.assertEqual(len(calls), 7)

    def test_reparses_authoritative_raw_bytes_after_input_value_mutation(self):
        parsed = self.envelope()
        expected_payload_bytes = self.payload_bytes()
        parsed.value["digest"]["value"] = "0" * 64
        parsed.value["revocation"]["status"] = "modified-after-parse"
        parsed.value["payload"] = "not-base64"

        snapshot = validate_candidate(parsed, self.validators(), self.context())

        self.assertEqual(snapshot.payload_bytes, expected_payload_bytes)
        self.assertEqual(snapshot.payload["provider_id"], "P02/T006")
        self.assertEqual(snapshot.envelope["revocation"]["status"], "clear")

    def test_validator_mutations_do_not_reach_later_callbacks_or_snapshot(self):
        retained = []
        validator_names = (
            "attestation", "revocation", "host_identity", "sid", "acl", "path", "mutex"
        )

        def mutate_first(candidate, context):
            retained.append((candidate, context))
            if len(retained) == 1:
                candidate.value["revocation"]["status"] = "changed"
                context["nested"]["value"] = "changed"
            else:
                self.assertEqual(candidate.value["revocation"]["status"], "clear")
                self.assertEqual(context["nested"]["value"], "original")
            return True

        validators = {name: mutate_first for name in validator_names}
        validation_context = self.context()
        validation_context["nested"] = {"value": "original"}
        source = self.envelope()
        snapshot = validate_candidate(source, validators, validation_context)

        retained[0][0].value["provider_id"] = "changed-later"
        retained[0][1]["nested"]["value"] = "changed-later"
        source.value["provider_id"] = "changed-source"
        source.value["payload"] = "changed-source"
        validation_context["nested"]["value"] = "changed-source"
        self.assertEqual(snapshot.envelope["provider_id"], "P02/T006")
        self.assertEqual(snapshot.payload["provider_id"], "P02/T006")

    def test_context_is_captured_once_and_callbacks_receive_independent_snapshots(self):
        initial_now = datetime(
            2026, 11, 15, 5, 30, tzinfo=timezone(timedelta(hours=5, minutes=30))
        )
        expected_now = datetime(2026, 11, 15, tzinfo=timezone.utc)
        context = {"now": initial_now, "nested": {"values": ["initial"]}}
        observations = []
        names = (
            "attestation", "revocation", "host_identity", "sid", "acl", "path", "mutex"
        )

        def inspect_and_mutate(_candidate, callback_context):
            observations.append(
                (
                    callback_context["now"],
                    list(callback_context["nested"]["values"]),
                )
            )
            callback_context["nested"]["values"].append("callback-change")
            if len(observations) == 1:
                context["now"] = datetime(2035, 1, 1, tzinfo=timezone.utc)
                context["nested"]["values"].append("closure-change")
            return True

        validators = {name: inspect_and_mutate for name in names}
        validity = {
            "not_before": "2026-11-15T00:00:00Z",
            "expires_at": "2026-11-15T00:00:01Z",
        }
        revocation = {
            "status": "clear",
            "checked_at": "2026-11-15T00:00:00Z",
            "valid_until": "2026-11-15T00:00:00.000001Z",
            "authority_identity_claim": {"authority": "test"},
            "proof": base64.b64encode(b"proof").decode("ascii"),
        }

        validate_candidate(
            self.envelope(validity=validity, revocation=revocation),
            validators,
            context,
        )

        self.assertEqual(len(observations), len(names))
        self.assertTrue(
            all(observation == (expected_now, ["initial"]) for observation in observations)
        )
        self.assertEqual(context["now"], datetime(2035, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(context["nested"]["values"], ["initial", "closure-change"])

    def test_validation_context_rejects_custom_copy_and_callable_values_before_callbacks(self):
        deepcopy_calls = []
        callback_calls = []

        class SelfReturningCopy:
            def __deepcopy__(self, memo):
                deepcopy_calls.append("called")
                return self

        def function_value():
            return None

        function_value.mutable_attribute = []
        validators = self.validators(calls=callback_calls)
        for value in (function_value, SelfReturningCopy()):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaisesRegex(
                    CandidateVerificationError, "invalid_validation_context"
                ):
                    validate_candidate(
                        self.envelope(),
                        validators,
                        {"now": self.context()["now"], "invalid": value},
                    )
        self.assertEqual(deepcopy_calls, [])
        self.assertEqual(callback_calls, [])

    def test_validation_context_requires_exact_datetime_timezone_and_types(self):
        class DateTimeSubclass(datetime):
            pass

        class CustomTimezone(tzinfo):
            def __init__(self):
                self.calls = 0

            def utcoffset(self, dt):
                self.calls += 1
                return timedelta(0)

            def dst(self, dt):
                return timedelta(0)

        custom_timezone = CustomTimezone()
        invalid_contexts = (
            {"now": DateTimeSubclass(2026, 11, 15, tzinfo=timezone.utc)},
            {"now": datetime(2026, 11, 15, tzinfo=custom_timezone)},
        )
        for context in invalid_contexts:
            with self.subTest(now_type=type(context["now"]), timezone=type(context["now"].tzinfo)):
                with self.assertRaisesRegex(
                    CandidateVerificationError, "invalid_validation_clock"
                ):
                    validate_candidate(self.envelope(), self.validators(), context)
        self.assertEqual(custom_timezone.calls, 0)

        fixed_offset = timezone(timedelta(hours=5, minutes=30))
        context = {
            "now": datetime(2026, 11, 15, 5, 30, tzinfo=fixed_offset),
            "legal_values": (None, True, 7, 1.5, "text", b"bytes", {"nested": [1]}),
        }
        observed_now = []
        validators = {
            name: lambda _candidate, callback_context: (
                observed_now.append(callback_context["now"]) or True
            )
            for name in (
                "attestation", "revocation", "host_identity", "sid", "acl", "path", "mutex"
            )
        }
        validate_candidate(self.envelope(), validators, context)
        self.assertTrue(all(type(value) is datetime for value in observed_now))
        self.assertTrue(all(value.tzinfo is timezone.utc for value in observed_now))
        self.assertTrue(all(value is observed_now[0] for value in observed_now))

    def test_validation_context_rejects_container_cycles_and_type_subclasses(self):
        cyclic_list = []
        cyclic_list.append(cyclic_list)

        class IntSubclass(int):
            pass

        class StringSubclass(str):
            pass

        class BytesSubclass(bytes):
            pass

        class DictSubclass(dict):
            pass

        class ListSubclass(list):
            pass

        class TupleSubclass(tuple):
            pass

        class FloatSubclass(float):
            pass

        invalid_contexts = (
            {"now": self.context()["now"], "cycle": cyclic_list},
            {"now": self.context()["now"], "value": IntSubclass(1)},
            {"now": self.context()["now"], StringSubclass("key"): "value"},
            {"now": self.context()["now"], "value": StringSubclass("value")},
            {"now": self.context()["now"], "value": BytesSubclass(b"value")},
            {"now": self.context()["now"], "value": DictSubclass()},
            {"now": self.context()["now"], "value": ListSubclass()},
            {"now": self.context()["now"], "value": TupleSubclass()},
            {"now": self.context()["now"], "value": FloatSubclass(1.5)},
        )
        for context in invalid_contexts:
            with self.subTest(context_type=type(context)):
                with self.assertRaisesRegex(
                    CandidateVerificationError, "invalid_validation_context"
                ):
                    validate_candidate(self.envelope(), self.validators(), context)

        class ContextSubclass(dict):
            pass

        with self.assertRaisesRegex(
            CandidateVerificationError, "invalid_validation_context"
        ):
            validate_candidate(
                self.envelope(),
                self.validators(),
                ContextSubclass(self.context()),
            )

    def test_context_type_whitelist_uses_identity_without_custom_metaclass_calls(self):
        calls = {"hash": 0, "eq": 0, "deepcopy": 0, "validator": 0}

        class SpoofMeta(type):
            def __hash__(cls):
                calls["hash"] += 1
                return hash(int)

            def __eq__(cls, other):
                calls["eq"] += 1
                return other is int or other is float or other is str

        class SpoofedScalar(metaclass=SpoofMeta):
            def __deepcopy__(self, memo):
                calls["deepcopy"] += 1
                return self

        def callback(_candidate, _context):
            calls["validator"] += 1
            return True

        validators = {
            name: callback
            for name in (
                "attestation", "revocation", "host_identity", "sid", "acl", "path", "mutex"
            )
        }
        values = (
            {"now": self.context()["now"], "value": SpoofedScalar()},
            {
                "now": self.context()["now"],
                "nested": {"items": [SpoofedScalar()]},
            },
        )
        for context in values:
            with self.subTest(nested="nested" in context):
                with self.assertRaisesRegex(
                    CandidateVerificationError, "invalid_validation_context"
                ):
                    validate_candidate(self.envelope(), validators, context)

        self.assertEqual(calls, {"hash": 0, "eq": 0, "deepcopy": 0, "validator": 0})

    def test_revocation_valid_until_is_an_exclusive_utc_boundary(self):
        now = datetime(2026, 11, 15, tzinfo=timezone.utc)
        context = {"now": now}
        base_revocation = self.envelope().value["revocation"]
        cases = (
            ("2026-11-15T00:00:00.000001Z", True),
            ("2026-11-15T00:00:00Z", False),
            ("2026-11-14T23:59:59.999999Z", False),
            ("2026-11-15T05:30:00+05:30", False),
        )
        for valid_until, accepted in cases:
            with self.subTest(valid_until=valid_until):
                revocation = dict(base_revocation, valid_until=valid_until)
                candidate = self.envelope(revocation=revocation)
                if accepted:
                    validate_candidate(candidate, self.validators(), context)
                else:
                    with self.assertRaisesRegex(
                        CandidateVerificationError, "invalid_revocation"
                    ):
                        validate_candidate(candidate, self.validators(), context)

    def test_returned_snapshot_is_deeply_read_only_and_matches_hashed_bytes(self):
        snapshot = validate_candidate(
            self.envelope(), self.validators(), self.context()
        )

        self.assertEqual(
            hashlib.sha256(snapshot.payload_bytes).hexdigest(),
            snapshot.envelope["digest"]["value"],
        )
        self.assertEqual(
            base64.b64decode(snapshot.envelope["payload"], validate=True),
            snapshot.payload_bytes,
        )
        with self.assertRaises(TypeError):
            snapshot.payload["target"]["host_identity"] = "changed"
        with self.assertRaises(TypeError):
            snapshot.payload["acl"]["ledger"]["entries"][0]["sid"] = "changed"
        with self.assertRaises(AttributeError):
            snapshot.payload["acl"]["ledger"]["entries"].append({})

    def test_snapshot_root_has_no_instance_dictionary_or_mutable_fields(self):
        snapshot = validate_candidate(
            self.envelope(), self.validators(), self.context()
        )
        original_envelope = snapshot.envelope
        original_payload = snapshot.payload
        original_payload_bytes = snapshot.payload_bytes

        with self.assertRaises(TypeError):
            vars(snapshot)
        for field, replacement in (
            ("envelope", {}),
            ("payload", {}),
            ("payload_bytes", b"changed"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(AttributeError):
                    setattr(snapshot, field, replacement)
                with self.assertRaises(AttributeError):
                    delattr(snapshot, field)

        self.assertIs(snapshot.envelope, original_envelope)
        self.assertIs(snapshot.payload, original_payload)
        self.assertIs(snapshot.payload_bytes, original_payload_bytes)

    def test_bytes_subclass_is_copied_to_builtin_bytes_for_parser_callbacks_and_result(self):
        parsed = self.envelope()
        raw_content = parsed.raw_envelope

        class MutableBytes(bytes):
            def __new__(cls, content):
                instance = super().__new__(cls, content)
                instance.mutable_attribute = ["original"]
                return instance

            def __bytes__(self):
                return b"untrusted conversion"

        supplied_raw = MutableBytes(raw_content)
        candidate = ParsedEnvelope(
            value={"tampered": True},
            raw_envelope=supplied_raw,
            payload_raw_bytes=b"untrusted token",
        )
        callback_raw_values = []

        def inspect_raw(callback_candidate, _context):
            self.assertIs(type(callback_candidate.raw_envelope), bytes)
            self.assertEqual(callback_candidate.raw_envelope, raw_content)
            callback_raw_values.append(callback_candidate.raw_envelope)
            return True

        validators = {
            name: inspect_raw
            for name in (
                "attestation", "revocation", "host_identity", "sid", "acl", "path", "mutex"
            )
        }
        snapshot = validate_candidate(candidate, validators, self.context())
        supplied_raw.mutable_attribute.append("changed-after-validation")

        self.assertIs(type(snapshot.raw_envelope), bytes)
        self.assertEqual(snapshot.raw_envelope, raw_content)
        self.assertIsNot(snapshot.raw_envelope, supplied_raw)
        self.assertEqual(snapshot.payload["provider_id"], "P02/T006")
        self.assertTrue(all(value is snapshot.raw_envelope for value in callback_raw_values))
        self.assertEqual(
            hashlib.sha256(snapshot.payload_bytes).hexdigest(),
            snapshot.envelope["digest"]["value"],
        )

    def test_requires_strict_schema_version_provider_id_and_revision(self):
        for version in (True, 1.0, "1", None):
            with self.subTest(schema_version=version):
                payload = self.payload_value()
                payload["schema_version"] = version
                parsed = self.envelope(payload_bytes=self.encoded_payload(payload))
                with self.assertRaisesRegex(
                    CandidateVerificationError, "invalid_provider_schema_version"
                ):
                    validate_candidate(parsed, self.validators(), self.context())
        payload = self.payload_value()
        payload["provider_id"] = "provider-a"
        with self.assertRaisesRegex(CandidateVerificationError, "provider_id_mismatch"):
            validate_candidate(
                self.envelope(payload_bytes=self.encoded_payload(payload)),
                self.validators(),
                self.context(),
            )
        for revision in (True, 0, -1, 1.0, "1", None):
            with self.subTest(revision=revision):
                with self.assertRaisesRegex(CandidateVerificationError, "invalid_revision"):
                    validate_candidate(
                        self.envelope(revision=revision),
                        self.validators(),
                        self.context(),
                    )

    def test_validates_every_provider_payload_object_schema(self):
        mutations = (
            lambda p: p["target"].pop("host_identity"),
            lambda p: p["target"].update(unknown="x"),
            lambda p: p["target"].update(service_sid=[]),
            lambda p: p["ledger"].pop("path"),
            lambda p: p["ledger"].update(extra="x"),
            lambda p: p["ledger"].update(path=None),
            lambda p: p["mutex"].pop("scope"),
            lambda p: p["mutex"].update(extra="x"),
            lambda p: p["mutex"].update(name=1),
            lambda p: p["acl"].pop("ledger"),
            lambda p: p["acl"].update(extra={}),
            lambda p: p["acl"]["ledger"].update(extra=True),
            lambda p: p["acl"]["ledger"].update(inheritance_enabled=1),
            lambda p: p["acl"]["ledger"]["entries"].append({"sid": "s", "access": "allow"}),
            lambda p: p["acl"]["ledger"]["entries"][0].update(access="maybe"),
            lambda p: p["acl"]["ledger"]["entries"][0].update(rights="read"),
            lambda p: p["acl"]["ledger"]["entries"][0].update(extra=True),
        )
        for mutate in mutations:
            payload = self.payload_value()
            mutate(payload)
            with self.subTest(payload=payload):
                parsed = self.envelope(payload_bytes=self.encoded_payload(payload))
                with self.assertRaises(CandidateVerificationError):
                    validate_candidate(parsed, self.validators(), self.context())

    def test_wait_schema_accepts_only_fail_fast_or_bounded_poll(self):
        for wait in (
            {"strategy": "fail_fast"},
            {"strategy": "bounded_poll", "timeout_ms": 500, "poll_interval_ms": 50},
        ):
            with self.subTest(wait=wait):
                payload = self.payload_value()
                payload["wait"] = wait
                validate_candidate(
                    self.envelope(payload_bytes=self.encoded_payload(payload)),
                    self.validators(),
                    self.context(),
                )
        invalid_waits = (
            {"strategy": "fail_fast", "timeout_ms": 1},
            {"strategy": "bounded_poll", "timeout_ms": 10},
            {"strategy": "bounded_poll", "timeout_ms": 10, "poll_interval_ms": 11},
            {"strategy": "bounded_poll", "timeout_ms": True, "poll_interval_ms": 1},
            {"strategy": "bounded_poll", "timeout_ms": 10.0, "poll_interval_ms": 1},
            {"strategy": "bounded_poll", "timeout_ms": 10, "poll_interval_ms": False},
            {"strategy": "later"},
        )
        for wait in invalid_waits:
            with self.subTest(wait=wait):
                payload = self.payload_value()
                payload["wait"] = wait
                with self.assertRaisesRegex(CandidateVerificationError, "invalid_wait"):
                    validate_candidate(
                        self.envelope(payload_bytes=self.encoded_payload(payload)),
                        self.validators(),
                        self.context(),
                    )

    def test_rejects_unapproved_legacy_and_structured_envelope_fields(self):
        approved = self.envelope().value
        for key, value in (
            ("schema", "ConfigSnapshotCandidateV1"),
            ("payload_sha256", "0" * 64),
            ("attestation_key_id", "old-key"),
            ("not_after", "2026-12-01T00:00:00Z"),
            ("attestation", {"signature": "structured"}),
        ):
            with self.subTest(field=key):
                candidate = dict(approved)
                candidate[key] = value
                parsed = self.envelope(**candidate)
                with self.assertRaises(CandidateVerificationError):
                    validate_candidate(parsed, self.validators(), self.context())

    def test_rejects_missing_unknown_and_wrong_nested_types(self):
        approved = self.envelope().value
        cases = []
        missing = dict(approved)
        del missing["source_identity_claim"]
        cases.append(missing)
        unknown = dict(approved, unexpected=True)
        cases.append(unknown)
        for field in ("digest", "validity", "revocation"):
            changed = dict(approved)
            changed[field] = []
            cases.append(changed)
        for candidate in cases:
            with self.subTest(candidate=candidate):
                parsed = parse_envelope(
                    json.dumps(candidate, separators=(",", ":")).encode()
                )
                with self.assertRaises(CandidateVerificationError):
                    validate_candidate(parsed, self.validators(), self.context())

    def test_requires_canonical_nonempty_base64_in_all_three_fields(self):
        invalid_values = ("", "Y Q==", "-_==", "YQ", "Y===", "YR==")
        for field in ("payload", "attestation"):
            for value in invalid_values:
                with self.subTest(field=field, value=value):
                    parsed = self.envelope(**{field: value})
                    with self.assertRaises(CandidateVerificationError):
                        validate_candidate(parsed, self.validators(), self.context())
        approved = self.envelope().value
        for value in invalid_values:
            with self.subTest(field="revocation.proof", value=value):
                revocation = dict(approved["revocation"], proof=value)
                parsed = self.envelope(revocation=revocation)
                with self.assertRaises(CandidateVerificationError):
                    validate_candidate(parsed, self.validators(), self.context())

    def test_hashes_and_strictly_parses_the_exact_decoded_payload_bytes(self):
        parsed = self.envelope()
        with patch.object(
            config_snapshot_candidate_verifier,
            "parse_envelope",
            wraps=parse_envelope,
        ) as strict_parser:
            validate_candidate(parsed, self.validators(), self.context())
        self.assertEqual(
            [call.args[0] for call in strict_parser.call_args_list],
            [parsed.raw_envelope, self.payload_bytes()],
        )

        encoded_payload = parsed.value["payload"].encode("ascii")
        token_digest = hashlib.sha256(encoded_payload).hexdigest()
        candidate = dict(parsed.value)
        candidate["digest"] = {"algorithm": "sha256", "value": token_digest}
        with self.assertRaisesRegex(
            CandidateVerificationError, "payload_digest_mismatch"
        ):
            validate_candidate(
                self.envelope(**candidate), self.validators(), self.context()
            )

    def test_injected_policy_failure_and_missing_dependency_fail_closed(self):
        with self.assertRaises(CandidateVerificationError):
            validate_candidate(
                self.envelope(), self.validators(result=False), self.context()
            )
        validators = self.validators()
        del validators["mutex"]
        with self.assertRaises(CandidateVerificationError):
            validate_candidate(self.envelope(), validators, self.context())

    def assert_sanitized_error(self, error, code, secrets=()):
        self.assertIsInstance(error, CandidateVerificationError)
        self.assertEqual(vars(error), {"code": code, "field_path": "/"})
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertTrue(error.__suppress_context__)
        rendered = repr((error.args, str(error), vars(error)))
        for secret in secrets:
            self.assertNotIn(secret, rendered)

    def test_callback_exception_is_sanitized_and_traceback_has_no_input_locals(self):
        raw_envelope = self.envelope().raw_envelope
        payload_bytes = self.payload_bytes()
        secret = "sensitive-callback-detail"

        class CallbackFailure(Exception):
            def __init__(self):
                self.private_value = secret
                super().__init__(secret)

        def fail(_candidate, _context):
            raise CallbackFailure()

        validators = self.validators()
        validators["attestation"] = fail
        try:
            validate_candidate(self.envelope(), validators, self.context())
        except CandidateVerificationError as error:
            self.assert_sanitized_error(error, "validator_failed", (secret,))
            frame = error.__traceback__
            verifier_frames = []
            while frame is not None:
                if frame.tb_frame.f_code.co_filename == config_snapshot_candidate_verifier.__file__:
                    verifier_frames.append(frame.tb_frame.f_locals)
                frame = frame.tb_next
            captured_traceback = error.__traceback__
        else:
            self.fail("Expected sanitized validation failure")
        frame = captured_traceback
        while frame is not None:
            if frame.tb_frame.f_code.co_filename == config_snapshot_candidate_verifier.__file__:
                verifier_frames.append(frame.tb_frame.f_locals)
            frame = frame.tb_next
        self.assertTrue(verifier_frames)
        for local_values in verifier_frames:
            rendered = repr(local_values)
            self.assertNotIn(secret, rendered)
            self.assertNotIn(raw_envelope.decode("utf-8"), rendered)
            self.assertNotIn(payload_bytes.decode("utf-8"), rendered)
            for name in ("parsed", "validators", "validation_context", "candidate", "payload_bytes"):
                self.assertNotIn(name, local_values)

    def test_locked_third_party_exceptions_are_sanitized_at_all_boundaries(self):
        secret = "locked-sensitive-detail"
        blocked_assignments = []

        class LockedFailure(Exception):
            def __init__(self):
                super().__init__(secret)

            def __setattr__(self, name, value):
                if name in {"__traceback__", "__cause__", "__context__"}:
                    blocked_assignments.append(name)
                    raise AttributeError("exception attribute is locked")
                super().__setattr__(name, value)

        class RaisingValidators(dict):
            def get(self, key, default=None):
                raise LockedFailure()

        def assert_sanitized_without_internal_leak(error, expected_code):
            self.assert_sanitized_error(error, expected_code, (secret,))
            frame = error.__traceback__
            while frame is not None:
                if frame.tb_frame.f_code.co_filename == config_snapshot_candidate_verifier.__file__:
                    local_values = repr(frame.tb_frame.f_locals)
                    self.assertNotIn(secret, local_values)
                    self.assertNotIn("LockedFailure", local_values)
                frame = frame.tb_next

        cases = (
            (
                RaisingValidators(),
                self.context(),
                "verification_failed",
            ),
        )
        for validators, context, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                try:
                    validate_candidate(self.envelope(), validators, context)
                except CandidateVerificationError as error:
                    assert_sanitized_without_internal_leak(error, expected_code)
                else:
                    self.fail("Expected sanitized validation failure")

        def locked_callback(_candidate, _context):
            raise LockedFailure()

        validators = self.validators()
        validators["attestation"] = locked_callback
        try:
            validate_candidate(self.envelope(), validators, self.context())
        except CandidateVerificationError as error:
            assert_sanitized_without_internal_leak(error, "validator_failed")
        else:
            self.fail("Expected sanitized callback failure")
        self.assertEqual(blocked_assignments, [])

    def test_base_exception_from_callback_is_not_caught(self):
        class StopValidation(BaseException):
            pass

        stop = StopValidation("stop")

        def abort(_candidate, _context):
            raise stop

        validators = self.validators()
        validators["attestation"] = abort
        with self.assertRaises(StopValidation) as caught:
            validate_candidate(self.envelope(), validators, self.context())
        self.assertIs(caught.exception, stop)

    def test_timezone_conversion_failures_are_stable(self):
        validity = {
            "not_before": "0001-01-01T00:00:00+23:59",
            "expires_at": "2026-12-01T00:00:00Z",
        }
        with self.assertRaises(CandidateVerificationError) as caught:
            validate_candidate(
                self.envelope(validity=validity), self.validators(), self.context()
            )
        self.assert_sanitized_error(caught.exception, "invalid_validity")

        class RaisingOffset(tzinfo):
            def __init__(self):
                self.calls = 0

            def utcoffset(self, dt):
                self.calls += 1
                raise RuntimeError("sensitive offset detail")

            def dst(self, dt):
                return None

        raising_offset = RaisingOffset()
        context = {"now": datetime(2026, 11, 15, tzinfo=raising_offset)}
        with self.assertRaises(CandidateVerificationError) as caught:
            validate_candidate(self.envelope(), self.validators(), context)
        self.assert_sanitized_error(caught.exception, "invalid_validation_clock", ("sensitive",))
        self.assertEqual(raising_offset.calls, 0)

        context = {
            "now": datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))
        }
        with self.assertRaises(CandidateVerificationError) as caught:
            validate_candidate(self.envelope(), self.validators(), context)
        self.assert_sanitized_error(caught.exception, "invalid_validation_clock")

    def test_caller_active_json_and_unicode_errors_are_not_chained(self):
        bad_candidates = (
            (b'{"private":"json-secret",}', "json-secret"),
            (b'{"private":"unicode-secret\xff"}', "unicode-secret"),
        )
        for raw, secret in bad_candidates:
            with self.subTest(secret=secret):
                try:
                    if secret == "json-secret":
                        json.loads(raw.decode("ascii"))
                    else:
                        raw.decode("utf-8")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    with self.assertRaises(CandidateVerificationError) as caught:
                        validate_candidate(
                            ParsedEnvelope({}, raw, None),
                            self.validators(),
                            self.context(),
                        )
                else:
                    self.fail("Expected the caller-side parsing exception")
                self.assert_sanitized_error(
                    caught.exception, "invalid_envelope", (secret,)
                )
