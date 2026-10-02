"""Opt-in integration checks over the shipped Job-SDF graph data (tasks 1.4 and 4.3).

These tests read (and optionally generate) the real Parquet sources, so they are
skipped unless ``JOB_SDF_INTEGRATION`` is set to a truthy value. Run them with::

    JOB_SDF_INTEGRATION=1 .venv-graph/bin/python -m unittest discover \\
        -s benchmark/graph_method/tests -p "test_generated_datasets.py"

Set ``JOB_SDF_DATA_DIR`` to verify an already-generated directory (the one that
contains ``<mode>/<granularity>.json``) instead of regenerating everything.
"""

from __future__ import annotations

import gc
import os
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import dataset as dataset_module  # noqa: E402
import main  # noqa: E402
import prepare_graph_data as prep  # noqa: E402
from dataset import DatasetLoader, validate_payload  # noqa: E402

INTEGRATION_ENABLED = os.environ.get("JOB_SDF_INTEGRATION", "").strip().lower() in {
    "1",
    "true",
    "yes",
}
SKIP_REASON = "set JOB_SDF_INTEGRATION=1 to check the shipped Job-SDF data"

DEFAULT_WINDOW = 6
DEFAULT_PRED_LENGTH = 3
EXPECTED_COMBINATIONS = len(prep.GRANULARITIES) * len(prep.MODES)


def _source_graph_rows(data_name: str, mode: str) -> int:
    """Number of directed source rows the generated edge weights must preserve."""
    _, graph_path = prep.source_paths(data_name, mode)
    frame = prep._read_parquet(graph_path)
    return len(prep._column_values(frame, prep.ROW_COLUMN))


def _summarize(data_dir: Path, data_name: str, mode: str) -> dict:
    """Load one artifact with the default window and check schema, integrity and splits."""
    payload = dataset_module.load_payload(data_name, mode, data_dir=data_dir)
    validate_payload(payload)

    node_count = len(payload["node_keys"])
    signal = DatasetLoader(data_name, mode, data_dir=data_dir).get_dataset(
        lags=DEFAULT_WINDOW, pred_length=DEFAULT_PRED_LENGTH
    )
    train, evaluation, test = main.temporal_signal_split(signal, 0.83, 0.04)
    splits = {
        "train": train.snapshot_count,
        "validation": evaluation.snapshot_count,
        "test": test.snapshot_count,
    }
    if min(splits.values()) < 1:
        raise AssertionError(f"{data_name}/{mode}: empty partition {splits}")

    snapshot = signal[0]
    if tuple(snapshot.edge_index.shape)[0] != 2:
        raise AssertionError(f"{data_name}/{mode}: edge_index is not [2, E]")
    if snapshot.edge_index.shape[1] != snapshot.edge_attr.shape[0]:
        raise AssertionError(f"{data_name}/{mode}: edge index and weight counts differ")
    if tuple(snapshot.x.shape) != (node_count, DEFAULT_WINDOW):
        raise AssertionError(f"{data_name}/{mode}: feature shape {tuple(snapshot.x.shape)}")
    if tuple(snapshot.y.shape) != (node_count, DEFAULT_PRED_LENGTH):
        raise AssertionError(f"{data_name}/{mode}: target shape {tuple(snapshot.y.shape)}")

    source_rows = _source_graph_rows(data_name, mode)
    weight_total = float(sum(payload["edge_weights"]))
    if weight_total != float(source_rows):
        raise AssertionError(
            f"{data_name}/{mode}: edge weights total {weight_total}, expected {source_rows} source rows"
        )

    return {
        "nodes": node_count,
        "times": len(payload["features"]),
        "edges": len(payload["edges"]),
        "source_rows": source_rows,
        "snapshots": signal.snapshot_count,
        "splits": splits,
    }


def _verify_every_combination(output_dir: Path) -> dict:
    summaries = {}
    for mode in prep.MODES:
        for data_name in prep.GRANULARITIES:
            summaries[f"{data_name}/{mode}"] = _summarize(output_dir, data_name, mode)
            gc.collect()
    return summaries


@unittest.skipUnless(INTEGRATION_ENABLED, SKIP_REASON)
class ShippedDataIntegrationTests(unittest.TestCase):
    """Task 1.4: the default combination prepares and loads from a clean directory."""

    def test_default_r0_rate_artifact_is_created_and_loadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = prep.prepare_dataset("r0", "rate", output_dir=Path(tmp))
            self.assertTrue(destination.is_file())
            summary = _summarize(Path(tmp), "r0", "rate")
        self.assertGreater(summary["nodes"], 0)
        self.assertGreater(summary["edges"], 0)


@unittest.skipUnless(INTEGRATION_ENABLED, SKIP_REASON)
class EveryShippedCombinationTests(unittest.TestCase):
    """Task 4.3: every shipped granularity/mode artifact is valid and splittable."""

    def test_all_fourteen_combinations(self):
        configured = os.environ.get("JOB_SDF_DATA_DIR")
        if configured:
            summaries = _verify_every_combination(Path(configured))
        else:
            with tempfile.TemporaryDirectory() as generated:
                output_dir = Path(generated)
                for mode in prep.MODES:
                    for data_name in prep.GRANULARITIES:
                        prep.prepare_dataset(data_name, mode, output_dir=output_dir)
                summaries = _verify_every_combination(output_dir)

        self.assertEqual(len(summaries), EXPECTED_COMBINATIONS)
        for key, summary in summaries.items():
            with self.subTest(combination=key):
                self.assertGreater(summary["nodes"], 0)
                self.assertGreater(summary["times"], DEFAULT_WINDOW + DEFAULT_PRED_LENGTH)
                self.assertGreater(summary["edges"], 0)
                self.assertTrue(all(count > 0 for count in summary["splits"].values()), summary)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
