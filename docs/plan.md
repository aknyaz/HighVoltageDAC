# Project plan

## Phase A0 — first reproducible test bench

- [x] Locate the KiCad CLI and run the ngspice DLL.
- [x] Implement transformer and equivalent source resistance calculations.
- [x] Verify two 4-bit R–2R arms at 5 V across all 16 codes.
- [x] Verify power balance with a resistive load.
- [x] Run a 1 kHz sine at 192 kS/s at two levels through a simplified transformer.
- [x] Compare simultaneous major-carry switching with a 20 ns delay between bits.
- [x] Create the first editable KiCad sheet: the passive core of the test bench.

## Next phase: A1

1. Check frequency response and output impedance, including at 20 Hz.
2. Measure DC current and magnetic flux during startup, with a constant code, and with PCM offset.
3. Add a 12-bit test bench and compare quantization and switching glitches.
4. Introduce resistor tolerances, temperature drift, and delay variation; compare segmentation.
5. Compare datasheets for several real transformers and select an impedance range.
6. Transfer the complete validated model into the KiCad simulator while retaining independent .cir files.

## Phase B

Add winding resistance, magnetizing inductance, leakage inductance, capacitance, losses,
and a nonlinear core model if justified. Then add Ron/Coss and models of real switches,
a passive filter, and a thermal assessment.

## Phase C

Develop the complete schematic after validating the architecture. PCB design and
physical high-voltage hardware are outside the current scope.
