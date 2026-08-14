# Cycle 6.5 — Operational longitudinal containment specification

## 1. Objective

Derive reproducible, explicitly operational containment metrics from the
versioned Cycle 6.4 statistical evidence without rerunning the 45 Geant4 jobs.
The analysis groups the ten sampling means, verifies energy-fraction closure,
and identifies the first central-barrel sampling that accumulates 90%, 95%, and
99% of the total observed deposited energy.

This stage does not claim calibrated calorimeter depth or measure energy that
escaped the instrumented geometry.

## 2. Inputs

The analyzer consumes the two versioned Cycle 6.4 tables:

- `statistical_summary.csv`: nine physical points and their pooled total means;
- `statistical_samplings.csv`: ten sampling means for each physical point.

Both inputs must contain the fixed matrix of electrons, photons, and positive
pions at 1, 10, and 100 GeV. Their Git commit, particle labels, run counts,
event counts, sampling identities, means, and fractions must agree.

## 3. Geometry-aware grouping

The analysis uses these groups:

| Metric | Sampling membership | Interpretation |
|---|---|---|
| PSB | PSB | presampler activity |
| EMB | EMB1–EMB3 | electromagnetic barrel activity after PSB |
| EM total | PSB and EMB1–EMB3 | all electromagnetic-barrel activity |
| Tile central | TileCal1–TileCal3 | central Tile barrel activity |
| Tile extended | TileExt1–TileExt3 | activity outside the eta-zero central path |
| Central path | PSB–EMB3 and TileCal1–TileCal3 | radial eta-zero instrumented path |
| Outer central | TileCal3 | activity in the last active central radial sampling |

`TileExt` is not appended to `TileCal3` as a later longitudinal layer. The
extended barrel occupies a different z region. Its fraction is reported
separately and must remain small enough for the eta-zero central-path metric to
be meaningful.

## 4. Operational containment definition

For each point, sampling fractions are recomputed from the pooled mean energy:

```text
sampling fraction = sampling mean deposited energy / total mean deposited energy
```

The central cumulative fraction is evaluated in this order:

```text
PSB -> EMB1 -> EMB2 -> EMB3 -> TileCal1 -> TileCal2 -> TileCal3
```

The 90%, 95%, or 99% operational containment sampling is the first member of
that sequence whose cumulative fraction reaches the corresponding threshold.
The denominator includes energy observed in all ten samplings, including
`TileExt`.

The `TileCal3` fraction is an outer-tail indicator. It can flag a point for
further study, but it is not an estimator of invisible leakage beyond the
geometry.

## 5. Acceptance criteria

The analyzer passes only when:

- the input contains exactly nine summary rows and 90 sampling rows;
- every point contains five runs and 1,000 events from the Cycle 6.4 campaign;
- every point has the canonical ten sampling names and indices;
- sampling means and fractions close to the total within `1e-9`;
- the 90%, 95%, and 99% thresholds are reached on the central path;
- electron and photon points reach 99% no later than `EMB3`;
- `TileExt` activity is at most 1% at every eta-zero point;
- outputs are created transactionally and pre-existing outputs are rejected.

A `TileCal3` fraction above 1% emits `outer_tail_review=REQUIRED` but does not
invalidate the operational analysis. It defines the priority for the following
systematic-validation stage.

## 6. Outputs

The analyzer writes:

- `containment_summary.csv`: one row per physical point with group fractions,
  containment samplings, closure error, and the outer-tail flag;
- `containment_validation.txt`: machine-readable acceptance markers and extrema.

Floating-point reductions that affect validation or versioned output use
`math.fsum`. This avoids the version-dependent result of Python's built-in
`sum` algorithm and makes the CSV serialization stable across supported Python
versions for byte-level reproducibility checks.

Suggested local execution:

```bash
python3 scripts/analyze_longitudinal_containment.py \
  --summary docs/cycle-6.4-statistical-validation/evidence/statistical_summary.csv \
  --samplings docs/cycle-6.4-statistical-validation/evidence/statistical_samplings.csv \
  --output outputs/cycle6-stage65a/containment_summary.csv \
  --validation outputs/cycle6-stage65a/containment_validation.txt
```

## 7. Statistical and scientific limits

The group fractions are ratios of pooled means. The versioned Cycle 6.4 tables
do not preserve the covariance between sampling energy and total energy, so the
analyzer does not invent confidence intervals for those ratios. Cycle 6.4
already quantifies precision for the pooled total mean.

The present matrix is limited to eta and phi equal to zero, one production cut,
and one physics list. It cannot establish ATLAS performance, absolute
calibration, material-depth containment, or systematic uncertainty. Those
questions require additional simulations or external reference data.
