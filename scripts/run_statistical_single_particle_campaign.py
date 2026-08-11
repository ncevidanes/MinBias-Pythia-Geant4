#!/usr/bin/env python3
"""Run the fixed Cycle 6.4 single-particle statistical campaign."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


PROJECT_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = PROJECT_DIR / "config" / "single_particle.conf"
RUN_SCRIPT = PROJECT_DIR / "run.sh"
ANALYZER = PROJECT_DIR / "build" / "single_particle_analyzer"
AGGREGATOR = PROJECT_DIR / "scripts" / "aggregate_single_particle_statistics.py"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "cycle6-stage64c"

EVENTS_PER_RUN = 200
RUNS_PER_POINT = 5
THREADS = 1
TOTAL_POINTS = 9
TOTAL_RUNS = TOTAL_POINTS * RUNS_PER_POINT
TOTAL_EVENTS = TOTAL_RUNS * EVENTS_PER_RUN
PARTICLES = (("electron", 11), ("photon", 22), ("pion_plus", 211))
ENERGIES_GEV = (1, 10, 100)
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


class CampaignError(RuntimeError):
    """A controlled campaign failure with a user-facing diagnostic."""


@dataclass(frozen=True)
class Case:
    particle: str
    pdg: int
    energy_gev: int
    repeat: int
    seed: int

    @property
    def name(self) -> str:
        return f"{self.particle}_{self.energy_gev}gev_seed{self.seed}"


def campaign_cases() -> tuple[Case, ...]:
    cases = tuple(
        Case(
            particle=particle,
            pdg=pdg,
            energy_gev=energy,
            repeat=repeat,
            seed=640000 + particle_index * 1000 + energy_index * 10 + repeat,
        )
        for particle_index, (particle, pdg) in enumerate(PARTICLES, start=1)
        for energy_index, energy in enumerate(ENERGIES_GEV, start=1)
        for repeat in range(1, RUNS_PER_POINT + 1)
    )
    if len(cases) != TOTAL_RUNS:
        raise CampaignError("internal error: incomplete campaign matrix")
    if len({case.name for case in cases}) != TOTAL_RUNS:
        raise CampaignError("internal error: duplicate run names")
    if len({case.seed for case in cases}) != TOTAL_RUNS:
        raise CampaignError("internal error: duplicate campaign seeds")
    point_counts = Counter((case.pdg, case.energy_gev) for case in cases)
    if set(point_counts.values()) != {RUNS_PER_POINT} or len(point_counts) != TOTAL_POINTS:
        raise CampaignError("internal error: invalid runs-per-point matrix")
    return cases


def positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected an integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="build, test, and validate all 45 resolved configurations without transport",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="campaign output directory (must not exist for a full run)",
    )
    parser.add_argument(
        "--build-jobs",
        type=positive_integer,
        default=positive_integer(os.environ.get("BUILD_JOBS", "2")),
        help="parallel build jobs (default: BUILD_JOBS or 2)",
    )
    return parser.parse_args(argv)


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise CampaignError(f"required command not found: {name}")


def require_project_layout() -> None:
    for command in ("cmake", "ctest", "git"):
        require_command(command)
    if not CONFIG_FILE.is_file() or CONFIG_FILE.stat().st_size == 0:
        raise CampaignError(f"missing configuration: {CONFIG_FILE}")
    if not RUN_SCRIPT.is_file() or not os.access(RUN_SCRIPT, os.X_OK):
        raise CampaignError(f"run.sh is not executable: {RUN_SCRIPT}")
    if not AGGREGATOR.is_file() or AGGREGATOR.stat().st_size == 0:
        raise CampaignError(f"missing statistical aggregator: {AGGREGATOR}")


def run_checked(
    command: Sequence[str | Path],
    *,
    capture: bool = False,
    environment: dict[str, str] | None = None,
) -> str:
    result = subprocess.run(
        [str(item) for item in command],
        cwd=PROJECT_DIR,
        env=environment,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )
    if result.returncode != 0:
        diagnostic = f"command failed with exit {result.returncode}: {command[0]}"
        if capture and result.stdout:
            diagnostic += f"\n{result.stdout.rstrip()}"
        raise CampaignError(diagnostic)
    return result.stdout or ""


def run_and_tee(
    command: Sequence[str | Path],
    log_path: Path,
    *,
    environment: dict[str, str] | None = None,
) -> str:
    with log_path.open("w", encoding="utf-8", newline="\n") as log_stream:
        process = subprocess.Popen(
            [str(item) for item in command],
            cwd=PROJECT_DIR,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        assert process.stdout is not None
        chunks: list[str] = []
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            log_stream.write(line)
            log_stream.flush()
            chunks.append(line)
        return_code = process.wait()
    output = "".join(chunks)
    if return_code != 0:
        raise CampaignError(
            f"command failed with exit {return_code}: {command[0]} "
            f"(see {log_path})"
        )
    return output


def build_project(build_jobs: int) -> None:
    run_checked(("cmake", "-S", ".", "-B", "build", "-DCMAKE_BUILD_TYPE=Release"))
    run_checked(("cmake", "--build", "build", "--parallel", str(build_jobs)))
    run_checked(("ctest", "--test-dir", "build", "--output-on-failure"))
    if not ANALYZER.is_file() or not os.access(ANALYZER, os.X_OK):
        raise CampaignError(f"analyzer was not produced: {ANALYZER}")


def resolved_output_dir(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (PROJECT_DIR / path).resolve()


def run_arguments(case: Case, root_file: Path) -> tuple[str, ...]:
    return (
        "--events",
        str(EVENTS_PER_RUN),
        "--threads",
        str(THREADS),
        "--seed",
        str(case.seed),
        "--particle-pdg",
        str(case.pdg),
        "--particle-kinetic-energy-gev",
        str(case.energy_gev),
        "--particle-eta",
        "0",
        "--particle-phi",
        "0",
        "--output",
        str(root_file),
    )


def preflight_case(case: Case, output_dir: Path, build_jobs: int) -> None:
    root_file = output_dir / f"{case.name}.root"
    environment = os.environ.copy()
    environment["BUILD_JOBS"] = str(build_jobs)
    output = run_checked(
        (RUN_SCRIPT, CONFIG_FILE, *run_arguments(case, root_file), "--dry-run"),
        capture=True,
        environment=environment,
    )
    lines = set(output.splitlines())
    expected = (
        "generator_mode = single_particle",
        f"events = {EVENTS_PER_RUN}",
        f"threads = {THREADS}",
        f"seed_base = {case.seed}",
        "physics_list = FTFP_BERT_ATL",
        f"single_particle_pdg = {case.pdg}",
        f"single_particle_kinetic_energy_gev = {case.energy_gev}",
        "single_particle_eta = 0",
        "single_particle_phi = 0",
    )
    missing = [line for line in expected if line not in lines]
    if missing:
        raise CampaignError(
            f"preflight mismatch for {case.name}: missing {', '.join(missing)}"
        )
    if not any(
        line.startswith("production_cut_mm = ")
        and math.isclose(float(line.partition("=")[2]), 1.0)
        for line in lines
    ):
        raise CampaignError(f"preflight production cut mismatch for {case.name}")
    print(
        "STATISTICAL_PREFLIGHT_CASE=PASS "
        f"run={case.name} pdg={case.pdg} energy_gev={case.energy_gev} "
        f"repeat={case.repeat} seed={case.seed}"
    )


def git_provenance() -> str:
    run_checked(("git", "rev-parse", "--is-inside-work-tree"), capture=True)
    run_checked(("git", "diff", "--quiet"))
    run_checked(("git", "diff", "--cached", "--quiet"))
    commit = run_checked(("git", "rev-parse", "HEAD"), capture=True).strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise CampaignError("invalid Git commit returned by git rev-parse")
    return commit


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_one_csv_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise CampaignError(f"expected exactly one data row in {path}")
    return rows[0]


def finite(value: str, field: str, path: Path) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise CampaignError(f"non-numeric {field} in {path}") from error
    if not math.isfinite(parsed):
        raise CampaignError(f"non-finite {field} in {path}")
    return parsed


def validate_case_outputs(
    case: Case,
    summary_path: Path,
    sampling_path: Path,
    git_commit: str,
) -> None:
    summary = read_one_csv_row(summary_path)
    if int(summary["schema_version"]) != 2:
        raise CampaignError(f"unexpected schema in {summary_path}")
    if summary["git_commit"] != git_commit:
        raise CampaignError(f"Git provenance mismatch in {summary_path}")
    if summary["generator_mode"] != "single_particle":
        raise CampaignError(f"unexpected generator mode in {summary_path}")
    if int(summary["single_particle_pdg"]) != case.pdg:
        raise CampaignError(f"PDG mismatch in {summary_path}")
    if not math.isclose(
        finite(summary["single_particle_kinetic_energy_gev"], "energy", summary_path),
        case.energy_gev,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ):
        raise CampaignError(f"energy mismatch in {summary_path}")
    if finite(summary["single_particle_eta"], "eta", summary_path) != 0.0:
        raise CampaignError(f"eta mismatch in {summary_path}")
    if finite(summary["single_particle_phi"], "phi", summary_path) != 0.0:
        raise CampaignError(f"phi mismatch in {summary_path}")
    if int(summary["event_count"]) != EVENTS_PER_RUN:
        raise CampaignError(f"event count mismatch in {summary_path}")
    if int(summary["hit_count"]) <= 0:
        raise CampaignError(f"hit count must be positive in {summary_path}")
    for field in (
        "mean_energy_mev",
        "sample_stddev_energy_mev",
        "mean_response",
        "relative_resolution",
        "sampling_centroid",
        "sampling_width",
        "eta_width",
        "phi_width",
    ):
        value = finite(summary[field], field, summary_path)
        if value < 0.0:
            raise CampaignError(f"negative {field} in {summary_path}")
    if finite(summary["mean_energy_mev"], "mean energy", summary_path) <= 0.0:
        raise CampaignError(f"mean energy must be positive in {summary_path}")
    if finite(summary["mean_response"], "response", summary_path) <= 0.0:
        raise CampaignError(f"response must be positive in {summary_path}")

    with sampling_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(SAMPLING_NAMES):
        raise CampaignError(f"expected ten sampling rows in {sampling_path}")
    for index, (row, expected_name) in enumerate(zip(rows, SAMPLING_NAMES)):
        if int(row["sampling"]) != index or row["name"] != expected_name:
            raise CampaignError(f"unexpected sampling row {index} in {sampling_path}")
        for field in (
            "mean_energy_mev",
            "sample_stddev_energy_mev",
            "total_energy_fraction",
            "eta_width",
            "phi_width",
        ):
            if finite(row[field], field, sampling_path) < 0.0:
                raise CampaignError(f"negative {field} in {sampling_path}")


def compare_files(first: Path, second: Path, description: str) -> None:
    if first.read_bytes() != second.read_bytes():
        raise CampaignError(f"non-deterministic {description}: {first.name}")


def expected_case_paths(output_dir: Path, case: Case) -> tuple[Path, ...]:
    base = output_dir / case.name
    return tuple(
        Path(f"{base}.{suffix}")
        for suffix in (
            "root",
            "root.manifest.txt",
            "summary.csv",
            "samplings.csv",
            "simulation.log",
            "analysis.log",
        )
    )


def run_case(
    case: Case,
    output_dir: Path,
    staging_dir: Path,
    build_jobs: int,
    git_commit: str,
) -> dict[str, object]:
    (
        root_file,
        root_manifest,
        summary_file,
        sampling_file,
        simulation_log,
        analysis_log,
    ) = expected_case_paths(output_dir, case)
    repeated_summary = staging_dir / f"{case.name}.summary.csv"
    repeated_sampling = staging_dir / f"{case.name}.samplings.csv"
    repeated_log = staging_dir / f"{case.name}.analysis.log"
    environment = os.environ.copy()
    environment["BUILD_JOBS"] = str(build_jobs)

    print(f"STATISTICAL_CAMPAIGN_CASE=START run={case.name}")
    run_and_tee(
        (RUN_SCRIPT, CONFIG_FILE, *run_arguments(case, root_file)),
        simulation_log,
        environment=environment,
    )
    if not root_file.is_file() or root_file.stat().st_size == 0:
        raise CampaignError(f"ROOT is absent or empty: {root_file}")
    if not root_manifest.is_file() or root_manifest.stat().st_size == 0:
        raise CampaignError(f"ROOT manifest is absent or empty: {root_manifest}")
    root_hash_before = sha256(root_file)

    analysis_output = run_and_tee(
        (
            ANALYZER,
            "--input",
            root_file,
            "--summary-csv",
            summary_file,
            "--sampling-csv",
            sampling_file,
        ),
        analysis_log,
    )
    if "ANALYSIS_RESULT=PASS" not in analysis_output.splitlines():
        raise CampaignError(f"analysis did not pass: {case.name}")
    repeated_output = run_and_tee(
        (
            ANALYZER,
            "--input",
            root_file,
            "--summary-csv",
            repeated_summary,
            "--sampling-csv",
            repeated_sampling,
        ),
        repeated_log,
    )
    if "ANALYSIS_RESULT=PASS" not in repeated_output.splitlines():
        raise CampaignError(f"repeated analysis did not pass: {case.name}")
    compare_files(summary_file, repeated_summary, "summary")
    compare_files(sampling_file, repeated_sampling, "sampling CSV")
    if sha256(root_file) != root_hash_before:
        raise CampaignError(f"analyzer modified the ROOT file: {case.name}")
    validate_case_outputs(case, summary_file, sampling_file, git_commit)

    print(
        "STATISTICAL_CAMPAIGN_CASE=PASS "
        f"run={case.name} root_sha256={root_hash_before}"
    )
    return {
        "run": case.name,
        "particle": case.particle,
        "pdg": case.pdg,
        "kinetic_energy_gev": case.energy_gev,
        "events": EVENTS_PER_RUN,
        "seed": case.seed,
        "root_sha256": root_hash_before,
        "git_commit": git_commit,
    }


def ensure_new_output_directory(output_dir: Path) -> None:
    if output_dir.exists():
        raise CampaignError(
            f"output directory already exists; preserve it and choose another: {output_dir}"
        )
    output_dir.mkdir(parents=True)


def execute_campaign(
    cases: Sequence[Case], output_dir: Path, build_jobs: int, git_commit: str
) -> None:
    ensure_new_output_directory(output_dir)
    with tempfile.TemporaryDirectory(prefix=".stage64b-", dir=output_dir) as temporary:
        staging_dir = Path(temporary)
        manifest_staging = staging_dir / "campaign_manifest.tsv"
        statistical_summary_staging = staging_dir / "statistical_summary.csv"
        statistical_samplings_staging = staging_dir / "statistical_samplings.csv"
        statistical_validation_staging = staging_dir / "statistical_validation.txt"
        aggregation_log = output_dir / "statistical_aggregation.log"

        manifest_rows = [
            run_case(case, output_dir, staging_dir, build_jobs, git_commit)
            for case in cases
        ]
        with manifest_staging.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "run",
                    "particle",
                    "pdg",
                    "kinetic_energy_gev",
                    "events",
                    "seed",
                    "root_sha256",
                    "git_commit",
                ),
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(manifest_rows)

        aggregation_output = run_and_tee(
            (
                sys.executable,
                "-B",
                AGGREGATOR,
                "--manifest",
                manifest_staging,
                "--input-dir",
                output_dir,
                "--summary-csv",
                statistical_summary_staging,
                "--sampling-csv",
                statistical_samplings_staging,
                "--validation",
                statistical_validation_staging,
                "--runs-per-point",
                str(RUNS_PER_POINT),
                "--events-per-run",
                str(EVENTS_PER_RUN),
                "--max-relative-ci95-half-width",
                "0.03",
            ),
            aggregation_log,
        )
        if not any(
            line.startswith("STATISTICAL_AGGREGATION_RESULT=PASS")
            for line in aggregation_output.splitlines()
        ):
            raise CampaignError("statistical aggregation did not pass")

        final_outputs = (
            (manifest_staging, output_dir / "campaign_manifest.tsv"),
            (statistical_summary_staging, output_dir / "statistical_summary.csv"),
            (statistical_samplings_staging, output_dir / "statistical_samplings.csv"),
            (statistical_validation_staging, output_dir / "statistical_validation.txt"),
        )
        for source, destination in final_outputs:
            os.replace(source, destination)

    print(
        "STATISTICAL_CAMPAIGN_RESULT=PASS "
        f"points={TOTAL_POINTS} runs={TOTAL_RUNS} events={TOTAL_EVENTS}"
    )
    print(f"STATISTICAL_CAMPAIGN_OUTPUT_DIR={output_dir}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    cases = campaign_cases()
    output_dir = resolved_output_dir(args.output_dir)
    require_project_layout()
    build_project(args.build_jobs)

    if args.dry_run:
        for case in cases:
            preflight_case(case, output_dir, args.build_jobs)
        print(
            "STATISTICAL_CAMPAIGN_PREFLIGHT=PASS "
            f"points={TOTAL_POINTS} runs={TOTAL_RUNS} "
            f"runs_per_point={RUNS_PER_POINT} events_per_run={EVENTS_PER_RUN} "
            f"total_events={TOTAL_EVENTS} unique_seeds={len({case.seed for case in cases})}"
        )
        return 0

    git_commit = git_provenance()
    execute_campaign(cases, output_dir, args.build_jobs, git_commit)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CampaignError, OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("STATISTICAL_CAMPAIGN_RESULT=FAIL", file=sys.stderr)
        raise SystemExit(1)
