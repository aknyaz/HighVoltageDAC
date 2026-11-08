# HV-RDAC: High-Voltage Resistive Digital-to-Analog Audio Amplifier

## Project handoff for Codex / VS Code (2026-11-08)

### 1. Vision and non-negotiable intent

Develop and simulate an unconventional **5–10 W audiophile audio amplifier** whose power stage is itself a **high-voltage resistor-and-switch DAC**, coupled directly to an **off-the-shelf vacuum-tube amplifier output transformer**. There is **no conventional analog power amplifier or preamplifier between the DAC and transformer**. This is a research prototype; do not claim that it will outperform conventional class A, D, or tube amplifiers. The appeal is the distinctive topology and potentially distinctive sound. Cost, efficiency, and high component count are secondary to feasibility and sound character.

Digital PCM -> digital switch control -> HV precision resistive DAC -> passive coupling/transformer -> 8-ohm loudspeaker.

The transformer is intentional: (1) impedance transformation, (2) magnetic coloration/harmonics (to be measured, not assumed), and (3) attenuation of switching images, though a real transformer is **not a guaranteed low-pass filter** due to leakage inductance and parasitic capacitance.

### 2. Preliminary design targets (NOT finalized)

- Audio power: 5 W nominal, 10 W stretch goal, load 8 ohm.
- PCM: investigate 12-bit first, potentially 16-bit; initial fs 192 kHz (other rates/oversampling to be evaluated).
- HV supply: **not fixed at 1000 V**. Select a purchasable, high-quality tube output transformer first; design voltages backward from transformer and load. Initial analytical exploration: 600–1000 V supply, but simulation should begin with harmless scaled-down voltages.
- Candidate transformer nominal primary reflected load ~2.5–10 kohm, secondary 8 ohm. Vendor/part has NOT been selected or purchased. Verify actual data sheets and frequency response; distinguish impedance ratio from DC winding resistance.
- No requirement for ultrahigh efficiency. Must quantify resistor heat, key device stress and losses, switching glitch, THD+N, noise, and damping.

### 3. Reference math / sanity check

For ideal 5 kohm:8 ohm impedance transformation, 10 W into 8 ohm:
- Secondary V_rms = sqrt(10*8) = 8.944 V, I_rms = 1.118 A.
- Primary V_rms = sqrt(10*5000) = 223.61 V; I_rms = 44.72 mA.
- Primary V_peak = 316.23 V; primary V_pp = 632.46 V.
- Turns ratio n = sqrt(5000/8) = 25.

**These are numbers across the actual primary load**, not necessarily the open-circuit DAC voltage. DAC Thevenin resistance and transformer losses cause additional supply/voltage/power requirements.

DAC step for an ideal 0–1000 V 16-bit converter = approx. 15.26 mV before load division. This does **not** establish 16-bit linearity.

### 4. Critical questions: must be answered by models, not assumptions

1. Which resistive DAC architecture is viable at power level? Compare voltage-mode R-2R, segmented resistor network, and (if justified) weighted current summation. Explicitly model DAC output impedance, **total static dissipation including internal branches**, loading, and per-switch voltage/current stress. Do NOT simply assume any standard low-voltage R-2R network can handle 800 V or a transformer load.
2. What is the viable primary drive arrangement? Consider fully differential/bridge with complementary code and ideally zero DC voltage across transformer primary. Quantify residual DC due to mismatch/glitches. Consider galvanic references, level shifting, floating supplies and isolation only at an architectural level for now.
3. Does a transformer intended for single-ended tube use (gapped core / DC current allowance) suit zero-DC differential drive? Compare gapped SE and ungapped push-pull / transformer families. Transformers may color sound via nonlinear B-H; there is no guarantee of pleasing distortion.
4. Can 192 kS/s direct output adequately suppress out-of-band images? Include realistic transformer parasitics and evaluate need for passive snubber or output filter. Simulate actual switching waveforms and worst-case transitions, especially midscale major carry.
5. Evaluate resistance tolerance/temperature drift, HV resistor voltage ratings and thermal dependence, switch on-resistance/output capacitance and gate timing, quantization, sampled-data images, transformer losses, inrush/DC bias, and thermal budget.

### 5. Proposed phases and deliverables

**Phase A — architecture feasibility (START HERE)**
- Write a small reproducible Python calculation module (stdlib preferred; numpy/matplotlib okay) for given output W, load, nominal primary Z, DAC Thevenin Z, source swing: turns ratio, ideal winding voltage/current, attenuation, dissipations, attainable load power.
- Produce `docs/architecture_tradeoffs.md` comparing R-2R and segmented DAC and ways of preventing primary DC. Highlight impossible configurations and all assumptions.
- Create a low-voltage **4-bit or 6-bit** SPICE demonstrator in `sim/` first, using ideal switches + R/2R and an ideal coupled-inductor transformer with reflected impedance chosen for easy checking. Demonstrate correct digital code mapping, no DC in primary under symmetric drive, and measure resistor dissipation.
- Progress to 12-bit behavioral/structural model only once the low-bit circuit produces correct quantitative outputs. Avoid massive manual KiCad schematic generation initially.
- Run ngspice transient for a 1-kHz sine PCM test at several levels and a worst-case major-carry step, plot/report waveforms and FFT/THD estimates with transparent FFT windowing and sampling limitations.

**Phase B — transformer and switching realism**
- Replace ideal transformer's simplified model with winding resistances, magnetizing inductance, leakage inductance, core loss and stray capacitances. Add a documented nonlinear core model only if justified/validated.
- Add switch finite Ron, Coss, switching delays and eventually vendor SPICE models.
- Compare 5 W vs 10 W; quantify thermal dissipation, noise, audio-band distortion, out-of-band energy and effect on an 8-ohm load.

**Phase C — KiCad**
- Produce a KiCad project / schematic based on validated ngspice topology; verify local KiCad/ngspice versions and symbol/model compatibility before generation. Keep SPICE netlists as independently testable references. Don't commit to PCB/layout until architecture is settled.

### 6. Repository structure suggestion

```
HV-RDAC/
  README.md
  AGENTS.md
  docs/architecture_tradeoffs.md
  docs/assumptions.md
  calc/...
  sim/...
  plots/...
  kicad/...
```

### 7. First Codex task

Read this brief and create Phase A deliverables. First check available executables (`ngspice`, `kicad-cli`, `python`) and report versions; then calculate ideal 5 W/10 W transformer values and create a **working simulation with measurable outputs**. State unresolved topology choices instead of fabricating results. Validate that the Spice transient solution and expected theoretical voltage divider agree; document how to reproduce the run. Include a concise design review noting what *doesn't work*.

### 8. Safety / simulation restriction

This project discusses potentially lethal 600–1000 V DC and hazardous stored energy. **Simulation and low-voltage test benches only** at this stage. Do not create mains wiring or build instructions for an energized kilovolt prototype. Any future physical HV design requires verified creepage/clearance, insulation and winding isolation, interlocks, bleeders, discharge verification, protective earth, current limiting, enclosures, and qualified HV engineering review.
