# HV-RDAC

A research project exploring a resistive DAC as a power stage with an output transformer.
Current status: **a low-voltage simulation of a 4-bit core**, not a finished 5–10 W amplifier.

## Repository layout

- `docs/` — original brief, project plan, assumptions, and architecture comparisons.
- `calc/architecture.py` — ideal transformer and Thevenin source calculations.
- `calc/power_trade_study.py` — equal-output-power sweep including every ladder resistor.
- `sim/verify_power_study.py` — independent nodal and scaled 5 V SPICE verification of the sweep.
- `sim/run_phase_a.py` — circuit generation, ngspice execution, and verification.
- `sim/generated/*.cir` — complete standalone SPICE circuits with switches and sources.
- `results/` — measured values in JSON, waveform CSV files, and the ngspice log.
- `plots/` — code mapping, sine waveforms, spectra, and major-carry transitions.
- `kicad/hv_rdac_core.kicad_pro` — initial KiCad project with an editable passive core.
- `kicad/full/hv_rdac_full.kicad_pro` — complete wired simulation schematic with PCM sources,
  switches, both ladders, reference supply, transformer, and load.
- `kicad/parallel/hv_rdac_parallel.kicad_pro` — complete wired 4-bit parallel resistor alternative.

## Running the simulations (PowerShell, from the repository root)

```powershell
python -m pip install -r requirements.txt
python calc/architecture.py
python sim/run_phase_a.py
```

Verified environment: Python 3.13.3, KiCad 10.0.1, ngspice 46 shared library.
Default DLL location: `C:\Program Files\KiCad\10.0\bin\ngspice.dll`.
Set the `NGSPICE_DLL` environment variable to use another path. The adapter currently targets Windows.
The simulator does not require a graphical interface.
With a standalone ngspice CLI, circuits can also be run using, for example,
`ngspice -b -r output.raw sim/generated/code_sweep.cir`.

## KiCad

The selected 12-bit design review is **`kicad/segmented/hv_rdac_segmented.kicad_pro`**.
The earlier 4-bit simulation alternative is **`kicad/parallel/hv_rdac_parallel.kicad_pro`**;
see [the parallel bench walkthrough](docs/kicad_parallel_bench.md). It preserves
the reference bench's 5 V supply, output resistance, PCM, and transformer for a direct comparison.

Open **`kicad/full/hv_rdac_full.kicad_pro`**, then `hv_rdac_full.kicad_sch`.
This A3 sheet contains the complete wired test bench. Local SPICE models and a transient
directive are included. See [the walkthrough](docs/kicad_full_bench.md) for signal names,
simulation setup, model details, and verification results.

The original `kicad/hv_rdac_core.kicad_pro` remains as the passive-core reference.
No PCB has been created.

To export and verify the complete schematic, including its actual SPICE netlist:

```powershell
python kicad/verify_full.py
```

The verifier uses the installed KiCad CLI; override its location with `KICAD_CLI` if needed.
`python kicad/generate_full.py` regenerates the full project and overwrites its generated
schematic and project settings. Preserve any manual edits before running it.

Results and limitations: `docs/phase_a_results.md`. Next steps: `docs/plan.md`.

## Power and impedance study

The completed [equal-power study](docs/power_trade_study.md) compares 600–700 V
targets, 5–20 kohm reflected primary loads, and 4/12-bit ladders at 5 and 10 W
of useful sine output. The SPICE checks run at 5 V and scale the results analytically.

```powershell
python calc/power_trade_study.py
python sim/verify_power_study.py
```

Tables and verification data are in `results/power_study/`; charts are in
`plots/power_study/`. These are ideal architecture comparisons, not hardware ratings.

## Alternative resistive architectures

The [parallel resistor comparison](docs/resistive_architecture_comparison.md) evaluates
binary-weighted branches and a defined thermometer/binary segmented network against
the R–2R reference at equal useful output power. It includes all resistor losses,
switch counts, resistor ranges, idle dissipation, and independent SPICE checks.

```powershell
python calc/power_trade_study.py
python calc/compare_resistive.py
python sim/verify_resistive_comparison.py
```

Results are in `results/resistive_comparison/`, the chart is in
`plots/resistive_comparison/`, and low-voltage decks are in
`sim/generated/resistive_comparison/`. The binary parallel alternative now has
a 4-bit KiCad project in `kicad/parallel/`. The selected 12-bit segmented design review is described below.

