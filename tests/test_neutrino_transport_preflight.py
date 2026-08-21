#!/usr/bin/env python3
"""Regression tests for the Cycle 8 neutrino-transport preflight."""

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
MODULE_PATH = PROJECT_DIR / "scripts" / "preflight_neutrino_transport.py"
SPEC = importlib.util.spec_from_file_location(
    "neutrino_transport_preflight", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
PREFLIGHT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PREFLIGHT
SPEC.loader.exec_module(PREFLIGHT)


class NeutrinoTransportPreflightTest(unittest.TestCase):
    def test_fixed_pilot_matrix(self) -> None:
        self.assertEqual(
            [
                (
                    run.role,
                    run.condition,
                    run.bunch_crossings,
                    run.transport_neutrinos,
                )
                for run in PREFLIGHT.RUNS
            ],
            [
                ("smoke", "on", 3, True),
                ("paired", "off", 100, False),
                ("paired", "on", 100, True),
            ],
        )
        self.assertEqual(
            sum(run.bunch_crossings for run in PREFLIGHT.RUNS), 203
        )
        self.assertEqual(
            sum(
                run.bunch_crossings
                for run in PREFLIGHT.RUNS
                if run.role == "paired"
            ),
            200,
        )

    def test_repository_configs_match_fixed_contract(self) -> None:
        for run in PREFLIGHT.RUNS:
            with self.subTest(role=run.role, condition=run.condition):
                PREFLIGHT.validate_run_contract(run)

    def test_pair_differs_only_by_output_and_neutrino_switch(self) -> None:
        self.assertEqual(
            PREFLIGHT.validate_pair_contract(),
            ("output", "transport_neutrinos"),
        )

    def test_smoke_is_an_event_count_variant_of_on_condition(self) -> None:
        self.assertEqual(
            PREFLIGHT.validate_smoke_contract(),
            ("events", "output"),
        )

    def test_unexpected_paired_difference_is_rejected(self) -> None:
        left = {"events": "100", "output": "off.root", "switch": "false"}
        right = {"events": "101", "output": "on.root", "switch": "true"}
        with self.assertRaisesRegex(PREFLIGHT.PreflightError, "unexpected=events"):
            PREFLIGHT.compare_config_maps(
                left,
                right,
                {"output", "switch"},
                "synthetic pair",
            )

    def test_static_pythia_and_neutrino_source_contracts(self) -> None:
        PREFLIGHT.validate_pythia_contract()
        PREFLIGHT.validate_neutrino_source_contract()

    def test_main_preflights_three_runs_without_transport_or_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "not-created"
            stdout = io.StringIO()
            with (
                mock.patch.object(
                    PREFLIGHT, "run_validator", return_value="ok"
                ) as validator,
                contextlib.redirect_stdout(stdout),
            ):
                result = PREFLIGHT.main(["--output-dir", str(output_dir)])

        self.assertEqual(result, 0)
        self.assertEqual(validator.call_count, 3)
        self.assertFalse(output_dir.exists())
        self.assertEqual(
            stdout.getvalue().splitlines()[-1],
            "NEUTRINO_TRANSPORT_PREFLIGHT=PASS runs=3 "
            "bunch_crossings=203 paired_bunch_crossings=200 "
            "seed=512 threads=1 transport_executed=NO",
        )

    def test_existing_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                PREFLIGHT.PreflightError, "output directory already exists"
            ):
                PREFLIGHT.ensure_output_absent(Path(temporary))


if __name__ == "__main__":
    unittest.main(verbosity=2)
