# HV-RDAC

A research project exploring a resistive DAC as a power stage with an output transformer.
Current status: **simulation studies of a 12-bit 3+9 segmented DAC**, with
the original 4-bit core retained as a regression bench; not a finished 5-10 W amplifier.

The [100 V versus 650 V supply study](docs/supply_voltage_study.md) compares
low-level audio with rescaled digital codes using the existing transformer and
switch models. All voltages are simulation parameters, not hardware validation.

## Resistor-array preliminary review (22 November 2026)

- [Complete resistor assembly table and sourcing](docs/resistor_array_candidate.md):
  3,052 identical 169 kohm chips per mono channel, with explicit series/parallel groups.
- [Thermal, aluminum-backing and fast-edge review](docs/resistor_array_preliminary.md):
  preliminary screen complete; repetitive chip pulse-voltage compliance remains open.
- [Interactive offline 3D envelope](output/resistor_array/resistor_array_3d.html),
  two illustrative 250 x 220 mm arm panels, not an HV PCB layout.
- [Predicted prototype BOM PDF](output/pdf/HV_RDAC_Predicted_Bill_of_Materials.pdf).

Reproduce with `python calc/resistor_array_design.py` and
`python calc/resistor_array_preliminary.py`. The BOM PDF builder is
`python docs/build_predicted_bom.py`; install its optional dependency with
`python -m pip install -r requirements-docs.txt`.

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

## Audio-band and low-level findings

The [audio-band study](docs/audio_band.md) identifies two limitations: the assumed
10 H transformer is down 12.22 dB at 20 Hz, and a 1% full-scale 1 kHz sine produces
0.531% THD in the switched model (0.520% with ideal held 12-bit codes). The latter
includes requests rounded to a 50 MHz grid. Five ngspice runs and independent
AC/Fourier calculations support these results.

```powershell
python sim/audio_band.py
python sim/transformer_bandwidth.py
```

A conditional -1 dB / 20 Hz target requires about 78 H under the stated fixed
parasitic assumptions. Actual transformer validation and low-level quantization
now take priority. Keep 3+9 / 200 ns; shutdown and full switched upper-band tests
remain open. Results and plots are in `results/audio_band/` and `plots/audio_band/`.

## Transformer working candidate

The [transformer selection](docs/transformer_selection.md) chooses
**Lundahl LL1679/PP, standard core, secondary alternative B / 8 ohm** for the
next modeling stage, with LL1620/PP as the higher-inductance fallback. Twenty-four
verified AC sweeps use datasheet winding parameters and explicitly assumed
capacitance/core loss. This is not procurement or hardware approval; the full
5 W / 20 Hz target at 600-700 V remains unproven.

```powershell
python sim/select_transformer.py
```

[Supplier inquiry draft](docs/transformer_vendor_inquiry.md) is prepared but not sent.

## Low-level quantization trade-off

The [quantization study](docs/quantization_study.md) compares rounding, triangular
dither and first/second-order error feedback over 128 numerical trials. At 1%
input, second-order EF reduces modeled 20 Hz-20 kHz error from 0.611% to 0.292%,
but adds switching activity. The conditional 650 V Coss-only idle estimate is
38.3 W, so it remains a software candidate and is not enabled in HDL.

```powershell
python calc/quantization_study.py
```

The model requires a high-precision source before 12-bit quantization. Next:
explicit idle/start/stop policy and transformer-energy validation, followed by
full switched-model evaluation. This is not a measured hardware noise result.

## Higher sample rates

The [192/384/768 kS/s study](docs/sample_rate_study.md) reuses the same model and
executes 384 trials. With second-order error feedback, 1%-input in-band error
falls from 0.292% to 0.0531% and 0.00985%. Conditional Coss-only losses rise from
10.4 to 20.4 and 40.9 W on that signal, and 38.3 to 76.4 and 153.0 W at silence.
These are spectral/linear and hard-switch-budget scenarios, not new analog
transient validation. Keep 192 kS/s as baseline and 384 kS/s as the next analog
candidate; address idle and commutation behavior before adopting a higher rate.

```powershell
python calc/sample_rate_study.py
```

Results: `results/sample_rates/comparison.json`; plot: `plots/sample_rates/comparison.png`.

## Quiet state and stored magnetic energy

