"""Bounded production-code/CLI verification: r0 only, three epochs per run.

Run from any directory with the project's Python environment. This does not
load isolated copies or patch the model/training/splitting functions.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GRAPH = ROOT / "benchmark" / "graph_method"
sys.path.insert(0, str(GRAPH))
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import pandas as pd
import torch
from torch_geometric_temporal.signal import StaticGraphTemporalSignal

import main
from dataset import DatasetLoader, build_snapshots
import prepare_graph_data as prep


def save_json(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def verify_dates():
    months = sorted(c for c in pd.read_parquet(ROOT / "dataset" / "demand" / "r0.parquet").columns
                    if prep.TIME_COLUMN_PATTERN.match(c))
    payload = {"schema_version": 1, "data_name": "r0", "mode": "count",
               "node_keys": [[0, 0]], "edges": [], "edge_weights": [],
               "features": [[float(i)] for i in range(len(months))]}
    x, y = build_snapshots(payload, lags=6, pred_length=3)
    signal = StaticGraphTemporalSignal(np.empty((2, 0), dtype=np.int64), np.empty(0), x, y)
    splits = main.temporal_signal_split(signal)
    dates = [{int(t) for snapshot in part for t in snapshot.y[0]} for part in splits]
    assert max(dates[0]) < min(dates[1]) and max(dates[1]) < min(dates[2])
    assert max(dates[0]) <= int(splits[1][0].x[0, -1])
    assert max(dates[1]) <= int(splits[2][0].x[0, -1])
    save_json("target-periods.json", {
        "counts": [part.snapshot_count for part in splits],
        "target_months": {label: [months[i] for i in sorted(indices)]
                          for label, indices in zip(("train", "validation", "test"), dates)},
        "targets_disjoint": True, "labels_available_at_next_forecast_origin": True,
    })


def run_cli(mode, device, label, seed):
    config = main.ExperimentConfig(data_name="r0", mode=mode, device=device, seed=seed, num_epochs=3)
    source = main.result_dir(config)
    # Refuse to replace unrelated existing experiments. A repeat is allowed
    # only for the same mode/device/seed already started by this script.
    key = (mode, device, seed)
    if source.exists() and key not in run_cli.started:
        raise RuntimeError("Choose a fresh verification seed; results already exist: " + str(source))
    run_cli.started.add(key)
    command = [sys.executable, str(GRAPH / "main.py"), "--data_name", "r0", "--mode", mode,
               "--model_name", "EvolveGCNH", "--device", device, "--seed", str(seed), "--num_epochs", "3"]
    started = time.perf_counter()
    # Run outside the repository to check module-relative data/output lookup.
    with tempfile.TemporaryDirectory() as cwd, (HERE / (label + ".log")).open("w", encoding="utf-8") as log:
        completed = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy())
    if completed.returncode:
        raise RuntimeError(label + " failed; see its log")
    destination = HERE / "runs" / label
    shutil.copytree(source, destination)
    metrics = json.loads((destination / "metrics.json").read_text(encoding="utf-8"))
    assert all(math.isfinite(value) for value in metrics.values())
    loaded = main.load_checkpoint(destination / "checkpoint.pt", torch.device("cpu"))
    assert loaded.seed == seed and math.isfinite(loaded.best_val_loss)
    payload = torch.load(destination / "checkpoint.pt", map_location="cpu", weights_only=True)
    assert payload["format_version"] == 2 and payload["best_val_loss"].ndim == 0
    assert "recurrent.initial_weight" in payload["model_state_dict"]
    signal = DatasetLoader("r0", mode).get_dataset(lags=6, pred_length=3)
    splits = main.temporal_signal_split(signal)
    assert [part.snapshot_count for part in splits] == [19, 1, 4]
    predictions = [torch.load(destination / f"pred_{i}.pt", weights_only=True) for i in range(4)]
    golds = [torch.load(destination / f"gold_{i}.pt", weights_only=True) for i in range(4)]
    assert len(list(destination.glob("pred_*.pt"))) == len(list(destination.glob("gold_*.pt"))) == 4
    assert main.regression_metrics(predictions, golds) == metrics
    for gold, snapshot in zip(golds, splits[2]):
        assert torch.equal(gold, snapshot.y)
    cross_device = "cpu" if device.startswith("cuda") else "cuda:0"
    max_delta = None
    if cross_device == "cpu" or torch.cuda.is_available():
        restored = main.load_checkpoint(destination / "checkpoint.pt", torch.device(cross_device))
        result = main.run_split(restored.model, splits[2], torch.device(cross_device), collect_predictions=True)
        max_delta = max(float((a - b).abs().max()) for a, b in zip(predictions, result.predictions))
        for expected, actual in zip(predictions, result.predictions):
            torch.testing.assert_close(actual, expected, rtol=1e-4, atol=1e-2 if mode == "count" else 1e-6)
    record = {"label": label, "mode": mode, "device": device, "seed": seed, "epochs": 3,
              "command": command, "metrics": metrics, "validation_loss": loaded.best_val_loss,
              "split_sizes": [19, 1, 4], "checkpoint_format": payload["format_version"],
              "cross_device_max_absolute_difference": max_delta,
              "wall_seconds_including_subprocess_startup": time.perf_counter() - started,
              "results": str(destination)}
    print(json.dumps(record), flush=True)
    return record


run_cli.started = set()


def run():
    verify_dates()
    preparation = []
    for mode in ("rate", "count"):
        destination = prep.prepare_dataset("r0", mode)
        signal = DatasetLoader("r0", mode).get_dataset(lags=6, pred_length=3)
        assert signal.snapshot_count == 28
        preparation.append({"mode": mode, "nodes": signal[0].x.shape[0],
                            "edges": signal[0].edge_index.shape[1], "path": str(destination)})
    save_json("prepared-r0.json", preparation)
    configurations = [("rate", "cpu", "final-rate-cpu-a", 202609221),
                      ("rate", "cpu", "final-rate-cpu-b", 202609221),
                      ("count", "cpu", "final-count-cpu", 202609221)]
    if torch.cuda.is_available():
        configurations.extend([("rate", "cuda:0", "final-rate-cuda", 202609222),
                               ("count", "cuda:0", "final-count-cuda", 202609222)])
    records = []
    for mode, device, label, seed in configurations:
        records.append(run_cli(mode, device, label, seed))
        save_json("cli-runs.json", records)
    first, second = (Path(record["results"]) for record in records[:2])
    assert records[0]["metrics"] == records[1]["metrics"]
    for i in range(4):
        assert torch.equal(torch.load(first / f"pred_{i}.pt", weights_only=True),
                           torch.load(second / f"pred_{i}.pt", weights_only=True))
    save_json("repeatability.json", {"identical_cpu_metrics": True, "identical_cpu_predictions": True})
    save_json("source-hashes.json", {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (GRAPH / "main.py", GRAPH / "dataset.py", GRAPH / "models" / "evolvegcnh.py")
    })
    print("PASS: production CLI, Unicode outputs, disjoint target periods, device mapping and CPU repeatability", flush=True)


if __name__ == "__main__":
    run()
