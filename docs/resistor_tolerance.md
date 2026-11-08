# 12-bit binary parallel DAC: resistor tolerance study

## Findings

The binary parallel DAC requires tight resistor ratios for monotonic 12-bit operation.
Independent uniform errors bounded by +/-0.1% produced nonmonotonic transfer curves
in 16.28% of the sampled networks. At +/-0.01%, all 5,000 independent samples were
monotonic, and the 95th percentile of maximum endpoint INL was 0.101 LSB.

For this ideal circuit, a separate worst-case argument guarantees strictly positive
code steps if every relevant resistance error is bounded by **less than +/-0.02442%**.
This is a static mathematical result under the assumptions below, not a hardware
guarantee based solely on a resistor's initial tolerance marking.

## Circuit and assumptions

- 12-bit binary parallel branches, two complementary arms, plus one grounded unit
  termination per arm: 26 resistor elements total.
- R=5274.6996277 ohm equivalent resistance per nominal arm; reflected load 10 kohm.
  These are the earlier 650 V / 5 W full-command comparison values.
- The analysis and all SPICE sweeps use a 5 V reference. INL/DNL in LSB and
  monotonicity are independent of supply scaling for this purely resistive model.
- Each resistance is nominal*(1+error). No switch resistance mismatch, leakage,
  noise, voltage coefficient, self-heating, temperature drift, or parasitic capacitance.
- The load is the ideal transformer's reflected **resistance**. Static DC code sweeps
  characterize the DAC transfer; they are not tests of a real transformer driven by DC.
- Eight error bounds: +/-1%, 0.5%, 0.1%, 0.05%, 0.02%, 0.01%, 0.005%, and 0.001%.
- 5,000 networks per bound per correlation mode, 80,000 networks total, seed 20261108.
- Errors are sampled uniformly within each bound. This is an explicit experiment,
  not a measured manufacturing distribution or production yield estimate.

The two correlation modes are independent errors for all resistors, and identical
errors in corresponding A/B branches while errors between different weights remain
independent. The terminations follow the same mode as the switched resistors.

## Metrics

For a measured code transfer V(D), define the endpoint line and calibrated step:

```text
LSB_fit = (V(4095)-V(0))/4095
INL(D) = [V(D)-V(0)-D*LSB_fit]/LSB_fit
DNL(D) = [V(D+1)-V(D)]/LSB_fit - 1
```

A strictly monotonic transfer has every step positive, equivalently every DNL > -1.
An increased digital code causing a lower output is a failure even if average gain
is accurate. INL and DNL remove endpoint gain/offset only for measurement; no physical
calibration circuit or correction algorithm is implemented. Gain error relative to
the nominal slope and centered offset are reported separately in JSON/CSV.

The table's INL percentile is taken across each network's **maximum absolute INL
over all codes**, not across individual code errors. It is not a worst-case bound.
These are static metrics, not ENOB, SNR, THD, or an audio-quality rating.

## Independent uniform-error results

| Resistance error bound | Strictly monotonic samples | 95th percentile max abs INL | Worst observed max abs INL |
|---|---:|---:|---:|
| +/-1% | 8.10% | 9.926 LSB | 16.337 LSB |
| +/-0.5% | 22.16% | 4.902 LSB | 7.837 LSB |
| +/-0.1% | 83.72% | 0.996 LSB | 1.565 LSB |
| +/-0.05% | 98.62% | 0.494 LSB | 0.736 LSB |
| +/-0.02% | 100% | 0.198 LSB | 0.344 LSB |
| +/-0.01% | 100% | 0.101 LSB | 0.163 LSB |
| +/-0.005% | 100% | 0.049 LSB | 0.077 LSB |
| +/-0.001% | 100% | 0.010 LSB | 0.015 LSB |

At +/-0.01%, the 95th-percentile absolute gain error was 0.00234%. Centered offset
was much smaller in this ideal symmetric topology. Both quantities are retained in
the output tables rather than being conflated with endpoint INL.

## Why midscale matters, and a deterministic bound

Let gAj and gBj be the actual conductances of bit j in the two arms. Let GA and GB
include all conductances in each arm, including the termination, and gL=1/Zp.
The two-node circuit solution is an affine function of the code bits:

