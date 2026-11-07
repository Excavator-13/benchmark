"""Structural summaries, component counts, associations and overlap."""

from __future__ import annotations

import unittest

import numpy as np

from benchmark.occupation_skill_graph import scores, structure
from benchmark.occupation_skill_graph.tests import fixtures as fx


class StructuralSummaryTests(unittest.TestCase):
    def test_all_zero_population_is_explicit(self) -> None:
        contexts = [1, 3]
        skills = [2, 5, 8, 11]
        observations = np.zeros((2, 4, 27), dtype=np.float64)
        training = fx.training_fixture(contexts, skills, observations)
        graph = scores.compute_candidate("cosine", training.x, training.support)
        summary, components = structure.candidate_structure(graph, training)
        self.assertEqual(summary["zero_demand_skills"]["count"], 4)
        self.assertEqual(summary["components"]["components"], 4)
        self.assertEqual(summary["components"]["isolated_nodes"], 4)
        self.assertEqual(
            summary["coverage"]["all_source_skills"]["coverage_fraction"], 0.0
        )
        self.assertEqual(summary["post_sparsification"]["edges"], 0)
        self.assertEqual(
            summary["post_sparsification"]["weight_distribution"]["status"], "null"
        )
        self.assertTrue(summary["empty_graph"])
        self.assertEqual(components.tolist(), [0, 1, 2, 3])

    def test_disconnected_components_are_counted(self) -> None:
        observations = np.zeros((2, 4, 27), dtype=np.float64)
        # Two disjoint occupational supports: skills 0-1 and skills 2-3.
        observations[0, 0, :] = 5.0
        observations[0, 1, :] = 5.0
        observations[1, 2, :] = 7.0
        observations[1, 3, :] = 7.0
        training = fx.training_fixture([0, 1], [0, 1, 2, 3], observations)
        graph = scores.compute_candidate("jaccard", training.x, training.support)
        summary, components = structure.candidate_structure(graph, training)
        self.assertEqual(graph.edge_index.tolist(), [[0, 1], [2, 3]])
        self.assertEqual(summary["components"]["components"], 2)
        self.assertEqual(len(set(components.tolist())), 2)
        self.assertEqual(summary["coverage"]["all_source_skills"]["covered_nodes"], 4)

    def test_equal_supports_expose_full_score_concentration(self) -> None:
        # Every skill has identical positive demand in every month.
        observations = np.ones((1, 13, 27), dtype=np.float64)
        training = fx.training_fixture([0], list(range(13)), observations)
        graph = scores.compute_candidate("jaccard", training.x, training.support)
        summary, _ = structure.candidate_structure(graph, training)
        self.assertEqual(summary["pre_sparsification"]["full_score_pairs"], 78)
        self.assertEqual(
            summary["pre_sparsification"]["full_score_fraction_of_positive"], 1.0
        )
        self.assertGreater(summary["cutoff_ties"]["boundary_tie_nodes"], 0)
        # Total demand is identical, so the association has zero variance.
        self.assertEqual(
            summary["associations"]["degree_vs_total_demand_all_skills"]["status"],
            "null",
        )
        self.assertEqual(
            summary["associations"]["degree_vs_total_demand_all_skills"]["r"], None
        )
        self.assertIn(
            "zero variance",
            summary["associations"]["degree_vs_total_demand_all_skills"]["reason"],
        )

    def test_zero_variance_degree_association_is_null(self) -> None:
        training = fx.training_fixture(observations=np.zeros((2, 4, 27)))
        graph = scores.compute_candidate("cosine", training.x, training.support)
        summary, _ = structure.candidate_structure(graph, training)
        for name in (
            "degree_vs_total_demand_all_skills",
            "degree_vs_occupational_breadth_all_skills",
        ):
            self.assertEqual(summary["associations"][name]["status"], "null")
            self.assertIn(name, summary["null_reasons"])

    def test_candidate_overlap_counts(self) -> None:
        x = np.array(
            [
                [1.0, 1.0, 0.0],
                [2.0, 0.0, 0.0],
                [0.0, 1.0, 1.0],
            ]
        )
        left = scores.compute_candidate("jaccard", x, x > 0)
        right = scores.compute_candidate("cosine", x, x > 0)
        overlap = structure.candidate_overlap(left, right)
        self.assertEqual(overlap["union_edges"], len(
            {tuple(pair) for pair in left.edge_index.tolist()}
            | {tuple(pair) for pair in right.edge_index.tolist()}
        ))
        self.assertEqual(
            overlap["shared_edges"],
            len(
                {tuple(pair) for pair in left.edge_index.tolist()}
                & {tuple(pair) for pair in right.edge_index.tolist()}
            ),
        )
        self.assertIsNotNone(overlap["jaccard"])

    def test_empty_distribution_has_reason(self) -> None:
        record = structure.distribution_summary([])
        self.assertEqual(record["status"], "null")
        self.assertEqual(record["reason"], "empty sample")


if __name__ == "__main__":
    unittest.main()
