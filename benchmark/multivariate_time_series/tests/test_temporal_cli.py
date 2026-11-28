"""CLI surface: staged operations, migration errors and a development chain."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import temporal_fixtures as fx
from benchmark.multivariate_time_series.temporal import cli, protocol, resources

MODULE = "benchmark.multivariate_time_series.effective_temporal_training"
REPO_ROOT = Path(__file__).resolve().parents[3]


def run_cli(*arguments: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(REPO_ROOT), environment.get("PYTHONPATH")) if value
    )
    return subprocess.run(
        [sys.executable, "-m", MODULE, *arguments],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


class CliContractTests(unittest.TestCase):
    def test_version_flag_prints_current_scientific_version(self):
        completed = run_cli("--version")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), protocol.SCIENTIFIC_VERSION)

    def test_help_lists_every_staged_operation_without_data(self):
        completed = run_cli("--help")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for operation in protocol.OPERATIONS:
            self.assertIn(operation, completed.stdout)

    def test_legacy_invocation_is_rejected_with_migration_message(self):
        completed = run_cli(
            "--data", "dataset/demand/r0.parquet", "--run-dir", "scratch/legacy"
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("staged", completed.stderr)
        self.assertIn("fit", completed.stderr)
        self.assertIn("select", completed.stderr)
        self.assertIn("report", completed.stderr)

    def test_invalid_option_and_value_are_usage_errors(self):
        completed = run_cli("fit", "--nonsense")
        self.assertEqual(completed.returncode, 2)
        completed = run_cli(
            "fit",
            "--data-name", "r9",
            "--run-id", "x",
        )
        self.assertEqual(completed.returncode, 2)

    def test_formal_100_epoch_request_fails_before_creating_worker_or_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed = run_cli(
                "fit", "--purpose", "formal", "--data-name", "r0",
                "--data", str(root / "unused.parquet"), "--run-id", "formal-100",
                "--output-root", str(root / "runs"), "--epochs", "100",
            )
            self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
            self.assertIn("formal purpose requires complete protocol controls", completed.stdout)
            self.assertFalse((root / "runs" / "formal-100").exists())

    def test_budget_debit_cli_requires_existing_matching_ledger_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "ledger.json"
            ledger = resources.Ledger(ledger_path, batch_id="batch")
            ledger.record(execution_id="prior", run_id="prior", seconds=12.0)
            arguments = (
                "budget-debit", "--ledger", str(ledger_path), "--batch-id", "batch",
                "--debit-id", "preparation", "--seconds", "900", "--reason", "prior preparation",
            )
            first = run_cli(*arguments)
            second = run_cli(*arguments)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            payload = json.loads(second.stdout)
            self.assertEqual(payload["debited_seconds"], 900.0)
            self.assertEqual(payload["effective_used_seconds"], 912.0)
            loaded = resources.Ledger(ledger_path, batch_id="batch")
            self.assertEqual(len(loaded.payload["entries"]), 2)
            conflict = run_cli(*arguments[:-4], "--seconds", "901", "--reason", "changed")
            self.assertNotEqual(conflict.returncode, 0)
            unbound = Path(temporary) / "unbound.json"
            unbound.write_bytes(b'{"version":1,"entries":[]}')
            before = unbound.read_bytes()
            rejected = run_cli(arguments[0], "--ledger", str(unbound), *arguments[3:])
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("stored batch_id", rejected.stdout)
            self.assertEqual(unbound.read_bytes(), before)

    def test_development_output_alias_into_formal_namespace_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = fx.write_demand(
                root / "r0.parquet", "r0", fx.r0_keys(3), fx.synthetic_signal(3, seed=2)
            )
            formal = REPO_ROOT / "research" / "runs"
            completed = run_cli(
                "fit",
                "--data-name", "r0",
                "--data", str(data),
                "--model", "GRU",
                "--seed", "0",
                "--epochs", "1",
                "--hidden-size", "4",
                "--node-chunk", "3",
                "--run-id", "e13-cli-alias",
                "--purpose", "development",
                "--output-root", str(formal),
                "--memory-available-bytes", str(16 * protocol.GIB),
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse((formal / "e13-cli-alias").exists())
            link = root / "linked"
            link.symlink_to(formal, target_is_directory=True)
            completed = run_cli(
                "fit",
                "--data-name", "r0",
                "--data", str(data),
                "--model", "GRU",
                "--seed", "0",
                "--epochs", "1",
                "--hidden-size", "4",
                "--node-chunk", "3",
                "--run-id", "e13-cli-alias-2",
                "--purpose", "development",
                "--output-root", str(link),
                "--memory-available-bytes", str(16 * protocol.GIB),
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse((formal / "e13-cli-alias-2").exists())


class DevelopmentChainTests(unittest.TestCase):
    """One temporary r0/GRU chain through every staged CLI operation."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.report_dir = self.root / "reports"
        self.data = fx.write_demand(
            self.root / "r0.parquet",
            "r0",
            fx.r0_keys(4),
            fx.synthetic_signal(4, seed=31),
        )
        self.common = [
            "--data-name", "r0",
            "--data", str(self.data),
            "--model", "GRU",
            "--epochs", "1",
            "--hidden-size", "4",
            "--layers", "1",
            "--node-chunk", "3",
            "--purpose", "development",
            "--output-root", str(self.root / "runs"),
            "--memory-available-bytes", str(16 * protocol.GIB),
        ]

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _fit(self, run_id: str, seed: int, learning_rate: float, role: str,
             candidate: str) -> subprocess.CompletedProcess:
        completed = run_cli(
            "fit",
            *self.common,
            "--seed", str(seed),
            "--learning-rate", str(learning_rate),
            "--run-id", run_id,
            "--candidate-role", candidate,
            "--repeat-role", role,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return completed

    def test_staged_development_chain_and_saved_only_checks(self):
        self._fit("cand-low", 0, 1e-3, "a", "screening")
        self._fit("cand-high", 0, 3e-3, "a", "screening")
        self._fit("a0", 0, 1e-3, "a", "confirmation")
        self._fit("b0", 0, 1e-3, "b", "confirmation")
        select = run_cli(
            "select",
            "--candidate", str(self.root / "runs" / "cand-low"),
            "--candidate", str(self.root / "runs" / "cand-high"),
            "--block-id", "cli-block",
            "--purpose", "development",
            "--output-root", str(self.root / "blocks"),
        )
        self.assertEqual(select.returncode, 0, select.stdout + select.stderr)
        block = self.root / "blocks" / "cli-block"
        self.assertTrue((block / "selection.json").is_file())
        diagnose = run_cli(
            "diagnose",
            "--block", str(block),
            "--a-run", f"0={self.root / 'runs' / 'a0'}",
            "--b-run", f"0={self.root / 'runs' / 'b0'}",
            "--purpose", "development",
            "--report", str(self.report_dir / "diagnose.json"),
        )
        self.assertEqual(
            diagnose.returncode, 1, diagnose.stdout + diagnose.stderr
        )
        self.assertTrue((self.report_dir / "diagnose.json").is_file())
        first_report = fx.read_json(self.report_dir / "diagnose.json")
        self.assertEqual(first_report["status"], "failed")
        self.assertFalse((block / "latest-diagnostics.json").exists())
        self.assertFalse((block / "diagnostics").exists())
        second = run_cli(
            "diagnose",
            "--block", str(block),
            "--a-run", f"0={self.root / 'runs' / 'a0'}",
            "--b-run", f"0={self.root / 'runs' / 'b0'}",
            "--purpose", "development",
            "--diagnostics-id", "second-diagnostics",
            "--report", str(self.report_dir / "diagnose-2.json"),
        )
        self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
        self.assertTrue((self.report_dir / "diagnose-2.json").exists())
        collision = run_cli(
            "diagnose",
            "--block", str(block),
            "--a-run", f"0={self.root / 'runs' / 'a0'}",
            "--purpose", "development",
            "--diagnostics-id", "second-diagnostics",
            "--report", str(self.report_dir / "diagnose-2.json"),
        )
        self.assertEqual(collision.returncode, 1, collision.stdout + collision.stderr)

        report = run_cli(
            "report",
            "--data-name", "r0",
            "--data", str(self.data),
            "--block", str(block),
            "--run", str(self.root / "runs" / "cand-low"),
            "--run-id", "cli-report",
            "--purpose", "development",
            "--output-root", str(self.root / "runs"),
        )
        self.assertEqual(report.returncode, 4, report.stdout + report.stderr)
        report_dir = self.root / "runs" / "cli-report"
        payload = fx.read_json(report_dir / "report.json")
        self.assertEqual(payload["test_windows"]["starts"], [24, 25, 26, 27])
        self.assertEqual(payload["status"], "development_incomplete")
        self.assertFalse(payload["protocol_complete"])

        recompute = run_cli(
            "recompute",
            "--run-dir", str(report_dir),
            "--report", str(self.report_dir / "recompute.json"),
        )
        self.assertEqual(recompute.returncode, 0, recompute.stdout + recompute.stderr)
        compare = run_cli(
            "compare",
            "--run-a", str(self.root / "runs" / "a0"),
            "--run-b", str(self.root / "runs" / "b0"),
            "--report", str(self.report_dir / "compare.json"),
        )
        self.assertEqual(compare.returncode, 0, compare.stdout + compare.stderr)
        self.assertEqual(fx.read_json(self.report_dir / "compare.json")["status"], "pass")

    def test_region_and_r2_with_the_second_encoder(self):
        cases = [
            ("region", fx.region_keys(2, 2), "LSTM"),
            ("r2", fx.r2_keys(2, 2), "GRU"),
        ]
        for data_name, keys, model in cases:
            with self.subTest(dataset=data_name, model=model):
                data = fx.write_demand(
                    self.root / f"{data_name}.parquet",
                    data_name,
                    keys,
                    fx.synthetic_signal(len(keys), seed=17),
                )
                completed = run_cli(
                    "fit",
                    "--data-name", data_name,
                    "--data", str(data),
                    "--model", model,
                    "--epochs", "1",
                    "--hidden-size", "4",
                    "--node-chunk", "3",
                    "--run-id", f"cli-{data_name}-{model.lower()}",
                    "--purpose", "development",
                    "--output-root", str(self.root / "runs"),
                    "--memory-available-bytes", str(16 * protocol.GIB),
                )
                self.assertEqual(
                    completed.returncode, 0, completed.stdout + completed.stderr
                )
                config = fx.read_json(
                    self.root / "runs" / f"cli-{data_name}-{model.lower()}" / "config.json"
                )
                self.assertEqual(config["dataset"]["name"], data_name)
                self.assertEqual(config["config"]["model"], model)
                provenance = fx.read_json(
                    self.root / "runs" / f"cli-{data_name}-{model.lower()}" / "provenance.json"
                )
                self.assertEqual(provenance["data"]["dataset"], data_name)
                self.assertEqual(
                    provenance["data"]["key_columns"],
                    list(fx.p01.node_key_columns(data_name)),
                )

    def test_successful_worker_exit_during_rss_sample_keeps_completed_status(self):
        import psutil

        sampling = threading.Event()
        worker_exited = threading.Event()
        missing = []
        sample_rss = resources.sample_process_tree_rss
        controller = threading.current_thread()

        def sample(pid):
            if threading.current_thread() is not controller:
                sampling.set()
                if not worker_exited.wait(timeout=60):
                    raise TimeoutError("worker did not exit during the RSS sample")
            try:
                return sample_rss(pid)
            except psutil.NoSuchProcess:
                missing.append(pid)
                raise

        class ExitOverlapWatchdog(resources.Watchdog):
            def start(self):
                super().start()
                if not sampling.wait(timeout=5):
                    raise TimeoutError("background RSS sample did not start")
                return self

            def stop(self):
                worker_exited.set()
                super().stop()

        with (
            mock.patch.object(resources, "Watchdog", ExitOverlapWatchdog),
            mock.patch.object(resources, "sample_process_tree_rss", side_effect=sample),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            code = cli.main((
                "fit", *self.common, "--run-id", "sample-overlap", "--monitor-interval", "0.05",
            ))

        self.assertEqual(len(missing), 1, output.getvalue())
        self.assertEqual(code, cli.EXIT_OK, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["status"], "completed")
        root = self.root / "runs"
        run = root / "sample-overlap"
        self.assertEqual(fx.read_json(run / "report.json")["status"], "completed")
        self.assertEqual(fx.read_json(run / "status.json")["state"], "completed")
        ledger = resources.Ledger(root / "ledger.json", "p02-t006", require_existing=True)
        self.assertEqual(ledger.payload["entries"][-1]["status"], "finished")


class PreflightCliTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Win32 trailing filename aliases")
    def test_preflight_refuses_windows_aliases_of_deferred_bill(self):
        for prefix, suffix in (("", ""), ("", "."), ("", " "), ("\\\\?\\", ""), ("", ":report")):
            with self.subTest(prefix=prefix, suffix=suffix), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                path = root / "ledger.json"
                ledger = resources.Ledger(path, "fixture")
                ledger.record(execution_id="prior", run_id="prior", seconds=100)
                ledger.register_debit(debit_id="prep", seconds=900, reason="fixture")
                before = path.read_bytes()
                pending = root / "ledger.json.pending-bill.json"
                result = run_cli(
                    "preflight", "--ledger", str(path), "--batch-id", "fixture",
                    "--out", prefix + str(pending) + suffix, "--output-root", str(root),
                    "--memory-available-bytes", str(16 * protocol.GIB),
                    "--disk-free-bytes", str(16 * protocol.GIB),
                )
                self.assertEqual(result.returncode, cli.EXIT_USAGE, result.stdout + result.stderr)
                self.assertIn("separate from the batch ledger", result.stdout)
                self.assertEqual(path.read_bytes(), before)
                self.assertFalse(pending.exists())
                fresh = resources.Ledger(path, "fixture", require_existing=True)
                self.assertEqual(fresh.effective_used_seconds(), 1000)

    def test_preflight_output_cannot_alias_batch_bookkeeping(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "ledger.json"
            ledger = resources.Ledger(path, "batch")
            ledger.record(execution_id="old", run_id="old", seconds=100)
            ledger.register_debit(debit_id="prep", seconds=900, reason="fixture")
            before = path.read_bytes()
            targets = [str(path), "ledger.json"]
            pending = root / "ledger.json.pending-bill.json"
            worker_lock = root / "ledger.json.worker.lock"
            guard = root / "ledger.json.worker.lock.guard"
            targets.extend(str(item) for item in (pending, worker_lock, guard))
            targets.extend((
                "ledger.json.lock", "./ledger.json.pending-bill.json",
                str(pending / "preflight.json"),
            ))
            for name, link in (("hardlink", os.link), ("symlink", os.symlink)):
                alias = root / name
                try:
                    link(path, alias)
                except (OSError, NotImplementedError):
                    continue
                targets.append(str(alias))
            args = ("preflight", "--ledger", str(path), "--batch-id", "batch",
                    "--output-root", str(root), "--memory-available-bytes", str(16 * protocol.GIB),
                    "--disk-free-bytes", str(16 * protocol.GIB))
            for target in targets:
                with self.subTest(target=target):
                    result = run_cli(*args, "--out", target, cwd=root)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("separate from the batch ledger", result.stdout)
                    self.assertEqual(path.read_bytes(), before)
                    self.assertTrue(all(not item.exists() for item in (pending, worker_lock, guard)))
            destination = root / "preflight.json"
            result = run_cli(*args, "--out", str(destination), cwd=root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(fx.read_json(destination)["status"], "pass")
            final = resources.Ledger(path, "batch")
            self.assertEqual(final.payload["entries"][:2], ledger.payload["entries"])
            self.assertEqual(final.payload["ledger_id"], ledger.payload["ledger_id"])
            self.assertEqual(len(final.payload["entries"]), 3)
            self.assertEqual(final.payload["entries"][-1]["kind"], "measured")
            self.assertGreater(final.payload["entries"][-1]["seconds"], 0)

    def test_formal_preflight_rejects_injected_resource_readings(self):
        completed = run_cli(
            "preflight",
            "--purpose", "formal",
            "--run-id", "formal-preflight",
            "--memory-available-bytes", str(16 * protocol.GIB),
        )
        self.assertEqual(completed.returncode, 2, completed.stdout)
        self.assertIn("development software", completed.stdout + completed.stderr)

    def test_preflight_is_machine_readable_without_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            completed = run_cli(
                "preflight",
                "--purpose", "development",
                "--run-id", "cli-preflight",
                "--output-root", temporary,
                "--memory-available-bytes", str(16 * protocol.GIB),
                "--disk-free-bytes", str(10 * protocol.GIB),
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["checks"]["data"]["status"], "not_supplied")
            self.assertEqual(payload["checks"]["threads"]["status"], "pass")

    def test_standalone_preflight_bills_pass_and_failure_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ledger_path = root / "ledger.json"
            ledger = resources.Ledger(ledger_path, batch_id="batch")
            ledger.record(execution_id="prior", run_id="prior", seconds=2.0)
            base = (
                "preflight", "--purpose", "development", "--batch-id", "batch",
                "--ledger", str(ledger_path), "--output-root", str(root),
                "--memory-available-bytes", str(8 * protocol.GIB),
                "--disk-free-bytes", str(8 * protocol.GIB),
            )
            passed = run_cli(*base, "--run-id", "preflight-pass")
            failed = run_cli(*base, "--run-id", "preflight-fail", "--dependencies-missing", "torch")
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            self.assertEqual(failed.returncode, 1, failed.stdout + failed.stderr)
            loaded = resources.Ledger(ledger_path, batch_id="batch")
            entries = [entry for entry in loaded.payload["entries"] if entry.get("run_id") == "run_preflight"]
            self.assertEqual(len(entries), 2)
            self.assertEqual({entry["status"] for entry in entries}, {"pass", "fail"})


class ResumeCliTests(unittest.TestCase):
    def test_interrupted_controller_bills_real_worker_and_allows_resume(self):
        for defer_bill in (False, True):
            with self.subTest(defer_bill=defer_bill), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = fx.write_demand(
                    root / "r0.parquet", "r0", fx.r0_keys(3), fx.synthetic_signal(3, seed=4)
                )
                ledger_path = root / "batch.json"
                ledger = resources.Ledger(ledger_path, "fixture")
                ledger.record(execution_id="prior", run_id="prior", seconds=100)
                ledger.register_debit(debit_id="prep", seconds=900, reason="fixture")
                parent = root / "parents" / "fit"
                checkpoint = parent / "recovery" / "last.pt"
                resource_readings = (
                    "--memory-available-bytes", str(16 * protocol.GIB),
                    "--disk-free-bytes", str(16 * protocol.GIB),
                )
                supervise = cli.supervise_worker
                publish = resources.Ledger._publish_json
                worker = None
                interrupted_at = None
                reaped_at = None
                blocked = []

                def interrupt_after_checkpoint(process, **kwargs):
                    nonlocal worker
                    worker = process

                    def sleeper(seconds):
                        nonlocal interrupted_at
                        if checkpoint.is_file():
                            self.assertIsNone(process.poll())
                            interrupted_at = time.monotonic()
                            raise KeyboardInterrupt
                        time.sleep(seconds)

                    def clock():
                        nonlocal reaped_at
                        now = time.monotonic()
                        if interrupted_at is not None:
                            self.assertIsNotNone(process.returncode)
                            reaped_at = now
                        return now

                    return supervise(process, **kwargs, clock=clock, sleeper=sleeper)

                def publish_ledger(path, payload):
                    if defer_bill and interrupted_at is not None and path == ledger_path.resolve():
                        blocked.append(path)
                        raise PermissionError("injected final ledger publication failure")
                    publish(path, payload)

                fit_args = (
                    "fit", "--data-name", "r0", "--data", str(source), "--epochs", "20",
                    "--output-root", str(parent.parent), "--run-id", parent.name,
                    "--ledger", str(ledger_path), "--batch-id", "fixture",
                    "--monitor-interval", "0.02", *resource_readings,
                )
                with (
                    mock.patch.object(cli, "supervise_worker", side_effect=interrupt_after_checkpoint),
                    mock.patch.object(resources.Ledger, "_publish_json", side_effect=publish_ledger),
                    contextlib.redirect_stdout(io.StringIO()) as output,
                ):
                    code = cli.main(fit_args)
                self.assertEqual(code, cli.EXIT_PAUSED, output.getvalue())
                self.assertIsNotNone(worker.returncode)
                self.assertGreaterEqual(reaped_at, interrupted_at)
                self.assertFalse(resources.worker_lock_path(ledger_path).exists())
                self.assertTrue(checkpoint.is_file())
                parent_before = fx.tree_digest(parent)
                stop = fx.read_json(parent / "status.json")["detail"]["stop"]
                self.assertEqual(stop["reason"], "fit controller interrupted")

                pending = root / "batch.json.pending-bill.json"
                self.assertEqual(len(blocked), int(defer_bill))
                self.assertEqual(pending.exists(), defer_bill)
                stored = fx.read_json(ledger_path)
                self.assertEqual(stored["entries"][-1]["status"], "running" if defer_bill else "paused")
                recovered = resources.Ledger(ledger_path, "fixture", require_existing=True)
                bill = recovered.payload["entries"][-1]
                self.assertEqual((bill["run_id"], bill["kind"], bill["status"]), ("fit", "measured", "paused"))
                self.assertEqual(bill["seconds"], stop["execution_seconds"])
                self.assertGreater(bill["seconds"], 0)
                self.assertEqual(recovered.debited_seconds(), 900)
                self.assertAlmostEqual(recovered.effective_used_seconds(), 1000 + bill["seconds"])

                resumed = run_cli(
                    "resume", "--data-name", "r0", "--parent", str(parent), "--run-id", "after-interrupt",
                    "--output-root", str(root / "children"), *resource_readings,
                )
                self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
                child = fx.read_json(root / "children" / "after-interrupt" / "config.json")
                self.assertEqual(child["parent"]["run_id"], "fit")
                self.assertGreaterEqual(child["parent"]["completed_epoch"], 1)
                self.assertEqual(fx.tree_digest(parent), parent_before)
                self.assertFalse(pending.exists())

    def test_resume_inherits_interrupted_parent_and_refuses_incompatible_parents(self):
        from benchmark.multivariate_time_series.temporal import engine

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = fx.write_demand(
                root / "r0.parquet", "r0", fx.r0_keys(3), fx.synthetic_signal(3, seed=4)
            )
            parent_dir = root / "parents" / "parent"
            ledger_path = root / "shared-ledger.json"
            resources.configure_threads()

            def interrupt(trajectory, epoch, window):
                if epoch == 2 and window == 2:
                    raise engine.PauseRequest("fixture interruption")

            parent = fx.fit_run(
                parent_dir.parent, run_id=parent_dir.name, data=fx.load_data("r0", source),
                data_path=source, ledger_path=ledger_path, epochs=3, seed=2,
                after_update=interrupt,
            )
            self.assertEqual((parent["status"], parent["completed_epoch"]), ("paused", 1))
            before = fx.tree_digest(parent_dir)
            args = ("resume", "--data-name", "r0", "--output-root", str(root / "children"),
                    "--memory-available-bytes", str(16 * protocol.GIB),
                    "--disk-free-bytes", str(16 * protocol.GIB))
            shared = ("--ledger", str(ledger_path), "--batch-id", "p02-t006")
            owner_args = cli.build_parser().parse_args(
                ["preflight", "--output-root", str(parent_dir.parent), *shared]
            )
            owner = resources.WorkerLock(cli._lock_path(owner_args), {"run_id": "active"})
            self.assertEqual(owner.acquire()["status"], "acquired")
            with owner:
                before_lock = owner.path.read_bytes()
                fit = run_cli(
                    "fit", *args[1:], *shared, "--data", str(source),
                    "--epochs", "1", "--run-id", "blocked-fit", "--takeover-stale",
                )
                resumed = run_cli(
                    *args, "--parent", str(parent_dir), "--run-id", "blocked-resume",
                    "--takeover-stale",
                )
                inspection = run_cli(
                    "preflight", *args[3:], *shared, "--lock", str(root / "unused.lock"),
                )
                for rejected in (fit, resumed, inspection):
                    self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
                    output = json.loads(rejected.stdout)
                    checks = output.get("preflight", output)["checks"]
                    self.assertEqual(checks["worker_lock"]["state"]["status"], "held")
                self.assertEqual(owner.path.read_bytes(), before_lock)
                self.assertFalse((root / "children").exists())
                other_ledger = root / "other-ledger.json"
                other_args = cli.build_parser().parse_args(
                    ["preflight", "--ledger", str(other_ledger), "--batch-id", "other",
                     "--output-root", str(parent_dir.parent)]
                )
                other = resources.WorkerLock(cli._lock_path(other_args), {"run_id": "other"})
                with other:
                    self.assertEqual(other.acquire()["status"], "acquired")

            result = run_cli(*args, "--parent", str(parent_dir), "--run-id", "resumed")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            child = fx.read_json(root / "children" / "resumed" / "config.json")
            self.assertEqual(child["parent"]["run_id"], "parent")
            self.assertEqual(child["parent"]["completed_epoch"], 1)
            self.assertEqual(child["config"], fx.read_json(parent_dir / "config.json")["config"])
            self.assertEqual(fx.tree_digest(parent_dir), before)
            ledger_bytes = ledger_path.read_bytes()

            missing = run_cli(*args, "--parent", str(root / "absent"), "--run-id", "missing")
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("config.json", missing.stdout)
            checkpoint = parent_dir / "recovery" / "last.pt"
            checkpoint.write_bytes(b"truncated")
            corrupt = run_cli(*args, "--parent", str(parent_dir), "--run-id", "corrupt")
            self.assertNotEqual(corrupt.returncode, 0)
            self.assertIn("unreadable or truncated", corrupt.stdout)
            provenance_path = parent_dir / "provenance.json"
            provenance = fx.read_json(provenance_path)
            provenance["scientific_version"] = "P2-effective-training-L6-H3-v1"
            fx.write_json(provenance_path, provenance)
            historical = run_cli(*args, "--parent", str(parent_dir), "--run-id", "historical")
            self.assertNotEqual(historical.returncode, 0)
            self.assertIn("3bd9fa4", historical.stdout)
            self.assertIn("fresh initialization", historical.stdout)
            self.assertEqual(ledger_path.read_bytes(), ledger_bytes)
            self.assertFalse(any((root / "children" / name).exists()
                                 for name in ("missing", "corrupt", "historical")))


if __name__ == "__main__":
    unittest.main()
