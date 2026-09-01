#!/usr/bin/env python3
"""Dependency-light partition-stability core for Cycle 11."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_performance_reproducibility import (  # noqa: E402
    EVENT_FIELDS_V4 as EVENT_FIELDS,
    GENERATOR_FIELDS,
    HIT_FIELDS,
    canonical_row,
    canonical_scalar,
    compare_tree_rows,
)

SCIENTIFIC_TREES = ("events", "hits", "generator")

GLOBAL_KEYS = {
    "events": ("bcid",),
    "hits": ("bcid", "subevent", "cell_id"),
    "generator": ("bcid", "subevent", "index"),
}

TREE_FIELDS = {
    "events": EVENT_FIELDS,
    "hits": HIT_FIELDS,
    "generator": GENERATOR_FIELDS,
}

GLOBAL_FIELDS = {
    name: tuple(
        field
        for field in fields
        if field not in {"run", "event"}
    )
    for name, fields in TREE_FIELDS.items()
}

OPERATIONAL_METADATA = frozenset(
    {
        "events",
        "first_bcid",
        "threads",
        "output_file",
        "config_file",
        "normalized_config",
    }
)


REQUIRED_SCHEMA_VERSION = 4

REQUIRED_TRANSPORT_METADATA = {
    "geant4_transport_seed_policy": "event-stable-v1",
    "geant4_transport_seed_identity": "bcid",
    "geant4_transport_seed_mixer": "splitmix64-v1",
    "geant4_transport_seed_stream": "transport-event",
    "geant4_transport_seed_max": 2147483646,
    "geant4_transport_reseed_scope": "event-before-tracking",
}


class PartitionAnalysisError(RuntimeError):
    """Controlled Cycle 11 partition-analysis failure."""


def _int(value: Any, label: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise PartitionAnalysisError(
            f"{label}: invalid integer {value!r}"
        ) from error

    if canonical_scalar(value) != canonical_scalar(result):
        raise PartitionAnalysisError(
            f"{label}: non-integral value {value!r}"
        )

    return result


def _rows(
    shard: Mapping[str, Any],
    tree: str,
) -> list[Mapping[str, Any]]:
    try:
        return list(shard["rows"][tree])
    except (KeyError, TypeError) as error:
        raise PartitionAnalysisError(
            f"{shard.get('name', '<unnamed>')}: "
            f"missing rows for {tree}"
        ) from error


def _metadata(
    shard: Mapping[str, Any],
) -> Mapping[str, Any]:
    rows = _rows(shard, "metadata")

    if len(rows) != 1:
        raise PartitionAnalysisError(
            f"{shard.get('name', '<unnamed>')}: "
            "metadata must contain one row"
        )

    return rows[0]


def _unique_global_keys(
    rows: Sequence[Mapping[str, Any]],
    tree: str,
) -> None:
    seen: set[tuple[tuple[str, Any], ...]] = set()

    for row in rows:
        try:
            key = tuple(
                canonical_scalar(row[field])
                for field in GLOBAL_KEYS[tree]
            )
        except KeyError as error:
            raise PartitionAnalysisError(
                f"{tree}: missing global key field "
                f"{error.args[0]}"
            ) from error

        if key in seen:
            raise PartitionAnalysisError(
                f"{tree}: duplicate global canonical key "
                f"{key!r}"
            )

        seen.add(key)


def validate_shard(
    shard: Mapping[str, Any],
) -> dict[str, Any]:

    name = str(shard.get("name", "<unnamed>"))

    events = _rows(shard, "events")
    hits = _rows(shard, "hits")
    generator = _rows(shard, "generator")
    metadata = _metadata(shard)

    try:
        schema_version = _int(
            metadata["schema_version"],
            f"{name}: metadata.schema_version",
        )
    except KeyError as error:
        raise PartitionAnalysisError(
            f"{name}: metadata missing {error.args[0]}"
        ) from error

    if schema_version != REQUIRED_SCHEMA_VERSION:
        raise PartitionAnalysisError(
            f"{name}: post-correction partition "
            f"analysis requires metadata schema "
            f"{REQUIRED_SCHEMA_VERSION}, "
            f"found {schema_version}"
        )

    for field, expected in (
        REQUIRED_TRANSPORT_METADATA.items()
    ):
        if field not in metadata:
            raise PartitionAnalysisError(
                f"{name}: metadata missing {field}"
            )

        if (
            canonical_scalar(metadata[field])
            != canonical_scalar(expected)
        ):
            raise PartitionAnalysisError(
                f"{name}: unexpected {field}: "
                f"{metadata[field]!r}"
            )

    try:
        count = _int(
            metadata["events"],
            f"{name}: metadata.events",
        )
        first = _int(
            metadata["first_bcid"],
            f"{name}: metadata.first_bcid",
        )
    except KeyError as error:
        raise PartitionAnalysisError(
            f"{name}: metadata missing {error.args[0]}"
        ) from error

    if count <= 0 or first < 0:
        raise PartitionAnalysisError(
            f"{name}: invalid shard interval"
        )

    if len(events) != count:
        raise PartitionAnalysisError(
            f"{name}: expected {count} events, "
            f"found {len(events)}"
        )

    pairs: set[tuple[int, int]] = set()
    event_ids: list[int] = []
    bcids: list[int] = []

    for row in events:

        try:
            event = _int(
                row["event"],
                f"{name}: event",
            )
            bcid = _int(
                row["bcid"],
                f"{name}: bcid",
            )
        except KeyError as error:
            raise PartitionAnalysisError(
                f"{name}: event row missing "
                f"{error.args[0]}"
            ) from error

        event_ids.append(event)
        bcids.append(bcid)

        if (event, bcid) in pairs:
            raise PartitionAnalysisError(
                f"{name}: duplicate local event/BCID pair"
            )

        pairs.add((event, bcid))

    if len(set(event_ids)) != count:
        raise PartitionAnalysisError(
            f"{name}: duplicate local event identifier"
        )

    if sorted(event_ids) != list(range(count)):
        raise PartitionAnalysisError(
            f"{name}: incomplete local event interval"
        )

    if len(set(bcids)) != count:
        raise PartitionAnalysisError(
            f"{name}: duplicate BCID"
        )

    if sorted(bcids) != list(
        range(first, first + count)
    ):
        raise PartitionAnalysisError(
            f"{name}: incomplete shard BCID interval"
        )

    for event, bcid in pairs:

        if bcid != first + event:
            raise PartitionAnalysisError(
                f"{name}: "
                "bcid = first_bcid + event violated"
            )

    for tree, rows in (
        ("hits", hits),
        ("generator", generator),
    ):

        for row in rows:

            try:
                pair = (
                    _int(
                        row["event"],
                        f"{name}: {tree}.event",
                    ),
                    _int(
                        row["bcid"],
                        f"{name}: {tree}.bcid",
                    ),
                )
            except KeyError as error:
                raise PartitionAnalysisError(
                    f"{name}: {tree} row missing "
                    f"{error.args[0]}"
                ) from error

            if pair not in pairs:
                raise PartitionAnalysisError(
                    f"{name}: orphan {tree} record"
                )

    for tree, rows in (
        ("events", events),
        ("hits", hits),
        ("generator", generator),
    ):
        _unique_global_keys(rows, tree)

    return {
        "name": name,
        "first_bcid": first,
        "events": count,
        "last_bcid": first + count - 1,
        "metadata": metadata,
        "rows": {
            "events": events,
            "hits": hits,
            "generator": generator,
        },
    }


def validate_metadata(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> None:

    if set(left) != set(right):
        raise PartitionAnalysisError(
            "metadata field mismatch"
        )

    changed = [
        field
        for field in sorted(
            set(left) - OPERATIONAL_METADATA
        )
        if canonical_scalar(left[field])
        != canonical_scalar(right[field])
    ]

    if changed:
        raise PartitionAnalysisError(
            "unexpected metadata differences: "
            + ",".join(changed)
        )


def aggregate_partition(
    shards: Sequence[Mapping[str, Any]],
    *,
    first_global_bcid: int,
    total_events: int,
) -> dict[str, Any]:

    if not shards:
        raise PartitionAnalysisError(
            "partition must contain at least one shard"
        )

    if first_global_bcid < 0 or total_events <= 0:
        raise PartitionAnalysisError(
            "invalid global BCID interval"
        )

    validated = [
        validate_shard(shard)
        for shard in shards
    ]

    reference = validated[0]["metadata"]

    for shard in validated[1:]:
        validate_metadata(
            reference,
            shard["metadata"],
        )

    combined = {
        tree: []
        for tree in SCIENTIFIC_TREES
    }

    bcids: list[int] = []

    for shard in validated:

        bcids.extend(
            int(row["bcid"])
            for row in shard["rows"]["events"]
        )

        for tree in SCIENTIFIC_TREES:
            combined[tree].extend(
                shard["rows"][tree]
            )

    if len(set(bcids)) != len(bcids):
        raise PartitionAnalysisError(
            "partition contains "
            "overlapping/duplicate BCIDs"
        )

    expected = set(
        range(
            first_global_bcid,
            first_global_bcid + total_events,
        )
    )

    observed = set(bcids)

    missing = sorted(expected - observed)
    outside = sorted(observed - expected)

    if missing:
        raise PartitionAnalysisError(
            "gaps in global BCID coverage"
        )

    if outside:
        raise PartitionAnalysisError(
            "BCIDs outside global interval"
        )

    if len(bcids) != total_events:
        raise PartitionAnalysisError(
            "global BCID multiplicity mismatch"
        )

    for tree in SCIENTIFIC_TREES:
        _unique_global_keys(
            combined[tree],
            tree,
        )

    return {
        "rows": combined,
        "shards": validated,
        "first_global_bcid": first_global_bcid,
        "last_global_bcid": (
            first_global_bcid
            + total_events
            - 1
        ),
        "total_events": total_events,
    }


def _digest(
    rows: Sequence[Mapping[str, Any]],
    tree: str,
) -> str:

    digest = hashlib.sha256()

    for line in sorted(
        canonical_row(
            row,
            GLOBAL_FIELDS[tree],
        )
        for row in rows
    ):
        digest.update(
            line.encode("utf-8")
        )
        digest.update(b"\n")

    return digest.hexdigest()


def compare_monolithic_to_partition(
    monolithic: Mapping[str, Any],
    shards: Sequence[Mapping[str, Any]],
    *,
    first_global_bcid: int,
    total_events: int,
) -> dict[str, Any]:

    mono = validate_shard(monolithic)

    if (
        mono["first_bcid"]
        != first_global_bcid
        or mono["events"]
        != total_events
    ):
        raise PartitionAnalysisError(
            "monolithic interval mismatch"
        )

    partition = aggregate_partition(
        shards,
        first_global_bcid=first_global_bcid,
        total_events=total_events,
    )

    for shard in partition["shards"]:
        validate_metadata(
            mono["metadata"],
            shard["metadata"],
        )

    trees: dict[str, dict[str, Any]] = {}

    for tree in SCIENTIFIC_TREES:

        result = compare_tree_rows(
            mono["rows"][tree],
            partition["rows"][tree],
            GLOBAL_FIELDS[tree],
            GLOBAL_KEYS[tree],
            tree,
        )

        result["monolithic_digest"] = _digest(
            mono["rows"][tree],
            tree,
        )

        result["partition_digest"] = _digest(
            partition["rows"][tree],
            tree,
        )

        result["digest_equal"] = (
            result["monolithic_digest"]
            == result["partition_digest"]
        )

        trees[tree] = result

    generator_equal = bool(
        trees["generator"]["equal"]
    )

    events_equal = bool(
        trees["events"]["equal"]
    )

    hits_equal = bool(
        trees["hits"]["equal"]
    )

    scientific_equal = (
        generator_equal
        and events_equal
        and hits_equal
    )

    if not generator_equal:

        classification = (
            "PRIMARY_PARTITION_STABILITY=FAIL"
        )

    elif not scientific_equal:

        classification = (
            "PRIMARY_PARTITION_STABILITY=PASS;"
            "TRANSPORT_PARTITION_STABILITY=FAIL"
        )

    else:

        classification = (
            "FULL_PARTITION_STABILITY=PASS"
        )

    return {
        "scientific_equal": scientific_equal,
        "generator_equal": generator_equal,
        "events_equal": events_equal,
        "hits_equal": hits_equal,
        "classification": classification,
        "trees": trees,
    }
