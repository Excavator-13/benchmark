"""Full-window optimization and immutable best-checkpoint selection.

One epoch is 19 updates in training-start order 0..18.  Every update accumulates
all node/horizon squared errors over the complete window (denominator ``N*3``)
chunk by chunk in canonical node order and performs exactly one Adam step after
one complete-gradient L2 clip.  The best snapshot is a deep copy of both the
model tensors and the optimizer state, so later updates can never alter it.

The engine is deliberately stage-neutral: it never sees test labels and never
writes artifacts.  The controller supplies checkpoint/resource hooks, which is
what lets recovery, watchdog and cost-gate tests inject failures.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

import numpy as np
import torch
from torch import nn

from benchmark.nograph_baseline import metrics as p01_metrics

from . import data as temporal_data
from . import model as temporal_model
from . import protocol

MetricMap = Dict[str, float]


class PauseRequest(RuntimeError):
    """Raised by a controller hook to stop the trajectory at an epoch boundary."""

    def __init__(self, reason: str, detail: Optional[Mapping[str, Any]] = None):
        super().__init__(reason)
        self.reason = reason
        self.detail = dict(detail or {})


@dataclass
class BestSnapshot:
    """An immutable copy of the best-so-far model and optimizer state."""

    epoch: int
    updates: int
    validation: MetricMap
    model_state: Dict[str, torch.Tensor]
    optimizer_state: Dict[str, Any]
    scale: float

    def manifest(self) -> Dict[str, Any]:
        return {
            "epoch": int(self.epoch),
            "updates": int(self.updates),
            "validation": dict(self.validation),
            "selection_metric": "validation original-unit MSE",
            "tie_break": "earliest update on an exact tie",
            "initialization_selected": False,
            "scale": float(self.scale),
        }


@dataclass
class EpochRecord:
    epoch: int
    updates: int
    validation_mse: float
    validation_mae: float
    online_train_loss: float
    clipped_updates: int
    pre_clip_norm_max: float
    wall_seconds: float

    def payload(self) -> Dict[str, Any]:
        return {
            "epoch": int(self.epoch),
            "updates": int(self.updates),
            "validation_MSE": float(self.validation_mse),
            "validation_MAE": float(self.validation_mae),
            "online_train_loss_mixed_parameters": float(self.online_train_loss),
            "clipped_updates": int(self.clipped_updates),
            "pre_clip_norm_max": float(self.pre_clip_norm_max),
            "wall_seconds": float(self.wall_seconds),
        }


@dataclass
class Hooks:
    """Controller callbacks; the scientific loop itself stays injectable-safe."""

    on_epoch_complete: Optional[Callable[["Trajectory"], None]] = None
    after_epoch: Optional[Callable[["Trajectory"], None]] = None
    after_update: Optional[Callable[["Trajectory", int, int], None]] = None
    clock: Optional[Callable[[], float]] = None


@dataclass
class RestoreState:
    """State restored from an epoch-boundary recovery checkpoint."""

    completed_epoch: int
    updates: int
    model_state: Dict[str, torch.Tensor]
    optimizer_state: Dict[str, Any]
    history: List[Dict[str, Any]]
    scores: Dict[str, Any]
    update_records: List[Dict[str, Any]]
    best: Optional[Dict[str, Any]]
    random_states: Dict[str, Any]


@dataclass
class FitResult:
    status: str
    config: protocol.FitConfig
    scale: float
    history: List[Dict[str, Any]]
    scores: Dict[str, Any]
    best: Dict[str, Any]
    best_model_state: Dict[str, torch.Tensor]
    best_optimizer_state: Dict[str, Any]
    final_model_state: Dict[str, torch.Tensor]
    final_optimizer_state: Dict[str, Any]
    updates: int
    update_records: List[Dict[str, Any]]
    epoch_seconds: List[float]
    validation_prediction: np.ndarray
    validation_targets: np.ndarray
    validation_metrics: MetricMap
    fit_diagnostics: Dict[str, Any]
    parameter_count: int
    initial_validation: MetricMap
    pause: Optional[Dict[str, Any]] = None
    completed_epoch: int = 0
    warnings: List[str] = field(default_factory=list)

    @property
    def paused(self) -> bool:
        return self.status != "completed"


def chunk_ranges(node_count: int, chunk: int) -> List[Tuple[int, int]]:
    """Return contiguous canonical node ranges (chunks never reorder nodes)."""
    if chunk <= 0:
        raise protocol.ProtocolError("node_chunk must be positive")
    return [(begin, min(node_count, begin + chunk)) for begin in range(0, node_count, chunk)]


def squared_error_sum(
    model: nn.Module,
    inputs: np.ndarray,
    targets: np.ndarray,
    scale: float,
    chunk: int,
    denominator: int,
) -> torch.Tensor:
    """Accumulate one complete window's scaled squared error and pre-clip norms.

    The returned scalar equals ``sum((pred - target)^2) / (N*H)`` over the whole
    window, independent of how many chunks the nodes were split into.
    """
    total: Optional[torch.Tensor] = None
    for begin, end in chunk_ranges(inputs.shape[0], chunk):
        x = torch.from_numpy(
            (inputs[begin:end] / float(scale)).astype(np.float32)
        ).unsqueeze(-1)
        y = torch.from_numpy(
            (targets[begin:end] / float(scale)).astype(np.float32)
        )
        prediction = model(x)
        error = prediction - y
        contribution = (error * error).sum() / float(denominator)
        total = contribution if total is None else total + contribution
    if total is None:
        raise protocol.ProtocolError("a window needs at least one node")
    return total


class Trajectory:
    """One deterministic protocol trajectory over training windows 0..18."""

    def __init__(
        self,
        arrays: temporal_data.FitArrays,
        config: protocol.FitConfig,
        *,
        hooks: Optional[Hooks] = None,
        restore: Optional[RestoreState] = None,
    ):
        arrays.assert_no_test_labels()
        self.arrays = arrays
        self.config = config.validate()
        self.hooks = hooks or Hooks()
        self.clock: Callable[[], float] = self.hooks.clock or time.perf_counter
        self.model = temporal_model.build_model(self.config)
        self.parameter_report = temporal_model.parameter_count_report(
            self.model, self.config.model
        )
        if (
            self.config.hidden_size == protocol.HIDDEN_SIZE
            and self.config.layers == protocol.LAYERS
            and not self.parameter_report["matches_protocol_architecture"]
        ):
            raise protocol.ProtocolError(
                f"{self.config.model} parameter count is "
                f"{self.parameter_report['observed']}, protocol requires "
                f"{self.parameter_report['protocol_expected']}"
            )
        self.parameter_count = int(self.parameter_report["observed"])
        self.optimizer = temporal_model.build_optimizer(
            self.model, self.config.learning_rate
        )
        self.scale = float(
            protocol.normalization_scale(
                float(np.sum(self.arrays.preprocessing_values**2, dtype=np.float64)),
                int(self.arrays.preprocessing_values.size),
            )
        )
        self.history: List[Dict[str, Any]] = []
        self.scores: Dict[str, Any] = {}
        self.best: Optional[BestSnapshot] = None
        self.updates = 0
        self.update_records: List[Dict[str, Any]] = []
        self.epoch_seconds: List[float] = []
        self.warnings: List[str] = []
        self.initial_validation: MetricMap = {}
        self.completed_epoch = 0
        self.pause: Optional[Dict[str, Any]] = None
        if restore is not None:
            self._restore(restore)

    # -- state -------------------------------------------------------------
    def _restore(self, restore: RestoreState) -> None:
        self.model.load_state_dict(restore.model_state)
        if restore.optimizer_state:
            self.optimizer.load_state_dict(
                temporal_model.deepcopy_state(restore.optimizer_state)
            )
        temporal_model.restore_random_states(restore.random_states)
        self.history = [dict(record) for record in restore.history]
        self.scores = {key: value for key, value in restore.scores.items()}
        self.update_records = [dict(record) for record in restore.update_records]
        self.completed_epoch = int(restore.completed_epoch)
        self.updates = int(restore.updates)
        if restore.best is not None:
            self.best = BestSnapshot(
                epoch=int(restore.best["epoch"]),
                updates=int(restore.best["updates"]),
                validation=dict(restore.best["validation"]),
                model_state=temporal_model.deepcopy_state(restore.best["model_state"]),
                optimizer_state=temporal_model.deepcopy_state(
                    restore.best["optimizer_state"]
                ),
                scale=float(restore.best["scale"]),
            )
        self.initial_validation = dict(restore.scores.get("init", {}).get("validation", {}))

    def epoch_seconds_map(self) -> Dict[int, float]:
        return {
            int(record["epoch"]): float(record["wall_seconds"])
            for record in self.history
        }

    # -- scoring -----------------------------------------------------------
    def validation_metrics(self, model: Optional[nn.Module] = None) -> MetricMap:
        prediction, _ = temporal_model.predict(
            model or self.model,
            self.arrays.validation_inputs,
            self.scale,
            self.config.node_chunk,
        )
        record = p01_metrics.error_metrics(
            prediction, self.arrays.validation_targets
        )
        return {"MSE": float(record["MSE"]), "MAE": float(record["MAE"])}

    def validation_prediction(self, model: Optional[nn.Module] = None) -> np.ndarray:
        prediction, _ = temporal_model.predict(
            model or self.model,
            self.arrays.validation_inputs,
            self.scale,
            self.config.node_chunk,
        )
        return prediction

    def fixed_parameter_scores(self) -> Dict[str, Any]:
        """Re-evaluate train and validation with the current fixed parameters."""
        train_prediction, _ = temporal_model.predict(
            self.model,
            self.arrays.train_inputs,
            self.scale,
            self.config.node_chunk,
        )
        validation_prediction = self.validation_prediction()
        train = p01_metrics.error_metrics(
            train_prediction, self.arrays.train_targets
        )
        validation = p01_metrics.error_metrics(
            validation_prediction, self.arrays.validation_targets
        )
        return {
            "train": {"MSE": float(train["MSE"]), "MAE": float(train["MAE"])},
            "validation": {
                "MSE": float(validation["MSE"]),
                "MAE": float(validation["MAE"]),
            },
            "parameter_state": "fixed",
        }

    # -- training ----------------------------------------------------------
    def _train_epoch(self, epoch: int) -> Tuple[float, int, float]:
        self.model.train()
        denominator = int(self.arrays.node_count * protocol.p01.HORIZON)
        loss_total = 0.0
        clipped = 0
        pre_clip_max = 0.0
        for window, start in enumerate(self.arrays.train_starts):
            self.optimizer.zero_grad(set_to_none=True)
            contribution = squared_error_sum(
                self.model,
                self.arrays.train_inputs[window],
                self.arrays.train_targets[window],
                self.scale,
                self.config.node_chunk,
                denominator,
            )
            contribution.backward()
            loss_total += float(contribution.detach())
            pre_clip = float(
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), float(self.config.grad_clip)
                )
            )
            pre_clip_max = max(pre_clip_max, pre_clip)
            was_clipped = pre_clip > float(self.config.grad_clip)
            clipped += int(was_clipped)
            self.optimizer.step()
            self.updates += 1
            if self.hooks.after_update is not None:
                self.hooks.after_update(self, epoch, window)
            self.update_records.append(
                {
                    "epoch": int(epoch),
                    "window_start": int(start),
                    "window_index": int(window),
                    "update": int(self.updates),
                    "pre_clip_norm": pre_clip,
                    "clipped": was_clipped,
                    "loss_sum": float(contribution.detach()),
                }
            )
        return loss_total, clipped, pre_clip_max

    def _maybe_select(self, epoch: int, validation: MetricMap) -> None:
        if self.updates <= 0:
            raise protocol.ProtocolError("a checkpoint must have step > 0")
        if self.best is not None and validation["MSE"] >= self.best.validation["MSE"]:
            return
        self.best = BestSnapshot(
            epoch=int(epoch),
            updates=int(self.updates),
            validation=dict(validation),
            model_state=temporal_model.clone_state_dict(self.model),
            optimizer_state=temporal_model.deepcopy_state(
                self.optimizer.state_dict()
            ),
            scale=self.scale,
        )

    def _record_score(self, name: str) -> None:
        scores = self.fixed_parameter_scores()
        scores["updates"] = int(self.updates)
        scores["epoch"] = int(self.completed_epoch)
        self.scores[name] = scores

    # -- run ---------------------------------------------------------------
    def run(self) -> FitResult:
        start_epoch = int(self.completed_epoch)
        if start_epoch == 0:
            initial = self.fixed_parameter_scores()
            initial["updates"] = 0
            initial["epoch"] = 0
            initial["note"] = "initialization evaluation; never a selectable step"
            self.scores["init"] = initial
            self.initial_validation = dict(initial["validation"])
        try:
            for epoch in range(start_epoch + 1, self.config.epochs + 1):
                started = self.clock()
                loss_total, clipped, pre_clip_max = self._train_epoch(epoch)
                validation = self.validation_metrics()
                elapsed = max(0.0, float(self.clock() - started))
                record = EpochRecord(
                    epoch=epoch,
                    updates=self.updates,
                    validation_mse=validation["MSE"],
                    validation_mae=validation["MAE"],
                    online_train_loss=loss_total,
                    clipped_updates=clipped,
                    pre_clip_norm_max=pre_clip_max,
                    wall_seconds=elapsed,
                )
                self.history.append(record.payload())
                self.epoch_seconds.append(elapsed)
                self._maybe_select(epoch, validation)
                self.completed_epoch = epoch
                if epoch in self.config.diagnostic_epochs:
                    self._record_score(str(epoch))
                if self.hooks.on_epoch_complete is not None:
                    self.hooks.on_epoch_complete(self)
                if self.hooks.after_epoch is not None:
                    self.hooks.after_epoch(self)
        except PauseRequest as exc:
            self.pause = {"reason": exc.reason, "detail": dict(exc.detail)}
        return self._finish()

    def _finish(self) -> FitResult:
        if self.best is None:
            raise protocol.ProtocolError(
                "no validation checkpoint was selected; the trajectory is unusable"
            )
        best = self.best
        self.model.load_state_dict(best.model_state)
        reproduced = self.validation_metrics()
        validation_prediction = self.validation_prediction()
        reproduction_tolerance = 1e-6
        differences = {
            key: abs(float(reproduced[key]) - float(best.validation[key]))
            for key in ("MSE", "MAE")
        }
        reproduction = {
            "saved": dict(best.validation),
            "reevaluated": dict(reproduced),
            "absolute_differences": differences,
            "tolerance": reproduction_tolerance,
            "status": (
                "pass"
                if all(value <= reproduction_tolerance for value in differences.values())
                else "fail"
            ),
        }
        best_scores = self.fixed_parameter_scores()
        best_scores.update(
            {
                "epoch": int(best.epoch),
                "updates": int(best.updates),
                "reproduction": reproduction,
            }
        )
        self.scores["best"] = best_scores
        diagnostics = self._fit_diagnostics(best, validation_prediction)
        final_model_state = temporal_model.clone_state_dict(self.model)
        final_optimizer_state = temporal_model.deepcopy_state(
            self.optimizer.state_dict()
        )
        if self.completed_epoch < self.config.epochs:
            self.warnings.append(
                "trajectory stopped at epoch "
                f"{self.completed_epoch} of {self.config.epochs}"
            )
        return FitResult(
            status="completed" if self.pause is None else "paused",
            config=self.config,
            scale=self.scale,
            history=self.history,
            scores=self.scores,
            best=best.manifest(),
            best_model_state=temporal_model.deepcopy_state(best.model_state),
            best_optimizer_state=temporal_model.deepcopy_state(
                best.optimizer_state
            ),
            final_model_state=final_model_state,
            final_optimizer_state=final_optimizer_state,
            updates=self.updates,
            update_records=self.update_records,
            epoch_seconds=self.epoch_seconds,
            validation_prediction=validation_prediction,
            validation_targets=np.asarray(
                self.arrays.validation_targets, dtype=np.float64
            ),
            validation_metrics=reproduced,
            fit_diagnostics=diagnostics,
            parameter_count=self.parameter_count,
            initial_validation=self.initial_validation,
            pause=self.pause,
            completed_epoch=self.completed_epoch,
            warnings=self.warnings,
        )

    # -- fit-time diagnostics ---------------------------------------------
    def _fit_diagnostics(
        self, best: BestSnapshot, validation_prediction: np.ndarray
    ) -> Dict[str, Any]:
        scaled_train_inputs = self.arrays.train_inputs / self.scale
        scaled_train_targets = self.arrays.train_targets / self.scale
        scaled_validation_inputs = self.arrays.validation_inputs / self.scale
        scaled_validation_targets = self.arrays.validation_targets / self.scale
        zeroed, _ = temporal_model.predict(
            self.model,
            np.zeros_like(self.arrays.validation_inputs),
            self.scale,
            self.config.node_chunk,
        )
        _, saturation = temporal_model.predict(
            self.model,
            self.arrays.validation_inputs,
            self.scale,
            self.config.node_chunk,
            collect_hidden_stats=True,
        )
        baseline = p01_metrics.error_metrics(
            validation_prediction, self.arrays.validation_targets
        )
        zeroed_metrics = p01_metrics.error_metrics(
            zeroed, self.arrays.validation_targets
        )
        return {
            "stage": "fit",
            "test_labels_used": False,
            "quantiles": {
                "train_scaled_inputs": _quantiles(scaled_train_inputs),
                "train_scaled_targets": _quantiles(scaled_train_targets),
                "validation_scaled_inputs": _quantiles(scaled_validation_inputs),
                "validation_scaled_targets": _quantiles(scaled_validation_targets),
                "percentiles": [0, 1, 5, 25, 50, 75, 95, 99, 100],
            },
            "saturation": {
                "definition": (
                    "fraction of output hidden-sequence elements with abs(h) > 0.99 "
                    "on validation windows; LSTM cell state is not used"
                ),
                "validation_fraction": saturation,
            },
            "prediction_scale": {
                "validation": _scale_statistics(
                    validation_prediction, self.arrays.validation_targets
                )
            },
            "input_zeroing": {
                "definition": (
                    "validation prediction difference when every validation input "
                    "is replaced by zero; diagnostic only, never used for tuning"
                ),
                "baseline_validation_MAE": float(baseline["MAE"]),
                "zeroed_validation_MAE": float(zeroed_metrics["MAE"]),
                "MAE_change": float(zeroed_metrics["MAE"] - baseline["MAE"]),
                "max_absolute_prediction_change": float(
                    np.max(np.abs(zeroed - validation_prediction))
                ),
            },
            "online_train_loss_note": (
                "history.online_train_loss_mixed_parameters accumulates losses "
                "computed on pre-update parameters and is not a fixed-checkpoint "
                "training MSE"
            ),
        }


def _quantiles(values: np.ndarray) -> Dict[str, Any]:
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    if flat.size == 0:
        return {"status": "empty"}
    percentiles = np.percentile(flat, [0, 1, 5, 25, 50, 75, 95, 99, 100])
    return {
        "min": float(percentiles[0]),
        "p1": float(percentiles[1]),
        "p5": float(percentiles[2]),
        "p25": float(percentiles[3]),
        "p50": float(percentiles[4]),
        "p75": float(percentiles[5]),
        "p95": float(percentiles[6]),
        "p99": float(percentiles[7]),
        "max": float(percentiles[8]),
        "mean": float(flat.mean()),
        "std": float(flat.std(ddof=0)),
        "elements": int(flat.size),
    }


def _scale_statistics(prediction: np.ndarray, targets: np.ndarray) -> Dict[str, Any]:
    values = np.asarray(prediction, dtype=np.float64)
    return {
        "mean": float(values.mean()),
        "std": float(values.std(ddof=0)),
        "min": float(values.min()),
        "max": float(values.max()),
        "negative_fraction": float((values < 0).mean()),
        "saturated_above_99th_target_percentile": None,
        "target_max": float(np.asarray(targets, dtype=np.float64).max()),
    }


def run_trajectory(
    arrays: temporal_data.FitArrays,
    config: protocol.FitConfig,
    *,
    hooks: Optional[Hooks] = None,
    restore: Optional[RestoreState] = None,
) -> FitResult:
    return Trajectory(arrays, config, hooks=hooks, restore=restore).run()
