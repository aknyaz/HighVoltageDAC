# Preliminary array review: heat, metal backing and switching stress

Date: 22 November 2026. This closes a bounded preliminary review, **not** all
amplifier calculations or a physical HV design. The stock-based candidate and
3D envelope remain research artifacts, not released purchasing/layout data.

## Completion record

| Preliminary question | Result |
|---|---|
| Can all nominal positions use purchasable parts? | Complete: 3,052 ERA-8AEB1693V, one nominal value; archived stock observations exceed one-channel needs. |
| Do all ten nominal ratios and counts agree? | Complete: common +0.1241847% scaling; full 4,096-code structural DC verification passed. |
| Do DC voltage/current/power ratings pass the stated screen? | Complete: six-part minimum string passes the 700 V static screen with initial tolerance corners. |
| What is the mechanical scale? | Complete as an envelope: two 250 x 220 mm panels, 1,526 bodies each; no routing/clearance approval. |
| What thermal load must a thermostat handle? | Complete as a lumped preliminary calculation: about 25.28 W on a full-scale sine, up to 40 W total over static codes. |
| Is aluminum backing electrically neutral? | No: added capacitance can materially change the response; stackup is not selected. |
| Does static series sharing establish switching-voltage compliance? | No: executed edge fixtures expose unequal sharing. Pulse qualification is open. |
| Is 0.01% assembly accuracy guaranteed? | No: matching/calibration and working-condition verification remain open. |

The nominal-value sourcing question has a concrete solution. The dynamic
qualification question does not yet have a positive answer. Do not turn the
preliminary completion record into a claim that the array is ready for HV assembly.

## Thermal calculation

`python calc/resistor_array_preliminary.py` enumerates all 4,096 static codes in
the ideal matched 169 kohm assembly model, with 650 V analytical scaling and
10 kohm resistive load. The physical simulator is only driven at 5 V.

- Maximum resistor heat in one panel: **20.00 W**.
- Maximum heat summed across both panels: **40.00 W**.
- Rounded full-scale 1 kHz sine, 192 kS/s: **25.284 W total**.
- Maximum individual-chip static dissipation in that code/load sweep: **37.58 mW**.

The full-rail 700 V rating screen is a different, more conservative test; its
80.728 mW chip bound is not the normal sine-wave dissipation. The thermal result
excludes drivers, switches, heater input, transformer loss and capacitive loss.
Other loads/transients need separate evaluation. Uniform temperature is not
implied by a lumped heat calculation.

For a hypothetical 50 C panel and ambient Ta, heat rejection is
`Qout = (50-Ta)/theta`, where theta is panel-to-ambient thermal resistance in K/W.
Required equilibrium heater input is `Qout-Ppanel`; a negative result means
additional heat rejection is necessary. Example per panel, at 25 C ambient:

| Assumed theta | Heat rejection at 50 C | Heater with amplifier supply off | Extra rejection at 20 W panel heat |
|---|---:|---:|---:|
| 1 K/W | 25 W | 25 W | 0 W |
| 2 K/W | 12.5 W | 12.5 W | 7.5 W |
| 4 K/W | 6.25 W | 6.25 W | 13.75 W |

At 35 C ambient, theta must be no larger than about **0.75 K/W per panel** to
hold 50 C at the 20 W model maximum without active cooling, with the heater
turned off at that boundary. These are requirements for evaluating a future
thermal solution, not an achieved thermal resistance or selected heater size.
Warm-up time, spatial gradients, closed-loop stability and component-to-panel
thermal resistance have not been modeled.

## Aluminum-backed material screen

