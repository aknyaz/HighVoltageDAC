"""Generate the complete wired 4-bit simulation sheet and local SPICE models.

Coordinates in this generator are multiples of 2.54 mm. Existing passive-core
files remain untouched. Re-running replaces the generated full/ project.
"""
from pathlib import Path
import json
import sys
from uuid import uuid5, NAMESPACE_URL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'sim'))
from run_phase_a import circuit, np

OUT = ROOT/'kicad/full'
OUT.mkdir(exist_ok=True)
PROJECT = 'hv_rdac_full'
counter = 0


def uid(key=None):
    global counter
    counter += 1
    return str(uuid5(NAMESPACE_URL, f'hvrdac/full/{key or counter}'))


def mm(v):
    return f'{v*2.54:.4f}'


def q(value):
    return json.dumps(str(value), ensure_ascii=False)


def effects(size=1.0, extra=''):
    return f'(effects (font (size {size} {size})) {extra})'


def line(points, width=0.254):
    return '(polyline (pts '+' '.join(f'(xy {mm(x)} {mm(y)})' for x,y in points)+f') (stroke (width {width}) (type default)) (fill (type none)))'


def pin(number, name, x, y, angle, length=2):
    return f'(pin passive line (at {mm(x)} {mm(y)} {angle}) (length {mm(length)}) (name {q(name)} {effects()}) (number "{number}" {effects()}))'


def circle(x,y,r):
    return f'(circle (center {mm(x)} {mm(y)}) (radius {mm(r)}) (stroke (width 0.254) (type default)) (fill (type none)))'


def symbol(name, prefix, drawing, pins):
    return f'''(symbol "{name}" (pin_numbers hide) (pin_names (offset 0) hide)
    (in_bom yes) (on_board yes)
    (property "Reference" "{prefix}" (at 0 0 0) {effects()})
    (property "Value" "{name}" (at 0 0 0) {effects()})
    (symbol "{name}_0_1" {drawing}) (symbol "{name}_1_1" {pins}))'''


symbols = {}
symbols['R'] = symbol('R','R',line([(-.5,-1),(.5,-1),(.5,1),(-.5,1),(-.5,-1)]),
                       pin(1,'~',0,3,270)+pin(2,'~',0,-3,90))
symbols['V'] = symbol('V','V',circle(0,0,2)+line([(-.6,1),(.6,1)])+line([(0,.4),(0,1.6)])+line([(-.6,-1),(.6,-1)]),
                       pin(1,'+',0,3,270,1)+pin(2,'-',0,-3,90,1))
symbols['PCM'] = symbol('PCM','U',circle(0,0,2)+line([(-1.3,-.5),(-.5,-.5),(-.5,.6),(.5,.6),(.5,-.5),(1.3,-.5)]),
                         pin(1,'OUT',0,3,270,1)+pin(2,'RET',0,-3,90,1))
# SPDT: top common, left HIGH, right LOW, bottom logic control.
symbols['SPDT'] = symbol('SPDT','U',line([(0,2),(0,.5),(-1.8,-.2)])+circle(-2,0,.18)+circle(2,0,.18)+
                         line([(0,-2),(0,-1)],.15),
                         pin(1,'HI',-4,0,0)+pin(2,'LO',4,0,180)+pin(3,'OUT',0,4,270)+pin(4,'CTRL',0,-4,90))
coil = ''
for x in (-3,3):
    for y in (-3,-1,1,3):
        coil += f'(arc (start {mm(x)} {mm(y-1)}) (mid {mm(x+(1 if x<0 else -1))} {mm(y)}) (end {mm(x)} {mm(y+1)}) (stroke (width .254) (type default)) (fill (type none)))'
    coil += line([(x,5),(x,4)])+line([(x,-4),(x,-5)])
