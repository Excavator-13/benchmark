import sys
import unittest
from unittest.mock import patch

from benchmark.multivariate_time_series.temporal import config_snapshot_candidate_parser
from benchmark.multivariate_time_series.temporal.config_snapshot_candidate_parser import (
    CandidateParseError,
    parse_envelope,
)


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
