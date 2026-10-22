"""Saved-only checks: read-only recomputation, repeat comparison, shuffle summary.

None of these commands reads source demand/graph data, trains a model or calls a
model forward pass.  Each writes exactly one exclusive JSON report under the
ignored scratch tree or a validated temporary root, carrying the exact command,
checker source identity, input identities, tolerances, status and decisive
differences.  Input files are hashed before and after every check and must stay
bytewise unchanged.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from benchmark.nograph_baseline import artifacts as nb_artifacts
from benchmark.nograph_baseline import checks as nb_checks
from benchmark.nograph_baseline import metrics as p01_metrics
from benchmark.nograph_baseline import protocol as p01
from benchmark.nograph_baseline.data import sha256_file

from . import artifacts, config as gvs_config, graph as gvs_graph, protocol
from . import shuffle as gvs_shuffle

__all__ = [
    "CheckError",
    "RECOMPUTE_TOLERANCES",
    "COMPARE_TOLERANCES",
    "validate_report_destination",
    "recompute_run",
    "command_recompute",
    "command_compare",
    "command_summarize_shuffled",
    "normalized_difference",
    "REPORT_VERSION",
]

REPORT_VERSION = 1
CPU_RELATIVE_TOLERANCE = 1e-6
DIAGNOSTIC_RELATIVE_TOLERANCE = 1e-12
RECOMPUTE_TOLERANCES = {
    "numeric": DIAGNOSTIC_RELATIVE_TOLERANCE,
    "formula": "abs(a-b)/max(1,abs(a),abs(b))",
    "non_numeric": "exact (keys, schema, dtype, shape, masks, null status, counts)",
}
COMPARE_TOLERANCES = {
    "MAE_normalized": CPU_RELATIVE_TOLERANCE,
    "elementwise_prediction_normalized": CPU_RELATIVE_TOLERANCE,
    "other_error_metrics_normalized": CPU_RELATIVE_TOLERANCE,
    "derived_sums": (
        "absolute/squared error sums and contribution fractions are derived "
        "from the compared error metrics and exactly-compared element counts"
    ),
    "formula": "abs(a-b)/max(1,abs(a),abs(b))",
    "identity_conditions": "exact",
}

normalized_difference = nb_checks.normalized_difference
_METADATA_KEYS = frozenset(
    {
        "method",
        "split",
        "dataset",
        "nonself_neighbor_coverage_source",
        "evidence_role",
    }
)
#: Raw error sums and their contribution fractions are exact functions of the
#: reported MSE/MAE and the exactly-compared element counts, so repeat
#: comparison checks the error metrics themselves rather than re-testing derived
#: accumulators whose near-zero group values could amplify a tolerated
#: prediction difference.  Recomputation still compares every stored aggregate.
_COMPARE_DERIVED_KEYS = frozenset(
    {
        "absolute_error_sum",
        "squared_error_sum",
        "absolute_error_contribution_fraction",
        "squared_error_contribution_fraction",
    }
)
_COMPARE_IGNORED_KEYS = _METADATA_KEYS | _COMPARE_DERIVED_KEYS
_GOLD_SHAPES = {"validation": 1, "test": 4}
_EXPECTED_MASK_KEYS = {
    "nonzero_activity_train27",
    "constant_train27",
    "activity_inactive",
    "activity_low",
    "activity_medium",
    "activity_high",
    "has_nonself_neighbor",
}
_COUNT_KEYS = {
    "parameter_count_gru",
    "parameter_count_head",
    "parameter_count_graph_only",
    "parameter_count_total",
    "parameter_names",
    "named_tensor_map",
}


class CheckError(RuntimeError):
    """Raised when a saved-run check cannot be completed."""


# ---------------------------------------------------------------------------
# report destination policy
# ---------------------------------------------------------------------------
def validate_report_destination(
    repo_root: Path, destination: Path, inputs: Sequence[Path] = ()
) -> Path:
    """Require one fresh report path under ignored scratch or the temp root."""
    destination = Path(destination).expanduser()
    if destination.exists() or destination.is_symlink():
        raise CheckError(
            "report destination already exists and will not be replaced: "
            f"{destination}"
        )
    try:
        repo_root = gvs_config.validate_implementation_root(Path(repo_root))
    except gvs_config.ConfigError as exc:
        raise CheckError(str(exc)) from exc
    resolved = destination.resolve()
    # Eligibility is anchored to the authoritative ignored scratch tree and the
    # system temporary directory, never to a scratch directory implied by an
    # arbitrary repository-root override.
    allowed = [
        gvs_config.authoritative_scratch_root().resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ]
    if not any(nb_artifacts.is_within(resolved, root) for root in allowed):
        raise CheckError(
            "check reports must be written under the ignored scratch tree or a "
            f"validated temporary root; got {destination} -> {resolved}"
        )
    # Authoritative project protections are applied independently of any
    # user-supplied repository-root rebasing.
    protected = [
        Path(repo_root) / "research",
        Path(repo_root) / "experiments_archive",
        *gvs_config.protected_project_roots(),
    ]
    for root in protected:
        if nb_artifacts.is_within(resolved, root):
            raise CheckError(
                f"check reports may not be written inside protected project "
                f"records or source: {resolved}"
            )
    for input_path in inputs:
        input_path = Path(input_path)
        if not input_path.exists():
            continue
        resolved_input = input_path.resolve()
        if resolved == resolved_input:
            raise CheckError(
                f"report destination {destination} resolves to an input path"
            )
        if resolved_input.is_dir() and nb_artifacts.is_within(resolved, resolved_input):
            raise CheckError(
                f"report destination {destination} resolves inside the input "
                f"directory {input_path}"
            )
    return destination


def _write_report(destination: Path, envelope: Mapping[str, Any]) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(envelope), indent=2, sort_keys=True, ensure_ascii=False)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        descriptor = os.open(destination, flags, 0o644)
    except FileExistsError as exc:
        raise CheckError(
            "report destination already exists and will not be replaced: "
            f"{destination}"
        ) from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.unlink(destination)
        except OSError:  # pragma: no cover - best-effort cleanup
            pass
        raise
    return destination


def _envelope(
    kind: str,
    *,
    command: Sequence[str],
    repo_root: Path,
    inputs: Mapping[str, Any],
    tolerances: Mapping[str, Any],
    status: str,
    result: Mapping[str, Any],
    errors: Sequence[Any],
) -> Dict[str, Any]:
    return {
        "version": REPORT_VERSION,
        "kind": kind,
        "created": _now(),
        "status": status,
        "command": {"argv": list(command), "cwd": str(Path.cwd())},
        "checker": {
            "protocol_version": protocol.SCIENTIFIC_PROTOCOL_VERSION,
            "skeleton_version": protocol.SKELETON_VERSION,
            "source": artifacts.checker_source_identity(Path(repo_root)),
        },
        "inputs": dict(inputs),
        "tolerances": dict(tolerances),
        "result": dict(result),
        "errors": list(errors),
    }


def _failure_envelope(
    kind: str,
    *,
    command: Sequence[str],
    repo_root: Path,
    inputs: Mapping[str, Any],
    tolerances: Mapping[str, Any],
    exc: BaseException,
) -> Dict[str, Any]:
    error = {"type": type(exc).__name__, "message": str(exc)}
    return _envelope(
        kind,
        command=command,
        repo_root=repo_root,
        inputs=inputs,
        tolerances=tolerances,
        status="failed",
        result={"status": "failed", "error": error},
        errors=[error],
    )


def _finish(destination: Path, envelope: Dict[str, Any]) -> Dict[str, Any]:
    path = _write_report(destination, envelope)
    return {
        "report_path": str(path),
        "status": envelope["status"],
        "report": envelope["result"],
        "envelope": envelope,
    }


def _now() -> str:
    return artifacts.now()


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise CheckError(f"required artifact is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_npy(path: Path) -> np.ndarray:
    if not path.exists():
        raise CheckError(f"required numeric artifact is missing: {path}")
    return np.load(path, allow_pickle=False)


def _load_npz(path: Path) -> Dict[str, np.ndarray]:
    if not path.exists():
        raise CheckError(f"required numeric artifact is missing: {path}")
    with np.load(path, allow_pickle=False) as handle:
        return {name: np.asarray(handle[name]) for name in handle.files}


def _hash_files(relative_paths: Iterable[str], run_dir: Path) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for relative in relative_paths:
        path = run_dir / relative
        if path.is_file():
            hashes[relative] = sha256_file(path)
    return hashes


_CONSUMED_RELATIVE = (
    "config.json",
    "provenance.json",
    "metrics.json",
    "windows.json",
    "nodes.parquet",
    "masks.npz",
    "audit.json",
    "graph-audit.json",
    "selection.json",
    "training-history.json",
    "models/selected.npz",
    "source.json",
    "environment.json",
    "gold/validation.npy",
    "gold/test.npy",
)


def _prediction_relative(method: str, split: str) -> str:
    return f"predictions/{method}/{split}.npy"


@dataclass
class LoadedRun:
    run_dir: Path
    status: Mapping[str, Any]
    config: Mapping[str, Any]
    provenance: Mapping[str, Any]
    metrics: Mapping[str, Any]
    windows: Mapping[str, Any]
    selection: Mapping[str, Any]
    history: Mapping[str, Any]
    environment: Mapping[str, Any]
    source: Mapping[str, Any]
    audit: Mapping[str, Any]
    graph_audit: Mapping[str, Any]
    masks: Dict[str, np.ndarray]
    nodes: Any
    gold: Dict[str, np.ndarray]
    predictions: Dict[str, Dict[str, np.ndarray]]
    parameters: Dict[str, np.ndarray]

    @property
    def dataset(self) -> str:
        return str(self.config.get("spec", {}).get("data_name"))

    @property
    def method(self) -> str:
        return str(self.config.get("spec", {}).get("method"))

    @property
    def model_seed(self) -> int:
        return int(self.config.get("spec", {}).get("model_seed"))

    @property
    def shuffle_seed(self) -> Optional[int]:
        value = self.config.get("spec", {}).get("shuffle_seed")
        return None if value is None else int(value)

    @property
    def methods(self) -> List[str]:
        return [*protocol.NAIVE_METHODS, self.method]

    @property
    def splits(self) -> Tuple[str, ...]:
        return ("validation", "test")


def load_run(run_dir: Path) -> LoadedRun:
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise CheckError(f"input run directory does not exist: {run_dir}")
    status = _read_json(run_dir / "status.json")
    if not isinstance(status, Mapping):
        raise CheckError(f"{run_dir}/status.json is not a JSON object")
    state = status.get("state")
    if state != "success":
        raise CheckError(
            f"{run_dir} is not a completed run (state={state!r}); saved-only checks "
            "require a successful execution"
        )
    config = _read_json(run_dir / "config.json")
    provenance = _read_json(run_dir / "provenance.json")
    metrics_document = _read_json(run_dir / "metrics.json")
    windows = _read_json(run_dir / "windows.json")
    selection = _read_json(run_dir / "selection.json")
    history = _read_json(run_dir / "training-history.json")
    environment = _read_json(run_dir / "environment.json")
    source = _read_json(run_dir / "source.json")
    audit_document = _read_json(run_dir / "audit.json")
    graph_audit_document = _read_json(run_dir / "graph-audit.json")
    if not isinstance(audit_document, Mapping):
        raise CheckError(f"{run_dir}/audit.json is not a JSON object")
    if not isinstance(graph_audit_document, Mapping):
        raise CheckError(f"{run_dir}/graph-audit.json is not a JSON object")
    masks = _load_npz(run_dir / "masks.npz")
    import pandas as pd

    nodes = pd.read_parquet(run_dir / "nodes.parquet")
    gold = {split: _load_npy(run_dir / "gold" / f"{split}.npy") for split in ("validation", "test")}
    spec = config.get("spec") if isinstance(config, Mapping) else None
    if not isinstance(spec, Mapping):
        raise CheckError(f"{run_dir}/config.json does not contain a run spec")
    method = str(spec.get("method"))
    if method not in protocol.METHODS:
        raise CheckError(f"{run_dir}: unknown method {method!r}")
    predictions = {
        split: {
            name: _load_npy(run_dir / _prediction_relative(name, split))
            for name in [*protocol.NAIVE_METHODS, method]
        }
        for split in ("validation", "test")
    }
    parameters = _load_npz(run_dir / "models/selected.npz")
    return LoadedRun(
        run_dir=run_dir,
        status=status,
        config=config,
        provenance=provenance,
        metrics=metrics_document,
        windows=windows,
        selection=selection,
        history=history,
        environment=environment,
        source=source,
        audit=audit_document,
        graph_audit=graph_audit_document,
        masks=masks,
        nodes=nodes,
        gold=gold,
        predictions=predictions,
        parameters=parameters,
    )


# ---------------------------------------------------------------------------
# shared validation and recomputation
# ---------------------------------------------------------------------------
def _json_equal(left: Any, right: Any) -> bool:
    return left == right


def _validate_loaded(loaded: LoadedRun) -> Dict[str, Any]:
    """Validate saved identity/schema and return the recomputation inputs."""
    problems: List[str] = []
    run_dir = loaded.run_dir
    node_count = int(loaded.nodes.shape[0])
    key_columns = [column for column in loaded.nodes.columns if column != "node_index"]
    if not key_columns:
        raise CheckError(f"{run_dir}/nodes.parquet has no key columns")
    key_array = loaded.nodes[key_columns].to_numpy()
    if int(loaded.nodes["node_index"].to_numpy()[0]) != 0:
        problems.append("node_index does not start at 0")
    if not np.array_equal(
        loaded.nodes["node_index"].to_numpy(), np.arange(node_count)
    ):
        problems.append("node_index is not 0..N-1 in canonical order")
    demand_identity = loaded.provenance.get("demand", {})
    node_keys_sha = demand_identity.get("node_keys_sha256")
    if node_keys_sha != gvs_graph.node_keys_sha256(key_array):
        problems.append("nodes.parquet canonical keys do not match provenance hash")
    if int(demand_identity.get("nodes", -1)) != node_count:
        problems.append("provenance node count does not match nodes.parquet")
    spec = loaded.config.get("spec", {})
    if str(spec.get("data_name")) != str(loaded.provenance.get("dataset")):
        problems.append("config dataset disagrees with provenance")
    if str(spec.get("method")) != str(loaded.provenance.get("method")):
        problems.append("config method disagrees with provenance")
    if int(spec.get("model_seed", -1)) != int(loaded.provenance.get("model_seed", -2)):
        problems.append("config model seed disagrees with provenance")
    if spec.get("shuffle_seed") != loaded.provenance.get("shuffle_seed"):
        problems.append("config shuffle seed disagrees with provenance")
    if loaded.metrics.get("method") != spec.get("method"):
        problems.append("metrics.json method disagrees with config")
    if loaded.metrics.get("dataset") != spec.get("data_name"):
        problems.append("metrics.json dataset disagrees with config")
    expected_windows = protocol.window_metadata()
    if not _json_equal(loaded.windows, expected_windows):
        problems.append("windows.json is not the fixed 28-window main-split metadata")
    expected_mask_keys = set(_EXPECTED_MASK_KEYS)
    if set(loaded.masks) != expected_mask_keys:
        problems.append(
            f"mask keys {sorted(loaded.masks)} != {sorted(expected_mask_keys)}"
        )
    for name, array in loaded.masks.items():
        shape = (node_count,) if name != "nonzero_activity_train27" else (node_count,)
        if tuple(array.shape) != shape:
            problems.append(f"mask {name} shape {tuple(array.shape)} != {shape}")
    if set(loaded.masks) == expected_mask_keys:
        activity = loaded.masks["nonzero_activity_train27"]
        recomputed_groups = {
            "inactive": activity == 0,
            "low": (activity > 0) & (activity <= 1.0 / 3.0),
            "medium": (activity > 1.0 / 3.0) & (activity <= 2.0 / 3.0),
            "high": activity > 2.0 / 3.0,
        }
        for name, expected in recomputed_groups.items():
            if not np.array_equal(expected, loaded.masks[f"activity_{name}"]):
                problems.append(f"mask activity_{name} disagrees with the activity fraction")
        partition = sum(
            loaded.masks[f"activity_{name}"].astype(int)
            for name in ("inactive", "low", "medium", "high")
        )
        if not np.array_equal(partition, np.ones(node_count, dtype=int)):
            problems.append("activity masks do not partition the nodes")
        if not np.array_equal(
            loaded.masks["nonzero_activity_train27"] > 0,
            ~loaded.masks["activity_inactive"],
        ):
            problems.append("activity zero boundary disagrees with the inactive mask")
    mask_hashes = loaded.provenance.get("masks", {}).get("array_sha256", {})
    from .data import array_sha256

    for name, array in loaded.masks.items():
        recorded = mask_hashes.get(name)
        if recorded != array_sha256(array):
            problems.append(f"mask {name} bytes do not match provenance identity")
    gold_shape = {
        "validation": (1, node_count, protocol.HORIZON),
        "test": (4, node_count, protocol.HORIZON),
    }
    for split, shape in gold_shape.items():
        gold = loaded.gold[split]
        if tuple(gold.shape) != shape:
            problems.append(f"gold/{split}.npy shape {tuple(gold.shape)} != {shape}")
        if not np.isfinite(gold).all():
            problems.append(f"gold/{split}.npy contains non-finite labels")
        for name in loaded.methods:
            pred = loaded.predictions[split][name]
            if tuple(pred.shape) != shape:
                problems.append(
                    f"predictions/{name}/{split}.npy shape {tuple(pred.shape)} != {shape}"
                )
            if not np.isfinite(pred).all():
                problems.append(f"predictions/{name}/{split}.npy is non-finite")
    stored_methods = loaded.metrics.get("methods")
    if not isinstance(stored_methods, Mapping):
        problems.append("metrics.json has no methods object")
    else:
        for split in ("validation", "test"):
            present = set(stored_methods.get(split, {}))
            expected = set(loaded.methods)
            if present != expected:
                problems.append(
                    f"metrics.json {split} methods {sorted(present)} != {sorted(expected)}"
                )
    selection = loaded.selection
    if selection.get("test_labels_used_for_selection") is not False:
        problems.append("selection.json does not deny test-label use")
    training = selection.get("training")
    if not isinstance(training, Mapping):
        problems.append("selection.json has no training selection record")
    else:
        if int(training.get("epochs_completed", -1)) != protocol.EPOCHS:
            problems.append("training selection does not record 200 epochs")
        if training.get("test_labels_used_for_selection") is not False:
            problems.append("training selection does not deny test labels")
        if training.get("scheduler") is not None:
            problems.append("training selection records a scheduler")
        if training.get("early_stopping") is not False:
            problems.append("training selection records early stopping")
        if training.get("gradient_clipping") is not None:
            problems.append("training selection records gradient clipping")
    _validate_history(loaded, problems, node_count)
    _validate_parameters(loaded, problems)
    _validate_saved_graph_evidence(loaded, problems, node_count)
    _validate_saved_audit_evidence(loaded, problems, node_count)

    # Naive reference identity: published runs must still be LastValue.
    references = loaded.metrics.get("references", {})
    if demand_identity.get("source_kind") == "published":
        if references.get("NaiveRef") != protocol.NAIVE_REF_PUBLISHED:
            problems.append(
                "published run does not record NaiveRef=LastValue"
            )
    if problems:
        raise CheckError("saved evidence is inconsistent: " + "; ".join(problems))
    selected_epoch = int(loaded.history["selected_epoch"])
    return {
        "node_count": node_count,
        "key_columns": key_columns,
        "key_array": key_array,
        "context_values": key_array[:, 0],
        "selected_epoch": selected_epoch,
        "activity_masks": {
            name: loaded.masks[f"activity_{name}"]
            for name in ("inactive", "low", "medium", "high")
        },
        "constant_masks": p01_metrics.constant_group_masks(
            loaded.masks["constant_train27"], scope="train27"
        ),
        "neighbor_masks": p01_metrics.neighbor_group_masks(
            loaded.masks["has_nonself_neighbor"]
        ),
        "context_masks": p01_metrics.context_masks(key_array[:, 0]),
    }


def _exact_int(value: Any) -> bool:
    """Return True only for a JSON integer (never a bool or a float)."""
    return isinstance(value, int) and not isinstance(value, bool)


_SCORE_FIELDS = (
    "train_MSE_original_units_before_update",
    "train_MAE_original_units_before_update",
    "validation_MSE_original_units_after_update",
    "validation_MAE_original_units_after_update",
)


def _validate_history(
    loaded: LoadedRun, problems: List[str], node_count: int
) -> None:
    """Validate exact history counts, score domains and selection consistency."""
    history = loaded.history
    rows = history.get("rows")
    if not isinstance(rows, list) or len(rows) != protocol.EPOCHS:
        problems.append(
            f"training-history.json must hold {protocol.EPOCHS} rows, got "
            f"{len(rows) if isinstance(rows, list) else type(rows).__name__}"
        )
        return
    expected_train_elements = (
        len(protocol.TRAIN_STARTS) * int(node_count) * protocol.HORIZON
    )
    expected_validation_elements = (
        len(protocol.VALIDATION_STARTS) * int(node_count) * protocol.HORIZON
    )
    history_valid = True
    for index, row in enumerate(rows):
        label = f"history row {index + 1}"
        if not isinstance(row, Mapping):
            problems.append(f"{label} is not an object")
            history_valid = False
            continue
        epoch = row.get("epoch")
        if not _exact_int(epoch) or int(epoch) != index + 1:
            problems.append(
                f"{label} epoch {epoch!r} is not the exact integer {index + 1}"
            )
            history_valid = False
        missing = [
            field
            for field in ("train_elements", "validation_elements", *_SCORE_FIELDS)
            if field not in row
        ]
        if missing:
            problems.append(f"{label} is missing {missing}")
            history_valid = False
            continue
        for field, expected in (
            ("train_elements", expected_train_elements),
            ("validation_elements", expected_validation_elements),
        ):
            value = row[field]
            if not _exact_int(value):
                problems.append(
                    f"{label} {field} {value!r} is not an exact integer"
                )
                history_valid = False
            elif int(value) != expected:
                problems.append(
                    f"{label} {field} {int(value)} != {expected}"
                )
                history_valid = False
        for field in _SCORE_FIELDS:
            value = row[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                problems.append(f"{label} {field} {value!r} is not a number")
                history_valid = False
                continue
            number = float(value)
            if not math.isfinite(number):
                problems.append(f"{label} {field} is non-finite")
                history_valid = False
            elif number < 0.0:
                problems.append(f"{label} {field} {number} is negative")
                history_valid = False
    if not history_valid:
        return
    best_epoch = 0
    best_value = float("inf")
    for row in rows:
        value = float(row["validation_MSE_original_units_after_update"])
        if value < best_value:
            best_value = value
            best_epoch = int(row["epoch"])
    recorded_epoch = history.get("selected_epoch")
    if not _exact_int(recorded_epoch) or int(recorded_epoch) != best_epoch:
        problems.append(
            f"selected epoch {recorded_epoch!r} is not the earliest "
            f"validation-MSE minimum {best_epoch}"
        )
    selection_training = loaded.selection.get("training")
    if not isinstance(selection_training, Mapping):
        problems.append("selection.json has no training selection record")
        selection_training = {}
    recorded_selection_epoch = selection_training.get("selected_epoch")
    if not _exact_int(recorded_selection_epoch) or int(recorded_selection_epoch) != best_epoch:
        problems.append(
            "selection.json selected epoch "
            f"{recorded_selection_epoch!r} is not the earliest validation-MSE "
            f"minimum {best_epoch}"
        )
    selected_row = rows[best_epoch - 1]
    recorded_value = history.get("selected_validation_MSE")
    if isinstance(recorded_value, bool) or not isinstance(recorded_value, (int, float)):
        problems.append(
            f"recorded selected validation MSE {recorded_value!r} is not a number"
        )
    else:
        number = float(recorded_value)
        if not math.isfinite(number) or number < 0.0:
            problems.append(
                f"recorded selected validation MSE {number} is not a finite "
                "nonnegative error score"
            )
        elif not math.isclose(
            number,
            float(selected_row["validation_MSE_original_units_after_update"]),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            problems.append(
                "recorded selected validation MSE disagrees with the selected "
                "history row"
            )
    selection_value = selection_training.get("selected_validation_MSE")
    if isinstance(selection_value, bool) or not isinstance(selection_value, (int, float)):
        problems.append(
            f"selection.json selected validation MSE {selection_value!r} is not a number"
        )
    else:
        number = float(selection_value)
        if not math.isfinite(number) or number < 0.0:
            problems.append(
                f"selection.json selected validation MSE {number} is not a finite "
                "nonnegative error score"
            )
        elif float(selected_row["validation_MSE_original_units_after_update"]) != number:
            problems.append(
                "selection.json selected validation MSE disagrees with the selected "
                "history row"
            )
    # The selected history score must agree with the saved selected-prediction
    # validation metrics; this is the consistency the negative-score probe broke.
    methods = loaded.metrics.get("methods")
    validation_report = (
        methods.get("validation") if isinstance(methods, Mapping) else None
    )
    model_report = (
        validation_report.get(loaded.method)
        if isinstance(validation_report, Mapping)
        else None
    )
    if not isinstance(model_report, Mapping):
        problems.append(
            "metrics.json has no validation report for the model method"
        )
        return
    for field, metric in (
        ("validation_MSE_original_units_after_update", "MSE"),
        ("validation_MAE_original_units_after_update", "MAE"),
    ):
        reported = model_report.get(metric)
        if isinstance(reported, bool) or not isinstance(reported, (int, float)):
            problems.append(
                f"metrics.json validation {metric} {reported!r} is not a number"
            )
            continue
        reported_number = float(reported)
        if not math.isfinite(reported_number) or reported_number < 0.0:
            problems.append(
                f"metrics.json validation {metric} {reported_number} is not a "
                "finite nonnegative error score"
            )
            continue
        row_number = float(selected_row[field])
        difference = normalized_difference(row_number, reported_number)
        if difference > DIAGNOSTIC_RELATIVE_TOLERANCE:
            problems.append(
                f"selected history {metric} {row_number} disagrees with the saved "
                f"selected-prediction validation {metric} {reported_number} "
                f"(normalized difference {difference:.3e})"
            )


def _exact_nonnegative_count(
    value: Any, label: str, problems: List[str]
) -> Optional[int]:
    """Return an exact nonnegative JSON integer, or record why it is invalid."""
    if not _exact_int(value):
        problems.append(f"{label} {value!r} is not an exact integer")
        return None
    number = int(value)
    if number < 0:
        problems.append(f"{label} {number} is negative")
        return None
    return number


def _validate_fraction(
    value: Any, expected: Optional[float], label: str, problems: List[str]
) -> None:
    """Validate a saved audit fraction against saved-set arithmetic."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        problems.append(f"{label} {value!r} is not a number")
        return
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        problems.append(f"{label} {number} is outside [0,1]")
        return
    if expected is None:
        problems.append(f"{label} has no saved-set arithmetic value")
        return
    difference = normalized_difference(number, expected)
    if difference > DIAGNOSTIC_RELATIVE_TOLERANCE:
        problems.append(
            f"{label} {number} disagrees with saved-set arithmetic {expected} "
            f"(normalized difference {difference:.3e})"
        )


