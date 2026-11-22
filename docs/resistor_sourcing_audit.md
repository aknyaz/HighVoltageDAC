# Precision resistor sourcing and rating audit

Research date: 21 November 2026. Status: **not a released purchasing BOM**.

Follow-up: [complete single-value candidate](resistor_array_candidate.md) now
maps all 34 positions to 3,052 stocked 169 kohm parts, with a common nominal
resistance scaling, structural simulations and an illustrative 3D envelope.
The initial audit below is retained as the pre-selection record.

## Conclusion

Stocked precision and high-voltage resistor families exist. However, the current
34 resistor assembly positions have not been mapped to a complete, stocked BOM
that meets the existing 0.01% resistance-error scenario under working conditions.
The previous budget's USD 200-600 resistor allowance remains provisional. Do not
interpret availability of inexpensive 0.1% parts as closure of this requirement.

The current baseline in `partition_decision.md` is 3+9 segmentation with 0.01%
bounded resistance errors, including terminations. It is not the earlier 4+8
study, and neither 1% nor unselected 0.1% components guarantee its performance.
At 0.1%, only 68.1% of the sampled independent 3+9 networks met 0.5 LSB INL.

## Calculated electrical requirements

Reproduce with `python calc/resistor_rating_audit.py`. Results, including all ten
resistance groups, are in `results/resistor_rating_audit/summary.json` and
`results/resistor_rating_audit/rating_table.md`.

The calculation enumerates all 4096 codes for matched ideal switches/resistors,
650 V analytical scaling, and resistive primary loads of 10 kohm and 9522 ohm
(34.5 squared times 8 ohm). These are quasi-static calculations, not transformer
transient simulations. Full-rail bounds are screening values conditional on
nodes remaining within the supply rails; ringing and faults can exceed them.

| Assembly group | Quantity | Nominal resistance | Static maximum power | Current at full 650 V | Power at full 650 V | Power at full 700 V |
|---|---:|---:|---:|---:|---:|---:|
| Coarse, weight 512 | 14 | 42.197597 kohm | 4.6645 W | 15.4037 mA | 10.0124 W | 11.6120 W |
| Highest fine bit, weight 256 | 2 | 84.395194 kohm | 2.5447 W | 7.7019 mA | 5.0062 W | 5.8060 W |
| Weight 8 | 2 | 2.700646 Mohm | 0.0862 W | 0.2407 mA | 0.1564 W | 0.1814 W |
| Weight 1, including terminations | 4 | 21.605170 Mohm | 0.0108 W | 0.0301 mA | 0.0196 W | 0.0227 W |

The coarse static peak voltage is 443.66 V. Some other positions reach about
483 V. The sum of all resistor losses for a rounded full-scale 1 kHz sine at
192 kS/s and the 10 kohm reference load is 25.3092 W. Individual maxima do not
occur simultaneously; adding full-rail power bounds is not a supply-power estimate.

For each individual part, require both voltage and power compliance:
`V <= min(V_working, sqrt(P_allowed(T) * R))`; current follows `I = V/R`.
Use temperature-derated power, not only a catalog wattage. Series/parallel
assemblies must also be assessed for imbalance, pulse stress and parasitics.

## Distributor evidence and candidate screening

The following are distributor page/index snapshots, not reserved stock or a live
checkout confirmation. Regional/cached pages disagree on quantities, and some
direct page reads returned HTTP 403. The counts therefore document observed
availability, not an exact guaranteed count at purchase time. Links identify
specific manufacturer part numbers, not merely a family catalog.

| Part | Specifications | Observed stock | Assessment |
|---|---|---|---|
| Vishay CPF2100K00BEB14 | 100 kohm, 0.1%, 25 ppm/K, 2 W at 70 C, 350 V working limit | Mouser listing: 499 | Potential power-assembly element. Not a standalone 650 V resistor and not one of our exact target values. |
| Vishay TNPW1206100KBEEA | 100 kohm, 0.1%, 25 ppm/K, 200 V working limit; up to 0.52 W depending on operating mode | DigiKey listing: 44,757; Mouser also lists stock | Potential distributed assembly element only. A single part fails the voltage requirement. |
| Susumu RGV3216P-2704-B-T1 | 2.7 Mohm, 0.1%, 25 ppm/K, 0.25 W, 700 V maximum element voltage | DigiKey US category: 9,249; regional detail: 9,599 | Promising high-resistance candidate. At 650 V: 240.74 uA and 0.15648 W. Does not establish 0.01% accuracy. |

The RGV nominal 2.7 Mohm differs from the weight-8 target by -0.02393%, before
its +/-0.1% initial tolerance. At 700 V it dissipates 0.18148 W and reaches its
maximum element voltage, leaving no voltage headroom. Its thermal derating,
voltage coefficient and transient environment still require review. It is not
approved as an unmodified drop-in replacement.

TNPW's headline 0.52 W is its advanced operating mode. The current datasheet lists
0.27 W for general operation of 1206, with different permissible film temperature
and load-life drift. Survival at a rated wattage does not establish DAC accuracy.
At 25 ppm/K, only a 4 K temperature change corresponds to 100 ppm (0.01%) in
one resistor at the specified coefficient limit. Tracking and thermal gradients
therefore matter even after room-temperature resistance selection.

0.01% parts are also stocked: DigiKey lists Riedon 101-10KX8 at 458 units,
10 kohm, 0.25 W and +/-10 ppm/K. This example proves availability of the tolerance
grade only; it is not a qualified power-network candidate. Its 0.25 W rating
corresponds to only 50 V across 10 kohm before any separate voltage limit.

## Remaining procurement gates

1. Map all 34 target positions to exact component combinations and quantities,
   with an explicit decision on nominal scaling versus trimming/selection.
2. Establish the complete ratio-error budget: initial tolerance, measurement
   uncertainty, temperature tracking, voltage coefficient and aging. Do not
   replace bounded errors with assumed statistical averaging.
3. Verify individual electrical/thermal loading in each proposed assembly and
   model the added parasitic capacitance in the existing switched simulations.
4. Re-price that actual BOM and verify sufficient distributor stock for one
   channel plus selection/rework stock. No orders or supplier messages were sent.

This audit leaves circuit values and the schematic unchanged. The existing
`python sim/run_phase_a.py` regression was executed successfully; it is the
initial low-voltage bench and does not qualify these new resistor candidates.

## Sources

- [Mouser 2 W / 0.1% axial listings, including CPF2100K00BEB14](https://www.mouser.com/en/c/passive-components/resistors/film-resistors/?power+rating=2+W&termination+style=Axial&tolerance=0.1+%25)
- [Vishay CPF datasheet](https://www.vishay.com/docs/31021/cpf.pdf)
- [DigiKey TNPW1206100KBEEA](https://www.digikey.com/en/products/detail/vishay-dale/TNPW1206100KBEEA/1608081)
- [Vishay TNPW e3 datasheet, revision 10 April 2026](https://www.vishay.com/docs/28758/tnpw_e3.pdf)
- [DigiKey RGV3216P-2704-B-T1](https://www.digikey.com/en/products/detail/susumu/RGV3216P-2704-B-T1/13180863)
- [Susumu manufacturer catalog, RGV specifications](https://www.susumu.co.jp/dl/?filename=n_e_all.pdf&type=application%2Fpdf)
- [DigiKey 101-10KX8](https://www.digikey.com/en/products/detail/riedon-products-by-bourns/101-10KX8/4832934)
