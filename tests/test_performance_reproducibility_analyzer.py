#!/usr/bin/env python3
"""Regression tests for the Cycle 9 canonical ROOT analyzer."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from array import array
from pathlib import Path

import ROOT


ROOT.gROOT.SetBatch(True)

PROJECT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_DIR / "scripts" / "analyze_performance_reproducibility.py"

SPEC = importlib.util.spec_from_file_location(
    "performance_reproducibility_analyzer",
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
    "interaction_mode",
    "pythia_config",
    "physics_list",
    "config_file",
    "generator_mode",
}


def default_value(field: str):
    if field in STRING_FIELDS:
        return "synthetic"
    if field in DOUBLE_FIELDS:
        return 0.0
    return 0


def make_row(fields, **updates):
    row = {field: default_value(field) for field in fields}
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
            value = row[field]
            holder = holders[field]
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
    reverse: bool = False,
    energy: float = 10.0,
    threads: int = 1,
) -> None:
    events = [
        make_row(
            ANALYZER.EVENT_FIELDS,
            run=0,
            event=0,
            bcid=0,
            mu_configured=1.0,
            n_interactions_requested=1,
            n_interactions_generated=1,
            transported_particles=5,
            total_edep_mev=energy,
        ),
        make_row(
            ANALYZER.EVENT_FIELDS,
            run=0,
            event=1,
            bcid=1,
            mu_configured=1.0,
            n_interactions_requested=1,
            n_interactions_generated=1,
            transported_particles=4,
            total_edep_mev=5.0,
        ),
    ]

    hits = [
        make_row(
            ANALYZER.HIT_FIELDS,
            run=0,
            event=0,
            bcid=0,
            subevent=0,
            cell_id=1001.0,
            sampling=1,
            edep_mev=energy,
            steps=2,
        ),
        make_row(
            ANALYZER.HIT_FIELDS,
            run=0,
            event=1,
            bcid=1,
            subevent=0,
            cell_id=1002.0,
            sampling=2,
            edep_mev=5.0,
            steps=1,
        ),
    ]

    generator = [
        make_row(
            ANALYZER.GENERATOR_FIELDS,
            run=0,
            event=0,
            bcid=0,
            subevent=0,
            index=0,
            pdg=211,
            status=1,
            is_final=1,
            is_visible=1,
            energy_gev=1.0,
            accepted_for_transport=1,
        ),
        make_row(
            ANALYZER.GENERATOR_FIELDS,
            run=0,
            event=1,
            bcid=1,
            subevent=0,
            index=0,
            pdg=-211,
            status=1,
            is_final=1,
            is_visible=1,
            energy_gev=2.0,
            accepted_for_transport=1,
        ),
    ]

    metadata = [
        make_row(
            ANALYZER.METADATA_FIELDS,
            schema_version=2,
            project_version="synthetic",
            git_commit="deadbeef",
            git_describe="synthetic",
            root_version=str(ROOT.gROOT.GetVersion()),
            geant4_version="synthetic",
            pythia_version="synthetic",
            run=0,
            events=2,
            first_bcid=0,
            threads=threads,
            seed_base=9512,
            geant4_master_seed=9512,
            pythia_seed_base=9512,
            pythia_worker_seed_stride=104729,
            pythia_seed_max=900000000,
            interaction_mode="poisson",
            mean_interactions=1.0,
            fixed_interactions=1,
            pythia_config="pythia_minbias.cmnd",
            physics_list="FTFP_BERT_ATL",
            production_cut_mm=1.0,
            max_abs_eta=1.8,
            generator_mode="pythia",
        )
    ]

    if reverse:
        events.reverse()
        hits.reverse()
        generator.reverse()

    root_file = ROOT.TFile(str(path), "RECREATE")
    write_tree(root_file, "events", ANALYZER.EVENT_FIELDS, events)
    write_tree(root_file, "hits", ANALYZER.HIT_FIELDS, hits)
    write_tree(root_file, "generator", ANALYZER.GENERATOR_FIELDS, generator)
    write_tree(root_file, "metadata", ANALYZER.METADATA_FIELDS, metadata)
    root_file.Close()


class PerformanceReproducibilityAnalyzerTest(unittest.TestCase):
    def test_full_root_reader_extracts_all_trees(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.root"
            write_fixture(path)
            result = ANALYZER.analyze_root_file(path)

        self.assertEqual(result["trees"]["events"]["entries"], 2)
        self.assertEqual(result["trees"]["hits"]["entries"], 2)
        self.assertEqual(result["trees"]["generator"]["entries"], 2)
        self.assertEqual(result["trees"]["metadata"]["entries"], 1)
        self.assertEqual(len(result["scientific_digest"]), 64)
        self.assertEqual(len(result["metadata_digest"]), 64)

    def test_reordered_root_content_is_canonically_equal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            left = Path(temporary) / "left.root"
            right = Path(temporary) / "right.root"
            write_fixture(left)
            write_fixture(right, reverse=True)
            result = ANALYZER.compare_root_files(left, right)

        self.assertTrue(result["scientific_equal"])
        self.assertTrue(result["metadata_equal"])
        self.assertTrue(result["canonical_equal"])

    def test_scientific_difference_is_measured(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            left = Path(temporary) / "left.root"
            right = Path(temporary) / "right.root"
            write_fixture(left, energy=10.0)
            write_fixture(right, energy=11.0)
            result = ANALYZER.compare_root_files(left, right)

        self.assertFalse(result["scientific_equal"])
        self.assertTrue(result["metadata_equal"])
        self.assertEqual(result["trees"]["events"]["differing_rows"], 1)
        self.assertEqual(result["trees"]["hits"]["differing_rows"], 1)
        self.assertAlmostEqual(
            result["trees"]["events"]["max_abs_difference"],
            1.0,
        )

    def test_metadata_difference_is_separate_from_science(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            left = Path(temporary) / "left.root"
            right = Path(temporary) / "right.root"
            write_fixture(left, threads=1)
            write_fixture(right, threads=2)
            result = ANALYZER.compare_root_files(left, right)

        self.assertTrue(result["scientific_equal"])
        self.assertFalse(result["metadata_equal"])
        self.assertFalse(result["canonical_equal"])
        self.assertEqual(
            result["trees"]["metadata"]["differing_fields"],
            {"threads": 1},
        )

    def test_repeatability_and_cross_thread_exit_policies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            left = Path(temporary) / "left.root"
            same = Path(temporary) / "same.root"
            changed = Path(temporary) / "changed.root"
            write_fixture(left)
            write_fixture(same, reverse=True)
            write_fixture(changed, energy=11.0, threads=2)

            with contextlib.redirect_stdout(io.StringIO()):
                repeat_rc = ANALYZER.analyzer_main(
                    ["repeatability", str(left), str(same)]
                )
                repeat_fail_rc = ANALYZER.analyzer_main(
                    ["repeatability", str(left), str(changed)]
                )
                cross_rc = ANALYZER.analyzer_main(
                    ["cross-thread", str(left), str(changed)]
                )

        self.assertEqual(repeat_rc, 0)
        self.assertEqual(repeat_fail_rc, 2)
        self.assertEqual(cross_rc, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
