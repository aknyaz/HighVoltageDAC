# Wired 3+9 KiCad design review

Open `kicad/segmented/hv_rdac_segmented.kicad_pro`, then the schematic.
The root sheet shows all 32 branches, their shared power rails and weighted output
connections. Open a branch sheet to inspect its actual transistor/driver wiring.
The 34-page PDF is `plots/segmented_review/schematic.pdf`; its hierarchy links
allow navigation. Page 2 is the first complete branch example; page 34 is the HDL controller interface.

## Implemented scope

- 32 explicit half bridges, 64 candidate SiC transistors and 64 isolated drivers.
- Nine binary branches plus seven thermometer branches per arm.
- All 16 driver pins represented with datasheet pin numbers; APWM intentionally NC.
- Separate OUTH/OUTL gate resistors, direct clamp-to-gate wire, gate-source bleed.
- Upper COM connected to the switching node, lower COM connected to PGND.
- Local positive/negative bias bypass capacitors, input bypass and explicit
  ideal bias interfaces and a tested HDL command sequencer.
- 32 weighted resistor positions plus two grounded unit-weight terminations.
- Transformer placeholder with 10 kohm:8 ohm impedance target and output interface.

The weighted resistor is attached to the midpoint of its two FETs and then to the
arm output. A coarse branch has weight 512; nine fine branches have weights 1–256.
Resistor values are displayed in k/M notation, using the established normalized
Rout. They are target assembly values, not invented purchasable resistor MPNs.

## Candidate part numbers

| Function | Quantity | Candidate MPN | Qualification still required |
|---|---:|---|---|
| SiC transistor | 64 | C3M0350120D | Nonlinear device/thermal/drive validation |
| Isolated driver | 64 | UCC21750DWR | Timing, bias consumption, protection implementation |
| Gate series resistor | 128 | RC0603FR-0710RL | Pulse loading and final gate resistance |
| Gate-source bleed | 64 | RC0603FR-0710KL | Final resistance and bias budget |
| Output-side bypass | 128 | GRM32ER71E226KE15L | DC-bias capacitance and transient current |
| Input bypass | 64 | TBD, 2.2 uF target | Package, rating and effective capacitance |
| Precision weighted/termination assembly | 34 | TBD | Ratio accuracy, voltage coefficient, power and voltage distribution |
| Transformer | 1 | TBD | Actual transfer function, DC behavior and insulation |

MPN, selection status and candidate footprints are stored as symbol properties.
`kicad/segmented/bom.csv` lists every reference, sheet, MPN and status. The drawing
contains 618 symbols including ideal interfaces; that is not a 618-part purchasing
BOM. No PCB is generated. Footprints are references, not a completed layout review.

Sources: [Wolfspeed transistor datasheet](https://assets.wolfspeed.com/uploads/2024/01/Wolfspeed_C3M0350120D_data_sheet.pdf),
[TI driver datasheet, pin functions](https://www.ti.com/lit/ds/symlink/ucc21750.pdf),
[Yageo 10 ohm specification](https://www.yageogroup.com/component-documentation/download/specsheet/RC0603FR-0710RL),
[Yageo 10 kohm specification](https://www.yageogroup.com/component-documentation/download/specsheet/RC0603FR-0710KL),
[Murata capacitor reference](https://ds.murata.com/simsurfing/mlcc.html?oripartnumbers=%5B%22GRM32ER71E226KE15L%22%5D&partnumbers=%5B%22GRM32ER71E226KE15%22%5D).
The capacitor is a nominal 22 uF/25 V candidate; effective capacitance at bias has
not been established. Gate-resistor pulse suitability is not established by its
average-power rating. These are candidate selections, not approval for assembly.

## Explicit open interfaces

CONTROL is now a single logical HDL module on sheet 34, connected to every
high/low command, common enable, RDY and FLT line. The sequencer implements
complementary decoding, 200 ns nominal non-overlap and latched fault handling.
See [implementation and tests](controller_design.md). Its symbol uses logical
port names; physical FPGA pins, power banks, clock and configuration circuits
are still unfinished. VCC3V3/DGND come from a test supply interface.

BIAS blocks stand for ideal +15/-4 V rails relative to their local COM. No isolated
converter MPN, transformer winding arrangement or bias startup circuit is selected.
The repeated lower-side bias blocks are logical interfaces and may eventually
share a supply; they do not mandate 64 physical converters.

AIN and DESAT are tied to COM in this review bench per the unused-pin provision.
That disables desaturation protection. Digital startup and fault handling are implemented in HDL; physical protection
and the complete hardware shutdown chain are **not implemented**. The sheet labels make this visible.
The drawing uses a 5 V bench input; it is not a released 650 V construction design.

The new 10 kohm gate-source bleeds add about 0.771 W across 32 settled half bridges
at +15/-4 V: 32*(15^2+4^2)/10000. That contribution was absent from the earlier
ideal driver budget. Future budgeting must include it or revise the bleed value.

## Validation and simulation status

```powershell
python kicad/generate_segmented.py
python kicad/verify_segmented.py
```

KiCad 10.0.1 exports the full 34-sheet hierarchy. The verifier checks its actual
XML netlist against the intended electrical partition: 2301 connected pins,
447 nets, zero unintended shorts and zero split nets. It verifies the shared
rails through the sheet ports, not merely the labels in the generator.

ERC reports zero violations. Custom review symbols use passive electrical pin
types; consequently this result is a connectivity/syntax check, not a claim of
validated power drive, voltage limits or isolation. Representative overview,
branch and controller pages are visually reviewed; all repeated sheets
are generated from the same branch template.

This is an editable **design-review schematic**, not a complete executable vendor-
model SPICE circuit. Existing standalone 5 V simulation decks remain the verified
numerical reference. Do not assume KiCad's Run Simulation command will reproduce
the earlier analyses from these candidate component symbols.

Next work stays on the fixed 3+9 baseline: review this wiring, then implement the
physical FPGA/bias interfaces and documented transformer model. Part numbers left TBD
are real unfinished selections, not hidden ideal components presented as hardware.
