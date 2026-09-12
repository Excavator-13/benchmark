"""Unit tests for :mod:`main` (tasks 3.1 through 3.5)."""

from __future__ import annotations

import contextlib
import io
import json
import os
import random
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from torch_geometric_temporal.signal import StaticGraphTemporalSignal  # noqa: E402

import main  # noqa: E402
from main import (  # noqa: E402
    CheckpointError,
    ExperimentConfig,
    SplitResult,
    SplitValidationError,
    build_model,
    load_checkpoint,
    run_split,
    save_checkpoint,
    set_seed,
    split_sizes,
    temporal_signal_split,
    train_experiment,
)

CUDA_AVAILABLE = torch.cuda.is_available()
CUDA_REASON = "CUDA is not available in this environment"

NUM_NODES = 32
WINDOW = 6
PRED = 3


def synthetic_signal(num_nodes=NUM_NODES, snapshot_count=8, window=WINDOW, pred=PRED, seed=0):
    """A tiny but structurally valid weighted temporal signal."""
    rng = np.random.default_rng(seed)
    features = [
        rng.normal(size=(num_nodes, window)).astype(np.float32) for _ in range(snapshot_count)
    ]
    targets = [rng.normal(size=(num_nodes, pred)).astype(np.float32) for _ in range(snapshot_count)]
    edge_index = np.asarray(
        [[node, (node + 1) % num_nodes] for node in range(num_nodes)], dtype=np.int64
    ).T
    edge_weight = np.ones(edge_index.shape[1], dtype=np.float32)
    return StaticGraphTemporalSignal(edge_index, edge_weight, features, targets)


def small_config(**overrides):
    values = dict(
        data_name="r0",
        mode="rate",
        model_name="EvolveGCNH",
        device="cpu",
        seed=0,
        window_size=WINDOW,
        hidden_dim=8,
        pred_length=PRED,
        num_epochs=2,
        train_ratio=0.5,
        eval_ratio=0.25,
    )
    values.update(overrides)
    return ExperimentConfig(**values)


class CountingSignal:
    """Wrap a signal and count how many times it is iterated."""

    def __init__(self, signal):
        self._signal = signal
        self.iterations = 0
        self.items = 0

    @property
    def snapshot_count(self):
        return self._signal.snapshot_count

    def __getitem__(self, index):
        return self._signal[index]

    def __iter__(self):
        self.iterations += 1
        for snapshot in self._signal:
            self.items += 1
            yield snapshot


@contextlib.contextmanager
def quiet_progress():
    class _Progress:
        def __init__(self, iterable, **kwargs):
            self._iterable = iterable

        def __iter__(self):
            return iter(self._iterable)

        def set_postfix(self, **kwargs):
            return None

    with mock.patch.object(main, "tqdm", _Progress):
        yield