coil += line([(-1,-4),(-1,4)])+line([(1,-4),(1,4)])+circle(-4,3.8,.25)+circle(4,3.8,.25)
coil += line([(-6,5),(-3,5)])+line([(-6,-5),(-3,-5)])+line([(3,5),(6,5)])+line([(3,-5),(6,-5)])
symbols['Transformer'] = symbol('Transformer','T',coil,
    pin(1,'P+',-8,5,0)+pin(2,'P-',-8,-5,0)+pin(3,'S+',8,5,180)+pin(4,'S-',8,-5,180))
symbols['GND'] = symbol('GND','#PWR',line([(0,0),(0,-1),(-1,-1),(1,-1)])+
                        line([(-.6,-1.5),(.6,-1.5)])+line([(-.2,-2),(.2,-2)]),
                        pin(1,'GND',0,0,90,0)).replace('(symbol "GND"','(symbol "GND" (power)',1).replace('(pin passive','(pin power_in')
symbols['V'] = symbols['V'].replace('(pin passive','(pin power_out')

root_uid = uid('root')
parts = [f'''(kicad_sch (version 20250114) (generator "eeschema")
 (uuid "{root_uid}") (paper "A3")
 (title_block (title "HV-RDAC | complete 4-bit simulation bench") (rev "A1")
 (comment 1 "5 V model only | 1 kHz PCM at 192 kS/s | idealized switches and transformer"))
 (lib_symbols {''.join(s.replace('(symbol '+q(n), '(symbol '+q('HV_RDAC_Full:'+n),1) for n,s in symbols.items())})''']
expected = {}


def wire(x1,y1,x2,y2):
    if (x1,y1)==(x2,y2):
        return
    assert x1==x2 or y1==y2
    parts.append(f'(wire (pts (xy {mm(x1)} {mm(y1)}) (xy {mm(x2)} {mm(y2)})) (stroke (width 0) (type default)) (uuid "{uid()}"))')


def junction(x,y):
    parts.append(f'(junction (at {mm(x)} {mm(y)}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))')


def label(name,x,y):
    parts.append(f'(label {q(name)} (at {mm(x)} {mm(y)} 0) {effects()} (uuid "{uid()}"))')


def note(text,x,y,size=1.3):
    parts.append(f'(text {q(text)} (at {mm(x)} {mm(y)} 0) {effects(size,"(justify left)")} (uuid "{uid()}"))')


def component(kind,ref,value,x,y,nodes,angle=0,model=None,params=None):
    expected[ref] = nodes
    if angle:
        positions = [(x,y-2.5),(x,y+2.5)]
    elif kind == 'Transformer':
        positions = [(x,y-8),(x,y+8)]
    elif kind == 'SPDT':
        positions = [(x+4,y-2.5),(x+5,y+2.5)]
    else:
        positions = [(x+4,y-.8),(x+4,y+1)]
    props = []
    for (key,val),(px,py) in zip([('Reference',ref),('Value',value)],positions):
        props.append(f'(property {q(key)} {q(val)} (at {mm(px)} {mm(py)} {angle}) {effects()})')
    sim = {}
    if model:
        sim = {'Sim.Device':'SUBCKT','Sim.Library':'hv_rdac_models.lib','Sim.Name':model,
               'Sim.Pins':' '.join(f'{i}={i}' for i in range(1,len(nodes)+1))}
    elif kind == 'V':
        sim = {'Sim.Device':'V','Sim.Type':'DC','Sim.Params':params or 'dc=5','Sim.Pins':'1=+ 2=-'}
    for key,val in sim.items():
        props.append(f'(property {q(key)} {q(val)} (at {mm(x)} {mm(y)} 0) {effects(1,"(hide yes)")})')
    parts.append(f'''(symbol (lib_id "HV_RDAC_Full:{kind}") (at {mm(x)} {mm(y)} {angle}) (unit 1)
    (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}") {''.join(props)}
    {''.join(f'(pin "{i}" (uuid "{uid()}"))' for i in range(1,len(nodes)+1))}
    (instances (project "{PROJECT}" (path "/{root_uid}" (reference "{ref}") (unit 1)))))''')


