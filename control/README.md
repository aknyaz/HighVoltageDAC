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
