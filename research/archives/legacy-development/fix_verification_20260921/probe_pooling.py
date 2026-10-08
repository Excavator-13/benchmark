"""Inspect CPU/CUDA TopK tie handling for the checkpoint found during verification."""
import json
from pathlib import Path
import sys
import types

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "benchmark" / "graph_method"))
import main
from dataset import DatasetLoader

checkpoint = HERE / "runs" / "count-cpu" / "checkpoint.pt"
signal = DatasetLoader("r0", "count").get_dataset()
test = main.temporal_signal_split(signal)[2]
output = {}


def stable_forward(pool, x, edge_index):
    score = pool.select.act((x * pool.select.weight).sum(dim=-1) / pool.select.weight.norm(p=2, dim=-1))
    keep = torch.argsort(score, descending=True, stable=True)[:6]
    return (x[keep] * score[keep, None],)


predictions = {}
for stable in (False, True):
    for device in ("cpu", "cuda:0"):
        model = main.load_checkpoint(checkpoint, torch.device(device)).model
        pool = model.recurrent.pooling_layer
        x = test[0].x.to(device)
        edge = test[0].edge_index.to(device)
        scores = pool.select.act((x * pool.select.weight).sum(dim=-1) / pool.select.weight.norm(p=2, dim=-1))
        selected = pool(x, edge)[4]
        key = ("stable" if stable else "original") + "/" + device
        output[key] = {"maximum_score": float(scores.max()), "tied_maxima": int((scores == scores.max()).sum()),
                       "selected_nodes": selected.tolist(),
                       "stable_selected_nodes": torch.argsort(scores, descending=True, stable=True)[:6].tolist()}
        if stable:
            pool.forward = types.MethodType(stable_forward, pool)
        predictions[key] = main.run_split(model, test, torch.device(device), collect_predictions=True).predictions
    prefix = "stable" if stable else "original"
    output[prefix + "_max_difference"] = max(float((a - b).abs().max()) for a, b in
                                            zip(predictions[prefix + "/cpu"], predictions[prefix + "/cuda:0"]))
(HERE / "pooling-probe.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
print(json.dumps(output, indent=2))
