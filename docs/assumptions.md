# Assumptions and measurement limits

- Initial reference: ideal 5 V source. Logic generators and ideal switch controls cost no power.
- Switch Ron=1e-6 ohm, Roff=1e12 ohm, no charge injection/capacitance or gate-drive losses.
- Logic PWL edges: 1 ns. Skew test delays bit b by b*20 ns in both arms.
- R/2R exact, temperature-independent. No thermal or electrical noise model.
- R=1000 ohm per arm, differential source resistance 2000 ohm.
- Transformer: Lp=10 H, Ls=0.04 H, K=1, no winding/core losses or nonlinear saturation.
- PCM: 192 kS/s; 1 kHz periodic rounded 4-bit sine; half-cycle codes explicitly complementary.
- Sine amplitudes: 0.9 and 0.25 of nominal full scale before rounding. No dither.
- Simulation: 100 ms; report sine averages over last 8 ms after startup settling.
- Maximum transient step 200 ns; solver inserts smaller steps around switching events.
- FFT: interpolate adaptive results to 3.072 MS/s; last coherent 8 ms, rectangular window,
  subtract mean; THD sums harmonics 2–20 relative to fundamental. This is not THD+N.
- FFT interpolation affects high-frequency detail; ns glitch energy needs a separate convergence study.
- Code test uses a resistor instead of an inductor: a transformer cannot transfer static code levels.
- No physical HV build, real component selection, damping certification, or audio-quality claim.

## Additional scope: equal-power study

`calc/power_trade_study.py` and `sim/verify_power_study.py` have a separate scope:
4/12-bit ladders, ideal reflected resistive loads of 5/10/20 kohm, and analytically
scaled supply targets of 600/650/700 V. The useful target is the 1 kHz fundamental
power (including the zero-order-hold sinc factor), not total waveform RMS power.
The power sweep omits finite magnetizing inductance, transformer bandwidth and
losses. Each SPICE check runs one 1 ms period at 5 V into the reflected resistor;
there are no energy-storage elements requiring settling in these particular decks.
This study verifies dissipation and static loading, not full 12-bit audio performance.
See `power_trade_study.md` for derivations, numerical tolerances, and limitations.

## Parallel architecture comparison

The new binary and segmented networks are voltage-mode parallel branches, each
switched between supply and return and connected through a resistor to its arm's
output node. A grounded unit-conductance termination per arm preserves the exact
R–2R code scale and output resistance. The 12-bit segmented case uses 15 equal
coarse branches of weight 256 and eight binary fine branches of weights 1–128.
There is no current source, interstage buffer, PWM power stage, or analog amplifier.
Ideal code mapping and resistor power are verified; real 12-bit accuracy, glitch
energy, leakage, capacitance, and driver losses remain unvalidated.
