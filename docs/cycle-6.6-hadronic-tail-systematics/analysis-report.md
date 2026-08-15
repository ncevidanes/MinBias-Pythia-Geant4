# Cycle 6.6 — Hadronic-tail systematic validation

## 1. Status

The fixed Cycle 6.6 campaign completed successfully at Git commit
`6a4aa8e1913193cd4ed7e3ae76f88ba98037400e`.

```text
HADRONIC_TAIL_AGGREGATION_RESULT=PASS
physical_points=9
runs=45
total_events=9000
paired_seed_count=5
fraction_closure=PASS
root_sha256_integrity=PASS
paired_seed_coverage=PASS
```

The campaign is operationally accepted. Its two `REQUIRED` markers trigger
scientific interpretation and do not represent execution failures:

```text
precision_review_points=7
precision_review=REQUIRED
significant_tilecal3_points=3
significant_tileext_points=7
systematic_review=REQUIRED
```

## 2. Fixed campaign

The incident particle was a positive pion at 100 GeV with phi zero and the
`FTFP_BERT_ATL` physics list. The scan used eta values 0.0, 0.4, and 0.8 and
production cuts 0.1, 1.0, and 10.0 mm. Each point contains 200 events for each
of the same five seeds, 643031 through 643035, permitting paired comparisons
against the eta-zero, 1 mm baseline.

All 45 ROOT inputs were analyzed twice. The two summary products for each run
were byte-identical, and analysis did not change the ROOT SHA-256. Aggregation
then independently checked every ROOT hash, the complete 3 by 3 matrix, the
paired seed set, finite nonnegative observables, and sampling-fraction closure.

## 3. Point-level results

Fractions below are percentages of the observed deposited energy. `Outer sum`
is the derived sum of TileCal3 and TileExt and is used only to distinguish
regional redistribution from a global increase of the outer-tail marker.

| eta | Cut (mm) | Mean deposit (MeV) | Relative CI95 half-width | TileCal3 | TileExt | Outer sum | Precision review |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 0.0 | 0.1 | 11756.811 | 3.893% | 2.0491% | 0.1150% | 2.1640% | yes |
| 0.0 | 1.0 | 11631.439 | 3.960% | 2.1629% | 0.1117% | 2.2745% | yes |
| 0.0 | 10.0 | 11519.453 | 3.447% | 1.9771% | 0.1186% | 2.0957% | yes |
| 0.4 | 0.1 | 12209.733 | 1.922% | 1.4459% | 0.1596% | 1.6055% | no |
| 0.4 | 1.0 | 11961.149 | 3.539% | 1.5644% | 0.1534% | 1.7178% | yes |
| 0.4 | 10.0 | 11912.048 | 3.385% | 1.4240% | 0.1617% | 1.5858% | yes |
| 0.8 | 0.1 | 13116.438 | 4.127% | 0.0931% | 1.6446% | 1.7377% | yes |
| 0.8 | 1.0 | 13147.669 | 4.275% | 0.1024% | 1.7746% | 1.8769% | yes |
| 0.8 | 10.0 | 13013.294 | 2.752% | 0.0934% | 1.7355% | 1.8289% | no |

The largest relative CI95 half-width is 4.275269%, compared with the 3%
review threshold. Seven points therefore require a precision note, but none
exceeds 4.3%. This precision marker concerns the run-level mean deposited
energy; it is separate from the paired confidence intervals for the tail
fractions that address the primary Cycle 6.6 question.

## 4. Paired comparisons

The intervals are nominal two-sided 95% paired Student-t intervals with four
degrees of freedom. Fraction differences are expressed in percentage points.

