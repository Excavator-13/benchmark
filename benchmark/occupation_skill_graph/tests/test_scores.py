"""Hand-computable candidate scores, deterministic ties and union graphs."""

from __future__ import annotations

import unittest

import numpy as np

from benchmark.occupation_skill_graph import protocol, scores
from benchmark.occupation_skill_graph.tests import fixtures as fx


def _x(rows) -> np.ndarray:
    return np.asarray(rows, dtype=np.float64)


class HandScoreTests(unittest.TestCase):
    def test_hand_computable_candidate_differences(self) -> None:
        x = _x(
            [
                [1.0, 1.0, 0.0],  # A
                [2.0, 0.0, 0.0],  # B
                [0.0, 0.0, 0.0],  # C
            ]
        )
        support = x > 0
        self.assertAlmostEqual(scores.jaccard_pair(x, support, 0, 1), 0.5)
        totals = x.sum(axis=1, keepdims=True)
        profiles = np.divide(
            x, totals, out=np.zeros_like(x), where=totals > 0
        )
        self.assertAlmostEqual(
            scores.cosine_pair(profiles, 0, 1), 1.0 / np.sqrt(2.0)
        )
        jaccard = scores.compute_candidate("jaccard", x, support)
        cosine = scores.compute_candidate("cosine", x, support)
        self.assertEqual(jaccard.selection_index.shape[0], 3)
        self.assertEqual(cosine.selection_index.shape[0], 3)
        np.testing.assert_allclose(
            jaccard.edge_score[jaccard.edge_index.tolist().index([0, 1])], 0.5
        )
        index = [tuple(pair) for pair in cosine.edge_index.tolist()].index((0, 1))
        np.testing.assert_allclose(
            cosine.edge_score[index], 1.0 / np.sqrt(2.0), rtol=1e-12
        )
        # Inactive C remains a node with no positive relation.
        self.assertEqual(cosine.n_nodes, 3)
        self.assertEqual(int(cosine.degree[2]), 0)
        self.assertEqual(int(jaccard.degree[2]), 0)

    def test_disjoint_support_scores_zero(self) -> None:
        x = _x([[1.0, 0.0], [0.0, 2.0]])
        support = x > 0
        self.assertEqual(scores.jaccard_pair(x, support, 0, 1), 0.0)
        totals = x.sum(axis=1, keepdims=True)
        profiles = np.divide(
            x, totals, out=np.zeros_like(x), where=totals > 0
        )
        self.assertEqual(scores.cosine_pair(profiles, 0, 1), 0.0)
        graph = scores.compute_candidate("jaccard", x, support)
        self.assertEqual(graph.n_edges, 0)

    def test_cosine_scale_invariance(self) -> None:
        x = _x([[1.0, 2.0, 0.0], [3.0, 1.0, 1.0], [0.0, 0.0, 0.0]])
        support = x > 0
        scaled = x * 3.5
        left = scores.compute_candidate("cosine", x, support)
        right = scores.compute_candidate("cosine", scaled, scaled > 0)
        np.testing.assert_array_equal(left.selection_index, right.selection_index)
        np.testing.assert_array_equal(left.edge_index, right.edge_index)
        np.testing.assert_allclose(
            left.edge_score, right.edge_score, rtol=1e-12, atol=1e-12
        )

    def test_scores_are_symmetric(self) -> None:
        x = _x([[1.0, 2.0, 0.0], [3.0, 1.0, 1.0], [0.5, 0.0, 0.0]])
        support = x > 0
        jaccard = scores.compute_candidate("jaccard", x, support)
        cosine = scores.compute_candidate("cosine", x, support)
        for graph in (jaccard, cosine):
            for left in range(3):
                for right in range(3):
                    if left == right:
                        continue
                    forward = graph.selection_score[left][
                        np.where(graph.selection_index[left] == right)[0]
                    ]
                    backward = graph.selection_score[right][
                        np.where(graph.selection_index[right] == left)[0]
                    ]
                    if forward.size and backward.size:
                        np.testing.assert_allclose(
                            forward, backward, rtol=1e-12, atol=1e-12
                        )


