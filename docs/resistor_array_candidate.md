# Complete resistor-array candidate: one stocked nominal value

Date: 21 November 2026. Scope: sourcing, circuit calculations and mechanical
envelope only. This is a candidate study; the baseline KiCad schematic is unchanged.

**22 November review:** [thermal/substrate/edge screen](resistor_array_preliminary.md)
found that the static voltage-sharing result does not establish fast-edge pulse
compliance. The nominal-value implementation remains valid, but its repetitive
pulse rating and metal-backed substrate are unqualified. This is not a release
for HV purchasing or assembly.

## Decision and procurement answer

All 34 resistor positions can be represented by series/parallel combinations of
one catalog part: **Panasonic ERA-8AEB1693V**, 169 kohm, +/-0.1%, 1206 thin film.
No custom resistance or nonexistent part number is required for this candidate.
The cost is a high component count: **3,052 resistors per mono channel**.

This is a deliberately simple single-value implementation, not a minimum-size
or minimum-count solution. It closes the nominal-value sourcing question by
accepting a common +0.1241847% scale change from the previous analytical targets.
It does not claim that unselected 0.1% parts guarantee the model's 0.01% error budget.

## Complete assembly table

Every resistor in the table is the same 169 kohm part. `S x P` means P independent
parallel strings, each containing S series resistors. Thus `R = 169000*S/P`.
The quantity counts both complementary arms of one mono channel.

| Weight | Previous target, kohm | Candidate, kohm | Connection | Assemblies | Resistors each | Total resistors |
|---|---:|---:|---|---:|---:|---:|
| 512 | 42.197597 | 42.25 | 6S x 24P | 14 | 144 | 2016 |
| 256 | 84.395194 | 84.5 | 6S x 12P | 2 | 72 | 144 |
| 128 | 168.790388 | 169 | 6S x 6P | 2 | 36 | 72 |
| 64 | 337.580776 | 338 | 6S x 3P | 2 | 18 | 36 |
| 32 | 675.161552 | 676 | 8S x 2P | 2 | 16 | 32 |
| 16 | 1350.323105 | 1352 | 8S x 1P | 2 | 8 | 16 |
| 8 | 2700.646209 | 2704 | 16S x 1P | 2 | 16 | 32 |
| 4 | 5401.292419 | 5408 | 32S x 1P | 2 | 32 | 64 |
| 2 | 10802.584838 | 10816 | 64S x 1P | 2 | 64 | 128 |
| 1 | 21605.169675 | 21632 | 128S x 1P | 4 | 128 | 512 |
| **Total** | | | | **34** | | **3052** |

The four weight-1 positions comprise two switched LSB branches and two grounded
terminations. A 169 kohm assembly is not a single chip: its multiple chips are
needed to distribute voltage and power.

For the coarse assembly, six resistors form a 1.014 Mohm string. Twenty-four such
strings in parallel give 42.25 kohm. See the explicitly wired
[coarse assembly diagram](../output/resistor_array/coarse_connection.svg).

## Actual ordering line

| Manufacturer part number | Distributor identifier | Fitted quantity | Quantity with 20% reserve |
|---|---|---:|---:|
| Panasonic ERA-8AEB1693V | DigiKey P169KBCCT-ND (cut tape); P169KBCTR-ND (reel) | 3052 | 3663 |

