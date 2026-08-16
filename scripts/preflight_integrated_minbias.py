#!/usr/bin/env python3
"""Validate the fixed Cycle 7 integrated minimum-bias contract without transport."""

from __future__ import annotations

import argparse
import importlib.util
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


PROJECT_DIR = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = PROJECT_DIR / "scripts" / "validate_project.py"
PYTHIA_CONFIG = PROJECT_DIR / "config" / "pythia_minbias.cmnd"
ROOT_OUTPUT_SOURCE = PROJECT_DIR / "src" / "RootOutput.cc"
SAMPLING_SOURCE = PROJECT_DIR / "src" / "Sampling.cc"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "cycle7-integrated-minbias"

ROOT_BRANCHES = {
    "events": (
        "run", "event", "bcid", "mu_configured",
        "n_interactions_requested", "n_interactions_generated",
        "generation_failures", "generator_particles", "transported_particles",
        "unknown_pdg_particles", "total_edep_mev", "rejected_not_final",
        "rejected_neutrino_disabled", "rejected_invisible_non_neutrino",
        "rejected_outside_eta_acceptance", "unlineaged_steps",
        "segmentation_failures",
    ),
    "hits": (
        "run", "event", "bcid", "subevent", "cell_id", "subdetector",
        "sampling", "side", "eta_index", "phi_index", "eta_center",
        "phi_center", "edep_mev", "time_mean_ns", "time_first_ns",
        "leading_pdg", "leading_track_id", "leading_parent_id", "steps",
    ),
    "generator": (
        "run", "event", "bcid", "subevent", "index", "pdg", "status",
        "mother1", "mother2", "daughter1", "daughter2", "is_final",
        "is_visible", "px_gev", "py_gev", "pz_gev", "energy_gev",
        "mass_gev", "eta", "phi", "x_prod_mm", "y_prod_mm", "z_prod_mm",
        "t_prod_mm_over_c", "accepted_for_transport", "rejection_code",
    ),
    "metadata": (
        "schema_version", "project_version", "git_commit", "git_describe",
        "root_version", "geant4_version", "pythia_version", "run", "events",
        "first_bcid", "threads", "seed_base", "geant4_master_seed",
        "pythia_seed_base", "pythia_worker_seed_stride", "pythia_seed_max",
        "interaction_mode", "mean_interactions", "fixed_interactions",
        "pythia_config", "physics_list", "production_cut_mm",
        "beam_sigma_x_mm", "beam_sigma_y_mm", "beam_sigma_z_mm",
        "beam_sigma_t_ns", "max_abs_eta", "transport_neutrinos",
        "generator_audit", "check_overlaps", "print_every", "config_file",
        "output_file", "normalized_config", "generator_mode",
        "single_particle_pdg", "single_particle_kinetic_energy_gev",
        "single_particle_eta", "single_particle_phi",
    ),
}

SAMPLINGS = (
    "PSB", "EMB1", "EMB2", "EMB3", "TileCal1", "TileCal2", "TileCal3",
    "TileExt1", "TileExt2", "TileExt3",
)


class PreflightError(RuntimeError):
    """A controlled Stage 7.0A failure."""


@dataclass(frozen=True)
class Stage:
    phase: str
    name: str
    config: Path
    bunch_crossings: int
    mean_interactions: float
    seed: int
    generator_audit: bool
    check_overlaps: bool

    @property
    def expected_interactions(self) -> float:
        return self.bunch_crossings * self.mean_interactions


STAGES = (
    Stage("7.1", "smoke", PROJECT_DIR / "config" / "smoke.conf", 3, 1.0, 512, True, True),
    Stage("7.2", "statistical", PROJECT_DIR / "config" / "poisson_mu2.conf", 500, 2.0, 513, True, True),
    Stage("7.3", "production", PROJECT_DIR / "config" / "production.conf", 3000, 50.0, 512, False, False),
)


def _load_validator():
    spec = importlib.util.spec_from_file_location("cycle7_project_validator", VALIDATOR_PATH)
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
    required = (VALIDATOR_PATH, PYTHIA_CONFIG, ROOT_OUTPUT_SOURCE, SAMPLING_SOURCE)
    required += tuple(stage.config for stage in STAGES)
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


def expect_equal(values: Mapping[str, str], key: str, expected: str, default: str | None = None) -> None:
    actual = values.get(key, default)
    if actual != expected:
        raise PreflightError(f"{key}: expected {expected!r}, found {actual!r}")


