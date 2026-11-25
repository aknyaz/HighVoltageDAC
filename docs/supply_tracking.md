# Equal-output heat and slow supply tracking

Date: 24 November 2026. Follow-up to [the fixed-supply audio study](supply_voltage_study.md).
Reproduce with `python sim/supply_tracking.py`; netlists and results are saved
under `sim/generated/supply_tracking/` and `results/supply_tracking/`.

## Resistor heat at equal target signal

This calculation uses the exact equivalent branch resistances of the 3052-chip
candidate (5281.25 ohm per arm), ideal switches and a 10 kohm resistive load.
It evaluates each branch, including the grounded termination, at every sample
of a 192-sample 1 kHz sine. At each supply the signal is rescaled before 12-bit
rounding. Instantaneous source power equals resistor heat plus load power to
within 2e-14 W. This is a power calculation, not a temperature simulation.

| Target amplitude relative to 650 V full scale | Array heat at 650 V | Array heat at 100 V | Load power at 650 / 100 V |
|---|---:|---:|---:|
| 10% (-20 dBFS) | 39.8528 W | 0.7996 W | 49.9442 / 49.9440 mW |
| 1% (-40 dBFS) | 39.9985 W | 0.9453 W | 0.50279 / 0.49931 mW |
| 0.1% (-60 dBFS) | 40.0000 W | 0.9467 W | 5.1619 / 5.0373 uW |

The target signal is identical in each pair; actual load power differs slightly
because of quantization (and includes the distorted waveform's total power).
Array heat is for both arms of one channel. The low-level reduction is about
42 times, and about 50 times at the -20 dBFS target because code utilization also
changes. It must not be interpreted as the efficiency of the whole amplifier.
Driver bias, switching losses, transformer losses, regulator losses and any
thermostat heater are excluded. The earlier LL1679 audio results use the prior
5274.70 ohm arm equivalent; the two models are deliberately distinguished.

## Tracking experiment

The supply command starts at 650 V, ramps to 100 V over 200 ms, holds for
200 ms, and ramps back to 650 V over 200 ms. The experiment maintains a constant
desired 6.5 V peak differential source signal so that any volume modulation is
an error. This isolates supply handover; it is not yet a complete volume-knob
policy, arbitrary mid-ramp reversal or a maximum-output test.

Supply behavior is represented by an assumed first-order response with 10 or
50 ms time constant. These values are sensitivity cases, not measurements or
specifications of a selected converter. The circuit does not model rail load
coupling or the physical method of discharging the supply.

For each lag and for 20 Hz / 1 kHz audio, compare:

1. Digital scaling based on commanded rail voltage: source amplitude is
   multiplied by actual supply divided by commanded supply.
2. Scaling based on perfect instantaneous knowledge of actual rail voltage:
   the voltage factor cancels algebraically. This is an ideal reference bound,
   not proof that a practical measurement/control system achieves cancellation.

Both signals drive identical continuous Thevenin/linear LL1679 models from
`low_frequency_mute.py`. There is no 12-bit rounding, sample hold or switching
in this bounded tracking experiment. The preceding fixed-supply study covers
those effects separately; results must not be combined into a hardware guarantee.

The source gain ratio with command-based scaling ranges approximately from
0.846 to 1.275 for 10 ms lag, and 0.638 to 2.350 for 50 ms lag. The largest
over-amplification occurs near the end of the downward ramp, where the actual
rail remains above the requested 100 V. The rising ramp produces attenuation.
The code amplitude remains below 0.065, so these effects are not caused by
digital clipping in this experiment.

Executed output results with command-based scaling:

| Tone | Supply time constant | Peak output error | Peak error / reference peak |
|---|---:|---:|---:|
| 20 Hz | 10 ms | 15.6175 mV | 19.2817% |
| 20 Hz | 50 ms | 89.3370 mV | 110.2975% |
| 1 kHz | 10 ms | 22.7732 mV | 27.3059% |
| 1 kHz | 50 ms | 111.9958 mV | 134.2870% |

These percentages describe temporary waveform error, not THD. All four perfect
actual-voltage controls cancel to below 1.5e-12 V output error, a numerical
identity check rather than a realizable audio performance claim.
See the [tracking plot](../plots/supply_tracking/tracking.png).

The mechanism is multiplicative: source gain = actual rail / rail estimate.
Therefore slowing the rail command helps but does not by itself establish an
audio error bound. Rail estimation accuracy and latency must be part of the
digital scale calculation. Perfect actual-rail scaling cancels the error in
this model by construction; practical residual error remains to be evaluated.

## Verification and limitations

All 16 runs passed. The largest rail error against the analytical response was
3.21 uV and the largest timestep change in peak output error was 21.1 nV.
The original `python sim/run_phase_a.py` regression also passed.

The script executes 16 SPICE transients (eight cases at 20 and 10 us maximum
timesteps). It compares the simulated rail to an independent exact analytical
first-order response, checks completion and timestep refinement, and verifies
the ideal cancellation control. Numerical results and logs are retained.
Transient peak output error is reported separately from THD: it is not a
stationary harmonic measurement. Flux-linkage error is not magnetic flux density
or a core saturation qualification. Window-average differential source error
is a finite-transition mean, not evidence of persistent DC.

The next bounded step is to add finite rail-measurement delay/accuracy and
ripple, then combine the chosen slow volume policy with 12-bit held codes.
Do not select an FPGA or a physical HV supply based on this simplified model.
