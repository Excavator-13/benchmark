import base64
import hashlib
import json
import unittest
from contextlib import nullcontext
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from benchmark.multivariate_time_series.temporal import config_snapshot_candidate_adapter as adapter
from benchmark.multivariate_time_series.temporal.config_snapshot_candidate_verifier import (
    CandidateVerificationSnapshot,
)


def _synthetic_candidate():
    reader_entry = {"sid": "synthetic-reader", "access": "allow", "rights": ["read"]}
    policy = {
        "owner_sid": "synthetic-owner",
        "inheritance_enabled": False,
        "entries": [reader_entry],
    }
    payload = {
        "schema_version": 1,
        "provider_id": "P02/T006",
        "target": {"host_identity": "synthetic-host", "service_sid": "synthetic-service"},
        "ledger": {"path": "synthetic-path"},
        "mutex": {"name": "synthetic-name", "scope": "synthetic-scope"},
        "acl": {"ledger": policy, "mutex": policy},
        "wait": {"strategy": "fail_fast"},
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    envelope = {
        "payload": base64.b64encode(payload_bytes).decode("ascii"),
        "provider_id": "P02/T006",
        "revision": 1,
        "digest": {"algorithm": "sha256", "value": hashlib.sha256(payload_bytes).hexdigest()},
        "validity": {"not_before": "2030-01-01T00:00:00Z", "expires_at": "2030-01-03T00:00:00Z"},
        "source_identity_claim": {"name": "synthetic-source"},
        "revocation": {
            "status": "good",
            "checked_at": "2030-01-01T00:00:00Z",
            "valid_until": "2030-01-03T00:00:00Z",
            "authority_identity_claim": {"name": "synthetic-authority"},
            "proof": "cHJvb2Y=",
        },
        "attestation": "YXR0ZXN0YXRpb24=",
    }
    raw = b" \n" + json.dumps(envelope).encode("utf-8") + b"\t "
    return raw, payload_bytes


class ConfigSnapshotCandidateAdapterTests(unittest.TestCase):
    def setUp(self):
        self.raw, self.payload_bytes = _synthetic_candidate()
        self.provider = Mock(return_value=self.raw)
        self.validators = {
            name: Mock(return_value=True)
            for name in ("attestation", "revocation", "host_identity", "sid", "acl", "path", "mutex")
        }
        self.validation_context = {"now": datetime(2030, 1, 2, tzinfo=timezone.utc)}

    def test_success_uses_existing_gate_parser_and_verifier_in_order(self):
        real_parse = adapter.parse_envelope
        real_verify = adapter.validate_candidate
        parsed_results = []
        verified_results = []

        def parse(raw):
            self.provider.assert_called_once_with()
            self.assertIs(raw, self.raw)
            parsed_results.append(real_parse(raw))
            return parsed_results[0]

        def verify(parsed, validators, validation_context):
            self.assertIs(parsed, parsed_results[0])
            self.assertIs(validators, self.validators)
            self.assertIs(validation_context, self.validation_context)
            verified_results.append(real_verify(parsed, validators, validation_context))
            return verified_results[0]

        with (
            patch.object(adapter, "require_deployment_config", wraps=adapter.require_deployment_config) as gate,
            patch.object(adapter, "parse_envelope", side_effect=parse) as parser,
            patch.object(adapter, "validate_candidate", side_effect=verify) as verifier,
        ):
            snapshot = adapter.verify_deployment_candidate(
                provider=self.provider,
                validators=self.validators,
                validation_context=self.validation_context,
            )

        gate.assert_called_once()
        self.provider.assert_called_once_with()
        parser.assert_called_once()
        verifier.assert_called_once()
        self.assertIs(snapshot, verified_results[0])
        self.assertIsInstance(snapshot, CandidateVerificationSnapshot)
        self.assertEqual(snapshot.raw_envelope, self.raw)
        self.assertEqual(snapshot.payload_bytes, self.payload_bytes)
        for validator in self.validators.values():
            validator.assert_called_once()
            parsed, context = validator.call_args.args
            self.assertEqual(parsed.raw_envelope, self.raw)
            self.assertEqual(context, self.validation_context)

    def test_snapshot_is_immutable(self):
        snapshot = adapter.verify_deployment_candidate(
            self.provider, self.validators, self.validation_context
        )
        with self.assertRaises(FrozenInstanceError):
            snapshot.raw_envelope = b""
        with self.assertRaises(TypeError):
            snapshot.envelope["digest"]["value"] = "changed"
        with self.assertRaises(TypeError):
            snapshot.payload["acl"]["ledger"]["entries"][0]["sid"] = "changed"
        self.assertEqual(snapshot.payload["acl"]["ledger"]["entries"][0]["rights"], ("read",))

    def test_all_three_arguments_are_required(self):
        arguments = (self.provider, self.validators, self.validation_context)
        for supplied_count in range(3):
            with self.subTest(supplied_count=supplied_count):
                with self.assertRaises(TypeError):
                    adapter.verify_deployment_candidate(*arguments[:supplied_count])
        self.provider.assert_not_called()

    def test_missing_provider_stops_before_parsing(self):
        with (
            patch.object(adapter, "parse_envelope") as parser,
            patch.object(adapter, "validate_candidate") as verifier,
            self.assertRaises(adapter.CandidateAdapterError) as caught,
        ):
            adapter.verify_deployment_candidate(None, self.validators, self.validation_context)
        self.assertEqual(caught.exception.code, "provider_missing")
        parser.assert_not_called()
        verifier.assert_not_called()

    def test_provider_returning_none_is_missing_and_stops_before_parsing(self):
        self.provider.return_value = None
        with (
            patch.object(adapter, "require_deployment_config", wraps=adapter.require_deployment_config) as gate,
            patch.object(adapter, "parse_envelope") as parser,
            patch.object(adapter, "validate_candidate") as verifier,
            self.assertRaises(adapter.CandidateAdapterError) as caught,
        ):
            adapter.verify_deployment_candidate(self.provider, self.validators, self.validation_context)
        self.assertEqual(caught.exception.code, "provider_missing")
        gate.assert_called_once()
        self.provider.assert_called_once_with()
        parser.assert_not_called()
        verifier.assert_not_called()

    def test_failing_provider_is_called_once_and_stops_before_parsing(self):
        self.provider.side_effect = RuntimeError("synthetic provider failure")
        with (
            patch.object(adapter, "parse_envelope") as parser,
            patch.object(adapter, "validate_candidate") as verifier,
            self.assertRaises(adapter.CandidateAdapterError) as caught,
        ):
            adapter.verify_deployment_candidate(self.provider, self.validators, self.validation_context)
        self.assertEqual(caught.exception.code, "provider_failed")
        self.provider.assert_called_once_with()
        parser.assert_not_called()
        verifier.assert_not_called()

    def test_rejects_every_sample_non_bytes_result_before_parsing(self):
        class BytesSubclass(bytes):
            pass

        results = ("{}", bytearray(b"{}"), memoryview(b"{}"), BytesSubclass(b"{}"), {})
        with (
            patch.object(adapter, "parse_envelope") as parser,
            patch.object(adapter, "validate_candidate") as verifier,
        ):
            for result in results:
                with self.subTest(result_type=type(result)):
                    provider = Mock(return_value=result)
                    with self.assertRaises(adapter.CandidateAdapterError) as caught:
                        adapter.verify_deployment_candidate(
                            provider, self.validators, self.validation_context
                        )
                    self.assertEqual(caught.exception.code, "invalid_provider_result")
                    provider.assert_called_once_with()
        parser.assert_not_called()
        verifier.assert_not_called()

    def test_real_parse_failure_stops_before_verification(self):
        self.provider.return_value = b'{"synthetic-key": "synthetic-value",}'
        with (
            patch.object(adapter, "validate_candidate") as verifier,
            self.assertRaises(adapter.CandidateAdapterError) as caught,
        ):
            adapter.verify_deployment_candidate(self.provider, self.validators, self.validation_context)
        self.assertEqual(caught.exception.code, "parse_failed")
        self.provider.assert_called_once_with()
        verifier.assert_not_called()

    def test_real_verification_failure_stops_later_validators(self):
        self.validators["attestation"].return_value = False
        with self.assertRaises(adapter.CandidateAdapterError) as caught:
            adapter.verify_deployment_candidate(self.provider, self.validators, self.validation_context)
        self.assertEqual(caught.exception.code, "verification_failed")
        self.provider.assert_called_once_with()
        self.validators["attestation"].assert_called_once()
        for name in ("revocation", "host_identity", "sid", "acl", "path", "mutex"):
            self.validators[name].assert_not_called()

    def test_public_errors_omit_internal_inputs_and_exception_chains(self):
        accesses = []

        class SensitiveError(Exception):
            def __getattribute__(self, name):
                accesses.append(name)
                return super().__getattribute__(name)

            def __setattr__(self, name, value):
                accesses.append(name)
                super().__setattr__(name, value)

            def __str__(self):
                accesses.append("__str__")
                return super().__str__()

            def __repr__(self):
                accesses.append("__repr__")
                return super().__repr__()

        for stage, code in (
            ("provider", "provider_failed"),
            ("parse_envelope", "parse_failed"),
            ("validate_candidate", "verification_failed"),
        ):
            with self.subTest(stage=stage):
                lower_error = SensitiveError("synthetic private message")
                lower_cause = RuntimeError("synthetic private cause")
                BaseException.__setattr__(lower_error, "secret", "synthetic private attribute")

                def fail(*args):
                    raise lower_error from lower_cause

                caller_owned = RuntimeError("synthetic caller exception")
                dependency = nullcontext() if stage == "provider" else patch.object(adapter, stage, fail)
                provider = fail if stage == "provider" else self.provider
                with dependency:
                    try:
                        raise caller_owned
                    except RuntimeError:
                        try:
                            adapter.verify_deployment_candidate(
                                provider, self.validators, self.validation_context
                            )
                        except adapter.CandidateAdapterError as error:
                            self.assertEqual(vars(error), {"code": code})
                            self.assertEqual(error.args, (code,))
                            self.assertEqual(str(error), code)
                            self.assertIsNone(error.__cause__)
                            self.assertIsNone(error.__context__)
                            entry = error.__traceback__
                            self.assertIs(entry.tb_frame.f_locals["caller_owned"], caller_owned)
                            entry = entry.tb_next
                            self.assertEqual(entry.tb_frame.f_code.co_name, "verify_deployment_candidate")
                            self.assertEqual(dict(entry.tb_frame.f_locals), {"result": error})
                            self.assertIsNone(entry.tb_next)
                        else:
                            self.fail("expected a public adapter error")
                self.assertEqual(accesses, [])
                read = BaseException.__getattribute__
                self.assertEqual(read(lower_error, "args"), ("synthetic private message",))
                self.assertEqual(read(lower_error, "secret"), "synthetic private attribute")
                self.assertIs(read(lower_error, "__cause__"), lower_cause)
                self.assertIs(read(lower_error, "__context__"), caller_owned)
                entry = read(lower_error, "__traceback__")
                while entry.tb_next is not None:
                    entry = entry.tb_next
                self.assertEqual(entry.tb_frame.f_code.co_name, "fail")

    def test_base_exception_propagates_from_each_stage(self):
        class Abort(BaseException):
            pass

        for stage in ("provider", "parse_envelope", "validator"):
            with self.subTest(stage=stage):
                abort = Abort()

                def fail(*args):
                    raise abort

                provider = fail if stage == "provider" else self.provider
                validators = dict(self.validators)
                if stage == "validator":
                    validators["attestation"] = fail
                parser = fail if stage == "parse_envelope" else adapter.parse_envelope
                with patch.object(adapter, "parse_envelope", parser):
                    try:
                        adapter.verify_deployment_candidate(provider, validators, self.validation_context)
                    except Abort as error:
                        self.assertIs(error, abort)
                    else:
                        self.fail("expected the original BaseException")
