#!/usr/bin/env python3
"""Regression tests for the Cycle 6.6 paired systematic aggregator."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import math
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_DIR / "scripts" / "aggregate_hadronic_tail_systematics.py"
SPEC = importlib.util.spec_from_file_location("hadronic_tail_aggregator", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
AGGREGATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AGGREGATOR
SPEC.loader.exec_module(AGGREGATOR)


class HadronicTailAggregatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.manifest = self.directory / "campaign_manifest.tsv"
        self.summary = self.directory / "systematic_summary.csv"
        self.paired = self.directory / "paired_differences.csv"
        self.validation = self.directory / "systematic_validation.txt"
        self._write_campaign()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_campaign(self) -> None:
        rows = []
        seed_offsets = (-2.0, -1.0, 0.0, 1.0, 2.0)
        for eta in AGGREGATOR.ETA_VALUES:
            for production_cut_mm in AGGREGATOR.PRODUCTION_CUTS_MM:
                cut_index = AGGREGATOR.PRODUCTION_CUTS_MM.index(production_cut_mm) - 1
                for seed, seed_offset in zip(AGGREGATOR.SEEDS, seed_offsets):
                    run = (
                        f"pion_plus_100gev_eta{eta:g}_"
                        f"cut{production_cut_mm:g}mm_seed{seed}"
                    )
                    root_path = self.directory / f"{run}.root"
                    root_path.write_bytes(f"ROOT fixture {run}\n".encode())
                    root_sha256 = hashlib.sha256(root_path.read_bytes()).hexdigest()
                    mean_energy = 50000.0 + seed_offset + 100.0 * eta + 10.0 * cut_index
                    tilecal3 = 0.02 + 0.002 * eta + 0.0005 * cut_index
                    tileext = 0.003 + 0.0003 * eta + 0.0001 * cut_index
                    fractions = [
                        0.02,
                        0.08,
                        0.0,
                        0.15,
                        0.25,
                        0.20,
                        tilecal3,
                        tileext / 3.0,
                        tileext / 3.0,
                        tileext / 3.0,
                    ]
                    fractions[2] = 1.0 - math.fsum(fractions)
                    rows.append({
                        "run": run,
                        "particle": "pion_plus",
                        "pdg": 211,
                        "kinetic_energy_gev": 100,
                        "eta": eta,
                        "production_cut_mm": production_cut_mm,
                        "events": 2,
                        "seed": seed,
                        "root_sha256": root_sha256,
                        "git_commit": "a" * 40,
                    })
                    with (self.directory / f"{run}.summary.csv").open(
                        "w", newline="", encoding="utf-8"
                    ) as stream:
                        writer = csv.DictWriter(
                            stream,
                            fieldnames=(
                                "schema_version",
                                "git_commit",
                                "generator_mode",
                                "single_particle_pdg",
                                "single_particle_kinetic_energy_gev",
                                "single_particle_eta",
                                "single_particle_phi",
                                "production_cut_mm",
                                "event_count",
                                "hit_count",
                                "mean_energy_mev",
                                "sample_stddev_energy_mev",
                                "mean_response",
                                "relative_resolution",
                            ),
                            lineterminator="\n",
                        )
                        writer.writeheader()
                        writer.writerow({
                            "schema_version": 2,
                            "git_commit": "a" * 40,
                            "generator_mode": "single_particle",
                            "single_particle_pdg": 211,
                            "single_particle_kinetic_energy_gev": 100,
                            "single_particle_eta": eta,
                            "single_particle_phi": 0,
                            "production_cut_mm": production_cut_mm,
                            "event_count": 2,
                            "hit_count": 20,
                            "mean_energy_mev": mean_energy,
                            "sample_stddev_energy_mev": 1000,
                            "mean_response": mean_energy / 100000.0,
                            "relative_resolution": 1000.0 / mean_energy,
                        })
                    with (self.directory / f"{run}.samplings.csv").open(
                        "w", newline="", encoding="utf-8"
                    ) as stream:
                        writer = csv.DictWriter(
                            stream,
                            fieldnames=(
                                "sampling",
                                "name",
                                "mean_energy_mev",
                                "sample_stddev_energy_mev",
                                "total_energy_fraction",
                            ),
                            lineterminator="\n",
                        )
                        writer.writeheader()
                        for sampling, (name, fraction) in enumerate(
                            zip(AGGREGATOR.SAMPLING_NAMES, fractions)
                        ):
                            writer.writerow({
                                "sampling": sampling,
                                "name": name,
                                "mean_energy_mev": mean_energy * fraction,
                                "sample_stddev_energy_mev": 10,
                                "total_energy_fraction": fraction,
                            })
        with self.manifest.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "run",
                    "particle",
                    "pdg",
                    "kinetic_energy_gev",
                    "eta",
                    "production_cut_mm",
                    "events",
                    "seed",
                    "root_sha256",
                    "git_commit",
                ),
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)

    def _run(self) -> None:
        result = AGGREGATOR.main([
            "--manifest",
            str(self.manifest),
            "--input-dir",
            str(self.directory),
            "--summary-csv",
            str(self.summary),
            "--paired-csv",
            str(self.paired),
            "--validation",
            str(self.validation),
            "--events-per-run",
            "2",
        ])
        self.assertEqual(result, 0)

    def _rewrite_manifest(self, rows: list[dict[str, str]]) -> None:
        with self.manifest.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=rows[0].keys(),
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)

    def test_paired_outputs_and_review_markers(self) -> None:
        self._run()
        with self.summary.open(newline="", encoding="utf-8") as stream:
            point_rows = list(csv.DictReader(stream))
        with self.paired.open(newline="", encoding="utf-8") as stream:
            paired_rows = list(csv.DictReader(stream))
        self.assertEqual(len(point_rows), 9)
        self.assertEqual(len(paired_rows), 8)
        eta04 = next(
            row
            for row in paired_rows
            if float(row["eta"]) == 0.4
            and float(row["production_cut_mm"]) == 1.0
        )
        self.assertAlmostEqual(float(eta04["mean_delta_energy_mev"]), 40.0)
        self.assertAlmostEqual(
            float(eta04["mean_delta_tilecal3_fraction"]), 0.0008
        )
        self.assertEqual(eta04["tilecal3_significant"], "true")
        validation = self.validation.read_text(encoding="utf-8")
        self.assertIn("HADRONIC_TAIL_AGGREGATION_RESULT=PASS\n", validation)
        self.assertIn("root_sha256_integrity=PASS\n", validation)
        self.assertIn("paired_seed_coverage=PASS\n", validation)
        self.assertIn("systematic_review=REQUIRED\n", validation)

    def test_unpaired_seed_is_rejected_transactionally(self) -> None:
        with self.manifest.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        rows[1]["seed"] = rows[0]["seed"]
        self._rewrite_manifest(rows)
        with self.assertRaisesRegex(ValueError, "paired seed set"):
            self._run()
        self.assertFalse(self.summary.exists())
        self.assertFalse(self.paired.exists())
        self.assertFalse(self.validation.exists())

    def test_root_hash_mismatch_is_rejected_transactionally(self) -> None:
        with self.manifest.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        rows[0]["root_sha256"] = "0" * 64
        self._rewrite_manifest(rows)
        with self.assertRaisesRegex(ValueError, "ROOT SHA-256 mismatch"):
            self._run()
        self.assertFalse(self.summary.exists())
        self.assertFalse(self.paired.exists())
        self.assertFalse(self.validation.exists())

    def test_fraction_mismatch_is_rejected_transactionally(self) -> None:
        with self.manifest.open(newline="", encoding="utf-8") as stream:
            first = next(csv.DictReader(stream, delimiter="\t"))
        sampling_path = self.directory / f"{first['run']}.samplings.csv"
        with sampling_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        rows[0]["total_energy_fraction"] = "0.5"
        with sampling_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=rows[0].keys(), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "fractions do not sum to one"):
            self._run()
        self.assertFalse(self.summary.exists())
        self.assertFalse(self.paired.exists())
        self.assertFalse(self.validation.exists())


if __name__ == "__main__":
    unittest.main()
