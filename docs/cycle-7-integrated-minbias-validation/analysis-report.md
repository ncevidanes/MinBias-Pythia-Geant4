# Cycle 7 — Integrated minimum-bias validation report

## 1. Decision

Cycle 7 is **approved**. The three fixed stages completed with exact event
coverage, zero exhausted generation failures, zero unknown PDGs, complete
particle and energy accounting, valid ROOT structure, and reproducible
artifact hashes. Stages 7.2 and 7.3 observed all ten calorimeter samplings and
remained within the five-standard-deviation Poisson acceptance gate.

The detector is ATLAS/Lorenzetti-like and simplified. These results validate
this simulator and must not be presented as official ATLAS performance.

## 2. Scope and provenance

All accepted outputs were produced from Git commit
`6f248fe375b7609cffbdb0f0d3ecb8588efed503` on branch
`cycle-7-integrated-minbias-validation`. The fixed baseline used proton-proton
collisions at 14 TeV, `SoftQCD:inelastic`, Poisson interaction multiplicity,
`FTFP_BERT_ATL`, a 1 mm production cut, `max_abs_eta = 1.8`, disabled neutrino
transport, and one transport thread.

The executor built and tested the project, applied the Stage 7.0A preflight,
ran simulator dry-runs, wrote into a temporary sibling directory, audited and
analyzed the ROOT file without changing its SHA-256, and published each final
directory with one atomic rename.

## 3. Campaign results

| Stage | Purpose | BCs | Poisson mean | Seed | Requested/generated | Failures | Generator particles | Transported particles | Hits | Energy (MeV) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 7.1 | Smoke | 3 | 1 | 512 | 6 / 6 | 0 | 2,055 | 185 | 11,644 | 19,573.1252 |
| 7.2 | Statistical validation | 500 | 2 | 513 | 938 / 938 | 0 | 552,624 | 55,360 | 4,028,007 | 6,723,317.1206 |
| 7.3 | Production | 3,000 | 50 | 512 | 150,378 / 150,378 | 0 | 82,969,737 | 8,213,042 | 594,664,732 | 993,087,270.8209 |
| **Total** | — | **3,503** | — | — | **151,322 / 151,322** | **0** | **83,524,416** | **8,268,587** | **598,704,383** | **999,830,161.0667** |

Generator auditing and overlap checks were enabled for Stages 7.1 and 7.2 and
disabled for the high-statistics Stage 7.3 according to the fixed campaign
contract. Consequently, the Stage 7.3 `generator` tree retains its schema but
contains zero entries; this is expected and was explicitly checked.

## 4. Acceptance gates

All three stages passed the canonical ROOT audit and integrated analyzer. The
following gates were satisfied:

- exact event count and unique identifiers;
- readable, non-zombie, non-recovered ROOT files;
- requested interactions equal generated interactions plus recorded failures;
- zero generation failures and zero unknown PDGs;
- complete generator-particle decision accounting;
- zero unlineaged steps and zero segmentation failures;
- valid hit sampling identifiers and positive finite hit energy;
- event-to-hit energy closure;
- ten ordered sampling rows with hit and energy closure;
- all ten samplings observed;
- unchanged ROOT SHA-256 after structural audit and integrated analysis;
- zero true fatal markers and process exit status zero;
- no temporary campaign directories after atomic publication.

Stage 7.1 treats sampling coverage as structural and the Poisson test as not
applicable, as required by the smoke-stage contract. Its output nevertheless
contained hits in all ten samplings.

## 5. Poisson consistency

| Stage | Requested mean | Requested variance | Poisson z | Contract |
|---|---:|---:|---:|---|
| 7.1 | 2.0000 | 1.0000 | 1.7321 | Not applicable (structural smoke) |
| 7.2 | 1.8760 | 1.6599 | 1.9606 | PASS |
| 7.3 | 50.1260 | 50.4029 | 0.9760 | PASS |

