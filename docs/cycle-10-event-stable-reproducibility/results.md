# Cycle 10 — Event-stable reproducibility results

## 1. Final status

**Cycle 10 result: PASS.**

The Cycle 10 event-stable seed policy makes the canonical scientific
realization independent of whether the simulator is executed with one
or two Geant4 worker threads for the contracted validation domain.

The validated scientific-production commit is:

    cc05be4c9a8636ad7588b7598309e91e2f8f6fb2

The documentation commit intentionally postdates the production
commit. All published production artifacts described below remain
anchored to `cc05be4c9a8636ad7588b7598309e91e2f8f6fb2`.

## 2. Seed-policy result

Cycle 10 replaces worker-dependent primary-generation random streams
with the frozen policy:

    seed_policy = event-stable-v1
    seed_identity = bcid
    seed_mixer = splitmix64-v1
    pythia_reseed_scope = subevent

Scientific random streams are derived from:

    (seed_base, bcid, subevent, stream_id)

Worker identity is not part of the scientific seed tuple.

The implementation retains thread-local PYTHIA instances, but worker
initialization and per-subevent generation are derived from stable
identifiers rather than scheduling or worker identity.

The ROOT metadata schema records the new policy explicitly and no
longer presents the old worker-seed-stride semantics as active.

## 3. Regression and short-validation evidence

The final regression suite before production passed:

    23/23 tests PASS

The validation sequence covered:

- stable SplitMix64 known vectors and tuple composition;
- deterministic and bounded PYTHIA seed mapping;
- operational-domain collision checks;
- stable event-level interaction-count random streams;
- stable per-coordinate collision-vertex streams;
- worker-independent PYTHIA initialization;
- per-subevent PYTHIA reseeding;
- schema-aware ROOT metadata interpretation;
- fixed-interaction cross-thread validation;
- Poisson interaction sampling with nonzero beam smearing;
- cross-thread comparison with generator audit enabled.

The Poisson plus nonzero-smearing validation produced exact canonical
scientific equality across all four 1T/2T executions, including
`events`, `hits`, and `generator`.

Its common scientific digest was:

    8bbafec9cdbcdb1493249f63b2058060678d019cc36be0491aedf1616b606621

These short gates were completed before the performance campaign.

## 4. Production performance/reproducibility campaign

The final production evidence is stored locally under:

    outputs/cycle10-stage104a-performance-cc05be4/

The campaign contained ten sequential simulator processes:

- four reproducibility runs with 100 events;
- six performance runs with 200 events;
- one- and two-thread configurations;
- `seed_base = 9512`;
- `mean_interactions = 1`.

All ten runs passed the computational validation contract.

The transactional campaign was published atomically only after all
runs and the final schema-aware reproducibility analysis passed.

### 4.1 Reproducibility runs

| Run | Threads | Events | Wall time (s) | Max RSS (kB) |
|---|---:|---:|---:|---:|
| repro-t1-r1 | 1 | 100 | 185.86 | 164800 |
| repro-t1-r2 | 1 | 100 | 189.53 | 164816 |
| repro-t2-r1 | 2 | 100 | 115.64 | 189336 |
| repro-t2-r2 | 2 | 100 | 116.41 | 189688 |

All four runs have exactly the same canonical scientific digest:

    503ac390bd8a7a8d2ea2fd942b096d1214890c59cf37dfd765f731f2cd95f539

Final classifications:

    one-thread repeatability = PASS
    two-thread repeatability = PASS
    two-thread exact repeatability = YES
    cross-thread repetition 1 = IDENTICAL
    cross-thread repetition 2 = IDENTICAL
    acceptance policy = SCHEMA_AWARE_EVENT_STABLE_GATE

The allowed operational metadata differences do not enter the
scientific identity gate.

### 4.2 Performance runs

| Run | Threads | Events | Wall time (s) | Max RSS (kB) |
|---|---:|---:|---:|---:|
| perf-t1-r1 | 1 | 200 | 288.86 | 166228 |
| perf-t2-r1 | 2 | 200 | 191.98 | 195020 |
| perf-t1-r2 | 1 | 200 | 298.32 | 166008 |
| perf-t2-r2 | 2 | 200 | 191.20 | 195124 |
| perf-t1-r3 | 1 | 200 | 342.46 | 165672 |
| perf-t2-r3 | 2 | 200 | 186.59 | 195360 |

All six performance runs also have exactly the same canonical
scientific digest:

    2155bdff11558285fccf7d7c3ad54206017914b0a225d64e36bf823082722555

This is stronger than the minimum performance contract because the
benchmark repetitions themselves reproduce the same scientific
realization across both thread counts.

## 5. Performance result

| Metric | 1 thread | 2 threads |
|---|---:|---:|
| Minimum wall time (s) | 288.860 | 186.590 |
| Maximum wall time (s) | 342.460 | 191.980 |
| Mean wall time (s) | 309.880 | 189.923 |
| Median wall time (s) | 298.320 | 191.200 |
| Sample standard deviation (s) | 28.609 | 2.913 |
| Coefficient of variation | 9.232% | 1.534% |

