# Cycle 10 — Event-stable reproducibility contract

## 1. Purpose

Cycle 10 shall make the scientific realization independent of the
number of Geant4 worker threads.

For the same physical configuration, seed base and BCID range,
changing `threads` shall not change the generated primary event or
the transported scientific result.

The thread count shall become an execution parameter rather than a
parameter defining the random physical realization.

## 2. Baseline

Cycle 10 starts from:

    master = ac0867fd938b7f21912ebc519870345383f448f1

Cycle 9 demonstrated:

- exact repeatability for repeated 1-thread runs;
- exact repeatability for repeated 2-thread runs;
- deterministic scientific differences between 1-thread and
  2-thread runs.

Cycle 10.0A identified the cause in primary generation:

- PYTHIA seed depends on `threadId`;
- the auxiliary `std::mt19937_64` seed depends on `threadId`;
- that auxiliary engine controls pile-up Poisson sampling and
  collision-vertex smearing;
- Geant4 is seeded independently through its master RNG path.

## 3. Stable event identity

### 3.1 Local event identifier

`eventId` is the Geant4-local event index.

It is not the canonical random-stream identity.

### 3.2 Global generation identifier

The canonical event identity for primary-generation random streams is:

    bcid = first_bcid + eventId

`bcid` is chosen because it remains meaningful when a campaign is
partitioned into multiple jobs whose local event IDs restart at zero.

All Cycle 10 primary-generation random streams shall therefore be
derived from `bcid`, not from `threadId`.

## 4. Root seed

`seed_base` remains the single user-controlled root seed.

The existing CLI and configuration meaning of `seed_base` shall remain
unchanged.

No wall-clock time, process ID, worker ID, scheduling order or external
entropy may participate in scientific seed derivation.

## 5. Stable seed tuple

Every primary-generation random stream shall be identified by:

    (seed_base, bcid, subevent, stream_id)

For run-level initialization streams, `bcid = 0` and `subevent = 0`
shall be used.

For event-level streams, `subevent = 0` shall be used.

For per-interaction streams, the actual zero-based subevent index shall
be used.

`threadId` is forbidden from this tuple.

## 6. Seed mixer

Cycle 10 shall use a frozen 64-bit deterministic mixer named:

    splitmix64-v1

The primitive is defined using unsigned 64-bit arithmetic:

    x += 0x9E3779B97F4A7C15
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9
    x = (x ^ (x >> 27)) * 0x94D049BB133111EB
    x = x ^ (x >> 31)

Tuple composition shall be deterministic and shall be frozen by
known-vector unit tests before production validation.

The implementation must use only well-defined unsigned integer
operations for seed mixing.

No guarantee of mathematical collision freedom over the entire
64-bit input domain is claimed.

Collision tests over the contracted operational validation domain are
mandatory.

## 7. Immutable random-stream identifiers

The following stream IDs are frozen for Cycle 10:

    1 = PYTHIA_INITIALIZATION
    2 = INTERACTION_COUNT
    3 = PYTHIA_SUBEVENT
    4 = VERTEX_X
    5 = VERTEX_Y
    6 = VERTEX_Z
    7 = VERTEX_T

Existing stream IDs must never be silently reassigned to a different
meaning.

Future streams shall receive new IDs.

## 8. PYTHIA initialization

Every worker may retain a thread-local PYTHIA object for performance.

However, PYTHIA initialization must no longer depend on the worker ID.

All worker-local PYTHIA instances shall be initialized from the same
deterministic initialization seed derived from:

    (seed_base, 0, 0, PYTHIA_INITIALIZATION)

This prevents worker-dependent initialization state.

## 9. PYTHIA subevent generation

Immediately before each `pythia.next()` attempt, PYTHIA's RNG shall be
reinitialized with the seed derived from:

    (seed_base, bcid, subevent, PYTHIA_SUBEVENT)

The resulting 64-bit value shall be mapped to the valid PYTHIA
interval:

    1 .. 900000000

using a deterministic mapping.

The preferred mapping is:

    pythia_seed = 1 + (stable_seed_64 % 900000000)

