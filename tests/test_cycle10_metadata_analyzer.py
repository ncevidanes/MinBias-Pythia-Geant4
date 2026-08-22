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
    "cycle10_reproducibility_analyzer",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None

ANALYZER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ANALYZER
SPEC.loader.exec_module(ANALYZER)

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
}


def default_value(field: str):
    if field in STRING_FIELDS:
        return "synthetic"
    if field in DOUBLE_FIELDS:
        return 0.0
    return 0


def make_row(fields, **updates):
    row = {
        field: default_value(field)
        for field in fields
    }
    row.update(updates)
    return row


def write_tree(root_file, name, fields, rows):
    tree = ROOT.TTree(name, name)
    holders = {}

    for field in fields:
        if field in STRING_FIELDS:
            holder = ROOT.std.string()
            tree.Branch(field, holder)
        elif field in DOUBLE_FIELDS:
            holder = array("d", [0.0])
            tree.Branch(field, holder, f"{field}/D")
        else:
            holder = array("i", [0])
            tree.Branch(field, holder, f"{field}/I")

        holders[field] = holder

    for row in rows:
        for field in fields:
            holder = holders[field]
            value = row[field]

            if field in STRING_FIELDS:
                holder.assign(str(value))
            elif field in DOUBLE_FIELDS:
                holder[0] = float(value)
            else:
                holder[0] = int(value)

        tree.Fill()

    root_file.cd()
    tree.Write()


