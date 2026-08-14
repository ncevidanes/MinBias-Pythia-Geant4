#!/usr/bin/env python3
"""Preflight the fixed Cycle 6.6 hadronic-tail systematic matrix."""

from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


PROJECT_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = PROJECT_DIR / "config" / "single_particle.conf"
RUN_SCRIPT = PROJECT_DIR / "run.sh"
ANALYZER = PROJECT_DIR / "build" / "single_particle_analyzer"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "cycle6-stage66a-preflight"

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
    """A controlled Cycle 6.6 preflight failure."""


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
        help="prospective output directory; it is not created in 6.6A",
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
    for command in ("cmake", "ctest"):
        require_command(command)
    if not CONFIG_FILE.is_file() or CONFIG_FILE.stat().st_size == 0:
        raise CampaignError(f"missing configuration: {CONFIG_FILE}")
    if not RUN_SCRIPT.is_file() or not os.access(RUN_SCRIPT, os.X_OK):
        raise CampaignError(f"run.sh is not executable: {RUN_SCRIPT}")


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


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.dry_run:
        raise CampaignError(
            "Cycle 6.6A is preflight-only; pass --dry-run and do not transport yet"
        )
    cases = campaign_cases()
    output_dir = resolved_output_dir(args.output_dir)
    require_project_layout()
    build_project(args.build_jobs)
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


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CampaignError, OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("HADRONIC_TAIL_SYSTEMATICS_RESULT=FAIL", file=sys.stderr)
        raise SystemExit(1)
