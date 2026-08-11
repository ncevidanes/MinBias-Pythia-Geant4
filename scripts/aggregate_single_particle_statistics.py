#!/usr/bin/env python3
"""Aggregate independent single-particle runs without reopening ROOT files."""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


Z_975 = 1.959963984540054
EXPECTED_POINTS = {
    (pdg, energy)
    for pdg in (11, 22, 211)
    for energy in (1.0, 10.0, 100.0)
}
EXPECTED_PARTICLES = {11: "electron", 22: "photon", 211: "pion_plus"}
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


@dataclass(frozen=True)
class Moments:
    count: int
    mean: float
    sample_stddev: float


@dataclass(frozen=True)
class Run:
    name: str
    particle: str
    pdg: int
    energy_gev: float
    events: int
    seed: int
    hit_count: int
    git_commit: str
    mean_energy_mev: float
    sample_stddev_energy_mev: float
    samplings: tuple[Moments, ...]


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


def nearly_equal(first: float, second: float, tolerance: float = 1.0e-12) -> bool:
    return math.isclose(first, second, rel_tol=tolerance, abs_tol=tolerance)


def load_run(manifest: dict[str, str], input_dir: Path) -> Run:
    required_manifest = (
        "run", "particle", "pdg", "kinetic_energy_gev", "events", "seed",
        "root_sha256", "git_commit",
    )
    for field in required_manifest:
        if not manifest.get(field):
            raise ValueError(f"empty manifest field {field!r}")

    name = manifest["run"]
    if Path(name).name != name:
        raise ValueError(f"unsafe run name: {name!r}")
    pdg = int(manifest["pdg"])
    energy_gev = finite_float(manifest["kinetic_energy_gev"], f"{name} energy")
    events = positive_int(manifest["events"], f"{name} events")
    seed = positive_int(manifest["seed"], f"{name} seed")
    if manifest["particle"] != EXPECTED_PARTICLES.get(pdg):
        raise ValueError(f"particle label does not match PDG for run {name}")
    if re.fullmatch(r"[0-9a-f]{64}", manifest["root_sha256"]) is None:
        raise ValueError(f"invalid ROOT SHA-256 for run {name}")
    if re.fullmatch(r"[0-9a-f]{40}", manifest["git_commit"]) is None:
        raise ValueError(f"invalid Git commit for run {name}")
    summary_path = input_dir / f"{name}.summary.csv"
    sampling_path = input_dir / f"{name}.samplings.csv"

    summary = read_one_row(
        summary_path,
        (
            "schema_version", "git_commit", "generator_mode", "single_particle_pdg",
            "single_particle_kinetic_energy_gev", "single_particle_eta",
            "single_particle_phi", "event_count", "hit_count",
            "mean_energy_mev", "sample_stddev_energy_mev", "mean_response",
            "relative_resolution",
        ),
    )
    if int(summary["schema_version"]) != 2:
        raise ValueError(f"unsupported schema version in {summary_path}")
    if summary["generator_mode"] != "single_particle":
        raise ValueError(f"unexpected generator mode in {summary_path}")
    if int(summary["single_particle_pdg"]) != pdg:
        raise ValueError(f"PDG mismatch in {summary_path}")
    if not nearly_equal(
        finite_float(summary["single_particle_kinetic_energy_gev"], "summary energy"),
        energy_gev,
    ):
        raise ValueError(f"energy mismatch in {summary_path}")
    if not nearly_equal(finite_float(summary["single_particle_eta"], "eta"), 0.0):
        raise ValueError(f"eta must be zero in {summary_path}")
    if not nearly_equal(finite_float(summary["single_particle_phi"], "phi"), 0.0):
        raise ValueError(f"phi must be zero in {summary_path}")
    if positive_int(summary["event_count"], "summary event_count") != events:
        raise ValueError(f"event count mismatch in {summary_path}")
    if summary["git_commit"] != manifest["git_commit"]:
        raise ValueError(f"Git commit mismatch in {summary_path}")

    hit_count = positive_int(summary["hit_count"], "hit_count")
    mean = finite_float(summary["mean_energy_mev"], "mean energy", nonnegative=True)
    stddev = finite_float(
        summary["sample_stddev_energy_mev"], "sample standard deviation",
        nonnegative=True,
    )
    if mean <= 0.0:
        raise ValueError(f"mean energy must be positive in {summary_path}")
    response = finite_float(summary["mean_response"], "mean response", nonnegative=True)
    resolution = finite_float(
        summary["relative_resolution"], "relative resolution", nonnegative=True,
    )
    if not nearly_equal(response, mean / (1000.0 * energy_gev)):
        raise ValueError(f"inconsistent response in {summary_path}")
    if not nearly_equal(resolution, stddev / mean):
        raise ValueError(f"inconsistent relative resolution in {summary_path}")

    with sampling_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        require_columns(
            reader,
            ("sampling", "name", "mean_energy_mev", "sample_stddev_energy_mev",
             "total_energy_fraction"),
            sampling_path,
        )
        sampling_rows = list(reader)
    if len(sampling_rows) != len(SAMPLING_NAMES):
        raise ValueError(f"expected ten sampling rows in {sampling_path}")

    samplings: list[Moments] = []
    sampling_mean_sum = 0.0
    fraction_sum = 0.0
    for index, (row, expected_name) in enumerate(zip(sampling_rows, SAMPLING_NAMES)):
        if int(row["sampling"]) != index or row["name"] != expected_name:
            raise ValueError(f"unexpected sampling row {index} in {sampling_path}")
        sampling_mean = finite_float(
            row["mean_energy_mev"], "sampling mean", nonnegative=True,
        )
        sampling_stddev = finite_float(
            row["sample_stddev_energy_mev"], "sampling stddev", nonnegative=True,
        )
        fraction = finite_float(
            row["total_energy_fraction"], "sampling fraction", nonnegative=True,
        )
        sampling_mean_sum += sampling_mean
        fraction_sum += fraction
        samplings.append(Moments(events, sampling_mean, sampling_stddev))
    if not nearly_equal(sampling_mean_sum, mean, 1.0e-9):
        raise ValueError(f"sampling means do not sum to total mean in {sampling_path}")
    if not nearly_equal(fraction_sum, 1.0, 1.0e-9):
        raise ValueError(f"sampling fractions do not sum to one in {sampling_path}")

    return Run(
        name=name,
        particle=manifest["particle"],
        pdg=pdg,
        energy_gev=energy_gev,
        events=events,
        seed=seed,
        hit_count=hit_count,
        git_commit=manifest["git_commit"],
        mean_energy_mev=mean,
        sample_stddev_energy_mev=stddev,
        samplings=tuple(samplings),
    )


