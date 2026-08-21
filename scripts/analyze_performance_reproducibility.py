#!/usr/bin/env python3
"""Canonical ROOT analysis for Cycle 9 reproducibility studies."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EVENT_FIELDS = (
    "run",
    "event",
    "bcid",
    "mu_configured",
    "n_interactions_requested",
    "n_interactions_generated",
    "generation_failures",
    "generator_particles",
    "transported_particles",
    "unknown_pdg_particles",
    "total_edep_mev",
    "rejected_not_final",
    "rejected_neutrino_disabled",
    "rejected_invisible_non_neutrino",
    "rejected_outside_eta_acceptance",
    "unlineaged_steps",
    "segmentation_failures",
)

HIT_FIELDS = (
    "run",
    "event",
    "bcid",
    "subevent",
    "cell_id",
    "subdetector",
    "sampling",
    "side",
    "eta_index",
    "phi_index",
    "eta_center",
    "phi_center",
    "edep_mev",
    "time_mean_ns",
    "time_first_ns",
    "leading_pdg",
    "leading_track_id",
    "leading_parent_id",
    "steps",
)

GENERATOR_FIELDS = (
    "run",
    "event",
    "bcid",
    "subevent",
    "index",
    "pdg",
    "status",
    "mother1",
    "mother2",
    "daughter1",
    "daughter2",
    "is_final",
    "is_visible",
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
    "accepted_for_transport",
    "rejection_code",
)

METADATA_EXCLUDED_FIELDS = {
    "output_file",
    "normalized_config",
}


class AnalysisError(RuntimeError):
    """Controlled Cycle 9 canonical-analysis failure."""


def canonical_scalar(value: Any) -> tuple[str, Any]:
    if isinstance(value, bool):
        return ("i", int(value))
    if isinstance(value, int):
        return ("i", value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AnalysisError(f"non-finite floating-point value: {value!r}")
        return ("f", value.hex())
    if isinstance(value, str):
        return ("s", value)
    try:
        integer = int(value)
        if value == integer:
            return ("i", integer)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        floating = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise AnalysisError(f"unsupported scalar value: {value!r}") from error
    if not math.isfinite(floating):
        raise AnalysisError(f"non-finite floating-point value: {floating!r}")
    return ("f", floating.hex())


def canonical_row(row: Mapping[str, Any], fields: Sequence[str]) -> str:
    missing = [field for field in fields if field not in row]
    if missing:
        raise AnalysisError("missing fields: " + ",".join(missing))
    payload = [
        [field, *canonical_scalar(row[field])]
        for field in fields
    ]
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def canonical_lines(
    rows: Iterable[Mapping[str, Any]],
    fields: Sequence[str],
) -> tuple[str, ...]:
    return tuple(sorted(canonical_row(row, fields) for row in rows))


def digest_lines(lines: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def digest_rows(
    rows: Iterable[Mapping[str, Any]],
    fields: Sequence[str],
) -> str:
    return digest_lines(canonical_lines(rows, fields))


METADATA_FIELDS = (
    "schema_version",
    "project_version",
    "git_commit",
    "git_describe",
    "root_version",
    "geant4_version",
    "pythia_version",
    "run",
    "events",
    "first_bcid",
    "threads",
    "seed_base",
    "geant4_master_seed",
    "pythia_seed_base",
    "pythia_worker_seed_stride",
    "pythia_seed_max",
    "interaction_mode",
    "mean_interactions",
    "fixed_interactions",
    "pythia_config",
    "physics_list",
    "production_cut_mm",
    "beam_sigma_x_mm",
    "beam_sigma_y_mm",
    "beam_sigma_z_mm",
    "beam_sigma_t_ns",
    "max_abs_eta",
    "transport_neutrinos",
    "generator_audit",
    "check_overlaps",
    "print_every",
    "config_file",
    "generator_mode",
    "single_particle_pdg",
    "single_particle_kinetic_energy_gev",
    "single_particle_eta",
    "single_particle_phi",
)

TREE_FIELDS = {
    "events": EVENT_FIELDS,
    "hits": HIT_FIELDS,
    "generator": GENERATOR_FIELDS,
    "metadata": METADATA_FIELDS,
}

INTEGER_LEAF_TYPES = {
    "Bool_t",
    "Char_t",
    "UChar_t",
    "Short_t",
    "UShort_t",
    "Int_t",
    "UInt_t",
    "Long_t",
    "ULong_t",
    "Long64_t",
    "ULong64_t",
}

FLOAT_LEAF_TYPES = {
    "Float_t",
    "Double_t",
    "Float16_t",
    "Double32_t",
}


def import_root() -> Any:
    try:
        import ROOT
    except ImportError as error:
        raise AnalysisError("PyROOT is unavailable") from error
    ROOT.gROOT.SetBatch(True)
    return ROOT


def branch_names(tree: Any) -> tuple[str, ...]:
    branches = tree.GetListOfBranches()
    if branches is None:
        raise AnalysisError(f"tree {tree.GetName()} has no branch list")
    return tuple(
        str(branches.At(index).GetName())
        for index in range(branches.GetEntries())
    )


def validate_tree_schema(
    tree: Any,
    tree_name: str,
    fields: Sequence[str],
) -> None:
    available = set(branch_names(tree))
    missing = sorted(set(fields) - available)
    if missing:
        raise AnalysisError(
            f"{tree_name}: missing branches: " + ",".join(missing)
        )


def read_branch_scalar(tree: Any, field: str) -> Any:
    branch = tree.GetBranch(field)
    if branch is None:
        raise AnalysisError(f"{tree.GetName()}: missing branch {field}")

    leaf = branch.GetLeaf(field)
    if leaf is not None:
        type_name = str(leaf.GetTypeName())
        if "string" in type_name.lower():
            return str(getattr(tree, field))
        value = leaf.GetValue()
        if type_name in INTEGER_LEAF_TYPES:
            return int(value)
        if type_name in FLOAT_LEAF_TYPES:
            return float(value)
        raise AnalysisError(
            f"{tree.GetName()}.{field}: unsupported leaf type {type_name}"
        )

    class_name = str(branch.GetClassName())
    value = getattr(tree, field)
    if "string" in class_name.lower():
        return str(value)

    raise AnalysisError(
        f"{tree.GetName()}.{field}: unsupported branch class {class_name!r}"
    )


def extract_tree_rows(
    tree: Any,
    fields: Sequence[str],
) -> list[dict[str, Any]]:
    validate_tree_schema(tree, str(tree.GetName()), fields)
    rows: list[dict[str, Any]] = []
    entries = int(tree.GetEntries())
    for entry in range(entries):
        if tree.GetEntry(entry) <= 0:
            raise AnalysisError(
                f"{tree.GetName()}: failed to read entry {entry}"
            )
        rows.append({
            field: read_branch_scalar(tree, field)
            for field in fields
        })
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def analyze_root_file(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise AnalysisError(f"ROOT file does not exist: {path}")

    ROOT = import_root()
    root_file = ROOT.TFile.Open(str(path), "READ")
    if not root_file or root_file.IsZombie():
        raise AnalysisError(f"cannot open ROOT file: {path}")

    try:
        result: dict[str, Any] = {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "trees": {},
        }

        for tree_name, fields in TREE_FIELDS.items():
            tree = root_file.Get(tree_name)
            if tree is None:
                raise AnalysisError(f"missing TTree: {tree_name}")
            rows = extract_tree_rows(tree, fields)
            lines = canonical_lines(rows, fields)
            result["trees"][tree_name] = {
                "entries": len(rows),
                "digest": digest_lines(lines),
            }

        scientific = hashlib.sha256()
        for tree_name in ("events", "hits", "generator"):
            scientific.update(tree_name.encode("utf-8"))
            scientific.update(b":")
            scientific.update(
                result["trees"][tree_name]["digest"].encode("ascii")
            )
            scientific.update(b"\n")

        result["scientific_digest"] = scientific.hexdigest()
        result["metadata_digest"] = result["trees"]["metadata"]["digest"]
        return result
    finally:
        root_file.Close()


TREE_KEYS = {
    "events": ("run", "event", "bcid"),
    "hits": ("run", "event", "bcid", "subevent", "cell_id"),
    "generator": ("run", "event", "bcid", "subevent", "index"),
    "metadata": (),
}


def canonical_key(
    row: Mapping[str, Any],
    key_fields: Sequence[str],
) -> tuple[tuple[str, Any], ...]:
    missing = [field for field in key_fields if field not in row]
    if missing:
        raise AnalysisError("missing key fields: " + ",".join(missing))
    return tuple(canonical_scalar(row[field]) for field in key_fields)


def index_rows_by_key(
    rows: Sequence[Mapping[str, Any]],
    key_fields: Sequence[str],
    tree_name: str,
) -> dict[tuple[Any, ...], Mapping[str, Any]]:
    if not key_fields:
        if len(rows) != 1:
            raise AnalysisError(
                f"{tree_name}: expected exactly one metadata row, found {len(rows)}"
            )
        return {(("__single__", 0),): rows[0]}

    indexed: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for row in rows:
        key = canonical_key(row, key_fields)
        if key in indexed:
            raise AnalysisError(
                f"{tree_name}: duplicate canonical key {key!r}"
            )
        indexed[key] = row
    return indexed


def relative_difference(left: float, right: float) -> float:
    absolute = abs(left - right)
    scale = max(abs(left), abs(right))
    return 0.0 if scale == 0.0 else absolute / scale


def compare_tree_rows(
    left_rows: Sequence[Mapping[str, Any]],
    right_rows: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
    key_fields: Sequence[str],
    tree_name: str,
) -> dict[str, Any]:
    left_index = index_rows_by_key(left_rows, key_fields, tree_name)
    right_index = index_rows_by_key(right_rows, key_fields, tree_name)

    left_keys = set(left_index)
    right_keys = set(right_index)
    only_left = sorted(left_keys - right_keys, key=repr)
    only_right = sorted(right_keys - left_keys, key=repr)
    common = sorted(left_keys & right_keys, key=repr)

    differing_rows = 0
    differing_values = 0
    differing_fields: dict[str, int] = {}
    max_abs_difference = 0.0
    max_rel_difference = 0.0
    max_abs_field: str | None = None
    max_rel_field: str | None = None

    for key in common:
        left_row = left_index[key]
        right_row = right_index[key]
        row_differs = False

        for field in fields:
            left_value = canonical_scalar(left_row[field])
            right_value = canonical_scalar(right_row[field])

            if left_value == right_value:
                continue

            row_differs = True
            differing_values += 1
            differing_fields[field] = differing_fields.get(field, 0) + 1

            if left_value[0] == "f" and right_value[0] == "f":
                left_float = float.fromhex(left_value[1])
                right_float = float.fromhex(right_value[1])
                absolute = abs(left_float - right_float)
                relative = relative_difference(left_float, right_float)

                if absolute > max_abs_difference:
                    max_abs_difference = absolute
                    max_abs_field = field
                if relative > max_rel_difference:
                    max_rel_difference = relative
                    max_rel_field = field

        if row_differs:
            differing_rows += 1

    equal = (
        not only_left
        and not only_right
        and differing_values == 0
    )

    return {
        "tree": tree_name,
        "equal": equal,
        "left_entries": len(left_rows),
        "right_entries": len(right_rows),
        "only_left_keys": len(only_left),
        "only_right_keys": len(only_right),
        "first_only_left_key": repr(only_left[0]) if only_left else None,
        "first_only_right_key": repr(only_right[0]) if only_right else None,
        "differing_rows": differing_rows,
        "differing_values": differing_values,
        "differing_fields": dict(sorted(differing_fields.items())),
        "max_abs_difference": max_abs_difference,
        "max_abs_field": max_abs_field,
        "max_rel_difference": max_rel_difference,
        "max_rel_field": max_rel_field,
    }


SCIENTIFIC_TREES = ("events", "hits", "generator")


def combine_tree_digests(
    digests: Mapping[str, str],
    tree_names: Sequence[str],
) -> str:
    combined = hashlib.sha256()
    for tree_name in tree_names:
        if tree_name not in digests:
            raise AnalysisError(f"missing tree digest: {tree_name}")
        combined.update(tree_name.encode("utf-8"))
        combined.update(b":")
        combined.update(digests[tree_name].encode("ascii"))
        combined.update(b"\n")
    return combined.hexdigest()


def extract_root_content(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise AnalysisError(f"ROOT file does not exist: {path}")

    ROOT = import_root()
    root_file = ROOT.TFile.Open(str(path), "READ")
    if not root_file or root_file.IsZombie():
        raise AnalysisError(f"cannot open ROOT file: {path}")

    try:
        rows_by_tree: dict[str, list[dict[str, Any]]] = {}
        digests: dict[str, str] = {}

        for tree_name, fields in TREE_FIELDS.items():
            tree = root_file.Get(tree_name)
            if tree is None:
                raise AnalysisError(f"{path}: missing TTree {tree_name}")

            rows = extract_tree_rows(tree, fields)
            rows_by_tree[tree_name] = rows
            digests[tree_name] = digest_rows(rows, fields)

        return {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "rows": rows_by_tree,
            "tree_digests": digests,
            "scientific_digest": combine_tree_digests(
                digests,
                SCIENTIFIC_TREES,
            ),
            "metadata_digest": digests["metadata"],
        }
    finally:
        root_file.Close()


def compare_root_files(left_path: Path, right_path: Path) -> dict[str, Any]:
    left = extract_root_content(left_path)
    right = extract_root_content(right_path)

    tree_results: dict[str, dict[str, Any]] = {}

    for tree_name, fields in TREE_FIELDS.items():
        comparison = compare_tree_rows(
            left["rows"][tree_name],
            right["rows"][tree_name],
            fields,
            TREE_KEYS[tree_name],
            tree_name,
        )

        left_digest = left["tree_digests"][tree_name]
        right_digest = right["tree_digests"][tree_name]

        comparison["left_digest"] = left_digest
        comparison["right_digest"] = right_digest
        comparison["digest_equal"] = left_digest == right_digest

        tree_results[tree_name] = comparison

    scientific_equal = all(
        tree_results[name]["equal"]
        for name in SCIENTIFIC_TREES
    )

    metadata_equal = tree_results["metadata"]["equal"]

    return {
        "left_path": left["path"],
        "right_path": right["path"],
        "left_size_bytes": left["size_bytes"],
        "right_size_bytes": right["size_bytes"],
        "left_sha256": left["sha256"],
        "right_sha256": right["sha256"],
        "raw_sha256_equal": left["sha256"] == right["sha256"],
        "left_scientific_digest": left["scientific_digest"],
        "right_scientific_digest": right["scientific_digest"],
        "scientific_digest_equal": (
            left["scientific_digest"] == right["scientific_digest"]
        ),
        "left_metadata_digest": left["metadata_digest"],
        "right_metadata_digest": right["metadata_digest"],
        "metadata_digest_equal": (
            left["metadata_digest"] == right["metadata_digest"]
        ),
        "scientific_equal": scientific_equal,
        "metadata_equal": metadata_equal,
        "canonical_equal": scientific_equal and metadata_equal,
        "trees": tree_results,
    }


def yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def evaluate_comparison(
    mode: str,
    comparison: Mapping[str, Any],
) -> dict[str, Any]:
    if mode == "repeatability":
        accepted = bool(comparison["canonical_equal"])
        return {
            "mode": mode,
            "accepted": accepted,
            "classification": "PASS" if accepted else "FAIL",
            "scientific_equal": bool(comparison["scientific_equal"]),
            "metadata_equal": bool(comparison["metadata_equal"]),
            "raw_sha256_equal": bool(comparison["raw_sha256_equal"]),
        }

    if mode == "cross-thread":
        scientific_equal = bool(comparison["scientific_equal"])
        return {
            "mode": mode,
            "accepted": True,
            "classification": (
                "IDENTICAL"
                if scientific_equal
                else "MEASURED_DIFFERENCE"
            ),
            "scientific_equal": scientific_equal,
            "metadata_equal": bool(comparison["metadata_equal"]),
            "raw_sha256_equal": bool(comparison["raw_sha256_equal"]),
        }

    raise AnalysisError(f"unsupported comparison mode: {mode}")


def inspection_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    trees = result["trees"]
    return {
        "path": result["path"],
        "size_bytes": result["size_bytes"],
        "sha256": result["sha256"],
        "scientific_digest": result["scientific_digest"],
        "metadata_digest": result["metadata_digest"],
        "tree_entries": {
            name: int(values["entries"])
            for name, values in trees.items()
        },
        "tree_digests": {
            name: str(values["digest"])
            for name, values in trees.items()
        },
    }


def print_inspection(result: Mapping[str, Any]) -> None:
    summary = inspection_summary(result)
    print("CYCLE_9_ANALYSIS_MODE=inspect")
    print("ROOT_INSPECTION=PASS")
    print("ROOT_PATH=" + summary["path"])
    print("ROOT_SIZE_BYTES=" + str(summary["size_bytes"]))
    print("ROOT_SHA256=" + summary["sha256"])
    print("SCIENTIFIC_DIGEST=" + summary["scientific_digest"])
    print("METADATA_DIGEST=" + summary["metadata_digest"])
    for tree_name in ("events", "hits", "generator", "metadata"):
        print(
            "TREE_ENTRIES_"
            + tree_name.upper()
            + "="
            + str(summary["tree_entries"][tree_name])
        )


def print_comparison(
    mode: str,
    comparison: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> None:
    print("CYCLE_9_ANALYSIS_MODE=" + mode)
    print("LEFT_ROOT=" + str(comparison["left_path"]))
    print("RIGHT_ROOT=" + str(comparison["right_path"]))
    print(
        "RAW_SHA256_EQUAL="
        + yes_no(bool(comparison["raw_sha256_equal"]))
    )
    print(
        "SCIENTIFIC_EQUAL="
        + yes_no(bool(comparison["scientific_equal"]))
    )
    print(
        "METADATA_EQUAL="
        + yes_no(bool(comparison["metadata_equal"]))
    )
    print(
        "CANONICAL_EQUAL="
        + yes_no(bool(comparison["canonical_equal"]))
    )
    print("CLASSIFICATION=" + str(evaluation["classification"]))

    for tree_name in ("events", "hits", "generator", "metadata"):
        tree = comparison["trees"][tree_name]
        print(
            "TREE_COMPARISON="
            + tree_name
            + " equal="
            + yes_no(bool(tree["equal"]))
            + " left_entries="
            + str(tree["left_entries"])
            + " right_entries="
            + str(tree["right_entries"])
            + " differing_rows="
            + str(tree["differing_rows"])
            + " differing_values="
            + str(tree["differing_values"])
            + " only_left_keys="
            + str(tree["only_left_keys"])
            + " only_right_keys="
            + str(tree["only_right_keys"])
            + " max_abs="
            + repr(tree["max_abs_difference"])
            + " max_rel="
            + repr(tree["max_rel_difference"])
        )

    if mode == "repeatability":
        print(
            "REPEATABILITY_RESULT="
            + ("PASS" if evaluation["accepted"] else "FAIL")
        )
    else:
        print(
            "CROSS_THREAD_COMPARISON=REPORT "
            + "identity="
            + str(evaluation["classification"])
        )


def parse_cli(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("inspect", "repeatability", "cross-thread"),
    )
    parser.add_argument("left", type=Path)
    parser.add_argument("right", nargs="?", type=Path)
    parser.add_argument(
        "--json",
        action="store_true",
        help="also print the machine-readable analysis object as JSON",
    )
    return parser.parse_args(argv)


def analyzer_main(argv: Sequence[str] | None = None) -> int:
    args = parse_cli(argv)

    if args.mode == "inspect":
        if args.right is not None:
            raise AnalysisError("inspect mode accepts exactly one ROOT file")
        result = analyze_root_file(args.left)
        print_inspection(result)
        if args.json:
            print(
                "ANALYSIS_JSON="
                + json.dumps(
                    inspection_summary(result),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        return 0

    if args.right is None:
        raise AnalysisError(f"{args.mode} mode requires two ROOT files")

    comparison = compare_root_files(args.left, args.right)
    evaluation = evaluate_comparison(args.mode, comparison)
    print_comparison(args.mode, comparison, evaluation)

    if args.json:
        payload = {
            "comparison": comparison,
            "evaluation": evaluation,
        }
        print(
            "ANALYSIS_JSON="
            + json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    if args.mode == "repeatability" and not evaluation["accepted"]:
        return 2

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(analyzer_main())
    except (OSError, ValueError, AnalysisError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print("CYCLE_9_CANONICAL_ANALYSIS=FAIL", file=sys.stderr)
        raise SystemExit(1)
