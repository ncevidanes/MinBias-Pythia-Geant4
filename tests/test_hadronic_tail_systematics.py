#!/usr/bin/env python3
"""Regression tests for the Cycle 6.6 systematic campaign executor."""

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
MODULE_PATH = PROJECT_DIR / "scripts" / "run_hadronic_tail_systematics.py"
SPEC = importlib.util.spec_from_file_location("hadronic_tail_systematics", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
EXECUTOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXECUTOR
SPEC.loader.exec_module(EXECUTOR)


class HadronicTailSystematicsTest(unittest.TestCase):
    def test_fixed_matrix_has_paired_seeds_and_unique_names(self) -> None:
        cases = EXECUTOR.campaign_cases()
        self.assertEqual(len(cases), 45)
        self.assertEqual(len({case.name for case in cases}), 45)
        self.assertEqual({case.seed for case in cases}, set(EXECUTOR.SEEDS))
        self.assertEqual(
            Counter((case.eta, case.production_cut_mm) for case in cases),
            Counter({
                (eta, cut): 5
                for eta in EXECUTOR.ETA_VALUES
                for cut in EXECUTOR.PRODUCTION_CUTS_MM
            }),
        )
        for eta in EXECUTOR.ETA_VALUES:
            for cut in EXECUTOR.PRODUCTION_CUTS_MM:
                self.assertEqual(
                    {
                        case.seed
                        for case in cases
                        if case.eta == eta and case.production_cut_mm == cut
                    },
                    set(EXECUTOR.SEEDS),
                )

    def test_run_arguments_fix_systematic_physics_contract(self) -> None:
        case = next(
            case
            for case in EXECUTOR.campaign_cases()
            if case.eta == 0.4
            and case.production_cut_mm == 1.0
            and case.seed == 643031
        )
        arguments = EXECUTOR.run_arguments(case, Path("result.root"))
        pairs = dict(zip(arguments[::2], arguments[1::2]))
        self.assertEqual(pairs["--events"], "200")
        self.assertEqual(pairs["--threads"], "1")
        self.assertEqual(pairs["--seed"], "643031")
        self.assertEqual(pairs["--particle-pdg"], "211")
        self.assertEqual(pairs["--particle-kinetic-energy-gev"], "100")
        self.assertEqual(pairs["--particle-eta"], "0.4")
        self.assertEqual(pairs["--particle-phi"], "0")
        self.assertEqual(pairs["--production-cut-mm"], "1")

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
                mock.patch.object(
                    EXECUTOR, "preflight_case", side_effect=fake_preflight
                ),
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
        self.assertEqual(len(observed), 45)
        self.assertTrue(all(item[1] == output_dir.resolve() for item in observed))
        self.assertTrue(all(item[2] == 3 for item in observed))
        self.assertEqual(
            stdout.getvalue().splitlines()[-1],
            "HADRONIC_TAIL_SYSTEMATICS_PREFLIGHT=PASS "
            "points=9 runs=45 runs_per_point=5 events_per_run=200 "
            "total_events=9000 paired_seeds=5",
        )
        self.assertFalse(output_dir.exists())

    def test_full_run_dispatches_transactional_campaign(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "campaign"
            with (
                mock.patch.object(EXECUTOR, "require_project_layout"),
                mock.patch.object(EXECUTOR, "build_project") as build,
                mock.patch.object(
                    EXECUTOR, "git_provenance", return_value="a" * 40
                ),
                mock.patch.object(EXECUTOR, "execute_campaign") as execute,
            ):
                result = EXECUTOR.main([
                    "--output-dir",
                    str(output_dir),
                    "--build-jobs",
                    "4",
                ])

        self.assertEqual(result, 0)
        build.assert_called_once_with(4)
        execute.assert_called_once_with(
            EXECUTOR.campaign_cases(), output_dir.resolve(), 4, "a" * 40
        )

    def test_existing_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "existing"
            output_dir.mkdir()
            marker = output_dir / "preserve.txt"
            marker.write_text("preserve\n", encoding="utf-8")
            with self.assertRaisesRegex(EXECUTOR.CampaignError, "already exists"):
                EXECUTOR.ensure_output_absent(output_dir)
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve\n")

    def test_campaign_failure_leaves_no_output_directory(self) -> None:
        case = EXECUTOR.campaign_cases()[0]
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "campaign"
            with mock.patch.object(
                EXECUTOR,
                "run_case",
                side_effect=EXECUTOR.CampaignError("synthetic transport failure"),
            ):
                with self.assertRaisesRegex(
                    EXECUTOR.CampaignError, "synthetic transport failure"
                ):
                    EXECUTOR.execute_campaign((case,), output_dir, 2, "a" * 40)
            self.assertFalse(output_dir.exists())
            self.assertEqual(list(Path(temporary).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
