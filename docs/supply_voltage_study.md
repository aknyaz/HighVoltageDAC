# Fixed supply reduction: 650 V versus 100 V

## Scope and reproduction

Run `python sim/supply_voltage_study.py`. The script reuses the existing
`audio_viability_switched.py` stimulus, circuit generator, transformer transfer
function and spectral analysis. It writes netlists to `sim/generated/supply_voltage/`,
quantitative records to `results/supply_voltage/` and a harmonic plot to
`plots/supply_voltage/harmonics.png`.

This first check is a 1 kHz sine at 192 kS/s, nominal 12-bit 3+9 equivalent
resistors, 8 ohm load and the linear LL1679/PP B model. Fixed ideal supplies are
used; no regulator or volume ramp is modeled. Digital amplitude is rescaled
before rounding to 12 bits. Identical target output is compared, not identical
code utilization. Actual fundamental amplitudes can differ slightly because
quantization and switching produce gain error.

The original `python sim/run_phase_a.py` regression was executed successfully.
Three unchanged-code scaling checks also agree with the existing held-reference
routine to within 1e-10 percentage points of THD. The new script retains those
checks for future reproduction.

The held-code reference integrates the exact piecewise-constant waveform,
including the existing 50 MHz command grid. Harmonics 2 through 20 are passed
through the same linear transformer response. Source quantization RMS error
is a separate sample-domain metric before the transformer, not output THD+N.
The amplitude reference includes the DAC's 4095/4096 endpoint factor.

## Held-code result

| Target level relative to 650 V full scale | Code amplitude at 650 V | Code amplitude at 100 V | THD at 650 V | THD at 100 V |
|---|---:|---:|---:|---:|
| -20 dBFS | 10% | 65% | 0.077844% | 0.014514% |
| -40 dBFS | 1% | 6.5% | 0.519128% | 0.139277% |
| -60 dBFS | 0.1% | 0.65% | 20.037497% | 0.998827% |

The unchanged-code controls retain the same relative THD at both rails, while
the output amplitude falls by 6.5. Supply reduction alone is not an improvement
in relative quantization distortion.

At the -40 dBFS target, held-code fundamental gain error changes from +0.32174%
to -0.00761%; source quantization RMS error relative to the desired sampled sine
changes from 1.94825% to 0.30824%. At -60 dBFS the corresponding gain errors are
-0.92714% and +0.38809%, and relative RMS errors are 22.85176% and 3.08716%.
These are deterministic nominal-model errors, not tolerance or calibration bounds.

The differential open-circuit source step falls from 0.317383 V to 0.048828 V.
This is the step between complementary arm codes, before transformer loading
and turns ratio. The benefit does not imply 16-bit hardware or uniformly lower
THD at every amplitude: undithered quantization harmonics depend on the code
sequence. Only the listed levels and frequency are covered here.

## Switched model method

All ten SPICE runs completed. Final results at 250 ns maximum timestep:

| Supply | Code amplitude | Output fundamental, peak | THD, harmonics 2-20 |
|---|---:|---:|---:|
| 650 V | 1% | 83.6211 mV | 0.530234% |
| 100 V | 6.5% | 83.3527 mV | 0.140474% |
| 100 V | 1%, unchanged-code control | 12.8648 mV | 0.530222% |
| 650 V | 0.1% | 8.25145 mV | 20.081713% |
| 100 V | 0.65% | 8.36724 mV | 1.015012% |

At equal target output, THD improves by approximately 3.77 times at -40 dBFS
and 19.78 times at -60 dBFS. Actual output amplitudes are listed to expose the
small quantization/gain differences rather than implying an exact measured match.
The maximum timestep-refinement difference is 0.00001635 percentage points;
the maximum adjacent-window difference is 0.00000724 percentage points.
The [harmonic plot](../plots/supply_voltage/harmonics.png) shows both comparisons.

The follow-up uses the existing full 32-branch switch surrogate: fixed 0.35 ohm
on resistance, 20 pF per switch, 200 ns non-overlap and 2 ns control edges.
The SPICE reference source is explicitly set to 650 or 100 V. The upper generic
clamp threshold is adjusted to the respective rail plus 0.7 V; leaving its
original 5.7 V threshold would invalidate the comparison.

Each case is run for 30 ms with maximum timesteps of 500 and 250 ns. Harmonic
analysis uses the last 10 ms and compares the preceding 10 ms. The existing
period-mean exponential fit removes the slow startup tail with its documented
30.874 ms time constant. Raw-window metrics and fitted-tail amplitudes are also
saved. Both timestep and adjacent-window THD changes must be below 0.001
percentage points. Results are collected in `results/supply_voltage/summary.json`.

## Limits and next decision

These are simulations, not measured hardware performance. No nonlinear core,
physical noise, resistor mismatch/temperature/voltage dependence, real supply
ripple or validated nonlinear HV transistor model is included. The branch
resistors are the prior equivalent values; the expanded 3052-chip array and
its internal parasitic/pulse-voltage problem are not included. Fixed-capacitance
surrogates at 100/650 V do not qualify actual switching losses or voltage stress.

The held-code and switched results support testing coordinated supply and volume
control. It does not establish 0.011% THD at all listening levels. Regulator
ripple, settling, coordinated ramps and heat at equal output remain separate
follow-up work. FPGA and physical implementation remain deferred.