def _validate_saved_audit_evidence(
    loaded: LoadedRun, problems: List[str], node_count: int
) -> None:
    """Require complete, exact and mutually consistent graph/shuffle audits."""
    audit_document = loaded.audit
    graph_audit = loaded.graph_audit
    demand_identity = loaded.provenance.get("demand", {})
    graph_identity = loaded.provenance.get("graph", {})
    graph_used = loaded.provenance.get("graph_used", {})
    if not isinstance(graph_identity, Mapping):
        graph_identity = {}
    if not isinstance(graph_used, Mapping):
        graph_used = {}
    identity = audit_document.get("identity")
    if not isinstance(identity, Mapping):
        problems.append("audit.json has no identity record")
    else:
        if identity.get("node_keys_sha256") != demand_identity.get(
            "node_keys_sha256"
        ):
            problems.append("audit.json node-key hash disagrees with provenance")
        recorded_nodes = _exact_nonnegative_count(
            identity.get("nodes"), "audit.json identity nodes", problems
        )
        if recorded_nodes is not None and recorded_nodes != node_count:
            problems.append(
                "audit.json node count is not the saved node count"
            )
    masks = audit_document.get("masks")
    if not isinstance(masks, Mapping):
        problems.append("audit.json has no mask record")
    else:
        recorded_hashes = loaded.provenance.get("masks", {}).get("array_sha256")
        if masks.get("array_sha256") != recorded_hashes:
            problems.append("audit.json mask hashes disagree with provenance")
        if masks.get("recomputed_from_shuffled_adjacency") is not False:
            problems.append(
                "audit.json does not state that masks are independent of the "
                "shuffled adjacency"
            )
        if masks.get("shared_by_methods") != list(protocol.METHODS):
            problems.append(
                "audit.json does not record the mask as shared by all methods"
            )
    if not isinstance(graph_audit, Mapping):
        problems.append("graph-audit.json is not an object")
        return
    raw_rows = _exact_nonnegative_count(
        graph_audit.get("raw_rows"), "graph-audit.json raw_rows", problems
    )
    unique_edges = _exact_nonnegative_count(
        graph_audit.get("unique_edges"), "graph-audit.json unique_edges", problems
    )
    provenance_raw = _exact_nonnegative_count(
        graph_identity.get("raw_rows"), "provenance graph raw_rows", problems
    )
    provenance_unique = _exact_nonnegative_count(
        graph_identity.get("unique_edges"), "provenance graph unique_edges", problems
    )
    if (
        raw_rows is not None
        and provenance_raw is not None
        and raw_rows != provenance_raw
    ):
        problems.append("graph-audit.json raw row count disagrees with provenance")
    if (
        unique_edges is not None
        and provenance_unique is not None
        and unique_edges != provenance_unique
    ):
        problems.append("graph-audit.json unique edge count disagrees with provenance")
    if graph_audit.get("source_sha256") != graph_identity.get("source_sha256"):
        problems.append("graph-audit.json source hash disagrees with provenance")
    self_loops = _exact_nonnegative_count(
        graph_audit.get("self_loop_rows"), "graph-audit.json self_loop_rows", problems
    )
    if self_loops is not None and self_loops != 0:
        problems.append("graph-audit.json records accepted self-loop rows")
    multiplicity = graph_audit.get("multiplicity")
    if not isinstance(multiplicity, Mapping):
        problems.append("graph-audit.json has no multiplicity audit")
    else:
        if multiplicity.get("weights_edges") is not False:
            problems.append(
                "graph-audit.json does not record a binary, unweighted multiplicity audit"
            )
        _exact_nonnegative_count(
            multiplicity.get("duplicate_rows", 0),
            "graph-audit.json multiplicity duplicate_rows",
            problems,
        )
        maximum = _exact_nonnegative_count(
            multiplicity.get("max_multiplicity", 0),
            "graph-audit.json multiplicity max_multiplicity",
            problems,
        )
        if maximum is not None and unique_edges and maximum < 1:
            problems.append("graph-audit.json max multiplicity is below one")
    message_record = graph_audit.get("message_edges")
    if not isinstance(message_record, Mapping):
        problems.append("graph-audit.json has no message-edge record")
    else:
        if message_record.get("edges_sha256") != graph_used.get(
            "message_edges_sha256"
        ):
            problems.append(
                "graph-audit.json message-edge hash disagrees with provenance"
            )
        message_count = _exact_nonnegative_count(
            message_record.get("edges"),
            "graph-audit.json message-edge edges",
            problems,
        )
        provenance_message_count = _exact_nonnegative_count(
            graph_used.get("message_edges"),
            "provenance graph_used message_edges",
            problems,
        )
        if (
            message_count is not None
            and provenance_message_count is not None
            and message_count != provenance_message_count
        ):
            problems.append(
                "graph-audit.json message-edge count disagrees with provenance"
            )
        if message_record.get("binary_unique_directed") is not True:
            problems.append(
                "graph-audit.json does not record binary unique directed edges"
            )
    key_columns = [column for column in loaded.nodes.columns if column != "node_index"]
    key_array = loaded.nodes[key_columns].to_numpy(dtype=np.int64)
    message_edges = _load_npy(loaded.run_dir / "graph/edges.npy")
    source_edges = _load_npy(loaded.run_dir / "graph/source-edges.npy")
    if source_edges.size and not np.array_equal(
        key_array[source_edges[:, 0], :-1], key_array[source_edges[:, 1], :-1]
    ):
        problems.append('saved source graph contains a cross-context edge')
    if message_edges.size and not np.array_equal(
        key_array[message_edges[:, 0], :-1], key_array[message_edges[:, 1], :-1]
    ):
        problems.append('saved message graph contains a cross-context edge')
    if loaded.method != protocol.METHOD_SHUFFLED:
        if "shuffle" in graph_audit:
            problems.append("non-shuffled run carries a shuffle audit record")
        return
    validate_shuffle_audit(key_array, source_edges, message_edges,
                           graph_audit.get("shuffle"), loaded.shuffle_seed, problems)
    shuffle_identity = graph_used.get("shuffle_identity", {})
    if not isinstance(shuffle_identity, Mapping):
        problems.append("provenance has no shuffled-graph identity")
    elif (shuffle_identity.get("edges_sha256") != gvs_graph.edge_set_sha256(message_edges)
          or shuffle_identity.get("source_edges_sha256") != gvs_graph.edge_set_sha256(source_edges)
          or shuffle_identity.get("edge_count") != len(message_edges)
          or shuffle_identity.get("shuffle_seed") != loaded.shuffle_seed
          or shuffle_identity.get("algorithm_version") != graph_audit.get("shuffle", {}).get("algorithm_version")):
        problems.append("provenance shuffled-graph identity disagrees with saved evidence")


