"""Train-only loading, canonical identities and published assertions."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from benchmark.nograph_baseline import data as p01_data
from benchmark.nograph_baseline import protocol as p01
from benchmark.occupation_skill_graph import data as osg_data
from benchmark.occupation_skill_graph import protocol
from benchmark.occupation_skill_graph.tests import fixtures as fx


class CanonicalLoadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_non_dense_shuffled_fixture_is_canonical(self) -> None:
        observations = fx.canonical_observations()
        first = fx.write_demand_table(
            self.root / "first.parquet",
            "r2",
            fx.DEFAULT_CONTEXTS,
            fx.DEFAULT_SKILLS,
            observations,
        )
        second = fx.write_demand_table(
            self.root / "second.parquet",
            "r2",
            fx.DEFAULT_CONTEXTS,
            fx.DEFAULT_SKILLS,
            observations,
            row_order_seed=17,
        )
        left = osg_data.load_training(first, fixture=True)
        right = osg_data.load_training(second, fixture=True)
        np.testing.assert_array_equal(left.contexts, np.array([2, 5]))
        np.testing.assert_array_equal(left.skills, np.array([1, 4, 7, 10]))
        np.testing.assert_array_equal(left.observations, right.observations)
        self.assertEqual(
            left.content_identity["sha256"], right.content_identity["sha256"]
        )
        # Row order changes the file bytes but not the scientific identity.
        self.assertNotEqual(
            left.file_identity["sha256"], right.file_identity["sha256"]
        )

    def test_held_out_perturbation_changes_only_file_identity(self) -> None:
        observations = fx.canonical_observations()
        first = fx.write_demand_table(
            self.root / "a.parquet",
            "r2",
            fx.DEFAULT_CONTEXTS,
            fx.DEFAULT_SKILLS,
            observations,
            held_out_value=0.0,
        )
        second = fx.write_demand_table(
            self.root / "b.parquet",
            "r2",
            fx.DEFAULT_CONTEXTS,
            fx.DEFAULT_SKILLS,
            observations,
            held_out_value=999.0,
        )
        left = osg_data.load_training(first, fixture=True)
        right = osg_data.load_training(second, fixture=True)
        np.testing.assert_array_equal(left.observations, right.observations)
        self.assertEqual(
            left.content_identity["sha256"], right.content_identity["sha256"]
        )
        self.assertNotEqual(
            left.file_identity["sha256"], right.file_identity["sha256"]
        )
        self.assertFalse(left.file_identity["held_out_values_read"])
        self.assertFalse(left.content_identity["includes_held_out_months"])

    def test_loader_requests_only_training_columns(self) -> None:
        path = fx.write_demand_table(
            self.root / "source.parquet",
            "r2",
            fx.DEFAULT_CONTEXTS,
            fx.DEFAULT_SKILLS,
            fx.canonical_observations(),
            held_out_value=float("nan"),
        )
        import pandas as pd

        original = pd.read_parquet
        requested: list[list[str]] = []

        def wrapper(*args, **kwargs):
            requested.append(list(kwargs.get("columns", [])))
            return original(*args, **kwargs)

        with mock.patch("pandas.read_parquet", side_effect=wrapper):
            loaded = osg_data.load_training(path, fixture=True)
        self.assertTrue(requested)
        columns = requested[0]
        held_out = protocol.MONTHS[protocol.N_TRAIN_MONTHS :]
        self.assertFalse(any(month in columns for month in held_out))
        self.assertTrue(all(month in columns for month in protocol.TRAIN_MONTHS))
        np.testing.assert_array_equal(loaded.skills, np.array([1, 4, 7, 10]))

    def test_unread_held_out_nan_is_accepted(self) -> None:
        path = fx.write_demand_table(
            self.root / "nan-held-out.parquet",
            "r2",
            fx.DEFAULT_CONTEXTS,
            fx.DEFAULT_SKILLS,
            fx.canonical_observations(),
            held_out_value=float("nan"),
        )
        loaded = osg_data.load_training(path, fixture=True)
        self.assertEqual(loaded.observations.shape[2], 27)


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.path = fx.write_demand_table(
            self.root / "source.parquet",
            "r2",
            fx.DEFAULT_CONTEXTS,
            fx.DEFAULT_SKILLS,
            fx.canonical_observations(),
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _mutate(self, mutator) -> Path:
        import pandas as pd

        frame = pd.read_parquet(self.path)
        frame = mutator(frame)
        path = self.root / "bad.parquet"
        frame.to_parquet(path, index=False)
        return path

    def test_duplicate_keys_rejected(self) -> None:
        def duplicate(frame):
            frame = frame.copy()
            frame.loc[1, "skill_id"] = frame.loc[0, "skill_id"]
            return frame

        path = self._mutate(duplicate)
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_training(path, fixture=True)

    def test_fractional_keys_rejected(self) -> None:
        path = self._mutate(
            lambda frame: frame.assign(skill_id=frame["skill_id"].astype(float) + 0.5)
        )
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_training(path, fixture=True)

    def test_incomplete_grid_rejected(self) -> None:
        path = self._mutate(lambda frame: frame.iloc[1:].reset_index(drop=True))
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_training(path, fixture=True)

    def test_missing_month_rejected(self) -> None:
        path = self._mutate(lambda frame: frame.drop(columns=["2023-12"]))
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_training(path, fixture=True)

    def test_extra_month_rejected(self) -> None:
        path = self._mutate(lambda frame: frame.assign(**{"2024-01": 0.0}))
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_training(path, fixture=True)

    def test_negative_training_value_rejected(self) -> None:
        path = self._mutate(lambda frame: frame.assign(**{"2021-01": -1.0}))
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_training(path, fixture=True)

    def test_nonfinite_training_value_rejected(self) -> None:
        path = self._mutate(lambda frame: frame.assign(**{"2022-05": np.nan}))
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_training(path, fixture=True)

    def test_published_assertions_reject_small_fixture(self) -> None:
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_training(self.path, fixture=False)

    def test_published_assertions_accept_expected_ranges(self) -> None:
        osg_data.assert_published_training(
            np.asarray(protocol.EXPECTED_OCCUPATION_IDS),
            np.asarray(protocol.EXPECTED_SKILL_IDS),
            "published",
        )
        with self.assertRaises(osg_data.SourceError):
            osg_data.assert_published_training(
                np.arange(51), np.asarray(protocol.EXPECTED_SKILL_IDS), "short"
            )
        with self.assertRaises(osg_data.SourceError):
            osg_data.assert_published_training(
                np.asarray(protocol.EXPECTED_OCCUPATION_IDS),
                np.arange(2334),
                "short skills",
            )

    def test_empty_source_rejected(self) -> None:
        import pandas as pd

        path = self.root / "empty.parquet"
        pd.read_parquet(self.path).iloc[0:0].to_parquet(path, index=False)
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_training(path, fixture=True)

    def test_unsupported_scope_rejected(self) -> None:
        with self.assertRaises(protocol.ProtocolError):
            osg_data.load_training(self.path, fixture=True, source="r0")
        with self.assertRaises(protocol.ProtocolError):
            osg_data.load_training(self.path, fixture=True, mode="rate")
        with self.assertRaises(protocol.ProtocolError):
            osg_data.load_training(self.path, fixture=True, fold="A")
        with self.assertRaises(protocol.ProtocolError):
            osg_data.load_training(
                self.path, fixture=True, protocol_version="P2-other"
            )
        with self.assertRaises(osg_data.SourceError):
            osg_data.load_training(self.root / "missing.parquet", fixture=True)


class OldEntryCompatibilityTests(unittest.TestCase):
    def test_old_constants_and_float32_loader_unchanged(self) -> None:
        self.assertEqual(tuple(p01.MONTHS), tuple(protocol.MONTHS))
        self.assertEqual(
            tuple(p01.TRAIN_OBSERVATION_MONTHS), tuple(protocol.TRAIN_MONTHS)
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = fx.write_demand_table(
                root / "all-finite.parquet",
                "r2",
                fx.DEFAULT_CONTEXTS,
                fx.DEFAULT_SKILLS,
                fx.canonical_observations(),
                held_out_value=0.0,
            )
            old = p01_data.load_demand("r2", demand_path=path)
            self.assertEqual(old.signal.dtype, np.float32)
            self.assertEqual(old.signal.shape, (8, 36))
            new = osg_data.load_training(path, fixture=True)
            self.assertEqual(new.observations.dtype, np.float64)
            self.assertEqual(new.observations.shape, (2, 4, 27))


if __name__ == "__main__":
    unittest.main()
