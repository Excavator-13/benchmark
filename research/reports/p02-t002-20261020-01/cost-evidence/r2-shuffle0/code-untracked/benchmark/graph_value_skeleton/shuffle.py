"""Degree-preserving shuffled control graphs inside each context.

A shuffled graph is built by directed double-edge endpoint swaps
``(a,b),(c,d) -> (a,d),(c,b)`` within one context.  Every accepted swap and the
final graph preserve each node's incoming and outgoing degree and the edge count,
and introduce no self-loop, duplicate edge or cross-context edge.  The work
budget is versioned (accept ``10*E_ctx`` swaps, try at most ``500*E_ctx`` in v2)
and the RNG is derived from ``SeedSequence([shuffle_seed, context_id...])``, so
the result depends only on the source graph identity and the shuffle seed — not
on the model seed, run ID, source row order or process hash iteration order.

A nonempty context that cannot change its final edge set, exhausts the attempt
budget or reaches the budget with an unchanged graph fails explicitly.  The
original graph is never returned labelled as shuffled, and the seed is never
silently retried.  Preserving reverse-edge symmetry is deliberately not a
constraint.
"""

from __future__ import annotations

import hashlib
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from . import graph as gvs_graph
from . import protocol

__all__ = [
    "ShuffleError",
    "ShuffledGraph",
    "shuffle_graph",
    "swap_context_edges",
    "context_seed_sequence",
    "context_edge_sha256",
]