def validate_shuffle_audit(key_array, source_edges, message_edges, shuffle_audit, configured_seed, problems):
    """Shared saved-only audit oracle for prepared graphs and completed runs."""
    node_count = len(key_array)
    for label, edges in (('source', source_edges), ('message', message_edges)):
        if (edges.ndim != 2 or edges.shape[1] != 2 or edges.dtype.kind not in 'iu'
            or (edges.size and (edges.min() < 0 or edges.max() >= node_count))):
            problems.append(f'invalid saved {label} edge shape/type/bounds')
            return
        if (len(edges) != len(np.unique(edges, axis=0))
            or (edges[:, 0] == edges[:, 1]).any()):
            problems.append(f'saved {label} graph has duplicate edges or self-loops')
    if len(source_edges) != len(message_edges):
        problems.append('shuffle changed edge count')
    for column in (0, 1):
        if not np.array_equal(np.bincount(source_edges[:, column], minlength=node_count),
                              np.bincount(message_edges[:, column], minlength=node_count)):
            problems.append('shuffle changed per-node directed degree')
    context_of_node = [
        tuple(int(value) for value in row[:-1]) for row in key_array.tolist()
    ]
    expected_contexts = sorted(set(context_of_node))
    context_ordinal = {
        context: index for index, context in enumerate(expected_contexts)
    }
    context_code = np.array(
        [context_ordinal[context_of_node[node]] for node in range(node_count)],
        dtype=np.int64,
    )
    context_nodes = {
        context: np.flatnonzero(context_code == index)
        for context, index in context_ordinal.items()
    }
    for label, edges in (
        ("graph/edges.npy", message_edges),
        ("graph/source-edges.npy", source_edges),
    ):
        if edges.size and not np.array_equal(
            context_code[edges[:, 0]], context_code[edges[:, 1]]
        ):
            problems.append(f"{label} contains a cross-context edge")
    if not isinstance(shuffle_audit, Mapping):
        problems.append("graph-audit.json has no shuffle audit for a shuffled run")
        return
    if shuffle_audit.get("algorithm") != protocol.SHUFFLE_ALGORITHM:
        problems.append("shuffle audit algorithm disagrees with the frozen algorithm")
    try:
        contract = protocol.shuffle_contract(shuffle_audit.get("algorithm_version"))
    except ValueError as exc:
        problems.append(str(exc))
        return
    if contract["proposal_batch_size"] > 1 or "proposal_batch_size" in shuffle_audit:
        batch = shuffle_audit.get("proposal_batch_size")
        if not _exact_int(batch) or batch != contract["proposal_batch_size"]:
            problems.append("shuffle audit proposal batch size disagrees with version")
    if shuffle_audit.get('seed_derivation') != 'PCG64(SeedSequence([shuffle_seed, context_id...]))':
        problems.append('shuffle seed derivation disagrees with contract')
    expected_rule = (f"accept {contract['accept_target_factor']}*E_ctx swaps, attempt at most "
                     f"{contract['attempt_limit_factor']}*E_ctx")
    if shuffle_audit.get('target_rule') != expected_rule:
        problems.append('shuffle target rule disagrees with version')
    for field, expected in (('model_rng_consumed', False), ('process_hash_iteration_used', False),
                            ('uniform_sampling_claimed', False), ('symmetry_is_not_a_shuffle_constraint', True)):
        if shuffle_audit.get(field) is not expected:
            problems.append(f'shuffle {field} disagrees with contract')
    if shuffle_audit.get('degree_summary') != gvs_shuffle._degree_summary(key_array, source_edges, message_edges):
        problems.append('shuffle degree summary disagrees with saved edges')
    audit_seed = _exact_nonnegative_count(
        shuffle_audit.get("shuffle_seed"), "shuffle audit shuffle_seed", problems
    )
    if audit_seed is None or configured_seed is None or audit_seed != int(
        configured_seed
    ):
        problems.append("shuffle audit seed disagrees with the configured seed")
        return
    if shuffle_audit.get("source_edges_sha256") != gvs_graph.edge_set_sha256(source_edges):
        problems.append("shuffle audit source-edge hash disagrees with saved edges")
    if shuffle_audit.get("result_edges_sha256") != gvs_graph.edge_set_sha256(message_edges):
        problems.append("shuffle audit result-edge hash disagrees with saved edges")
    accept_factor = _exact_nonnegative_count(
        shuffle_audit.get("accept_target_factor"),
        "shuffle audit accept_target_factor",
        problems,
    )
    attempt_factor = _exact_nonnegative_count(
        shuffle_audit.get("attempt_limit_factor"),
        "shuffle audit attempt_limit_factor",
        problems,
    )
    if (
        accept_factor is not None
        and accept_factor != contract["accept_target_factor"]
    ):
        problems.append(
            "shuffle audit accept_target_factor is not the frozen "
            f"{contract['accept_target_factor']}*E budget"
        )
    if (
        attempt_factor is not None
        and attempt_factor != contract["attempt_limit_factor"]
    ):
        problems.append(
            "shuffle audit attempt_limit_factor is not the frozen "
            f"{contract['attempt_limit_factor']}*E limit"
        )
    contexts = shuffle_audit.get("contexts")
    if not isinstance(contexts, list) or not contexts:
        problems.append("shuffle audit has no per-context records")
        return
    recorded_contexts: List[List[int]] = []
    for entry in contexts:
        if not isinstance(entry, Mapping) or not isinstance(
            entry.get("context"), list
        ):
            problems.append("shuffle audit context entry has no context list")
            return
        if not all(_exact_int(value) for value in entry["context"]):
            problems.append("shuffle audit context identity is not exact integers")
            return
        recorded_contexts.append([int(value) for value in entry["context"]])
    expected_context_lists = [list(context) for context in expected_contexts]
    if recorded_contexts != expected_context_lists:
        problems.append(
            "shuffle audit context inventory "
            f"{recorded_contexts} != expected {expected_context_lists}"
        )
        return
    total_attempts = 0
    total_accepted = 0
    total_edges = 0
    total_changed = 0
    nonempty_contexts = 0
    empty_contexts = 0
    for index, (entry, context) in enumerate(zip(contexts, expected_contexts)):
        label = f"shuffle audit context {list(context)}"
        ordinal = _exact_nonnegative_count(
            entry.get("ordinal"), f"{label} ordinal", problems
        )
        if ordinal is not None and ordinal != index:
            problems.append(f"{label} ordinal {ordinal} != {index}")
        expected_seed = gvs_shuffle.context_seed_sequence(
            int(configured_seed), context
        )
        if entry.get("seed_sequence") != expected_seed:
            problems.append(
                f"{label} seed_sequence {entry.get('seed_sequence')!r} != "
                f"{expected_seed}"
            )
        nodes_global = context_nodes[context]
        recorded_nodes = _exact_nonnegative_count(
            entry.get("nodes"), f"{label} nodes", problems
        )
        if recorded_nodes is not None and recorded_nodes != int(nodes_global.shape[0]):
            problems.append(f"{label} node count disagrees with saved nodes")
        edge_count = _exact_nonnegative_count(
            entry.get("edge_count"), f"{label} edge_count", problems
        )
        attempts = _exact_nonnegative_count(
            entry.get("attempts"), f"{label} attempts", problems
        )
        accepted = _exact_nonnegative_count(
            entry.get("accepted"), f"{label} accepted", problems
        )
        target = _exact_nonnegative_count(
            entry.get("target_accepted"), f"{label} target_accepted", problems
        )
        changed = _exact_nonnegative_count(
            entry.get("changed_edges"), f"{label} changed_edges", problems
        )
        empty_flag = entry.get("empty")
        if not isinstance(empty_flag, bool):
            problems.append(f"{label} empty flag is not boolean")
            continue
        inverse = np.full(node_count, -1, dtype=np.int64)
        inverse[nodes_global] = np.arange(nodes_global.shape[0], dtype=np.int64)
        member = context_code[message_edges[:, 0]] == index if message_edges.size else np.zeros(0, dtype=bool)
        context_message = (
            np.stack(
                [inverse[message_edges[member, 0]], inverse[message_edges[member, 1]]],
                axis=1,
            )
            if message_edges.size
            else np.zeros((0, 2), dtype=np.int64)
        )
        context_message = gvs_graph.canonical_edge_array(context_message)
        source_member = context_code[source_edges[:, 0]] == index if source_edges.size else np.zeros(0, dtype=bool)
        context_source = (
            np.stack(
                [inverse[source_edges[source_member, 0]], inverse[source_edges[source_member, 1]]],
                axis=1,
            )
            if source_edges.size
            else np.zeros((0, 2), dtype=np.int64)
        )
        context_source = gvs_graph.canonical_edge_array(context_source)
        if edge_count is not None and edge_count != int(context_message.shape[0]):
            problems.append(f"{label} edge_count disagrees with saved message edges")
        if edge_count is not None and edge_count != int(context_source.shape[0]):
            problems.append(f"{label} edge_count disagrees with saved source edges")
        original_set = {
            tuple(int(value) for value in row) for row in context_source.tolist()
        }
        result_set = {
            tuple(int(value) for value in row) for row in context_message.tolist()
        }
        removed = original_set - result_set
        added_set = result_set - original_set
        intersection_set = original_set & result_set
        symmetric_set = original_set ^ result_set
        edge_total = len(original_set)
        expected_fractions = {
            "changed_fraction": (
                len(removed) / edge_total if edge_total else None
            ),
            "intersection_fraction": (
                len(intersection_set) / edge_total if edge_total else None
            ),
            "symmetric_difference_fraction": (
                len(symmetric_set) / (2 * edge_total) if edge_total else None
            ),
        }
        if empty_flag != (context_message.shape[0] == 0):
            problems.append(f"{label} empty flag disagrees with saved message edges")
        if attempts is not None:
            total_attempts += attempts
        if accepted is not None:
            total_accepted += accepted
        if edge_count is not None:
            total_edges += edge_count
        if empty_flag:
            empty_contexts += 1
            for field, value in (
                ("edge_count", edge_count),
                ("attempts", attempts),
                ("accepted", accepted),
                ("target_accepted", target),
                ("changed_edges", changed),
            ):
                if value is not None and value != 0:
                    problems.append(f"{label} empty context has nonzero {field}")
            if "changed_fraction" not in entry or entry.get(
                "changed_fraction"
            ) is not None:
                problems.append(
                    f"{label} empty context changed_fraction is not null"
                )
            for field in ("intersection_edges", "symmetric_difference_edges"):
                value = _exact_nonnegative_count(
                    entry.get(field), f"{label} {field}", problems
                )
                if value is not None and value != 0:
                    problems.append(f"{label} empty context has nonzero {field}")
            rejections = entry.get("rejections")
            if not isinstance(rejections, Mapping):
                problems.append(f"{label} rejections is missing or not an object")
            else:
                counts = []
                for reason, count in rejections.items():
                    number = _exact_nonnegative_count(
                        count, f"{label} rejection {reason}", problems
                    )
                    if number is not None:
                        counts.append(number)
                if len(counts) == len(rejections) and sum(counts) != 0:
                    problems.append(
                        f"{label} empty context has nonzero rejection counts"
                    )
            continue
        nonempty_contexts += 1
        if context_message.shape[0] == 0 or context_source.shape[0] == 0:
            problems.append(f"{label} nonempty context has no saved edges")
            continue
        if changed is not None:
            total_changed += changed
        added = _exact_nonnegative_count(
            entry.get("added_edges"), f"{label} added_edges", problems
        )
        intersection = _exact_nonnegative_count(
            entry.get("intersection_edges"), f"{label} intersection_edges", problems
        )
        symmetric_difference = _exact_nonnegative_count(
            entry.get("symmetric_difference_edges"),
            f"{label} symmetric_difference_edges",
            problems,
        )
        attempt_limit = _exact_nonnegative_count(
            entry.get("attempt_limit"), f"{label} attempt_limit", problems
        )
        for field, actual, expected in (
            ("changed_edges", changed, len(removed)),
            ("added_edges", added, len(added_set)),
            ("intersection_edges", intersection, len(intersection_set)),
            (
                "symmetric_difference_edges",
                symmetric_difference,
                len(symmetric_set),
            ),
        ):
            if actual is not None and actual != expected:
                problems.append(
                    f"{label} {field} {actual} != saved-set arithmetic {expected}"
                )
        if changed is not None and changed <= 0:
            problems.append(f"{label} nonempty context changed no edges")
        for field, expected in expected_fractions.items():
            if field not in entry:
                problems.append(f"{label} is missing {field}")
            else:
                _validate_fraction(
                    entry.get(field), expected, f"{label} {field}", problems
                )
        if accepted is not None and target is not None and accepted != target:
            problems.append(f"{label} accepted swaps != target")
        if accepted is not None and attempts is not None and accepted > attempts:
            problems.append(f"{label} accepted swaps exceed attempts")
        if (
            attempts is not None
            and attempt_limit is not None
            and attempts > attempt_limit
        ):
            problems.append(f"{label} attempts exceed attempt_limit")
        if accept_factor is not None and target is not None and edge_count is not None:
            if target != accept_factor * edge_count:
                problems.append(
                    f"{label} target_accepted != accept_factor * edge_count"
                )
        if (
            attempt_factor is not None
            and attempt_limit is not None
            and edge_count is not None
            and attempt_limit != attempt_factor * edge_count
        ):
            problems.append(
                f"{label} attempt_limit != attempt_limit_factor * edge_count"
            )
        expected_source_hash = gvs_shuffle.context_edge_sha256(
            context, context_source
        )
        if entry.get("source_edges_sha256") != expected_source_hash:
            problems.append(
                f"{label} source_edges_sha256 disagrees with saved source edges"
            )
        expected_result_hash = gvs_shuffle.context_edge_sha256(
            context, context_message
        )
        if entry.get("result_edges_sha256") != expected_result_hash:
            problems.append(
                f"{label} result_edges_sha256 disagrees with saved message edges"
            )
        rejections = entry.get("rejections")
        if not isinstance(rejections, Mapping):
            problems.append(f"{label} rejections is missing or not an object")
        else:
            counts = []
            for reason, count in rejections.items():
                number = _exact_nonnegative_count(
                    count, f"{label} rejection {reason}", problems
                )
                if number is not None:
                    counts.append(number)
            if (
                len(counts) == len(rejections)
                and accepted is not None
                and attempts is not None
                and sum(counts) + accepted != attempts
            ):
                problems.append(
                    f"{label} rejection counts + accepted swaps != attempts"
                )
    top_changed = _exact_nonnegative_count(
        shuffle_audit.get("changed_edges"),
        "shuffle audit changed_edges",
        problems,
    )
    if top_changed is not None and top_changed != total_changed:
        problems.append(
            "shuffle audit changed_edges "
            f"{top_changed} != per-context changed sum {total_changed}"
        )
    if shuffle_audit.get("node_keys_sha256") != gvs_graph.node_keys_sha256(key_array):
        problems.append("shuffle audit node-key hash disagrees with provenance")
    totals = shuffle_audit.get("totals")
    if not isinstance(totals, Mapping):
        problems.append("shuffle audit has no totals record")
        return
    expected_totals = {
        "contexts": len(expected_contexts),
        "nonempty_contexts": nonempty_contexts,
        "empty_contexts": empty_contexts,
        "attempts": total_attempts,
        "accepted": total_accepted,
        "edges": total_edges,
    }
    for field, expected in expected_totals.items():
        value = _exact_nonnegative_count(
            totals.get(field), f"shuffle audit totals {field}", problems
        )
        if value is not None and value != expected:
            problems.append(
                f"shuffle audit totals {field} {value} != {expected}"
            )
    if total_edges != int(message_edges.shape[0]):
        problems.append(
            "shuffle audit per-context edges do not sum to the saved message edges"
        )


