"""End-to-end development fixtures and same-seed repeat evidence.

Covers tasks 7.1, 7.2 and 7.4's fixture evidence: the complete 200-epoch CPU path
for r0/region/r2 x self/graph/shuffled (all three shuffle seeds), at least one
public CLI -> isolated worker execution per method, saved-only recompute and
same-seed repeat comparison, the three-member shuffled summary, and proof that
no research run or scientific claim is produced.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from benchmark.graph_value_skeleton import checks as gvs_checks
from benchmark.graph_value_skeleton import cli as gvs_cli
from benchmark.graph_value_skeleton import graph as gvs_graph
from benchmark.graph_value_skeleton import protocol
from benchmark.graph_value_skeleton import runner
from benchmark.graph_value_skeleton.tests import fixtures
from benchmark.nograph_baseline import protocol as p01
from benchmark.nograph_baseline.data import sha256_file


class EndToEndMatrixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(tempfile.mkdtemp(prefix="gvs-e2e-"))
        cls.research_before = cls._research_snapshot()
        cls.runs = {}
        cls.fixtures = {}
        for data_name in fixtures.SCHEMAS:
            fixture_root = cls.root / "fixtures" / data_name
            fixture = fixtures.build_fixture(fixture_root, data_name)
            cls.fixtures[data_name] = fixture
            for method in ("self", "graph"):
                cls.runs[(data_name, method, None)] = cls._execute(
                    fixture, method, run_id=f"{data_name}-{method}-s0"
                )
            for seed in protocol.SHUFFLE_SEEDS:
                cls.runs[(data_name, "shuffled", seed)] = cls._execute(
                    fixture,
                    "shuffled",
                    run_id=f"{data_name}-shuffled{seed}-s0",
                    shuffle_seed=seed,
                )
        # One fresh same-seed repeat per method (task 7.2).
        cls.repeats = {}
        for method in ("self", "graph", "shuffled"):
            fixture = cls.fixtures["r0"]
            cls.repeats[method] = cls._execute(
                fixture,
                method,
                run_id=f"repeat-{method}",
                shuffle_seed=0 if method == "shuffled" else None,
            )

    @classmethod
    def _research_snapshot(cls) -> dict:
        runs = protocol.REPO_ROOT / "research" / "runs"
        state = protocol.REPO_ROOT / "research" / "state.md"
        return {
            "runs": sorted(path.name for path in runs.iterdir()) if runs.exists() else [],
            "state_sha256": sha256_file(state) if state.exists() else None,
        }

    @classmethod
    def _execute(cls, fixture, method, *, run_id, shuffle_seed=None):
        config = fixtures.make_config(
            cls.root,
            fixture,
            method=method,
            shuffle_seed=shuffle_seed,
            run_id=run_id,
            model_seed=0,
        )
        result = runner.execute_run(config)
        return Path(result["run_dir"])

    # -- matrix ----------------------------------------------------------
    def test_every_schema_method_seed_completes(self) -> None:
        self.assertEqual(
            len(self.runs), len(fixtures.SCHEMAS) * (1 + 1 + 3)
        )
        for (data_name, method, seed), run_dir in self.runs.items():
            with self.subTest(dataset=data_name, method=method, shuffle_seed=seed):
                status = fixtures.read_json(run_dir / "status.json")
                self.assertEqual(status["state"], "success")
                self.assertEqual(status["method"], method)
                self.assertEqual(status["shuffle_seed"], seed)
                history = fixtures.read_json(run_dir / "training-history.json")
                self.assertEqual(len(history["rows"]), 200)
                self.assertIn(history["selected_epoch"], range(1, 201))
                selection = fixtures.read_json(run_dir / "selection.json")
                self.assertEqual(
                    selection["parameter_counts_measured"]["total"], 3459
                )
                provenance = fixtures.read_json(run_dir / "provenance.json")
                self.assertEqual(provenance["task"], protocol.TASK_ID)
                self.assertEqual(provenance["purpose"], "development")
                self.assertFalse(provenance["scientific_acceptance"])
                metrics = fixtures.read_json(run_dir / "metrics.json")
                for split in ("validation", "test"):
                    self.assertIn(
                        method, metrics["methods"][split]
                    )
                    for naive in protocol.NAIVE_METHODS:
                        self.assertIn(naive, metrics["methods"][split])
                measurements = fixtures.read_json(run_dir / "measurements.json")
                self.assertEqual(measurements["input"]["epochs"], 200)
                self.assertEqual(measurements["device"], "cpu")
                self.assertIsNotNone(measurements["peak_memory"]["bytes"])
                # Identity and masks do not depend on the method or shuffle seed.
                audit = fixtures.read_json(run_dir / "audit.json")
                self.assertFalse(
                    audit["masks"]["recomputed_from_shuffled_adjacency"]
                )

    def test_masks_and_identity_shared_across_methods(self) -> None:
        for data_name in fixtures.SCHEMAS:
            mask_hashes = set()
            node_hashes = set()
            for (schema, method, seed), run_dir in self.runs.items():
                if schema != data_name:
                    continue
                audit = fixtures.read_json(run_dir / "audit.json")
                mask_hashes.add(json.dumps(audit["masks"]["array_sha256"], sort_keys=True))
                node_hashes.add(audit["identity"]["node_keys_sha256"])
            self.assertEqual(len(node_hashes), 1)
            self.assertEqual(len(mask_hashes), 1)
            self.assertEqual(
                len([key for key in self.runs if key[0] == data_name]), 5
            )

    def test_shuffled_members_are_distinct_and_summarized(self) -> None:
        report_root = self.root / "reports"
        report_root.mkdir(parents=True, exist_ok=True)
        for data_name in fixtures.SCHEMAS:
            members = [
                self.runs[(data_name, "shuffled", seed)]
                for seed in protocol.SHUFFLE_SEEDS
            ]
            graph_hashes = set()
            for seed, run_dir in zip(protocol.SHUFFLE_SEEDS, members):
                provenance = fixtures.read_json(run_dir / "provenance.json")
                graph_hashes.add(
                    provenance["graph_used"]["shuffle_identity"]["edges_sha256"]
                )
                self.assertEqual(
                    provenance["graph_used"]["shuffle_identity"]["shuffle_seed"],
                    seed,
                )
            self.assertEqual(len(graph_hashes), 3)
            report = report_root / f"summary-{data_name}.json"
            result = gvs_checks.command_summarize_shuffled(
                run_dirs=members,
                repo_root=protocol.REPO_ROOT,
                command=["test", "summarize-shuffled"],
                report_path=report,
            )
            self.assertEqual(result["status"], "ok", result["envelope"]["errors"])
            payload = json.loads(report.read_text(encoding="utf-8"))["result"]
            individual = payload["individual_test_MAEs"]
            self.assertAlmostEqual(
                payload["control_test_MAE"],
                float(np.mean([individual["0"], individual["1"], individual["2"]])),
                places=12,
            )
            self.assertEqual(len(payload["members"]), 3)

    def test_each_method_recomputes_and_repeats(self) -> None:
        report_root = self.root / "reports"
        report_root.mkdir(parents=True, exist_ok=True)
        for method in ("self", "graph", "shuffled"):
            original = self.runs[("r0", method, 0 if method == "shuffled" else None)]
            repeat = self.repeats[method]
            with self.subTest(method=method):
                recompute = gvs_checks.command_recompute(
                    run_dir=original,
                    repo_root=protocol.REPO_ROOT,
                    command=["test", "recompute"],
                    report_path=report_root / f"recompute-{method}.json",
                )
                self.assertEqual(
                    recompute["status"], "ok", recompute["envelope"]["errors"]
                )
                compare = gvs_checks.command_compare(
                    run_a=original,
                    run_b=repeat,
                    repo_root=protocol.REPO_ROOT,
                    command=["test", "compare"],
                    report_path=report_root / f"compare-{method}.json",
                )
                self.assertEqual(
                    compare["status"], "ok", compare["envelope"]["errors"]
                )
                payload = compare["report"]
                for split in ("validation", "test"):
                    self.assertLessEqual(
                        payload["predictions"][split]["MAE_normalized_difference"],
                        1e-6,
                    )
                    self.assertLessEqual(
                        payload["predictions"][split]["max_normalized_difference"],
                        1e-6,
                    )
                self.assertEqual(payload["condition_identity"]["differences"], [])

    def test_public_cli_worker_per_method(self) -> None:
        cli_root = self.root / "cli-runs"
        for method in ("self", "graph", "shuffled"):
            run_id = f"cli-{method}-s0"
            argv = [
                "run",
                "--data-name", "r0",
                "--method", method,
                "--model-seed", "0",
                "--purpose", "development",
                "--run-id", run_id,
                "--output-root", str(cli_root),
                "--demand-path", str(self.fixtures["r0"]["demand_path"]),
                "--graph-path", str(self.fixtures["r0"]["graph_path"]),
            ]
            if method == "shuffled":
                argv.extend(["--shuffle-seed", "1"])
            with self.subTest(method=method):
                code = gvs_cli.main(argv)
                self.assertEqual(code, 0)
                run_dir = cli_root / run_id
                status = fixtures.read_json(run_dir / "status.json")
                self.assertEqual(status["state"], "success")
                self.assertEqual(status["method"], method)
                config = fixtures.read_json(run_dir / "config.json")
                self.assertEqual(config["spec"]["method"], method)
                self.assertEqual(
                    config["spec"]["shuffle_seed"],
                    1 if method == "shuffled" else None,
                )
                environment = fixtures.read_json(run_dir / "environment.json")
                for variable in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS",
                ):
                    self.assertEqual(
                        environment["thread_environment"][variable], "1"
                    )

    def test_shuffled_graph_independent_of_model_seed_and_run_id(self) -> None:
        baseline = self.runs[("r0", "shuffled", 0)]
        fixture = self.fixtures["r0"]
        config = fixtures.make_config(
            self.root,
            fixture,
            method="shuffled",
            shuffle_seed=0,
            model_seed=1,
            run_id="shuffle-model-seed-1",
        )
        other = Path(runner.execute_run(config)["run_dir"])
        first = fixtures.read_json(baseline / "provenance.json")["graph_used"]
        second = fixtures.read_json(other / "provenance.json")["graph_used"]
        self.assertEqual(
            first["shuffle_identity"]["edges_sha256"],
            second["shuffle_identity"]["edges_sha256"],
        )
        self.assertEqual(
            first["shuffle_identity"]["source_edges_sha256"],
            second["shuffle_identity"]["source_edges_sha256"],
        )
        self.assertNotEqual(
            fixtures.read_json(baseline / "provenance.json")["model_seed"],
            fixtures.read_json(other / "provenance.json")["model_seed"],
        )
        self.assertNotEqual(
            fixtures.read_json(baseline / "provenance.json")["run_id"],
            fixtures.read_json(other / "provenance.json")["run_id"],
        )

    def test_no_research_records_or_benefit_claims(self) -> None:
        self.assertEqual(self._research_snapshot(), self.research_before)
        for run_dir in self.runs.values():
            summary = (run_dir / "summary.md").read_text(encoding="utf-8")
            self.assertIn("implementation evidence only", summary)
            metrics = fixtures.read_json(run_dir / "metrics.json")
            self.assertFalse(metrics["evidence_role"].startswith("formal"))
            serialized = json.dumps(metrics).lower()
            for forbidden in (
                "predictive benefit established",
                "scientifically accepted",
                "outperforms the baseline",
            ):
                self.assertNotIn(forbidden, serialized)
        # The fixture matrix never creates a formal run directory.
        for run_dir in self.runs.values():
            config = fixtures.read_json(run_dir / "config.json")
            self.assertEqual(config["spec"]["purpose"], "development")
            self.assertFalse(
                str(run_dir).startswith(str(protocol.REPO_ROOT / "research" / "runs"))
            )


if __name__ == "__main__":
    unittest.main()
