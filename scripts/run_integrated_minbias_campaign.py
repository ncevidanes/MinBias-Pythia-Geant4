#!/usr/bin/env python3
"""Run one transactional Cycle 7 minimum-bias stage or preflight all stages."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Mapping, Sequence


PROJECT_DIR = Path(__file__).resolve().parents[1]
PREFLIGHT_PATH = PROJECT_DIR / "scripts" / "preflight_integrated_minbias.py"
SIMULATOR = PROJECT_DIR / "build" / "pythia_geant"
AUDIT_MACRO = PROJECT_DIR / "scripts" / "audit_root.C"
ANALYZER_MACRO = PROJECT_DIR / "scripts" / "analyze_integrated_minbias.C"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "cycle7-integrated-minbias"


class CampaignError(RuntimeError):
    """A controlled integrated minimum-bias campaign failure."""


def _load_preflight():
    spec = importlib.util.spec_from_file_location("cycle7_preflight_contract", PREFLIGHT_PATH)
    if spec is None or spec.loader is None:
        raise CampaignError(f"cannot load preflight contract: {PREFLIGHT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PREFLIGHT = _load_preflight()
STAGES = PREFLIGHT.STAGES
SAMPLINGS = PREFLIGHT.SAMPLINGS


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
        help="build, test, and resolve all three stages without transport",
    )
    parser.add_argument(
        "--stage",
        choices=tuple(stage.phase for stage in STAGES),
        help="single stage to execute; required unless --dry-run is used",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="prospective directory for dry-run or final directory for one stage",
    )
    parser.add_argument(
        "--build-jobs",
        type=positive_integer,
        default=positive_integer(os.environ.get("BUILD_JOBS", "1")),
        help="parallel build jobs (default: BUILD_JOBS or 1)",
    )
    return parser.parse_args(argv)


def stage_by_phase(phase: str):
    for stage in STAGES:
        if stage.phase == phase:
            return stage
    raise CampaignError(f"unknown Cycle 7 stage: {phase}")


def resolved_output_dir(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (PROJECT_DIR / path).resolve()


def ensure_output_absent(path: Path) -> None:
    if path.exists():
        raise CampaignError(f"output directory already exists: {path}")


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise CampaignError(f"required command not found: {name}")


def require_project_layout(*, full_run: bool) -> None:
    for command in ("cmake", "ctest", "git"):
        require_command(command)
    for path in (PREFLIGHT_PATH, AUDIT_MACRO, ANALYZER_MACRO):
        if not path.is_file() or path.stat().st_size == 0:
            raise CampaignError(f"missing or empty project file: {path}")
    if full_run:
        require_command("root")
        if not Path("/usr/bin/time").is_file():
            raise CampaignError("required command not found: /usr/bin/time")


def run_checked(
    command: Sequence[str | Path],
    *,
    capture: bool = False,
    environment: Mapping[str, str] | None = None,
) -> str:
    result = subprocess.run(
        [str(item) for item in command],
        cwd=PROJECT_DIR,
        env=dict(environment) if environment is not None else None,
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


def run_and_tee(command: Sequence[str | Path], log_path: Path) -> str:
    with log_path.open("w", encoding="utf-8", newline="\n") as log_stream:
        process = subprocess.Popen(
            [str(item) for item in command],
            cwd=PROJECT_DIR,
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
    run_checked(
        (
            "cmake", "-S", ".", "-B", "build",
            "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_TESTING=ON",
        )
    )
    run_checked(("cmake", "--build", "build", "--parallel", str(build_jobs)))
    run_checked(("ctest", "--test-dir", "build", "--output-on-failure"))
    if not SIMULATOR.is_file() or not os.access(SIMULATOR, os.X_OK):
        raise CampaignError(f"simulator was not produced: {SIMULATOR}")


def simulator_arguments(stage, root_file: Path, *, dry_run: bool = False) -> tuple[str, ...]:
    arguments = (
        str(SIMULATOR),
        "--config", str(stage.config),
        "--events", str(stage.bunch_crossings),
        "--mu", format(stage.mean_interactions, ".12g"),
        "--threads", "1",
        "--seed", str(stage.seed),
        "--output", str(root_file),
    )
    return arguments + (("--dry-run",) if dry_run else ())


def run_contract_preflight(output_dir: Path) -> None:
    output = run_checked(
        (sys.executable, "-B", PREFLIGHT_PATH, "--output-dir", output_dir),
        capture=True,
    )
    if "INTEGRATED_MINBIAS_PREFLIGHT=PASS" not in output:
        raise CampaignError("Stage 7.0A contract preflight did not pass")


def preflight_stage(stage, output_dir: Path) -> None:
    ensure_output_absent(output_dir)
    prospective_root = output_dir / f"stage{stage.phase.replace('.', '')}-{stage.name}.root"
    output = run_checked(
        simulator_arguments(stage, prospective_root, dry_run=True),
        capture=True,
    )
    if "Dry run concluído; nenhuma simulação foi executada." not in output:
        raise CampaignError(f"simulator dry-run marker missing for stage {stage.phase}")
    ensure_output_absent(output_dir)


def git_provenance() -> str:
    commit = run_checked(("git", "rev-parse", "HEAD"), capture=True).strip()
    if len(commit) != 40:
        raise CampaignError("git rev-parse did not return a full commit SHA")
    tracked_status = run_checked(
        ("git", "status", "--porcelain", "--untracked-files=no"), capture=True
    )
    if tracked_status.strip():
        raise CampaignError("tracked worktree must be clean before transport")
    return commit


def root_quote(value: str | Path) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def root_macro_call(macro: Path, *arguments: str | Path) -> str:
    return f"{macro}({','.join(root_quote(item) for item in arguments)})"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_validation(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = raw_line.partition("=")
        if not separator or not key or key in values:
            raise CampaignError(f"invalid validation line: {raw_line!r}")
        values[key] = value
    return values


def parse_nonnegative_float(row: Mapping[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, ValueError) as error:
        raise CampaignError(f"invalid analysis value for {key}") from error
    if not math.isfinite(value) or value < 0.0:
        raise CampaignError(f"analysis value must be finite and nonnegative: {key}")
    return value


def validate_analysis_products(stage, analysis_dir: Path) -> None:
    summary_path = analysis_dir / "integrated_summary.csv"
    sampling_path = analysis_dir / "sampling_summary.csv"
    validation_path = analysis_dir / "integrated_validation.txt"
    for path in (summary_path, sampling_path, validation_path):
        if not path.is_file() or path.stat().st_size == 0:
            raise CampaignError(f"missing analysis product: {path}")

    with summary_path.open(newline="", encoding="utf-8") as stream:
        summary_rows = list(csv.DictReader(stream))
    if len(summary_rows) != 1:
        raise CampaignError("integrated summary must contain exactly one row")
    row = summary_rows[0]
    if row.get("stage") != stage.phase:
        raise CampaignError("analysis stage does not match requested stage")
    if int(row["bunch_crossings"]) != stage.bunch_crossings:
        raise CampaignError("analysis bunch-crossing count mismatch")
    if not math.isclose(float(row["mean_interactions"]), stage.mean_interactions):
        raise CampaignError("analysis interaction mean mismatch")
    if int(row["seed"]) != stage.seed or int(row["threads"]) != 1:
        raise CampaignError("analysis seed or thread contract mismatch")
    if int(row["transport_neutrinos"]) != 0:
        raise CampaignError("analysis reports transported neutrinos")
    if int(row["generator_audit"]) != int(stage.generator_audit):
        raise CampaignError("analysis generator-audit policy mismatch")
    if int(row["check_overlaps"]) != int(stage.check_overlaps):
        raise CampaignError("analysis overlap-check policy mismatch")

    requested = int(row["requested_interactions"])
    generated = int(row["generated_interactions"])
    failures = int(row["generation_failures"])
    if min(requested, generated, failures) < 0 or requested != generated + failures:
        raise CampaignError("analysis interaction accounting mismatch")
    if int(row["unknown_pdg_particles"]) != 0:
        raise CampaignError("analysis reports unknown PDGs")
    total_energy = parse_nonnegative_float(row, "total_energy_mev")
    poisson_z = parse_nonnegative_float(row, "poisson_z")
    if stage.phase != "7.1" and poisson_z > 5.0:
        raise CampaignError("analysis Poisson count lies outside five sigma")

    with sampling_path.open(newline="", encoding="utf-8") as stream:
        sampling_rows = list(csv.DictReader(stream))
    if len(sampling_rows) != len(SAMPLINGS):
        raise CampaignError("sampling summary must contain ten rows")
    sampling_energies: list[float] = []
    fractions: list[float] = []
    for sampling, (name, sampling_row) in enumerate(zip(SAMPLINGS, sampling_rows)):
        if int(sampling_row["sampling"]) != sampling or sampling_row["name"] != name:
            raise CampaignError("sampling summary order or name mismatch")
        hit_count = int(sampling_row["hit_count"])
        if hit_count < 0:
            raise CampaignError("negative sampling hit count")
        sampling_energies.append(
            parse_nonnegative_float(sampling_row, "total_energy_mev")
        )
        fractions.append(parse_nonnegative_float(sampling_row, "energy_fraction"))
        if stage.phase != "7.1" and hit_count == 0:
            raise CampaignError("required sampling is not observed")
    expected_fraction_sum = 1.0 if total_energy > 0.0 else 0.0
    if not math.isclose(
        math.fsum(sampling_energies), total_energy, rel_tol=1e-10, abs_tol=1e-9
    ):
        raise CampaignError("sampling energies do not close")
    if not math.isclose(math.fsum(fractions), expected_fraction_sum, rel_tol=0.0, abs_tol=1e-9):
        raise CampaignError("sampling energy fractions do not close")

    validation = read_validation(validation_path)
    expected_sampling_marker = "STRUCTURAL" if stage.phase == "7.1" else "PASS"
    expected_poisson_marker = "NOT_APPLICABLE" if stage.phase == "7.1" else "PASS"
    expected = {
        "INTEGRATED_MINBIAS_ANALYSIS_RESULT": "PASS",
        "stage": stage.phase,
        "energy_closure": "PASS",
        "particle_accounting": "PASS",
        "sampling_coverage": expected_sampling_marker,
        "poisson_consistency": expected_poisson_marker,
    }
    for key, value in expected.items():
        if validation.get(key) != value:
            raise CampaignError(f"analysis validation mismatch for {key}")


def execute_stage(stage, output_dir: Path, git_commit: str) -> None:
    ensure_output_absent(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    try:
        root_file = staging_dir / f"stage{stage.phase.replace('.', '')}-{stage.name}.root"
        simulation_log = staging_dir / "simulation.log"
        resource_log = staging_dir / "resource_usage.txt"
        audit_log = staging_dir / "root_audit.log"
        analysis_log = staging_dir / "integrated_analysis.log"
        analysis_dir = staging_dir / "analysis"

        run_and_tee(
            ("/usr/bin/time", "-v", "-o", resource_log, *simulator_arguments(stage, root_file)),
            simulation_log,
        )
        if not root_file.is_file() or root_file.stat().st_size == 0:
            raise CampaignError(f"simulation did not produce ROOT output: {root_file}")
        root_sha256 = sha256_file(root_file)

        audit_output = run_and_tee(
            ("root", "-l", "-b", "-q", root_macro_call(AUDIT_MACRO, root_file, git_commit)),
            audit_log,
        )
        if "AUDIT_RESULT=PASS" not in audit_output:
            raise CampaignError("ROOT structural audit did not pass")
        if sha256_file(root_file) != root_sha256:
            raise CampaignError("ROOT hash changed during structural audit")

        analysis_output = run_and_tee(
            (
                "root", "-l", "-b", "-q",
                root_macro_call(ANALYZER_MACRO, root_file, stage.phase, analysis_dir),
            ),
            analysis_log,
        )
        if "INTEGRATED_MINBIAS_ANALYSIS_RESULT=PASS" not in analysis_output:
            raise CampaignError("integrated minimum-bias analysis did not pass")
        if sha256_file(root_file) != root_sha256:
            raise CampaignError("ROOT hash changed during integrated analysis")
        validate_analysis_products(stage, analysis_dir)

        manifest_path = staging_dir / "campaign_manifest.tsv"
        with manifest_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "stage", "name", "bunch_crossings", "mean_interactions",
                    "seed", "threads", "git_commit", "root_file", "root_sha256",
                ),
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerow({
                "stage": stage.phase,
                "name": stage.name,
                "bunch_crossings": stage.bunch_crossings,
                "mean_interactions": format(stage.mean_interactions, ".12g"),
                "seed": stage.seed,
                "threads": 1,
                "git_commit": git_commit,
                "root_file": root_file.name,
                "root_sha256": root_sha256,
            })
        checksum_path = staging_dir / "campaign_artifacts.sha256"
        checksum_lines = []
        for artifact in sorted(path for path in staging_dir.rglob("*") if path.is_file()):
            if artifact != checksum_path:
                checksum_lines.append(
                    f"{sha256_file(artifact)}  {artifact.relative_to(staging_dir)}\n"
                )
        checksum_path.write_text("".join(checksum_lines), encoding="utf-8")
        os.replace(staging_dir, output_dir)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    print(
        "INTEGRATED_MINBIAS_STAGE_RESULT=PASS "
        f"stage={stage.phase} bunch_crossings={stage.bunch_crossings} "
        f"mean_interactions={stage.mean_interactions:g}"
    )
    print(f"INTEGRATED_MINBIAS_STAGE_OUTPUT_DIR={output_dir}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = resolved_output_dir(args.output_dir)
    if args.dry_run and args.stage is not None:
        raise CampaignError("--stage cannot be combined with --dry-run")
    if not args.dry_run and args.stage is None:
        raise CampaignError("--stage is required for transport")

    require_project_layout(full_run=not args.dry_run)
    build_project(args.build_jobs)
    ensure_output_absent(output_dir)
    run_contract_preflight(output_dir)
    for stage in STAGES:
        preflight_stage(stage, output_dir)
    ensure_output_absent(output_dir)
    if args.dry_run:
        print(
            "INTEGRATED_MINBIAS_EXECUTOR_PREFLIGHT=PASS "
            "stages=3 bunch_crossings=3503 expected_interactions=151003 "
            "transport_executed=NO"
        )
        return 0

    stage = stage_by_phase(args.stage)
    execute_stage(stage, output_dir, git_provenance())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CampaignError, OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("INTEGRATED_MINBIAS_CAMPAIGN_RESULT=FAIL", file=sys.stderr)
        raise SystemExit(1)
