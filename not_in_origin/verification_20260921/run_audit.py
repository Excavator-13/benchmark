"""Independent, bounded verification; original graph-method sources stay unchanged.

Run with D:/conda-envs/JOBSDF/python.exe and one phase: original, compat, real.
The compat/real phases use explicit reviewable source copies, not production edits.
"""
from __future__ import annotations

import argparse
import difflib
import gc
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GRAPH = ROOT / "benchmark" / "graph_method"
sys.path.insert(0, str(GRAPH))
sys.path.insert(0, str(GRAPH / "tests"))
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch


def write_json(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def isolated_module(name, path, changes):
    original = path.read_text(encoding="utf-8")
    source = original
    for old, new in changes:
        if source.count(old) != 1:
            raise RuntimeError("replacement must be unique: " + repr(old))
        source = source.replace(old, new)
    copies = HERE / "isolated"
    copies.mkdir(exist_ok=True)
    copy = copies / (name + ".py")
    copy.write_text(source, encoding="utf-8")
    (copies / (name + ".diff")).write_text("".join(difflib.unified_diff(
        original.splitlines(True), source.splitlines(True),
        fromfile=str(path), tofile=str(copy))), encoding="utf-8")
    module = types.ModuleType(name)
    # Keep resource paths referring to the original dataset/README. Executed
    # code and tracebacks refer to the saved isolated copy above.
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(source, str(copy), "exec"), module.__dict__)
    return module


def compatibility_main():
    return isolated_module("main", GRAPH / "main.py", [
        ('"best_val_loss": float(best_val_loss),',
         '"best_val_loss": torch.tensor(best_val_loss, dtype=torch.float64),'),
        ('    torch.save(payload, path)',
         '    with path.open("wb") as handle:\n        torch.save(payload, handle)'),
        ('        torch.save(prediction, directory / f"pred_{time_index}.pt")',
         '        with (directory / f"pred_{time_index}.pt").open("wb") as handle:\n'
         '            torch.save(prediction, handle)'),
        ('        torch.save(gold, directory / f"gold_{time_index}.pt")',
         '        with (directory / f"gold_{time_index}.pt").open("wb") as handle:\n'
         '            torch.save(gold, handle)'),
    ])


def unit_tests(compat):
    if compat:
        compatibility_main()
        isolated_module("test_main", GRAPH / "tests" / "test_main.py", [
            ('                model = build_model(config, NUM_NODES)',
             '                model = build_model(config, NUM_NODES).to("cpu")'),
            ('                    "best_val_loss": 0.0,',
             '                    "best_val_loss": torch.tensor(0.0, dtype=torch.float64),'),
        ])
        isolated_module("test_prepare_graph_data", GRAPH / "tests" / "test_prepare_graph_data.py", [
            ('            os.chdir(tmp)\n'
             '            self.assertEqual(prep.output_path("r0", "rate"), expected)\n'
             '            self.assertEqual(prep.source_paths("r0", "rate")[0], prep.DATASET_DIR / "proportion" / "r0.parquet")',
             '            try:\n'
             '                os.chdir(tmp)\n'
             '                self.assertEqual(prep.output_path("r0", "rate"), expected)\n'
             '                self.assertEqual(prep.source_paths("r0", "rate")[0], prep.DATASET_DIR / "proportion" / "r0.parquet")\n'
             '            finally:\n'
             '                os.chdir(original)'),
        ])
    else:
        import test_prepare_graph_data
        method = test_prepare_graph_data.PathResolutionTests.test_paths_do_not_depend_on_working_directory
        test_prepare_graph_data.PathResolutionTests.test_paths_do_not_depend_on_working_directory = unittest.skip(
            "Already reproduced: Windows cannot delete the current directory; original test crashes the runner"
        )(method)
    names = ["test_dataset", "test_evolvegcnh", "test_generated_datasets", "test_main", "test_prepare_graph_data"]
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    label = "compat" if compat else "original"
    with (HERE / (label + "-unit-tests.log")).open("w", encoding="utf-8") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    summary = {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "skipped": [(str(t), reason) for t, reason in result.skipped],
               "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
               "successful": result.wasSuccessful(), "isolated_compatibility_copy": compat}
    write_json(label + "-unit-tests.json", summary)
    print(json.dumps(summary, indent=2), flush=True)


