"""Development backtest folds A/B: definitions, fitting scope, artifacts, checks.

Covers tasks 2.1-2.3, 3.1-3.4, 4.1-4.6, 5.1-5.6 and 6.1 of the
``add-nograph-backtest-folds`` change with temporary fixtures only.  No formal
fold run, no repository graph/demand data and no sealed artifact is touched.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import nb_fixtures as fx
from benchmark.nograph_baseline import artifacts, baselines, checks, cli, protocol, ridge, runner
from benchmark.nograph_baseline import data as nb_data
from benchmark.nograph_baseline.data import sha256_file

REPO_ROOT = protocol.REPO_ROOT
FORMAL_ROOT = REPO_ROOT / "research" / "runs"


def _read(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path: Path, payload) -> None:
    Path(path).write_text(json.dumps(payload), encoding="utf-8")


def _run(
    root: Path,
    data_name: str,
    fixture: dict,
    run_id: str,
    *,
    fold=None,
    seed: int = 0,
    purpose: str = "development",
    runs_root: Path | None = None,
    **overrides,
) -> Path:
    spec = fx.make_run_spec(
        runs_root or (root / "runs"),
        data_name,
        fixture["demand_path"],
        fixture["graph_path"],
        run_id,
        fold=fold,
        seed=seed,
        purpose=purpose,
        **overrides,
    )
    return Path(runner.execute_run(spec)["run_dir"])


def _tree_hash(root: Path) -> dict:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(Path(root).rglob("*"))
        if path.is_file()
    }


def _boundary_signal(node_count: int = 8) -> np.ndarray:
    """Deterministic signal with A/B activity and constant boundaries."""
    rng = np.random.default_rng(11)
    signal = rng.integers(0, 30, size=(node_count, 36)).astype(np.float32)
    # A fitting (first 18): inactive, but the main 27 months are active.
    signal[0, :18] = 0.0
    signal[0, 18:] = 3.0
    # Constant over both A (18) and B (21) fitting scopes, while the main 27
    # months vary.
    signal[1, :21] = 5.0
    signal[1, 21:] = np.arange(21, 36, dtype=np.float32) % 7.0
    # A fitting activity 6/18 == 1/3 (low) and 12/18 == 2/3 (medium).
    signal[2, :6] = 1.0
    signal[2, 6:] = 0.0
    signal[3, :12] = 1.0
    signal[3, 12:] = 0.0
    # Activity 1 without zero variance (high).
    signal[4, :18] = 1.0 + (np.arange(18, dtype=np.float32) % 3.0)
    signal[4, 18:] = 2.0
    # Activity 7/21 and 14/21 boundaries for B (only when those rows exist).
    if node_count > 5:
        signal[5, :7] = 1.0
        signal[5, 7:] = 0.0
    if node_count > 6:
        signal[6, :14] = 1.0
        signal[6, 14:] = 0.0
    return signal


def _write_signal_demand(root: Path, signal: np.ndarray) -> dict:
    keys = fx.r0_keys(signal.shape[0])
    demand_path = fx.write_demand(root / "demand.parquet", "r0", keys, signal)
    graph_path = fx.write_graph(
        root / "graph.parquet", "r0", [[0, 0, 1], [0, 1, 1]]
    )
    return {
        "data_name": "r0",
        "keys": keys,
        "signal": signal,
        "demand_path": demand_path,
        "graph_path": graph_path,
        "node_count": len(keys),
    }


class FoldDefinitionTests(unittest.TestCase):
    def test_fold_a_fixed_definition(self) -> None:
        definition = protocol.resolve_split("A")
        self.assertEqual(definition.fitting_month_count, 18)
        self.assertEqual(definition.train_starts, tuple(range(10)))
        self.assertEqual(definition.validation_starts, (12,))
        self.assertEqual(definition.evaluation_starts, (15,))
        self.assertEqual(definition.evaluation_split, "eval")
        self.assertEqual(definition.omitted_starts, (10, 11, 13, 14, 16, 17))
        self.assertEqual(definition.outside_fold_starts, tuple(range(18, 28)))
        self.assertEqual(definition.train_mean_method, "TrainMean18")
        self.assertEqual(
            list(definition.fitting_observation_months),
            [protocol.MONTHS[index] for index in range(18)],
        )
        self.assertEqual(
            list(definition.target_months_for("train")),
            [protocol.MONTHS[index] for index in range(6, 18)],
        )
        self.assertEqual(
            list(definition.target_months_for("validation")),
            ["2022-07", "2022-08", "2022-09"],
        )
        self.assertEqual(
            list(definition.eval_target_months),
            ["2022-10", "2022-11", "2022-12"],
        )

    def test_fold_b_fixed_definition(self) -> None:
        definition = protocol.resolve_split("B")
        self.assertEqual(definition.fitting_month_count, 21)
        self.assertEqual(definition.train_starts, tuple(range(13)))
        self.assertEqual(definition.validation_starts, (15,))
        self.assertEqual(definition.evaluation_starts, (18,))
        self.assertEqual(definition.omitted_starts, (13, 14, 16, 17, 19, 20))
        self.assertEqual(definition.outside_fold_starts, tuple(range(21, 28)))
        self.assertEqual(definition.train_mean_method, "TrainMean21")
        self.assertEqual(
            list(definition.target_months_for("train")),
            [protocol.MONTHS[index] for index in range(6, 21)],
        )
        self.assertEqual(
            list(definition.target_months_for("validation")),
            ["2022-10", "2022-11", "2022-12"],
        )
        self.assertEqual(
            list(definition.eval_target_months),
            ["2023-01", "2023-02", "2023-03"],
        )

    def test_main_defaults_are_unchanged(self) -> None:
        protocol.validate_split_assertions()
        definition = protocol.resolve_split(None)
        self.assertTrue(definition.is_main)
        self.assertEqual(definition.fitting_month_count, 27)
        self.assertEqual(definition.train_starts, tuple(range(19)))
        self.assertEqual(definition.validation_starts, (21,))
        self.assertEqual(definition.evaluation_starts, (24, 25, 26, 27))
        self.assertEqual(definition.evaluation_split, "test")
        self.assertEqual(definition.omitted_starts, (19, 20, 22, 23))
        self.assertEqual(definition.outside_fold_starts, ())
        self.assertEqual(definition.naive_methods, protocol.NAIVE_METHODS)
        self.assertEqual(protocol.windows_for_split("train"), tuple(range(19)))
        self.assertEqual(protocol.windows_for_split("test"), (24, 25, 26, 27))
        with self.assertRaises(protocol.ProtocolError):
            protocol.windows_for_split("eval")
        self.assertEqual(protocol.resolve_split("main"), protocol.MAIN_SPLIT)

    def test_unknown_fold_is_rejected(self) -> None:
        for value in ("C", "a", "", 1, "fold-a"):
            with self.subTest(value=value):
                with self.assertRaises(protocol.ProtocolError):
                    protocol.resolve_split(value)

    def test_fold_window_metadata_lists_every_role_and_reason(self) -> None:
        for fold, definition in (("A", protocol.FOLD_A), ("B", protocol.FOLD_B)):
            with self.subTest(fold=fold):
                metadata = protocol.build_window_metadata(definition)
                self.assertEqual(metadata["fold"], fold)
                self.assertEqual(len(metadata["windows"]), 28)
                self.assertEqual(
                    metadata["splits"],
                    {
                        "train": list(definition.train_starts),
                        "validation": list(definition.validation_starts),
                        "eval": list(definition.evaluation_starts),
                    },
                )
                self.assertEqual(metadata["omitted_starts"], list(definition.omitted_starts))
                roles = {entry["start"]: entry["role"] for entry in metadata["windows"]}
                self.assertEqual(roles[0], "train")
                self.assertEqual(roles[definition.validation_starts[0]], "validation")
                self.assertEqual(roles[definition.evaluation_starts[0]], "eval")
                self.assertEqual(roles[definition.omitted_starts[0]], "omitted")
                self.assertEqual(roles[definition.outside_fold_starts[0]], "outside_fold")
                for entry in metadata["windows"]:
                    if entry["role"] == "omitted":
                        self.assertEqual(
                            entry["reason"],
                            definition.omitted_reason_map()[entry["start"]],
                        )
                    elif entry["role"] == "outside_fold":
                        self.assertEqual(entry["reason"], "outside_fold")
                    else:
                        self.assertIsNone(entry["reason"])
                    self.assertEqual(
                        entry["input_months"],
                        list(protocol.window_input_months(entry["start"])),
                    )
                    self.assertEqual(
                        entry["target_months"],
                        list(protocol.window_target_months(entry["start"])),
                    )

    def test_main_window_metadata_keeps_historical_schema(self) -> None:
        metadata = protocol.build_window_metadata()
        self.assertEqual(
            set(metadata),
            {
                "protocol_version",
                "input_length",
                "horizon",
                "n_windows",
                "all_starts",
                "splits",
                "omitted_starts",
                "windows",
            },
        )
        for entry in metadata["windows"]:
            self.assertEqual(
                set(entry),
                {"start", "split", "input_months", "target_months", "forecast_origin"},
            )

    def test_modified_definitions_fail_validation(self) -> None:
        mutations = [
            dataclasses.replace(protocol.FOLD_A, train_starts=tuple(range(11))),
            dataclasses.replace(protocol.FOLD_B, fitting_month_count=20),
            dataclasses.replace(protocol.FOLD_A, validation_starts=(13,)),
            dataclasses.replace(
                protocol.FOLD_A,
                omitted_reasons=tuple(
                    (start, "wrong_reason") for start in protocol.FOLD_A.omitted_starts
                ),
            ),
            dataclasses.replace(protocol.FOLD_B, omitted_starts=(13, 14, 16, 17, 19)),
            dataclasses.replace(protocol.FOLD_A, outside_fold_starts=tuple(range(19, 28))),
            dataclasses.replace(protocol.FOLD_B, evaluation_starts=(19,)),
            dataclasses.replace(
                protocol.FOLD_A,
                naive_methods=("Zero", "LastValue", "WindowMean6", "TrainMean27", "SeasonalNaive12"),
            ),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(protocol.ProtocolError):
                    protocol.validate_split_definition(mutation)
        with self.assertRaises(protocol.ProtocolError):
            protocol.validate_split_assertions(
                dataclasses.replace(protocol.MAIN_SPLIT, validation_starts=(20,))
            )

    def test_overlapping_target_months_fail(self) -> None:
        overlap = dataclasses.replace(protocol.FOLD_A, validation_starts=(13,))
        with self.assertRaises(protocol.ProtocolError):
            protocol.validate_split_definition(overlap)

    def test_historical_target_months_are_allowed_as_inputs(self) -> None:
        # Fold A's eval window inputs include earlier training/validation target
        # months; this is legitimate observed history, not leakage.
        inputs = set(protocol.window_input_months(15))
        train_targets = set(protocol.FOLD_A.target_months_for("train"))
        validation_targets = set(protocol.FOLD_A.target_months_for("validation"))
        self.assertTrue(inputs & train_targets)
        self.assertTrue(inputs & validation_targets)
        protocol.validate_split_assertions(protocol.FOLD_A)


class FoldFittingStatisticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.signal = _boundary_signal(8)

    def test_mean_std_ddof0_constant_and_activity_match_oracle(self) -> None:
        for definition in (protocol.FOLD_A, protocol.FOLD_B):
            with self.subTest(fold=definition.fold):
                count = definition.fitting_month_count
                stats = ridge.compute_training_stats(self.signal, definition=definition)
                expected = self.signal[:, :count].astype(np.float64)
                np.testing.assert_allclose(stats.mean, expected.mean(axis=1), rtol=0, atol=0)
                np.testing.assert_allclose(
                    stats.std, expected.std(axis=1, ddof=0), rtol=0, atol=0
                )
                constant = expected.std(axis=1) == 0
                np.testing.assert_array_equal(stats.constant_mask, constant)
                expected_effective = np.where(constant, 1.0, expected.std(axis=1))
                np.testing.assert_array_equal(stats.effective_std, expected_effective)
                np.testing.assert_allclose(
                    stats.activity,
                    (self.signal[:, :count] > 0).mean(axis=1),
                    rtol=0,
                    atol=0,
                )
                frozen = baselines.train_mean(self.signal, count)
                np.testing.assert_array_equal(stats.train_mean_float32, frozen)
                self.assertEqual(stats.fitting_month_count, count)
                self.assertEqual(stats.train_mean_method, definition.train_mean_method)
                partition = np.stack(list(stats.activity_groups.values())).sum(axis=0)
                np.testing.assert_array_equal(partition, np.ones(8))

    def test_fold_activity_boundaries(self) -> None:
        for definition, counts in (
            (protocol.FOLD_A, (0, 6, 12, 18)),
            (protocol.FOLD_B, (0, 7, 14, 21)),
        ):
            with self.subTest(fold=definition.fold):
                month_count = definition.fitting_month_count
                signal = np.zeros((4, 36), dtype=np.float32)
                for row, count in enumerate(counts):
                    signal[row, :count] = 1.0
                stats = ridge.compute_training_stats(signal, definition=definition)
                groups = stats.activity_groups
                self.assertTrue(groups["inactive"][0])
                self.assertTrue(groups["low"][1], "activity exactly 1/3 is low")
                self.assertTrue(groups["medium"][2], "activity exactly 2/3 is medium")
                self.assertTrue(groups["high"][3])
                self.assertEqual(stats.fitting_month_count, month_count)

    def test_inputs_and_targets_share_fold_statistics(self) -> None:
        stats = ridge.compute_training_stats(self.signal, definition=protocol.FOLD_A)
        inputs = self.signal[:, 7:13]
        targets = self.signal[:, 13:16]
        expected_inputs = (inputs.astype(np.float64) - stats.mean[:, None]) / stats.effective_std[:, None]
        expected_targets = (targets.astype(np.float64) - stats.mean[:, None]) / stats.effective_std[:, None]
        np.testing.assert_array_equal(stats.standardize(inputs), expected_inputs)
        np.testing.assert_array_equal(stats.standardize(targets), expected_targets)

    def test_post_fitting_values_leave_statistics_and_training_parameters(self) -> None:
        for definition in (protocol.FOLD_A, protocol.FOLD_B):
            with self.subTest(fold=definition.fold):
                changed = self.signal.copy()
                cutoff = definition.fitting_month_count
                changed[:, cutoff:] = changed[:, cutoff:] * 1000.0 + 17.0
                before = ridge.compute_training_stats(self.signal, definition=definition)
                after = ridge.compute_training_stats(changed, definition=definition)
                for name in (
                    "mean",
                    "std",
                    "effective_std",
                    "constant_mask",
                    "activity",
                    "train_mean_float32",
                ):
                    np.testing.assert_array_equal(
                        getattr(before, name), getattr(after, name)
                    )
                for name in protocol.ACTIVITY_GROUP_NAMES:
                    np.testing.assert_array_equal(
                        before.activity_groups[name], after.activity_groups[name]
                    )
                x_before, y_before = ridge.build_design(
                    self.signal, before, definition.train_starts
                )
                x_after, y_after = ridge.build_design(
                    changed, after, definition.train_starts
                )
                np.testing.assert_array_equal(x_before, x_after)
                np.testing.assert_array_equal(y_before, y_after)
                for lam in protocol.LAMBDA_CANDIDATES:
                    left = ridge.fit_numpy(x_before, y_before, lam)
                    right = ridge.fit_numpy(x_after, y_after, lam)
                    np.testing.assert_array_equal(left["W"], right["W"])
                    np.testing.assert_array_equal(left["b"], right["b"])


class FoldNaiveAndRidgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.signal = _boundary_signal(6)
        self.definition = protocol.FOLD_A
        self.validation_starts = self.definition.validation_starts
        self.eval_starts = self.definition.evaluation_starts

    def test_train_mean_names_and_values(self) -> None:
        for count, name in ((18, "TrainMean18"), (21, "TrainMean21")):
            with self.subTest(name=name):
                frozen = baselines.train_mean(self.signal, count)
                np.testing.assert_array_equal(
                    frozen,
                    self.signal[:, :count].mean(axis=1, keepdims=True),
                )
                definition = protocol.resolve_split("A" if count == 18 else "B")
                stats = ridge.compute_training_stats(self.signal, definition=definition)
                np.testing.assert_array_equal(stats.train_mean_float32, frozen)
                self.assertEqual(stats.train_mean_method, name)

    def test_fold_naive_predictions_and_seasonal_history(self) -> None:
        frozen = baselines.train_mean(self.signal, 18)
        predictions = baselines.naive_predictions(
            self.signal,
            self.validation_starts,
            frozen_train_mean=frozen,
            train_mean_method="TrainMean18",
        )
        self.assertEqual(list(predictions), list(self.definition.naive_methods))
        self.assertNotIn("TrainMean27", predictions)
        gold = np.stack([self.signal[:, s + 6 : s + 9] for s in self.validation_starts])
        for prediction in predictions.values():
            self.assertEqual(prediction.shape, gold.shape)
        seasonal = predictions["SeasonalNaive12"]
        for index, start in enumerate(self.validation_starts):
            for horizon in range(3):
                target_index = start + 6 + horizon
                np.testing.assert_array_equal(
                    seasonal[index, :, horizon],
                    self.signal[:, target_index - 12],
                )
        expected_eval = np.stack(
            [self.signal[:, s + 6 : s + 9] for s in self.eval_starts]
        )
        eval_predictions = baselines.naive_predictions(
            self.signal,
            self.eval_starts,
            frozen_train_mean=frozen,
            train_mean_method="TrainMean18",
        )
        self.assertEqual(eval_predictions["TrainMean18"].shape, expected_eval.shape)
        self.assertEqual(
            list(protocol.window_target_months(15)),
            ["2022-10", "2022-11", "2022-12"],
        )

    def test_reference_ties_use_fold_table_order(self) -> None:
        scores = {
            "Zero": 10.0,
            "LastValue": 1.0,
            "WindowMean6": 1.0,
            "TrainMean18": 0.5,
            "SeasonalNaive12": 0.5,
        }
        selection = baselines.select_references(
            scores,
            order=self.definition.naive_methods,
            ref6_candidates=self.definition.naive_ref6_methods,
        )
        self.assertEqual(selection["NaiveRef"], "TrainMean18")
        self.assertEqual(selection["NaiveRef6"], "TrainMean18")
        self.assertEqual(
            selection["table_order"], list(self.definition.naive_methods)
        )
        self.assertEqual(selection["NaiveRef6_ties"], ["TrainMean18"])
        self.assertNotIn("SeasonalNaive12", self.definition.naive_ref6_methods)
        self.assertTrue(selection["SeasonalNaive12_excluded_from_NaiveRef6"])

    def test_fold_candidate_scores_use_fold_validation_and_M(self) -> None:
        definition = self.definition
        stats = ridge.compute_training_stats(self.signal, definition=definition)
        x_train, y_train = ridge.build_design(
            self.signal, stats, definition.train_starts
        )
        x_validation, y_validation = ridge.build_design(
            self.signal, stats, definition.validation_starts
        )
        candidates = ridge.fit_candidates(
            x_train, y_train, x_validation, y_validation, stats
        )
        expected_m = 10 * self.signal.shape[0]
        self.assertEqual(x_train.shape[0], expected_m)
        for candidate in candidates:
            self.assertEqual(candidate["M"], expected_m)
            self.assertAlmostEqual(
                candidate["alpha"], candidate["lambda"] * expected_m
            )
            gold = stats.inverse(y_validation)
            self.assertAlmostEqual(
                candidate["validation_MSE"],
                baselines.mse(candidate["validation_predictions"], gold),
                places=12,
            )
        selection = ridge.select_lambda(candidates)
        self.assertEqual(selection["test_labels_used"], False)
        tied = [
            {
                "lambda": 1e-4, "alpha": 1e-4, "M": expected_m,
                "validation_MSE": 3.0, "validation_MAE": 1.0,
                "objective": 0.0, "backend": "numpy",
            },
            {
                "lambda": 1.0, "alpha": 1.0, "M": expected_m,
                "validation_MSE": 3.0, "validation_MAE": 9.0,
                "objective": 0.0, "backend": "numpy",
            },
        ]
        self.assertEqual(ridge.select_lambda(tied)["selected_lambda"], 1.0)


class FoldInformationIsolationTests(unittest.TestCase):
    def test_only_eval_targets_change_selection_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            signal = _boundary_signal(6)
            base = _write_signal_demand(root / "base", signal)
            changed_signal = signal.copy()
            # Fold A eval targets are 2022-10..12 (month indices 21..23).
            changed_signal[:, 21:24] = changed_signal[:, 21:24] * 100.0 + 9.0
            changed = _write_signal_demand(root / "changed", changed_signal)
            run_a = _run(root, "r0", base, "isolation-base", fold="A")
            run_b = _run(root, "r0", changed, "isolation-eval", fold="A")
            self.assertEqual((run_a / "selection.json").read_bytes(), (run_b / "selection.json").read_bytes())
            for method in protocol.FOLD_A.naive_methods + (protocol.MODEL_NAME,):
                if method == "SeasonalNaive12":
                    continue
                np.testing.assert_array_equal(
                    np.load(run_a / "predictions" / method / "validation.npy"),
                    np.load(run_b / "predictions" / method / "validation.npy"),
                )
            with np.load(run_a / "models" / "SharedRidge.npz") as left, np.load(
                run_b / "models" / "SharedRidge.npz"
            ) as right:
                for name in ("W", "b", "node_mean", "node_effective_std"):
                    np.testing.assert_array_equal(left[name], right[name])
            np.testing.assert_array_equal(
                np.load(run_a / "gold" / "validation.npy"),
                np.load(run_b / "gold" / "validation.npy"),
            )

    def test_eval_targets_are_not_constructed_before_selection(self) -> None:
        # A run stopped before the selection write must not have eval gold or
        # eval predictions; the selection itself is written at ridge_selection.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_signal_demand(root, _boundary_signal(6))
            run_dir = _run(root, "r0", fixture, "ordering-run", fold="A")
            metrics = _read(run_dir / "metrics.json")
            self.assertNotIn("test", metrics["methods"])
            self.assertEqual(set(metrics["methods"]), {"validation", "eval"})
            self.assertEqual(
                _read(run_dir / "selection.json")["model_evaluation"][
                    "eval_built_after_selection_frozen"
                ],
                True,
            )


class FoldRunArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.signal = _boundary_signal(8)
        cls.fixture = _write_signal_demand(cls.root / "fixture", cls.signal)
        cls.run_dirs = {
            "A": _run(cls.root, "r0", cls.fixture, "artifacts-a", fold="A"),
            "B": _run(cls.root, "r0", cls.fixture, "artifacts-b", fold="B"),
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_fold_metadata_is_consistent_across_writers(self) -> None:
        for fold, run_dir in self.run_dirs.items():
            definition = protocol.resolve_split(fold)
            expected = definition.to_payload()
            with self.subTest(fold=fold):
                config = _read(run_dir / "config.json")
                provenance = _read(run_dir / "provenance.json")
                windows = _read(run_dir / "windows.json")
                selection = _read(run_dir / "selection.json")
                metrics = _read(run_dir / "metrics.json")
                self.assertEqual(config["spec"]["fold"], fold)
                self.assertEqual(config["fold"], expected)
                self.assertEqual(provenance["fold"], expected)
                self.assertEqual(metrics["fold"], expected)
                self.assertEqual(selection["fold"], expected)
                self.assertEqual(windows["fold"], fold)
                self.assertEqual(windows["splits"]["train"], list(definition.train_starts))
                self.assertEqual(
                    windows["splits"]["validation"], list(definition.validation_starts)
                )
                self.assertEqual(
                    windows["splits"]["eval"], list(definition.evaluation_starts)
                )
                self.assertEqual(windows["omitted_starts"], list(definition.omitted_starts))
                self.assertEqual(
                    windows["omitted_reasons"],
                    {str(k): v for k, v in definition.omitted_reason_map().items()},
                )
                self.assertEqual(
                    windows["outside_fold_starts"],
                    list(definition.outside_fold_starts),
                )
                self.assertEqual(windows["eval_target_months"], list(definition.eval_target_months))
                self.assertEqual(provenance["evidence_role"], "development_backtest")
                self.assertEqual(metrics["evidence_role"], "development_backtest")
                self.assertEqual(config["evidence_role"], "development_backtest")
                self.assertEqual(selection["evidence_role"], "development_backtest")
                self.assertEqual(len(windows["windows"]), 28)
                self.assertEqual(
                    set(windows), {
                        "protocol_version", "input_length", "horizon", "n_windows",
                        "all_starts", "fold", "fitting_observation_months",
                        "fitting_month_count", "splits", "omitted_starts",
                        "omitted_reasons", "outside_fold_starts",
                        "eval_target_months", "evaluation_splits", "windows",
                    }
                )

    def test_selection_records_full_fold_contract(self) -> None:
        for fold, run_dir in self.run_dirs.items():
            definition = protocol.resolve_split(fold)
            with self.subTest(fold=fold):
                selection = _read(run_dir / "selection.json")
                self.assertEqual(
                    selection["normalization"]["train_observation_months"],
                    list(definition.fitting_observation_months),
                )
                self.assertEqual(
                    selection["normalization"]["fitting_month_count"],
                    definition.fitting_month_count,
                )
                self.assertEqual(
                    selection["normalization"]["train_mean_method"],
                    definition.train_mean_method,
                )
                self.assertEqual(
                    list(selection["naive_validation_scores"]),
                    sorted(definition.naive_methods),
                )
                references = selection["naive_references"]
                self.assertIn(references["NaiveRef"], definition.naive_methods)
                self.assertIn(references["NaiveRef6"], definition.naive_ref6_methods)
                self.assertEqual(len(references["validation_MSE_table"]), 5)
                self.assertEqual(
                    selection["naive_reference_reasons"]["NaiveRef"]["selected"],
                    references["NaiveRef"],
                )
                self.assertEqual(
                    selection["naive_reference_reasons"]["NaiveRef6"]["selected"],
                    references["NaiveRef6"],
                )
                candidates = selection["shared_ridge"]["candidate_table"]
                self.assertEqual(len(candidates), 5)
                self.assertEqual(
                    sorted(row["lambda"] for row in candidates),
                    sorted(protocol.LAMBDA_CANDIDATES),
                )
                expected_m = len(definition.train_starts) * self.signal.shape[0]
                self.assertEqual(selection["training_samples_M"], expected_m)
                self.assertEqual(selection["expected_training_samples_M"], expected_m)
                for row in candidates:
                    self.assertEqual(row["M"], expected_m)
                    self.assertAlmostEqual(row["alpha"], row["lambda"] * expected_m)
                self.assertIs(selection["test_labels_used_for_selection"], False)
                self.assertEqual(
                    selection["model_evaluation"],
                    {
                        "eval_built_after_selection_frozen": True,
                        "eval_targets_used_for_fitting_or_selection": False,
                    },
                )
                self.assertEqual(selection["eval_target_months"], list(definition.eval_target_months))

    def test_fold_mean_and_mask_artifacts(self) -> None:
        for fold, run_dir in self.run_dirs.items():
            definition = protocol.resolve_split(fold)
            label = definition.scope_label
            with self.subTest(fold=fold):
                self.assertFalse((run_dir / "models" / "TrainMean27.npz").exists())
                mean_path = run_dir / "models" / f"{definition.train_mean_method}.npz"
                with np.load(mean_path, allow_pickle=False) as handle:
                    self.assertEqual(
                        sorted(handle.files),
                        [f"train_mean{definition.fitting_month_count}", "train_observation_month_count"],
                    )
                    expected = self.signal[:, : definition.fitting_month_count].mean(
                        axis=1
                    )
                    np.testing.assert_array_equal(
                        handle[f"train_mean{definition.fitting_month_count}"],
                        expected,
                    )
                    self.assertEqual(
                        int(handle["train_observation_month_count"][0]),
                        definition.fitting_month_count,
                    )
                    self.assertNotIn("train_mean27", handle.files)
                masks = np.load(run_dir / "masks.npz", allow_pickle=False)
                self.assertEqual(
                    set(masks.files),
                    {
                        f"constant_{label}",
                        f"nonzero_activity_{label}",
                        "has_nonself_neighbor",
                        *{f"activity_{name}" for name in definition.activity_group_names},
                    },
                )
                partition = np.stack(
                    [
                        masks[f"activity_{name}"]
                        for name in definition.activity_group_names
                    ]
                ).sum(axis=0)
                np.testing.assert_array_equal(
                    partition, np.ones(self.signal.shape[0])
                )
                # Node 1 is constant over both A and B fitting scopes.
                self.assertTrue(bool(masks[f"constant_{label}"][1]))
                if fold == "A":
                    self.assertTrue(
                        bool(
                            masks[
                                f"activity_{definition.activity_group_names[0]}"
                            ][0]
                        )
                    )
                else:
                    self.assertFalse(
                        bool(
                            masks[
                                f"activity_{definition.activity_group_names[0]}"
                            ][0]
                        )
                    )
                for mask in masks.values():
                    np.asarray(mask)

    def test_fold_groups_before_and_after_main_scope_differ(self) -> None:
        run_dir = self.run_dirs["A"]
        masks = np.load(run_dir / "masks.npz", allow_pickle=False)
        audit = _read(run_dir / "audit.json")
        # Node 0: fit18 inactive, main 27 active.
        self.assertEqual(bool(masks["activity_fit18_inactive"][0]), True)
        self.assertEqual(
            audit["main_protocol_diagnostics"]["train_observation_months"],
            list(protocol.TRAIN_OBSERVATION_MONTHS),
        )
        # Nodes 0 and 1: fit18 constant, while the main 27 months vary.
        self.assertEqual(bool(masks["constant_fit18"][1]), True)
        self.assertEqual(
            audit["main_protocol_diagnostics"]["constant_node_count_train27"], 0
        )
        self.assertEqual(audit["fit18"]["constant_node_count"], 2)
        activity = (self.signal[:, :18] > 0).mean(axis=1)
        expected = {
            "fit18_inactive": int((activity == 0).sum()),
            "fit18_low": int(((activity > 0) & (activity <= 1 / 3)).sum()),
            "fit18_medium": int(
                ((activity > 1 / 3) & (activity <= 2 / 3)).sum()
            ),
            "fit18_high": int((activity > 2 / 3).sum()),
        }
        self.assertEqual(
            audit["fit18"]["activity_group_counts"], expected
        )
        self.assertEqual(sum(expected.values()), self.signal.shape[0])

    def test_fold_audit_scopes_main_and_full_period_diagnostics(self) -> None:
        for fold, run_dir in self.run_dirs.items():
            definition = protocol.resolve_split(fold)
            with self.subTest(fold=fold):
                audit = _read(run_dir / "audit.json")
                self.assertEqual(audit["fold"], fold)
                self.assertEqual(
                    audit[definition.scope_label]["fitting_observation_months"],
                    list(definition.fitting_observation_months),
                )
                nested = audit["main_protocol_diagnostics"]
                self.assertTrue(nested["descriptive_only"])
                self.assertIn("2021-01..2023-03", nested["scope"])
                self.assertEqual(
                    nested["train_observation_months"],
                    list(protocol.TRAIN_OBSERVATION_MONTHS),
                )
                self.assertIn("per_context", nested)
                self.assertIn(
                    "descriptive only", audit["full_36_month_diagnostics_scope"]
                )
                self.assertNotIn("train_observation_months", audit)

    def test_fold_predictions_gold_shapes_and_no_test_split(self) -> None:
        definition = protocol.FOLD_A
        run_dir = self.run_dirs["A"]
        node_count = self.signal.shape[0]
        expected_eval_starts = definition.evaluation_starts
        expected_validation = np.stack(
            [self.signal[:, s + 6 : s + 9] for s in definition.validation_starts]
        )
        expected_eval = np.stack(
            [self.signal[:, s + 6 : s + 9] for s in expected_eval_starts]
        )
        np.testing.assert_array_equal(
            np.load(run_dir / "gold" / "validation.npy"), expected_validation
        )
        np.testing.assert_array_equal(
            np.load(run_dir / "gold" / "eval.npy"), expected_eval
        )
        self.assertFalse((run_dir / "gold" / "test.npy").exists())
        for method in definition.naive_methods + (protocol.MODEL_NAME,):
            with self.subTest(method=method):
                self.assertFalse((run_dir / "predictions" / method / "test.npy").exists())
                for split in ("validation", "eval"):
                    array = np.load(run_dir / "predictions" / method / f"{split}.npy")
                    expected_len = (
                        len(definition.validation_starts)
                        if split == "validation"
                        else len(definition.evaluation_starts)
                    )
                    self.assertEqual(array.shape, (expected_len, node_count, 3))
        self.assertEqual(_read(run_dir / "gold" / "dtype.json")["dtype"], "float32")

    def test_fold_node_error_table_columns(self) -> None:
        import pandas as pd

        run_dir = self.run_dirs["A"]
        frame = pd.read_parquet(run_dir / "node-errors.parquet")
        for column in (
            "r0_id", "skill_id", "node_index", "method", "split", "context",
            "train_mean18", "activity_fit18", "activity_group_fit18",
            "constant_fit18", "absolute_error_sum", "squared_error_sum",
            "MAE", "MSE",
        ):
            self.assertIn(column, frame.columns)
        self.assertNotIn("train_mean27", frame.columns)
        self.assertEqual(set(frame["split"]), {"validation", "eval"})
        self.assertEqual(
            set(frame["activity_group_fit18"]),
            {"fit18_inactive", "fit18_low", "fit18_medium", "fit18_high"},
        )
        # Same masks as the metrics report and the masks file.
        masks = np.load(run_dir / "masks.npz", allow_pickle=False)
        group_zero = frame[(frame["method"] == "Zero") & (frame["split"] == "eval")]
        group_zero = group_zero.sort_values("node_index")
        np.testing.assert_array_equal(
            group_zero["activity_fit18"].to_numpy(),
            masks["nonzero_activity_fit18"],
        )
        np.testing.assert_array_equal(
            group_zero["constant_fit18"].to_numpy(),
            masks["constant_fit18"],
        )
        np.testing.assert_array_equal(
            group_zero["train_mean18"].to_numpy(),
            np.load(run_dir / "models" / "TrainMean18.npz")["train_mean18"],
        )

    def test_fold_metrics_use_fold_groups_and_no_test(self) -> None:
        run_dir = self.run_dirs["A"]
        metrics = _read(run_dir / "metrics.json")
        self.assertEqual(set(metrics["methods"]), {"validation", "eval"})
        self.assertNotIn("test", metrics["methods"])
        for split in ("validation", "eval"):
            report = metrics["methods"][split][protocol.MODEL_NAME]
            self.assertEqual(
                set(report["activity_groups"]),
                set(protocol.FOLD_A.activity_group_names),
            )
            self.assertEqual(
                set(report["constant_groups"]),
                {"constant_fit18", "nonconstant_fit18"},
            )
            self.assertEqual(
                report["training_all_zero_group"]["group"], "fit18_inactive"
            )
            self.assertEqual(len(report["windows"]), len(protocol.FOLD_A.starts_for(split)))
        self.assertIn("fold", metrics["fold"])
        self.assertIn("eval", metrics["aggregation_note"])
        self.assertEqual(
            set(metrics["relative_gains"]), {"validation", "eval"}
        )
        for split in ("validation", "eval"):
            self.assertIn(protocol.MODEL_NAME, metrics["relative_gains"][split])

    def test_fold_summary_names_scope_and_eval(self) -> None:
        text = (self.run_dirs["A"] / "summary.md").read_text(encoding="utf-8")
        self.assertIn("Fold: `A`", text)
        self.assertIn("TrainMean18", text)
        self.assertIn("validation` and `eval", text)
        self.assertIn("development_backtest", text)
        self.assertIn("2021-01", text)

    def test_fold_purpose_rules_and_no_formal_start(self) -> None:
        self.assertEqual(
            artifacts.default_runs_root(REPO_ROOT, "formal"),
            FORMAL_ROOT,
        )
        self.assertEqual(
            artifacts.default_runs_root(REPO_ROOT, "development"),
            REPO_ROOT / "scratch" / "nograph-baseline",
        )
        self.assertEqual(artifacts.PURPOSES, ("formal", "development"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_signal_demand(root, _boundary_signal(6))
            spec = fx.make_run_spec(
                FORMAL_ROOT,
                "r0",
                fixture["demand_path"],
                fixture["graph_path"],
                "fold-formal-reject",
                fold="A",
                purpose="development",
            )
            with self.assertRaises(runner.RunError):
                runner.execute_run(spec)
            self.assertFalse((FORMAL_ROOT / "fold-formal-reject").exists())
            target = root / "alias"
            target.symlink_to(FORMAL_ROOT)
            spec = fx.make_run_spec(
                target,
                "r0",
                fixture["demand_path"],
                fixture["graph_path"],
                "fold-symlink-reject",
                fold="A",
                purpose="development",
            )
            with self.assertRaises(runner.RunError):
                runner.execute_run(spec)
            self.assertFalse((FORMAL_ROOT / "fold-symlink-reject").exists())
            # Formal fold capability is covered without executing a run: root
            # resolution, spec serialization, purpose validation and the fold
            # payload's evidence role are all static.
            formal_spec = runner.RunSpec(
                data_name="r0",
                run_id="fold-formal-static",
                fold="A",
                purpose="formal",
                runs_root=str(root / "formal-temp"),
            )
            payload = formal_spec.to_dict()
            self.assertEqual(payload["fold"], "A")
            self.assertEqual(payload["purpose"], "formal")
            self.assertEqual(
                artifacts.default_runs_root(REPO_ROOT, payload["purpose"]),
                FORMAL_ROOT,
            )
            runner._validate_purpose(
                formal_spec,
                REPO_ROOT,
                artifacts.default_runs_root(REPO_ROOT, "formal"),
            )
            self.assertEqual(
                protocol.resolve_split(payload["fold"]).to_payload()[
                    "evidence_role"
                ],
                "development_backtest",
            )
            self.assertFalse((root / "formal-temp").exists())


class FoldCliAndSpecTests(unittest.TestCase):
    def test_public_parser_accepts_a_and_b(self) -> None:
        parser = cli.build_parser()
        for fold in ("A", "B"):
            parsed = parser.parse_args(
                ["run", "--data-name", "r0", "--run-id", "x", "--fold", fold]
            )
            self.assertEqual(parsed.fold, fold)
        default = parser.parse_args(["run", "--data-name", "r0", "--run-id", "x"])
        self.assertIsNone(default.fold)
        with self.assertRaises(SystemExit):
            parser.parse_args(
                ["run", "--data-name", "r0", "--run-id", "x", "--fold", "C"]
            )
        run_help = parser._subparsers._group_actions[0].choices["run"].format_help()
        self.assertIn("{A,B}", run_help)

    def test_main_config_serialization_has_no_empty_fold(self) -> None:
        spec = runner.RunSpec(data_name="r0", run_id="x")
        self.assertNotIn("fold", spec.to_dict())
        fold_spec = runner.RunSpec(data_name="r0", run_id="x", fold="A")
        self.assertEqual(fold_spec.to_dict()["fold"], "A")
        self.assertEqual(
            runner.RunSpec.from_dict(
                {"data_name": "r0", "run_id": "x", "fold": "B"}
            ).fold,
            "B",
        )

    def test_unknown_programmatic_fold_fails_before_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_signal_demand(root, _boundary_signal(6))
            runs_root = root / "runs"
            spec = fx.make_run_spec(
                runs_root,
                "r0",
                fixture["demand_path"],
                fixture["graph_path"],
                "unknown-fold",
                fold="C",
                purpose="development",
            )
            with self.assertRaises(protocol.ProtocolError):
                runner.execute_run(spec)
            self.assertFalse((runs_root / "unknown-fold").exists())

    def test_main_a_b_alternation_does_not_leak_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_signal_demand(root, _boundary_signal(6))
            main_dir = _run(root, "r0", fixture, "alt-main")
            fold_a = _run(root, "r0", fixture, "alt-a", fold="A")
            fold_b = _run(root, "r0", fixture, "alt-b", fold="B")
            main_again = _run(root, "r0", fixture, "alt-main-2")
            main_windows = _read(main_dir / "windows.json")
            self.assertEqual(set(main_windows["splits"]), {"train", "validation", "test"})
            self.assertNotIn("fold", main_windows)
            self.assertEqual(
                set(_read(fold_a / "windows.json")["splits"]),
                {"train", "validation", "eval"},
            )
            self.assertEqual(
                set(_read(fold_b / "windows.json")["splits"]),
                {"train", "validation", "eval"},
            )
            self.assertEqual(
                _read(main_dir / "windows.json"), _read(main_again / "windows.json")
            )
            self.assertEqual(
                _read(main_dir / "metrics.json")["methods"].keys(),
                {"validation", "test"},
            )
            self.assertEqual(
                _read(fold_a / "metrics.json")["methods"].keys(),
                {"validation", "eval"},
            )
            self.assertFalse((main_dir / "gold" / "eval.npy").exists())


class FoldCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.signal = _boundary_signal(6)
        cls.fixture = _write_signal_demand(cls.root / "fixture", cls.signal)
        cls.fold_a = _run(cls.root, "r0", cls.fixture, "check-a", fold="A")
        cls.fold_a_repeat = _run(cls.root, "r0", cls.fixture, "check-a-repeat", fold="A")
        cls.fold_b = _run(cls.root, "r0", cls.fixture, "check-b", fold="B")
        cls.fold_b_repeat = _run(
            cls.root, "r0", cls.fixture, "check-b-repeat", fold="B"
        )
        cls.main = _run(cls.root, "r0", cls.fixture, "check-main")
        cls.main_repeat = _run(cls.root, "r0", cls.fixture, "check-main-repeat")
        cls.seed_one = _run(cls.root, "r0", cls.fixture, "check-a-seed", fold="A", seed=1)
        cls.region_fixture = fx.build_fixture(
            cls.root / "region-fixture", "region", node_count=4
        )
        cls.region_fold_a = _run(
            cls.root, "region", cls.region_fixture, "check-region-a", fold="A"
        )
        changed = cls.signal.copy()
        # A month outside every fold A split target; predictions are identical.
        changed[:, 30] = changed[:, 30] + 1000.0
        cls.changed_fixture = _write_signal_demand(cls.root / "changed", changed)
        cls.changed_demand = _run(
            cls.root, "r0", cls.changed_fixture, "check-a-content", fold="A"
        )
        cls.report_root = cls.root / "reports"
        cls.report_root.mkdir()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _report(self, name: str) -> Path:
        return self.report_root / name

    def _recompute(self, run_dir: Path, name: str):
        return checks.command_recompute(
            run_dir=run_dir,
            repo_root=REPO_ROOT,
            command=["python", "-m", "benchmark.nograph_baseline", "recompute"],
            report_path=self._report(name),
        )

    def _compare(self, run_a: Path, run_b: Path, name: str):
        return checks.command_compare(
            run_a=run_a,
            run_b=run_b,
            repo_root=REPO_ROOT,
            command=["python", "-m", "benchmark.nograph_baseline", "compare"],
            report_path=self._report(name),
        )

    def test_recompute_fold_without_source_or_refit(self) -> None:
        for fold, run_dir in (("A", self.fold_a), ("B", self.fold_b)):
            with self.subTest(fold=fold):
                before = _tree_hash(run_dir)
                with mock.patch(
                    "benchmark.nograph_baseline.data.load_demand",
                    side_effect=AssertionError("source data must not be read"),
                ), mock.patch(
                    "benchmark.nograph_baseline.ridge.fit_numpy",
                    side_effect=AssertionError("models must not be refit"),
                ), mock.patch(
                    "benchmark.nograph_baseline.ridge.fit_candidates",
                    side_effect=AssertionError("models must not be refit"),
                ):
                    result = self._recompute(run_dir, f"recompute-{fold}.json")
                self.assertEqual(result["status"], "ok", msg=result["report"])
                self.assertEqual(_tree_hash(run_dir), before)
                report = result["report"]
                self.assertEqual(report["fold"], fold)
                self.assertEqual(report["evaluation_splits"], ["validation", "eval"])
                self.assertEqual(
                    report["saved_split"]["mean_artifact"],
                    f"models/TrainMean{18 if fold == 'A' else 21}.npz",
                )
                self.assertIn(
                    f"constant_fit{18 if fold == 'A' else 21}",
                    report["saved_split"]["consumed_mask_keys"],
                )
                self.assertEqual(
                    set(report["comparisons"]), {"validation", "eval"}
                )

    def test_compare_same_fold_same_seed(self) -> None:
        result = self._compare(self.fold_a, self.fold_a_repeat, "compare-a.json")
        self.assertEqual(result["status"], "ok", msg=result["report"])
        report = result["report"]
        self.assertEqual(report["fold_a"], "A")
        self.assertEqual(report["fold_b"], "A")
        self.assertTrue(report["methods_equal"])
        for key, row in report["prediction_comparisons"].items():
            self.assertEqual(row["status"], "ok")
            self.assertAlmostEqual(row["max_absolute_difference"], 0.0)
        for row in report["mae_relative_differences"].values():
            self.assertLessEqual(row["relative_difference"], 1e-6)
        self.assertEqual(
            set(report["prediction_comparisons"]),
            {f"{split}/{method}" for split in ("validation", "eval") for method in protocol.FOLD_A.naive_methods + (protocol.MODEL_NAME,)},
        )

    def test_compare_rejects_fold_dataset_content_and_seed_mismatches(self) -> None:
        cases = {
            "A-vs-B": (self.fold_a, self.fold_b),
            "main-vs-A": (self.main, self.fold_a),
            "dataset": (self.fold_a, self.region_fold_a),
            "content": (self.fold_a, self.changed_demand),
            "seed": (self.fold_a, self.seed_one),
        }
        for name, (run_a, run_b) in cases.items():
            with self.subTest(case=name):
                result = self._compare(run_a, run_b, f"neg-{name}.json")
                self.assertEqual(result["status"], "mismatch", msg=result["report"])
        # Different content with identical predictions must still be rejected.
        for split in ("validation", "eval"):
            np.testing.assert_array_equal(
                np.load(self.fold_a / "predictions" / protocol.MODEL_NAME / f"{split}.npy"),
                np.load(self.changed_demand / "predictions" / protocol.MODEL_NAME / f"{split}.npy"),
            )
        content = _read(self._report("neg-content.json"))["result"]
        self.assertFalse(content["identity_checks"]["demand_sha256"])
        self.assertTrue(content["identity_checks"]["node_keys_sha256"])
        fold = _read(self._report("neg-A-vs-B.json"))["result"]
        self.assertFalse(fold["identity_checks"]["fold"])
        main = _read(self._report("neg-main-vs-A.json"))["result"]
        self.assertFalse(main["identity_checks"]["fold"])
        dataset = _read(self._report("neg-dataset.json"))["result"]
        self.assertFalse(dataset["identity_checks"]["dataset"])
        seed = _read(self._report("neg-seed.json"))["result"]
        self.assertFalse(seed["identity_checks"]["seed"])

    def test_compare_does_not_mask_missing_methods_with_an_intersection(self) -> None:
        copy_dir = self.root / "main-method-missing"
        shutil.copytree(self.main_repeat, copy_dir)
        metrics = _read(copy_dir / "metrics.json")
        del metrics["methods"]["test"]["Zero"]
        _write(copy_dir / "metrics.json", metrics)
        result = self._compare(self.main, copy_dir, "neg-methods.json")
        self.assertEqual(result["status"], "mismatch")
        report = result["report"]
        self.assertFalse(report["methods_equal"])
        self.assertIn("Zero", report["missing_methods"]["run_b"])
        self.assertIn("Zero", report["missing_methods"]["run_b"])
        self.assertEqual(report["prediction_comparisons"]["test/Zero"]["status"], "ok")

    def test_align_v2_rejects_every_fold(self) -> None:
        reference = self.root / "reference.log"
        reference.write_text(
            json.dumps({"dataset": "r0", "nodes": 6}) + "\n", encoding="utf-8"
        )
        for label, run_dir in (("A", self.fold_a), ("B", self.fold_b)):
            with self.subTest(fold=label):
                before = _tree_hash(run_dir)
                reference_before = reference.read_bytes()
                result = checks.command_align_v2(
                    run_dir=run_dir,
                    reference=reference,
                    repo_root=REPO_ROOT,
                    command=["python", "-m", "benchmark.nograph_baseline", "align-v2"],
                    report_path=self._report(f"align-{label}.json"),
                )
                self.assertEqual(result["status"], "failed")
                message = result["report"]["error"]["message"]
                self.assertIn("fold records", message)
                self.assertIn(f"fold run {label}", message)
                self.assertEqual(_tree_hash(run_dir), before)
                self.assertEqual(reference.read_bytes(), reference_before)
                self.assertFalse(_read(self._report(f"align-{label}.json"))["result"].get("checks"))
        # A reference that pretends to carry a fold record is rejected for each
        # fold too.
        fabricated = self.root / "fabricated-fold-reference.log"
        fabricated.write_text(
            json.dumps({"dataset": "r0", "fold": "A", "nodes": 6}) + "\n",
            encoding="utf-8",
        )
        for label, run_dir in (("A", self.fold_a), ("B", self.fold_b)):
            with self.subTest(fold=label, reference="fabricated"):
                result = checks.command_align_v2(
                    run_dir=run_dir,
                    reference=fabricated,
                    repo_root=REPO_ROOT,
                    command=["python", "-m", "benchmark.nograph_baseline", "align-v2"],
                    report_path=self._report(f"align-fabricated-{label}.json"),
                )
                self.assertEqual(result["status"], "failed")
                self.assertIn("fold records", result["report"]["error"]["message"])
                self.assertIn(f"fold run {label}", result["report"]["error"]["message"])

    def test_inconsistent_fold_evidence_fails_without_main_fallback(self) -> None:
        mutations = {
            "unknown-fold": lambda documents: documents["config"].setdefault("spec", {}).update({"fold": "C"}),
            "missing-windows-fold": lambda documents: documents["windows"].pop("fold"),
            "conflicting-fold": lambda documents: documents["metrics"]["fold"].update({"fold": "B"}),
            "wrong-fitting-count": lambda documents: documents["config"]["fold"].update({"fitting_month_count": 19}),
            "wrong-reason": lambda documents: documents["windows"]["omitted_reasons"].update({"10": "wrong"}),
            "wrong-train-mean": lambda documents: documents["selection"]["normalization"].update({"train_mean_method": "TrainMean27"}),
        }
        for index, (name, mutate) in enumerate(mutations.items()):
            with self.subTest(case=name):
                target = self.root / f"mutated-{index}"
                shutil.copytree(self.fold_a, target)
                documents = {
                    "config": _read(target / "config.json"),
                    "windows": _read(target / "windows.json"),
                    "metrics": _read(target / "metrics.json"),
                    "selection": _read(target / "selection.json"),
                }
                mutate(documents)
                for key, payload in documents.items():
                    _write(target / f"{key}.json", payload)
                result = self._recompute(target, f"mutated-{index}.json")
                self.assertEqual(result["status"], "failed", msg=result["report"])
                self.assertIn(
                    result["report"]["error"]["type"],
                    {"CheckError", "ProtocolError"},
                )

    def test_eval_evidence_without_fold_metadata_is_not_main(self) -> None:
        target = self.root / "fold-clues-removed"
        shutil.copytree(self.fold_a, target)
        for name in ("config", "metrics", "provenance", "selection"):
            payload = _read(target / f"{name}.json")
            payload.pop("fold", None)
            if name == "config":
                payload.get("spec", {}).pop("fold", None)
            _write(target / f"{name}.json", payload)
        windows = _read(target / "windows.json")
        windows.pop("fold")
        _write(target / "windows.json", windows)
        result = self._recompute(target, "clues-removed.json")
        self.assertEqual(result["status"], "failed")
        self.assertIn("without fold metadata", result["report"]["error"]["message"])

    def test_corrupt_fold_masks_node_columns_and_collision(self) -> None:
        # 1. Missing activity mask key.
        target = self.root / "corrupt-mask"
        shutil.copytree(self.fold_a, target)
        masks = dict(np.load(target / "masks.npz", allow_pickle=False))
        del masks["activity_fit18_low"]
        np.savez(target / "masks.npz", **masks)
        result = self._recompute(target, "corrupt-mask.json")
        self.assertEqual(result["status"], "failed")
        # 2. Corrupted node-error activity group column.
        target = self.root / "corrupt-node-errors"
        shutil.copytree(self.fold_a, target)
        import pandas as pd

        frame = pd.read_parquet(target / "node-errors.parquet")
        frame.loc[frame.index[0], "activity_group_fit18"] = "fit18_inactive"
        if frame.loc[frame.index[0], "activity_group_fit18"] == "fit18_inactive" and (
            frame["activity_group_fit18"] == "fit18_inactive"
        ).all():
            frame.loc[frame.index[0], "activity_group_fit18"] = "fit18_high"
        frame.to_parquet(target / "node-errors.parquet", index=False)
        result = self._recompute(target, "corrupt-node-errors.json")
        self.assertEqual(result["status"], "mismatch")
        self.assertGreater(
            result["report"]["node_error_comparison"]["categorical_mismatches"], 0
        )
        # 3. Missing prediction array.
        target = self.root / "missing-array"
        shutil.copytree(self.fold_a, target)
        (target / "predictions" / "SharedRidge" / "eval.npy").unlink()
        result = self._recompute(target, "missing-array.json")
        self.assertEqual(result["status"], "failed")
        # 4. Report destination collision and destination inside the input run.
        collision = self._report("collision.json")
        collision.write_text("taken", encoding="utf-8")
        with self.assertRaises(checks.CheckError):
            self._recompute(self.fold_a, "collision.json")
        with self.assertRaises(checks.CheckError):
            checks.command_recompute(
                run_dir=self.fold_a,
                repo_root=REPO_ROOT,
                command=["x"],
                report_path=self.fold_a / "inside.json",
            )
        # 5. The input tree is unchanged by failed and successful checks.
        before = _tree_hash(self.fold_a)
        result = self._recompute(self.fold_a, "recompute-A-after.json")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(_tree_hash(self.fold_a), before)

    def test_recompute_rejects_contradictory_fold_masks(self) -> None:
        def copy_run(name: str) -> Path:
            target = self.root / name
            shutil.copytree(self.fold_a, target)
            return target

        def mask_mutation(
            target: Path, key: str, value
        ) -> None:
            masks = dict(np.load(target / "masks.npz", allow_pickle=False))
            masks[key] = np.array(value, copy=True)
            np.savez(target / "masks.npz", **masks)

        # activity says 0 (inactive) while the boolean group still says high.
        target = copy_run("semantic-activity-group")
        masks = dict(np.load(target / "masks.npz", allow_pickle=False))
        activity = np.array(masks["nonzero_activity_fit18"], copy=True)
        activity[1] = 0.0
        masks["nonzero_activity_fit18"] = activity
        np.savez(target / "masks.npz", **masks)
        import pandas as pd

        frame = pd.read_parquet(target / "node-errors.parquet")
        frame.loc[frame["node_index"] == 1, "activity_fit18"] = 0.0
        frame.to_parquet(target / "node-errors.parquet", index=False)
        result = self._recompute(target, "semantic-activity-group.json")
        self.assertEqual(result["status"], "failed", msg=result["report"])
        self.assertIn(
            "activity mask", result["report"]["error"]["message"]
        )
        self.assertEqual(
            cli.main(
                [
                    "recompute",
                    "--run-dir",
                    str(target),
                    "--report",
                    str(self.report_root / "semantic-activity-cli.json"),
                ]
            ),
            1,
        )
        self.assertTrue((self.report_root / "semantic-activity-cli.json").is_file())

        # Overlapping and missing activity groups.
        overlap = copy_run("semantic-overlap")
        mask_mutation(overlap, "activity_fit18_high", [True, False, False, False, False, False])
        result = self._recompute(overlap, "semantic-overlap.json")
        self.assertEqual(result["status"], "failed")
        self.assertIn("partition", result["report"]["error"]["message"])

        missing = copy_run("semantic-missing-group")
        mask_mutation(missing, "activity_fit18_inactive", [False, False, False, False, False, False])
        result = self._recompute(missing, "semantic-missing-group.json")
        self.assertEqual(result["status"], "failed")
        self.assertIn("partition", result["report"]["error"]["message"])

        # A legal 9/18 fraction placed in the wrong boundary group.
        wrong_boundary = copy_run("semantic-boundary")
        masks = dict(np.load(wrong_boundary / "masks.npz", allow_pickle=False))
        activity = np.array(masks["nonzero_activity_fit18"], copy=True)
        activity[2] = 0.5
        masks["nonzero_activity_fit18"] = activity
        np.savez(wrong_boundary / "masks.npz", **masks)
        result = self._recompute(wrong_boundary, "semantic-boundary.json")
        self.assertEqual(result["status"], "failed")
        self.assertIn("disagrees", result["report"]["error"]["message"])

        # Illegal fractions, wrong dtype and contradictory normalization.
        for name, value in (
            ("semantic-nan", np.nan),
            ("semantic-above-one", 1.2),
            ("semantic-negative", -0.1),
        ):
            target = copy_run(name)
            masks = dict(np.load(target / "masks.npz", allow_pickle=False))
            activity = np.array(masks["nonzero_activity_fit18"], copy=True)
            activity[0] = value
            masks["nonzero_activity_fit18"] = activity
            np.savez(target / "masks.npz", **masks)
            result = self._recompute(target, f"{name}.json")
            self.assertEqual(result["status"], "failed", msg=(name, result["report"]))

        integer_activity = copy_run("semantic-integer-activity")
        masks = dict(np.load(integer_activity / "masks.npz", allow_pickle=False))
        masks["nonzero_activity_fit18"] = np.asarray(
            masks["nonzero_activity_fit18"], dtype=np.int64
        )
        np.savez(integer_activity / "masks.npz", **masks)
        result = self._recompute(integer_activity, "semantic-integer-activity.json")
        self.assertEqual(result["status"], "failed")
        self.assertIn("floating-point", result["report"]["error"]["message"])

        for name, key, value in (
            ("semantic-group-dtype", "activity_fit18_low", np.zeros(6, dtype=np.int8)),
            ("semantic-constant-dtype", "constant_fit18", np.zeros(6, dtype=np.int8)),
        ):
            target = copy_run(name)
            mask_mutation(target, key, value)
            result = self._recompute(target, f"{name}.json")
            self.assertEqual(result["status"], "failed")

        for name, field, value in (
            ("semantic-ddof", "ddof", 1),
            ("semantic-constant-std", "constant_node_std", 2.0),
            ("semantic-applied", "applied_to_inputs_and_targets", False),
        ):
            target = copy_run(name)
            selection = _read(target / "selection.json")
            selection["normalization"][field] = value
            _write(target / "selection.json", selection)
            result = self._recompute(target, f"{name}.json")
            self.assertEqual(result["status"], "failed", msg=(name, result["report"]))

    def test_fold_boundary_activity_values_are_accepted(self) -> None:
        signal = np.zeros((4, 36), dtype=np.float32)
        for row, active_months in enumerate((0, 6, 12, 18)):
            signal[row, :active_months] = 1.0
        # Keep the all-active node nonconstant without changing activity 1.
        signal[3, :18] = 1.0 + (np.arange(18, dtype=np.float32) % 2.0)
        fixture = _write_signal_demand(self.root / "boundary-fixture", signal)
        run_dir = _run(self.root, "r0", fixture, "boundary-activity", fold="A")
        masks = np.load(run_dir / "masks.npz", allow_pickle=False)
        self.assertEqual(bool(masks["activity_fit18_inactive"][0]), True)
        self.assertEqual(bool(masks["activity_fit18_low"][1]), True)
        self.assertEqual(bool(masks["activity_fit18_medium"][2]), True)
        self.assertEqual(bool(masks["activity_fit18_high"][3]), True)
        np.testing.assert_array_equal(
            masks["nonzero_activity_fit18"],
            np.array([0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0], dtype=np.float64),
        )
        result = self._recompute(run_dir, "boundary-activity.json")
        self.assertEqual(result["status"], "ok", msg=result["report"])

    def test_compare_consumed_inputs_include_fold_metadata_and_mean(self) -> None:
        for fold, run_a, run_b, mean_relative in (
            ("A", self.fold_a, self.fold_a_repeat, "models/TrainMean18.npz"),
            ("B", self.fold_b, self.fold_b_repeat, "models/TrainMean21.npz"),
        ):
            with self.subTest(fold=fold):
                result = self._compare(
                    run_a, run_b, f"compare-consumed-{fold}.json"
                )
                self.assertEqual(result["status"], "ok", msg=result["report"])
                inputs = result["envelope"]["inputs"]
                for label, run_dir in (("a", run_a), ("b", run_b)):
                    consumed = inputs[f"run_{label}_consumed_sha256"]
                    for relative in (
                        "windows.json",
                        "provenance.json",
                        mean_relative,
                    ):
                        with self.subTest(label=label, relative=relative):
                            self.assertIn(relative, consumed)
                            self.assertEqual(
                                consumed[relative],
                                sha256_file(run_dir / relative),
                            )
        # A consumed metadata contradiction fails with a safe report and does
        # not mutate either input.
        target = self.root / "compare-consumed-conflict"
        shutil.copytree(self.fold_a_repeat, target)
        provenance = _read(target / "provenance.json")
        provenance["fold"]["fold"] = "B"
        _write(target / "provenance.json", provenance)
        before_a = _tree_hash(self.fold_a)
        before_b = _tree_hash(target)
        failed = self._compare(self.fold_a, target, "compare-consumed-conflict.json")
        self.assertEqual(failed["status"], "failed", msg=failed["report"])
        self.assertTrue(
            (self.report_root / "compare-consumed-conflict.json").is_file()
        )
        self.assertEqual(_tree_hash(self.fold_a), before_a)
        self.assertEqual(_tree_hash(target), before_b)

    def test_align_v2_rejects_fold_before_reference_access(self) -> None:
        missing = self.root / "missing-reference.log"
        self.assertFalse(missing.exists())
        malformed = self.root / "malformed-reference.log"
        malformed.write_text("this is not a JSON line\n", encoding="utf-8")
        for label, run_dir in (("A", self.fold_a), ("B", self.fold_b)):
            for kind, reference in (("missing", missing), ("malformed", malformed)):
                with self.subTest(fold=label, reference=kind):
                    before = _tree_hash(run_dir)
                    reference_before = (
                        reference.read_bytes() if reference.exists() else None
                    )
                    result = checks.command_align_v2(
                        run_dir=run_dir,
                        reference=reference,
                        repo_root=REPO_ROOT,
                        command=["python", "-m", "benchmark.nograph_baseline", "align-v2"],
                        report_path=self._report(f"align-{kind}-{label}.json"),
                    )
                    self.assertEqual(result["status"], "failed")
                    message = result["report"]["error"]["message"]
                    self.assertIn("fold records", message)
                    self.assertIn(f"fold run {label}", message)
                    self.assertNotIn("does not exist", message)
                    self.assertNotIn("invalid JSON line", message)
                    self.assertFalse(missing.exists())
                    self.assertEqual(_tree_hash(run_dir), before)
                    if reference_before is not None:
                        self.assertEqual(reference.read_bytes(), reference_before)

    def test_previous_report_alias_is_single_exclusive_json(self) -> None:
        report_root = self.root / "legacy-reports"
        result = checks.command_recompute(
            run_dir=self.fold_a,
            repo_root=REPO_ROOT,
            command=["x"],
            run_id="fold-legacy",
            runs_root=report_root,
        )
        self.assertEqual(result["status"], "ok")
        self.assertTrue((report_root / "fold-legacy.json").is_file())
        self.assertEqual(len(list(report_root.iterdir())), 1)


class FoldMainRegressionTests(unittest.TestCase):
    def test_main_artifacts_keep_historical_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_signal_demand(root, _boundary_signal(6))
            run_dir = _run(root, "r0", fixture, "main-contract")
            windows = _read(run_dir / "windows.json")
            config = _read(run_dir / "config.json")
            metrics = _read(run_dir / "metrics.json")
            selection = _read(run_dir / "selection.json")
            self.assertNotIn("fold", windows)
            self.assertNotIn("fold", config)
            self.assertNotIn("fold", metrics)
            self.assertNotIn("fold", selection)
            self.assertNotIn("evidence_role", metrics)
            self.assertEqual(set(metrics["methods"]), {"validation", "test"})
            self.assertTrue((run_dir / "models" / "TrainMean27.npz").exists())
            self.assertFalse((run_dir / "models" / "TrainMean18.npz").exists())
            self.assertEqual(
                set(np.load(run_dir / "masks.npz", allow_pickle=False).files),
                {
                    "constant_train27",
                    "nonzero_activity_train27",
                    "has_nonself_neighbor",
                    "activity_inactive",
                    "activity_low",
                    "activity_medium",
                    "activity_high",
                },
            )
            import pandas as pd

            node_errors = pd.read_parquet(run_dir / "node-errors.parquet")
            self.assertIn("train_mean27", node_errors.columns)
            self.assertNotIn("activity_fit18", node_errors.columns)
            self.assertTrue((run_dir / "gold" / "test.npy").exists())
            self.assertFalse((run_dir / "gold" / "eval.npy").exists())
            self.assertEqual(selection["training_samples_M"], 19 * 6)
            self.assertEqual(
                selection["training_samples_M"],
                selection["expected_training_samples_M"],
            )
            recompute = checks.command_recompute(
                run_dir=run_dir,
                repo_root=REPO_ROOT,
                command=["x"],
                report_path=root / "main-recompute.json",
            )
            self.assertEqual(recompute["status"], "ok", msg=recompute["report"])
            self.assertIsNone(recompute["report"]["fold"])
            compare = checks.command_compare(
                run_a=run_dir,
                run_b=_run(root, "r0", fixture, "main-contract-2"),
                repo_root=REPO_ROOT,
                command=["x"],
                report_path=root / "main-compare.json",
            )
            self.assertEqual(compare["status"], "ok", msg=compare["report"])


class FoldEndToEndCliTests(unittest.TestCase):
    """Task 6.1: A/B x r0/region/r2 through the public CPU CLI."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.runs_root = cls.root / "runs"
        cls.fixtures = {
            "r0": fx.build_fixture(cls.root / "fixture-r0", "r0", node_count=6, seed=3),
            "region": fx.build_fixture(
                cls.root / "fixture-region", "region", node_count=3, seed=3
            ),
            "r2": fx.build_fixture(
                cls.root / "fixture-r2", "r2", contexts=3, skills=2, seed=3
            ),
        }
        cls.runs = {}
        for data_name, fixture in cls.fixtures.items():
            for fold in ("A", "B"):
                run_id = f"e2e-{data_name}-{fold.lower()}"
                argv = [
                    sys.executable,
                    "-m",
                    "benchmark.nograph_baseline",
                    "run",
                    "--data-name",
                    data_name,
                    "--mode",
                    "count",
                    "--seed",
                    "0",
                    "--fold",
                    fold,
                    "--run-id",
                    run_id,
                    "--purpose",
                    "development",
                    "--runs-root",
                    str(cls.runs_root),
                    "--demand-path",
                    str(fixture["demand_path"]),
                    "--graph-path",
                    str(fixture["graph_path"]),
                ]
                completed = subprocess.run(
                    argv, cwd=str(REPO_ROOT), capture_output=True, text=True
                )
                if completed.returncode != 0:
                    raise AssertionError(
                        f"{run_id} failed:\n{completed.stdout}\n{completed.stderr}"
                    )
                cls.runs[(data_name, fold)] = cls.runs_root / run_id

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_every_fold_dataset_run_completes_development_contract(self) -> None:
        for (data_name, fold), run_dir in self.runs.items():
            definition = protocol.resolve_split(fold)
            with self.subTest(dataset=data_name, fold=fold):
                self.assertEqual(_read(run_dir / "status.json")["state"], "success")
                self.assertEqual(_read(run_dir / "status.json")["purpose"], "development")
                self.assertFalse(artifacts.is_within(run_dir, FORMAL_ROOT))
                metrics = _read(run_dir / "metrics.json")
                self.assertEqual(set(metrics["methods"]), {"validation", "eval"})
                self.assertNotIn("test", metrics["methods"])
                selection = _read(run_dir / "selection.json")
                self.assertEqual(
                    selection["normalization"]["train_mean_method"],
                    definition.train_mean_method,
                )
                self.assertEqual(
                    selection["training_samples_M"],
                    len(definition.train_starts) * len(self.fixtures[data_name]["keys"]),
                )
                self.assertTrue(
                    (run_dir / "models" / f"{definition.train_mean_method}.npz").is_file()
                )
                self.assertFalse((run_dir / "models" / "TrainMean27.npz").exists())
                self.assertFalse((run_dir / "gold" / "test.npy").exists())
                node_count = len(self.fixtures[data_name]["keys"])
                for method in definition.naive_methods + (protocol.MODEL_NAME,):
                    for split in ("validation", "eval"):
                        array = np.load(
                            run_dir / "predictions" / method / f"{split}.npy",
                            allow_pickle=False,
                        )
                        self.assertEqual(array.shape[1], node_count)
                report = next(
                    iter(
                        _read(run_dir / "metrics.json")["methods"]["eval"][
                            protocol.MODEL_NAME
                        ]["activity_groups"]
                    )
                )
                self.assertTrue(report.startswith(f"fit{definition.fitting_month_count}_"))
                import pandas as pd

                nodes = pd.read_parquet(run_dir / "nodes.parquet")
                from benchmark.nograph_baseline import protocol as nb_protocol

                self.assertEqual(
                    list(nodes.columns),
                    ["node_index", *nb_protocol.node_key_columns(data_name)],
                )
                self.assertEqual(
                    nodes["node_index"].tolist(), list(range(node_count))
                )

    def test_fold_help_and_invalid_value(self) -> None:
        parser = cli.build_parser()
        argv = [
            "run", "--data-name", "r0", "--run-id", "x", "--fold", "C"
        ]
        with self.assertRaises(SystemExit):
            parser.parse_args(argv)


if __name__ == "__main__":
    unittest.main()