def expect_float(values: Mapping[str, str], key: str, expected: float, default: str | None = None) -> None:
    raw = values.get(key, default)
    try:
        actual = float(raw) if raw is not None else math.nan
    except ValueError as error:
        raise PreflightError(f"{key}: invalid number {raw!r}") from error
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
        raise PreflightError(f"{key}: expected {expected}, found {actual}")


def validate_stage_contract(stage: Stage) -> None:
    validator = _load_validator()
    values = validator.parse_config(stage.config)
    expect_equal(values, "generator_mode", "pythia", "pythia")
    expect_equal(values, "events", str(stage.bunch_crossings))
    expect_equal(values, "first_bcid", "0", "0")
    expect_equal(values, "threads", "1")
    expect_equal(values, "seed_base", str(stage.seed))
    expect_equal(values, "interaction_mode", "poisson")
    expect_float(values, "mean_interactions", stage.mean_interactions)
    expect_equal(values, "fixed_interactions", "1", "1")
    expect_equal(values, "pythia_config", "pythia_minbias.cmnd")
    expect_equal(values, "physics_list", "FTFP_BERT_ATL")
    expect_float(values, "production_cut_mm", 1.0, "1.0")
    for key in ("beam_sigma_x_mm", "beam_sigma_y_mm", "beam_sigma_z_mm", "beam_sigma_t_ns"):
        expect_float(values, key, 0.0, "0.0")
    expect_float(values, "max_abs_eta", 1.8, "1.8")
    if as_bool(values.get("transport_neutrinos", "false")):
        raise PreflightError(f"{stage.name}: neutrino transport must be disabled")
    if as_bool(values.get("generator_audit", "false")) != stage.generator_audit:
        raise PreflightError(f"{stage.name}: unexpected generator_audit policy")
    if as_bool(values.get("check_overlaps", "false")) != stage.check_overlaps:
        raise PreflightError(f"{stage.name}: unexpected check_overlaps policy")


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


def validate_root_source_contract() -> None:
    source = ROOT_OUTPUT_SOURCE.read_text(encoding="utf-8")
    for tree, branches in ROOT_BRANCHES.items():
        match = re.search(
            rf'CreateNtuple\("{re.escape(tree)}".*?FinishNtuple\(\);',
            source,
            flags=re.DOTALL,
        )
        if match is None:
            raise PreflightError(f"ROOT tree definition missing: {tree}")
        block = match.group(0)
        for branch in branches:
            if re.search(
                rf'Column\(\s*"{re.escape(branch)}"\s*\)', block
            ) is None:
                raise PreflightError(f"ROOT branch definition missing: {tree}.{branch}")


def validate_sampling_source_contract() -> None:
    source = SAMPLING_SOURCE.read_text(encoding="utf-8")
    missing = [name for name in SAMPLINGS if f'"{name}"' not in source]
    if missing:
        raise PreflightError("sampling definitions missing: " + ", ".join(missing))


def run_validator(stage: Stage) -> str:
    result = subprocess.run(
        [sys.executable, "-B", str(VALIDATOR_PATH), str(stage.config)],
        cwd=PROJECT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise PreflightError(
            f"configuration validator failed for {stage.name}\n{result.stdout.rstrip()}"
        )
    return result.stdout


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = resolved_output_dir(args.output_dir)
    ensure_output_absent(output_dir)
    require_project_layout()
    validate_pythia_contract()
    validate_root_source_contract()
    validate_sampling_source_contract()

    for stage in STAGES:
        validate_stage_contract(stage)
        run_validator(stage)
        print(
            f"CYCLE_7_STAGE_PREFLIGHT=PASS phase={stage.phase} name={stage.name} "
            f"bunch_crossings={stage.bunch_crossings} "
            f"mean_interactions={stage.mean_interactions:g} seed={stage.seed}"
        )

    ensure_output_absent(output_dir)
    total_bunch_crossings = sum(stage.bunch_crossings for stage in STAGES)
    expected_interactions = sum(stage.expected_interactions for stage in STAGES)
    print(
        "INTEGRATED_MINBIAS_PREFLIGHT=PASS "
        f"stages={len(STAGES)} bunch_crossings={total_bunch_crossings} "
        f"expected_interactions={expected_interactions:g} trees={len(ROOT_BRANCHES)} "
        f"samplings={len(SAMPLINGS)} threads=1 transport_executed=NO"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, PreflightError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("INTEGRATED_MINBIAS_PREFLIGHT=FAIL", file=sys.stderr)
        raise SystemExit(1)
