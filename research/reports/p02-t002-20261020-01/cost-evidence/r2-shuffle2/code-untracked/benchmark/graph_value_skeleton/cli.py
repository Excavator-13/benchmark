"""Public command surface with an isolated CPU worker.

The BLAS thread variables are pinned before NumPy/torch are imported so stage
timings and process-lifetime peak RSS belong to a single CPU execution.  The
public commands are ``run``, ``recompute``, ``compare`` and
``summarize-shuffled``.  ``run`` launches a fresh worker process; saved-result
checks run in-process, read only saved evidence and write one exclusive report.
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
import os as _os  # noqa: E402
import signal  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, Dict, List, Optional, Sequence  # noqa: E402

from . import protocol  # noqa: E402

WORKER_MODULE = "benchmark.graph_value_skeleton._worker"
BLAS_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m benchmark.graph_value_skeleton",
        description=(
            "Frozen P02 temporal skeleton (per-node GRU(1,32) + shared "
            "Linear(32,3)) with self, real-graph and degree-preserving shuffled "
            "branches on the unchanged P1-count-L6-H3-v3 protocol. CPU only."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help=(
            "repository root override; must be the project checkout or a "
            "temporary directory (default: derived from the module location)"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="execute one CPU skeleton run")
    run.add_argument(
        "--data-name",
        required=True,
        choices=sorted(protocol.PUBLISHED_DEMAND),
        help="published dataset granularity (r0 | region | r2)",
    )
    run.add_argument(
        "--method",
        required=True,
        choices=list(protocol.METHODS),
        help="self | graph | shuffled",
    )
    run.add_argument(
        "--model-seed",
        required=True,
        type=int,
        help="model seed (development profile 0..2, final profile 0..4)",
    )
    run.add_argument(
        "--shuffle-seed",
        type=int,
        default=None,
        help="0|1|2, required for --method shuffled and forbidden otherwise",
    )
    run.add_argument(
        "--purpose",
        default=protocol.PURPOSE_DEVELOPMENT,
        choices=list(protocol.PURPOSES),
        help=(
            "development (default; ignored scratch/temp output only) or formal "
            "(research/runs; requires separate research authorization)"
        ),
    )
    run.add_argument("--run-id", required=True, help="fresh run directory name")
    run.add_argument(
        "--output-root",
        default=None,
        help=(
            "development-only output root; must resolve inside the ignored "
            "scratch tree or the system temporary directory"
        ),
    )
    run.add_argument("--demand-path", default=None, help=argparse.SUPPRESS)
    run.add_argument("--graph-path", default=None, help=argparse.SUPPRESS)
    run.add_argument("--shuffle-artifact", default=None, help="checked prepared graph; shuffled only")
    run.set_defaults(handler=_handle_run)

    prepare = subparsers.add_parser('prepare-shuffle', help='prepare one development graph without training')
    prepare.add_argument('--data-name', required=True, choices=sorted(protocol.PUBLISHED_DEMAND))
    prepare.add_argument('--shuffle-seed', required=True, type=int, choices=protocol.SHUFFLE_SEEDS)
    prepare.add_argument('--run-id', required=True)
    prepare.add_argument('--output-root', default=None)
    prepare.add_argument('--demand-path', default=None, help=argparse.SUPPRESS)
    prepare.add_argument('--graph-path', default=None, help=argparse.SUPPRESS)
    prepare.set_defaults(handler=_handle_prepare)
    check = subparsers.add_parser('check-shuffle', help='check one prepared graph from saved evidence only')
    check.add_argument('--artifact-dir', required=True)
    check.add_argument('--report', required=True)
    check.set_defaults(handler=_handle_check_shuffle)

    recompute = subparsers.add_parser(
        "recompute", help="recompute every saved metric from saved evidence only"
    )
    recompute.add_argument("--run-dir", required=True)
    recompute.add_argument("--report", required=True)
    recompute.set_defaults(handler=_handle_recompute)

    compare = subparsers.add_parser(
        "compare", help="compare two same-condition runs under the CPU tolerance"
    )
    compare.add_argument("--run-a", required=True)
    compare.add_argument("--run-b", required=True)
    compare.add_argument("--report", required=True)
    compare.set_defaults(handler=_handle_compare)

    summarize = subparsers.add_parser(
        "summarize-shuffled",
        help="average the three shuffle-seed MAEs for one model seed",
    )
    summarize.add_argument(
        "--run-dirs", nargs=3, required=True, metavar=("SEED0", "SEED1", "SEED2")
    )
    summarize.add_argument("--report", required=True)
    summarize.set_defaults(handler=_handle_summarize)

    return parser


def _repo_root(args: argparse.Namespace) -> Path:
    return Path(args.repo_root).resolve() if args.repo_root else protocol.REPO_ROOT


def _resolve(path: Optional[str], base: Path) -> Optional[Path]:
    if path is None:
        return None
    candidate = Path(path)
    return candidate if candidate.is_absolute() else (base / candidate)


def _canonical_command(args: argparse.Namespace) -> List[str]:
    invocation = getattr(args, "invocation_argv", None)
    if invocation is None:
        invocation = list(sys.argv[1:])
    return [sys.executable, "-m", "benchmark.graph_value_skeleton", *invocation]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.invocation_argv = list(argv) if argv is not None else list(sys.argv[1:])
    handler = getattr(args, "handler", None)
    if handler is None:  # pragma: no cover - argparse enforces subcommands
        parser.error("a command is required")
    try:
        return int(handler(args))
    except Exception as exc:  # noqa: BLE001 - surface a clean nonzero exit
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def _handle_run(args: argparse.Namespace) -> int:
    from .config import resolve_config

    repo_root = _repo_root(args)
    launcher_cwd = Path.cwd()
    config = resolve_config(
        data_name=args.data_name,
        method=args.method,
        model_seed=args.model_seed,
        shuffle_seed=args.shuffle_seed,
        run_id=args.run_id,
        purpose=args.purpose,
        repo_root=repo_root,
        output_root=_resolve(args.output_root, launcher_cwd),
        demand_path=args.demand_path,
        graph_path=args.graph_path,
        shuffle_artifact=args.shuffle_artifact,
        command=_canonical_command(args),
        launcher_cwd=launcher_cwd,
    )
    environment = dict(_os.environ)
    for variable in BLAS_VARIABLES:
        environment[variable] = "1"
    spec = {"config": config.to_dict()}
    return _launch_worker(spec, environment, cwd=repo_root)


def _handle_prepare(args):
    # Windows Arrow/pandas DLLs can prevent a later c10.dll initialization.
    # Preparation already records torch runtime evidence; load it before the
    # config/data modules load Arrow. This does not construct or train a model.
    if _os.name == 'nt':
        import torch  # noqa: F401
    from .config import resolve_config
    from .prepared import prepare
    config = resolve_config(data_name=args.data_name, method='shuffled', model_seed=0,
        shuffle_seed=args.shuffle_seed, run_id=args.run_id, repo_root=_repo_root(args),
        output_root=_resolve(args.output_root, Path.cwd()) if args.output_root else None,
        demand_path=args.demand_path, graph_path=args.graph_path,
        command=_canonical_command(args), launcher_cwd=Path.cwd())
    print(json.dumps(prepare(config), sort_keys=True))
    return 0


def _handle_check_shuffle(args):
    from .prepared import check
    result = check(_resolve(args.artifact_dir, Path.cwd()), _resolve(args.report, Path.cwd()),
                   _repo_root(args), _canonical_command(args))
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'ok' else 1


def _launch_worker(
    spec: Dict[str, Any], environment: Dict[str, str], *, cwd: Path
) -> int:
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="gvs-spec-", delete=False
    )
    try:
        json.dump(spec, handle, sort_keys=True)
        handle.flush()
        _os.fsync(handle.fileno())
    finally:
        handle.close()
    argv = [sys.executable, "-m", WORKER_MODULE, "--spec", handle.name]
    forwarded: List[int] = []
    process: Optional[subprocess.Popen] = None

    def _forward(signum: int, _frame: Any) -> None:
        forwarded.append(signum)
        if process is not None and process.poll() is None:
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
            _os.unlink(handle.name)
        except OSError:  # pragma: no cover - best effort cleanup
            pass
    if returncode < 0:
        print(
            f"worker terminated by signal {-returncode} (forwarded={forwarded})",
            file=sys.stderr,
        )
        return 128 - returncode
    return returncode


def _print_check_result(result: Dict[str, Any]) -> int:
    print(
        json.dumps(
            {"report_path": result["report_path"], "status": result["status"]}
        )
    )
    return 0 if result["status"] == "ok" else 1


def _handle_recompute(args: argparse.Namespace) -> int:
    from .checks import command_recompute

    repo_root = _repo_root(args)
    result = command_recompute(
        run_dir=_resolve(args.run_dir, Path.cwd()),
        repo_root=repo_root,
        command=_canonical_command(args),
        report_path=_resolve(args.report, Path.cwd()),
    )
    return _print_check_result(result)


def _handle_compare(args: argparse.Namespace) -> int:
    from .checks import command_compare

    repo_root = _repo_root(args)
    result = command_compare(
        run_a=_resolve(args.run_a, Path.cwd()),
        run_b=_resolve(args.run_b, Path.cwd()),
        repo_root=repo_root,
        command=_canonical_command(args),
        report_path=_resolve(args.report, Path.cwd()),
    )
    return _print_check_result(result)


def _handle_summarize(args: argparse.Namespace) -> int:
    from .checks import command_summarize_shuffled

    repo_root = _repo_root(args)
    result = command_summarize_shuffled(
        run_dirs=[_resolve(path, Path.cwd()) for path in args.run_dirs],
        repo_root=repo_root,
        command=_canonical_command(args),
        report_path=_resolve(args.report, Path.cwd()),
    )
    return _print_check_result(result)
