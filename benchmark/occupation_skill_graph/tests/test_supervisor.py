"""Isolated worker supervision: budgets, memory, monitor preflight, cancellation."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from benchmark.occupation_skill_graph import artifacts, checks, supervisor
from benchmark.occupation_skill_graph.tests import fixtures as fx


class SupervisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.fixture = fx.standard_fixture(self.root / "data")
        self.output = self.root / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _spec(self, run_id: str, **overrides):
        return fx.build_spec(
            self.root,
            fixture=self.fixture,
            run_id=run_id,
            output_root=self.output,
            monitor_interval_seconds=0.01,
            **overrides,
        )

    def test_short_budget_terminates_without_success(self) -> None:
        spec = self._spec(
            "short-budget",
            build_timeout_seconds=0.0001,
            trend_timeout_seconds=0.0001,
        )
        code = supervisor.launch(spec)
        self.assertNotEqual(code, 0)
        run_dir = self.output / "short-budget"
        status = json.loads((run_dir / "artifacts/status.json").read_text())
        self.assertEqual(status["state"], "terminated")
        self.assertIn("timeout", status["reason"])
        self.assertFalse((run_dir / "report.json").exists())

    def test_rss_limit_terminates_with_units(self) -> None:
        calls = {"count": 0}

        def probe(pid: int):
            calls["count"] += 1
            if calls["count"] == 1:
                return {"status": "ok", "bytes": 1024, "method": "fixture"}
            return {
                "status": "ok",
                "bytes": 8 * 1024 * 1024,
                "native_unit": "bytes",
                "method": "fixture probe",
                "scope": "worker process resident set size, sampled",
            }

        spec = self._spec("rss-limit", max_rss_bytes=1024 * 1024)
        code = supervisor.launch(spec, probe=probe)
        self.assertNotEqual(code, 0)
        run_dir = self.output / "rss-limit"
        status = json.loads((run_dir / "artifacts/status.json").read_text())
        self.assertEqual(status["state"], "terminated")
        self.assertEqual(status["reason"], "rss_limit_exceeded")
        self.assertEqual(status["detail"]["limit_bytes"], 1024 * 1024)
        self.assertEqual(status["detail"]["observed_bytes"], 8 * 1024 * 1024)
        self.assertEqual(status["detail"]["measurement"]["native_unit"], "bytes")
        self.assertFalse((run_dir / "report.json").exists())

    def test_unsupported_monitor_fails_preflight(self) -> None:
        spec = self._spec("no-monitor")

        def probe(pid: int):
            return {"status": "unsupported", "reason": "fixture monitor unavailable"}

        with self.assertRaises(supervisor.SupervisorError):
            supervisor.launch(spec, probe=probe)
        self.assertFalse((self.output / "no-monitor").exists())

    def test_monitor_loss_after_preflight_fails_real_worker(self) -> None:
        for failure in ("unsupported", "unavailable"):
            with self.subTest(sample_status=failure):
                spec = self._spec(f"monitor-{failure}")
                spec.repo_root = str(Path(__file__).resolve().parents[3])
                calls = 0

                def probe(pid):
                    nonlocal calls
                    calls += 1
                    if calls == 1:
                        return {"status": "ok", "bytes": 1024}
                    return {"status": failure, "bytes": None,
                            "reason": "injected monitor loss"}

                self.assertNotEqual(supervisor.launch(spec, probe=probe), 0)
                run = spec.run_directory
                status = artifacts.read_status(run)
                self.assertEqual(status["state"], "terminated")
                self.assertEqual(status["reason"], "rss_monitor_failure")
                self.assertEqual(status["detail"]["measurement"]["status"], failure)
                record = json.loads((run / "artifacts/supervisor.json").read_text())
                self.assertEqual(record["reason"], "rss_monitor_failure")
                self.assertIn("injected monitor loss", json.dumps(record))
                self.assertFalse((run / "artifacts-sha256.json").exists())

    def test_monitor_loss_retains_completed_stage(self) -> None:
        spec = self._spec("completed-stage")
        spec.repo_root = str(Path(__file__).resolve().parents[3])
        run = spec.run_directory

        def probe(pid):
            progress = artifacts.read_progress(run) or {}
            if "source" in progress.get("completed_stages", []):
                return {"status": "unavailable", "bytes": None,
                        "reason": "lost after source"}
            return {"status": "ok", "bytes": 1024}

        # A separate worker writes real completed source evidence, then waits.
        script = (
            "import time\n"
            "from benchmark.occupation_skill_graph import runner\n"
            f"spec = runner.BuildSpec.from_dict({spec.to_dict()!r})\n"
            "spec.run_reserved = True\n"
            "spec.fail_after_stage = 'source'\n"
            "try: runner.execute_build(spec)\n"
            "except runner.InjectedFailure: pass\n"
            "time.sleep(30)\n"
        )
        code = supervisor.launch(spec, probe=probe,
                                 worker_argv=[sys.executable, "-c", script])
        self.assertNotEqual(code, 0)
        status = artifacts.read_status(run)
        self.assertEqual(status["reason"], "rss_monitor_failure")
        self.assertIn("source", status["completed_stages"])
        self.assertTrue((run / "artifacts/observations.npy").exists())
        self.assertFalse((run / "artifacts-sha256.json").exists())

    def test_exited_worker_does_not_require_rss_sample(self) -> None:
        spec = self._spec("exit-race")
        spec.repo_root = str(Path(__file__).resolve().parents[3])
        workers = []
        real_popen = supervisor.subprocess.Popen

        def start(*args, **kwargs):
            worker = real_popen(*args, **kwargs)
            workers.append(worker)
            return worker

        def probe(pid):
            if not workers:
                return {"status": "ok", "bytes": 1024}
            # Wait for an actual worker to exit during its RSS probe.
            workers[0].wait(timeout=10)
            return {"status": "unavailable", "bytes": None,
                    "reason": "worker has exited"}

        with mock.patch.object(supervisor.subprocess, "Popen", side_effect=start):
            self.assertEqual(supervisor.launch(spec, probe=probe), 0)
        result = checks.check_artifact(spec.run_directory, self.root / "race-check.json",
                                       repo_root=Path(spec.repo_root), command=["check"])
        self.assertEqual(result["status"], "ok", result["report"]["errors"])

    def test_successful_supervised_build_is_checkable(self) -> None:
        spec = self._spec("supervised-ok")
        spec.repo_root = str(Path(__file__).resolve().parents[3])
        self.assertEqual(supervisor.launch(spec), 0)
        result = checks.check_artifact(spec.run_directory, self.root / "check.json",
                                       repo_root=Path(spec.repo_root), command=["check"])
        self.assertEqual(result["status"], "ok", result["report"]["errors"])

    def test_cancellation_preserves_interrupted_state(self) -> None:
        spec = self._spec("cancelled")
        event = threading.Event()
        timer = threading.Timer(0.2, event.set)
        timer.start()
        try:
            code = supervisor.launch(
                spec,
                worker_argv=[
                    sys.executable,
                    "-c",
                    "import time; time.sleep(30)",
                ],
                cancel_event=event,
            )
        finally:
            timer.cancel()
        self.assertEqual(code, 130)
        run_dir = self.output / "cancelled"
        status = json.loads((run_dir / "artifacts/status.json").read_text())
        self.assertEqual(status["state"], "interrupted")
        self.assertFalse((run_dir / "report.json").exists())


    def test_nonzero_exit_after_success_status_cannot_remain_success(self) -> None:
        run_dir = self.output / "hard-kill"
        script = (
            "from pathlib import Path\n"
            f"p = Path({str(run_dir / 'artifacts/status.json')!r})\n"
            "p.parent.mkdir(parents=True, exist_ok=True)\n"
            "p.write_text('{\"state\": \"succeeded\"}')\n"
            "raise SystemExit(1)\n"
        )
        spec = self._spec("hard-kill")
        code = supervisor.launch(spec, worker_argv=[sys.executable, "-c", script])
        self.assertNotEqual(code, 0)
        status = json.loads((run_dir / "artifacts/status.json").read_text())
        self.assertEqual(status["state"], "failed")
        self.assertEqual(status["reason"], "worker_hard_killed_after_success_status")

    def test_no_automatic_retry(self) -> None:
        counter = self.root / "attempts.txt"
        script = (
            "from pathlib import Path\n"
            f"p = Path({str(counter)!r})\n"
            "p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1')\n"
            "raise SystemExit(1)\n"
        )
        spec = self._spec("no-retry")
        code = supervisor.launch(spec, worker_argv=[sys.executable, "-c", script])
        self.assertNotEqual(code, 0)
        self.assertEqual(counter.read_text(), "1")
        status = json.loads(
            (self.output / "no-retry/artifacts/status.json").read_text()
        )
        self.assertNotEqual(status["state"], "succeeded")


if __name__ == "__main__":
    unittest.main()
