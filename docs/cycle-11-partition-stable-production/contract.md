# Cycle 11 — Partition-stable production contract

## 1. Purpose

Cycle 11 shall extend the event-stable reproducibility achieved in
Cycle 10 from thread-count independence to production-job partition
independence.

For the same scientific configuration, root seed and global BCID
interval, the scientific realization shall not depend on whether the
campaign is executed:

- as one monolithic job;
- as multiple non-overlapping jobs;
- with different valid partition boundaries;
- with the partition jobs executed in a different order;
- with one or two Geant4 worker threads;
- with a mixture of thread counts across partition jobs.

The number and organization of production jobs shall become operational
parameters rather than parameters defining the physical realization.

## 2. Baseline

Cycle 11 starts from:

    master = bc9c4aab56fa6a3ee8a69452cf2a0e0831886e0a

and branch:

    cycle-11-partition-stable-production

The baseline includes the Cycle 10 event-stable primary-generation
policy:

    seed_policy = event-stable-v1
    seed_identity = bcid
    seed_mixer = splitmix64-v1

with scientific primary-generation streams derived from:

    (seed_base, bcid, subevent, stream_id)

Cycle 11 shall preserve those validated semantics.

## 3. Global and local event identity

A Geant4 `event` identifier is local to one simulator invocation.

For every individual job:

    event = 0 .. events - 1

and:

    bcid = first_bcid + event

shall hold exactly.

A local `event` identifier is therefore not a globally stable production
identifier.

The BCID is the canonical global event identity.

A restarted or separately launched job may legitimately contain:

    event = 0

while representing a different physical event because its
`first_bcid` is different.

## 4. Global BCID interval

A logical campaign shall define one global closed BCID interval:

    [first_global_bcid, last_global_bcid]

with:

    last_global_bcid =
        first_global_bcid + total_events - 1

Every BCID in this interval shall occur exactly once in a valid
partitioned realization.

No gap is permitted.

No overlap is permitted.

No duplicate BCID is permitted.

No BCID outside the contracted global interval is permitted.

## 5. Partition definition

A partition is a finite collection of non-empty shards.

Each shard shall define at minimum:

    first_bcid
    events
    threads
    output_file

and therefore represents:

    [first_bcid, first_bcid + events - 1]

The union of all shard intervals shall be exactly equal to the
contracted global BCID interval.

Partition correctness shall be determined from BCID coverage, not from
the order in which shard processes are launched or completed.

## 6. Partition-order independence

Reordering otherwise identical shards shall not change the global
scientific realization.

For example:

    shard A
    shard B
    shard C

and:

    shard C
    shard A
    shard B

shall produce the same global canonical scientific content.

Output filenames and wall-clock execution order are operational and do
not define scientific identity.

## 7. Canonical global scientific keys

Partition-aware comparison shall not use the local `event` identifier
as part of the global scientific key.

The canonical global keys shall be:

### events

    (bcid)

### hits

    (bcid, subevent, cell_id)

### generator

    (bcid, subevent, index)

These keys shall be unique inside the aggregated logical campaign.

The `run` and `event` branches remain useful provenance and local
consistency fields, but shall not define global partition-independent
scientific identity.

## 8. Local provenance invariants

Removing `event` from the global comparison key shall not mean ignoring
local provenance integrity.

For every individual shard, validation shall require:

    event = 0 .. events - 1

without gaps or duplicates, and:

    bcid = first_bcid + event

for every event.

Every hit and every generator record shall reference an event/BCID pair
that is valid inside its source shard.

Therefore local job consistency and global scientific identity remain
separate mandatory gates.

## 9. Scientific comparison fields

All physical fields of `events`, `hits` and `generator` shall be
compared exactly after global canonicalization.

The local fields:

    run
    event

may differ in representation between monolithic and partitioned
execution and shall not by themselves cause partition-equivalence
failure.

They shall nevertheless satisfy the local provenance invariants of
Section 8.

No floating-point tolerance shall be introduced merely to make
partitioned execution pass.

The target is exact canonical scientific equality.

## 10. Monolithic versus partitioned equality

For equal:

    seed_base
    global BCID interval
    generator configuration
    PYTHIA configuration
    interaction configuration
    beam configuration
    detector geometry
    physics list
    production cuts
    transport-neutrino policy
    generator-audit policy
    software identity

the following shall hold:

    monolithic events
        ==
    globally canonicalized partition events

    monolithic hits
        ==
    globally canonicalized partition hits

    monolithic generator
        ==
    globally canonicalized partition generator

Byte-for-byte equality of ROOT files is not required.

## 11. Metadata policy

Metadata shall be evaluated in two layers.

### 11.1 Campaign-invariant metadata

