# Continuous integration

The repository uses two complementary GitHub Actions workflows:

- `lightweight-ci.yml` for fast dependency-reduced regression and
  source-quality checks;
- `coverage-ci.yml` for canonical full-stack coverage validation.

These workflows serve different purposes and must not be interpreted
as equivalent validation environments.

## Lightweight CI scope

The lightweight suite validates code paths that do not require the
full High-Energy Physics software stack.

At the Cycle 13.7 baseline it contains:

- twelve standalone C++17 regression-test executables;
- fifteen Python regression-test files;
- twenty-seven registered lightweight tests in total;
- deterministic seed-policy and auxiliary RNG checks;
- current and historical ROOT schema-contract checks;
- configuration, segmentation, output-transaction, interruption,
  single-particle kinematics and single-particle analysis checks;
- campaign, preflight, aggregation and reproducibility support logic.

The lightweight suite is configured independently through
`ci/lightweight/CMakeLists.txt`.

## Lightweight source-quality gates

The tracked lightweight workflow also performs source-quality checks.

At the Cycle 13.7 baseline it validates:

- `clang-format-21` over exactly 54 tracked C/C++ source and header
  files;
- `clang-tidy-21` over exactly 19 lightweight translation units;
- all selected `clang-tidy` diagnostics with
  `--warnings-as-errors='*'`.

The file and translation-unit counts are structural regression guards.
They must be reviewed when the corresponding source inventory changes
intentionally.

## What Lightweight CI does not validate

The lightweight workflow does not install or execute:

- PYTHIA 8;
- Geant4;
- ROOT;
- full detector transport;
- production Monte Carlo campaigns;
- full scientific coverage instrumentation.

It complements rather than replaces the complete scientific build and
the canonical top-level CTest suite.

## Coverage CI

Full-stack coverage is handled by the separate tracked workflow:

```text
.github/workflows/coverage-ci.yml
```

That workflow creates a controlled HEP software environment and
validates the scientific toolchain before executing canonical
coverage.

The current validated toolchain includes:

```text
GCC:     14.3.0
G++:     14.3.0
gcov:    14.3.0
ROOT:    6.36.06
Pythia8: 8.312
Geant4:  11.3.2
```

Coverage execution uses:

```text
COVERAGE_ENFORCE_BASELINE=1
```

and delegates the canonical run to:

```text
scripts/run_coverage.sh
```

The coverage baseline expects the complete 36-test top-level CTest
inventory.

## Canonical quality contracts

The detailed engineering contract for build, tests, warnings,
formatting, static analysis, sanitizer status and coverage is:

```text
docs/operations/quality-gates.md
```

Runtime failure, signal handling, transactional output publication and
manual recovery are documented separately in:

```text
docs/operations/failure-contracts.md
```

AddressSanitizer and UndefinedBehaviorSanitizer are not currently
tracked permanent CI gates. Historical sanitizer validation must not be
described as automatically enforced repository behavior.

## Rationale

The lightweight workflow keeps ordinary pull-request feedback fast and
dependency-reduced.

The coverage workflow supplies a controlled full scientific environment
when coverage-relevant files change or when the workflow is invoked
explicitly.

The main `CMakeLists.txt` remains the authoritative build and test
definition for the complete simulator. The lightweight CMake project
exists to exercise dependency-independent regression paths and provide
a compile database for lightweight static analysis.

The different verification layers are complementary and no individual
workflow replaces the complete engineering validation contract.
