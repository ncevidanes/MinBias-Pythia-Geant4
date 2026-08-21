#!/usr/bin/env python3
"""Run the transactional Cycle 8 paired neutrino-transport pilot."""

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
PREFLIGHT_PATH = PROJECT_DIR / "scripts" / "preflight_neutrino_transport.py"
SIMULATOR = PROJECT_DIR / "build" / "pythia_geant"
AUDIT_MACRO = PROJECT_DIR / "scripts" / "audit_root.C"
ANALYZER_MACRO = PROJECT_DIR / "scripts" / "analyze_neutrino_transport.C"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "cycle8-neutrino-transport"


class CampaignError(RuntimeError):
    """A controlled Cycle 8 campaign failure."""


def _load_preflight():
    spec = importlib.util.spec_from_file_location(
        "cycle8_neutrino_preflight_contract", PREFLIGHT_PATH
    )
    if spec is None or spec.loader is None:
        raise CampaignError(f"cannot load preflight contract: {PREFLIGHT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PREFLIGHT = _load_preflight()
RUNS = PREFLIGHT.RUNS


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
        help="build, test, and resolve all pilot runs without transport",
    )
    parser.add_argument(
        "--execute-pilot",
        action="store_true",
        help="execute the complete three-run pilot transaction",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="prospective directory for dry-run or final campaign directory",
    )
    parser.add_argument(
        "--build-jobs",
        type=positive_integer,
        default=positive_integer(os.environ.get("BUILD_JOBS", "1")),
        help="parallel build jobs (default: BUILD_JOBS or 1)",
    )
    return parser.parse_args(argv)


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
    required = (PREFLIGHT_PATH, AUDIT_MACRO, ANALYZER_MACRO)
    required += tuple(run.config for run in RUNS)
    for path in required:
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
            "cmake",
            "-S",
            ".",
            "-B",
            "build",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DBUILD_TESTING=ON",
        )
    )
    run_checked(("cmake", "--build", "build", "--parallel", str(build_jobs)))
    run_checked(("ctest", "--test-dir", "build", "--output-on-failure"))
    if not SIMULATOR.is_file() or not os.access(SIMULATOR, os.X_OK):
        raise CampaignError(f"simulator was not produced: {SIMULATOR}")


def run_by(role: str, condition: str):
    for run in RUNS:
        if run.role == role and run.condition == condition:
            return run
    raise CampaignError(f"unknown Cycle 8 run: {role}/{condition}")


def simulator_arguments(
    run, root_file: Path, *, dry_run: bool = False
) -> tuple[str, ...]:
    arguments = (
        str(SIMULATOR),
        "--config",
        str(run.config),
        "--events",
        str(run.bunch_crossings),
        "--mu",
        "1",
        "--threads",
        "1",
        "--seed",
        "512",
        "--output",
        str(root_file),
    )
    return arguments + (("--dry-run",) if dry_run else ())


def run_contract_preflight(output_dir: Path) -> None:
    output = run_checked(
        (sys.executable, "-B", PREFLIGHT_PATH, "--output-dir", output_dir),
        capture=True,
    )
    if "NEUTRINO_TRANSPORT_PREFLIGHT=PASS" not in output:
        raise CampaignError("Cycle 8 contract preflight did not pass")


def preflight_run(run, output_dir: Path) -> None:
    ensure_output_absent(output_dir)
    prospective_root = output_dir / root_filename(run)
    output = run_checked(
        simulator_arguments(run, prospective_root, dry_run=True), capture=True
    )
    if "Dry run concluído; nenhuma simulação foi executada." not in output:
        raise CampaignError(
            f"simulator dry-run marker missing for {run.role}/{run.condition}"
        )
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


def root_filename(run) -> str:
    return f"{run.role}-{run.condition}-{run.bunch_crossings}.root"


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


