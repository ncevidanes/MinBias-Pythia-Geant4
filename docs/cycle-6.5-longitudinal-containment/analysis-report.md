# Cycle 6.5 — Operational longitudinal containment

## Status

**Operational longitudinal-containment validation: PASS**

The analysis was performed with the analyzer versioned in Git commit
`496ce4ae10e21d3cb5e52d12dc740fc45a4cf787`. It derives group energy
fractions and central-path containment samplings from the versioned Cycle 6.4
statistical evidence. No Geant4 transport was rerun for this stage.

The result applies to the fixed matrix of electrons, photons, and positive
pions at 1, 10, and 100 GeV, normal incidence, five independent seeds and
1,000 events per physical point. The source campaign records Git commit
`a7c24f9127a09699234e84399bf307ace29566c3`.

## Acceptance results

| Criterion | Result |
|---|---:|
| Physical points | 9/9 |
| Runs per point | 5 |
| Events per point | 1,000 |
| Sampling rows | 90/90 |
| Sampling-fraction closure | PASS |
| Central path reaches 90% | 9/9 |
| Central path reaches 95% | 9/9 |
| Central path reaches 99% | 9/9 |
| Electron/photon 99% no later than EMB3 | 6/6 |
| Maximum TileExt fraction | 0.473411% |
| Required maximum TileExt fraction | 1.000000% |
| TileExt activity | PASS |
| Maximum TileCal3 fraction | 2.146817% |
| Points above the 1% outer-tail review threshold | 1 |
| Outer-tail follow-up | REQUIRED |

`outer_tail_review=REQUIRED` is a follow-up marker, not a failed acceptance
criterion. The analyzer intentionally treats activity in `TileCal3` as an
outer-tail indicator and not as an estimate of energy escaping the geometry.

## Results by physical point

Fractions below are percentages of the pooled mean deposited energy observed
across all ten samplings. `EM total` includes PSB and EMB1–EMB3; `Tile central`
includes TileCal1–TileCal3. The 90%, 95%, and 99% columns identify the first
sampling on the eta-zero central path that reaches each cumulative threshold.

| Particle | Energy (GeV) | EM total | Tile central | TileExt | TileCal3 | 90% | 95% | 99% | Review |
|---|---:|---:|---:|---:|---:|---|---|---|---:|
| Electron | 1 | 99.9618% | 0.0331% | 0.0051% | 0.0000% | EMB2 | EMB2 | EMB2 | No |
| Electron | 10 | 99.9110% | 0.0802% | 0.0088% | 0.0001% | EMB2 | EMB2 | EMB2 | No |
| Electron | 100 | 99.8495% | 0.1437% | 0.0068% | 0.0002% | EMB2 | EMB2 | EMB2 | No |
| Photon | 1 | 99.9311% | 0.0618% | 0.0071% | 0.0000% | EMB2 | EMB2 | EMB2 | No |
| Photon | 10 | 99.8996% | 0.0928% | 0.0076% | 0.0001% | EMB2 | EMB2 | EMB2 | No |
| Photon | 100 | 99.7793% | 0.2147% | 0.0060% | 0.0003% | EMB2 | EMB2 | EMB3 | No |
| Positive pion | 1 | 81.4194% | 18.1072% | 0.4734% | 0.0141% | TileCal1 | TileCal1 | TileCal2 | No |
| Positive pion | 10 | 57.3934% | 42.2483% | 0.3583% | 0.8364% | TileCal2 | TileCal2 | TileCal3 | No |
| Positive pion | 100 | 46.9984% | 52.8898% | 0.1118% | 2.1468% | TileCal2 | TileCal2 | TileCal3 | Yes |

## Operational interpretation

All electron and photon points reach 99% of their observed deposited energy
by `EMB3`; five of the six reach it by `EMB2`. Their Tile central and TileExt
fractions remain small in this fixed eta-zero matrix.

The pion distributions extend deeper. The 1 GeV point reaches 99% by
`TileCal2`, while the 10 and 100 GeV points reach it in `TileCal3`. The
100 GeV pion point deposits 2.146817% in `TileCal3`, exceeding the predefined
1% review threshold and setting the priority for the next systematic stage.

TileExt contributes at most 0.473411%, below the 1% acceptance limit. This
supports use of the selected central-path ordering for the present normal-
incidence sample, while preserving TileExt as a separately reported region.

## Reproducibility and integrity

The two output files are deterministic products of versioned CSV inputs and
the versioned analyzer. Their SHA-256 hashes, together with those of the
analyzer, specification, and inputs, are recorded in
[`containment_provenance.sha256`](evidence/containment_provenance.sha256).

Versioned evidence:

- [containment summary](evidence/containment_summary.csv);
- [validation markers](evidence/containment_validation.txt);
- [provenance hash manifest](evidence/containment_provenance.sha256).

Reproduce the outputs from a clean checkout of the analyzer commit using a new
destination:

```bash
python3 scripts/analyze_longitudinal_containment.py \
  --summary docs/cycle-6.4-statistical-validation/evidence/statistical_summary.csv \
  --samplings docs/cycle-6.4-statistical-validation/evidence/statistical_samplings.csv \
  --output outputs/cycle6-stage65-repeat/containment_summary.csv \
  --validation outputs/cycle6-stage65-repeat/containment_validation.txt
```

The analyzer refuses pre-existing output paths. On success it prints
`LONGITUDINAL_CONTAINMENT_RESULT=PASS`.

## Scientific limits and next validation step

These are operational fractions of the energy observed inside the simplified
instrumented geometry. They are not calibrated material-depth measurements,
do not include unobserved energy beyond the geometry, and do not establish
official ATLAS calorimeter performance. The Cycle 6.4 tables also do not retain
the event-level covariance required to assign justified confidence intervals
to these derived ratios.

The next stage should focus on the positive-pion 100 GeV outer tail and vary
incidence eta and production cut under controlled seeds. If the 2.146817%
`TileCal3` signal remains stable and no closure or geometry anomaly appears,
the project can proceed to the broader Cycle 7 program.
