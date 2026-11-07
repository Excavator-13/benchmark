"""Deterministic small Parquet fixtures for the occupation-skill graph tests.

Fixtures use real Parquet files with all 36 source month columns, non-dense
numeric contexts and skills, and deliberately unread held-out values so the
loader is exercised through the same path as published data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

from benchmark.occupation_skill_graph import data as osg_data
from benchmark.occupation_skill_graph import protocol

DEFAULT_CONTEXTS: Tuple[int, ...] = (2, 5)
DEFAULT_SKILLS: Tuple[int, ...] = (1, 4, 7, 10)


def canonical_observations(
    contexts: Sequence[int] = DEFAULT_CONTEXTS,
    skills: Sequence[int] = DEFAULT_SKILLS,
) -> np.ndarray:
    """Return a deterministic ``[C, S, 27]`` fixture with varied structure."""
    context_values = sorted(int(value) for value in contexts)
    skill_values = sorted(int(value) for value in skills)
    observations = np.zeros(
        (len(context_values), len(skill_values), protocol.N_TRAIN_MONTHS),
        dtype=np.float64,
    )
    for skill_index in range(len(skill_values)):
        base = np.linspace(1.0, 10.0 + skill_index, protocol.N_TRAIN_MONTHS)
        observations[0, skill_index, :] = base
        observations[1, skill_index, :] = base[::-1]
    # A zero-demand skill and a sparse-history skill exercise both candidate
    # zero handling and the trend history rule.
    if len(skill_values) >= 3:
        observations[:, 2, :] = 0.0
    if len(skill_values) >= 4:
        observations[0, 3, :5] = 4.0
        observations[1, 3, :] = 6.0
    return observations


def write_demand_table(
    path: Path,
    data_name: str,
    contexts: Sequence[int],
    skills: Sequence[int],
    observations: np.ndarray,
    *,
    held_out_value: float = float("nan"),
    row_order_seed: Optional[int] = None,
    extra_value_column: bool = False,
) -> Path:
    """Write a full 36-month demand table, keeping held-out values unread."""
    import pandas as pd

    context_values = list(contexts)
    skill_values = list(skills)
    values = np.asarray(observations, dtype=np.float64)
    if values.shape != (
        len(context_values),
        len(skill_values),
        protocol.N_TRAIN_MONTHS,
    ):
        raise ValueError("observations shape does not match the identity grid")
    key_columns = list(protocol.TARGET_KEY_COLUMNS[data_name])
    rows: list[dict[str, Any]] = []
    for context_index, context in enumerate(context_values):
        for skill_index, skill in enumerate(skill_values):
            row: Dict[str, Any] = {key_columns[0]: context, "skill_id": skill}
            for month_index, month in enumerate(protocol.MONTHS):
                if month_index < protocol.N_TRAIN_MONTHS:
                    row[month] = float(values[context_index, skill_index, month_index])
                else:
                    row[month] = float(held_out_value)
            if extra_value_column:
                row["target_demand_value"] = float("nan")
            rows.append(row)
    frame = pd.DataFrame(rows)
    if row_order_seed is not None:
        frame = frame.sample(frac=1.0, random_state=row_order_seed).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def write_target_table(
    path: Path,
    data_name: str,
    contexts: Sequence[int],
    skills: Sequence[int],
    *,
    row_order_seed: Optional[int] = None,
    include_value_columns: bool = True,
) -> Path:
    """Write identity keys plus deliberately unusable target value columns."""
    import pandas as pd

    key_columns = list(protocol.TARGET_KEY_COLUMNS[data_name])
    rows: list[dict[str, Any]] = []
    for context in contexts:
        for skill in skills:
            row: Dict[str, Any] = {key_columns[0]: context, "skill_id": skill}
            if include_value_columns:
                for month in protocol.MONTHS:
                    row[month] = float("nan")
                row["target_demand_value"] = -1.0
            rows.append(row)
    frame = pd.DataFrame(rows)
    if row_order_seed is not None:
        frame = frame.sample(frac=1.0, random_state=row_order_seed).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path


def standard_fixture(
    root: Path,
    *,
    contexts: Sequence[int] = DEFAULT_CONTEXTS,
    skills: Sequence[int] = DEFAULT_SKILLS,
    observations: Optional[np.ndarray] = None,
    row_order_seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Write one source plus three target key tables under ``root``."""
    values = (
        canonical_observations(contexts, skills)
        if observations is None
        else np.asarray(observations, dtype=np.float64)
    )
    source = write_demand_table(
        root / "r2-source.parquet",
        "r2",
        contexts,
        skills,
        values,
        row_order_seed=row_order_seed,
    )
    targets = {
        "r0": write_target_table(
            root / "r0-target.parquet", "r0", [contexts[0]], skills
        ),
        "region": write_target_table(
            root / "region-target.parquet", "region", [0, 4], skills
        ),
        "r2": write_target_table(
            root / "r2-target.parquet", "r2", contexts, skills
        ),
    }
    return {
        "contexts": list(contexts),
        "skills": list(skills),
        "observations": values,
        "source_path": source,
        "target_paths": targets,
    }


def training_fixture(
    contexts: Sequence[int] = DEFAULT_CONTEXTS,
    skills: Sequence[int] = DEFAULT_SKILLS,
    observations: Optional[np.ndarray] = None,
) -> osg_data.TrainingData:
    values = (
        canonical_observations(contexts, skills)
        if observations is None
        else np.asarray(observations, dtype=np.float64)
    )
    return osg_data.training_from_arrays(contexts, skills, values)


def target_fixture(
    data_name: str,
    contexts: Sequence[int],
    skills: Sequence[int],
) -> osg_data.TargetKeyData:
    return osg_data.target_keys_from_arrays(data_name, contexts, skills)


def build_spec(
    root: Path,
    *,
    fixture: Dict[str, Any],
    run_id: str = "fixture-run",
    output_root: Optional[Path] = None,
    purpose: str = "development",
    fail_after_stage: Optional[str] = None,
    build_timeout_seconds: float = protocol.DEFAULT_STAGE_TIMEOUT_SECONDS,
    trend_timeout_seconds: float = protocol.DEFAULT_STAGE_TIMEOUT_SECONDS,
    max_rss_bytes: int = protocol.DEFAULT_MAX_RSS_BYTES,
    monitor_interval_seconds: float = protocol.DEFAULT_MONITOR_INTERVAL_SECONDS,
) -> Any:
    from benchmark.occupation_skill_graph.runner import BuildSpec

    return BuildSpec(
        run_id=run_id,
        purpose=purpose,
        repo_root=str(root),
        output_root=str(output_root if output_root is not None else root / "output"),
        demand_path=str(fixture["source_path"]),
        target_paths={
            name: str(path) for name, path in fixture["target_paths"].items()
        },
        fixture=True,
        fail_after_stage=fail_after_stage,
        build_timeout_seconds=build_timeout_seconds,
        trend_timeout_seconds=trend_timeout_seconds,
        max_rss_bytes=max_rss_bytes,
        monitor_interval_seconds=monitor_interval_seconds,
        command=["fixture-build"],
        launcher_cwd=str(root),
    )
