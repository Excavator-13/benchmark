"""P02-T002 orchestration only; frozen training is invoked through its public CLI.

Run from the repository root with the dedicated Python environment. Commands:
  python research/phases/P02/t002_batch.py preflight --batch p02-t002-20261019-01
  python research/phases/P02/t002_batch.py cost --batch p02-t002-20261019-01
  python research/phases/P02/t002_batch.py formal --batch p02-t002-20261019-01

Formal execution also needs cost-confirmation.json, written after costs are reviewed.
All subprocesses are sequential. Existing failed/incomplete runs are never retried
under the same ID. A successful existing run is revalidated before being skipped.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"
EXPECTED = {"numpy": "1.26.4", "pandas": "2.2.3", "pyarrow": "17.0.0", "torch": "2.14.1"}


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_identity():
    files = []
    for package in ("graph_value_skeleton", "nograph_baseline"):
        files.extend(p for p in (ROOT / "benchmark" / package).rglob("*.py")
                     if "tests" not in p.parts)
    files += [p for p in (ROOT / "benchmark/__init__.py", ROOT / "research/phases/P01/protocol.md")
              if p.is_file()]
    return {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p) for p in sorted(files)}


def axes():
    for dataset in ("r0", "region", "r2"):
        for seed in range(3):
            for method, shuffle in (("self", None), ("graph", None),
                                    ("shuffled", 0), ("shuffled", 1), ("shuffled", 2)):
                for repeat in ("a", "b"):
                    yield {"dataset": dataset, "seed": seed, "method": method,
                           "shuffle": shuffle, "repeat": repeat}


def suffix(axis):
    method = axis["method"] + (str(axis["shuffle"]) if axis["shuffle"] is not None else "")
    return f'{axis["dataset"]}-{method}-s{axis["seed"]}-{axis["repeat"]}'


def windows_sample(root_pid):
    """Windows process-tree RSS and per-process lifetime PeakWorkingSetSize."""
    import ctypes as c
    from ctypes import wintypes as w
    class Entry(c.Structure):
        _fields_ = [("size", w.DWORD), ("usage", w.DWORD), ("pid", w.DWORD),
                    ("heap", c.c_size_t), ("module", w.DWORD), ("threads", w.DWORD),
                    ("parent", w.DWORD), ("priority", w.LONG), ("flags", w.DWORD),
                    ("exe", w.WCHAR * 260)]
    class Memory(c.Structure):
        _fields_ = [("cb", w.DWORD), ("faults", w.DWORD)] + [
            (n, c.c_size_t) for n in ("peak_wset", "wset", "peak_pool_paged", "pool_paged",
                                     "peak_pool_nonpaged", "pool_nonpaged", "pagefile", "peak_pagefile")]
    k = c.WinDLL("kernel32", use_last_error=True)
    p = c.WinDLL("psapi", use_last_error=True)
    k.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
    k.CreateToolhelp32Snapshot.restype = w.HANDLE
    k.Process32FirstW.argtypes = k.Process32NextW.argtypes = [w.HANDLE, c.POINTER(Entry)]
    k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    k.OpenProcess.restype = w.HANDLE
    k.CloseHandle.argtypes = [w.HANDLE]
    p.GetProcessMemoryInfo.argtypes = [w.HANDLE, c.POINTER(Memory), w.DWORD]
    snapshot = k.CreateToolhelp32Snapshot(2, 0)
    if snapshot == c.c_void_p(-1).value:
        raise OSError(c.get_last_error(), "process snapshot failed")
    entry = Entry(); entry.size = c.sizeof(entry)
    parents = {}
    try:
        valid = k.Process32FirstW(snapshot, c.byref(entry))
        while valid:
            parents[int(entry.pid)] = int(entry.parent)
            valid = k.Process32NextW(snapshot, c.byref(entry))
    finally:
        k.CloseHandle(snapshot)
    descendants = {root_pid}
    while True:
        more = {pid for pid, parent in parents.items() if parent in descendants}
        if more <= descendants:
            break
        descendants |= more
    samples = {}
    for pid in descendants:
        handle = k.OpenProcess(0x0400 | 0x0010, False, pid)
        if not handle:
            continue
        try:
            mem = Memory(); mem.cb = c.sizeof(mem)
            if p.GetProcessMemoryInfo(handle, c.byref(mem), mem.cb):
                samples[str(pid)] = {"rss_bytes": int(mem.wset), "peak_rss_bytes": int(mem.peak_wset)}
        finally:
            k.CloseHandle(handle)
    return samples


def invoke(arguments, name, scratch, saved):
    command = [sys.executable, "-m", "benchmark.graph_value_skeleton", *map(str, arguments)]
    log = scratch / "logs" / (name + ".log")
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    monitoring = {"started_at": now(), "command": command, "cwd": str(ROOT),
                  "sampling_seconds": 0.5, "process_tree_peak_sampled_rss_bytes": 0,
                  "per_pid_peak_rss_bytes": {}, "monitor_errors": []}
    print(f'{now()} START {name}', flush=True)
    with log.open("a", encoding="utf-8") as stream:
        child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                if os.name == "nt":
                    try:
                        sample = windows_sample(child.pid)
                        total = sum(v["rss_bytes"] for v in sample.values())
                        monitoring["process_tree_peak_sampled_rss_bytes"] = max(
                            monitoring["process_tree_peak_sampled_rss_bytes"], total)
                        for pid, value in sample.items():
                            previous = monitoring["per_pid_peak_rss_bytes"].get(pid, 0)
                            monitoring["per_pid_peak_rss_bytes"][pid] = max(previous, value["peak_rss_bytes"])
                    except OSError as exc:
                        message = str(exc)
                        if message not in monitoring["monitor_errors"]:
                            monitoring["monitor_errors"].append(message)
                time.sleep(0.5)
        except BaseException:
            child.terminate()
            child.wait()
            raise
    monitoring.update(exit_code=child.returncode, elapsed_seconds=time.monotonic() - started,
                      finished_at=now(), log=str(log.relative_to(ROOT)))
    write(saved / "monitor" / (name + ".json"), monitoring)
    if child.returncode:
        raise RuntimeError(f"{name}: exit {child.returncode}; see {log}")
    print(f'{now()} DONE {name} ({monitoring["elapsed_seconds"]:.1f}s)', flush=True)
    return monitoring


def preflight(scratch, saved, batch):
    result = {"task": "P02-T002", "batch": batch, "created_at": now(),
              "python": sys.version, "executable": sys.executable, "status": "failed"}
    try:
        assert sys.version_info[:2] == (3, 11), "dedicated Python 3.11 required"
        versions = {name: importlib.metadata.version(name) for name in EXPECTED}
        result["versions"] = versions
        assert all(versions[n].split("+")[0] == v for n, v in EXPECTED.items()), versions
        import torch
        assert torch.version.cuda is None, "CPU-only torch required"
        from benchmark.graph_value_skeleton import data, graph, protocol
        assert protocol.EPOCHS == 200 and protocol.HIDDEN_DIM == 32
        assert tuple(protocol.DEVELOPMENT_MODEL_SEEDS) == (0, 1, 2)
        result["source"] = source_identity()
        result["git_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        result["data"] = {}
        for name in ("r0", "region", "r2"):
            dataset = data.load_dataset(name)
            g = graph.load_graph(name, dataset.key_array)
            result["data"][name] = {"nodes": len(dataset.key_array),
                "demand_sha256": digest(ROOT / f"dataset/demand/{name}.parquet"),
                "graph_sha256": digest(ROOT / f"dataset/graph/{name}.parquet")}
            del g, dataset
        result["disk_free_bytes"] = shutil.disk_usage(ROOT).free
        assert result["disk_free_bytes"] > 4 * 1024**3, "less than 4 GiB disk space"
        result["status"] = "ok"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        write(saved / "preflight.json", result)
    schedule = [{**a, "run_id": f"{batch}-{suffix(a)}"} for a in axes()]
    write(saved / "manifest.json", {"task": "P02-T002", "batch": batch,
        "created_at": now(), "script_sha256": digest(Path(__file__)),
        "frozen_epochs": 200, "formal_count": 90, "schedule": schedule})
    print(json.dumps({"preflight": "ok", "formal_count": len(schedule)}), flush=True)


def verify_frozen(saved):
    before = read(saved / "preflight.json")
    assert before["status"] == "ok"
    assert before["source"] == source_identity(), "source changed since preflight"
    assert before["executable"] == sys.executable, "Python environment changed"
    assert before["versions"] == {n: importlib.metadata.version(n) for n in EXPECTED}
    for name, entry in before["data"].items():
        assert entry["demand_sha256"] == digest(ROOT / f"dataset/demand/{name}.parquet")
        assert entry["graph_sha256"] == digest(ROOT / f"dataset/graph/{name}.parquet")


def train(axis, run_id, purpose, scratch, saved):
    run_dir = (ROOT / "research/runs" if purpose == "formal" else scratch / "cost-runs") / run_id
    if run_dir.exists():
        assert read(run_dir / "status.json")["state"] == "success", f"unfinished/failed run: {run_dir}"
        prior = read(run_dir / "config.json")["spec"]
        expected = {"data_name": axis["dataset"], "method": axis["method"],
                    "model_seed": axis["seed"], "shuffle_seed": axis["shuffle"], "purpose": purpose}
        assert all(prior[k] == v for k, v in expected.items()), "existing run axes differ"
        return run_dir
    command = ["run", "--data-name", axis["dataset"], "--method", axis["method"],
               "--model-seed", str(axis["seed"]), "--purpose", purpose, "--run-id", run_id]
    if purpose == "development":
        command += ["--output-root", str(scratch / "cost-runs")]
    if axis["shuffle"] is not None:
        command += ["--shuffle-seed", str(axis["shuffle"])]
    write(saved / "progress.json", {"status": "running", "run_id": run_id, "updated_at": now()})
    invoke(command, run_id, scratch, saved)
    assert read(run_dir / "status.json")["state"] == "success"
    return run_dir


def check(arguments, name, scratch, saved):
    persistent = saved / "checks" / (name + ".json")
    if persistent.exists():
        assert read(persistent)["status"] == "ok", persistent
        return
    original = scratch / "checks" / (name + ".json")
    assert not original.exists(), f"unreviewed prior check exists: {original}"
    invoke([*arguments, "--report", str(original)], name, scratch, saved)
    assert read(original)["status"] == "ok", original
    persistent.parent.mkdir(parents=True, exist_ok=True)
    with persistent.open("xb") as stream:
        stream.write(original.read_bytes())
    write(saved / "check-copies" / (name + ".json"), {
        "source": str(original.relative_to(ROOT)), "saved": str(persistent.relative_to(ROOT)),
        "sha256": digest(persistent), "copied_at": now()})


def cost(scratch, saved, batch):
    verify_frozen(saved)
    runs = []
    for dataset, method, shuffle in (("r0", "self", None), ("r2", "shuffled", 0)):
        axis = {"dataset": dataset, "method": method, "seed": 0, "shuffle": shuffle, "repeat": "cost"}
        rid = batch + "-cost-" + suffix(axis)
        directory = train(axis, rid, "development", scratch, saved)
        runs.append({"run_id": rid, "run_dir": str(directory.relative_to(ROOT)),
                     "measurements": read(directory / "measurements.json"),
                     "monitor": read(saved / "monitor" / (rid + ".json"))})
    write(saved / "cost.json", {"status": "ok", "task": "P02-T002", "runs": runs,
                               "created_at": now(), "epochs": 200})
    write(saved / "progress.json", {"status": "awaiting_cost_review", "updated_at": now()})


def formal(scratch, saved, batch):
    verify_frozen(saved)
    confirmation = read(saved / "cost-confirmation.json")
    assert confirmation["status"] == "accepted" and confirmation["epochs"] == 200
    assert confirmation["cost_sha256"] == digest(saved / "cost.json")
    schedule = read(saved / "manifest.json")["schedule"]
    assert len(schedule) == 90
    completed = []
    for axis in schedule:
        verify_frozen(saved)
        rid = axis["run_id"]
        directory = train(axis, rid, "formal", scratch, saved)
        check(["recompute", "--run-dir", str(directory)], rid + "-recompute", scratch, saved)
        if axis["repeat"] == "b":
            other = directory.with_name(rid[:-1] + "a")
            check(["compare", "--run-a", str(other), "--run-b", str(directory)],
                  rid[:-1] + "repeat", scratch, saved)
        completed.append(rid)
        write(saved / "progress.json", {"status": "running", "completed": completed,
                                        "total": 90, "updated_at": now()})
    for dataset in ("r0", "region", "r2"):
        for seed in range(3):
            for repeat in ("a", "b"):
                dirs = [ROOT / "research/runs" / f"{batch}-{dataset}-shuffled{s}-s{seed}-{repeat}"
                        for s in range(3)]
                check(["summarize-shuffled", "--run-dirs", *map(str, dirs)],
                      f"{batch}-{dataset}-s{seed}-{repeat}-shuffled-summary", scratch, saved)
    write(saved / "progress.json", {"status": "complete", "completed": completed,
        "recomputes": 90, "repeat_pairs": 45, "shuffled_summaries": 18, "updated_at": now()})


def continue_after_cost(scratch, saved, batch):
    """Wait for the current cost controller, review fixed-budget cost, then run."""
    lock = saved / "scheduler.lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    scheduler = {"pid": os.getpid(), "status": "awaiting_cost", "started_at": now(),
                 "task": "P02-T002", "batch": batch}
    write(saved / "scheduler.json", scheduler)
    try:
        while not (saved / "cost.json").exists():
            status = read(saved / "controller-status.json")
            if status["status"] == "failed":
                raise RuntimeError(f"cost controller failed: {status}")
            controller = read(saved / "controller.json")
            if (os.name == "nt" and not windows_sample(controller["pid"])
                    and not (saved / "cost.json").exists()):
                raise RuntimeError("cost controller no longer running; inspect partial run")
            scheduler["updated_at"] = now()
            write(saved / "scheduler.json", scheduler)
            time.sleep(15)
        verify_frozen(saved)
        assert read(saved / "environment-diagnostics.json")["status"] == "ok"
        costs = read(saved / "cost.json")
        assert costs["status"] == "ok" and costs["epochs"] == 200
        samples = costs["runs"]
        assert len(samples) == 2
        totals, sizes, peaks = {}, {}, []
        for sample in samples:
            directory = ROOT / sample["run_dir"]
            assert read(directory / "status.json")["state"] == "success"
            check(["recompute", "--run-dir", str(directory)],
                  sample["run_id"] + "-recompute", scratch, saved)
            dataset = sample["measurements"]["dataset"]
            totals[dataset] = sample["monitor"]["elapsed_seconds"]
            sizes[dataset] = sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
            peaks.append(sample["monitor"]["process_tree_peak_sampled_rss_bytes"])
        # Region estimate interpolates the two measured node counts. Methods and
        # checkpoint choice are unchanged; timing is only a scheduling estimate.
        ratio = (16345 - 2335) / (121420 - 2335)
        totals["region"] = totals["r0"] + ratio * (totals["r2"] - totals["r0"])
        sizes["region"] = sizes["r0"] + ratio * (sizes["r2"] - sizes["r0"])
        disk_estimate = int(30 * sum(sizes.values()) * 1.5)
        free = shutil.disk_usage(ROOT).free
        assert free > disk_estimate + 1024**3, "insufficient disk space for formal matrix"
        assert max(peaks) < 4 * 1024**3, "cost process tree exceeded 4 GiB; review memory before formal runs"
        confirmation = {"status": "accepted", "task": "P02-T002", "epochs": 200,
            "created_at": now(), "cost_sha256": digest(saved / "cost.json"),
            "basis": "User authorized fixed-budget T002; successful real-data costs and recomputes; retain frozen settings without tuning on scores.",
            "sequential_estimated_seconds": 30 * sum(totals.values()),
            "timing_estimate_basis": "30 runs per dataset; r0/self and r2/shuffled measured; region linearly interpolated by nodes; methods may differ; excludes checks",
            "estimated_expanded_bytes_with_50pct_margin": disk_estimate,
            "disk_free_bytes": free, "cost_process_tree_peak_sampled_rss_bytes": max(peaks),
            "parallel_training_processes": 1, "scientific_configuration_changed": False}
        write(saved / "cost-confirmation.json", confirmation)
        write(saved / "controller.json", {"pid": os.getpid(), "mode": "formal",
              "started_at": now(), "command": [sys.executable, *sys.argv], "task": "P02-T002"})
        write(saved / "controller-status.json", {"status": "running", "mode": "formal", "updated_at": now()})
        scheduler.update(status="formal_running", updated_at=now())
        write(saved / "scheduler.json", scheduler)
        formal(scratch, saved, batch)
        # Completion evidence is separate from a later research acceptance and
        # never writes mutable task/state documents from an unattended process.
        reports = sorted((saved / "checks").glob("*.json"))
        assert len(reports) == 155  # 153 formal checks and two cost recomputes
        assert all(read(p)["status"] == "ok" for p in reports)
        write(saved / "completion.json", {"status": "ready_for_research_acceptance",
              "task": "P02-T002", "formal_runs": 90, "formal_checks": 153,
              "cost_checks": 2, "completed_at": now(),
              "note": "No T003 threshold verdict; phase plan remains subject to research-side acceptance."})
        scheduler.update(status="complete", updated_at=now())
        write(saved / "scheduler.json", scheduler)
        write(saved / "controller-status.json", {"status": "success", "mode": "formal", "updated_at": now()})
    except BaseException as exc:
        scheduler.update(status="failed", error=f"{type(exc).__name__}: {exc}", updated_at=now())
        write(saved / "scheduler.json", scheduler)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "cost", "formal", "continue"))
    parser.add_argument("--batch", required=True)
    args = parser.parse_args()
    assert all(c.isalnum() or c in "-_" for c in args.batch), "invalid batch ID"
    scratch = ROOT / "scratch/graph-value-skeleton" / args.batch
    saved = ROOT / "research/reports" / args.batch
    scratch.mkdir(parents=True, exist_ok=True)
    saved.mkdir(parents=True, exist_ok=True)
    controller_sha = digest(Path(__file__))
    snapshot = saved / ("controller-script-" + controller_sha[:12] + ".py")
    if not snapshot.exists():
        snapshot.write_bytes(Path(__file__).read_bytes())
    if args.mode == "continue":
        continue_after_cost(scratch, saved, args.batch)
        return
    write(saved / "controller.json", {"pid": os.getpid(), "mode": args.mode,
        "started_at": now(), "command": [sys.executable, *sys.argv], "task": "P02-T002"})
    write(saved / "controller-status.json", {"status": "running", "mode": args.mode,
          "updated_at": now()})
    try:
        {"preflight": preflight, "cost": cost, "formal": formal}[args.mode](scratch, saved, args.batch)
    except BaseException as exc:
        write(saved / "controller-status.json", {"status": "failed", "mode": args.mode,
              "error": f"{type(exc).__name__}: {exc}", "updated_at": now()})
        raise
    write(saved / "controller-status.json", {"status": "success", "mode": args.mode, "updated_at": now()})


if __name__ == "__main__":
    main()
