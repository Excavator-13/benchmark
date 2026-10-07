"""Frozen training statistics, shared Ridge fitting and validation-only selection.

The model is a single shared ``6 x 3`` weight matrix plus three unregularized
biases, fit on standardized training windows with the objective

``(1/M) * sum_m ||x_m W + b - y_m||_2^2 + lambda * ||W||_F^2``

where ``M = 19 * N``.  Lambda is chosen exclusively by validation original-unit
MSE; test labels never reach fitting or selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from . import baselines, protocol
from .data import activity_group_masks


class RidgeError(ValueError):
    """Raised when a Ridge request violates the protocol contract."""


#: Fields every accepted solver backend must supply to the shared artifact
#: writer, so an optional backend cannot advertise support it cannot persist.
MODEL_PARAMETER_KEYS: Tuple[str, ...] = (
    "backend",
    "lambda",
    "alpha",
    "M",
    "W",
    "b",
    "objective",
    "centered_x_mean",
    "centered_y_mean",
)


def validate_model_payload(
    model: Mapping[str, Any], *, label: str = "model"
) -> Dict[str, Any]:
    """Return ``model`` after checking the shared backend payload contract."""
    missing = [key for key in MODEL_PARAMETER_KEYS if key not in model]
    if missing:
        raise RidgeError(
            f"{label} payload is missing required key(s) {missing}; every "
            f"accepted backend must supply {list(MODEL_PARAMETER_KEYS)}"
        )
    if np.asarray(model["W"]).shape != (
        protocol.INPUT_LENGTH,
        protocol.HORIZON,
    ):
        raise RidgeError(
            f"{label} weights must have shape [6, 3], got "
            f"{np.asarray(model['W']).shape}"
        )
    if np.asarray(model["b"]).shape != (protocol.HORIZON,):
        raise RidgeError(
            f"{label} bias must have shape [3], got {np.asarray(model['b']).shape}"
        )
    return dict(model)


@dataclass
class TrainingStats:
    """Frozen per-node statistics over the unique 27 training observations."""

    mean: np.ndarray  # float64 [N]
    std: np.ndarray  # float64 [N]
    effective_std: np.ndarray  # float64 [N], constant nodes -> 1
    constant_mask: np.ndarray  # bool [N]
    activity: np.ndarray  # float64 [N]
    activity_groups: Dict[str, np.ndarray]
    train_mean27_float32: np.ndarray  # float32 [N, 1]
    train_observation_months: Tuple[str, ...] = protocol.TRAIN_OBSERVATION_MONTHS
    ddof: int = 0

    @property
    def node_count(self) -> int:
        return int(self.mean.shape[0])

    def standardize(self, values: np.ndarray) -> np.ndarray:
        """Standardize raw values whose first axis is the node index."""
        array = np.asarray(values, dtype=np.float64)
        return (array - _node_axis_view(self.mean, array.ndim)) / _node_axis_view(
            self.effective_std, array.ndim
        )

    def inverse(self, standardized: np.ndarray) -> np.ndarray:
        """Map standardized values back to original count units."""
        array = np.asarray(standardized, dtype=np.float64)
        return array * _node_axis_view(
            self.effective_std, array.ndim
        ) + _node_axis_view(self.mean, array.ndim)

    def inverse_nodes_last(self, standardized: np.ndarray) -> np.ndarray:
        """Inverse-transform arrays whose node axis is axis 1."""
        array = np.asarray(standardized, dtype=np.float64)
        shape = (1, self.node_count) + (1,) * (array.ndim - 2)
        return array * self.effective_std.reshape(shape) + self.mean.reshape(shape)

    def payload(self) -> Dict[str, Any]:
        return {
            "node_count": self.node_count,
            "train_observation_months": list(self.train_observation_months),
            "ddof": self.ddof,
            "mean": self.mean,
            "std": self.std,
            "effective_std": self.effective_std,
            "constant_mask": self.constant_mask,
            "activity": self.activity,
        }


def compute_training_stats(signal: np.ndarray) -> TrainingStats:
    """Compute the frozen normalization and activity/constant masks.

    Statistics use exactly the 27 unique observations ``2021-01..2023-03``
    (each month counted once), never flattened overlapping windows.
    """
    values = np.asarray(signal)
    if values.ndim != 2 or values.shape[1] != protocol.N_MONTHS:
        raise RidgeError(
            f"signal must have shape [N, {protocol.N_MONTHS}], got {values.shape}"
        )
    train_count = protocol.TRAIN_OBSERVATION_MONTH_COUNT
    train = values[:, :train_count].astype(np.float64)
    mean = train.mean(axis=1)
    std = train.std(axis=1, ddof=0)
    constant_mask = std == 0
    effective_std = np.where(constant_mask, 1.0, std)
    # Activity is defined by the same unique training range; the boolean-mean
    # formula matches the v2 diagnostic exactly (all boundaries are k/27).
    activity = (values[:, :train_count] > 0).mean(axis=1).astype(np.float64)
    groups = activity_group_masks(activity)
    return TrainingStats(
        mean=mean,
        std=std,
        effective_std=effective_std,
        constant_mask=constant_mask,
        activity=activity,
        activity_groups=groups,
        train_mean27_float32=values[:, :train_count].mean(axis=1, keepdims=True),
    )


def build_design(
    signal: np.ndarray,
    stats: TrainingStats,
    starts: Sequence[int],
) -> Tuple[np.ndarray, np.ndarray]:
    """Build standardized ``[W*N, 6]`` inputs and ``[W*N, 3]`` targets.

    Ordering is window-major then node-major, so row ``w * N + i`` belongs to
    window ``starts[w]`` and node index ``i``.
    """
    values = np.asarray(signal)
    offset = protocol.INPUT_LENGTH
    horizon = protocol.HORIZON
    inputs = np.stack(
        [
            stats.standardize(values[:, start : start + offset])
            for start in starts
        ],
        axis=0,
    )
    targets = np.stack(
        [
            stats.standardize(
                values[:, start + offset : start + offset + horizon]
            )
            for start in starts
        ],
        axis=0,
    )
    windows, nodes = inputs.shape[0], inputs.shape[1]
    x = np.ascontiguousarray(inputs.reshape(windows * nodes, offset))
    y = np.ascontiguousarray(targets.reshape(windows * nodes, horizon))
    return x, y


def fit_numpy(x: np.ndarray, y: np.ndarray, lam: float) -> Dict[str, Any]:
    """Fit the shared Ridge solution with pure NumPy linear algebra."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != protocol.INPUT_LENGTH:
        raise RidgeError(f"x must have shape [M, 6], got {x.shape}")
    if y.ndim != 2 or y.shape[1] != protocol.HORIZON:
        raise RidgeError(f"y must have shape [M, 3], got {y.shape}")
    samples = int(x.shape[0])
    x_mean = x.mean(axis=0)
    y_mean = y.mean(axis=0)
    x_centered = x - x_mean
    y_centered = y - y_mean
    alpha = float(lam) * samples
    gram = x_centered.T @ x_centered + alpha * np.eye(protocol.INPUT_LENGTH)
    weights = np.linalg.solve(gram, x_centered.T @ y_centered)
    bias = y_mean - x_mean @ weights
    residual = x @ weights + bias - y
    objective = float(np.sum(residual**2) / samples) + float(lam) * float(
        np.sum(weights**2)
    )
    return validate_model_payload(
        {
            "backend": "numpy",
            "solver_version": np.__version__,
            "lambda": float(lam),
            "alpha": alpha,
            "M": samples,
            "W": weights,
            "b": bias,
            "objective": objective,
            "residual_sum_squares": float(np.sum(residual**2)),
            "centered_x_mean": x_mean,
            "centered_y_mean": y_mean,
            "intercept_regularized": False,
        },
        label="numpy",
    )