def parse_nonnegative_float(row: Mapping[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, ValueError) as error:
        raise CampaignError(f"invalid analysis value for {key}") from error
    if not math.isfinite(value) or value < 0.0:
        raise CampaignError(f"analysis value must be finite and nonnegative: {key}")
    return value


def read_validation(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = raw_line.partition("=")
        if not separator or not key or key in values:
            raise CampaignError(f"invalid validation line: {raw_line!r}")
        values[key] = value
    return values


def validate_analysis_products(analysis_dir: Path) -> None:
    summary_path = analysis_dir / "paired_summary.csv"
    events_path = analysis_dir / "paired_events.csv"
    validation_path = analysis_dir / "paired_validation.txt"
    for path in (summary_path, events_path, validation_path):
        if not path.is_file() or path.stat().st_size == 0:
            raise CampaignError(f"missing analysis product: {path}")

    with summary_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise CampaignError("paired summary must contain exactly one row")
    row = rows[0]
    if int(row["events"]) != 100 or int(row["seed"]) != 512:
        raise CampaignError("paired summary event or seed contract mismatch")
    if not math.isclose(float(row["mean_interactions"]), 1.0):
        raise CampaignError("paired summary interaction mean mismatch")
    eligible = int(row["eligible_neutrinos"])
    outside = int(row["outside_acceptance_neutrinos"])
    transported_delta = int(row["transported_delta"])
    if eligible <= 0:
        raise CampaignError("pilot contains no eligible neutrinos")
    if transported_delta != eligible:
        raise CampaignError("transported-particle delta does not equal eligibility")
    if outside < 0:
        raise CampaignError("negative outside-acceptance neutrino count")
    for key in (
        "off_total_energy_mev",
        "on_total_energy_mev",
        "energy_abs_delta_mev",
        "hit_energy_l1_mev",
        "max_abs_hit_delta_mev",
    ):
        parse_nonnegative_float(row, key)
    for key in (
        "off_hit_count",
        "on_hit_count",
        "changed_hit_cells",
        "missing_off_hit_cells",
        "missing_on_hit_cells",
        "generator_entries",
    ):
        if int(row[key]) < 0:
            raise CampaignError(f"negative analysis count: {key}")

    with events_path.open(newline="", encoding="utf-8") as stream:
        event_rows = list(csv.DictReader(stream))
    if len(event_rows) != 100:
        raise CampaignError("paired event table must contain 100 rows")
    observed_ids = []
    summed_eligible = 0
    summed_outside = 0
    for event_row in event_rows:
        event_id = int(event_row["event"])
        observed_ids.append(event_id)
        event_eligible = int(event_row["eligible_neutrinos"])
        event_outside = int(event_row["outside_acceptance_neutrinos"])
        if event_eligible < 0:
            raise CampaignError("negative event neutrino eligibility")
        if event_outside < 0:
            raise CampaignError("negative event outside-acceptance count")
        if (
            int(event_row["on_transported"])
            - int(event_row["off_transported"])
            != event_eligible
        ):
            raise CampaignError("event transported-particle delta mismatch")
        parse_nonnegative_float(event_row, "off_energy_mev")
        parse_nonnegative_float(event_row, "on_energy_mev")
        parse_nonnegative_float(event_row, "energy_abs_delta_mev")
        summed_eligible += event_eligible
        summed_outside += event_outside
    if observed_ids != list(range(100)):
        raise CampaignError("paired event identifiers are not exactly 0..99")
    if summed_eligible != eligible:
        raise CampaignError("event and summary neutrino eligibility disagree")
    if summed_outside != outside:
        raise CampaignError("event and summary outside-acceptance counts disagree")

    validation = read_validation(validation_path)
    expected = {
        "NEUTRINO_TRANSPORT_ANALYSIS_RESULT": "PASS",
        "metadata_pairing": "PASS",
        "event_pairing": "PASS",
        "generator_pairing": "PASS",
        "particle_accounting": "PASS",
        "eligible_neutrinos": str(eligible),
        "outside_acceptance_neutrinos": str(outside),
        "energy_difference_classification": "REPORTED_NOT_ASSUMED",
    }
    for key, value in expected.items():
        if validation.get(key) != value:
            raise CampaignError(f"analysis validation mismatch for {key}")


def execute_pilot(output_dir: Path, git_commit: str) -> None:
    ensure_output_absent(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    try:
        root_files: dict[tuple[str, str], Path] = {}
        root_hashes: dict[tuple[str, str], str] = {}
        for run in RUNS:
            label = f"{run.role}-{run.condition}"
            root_file = staging_dir / root_filename(run)
            simulation_log = staging_dir / f"{label}-simulation.log"
            resource_log = staging_dir / f"{label}-resource-usage.txt"
            audit_log = staging_dir / f"{label}-root-audit.log"

            run_and_tee(
                (
                    "/usr/bin/time",
                    "-v",
                    "-o",
                    resource_log,
                    *simulator_arguments(run, root_file),
                ),
                simulation_log,
            )
            if not root_file.is_file() or root_file.stat().st_size == 0:
                raise CampaignError(f"simulation did not produce ROOT output: {root_file}")
            root_hash = sha256_file(root_file)
            audit_output = run_and_tee(
                (
                    "root",
                    "-l",
                    "-b",
                    "-q",
                    root_macro_call(AUDIT_MACRO, root_file, git_commit),
                ),
                audit_log,
            )
            if "AUDIT_RESULT=PASS" not in audit_output:
                raise CampaignError(f"ROOT audit did not pass for {label}")
            if sha256_file(root_file) != root_hash:
                raise CampaignError(f"ROOT hash changed during audit for {label}")
            root_files[(run.role, run.condition)] = root_file
            root_hashes[(run.role, run.condition)] = root_hash

        analysis_dir = staging_dir / "analysis"
        analysis_log = staging_dir / "paired-analysis.log"
        off_root = root_files[("paired", "off")]
        on_root = root_files[("paired", "on")]
        analysis_output = run_and_tee(
            (
                "root",
                "-l",
                "-b",
                "-q",
                root_macro_call(ANALYZER_MACRO, off_root, on_root, analysis_dir),
            ),
            analysis_log,
        )
        if "NEUTRINO_TRANSPORT_ANALYSIS_RESULT=PASS" not in analysis_output:
            raise CampaignError("paired neutrino-transport analysis did not pass")
        for key, root_file in root_files.items():
            if sha256_file(root_file) != root_hashes[key]:
                raise CampaignError(f"ROOT hash changed during paired analysis: {key}")
        validate_analysis_products(analysis_dir)

        manifest_path = staging_dir / "campaign_manifest.tsv"
        with manifest_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "role",
                    "condition",
                    "bunch_crossings",
                    "seed",
                    "threads",
                    "transport_neutrinos",
                    "git_commit",
                    "root_file",
                    "root_sha256",
                ),
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            for run in RUNS:
                key = (run.role, run.condition)
                writer.writerow(
                    {
                        "role": run.role,
                        "condition": run.condition,
                        "bunch_crossings": run.bunch_crossings,
                        "seed": 512,
                        "threads": 1,
                        "transport_neutrinos": int(run.transport_neutrinos),
                        "git_commit": git_commit,
                        "root_file": root_files[key].name,
                        "root_sha256": root_hashes[key],
                    }
                )

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
        "NEUTRINO_TRANSPORT_CAMPAIGN_RESULT=PASS "
        "runs=3 bunch_crossings=203 paired_bunch_crossings=200"
    )
    print(f"NEUTRINO_TRANSPORT_CAMPAIGN_OUTPUT_DIR={output_dir}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run == args.execute_pilot:
        raise CampaignError("choose exactly one of --dry-run or --execute-pilot")
    output_dir = resolved_output_dir(args.output_dir)
    require_project_layout(full_run=args.execute_pilot)
    build_project(args.build_jobs)
    ensure_output_absent(output_dir)
    run_contract_preflight(output_dir)
    for run in RUNS:
        preflight_run(run, output_dir)
    ensure_output_absent(output_dir)
    if args.dry_run:
        print(
            "NEUTRINO_TRANSPORT_EXECUTOR_PREFLIGHT=PASS "
            "runs=3 bunch_crossings=203 paired_bunch_crossings=200 "
            "transport_executed=NO"
        )
        return 0

    execute_pilot(output_dir, git_provenance())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CampaignError, OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("NEUTRINO_TRANSPORT_CAMPAIGN_RESULT=FAIL", file=sys.stderr)
        raise SystemExit(1)
