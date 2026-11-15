# Audio-band and low-level checks

Date: 2026-11-15. Decision: retain the 3+9 architecture and 200 ns command blanking
as the research baseline. Do not treat the earlier 1 kHz / 90% result as a
full-band or low-level performance specification.

## Reproduction and executed coverage

```powershell
python sim/audio_band.py
python sim/transformer_bandwidth.py
```

Five ngspice runs completed: one 401-point AC sweep, two full switched low-level
transients with timestep refinement, and two AC points checking the conditional
inductance requirement. Independent complex-impedance calculations verify the
AC sweep. Results are in `results/audio_band/`, generated decks in
`sim/generated/audio_band/`, and plots in `plots/audio_band/`.

The original 4-bit bench and the preceding 90%-amplitude study are unchanged.
No hardware or KiCad component choice is changed by this study.

## Frequency response: the assumed transformer is not adequate at low frequency

The linear AC network uses the existing assumed transformer: primary/secondary
self-inductances 10 H / 8 mH, coupling 0.999, winding resistance 200 / 0.2 ohm,
primary shunt capacitance 100 pF, primary core-loss resistance 100 kohm and 8 ohm
load. The source is the differential Thevenin equivalent, with 10549.4 ohm
series resistance. It is not a full switch-network AC analysis.

The table includes the analytical zero-order-hold factor sinc(f/192000), with
all values normalized to 1 kHz. The AC sweep itself uses a continuous source.

| Frequency | Gain relative to 1 kHz |
|---|---:|
| 20 Hz | -12.216 dB |
| 50 Hz | -5.440 dB |
| 100 Hz | -2.095 dB |
| 1 kHz | 0 dB |
| 10 kHz | -0.017 dB |
| 20 kHz | -0.150 dB |

The small-signal analog network and the independent complex-impedance solution
agree to a maximum relative error of 1.78e-13 over 10 Hz to 1 MHz. This checks
implementation of the assumed network, not the accuracy of its assumed values.
The 20 kHz result does not include branch Coss, switching distortion, sample-clock
quantization or nonlinear magnetic effects; full switched upper-band validation
remains open. Linear response does not establish saturation margin at 20 Hz.

### Conditional inductance requirement

For an illustrative -1 dB limit at 20 Hz relative to 1 kHz, solving the same
linear network requires about **77.93 H primary self-inductance**. This is a
conditional selection criterion, not a purchasable part specification.

During the calculation, the nominal squared turns ratio remains 1250, primary
short-circuit leakage Lp*(1-k^2) remains 19.99 mH, and winding resistance,
capacitance and core-loss resistance are held fixed. Secondary self-inductance
therefore becomes 62.35 mH and k becomes approximately 0.99987174. Two separate
ngspice AC operating points verify -1.000000 dB including the hold correction.
A real transformer will not necessarily preserve those other parameters as
inductance increases. Its large-signal inductance, core behavior and winding
parasitics must be checked together.

## Low-level 12-bit behavior

The full 32-branch / 64-controlled-conductance network is run at 5 V with the
same 10 H transformer, 20 pF fixed capacitance per transistor, 0.35 ohm on
resistance, 2 ns conductance edges and 200 ns command blanking. Input: 1 kHz,
1% full-scale amplitude (-40 dBFS relative to full-scale sine amplitude), 192 kS/s.

Each request instant is rounded to the nearest 50 MHz clock edge. Timing error
is bounded by 10 ns and the 1 ms sequence repeats after exactly 50000 clocks.
This represents the requested clock-grid constraint; it does not implement an
asynchronous PCM receiver, prove clock-domain crossing, or co-simulate the HDL.
The outgoing/incoming command edge behavior otherwise matches the previous
analog surrogate. There is no dither, noise model, mismatch or saturation.

The rounded sine uses 42 distinct codes, from 2027 through 2068. The reference
calculation integrates each held code exactly in the Fourier domain using the
same rounded event times, then applies the transformer transfer function at
each harmonic. It omits switch resistance, branch capacitance and blanking.

| Result | Full switched model | Ideal held-code reference |
|---|---:|---:|
| Secondary fundamental peak | 0.639523 mV | 0.639575 mV |
| THD, harmonics 2-20 | 0.53137% | 0.52018% |

Most of the observed low-level harmonic distortion is already present in the
ideal 12-bit held-code reference. The difference cannot be assigned solely to
dead time: the reference also omits Ron and Coss. Likewise, THD is a norm of
harmonic phasors, so subtracting the percentages is not an independent distortion
budget. These figures are not THD+N and do not establish subjective audibility.

Transient duration is 20 ms; the final 18-20 ms window is compared to 16-18 ms.
FFT processing follows the preceding study: coherent rectangular window,
50 ns interpolation grid, harmonics 2-20. Maximum solver steps of 500 and 250 ns
produce a fundamental difference of 0.0001703% and a THD difference of 0.0000719
percentage point. The preceding-window differences are 0.0001184% and 0.00000272
percentage point respectively. Both refinement and settling checks pass.

## Decision and remaining work

1. Keep 3+9 and 200 ns as the baseline; do not reopen resistor segmentation on
   the basis of these results.
2. Prioritize an actual output-transformer model or measured impedance data.
   The assumed 10 H case has a substantial low-frequency limitation. Use the
   conditional 78 H estimate to guide evaluation, not to approve a component.
3. Address low-level quantization explicitly. A bounded dither/noise-shaping
   experiment can test the distortion/noise trade-off without immediately adding
   physical bits. Higher resolution remains a possible later design decision.
4. Still required: full switched upper-band cases, shutdown/fault transients with
   stored magnetic energy and an appropriate clamp/body-diode model, nonlinear
   device/transformer models, bias/protection implementation and physical FPGA
   timing/clock-domain qualification.

These checks identify concrete limitations; they do not complete the hardware
schematic or qualify an energized high-voltage build. The project remains
simulation-only.
