# Nonlinear SiC charge and driver budget

Date: 2026-11-09. This is an architecture-level estimate, not a hardware rating.

## Outcome

Using an approximate voltage-dependent capacitance curve raises the segmented
650 V, full-range 1 kHz sine capacitive-loss scenario from 12.13 W to **20.12 W**.
The basic one-isolated-driver-per-transistor reference adds approximately **8.01 W**
at its bias outputs and logic supplies, before bias-converter losses. These are
model estimates with different uncertainty sources, not measured performance.

The prior ideal resistor heat was about 25.3 W for 5 W output. Adding these
illustrative contributions gives about 53.4 W of losses before transformer and
power-supply losses. This is not a validated total or an efficiency specification.
The chosen power devices and driver arrangement need optimization before a BOM.

## Sources and model status

The [Wolfspeed model portal](https://www.wolfspeed.com/tools-and-support/power/ltspice-and-plecs-models/)
was checked, including its public page data. A downloadable C3M0350120D model
was not retrieved in this session. This does not establish that none exists.
No vendor transistor model has been imported or validated.

Instead, `calc/sic_charge.py` contains rounded visual samples of typical Coss
from figures 17/18 of the [C3M0350120D revision 04 datasheet](https://assets.wolfspeed.com/uploads/2024/01/Wolfspeed_C3M0350120D_data_sheet.pdf),
page 5. Capacitance is interpolated linearly; charge and energy are integrated
analytically per segment. Samples and provenance are saved in the JSON results.
Figure 16 is an independent visual cross-check: computed stored energy at 1000 V
is 10.777 uJ, versus the 10.6 uJ reference, a 1.67% difference. Low-voltage sampling
is visually approximate; this agreement does not establish charge accuracy.

The source gives a typical curve, not tolerance limits. Scaling every C value
by 0.75 and 1.25 is an assumed sensitivity exercise, not a guaranteed bound.
The segmented full-scale estimate becomes 15.09–25.15 W under that exercise.

## Charge versus energy

For nonlinear capacitance:

- `Q(V) = integral(C(v) dv)`.
- `E(V) = integral(v*C(v) dv)` is stored energy in one device.
- For two identical half-bridge devices, a fully hard-switched, monotonic
  rail-to-rail node transition dissipates `V*Q(V)` when no energy is recovered.

The last identity follows by integrating
`(V-x) * [C(x)+C(V-x)] dx` from zero to V: one term is `V*Q-E`, the other is E.
For nonlinear C, simply doubling E is generally incorrect. The earlier constant-C
formula is recovered because Q=C*V.

| Rail | Qoss | One-device stored Eoss | Half-bridge transition loss |
|---|---:|---:|---:|
| 600 V | 20.56 nC | 4.38 uJ | 12.33 uJ |
| 650 V | 21.56 nC | 5.00 uJ | 14.01 uJ |
| 700 V | 22.56 nC | 5.68 uJ | 15.79 uJ |

At 650 V, Q/V is about 33.17 pF. This is a charge-equivalent average, not the
point capacitance, energy-equivalent capacitance, or a physical constant.
Device Coss dissipation mechanisms, gate overlap, reverse recovery, temperature,
and current-driven partial commutation remain absent.

## SPICE verification

```powershell
python calc/sic_charge.py
python sim/verify_sic_charge.py
```

Eight independent 5 V decks verify the charge-work calculation at equivalent
600, 650, 700 and 1000 V, each with maximum steps of 0.02 and 0.01 ns.
With scale S=Vrail/5, the capacitor law is `Qscaled(v)=Q(S*v)/S`; thus capacitance
follows the physical voltage axis and energy scales by S squared. This is an
explicit nonlinear normalization, not applying the real device at 5 V.

The node is driven through a prescribed 100 ns monotonic ramp. Behavioral currents
differentiate the charge on both capacitors. The integral of `(5-x)*I_node` is the
work dissipated in a hypothetical high-side conducting element imposing that ramp.
This fixture tests charge/energy consistency; it does not predict a transistor's
switching waveform or its gate drive. All eight runs pass. Fine-step work differs
from the analytical result by at most 0.138%; step-halving changes it by at most
0.137%. Source derivatives need fine timesteps; these checks do not validate the
visual curve or substitute for a complete MOSFET transient model.

The earlier DAC transient decks retain their linear surrogates. This stage adds
a separately verified nonlinear charge fixture, not a silent replacement of all
previous simulations.

## Signal dependence

One periodic 192-sample sine is rounded to 12 bits. Both arms and wraparound are
counted. Capacitive power is the transition rate times V*Q. No switching is assumed
for a held midpoint code; this differs from alternating the two midpoint codes.

| Architecture | Amplitude / full range | Node transitions per ms | Capacitive loss at 650 V |
|---|---:|---:|---:|
| Binary | 100% | 1480 | 20.74 W |
| Segmented | 100% | 1436 | 20.12 W |
| Segmented | 50% | 1292 | 18.10 W |
| Segmented | 10% | 1012 | 14.18 W |
| Either | Held code | 0 | 0 W |

These examples show why switching loss does not scale with audio output power
as a simple square law. Frequency, dither and other PCM sequences change counts.

## Driver reference and held states

The [TI UCC21750 datasheet, revision C](https://www.ti.com/lit/ds/symlink/ucc21750.pdf)
provides an isolated single-channel reference. Its typical static input currents
are 3/2 mA for output high/low; output-side currents are 4/3.7 mA. Maximum
propagation delay is 130 ns and specified maximum part/pulse skew is 30 ns.
Those numbers motivate a budget, not a selected driver circuit. Its integrated
protection is substantial for our small branch currents.

Assume one driver per FET, 3.3 V input bias, and +15/-4 V output bias (19 V span).
Using those typical currents at the assumed rails is an extrapolated estimate,
not a guaranteed operating-point specification. Each settled half bridge has one
high and one low driver. Bias power per half bridge is:

`3.3*(3+2) mA + 19*(4+3.7) mA = 0.1628 W`.

Using 19 nC as a gate-charge scenario over that 19 V swing gives one gate-charge
cycle per branch-node transition. The actual charge must be revisited at our
voltage and milliampere-scale current. Do not multiply this term by two: each node
transition turns one device on and the other off.

| Reference budget | Binary | Segmented |
|---|---:|---:|
| Drivers / transistors | 48 | 92 |
| Floating upper-device source domains | 24 | 46 |
| Typical quiescent bias estimate | 3.91 W | 7.49 W |
| Full-sine gate-charge estimate | 0.53 W | 0.52 W |
| Sum at bias outputs and logic supplies | 4.44 W | 8.01 W |

The domain count is not a claim that 46 individual DC/DC modules are necessary;
it identifies moving source references that cannot simply share one ground-
referenced gate supply. A common low-side supply is possible in principle.
Continuous isolated bias can support indefinitely held high codes, whereas a
bootstrap-only arrangement cannot be assumed to do so without refresh analysis.
Power-up/UVLO states must keep both devices off until bias and control are valid.
Driver delays and device turn-off variation must be included in the dead-time
budget: a nominal 20 ns command gap is not a guaranteed non-overlap interval.

## Decision and next step

Retain segmentation for its static and carry-glitch advantages, but do not select
this 92-device/92-driver implementation as final. Search for smaller-charge
devices and a lower-quiescent driver architecture, then compare at equal voltage
margin and accuracy. Also test whether a different coarse/fine split reduces
device count and total loss while retaining acceptable linearity. Transformer
and audio performance still require a separate dynamic validation.

Results: `results/sic_charge/summary.json`, `verification.json` and `ngspice.log`.
Decks: `sim/generated/sic_charge/`. Plot: `plots/sic_charge/charge_model.png`.
