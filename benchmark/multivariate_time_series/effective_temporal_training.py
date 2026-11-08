"""Protocol-isolated recurrent training for P02/T006.

This module deliberately does not import the legacy experiment runner.  It keeps
the P02 effective-training rules (training-only RMS, L6/H3 windows, one update
per complete window, validation-only checkpoint selection) in one auditable
entry point.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import platform
import random
import sys
import tempfile
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import torch
from torch import nn

PROTOCOL_VERSION = "P2-effective-training-L6-H3-v1"
TRAIN_MONTHS = 27
VAL_MONTHS = 3
TEST_MONTHS = 6
SEQ_LEN = 6
PRED_LEN = 3


@dataclass(frozen=True)
class Config:
    model: str = "GRU"
    seed: int = 0
    epochs: int = 100
    hidden_size: int = 32
    layers: int = 1
    learning_rate: float = 1e-3
    node_chunk: int = 2048
    grad_clip: float = 1.0
    threads: int = 1

    def __post_init__(self) -> None:
        validate_config(self)


def validate_config(config: Config) -> None:
    if str(config.model).upper() not in {"GRU", "LSTM"}:
        raise ValueError("model must be GRU or LSTM")
    if int(config.epochs) <= 0:
        raise ValueError("epochs must be positive")
    if int(config.hidden_size) <= 0 or int(config.layers) <= 0:
        raise ValueError("hidden_size and layers must be positive")
    if int(config.node_chunk) <= 0 or int(config.threads) <= 0:
        raise ValueError("node_chunk and threads must be positive")
    if not math.isfinite(float(config.learning_rate)) or float(config.learning_rate) <= 0:
        raise ValueError("learning_rate must be finite and positive")
    if not math.isfinite(float(config.grad_clip)) or float(config.grad_clip) <= 0:
        raise ValueError("grad_clip must be finite and positive")


class RecurrentForecaster(nn.Module):
    def __init__(self, model: str, hidden_size: int, layers: int):
        super().__init__()
        kind = model.upper()
        if kind not in {"GRU", "LSTM"}:
            raise ValueError("model must be GRU or LSTM")
        if int(hidden_size) <= 0 or int(layers) <= 0:
            raise ValueError("hidden_size and layers must be positive")
        self.kind = kind
        self.hidden_size = int(hidden_size)
        self.layers = int(layers)
        self.rnn = (nn.GRU if kind == "GRU" else nn.LSTM)(
            input_size=1, hidden_size=self.hidden_size, num_layers=self.layers,
            batch_first=True, dropout=0.0,
        )
        self.head = nn.Linear(self.hidden_size, PRED_LEN)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output, _ = self.rnn(x)
        return self.head(output[:, -1, :])


def set_determinism(seed: int, threads: int = 1) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(max(1, int(threads)))
    torch.use_deterministic_algorithms(True)


def training_rms(values: np.ndarray) -> float:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != TRAIN_MONTHS:
        raise ValueError(f"training values must have shape (nodes, {TRAIN_MONTHS})")
    scale = math.sqrt(float(np.sum(arr * arr, dtype=np.float64)) / (arr.size))
    return max(1.0, scale)


def make_windows(values: np.ndarray, start: int, count: int = 1) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError("values must be a 2-D array")
    if int(start) < 0 or int(count) <= 0:
        raise ValueError("window start must be non-negative and count must be positive")
    end = int(start) + int(count) + SEQ_LEN + PRED_LEN - 1
    if end > arr.shape[1]:
        raise ValueError("values do not contain the requested L6/H3 window count")
    xs = np.stack([arr[:, s:s + SEQ_LEN] for s in range(int(start), int(start) + int(count))], axis=1)
    ys = np.stack([arr[:, s + SEQ_LEN:s + SEQ_LEN + PRED_LEN] for s in range(int(start), int(start) + int(count))], axis=1)
    return xs, ys


def _metric(pred: np.ndarray, true: np.ndarray) -> dict[str, float]:
    error = np.asarray(pred, dtype=np.float64) - np.asarray(true, dtype=np.float64)
    return {"mse": float(np.mean(error * error)), "mae": float(np.mean(np.abs(error)))}


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _atomic_torch(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    os.close(fd)
    try:
        torch.save(value, tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _identity(config: Config, arr: np.ndarray, source: str, scale: float) -> dict:
    data_digest = hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()
    return {"protocol_version": PROTOCOL_VERSION, "config": asdict(config),
            "source": str(source), "data_digest": data_digest,
            "nodes": int(arr.shape[0]), "months": int(arr.shape[1]),
            "scale": float(scale), "train_start": 0, "train_count": 19,
            "train_months": list(range(TRAIN_MONTHS)),
            "val_start": TRAIN_MONTHS - SEQ_LEN, "val_count": 1,
            "test_start": TRAIN_MONTHS, "test_count": 1}


def _identity_digest(identity: dict) -> str:
    digest_identity = dict(identity)
    digest_identity["config"] = dict(identity["config"])
    digest_identity["config"].pop("epochs", None)
    encoded = json.dumps(digest_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _predict(model: nn.Module, x: np.ndarray, scale: float, chunk: int) -> np.ndarray:
    model.eval()
    result = []
    with torch.no_grad():
        for begin in range(0, len(x), chunk):
            tensor = torch.from_numpy((x[begin:begin + chunk] / scale).astype(np.float32)).unsqueeze(-1)
            result.append(model(tensor).cpu().numpy() * scale)
    return np.concatenate(result, axis=0)


def load_checkpoint(path: Path, model: nn.Module, optimizer: torch.optim.Optimizer | None = None) -> dict:
    """Restore a protocol checkpoint after validating its identity."""
    payload = torch.load(path, map_location="cpu", weights_only=False)
    manifest = payload.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("checkpoint is missing the P02 protocol identity")
    model.load_state_dict(payload["model"])
    if optimizer is not None:
        if "optimizer" not in payload:
            raise ValueError("checkpoint has no optimizer state for resume")
        optimizer.load_state_dict(payload["optimizer"])
    return manifest

def train(values: np.ndarray, config: Config, run_dir: Path, source: str = "array",
          resume_from: Path | None = None) -> dict:
    validate_config(config)
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] < TRAIN_MONTHS + VAL_MONTHS + TEST_MONTHS:
        raise ValueError("expected (nodes, at least 36 months) demand array")
    if arr.shape[0] <= 0 or not np.isfinite(arr).all():
        raise ValueError("values must contain finite observations")
    set_determinism(config.seed, config.threads)
    scale = training_rms(arr[:, :TRAIN_MONTHS])
    identity = _identity(config, arr, source, scale)
    identity_digest = _identity_digest(identity)
    model = RecurrentForecaster(config.model, config.hidden_size, config.layers)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate, betas=(0.9, 0.999), eps=1e-8)
    train_x, train_y = make_windows(arr, 0, TRAIN_MONTHS - SEQ_LEN - PRED_LEN + 1)
    train_x, train_y = train_x[:, :19], train_y[:, :19]
    val_x, val_y = make_windows(arr, TRAIN_MONTHS - SEQ_LEN, 1)
    start_epoch = 0
    progress = []
    best = None
    resumed_from = None
    if resume_from is not None:
        resume_path = Path(resume_from)
        payload = torch.load(resume_path, map_location="cpu", weights_only=False)
        manifest = payload.get("manifest")
        if not isinstance(manifest, dict) or manifest.get("identity_digest") != identity_digest:
            raise ValueError("checkpoint identity does not match protocol, configuration, or data")
        model.load_state_dict(payload["model"])
        optimizer.load_state_dict(payload["optimizer"])
        start_epoch = int(manifest.get("current_epoch", 0))
        if start_epoch < 0 or start_epoch > config.epochs:
            raise ValueError("checkpoint epoch is outside the configured range")
        progress_path = resume_path.parent / "progress.json"
        if progress_path.exists():
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
        best_payload = payload.get("best")
        if best_payload is not None:
            best = {"epoch": best_payload["epoch"], "val": best_payload["val"],
                    "clip_norm": best_payload.get("clip_norm", 0.0),
                    "model": best_payload["model"], "optimizer": best_payload["optimizer"]}
        resumed_from = str(resume_path.resolve())
    criterion = nn.MSELoss(reduction="sum")
    for epoch in range(start_epoch + 1, config.epochs + 1):
        model.train()
        train_losses = []
        pre_clip = 0.0
        for window in range(train_x.shape[1]):
            optimizer.zero_grad(set_to_none=True)
            for begin in range(0, arr.shape[0], config.node_chunk):
                end = min(arr.shape[0], begin + config.node_chunk)
                x = torch.from_numpy((train_x[begin:end, window] / scale).astype(np.float32)).unsqueeze(-1)
                y = torch.from_numpy((train_y[begin:end, window] / scale).astype(np.float32))
                loss = criterion(model(x), y) / (arr.shape[0] * PRED_LEN)
                loss.backward()
                train_losses.append(float(loss.detach()))
            pre_clip = float(torch.nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip))
            optimizer.step()
        val_pred = _predict(model, val_x[:, 0], scale, config.node_chunk)
        val_metrics = _metric(val_pred, val_y[:, 0])
        record = {"epoch": epoch, "train_loss_sum": float(sum(train_losses)), "val": val_metrics}
        progress.append(record)
        if best is None or val_metrics["mse"] < best["val"]["mse"]:
            best = {"epoch": epoch, "val": val_metrics, "clip_norm": pre_clip,
                    "model": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
                    "optimizer": copy.deepcopy(optimizer.state_dict())}
        manifest = {**identity, "identity_digest": identity_digest, "current_epoch": epoch,
                    "selected_epoch": best["epoch"], "metrics": {"val": best["val"]},
                    "resumed_from": resumed_from, "complete": epoch >= config.epochs,
                    "python": sys.version, "platform": platform.platform()}
        run_dir.mkdir(parents=True, exist_ok=True)
        _atomic_torch(run_dir / "checkpoint.pt", {"model": model.state_dict(),
            "optimizer": optimizer.state_dict(), "best": best, "manifest": manifest})
        _atomic_json(run_dir / "summary.json", manifest)
        _atomic_json(run_dir / "progress.json", progress)
    if best is None:
        raise ValueError("checkpoint has no completed epoch")
    # Keep the latest training state aligned with current_epoch for resume.  The
    # selected validation state is stored separately in ``best`` below.
    latest_model = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    latest_optimizer = copy.deepcopy(optimizer.state_dict())
    model.load_state_dict(best["model"])
    # Materialize test inputs and labels only after validation selection/restoration.
    test_x, test_y = make_windows(arr, TRAIN_MONTHS, 1)
    test_pred = _predict(model, test_x[:, 0], scale, config.node_chunk)
    metrics = {"val": best["val"], "test": _metric(test_pred, test_y[:, 0])}
    manifest = {**identity, "identity_digest": identity_digest, "current_epoch": config.epochs,
                "selected_epoch": best["epoch"], "metrics": metrics,
                "resumed_from": resumed_from, "complete": True,
                "python": sys.version, "platform": platform.platform()}
    run_dir.mkdir(parents=True, exist_ok=True)
    _atomic_torch(run_dir / "checkpoint.pt", {"model": latest_model, "optimizer": latest_optimizer,
        "best": best, "manifest": manifest})
    _atomic_json(run_dir / "summary.json", manifest)
    _atomic_json(run_dir / "progress.json", progress)
    return manifest

def load_demand(path: Path) -> np.ndarray:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("reading parquet requires pandas and pyarrow; install requirements first") from exc
    frame = pd.read_parquet(path)
    cols = [c for c in frame.columns if "id" not in str(c).lower()]
    frame = frame[cols].T.reset_index()
    frame.columns = ["date"] + list(frame.columns[1:])
    data = frame.iloc[:, 1:].to_numpy(dtype=np.float64).T
    return data


def compare(values: np.ndarray, models: Sequence[str], seeds: Sequence[int], run_dir: Path, config: Config) -> dict:
    records = []
    for model in models:
        for seed in seeds:
            cfg = Config(**{**asdict(config), "model": model, "seed": int(seed)})
            records.append(train(values, cfg, run_dir / f"{model.lower()}-seed{seed}"))
    grouped = {}
    for record in records:
        key = record["config"]["model"]
        grouped.setdefault(key, []).append(record["metrics"]["test"])
    summary = {"protocol_version": PROTOCOL_VERSION, "runs": records, "comparison": {}}
    for model, metrics in grouped.items():
        summary["comparison"][model] = {k: {"mean": float(np.mean([m[k] for m in metrics])),
                                             "sample_sd": float(np.std([m[k] for m in metrics], ddof=1)) if len(metrics) > 1 else 0.0}
                                         for k in ("mse", "mae")}
    _atomic_json(run_dir / "comparison.json", summary)
    return summary


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="P02 effective GRU/LSTM training")
    p.add_argument("--data", type=Path, help="Job-SDF parquet file")
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--model", choices=["GRU", "LSTM", "compare"], default="compare")
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--hidden-size", type=int, default=32)
    p.add_argument("--layers", type=int, default=1)
    p.add_argument("--learning-rate", type=float, default=1e-3)
    p.add_argument("--node-chunk", type=int, default=2048)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--synthetic-nodes", type=int, default=0, help="generate deterministic fixture data")
    p.add_argument("--resume", type=Path, help="resume from an identity-matched checkpoint")
    return p


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.synthetic_nodes:
        rng = np.random.default_rng(1234)
        values = np.abs(rng.normal(10, 2, size=(args.synthetic_nodes, 36)))
        source = "synthetic-fixture"
    elif args.data:
        values = load_demand(args.data)
        source = str(args.data.resolve())
    else:
        raise SystemExit("--data or --synthetic-nodes is required")
    cfg = Config(model="GRU", epochs=args.epochs, hidden_size=args.hidden_size, layers=args.layers,
                 learning_rate=args.learning_rate, node_chunk=args.node_chunk, threads=args.threads)
    if args.model == "compare":
        compare(values, ("GRU", "LSTM"), args.seeds, args.run_dir, cfg)
    else:
        train(values, Config(**{**asdict(cfg), "model": args.model, "seed": args.seeds[0]}), args.run_dir, source, args.resume)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
