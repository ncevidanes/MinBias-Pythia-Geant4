# Cycle 9 — Performance, parallelism, and reproducibility results

## 1. Campaign status

- Git commit: `70c1cc4dcec692ae8901ade5ccc105f9fba34f32`
- Branch: `cycle-9-performance-reproducibility`
- Executed runs: 10
- Execution policy: sequential simulator processes
- Worker configurations: 1 and 2 threads
- Computational validation: PASS
- Computational gates per run: 16/16
- Timing warnings: []

All ten transported runs completed successfully and passed the complete computational validation contract.

## 2. Same-thread reproducibility

### 2.1 One worker

- Classification: PASS
- Canonical equality: True

The two one-thread executions reproduce identical canonical scientific ROOT content.

### 2.2 Two workers

- Classification: PASS
- Exact repeatability: True

The two-thread configuration also reproduces identical canonical scientific ROOT content.

No scheduling-induced nondeterminism was observed between repeated executions with the same worker count.

## 3. Cross-thread consistency

Exact event-by-event identity between 1T and 2T is not an acceptance requirement because the current PYTHIA seed policy depends on worker identity.

- Repetition 1 classification: MEASURED_DIFFERENCE
- Repetition 2 classification: MEASURED_DIFFERENCE
- Event entries: 100 versus 100
- Differing event rows: 84
- Differing event values: 560
- Hit entries: 334056 versus 346992
- Canonically differing hit rows: 6688
- Total deposited energy, 1T: 558111.749743805616 MeV
- Total deposited energy, 2T: 542302.092743415385 MeV
- Relative aggregate-energy difference: 2.832705%

The event-level differences include interaction multiplicity, particle-selection accounting, transported-particle counts and deposited energy.

The hit-level differences include deposited energy, timing, step counts and leading-particle lineage fields.

The generator tree is empty by construction because generator audit is disabled for the fixed Cycle 9 campaign.

The metadata difference is limited to the configured worker count.

Both cross-thread realizations independently pass all computational gates. The differences are therefore interpreted as deterministic consequences of the worker-dependent random-stream policy rather than failures of transport, lineage, segmentation or ROOT accounting.

## 4. Performance

| Metric | 1 thread | 2 threads |
|---|---:|---:|
| Minimum wall time (s) | 261.110 | 152.670 |
| Maximum wall time (s) | 263.330 | 155.580 |
| Mean wall time (s) | 262.357 | 153.730 |
| Median wall time (s) | 262.630 | 152.940 |
| Standard deviation (s) | 1.135 | 1.608 |
| Coefficient of variation | 0.433% | 1.046% |

- Two-thread speedup: **1.717209x**
- Parallel efficiency: **85.860%**
- Median wall-time reduction: **41.766%**
- Throughput gain: **71.721%**

No minimum speedup threshold was imposed and all three measurements for each thread count were retained.

The timing coefficients of variation are far below the contracted 20% warning threshold.

## 5. Interpretation

Cycle 9 demonstrates exact reproducibility when the worker count is held fixed, including the two-thread configuration.

Changing from one to two workers changes the PYTHIA random streams participating in the run and therefore generates a different minimum-bias realization.

Event-by-event equality across thread counts is consequently neither observed nor claimed. The correct interpretation is cross-thread consistency with distinct statistical realizations.

The cross-thread samples retain structural validity, complete accounting, energy closure, lineage integrity, segmentation integrity and valid transport state.

## 6. Engineering conclusion

**Cycle 9 result: PASS.**

On the reference machine, two workers provide a speedup of 1.717209x with 85.860% parallel efficiency and a 41.766% reduction in median wall-clock time.

Two worker threads are therefore the recommended reference execution mode on this machine when throughput is preferred.

If future work requires event identity independent of thread count, generator streams should be derived from stable event or subevent identifiers rather than worker identity.

That seed-policy redesign is an optional future engineering improvement and is not required for Cycle 9 acceptance.

## 7. Scope

These measurements characterize the simplified ATLAS/Lorenzetti-like minimum-bias simulator implemented in this repository. They are not official ATLAS performance or detector results.