def pool(moments: Sequence[Moments]) -> Moments:
    count = sum(item.count for item in moments)
    if count < 2:
        raise ValueError("at least two observations are required")
    mean = sum(item.count * item.mean for item in moments) / count
    sum_squares = sum(
        (item.count - 1) * item.sample_stddev**2
        + item.count * (item.mean - mean) ** 2
        for item in moments
    )
    return Moments(count, mean, math.sqrt(max(0.0, sum_squares / (count - 1))))


def sample_stddev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def format_value(value: object) -> object:
    return format(value, ".17g") if isinstance(value, float) else value


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    max_relative_half_width: float,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str]]:
    with manifest_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        require_columns(
            reader,
            ("run", "particle", "pdg", "kinetic_energy_gev", "events", "seed",
             "root_sha256", "git_commit"),
            manifest_path,
        )
        manifest_rows = list(reader)
    runs = [load_run(row, input_dir) for row in manifest_rows]
    if len({run.name for run in runs}) != len(runs):
        raise ValueError("manifest contains duplicate run names")
    if len({run.seed for run in runs}) != len(runs):
        raise ValueError("campaign seeds must be globally unique")
    if len({run.git_commit for run in runs}) != 1:
        raise ValueError("campaign spans multiple Git commits")

    groups: dict[tuple[int, float], list[Run]] = defaultdict(list)
    for run in runs:
        if run.events != events_per_run:
            raise ValueError(f"unexpected event count for run {run.name}")
        groups[(run.pdg, run.energy_gev)].append(run)
    if set(groups) != EXPECTED_POINTS:
        raise ValueError("campaign does not contain the fixed nine-point matrix")

    point_rows: list[dict[str, object]] = []
    sampling_rows: list[dict[str, object]] = []
    max_observed_half_width = 0.0
    means_by_particle: dict[int, list[tuple[float, float]]] = defaultdict(list)

    for point in sorted(groups):
        point_runs = groups[point]
        if len(point_runs) != runs_per_point:
            raise ValueError(f"point {point} has {len(point_runs)} runs")
        if len({run.seed for run in point_runs}) != runs_per_point:
            raise ValueError(f"point {point} does not have unique seeds")
        if len({run.particle for run in point_runs}) != 1:
            raise ValueError(f"point {point} has inconsistent particle labels")
        if len({run.git_commit for run in point_runs}) != 1:
            raise ValueError(f"point {point} spans multiple Git commits")

        pooled = pool([
            Moments(run.events, run.mean_energy_mev, run.sample_stddev_energy_mev)
            for run in point_runs
        ])
        standard_error = pooled.sample_stddev / math.sqrt(pooled.count)
        half_width = Z_975 * standard_error
        relative_half_width = half_width / pooled.mean
        max_observed_half_width = max(max_observed_half_width, relative_half_width)
        seed_stddev = sample_stddev([run.mean_energy_mev for run in point_runs])
        means_by_particle[point[0]].append((point[1], pooled.mean))
        point_rows.append({
            "git_commit": point_runs[0].git_commit,
            "particle": point_runs[0].particle,
            "pdg": point[0],
            "kinetic_energy_gev": point[1],
            "runs": len(point_runs),
            "events": pooled.count,
            "hits": sum(run.hit_count for run in point_runs),
            "mean_energy_mev": pooled.mean,
            "sample_stddev_energy_mev": pooled.sample_stddev,
            "mean_response": pooled.mean / (1000.0 * point[1]),
            "relative_resolution": pooled.sample_stddev / pooled.mean,
            "standard_error_mean_mev": standard_error,
            "ci95_low_mev": pooled.mean - half_width,
            "ci95_high_mev": pooled.mean + half_width,
            "relative_ci95_half_width": relative_half_width,
            "seed_mean_stddev_mev": seed_stddev,
            "seed_mean_cv": seed_stddev / pooled.mean,
        })

        for sampling, name in enumerate(SAMPLING_NAMES):
            sampling_pooled = pool([run.samplings[sampling] for run in point_runs])
            sampling_rows.append({
                "git_commit": point_runs[0].git_commit,
                "particle": point_runs[0].particle,
                "pdg": point[0],
                "kinetic_energy_gev": point[1],
                "sampling": sampling,
                "name": name,
                "runs": len(point_runs),
                "events": sampling_pooled.count,
                "mean_energy_mev": sampling_pooled.mean,
                "sample_stddev_energy_mev": sampling_pooled.sample_stddev,
                "total_energy_fraction": sampling_pooled.mean / pooled.mean,
                "seed_mean_stddev_mev": sample_stddev(
                    [run.samplings[sampling].mean for run in point_runs]
                ),
            })

    for pdg, points in means_by_particle.items():
        means = [mean for _, mean in sorted(points)]
        if not means[0] < means[1] < means[2]:
            raise ValueError(f"mean deposit is not monotonic for PDG {pdg}")
    if max_observed_half_width > max_relative_half_width:
        raise ValueError(
            "relative CI95 half-width exceeds limit: "
            f"{max_observed_half_width:.17g} > {max_relative_half_width:.17g}"
        )

    validation = [
        "STATISTICAL_AGGREGATION_RESULT=PASS",
        f"physical_points={len(point_rows)}",
        f"runs={len(runs)}",
        f"runs_per_point={runs_per_point}",
        f"events_per_run={events_per_run}",
        f"total_events={sum(run.events for run in runs)}",
        f"sampling_rows={len(sampling_rows)}",
        "confidence_level=0.95",
        "confidence_method=normal_approximation",
        f"max_relative_ci95_half_width={max_observed_half_width:.17g}",
        f"required_max_relative_ci95_half_width={max_relative_half_width:.17g}",
        "ci95_precision=PASS",
        "unique_seeds_per_point=true",
        "unique_seeds_global=true",
        "mean_deposit_monotonic_by_particle=true",
    ]
    return point_rows, sampling_rows, validation


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--summary-csv", required=True, type=Path)
    parser.add_argument("--sampling-csv", required=True, type=Path)
    parser.add_argument("--validation", required=True, type=Path)
    parser.add_argument("--runs-per-point", type=int, default=5)
    parser.add_argument("--events-per-run", type=int, default=200)
    parser.add_argument("--max-relative-ci95-half-width", type=float, default=0.03)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    outputs = (args.summary_csv, args.sampling_csv, args.validation)
    if len({path.resolve() for path in outputs}) != len(outputs):
        raise ValueError("output paths must be distinct")
    for path in outputs:
        if path.exists():
            raise ValueError(f"output already exists: {path}")
    if args.runs_per_point < 2 or args.events_per_run < 2:
        raise ValueError("at least two runs and two events per run are required")
    if not math.isfinite(args.max_relative_ci95_half_width) or not (
        0.0 < args.max_relative_ci95_half_width < 1.0
    ):
        raise ValueError("CI95 half-width limit must be between zero and one")

    point_rows, sampling_rows, validation = aggregate(
        args.manifest,
        args.input_dir,
        args.runs_per_point,
        args.events_per_run,
        args.max_relative_ci95_half_width,
    )
    fieldnames = list(point_rows[0])
    sampling_fieldnames = list(sampling_rows[0])
    temporary_paths: list[Path] = []
    try:
        for final_path, kind in zip(outputs, ("points", "samplings", "validation")):
            final_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{final_path.name}.{kind}.", dir=final_path.parent,
            )
            os.close(descriptor)
            temporary_paths.append(Path(temporary_name))
        write_csv(temporary_paths[0], fieldnames, point_rows)
        write_csv(temporary_paths[1], sampling_fieldnames, sampling_rows)
        temporary_paths[2].write_text("\n".join(validation) + "\n", encoding="utf-8")
        for temporary_path in temporary_paths:
            temporary_path.chmod(0o644)
        for temporary_path, final_path in zip(temporary_paths, outputs):
            os.replace(temporary_path, final_path)
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)

    print(
        f"STATISTICAL_AGGREGATION_RESULT=PASS points={len(point_rows)} "
        f"runs={len(point_rows) * args.runs_per_point}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("STATISTICAL_AGGREGATION_RESULT=FAIL", file=sys.stderr)
        raise SystemExit(1)
