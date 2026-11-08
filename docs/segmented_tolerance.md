# 12-bit segmented parallel DAC: resistor mismatch comparison

## Result

The specified 4+8 segmented network is substantially more robust against reverse
code steps than the binary parallel network. In the independent uniform +/-0.1%
scenario, all 5,000 segmented samples were strictly monotonic, compared with 83.72%
of the earlier binary samples. The 95th percentile of maximum endpoint INL improved
from 0.996 to 0.531 LSB.

The deterministic static monotonicity condition changes from t < 1/4095 for the
binary network to t < 1/511 for this segmentation: **less than +/-0.195695%**,
roughly eight times the binary bound. This is a bound on positive steps, not a
guarantee of INL within half an LSB, real 12-bit accuracy, or dynamic performance.

At +/-0.1%, only 92.40% of the independent segmented samples had maximum absolute
INL <=0.5 LSB, despite all being monotonic. These two requirements must remain separate.

## Circuit and comparison conditions

The topology is the parallel network defined in `resistive_architecture_comparison.md`:

- 15 equal coarse branches of weight 256, representing the upper four bits with
  a fixed thermometer decoder.
- Eight binary fine branches of weights 1, 2, 4, ..., 128.
- One fixed grounded branch of weight 1 in each arm.
- Two complementary arms driven with D and 4095-D, directly loading a reflected
  primary resistance of 10 kohm.
- Nominal equivalent resistance R=5274.6996277 ohm per arm; branch resistance
  is 4096*R/weight. This retains the earlier 650 V / 5 W comparison values.
- Calculations and SPICE checks use 5 V. This linear resistive model has the same
  normalized INL/DNL when supply voltage is scaled.

No physical high-voltage circuit is built. The DC transfer sweep uses a resistive
load, not a real transformer receiving static DC. Switch parasitics, leakage,
temperature drift, voltage coefficient, thermal gradients, and noise are excluded.

The new study uses the same eight tolerance bounds and 5,000 networks per point
as the binary study, with seed 20261109. For each resistor, the value is
nominal*(1+error), with error sampled uniformly inside the stated bounds.
Two correlation modes give 80,000 new networks:

1. Independent errors in all 48 resistors.
2. The same error in corresponding A/B resistor indices, with independent errors
   across different indices. The terminations follow the same rule.

The comparison reads the existing binary study with seed 20261108. Both studies
have equal trial counts and the same distribution assumptions; their differently
sized resistor arrays do not represent paired samples. Percentages describe these
simulated distributions, not production yield.

## Independent-error comparison

INL uses the fitted endpoint line and is reported in fitted LSB, as defined in
`resistor_tolerance.md`. Each percentile is across networks' maximum absolute
INL over all 4096 codes. No physical calibration is implemented by this metric.

| Resistor error bound | Binary monotonic | Segmented monotonic | Binary INL p95 | Segmented INL p95 |
|---|---:|---:|---:|---:|
| +/-1% | 8.10% | 14.36% | 9.926 LSB | 5.360 LSB |
| +/-0.5% | 22.16% | 62.54% | 4.902 LSB | 2.660 LSB |
| +/-0.1% | 83.72% | 100% | 0.996 LSB | 0.531 LSB |
| +/-0.05% | 98.62% | 100% | 0.494 LSB | 0.264 LSB |
| +/-0.02% | 100% | 100% | 0.198 LSB | 0.105 LSB |
| +/-0.01% | 100% | 100% | 0.101 LSB | 0.053 LSB |
| +/-0.005% | 100% | 100% | 0.049 LSB | 0.026 LSB |
| +/-0.001% | 100% | 100% | 0.010 LSB | 0.005 LSB |

At +/-0.05%, all 5,000 independent segmented samples had INL <=0.5 LSB;
the largest observed value was 0.412 LSB. That finite sample does not establish
a worst-case INL bound. At +/-0.01%, the largest observed value was 0.087 LSB.

## Correct complementary decoding

Write D=256*C+F, where C ranges from 0 to 15 and F from 0 to 255.
Arm A enables the first C coarse branches; arm B enables the first 15-C coarse
branches. When C increases from j to j+1, A[j] turns on and **B[14-j] turns off**.
Using a one-for-one inversion of coarse branch j would describe a different
physical error assignment and give incorrect results for this specified decoder.

With actual conductances gAj and gBj, arm totals GA and GB including terminations,
and Delta=GA*GB+(GA+GB)/Zp, the effective fine weights are:

```text
f_j = Vs * (GB*gA_fine_j + GA*gB_fine_j) / Delta
```

