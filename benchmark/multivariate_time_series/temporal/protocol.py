"""Fixed ``P2-effective-training-L6-H3-v1`` constants and stage contracts.

Everything scientific in this package derives from ``research/phases/P02/
protocol.md`` (sections 2-6) and its inherited P01 definitions.  The values are
copied here and re-validated before a run may publish evidence; the protocol
file itself is hashed into the provenance record rather than re-interpreted.

Nothing in this module imports torch, pandas or psutil: the saved-only checks
must run with only NumPy available.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from benchmark.nograph_baseline import protocol as p01

SCIENTIFIC_VERSION = "P2-effective-training-L6-H3-v1"
ARTIFACT_FORMAT_VERSION = 2
REPORT_VERSION = 1

#: The protocol document this implementation claims to follow.
P02_PROTOCOL_PATH = p01.REPO_ROOT / "research" / "phases" / "P02" / "protocol.md"

MODELS: Tuple[str, ...] = ("GRU", "LSTM")
DATASETS: Tuple[str, ...] = ("r0", "region", "r2")
MODES: Tuple[str, ...] = ("count",)
PURPOSES: Tuple[str, ...] = ("formal", "development")

#: Operation names; also the argparse subcommands of the public entry point.
OPERATIONS: Tuple[str, ...] = (
    "preflight",
    "fit",
    "select",
    "diagnose",
    "report",
    "recompute",
    "compare",
    "resume",
)

# -- section 3: model and optimization unit ---------------------------------
HIDDEN_SIZE = 32
LAYERS = 1
EPOCHS = 100
TRAIN_WINDOW_COUNT = 19
UPDATES_PER_EPOCH = TRAIN_WINDOW_COUNT
TOTAL_UPDATES = EPOCHS * UPDATES_PER_EPOCH
ADAM_BETAS: Tuple[float, float] = (0.9, 0.999)
ADAM_EPS = 1e-8
WEIGHT_DECAY = 0.0
AMSGRAD = False
GRAD_CLIP_NORM = 1.0
DIAGNOSTIC_EPOCHS: Tuple[int, ...] = (10, 50, 100)
PARAMETER_COUNTS: Mapping[str, int] = {"GRU": 3459, "LSTM": 4579}
LR_CANDIDATES: Tuple[float, ...] = (1e-3, 3e-3)
SEEDS: Tuple[int, ...] = (0, 1, 2)
REPEAT_ROLES: Tuple[str, ...] = ("a", "b")
CANDIDATE_ROLES: Tuple[str, ...] = ("screening", "confirmation")

# -- section 5: learning-validity gates -------------------------------------
LEARNING_TRAIN_REDUCTION = 0.10
LEARNING_VAL_REDUCTION = 0.05
ZERO_MAE_IMPROVEMENT = 0.05
BUDGET_TAIL_EPOCH = 80
BUDGET_TAIL_RELATIVE = 0.01
MIN_PASSING_SEEDS = 2
REQUIRED_SEED_COUNT = 3
REPETITION_TOLERANCE = 1e-6
BUDGET_TAIL_FLOOR = 1e-12

# -- section 6: resource and cost limits ------------------------------------
GIB = 1024**3
MEMORY_STOP_BYTES = 8 * GIB
AVAILABLE_MEMORY_MIN_BYTES = 6 * GIB
DISK_FREE_MIN_BYTES = 5 * GIB
MONITOR_INTERVAL_SECONDS = 5.0
COST_SAMPLE_EPOCHS = 10
COST_SAMPLE_SECONDS = 15 * 60
FIT_SECONDS = 60 * 60
BATCH_SECONDS = 12 * 60 * 60
STEADY_STATE_EPOCHS: Tuple[int, ...] = (6, 7, 8, 9, 10)
COST_RESERVE_FACTOR = 1.3
COST_RESERVE_NOTE = "setup + 2*100*t with a 30% terminal reserve"
MAX_FITS_PER_BLOCK = 7
MAX_BLOCK_FITS = 42

# -- artifact layout (format v2) -------------------------------------------
RUN_DIRECTORY_FILES: Mapping[str, str] = {
    "config": "config.json",
    "command": "command.json",
    "provenance": "provenance.json",
    "status": "status.json",
    "readable_report": "report.json",
    "summary": "summary.md",
    "preprocessing": "preprocessing.json",
    "keys": "keys.npy",
    "months": "months.json",
    "splits": "splits.json",
    "history": "history.json",
    "scores": "scores.json",
    "gradients": "gradients.json",
    "baselines": "baselines.json",
    "fit_diagnostics": "fit-diagnostics.json",
    "masks": "masks.npz",
    "validation_prediction": "validation/prediction.npy",
    "validation_gold": "validation/gold.npy",
    "validation_metrics": "validation/metrics.json",
    "test_prediction": "test/prediction.npy",
    "test_gold": "test/gold.npy",
    "test_windows": "test/windows.json",
    "metrics": "metrics.json",
    "best_weights": "weights/best.pt",
    "last_recovery": "recovery/last.pt",
    "cost": "cost.json",
    "ledger": "ledger.json",
    "selection": "selection.json",
    "diagnostics": "diagnostics.json",
}

#: Arrays whose bytes must be sufficient for an independent recomputation.
RECOMPUTE_ARRAYS: Tuple[str, ...] = (
    "test/prediction.npy",
    "test/gold.npy",
    "validation/prediction.npy",
    "validation/gold.npy",
    "keys.npy",
    "masks.npz",
)

HASH_ALGORITHM = "sha256"


class ProtocolError(ValueError):
    """Raised when a request violates the frozen protocol."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    from . import resources
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            resources.check_stage_budget()
            digest.update(block)
    return digest.hexdigest()


