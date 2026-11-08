# Equal-power R–2R study — 2026-11-08

## Finding

High reflected primary impedance matters, but increasing it indefinitely does not
reduce heat. In this ordinary complementary voltage-mode R–2R topology, internal
currents dominate the losses. The best sampled 12-bit cases around 650 V require
about 160 W of ladder heat for 5 W useful output, or 320 W for 10 W useful output.
These results include exact ideal ladder loading and every resistor, but exclude
real device, gate-driver, transformer, and power-supply losses.

This is a finding about the modeled R–2R architecture, not a general limit on all
resistive power DACs. It does not select or validate physical HV hardware.

## Scope and method

- Supply targets: 600, 650, 700 V; reflected primary loads: 5, 10, 20 kohm.
- Useful sine power: 5 or 10 W into an ideal 8 ohm secondary load.
- Resolution: 4 bits for continuity with the verified bench; 12 bits for comparison.
- PCM: 1 kHz, 192 kS/s, half-sample phase offset, complementary half-cycles.
- Command amplitude grid: 0.05 to 1.00 in 0.005 steps; no dither or noise shaping.
- For each waveform, solve ladder R for exactly the requested fundamental power.
  Reject nonpositive R. Each arm has output resistance R; the bridge has 2R.
- Solve all internal node voltages and sum every resistor's squared voltage divided
  by its resistance. Independently compute current drawn from the supply.
- An ideal transformer is represented by its reflected resistance in this study.
  Finite Lm, winding loss, leakage, bandwidth, and core saturation are not modeled here.

There are 36 combinations of supply, load, power, and resolution. Of these,
33 have feasible points on the amplitude grid, totaling 2,695 feasible points.
The reported best points minimize ladder heat **among the sampled amplitudes**;
this is not a proof of a continuous global optimum. In this sweep, all best points
occur at command amplitude 1.0 and therefore have no command headroom.

## Equations and power accounting

Let N be the number of bits, D the unsigned code, Vs the supply, Zp the reflected
primary resistance, and R the ladder resistance. Each bit branch and termination
uses 2R. The complementary arm receives (2^N-1-D).

The normalized unloaded bridge voltage is:

```text
x[D] = (2D - (2^N - 1)) / 2^N
v_primary[D] = Vs * x[D] * Zp / (Zp + 2R)
```

For M=192 equally spaced samples in one period, the exact fundamental amplitude
of the zero-order-held sequence is:

```text
g1 = (2/M) * abs(DFT(x)[1]) * sinc(1/M)
required_primary_peak = sqrt(2 * P_useful * Zp)
R = (Zp/2) * (Vs*g1 / required_primary_peak - 1)
```

Here sinc(u)=sin(pi*u)/(pi*u). This distinguishes useful fundamental power from
harmonic and sampling-image power. All of the latter is also included in the
resistive load's total RMS power and the supply balance.

For this complementary ladder, the direct resistor sum also agrees with:

```text
P_heat = P_internal_no_load + P_load_total * (2R/Zp)
P_supply = P_heat + P_load_total
```

The first term is the code-dependent internal dissipation of both disconnected
ladders driven with the same bit sequence. It does not disappear when the output
current is small. The second term is the familiar equivalent series-resistance loss.
Both identities are checked numerically for every sweep point.

## Results at 650 V

All rows below use full command amplitude and ideal devices. R is the value of
each series ladder resistor; bit resistors and the termination are 2R.

| Bits | Useful output | Primary load | R | Ladder heat | Useful efficiency |
|---|---:|---:|---:|---:|---:|
| 4 | 5 W | 5 kohm | 4.359 kohm | 77.27 W | 6.08% |
| 4 | 5 W | 10 kohm | 4.700 kohm | 68.27 W | 6.82% |
| 4 | 5 W | 20 kohm | 3.718 kohm | 82.21 W | 5.73% |
| 12 | 5 W | 5 kohm | 4.765 kohm | 181.01 W | 2.69% |
| 12 | 5 W | 10 kohm | 5.275 kohm | 160.19 W | 3.03% |
| 12 | 5 W | 20 kohm | 4.531 kohm | 182.63 W | 2.66% |
| 12 | 10 W | 5 kohm | 2.637 kohm | 320.39 W | 3.03% |
| 12 | 10 W | 10 kohm | 2.265 kohm | 365.25 W | 2.66% |
| 12 | 10 W | 20 kohm | 0.275 kohm | 2,974.97 W | 0.34% |

At 650 V, the 4-bit 20 kohm / 10 W case is infeasible for the specified rounded
sine waveform. At 600 V, the 20 kohm / 10 W case is infeasible for both resolutions.
The 12-bit 650 V / 20 kohm / 10 W case is mathematically feasible only with a very
small R and extreme dissipation. It also has no 10% command-reserve solution.
The same reserve restriction holds for the 12-bit 700 V / 20 kohm / 10 W case.

