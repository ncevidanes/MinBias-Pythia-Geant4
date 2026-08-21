#!/usr/bin/env python3
"""Regression tests for the Cycle 9 performance/reproducibility preflight."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_DIR / "scripts" / "preflight_performance_reproducibility.py"

SPEC = importlib.util.spec_from_file_location(
    "performance_reproducibility_preflight",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
PREFLIGHT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PREFLIGHT
SPEC.loader.exec_module(PREFLIGHT)


class PerformanceReproducibilityPreflightTest(unittest.TestCase):
    def test_fixed_reproducibility_matrix(self) -> None:
        self.assertEqual(
            [(r.name, r.threads, r.repetition, r.events) for r in PREFLIGHT.REPRO_RUNS],
            [
                ("repro-t1-r1", 1, 1, 100),
                ("repro-t1-r2", 1, 2, 100),
                ("repro-t2-r1", 2, 1, 100),
                ("repro-t2-r2", 2, 2, 100),
            ],
        )

    def test_fixed_performance_matrix_is_interleaved(self) -> None:
        self.assertEqual(
            [(r.name, r.threads, r.repetition, r.events) for r in PREFLIGHT.PERF_RUNS],
            [
                ("perf-t1-r1", 1, 1, 200),
                ("perf-t2-r1", 2, 1, 200),
                ("perf-t1-r2", 1, 2, 200),
                ("perf-t2-r2", 2, 2, 200),
                ("perf-t1-r3", 1, 3, 200),
                ("perf-t2-r3", 2, 3, 200),
            ],
        )

    def test_repository_static_contracts(self) -> None:
        PREFLIGHT.validate_project_layout()
        PREFLIGHT.validate_template_contract()
        PREFLIGHT.validate_pythia_contract()
        PREFLIGHT.validate_source_contract()
        PREFLIGHT.validate_matrix_contract()
        PREFLIGHT.validate_contract_text()

    def test_dry_run_command_contains_authoritative_overrides(self) -> None:
        run = PREFLIGHT.REPRO_RUNS[0]
        output_dir = PROJECT_DIR / "outputs" / "synthetic-cycle9"
        command = PREFLIGHT.dry_run_command(output_dir, run)
        joined = " ".join(command)
        self.assertIn("--events 100", joined)
        self.assertIn("--mu 1.0", joined)
        self.assertIn("--threads 1", joined)
        self.assertIn("--seed 9512", joined)
        self.assertIn("--dry-run", joined)
        self.assertIn("repro-t1-r1.root", joined)

    def test_existing_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                PREFLIGHT.PreflightError,
                "output directory already exists",
            ):
                PREFLIGHT.ensure_output_absent(Path(temporary))

    def test_execute_dry_run_accepts_valid_simulator_report(self) -> None:
        run = PREFLIGHT.REPRO_RUNS[0]
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "future-output"
            root_path = PREFLIGHT.run_output_path(output_dir, run)
            fake_output = "\n".join(
                [
                    "events = 100",
                    "threads = 1",
                    "seed_base = 9512",
                    "interaction_mode = poisson",
                    "mean_interactions = 1",
                    f"output = \"{root_path}\"",
                    "Dry run concluído; nenhuma simulação foi executada.",
                ]
            )
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=fake_output,
            )
            stdout = io.StringIO()
            with (
                mock.patch.object(PREFLIGHT.subprocess, "run", return_value=completed),
                contextlib.redirect_stdout(stdout),
            ):
                PREFLIGHT.execute_dry_run(output_dir, run)
            self.assertFalse(output_dir.exists())
            self.assertIn("CYCLE_9_RUN_DRY_RUN=PASS", stdout.getvalue())

    def test_main_validates_ten_runs_without_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "not-created"
            stdout = io.StringIO()
            with (
                mock.patch.object(PREFLIGHT, "validate_simulator"),
                mock.patch.object(
                    PREFLIGHT,
                    "validate_resources",
                    return_value=(12, 3 * 1024**3, 10 * 1024**3),
                ),
                mock.patch.object(PREFLIGHT, "execute_dry_run") as execute,
                contextlib.redirect_stdout(stdout),
            ):
                result = PREFLIGHT.main(["--output-dir", str(output_dir)])

        self.assertEqual(result, 0)
        self.assertEqual(execute.call_count, 10)
        self.assertFalse(output_dir.exists())
        self.assertIn(
            "PERFORMANCE_REPRODUCIBILITY_PREFLIGHT=PASS runs=10",
            stdout.getvalue(),
        )
        self.assertIn("transport_executed=NO", stdout.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
