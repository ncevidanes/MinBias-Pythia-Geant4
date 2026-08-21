# Cycle 8.3 — Neutrino transport production report

## 1. Decision

The fixed-budget Cycle 8.3 production campaign is **approved**. All six
transport runs, six canonical ROOT audits, three paired analyses, aggregate
validation, checksum verification, and transactional publication passed from
Git commit `f5be2f662ac08050773ddd839310e5284bf8e822`.

The aggregate contains 3,000 exact OFF/ON event pairs across the precommitted
seeds 1512, 2512, and 3512. Its eligible-neutrino sample is classified as
`DESCRIPTIVE` by the threshold frozen before transport.

## 2. Scope and provenance

Each seed used 1,000 OFF and 1,000 ON bunch crossings, one transport thread,
Poisson mean 1, proton-proton collisions at 14 TeV, `SoftQCD:inelastic`,
`FTFP_BERT_ATL`, a 1 mm production cut, `max_abs_eta = 1.8`, generator
auditing, and overlap checking.

The total executed transport budget was 6,000 bunch crossings. The primary
paired sample contains 3,000 unique `(seed, event, bcid)` keys. Seed 512 from
the implementation pilot is not pooled into this production estimate.

## 3. Neutrino eligibility and particle accounting

| Seed | Eligible | Outside acceptance | Transported delta | Energy absolute delta (MeV) | Changed hit cells |
|---:|---:|---:|---:|---:|---:|
| 1512 | 25 | 41 | 25 | 0 | 0 |
| 2512 | 26 | 44 | 26 | 0 | 0 |
| 3512 | 29 | 57 | 29 | 0 | 0 |
| **Total** | **80** | **142** | **80** | **0** | **0** |

The aggregate eligible frequency is 2.6667% per paired bunch
crossing. The outside-acceptance final-neutrino frequency is
4.7333% per paired bunch crossing. These are descriptive
frequencies for the fixed simulated configuration.

The ON-minus-OFF transported-particle delta is exactly 80, equal to the
eligible-neutrino count globally and event by event. Generator content,
non-neutrino decisions, event identity, and BCID identity remained paired.

## 4. Energy and calorimeter response

| Metric | OFF | ON | Difference |
|---|---:|---:|---:|
| Total deposited energy (MeV) | 20890822.160133298 | 20890822.160133298 | 0 |
| Hit count | 12388417 | 12388417 | 0 |
| Energy-changed events | — | — | 0 |
| Hit-count-changed events | — | — | 0 |
| Changed hit cells | — | — | 0 |
| Hit-energy L1 (MeV) | — | — | 0 |
| Maximum cell delta (MeV) | — | — | 0 |

No deposited-energy, hit-count, or hit-cell difference was recorded across
the 3,000 paired events. This is an observed result for this simplified
ATLAS/Lorenzetti-like configuration, not a universal statement about neutrino
interactions or official ATLAS detector performance.

## 5. Runtime, memory, and storage

| Seed | Condition | Wall time (s) | Maximum RSS (MiB) | ROOT size (MiB) |
|---:|---|---:|---:|---:|
| 1512 | OFF | 1758.90 | 170.19 | 300.27 |
| 1512 | ON | 1581.25 | 169.66 | 300.27 |
| 2512 | OFF | 1636.22 | 169.16 | 279.42 |
| 2512 | ON | 1646.65 | 169.02 | 279.42 |
| 3512 | OFF | 1391.36 | 169.49 | 291.60 |
| 3512 | ON | 1379.09 | 169.68 | 291.60 |

The six sequential runs required 9393.47 seconds
(2 h 36 min 33.47 s). OFF conditions totaled 4786.48 seconds and ON
conditions totaled 4606.99 seconds. The observed total differed from
the preflight estimate by +0.58%.

The six ROOT files occupy 1,827,226,379 bytes
(1.702 GiB), differing from the planning
estimate by +4.13%. OFF ROOTs total
913,613,768 bytes and ON ROOTs total 913,612,611 bytes. Peak RSS
was 170.19 MiB.

Runtime differences between paired conditions are reported operationally and
are not interpreted as a physics effect.

## 6. Computational integrity

The following gates passed:

- the fixed six-run matrix and stopping rule;
- 3,000 unique and ordered `(seed, event, bcid)` keys;
- exact metadata, event, BCID, and generator pairing;
- exact particle accounting per event, seed, and aggregate;
- zero generation failures, unknown PDGs, unlineaged steps, and segmentation
  failures;
- finite non-negative energy and event-to-hit energy closure;
- six canonical ROOT audits and three paired analyses;
- immutable SHA-256 hashes for all campaign artifacts;
- atomic publication with zero residual temporary directories.

The compact evidence retains the campaign manifest, aggregate and seed
summaries, resource summary, validation markers, ROOT registries, and artifact
hashes. ROOT data, simulation logs, ROOT-audit logs, resource logs, and the
3,000-row event table remain under `outputs/` and are not versioned.

## 7. Post-run storage recovery

After successful atomic publication, the external volume temporarily became
unavailable to a later audit shell. The campaign itself had already completed
with status zero. The volume was recovered without rerunning transport, all
campaign checksums passed, and the scientific audit was repeated from the
safe working directory `/tmp`.

No evidence of campaign-data mutation or corruption was observed.

## 8. Interpretation boundary

The precommitted `DESCRIPTIVE` label is an internal sample-adequacy category,
not an inferential confidence statement. The results characterize only the
fixed seeds, generator configuration, acceptance, simplified detector, and
software commit documented here.

The observed zero calorimeter difference is reported rather than assumed.
No universal neutrino-production rate, neutrino interaction probability, or
official detector-performance claim is authorized.

## 9. Conclusion

Cycle 8.3 satisfies its fixed-budget, provenance, transport, ROOT, pairing,
particle-accounting, resource, checksum, and transactional-publication
contracts. The production result is accepted and requires no transport rerun.