def fit_sklearn(x: np.ndarray, y: np.ndarray, lam: float) -> Dict[str, Any]:
    """Fit the equivalent solution through the optional scikit-learn backend."""
    try:  # Lazy import keeps scikit-learn optional.
        import sklearn
        from sklearn.linear_model import Ridge
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RidgeError(
            "ridge backend 'sklearn' was requested but scikit-learn is not "
            "installed; install it or use --ridge-backend numpy"
        ) from exc

    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    samples = int(x.shape[0])
    alpha = float(lam) * samples
    estimator = Ridge(alpha=alpha, fit_intercept=True, solver="svd")
    estimator.fit(x, y)
    weights = np.ascontiguousarray(estimator.coef_.T)
    bias = np.asarray(estimator.intercept_, dtype=np.float64)
    residual = x @ weights + bias - y
    objective = float(np.sum(residual**2) / samples) + float(lam) * float(
        np.sum(weights**2)
    )
    # The shared artifact writer reconstructs predictions from the frozen node
    # normalization plus these centered training means, so every accepted
    # backend must supply the same payload schema as the NumPy solver.
    centered_x_mean = x.mean(axis=0)
    centered_y_mean = y.mean(axis=0)
    return validate_model_payload(
        {
            "backend": "sklearn",
            "sklearn_version": getattr(sklearn, "__version__", "unknown"),
            "lambda": float(lam),
            "alpha": alpha,
            "M": samples,
            "W": weights,
            "b": bias,
            "objective": objective,
            "residual_sum_squares": float(np.sum(residual**2)),
            "centered_x_mean": centered_x_mean,
            "centered_y_mean": centered_y_mean,
            "intercept_regularized": False,
            "equivalent_sum_loss_regularizer": "alpha = lambda * M",
        },
        label="sklearn",
    )


def predict_standardized(
    x: np.ndarray, weights: np.ndarray, bias: np.ndarray
) -> np.ndarray:
    """Apply ``x W + b`` to standardized inputs."""
    return np.asarray(x, dtype=np.float64) @ np.asarray(
        weights, dtype=np.float64
    ) + np.asarray(bias, dtype=np.float64)