note('4-BIT RESISTIVE DAC / DIFFERENTIAL TRANSFORMER DRIVE',8,8,2.3)
note('Follow the wires: PCM bit sources -> ideal SPDT switches -> R-2R ladders -> transformer -> 8 ohm load.',8,13)
note('Both arms share the same 5 V reference and return. Dots indicate connections; crossings without dots are not connected.',8,17)

xs = [38,60,82,104]
for side, base, roffset, uoffset in [('A',0,0,0),('B',44,8,8)]:
    rail, sy, cy, ground, refy = [v+base for v in (24,38,50,57,44)]
    note(f'ARM {side} / '+('CODE D' if side=='A' else 'CODE 15 - D'),8 if side=='A' else 28,20 if side=='A' else 60,1.6)
    # Termination is visibly connected to the LSB end and the common return.
    component('R',f'R{roffset+8}','2k',26,rail+7,{1:f'{side}0',2:'0'})
    wire(26,rail,38,rail); wire(26,rail,26,rail+4); wire(26,rail+10,26,ground)
    for bit,x in enumerate(xs):
        node=f'{side}{bit}'
        note(f'BIT {bit}'+(' / LSB' if bit==0 else ' / MSB' if bit==3 else ''),x-4,rail-4,1.2)
        component('R',f'R{roffset+bit+1}','2k',x,rail+7,{1:node,2:f'D{side}{bit}'})
        wire(x,rail,x,rail+4); wire(x,rail+10,x,sy-4)
        label(node,x,rail)
        if bit:
            mid=(xs[bit-1]+x)/2
            component('R',f'R{roffset+4+bit}','1k',mid,rail,{1:f'{side}{bit-1}',2:node},90)
            wire(xs[bit-1],rail,mid-3,rail); wire(mid+3,rail,x,rail)
        if bit<3:
            junction(x,rail)
        component('SPDT',f'U{uoffset+bit+1}','SPDT',x,sy,{1:'VREF',2:'0',3:f'D{side}{bit}',4:f'C{side}{bit}'},model='RDAC_SPDT')
        wire(x-4,sy,x-6,sy); wire(x-6,sy,x-6,refy); junction(x-6,refy)
        wire(x+4,sy,x+8,sy); wire(x+8,sy,x+8,ground); junction(x+8,ground)
        component('PCM',f'U{uoffset+bit+5}',f'PCM {side}{bit}',x,cy,{1:f'C{side}{bit}',2:'0'},model=f'PCM_{side}{bit}')
        wire(x,sy+4,x,cy-3); wire(x,cy+3,x,ground); junction(x,ground)
        label(f'C{side}{bit}',x,cy-4)
    # Segment shared rails at every actual connection, leaving crossovers unjoined.
    refxs=[16]+[x-6 for x in xs]
    for left,right in zip(refxs,refxs[1:]):
        wire(left,refy,right,refy)
    gxs=[20,26]+sorted([x for x in xs]+[x+8 for x in xs])
    for left,right in zip(gxs,gxs[1:]):
        wire(left,ground,right,ground)
    junction(26,ground)

# Single reference source and a visibly shared return between arms.
component('V','V1','5 V',12,50,{1:'VREF',2:'0'})
wire(12,47,12,44); wire(12,44,16,44); junction(16,44)
wire(16,44,16,88)
wire(12,53,12,57); wire(12,57,20,57); junction(20,57)
wire(20,57,20,101)
label('VREF',16,44)
wire(20,101,20,103); junction(20,101)
component('GND','#PWR01','GND',20,103,{1:'0'})

