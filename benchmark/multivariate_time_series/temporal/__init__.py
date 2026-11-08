"""Protocol-isolated recurrent training for ``P2-effective-training-L6-H3-v1``.

The package keeps the scientific constants of ``research/phases/P02/protocol.md``
in :mod:`benchmark.multivariate_time_series.temporal.protocol` and separates the
entry point into explicit stages: preflight, fit, select, diagnose, report,
recompute, compare and resume.  The public module path remains
``benchmark.multivariate_time_series.effective_temporal_training``.
"""

from __future__ import annotations

__all__ = [
    "protocol",
    "data",
    "model",
    "engine",
    "selection",
    "diagnostics",
    "report",
    "artifacts",
    "checks",
    "resources",
    "recovery",
]