def canonical_json(payload: Any) -> str:
    """Return a stable JSON encoding used for content identities."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_sha256(payload: Any) -> str:
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def protocol_content_sha256() -> Optional[str]:
    """SHA256 of the frozen P02 protocol document, or ``None`` when absent."""
    if P02_PROTOCOL_PATH.is_file():
        return sha256_file(P02_PROTOCOL_PATH)
    return None


def normalization_scale(square_sum: float, elements: int) -> float:
    """Return ``max(1, sqrt(sum(y^2)/(N*27)))`` from exact float64 sums."""
    if elements <= 0:
        raise ProtocolError("the training-only RMS needs at least one value")
    value = math.sqrt(float(square_sum) / float(elements))
    return max(1.0, value)


def validate_dataset(data_name: str) -> str:
    if data_name not in DATASETS:
        raise ProtocolError(
            f"unsupported dataset {data_name!r}; supported: {list(DATASETS)}"
        )
    return data_name


def validate_mode(mode: str) -> str:
    if mode not in MODES:
        raise ProtocolError(f"unsupported mode {mode!r}; supported: {list(MODES)}")
    return mode


def validate_model(model: str) -> str:
    if model not in MODELS:
        raise ProtocolError(f"unsupported model {model!r}; supported: {list(MODELS)}")
    return model


def validate_purpose(purpose: str) -> str:
    if purpose not in PURPOSES:
        raise ProtocolError(
            f"unsupported purpose {purpose!r}; supported: {list(PURPOSES)}"
        )
    return purpose


def validate_learning_rate(learning_rate: float) -> float:
    for candidate in LR_CANDIDATES:
        if float(learning_rate) == float(candidate):
            return float(learning_rate)
    raise ProtocolError(
        f"learning rate {learning_rate!r} is outside the frozen candidate set "
        f"{list(LR_CANDIDATES)}"
    )


def validate_split() -> None:
    """Reject a mutated P01 main split before any fit or report."""
    p01.validate_split_assertions(p01.MAIN_SPLIT)


def split_payload() -> Dict[str, Any]:
    validate_split()
    definition = p01.MAIN_SPLIT
    return {
        "name": definition.name,
        "fitting_month_count": definition.fitting_month_count,
        "train_starts": list(definition.train_starts),
        "validation_starts": list(definition.validation_starts),
        "test_starts": list(definition.evaluation_starts),
        "omitted_starts": list(definition.omitted_starts),
        "omitted_reasons": {
            str(start): reason
            for start, reason in definition.omitted_reason_map().items()
        },
        "train_target_months": list(
            p01.MAIN_SPLIT.target_months_for("train")
        ),
        "validation_target_months": list(
            p01.MAIN_SPLIT.target_months_for("validation")
        ),
        "test_target_months": list(p01.MAIN_SPLIT.eval_target_months),
        "input_length": p01.INPUT_LENGTH,
        "horizon": p01.HORIZON,
        "months": list(p01.MONTHS),
    }


def train_observation_months() -> Tuple[str, ...]:
    return p01.TRAIN_OBSERVATION_MONTHS


def fit_observation_month_count() -> int:
    """Months needed by the training and validation windows only (0..29)."""
    definition = p01.MAIN_SPLIT
    starts = list(definition.train_starts) + list(definition.validation_starts)
    highest = max(start + p01.INPUT_LENGTH + p01.HORIZON for start in starts)
    return int(highest)


def target_month_multiplicities(starts: Sequence[int]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for start in starts:
        for month in p01.window_target_months(int(start)):
            counts[month] = counts.get(month, 0) + 1
    return counts


@dataclass(frozen=True)
class FitConfig:
    """One immutable trajectory request."""

    model: str = "GRU"
    seed: int = 0
    learning_rate: float = 1e-3
    epochs: int = EPOCHS
    hidden_size: int = HIDDEN_SIZE
    layers: int = LAYERS
    node_chunk: int = 2048
    grad_clip: float = GRAD_CLIP_NORM
    threads: int = 1
    diagnostic_epochs: Tuple[int, ...] = DIAGNOSTIC_EPOCHS

    def validate(self) -> "FitConfig":
        validate_model(self.model)
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ProtocolError(f"seed must be a nonnegative integer, got {self.seed!r}")
        validate_learning_rate(self.learning_rate)
        if not isinstance(self.epochs, int) or self.epochs <= 0:
            raise ProtocolError(f"epochs must be a positive integer, got {self.epochs!r}")
        if self.epochs > EPOCHS:
            raise ProtocolError(
                f"epochs {self.epochs} exceeds the frozen budget of {EPOCHS}"
            )
        if not isinstance(self.hidden_size, int) or self.hidden_size <= 0:
            raise ProtocolError("hidden_size must be a positive integer")
        if not isinstance(self.layers, int) or self.layers <= 0:
            raise ProtocolError("layers must be a positive integer")
        if not isinstance(self.node_chunk, int) or self.node_chunk <= 0:
            raise ProtocolError("node_chunk must be a positive integer")
        if not isinstance(self.grad_clip, (int, float)) or float(self.grad_clip) <= 0:
            raise ProtocolError("grad_clip must be a positive number")
        if not isinstance(self.threads, int) or self.threads != 1:
            raise ProtocolError(
                "this protocol is CPU single-thread only; threads must be 1"
            )
        if tuple(self.diagnostic_epochs) != DIAGNOSTIC_EPOCHS:
            raise ProtocolError(
                f"diagnostic epochs are frozen at {list(DIAGNOSTIC_EPOCHS)}"
            )
        return self

    def to_payload(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "seed": int(self.seed),
            "learning_rate": float(self.learning_rate),
            "epochs": int(self.epochs),
            "hidden_size": int(self.hidden_size),
            "layers": int(self.layers),
            "node_chunk": int(self.node_chunk),
            "grad_clip": float(self.grad_clip),
            "threads": int(self.threads),
            "diagnostic_epochs": list(self.diagnostic_epochs),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "FitConfig":
        return cls(
            model=str(payload["model"]),
            seed=int(payload["seed"]),
            learning_rate=float(payload["learning_rate"]),
            epochs=int(payload["epochs"]),
            hidden_size=int(payload["hidden_size"]),
            layers=int(payload["layers"]),
            node_chunk=int(payload["node_chunk"]),
            grad_clip=float(payload["grad_clip"]),
            threads=int(payload["threads"]),
            diagnostic_epochs=tuple(int(v) for v in payload["diagnostic_epochs"]),
        ).validate()

    def deviations(self) -> List[str]:
        """Return every way this request differs from the frozen controls."""
        found: List[str] = []
        if self.epochs != EPOCHS:
            found.append(f"epochs={self.epochs} (protocol {EPOCHS})")
        if self.hidden_size != HIDDEN_SIZE:
            found.append(f"hidden_size={self.hidden_size} (protocol {HIDDEN_SIZE})")
        if self.layers != LAYERS:
            found.append(f"layers={self.layers} (protocol {LAYERS})")
        if float(self.grad_clip) != GRAD_CLIP_NORM:
            found.append(f"grad_clip={self.grad_clip} (protocol {GRAD_CLIP_NORM})")
        return found

    @property
    def complete_protocol(self) -> bool:
        return not self.deviations()


def require_formal_controls(config: FitConfig) -> None:
    deviations = config.deviations()
    if deviations:
        raise ProtocolError(
            "formal purpose requires complete protocol controls; deviations: "
            + ", ".join(deviations)
        )


def resource_controls(purpose: str, limit_bytes: Any = MEMORY_STOP_BYTES) -> Dict[str, Any]:
    """Validate the effective RSS stop before reserving any execution output."""
    validate_purpose(purpose)
    if isinstance(limit_bytes, bool) or not isinstance(limit_bytes, int) or limit_bytes <= 0:
        raise ProtocolError("memory_limit_bytes must be a positive integer")
    if purpose == "formal" and limit_bytes > MEMORY_STOP_BYTES:
        raise ProtocolError("formal RSS stopping line cannot exceed 8 GiB")
    override = limit_bytes != MEMORY_STOP_BYTES
    return {
        "rss_stop_bytes": limit_bytes,
        "protocol_rss_stop_bytes": MEMORY_STOP_BYTES,
        "development_override": purpose == "development" and override,
        "conservative_limit": limit_bytes < MEMORY_STOP_BYTES,
        "complete": not (purpose == "development" and override),
    }


@dataclass(frozen=True)
class Roles:
    """Selection/repetition identity of one trajectory."""

    candidate_role: str = "confirmation"
    repeat_role: str = "a"

    def validate(self) -> "Roles":
        if self.candidate_role not in CANDIDATE_ROLES:
            raise ProtocolError(
                f"candidate role must be one of {list(CANDIDATE_ROLES)}, "
                f"got {self.candidate_role!r}"
            )
        if self.repeat_role not in REPEAT_ROLES:
            raise ProtocolError(
                f"repeat role must be one of {list(REPEAT_ROLES)}, "
                f"got {self.repeat_role!r}"
            )
        return self

    def to_payload(self) -> Dict[str, Any]:
        return {
            "candidate_role": self.candidate_role,
            "repeat_role": self.repeat_role,
        }


def condition_identity(
    config: FitConfig,
    *,
    dataset: str,
    mode: str,
    data_sha256: Optional[str],
    keys_sha256: Optional[str],
    protocol_sha256: Optional[str],
) -> Dict[str, Any]:
    """Return the shared condition identity of an a/b repetition pair.

    ``purpose``, output paths, run IDs and the repetition role are excluded so a
    same-condition a/b pair shares one identity while different seeds, data
    contents, model settings or protocol contents never do.
    """
    payload = {
        "scientific_version": SCIENTIFIC_VERSION,
        "dataset": dataset,
        "mode": mode,
        "config": config.to_payload(),
        "data_sha256": data_sha256,
        "keys_sha256": keys_sha256,
        "protocol_sha256": protocol_sha256,
        "split": split_payload(),
    }
    return {
        "condition_id": content_sha256(payload),
        "payload": payload,
    }


def summary_statistics(values: Sequence[float]) -> Dict[str, Any]:
    """Return mean / sample standard deviation for a nonempty sequence."""
    numbers = [float(value) for value in values]
    if not numbers:
        return {"mean": None, "sample_sd": None, "count": 0}
    mean = sum(numbers) / len(numbers)
    if len(numbers) < 2:
        sd = 0.0
    else:
        variance = sum((value - mean) ** 2 for value in numbers) / (len(numbers) - 1)
        sd = math.sqrt(variance)
    return {"mean": mean, "sample_sd": sd, "count": len(numbers)}
