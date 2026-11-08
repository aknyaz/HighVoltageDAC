# Wired 4-bit parallel resistor DAC bench

## Open and read the circuit

Open `kicad/parallel/hv_rdac_parallel.kicad_pro` in KiCad 10, then
`hv_rdac_parallel.kicad_sch`. A preview is available at
`plots/kicad_parallel/hv_rdac_parallel.png`.

This is a complete low-voltage simulation sheet for the binary parallel
architecture. The original R–2R project in `kicad/full/` is unchanged.
All supply, signal, control, transformer, and return connections are drawn as wires.

In each arm, the four switched resistors are 16, 8, 4, and 2 kohm from LSB to MSB.
Their top ends join directly at one output node. Unlike R–2R, no series ladder
resistors separate these connections. The resulting conductance weights are 1:2:4:8.
Each SPDT selects 5 V or return for its branch; the PCM source underneath is its control.

The additional grounded 16 kohm resistor in each arm is intentional. It adds the
unit conductance needed to preserve the original code scale and 1 kohm arm output
resistance. The complete bridge output resistance is therefore 2 kohm.
The lower arm receives 15-D, complementary to the upper arm's code D.

The transformer connects directly between AOUT and BOUT. It uses the same linear
model as the R–2R bench: Lp=10 H, Ls=40 mH, K=1, and an 8 ohm secondary load.
The reflected primary load is 2 kohm. Keeping these values unchanged isolates the
effect of architecture in this demonstration; it does not replace the separate
600–700 V, 5–20 kohm equal-power study or select a physical transformer.

## Run the simulation

The local `hv_rdac_models.lib` contains the idealized switch, PCM, and transformer
models. Keep it beside the schematic. The sheet includes:

```spice
.tran 200n 100m 0 200n
.options reltol=1e-6 abstol=1e-12
```

Open **Inspect → Simulator** in the schematic editor and run the transient analysis.
If an analysis setup is requested, use the directive above: 100 ms duration and
200 ns output/maximum time steps. Plot `V(/SEC)` for the secondary output or
`V(/AOUT)-V(/BOUT)` for the primary voltage. The interface may display signal names
without the leading slash. Zoom to 98–100 ms for two settled 1 kHz periods.

The actual KiCad CLI export has been run in ngspice 46. The interactive simulator
window was not operated during this verification; no saved GUI waveform session
is included. This is an idealized model, not a real gate-driver or HV build schematic.

## Verification results

Run from the repository root:

```powershell
python kicad/verify_parallel.py
```

This exports the actual KiCad sheet, runs ERC, checks every component connection,
simulates the exported deck, and compares it with an independently generated
parallel-resistor netlist including the coupled-inductor transformer.

| Check | Result |
|---|---:|
| Simulation symbols | 29 |
| Verified component pins | 76 |
| Electrical nets | 21 |
| ERC errors / warnings | 0 / 0 |
| Secondary load power | 1.118695 mW |
| Supply power | 10.213791 mW |
| Total parallel resistor heat | 9.095086 mW |
| Original R–2R resistor heat in the same bench | 21.074253 mW |
| Heat reduction factor | 2.317 |
| Maximum secondary difference from independent parallel model | 2.83 nV |
| Power-balance residual over 92–100 ms | 10.3 nW |

The power balance includes a transformer with stored energy and a finite averaging
window; its small residual is not a real hardware-loss measurement. Useful output
agrees with the original R–2R bench to relative error 5.43e-9.

The 2.317 heat ratio belongs to this **4-bit, 5 V, 90%-command, 2 kohm** bench.
It is not expected to equal the roughly 6.3 ratio from the **12-bit, 650 V,
full-command, optimized-load** power study. Both comparisons have matching conditions
between architectures within their own test.

The 29 simulation symbols comprise 11 resistors (including the load), 8 SPDTs,
8 PCM sources, one reference supply, and one transformer. Ground is not counted.

Artifacts:

- `results/parallel_verification.json` — measured values and checks.
- `results/parallel_erc.rpt` and `results/parallel_netlist.xml` — KiCad exports.
- `results/parallel_kicad.cir` — portable SPICE export; relative include assumes execution from `results/`.
- `sim/generated/parallel_transformer.cir` — independent low-voltage reference.
- `plots/parallel_kicad_verification.png` — waveform comparison.

`python kicad/generate_parallel.py` regenerates this project and its local models.
Preserve manual edits first: regeneration replaces the generated sheet and settings.
Future work remains resistor mismatch, leakage, switching delay/capacitance,
transformer bandwidth and DC/startup behavior, followed by a 12-bit schematic.
