# High-voltage switch candidates and first nonideal model

Research date: 2026-11-09. Simulation only; no purchasing decision or hardware BOM.

## Candidate screen

The likely intended gallium technology is gallium nitride (GaN), rather than
gallium arsenide (GaAs). A device must withstand the full supply when its opposite
half-bridge device conducts. A 650 V rating does not support a 700 V rail; operation
at a 650 V absolute maximum also leaves no transient margin.

| Candidate | Technology / rating | Decision for this study |
|---|---|---|
| Wolfspeed C3M0350120D | SiC, 1200 V | First parameter reference; not yet a qualified device selection |
| ST STP3N150 | Silicon MOSFET, 1500 V | Higher-resistance comparison reference |
| TI LMG3650R070 | GaN, 650 V, integrated driver | Excluded for a 700 V rail; reconsider only with a lower supply and stress analysis |
| Transphorm TP90H180PS | Cascode GaN, 900 V | Manufacturer datasheet marked Discontinued; excluded for new design |

Sources: [Wolfspeed active product listing](https://www.wolfspeed.com/products/power/sic-mosfets/1200v-silicon-carbide-mosfets/),
[ST product page](https://www.st.com/en/power-transistors/stp3n150.html),
[TI product page](https://www.ti.com/product/LMG3650R070),
[Transphorm manufacturer datasheet hosted by Mouser](https://www.mouser.com/datasheet/2/970/datasheet_tp90h180ps_900v_gan_fet_20210308-1539030.pdf).
This is a shortlist, not an exhaustive claim about available GaN voltage classes.
Stock, price, and delivery have not been established.

## Parameters and provenance

The [C3M0350120D datasheet, revision 04](https://assets.wolfspeed.com/uploads/2024/01/Wolfspeed_C3M0350120D_data_sheet.pdf)
specifies typical Ron 0.350 ohm (maximum 0.455 ohm) at Vgs 15 V and Id 3.6 A.
Typical Coss is 20 pF at Vds 1000 V, not across the whole voltage swing. Typical
gate charge is 19 nC under its stated 800 V switching test. Drain leakage at
1200 V is 1 uA typical, 50 uA maximum. These conditions do not establish behavior
at our much smaller branch currents. The capacitance curves are nonlinear.

The [STP3N150 datasheet, DS5052 revision 13](https://www.st.com/resource/en/datasheet/stp3n150.pdf)
specifies Ron 6 ohm typical, 9 ohm maximum at Vgs 10 V and Id 1.3 A; Coss is
102 pF typical at Vds 25 V. Its time-equivalent capacitance over 0–1200 V is
100 pF; that quantity is not an energy-equivalent capacitance. These references
are deliberately not treated as comparable capacitance measurements at 650 V.

Three simulation profiles were added:

- `sic_20pf`: Ron 0.35 ohm, constant 20 pF across each of two switches.
- `sic_100pf_sensitivity`: same Ron, assumed 100 pF per switch; sensitivity only.
- `silicon_102pf`: Ron 6 ohm, constant 102 pF per switch.

**These are linear parameter surrogates, not manufacturer transistor models.**
No actual GaN transistor model has been added. Their 5 V supply preserves the
linear RC equations for the chosen constants, but cannot reproduce voltage-
dependent capacitance, leakage, diode conduction or gate-drive behavior at 650 V.
No Coss datum has been silently relabeled as the device's effective 650 V value.

## SPDT implementation implications

One rail-selecting SPDT function corresponds to two controlled power devices in
a half bridge. Thus 24 binary SPDT functions imply 48 transistors, and 46 segmented
functions imply 92, before drivers. The present surrogate places one capacitor
across each device and opens the outgoing switch before closing the incoming one.

Upper-device gate drive is referenced to its moving source. Codes can remain
constant indefinitely, so a future driver solution must explicitly support held
high states; periodic refresh cannot be assumed. Isolation, driver quiescent
power, timing mismatch and device reverse conduction remain unresolved.

Our segmented branch resistances range from about 84.4 kohm to 21.6 Mohm.
At 650 V, the rail-to-rail current bounds are only about 7.7 mA and 30 uA.
Consequently, very low Ron is less valuable than it is in an ampere-scale power
converter. Leakage near a switch node is often shunted by the conducting device;
it must be modeled at its actual location rather than equated directly to DAC
output error. Board leakage across high-value resistors is a separate issue.

## Executed transient experiment

Run `python sim/nonideal_switches.py`.

Both architectures undergo 2047 to 2048, with three profiles and four timing
cases: (dead time, heavy-branch skew) = (0,0), (20,0), (20,20), (100,20) ns.
Each case repeats with maximum timesteps of 1 ns and 0.5 ns: 48 SPICE runs.
Initial and final voltages are checked against an independent DC nodal solution
including Ron. All checks pass. The largest absolute-area difference on timestep
halving is 0.0521 LSB ns. The comparison permits 0.1 LSB ns plus 0.5%.

For the 20 pF SiC surrogate with 20 ns dead time and 20 ns skew:

| Architecture | Peak error | Absolute error area |
|---|---:|---:|
| Binary | 2047.70 LSB | 40892.08 LSB ns |
| Segmented | 255.99 LSB | 5135.40 LSB ns |

The approximate eightfold advantage survives this experiment. This does not
establish audio THD or cover all PCM transitions. Error is measured relative to
the instantaneous final code, so even an ordinary finite settling edge contributes
to the metric. With no skew, a dead interval can itself produce an error.

The model still omits gate-controlled slew, nonlinear Coss/Qoss, body diodes,
reverse recovery, driver impedance, inductive overshoot and the transformer.
Very fast Ron*C edges and their peak currents are not device predictions.

## Capacitive power: a newly quantified risk

Independent analytical scenario: count every branch-node transition in both arms
over one rounded full-range 1 kHz sine period at 192 kS/s, including wraparound.
There are 1480 binary and 1436 segmented transitions per millisecond.

For two equal **linear** capacitors C in a half bridge, a fully hard-switched
rail-to-rail node transition dissipates C*Vbus^2 if there is no energy recovery.
This includes charging one capacitor and discharging the other. Therefore:

| Constant C per transistor | Binary, 650 V | Segmented, 650 V |
|---|---:|---:|
| 20 pF | 12.506 W | 12.134 W |
| 100 pF | 62.530 W | 60.671 W |

These are sensitivity estimates, **not measured or predicted C3M0350120D losses**.
They are separate from the 5 V transient runs and exclude gate-drive and overlap
losses. Real nonlinear devices require charge/energy curves and commutation
analysis; dead-time current can alter how much energy is recovered. Do not use
the 1000 V point capacitance as a guaranteed lower or upper bound at 650 V.

This matters because the previous ideal segmented resistor heat was about 25.3 W
for the 5 W target. The benefit of segmentation does not automatically extend to
capacitive losses: the PCM transition counts in this scenario are similar.

## Next decision

Keep the SiC device as a modeling reference. Before buying or drawing a final
92-device implementation, obtain and validate a compatible manufacturer model
or build a documented nonlinear charge model, then check switching energy,
driver consumption, held-code behavior and leakage at temperature. Search for
smaller-die low-capacitance parts as well; the lowest Ron is not our objective.

Artifacts: `sim/nonideal_switches.py`, `sim/generated/nonideal_switches/`,
`results/nonideal_switches/summary.json`, and `plots/nonideal_switches/midscale.png`.