class SparsificationTests(unittest.TestCase):
    def test_more_than_ten_ties_select_low_ids(self) -> None:
        x = np.ones((13, 1), dtype=np.float64)
        graph = scores.compute_candidate("jaccard", x, x > 0)
        np.testing.assert_array_equal(
            graph.selection_index[0], np.arange(1, 11)
        )
        self.assertTrue(bool(graph.boundary_tie[0]))
        self.assertEqual(int(graph.cutoff_tied_candidates[0]), 12)
        self.assertGreater(int(graph.degree.max()), 10)
        self.assertGreater(graph.tie_summary["boundary_tie_nodes"], 0)

    def test_one_sided_selection_is_retained(self) -> None:
        # Skill 1 prefers 2 and 3 to 0, while skill 0 selects 1 and 2 at the
        # two-neighbour cutoff.  The union keeps 0-1 with a one-sided direction.
        support = np.array(
            [
                [1, 1, 0, 0],  # 0: a,b
                [0, 1, 1, 0],  # 1: b,c
                [1, 1, 1, 0],  # 2: a,b,c
                [0, 1, 1, 1],  # 3: b,c,d
            ],
            dtype=bool,
        )
        x = support.astype(np.float64)
        graph = scores.compute_candidate("jaccard", x, support, top_k=2)
        pairs = [tuple(pair) for pair in graph.edge_index.tolist()]
        self.assertIn((0, 1), pairs)
        direction = int(graph.edge_direction[pairs.index((0, 1))])
        self.assertEqual(direction, 1)
        self.assertNotIn(1, graph.selection_index[1].tolist())
        self.assertIn(1, graph.selection_index[0].tolist())

    def test_no_self_duplicate_or_zero_edges(self) -> None:
        graph = scores.compute_candidate(
            "cosine", *_x_rows()
        )
        self.assertTrue((graph.edge_index[:, 0] < graph.edge_index[:, 1]).all())
        self.assertEqual(
            np.unique(graph.edge_index, axis=0).shape[0],
            graph.edge_index.shape[0],
        )
        self.assertTrue((graph.edge_score > 0).all())
        for row in range(graph.selection_index.shape[0]):
            selected = graph.selection_index[row]
            selected = selected[selected >= 0]
            self.assertEqual(len(set(selected.tolist())), len(selected))
            self.assertNotIn(row, selected.tolist())

    def test_row_permutation_does_not_change_graph(self) -> None:
        observations = fx.canonical_observations()
        base = fx.training_fixture()
        contexts = list(fx.DEFAULT_CONTEXTS)
        skills = list(fx.DEFAULT_SKILLS)
        # Reverse both identity orders and reorder observations consistently.
        reversed_contexts = contexts[::-1]
        reversed_skills = skills[::-1]
        reordered = observations[::-1, ::-1, :]
        shuffled = fx.training_fixture(reversed_contexts, reversed_skills, reordered)
        left = scores.compute_candidate("jaccard", base.x, base.support)
        right = scores.compute_candidate("jaccard", shuffled.x, shuffled.support)
        np.testing.assert_array_equal(left.edge_index, right.edge_index)
        np.testing.assert_allclose(left.edge_score, right.edge_score, rtol=0, atol=0)
        np.testing.assert_array_equal(left.selection_index, right.selection_index)

    def test_all_zero_graph_remains_explicit(self) -> None:
        x = np.zeros((4, 3), dtype=np.float64)
        graph = scores.compute_candidate("cosine", x, x > 0)
        self.assertEqual(graph.n_edges, 0)
        self.assertEqual(graph.selection_index.shape, (4, protocol.TOP_K))
        self.assertTrue((graph.selection_index < 0).all())
        self.assertEqual(graph.pre_sparsification["status"], "null")
        self.assertIsNone(graph.pre_sparsification["score_mean"])


def _x_rows() -> tuple[np.ndarray, np.ndarray]:
    x = _x(
        [
            [1.0, 2.0, 0.0],
            [3.0, 1.0, 1.0],
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 1.0],
        ]
    )
    return x, x > 0


if __name__ == "__main__":
    unittest.main()
