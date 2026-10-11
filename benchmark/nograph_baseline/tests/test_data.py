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


class FixtureGridTests(unittest.TestCase):
    """P01-T006: the r2 fixture exposes context-qualified identities."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_r2_fixture_generates_r2_id_and_keeps_contexts_distinct(self) -> None:
        fixture = fx.build_fixture(self.root, "r2", contexts=3, skills=2, seed=5)
        self.assertEqual(
            fixture["keys"],
            [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)],
        )
        self.assertEqual(fixture["node_count"], 6)
        demand = nb_data.load_demand("r2", demand_path=fixture["demand_path"])
        self.assertEqual(demand.key_columns, ("r2_id", "skill_id"))
        self.assertEqual(demand.keys, fixture["keys"])
        self.assertEqual(demand.node_count, 6)
        self.assertEqual(demand.audit["context_id_counts"], {"r2_id": 3})
        self.assertEqual(demand.audit["joint_contexts"], 3)
        # The same skill_id recurs in every context and is not merged into one
        # node: the identity is the whole (r2_id, skill_id) tuple.
        self.assertEqual(demand.audit["skill_id_nunique"], 2)
        self.assertEqual(len(set(demand.keys)), 6)
        np.testing.assert_array_equal(
            demand.key_array, np.asarray(fixture["keys"], dtype=np.int64)
        )

    def test_r2_fixture_shuffles_rows_before_canonical_ordering(self) -> None:
        fixture = fx.build_fixture(
            self.root, "r2", contexts=2, skills=3, seed=3, shuffle_seed=11
        )
        demand = nb_data.load_demand("r2", demand_path=fixture["demand_path"])
        self.assertEqual(demand.keys, fixture["keys"])
        self.assertEqual(demand.audit["is_complete_context_skill_grid"], True)

    def test_r0_and_region_fixture_semantics_are_unchanged(self) -> None:
        r0 = fx.build_fixture(self.root, "r0", node_count=4, seed=2)
        self.assertEqual(r0["keys"], [(0, skill) for skill in range(4)])
        self.assertEqual(r0["node_count"], 4)
        self.assertEqual(r0["signal"].shape, (4, 36))
        r0_demand = nb_data.load_demand("r0", demand_path=r0["demand_path"])
        self.assertEqual(r0_demand.key_columns, ("r0_id", "skill_id"))

        region = fx.build_fixture(self.root, "region", node_count=3, seed=2)
        self.assertEqual(
            region["keys"], [(region_id, skill) for region_id in range(3) for skill in range(2)]
        )
        self.assertEqual(region["node_count"], 6)
        region_demand = nb_data.load_demand("region", demand_path=region["demand_path"])
        self.assertEqual(region_demand.key_columns, ("region_id", "skill_id"))
        self.assertEqual(region_demand.audit["context_id_counts"], {"region_id": 3})


class R2DemandAuditTests(unittest.TestCase):
    """P01-T006: r2 demand identity, grid audits and pre-fit rejection."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_shuffled_multi_context_r2_is_canonically_ordered(self) -> None:
        keys = fx.r2_keys(3, 4)
        signal = fx.synthetic_signal(len(keys), seed=17)
        path = fx.write_demand(
            self.root / "r2.parquet", "r2", keys, signal, shuffle_seed=23
        )
        demand = nb_data.load_demand("r2", demand_path=path)
        self.assertEqual(demand.keys, keys)
        self.assertEqual(demand.node_count, 12)
        np.testing.assert_array_equal(
            demand.key_array, np.asarray(keys, dtype=np.int64)
        )
        np.testing.assert_array_equal(demand.signal, signal)
        audit = demand.audit
        self.assertEqual(audit["key_columns"], ["r2_id", "skill_id"])
        self.assertEqual(audit["nodes"], 12)
        self.assertEqual(audit["context_id_counts"], {"r2_id": 3})
        self.assertEqual(audit["joint_contexts"], 3)
        self.assertEqual(audit["skill_id_nunique"], 4)
        self.assertEqual(audit["context_cartesian_size"], 3)
        self.assertEqual(audit["expected_context_skill_nodes"], 12)
        self.assertTrue(audit["is_complete_context_skill_grid"])
        self.assertEqual(len(audit["monthly_nonzero_fraction"]), 36)
        self.assertEqual(audit["train_observation_months"][0], "2021-01")
        self.assertEqual(audit["train_observation_months"][-1], "2023-03")
        self.assertIn("r2_id", audit["per_context"])

    def test_incomplete_r2_grid_is_reported_without_filling_rows(self) -> None:
        keys = [(0, 0), (0, 1), (1, 0)]  # (1, 1) is absent
        signal = fx.synthetic_signal(len(keys), seed=4)
        path = fx.write_demand(self.root / "sparse.parquet", "r2", keys, signal)
        demand = nb_data.load_demand("r2", demand_path=path)
        self.assertEqual(demand.keys, keys)
        self.assertEqual(demand.node_count, 3)
        audit = demand.audit
        self.assertFalse(audit["is_complete_context_skill_grid"])
        self.assertEqual(audit["expected_context_skill_nodes"], 4)
        self.assertEqual(audit["joint_contexts"], 2)
        self.assertEqual(audit["skill_id_nunique"], 2)
        self.assertEqual(audit["per_context"]["r2_id"]["0"]["nodes"], 2)
        self.assertEqual(audit["per_context"]["r2_id"]["1"]["nodes"], 1)

    def test_r2_activity_boundaries_and_zero_constant_audits(self) -> None:
        keys = fx.r2_keys(1, 8)
        signal = np.zeros((8, 36), dtype=np.float64)
        signal[1, :1] = 1.0  # 1/27 -> low
        signal[2, :9] = 1.0  # exactly 1/3 -> low (inclusive upper bound)
        signal[3, :10] = 1.0  # 10/27 -> medium
        signal[4, :18] = 1.0  # exactly 2/3 -> medium (inclusive upper bound)
        signal[5, :19] = 1.0  # 19/27 -> high
        signal[6, :27] = 1.0  # 27/27 -> high, constant in train
        signal[7, 30] = 3.0  # only after 2023-03: descriptive-only late activity
        demand = fx.make_demand("r2", keys, signal)
        audit = demand.audit
        self.assertEqual(
            audit["activity_group_counts"],
            # rows 0 and 7 are inactive (row 7 only becomes active after 2023-03)
            {"inactive": 2, "low": 2, "medium": 2, "high": 2},
        )
        self.assertEqual(
            audit["constant_node_count_train27"],
            3,  # row 0 all-zero, row 6 constant one, row 7 zero in train
        )
        self.assertAlmostEqual(audit["train_all_zero_fraction"], 2.0 / 8.0)
        self.assertAlmostEqual(
            audit["full_36_month_all_zero_fraction_diagnostic_only"], 1.0 / 8.0
        )
        self.assertTrue(audit["full_36_month_diagnostics_are_descriptive_only"])
        self.assertAlmostEqual(audit["monthly_nonzero_fraction"][0], 6.0 / 8.0)
        # Only row 7 is active in 2023-07, and that late activity is audit-only.
        self.assertAlmostEqual(audit["monthly_nonzero_fraction"][30], 1.0 / 8.0)
        context = audit["per_context"]["r2_id"]["0"]
        self.assertEqual(context["nodes"], 8)
        self.assertAlmostEqual(context["train_all_zero_fraction"], 2.0 / 8.0)
        self.assertAlmostEqual(
            context["full_36_month_all_zero_fraction"], 1.0 / 8.0
        )
        self.assertTrue(np.isfinite(context["mean_train_value"]))

    def _write_valid_r2(self) -> Path:
        keys = fx.r2_keys(2, 2)
        signal = fx.synthetic_signal(len(keys), seed=6)
        return fx.write_demand(self.root / "valid-r2.parquet", "r2", keys, signal)

    def _expect_r2_error(self, frame_mutator, message: str) -> None:
        import pandas as pd

        path = self._write_valid_r2()
        frame = pd.read_parquet(path)
        frame = frame_mutator(frame)
        frame.to_parquet(path, index=False)
        with self.assertRaises(nb_data.DemandError, msg=message):
            nb_data.load_demand("r2", demand_path=path)

    def test_missing_r2_id_is_rejected(self) -> None:
        self._expect_r2_error(
            lambda frame: frame.drop(columns=["r2_id"]), "missing context key"
        )

    def test_duplicate_r2_identity_is_rejected(self) -> None:
        self._expect_r2_error(
            lambda frame: frame.assign(skill_id=[0, 0, 0, 1]),
            "duplicate r2 identity",
        )

    def test_non_integer_r2_key_is_rejected(self) -> None:
        self._expect_r2_error(
            lambda frame: frame.assign(r2_id=[0.0, 0.0, 1.5, 1.5]),
            "non-integer r2_id",
        )

    def test_nonfinite_r2_key_is_rejected(self) -> None:
        self._expect_r2_error(
            lambda frame: frame.assign(r2_id=[0.0, 0.0, np.inf, np.inf]),
            "nonfinite r2_id",
        )

    def test_missing_month_r2_is_rejected(self) -> None:
        self._expect_r2_error(
            lambda frame: frame.drop(columns=["2023-06"]), "missing r2 month"
        )

    def test_extra_month_r2_is_rejected(self) -> None:
        self._expect_r2_error(
            lambda frame: frame.assign(**{"2024-01": 0.0}), "extra r2 month"
        )

    def test_negative_r2_count_is_rejected(self) -> None:
        self._expect_r2_error(
            lambda frame: frame.assign(**{"2021-01": -2.0}), "negative r2 count"
        )

    def test_nonfinite_r2_count_is_rejected(self) -> None:
        self._expect_r2_error(
            lambda frame: frame.assign(**{"2022-05": np.nan}), "nonfinite r2 count"
        )

    def test_api_rejects_missing_r2_identity_and_fractional_keys(self) -> None:
        signal = fx.synthetic_signal(1, seed=1)
        with self.assertRaises(nb_data.DemandError):
            nb_data.from_arrays("r2", [(0, 0.5)], signal)
        with self.assertRaises(nb_data.DemandError):
            nb_data.from_arrays("r2", [(0, 0), (0, 0)], np.ones((2, 36)))


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
