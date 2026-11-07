"""CPU-only occupation-skill graph construction and audit (P02-T009).

The package implements ``P2-occupation-skill-graph-v1`` from the training-period
r2/count demand observations.  It builds two independent candidates
(occupational-support Jaccard and demand-composition cosine), retains a
deterministic top-10 undirected union with explicit scores, maps the shared
relation into r0/region/r2 contexts without duplicating edge storage, and audits
structure, target population and occupational trend heterogeneity.

The public entry point is the module CLI::

    python -m benchmark.occupation_skill_graph --help

It requires only NumPy, pandas and PyArrow; no model, graph-learning or GPU
package is imported.
"""

from __future__ import annotations

from .protocol import (  # noqa: E402
    SCIENTIFIC_PROTOCOL_VERSION,
    TASK_ID,
)

__version__ = "1.0.0"

__all__ = ["SCIENTIFIC_PROTOCOL_VERSION", "TASK_ID", "__version__"]