`Random:seed = 0` is forbidden for derived scientific seeds.

A PYTHIA generation failure must not shift the random stream assigned
to any later subevent.

If reseeding the worker-local PYTHIA RNG proves insufficient to obtain
exact cross-thread primary generation, the implementation must adopt a
stronger isolation strategy.

The acceptance criterion shall not be relaxed merely to preserve the
initial implementation strategy.

## 10. Pile-up interaction count

For `interaction_mode = poisson`, the number of requested interactions
shall be sampled from an RNG initialized only from:

    (seed_base, bcid, 0, INTERACTION_COUNT)

No persistent worker-level auxiliary RNG state may determine the
interaction count.

For `interaction_mode = fixed`, no random draw is required.

## 11. Collision-vertex smearing

The four collision-vertex dimensions shall use independent stable
streams.

For subevent `s`:

    X -> (seed_base, bcid, s, VERTEX_X)
    Y -> (seed_base, bcid, s, VERTEX_Y)
    Z -> (seed_base, bcid, s, VERTEX_Z)
    T -> (seed_base, bcid, s, VERTEX_T)

A zero configured sigma shall return exactly zero.

Changing whether one coordinate has zero sigma must not consume or
shift the random stream of another coordinate.

The single-particle generator shall use the same vertex-stream policy
with `subevent = 0`.

## 12. Persistent auxiliary RNG state

The current persistent worker-level `std::mt19937_64 random_` must no
longer determine scientific event content across multiple events.

Scientific random draws must be reconstructed from stable tuple keys.

Thread scheduling must therefore be unable to alter which random
numbers belong to a BCID.

## 13. Geant4 transport RNG

Cycle 10 shall initially retain Geant4's standard multithreaded
event-seeding mechanism.

The existing master seed path remains rooted in `seed_base`.

No custom Geant4 run manager or custom transport seeding shall be
introduced unless primary generation has first been made exact and a
residual transport-level difference is demonstrated.

This follows the Geant4 MT design in which event random seeds are
preassigned independently of worker scheduling.

## 14. ROOT metadata

The current metadata describing a worker-based PYTHIA stride becomes
obsolete under the event-stable policy.

Cycle 10 shall bump the ROOT metadata/schema version rather than
silently changing the meaning of the old field.

The new metadata shall identify at least:

    seed_policy = event-stable-v1
    seed_identity = bcid
    seed_mixer = splitmix64-v1
    pythia_seed_max = 900000000
    pythia_reseed_scope = subevent

The old `pythia_worker_seed_stride` semantics must not be presented as
active under the new schema.

Backward interpretation of previous ROOT schemas must remain explicit.

## 15. Analyzer compatibility

The Cycle 9 canonical analyzer currently knows the old metadata schema.

Cycle 10 must update or extend analysis logic in a version-aware way.

A new schema must not be interpreted using old worker-stride semantics.

Scientific comparison shall remain canonical and independent of ROOT
entry ordering.

## 16. Scientific equality contract

For two runs differing only in thread count:

    same seed_base
    same first_bcid
    same number of events
    same generator configuration
    same physics configuration

the following canonical scientific content must be exactly equal:

    events
    hits
    generator

Canonical sorting may be used before comparison.

Byte-for-byte equality of the ROOT files themselves is NOT required.

ROOT serialization order, compression or file metadata are not
scientific equality criteria.

## 17. Metadata comparison across thread counts

Cross-thread metadata is allowed to differ only in explicitly
operational fields, including:

    threads
    output_file
    normalized_config

All physics and random-policy metadata must otherwise agree.

The analyzer must report unexpected metadata differences.

## 18. Required validation modes

Cycle 10 validation must exercise all of the following.

### 18.1 Fixed interactions

A fixed-interaction campaign shall verify PYTHIA and vertex stability
without Poisson multiplicity as an additional variable.

### 18.2 Poisson interactions

A Poisson campaign shall verify stable interaction-count sampling in
addition to PYTHIA and vertex stability.

### 18.3 Generator audit

