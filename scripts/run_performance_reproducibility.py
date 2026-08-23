#!/usr/bin/env python3
"""Transactional executor for the fixed Cycle 9 performance/reproducibility campaign."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence


PROJECT_DIR = Path(__file__).resolve().parents[1]
PREFLIGHT_PATH = (
    PROJECT_DIR / "scripts" / "preflight_performance_reproducibility.py"
)
ANALYZER_PATH = (
    PROJECT_DIR / "scripts" / "analyze_performance_reproducibility.py"
)
SIMULATOR = PROJECT_DIR / "build" / "pythia_geant"
PRODUCTION_CONFIG = PROJECT_DIR / "config" / "production.conf"
DEFAULT_OUTPUT_DIR = (
    PROJECT_DIR / "outputs" / "cycle9-performance-reproducibility"
)
TIME_COMMAND = Path("/usr/bin/time")


class CampaignError(RuntimeError):
    """A controlled Cycle 9 campaign failure."""


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CampaignError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PREFLIGHT = load_module(
    PREFLIGHT_PATH,
    "cycle9_performance_reproducibility_preflight",
)
ANALYZER = load_module(
    ANALYZER_PATH,
    "cycle9_performance_reproducibility_analyzer",
)

REPRO_RUNS = PREFLIGHT.REPRO_RUNS
PERF_RUNS = PREFLIGHT.PERF_RUNS
RUNS = PREFLIGHT.RUNS
SEED_BASE = PREFLIGHT.SEED_BASE
MEAN_INTERACTIONS = PREFLIGHT.MEAN_INTERACTIONS


def build_jobs_value(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("build jobs must be an integer") from error
    if parsed < 1 or parsed > 2:
        raise argparse.ArgumentTypeError("build jobs must be 1 or 2")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="build, test, and resolve the fixed matrix without transport",
    )
    parser.add_argument(
        "--execute-production",
        action="store_true",
        help="execute the complete fixed Cycle 9 production transaction",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="prospective final campaign directory",
    )
    parser.add_argument(
        "--build-jobs",
        type=build_jobs_value,
        default=build_jobs_value(os.environ.get("BUILD_JOBS", "2")),
        help="controlled build parallelism: 1 or 2 jobs",
    )
    return parser.parse_args(argv)


def resolved_output_dir(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (PROJECT_DIR / path).resolve()


def validate_execution_mode(args: argparse.Namespace) -> None:
    selected = int(args.dry_run) + int(args.execute_production)
    if selected != 1:
        raise CampaignError(
            "choose exactly one of --dry-run or --execute-production"
        )


def ensure_output_absent(path: Path) -> None:
    if path.exists():
        raise CampaignError(f"output directory already exists: {path}")


def run_name_sequence() -> tuple[str, ...]:
    return tuple(run.name for run in RUNS)


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise CampaignError(f"required command not found: {name}")


def require_project_layout(*, full_run: bool) -> None:
    for command in ("cmake", "ctest", "git"):
        require_command(command)

    required = (
        PREFLIGHT_PATH,
        ANALYZER_PATH,
        PRODUCTION_CONFIG,
    )
    for path in required:
        if not path.is_file() or path.stat().st_size == 0:
            raise CampaignError(f"missing or empty project file: {path}")

    if full_run:
        if not TIME_COMMAND.is_file():
            raise CampaignError(f"required command not found: {TIME_COMMAND}")


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
        diagnostic = (
            f"command failed with exit {result.returncode}: {command[0]}"
        )
        if capture and result.stdout:
            diagnostic += "\n" + result.stdout.rstrip()
        raise CampaignError(diagnostic)
    return result.stdout or ""


def build_project(build_jobs: int) -> None:
    if build_jobs not in (1, 2):
        raise CampaignError("build jobs must be 1 or 2")

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
    run_checked(
        (
            "cmake",
            "--build",
            "build",
            "--parallel",
            str(build_jobs),
        )
    )
    run_checked(
        (
            "ctest",
            "--test-dir",
            "build",
            "--output-on-failure",
        )
    )

    if not SIMULATOR.is_file() or not os.access(SIMULATOR, os.X_OK):
        raise CampaignError(f"simulator was not produced: {SIMULATOR}")


def run_contract_preflight(output_dir: Path) -> None:
    ensure_output_absent(output_dir)

    output = run_checked(
        (
            sys.executable,
            "-B",
            PREFLIGHT_PATH,
            "--output-dir",
            output_dir,
        ),
        capture=True,
    )

    marker = "PERFORMANCE_REPRODUCIBILITY_PREFLIGHT=PASS"
    if marker not in output:
        raise CampaignError("Cycle 9 contract preflight did not pass")

    ensure_output_absent(output_dir)


def git_provenance() -> dict[str, str]:
    commit = run_checked(
        ("git", "rev-parse", "HEAD"),
        capture=True,
    ).strip()
    if len(commit) != 40:
        raise CampaignError("git rev-parse did not return a full commit SHA")

    branch = run_checked(
        ("git", "branch", "--show-current"),
        capture=True,
    ).strip()
    if not branch:
        raise CampaignError("detached HEAD is not allowed for production")

    tracked_status = run_checked(
        (
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=no",
        ),
        capture=True,
    )
    if tracked_status.strip():
        raise CampaignError(
            "tracked worktree must be clean before production"
        )

    describe = run_checked(
        ("git", "describe", "--always", "--tags"),
        capture=True,
    ).strip()

    return {
        "commit": commit,
        "branch": branch,
        "describe": describe,
    }


def run_directory(base_dir: Path, run: Any) -> Path:
    return base_dir / run.name


def run_root_path(base_dir: Path, run: Any) -> Path:
    return run_directory(base_dir, run) / f"{run.name}.root"


def simulator_arguments(
    run: Any,
    root_file: Path,
    *,
    dry_run: bool = False,
) -> tuple[str, ...]:
    arguments = (
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
        str(root_file),
    )
    if dry_run:
        return arguments + ("--dry-run",)
    return arguments


def expected_dry_run_tokens(run: Any, root_file: Path) -> tuple[str, ...]:
    return (
        f"events = {run.events}",
        f"threads = {run.threads}",
        f"seed_base = {SEED_BASE}",
        "interaction_mode = poisson",
        "mean_interactions = 1",
        f'output = "{root_file}"',
        "Dry run concluído; nenhuma simulação foi executada.",
    )


def preflight_run(run: Any, output_dir: Path) -> None:
    ensure_output_absent(output_dir)
    root_file = run_root_path(output_dir, run)
    command = simulator_arguments(run, root_file, dry_run=True)
    output = run_checked(command, capture=True)

    missing = [
        token
        for token in expected_dry_run_tokens(run, root_file)
        if token not in output
    ]
    if missing:
        raise CampaignError(
            f"dry-run validation failed for {run.name}: "
            + ",".join(missing)
        )

    if root_file.exists():
        raise CampaignError(
            f"dry-run unexpectedly created ROOT output: {root_file}"
        )

    ensure_output_absent(output_dir)


def elapsed_seconds(value: str) -> float:
    parts = value.strip().split(":")
    try:
        if len(parts) == 2:
            minutes, seconds = parts
            result = int(minutes) * 60.0 + float(seconds)
        elif len(parts) == 3:
            hours, minutes, seconds = parts
            result = (
                int(hours) * 3600.0
                + int(minutes) * 60.0
                + float(seconds)
            )
        else:
            raise ValueError
    except ValueError as error:
        raise CampaignError(f"invalid elapsed wall time: {value!r}") from error

    if not math.isfinite(result) or result < 0.0:
        raise CampaignError(f"invalid elapsed wall time: {value!r}")
    return result


def parse_resource_log(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size == 0:
        raise CampaignError(f"missing or empty resource log: {path}")

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
        "Exit status",
    )
    missing = [key for key in required if key not in values]
    if missing:
        raise CampaignError(
            "resource log missing fields: " + ",".join(missing)
        )

    try:
        user_seconds = float(values["User time (seconds)"])
        system_seconds = float(values["System time (seconds)"])
        wall_seconds = elapsed_seconds(
            values["Elapsed (wall clock) time (h:mm:ss or m:ss)"]
        )
        max_rss_kbytes = int(
            values["Maximum resident set size (kbytes)"]
        )
        exit_status = int(values["Exit status"])
    except ValueError as error:
        raise CampaignError("invalid resource-log numeric value") from error

    if not math.isfinite(user_seconds) or user_seconds < 0.0:
        raise CampaignError("invalid user CPU time")
    if not math.isfinite(system_seconds) or system_seconds < 0.0:
        raise CampaignError("invalid system CPU time")
    if wall_seconds <= 0.0:
        raise CampaignError("wall time must be positive")
    if max_rss_kbytes <= 0:
        raise CampaignError("maximum RSS must be positive")
    if exit_status != 0:
        raise CampaignError(
            f"resource log reports nonzero exit status: {exit_status}"
        )

    return {
        "wall_seconds": wall_seconds,
        "user_seconds": user_seconds,
        "system_seconds": system_seconds,
        "max_rss_kbytes": max_rss_kbytes,
        "exit_status": exit_status,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_staging_dir(final_dir: Path) -> Path:
    final_dir = final_dir.resolve()
    ensure_output_absent(final_dir)
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{final_dir.name}.staging-",
            dir=final_dir.parent,
        )
    ).resolve()
    if staging.parent != final_dir.parent:
        shutil.rmtree(staging, ignore_errors=True)
        raise CampaignError("staging directory is not a sibling of final output")
    return staging


def cleanup_staging(staging_dir: Path) -> None:
    shutil.rmtree(staging_dir, ignore_errors=True)


def publish_staging(staging_dir: Path, final_dir: Path) -> None:
    staging_dir = staging_dir.resolve()
    final_dir = final_dir.resolve()
    ensure_output_absent(final_dir)
    if not staging_dir.is_dir():
        raise CampaignError(f"staging directory missing: {staging_dir}")
    if staging_dir.parent != final_dir.parent:
        raise CampaignError("staging and final output must be siblings")
    os.replace(staging_dir, final_dir)
    if not final_dir.is_dir() or staging_dir.exists():
        raise CampaignError("atomic staging publication failed")


def run_and_tee(
    command: Sequence[str | Path],
    log_path: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> str:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", newline="\n") as stream:
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
            stream.write(line)
            stream.flush()
            chunks.append(line)
        return_code = process.wait()

    if return_code != 0:
        raise CampaignError(
            f"command failed with exit {return_code}: {command[0]} "
            f"(see {log_path})"
        )
    return "".join(chunks)


def timed_simulator_command(
    run: Any,
    root_file: Path,
    resource_log: Path,
) -> tuple[str, ...]:
    return (
        str(TIME_COMMAND),
        "-v",
        "-o",
        str(resource_log),
        *simulator_arguments(run, root_file, dry_run=False),
    )


def execute_single_run(
    run: Any,
    staging_dir: Path,
) -> dict[str, Any]:
    directory = run_directory(staging_dir, run)
    if directory.exists():
        raise CampaignError(f"run directory already exists: {directory}")

    directory.mkdir(parents=True)
    root_file = run_root_path(staging_dir, run)
    simulation_log = directory / "simulation.log"
    resource_log = directory / "resource-usage.txt"

    command = timed_simulator_command(run, root_file, resource_log)

    try:
        run_and_tee(command, simulation_log)

        if not root_file.is_file() or root_file.stat().st_size == 0:
            raise CampaignError(
                f"simulation did not produce a non-empty ROOT file: {root_file}"
            )

        timing = parse_resource_log(resource_log)

        return {
            "name": run.name,
            "profile": run.profile,
            "repetition": run.repetition,
            "threads": run.threads,
            "events": run.events,
            "seed": SEED_BASE,
            "root_file": root_file,
            "root_size_bytes": root_file.stat().st_size,
            "root_sha256": sha256_file(root_file),
            "simulation_log": simulation_log,
            "resource_log": resource_log,
            **timing,
        }
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise


def energy_closure_tolerance(reference_mev: float) -> float:
    return 1.0e-9 + 1.0e-12 * abs(reference_mev)


def validate_root_content(run: Any, content: Mapping[str, Any]) -> dict[str, Any]:
    try:
        rows = content["rows"]
        events = list(rows["events"])
        hits = list(rows["hits"])
        generator = list(rows["generator"])
        metadata_rows = list(rows["metadata"])
    except (KeyError, TypeError) as error:
        raise CampaignError("canonical ROOT content is incomplete") from error

    if len(events) != run.events:
        raise CampaignError(
            f"{run.name}: expected {run.events} events, found {len(events)}"
        )

    event_ids = [int(row["event"]) for row in events]
    if len(event_ids) != len(set(event_ids)):
        raise CampaignError(f"{run.name}: duplicate event identifiers")
    if sorted(event_ids) != list(range(run.events)):
        raise CampaignError(f"{run.name}: incomplete event identifier interval")

    bcids = [int(row["bcid"]) for row in events]
    if len(bcids) != len(set(bcids)):
        raise CampaignError(f"{run.name}: duplicate BCIDs")
    if sorted(bcids) != list(range(run.events)):
        raise CampaignError(f"{run.name}: incomplete expected BCID interval")

    if len(metadata_rows) != 1:
        raise CampaignError(
            f"{run.name}: metadata must contain exactly one row"
        )

    metadata = metadata_rows[0]
    expected_metadata = {
        "events": run.events,
        "first_bcid": 0,
        "threads": run.threads,
        "seed_base": SEED_BASE,
        "transport_neutrinos": 0,
        "generator_audit": 0,
        "check_overlaps": 0,
    }
    for field, expected in expected_metadata.items():
        if int(metadata[field]) != expected:
            raise CampaignError(
                f"{run.name}: metadata mismatch for {field}: "
                f"expected {expected}, found {metadata[field]}"
            )

    mean_interactions = float(metadata["mean_interactions"])
    if not math.isfinite(mean_interactions) or not math.isclose(
        mean_interactions,
        MEAN_INTERACTIONS,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ):
        raise CampaignError(f"{run.name}: metadata mean_interactions mismatch")

    event_keys: set[tuple[int, int, int]] = set()
    event_energy: dict[tuple[int, int, int], float] = {}

    for row in events:
        key = (int(row["run"]), int(row["event"]), int(row["bcid"]))
        if key in event_keys:
            raise CampaignError(f"{run.name}: duplicate canonical event key")
        event_keys.add(key)

        requested = int(row["n_interactions_requested"])
        generated = int(row["n_interactions_generated"])
        failures = int(row["generation_failures"])
        if requested != generated + failures:
            raise CampaignError(
                f"{run.name}: interaction accounting mismatch at event {row['event']}"
            )

        if int(row["unknown_pdg_particles"]) != 0:
            raise CampaignError(
                f"{run.name}: unknown-PDG transport state is nonzero"
            )
        if int(row["unlineaged_steps"]) != 0:
            raise CampaignError(f"{run.name}: unlineaged steps detected")
        if int(row["segmentation_failures"]) != 0:
            raise CampaignError(f"{run.name}: segmentation failures detected")

        energy = float(row["total_edep_mev"])
        if not math.isfinite(energy):
            raise CampaignError(f"{run.name}: non-finite event energy")
        if energy < 0.0:
            raise CampaignError(f"{run.name}: negative event energy")
        event_energy[key] = energy

    hit_energy: dict[tuple[int, int, int], list[float]] = {
        key: [] for key in event_keys
    }

    for row in hits:
        if int(row["subevent"]) < 0:
            raise CampaignError(f"{run.name}: negative hit subevent identifier")

        key = (int(row["run"]), int(row["event"]), int(row["bcid"]))
        if key not in event_keys:
            raise CampaignError(f"{run.name}: orphan hit detected")

        energy = float(row["edep_mev"])
        if not math.isfinite(energy):
            raise CampaignError(f"{run.name}: non-finite hit energy")
        if energy < 0.0:
            raise CampaignError(f"{run.name}: negative hit energy")
        hit_energy[key].append(energy)

    for row in generator:
        if int(row["subevent"]) < 0:
            raise CampaignError(
                f"{run.name}: negative generator subevent identifier"
            )

    max_closure_abs = 0.0
    max_closure_rel = 0.0
    total_event_energy = math.fsum(event_energy.values())
    total_hit_energy = 0.0

    for key in sorted(event_keys):
        expected = event_energy[key]
        observed = math.fsum(hit_energy[key])
        total_hit_energy += observed
        difference = abs(expected - observed)
        tolerance = energy_closure_tolerance(expected)
        if difference > tolerance:
            raise CampaignError(
                f"{run.name}: event-hit energy closure failed for key {key}: "
                f"event={expected:.17g} hits={observed:.17g} "
                f"abs={difference:.17g} tolerance={tolerance:.17g}"
            )
        max_closure_abs = max(max_closure_abs, difference)
        scale = max(abs(expected), abs(observed))
        relative = 0.0 if scale == 0.0 else difference / scale
        max_closure_rel = max(max_closure_rel, relative)

    gates = {
        "exact_event_count": "PASS",
        "unique_event_ids": "PASS",
        "complete_event_interval": "PASS",
        "complete_bcid_interval": "PASS",
        "unique_bcids": "PASS",
        "interaction_accounting": "PASS",
        "finite_edep": "PASS",
        "nonnegative_edep": "PASS",
        "event_hit_energy_closure": "PASS",
        "no_orphan_hits": "PASS",
        "no_negative_subevent_ids": "PASS",
        "unknown_pdg_transport_state": "PASS",
        "no_unlineaged_steps": "PASS",
        "no_segmentation_failures": "PASS",
        "metadata_contract": "PASS",
    }

    return {
        "gates": gates,
        "metadata": dict(metadata),
        "tree_entries": {
            "events": len(events),
            "hits": len(hits),
            "generator": len(generator),
            "metadata": len(metadata_rows),
        },
        "scientific_digest": str(content["scientific_digest"]),
        "metadata_digest": str(content["metadata_digest"]),
        "tree_digests": dict(content["tree_digests"]),
        "total_event_energy_mev": total_event_energy,
        "total_hit_energy_mev": total_hit_energy,
        "max_energy_closure_abs_mev": max_closure_abs,
        "max_energy_closure_rel": max_closure_rel,
    }


def validate_root_artifact(run: Any, root_file: Path) -> dict[str, Any]:
    try:
        content = ANALYZER.extract_root_content(root_file)
    except (OSError, ValueError, ANALYZER.AnalysisError) as error:
        raise CampaignError(
            f"{run.name}: canonical ROOT analysis failed: {error}"
        ) from error
    result = validate_root_content(run, content)
    result["gates"] = {
        "readable_non_zombie_root": "PASS",
        **result["gates"],
    }
    return result


def write_run_manifest(
    run: Any,
    staging_dir: Path,
    artifact: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> Path:
    directory = run_directory(staging_dir, run)
    final_path = directory / "run-manifest.json"
    temporary_path = directory / "run-manifest.json.tmp"

    if final_path.exists() or temporary_path.exists():
        raise CampaignError(f"run manifest already exists: {final_path}")

    wall_seconds = float(artifact["wall_seconds"])
    if not math.isfinite(wall_seconds) or wall_seconds <= 0.0:
        raise CampaignError(f"{run.name}: invalid wall time for manifest")

    payload = {
        "schema_version": 1,
        "cycle": 9,
        "run": {
            "name": run.name,
            "profile": run.profile,
            "repetition": run.repetition,
            "threads": run.threads,
            "events": run.events,
            "seed_base": SEED_BASE,
            "mean_interactions": MEAN_INTERACTIONS,
        },
        "timing": {
            "wall_seconds": wall_seconds,
            "user_seconds": float(artifact["user_seconds"]),
            "system_seconds": float(artifact["system_seconds"]),
            "max_rss_kbytes": int(artifact["max_rss_kbytes"]),
            "exit_status": int(artifact["exit_status"]),
            "events_per_second": run.events / wall_seconds,
            "bc_per_second": run.events / wall_seconds,
        },
        "root": {
            "file": str(Path(artifact["root_file"]).relative_to(staging_dir)),
            "size_bytes": int(artifact["root_size_bytes"]),
            "sha256": str(artifact["root_sha256"]),
            "scientific_digest": str(validation["scientific_digest"]),
            "metadata_digest": str(validation["metadata_digest"]),
            "tree_entries": dict(validation["tree_entries"]),
            "tree_digests": dict(validation["tree_digests"]),
        },
        "energy": {
            "total_event_energy_mev": float(
                validation["total_event_energy_mev"]
            ),
            "total_hit_energy_mev": float(
                validation["total_hit_energy_mev"]
            ),
            "max_closure_abs_mev": float(
                validation["max_energy_closure_abs_mev"]
            ),
            "max_closure_rel": float(
                validation["max_energy_closure_rel"]
            ),
        },
        "validation": dict(validation["gates"]),
        "resolved_metadata": dict(validation["metadata"]),
    }

    try:
        temporary_path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, final_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    if not final_path.is_file() or final_path.stat().st_size == 0:
        raise CampaignError(f"failed to write run manifest: {final_path}")
    return final_path


def compact_tree_comparison(tree: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "equal": bool(tree["equal"]),
        "left_entries": int(tree["left_entries"]),
        "right_entries": int(tree["right_entries"]),
        "only_left_keys": int(tree["only_left_keys"]),
        "only_right_keys": int(tree["only_right_keys"]),
        "differing_rows": int(tree["differing_rows"]),
        "differing_values": int(tree["differing_values"]),
        "differing_fields": dict(tree["differing_fields"]),
        "max_abs_difference": float(tree["max_abs_difference"]),
        "max_abs_field": tree["max_abs_field"],
        "max_rel_difference": float(tree["max_rel_difference"]),
        "max_rel_field": tree["max_rel_field"],
        "digest_equal": bool(tree["digest_equal"]),
        "left_digest": str(tree["left_digest"]),
        "right_digest": str(tree["right_digest"]),
    }


def compact_comparison(comparison: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "raw_sha256_equal": bool(comparison["raw_sha256_equal"]),
        "scientific_equal": bool(comparison["scientific_equal"]),
        "metadata_equal": bool(comparison["metadata_equal"]),
        "canonical_equal": bool(comparison["canonical_equal"]),
        "scientific_digest_equal": bool(
            comparison["scientific_digest_equal"]
        ),
        "metadata_digest_equal": bool(
            comparison["metadata_digest_equal"]
        ),
        "left_scientific_digest": str(
            comparison["left_scientific_digest"]
        ),
        "right_scientific_digest": str(
            comparison["right_scientific_digest"]
        ),
        "left_metadata_digest": str(comparison["left_metadata_digest"]),
        "right_metadata_digest": str(comparison["right_metadata_digest"]),
        "trees": {
            name: compact_tree_comparison(comparison["trees"][name])
            for name in ("events", "hits", "generator", "metadata")
        },
    }


def compare_repro_pair(
    staging_dir: Path,
    left_name: str,
    right_name: str,
    mode: str,
) -> dict[str, Any]:
    left_run = next(run for run in REPRO_RUNS if run.name == left_name)
    right_run = next(run for run in REPRO_RUNS if run.name == right_name)
    left_root = run_root_path(staging_dir, left_run)
    right_root = run_root_path(staging_dir, right_run)
    comparison = ANALYZER.compare_root_files(left_root, right_root)
    evaluation = ANALYZER.evaluate_comparison(mode, comparison)
    return {
        "comparison": compact_comparison(comparison),
        "evaluation": dict(evaluation),
    }


def reproducibility_report(staging_dir: Path) -> dict[str, Any]:
    t1_result = compare_repro_pair(
        staging_dir,
        "repro-t1-r1",
        "repro-t1-r2",
        "repeatability",
    )
    t1 = t1_result["comparison"]
    t1_evaluation = t1_result["evaluation"]

    if not t1_evaluation["accepted"]:
        raise CampaignError(
            "one-thread repeatability failed: "
            "schema-aware comparison rejected"
        )

    t2_result = compare_repro_pair(
        staging_dir,
        "repro-t2-r1",
        "repro-t2-r2",
        "repeatability",
    )
    t2 = t2_result["comparison"]
    t2_evaluation = t2_result["evaluation"]

    if not t2_evaluation["accepted"]:
        raise CampaignError(
            "two-thread repeatability failed: "
            "schema-aware comparison rejected"
        )

    cross_r1_result = compare_repro_pair(
        staging_dir,
        "repro-t1-r1",
        "repro-t2-r1",
        "cross-thread",
    )
    cross_r1 = cross_r1_result["comparison"]
    cross_r1_evaluation = cross_r1_result["evaluation"]

    if not cross_r1_evaluation["accepted"]:
        raise CampaignError(
            "cross-thread reproducibility failed for repetition 1: "
            "schema-aware comparison rejected"
        )

    cross_r2_result = compare_repro_pair(
        staging_dir,
        "repro-t1-r2",
        "repro-t2-r2",
        "cross-thread",
    )
    cross_r2 = cross_r2_result["comparison"]
    cross_r2_evaluation = cross_r2_result["evaluation"]

    if not cross_r2_evaluation["accepted"]:
        raise CampaignError(
            "cross-thread reproducibility failed for repetition 2: "
            "schema-aware comparison rejected"
        )

    return {
        "schema_version": 1,
        "one_thread_repeatability": {
            "classification": t1_evaluation["classification"],
            "evaluation": t1_evaluation,
            "comparison": t1,
        },
        "two_thread_repeatability": {
            "classification": t2_evaluation["classification"],
            "exact_repeatability": bool(t2_evaluation["accepted"]),
            "evaluation": t2_evaluation,
            "comparison": t2,
        },
        "cross_thread": {
            "acceptance_policy": "SCHEMA_AWARE_EVENT_STABLE_GATE",
            "repetition_1": {
                "classification": cross_r1_evaluation["classification"],
                "evaluation": cross_r1_evaluation,
                "comparison": cross_r1,
            },
            "repetition_2": {
                "classification": cross_r2_evaluation["classification"],
                "evaluation": cross_r2_evaluation,
                "comparison": cross_r2,
            },
        },
    }


def timing_statistics(values: Sequence[float]) -> dict[str, Any]:
    if len(values) != 3:
        raise CampaignError("performance statistics require exactly three runs")

    numeric = [float(value) for value in values]
    if any(not math.isfinite(value) or value <= 0.0 for value in numeric):
        raise CampaignError("invalid wall time in performance statistics")

    mean = statistics.mean(numeric)
    median = statistics.median(numeric)
    stddev = statistics.stdev(numeric)
    coefficient = stddev / mean if mean > 0.0 else math.inf

    return {
        "count": len(numeric),
        "minimum_wall_seconds": min(numeric),
        "maximum_wall_seconds": max(numeric),
        "mean_wall_seconds": mean,
        "median_wall_seconds": median,
        "sample_stddev_wall_seconds": stddev,
        "coefficient_of_variation": coefficient,
        "stability_warning": coefficient > 0.20,
    }


def performance_summary(
    artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    expected_names = {run.name for run in PERF_RUNS}
    available_names = set(artifacts)
    missing = sorted(expected_names - available_names)
    if missing:
        raise CampaignError(
            "missing validated performance runs: " + ",".join(missing)
        )

    rows: list[dict[str, Any]] = []
    walls: dict[int, list[float]] = {1: [], 2: []}

    for run in PERF_RUNS:
        artifact = artifacts[run.name]
        if artifact.get("computational_validation") != "PASS":
            raise CampaignError(
                f"{run.name}: invalid run cannot enter performance summary"
            )

        wall = float(artifact["wall_seconds"])
        user = float(artifact["user_seconds"])
        system = float(artifact["system_seconds"])
        rss = int(artifact["max_rss_kbytes"])
        root_size = int(artifact["root_size_bytes"])
        exit_status = int(artifact["exit_status"])

        if (
            not math.isfinite(wall)
            or wall <= 0.0
            or not math.isfinite(user)
            or user < 0.0
            or not math.isfinite(system)
            or system < 0.0
            or rss <= 0
            or root_size <= 0
            or exit_status != 0
        ):
            raise CampaignError(f"{run.name}: invalid performance measurement")

        walls[run.threads].append(wall)
        rows.append({
            "name": run.name,
            "threads": run.threads,
            "repetition": run.repetition,
            "events": run.events,
            "wall_seconds": wall,
            "user_seconds": user,
            "system_seconds": system,
            "max_rss_kbytes": rss,
            "root_size_bytes": root_size,
            "events_per_second": run.events / wall,
            "bc_per_second": run.events / wall,
            "exit_status": exit_status,
            "root_sha256": str(artifact["root_sha256"]),
        })

    stats_1t = timing_statistics(walls[1])
    stats_2t = timing_statistics(walls[2])
    median_1t = float(stats_1t["median_wall_seconds"])
    median_2t = float(stats_2t["median_wall_seconds"])
    speedup = median_1t / median_2t
    efficiency = speedup / 2.0

    warnings: list[str] = []
    if stats_1t["stability_warning"]:
        warnings.append("TIMING_CV_ABOVE_20_PERCENT_THREADS_1")
    if stats_2t["stability_warning"]:
        warnings.append("TIMING_CV_ABOVE_20_PERCENT_THREADS_2")

    return {
        "schema_version": 1,
        "run_count": len(rows),
        "runs": rows,
        "threads": {
            "1": stats_1t,
            "2": stats_2t,
        },
        "speedup_2t": speedup,
        "parallel_efficiency_2t": efficiency,
        "speedup_acceptance_threshold": None,
        "warnings": warnings,
    }


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if path.exists() or temporary.exists():
        raise CampaignError(f"analysis product already exists: {path}")
    try:
        temporary.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_campaign_analysis(
    staging_dir: Path,
    artifacts: Mapping[str, Mapping[str, Any]],
) -> tuple[Path, Path]:
    analysis_dir = staging_dir / "analysis"
    if analysis_dir.exists():
        raise CampaignError(f"analysis directory already exists: {analysis_dir}")
    analysis_dir.mkdir()

    try:
        reproducibility = reproducibility_report(staging_dir)
        performance = performance_summary(artifacts)

        repro_path = analysis_dir / "reproducibility.json"
        performance_path = analysis_dir / "performance-summary.json"

        write_json_atomic(repro_path, reproducibility)
        write_json_atomic(performance_path, performance)
        return repro_path, performance_path
    except Exception:
        shutil.rmtree(analysis_dir, ignore_errors=True)
        raise


def write_campaign_manifest(
    staging_dir: Path,
    provenance: Mapping[str, str],
    artifacts: Mapping[str, Mapping[str, Any]],
    reproducibility_path: Path,
    performance_path: Path,
) -> Path:
    expected = [run.name for run in RUNS]
    if list(artifacts) != expected:
        raise CampaignError("campaign artifacts do not match fixed run order")

    run_records: list[dict[str, Any]] = []
    for run in RUNS:
        artifact = artifacts[run.name]
        if artifact.get("computational_validation") != "PASS":
            raise CampaignError(
                f"{run.name}: campaign manifest received invalid run"
            )
        run_records.append({
            "name": run.name,
            "profile": run.profile,
            "repetition": run.repetition,
            "threads": run.threads,
            "events": run.events,
            "seed_base": SEED_BASE,
            "root_file": str(
                Path(artifact["root_file"]).relative_to(staging_dir)
            ),
            "run_manifest": str(
                Path(artifact["manifest"]).relative_to(staging_dir)
            ),
            "root_sha256": str(artifact["root_sha256"]),
            "scientific_digest": str(artifact["scientific_digest"]),
            "metadata_digest": str(artifact["metadata_digest"]),
            "wall_seconds": float(artifact["wall_seconds"]),
        })

    payload = {
        "schema_version": 1,
        "cycle": 9,
        "transaction": {
            "run_count": len(RUNS),
            "execution_order": expected,
            "sequential_execution": True,
            "parallel_simulator_processes": 1,
            "publication": "ATOMIC_SIBLING_RENAME",
        },
        "configuration": {
            "seed_base": SEED_BASE,
            "mean_interactions": MEAN_INTERACTIONS,
            "threads": [1, 2],
            "production_config": str(PRODUCTION_CONFIG.relative_to(PROJECT_DIR)),
        },
        "git": dict(provenance),
        "runs": run_records,
        "analysis": {
            "reproducibility": str(
                reproducibility_path.relative_to(staging_dir)
            ),
            "performance": str(
                performance_path.relative_to(staging_dir)
            ),
        },
        "campaign_validation": "PASS",
    }

    path = staging_dir / "campaign-manifest.json"
    write_json_atomic(path, payload)
    return path


def execute_production(
    final_dir: Path,
    provenance: Mapping[str, str],
) -> Path:
    final_dir = final_dir.resolve()
    staging = create_staging_dir(final_dir)
    artifacts: dict[str, dict[str, Any]] = {}

    try:
        for run in RUNS:
            print(
                "CYCLE_9_PRODUCTION_RUN_START="
                + run.name
                + " threads="
                + str(run.threads)
                + " events="
                + str(run.events)
            )

            artifact = execute_single_run(run, staging)
            validation = validate_root_artifact(
                run,
                Path(artifact["root_file"]),
            )
            manifest = write_run_manifest(
                run,
                staging,
                artifact,
                validation,
            )

            enriched = dict(artifact)
            enriched["computational_validation"] = "PASS"
            enriched["manifest"] = manifest
            enriched["scientific_digest"] = validation["scientific_digest"]
            enriched["metadata_digest"] = validation["metadata_digest"]
            artifacts[run.name] = enriched

            print(
                "CYCLE_9_PRODUCTION_RUN=PASS name="
                + run.name
            )

        if list(artifacts) != [run.name for run in RUNS]:
            raise CampaignError("production did not preserve fixed run order")

        reproducibility_path, performance_path = write_campaign_analysis(
            staging,
            artifacts,
        )

        write_campaign_manifest(
            staging,
            provenance,
            artifacts,
            reproducibility_path,
            performance_path,
        )

        publish_staging(staging, final_dir)
        return final_dir

    except Exception:
        cleanup_staging(staging)
        if final_dir.exists():
            shutil.rmtree(final_dir, ignore_errors=True)
        raise


def execute_dry_run_flow(
    output_dir: Path,
    build_jobs: int,
) -> None:
    ensure_output_absent(output_dir)
    require_project_layout(full_run=False)
    build_project(build_jobs)
    run_contract_preflight(output_dir)

    for run in RUNS:
        preflight_run(run, output_dir)

    ensure_output_absent(output_dir)


def execute_production_flow(
    output_dir: Path,
    build_jobs: int,
) -> Path:
    ensure_output_absent(output_dir)
    require_project_layout(full_run=True)
    build_project(build_jobs)
    run_contract_preflight(output_dir)

    for run in RUNS:
        preflight_run(run, output_dir)

    ensure_output_absent(output_dir)
    provenance = git_provenance()
    return execute_production(output_dir, provenance)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    validate_execution_mode(args)
    output_dir = resolved_output_dir(args.output_dir)

    if args.dry_run:
        execute_dry_run_flow(output_dir, args.build_jobs)
        print(
            "PERFORMANCE_REPRODUCIBILITY_EXECUTOR_PREFLIGHT=PASS "
            f"runs={len(RUNS)} "
            "transport_executed=NO"
        )
        return 0

    final_dir = execute_production_flow(
        output_dir,
        args.build_jobs,
    )
    print(
        "PERFORMANCE_REPRODUCIBILITY_EXECUTOR_PRODUCTION=PASS "
        f"runs={len(RUNS)} "
        f"output={final_dir}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, CampaignError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print(
            "PERFORMANCE_REPRODUCIBILITY_EXECUTOR=FAIL",
            file=sys.stderr,
        )
        raise SystemExit(1)
