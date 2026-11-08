# Complete wired KiCad simulation bench

## Open the project

Open `kicad/full/hv_rdac_full.kicad_pro` in KiCad 10, then open
`hv_rdac_full.kicad_sch`. This is a new project; the original passive-core project
remains available at `kicad/hv_rdac_core.kicad_pro`.

The full sheet uses A3 landscape. All power, signal, control, and return connections
are drawn as wires. Labels identify probe points; they are not used to connect
otherwise isolated circuit blocks. Dots identify connected intersections.

## Reading the sheet

- The upper arm receives code D; the lower arm receives its complement, 15-D.
- Bits run left to right from LSB to MSB. Each ladder has four 2 kohm bit resistors,
  three 1 kohm series resistors, and a 2 kohm termination on its left end.
- Each pulse-source symbol represents one bit of the sampled PCM sequence.
  The eight sources together implement a 1 kHz, 90%-full-scale rounded sine,
  sampled at 192 kS/s with 1 ns transitions.
- Each SPDT symbol selects the 5 V reference when its control is 1 and return
  when its control is 0. Its local subcircuit contains the same two complementary
  voltage-controlled switches and inversion used in the independent Phase A bench.
  These are idealized electronic switches, not mechanical relays or selected HV devices.
- V1 is the shared 5 V supply. The supply and return rails are visibly connected
  between both arms. There is no separate analog output amplifier.
- T1 connects directly between A3 and B3. Its model contains Lp=10 H, Ls=40 mH,
  K=1. R17 is the 8 ohm secondary load, reflecting 2 kohm to the primary.
- The secondary return is connected to simulation ground, matching the original
  bench. This is a reference choice for simulation, not a physical isolation design.

## Run in KiCad

1. Open the full schematic and select **Inspect → Simulator**.
2. The schematic contains `.tran 200n 100m 0 200n` and the solver options. If an
   analysis setup is requested, use transient analysis with a 200 ns time step,
   100 ms final time, 0 start time, and 200 ns maximum time step.
3. Run the simulation. Plot `V(/SEC)` for the speaker-load voltage. Signal names
   may be displayed without the leading slash in the interface.
4. Plot `V(/A3)` and `V(/B3)` to inspect each arm. To inspect the voltage across
   the primary, add the expression `V(/A3)-V(/B3)`.
5. Zoom to 98–100 ms to see two settled sine periods. Measurements in the
   verification script use the 92–100 ms window.

`hv_rdac_models.lib` is stored beside the schematic, and symbols reference it with
a relative path. Keep these files together when sharing the project. Model mappings
can be inspected through each symbol's Simulation Model settings.

The schematic's CLI export and execution in ngspice 46 have been tested. The
interactive simulator window has not been operated as part of this verification;
no saved GUI waveform session is supplied.

KiCad documents schematic simulation directives and subcircuit model assignment in
its [Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html).

## Reproducible verification

From the repository root, run `python kicad/verify_full.py`. It exports the actual
sheet, runs ERC, checks connectivity against the intended circuit, simulates the
exported SPICE deck, and compares the output with the independent Phase A model.

Verified with KiCad 10.0.1 and ngspice 46:

| Check | Result |
|---|---:|
| Connected simulation symbols | 35 |
| Checked component pins | 88 |
| Distinct electrical nets | 27 |
| ERC errors / warnings | 0 / 0 |
| Load power | 1.118695 mW |
| Supply power | 22.192952 mW |
| Maximum secondary waveform difference, 98–100 ms | 6.65 nV |
| Relative load-power difference from Phase A | 1.30e-8 |

The 35 symbols comprise 17 resistors, 8 SPDT models, 8 PCM source models,
one supply, and one transformer; the ground symbol is not counted as a component.

Outputs: `results/full_verification.json`, `results/full_erc.rpt`,
`results/full_kicad.cir`, and `plots/full_kicad_verification.png`.
The saved SPICE export uses a relative include path intended for execution from
the `results/` directory. The verifier re-exports it with a resolved path before each run.

This is a complete **simulation schematic**, not a hardware-ready amplifier.
The models still omit real gate drivers, device capacitance, resistor tolerances,
transformer loss and saturation. It does not validate a 5–10 W HV build.
