"""Private isolated-worker entry point (not part of the public command surface).

The public ``run`` command launches this module in a fresh CPU subprocess with
pinned BLAS threads, so process-lifetime peak RSS and stage timings belong to a
single dataset run.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

from .runner import RunInterrupted, RunSpec, execute_run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nograph-baseline-worker")
    parser.add_argument("--spec", required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    spec = RunSpec.from_dict(payload)

    def _terminate(signum: int, _frame: Any) -> None:
        raise RunInterrupted(f"received signal {signum}")

    previous = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, _terminate)
    try:
        result = execute_run(spec)
    except RunInterrupted:
        print("run interrupted; partial evidence retained", file=sys.stderr)
        return 130
    except KeyboardInterrupt:
        print("run interrupted; partial evidence retained", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - evidence is already on disk
        print(f"run failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
