#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from array import array
from pathlib import Path

import ROOT

ROOT.gROOT.SetBatch(True)

PROJECT_DIR = Path(__file__).resolve().parents[1]

MODULE_PATH = (
    PROJECT_DIR
    / "scripts"
    / "analyze_performance_reproducibility.py"
)

SPEC = importlib.util.spec_from_file_location(
    "cycle11_schema4_analyzer",
    MODULE_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

ANALYZER = importlib.util.module_from_spec(
    SPEC
)

sys.modules[SPEC.name] = ANALYZER

SPEC.loader.exec_module(
    ANALYZER
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


def default_value(field):
    if field in STRING_FIELDS:
        return "synthetic"

    if field in DOUBLE_FIELDS:
        return 0.0

    return 0


def make_row(fields, **updates):
    result = {
        field: default_value(field)
        for field in fields
    }

    result.update(updates)

    return result


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
            holder = ROOT.std.string()
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

            holder = holders[field]
            value = row[field]

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
    path,
    *,
    schema_version,
    transport_seed=749816736,
):

    if schema_version == 4:
        event_fields = (
            ANALYZER.EVENT_FIELDS_V4
        )
    else:
        event_fields = (
            ANALYZER.EVENT_FIELDS_V3
        )

    metadata_fields = (
        ANALYZER.metadata_fields_for_schema(
            schema_version
        )
    )

    event_updates = dict(
        run=0,
        event=0,
        bcid=11000,
        mu_configured=1.0,
        n_interactions_requested=1,
        n_interactions_generated=1,
        generator_particles=10,
        transported_particles=5,
        total_edep_mev=10.0,
    )

    if schema_version == 4:
        event_updates[
            "geant4_transport_seed"
        ] = transport_seed

    events = [
        make_row(
            event_fields,
            **event_updates,
        )
    ]

    hits = [
        make_row(
            ANALYZER.HIT_FIELDS,
            run=0,
            event=0,
            bcid=11000,
            subevent=0,
            cell_id=1001.0,
            sampling=1,
            edep_mev=10.0,
            steps=2,
        )
    ]

    generator = [
        make_row(
            ANALYZER.GENERATOR_FIELDS,
            run=0,
            event=0,
            bcid=11000,
            subevent=0,
            index=0,
            pdg=211,
            status=1,
            is_final=1,
            is_visible=1,
            energy_gev=1.0,
            accepted_for_transport=1,
        )
    ]

    metadata_updates = dict(
        schema_version=schema_version,
        project_version="synthetic",
        git_commit="deadbeef",
        git_describe="synthetic",
        root_version=str(
            ROOT.gROOT.GetVersion()
        ),
        geant4_version="11.3.2",
        pythia_version="8.312",
        run=0,
        events=1,
        first_bcid=11000,
        threads=1,
        seed_base=9512,
        geant4_master_seed=9512,
        seed_policy="event-stable-v1",
        seed_identity="bcid",
        seed_mixer="splitmix64-v1",
        pythia_initialization_seed=258266518,
        pythia_seed_max=900000000,
        pythia_reseed_scope="subevent",
        interaction_mode="fixed",
        mean_interactions=1.0,
        fixed_interactions=1,
        pythia_config="pythia_minbias.cmnd",
        physics_list="FTFP_BERT_ATL",
        production_cut_mm=1.0,
        max_abs_eta=1.8,
        generator_audit=1,
        config_file="synthetic.conf",
        output_file="synthetic.root",
        normalized_config="synthetic",
        generator_mode="pythia",
    )

    if schema_version == 4:
        metadata_updates.update(
            geant4_transport_seed_policy=(
                "event-stable-v1"
            ),
            geant4_transport_seed_identity=(
                "bcid"
            ),
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
        event_fields,
        events,
    )

    write_tree(
        root_file,
        "hits",
        ANALYZER.HIT_FIELDS,
        hits,
    )

    write_tree(
        root_file,
        "generator",
        ANALYZER.GENERATOR_FIELDS,
        generator,
    )

    write_tree(
        root_file,
        "metadata",
        metadata_fields,
        metadata,
    )

    root_file.Close()


class Cycle11Schema4AnalyzerTest(
    unittest.TestCase
):

    def test_schema4_reads_transport_seed(self):

        with tempfile.TemporaryDirectory() as tmp:

            path = (
                Path(tmp)
                / "schema4.root"
            )

            write_fixture(
                path,
                schema_version=4,
            )

            result = (
                ANALYZER.extract_root_content(
                    path
                )
            )

        self.assertEqual(
            result[
                "metadata_schema_version"
            ],
            4,
        )

        self.assertEqual(
            result["event_fields"],
            ANALYZER.EVENT_FIELDS_V4,
        )

        self.assertEqual(
            result["rows"]["events"][0][
                "geant4_transport_seed"
            ],
            749816736,
        )

        metadata = (
            result["rows"]["metadata"][0]
        )

        self.assertEqual(
            metadata[
                "geant4_transport_seed_policy"
            ],
            "event-stable-v1",
        )

        self.assertEqual(
            metadata[
                "geant4_transport_seed_identity"
            ],
            "bcid",
        )

        self.assertEqual(
            metadata[
                "geant4_transport_seed_stream"
            ],
            "transport-event",
        )

        self.assertEqual(
            metadata[
                "geant4_transport_seed_max"
            ],
            2147483646,
        )

        self.assertEqual(
            metadata[
                "geant4_transport_reseed_scope"
            ],
            "event-before-tracking",
        )

    def test_schema3_remains_readable(self):

        with tempfile.TemporaryDirectory() as tmp:

            path = (
                Path(tmp)
                / "schema3.root"
            )

            write_fixture(
                path,
                schema_version=3,
            )

            result = (
                ANALYZER.extract_root_content(
                    path
                )
            )

        self.assertEqual(
            result[
                "metadata_schema_version"
            ],
            3,
        )

        self.assertEqual(
            result["event_fields"],
            ANALYZER.EVENT_FIELDS_V3,
        )

        self.assertNotIn(
            "geant4_transport_seed",
            result["rows"]["events"][0],
        )

    def test_schema4_transport_seed_is_scientific(self):

        with tempfile.TemporaryDirectory() as tmp:

            left = (
                Path(tmp)
                / "left.root"
            )

            right = (
                Path(tmp)
                / "right.root"
            )

            write_fixture(
                left,
                schema_version=4,
                transport_seed=749816736,
            )

            write_fixture(
                right,
                schema_version=4,
                transport_seed=749816737,
            )

            comparison = (
                ANALYZER.compare_root_files(
                    left,
                    right,
                )
            )

        self.assertFalse(
            comparison[
                "scientific_equal"
            ]
        )

        self.assertFalse(
            comparison[
                "trees"
            ][
                "events"
            ][
                "equal"
            ]
        )


if __name__ == "__main__":
    unittest.main()
