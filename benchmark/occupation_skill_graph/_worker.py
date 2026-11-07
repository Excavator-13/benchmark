"""Private isolated-worker entry point (not part of the public command surface).

The public ``build`` command launches this module in a fresh CPU subprocess with
single-thread BLAS settings established before numerical imports, so
process-lifetime peak RSS and stage timings belong to one execution.
"""

from __future__ import annotations

import os

for _variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_variable, "1")

import argparse  # noqa: E402
import json  # noqa: E402
import signal  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, Optional, Sequence  # noqa: E402

from .runner import BuildSpec, RunInterrupted, execute_build  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="occupation-skill-graph-worker")
    parser.add_argument("--spec", required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    spec = BuildSpec.from_dict(payload)

    def _terminate(signum: int, _frame: Any) -> None:
        raise RunInterrupted(f"received signal {signum}")

    previous = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, _terminate)
    try:
        result = execute_build(spec)
    except RunInterrupted:
        print("build interrupted; completed-stage evidence retained", file=sys.stderr)
        return 130
    except KeyboardInterrupt:
        print("build interrupted; completed-stage evidence retained", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - failure evidence is already on disk
        print(f"build failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
