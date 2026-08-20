# Cycle 8 — Neutrino transport systematics specification

## 1. Objective and scope

Cycle 8 measures the operational effect of enabling neutrino transport in the
integrated minimum-bias simulator. The comparison is paired: both conditions
use the same PYTHIA process, bunch crossings, seed, thread count, detector,
physics list, acceptance, and generator audit. Only
`transport_neutrinos` and the output path may differ.

The initial 100+100-event comparison is a pilot that validates causality,
accounting, and execution behavior. It is not, by itself, a precision statement
about neutrino production or detector physics. Any larger Stage 8.3 campaign
must have its matrix and acceptance thresholds committed before transport.

The detector remains ATLAS/Lorenzetti-like and simplified. Results validate
this simulator and must not be presented as official ATLAS performance.

## 2. Fixed physics and execution contract

| Parameter | Value |
|---|---:|
| Beams | proton-proton |
| Centre-of-mass energy | 14 TeV |
| PYTHIA process | `SoftQCD:inelastic` |
| Interaction multiplicity | Poisson |
| Mean interactions per BC | 1 |
| Physics list | `FTFP_BERT_ATL` |
| Production cut | 1 mm |
| Acceptance | `max_abs_eta = 1.8` |
| Beam sigmas | 0 mm and 0 ns |
| Seed | 512 |
| Threads | 1 |
| Generator audit | enabled |
| Overlap check | enabled |

One thread is mandatory for the pilot so that worker assignment cannot
confound the paired comparison. Zero beam sigmas retain the validated Cycle 7
baseline.

## 3. Pilot matrix

| Role | Condition | Configuration | BCs | Neutrino transport |
|---|---|---|---:|---|
| smoke | ON | `config/neutrinos_smoke.conf` | 3 | enabled |
| paired | OFF | `config/neutrinos_off_100.conf` | 100 | disabled |
| paired | ON | `config/neutrinos_on_100.conf` | 100 | enabled |

The plan contains 203 transported bunch crossings, of which 200 form the
paired comparison. The smoke run is structural and is excluded from paired
effect estimates.

The OFF and ON configurations must differ only in `transport_neutrinos` and
`output`. The smoke configuration must be an event-count/output variant of the
ON condition. The executor will override template outputs with paths inside a
transactional campaign directory.

## 4. Neutrino decision contract

The supported neutrino PDG codes are `±12`, `±14`, `±16`, and `±18`.
For a final neutrino within acceptance and with a Geant4 definition:

- OFF must record `accepted_for_transport = 0` and rejection code
  `kNeutrinoDisabled = 2`;
- ON must record `accepted_for_transport = 1` and rejection code
  `kAccepted = 0`;
- ON `transported_particles` must equal OFF `transported_particles` plus the
  number of eligible neutrinos;
- non-neutrino generator decisions must remain identical between conditions.

The generator record is the authoritative source for eligibility. A neutrino
outside `|eta| <= 1.8`, non-final particle, or unknown PDG definition is not an
eligible switched particle.

## 5. Paired ROOT and accounting contract

Both ROOT files must contain `events`, `hits`, `generator`, and `metadata`.
The pair must have identical event and BCID coverage and identical requested
and generated interaction counts. Generation failures, generator-particle
counts, non-neutrino rejection counters, unknown PDGs, unlineaged steps, and
segmentation failures must agree event by event.

The following conditions are computational failures:

- unreadable, missing, empty, or zombie ROOT file;
- duplicate/missing events or BCID mismatch;
- requested interactions not equal to generated interactions plus recorded
  failures;
- negative or non-finite deposited energy;
- event-to-hit energy-closure failure;
- orphan hits or negative subevent IDs;
- unknown PDGs, unlineaged steps, or segmentation failures;
- divergence in generator content not explained exclusively by the neutrino
  switch;
- absence of at least one eligible neutrino in the 100-BC pilot pair.

Energy deposits and hits are compared rather than assumed identical. Any
nonzero difference must be reported with absolute and relative metrics and
traced to the paired event. It is not silently classified as either failure or
physics effect before inspection.

## 6. Resource and provenance contract

Each run records Git commit, resolved configuration, software versions, seed,
wall time, user/system time, peak RSS, ROOT SHA-256, and artifact hashes. Runs
are sequential and use `/usr/bin/time -v`.

The eventual executor must reject an existing destination, write into a
temporary sibling directory, publish with one atomic rename only after every
gate passes, and remove incomplete staging data after controlled failure.
ROOT files and logs remain under `outputs/` and are never versioned.

## 7. Stage 8.0B preflight

Run without transport:

```bash
python3 -B scripts/preflight_neutrino_transport.py \
  --output-dir outputs/cycle8-neutrino-transport
```

The command validates the three configurations, the unique OFF/ON difference,
the smoke relationship, the PYTHIA process, the neutrino-classification source
contract, ROOT decision fields, and absence of the prospective output. It must
end with:

```text
NEUTRINO_TRANSPORT_PREFLIGHT=PASS runs=3 bunch_crossings=203 paired_bunch_crossings=200 seed=512 threads=1 transport_executed=NO
```

Only after this marker and the complete CTest suite pass may an executor and a
paired ROOT analyzer be implemented. Transport remains unauthorized until
those components have synthetic tests, a clean tracked worktree, and a
separate execution gate.

## 8. Interpretation boundary and Stage 8.3

The pilot answers whether the switch changes the intended particle decisions,
transport count, resource use, hits, and energy within this implementation. It
does not estimate a universal neutrino rate.

After the pilot, Stage 8.3 may be specified to obtain a larger eligible-neutrino
sample. Its event count, seeds, stopping rule, primary metrics, and thresholds
must be fixed in a new committed contract before examining those production
results. This prevents an observed pilot fluctuation from being promoted into
an unplanned statistical claim.
