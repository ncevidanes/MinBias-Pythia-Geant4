# Build, test, and quality gates

This document defines the canonical software-quality verification
contracts of `PythiaGeantOneStage`.

It describes the quality mechanisms that are present and traceable in
the current repository.

Historical development checks are not promoted to permanent gates
unless the corresponding configuration or workflow remains tracked in
the repository.

## 1. Scope

The quality contract covers:

- full scientific CMake configuration and build;
- the canonical full-project CTest suite;
- project warning policy;
- invalid-input regression testing;
- dependency-light regression testing;
- `clang-format`;
- `clang-tidy`;
- code coverage;
- permanent CPU sanitizer validation;
- local pre-merge verification.

Runtime failure and output-publication behavior are documented
separately in:

```text
docs/operations/failure-contracts.md
```

## 2. Full scientific build

The complete simulator requires the scientific dependency stack used
by the main CMake project, including Geant4, Pythia 8, ROOT, and
Python.

From the repository root, a normal release-style configuration is:

```bash
cmake \
    -S . \
    -B build \
    -DCMAKE_BUILD_TYPE=Release
```

The project is built with:

```bash
cmake \
    --build build \
    --parallel 2
```

The exact parallelism value is operational rather than semantic.
It may be adjusted according to available memory and CPU resources.

A successful build is required before the full CTest suite is treated
as meaningful.

## 3. Canonical full-project CTest suite

The top-level `CMakeLists.txt` defines the canonical project test
suite.

At the baseline documented by Cycle 13.7, the expected registered
CTest count is:

```text
36
```

The suite can be enumerated without execution using:

```bash
ctest \
    --test-dir build \
    -N
```

The complete suite is executed with:

```bash
ctest \
    --test-dir build \
    --output-on-failure
```

The quality contract requires:

```text
configured tests: 36
failed tests: 0
```

The expected count is a structural regression guard.

If tests are deliberately added or removed, the expected count must
be reviewed and updated together with the corresponding quality
baseline.

A count mismatch must not be silently ignored.

## 4. Centralized compiler warning policy

Project-owned C++ targets in the full scientific build inherit the
central warning interface defined in the top-level CMake project.

For GNU-compatible, Clang, and AppleClang compilers, the policy is:

```text
-Wall
-Wextra
-Wpedantic
```

The intent is to apply the warning policy consistently to project
targets without mixing dependency-provided compiler options into the
project warning contract.

The centralized warning policy is not equivalent to a permanent
compiler `-Werror` policy.

Warnings should nevertheless be reviewed as quality defects rather
than treated as harmless output.

The independent lightweight CMake project applies the same three
warning options directly to its C++ test targets.

## 5. Negative CLI regression testing

The canonical CTest suite registers:

```text
cli_invalid_inputs
```

using:

```text
tests/test_cli_invalid_inputs.py
```

against the built `pythia_geant` executable.

This test exercises rejected command-line and configuration input
paths and verifies that invalid input does not silently become an
accepted simulation configuration.

The existence of this regression test is part of the quality
contract.

The number of semantic negative cases must be derived from the test
definition itself when auditing that suite.

A simple textual grep for words such as `invalid` or `failure` is not
a reliable case counter and must not be used as the canonical case
count.

## 6. Lightweight test project

A dependency-light CMake project is maintained under:

```text
ci/lightweight
```

It allows a substantial subset of project behavior to be tested
without configuring the full Geant4/Pythia/ROOT application.

At the Cycle 13.7 baseline it contains:

```text
C++ lightweight tests:    12
Python lightweight tests: 15
total lightweight tests:  27
```

It can be configured with:

```bash
cmake \
    -S ci/lightweight \
    -B build-lightweight \
    -DCMAKE_BUILD_TYPE=Release
```

Built with:

```bash
cmake \
    --build build-lightweight \
    --parallel 2
```

and executed with:

```bash
ctest \
    --test-dir build-lightweight \
    --output-on-failure
```

The lightweight suite complements rather than replaces the full
scientific build and its canonical 36-test CTest suite.

## 7. clang-format gate

The tracked CI quality workflow uses:

```text
clang-format-21
```

At the Cycle 13.7 baseline, the formatting gate expects exactly:

```text
54 tracked C/C++ source and header files
```

The CI invocation uses dry-run error mode:

```bash
clang-format-21 \
    --dry-run \
    --Werror \
    --style=file \
    <tracked C/C++ files>
```

Formatting is therefore a non-mutating CI check.

The tracked file-count assertion is also a regression guard. If the
C++ source inventory changes deliberately, the expected count in the
workflow must be reviewed.

## 8. clang-tidy gate

The quality workflow uses:

```text
clang-tidy-21
```

against a compile database generated from the independent lightweight
CMake project.

At the Cycle 13.7 baseline, the expected lightweight translation-unit
count is:

```text
19
```

Each selected translation unit is checked with:

```text
--warnings-as-errors='*'
```

Therefore a `clang-tidy` diagnostic promoted by the configured checks
causes the quality gate to fail.

The 19-translation-unit expectation is a structural guard and must be
reviewed if the lightweight project changes intentionally.

## 9. Permanent CPU sanitizer gate

AddressSanitizer and UndefinedBehaviorSanitizer are permanent tracked quality gates.

The top-level CMake option `PYTHIA_ENABLE_SANITIZERS` is disabled by default and enables `-fsanitize=address,undefined`, `-fno-omit-frame-pointer` and `-fno-sanitize-recover=all` for supported GNU GCC and Clang builds.

