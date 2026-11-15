# Controller blanking with a linear transformer

Date: 2026-11-12. Fixed architecture: 3+9 segmented differential DAC.

## Scope and reproduction

Run `python sim/controller_analog.py` and then
`python sim/verify_controller_analog.py` from the repository root. The first writes eight
standalone ngspice decks, a JSON summary, simulator log and comparison plot.
No existing KiCad schematic or initial 4-bit simulation is modified.

The study uses 5 V, 192 kS/s, a coherent 1 kHz sine at 90% full scale, and
complementary 12-bit codes. It compares 0 ns and 200 ns command blanking with
20 pF and 100 pF **fixed capacitance per transistor**. These are sensitivity
cases, not a validated model of Coss at 5 V or 650 V. Only branches whose state
changes are blanked. Unlike the FPGA, sample requests are not quantized to a
50 MHz clock; audio clock crossing/jitter is outside this experiment.

The circuit contains 64 controlled conductances, with 0.35 ohm on resistance,
1 Tohm off resistance and a linear conductance edge lasting 2 ns. The outgoing
edge starts at the request and the incoming edge starts 200 ns later. Thus the
200 ns case has 198 ns with both conductances at their off value. The 0 ns case
is an overlapping-edge mathematical reference, not an acceptable hardware gate
sequence. No switching-loss conclusions are drawn from that reference.

An abrupt ideal-switch version failed transient convergence; smoothing the
conductance resolves that numerical discontinuity. The 2 ns edge is an assumed
model parameter, not a claimed MOSFET transition time. There are no body diodes,
nonlinear charge, driver delays, magnetic saturation, noise, resistor mismatch
or physical protection in this model. Its control waveforms implement the
sequencer's nominal behavior, but this is not HDL/analog co-simulation.

## Assumed transformer

| Parameter | Value |
|---|---:|
| Primary/secondary inductance | 10 H / 8 mH |
| Nominal squared turns ratio | 1250 (10 kohm:8 ohm) |
| Coupling coefficient | 0.999 |
| Primary/secondary series resistance | 200 ohm / 0.2 ohm |
| Primary shunt capacitance | 100 pF |
| Linear core-loss resistance across primary | 100 kohm |
| Secondary load | 8 ohm |

These parameters are an explicitly assumed network, not a selected transformer
specification. An actual transformer must be characterized or supported by a
manufacturer model. A linear core cannot establish magnetic coloration or
saturation margin. Scaling a linear output to 650 V does not validate those effects.

## Measurement method

Simulate 20 ms and analyze 18-20 ms, comparing against 16-18 ms for settling.
An initial 8 ms run failed the settling check and is not a reported steady-state
result. Each case is repeated at 500 ns and 250 ns maximum integration steps;
adaptive timesteps and source breakpoints resolve the 2 ns transitions.

Uniform interpolation to 50 ns produces 40000 points in each two-cycle window.
The rectangular FFT is coherent (500 Hz bins). THD uses harmonics 2 through 20,
relative to the 1 kHz fundamental. It is not THD+N or an audio-quality verdict.
The 50 ns analysis grid does not imply a 50 ns integration accuracy; convergence
is checked separately by halving the solver's maximum step. Output power includes
all content represented on that grid, rather than just the fundamental.

Acceptance checks require less than 0.1% fundamental difference and 0.01 percentage
point THD difference on timestep refinement, and less than 0.05% fundamental / 0.01
percentage point THD change between settling windows. See the JSON for actual
residuals; these thresholds alone are not a guarantee of 12-bit accuracy.

Periodic PWL sources use the repeat facility documented in the
[ngspice 46 manual](https://ngspice.sourceforge.io/docs/ngspice-46-manual.pdf).

## Executed sine results

All eight long runs and sixteen short runs completed and passed their numerical
checks. The table uses the finer timestep in each case.

| Per-device capacitance | THD, 0 ns | THD, 200 ns | Fundamental change with blanking |
|---|---:|---:|---:|
| 20 pF | 0.01031% | 0.01070% | +0.00122% |
| 100 pF | 0.01031% | 0.01033% | +0.000246% |

Maximum long-run timestep-refinement differences are 0.000242% in fundamental
amplitude and 0.0000852 percentage point in THD. Maximum settling-window changes
are 0.000137% and 0.0000174 percentage point respectively. The very small THD
change at 100 pF is below the timestep-refinement difference, so its sign and
magnitude are not resolved. The 20 pF increase is small in absolute terms.

An independent complex-impedance calculation predicts 57.3772 mV peak at the
secondary for an ideal source and held sine. The 20 pF / 0 ns simulation gives
57.3756 mV, a 0.00279% difference. The calculation includes winding impedances,
coupling, core-loss resistance, primary capacitance and zero-order hold, but
omits finite switch resistance, branch capacitance and PCM rounding. See
`sim/verify_controller_analog.py` and `results/controller_analog/verification.json`.

Load power is approximately 205.75 uW in the 5 V simulation. Pure linear scaling
by (650/5)^2 would imply about 3.48 W at this 90% amplitude, or roughly 4.29 W at
full scale. This is a conditional linear-model projection, not a 650 V simulation
or hardware rating. It shows that transformer losses/loading can reduce the
previous ideal 5 W full-scale estimate. A real transformer and nonlinear Coss
may change both output and switching behavior.

Decision: retain 3+9 and 200 ns for the next simulation stage. This particular
1 kHz test does not identify blanking as a reason to reject the design. It does
not establish broadband audio performance or actual transistor non-overlap.

## Major-carry check

Run `python sim/controller_transitions.py`. Sixteen additional SPICE runs cover
2047 -> 2048 and its reverse, both capacitances, both blanking times, and 2 ns / 1 ns
maximum steps. Initial conditions are the settled DC operating point at the
starting code. This is a small-code local transition test, not shutdown from a
large magnetic current or a full-code worst-case search.

The table reports the **difference from the zero-blanking waveform** over 9 us
following the request, not total overshoot relative to a settled target.

| Coss per device | Peak primary difference | Peak secondary difference | Primary absolute difference area |
|---|---:|---:|---:|
| 20 pF | 4.331 mV | 23.42 uV | 3.270 V ns |
| 100 pF | 0.556 mV | 2.727 uV | 0.3882 V ns |

Reverse transitions match within the asserted 10 uV primary-peak tolerance.
Area changes on timestep refinement are below 0.000052 V ns. Larger capacitance
reduces this particular difference by holding branch voltages through blanking;
this does not imply that larger Coss improves power loss or wideband behavior.
See `plots/controller_analog/major_carry.png` and `results/controller_analog/transitions.json`.

The reported primary peak in the sine summary is sampled on the 50 ns analysis
grid. It is not a guaranteed instantaneous device-voltage maximum or insulation
stress check. Neither the small-code test nor these settled sine cases validate
shutdown with stored magnetic energy.

## Interpretation limits and next decision

This step tests one sine frequency and level plus one pair of major-carry
transitions. A favorable result is sufficient to retain 200 ns as the working
simulation setting; it is not sufficient to freeze hardware dead time or claim
12-bit performance throughout the audio band.

The next bounded study should cover low frequency, the upper audio band and low
amplitude, followed by stop/fault transients with magnetic energy. It must also
include the actual 50 MHz request timing. The transformer parameters remain a
major uncertainty; component/model selection or measured impedance data must
precede hardware conclusions. Keep the 3+9 partition fixed unless a concrete
failure establishes a reason to change it.
