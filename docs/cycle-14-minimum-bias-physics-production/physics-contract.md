# Cycle 14.1 — Minimum Bias Physics Production Contract

## Status

This document is the Cycle 14.1 physics-contract freeze candidate.

It does not authorize large-scale physics production by itself.

Baseline commit:

`e4bbde6c12f430e81e2bc843b998ae2ec6b707e2`

## Collision system

- beam A: proton, PDG 2212
- beam B: proton, PDG 2212
- centre-of-mass energy: 14 TeV
- PYTHIA process selection: `SoftQCD:inelastic = on`
- `SoftQCD:all` must remain disabled

## Nominal production profile

- generator: PYTHIA
- bunch crossings: 3000
- first BCID: 0
- interaction distribution: Poisson
- requested mean interactions: 50
- seed base: 512
- initial execution topology: 1 thread
- Geant4 physics list: FTFP_BERT_ATL
- production cut: 1.0 mm
- maximum transported pseudorapidity: |eta| <= 1.8
- neutrino transport: disabled

## Beam-region assumption

The current nominal configuration has:

- beam_sigma_x_mm = 0
- beam_sigma_y_mm = 0
- beam_sigma_z_mm = 0
- beam_sigma_t_ns = 0

Therefore the nominal Cycle 14 production does not claim a validated
experimental luminous-region model.

These values must not be silently replaced by experiment-specific beam
parameters.

## Random-number identity

Primary-generation random identity is event-stable and based on BCID.

The PYTHIA stream is deterministically derived from seed_base, BCID,
subevent and stream identity.

Geant4 transport uses an event-stable BCID-derived transport seed installed
before tracking.

Worker identity, local event identifier, partition boundary and supported
thread topology are not part of the scientific random identity.

## Output contract

The current ROOT schema is schema version 4.

The scientific output contains the trees:

- events
- hits
- generator
- metadata

The metadata records configuration, random policy, software versions and
provenance.

The resolved textual run manifest remains part of the production provenance.

## Reproducibility

Cycle 14 inherits the previously validated partition-stability contract.

Production must preserve global BCID identity and must not introduce
partition-dependent physics.

## Geometry interpretation

The detector is the project's simplified ATLAS/Lorenzetti-like calorimeter
model.

Results must not be described as simulation of the complete official ATLAS
detector geometry.

## Canonical configuration hashes

`config/production.conf`

SHA-256:

`d7f1d56e9ebd8fa67c68c48487caf469f7a8e09516793406c36b3c386dd56db7`

`config/pythia_minbias.cmnd`

SHA-256:

`f746771d0033e8e545a9a75ac8dc7993f2784e180738ce0de582db3cf7226983`

The complete Cycle 14.1 contract-file hash inventory is stored at:

`evidence/physics-contract-files.sha256`

## Production authorization rule

Large-scale minimum-bias production remains forbidden until the complete
Cycle 14.1 freeze gate has passed.

A later change to collision energy, process selection, pile-up distribution,
seed policy, Geant4 physics list, production cut, acceptance, detector
geometry, ROOT scientific schema or beam-region model requires a new contract
revision and explicit validation.
