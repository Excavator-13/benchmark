"""Fixed 200-epoch training, chunked full-batch accumulation and selection.

Every epoch covers exactly the 19 training windows and all nodes/horizons with
equal element weighting.  Chunks follow ascending window then ascending context
and always carry a context's complete adjacency, so accumulating
``squared_error_sum / global_element_count`` gradients and stepping once is
mathematically the global mean-squared-error gradient (not a per-chunk step and
not a re-weighting by context size).  There is no scheduler, early stopping,
clipping or preprocessing search.  Validation MSE in original units selects the
checkpoint, with exact ties resolved to the earliest epoch; test labels never
reach this interface.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import torch

from . import model as gvs_model
from . import protocol
from .graph import ContextLayout, canonical_edge_array

__all__ = [
    "TrainingError",
    "Chunk",
    "TrainingResult",
    "build_chunks",
    "chunk_global_edges",
    "train",
    "selected_predictions",
    "configure_determinism",
]


class TrainingError(RuntimeError):
    """Raised when the fixed training budget or selection cannot be honoured."""


def configure_determinism(model_seed: int) -> Dict[str, Any]:
    """Pin seeds, threads and deterministic algorithms before model creation.

    BLAS thread environment variables are set by the launcher/worker before
    numerical libraries are imported; here the torch intra/inter-op pools and
    deterministic algorithms are pinned, and Python/NumPy/torch seeds are set to
    the model seed so paired method branches start from identical parameters.
    """
    import os
    import random

    import numpy as np

    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        os.environ.setdefault(variable, "1")
    random.seed(int(model_seed))
    np.random.seed(int(model_seed))
    torch.manual_seed(int(model_seed))
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    interop: Optional[int]
    try:
        torch.set_num_interop_threads(1)
        interop = 1
    except RuntimeError:  # pragma: no cover - already parallelized
        interop = torch.get_num_interop_threads()
    return {
        "python_seed": int(model_seed),
        "numpy_seed": int(model_seed),
        "torch_seed": int(model_seed),
        "torch_deterministic_algorithms": True,
        "torch_intra_op_threads": int(torch.get_num_threads()),
        "torch_inter_op_threads": int(interop),
        "blas_thread_environment": {
            name: os.environ.get(name)
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS",
            )
        },
        "device": "cpu",
    }


@dataclass(frozen=True)
class Chunk:
    """One (window, context) training block with complete local adjacency."""

    window_index: int
    window_start: int
    context: Tuple[int, ...]
    node_indices: torch.Tensor
    aggregation: gvs_model.GraphAggregation
    element_count: int


@dataclass
class TrainingResult:
    history: List[Dict[str, Any]]
    selected_epoch: int
    selected_validation_mse: float
    selected_state: Dict[str, Any]
    epochs: int
    total_elements: int
    chunk_count: int
    optimizer: Dict[str, Any]
    training_seconds: float
    validation_seconds: float
    selection_payload: Dict[str, Any] = field(default_factory=dict)


def build_chunks(
    layout: ContextLayout,
    *,
    node_count: int,
) -> List[Chunk]:
    """Precompute the deterministic ascending window/context training chunks."""
    chunks: List[Chunk] = []
    for window_index, window_start in enumerate(protocol.TRAIN_STARTS):
        for context in layout.contexts:
            node_indices = torch.as_tensor(
                layout.node_indices[context], dtype=torch.int64
            )
            aggregation = gvs_model.GraphAggregation(
                source=torch.as_tensor(
                    layout.edge_source_local[context], dtype=torch.int64
                ),
                target=torch.as_tensor(
                    layout.edge_target_local[context], dtype=torch.int64
                ),
                node_count=int(node_indices.numel()),
                label=f"window {window_start} context {list(context)}",
            )
            chunks.append(
                Chunk(
                    window_index=window_index,
                    window_start=int(window_start),
                    context=tuple(int(value) for value in context),
                    node_indices=node_indices,
                    aggregation=aggregation,
                    element_count=int(node_indices.numel()) * protocol.HORIZON,
                )
            )
    covered = sum(chunk.element_count for chunk in chunks)
    if covered != len(protocol.TRAIN_STARTS) * int(node_count) * protocol.HORIZON:
        raise TrainingError(
            f"training chunks cover {covered} elements, expected "
            f"{len(protocol.TRAIN_STARTS) * int(node_count) * protocol.HORIZON}"
        )
    return chunks


def chunk_global_edges(chunks: Sequence[Chunk]) -> Dict[int, Any]:
    """Convert every training chunk's local edges to canonical global indices.

    The return value maps every training window index to its actual canonical
    ``int64 [E, 2]`` adjacency.  Reconstructing the global edge set from the
    chunks is what lets a run (or a test) prove that training used the method's
    message graph rather than a different saved graph.
    """
    import numpy as np

    per_window: Dict[int, List[Any]] = {}
    for chunk in chunks:
        node_indices = chunk.node_indices.detach().cpu().numpy().astype(np.int64)
        source = chunk.aggregation.source.detach().cpu().numpy().astype(np.int64)
        target = chunk.aggregation.target.detach().cpu().numpy().astype(np.int64)
        if source.size:
            edges = np.stack(
                [node_indices[source], node_indices[target]], axis=1
            )
        else:
            edges = np.zeros((0, 2), dtype=np.int64)
        per_window.setdefault(int(chunk.window_index), []).append(edges)
    result: Dict[int, Any] = {}
    for window_index, blocks in sorted(per_window.items()):
        combined = (
            np.concatenate(blocks, axis=0)
            if blocks
            else np.zeros((0, 2), dtype=np.int64)
        )
        result[int(window_index)] = canonical_edge_array(combined)
    return result


def _to_tensor(array: Any) -> torch.Tensor:
    return torch.as_tensor(array, dtype=torch.float32)


def train(
    model: gvs_model.SkeletonModel,
    *,
    train_inputs: Any,
    train_targets: Any,
    validation_inputs: Any,
    validation_targets: Any,
    chunks: Sequence[Chunk],
    validation_aggregation: Optional[gvs_model.GraphAggregation],
    epochs: int = protocol.EPOCHS,
    node_count: int,
    resume_state: Optional[Mapping[str, Any]] = None,
    checkpoint_callback: Any = None,
    progress_callback: Any = None,
) -> TrainingResult:
    """Run exactly ``epochs`` epochs and select the validation-MSE checkpoint."""
    if int(epochs) != protocol.EPOCHS:
        raise TrainingError(
            f"the frozen budget is {protocol.EPOCHS} epochs, got {epochs}"
        )
    train_x = _to_tensor(train_inputs)
    train_y = _to_tensor(train_targets)
    validation_x = _to_tensor(validation_inputs)
    validation_y = _to_tensor(validation_targets)
    if train_x.shape[0] != len(protocol.TRAIN_STARTS):
        raise TrainingError(
            f"training windows {train_x.shape[0]} != {len(protocol.TRAIN_STARTS)}"
        )
    total_elements = (
        len(protocol.TRAIN_STARTS) * int(node_count) * protocol.HORIZON
    )
    coverage = sum(chunk.element_count for chunk in chunks)
    if coverage != total_elements:
        raise TrainingError(
            f"chunk elements {coverage} != global training elements {total_elements}"
        )
    validation_elements = (
        int(validation_x.shape[0]) * int(node_count) * protocol.HORIZON
    )
    optimizer = torch.optim.Adam(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=float(protocol.ADAM["lr"]),
        betas=tuple(float(value) for value in protocol.ADAM["betas"]),
        eps=float(protocol.ADAM["eps"]),
        weight_decay=float(protocol.ADAM["weight_decay"]),
        amsgrad=bool(protocol.ADAM["amsgrad"]),
    )
    history: List[Dict[str, Any]] = []
    best_epoch = 0
    best_validation_mse = float("inf")
    best_state: Dict[str, Any] = {}
    training_seconds = 0.0
    validation_seconds = 0.0
    completed_epoch = 0
    if resume_state is not None:
        from . import checkpoints
        checkpoints.validate_state(resume_state, model, optimizer,
                                   train_elements=total_elements, validation_elements=validation_elements)
        model.load_state_dict(resume_state['model'])
        optimizer.load_state_dict(resume_state['optimizer'])
        history = list(resume_state['history'])
        best_epoch = resume_state['best_epoch']
        best_validation_mse = resume_state['best_mse']
        best_state = resume_state['best_state']
        training_seconds = resume_state['training_seconds']
        validation_seconds = resume_state['validation_seconds']
        completed_epoch = resume_state['epoch']
        checkpoints.restore_rng(resume_state['rng'])
    for epoch in range(completed_epoch + 1, int(epochs) + 1):
        epoch_started = time.perf_counter()
        started = time.perf_counter()
        model.train()
        optimizer.zero_grad(set_to_none=True)
        squared_sum = 0.0
        absolute_sum = 0.0
        last_progress = 0.0
        for chunk_index, chunk in enumerate(chunks):
            if progress_callback and (time.perf_counter() - last_progress >= 10):
                progress_callback({'stage': 'training', 'epoch_in_progress': epoch,
                                   'completed_chunks': chunk_index, 'total_chunks': len(chunks)})
                last_progress = time.perf_counter()
            x = train_x[chunk.window_index].index_select(0, chunk.node_indices)
            y = train_y[chunk.window_index].index_select(0, chunk.node_indices)
            prediction = model(x, chunk.aggregation)
            difference = prediction - y
            squared = torch.square(difference)
            chunk_squared = squared.sum()
            if not bool(torch.isfinite(chunk_squared)):
                raise TrainingError(
                    f"epoch {epoch}: non-finite squared error in chunk "
                    f"window {chunk.window_start} context {list(chunk.context)}"
                )
            (chunk_squared / float(total_elements)).backward()
            squared_sum += float(chunk_squared.detach().double())
            absolute_sum += float(difference.detach().double().abs().sum())
        parameters = [p for p in model.parameters() if p.grad is not None]
        for parameter in parameters:
            if not bool(torch.isfinite(parameter.grad).all()):
                raise TrainingError(f"epoch {epoch}: non-finite gradient")
        optimizer.step()
        training_seconds += time.perf_counter() - started

        if progress_callback:
            progress_callback({'stage': 'validation', 'epoch_in_progress': epoch})

        started = time.perf_counter()
        model.eval()
        with torch.no_grad():
            prediction = gvs_model.predict_windows(
                model, validation_x, validation_aggregation
            )
            difference = prediction.double() - validation_y.double()
            validation_squared = float(torch.square(difference).sum())
            validation_absolute = float(difference.abs().sum())
        validation_seconds += time.perf_counter() - started
        validation_mse = validation_squared / float(validation_elements)
        validation_mae = validation_absolute / float(validation_elements)
        train_mse = squared_sum / float(total_elements)
        train_mae = absolute_sum / float(total_elements)
        if not all(
            value == value and abs(value) != float("inf")
            for value in (train_mse, train_mae, validation_mse, validation_mae)
        ):
            raise TrainingError(f"epoch {epoch}: non-finite recorded score")
        if validation_mse < best_validation_mse:
            best_validation_mse = validation_mse
            best_epoch = epoch
            best_state = {
                name: tensor.detach().clone()
                for name, tensor in model.state_dict().items()
            }
        history.append(
            {
                "epoch": epoch,
                "train_elements": int(total_elements),
                "train_MSE_original_units_before_update": train_mse,
                "train_MAE_original_units_before_update": train_mae,
                "validation_elements": int(validation_elements),
                "validation_MSE_original_units_after_update": validation_mse,
                "validation_MAE_original_units_after_update": validation_mae,
                "optimizer_step": epoch,
                "selected_so_far": epoch == best_epoch,
            }
        )
        if checkpoint_callback:
            from . import checkpoints
            checkpoint_callback({
                'epoch': epoch, 'model': model.state_dict(),
                'optimizer': optimizer.state_dict(), 'rng': checkpoints.rng_state(),
                'history': history, 'best_epoch': best_epoch,
                'best_mse': best_validation_mse, 'best_state': best_state,
                'training_seconds': training_seconds, 'validation_seconds': validation_seconds,
            }, time.perf_counter() - epoch_started)
    if len(history) != protocol.EPOCHS:
        raise TrainingError(
            f"history has {len(history)} epochs, expected {protocol.EPOCHS}"
        )
    if best_epoch == 0:
        raise TrainingError("no validation epoch produced a finite MSE")
    selection = {
        "selection_metric": "validation MSE (original units)",
        "measurement_timing": (
            "validation scores are measured after the epoch's single optimizer "
            "step; training scores are measured over the pre-update epoch pass"
        ),
        "epochs_completed": int(epochs),
        "selected_epoch": int(best_epoch),
        "selected_validation_MSE": float(best_validation_mse),
        "tie_break": "earliest epoch on an exact validation-MSE tie",
        "selected_is_earliest_minimum": _earliest_minimum(history) == best_epoch,
        "test_labels_used_for_selection": False,
        "test_labels_available_to_training": False,
        "scheduler": None,
        "early_stopping": False,
        "gradient_clipping": None,
        "training_windows": list(protocol.TRAIN_STARTS),
        "training_elements_per_epoch": int(total_elements),
        "chunks_per_epoch": len(chunks),
        "chunk_order": (
            "ascending training window start, then ascending context; each chunk "
            "carries the complete context adjacency"
        ),
        "optimizer": {
            "name": "Adam",
            "lr": float(protocol.ADAM["lr"]),
            "betas": [float(v) for v in protocol.ADAM["betas"]],
            "eps": float(protocol.ADAM["eps"]),
            "weight_decay": float(protocol.ADAM["weight_decay"]),
            "amsgrad": bool(protocol.ADAM["amsgrad"]),
            "steps_per_epoch": 1,
            "total_steps": int(epochs),
        },
        "loss": protocol.LOSS,
    }
    return TrainingResult(
        history=history,
        selected_epoch=int(best_epoch),
        selected_validation_mse=float(best_validation_mse),
        selected_state=best_state,
        epochs=int(epochs),
        total_elements=int(total_elements),
        chunk_count=len(chunks),
        optimizer=selection["optimizer"],
        training_seconds=training_seconds,
        validation_seconds=validation_seconds,
        selection_payload=selection,
    )


def _earliest_minimum(history: Sequence[Mapping[str, Any]]) -> int:
    best_epoch = 0
    best_value = float("inf")
    for row in history:
        value = float(row["validation_MSE_original_units_after_update"])
        if value < best_value:
            best_value = value
            best_epoch = int(row["epoch"])
    return best_epoch


def selected_predictions(
    model: gvs_model.SkeletonModel,
    state: Mapping[str, Any],
    *,
    validation_inputs: Any,
    test_inputs: Any,
    validation_aggregation: Optional[gvs_model.GraphAggregation],
    test_aggregation: Optional[gvs_model.GraphAggregation],
) -> Tuple[Any, Any]:
    """Load the selected numerical parameters and predict both splits."""
    for name, tensor in state.items():
        model.state_dict()[name].copy_(tensor)
    model.eval()
    validation = gvs_model.predict_windows(
        model, _to_tensor(validation_inputs), validation_aggregation
    )
    test = gvs_model.predict_windows(
        model, _to_tensor(test_inputs), test_aggregation
    )
    return validation.detach().cpu().numpy(), test.detach().cpu().numpy()
