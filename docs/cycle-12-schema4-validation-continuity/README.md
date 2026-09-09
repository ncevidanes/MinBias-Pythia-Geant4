# Cycle 12 — ROOT schema 4 validation continuity

## Formal objective

Restore and regression-protect complete validation continuity for ROOT schema
4, preserving explicit historical schema interpretation, without changing
configuration, geometry or physics models.

## Baseline

- baseline cycle: Cycle 11, partition-stable production;
- baseline branch: `master`;
- baseline commit: `59921058cf72ec6dafca0ad852636db00a553a7c`;
- remote state after authorized fetch: `master` equals `origin/master`;
- current ROOT output contract: schema 4, with 18 `events` branches and 48
  `metadata` branches;
- pre-existing untracked audit/procedure files are outside this cycle and must
  remain preserved.

The audit found a cross-layer compatibility break: production emits schema 4,
while the generic ROOT auditor, the single-particle analyzer and four Python
campaign validation paths still required schema 2. The lightweight CI also
omitted the dependency-free Cycle 11 transport-seed tests. As a result, current
outputs could be scientifically valid yet rejected by release or campaign
validation tooling.

## Scope

The minimum sufficient change is limited to:

- a shared C++ contract for ROOT schemas 2, 3 and 4;
- a shared Python schema compatibility contract;
- schema-aware ROOT auditing, including schema 4 transport-seed metadata and
  per-event seed validation;
- schema 4 acceptance in the single-particle analyzer and campaign validators;
- regression tests and lightweight CI coverage;
- correction of active architecture and validation documentation.

Schemas 2 and 3 remain supported only through explicit historical
interpretations. Unknown older or future schemas fail closed.

## Non-goals

This cycle does not change:

- the configuration grammar or defaults;
- detector geometry, materials, segmentation or physics list;
- PYTHIA generation settings;
- Geant4 transport behavior;
- seed derivation, RNG streams or scientific event identity;
- existing ROOT data files or campaign evidence.

## Acceptance gates

- `CYCLE_12_CODE_GATE`: schema contracts are centralized and all affected
  validators consume the supported-version policy;
- `CYCLE_12_TEST_GATE`: full CTest and lightweight CI suites pass;
- `CYCLE_12_PHYSICS_GATE`: no physics/configuration source is changed;
- `CYCLE_12_REGRESSION_GATE`: current schema 4 fixtures and historical schema
  contract tests pass;
- `CYCLE_12_REPRODUCIBILITY_GATE`: the Cycle 11 seed-policy tests remain green
  and the ROOT auditor verifies the recorded transport seed;
- `CYCLE_12_DOCUMENTATION_GATE`: active documentation describes schema 4 and
  event-stable threading semantics;
- `CYCLE_12_EVIDENCE_GATE`: commands, code identity and observed results are
  recorded in `validation.md`.

The final gate cannot pass until all results in `validation.md` have been
observed on the implementation worktree.
