#!/usr/bin/env python3
"""T002 adjacency-sensitivity probe for the graph models used by the repository.

Protocol section 4.3: with the same input, parameters and initial recurrent
state, compare the output under the shipped-style adjacency with replacement
adjacencies, resetting state before every traversal and removing randomness.
Both the recurrent layer output and the full forecast output are checked.

What is probed:

* ``GConvGRU(K=1)`` and ``GConvLSTM(K=1)`` exactly as ``main.py`` builds them
  (third positional argument is ``K``), plus the full ``GraphForecaster`` head.
* ``EvolveGCNH`` from ``benchmark/graph_method/models/evolvegcnh.py`` plus the
  full head.
* A clearly labelled ``K=2`` positive control that must show a difference, to
  prove the probe can detect adjacency use at all.

Not probed / not changed: no training, no formal run, no repository source
edits, no overwrite of any archived artifact.  Small deterministic CPU tensors
only.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch_geometric

REPO_ROOT = Path(__file__).resolve().parents[3]
GRAPH_METHOD = REPO_ROOT / "benchmark" / "graph_method"
sys.path.insert(0, str(GRAPH_METHOD))

NUM_NODES = 32
IN_CHANNELS = 6
HIDDEN_DIM = 8
PRED_LENGTH = 3
NUM_EDGES = 96
TOLERANCE = 1e-6
SEED = 20261011


def make_adjacencies() -> dict[str, torch.Tensor]:
    """Deterministic adjacency variants over NUM_NODES nodes."""
    generator = np.random.default_rng(SEED)
    sources = generator.integers(0, NUM_NODES, size=NUM_EDGES)
    targets = generator.integers(0, NUM_NODES, size=NUM_EDGES)
    keep = sources != targets
    sources, targets = sources[keep], targets[keep]
    base = torch.tensor(np.stack([sources, targets]), dtype=torch.long)

    ring = torch.tensor(
        np.stack([
            np.concatenate([np.arange(NUM_NODES), np.arange(NUM_NODES)]),
            np.concatenate([(np.arange(NUM_NODES) + 1) % NUM_NODES,
                            (np.arange(NUM_NODES) - 1) % NUM_NODES]),
        ]), dtype=torch.long,
    )
    # A shift of the ring's destinations keeps the edge count but changes the
    # neighbours of almost every node.
    shift = NUM_NODES // 2 + 1
    shuffled = ring.clone()
    shuffled[1] = (ring[1] + shift) % NUM_NODES
    empty = torch.zeros((2, 0), dtype=torch.long)
    star = torch.tensor(
        np.stack([
            np.concatenate([np.zeros(NUM_NODES - 1, dtype=int), np.arange(1, NUM_NODES)]),
            np.concatenate([np.arange(1, NUM_NODES), np.zeros(NUM_NODES - 1, dtype=int)]),
        ]), dtype=torch.long,
    )
    return {"base_random": base, "ring": ring, "ring_shifted": shuffled,
            "empty": empty, "star": star}


def make_input() -> torch.Tensor:
    """Non-degenerate per-node features: no two rows are identical."""
    generator = torch.Generator().manual_seed(SEED + 1)
    base = torch.randn(NUM_NODES, IN_CHANNELS, generator=generator)
    offsets = torch.arange(NUM_NODES, dtype=torch.float32).unsqueeze(1) * 0.05
    return base + offsets


def load_recurrent_module(model_name: str) -> tuple[object, str]:
    """Return an object exposing the layer class plus how it was imported."""
    module_name = {"GConvGRU": "gconv_gru", "GConvLSTM": "gconv_lstm"}[model_name]
    try:
        return importlib.import_module("torch_geometric_temporal.nn.recurrent"), "package-import"
    except Exception as error:  # pragma: no cover - environment dependent
        site = Path(torch.__file__).resolve().parents[1] / "torch_geometric_temporal"
        path = site / "nn" / "recurrent" / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(f"_direct_{module_name}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, f"direct-file-load({type(error).__name__}: {error})"


def layer_outputs(model_name: str, k: int, edges: torch.Tensor, x: torch.Tensor,
                  seed: int) -> tuple[dict[str, torch.Tensor], dict]:
    module, import_mode = load_recurrent_module(model_name)
    layer_cls = getattr(module, model_name)
    torch.manual_seed(seed)
    layer = layer_cls(IN_CHANNELS, HIDDEN_DIM, k)
    layer.eval()
    weight = torch.ones(edges.shape[1], dtype=torch.float32)
    with torch.no_grad():
        if model_name == "GConvGRU":
            outputs = {"h": layer(x, edges, weight, None).detach()}
        else:
            hidden, cell = layer(x, edges, weight, None, None)
            outputs = {"h": hidden.detach(), "c": cell.detach()}
    meta = {
        "import_mode": import_mode,
        "configured_K": int(getattr(layer, "K", k)),
        # PyG 2.8 ChebConv keeps no ``K`` attribute; the number of Chebyshev
        # linear terms is the empirical depth of each convolution.
        "cheb_lins_counts": sorted({
            len(module.lins) for module in layer.modules()
            if module.__class__.__name__ == "ChebConv"
        }),
        "output_shapes": {name: list(tensor.shape) for name, tensor in outputs.items()},
    }
    return outputs, meta


def tensor_diff(current: dict[str, torch.Tensor],
                baseline: dict[str, torch.Tensor]) -> dict:
    per_key = {
        key: {
            "max_abs_diff": float((current[key] - baseline[key]).abs().max()),
            "mean_abs_diff": float((current[key] - baseline[key]).abs().mean()),
        }
        for key in current
    }
    return {
        "layer_max_abs_diff_vs_base": max(value["max_abs_diff"] for value in per_key.values()),
        "layer_mean_abs_diff_vs_base": max(value["mean_abs_diff"] for value in per_key.values()),
        "per_output_key": per_key,
    }


def full_model_outputs(model_name: str, edges: torch.Tensor, x: torch.Tensor,
                       seed: int) -> torch.Tensor:
    import main as graph_main

    torch.manual_seed(seed)
    config = graph_main.ExperimentConfig(
        data_name="r0", mode="count", model_name=model_name, seed=seed,
        window_size=IN_CHANNELS, pred_length=PRED_LENGTH, hidden_dim=HIDDEN_DIM,
        num_epochs=1,
    )
    model = graph_main.build_model(config, num_nodes=NUM_NODES, node_features=IN_CHANNELS)
    model.eval()
    weight = torch.ones(edges.shape[1], dtype=torch.float32)
    with torch.no_grad():
        forecast, _ = model(x, edges, weight, model.initial_state())
    return forecast.detach()


def max_abs(a: torch.Tensor, b: torch.Tensor) -> float:
    return float((a - b).abs().max()) if a.numel() else 0.0


def main() -> None:
    started = time.perf_counter()
    adjacencies = make_adjacencies()
    x = make_input()
    assert len({tuple(row.tolist()) for row in x}) == NUM_NODES, "input rows must differ"
    base_edges = adjacencies["base_random"]
    report: dict = {
        "probe_id": "p01-t002-adjacency-probe-20261011-01",
        "protocol": "P1-count-L6-H3-v3",
        "question": "does each model's output actually depend on the adjacency?",
        "seed": SEED,
        "tolerance": TOLERANCE,
        "config": {"num_nodes": NUM_NODES, "in_channels": IN_CHANNELS,
                   "hidden_dim": HIDDEN_DIM, "pred_length": PRED_LENGTH,
                   "num_edges": int(base_edges.shape[1])},
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
            "torch_geometric": torch_geometric.__version__,
            "device": "cpu",
        },
        "models": {},
    }

    for model_name in ("GConvGRU", "GConvLSTM", "EvolveGCNH"):
        model_entry: dict = {"adjacency_trials": {}, "controls": {}}
        for k in (1, 2):
            if model_name == "EvolveGCNH" and k == 2:
                continue
            baseline: dict[str, torch.Tensor] | None = None
            for adj_name, edges in adjacencies.items():
                key = f"K={k}|{adj_name}"
                try:
                    if model_name == "EvolveGCNH":
                        from models.evolvegcnh import EvolveGCNH

                        torch.manual_seed(SEED)
                        layer = EvolveGCNH(NUM_NODES, IN_CHANNELS)
                        layer.eval()
                        weight = torch.ones(edges.shape[1], dtype=torch.float32)
                        with torch.no_grad():
                            raw, _ = layer(x, edges, weight, None)
                        outputs = {"h": raw.detach()}
                        meta = {"import_mode": "repository models.evolvegcnh",
                                "configured_K": None, "cheb_lins_counts": [],
                                "output_shapes": {"h": list(outputs["h"].shape)}}
                    else:
                        outputs, meta = layer_outputs(model_name, k, edges, x, SEED)
                    if baseline is None:
                        baseline = outputs
                    model_entry["adjacency_trials"][key] = {
                        **meta, **tensor_diff(outputs, baseline),
                    }
                except Exception as error:  # pragma: no cover - environment dependent
                    model_entry["adjacency_trials"][key] = {
                        "error": f"{type(error).__name__}: {error}"
                    }
            if model_name != "EvolveGCNH" and baseline is not None:
                repeat, _ = layer_outputs(model_name, k, base_edges, x, SEED)
                reference, _ = layer_outputs(model_name, k, base_edges, x, SEED)
                model_entry["controls"][f"K={k}|same_adjacency_repeat"] = (
                    tensor_diff(repeat, reference)
                )
        report["models"][model_name] = model_entry

    full_entry: dict = {}
    try:
        forecast_base = full_model_outputs("GConvGRU", base_edges, x, SEED)
        for adj_name, edges in adjacencies.items():
            forecast = full_model_outputs("GConvGRU", edges, x, SEED)
            full_entry[f"GConvGRU|{adj_name}"] = {
                "forecast_shape": list(forecast.shape),
                "forecast_max_abs_diff_vs_base": max_abs(forecast, forecast_base),
            }
        forecast_repeat = full_model_outputs("GConvGRU", base_edges, x, SEED)
        full_entry["GConvGRU|same_adjacency_repeat"] = {
            "forecast_max_abs_diff": max_abs(forecast_repeat, forecast_base)
        }
        for model_name in ("GConvLSTM", "EvolveGCNH"):
            base = full_model_outputs(model_name, base_edges, x, SEED)
            other = full_model_outputs(model_name, adjacencies["ring_shifted"], x, SEED)
            full_entry[f"{model_name}|base_vs_ring_shifted"] = {
                "forecast_shape": list(base.shape),
                "forecast_max_abs_diff": max_abs(other, base),
            }
        full_entry["status"] = "ok"
    except Exception as error:  # pragma: no cover - environment dependent
        full_entry = {"status": "unavailable", "error": f"{type(error).__name__}: {error}"}
    report["full_forecast_head"] = full_entry
    report["elapsed_seconds"] = time.perf_counter() - started

    destination = Path(__file__).resolve().parent / "adjacency-probe.json"
    destination.write_text(json.dumps(report, indent=2, sort_keys=True, default=str),
                           encoding="utf-8")
    print(json.dumps({"wrote": str(destination), "elapsed_seconds": report["elapsed_seconds"]}))
    for model_name, entry in report["models"].items():
        for key, trial in entry["adjacency_trials"].items():
            value = trial.get("layer_max_abs_diff_vs_base")
            print(f"{model_name:11s} {key:24s} "
                  + (f"layer_max_abs_diff={value:.3e}" if value is not None else str(trial)))
        for key, control in entry["controls"].items():
            print(f"{model_name:11s} {key:24s} "
                  f"layer_max_abs_diff={control['layer_max_abs_diff_vs_base']:.3e}")
    print("full forecast head:", json.dumps(report["full_forecast_head"], default=str))


if __name__ == "__main__":
    main()
