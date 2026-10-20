"""CPU skeleton entry for the frozen P02 temporal graph-value comparison.

The package implements P02-T001 only: a per-node raw-count GRU(1,32) encoder,
a shared Linear(32,3) head, unweighted incoming-neighbour mean propagation and
a degree-preserving context-local shuffled control.  It reuses the P01 numeric
contract (data identity, splits, naive references, masks and metrics) without
requiring torch in the graph-free entry.
"""

from __future__ import annotations

__all__ = ["SCIENTIFIC_PROTOCOL_VERSION", "SKELETON_VERSION", "TASK_ID"]
__version__ = "1.0.0"

from .protocol import (  # noqa: E402
    SCIENTIFIC_PROTOCOL_VERSION,
    SKELETON_VERSION,
    TASK_ID,
)
