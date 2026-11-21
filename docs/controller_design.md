# Digital control implementation for the fixed 3+9 DAC

Date: 2026-11-10. Architecture remains 3+9; this stage implements its command
logic and connects it to the review schematic.

## Implemented behavior

`control/controller.py` implements a synthesizable 50 MHz sequencer, exported to
`control/generated/rdac_control.v`. It generates 32 high-side and 32 low-side
commands plus a common driver enable. Logical channels 0–15 are A_00–A_15,
16–31 are B_00–B_15. Fine bits occupy indices 0–8 within each arm; thermometer
cells occupy 9–15. Arm B independently decodes 4095-D, including reversed coarse
cell correspondence. Input code is unsigned offset binary, not signed PCM.

On a sample request, only changing branches turn off. Unchanged branches remain
in their previous state. The target vector is latched, and changing branches
remain off for ten full clock periods (200 ns), then turn on in their new state.
A repeated identical settled code does not introduce a blank interval. Requests
while busy cause a latched protocol fault; this implementation has no queue.

Inputs `code`, `valid`, `arm`, `run`, `clear`, `ready` and `fault_n` must satisfy
the clock-domain contract. The core has no I2S receiver, asynchronous FIFO or
physical synchronizer wrapper. `valid` is one clock wide; the host must wait for
`busy=0`. At 192 kS/s the nominal sample period is about 5.208 us, much longer than
the 200 ns command pause, but this does not establish audio performance.

## Startup, stop and faults

Reset forces both command vectors and enable low. After reset, all drivers must
report ready and no fault. A fresh arm rising edge with RUN high activates the
sequencer; commands remain off until a valid sample is received. RUN falling
masks commands immediately in the behavioral model and disarms on the next clock.
Returning RUN high alone does not restart it.

FAULT low, READY loss while active, sample-while-busy, or missing valid samples
for approximately 1 ms cause a latched shutdown. Reset clears state. Otherwise,
clear requires RUN low, READY high and FAULT released, followed by a new arm edge.
A held code is supported by refreshing the same code before the watchdog expires;
silence does not mean that the PCM interface may silently stop.

READY/FAULT directly mask the outputs between clocks, but fault state is latched
on clock edges. Pulses shorter than a clock may mask without latching. An actual
wrapper needs defined asynchronous assertion, qualified release, pulse capture,
CDC and a separate response to clock failure. The synchronous watchdog cannot
detect failure of its own clock. This is a digital research implementation, not
a qualified hardware shutdown chain. Switching all devices off is not itself a
validated safe magnetic transient; that requires the transformer/clamp model.

## Dead-time budget

The [UCC21750 switching table](https://www.ti.com/lit/ds/symlink/ucc21750.pdf)
lists 60–130 ns propagation delay under its stated test conditions. A conservative
cross-edge calculation uses 130-60=70 ns mismatch, rather than assuming the
same-edge 30 ns part-skew specification covers arbitrary on/off events.

Illustrative budget:

| Contribution | Value | Status |
|---|---:|---|
| Command dead time | 200 ns | Ten 50 MHz cycles in HDL |
| Driver delay mismatch | 70 ns | Datasheet interval, stated test conditions |
| Additional turn-off / edge time | 50 ns | Assumption, NOT a guaranteed SiC limit |
| FPGA routing / external path mismatch | 20 ns | Assumption, not post-route measured |
| Residual illustrative margin | 60 ns | Conditional calculation only |

The 200 ns default is a simulation starting point. The actual gate drive uses
different loads and bias details; final dead time requires minimum turn-on and
maximum turn-off characterization across device, temperature and driver corners.
The longer pause must also be included in the next analog glitch/audio study.

## FPGA candidate and I/O budget

Working hardware candidate: **LCMXO2-2000HC-4TG144C**. The manufacturer's
[MachXO2 family information](https://www.latticesemi.com/-/media/LatticeSemi/Documents/Solutions/Packaging-Solutions/MachXO2-Family-Data-Sheet.ashx?la=en)
lists that ordering code and 111 general-purpose I/Os for the 2000 device in
144-pin TQFP. The logic interface needs 87 signals including clock: 64 commands,
enable/busy/fault, twelve code bits and eight other inputs. This is an I/O-count
screen only; dual-purpose/configuration pins and bank placement still need review.

No physical pin assignment, power-bank schematic, oscillator, JTAG wiring,
programming image, placement/routing or achieved 50 MHz timing is provided yet.
The schematic X900 uses **logical HDL port names**, not fabricated package pin
numbers. The candidate FPGA is recorded as a design choice in this document,
not disguised as a wired and verified 144-pin component.

## KiCad integration

`kicad/segmented/control.kicad_sch` is sheet 34. It shows the full logical module,
parallel host test interface and every H/L command. The old 64 CONTROL blocks
have been removed. Global labels are used specifically for inter-sheet command
connections; driver-to-gate and power wiring remain explicit.

All input-side VCC/GND references now share VCC3V3/DGND. All driver enables share
DRV_EN. Open-drain RDY and FLT outputs aggregate onto separate lines with 4.7 kohm
pullup placeholders on the control sheet. Their 64-device leakage, capacitance,
rise time and FPGA input margins are unqualified. Enable fanout may require
buffering. The driver DESAT protection is still disabled in the review bench;
a connected fault wire does not make a complete physical protection circuit.

Updated export: 34 sheets, 618 symbols, 2301 checked pins, 447 nets, no unintended
shorts or split nets. Custom passive symbol pin types limit ERC's electrical scope.
There is still no complete vendor-model SPICE simulation of the candidate assembly.

## Executed validation

Amaranth 0.5.10 simulation checks every 12-bit code and 1000 seeded random code
transitions, verifies complementary settled decoding, no simultaneous H/L command,
and the full programmed blank interval on changing channels. Fault, READY loss,
overspeed request, watchdog expiry, reset and RUN drop are exercised. The watchdog
parameter is shortened to 100 cycles in the test; generated production-reference
RTL retains 50000 cycles. The KiCad export is independently checked for all 64
command paths and 192 enable/status connections.

Verilog generation through bundled Yosys succeeds. That is HDL elaboration and
conversion, not a synthesis/utilization or FPGA timing sign-off. Behavioral
simulation coverage is not a formal proof over all sequences or analog behavior.

The initial analog blanking/transformer study is now complete; see
[results and limitations](controller_analog.md). Retain 200 ns for further tests.
Next: audio-band/low-level and stop/fault checks, then physical FPGA/bias interfaces. Do not reopen the 3+9 partition
without a concrete failing result.

## Independent-arm extension and mute wrapper

The standalone core now has `independent` and `code_b` inputs. Drive
`independent=0` for the legacy behavior described above, or select explicit arm
codes with `independent=1`. The new `mute_controller.py` wrapper handles signed
24-bit PCM, pre-quantization fading and coordinated common-mode movement.
See [FPGA mute implementation](fpga_mute.md) for the updated interface and tests.
The earlier KiCad logical input block is not yet an integration of this wrapper.
