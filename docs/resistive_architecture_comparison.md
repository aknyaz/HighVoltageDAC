# Parallel resistor architectures versus R–2R

## Outcome

At 650 V, 12 bits, 5 W useful output, and a 10 kohm reflected primary load,
the best sampled parallel resistor designs dissipate **25.31 W**, versus
**160.19 W** for the ordinary R–2R reference. Useful efficiency rises from
3.03% to 16.50% in the ideal model. At 10 W into a 5 kohm primary load, these
figures double to 50.62 W and 320.39 W of resistor heat respectively.

Binary and segmented parallel networks have identical ideal total heat. The
segmented network trades more switches for a smaller resistor ratio and more
distributed dissipation. These findings justify further study, but do not
demonstrate real 12-bit linearity, acceptable switching behavior, or an HV build.

## Precisely defined topologies

Both alternatives retain two complementary arms driving the transformer primary
directly. In each arm, all weighted branches meet at one output node. Each branch
consists of a resistor between that node and an SPDT switch selecting Vs or ground.
The branch is never intentionally disconnected in the ideal steady-state model.

Define N bits, K=2^N, code D, and an equivalent output resistance R per arm.
A branch of integer weight w has resistance K*R/w. A fixed resistor K*R connects
each output node to ground. This extra unit conductance ensures that the total
arm conductance is 1/R and exactly matches the original R–2R code normalization.

### Binary-weighted parallel network

For 12 bits, the switched weights are 1, 2, 4, ..., 2048. Each branch is controlled
by its corresponding code bit. The opposite arm receives 4095-D.
There are 12 switched branches plus one fixed termination per arm.

### Segmented parallel network: 4 thermometer bits + 8 binary bits

Split the 12-bit code as D=256*C+F, where C is 0–15 and F is 0–255.
The coarse section has 15 equal branches, each of weight 256. Exactly C of them
select Vs and the remainder select ground, using a fixed thermometer ordering.
The fine section has eight binary branches of weights 1, 2, ..., 128.
The opposite arm independently decodes 4095-D. This is not necessarily a
one-for-one inversion of the corresponding coarse branch control lines.

There are 23 switched branches plus the fixed unit termination per arm.
No buffer or isolated amplifier joins the two sections: they share the same
output node. For the 4-bit demonstrator, the analogous split is 2+2: three
coarse branches of weight 4 and two fine branches of weights 1 and 2.

## Why their ideal losses are identical

Both parallel networks have the same total conductance and, for a given code,
the same conductance connected to Vs: D/(K*R). Their two output node equations
are therefore identical. Each resistor's heat is summed independently in the
implementation; supply power is checked against heat plus total load power.

For a direct check, let s=(K-1)/K, x=(2D-(K-1))/K, and t=Zp/(Zp+2R), where
Zp is the reflected primary resistance. The paired source power per code is:

```text
P_supply[D] = (Vs^2/R) * (s - s^2/2 - t*x^2/2)
v_primary[D] = Vs*t*x
P_heat[D] = P_supply[D] - v_primary[D]^2/Zp
```

This depends on the code and aggregate conductances, not whether a coarse weight
is one binary branch or several thermometer branches. Segmentation is therefore
not an additional ideal efficiency improvement. Device losses can differ because
the switch count and switching activity differ; those losses are not modeled here.

## Equal-power comparison

The sweep reuses the original 600/650/700 V, 5/10/20 kohm, 5/10 W targets and
PCM sequences. For each amplitude it uses the same source resistance R needed
to obtain the requested **1 kHz fundamental** power. This makes loading, code
scale, and waveform utilization equal across architectures.

There are 2,695 feasible points per alternative, 5,390 total. The best sampled
points all use full command amplitude, so they have no command headroom.
The infeasible target combinations are unchanged because unloaded voltage and
output resistance match R–2R exactly. These are sampled optima, not a proof of
global optimality over all possible waveforms or circuit topologies.

At 650 V and 12 bits:

| Useful output | Primary load | R–2R heat | Binary parallel heat | Segmented parallel heat | Parallel useful efficiency |
|---|---:|---:|---:|---:|---:|
| 5 W | 5 kohm | 181.01 W | 31.71 W | 31.71 W | 13.62% |
| 5 W | 10 kohm | 160.19 W | 25.31 W | 25.31 W | 16.50% |
| 5 W | 20 kohm | 182.63 W | 25.59 W | 25.59 W | 16.35% |
| 10 W | 5 kohm | 320.39 W | 50.62 W | 50.62 W | 16.50% |
| 10 W | 10 kohm | 365.25 W | 51.18 W | 51.18 W | 16.35% |
| 10 W | 20 kohm | 2,974.97 W | 384.95 W | 384.95 W | 2.53% |