def temporal_probe(main, signal):
    import pandas as pd
    frame = pd.read_parquet(ROOT / "dataset" / "proportion" / "r0.parquet")
    months = sorted(c for c in frame.columns if c[:4] in {"2021", "2022", "2023"})
    sizes = main.split_sizes(signal.snapshot_count, 0.83, 0.04)
    indices = {}
    cursor = 0
    for label, size in zip(("train", "validation", "test"), sizes):
        indices[label] = set(i + 6 + lead for i in range(cursor, cursor + size) for lead in range(3))
        cursor += size
    result = {"split_sizes": list(sizes), "target_months": {k: [months[i] for i in sorted(v)] for k, v in indices.items()}}
    result["overlap"] = {a + "_" + b: [months[i] for i in sorted(indices[a] & indices[b])]
                         for a, b in (("train", "validation"), ("train", "test"), ("validation", "test"))}
    # Verify actual target tensors contain the same source month at the boundaries.
    result["actual_tensor_equalities"] = {
        "last_train_last_horizon_equals_first_test_first_horizon": torch.equal(signal[22].y[:, 2], signal[24].y[:, 0]),
        "validation_last_two_horizons_equal_first_test_first_two": torch.equal(signal[23].y[:, 1:], signal[24].y[:, :2]),
    }
    write_json("temporal-overlap.json", result)


def tiny_models(main):
    from test_main import synthetic_signal
    records = []
    for device in ("cpu", "cuda:0"):
        for name in main.MODEL_NAMES:
            record = {"model": name, "device": device}
            try:
                main.set_seed(17)
                config = main.ExperimentConfig(model_name=name, device=device, hidden_dim=8, num_epochs=2)
                model = main.build_model(config, 32).to(device)
                optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
                signal = synthetic_signal(snapshot_count=2)
                losses = []
                for epoch in range(2):
                    output = main.run_split(model, signal, torch.device(device), training=True, optimizer=optimizer)
                    losses.append(output.loss)
                assert all(math.isfinite(v) for v in losses)
                record.update(status="PASS", losses=losses)
            except Exception as exc:
                record.update(status="FAIL", error=repr(exc), traceback=traceback.format_exc())
            records.append(record)
            print("tiny", name, device, record["status"], flush=True)
    write_json("all-models-two-epochs.json", records)


