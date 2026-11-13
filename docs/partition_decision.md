# Working architecture decision: 3+9 segmented parallel DAC

## Decision

Freeze **3 thermometer-decoded coarse bits plus 9 binary fine bits** as the working
12-bit architecture. Stop broad partition exploration. The next implementation
and transformer tests should use this partition; the existing 4+8 results remain
references, not the default design. This decision selects a development baseline,
not qualified hardware or a final driver BOM.

Per arm: seven equal weight-512 branches, nine binary branches of weights 1–256,
and one grounded unit-weight termination. There are 16 SPDT functions per arm,
32 total, implemented conceptually by 64 transistors. Resistance is 4096*R/weight
with the previous nominal R=5274.699627701833 ohm. The two arms decode D and 4095-D.
Increasing coarse index j turns A[j] on and B[6-j] off.

Use the existing 650 V analytical / 5 V simulation normalization and 10 kohm
reflected-load reference for the 5 W target. Retain the 0.01% bounded resistance-
error scenario as the static modeling baseline, including terminations. This is
a ratio-error budget assumption, not a claim about assembled accuracy or drift.

## Comparison performed

`python calc/partition_study.py`

Seven partitions, coarse bits 0 through 6, were evaluated. The 0+12 and 1+11
partitions have identical ideal weights, serving as a useful consistency reference.
Every partition uses the same output resistance, ideal transfer and resistor heat.

Mismatch: 5000 networks per partition, tolerance and correlation mode; three
uniform bounded tolerances (0.01%, 0.05%, 0.1%), independent arms or physically
same-index paired errors. Total: 210000 networks, seed 20261110. Reported INL is
endpoint-calibrated; gain/offset, temperature and device errors are not included
in this accuracy criterion. Monte Carlo fractions are not manufacturing yield.

Exact fine-carry and coarse-boundary expressions find the minimum step; cumulative
coarse errors plus fine-bit subset extrema find full-range maximum INL. For each
partition the worst sampled independent 0.01% case is checked against a separate
full 4096-code nodal solve. Eight structural SPICE sweeps then verify those seven
cases plus the ideal 3+9 case: 32768 code points. Maximum disagreement is below
8.18e-8 LSB. Run `python sim/verify_partition_study.py`.

## Results

| Partition | Transistors | Adjacent carry peak (LSB) | INL p95, independent 0.01% (LSB) | Switch + driver estimate (W) |
|---|---:|---:|---:|---:|
| Binary / 0+12 | 48 | 2048 | 0.099 | 25.18 |
| 1+11 | 48 | 2048 | 0.099 | 25.18 |
| 2+10 | 52 | 1024 | 0.094 | 25.45 |
| **3+9** | **64** | **512** | **0.072** | **26.25** |
| 4+8 | 92 | 256 | 0.053 | 28.13 |
| 5+7 | 152 | 128 | 0.039 | 32.15 |
| 6+6 | 276 | 64 | 0.028 | 40.58 |

The carry column is the analytical peak for the previous ideal matched-resistor
heavy-late/light-late timing experiment on adjacent codes. It is not a bound on
real parasitic transients or arbitrary multi-code PCM jumps. At 20 ns skew, the
3+9 maximum ideal error area is 10240 LSB ns. No new transistor transient study
is claimed by this static partition comparison.

Power uses the previous approximate nonlinear SiC charge model and the same
one-UCC21750-per-FET driver reference, at 650 V, full-range rounded 1 kHz sine and
192 kS/s. It excludes resistor, transformer and bias-converter losses. These
are scenarios, not new device measurements; see `sic_charge_and_drivers.md`.

For 3+9, 1464 branch-node transitions/ms give 20.51 W capacitive loss, 0.53 W gate
charge and 5.21 W driver quiescent power. The 4+8 sum is only 1.88 W higher.
Segmentation choice alone therefore does not solve the heat problem. Adding the
previous 25.3 W resistor estimate gives roughly 51.6 W losses for the 3+9 scenario.

## Why stop at 3+9

The selected engineering compromise is: at least fourfold reduction in the ideal
binary adjacent-carry peak; at most 64 transistors; and INL p95 below 0.1 LSB in
both tested correlation modes at 0.01% tolerance, with all sampled networks
monotonic. These are explicit design judgments for selecting a baseline, not
requirements previously supplied by the user or a proof of global optimality.
Only 3+9 satisfies this combination within the tested set.

Relative to 4+8 it removes 28 transistors and driver channels (30.4%), and reduces
floating upper-source domains from 46 to 32. It accepts twice the ideal carry
peak and moderately worse mismatch accuracy. Relative to 2+10 it adds 12 devices
but halves the carry peak again. Larger thermometer sections rapidly increase
device count and driver overhead.

For 3+9 at 0.01%, independent-error INL p95 is 0.0716 LSB; worst sampled INL is
0.1130 LSB. The paired-error p95 is 0.0557 LSB. All sampled networks are monotonic
and within 0.5 LSB INL. At 0.05%, independent p95 is 0.357 LSB and 99.86% meet
0.5 LSB; at 0.1%, p95 is 0.721 LSB and only 68.1% meet 0.5 LSB.

The sufficient positive-step tolerance bound is t < 1/(2*512-1), or 0.09775%,
for the ideal matched-topology model with independently bounded resistor errors.
It follows from 512/(1+t) > 511/(1-t); fine carries have a looser bound. Although
all sampled 0.1% cases were monotonic, that tolerance exceeds the guarantee.
Neither the bound nor the sampled INL includes real-switch or board effects.

## Bounded completion path

1. Implement a readable wired 3+9 KiCad bench and verify its exported connectivity.
2. Validate this fixed architecture with switching/driver timing and a documented
   transformer equivalent model: frequency response, DC/flux, and PCM distortion.
3. Consolidate component and thermal budgets; choose a small low-voltage proof-of-
   concept configuration before any physical HV design.

Reopen partition selection only if these checks demonstrate a concrete failure
that the split can remedy. Do not reopen it merely because another split has a
slightly better isolated metric. Device/driver optimization remains useful within
the fixed 3+9 architecture; its unresolved losses are explicitly carried forward.

Artifacts: `results/partition_study/`, `sim/generated/partition_study/`, and
`plots/partition_study/partitions.png`. Existing KiCad files still represent the
earlier benches; this task has not silently changed them into a 3+9 schematic.
