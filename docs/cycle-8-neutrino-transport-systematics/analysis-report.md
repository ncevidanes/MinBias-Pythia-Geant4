# Cycle 8 — Neutrino transport pilot report

## 1. Decision

The fixed Cycle 8 pilot is **approved**. The smoke run and the paired OFF/ON
conditions completed transactionally from Git commit `56d44bdb8be06fa9ec416d9de8d1c35af7083d2a`. All
three ROOT files passed the canonical audit, the complete generator records
were paired, particle accounting closed globally and event by event, and all
recorded artifact hashes passed verification.

This is a causal implementation pilot, not a precision measurement of neutrino
production or official ATLAS detector performance. The detector remains
ATLAS/Lorenzetti-like and simplified.

## 2. Fixed scope and provenance

The accepted campaign used proton-proton collisions at 14 TeV,
`SoftQCD:inelastic`, Poisson mean 1, seed 512, one thread, `FTFP_BERT_ATL`, a
1 mm production cut, `max_abs_eta = 1.8`, generator auditing, and overlap
checking. The paired configurations differed only in the neutrino switch and
output path.

| Role | Condition | BCs | Neutrino transport |
|---|---|---:|---|
| Smoke | ON | 3 | Enabled |
| Paired | OFF | 100 | Disabled |
| Paired | ON | 100 | Enabled |

The campaign transported 203 bunch crossings, of which 200 form 100 exact
OFF/ON pairs.

## 3. Particle-decision result

The pair contained 55114 generator records per
condition. One final neutrino inside acceptance was eligible for the switch.
Four additional final neutrinos were outside `|eta| <= 1.8`; they migrated from
the OFF neutrino-disabled category to the ON outside-acceptance category and
were not transported.

| Metric | OFF | ON | ON − OFF |
|---|---:|---:|---:|
| Transported particles | 5401 | 5402 | 1 |
| Eligible neutrinos | — | 1 | 1 |
| Outside-acceptance neutrinos | — | 4 | Not transported |

The transported-particle delta is exactly equal to the eligible-neutrino count
globally and event by event. All non-neutrino decisions remained paired.

## 4. Energy and hit comparison

| Metric | OFF | ON | Difference |
|---|---:|---:|---:|
| Total energy (MeV) | 650664.8847771642 | 650664.8847771642 | 0 |
| Hit count | 396241 | 396241 | 0 |
| Changed hit cells | — | — | 0 |
| Hit-energy L1 (MeV) | — | — | 0 |
| Maximum cell difference (MeV) | — | — | 0 |

Within this fixed pilot, enabling transport for the single eligible neutrino
produced no recorded calorimeter energy or hit difference. This zero is an
observed pilot result and must not be generalized into a universal neutrino
interaction or detector-response claim.

## 5. Controlled analyzer correction

The first paired analysis rejected 104 otherwise identical generator records.
A field-level audit proved that all 104 differences were `eta = +inf` in both
conditions, corresponding to identical non-finite kinematics; there were zero
finite or integer-field differences.

Commit `56d44bdb8be06fa9ec416d9de8d1c35af7083d2a` introduced a generator-specific comparator that treats
matching NaNs as equivalent and infinities as equivalent only when their signs
match. Energy, metadata, hit, geometry, and acceptance checks were not relaxed.
The preserved ROOT pair then passed, and the complete transactional campaign
was repeated successfully from the corrected commit.

## 6. Runtime and storage

| Role | Condition | BCs | Wall time | Maximum RSS | ROOT size (bytes) |
|---|---|---:|---:|---:|---:|
| smoke | ON | 3 | 17.94 s | 152.77 MiB | 961,139 |
| paired | OFF | 100 | 149.24 s | 160.99 MiB | 29,244,959 |
| paired | ON | 100 | 162.07 s | 160.75 MiB | 29,244,869 |
| **Total/peak** | — | **203** | **329.25 s** | **160.99 MiB** | **59,450,967** |

Runs were sequential and used one transport thread. Resource values come from
`/usr/bin/time -v`; their compact hashes and summaries are retained as
versioned evidence while raw logs remain local.

## 7. Acceptance and integrity

The following gates passed:

- exact metadata, event, BCID, and generator-record pairing;
- requested/generated interaction accounting;
- zero unknown PDGs, unlineaged steps, and segmentation failures;
- exact neutrino eligibility and transported-particle deltas;
- finite non-negative energy and event-to-hit energy closure;
- immutable ROOT SHA-256 across audit and analysis;
- three canonical ROOT-audit markers;
- paired analysis and product validation;
- full campaign checksum verification;
- atomic final-directory publication and zero residual staging directories.

ROOT files, simulation logs, resource logs, audit logs, console logs, and
diagnostic directories remain excluded from Git. The tracked evidence contains
only compact tables, validation markers, and checksum registries.

## 8. Interpretation boundary and next stage

The pilot establishes that the switch operates causally and that the current
single eligible neutrino causes no recorded calorimeter difference. The sample
is too small for a precision estimate of neutrino frequency or detector
effects.

A larger Stage 8.3 campaign is optional. If pursued, its seeds, event count,
stopping rule, primary metrics, and thresholds must be committed before
transport. No additional transport is required to approve this fixed pilot.

## 9. Conclusion

The Cycle 8 neutrino-transport pilot satisfies its configuration, execution,
ROOT, provenance, particle-accounting, comparison, and transactional integrity
contracts. The pilot is accepted and its final outputs require no rerun.
