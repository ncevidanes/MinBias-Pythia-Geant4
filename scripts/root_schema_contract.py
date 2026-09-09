#!/usr/bin/env python3
"""Shared ROOT schema compatibility contract for Python validators."""

from __future__ import annotations


WORKER_SEED_SCHEMA_VERSION = 2
PRIMARY_EVENT_STABLE_SCHEMA_VERSION = 3
TRANSPORT_EVENT_STABLE_SCHEMA_VERSION = 4
CURRENT_ROOT_SCHEMA_VERSION = TRANSPORT_EVENT_STABLE_SCHEMA_VERSION

SUPPORTED_ROOT_SCHEMA_VERSIONS = frozenset(
    {
        WORKER_SEED_SCHEMA_VERSION,
        PRIMARY_EVENT_STABLE_SCHEMA_VERSION,
        TRANSPORT_EVENT_STABLE_SCHEMA_VERSION,
    }
)


def is_supported_root_schema_version(version: int) -> bool:
    """Return whether *version* has an explicit historical interpretation."""

    return type(version) is int and version in SUPPORTED_ROOT_SCHEMA_VERSIONS
