#!/usr/bin/env python3
"""Verify the uploaded T002 model/history artifacts against the recorded checks.

Inputs (all in the repository):

* ``research/runs/p02-t002-*/models/selected.npz`` and
  ``research/runs/p02-t002-*/training-history.json`` — the 90 formal runs'
  uploaded artifacts (imported from branch ``upload-t002-models-history-20261022``,
  commit ``cbcff40``).
* ``research/reports/p02-t002-*/checks/*-recompute.json`` — the formal checks
  that recorded each run's SHA256 for both artifacts and its recomputed metrics.

Checks performed:

1. SHA256 of both artifacts against ``input_sha256_after`` in the check.
2. ``training-history`` consistency: 200 epochs, one Adam step per epoch,
   selected epoch 200, and selected validation MSE equal to the check's
   recomputed validation MSE.
3. Exact output ceiling of each trained model from the head weights:
   ``|prediction| <= max_h(sum_i |W[h,i]| + |b[h]|)`` for the self branch, and
   twice that for graph/shuffled branches (|h|<=1, |h + mean(h_u)|<=2).
4. Consequence for MAE: for any prediction with ``|p| <= B``,
   ``E|y - p| >= E|y| - B``; ``E|y|`` is the ``Zero`` baseline's MAE, so the
   recorded MAE should sit close to this floor if the model is collapsed.

Only the Python standard library is used (numpy is not needed: the ``.npy``
payloads inside the ``.npz`` are decoded directly).  Output: ``verification.json``.

    python3 -B research/analyses/p02-t003-formal-artifacts-20261022-01/verify_artifacts.py
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import struct
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "verification.json"
BASELINES = ("LastValue", "SeasonalNaive12", "TrainMean27", "WindowMean6", "Zero")
BATCHES = {
    "r2": "research/reports/p02-t002-r2-20261020-02",
    "region": "research/reports/p02-t002-region-20261022-01",
    "r0": "research/reports/p02-t002-r0-20261022-01",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_npy(raw: bytes) -> tuple[tuple[int, ...], list[float]]:
    if raw[:6] != b"\x93NUMPY":
        raise ValueError("not a npy payload")
    major = raw[6]
    if major == 1:
        header_len = int.from_bytes(raw[8:10], "little")
        start = 10
    else:
        header_len = int.from_bytes(raw[8:12], "little")
        start = 12
    header = ast.literal_eval(raw[start : start + header_len].decode("latin-1"))
    dtype = header["descr"]
    if dtype not in ("<f4", "<f8"):
        raise ValueError(f"unsupported dtype {dtype}")
    payload = raw[start + header_len :]
    size = 4 if dtype == "<f4" else 8
    values = list(struct.unpack(f"<{len(payload) // size}{'f' if size == 4 else 'd'}", payload))
    return tuple(header["shape"]), values


def load_npz(
    path: Path, wanted: tuple[str, ...] = ("head.weight", "head.bias")
) -> dict[str, tuple[tuple[int, ...], list[float]]]:
    arrays: dict[str, tuple[tuple[int, ...], list[float]]] = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith(".npy") or name[:-4] not in wanted:
                continue
            arrays[name[:-4]] = read_npy(archive.read(name))
    missing = set(wanted) - set(arrays)
    if missing:
        raise ValueError(f"{path}: missing arrays {sorted(missing)}")
    return arrays


def head_bound(arrays: dict[str, tuple[tuple[int, ...], list[float]]]) -> float:
    shape, weight = arrays["head.weight"]
    (rows, columns) = shape
    (_, bias) = arrays["head.bias"]
    bound = 0.0
    for row in range(rows):
        chunk = weight[row * columns : (row + 1) * columns]
        bound = max(bound, sum(abs(value) for value in chunk) + abs(bias[row]))
    return bound


def dataset_of(check_path: Path) -> str:
    text = str(check_path)
    for name, prefix in BATCHES.items():
        if f"research/reports/{prefix.split('/')[-1]}/" in text:
            return name
    raise SystemExit(f"cannot classify check path {check_path}")


def main() -> int:
    checks: dict[str, dict[str, Any]] = {}
    check_paths: dict[str, Path] = {}
    for dataset, batch in BATCHES.items():
        for path in sorted((ROOT / batch / "checks").glob("*-recompute.json")):
            run_id = path.name[: -len("-recompute.json")]
            if run_id in checks:
                raise SystemExit(f"duplicate check for {run_id}")
            checks[run_id] = json.loads(path.read_text(encoding="utf-8"))
            check_paths[run_id] = path
    if len(checks) != 90:
        raise SystemExit(f"expected 90 checks, found {len(checks)}")

    per_run: list[dict[str, Any]] = []
    mismatched_hashes: list[str] = []
    missing_artifacts: list[str] = []
    history_problems: list[str] = []
    for run_id in sorted(checks):
        check = checks[run_id]
        run_dir = ROOT / "research" / "runs" / run_id
        history_path = run_dir / "training-history.json"
        weights_path = run_dir / "models" / "selected.npz"
        for path in (history_path, weights_path):
            if not path.is_file():
                missing_artifacts.append(str(path.relative_to(ROOT)))
        if missing_artifacts:
            continue
        recorded = check["result"]["input_sha256_after"]
        for relative, path in (
            ("training-history.json", history_path),
            ("models/selected.npz", weights_path),
        ):
            recorded_hash = recorded.get(relative)
            if recorded_hash != sha256_file(path):
                mismatched_hashes.append(f"{run_id}: {relative}")

        history = json.loads(history_path.read_text(encoding="utf-8"))
        arrays = load_npz(weights_path)
        bound_rows = arrays["head.weight"]
        row_count, column_count = bound_rows[0]
        head_l1 = [
            sum(abs(value) for value in bound_rows[1][row * column_count : (row + 1) * column_count])
            for row in range(row_count)
        ]
        summary_match = re.search(
            r"Total: ([0-9.]+) s", (run_dir / "summary.md").read_text(encoding="utf-8")
        )
        total_seconds = float(summary_match.group(1)) if summary_match else None
        method = history["method"]
        factor = 2.0 if method in ("graph", "shuffled") else 1.0
        bound_self = head_bound(arrays)
        bound = bound_self * factor

        selection = history.get("selection", {})
        optimizer = selection.get("optimizer", {})
        rows = history["rows"]
        if (
            history.get("epochs") != 200
            or len(rows) != 200
            or history.get("selected_epoch") != 200
            or optimizer.get("steps_per_epoch") != 1
            or optimizer.get("total_steps") != 200
        ):
            history_problems.append(run_id)
        first_val_mae = rows[0]["validation_MAE_original_units_after_update"]
        last_val_mae = rows[-1]["validation_MAE_original_units_after_update"]
        first_train_mae = rows[0]["train_MAE_original_units_before_update"]
        last_train_mae = rows[-1]["train_MAE_original_units_before_update"]

        metrics = check["result"]["recomputed_methods"]
        own = [name for name in metrics["test"] if name not in BASELINES]
        if len(own) != 1:
            raise SystemExit(f"{run_id}: unexpected methods {own}")
        own = own[0]
        test_mae = metrics["test"][own]["MAE"]
        zero_test_mae = metrics["test"]["Zero"]["MAE"]
        validation_mse = metrics["validation"][own]["MSE"]
        selected_mse = history["selected_validation_MSE"]
        if abs(validation_mse - selected_mse) > 1e-6 * max(1.0, abs(selected_mse)):
            history_problems.append(f"{run_id}: selected MSE mismatch")

        dataset = dataset_of(check_paths[run_id])
        floor = zero_test_mae - bound
        per_run.append(
            {
                "run_id": run_id,
                "dataset": dataset,
                "method": method,
                "model_seed": history["model_seed"],
                "factor": factor,
                "bound_self": bound_self,
                "bound_branch": bound,
                "zero_test_mae": zero_test_mae,
                "test_mae": test_mae,
                "floor_mae": floor,
                "gap_to_floor": test_mae - floor,
                "max_gain_over_zero": (zero_test_mae - floor) / zero_test_mae,
                "validation_mae_first": first_val_mae,
                "validation_mae_last": last_val_mae,
                "train_mae_first": first_train_mae,
                "train_mae_last": last_train_mae,
                "validation_mae_relative_change": (last_val_mae - first_val_mae)
                / first_val_mae,
                "selected_epoch": history["selected_epoch"],
                "selected_validation_mse": selected_mse,
                "check_validation_mse": validation_mse,
                "head_l1": head_l1,
                "total_seconds": total_seconds,
            }
        )

    groups: dict[str, dict[str, Any]] = {}
    for dataset in BATCHES:
        for method in ("self", "graph", "shuffled"):
            subset = [
                item
                for item in per_run
                if item["dataset"] == dataset and item["method"] == method
            ]
            if not subset:
                continue
            groups[f"{dataset}/{method}"] = {
                "runs": len(subset),
                "bound_self_min": min(item["bound_self"] for item in subset),
                "bound_self_max": max(item["bound_self"] for item in subset),
                "bound_branch_min": min(item["bound_branch"] for item in subset),
                "bound_branch_max": max(item["bound_branch"] for item in subset),
                "zero_test_mae": subset[0]["zero_test_mae"],
                "floor_mae_min": min(item["floor_mae"] for item in subset),
                "test_mae_min": min(item["test_mae"] for item in subset),
                "test_mae_max": max(item["test_mae"] for item in subset),
                "gap_to_floor_min": min(item["gap_to_floor"] for item in subset),
                "gap_to_floor_max": max(item["gap_to_floor"] for item in subset),
                "max_gain_over_zero": max(
                    item["max_gain_over_zero"] for item in subset
                ),
                "validation_mae_first_min": min(
                    item["validation_mae_first"] for item in subset
                ),
                "validation_mae_last_max": max(
                    item["validation_mae_last"] for item in subset
                ),
                "validation_mae_relative_change_max": max(
                    item["validation_mae_relative_change"] for item in subset
                ),
            }

    head_l1_values = [value for item in per_run for value in item["head_l1"]]
    init_l1 = 2.9  # expectation for nn.Linear(U(-1/sqrt(32), 1/sqrt(32))): 32*0.0884 + 0.0884
    mean_l1 = mean(head_l1_values)
    movement_per_element_step = (mean_l1 - init_l1) / 200 / 32
    step_budget: dict[str, Any] = {
        "init_l1_expected": init_l1,
        "observed_l1_min": min(head_l1_values),
        "observed_l1_mean": mean_l1,
        "observed_l1_max": max(head_l1_values),
        "movement_per_element_step": movement_per_element_step,
        "movement_fraction_of_lr_1e3": movement_per_element_step / 1e-3,
        "note": "initial L1 is the expectation of PyTorch default Linear init; observed growth approximates Adam's step-size ceiling",
        "datasets": {},
    }
    for dataset in BATCHES:
        subset = [item for item in per_run if item["dataset"] == dataset and item["method"] == "self"]
        if not subset:
            continue
        target = subset[0]["zero_test_mae"]
        required_l1 = target
        required_steps_1e3 = (required_l1 - init_l1) / 32 / movement_per_element_step
        seconds_per_step = mean(
            item["total_seconds"] for item in subset if item["total_seconds"]
        ) / 200
        step_budget["datasets"][dataset] = {
            "target_mean": target,
            "required_l1": required_l1,
            "required_steps_lr_1e-3": required_steps_1e3,
            "required_steps_lr_1e-2": required_steps_1e3 / 10,
            "seconds_per_step": seconds_per_step,
            "hours_for_30_runs_lr_1e-3": required_steps_1e3
            * seconds_per_step
            * 30
            / 3600,
        }

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "script": "verify_artifacts.py",
        "script_sha256": sha256_file(Path(__file__)),
        "interpreter": sys.version.split()[0],
        "imported_from": {
            "branch": "upload-t002-models-history-20261022",
            "commit": "cbcff4061e8d4b18c32edb631089846d9188681e",
            "scope_record": "research/reports/t002-upload-20261022-01/upload-scope.json",
        },
        "inputs": {
            "checks": {dataset: BATCHES[dataset] for dataset in BATCHES},
            "runs": len(checks),
            "artifact_files": 2 * len(checks),
        },
        "hash_verification": {
            "matched": 2 * len(checks) - len(mismatched_hashes) - len(missing_artifacts),
            "mismatched": mismatched_hashes,
            "missing": missing_artifacts,
        },
        "history_checks": {
            "selected_epochs": sorted({item["selected_epoch"] for item in per_run}),
            "problems": history_problems,
        },
        "aggregates": groups,
        "step_budget": step_budget,
        "runs": per_run,
        "method": {
            "bound": "max_h(sum_i |head.weight[h,i]| + |head.bias[h]|), doubled for graph/shuffled (|h|<=1, |h+mean(h_u)|<=2)",
            "floor": "Zero test MAE - bound; valid for any prediction |p| <= bound by E|y-p| >= E|y| - E|p|",
            "limit": "bounds are exact given the weights; they do not require running the GRU and do not replace prediction-level checks",
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(
        "hash matches:",
        payload["hash_verification"]["matched"],
        "mismatched:",
        len(mismatched_hashes),
        "missing:",
        len(missing_artifacts),
    )
    print("history problems:", history_problems)
    for name, values in groups.items():
        print(
            f"{name:15s} n={values['runs']:2d} bound {values['bound_branch_min']:.2f}-{values['bound_branch_max']:.2f} "
            f"Zero {values['zero_test_mae']:.2f} floor {values['floor_mae_min']:.2f} "
            f"obs {values['test_mae_min']:.2f}-{values['test_mae_max']:.2f} "
            f"maxgain {100 * values['max_gain_over_zero']:.2f}% "
            f"val {values['validation_mae_first_min']:.1f}->{values['validation_mae_last_max']:.1f}"
        )
    sb = payload["step_budget"]
    print(
        "head L1 init %.2f -> observed %.2f (mean), movement/element/step %.2e (%.0f%% of lr 1e-3)"
        % (
            sb["init_l1_expected"],
            sb["observed_l1_mean"],
            sb["movement_per_element_step"],
            100 * sb["movement_fraction_of_lr_1e3"],
        )
    )
    for dataset, values in sb["datasets"].items():
        print(
            f"{dataset:7s} target {values['target_mean']:.1f} steps(lr1e-3) {values['required_steps_lr_1e-3']:.0f} "
            f"steps(lr1e-2) {values['required_steps_lr_1e-2']:.0f} "
            f"30-run hours {values['hours_for_30_runs_lr_1e-3']:.1f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
