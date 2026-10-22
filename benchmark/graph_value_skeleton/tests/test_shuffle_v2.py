"""Buffered sequential swaps agree with an independent scalar oracle."""
import unittest
from collections import Counter
import numpy as np
from benchmark.graph_value_skeleton import shuffle, protocol


def scalar(edges, seed, target_factor=10, limit_factor=500):
    edges = sorted(edges)
    present = set(edges)
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed)))
    accepted = attempts = 0
    rejected = Counter()
    while accepted < target_factor * len(edges) and attempts < limit_factor * len(edges):
        i, j = map(int, rng.integers(0, len(edges), size=2))
        attempts += 1
        if i == j:
            rejected['same_edge_index'] += 1
            continue
        a, b = edges[i]; c, d = edges[j]
        if a == d or c == b:
            rejected['self_loop'] += 1
            continue
        first, second = (a, d), (c, b)
        if first == second:
            rejected['coincident_new_edges'] += 1
            continue
        if first in present or second in present:
            rejected['existing_edge'] += 1
            continue
        present.remove((a, b)); present.remove((c, d))
        present.update((first, second))
        edges[i], edges[j] = first, second
        accepted += 1
    return np.asarray(sorted(present)), attempts, accepted, dict(rejected)


class ShuffleV2Test(unittest.TestCase):
    def test_contracts_and_invalid_arguments(self):
        self.assertEqual(protocol.shuffle_contract('dds-v1')['attempt_limit_factor'], 100)
        self.assertEqual(protocol.shuffle_contract('dds-v2')['attempt_limit_factor'], 500)
        with self.assertRaises(ValueError): protocol.shuffle_contract('unknown')
        for argument in ('accept_factor', 'attempt_factor', 'proposal_batch_size'):
            for invalid in (0, -1, True, 1.5):
                kwargs = dict(seed_sequence=[0], accept_factor=10, attempt_factor=500)
                kwargs[argument] = invalid
                with self.assertRaises(shuffle.ShuffleError):
                    shuffle._swap_edges([(0, 1), (2, 3)], **kwargs)

    def test_exact_scalar_stream_decisions_and_backends(self):
        edges = [(i, (i + 1) % 11) for i in range(11)]
        edges += [(i, (i + 3) % 11) for i in range(6)]
        for seed in (0, 1, 2):
            expected, attempts, accepted, rejected = scalar(edges, [seed, 17])
            for backend in ('set', 'dense'):
                for size in (1, 7, 4096):
                    result = shuffle._swap_edges(edges, seed_sequence=[seed, 17],
                        accept_factor=10, attempt_factor=500, proposal_batch_size=size, backend=backend)
                    np.testing.assert_array_equal(result['result_edges'], expected)
                    self.assertEqual((result['attempts'], result['accepted'], result['rejections']),
                                     (attempts, accepted, rejected))

    def test_failure_accounting_progress_and_previous_context(self):
        progress = []
        with self.assertRaises(shuffle.ShuffleError) as caught:
            shuffle._swap_edges([(0, 1), (2, 3)], seed_sequence=[0], accept_factor=10,
                                attempt_factor=1, context=[12], progress=progress.append)
        current = caught.exception.diagnostics
        self.assertEqual(current['attempts'], 2)
        self.assertEqual(current['accepted'] + sum(current['rejections'].values()), 2)
        self.assertEqual(current['context'], [12])
        self.assertTrue(progress)
        keys = np.array([(c, n) for c in (1, 17) for n in range(11)], dtype=np.int64)
        edges = np.array([(i, (i+1)%11) for i in range(11)] + [(11, 12)])
        with self.assertRaises(shuffle.ShuffleError) as caught:
            shuffle.shuffle_graph('r2', keys, edges, 0, progress=progress.append)
        diagnostic = caught.exception.diagnostics
        self.assertEqual(diagnostic['completed_contexts'][0]['context'], [1])
        self.assertEqual(diagnostic['current']['context'], [17])
        self.assertEqual(diagnostic['current']['target_accepted'], 10)

    def test_long_context_checkpoints(self):
        progress = []
        complete = [(i,j) for i in range(18) for j in range(18) if i != j]
        with self.assertRaises(shuffle.ShuffleError):
            shuffle._swap_edges(complete, seed_sequence=[0], accept_factor=10,
                                attempt_factor=500, progress=progress.append)
        self.assertIn(100000, [p['attempts'] for p in progress])

    def test_empty_and_unchanged(self):
        self.assertTrue(shuffle._swap_edges([], seed_sequence=[0], accept_factor=10, attempt_factor=500)['empty'])
        with self.assertRaisesRegex(shuffle.ShuffleError, 'equals the original'):
            shuffle._swap_edges([(0,1),(2,3)], seed_sequence=[0], accept_factor=2, attempt_factor=500)
