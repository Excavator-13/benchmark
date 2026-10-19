"""Explicit axes, purpose-scoped destinations and the public CLI surface.

Covers tasks 5.1 and 5.5.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmark.graph_value_skeleton import checks as gvs_checks
from benchmark.graph_value_skeleton import cli as gvs_cli
from benchmark.graph_value_skeleton import config as gvs_config
from benchmark.graph_value_skeleton import protocol
from benchmark.graph_value_skeleton.tests import fixtures
from benchmark.nograph_baseline import protocol as p01


class AxisValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="gvs-config-"))
        self.fixture = fixtures.build_fixture(self.root, "r0")

    def _resolve(self, **overrides):
        payload = dict(
            data_name="r0",
            method="self",
            model_seed=0,
            shuffle_seed=None,
            run_id="run-a",
            purpose="development",
            repo_root=protocol.REPO_ROOT,
            output_root=(None if overrides.get("purpose") == "formal" else self.root / "out"),
            demand_path=str(self.fixture["demand_path"]),
            graph_path=str(self.fixture["graph_path"]),
            command=["python", "-m", "benchmark.graph_value_skeleton", "run"],
        )
        payload.update(overrides)
        return gvs_config.resolve_config(**payload)

    def test_method_and_seed_axes(self) -> None:
        with self.assertRaises(ValueError):
            self._resolve(method="shuffled", shuffle_seed=None)
        with self.assertRaises(ValueError):
            self._resolve(method="self", shuffle_seed=0)
        with self.assertRaises(protocol.ProtocolError):
            self._resolve(method="graph", shuffle_seed=1)
        with self.assertRaises(protocol.ProtocolError):
            self._resolve(method="shuffled", shuffle_seed=3)
        with self.assertRaises(protocol.ProtocolError):
            self._resolve(method="magic")
        with self.assertRaises(protocol.ProtocolError):
            self._resolve(model_seed=9)
        with self.assertRaises(protocol.ProtocolError):
            self._resolve(model_seed=-1)
        with self.assertRaises(protocol.ProtocolError):
            self._resolve(purpose="production")
        with self.assertRaises(protocol.ProtocolError):
            self._resolve(data_name="company")
        config = self._resolve(method="shuffled", shuffle_seed=2, model_seed=4)
        self.assertEqual(config.method, "shuffled")
        self.assertEqual(config.shuffle_seed, 2)
        self.assertEqual(config.model_seed, 4)
        self.assertEqual(
            protocol.seed_profile(config.model_seed),
            {"development": False, "final": True},
        )
        self.assertEqual(
            protocol.seed_profile(1), {"development": True, "final": True}
        )

    def test_development_destination_whitelist(self) -> None:
        default = gvs_config.resolve_output_root(protocol.REPO_ROOT, "development")
        self.assertEqual(default, protocol.REPO_ROOT / "scratch" / "graph-value-skeleton")
        temp_root = Path(tempfile.mkdtemp(prefix="gvs-out-"))
        self.assertEqual(
            gvs_config.resolve_output_root(protocol.REPO_ROOT, "development", temp_root),
            temp_root.resolve(),
        )
        for forbidden in (
            protocol.REPO_ROOT / "research",
            protocol.REPO_ROOT / "research" / "runs",
            protocol.REPO_ROOT / "experiments_archive",
            protocol.REPO_ROOT / "dataset",
            protocol.REPO_ROOT / "benchmark",
            Path(tempfile.gettempdir()).parent.parent / "gvs-elsewhere",
        ):
            with self.subTest(path=str(forbidden)):
                with self.assertRaises(gvs_config.ConfigError):
                    gvs_config.resolve_output_root(
                        protocol.REPO_ROOT, "development", forbidden
                    )
        # A symlink inside scratch that resolves into research is rejected.
        scratch = protocol.REPO_ROOT / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        link = scratch / f"gvs-link-{os.getpid()}"
        if link.exists() or link.is_symlink():
            link.unlink()
        try:
            link.symlink_to(protocol.REPO_ROOT / "research", target_is_directory=True)
            with self.assertRaises(gvs_config.ConfigError):
                gvs_config.resolve_output_root(
                    protocol.REPO_ROOT, "development", link / "graph-value-skeleton"
                )
        finally:
            if link.is_symlink():
                link.unlink()

    def test_run_id_cannot_escape(self) -> None:
        root = self.root / "out"
        root.mkdir(parents=True, exist_ok=True)
        for run_id in ("../escape", "a/b", "..", ".", "", "a b"):
            with self.subTest(run_id=run_id):
                with self.assertRaises(gvs_config.ConfigError):
                    gvs_config.validate_run_destination(root, run_id)
        self.assertEqual(
            gvs_config.validate_run_destination(root, "safe-id_1"),
            root / "safe-id_1",
        )

    def test_formal_resolution_is_path_only(self) -> None:
        formal = gvs_config.resolve_output_root(protocol.REPO_ROOT, "formal")
        self.assertEqual(formal, protocol.REPO_ROOT / "research" / "runs")
        with self.assertRaises(gvs_config.ConfigError):
            gvs_config.resolve_output_root(protocol.REPO_ROOT, "formal", self.root)
        config = self._resolve(purpose="formal")
        self.assertEqual(config.purpose, "formal")
        self.assertEqual(
            Path(config.output_root), protocol.REPO_ROOT / "research" / "runs"
        )
        self.assertFalse((protocol.REPO_ROOT / "research" / "runs" / config.run_id).exists())

    def test_purpose_does_not_change_computation(self) -> None:
        development = self._resolve(purpose="development")
        formal = self._resolve(purpose="formal")
        self.assertEqual(
            development.computational_identity(), formal.computational_identity()
        )
        self.assertNotEqual(development.output_root, formal.output_root)

    def test_implementation_root_override_cannot_rebase_protected_trees(self) -> None:
        for relative in (
            "research",
            "research/runs",
            "dataset",
            "benchmark",
            "experiments_archive",
            ".git",
        ):
            with self.subTest(relative=relative):
                with self.assertRaises(gvs_config.ConfigError):
                    gvs_config.resolve_config(
                        data_name="r0",
                        method="self",
                        model_seed=0,
                        shuffle_seed=None,
                        run_id="rebased",
                        purpose="development",
                        repo_root=protocol.REPO_ROOT / relative,
                    )
        link = Path(tempfile.mkdtemp(prefix="gvs-root-link-")) / "research-link"
        link.symlink_to(protocol.REPO_ROOT / "research", target_is_directory=True)
        with self.assertRaises(gvs_config.ConfigError):
            gvs_config.resolve_config(
                data_name="r0",
                method="self",
                model_seed=0,
                shuffle_seed=None,
                run_id="rebased",
                purpose="development",
                repo_root=link,
            )
        with self.assertRaises(gvs_checks.CheckError):
            gvs_checks.validate_report_destination(
                protocol.REPO_ROOT / "research",
                protocol.REPO_ROOT / "research" / "scratch" / "probe.json",
            )
        with self.assertRaises(gvs_checks.CheckError):
            gvs_checks.validate_report_destination(
                link, link / "scratch" / "probe.json"
            )
        # A legitimate temporary implementation root still works.
        temp_root = Path(tempfile.mkdtemp(prefix="gvs-legit-root-"))
        config = gvs_config.resolve_config(
            data_name="r0",
            method="self",
            model_seed=0,
            shuffle_seed=None,
            run_id="legit",
            purpose="development",
            repo_root=temp_root,
            output_root=temp_root / "scratch",
        )
        self.assertEqual(
            Path(config.output_root), (temp_root / "scratch").resolve()
        )

    def test_interleaved_methods_do_not_mutate_module_globals(self) -> None:
        snapshot = {
            "MAIN_SPLIT": p01.MAIN_SPLIT,
            "SPLITS": dict(p01.SPLITS),
            "NAIVE_METHODS": tuple(p01.NAIVE_METHODS),
            "PROTOCOL_VERSION": p01.PROTOCOL_VERSION,
            "MODEL_NAME": p01.MODEL_NAME,
            "LAMBDA_CANDIDATES": tuple(p01.LAMBDA_CANDIDATES),
            "METHODS": tuple(protocol.METHODS),
            "EPOCHS": protocol.EPOCHS,
            "HIDDEN_DIM": protocol.HIDDEN_DIM,
            "ADAM": dict(protocol.ADAM),
        }
        resolved = []
        for method, shuffle_seed in (("self", None), ("graph", None), ("shuffled", 0), ("shuffled", 1), ("self", None)):
            config = self._resolve(method=method, shuffle_seed=shuffle_seed)
            resolved.append((config.method, config.shuffle_seed, config.model_seed))
        self.assertEqual(
            resolved,
            [("self", None, 0), ("graph", None, 0), ("shuffled", 0, 0), ("shuffled", 1, 0), ("self", None, 0)],
        )
        self.assertEqual(snapshot["MAIN_SPLIT"], p01.MAIN_SPLIT)
        self.assertEqual(snapshot["SPLITS"], dict(p01.SPLITS))
        self.assertEqual(snapshot["NAIVE_METHODS"], tuple(p01.NAIVE_METHODS))
        self.assertEqual(snapshot["PROTOCOL_VERSION"], p01.PROTOCOL_VERSION)
        self.assertEqual(snapshot["MODEL_NAME"], p01.MODEL_NAME)
        self.assertEqual(snapshot["LAMBDA_CANDIDATES"], tuple(p01.LAMBDA_CANDIDATES))
        self.assertEqual(snapshot["METHODS"], tuple(protocol.METHODS))
        self.assertEqual(snapshot["EPOCHS"], protocol.EPOCHS)
        self.assertEqual(snapshot["HIDDEN_DIM"], protocol.HIDDEN_DIM)
        self.assertEqual(snapshot["ADAM"], dict(protocol.ADAM))


class CliSurfaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="gvs-cli-"))
        self.fixture = fixtures.build_fixture(self.root, "r0")
        self.output = self.root / "out"

    def test_help_surface(self) -> None:
        help_text = gvs_cli.build_parser().format_help()
        for command in ("run", "recompute", "compare", "summarize-shuffled"):
            self.assertIn(command, help_text)
        run_parser = gvs_cli.build_parser()
        args = run_parser.parse_args(
            [
                "run", "--data-name", "r0", "--method", "shuffled",
                "--model-seed", "1", "--shuffle-seed", "2",
                "--purpose", "development", "--run-id", "x",
            ]
        )
        self.assertEqual(args.method, "shuffled")
        self.assertEqual(args.shuffle_seed, 2)
        self.assertEqual(args.purpose, "development")
        # Rate mode, A/B folds and unknown datasets are not part of the surface.
        for invalid in (
            ["run", "--data-name", "r0", "--method", "self", "--model-seed", "0", "--run-id", "x", "--mode", "rate"],
            ["run", "--data-name", "r0", "--method", "self", "--model-seed", "0", "--run-id", "x", "--fold", "A"],
            ["run", "--data-name", "company", "--method", "self", "--model-seed", "0", "--run-id", "x"],
        ):
            with self.subTest(argv=invalid):
                with self.assertRaises(SystemExit):
                    gvs_cli.build_parser().parse_args(invalid)

    def test_invalid_axes_return_nonzero_before_training(self) -> None:
        code = gvs_cli.main(
            [
                "run", "--data-name", "r0", "--method", "shuffled",
                "--model-seed", "0", "--run-id", "no-seed",
                "--output-root", str(self.output),
                "--demand-path", str(self.fixture["demand_path"]),
                "--graph-path", str(self.fixture["graph_path"]),
            ]
        )
        self.assertEqual(code, 1)
        self.assertFalse((self.output / "no-seed").exists())
        code = gvs_cli.main(
            [
                "run", "--data-name", "r0", "--method", "self",
                "--model-seed", "0", "--shuffle-seed", "1", "--run-id", "bad-seed",
                "--output-root", str(self.output),
                "--demand-path", str(self.fixture["demand_path"]),
                "--graph-path", str(self.fixture["graph_path"]),
            ]
        )
        self.assertEqual(code, 1)
        self.assertFalse((self.output / "bad-seed").exists())

    def test_cli_passes_every_axis_to_the_worker(self) -> None:
        captured = {}

        def fake_launch(spec, environment, *, cwd):
            captured["spec"] = spec
            captured["environment"] = environment
            captured["cwd"] = cwd
            return 0

        with mock.patch.object(gvs_cli, "_launch_worker", side_effect=fake_launch):
            code = gvs_cli.main(
                [
                    "run", "--data-name", "region", "--method", "shuffled",
                    "--model-seed", "2", "--shuffle-seed", "1",
                    "--purpose", "development", "--run-id", "axis-check",
                    "--output-root", str(self.output),
                    "--demand-path", str(self.fixture["demand_path"]),
                    "--graph-path", str(self.fixture["graph_path"]),
                ]
            )
        self.assertEqual(code, 0)
        spec = captured["spec"]["config"]
        self.assertEqual(spec["data_name"], "region")
        self.assertEqual(spec["method"], "shuffled")
        self.assertEqual(spec["model_seed"], 2)
        self.assertEqual(spec["shuffle_seed"], 1)
        self.assertEqual(spec["purpose"], "development")
        self.assertEqual(spec["run_id"], "axis-check")
        self.assertEqual(Path(spec["output_root"]).resolve(), self.output.resolve())
        self.assertEqual(
            Path(spec["demand_path"]).resolve(), self.fixture["demand_path"].resolve()
        )
        for variable in gvs_cli.BLAS_VARIABLES:
            self.assertEqual(captured["environment"][variable], "1")

    def test_worker_spec_round_trips_through_launch(self) -> None:
        seen = {}

        class FakeProcess:
            def poll(self):
                return None

            def wait(self):
                return 0

            def send_signal(self, signum):  # pragma: no cover - not used
                seen["signal"] = signum

        def fake_popen(argv, cwd=None, env=None):
            spec_path = Path(argv[-1])
            seen["spec"] = json.loads(spec_path.read_text(encoding="utf-8"))
            seen["argv"] = argv
            return FakeProcess()

        with mock.patch("subprocess.Popen", side_effect=fake_popen):
            code = gvs_cli._launch_worker(
                {"config": {"run_id": "x"}}, {"OMP_NUM_THREADS": "1"}, cwd=self.root
            )
        self.assertEqual(code, 0)
        self.assertEqual(seen["spec"], {"config": {"run_id": "x"}})
        self.assertEqual(seen["argv"][1:3], ["-m", gvs_cli.WORKER_MODULE])


if __name__ == "__main__":
    unittest.main()
