"""Finite learning-rate selection, repetition identity and section-5 gates."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

import temporal_fixtures as fx
from benchmark.multivariate_time_series.temporal import diagnostics, protocol, runner
from benchmark.multivariate_time_series.temporal import selection as temporal_selection


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._block_counter = 0

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _candidate(self, run_id: str, learning_rate: float, **kwargs):
        return fx.synthetic_completed_run(
            self.root / "runs",
            run_id,
            learning_rate=learning_rate,
            candidate_role="screening",
            best_validation=kwargs.pop("best_validation", 5.0),
            **kwargs,
        )

    def _select(self, candidates, block_id: str = None):
        if block_id is None:
            self._block_counter += 1
            block_id = f"block-{self._block_counter}"
        return runner.run_select(
            {
                "block_id": block_id,
                "purpose": "development",
                "output_root": str(self.root / "blocks"),
                "candidates": [str(path) for path in candidates],
                "argv": ["test"],
            }
        )

    def test_exact_tie_prefers_the_smaller_learning_rate(self):
        low = self._candidate("cand-1e-3", 1e-3, best_validation=4.0)
        high = self._candidate("cand-3e-3", 3e-3, best_validation=4.0)
        result = self._select([high, low])
        selection = fx.read_json(Path(result["block_dir"]) / "selection.json")
        self.assertEqual(selection["status"], "frozen")
        self.assertEqual(selection["winner"]["learning_rate"], 1e-3)
        self.assertTrue(selection["tie"])
        self.assertEqual(selection["tied_learning_rates"], [1e-3, 3e-3])
        self.assertFalse(selection["test_scores_used"])
        self.assertFalse(selection["b_used_for_selection"])
        self.assertEqual(selection["winner_as_a"]["repeat_role"], "a")
        self.assertEqual(selection["winner_as_a"]["run_id"], "cand-1e-3")
        self.assertIn("tie", selection["winner"]["reason"])

    def test_higher_validation_mse_loses_with_a_recorded_reason(self):
        low = self._candidate("cand-1e-3", 1e-3, best_validation=4.0)
        high = self._candidate("cand-3e-3", 3e-3, best_validation=6.0)
        result = self._select([low, high])
        selection = fx.read_json(Path(result["block_dir"]) / "selection.json")
        self.assertEqual(selection["winner"]["learning_rate"], 1e-3)
        self.assertFalse(selection["tie"])
        self.assertEqual(len(selection["eliminated"]), 1)
        self.assertIn("higher validation MSE", selection["eliminated"][0]["reason"])

    def test_missing_candidate_is_rejected(self):
        low = self._candidate("cand-1e-3", 1e-3)
        with self.assertRaises(temporal_selection.SelectionError):
            self._select([low])

    def test_duplicate_candidate_learning_rate_is_rejected(self):
        first = self._candidate("cand-a", 1e-3)
        second = self._candidate("cand-b", 1e-3)
        with self.assertRaises(temporal_selection.SelectionError):
            self._select([first, second])

    def test_repetition_b_never_chooses_a_configuration(self):
        low = fx.synthetic_completed_run(
            self.root / "runs",
            "b-low",
            learning_rate=1e-3,
            repeat_role="b",
            candidate_role="confirmation",
        )
        high = self._candidate("cand-3e-3", 3e-3)
        with self.assertRaises(temporal_selection.SelectionError):
            self._select([low, high])

    def test_wrong_seed_or_condition_is_rejected(self):
        seeded = fx.synthetic_completed_run(
            self.root / "runs",
            "seed1",
            learning_rate=1e-3,
            seed=1,
            candidate_role="screening",
        )
        other = self._candidate("cand-3e-3", 3e-3)
        with self.assertRaises(temporal_selection.SelectionError):
            self._select([seeded, other])
        mismatched = self._candidate("cand-mismatch", 3e-3, data_sha="c" * 64)
        low = self._candidate("cand-low", 1e-3)
        with self.assertRaises(temporal_selection.SelectionError):
            self._select([low, mismatched])

    def test_failed_candidate_is_retained_and_blocks_freezing(self):
        low = self._candidate("cand-complete", 1e-3)
        failed = fx.synthetic_completed_run(
            self.root / "runs",
            "cand-failed",
            learning_rate=3e-3,
            candidate_role="screening",
            state="failed",
        )
        result = self._select([low, failed])
        selection = fx.read_json(Path(result["block_dir"]) / "selection.json")
        self.assertEqual(selection["status"], "incomplete")
        self.assertFalse(selection["frozen"])
        statuses = {row["run_id"]: row["status"] for row in selection["candidates"]}
        self.assertEqual(statuses["cand-complete"], "complete")
        self.assertEqual(statuses["cand-failed"], "failed")
        self.assertEqual(result["status"], "incomplete")


class LongTrajectoryTests(unittest.TestCase):
    """One complete 100-epoch development trajectory for the diagnostic nodes."""

    def test_complete_history_and_diagnostic_node_scores(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = fx.in_memory("r0", 3, seed=1)
            result = fx.fit_run(
                root / "runs",
                run_id="full-dev",
                data=data,
                epochs=protocol.EPOCHS,
                hidden_size=4,
                node_chunk=3,
                monitor_interval=1.0,
            )
            directory = Path(result["run_dir"])
            config = fx.read_json(directory / "config.json")
            self.assertFalse(config["protocol_controls"]["complete"])
            self.assertEqual(
                config["protocol_controls"]["deviations"],
                ["hidden_size=4 (protocol 32)"],
            )
            history = fx.read_json(directory / "history.json")
            self.assertEqual(len(history["epochs"]), protocol.EPOCHS)
            self.assertEqual(history["epochs"][-1]["epoch"], protocol.EPOCHS)
            scores = fx.read_json(directory / "scores.json")
            for name in ("init", "10", "50", "100", "best"):
                self.assertIn(name, scores)
                self.assertIn("train", scores[name])
                self.assertIn("validation", scores[name])
            self.assertEqual(scores["init"]["epoch"], 0)
            self.assertEqual(scores["10"]["updates"], 10 * protocol.UPDATES_PER_EPOCH)
            self.assertEqual(scores["100"]["updates"], protocol.TOTAL_UPDATES)
            report = fx.read_json(directory / "report.json")
            self.assertEqual(report["total_updates"], protocol.TOTAL_UPDATES)
            self.assertEqual(report["history_epochs"], protocol.EPOCHS)
            self.assertEqual(report["status"], "completed")
            cost = fx.read_json(directory / "cost.json")
            self.assertEqual(cost["status"], "ok")
            self.assertIsNotNone(cost["steady_state_median_seconds"])
            self.assertIsNotNone(cost["estimate_seconds"])


class DiagnosticsGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, run_id: str, **kwargs):
        return diagnostics.load_run_evidence(
            fx.synthetic_completed_run(self.root, run_id, **kwargs)
        )

    def _diagnose(self, a_runs, b_runs=None, *, ridge=None):
        selection = fx.selection_document(self.root, selection_sha="s" * 64)
        return diagnostics.build_diagnostics(
            selection=selection,
            block_id="block",
            a_runs=a_runs,
            b_runs=b_runs or {},
            ridge=ridge,
        )

    @staticmethod
    def _passing(seed: int, **overrides) -> dict:
        payload = dict(
            seed=seed,
            init_train=10.0,
            best_train=9.0,
            init_validation=20.0,
            best_validation=19.0,
            validation_mae=9.5,
            zero_mae=10.0,
            history_values=[max(10.0 - 0.1 * index, 5.0) for index in range(100)],
            condition_id=f"condition-{seed}",
        )
        payload.update(overrides)
        return payload

    def _all_pass(self, **overrides):
        a_runs = {
            seed: self._run(
                f"a{seed}", repeat_role="a", candidate_role="confirmation",
                **self._passing(seed, **overrides)
            )
            for seed in protocol.SEEDS
        }
        b_runs = {
            seed: self._run(
                f"b{seed}", repeat_role="b", candidate_role="confirmation",
                **self._passing(seed, **overrides)
            )
            for seed in protocol.SEEDS
        }
        return a_runs, b_runs

    @staticmethod
    def _compatible_ridge() -> dict:
        return {
            "dataset": "r0",
            "data_sha256": "a" * 64,
            "node_keys_sha256": "b" * 64,
            "split": {"validation_starts": [21]},
            "selection": {"lambda": 0.01, "selected_on": "validation"},
            "preprocessing": {"definition": "per-node standardization"},
            "validation": {"MAE": 6.0, "MSE": 36.0},
        }

    def test_every_gate_passes_with_complete_evidence(self):
        a_runs, b_runs = self._all_pass()
        payload = self._diagnose(a_runs, b_runs, ridge=self._compatible_ridge())
        self.assertEqual(payload["status"], "pass", payload["incomplete_reasons"])
        self.assertTrue(payload["learning_ready"])
        for gate in payload["gates"].values():
            self.assertEqual(gate["status"], "pass", gate)
        self.assertFalse(payload["test_scores_used"])
        self.assertFalse(payload["declares_research_acceptance"])
        self.assertTrue(payload["summary"]["complete_comparison"])

    def test_learning_gate_threshold_edges(self):
        for train, expected in ((9.0, "pass"), (9.001, "fail")):
            with self.subTest(train_MSE=train):
                a_runs = {
                    seed: self._run(
                        f"a{seed}-{train}", **self._passing(seed, best_train=train)
                    )
                    for seed in protocol.SEEDS
                }
                payload = self._diagnose(a_runs)
                gate = payload["gates"]["definite_learning"]
                self.assertEqual(gate["status"], expected, gate)
        for value, expected in ((19.0, "pass"), (19.001, "fail")):
            with self.subTest(validation_MSE=value):
                a_runs = {
                    seed: self._run(
                        f"a{seed}-v{value}",
                        **self._passing(seed, best_validation=value),
                    )
                    for seed in protocol.SEEDS
                }
                gate = self._diagnose(a_runs)["gates"]["definite_learning"]
                self.assertEqual(gate["status"], expected, gate)

    def test_zero_baseline_threshold_edge(self):
        for value, expected in ((9.5, "pass"), (9.501, "fail")):
            with self.subTest(validation_MAE=value):
                a_runs = {
                    seed: self._run(
                        f"a{seed}-z{value}",
                        **self._passing(seed, validation_mae=value),
                    )
                    for seed in protocol.SEEDS
                }
                gate = self._diagnose(a_runs)["gates"]["beyond_zero_baseline"]
                self.assertEqual(gate["status"], expected, gate)

    def test_zero_denominator_is_incomplete_not_a_pass(self):
        a_runs = {
            seed: self._run(f"a{seed}-zero", **self._passing(seed, zero_mae=0.0))
            for seed in protocol.SEEDS
        }
        payload = self._diagnose(a_runs)
        gate = payload["gates"]["beyond_zero_baseline"]
        self.assertEqual(gate["status"], "incomplete")
        self.assertFalse(payload["learning_ready"])
        self.assertTrue(
            any("all-zero" in reason for reason in payload["incomplete_reasons"])
        )

    def test_budget_tail_boundary_and_both_zero_rule(self):
        flat = [10.0] * 79 + [5.0] + [4.95] * 20
        a_runs = {
            seed: self._run(
                f"a{seed}-tail", **self._passing(seed, history_values=flat)
            )
            for seed in protocol.SEEDS
        }
        gate = self._diagnose(a_runs)["gates"]["budget_tail_stability"]
        self.assertEqual(gate["status"], "pass", gate)
        self.assertAlmostEqual(gate["per_seed"][0]["relative"], 0.01, places=12)
        steeper = [10.0] * 79 + [5.0] + [4.94] * 20
        a_runs = {
            seed: self._run(
                f"a{seed}-steep", **self._passing(seed, history_values=steeper)
            )
            for seed in protocol.SEEDS
        }
        gate = self._diagnose(a_runs)["gates"]["budget_tail_stability"]
        self.assertEqual(gate["status"], "fail")
        zeros = [0.0] * 100
        a_runs = {
            seed: self._run(
                f"a{seed}-zeros", **self._passing(seed, history_values=zeros)
            )
            for seed in protocol.SEEDS
        }
        gate = self._diagnose(a_runs)["gates"]["budget_tail_stability"]
        self.assertEqual(gate["status"], "pass")
        self.assertTrue(gate["per_seed"][0]["both_zero"])

    def test_two_of_three_seeds_can_carry_a_gate(self):
        a_runs = {}
        for seed in protocol.SEEDS:
            train = 9.0 if seed < 2 else 9.5
            a_runs[seed] = self._run(
                f"a{seed}-mix", **self._passing(seed, best_train=train)
            )
        payload = self._diagnose(a_runs)
        gate = payload["gates"]["definite_learning"]
        self.assertEqual(gate["status"], "pass")
        self.assertEqual(gate["passing_seeds"], [0, 1])
        self.assertEqual(gate["failing_seeds"], [2])

    def test_missing_history_is_incomplete(self):
        a_runs = {
            seed: self._run(
                f"a{seed}-short",
                **self._passing(seed, history_values=[50.0 - index for index in range(50)]),
            )
            for seed in protocol.SEEDS
        }
        payload = self._diagnose(a_runs)
        self.assertEqual(payload["status"], "incomplete")
        self.assertEqual(
            payload["gates"]["complete_and_finite_trajectories"]["status"],
            "incomplete",
        )
        self.assertEqual(payload["gates"]["budget_tail_stability"]["status"], "incomplete")
        self.assertFalse(payload["learning_ready"])

    def test_nonfinite_history_fails_the_completeness_gate(self):
        broken = [10.0] * 99 + [float("inf")]
        a_runs = {
            seed: self._run(
                f"a{seed}-inf", **self._passing(seed, history_values=broken)
            )
            for seed in protocol.SEEDS
        }
        payload = self._diagnose(a_runs)
        gate = payload["gates"]["complete_and_finite_trajectories"]
        self.assertEqual(gate["status"], "fail")
        self.assertEqual(payload["status"], "fail")

    def test_development_override_is_incomplete(self):
        a_runs = {
            seed: self._run(
                f"a{seed}-dev", **self._passing(seed, complete_controls=False)
            )
            for seed in protocol.SEEDS
        }
        payload = self._diagnose(a_runs)
        self.assertEqual(
            payload["gates"]["complete_and_finite_trajectories"]["status"],
            "incomplete",
        )
        self.assertIn(
            "development override",
            " ".join(payload["incomplete_reasons"]),
        )

    def test_repetition_bound_and_condition_identity(self):
        a_runs, b_runs = self._all_pass()
        payload = self._diagnose(a_runs, b_runs)
        self.assertEqual(payload["gates"]["same_condition_repetition"]["status"], "pass")
        different = {
            seed: self._run(
                f"b{seed}-diff",
                repeat_role="b",
                candidate_role="confirmation",
                **self._passing(seed, validation_mae=9.5001),
            )
            for seed in protocol.SEEDS
        }
        payload = self._diagnose(a_runs, different)
        gate = payload["gates"]["same_condition_repetition"]
        self.assertEqual(gate["status"], "fail")
        mismatched = {
            seed: self._run(
                f"b{seed}-cond",
                repeat_role="b",
                candidate_role="confirmation",
                **self._passing(seed, condition_id=f"other-{seed}"),
            )
            for seed in protocol.SEEDS
        }
        payload = self._diagnose(a_runs, mismatched)
        gate = payload["gates"]["same_condition_repetition"]
        self.assertEqual(gate["status"], "fail")
        self.assertTrue(
            any("condition identities differ" in problem
                for problem in gate["per_seed"][0]["problems"])
        )

    def test_failed_seed_is_retained_in_the_summary(self):
        a_runs = {
            seed: self._run(f"a{seed}-ok", **self._passing(seed))
            for seed in protocol.SEEDS
        }
        a_runs[1] = self._run(
            "a1-failed", state="failed", **self._passing(1)
        )
        payload = self._diagnose(a_runs)
        summary = payload["summary"]
        self.assertFalse(summary["complete_comparison"])
        self.assertTrue(
            any(entry["seed"] == 1 and entry["role"] == "a"
                for entry in summary["failed_or_incomplete"])
        )
        self.assertEqual(payload["status"], "incomplete")

    def test_missing_baseline_or_repetition_evidence_stays_incomplete(self):
        directories = {
            seed: fx.synthetic_completed_run(
                self.root, f"a{seed}-nobase", **self._passing(seed)
            )
            for seed in protocol.SEEDS
        }
        (directories[1] / "baselines.json").unlink()
        a_runs = {
            seed: diagnostics.load_run_evidence(path)
            for seed, path in directories.items()
        }
        payload = self._diagnose(a_runs)
        self.assertEqual(
            payload["gates"]["beyond_zero_baseline"]["per_seed"][1]["status"],
            "incomplete",
        )
        self.assertEqual(payload["gates"]["beyond_zero_baseline"]["status"], "incomplete")
        self.assertFalse(payload["learning_ready"])
        a_runs, _ = self._all_pass()
        payload = self._diagnose(a_runs, {0: self._run("b0-only", repeat_role="b",
                                                     candidate_role="confirmation",
                                                     **self._passing(0))})
        gate = payload["gates"]["same_condition_repetition"]
        self.assertEqual(gate["status"], "incomplete")
        self.assertEqual(payload["status"], "incomplete")
        self.assertTrue(
            any("a/b repetition evidence is incomplete" in reason
                for reason in gate["reasons"])
        )

    def test_ridge_evidence_identity_mismatch_stays_incomplete(self):
        a_runs, b_runs = self._all_pass()
        ridge = {
            "dataset": "r0",
            "data_sha256": "f" * 64,
            "node_keys_sha256": "e" * 64,
            "split": {"validation_starts": [21]},
            "selection": {"lambda": 0.01},
            "validation": {"MAE": 5.0, "MSE": 25.0},
        }
        payload = self._diagnose(a_runs, b_runs, ridge=ridge)
        self.assertNotEqual(payload["baselines"]["status"], "pass")
        self.assertFalse(payload["learning_ready"])
        self.assertNotEqual(payload["status"], "pass")
        self.assertTrue(payload["baselines"]["ridge"]["mismatches"])
        month_mismatch = {
            **self._compatible_ridge(),
            "split": {
                "validation_starts": [21],
                "validation_target_months": ["2023-01", "2023-02", "2023-03"],
            },
        }
        payload = self._diagnose(a_runs, b_runs, ridge=month_mismatch)
        self.assertTrue(
            any("month identity" in reason for reason in payload["baselines"]["reasons"])
        )


if __name__ == "__main__":
    unittest.main()
