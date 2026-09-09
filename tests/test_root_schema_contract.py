#!/usr/bin/env python3
"""Regression tests for the shared Python ROOT schema contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = PROJECT_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import root_schema_contract as contract


class RootSchemaContractTest(unittest.TestCase):
    def test_current_schema_is_supported(self) -> None:
        self.assertEqual(contract.CURRENT_ROOT_SCHEMA_VERSION, 4)
        self.assertTrue(
            contract.is_supported_root_schema_version(
                contract.CURRENT_ROOT_SCHEMA_VERSION
            )
        )

    def test_historical_interpretations_are_explicit(self) -> None:
        self.assertEqual(contract.SUPPORTED_ROOT_SCHEMA_VERSIONS, {2, 3, 4})
        for version in (2, 3, 4):
            self.assertTrue(contract.is_supported_root_schema_version(version))

    def test_unknown_and_non_integer_versions_are_rejected(self) -> None:
        for version in (1, 5, -1, True, 4.0, "4"):
            self.assertFalse(contract.is_supported_root_schema_version(version))


if __name__ == "__main__":
    unittest.main()
