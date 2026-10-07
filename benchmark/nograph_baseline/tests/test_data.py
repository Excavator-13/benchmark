"""Demand loading, canonical identity, audits and window construction."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

import nb_fixtures as fx
from benchmark.nograph_baseline import data as nb_data
from benchmark.nograph_baseline import protocol


class CanonicalIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_shuffled_parquet_preserves_key_value_alignment(self) -> None:
        keys = fx.r0_keys(9)
        signal = fx.synthetic_signal(len(keys), seed=11)
        path = fx.write_demand(
            self.root / "r0.parquet", "r0", keys, signal, shuffle_seed=5
        )
        demand = nb_data.load_demand("r0", demand_path=path)
        self.assertEqual(demand.keys, keys)
        np.testing.assert_array_equal(demand.key_array[:, 1], np.arange(9))
        np.testing.assert_array_equal(demand.signal, signal)

    def test_region_schema_uses_region_id(self) -> None:
        keys = fx.region_keys(3, 2)
        signal = fx.synthetic_signal(len(keys), seed=2)
        path = fx.write_demand(self.root / "region.parquet", "region", keys, signal)
        demand = nb_data.load_demand("region", demand_path=path)
        self.assertEqual(demand.key_columns, ("region_id", "skill_id"))
        self.assertEqual(demand.keys, keys)
        self.assertEqual(demand.audit["context_id_counts"], {"region_id": 3})
        self.assertEqual(demand.audit["skill_id_nunique"], 2)
        self.assertTrue(demand.audit["is_complete_context_skill_grid"])

    def test_audit_describes_activity_and_zero_fractions(self) -> None:
        keys = fx.r0_keys(4)
        signal = fx.synthetic_signal(
            len(keys), seed=1, zero_rows=(0,), constant_rows=(1,)
        )
        demand = fx.make_demand("r0", keys, signal)
        audit = demand.audit
        self.assertEqual(audit["nodes"], 4)
        self.assertEqual(audit["train_observation_months"][0], "2021-01")
        self.assertEqual(audit["train_observation_months"][-1], "2023-03")
        self.assertEqual(audit["activity_group_counts"]["inactive"], 1)
        self.assertEqual(audit["constant_node_count_train27"], 2)
        self.assertAlmostEqual(
            audit["train_all_zero_fraction"],
            float(((signal[:, :27] > 0).mean(axis=1) == 0).mean()),
        )
        self.assertEqual(len(audit["monthly_nonzero_fraction"]), 36)
        self.assertTrue(audit["full_36_month_diagnostics_are_descriptive_only"])

    def _expect_error(self, frame_mutator, message: str) -> None:
        import pandas as pd

        keys = fx.r0_keys(3)
        signal = fx.synthetic_signal(3, seed=4)
        path = fx.write_demand(self.root / "bad.parquet", "r0", keys, signal)
        frame = pd.read_parquet(path)
        frame = frame_mutator(frame)
        frame.to_parquet(path, index=False)
        with self.assertRaises(nb_data.DemandError, msg=message):
            nb_data.load_demand("r0", demand_path=path)

    def test_duplicate_keys_rejected(self) -> None:
        self._expect_error(
            lambda frame: frame.assign(skill_id=[0, 0, 2]), "duplicate identity"
        )

    def test_non_integer_keys_rejected(self) -> None:
        self._expect_error(
            lambda frame: frame.assign(skill_id=[0, 1, 1.5]), "non-integer identity"
        )

    def test_missing_month_rejected(self) -> None:
        self._expect_error(lambda frame: frame.drop(columns=["2023-06"]), "missing month")

    def test_extra_month_rejected(self) -> None:
        self._expect_error(
            lambda frame: frame.assign(**{"2024-01": 0.0}), "extra month"
        )

    def test_negative_values_rejected(self) -> None:
        frame_mutator = lambda frame: frame.assign(**{"2021-01": -1.0})  # noqa: E731
        self._expect_error(frame_mutator, "negative value")

    def test_nonfinite_values_rejected(self) -> None:
        frame_mutator = lambda frame: frame.assign(**{"2022-05": np.nan})  # noqa: E731
        self._expect_error(frame_mutator, "nonfinite value")

    def test_empty_source_rejected(self) -> None:
        import pandas as pd

        keys = fx.r0_keys(2)
        signal = fx.synthetic_signal(2, seed=4)
        path = fx.write_demand(self.root / "empty.parquet", "r0", keys, signal)
        pd.read_parquet(path).iloc[0:0].to_parquet(path, index=False)
        with self.assertRaises(nb_data.DemandError):
            nb_data.load_demand("r0", demand_path=path)


class WindowConstructionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.keys = fx.r0_keys(6)
        self.signal = fx.synthetic_signal(6, seed=9)
        self.demand = fx.make_demand("r0", self.keys, self.signal)

    def test_true_history_inputs_are_rolling(self) -> None:
        for start in (21, 25):
            inputs = self.demand.input_windows([start])
            targets = self.demand.target_windows([start])
            np.testing.assert_array_equal(
                inputs[0], self.signal[:, start : start + protocol.INPUT_LENGTH]
            )
            np.testing.assert_array_equal(
                targets[0],
                self.signal[
                    :, start + protocol.INPUT_LENGTH : start + protocol.INPUT_LENGTH + protocol.HORIZON
                ],
            )

    def test_later_test_origin_uses_observed_july_history(self) -> None:
        start = 25
        inputs = self.demand.input_windows([start])[0]
        np.testing.assert_array_equal(inputs, self.signal[:, 25:31])
        self.assertEqual(protocol.MONTHS[30], "2023-07")
        self.assertIn(protocol.MONTHS[30], protocol.window_input_months(25))

    def test_all_starts_and_omissions_accounted_for(self) -> None:
        assigned = {
            start for starts in protocol.SPLITS.values() for start in starts
        }
        self.assertEqual(assigned | set(protocol.OMITTED_STARTS), set(range(28)))
        self.assertEqual(len(assigned), 24)

    def test_split_target_months_do_not_overlap(self) -> None:
        seen: set = set()
        for name, starts in protocol.SPLITS.items():
            targets = {
                month
                for start in starts
                for month in protocol.window_target_months(start)
            }
            self.assertFalse(targets & seen, msg=f"{name} overlaps earlier splits")
            seen |= targets


class NativeValidationTests(unittest.TestCase):
    """V-008: validate native representations before any lossy conversion."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_native_negative_underflow_is_rejected(self) -> None:
        import pandas as pd

        keys = fx.r0_keys(1)
        signal = fx.synthetic_signal(1, seed=1)
        path = fx.write_demand(self.root / "d.parquet", "r0", keys, signal)
        frame = pd.read_parquet(path)
        frame["2021-01"] = -1e-50  # becomes -0.0 after a float32 cast
        frame.to_parquet(path, index=False)
        with self.assertRaises(nb_data.DemandError):
            nb_data.load_demand("r0", demand_path=path)

    def test_fractional_api_key_is_rejected(self) -> None:
        with self.assertRaises(nb_data.DemandError):
            nb_data.from_arrays("r0", [(0, 0.5)], np.ones((1, 36)))

    def test_nonfinite_and_out_of_range_api_keys_are_rejected(self) -> None:
        for key in ((0, float("nan")), (0, float("inf")), (0, 1e30)):
            with self.assertRaises(nb_data.DemandError, msg=str(key)):
                nb_data.from_arrays("r0", [key], np.ones((1, 36)))

    def test_int64_upper_bound_float_key_is_rejected(self) -> None:
        # float(np.iinfo(int64).max) rounds to 2**63, which must not be treated
        # as representable; 2**63 and above are outside [-2**63, 2**63).
        for key in ((0, float(2**63)), (0, float(2**63) + 2048.0)):
            with self.subTest(key=key):
                with self.assertRaises(nb_data.DemandError):
                    nb_data.from_arrays("r0", [key], np.ones((1, 36)))

    def test_int64_lower_bound_and_representable_keys_are_accepted(self) -> None:
        lower = -(2**63)
        demand = nb_data.from_arrays("r0", [(0, lower), (0, 0)], np.ones((2, 36)))
        self.assertEqual(demand.keys[0], (0, lower))
        maximum_representable = float(2**63 - 1024)
        demand = nb_data.from_arrays(
            "r0", [(0, maximum_representable)], np.ones((1, 36))
        )
        self.assertEqual(demand.keys[0][1], int(maximum_representable))

    def test_native_int64_upper_bound_key_is_rejected(self) -> None:
        import pandas as pd

        keys = fx.r0_keys(1)
        signal = fx.synthetic_signal(1, seed=3)
        path = fx.write_demand(self.root / "upper.parquet", "r0", keys, signal)
        frame = pd.read_parquet(path)
        frame["skill_id"] = float(2**63)
        frame.to_parquet(path, index=False)
        with self.assertRaises(nb_data.DemandError):
            nb_data.load_demand("r0", demand_path=path)

    def test_boolean_api_key_is_rejected(self) -> None:
        with self.assertRaises(nb_data.DemandError):
            nb_data.from_arrays("r0", [(True, False)], np.ones((1, 36)))

    def test_negative_api_values_are_rejected(self) -> None:
        signal = np.ones((1, 36))
        signal[0, 0] = -1e-50
        with self.assertRaises(nb_data.DemandError):
            nb_data.from_arrays("r0", [(0, 0)], signal)

    def test_valid_declared_dtype_and_key_order_are_preserved(self) -> None:
        keys = [(0, 2), (0, 0), (0, 1)]
        signal = fx.synthetic_signal(3, seed=2)
        demand = nb_data.from_arrays("r0", keys, signal)
        self.assertEqual(demand.signal.dtype, np.float32)
        self.assertEqual(demand.keys, [(0, 0), (0, 1), (0, 2)])


if __name__ == "__main__":
    unittest.main()
