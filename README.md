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

The latest alternative is **`kicad/parallel/hv_rdac_parallel.kicad_pro`**;
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
a 4-bit KiCad project in `kicad/parallel/`. A segmented KiCad sheet is not yet supplied.

## 12-bit resistor mismatch

The [static tolerance study](docs/resistor_tolerance.md) evaluates bounded resistor
errors, endpoint INL/DNL, gain/offset, and monotonicity of the binary parallel network.

```powershell
python calc/resistor_tolerance.py
python sim/verify_resistor_tolerance.py
```

Results: `results/resistor_tolerance/`. Plots: `plots/resistor_tolerance/`.
Monte Carlo fractions describe the stated uniform-error scenario, not manufacturing yield.
