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

Open `kicad/hv_rdac_core.kicad_pro`, then the `hv_rdac_core.kicad_sch` schematic.
The initial sheet shows both R–2R arms and the verification load. Net labels connect
branches; D_A0…3 and D_B0…3 identify inputs from the switches. **Sources, switches,
and the transformer are currently implemented only in the complete SPICE files.**
Simulation through the KiCad interface is not yet configured for this passive sheet;
no PCB has been created.

Results and limitations: `docs/phase_a_results.md`. Next steps: `docs/plan.md`.
