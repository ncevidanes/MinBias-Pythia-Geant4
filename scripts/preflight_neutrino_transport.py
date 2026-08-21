#!/usr/bin/env python3
"""Validate the fixed Cycle 8 neutrino-transport pilot without transport."""

from __future__ import annotations

import argparse
import importlib.util
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


PROJECT_DIR = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = PROJECT_DIR / "scripts" / "validate_project.py"
PYTHIA_CONFIG = PROJECT_DIR / "config" / "pythia_minbias.cmnd"
PARTICLE_DECISION_HEADER = PROJECT_DIR / "include" / "ParticleDecision.hh"
PRIMARY_GENERATOR_SOURCE = PROJECT_DIR / "src" / "PrimaryGeneratorAction.cc"
EVENT_STATE_HEADER = PROJECT_DIR / "include" / "EventState.hh"
ROOT_OUTPUT_SOURCE = PROJECT_DIR / "src" / "RootOutput.cc"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "cycle8-neutrino-transport"


class PreflightError(RuntimeError):
    """A controlled Cycle 8 preflight failure."""


@dataclass(frozen=True)
class Run:
    role: str
    condition: str
    config: Path
    bunch_crossings: int
    transport_neutrinos: bool
    output_name: str


RUNS = (
    Run(
        "smoke",
        "on",
        PROJECT_DIR / "config" / "neutrinos_smoke.conf",
        3,
        True,
        "minbias_neutrinos_smoke.root",
    ),
    Run(
        "paired",
        "off",
        PROJECT_DIR / "config" / "neutrinos_off_100.conf",
        100,
        False,
        "minbias_neutrinos_off_100.root",
    ),
    Run(
        "paired",
        "on",
        PROJECT_DIR / "config" / "neutrinos_on_100.conf",
        100,
        True,
        "minbias_neutrinos_on_100.root",
    ),
)


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "cycle8_project_validator", VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise PreflightError(f"cannot load validator: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="prospective transactional output directory; it must not exist",
    )
    return parser.parse_args(argv)


def resolved_output_dir(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (PROJECT_DIR / path).resolve()


def ensure_output_absent(path: Path) -> None:
    if path.exists():
        raise PreflightError(f"output directory already exists: {path}")


def require_project_layout() -> None:
    required = (
        VALIDATOR_PATH,
        PYTHIA_CONFIG,
        PARTICLE_DECISION_HEADER,
        PRIMARY_GENERATOR_SOURCE,
        EVENT_STATE_HEADER,
        ROOT_OUTPUT_SOURCE,
    ) + tuple(run.config for run in RUNS)
    for path in required:
        if not path.is_file() or path.stat().st_size == 0:
            raise PreflightError(f"missing or empty project file: {path}")


def as_bool(value: str) -> bool:
    normalized = value.lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    raise PreflightError(f"invalid boolean: {value}")


def expect_equal(
    values: Mapping[str, str],
    key: str,
    expected: str,
    default: str | None = None,
) -> None:
    actual = values.get(key, default)
    if actual != expected:
        raise PreflightError(f"{key}: expected {expected!r}, found {actual!r}")


def expect_float(
    values: Mapping[str, str],
    key: str,
    expected: float,
    default: str | None = None,
) -> None:
    raw = values.get(key, default)
    try:
        actual = float(raw) if raw is not None else math.nan
    except ValueError as error:
        raise PreflightError(f"{key}: invalid number {raw!r}") from error
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
        raise PreflightError(f"{key}: expected {expected}, found {actual}")


def config_values(run: Run) -> dict[str, str]:
    return _load_validator().parse_config(run.config)


def validate_run_contract(run: Run) -> dict[str, str]:
    values = config_values(run)
    expect_equal(values, "generator_mode", "pythia", "pythia")
    expect_equal(values, "events", str(run.bunch_crossings))
    expect_equal(values, "first_bcid", "0", "0")
    expect_equal(values, "threads", "1")
    expect_equal(values, "seed_base", "512")
    expect_equal(values, "interaction_mode", "poisson")
    expect_float(values, "mean_interactions", 1.0)
    expect_equal(values, "fixed_interactions", "1", "1")
    expect_equal(values, "pythia_config", "pythia_minbias.cmnd")
    expect_equal(values, "physics_list", "FTFP_BERT_ATL")
    expect_float(values, "production_cut_mm", 1.0, "1.0")
    for key in (
        "beam_sigma_x_mm",
        "beam_sigma_y_mm",
        "beam_sigma_z_mm",
        "beam_sigma_t_ns",
    ):
        expect_float(values, key, 0.0, "0.0")
    expect_float(values, "max_abs_eta", 1.8, "1.8")
    if as_bool(values.get("transport_neutrinos", "false")) != run.transport_neutrinos:
        raise PreflightError(
            f"{run.role}/{run.condition}: unexpected neutrino transport policy"
        )
    if not as_bool(values.get("generator_audit", "false")):
        raise PreflightError(f"{run.role}/{run.condition}: generator audit is required")
    if not as_bool(values.get("check_overlaps", "false")):
        raise PreflightError(f"{run.role}/{run.condition}: overlap check is required")
    expect_equal(values, "print_every", "1", "10")
    output = Path(values["output"])
    if output.name != run.output_name:
        raise PreflightError(
            f"{run.role}/{run.condition}: unexpected output name {output.name!r}"
        )
    return values


def compare_config_maps(
    left: Mapping[str, str],
    right: Mapping[str, str],
    allowed_differences: set[str],
    label: str,
) -> tuple[str, ...]:
    differences = tuple(
        sorted(key for key in set(left) | set(right) if left.get(key) != right.get(key))
    )
    unexpected = set(differences) - allowed_differences
    missing = allowed_differences - set(differences)
    if unexpected or missing:
        details = []
        if unexpected:
            details.append("unexpected=" + ",".join(sorted(unexpected)))
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        raise PreflightError(f"{label}: invalid configuration differences ({'; '.join(details)})")
    return differences


def validate_pair_contract() -> tuple[str, ...]:
    off_values = validate_run_contract(RUNS[1])
    on_values = validate_run_contract(RUNS[2])
    return compare_config_maps(
        off_values,
        on_values,
        {"output", "transport_neutrinos"},
        "paired off/on",
    )


def validate_smoke_contract() -> tuple[str, ...]:
    smoke_values = validate_run_contract(RUNS[0])
    on_values = validate_run_contract(RUNS[2])
    return compare_config_maps(
        smoke_values,
        on_values,
        {"events", "output"},
        "smoke/on",
    )


def parse_pythia_commands(path: Path) -> dict[str, str]:
    commands: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.split("!", 1)[0].split("#", 1)[0].strip()
        if not line:
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise PreflightError(f"{path}:{number}: expected a PYTHIA assignment")
        key, value = key.strip(), value.strip()
        if key in commands:
            raise PreflightError(f"{path}:{number}: duplicate command: {key}")
        commands[key] = value
    return commands


def validate_pythia_contract() -> None:
    commands = parse_pythia_commands(PYTHIA_CONFIG)
    expected = {
        "Beams:idA": "2212",
        "Beams:idB": "2212",
        "Beams:eCM": "14000.",
        "SoftQCD:inelastic": "on",
        "Random:setSeed": "on",
    }
    for key, value in expected.items():
        if commands.get(key) != value:
            raise PreflightError(f"PYTHIA contract mismatch for {key}")
    if commands.get("SoftQCD:all", "off").lower() in {"on", "true", "1"}:
        raise PreflightError("SoftQCD:all must remain disabled")


def require_tokens(path: Path, tokens: Sequence[str]) -> None:
    source = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in source]
    if missing:
        raise PreflightError(
            f"source contract mismatch in {path}: missing " + ", ".join(missing)
        )


