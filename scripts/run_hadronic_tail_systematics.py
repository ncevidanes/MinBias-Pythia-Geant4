#!/usr/bin/env python3
"""Run the fixed Cycle 6.6 paired hadronic-tail systematic campaign."""

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
AGGREGATOR = PROJECT_DIR / "scripts" / "aggregate_hadronic_tail_systematics.py"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "cycle6-stage66-systematics"

PARTICLE = "pion_plus"
PDG = 211
KINETIC_ENERGY_GEV = 100
PHI = 0.0
ETA_VALUES = (0.0, 0.4, 0.8)
PRODUCTION_CUTS_MM = (0.1, 1.0, 10.0)
SEEDS = (643031, 643032, 643033, 643034, 643035)
EVENTS_PER_RUN = 200
RUNS_PER_POINT = len(SEEDS)
THREADS = 1
TOTAL_POINTS = len(ETA_VALUES) * len(PRODUCTION_CUTS_MM)
TOTAL_RUNS = TOTAL_POINTS * RUNS_PER_POINT
TOTAL_EVENTS = TOTAL_RUNS * EVENTS_PER_RUN


class CampaignError(RuntimeError):
    """A controlled Cycle 6.6 campaign failure."""


def number(value: float) -> str:
    return format(value, ".12g")


def name_token(value: float) -> str:
    return number(value).replace("-", "m").replace(".", "p")


@dataclass(frozen=True)
class Case:
    eta: float
    production_cut_mm: float
    repeat: int
    seed: int

    @property
    def name(self) -> str:
        return (
            f"{PARTICLE}_{KINETIC_ENERGY_GEV}gev_"
            f"eta{name_token(self.eta)}_"
            f"cut{name_token(self.production_cut_mm)}mm_"
            f"seed{self.seed}"
        )


def campaign_cases() -> tuple[Case, ...]:
    cases = tuple(
        Case(eta=eta, production_cut_mm=cut, repeat=repeat, seed=seed)
        for eta in ETA_VALUES
        for cut in PRODUCTION_CUTS_MM
        for repeat, seed in enumerate(SEEDS, start=1)
    )
    if len(cases) != TOTAL_RUNS:
        raise CampaignError("internal error: incomplete systematic matrix")
    if len({case.name for case in cases}) != TOTAL_RUNS:
        raise CampaignError("internal error: duplicate systematic run names")
    if {case.seed for case in cases} != set(SEEDS):
        raise CampaignError("internal error: unexpected paired seed set")
    point_counts = Counter(
        (case.eta, case.production_cut_mm) for case in cases
    )
    if len(point_counts) != TOTAL_POINTS or set(point_counts.values()) != {
        RUNS_PER_POINT
    }:
        raise CampaignError("internal error: invalid runs-per-point matrix")
    for eta in ETA_VALUES:
        for cut in PRODUCTION_CUTS_MM:
            point_seeds = {
                case.seed
                for case in cases
                if case.eta == eta and case.production_cut_mm == cut
            }
            if point_seeds != set(SEEDS):
                raise CampaignError("internal error: unpaired systematic seeds")
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
        help="validate all 45 configurations without Geant4 transport",
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
        raise CampaignError(f"missing systematic aggregator: {AGGREGATOR}")


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
    if return_code != 0:
        raise CampaignError(
            f"command failed with exit {return_code}: {command[0]} (see {log_path})"
        )
    return "".join(chunks)


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
        str(PDG),
        "--particle-kinetic-energy-gev",
        str(KINETIC_ENERGY_GEV),
        "--particle-eta",
        number(case.eta),
        "--particle-phi",
        number(PHI),
        "--production-cut-mm",
        number(case.production_cut_mm),
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
        f"production_cut_mm = {number(case.production_cut_mm)}",
        f"single_particle_pdg = {PDG}",
        f"single_particle_kinetic_energy_gev = {KINETIC_ENERGY_GEV}",
        f"single_particle_eta = {number(case.eta)}",
        f"single_particle_phi = {number(PHI)}",
    )
    missing = [line for line in expected if line not in lines]
    if missing:
        raise CampaignError(
            f"preflight mismatch for {case.name}: missing {', '.join(missing)}"
        )
    print(
        "HADRONIC_TAIL_PREFLIGHT_CASE=PASS "
        f"run={case.name} eta={number(case.eta)} "
        f"production_cut_mm={number(case.production_cut_mm)} "
        f"repeat={case.repeat} seed={case.seed}"
    )


