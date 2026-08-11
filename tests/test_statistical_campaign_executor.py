#!/usr/bin/env python3
"""Regression tests for the Cycle 6.4 statistical campaign executor."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock


PROJECT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_DIR / "scripts" / "run_statistical_single_particle_campaign.py"
SPEC = importlib.util.spec_from_file_location("statistical_campaign_executor", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
EXECUTOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXECUTOR
SPEC.loader.exec_module(EXECUTOR)


class StatisticalCampaignExecutorTest(unittest.TestCase):
    def test_fixed_matrix_has_unique_names_and_seeds(self) -> None:
        cases = EXECUTOR.campaign_cases()
        self.assertEqual(len(cases), 45)
        self.assertEqual(len({case.name for case in cases}), 45)
        self.assertEqual(len({case.seed for case in cases}), 45)
        self.assertEqual(
            Counter((case.pdg, case.energy_gev) for case in cases),
            Counter({
                (pdg, energy): 5
                for _, pdg in EXECUTOR.PARTICLES
                for energy in EXECUTOR.ENERGIES_GEV
            }),
        )
        self.assertEqual(
            [case.seed for case in cases[:5]],
            [641011, 641012, 641013, 641014, 641015],
        )
        self.assertEqual(
            [case.seed for case in cases[-5:]],
            [643031, 643032, 643033, 643034, 643035],
        )

    def test_run_arguments_fix_physics_contract(self) -> None:
        case = EXECUTOR.campaign_cases()[0]
        arguments = EXECUTOR.run_arguments(case, Path("result.root"))
        pairs = dict(zip(arguments[::2], arguments[1::2]))
        self.assertEqual(pairs["--events"], "200")
        self.assertEqual(pairs["--threads"], "1")
        self.assertEqual(pairs["--seed"], "641011")
        self.assertEqual(pairs["--particle-pdg"], "11")
        self.assertEqual(pairs["--particle-kinetic-energy-gev"], "1")
        self.assertEqual(pairs["--particle-eta"], "0")
        self.assertEqual(pairs["--particle-phi"], "0")

    def test_dry_run_preflights_all_cases_without_transport(self) -> None:
        observed = []

        def fake_preflight(case, output_dir, build_jobs):
            observed.append((case, output_dir, build_jobs))

        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "not-created"
            stdout = io.StringIO()
            with (
                mock.patch.object(EXECUTOR, "require_project_layout"),
                mock.patch.object(EXECUTOR, "build_project") as build,
                mock.patch.object(EXECUTOR, "preflight_case", side_effect=fake_preflight),
                mock.patch.object(EXECUTOR, "git_provenance") as provenance,
                mock.patch.object(EXECUTOR, "execute_campaign") as execute,
                contextlib.redirect_stdout(stdout),
            ):
                result = EXECUTOR.main([
                    "--dry-run",
                    "--output-dir",
                    str(output_dir),
                    "--build-jobs",
                    "3",
                ])

        self.assertEqual(result, 0)
        build.assert_called_once_with(3)
        provenance.assert_not_called()
        execute.assert_not_called()
        self.assertEqual(len(observed), 45)
        self.assertTrue(all(item[1] == output_dir.resolve() for item in observed))
        self.assertTrue(all(item[2] == 3 for item in observed))
        final_line = stdout.getvalue().splitlines()[-1]
        self.assertEqual(
            final_line,
            "STATISTICAL_CAMPAIGN_PREFLIGHT=PASS points=9 runs=45 "
            "runs_per_point=5 events_per_run=200 total_events=9000 unique_seeds=45",
        )
        self.assertFalse(output_dir.exists())

    def test_existing_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            with self.assertRaisesRegex(
                EXECUTOR.CampaignError, "output directory already exists"
            ):
                EXECUTOR.ensure_new_output_directory(output_dir)


if __name__ == "__main__":
    unittest.main()