def validate_neutrino_source_contract() -> None:
    require_tokens(
        PARTICLE_DECISION_HEADER,
        (
            "kNeutrinoDisabled = 2",
            "absolute == 12",
            "absolute == 14",
            "absolute == 16",
            "absolute == 18",
            "isNeutrino && !input.transportNeutrinos",
        ),
    )
    require_tokens(
        PRIMARY_GENERATOR_SOURCE,
        (
            "decisionInput.transportNeutrinos = configuration_.transportNeutrinos",
            "state.RecordGeneratorDecision(rejectionCode)",
            "rejectionCode != ParticleRejectionCode::kAccepted",
        ),
    )
    require_tokens(
        EVENT_STATE_HEADER,
        ("transportedParticles", "rejectedNeutrinoDisabled", "unknownPdgParticles"),
    )
    require_tokens(
        ROOT_OUTPUT_SOURCE,
        (
            'CreateNtupleIColumn("transported_particles")',
            'CreateNtupleIColumn("rejected_neutrino_disabled")',
            'CreateNtupleIColumn("accepted_for_transport")',
            'CreateNtupleIColumn("rejection_code")',
            'CreateNtupleIColumn("transport_neutrinos")',
        ),
    )


def run_validator(run: Run) -> str:
    result = subprocess.run(
        [sys.executable, "-B", str(VALIDATOR_PATH), str(run.config)],
        cwd=PROJECT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise PreflightError(
            f"configuration validator failed for {run.role}/{run.condition}\n"
            f"{result.stdout.rstrip()}"
        )
    return result.stdout


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = resolved_output_dir(args.output_dir)
    ensure_output_absent(output_dir)
    require_project_layout()
    validate_pythia_contract()
    validate_neutrino_source_contract()
    pair_differences = validate_pair_contract()
    smoke_differences = validate_smoke_contract()

    for run in RUNS:
        validate_run_contract(run)
        run_validator(run)
        print(
            "CYCLE_8_RUN_PREFLIGHT=PASS "
            f"role={run.role} condition={run.condition} "
            f"bunch_crossings={run.bunch_crossings} seed=512"
        )

    ensure_output_absent(output_dir)
    total_bunch_crossings = sum(run.bunch_crossings for run in RUNS)
    paired_bunch_crossings = sum(
        run.bunch_crossings for run in RUNS if run.role == "paired"
    )
    print("PAIR_DIFFERENCES=" + ",".join(pair_differences))
    print("SMOKE_DIFFERENCES=" + ",".join(smoke_differences))
    print(
        "NEUTRINO_TRANSPORT_PREFLIGHT=PASS "
        f"runs={len(RUNS)} bunch_crossings={total_bunch_crossings} "
        f"paired_bunch_crossings={paired_bunch_crossings} "
        "seed=512 threads=1 transport_executed=NO"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, PreflightError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("NEUTRINO_TRANSPORT_PREFLIGHT=FAIL", file=sys.stderr)
        raise SystemExit(1)
