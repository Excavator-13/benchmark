"""Synthetic fixtures for the P02 recurrent-entry CPU test suite.

No real demand or graph file is read: every test writes small temporary Parquet
tables, in-memory arrays or synthetic saved-evidence directories.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from benchmark.nograph_baseline import protocol as p01
from benchmark.multivariate_time_series.temporal import data as temporal_data
from benchmark.multivariate_time_series.temporal import protocol, runner

MONTHS = list(p01.MONTHS)


def r0_keys(skills: int) -> List[Tuple[int, int]]:
    return [(0, skill) for skill in range(skills)]


def region_keys(regions: int, skills: int) -> List[Tuple[int, int]]:
    return [(region, skill) for region in range(regions) for skill in range(skills)]


def r2_keys(contexts: int, skills: int) -> List[Tuple[int, int]]:
    return [(context, skill) for context in range(contexts) for skill in range(skills)]


def synthetic_signal(
    node_count: int,
    seed: int = 0,
    *,
    zero_rows: Sequence[int] = (),
    constant_rows: Sequence[int] = (),
    constant_value: float = 5.0,
    max_value: int = 40,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    signal = rng.integers(0, max_value, size=(node_count, len(MONTHS))).astype(np.float64)
    for row in zero_rows:
        signal[row, :] = 0.0
    for row in constant_rows:
        signal[row, :] = float(constant_value)
    return signal


def write_demand(
    path: Path,
    data_name: str,
    keys: Sequence[Sequence[int]],
    signal: np.ndarray,
    *,
    shuffle_seed: Optional[int] = None,
    drop_month: Optional[str] = None,
) -> Path:
    import pandas as pd

    key_columns = list(p01.node_key_columns(data_name))
    frame = pd.DataFrame(np.asarray(keys, dtype=np.int64), columns=key_columns)
    for index, month in enumerate(MONTHS):
        if month == drop_month:
            continue
        frame[month] = np.asarray(signal, dtype=np.float64)[:, index]
    if shuffle_seed is not None:
        frame = frame.sample(frac=1.0, random_state=shuffle_seed).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def write_graph(path: Path, data_name: str, edges: Sequence[Sequence[int]]) -> Path:
    """Write a tiny graph table with context columns plus row_id/col_id."""
    import pandas as pd

    context = list(p01.context_columns(data_name))
    rows = []
    for edge in edges:
        rows.append(list(edge))
    frame = pd.DataFrame(rows, columns=context + ["row_id", "col_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def load_data(data_name: str, path: Path) -> temporal_data.TemporalData:
    return temporal_data.load_temporal_data(data_name, demand_path=path)


def in_memory(data_name: str, node_count: int, seed: int = 0) -> temporal_data.TemporalData:
    keys = r0_keys(node_count) if data_name == "r0" else region_keys(1, node_count)
    return temporal_data.from_arrays(
        data_name, keys, synthetic_signal(node_count, seed)
    )


def config_payload(**overrides: Any) -> Dict[str, Any]:
    payload = protocol.FitConfig(
        model="GRU",
        seed=0,
        learning_rate=1e-3,
        epochs=2,
        hidden_size=4,
        layers=1,
        node_chunk=3,
        grad_clip=1.0,
        threads=1,
    ).to_payload()
    payload.update(overrides)
    return protocol.FitConfig.from_payload(payload).to_payload()


def fit_run(
    root: Path,
    *,
    run_id: str,
    data: temporal_data.TemporalData,
    data_path: Optional[Path] = None,
    output_root: Optional[Path] = None,
    learning_rate: float = 1e-3,
    seed: int = 0,
    epochs: int = 2,
    hidden_size: int = 4,
    node_chunk: int = 3,
    candidate_role: str = "confirmation",
    repeat_role: str = "a",
    purpose: str = "development",
    monitor_interval: float = 1.0,
    after_update: Any = None,
    sampler: Any = None,
    publish: Any = None,
    publish_best: Any = None,
    setup_seconds: float = 0.0,
    clock: Any = None,
    ledger_path: Optional[Path] = None,
    operation: str = "fit",
    parent_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    request = {
        "run_id": run_id,
        "purpose": purpose,
        "operation": operation,
        "data_name": data.dataset,
        "data_path": str(data_path) if data_path is not None else None,
        "output_root": str(output_root or root),
        "config": config_payload(
            model="GRU",
            seed=seed,
            learning_rate=learning_rate,
            epochs=epochs,
            hidden_size=hidden_size,
            node_chunk=node_chunk,
        ),
        "roles": {"candidate_role": candidate_role, "repeat_role": repeat_role},
        "argv": ["fixture"],
        "monitor_interval": monitor_interval,
        "setup_seconds": setup_seconds,
        "ledger_path": str(ledger_path) if ledger_path is not None else None,
    }
    if parent_dir is not None:
        request["parent_dir"] = str(parent_dir)
        parent_config = json.loads(
            (Path(parent_dir) / "config.json").read_text(encoding="utf-8")
        )
        request["config"] = parent_config["config"]
        request["roles"] = parent_config["roles"]
        request["data_name"] = parent_config["dataset"]["name"]
    return runner.run_fit(
        request,
        data=data,
        after_update=after_update,
        sampler=sampler,
        publish=publish,
        clock=clock,
    )


def synthetic_completed_run(
    root: Path,
    run_id: str,
    *,
    seed: int = 0,
    learning_rate: float = 1e-3,
    model: str = "GRU",
    repeat_role: str = "a",
    candidate_role: str = "confirmation",
    state: str = "completed",
    complete_controls: bool = True,
    dataset: str = "r0",
    node_count: int = 4,
    epochs: int = protocol.EPOCHS,
    history_values: Optional[Sequence[float]] = None,
    init_train: float = 10.0,
    init_validation: float = 20.0,
    best_train: float = 8.0,
    best_validation: float = 18.0,
    validation_mae: Optional[float] = None,
    zero_mae: float = 10.0,
    reproduction_status: str = "pass",
    condition_id: Optional[str] = None,
    data_sha: str = "a" * 64,
    keys_sha: str = "b" * 64,
    purpose: str = "development",
) -> Path:
    """Write a synthetic format-v2 run with controlled saved diagnostics evidence."""
    directory = Path(root) / run_id
    directory.mkdir(parents=True, exist_ok=False)
    if history_values is None:
        history_values = [100.0 - index for index in range(epochs)]
    records = []
    for index, value in enumerate(history_values):
        records.append(
            {
                "epoch": index + 1,
                "updates": (index + 1) * protocol.UPDATES_PER_EPOCH,
                "validation_MSE": float(value),
                "validation_MAE": float(np.sqrt(max(value, 0.0))),
                "online_train_loss_mixed_parameters": float(value) / 2.0,
                "clipped_updates": 1,
                "pre_clip_norm_max": 1.5,
                "wall_seconds": 1.0,
            }
        )
    mae = float(validation_mae if validation_mae is not None else np.sqrt(best_validation))
    prediction = np.full((1, node_count, p01.HORIZON), mae, dtype=np.float64)
    gold = np.zeros_like(prediction)
    config = protocol.FitConfig(
        model=model,
        seed=seed,
        learning_rate=learning_rate,
        epochs=epochs,
        hidden_size=4,
        layers=1,
        node_chunk=3,
        grad_clip=1.0,
        threads=1,
    )
    condition = condition_id or protocol.content_sha256(
        {
            "seed": seed,
            "model": model,
            "learning_rate": learning_rate,
            "data_sha": data_sha,
            "keys_sha": keys_sha,
        }
    )
    config_doc = {
        "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
        "scientific_version": protocol.SCIENTIFIC_VERSION,
        "run_id": run_id,
        "operation": "fit",
        "purpose": purpose,
        "dataset": {
            "name": dataset,
            "mode": "count",
            "key_columns": list(p01.node_key_columns(dataset)),
            "nodes": node_count,
        },
        "config": config.to_payload(),
        "protocol_controls": {
            "complete": bool(complete_controls),
            "deviations": [] if complete_controls else ["hidden_size=4 (protocol 32)"],
        },
        "roles": {
            "candidate_role": candidate_role,
            "repeat_role": repeat_role,
        },
        "condition": {"condition_id": condition},
        "split": protocol.split_payload(),
        "parent": None,
    }
    scores = {
        "init": {
            "train": {"MSE": float(init_train), "MAE": float(np.sqrt(init_train))},
            "validation": {
                "MSE": float(init_validation),
                "MAE": float(np.sqrt(init_validation)),
            },
            "updates": 0,
            "epoch": 0,
        },
        "best": {
            "train": {"MSE": float(best_train), "MAE": float(np.sqrt(best_train))},
            "validation": {
                "MSE": float(best_validation),
                "MAE": float(np.sqrt(best_validation)),
            },
            "updates": protocol.UPDATES_PER_EPOCH,
            "epoch": 1,
            "reproduction": {
                "status": reproduction_status,
                "saved": {"MSE": float(best_validation), "MAE": mae},
                "reevaluated": {"MSE": float(best_validation), "MAE": mae},
                "absolute_differences": {"MSE": 0.0, "MAE": 0.0},
                "tolerance": 1e-6,
            },
        },
    }
    provenance = {
        "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
        "scientific_version": protocol.SCIENTIFIC_VERSION,
        "data": {
            "dataset": dataset,
            "mode": "count",
            "source_sha256": data_sha,
            "node_keys_sha256": keys_sha,
            "nodes": node_count,
        },
        "protocol": {
            "sha256": protocol.protocol_content_sha256(),
            "version": protocol.SCIENTIFIC_VERSION,
        },
    }
    baselines = {
        "scores": {
            "Zero": {"MAE": float(zero_mae), "MSE": float(zero_mae) ** 2},
            "LastValue": {"MAE": 5.0, "MSE": 25.0},
            "WindowMean6": {"MAE": 4.0, "MSE": 16.0},
            "TrainMean27": {"MAE": 3.0, "MSE": 9.0},
            "SeasonalNaive12": {"MAE": 6.0, "MSE": 36.0},
        },
        "identity": {"dataset": dataset, "source_sha256": data_sha},
    }
    fit_diagnostics = {
        "stage": "fit",
        "quantiles": {"validation_scaled_inputs": {"p50": 1.0}},
        "saturation": {"validation_fraction": 0.0},
        "prediction_scale": {"validation": {"mean": mae}},
        "input_zeroing": {"MAE_change": 0.1},
    }
    _write_json(directory / "config.json", config_doc)
    _write_json(directory / "provenance.json", provenance)
    _write_json(
        directory / "status.json",
        {"run_id": run_id, "state": state, "updated": "2026-01-01T00:00:00+08:00"},
    )
    _write_json(directory / "history.json", {"epochs": records})
    _write_json(directory / "scores.json", scores)
    _write_json(
        directory / "validation" / "metrics.json",
        {
            "best": {
                "MSE": float(best_validation),
                "MAE": mae,
                "epoch": 1,
                "updates": protocol.UPDATES_PER_EPOCH,
            },
            "reevaluated": {"MSE": float(best_validation), "MAE": mae},
            "reproduction": scores["best"]["reproduction"],
            "history_epochs": len(records),
        },
    )
    np.save(directory / "validation" / "prediction.npy", prediction)
    np.save(directory / "validation" / "gold.npy", gold)
    _write_json(directory / "baselines.json", baselines)
    _write_json(directory / "fit-diagnostics.json", fit_diagnostics)
    return directory


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def tree_digest(root: Path) -> Dict[str, str]:
    """Map every file under a directory to its SHA256 (parent-unchanged checks)."""
    from benchmark.nograph_baseline.data import sha256_file

    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(Path(root).rglob("*"))
        if path.is_file()
    }


def selection_document(
    root: Path,
    *,
    block_id: str = "block",
    model: str = "GRU",
    dataset: str = "r0",
    status: str = "frozen",
    selection_sha: str = "s" * 64,
    winner_run_dir: Optional[Path] = None,
    learning_rate: float = 1e-3,
) -> Dict[str, Any]:
    return {
        "artifact_format_version": protocol.ARTIFACT_FORMAT_VERSION,
        "scientific_version": protocol.SCIENTIFIC_VERSION,
        "kind": "selection",
        "block_id": block_id,
        "purpose": "development",
        "model": model,
        "dataset": dataset,
        "mode": "count",
        "seed": 0,
        "learning_rate_candidates": list(protocol.LR_CANDIDATES),
        "winner": (
            {
                "learning_rate": float(learning_rate),
                "run_id": Path(winner_run_dir).name if winner_run_dir else "winner",
                "run_dir": str(winner_run_dir) if winner_run_dir else "",
                "validation_MSE": 1.0,
            }
            if status == "frozen"
            else None
        ),
        "status": status,
        "frozen": status == "frozen",
        "selection_sha256": selection_sha,
        "test_scores_used": False,
        "b_used_for_selection": False,
    }


def write_json(path: Path, payload: Any) -> Path:
    return _write_json(path, payload)


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