Across all stages, 151,322 interactions were requested against a combined
expectation of 151,003. The descriptive combined deviation is 0.8209 standard
deviations. The production mean and variance are both close to 50, providing
evidence that the configured Poisson multiplicity is operating as intended.

## 6. Calorimeter energy composition

The higher-statistics stages show a stable sampling-level energy composition.
The largest absolute change from Stage 7.2 to Stage 7.3 is 0.1121 percentage
points in `TileExt1`; the total-variation distance is 0.1426 percentage points.
This is a descriptive simulator-level comparison, not a detector-performance
or systematic-uncertainty claim.

| Sampling | Stage 7.2 energy (%) | Stage 7.3 energy (%) | Change (percentage points) |
|---|---:|---:|---:|
| PSB | 2.8602 | 2.8688 | +0.0086 |
| EMB1 | 41.9303 | 41.8665 | -0.0638 |
| EMB2 | 38.4520 | 38.4447 | -0.0074 |
| EMB3 | 2.2087 | 2.1698 | -0.0389 |
| TileCal1 | 4.5383 | 4.5175 | -0.0208 |
| TileCal2 | 0.8094 | 0.8000 | -0.0093 |
| TileCal3 | 0.0335 | 0.0312 | -0.0023 |
| TileExt1 | 8.0304 | 8.1424 | +0.1121 |
| TileExt2 | 1.0859 | 1.1004 | +0.0145 |
| TileExt3 | 0.0512 | 0.0586 | +0.0074 |

The energy fractions sum to unity within floating-point precision in every
stage. The raw 30-row sampling evidence is preserved in
`evidence/sampling_summary.csv`.

## 7. Runtime and memory

| Stage | Wall time | Maximum RSS | ROOT size | PYTHIA error messages | True fatal markers |
|---|---:|---:|---:|---:|---:|
| 7.1 | 26.33 s | 152.61 MiB | 961,113 bytes | 0 | 0 |
| 7.2 | 1,652.21 s | 170.73 MiB | 296,037,524 bytes | 1 | 0 |
| 7.3 | 238,311 s (66:11:51) | 328.94 MiB | 36,224,216,354 bytes | 4 | 0 |

The Stage 7.3 peak RSS remained below both the approximately 492.7 MiB
stress-test reference and the 7 GiB host capacity. Its throughput was about
2,495 hits/s and 1.585 wall-clock seconds per requested interaction. The
one-thread sequential policy was therefore sufficient for the accepted
production, although the ROOT volume remains the dominant storage cost.

The PYTHIA messages were recoverable retry diagnostics. No stage exhausted a
generation attempt: all 151,322 requested interactions were generated and the
recorded generation-failure total is zero.

## 8. Integrity and retained evidence

Full checksum validation passed for Stages 7.1 and 7.2. Stage 7.3 passed a
full checksum validation, including its 36.2 GB ROOT file, during the final
audit; its smaller artifacts were subsequently checked again. The manifest
and checksum registry agree on every ROOT SHA-256.

ROOT files and execution logs remain local under `outputs/` and are excluded
by `.gitignore`. They are not copied into this documentation. The tracked
evidence contains only compact summaries, validation markers, resource and
integrity metadata sufficient to identify the accepted local products.

## 9. Non-blocking observations

- The readiness probe is an auxiliary capacity measurement and is not one of
  the three accepted campaign stages.
- The ROOT-side run manifest records the temporary staging path used before
  atomic publication. The campaign manifest records the final ROOT filename
  and authoritative SHA-256, so this does not affect integrity.
- Absolute host paths in local run metadata are provenance records and are not
  portable configuration recommendations.

## 10. Final conclusion

The Cycle 7 campaign satisfies its physics, computational, schema,
provenance, Poisson, sampling, and transactional-publication contracts. The
integrated PYTHIA-to-Geant4 minimum-bias baseline is accepted for subsequent
analysis and development. No transport rerun is required.
