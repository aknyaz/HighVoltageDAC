# HV-RDAC

A research project exploring a resistive DAC as a power stage with an output transformer.
Current status: **a low-voltage simulation of a 4-bit core**, not a finished 5–10 W amplifier.

## Repository layout

- `docs/` — original brief, project plan, assumptions, and architecture comparisons.
- `calc/architecture.py` — ideal transformer and Thevenin source calculations.
- `sim/run_phase_a.py` — circuit generation, ngspice execution, and verification.
- `sim/generated/*.cir` — complete standalone SPICE circuits with switches and sources.
- `results/` — measured values in JSON, waveform CSV files, and the ngspice log.
- `plots/` — code mapping, sine waveforms, spectra, and major-carry transitions.
- `kicad/hv_rdac_core.kicad_pro` — initial KiCad project with an editable passive core.
- `kicad/full/hv_rdac_full.kicad_pro` — complete wired simulation schematic with PCM sources,
  switches, both ladders, reference supply, transformer, and load.

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
