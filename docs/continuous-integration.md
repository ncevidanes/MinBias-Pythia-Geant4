# Continuous integration

The repository uses a deliberately lightweight continuous-integration
layer for fast regression detection on GitHub-hosted runners.

## Lightweight CI scope

The lightweight suite validates code paths that do not require the
full High-Energy Physics software stack.

It contains:

- seven standalone C++17 regression-test executables;
- thirteen Python regression-test files;
- deterministic seed-policy and auxiliary RNG checks;
- configuration, segmentation, single-particle kinematics and
  single-particle analysis checks;
- campaign, preflight, aggregation and reproducibility support logic.

The lightweight suite is configured independently through
`ci/lightweight/CMakeLists.txt`.

## What lightweight CI does not validate

The GitHub Actions workflow does not install or execute:

- PYTHIA 8;
- Geant4;
- ROOT;
- full detector transport;
- production Monte Carlo campaigns;
- performance or scientific reproducibility campaigns requiring the
  validated HEP runtime environment.

Those remain part of the repository's controlled scientific-validation
workflow and are not replaced by GitHub Actions.

## Rationale

The separation keeps pull-request feedback fast while preserving the
validated scientific build and runtime environment.

The main `CMakeLists.txt` remains the authoritative build definition for
the complete simulator. The lightweight CMake project exists only to
exercise dependency-independent regression tests in continuous
integration.