Increasing primary impedance lowers winding current at the same useful power but
raises the required primary voltage. Once the supply headroom is nearly exhausted,
R must become small to avoid excessive voltage division. Internal currents then rise.

## Why Thevenin loss alone was misleading

For the 12-bit, 650 V, 10 kohm, 5 W point:

| Power term | Value |
|---|---:|
| Useful 1 kHz power | 5.000 W |
| Other load power, including images | 0.000447 W |
| Equivalent source series heat | 5.275 W |
| Internal ladder heat at no load | 154.918 W |
| Total supply power | 165.194 W |

Thus a comparison based solely on 2R/Zp would miss most of the heat.
Additional low-significance bits still switch full supply voltage across internal
resistive branches, even though their contributions to output voltage are small.
The hottest individual resistor at this operating point dissipates about 5.97 W
on average. This is a model result, not a component-rating recommendation.

## Useful comparison ranges, not final component values

Across the tested 600–700 V supplies, the best sampled primary-load choice is
10 kohm for 5 W and 5 kohm for 10 W. This favors further transformer research in
the 5–10 kohm range rather than assuming 20 kohm must be better.

For the 12-bit full-command cases:

| Useful power | Primary load | R over 600–700 V | Ladder heat over those supplies |
|---|---:|---:|---:|
| 5 W | 10 kohm | 4.484–6.065 kohm | 159.75–162.32 W |
| 10 W | 5 kohm | 2.242–3.033 kohm | 319.50–324.64 W |

At 650 V, the corresponding turns ratios are sqrt(10000/8)=35.355 for 5 W and
sqrt(5000/8)=25 for 10 W. Primary RMS currents are about 22.36 mA and 44.72 mA;
secondary RMS currents are about 0.791 A and 1.118 A respectively.

Full command leaves no margin for gain variation or a higher signal. Requiring
at least 10% command reserve increases the best sampled 650 V ladder heat to:

- 214.00 W at 5 W / 10 kohm, R=4.196 kohm, command amplitude 0.895.
- 428.00 W at 10 W / 5 kohm, R=2.098 kohm, command amplitude 0.895.

The slight preference for 0.895 over 0.900 follows the discrete bit patterns on
this grid; it is not a robust real-component optimum. Headroom columns in the
CSV include command reserve and maximum fundamental output at the same R.
The code-endpoint-minus-fundamental column is not a general clipping metric:
for distorted 4-bit waveforms the fundamental amplitude can exceed the endpoint.

Alternating the two midpoint codes in the 12-bit 650 V / 5 W full-command design
still dissipates about 66.73 W in the ladders. That is a specified balanced idle
sequence, not a claim about every possible idle or mute strategy.

## Verification and reproducibility

```powershell
python calc/power_trade_study.py
python sim/verify_power_study.py
python sim/run_phase_a.py
```

The verifier checks a separate full 2N-node conductance matrix against the reduced
calculation for all 4-bit codes and selected/random 12-bit codes. Maximum node-voltage
disagreement was 2.27e-13 V. It also checks both scaling statements:

- At fixed resistances and waveform, changing 5 V to 650 V multiplies every power by 130^2.
- Scaling all resistances by 130^2 as well preserves those powers and efficiency.

All 33 feasible best sampled cases, plus one command-reserve case, were run through
ngspice 46 using structural ladders and complementary idealized switches.
Every SPICE supply was **5 V**; R and reflected load were unchanged, and powers
were rescaled by (Vs/5)^2. Logic levels were not scaled. The largest relative
power discrepancy was 4.52e-6, or about 0.000452%.

SPICE uses 1 ns control edges, Ron=1 microohm, Roff=1e12 ohm, and a 100 ns maximum
time step over one 1 ms period. The analytical sweep has instantaneous switching.
Acceptance thresholds are 0.2% for analytical/SPICE power comparison and 0.01%
for SPICE power balance, allowing finite-transition and numerical-integration effects.
These checks do not characterize real switching loss or glitches at HV.
The original Phase A regression also passed.

Files:

- `results/power_study/summary.json`: feasible/infeasible cases and reserve variants.
- `results/power_study/sweep.csv`: every feasible grid point, including currents and resistor heat.
- `results/power_study/best_cases.csv`: compact table of best sampled cases.
- `results/power_study/verification.json`: independent calculation and SPICE errors.
- `sim/generated/power_study/`: standalone low-voltage SPICE decks.
- `plots/power_study/`: equal-power heat, resistance tradeoff, and power allocation charts.

## Next decision

Retain the current R–2R model as a validated reference. Before choosing real switches,
compare a binary-weighted parallel resistor DAC and a precisely defined segmented
resistive topology at equal useful power, with every internal current included.
The requirement for direct transformer drive remains unchanged. Lower heat from
those alternatives is a question to test, not an established result.
