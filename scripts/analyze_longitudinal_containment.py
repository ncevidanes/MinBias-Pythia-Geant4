#!/usr/bin/env python3
"""Derive operational longitudinal-containment metrics from Cycle 6.4 evidence."""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence


EXPECTED_POINTS = {
    (pdg, energy)
    for pdg in (11, 22, 211)
    for energy in (1.0, 10.0, 100.0)
}
EXPECTED_PARTICLES = {11: "electron", 22: "photon", 211: "pion_plus"}
EXPECTED_RUNS_PER_POINT = 5
EXPECTED_EVENTS_PER_POINT = 1000
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
CENTRAL_PATH = tuple(range(7))
GROUPS = {
    "psb_fraction": (0,),
    "emb_fraction": (1, 2, 3),
    "em_total_fraction": (0, 1, 2, 3),
    "tile_central_fraction": (4, 5, 6),
    "tile_extended_fraction": (7, 8, 9),
    "central_path_fraction": CENTRAL_PATH,
    "tilecal3_outer_fraction": (6,),
}
CONTAINMENT_THRESHOLDS = (
    (0.90, "containment_90_sampling", "containment_90_index"),
    (0.95, "containment_95_sampling", "containment_95_index"),
    (0.99, "containment_99_sampling", "containment_99_index"),
)


def require_columns(reader: csv.DictReader, required: Iterable[str], path: Path) -> None:
    missing = set(required) - set(reader.fieldnames or ())
    if missing:
        raise ValueError(f"missing columns in {path}: {', '.join(sorted(missing))}")


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


def nearly_equal(first: float, second: float, tolerance: float = 1.0e-9) -> bool:
    return math.isclose(first, second, rel_tol=tolerance, abs_tol=tolerance)


def point_key(row: dict[str, str], path: Path) -> tuple[int, float]:
    try:
        pdg = int(row["pdg"])
    except ValueError as error:
        raise ValueError(f"invalid PDG in {path}: {row['pdg']!r}") from error
    energy = finite_float(row["kinetic_energy_gev"], "kinetic energy")
    return pdg, energy