The [DigiKey part page](https://www.digikey.com/en/products/detail/panasonic-industry/ERA-8AEB1693V/3069615)
lists 7,386 pieces and USD 0.15558 each at 1,000+, or USD 699.25 for a 5,000-piece
reel. A more recent substitute listing shows 5,166 pieces; both observations
exceed 3,663. [Mouser's listing](https://www.mouser.co.uk/en/ProductDetail/Panasonic-Industry/ERA-8AEB1693V?qs=MNPzkKEzRtRTYbNc%2Fy2ZhA%3D%3D)
shows 8,268 pieces. These are retrieved catalog/index observations, not stock
reservations; page caches differ and some direct requests return HTTP 403.
Recheck the cart before purchase. No purchase was made.

At the quoted cut-tape tier: USD **474.83** fitted, or **569.89** with 20% reserve,
before delivery/taxes. Selection yield is unknown; 20% reserve is not a guarantee
that resistance matching will succeed. A complete reel costs more but gives
additional selection stock. PCB/assembly/thermal-control costs are separate.

## Electrical rating screen

The [Panasonic manufacturer datasheet](https://industrial.panasonic.com/cdbs/www-data/pdf/RDM0000/AOA0000C309.pdf)
specifies ERA8A at 0.25 W, maximum element voltage 150 V, and nominal body size
3.2 x 1.6 mm. Its power derating starts above 85 C in the retrieved revision.
The selected E/B suffix is 25 ppm/K and 0.1%. Use the exact part specification
when ordering; overload-test voltage is not the working-voltage rating.

The shortest string contains six parts:

| Screen | Per-chip voltage | Per-chip current | Per-chip dissipation |
|---|---:|---:|---:|
| Full 650 V across an assembly, equal nominal resistors | 108.333 V | 0.6410 mA | 69.444 mW |
| Full 700 V, worst initial +/-0.1% tolerance corners | <=116.862 V | <=0.6911 mA | <=80.728 mW |

The voltage, current and power maxima use their respective worst corners and
need not occur simultaneously. Longer strings have lower per-chip stress.
The 700 V screen therefore stays below both 150 V and 0.25 W at the stated
temperature-rating conditions. It excludes voltage overshoot, capacitive voltage
division at fast edges, leakage, open-component faults and PCB insulation.
It is a resistance-network rating screen, not an HV assembly qualification.

## Executed verification and nominal scaling

Run `python calc/resistor_array_design.py` to reproduce the tables, netlists,
results and envelope models. The calculation asserts the count of all 3,052
physical resistors and every binary weight ratio. New equivalent arm resistance:
5281.25 ohm versus 5274.699628 ohm previously.

The full 3,052-resistor structural ngspice deck was executed at 5 V over all
4096 codes with the 10 kohm resistive primary reference. It agrees with the
analytical transfer to 2.92e-11 LSB. Ideal nominal endpoint INL remains zero;
relative gain changes by -0.06371% and load power by -0.12738%. These figures
describe the matched nominal array, not random component tolerance or real-core
distortion. All ten equivalent resistances scale together; none is independently
rounded to a nearby catalog value.

Four additional structural AC simulations used 0, 0.02, 0.1 and 0.5 pF from every
internal series junction to ground. Near 20 kHz, the additional attenuation
relative to zero parasitics was 0, 0.00331, 0.01707 and 0.08062 dB respectively.
These are invented sensitivity cases, not extracted or measured capacitances.
Sources excite all A branches coherently at +0.5 AC and B branches at -0.5 AC;
the load is resistive. This is not a code-transition/glitch or THD validation.
Long fine-branch strings require switched-model checking before adoption.

`python sim/run_phase_a.py` also passed. This is the existing initial low-voltage
regression, not hardware certification of the candidate.

## Mechanical envelope and how to open it

- [Interactive offline 3D envelope](../output/resistor_array/resistor_array_3d.html):
  open in a browser, drag to rotate, scroll to zoom.
- [Top view](../output/resistor_array/array_top.png) and
  [perspective preview](../output/resistor_array/array_3d.png).
- [OBJ geometry](../output/resistor_array/resistor_array.obj), with its adjacent
  MTL material file. Units are millimetres; import at 1 mm per unit.

Two **250 x 220 mm** illustrative arm panels contain **1,526 resistor bodies each**.
Each arm has seven coarse assemblies (1,008 chips) and 518 fine/termination chips.
The body model is 3.2 x 1.6 x 0.6 mm on a 1.6 mm panel; the datasheet maximum
height can differ, and the distributor lists 0.7 mm maximum. Spacing is an
explicit visual assumption (6 x 3 mm body pitch), not an approved pad pitch or
creepage distance. Coarse groups are visual blocks, not a placement/routing plan.

This is approximately two 25 x 22 cm panels for resistors alone, before switches,
drivers, transformer, connections, shielding or thermal hardware. It is not a
minimum size and not a manufacturing PCB. No Gerbers or copper layout were made.

## What this resolves, and what remains

The nominal-value availability problem now has a complete concrete solution.
All 34 positions use a catalog part with sufficient observed stock. There is no
need to buy 21.605170 Mohm as a single custom resistor. The cost and body count
are explicit, so a smaller multi-value implementation can be compared against it.

The 0.01% assembly-error scenario is still a separate acceptance target. Initial
0.1% chip tolerance does not become a guaranteed 0.01% assembly tolerance merely
through parallel/series averaging. Matching or calibration must be developed and
verified. User-planned thermal stabilization is not designed here. A later study
must retain the same clear procurement/rating accounting if it reduces part count.