def _validate_parameters(loaded: LoadedRun, problems: List[str]) -> None:
    parameters = loaded.parameters
    counts = {
        "gru": int(np.asarray(parameters["parameter_count_gru"]).reshape(-1)[0]),
        "head": int(np.asarray(parameters["parameter_count_head"]).reshape(-1)[0]),
        "graph_only": int(
            np.asarray(parameters["parameter_count_graph_only"]).reshape(-1)[0]
        ),
        "total": int(np.asarray(parameters["parameter_count_total"]).reshape(-1)[0]),
    }
    expected = protocol.PARAMETER_COUNTS
    if counts["gru"] != expected["gru"] or counts["head"] != expected["head"]:
        problems.append(f"saved component parameter counts {counts} disagree with the frozen architecture")
    if counts["total"] != expected["total"]:
        problems.append(
            f"saved total parameter count {counts['total']} != {expected['total']}"
        )
    if counts["graph_only"] != 0:
        problems.append("saved model contains graph-only trainable parameters")
    names = [str(value) for value in np.asarray(parameters["parameter_names"]).reshape(-1)]
    tensor_keys = sorted(name for name in parameters if name not in _COUNT_KEYS)
    if sorted(names) != tensor_keys:
        problems.append("saved tensor names do not match the recorded parameter names")
    if counts["total"] != sum(int(parameters[name].size) for name in tensor_keys):
        problems.append("saved tensor sizes do not sum to the recorded total")
    measured = loaded.selection.get("parameter_counts_measured", {})
    if int(measured.get("total", -1)) != counts["total"]:
        problems.append("selection.json measured parameter count disagrees with the NPZ")
    signature = loaded.selection.get("parameter_signature", {})
    for name in tensor_keys:
        array = np.asarray(parameters[name])
        if list(array.shape) != list(signature.get(name, [])):
            problems.append(f"parameter {name} shape disagrees with selection.json")
            break
        if array.dtype.kind not in "fiu":
            problems.append(f"parameter {name} has unsupported dtype {array.dtype}")
            break
        if not np.isfinite(array.astype(np.float64)).all():
            problems.append(f"parameter {name} contains non-finite values")
            break