def read_summary(path: Path) -> dict[tuple[int, float], dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        require_columns(
            reader,
            (
                "git_commit",
                "particle",
                "pdg",
                "kinetic_energy_gev",
                "runs",
                "events",
                "mean_energy_mev",
            ),
            path,
        )
        rows = list(reader)
    if len(rows) != len(EXPECTED_POINTS):
        raise ValueError(f"expected nine summary rows in {path}")

    points: dict[tuple[int, float], dict[str, object]] = {}
    for row in rows:
        key = point_key(row, path)
        if key in points:
            raise ValueError(f"duplicate point {key} in {path}")
        pdg, energy = key
        if row["particle"] != EXPECTED_PARTICLES.get(pdg):
            raise ValueError(f"particle label does not match PDG at point {key}")
        if len(row["git_commit"]) != 40 or any(
            character not in "0123456789abcdef" for character in row["git_commit"]
        ):
            raise ValueError(f"invalid Git commit at point {key}")
        points[key] = {
            "git_commit": row["git_commit"],
            "particle": row["particle"],
            "pdg": pdg,
            "energy": energy,
            "runs": positive_int(row["runs"], "runs"),
            "events": positive_int(row["events"], "events"),
            "mean_energy_mev": finite_float(
                row["mean_energy_mev"], "mean energy", nonnegative=True
            ),
        }
        if points[key]["mean_energy_mev"] <= 0.0:
            raise ValueError(f"mean energy must be positive at point {key}")
        if points[key]["runs"] != EXPECTED_RUNS_PER_POINT:
            raise ValueError(f"expected five runs at point {key}")
        if points[key]["events"] != EXPECTED_EVENTS_PER_POINT:
            raise ValueError(f"expected 1000 events at point {key}")
    if set(points) != EXPECTED_POINTS:
        raise ValueError("summary does not contain the fixed nine-point matrix")
    if len({point["git_commit"] for point in points.values()}) != 1:
        raise ValueError("summary spans multiple Git commits")
    return points


def read_samplings(
    path: Path,
    summary: dict[tuple[int, float], dict[str, object]],
) -> dict[tuple[int, float], tuple[float, ...]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        require_columns(
            reader,
            (
                "git_commit",
                "particle",
                "pdg",
                "kinetic_energy_gev",
                "sampling",
                "name",
                "runs",
                "events",
                "mean_energy_mev",
                "total_energy_fraction",
            ),
            path,
        )
        rows = list(reader)
    if len(rows) != len(EXPECTED_POINTS) * len(SAMPLING_NAMES):
        raise ValueError(f"expected 90 sampling rows in {path}")

    grouped: dict[tuple[int, float], dict[int, float]] = defaultdict(dict)
    fractions: dict[tuple[int, float], dict[int, float]] = defaultdict(dict)
    for row in rows:
        key = point_key(row, path)
        if key not in summary:
            raise ValueError(f"sampling point {key} is absent from summary")
        point = summary[key]
        try:
            sampling = int(row["sampling"])
        except ValueError as error:
            raise ValueError(f"invalid sampling index at point {key}") from error
        if sampling < 0 or sampling >= len(SAMPLING_NAMES):
            raise ValueError(f"sampling index out of range at point {key}")
        if sampling in grouped[key]:
            raise ValueError(f"duplicate sampling {sampling} at point {key}")
        if row["name"] != SAMPLING_NAMES[sampling]:
            raise ValueError(f"sampling name mismatch at point {key}, index {sampling}")
        if row["git_commit"] != point["git_commit"]:
            raise ValueError(f"Git commit mismatch at point {key}")
        if row["particle"] != point["particle"]:
            raise ValueError(f"particle mismatch at point {key}")
        if positive_int(row["runs"], "sampling runs") != point["runs"]:
            raise ValueError(f"run count mismatch at point {key}")
        if positive_int(row["events"], "sampling events") != point["events"]:
            raise ValueError(f"event count mismatch at point {key}")
        mean = finite_float(row["mean_energy_mev"], "sampling mean", nonnegative=True)
        fraction = finite_float(
            row["total_energy_fraction"], "sampling fraction", nonnegative=True
        )
        expected_fraction = mean / float(point["mean_energy_mev"])
        if not nearly_equal(fraction, expected_fraction):
            raise ValueError(f"inconsistent sampling fraction at point {key}")
        grouped[key][sampling] = mean
        fractions[key][sampling] = fraction

    result: dict[tuple[int, float], tuple[float, ...]] = {}
    for key in sorted(summary):
        if set(grouped[key]) != set(range(len(SAMPLING_NAMES))):
            raise ValueError(f"incomplete sampling set at point {key}")
        means = tuple(grouped[key][index] for index in range(len(SAMPLING_NAMES)))
        total_mean = float(summary[key]["mean_energy_mev"])
        if not nearly_equal(math.fsum(means), total_mean):
            raise ValueError(f"sampling means do not close at point {key}")
        if not nearly_equal(math.fsum(fractions[key].values()), 1.0):
            raise ValueError(f"sampling fractions do not close at point {key}")
        result[key] = means
    return result


def threshold_sampling(fractions: Sequence[float], threshold: float) -> tuple[str, int]:
    cumulative = 0.0
    for sampling in CENTRAL_PATH:
        cumulative += fractions[sampling]
        if cumulative + 1.0e-12 >= threshold:
            return SAMPLING_NAMES[sampling], sampling
    raise ValueError(
        f"central path does not reach {threshold:.0%} of total deposited energy"
    )


def format_value(value: object) -> object:
    if isinstance(value, float):
        return format(value, ".17g")
    if isinstance(value, bool):
        return str(value).lower()
    return value


def write_csv(path: Path, rows: Sequence[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            {key: format_value(value) for key, value in row.items()} for row in rows
        )


def analyze(
    summary_path: Path,
    sampling_path: Path,
    max_tile_extended_fraction: float,
    outer_tail_review_threshold: float,
) -> tuple[list[dict[str, object]], list[str]]:
    summary = read_summary(summary_path)
    samplings = read_samplings(sampling_path, summary)
    rows: list[dict[str, object]] = []

    for key in sorted(summary):
        point = summary[key]
        total_mean = float(point["mean_energy_mev"])
        fractions = tuple(mean / total_mean for mean in samplings[key])
        row: dict[str, object] = {
            "git_commit": point["git_commit"],
            "particle": point["particle"],
            "pdg": point["pdg"],
            "kinetic_energy_gev": point["energy"],
            "runs": point["runs"],
            "events": point["events"],
            "mean_energy_mev": total_mean,
        }
        row.update({
            name: math.fsum(fractions[index] for index in indices)
            for name, indices in GROUPS.items()
        })
        row["fraction_closure_error"] = abs(math.fsum(fractions) - 1.0)
        for threshold, name_field, index_field in CONTAINMENT_THRESHOLDS:
            name, index = threshold_sampling(fractions, threshold)
            row[name_field] = name
            row[index_field] = index
        row["outer_tail_review"] = (
            float(row["tilecal3_outer_fraction"]) > outer_tail_review_threshold
        )

        if float(row["tile_extended_fraction"]) > max_tile_extended_fraction + 1.0e-12:
            raise ValueError(
                f"TileExt fraction exceeds limit at point {key}: "
                f"{row['tile_extended_fraction']:.17g} > "
                f"{max_tile_extended_fraction:.17g}"
            )
        if int(point["pdg"]) in (11, 22) and int(row["containment_99_index"]) > 3:
            raise ValueError(f"electromagnetic point reaches 99% after EMB3: {key}")
        rows.append(row)

    maximum_extended = max(float(row["tile_extended_fraction"]) for row in rows)
    maximum_outer_tail = max(float(row["tilecal3_outer_fraction"]) for row in rows)
    review_rows = [row for row in rows if bool(row["outer_tail_review"])]
    validation = [
        "LONGITUDINAL_CONTAINMENT_RESULT=PASS",
        f"physical_points={len(rows)}",
        f"runs_per_point={EXPECTED_RUNS_PER_POINT}",
        f"events_per_point={EXPECTED_EVENTS_PER_POINT}",
        f"sampling_rows={len(rows) * len(SAMPLING_NAMES)}",
        "fraction_closure=PASS",
        "central_containment_90=PASS",
        "central_containment_95=PASS",
        "central_containment_99=PASS",
        "electromagnetic_containment_99_by_emb3=PASS",
        f"max_tile_extended_fraction={maximum_extended:.17g}",
        f"required_max_tile_extended_fraction={max_tile_extended_fraction:.17g}",
        "tile_extended_activity=PASS",
        f"max_tilecal3_outer_fraction={maximum_outer_tail:.17g}",
        f"outer_tail_review_threshold={outer_tail_review_threshold:.17g}",
        f"outer_tail_review_points={len(review_rows)}",
        "outer_tail_review=" + ("REQUIRED" if review_rows else "NOT_REQUIRED"),
    ]
    return rows, validation


def fraction(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected a number") from error
    if not math.isfinite(parsed) or not 0.0 < parsed < 1.0:
        raise argparse.ArgumentTypeError("expected a finite fraction between zero and one")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--samplings", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--validation", required=True, type=Path)
    parser.add_argument("--max-tile-extended-fraction", type=fraction, default=0.01)
    parser.add_argument("--outer-tail-review-threshold", type=fraction, default=0.01)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.output.resolve() == args.validation.resolve():
        raise ValueError("output paths must be distinct")
    for path in (args.output, args.validation):
        if path.exists():
            raise ValueError(f"output already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)

    rows, validation = analyze(
        args.summary,
        args.samplings,
        args.max_tile_extended_fraction,
        args.outer_tail_review_threshold,
    )
    temporary_paths: list[Path] = []
    try:
        for final_path, kind in (
            (args.output, "summary"),
            (args.validation, "validation"),
        ):
            descriptor, name = tempfile.mkstemp(
                prefix=f".{final_path.name}.{kind}.", dir=final_path.parent
            )
            os.close(descriptor)
            temporary_paths.append(Path(name))
        write_csv(temporary_paths[0], rows)
        temporary_paths[1].write_text("\n".join(validation) + "\n", encoding="utf-8")
        for path in temporary_paths:
            path.chmod(0o644)
        for temporary, final in zip(temporary_paths, (args.output, args.validation)):
            os.replace(temporary, final)
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)

    review_points = sum(bool(row["outer_tail_review"]) for row in rows)
    print(
        "LONGITUDINAL_CONTAINMENT_RESULT=PASS "
        f"points={len(rows)} outer_tail_review_points={review_points}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("LONGITUDINAL_CONTAINMENT_RESULT=FAIL", file=sys.stderr)
        raise SystemExit(1)
