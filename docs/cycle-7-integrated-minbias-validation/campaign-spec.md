# Cycle 7 — Integrated minimum-bias validation specification

## 1. Objective and scope

Cycle 7 transitions from the single-particle validation completed in Cycle 6
to integrated PYTHIA-to-Geant4 minimum-bias production. Stage 7.0A fixes the
physics, execution, ROOT-schema, provenance, and acceptance contracts and
validates them without starting PYTHIA or Geant4 transport.

The detector remains ATLAS/Lorenzetti-like and simplified. Results validate
this simulator and must not be presented as official ATLAS performance.

## 2. Fixed physics contract

| Parameter | Value |
|---|---:|
| Beams | proton-proton |
| Centre-of-mass energy | 14 TeV |
| PYTHIA process | `SoftQCD:inelastic` |
| Interaction multiplicity | Poisson |
| Physics list | `FTFP_BERT_ATL` |
| Production cut | 1 mm |
| Acceptance | `max_abs_eta = 1.8` |
| Beam sigmas | 0 mm and 0 ns |
| Neutrino transport | disabled |
| Threads | 1 |

The zero beam sigmas deliberately avoid introducing an unvalidated luminous
region. Neutrinos remain in the generator audit when enabled but are not
transported in the Cycle 7 baseline.

## 3. Staged campaign matrix

| Stage | Purpose | BCs | Poisson mean | Seed | Generator audit | Overlap check |
|---|---|---:|---:|---:|---|---|
| 7.1 | smoke | 3 | 1 | 512 | yes | yes |
| 7.2 | statistical validation | 500 | 2 | 513 | yes | yes |
| 7.3 | production | 3,000 | 50 | 512 | no | no |

The complete plan contains 3,503 bunch crossings and 151,003 expected
interactions. The latter is an expectation under the Poisson model, not an
event-count acceptance target. Reusing seed 512 in stages 7.1 and 7.3 creates
a deliberate prefix-reproducibility check; seed 513 keeps stage 7.2
statistically independent.

The configurations are `config/smoke.conf`, `config/poisson_mu2.conf`, and
`config/production.conf`. Their current output paths are templates. The Stage
7.0B executor must override them with paths inside a temporary sibling of the
requested campaign directory.

## 4. ROOT contract

Every ROOT file must contain the four TTrees `events`, `hits`, `generator`, and
`metadata`. The Stage 7.0A preflight checks their source definitions and the
complete branch contract. `generator` entries are required when
`generator_audit=true`; the tree and its schema remain present in production
when the audit is disabled to control file size.

The canonical samplings are `PSB`, `EMB1`, `EMB2`, `EMB3`, `TileCal1`,
`TileCal2`, `TileCal3`, `TileExt1`, `TileExt2`, and `TileExt3`.

## 5. Execution and provenance contract

Stages execute sequentially with one transport thread. A future executor must:

- run the Stage 7.0A preflight before transport;
- reject an existing destination directory;
- write ROOT files, logs, manifests, summaries, and hashes to a temporary
  sibling directory;
- publish with one atomic rename only after every gate passes;
- remove incomplete staging data after controlled failure;
- record the resolved configuration, Git commit, software versions, seed,
  ROOT SHA-256, event counts, and peak resident memory;
- never version ROOT files or execution logs.

The known stress-test reference is approximately 492.7 MiB RSS. Stage 7.1
must measure peak RSS before stages 7.2 or 7.3 are authorized. The one-thread
policy and sequential execution are mandatory on the 7 GiB host.

## 6. Acceptance contract

All stages require a readable, non-zombie ROOT file; exact BCID coverage;
finite nonnegative deposited energy; event-to-hit energy closure within
`1e-9`; no duplicate events; no orphan hits; no negative subevent IDs; no
unknown PDGs; no unlineaged steps; no segmentation failures; and consistent
generator/transport decisions.

Stage 7.1 is a structural smoke gate. Stages 7.2 and 7.3 additionally require
all ten samplings and a Poisson interaction-count consistency check. The
requested/generated difference must equal the explicitly recorded generation
failures; a generation failure is never silently discarded.

Physics-review markers remain distinct from computational failure. Regional
energy migration or tail changes require interpretation but do not by
themselves invalidate ROOT integrity.

## 7. Stage 7.0A preflight

Run:

```bash
python3 -B scripts/preflight_integrated_minbias.py \
  --output-dir outputs/cycle7-integrated-minbias
```

The command parses all three configurations with the canonical project
validator, checks the PYTHIA process, ROOT schema, sampling vocabulary, and
campaign matrix, and must leave the prospective output directory absent.
Successful completion ends with:

```text
INTEGRATED_MINBIAS_PREFLIGHT=PASS stages=3 bunch_crossings=3503 expected_interactions=151003 trees=4 samplings=10 threads=1 transport_executed=NO
```

Only after this marker and the Stage 7.0A tests pass may Stage 7.0B implement
the transactional executor and integrated ROOT analyzer.