def _validate_saved_graph_evidence(
    loaded: LoadedRun, problems: List[str], node_count: int
) -> None:
    """Validate the saved actual-graph evidence and its recorded identity.

    The saved message and source edge arrays are part of the recoverable
    evidence: a report may not claim success when the actual graph is missing,
    non-canonical, out of range or inconsistent with its recorded hash.
    """
    graph_used = loaded.provenance.get("graph_used")
    graph_identity = loaded.provenance.get("graph")
    if not isinstance(graph_used, Mapping):
        problems.append("provenance.json has no graph_used record")
        graph_used = {}
    if not isinstance(graph_identity, Mapping):
        problems.append("provenance.json has no graph identity record")
        graph_identity = {}
    method = str(loaded.method)
    if graph_used.get("method") != method:
        problems.append("graph_used method disagrees with the configured method")
    if bool(graph_used.get("propagates_messages")) != (method != protocol.METHOD_SELF):
        problems.append("graph_used message flag disagrees with the configured method")
    if bool(graph_used.get("shuffled")) != (method == protocol.METHOD_SHUFFLED):
        problems.append("graph_used shuffled flag disagrees with the configured method")
    message_edges = _load_npy(loaded.run_dir / "graph/edges.npy")
    source_edges = _load_npy(loaded.run_dir / "graph/source-edges.npy")
    for label, array in (
        ("graph/edges.npy", message_edges),
        ("graph/source-edges.npy", source_edges),
    ):
        if array.ndim != 2 or int(array.shape[1]) != 2:
            problems.append(f"{label} shape {tuple(array.shape)} is not [E, 2]")
            continue
        if not np.issubdtype(array.dtype, np.integer):
            problems.append(f"{label} dtype {array.dtype} is not integer")
            continue
        canonical = gvs_graph.canonical_edge_array(array)
        if canonical.shape != array.shape or not np.array_equal(canonical, array):
            problems.append(f"{label} is not a unique canonical sorted edge array")
        if array.size:
            if int(array.min()) < 0 or int(array.max()) >= node_count:
                problems.append(f"{label} references a node outside 0..{node_count - 1}")
    expected_message = graph_used.get("message_edges_sha256")
    actual_message = gvs_graph.edge_set_sha256(message_edges)
    if message_edges.size == 0:
        if not (isinstance(expected_message, str) and expected_message.startswith("<empty")):
            problems.append(
                "saved message edges are empty but provenance does not record an "
                "empty message graph"
            )
    elif expected_message != actual_message:
        problems.append(
            "saved message edges do not match the provenance message-edge identity"
        )
    expected_source = graph_identity.get("edges_sha256")
    if expected_source != gvs_graph.edge_set_sha256(source_edges):
        problems.append(
            "saved source edges do not match the provenance source-edge identity"
        )
    recorded_unique = graph_identity.get("unique_edges")
    if isinstance(recorded_unique, int) and recorded_unique != int(source_edges.shape[0]):
        problems.append(
            f"saved source edge count {source_edges.shape[0]} != provenance "
            f"unique_edges {recorded_unique}"
        )
    training = graph_used.get("training_edges")
    if not isinstance(training, Mapping):
        problems.append("provenance.json has no training-edge identity")
    else:
        if training.get("edges_sha256") != actual_message:
            problems.append(
                "recorded training edges do not match the saved message edges"
            )
        if int(training.get("windows_verified", -1)) != len(protocol.TRAIN_STARTS):
            problems.append(
                "training-edge identity does not cover the 19 training windows"
            )
        if training.get("matches_message_edges") is not True:
            problems.append("training-edge identity does not assert message-graph equality")


