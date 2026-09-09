# Cycle 12 validation record

## Identity

```text
BASELINE_COMMIT=59921058cf72ec6dafca0ad852636db00a553a7c
IMPLEMENTATION_BRANCH=cycle-12-schema4-validation-continuity
CODE_COMMIT=acb730ca7a63b4e8fb19949e8ce0bb27611c9d5d
CODE_TREE=d0701bc1745bf7a88f1030090f1eff03eaa28611
CODE_DESCRIBE=v0.1.0-55-gacb730c
EVIDENCE_COMMIT=SELF
PRECOMMIT_TRACKED_DIFF_SHA256=8fba41a6046334e2962d90dc9b19cdcd646df94c759e384e6382de2d85af8230
ROOT_SCHEMA_HEADER_SHA256=3df6f224fb3afd74a4be344e3f503220e9f559479c06e51f80714e45e5bcfc96
PYTHON_SCHEMA_CONTRACT_SHA256=9349e4ea888b998236c70530a2799dbe34d8cedb3036ad955941824e2d5db837
CPP_SCHEMA_TEST_SHA256=0150521d85cbb20f27760b6b9b43ecaf63d06cd8b5c364ff5b935f5afee28814
PYTHON_SCHEMA_TEST_SHA256=9569f0e06bec96ea40bab0d6c15d287a37aa5a2819d93aec1092d6a82e12a244
```

`CODE_COMMIT` is the clean code identity embedded in the generated ROOT.
`EVIDENCE_COMMIT=SELF` denotes the separate documentary commit containing this
record. `PRECOMMIT_TRACKED_DIFF_SHA256` identifies the reviewed tracked diff
before the code commit; new source and test files are identified separately by
their content hashes above.

## Reproduced symptom

Before the compatibility change, schema 4 fixtures in the statistical and
hadronic-tail aggregators failed with `unsupported schema version` or
`unexpected schema`. This isolates the defect to validation continuity rather
than simulation output.

## Validation matrix

| Class | Command or artifact | Expected gate |
|---|---|---|
| UNIT / REGRESSION | `tests/RootSchemaTest.cc` | schemas 2/3/4 supported, current schema 4, exact branch contracts |
| UNIT / REGRESSION | `tests/test_root_schema_contract.py` | Python policy matches the C++ version set |
| REGRESSION | schema 4 aggregator fixtures | current analyzer outputs accepted |
| STRUCTURAL | lightweight CMake/CTest project | all dependency-free tests pass |
| BUILD / REGRESSION | full project CMake/CTest | all registered tests pass |
| STRUCTURAL / REPRODUCIBILITY | `scripts/audit_root.C` on Cycle 11 schema 4 ROOT | branch, metadata and transport-seed contracts pass |
| REGRESSION | `single_particle_analyzer` on schema 4 ROOT | analysis completes without mutating input |

## Observed results

### Lightweight regression suite

Configured outside the repository in `/tmp/minbias-cycle12-lightweight` with
GCC 15.2.0 and Python 3.12.12:

```text
TESTS=25
PASSED=25
FAILED=0
TOTAL_TEST_TIME_SECONDS=1.80
RESULT=PASS
```

This includes ten standalone C++ tests and fifteen Python test files. The
schema 4 statistical and hadronic-tail fixtures both passed.

### Full scientific build and CTest

The existing Release build was reconfigured with the validated
`ambiente_fisica` dependency prefix. The correct run explicitly provided the
PYTHIA 8.312 XML directory:

```text
PYTHIA8DATA=/home/nelsonassis/miniforge3/envs/ambiente_fisica/share/Pythia8/xmldoc
TESTS=30
PASSED=30
FAILED=0
TOTAL_TEST_TIME_SECONDS=151.50
RESULT=PASS
```

An earlier invocation without complete environment activation was discarded:
it either failed HDF5 discovery or let `pythia_reseed` see XML version 0.000.
That environmental failure is not used as evidence for any gate.

### ROOT auditor

With ROOT 6.36.06 and the Conda compiler sysroot activated:

```text
INPUT=outputs/cycle12-schema4-validation-continuity/clean-provenance-acb730c.root
EXPECTED_COMMIT=acb730ca7a63b4e8fb19949e8ce0bb27611c9d5d
ROOT_SHA256=112b55a7988d32fa2badecd3f679aebdb12bee1d110b3695ceac880dc2d7df9b
MANIFEST_SHA256=64d873e1c08dfd5738a30f47531441a891ea1dd6e16d096015535fba89ee66c5
AUDIT_RESULT=PASS schema=4 events=1 hits=138 generator=1

INPUT=outputs/cycle11-canonical-provenance/provenance-d5e708c.root
AUDIT_RESULT=PASS schema=4 events=1 hits=0 generator=0

INPUT=outputs/cycle6-stage63a/single_particle_schema2.root
AUDIT_RESULT=PASS schema=2 events=3 hits=453 generator=3
```

The Cycle 12 artifact was produced after reconfiguration from a tracked-clean
`CODE_COMMIT`; `audit_root.C` compared `metadata.git_commit` to the full SHA and
accepted `metadata.git_describe` without `dirty`. The historical Cycle 11
schema 3 pilot reached only its pre-existing dirty-provenance rejection; no
schema, branch, seed-policy or accounting failure was reported.

### Single-particle analyzer

```text
SCHEMA=2
INPUT_SHA256_BEFORE=1e60ef1ac58872ffda4b181f0cd762cdf5d49dd33af5919e643ec4e4e13533f8
ANALYSIS_RESULT=PASS
INPUT_SHA256_AFTER=1e60ef1ac58872ffda4b181f0cd762cdf5d49dd33af5919e643ec4e4e13533f8

SCHEMA=4
INPUT=outputs/cycle12-schema4-validation-continuity/clean-provenance-acb730c.root
EVENTS=1
HITS=138
INPUT_SHA256_BEFORE=112b55a7988d32fa2badecd3f679aebdb12bee1d110b3695ceac880dc2d7df9b
ANALYSIS_RUN_A=PASS
ANALYSIS_RUN_B=PASS
ANALYZER_REPEATABILITY=PASS
SUMMARY_SHA256=416f3eecc249f3cb458a077337b30da564de33f89f67de574991e27771f6669c
SAMPLINGS_SHA256=ae0ed5066c8e6bf359521ef9b13bc595afc916acc4de8d81f9295780c3014d2c
INPUT_SHA256_AFTER=112b55a7988d32fa2badecd3f679aebdb12bee1d110b3695ceac880dc2d7df9b
```

The schema 4 smoke used the unchanged `config/single_particle.conf` physics
configuration with one event and one thread. Its purpose was compatibility and
I/O validation, not a new physics conclusion.

## Conclusion and gates

```text
CYCLE_12_CODE_GATE=PASS
CYCLE_12_TEST_GATE=PASS
CYCLE_12_PHYSICS_GATE=PASS
CYCLE_12_REGRESSION_GATE=PASS
CYCLE_12_REPRODUCIBILITY_GATE=PASS
CYCLE_12_DOCUMENTATION_GATE=PASS
CYCLE_12_EVIDENCE_GATE=PASS
CYCLE_12_FINAL_GATE=PASS
```

The raw evidence summary is preserved in
`evidence/clean-provenance-acb730c.txt`. The ROOT and derived CSV artifacts are
kept under the ignored `outputs/cycle12-schema4-validation-continuity/`
directory and are identified by the checksums above.