Physics and random-policy metadata shall agree across all shards and the
monolithic reference where semantically applicable.

This includes at minimum:

    schema_version
    project_version
    git_commit
    root_version
    geant4_version
    pythia_version
    seed_base
    seed_policy
    seed_identity
    seed_mixer
    pythia_seed_max
    pythia_reseed_scope
    interaction_mode
    mean_interactions
    fixed_interactions
    pythia_config
    physics_list
    production_cut_mm
    beam_sigma_x_mm
    beam_sigma_y_mm
    beam_sigma_z_mm
    beam_sigma_t_ns
    max_abs_eta
    transport_neutrinos
    generator_audit
    generator_mode

### 11.2 Shard-operational metadata

The following may legitimately vary by shard:

    events
    first_bcid
    threads
    output_file
    config_file
    normalized_config

Differences outside the explicitly allowed partition-operational set
shall be reported.

## 12. Primary-generation isolation gate

At least one validation campaign shall enable:

    generator_audit = true

and produce a non-empty `generator` tree.

Before a full partition-equivalence result is classified, the global
canonical `generator` content shall be compared independently.

This establishes whether primary generation itself is partition-stable.

A generator mismatch shall be classified separately from a transport
mismatch.

## 13. Current Geant4 transport-seed risk

At the Cycle 11 baseline, Geant4 is initialized with a master random
seed rooted in `seed_base`.

The existing application does not derive that initial Geant4 transport
seed directly from `first_bcid`.

Cycle 10 demonstrated thread-count independence for the contracted
single-job validation domain.

It did not demonstrate that restarting a process at a new
`first_bcid` preserves the Geant4 transport random realization of that
BCID relative to a monolithic job.

Therefore partition-stable Geant4 transport is an explicit Cycle 11
hypothesis to test and must not be assumed.

## 14. Diagnostic classification

The first controlled partition pilot shall distinguish at least three
outcomes.

### Classification A — full partition stability

    generator = identical
    events    = identical
    hits      = identical

Result:

    FULL_PARTITION_STABILITY=PASS

### Classification B — transport-level partition dependence

    generator = identical
    events or hits = different

Result:

    PRIMARY_PARTITION_STABILITY=PASS
    TRANSPORT_PARTITION_STABILITY=FAIL

This result shall trigger investigation of Geant4 event-level random
identity.

It shall not be hidden by loosening the scientific comparison.

### Classification C — primary-generation partition dependence

    generator = different

Result:

    PRIMARY_PARTITION_STABILITY=FAIL

Primary generation shall be repaired before transport-level conclusions
are drawn.

## 15. Transport RNG correction policy

No custom Geant4 transport-seeding implementation shall be introduced
before the diagnostic pilot demonstrates that it is necessary.

If transport-level partition dependence is demonstrated, the correction
shall satisfy all of the following:

- transport random identity is derived from stable global event
  identity;
- worker identity is excluded;
- process scheduling is excluded;
- local event numbering is excluded from global random identity;
- changing partition boundaries does not change the transport stream
  assigned to a BCID;
- existing Cycle 10 cross-thread equality remains valid;
- different `seed_base` values still produce different realizations.

The preferred conceptual transport identity is:

    (seed_base, bcid, TRANSPORT_EVENT)

but the exact Geant4 integration mechanism shall be selected only after
the diagnostic result is known.

## 16. Schema and metadata evolution

If Cycle 11 changes the Geant4 scientific random-seeding semantics, the
ROOT metadata schema shall be bumped.

The new metadata shall identify the transport random policy explicitly.

Existing schema-3 files shall continue to be interpreted according to
their historical semantics.

A new transport policy shall never be silently represented as schema 3.

If no transport-seeding change is necessary, a schema bump shall not be
performed merely for the partition analyzer.

## 17. Required partition-aware analyzer behavior

Cycle 11 shall provide analysis logic able to consume:

- one monolithic ROOT file;
- multiple partition ROOT files.

The analyzer shall validate every input shard before global aggregation.

It shall reject:

- duplicate BCIDs;
- overlapping shard intervals;
- gaps in global BCID coverage;
- BCIDs outside the declared campaign interval;
- incomplete local event intervals;
- violations of `bcid = first_bcid + event`;
- orphan hits;
- orphan generator records;
- duplicate global canonical keys;
- incompatible scientific metadata;
- incompatible ROOT schemas.

Input-file ordering shall not affect the result.

## 18. Required analyzer regression tests

Synthetic or dependency-light tests shall cover at minimum:

1. one monolithic representation equals an equivalent two-shard
   representation;
2. local `event` restart at zero does not create a false scientific
   difference;
