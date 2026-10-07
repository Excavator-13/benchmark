"""Command-line interface with isolated CPU workers.

The default BLAS thread counts are pinned to 1 *before* NumPy is imported so
that process-lifetime peak RSS and stage timings are attributable to one
dataset run and can be repeated under identical conditions.  The public
commands are ``run``, ``recompute``, ``compare`` and ``align-v2``.
"""

from __future__ import annotations

import os

# Pin the CPU linear-algebra threads before NumPy/PyArrow are imported.
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
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, Dict, List, Optional, Sequence  # noqa: E402

from . import protocol  # noqa: E402

WORKER_MODULE = "benchmark.nograph_baseline._worker"


def _resolve(path: Optional[str], base: Path) -> Optional[Path]:
    if path is None:
        return None
    candidate = Path(path)
    return candidate if candidate.is_absolute() else (base / candidate)


def _repo_root(args: argparse.Namespace) -> Path:
    return Path(args.repo_root).resolve() if args.repo_root else protocol.REPO_ROOT


def _runs_root(args: argparse.Namespace, repo_root: Path) -> Path:
    if args.runs_root:
        return Path(args.runs_root).resolve()
    return repo_root / "research" / "runs"


def build_parser() -> argparse.ArgumentParser:
    """Build the public parser with the stable command surface."""
    parser = argparse.ArgumentParser(
        prog="python -m benchmark.nograph_baseline",
        description=(
            "Graph-free CPU baseline entry for the P1-count-L6-H3-v3 protocol "
            "(r0/count and region/count). Uses only NumPy, pandas and PyArrow on "
            "the default path."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="repository root override (default: derived from the module location)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser(
        "run", help="execute one formal CPU run for a dataset"
    )
    run.add_argument(
        "--data-name",
        required=True,
        choices=sorted(protocol.SUPPORTED_DATASETS),
        help="dataset granularity",
    )
    run.add_argument(
        "--mode",
        default="count",
        choices=list(protocol.SUPPORTED_MODES),
        help="value mode (only count is supported by this protocol)",
    )
    run.add_argument("--seed", type=int, default=0, help="deterministic seed")
    run.add_argument("--run-id", required=True, help="fresh run directory name")
    run.add_argument(
        "--ridge-backend",
        default="numpy",
        choices=("numpy", "sklearn"),
        help="shared Ridge solver (sklearn is optional)",
    )
    run.add_argument(
        "--clip-nonnegative",
        action="store_true",
        help=(
            "also save and report the separately labeled "
            "SharedRidgeNonnegative clipped outputs"
        ),
    )
    run.add_argument("--demand-path", default=None, help=argparse.SUPPRESS)
    run.add_argument("--graph-path", default=None, help=argparse.SUPPRESS)
    run.add_argument("--neighbor-mask", default=None, help=argparse.SUPPRESS)
    run.add_argument("--runs-root", default=None, help=argparse.SUPPRESS)
    run.add_argument("--protocol-path", default=None, help=argparse.SUPPRESS)
    run.set_defaults(handler=_handle_run)

    recompute = subparsers.add_parser(
        "recompute", help="recompute saved metrics from a completed run only"
    )
    recompute.add_argument("--run-dir", required=True)
    recompute.add_argument("--run-id", required=True)
    recompute.add_argument("--runs-root", default=None, help=argparse.SUPPRESS)
    recompute.set_defaults(handler=_handle_recompute)

    compare = subparsers.add_parser(
        "compare", help="compare two same-seed runs under the CPU tolerance"
    )
    compare.add_argument("--run-a", required=True)
    compare.add_argument("--run-b", required=True)
    compare.add_argument("--run-id", required=True)
    compare.add_argument("--runs-root", default=None, help=argparse.SUPPRESS)
    compare.set_defaults(handler=_handle_compare)

    align = subparsers.add_parser(
        "align-v2", help="align a run's naive results with the sealed v2 diagnostic"
    )
    align.add_argument("--run-dir", required=True)
    align.add_argument("--reference", required=True)
    align.add_argument("--run-id", required=True)
    align.add_argument("--runs-root", default=None, help=argparse.SUPPRESS)
    align.set_defaults(handler=_handle_align_v2)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Remember the exact invocation so run records can capture a replayable
    # canonical command even when main() is called programmatically.
    args.invocation_argv = list(argv) if argv is not None else list(sys.argv[1:])
    handler = getattr(args, "handler", None)
    if handler is None:  # pragma: no cover - argparse enforces subcommands
        parser.error("a command is required")
    try:
        return int(handler(args))
    except Exception as exc:  # noqa: BLE001 - surface a clean nonzero exit
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def _canonical_command(args: argparse.Namespace) -> List[str]:
    """Return the replayable module invocation for provenance records."""
    invocation = getattr(args, "invocation_argv", None)
    if invocation is None:
        invocation = list(sys.argv[1:])
    return [sys.executable, "-m", "benchmark.nograph_baseline", *invocation]


def _handle_run(args: argparse.Namespace) -> int:
    from .artifacts import validate_run_id

    repo_root = _repo_root(args)
    runs_root = _runs_root(args, repo_root)
    validate_run_id(args.run_id)
    run_type = "run"
    launcher_cwd = Path.cwd()
    spec = {
        "data_name": args.data_name,
        "run_id": args.run_id,
        "mode": args.mode,
        "seed": int(args.seed),
        "ridge_backend": args.ridge_backend,
        "clip_nonnegative": bool(args.clip_nonnegative),
        "demand_path": _resolve(args.demand_path, launcher_cwd).as_posix()
        if args.demand_path
        else None,
        "graph_path": _resolve(args.graph_path, launcher_cwd).as_posix()
        if args.graph_path
        else None,
        "mask_bundle": _resolve(args.neighbor_mask, launcher_cwd).as_posix()
        if args.neighbor_mask
        else None,
        "runs_root": runs_root.as_posix(),
        "repo_root": repo_root.as_posix(),
        "protocol_path": _resolve(args.protocol_path, launcher_cwd).as_posix()
        if args.protocol_path
        else None,
        "command": _canonical_command(args),
        "launcher_cwd": launcher_cwd.as_posix(),
        "run_type": run_type,
    }
    environment = dict(os.environ)
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        environment[variable] = "1"
    return _launch_worker(spec, environment, cwd=repo_root)


def _launch_worker(
    spec: Dict[str, Any], environment: Dict[str, str], *, cwd: Path
) -> int:
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="nograph-spec-", delete=False
    )
    try:
        json.dump(spec, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    argv = [
        sys.executable,
        "-m",
        WORKER_MODULE,
        "--spec",
        handle.name,
    ]
    forwarded: List[int] = []

    def _forward(signum: int, _frame: Any) -> None:
        forwarded.append(signum)
        if process.poll() is None:
            try:
                process.send_signal(signum)
            except (OSError, ValueError):  # pragma: no cover - process race
                pass

    previous = {
        signal.SIGINT: signal.getsignal(signal.SIGINT),
        signal.SIGTERM: signal.getsignal(signal.SIGTERM),
    }
    process = subprocess.Popen(argv, cwd=str(cwd), env=environment)
    try:
        signal.signal(signal.SIGINT, _forward)
        signal.signal(signal.SIGTERM, _forward)
        returncode = process.wait()
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        try:
            os.unlink(handle.name)
        except OSError:  # pragma: no cover - best effort cleanup
            pass
    if returncode < 0:
        print(
            f"worker terminated by signal {-returncode} "
            f"(forwarded={forwarded})",
            file=sys.stderr,
        )
        return 128 - returncode
    return returncode


def _handle_recompute(args: argparse.Namespace) -> int:
    from .checks import command_recompute

    repo_root = _repo_root(args)
    runs_root = _runs_root(args, repo_root)
    result = command_recompute(
        run_dir=_resolve(args.run_dir, Path.cwd()),
        run_id=args.run_id,
        runs_root=runs_root,
        repo_root=repo_root,
        command=_canonical_command(args),
    )
    print(json.dumps({"run_dir": result["run_dir"], "status": result["status"]}))
    return 0 if result["status"] == "ok" else 1


def _handle_compare(args: argparse.Namespace) -> int:
    from .checks import command_compare

    repo_root = _repo_root(args)
    runs_root = _runs_root(args, repo_root)
    result = command_compare(
        run_a=_resolve(args.run_a, Path.cwd()),
        run_b=_resolve(args.run_b, Path.cwd()),
        run_id=args.run_id,
        runs_root=runs_root,
        repo_root=repo_root,
        command=_canonical_command(args),
    )
    print(json.dumps({"run_dir": result["run_dir"], "status": result["status"]}))
    return 0 if result["status"] == "ok" else 1


def _handle_align_v2(args: argparse.Namespace) -> int:
    from .checks import command_align_v2

    repo_root = _repo_root(args)
    runs_root = _runs_root(args, repo_root)
    result = command_align_v2(
        run_dir=_resolve(args.run_dir, Path.cwd()),
        reference=_resolve(args.reference, Path.cwd()),
        run_id=args.run_id,
        runs_root=runs_root,
        repo_root=repo_root,
        command=_canonical_command(args),
    )
    print(json.dumps({"run_dir": result["run_dir"], "status": result["status"]}))
    return 0 if result["status"] == "ok" else 1
