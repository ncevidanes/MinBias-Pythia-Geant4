#!/usr/bin/env python3
"""Synthetic tests for the transactional Cycle 8.3 executor."""

from __future__ import annotations

import contextlib
import csv
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_DIR / "scripts" / "run_neutrino_transport_stage83.py"
ANALYZER_PATH = PROJECT_DIR / "scripts" / "analyze_neutrino_transport.C"


def load_executor():
    spec = importlib.util.spec_from_file_location(
        "cycle8_stage83_executor_under_test", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EXECUTOR = load_executor()


class NeutrinoTransportStage83ExecutorTest(unittest.TestCase):
    def write_seed_analysis(
        self,
        staging_dir: Path,
        seed: int,
        *,
        eligible: int,
        outside: int = 1,
    ) -> None:
        analysis_dir = staging_dir / f"seed-{seed}" / "analysis"
        analysis_dir.mkdir(parents=True)
        summary_fields = (
            "events",
            "seed",
            "mean_interactions",
            "eligible_neutrinos",
            "outside_acceptance_neutrinos",
            "off_transported",
            "on_transported",
            "transported_delta",
            "off_total_energy_mev",
            "on_total_energy_mev",
            "energy_delta_mev",
            "energy_abs_delta_mev",
            "energy_relative_delta",
            "off_hit_count",
            "on_hit_count",
            "changed_hit_cells",
            "missing_off_hit_cells",
            "missing_on_hit_cells",
            "hit_energy_l1_mev",
            "max_abs_hit_delta_mev",
            "generator_entries",
            "requested_interactions",
            "generated_interactions",
            "generation_failures",
            "unknown_pdg_particles",
            "unlineaged_steps",
            "segmentation_failures",
        )
        with (analysis_dir / "paired_summary.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=summary_fields)
            writer.writeheader()
            writer.writerow(
                {
                    "events": EXECUTOR.EVENTS_PER_CONDITION,
                    "seed": seed,
                    "mean_interactions": 1.0,
                    "eligible_neutrinos": eligible,
                    "outside_acceptance_neutrinos": outside,
                    "off_transported": 50000,
                    "on_transported": 50000 + eligible,
                    "transported_delta": eligible,
                    "off_total_energy_mev": 1000.0,
                    "on_total_energy_mev": 1000.0,
                    "energy_delta_mev": 0.0,
                    "energy_abs_delta_mev": 0.0,
                    "energy_relative_delta": 0.0,
                    "off_hit_count": 10000,
                    "on_hit_count": 10000,
                    "changed_hit_cells": 0,
                    "missing_off_hit_cells": 0,
                    "missing_on_hit_cells": 0,
                    "hit_energy_l1_mev": 0.0,
                    "max_abs_hit_delta_mev": 0.0,
                    "generator_entries": 60000,
                    "requested_interactions": 1000,
                    "generated_interactions": 1000,
                    "generation_failures": 0,
                    "unknown_pdg_particles": 0,
                    "unlineaged_steps": 0,
                    "segmentation_failures": 0,
                }
            )

        event_fields = (
            "event",
            "bcid",
            "eligible_neutrinos",
            "outside_acceptance_neutrinos",
            "off_transported",
            "on_transported",
            "off_energy_mev",
            "on_energy_mev",
            "energy_delta_mev",
            "energy_abs_delta_mev",
            "off_hit_count",
            "on_hit_count",
        )
        with (analysis_dir / "paired_events.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=event_fields)
            writer.writeheader()
            for event in range(EXECUTOR.EVENTS_PER_CONDITION):
                event_eligible = eligible if event == 0 else 0
                event_outside = outside if event == 1 else 0
                writer.writerow(
                    {
                        "event": event,
                        "bcid": event,
                        "eligible_neutrinos": event_eligible,
                        "outside_acceptance_neutrinos": event_outside,
                        "off_transported": 50,
                        "on_transported": 50 + event_eligible,
                        "off_energy_mev": 1.0,
                        "on_energy_mev": 1.0,
                        "energy_delta_mev": 0.0,
                        "energy_abs_delta_mev": 0.0,
                        "off_hit_count": 10,
                        "on_hit_count": 10,
                    }
                )

        (analysis_dir / "paired_validation.txt").write_text(
            "NEUTRINO_TRANSPORT_ANALYSIS_RESULT=PASS\n"
            "metadata_pairing=PASS\n"
            "event_pairing=PASS\n"
            "generator_pairing=PASS\n"
            "particle_accounting=PASS\n"
            f"eligible_neutrinos={eligible}\n"
            f"outside_acceptance_neutrinos={outside}\n"
            "energy_difference_classification=REPORTED_NOT_ASSUMED\n",
            encoding="utf-8",
        )

    def test_fixed_matrix_and_simulator_arguments(self) -> None:
        self.assertEqual(
            [(run.seed, run.condition) for run in EXECUTOR.RUNS],
            [
                (1512, "off"),
                (1512, "on"),
                (2512, "off"),
                (2512, "on"),
                (3512, "off"),
                (3512, "on"),
            ],
        )
        run = EXECUTOR.RUNS[-1]
        arguments = EXECUTOR.simulator_arguments(
            run, Path("sample.root"), dry_run=True
        )
        pairs = dict(zip(arguments[1::2], arguments[2::2]))
        self.assertEqual(pairs["--events"], "1000")
        self.assertEqual(pairs["--mu"], "1")
        self.assertEqual(pairs["--threads"], "1")
        self.assertEqual(pairs["--seed"], "3512")
        self.assertEqual(arguments[-1], "--dry-run")

    def test_dry_run_preflights_six_runs_without_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "prospective"
            with (
                mock.patch.object(EXECUTOR, "require_project_layout"),
                mock.patch.object(EXECUTOR, "build_project"),
                mock.patch.object(EXECUTOR, "run_contract_preflight") as contract,
                mock.patch.object(EXECUTOR, "preflight_run") as preflight,
                mock.patch.object(EXECUTOR, "execute_production") as transport,
                contextlib.redirect_stdout(io.StringIO()) as captured,
            ):
                self.assertEqual(
                    EXECUTOR.main(["--dry-run", "--output-dir", str(output)]), 0
                )
            contract.assert_called_once_with(output.resolve())
            self.assertEqual(preflight.call_count, 6)
            transport.assert_not_called()
            self.assertFalse(output.exists())
            self.assertIn(
                "NEUTRINO_TRANSPORT_STAGE83_EXECUTOR_PREFLIGHT=PASS",
                captured.getvalue(),
            )
            self.assertIn("transport_executed=NO", captured.getvalue())

    def test_transport_requires_explicit_production_flag(self) -> None:
        with self.assertRaisesRegex(
            EXECUTOR.Stage83CampaignError, "choose exactly one"
        ):
            EXECUTOR.main([])
        with self.assertRaisesRegex(
            EXECUTOR.Stage83CampaignError, "choose exactly one"
        ):
            EXECUTOR.main(["--dry-run", "--execute-production"])

    def test_existing_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                EXECUTOR.Stage83CampaignError, "already exists"
            ):
                EXECUTOR.ensure_output_absent(Path(temporary))

    def test_zero_eligible_seed_and_aggregate_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary)
            for seed in EXECUTOR.SEEDS:
                self.write_seed_analysis(staging, seed, eligible=0)
            aggregate = EXECUTOR.aggregate_seed_products(staging)
            self.assertEqual(aggregate["eligible_neutrinos"], "0")
            self.assertEqual(aggregate["transported_delta"], "0")
            self.assertEqual(
                aggregate["eligible_sample_classification"], "NONE"
            )
            EXECUTOR.validate_aggregate_products(staging / "analysis")

    def test_three_seed_aggregate_is_descriptive_at_thirty(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary)
            for seed, eligible in zip(EXECUTOR.SEEDS, (0, 1, 29)):
                self.write_seed_analysis(staging, seed, eligible=eligible)
            aggregate = EXECUTOR.aggregate_seed_products(staging)
            self.assertEqual(aggregate["eligible_neutrinos"], "30")
            self.assertEqual(aggregate["transported_delta"], "30")
            self.assertEqual(
                aggregate["eligible_sample_classification"], "DESCRIPTIVE"
            )
            with (
                staging / "analysis" / "stage83_events.csv"
            ).open(newline="", encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 3000)

    def test_eligible_sample_classification_boundaries(self) -> None:
        self.assertEqual(EXECUTOR.classify_eligible_sample(0), "NONE")
        self.assertEqual(EXECUTOR.classify_eligible_sample(1), "LIMITED")
        self.assertEqual(EXECUTOR.classify_eligible_sample(29), "LIMITED")
        self.assertEqual(EXECUTOR.classify_eligible_sample(30), "DESCRIPTIVE")

    def test_resource_log_parser(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "resource.txt"
            path.write_text(
                "\tUser time (seconds): 149.33\n"
                "\tSystem time (seconds): 0.19\n"
                "\tElapsed (wall clock) time (h:mm:ss or m:ss): 2:29.24\n"
                "\tMaximum resident set size (kbytes): 164852\n",
                encoding="utf-8",
            )
            values = EXECUTOR.parse_resource_log(path)
            self.assertEqual(values["elapsed_seconds"], "149.240000")
            self.assertEqual(values["max_rss_kbytes"], "164852")

    def test_resource_summary_contains_paired_ratios(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary)
            (staging / "analysis").mkdir()
            artifacts = {}
            for run in EXECUTOR.RUNS:
                seed_dir = staging / f"seed-{run.seed}"
                seed_dir.mkdir(exist_ok=True)
                label = f"paired-{run.condition}-1000"
                root_file = seed_dir / f"{label}.root"
                simulation_log = seed_dir / f"{label}-simulation.log"
                resource_log = seed_dir / f"{label}-resource-usage.txt"
                audit_log = seed_dir / f"{label}-root-audit.log"
                multiplier = 1 if run.condition == "off" else 2
                root_file.write_bytes(b"r" * (10 * multiplier))
                simulation_log.write_text("simulation\n", encoding="utf-8")
                resource_log.write_text(
                    "User time (seconds): 1.0\n"
                    "System time (seconds): 0.1\n"
                    f"Elapsed (wall clock) time (h:mm:ss or m:ss): {multiplier}:00.00\n"
                    f"Maximum resident set size (kbytes): {100 * multiplier}\n",
                    encoding="utf-8",
                )
                audit_log.write_text("AUDIT_RESULT=PASS\n", encoding="utf-8")
                artifacts[(run.seed, run.condition)] = {
                    "root_file": root_file,
                    "root_sha256": EXECUTOR.sha256_file(root_file),
                    "simulation_log": simulation_log,
                    "resource_log": resource_log,
                    "audit_log": audit_log,
                }

            EXECUTOR.write_resource_summary(staging, artifacts)
            path = staging / "analysis" / "stage83_resource_summary.csv"
            EXECUTOR.validate_resource_summary(path)
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 6)
            for row in rows:
                self.assertEqual(row["wall_time_ratio_on_over_off"], "2")
                self.assertEqual(row["max_rss_ratio_on_over_off"], "2")
                self.assertEqual(row["root_size_ratio_on_over_off"], "2")

    def test_transport_failure_removes_transactional_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / "campaigns"
            output = parent / "stage83"
            with mock.patch.object(
                EXECUTOR,
                "run_and_tee",
                side_effect=EXECUTOR.Stage83CampaignError(
                    "synthetic production failure"
                ),
            ):
                with self.assertRaisesRegex(
                    EXECUTOR.Stage83CampaignError, "synthetic"
                ):
                    EXECUTOR.execute_production(output, "b" * 40)
            self.assertFalse(output.exists())
            self.assertEqual(list(parent.iterdir()), [])

    def test_analyzer_is_parameterized_and_pilot_compatible(self) -> None:
        source = ANALYZER_PATH.read_text(encoding="utf-8")
        for required in (
            "const int expectedEvents = 100",
            "const int expectedSeed = 512",
            "const bool requirePositiveEligible = true",
            "if (requirePositiveEligible)",
            "event < expectedEvents",
            "record->events == expectedEvents",
            "record->seed == expectedSeed",
            "requested_interactions,generated_interactions",
            "unknown_pdg_particles",
            "segmentation_failures",
        ):
            self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
