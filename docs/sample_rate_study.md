# Sample-rate comparison: 192, 384 and 768 kS/s

Date: 2026-11-15. This study reuses the digital quantization and linear output
model without changing the 3+9 architecture or enabling any new FPGA behavior.

## Reproduction

```powershell
python calc/sample_rate_study.py
```

The shared calculator now accepts a sample rate and output directory; its
original default remains 192 kS/s and `results/quantization/`. The new runner
writes per-rate reports under `results/sample_rates/<rate>/` and a consolidated
`results/sample_rates/comparison.json`. Plots follow the same directory layout.
The 192 kS/s rows must match the previous saved study exactly before proceeding.

Each rate uses the same 1 kHz high-precision sine, four amplitudes (90%, 1%, 0.1%
and silence), four quantizers and eight seeds. Record duration remains 0.2 s,
warmup 0.01 s, and Fourier spacing 5 Hz. This totals 384 trials. Rounding trials
repeat identically across seeds. Higher-rate cases synthesize new samples of
the same high-precision waveform; they do not repeat already rounded 12-bit
samples. This tests potential oversampling benefits, not a finished audio-file
resampler or the recovery of information lost in 12-bit source material.

Algorithms, clipping checks, Parseval check, error-feedback identities and
metrics are defined in `quantization_study.md`. All use LL1679/PP B with assumed
100 pF primary capacitance and 100 kohm core loss. The physical signal scale is
5 V. In-band error integrates 20 Hz-20 kHz relative to the unquantized reference
through the same model; it includes quantization harmonics and dither noise.
It is not THD alone or measured amplifier THD+N.

## Timing and physical limits

A separate scheduling calculation rounds requests to 50 MHz edges and checks
that the shortest interval exceeds the ten-cycle blanking interval. This is
only an interval check. The spectral model uses uniformly spaced samples and
omits the rounded request timing, 200 ns blanking, device dynamics, mismatch,
magnetic nonlinearity and physical noise. Timing fit alone cannot qualify gates.

| Rate | Nominal sample interval | 50 MHz intervals | 200 ns / sample interval |
|---|---:|---:|---:|
| 192 kS/s | 5.208 us | 260 or 261 clocks | 3.84% |
| 384 kS/s | 2.604 us | 130 or 131 clocks | 7.68% |
| 768 kS/s | 1.302 us | 65 or 66 clocks | 15.36% |

These percentages are not distortion or output-power losses. Blanking applies
only to changing branches. The consolidated report additionally provides
transition-rate*200ns/32 as an average commanded blank-time fraction per branch;
it is not an analog performance estimate.

Conditional Coss-only loss is calculated from the actual decoded branch-change
count at each rate and the existing approximate 650*Qoss(650) hard-switch model.
It is not obtained by blindly multiplying the prior watts by sample rate. It
excludes resistor, driver, gate-charge and core losses. It is not an HV simulation,
measured dissipation, or an estimate of partial/soft commutation.

The finite coherent record and linear frequency-domain filtering are the same
as in the earlier study. Frequencies above each rate's Nyquist limit are omitted,
including higher sampling images. Consequently the reported out-of-band RMS
covers different upper limits at different rates and is not an equal-band
emissions comparison. Unknown distributed transformer parasitics make such
high-frequency predictions provisional. Seed ranges are empirical variation,
not confidence bounds or proof of general stability.

## Executed results

All 384 trials completed without clipping. Error-feedback identities and
Parseval checks passed. The regenerated 192 kS/s statistics match the earlier
study exactly. Request intervals pass the separate ten-cycle spacing check.

The following medians use second-order error feedback with triangular dither,
at 1 kHz. Error integrates the entire 20 Hz-20 kHz band, not only harmonic bins.

| Rate | Error / signal at 1% input | Error / signal at 0.1% input | Coss scenario, 1% input | Coss scenario, silence |
|---|---:|---:|---:|---:|
| 192 kS/s | 0.29174% | 2.9215% | 10.38 W | 38.26 W |
| 384 kS/s | 0.05308% | 0.5344% | 20.38 W | 76.43 W |
| 768 kS/s | 0.00985% | 0.09724% | 40.93 W | 152.98 W |

At 1% input the error reduction relative to 192 kS/s is about 5.50 times at
384 kS/s and 29.63 times at 768 kS/s. The eight-seed error ranges are
0.05217%-0.05401% at 384 kS/s and 0.00932%-0.01223% at 768 kS/s. The larger
relative spread at the lowest error level is a reason not to overstate precision.

Increasing rate alone is less effective: undithered rounding yields 0.6113%,
0.3494% and 0.2720% error at 1% input for the three rates. At 0.1% input, rounding
stays near 19.8% across rates. The large improvement comes from the combination
of oversampling and error feedback, not from the sample-rate label alone.

For undithered rounding at 1% input, transition-rate-based loss stays near 4.82 W
at every rate: the branch-change count is almost unchanged despite more sample
updates. This is a useful counterexample to assuming all switching loss scales
in proportion to sample rate. For the dithered second-order case, actual counted
transitions do grow approximately with rate.

Second-order average commanded blank-time fractions per branch at 1% input are
0.463%, 0.909% and 1.826%; at silence they are 1.707%, 3.409% and 6.824%. These
averages do not resolve code-dependent glitches or simultaneous multi-branch
transitions, and cannot replace the missing analog simulation.

## Decision

The higher-rate experiment is worthwhile and confirms a substantial potential
low-level benefit. Keep 192 kS/s as the verified baseline. Use **384 kS/s as the
next analog-test candidate**; retain 768 kS/s as a higher-cost comparison, not a
new default. No FPGA timing, clock setting or gate command logic was changed.

Before adoption, define an idle/mute/start/stop policy, resolve transformer
stored-energy behavior, and run the shaped stream through the switched model
with real blank intervals and clock rounding. Even perfect silence muting would
not remove the approximately 41 W conditional Coss estimate at 1% input for
768 kS/s. The findings therefore do not justify assuming that idle muting alone
makes the highest rate practical.

The remaining trade is concrete: low-level digital error versus commutation
loss and analog glitches. The estimate does not establish an exact thermal
limit, but it is sufficient to avoid adopting 768 kS/s on the spectral result
alone. No purchase, external message, hardware build or commit was performed
as part of this rate-comparison stage.
