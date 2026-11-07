"""Fixed constants for ``P2-occupation-skill-graph-v1`` (P02-T009).

Everything scientific in this package derives from this module.  The values are
copied from ``research/phases/P02/t009-graph-protocol.md``; the protocol file
itself is snapshotted into every successful run rather than re-interpreted here.

The package reuses the canonical month labels, context key columns and key
ordering conventions of the unchanged ``P1-count-L6-H3-v3`` entry.  It never
routes source counts through that entry's ``float32`` demand loader.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping, Tuple

from benchmark.nograph_baseline import protocol as p01

__all__ = [
    "TASK_ID",
    "SCIENTIFIC_PROTOCOL_VERSION",
    "REPORT_VERSION",
    "CHECK_REPORT_VERSION",
    "SCIENTIFIC_SCHEMA",
    "SOURCE_DATA_NAME",
    "MODE",
    "N_MONTHS",
    "N_TRAIN_MONTHS",
    "MONTHS",
    "TRAIN_MONTHS",
    "MONTH_COLUMN_PATTERN",
    "EXPECTED_OCCUPATION_IDS",
    "EXPECTED_SKILL_IDS",
    "EXPECTED_NODES",
    "SOURCE_KEY_COLUMNS",
    "TARGET_DATA_NAMES",
    "TARGET_KEY_COLUMNS",
    "CANDIDATES",
    "TOP_K",
    "SCORE_BLOCK_SIZE",
    "TREND_BLOCK_SIZE",
    "MIN_POSITIVE_MONTHS",
    "FIRST_DIFFERENCE_LENGTH",
    "DEFAULT_STAGE_TIMEOUT_SECONDS",
    "DEFAULT_MAX_RSS_BYTES",
    "DEFAULT_MONITOR_INTERVAL_SECONDS",
    "PURPOSES",
    "DEVELOPMENT_PURPOSE",
    "RESEARCH_PURPOSE",
    "MODULE_DIR",
    "REPO_ROOT",
    "DATASET_DIR",
    "DEMAND_DIR",
    "PROTOCOL_PATH",
    "DEVELOPMENT_ROOT",
    "RESEARCH_RUNS_ROOT",
    "ARTIFACT_DIR",
    "STATUS_FILE",
    "PROGRESS_FILE",
    "MANIFEST_FILE",
    "REPORT_FILE",
    "COMMAND_FILE",
    "PROVENANCE_FILE",
    "SUMMARY_FILE",
    "PROTOCOL_SNAPSHOT",
    "REQUIRED_TOP_LEVEL_FILES",
    "validate_protocol_version",
    "validate_scope",
    "demand_path",
    "target_demand_path",
    "node_key_columns",
    "candidate_names",
]

TASK_ID = "P02-T009"
SCIENTIFIC_PROTOCOL_VERSION = "P2-occupation-skill-graph-v1"
SCIENTIFIC_SCHEMA = "P2-occupation-skill-graph-v1"
REPORT_VERSION = "occupation-skill-graph-report-v1"
CHECK_REPORT_VERSION = "occupation-skill-graph-check-v1"

#: The only implemented source.  The mode is the unchanged ``count`` mode.
SOURCE_DATA_NAME = "r2"
MODE = "count"

N_MONTHS = p01.N_MONTHS
N_TRAIN_MONTHS = p01.TRAIN_OBSERVATION_MONTH_COUNT
MONTHS: Tuple[str, ...] = tuple(p01.MONTHS)
TRAIN_MONTHS: Tuple[str, ...] = tuple(p01.TRAIN_OBSERVATION_MONTHS)
MONTH_COLUMN_PATTERN = re.compile(r"^\d{4}-\d{2}$")

EXPECTED_OCCUPATION_IDS: Tuple[int, ...] = tuple(range(52))
EXPECTED_SKILL_IDS: Tuple[int, ...] = tuple(range(2335))
EXPECTED_NODES = len(EXPECTED_OCCUPATION_IDS) * len(EXPECTED_SKILL_IDS)

SOURCE_KEY_COLUMNS: Tuple[str, ...] = p01.node_key_columns(SOURCE_DATA_NAME)
TARGET_DATA_NAMES: Tuple[str, ...] = ("r0", "region", "r2")
TARGET_KEY_COLUMNS: Mapping[str, Tuple[str, ...]] = {
    name: p01.node_key_columns(name) for name in TARGET_DATA_NAMES
}

#: Fixed first-batch candidate names and execution settings.
CANDIDATES: Tuple[str, ...] = ("jaccard", "cosine")
TOP_K = 10
SCORE_BLOCK_SIZE = 256
TREND_BLOCK_SIZE = 512
MIN_POSITIVE_MONTHS = 12
FIRST_DIFFERENCE_LENGTH = N_TRAIN_MONTHS - 1

DEFAULT_STAGE_TIMEOUT_SECONDS = 30 * 60.0
DEFAULT_MAX_RSS_BYTES = 2 * 1024**3
DEFAULT_MONITOR_INTERVAL_SECONDS = 0.25

PURPOSES: Tuple[str, ...] = ("development", "research")
DEVELOPMENT_PURPOSE = "development"
RESEARCH_PURPOSE = "research"

MODULE_DIR = Path(__file__).resolve().parent
REPO_ROOT = MODULE_DIR.parents[1]
DATASET_DIR = REPO_ROOT / "dataset"
DEMAND_DIR = DATASET_DIR / "demand"
PROTOCOL_PATH = REPO_ROOT / "research" / "phases" / "P02" / "t009-graph-protocol.md"
DEVELOPMENT_ROOT = REPO_ROOT / "scratch" / "occupation-skill-graph"
RESEARCH_RUNS_ROOT = REPO_ROOT / "research" / "runs"

ARTIFACT_DIR = "artifacts"
STATUS_FILE = "artifacts/status.json"
PROGRESS_FILE = "artifacts/progress.json"
MANIFEST_FILE = "artifacts-sha256.json"
REPORT_FILE = "report.json"
COMMAND_FILE = "command.json"
PROVENANCE_FILE = "provenance.json"
SUMMARY_FILE = "summary.md"
PROTOCOL_SNAPSHOT = "protocol.md"

REQUIRED_TOP_LEVEL_FILES: Tuple[str, ...] = (
    COMMAND_FILE,
    PROVENANCE_FILE,
    REPORT_FILE,
    SUMMARY_FILE,
    PROTOCOL_SNAPSHOT,
    MANIFEST_FILE,
    STATUS_FILE,
)


class ProtocolError(ValueError):
    """Raised when a request or artifact violates the fixed protocol."""


def validate_protocol_version(version: str) -> str:
    """Reject any protocol version other than the fixed one."""
    if version != SCIENTIFIC_PROTOCOL_VERSION:
        raise ProtocolError(
            f"unsupported protocol version {version!r}; "
            f"expected {SCIENTIFIC_PROTOCOL_VERSION!r}"
        )
    return version


def validate_scope(
    *,
    source: str = SOURCE_DATA_NAME,
    mode: str = MODE,
    fold: str | None = None,
    protocol_version: str = SCIENTIFIC_PROTOCOL_VERSION,
) -> None:
    """Reject unsupported sources, modes, folds and protocol versions."""
    if source != SOURCE_DATA_NAME:
        raise ProtocolError(
            f"unsupported source {source!r}; this protocol builds from "
            f"{SOURCE_DATA_NAME!r} only"
        )
    if mode != MODE:
        raise ProtocolError(
            f"unsupported mode {mode!r}; this protocol implements {MODE!r} only"
        )
    if fold is not None:
        raise ProtocolError(
            f"unsupported fold {fold!r}; backtest refitting is outside "
            f"{SCIENTIFIC_PROTOCOL_VERSION}"
        )
    validate_protocol_version(protocol_version)


def node_key_columns(data_name: str) -> Tuple[str, ...]:
    """Return canonical key columns for a supported target/source name."""
    if data_name not in TARGET_DATA_NAMES:
        raise ProtocolError(
            f"unsupported data name {data_name!r}; supported: "
            f"{list(TARGET_DATA_NAMES)}"
        )
    return TARGET_KEY_COLUMNS[data_name]


def demand_path(data_name: str = SOURCE_DATA_NAME) -> Path:
    """Default published demand Parquet path for a data name."""
    node_key_columns(data_name)
    return DEMAND_DIR / f"{data_name}.parquet"


def target_demand_path(data_name: str) -> Path:
    """Default published target demand Parquet path."""
    return demand_path(data_name)


def candidate_names() -> Tuple[str, ...]:
    """Return the fixed candidate names in reporting order."""
    return CANDIDATES
