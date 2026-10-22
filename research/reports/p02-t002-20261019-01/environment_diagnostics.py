"""Reproduce the two Windows environment differences without changing the model."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"

import numpy as np
import torch
from benchmark.graph_value_skeleton import model, training

training.configure_determinism(0)
m = model.build_model(0)
x = torch.as_tensor(np.random.default_rng(7).uniform(0, 40, size=(5, 6)), dtype=torch.float32)
a, b = x[:2], x[:2] + 3
first = m.encode(a)
m.encode(b)
second = m.encode(a)
alone = model.predict_windows(m, b.unsqueeze(0))
after = model.predict_windows(m, torch.stack([a, b]))
again = model.predict_windows(m, torch.stack([a, b]))
diff = (alone[0] - after[1]).abs()
scale = torch.maximum(torch.ones_like(diff), torch.maximum(alone[0].abs(), after[1].abs()))
print(json.dumps({
    "torch": torch.__version__, "cuda": torch.version.cuda,
    "same_shape_state_reset_exact": torch.equal(first, second),
    "same_shape_repeat_exact": torch.equal(after, again),
    "cross_batch_max_absolute_difference": float(diff.max()),
    "cross_batch_max_normalized_difference": float((diff / scale).max()),
    "tolerance": 1e-6,
}, indent=2))
