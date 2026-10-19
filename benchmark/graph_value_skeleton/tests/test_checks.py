"""Saved-only recomputation, repeat comparison, shuffle summary and reports.

Covers tasks 4.3 (saved-control summary), 6.4, 6.5 and 6.6.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from benchmark.graph_value_skeleton import checks as gvs_checks
from benchmark.graph_value_skeleton import cli as gvs_cli
from benchmark.graph_value_skeleton import data as gvs_data
from benchmark.graph_value_skeleton import graph as gvs_graph
from benchmark.graph_value_skeleton import model as gvs_model
from benchmark.graph_value_skeleton import protocol
from benchmark.graph_value_skeleton import runner
from benchmark.graph_value_skeleton import training
from benchmark.graph_value_skeleton.tests import fixtures
from benchmark.nograph_baseline.data import sha256_file


def copy_run(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    return destination


def tree_hashes(root: Path) -> dict:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class ChecksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(tempfile.mkdtemp(prefix="gvs-checks-"))
        cls.fixture = fixtures.build_fixture(cls.root, "r0")

        def run(run_id, **overrides):
            config = fixtures.make_config(
                cls.root, cls.fixture, run_id=run_id, **overrides
            )
            return Path(runner.execute_run(config)["run_dir"])

        cls.run_a = run("graph-a", method="graph")
        cls.run_b = run("graph-b", method="graph")
        cls.run_other_seed = run("graph-seed1", method="graph", model_seed=1)
        cls.shuffled = {
            seed: run(f"shuffled-{seed}", method="shuffled", shuffle_seed=seed)
            for seed in protocol.SHUFFLE_SEEDS
        }

    # -- helpers ---------------------------------------------------------
    def _report(self, name: str) -> Path:
        destination = self.root / "reports" / f"{name}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination

    def _assert_single_report(self, report: Path) -> dict:
        self.assertTrue(report.is_file())
        self.assertEqual(
            [path for path in report.parent.glob("*.json") if path.stat().st_size],
            [path for path in report.parent.glob("*.json")],
        )
        return json.loads(report.read_text(encoding="utf-8"))

    # -- recompute -------------------------------------------------------
    def test_recompute_reads_saved_evidence_only(self) -> None:
        report = self._report("recompute-ok")
        before = tree_hashes(self.run_a)
        with mock.patch.object(
            gvs_data, "load_dataset", side_effect=AssertionError("source read")
        ), mock.patch.object(
            gvs_graph, "load_graph", side_effect=AssertionError("graph read")
        ), mock.patch.object(
            training, "train", side_effect=AssertionError("training called")
        ), mock.patch.object(
            gvs_model, "predict_windows", side_effect=AssertionError("forward called")
        ), mock.patch.object(
            gvs_model.SkeletonModel,
            "forward",
            side_effect=AssertionError("model forward called"),
        ):
            result = gvs_checks.command_recompute(
                run_dir=self.run_a,
                repo_root=protocol.REPO_ROOT,
                command=["test", "recompute"],
                report_path=report,
            )
        self.assertEqual(result["status"], "ok", result["envelope"]["errors"])
        self.assertEqual(before, tree_hashes(self.run_a))
        envelope = self._assert_single_report(report)
        self.assertEqual(envelope["status"], "ok")
        payload = envelope["result"]
        self.assertFalse(payload["source_data_read"])
        self.assertFalse(payload["model_trained"])
        self.assertFalse(payload["model_forward_called"])
        self.assertTrue(payload["inputs_bytewise_unchanged"])
        self.assertEqual(payload["comparisons"]["test"]["status"], "ok")
        self.assertLessEqual(
            payload["comparisons"]["test"]["max_normalized_difference"], 1e-12
        )
        self.assertEqual(payload["relative_gains_comparison"]["status"], "ok")
        self.assertIn("recomputed_methods", payload)
        self.assertIn("graph", payload["recomputed_methods"]["test"])
        self.assertEqual(
            envelope["tolerances"]["numeric"], 1e-12
        )
        self.assertEqual(envelope["kind"], "recompute")
        self.assertEqual(envelope["command"]["argv"], ["test", "recompute"])
        self.assertIn("benchmark/graph_value_skeleton/checks.py", envelope["checker"]["source"]["files"])

    def test_recompute_detects_corrupt_evidence(self) -> None:
        tamper_dir = self.root / "tampered"
        cases = {
            "node-key": lambda directory: _replace_int_column(
                directory / "nodes.parquet", "skill_id", 99
            ),
            "label-shape": lambda directory: np.save(
                directory / "gold/test.npy",
                np.load(directory / "gold/test.npy", allow_pickle=False)[:3],
            ),
            "mask-bit": lambda directory: _flip_mask(directory / "masks.npz"),
            "window-role": lambda directory: _edit_json(
                directory / "windows.json",
                lambda payload: payload["splits"].__setitem__("validation", [20]),
            ),
            "missing-metric": lambda directory: _edit_json(
                directory / "metrics.json",
                lambda payload: payload["methods"]["test"]["graph"].pop("MAE"),
            ),
            "count-null": lambda directory: _edit_json(
                directory / "metrics.json",
                lambda payload: payload["methods"]["test"]["graph"].__setitem__(
                    "elements", 0
                ),
            ),
            "nonfinite": lambda directory: _edit_json(
                directory / "metrics.json",
                lambda payload: payload["methods"]["test"]["graph"].__setitem__(
                    "MAE", float("nan")
                ),
            ),
            "parameter-count": lambda directory: _edit_npz_scalar(
                directory / "models/selected.npz", "parameter_count_total", 1
            ),
            "nan-parameter": lambda directory: _nan_parameter(
                directory / "models/selected.npz"
            ),
            "missing-graph": lambda directory: (
                directory / "graph/edges.npy"
            ).unlink(),
            "missing-source-edges": lambda directory: (
                directory / "graph/source-edges.npy"
            ).unlink(),
            "message-edge-hash": lambda directory: _edit_json(
                directory / "provenance.json",
                lambda payload: payload["graph_used"].__setitem__(
                    "message_edges_sha256", "0" * 64
                ),
            ),
            "graph-edge-content": lambda directory: _rewrite_edge(
                directory / "graph/edges.npy"
            ),
            "validation-count": lambda directory: _edit_json(
                directory / "training-history.json",
                lambda payload: payload["rows"][0].__setitem__(
                    "validation_elements", 0
                ),
            ),
            "missing-audit": lambda directory: (directory / "audit.json").unlink(),
            "missing-graph-audit": lambda directory: (
                directory / "graph-audit.json"
            ).unlink(),
            "fractional-count": lambda directory: _edit_json(
                directory / "training-history.json",
                lambda payload: payload["rows"][0].__setitem__(
                    "validation_elements",
                    float(payload["rows"][0]["validation_elements"]) + 0.5,
                ),
            ),
            "negative-history-score": lambda directory: _edit_json(
                directory / "training-history.json",
                lambda payload: payload["rows"][1].__setitem__(
                    "validation_MAE_original_units_after_update", -5.0
                ),
            ),
            "selected-score-contradiction": _contradict_selected_score,
            "audit-identity-hash": lambda directory: _edit_json(
                directory / "audit.json",
                lambda payload: payload["identity"].__setitem__(
                    "node_keys_sha256", "0" * 64
                ),
            ),
            "graph-audit-message-hash": lambda directory: _edit_json(
                directory / "graph-audit.json",
                lambda payload: payload["message_edges"].__setitem__(
                    "edges_sha256", "0" * 64
                ),
            ),
            "unexpected-shuffle-audit": lambda directory: _edit_json(
                directory / "graph-audit.json",
                lambda payload: payload.__setitem__(
                    "shuffle", {"algorithm": "unexpected"}
                ),
            ),
        }
        for label, tamper in cases.items():
            with self.subTest(case=label):
                destination = copy_run(self.run_a, tamper_dir / label)
                tamper(destination)
                before = tree_hashes(destination)
                report = self._report(f"recompute-{label}")
                result = gvs_checks.command_recompute(
                    run_dir=destination,
                    repo_root=protocol.REPO_ROOT,
                    command=["test", "recompute"],
                    report_path=report,
                )
                self.assertNotEqual(result["status"], "ok", label)
                self.assertEqual(before, tree_hashes(destination), label)
                envelope = json.loads(report.read_text(encoding="utf-8"))
                self.assertNotEqual(envelope["status"], "ok")
                self.assertEqual(envelope["kind"], "recompute")

    def test_recompute_detects_damaged_shuffle_audit(self) -> None:
        for label, mutate in _shuffle_audit_mutations().items():
            with self.subTest(case=label):
                destination = copy_run(
                    self.shuffled[0], self.root / "tampered" / f"shuffle-{label}"
                )
                _edit_json(destination / "graph-audit.json", mutate)
                before = tree_hashes(destination)
                report = self._report(f"recompute-shuffle-{label}")
                result = gvs_checks.command_recompute(
                    run_dir=destination,
                    repo_root=protocol.REPO_ROOT,
                    command=["test", "recompute"],
                    report_path=report,
                )
                self.assertNotEqual(result["status"], "ok", label)
                self.assertEqual(before, tree_hashes(destination), label)

    def test_recompute_cli_exits_nonzero_for_damaged_shuffle_audit(self) -> None:
        for label, mutate in _shuffle_audit_mutations().items():
            with self.subTest(case=label):
                destination = copy_run(
                    self.shuffled[0], self.root / "tampered" / f"cli-{label}"
                )
                _edit_json(destination / "graph-audit.json", mutate)
                report = self._report(f"cli-{label}")
                code = gvs_cli.main(
                    [
                        "recompute",
                        "--run-dir",
                        str(destination),
                        "--report",
                        str(report),
                    ]
                )
                self.assertNotEqual(code, 0, label)
                envelope = json.loads(report.read_text(encoding="utf-8"))
                self.assertNotEqual(envelope["status"], "ok", label)

    def test_valid_shuffled_run_with_empty_context_recomputes(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="gvs-empty-context-"))
        keys = [(0, skill) for skill in range(4)] + [(2, skill) for skill in range(4)]
        signal = (
            np.arange(len(keys) * 36, dtype=np.float32).reshape(len(keys), 36) + 1.0
        )
        rows = [
            (0, source, target)
            for source, target in fixtures.CONTEXT_EDGES["region"]
        ]
        fixture = fixtures.build_fixture(
            root, "r2", keys=keys, signal=signal, graph_rows=rows
        )
        config = fixtures.make_config(
            root, fixture, method="shuffled", shuffle_seed=1, run_id="empty-context"
        )
        run_dir = Path(runner.execute_run(config)["run_dir"])
        audit = fixtures.read_json(run_dir / "graph-audit.json")
        empty = [entry for entry in audit["shuffle"]["contexts"] if entry["empty"]]
        self.assertEqual(len(empty), 1)
        self.assertEqual(empty[0]["context"], [2])
        result = gvs_checks.command_recompute(
            run_dir=run_dir,
            repo_root=protocol.REPO_ROOT,
            command=["test", "recompute"],
            report_path=root / "report.json",
        )
        self.assertEqual(result["status"], "ok", result["envelope"]["errors"])

    def test_recompute_reports_failure_for_missing_artifacts(self) -> None:
        destination = copy_run(self.run_a, self.root / "tampered" / "missing")
        (destination / "metrics.json").unlink()
        report = self._report("recompute-missing")
        result = gvs_checks.command_recompute(
            run_dir=destination,
            repo_root=protocol.REPO_ROOT,
            command=["test", "recompute"],
            report_path=report,
        )
        self.assertEqual(result["status"], "failed")
        envelope = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(envelope["status"], "failed")
        self.assertIn("metrics.json", json.dumps(envelope["errors"]))

    # -- compare ---------------------------------------------------------
    def test_same_seed_repeat_compare_passes(self) -> None:
        report = self._report("compare-ok")
        before = (tree_hashes(self.run_a), tree_hashes(self.run_b))
        result = gvs_checks.command_compare(
            run_a=self.run_a,
            run_b=self.run_b,
            repo_root=protocol.REPO_ROOT,
            command=["test", "compare"],
            report_path=report,
        )
        self.assertEqual(result["status"], "ok", result["envelope"]["errors"])
        self.assertEqual(before, (tree_hashes(self.run_a), tree_hashes(self.run_b)))
        envelope = json.loads(report.read_text(encoding="utf-8"))
        payload = envelope["result"]
        self.assertEqual(payload["condition_identity"]["differences"], [])
        for split in ("validation", "test"):
            self.assertEqual(payload["predictions"][split]["status"], "ok")
            self.assertLessEqual(
                payload["predictions"][split]["MAE_normalized_difference"], 1e-6
            )
            self.assertLessEqual(
                payload["predictions"][split]["max_absolute_difference"], 1e-6
            )
            self.assertTrue(payload["predictions"][split]["gold_labels_equal"])
            self.assertEqual(payload["metric_comparisons"][split]["status"], "ok")
        self.assertEqual(envelope["tolerances"]["MAE_normalized"], 1e-6)

    def test_compare_rejects_numeric_mismatch(self) -> None:
        for label, delta, expected in (
            ("within-tolerance", 5e-7, "ok"),
            ("beyond-tolerance", 1e-4, "mismatch"),
        ):
            with self.subTest(case=label):
                destination = copy_run(self.run_b, self.root / "tampered" / f"compare-{label}")
                path = destination / "predictions/graph/test.npy"
                prediction = np.load(path, allow_pickle=False)
                mask = np.abs(prediction) > 1.0
                prediction[mask] = prediction[mask] + np.float32(delta)
                np.save(path, prediction)
                report = self._report(f"compare-{label}")
                result = gvs_checks.command_compare(
                    run_a=self.run_a,
                    run_b=destination,
                    repo_root=protocol.REPO_ROOT,
                    command=["test", "compare"],
                    report_path=report,
                )
                self.assertEqual(result["status"], expected)
                if expected != "ok":
                    envelope = json.loads(report.read_text(encoding="utf-8"))
                    self.assertIn(
                        "predictions:test", envelope["result"]["failed_checks"]
                    )

    def test_compare_rejects_condition_mismatch_with_identical_predictions(self) -> None:
        destination = copy_run(self.run_b, self.root / "tampered" / "condition")
        _edit_json(
            destination / "provenance.json",
            lambda payload: payload.__setitem__("model_seed", 1),
        )
        _edit_json(
            destination / "config.json",
            lambda payload: payload["spec"].__setitem__("model_seed", 1),
        )
        report = self._report("compare-condition")
        result = gvs_checks.command_compare(
            run_a=self.run_a,
            run_b=destination,
            repo_root=protocol.REPO_ROOT,
            command=["test", "compare"],
            report_path=report,
        )
        self.assertEqual(result["status"], "failed")
        envelope = json.loads(report.read_text(encoding="utf-8"))
        self.assertIn("model seeds differ", json.dumps(envelope["errors"]))
        # Explicit axis differences are rejected before numbers are considered.
        result = gvs_checks.command_compare(
            run_a=self.run_a,
            run_b=self.run_other_seed,
            repo_root=protocol.REPO_ROOT,
            command=["test", "compare"],
            report_path=self._report("compare-axis"),
        )
        self.assertEqual(result["status"], "failed")
        # A condition difference that is not a hard axis check is still a
        # mismatch even though the predictions are byte-identical.
        environment_copy = copy_run(
            self.run_b, self.root / "tampered" / "environment"
        )
        _edit_json(
            environment_copy / "environment.json",
            lambda payload: payload.__setitem__("python_version", "other"),
        )
        report = self._report("compare-environment")
        result = gvs_checks.command_compare(
            run_a=self.run_a,
            run_b=environment_copy,
            repo_root=protocol.REPO_ROOT,
            command=["test", "compare"],
            report_path=report,
        )
        self.assertEqual(result["status"], "mismatch")
        envelope = json.loads(report.read_text(encoding="utf-8"))
        self.assertIn("condition_identity", envelope["result"]["failed_checks"])
        paths = [
            entry["path"]
            for entry in envelope["result"]["condition_identity"]["differences"]
        ]
        self.assertTrue(any("python_version" in path for path in paths), paths)
        for split in ("validation", "test"):
            self.assertEqual(
                envelope["result"]["predictions"][split]["max_absolute_difference"],
                0.0,
            )

    def test_compare_rejects_self_alias_and_copied_execution(self) -> None:
        report = self._report("compare-self")
        result = gvs_checks.command_compare(
            run_a=self.run_a,
            run_b=self.run_a,
            repo_root=protocol.REPO_ROOT,
            command=["test"],
            report_path=report,
        )
        self.assertEqual(result["status"], "failed")
        self.assertIn("same execution", json.dumps(result["envelope"]["errors"]))
        alias = self.root / "alias-run"
        if alias.exists() or alias.is_symlink():
            alias.unlink()
        alias.symlink_to(self.run_a, target_is_directory=True)
        result = gvs_checks.command_compare(
            run_a=self.run_a,
            run_b=alias,
            repo_root=protocol.REPO_ROOT,
            command=["test"],
            report_path=self._report("compare-alias"),
        )
        self.assertEqual(result["status"], "failed")
        copied = copy_run(self.run_a, self.root / "tampered" / "copy-execution")
        result = gvs_checks.command_compare(
            run_a=self.run_a,
            run_b=copied,
            repo_root=protocol.REPO_ROOT,
            command=["test"],
            report_path=self._report("compare-copied"),
        )
        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "same execution identity", json.dumps(result["envelope"]["errors"])
        )

    # -- report destination safety --------------------------------------
    def test_report_destination_is_exclusive_and_scoped(self) -> None:
        existing = self._report("existing")
        existing.write_text("{}", encoding="utf-8")
        with self.assertRaises(gvs_checks.CheckError):
            gvs_checks.command_recompute(
                run_dir=self.run_a,
                repo_root=protocol.REPO_ROOT,
                command=["test"],
                report_path=existing,
            )
        inside = self.run_a / "report.json"
        with self.assertRaises(gvs_checks.CheckError):
            gvs_checks.command_recompute(
                run_dir=self.run_a,
                repo_root=protocol.REPO_ROOT,
                command=["test"],
                report_path=inside,
            )
        research_report = protocol.REPO_ROOT / "research" / "gvs-report.json"
        with self.assertRaises(gvs_checks.CheckError):
            gvs_checks.command_recompute(
                run_dir=self.run_a,
                repo_root=protocol.REPO_ROOT,
                command=["test"],
                report_path=research_report,
            )
        self.assertFalse(research_report.exists())
        # Rebased implementation roots cannot turn research into scratch.
        with self.assertRaises(gvs_checks.CheckError):
            gvs_checks.validate_report_destination(
                protocol.REPO_ROOT / "research",
                protocol.REPO_ROOT / "research" / "scratch" / "rebased.json",
            )
        # A symlink inside scratch pointing at research is rejected.
        scratch = protocol.REPO_ROOT / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        link = scratch / f"gvs-report-link-{__import__('os').getpid()}"
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(protocol.REPO_ROOT / "research", target_is_directory=True)
        try:
            with self.assertRaises(gvs_checks.CheckError):
                gvs_checks.command_recompute(
                    run_dir=self.run_a,
                    repo_root=protocol.REPO_ROOT,
                    command=["test"],
                    report_path=link / "report.json",
                )
        finally:
            link.unlink()

    # -- summarize-shuffled ---------------------------------------------
    def test_summarize_shuffled_averages_three_members(self) -> None:
        report = self._report("summary-ok")
        members = [self.shuffled[seed] for seed in protocol.SHUFFLE_SEEDS]
        result = gvs_checks.command_summarize_shuffled(
            run_dirs=members,
            repo_root=protocol.REPO_ROOT,
            command=["test", "summarize-shuffled"],
            report_path=report,
        )
        self.assertEqual(result["status"], "ok", result["envelope"]["errors"])
        envelope = json.loads(report.read_text(encoding="utf-8"))
        payload = envelope["result"]
        individual = payload["individual_test_MAEs"]
        self.assertEqual(sorted(individual, key=int), ["0", "1", "2"])
        expected = float(np.mean([individual[seed] for seed in ("0", "1", "2")]))
        self.assertAlmostEqual(payload["control_test_MAE"], expected, places=12)
        for seed in ("0", "1", "2"):
            self.assertIn(seed, payload["members"])
            self.assertEqual(payload["members"][seed]["shuffle_seed"], int(seed))
            self.assertEqual(payload["members"][seed]["recompute_status"], "ok")
        self.assertTrue(payload["mae_of_averaged_predictions_is_not_the_control"])
        self.assertFalse(payload["ranking_used"])
        self.assertFalse(payload["weakest_graph_selected"])
        self.assertNotEqual(payload["control_test_MAE"], payload["mae_of_averaged_predictions"])

    def test_summarize_rejects_incomplete_or_mixed_members(self) -> None:
        members = [self.shuffled[seed] for seed in protocol.SHUFFLE_SEEDS]
        # Duplicate seed.
        result = gvs_checks.command_summarize_shuffled(
            run_dirs=[members[0], members[1], members[1]],
            repo_root=protocol.REPO_ROOT,
            command=["test"],
            report_path=self._report("summary-duplicate"),
        )
        self.assertEqual(result["status"], "failed")
        # Missing member directory.
        result = gvs_checks.command_summarize_shuffled(
            run_dirs=[members[0], members[1], self.root / "missing-member"],
            repo_root=protocol.REPO_ROOT,
            command=["test"],
            report_path=self._report("summary-missing"),
        )
        self.assertEqual(result["status"], "failed")
        # Mixed model seed member, predictions untouched.
        mixed = copy_run(members[2], self.root / "tampered" / "mixed-seed")
        _edit_json(
            mixed / "config.json",
            lambda payload: payload["spec"].__setitem__("model_seed", 2),
        )
        _edit_json(
            mixed / "provenance.json",
            lambda payload: payload.__setitem__("model_seed", 2),
        )
        result = gvs_checks.command_summarize_shuffled(
            run_dirs=[members[0], members[1], mixed],
            repo_root=protocol.REPO_ROOT,
            command=["test"],
            report_path=self._report("summary-mixed"),
        )
        self.assertEqual(result["status"], "failed")
        # A non-shuffled member is rejected.
        result = gvs_checks.command_summarize_shuffled(
            run_dirs=[members[0], members[1], self.run_a],
            repo_root=protocol.REPO_ROOT,
            command=["test"],
            report_path=self._report("summary-method"),
        )
        self.assertEqual(result["status"], "failed")

    def test_summarize_rejects_incompatible_graph_identity(self) -> None:
        members = [self.shuffled[seed] for seed in protocol.SHUFFLE_SEEDS]
        destination = copy_run(members[1], self.root / "tampered" / "graph-identity")
        _edit_json(
            destination / "provenance.json",
            lambda payload: payload["graph"].__setitem__(
                "source_path", str(destination / "different-source.parquet")
            ),
        )
        result = gvs_checks.command_summarize_shuffled(
            run_dirs=[members[0], destination, members[2]],
            repo_root=protocol.REPO_ROOT,
            command=["test"],
            report_path=self._report("summary-graph"),
        )
        self.assertEqual(result["status"], "mismatch")


def _edit_json(path: Path, mutate) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _replace_int_column(path: Path, column: str, value: int) -> None:
    import pandas as pd

    frame = pd.read_parquet(path)
    frame[column] = value
    frame.to_parquet(path, index=False)


def _flip_mask(path: Path) -> None:
    with np.load(path, allow_pickle=False) as handle:
        arrays = {name: np.asarray(handle[name]) for name in handle.files}
    mask = arrays["has_nonself_neighbor"].copy()
    mask[0] = ~mask[0]
    arrays["has_nonself_neighbor"] = mask
    np.savez(path, **arrays)


def _coherent_false_overlap(payload: dict) -> None:
    shuffle_audit = payload["shuffle"]
    context = shuffle_audit["contexts"][0]
    edge_count = context["edge_count"]
    context.update(
        changed_edges=1,
        added_edges=1,
        intersection_edges=edge_count - 1,
        symmetric_difference_edges=2,
        changed_fraction=1 / edge_count,
        intersection_fraction=(edge_count - 1) / edge_count,
        symmetric_difference_fraction=1 / edge_count,
    )
    shuffle_audit["changed_edges"] = sum(
        entry["changed_edges"] for entry in shuffle_audit["contexts"]
    )


def _lower_work_budget(payload: dict) -> None:
    shuffle_audit = payload["shuffle"]
    shuffle_audit["accept_target_factor"] = 1
    for context in shuffle_audit["contexts"]:
        context["target_accepted"] = context["edge_count"]
        context["accepted"] = context["edge_count"]
    shuffle_audit["totals"]["accepted"] = sum(
        context["accepted"] for context in shuffle_audit["contexts"]
    )


def _shuffle_audit_mutations():
    return {
        "missing-shuffle": lambda payload: payload.pop("shuffle"),
        "result-hash": lambda payload: payload["shuffle"].__setitem__(
            "result_edges_sha256", "0" * 64
        ),
        "seed": lambda payload: payload["shuffle"].__setitem__("shuffle_seed", 1),
        "unchanged-context": lambda payload: payload["shuffle"]["contexts"][
            0
        ].__setitem__("changed_edges", 0),
        "missing-totals": lambda payload: payload["shuffle"].pop("totals"),
        "missing-context": lambda payload: payload["shuffle"]["contexts"].pop(),
        "duplicate-context": lambda payload: payload["shuffle"]["contexts"].append(
            dict(payload["shuffle"]["contexts"][0])
        ),
        "wrong-context": lambda payload: payload["shuffle"]["contexts"][
            0
        ].__setitem__("context", [999]),
        "negative-swaps": lambda payload: payload["shuffle"]["contexts"][
            0
        ].__setitem__("accepted", -1),
        "negative-attempts": lambda payload: payload["shuffle"]["contexts"][
            0
        ].__setitem__("attempts", -1),
        "target-mismatch": lambda payload: payload["shuffle"]["contexts"][
            0
        ].__setitem__("target_accepted", 0),
        "attempts-exceed": lambda payload: payload["shuffle"]["contexts"][
            0
        ].__setitem__("attempts", 0),
        "missing-context-result-hash": lambda payload: payload["shuffle"][
            "contexts"
        ][0].pop("result_edges_sha256"),
        "wrong-context-source-hash": lambda payload: payload["shuffle"]["contexts"][
            0
        ].__setitem__("source_edges_sha256", "0" * 64),
        "missing-seed-sequence": lambda payload: payload["shuffle"]["contexts"][
            0
        ].pop("seed_sequence"),
        "totals-mismatch": lambda payload: payload["shuffle"]["totals"].__setitem__(
            "accepted", payload["shuffle"]["totals"]["accepted"] + 1
        ),
        "fractional-raw-count": lambda payload: payload.__setitem__(
            "raw_rows", payload["raw_rows"] + 0.5
        ),
        "fractional-message-count": lambda payload: payload["message_edges"].__setitem__(
            "edges", payload["message_edges"]["edges"] + 0.5
        ),
        "negative-changed-fraction": lambda payload: payload["shuffle"]["contexts"][
            0
        ].__setitem__("changed_fraction", -1.0),
        "missing-changed-fraction": lambda payload: payload["shuffle"]["contexts"][
            0
        ].pop("changed_fraction"),
        "coherent-false-overlap": _coherent_false_overlap,
        "missing-rejections": lambda payload: payload["shuffle"]["contexts"][0].pop(
            "rejections"
        ),
        "inconsistent-rejections": lambda payload: payload["shuffle"]["contexts"][
            0
        ].__setitem__(
            "rejections",
            {
                "same_edge_index": payload["shuffle"]["contexts"][0]["attempts"] + 1
            },
        ),
        "lower-work-budget": _lower_work_budget,
        "missing-top-changed": lambda payload: payload["shuffle"].pop("changed_edges"),
    }


def _contradict_selected_score(directory: Path) -> None:
    history_path = directory / "training-history.json"
    history = json.loads(history_path.read_text(encoding="utf-8"))
    epoch = int(history["selected_epoch"])
    history["rows"][epoch - 1][
        "validation_MSE_original_units_after_update"
    ] = -1.0
    history["selected_validation_MSE"] = -1.0
    history_path.write_text(json.dumps(history), encoding="utf-8")
    selection_path = directory / "selection.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    selection["training"]["selected_validation_MSE"] = -1.0
    selection_path.write_text(json.dumps(selection), encoding="utf-8")


def _nan_parameter(path: Path) -> None:
    with np.load(path, allow_pickle=False) as handle:
        arrays = {name: np.asarray(handle[name]).copy() for name in handle.files}
    arrays["head.weight"][0, 0] = np.nan
    np.savez(path, **arrays)


def _rewrite_edge(path: Path) -> None:
    edges = np.load(path, allow_pickle=False)
    edges[0, 1] = (int(edges[0, 1]) + 1) % 7
    np.save(path, edges)


def _edit_npz_scalar(path: Path, key: str, value: int) -> None:
    with np.load(path, allow_pickle=False) as handle:
        arrays = {name: np.asarray(handle[name]) for name in handle.files}
    arrays[key] = np.array([value], dtype=np.int64)
    np.savez(path, **arrays)


if __name__ == "__main__":
    unittest.main()
