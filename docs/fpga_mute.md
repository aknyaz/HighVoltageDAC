# FPGA mute sequencer

## Implemented result

`control/mute_controller.py` adds a synthesizable Amaranth wrapper around the
existing 3+9 gate sequencer. `control/generated/rdac_mute_control.v` is the
exported RTL. This is executed digital logic, not a programmed or routed FPGA.
The independent-arm extension also appears in `rdac_control.v`; its legacy
complementary mode remains available and passes the existing 5,096-code tests.

The wrapper accepts **signed 24-bit PCM**, applies an amplitude envelope before
12-bit quantization, and sequences common-mode movement independently of audio.
The default ramp length is 384 accepted samples: 2 ms at 192 kS/s per ramp.
No dither, error feedback, I2S receiver, asynchronous FIFO or sample-rate
conversion is added.

## Interface and behavior

Inputs `pcm`, `mute`, `valid`, `arm`, `run`, `ready`, `fault_n`, `clear` and
`reset_n` obey the existing synchronous-control contract. `valid` must be one
clock wide and arrive only when `busy=0`. `pcm` and `mute` are sampled with it.
Each accepted sample advances the envelope/common-mode level by one step.
Changing `mute` without `valid` does not advance the sequence.

| Request and current condition | Next accepted sample |
|---|---|
| Mute, nonzero audio gain | Reduce gain by one step. |
| Mute, zero gain and nonzero common level | Reduce common level by one step. |
| Mute, both levels zero | Refresh the all-low command without switching. |
| Unmute, common level below midpoint | Increase common level by one step. |
| Unmute, common at midpoint and gain below full | Increase gain by one step. |
| Unmute, both levels full | Process full-level PCM. |

A request reversal retraces the current ramp without jumping to a boundary.
Mute takes 768 accepted samples (4 ms at 192 kS/s) from full play to park;
unmute takes the same number from park to full play. Startup after arming also
begins from the zero-level state and follows the unmute path if requested.
Gate commands remain off until the first accepted sample. A first muted sample
commands all lower switches on through the existing blanking sequencer.

`muted` is asserted only when the controller is enabled, both levels are zero,
blanking is complete, all high-side commands are off, and all low-side commands
are on. It deasserts on disable/fault. `gain_step` and `common_step` expose the
accepted levels; `code_a` and `code_b` expose combinational targets for the next
accepted sample, not necessarily the currently settled gate state.

The ramps are sample-count based. At 384/768 kS/s the default durations become
1/0.5 ms; use 768/1536 samples if retaining 2 ms ramps at those rates. This wrapper
does not qualify those rates or enforce a fixed sample cadence.

## Arithmetic

Let N = ramp_samples, g = gain_step, c = common_step, and x = pcm / 2^23.
The command levels are independently rounded half upward:

- A = round_half_up((4095/2) * (c/N + x*g/N)).
- B = round_half_up((4095/2) * (c/N - x*g/N)).

The sequencer ensures g > 0 only when c = N. During common-mode movement g = 0,
so both arm codes are identical. Zero PCM at full common level maps to
2048/2048, eliminating the one-code differential midpoint offset of the legacy
complementary 2048/2047 pair. Signed 24-bit extrema stay within 0..4095.
Integer multiplication and constant division implement the envelope before
rounding; this does not recover information already lost in a 12-bit source.

`Controller.independent=1` selects explicit `code` and `code_b` targets.
When it is zero, B remains 4095-code, preserving the existing standalone core
behavior. The mute wrapper holds this mode high internally. Standalone users
must explicitly drive this new input; an unconnected hardware pin is not a
valid way to select the legacy mode.

## Watchdog and fault priority

Every quiet refresh passes through the normal valid-sample watchdog. Holding
silence does not disable supervision. With the default 50 MHz clock, missing
samples still produces a fault after approximately 1 ms, including while parked.
The host must continue refreshing valid samples even when no gate changes occur.

RAW RUN/READY/FAULT/reset masks keep priority over the envelope, including during
blanking. Faults are handled by the existing core. On disable the wrapper clears
its levels, so a later explicit rearm starts from park instead of resuming an
interrupted ramp. Removing a fault or restoring RUN alone does not rearm.
This does not validate the analog consequences of all-gates-off shutdown.

## Executed verification

```powershell
.venv/control/Scripts/python.exe control/verify.py
.venv/control/Scripts/python.exe control/verify_mute.py
.venv/control/Scripts/python.exe control/controller.py
.venv/control/Scripts/python.exe control/mute_controller.py
```

The legacy suite passed 5,096 code cases and 56,187 non-overlap checks, including
its exported schematic channel-order checks. The mute suite passed:

- 1,761 samples at the default ramp length with 260/261-clock sample spacing,
  independent Fraction-based arithmetic and branch decoding, signed PCM extrema
  and seeded random PCM; 21,136 timing/non-overlap checks.
- Quiet refresh for 220 samples (over 1 ms), with no switching or watchdog fault,
  followed by intentional loss of refresh and the expected timeout shutdown.
- 547 samples covering partial-ramp reversals and 36 phase/fault combinations;
  6,765 additional timing/non-overlap checks.
- Fault, READY loss, RUN drop and reset asserted during actual blank intervals
  in six phases; overspeed requests and missing samples in all six phases;
  no automatic restart on restoration.

For every normal accepted request, tests check that unchanged branches stay on,
changing branches remain off for ten full 50 MHz cycles, no high/low overlap
occurs, the final decoded states are correct, and `muted` waits for settling.
Results: `results/control/mute_verification.json`. An executed sample-command
trace is saved in `results/control/mute_commands.csv`; it contains settled
commands and is not a timestamped gate-edge trace or an analog co-simulation.

## Integration limits and next step

The earlier analog quiet study used a Python-generated schedule, not this RTL.
Its 26-fold peak-error reduction must not be presented as a new measurement of
this implementation. Startup, sample alignment and integer PCM rounding now have a nominal
one-way gate-edge replay in [RTL replay](rtl_mute_replay.md). Request reversal,
fault feedback and nonnominal analog coverage remain open.

The wired KiCad X900 block remains the earlier logical interface. Its 64 gate
outputs and status paths still match the core, but the 24-bit PCM/mute wrapper
is not wired into that sheet or assigned to physical FPGA pins yet.

The generated arithmetic contains multipliers and constant dividers. FPGA
resource fit and 50 MHz timing are unproven, including for the provisional
LCMXO2-2000HC candidate. The bundled Amaranth Yosys supports RTL export but its
`synth` command is unavailable; export is not a device-mapped synthesis result.
A real target flow may require pipelining, a different arithmetic implementation,
or moving audio processing upstream. CDC, clock failure and driver/bias hardware
remain open. No PCB or energized HV build is included.
