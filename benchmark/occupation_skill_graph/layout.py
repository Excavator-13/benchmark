"""Readable artifact layout used by both the builder and the saved-only checker."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from . import protocol

__all__ = [
    "SOURCE_ARRAY_FILES",
    "SOURCE_JSON_FILES",
    "CANDIDATE_ARRAY_NAMES",
    "CANDIDATE_JSON_NAMES",
    "TREND_ARRAY_NAMES",
    "TREND_JSON_NAMES",
    "candidate_array_path",
    "candidate_json_path",
    "target_array_path",
    "target_json_path",
    "source_required_files",
    "candidate_required_files",
    "target_required_files",
    "trend_required_files",
    "required_payload_files",
    "PAYLOAD_ARRAY_DTYPES",
]

SOURCE_ARRAY_FILES: Tuple[str, ...] = (
    "artifacts/contexts.npy",
    "artifacts/skills.npy",
    "artifacts/observations.npy",
    "artifacts/x.npy",
    "artifacts/support.npy",
    "artifacts/profiles.npy",
    "artifacts/occupational_support_counts.npy",
)
SOURCE_JSON_FILES: Tuple[str, ...] = (
    "artifacts/source.json",
)

CANDIDATE_ARRAY_NAMES: Tuple[str, ...] = (
    "selection_index",
    "selection_score",
    "cutoff_score",
    "cutoff_tied_candidates",
    "boundary_tie",
    "edge_index",
    "edge_score",
    "edge_direction",
    "degree",
    "components",
)
CANDIDATE_JSON_NAMES: Tuple[str, ...] = (
    "structure.json",
    "graph-hashes.json",
)

TREND_ARRAY_NAMES: Tuple[str, ...] = (
    "trend_edge_index",
    "trend_eligible_counts",
    "trend_insufficient_counts",
    "trend_constant_counts",
    "trend_reason_codes",
    "trend_positive_counts",
    "trend_zero_counts",
    "trend_negative_counts",
    "trend_common_zero_months",
    "trend_common_zero_fraction",
    "trend_mean_context_common_zero_fraction",
    "trend_correlation_min",
    "trend_correlation_max",
    "trend_correlation_mean",
    "trend_correlation_median",
    "trend_correlation_std",
)
TREND_JSON_NAMES: Tuple[str, ...] = (
    "artifacts/trends/global.json",
    "artifacts/trends/jaccard.json",
    "artifacts/trends/cosine.json",
)
CANDIDATE_OVERLAP_FILE = "artifacts/candidate-overlap.json"

PAYLOAD_ARRAY_DTYPES: Dict[str, str] = {
    "artifacts/contexts.npy": "int64",
    "artifacts/skills.npy": "int64",
    "artifacts/observations.npy": "float64",
    "artifacts/x.npy": "float64",
    "artifacts/support.npy": "bool",
    "artifacts/profiles.npy": "float64",
    "artifacts/occupational_support_counts.npy": "int64",
}


def candidate_array_path(name: str, key: str) -> str:
    return f"artifacts/candidates/{name}/{key}.npy"


def candidate_json_path(name: str, key: str) -> str:
    return f"artifacts/candidates/{name}/{key}"


def target_array_path(name: str, key: str) -> str:
    return f"artifacts/targets/{name}/{key}.npy"


def target_json_path(name: str, key: str) -> str:
    return f"artifacts/targets/{name}/{key}.json"


def source_required_files() -> List[str]:
    return list(SOURCE_ARRAY_FILES) + list(SOURCE_JSON_FILES)


def candidate_required_files(name: str) -> List[str]:
    return [
        candidate_array_path(name, key) for key in CANDIDATE_ARRAY_NAMES
    ] + [candidate_json_path(name, key) for key in CANDIDATE_JSON_NAMES]


def target_required_files(name: str) -> List[str]:
    return [
        target_array_path(name, key) for key in ("keys", "contexts", "skills")
    ] + [
        target_json_path(name, key)
        for key in ("population.json", "mapping_jaccard.json", "mapping_cosine.json")
    ]


def trend_required_files() -> List[str]:
    return [
        f"artifacts/trends/{key}.npy" for key in TREND_ARRAY_NAMES
    ] + list(TREND_JSON_NAMES)


def required_payload_files() -> List[str]:
    files = source_required_files() + trend_required_files() + [CANDIDATE_OVERLAP_FILE]
    for name in protocol.CANDIDATES:
        files.extend(candidate_required_files(name))
    for name in protocol.TARGET_DATA_NAMES:
        files.extend(target_required_files(name))
    return files