Derived metrics:

    two-thread speedup = 1.560251x
    parallel efficiency = 78.013%
    median wall-time reduction = 35.908%
    throughput gain = 56.025%

No performance-stability warning was emitted. Both coefficients of
variation remain below the contracted 20% warning threshold.

Two threads therefore remain beneficial on the reference machine for
this tested workload, while exact scientific event identity is
preserved.

## 6. Comparison with Cycle 9

Cycle 9 reported:

    1T median wall time = 262.630 s
    2T median wall time = 152.940 s
    two-thread speedup = 1.717209x
    parallel efficiency = 85.860%

Cycle 10 reports:

    1T median wall time = 298.320 s
    2T median wall time = 191.200 s
    two-thread speedup = 1.560251x
    parallel efficiency = 78.013%

Relative to the Cycle 9 measurements, the observed Cycle 10 medians
are approximately:

    +13.589% for 1T
    +25.016% for 2T

The observed two-thread speedup is approximately 9.140% lower, and
parallel efficiency is lower by approximately 7.847 percentage points.

These differences are reported rather than hidden, as required by the
Cycle 10 contract.

They must not be interpreted as a pure isolated measurement of the
computational cost of one specific reseeding instruction. Cycle 9 and
Cycle 10 use different scientific random-stream policies, and Cycle 9
did not preserve the same physical realization across thread counts.
The numbers characterize the complete validated implementations on
the reference machine.

## 7. Seed-base sensitivity

The final seed-sensitivity evidence is stored locally under:

    outputs/cycle10-stage104b-seed-sensitivity-cc05be4/

Two 20-event, one-thread runs were executed with the same physical
configuration and different root seeds:

    seed A = 9512
    seed B = 9513

Both runs passed computational validation.

Scientific digests:

    seed 9512:
    8116fe2a083a1d07ade902c47ef7714c44e6ed54da66ca0d05512e3bdc830a10

    seed 9513:
    c1eba314d9478941ac8fa4afbd4b82f1f3e79cf80a3d06fe19b5f86c9aba2afa

The scientific digests are different.

Tree-level result:

    events digest equal = NO
    hits digest equal = NO
    generator digest equal = YES

The generator tree is empty in this production configuration because
generator audit is disabled, so its unchanged empty digest does not
invalidate the sensitivity test.

The only metadata differences were:

    seed_base
    geant4_master_seed
    pythia_initialization_seed
    output_file
    normalized_config

No unexpected metadata difference was observed.

Therefore changing `seed_base` changes the scientific realization
without changing unrelated physics/configuration metadata.

Seed-base sensitivity result:

    PASS

## 8. PYTHIA diagnostics

The Cycle 10.4A production logs contained:

    21 PYTHIA Warning lines
    6 PYTHIA Error lines

These messages are retained as diagnostic evidence and are not
silently discarded.

All affected simulator processes nevertheless exited successfully and
passed the computational validation gates, including interaction
accounting, finite/nonnegative energy checks, event-hit energy
closure, orphan-hit checks, lineage checks, segmentation checks and
metadata validation.

The diagnostic messages therefore do not constitute a failed Cycle 10
acceptance gate in the validated campaign.

## 9. Final acceptance matrix

| Requirement | Result |
|---|---|
| Repository regression tests | PASS |
| Same-thread exact repeatability | PASS |
| 1T/2T canonical `events` equality | PASS |
| 1T/2T canonical `hits` equality | PASS |
| 1T/2T canonical `generator` equality | PASS |
| Schema-aware metadata policy | PASS |
| Poisson interaction stability | PASS |
| Nonzero vertex-smearing stability | PASS |
| Generator-audit cross-thread comparison | PASS |
| Seed-base sensitivity | PASS |
| Worker-independent scientific seed derivation | PASS |
| Event-stable policy recorded in ROOT metadata | PASS |
| Performance measured without cherry-picking | PASS |
| Independent artifact/hash/statistics audit | PASS |

**Final Cycle 10 acceptance: PASS.**

## 10. Engineering conclusion

Cycle 10 resolves the principal reproducibility limitation documented
in Cycle 9.

For the same seed base, BCID range and physical configuration, changing
the Geant4 worker count from one to two no longer changes the canonical
minimum-bias realization.

The `--threads` option now changes execution parallelism without
changing the validated scientific event content.

At the same time, the root seed remains scientifically active:
changing `seed_base` changes the resulting realization.

The final 200-event performance campaign shows a two-thread speedup of
1.560251x with 78.013% parallel efficiency on the reference machine.

Correctness and reproducibility were prioritized over preserving the
Cycle 9 timing result.

## 11. Scope and limitations

Cycle 10 establishes exact reproducibility for the tested software
environment and contracted one-/two-thread validation domain.

It does not claim:

- bitwise reproducibility across compilers or standard libraries;
- bitwise reproducibility across PYTHIA or Geant4 versions;
- GPU reproducibility;
- scaling behavior beyond the tested worker counts;
- arbitrary multi-process repartitioning equivalence;
- official ATLAS detector or performance results.

The results characterize the simplified ATLAS/Lorenzetti-like
minimum-bias simulator implemented in this repository.
