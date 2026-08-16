#!/usr/bin/env python3
"""Synthetic tests for the Cycle 7 transactional campaign executor."""

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
SCRIPT_PATH = PROJECT_DIR / "scripts" / "run_integrated_minbias_campaign.py"
ANALYZER_PATH = PROJECT_DIR / "scripts" / "analyze_integrated_minbias.C"


def load_executor():
    spec = importlib.util.spec_from_file_location("cycle7_executor_under_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXECUTOR = load_executor()


class IntegratedMinbiasExecutorTest(unittest.TestCase):
    def write_analysis_products(
        self,
        stage,
        directory: Path,
        *,
        empty_sampling: int | None = None,
    ) -> None:
        directory.mkdir()
        summary_fields = (
            "stage",
            "bunch_crossings",
            "mean_interactions",
            "seed",
            "threads",
            "transport_neutrinos",
            "generator_audit",
            "check_overlaps",
            "requested_interactions",
            "generated_interactions",
            "generation_failures",
            "unknown_pdg_particles",
            "total_energy_mev",
            "poisson_z",
        )
        with (directory / "integrated_summary.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=summary_fields)
            writer.writeheader()
            writer.writerow(
                {
                    "stage": stage.phase,
                    "bunch_crossings": stage.bunch_crossings,
                    "mean_interactions": stage.mean_interactions,
                    "seed": stage.seed,
                    "threads": 1,
                    "transport_neutrinos": 0,
                    "generator_audit": int(stage.generator_audit),
                    "check_overlaps": int(stage.check_overlaps),
                    "requested_interactions": stage.bunch_crossings,
                    "generated_interactions": stage.bunch_crossings - 1,
                    "generation_failures": 1,
                    "unknown_pdg_particles": 0,
                    "total_energy_mev": 100.0,
                    "poisson_z": 0.25,
                }
            )

        with (directory / "sampling_summary.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "sampling",
                    "name",
                    "hit_count",
                    "total_energy_mev",
                    "energy_fraction",
                ),
            )
            writer.writeheader()
            for index, name in enumerate(EXECUTOR.SAMPLINGS):
                writer.writerow(
                    {
                        "sampling": index,
                        "name": name,
                        "hit_count": 0 if index == empty_sampling else 1,
                        "total_energy_mev": 10.0,
                        "energy_fraction": 0.1,
                    }
                )

        coverage = "STRUCTURAL" if stage.phase == "7.1" else "PASS"
        poisson = "NOT_APPLICABLE" if stage.phase == "7.1" else "PASS"
        (directory / "integrated_validation.txt").write_text(
            "INTEGRATED_MINBIAS_ANALYSIS_RESULT=PASS\n"
            f"stage={stage.phase}\n"
            "energy_closure=PASS\n"
            "particle_accounting=PASS\n"
            f"sampling_coverage={coverage}\n"
            f"poisson_consistency={poisson}\n",
            encoding="utf-8",
        )

    def test_fixed_matrix_and_simulator_arguments(self) -> None:
        self.assertEqual([stage.phase for stage in EXECUTOR.STAGES], ["7.1", "7.2", "7.3"])
        stage = EXECUTOR.stage_by_phase("7.2")
        arguments = EXECUTOR.simulator_arguments(stage, Path("sample.root"), dry_run=True)
        pairs = dict(zip(arguments[1::2], arguments[2::2]))
        self.assertEqual(pairs["--events"], "500")
        self.assertEqual(pairs["--mu"], "2")
        self.assertEqual(pairs["--threads"], "1")
        self.assertEqual(pairs["--seed"], "513")
        self.assertEqual(arguments[-1], "--dry-run")

    def test_dry_run_preflights_every_stage_without_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "prospective"
            with (
                mock.patch.object(EXECUTOR, "require_project_layout"),
                mock.patch.object(EXECUTOR, "build_project"),
                mock.patch.object(EXECUTOR, "run_contract_preflight") as contract,
                mock.patch.object(EXECUTOR, "preflight_stage") as preflight,
                mock.patch.object(EXECUTOR, "execute_stage") as transport,
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

    def test_full_run_dispatches_only_the_selected_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "stage71"
            with (
                mock.patch.object(EXECUTOR, "require_project_layout"),
                mock.patch.object(EXECUTOR, "build_project"),
                mock.patch.object(EXECUTOR, "run_contract_preflight"),
                mock.patch.object(EXECUTOR, "preflight_stage"),
                mock.patch.object(EXECUTOR, "git_provenance", return_value="a" * 40),
                mock.patch.object(EXECUTOR, "execute_stage") as execute,
            ):
                self.assertEqual(
                    EXECUTOR.main(
                        ["--stage", "7.1", "--output-dir", str(output)]
                    ),
                    0,
                )
            execute.assert_called_once_with(
                EXECUTOR.stage_by_phase("7.1"), output.resolve(), "a" * 40
            )

    def test_transport_requires_an_explicit_stage(self) -> None:
        with self.assertRaisesRegex(EXECUTOR.CampaignError, "--stage is required"):
            EXECUTOR.main([])

    def test_existing_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(EXECUTOR.CampaignError, "already exists"):
                EXECUTOR.ensure_output_absent(Path(temporary))

    def test_valid_synthetic_analysis_products(self) -> None:
        stage = EXECUTOR.stage_by_phase("7.2")
        with tempfile.TemporaryDirectory() as temporary:
            analysis = Path(temporary) / "analysis"
            self.write_analysis_products(stage, analysis)
            EXECUTOR.validate_analysis_products(stage, analysis)

    def test_missing_required_sampling_is_rejected(self) -> None:
        stage = EXECUTOR.stage_by_phase("7.3")
        with tempfile.TemporaryDirectory() as temporary:
            analysis = Path(temporary) / "analysis"
            self.write_analysis_products(stage, analysis, empty_sampling=4)
            with self.assertRaisesRegex(EXECUTOR.CampaignError, "not observed"):
                EXECUTOR.validate_analysis_products(stage, analysis)

    def test_transport_failure_removes_transactional_staging(self) -> None:
        stage = EXECUTOR.stage_by_phase("7.1")
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / "campaigns"
            output = parent / "stage71"
            with mock.patch.object(
                EXECUTOR,
                "run_and_tee",
                side_effect=EXECUTOR.CampaignError("synthetic transport failure"),
            ):
                with self.assertRaisesRegex(EXECUTOR.CampaignError, "synthetic"):
                    EXECUTOR.execute_stage(stage, output, "b" * 40)
            self.assertFalse(output.exists())
            self.assertEqual(list(parent.iterdir()), [])

    def test_root_analyzer_contains_transactional_acceptance_markers(self) -> None:
        source = ANALYZER_PATH.read_text(encoding="utf-8")
        for required in (
            "INTEGRATED_MINBIAS_ANALYSIS_RESULT=PASS",
            "std::filesystem::rename(temporaryDirectory, finalDirectory)",
            '"Poisson count lies outside five sigma"',
            '"required sampling is not observed"',
            '"energy closure mismatch"',
        ):
            self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
