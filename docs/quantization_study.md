# Low-level quantization and switching-cost study

Date: 2026-11-15. Research result: second-order error feedback is the preferred
candidate among the tested digital quantizers, but is **not enabled in HDL**.
Its idle switching cost must be addressed before adopting it in the power DAC.

## Reproduction and scope

```powershell
python calc/quantization_study.py
```

The script executes 128 numerical trials: four modes, four input amplitudes
(90%, 1%, 0.1%, zero), and eight deterministic random seeds. The undithered
rounding results repeat identically across seeds. Each run warms up for 1920
samples and evaluates 38400 samples (0.2 s) at 192 kS/s. The sinusoid is 1 kHz.
All modes receive the same high-precision input waveform before 12-bit rounding.
**Already quantized 12-bit source PCM cannot recover lost information from this
process.** A higher-precision source or upstream DSP is required for the modeled
benefit. The existing HDL accepts the final 12-bit stream; none of these DSP
algorithms has been implemented or timed in FPGA hardware.

The linear output model uses the LL1679/PP B candidate with the existing assumed
100 pF primary capacitance and 100 kohm core-loss resistance. Differential code
voltage is 5*(2*q-4095)/4096. Frequency-domain filtering applies the sample hold
and transformer response from `sim/select_transformer.py`.

This is a digital/linear spectral simulation, not a new ngspice or full-switch
transient test. It omits 50 MHz request rounding, 200 ns blanking, resistor
mismatch, nonlinear magnetics, driver behavior and physical noise. Frequencies
above Nyquist (96 kHz), including higher sampling images, are omitted. The
finite FFT record represents a periodic steady-state approximation; results
are not a formal stability or broadband qualification.

## Explicit algorithms

Let x be the desired offset-binary code, d the difference of two independent
uniform [0,1) random values, and q the nearest integer using floor(v+0.5).
Thus d is triangular dither in (-1,1) code units, without subtracting it from
the analog output. State starts at zero.

- `round`: q = round(x).
- `tpdf`: q = round(x+d).
- `ef1_tpdf`: v = x+e_previous; q = round(v+d); e = v-q.
- `ef2_tpdf`: v = x+2*e_previous-e_previous2; q = round(v+d); e = v-q.

The stored error excludes d from v. Without clipping the last two modes satisfy
q-x = e_previous-e and q-x = 2*e_previous-e_previous2-e respectively. These exact
time-domain identities are asserted for every trial. Quantizer state stays
within 1.5 code units in the tested cases. Saturation would reset the error
state, but no tested case clips. Near-full-scale overload, arbitrary transients
and fixed-point arithmetic are not qualified by these tests.

## Metrics and executed checks

A coherent rectangular FFT gives 5 Hz bins. One-sided power weighting is checked
against time-domain mean-square error using Parseval's identity. The error is
measured against the unquantized sine through the same linear model, so it
includes harmonic error, added dither noise and fundamental amplitude/phase
error. DC is excluded from the 20 Hz-20 kHz result and reported separately.

Harmonic-bin readings contain noise in those bins. They are finite-record values,
not unbiased deterministic THD estimates. In-band error must therefore accompany
any apparent harmonic improvement. Values below are eight-seed medians; the JSON
also contains observed minima and maxima. dBFS references the model's full-scale
1 kHz output sine RMS. The spectrum plot combines power into 50 Hz bands; it is
not a power-spectral-density plot in dB/Hz.

At 1% input (-40 dBFS):

| Mode | 20 Hz-20 kHz error / signal | Harmonic-bin RMS / signal | Branch transitions/s |
|---|---:|---:|---:|
| Rounding | 0.611% | 0.520% | 343909 |
| TPDF | 1.554% | 0.105% | 445082 |
| First-order EF + TPDF | 0.585% | 0.041% | 590430 |
| Second-order EF + TPDF | 0.292% | 0.0185% | 740744 |

Second-order EF improves in-band error by approximately 6.43 dB versus rounding
in this case. Its eight-seed error range is 0.283%-0.298%. Plain TPDF reduces
coherent-looking spectral lines but worsens the total in-band error here.
These numbers are not directly interchangeable with the earlier switched-model
THD: the transformer, timing model and metric differ.

At 0.1% input (-60 dBFS), in-band error is 19.87% for rounding, 15.64% for TPDF,
5.84% for first-order EF and 2.92% for second-order EF. Better low-level behavior
is possible in this ideal model, but no claim of additional hardware resolution,
subjective audibility or actual amplifier noise performance is made.

## Switching and idle cost

Branch transitions are counted by decoding both 3+9 arms, including B=4095-A.
A transition is a half-bridge node change, not an individual gate edge. There is
no artificial wraparound transition between the end and start of the record.

For context only, the transition rate is multiplied by 650*Qoss(650), using the
existing approximate typical curve in `calc/sic_charge.py`. This is a conditional
hard-switch estimate, not a newly simulated HV loss. It excludes driver supply,
gate-charge, resistor and magnetic losses. Partial commutation and actual node
voltage trajectories can change it.

| Mode | Coss-only estimate at 1% input | Coss-only estimate at digital silence |
|---|---:|---:|
| Rounding | 4.82 W | 0 W |
| TPDF | 6.24 W | 27.02 W |
| First-order EF + TPDF | 8.27 W | 37.07 W |
| Second-order EF + TPDF | 10.38 W | 38.26 W |

Idle cost is high because code excursions around 2047/2048 toggle many branches.
The second-order case reaches about 2.73 million branch changes per second at
silence. Its simulated in-band idle error is approximately -90.65 dBFS, but that
noise result does not remove the switching burden or omitted blanking glitches.

Undithered zero input rounds to code 2048 and creates no AC error in this
noise-free model. The JSON's -400 dBFS is only a numerical log floor, not a real
noise-floor claim. It leaves +0.5 code DC error: approximately 1.22 mV differential
Thevenin source offset at the 5 V scale. The output transformer blocks secondary
DC but does not eliminate primary DC current. Idle cannot be declared validated
by either the zero-AC-error rounding case or the shaped-noise result.

## Decision

Keep second-order EF + TPDF as a software research candidate. Do not integrate
it into the hardware controller yet. Do not select plain dither merely because
its harmonic bins are lower. Preserve the fixed 3+9 topology and 200 ns setting.

Next bounded task: evaluate a defined silence/mute/start/stop policy together
with transformer stored energy and clamp/body-diode behavior, then run the
candidate quantizer through the switched model. Any code strategy that avoids
midscale carry or changes complementary decoding must be a separately reviewed
change. Do not silently assume all-off shutdown is safe, or assume exact zero DC
from a static complementary 12-bit midscale code.

Actual transformer impedance/core-loss data and its permitted DC imbalance
remain outstanding. The supplier inquiry draft is still unsent. Files from this
study are in `results/quantization/` and `plots/quantization/`.