class ShuffleError(ValueError):
    """Raised when a shuffled control cannot be produced honestly."""

    def __init__(self, message, diagnostics=None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


@dataclass
class ShuffledGraph:
    """The shuffled edge set plus its complete per-context audit."""

    data_name: str
    shuffle_seed: int
    source_edges: np.ndarray
    edges: np.ndarray
    audit: Dict[str, Any] = field(default_factory=dict)

    @property
    def edge_count(self) -> int:
        return int(self.edges.shape[0])

    @property
    def source_edges_sha256(self) -> str:
        return gvs_graph.edge_set_sha256(self.source_edges)

    @property
    def edges_sha256(self) -> str:
        return gvs_graph.edge_set_sha256(self.edges)

    def identity_payload(self) -> Dict[str, Any]:
        return {
            "data_name": self.data_name,
            "shuffle_seed": self.shuffle_seed,
            "source_edges_sha256": self.source_edges_sha256,
            "edges_sha256": self.edges_sha256,
            "edge_count": self.edge_count,
            "algorithm": protocol.SHUFFLE_ALGORITHM,
            "algorithm_version": self.audit.get("algorithm_version", protocol.SHUFFLE_VERSION),
        }


def _context_edge_sha256(
    context: Sequence[int], local_edges: np.ndarray
) -> str:
    digest = hashlib.sha256()
    digest.update(b"context:")
    digest.update(",".join(str(int(value)) for value in context).encode("ascii"))
    digest.update(b"\0")
    digest.update(b"local-int64-le:")
    digest.update(str(tuple(local_edges.shape)).encode("ascii"))
    digest.update(b"\0")
    digest.update(
        np.ascontiguousarray(local_edges.astype("<i8")).tobytes(order="C")
    )
    return digest.hexdigest()


def _context_label(context: Optional[Sequence[int]]) -> str:
    return "context" if context is None else f"context {list(int(v) for v in context)}"


def context_seed_sequence(
    shuffle_seed: int, context: Sequence[int]
) -> List[int]:
    """Derive the designed ``SeedSequence([shuffle_seed, context_id...])``.

    Design D6 specifies the context *ID* (not its ordinal position), so a
    non-dense or non-consecutive context ID selects a different local stream
    while contiguous published IDs 0..N-1 remain unchanged.
    """
    return [int(shuffle_seed), *(int(value) for value in context)]


def context_edge_sha256(
    context: Sequence[int], local_edges: np.ndarray
) -> str:
    """Hash a context's canonical local edge set (public for saved checks)."""
    array = np.asarray(local_edges, dtype=np.int64)
    if array.size == 0:
        array = np.zeros((0, 2), dtype=np.int64)
    else:
        array = array.reshape(-1, 2)
    return _context_edge_sha256(context, array)


def _swap_edges(
    local_edges: List[Tuple[int, int]],
    *,
    seed_sequence: Sequence[int],
    accept_factor: int,
    attempt_factor: int,
    context: Optional[Sequence[int]] = None,
    proposal_batch_size: int = protocol.SHUFFLE_PROPOSAL_BATCH,
    progress=None,
    backend: str = "set",
) -> Dict[str, Any]:
    """Run the deterministic double-edge swap budget for one context.

    The local edge list is canonicalized (sorted by source then target) before
    the first proposal, so the stream depends only on the context identity, the
    shuffle seed and the source edge set -- never on the caller's row order.
    """
    label = _context_label(context)
    for name, value in (("accept_factor", accept_factor), ("attempt_factor", attempt_factor),
                        ("proposal_batch_size", proposal_batch_size)):
        if type(value) is not int or value <= 0:
            raise ShuffleError(f"{name} must be a positive integer")
    if backend not in ("set", "dense"):
        raise ShuffleError(f"unknown membership backend {backend!r}")
    started = time.perf_counter()
    edges: List[Tuple[int, int]] = sorted(
        (int(source), int(target)) for source, target in local_edges
    )
    edge_count = len(edges)
    if edge_count == 0:
        return {
            "edge_count": 0,
            "empty": True,
            "target_accepted": 0,
            "attempts": 0,
            "accepted": 0,
            "rejections": {},
            "unchanged": True,
        }
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(list(seed_sequence))))
    target_accepted = accept_factor * edge_count
    attempt_limit = attempt_factor * edge_count
    edge_set = set(edges)
    original = set(edges)
    rejections: Counter = Counter()
    attempts = 0
    accepted = 0
    # Only active local endpoints are compacted, preserving canonical edge order.
    active = sorted({node for edge in edges for node in edge}) if backend == "dense" else []
    dense_bytes = len(active) ** 2
    if backend == "dense" and dense_bytes > 16 * 1024 * 1024:
        raise ShuffleError("active adjacency exceeds the 16 MiB backend bound")
    inverse = {node: index for index, node in enumerate(active)}
    adjacency = np.zeros((len(active), len(active)), dtype=np.bool_) if active else None
    if adjacency is not None:
        for a, b in edges:
            adjacency[inverse[a], inverse[b]] = True

    def snapshot(reason=None):
        return {"context": list(context) if context is not None else None,
                "seed_sequence": list(seed_sequence), "edge_count": edge_count,
                "target_accepted": target_accepted, "attempt_limit": attempt_limit,
                "attempts": attempts, "accepted": accepted,
                "rejections": dict(sorted(rejections.items())),
                "elapsed_seconds": time.perf_counter() - started, "reason": reason}

    def fail(message):
        raise ShuffleError(message, snapshot(message))

    if progress is not None:
        progress(snapshot())
    if edge_count < 2:
        fail(f"{label} has a single edge ({edge_count}); no legal endpoint swap exists")
    proposals = np.zeros((0, 2), dtype=np.int64)
    cursor = 0
    while accepted < target_accepted and attempts < attempt_limit:
        if attempts and attempts % 100000 == 0 and progress is not None:
            progress(snapshot())
        if cursor == len(proposals):
            proposals = rng.integers(0, edge_count, size=(proposal_batch_size, 2))
            cursor = 0
        attempts += 1
        pair = proposals[cursor]
        cursor += 1
        first_index, second_index = int(pair[0]), int(pair[1])
        if first_index == second_index:
            rejections["same_edge_index"] += 1
            continue
        a, b = edges[first_index]
        c, d = edges[second_index]
        if a == d or c == b:
            rejections["self_loop"] += 1
            continue
        first = (a, d)
        second = (c, b)
        if first == second:
            rejections["coincident_new_edges"] += 1
            continue
        exists = (first in edge_set or second in edge_set) if adjacency is None else (
            adjacency[inverse[a], inverse[d]] or adjacency[inverse[c], inverse[b]])
        if exists:
            rejections["existing_edge"] += 1
            continue
        edge_set.discard((a, b))
        edge_set.discard((c, d))
        edge_set.add(first)
        edge_set.add(second)
        if adjacency is not None:
            adjacency[inverse[a], inverse[b]] = False
            adjacency[inverse[c], inverse[d]] = False
            adjacency[inverse[a], inverse[d]] = True
            adjacency[inverse[c], inverse[b]] = True
        edges[first_index] = first
        edges[second_index] = second
        accepted += 1
    if accepted < target_accepted:
        fail(
            f"{label}: attempt budget exhausted: accepted {accepted} of "
            f"{target_accepted} swaps within {attempt_limit} attempts"
        )
    unchanged = edge_set == original
    if unchanged:
        fail(
            f"{label}: the final edge set equals the original graph; refusing to "
            "label an unchanged graph as shuffled"
        )
    result_edges = np.asarray(sorted(edge_set), dtype=np.int64)
    if progress is not None:
        progress(snapshot())
    return {
        "edge_count": edge_count,
        "empty": False,
        "target_accepted": target_accepted,
        "attempt_limit": attempt_limit,
        "attempts": attempts,
        "accepted": accepted,
        "rejections": dict(sorted(rejections.items())),
        "unchanged": unchanged,
        "result_edges": result_edges,
    }