```text
Delta = GA*GB + gL*(GA+GB)
w_j = Vs * (GB*gAj + GA*gBj) / Delta
offset = -Vs * GA * sum(gBj) / Delta
V(D) = offset + sum(bit_j(D)*w_j)
```

All prefactors are positive. A transition that clears k low bits and sets bit k
has voltage step w_k-sum(w_j for j<k). The most demanding ideal binary boundary
is 2047 -> 2048: the old weights sum to 2047 while the new weight is 2048.

For bounded fractional resistance errors +/-t, the smallest possible MSB
conductance and largest possible lower-bit sum in either arm are proportional to:

```text
2048/(1+t) - 2047/(1-t)
```

This is positive exactly when t < 1/4095, or t < 0.0244200244%.
The lower-order carries have looser bounds. Because the differential weights are
positive combinations of the arm conductances, the condition guarantees every step
is positive regardless of termination mismatch within the stated model.
Both arms can simultaneously realize the adverse combination, so exceeding the
bound allows a reversal; it does not mean every circuit beyond it will fail.

Explicit corner cases set the MSB resistance high and all lower-bit resistances
low in both arms, with nominal terminations:

| Error bound | Midscale step, fitted LSB | Result |
|---|---:|---|
| +/-0.02% | +0.1810 | Positive, but substantially smaller than one LSB |
| +/-0.05% | -1.0475 | Reverse step |

A sampled +/-0.1% network also produced a -2.0684 LSB step. The sample with the
largest INL need not be the sample with the worst monotonicity; both were tested.

## Correlation and tracking

Matching each A-arm resistor to its B-arm counterpart does not cancel a bit-weight
error in this differential topology: the weight contributions add. With identical
errors in corresponding A/B resistors, +/-0.1% produced 67.32% monotonic samples
and a 1.351 LSB INL 95th percentile. At +/-0.01%, that percentile was 0.138 LSB.
Independent arm errors sometimes partially average, explaining the better Monte
Carlo figures. That statistical averaging is not a design guarantee.

By contrast, scaling **all** resistors by the same +1% preserves their ratios.
The test produced zero endpoint INL to numerical precision, but gain changed by
-0.51075% because the load was held fixed. Ratio tracking among different weights
must therefore be distinguished from absolute resistance accuracy and A/B pairing.

## Verification

```powershell
python calc/resistor_tolerance.py
python sim/verify_resistor_tolerance.py
```

The Monte Carlo calculation uses the affine bit weights above. All possible
carry-step types are evaluated exactly. The maximum endpoint INL is computed
from the bit-weight deviations: every subset corresponds to a valid code, and
the largest absolute subset sum is half the sum of absolute deviations because
the deviations sum to zero. This avoids enumerating 4096 codes for every trial.

Six selected cases were additionally evaluated over all 4096 codes with a separate
two-node matrix solve, then run through structural ngspice DC sweeps: ideal,
two largest-INL samples, one smallest-step sample, and two bounded corners.
Independent analytical node solutions agreed within 2.22e-15 V. The 24,576 SPICE
DC points agreed with the analytical transfer to within 8.19e-8 LSB. The SPICE
models use idealized switches, Ron=1 microohm and Roff=1e12 ohm, at 5 V only.
The predicted reversal counts and corner steps were confirmed.

Outputs:

- `results/resistor_tolerance/summary.json` and `summary.csv`: metrics, seed, and exact example errors.
- `results/resistor_tolerance/verification.json`: SPICE checks for all selected codes.
- `sim/generated/resistor_tolerance/`: six reproducible low-voltage DC decks.
- `plots/resistor_tolerance/tolerance_summary.png`: tolerance versus monotonicity and INL.
- `plots/resistor_tolerance/midscale_transition.png`: positive and reversed midscale steps.
- `plots/resistor_tolerance/linearity_examples.png`: full-range INL and local DNL examples.

## Next modeling step

Use +/-0.01% ratio errors as a promising static baseline, with tighter cases for
margin. This does not select a resistor product or guarantee that real HV ratios
stay within that bound under dissipation and voltage stress. Extend the analysis
to the segmented network and model temperature/voltage dependence, leakage, and
finite switching behavior. Monotonicity alone does not establish 12-bit accuracy.