At least one cross-thread validation campaign shall enable
`generator_audit` so that the PYTHIA-level canonical tree is
non-empty and directly comparable.

### 18.4 Nonzero beam smearing

At least one validation campaign shall use nonzero beam sigmas so that
all four stable vertex streams are exercised.

## 19. Required unit tests

The new seed-policy tests shall cover at minimum:

- frozen SplitMix64 known vectors;
- deterministic tuple composition;
- valid PYTHIA seed interval;
- stable initialization seed;
- different BCIDs produce different tested seeds;
- different stream IDs produce different tested seeds;
- different tested subevents produce different tested seeds;
- identical tuple always produces identical seed;
- no `threadId` parameter exists in the new scientific seed API;
- no collisions in the selected operational test domain;
- deterministic event-level interaction-count RNG setup;
- deterministic per-coordinate vertex RNG setup.

The existing tests that require distinct seeds by worker shall be
replaced because they encode the behavior Cycle 10 intentionally
removes.

## 20. Cross-thread acceptance matrix

At minimum:

    1T run A == 1T run B
    2T run A == 2T run B
    1T run A == 2T run A
    1T run B == 2T run B

shall hold for canonical scientific content.

Both fixed and Poisson configurations shall be represented.

## 21. Seed sensitivity

Thread independence must not accidentally collapse all campaigns onto
one realization.

Changing `seed_base` while keeping the physical configuration fixed
must change the scientific digest in a validation campaign.

## 22. Performance

Cycle 10 shall measure the performance cost of event-stable reseeding.

No result may be cherry-picked.

No arbitrary minimum speedup is a correctness gate.

If event-stable generation causes a material regression, it shall be
reported and analyzed rather than hidden.

Correctness and reproducibility take precedence over preserving Cycle 9
timing.

## 23. Compatibility

Cycle 10 shall preserve the existing user-facing meanings of:

    --seed
    --threads
    seed_base
    first_bcid
    interaction_mode
    mean_interactions
    fixed_interactions

After Cycle 10, `--threads` shall alter execution parallelism but must
not alter the scientific realization.

## 24. Scope boundary

Cycle 10 acceptance concerns exact reproducibility across thread counts
for the same run definition and software environment.

The following are not Cycle 10 acceptance requirements:

- bitwise reproducibility across different compilers;
- bitwise reproducibility across different standard libraries;
- bitwise reproducibility across different PYTHIA versions;
- bitwise reproducibility across different Geant4 versions;
- GPU reproducibility;
- scaling studies beyond the thread-count validation needed here;
- exact full-transport invariance under arbitrary repartitioning of one
  campaign into multiple independent processes.

Using `bcid` as the generation identity nevertheless avoids deliberate
reuse of the same primary-generation stream when local event IDs restart
in separate BCID ranges.

## 25. Implementation order

The implementation shall proceed in this order:

1. stable seed primitive and unit tests;
2. replacement of worker-based seed-policy tests;
3. event-stable auxiliary RNG;
4. worker-independent PYTHIA initialization;
5. per-subevent PYTHIA reseeding;
6. ROOT schema/metadata update;
7. version-aware canonical analyzer;
8. fixed-interaction cross-thread validation;
9. Poisson + nonzero-smearing cross-thread validation;
10. full scientific equality gate;
11. performance measurement;
12. documentation and merge.

No production-scale campaign shall run before the unit and short
cross-thread gates pass.

## 26. Final Cycle 10 acceptance

Cycle 10 is PASS only if:

- all repository regression tests pass;
- same-thread repeatability remains exact;
- 1T and 2T canonical generator content is exact;
- 1T and 2T canonical event content is exact;
- 1T and 2T canonical hit content is exact;
- metadata differences are limited to allowed operational fields;
- changing the root seed changes the realization;
- no worker ID participates in scientific primary-generation seed
  derivation;
- the new RNG policy is recorded in ROOT metadata;
- performance impact is measured and documented.

If primary generation becomes exact but transport does not, Cycle 10
must isolate and document the residual Geant4-level cause before any
further modification of transport seeding.