The permanent CI implementation is `.github/workflows/sanitizer-ci.yml`. It uses the controlled HEP environment and requires the canonical 36-test full-project CTest inventory.

ASan and UBSan operate in fail-fast mode. LeakSanitizer reporting is disabled because the executable links against externally built HEP libraries whose process-lifetime allocations are outside this repository ownership boundary. Address-safety checks remain enabled.

A project-owned ASan or UBSan diagnostic is a quality-gate failure.

## 10. Coverage gate

Canonical coverage configuration is stored in:

```text
ci/coverage-baseline.env
```

and executed through:

```text
scripts/run_coverage.sh
```

The tracked CI coverage workflow enables strict baseline enforcement
with:

```text
COVERAGE_ENFORCE_BASELINE=1
```

The canonical baseline identifier is:

```text
cycle-13.6F2-R1A-R1
```

The baseline expects:

```text
CTest count: 36

global lines:
  total:    1931
  executed: 932

global branches:
  total: 3822
  taken: 1232
```

The coverage baseline also records selected component-level line and
branch counts.

Coverage counts are regression evidence, not a universal statement of
test adequacy.

A changed baseline must be justified by an intentional
coverage-relevant modification rather than silently regenerated merely
to make a failing gate pass.

## 11. Coverage toolchain contract

The tracked coverage workflow validates a controlled scientific
toolchain before accepting canonical coverage.

The current CI contract includes:

```text
GCC:     14.3.0
G++:     14.3.0
gcov:    14.3.0
ROOT:    6.36.06
Pythia8: 8.312
Geant4:  11.3.2
gcovr:   8.6 baseline expectation
```

Toolchain identity matters because coverage instrumentation and branch
accounting can change across compiler and coverage-tool versions.

Coverage results produced with a materially different toolchain should
not be assumed automatically equivalent to the canonical baseline.

## 12. CI workflows

The current repository tracks three GitHub Actions workflows relevant to
this quality contract:

```text
.github/workflows/lightweight-ci.yml
.github/workflows/coverage-ci.yml
.github/workflows/sanitizer-ci.yml
```

The lightweight workflow provides:

- compiler/tool version validation;
- tracked C++ file-count validation;
- `clang-format-21`;
- lightweight compile database generation;
- `clang-tidy-21`;
- lightweight C++ and Python tests.

The coverage workflow provides:

- the full scientific coverage environment;
- scientific toolchain identity checks;
- strict canonical coverage execution;
- coverage summary reporting.

The existence of a local development check does not imply that it is a
CI gate. Only tracked workflow behavior should be described as
automatically enforced CI behavior.

## 13. Recommended local pre-merge sequence

When the full scientific dependency environment is available, the
recommended local regression sequence is:

```bash
cmake \
    -S . \
    -B build \
    -DCMAKE_BUILD_TYPE=Release

cmake \
    --build build \
    --parallel 2

ctest \
    --test-dir build \
    --output-on-failure
```

The lightweight suite can additionally be executed independently:

```bash
cmake \
    -S ci/lightweight \
    -B build-lightweight \
    -DCMAKE_BUILD_TYPE=Release

cmake \
    --build build-lightweight \
    --parallel 2

ctest \
    --test-dir build-lightweight \
    --output-on-failure
```

A developer with the matching LLVM tools can reproduce the formatting
gate over the tracked C/C++ inventory using:

```bash
mapfile -t files < <(
    git ls-files |
        grep -E '\.(c|cc|cpp|cxx|h|hh|hpp|hxx)$'
)

clang-format-21 \
    --dry-run \
    --Werror \
    --style=file \
    "${files[@]}"
```

The canonical CI workflow remains authoritative for its exact
`clang-tidy` translation-unit selection.

## 14. Failure interpretation

A quality gate failure should identify a specific violated contract.

Examples include:

```text
build failure
CTest regression
unexpected CTest inventory
compiler diagnostic
formatting drift
clang-tidy diagnostic
unexpected C++ inventory
unexpected lightweight translation-unit inventory
coverage baseline mismatch
coverage toolchain mismatch
```

A failed gate should be investigated at its cause.

Changing an expected count or baseline solely to convert a failure
into a pass is not a valid repair.

Expected values should change only when the corresponding project
change is intentional and reviewed.

## 15. Relationship between quality layers

The project uses complementary verification layers.

The full scientific suite verifies behavior in the complete dependency
environment.

The lightweight suite provides fast dependency-reduced regression
coverage.

Static analysis and formatting check source quality properties that
runtime tests do not cover.

Coverage measures exercised code structure but does not replace
correctness assertions.

Negative tests verify rejection behavior and interface robustness.

Operational failure contracts validate runtime behavior that ordinary
successful tests may not expose.

No single layer should be interpreted as replacing all others.

## 16. Baseline evolution

The numerical guards documented here correspond to the Cycle 13.7
repository baseline.

Current structural expectations are:

```text
full CTest tests:                  36
tracked C/C++ files:               54
lightweight C++ tests:             12
lightweight Python tests:          15
lightweight total tests:           27
clang-tidy translation units:      19
coverage global lines:       932/1931
coverage global branches:   1232/3822
```

These values are intentionally explicit.

When project structure changes, the appropriate procedure is:

1. explain why the structural inventory changed;
2. validate the new behavior;
3. update the corresponding tracked gate;
4. update this document in the same reviewed change.

## 17. Scope boundary

This quality contract documents engineering validation.

It does not define:

- release numbering;
- GitHub presentation;
- DOI publication;
- Zenodo deposition;
- scientific-paper submission;
- marketing or public release material.

Those activities remain outside Cycle 13.7.
