#!/usr/bin/env python3
"""ROOT adapter for Cycle 11 partition-stability analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(SCRIPT_DIR),
    )

import analyze_partition_stability as partition
import analyze_performance_reproducibility as root_analysis


REQUIRED_SCHEMA_VERSION = partition.REQUIRED_SCHEMA_VERSION


class PartitionRootError(RuntimeError):
    """Controlled ROOT-adapter failure for Cycle 11."""


def load_root_shard(
    path: Path | str,
) -> dict[str, Any]:

    resolved = Path(path).resolve()

    try:
        content = (
            root_analysis
            .extract_root_content(
                resolved
            )
        )
    except root_analysis.AnalysisError as error:
        raise PartitionRootError(
            f"{resolved}: ROOT extraction failed: "
            f"{error}"
        ) from error

    schema = int(
        content[
            "metadata_schema_version"
        ]
    )

    if schema != REQUIRED_SCHEMA_VERSION:
        raise PartitionRootError(
            f"{resolved}: Cycle 11 partition "
            f"analysis requires metadata schema "
            f"{REQUIRED_SCHEMA_VERSION}, "
            f"found {schema}"
        )

    return {
        "name": resolved.name,
        "path": str(resolved),
        "metadata_schema_version": schema,
        "raw_sha256": content["sha256"],
        "size_bytes": content["size_bytes"],
        "rows": content["rows"],
    }


def compare_root_partition(
    monolithic_path: Path | str,
    shard_paths: Sequence[Path | str],
    *,
    first_global_bcid: int,
    total_events: int,
) -> dict[str, Any]:

    if not shard_paths:
        raise PartitionRootError(
            "at least one shard ROOT file is required"
        )

    monolithic = load_root_shard(
        monolithic_path
    )

    shards = [
        load_root_shard(path)
        for path in shard_paths
    ]

    schemas = {
        monolithic[
            "metadata_schema_version"
        ],
        *(
            shard[
                "metadata_schema_version"
            ]
            for shard in shards
        ),
    }

    if len(schemas) != 1:
        raise PartitionRootError(
            "incompatible ROOT metadata schemas"
        )

    try:
        comparison = (
            partition
            .compare_monolithic_to_partition(
                monolithic,
                shards,
                first_global_bcid=(
                    first_global_bcid
                ),
                total_events=total_events,
            )
        )
    except partition.PartitionAnalysisError as error:
        raise PartitionRootError(
            str(error)
        ) from error

    return {
        **comparison,
        "metadata_schema_version": (
            monolithic[
                "metadata_schema_version"
            ]
        ),
        "monolithic_path": (
            monolithic["path"]
        ),
        "shard_paths": [
            shard["path"]
            for shard in shards
        ],
        "monolithic_raw_sha256": (
            monolithic[
                "raw_sha256"
            ]
        ),
        "shard_raw_sha256": [
            shard[
                "raw_sha256"
            ]
            for shard in shards
        ],
    }


def _yes_no(value: bool) -> str:
    return (
        "YES"
        if value
        else "NO"
    )


def _build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description=(
            "Compare one monolithic ROOT file "
            "against partitioned Cycle 11 shards."
        )
    )

    parser.add_argument(
        "--monolithic",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--shard",
        action="append",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--first-bcid",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--events",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--json",
        type=Path,
        default=None,
    )

    return parser


def analyzer_main(
    argv: Sequence[str] | None = None,
) -> int:

    args = _build_parser().parse_args(
        argv
    )

    try:

        result = compare_root_partition(
            args.monolithic,
            args.shard,
            first_global_bcid=(
                args.first_bcid
            ),
            total_events=args.events,
        )

    except (
        PartitionRootError,
        OSError,
        ValueError,
    ) as error:

        print(
            "ROOT_PARTITION_ADAPTER_GATE=FAIL"
        )

        print(
            "ERROR="
            + str(error)
        )

        return 1

    print(
        "ROOT_PARTITION_ADAPTER_GATE=PASS"
    )

    print(
        "METADATA_SCHEMA_VERSION="
        + str(
            result[
                "metadata_schema_version"
            ]
        )
    )

    print(
        "GENERATOR_EQUAL="
        + _yes_no(
            bool(
                result[
                    "generator_equal"
                ]
            )
        )
    )

    print(
        "EVENTS_EQUAL="
        + _yes_no(
            bool(
                result[
                    "events_equal"
                ]
            )
        )
    )

    print(
        "HITS_EQUAL="
        + _yes_no(
            bool(
                result[
                    "hits_equal"
                ]
            )
        )
    )

    print(
        "SCIENTIFIC_EQUAL="
        + _yes_no(
            bool(
                result[
                    "scientific_equal"
                ]
            )
        )
    )

    print(
        "CLASSIFICATION="
        + str(
            result[
                "classification"
            ]
        )
    )

    for tree in (
        "events",
        "hits",
        "generator",
    ):

        values = (
            result[
                "trees"
            ][tree]
        )

        print(
            tree.upper()
            + "_DIGEST_EQUAL="
            + _yes_no(
                bool(
                    values[
                        "digest_equal"
                    ]
                )
            )
        )

        print(
            tree.upper()
            + "_MONOLITHIC_DIGEST="
            + str(
                values[
                    "monolithic_digest"
                ]
            )
        )

        print(
            tree.upper()
            + "_PARTITION_DIGEST="
            + str(
                values[
                    "partition_digest"
                ]
            )
        )

    if args.json is not None:

        args.json.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.json.write_text(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        print(
            "JSON_REPORT="
            + str(
                args.json.resolve()
            )
        )

    return (
        0
        if result[
            "scientific_equal"
        ]
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(
        analyzer_main()
    )
