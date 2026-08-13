#!/usr/bin/env python3
"""Regression tests for the Cycle 6.5 operational-containment analyzer."""

from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_DIR / "scripts" / "analyze_longitudinal_containment.py"
SPEC = importlib.util.spec_from_file_location("longitudinal_containment", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
ANALYZER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ANALYZER
SPEC.loader.exec_module(ANALYZER)


class LongitudinalContainmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.summary = self.directory / "statistical_summary.csv"
        self.samplings = self.directory / "statistical_samplings.csv"
        self.output = self.directory / "containment_summary.csv"
        self.validation = self.directory / "containment_validation.txt"
        self._write_evidence()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_evidence(self) -> None:
        particles = (("electron", 11), ("photon", 22), ("pion_plus", 211))
        electromagnetic = (
            0.01, 0.50, 0.485, 0.004, 0.0004,
            0.0002, 0.0001, 0.0001, 0.0001, 0.0001,
        )
        pion = (0.02, 0.10, 0.35, 0.05, 0.25, 0.20, 0.02, 0.004, 0.003, 0.003)
        summary_rows = []
        sampling_rows = []
        for particle, pdg in particles:
            for energy in (1.0, 10.0, 100.0):
                mean = energy * 100.0 + pdg / 1000.0
                summary_rows.append({
                    "git_commit": "a" * 40,
                    "particle": particle,
                    "pdg": pdg,
                    "kinetic_energy_gev": energy,
                    "runs": 5,
                    "events": 1000,
                    "mean_energy_mev": mean,
                })
                profile = pion if pdg == 211 else electromagnetic
                for sampling, (name, fraction) in enumerate(
                    zip(ANALYZER.SAMPLING_NAMES, profile)
                ):
                    sampling_rows.append({
                        "git_commit": "a" * 40,
                        "particle": particle,
                        "pdg": pdg,
                        "kinetic_energy_gev": energy,
                        "sampling": sampling,
                        "name": name,
                        "runs": 5,
                        "events": 1000,
                        "mean_energy_mev": mean * fraction,
                        "total_energy_fraction": fraction,
                    })
        with self.summary.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=summary_rows[0], lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(summary_rows)
        with self.samplings.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=sampling_rows[0], lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(sampling_rows)

    def _run(self, *extra: str) -> None:
        result = ANALYZER.main([
            "--summary", str(self.summary),
            "--samplings", str(self.samplings),
            "--output", str(self.output),
            "--validation", str(self.validation),
            *extra,
        ])
        self.assertEqual(result, 0)

    def test_group_fractions_and_containment_outputs(self) -> None:
        self._run()
        with self.output.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 9)
        electron = next(
            row for row in rows
            if int(row["pdg"]) == 11 and float(row["kinetic_energy_gev"]) == 1.0
        )
        pion = next(
            row for row in rows
            if int(row["pdg"]) == 211 and float(row["kinetic_energy_gev"]) == 100.0
        )
        self.assertAlmostEqual(float(electron["em_total_fraction"]), 0.999)
        self.assertEqual(electron["containment_99_sampling"], "EMB2")
        self.assertAlmostEqual(float(pion["tile_central_fraction"]), 0.47)
        self.assertAlmostEqual(float(pion["tile_extended_fraction"]), 0.01)
        self.assertEqual(pion["containment_99_sampling"], "TileCal3")
        self.assertEqual(pion["outer_tail_review"], "true")
        validation = self.validation.read_text(encoding="utf-8")
        self.assertIn("LONGITUDINAL_CONTAINMENT_RESULT=PASS\n", validation)
        self.assertIn("physical_points=9\n", validation)
        self.assertIn("outer_tail_review_points=3\n", validation)
        self.assertIn("outer_tail_review=REQUIRED\n", validation)

    def test_fraction_mismatch_is_rejected_transactionally(self) -> None:
        with self.samplings.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        rows[0]["total_energy_fraction"] = "0.02"
        with self.samplings.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "inconsistent sampling fraction"):
            self._run()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.validation.exists())

    def test_extended_activity_limit_is_rejected_transactionally(self) -> None:
        with self.assertRaisesRegex(ValueError, "TileExt fraction exceeds limit"):
            self._run("--max-tile-extended-fraction", "0.009")
        self.assertFalse(self.output.exists())
        self.assertFalse(self.validation.exists())


if __name__ == "__main__":
    unittest.main()
