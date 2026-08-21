#!/usr/bin/env python3
"""Run the fixed-budget Cycle 8.3 neutrino-transport campaign transaction."""

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
PREFLIGHT_PATH = PROJECT_DIR / "scripts" / "preflight_neutrino_transport_stage83.py"
SIMULATOR = PROJECT_DIR / "build" / "pythia_geant"
AUDIT_MACRO = PROJECT_DIR / "scripts" / "audit_root.C"
ANALYZER_MACRO = PROJECT_DIR / "scripts" / "analyze_neutrino_transport.C"
DEFAULT_OUTPUT_DIR = (
    PROJECT_DIR / "outputs" / "cycle8-neutrino-transport-stage83"
)


class Stage83CampaignError(RuntimeError):
    """A controlled Stage 8.3 campaign failure."""


def _load_preflight():
    spec = importlib.util.spec_from_file_location(
        "cycle8_stage83_preflight_contract", PREFLIGHT_PATH
    )
    if spec is None or spec.loader is None:
        raise Stage83CampaignError(
            f"cannot load Stage 8.3 preflight: {PREFLIGHT_PATH}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PREFLIGHT = _load_preflight()
RUNS = PREFLIGHT.RUNS
SEEDS = PREFLIGHT.SEEDS
EVENTS_PER_CONDITION = PREFLIGHT.EVENTS_PER_CONDITION
THREADS = PREFLIGHT.THREADS


SUMMARY_INTEGER_FIELDS = (
    "eligible_neutrinos",
    "outside_acceptance_neutrinos",
    "off_transported",
    "on_transported",
    "transported_delta",
    "off_hit_count",
    "on_hit_count",
    "changed_hit_cells",
    "missing_off_hit_cells",
    "missing_on_hit_cells",
    "generator_entries",
    "requested_interactions",
    "generated_interactions",
    "generation_failures",
    "unknown_pdg_particles",
    "unlineaged_steps",
    "segmentation_failures",
)
SUMMARY_NONNEGATIVE_FLOAT_FIELDS = (
    "off_total_energy_mev",
    "on_total_energy_mev",
    "energy_abs_delta_mev",
    "energy_relative_delta",
    "hit_energy_l1_mev",
    "max_abs_hit_delta_mev",
)


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
        help="build, test, and resolve all six runs without transport",
    )
    parser.add_argument(
        "--execute-production",
        action="store_true",
        help="execute the complete fixed six-run production transaction",
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
        raise Stage83CampaignError(f"output directory already exists: {path}")


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise Stage83CampaignError(f"required command not found: {name}")


def paired_template(condition: str):
    for run in PREFLIGHT.PILOT.RUNS:
        if run.role == "paired" and run.condition == condition:
            return run
    raise Stage83CampaignError(f"missing pilot template for condition: {condition}")


def require_project_layout(*, full_run: bool) -> None:
    for command in ("cmake", "ctest", "git"):
        require_command(command)
    required = (
        PREFLIGHT_PATH,
        PREFLIGHT.SPEC_PATH,
        AUDIT_MACRO,
        ANALYZER_MACRO,
        paired_template("off").config,
        paired_template("on").config,
    )
    for path in required:
        if not path.is_file() or path.stat().st_size == 0:
            raise Stage83CampaignError(f"missing or empty project file: {path}")
    if full_run:
        require_command("root")
        if not Path("/usr/bin/time").is_file():
            raise Stage83CampaignError("required command not found: /usr/bin/time")


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
        raise Stage83CampaignError(diagnostic)
    return result.stdout or ""


def run_and_tee(
    command: Sequence[str | Path],
    log_path: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> str:
    with log_path.open("w", encoding="utf-8", newline="\n") as log_stream:
        process = subprocess.Popen(
            [str(item) for item in command],
            cwd=PROJECT_DIR,
            env=dict(environment) if environment is not None else None,
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
        raise Stage83CampaignError(
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
        raise Stage83CampaignError(f"simulator was not produced: {SIMULATOR}")


def simulator_arguments(
    run, root_file: Path, *, dry_run: bool = False
) -> tuple[str, ...]:
    template = paired_template(run.condition)
    arguments = (
        str(SIMULATOR),
        "--config",
        str(template.config),
        "--events",
        str(run.bunch_crossings),
        "--mu",
        "1",
        "--threads",
        str(run.threads),
        "--seed",
        str(run.seed),
        "--output",
        str(root_file),
    )
    return arguments + (("--dry-run",) if dry_run else ())


def run_contract_preflight(output_dir: Path) -> None:
    output = run_checked(
        (sys.executable, "-B", PREFLIGHT_PATH, "--output-dir", output_dir),
        capture=True,
    )
    if "NEUTRINO_TRANSPORT_STAGE83_PREFLIGHT=PASS" not in output:
        raise Stage83CampaignError("Stage 8.3 contract preflight did not pass")


def preflight_run(run, output_dir: Path) -> None:
    ensure_output_absent(output_dir)
    prospective_root = output_dir / run.output_name
    output = run_checked(
        simulator_arguments(run, prospective_root, dry_run=True), capture=True
    )
    if "Dry run concluído; nenhuma simulação foi executada." not in output:
        raise Stage83CampaignError(
            f"simulator dry-run marker missing for seed={run.seed}/{run.condition}"
        )
    ensure_output_absent(output_dir)


def git_provenance() -> str:
    commit = run_checked(("git", "rev-parse", "HEAD"), capture=True).strip()
    if len(commit) != 40:
        raise Stage83CampaignError("git rev-parse did not return a full commit SHA")
    tracked_status = run_checked(
        ("git", "status", "--porcelain", "--untracked-files=no"), capture=True
    )
    if tracked_status.strip():
        raise Stage83CampaignError("tracked worktree must be clean before transport")
    return commit


def root_quote(value: str | Path) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def root_macro_call(macro: Path, *arguments: str | Path) -> str:
    return f"{macro}({','.join(root_quote(item) for item in arguments)})"


def analyzer_macro_call(
    off_root: Path,
    on_root: Path,
    output_dir: Path,
    expected_events: int,
    expected_seed: int,
    require_positive_eligible: bool,
) -> str:
    required = "true" if require_positive_eligible else "false"
    return (
        f"{ANALYZER_MACRO}("
        f"{root_quote(off_root)},{root_quote(on_root)},{root_quote(output_dir)},"
        f"{expected_events},{expected_seed},{required})"
    )


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
            raise Stage83CampaignError(f"invalid validation line: {raw_line!r}")
        values[key] = value
    return values


def finite_float(row: Mapping[str, str], key: str, *, nonnegative: bool) -> float:
    try:
        value = float(row[key])
    except (KeyError, ValueError) as error:
        raise Stage83CampaignError(f"invalid analysis value for {key}") from error
    if not math.isfinite(value) or (nonnegative and value < 0.0):
        raise Stage83CampaignError(f"invalid finite analysis value: {key}")
    return value


def nonnegative_integer(row: Mapping[str, str], key: str) -> int:
    try:
        value = int(row[key])
    except (KeyError, ValueError) as error:
        raise Stage83CampaignError(f"invalid analysis count for {key}") from error
    if value < 0:
        raise Stage83CampaignError(f"negative analysis count: {key}")
    return value


def validate_seed_analysis(
    analysis_dir: Path, expected_seed: int
) -> tuple[dict[str, str], list[dict[str, str]]]:
    summary_path = analysis_dir / "paired_summary.csv"
    events_path = analysis_dir / "paired_events.csv"
    validation_path = analysis_dir / "paired_validation.txt"
    for path in (summary_path, events_path, validation_path):
        if not path.is_file() or path.stat().st_size == 0:
            raise Stage83CampaignError(f"missing seed analysis product: {path}")

    with summary_path.open(newline="", encoding="utf-8") as stream:
        summary_rows = list(csv.DictReader(stream))
    if len(summary_rows) != 1:
        raise Stage83CampaignError("seed summary must contain exactly one row")
    summary = summary_rows[0]
    if (
        int(summary["events"]) != EVENTS_PER_CONDITION
        or int(summary["seed"]) != expected_seed
    ):
        raise Stage83CampaignError("seed summary event or seed contract mismatch")
    if not math.isclose(float(summary["mean_interactions"]), 1.0):
        raise Stage83CampaignError("seed summary interaction mean mismatch")
    for key in SUMMARY_INTEGER_FIELDS:
        nonnegative_integer(summary, key)
    for key in SUMMARY_NONNEGATIVE_FLOAT_FIELDS:
        finite_float(summary, key, nonnegative=True)
    finite_float(summary, "energy_delta_mev", nonnegative=False)

    eligible = int(summary["eligible_neutrinos"])
    outside = int(summary["outside_acceptance_neutrinos"])
    if int(summary["transported_delta"]) != eligible:
        raise Stage83CampaignError(
            "seed transported-particle delta does not equal eligibility"
        )

    with events_path.open(newline="", encoding="utf-8") as stream:
        event_rows = list(csv.DictReader(stream))
    if len(event_rows) != EVENTS_PER_CONDITION:
        raise Stage83CampaignError("seed event table has an unexpected row count")
    observed: list[tuple[int, int]] = []
    summed_eligible = 0
    summed_outside = 0
    for event_row in event_rows:
        event = int(event_row["event"])
        bcid = int(event_row["bcid"])
        observed.append((event, bcid))
        event_eligible = nonnegative_integer(event_row, "eligible_neutrinos")
        event_outside = nonnegative_integer(
            event_row, "outside_acceptance_neutrinos"
        )
        off_transported = nonnegative_integer(event_row, "off_transported")
        on_transported = nonnegative_integer(event_row, "on_transported")
        if on_transported - off_transported != event_eligible:
            raise Stage83CampaignError("event transported-particle delta mismatch")
        for key in ("off_hit_count", "on_hit_count"):
            nonnegative_integer(event_row, key)
        for key in ("off_energy_mev", "on_energy_mev", "energy_abs_delta_mev"):
            finite_float(event_row, key, nonnegative=True)
        finite_float(event_row, "energy_delta_mev", nonnegative=False)
        summed_eligible += event_eligible
        summed_outside += event_outside
    expected_ids = [(event, event) for event in range(EVENTS_PER_CONDITION)]
    if observed != expected_ids:
        raise Stage83CampaignError("seed event/BCID identifiers are not exactly 0..999")
    if summed_eligible != eligible or summed_outside != outside:
        raise Stage83CampaignError("seed event and summary neutrino counts disagree")

    validation = read_validation(validation_path)
    expected_validation = {
        "NEUTRINO_TRANSPORT_ANALYSIS_RESULT": "PASS",
        "metadata_pairing": "PASS",
        "event_pairing": "PASS",
        "generator_pairing": "PASS",
        "particle_accounting": "PASS",
        "eligible_neutrinos": str(eligible),
        "outside_acceptance_neutrinos": str(outside),
        "energy_difference_classification": "REPORTED_NOT_ASSUMED",
    }
    for key, value in expected_validation.items():
        if validation.get(key) != value:
            raise Stage83CampaignError(f"seed validation mismatch for {key}")
    return summary, event_rows


def classify_eligible_sample(eligible: int) -> str:
    if eligible < 0:
        raise Stage83CampaignError("eligible sample cannot be negative")
    if eligible == 0:
        return "NONE"
    if eligible < 30:
        return "LIMITED"
    return "DESCRIPTIVE"


def aggregate_seed_products(staging_dir: Path) -> dict[str, str]:
    final_dir = staging_dir / "analysis"
    temporary_dir = staging_dir / "analysis.tmp"
    if final_dir.exists() or temporary_dir.exists():
        raise Stage83CampaignError("aggregate analysis directory already exists")

    seed_summaries: list[dict[str, str]] = []
    combined_events: list[dict[str, str]] = []
    for seed in SEEDS:
        summary, events = validate_seed_analysis(
            staging_dir / f"seed-{seed}" / "analysis", seed
        )
        seed_summaries.append(summary)
        for row in events:
            combined_events.append({"seed": str(seed), **row})

    eligible = sum(int(row["eligible_neutrinos"]) for row in seed_summaries)
    outside = sum(
        int(row["outside_acceptance_neutrinos"]) for row in seed_summaries
    )
    aggregate: dict[str, str] = {
        "seed_pairs": str(len(SEEDS)),
        "paired_bunch_crossings": str(len(SEEDS) * EVENTS_PER_CONDITION),
        "total_runs": str(len(RUNS)),
        "total_transport_bunch_crossings": str(
            sum(run.bunch_crossings for run in RUNS)
        ),
        "seeds": ";".join(str(seed) for seed in SEEDS),
        "eligible_neutrinos": str(eligible),
        "eligible_sample_classification": classify_eligible_sample(eligible),
        "outside_acceptance_neutrinos": str(outside),
    }
    for key in (
        "off_transported",
        "on_transported",
        "off_hit_count",
        "on_hit_count",
        "changed_hit_cells",
        "missing_off_hit_cells",
        "missing_on_hit_cells",
        "generator_entries",
        "requested_interactions",
        "generated_interactions",
        "generation_failures",
        "unknown_pdg_particles",
        "unlineaged_steps",
        "segmentation_failures",
    ):
        aggregate[key] = str(sum(int(row[key]) for row in seed_summaries))
    aggregate["transported_delta"] = str(
        int(aggregate["on_transported"]) - int(aggregate["off_transported"])
    )
    for key in (
        "off_total_energy_mev",
        "on_total_energy_mev",
        "energy_abs_delta_mev",
        "hit_energy_l1_mev",
    ):
        aggregate[key] = format(sum(float(row[key]) for row in seed_summaries), ".17g")
    aggregate["energy_delta_mev"] = format(
        float(aggregate["on_total_energy_mev"])
        - float(aggregate["off_total_energy_mev"]),
        ".17g",
    )
    denominator = max(
        float(aggregate["off_total_energy_mev"]),
        float(aggregate["on_total_energy_mev"]),
    )
    aggregate["energy_relative_delta"] = format(
        float(aggregate["energy_abs_delta_mev"]) / denominator
        if denominator > 0.0
        else 0.0,
        ".17g",
    )
    aggregate["max_abs_hit_delta_mev"] = format(
        max(float(row["max_abs_hit_delta_mev"]) for row in seed_summaries),
        ".17g",
    )
    aggregate["energy_changed_events"] = str(
        sum(float(row["energy_abs_delta_mev"]) > 0.0 for row in combined_events)
    )
    aggregate["hit_count_changed_events"] = str(
        sum(
            int(row["off_hit_count"]) != int(row["on_hit_count"])
            for row in combined_events
        )
    )
    if int(aggregate["transported_delta"]) != eligible:
        raise Stage83CampaignError(
            "aggregate transported-particle delta does not equal eligibility"
        )

    try:
        temporary_dir.mkdir()
        seed_summary_path = temporary_dir / "stage83_seed_summary.csv"
        with seed_summary_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=tuple(seed_summaries[0]))
            writer.writeheader()
            writer.writerows(seed_summaries)

        event_path = temporary_dir / "stage83_events.csv"
        with event_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=tuple(combined_events[0]))
            writer.writeheader()
            writer.writerows(combined_events)

        summary_path = temporary_dir / "stage83_summary.csv"
        with summary_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=tuple(aggregate))
            writer.writeheader()
            writer.writerow(aggregate)

        (temporary_dir / "stage83_validation.txt").write_text(
            "NEUTRINO_TRANSPORT_STAGE83_ANALYSIS_RESULT=PASS\n"
            "fixed_matrix=PASS\n"
            "seed_pairing=PASS\n"
            "event_pairing=PASS\n"
            "generator_pairing=PASS\n"
            "particle_accounting=PASS\n"
            f"eligible_neutrinos={eligible}\n"
            f"outside_acceptance_neutrinos={outside}\n"
            f"eligible_sample_classification={aggregate['eligible_sample_classification']}\n"
            "energy_difference_classification=REPORTED_NOT_ASSUMED\n",
            encoding="utf-8",
        )
        os.replace(temporary_dir, final_dir)
    finally:
        shutil.rmtree(temporary_dir, ignore_errors=True)

    validate_aggregate_products(final_dir)
    return aggregate


def validate_aggregate_products(analysis_dir: Path) -> None:
    required = (
        analysis_dir / "stage83_seed_summary.csv",
        analysis_dir / "stage83_events.csv",
        analysis_dir / "stage83_summary.csv",
        analysis_dir / "stage83_validation.txt",
    )
    for path in required:
        if not path.is_file() or path.stat().st_size == 0:
            raise Stage83CampaignError(f"missing aggregate product: {path}")

    with required[0].open(newline="", encoding="utf-8") as stream:
        seed_rows = list(csv.DictReader(stream))
    if [int(row["seed"]) for row in seed_rows] != list(SEEDS):
        raise Stage83CampaignError("aggregate seed summary does not match matrix")

    with required[1].open(newline="", encoding="utf-8") as stream:
        event_rows = list(csv.DictReader(stream))
    expected_count = len(SEEDS) * EVENTS_PER_CONDITION
    if len(event_rows) != expected_count:
        raise Stage83CampaignError("aggregate event table has unexpected row count")
    observed_keys = [
        (int(row["seed"]), int(row["event"]), int(row["bcid"]))
        for row in event_rows
    ]
    expected_keys = [
        (seed, event, event)
        for seed in SEEDS
        for event in range(EVENTS_PER_CONDITION)
    ]
    if observed_keys != expected_keys:
        raise Stage83CampaignError("aggregate event keys do not match fixed matrix")

    with required[2].open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise Stage83CampaignError("aggregate summary must contain one row")
    summary = rows[0]
    eligible = nonnegative_integer(summary, "eligible_neutrinos")
    if (
        int(summary["seed_pairs"]) != len(SEEDS)
        or int(summary["paired_bunch_crossings"]) != expected_count
        or int(summary["total_runs"]) != len(RUNS)
        or int(summary["total_transport_bunch_crossings"]) != 6000
        or summary["seeds"] != ";".join(str(seed) for seed in SEEDS)
        or int(summary["transported_delta"]) != eligible
        or summary["eligible_sample_classification"]
        != classify_eligible_sample(eligible)
    ):
        raise Stage83CampaignError("aggregate summary contract mismatch")

    validation = read_validation(required[3])
    expected_validation = {
        "NEUTRINO_TRANSPORT_STAGE83_ANALYSIS_RESULT": "PASS",
        "fixed_matrix": "PASS",
        "seed_pairing": "PASS",
        "event_pairing": "PASS",
        "generator_pairing": "PASS",
        "particle_accounting": "PASS",
        "eligible_neutrinos": str(eligible),
        "outside_acceptance_neutrinos": summary[
            "outside_acceptance_neutrinos"
        ],
        "eligible_sample_classification": classify_eligible_sample(eligible),
        "energy_difference_classification": "REPORTED_NOT_ASSUMED",
    }
    for key, value in expected_validation.items():
        if validation.get(key) != value:
            raise Stage83CampaignError(f"aggregate validation mismatch for {key}")


def elapsed_seconds(value: str) -> float:
    parts = value.strip().split(":")
    try:
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60.0 + float(seconds)
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600.0 + int(minutes) * 60.0 + float(seconds)
    except ValueError as error:
        raise Stage83CampaignError(f"invalid elapsed time: {value!r}") from error
    raise Stage83CampaignError(f"invalid elapsed time: {value!r}")


def parse_resource_log(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = raw_line.strip().rpartition(": ")
        if separator:
            values[key] = value.strip()
    required = (
        "User time (seconds)",
        "System time (seconds)",
        "Elapsed (wall clock) time (h:mm:ss or m:ss)",
        "Maximum resident set size (kbytes)",
    )
    missing = [key for key in required if key not in values]
    if missing:
        raise Stage83CampaignError(
            "resource log missing fields: " + ", ".join(missing)
        )
    elapsed = elapsed_seconds(
        values["Elapsed (wall clock) time (h:mm:ss or m:ss)"]
    )
    user = float(values["User time (seconds)"])
    system = float(values["System time (seconds)"])
    rss = int(values["Maximum resident set size (kbytes)"])
    if any(not math.isfinite(value) or value < 0.0 for value in (elapsed, user, system)):
        raise Stage83CampaignError("invalid resource timing value")
    if rss <= 0:
        raise Stage83CampaignError("invalid maximum RSS value")
    return {
        "elapsed_wall_clock": values[
            "Elapsed (wall clock) time (h:mm:ss or m:ss)"
        ],
        "elapsed_seconds": format(elapsed, ".6f"),
        "user_seconds": format(user, ".6f"),
        "system_seconds": format(system, ".6f"),
        "max_rss_kbytes": str(rss),
    }


def write_resource_summary(
    staging_dir: Path, artifacts: Mapping[tuple[int, str], Mapping[str, Path | str]]
) -> None:
    rows: list[dict[str, str]] = []
    for run in RUNS:
        item = artifacts[(run.seed, run.condition)]
        root_file = Path(item["root_file"])
        simulation_log = Path(item["simulation_log"])
        resource_log = Path(item["resource_log"])
        audit_log = Path(item["audit_log"])
        rows.append(
            {
                "seed": str(run.seed),
                "condition": run.condition,
                "bunch_crossings": str(run.bunch_crossings),
                **parse_resource_log(resource_log),
                "root_file": str(root_file.relative_to(staging_dir)),
                "root_size_bytes": str(root_file.stat().st_size),
                "root_sha256": str(item["root_sha256"]),
                "simulation_log_sha256": sha256_file(simulation_log),
                "resource_log_sha256": sha256_file(resource_log),
                "root_audit_log_sha256": sha256_file(audit_log),
            }
        )
    for seed in SEEDS:
        pair = [row for row in rows if int(row["seed"]) == seed]
        if [row["condition"] for row in pair] != ["off", "on"]:
            raise Stage83CampaignError(f"resource pair is incomplete for seed={seed}")
        off, on = pair
        ratios: dict[str, str] = {}
        for output_key, value_key in (
            ("wall_time_ratio_on_over_off", "elapsed_seconds"),
            ("max_rss_ratio_on_over_off", "max_rss_kbytes"),
            ("root_size_ratio_on_over_off", "root_size_bytes"),
        ):
            denominator = float(off[value_key])
            numerator = float(on[value_key])
            if denominator <= 0.0 or numerator <= 0.0:
                raise Stage83CampaignError(
                    f"resource ratio has a nonpositive input for seed={seed}"
                )
            ratios[output_key] = format(numerator / denominator, ".17g")
        off.update(ratios)
        on.update(ratios)
    path = staging_dir / "analysis" / "stage83_resource_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    validate_resource_summary(path)


def validate_resource_summary(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    observed = [
        (int(row["seed"]), row["condition"], int(row["bunch_crossings"]))
        for row in rows
    ]
    expected = [
        (run.seed, run.condition, run.bunch_crossings) for run in RUNS
    ]
    if observed != expected:
        raise Stage83CampaignError("resource summary does not match fixed matrix")
    for row in rows:
        for key in (
            "elapsed_seconds",
            "user_seconds",
            "system_seconds",
            "max_rss_kbytes",
            "root_size_bytes",
            "wall_time_ratio_on_over_off",
            "max_rss_ratio_on_over_off",
            "root_size_ratio_on_over_off",
        ):
            value = finite_float(row, key, nonnegative=True)
            if key not in {"user_seconds", "system_seconds"} and value <= 0.0:
                raise Stage83CampaignError(
                    f"resource summary value must be positive: {key}"
                )
        for key in (
            "root_sha256",
            "simulation_log_sha256",
            "resource_log_sha256",
            "root_audit_log_sha256",
        ):
            value = row[key]
            if len(value) != 64 or any(
                character not in "0123456789abcdef" for character in value
            ):
                raise Stage83CampaignError(f"invalid resource checksum: {key}")


def write_campaign_manifest(
    staging_dir: Path,
    git_commit: str,
    artifacts: Mapping[tuple[int, str], Mapping[str, Path | str]],
) -> None:
    path = staging_dir / "campaign_manifest.tsv"
    fieldnames = (
        "seed",
        "condition",
        "bunch_crossings",
        "threads",
        "transport_neutrinos",
        "git_commit",
        "root_file",
        "root_sha256",
        "simulation_log",
        "resource_log",
        "root_audit_log",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for run in RUNS:
            item = artifacts[(run.seed, run.condition)]
            writer.writerow(
                {
                    "seed": run.seed,
                    "condition": run.condition,
                    "bunch_crossings": run.bunch_crossings,
                    "threads": run.threads,
                    "transport_neutrinos": int(run.transport_neutrinos),
                    "git_commit": git_commit,
                    "root_file": Path(item["root_file"]).relative_to(staging_dir),
                    "root_sha256": item["root_sha256"],
                    "simulation_log": Path(item["simulation_log"]).relative_to(
                        staging_dir
                    ),
                    "resource_log": Path(item["resource_log"]).relative_to(
                        staging_dir
                    ),
                    "root_audit_log": Path(item["audit_log"]).relative_to(
                        staging_dir
                    ),
                }
            )


def write_campaign_checksums(staging_dir: Path) -> None:
    checksum_path = staging_dir / "campaign_artifacts.sha256"
    lines = []
    for artifact in sorted(path for path in staging_dir.rglob("*") if path.is_file()):
        if artifact != checksum_path:
            lines.append(
                f"{sha256_file(artifact)}  {artifact.relative_to(staging_dir)}\n"
            )
    checksum_path.write_text("".join(lines), encoding="utf-8")


def execute_production(output_dir: Path, git_commit: str) -> None:
    ensure_output_absent(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent)
    )
    artifacts: dict[tuple[int, str], dict[str, Path | str]] = {}
    root_environment = os.environ.copy()
    root_environment["LC_ALL"] = "C"
    try:
        for run in RUNS:
            seed_dir = staging_dir / f"seed-{run.seed}"
            seed_dir.mkdir(parents=True, exist_ok=True)
            label = f"paired-{run.condition}-1000"
            root_file = seed_dir / f"{label}.root"
            simulation_log = seed_dir / f"{label}-simulation.log"
            resource_log = seed_dir / f"{label}-resource-usage.txt"
            audit_log = seed_dir / f"{label}-root-audit.log"

            run_and_tee(
                (
                    "/usr/bin/time",
                    "-v",
                    "-o",
                    resource_log,
                    *simulator_arguments(run, root_file),
                ),
                simulation_log,
                environment=root_environment,
            )
            for path in (root_file, simulation_log, resource_log):
                if not path.is_file() or path.stat().st_size == 0:
                    raise Stage83CampaignError(
                        f"production run did not create a required artifact: {path}"
                    )
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
                environment=root_environment,
            )
            if "AUDIT_RESULT=PASS" not in audit_output:
                raise Stage83CampaignError(
                    f"ROOT audit did not pass for seed={run.seed}/{run.condition}"
                )
            if sha256_file(root_file) != root_hash:
                raise Stage83CampaignError(
                    f"ROOT hash changed during audit for seed={run.seed}/{run.condition}"
                )
            artifacts[(run.seed, run.condition)] = {
                "root_file": root_file,
                "root_sha256": root_hash,
                "simulation_log": simulation_log,
                "resource_log": resource_log,
                "audit_log": audit_log,
            }

        for seed in SEEDS:
            seed_dir = staging_dir / f"seed-{seed}"
            analysis_dir = seed_dir / "analysis"
            analysis_log = seed_dir / "paired-analysis.log"
            off_root = Path(artifacts[(seed, "off")]["root_file"])
            on_root = Path(artifacts[(seed, "on")]["root_file"])
            output = run_and_tee(
                (
                    "root",
                    "-l",
                    "-b",
                    "-q",
                    analyzer_macro_call(
                        off_root,
                        on_root,
                        analysis_dir,
                        EVENTS_PER_CONDITION,
                        seed,
                        False,
                    ),
                ),
                analysis_log,
                environment=root_environment,
            )
            if "NEUTRINO_TRANSPORT_ANALYSIS_RESULT=PASS" not in output:
                raise Stage83CampaignError(
                    f"paired analysis did not pass for seed={seed}"
                )
            for condition in ("off", "on"):
                item = artifacts[(seed, condition)]
                if sha256_file(Path(item["root_file"])) != item["root_sha256"]:
                    raise Stage83CampaignError(
                        f"ROOT hash changed during analysis for seed={seed}/{condition}"
                    )
            validate_seed_analysis(analysis_dir, seed)

        aggregate = aggregate_seed_products(staging_dir)
        write_resource_summary(staging_dir, artifacts)
        validate_aggregate_products(staging_dir / "analysis")
        write_campaign_manifest(staging_dir, git_commit, artifacts)
        write_campaign_checksums(staging_dir)
        os.replace(staging_dir, output_dir)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    print(
        "NEUTRINO_TRANSPORT_STAGE83_CAMPAIGN_RESULT=PASS "
        "runs=6 seed_pairs=3 bunch_crossings=6000 "
        "paired_bunch_crossings=3000 stopping_rule=fixed_budget "
        f"eligible_neutrinos={aggregate['eligible_neutrinos']} "
        f"eligible_sample_classification={aggregate['eligible_sample_classification']}"
    )
    print(f"NEUTRINO_TRANSPORT_STAGE83_OUTPUT_DIR={output_dir}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run == args.execute_production:
        raise Stage83CampaignError(
            "choose exactly one of --dry-run or --execute-production"
        )
    output_dir = resolved_output_dir(args.output_dir)
    require_project_layout(full_run=args.execute_production)
    build_project(args.build_jobs)
    ensure_output_absent(output_dir)
    run_contract_preflight(output_dir)
    for run in RUNS:
        preflight_run(run, output_dir)
    ensure_output_absent(output_dir)
    if args.dry_run:
        print(
            "NEUTRINO_TRANSPORT_STAGE83_EXECUTOR_PREFLIGHT=PASS "
            "runs=6 seed_pairs=3 bunch_crossings=6000 "
            "paired_bunch_crossings=3000 transport_executed=NO"
        )
        return 0

    execute_production(output_dir, git_provenance())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, Stage83CampaignError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("NEUTRINO_TRANSPORT_STAGE83_CAMPAIGN_RESULT=FAIL", file=sys.stderr)
        raise SystemExit(1)