class ModuleImportTests(unittest.TestCase):
    """Task 3.1: importing the module must not train anything."""

    def test_import_has_no_training_side_effects(self):
        before_module = sorted(os.listdir(MODULE_DIR))
        with tempfile.TemporaryDirectory() as tmp:
            environment = dict(os.environ, PYTHONPATH=str(MODULE_DIR))
            completed = subprocess.run(
                [sys.executable, "-c", "import main; print(main.MODEL_NAMES[0])"],
                cwd=tmp,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("A3TGCN", completed.stdout)
            self.assertEqual(sorted(os.listdir(tmp)), [])
        self.assertEqual(sorted(os.listdir(MODULE_DIR)), before_module)

    def test_module_exposes_main_guard_and_pieces(self):
        self.assertTrue(callable(main.main))
        self.assertTrue(callable(main.build_parser))
        self.assertTrue(callable(main.parse_config))
        self.assertTrue(callable(main.temporal_signal_split))
        self.assertTrue(callable(main.build_model))


class CliTests(unittest.TestCase):
    """Task 3.1 and task 4.1: the public interface is testable and truthful."""

    def test_documented_options_are_accepted(self):
        config = main.parse_config(
            [
                "--data_name",
                "r0",
                "--mode",
                "rate",
                "--model_name",
                "EvolveGCNH",
                "--device",
                "cpu",
                "--seed",
                "17",
                "--window_size",
                "6",
                "--hidden_dim",
                "32",
                "--pred_length",
                "3",
                "--num_epochs",
                "1",
            ]
        )
        self.assertEqual(config.data_name, "r0")
        self.assertEqual(config.mode, "rate")
        self.assertEqual(config.model_name, "EvolveGCNH")
        self.assertEqual(config.seed, 17)
        self.assertEqual(config.window_size, 6)
        self.assertEqual(config.pred_length, 3)
        self.assertEqual(config.num_epochs, 1)

    def test_defaults_match_the_documented_default_command(self):
        config = main.parse_config([])
        self.assertEqual(config.data_name, "r0")
        self.assertEqual(config.mode, "rate")
        self.assertEqual(config.model_name, "EvolveGCNH")
        self.assertEqual(config.device, "cpu")
        self.assertEqual(config.window_size, 6)
        self.assertEqual(config.pred_length, 3)

    def test_unknown_model_lists_accepted_values(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            main.parse_config(["--model_name", "Transformer"])
        self.assertEqual(caught.exception.code, 2)
        for name in main.MODEL_NAMES:
            self.assertIn(name, stderr.getvalue())

    def test_unknown_option_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main.parse_config(["--model", "EvolveGCNH"])
        self.assertEqual(caught.exception.code, 2)

    def test_help_names_model_name_and_hidden_dim_scope(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), self.assertRaises(SystemExit) as caught:
            main.build_parser().parse_args(["--help"])
        self.assertEqual(caught.exception.code, 0)
        text = stdout.getvalue()
        self.assertIn("--model_name", text)
        self.assertIsNone(
            __import__("re").search(r"(?<![\w-])--model(?![\w-])", text),
            "help must not advertise a bare --model option",
        )
        flattened = " ".join(text.split())
        self.assertIn("EvolveGCNH", flattened)
        self.assertIn("ignore it", flattened)

    def test_configuration_rejects_non_positive_lengths(self):
        for field in ("window_size", "pred_length", "hidden_dim", "num_epochs"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                small_config(**{field: 0})

    def test_architecture_matches_checkpoint_contract(self):
        config = small_config()
        self.assertEqual(
            sorted(config.architecture(NUM_NODES)),
            sorted(main.CHECKPOINT_CONFIG_KEYS),
        )


class DatasetAndModelTests(unittest.TestCase):
    """Task 3.1 and task 3.2: loader lengths and per-model construction."""

    def test_load_dataset_passes_window_and_prediction_lengths(self):
        captured = {}

        class FakeLoader:
            def __init__(self, data_name, mode, data_dir=None):
                captured["data_name"] = data_name
                captured["mode"] = mode

            def get_dataset(self, lags=None, pred_length=None):
                captured["lags"] = lags
                captured["pred_length"] = pred_length
                return "dataset"

        with mock.patch.object(main, "DatasetLoader", FakeLoader):
            result = main.load_dataset(small_config(window_size=7, pred_length=4))
        self.assertEqual(result, "dataset")
        self.assertEqual(captured["lags"], 7)
        self.assertEqual(captured["pred_length"], 4)
        self.assertEqual(captured["data_name"], "r0")

    def test_model_names_match_every_advertised_family(self):
        self.assertIn("EvolveGCNH", main.MODEL_NAMES)
        self.assertIn("EvolveGCNO", main.MODEL_NAMES)
        self.assertEqual(len(main.MODEL_NAMES), len(set(main.MODEL_NAMES)))

    def test_build_model_uses_configured_lengths(self):
        model = build_model(small_config(pred_length=5), NUM_NODES)
        self.assertEqual(model.linear.out_features, 5)
        self.assertEqual(model.recurrent.in_channels, WINDOW)
        self.assertEqual(model.pred_length, 5)

    def test_unknown_model_name_is_rejected(self):
        with self.assertRaises(ValueError):
            build_model(small_config(model_name="Nope"), NUM_NODES)

    def test_forecaster_shape_and_state_smoke_for_every_advertised_model(self):
        signal = synthetic_signal()
        unavailable = {}
        for model_name in main.MODEL_NAMES:
            config = small_config(model_name=model_name, num_epochs=1)
            try:
                model = build_model(config, NUM_NODES)
                result = run_split(
                    model, signal[0:2], torch.device("cpu"), collect_predictions=True
                )
            except Exception as exc:  # pragma: no cover - reported when a model regresses
                unavailable[model_name] = f"{type(exc).__name__}: {exc}"
                continue
            with self.subTest(model=model_name):
                self.assertEqual(len(result.predictions), 2)
                for prediction, gold in zip(result.predictions, result.golds):
                    self.assertEqual(tuple(prediction.shape), (NUM_NODES, PRED))
                    self.assertEqual(tuple(gold.shape), (NUM_NODES, PRED))
        self.assertEqual(
            unavailable,
            {},
            f"advertised models must run with the pinned libraries: {unavailable}",
        )

    def test_evolvegcnh_state_is_returned_and_not_on_the_module(self):
        model = build_model(small_config(), NUM_NODES)
        result = run_split(model, synthetic_signal()[0:2], torch.device("cpu"))
        self.assertTrue(torch.isfinite(torch.tensor(result.loss)))
        self.assertFalse(hasattr(model.recurrent, "weight"))


class SplitTests(unittest.TestCase):
    """Task 3.1: validated, chronological, three-way splitting."""

    def test_default_ratios_over_default_snapshots(self):
        self.assertEqual(split_sizes(28, 0.83, 0.04), (23, 1, 4))

    def test_sizes_are_chronological_and_non_empty(self):
        train, evaluation, test = split_sizes(100, 0.8, 0.1)
        self.assertEqual((train, evaluation, test), (80, 10, 10))

    def test_empty_partition_is_rejected(self):
        with self.assertRaises(SplitValidationError) as caught:
            split_sizes(10, 0.5, 0.05)
        self.assertIn("empty partitions", str(caught.exception))

    def test_ratios_that_leave_no_test_room_are_rejected(self):
        with self.assertRaises(SplitValidationError):
            split_sizes(10, 0.95, 0.05)

    def test_invalid_ratios_are_rejected(self):
        for train_ratio, eval_ratio in ((0.0, 0.1), (1.0, 0.1), (0.5, 0.0), (0.5, 1.0), (-0.1, 0.1), (0.6, 0.5)):
            with self.subTest(train_ratio=train_ratio, eval_ratio=eval_ratio):
                with self.assertRaises(SplitValidationError):
                    split_sizes(50, train_ratio, eval_ratio)

    def test_empty_dataset_is_rejected(self):
        with self.assertRaises(SplitValidationError):
            split_sizes(0, 0.8, 0.1)

    def test_split_slices_a_real_signal_chronologically(self):
        signal = synthetic_signal(snapshot_count=10)
        train, evaluation, test = temporal_signal_split(signal, 0.5, 0.3)
        self.assertEqual((train.snapshot_count, evaluation.snapshot_count, test.snapshot_count), (5, 3, 2))
        np.testing.assert_allclose(train.features[-1], signal.features[4])
        np.testing.assert_allclose(evaluation.features[0], signal.features[5])
        np.testing.assert_allclose(test.features[0], signal.features[8])

    def test_split_reports_empty_partition_before_training(self):
        signal = synthetic_signal(snapshot_count=8)
        with self.assertRaises(SplitValidationError):
            temporal_signal_split(signal, 0.9, 0.1)

    def test_split_docstring_describes_three_partitions(self):
        docstring = temporal_signal_split.__doc__ or ""
        self.assertIn("train_iterator", docstring)
        self.assertIn("eval_iterator", docstring)
        self.assertIn("test_iterator", docstring)
        self.assertIn("non-empty", docstring)


class DeviceAndRunnerTests(unittest.TestCase):
    """Task 3.2: one shared, device-consistent split runner."""

    def test_move_snapshot_moves_every_tensor(self):
        snapshot = synthetic_signal()[0]
        moved = main.move_snapshot(snapshot, torch.device("cpu"))
        self.assertIs(moved, snapshot)
        for name in ("x", "edge_index", "edge_attr", "y"):
            self.assertEqual(getattr(moved, name).device.type, "cpu")

    def test_runner_requests_configured_device_for_every_snapshot_tensor(self):
        signal = synthetic_signal(snapshot_count=3)
        model = build_model(small_config(), NUM_NODES)
        recorded = []

        def recording(tensor, device):
            recorded.append((str(device), tuple(tensor.shape)))
            return tensor.to(torch.device("cpu"))

        requested = torch.device("cuda:0")
        with mock.patch.object(main, "_to_device", side_effect=recording):
            result = run_split(model, signal, requested, collect_predictions=True)

        self.assertEqual(len(recorded), 4 * signal.snapshot_count)
        self.assertEqual({device for device, _ in recorded}, {"cuda:0"})
        self.assertEqual(len(result.predictions), signal.snapshot_count)
        for prediction in result.predictions:
            self.assertEqual(prediction.device.type, "cpu")

    @unittest.skipUnless(CUDA_AVAILABLE, CUDA_REASON)
    def test_runner_executes_on_cuda_when_available(self):
        device = torch.device("cuda")
        model = build_model(small_config(), NUM_NODES).to(device)
        result = run_split(
            model, synthetic_signal(snapshot_count=3), device, collect_predictions=True
        )
        self.assertTrue(torch.isfinite(torch.tensor(result.loss)))
        for prediction in result.predictions:
            self.assertEqual(prediction.device.type, "cpu")  # collected on CPU by design

    def test_runner_performs_one_optimizer_step_per_traversal(self):
        model = build_model(small_config(), NUM_NODES)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
        with mock.patch.object(optimizer, "step", wraps=optimizer.step) as step, mock.patch.object(
            optimizer, "zero_grad", wraps=optimizer.zero_grad
        ) as zero_grad:
            result = run_split(
                model, synthetic_signal(snapshot_count=4), torch.device("cpu"), training=True, optimizer=optimizer
            )
        self.assertEqual(result.optimizer_steps, 1)
        self.assertEqual(step.call_count, 1)
        self.assertEqual(zero_grad.call_count, 1)

    def test_runner_does_not_step_without_an_optimizer(self):
        model = build_model(small_config(), NUM_NODES)
        result = run_split(model, synthetic_signal(snapshot_count=2), torch.device("cpu"), training=True)
        self.assertEqual(result.optimizer_steps, 0)

    def test_empty_partition_is_reported_by_the_runner(self):
        model = build_model(small_config(), NUM_NODES)
        with self.assertRaises(SplitValidationError):
            run_split(model, [], torch.device("cpu"))

    @contextlib.contextmanager
    def _stub_gru(self, model):
        """Make each GRU call deterministically advance the weight by one."""
        layer = model.recurrent
        received = []

        def fake_forward(inputs, hidden):
            received.append(hidden.detach().clone())
            return inputs, hidden + 1.0

        original = layer.recurrent_layer.forward
        layer.recurrent_layer.forward = fake_forward
        try:
            yield received
        finally:
            layer.recurrent_layer.forward = original

    def test_state_carries_between_snapshots_within_one_traversal(self):
        model = build_model(small_config(), NUM_NODES)
        signal = synthetic_signal(snapshot_count=3)
        with self._stub_gru(model) as received:
            run_split(model, signal, torch.device("cpu"))
        self.assertEqual(len(received), 3)
        torch.testing.assert_close(received[0].squeeze(0), model.recurrent.initial_weight.detach())
        torch.testing.assert_close(received[1], received[0] + 1.0)
        torch.testing.assert_close(received[2], received[1] + 1.0)

    def test_state_resets_between_traversals(self):
        model = build_model(small_config(), NUM_NODES)
        signal = synthetic_signal(snapshot_count=2)
        with self._stub_gru(model) as received:
            run_split(model, signal, torch.device("cpu"))
            run_split(model, signal, torch.device("cpu"))
        self.assertEqual(len(received), 4)
        torch.testing.assert_close(received[0].squeeze(0), model.recurrent.initial_weight.detach())
        self.assertFalse(torch.allclose(received[1], received[0]))
        # The second traversal starts over from the learnable initial weight.
        torch.testing.assert_close(received[2].squeeze(0), model.recurrent.initial_weight.detach())

    def test_third_party_evolvegcno_state_is_reset_between_traversals(self):
        model = build_model(small_config(model_name="EvolveGCNO"), NUM_NODES)
        run_split(model, synthetic_signal(snapshot_count=1), torch.device("cpu"))
        self.assertIsNotNone(model.recurrent.weight)
        model.initial_state()
        self.assertIsNone(model.recurrent.weight)

    def test_reset_never_clobbers_a_learnable_weight_parameter(self):
        model = build_model(small_config(model_name="TGCN"), NUM_NODES)
        parameter = torch.nn.Parameter(torch.ones(2, 2))
        model.recurrent.weight = parameter
        model.initial_state()
        self.assertIs(model.recurrent.weight, parameter)

    def test_untrained_model_initial_state_is_empty(self):
        model = build_model(small_config(), NUM_NODES)
        self.assertEqual(model.initial_state(), {"h": None, "c": None, "weight": None})


class SelectionTests(unittest.TestCase):
    """Task 3.3: train on train, select on validation, test exactly once."""

    def _splits(self):
        signal = synthetic_signal(snapshot_count=12)
        train, evaluation, test = temporal_signal_split(signal, 0.5, 0.25)
        return CountingSignal(train), CountingSignal(evaluation), CountingSignal(test)

    def test_epoch_loop_touches_each_split_the_expected_number_of_times(self):
        train, evaluation, test = self._splits()
        calls = []
        original = main.run_split

        def recording(model, iterator, device, **kwargs):
            calls.append((iterator, bool(kwargs.get("training"))))
            return original(model, iterator, device, **kwargs)

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(main, "run_split", recording), quiet_progress():
            train_experiment(small_config(num_epochs=3), train, evaluation, test, results_dir=Path(tmp))

        self.assertEqual(train.iterations, 3)
        self.assertEqual(evaluation.iterations, 3)
        self.assertEqual(test.iterations, 1)
        self.assertEqual([training for _, training in calls].count(True), 3)
        test_calls = [index for index, (iterator, _) in enumerate(calls) if iterator is test]
        self.assertEqual(test_calls, [len(calls) - 1], "test must be traversed once, last")

    def test_no_test_access_before_final_evaluation(self):
        train, evaluation, test = self._splits()
        with tempfile.TemporaryDirectory() as tmp, quiet_progress():
            with mock.patch.object(main, "run_split", wraps=main.run_split) as spy:
                train_experiment(
                    small_config(num_epochs=3), train, evaluation, test, results_dir=Path(tmp)
                )
            test_snapshots = [
                call
                for call in spy.call_args_list
                if call.args[1] is test
            ]
        self.assertEqual(len(test_snapshots), 1)

    def test_checkpoint_is_written_only_when_validation_improves(self):
        signal = synthetic_signal(snapshot_count=12)
        train, evaluation, test = temporal_signal_split(signal, 0.5, 0.25)
        scripted = [0.9, 0.5, 0.7, 0.3]
        seen = {"validation": 0}
        recorded = []
        real_save = main.save_checkpoint

        def fake_save(*args, **kwargs):
            recorded.append(kwargs["best_val_loss"])
            return real_save(*args, **kwargs)

        real_run_split = main.run_split

        def fake_run_split(model, iterator, device, **kwargs):
            if kwargs.get("training"):
                return SplitResult(loss=1.0, optimizer_steps=1)
            if iterator is evaluation:
                loss = scripted[seen["validation"]]
                seen["validation"] += 1
                return SplitResult(loss=loss)
            # The final evaluation uses the real shared runner.
            return real_run_split(model, iterator, device, **kwargs)

        with tempfile.TemporaryDirectory() as tmp, quiet_progress():
            with mock.patch.object(main, "run_split", fake_run_split), mock.patch.object(
                main, "save_checkpoint", fake_save
            ):
                train_experiment(
                    small_config(num_epochs=len(scripted)),
                    train,
                    evaluation,
                    test,
                    results_dir=Path(tmp),
                )
            checkpoint = load_checkpoint(
                Path(tmp) / "rate" / "r0" / "EvolveGCNH" / "0" / main.CHECKPOINT_FILENAME,
                torch.device("cpu"),
            )
        self.assertEqual(recorded, [0.9, 0.5, 0.3])
        self.assertAlmostEqual(checkpoint.best_val_loss, 0.3)

    def test_final_metrics_come_from_the_test_traversal(self):
        train, evaluation, test = self._splits()
        with tempfile.TemporaryDirectory() as tmp, quiet_progress():
            metrics = train_experiment(
                small_config(num_epochs=2), train, evaluation, test, results_dir=Path(tmp)
            )
            directory = Path(tmp) / "rate" / "r0" / "EvolveGCNH" / "0"
            predictions = sorted(directory.glob("pred_*.pt"))
            golds = sorted(directory.glob("gold_*.pt"))
            stored = json.loads((directory / main.METRICS_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual(len(predictions), test.snapshot_count)
        self.assertEqual(len(golds), test.snapshot_count)
        self.assertEqual(stored, metrics)
        self.assertTrue(np.isfinite(metrics["RMSE"]))
        self.assertTrue(np.isfinite(metrics["MAE"]))
        self.assertGreaterEqual(metrics["RMSE"], 0.0)
        self.assertGreaterEqual(metrics["MAE"], 0.0)

    def test_checkpoint_file_is_written_and_legacy_name_is_unused(self):
        train, evaluation, test = self._splits()
        with tempfile.TemporaryDirectory() as tmp, quiet_progress():
            train_experiment(
                small_config(num_epochs=1), train, evaluation, test, results_dir=Path(tmp)
            )
            directory = Path(tmp) / "rate" / "r0" / "EvolveGCNH" / "0"
            self.assertTrue((directory / main.CHECKPOINT_FILENAME).is_file())
            self.assertFalse((directory / main.LEGACY_CHECKPOINT_FILENAME).exists())


class ResultDirectoryTests(unittest.TestCase):
    """Task 3.3: a rerun in the same seed directory must not keep stale predictions."""

    @staticmethod
    def _splits(snapshot_count=12):
        signal = synthetic_signal(snapshot_count=snapshot_count)
        return temporal_signal_split(signal, 0.5, 0.25)

    def test_rerun_removes_predictions_left_by_a_longer_previous_run(self):
        train, evaluation, test = self._splits()
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp)
            directory = main.result_dir(small_config(), results_dir=results)
            directory.mkdir(parents=True)
            for index in range(test.snapshot_count + 2):
                for kind in ("pred", "gold"):
                    torch.save(torch.zeros(NUM_NODES, PRED), directory / f"{kind}_{index}.pt")
            # Files the cleanup must never touch.
            (directory / "notes.txt").write_text("keep me", encoding="utf-8")
            (directory / "pred_extra.pt").write_text("keep me", encoding="utf-8")

            with quiet_progress():
                train_experiment(
                    small_config(num_epochs=1), train, evaluation, test, results_dir=results
                )

            present = {path.name for path in directory.iterdir()}
            stored_metrics = json.loads(
                (directory / main.METRICS_FILENAME).read_text(encoding="utf-8")
            )

        self.assertGreater(test.snapshot_count, 0)
        for index in range(test.snapshot_count):
            self.assertIn(f"pred_{index}.pt", present)
            self.assertIn(f"gold_{index}.pt", present)
        for index in range(test.snapshot_count, test.snapshot_count + 2):
            self.assertNotIn(f"pred_{index}.pt", present)
            self.assertNotIn(f"gold_{index}.pt", present)
        self.assertIn("notes.txt", present)
        self.assertIn("pred_extra.pt", present)
        stored_predictions = sorted(
            name for name in present if re.match(r"^pred_\d+\.pt$", name)
        )
        self.assertEqual(len(stored_predictions), test.snapshot_count)
        self.assertTrue(np.isfinite(stored_metrics["RMSE"]))

    def test_clear_prediction_artifacts_matches_only_strict_names(self):
        keep = ["pred_0.pt.bak", "pred_x.pt", "gold_.pt", "prediction_0.pt", "metrics.json"]
        remove = ["pred_0.pt", "pred_12.pt", "gold_3.pt"]
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in keep + remove:
                (directory / name).write_text("x", encoding="utf-8")
            removed = main.clear_prediction_artifacts(directory)
            remaining = {path.name for path in directory.iterdir()}
        self.assertEqual(sorted(path.name for path in removed), sorted(remove))
        for name in keep:
            self.assertIn(name, remaining)

    def test_clear_prediction_artifacts_tolerates_a_missing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main.clear_prediction_artifacts(Path(tmp) / "absent"), [])


class SeedTests(unittest.TestCase):
    """Task 3.4: one seeded run, reproducible on CPU."""

    def test_set_seed_covers_python_numpy_and_torch(self):
        set_seed(1234)
        first = (random.random(), float(np.random.rand()), torch.rand(3))
        set_seed(1234)
        second = (random.random(), float(np.random.rand()), torch.rand(3))
        self.assertEqual(first[0], second[0])
        self.assertEqual(first[1], second[1])
        torch.testing.assert_close(first[2], second[2])

    def test_seed_reproduces_initial_parameters(self):
        set_seed(7)
        first = build_model(small_config(), NUM_NODES)
        set_seed(7)
        second = build_model(small_config(), NUM_NODES)
        for (name, left), (_, right) in zip(first.state_dict().items(), second.state_dict().items()):
            torch.testing.assert_close(left, right, msg=name)

    def test_requested_seed_runs_exactly_one_result_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp) / "results"
            with mock.patch.object(main, "DEFAULT_RESULTS_DIR", results), mock.patch.object(
                main, "load_dataset", lambda config: synthetic_signal(snapshot_count=28)
            ), quiet_progress(), contextlib.redirect_stdout(io.StringIO()):
                code = main.main(["--seed", "17", "--num_epochs", "1"])
            self.assertEqual(code, 0)
            seed_root = results / "rate" / "r0" / "EvolveGCNH"
            self.assertEqual([path.name for path in seed_root.iterdir()], ["17"])
            self.assertTrue((seed_root / "17" / "metrics.json").is_file())

    def test_two_cpu_runs_with_the_same_seed_match(self):
        signal = synthetic_signal(snapshot_count=12)
        train, evaluation, test = temporal_signal_split(signal, 0.5, 0.25)
        config = small_config(num_epochs=3, seed=5)
        with tempfile.TemporaryDirectory() as first_tmp, tempfile.TemporaryDirectory() as second_tmp:
            with quiet_progress():
                first = train_experiment(
                    config, train, evaluation, test, results_dir=Path(first_tmp)
                )
                second = train_experiment(
                    config, train, evaluation, test, results_dir=Path(second_tmp)
                )
        self.assertAlmostEqual(first["RMSE"], second["RMSE"], delta=main.DETERMINISM_TOLERANCE)
        self.assertAlmostEqual(first["MAE"], second["MAE"], delta=main.DETERMINISM_TOLERANCE)

    def test_configure_determinism_enables_backend_switches(self):
        notes = main.configure_determinism(torch.device("cpu"))
        self.assertIsInstance(notes, list)
        self.assertTrue(torch.backends.cudnn.deterministic)

    def test_declared_tolerance_is_positive_and_small(self):
        self.assertGreater(main.DETERMINISM_TOLERANCE, 0.0)
        self.assertLessEqual(main.DETERMINISM_TOLERANCE, 1e-3)


class CheckpointTests(unittest.TestCase):
    """Task 3.5: versioned, reconstructable, device-portable checkpoints."""

    def _save(self, directory, config=None, model_name="EvolveGCNH", loss=0.25, seed=3):
        config = config or small_config(model_name=model_name, seed=seed)
        model = build_model(config, NUM_NODES)
        path = Path(directory) / main.CHECKPOINT_FILENAME
        save_checkpoint(
            path, model, config, num_nodes=NUM_NODES, node_features=1, best_val_loss=loss
        )
        return path, model

    def test_payload_is_a_state_dictionary_with_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, model = self._save(tmp)
            payload = torch.load(path, map_location="cpu", weights_only=True)
        self.assertEqual(payload["format_version"], main.CHECKPOINT_FORMAT_VERSION)
        self.assertIsInstance(payload["model_state_dict"], dict)
        self.assertNotIsInstance(payload["model_state_dict"], torch.nn.Module)
        self.assertEqual(payload["seed"], 3)
        self.assertAlmostEqual(payload["best_val_loss"], 0.25)
        self.assertEqual(sorted(payload["config"]), sorted(main.CHECKPOINT_CONFIG_KEYS))
        self.assertTrue(
            any(key.endswith("initial_weight") for key in payload["model_state_dict"]),
            "the learnable initial weight must be checkpointed",
        )

    def test_round_trip_reproduces_predictions(self):
        signal = synthetic_signal(snapshot_count=3)
        with tempfile.TemporaryDirectory() as tmp:
            path, model = self._save(tmp)
            before = run_split(model, signal, torch.device("cpu"), collect_predictions=True)
            restored = load_checkpoint(path, torch.device("cpu"))
            after = run_split(
                restored.model, signal, torch.device("cpu"), collect_predictions=True
            )
        self.assertEqual(restored.seed, 3)
        self.assertAlmostEqual(restored.best_val_loss, 0.25)
        for left, right in zip(before.predictions, after.predictions):
            torch.testing.assert_close(left, right)

    def test_loading_passes_an_explicit_map_location(self):
        device = torch.device("cpu")
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self._save(tmp)
            real_load = torch.load

            def spy(*args, **kwargs):
                self.assertEqual(kwargs.get("map_location"), device)
                return real_load(*args, **kwargs)

            with mock.patch.object(torch, "load", spy):
                load_checkpoint(path, device)

    def test_restored_parameters_live_on_the_requested_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self._save(tmp)
            restored = load_checkpoint(path, torch.device("cpu"))
        for parameter in restored.model.parameters():
            self.assertEqual(parameter.device.type, "cpu")

    @unittest.skipUnless(CUDA_AVAILABLE, CUDA_REASON)
    def test_checkpoint_maps_from_cpu_to_cuda(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self._save(tmp)
            restored = load_checkpoint(path, torch.device("cuda"))
        for parameter in restored.model.parameters():
            self.assertEqual(parameter.device.type, "cuda")

    def test_incompatible_configuration_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self._save(tmp)
            incompatible = dict(small_config().architecture(NUM_NODES))
            incompatible["window_size"] = WINDOW + 1
            with self.assertRaises(CheckpointError) as caught:
                load_checkpoint(path, torch.device("cpu"), expected_config=incompatible)
        self.assertIn("window_size", str(caught.exception))

    def test_matching_configuration_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self._save(tmp)
            restored = load_checkpoint(
                path,
                torch.device("cpu"),
                expected_config=small_config().architecture(NUM_NODES),
            )
        self.assertEqual(restored.config["model_name"], "EvolveGCNH")

    def test_legacy_model_pt_produces_an_actionable_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / main.LEGACY_CHECKPOINT_FILENAME).write_bytes(b"legacy")
            with self.assertRaises(CheckpointError) as caught:
                load_checkpoint(directory / main.CHECKPOINT_FILENAME, torch.device("cpu"))
        message = str(caught.exception)
        self.assertIn("model.pt", message)
        self.assertIn("Rerun", message)

    def test_missing_checkpoint_without_legacy_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CheckpointError) as caught:
                load_checkpoint(Path(tmp) / main.CHECKPOINT_FILENAME, torch.device("cpu"))
        self.assertIn("does not exist", str(caught.exception))

    def test_unknown_format_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / main.CHECKPOINT_FILENAME
            torch.save(
                {
                    "format_version": 99,
                    "model_state_dict": {},
                    "config": {},
                    "seed": 0,
                    "best_val_loss": 0.0,
                },
                path,
            )
            with self.assertRaises(CheckpointError) as caught:
                load_checkpoint(path, torch.device("cpu"))
        self.assertIn("format_version", str(caught.exception))

    def test_non_mapping_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / main.CHECKPOINT_FILENAME
            torch.save([1, 2, 3], path)
            with self.assertRaises(CheckpointError):
                load_checkpoint(path, torch.device("cpu"))

    def test_missing_metadata_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self._save(tmp)
            payload = torch.load(path, map_location="cpu", weights_only=True)
            del payload["seed"]
            torch.save(payload, path)
            with self.assertRaises(CheckpointError) as caught:
                load_checkpoint(path, torch.device("cpu"))
        self.assertIn("seed", str(caught.exception))

    def test_missing_configuration_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self._save(tmp)
            payload = torch.load(path, map_location="cpu", weights_only=True)
            del payload["config"]["window_size"]
            torch.save(payload, path)
            with self.assertRaises(CheckpointError) as caught:
                load_checkpoint(path, torch.device("cpu"))
        self.assertIn("configuration fields", str(caught.exception))

    def test_incompatible_state_dict_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self._save(tmp, config=small_config(model_name="EvolveGCNH"))
            payload = torch.load(path, map_location="cpu", weights_only=True)
            payload["config"]["window_size"] = payload["config"]["window_size"] + 1
            torch.save(payload, path)
            with self.assertRaises(RuntimeError):
                load_checkpoint(path, torch.device("cpu"))


class DocumentationContractTests(unittest.TestCase):
    """Task 4.1: the documented graph workflow matches the implementation."""

    def setUp(self):
        self.repository_root = MODULE_DIR.parents[1]
        self.readme = (self.repository_root / "README.md").read_text(encoding="utf-8")
        start = self.readme.index("### 4.4")
        end = self.readme.index("\n## ", start)
        self.graph_section = self.readme[start:end]

    def _bash_blocks(self):
        """Every ``bash`` fenced block in the graph section, as command lists."""
        blocks = re.findall(r"```bash\n(.*?)```", self.graph_section, flags=re.S)
        return [
            [line.strip() for line in block.splitlines() if line.strip()] for block in blocks
        ]

    def _documented_commands(self):
        return [line for block in self._bash_blocks() for line in block]

    def test_readme_documents_the_real_options_and_environment(self):
        self.assertIn("--model_name", self.graph_section)
        self.assertIsNone(
            re.search(r"(?<![\w-])--model(?![\w-])", self.graph_section),
            "the graph section must not document a bare --model option",
        )
        self.assertIn("prepare_graph_data.py", self.graph_section)
        self.assertIn("conda create -n Job-SDF python=3.8", self.readme)
        self.assertIn("checkpoint.pt", self.graph_section)

    def test_readme_states_hidden_dim_scope(self):
        self.assertIn("ignore", self.readme)
        self.assertIn("--window_size", self.readme)

    def test_readme_does_not_claim_a_frequency_column(self):
        self.assertNotIn("frequency of co-occurrence", self.readme)
        for token in ("row_id", "col_id", "context"):
            self.assertIn(token, self.readme)

    def test_graph_section_never_changes_the_working_directory(self):
        for line in self._documented_commands():
            with self.subTest(command=line):
                self.assertFalse(
                    line.startswith("cd "),
                    "the graph section must declare one working directory and keep it",
                )
        self.assertIn("repository root", self.graph_section)

    def test_every_documented_script_resolves_from_the_repository_root(self):
        scripts = set()
        for line in self._documented_commands():
            match = re.match(r"python\s+(\S+)", line)
            if match:
                scripts.add(match.group(1))
        self.assertIn("benchmark/graph_method/main.py", scripts)
        self.assertIn("benchmark/graph_method/prepare_graph_data.py", scripts)
        for script in scripts:
            with self.subTest(script=script):
                self.assertTrue(
                    (self.repository_root / script).is_file(),
                    f"{script} must exist relative to the repository root",
                )

    def test_documented_preparation_commands_run_verbatim_in_order(self):
        """Run the README lines as written (relative script path, declared cwd)."""
        commands = [
            line
            for line in self._documented_commands()
            if line.startswith("python benchmark/graph_method/prepare_graph_data.py")
        ]
        self.assertTrue(commands, "the graph section must document the preparation CLI")
        self.assertTrue(commands[0].endswith("--help"))
        for line in commands:
            with self.subTest(command=line):
                # Only the interpreter is substituted; the documented script path
                # and arguments are executed exactly as written, from the root.
                completed = subprocess.run(
                    [sys.executable, *shlex.split(line)[1:]],
                    cwd=str(self.repository_root),
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_documented_training_command_resolves_and_parses(self):
        documented = [
            line
            for line in self._documented_commands()
            if line.startswith("python benchmark/graph_method/main.py --data_name r0")
        ]
        self.assertTrue(documented, "the graph section must document the default training command")
        for line in documented:
            parts = shlex.split(line)
            # parts[0] is the interpreter; parts[1] the documented script path.
            script_args = parts[1:]
            argv = parts[2:]
            with self.subTest(command=line):
                completed = subprocess.run(
                    [sys.executable, *script_args, "--help"],
                    cwd=str(self.repository_root),
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                config = main.parse_config(argv)
                self.assertEqual(config.data_name, "r0")
                self.assertEqual(config.mode, "rate")
                self.assertEqual(config.model_name, "EvolveGCNH")


class DeviceResolutionTests(unittest.TestCase):
    """Task 3.2: unusable devices fail before any training."""

    def test_cpu_resolves(self):
        self.assertEqual(main.resolve_device("cpu").type, "cpu")

    def test_unknown_backend_is_rejected(self):
        with self.assertRaises(RuntimeError):
            main.resolve_device("tpu")

    def test_garbage_device_is_rejected(self):
        with self.assertRaises(RuntimeError):
            main.resolve_device("not-a-device")

    @unittest.skipIf(CUDA_AVAILABLE, "CUDA is available here, so the failure path is untestable")
    def test_unavailable_cuda_is_rejected(self):
        with self.assertRaises(RuntimeError) as caught:
            main.resolve_device("cuda")
        self.assertIn("cuda", str(caught.exception).lower())

    @unittest.skipIf(CUDA_AVAILABLE, "CUDA is available here, so the failure path is untestable")
    def test_main_fails_before_loading_data_on_an_unavailable_device(self):
        stderr = io.StringIO()
        with mock.patch.object(
            main, "load_dataset", side_effect=AssertionError("must not load data")
        ), contextlib.redirect_stderr(stderr):
            code = main.main(["--device", "cuda"])
        self.assertEqual(code, 1)
        self.assertIn("cuda", stderr.getvalue().lower())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
