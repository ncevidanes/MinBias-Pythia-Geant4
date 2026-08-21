#!/usr/bin/env python3
"""Synthetic tests for the Cycle 8 paired executor and analyzer contract."""

from __future__ import annotations

import contextlib
import csv
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_DIR / "scripts" / "run_neutrino_transport_campaign.py"
ANALYZER_PATH = PROJECT_DIR / "scripts" / "analyze_neutrino_transport.C"


def load_executor():
    spec = importlib.util.spec_from_file_location(
        "cycle8_executor_under_test", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXECUTOR = load_executor()


class NeutrinoTransportExecutorTest(unittest.TestCase):
    def write_analysis_products(
        self, directory: Path, *, eligible: int = 2
    ) -> None:
        directory.mkdir()
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
        )
        with (directory / "paired_summary.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=summary_fields)
            writer.writeheader()
            writer.writerow(
                {
                    "events": 100,
                    "seed": 512,
                    "mean_interactions": 1.0,
                    "eligible_neutrinos": eligible,
                    "outside_acceptance_neutrinos": 3,
                    "off_transported": 5000,
                    "on_transported": 5000 + eligible,
                    "transported_delta": eligible,
                    "off_total_energy_mev": 100.0,
                    "on_total_energy_mev": 100.0,
                    "energy_delta_mev": 0.0,
                    "energy_abs_delta_mev": 0.0,
                    "energy_relative_delta": 0.0,
                    "off_hit_count": 1000,
                    "on_hit_count": 1000,
                    "changed_hit_cells": 0,
                    "missing_off_hit_cells": 0,
                    "missing_on_hit_cells": 0,
                    "hit_energy_l1_mev": 0.0,
                    "max_abs_hit_delta_mev": 0.0,
                    "generator_entries": 6000,
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
        with (directory / "paired_events.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=event_fields)
            writer.writeheader()
            for event in range(100):
                event_eligible = eligible if event == 0 else 0
                writer.writerow(
                    {
                        "event": event,
                        "bcid": event,
                        "eligible_neutrinos": event_eligible,
                        "outside_acceptance_neutrinos": 3 if event == 1 else 0,
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

        (directory / "paired_validation.txt").write_text(
            "NEUTRINO_TRANSPORT_ANALYSIS_RESULT=PASS\n"
            "metadata_pairing=PASS\n"
            "event_pairing=PASS\n"
            "generator_pairing=PASS\n"
            "particle_accounting=PASS\n"
            f"eligible_neutrinos={eligible}\n"
            "outside_acceptance_neutrinos=3\n"
            "energy_difference_classification=REPORTED_NOT_ASSUMED\n",
            encoding="utf-8",
        )

    def test_fixed_matrix_and_simulator_arguments(self) -> None:
        self.assertEqual(
            [
                (run.role, run.condition, run.bunch_crossings)
                for run in EXECUTOR.RUNS
            ],
            [("smoke", "on", 3), ("paired", "off", 100), ("paired", "on", 100)],
        )
        run = EXECUTOR.run_by("paired", "on")
        arguments = EXECUTOR.simulator_arguments(
            run, Path("sample.root"), dry_run=True
        )
        pairs = dict(zip(arguments[1::2], arguments[2::2]))
        self.assertEqual(pairs["--events"], "100")
        self.assertEqual(pairs["--mu"], "1")
        self.assertEqual(pairs["--threads"], "1")
        self.assertEqual(pairs["--seed"], "512")
        self.assertEqual(arguments[-1], "--dry-run")

    def test_dry_run_preflights_every_run_without_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "prospective"
            with (
                mock.patch.object(EXECUTOR, "require_project_layout"),
                mock.patch.object(EXECUTOR, "build_project"),
                mock.patch.object(EXECUTOR, "run_contract_preflight") as contract,
                mock.patch.object(EXECUTOR, "preflight_run") as preflight,
                mock.patch.object(EXECUTOR, "execute_pilot") as transport,
                contextlib.redirect_stdout(io.StringIO()) as captured,
            ):
                self.assertEqual(
                    EXECUTOR.main(["--dry-run", "--output-dir", str(output)]), 0
                )
            contract.assert_called_once_with(output.resolve())
            self.assertEqual(preflight.call_count, 3)
            transport.assert_not_called()
            self.assertFalse(output.exists())
            self.assertIn("transport_executed=NO", captured.getvalue())

    def test_transport_requires_explicit_execute_pilot_flag(self) -> None:
        with self.assertRaisesRegex(EXECUTOR.CampaignError, "choose exactly one"):
            EXECUTOR.main([])
        with self.assertRaisesRegex(EXECUTOR.CampaignError, "choose exactly one"):
            EXECUTOR.main(["--dry-run", "--execute-pilot"])

    def test_existing_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(EXECUTOR.CampaignError, "already exists"):
                EXECUTOR.ensure_output_absent(Path(temporary))

    def test_valid_synthetic_analysis_products(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            analysis = Path(temporary) / "analysis"
            self.write_analysis_products(analysis)
            EXECUTOR.validate_analysis_products(analysis)

    def test_zero_eligible_neutrinos_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            analysis = Path(temporary) / "analysis"
            self.write_analysis_products(analysis, eligible=0)
            with self.assertRaisesRegex(
                EXECUTOR.CampaignError, "no eligible neutrinos"
            ):
                EXECUTOR.validate_analysis_products(analysis)

    def test_transport_failure_removes_transactional_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / "campaigns"
            output = parent / "pilot"
            with mock.patch.object(
                EXECUTOR,
                "run_and_tee",
                side_effect=EXECUTOR.CampaignError("synthetic transport failure"),
            ):
                with self.assertRaisesRegex(EXECUTOR.CampaignError, "synthetic"):
                    EXECUTOR.execute_pilot(output, "b" * 40)
            self.assertFalse(output.exists())
            self.assertEqual(list(parent.iterdir()), [])

    def test_root_analyzer_contains_paired_acceptance_markers(self) -> None:
        source = ANALYZER_PATH.read_text(encoding="utf-8")
        for required in (
            "NEUTRINO_TRANSPORT_ANALYSIS_RESULT=PASS",
            "REPORTED_NOT_ASSUMED",
            "eligible neutrino count must be positive",
            "transported-particle delta mismatch",
            "std::filesystem::rename(temporaryDirectory, finalDirectory)",
        ):
            self.assertIn(required, source)

    def test_root_analyzer_handles_matching_nonfinite_generator_values(self) -> None:
        source = ANALYZER_PATH.read_text(encoding="utf-8")
        for required in (
            "bool SameGeneratorFloatingValue",
            "std::isnan(left) && std::isnan(right)",
            "std::isinf(left) || std::isinf(right)",
            "SameGeneratorFloatingValue(left.eta, right.eta)",
            "SameGeneratorFloatingValue(left.phi, right.phi)",
        ):
            self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