def write_fixture(
    path: Path,
    *,
    schema_version: int = 3,
    threads: int = 1,
    energy: float = 10.0,
    output_file: str = "synthetic.root",
    normalized_config: str = "synthetic-config",
    physics_list: str = "FTFP_BERT_ATL",
) -> None:
    events = [
        make_row(
            ANALYZER.EVENT_FIELDS,
            run=0,
            event=0,
            bcid=42,
            mu_configured=1.0,
            n_interactions_requested=1,
            n_interactions_generated=1,
            transported_particles=5,
            total_edep_mev=energy,
        )
    ]

    hits = [
        make_row(
            ANALYZER.HIT_FIELDS,
            run=0,
            event=0,
            bcid=42,
            subevent=0,
            cell_id=1001.0,
            sampling=1,
            edep_mev=energy,
            steps=2,
        )
    ]

    generator = [
        make_row(
            ANALYZER.GENERATOR_FIELDS,
            run=0,
            event=0,
            bcid=42,
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

    metadata_fields = (
        ANALYZER.metadata_fields_for_schema(
            schema_version
        )
    )

    metadata_updates = dict(
        schema_version=schema_version,
        project_version="synthetic",
        git_commit="deadbeef",
        git_describe="synthetic",
        root_version=str(ROOT.gROOT.GetVersion()),
        geant4_version="synthetic",
        pythia_version="synthetic",
        run=0,
        events=1,
        first_bcid=42,
        threads=threads,
        seed_base=9512,
        geant4_master_seed=9512,
        pythia_seed_max=900000000,
        interaction_mode="poisson",
        mean_interactions=1.0,
        fixed_interactions=1,
        pythia_config="pythia_minbias.cmnd",
        physics_list=physics_list,
        production_cut_mm=1.0,
        max_abs_eta=1.8,
        config_file="synthetic.conf",
        output_file=output_file,
        normalized_config=normalized_config,
        generator_mode="pythia",
    )

    if schema_version == 2:
        metadata_updates.update(
            pythia_seed_base=9512,
            pythia_worker_seed_stride=104729,
        )
    elif schema_version == 3:
        metadata_updates.update(
            seed_policy="event-stable-v1",
            seed_identity="bcid",
            seed_mixer="splitmix64-v1",
            pythia_initialization_seed=258266518,
            pythia_reseed_scope="subevent",
        )

    metadata = [
        make_row(
            metadata_fields,
            **metadata_updates,
        )
    ]

    root_file = ROOT.TFile(str(path), "RECREATE")

    write_tree(
        root_file,
        "events",
        ANALYZER.EVENT_FIELDS,
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


class Cycle10MetadataAnalyzerTest(unittest.TestCase):

    def test_tleafc_string_is_read_as_full_string(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tleafc.root"

            root_file = ROOT.TFile(
                str(path),
                "RECREATE",
            )

            tree = ROOT.TTree(
                "metadata",
                "metadata",
            )

            capacity = 128
            holder = array("b", [0] * capacity)

            tree.Branch(
                "seed_policy",
                holder,
                "seed_policy/C",
            )

            encoded = b"event-stable-v1"

            for index, byte in enumerate(encoded):
                holder[index] = byte

            holder[len(encoded)] = 0

            tree.Fill()
            tree.Write()
            root_file.Close()

            root_file = ROOT.TFile.Open(
                str(path),
                "READ",
            )

            tree = root_file.Get("metadata")
            self.assertGreater(tree.GetEntry(0), 0)

            leaf = tree.GetBranch(
                "seed_policy"
            ).GetLeaf("seed_policy")

            self.assertEqual(
                str(leaf.ClassName()),
                "TLeafC",
            )

            self.assertEqual(
                ANALYZER.read_branch_scalar(
                    tree,
                    "seed_policy",
                ),
                "event-stable-v1",
            )

            root_file.Close()

    def test_nonfinite_float_is_exactly_canonicalized(self):
        positive_infinity = ANALYZER.canonical_scalar(
            float("inf")
        )
        negative_infinity = ANALYZER.canonical_scalar(
            float("-inf")
        )
        nan_value = ANALYZER.canonical_scalar(
            float("nan")
        )

        self.assertEqual(
            positive_infinity,
            ("nf", "7ff0000000000000"),
        )

        self.assertEqual(
            negative_infinity,
            ("nf", "fff0000000000000"),
        )

        self.assertEqual(
            nan_value[0],
            "nf",
        )

        self.assertEqual(
            len(nan_value[1]),
            16,
        )

        self.assertNotEqual(
            positive_infinity,
            negative_infinity,
        )

        digest = ANALYZER.digest_rows(
            [{"eta": float("inf")}],
            ("eta",),
        )

        self.assertEqual(
            len(digest),
            64,
        )

    def test_schema3_is_read_with_event_stable_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "schema3.root"
            write_fixture(path, schema_version=3)

            result = ANALYZER.extract_root_content(path)

        self.assertEqual(
            result["metadata_schema_version"],
            3,
        )

        metadata = result["rows"]["metadata"][0]

        self.assertEqual(
            metadata["seed_policy"],
            "event-stable-v1",
        )
        self.assertEqual(
            metadata["seed_identity"],
            "bcid",
        )
        self.assertEqual(
            metadata["seed_mixer"],
            "splitmix64-v1",
        )
        self.assertEqual(
            metadata["pythia_reseed_scope"],
            "subevent",
        )
        self.assertNotIn(
            "pythia_worker_seed_stride",
            metadata,
        )

    def test_schema2_remains_readable(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "schema2.root"
            write_fixture(path, schema_version=2)

            result = ANALYZER.extract_root_content(path)

        self.assertEqual(
            result["metadata_schema_version"],
            2,
        )

        metadata = result["rows"]["metadata"][0]

        self.assertEqual(
            metadata["pythia_worker_seed_stride"],
            104729,
        )
        self.assertNotIn(
            "seed_policy",
            metadata,
        )

    def test_schema3_cross_thread_allows_operational_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            left = Path(temporary) / "left.root"
            right = Path(temporary) / "right.root"

            write_fixture(
                left,
                threads=1,
                output_file="left.root",
                normalized_config="threads=1;output=left",
            )

            write_fixture(
                right,
                threads=2,
                output_file="right.root",
                normalized_config="threads=2;output=right",
            )

            comparison = ANALYZER.compare_root_files(
                left,
                right,
            )

            evaluation = ANALYZER.evaluate_comparison(
                "cross-thread",
                comparison,
            )

        self.assertTrue(comparison["scientific_equal"])
        self.assertFalse(comparison["metadata_equal"])
        self.assertTrue(evaluation["accepted"])
        self.assertTrue(
            evaluation["metadata_policy_equal"]
        )
        self.assertEqual(
            evaluation["unexpected_metadata_fields"],
            [],
        )
        self.assertFalse(
            evaluation["legacy_cycle9_policy"]
        )

    def test_schema3_cross_thread_science_difference_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            left = Path(temporary) / "left.root"
            right = Path(temporary) / "right.root"

            write_fixture(left, threads=1, energy=10.0)
            write_fixture(right, threads=2, energy=11.0)

            comparison = ANALYZER.compare_root_files(
                left,
                right,
            )

            evaluation = ANALYZER.evaluate_comparison(
                "cross-thread",
                comparison,
            )

        self.assertFalse(comparison["scientific_equal"])
        self.assertFalse(evaluation["accepted"])
        self.assertEqual(
            evaluation["classification"],
            "FAIL",
        )

    def test_schema3_unexpected_physics_metadata_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            left = Path(temporary) / "left.root"
            right = Path(temporary) / "right.root"

            write_fixture(
                left,
                threads=1,
                physics_list="FTFP_BERT_ATL",
            )
            write_fixture(
                right,
                threads=2,
                physics_list="QGSP_BERT",
            )

            comparison = ANALYZER.compare_root_files(
                left,
                right,
            )

            evaluation = ANALYZER.evaluate_comparison(
                "cross-thread",
                comparison,
            )

        self.assertTrue(comparison["scientific_equal"])
        self.assertFalse(evaluation["accepted"])
        self.assertEqual(
            evaluation["unexpected_metadata_fields"],
            ["physics_list"],
        )

    def test_schema2_preserves_cycle9_reporting_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            left = Path(temporary) / "left.root"
            right = Path(temporary) / "right.root"

            write_fixture(
                left,
                schema_version=2,
                threads=1,
                energy=10.0,
            )
            write_fixture(
                right,
                schema_version=2,
                threads=2,
                energy=11.0,
            )

            comparison = ANALYZER.compare_root_files(
                left,
                right,
            )

            evaluation = ANALYZER.evaluate_comparison(
                "cross-thread",
                comparison,
            )

        self.assertFalse(comparison["scientific_equal"])
        self.assertTrue(evaluation["accepted"])
        self.assertTrue(
            evaluation["legacy_cycle9_policy"]
        )
        self.assertEqual(
            evaluation["classification"],
            "MEASURED_DIFFERENCE",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