The effective coarse increments are:

```text
c_j = Vs * (GB*gA_coarse_j + GA*gB_coarse_(14-j)) / Delta
offset = -Vs*GA*sum(all switched B conductances)/Delta
V(D) = offset + sum(first C coarse increments) + sum(enabled fine weights)
```

Within a segment, binary fine carries have steps f_k-sum(f_j for j<k).
At a segment boundary, the step is c_j-sum(all eight fine weights).
All eight fine carry types and all 15 coarse boundaries are evaluated for every trial.

Maximum INL is computed exactly from coarse-prefix deviations plus the possible
fine-bit subset deviations. Six selected cases are also enumerated over all codes
and compared with a separate two-node conductance matrix solve. This validates the
fast metric calculation and the complementary branch indexing.

## Deterministic monotonicity condition

At a coarse boundary, one weight-256 branch replaces fine weights totaling 255.
Under resistance bounds +/-t, the smallest possible forward conductance change
in either arm is proportional to:

```text
256/(1+t) - 255/(1-t)
```

It remains positive when t < 1/511. Fine-only carries have a looser bound:
the largest is 128 replacing 127, requiring t < 1/255. The positive coefficients
in the differential expression preserve the sign, so the coarse condition is
sufficient for every transition. Both arms can realize the adverse coarse/fine
errors at once; crossing the bound permits a reversal.

The explicit corner sets all coarse resistances high and all fine resistances
low in both arms, leaving terminations nominal. SPICE confirmed:

| Error bound | Minimum step | Nonpositive steps |
|---|---:|---:|
| +/-0.1% | +0.48943 LSB | 0 |
| +/-0.2% | -0.02204 LSB | 15 |

The guarantee assumes those error bounds remain valid during operation and all
other elements are ideal. Initial tolerance alone does not cover temperature,
voltage stress, driver errors, leakage, or switching effects.

## Correlation matters

With same-index paired A/B errors, segmented INL p95 was 0.398 LSB at +/-0.1%
and 0.040 LSB at +/-0.01%, somewhat better than the independent segmented scenario.
This differs from the binary result: the fixed thermometer decoder combines
opposite-index coarse branches, producing symmetric effective coarse increments
when same-index A/B errors are equal. The correlation changes the accumulated
coarse-prefix error. It is not a universal benefit of matching across two arms.

Different thermometer ordering, reversed-index matching, and shared coarse/fine
drift are different statistical scenarios, not covered by these percentages.
The explicit bounded corner is included to avoid relying only on favorable random
averaging. Uniformly increasing all resistor values by 1% still changes gain but
leaves endpoint INL essentially zero, confirming that ratio error is distinct from
common absolute resistance error.

## Verification and files

```powershell
python calc/segmented_tolerance.py
python sim/verify_segmented_tolerance.py
```

The first command reads `results/resistor_tolerance/summary.json` for the binary
comparison. The second builds structural switched SPICE decks with explicit
fine/coarse decoding and sweeps all 4096 codes in six cases: nominal, two large-INL
samples, a small-step sample at +/-0.5%, and the two coarse/fine corners.

All 24,576 DC points passed. Maximum SPICE/analytical disagreement was 1.24e-8 LSB;
the separate analytical node solve agreed within 2.22e-15 V. These tiny errors
measure agreement between ideal models, not achievable physical precision.
SPICE uses Ron=1 microohm, Roff=1e12 ohm, and a 5 V source. The existing binary
and KiCad models were not altered.

- `results/segmented_tolerance/summary.json` and `summary.csv`: trial statistics and exact example errors.
- `results/segmented_tolerance/verification.json`: full-code SPICE results.
- `sim/generated/segmented_tolerance/`: six low-voltage DC decks.
- `plots/segmented_tolerance/binary_vs_segmented.png`: direct tolerance comparison.
- `plots/segmented_tolerance/linearity_examples.png`: INL/DNL over the full code range.

## Design implication

The 4+8 segmentation earns its place as a serious candidate: substantially greater
static monotonicity margin and roughly half the sampled INL at the same independent
error bounds. It retains the parallel architecture's ideal heat rather than adding
an efficiency improvement. The cost remains 46 SPDT functions instead of 24 across
the two arms, with more drivers and potentially different switching loss/glitches.

Do not select hardware solely from the static result. Next compare timing, leakage,
Ron and capacitance effects, especially coarse-boundary transitions, while retaining
the 0.01% ratio-error case as a useful baseline. Lower-cost or looser-tolerance
options can be evaluated, but +/-0.1% has not demonstrated universal half-LSB INL.
