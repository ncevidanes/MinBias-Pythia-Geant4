#!/usr/bin/env python3
"""Regression tests for the fixed Cycle 8.3 production contract."""

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
MODULE_PATH = PROJECT_DIR / "scripts" / "preflight_neutrino_transport_stage83.py"
SPEC = importlib.util.spec_from_file_location(
    "neutrino_transport_stage83_preflight", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
PREFLIGHT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PREFLIGHT
SPEC.loader.exec_module(PREFLIGHT)


class NeutrinoTransportStage83PreflightTest(unittest.TestCase):
    def test_fixed_matrix_and_budget(self) -> None:
        self.assertEqual(PREFLIGHT.SEEDS, (1512, 2512, 3512))
        self.assertEqual(PREFLIGHT.EVENTS_PER_CONDITION, 1000)
        self.assertEqual(PREFLIGHT.THREADS, 1)
        self.assertEqual(
            [
                (run.seed, run.condition, run.transport_neutrinos)
                for run in PREFLIGHT.RUNS
            ],
            [
                (1512, "off", False),
                (1512, "on", True),
                (2512, "off", False),
                (2512, "on", True),
                (3512, "off", False),
                (3512, "on", True),
            ],
        )
        self.assertEqual(
            sum(run.bunch_crossings for run in PREFLIGHT.RUNS), 6000
        )
        self.assertEqual(len({run.output_name for run in PREFLIGHT.RUNS}), 6)

    def test_changed_matrix_is_rejected(self) -> None:
        changed = list(PREFLIGHT.RUNS)
        changed[-1] = PREFLIGHT.ProductionRun(4512, "on", True)
        with self.assertRaisesRegex(
            PREFLIGHT.Stage83PreflightError, "differs from contract"
        ):
            PREFLIGHT.validate_matrix(changed)

    def test_specification_and_pilot_templates(self) -> None:
        PREFLIGHT.require_contract_files()
        PREFLIGHT.validate_specification()
        with mock.patch.object(PREFLIGHT.PILOT, "run_validator") as validator:
            PREFLIGHT.validate_pilot_templates()
        self.assertEqual(validator.call_count, 2)

    def test_existing_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                PREFLIGHT.Stage83PreflightError,
                "output directory already exists",
            ):
                PREFLIGHT.ensure_output_absent(Path(temporary))

    def test_storage_below_five_gib_is_rejected(self) -> None:
        usage = mock.Mock(free=PREFLIGHT.MINIMUM_FREE_BYTES - 1)
        with (
            tempfile.TemporaryDirectory() as temporary,
            mock.patch.object(PREFLIGHT.shutil, "disk_usage", return_value=usage),
            self.assertRaisesRegex(
                PREFLIGHT.Stage83PreflightError, "insufficient storage"
            ),
        ):
            PREFLIGHT.validate_storage_budget(Path(temporary) / "campaign")

    def test_main_validates_six_runs_without_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "not-created"
            stdout = io.StringIO()
            with (
                mock.patch.object(PREFLIGHT.PILOT, "run_validator"),
                mock.patch.object(
                    PREFLIGHT,
                    "validate_storage_budget",
                    return_value=PREFLIGHT.MINIMUM_FREE_BYTES,
                ),
                contextlib.redirect_stdout(stdout),
            ):
                result = PREFLIGHT.main(["--output-dir", str(output_dir)])

        lines = stdout.getvalue().splitlines()
        self.assertEqual(result, 0)
        self.assertFalse(output_dir.exists())
        self.assertEqual(
            sum(line.startswith("CYCLE_8_STAGE83_RUN_PREFLIGHT=PASS") for line in lines),
            6,
        )
        self.assertEqual(
            lines[-1],
            "NEUTRINO_TRANSPORT_STAGE83_PREFLIGHT=PASS runs=6 "
            "seed_pairs=3 bunch_crossings=6000 paired_bunch_crossings=3000 "
            "events_per_condition=1000 seeds=1512,2512,3512 threads=1 "
            "stopping_rule=fixed_budget transport_executed=NO",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
