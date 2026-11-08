# Project plan

## Phase A0 — first reproducible test bench

- [x] Locate the KiCad CLI and run the ngspice DLL.
- [x] Implement transformer and equivalent source resistance calculations.
- [x] Verify two 4-bit R–2R arms at 5 V across all 16 codes.
- [x] Verify power balance with a resistive load.
- [x] Run a 1 kHz sine at 192 kS/s at two levels through a simplified transformer.
- [x] Compare simultaneous major-carry switching with a 20 ns delay between bits.
- [x] Create the first editable KiCad sheet: the passive core of the test bench.
- [x] Create a complete wired KiCad test bench and validate its exported SPICE model.

## Next phase: A1

### Completed: power and impedance trade study

- [x] Evaluated 2,695 feasible amplitude/resistance points across 36 target cases.
- [x] Verified all 33 feasible best sampled cases plus one reserve case in scaled 5 V SPICE.
- [x] Verified independent nodal solutions and voltage/resistance scaling identities.
- [x] Reported full internal ladder heat, useful power, headroom, and infeasible cases.

Results: `docs/power_trade_study.md`. The 12-bit models at this stage verify power
and code-dependent static loading; a complete 12-bit frequency/glitch study remains open.

Compare 600, 650, and 700 V supply targets at the same useful output power
(5 W nominal and 10 W stretch) into 8 ohm. Sweep the transformer's reflected
primary load, initially 5, 10, and 20 kohm, together with ladder resistance.
These are simulation targets, not selected hardware ratings.

For each feasible case, report required code amplitude, voltage headroom, winding
currents, total ladder dissipation including internal branches, supply power,
and efficiency. Explicitly flag cases that cannot achieve the target power.
Compare equivalent scaled low-voltage SPICE cases with the analytical predictions.
Increasing voltage alone must not be presented as an efficiency improvement:
at fixed resistance and normalized waveform, load power and resistive heat both
scale with voltage squared. If all resistances scale with voltage squared too,
both powers remain constant and efficiency is unchanged; improving efficiency
requires changing resistance ratios, waveform utilization, or topology.

Deliverable: a reproducible parameter sweep and plots at equal useful output
power, followed by a justified working range for ladder and transformer impedance.
The present 5 V bench's efficiency is not a verdict on the final architecture.

### Following steps

The immediate design decision is whether to accept the ordinary R–2R ladder's
large internal dissipation. Compare a binary-weighted parallel resistor DAC and
a clearly specified segmented resistive DAC at equal useful power before selecting
real HV switches. Both candidates must retain direct transformer drive and explicitly
account for all internal currents; lower heat is a hypothesis to test, not a promised result.

1. Check frequency response and output impedance, including at 20 Hz.
2. Measure DC current and magnetic flux during startup, with a constant code, and with PCM offset.
3. Add a 12-bit test bench and compare quantization and switching glitches.
4. Introduce resistor tolerances, temperature drift, and delay variation; compare segmentation.
5. Compare datasheets for several real transformers and select an impedance range.
6. Extend the complete KiCad bench as the models evolve, retaining independent .cir references.

## Phase B

Add winding resistance, magnetizing inductance, leakage inductance, capacitance, losses,
and a nonlinear core model if justified. Then add Ron/Coss and models of real switches,
a passive filter, and a thermal assessment.

## Phase C

Develop the complete schematic after validating the architecture. PCB design and
physical high-voltage hardware are outside the current scope.
