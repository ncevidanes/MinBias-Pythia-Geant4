# Cycle 6.6 — Hadronic-tail systematic campaign specification

## 1. Objective

Investigate the `TileCal3` outer-tail marker observed for positive pions at
100 GeV in Cycle 6.5. The campaign varies incidence pseudorapidity and the
Geant4 production cut while keeping the incident particle, energy, azimuth,
physics list, event count, thread count, and paired seed set fixed.

Cycle 6.6A establishes and tests the resolved configuration contract only.
It intentionally blocks transport until the systematic aggregator and its
acceptance logic are versioned in the next stage.

## 2. Fixed physics contract

| Parameter | Value |
|---|---:|
| Particle | positive pion |
| PDG | 211 |
| Kinetic energy | 100 GeV |
| Phi | 0 |
| Physics list | `FTFP_BERT_ATL` |
| Threads | 1 |
| Events per run | 200 |
| Runs per point | 5 |
| Seeds | 643031–643035 |

The five seeds are the Cycle 6.4 positive-pion 100 GeV seeds. The same seed
set is reused at every systematic point to support paired comparisons and an
exact baseline contract at eta zero and a 1 mm production cut.

## 3. Systematic matrix

| Variable | Values |
|---|---|
| `single_particle_eta` | 0.0, 0.4, 0.8 |
| `production_cut_mm` | 0.1, 1.0, 10.0 mm |

The Cartesian product contains nine physical configurations, 45 runs and
9,000 transported events. Eta zero is the Cycle 6.5 reference direction;
0.4 probes the central-barrel response; 0.8 approaches the central/extended
barrel transition represented by the simplified geometry. The production-cut
values form a decade scan around the 1 mm baseline.

## 4. Stage 6.6A contract

The executable gains a validated `--production-cut-mm` override. The ROOT
single-particle analyzer propagates `production_cut_mm` from the metadata tree
to each per-run summary CSV so subsequent aggregation cannot infer the cut
from a filename.

The preflight executor must verify all 45 fully resolved configurations and
must not create the prospective output directory or start Geant4 transport.
Run it with:

```bash
python3 -B scripts/run_hadronic_tail_systematics.py \
  --dry-run \
  --output-dir outputs/cycle6-stage66-systematics
```

Successful completion prints:

```text
HADRONIC_TAIL_SYSTEMATICS_PREFLIGHT=PASS points=9 runs=45 runs_per_point=5 events_per_run=200 total_events=9000 paired_seeds=5
```

## 5. Acceptance gates for later stages

Before transport is enabled, Cycle 6.6B must add transactional aggregation
and tests for:

- exact point, run, event, eta, cut, and paired-seed coverage;
- provenance and SHA-256 integrity of every ROOT input;
- deterministic per-run CSV reproduction;
- sampling-fraction closure and nonnegative finite observables;
- paired TileCal3 and TileExt fraction differences relative to eta 0 and
  the 1 mm baseline, including confidence intervals across the five seeds;
- explicit review markers whose thresholds do not silently convert a
  systematic sensitivity into a physics failure.

## 6. Scientific limits

This matrix probes numerical and geometry sensitivity inside the simplified
detector only. Production cuts are Geant4 secondary-production thresholds,
not detector calibration parameters. Eta variation changes the traversed
geometry as well as the effective path, so any trend must be interpreted by
region and sampling rather than as a one-dimensional leakage measurement.
The campaign does not establish official ATLAS performance.