def experiment(main, name, mode, device, label, epochs=3):
    config = main.ExperimentConfig(data_name=name, mode=mode, device=device, seed=17, num_epochs=epochs,
                                   results_dir=HERE / "runs" / label)
    started = time.perf_counter()
    signal = main.load_dataset(config)
    train, validation, test = main.temporal_signal_split(signal)
    calls = []
    gradients = []
    original_runner = main.run_split

    def observed(model, iterator, execution_device, **kwargs):
        role = "train" if iterator is train else "validation" if iterator is validation else "test"
        result = original_runner(model, iterator, execution_device, **kwargs)
        calls.append({"split": role, "loss": result.loss, "optimizer_steps": result.optimizer_steps})
        if kwargs.get("training"):
            grad = model.recurrent.initial_weight.grad
            gradients.append({"finite": grad is not None and bool(torch.isfinite(grad).all()),
                              "norm": float(grad.norm()) if grad is not None else None})
        return result

    if device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats()
    with mock.patch.object(main, "run_split", observed):
        metrics = main.train_experiment(config, train, validation, test, progress=False)
    directory = main.result_dir(config)
    payload = torch.load(directory / "checkpoint.pt", map_location="cpu", weights_only=True)
    predictions = [torch.load(directory / ("pred_%d.pt" % i), map_location="cpu", weights_only=True)
                   for i in range(test.snapshot_count)]
    golds = [torch.load(directory / ("gold_%d.pt" % i), map_location="cpu", weights_only=True)
             for i in range(test.snapshot_count)]
    assert all(math.isfinite(v) for v in metrics.values())
    assert calls[-1]["split"] == "test" and sum(c["split"] == "test" for c in calls) == 1
    assert all(g["finite"] for g in gradients)
    assert float(payload["best_val_loss"]) == min(c["loss"] for c in calls if c["split"] == "validation")
    assert main.regression_metrics(predictions, golds) == metrics
    # Evaluate the selected checkpoint on the other device to verify portability.
    other = torch.device("cpu" if device.startswith("cuda") else "cuda:0")
    restored = main.load_checkpoint(directory / "checkpoint.pt", other)
    mapped = original_runner(restored.model, test, other, collect_predictions=True)
    cross_device_delta = max(float((a - b).abs().max()) for a, b in zip(predictions, mapped.predictions))
    baseline = main.regression_metrics([s.x[:, -1:].repeat(1, 3) for s in test], golds)
    result = {"label": label, "data_name": name, "mode": mode, "device": device, "seed": 17, "epochs": epochs,
              "metrics": metrics, "last_value_baseline": baseline, "snapshots": signal.snapshot_count,
              "nodes": int(signal[0].x.shape[0]), "edges": int(signal[0].edge_index.shape[1]),
              "split_sizes": [s.snapshot_count for s in (train, validation, test)],
              "best_validation_loss": float(payload["best_val_loss"]), "calls": calls, "initial_weight_gradients": gradients,
              "cross_device_max_absolute_prediction_difference": cross_device_delta,
              "peak_cuda_allocated_mb": torch.cuda.max_memory_allocated() / 1024**2,
              "wall_seconds": time.perf_counter() - started, "result_directory": str(directory)}
    print(json.dumps(result, ensure_ascii=True), flush=True)
    del restored, mapped, signal, train, validation, test, payload
    gc.collect()
    torch.cuda.empty_cache()
    return result


def real_data():
    main = compatibility_main()
    import prepare_graph_data as prep
    from test_generated_datasets import _summarize
    data = []
    for name in ("r0", "region"):
        for mode in ("rate", "count"):
            print("prepare", name, mode, flush=True)
            prep.prepare_dataset(name, mode)
            summary = _summarize(prep.DEFAULT_OUTPUT_DIR, name, mode)
            summary.update(data_name=name, mode=mode)
            data.append(summary)
    write_json("real-data-four-combinations.json", data)
    temporal_probe(main, main.load_dataset(main.ExperimentConfig()))
    tiny_models(main)
    runs = []
    for name, mode, device, label in [
        ("r0", "rate", "cpu", "r0-rate-cpu-a"),
        ("r0", "rate", "cpu", "r0-rate-cpu-b"),
        ("r0", "rate", "cuda:0", "r0-rate-cuda"),
        ("r0", "count", "cpu", "r0-count-cpu"),
        ("r0", "count", "cuda:0", "r0-count-cuda"),
    ]:
        runs.append(experiment(main, name, mode, device, label))
        write_json("real-runs.json", runs)
    assert runs[0]["metrics"] == runs[1]["metrics"]
    first, second = (Path(run["result_directory"]) for run in runs[:2])
    matches = []
    for i in range(4):
        a = torch.load(first / ("pred_%d.pt" % i), weights_only=True)
        b = torch.load(second / ("pred_%d.pt" % i), weights_only=True)
        matches.append(torch.equal(a, b))
    write_json("cpu-repeatability.json", {"identical_metrics": True, "identical_predictions": matches})
    assert all(matches)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("original", "compat", "real"))
    args = parser.parse_args()
    if args.phase in {"original", "compat"}:
        unit_tests(args.phase == "compat")
    else:
        real_data()
