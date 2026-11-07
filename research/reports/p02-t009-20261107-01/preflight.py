"""Key/source preflight using the accepted T009 loaders; no graph or training."""
import json
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"

from benchmark.occupation_skill_graph import artifacts, data, mapping

root = Path.cwd()
out = Path(__file__).with_name("preflight.json")
started = time.perf_counter()
source = data.load_training()
targets = {}
for name in ("r0", "region", "r2"):
    target = data.load_target_keys(name)
    targets[name] = {
        "identity": target.identity_payload(),
        "population": mapping.validate_target_population(target, source.skills),
    }
receipt = {
    "status": "ok",
    "utc": datetime.now(timezone.utc).isoformat(),
    "source": source.identity_payload(),
    "targets": targets,
    "resource": {
        "platform": platform.platform(), "cpu_count": os.cpu_count(),
        "disk_free_bytes": shutil.disk_usage(root).free,
        "vm_stat": subprocess.run(["vm_stat"], capture_output=True, text=True).stdout,
        "rss_probe": artifacts.process_rss_bytes(os.getpid()),
    },
    "seconds": time.perf_counter() - started,
    "scope": "Source training columns only; target identity columns only; no training",
}
with out.open("x") as handle:
    json.dump(receipt, handle, indent=2)
print(json.dumps({"status": receipt["status"], "seconds": receipt["seconds"],
                  "rss_probe": receipt["resource"]["rss_probe"],
                  "targets": {n: {k: t["population"][k] for k in
                                  ("contexts", "skills", "status")} for n,t in targets.items()}}))