[JLCPCB's current material page](https://jlcpcb.com/help/article/jlcpcb-base-material)
lists an aluminum process with one copper layer, 1 W/mK dielectric thermal
conductivity and a 3000 V breakdown figure. Our 250 x 220 mm envelope fits its
listed size capability. The breakdown figure is not proof of allowable
continuous working voltage, lifetime, leakage or an insulation-system approval.
One copper layer also constrains routing of this large network.

An electrically insulated metal base can distribute heat and interface to a
cooler, but the copper-to-base dielectric also creates capacitance. Manufacturer
[Thermal Clad material data](https://dm.henkel-dam.com/is/content/henkel/Bergquist%20Comprensive%20Selection%20Guide%20-%20Thermal%20Cladpdf)
show that dielectric thickness and permittivity depend on the specific material;
those materials are not asserted to be JLCPCB's stackup.

Using `C = epsilon0 * epsilon_r * A / thickness`, a hypothetical node copper
area of 1-4 mm2, epsilon_r of 4-7 and dielectric thickness of 75-150 um gives
**0.236-3.306 pF**. These are assumed dimensions, not extracted pad/trace geometry.
Fringing, component capacitance, a floating metal base and inter-node coupling
are not represented by that simple parallel-plate estimate.

Four full-array AC simulations with the metal reference treated as AC ground
give the following additional loss near 20 kHz versus the zero-capacitance model:

| Capacitance from each internal string junction to ground | Additional attenuation |
|---|---:|
| 0 pF | 0 dB |
| 1 pF | 0.201 dB |
| 5 pF | 2.557 dB |
| 10 pF | 6.363 dB |

The latter two cases extend beyond the small-area estimate to screen larger
node copper and uncertainty. This is the same coherent analog excitation and
10 kohm load used in the earlier array study, not a switched audio THD result.
It establishes sensitivity, not the predicted response of an aluminum board.
Aluminum backing therefore remains an option to evaluate, not a selected stackup.

## Fast-edge voltage sharing: new qualification concern

Twenty-six ngspice fixtures apply a 5 V ramp to a six-resistor string with a
held-zero far end, starting discharged. Rise times are 20 and 100 ns. Internal
node-to-ground capacitance is 0, 0.02, 0.1, 1 or 5 pF; additional across-resistor
capacitance is 0, 0.05 or 0.2 pF for nonzero node capacitance. These capacitances
are explicit assumptions, not measured Panasonic or board parameters.

For a 20 ns edge, peak individual-chip voltage scaled linearly to 650 V is:

| Node-to-ground C | Across-resistor C | Peak chip voltage |
|---|---:|---:|
| 0 | 0 | 108.33 V |
| 0.02 pF | 0.05 pF | 220.04 V |
| 0.1 pF | 0.05 pF | 384.69 V |
| 1 pF | 0.05 pF | 590.43 V |
| 5 pF | 0.05 pF | 636.34 V |

The initial edge does not divide as a DC voltage divider: the series-junction
capacitances temporarily hold their prior voltages. The 150 V continuous element
rating cannot be used as proof that these repetitive pulses are acceptable.
Conversely, exceeding that continuous rating in a hypothetical short-pulse model
does not by itself prove physical destruction. Repetitive pulse-voltage/energy
limits, actual waveforms and parasitics must be established before acceptance.

The 0.1/0.05 pF, 20 ns case was repeated at 0.5 ns maximum timestep versus 1 ns:
peak voltage differed by **0.00284 V** after HV scaling. This checks numerical
resolution, not the validity of the assumed parasitic values. The held-zero end
is a screening fixture, not the complete amplifier load; source impedance and
real switching behavior are omitted. See
[edge plot](../output/resistor_array/edge_voltage_screen.png).

## Reproduction and next bounded step

Run these from the repository root:

```powershell
python calc/resistor_rating_audit.py
python calc/resistor_array_design.py
python calc/resistor_array_preliminary.py
python sim/run_phase_a.py
```

The new preliminary script saves all 27 transient decks (including refinement),
four AC decks, numerical results and ngspice logs. It does not modify the baseline
KiCad circuit or select an FPGA. The 3D artifacts remain envelope illustrations.

Next resolve **repetitive resistor pulse stress and parasitic capacitance** in
the candidate array with a bounded comparison of waveform control, rated parts
or a different assembly implementation. Carry the component-count/stock table
through any change. Do not proceed to a metal-backed layout merely because the
static power ratings pass. Vendor pulse data or a revised implementation may be
needed; this review deliberately does not claim that unknown data are verified.
