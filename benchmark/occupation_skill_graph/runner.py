"""Build orchestration for one occupation-skill graph audit.

The builder separates source loading, graph construction, target mapping,
trend diagnostics and finalization so a completed stage remains inspectable
after a later failure.  It writes no report and no success status until every
payload and audit has been persisted.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from . import artifacts, data, layout, mapping, protocol, scores, structure, trends

__all__ = [
    "BuildSpec",
    "BuildError",
    "RunInterrupted",
    "InjectedFailure",
    "reserve_run_directory",
    "execute_build",
    "stage_order",
]


class BuildError(RuntimeError):
    """Raised when a build request or its evidence violates the protocol."""


class RunInterrupted(RuntimeError):
    """Raised when the worker receives an interruption signal."""


class InjectedFailure(RuntimeError):
    """Test-only failure injected after a completed stage."""


STAGES: Tuple[str, ...] = ("source", "construct", "targets", "trends", "finalize")


def stage_order() -> Tuple[str, ...]:
    return STAGES


@dataclass
class BuildSpec:
    """Validated, serializable description of one build execution."""

    run_id: str
    purpose: str
    repo_root: str
    output_root: str
    demand_path: str
    target_paths: Dict[str, str]
    fixture: bool
    build_timeout_seconds: float = protocol.DEFAULT_STAGE_TIMEOUT_SECONDS
    trend_timeout_seconds: float = protocol.DEFAULT_STAGE_TIMEOUT_SECONDS
    max_rss_bytes: int = protocol.DEFAULT_MAX_RSS_BYTES
    monitor_interval_seconds: float = protocol.DEFAULT_MONITOR_INTERVAL_SECONDS
    command: List[str] = field(default_factory=list)
    launcher_cwd: str = ""
    fail_after_stage: Optional[str] = None
    run_reserved: bool = False

    def __post_init__(self) -> None:
        artifacts.validate_run_id(self.run_id)
        if self.purpose not in protocol.PURPOSES:
            raise BuildError(
                f"unsupported purpose {self.purpose!r}; supported: "
                f"{list(protocol.PURPOSES)}"
            )
        if self.purpose == protocol.RESEARCH_PURPOSE and self.fixture:
            raise BuildError(
                "fixture injection is development-only; research purpose requires "
                "the published r2 source"
            )
        if not Path(self.repo_root).exists():
            raise BuildError(f"repository root does not exist: {self.repo_root}")
        if not Path(self.demand_path).is_file():
            raise BuildError(f"training source does not exist: {self.demand_path}")
        if set(self.target_paths) != set(protocol.TARGET_DATA_NAMES):
            raise BuildError(
                "target paths must name exactly "
                f"{list(protocol.TARGET_DATA_NAMES)}, got {sorted(self.target_paths)}"
            )
        for name, path in self.target_paths.items():
            if not Path(path).is_file():
                raise BuildError(f"target {name} source does not exist: {path}")
        for label, value in (
            ("build timeout", self.build_timeout_seconds),
            ("trend timeout", self.trend_timeout_seconds),
            ("monitor interval", self.monitor_interval_seconds),
        ):
            if not np.isfinite(value) or value <= 0:
                raise BuildError(f"{label} must be a positive finite number")
        if self.max_rss_bytes <= 0:
            raise BuildError("max RSS must be a positive byte count")
        if self.fail_after_stage is not None and self.fail_after_stage not in STAGES:
            raise BuildError(f"unsupported failure stage {self.fail_after_stage!r}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "purpose": self.purpose,
            "repo_root": self.repo_root,
            "output_root": self.output_root,
            "demand_path": self.demand_path,
            "target_paths": dict(self.target_paths),
            "fixture": bool(self.fixture),
            "build_timeout_seconds": float(self.build_timeout_seconds),
            "trend_timeout_seconds": float(self.trend_timeout_seconds),
            "max_rss_bytes": int(self.max_rss_bytes),
            "monitor_interval_seconds": float(self.monitor_interval_seconds),
            "command": list(self.command),
            "launcher_cwd": self.launcher_cwd,
            "fail_after_stage": self.fail_after_stage,
            "run_reserved": bool(self.run_reserved),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BuildSpec":
        return cls(
            run_id=str(payload["run_id"]),
            purpose=str(payload["purpose"]),
            repo_root=str(payload["repo_root"]),
            output_root=str(payload["output_root"]),
            demand_path=str(payload["demand_path"]),
            target_paths={
                str(name): str(path)
                for name, path in dict(payload["target_paths"]).items()
            },
            fixture=bool(payload["fixture"]),
            build_timeout_seconds=float(payload["build_timeout_seconds"]),
            trend_timeout_seconds=float(payload["trend_timeout_seconds"]),
            max_rss_bytes=int(payload["max_rss_bytes"]),
            monitor_interval_seconds=float(payload["monitor_interval_seconds"]),
            command=[str(value) for value in payload.get("command", [])],
            launcher_cwd=str(payload.get("launcher_cwd", "")),
            fail_after_stage=payload.get("fail_after_stage"),
            run_reserved=bool(payload.get("run_reserved", False)),
        )

    @property
    def run_directory(self) -> Path:
        return Path(self.output_root) / self.run_id

    def limits(self) -> Dict[str, Any]:
        return {
            "build_stage_timeout_seconds": float(self.build_timeout_seconds),
            "trend_stage_timeout_seconds": float(self.trend_timeout_seconds),
            "process_rss_limit_bytes": int(self.max_rss_bytes),
            "monitor_interval_seconds": float(self.monitor_interval_seconds),
            "timeout_scope": "separate construction and trend stage wall clocks",
            "rss_scope": "worker process lifetime, sampled; not an OS hard cap",
        }


def reserve_run_directory(spec: BuildSpec) -> artifacts.RunDirectory:
    """Reserve the exclusive output directory without the top-level status file."""
    run = artifacts.RunDirectory(
        Path(spec.output_root), spec.run_id, run_type="occupation-skill-graph-build"
    )
    run.root.mkdir(parents=True, exist_ok=True)
    try:
        run.path.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise artifacts.RunExistsError(
            "run directory already exists and will not be overwritten: "
            f"{run.path}"
        ) from exc
    run._created = True  # type: ignore[attr-defined]
    run.append_event("run_reserved", run_id=run.run_id, run_type=run.run_type)
    artifacts.write_status(
        run,
        "running",
        stage="starting",
        completed_stages=[],
        purpose=spec.purpose,
        fixture=spec.fixture,
    )
    return run


def _protocol_record() -> Dict[str, Any]:
    text = protocol.PROTOCOL_PATH.read_text(encoding="utf-8")
    return {
        "version": protocol.SCIENTIFIC_PROTOCOL_VERSION,
        "task_id": protocol.TASK_ID,
        "path": str(protocol.PROTOCOL_PATH),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "contents": text,
        "top_k": protocol.TOP_K,
        "min_positive_months": protocol.MIN_POSITIVE_MONTHS,
        "train_months": list(protocol.TRAIN_MONTHS),
    }


def _command_record(spec: BuildSpec) -> Dict[str, Any]:
    return {
        "schema": "occupation-skill-graph-command-v1",
        "argv": list(spec.command),
        "cwd": spec.launcher_cwd or str(Path.cwd()),
        "run_id": spec.run_id,
        "purpose": spec.purpose,
        "fixture": bool(spec.fixture),
        "output_root": spec.output_root,
        "demand_path": spec.demand_path,
        "target_paths": dict(spec.target_paths),
        "limits": spec.limits(),
        "created": artifacts.iso_now(),
    }


def _save_source_arrays(run: artifacts.RunDirectory, training: data.TrainingData) -> None:
    run.save_npy("artifacts/contexts.npy", training.contexts)
    run.save_npy("artifacts/skills.npy", training.skills)
    run.save_npy("artifacts/observations.npy", training.observations)
    run.save_npy("artifacts/x.npy", training.x)
    run.save_npy("artifacts/support.npy", training.support)
    run.save_npy("artifacts/profiles.npy", training.profiles)
    run.save_npy(
        "artifacts/occupational_support_counts.npy",
        training.occupational_support_counts,
    )
    run.write_json("artifacts/source.json", training.identity_payload())


def _save_candidate(
    run: artifacts.RunDirectory,
    graph: scores.CandidateGraph,
    candidate_structure: Mapping[str, Any],
    components: np.ndarray,
    graph_hashes: Mapping[str, str],
) -> None:
    arrays = dict(graph.arrays())
    arrays["components"] = components
    for name, value in arrays.items():
        run.save_npy(layout.candidate_array_path(graph.name, name), value)
    run.write_json(
        layout.candidate_json_path(graph.name, "structure.json"),
        candidate_structure,
    )
    run.write_json(
        layout.candidate_json_path(graph.name, "graph-hashes.json"),
        {"payload": dict(graph_hashes)},
    )


def _save_trends(
    run: artifacts.RunDirectory, result: trends.TrendResult
) -> None:
    for name, value in result.arrays().items():
        run.save_npy(f"artifacts/trends/{name}.npy", value)


def _union_edges(
    left: scores.CandidateGraph, right: scores.CandidateGraph
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    pairs = {
        tuple(int(value) for value in pair)
        for pair in left.edge_index.tolist()
    } | {
        tuple(int(value) for value in pair)
        for pair in right.edge_index.tolist()
    }
    ordered = sorted(pairs)
    if ordered:
        union = np.asarray(ordered, dtype=np.int64)
    else:
        union = np.empty((0, 2), dtype=np.int64)
    lookup = {pair: index for index, pair in enumerate(ordered)}
    positions = {
        graph.name: np.asarray(
            [
                lookup[tuple(int(value) for value in pair)]
                for pair in graph.edge_index.tolist()
            ],
            dtype=np.int64,
        )
        for graph in (left, right)
    }
    return union, positions


def _summary_text(report: Mapping[str, Any]) -> str:
    source = report["source"]
    lines = [
        "# Occupation-skill graph audit",
        "",
        f"- Protocol: `{report['protocol']['version']}`",
        f"- Run: `{report['run_id']}` ({report['purpose']})",
        f"- Fixture mode: `{report['fixture']}`",
        f"- Training months: {source['dimensions']['training_months']} "
        f"({protocol.TRAIN_MONTHS[0]}..{protocol.TRAIN_MONTHS[-1]})",
        f"- Occupations: {source['dimensions']['occupations']}",
        f"- Skills: {source['dimensions']['skills']}",
        f"- Top-k per candidate: {protocol.TOP_K}",
        "",
        "## Candidate structure",
        "",
        "| candidate | edges | isolated | components | max degree | boundary-tie nodes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name in protocol.CANDIDATES:
        candidate = report["candidates"][name]
        lines.append(
            f"| {name} | {candidate['post_sparsification']['edges']} | "
            f"{candidate['coverage']['all_source_skills']['isolated_nodes']} | "
            f"{candidate['components']['components']} | "
            f"{candidate['post_sparsification']['max_degree']} | "
            f"{candidate['cutoff_ties']['boundary_tie_nodes']} |"
        )
    overlap = report["candidate_overlap"]
    lines.extend(
        [
            "",
            f"Candidate edge overlap: {overlap['shared_edges']} shared of "
            f"{overlap['union_edges']} union edges "
            f"(Jaccard {overlap['jaccard']}).",
            "",
            "## Target mapping",
            "",
            "| target | contexts | skills | undirected edges per context |",
            "| --- | --- | --- | --- |",
        ]
    )
    for name in protocol.TARGET_DATA_NAMES:
        target = report["targets"][name]
        descriptor = target["mappings"]["jaccard"]["descriptor"]
        lines.append(
            f"| {name} | {target['contexts']} | {target['skills']} | "
            f"{descriptor['undirected_edges_per_context']} |"
        )
    lines.extend(
        [
            "",
            "## Trend diagnostics",
            "",
            "| candidate | eligible contexts | insufficient | constant | unknown edges |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for name in protocol.CANDIDATES:
        trend = report["trends"][name]
        lines.append(
            f"| {name} | {trend['eligible_context_count']} | "
            f"{trend['insufficient_context_count']} | "
            f"{trend['constant_context_count']} | {trend['unknown_edges']} |"
        )
    costs = report["costs"]
    lines.extend(
        [
            "",
            "## Costs and limits",
            "",
            f"- Stage seconds: {json.dumps(costs['stage_seconds'], sort_keys=True)}",
            f"- Peak RSS: {costs['peak_rss']['bytes']} bytes "
            f"({costs['peak_rss']['method']}; {costs['peak_rss']['scope']})",
            f"- Build stage timeout: {report['limits']['build_stage_timeout_seconds']} s",
            f"- Trend stage timeout: {report['limits']['trend_stage_timeout_seconds']} s",
            f"- Process RSS limit: {report['limits']['process_rss_limit_bytes']} bytes",
            "",
            "This is software evidence only. It does not freeze a graph, accept a "
            "scientific candidate, run prediction training or claim predictive "
            "benefit. Real published-data construction and research acceptance are "
            "separate research-side actions.",
            "",
        ]
    )
    return "\n".join(lines)


def execute_build(spec: BuildSpec) -> Dict[str, Any]:
    """Execute one build, preserving completed-stage evidence on failure."""
    if not spec.run_reserved:
        run = reserve_run_directory(spec)
    else:
        run = artifacts.RunDirectory(
            Path(spec.output_root),
            spec.run_id,
            run_type="occupation-skill-graph-build",
        )
        if not run.path.is_dir():
            raise BuildError(
                f"reserved run directory is missing: {run.path}"
            )
    run_path = run.path
    started = time.perf_counter()
    stage_seconds: Dict[str, float] = {}
    completed_stages: List[str] = []
    current_stage = "starting"
    stage_started_monotonic = started
    stage_started_epoch = time.time()
    stage_start_epochs: Dict[str, float] = {}
    training: Optional[data.TrainingData] = None
    targets: Dict[str, data.TargetKeyData] = {}
    graphs: Dict[str, scores.CandidateGraph] = {}
    structures: Dict[str, Dict[str, Any]] = {}
    graph_hashes: Dict[str, Dict[str, str]] = {}
    overlap: Dict[str, Any] = {}
    trend_result: Optional[trends.TrendResult] = None
    trend_positions: Dict[str, np.ndarray] = {}
    trend_summaries: Dict[str, Dict[str, Any]] = {}
    source_record: Dict[str, Any] = {}
    environment: Dict[str, Any] = {}
    protocol_record = _protocol_record()
    command_record = _command_record(spec)

    def update(stage: str, completed: int, total: Optional[int], **extra: Any) -> None:
        artifacts.write_progress(
            run,
            stage=stage,
            completed=completed,
            total=total,
            stage_elapsed_seconds=time.perf_counter() - stage_started_monotonic,
            stage_started_epoch=stage_started_epoch,
            completed_stages=completed_stages,
            **extra,
        )

    def begin_stage(stage: str) -> None:
        nonlocal current_stage, stage_started_monotonic, stage_started_epoch
        current_stage = stage
        stage_started_monotonic = time.perf_counter()
        stage_started_epoch = time.time()
        stage_start_epochs[stage] = stage_started_epoch
        update(stage, 0, None)

    def end_stage(stage: str) -> None:
        nonlocal stage_seconds
        stage_seconds[stage] = time.perf_counter() - stage_started_monotonic
        completed_stages.append(stage)
        update(stage, 1, 1, stage_seconds=stage_seconds[stage])

    def maybe_inject(stage: str) -> None:
        if spec.fail_after_stage == stage:
            raise InjectedFailure(
                f"injected failure after completed stage {stage!r}"
            )

    def base_provenance() -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "schema": "occupation-skill-graph-provenance-v1",
            "created": artifacts.iso_now(),
            "run_id": spec.run_id,
            "purpose": spec.purpose,
            "fixture": bool(spec.fixture),
            "protocol": {
                key: value
                for key, value in protocol_record.items()
                if key != "contents"
            },
            "command": command_record,
            "limits": spec.limits(),
            "code_source": source_record,
            "environment": environment,
            "source": None,
            "targets": {},
            "software_scope": (
                "P02-T009 software evidence only; no research acceptance, graph "
                "freeze, dataset change or prediction training"
            ),
        }
        if training is not None:
            payload["source"] = training.identity_payload()
        if targets:
            payload["targets"] = {
                name: target.identity_payload() for name, target in targets.items()
            }
        return payload

    try:
        # Durable identity records are written before the expensive stages so a
        # later failure still leaves command/protocol/code evidence on disk.
        run.write_json(protocol.COMMAND_FILE, command_record)
        run.write_text(protocol.PROTOCOL_SNAPSHOT, protocol_record["contents"])
        source_record = artifacts.capture_source(run, Path(spec.repo_root))
        environment = artifacts.capture_environment(Path(spec.repo_root))
        artifacts.write_environment_snapshot(run, environment)
        run.write_json(protocol.PROVENANCE_FILE, base_provenance())

        begin_stage("source")
        training = data.load_training(Path(spec.demand_path), fixture=spec.fixture)
        _save_source_arrays(run, training)
        end_stage("source")
        maybe_inject("source")

        begin_stage("construct")
        for name in protocol.CANDIDATES:
            graph = scores.compute_candidate(
                name,
                training.x,
                training.support,
                progress=lambda stage, completed, total, candidate=name: update(
                    stage, completed, total, candidate=candidate
                ),
            )
            candidate_structure, components = structure.candidate_structure(
                graph, training
            )
            graphs[name] = graph
            structures[name] = candidate_structure
            graph_hashes[name] = graph.identity_hashes()
            _save_candidate(
                run,
                graph,
                candidate_structure,
                components,
                graph_hashes[name],
            )
        overlap = structure.candidate_overlap(graphs["jaccard"], graphs["cosine"])
        run.write_json(layout.CANDIDATE_OVERLAP_FILE, overlap)
        end_stage("construct")
        maybe_inject("construct")

        begin_stage("targets")
        for name in protocol.TARGET_DATA_NAMES:
            target = data.load_target_keys(
                name, Path(spec.target_paths[name]), fixture=spec.fixture
            )
            population = mapping.validate_target_population(target, training.skills)
            run.save_npy(layout.target_array_path(name, "keys"), target.key_array)
            run.save_npy(layout.target_array_path(name, "contexts"), target.contexts)
            run.save_npy(layout.target_array_path(name, "skills"), target.skills)
            run.write_json(
                layout.target_json_path(name, "population.json"), population
            )
            for candidate_name in protocol.CANDIDATES:
                graph = graphs[candidate_name]
                descriptor = mapping.mapping_descriptor(
                    target, graph.edge_index, graph.edge_score
                )
                run.write_json(
                    layout.target_json_path(
                        name, f"mapping_{candidate_name}.json"
                    ),
                    descriptor,
                )
            # Verify the lazy expansion preserves exact edge/score identity for
            # every context without materialising duplicated edge storage.
            for candidate_name in protocol.CANDIDATES:
                candidate_graph = graphs[candidate_name]
                for context in mapping.iter_context_edges(
                    target,
                    candidate_graph.edge_index,
                    candidate_graph.edge_score,
                ):
                    if context.undirected_edges != candidate_graph.n_edges:
                        raise mapping.MappingError(
                            f"target {name}: lazily expanded edge count differs "
                            f"for {candidate_name}"
                        )
            targets[name] = target
        end_stage("targets")
        maybe_inject("targets")

        begin_stage("trends")
        union_edges, trend_positions = _union_edges(
            graphs["jaccard"], graphs["cosine"]
        )
        before_hashes = {
            name: graph.identity_hashes() for name, graph in graphs.items()
        }
        if before_hashes != graph_hashes:
            raise BuildError("graph payload changed before trend diagnostics")
        trend_result = trends.compute_trends(
            training.observations,
            union_edges,
            progress=lambda stage, completed, total: update(stage, completed, total),
        )
        after_hashes = {
            name: graph.identity_hashes() for name, graph in graphs.items()
        }
        if after_hashes != before_hashes:
            raise BuildError(
                "trend diagnostics changed graph bytes; refusing to publish"
            )
        _save_trends(run, trend_result)
        run.write_json(
            "artifacts/trends/global.json", trend_result.global_summary
        )
        for name in protocol.CANDIDATES:
            summary = trends.candidate_trend_summary(
                trend_result, trend_positions[name], name
            )
            trend_summaries[name] = summary
            run.write_json(f"artifacts/trends/{name}.json", summary)
        end_stage("trends")
        maybe_inject("trends")

        begin_stage("finalize")
        peak_rss = artifacts.measure_peak_rss()
        costs = {
            "stage_seconds": {
                stage: float(value)
                for stage, value in stage_seconds.items()
                if stage != "finalize"
            },
            "construction_seconds": float(stage_seconds.get("construct", 0.0)),
            "mapping_seconds": float(stage_seconds.get("targets", 0.0)),
            "trend_seconds": float(stage_seconds.get("trends", 0.0)),
            "source_load_seconds": float(stage_seconds.get("source", 0.0)),
            "peak_rss": peak_rss,
            "process_rss_limit_bytes": int(spec.max_rss_bytes),
            "monitor_interval_seconds": float(spec.monitor_interval_seconds),
            "dimensions": {
                "occupations": training.n_contexts,
                "skills": training.n_skills,
                "training_months": training.n_months,
                "union_edges": int(trend_result.n_edges),
                "jaccard_edges": int(graphs["jaccard"].n_edges),
                "cosine_edges": int(graphs["cosine"].n_edges),
            },
            "blocks": {
                "score_block_size": protocol.SCORE_BLOCK_SIZE,
                "trend_block_size": protocol.TREND_BLOCK_SIZE,
            },
        }
        report: Dict[str, Any] = {
            "schema": protocol.REPORT_VERSION,
            "status": "succeeded",
            "terminal_state": "succeeded",
            "created": artifacts.iso_now(),
            "run_id": spec.run_id,
            "purpose": spec.purpose,
            "fixture": bool(spec.fixture),
            "protocol": {
                key: value
                for key, value in protocol_record.items()
                if key != "contents"
            },
            "command": command_record,
            "source": training.identity_payload(),
            "dimensions": costs["dimensions"],
            "candidates": structures,
            "candidate_overlap": overlap,
            "targets": {
                name: {
                    "identity": target.identity,
                    "key_columns": list(target.key_columns),
                    "source_path": target.source_path,
                    "source_file_sha256": target.source_sha256,
                    "contexts": target.n_contexts,
                    "skills": target.n_skills,
                    "population": mapping.validate_target_population(
                        target, training.skills
                    ),
                    "mappings": {
                        candidate_name: {
                            "descriptor": mapping.mapping_descriptor(
                                target,
                                graphs[candidate_name].edge_index,
                                graphs[candidate_name].edge_score,
                            )
                        }
                        for candidate_name in protocol.CANDIDATES
                    },
                }
                for name, target in targets.items()
            },
            "trends": {
                **trend_summaries,
                "global": trend_result.global_summary,
                "union_edges": int(trend_result.n_edges),
                "graph_bytes_unchanged_by_diagnostics": True,
            },
            "graph_bytes_unchanged_by_diagnostics": True,
            "costs": costs,
            "limits": spec.limits(),
            "software_scope": (
                "fixture/software evidence only; not research acceptance, graph "
                "freezing, prediction training or predictive-benefit evidence"
            ),
            "research_acceptance_performed": False,
            "graph_frozen": False,
            "predictive_benefit_claimed": False,
        }
        run.write_json(protocol.REPORT_FILE, report)
        run.write_text(protocol.SUMMARY_FILE, _summary_text(report))
        run.write_json(protocol.PROVENANCE_FILE, base_provenance())
        manifest = artifacts.finalize_manifest(run)
        stage_seconds["total"] = time.perf_counter() - started
        artifacts.write_status(
            run,
            "succeeded",
            stage="finalize",
            completed_stages=completed_stages,
            stage_seconds=stage_seconds,
            report=protocol.REPORT_FILE,
            manifest=protocol.MANIFEST_FILE,
            artifact_count=len(manifest["files"]),
        )
        return {
            "status": "succeeded",
            "run_id": spec.run_id,
            "run_dir": str(run_path),
            "report_path": str(run_path / protocol.REPORT_FILE),
            "manifest_path": str(run_path / protocol.MANIFEST_FILE),
            "status_path": str(run_path / protocol.STATUS_FILE),
        }
    except RunInterrupted as exc:
        artifacts.write_status(
            run,
            "interrupted",
            stage=current_stage,
            completed_stages=completed_stages,
            error={"type": type(exc).__name__, "message": str(exc)},
            stage_seconds=stage_seconds,
        )
        raise
    except BaseException as exc:
        artifacts.write_status(
            run,
            "failed",
            stage=current_stage,
            completed_stages=completed_stages,
            error={"type": type(exc).__name__, "message": str(exc)},
            stage_seconds=stage_seconds,
        )
        if training is not None:
            try:
                run.write_json(protocol.PROVENANCE_FILE, base_provenance())
            except Exception:  # pragma: no cover - preserve original failure
                pass
        raise
