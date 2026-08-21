# Cycle 9 — Performance, parallelism, and reproducibility contract

## 1. Objective

Cycle 9 characterizes performance, CPU parallelism, and reproducibility of the
integrated minimum-bias PYTHIA -> Geant4 simulator.

The campaign addresses three distinct questions:

1. whether repeated executions with the same thread count and seed reproduce
   the same scientific content;
2. whether changing the Geant4 worker count preserves validated computational
   and physical invariants;
3. what execution-time benefit is obtained when moving from one to two worker
   threads on the reference machine.

Performance measurements are valid only for runs that pass the complete
computational validation contract.

The detector remains ATLAS/Lorenzetti-like and simplified. Cycle 9 results
characterize this simulator and are not official ATLAS performance results.

## 2. Baseline

The Cycle 9 branch starts from commit:

6249d914763b370e6082e98c00f8d530b17ba1bf

This is the integrated master state after Cycle 8.

The tracked worktree must be clean before campaign execution.

Pre-existing unrelated untracked files are outside Cycle 9 and must not be
staged, deleted, moved, or modified by Cycle 9 tooling.

Generated ROOT files, timing logs, temporary files, and campaign products remain
under outputs/ and are not versioned.

## 3. Fixed physics and execution configuration

Cycle 9 uses config/production.conf as its configuration template.

The following command-line overrides and fixed settings are authoritative:

- Generator: PYTHIA
- Beams: proton-proton
- Centre-of-mass energy: 14 TeV
- PYTHIA process: SoftQCD:inelastic
- Interaction mode: Poisson
- Mean interactions per BC: 1
- First BCID: 0
- Physics list: FTFP_BERT_ATL
- Production cut: 1 mm
- Beam sigma X/Y/Z: 0 mm
- Beam sigma T: 0 ns
- Maximum absolute eta: 1.8
- Neutrino transport: disabled
- Generator audit: disabled
- Overlap check: disabled
- Seed base: 9512
- Initial worker counts: 1 and 2

The events, mean_interactions, threads, seed_base, and output path stored in
production.conf are overridden by the Cycle 9 command line.

## 4. Current random-seed architecture

The current implementation derives the PYTHIA random seed from the worker
identity.

Conceptually:

worker_seed = normalize(seed_base + 104729 * worker_id)

Therefore changing the Geant4 worker count can change the collection of PYTHIA
random streams participating in a run.

Cycle 9 consequently separates repeatability under an equal thread count from
cross-thread scientific consistency.

## 5. Reproducibility definitions

### 5.1 One-thread repeatability

Two executions with threads = 1 and seed_base = 9512 must reproduce identical
canonical scientific ROOT content.

Any difference is a reproducibility failure requiring investigation.

### 5.2 Two-thread repeatability

Two executions with threads = 2 and seed_base = 9512 are tested for canonical
scientific repeatability.

Exact repeatability is the target.

If Geant4 scheduling changes event-to-worker assignment and therefore event
content, that behavior must be measured and documented rather than hidden by
aggregate-only comparisons.

### 5.3 Cross-thread consistency

Exact event-by-event identity between one-thread and two-thread runs is not an
initial acceptance requirement because the current PYTHIA seed policy is
worker-dependent.

The 1T and 2T campaigns must nevertheless preserve:

- ROOT structural validity;
- complete event and BCID coverage;
- interaction accounting;
- valid deposited energy;
- event-to-hit energy closure;
- lineage integrity;
- segmentation integrity;
- absence of invalid transport states;
- physically compatible aggregate behavior.

## 6. Reproducibility matrix

The fixed reproducibility profile contains four runs:

| Run | Threads | Repetition | Events | Mean interactions | Seed |
|---|---:|---:|---:|---:|---:|
| repro-t1-r1 | 1 | 1 | 100 | 1 | 9512 |
| repro-t1-r2 | 1 | 2 | 100 | 1 | 9512 |
| repro-t2-r1 | 2 | 1 | 100 | 1 | 9512 |
| repro-t2-r2 | 2 | 2 | 100 | 1 | 9512 |

All runs are executed sequentially.

No two reference simulator processes may execute concurrently.

## 7. Canonical ROOT comparison

Reproducibility is evaluated from canonical scientific content rather than raw
ROOT SHA-256 alone.

Raw SHA-256 remains a provenance measurement.

The canonical analyzer must compare at least:

- event ID;
- BCID;
- requested interactions;
- generated interactions;
- generation failures;
- transported-particle count;
- unknown-PDG count;
- unlineaged-step count;
- segmentation-failure count;
- total deposited energy per event;
- complete hit content after deterministic ordering.

TTree entry order alone must not define hit identity.

Stable scientific fields must be used to canonicalize event and hit records
before equality or digest comparison.

If floating-point differences occur, the analyzer must report maximum absolute
and relative differences explicitly.

No floating-point difference may be silently hidden by a loose global
tolerance.

## 8. Computational acceptance gates

Every transported run must satisfy all of the following:

- simulator return code zero;
- readable and non-zombie ROOT output;
- exactly the requested number of events;
- unique event IDs;
- complete expected BCID interval;
- no duplicate BCIDs;
- requested interactions equal generated interactions plus recorded failures;
- no negative deposited energy;
- no non-finite deposited energy;
- event-to-hit deposited-energy closure;
- no orphan hits;
- no negative subevent IDs;
- no invalid unknown-PDG transport state;
- no unlineaged steps;
- no segmentation failures.

A run failing any computational gate is invalid.

Timing from a computationally invalid run must not enter performance summaries.

## 9. Performance matrix

The fixed performance profile contains six runs:

| Run | Threads | Repetition | Events | Mean interactions | Seed |
|---|---:|---:|---:|---:|---:|
| perf-t1-r1 | 1 | 1 | 200 | 1 | 9512 |
| perf-t2-r1 | 2 | 1 | 200 | 1 | 9512 |
| perf-t1-r2 | 1 | 2 | 200 | 1 | 9512 |
| perf-t2-r2 | 2 | 2 | 200 | 1 | 9512 |
| perf-t1-r3 | 1 | 3 | 200 | 1 | 9512 |
| perf-t2-r3 | 2 | 3 | 200 | 1 | 9512 |

The execution order is interleaved between one-thread and two-thread runs to
reduce systematic bias from machine drift, temperature, cache state, and
unrelated background activity.

Each run is executed sequentially and measured independently with
/usr/bin/time -v.

## 10. Performance metrics

For every computationally valid performance run record:

- wall-clock time;
- user CPU time;
- system CPU time;
- maximum resident set size;
- ROOT output size;
- events per second;
- bunch crossings per second;
- simulator return code;
- ROOT SHA-256;
- resolved simulator configuration;
- Git commit;
- software versions.

For each thread count, the primary estimator is the median of the three valid
runs.

Primary two-thread speedup:

speedup_2T = median_wall_1T / median_wall_2T

Parallel efficiency:

efficiency_2T = speedup_2T / 2

No minimum speedup is imposed before measurement.

A measured speedup below one is a valid engineering result if all computational
validation gates pass.

The measured result must be reported without removing runs merely because they
reduce the apparent speedup.

## 11. Timing stability

For each thread count report:

- minimum wall time;
- maximum wall time;
- mean wall time;
- median wall time;
- standard deviation;
- coefficient of variation.

A coefficient of variation above 20 percent is a timing-stability warning and
requires inspection of machine load or other execution conditions.

No repetition may be discarded solely because it is slower than the others.

## 12. Resource safety

The initial Cycle 9 campaign is restricted to a maximum of two simulator
threads.

Before transport the executor must verify:

- logical CPUs >= 2;
- available memory >= 2 GiB;
- available storage >= 5 GiB;
- Geant4 multithreading enabled.

Failure of any resource gate aborts transport.

Tests with more than two threads require a separately committed contract
extension after the initial 1T/2T campaign is analyzed.

## 13. Transactional execution

The eventual Cycle 9 executor must:

1. reject an existing final campaign destination;
2. verify repository and branch state;
3. rebuild with controlled build parallelism;
4. execute the complete CTest suite;
5. execute the Cycle 9 preflight;
6. validate all simulator dry-runs;
7. create a temporary sibling staging directory;
8. execute reference runs sequentially;
9. validate every ROOT output before accepting timing data;
10. execute canonical reproducibility analysis;
11. execute performance analysis;
12. record manifests, versions, timing data, and checksums;
13. publish the final campaign through one atomic rename.

A controlled failure must not leave a partial final campaign directory.

Incomplete staging data must be removed after a controlled failure.

## 14. Interpretation boundaries

Cycle 9 distinguishes the following concepts:

- repeatability under an equal execution configuration;
- scientific consistency across different thread counts;
- execution performance;
- parallel efficiency;
- thread-independent reproducibility.

A performance gain does not prove reproducibility.

Reproducibility does not imply a performance gain.

Cross-thread non-identity is not automatically a detector-physics failure while
the current worker-dependent seed architecture exists.

Any cross-thread non-identity must nevertheless be quantified and documented.

## 15. Planned stages

The planned Cycle 9 progression is:

- 9.0A — environment and multithreading readiness;
- 9.0B — committed experimental contract;
- 9.0C — preflight, executor, and analysis tooling;
- 9.1 — reproducibility campaign;
- 9.2 — canonical ROOT reproducibility audit;
- 9.3 — performance and parallelism benchmark;
- 9.4 — seed-policy and thread-independence investigation;
- 9.5 — integrated regression validation;
- 9.6 — evidence, review, pull request, and integration.

## 16. Transport authorization boundary

This specification alone does not authorize transport.

Transport remains forbidden until all of the following exist and pass:

- Cycle 9 preflight tooling;
- transactional executor;
- canonical ROOT analyzer;
- synthetic tests for Cycle 9 tooling;
- complete CTest suite;
- simulator dry-run matrix;
- tracked-worktree execution gate;
- resource-safety execution gate.

Only a later explicit execution gate may authorize the Cycle 9 transported
campaign.