The [stored-energy study](docs/shutdown_study.md) runs 24 structural ngspice
transients with both current polarities, loaded/open secondary and timestep
refinement. In the imposed 50 uA, 5 V open-load fixture, holding all lower
switches on reduces the primary peak from 4.517 V (all off, unclamped) to
0.476 V, but leaves 13.77 uA after 20 ms. Generic rail clamps are not validated
device models. A dedicated healthy-control quiet state remains a proposal;
entry/exit sequencing and loss-of-drive behavior still require validation.

```powershell
python sim/shutdown_study.py
```

## Audio-to-quiet sequencing

The [quiet-transition study](docs/quiet_transitions.md) completes 16 ngspice
runs at 5 V, including timestep refinement, 100 ns arm skew and a seeded
+/-0.01% resistor-error scenario. A 2 ms audio fade followed by a 2 ms common-mode
move to all-low reduces transition-error peak from 8.061 to 0.306 mV in the
combined skew/mismatch case, relative to each sequence's ideal-code reference.
Adopt this as the working mute candidate for controller integration; no HDL or
hardware protection change is included. Keep supervised refresh during quiet:
the existing 1 ms watchdog must not be allowed to mistake mute for lost PCM.

```powershell
python sim/quiet_transitions.py
```

Plot: `plots/quiet_transitions/comparison.png`; results: `results/quiet_transitions/summary.json`.
The 1 kHz loaded fixture does not establish general click-free behavior or
nonlinear magnetic limits.

## Implemented FPGA mute logic

The [mute wrapper](docs/fpga_mute.md) now implements the 24-bit PCM envelope,
independent arm commands, reversible 384-sample ramps and supervised quiet hold
in Amaranth, with generated Verilog. Executed RTL tests cover 1,761 default-rate
samples, 547 additional reversal/fault samples and 36 phase/fault combinations.
The existing 5,096-code core regression still passes. Device-mapped FPGA timing,
resource fit and analog replay of actual RTL gate edges remain unvalidated.

## Executed RTL-to-analog replay

The [RTL replay](docs/rtl_mute_replay.md) now exports actual mute-controller
commands and runs them through the nominal 5 V structural network. The full
startup/mute/resume trace includes 2,688 samples and 4,947 gate-vector changes.
Four ngspice runs pass timestep checks; peak error against ideal accepted codes
is 0.2734 mV. This is one-way replay, not physical FPGA timing or analog fault
feedback. FPGA selection and implementation are deferred while simulation
coverage is completed.

```powershell
.venv/control/Scripts/python.exe control/export_mute_edges.py
python sim/rtl_mute_replay.py
```

## Low-frequency magnetic memory and DC

The [20 Hz study](docs/low_frequency_mute.md) completes 35 ngspice runs using
four interruption phases, four PCM offsets, a 200 ms quiet hold and resume.
In the continuous 5 V equivalent, a zero-offset parked output tail reaches
12.109 mV and takes about 142 ms to decay to 1%. A +1% input offset produces
4.668 uA primary DC even though secondary steady DC is zero. Independent
state-space and algebraic checks pass. This is not a switching or nonlinear-core
qualification; the 2 ms fade remains a 1 kHz reference, not a full-band solution.
Next compare longer fades and DC rejection. FPGA vendor/device/cost and physical
implementation decisions are deferred until the simulation findings are settled.

```powershell
python sim/low_frequency_mute.py
```

## Audio viability checkpoint

The [preliminary audio review](docs/audio_viability.md) consolidates 272 static
single-tone records, 51 two-tone records and four independently checked AC
sweeps. At 1 kHz, nominal 12-bit undithered THD rises from 0.01029% at 90%
amplitude to 0.51808% at 1% and 20.04% at 0.1%. The nominal response is flat,
but output impedance is about 8.33 ohm. These are model findings, not complete
hardware THD or noise predictions. Pause detailed mute/FPGA work while judging
low-level quality and load dependence; switched-model checks are reported
separately from this static screen.


The subsequent six switched checks on the LL1679 model give approximately
0.011% THD at 90% amplitude and 0.530% at 1%, with about 0.026% total in-band
unwanted content for 19/20 kHz tones. The small IMD figures use documented slow
startup-tail removal and window/timestep checks; raw values are retained.
See the [completed review](docs/audio_viability.md) and
[switched spectra](plots/audio_viability/switched.png). This supports an audio
viability decision now; it is not a completed hardware-quality qualification.
