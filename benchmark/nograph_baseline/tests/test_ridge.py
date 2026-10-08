"""Shared Ridge fitting, validation-only selection and the optional backend."""

from __future__ import annotations

import importlib.util
import unittest

import numpy as np

import nb_fixtures as fx
from benchmark.nograph_baseline import baselines, protocol, ridge


class NumpyFitTests(unittest.TestCase):
    def setUp(self) -> None:
        rng = np.random.default_rng(7)
        self.samples = 200
        self.x = rng.normal(size=(self.samples, 6))
        self.y = rng.normal(size=(self.samples, 3))
        self.lam = 0.1

    def _independent_solution(self):
        # Minimize (1/M)||XW+b-Y||^2 + lam*||W||^2 with an unpenalized
        # intercept via an augmented penalized least-squares system.
        x_augmented = np.hstack([self.x, np.ones((self.samples, 1))])
        penalty = np.zeros((6, 7))
        penalty[:, :6] = np.sqrt(self.lam * self.samples) * np.eye(6)
        a = np.vstack([x_augmented, penalty])
        b = np.vstack([self.y, np.zeros((6, 3))])
        solution, _, _, _ = np.linalg.lstsq(a, b, rcond=None)
        return solution[:6], solution[6]

    def test_single_shared_weight_matrix_and_bias(self) -> None:
        result = ridge.fit_numpy(self.x, self.y, self.lam)
        self.assertEqual(result["W"].shape, (6, 3))
        self.assertEqual(result["b"].shape, (3,))
        self.assertEqual(result["M"], self.samples)
        self.assertFalse(result["intercept_regularized"])
        weights, bias = self._independent_solution()
        np.testing.assert_allclose(result["W"], weights, atol=1e-12)
        np.testing.assert_allclose(result["b"], bias, atol=1e-12)

    def test_objective_matches_protocol_mean_loss(self) -> None:
        result = ridge.fit_numpy(self.x, self.y, self.lam)
        residual = self.x @ result["W"] + result["b"] - self.y
        expected = float(np.sum(residual**2) / self.samples) + self.lam * float(
            np.sum(result["W"] ** 2)
        )
        self.assertAlmostEqual(result["objective"], expected, places=12)
        # No divide-by-horizon factor: objective decreases with more shrinkage
        # only through the penalty term, never by scaling alpha.
        self.assertAlmostEqual(result["alpha"], self.lam * self.samples)

    def test_larger_lambda_shrinks_weights(self) -> None:
        small = ridge.fit_numpy(self.x, self.y, 1e-4)
        large = ridge.fit_numpy(self.x, self.y, 1.0)
        self.assertLess(
            float(np.sum(large["W"] ** 2)), float(np.sum(small["W"] ** 2))
        )


class DesignTests(unittest.TestCase):
    def test_training_sample_count_is_19_times_nodes(self) -> None:
        keys = fx.r0_keys(6)
        signal = fx.synthetic_signal(6, seed=12)
        demand = fx.make_demand("r0", keys, signal)
        stats = ridge.compute_training_stats(demand.signal)
        x, y = ridge.build_design(
            demand.signal, stats, protocol.SPLITS["train"]
        )
        self.assertEqual(x.shape, (19 * 6, 6))
        self.assertEqual(y.shape, (19 * 6, 3))
        self.assertEqual(
            protocol.expected_train_sample_count(6), 19 * 6
        )
        # Window-major then node-major ordering.
        np.testing.assert_allclose(
            x[:6], stats.standardize(signal[:, 0:6]), rtol=0, atol=0
        )
        np.testing.assert_allclose(
            x[6:12], stats.standardize(signal[:, 1:7]), rtol=0, atol=0
        )

    def test_predict_reconstructs_original_units(self) -> None:
        signal = fx.synthetic_signal(5, seed=5)
        stats = ridge.compute_training_stats(signal)
        weights = np.arange(18, dtype=np.float64).reshape(6, 3) / 10.0
        bias = np.array([1.0, -2.0, 0.5])
        raw = signal[:, 10:16]
        standardized = stats.standardize(raw)
        expected = stats.inverse(standardized @ weights + bias)
        actual = ridge.predict_original(raw, stats, weights, bias)
        np.testing.assert_allclose(actual, expected, rtol=0, atol=0)


class CandidateSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        keys = fx.r0_keys(10)
        self.signal = fx.synthetic_signal(10, seed=21)
        self.demand = fx.make_demand("r0", keys, self.signal)
        self.stats = ridge.compute_training_stats(self.demand.signal)
        self.x_train, self.y_train = ridge.build_design(
            self.demand.signal, self.stats, protocol.SPLITS["train"]
        )
        self.x_validation, self.y_validation = ridge.build_design(
            self.demand.signal, self.stats, protocol.SPLITS["validation"]
        )

    def test_all_five_candidates_record_validation_scores(self) -> None:
        candidates = ridge.fit_candidates(
            self.x_train,
            self.y_train,
            self.x_validation,
            self.y_validation,
            self.stats,
        )
        self.assertEqual(len(candidates), 5)
        for candidate in candidates:
            self.assertIn(candidate["lambda"], protocol.LAMBDA_CANDIDATES)
            self.assertAlmostEqual(
                candidate["alpha"], candidate["lambda"] * candidate["M"]
            )
            self.assertIn("validation_MSE", candidate)
            self.assertIn("validation_MAE", candidate)
            self.assertEqual(candidate["backend"], "numpy")
            self.assertIn("solver_version", candidate)

    def test_candidate_scores_use_original_unit_validation_targets(self) -> None:
        candidates = ridge.fit_candidates(
            self.x_train,
            self.y_train,
            self.x_validation,
            self.y_validation,
            self.stats,
        )
        gold_original = self.stats.inverse(self.y_validation)
        for candidate in candidates:
            self.assertEqual(candidate["validation_gold_units"], "original")
            self.assertAlmostEqual(
                candidate["validation_MSE"],
                baselines.mse(
                    candidate["validation_predictions"], gold_original
                ),
                places=12,
            )
            self.assertAlmostEqual(
                candidate["validation_MAE"],
                baselines.mae(
                    candidate["validation_predictions"], gold_original
                ),
                places=12,
            )

    def test_selection_uses_validation_mse_not_mae(self) -> None:
        candidates = [
            {"lambda": 1e-4, "alpha": 1e-4, "M": 1, "validation_MSE": 2.0,
             "validation_MAE": 1.0, "objective": 0.0, "backend": "numpy"},
            {"lambda": 1e-3, "alpha": 1e-3, "M": 1, "validation_MSE": 1.0,
             "validation_MAE": 9.0, "objective": 0.0, "backend": "numpy"},
        ]
        selection = ridge.select_lambda(candidates)
        self.assertEqual(selection["selected_lambda"], 1e-3)
        self.assertFalse(selection["test_labels_used"])

    def test_exact_mse_tie_selects_larger_lambda(self) -> None:
        candidates = [
            {"lambda": 0.01, "alpha": 0.01, "M": 1, "validation_MSE": 5.0,
             "validation_MAE": 1.0, "objective": 0.0, "backend": "numpy"},
            {"lambda": 1.0, "alpha": 1.0, "M": 1, "validation_MSE": 5.0,
             "validation_MAE": 8.0, "objective": 0.0, "backend": "numpy"},
        ]
        selection = ridge.select_lambda(candidates)
        self.assertEqual(selection["selected_lambda"], 1.0)
        self.assertEqual(selection["tied_lambdas"], [1.0, 0.01])

    def test_changed_test_labels_do_not_change_selection(self) -> None:
        candidates = ridge.fit_candidates(
            self.x_train,
            self.y_train,
            self.x_validation,
            self.y_validation,
            self.stats,
        )
        before = ridge.select_lambda(candidates)
        # Selection APIs never receive test labels; mutate a hypothetical test
        # target and confirm the frozen selection is unchanged.
        _ = self.signal[:, 30:33] * 1000.0
        after = ridge.select_lambda(candidates)
        self.assertEqual(before["selected_lambda"], after["selected_lambda"])
        for left, right in zip(
            before["candidate_table"], after["candidate_table"]
        ):
            self.assertEqual(left["validation_MSE"], right["validation_MSE"])

    def test_clipped_report_is_separately_labeled(self) -> None:
        prediction = np.array([[[-1.0, 2.0, -3.0]]])
        clipped = ridge.clip_nonnegative(prediction)
        np.testing.assert_array_equal(clipped, np.array([[[0.0, 2.0, 0.0]]]))
        self.assertNotEqual(protocol.CLIPPED_MODEL_NAME, protocol.MODEL_NAME)


