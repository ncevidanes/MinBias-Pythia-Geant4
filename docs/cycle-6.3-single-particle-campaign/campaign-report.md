# Cycle 6.3D — Single-particle validation campaign

## Status

**Operational validation: PASS**

The campaign was executed from Git commit
`a77bb1f9f36a7131cfb06eecf4e5a621d702ed20`.

It comprises nine Geant4 runs and 900 simulated events:

- electrons (`PDG 11`);
- photons (`PDG 22`);
- positive pions (`PDG 211`);
- kinetic energies of 1, 10, and 100 GeV;
- 100 events per particle-energy point.

This result validates the campaign executor, output structure, analysis
repeatability, provenance records, and predefined operational invariants. It
does not, by itself, constitute a complete calibration or physical validation
of the calorimeter model.

## Acceptance results

| Criterion | Result |
|---|---:|
| Campaign cases completed | 9/9 |
| Events per case | 100 |
| Total simulated events | 900 |
| Case analyses passed | 9/9 |
| Sampling rows per case | 10 |
| Repeated analysis | Byte-identical |
| ROOT files modified by analysis | No |
| Mean deposit monotonic with energy | Yes |
| ROOT files produced | 9 |

## Aggregate results

The response and relative-resolution values below are the operational metrics
calculated by the campaign analyzer.

| Particle | PDG | Energy (GeV) | Seed | Events | Hits | Mean deposit (MeV) | Mean response | Relative resolution |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Electron | 11 | 1 | 631001 | 100 | 5,118 | 242.946713 | 0.242946713 | 0.0636111701 |
| Electron | 11 | 10 | 631002 | 100 | 15,643 | 2317.79405 | 0.231779405 | 0.0218625155 |
| Electron | 11 | 100 | 631003 | 100 | 56,456 | 22744.7414 | 0.227447414 | 0.00969665945 |
| Photon | 22 | 1 | 632001 | 100 | 4,505 | 235.745870 | 0.235745870 | 0.0570378293 |
| Photon | 22 | 10 | 632002 | 100 | 14,714 | 2306.00079 | 0.230600079 | 0.0231986073 |
| Photon | 22 | 100 | 632003 | 100 | 51,725 | 22579.5592 | 0.225795592 | 0.0141031679 |
| Positive pion | 211 | 1 | 633001 | 100 | 15,574 | 201.386743 | 0.201386743 | 0.294940401 |
| Positive pion | 211 | 10 | 633002 | 100 | 86,548 | 1444.80188 | 0.144480188 | 0.299732042 |
| Positive pion | 211 | 100 | 633003 | 100 | 195,822 | 11295.9747 | 0.112959747 | 0.338147951 |

The complete machine-readable table is available in the
[campaign summary](evidence/campaign_summary.csv).

## Observations

Mean deposited energy increases monotonically from 1 to 100 GeV for all three
particle species.

Electrons and photons have responses of similar magnitude. Their reported
relative resolution improves as the incident energy increases.

Positive pions show a lower response and substantially larger fluctuations.
Their response decreases across the three tested energies, while the reported
relative resolution remains close to 30–34%. These results motivate dedicated
studies of longitudinal and transverse containment, passive-material losses,
sampling behavior, and event-level shower fluctuations.

These observations are descriptive. The present sample size is not sufficient
to establish precision performance claims.

## Reproducibility and integrity

The campaign recorded 59 artifacts with an aggregate local size of
approximately 28 MiB. Their hashes are listed in
[`campaign_artifacts.sha256`](evidence/campaign_artifacts.sha256).

SHA-256 of that hash manifest:

```text
66032ada4b7e7d12f85ab0734ee46cd07e3a774b2a6cfa84a00242567d521394
```

The nine ROOT files and execution logs are intentionally excluded from version
control. Their hashes remain recorded in the textual evidence, allowing the
preserved local artifacts to be checked without committing binary results.

Additional evidence:

- [campaign manifest](evidence/campaign_manifest.tsv);
- [campaign validation markers](evidence/campaign_validation.txt);
- [execution environment](evidence/campaign_environment.txt);
- [aggregate campaign summary](evidence/campaign_summary.csv).

## Execution environment

| Component | Version |
|---|---|
| Operating system | Linux 7.0.0-29-generic x86_64 |
| CMake | 4.2.3 |
| C++ compiler | conda-forge GCC 14.3.0 |
| ROOT | 6.36.06 |
| Geant4 | 11.3.2 |
| Pythia | 8.312 |

The environment was captured at `2026-08-11T16:22:03Z`.

## Reproduction

From a clean checkout of the provenance commit, with the output destination
absent:

```bash
./scripts/run_single_particle_campaign.sh --build-jobs 2
```

Reproducing byte-identical ROOT files can depend on the software stack,
platform, and runtime environment documented above.

## Limitations and next validation step

The campaign uses only 100 events and one deterministic seed per
particle-energy point. It verifies execution and internal consistency but does
not yet quantify statistical uncertainty, seed dependence, calibration
accuracy, or agreement with external reference data.

The next physical-validation stage should increase the event sample, repeat
each point with independent seeds, and investigate pion containment and
energy-loss contributions by calorimeter sampling.
