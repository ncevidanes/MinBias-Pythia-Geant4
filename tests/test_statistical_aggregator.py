#!/usr/bin/env python3
"""Regression tests for the Cycle 6.4 statistical aggregator."""

from __future__ import annotations

import csv
import importlib.util
import math
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_DIR / "scripts" / "aggregate_single_particle_statistics.py"
SPEC = importlib.util.spec_from_file_location("statistical_aggregator", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
AGGREGATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AGGREGATOR
SPEC.loader.exec_module(AGGREGATOR)


class StatisticalAggregatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.manifest = self.directory / "campaign_manifest.tsv"
        self.summary = self.directory / "statistical_summary.csv"
        self.samplings = self.directory / "statistical_samplings.csv"
        self.validation = self.directory / "statistical_validation.txt"
        self._write_campaign()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_campaign(self) -> None:
        rows = []
        particles = (("electron", 11), ("photon", 22), ("pion_plus", 211))
        offsets = (-2.0, -1.0, 0.0, 1.0, 2.0)
        for particle, pdg in particles:
            for energy in (1.0, 10.0, 100.0):
                base = energy * 100.0 + pdg / 1000.0
                for repeat, offset in enumerate(offsets, start=1):
                    run = f"{particle}_{int(energy)}gev_seed{repeat}"
                    seed = pdg * 100000 + int(energy) * 10 + repeat
                    rows.append({
                        "run": run,
                        "particle": particle,
                        "pdg": pdg,
                        "kinetic_energy_gev": energy,
                        "events": 2,
                        "seed": seed,
                        "root_sha256": "0" * 64,
                        "git_commit": "a" * 40,
                    })
                    mean = base + offset
                    stddev = math.sqrt(2.0)
                    with (self.directory / f"{run}.summary.csv").open(
                        "w", newline="", encoding="utf-8"
                    ) as stream:
                        writer = csv.DictWriter(
                            stream,
                            fieldnames=(
                                "schema_version", "git_commit", "generator_mode",
                                "single_particle_pdg",
                                "single_particle_kinetic_energy_gev", "single_particle_eta",
                                "single_particle_phi", "event_count", "hit_count",
                                "mean_energy_mev", "sample_stddev_energy_mev",
                                "mean_response", "relative_resolution",
                            ),
                            lineterminator="\n",
                        )
                        writer.writeheader()
                        writer.writerow({
                            "schema_version": 2,
                            "git_commit": "a" * 40,
                            "generator_mode": "single_particle",
                            "single_particle_pdg": pdg,
                            "single_particle_kinetic_energy_gev": energy,
                            "single_particle_eta": 0,
                            "single_particle_phi": 0,
                            "event_count": 2,
                            "hit_count": 20,
                            "mean_energy_mev": mean,
                            "sample_stddev_energy_mev": stddev,
                            "mean_response": mean / (1000.0 * energy),
                            "relative_resolution": stddev / mean,
                        })
                    with (self.directory / f"{run}.samplings.csv").open(
                        "w", newline="", encoding="utf-8"
                    ) as stream:
                        writer = csv.DictWriter(
                            stream,
                            fieldnames=(
                                "sampling", "name", "mean_energy_mev",
                                "sample_stddev_energy_mev", "total_energy_fraction",
                            ),
                            lineterminator="\n",
                        )
                        writer.writeheader()
                        for sampling, name in enumerate(AGGREGATOR.SAMPLING_NAMES):
                            writer.writerow({
                                "sampling": sampling,
                                "name": name,
                                "mean_energy_mev": mean / 10.0,
                                "sample_stddev_energy_mev": stddev / 10.0,
                                "total_energy_fraction": 0.1,
                            })
        with self.manifest.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "run", "particle", "pdg", "kinetic_energy_gev", "events", "seed",
                    "root_sha256", "git_commit",
                ),
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)

    def _run(self) -> None:
        result = AGGREGATOR.main([
            "--manifest", str(self.manifest),
            "--input-dir", str(self.directory),
            "--summary-csv", str(self.summary),
            "--sampling-csv", str(self.samplings),
            "--validation", str(self.validation),
            "--runs-per-point", "5",
            "--events-per-run", "2",
            "--max-relative-ci95-half-width", "0.03",
        ])
        self.assertEqual(result, 0)

    def test_pooled_variance_and_outputs(self) -> None:
        self._run()
        with self.summary.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 9)
        electron = next(
            row for row in rows
            if int(row["pdg"]) == 11 and float(row["kinetic_energy_gev"]) == 1.0
        )
        expected_mean = 100.011
        expected_stddev = math.sqrt(10.0 / 3.0)
        self.assertAlmostEqual(float(electron["mean_energy_mev"]), expected_mean)
        self.assertAlmostEqual(
            float(electron["sample_stddev_energy_mev"]), expected_stddev
        )
        self.assertAlmostEqual(
            float(electron["standard_error_mean_mev"]), math.sqrt(1.0 / 3.0)
        )
        self.assertAlmostEqual(
            float(electron["seed_mean_stddev_mev"]), math.sqrt(2.5)
        )
        with self.samplings.open(newline="", encoding="utf-8") as stream:
            sampling_rows = list(csv.DictReader(stream))
        self.assertEqual(len(sampling_rows), 90)
        self.assertTrue(
            all(math.isclose(float(row["total_energy_fraction"]), 0.1)
                for row in sampling_rows)
        )
        validation = self.validation.read_text(encoding="utf-8")
        self.assertIn("STATISTICAL_AGGREGATION_RESULT=PASS\n", validation)
        self.assertIn("total_events=90\n", validation)

    def test_duplicate_seed_is_rejected_transactionally(self) -> None:
        with self.manifest.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        rows[1]["seed"] = rows[0]["seed"]
        with self.manifest.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=rows[0].keys(), delimiter="\t", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "globally unique"):
            self._run()
        self.assertFalse(self.summary.exists())
        self.assertFalse(self.samplings.exists())
        self.assertFalse(self.validation.exists())


if __name__ == "__main__":
    unittest.main()
