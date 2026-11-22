import unittest

from benchmark.multivariate_time_series.temporal.ledger_lock import AcquireStatus
from benchmark.multivariate_time_series.temporal.windows_mutex_lock import (
    map_wait_status,
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


if __name__ == "__main__":
    unittest.main()
