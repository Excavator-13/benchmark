"""The new entry leaves the old no-graph and published-graph interfaces intact."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _run(argv):
    return subprocess.run(
        argv, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False
    )


class CompatibilityTests(unittest.TestCase):
    def test_old_help_surfaces_remain_available(self) -> None:
        for module in (
            "benchmark.nograph_baseline",
            "benchmark.graph_value_skeleton",
        ):
            result = _run([sys.executable, "-m", module, "--help"])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("usage", result.stdout.lower())

    def test_old_packages_are_unmodified_in_git(self) -> None:
        result = _run(
            [
                "git",
                "diff",
                "--name-only",
                "--",
                "benchmark/nograph_baseline",
                "benchmark/graph_value_skeleton",
                "benchmark/graph_method",
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_old_modules_import_without_new_package(self) -> None:
        result = _run(
            [
                sys.executable,
                "-c",
                "import benchmark.nograph_baseline as nb; "
                "import benchmark.graph_value_skeleton as gvs; "
                "print(nb.PROTOCOL_VERSION, gvs.SCIENTIFIC_PROTOCOL_VERSION)",
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("P1-count-L6-H3-v3", result.stdout)


if __name__ == "__main__":
    unittest.main()