def swap_context_edges(
    local_edges: Sequence[Sequence[int]],
    *,
    seed_sequence: Sequence[int],
    accept_factor: int = protocol.SHUFFLE_ACCEPT_FACTOR,
    attempt_factor: int = protocol.SHUFFLE_ATTEMPT_LIMIT_FACTOR,
    context: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    """Public single-context swap helper used by unit tests."""
    edges = [(int(source), int(target)) for source, target in local_edges]
    return _swap_edges(
        edges,
        seed_sequence=seed_sequence,
        accept_factor=accept_factor,
        attempt_factor=attempt_factor,
        context=context,
    )


def shuffle_graph(
    data_name: str,
    key_array: np.ndarray,
    edges: np.ndarray,
    shuffle_seed: int,
    *,
    accept_factor: int = protocol.SHUFFLE_ACCEPT_FACTOR,
    attempt_factor: int = protocol.SHUFFLE_ATTEMPT_LIMIT_FACTOR,
    progress=None,
) -> ShuffledGraph:
    """Build a context-local degree-preserving shuffled control graph."""
    protocol.validate_dataset_name(data_name)
    if shuffle_seed not in protocol.SHUFFLE_SEEDS:
        raise ShuffleError(
            f"shuffle seed {shuffle_seed} is outside {list(protocol.SHUFFLE_SEEDS)}"
        )
    source = gvs_graph.canonical_edge_array(edges)
    layout = gvs_graph.context_layout(key_array, source)
    result_blocks: List[np.ndarray] = []
    contexts: List[Dict[str, Any]] = []
    total_attempts = 0
    total_accepted = 0
    started = time.perf_counter()
    identity = {"data_name": data_name, "shuffle_seed": int(shuffle_seed),
                "algorithm_version": protocol.SHUFFLE_VERSION,
                "source_edges_sha256": gvs_graph.edge_set_sha256(source),
                "node_keys_sha256": gvs_graph.node_keys_sha256(key_array)}

    def publish(current):
        payload = {**identity, "completed_contexts": list(contexts),
                   "current": current, "elapsed_seconds": time.perf_counter() - started}
        if progress is not None:
            progress(payload)
        return payload
    for ordinal, context in enumerate(layout.contexts):
        node_indices = layout.node_indices[context]
        positions = layout.edge_indices[context]
        if positions.size == 0:
            local_edges: List[Tuple[int, int]] = []
        else:
            local = source[positions]
            inverse = {int(value): index for index, value in enumerate(node_indices.tolist())}
            local_edges = [
                (inverse[int(source_node)], inverse[int(target_node)])
                for source_node, target_node in local.tolist()
            ]
        original_local = list(local_edges)
        seed_sequence = context_seed_sequence(shuffle_seed, context)
        try:
            result = _swap_edges(
                local_edges, seed_sequence=seed_sequence, accept_factor=accept_factor,
                attempt_factor=attempt_factor, context=context, progress=publish,
            )
        except ShuffleError as exc:
            exc.diagnostics = publish(exc.diagnostics)
            raise
        if result["empty"]:
            contexts.append(
                {
                    "context": list(context),
                    "ordinal": ordinal,
                    "seed_sequence": list(seed_sequence),
                    "nodes": int(node_indices.shape[0]),
                    "edge_count": 0,
                    "empty": True,
                    "attempts": 0,
                    "accepted": 0,
                    "target_accepted": 0,
                    "rejections": {},
                    "changed_edges": 0,
                    "changed_fraction": None,
                    "intersection_edges": 0,
                    "symmetric_difference_edges": 0,
                }
            )
            publish({"context": list(context), "empty": True})
            continue
        local_result = result["result_edges"]
        result_blocks.append(node_indices[local_result.reshape(-1)].reshape(-1, 2))
        original_edges = set(original_local)
        result_set = {tuple(int(value) for value in row) for row in local_result.tolist()}
        intersection = original_edges & result_set
        removed = original_edges - result_set
        added = result_set - original_edges
        symmetric_difference = original_edges ^ result_set
        total_attempts += int(result["attempts"])
        total_accepted += int(result["accepted"])
        contexts.append(
            {
                "context": list(context),
                "ordinal": ordinal,
                "seed_sequence": list(seed_sequence),
                "nodes": int(node_indices.shape[0]),
                "edge_count": int(result["edge_count"]),
                "empty": False,
                "attempts": int(result["attempts"]),
                "accepted": int(result["accepted"]),
                "target_accepted": int(result["target_accepted"]),
                "attempt_limit": int(result["attempt_limit"]),
                "rejections": dict(result["rejections"]),
                "changed_edges": int(len(removed)),
                "added_edges": int(len(added)),
                "changed_fraction": (
                    float(len(removed)) / float(len(original_edges))
                    if original_edges
                    else None
                ),
                "intersection_edges": int(len(intersection)),
                "intersection_fraction": (
                    float(len(intersection)) / float(len(original_edges))
                    if original_edges
                    else None
                ),
                "symmetric_difference_edges": int(len(symmetric_difference)),
                "symmetric_difference_fraction": (
                    float(len(symmetric_difference)) / float(2 * len(original_edges))
                    if original_edges
                    else None
                ),
                "source_edges_sha256": _context_edge_sha256(
                    context,
                    np.asarray(sorted(original_edges), dtype=np.int64),
                ),
                "result_edges_sha256": _context_edge_sha256(context, local_result),
            }
        )
        publish({"context": list(context), "complete": True})
    result_edges = (
        gvs_graph.canonical_edge_array(np.concatenate(result_blocks, axis=0))
        if result_blocks
        else np.zeros((0, 2), dtype=np.int64)
    )
    if result_edges.shape[0] != source.shape[0]:
        raise ShuffleError(
            f"shuffled edge count {result_edges.shape[0]} != source {source.shape[0]}"
        )
    if result_edges.shape[0] and bool((result_edges[:, 0] == result_edges[:, 1]).any()):
        raise ShuffleError("shuffled graph contains a self-loop")
    # Re-assert per-node in/out degree, context locality and uniqueness.
    _assert_preserved(data_name, key_array, source, result_edges)
    audit = {
        "algorithm": protocol.SHUFFLE_ALGORITHM,
        "algorithm_version": protocol.SHUFFLE_VERSION,
        "shuffle_seed": int(shuffle_seed),
        "seed_derivation": "PCG64(SeedSequence([shuffle_seed, context_id...]))",
        "accept_target_factor": int(accept_factor),
        "attempt_limit_factor": int(attempt_factor),
        "target_rule": f"accept {accept_factor}*E_ctx swaps, attempt at most {attempt_factor}*E_ctx",
        "proposal_batch_size": protocol.SHUFFLE_PROPOSAL_BATCH,
        "contexts": contexts,
        "totals": {
            "contexts": len(contexts),
            "nonempty_contexts": sum(1 for entry in contexts if not entry["empty"]),
            "empty_contexts": sum(1 for entry in contexts if entry["empty"]),
            "attempts": total_attempts,
            "accepted": total_accepted,
            "edges": int(result_edges.shape[0]),
        },
        "source_edges_sha256": gvs_graph.edge_set_sha256(source),
        "result_edges_sha256": gvs_graph.edge_set_sha256(result_edges),
        "node_keys_sha256": gvs_graph.node_keys_sha256(key_array),
        "changed_edges": int(
            sum(entry["changed_edges"] for entry in contexts)
        ),
        "model_rng_consumed": False,
        "process_hash_iteration_used": False,
        "preserves_reverse_edge_symmetry": False,
        "symmetry_is_not_a_shuffle_constraint": True,
        "degree_summary": _degree_summary(key_array, source, result_edges),
        "uniform_sampling_claimed": False,
    }
    return ShuffledGraph(
        data_name=data_name,
        shuffle_seed=int(shuffle_seed),
        source_edges=source,
        edges=result_edges,
        audit=audit,
    )


def _degree_summary(
    key_array: np.ndarray, source: np.ndarray, result: np.ndarray
) -> Dict[str, Any]:
    node_count = int(np.asarray(key_array).shape[0])
    summary: Dict[str, Any] = {}
    for label, edges in (("source", source), ("result", result)):
        incoming = np.bincount(edges[:, 1], minlength=node_count) if edges.size else np.zeros(node_count)
        outgoing = np.bincount(edges[:, 0], minlength=node_count) if edges.size else np.zeros(node_count)
        summary[label] = {
            "in_degree_sum": int(incoming.sum()),
            "out_degree_sum": int(outgoing.sum()),
            "max_in_degree": int(incoming.max()) if node_count else 0,
            "max_out_degree": int(outgoing.max()) if node_count else 0,
            "isolated_incoming_nodes": int((incoming == 0).sum()),
        }
    return summary


def _assert_preserved(
    data_name: str, key_array: np.ndarray, source: np.ndarray, result: np.ndarray
) -> None:
    """Assert degree preservation, context locality and binary uniqueness."""
    node_count = int(np.asarray(key_array).shape[0])
    for label, edges in (("source", source), ("result", result)):
        if edges.shape[0] == 0:
            continue
        if edges.shape[1] != 2:
            raise ShuffleError(f"{label}: edges must be [E, 2]")
    if source.shape[0] and result.shape[0]:
        source_in = np.bincount(source[:, 1], minlength=node_count)
        result_in = np.bincount(result[:, 1], minlength=node_count)
        source_out = np.bincount(source[:, 0], minlength=node_count)
        result_out = np.bincount(result[:, 0], minlength=node_count)
        if not np.array_equal(source_in, result_in) or not np.array_equal(
            source_out, result_out
        ):
            raise ShuffleError(
                "shuffled graph changed at least one node's in/out degree"
            )
    if result.shape[0] != np.unique(result, axis=0).shape[0]:
        raise ShuffleError("shuffled graph contains a duplicate edge")
    keys = np.asarray(key_array, dtype=np.int64)
    node_context = [tuple(int(value) for value in row[:-1]) for row in keys.tolist()]
    for source_node, target_node in result.tolist():
        if node_context[int(source_node)] != node_context[int(target_node)]:
            raise ShuffleError(
                f"{data_name}: shuffled edge {source_node}->{target_node} crosses contexts"
            )