## 12-bit resistor mismatch

The [static tolerance study](docs/resistor_tolerance.md) evaluates bounded resistor
errors, endpoint INL/DNL, gain/offset, and monotonicity of the binary parallel network.

```powershell
python calc/resistor_tolerance.py
python sim/verify_resistor_tolerance.py
```

Results: `results/resistor_tolerance/`. Plots: `plots/resistor_tolerance/`.
Monte Carlo fractions describe the stated uniform-error scenario, not manufacturing yield.

The [4+8 segmented tolerance study](docs/segmented_tolerance.md) now compares the
same error bounds against the binary network, including explicit complementary
thermometer decoding and full-code SPICE checks:

```powershell
python calc/segmented_tolerance.py
python sim/verify_segmented_tolerance.py
```

It reads the binary baseline from `results/resistor_tolerance/summary.json`.
New results and plots are in `results/segmented_tolerance/` and `plots/segmented_tolerance/`.

## 12-bit switching skew

The [switching timing study](docs/switching_glitches.md) compares ideal-switch
binary and segmented carry glitches with exact event calculations and 72 SPICE
transient runs. This isolates timing skew; device capacitance and transformer
response remain unmodeled.

```powershell
python sim/compare_switching_glitches.py
```

Results: `results/switching_glitches/`. Plot: `plots/switching_glitches/midscale_glitch.png`.

## High-voltage switch references

[Device research and nonideal switch results](docs/switch_candidates.md) compare
SiC, silicon, and GaN candidates and introduce linear Ron/Coss/dead-time surrogates.
They are not vendor transistor models. The report also quantifies a capacitive
switching-loss sensitivity that was absent from the ideal resistor heat study.

```powershell
python sim/nonideal_switches.py
```

The [nonlinear charge and driver budget](docs/sic_charge_and_drivers.md) integrates
an approximate datasheet Coss curve, verifies scaled charge-work calculations in
SPICE, and estimates driver bias overhead. It is not a manufacturer MOSFET model.

```powershell
python calc/sic_charge.py
python sim/verify_sic_charge.py
```

## Selected working architecture

The [partition decision](docs/partition_decision.md) freezes **3+9 segmented parallel**
as the next 12-bit implementation baseline: 32 SPDT functions / 64 transistors.
It compares seven splits, 210000 mismatch networks and eight full-code SPICE sweeps.
The existing KiCad benches remain references. A wired 34-sheet 3+9 design review is
now available in `kicad/segmented/hv_rdac_segmented.kicad_pro`, with candidate FETs,
drivers and a status-tagged BOM. See [opening instructions and limitations](docs/kicad_segmented_review.md).
The PDF is `plots/segmented_review/schematic.pdf`. Control HDL is implemented and tested; physical FPGA wiring, isolated bias and the
transformer remain unfinished. This is not a complete vendor-model simulation.

```powershell
python calc/partition_study.py
python sim/verify_partition_study.py
```

## Digital command controller

[Controller implementation](docs/controller_design.md) adds complementary 3+9
code decoding, per-branch 200 ns command non-overlap and latched fault handling.
All 4096 codes and 1000 random transitions pass behavioral HDL simulation.
The 64 command paths and 192 enable/status connections are checked against the
exported KiCad netlist. See [reproduction commands](control/README.md).
Physical FPGA wiring and timing qualification remain open; the initial analog study below includes this blank interval and a linear transformer.
Audio-band, low-level and shutdown validation remain open.

## Controller blanking with transformer loading

The [analog controller study](docs/controller_analog.md) runs the 3+9 network at
5 V with an assumed linear transformer, comparing 0/200 ns blanking and fixed
20/100 pF per-device capacitance. Eight sine and sixteen major-carry SPICE runs
include timestep refinement and settling checks. At 1 kHz / 90% amplitude the
20 pF case changes from 0.01031% to 0.01070% THD. This is not a vendor transistor
or transformer qualification. Retain 200 ns for further simulation.

```powershell
python sim/controller_analog.py
python sim/verify_controller_analog.py
python sim/controller_transitions.py
```

Results: `results/controller_analog/`; plots: `plots/controller_analog/`.
