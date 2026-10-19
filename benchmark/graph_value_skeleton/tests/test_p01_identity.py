"""P01 identity preservation and fixed-mask reuse (tasks 1.1/1.2/2.3/5.4)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from benchmark.graph_value_skeleton import data as gvs_data
from benchmark.graph_value_skeleton import graph as gvs_graph
from benchmark.graph_value_skeleton import protocol
from benchmark.graph_value_skeleton import shuffle as gvs_shuffle
from benchmark.graph_value_skeleton.tests import fixtures
from benchmark.nograph_baseline import baselines as p01_baselines
from benchmark.nograph_baseline import coverage as p01_coverage
from benchmark.nograph_baseline import data as p01_data
from benchmark.nograph_baseline import metrics as p01_metrics
from benchmark.nograph_baseline import protocol as p01
from benchmark.nograph_baseline import ridge as p01_ridge


class P01IdentityTest(unittest.TestCase):
    """The new package must reproduce P01's identity contract exactly."""

    def test_demand_identity_matches_p01(self) -> None:
        for data_name in fixtures.SCHEMAS:
            with self.subTest(dataset=data_name):
                keys = fixtures.keys_for(data_name)
                signal = fixtures.signal_for(len(keys))
                p01_demand = p01_data.from_arrays(
                    data_name,
                    keys,
                    signal,
                    source_path="<fixture>",
                    source_sha256="fixture",
                )
                new = gvs_data.from_fixture(data_name, keys, signal)
                self.assertEqual(new.demand.keys, p01_demand.keys)
                self.assertEqual(
                    p01_data.node_keys_sha256(new.key_array),
                    p01_data.node_keys_sha256(p01_demand.key_array),
                )
                self.assertEqual(
                    p01_data.node_keys_sha256(new.key_array),
                    new.demand.identity_payload()["node_keys_sha256"],
                )
                np.testing.assert_array_equal(new.signal, p01_demand.signal)
                self.assertEqual(new.signal.dtype, np.float32)
                for starts in (
                    p01.ALL_STARTS,
                    p01.MAIN_SPLIT.train_starts,
                    p01.MAIN_SPLIT.validation_starts,
                    p01.MAIN_SPLIT.evaluation_starts,
                ):
                    np.testing.assert_array_equal(
                        new.input_windows(starts), p01_demand.input_windows(starts)
                    )
                    np.testing.assert_array_equal(
                        new.target_windows(starts), p01_demand.target_windows(starts)
                    )
                self.assertEqual(
                    protocol.window_metadata(), p01.build_window_metadata(p01.MAIN_SPLIT)
                )
                self.assertEqual(new.audit["nodes"], p01_demand.audit["nodes"])
                self.assertEqual(
                    new.audit["activity_group_counts"],
                    p01_demand.audit["activity_group_counts"],
                )

    def test_integer_order_places_2_before_10(self) -> None:
        keys = [(0, 2), (0, 10), (0, 1)]
        signal = np.arange(len(keys) * 36, dtype=np.float32).reshape(len(keys), 36)
        dataset = gvs_data.from_fixture("r0", keys, signal)
        self.assertEqual(dataset.key_array[:, -1].tolist(), [1, 2, 10])
        # Context-qualified identity keeps the same skill under two contexts apart.
        multi = gvs_data.from_fixture(
            "region",
            [(0, 2), (1, 2), (0, 10), (1, 10)],
            np.arange(4 * 36, dtype=np.float32).reshape(4, 36),
        )
        self.assertEqual(
            multi.key_array.tolist(), [[0, 2], [0, 10], [1, 2], [1, 10]]
        )

    def test_invalid_fixture_inputs_rejected(self) -> None:
        keys = [(0, 0), (0, 1)]
        good = np.ones((2, 36), dtype=np.float32)
        with self.assertRaises(gvs_data.DatasetError):
            gvs_data.from_fixture("r0", keys, -good)
        with self.assertRaises(gvs_data.DatasetError):
            gvs_data.from_fixture("r0", keys, np.full((2, 36), np.nan))
        with self.assertRaises(gvs_data.DatasetError):
            gvs_data.from_fixture("r0", [(0, 0), (0, 0)], good)
        with self.assertRaises(gvs_data.DatasetError):
            gvs_data.from_fixture("r0", keys, good[:, :35])
        with self.assertRaises(protocol.ProtocolError):
            gvs_data.from_fixture("company", keys, good)
        # A demand file with a missing month column is rejected by the loader.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = fixtures.build_fixture(root, "r0")
            import pandas as pd

            frame = pd.read_parquet(fixture["demand_path"])
            frame = frame.drop(columns=["2022-05"])
            broken = root / "broken-demand.parquet"
            frame.to_parquet(broken, index=False)
            with self.assertRaises(gvs_data.DatasetError):
                gvs_data.load_dataset("r0", demand_path=broken, published=False)

    def test_naive_reference_matches_p01(self) -> None:
        for data_name in fixtures.SCHEMAS:
            with self.subTest(dataset=data_name):
                fixture = fixtures.build_fixture(
                    Path(tempfile.mkdtemp(prefix="gvs-id-")), data_name
                )
                dataset, _ = fixtures.load_fixture(fixture)
                predictions, scores, references, frozen_mean = (
                    gvs_data.naive_reference_block(dataset)
                )
                p01_predictions = p01_baselines.naive_predictions(
                    dataset.signal,
                    p01.MAIN_SPLIT.validation_starts,
                    frozen_train_mean=p01_baselines.train_mean(dataset.signal, 27),
                )
                for name, prediction in p01_predictions.items():
                    np.testing.assert_array_equal(prediction, predictions[name])
                p01_scores = p01_baselines.validation_mse(
                    p01_predictions, dataset.target_windows(p01.MAIN_SPLIT.validation_starts)
                )
                self.assertEqual(scores, p01_scores)
                expected = p01_baselines.select_references(p01_scores)
                self.assertEqual(references["NaiveRef"], expected["NaiveRef"])
                self.assertEqual(references["NaiveRef6"], expected["NaiveRef6"])
                self.assertEqual(
                    references["NaiveRef"],
                    min(scores, key=lambda name: (scores[name], p01.NAIVE_METHODS.index(name))),
                )
                self.assertEqual(frozen_mean.shape, (dataset.node_count, 1))
                # A published dataset whose reference is not LastValue must fail.
                published = gvs_data.SkeletonDataset(
                    demand=dataset.demand,
                    published=True,
                    audit=dataset.audit,
                    publication={"fixture": True},
                )
                if references["NaiveRef"] != protocol.NAIVE_REF_PUBLISHED:
                    with self.assertRaises(gvs_data.DatasetError):
                        gvs_data.naive_reference_block(published)

    def test_zero_reference_gain_is_unavailable(self) -> None:
        gain = p01_metrics.relative_gain(1.0, 0.0)
        self.assertIsNone(gain["relative_MAE_gain"])
        self.assertEqual(gain["status"], p01_metrics.UNAVAILABLE_STATUS)
        self.assertIn("zero", gain["reason"])

    def test_shared_masks_match_p01(self) -> None:
        for data_name in fixtures.SCHEMAS:
            with self.subTest(dataset=data_name):
                fixture = fixtures.build_fixture(
                    Path(tempfile.mkdtemp(prefix="gvs-mask-")), data_name
                )
                dataset, _ = fixtures.load_fixture(fixture)
                coverage = p01_coverage.load_graph_coverage(
                    data_name, dataset.key_array, graph_path=fixture["graph_path"]
                )
                masks = gvs_data.build_masks(dataset, coverage)
                stats = p01_ridge.compute_training_stats(dataset.signal)
                np.testing.assert_array_equal(masks.activity, stats.activity)
                np.testing.assert_array_equal(masks.constant_mask, stats.constant_mask)
                for name in p01.ACTIVITY_GROUP_NAMES:
                    np.testing.assert_array_equal(
                        masks.activity_groups[name], stats.activity_groups[name]
                    )
                np.testing.assert_array_equal(masks.neighbor_mask, coverage.mask)
                counts = {
                    name: int(mask.sum()) for name, mask in masks.activity_groups.items()
                }
                self.assertEqual(
                    sorted(counts), sorted(p01.ACTIVITY_GROUP_NAMES)
                )
                self.assertEqual(sum(counts.values()), dataset.node_count)
                # All four activity groups are exercised by the boundary rows.
                self.assertTrue(all(value > 0 for value in counts.values()))
                self.assertGreater(int(masks.neighbor_mask.sum()), 0)
                self.assertFalse(masks.payload["recomputed_from_shuffled_adjacency"])
                self.assertEqual(
                    masks.payload["shared_by_methods"], list(protocol.METHODS)
                )
                # The shuffled adjacency must never redefine the evaluation groups.
                shuffled = gvs_shuffle.shuffle_graph(
                    data_name, dataset.key_array, gvs_graph.canonical_edge_array(
                        fixtures.unique_edges(fixture)
                    ), 1
                )
                shuffled_masks = gvs_data.build_masks(dataset, coverage)
                self.assertEqual(masks.hashes(), shuffled_masks.hashes())
                self.assertFalse(shuffled.audit["model_rng_consumed"])


if __name__ == "__main__":
    unittest.main()