| eta | Cut (mm) | Delta deposit (MeV) | Delta TileCal3 (pp) | TileCal3 CI95 (pp) | Delta TileExt (pp) | TileExt CI95 (pp) |
|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | 0.1 | +125.373 | -0.1138 | [-0.7323, +0.5047] | +0.0033 | [-0.0079, +0.0145] |
| 0.0 | 10.0 | -111.985 | -0.1858 | [-0.9079, +0.5364] | +0.0070 | [+0.0016, +0.0124] |
| 0.4 | 0.1 | +578.295 | -0.7169 | [-1.4902, +0.0563] | +0.0479 | [+0.0286, +0.0672] |
| 0.4 | 1.0 | +329.710 | -0.5985 | [-1.4730, +0.2761] | +0.0418 | [+0.0305, +0.0530] |
| 0.4 | 10.0 | +280.609 | -0.7389 | [-1.5585, +0.0808] | +0.0501 | [+0.0320, +0.0682] |
| 0.8 | 0.1 | +1484.999 | -2.0698 | [-2.8638, -1.2758] | +1.5330 | [+1.2714, +1.7945] |
| 0.8 | 1.0 | +1516.230 | -2.0605 | [-2.8522, -1.2688] | +1.6629 | [+1.4467, +1.8791] |
| 0.8 | 10.0 | +1381.856 | -2.0695 | [-2.8767, -1.2623] | +1.6238 | [+1.3971, +1.8505] |

At eta zero, neither production-cut variation produces a significant TileCal3
change. The TileExt difference at 10 mm excludes zero, but its absolute size is
only 0.006994 percentage point. It is therefore a small exploratory numerical
sensitivity, not evidence of a materially larger hadronic tail.

At eta 0.4, TileCal3 intervals include zero, while TileExt increases by about
0.042 to 0.050 percentage point. At eta 0.8, all three cuts show a large and
consistent change: TileCal3 falls by about 2.06 percentage points and TileExt
rises by about 1.53 to 1.66 percentage points.

## 5. Interpretation

The eta-0.8 result is a redistribution between detector regions. The baseline
TileCal3 plus TileExt fraction is 2.2745%, whereas the three eta-0.8 outer sums
range from 1.7377% to 1.8769%. TileExt activity increases because the incident
trajectory approaches the simplified central/extended-barrel transition; the
combined marker does not increase.

Consequently, the Cycle 6.5 TileCal3 observation is not robustly driven by the
production cut over 0.1 to 10 mm. TileCal3 must remain a regional last-central-
sampling marker, not an isolated estimate of invisible energy or leakage from
the full detector. Trends with eta combine path-length and geometry changes and
must not be presented as a one-dimensional longitudinal leakage scan.

The significant flags are exploratory nominal 95% intervals. Eight comparisons
were made for each fraction without a family-wise multiplicity correction. The
small eta-zero TileExt flag in particular must not be overinterpreted. The much
larger, cut-consistent eta-0.8 redistribution is the dominant systematic result.

## 6. Precision decision

No immediate rerun is required. Under ideal inverse-square-root scaling, moving
the worst energy interval from 4.275% to 3% would require approximately 406
events per run; 500 events per run would be a reasonable future refinement.
The present 9,000-event campaign is sufficient for the regional tail question,
provided the precision marker remains visible in every downstream use.

## 7. Evidence and storage policy

The versioned evidence contains the compact manifest, point summary, paired
differences, validation markers, execution environment, and SHA-256 catalogue
of all local campaign artifacts. The 45 ROOT files and simulation or analysis
logs remain under `outputs/cycle6-stage66c-systematics/` and are not versioned.

Canonical aggregate hashes:

```text
24a3ac41d539f4446708d04ad15d6391dd9431b935f7146216659a149748559a  campaign_manifest.tsv
5ffe1108d7352fbe099e2125ddae7d3fcc722c3848226c48ff46501f830ab4ec  systematic_summary.csv
13fef5fa222916ac2dfe9678ae6d6e56929876eee756cde1b2c66a15e7f3e815  paired_differences.csv
276a8aad02258a8b109a58da7ba06e793084c73f4734f2a89c3a397742af75af  systematic_validation.txt
```

## 8. Conclusion

Cycle 6.6 is scientifically accepted with documented precision and systematic
review markers. Production-cut variation does not explain the Cycle 6.5
TileCal3 tail. Eta variation reveals geometry-driven migration from TileCal3
to TileExt, while the combined outer fraction remains below the eta-zero
baseline. These findings close the targeted hadronic-tail systematic study for
the simplified geometry without claiming official ATLAS performance.
