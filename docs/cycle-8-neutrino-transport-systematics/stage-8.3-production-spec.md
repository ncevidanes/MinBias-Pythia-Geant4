# Cycle 8.3 — Fixed-budget neutrino transport production

## 1. Purpose

Stage 8.3 extends the accepted 100-BC causal pilot into a larger descriptive
study of the neutrino-transport switch. The production campaign measures
eligible-neutrino frequency, particle-accounting deltas, calorimeter energy and
hit differences, runtime, and storage across independent deterministic seeds.

The pilot at seed 512 remains an implementation validation and is excluded
from the primary Stage 8.3 aggregate. Results apply to this simplified
ATLAS/Lorenzetti-like simulator and are not official ATLAS performance.

## 2. Frozen matrix

The matrix contains three seed pairs. Each seed runs the OFF and ON conditions
for exactly 1,000 bunch crossings with one thread.

| Seed | OFF BCs | ON BCs | Paired BCs |
|---:|---:|---:|---:|
| 1512 | 1,000 | 1,000 | 1,000 |
| 2512 | 1,000 | 1,000 | 1,000 |
| 3512 | 1,000 | 1,000 | 1,000 |
| **Total** | **3,000** | **3,000** | **3,000** |

The total transport budget is 6,000 executed BCs. The OFF/ON members of each
seed pair must use identical runtime parameters and differ only in
`transport_neutrinos` and output path.

## 3. Stopping rule

The stopping rule is the fixed matrix above. The campaign must not stop early
because of the observed number of eligible neutrinos, a zero/nonzero energy
difference, a hit difference, runtime, or an apparent trend. A computational
failure aborts transactional publication; it does not redefine the sample.

The campaign is computationally complete after all six fixed runs, six ROOT
audits, three paired analyses, aggregate validation, and checksum publication
pass. A zero eligible-neutrino count is a scientifically limited result, not a
reason to alter the budget after examining data.

## 4. Physics and execution invariants

Stage 8.3 retains the accepted pilot physics contract: proton-proton collisions
at 14 TeV, `SoftQCD:inelastic`, Poisson mean 1, `FTFP_BERT_ATL`, 1 mm
production cut, `max_abs_eta = 1.8`, zero beam sigmas, generator auditing,
overlap checking, and one transport thread.

Seeds are fixed at 1512, 2512, and 3512 before transport. Seed 512 is not reused
in the primary production estimate. Event IDs and BCIDs run from 0 through 999
inside each seed and are aggregated using `(seed, event, bcid)` keys.

## 5. Primary metrics

For every seed and for the aggregate, the campaign reports:

- eligible final neutrinos inside acceptance;
- final neutrinos outside acceptance;
- OFF and ON transported-particle counts and their difference;
- total and per-event deposited-energy differences;
- changed events, changed hit cells, hit-energy L1, and maximum cell delta;
- OFF/ON wall time, peak RSS, ROOT size, and their ratios;
- requested/generated interactions, failures, unknown PDGs, unlineaged steps,
  and segmentation failures.

The pilot is reported separately and is never silently pooled with Stage 8.3.
Rates are descriptive counts per BC and per seed. No universal neutrino-rate or
official detector-response claim is authorized.

## 6. Computational acceptance

Every seed pair must satisfy exact metadata, event, BCID, generator-content,
and non-neutrino decision pairing. The ON-minus-OFF transported-particle delta
must equal the eligible-neutrino count globally and event by event.

The following remain hard failures:

- missing, unreadable, empty, or zombie ROOT data;
- generator or event mismatch outside the documented neutrino switch;
- unknown PDGs, unlineaged steps, segmentation failures, or orphan hits;
- negative/non-finite energy or event-to-hit energy-closure failure;
- checksum mutation, incomplete analysis products, or non-atomic publication.

Energy and hit differences are measured rather than assumed. Zero is accepted
when observed after all computational gates pass. Eligible-sample adequacy is
classified only after the fixed campaign: 0 is `NONE`, 1–29 is `LIMITED`, and
30 or more is `DESCRIPTIVE`. This classification does not change campaign
completion.

## 7. Resource plan

The pilot measured 149.24 s for 100 OFF BCs and 162.07 s for 100 ON BCs.
Linear planning therefore estimates 9,339.3 s (about 2 h 36 min) of simulator
wall time for the six production runs. The corresponding projected ROOT volume
is 1,754,694,840 bytes (about 1.63 GiB), with peak RSS near 161 MiB.

These are planning estimates, not acceptance thresholds. Preflight must require
at least 5 GiB of available storage to cover transactional data, analysis,
logs, and safety margin. Runs remain sequential with build parallelism one.

## 8. Provenance and publication

The executor must reject an existing destination, require a clean tracked
worktree, record the exact Git commit, build and run the complete test suite,
and write into a temporary sibling directory. Final publication occurs through
one atomic rename only after all six runs and all aggregate gates pass.

ROOT files and execution logs remain under `outputs/` and are not versioned.
Only compact summaries, validation markers, manifests, and SHA-256 registries
may enter Git after the campaign.

## 9. Authorization gate

This document and the Stage 8.3 preflight must be committed before transport.
Transport remains disabled until a transactional six-run executor and aggregate
analyzer have synthetic tests and the complete CTest suite passes.

The contract-only preflight must end with:

```text
NEUTRINO_TRANSPORT_STAGE83_PREFLIGHT=PASS runs=6 seed_pairs=3 bunch_crossings=6000 paired_bunch_crossings=3000 events_per_condition=1000 seeds=1512,2512,3512 threads=1 stopping_rule=fixed_budget transport_executed=NO
```

## 10. Transactional executor and aggregate products

The production executor exposes mutually exclusive `--dry-run` and
`--execute-production` gates. Dry-run builds the project, runs the complete
CTest suite, executes the contract preflight, and resolves all six simulator
commands without transport or output creation. Production remains sequential
and writes only to a temporary sibling of the final output directory.

Each seed pair is analyzed independently with its expected event count and
seed. Unlike the pilot-only gate, an individual production seed may contain
zero eligible neutrinos. The aggregate then validates exactly 3,000 unique
`(seed, event, bcid)` keys, sums accounting and energy metrics, reports resource
usage for all six runs, applies the fixed adequacy classification, and checks
that the total transported-particle delta equals the total eligible count.

The accepted output transaction contains per-seed ROOT data, execution logs,
ROOT audits, paired analysis products, `analysis/stage83_seed_summary.csv`,
`analysis/stage83_events.csv`, `analysis/stage83_summary.csv`,
`analysis/stage83_resource_summary.csv`, `analysis/stage83_validation.txt`, a
six-row `campaign_manifest.tsv`, and `campaign_artifacts.sha256`. Publication
uses one atomic rename after every gate passes; any failure removes the
temporary transaction and leaves the final destination absent.

The executor-only dry-run must end with:

```text
NEUTRINO_TRANSPORT_STAGE83_EXECUTOR_PREFLIGHT=PASS runs=6 seed_pairs=3 bunch_crossings=6000 paired_bunch_crossings=3000 transport_executed=NO
```

No production transport is authorized merely by implementing this executor.
Its commit and remote head must be audited before `--execute-production` is
invoked.