3. reversed shard order gives the same result;
4. mixed shard thread counts are allowed;
5. a BCID gap is rejected;
6. a BCID overlap is rejected;
7. a duplicate global BCID is rejected;
8. a duplicate hit global key is rejected;
9. a duplicate generator global key is rejected;
10. a local `event` gap is rejected;
11. a local event/BCID relation violation is rejected;
12. a scientific event-field difference is detected;
13. a scientific hit-field difference is detected;
14. a generator-field difference is detected;
15. an unexpected metadata difference is rejected;
16. allowed shard-operational metadata differences are accepted.

These tests shall run without requiring a Geant4 transport campaign.

They shall be added to the lightweight regression suite where
appropriate.

## 19. Controlled diagnostic pilot

After analyzer and preflight regression tests pass, Cycle 11 shall run
a small controlled diagnostic pilot.

The pilot shall use:

- a nonzero `first_bcid`;
- a fixed `seed_base`;
- generator audit enabled;
- a non-empty generator tree;
- nonzero beam smearing;
- identical physics configuration;
- a monolithic realization;
- an equivalent multi-shard realization.

The first pilot shall be intentionally small.

Its purpose is diagnosis, not performance measurement.

## 20. Required pilot comparisons

The pilot shall compare at minimum:

    monolithic 1T
        versus
    partitioned 1T

and:

    monolithic 1T
        versus
    partitioned mixed 1T/2T

If a transport correction becomes necessary, the same matrix shall be
repeated after the correction.

## 21. Shard restart repeatability

At least one individual shard shall be executed twice with identical:

    first_bcid
    events
    seed_base
    threads
    physics configuration

and shall reproduce exactly.

This verifies that restartability itself remains deterministic.

## 22. Cross-thread preservation

Cycle 11 must not regress the Cycle 10 result.

For equal global BCID content:

    1T == 2T

shall remain true under the event-stable policy.

Any transport RNG correction required for partition stability must also
remain independent of worker scheduling.

## 23. Seed sensitivity preservation

Partition stability must not collapse different root seeds onto one
realization.

For otherwise identical partition definitions:

    seed_base = S
        !=
    seed_base = S + 1

shall produce a different non-empty scientific realization.

## 24. Fixed and Poisson interaction modes

The final Cycle 11 validation shall exercise both:

    interaction_mode = fixed

and:

    interaction_mode = poisson

The fixed mode helps isolate generation/transport partition identity.

The Poisson mode exercises the stable interaction-count stream.

## 25. Performance

Correctness precedes performance.

No benchmark shall be executed before partition-stable scientific
correctness is established.

After correctness, Cycle 11 may measure partition orchestration or
transport-seeding overhead.

No arbitrary minimum speedup shall be a correctness gate.

## 26. README correction

The repository README currently contains historical worker-based seed
language from before Cycle 10.

Cycle 11 shall update the README so that it describes:

    seed_policy = event-stable-v1
    seed_identity = bcid

and no longer states that thread count defines the scientific random
realization.

The correction shall preserve historical documentation in the
cycle-specific reports rather than rewriting history.

## 27. Compatibility

Cycle 11 shall preserve the existing meanings of:

    --seed
    --threads
    seed_base
    first_bcid
    events
    interaction_mode
    mean_interactions
    fixed_interactions

No user-facing option shall silently change meaning.

## 28. Acceptance matrix

The final Cycle 11 acceptance matrix shall include at minimum:

    monolithic 1T
        ==
    partitioned 1T

    monolithic 1T
        ==
    partitioned mixed 1T/2T

    partition order A,B,C
        ==
    partition order C,A,B

    shard restart run 1
        ==
    shard restart run 2

    seed S
        !=
    seed S+1

for canonical scientific content.

Both fixed and Poisson configurations shall be represented before final
closure.

## 29. Failure policy

A partition mismatch is a scientific diagnostic result.

The acceptance criteria shall not be relaxed after observing the
result.

In particular:

- local event identifiers shall not be incorrectly promoted to global
  identities;
- real physics differences shall not be removed from comparison;
- floating-point tolerances shall not be introduced solely to create a
  PASS;
- a transport-level mismatch shall not be attributed to PYTHIA if the
  generator audit proves primary equality.

## 30. Cycle 11 completion criterion

Cycle 11 may be closed only when:

- partition-aware static/regression tests pass;
- shard coverage validation passes;
- generator partition stability passes;
- full events/hits partition stability passes;
- cross-thread equality remains preserved;
- shard restart repeatability passes;
- partition-order independence passes;
- seed sensitivity passes;
- fixed and Poisson validation modes pass;
- metadata/schema semantics are explicit;
- README reproducibility documentation is current;
- the final tracked worktree is clean;
- all accepted changes are integrated through the normal branch and PR
  workflow.

Until all of these conditions are met:

    CYCLE_11_COMPLETE=NO