# Transformer and the entire secondary loop are wired explicitly.
component('Transformer','T1','10 H : 40 mH',136,56,{1:'A3',2:'B3',3:'SEC',4:'0'},model='RDAC_TRANSFORMER')
wire(104,24,120,24); wire(120,24,120,51); wire(120,51,128,51)
wire(104,68,120,68); wire(120,68,120,61); wire(120,61,128,61)
component('R','R17','8',150,56,{1:'SEC',2:'0'})
wire(144,51,150,51); wire(150,51,150,53)
wire(144,61,150,61); wire(150,59,150,61)
wire(150,61,154,61); junction(150,61); wire(154,61,154,74)
wire(154,74,114,74); wire(114,74,114,101); wire(112,101,114,101)
label('SEC',150,51)
note('K = 1; n = sqrt(250)',125,68,1.2)
note('Reflected load = 2 kohm',125,71,1.2)
note('OUTPUT / 8 ohm',143,45,1.3)
note('TRANSIENT SETUP',124,79,1.6)
note('.tran 200n 100m 0 200n\n.options reltol=1e-6 abstol=1e-12',124,84,1.2)
note('PCM: 1 kHz sine, 90% FS\n192 kS/s, 4 bits, 1 ns edges\nEvaluate settled output at 92-100 ms.',124,92,1.2)
note('SPDT: CTRL=1 selects 5 V; CTRL=0 selects return. Model contains two complementary idealized switches.',8,106,1.2)
note('No analog amplifier. Transformer model is linear: finite magnetizing inductance, no winding losses or saturation.',8,109,1.2)
parts.append(')')
(OUT/f'{PROJECT}.kicad_sch').write_text('\n'.join(parts),encoding='utf-8')
(OUT/f'{PROJECT}.kicad_pro').write_text(json.dumps({'meta':{'filename':f'{PROJECT}.kicad_pro','version':1}},indent=2))
(OUT/'HV_RDAC_Full.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(symbols.values())+'\n)')
(OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "HV_RDAC_Full") (type "KiCad") (uri "${KIPRJMOD}/HV_RDAC_Full.kicad_sym") (options "") (descr "Simulation bench symbols")))')
(OUT/'expected_connections.json').write_text(json.dumps(expected,indent=2))

# Reuse the original validated PCM generator, rather than approximate it with analog sine sources.
half=np.floor(7.5+7.5*.9*np.sin(2*np.pi*(np.arange(96)+.5)/192)+.5).astype(int)
deck,_=circuit(np.tile(np.concatenate((half,15-half)),100),transformer=True)
model=['* HV-RDAC simulation-only models; same idealized devices as Phase A.',
       '.subckt RDAC_SPDT HI LO OUT CTRL',
       '.model ideal SW(Ron=1u Roff=1e12 Vt=0.5 Vh=0)',
       'Binv inv LO V=1-v(CTRL,LO)',
       'Shi OUT HI CTRL LO ideal', 'Slo OUT LO inv LO ideal', '.ends RDAC_SPDT',
       '.subckt RDAC_TRANSFORMER PPLUS PMINUS SPLUS SMINUS',
       'Lp PPLUS PMINUS 10', 'Ls SPLUS SMINUS 0.04', 'K1 Lp Ls 1', '.ends RDAC_TRANSFORMER']
for side in ('A','B'):
    for bit in range(4):
        source=next(l for l in deck.splitlines() if l.startswith(f'V{side.lower()}{bit} '))
        pwl=source[source.index('PWL('):]
        # Short continuation lines keep the library easy for SPICE parsers to handle.
        pairs=pwl[4:-1].split()
        model += [f'.subckt PCM_{side}{bit} OUT RET', 'Vbit OUT RET PWL(']
        model += ['+ '+' '.join(pairs[i:i+12]) for i in range(0,len(pairs),12)]
        model += ['+ )', f'.ends PCM_{side}{bit}']
(OUT/'hv_rdac_models.lib').write_text('\n'.join(model)+'\n')
print('Generated',OUT/f'{PROJECT}.kicad_pro')
