# First simulation results — 2026-11-08

Run: `python sim/run_phase_a.py`. Full values: `results/summary.json`.
Engine: ngspice 46 bundled with KiCad 10.0.1; Python 3.13.3.

## Verification

Across 16 constant codes with a 2000 ohm load, the maximum deviation from
Vout=5*(2D-15)/16*0.5 was 5.45e-10 V. This verifies the idealized topology,
not the physical accuracy of resistors.
Average supply power during the code sweep was 21.5088 mW,
total dissipation in both ladders was 20.4712 mW, and load power was 1.03760 mW.
The balance of these three quantities is checked automatically.

| 1 kHz sine | 90% of full scale | 25% of full scale |
|---|---:|---:|
| Power into 8 ohm | 1.11869 mW | 0.0752583 mW |
| Dissipation in all ladder resistors | 21.0743 mW | 22.5932 mW |
| Supply power | 22.1930 mW | 22.6685 mW |
| THD, harmonics 2–20 | 2.546% | 18.223% |
| Mean primary voltage | -13.2 uV | -11.5 uV |
| Mean primary current | 6.61 nA | 5.74 nA |

These THD values describe the **4-bit** test without noise or core nonlinearity.
They do not characterize the future 12-bit amplifier. FFT conditions are listed in assumptions.md.
The residual mean values reflect the finite measurement window, settling, and numerical precision;
exactly zero DC and robustness to mismatch have not been demonstrated.

The initial 20 ms run was insufficient to meet the selected mean-voltage criterion.
The duration was increased to 100 ms, with measurements taken over 92–100 ms.
This illustrates why symmetric PCM does not eliminate startup transients.

## Initial findings

1. The baseline R–2R topology works and agrees with its Thevenin equivalent.
2. Internal ladder dissipation remains substantial even at low signal levels.
3. Adding a 20 ns delay for each successive bit produces a major-carry glitch;
   ideal simultaneous switches conceal this effect. See plots/major_carry.png.
4. The 5–10 W targets have not been validated. Real switches and a real transformer are not yet modeled.

## KiCad status

An editable passive core sheet has been created: 16 ladder resistors and a load resistor.
The complete working simulation bench is in sim/generated, rather than in this sheet.
The exported netlist is checked using `python kicad/check_core.py`.
Verification passed for all 17 resistors. ERC reported 0 errors and 8 warnings
about isolated labels D_A0…3/D_B0…3, which are inputs from switches not yet added to the sheet.
The next iteration should add the sources, switches, and transformer to the KiCad sheet itself.

When loading the DLL, ngspice reports that spinit was not found. The simulations ran
using built-in R/L/K/S/B/V models and explicitly specified options; XSPICE modules are not used.