def _recompute_reports(
    loaded: LoadedRun, validated: Mapping[str, Any]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    starts = {
        "validation": protocol.VALIDATION_STARTS,
        "test": protocol.TEST_STARTS,
    }
    recomputed: Dict[str, Dict[str, Any]] = {"validation": {}, "test": {}}
    for split in loaded.splits:
        for name in loaded.methods:
            recomputed[split][name] = p01_metrics.split_report(
                loaded.predictions[split][name],
                loaded.gold[split],
                starts=starts[split],
                activity_masks=validated["activity_masks"],
                constant_masks=validated["constant_masks"],
                context_masks_map=validated["context_masks"],
                neighbor_masks=validated["neighbor_masks"],
                group_names=p01.ACTIVITY_GROUP_NAMES,
                inactive_group_name="inactive",
            )
    references = loaded.metrics.get("references", {})
    reference_names = [
        name
        for name in (references.get("NaiveRef"), references.get("NaiveRef6"))
        if name is not None
    ]
    gains: Dict[str, Any] = {}
    for split in loaded.splits:
        gains[split] = p01_metrics.baseline_relative_comparison(
            recomputed[split],
            activity_groups=p01.ACTIVITY_GROUP_NAMES,
            context_names=list(validated["context_masks"]),
            neighbor_names=list(validated["neighbor_masks"]),
            model_names=[loaded.method],
            reference_names=reference_names,
        )
    return recomputed, gains


def recompute_run(loaded: LoadedRun) -> Dict[str, Any]:
    """Recompute every reported metric from saved arrays only."""
    validated = _validate_loaded(loaded)
    recomputed, gains = _recompute_reports(loaded, validated)
    stored = loaded.metrics.get("methods", {})
    comparisons: Dict[str, Any] = {}
    for split in loaded.splits:
        comparisons[split] = nb_checks.compare_report_schema(
            recomputed[split],
            stored.get(split, {}),
            tolerance=DIAGNOSTIC_RELATIVE_TOLERANCE,
            label=f"recompute:{split}",
            ignore_keys=_METADATA_KEYS,
        )
    gains_comparison = nb_checks.compare_report_schema(
        gains,
        loaded.metrics.get("relative_gains", {}),
        tolerance=DIAGNOSTIC_RELATIVE_TOLERANCE,
        label="recompute:relative_gains",
    )
    nonfinite = (
        nb_checks.find_nonfinite(stored)
        + nb_checks.find_nonfinite(recomputed)
        + nb_checks.find_nonfinite(loaded.metrics.get("relative_gains", {}))
    )
    semantics = nb_checks.validate_report_semantics(
        stored, label="stored"
    ) + nb_checks.validate_report_semantics(recomputed, label="recomputed")
    failed = [
        split for split in loaded.splits if comparisons[split]["status"] != "ok"
    ]
    if gains_comparison["status"] != "ok":
        failed.append("relative_gains")
    if nonfinite:
        failed.append("nonfinite_values")
    if semantics:
        failed.append("null_status_semantics")
    return {
        "status": "ok" if not failed else "mismatch",
        "failed_checks": failed,
        "comparisons": comparisons,
        "relative_gains_comparison": gains_comparison,
        "recomputed_methods": recomputed,
        "recomputed_relative_gains": gains,
        "nonfinite_fields": nonfinite,
        "semantic_problems": semantics,
        "source_data_read": False,
        "model_trained": False,
        "model_forward_called": False,
        "validated": {
            "nodes": validated["node_count"],
            "selected_epoch": validated["selected_epoch"],
            "methods": loaded.methods,
        },
    }


# ---------------------------------------------------------------------------
# command: recompute
# ---------------------------------------------------------------------------
def command_recompute(
    *,
    run_dir: Path,
    repo_root: Path,
    command: Sequence[str],
    report_path: Path,
) -> Dict[str, Any]:
    run_dir = Path(run_dir)
    destination = validate_report_destination(repo_root, Path(report_path), [run_dir])
    inputs: Dict[str, Any] = {"input_run_dir": str(run_dir)}
    before: Dict[str, str] = {}
    try:
        before = _hash_files(_CONSUMED_RELATIVE, run_dir)
        loaded = load_run(run_dir)
        before.update(
            {
                _prediction_relative(name, split): sha256_file(
                    run_dir / _prediction_relative(name, split)
                )
                for split in ("validation", "test")
                for name in loaded.methods
            }
        )
        inputs.update(
            {
                "input_run_id": loaded.provenance.get("run_id"),
                "input_status": loaded.status.get("state"),
                "dataset": loaded.dataset,
                "method": loaded.method,
                "model_seed": loaded.model_seed,
                "shuffle_seed": loaded.shuffle_seed,
                "consumed_sha256": before,
            }
        )
        result = recompute_run(loaded)
        after = dict(before)
        after.update(
            {
                _prediction_relative(name, split): sha256_file(
                    run_dir / _prediction_relative(name, split)
                )
                for split in ("validation", "test")
                for name in loaded.methods
            }
        )
        result["inputs_bytewise_unchanged"] = before == after
        result["input_sha256_after"] = after
        if before != after:
            result["failed_checks"].append("input_files_changed")
            result["status"] = "mismatch"
        envelope = _envelope(
            "recompute",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=RECOMPUTE_TOLERANCES,
            status=result["status"],
            result=result,
            errors=[],
        )
    except BaseException as exc:  # noqa: BLE001 - a usable destination gets a report
        envelope = _failure_envelope(
            "recompute",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=RECOMPUTE_TOLERANCES,
            exc=exc,
        )
    return _finish(destination, envelope)


# ---------------------------------------------------------------------------
# command: compare
# ---------------------------------------------------------------------------
def _source_identity(source: Mapping[str, Any]) -> Dict[str, Any]:
    files = source.get("files", {})
    return {
        "commit": source.get("commit"),
        "identity_available": source.get("identity_available"),
        "files": {
            relative: entry.get("sha256") if isinstance(entry, Mapping) else entry
            for relative, entry in files.items()
        },
        "unrecoverable_paths": source.get("unrecoverable_paths"),
    }


def _environment_identity(environment: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "python_version": environment.get("python_version"),
        "python_version_info": environment.get("python_version_info"),
        "platform": environment.get("platform"),
        "system": environment.get("system"),
        "machine": environment.get("machine"),
        "processor": environment.get("processor"),
        "cpu_count": environment.get("cpu_count"),
        "packages": environment.get("packages"),
        "torch": environment.get("torch"),
        "graph_extensions": environment.get("graph_extensions"),
        "gpu_available": environment.get("gpu_available"),
        "numpy_blas_config": environment.get("numpy_blas_config"),
        "thread_environment": environment.get("thread_environment"),
    }


def _condition_identity(loaded: LoadedRun) -> Dict[str, Any]:
    provenance = loaded.provenance
    return {
        "computational": loaded.config.get("computational"),
        "dataset_identity": {
            "node_keys_sha256": provenance.get("demand", {}).get("node_keys_sha256"),
            "source_sha256": provenance.get("demand", {}).get("source_sha256"),
            "source_kind": provenance.get("demand", {}).get("source_kind"),
            "nodes": provenance.get("demand", {}).get("nodes"),
            "key_columns": provenance.get("demand", {}).get("key_columns"),
        },
        "graph_identity": {
            "source_path": provenance.get("graph", {}).get("source_path"),
            "source_sha256": provenance.get("graph", {}).get("source_sha256"),
            "source_edges_sha256": provenance.get("graph", {}).get("edges_sha256"),
            "raw_rows": provenance.get("graph", {}).get("raw_rows"),
            "message_edges_sha256": provenance.get("graph_used", {}).get(
                "message_edges_sha256"
            ),
            "shuffle_identity": provenance.get("graph_used", {}).get(
                "shuffle_identity"
            ),
        },
        "protocol_identity": {
            "version": provenance.get("scientific_protocol", {}).get("version"),
            "sha256": provenance.get("scientific_protocol", {}).get("sha256"),
        },
        "policy_identity": provenance.get("records_policy"),
        "skeleton_version": provenance.get("skeleton_version"),
        "mask_sha256": provenance.get("masks", {}).get("array_sha256"),
        "source_identity": _source_identity(loaded.source),
        "environment_identity": _environment_identity(loaded.environment),
    }


def _diff_paths(left: Any, right: Any, prefix: str = "") -> List[Dict[str, Any]]:
    differences: List[Dict[str, Any]] = []

    def walk(a: Any, b: Any, path: str) -> None:
        if isinstance(a, Mapping) and isinstance(b, Mapping):
            for key in sorted({*a, *b}):
                walk(a.get(key), b.get(key), f"{path}.{key}" if path else str(key))
            return
        if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            for index, (left_item, right_item) in enumerate(zip(a, b)):
                walk(left_item, right_item, f"{path}[{index}]")
            return
        if a != b:
            differences.append({"path": path, "run_a": a, "run_b": b})

    walk(left, right, prefix)
    return differences


def compare_predictions(
    left: LoadedRun, right: LoadedRun
) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for split in left.splits:
        left_pred = left.predictions[split][left.method]
        right_pred = right.predictions[split][right.method]
        if left_pred.shape != right_pred.shape:
            raise CheckError(
                f"{split}: prediction shapes {left_pred.shape} != {right_pred.shape}"
            )
        absolute = np.abs(
            left_pred.astype(np.float64) - right_pred.astype(np.float64)
        )
        scale = np.maximum(
            1.0, np.maximum(np.abs(left_pred.astype(np.float64)), np.abs(right_pred.astype(np.float64)))
        )
        normalized = absolute / scale
        results[split] = {
            "max_absolute_difference": float(absolute.max()) if absolute.size else 0.0,
            "max_normalized_difference": float(normalized.max()) if normalized.size else 0.0,
            "elementwise_tolerance": CPU_RELATIVE_TOLERANCE,
            "elements": int(absolute.size),
            "status": (
                "ok"
                if absolute.size == 0 or float(normalized.max()) <= CPU_RELATIVE_TOLERANCE
                else "mismatch"
            ),
        }
        gold = left.gold[split]
        if not np.array_equal(gold, right.gold[split]):
            results[split]["gold_labels_equal"] = False
            results[split]["status"] = "mismatch"
        else:
            results[split]["gold_labels_equal"] = True
        left_mae = p01_metrics.error_metrics(left_pred, gold)["MAE"]
        right_mae = p01_metrics.error_metrics(right_pred, gold)["MAE"]
        mae_difference = normalized_difference(left_mae, right_mae)
        results[split]["MAE_a"] = left_mae
        results[split]["MAE_b"] = right_mae
        results[split]["MAE_normalized_difference"] = mae_difference
        if mae_difference > CPU_RELATIVE_TOLERANCE:
            results[split]["status"] = "mismatch"
    return results


def command_compare(
    *,
    run_a: Path,
    run_b: Path,
    repo_root: Path,
    command: Sequence[str],
    report_path: Path,
) -> Dict[str, Any]:
    run_a = Path(run_a)
    run_b = Path(run_b)
    destination = validate_report_destination(
        repo_root, Path(report_path), [run_a, run_b]
    )
    inputs: Dict[str, Any] = {
        "run_a": str(run_a),
        "run_b": str(run_b),
        "resolved_run_a": Path(run_a).resolve().as_posix(),
        "resolved_run_b": Path(run_b).resolve().as_posix(),
    }
    hashes_before: Dict[str, Dict[str, str]] = {}
    try:
        resolved_a = Path(run_a).resolve()
        resolved_b = Path(run_b).resolve()
        if resolved_a == resolved_b:
            raise CheckError(
                "run_a and run_b resolve to the same execution directory "
                f"({resolved_a}); a repeat comparison requires two independent runs"
            )
        left = load_run(run_a)
        right = load_run(run_b)
        left_execution = (left.provenance or {}).get("run_id")
        right_execution = (right.provenance or {}).get("run_id")
        if left_execution is not None and left_execution == right_execution:
            raise CheckError(
                "run_a and run_b declare the same execution identity "
                f"(run_id={left_execution!r}); a copied or aliased run cannot "
                "establish an independent repeat"
            )
        consumed_a = [
            *_CONSUMED_RELATIVE,
            *(
                _prediction_relative(name, split)
                for split in left.splits
                for name in left.methods
            ),
        ]
        consumed_b = [
            *_CONSUMED_RELATIVE,
            *(
                _prediction_relative(name, split)
                for split in right.splits
                for name in right.methods
            ),
        ]
        hashes_before = {
            "run_a": _hash_files(consumed_a, run_a),
            "run_b": _hash_files(consumed_b, run_b),
        }
        if left.method != right.method:
            raise CheckError(
                f"methods differ: {left.method!r} vs {right.method!r}"
            )
        if left.dataset != right.dataset:
            raise CheckError(
                f"datasets differ: {left.dataset!r} vs {right.dataset!r}"
            )
        if left.model_seed != right.model_seed:
            raise CheckError(
                f"model seeds differ: {left.model_seed} vs {right.model_seed}"
            )
        if left.shuffle_seed != right.shuffle_seed:
            raise CheckError(
                f"shuffle seeds differ: {left.shuffle_seed} vs {right.shuffle_seed}"
            )
        left_identity = _condition_identity(left)
        right_identity = _condition_identity(right)
        condition_differences = _diff_paths(left_identity, right_identity)
        predictions = compare_predictions(left, right)
        # Compare every recomputed metric between the two executions as well.
        left_validated = _validate_loaded(left)
        right_validated = _validate_loaded(right)
        left_recomputed, _ = _recompute_reports(left, left_validated)
        right_recomputed, _ = _recompute_reports(right, right_validated)
        metric_comparisons = {
            split: nb_checks.compare_report_schema(
                left_recomputed[split],
                right_recomputed[split],
                tolerance=CPU_RELATIVE_TOLERANCE,
                label=f"compare:{split}",
                ignore_keys=_COMPARE_IGNORED_KEYS,
            )
            for split in left.splits
        }
        nonfinite = (
            nb_checks.find_nonfinite(left_recomputed)
            + nb_checks.find_nonfinite(right_recomputed)
        )
        failed: List[str] = []
        if condition_differences:
            failed.append("condition_identity")
        for split, result in predictions.items():
            if result["status"] != "ok":
                failed.append(f"predictions:{split}")
        for split, comparison in metric_comparisons.items():
            if comparison["status"] != "ok":
                failed.append(f"metrics:{split}")
        if nonfinite:
            failed.append("nonfinite_values")
        inputs.update(
            {
                "run_a_id": left.provenance.get("run_id"),
                "run_b_id": right.provenance.get("run_id"),
                "dataset": left.dataset,
                "method": left.method,
                "model_seed": left.model_seed,
                "shuffle_seed": left.shuffle_seed,
                "consumed_sha256": hashes_before,
            }
        )
        result = {
            "status": "ok" if not failed else "mismatch",
            "failed_checks": failed,
            "condition_identity": {
                "run_a": left_identity,
                "run_b": right_identity,
                "differences": condition_differences,
            },
            "predictions": predictions,
            "metric_comparisons": metric_comparisons,
            "nonfinite_fields": nonfinite,
            "permitted_execution_metadata_differences": [
                "run_id",
                "output location",
                "timestamps",
                "measured costs",
            ],
            "source_data_read": False,
            "model_trained": False,
            "model_forward_called": False,
            "inputs_bytewise_unchanged": {
                "run_a": hashes_before.get("run_a")
                == _hash_files(consumed_a, run_a),
                "run_b": hashes_before.get("run_b")
                == _hash_files(consumed_b, run_b),
            },
        }
        if not all(result["inputs_bytewise_unchanged"].values()):
            result["failed_checks"].append("input_files_changed")
            result["status"] = "mismatch"
        envelope = _envelope(
            "compare",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=COMPARE_TOLERANCES,
            status=result["status"],
            result=result,
            errors=[],
        )
    except BaseException as exc:  # noqa: BLE001
        envelope = _failure_envelope(
            "compare",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=COMPARE_TOLERANCES,
            exc=exc,
        )
    return _finish(destination, envelope)


# ---------------------------------------------------------------------------
# command: summarize-shuffled
# ---------------------------------------------------------------------------
def command_summarize_shuffled(
    *,
    run_dirs: Sequence[Path],
    repo_root: Path,
    command: Sequence[str],
    report_path: Path,
) -> Dict[str, Any]:
    resolved_dirs = [Path(path) for path in run_dirs]
    if len(resolved_dirs) != 3:
        raise CheckError(
            "summarize-shuffled requires exactly three member run directories"
        )
    destination = validate_report_destination(
        repo_root, Path(report_path), resolved_dirs
    )
    inputs: Dict[str, Any] = {"run_dirs": [str(path) for path in resolved_dirs]}
    member_hashes_before: Dict[str, Dict[str, str]] = {}
    try:
        members: List[LoadedRun] = [load_run(path) for path in resolved_dirs]
        for member in members:
            if member.method != protocol.METHOD_SHUFFLED:
                raise CheckError(
                    f"{member.run_dir}: method is {member.method!r}, expected "
                    f"{protocol.METHOD_SHUFFLED!r}"
                )
        consumed_by_member = {
            str(member.run_dir): [
                *_CONSUMED_RELATIVE,
                *(
                    _prediction_relative(member.method, split)
                    for split in member.splits
                ),
            ]
            for member in members
        }
        member_hashes_before = {
            run_dir: _hash_files(paths, Path(run_dir))
            for run_dir, paths in consumed_by_member.items()
        }
        seeds = [member.shuffle_seed for member in members]
        if sorted(seed for seed in seeds if seed is not None) != list(protocol.SHUFFLE_SEEDS):
            raise CheckError(
                f"shuffle seeds {seeds} are not exactly {list(protocol.SHUFFLE_SEEDS)}"
            )
        if len(set(seeds)) != 3:
            raise CheckError(f"duplicate shuffle seeds: {seeds}")
        model_seeds = {member.model_seed for member in members}
        if len(model_seeds) != 1:
            raise CheckError(f"mixed model seeds: {sorted(model_seeds)}")
        # Members may differ only in shuffle seed/result graph and execution
        # identity; every other condition must match.
        def member_condition(member: LoadedRun) -> Dict[str, Any]:
            computational = dict(member.config.get("computational", {}))
            computational.pop("shuffle_seed", None)
            identity = _condition_identity(member)
            identity.pop("computational", None)
            graph_identity = dict(identity.get("graph_identity", {}))
            graph_identity.pop("shuffle_identity", None)
            graph_identity.pop("message_edges_sha256", None)
            identity["graph_identity"] = graph_identity
            return {"computational": computational, "identity": identity}

        reference_condition = member_condition(members[0])
        order = sorted(
            range(3),
            key=lambda index: (members[index].shuffle_seed is None, members[index].shuffle_seed),
        )
        condition_differences: List[Dict[str, Any]] = []
        for index in order:
            differences = _diff_paths(reference_condition, member_condition(members[index]))
            if differences:
                condition_differences.append(
                    {"member": str(members[index].run_dir), "differences": differences}
                )
        member_results: Dict[str, Any] = {}
        member_predictions: Dict[str, np.ndarray] = {}
        member_maes: Dict[str, float] = {}
        validation_maes: Dict[str, float] = {}
        for member in members:
            computed = recompute_run(member)
            if computed["status"] != "ok":
                raise CheckError(
                    f"{member.run_dir}: member metrics do not recompute from saved "
                    f"evidence ({computed['failed_checks']})"
                )
            split = "test"
            stored_mae = member.metrics["methods"][split][member.method]["MAE"]
            member_maes[str(member.shuffle_seed)] = float(stored_mae)
            validation_maes[str(member.shuffle_seed)] = float(
                member.metrics["methods"]["validation"][member.method]["MAE"]
            )
            member_predictions[str(member.shuffle_seed)] = member.predictions[split][
                member.method
            ]
            member_results[str(member.shuffle_seed)] = {
                "run_id": member.provenance.get("run_id"),
                "run_dir": str(member.run_dir),
                "shuffle_seed": member.shuffle_seed,
                "model_seed": member.model_seed,
                "test_MAE": float(stored_mae),
                "validation_MAE": validation_maes[str(member.shuffle_seed)],
                "shuffled_graph_edges_sha256": member.provenance.get(
                    "graph_used", {}
                ).get("shuffle_identity", {}).get("edges_sha256"),
                "source_graph_edges_sha256": member.provenance.get(
                    "graph", {}
                ).get("edges_sha256"),
                "recompute_status": computed["status"],
            }
        labels = [str(seed) for seed in protocol.SHUFFLE_SEEDS]
        control_test_mae = float(np.mean([member_maes[seed] for seed in labels]))
        control_validation_mae = float(
            np.mean([validation_maes[seed] for seed in labels])
        )
        gold = members[0].gold["test"]
        averaged_predictions = np.mean(
            np.stack([member_predictions[seed] for seed in labels], axis=0), axis=0
        )
        mae_of_averaged_predictions = p01_metrics.error_metrics(
            averaged_predictions, gold
        )["MAE"]
        failed: List[str] = []
        if condition_differences:
            failed.append("member_conditions")
        if any(
            entry["source_graph_edges_sha256"]
            != member_results[labels[0]]["source_graph_edges_sha256"]
            for entry in member_results.values()
        ):
            failed.append("source_graph_identity")
        result = {
            "status": "ok" if not failed else "mismatch",
            "failed_checks": failed,
            "model_seed": int(next(iter(model_seeds))),
            "dataset": members[0].dataset,
            "method": protocol.METHOD_SHUFFLED,
            "control_definition": (
                "(MAE_shuffle0 + MAE_shuffle1 + MAE_shuffle2) / 3 over the three "
                "independently trained shuffled graphs at the same model seed"
            ),
            "control_test_MAE": control_test_mae,
            "control_validation_MAE": control_validation_mae,
            "members": member_results,
            "member_order": labels,
            "individual_test_MAEs": member_maes,
            "individual_validation_MAEs": validation_maes,
            "mae_of_averaged_predictions": mae_of_averaged_predictions,
            "mae_of_averaged_predictions_is_not_the_control": True,
            "ranking_used": False,
            "weakest_graph_selected": False,
            "member_identity_retained": True,
            "condition_differences": condition_differences,
            "source_data_read": False,
            "model_trained": False,
            "model_forward_called": False,
        }
        member_inputs = []
        unchanged = True
        for member in members:
            key = str(member.run_dir)
            before = member_hashes_before[key]
            unchanged = unchanged and before == _hash_files(
                consumed_by_member[key], member.run_dir
            )
            member_inputs.append(
                {
                    "run_dir": str(member.run_dir),
                    "run_id": member.provenance.get("run_id"),
                    "shuffle_seed": member.shuffle_seed,
                    "consumed_sha256": before,
                }
            )
        result["inputs_bytewise_unchanged"] = unchanged
        if not unchanged:
            result["failed_checks"].append("input_files_changed")
            result["status"] = "mismatch"
        inputs.update({"members": member_inputs})
        envelope = _envelope(
            "summarize-shuffled",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=RECOMPUTE_TOLERANCES,
            status=result["status"],
            result=result,
            errors=[],
        )
    except BaseException as exc:  # noqa: BLE001
        envelope = _failure_envelope(
            "summarize-shuffled",
            command=command,
            repo_root=repo_root,
            inputs=inputs,
            tolerances=RECOMPUTE_TOLERANCES,
            exc=exc,
        )
    return _finish(destination, envelope)