def git_provenance() -> str:
    run_checked(("git", "rev-parse", "--is-inside-work-tree"), capture=True)
    run_checked(("git", "diff", "--quiet"))
    run_checked(("git", "diff", "--cached", "--quiet"))
    commit = run_checked(("git", "rev-parse", "HEAD"), capture=True).strip()
    if len(commit) != 40 or any(
        character not in "0123456789abcdef" for character in commit
    ):
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
    if int(summary["single_particle_pdg"]) != PDG:
        raise CampaignError(f"PDG mismatch in {summary_path}")
    expected_values = (
        ("single_particle_kinetic_energy_gev", KINETIC_ENERGY_GEV),
        ("single_particle_eta", case.eta),
        ("single_particle_phi", PHI),
        ("production_cut_mm", case.production_cut_mm),
    )
    for field, expected in expected_values:
        if not math.isclose(
            finite(summary[field], field, summary_path),
            expected,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise CampaignError(f"{field} mismatch in {summary_path}")
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
        if finite(summary[field], field, summary_path) < 0.0:
            raise CampaignError(f"negative {field} in {summary_path}")
    if finite(summary["mean_energy_mev"], "mean energy", summary_path) <= 0.0:
        raise CampaignError(f"mean energy must be positive in {summary_path}")
    if finite(summary["mean_response"], "response", summary_path) <= 0.0:
        raise CampaignError(f"response must be positive in {summary_path}")

    with sampling_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 10:
        raise CampaignError(f"expected ten sampling rows in {sampling_path}")
    sampling_names = (
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
    fractions: list[float] = []
    sampling_means: list[float] = []
    for index, (row, expected_name) in enumerate(zip(rows, sampling_names)):
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
        sampling_means.append(finite(row["mean_energy_mev"], "mean", sampling_path))
        fractions.append(
            finite(row["total_energy_fraction"], "fraction", sampling_path)
        )
    if not math.isclose(
        math.fsum(sampling_means),
        finite(summary["mean_energy_mev"], "mean energy", summary_path),
        rel_tol=1.0e-9,
        abs_tol=1.0e-9,
    ):
        raise CampaignError(f"sampling mean closure failed in {sampling_path}")
    if not math.isclose(
        math.fsum(fractions), 1.0, rel_tol=1.0e-9, abs_tol=1.0e-9
    ):
        raise CampaignError(f"sampling fraction closure failed in {sampling_path}")


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
    reanalysis_dir: Path,
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
    repeated_summary = reanalysis_dir / f"{case.name}.summary.csv"
    repeated_sampling = reanalysis_dir / f"{case.name}.samplings.csv"
    repeated_log = reanalysis_dir / f"{case.name}.analysis.log"
    environment = os.environ.copy()
    environment["BUILD_JOBS"] = str(build_jobs)

    print(f"HADRONIC_TAIL_CAMPAIGN_CASE=START run={case.name}")
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
    compare_files(summary_file, repeated_summary, "summary CSV")
    compare_files(sampling_file, repeated_sampling, "sampling CSV")
    if sha256(root_file) != root_hash_before:
        raise CampaignError(f"analyzer modified the ROOT file: {case.name}")
    validate_case_outputs(case, summary_file, sampling_file, git_commit)

    print(
        "HADRONIC_TAIL_CAMPAIGN_CASE=PASS "
        f"run={case.name} root_sha256={root_hash_before}"
    )
    return {
        "run": case.name,
        "particle": PARTICLE,
        "pdg": PDG,
        "kinetic_energy_gev": KINETIC_ENERGY_GEV,
        "eta": case.eta,
        "production_cut_mm": case.production_cut_mm,
        "events": EVENTS_PER_RUN,
        "seed": case.seed,
        "root_sha256": root_hash_before,
        "git_commit": git_commit,
    }


def ensure_output_absent(output_dir: Path) -> None:
    if output_dir.exists():
        raise CampaignError(
            f"output directory already exists; preserve it and choose another: {output_dir}"
        )


def execute_campaign(
    cases: Sequence[Case], output_dir: Path, build_jobs: int, git_commit: str
) -> None:
    ensure_output_absent(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.stage-", dir=output_dir.parent)
    )
    try:
        reanalysis_dir = staging_dir / ".reanalysis"
        reanalysis_dir.mkdir()
        manifest_path = staging_dir / "campaign_manifest.tsv"
        summary_path = staging_dir / "systematic_summary.csv"
        paired_path = staging_dir / "paired_differences.csv"
        validation_path = staging_dir / "systematic_validation.txt"
        aggregation_log = staging_dir / "systematic_aggregation.log"

        manifest_rows = [
            run_case(case, staging_dir, reanalysis_dir, build_jobs, git_commit)
            for case in cases
        ]
        with manifest_path.open("w", newline="", encoding="utf-8") as stream:
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
            writer.writerows(manifest_rows)

        aggregation_output = run_and_tee(
            (
                sys.executable,
                "-B",
                AGGREGATOR,
                "--manifest",
                manifest_path,
                "--input-dir",
                staging_dir,
                "--summary-csv",
                summary_path,
                "--paired-csv",
                paired_path,
                "--validation",
                validation_path,
                "--runs-per-point",
                str(RUNS_PER_POINT),
                "--events-per-run",
                str(EVENTS_PER_RUN),
                "--precision-review-threshold",
                "0.03",
            ),
            aggregation_log,
        )
        if not any(
            line.startswith("HADRONIC_TAIL_AGGREGATION_RESULT=PASS")
            for line in aggregation_output.splitlines()
        ):
            raise CampaignError("hadronic-tail aggregation did not pass")
        shutil.rmtree(reanalysis_dir)
        os.replace(staging_dir, output_dir)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    print(
        "HADRONIC_TAIL_SYSTEMATICS_RESULT=PASS "
        f"points={TOTAL_POINTS} runs={TOTAL_RUNS} events={TOTAL_EVENTS} "
        f"paired_seeds={len(SEEDS)}"
    )
    print(f"HADRONIC_TAIL_SYSTEMATICS_OUTPUT_DIR={output_dir}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    cases = campaign_cases()
    output_dir = resolved_output_dir(args.output_dir)
    require_project_layout()
    build_project(args.build_jobs)

    if args.dry_run:
        ensure_output_absent(output_dir)
        for case in cases:
            preflight_case(case, output_dir, args.build_jobs)
        if output_dir.exists():
            raise CampaignError(
                f"dry-run unexpectedly created output directory: {output_dir}"
            )
        print(
            "HADRONIC_TAIL_SYSTEMATICS_PREFLIGHT=PASS "
            f"points={TOTAL_POINTS} runs={TOTAL_RUNS} "
            f"runs_per_point={RUNS_PER_POINT} events_per_run={EVENTS_PER_RUN} "
            f"total_events={TOTAL_EVENTS} paired_seeds={len(SEEDS)}"
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
        print("HADRONIC_TAIL_SYSTEMATICS_RESULT=FAIL", file=sys.stderr)
        raise SystemExit(1)
