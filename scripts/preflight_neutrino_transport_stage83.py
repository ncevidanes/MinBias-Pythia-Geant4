#!/usr/bin/env python3
"""Validate the fixed-budget Cycle 8.3 matrix without transport."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


PROJECT_DIR = Path(__file__).resolve().parents[1]
PILOT_PREFLIGHT_PATH = PROJECT_DIR / "scripts" / "preflight_neutrino_transport.py"
SPEC_PATH = (
    PROJECT_DIR
    / "docs"
    / "cycle-8-neutrino-transport-systematics"
    / "stage-8.3-production-spec.md"
)
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "cycle8-neutrino-transport-stage83"
SEEDS = (1512, 2512, 3512)
EVENTS_PER_CONDITION = 1000
THREADS = 1
MINIMUM_FREE_BYTES = 5 * 1024**3


class Stage83PreflightError(RuntimeError):
    """A controlled Stage 8.3 preflight failure."""


def _load_pilot_preflight():
    spec = importlib.util.spec_from_file_location(
        "cycle8_pilot_preflight_for_stage83", PILOT_PREFLIGHT_PATH
    )
    if spec is None or spec.loader is None:
        raise Stage83PreflightError(
            f"cannot load pilot preflight: {PILOT_PREFLIGHT_PATH}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PILOT = _load_pilot_preflight()


@dataclass(frozen=True)
class ProductionRun:
    seed: int
    condition: str
    transport_neutrinos: bool
    bunch_crossings: int = EVENTS_PER_CONDITION
    threads: int = THREADS

    @property
    def output_name(self) -> str:
        return f"seed-{self.seed}/paired-{self.condition}-1000.root"


RUNS = tuple(
    ProductionRun(seed, condition, condition == "on")
    for seed in SEEDS
    for condition in ("off", "on")
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="prospective Stage 8.3 output directory; it must not exist",
    )
    return parser.parse_args(argv)


def resolved_output_dir(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (PROJECT_DIR / path).resolve()


def ensure_output_absent(path: Path) -> None:
    if path.exists():
        raise Stage83PreflightError(f"output directory already exists: {path}")


def validate_storage_budget(output_dir: Path) -> int:
    probe = output_dir.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    available = shutil.disk_usage(probe).free
    if available < MINIMUM_FREE_BYTES:
        raise Stage83PreflightError(
            f"insufficient storage: available={available} "
            f"required={MINIMUM_FREE_BYTES}"
        )
    return available


def validate_matrix(runs: Sequence[ProductionRun] = RUNS) -> None:
    expected = [
        (seed, condition, condition == "on", EVENTS_PER_CONDITION, THREADS)
        for seed in SEEDS
        for condition in ("off", "on")
    ]
    actual = [
        (
            run.seed,
            run.condition,
            run.transport_neutrinos,
            run.bunch_crossings,
            run.threads,
        )
        for run in runs
    ]
    if actual != expected:
        raise Stage83PreflightError("Stage 8.3 run matrix differs from contract")
    if len({run.output_name for run in runs}) != len(runs):
        raise Stage83PreflightError("Stage 8.3 output names are not unique")


def require_contract_files() -> None:
    for path in (PILOT_PREFLIGHT_PATH, SPEC_PATH):
        if not path.is_file() or path.stat().st_size == 0:
            raise Stage83PreflightError(f"missing or empty contract file: {path}")


def validate_specification() -> None:
    source = SPEC_PATH.read_text(encoding="utf-8")
    required = (
        "1512, 2512, and 3512",
        "exactly 1,000 bunch crossings",
        "fixed matrix",
        "must not stop early",
        "pilot is reported separately",
        "at least 5 GiB",
        "transport_executed=NO",
    )
    missing = [token for token in required if token not in source]
    if missing:
        raise Stage83PreflightError(
            "Stage 8.3 specification missing: " + ", ".join(missing)
        )


def validate_pilot_templates() -> None:
    PILOT.validate_pythia_contract()
    PILOT.validate_neutrino_source_contract()
    if PILOT.validate_pair_contract() != ("output", "transport_neutrinos"):
        raise Stage83PreflightError("pilot OFF/ON templates are not canonical")
    for run in (PILOT.RUNS[1], PILOT.RUNS[2]):
        PILOT.validate_run_contract(run)
        PILOT.run_validator(run)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = resolved_output_dir(args.output_dir)
    ensure_output_absent(output_dir)
    available_storage = validate_storage_budget(output_dir)
    require_contract_files()
    validate_matrix()
    validate_specification()
    validate_pilot_templates()

    for run in RUNS:
        print(
            "CYCLE_8_STAGE83_RUN_PREFLIGHT=PASS "
            f"seed={run.seed} condition={run.condition} "
            f"bunch_crossings={run.bunch_crossings} threads={run.threads}"
        )

    print(
        "CYCLE_8_STAGE83_STORAGE_PREFLIGHT=PASS "
        f"available_bytes={available_storage} "
        f"minimum_bytes={MINIMUM_FREE_BYTES}"
    )

    ensure_output_absent(output_dir)
    print(
        "NEUTRINO_TRANSPORT_STAGE83_PREFLIGHT=PASS "
        "runs=6 seed_pairs=3 bunch_crossings=6000 "
        "paired_bunch_crossings=3000 events_per_condition=1000 "
        "seeds=1512,2512,3512 threads=1 stopping_rule=fixed_budget "
        "transport_executed=NO"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, Stage83PreflightError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("NEUTRINO_TRANSPORT_STAGE83_PREFLIGHT=FAIL", file=sys.stderr)
        raise SystemExit(1)
