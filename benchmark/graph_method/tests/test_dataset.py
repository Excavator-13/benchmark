"""Unit tests for :mod:`dataset` (task 1.3)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import numpy as np  # noqa: E402
import torch  # noqa: E402

import dataset as dataset_module  # noqa: E402
from dataset import DatasetLoader, GraphDatasetError, build_snapshots, validate_payload  # noqa: E402


def payload(**overrides):
    """Two nodes and five time slices, so a 2/1 window yields three snapshots."""
    value = {
        "schema_version": 1,
        "data_name": "r0",
        "mode": "rate",
        "node_keys": [[0, 10], [0, 11]],
        "features": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0]],
        "edges": [[0, 1], [1, 0]],
        "edge_weights": [1.0, 2.0],
    }
    value.update(overrides)
    return value


class SnapshotShapeTests(unittest.TestCase):
    def test_snapshot_count_and_shapes(self):
        inputs, targets = build_snapshots(payload(), lags=2, pred_length=1)
        self.assertEqual(len(inputs), 5 - 2 - 1 + 1)
        self.assertEqual(len(targets), len(inputs))
        self.assertEqual(inputs[0].shape, (2, 2))
        self.assertEqual(targets[0].shape, (2, 1))
        np.testing.assert_allclose(inputs[0], [[1.0, 3.0], [2.0, 4.0]])
        np.testing.assert_allclose(targets[0], [[5.0], [6.0]])

    def test_default_window_matches_documented_formula(self):
        big = payload(features=[[float(t), float(t) + 0.5] for t in range(36)])
        inputs, targets = build_snapshots(big, lags=6, pred_length=3)
        self.assertEqual(len(inputs), 36 - 6 - 3 + 1)
        self.assertEqual(inputs[-1].shape, (2, 6))
        self.assertEqual(targets[-1].shape, (2, 3))

    def test_windows_do_not_cross_the_end_of_the_timeline(self):
        inputs, targets = build_snapshots(payload(), lags=2, pred_length=2)
        self.assertEqual(len(inputs), 2)
        np.testing.assert_allclose(inputs[-1], [[3.0, 5.0], [4.0, 6.0]])
        np.testing.assert_allclose(targets[-1], [[7.0, 9.0], [8.0, 10.0]])

    def test_exact_fit_still_yields_one_snapshot(self):
        inputs, targets = build_snapshots(payload(), lags=3, pred_length=2)
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0].shape, (2, 3))
        self.assertEqual(targets[0].shape, (2, 2))


class InvalidWindowTests(unittest.TestCase):
    def test_non_positive_lags_are_rejected(self):
        for bad in (0, -1):
            with self.subTest(lags=bad), self.assertRaises(GraphDatasetError):
                build_snapshots(payload(), lags=bad, pred_length=1)

    def test_non_positive_pred_length_is_rejected(self):
        for bad in (0, -3):
            with self.subTest(pred_length=bad), self.assertRaises(GraphDatasetError):
                build_snapshots(payload(), lags=1, pred_length=bad)

    def test_window_longer_than_timeline_is_rejected(self):
        with self.assertRaises(GraphDatasetError) as caught:
            build_snapshots(payload(), lags=4, pred_length=4)
        self.assertIn("available observations", str(caught.exception))

    def test_non_integer_window_is_rejected(self):
        with self.assertRaises(GraphDatasetError):
            build_snapshots(payload(), lags=2.5, pred_length=1)


class IntegrityTests(unittest.TestCase):
    def test_future_schema_version_is_rejected_with_regeneration_hint(self):
        with self.assertRaises(GraphDatasetError) as caught:
            validate_payload(payload(schema_version=2))
        message = str(caught.exception)
        self.assertIn("schema_version", message)
        self.assertIn("prepare_graph_data.py", message)

    def test_legacy_unversioned_payload_is_rejected(self):
        legacy = payload()
        del legacy["schema_version"]
        with self.assertRaises(GraphDatasetError):
            validate_payload(legacy)

    def test_missing_field_is_rejected(self):
        broken = payload()
        del broken["edge_weights"]
        with self.assertRaises(GraphDatasetError) as caught:
            validate_payload(broken)
        self.assertIn("edge_weights", str(caught.exception))

    def test_edge_weight_length_mismatch_is_rejected(self):
        with self.assertRaises(GraphDatasetError) as caught:
            validate_payload(payload(edge_weights=[1.0]))
        self.assertIn("edge weights", str(caught.exception))

    def test_out_of_range_edge_index_is_rejected(self):
        with self.assertRaises(GraphDatasetError) as caught:
            validate_payload(payload(edges=[[0, 5]], edge_weights=[1.0]))
        self.assertIn("range", str(caught.exception))

    def test_non_finite_feature_is_rejected(self):
        broken = payload()
        broken["features"][0][1] = float("inf")
        with self.assertRaises(GraphDatasetError) as caught:
            validate_payload(broken)
        self.assertIn("finite", str(caught.exception))

    def test_non_finite_edge_weight_is_rejected(self):
        with self.assertRaises(GraphDatasetError):
            validate_payload(payload(edge_weights=[1.0, float("nan")]))

    def test_duplicate_node_keys_are_rejected(self):
        with self.assertRaises(GraphDatasetError) as caught:
            validate_payload(payload(node_keys=[[0, 10], [0, 10]]))
        self.assertIn("duplicate node key", str(caught.exception))

    def test_feature_row_length_mismatch_is_rejected(self):
        with self.assertRaises(GraphDatasetError) as caught:
            validate_payload(payload(features=[[1.0], [3.0, 4.0]]))
        self.assertIn("expected", str(caught.exception))

    def test_loading_failure_precedes_snapshot_construction(self):
        broken = payload(edge_weights=[])
        with self.assertRaises(GraphDatasetError):
            build_snapshots(broken, lags=2, pred_length=1)


class LoaderTests(unittest.TestCase):
    def write(self, directory, value, data_name="r0", mode="rate"):
        destination = Path(directory) / mode / f"{data_name}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(value), encoding="utf-8")
        return destination

    def test_missing_artifact_reports_regeneration_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            loader = DatasetLoader("r0", "rate", data_dir=Path(tmp))
            with self.assertRaises(FileNotFoundError) as caught:
                loader.get_dataset(lags=2, pred_length=1)
            self.assertIn("prepare_graph_data.py", str(caught.exception))

    def test_signal_exposes_count_shapes_and_aligned_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, payload())
            loader = DatasetLoader("r0", "rate", data_dir=Path(tmp))
            signal = loader.get_dataset(lags=2, pred_length=1)
            self.assertEqual(signal.snapshot_count, 3)
            snapshot = signal[0]
            self.assertIsInstance(snapshot.x, torch.Tensor)
            self.assertEqual(tuple(snapshot.x.shape), (2, 2))
            self.assertEqual(tuple(snapshot.y.shape), (2, 1))
            self.assertEqual(tuple(snapshot.edge_index.shape), (2, 2))
            self.assertEqual(tuple(snapshot.edge_attr.shape), (2,))
            self.assertAlmostEqual(float(snapshot.edge_attr[1]), 2.0)

    def test_slicing_keeps_temporal_dimension(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, payload())
            loader = DatasetLoader("r0", "rate", data_dir=Path(tmp))
            signal = loader.get_dataset(lags=2, pred_length=1)
            train = signal[0:2]
            test = signal[2:3]
            self.assertEqual(train.snapshot_count, 2)
            self.assertEqual(test.snapshot_count, 1)

    def test_empty_edge_set_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, payload(edges=[], edge_weights=[]))
            signal = DatasetLoader("r0", "rate", data_dir=Path(tmp)).get_dataset(lags=2, pred_length=1)
            self.assertEqual(tuple(signal[0].edge_index.shape), (2, 0))
            self.assertEqual(tuple(signal[0].edge_attr.shape), (0,))

    def test_loader_paths_are_mode_and_granularity_specific(self):
        self.assertEqual(
            dataset_module.dataset_path("r1", "count"),
            dataset_module.DEFAULT_DATA_DIR / "count" / "r1.json",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
