# Cycle 11 benchmark closeout

## Scope

This benchmark validates the canonical Cycle 11 code-under-test commit
`d5e708c94f5c872a4b8d1bbe81380a36737f551d`.

The frozen campaign contains 10 simulator runs with seed base 9512:
4 reproducibility runs and 6 performance runs, using 1 and 2 threads.

## Scientific reproducibility

Scientific reproducibility is **PASS**.

- 1-thread repeatability: PASS.
- 2-thread repeatability: PASS.
- 2-thread exact repeatability: YES.
- Cross-thread repetition 1: IDENTICAL.
- Cross-thread repetition 2: IDENTICAL.
- Events are scientifically identical across thread counts.
- Hits are scientifically identical across thread counts.
- No unexpected metadata differences were observed.

Raw ROOT SHA256 equality is not required because operational metadata,
including output path and thread count, may differ.

The benchmark was executed with generator audit disabled, therefore the
generator tree contains zero entries in this campaign. Generator
stability is not independently exercised by this benchmark and remains
supported by the dedicated Cycle 11 scientific validation campaigns.

## Performance

Performance timing stability is **WARNING**, not FAIL.

- Median 1T wall time: 486.300000 s.
- Median 2T wall time: 198.080000 s.
- Apparent 2T speedup: 2.455068659.
- Apparent parallel efficiency: 1.227534330.
- 1T coefficient of variation: 0.285324584.
- 2T coefficient of variation: 0.208340643.

Both timing groups exceed the 20 percent stability-warning threshold.
The apparent superlinear speedup is therefore not accepted as a stable
scaling measurement.

Relative to the Cycle 10 reference, the 2T median is close to the
historical result while the 1T median is substantially slower. The
observed speedup is consequently dominated by 1T timing variability.

This campaign does not provide sufficient evidence to quantify the
performance overhead of the new event-stable Geant4 transport reseeding
policy, nor does it establish a systematic performance regression.

## Acceptance

Benchmark acceptance: **PASS_WITH_TIMING_WARNING**.

The scientific reproducibility requirement is satisfied. Timing
variability is retained as an operational warning and is not a
scientific rejection criterion.
