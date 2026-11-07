"""Public command surface for the occupation-skill graph audit.

``build`` launches an isolated CPU worker after resolving a safe development
scratch/temp root or an explicit fresh research ``research/runs/<run-id>``
directory.  ``check`` rederives every scientific array from saved evidence and
writes one exclusive external report.  This module imports no numerical or ML
package at import time, so ``--help`` works without NumPy/pandas/torch.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import paths, protocol

BLAS_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m benchmark.occupation_skill_graph",
        description=(
            "CPU-only P2-occupation-skill-graph-v1 construction and audit from "
            "r2 training demand. Builds two independent candidates, a "
            "deterministic top-10 union and diagnostic structure/trend audits. "
            "No model, graph-learning or GPU package is required."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help=(
            "repository root override (default: derived from the module "
            "location); output and source paths are resolved against it"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser(
        "build", help="execute one isolated CPU graph construction audit"
    )
    build.add_argument("--run-id", required=True, help="fresh output directory name")
    build.add_argument(
        "--purpose",
        default=protocol.DEVELOPMENT_PURPOSE,
        choices=list(protocol.PURPOSES),
        help=(
            "development (default; ignored scratch or system temp only) or "
            "research (fresh research/runs/<run-id>; separate authorization)"
        ),
    )
    build.add_argument(
        "--output-root",
        default=None,
        help=(
            "development-only output root; must resolve inside the ignored "
            "scratch tree or the system temporary directory"
        ),
    )
    build.add_argument(
        "--fixture",
        action="store_true",
        help=(
            "explicit development fixture mode; requires --demand-path and all "
            "three --target-path values and skips published identity ranges"
        ),
    )
    build.add_argument(
        "--demand-path",
        default=None,
        help="fixture-only training Parquet path (published mode uses dataset/)",
    )
    build.add_argument(
        "--target-path",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="fixture-only target key table; repeat for r0, region and r2",
    )
    build.add_argument(
        "--build-timeout-seconds",
        type=float,
        default=protocol.DEFAULT_STAGE_TIMEOUT_SECONDS,
        help="construction/source/target stage deadline (default: 1800 s)",
    )
    build.add_argument(
        "--trend-timeout-seconds",
        type=float,
        default=protocol.DEFAULT_STAGE_TIMEOUT_SECONDS,
        help="trend stage deadline (default: 1800 s)",
    )
    build.add_argument(
        "--max-rss-bytes",
        type=int,
        default=protocol.DEFAULT_MAX_RSS_BYTES,
        help="sampled worker process RSS limit in bytes (default: 2 GiB)",
    )
    build.add_argument(
        "--monitor-interval-seconds",
        type=float,
        default=protocol.DEFAULT_MONITOR_INTERVAL_SECONDS,
        help="RSS/progress sampling interval (default: 0.25 s)",
    )
    build.add_argument("--fail-after-stage", default=None, help=argparse.SUPPRESS)
    build.set_defaults(handler=_handle_build)

    check = subparsers.add_parser(
        "check", help="rederive a saved audit from saved evidence only"
    )
    check.add_argument("--artifact-dir", required=True)
    check.add_argument("--report", required=True)
    check.set_defaults(handler=_handle_check)
    return parser


def _repo_root(args: argparse.Namespace) -> Path:
    return Path(args.repo_root).resolve() if args.repo_root else protocol.REPO_ROOT


def _canonical_command(args: argparse.Namespace) -> List[str]:
    invocation = getattr(args, "invocation_argv", None)
    if invocation is None:
        invocation = list(sys.argv[1:])
    return [sys.executable, "-m", "benchmark.occupation_skill_graph", *invocation]


def _parse_target_paths(values: Sequence[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(
                f"target path {value!r} must use the NAME=PATH form"
            )
        name, path = value.split("=", 1)
        name = name.strip()
        path = path.strip()
        if name not in protocol.TARGET_DATA_NAMES:
            raise ValueError(
                f"unsupported target name {name!r}; supported: "
                f"{list(protocol.TARGET_DATA_NAMES)}"
            )
        if not path:
            raise ValueError(f"target {name} path is empty")
        if name in mapping:
            raise ValueError(f"target {name} was supplied more than once")
        mapping[name] = str(Path(path).expanduser())
    return mapping


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


def _handle_build(args: argparse.Namespace) -> int:
    # Numerical imports stay inside the worker launch path.
    from . import artifacts
    from .runner import BuildSpec, execute_build
    from . import supervisor

    repo_root = _repo_root(args)
    purpose = args.purpose
    if purpose == protocol.RESEARCH_PURPOSE:
        if args.fixture:
            raise ValueError(
                "research purpose cannot use fixture injection; run the "
                "published r2 source as a separate research-side action"
            )
        if args.output_root is not None:
            raise ValueError(
                "research purpose always writes a fresh research/runs/<run-id> "
                "directory; --output-root is development-only"
            )
        if args.demand_path is not None or args.target_path:
            raise ValueError(
                "research purpose uses the published dataset paths; source "
                "overrides are fixture-only"
            )
    output_root = paths.resolve_output_root(
        purpose=purpose, output_root=Path(args.output_root) if args.output_root else None, repo_root=repo_root
    )
    artifacts.validate_run_id(args.run_id)

    fixture = bool(args.fixture)
    if fixture:
        if purpose != protocol.DEVELOPMENT_PURPOSE:
            raise ValueError("fixture mode is development-only")
        if args.demand_path is None:
            raise ValueError("fixture mode requires --demand-path")
        target_paths = _parse_target_paths(args.target_path)
        missing = [
            name
            for name in protocol.TARGET_DATA_NAMES
            if name not in target_paths
        ]
        if missing:
            raise ValueError(
                f"fixture mode requires --target-path for every target; missing "
                f"{missing}"
            )
        demand_path = str(Path(args.demand_path).expanduser())
    else:
        if args.demand_path is not None or args.target_path:
            raise ValueError(
                "published mode uses the immutable dataset paths and does not "
                "accept source overrides; use --fixture explicitly for fixtures"
            )
        demand_path = str(repo_root / "dataset" / "demand" / "r2.parquet")
        target_paths = {
            name: str(repo_root / "dataset" / "demand" / f"{name}.parquet")
            for name in protocol.TARGET_DATA_NAMES
        }

    spec = BuildSpec(
        run_id=args.run_id,
        purpose=purpose,
        repo_root=str(repo_root),
        output_root=str(output_root),
        demand_path=demand_path,
        target_paths=target_paths,
        fixture=fixture,
        build_timeout_seconds=float(args.build_timeout_seconds),
        trend_timeout_seconds=float(args.trend_timeout_seconds),
        max_rss_bytes=int(args.max_rss_bytes),
        monitor_interval_seconds=float(args.monitor_interval_seconds),
        command=_canonical_command(args),
        launcher_cwd=str(Path.cwd()),
        fail_after_stage=args.fail_after_stage,
    )
    return supervisor.launch(spec)


def _handle_check(args: argparse.Namespace) -> int:
    from .checks import check_artifact, CheckError

    repo_root = _repo_root(args)
    result = check_artifact(
        artifact_dir=Path(args.artifact_dir).expanduser(),
        report_path=Path(args.report).expanduser(),
        repo_root=repo_root,
        command=_canonical_command(args),
    )
    print(
        json.dumps(
            {"report_path": result["report_path"], "status": result["status"]}
        )
    )
    return 0 if result["status"] == "ok" else 1
