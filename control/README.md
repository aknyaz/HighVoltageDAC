# 3+9 FPGA command sequencer

This is synthesizable HDL expressed in Amaranth, with generated Verilog and
executed behavioral simulation. It is not a programmed or routed FPGA design.

```powershell
python -m venv .venv/control
.venv/control/Scripts/python.exe -m pip install -r control/requirements.txt
python kicad/generate_segmented.py
python kicad/verify_segmented.py
.venv/control/Scripts/python.exe control/verify.py
.venv/control/Scripts/python.exe control/controller.py
```

`controller.py` is the source; `generated/rdac_control.v` is generated, not manually
edited. `verify.py` simulates actual HDL, checks an independent decoder, and
cross-checks the exported KiCad netlist against HDL channel order. Results are
in `results/control/verification.json`. See `docs/controller_design.md` for the
protocol, assumptions and unfinished hardware wrapper.

## Mute wrapper

`mute_controller.py` accepts signed 24-bit PCM and a synchronous mute request,
implements the pre-quantization envelope and common-mode ramps, and feeds
independent arm targets into the existing sequencer. Default: 384 samples per
ramp, or 2 ms at 192 kS/s. Quiet refresh remains subject to the watchdog.

```powershell
.venv/control/Scripts/python.exe control/verify_mute.py
.venv/control/Scripts/python.exe control/mute_controller.py
```

See [FPGA mute implementation](../docs/fpga_mute.md) for arithmetic, reversal and
fault behavior, executed tests and hardware integration limits. The exported
`generated/rdac_mute_control.v` is a new wrapper, not a drop-in physical-pin
replacement for the existing KiCad logical control block. In the standalone
core, drive `independent=0` for legacy complement decoding or `independent=1`
with explicit `code_b` for two arm targets.


`export_mute_edges.py` records actual timestamped RTL output vectors for a full
startup/mute/resume cycle. Run it with the control virtual environment, then
run `python sim/rtl_mute_replay.py` with the analog-analysis environment. See
[executed replay](../docs/rtl_mute_replay.md) for results and scope.
