"""Audit delivered T002 records only; no training or access to the Windows run root.

Run from the repository root with Python 3; JSON is printed to stdout.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BATCHES = {
    "r2": "p02-t002-r2-20261020-02",
    "region": "p02-t002-region-20261022-01",
    "r0": "p02-t002-r0-20261022-01",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def byte_relation(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() == expected:
        return "exact"
    # Classify a concrete byte transformation; never treat this as byte equality.
    windows = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    assert hashlib.sha256(windows).hexdigest() == expected, str(path)
    return "LF_checkout_matches_recorded_CRLF"


def audit(dataset, batch):
    directory = ROOT / "research/reports" / batch
    manifest = read(directory / "manifest.json")
    expected = {
        (method, seed, repeat, shuffle)
        for method, shuffle in [("self", None), ("graph", None), ("shuffled", 0),
                                ("shuffled", 1), ("shuffled", 2)]
        for seed in range(3) for repeat in ("a", "b")
    }
    schedule = manifest["schedule"]
    assert len(schedule) == manifest["formal_count"] == 30
    assert {(x["method"], x["model_seed"], x["repeat"], x["shuffle_seed"])
            for x in schedule} == expected
    assert all(x["dataset"] == dataset for x in schedule)
    assert manifest["frozen_epochs"] == 200
    assert read(directory / "preflight.json")["status"] == "ok"
    effective = read(directory / "effective-runs.json")
    run_ids = {x["run_id"] for x in schedule}
    assert set(effective) == set(effective.values()) == run_ids
    slots = read(directory / "recovery-plan.json")["slots"]
    assert len(slots) == 30 and {x["run_id"] for x in slots} == run_ids
    assert all(x["action"] == "fresh" for x in slots)
    ancestry = set()
    for axis in schedule:
        run = ROOT / "research/runs" / axis["run_id"]
        assert all((run / name).is_file()
                   for name in ("summary.md", "provenance.json", "command.json"))
        provenance = read(run / "provenance.json")
        assert provenance["run_id"] == axis["run_id"]
        assert provenance["dataset"] == dataset
        assert provenance["model_seed"] == axis["model_seed"]
        assert provenance["method"] == axis["method"]
        assert provenance["shuffle_seed"] == axis["shuffle_seed"]
        recovery = provenance["recovery"]
        assert recovery["completed_epoch_at_start"] == 0
        assert recovery["parent_checkpoint"] is None
        assert ancestry.isdisjoint(recovery["ancestry"])
        ancestry.update(recovery["ancestry"])
    kinds, receipts, sources = Counter(), Counter(), Counter()
    covered, pairs, summaries, fingerprints = set(), set(), set(), set()
    checks = sorted((directory / "checks").glob("*.json"))
    assert len(checks) == 51
    for file in checks:
        report = read(file)
        result, inputs, kind = report["result"], report["inputs"], report["kind"]
        assert report["status"] == result["status"] == "ok"
        assert not report["errors"] and not result["failed_checks"]
        assert read(directory / "monitor" / file.name)["exit_code"] == 0
        receipt = read(directory / "check-copies" / file.name)
        assert ROOT / receipt["saved"] == file
        receipts[byte_relation(file, receipt["sha256"])] += 1
        fingerprints.update(report["checker"]["source"]["files"].items())
        kinds[kind] += 1
        if kind == "recompute":
            assert inputs["input_status"] == "success"
            assert report["tolerances"]["numeric"] == 1e-12
            covered.add(inputs["input_run_id"])
        elif kind == "compare":
            assert report["tolerances"]["elementwise_prediction_normalized"] == 1e-6
            identity = result["condition_identity"]
            assert not identity["differences"]
            for side in ("run_a", "run_b"):
                config = identity[side]["computational"]
                assert config["epochs"] == 200 and not config["early_stopping"]
                assert config["hidden_dim"] == 32 and config["parameter_counts"]["total"] == 3459
                assert config["tie_break"] == "earliest epoch"
            pairs.add((inputs["run_a_id"], inputs["run_b_id"]))
        elif kind == "summarize-shuffled":
            assert not result["condition_differences"] and not result["weakest_graph_selected"]
            assert set(result["members"]) == {"0", "1", "2"}
            members = {x["run_id"] for x in result["members"].values()}
            assert members <= run_ids and len(members) == 3
            summaries.add(frozenset(members))
    assert covered == run_ids
    expected_pairs = {(f"{batch}-{dataset}-{method}-s{seed}-a",
                       f"{batch}-{dataset}-{method}-s{seed}-b")
                      for method in ("self", "graph", "shuffled0", "shuffled1", "shuffled2")
                      for seed in range(3)}
    assert pairs == expected_pairs
    assert summaries == {frozenset(f"{batch}-{dataset}-shuffled{x}-s{seed}-{repeat}"
                                  for x in range(3))
                         for seed in range(3) for repeat in ("a", "b")}
    assert kinds == {"recompute": 30, "compare": 15, "summarize-shuffled": 6}
    for name, digest in sorted(fingerprints):
        sources[byte_relation(ROOT / name, digest)] += 1
    progress = read(directory / "progress.json")
    assert progress["status"] == f"complete_{dataset}" and progress["active"] is None
    assert set(progress["completed"]) == run_ids
    completion = read(directory / "completion.json")
    assert completion["formal_fits"] == 30 and completion["successful_checks"] == 51
    assert all(read(directory / "monitor" / f"{rid}.json")["exit_code"] == 0 for rid in run_ids)
    return {"batch": batch, "status": "accepted_delivery_evidence", "formal_fits": 30,
            "checks": dict(kinds), "completed_at": completion["completed_at"],
            "fresh_independent_runs": 30, "copy_receipt_bytes": dict(receipts),
            "checker_source_bytes_vs_checkout": dict(sources)}


if __name__ == "__main__":
    print(json.dumps({"scope": "delivered records; no independent metric recomputation or retraining",
                      "datasets": {d: audit(d, b) for d, b in BATCHES.items()}},
                     ensure_ascii=False, indent=2))
