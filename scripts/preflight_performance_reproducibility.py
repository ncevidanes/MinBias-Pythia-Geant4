#!/usr/bin/env python3
"""Validate the fixed Cycle 9 performance/reproducibility contract without transport."""

from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


PROJECT_DIR = Path(__file__).resolve().parents[1]
PRODUCTION_CONFIG = PROJECT_DIR / "config" / "production.conf"
PYTHIA_CONFIG = PROJECT_DIR / "config" / "pythia_minbias.cmnd"
SEED_POLICY_HEADER = PROJECT_DIR / "include" / "SeedPolicy.hh"
MAIN_SOURCE = PROJECT_DIR / "app" / "main.cc"
CONTRACT = (
    PROJECT_DIR
    / "docs"
    / "cycle-9-performance-reproducibility"
    / "campaign-spec.md"
)
DEFAULT_OUTPUT_DIR = (
    PROJECT_DIR / "outputs" / "cycle9-performance-reproducibility"
)

SEED_BASE = 9512
MEAN_INTERACTIONS = 1.0
MAX_THREADS = 2
MIN_MEMORY_BYTES = 2 * 1024**3
MIN_STORAGE_BYTES = 5 * 1024**3


class PreflightError(RuntimeError):
    """A controlled Cycle 9 preflight failure."""


@dataclass(frozen=True)
class Run:
    profile: str
    name: str
    threads: int
    repetition: int
    events: int


REPRO_RUNS = (
    Run("reproducibility", "repro-t1-r1", 1, 1, 100),
    Run("reproducibility", "repro-t1-r2", 1, 2, 100),
    Run("reproducibility", "repro-t2-r1", 2, 1, 100),
    Run("reproducibility", "repro-t2-r2", 2, 2, 100),
)

PERF_RUNS = (
    Run("performance", "perf-t1-r1", 1, 1, 200),
    Run("performance", "perf-t2-r1", 2, 1, 200),
    Run("performance", "perf-t1-r2", 1, 2, 200),
    Run("performance", "perf-t2-r2", 2, 2, 200),
    Run("performance", "perf-t1-r3", 1, 3, 200),
    Run("performance", "perf-t2-r3", 2, 3, 200),
)

RUNS = REPRO_RUNS + PERF_RUNS


def parse_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise PreflightError(f"{path}:{number}: expected key = value")
        key, value = key.strip(), value.strip()
        if not key or not value:
            raise PreflightError(f"{path}:{number}: empty key or value")
        if key in values:
            raise PreflightError(f"{path}:{number}: duplicate key: {key}")
        values[key] = value
    return values


def parse_pythia_commands(path: Path) -> dict[str, str]:
    commands: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.split("!", 1)[0].split("#", 1)[0].strip()
        if not line:
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise PreflightError(f"{path}:{number}: expected PYTHIA assignment")
        key, value = key.strip(), value.strip()
        if key in commands:
            raise PreflightError(f"{path}:{number}: duplicate PYTHIA command: {key}")
        commands[key] = value
    return commands


def require_tokens(path: Path, tokens: Sequence[str]) -> None:
    source = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in source]
    if missing:
        raise PreflightError(
            f"source contract mismatch in {path}: missing " + ", ".join(missing)
        )


def validate_project_layout() -> None:
    required = (
        PRODUCTION_CONFIG,
        PYTHIA_CONFIG,
        SEED_POLICY_HEADER,
        MAIN_SOURCE,
        CONTRACT,
    )
    for path in required:
        if not path.is_file() or path.stat().st_size == 0:
            raise PreflightError(f"missing or empty project file: {path}")


def validate_template_contract() -> None:
    values = parse_config(PRODUCTION_CONFIG)
    expected = {
        "generator_mode": "pythia",
        "first_bcid": "0",
        "interaction_mode": "poisson",
        "pythia_config": "pythia_minbias.cmnd",
        "physics_list": "FTFP_BERT_ATL",
        "production_cut_mm": "1.0",
        "beam_sigma_x_mm": "0.0",
        "beam_sigma_y_mm": "0.0",
        "beam_sigma_z_mm": "0.0",
        "beam_sigma_t_ns": "0.0",
        "max_abs_eta": "1.8",
        "transport_neutrinos": "false",
        "generator_audit": "false",
        "check_overlaps": "false",
    }
    for key, expected_value in expected.items():
        actual = values.get(key)
        if actual != expected_value:
            raise PreflightError(
                f"production template mismatch for {key}: "
                f"expected {expected_value!r}, found {actual!r}"
            )
    for key in ("events", "threads", "seed_base", "mean_interactions", "output"):
        if key not in values:
            raise PreflightError(f"production template missing CLI override key: {key}")


