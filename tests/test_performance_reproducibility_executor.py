#!/usr/bin/env python3
"""Synthetic regression tests for the Cycle 9 transactional executor."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_DIR / "scripts" / "run_performance_reproducibility.py"


def load_executor():
    spec = importlib.util.spec_from_file_location(
        "cycle9_executor_under_test",
        SCRIPT_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EXECUTOR = load_executor()


def valid_content(run):
    events = []
    hits = []
    for event in range(run.events):
        energy = float(event + 1) / 10.0
        events.append({
            "run": 0,
            "event": event,
            "bcid": event,
            "n_interactions_requested": 1,
            "n_interactions_generated": 1,
            "generation_failures": 0,
            "unknown_pdg_particles": 0,
            "unlineaged_steps": 0,
            "segmentation_failures": 0,
            "total_edep_mev": energy,
        })
        hits.append({
            "run": 0,
            "event": event,
            "bcid": event,
            "subevent": 0,
            "edep_mev": energy,
        })
    return {
        "rows": {
            "events": events,
            "hits": hits,
            "generator": [],
            "metadata": [{
                "events": run.events,
                "first_bcid": 0,
                "threads": run.threads,
                "seed_base": 9512,
                "transport_neutrinos": 0,
                "generator_audit": 0,
                "check_overlaps": 0,
                "mean_interactions": 1.0,
            }],
        },
        "scientific_digest": "1" * 64,
        "metadata_digest": "2" * 64,
        "tree_digests": {
            "events": "3" * 64,
            "hits": "4" * 64,
            "generator": "5" * 64,
            "metadata": "6" * 64,
        },
    }


def comparison(equal, metadata_equal=True):
    def tree(tree_equal):
        return {
            "equal": tree_equal,
            "left_entries": 100,
            "right_entries": 100,
            "only_left_keys": 0,
            "only_right_keys": 0,
            "differing_rows": 0 if tree_equal else 1,
            "differing_values": 0 if tree_equal else 1,
            "differing_fields": {} if tree_equal else {"total_edep_mev": 1},
            "max_abs_difference": 0.0 if tree_equal else 0.25,
            "max_abs_field": None if tree_equal else "total_edep_mev",
            "max_rel_difference": 0.0 if tree_equal else 0.01,
            "max_rel_field": None if tree_equal else "total_edep_mev",
            "digest_equal": tree_equal,
            "left_digest": "a" * 64,
            "right_digest": ("a" if tree_equal else "b") * 64,
        }
    return {
        "raw_sha256_equal": False,
        "scientific_equal": equal,
        "metadata_equal": metadata_equal,
        "canonical_equal": equal and metadata_equal,
        "scientific_digest_equal": equal,
        "metadata_digest_equal": metadata_equal,
        "left_scientific_digest": "1" * 64,
        "right_scientific_digest": ("1" if equal else "2") * 64,
        "left_metadata_digest": "3" * 64,
        "right_metadata_digest": ("3" if metadata_equal else "4") * 64,
        "trees": {
            "events": tree(equal),
            "hits": tree(equal),
            "generator": tree(equal),
            "metadata": tree(metadata_equal),
        },
    }


class PerformanceReproducibilityExecutorTest(unittest.TestCase):
    def test_fixed_matrix_and_arguments(self):
        self.assertEqual(len(EXECUTOR.RUNS), 10)
        self.assertEqual(len(EXECUTOR.REPRO_RUNS), 4)
        self.assertEqual(len(EXECUTOR.PERF_RUNS), 6)
        self.assertEqual(EXECUTOR.SEED_BASE, 9512)
        self.assertEqual(
            [run.name for run in EXECUTOR.PERF_RUNS],
            [
                "perf-t1-r1",
                "perf-t2-r1",
                "perf-t1-r2",
                "perf-t2-r2",
                "perf-t1-r3",
                "perf-t2-r3",
            ],
        )
        for run in EXECUTOR.RUNS:
            root = Path("/tmp") / f"{run.name}.root"
            args = EXECUTOR.simulator_arguments(run, root, dry_run=True)
            self.assertEqual(args[-1], "--dry-run")
            options = dict(zip(args[1:-1:2], args[2:-1:2]))
            self.assertEqual(options["--events"], str(run.events))
            self.assertEqual(options["--threads"], str(run.threads))
            self.assertEqual(options["--seed"], "9512")

    def test_execution_mode_is_explicit(self):
        for argv in ([], ["--dry-run", "--execute-production"]):
            with self.assertRaises(EXECUTOR.CampaignError):
                EXECUTOR.validate_execution_mode(EXECUTOR.parse_args(argv))
        EXECUTOR.validate_execution_mode(EXECUTOR.parse_args(["--dry-run"]))
        EXECUTOR.validate_execution_mode(
            EXECUTOR.parse_args(["--execute-production"])
        )

    def test_resource_log_parser(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "resource.txt"
            path.write_text(
                "User time (seconds): 149.33\n"
                "System time (seconds): 0.19\n"
                "Elapsed (wall clock) time (h:mm:ss or m:ss): 2:29.24\n"
                "Maximum resident set size (kbytes): 164852\n"
                "Exit status: 0\n",
                encoding="utf-8",
            )
            values = EXECUTOR.parse_resource_log(path)
        self.assertAlmostEqual(values["wall_seconds"], 149.24)
        self.assertEqual(values["max_rss_kbytes"], 164852)
        self.assertEqual(values["exit_status"], 0)

    def test_root_validation_and_accounting_gate(self):
        run = EXECUTOR.REPRO_RUNS[0]
        result = EXECUTOR.validate_root_content(run, valid_content(run))
        self.assertTrue(all(value == "PASS" for value in result["gates"].values()))
        self.assertEqual(result["tree_entries"]["events"], 100)

        broken = valid_content(run)
        broken["rows"]["events"][0]["n_interactions_requested"] = 2
        with self.assertRaisesRegex(EXECUTOR.CampaignError, "accounting"):
            EXECUTOR.validate_root_content(run, broken)

    def test_performance_summary_uses_median_and_speedup(self):
        walls = {
            "perf-t1-r1": 10.0,
            "perf-t2-r1": 6.0,
            "perf-t1-r2": 12.0,
            "perf-t2-r2": 5.0,
            "perf-t1-r3": 11.0,
            "perf-t2-r3": 7.0,
        }
        artifacts = {}
        for run in EXECUTOR.PERF_RUNS:
            wall = walls[run.name]
            artifacts[run.name] = {
                "computational_validation": "PASS",
                "wall_seconds": wall,
                "user_seconds": wall * run.threads,
                "system_seconds": 0.1,
                "max_rss_kbytes": 100000,
                "root_size_bytes": 1000,
                "exit_status": 0,
                "root_sha256": "a" * 64,
            }
        result = EXECUTOR.performance_summary(artifacts)
        self.assertEqual(result["threads"]["1"]["median_wall_seconds"], 11.0)
        self.assertEqual(result["threads"]["2"]["median_wall_seconds"], 6.0)
        self.assertAlmostEqual(result["speedup_2t"], 11.0 / 6.0)
        self.assertAlmostEqual(result["parallel_efficiency_2t"], 11.0 / 12.0)
        self.assertIsNone(result["speedup_acceptance_threshold"])

    def test_one_thread_repeatability_is_strict(self):
        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary)
            with mock.patch.object(
                EXECUTOR.ANALYZER,
                "compare_root_files",
                return_value=comparison(False, True),
            ):
                with self.assertRaisesRegex(
                    EXECUTOR.CampaignError,
                    "one-thread repeatability failed",
                ):
                    EXECUTOR.reproducibility_report(staging)

    def test_two_thread_difference_is_reported(self):
        def fake_compare(left, right):
            names = (Path(left).parent.name, Path(right).parent.name)
            if names == ("repro-t1-r1", "repro-t1-r2"):
                return comparison(True, True)
            if names == ("repro-t2-r1", "repro-t2-r2"):
                return comparison(False, True)
            return comparison(False, False)

        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(
                EXECUTOR.ANALYZER,
                "compare_root_files",
                side_effect=fake_compare,
            ):
                result = EXECUTOR.reproducibility_report(Path(temporary))
        self.assertEqual(
            result["two_thread_repeatability"]["classification"],
            "MEASURED_DIFFERENCE_REQUIRES_DOCUMENTATION",
        )
        self.assertFalse(result["two_thread_repeatability"]["exact_repeatability"])
        self.assertEqual(
            result["cross_thread"]["repetition_1"]["classification"],
            "MEASURED_DIFFERENCE",
        )

    def test_dry_run_main_never_calls_transport(self):
        calls = []
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "prospective"
            def fake_preflight(run, output_dir):
                calls.append(run.name)
                self.assertFalse(output_dir.exists())
            with (
                mock.patch.object(EXECUTOR, "require_project_layout"),
                mock.patch.object(EXECUTOR, "build_project"),
                mock.patch.object(EXECUTOR, "run_contract_preflight"),
                mock.patch.object(EXECUTOR, "preflight_run", side_effect=fake_preflight),
                mock.patch.object(EXECUTOR, "execute_production") as production,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                rc = EXECUTOR.main([
                    "--dry-run",
                    "--output-dir",
                    str(output),
                    "--build-jobs",
                    "2",
                ])
            production.assert_not_called()
            self.assertFalse(output.exists())
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [run.name for run in EXECUTOR.RUNS])

    def test_full_transaction_is_sequential_and_atomic(self):
        order = []
        def fake_execute(run, staging):
            order.append(run.name)
            directory = EXECUTOR.run_directory(staging, run)
            directory.mkdir(parents=True)
            root = EXECUTOR.run_root_path(staging, run)
            root.write_bytes(("ROOT-" + run.name).encode())
            return {
                "root_file": root,
                "root_size_bytes": root.stat().st_size,
                "root_sha256": EXECUTOR.sha256_file(root),
                "wall_seconds": 1.0 + run.threads,
                "user_seconds": 1.0,
                "system_seconds": 0.1,
                "max_rss_kbytes": 100000,
                "exit_status": 0,
            }
        def fake_validation(run, root_file):
            return {
                "gates": {"readable_non_zombie_root": "PASS"},
                "metadata": {"events": run.events, "threads": run.threads},
                "tree_entries": {
                    "events": run.events,
                    "hits": 0,
                    "generator": 0,
                    "metadata": 1,
                },
                "scientific_digest": "1" * 64,
                "metadata_digest": "2" * 64,
                "tree_digests": {
                    "events": "3" * 64,
                    "hits": "4" * 64,
                    "generator": "5" * 64,
                    "metadata": "6" * 64,
                },
                "total_event_energy_mev": 0.0,
                "total_hit_energy_mev": 0.0,
                "max_energy_closure_abs_mev": 0.0,
                "max_energy_closure_rel": 0.0,
            }
        def fake_analysis(staging, artifacts):
            analysis = staging / "analysis"
            analysis.mkdir()
            repro = analysis / "reproducibility.json"
            perf = analysis / "performance-summary.json"
            repro.write_text("{}\n", encoding="utf-8")
            perf.write_text("{}\n", encoding="utf-8")
            return repro, perf
        provenance = {
            "commit": "a" * 40,
            "branch": "cycle-9-performance-reproducibility",
            "describe": "synthetic",
        }
        with tempfile.TemporaryDirectory() as temporary:
            final = Path(temporary) / "cycle9"
            with (
                mock.patch.object(EXECUTOR, "execute_single_run", side_effect=fake_execute),
                mock.patch.object(EXECUTOR, "validate_root_artifact", side_effect=fake_validation),
                mock.patch.object(EXECUTOR, "write_campaign_analysis", side_effect=fake_analysis),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                EXECUTOR.execute_production(final, provenance)
            self.assertTrue((final / "campaign-manifest.json").is_file())
            payload = json.loads(
                (final / "campaign-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["transaction"]["run_count"], 10)
            self.assertEqual(payload["transaction"]["parallel_simulator_processes"], 1)
            self.assertTrue(payload["transaction"]["sequential_execution"])
            self.assertFalse(list(Path(temporary).glob(".cycle9.staging-*")))
        self.assertEqual(order, [run.name for run in EXECUTOR.RUNS])

    def test_full_transaction_rolls_back_on_run_failure(self):
        counter = {"value": 0}
        def failing_execute(run, staging):
            counter["value"] += 1
            directory = EXECUTOR.run_directory(staging, run)
            directory.mkdir(parents=True)
            if counter["value"] == 3:
                raise EXECUTOR.CampaignError("synthetic third-run failure")
            root = EXECUTOR.run_root_path(staging, run)
            root.write_bytes(b"SYNTHETIC")
            return {
                "root_file": root,
                "root_size_bytes": root.stat().st_size,
                "root_sha256": "a" * 64,
                "wall_seconds": 1.0,
                "user_seconds": 1.0,
                "system_seconds": 0.0,
                "max_rss_kbytes": 1000,
                "exit_status": 0,
            }
        def fake_validation(run, root_file):
            return {
                "gates": {"readable_non_zombie_root": "PASS"},
                "metadata": {},
                "tree_entries": {"events": run.events, "hits": 0, "generator": 0, "metadata": 1},
                "scientific_digest": "1" * 64,
                "metadata_digest": "2" * 64,
                "tree_digests": {"events": "3" * 64, "hits": "4" * 64, "generator": "5" * 64, "metadata": "6" * 64},
                "total_event_energy_mev": 0.0,
                "total_hit_energy_mev": 0.0,
                "max_energy_closure_abs_mev": 0.0,
                "max_energy_closure_rel": 0.0,
            }
        def fake_manifest(run, staging, artifact, validation):
            path = EXECUTOR.run_directory(staging, run) / "run-manifest.json"
            path.write_text("{}\n", encoding="utf-8")
            return path
        provenance = {
            "commit": "a" * 40,
            "branch": "cycle-9-performance-reproducibility",
            "describe": "synthetic",
        }
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            final = parent / "cycle9"
            with (
                mock.patch.object(EXECUTOR, "execute_single_run", side_effect=failing_execute),
                mock.patch.object(EXECUTOR, "validate_root_artifact", side_effect=fake_validation),
                mock.patch.object(EXECUTOR, "write_run_manifest", side_effect=fake_manifest),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                with self.assertRaisesRegex(
                    EXECUTOR.CampaignError,
                    "third-run failure",
                ):
                    EXECUTOR.execute_production(final, provenance)
            self.assertFalse(final.exists())
            self.assertFalse(list(parent.glob(".cycle9.staging-*")))
        self.assertEqual(counter["value"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
