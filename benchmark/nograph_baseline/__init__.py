"""Graph-free CPU baseline entry for the P01 count datasets.

This package implements the ``P1-count-L6-H3-v3`` protocol defined in
``research/phases/P01/protocol.md`` sections 3-6 without importing any graph
method module, PyTorch, PyG or DGL.  The only required third-party
dependencies are NumPy, pandas and PyArrow; scikit-learn is an optional
backend.

The public entry point is the module CLI::

    python -m benchmark.nograph_baseline --help
"""

from __future__ import annotations

from .protocol import PROTOCOL_VERSION, __all__ as _protocol_all

__version__ = "0.1.0"

__all__ = ["PROTOCOL_VERSION", "__version__", *_protocol_all]
