# Cycle 11 — Event-stable Geant4 transport RNG design

## Status

Design frozen after Stage 11.3A.

Stage 11.3A established:

- primary-generation partition stability: PASS;
- Geant4 transport partition stability: FAIL;
- BCIDs 11000 and 11001: monolithic == partitioned;
- BCIDs 11002 and 11003: monolithic != partitioned;
- shard B restarts local event ID at zero;
- local-event restart signature: CONFIRMED.

No transport RNG correction had been applied when this diagnosis was made.

## Scientific objective

For a fixed physics configuration, the Geant4 transport result of a
physical bunch crossing must depend on its global scientific identity
and not on execution topology.

Required identity:

    (seed_base, bcid, transport-event stream)

The following MUST NOT participate in the transport scientific seed:

- worker or thread identifier;
- Geant4 local event ID;
- shard/job identifier;
- shard order;
- process restart count;
- campaign partition boundaries.

## Stable seed derivation

The Cycle 10 SplitMix64 tuple-composition rule remains the common mixer.

A new domain-separated stream SHALL be introduced:

    SeedStream::kGeant4TransportEvent

Transport seed derivation SHALL conceptually be:

    stable64 =
        StableSeed64(
            seed_base,
            bcid,
            0,
            SeedStream::kGeant4TransportEvent
        )

    geant4_transport_seed =
        1 + stable64 % 2147483646

Therefore:

    1 <= geant4_transport_seed <= 2147483646

The positive 31-bit range is selected deliberately for portability
through the signed `long` interface used by
`G4Random::setTheSeed`.

## Reseed point

The reseed SHALL occur in:

    EventAction::BeginOfEventAction(const G4Event*)

The global BCID SHALL be reconstructed as:

    first_bcid + event->GetEventID()

and SHALL agree with the BCID already established in EventState during
primary generation.

The event transport RNG SHALL then be installed with:

    G4Random::setTheSeed(geant4_transport_seed)

The hook is before Geant4 tracking/transport and after primary
generation.

Therefore Pythia keeps its independent event-stable RNG policy while
the Geant4 transport stream receives a BCID-stable event seed.

## Event-level audit

EventState SHALL store the actual event transport seed.

The ROOT `events` tree SHALL append:

    geant4_transport_seed

This is a scientific field and SHALL participate in canonical event
comparison.

For each event:

    geant4_transport_seed
      == TransportSeedForStableTuple(seed_base, bcid)

## Metadata

The historical field:

    geant4_master_seed

continues to identify process/run initialization and SHALL NOT be
interpreted as the event transport seed.

Schema 4 SHALL append:

    geant4_transport_seed_policy
    geant4_transport_seed_identity
    geant4_transport_seed_mixer
    geant4_transport_seed_stream
    geant4_transport_seed_max
    geant4_transport_reseed_scope

Frozen values:

    geant4_transport_seed_policy = event-stable-v1
    geant4_transport_seed_identity = bcid
    geant4_transport_seed_mixer = splitmix64-v1
    geant4_transport_seed_stream = transport-event
    geant4_transport_seed_max = 2147483646
    geant4_transport_reseed_scope = event-before-tracking

## ROOT schema

The scientific transport RNG semantics and data contract change.

Therefore:

    3 -> 4

Schema 3 remains historical evidence for Cycle 10 and the
pre-correction Cycle 11 pilot.

No schema-3 file may be relabelled as using the new transport RNG.

## Analyzer compatibility

The canonical ROOT extractor SHALL support:

- schema 2;
- schema 3;
- schema 4.

Post-correction Cycle 11 partition validation SHALL require schema 4.

Historical schema-3 pilot outputs remain valid evidence of the
pre-correction instability, but MUST NOT be mixed with schema-4
validation outputs.

## Required dependency-light tests

Before new physical transport validation, tests SHALL establish:

1. deterministic transport seed;
2. positive transport seed;
3. maximum seed of 2147483646;
4. BCID sensitivity;
5. no worker/thread input;
6. no local-event-ID input;
7. domain separation from Pythia streams;
8. frozen known vectors;
9. EventState reset clears transport seed;
10. ROOT schema version 4;
11. schema-4 metadata recognized;
12. historical schema-3 extraction remains supported;
13. schema-4 events require geant4_transport_seed;
14. canonical partition comparison includes the transport seed.

## First post-correction validation

The first physical validation SHALL reproduce the Stage 11.2B pilot:

    seed_base = 9512
    BCIDs = 11000..11003
    interaction mode = fixed
    fixed interactions = 1
    generator audit = enabled
    beam smearing = non-zero

Compare:

    monolithic 1T

against:

    shard A 1T + shard B 1T

Acceptance requires:

    GENERATOR_EQUAL=YES
    EVENTS_EQUAL=YES
    HITS_EQUAL=YES
    SCIENTIFIC_EQUAL=YES
    FULL_PARTITION_STABILITY=PASS

Only after that result may the wider partition-stability matrix begin.

## Later schema-4 matrix

If the corrected pilot passes, later stages SHALL include:

- exact shard rerun;
- reverse shard execution order;
- all-2T partition;
- mixed 1T/2T partition;
- monolithic 1T versus monolithic 2T;
- Poisson interactions;
- non-zero beam smearing;
- seed sensitivity;
- gap rejection;
- overlap rejection;
- duplicate-BCID rejection.

## Current state

At design freeze:

    PRIMARY_PARTITION_STABILITY=PASS
    TRANSPORT_PARTITION_STABILITY=FAIL
    FULL_PARTITION_STABILITY=FAIL
    TRANSPORT_SEQUENCE_DEPENDENCE_DIAGNOSIS=CONFIRMED
    CYCLE_11_COMPLETE=NO
