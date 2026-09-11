#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FailureCase:
    name: str
    arguments: tuple[str, ...]
    expected_message: str
    expect_usage: bool = False


def fail(
    message: str,
    result: subprocess.CompletedProcess[str] | None = None,
) -> None:
    print(f"FAIL: {message}", file=sys.stderr)

    if result is not None:
        print("--- command output ---", file=sys.stderr)
        print(result.stdout, file=sys.stderr)

    raise SystemExit(1)


def run(
    binary: Path,
    arguments: tuple[str, ...],
    directory: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(binary), *arguments],
        cwd=directory,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def check_failure(
    binary: Path,
    directory: Path,
    case: FailureCase,
) -> None:
    result = run(binary, case.arguments, directory)

    if result.returncode != 1:
        fail(
            f"{case.name}: expected exit code 1, "
            f"got {result.returncode}",
            result,
        )

    if case.expected_message not in result.stdout:
        fail(
            f"{case.name}: expected diagnostic "
            f"{case.expected_message!r} was not produced",
            result,
        )

    if "ANALYSIS_RESULT=FAIL" not in result.stdout:
        fail(
            f"{case.name}: failure marker is missing",
            result,
        )

    if case.expect_usage and "Usage: single_particle_analyzer" not in result.stdout:
        fail(
            f"{case.name}: usage text is missing",
            result,
        )

    print(f"PASS {case.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    args = parser.parse_args()

    binary = Path(args.binary).resolve()

    if not binary.is_file():
        fail(f"analyzer binary does not exist: {binary}")

    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)

        input_a = directory / "input-a.root"
        input_b = directory / "input-b.root"
        summary_a = directory / "summary-a.csv"
        summary_b = directory / "summary-b.csv"
        sampling_a = directory / "sampling-a.csv"
        sampling_b = directory / "sampling-b.csv"

        complete = (
            "--input",
            str(input_a),
            "--summary-csv",
            str(summary_a),
            "--sampling-csv",
            str(sampling_a),
        )

        cases = (
            FailureCase(
                "no_arguments",
                (),
                "All three path options are required",
                True,
            ),
            FailureCase(
                "unknown_option",
                ("--definitely-invalid",),
                "Unknown argument: --definitely-invalid",
                True,
            ),
            FailureCase(
                "missing_input_value",
                ("--input",),
                "Missing value for --input",
                True,
            ),
            FailureCase(
                "missing_summary_value",
                (
                    "--input",
                    str(input_a),
                    "--summary-csv",
                ),
                "Missing value for --summary-csv",
                True,
            ),
            FailureCase(
                "missing_sampling_value",
                (
                    "--input",
                    str(input_a),
                    "--summary-csv",
                    str(summary_a),
                    "--sampling-csv",
                ),
                "Missing value for --sampling-csv",
                True,
            ),
            FailureCase(
                "empty_input_value",
                (
                    "--input",
                    "",
                    "--summary-csv",
                    str(summary_a),
                    "--sampling-csv",
                    str(sampling_a),
                ),
                "Empty value for --input",
                True,
            ),
            FailureCase(
                "empty_summary_value",
                (
                    "--input",
                    str(input_a),
                    "--summary-csv",
                    "",
                    "--sampling-csv",
                    str(sampling_a),
                ),
                "Empty value for --summary-csv",
                True,
            ),
            FailureCase(
                "empty_sampling_value",
                (
                    "--input",
                    str(input_a),
                    "--summary-csv",
                    str(summary_a),
                    "--sampling-csv",
                    "",
                ),
                "Empty value for --sampling-csv",
                True,
            ),
            FailureCase(
                "duplicate_input",
                (
                    "--input",
                    str(input_a),
                    "--input",
                    str(input_b),
                    "--summary-csv",
                    str(summary_a),
                    "--sampling-csv",
                    str(sampling_a),
                ),
                "Duplicate --input option",
            ),
            FailureCase(
                "duplicate_summary",
                (
                    "--input",
                    str(input_a),
                    "--summary-csv",
                    str(summary_a),
                    "--summary-csv",
                    str(summary_b),
                    "--sampling-csv",
                    str(sampling_a),
                ),
                "Duplicate --summary-csv option",
            ),
            FailureCase(
                "duplicate_sampling",
                (
                    "--input",
                    str(input_a),
                    "--summary-csv",
                    str(summary_a),
                    "--sampling-csv",
                    str(sampling_a),
                    "--sampling-csv",
                    str(sampling_b),
                ),
                "Duplicate --sampling-csv option",
            ),
            FailureCase(
                "missing_required_sampling",
                (
                    "--input",
                    str(input_a),
                    "--summary-csv",
                    str(summary_a),
                ),
                "All three path options are required",
                True,
            ),
            FailureCase(
                "input_equals_summary",
                (
                    "--input",
                    str(input_a),
                    "--summary-csv",
                    str(input_a),
                    "--sampling-csv",
                    str(sampling_a),
                ),
                "An output CSV must not replace the ROOT input",
            ),
            FailureCase(
                "input_equals_sampling",
                (
                    "--input",
                    str(input_a),
                    "--summary-csv",
                    str(summary_a),
                    "--sampling-csv",
                    str(input_a),
                ),
                "An output CSV must not replace the ROOT input",
            ),
            FailureCase(
                "summary_equals_sampling",
                (
                    "--input",
                    str(input_a),
                    "--summary-csv",
                    str(summary_a),
                    "--sampling-csv",
                    str(summary_a),
                ),
                "Summary and sampling CSV paths must differ",
            ),
        )

        for case in cases:
            check_failure(binary, directory, case)

        alias_path = f"{directory}/./alias-input.root"

        check_failure(
            binary,
            directory,
            FailureCase(
                "normalized_input_summary_alias",
                (
                    "--input",
                    str(directory / "alias-input.root"),
                    "--summary-csv",
                    alias_path,
                    "--sampling-csv",
                    str(sampling_a),
                ),
                "An output CSV must not replace the ROOT input",
            ),
        )

        existing_input = directory / "existing-input.root"
        hardlink_output = directory / "hardlink-summary.csv"

        existing_input.write_text(
            "not a ROOT file\n",
            encoding="utf-8",
        )

        os.link(existing_input, hardlink_output)

        check_failure(
            binary,
            directory,
            FailureCase(
                "filesystem_equivalent_input_summary",
                (
                    "--input",
                    str(existing_input),
                    "--summary-csv",
                    str(hardlink_output),
                    "--sampling-csv",
                    str(sampling_a),
                ),
                "An output CSV must not replace the ROOT input",
            ),
        )

        missing_root = directory / "does-not-exist.root"
        missing_summary = directory / "not-created-summary.csv"
        missing_sampling = directory / "not-created-sampling.csv"

        check_failure(
            binary,
            directory,
            FailureCase(
                "distinct_paths_missing_root",
                (
                    "--input",
                    str(missing_root),
                    "--summary-csv",
                    str(missing_summary),
                    "--sampling-csv",
                    str(missing_sampling),
                ),
                "Unable to open ROOT input:",
            ),
        )

        if missing_summary.exists():
            fail(
                "distinct_paths_missing_root: "
                "summary CSV was unexpectedly created"
            )

        if missing_sampling.exists():
            fail(
                "distinct_paths_missing_root: "
                "sampling CSV was unexpectedly created"
            )

        print("ANALYZER_CLI_CASES=18")
        print("ANALYZER_CLI_CASES_PASS=18")
        print("ANALYZER_CLI_FAILURE_MARKER_GATE=PASS")
        print("ANALYZER_CLI_PATH_COLLISION_GATE=PASS")
        print("ANALYZER_CLI_FILESYSTEM_EQUIVALENCE_GATE=PASS")
        print("ANALYZER_CLI_ROOT_OPEN_FAILURE_GATE=PASS")
        print("ANALYZER_CLI_GATE=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
