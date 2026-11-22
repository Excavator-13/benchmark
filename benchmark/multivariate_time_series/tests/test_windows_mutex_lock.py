import math
import unittest

from benchmark.multivariate_time_series.temporal.ledger_lock import AcquireStatus
from benchmark.multivariate_time_series.temporal.windows_mutex_lock import (
    map_wait_status,
    timeout_to_wait_ms,
)


class HostileInt(int):
    def __int__(self):
        raise AssertionError("int conversion must not be called")

    def __hash__(self):
        raise AssertionError("hash must not be called")

    def __eq__(self, other):
        raise AssertionError("custom equality must not be called")


class MapWaitStatusTests(unittest.TestCase):
    def test_wait_object_zero_maps_to_acquired(self):
        self.assertIs(map_wait_status(0x00000000), AcquireStatus.ACQUIRED)

    def test_wait_abandoned_maps_to_abandoned(self):
        self.assertIs(map_wait_status(0x00000080), AcquireStatus.ABANDONED)

    def test_wait_timeout_maps_to_timeout(self):
        self.assertIs(map_wait_status(0x00000102), AcquireStatus.TIMEOUT)

    def test_wait_failed_maps_to_wait_failed(self):
        self.assertIs(map_wait_status(0xFFFFFFFF), AcquireStatus.WAIT_FAILED)

    def test_other_integer_maps_to_unknown(self):
        self.assertIs(map_wait_status(1), AcquireStatus.UNKNOWN)

    def test_invalid_types_map_to_unknown_without_custom_operations(self):
        invalid_codes = (
            False,
            True,
            HostileInt(0),
            None,
            "0",
            b"\x00",
            0.0,
            object(),
        )
        for code in invalid_codes:
            with self.subTest(code_type=type(code).__name__):
                self.assertIs(map_wait_status(code), AcquireStatus.UNKNOWN)

    def test_non_int_object_does_not_invoke_custom_methods(self):
        class WaitCode:
            def __init__(self):
                self.int_calls = 0
                self.hash_calls = 0
                self.eq_calls = 0

            def __int__(self):
                self.int_calls += 1
                return 0

            def __hash__(self):
                self.hash_calls += 1
                return 0

            def __eq__(self, other):
                self.eq_calls += 1
                return False

        code = WaitCode()
        self.assertIs(map_wait_status(code), AcquireStatus.UNKNOWN)
        self.assertEqual(code.int_calls, 0)
        self.assertEqual(code.hash_calls, 0)
        self.assertEqual(code.eq_calls, 0)


class TimeoutToWaitMsTests(unittest.TestCase):
    def test_rejects_non_builtin_types_without_invoking_custom_methods(self):
        class CustomTimeout:
            def unexpected_call(self, *args):
                raise AssertionError("rejected inputs must not be used")

            __int__ = __float__ = __index__ = unexpected_call
            __eq__ = __lt__ = __hash__ = unexpected_call

        class FloatSubclass(float):
            def as_integer_ratio(self):
                raise AssertionError("float subclasses must not be used")

        for timeout in (None, False, True, "0", HostileInt(0), FloatSubclass(0), CustomTimeout()):
            with self.subTest(input_type=type(timeout).__name__):
                self.assertIsNone(timeout_to_wait_ms(timeout))

    def test_rejects_negative_values(self):
        for timeout in (-1, -0.0005):
            with self.subTest(timeout=timeout):
                self.assertIsNone(timeout_to_wait_ms(timeout))

    def test_zero_and_positive_submillisecond_values_use_zero_wait(self):
        for timeout in (0, 0.0, -0.0, math.nextafter(0.0, 1.0), 0.0005):
            with self.subTest(timeout=timeout):
                wait_ms = timeout_to_wait_ms(timeout)
                self.assertIs(type(wait_ms), int)
                self.assertEqual(wait_ms, 0)

    def test_floors_the_exact_binary_float_value(self):
        self.assertEqual(timeout_to_wait_ms(0.125), 125)
        self.assertEqual(timeout_to_wait_ms(0.1259765625), 125)
        # This float is slightly below 9 ms even though float multiplication rounds to 9.
        self.assertEqual(timeout_to_wait_ms(0.009), 8)

    def test_integer_seconds_at_the_finite_limit_and_beyond(self):
        self.assertEqual(timeout_to_wait_ms(4_294_967), 4_294_967_000)
        self.assertIsNone(timeout_to_wait_ms(4_294_968))
        self.assertIsNone(timeout_to_wait_ms(10**400))

    def test_rejects_nonfinite_values(self):
        for timeout in (math.nan, math.inf, -math.inf):
            with self.subTest(timeout=timeout):
                self.assertIsNone(timeout_to_wait_ms(timeout))

    def test_float_boundary_where_floored_milliseconds_reach_infinite(self):
        # The nearest float to 0xFFFFFFFF ms in seconds lies below the threshold.
        last_finite = 4_294_967.295
        first_rejected = math.nextafter(last_finite, math.inf)
        self.assertEqual(timeout_to_wait_ms(4_294_967.2945), 0xFFFFFFFE)
        self.assertEqual(timeout_to_wait_ms(last_finite), 0xFFFFFFFE)
        self.assertIsNone(timeout_to_wait_ms(first_rejected))


if __name__ == "__main__":
    unittest.main()
