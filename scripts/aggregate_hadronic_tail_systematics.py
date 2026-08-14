#!/usr/bin/env python3
"""Aggregate the fixed Cycle 6.6 paired hadronic-tail systematic campaign."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import os
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


ETA_VALUES = (0.0, 0.4, 0.8)
PRODUCTION_CUTS_MM = (0.1, 1.0, 10.0)
SEEDS = (643031, 643032, 643033, 643034, 643035)
EXPECTED_POINTS = {
    (eta, production_cut_mm)
    for eta in ETA_VALUES
    for production_cut_mm in PRODUCTION_CUTS_MM
}
BASELINE_POINT = (0.0, 1.0)
PARTICLE = "pion_plus"
PDG = 211
KINETIC_ENERGY_GEV = 100.0
SAMPLING_NAMES = (
    "PSB",
    "EMB1",
    "EMB2",
    "EMB3",
    "TileCal1",
    "TileCal2",
    "TileCal3",
    "TileExt1",
    "TileExt2",
    "TileExt3",
)
T_975_DF4 = 2.7764451051977987


@dataclass(frozen=True)
class Run:
    name: str
    eta: float
    production_cut_mm: float
    events: int
    seed: int
    git_commit: str
    hit_count: int
    mean_energy_mev: float
    fractions: tuple[float, ...]

    @property
    def tilecal3_fraction(self) -> float:
        return self.fractions[6]

    @property
    def tileext_fraction(self) -> float:
        return math.fsum(self.fractions[7:10])


def finite_float(value: str, description: str, *, nonnegative: bool = False) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(f"{description} is not a number: {value!r}") from error
    if not math.isfinite(parsed):
        raise ValueError(f"{description} must be finite")
    if nonnegative and parsed < 0.0:
        raise ValueError(f"{description} must be non-negative")
    return parsed


def positive_int(value: str, description: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{description} is not an integer: {value!r}") from error
    if parsed <= 0:
        raise ValueError(f"{description} must be positive")
    return parsed


def require_columns(reader: csv.DictReader, required: Iterable[str], path: Path) -> None:
    missing = set(required) - set(reader.fieldnames or ())
    if missing:
        raise ValueError(f"missing columns in {path}: {', '.join(sorted(missing))}")


def read_one_row(path: Path, required: Iterable[str]) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        require_columns(reader, required, path)
        rows = list(reader)
    if len(rows) != 1:
        raise ValueError(f"expected exactly one data row in {path}")
    return rows[0]


def canonical_value(value: float, allowed: Sequence[float], description: str) -> float:
    matches = [
        expected
        for expected in allowed
        if math.isclose(value, expected, rel_tol=0.0, abs_tol=1.0e-12)
    ]
    if len(matches) != 1:
        raise ValueError(f"unexpected {description}: {value:.17g}")
    return matches[0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def nearly_equal(first: float, second: float, tolerance: float = 1.0e-9) -> bool:
    return math.isclose(first, second, rel_tol=tolerance, abs_tol=tolerance)


def load_run(manifest: dict[str, str], input_dir: Path) -> Run:
    required_manifest = (
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
    )
    for field in required_manifest:
        if not manifest.get(field):
            raise ValueError(f"empty manifest field {field!r}")

    name = manifest["run"]
    if Path(name).name != name:
        raise ValueError(f"unsafe run name: {name!r}")
    if manifest["particle"] != PARTICLE or int(manifest["pdg"]) != PDG:
        raise ValueError(f"unexpected particle contract for {name}")
    energy = finite_float(manifest["kinetic_energy_gev"], f"{name} energy")
    if not math.isclose(energy, KINETIC_ENERGY_GEV, rel_tol=0.0, abs_tol=1.0e-12):
        raise ValueError(f"unexpected kinetic energy for {name}")
    eta = canonical_value(
        finite_float(manifest["eta"], f"{name} eta"), ETA_VALUES, f"eta for {name}"
    )
    production_cut_mm = canonical_value(
        finite_float(manifest["production_cut_mm"], f"{name} production cut"),
        PRODUCTION_CUTS_MM,
        f"production cut for {name}",
    )
    events = positive_int(manifest["events"], f"{name} events")
    seed = positive_int(manifest["seed"], f"{name} seed")
    if seed not in SEEDS:
        raise ValueError(f"unexpected paired seed for {name}: {seed}")
    git_commit = manifest["git_commit"]
    if len(git_commit) != 40 or any(
        character not in "0123456789abcdef" for character in git_commit
    ):
        raise ValueError(f"invalid Git commit for {name}")

    expected_root_hash = manifest["root_sha256"]
    if len(expected_root_hash) != 64 or any(
        character not in "0123456789abcdef" for character in expected_root_hash
    ):
        raise ValueError(f"invalid ROOT SHA-256 for {name}")
    root_path = input_dir / f"{name}.root"
    if not root_path.is_file() or root_path.stat().st_size == 0:
        raise ValueError(f"ROOT input is absent or empty: {root_path}")
    if sha256(root_path) != expected_root_hash:
        raise ValueError(f"ROOT SHA-256 mismatch for {name}")

    summary_path = input_dir / f"{name}.summary.csv"
    summary = read_one_row(
        summary_path,
        (
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
    )
    if int(summary["schema_version"]) != 2:
        raise ValueError(f"unexpected schema in {summary_path}")
    if summary["git_commit"] != git_commit:
        raise ValueError(f"Git provenance mismatch in {summary_path}")
    if summary["generator_mode"] != "single_particle":
        raise ValueError(f"unexpected generator mode in {summary_path}")
    if int(summary["single_particle_pdg"]) != PDG:
        raise ValueError(f"PDG mismatch in {summary_path}")
    summary_energy = finite_float(
        summary["single_particle_kinetic_energy_gev"], "summary energy"
    )
    summary_eta = finite_float(summary["single_particle_eta"], "summary eta")
    summary_phi = finite_float(summary["single_particle_phi"], "summary phi")
    summary_cut = finite_float(summary["production_cut_mm"], "summary production cut")
    if not nearly_equal(summary_energy, energy) or not nearly_equal(summary_eta, eta):
        raise ValueError(f"incident-particle metadata mismatch in {summary_path}")
    if not nearly_equal(summary_phi, 0.0) or not nearly_equal(
        summary_cut, production_cut_mm
    ):
        raise ValueError(f"systematic metadata mismatch in {summary_path}")
    if positive_int(summary["event_count"], "summary event count") != events:
        raise ValueError(f"event count mismatch in {summary_path}")
    hit_count = positive_int(summary["hit_count"], "summary hit count")
    mean_energy_mev = finite_float(
        summary["mean_energy_mev"], "mean energy", nonnegative=True
    )
    if mean_energy_mev <= 0.0:
        raise ValueError(f"mean energy must be positive in {summary_path}")
    for field in ("sample_stddev_energy_mev", "relative_resolution"):
        finite_float(summary[field], field, nonnegative=True)
    if finite_float(summary["mean_response"], "mean response", nonnegative=True) <= 0.0:
        raise ValueError(f"mean response must be positive in {summary_path}")

    sampling_path = input_dir / f"{name}.samplings.csv"
    with sampling_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        require_columns(
            reader,
            (
                "sampling",
                "name",
                "mean_energy_mev",
                "sample_stddev_energy_mev",
                "total_energy_fraction",
            ),
            sampling_path,
        )
        sampling_rows = list(reader)
    if len(sampling_rows) != len(SAMPLING_NAMES):
        raise ValueError(f"expected ten sampling rows in {sampling_path}")

    sampling_means: list[float] = []
    fractions: list[float] = []
    for index, (row, expected_name) in enumerate(zip(sampling_rows, SAMPLING_NAMES)):
        if int(row["sampling"]) != index or row["name"] != expected_name:
            raise ValueError(f"unexpected sampling row {index} in {sampling_path}")
        sampling_means.append(
            finite_float(row["mean_energy_mev"], "sampling mean", nonnegative=True)
        )
        finite_float(
            row["sample_stddev_energy_mev"],
            "sampling standard deviation",
            nonnegative=True,
        )
        fractions.append(
            finite_float(
                row["total_energy_fraction"], "sampling fraction", nonnegative=True
            )
        )
    if not nearly_equal(math.fsum(sampling_means), mean_energy_mev):
        raise ValueError(f"sampling means do not sum to total mean in {sampling_path}")
    if not nearly_equal(math.fsum(fractions), 1.0):
        raise ValueError(f"sampling fractions do not sum to one in {sampling_path}")

    return Run(
        name=name,
        eta=eta,
        production_cut_mm=production_cut_mm,
        events=events,
        seed=seed,
        git_commit=git_commit,
        hit_count=hit_count,
        mean_energy_mev=mean_energy_mev,
        fractions=tuple(fractions),
    )


def mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("at least one value is required")
    return math.fsum(values) / len(values)


def sample_stddev(values: Sequence[float]) -> float:
    if len(values) < 2:
        raise ValueError("at least two values are required")
    average = mean(values)
    return math.sqrt(
        math.fsum((value - average) ** 2 for value in values) / (len(values) - 1)
    )


def confidence(values: Sequence[float]) -> tuple[float, float, float, float]:
    average = mean(values)
    standard_deviation = sample_stddev(values)
    half_width = T_975_DF4 * standard_deviation / math.sqrt(len(values))
    return average, standard_deviation, half_width, average - half_width


def significant_interval(low: float, high: float) -> bool:
    return low > 0.0 or high < 0.0


def format_value(value: object) -> object:
    if isinstance(value, bool):
        return str(value).lower()
    return format(value, ".17g") if isinstance(value, float) else value


def write_csv(
    path: Path, fieldnames: Sequence[str], rows: Sequence[dict[str, object]]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            {key: format_value(value) for key, value in row.items()} for row in rows
        )


def aggregate(
    manifest_path: Path,
    input_dir: Path,
    runs_per_point: int,
    events_per_run: int,
    precision_review_threshold: float,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str]]:
    with manifest_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        require_columns(
            reader,
            (
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
            manifest_path,
        )
        manifest_rows = list(reader)

    runs = [load_run(row, input_dir) for row in manifest_rows]
    if len({run.name for run in runs}) != len(runs):
        raise ValueError("manifest contains duplicate run names")
    if len({run.git_commit for run in runs}) != 1:
        raise ValueError("campaign spans multiple Git commits")
    groups: dict[tuple[float, float], list[Run]] = defaultdict(list)
    for run in runs:
        if run.events != events_per_run:
            raise ValueError(f"unexpected event count for run {run.name}")
        groups[(run.eta, run.production_cut_mm)].append(run)
    if set(groups) != EXPECTED_POINTS:
        raise ValueError("campaign does not contain the fixed nine-point matrix")

    ordered_groups: dict[tuple[float, float], list[Run]] = {}
    for point in sorted(groups):
        point_runs = sorted(groups[point], key=lambda run: run.seed)
        if len(point_runs) != runs_per_point:
            raise ValueError(f"point {point} has {len(point_runs)} runs")
        if tuple(run.seed for run in point_runs) != SEEDS:
            raise ValueError(f"point {point} does not contain the paired seed set")
        ordered_groups[point] = point_runs

    point_rows: list[dict[str, object]] = []
    precision_review_points = 0
    max_relative_half_width = 0.0
    for point in sorted(ordered_groups):
        point_runs = ordered_groups[point]
        energy = confidence([run.mean_energy_mev for run in point_runs])
        tilecal3 = confidence([run.tilecal3_fraction for run in point_runs])
        tileext = confidence([run.tileext_fraction for run in point_runs])
        relative_half_width = energy[2] / energy[0]
        max_relative_half_width = max(max_relative_half_width, relative_half_width)
        precision_review = relative_half_width > precision_review_threshold
        precision_review_points += int(precision_review)
        point_rows.append({
            "git_commit": point_runs[0].git_commit,
            "particle": PARTICLE,
            "pdg": PDG,
            "kinetic_energy_gev": KINETIC_ENERGY_GEV,
            "eta": point[0],
            "production_cut_mm": point[1],
            "runs": len(point_runs),
            "events": sum(run.events for run in point_runs),
            "hits": sum(run.hit_count for run in point_runs),
            "mean_energy_mev": energy[0],
            "seed_stddev_energy_mev": energy[1],
            "ci95_half_width_energy_mev": energy[2],
            "relative_ci95_half_width_energy": relative_half_width,
            "tilecal3_fraction": tilecal3[0],
            "seed_stddev_tilecal3_fraction": tilecal3[1],
            "ci95_half_width_tilecal3_fraction": tilecal3[2],
            "tileext_fraction": tileext[0],
            "seed_stddev_tileext_fraction": tileext[1],
            "ci95_half_width_tileext_fraction": tileext[2],
            "precision_review": precision_review,
        })

    baseline = {run.seed: run for run in ordered_groups[BASELINE_POINT]}
    paired_rows: list[dict[str, object]] = []
    significant_tilecal3_points = 0
    significant_tileext_points = 0
    for point in sorted(ordered_groups):
        if point == BASELINE_POINT:
            continue
        point_by_seed = {run.seed: run for run in ordered_groups[point]}
        energy_differences = [
            point_by_seed[seed].mean_energy_mev - baseline[seed].mean_energy_mev
            for seed in SEEDS
        ]
        tilecal3_differences = [
            point_by_seed[seed].tilecal3_fraction - baseline[seed].tilecal3_fraction
            for seed in SEEDS
        ]
        tileext_differences = [
            point_by_seed[seed].tileext_fraction - baseline[seed].tileext_fraction
            for seed in SEEDS
        ]
        energy = confidence(energy_differences)
        tilecal3 = confidence(tilecal3_differences)
        tileext = confidence(tileext_differences)
        tilecal3_high = tilecal3[0] + tilecal3[2]
        tileext_high = tileext[0] + tileext[2]
        tilecal3_significant = significant_interval(tilecal3[3], tilecal3_high)
        tileext_significant = significant_interval(tileext[3], tileext_high)
        significant_tilecal3_points += int(tilecal3_significant)
        significant_tileext_points += int(tileext_significant)
        paired_rows.append({
            "git_commit": ordered_groups[point][0].git_commit,
            "baseline_eta": BASELINE_POINT[0],
            "baseline_production_cut_mm": BASELINE_POINT[1],
            "eta": point[0],
            "production_cut_mm": point[1],
            "paired_seeds": len(SEEDS),
            "mean_delta_energy_mev": energy[0],
            "ci95_low_delta_energy_mev": energy[3],
            "ci95_high_delta_energy_mev": energy[0] + energy[2],
            "mean_delta_tilecal3_fraction": tilecal3[0],
            "ci95_low_delta_tilecal3_fraction": tilecal3[3],
            "ci95_high_delta_tilecal3_fraction": tilecal3_high,
            "tilecal3_significant": tilecal3_significant,
            "mean_delta_tileext_fraction": tileext[0],
            "ci95_low_delta_tileext_fraction": tileext[3],
            "ci95_high_delta_tileext_fraction": tileext_high,
            "tileext_significant": tileext_significant,
        })

    systematic_review = (
        significant_tilecal3_points > 0 or significant_tileext_points > 0
    )
    validation = [
        "HADRONIC_TAIL_AGGREGATION_RESULT=PASS",
        f"physical_points={len(point_rows)}",
        f"runs={len(runs)}",
        f"runs_per_point={runs_per_point}",
        f"events_per_run={events_per_run}",
        f"total_events={sum(run.events for run in runs)}",
        f"sampling_rows={len(runs) * len(SAMPLING_NAMES)}",
        f"paired_seed_count={len(SEEDS)}",
        "baseline_eta=0",
        "baseline_production_cut_mm=1",
        "confidence_level=0.95",
        "confidence_method=paired_t_df4",
        "fraction_closure=PASS",
        "root_sha256_integrity=PASS",
        "paired_seed_coverage=PASS",
        f"max_relative_ci95_half_width_energy={max_relative_half_width:.17g}",
        f"precision_review_threshold={precision_review_threshold:.17g}",
        f"precision_review_points={precision_review_points}",
        f"precision_review={'REQUIRED' if precision_review_points else 'NONE'}",
        f"significant_tilecal3_points={significant_tilecal3_points}",
        f"significant_tileext_points={significant_tileext_points}",
        f"systematic_review={'REQUIRED' if systematic_review else 'NONE'}",
    ]
    return point_rows, paired_rows, validation


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--summary-csv", required=True, type=Path)
    parser.add_argument("--paired-csv", required=True, type=Path)
    parser.add_argument("--validation", required=True, type=Path)
    parser.add_argument("--runs-per-point", type=int, default=5)
    parser.add_argument("--events-per-run", type=int, default=200)
    parser.add_argument("--precision-review-threshold", type=float, default=0.03)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    outputs = (args.summary_csv, args.paired_csv, args.validation)
    if len({path.resolve() for path in outputs}) != len(outputs):
        raise ValueError("output paths must be distinct")
    for path in outputs:
        if path.exists():
            raise ValueError(f"output already exists: {path}")
    if args.runs_per_point != len(SEEDS) or args.events_per_run < 2:
        raise ValueError("fixed campaign requires five runs and at least two events")
    if not math.isfinite(args.precision_review_threshold) or not (
        0.0 < args.precision_review_threshold < 1.0
    ):
        raise ValueError("precision review threshold must be between zero and one")

    point_rows, paired_rows, validation = aggregate(
        args.manifest,
        args.input_dir,
        args.runs_per_point,
        args.events_per_run,
        args.precision_review_threshold,
    )
    temporary_paths: list[Path] = []
    try:
        for final_path in outputs:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{final_path.name}.", dir=final_path.parent
            )
            os.close(descriptor)
            temporary_paths.append(Path(temporary_name))
        write_csv(temporary_paths[0], list(point_rows[0]), point_rows)
        write_csv(temporary_paths[1], list(paired_rows[0]), paired_rows)
        temporary_paths[2].write_text("\n".join(validation) + "\n", encoding="utf-8")
        for temporary_path in temporary_paths:
            temporary_path.chmod(0o644)
        for temporary_path, final_path in zip(temporary_paths, outputs):
            os.replace(temporary_path, final_path)
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)

    print(
        "HADRONIC_TAIL_AGGREGATION_RESULT=PASS "
        f"points={len(point_rows)} runs={len(point_rows) * args.runs_per_point} "
        f"paired_comparisons={len(paired_rows)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("HADRONIC_TAIL_AGGREGATION_RESULT=FAIL", file=sys.stderr)
        raise SystemExit(1)
