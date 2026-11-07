"""CLI help without ML imports, path safety and fixture build/check examples."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from benchmark.occupation_skill_graph import paths, protocol
from benchmark.occupation_skill_graph.tests import fixtures as fx

REPO_ROOT = Path(__file__).resolve().parents[3]


def _run(argv, *, cwd=REPO_ROOT):
    return subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


class HelpImportTests(unittest.TestCase):
    def test_help_does_not_import_numerical_packages(self) -> None:
        script = (
            "import sys\n"
            "from benchmark.occupation_skill_graph.cli import main\n"
            "try:\n"
            "    main(['--help'])\n"
            "except SystemExit:\n"
            "    pass\n"
            "print('numpy' in sys.modules, 'pandas' in sys.modules, "
            "'torch' in sys.modules, 'pyarrow' in sys.modules)\n"
        )
        result = _run([sys.executable, "-c", script])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip().splitlines()[-1], "False False False False")

    def test_cli_help_lists_build_and_check(self) -> None:
        result = _run(
            [sys.executable, "-m", "benchmark.occupation_skill_graph", "--help"]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("build", result.stdout)
        self.assertIn("check", result.stdout)


class PathSafetyTests(unittest.TestCase):
    def test_checkout_under_temporary_root_rejects_source_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "checkout"
            repo.mkdir()
            with self.assertRaises(paths.PathError):
                paths.resolve_output_root(
                    purpose="development",
                    output_root=repo / "benchmark",
                    repo_root=repo,
                )
            allowed = paths.resolve_output_root(
                purpose="development",
                output_root=repo / "scratch" / "ok",
                repo_root=repo,
            )
            self.assertEqual(
                allowed, (repo / "scratch" / "ok").resolve()
            )
            outside = paths.resolve_output_root(
                purpose="development",
                output_root=Path(temporary) / "outside",
                repo_root=repo,
            )
            self.assertEqual(outside, (Path(temporary) / "outside").resolve())

    def test_research_output_override_is_refused(self) -> None:
        with self.assertRaises(paths.PathError):
            paths.resolve_output_root(
                purpose="research",
                output_root=Path("/tmp/override"),
                repo_root=REPO_ROOT,
            )
        self.assertEqual(
            paths.resolve_output_root(
                purpose="research", output_root=None, repo_root=REPO_ROOT
            ),
            (REPO_ROOT / "research" / "runs").resolve(),
        )


class FixtureCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.fixture = fx.standard_fixture(self.root / "data")
        self.output = self.root / "output"
        self.build_command = [
            sys.executable,
            "-m",
            "benchmark.occupation_skill_graph",
            "build",
            "--purpose",
            "development",
            "--output-root",
            str(self.output),
            "--run-id",
            "cli-1",
            "--fixture",
            "--demand-path",
            str(self.fixture["source_path"]),
        ]
        for name, path in self.fixture["target_paths"].items():
            self.build_command.extend(["--target-path", f"{name}={path}"])

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_fixture_build_and_check(self) -> None:
        result = _run(self.build_command)
        self.assertEqual(result.returncode, 0, result.stderr)
        run_dir = self.output / "cli-1"
        self.assertTrue((run_dir / "report.json").is_file())
        report = json.loads((run_dir / "report.json").read_text())
        self.assertEqual(report["status"], "succeeded")
        check_report = self.root / "check.json"
        check = _run(
            [
                sys.executable,
                "-m",
                "benchmark.occupation_skill_graph",
                "check",
                "--artifact-dir",
                str(run_dir),
                "--report",
                str(check_report),
            ]
        )
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertEqual(json.loads(check_report.read_text())["status"], "ok")

    def test_collision_and_forbidden_outputs(self) -> None:
        first = _run(self.build_command)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = _run(self.build_command)
        self.assertNotEqual(second.returncode, 0)
        forbidden = list(self.build_command)
        index = forbidden.index(str(self.output))
        forbidden[index] = str(REPO_ROOT / "research" / "runs")
        result = _run(forbidden)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            json.loads((self.output / "cli-1" / "report.json").read_text())["status"],
            "succeeded",
        )


    def test_invalid_purpose_and_unsafe_outputs(self) -> None:
        invalid = list(self.build_command)
        purpose_index = invalid.index("--purpose")
        invalid[purpose_index + 1] = "not-a-purpose"
        result = _run(invalid)
        self.assertNotEqual(result.returncode, 0)

        traversal = list(self.build_command)
        output_index = traversal.index("--output-root")
        traversal[output_index + 1] = str(
            REPO_ROOT / "scratch" / ".." / "research" / "runs"
        )
        result = _run(traversal)
        self.assertNotEqual(result.returncode, 0)

        link = self.root / "research-link"
        link.symlink_to(REPO_ROOT / "research", target_is_directory=True)
        linked = list(self.build_command)
        linked[output_index + 1] = str(link / "runs")
        result = _run(linked)
        self.assertNotEqual(result.returncode, 0)

    def test_fixture_mode_requires_all_targets(self) -> None:
        command = list(self.build_command)
        while "--target-path" in command:
            target_index = command.index("--target-path")
            del command[target_index : target_index + 2]
        result = _run(command)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target-path", result.stderr)

    def test_research_purpose_refuses_fixture_and_override(self) -> None:
        command = list(self.build_command)
        purpose_index = command.index("--purpose")
        command[purpose_index + 1] = "research"
        result = _run(command)
        self.assertNotEqual(result.returncode, 0)
        command = list(self.build_command)
        purpose_index = command.index("--purpose")
        command[purpose_index + 1] = "research"
        command.extend(["--output-root", str(self.root / "override")])
        result = _run(command)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
