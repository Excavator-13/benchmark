"""Preflight, locking, watchdog, ledger, atomic checkpoints and recovery."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import torch

import temporal_fixtures as fx
from benchmark.multivariate_time_series.temporal import checkpoints, protocol
from benchmark.multivariate_time_series.temporal import engine as temporal_engine
from benchmark.multivariate_time_series.temporal import recovery, resources


def _history(epochs: int = 10, wall: float = 1.0) -> list:
    return [
        {
            "epoch": index + 1,
            "updates": (index + 1) * protocol.UPDATES_PER_EPOCH,
            "validation_MSE": 10.0 - 0.1 * index,
            "validation_MAE": 3.0,
            "online_train_loss_mixed_parameters": 2.0,
            "clipped_updates": 1,
            "pre_clip_norm_max": 1.5,
            "wall_seconds": wall,
        }
        for index in range(epochs)
    ]


class PreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.threads = {
            name: "1"
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS",
            )
        }

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _preflight(self, **overrides):
        payload = {
            "purpose": "development",
            "data_name": "r0",
            "run_id": "preflight-run",
            "output_root": self.root,
            "thread_environment": self.threads,
            "memory_available_bytes": 16 * protocol.GIB,
            "disk_free_bytes": 100 * protocol.GIB,
            "psutil_available": True,
        }
        payload.update(overrides)
        return resources.preflight(**payload)

    def test_preflight_passes_without_real_data(self):
        record = self._preflight()
        self.assertEqual(record["status"], "pass", record["failing_checks"])
        self.assertEqual(record["checks"]["data"]["status"], "not_supplied")
        self.assertEqual(record["checks"]["protocol"]["status"], "pass")
        self.assertEqual(record["checks"]["worker_lock"]["status"], "not_applicable")
        self.assertEqual(record["checks"]["resources"]["status"], "pass")
        self.assertFalse((self.root / "preflight-run").exists())

    def test_missing_dependency_fails(self):
        record = self._preflight(dependencies_missing=["psutil"])
        self.assertEqual(record["status"], "fail")
        self.assertIn("dependencies", record["failing_checks"])
        self.assertEqual(record["checks"]["dependencies"]["missing"], ["psutil"])

    def test_insufficient_resources_fail(self):
        record = self._preflight(memory_available_bytes=protocol.GIB)
        self.assertEqual(record["status"], "fail")
        self.assertEqual(
            record["checks"]["resources"]["checks"]["available_memory"]["status"],
            "fail",
        )
        record = self._preflight(disk_free_bytes=protocol.GIB)
        self.assertEqual(record["status"], "fail")
        self.assertEqual(
            record["checks"]["resources"]["checks"]["free_disk"]["status"], "fail"
        )
        record = self._preflight(psutil_available=False)
        self.assertEqual(record["status"], "fail")
        self.assertIn("resources", record["failing_checks"])

    def test_thread_environment_must_be_single_thread(self):
        broken = dict(self.threads)
        broken["OMP_NUM_THREADS"] = None
        record = self._preflight(thread_environment=broken)
        self.assertEqual(record["status"], "fail")
        self.assertIn("threads", record["failing_checks"])

    def test_formal_preflight_requires_a_data_source(self):
        record = self._preflight(purpose="formal")
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["checks"]["data"]["status"], "fail")

    def test_worker_lock_conflict_and_stale_takeover(self):
        lock_path = self.root / "locks" / "batch.lock"
        owner = resources.WorkerLock(lock_path, {"run_id": "held"})
        self.assertEqual(owner.acquire()["status"], "acquired")
        record = self._preflight(lock_path=lock_path)
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["checks"]["worker_lock"]["status"], "fail")
        owner.release()
        lock_path.write_text(
            json.dumps({"pid": 999_999, "created": "2026-01-01T00:00:00+08:00"}),
            encoding="utf-8",
        )
        record = self._preflight(lock_path=lock_path)
        self.assertEqual(record["status"], "pass")
        blocked = resources.WorkerLock(lock_path, {"run_id": "new"})
        self.assertEqual(blocked.acquire()["status"], "conflict")
        self.assertIn("stale", json.dumps(blocked.state))
        takeover = resources.WorkerLock(lock_path, {"run_id": "new"})
        self.assertEqual(takeover.acquire(takeover_stale=True)["status"], "acquired")
        takeover.release()
        self.assertFalse(lock_path.exists())

    def test_existing_output_identity_fails(self):
        (self.root / "preflight-run").mkdir()
        record = self._preflight()
        self.assertEqual(record["status"], "fail")
        self.assertIn("output", record["failing_checks"])

    def test_corrupt_recovery_fails_preflight(self):
        recovery_path = self.root / "recovery" / "last.pt"
        recovery_path.parent.mkdir(parents=True)
        recovery_path.write_bytes(b"not a checkpoint")
        record = self._preflight(recovery_path=recovery_path)
        self.assertEqual(record["status"], "fail")
        self.assertIn("recovery", record["failing_checks"])


class LedgerAndWatchdogTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_ledger_counts_measured_and_failed_but_not_estimates(self):
        path = self.root / "ledger.json"
        ledger = resources.Ledger(path, batch_id="batch")
        ledger.record(execution_id="one", run_id="r1", seconds=10.0)
        ledger.record(
            execution_id="two", run_id="r2", seconds=5.0, status="failed"
        )
        ledger.record(
            execution_id="three", run_id="r3", seconds=100.0, kind="estimated"
        )
        ledger.record(
            execution_id="four", run_id="r4", seconds=2.0, kind="replayed"
        )
        self.assertAlmostEqual(ledger.active_seconds(), 17.0)
        self.assertAlmostEqual(ledger.estimated_seconds(), 100.0)
        self.assertAlmostEqual(
            ledger.remaining_seconds(), protocol.BATCH_SECONDS - 17.0
        )
        reloaded = resources.Ledger(path, batch_id="batch")
        self.assertAlmostEqual(reloaded.active_seconds(), 17.0)
        with self.assertRaises(resources.ResourceError):
            resources.Ledger(path, batch_id="other")

    def test_cost_gate_limits(self):
        history = _history(10, wall=1.0)
        passed = resources.cost_gate(history, epochs=100, setup_seconds=0.0)
        self.assertEqual(passed["status"], "ok", passed)
        self.assertAlmostEqual(passed["steady_state_median_seconds"], 1.0)
        self.assertAlmostEqual(passed["estimate_seconds"], 1.3 * 200.0)
        slow_sample = resources.cost_gate(
            history, sample_seconds=protocol.COST_SAMPLE_SECONDS + 1
        )
        self.assertEqual(slow_sample["status"], "fail")
        over_fit = resources.cost_gate(
            history, spent_seconds=protocol.FIT_SECONDS
        )
        self.assertEqual(over_fit["status"], "fail")
        over_batch = resources.cost_gate(
            history,
            remaining_fits=50,
            batch_active_seconds=protocol.BATCH_SECONDS - 1000,
        )
        self.assertEqual(over_batch["status"], "fail")
        incomplete = resources.cost_gate(_history(5, wall=1.0))
        self.assertEqual(incomplete["status"], "incomplete")
        self.assertTrue(incomplete["unknown"])
        self.assertIn("paused", " ".join(incomplete["reasons"]))

    def test_watchdog_breach_and_monitor_failure(self):
        watchdog = resources.Watchdog(
            sampler=lambda: {"status": "ok", "rss_bytes": protocol.MEMORY_STOP_BYTES + 1},
            interval=0.01,
        )
        result = watchdog.sample_once()
        self.assertEqual(result["status"], "breach")
        self.assertIsNotNone(watchdog.pause_reason())
        self.assertIn("8 GiB", watchdog.pause_reason()["reason"])
        broken = resources.Watchdog(
            sampler=lambda: (_ for _ in ()).throw(OSError("psutil unavailable")),
            interval=0.01,
        )
        self.assertEqual(broken.sample_once()["status"], "monitor_failure")
        self.assertIn("monitoring failed", broken.pause_reason()["reason"])
        with self.assertRaises(resources.ResourceError):
            resources.Watchdog(sampler=lambda: {}, interval=30.0)


class FitResourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.data = fx.in_memory("r0", 3, seed=2)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_initial_rss_breach_stops_before_any_update(self):
        result = fx.fit_run(
            self.root / "runs",
            run_id="rss",
            data=self.data,
            epochs=3,
            monitor_interval=0.01,
            sampler=lambda: {"status": "ok", "rss_bytes": protocol.MEMORY_STOP_BYTES + 1},
        )
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["completed_epoch"], 0)
        directory = Path(result["run_dir"])
        self.assertFalse((directory / "recovery" / "last.pt").exists())
        self.assertEqual(fx.read_json(directory / "gradients.json")["total_updates"], 0)
        status = fx.read_json(directory / "status.json")
        self.assertEqual(status["state"], "paused")
        self.assertEqual(status["detail"]["reason"], "resource_stop")
        monitor = fx.read_json(directory / "monitor.json")
        self.assertIsNotNone(monitor["breach"])

    def test_monitor_failure_pauses_instead_of_crashing(self):
        def broken():
            raise OSError("sampling failed")

        result = fx.fit_run(
            self.root / "runs",
            run_id="monitor",
            data=self.data,
            epochs=2,
            monitor_interval=0.01,
            sampler=broken,
        )
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["completed_epoch"], 0)
        self.assertEqual(
            fx.read_json(Path(result["run_dir"]) / "monitor.json")["monitor_failure"][
                "reason"
            ],
            "process monitoring failed",
        )

    def test_cost_gate_pauses_before_continuing(self):
        result = fx.fit_run(
            self.root / "runs",
            run_id="cost-pause",
            data=self.data,
            epochs=12,
            setup_seconds=1_000_000.0,
        )
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["completed_epoch"], protocol.COST_SAMPLE_EPOCHS)
        cost = fx.read_json(Path(result["run_dir"]) / "cost.json")
        self.assertEqual(cost["status"], "fail")
        payload = checkpoints.load_last(
            Path(result["run_dir"]) / "recovery" / "last.pt"
        )
        self.assertEqual(payload["completed_epoch"], protocol.COST_SAMPLE_EPOCHS)

    def test_cost_sample_continues_the_same_trajectory(self):
        result = fx.fit_run(
            self.root / "runs",
            run_id="cost-continue",
            data=self.data,
            epochs=11,
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["completed_epoch"], 11)
        gradients = fx.read_json(Path(result["run_dir"]) / "gradients.json")
        self.assertEqual(gradients["total_updates"], 11 * protocol.UPDATES_PER_EPOCH)
        cost = fx.read_json(Path(result["run_dir"]) / "cost.json")
        self.assertEqual(cost["status"], "ok")
        self.assertIsNotNone(cost["estimated"]["fit_seconds"])


class CheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _payload(self, epoch: int = 1) -> dict:
        config = protocol.FitConfig(epochs=3, hidden_size=4)
        return {
            "artifact_format_version": 2,
            "scientific_version": protocol.SCIENTIFIC_VERSION,
            "kind": "last",
            "config": config.to_payload(),
            "completed_epoch": epoch,
            "updates": epoch * protocol.UPDATES_PER_EPOCH,
            "next_window": 0,
            "model_state": {"weight": torch.zeros(2)},
            "optimizer_state": {"state": {}, "param_groups": []},
            "random_states": {
                "python": __import__("random").getstate(),
                "numpy": np.random.get_state(),
                "torch": torch.get_rng_state(),
            },
            "history": [],
            "scores": {},
            "update_records": [],
            "best": None,
            "condition": {"condition_id": "c"},
            "data": {"source_sha256": "a", "node_keys_sha256": "b"},
        }

    def test_atomic_publication_keeps_the_previous_complete_version(self):
        path = self.root / "recovery" / "last.pt"
        first = checkpoints.publish_last(path, self._payload(1))
        before = path.read_bytes()
        with mock.patch(
            "benchmark.multivariate_time_series.temporal.checkpoints.os.replace",
            side_effect=OSError("rename failed"),
        ):
            with self.assertRaises(OSError):
                checkpoints.publish_last(path, self._payload(2))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(
            checkpoints.load_last(path)["completed_epoch"], 1
        )
        second = checkpoints.publish_last(path, self._payload(2))
        self.assertNotEqual(first, second)
        self.assertEqual(checkpoints.load_last(path)["completed_epoch"], 2)

    def test_legacy_corrupt_and_best_checkpoints_are_rejected(self):
        legacy = self.root / "legacy.pt"
        torch.save({"model": {}}, legacy)
        with self.assertRaises(protocol.ProtocolError) as context:
            checkpoints.load_last(legacy)
        self.assertIn("legacy", str(context.exception))
        corrupt = self.root / "corrupt.pt"
        corrupt.write_bytes(b"truncated")
        with self.assertRaises(protocol.ProtocolError):
            checkpoints.load_last(corrupt)
        best_path = self.root / "best.pt"
        config = protocol.FitConfig(epochs=2, hidden_size=4)
        checkpoints.save_best(
            best_path,
            checkpoints.best_payload(
                config,
                best={"epoch": 1, "updates": 19, "validation": {"MSE": 1.0, "MAE": 1.0}},
                model_state={"weight": torch.zeros(2)},
                optimizer_state={},
                scale=1.0,
            ),
        )
        with self.assertRaises(protocol.ProtocolError) as context:
            checkpoints.load_last(best_path)
        self.assertIn("not 'last'", str(context.exception))
        payload = checkpoints.load_best(best_path, expected_config=config)
        self.assertEqual(payload["manifest"]["epoch"], 1)
        with self.assertRaises(protocol.ProtocolError):
            checkpoints.load_best(
                best_path, expected_config=protocol.FitConfig(epochs=3, hidden_size=4)
            )


class ResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.data = fx.in_memory("r0", 4, seed=7)
        self.ledger = self.root / "ledger.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _interrupt(self, run_id: str = "parent"):
        def interrupt(trajectory, epoch, window):
            if trajectory.completed_epoch == 1 and epoch == 2 and window == 2:
                raise temporal_engine.PauseRequest(
                    "simulated_mid_epoch_interruption", {"epoch": epoch}
                )

        return fx.fit_run(
            self.root / "runs",
            run_id=run_id,
            data=self.data,
            epochs=3,
            node_chunk=2,
            after_update=interrupt,
            ledger_path=self.ledger,
        )

    def test_interrupted_and_resumed_trajectory_matches_uninterrupted(self):
        uninterrupted = fx.fit_run(
            self.root / "runs",
            run_id="uninterrupted",
            data=self.data,
            epochs=3,
            node_chunk=2,
            ledger_path=self.ledger,
        )
        interrupted = self._interrupt()
        self.assertEqual(interrupted["status"], "paused")
        self.assertEqual(interrupted["completed_epoch"], 1)
        parent_dir = Path(interrupted["run_dir"])
        before = fx.tree_digest(parent_dir)
        resumed = fx.fit_run(
            self.root / "runs",
            run_id="resumed",
            data=self.data,
            operation="resume",
            parent_dir=parent_dir,
            ledger_path=self.ledger,
        )
        self.assertEqual(resumed["status"], "completed")
        self.assertEqual(fx.tree_digest(parent_dir), before)
        reference = checkpoints.load_last(
            Path(uninterrupted["run_dir"]) / "recovery" / "last.pt"
        )
        restored = checkpoints.load_last(
            Path(resumed["run_dir"]) / "recovery" / "last.pt"
        )
        self.assertEqual(restored["completed_epoch"], 3)
        for name, tensor in reference["model_state"].items():
            self.assertTrue(
                torch.allclose(tensor, restored["model_state"][name], rtol=1e-6, atol=1e-8),
                f"resumed final parameter {name} differs",
            )
        self.assertEqual(
            reference["best"]["epoch"], restored["best"]["epoch"]
        )
        left = np.load(Path(uninterrupted["run_dir"]) / "validation" / "prediction.npy")
        right = np.load(Path(resumed["run_dir"]) / "validation" / "prediction.npy")
        np.testing.assert_allclose(left, right, rtol=1e-6, atol=1e-8)
        resumed_config = fx.read_json(Path(resumed["run_dir"]) / "config.json")
        self.assertEqual(
            resumed_config["parent"]["run_id"], "parent"
        )
        self.assertEqual(
            resumed_config["parent"]["completed_epoch"], 1
        )

    def test_replay_and_failed_work_are_billed_without_resetting_budget(self):
        uninterrupted = fx.fit_run(
            self.root / "runs",
            run_id="ledger-reference",
            data=self.data,
            epochs=3,
            node_chunk=2,
            ledger_path=self.ledger,
        )
        del uninterrupted
        interrupted = self._interrupt(run_id="ledger-parent")
        resumed = fx.fit_run(
            self.root / "runs",
            run_id="ledger-resumed",
            data=self.data,
            operation="resume",
            parent_dir=Path(interrupted["run_dir"]),
            ledger_path=self.ledger,
        )
        self.assertEqual(resumed["status"], "completed")
        ledger = resources.Ledger(self.ledger, batch_id="p02-t006")
        entries = ledger.payload["entries"]
        measured = [entry for entry in entries if entry["kind"] == "measured"]
        self.assertGreaterEqual(len(measured), 3)
        statuses = {entry["status"] for entry in measured}
        self.assertIn("paused", statuses)
        self.assertIn("completed", statuses)
        self.assertAlmostEqual(
            ledger.active_seconds(), sum(entry["seconds"] for entry in measured)
        )
        self.assertGreater(ledger.active_seconds(), 0.0)

    def test_exhausted_or_mismatched_parent_is_refused(self):
        interrupted = self._interrupt(run_id="budget-parent")
        parent_dir = Path(interrupted["run_dir"])
        saturated = resources.Ledger(self.root / "saturated.json", batch_id="p02-t006")
        saturated.record(
            execution_id="spent",
            run_id="prior",
            seconds=protocol.BATCH_SECONDS,
        )
        with self.assertRaises(recovery.RecoveryError):
            fx.fit_run(
                self.root / "runs",
                run_id="budget-resume",
                data=self.data,
                operation="resume",
                parent_dir=parent_dir,
                ledger_path=self.root / "saturated.json",
            )
        clone = self.root / "clone"
        clone.mkdir()
        for name in ("config.json", "provenance.json", "status.json", "recovery"):
            source = parent_dir / name
            if source.is_dir():
                __import__("shutil").copytree(source, clone / name)
            else:
                __import__("shutil").copy2(source, clone / name)
        provenance = fx.read_json(clone / "provenance.json")
        provenance["data"]["source_sha256"] = "f" * 64
        fx.write_json(clone / "provenance.json", provenance)
        with self.assertRaises(recovery.RecoveryError):
            recovery.load_parent(clone)
        os.replace(self.root / "nope", self.root / "nope") if False else None


if __name__ == "__main__":
    unittest.main()