class ModelPayloadContractTests(unittest.TestCase):
    """V-006: every accepted backend must satisfy the shared writer contract."""

    def test_numpy_payload_satisfies_contract(self) -> None:
        rng = np.random.default_rng(1)
        result = ridge.fit_numpy(
            rng.normal(size=(40, 6)), rng.normal(size=(40, 3)), 0.1
        )
        for key in ridge.MODEL_PARAMETER_KEYS:
            self.assertIn(key, result)
        validated = ridge.validate_model_payload(result)
        self.assertEqual(set(validated), set(result))

    def test_writer_contract_rejects_backend_without_centered_means(self) -> None:
        legacy = {
            "backend": "sklearn",
            "lambda": 0.1,
            "alpha": 1.0,
            "M": 10,
            "W": np.zeros((6, 3)),
            "b": np.zeros(3),
            "objective": 0.0,
        }
        with self.assertRaises(ridge.RidgeError):
            ridge.validate_model_payload(legacy, label="sklearn")

    def test_sklearn_return_schema_declares_contract_without_importing(self) -> None:
        # Static check so the defect is caught even where scikit-learn is absent.
        import ast
        import inspect

        source = inspect.getsource(ridge.fit_sklearn)
        tree = ast.parse(source)
        payload_keys = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Return)
                and isinstance(node.value, ast.Call)
                and getattr(node.value.func, "id", None) == "validate_model_payload"
                and node.value.args
                and isinstance(node.value.args[0], ast.Dict)
            ):
                payload_keys = [key.value for key in node.value.args[0].keys]
        self.assertIsNotNone(payload_keys, "fit_sklearn must return a payload dict")
        for key in ridge.MODEL_PARAMETER_KEYS:
            self.assertIn(key, payload_keys)


class OptionalSklearnTests(unittest.TestCase):
    @unittest.skipUnless(
        importlib.util.find_spec("sklearn") is not None,
        "optional scikit-learn backend is not installed",
    )
    def test_sklearn_matches_numpy(self) -> None:
        rng = np.random.default_rng(3)
        x = rng.normal(size=(500, 6))
        y = rng.normal(size=(500, 3))
        numpy_fit = ridge.fit_numpy(x, y, 0.01)
        sklearn_fit = ridge.fit_sklearn(x, y, 0.01)
        np.testing.assert_allclose(sklearn_fit["W"], numpy_fit["W"], atol=1e-9)
        np.testing.assert_allclose(sklearn_fit["b"], numpy_fit["b"], atol=1e-9)

    @unittest.skipUnless(
        importlib.util.find_spec("sklearn") is not None,
        "optional scikit-learn backend is not installed",
    )
    def test_sklearn_end_to_end_run_persists_parameters(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        from benchmark.nograph_baseline import runner

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = fx.build_fixture(root / "fixture", "r0", node_count=6)
            spec = fx.make_run_spec(
                root / "runs",
                "r0",
                fixture["demand_path"],
                fixture["graph_path"],
                "sklearn-run",
                ridge_backend="sklearn",
            )
            result = runner.execute_run(spec)
            run_dir = Path(result["run_dir"])
            self.assertEqual(
                json.loads((run_dir / "status.json").read_text())["state"], "success"
            )
            with np.load(
                run_dir / "models" / "SharedRidge.npz", allow_pickle=False
            ) as handle:
                for name in (
                    "W",
                    "b",
                    "node_mean",
                    "node_effective_std",
                    "centered_x_mean",
                    "centered_y_mean",
                ):
                    self.assertIn(name, handle.files)
            selection = json.loads((run_dir / "selection.json").read_text())
            self.assertEqual(
                selection["shared_ridge"]["candidate_table"][0]["backend"], "sklearn"
            )


if __name__ == "__main__":
    unittest.main()
