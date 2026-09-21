"""Reproduce the two checkpoint failures without any model or training."""
import io
import json
import pickletools
from pathlib import Path

import torch

directory = Path(__file__).resolve().parent
results = {}
buffer = io.BytesIO()
torch.save({"best_val_loss": 0.25}, buffer)
buffer.seek(0)
try:
    torch.load(buffer, weights_only=True)
except Exception as error:
    results["float_metadata_error"] = repr(error)
path = directory / "unicode-probe.pt"
results["parent_exists"] = path.parent.is_dir()
try:
    torch.save(torch.ones(1), path)
except Exception as error:
    results["unicode_path_error"] = repr(error)
with path.open("wb") as handle:
    torch.save(torch.ones(1), handle)
results["file_handle_roundtrip"] = torch.load(path, weights_only=True).tolist()
results["pickle_opcode_71"] = next(op.name for op in pickletools.opcodes if ord(op.code) == 71)
(directory / "minimal-reproductions.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results, indent=2))
