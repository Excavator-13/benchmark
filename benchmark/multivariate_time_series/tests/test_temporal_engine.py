"""Full-window optimization, clipping records and immutable best snapshots."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

import temporal_fixtures as fx
from benchmark.multivariate_time_series.temporal import data as td
from benchmark.multivariate_time_series.temporal import engine as temporal_engine
from benchmark.multivariate_time_series.temporal import model as temporal_model
from benchmark.multivariate_time_series.temporal import protocol


class WindowOptimizationTests(unittest.TestCase):
    def setUp(self) -> None:
        keys = fx.r0_keys(13)
        self.data = td.from_arrays("r0", keys, fx.synthetic_signal(13, seed=9))
        self.arrays = self.data.fit_arrays()

    def _run(self, *, epochs: int = 1, chunk: int = 13, seed: int = 0):
        config = protocol.FitConfig(
            model="GRU", seed=seed, epochs=epochs, hidden_size=4, node_chunk=chunk
        )
        result = temporal_engine.run_trajectory(self.arrays, config)
        return result

    def test_uneven_chunks_match_the_complete_window_reference(self):
        whole = self._run(epochs=1, chunk=13)
        uneven = self._run(epochs=1, chunk=5)
        reference = temporal_engine.Trajectory(self.arrays, whole.config)
        loss_whole = temporal_engine.squared_error_sum(
            reference.model,
            self.arrays.train_inputs[0],
            self.arrays.train_targets[0],
            reference.scale,
            13,
            self.arrays.node_count * protocol.p01.HORIZON,
        )
        loss_uneven = temporal_engine.squared_error_sum(
            reference.model,
            self.arrays.train_inputs[0],
            self.arrays.train_targets[0],
            reference.scale,
            5,
            self.arrays.node_count * protocol.p01.HORIZON,
        )
        self.assertAlmostEqual(
            float(loss_whole.detach()), float(loss_uneven.detach()), places=6
        )
        self.assertEqual(whole.updates, protocol.UPDATES_PER_EPOCH)
        self.assertEqual(uneven.updates, protocol.UPDATES_PER_EPOCH)
        for name, tensor in whole.best_model_state.items():
            self.assertTrue(
                torch.allclose(
                    tensor,
                    uneven.best_model_state[name],
                    rtol=1e-6,
                    atol=1e-8,
                ),
                f"chunking changed the update for {name}",
            )

    def test_one_step_per_window_in_training_order(self):
        result = self._run(epochs=2, chunk=4)
        self.assertEqual(result.updates, 2 * protocol.UPDATES_PER_EPOCH)
        first_epoch = [record["window_start"] for record in result.update_records[:19]]
        second_epoch = [record["window_start"] for record in result.update_records[19:]]
        self.assertEqual(first_epoch, list(range(19)))
        self.assertEqual(second_epoch, list(range(19)))
        self.assertEqual(
            [record["update"] for record in result.update_records],
            list(range(1, 39)),
        )
        windows = {record["window_index"] for record in result.update_records}
        self.assertEqual(windows, set(range(19)))
        self.assertTrue(all(record["clipped"] for record in result.update_records))
        self.assertTrue(
            all(record["pre_clip_norm"] > protocol.GRAD_CLIP_NORM
                for record in result.update_records)
        )

    def test_window_prediction_is_independent_of_evaluation_order(self):
        model = temporal_model.build_model(
            protocol.FitConfig(model="GRU", seed=2, epochs=1, hidden_size=4, node_chunk=3)
        )
        windows = self.arrays.train_inputs
        alone, _ = temporal_model.predict(model, windows[5:6], 1.0, 3)
        ordered, _ = temporal_model.predict(model, windows, 1.0, 3)
        permuted, _ = temporal_model.predict(
            model, windows[[18, 0, 5, 11, 3]], 1.0, 3
        )
        np.testing.assert_array_equal(alone[0], ordered[5])
        np.testing.assert_array_equal(alone[0], permuted[2])

    def test_all_zero_training_scale_and_finite_repeated_windows(self):
        zero_data = td.from_arrays("r0", fx.r0_keys(4), np.zeros((4, 36)))
        arrays = zero_data.fit_arrays()
        self.assertEqual(zero_data.training_rms()["scale"], 1.0)
        config = protocol.FitConfig(model="GRU", seed=1, epochs=2, hidden_size=4, node_chunk=2)
        result = temporal_engine.run_trajectory(arrays, config)
        self.assertTrue(np.isfinite(result.validation_prediction).all())
        model = temporal_model.build_model(config)
        model.load_state_dict(result.best_model_state)
        repeated = np.repeat(arrays.train_inputs[0:1], 3, axis=0)
        predictions, _ = temporal_model.predict(model, repeated, 1.0, 2)
        np.testing.assert_array_equal(predictions[0], predictions[1])
        np.testing.assert_array_equal(predictions[0], predictions[2])

    def test_configuration_violations_are_rejected(self):
        for override in (
            {"epochs": 101},
            {"threads": 2},
            {"learning_rate": 0.01},
            {"node_chunk": 0},
            {"grad_clip": 0.0},
            {"model": "MLP"},
            {"diagnostic_epochs": (1, 2)},
        ):
            with self.subTest(override=override):
                with self.assertRaises(protocol.ProtocolError):
                    protocol.FitConfig(**override).validate()
        protocol.require_formal_controls(
            protocol.FitConfig(hidden_size=protocol.HIDDEN_SIZE)
        )
        with self.assertRaises(protocol.ProtocolError):
            protocol.require_formal_controls(protocol.FitConfig(epochs=2))

    def test_diagnostic_node_scores_and_history(self):
        result = self._run(epochs=10, chunk=5)
        self.assertEqual(len(result.history), 10)
        self.assertIn("10", result.scores)
        score = result.scores["10"]
        self.assertEqual(score["parameter_state"], "fixed")
        self.assertIn("train", score)
        self.assertIn("validation", score)
        self.assertNotIn("50", result.scores)
        record = result.history[0]
        self.assertIn("online_train_loss_mixed_parameters", record)
        self.assertIn("validation_MSE", record)
        self.assertIn("wall_seconds", record)
        self.assertEqual(
            result.fit_diagnostics["online_train_loss_note"],
            (
                "history.online_train_loss_mixed_parameters accumulates losses "
                "computed on pre-update parameters and is not a fixed-checkpoint "
                "training MSE"
            ),
        )


class BestSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.data = td.from_arrays(
            "r0", fx.r0_keys(6), fx.synthetic_signal(6, seed=4)
        )
        self.arrays = self.data.fit_arrays()
        self.config = protocol.FitConfig(
            model="GRU", seed=0, epochs=3, hidden_size=4, node_chunk=3
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_initialization_is_recorded_but_never_selected(self):
        def sabotage(trajectory):
            if trajectory.completed_epoch == 1:
                with torch.no_grad():
                    for parameter in trajectory.model.parameters():
                        parameter.fill_(1000.0)

        result = temporal_engine.run_trajectory(
            self.arrays,
            self.config,
            hooks=temporal_engine.Hooks(on_epoch_complete=sabotage),
        )
        self.assertIn("init", result.scores)
        self.assertEqual(result.scores["init"]["epoch"], 0)
        self.assertGreaterEqual(result.best["epoch"], 1)
        self.assertFalse(result.best["initialization_selected"])

    def test_best_epoch_stays_immutable_when_later_epochs_worsen(self):
        captured: dict = {}

        def capture_and_break(trajectory):
            if trajectory.completed_epoch == 1:
                captured["epoch"] = trajectory.best.epoch
                captured["validation"] = dict(trajectory.best.validation)
                captured["optimizer"] = temporal_model.deepcopy_state(
                    trajectory.best.optimizer_state
                )
                captured["model"] = temporal_model.deepcopy_state(
                    trajectory.best.model_state
                )
                with torch.no_grad():
                    for parameter in trajectory.model.parameters():
                        parameter.fill_(1000.0)

        result = temporal_engine.run_trajectory(
            self.arrays,
            self.config,
            hooks=temporal_engine.Hooks(on_epoch_complete=capture_and_break),
        )
        self.assertEqual(captured["epoch"], 1)
        self.assertEqual(result.best["epoch"], 1)
        self.assertEqual(result.best["validation"], captured["validation"])
        for name, tensor in captured["model"].items():
            self.assertTrue(torch.equal(tensor, result.best_model_state[name]))
        # Later updates happened and changed the live optimizer state while the
        # best snapshot still holds the epoch-1 moment estimates.
        self.assertGreater(len(result.history), 1)
        self.assertGreater(
            result.history[-1]["validation_MSE"],
            result.history[0]["validation_MSE"],
        )
        changed = False
        for key, state in captured["optimizer"]["state"].items():
            live = result.final_optimizer_state["state"].get(key, {})
            for name, tensor in state.items():
                if torch.is_tensor(tensor) and name in live:
                    if not torch.equal(tensor, live[name]):
                        changed = True
        self.assertTrue(changed)
        for key, state in result.best_optimizer_state["state"].items():
            for name, tensor in state.items():
                if torch.is_tensor(tensor):
                    self.assertTrue(
                        torch.equal(
                            tensor,
                            captured["optimizer"]["state"][key][name],
                        ),
                        "the best optimizer state changed with later steps",
                    )

    def test_exact_tie_keeps_the_earliest_checkpoint(self):
        trajectory = temporal_engine.Trajectory(self.arrays, self.config)
        trajectory.updates = protocol.UPDATES_PER_EPOCH
        trajectory._maybe_select(1, {"MSE": 5.0, "MAE": 2.0})
        trajectory._maybe_select(2, {"MSE": 5.0, "MAE": 1.0})
        self.assertEqual(trajectory.best.epoch, 1)
        trajectory._maybe_select(3, {"MSE": 4.9, "MAE": 1.0})
        self.assertEqual(trajectory.best.epoch, 3)

    def test_restored_best_reproduces_saved_validation_metrics(self):
        result = temporal_engine.run_trajectory(self.arrays, self.config)
        reproduction = result.scores["best"]["reproduction"]
        self.assertEqual(reproduction["status"], "pass")
        self.assertLessEqual(
            max(reproduction["absolute_differences"].values()), 1e-6
        )
        self.assertEqual(
            result.validation_metrics["MSE"], reproduction["reevaluated"]["MSE"]
        )


class ArtifactSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.keys = fx.r0_keys(5)
        self.path = fx.write_demand(
            self.root / "r0.parquet", "r0", self.keys, fx.synthetic_signal(5, seed=2)
        )
        self.data = fx.load_data("r0", self.path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_fit_writes_the_complete_evidence_set(self):
        result = fx.fit_run(
            self.root / "runs",
            run_id="evidence",
            data=self.data,
            data_path=self.path,
            epochs=2,
        )
        directory = Path(result["run_dir"])
        for relative in (
            "config.json",
            "command.json",
            "provenance.json",
            "status.json",
            "report.json",
            "summary.md",
            "preprocessing.json",
            "keys.npy",
            "months.json",
            "splits.json",
            "history.json",
            "scores.json",
            "gradients.json",
            "baselines.json",
            "fit-diagnostics.json",
            "masks.npz",
            "validation/prediction.npy",
            "validation/gold.npy",
            "validation/metrics.json",
            "weights/best.pt",
            "recovery/last.pt",
            "cost.json",
        ):
            self.assertTrue((directory / relative).is_file(), relative)
        config = fx.read_json(directory / "config.json")
        self.assertEqual(config["artifact_format_version"], 2)
        self.assertEqual(config["operation"], "fit")
        self.assertFalse(config["protocol_controls"]["complete"])
        self.assertEqual(config["roles"]["repeat_role"], "a")
        self.assertTrue(config["condition"]["condition_id"])
        gradients = fx.read_json(directory / "gradients.json")
        self.assertEqual(len(gradients["updates"]), 2 * protocol.UPDATES_PER_EPOCH)
        self.assertEqual(gradients["total_updates"], 2 * protocol.UPDATES_PER_EPOCH)
        self.assertGreater(gradients["clipped_updates"], 0)
        provenance = fx.read_json(directory / "provenance.json")
        self.assertEqual(provenance["data"]["source_sha256"], self.data.identity()["source_sha256"])
        self.assertEqual(provenance["environment"]["threads"], 1)
        self.assertEqual(provenance["protocol"]["version"], protocol.SCIENTIFIC_VERSION)
        self.assertIn("benchmark/multivariate_time_series/temporal/engine.py",
                      provenance["source"]["files"])


if __name__ == "__main__":
    unittest.main()
