"""Module entry point for ``python -m benchmark.occupation_skill_graph``."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
