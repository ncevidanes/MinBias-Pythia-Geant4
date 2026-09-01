# Cycle 11 — Scientific closeout

## Status

Scientific partition-stability validation is complete.

    CYCLE_11_SCIENTIFIC_CLOSEOUT=PASS
    CYCLE_11_COMPLETE=NO
    FULL_PARTITION_STABILITY=PASS
    SCIENTIFIC_PARTITION_MATRIX=PASS
    READY_FOR_BENCHMARK=NO

## Diagnosed failure

The historical schema-3 pilot produced:

    PRIMARY_PARTITION_STABILITY=PASS
    TRANSPORT_PARTITION_STABILITY=FAIL

Primary PYTHIA content was stable while Geant4 transport diverged after the
local event sequence restarted in a new shard.

## Correction

Cycle 11 introduced event-stable Geant4 transport seeding with identity:

    (seed_base, bcid, transport-event stream)

The transport stream is domain-separated and the seed is installed in
`EventAction::BeginOfEventAction` after primary generation and before tracking.

The global scientific event identity is `bcid`. Local `event`, worker identity,
thread count, job identity and job order do not participate in the scientific
transport seed.

## ROOT schema 4

Schema 4 adds `geant4_transport_seed` to `events` and records:

    geant4_transport_seed_policy
    geant4_transport_seed_identity
    geant4_transport_seed_mixer
    geant4_transport_seed_stream
    geant4_transport_seed_max
    geant4_transport_reseed_scope

Historical schema-3 files remain readable as diagnostic evidence but are
rejected by the post-correction partition validator.

## Validated scientific matrix

The following passed:

- monolithic versus partitioned execution;
- exact rerun;
- reversed shard execution order;
- 1T versus 2T;
- all-2T partitioning;
- mixed 1T/2T partitioning;
- fixed interaction count;
- Poisson interactions;
- non-zero beam smearing;
- seed sensitivity;
- BCID gap rejection;
- BCID overlap rejection;
- duplicate BCID rejection.

Final gates:

    PRIMARY_PARTITION_STABILITY=PASS
    TRANSPORT_PARTITION_STABILITY=PASS
    THREAD_STABILITY=PASS
    FULL_PARTITION_STABILITY=PASS
    SCIENTIFIC_PARTITION_MATRIX=PASS

## Scientific contract

Within the validated matrix:

    (seed_base, BCID, physics configuration)
        -> same canonical scientific result

independent of local event ID, worker identity, thread count, job partition,
job order and job restart.

Different `seed_base` values continue to produce different physical
realizations.

## Evidence

Scientific ROOT artifacts:

    historical schema-3 pilot = 3
    post-correction schema-4 pilot = 3
    fixed-topology schema-4 matrix = 7
    Poisson schema-4 matrix = 9
    total = 22

SHA256 inventory:

    evidence/scientific-root-artifacts.sha256

Machine-readable summary:

    evidence/scientific-summary.json

## Remaining Cycle 11 work

Before benchmarking:

1. update public documentation to the Cycle-11/schema-4 contract;
2. create the canonical Cycle-11 commit;
3. rebuild from that committed HEAD;
4. verify runtime provenance against that HEAD;
5. execute the controlled performance campaign.

Therefore:

    CYCLE_11_SCIENTIFIC_CLOSEOUT=PASS
    CYCLE_11_COMPLETE=NO
    READY_FOR_CANONICAL_COMMIT=NO
    READY_FOR_BENCHMARK=NO