def validate_pythia_contract() -> None:
    commands = parse_pythia_commands(PYTHIA_CONFIG)
    expected = {
        "Beams:idA": "2212",
        "Beams:idB": "2212",
        "Beams:eCM": "14000.",
        "SoftQCD:inelastic": "on",
        "Random:setSeed": "on",
    }
    for key, expected_value in expected.items():
        if commands.get(key) != expected_value:
            raise PreflightError(f"PYTHIA contract mismatch for {key}")
    if commands.get("SoftQCD:all", "off").lower() in {"on", "true", "1"}:
        raise PreflightError("SoftQCD:all must remain disabled")


def validate_source_contract() -> None:
    require_tokens(
        SEED_POLICY_HEADER,
        (
            'kSeedPolicyName[] = "event-stable-v1"',
            'kSeedIdentityName[] = "bcid"',
            'kSeedMixerName[] = "splitmix64-v1"',
            "kPythiaMaximumSeed = 900000000LL",
            "enum class SeedStream",
            "kPythiaInitialization = 1ULL",
            "kInteractionCount = 2ULL",
            "kPythiaSubevent = 3ULL",
            "kVertexX = 4ULL",
            "kVertexY = 5ULL",
            "kVertexZ = 6ULL",
            "kVertexT = 7ULL",
            "SplitMix64",
            "StableSeed64",
            "PythiaSeedForStableTuple",
        ),
    )

    seed_source = SEED_POLICY_HEADER.read_text(
        encoding="utf-8"
    )
    forbidden_seed_tokens = (
        "kPythiaWorkerSeedStride",
        "PythiaSeedForWorker",
        "threadId < 0 ? 0 : threadId",
    )
    surviving = [
        token
        for token in forbidden_seed_tokens
        if token in seed_source
    ]
    if surviving:
        raise PreflightError(
            "legacy worker-seed contract remains active: "
            + ", ".join(surviving)
        )
    require_tokens(
        MAIN_SOURCE,
        (
            "--events",
            "--mu",
            "--threads",
            "--seed",
            "--output",
            "--dry-run",
            "Dry run concluído; nenhuma simulação foi executada.",
            "SetNumberOfThreads(configuration.threads)",
        ),
    )


def validate_matrix_contract() -> None:
    if len(REPRO_RUNS) != 4:
        raise PreflightError("reproducibility matrix must contain four runs")
    if len(PERF_RUNS) != 6:
        raise PreflightError("performance matrix must contain six runs")
    names = [run.name for run in RUNS]
    if len(names) != len(set(names)):
        raise PreflightError("run names must be unique")
    if {run.threads for run in RUNS} != {1, 2}:
        raise PreflightError("Cycle 9 initial matrix must use threads 1 and 2")
    if any(run.threads > MAX_THREADS for run in RUNS):
        raise PreflightError("run exceeds MAX_THREADS")
    if any(run.events <= 0 or run.repetition <= 0 for run in RUNS):
        raise PreflightError("invalid event count or repetition")
    if [run.name for run in PERF_RUNS] != [
        "perf-t1-r1",
        "perf-t2-r1",
        "perf-t1-r2",
        "perf-t2-r2",
        "perf-t1-r3",
        "perf-t2-r3",
    ]:
        raise PreflightError("performance matrix is not interleaved as contracted")


SIMULATOR = PROJECT_DIR / "build" / "pythia_geant"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="prospective Cycle 9 output directory; it must not exist",
    )
    return parser.parse_args(argv)


