# Cycle 6.4 — Multi-seed statistical validation

## Status

**Statistical operational validation: PASS**

The campaign was executed from Git commit
`a7c24f9127a09699234e84399bf307ace29566c3` on branch `cycle-6.4-statistical-validation`.

It comprises nine particle-energy points, five independent seeds per point,
45 Geant4 runs, and 9,000 simulated events. Every run used one simulation
thread and 200 events.

This checkpoint validates statistical precision, seed independence, campaign
integrity, analysis repeatability, provenance, and predefined operational
invariants for the simplified calorimeter. It is not an absolute calibration
or a quantitative validation against ATLAS or Lorenzetti reference data.

## Acceptance results

| Criterion | Result |
|---|---:|
| Physical points | 9/9 |
| Independent runs | 45/45 |
| Seeds per point | 5 |
| Globally unique seeds | 45/45 |
| Events per run | 200 |
| Total simulated events | 9,000 |
| Sampling rows | 90 |
| ROOT files | 45 |
| Maximum relative CI95 half-width | 2.060799% |
| Required maximum | 3.000000% |
| CI95 precision | PASS |
| Mean deposit monotonic with energy | Yes |
| Elapsed wall time | 2h 19min 33s |

## Statistical method

The aggregator combines the event counts, means, and sample standard
deviations from the five independent runs at each physical point. It uses the
pooled sample variance, the standard error of the pooled mean, and a two-sided
95% confidence interval with the normal approximation
(`z = 1.959963984540054`).

The predefined precision criterion requires the CI95 half-width divided by the
pooled mean deposited energy to be at most 3% at every physical point. The
largest observed value is 2.060799%, at positive pions with
100 GeV, so the campaign passes with a margin of
0.939201 percentage points.

## Aggregate results

| Particle | PDG | Energy (GeV) | Events | Mean deposit (MeV) | Mean response | Relative resolution | Relative CI95 half-width | Seed-mean CV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Electron | 11 | 1 | 1000 | 241.873163 | 0.241873163 | 0.0612924433 | 0.00379887518 | 0.00121469371 |
| Electron | 11 | 10 | 1000 | 2328.91884 | 0.232891884 | 0.022422434 | 0.00138973132 | 0.00120521946 |
| Electron | 11 | 100 | 1000 | 22776.6327 | 0.227766327 | 0.0087081206 | 0.000539724989 | 0.000312240917 |
| Photon | 22 | 1 | 1000 | 237.733407 | 0.237733407 | 0.0638760789 | 0.00395900764 | 0.00351791152 |
| Photon | 22 | 10 | 1000 | 2305.61471 | 0.230561471 | 0.0246212273 | 0.00152601143 | 0.00201999962 |
| Photon | 22 | 100 | 1000 | 22640.1034 | 0.226401034 | 0.0186804263 | 0.00115780354 | 0.00146038869 |
| Positive pion | 211 | 1 | 1000 | 203.804563 | 0.203804563 | 0.287823087 | 0.0178391319 | 0.0244037345 |
| Positive pion | 211 | 10 | 1000 | 1354.94892 | 0.135494892 | 0.325100041 | 0.020149539 | 0.0127236211 |
| Positive pion | 211 | 100 | 1000 | 11631.4387 | 0.116314387 | 0.332496892 | 0.0206079922 | 0.0318921941 |

The complete machine-readable results are available in the
[statistical summary](evidence/statistical_summary.csv) and
[sampling table](evidence/statistical_samplings.csv).

## Observations

Mean deposited energy increases monotonically from 1 to 100 GeV for electrons,
photons, and positive pions.

Electrons and photons have similar response magnitudes. Their relative
resolution improves as incident energy increases. Positive pions show lower
response and much wider fluctuations, consistent with the qualitative behavior
expected from hadronic showers in a simplified non-compensating calorimeter.

Seed-to-seed variability is small for the electromagnetic points and larger for
positive pions. The largest seed-mean coefficient of variation occurs for the
100 GeV pion point. These are descriptive operational observations and do not
establish detector-performance claims.

## Reproducibility and integrity

The evidence manifest records SHA-256 hashes for 277 local campaign
artifacts, comprising all 275 files under `outputs/cycle6-stage64c`, the general
console log, and the captured execution environment. Their aggregate size is
267.1 MiB.

SHA-256 of the artifact hash manifest:

```text
845cd67c097fe79da972d35bf20fc00bfb5f070b4d2b0ffb2ec940f003d650e1
```

The 45 ROOT files and all execution logs are intentionally excluded from
version control. Their hashes remain in
[`campaign_artifacts.sha256`](evidence/campaign_artifacts.sha256), allowing the
preserved local files to be checked without committing binary outputs.

Versioned evidence:

- [campaign manifest](evidence/campaign_manifest.tsv);
- [statistical validation markers](evidence/statistical_validation.txt);
- [execution environment](evidence/campaign_environment.txt);
- [statistical summary](evidence/statistical_summary.csv);
- [statistical sampling table](evidence/statistical_samplings.csv).

## Execution environment

| Component | Version |
|---|---|
| Operating system | Linux 7.0.0-29-generic x86_64 |
| CMake | cmake version 4.2.3 |
| C++ compiler | c++ (conda-forge gcc 14.3.0-16) 14.3.0 |
| ROOT | 6.36.06 |
| Geant4 | 11.3.2 |
| Pythia | 8.312 |

The environment was captured at `2026-08-13T12:27:47Z`, after the
campaign, in the same activated software environment used for consolidation.
The ROOT metadata and per-run manifests remain the authoritative embedded
provenance for each simulation.

## Reproduction

From a clean checkout of the provenance commit, with a new output destination:

```bash
./scripts/run_statistical_single_particle_campaign.py \
  --output-dir outputs/cycle6-stage64c-repeat \
  --build-jobs 2
```

The executor refuses pre-existing destinations. Reproducing byte-identical
ROOT files can depend on the software stack, platform, and runtime environment
documented above.

## Scientific limits and next validation step

This campaign tests only three particle species, three energies, normal
incidence (`eta = 0`, `phi = 0`), one physics list, and one production cut. The
confidence intervals quantify Monte Carlo precision for the simulated mean
deposits; they do not quantify geometry, physics-model, calibration, or
experimental systematic uncertainties.

The next physical-validation stage should investigate longitudinal containment
and sampling-energy fractions, especially for positive pions, before extending
the matrix in eta, production cut, and physics configuration or comparing with
external reference data.
