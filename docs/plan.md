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

The alternative-topology comparison is complete: see
`docs/resistive_architecture_comparison.md`. Both parallel architectures reduce
ideal resistor heat substantially; segmentation changes resistor range and switch
count, but not total ideal heat at the same code and output resistance.

- [x] Compare parallel binary and defined 4+8 segmented resistor networks at equal useful power.
- [x] Check all 4096 ideal 12-bit codes and verify both alternatives in structural 5 V SPICE.
- [x] Quantify branch count, resistor span, hottest resistor, and midpoint idle heat.

- [x] Create a complete wired 4-bit parallel KiCad bench and verify its actual SPICE export.

The parallel demonstrator is in `kicad/parallel/`; R–2R remains a reference. Before preferring
binary or segmented hardware, evaluate resistance mismatch, leakage, switch
capacitance/timing, and long-held code states. No real HV device is selected yet.

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
