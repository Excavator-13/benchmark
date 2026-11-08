"""Protocol-isolated recurrent training for P02/T006 (staged entry point).

The module path is preserved, but the entry is now a sequence of explicit
operations instead of one implicit train-then-test call:

``preflight`` -> ``fit`` -> ``select`` -> ``diagnose`` -> ``report``

with saved-evidence ``recompute``/``compare`` and parent-linked ``resume``.
Training and validation are the only inputs to ``fit``; the four rolling test
windows 24..27 are constructed exclusively by ``report`` after the selection and
validation diagnostics are frozen.

The default purpose is ``development`` and its output stays under an ignored
``scratch/`` root.  A development output that resolves into ``research/runs/`` is
rejected.  Formal operation requires a complete 100-epoch protocol trajectory and
explicit research authorization; this module never schedules the real-data
matrix and never declares research acceptance.

Legacy calls are rejected with a migration error: old single-window results and
checkpoints without format-2 recovery state cannot be reused as new evidence.
"""

from __future__ import annotations

from typing import Any, Iterable, NoReturn, Optional, Sequence

import numpy as np

from .temporal import protocol as _protocol

#: Backward-compatible configuration name (the same frozen request object).
Config = _protocol.FitConfig

#: Raised for the retired implicit train/test invocation.
LegacyInvocationError = RuntimeError

#: Scientific and artifact versions exported for downstream records.
SCIENTIFIC_VERSION = _protocol.SCIENTIFIC_VERSION
ARTIFACT_FORMAT_VERSION = _protocol.ARTIFACT_FORMAT_VERSION
PROTOCOL_VERSION = _protocol.SCIENTIFIC_VERSION
TRAIN_MONTHS = 27
SEQ_LEN = 6
PRED_LEN = 3

_MIGRATION = (
    "the implicit train-then-test API was removed by the staged P02 entry.\n"
    "Use the command line instead:\n"
    "  python -m benchmark.multivariate_time_series.effective_temporal_training \\\n"
    "      fit --data-name r0 --model GRU --seed 0 --learning-rate 1e-3 --run-id <id>\n"
    "then `select`, `diagnose` and finally `report` for the four test windows.\n"
    "Old single-window results and old checkpoints are not reusable evidence."
)


def __getattr__(name: str) -> Any:
    """Import torch-dependent names lazily so thread setup precedes torch."""
    if name == "RecurrentForecaster":
        from .temporal.model import RecurrentForecaster

        return RecurrentForecaster
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def training_rms(values: np.ndarray) -> float:
    """Return ``max(1, sqrt(sum(y^2)/(N*27)))`` for a training-only array."""
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != TRAIN_MONTHS:
        raise ValueError(f"training values must have shape (nodes, {TRAIN_MONTHS})")
    square_sum = float(np.sum(arr * arr, dtype=np.float64))
    return _protocol.normalization_scale(square_sum, int(arr.size))


def make_windows(
    values: np.ndarray, start: int, count: int = 1
) -> "tuple[np.ndarray, np.ndarray]":
    """Return ``[N, count, L6]`` inputs and ``[N, count, H3]`` targets."""
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] < start + SEQ_LEN + PRED_LEN:
        raise ValueError("values do not contain the requested L6/H3 window")
    xs = np.stack(
        [arr[:, s : s + SEQ_LEN] for s in range(start, start + count)], axis=1
    )
    ys = np.stack(
        [arr[:, s + SEQ_LEN : s + SEQ_LEN + PRED_LEN] for s in range(start, start + count)],
        axis=1,
    )
    return xs, ys


def train(*_args: Any, **_kwargs: Any) -> NoReturn:
    """Retired implicit fit+test call; always rejected."""
    raise LegacyInvocationError(_MIGRATION)


def compare(*_args: Any, **_kwargs: Any) -> NoReturn:
    """Retired implicit matrix comparison; always rejected."""
    raise LegacyInvocationError(_MIGRATION)


def load_checkpoint(*_args: Any, **_kwargs: Any) -> NoReturn:
    """Retired unchecked checkpoint loader; always rejected."""
    raise LegacyInvocationError(_MIGRATION)


def build_parser() -> Any:
    from .temporal.cli import build_parser as _build_parser

    return _build_parser()


def main(argv: Optional[Sequence[str]] = None) -> int:
    from .temporal.cli import main as _main

    return _main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
