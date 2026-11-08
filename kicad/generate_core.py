"""Generate the editable passive core sheet; full switched bench lives in sim/."""
from pathlib import Path
from uuid import uuid4
import json

HERE = Path(__file__).resolve().parent
uid = lambda: str(uuid4())
root = uid()
font = '(effects (font (size 1.27 1.27)))'
parts = [f'''(kicad_sch (version 20250114) (generator "eeschema")
 (uuid "{root}") (paper "A4")
 (title_block (title "HV-RDAC | 4-bit passive core") (rev "A0")
 (comment 1 "5 V simulation only; switched stimulus and transformer in sim/generated"))
 (lib_symbols
 (symbol "HV_RDAC:R" (pin_names (offset 0)) (in_bom yes) (on_board yes)
 (property "Reference" "R" (at 0 0 0) {font})
 (property "Value" "R" (at 0 0 0) {font})
 (symbol "R_0_1" (rectangle (start -1.016 -2.54) (end 1.016 2.54)
 (stroke (width 0.254) (type default)) (fill (type none))))
 (symbol "R_1_1"
 (pin passive line (at 0 3.81 270) (length 1.27) (name "~" {font}) (number "1" {font}))
 (pin passive line (at 0 -3.81 90) (length 1.27) (name "~" {font}) (number "2" {font})))))
''']
components = []


def label(name, x, y):
    parts.append(f'(label "{name}" (at {x} {y} 0) {font} (uuid "{uid()}"))')


def wire(x1, y1, x2, y2):
    parts.append(f'(wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0) (type default)) (uuid "{uid()}"))')


def resistor(ref, value, x, y, a, b, horizontal=False):
    x, y = round(x/1.27)*1.27, round(y/1.27)*1.27
    spice_ref = ref
    ref = f'R{len(components)+1}'
    angle = 90 if horizontal else 0
    rx, ry, vx, vy = (x, y-5, x, y+5) if horizontal else (x+4, y-1.5, x+4, y+1.5)
    identifier = uid()
    parts.append(f'''(symbol (lib_id "HV_RDAC:R") (at {x} {y} {angle}) (unit 1)
      (in_bom yes) (on_board yes) (dnp no) (uuid "{identifier}")
      (property "Reference" "{ref}" (at {rx} {ry} {angle}) {font})
      (property "Value" "{value}" (at {vx} {vy} {angle}) {font})
      (pin "1" (uuid "{uid()}")) (pin "2" (uuid "{uid()}"))
      (instances (project "hv_rdac_core" (path "/{root}" (reference "{ref}") (unit 1)))))''')
    if horizontal:
        wire(x-3.81,y,x-7.62,y); wire(x+3.81,y,x+7.62,y)
        label(a,x-7.62,y); label(b,x+7.62,y)
    else:
        wire(x,y-3.81,x,y-7.62); wire(x,y+3.81,x,y+7.62)
        label(a,x,y-7.62); label(b,x,y+7.62)
    components.append(dict(ref=ref,spice_ref=spice_ref,value=value,nodes=sorted([a,b])))


def note(text, x, y, size=1.5):
    parts.append(f'(text "{text}" (at {x} {y} 0) (effects (font (size {size} {size})) (justify left)) (uuid "{uid()}"))')


note('PASSIVE CORE / CODE-SWEEP BENCH',25,22,2)
note('R = 1 kohm; each arm Rout = 1 kohm; differential Rout = 2 kohm.',25,30)
note('D_A[3:0] = switched 0/5 V code; D_B[3:0] = complementary code. Bit 3 = MSB.',25,36)
for side, y in [('A',60), ('B',115)]:
    note(f'ARM {side}',25,y-15)
    for bit in range(4):
        x = 50+bit*48
        resistor(f'R{side}{bit}V','2k',x,y,f'{side}{bit}',f'D_{side}{bit}')
        if bit:
            resistor(f'R{side}{bit}H','1k',x-24,y-15,f'{side}{bit-1}',f'{side}{bit}',True)
            snap = lambda v: round(v/1.27)*1.27
            left, right, middle, top = snap(x-48), snap(x), snap(x-24), snap(y-15)
            wire(left,top,middle-7.62,top)
            wire(middle+7.62,top,right,top)
    for bit in range(4):
        x = round((50+bit*48)/1.27)*1.27
        top = round((y-15)/1.27)*1.27
        wire(x,top,x,round(y/1.27)*1.27-7.62)
        if bit in (1,2):
            parts.append(f'(junction (at {x} {top}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))')
    resistor(f'R{side}T','2k',242,y,f'{side}0','0')
resistor('RLOAD','2k',194,157,'A3','B3')
note('Load is 2 kohm for code verification (not winding DC resistance).',25,148)
note('Transformer test replaces RLOAD: Lp=10 H, Ls=40 mH, K=1, secondary=8 ohm.',25,175)
note('This sheet is the passive core, not a complete KiCad simulation or PCB design.',25,182)
note('Run the complete switch/transformer decks with: python sim/run_phase_a.py',25,189)
parts.append(')')
(HERE/'hv_rdac_core.kicad_sch').write_text('\n'.join(parts))
(HERE/'hv_rdac_core.kicad_pro').write_text(json.dumps({'meta':{'filename':'hv_rdac_core.kicad_pro','version':1}},indent=2))
(HERE/'expected_core.json').write_text(json.dumps(components,indent=2))
start = parts[0].index('(symbol "HV_RDAC:R"')
depth = 0
for end in range(start,len(parts[0])):
    depth += (parts[0][end] == '(') - (parts[0][end] == ')')
    if depth == 0:
        break
library_symbol = parts[0][start:end+1].replace('"HV_RDAC:R"','"R"',1)
(HERE/'HV_RDAC.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+library_symbol+'\n)')
(HERE/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "HV_RDAC") (type "KiCad") (uri "${KIPRJMOD}/HV_RDAC.kicad_sym") (options "") (descr "Local passive core symbols")))')
