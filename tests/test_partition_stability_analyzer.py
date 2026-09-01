#!/usr/bin/env python3
"""Cycle 11 dependency-light partition-stability tests."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

MODULE_PATH = (
    PROJECT_DIR
    / "scripts"
    / "analyze_partition_stability.py"
)

SPEC = importlib.util.spec_from_file_location(
    "partition_stability_analyzer",
    MODULE_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

ANALYZER = importlib.util.module_from_spec(
    SPEC
)

sys.modules[SPEC.name] = ANALYZER
SPEC.loader.exec_module(ANALYZER)


def full_row(fields, **updates):
    row = {
        field: 0
        for field in fields
    }

    row.update(updates)

    return row


def make_metadata(
    name,
    first_bcid,
    events,
    threads=1,
):
    return {
        "schema_version": 4,
        "geant4_transport_seed_policy": "event-stable-v1",
        "geant4_transport_seed_identity": "bcid",
        "geant4_transport_seed_mixer": "splitmix64-v1",
        "geant4_transport_seed_stream": "transport-event",
        "geant4_transport_seed_max": 2147483646,
        "geant4_transport_reseed_scope": "event-before-tracking",
        "project_version": "synthetic",
        "git_commit": "bc9c4aa",
        "root_version": "synthetic",
        "geant4_version": "synthetic",
        "pythia_version": "synthetic",
        "events": events,
        "first_bcid": first_bcid,
        "threads": threads,
        "seed_base": 9512,
        "seed_policy": "event-stable-v1",
        "seed_identity": "bcid",
        "seed_mixer": "splitmix64-v1",
        "interaction_mode": "poisson",
        "mean_interactions": 1.0,
        "physics_list": "FTFP_BERT_ATL",
        "output_file": f"{name}.root",
        "config_file": f"{name}.conf",
        "normalized_config": f"name={name}",
    }


def make_shard(
    name,
    first_bcid,
    events,
    threads=1,
):

    event_rows = []
    hit_rows = []
    generator_rows = []

    for local_event in range(events):

        bcid = (
            first_bcid
            + local_event
        )

        energy = float(
            10_000
            + bcid
        )

        event_rows.append(
            full_row(
                ANALYZER.EVENT_FIELDS,
                run=0,
                event=local_event,
                bcid=bcid,
                mu_configured=1.0,
                n_interactions_requested=1,
                n_interactions_generated=1,
                generator_particles=1,
                transported_particles=1,
                total_edep_mev=energy,
            )
        )

        hit_rows.append(
            full_row(
                ANALYZER.HIT_FIELDS,
                run=0,
                event=local_event,
                bcid=bcid,
                subevent=0,
                cell_id=100_000 + bcid,
                sampling=2,
                edep_mev=energy,
                steps=1,
            )
        )

        generator_rows.append(
            full_row(
                ANALYZER.GENERATOR_FIELDS,
                run=0,
                event=local_event,
                bcid=bcid,
                subevent=0,
                index=0,
                pdg=211,
                status=1,
                is_final=1,
                is_visible=1,
                energy_gev=float(bcid),
                accepted_for_transport=1,
            )
        )

    return {
        "name": name,
        "rows": {
            "events": event_rows,
            "hits": hit_rows,
            "generator": generator_rows,
            "metadata": [
                make_metadata(
                    name,
                    first_bcid,
                    events,
                    threads,
                )
            ],
        },
    }


def equivalent_fixture(
    mixed_threads=False,
):

    mono = make_shard(
        "mono",
        100,
        4,
        threads=1,
    )

    left = make_shard(
        "left",
        100,
        2,
        threads=1,
    )

    right = make_shard(
        "right",
        102,
        2,
        threads=(
            2
            if mixed_threads
            else 1
        ),
    )

    return mono, left, right


class PartitionStabilityAnalyzerTest(
    unittest.TestCase
):

    def compare(
        self,
        mono,
        shards,
    ):
        return (
            ANALYZER
            .compare_monolithic_to_partition(
                mono,
                shards,
                first_global_bcid=100,
                total_events=4,
            )
        )

    def assert_partition_error(
        self,
        callback,
        text,
    ):
        with self.assertRaises(
            ANALYZER.PartitionAnalysisError
        ) as context:
            callback()

        self.assertIn(
            text,
            str(context.exception),
        )

    def test_equivalent_two_shards_equal_monolithic(
        self,
    ):
        mono, left, right = (
            equivalent_fixture()
        )

        result = self.compare(
            mono,
            [left, right],
        )

        self.assertTrue(
            result["scientific_equal"]
        )

        self.assertEqual(
            result["classification"],
            "FULL_PARTITION_STABILITY=PASS",
        )

    def test_local_event_restart_is_allowed(
        self,
    ):
        mono, left, right = (
            equivalent_fixture()
        )

        self.assertEqual(
            right["rows"]["events"][0]["event"],
            0,
        )

        self.assertEqual(
            right["rows"]["events"][0]["bcid"],
            102,
        )

        result = self.compare(
            mono,
            [left, right],
        )

        self.assertTrue(
            result["scientific_equal"]
        )

    def test_reversed_shard_order_is_equal(
        self,
    ):
        mono, left, right = (
            equivalent_fixture()
        )

        forward = self.compare(
            mono,
            [left, right],
        )

        reverse = self.compare(
            mono,
            [right, left],
        )

        self.assertTrue(
            forward["scientific_equal"]
        )

        self.assertTrue(
            reverse["scientific_equal"]
        )

        for tree in ANALYZER.SCIENTIFIC_TREES:
            self.assertEqual(
                forward["trees"][tree][
                    "partition_digest"
                ],
                reverse["trees"][tree][
                    "partition_digest"
                ],
            )

    def test_mixed_thread_counts_are_operational(
        self,
    ):
        mono, left, right = (
            equivalent_fixture(
                mixed_threads=True
            )
        )

        result = self.compare(
            mono,
            [left, right],
        )

        self.assertTrue(
            result["scientific_equal"]
        )

    def test_bcid_gap_is_rejected(
        self,
    ):
        left = make_shard(
            "left",
            100,
            2,
        )

        right = make_shard(
            "right",
            103,
            1,
        )

        self.assert_partition_error(
            lambda:
            ANALYZER.aggregate_partition(
                [left, right],
                first_global_bcid=100,
                total_events=4,
            ),
            "gaps in global BCID coverage",
        )

    def test_bcid_overlap_is_rejected(
        self,
    ):
        left = make_shard(
            "left",
            100,
            3,
        )

        right = make_shard(
            "right",
            102,
            2,
        )

        self.assert_partition_error(
            lambda:
            ANALYZER.aggregate_partition(
                [left, right],
                first_global_bcid=100,
                total_events=4,
            ),
            "overlapping/duplicate BCIDs",
        )

    def test_duplicate_bcid_inside_shard(
        self,
    ):
        shard = make_shard(
            "bad",
            100,
            2,
        )

        shard["rows"]["events"][1][
            "bcid"
        ] = 100

        self.assert_partition_error(
            lambda:
            ANALYZER.validate_shard(
                shard
            ),
            "duplicate BCID",
        )

    def test_duplicate_hit_global_key(
        self,
    ):
        shard = make_shard(
            "bad",
            100,
            2,
        )

        shard["rows"]["hits"].append(
            dict(
                shard["rows"]["hits"][0]
            )
        )

        self.assert_partition_error(
            lambda:
            ANALYZER.validate_shard(
                shard
            ),
            "hits: duplicate global canonical key",
        )

    def test_duplicate_generator_global_key(
        self,
    ):
        shard = make_shard(
            "bad",
            100,
            2,
        )

        shard[
            "rows"
        ][
            "generator"
        ].append(
            dict(
                shard[
                    "rows"
                ][
                    "generator"
                ][0]
            )
        )

        self.assert_partition_error(
            lambda:
            ANALYZER.validate_shard(
                shard
            ),
            "generator: duplicate global canonical key",
        )

    def test_local_event_gap_is_rejected(
        self,
    ):
        shard = make_shard(
            "bad",
            100,
            2,
        )

        shard[
            "rows"
        ][
            "events"
        ][1][
            "event"
        ] = 2

        self.assert_partition_error(
            lambda:
            ANALYZER.validate_shard(
                shard
            ),
            "incomplete local event interval",
        )

    def test_event_bcid_relation_violation(
        self,
    ):
        shard = make_shard(
            "bad",
            100,
            2,
        )

        shard["rows"]["events"][0][
            "bcid"
        ] = 101

        shard["rows"]["events"][1][
            "bcid"
        ] = 100

        self.assert_partition_error(
            lambda:
            ANALYZER.validate_shard(
                shard
            ),
            "bcid = first_bcid + event violated",
        )

    def test_event_difference_is_detected(
        self,
    ):
        mono, left, right = (
            equivalent_fixture()
        )

        right["rows"]["events"][0][
            "total_edep_mev"
        ] += 1.0

        result = self.compare(
            mono,
            [left, right],
        )

        self.assertFalse(
            result["events_equal"]
        )

        self.assertTrue(
            result["generator_equal"]
        )

        self.assertEqual(
            result["classification"],
            "PRIMARY_PARTITION_STABILITY=PASS;"
            "TRANSPORT_PARTITION_STABILITY=FAIL",
        )

    def test_hit_difference_is_detected(
        self,
    ):
        mono, left, right = (
            equivalent_fixture()
        )

        right["rows"]["hits"][0][
            "edep_mev"
        ] += 1.0

        result = self.compare(
            mono,
            [left, right],
        )

        self.assertFalse(
            result["hits_equal"]
        )

        self.assertTrue(
            result["generator_equal"]
        )

    def test_generator_difference_is_detected(
        self,
    ):
        mono, left, right = (
            equivalent_fixture()
        )

        right[
            "rows"
        ][
            "generator"
        ][0][
            "energy_gev"
        ] += 1.0

        result = self.compare(
            mono,
            [left, right],
        )

        self.assertFalse(
            result["generator_equal"]
        )

        self.assertEqual(
            result["classification"],
            "PRIMARY_PARTITION_STABILITY=FAIL",
        )

    def test_unexpected_metadata_difference(
        self,
    ):
        mono, left, right = (
            equivalent_fixture()
        )

        right["rows"]["metadata"][0][
            "physics_list"
        ] = "DIFFERENT"

        self.assert_partition_error(
            lambda:
            self.compare(
                mono,
                [left, right],
            ),
            "unexpected metadata differences",
        )

    def test_allowed_operational_metadata(
        self,
    ):
        mono, left, right = (
            equivalent_fixture(
                mixed_threads=True
            )
        )

        result = self.compare(
            mono,
            [left, right],
        )

        self.assertTrue(
            result["scientific_equal"]
        )

    def test_outside_global_interval_is_rejected(
        self,
    ):
        left = make_shard(
            "left",
            100,
            2,
        )

        right = make_shard(
            "right",
            102,
            3,
        )

        self.assert_partition_error(
            lambda:
            ANALYZER.aggregate_partition(
                [left, right],
                first_global_bcid=100,
                total_events=4,
            ),
            "outside global interval",
        )

    def test_orphan_hit_is_rejected(
        self,
    ):
        shard = make_shard(
            "bad",
            100,
            2,
        )

        shard["rows"]["hits"][0][
            "event"
        ] = 9

        self.assert_partition_error(
            lambda:
            ANALYZER.validate_shard(
                shard
            ),
            "orphan hits record",
        )

    def test_orphan_generator_is_rejected(
        self,
    ):
        shard = make_shard(
            "bad",
            100,
            2,
        )

        shard[
            "rows"
        ][
            "generator"
        ][0][
            "bcid"
        ] = 999

        self.assert_partition_error(
            lambda:
            ANALYZER.validate_shard(
                shard
            ),
            "orphan generator record",
        )

    def test_metadata_field_mismatch(
        self,
    ):
        mono, left, right = (
            equivalent_fixture()
        )

        del right[
            "rows"
        ][
            "metadata"
        ][0][
            "seed_mixer"
        ]

        self.assert_partition_error(
            lambda:
            self.compare(
                mono,
                [left, right],
            ),
            "metadata field mismatch",
        )


class PartitionSchema4ContractTest(
    unittest.TestCase
):

    @staticmethod
    def _shard(
        *,
        schema_version=4,
        transport_seed=123456789,
        transport_policy="event-stable-v1",
    ):

        event = {
            field: 0
            for field in ANALYZER.EVENT_FIELDS
        }

        event.update(
            run=0,
            event=0,
            bcid=42,
            geant4_transport_seed=(
                transport_seed
            ),
        )

        metadata = {
            "schema_version": schema_version,
            "events": 1,
            "first_bcid": 42,
            "geant4_transport_seed_policy": (
                transport_policy
            ),
            "geant4_transport_seed_identity": "bcid",
            "geant4_transport_seed_mixer": (
                "splitmix64-v1"
            ),
            "geant4_transport_seed_stream": (
                "transport-event"
            ),
            "geant4_transport_seed_max": (
                2147483646
            ),
            "geant4_transport_reseed_scope": (
                "event-before-tracking"
            ),
        }

        return {
            "name": "schema4-contract",
            "rows": {
                "events": [event],
                "hits": [],
                "generator": [],
                "metadata": [metadata],
            },
        }

    def test_post_correction_schema_is_four(
        self,
    ):

        self.assertEqual(
            ANALYZER.REQUIRED_SCHEMA_VERSION,
            4,
        )

    def test_transport_seed_is_scientific_event_field(
        self,
    ):

        self.assertIn(
            "geant4_transport_seed",
            ANALYZER.GLOBAL_FIELDS[
                "events"
            ],
        )

    def test_schema3_is_rejected_post_correction(
        self,
    ):

        shard = self._shard(
            schema_version=3,
        )

        with self.assertRaisesRegex(
            ANALYZER.PartitionAnalysisError,
            "requires metadata schema 4",
        ):

            ANALYZER.validate_shard(
                shard
            )

    def test_transport_metadata_policy_is_enforced(
        self,
    ):

        shard = self._shard(
            transport_policy="wrong-policy",
        )

        with self.assertRaisesRegex(
            ANALYZER.PartitionAnalysisError,
            (
                "unexpected "
                "geant4_transport_seed_policy"
            ),
        ):

            ANALYZER.validate_shard(
                shard
            )

    def test_transport_seed_difference_is_scientific(
        self,
    ):

        mono = self._shard(
            transport_seed=1001,
        )

        partition = self._shard(
            transport_seed=1002,
        )

        result = (
            ANALYZER
            .compare_monolithic_to_partition(
                mono,
                [partition],
                first_global_bcid=42,
                total_events=1,
            )
        )

        self.assertTrue(
            result["generator_equal"]
        )

        self.assertFalse(
            result["events_equal"]
        )

        self.assertFalse(
            result["scientific_equal"]
        )

        self.assertEqual(
            result["classification"],
            (
                "PRIMARY_PARTITION_STABILITY=PASS;"
                "TRANSPORT_PARTITION_STABILITY=FAIL"
            ),
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
