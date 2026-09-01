#!/usr/bin/env python3
"""Cycle 11 tests for the partition-aware ROOT adapter."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from array import array
from pathlib import Path

import ROOT


ROOT.gROOT.SetBatch(True)

PROJECT_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
)

SCRIPTS_DIR = (
    PROJECT_DIR
    / "scripts"
)

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(SCRIPTS_DIR),
    )

import analyze_performance_reproducibility as PERF


ADAPTER_PATH = (
    SCRIPTS_DIR
    / "analyze_partition_root.py"
)

SPEC = importlib.util.spec_from_file_location(
    "partition_root_adapter",
    ADAPTER_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

ADAPTER = (
    importlib.util
    .module_from_spec(
        SPEC
    )
)

sys.modules[SPEC.name] = ADAPTER

SPEC.loader.exec_module(
    ADAPTER
)


DOUBLE_FIELDS = {
    "mu_configured",
    "total_edep_mev",
    "cell_id",
    "eta_center",
    "phi_center",
    "edep_mev",
    "time_mean_ns",
    "time_first_ns",
    "px_gev",
    "py_gev",
    "pz_gev",
    "energy_gev",
    "mass_gev",
    "eta",
    "phi",
    "x_prod_mm",
    "y_prod_mm",
    "z_prod_mm",
    "t_prod_mm_over_c",
    "mean_interactions",
    "production_cut_mm",
    "beam_sigma_x_mm",
    "beam_sigma_y_mm",
    "beam_sigma_z_mm",
    "beam_sigma_t_ns",
    "max_abs_eta",
    "single_particle_kinetic_energy_gev",
    "single_particle_eta",
    "single_particle_phi",
}

STRING_FIELDS = {
    "project_version",
    "git_commit",
    "git_describe",
    "root_version",
    "geant4_version",
    "pythia_version",
    "seed_policy",
    "seed_identity",
    "seed_mixer",
    "pythia_reseed_scope",
    "interaction_mode",
    "pythia_config",
    "physics_list",
    "config_file",
    "output_file",
    "normalized_config",
    "generator_mode",
    "geant4_transport_seed_policy",
    "geant4_transport_seed_identity",
    "geant4_transport_seed_mixer",
    "geant4_transport_seed_stream",
    "geant4_transport_reseed_scope",
}


def default_value(field: str):

    if field in STRING_FIELDS:
        return "synthetic"

    if field in DOUBLE_FIELDS:
        return 0.0

    return 0


def make_row(
    fields,
    **updates,
):

    row = {
        field: default_value(field)
        for field in fields
    }

    row.update(
        updates
    )

    return row


def write_tree(
    root_file,
    name,
    fields,
    rows,
):

    tree = ROOT.TTree(
        name,
        name,
    )

    holders = {}

    for field in fields:

        if field in STRING_FIELDS:

            holder = (
                ROOT.std.string()
            )

            tree.Branch(
                field,
                holder,
            )

        elif field in DOUBLE_FIELDS:

            holder = array(
                "d",
                [0.0],
            )

            tree.Branch(
                field,
                holder,
                f"{field}/D",
            )

        else:

            holder = array(
                "i",
                [0],
            )

            tree.Branch(
                field,
                holder,
                f"{field}/I",
            )

        holders[field] = holder

    for row in rows:

        for field in fields:

            holder = (
                holders[field]
            )

            value = (
                row[field]
            )

            if field in STRING_FIELDS:

                holder.assign(
                    str(value)
                )

            elif field in DOUBLE_FIELDS:

                holder[0] = float(
                    value
                )

            else:

                holder[0] = int(
                    value
                )

        tree.Fill()

    root_file.cd()
    tree.Write()


def write_fixture(
    path: Path,
    *,
    first_bcid: int,
    events: int,
    threads: int = 1,
    schema_version: int = 4,
    physics_list: str = "FTFP_BERT_ATL",
    event_delta: float = 0.0,
    hit_delta: float = 0.0,
    generator_delta: float = 0.0,
):

    event_rows = []
    hit_rows = []
    generator_rows = []

    for local_event in range(
        events
    ):

        bcid = (
            first_bcid
            + local_event
        )

        base_energy = float(
            10_000
            + bcid
        )

        local_event_delta = (
            event_delta
            if local_event == 0
            else 0.0
        )

        local_hit_delta = (
            hit_delta
            if local_event == 0
            else 0.0
        )

        local_generator_delta = (
            generator_delta
            if local_event == 0
            else 0.0
        )

        event_rows.append(
            make_row(
                PERF.event_fields_for_schema(schema_version),
                run=0,
                event=local_event,
                bcid=bcid,
                mu_configured=1.0,
                n_interactions_requested=1,
                n_interactions_generated=1,
                generation_failures=0,
                generator_particles=1,
                transported_particles=1,
                unknown_pdg_particles=0,
                total_edep_mev=(
                    base_energy
                    + local_event_delta
                ),
                unlineaged_steps=0,
                segmentation_failures=0,
            )
        )

        hit_rows.append(
            make_row(
                PERF.HIT_FIELDS,
                run=0,
                event=local_event,
                bcid=bcid,
                subevent=0,
                cell_id=float(
                    100_000
                    + bcid
                ),
                sampling=2,
                edep_mev=(
                    base_energy
                    + local_hit_delta
                ),
                steps=1,
            )
        )

        generator_rows.append(
            make_row(
                PERF.GENERATOR_FIELDS,
                run=0,
                event=local_event,
                bcid=bcid,
                subevent=0,
                index=0,
                pdg=211,
                status=1,
                is_final=1,
                is_visible=1,
                energy_gev=(
                    float(bcid)
                    + local_generator_delta
                ),
                accepted_for_transport=1,
            )
        )

    metadata_fields = (
        PERF
        .metadata_fields_for_schema(
            schema_version
        )
    )

    metadata_updates = {
        "schema_version": schema_version,
        "project_version": "synthetic",
        "git_commit": "bc9c4aa",
        "git_describe": "synthetic",
        "root_version": str(
            ROOT.gROOT.GetVersion()
        ),
        "geant4_version": "synthetic",
        "pythia_version": "synthetic",
        "run": 0,
        "events": events,
        "first_bcid": first_bcid,
        "threads": threads,
        "seed_base": 9512,
        "geant4_master_seed": 9512,
        "pythia_seed_max": 900000000,
        "interaction_mode": "poisson",
        "mean_interactions": 1.0,
        "fixed_interactions": 1,
        "pythia_config": (
            "pythia_minbias.cmnd"
        ),
        "physics_list": physics_list,
        "production_cut_mm": 1.0,
        "beam_sigma_x_mm": 0.1,
        "beam_sigma_y_mm": 0.1,
        "beam_sigma_z_mm": 10.0,
        "beam_sigma_t_ns": 0.2,
        "max_abs_eta": 1.8,
        "transport_neutrinos": 0,
        "generator_audit": 1,
        "check_overlaps": 0,
        "print_every": 100,
        "config_file": (
            f"synthetic-{first_bcid}.conf"
        ),
        "output_file": str(path),
        "normalized_config": (
            f"first_bcid={first_bcid};"
            f"events={events};"
            f"threads={threads}"
        ),
        "generator_mode": "pythia",
        "single_particle_pdg": 11,
        "single_particle_kinetic_energy_gev": 1.0,
        "single_particle_eta": 0.0,
        "single_particle_phi": 0.0,
    }

    if schema_version in (3, 4):

        metadata_updates.update(
            {
                "seed_policy": (
                    "event-stable-v1"
                ),
                "seed_identity": "bcid",
                "seed_mixer": (
                    "splitmix64-v1"
                ),
                "pythia_initialization_seed": (
                    258266518
                ),
                "pythia_reseed_scope": (
                    "subevent"
                ),
            }
        )

    elif schema_version == 2:

        metadata_updates.update(
            {
                "pythia_seed_base": 9512,
                "pythia_worker_seed_stride": (
                    104729
                ),
            }
        )

    if schema_version == 4:
        metadata_updates.update(
            geant4_transport_seed_policy=(
                "event-stable-v1"
            ),
            geant4_transport_seed_identity="bcid",
            geant4_transport_seed_mixer=(
                "splitmix64-v1"
            ),
            geant4_transport_seed_stream=(
                "transport-event"
            ),
            geant4_transport_seed_max=(
                2147483646
            ),
            geant4_transport_reseed_scope=(
                "event-before-tracking"
            ),
        )

    metadata = [
        make_row(
            metadata_fields,
            **metadata_updates,
        )
    ]

    root_file = ROOT.TFile(
        str(path),
        "RECREATE",
    )

    write_tree(
        root_file,
        "events",
        PERF.event_fields_for_schema(schema_version),
        event_rows,
    )

    write_tree(
        root_file,
        "hits",
        PERF.HIT_FIELDS,
        hit_rows,
    )

    write_tree(
        root_file,
        "generator",
        PERF.GENERATOR_FIELDS,
        generator_rows,
    )

    write_tree(
        root_file,
        "metadata",
        metadata_fields,
        metadata,
    )

    root_file.Close()


class PartitionRootAdapterTest(
    unittest.TestCase
):

    def make_reference_set(
        self,
        directory: Path,
        *,
        mixed_threads: bool = False,
    ):

        mono = (
            directory
            / "mono.root"
        )

        shard_a = (
            directory
            / "shard-a.root"
        )

        shard_b = (
            directory
            / "shard-b.root"
        )

        write_fixture(
            mono,
            first_bcid=100,
            events=4,
            threads=1,
        )

        write_fixture(
            shard_a,
            first_bcid=100,
            events=2,
            threads=1,
        )

        write_fixture(
            shard_b,
            first_bcid=102,
            events=2,
            threads=(
                2
                if mixed_threads
                else 1
            ),
        )

        return (
            mono,
            shard_a,
            shard_b,
        )

    def compare(
        self,
        mono,
        shards,
    ):

        return (
            ADAPTER
            .compare_root_partition(
                mono,
                shards,
                first_global_bcid=100,
                total_events=4,
            )
        )

    def test_schema4_root_partition_equals_monolithic(
        self,
    ):

        with tempfile.TemporaryDirectory() as temporary:

            directory = Path(
                temporary
            )

            mono, a, b = (
                self.make_reference_set(
                    directory
                )
            )

            result = self.compare(
                mono,
                [a, b],
            )

        self.assertTrue(
            result[
                "scientific_equal"
            ]
        )

        self.assertEqual(
            result[
                "metadata_schema_version"
            ],
            4,
        )

        self.assertEqual(
            result[
                "classification"
            ],
            "FULL_PARTITION_STABILITY=PASS",
        )

    def test_local_event_restart_survives_root_roundtrip(
        self,
    ):

        with tempfile.TemporaryDirectory() as temporary:

            directory = Path(
                temporary
            )

            mono, a, b = (
                self.make_reference_set(
                    directory
                )
            )

            shard = (
                ADAPTER
                .load_root_shard(
                    b
                )
            )

            self.assertEqual(
                int(
                    shard[
                        "rows"
                    ][
                        "events"
                    ][0][
                        "event"
                    ]
                ),
                0,
            )

            self.assertEqual(
                int(
                    shard[
                        "rows"
                    ][
                        "events"
                    ][0][
                        "bcid"
                    ]
                ),
                102,
            )

            result = self.compare(
                mono,
                [a, b],
            )

        self.assertTrue(
            result[
                "scientific_equal"
            ]
        )

    def test_reversed_root_shard_order_is_identical(
        self,
    ):

        with tempfile.TemporaryDirectory() as temporary:

            directory = Path(
                temporary
            )

            mono, a, b = (
                self.make_reference_set(
                    directory
                )
            )

            forward = self.compare(
                mono,
                [a, b],
            )

            reverse = self.compare(
                mono,
                [b, a],
            )

        for tree in (
            "events",
            "hits",
            "generator",
        ):

            self.assertEqual(
                forward[
                    "trees"
                ][tree][
                    "partition_digest"
                ],
                reverse[
                    "trees"
                ][tree][
                    "partition_digest"
                ],
            )

    def test_mixed_threads_are_operational_after_root_roundtrip(
        self,
    ):

        with tempfile.TemporaryDirectory() as temporary:

            directory = Path(
                temporary
            )

            mono, a, b = (
                self.make_reference_set(
                    directory,
                    mixed_threads=True,
                )
            )

            result = self.compare(
                mono,
                [a, b],
            )

        self.assertTrue(
            result[
                "scientific_equal"
            ]
        )

    def test_event_difference_classifies_transport_failure(
        self,
    ):

        with tempfile.TemporaryDirectory() as temporary:

            directory = Path(
                temporary
            )

            mono, a, b = (
                self.make_reference_set(
                    directory
                )
            )

            write_fixture(
                b,
                first_bcid=102,
                events=2,
                event_delta=1.0,
            )

            result = self.compare(
                mono,
                [a, b],
            )

        self.assertTrue(
            result[
                "generator_equal"
            ]
        )

        self.assertFalse(
            result[
                "events_equal"
            ]
        )

        self.assertEqual(
            result[
                "classification"
            ],
            "PRIMARY_PARTITION_STABILITY=PASS;"
            "TRANSPORT_PARTITION_STABILITY=FAIL",
        )

    def test_generator_difference_classifies_primary_failure(
        self,
    ):

        with tempfile.TemporaryDirectory() as temporary:

            directory = Path(
                temporary
            )

            mono, a, b = (
                self.make_reference_set(
                    directory
                )
            )

            write_fixture(
                b,
                first_bcid=102,
                events=2,
                generator_delta=1.0,
            )

            result = self.compare(
                mono,
                [a, b],
            )

        self.assertFalse(
            result[
                "generator_equal"
            ]
        )

        self.assertEqual(
            result[
                "classification"
            ],
            "PRIMARY_PARTITION_STABILITY=FAIL",
        )

    def test_scientific_metadata_difference_is_rejected(
        self,
    ):

        with tempfile.TemporaryDirectory() as temporary:

            directory = Path(
                temporary
            )

            mono, a, b = (
                self.make_reference_set(
                    directory
                )
            )

            write_fixture(
                b,
                first_bcid=102,
                events=2,
                physics_list=(
                    "DIFFERENT"
                ),
            )

            with self.assertRaises(
                ADAPTER.PartitionRootError
            ) as context:

                self.compare(
                    mono,
                    [a, b],
                )

        self.assertIn(
            "unexpected metadata differences",
            str(
                context.exception
            ),
        )

    def test_schema2_is_rejected_for_cycle11(
        self,
    ):

        with tempfile.TemporaryDirectory() as temporary:

            directory = Path(
                temporary
            )

            path = (
                directory
                / "schema2.root"
            )

            write_fixture(
                path,
                first_bcid=100,
                events=1,
                schema_version=2,
            )

            with self.assertRaises(
                ADAPTER.PartitionRootError
            ) as context:

                ADAPTER.load_root_shard(
                    path
                )

        self.assertIn(
            "requires metadata schema 4",
            str(
                context.exception
            ),
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
