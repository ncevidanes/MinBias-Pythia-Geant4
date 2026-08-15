# Cycle 6.6 — Hadronic-tail systematic campaign specification

## 1. Objective

Investigate the `TileCal3` outer-tail marker observed for positive pions at
100 GeV in Cycle 6.5. The campaign varies incidence pseudorapidity and the
Geant4 production cut while keeping the incident particle, energy, azimuth,
physics list, event count, thread count, and paired seed set fixed.

Cycle 6.6A established and tested the resolved configuration contract without
transport. Cycle 6.6B adds the transactional executor, paired systematic
aggregator, acceptance logic, and synthetic regression tests required before
the 9,000-event campaign is released.

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

## 5. Stage 6.6B aggregation contract

The full executor first runs the same build, CTest, and 45-case preflight. It
then writes all ROOT files, manifests, per-run CSVs, and logs under a temporary
sibling directory. The requested output directory is published atomically
only after all runs and the aggregation pass. Existing output directories are
never overwritten.

Each ROOT input is hashed before analysis. The analyzer is run twice and both
CSV products must be byte-identical; the ROOT hash must remain unchanged. The
manifest records eta, production cut, paired seed, Git commit, and ROOT SHA-256.

The aggregator requires:

- exact point, run, event, eta, cut, and paired-seed coverage;
- provenance and SHA-256 integrity of every ROOT input;
- deterministic per-run CSV reproduction;
- sampling-fraction closure and nonnegative finite observables;
- paired TileCal3 and TileExt fraction differences relative to eta 0 and
  the 1 mm baseline, including confidence intervals across the five seeds;
- explicit review markers whose thresholds do not silently convert a
  systematic sensitivity into a physics failure.

Across the five paired seeds, two-sided 95% confidence intervals use Student's
`t` distribution with four degrees of freedom. A TileCal3 or TileExt interval
that excludes zero sets `systematic_review=REQUIRED`; it does not fail the
campaign. Likewise, an energy-mean relative CI95 half-width above 3% sets a
precision review marker instead of redefining detector acceptance.

The final aggregate products are:

- `systematic_summary.csv`: nine point-level energy and tail observables;
- `paired_differences.csv`: eight comparisons with the fixed baseline;
- `systematic_validation.txt`: structural PASS gates and review markers;
- `campaign_manifest.tsv`: immutable run-level provenance and ROOT hashes.

Transport is enabled by omitting `--dry-run` only after the 6.6B implementation
has been committed, pushed, and independently revalidated:

```bash
python3 -B scripts/run_hadronic_tail_systematics.py \
  --output-dir outputs/cycle6-stage66-systematics
```

## 6. Scientific limits

This matrix probes numerical and geometry sensitivity inside the simplified
detector only. Production cuts are Geant4 secondary-production thresholds,
not detector calibration parameters. Eta variation changes the traversed
geometry as well as the effective path, so any trend must be interpreted by
region and sampling rather than as a one-dimensional leakage measurement.
The campaign does not establish official ATLAS performance.
