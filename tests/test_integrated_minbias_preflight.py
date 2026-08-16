#!/usr/bin/env python3
"""Regression tests for the Cycle 7.0A integrated minimum-bias preflight."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_DIR / "scripts" / "preflight_integrated_minbias.py"
SPEC = importlib.util.spec_from_file_location("integrated_minbias_preflight", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PREFLIGHT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PREFLIGHT
SPEC.loader.exec_module(PREFLIGHT)


class IntegratedMinbiasPreflightTest(unittest.TestCase):
    def test_fixed_stage_matrix(self) -> None:
        self.assertEqual(
            [
                (stage.phase, stage.name, stage.bunch_crossings, stage.mean_interactions, stage.seed)
                for stage in PREFLIGHT.STAGES
            ],
            [
                ("7.1", "smoke", 3, 1.0, 512),
                ("7.2", "statistical", 500, 2.0, 513),
                ("7.3", "production", 3000, 50.0, 512),
            ],
        )
        self.assertEqual(sum(stage.bunch_crossings for stage in PREFLIGHT.STAGES), 3503)
        self.assertEqual(sum(stage.expected_interactions for stage in PREFLIGHT.STAGES), 151003.0)

    def test_repository_configs_match_fixed_contract(self) -> None:
        for stage in PREFLIGHT.STAGES:
            with self.subTest(stage=stage.name):
                PREFLIGHT.validate_stage_contract(stage)
        self.assertEqual(
            [(stage.generator_audit, stage.check_overlaps) for stage in PREFLIGHT.STAGES],
            [(True, True), (True, True), (False, False)],
        )

    def test_static_pythia_root_and_sampling_contracts(self) -> None:
        PREFLIGHT.validate_pythia_contract()
        PREFLIGHT.validate_root_source_contract()
        PREFLIGHT.validate_sampling_source_contract()
        self.assertEqual(tuple(PREFLIGHT.ROOT_BRANCHES), ("events", "hits", "generator", "metadata"))
        self.assertEqual(len(PREFLIGHT.SAMPLINGS), 10)

    def test_main_preflights_three_stages_without_transport_or_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "not-created"
            stdout = io.StringIO()
            with (
                mock.patch.object(PREFLIGHT, "run_validator", return_value="ok") as validator,
                contextlib.redirect_stdout(stdout),
            ):
                result = PREFLIGHT.main(["--output-dir", str(output_dir)])
        self.assertEqual(result, 0)
        self.assertEqual(validator.call_count, 3)
        self.assertFalse(output_dir.exists())
        self.assertEqual(
            stdout.getvalue().splitlines()[-1],
            "INTEGRATED_MINBIAS_PREFLIGHT=PASS stages=3 bunch_crossings=3503 "
            "expected_interactions=151003 trees=4 samplings=10 threads=1 "
            "transport_executed=NO",
        )

    def test_existing_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(PREFLIGHT.PreflightError, "output directory already exists"):
                PREFLIGHT.ensure_output_absent(Path(temporary))


if __name__ == "__main__":
    unittest.main()
