# Output transformer selection

Research date: 2026-11-15. Status: working candidate selected for modeling;
not a purchase release or a qualified hardware design.

## Decision

Use **Lundahl LL1679/PP, standard silicon-iron core, secondary alternative B for
8 ohm** as the primary candidate. Keep **LL1620/PP, alternative B** as the
higher-inductance fallback. Retain the 3+9 network and 200 ns command setting.
The existing switched transient benches remain historical references; this
selection adds separate candidate models and does not silently replace them.

Our intended differential drive has nominally zero DC across the full primary.
That favors a PP gap for this screen. The topology does not require a tube
output stage to use a PP transformer. DC imbalance and shutdown behavior still
need validation; a winding thermal-current limit is not an allowable unbalanced
magnetizing-current specification. This report is not a primary-pin hookup guide.

## Manufacturer data used

| Item | LL1679/PP, B | LL1620/PP, B |
|---|---:|---:|
| Catalog primary load / 8 ohm secondary | 9.7 kohm | 11.5 kohm |
| Primary inductance | 150 H | 300 H |
| Primary DCR | 160 ohm | 308 ohm |
| Primary leakage | 8 mH | 11 mH |
| Turns ratio used in model | 69:2 | 76.8:2 |
| Secondary DCR, B | 0.2 ohm | 0.2 ohm |

Sources: [LL1679 datasheet, pages 1-3](https://www.lundahltransformers.com/wp-content/uploads/datasheets/1679.pdf)
and [LL1620 family datasheet, pages 2-4](https://www.lundahltransformers.com/wp-content/uploads/datasheets/1620_3_7_9202.pdf).
The connection tables were visually checked. The requested version is PP;
SE versions are not interchangeable for inductance. LL1679/70mA has only 40 H.
The published LL1679 bandwidth uses a different source/load/configuration than
ours, so it is not adopted as our circuit response.

The catalog impedance is a rounded application label, not a DC resistance and
not an exact substitute for turns ratio. The ratios above reflect 9522 and
11796.48 ohm respectively from an ideal 8 ohm load, before winding losses.
Catalog labels and the detailed winding numbers do not coincide exactly;
confirm the intended configuration and loaded impedance with the manufacturer.
The models use winding data rather than forcing a ratio from the catalog label
and then adding copper losses a second time.

Hammond 1609A was screened as the nominal 10 kohm alternative. Its datasheet
lists 13.5 H measured at 1 kHz / 1 V open circuit, which does not provide the
low-frequency margin sought here; it is not selected. Those test conditions
also do not establish its inductance at 20 Hz and larger signal.
[Hammond 1609A source](https://www.hammfg.com/files/parts/pdf/1609A.pdf).
Hammond 1650E was not advanced because its published primary-inductance field
contains an ambiguous value; do not resolve a datasheet typo by guessing.
[Hammond 1650E source](https://www.hammfg.com/files/parts/pdf/1650E.pdf).

## Executed candidate-model screening

```powershell
python sim/select_transformer.py
```

Twenty-four ngspice AC sweeps run at 1 V small signal with the fixed 10549.4 ohm
DAC differential source resistance. Each is checked against an independent
complex-impedance calculation. Maximum relative discrepancy is below 2e-11.
The report is `results/transformer_selection/summary.json`; standalone decks
are in `sim/generated/transformer_selection/`.

The model is our equivalent circuit, not a vendor SPICE model. Coupled-inductor
parameters use Ls=Lp/n^2 and k=sqrt(1-Lleak/Lp), interpreting published leakage
as primary short-circuit inductance for this approximation. It cannot represent
all distributed winding resonances. No nonlinear core or winding electrostatic
model was supplied in the reviewed sheets.

Unknowns are explicitly swept: lumped primary capacitance 100/500/1000 pF,
core-loss shunt resistance 100 kohm / 1 Gohm (near-lossless comparison), and
primary inductance at nominal / half nominal. These are sensitivity scenarios,
not measured values, statistical tolerances or guaranteed bounds. Secondary
inductance changes with primary inductance to preserve turns ratio; leakage
is kept fixed. Ideal 192 kS/s hold attenuation is applied analytically.

At nominal L, assumed 100 pF and 100 kohm core loss:

| Calculated quantity | LL1679/PP B | LL1620/PP B |
|---|---:|---:|
| 20 Hz relative to 1 kHz | -0.279 dB | -0.088 dB |
| 20 kHz relative to 1 kHz | -0.156 dB | -0.163 dB |
| Full-scale 650 V linear projection at 1 kHz | 4.34 W | 4.23 W |
| Full-scale 700 V linear projection at 1 kHz | 5.04 W | 4.91 W |

With the near-lossless core scenario, the LL1679 projection becomes 4.80 W at
650 V and 5.56 W at 700 V. These are mathematical scaling results, not HV
simulations. They exclude nonlinear core/device behavior and cannot establish
power ratings. Under the 100 kohm scenario, 5 W at 20 Hz would require about
720 V for LL1679; therefore 5 W across the whole band within 600-700 V is not
yet demonstrated. The 10 W stretch target is not supported by the present
source resistance and voltage range. Do not interpret transformer power
capacity as amplifier output power.

Across the sensitivity sweep, LL1679 reaches -1.12 dB at 20 Hz with half nominal
L and about -1.45 dB at 20 kHz with the largest assumed capacitance. LL1620
retains more LF margin (-0.38 dB worst case), but its largest-capacitance case
reaches about -1.76 dB at 20 kHz. None of these is a guaranteed production limit.

LL1679 is the working choice because its ratio is closest to our original
10 kohm load, with lower winding resistance and leakage. LL1620 is the fallback
if measured low-frequency inductance margin is inadequate. This is a bounded
choice between two candidates, not another open-ended architecture search.

## Sourcing snapshot

[Erhard Audio's output-transformer catalog](https://www.erhard-audio.com/OutputTransformers.html)
lists LL1679 at USD 299 and LL1620 at USD 298; the page states that output
transformers are built to order. Treat these as catalog price indications,
not a confirmed quotation for the exact PP variant, landed cost or stock status.
For one mono channel, plan for one transformer; stereo requires two.

[Audio.parts](https://audio.parts/product/ll1679-output-transformer/) lists a
variant-dependent EUR 269-470 range and approximately four weeks to dispatch.
Exact PP/standard-core price and delivery must be confirmed. No purchase or
supplier message was sent.

## What must be established next

Obtain the LL1679/PP inductance versus frequency, signal and residual DC;
open/short-circuit impedance data, capacitance/resonance information and core
loss. Confirm acceptable 20 Hz voltage/current and operation from our 10.55 kohm
source, not just a low-impedance tube test circuit. Evaluate startup/shutdown
with the full primary, nominal zero DC and fault imbalance.

Use those data to replace assumed capacitance/core loss, then rerun the switched
bench, power budget and shutdown cases. Keep the current KiCad transformer
interface marked incomplete until its physical wiring and protection have been
reviewed. A draft technical inquiry is supplied separately and has not been sent.
