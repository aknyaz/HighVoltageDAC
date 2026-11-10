# Binary versus segmented switching timing

## Result

For the matched-resistor, ideal-SPDT model, segmentation reduces the largest
adjacent-code carry glitch by a factor of eight under the tested timing profiles.
This is a timing-only result, not a hardware bandwidth, audio distortion, or
transformer-output prediction.

At the 2047 to 2048 transition, with 20 ns inter-group skew:

| Architecture | Largest error relative to ideal requested output | Error at 5 V supply | Absolute error area |
|---|---:|---:|---:|
| Binary | 2048 LSB | 2.43316 V | 48.6632 V ns |
| Segmented 4+8 | 256 LSB | 0.304145 V | 6.08290 V ns |

The corresponding areas are 40960 and 5120 LSB ns. At 100 ns they are five
times larger; peak magnitude does not change in this memoryless resistive model.
At zero skew, ideal simultaneous switching produces no extra glitch.

## Model and timing definition

- Supply: 5 V. Load: 10 kohm resistance, representing the previous nominal
  reflected load only. There is no actual transformer in these decks.
- Nominal output resistance per arm: 5274.699627701833 ohm.
- Branch resistance: `4096 * R / weight`, with a grounded unit-weight termination.
- Binary weights: 1 through 2048 in powers of two.
- Segmented weights: eight binary weights 1 through 128 and fifteen thermometer
  weights of 256. Arm B decodes `4095 - code` independently, retaining the
  complementary coarse-index mapping established in the tolerance study.
- All resistors are nominal. SPDT switches use paired ideal SPST models with
  Ron = 1 microohm and Roff = 1 teraohm. These are numerical idealizations.
- Requested transition time: 1 us. Two timing profiles are tested: the largest
  changing branch switches late (`heavy_late`), or all smaller changing branches
  switch late (`light_late`). The same weight-group timing applies to both arms.
- Delay is 0, 20, or 100 ns. These are sensitivity scenarios, not device data.
- The 1 ps control ramp places the ideal switch threshold at the requested event
  time. It does not model a 1 ps physical device voltage transition.
- No dead time, overlapping conduction, capacitance, charge injection, leakage
  mismatch, driver supply limitations, thermal effects, or resistor mismatch.

The nominal loaded differential LSB is 1.188066969577229 mV. Between events,
the differential output is exactly

`Vdiff = (Vs / 4096) * Load / (Load + 2*R) * sum(weight * (state_A - state_B))`.

The total conductance is constant because each ideal SPDT always connects its
branch to one rail. That identity would need revision during dead time.

## Why the peaks differ

At binary midscale, a rising weight of 2048 cancels falling weights totaling 2047.
If the heavy branch arrives late, the intermediate error relative to the final
code is -2048 LSB. If the lighter branches arrive late, it is +2047 LSB.

At a segmented coarse boundary, a rising weight of 256 cancels falling fine
weights totaling 255. The corresponding errors are -256 and +255 LSB. Reverse
transitions reverse the signs. Within a coarse segment, fine-bit carries remain.

These large peaks last only for the delay interval. They must not be interpreted
as settled INL or directly converted to an audio distortion percentage. Error
area, pulse repetition, signal dependence, and the eventual analog transfer
function all matter.

## Verification performed

`python sim/compare_switching_glitches.py`

The script scans all 4095 ascending adjacent-code transitions analytically for
each architecture and both timing profiles. Descending counterparts have the
same magnitudes by reversal symmetry. The worst peaks are 2048 and 256 LSB;
multiple segmented coarse boundaries tie, so a reported maximizing index may
depend on floating-point rounding.

Structural ngspice transients cover 127/128, 255/256, and 2047/2048 in both
directions, both timing profiles, and all three delays: 72 cases total.
Every case checks the settled/intermediate voltages against the independent
event calculation and integrates the SPICE waveform to check signed error area.
The largest voltage difference away from event edges is below 7.82e-8 LSB.
Area assertions allow 0.05 LSB ns plus 0.1% of the exact area for numerical
integration of discontinuities. This is not a measured hardware tolerance.

Transient maximum timestep is 1 ns, with source breakpoints at the switching
edges. There is no energy-storage state here; plateau and integral comparisons
are the relevant independent verification. Time-resolution convergence must be
revisited when capacitances or magnetic dynamics are introduced.

Artifacts:

- `sim/generated/switching_glitches/`: 72 independently runnable 5 V decks.
- `results/switching_glitches/summary.json` and `.csv`: per-case metrics.
- `results/switching_glitches/ngspice.log`: simulator output.
- `plots/switching_glitches/midscale_glitch.png`: actual SPICE waveforms.
  The two panels intentionally have different vertical scales.

## Decision and next experiment

Segmentation now has demonstrated advantages in static mismatch sensitivity and
ideal carry timing. It still uses 46 SPDT functions rather than 24, with unchanged
ideal resistor heat. More devices can introduce additional capacitance and driver
burden, which this comparison cannot price or quantify yet.

The next model should introduce explicit branch capacitance and break-before-make
timing, then connect a documented transformer equivalent circuit. Test arbitrary
PCM code jumps and relative arm timing as well as adjacent carries. No present
result establishes acceptable 192 kS/s audio performance or selects a real switch.
