# Architecture review — initial simulation

## Working baseline

Two voltage-mode 4-bit R–2R ladders, R=1000 ohm, 2R=2000 ohm, Vref=5 V.
The least-significant node has a 2R termination to ground; the output is the MSB node.
Each bit connects to reference or ground through complementary idealized switches.
Complementary codes are D and 15-D. Each arm has Rout=R, so the differential
Thevenin resistance is 2R. Unloaded differential voltage is Vref*(2D-15)/16.
With a 2000 ohm differential load the expected voltage is half this value.

The transformer bench uses Lp=10 H, Ls=0.04 H, K=1 and an 8 ohm secondary load.
The turns ratio is sqrt(Lp/Ls)=sqrt(250), reflecting 2000 ohm. This is a
perfectly coupled linear transformer with **finite magnetizing inductance**, not an
ideal transformer at every frequency. These values describe no selected vendor part.

## Alternatives

| Architecture | Advantage | Main unresolved cost |
|---|---|---|
| Voltage R–2R | Two resistor values, predictable nominal Rout | Internal code-dependent heat; major-carry glitches; ratio accuracy |
| Thermometer/segmented | Fewer simultaneous switching changes at segment boundaries | More switches, decoder and matched elements; exact losses depend on chosen topology |
| Weighted current summation | Explicit current contributions | Current-source compliance and matching; active regulation may conflict with intended resistive topology |

R–2R is a baseline for measurement, not a final architecture decision.
Thevenin equivalent series loss is NOT the total heat of the original DAC:
internal branches draw current even without output power. Sum every resistor's
(Va-Vb)^2/R and independently check supply power against heat plus load power.

## Primary DC and startup

Complementary drive cancels common-mode voltage but does not force zero differential
DC. An even number of complementary codes has no exact zero differential code:
for four bits, codes 7 and 8 straddle zero. Symmetric time sequences can average to
zero, whereas a fixed code or biased PCM drives magnetizing current.
The initial operating point also stores magnetic energy; allow settling and measure
both winding voltage and current. Zero final mean voltage alone does not prove absence
of bias under mismatch or during startup.

Possible mitigations: explicit digital DC control, balanced idle sequence, a primary
series capacitor, or a controlled startup/mute strategy. Capacitor size, resonance,
startup and failure behavior require separate models. None is yet selected.
Gapped SE transformers tolerate specified DC but tend to trade magnetizing inductance
for bias tolerance; ungapped families merit comparison for nominal zero-DC operation.

## What does not establish feasibility

- Directly applying open-circuit DAC voltage to transformer power equations ignores loading.
- Scaling this 5 V ideal-switch model to HV does not establish switch ratings, isolation or thermal viability.
- A linear K=1 transformer cannot predict core coloration, saturation or parasitic resonance.
- Neither 192 kS/s nor transformer coupling guarantees sufficient reconstruction filtering.
- Four-bit THD is a quantization demonstration, not a prediction for the eventual amplifier.
- No real transformer or switch is selected and no 5–10 W design is validated.

Shared simulator API reference: https://ngspice.sourceforge.io/shared.html