def predict_from_standardized(
    standardized_inputs: np.ndarray,
    stats: TrainingStats,
    weights: np.ndarray,
    bias: np.ndarray,
) -> np.ndarray:
    """Inverse-transform predictions whose inputs are already standardized.

    Accepts either node-major ``[N, 6]`` or window-major/node-major
    ``[W*N, 6]`` standardized inputs and returns original units.
    """
    x = np.asarray(standardized_inputs, dtype=np.float64)
    if x.ndim != 2:
        raise RidgeError(f"standardized inputs must be 2-D, got shape {x.shape}")
    node_count = stats.node_count
    if x.shape[0] == node_count:
        return stats.inverse(predict_standardized(x, weights, bias))
    if node_count and x.shape[0] % node_count == 0:
        windows = x.shape[0] // node_count
        stacked = x.reshape(windows, node_count, x.shape[1])
        return stats.inverse_nodes_last(
            predict_standardized(stacked, weights, bias)
        )
    raise RidgeError(
        f"standardized input rows {x.shape[0]} are not a multiple of {node_count} nodes"
    )


def _node_axis_view(values: np.ndarray, ndim: int) -> np.ndarray:
    """Reshape a ``[N]`` vector to broadcast along axis 0 of an ``ndim`` array."""
    return np.asarray(values, dtype=np.float64).reshape(
        (-1,) + (1,) * (ndim - 1)
    )


def predict_original(
    raw_inputs: np.ndarray,
    stats: TrainingStats,
    weights: np.ndarray,
    bias: np.ndarray,
) -> np.ndarray:
    """Predict original-unit targets from raw ``[N, 6]`` inputs."""
    return predict_from_standardized(
        stats.standardize(raw_inputs), stats, weights, bias
    )


def fit_candidates(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_validation: np.ndarray,
    y_validation: np.ndarray,
    stats: TrainingStats,
    *,
    backend: str = "numpy",
    lambdas: Sequence[float] = protocol.LAMBDA_CANDIDATES,
) -> List[Dict[str, Any]]:
    """Fit every lambda and record original-unit validation scores.

    ``y_validation`` arrives standardized with the frozen node statistics, so
    it is inverse-transformed first: selection must compare original-unit
    predictions with original-unit labels.
    """
    if backend not in ("numpy", "sklearn"):
        raise RidgeError(f"unknown ridge backend {backend!r}")
    fit = fit_numpy if backend == "numpy" else fit_sklearn
    validation_gold = np.asarray(y_validation, dtype=np.float64)
    if validation_gold.ndim == 2 and validation_gold.shape[0] == stats.node_count:
        validation_gold = stats.inverse(validation_gold)
    elif validation_gold.ndim == 3 and validation_gold.shape[1] == stats.node_count:
        validation_gold = stats.inverse_nodes_last(validation_gold)
    else:
        raise RidgeError(
            f"validation targets shape {validation_gold.shape} does not match "
            f"{stats.node_count} nodes"
        )
    candidates: List[Dict[str, Any]] = []
    for lam in lambdas:
        model = fit(x_train, y_train, float(lam))
        validation_pred = predict_from_standardized(
            x_validation, stats, model["W"], model["b"]
        )
        model = dict(model)
        model["validation_predictions"] = validation_pred
        model["validation_MSE"] = baselines.mse(validation_pred, validation_gold)
        model["validation_MAE"] = baselines.mae(validation_pred, validation_gold)
        model["validation_gold_units"] = "original"
        candidates.append(model)
    return candidates


def select_lambda(candidates: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Select by validation MSE, breaking exact ties toward the larger lambda."""
    if not candidates:
        raise RidgeError("no Ridge candidates to select from")
    ordered = sorted(
        candidates,
        key=lambda row: (float(row["validation_MSE"]), -float(row["lambda"])),
    )
    winner = ordered[0]
    table = [
        {
            "lambda": float(row["lambda"]),
            "alpha": float(row["alpha"]),
            "M": int(row["M"]),
            "validation_MSE": float(row["validation_MSE"]),
            "validation_MAE": float(row["validation_MAE"]),
            "objective": float(row["objective"]),
            "backend": row["backend"],
        }
        for row in ordered
    ]
    tied = [
        float(row["lambda"])
        for row in ordered
        if float(row["validation_MSE"]) == float(winner["validation_MSE"])
    ]
    return {
        "selection_metric": "validation original-unit MSE",
        "tie_break": "larger lambda",
        "selected_lambda": float(winner["lambda"]),
        "selected_alpha": float(winner["alpha"]),
        "selected_index": list(candidates).index(winner),
        "candidate_table": table,
        "tied_lambdas": tied,
        "selected_candidate": winner,
        "test_labels_used": False,
    }


def clip_nonnegative(pred: np.ndarray) -> np.ndarray:
    """Return the separately labeled nonnegative-clipped prediction."""
    return np.maximum(np.asarray(pred, dtype=np.float64), 0.0)