These are resistor losses only. The ideal transformer is represented by its
reflected resistance, just as in the preceding power study. Real transformer,
driver, switch, and supply losses remain outside the comparison.

## Component tradeoffs at 650 V / 5 W / 10 kohm

All three best sampled designs have R=5.2747 kohm per arm and the same waveform.

| Property | R–2R | Binary parallel | Segmented parallel 4+8 |
|---|---:|---:|---:|
| SPDT functions, both arms | 24 | 24 | 46 |
| Ideal SPST elements inside those functions | 48 | 48 | 92 |
| Resistor elements, both arms | 48 | 26 | 48 |
| Switched branch resistor range | 10.55 kohm (all 2R branches) | 10.55 kohm–21.61 Mohm | 84.40 kohm–21.61 Mohm |
| Switched resistor ratio | 1:1 | 2048:1 | 256:1 |
| Highest average dissipation in one resistor | 5.97 W | 4.99 W | 1.03 W |
| Total resistor heat at full command | 160.19 W | 25.31 W | 25.31 W |

R–2R also has 1R series resistors; its overall resistor-value ratio is 2:1.
For the parallel alternatives, the fixed termination is 21.61 Mohm per arm.
Counts refer to modeled elements, not a physical BOM: a high-voltage resistor
may need a series implementation, and SPDT functions require actual drive circuitry.

Segmentation raises the minimum switched resistance by splitting a large binary
conductance into equal coarse branches. It does **not** reduce the highest fine
resistance in this 4+8 version. The fine branches still need leakage, matching,
temperature/voltage dependence, and parasitic-capacitance assessment.

## Headroom and idle heat

Allowing 10% command reserve changes the best sampled parallel 650 V cases to:

| Useful output | Primary load | Command | R per arm | Resistor heat | Useful efficiency |
|---|---:|---:|---:|---:|---:|
| 5 W | 10 kohm | 0.900 | 4.2468 kohm | 33.86 W | 12.87% |
| 10 W | 5 kohm | 0.900 | 2.1234 kohm | 67.71 W | 12.87% |

Idle heat must not be inferred from full-scale sine heat. For the 5 W full-command
design, alternating the two middle codes produces about **40.05 W** of resistor
heat, greater than the 25.31 W under the full sine. In the 10%-reserve version,
the same idle sequence dissipates about 49.74 W. Near midpoint, substantial
conductance is tied to both rails while useful differential output is near zero.
This is a specified balanced idle sequence, not a claim about every possible
mute strategy. Arbitrarily using a constant off-center code would also introduce
primary DC and is not a substitute for a modeled mute/startup strategy.

## Verification performed

Run from the repository root:

```powershell
python calc/power_trade_study.py
python calc/compare_resistive.py
python sim/verify_resistive_comparison.py
```

- Checked all 16 ideal 4-bit codes and all 4096 ideal 12-bit codes for monotonicity,
  correct mapping, and binary/segmented output and heat equivalence.
- Verified both 4-bit architectures over all codes in structural SPICE.
- Ran 68 structural switched power tests: both alternatives for all 33 feasible
  best sampled cases, plus one 12-bit reserve case for each alternative.
- Every SPICE supply was 5 V. Resistance values were retained and power was
  rescaled by (target supply/5)^2. No HV circuit was built or energized.
- Maximum relative power disagreement was 3.78e-5, or **0.00378%**. The 4-bit
  voltage-mapping errors were below 1 nV.

The SPICE tests use the same idealized switch assumptions as the R–2R study:
1 ns control edges, Ron=1 microohm, Roff=1e12 ohm, and a 100 ns maximum step.
Acceptance limits are 0.2% for power comparison and 0.01% for power balance.
The finite-transition numerical discrepancy is not a measured real switching loss.

Artifacts:

- `results/resistive_comparison/summary.json` — selected cases, feasibility, and reserve results.
- `results/resistive_comparison/sweep.csv` — every feasible point and component metrics.
- `results/resistive_comparison/verification.json` — executed checks and errors.
- `plots/resistive_comparison/heat_comparison.png` — comparison across primary loads.
- `sim/generated/resistive_comparison/` — independent low-voltage SPICE decks.

## Next step

The parallel family deserves a low-bit wired KiCad demonstrator alongside the
existing R–2R reference. Binary parallel is simpler in switch count; segmentation
spreads dissipation and reduces the resistor ratio. Neither is yet selected as
the final architecture. Before committing to 12-bit hardware, compare mismatches,
leakage, timing/glitches, and switch capacitance, then restore the finite-inductance
transformer and assess startup/DC behavior. The current comparison establishes
ideal power behavior only; it does not establish audio quality or physical feasibility.
