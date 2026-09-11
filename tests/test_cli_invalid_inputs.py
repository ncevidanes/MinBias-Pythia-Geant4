#!/usr/bin/env python3

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NegativeCase:
    name: str
    arguments: tuple[str, ...]
    expected_message: str


@dataclass(frozen=True)
class PositiveCase:
    name: str
    arguments: tuple[str, ...]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def fail(message: str, result: subprocess.CompletedProcess[str] | None = None) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    if result is not None:
        print("--- command output ---", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    binary = Path(args.binary).resolve()
    config = Path(args.config).resolve()

    if not binary.is_file():
        fail(f"simulator binary does not exist: {binary}")
    if not config.is_file():
        fail(f"configuration file does not exist: {config}")

    base = [str(binary), "--config", str(config)]

    positive = run(base + ["--dry-run"])
    if positive.returncode != 0:
        fail("valid dry-run was rejected", positive)
    if "Dry run concluído" not in positive.stdout:
        fail("valid dry-run completion marker is missing", positive)

    cases = (
        NegativeCase(
            "unknown_option",
            ("--definitely-invalid", "--dry-run"),
            "Opção desconhecida",
        ),
        NegativeCase(
            "missing_events_value",
            ("--events",),
            "Valor ausente para --events",
        ),
        NegativeCase(
            "events_trailing_junk",
            ("--events", "3abc", "--dry-run"),
            "Valor inteiro inválido para --events",
        ),
        NegativeCase(
            "threads_trailing_junk",
            ("--threads", "1abc", "--dry-run"),
            "Valor inteiro inválido para --threads",
        ),
        NegativeCase(
            "seed_trailing_junk",
            ("--seed", "512abc", "--dry-run"),
            "Valor inteiro inválido para --seed",
        ),
        NegativeCase(
            "particle_pdg_trailing_junk",
            ("--particle-pdg", "11abc", "--dry-run"),
            "Valor inteiro inválido para --particle-pdg",
        ),
        NegativeCase(
            "mu_trailing_junk",
            ("--mu", "1.5abc", "--dry-run"),
            "Valor numérico inválido para --mu",
        ),
        NegativeCase(
            "production_cut_trailing_junk",
            ("--production-cut-mm", "1.0abc", "--dry-run"),
            "Valor numérico inválido para --production-cut-mm",
        ),
        NegativeCase(
            "particle_energy_trailing_junk",
            (
                "--particle-kinetic-energy-gev",
                "10.0abc",
                "--dry-run",
            ),
            "Valor numérico inválido para --particle-kinetic-energy-gev",
        ),
        NegativeCase(
            "particle_eta_trailing_junk",
            ("--particle-eta", "0.25abc", "--dry-run"),
            "Valor numérico inválido para --particle-eta",
        ),
        NegativeCase(
            "particle_phi_trailing_junk",
            ("--particle-phi", "-1.5abc", "--dry-run"),
            "Valor numérico inválido para --particle-phi",
        ),
        NegativeCase(
            "mu_nan",
            ("--mu", "nan", "--dry-run"),
            "Valor numérico inválido para --mu",
        ),
        NegativeCase(
            "mu_inf",
            ("--mu", "inf", "--dry-run"),
            "Valor numérico inválido para --mu",
        ),
        NegativeCase(
            "unknown_physics_list_dry_run",
            (
                "--physics-list",
                "THIS_PHYSICS_LIST_DOES_NOT_EXIST",
                "--dry-run",
            ),
            "Lista de física desconhecida",
        ),
    )

    passed = 0

    for case in cases:
        result = run(base + list(case.arguments))

        if result.returncode == 0:
            fail(f"{case.name}: invalid input was accepted", result)

        if case.expected_message not in result.stdout:
            fail(
                f"{case.name}: expected diagnostic "
                f"{case.expected_message!r} was not produced",
                result,
            )

        print(f"PASS {case.name}")
        passed += 1

    boundary_cases = (
        PositiveCase(
            "events_minimum",
            ("--events", "1", "--dry-run"),
        ),
        PositiveCase(
            "events_explicit_plus",
            ("--events", "+1", "--dry-run"),
        ),
        PositiveCase(
            "mu_zero",
            ("--mu", "0", "--dry-run"),
        ),
        PositiveCase(
            "mu_zero_scientific",
            ("--mu", "0e0", "--dry-run"),
        ),
        PositiveCase(
            "threads_minimum",
            ("--threads", "1", "--dry-run"),
        ),
        PositiveCase(
            "seed_minimum",
            ("--seed", "1", "--dry-run"),
        ),
        PositiveCase(
            "production_cut_tiny_positive",
            ("--production-cut-mm", "1e-300", "--dry-run"),
        ),
        PositiveCase(
            "particle_negative_pdg",
            ("--particle-pdg", "-11", "--dry-run"),
        ),
        PositiveCase(
            "particle_energy_tiny_positive",
            (
                "--particle-kinetic-energy-gev",
                "1e-300",
                "--dry-run",
            ),
        ),
        PositiveCase(
            "particle_eta_upper_boundary",
            ("--particle-eta", "1.8", "--dry-run"),
        ),
        PositiveCase(
            "particle_eta_lower_boundary",
            ("--particle-eta", "-1.8", "--dry-run"),
        ),
        PositiveCase(
            "particle_phi_upper_boundary",
            (
                "--particle-phi",
                "3.14159265358979323846",
                "--dry-run",
            ),
        ),
        PositiveCase(
            "particle_phi_lower_boundary",
            (
                "--particle-phi",
                "-3.14159265358979323846",
                "--dry-run",
            ),
        ),
    )

    boundary_passed = 0

    for case in boundary_cases:
        result = run(base + list(case.arguments))

        if result.returncode != 0:
            fail(f"{case.name}: valid boundary was rejected", result)

        if "Dry run concluído" not in result.stdout:
            fail(
                f"{case.name}: successful dry-run marker is missing",
                result,
            )

        print(f"PASS_BOUNDARY {case.name}")
        boundary_passed += 1

    print(f"CLI_NEGATIVE_CASES={len(cases)}")
    print(f"CLI_NEGATIVE_CASES_PASS={passed}")
    print(f"CLI_BOUNDARY_CASES={len(boundary_cases)}")
    print(f"CLI_BOUNDARY_CASES_PASS={boundary_passed}")
    print("VALID_DRY_RUN_GATE=PASS")
    print("CLI_INVALID_INPUT_GATE=PASS")
    print("CLI_BOUNDARY_INPUT_GATE=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
