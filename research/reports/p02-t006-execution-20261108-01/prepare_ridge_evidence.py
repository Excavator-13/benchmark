"""Read existing accepted Ridge selection evidence; do not extract or refit."""
import hashlib
import json
import tarfile
from pathlib import Path

repo = Path(__file__).resolve().parents[3]
package = repo / "research/archives/p01-r0-sharedridge-002.tar.gz"
run_id = "p01-r0-sharedridge-002"
with tarfile.open(package, "r:gz") as archive:
    def read(name):
        member = archive.extractfile(f"{run_id}/{name}")
        if member is None:
            raise ValueError(f"missing {name}")
        raw = member.read()
        return json.loads(raw), hashlib.sha256(raw).hexdigest()
    selection, selection_hash = read("selection.json")
    provenance, provenance_hash = read("provenance.json")
    windows, windows_hash = read("windows.json")

actual_data = hashlib.sha256((repo / "dataset/demand/r0.parquet").read_bytes()).hexdigest()
assert actual_data == provenance["source_sha256"]
assert windows["splits"]["validation"] == [21]
chosen = selection["shared_ridge"]
score = chosen["candidate_table"][chosen["selected_index"]]
assert score["lambda"] == chosen["selected_lambda"]
normalization = selection["normalization"]
payload = {
    "dataset": "r0", "data_sha256": actual_data,
    "node_keys_sha256": provenance["node_keys_sha256"],
    "split": {"validation_starts": [21], "validation_target_months": ["2023-04", "2023-05", "2023-06"]},
    "preprocessing": {"definition": "per-node standardization", "training_months": normalization["train_observation_months"], "ddof": normalization["ddof"], "constant_node_std": normalization["constant_node_std"]},
    "selection": {"lambda": chosen["selected_lambda"], "selected_on": "validation", "metric": chosen["selection_metric"], "tie_break": chosen["tie_break"]},
    "validation": {"MAE": score["validation_MAE"], "MSE": score["validation_MSE"]},
    "source": {"run_id": run_id, "package": str(package.relative_to(repo)), "selection_sha256": selection_hash, "provenance_sha256": provenance_hash, "windows_sha256": windows_hash, "operation": "read saved JSON members only; no extraction, refit or restore audit"},
}
destination = Path(__file__).with_name("ridge-r0-validation.json")
with destination.open("x") as handle:
    json.dump(payload, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
print(json.dumps({"output": str(destination), "validation": payload["validation"], "data_sha256": actual_data}))