def resolved_output_dir(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (PROJECT_DIR / path).resolve()


def ensure_output_absent(path: Path) -> None:
    if path.exists():
        raise PreflightError(f"output directory already exists: {path}")


def available_memory_bytes() -> int:
    meminfo = Path("/proc/meminfo")
    if not meminfo.is_file():
        raise PreflightError("/proc/meminfo is unavailable")
    for raw_line in meminfo.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("MemAvailable:"):
            fields = raw_line.split()
            if len(fields) < 2:
                break
            return int(fields[1]) * 1024
    raise PreflightError("MemAvailable not found in /proc/meminfo")


def validate_resources() -> tuple[int, int, int]:
    logical_cpus = os.cpu_count() or 0
    if logical_cpus < 2:
        raise PreflightError(
            f"at least 2 logical CPUs are required; found {logical_cpus}"
        )

    memory_bytes = available_memory_bytes()
    if memory_bytes < MIN_MEMORY_BYTES:
        raise PreflightError(
            f"available memory below 2 GiB: {memory_bytes} bytes"
        )

    storage_bytes = shutil.disk_usage(PROJECT_DIR).free
    if storage_bytes < MIN_STORAGE_BYTES:
        raise PreflightError(
            f"available storage below 5 GiB: {storage_bytes} bytes"
        )

    geant4_config = shutil.which("geant4-config")
    if geant4_config is None:
        raise PreflightError("geant4-config not found")

    result = subprocess.run(
        [geant4_config, "--has-feature", "multithreading"],
        cwd=PROJECT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    mt_output = result.stdout.strip().lower()
    if result.returncode != 0 or mt_output not in {
        "yes", "true", "on", "enabled"
    }:
        raise PreflightError(
            "Geant4 multithreading unavailable: "
            f"rc={result.returncode} output={result.stdout.strip()!r}"
        )

    return logical_cpus, memory_bytes, storage_bytes


def validate_simulator() -> None:
    if not SIMULATOR.is_file():
        raise PreflightError(f"simulator binary missing: {SIMULATOR}")
    if not os.access(SIMULATOR, os.X_OK):
        raise PreflightError(f"simulator binary is not executable: {SIMULATOR}")


def run_output_path(output_dir: Path, run: Run) -> Path:
    return output_dir / f"{run.name}.root"


def dry_run_command(output_dir: Path, run: Run) -> list[str]:
    return [
        str(SIMULATOR),
        "--config",
        str(PRODUCTION_CONFIG),
        "--events",
        str(run.events),
        "--mu",
        str(MEAN_INTERACTIONS),
        "--threads",
        str(run.threads),
        "--seed",
        str(SEED_BASE),
        "--output",
        str(run_output_path(output_dir, run)),
        "--dry-run",
    ]


def execute_dry_run(output_dir: Path, run: Run) -> None:
    command = dry_run_command(output_dir, run)
    result = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    output = result.stdout
    expected_tokens = (
        f"events = {run.events}",
        f"threads = {run.threads}",
        f"seed_base = {SEED_BASE}",
        "interaction_mode = poisson",
        "mean_interactions = 1",
        f"output = \"{run_output_path(output_dir, run)}\"",
        "Dry run concluído; nenhuma simulação foi executada.",
    )

    missing = [token for token in expected_tokens if token not in output]
    if result.returncode != 0 or missing:
        details = [
            f"rc={result.returncode}",
            f"run={run.name}",
        ]
        if missing:
            details.append("missing=" + ",".join(missing))
        raise PreflightError(
            "dry-run validation failed: "
            + " ".join(details)
            + "\n"
            + output.rstrip()
        )

    if run_output_path(output_dir, run).exists():
        raise PreflightError(
            f"dry-run unexpectedly created ROOT output: "
            f"{run_output_path(output_dir, run)}"
        )

    print(
        "CYCLE_9_RUN_DRY_RUN=PASS "
        f"profile={run.profile} "
        f"name={run.name} "
        f"threads={run.threads} "
        f"events={run.events} "
        f"seed={SEED_BASE}"
    )


def validate_contract_text() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    required = (
        "Seed base: 9512",
        "Initial worker counts: 1 and 2",
        "repro-t1-r1",
        "repro-t1-r2",
        "repro-t2-r1",
        "repro-t2-r2",
        "perf-t1-r1",
        "perf-t2-r1",
        "perf-t1-r2",
        "perf-t2-r2",
        "perf-t1-r3",
        "perf-t2-r3",
        "This specification alone does not authorize transport.",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise PreflightError(
            "Cycle 9 committed contract is incomplete: " + ", ".join(missing)
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = resolved_output_dir(args.output_dir)

    ensure_output_absent(output_dir)
    validate_project_layout()
    validate_template_contract()
    validate_pythia_contract()
    validate_source_contract()
    validate_matrix_contract()
    validate_contract_text()
    validate_simulator()

    logical_cpus, memory_bytes, storage_bytes = validate_resources()

    print(f"LOGICAL_CPUS={logical_cpus}")
    print(f"AVAILABLE_MEMORY_BYTES={memory_bytes}")
    print(f"AVAILABLE_STORAGE_BYTES={storage_bytes}")
    print("GEANT4_MULTITHREADING=PASS")

    for run in RUNS:
        execute_dry_run(output_dir, run)
        ensure_output_absent(output_dir)

    if output_dir.exists():
        raise PreflightError(
            f"preflight unexpectedly created output directory: {output_dir}"
        )

    print(
        "PERFORMANCE_REPRODUCIBILITY_PREFLIGHT=PASS "
        f"runs={len(RUNS)} "
        f"repro_runs={len(REPRO_RUNS)} "
        f"performance_runs={len(PERF_RUNS)} "
        f"seed={SEED_BASE} "
        "threads=1,2 "
        "transport_executed=NO"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, PreflightError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print(
            "PERFORMANCE_REPRODUCIBILITY_PREFLIGHT=FAIL",
            file=sys.stderr,
        )
        raise SystemExit(1)
