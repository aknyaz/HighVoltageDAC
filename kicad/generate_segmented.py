"""Generate a wired 3+9 design-review hierarchy. Not a construction schematic."""
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
import json,csv,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calc'))
from partition_study import weights,R,K
OUT=ROOT/'kicad/segmented';OUT.mkdir(exist_ok=True)
PROJECT='hv_rdac_segmented'
def uid(s):return str(uuid5(NAMESPACE_URL,'hvrdac/3plus9/'+s))
def q(s):return json.dumps(str(s))
def mm(x):return f'{x*2.54:.4f}'
def ohms(value):return f'{value/1e6:.6g}M' if value>=1e6 else f'{value/1e3:.6g}k'
def fx(size=1,extra=''):return f'(effects (font (size {size} {size})) {extra})'
def line(points):return '(polyline (pts '+' '.join(f'(xy {mm(x)} {mm(y)})' for x,y in points)+') (stroke (width .254) (type default)) (fill (type none)))'
def rect(x1,y1,x2,y2):return line([(x1,y1),(x2,y1),(x2,y2),(x1,y2),(x1,y1)])
LIB={};PINS={};BOM=[];EXPECTED={}
def lib(name,prefix,drawing,pins):
    PINS[name]=pins
    pp=''
    for number,(label,x,y,angle) in pins.items():
        pp+=f'(pin passive line (at {mm(x)} {mm(-y)} {angle}) (length {mm(2)}) (name {q(label)} {fx(.9)}) (number {q(number)} {fx(.8)}))'
    LIB[name]=f'(symbol {q(name)} (pin_names (offset .5)) (in_bom yes) (on_board yes) (property "Reference" {q(prefix)} (at 0 0 0) {fx()}) (property "Value" {q(name)} (at 0 0 0) {fx()}) (symbol {q(name+"_0_1")} {drawing}) (symbol {q(name+"_1_1")} {pp}))'
lib('R','R',rect(-1,-.5,1,.5),{'1':('~',-3,0,0),'2':('~',3,0,180)})
lib('C','C',line([(-1,-.3),(1,-.3)])+line([(-1,.3),(1,.3)])+line([(0,1),(0,.3)])+line([(0,-1),(0,-.3)]),{'1':('~',0,-3,270),'2':('~',0,3,90)})
lib('MOS','Q',line([(-2,-2),(-2,2)])+line([(-1,-2),(-1,2)])+line([(-1,2),(0,2),(0,4)])+line([(-1,-2),(0,-2),(0,-4)])+line([(-4,0),(-2,0)])+line([(0,2),(1,2),(1,-2),(0,-2)]),{'1':('G',-4,0,0),'2':('D',0,-6,270),'3':('S',0,6,90)})
lp=[('15','VCC',-12),('10','IN+',-9),('11','IN-',-6),('14','RST/EN',-3),('9','GND',0),('12','RDY',3),('13','FLT',6),('16','APWM',9)]
rp=[('5','VDD',-12),('4','OUTH',-6),('6','OUTL',-3),('7','CLMPI',0),('3','COM',3),('1','AIN',6),('2','DESAT',9),('8','VEE',12)]
lib('Driver','U',rect(-8,-14,8,14),{**{n:(s,-10,y,0) for n,s,y in lp},**{n:(s,10,y,180) for n,s,y in rp}})
lib('Bias','X',rect(-7,-14,7,14),{'1':('+15',-9,-12,0),'2':('COM',-9,6,0),'3':('-4',-9,12,0)})
lib('Logic','X',rect(-7,-14,7,8),{str(i+1):(s,9,y,180) for i,(s,y) in enumerate([('3V3',-12),('CMD',-9),('EN',-3),('DGND',0),('RDY',3),('FLT',6)])})
lib('Port','J',rect(-2,-3,2,3),{'1':('+',4,-2,180),'2':('-',4,2,180)})
lib('Transformer','T',rect(-4,-5,4,5)+line([(0,-5),(0,5)]),{'1':('P+',-6,-3,0),'2':('P-',-6,3,0),'3':('S+',6,-3,180),'4':('S-',6,3,180)})
INPUTS=[f'PCM{i}' for i in range(12)]+['CLK50','RESET_N','RUN','ARM','CLEAR','VALID','RDY_ALL','FLT_N']
OUTPUTS=[]
for i in range(32):
    name=('A' if i<16 else 'B')+f'_{i%16:02d}'
    OUTPUTS.extend([(f'H{i}',f'CMD_{name}_H'),(f'L{i}',f'CMD_{name}_L')])
OUTPUTS.extend([('ENABLE','DRV_EN'),('BUSY','CTRL_BUSY'),('FAULT','CTRL_FAULT')])
lib('Controller','X',rect(-28,-40,28,40),{**{n:(n,-30,-38+4*i,0) for i,n in enumerate(INPUTS)},**{p:(p,30,-38+i,180) for i,(p,n) in enumerate(OUTPUTS)}})
lib('Stimulus','X',rect(-8,-40,8,40),{**{n:(n,10,-38+4*i,180) for i,n in enumerate(INPUTS[:18])},'BUSY':('BUSY',-10,34,0),'FAULT':('FAULT',-10,38,0)})

class Sheet:
    def __init__(self,name,title,path,paper='A3'):
        self.name=name;self.path=path;self.root=uid(name);self.items=[];self.i=0
        syms=''.join(s.replace('(symbol '+q(n),'(symbol '+q('HV3:'+n),1) for n,s in LIB.items())
        self.items=[f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{self.root}") (paper "{paper}") (title_block (title {q(title)}) (rev "S1-review") (comment 1 "5 V review bench; candidate parts; NOT a released HV construction design")) (lib_symbols {syms})']
    def id(self):self.i+=1;return uid(self.name+str(self.i))
    def wire(self,x,y,a,b):
        if (x,y)==(a,b):return
        assert x==a or y==b
        self.items.append(f'(wire (pts (xy {mm(x)} {mm(y)}) (xy {mm(a)} {mm(b)})) (stroke (width 0) (type default)) (uuid "{self.id()}"))')
    def dot(self,x,y):self.items.append(f'(junction (at {mm(x)} {mm(y)}) (diameter 0) (color 0 0 0 0) (uuid "{self.id()}"))')
    def text(self,s,x,y,size=1.2):self.items.append(f'(text {q(s)} (at {mm(x)} {mm(y)} 0) {fx(size,"(justify left)")} (uuid "{self.id()}"))')
    def label(self,s,x,y,hier=False):
        typ='hierarchical_label' if hier else 'label';shape='(shape passive)' if hier else ''
        self.items.append(f'({typ} {q(s)} {shape} (at {mm(x)} {mm(y)} 0) {fx(1,"(justify left)")} (uuid "{self.id()}"))')
    def glob(self,s,x,y):
        self.items.append(f'(global_label {q(s)} (shape passive) (at {mm(x)} {mm(y)} 0) {fx(.85,"(justify left)")} (uuid "{self.id()}"))')
    def nc(self,x,y):self.items.append(f'(no_connect (at {mm(x)} {mm(y)}) (uuid "{self.id()}"))')
    def part(self,kind,ref,value,x,y,nets,mpn='TBD',status='UNSELECTED',footprint=''):
        if kind=='R' and value.startswith('10R'):
            mpn='RC0603FR-0710RL';status='CANDIDATE_PULSE_CHECK_PENDING';footprint='Resistor_SMD:R_0603_1608Metric'
        if kind=='R' and value.startswith('10k'):
            mpn='RC0603FR-0710KL';status='CANDIDATE';footprint='Resistor_SMD:R_0603_1608Metric'
        if kind=='C' and value.startswith('22u'):
            mpn='GRM32ER71E226KE15L';status='CANDIDATE_DC_BIAS_CHECK_PENDING';footprint='Capacitor_SMD:C_1210_3225Metric'
            value='22u 25V / candidate'
        props=''
        for key,val,dy in [('Reference',ref,-16 if kind in ('Driver','Bias','Logic') else -3),('Value',value,-14.5 if kind in ('Driver','Bias','Logic') else -1.5)]:
            py=y+dy
            if kind=='MOS':py=y+(-17 if key=='Reference' else -15.5)
            if kind in ('Controller','Stimulus'):py=y+(-43 if key=='Reference' else -41.5)
            props+=f'(property {q(key)} {q(val)} (at {mm(x)} {mm(py)} 0) {fx(.9)})'
        for key,val in [('MPN',mpn),('Selection',status),('Footprint',footprint)]:props+=f'(property {q(key)} {q(val)} (at {mm(x)} {mm(y)} 0) {fx(1,"(hide yes)")})'
        pins=''.join(f'(pin {q(n)} (uuid "{self.id()}"))' for n in PINS[kind])
        self.items.append(f'(symbol (lib_id "HV3:{kind}") (at {mm(x)} {mm(y)} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}") {props} {pins} (instances (project "{PROJECT}" (path "{self.path}" (reference {q(ref)}) (unit 1)))))')
        EXPECTED[ref]={str(k):str(v) for k,v in nets.items() if v is not None}
        BOM.append(dict(reference=ref,value=value,MPN=mpn,status=status,sheet=self.name,footprint=footprint))
    def save(self):
        if self.name==PROJECT:self.items.append(f'(sheet_instances (path "/" (page "1")))')
        (OUT/(self.name+'.kicad_sch')).write_text('\n'.join(self.items)+ '\n)',encoding='utf-8')

LIB['Logic']=LIB['Logic'].replace(rect(-7,-14,7,8),rect(-7,-14,7,14))
LIB['MOS']=LIB['MOS'].replace(line([(0,2),(1,2),(1,-2),(0,-2)]),line([(0,2),(1.5,2),(1.5,.5)])+line([(1,.5),(2,.5)])+line([(1,-.5),(2,-.5),(1.5,.5),(1,-.5)])+line([(1.5,-.5),(1.5,-2),(0,-2)]))
rootid=uid(PROJECT)
root=Sheet(PROJECT,'3+9 DAC / complete branch hierarchy',f'/{rootid}',paper='A2')
root.text('3+9 SEGMENTED DAC / 32 HALF-BRIDGES / 64 SiC FETs',10,9,2.4)
root.text('Open any branch sheet: all transistor, driver, gate and bias connections are drawn there.',10,15,1.5)
root.text('Bench interface = 5 V. Control = tested HDL; FPGA physical implementation pending. Bias remains an ideal interface.',10,20)
root.text('Candidate Q: C3M0350120D | candidate U: UCC21750DWR | precision resistor assemblies and transformer MPN: TBD.',10,25)

for index in range(32):
    arm='A' if index<16 else 'B';j=index%16;weight=int(weights(3)[j]);base=index*20
    name=f'{arm}_{j:02d}';sheetid=uid('sheet/'+name);path=f'/{rootid}/{sheetid}'
    s=Sheet(name,f'Arm {arm} / '+(f'fine bit {j}' if j<9 else f'coarse cell {j-9}')+f' / weight {weight}',path)
    s.text(f'ARM {arm} / '+(f'FINE BIT {j}' if j<9 else f'COARSE CELL {j-9}')+f' / WEIGHT {weight}',8,8,2)
    s.text('Candidate parts for review. Commands come from control.kicad_sch / tested HDL. Bias converters remain unselected.',8,13,1.1)
    s.text('DESAT is disabled in this review bench (tied to COM). Physical protection and driver timing remain unqualified.',8,17,1.1)
    # Two explicit driver + FET channels. All gate paths use visible wires.
    for half,y in enumerate((36,78)):
        n=2*index+half+1;local=f'{name}_{half}';com=f'{name}_SW' if half==0 else 'PGND'
        gate=local+'_G';vh=local+'_15';vl=local+'_M4';dg='DGND';vcc='VCC3V3'
        cmd=f'CMD_{name}_'+('H' if half==0 else 'L');en='DRV_EN';rdy='RDY_ALL';flt='FLT_N'
        s.part('Driver',f'U{n}','UCC21750DWR',60,y,{'1':com,'2':com,'3':com,'4':local+'_ON','5':vh,'6':local+'_OFF','7':gate,'8':vl,'9':dg,'10':cmd,'11':dg,'12':rdy,'13':flt,'14':en,'15':vcc,'16':None},'UCC21750DWR','CANDIDATE','Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm')
        s.part('MOS',f'Q{n}','C3M0350120D',110,y,{'1':gate,'2':'VREF' if half==0 else f'{name}_SW','3':com},'C3M0350120D','CANDIDATE','Package_TO_SOT_THT:TO-247-3_Vertical')
        for net,dy in ((vcc,-12),(cmd,-9),(en,-3),(dg,0),(rdy,3),(flt,6)):
            s.wire(34,y+dy,50,y+dy);s.glob(net,34,y+dy)
        s.text(f'Controller H[{index}]' if half==0 else f'Controller L[{index}]',16,y-16,1.1)
        s.wire(50,y-6,46,y-6);s.wire(46,y-6,46,y);s.dot(46,y)
        s.nc(50,y+9)
        s.part('Bias',f'X{base+half*3+2}','ISOLATED BIAS / TBD',139,y,{'1':vh,'2':com,'3':vl},'NONE - ideal +15/-4 V','MODEL_INTERFACE')
        s.wire(70,y-12,130,y-12);s.wire(70,y+12,130,y+12)
        for off,dy in ((1,-6),(2,-3)):
            ref=f'R{base+half*5+off}'
            s.part('R',ref,'10R / provisional',82,y+dy,{'1':local+('_ON' if off==1 else '_OFF'),'2':gate})
            s.wire(70,y+dy,79,y+dy);s.wire(85,y+dy,100,y+dy)
        s.wire(100,y-6,100,y-3);s.wire(100,y-3,100,y);s.dot(100,y-3)
        s.wire(70,y,100,y);s.wire(100,y,106,y);s.dot(100,y)
        s.wire(70,y+3,95,y+3);s.wire(95,y+3,95,y+6);s.wire(95,y+6,110,y+6);s.wire(110,y+6,130,y+6);s.dot(110,y+6)
        for dy,x in ((6,90),(9,92)):
            s.wire(70,y+dy,x,y+dy);s.wire(x,y+dy,x,y+3);s.dot(x,y+3)
        # Local bypasses, each visibly returned to the relevant source/COM.
        s.part('C',f'C{base+half*4+1}','22u / rating TBD',120,y-3,{'1':vh,'2':com})
        s.wire(120,y-12,120,y-6);s.dot(120,y-12);s.wire(120,y,120,y+6);s.dot(120,y+6)
        s.part('C',f'C{base+half*4+2}','22u / rating TBD',125,y+9,{'1':com,'2':vl});s.dot(125,y+6);s.dot(125,y+12)
        # Input bypass at left of logic wiring, connected by local rail names.
        s.part('C',f'C{base+half*4+3}','2.2u / rating TBD',12,y,{'1':vcc,'2':dg})
        s.wire(12,y-3,12,y-5);s.glob(vcc,12,y-5)
        s.wire(12,y+3,12,y+5);s.glob(dg,12,y+5)
        # Gate-source bleed on an explicit separate route.
        s.part('R',f'R{base+half*5+3}','10k / provisional',102,y+9,{'1':gate,'2':com})
        s.wire(99,y+9,98,y+9);s.wire(98,y+9,98,y);s.dot(98,y)
        s.wire(105,y+9,108,y+9);s.wire(108,y+9,108,y+6);s.dot(108,y+6)
    s.wire(110,30,110,22);s.label('VREF',110,22,True)
    s.wire(110,42,110,57);s.wire(110,57,110,72);s.dot(110,57)
    s.part('R',f'R{base+15}',ohms(K*R/weight),130,57,{'1':f'{name}_SW','2':arm+'OUT'},'TBD precision HV assembly','UNSELECTED_0.01pct_TARGET')
    s.wire(110,57,127,57);s.wire(133,57,152,57);s.label('OUT',152,57,True)
    s.wire(110,84,110,97);s.label('PGND',110,97,True)
    s.text('Timing: independent H/L commands with non-overlap; upper COM follows SW, lower COM follows PGND.',8,101,1.1)
    s.text(f'Code: '+('D' if arm=='A' else '4095-D')+f'; select bit {j}' if j<9 else f'Coarse cell {j-9}: ON when floor(code/512) > {j-9}',8,105,1.1)
    s.text('10R: RC0603FR-0710RL | 10k: RC0603FR-0710KL | 22u: GRM32ER71E226KE15L',8,108,.95)
    s.save()
    # Overview: four rows, eight branch sheets, visible shared rails per row.
    row=index//8;col=index%8;x=12+col*27;y=40+row*41
    root.items.append(f'(sheet (at {mm(x)} {mm(y)}) (size {mm(22)} {mm(19)}) (stroke (width .254) (type default)) (fill (color 0 0 0 0)) (uuid "{sheetid}") (property "Sheetname" {q(name+" w="+str(weight))} (at {mm(x)} {mm(y-1)} 0) {fx(1,"(justify left)")}) (property "Sheetfile" {q(name+".kicad_sch")} (at {mm(x)} {mm(y+20)} 0) {fx(.8,"(justify left)")}) (pin "VREF" passive (at {mm(x+4)} {mm(y)} 270) {fx(.9)} (uuid "{uid(name+"v")}")) (pin "PGND" passive (at {mm(x+10)} {mm(y)} 270) {fx(.9)} (uuid "{uid(name+"g")}")) (pin "OUT" passive (at {mm(x+16)} {mm(y+19)} 90) {fx(.9)} (uuid "{uid(name+"o")}")) (instances (project "{PROJECT}" (path "/{rootid}" (page "{index+2}")))))')
    root.items[-1]=root.items[-1].replace(f'{mm(y)} 270)',f'{mm(y)} 90)').replace(f'{mm(y+19)} 90)',f'{mm(y+19)} 270)')
    root.text('2 x SiC FET\n2 x isolated driver\nR = '+ohms(K*R/weight),x+2,y+9,1.2)
    root.wire(x+4,y,x+4,y-5);root.dot(x+4,y-5)
    root.wire(x+10,y,x+10,y-8);root.dot(x+10,y-8)
    root.wire(x+16,y+19,x+16,y+25);root.dot(x+16,y+25)
    if col==0:
        root.label('VREF',x+4,y-5);root.label('PGND',x+10,y-8);root.label(arm+'OUT',x+16,y+25)
    else:
        root.wire(x-23,y-5,x+4,y-5);root.wire(x-17,y-8,x+10,y-8);root.wire(x-11,y+25,x+16,y+25)

root.text('HOW TO READ THIS PROJECT',240,40,1.8)
root.text('A_00 ... A_08: fine bits 0 ... 8\nA_09 ... A_15: seven coarse cells\nB sheets: same network, code 4095-D\n\nEvery box opens a full branch sheet.\nVREF and PGND feed both switches.\nOUT is the weighted resistor terminal.\n\nUpper driver COM follows the switch node.\nLower driver COM follows PGND.\n\nCandidate part numbers are shown\non branch sheets and in bom.csv.\nTBD means not selected for hardware.\n\nCONTROL sheet maps tested HDL\nto all 64 gate commands.\nFPGA package wiring and isolated\nbias converters remain unfinished.',240,83,1.5)
root.text('OUTPUT AND BENCH INTERFACES / component selection pending',10,204,1.6)
ctl_id=uid('sheet/control')
root.items.append(f'(sheet (at {mm(240)} {mm(145)}) (size {mm(70)} {mm(35)}) (stroke (width .254) (type default)) (fill (color 0 0 0 0)) (uuid "{ctl_id}") (property "Sheetname" "CONTROL - tested HDL" (at {mm(240)} {mm(144)} 0) {fx(1.5,"(justify left)")}) (property "Sheetfile" "control.kicad_sch" (at {mm(240)} {mm(181)} 0) {fx(1,"(justify left)")}) (instances (project "{PROJECT}" (path "/{rootid}" (page "34")))))')
root.text('50 MHz / 200 ns command dead time\n64 commands + shared EN / RDY / FLT\nLogical HDL ports; FPGA pinout pending',244,162,1.5)
ctl=Sheet('control','3+9 digital controller / tested RTL interface',f'/{rootid}/{ctl_id}')
ctl.text('CONTROL IMPLEMENTATION / 64 COMMAND OUTPUTS',8,7,2)
ctl.text('Logical port names, NOT physical FPGA pin numbers. Candidate: LCMXO2-2000HC-4TG144C; package implementation pending.',8,12,1.1)
ctl.part('Controller','X900','rdac_control / generated Verilog',90,58,{**{n:n for n in INPUTS},**{p:n for p,n in OUTPUTS}},'NONE - synthesizable HDL','RTL_TESTED_NOT_ROUTED')
ctl.part('Stimulus','X901','Synchronous PCM host / test input',22,58,{**{n:n for n in INPUTS[:18]},'BUSY':'CTRL_BUSY','FAULT':'CTRL_FAULT'},'NONE - test interface','MODEL_INTERFACE')
for i,n in enumerate(('CTRL_BUSY','CTRL_FAULT')):
    ctl.wire(8,92+4*i,12,92+4*i);ctl.glob(n,8,92+4*i)
for i,n in enumerate(INPUTS[:18]):ctl.wire(32,20+4*i,60,20+4*i)
for i,n in enumerate(INPUTS[18:],18):
    ctl.wire(48,20+4*i,60,20+4*i);ctl.glob(n,48,20+4*i)
for i,(p,n) in enumerate(OUTPUTS):
    y=20+i;ctl.wire(120,y,128,y);ctl.glob(n,128,y)
for i,n in enumerate(('RDY_ALL','FLT_N')):
    x=76+30*i
    ctl.part('R',f'R{900+i}','4.7k / provisional',x,102,{'1':'VCC3V3','2':n})
    ctl.wire(x-3,102,x-7,102);ctl.glob('VCC3V3',x-7,102)
    ctl.wire(x+3,102,x+7,102);ctl.glob(n,x+7,102)
ctl.part('Port','J3','3.3 V logic bias',18,102,{'1':'VCC3V3','2':'DGND'},'NONE - bench port','MODEL_INTERFACE')
ctl.wire(22,100,29,100);ctl.glob('VCC3V3',29,100);ctl.wire(22,104,29,104);ctl.glob('DGND',29,104)
ctl.text('RDY/FLT: open-drain aggregation; fan-in, leakage and rise-time qualification pending. CDC/clock-failure wrapper pending.',8,110,1)
ctl.save()
for row in range(4):
    y=40+row*41
    root.wire(6,y-5,16,y-5);root.dot(16,y-5)
    root.wire(8,y-8,22,y-8);root.dot(22,y-8)
    if row:
        root.wire(6,y-46,6,y-5);root.dot(6,y-46)
        root.wire(8,y-49,8,y-8);root.dot(8,y-49)
for y in (65,147):
    root.wire(217,y,225,y);root.dot(217,y)
    root.wire(225,y,225,y+41);root.wire(217,y+41,225,y+41);root.dot(217,y+41)
root.part('Port','J1','5 V bench input',16,215,{'1':'VREF','2':'PGND'},'NONE - bench port','MODEL_INTERFACE')
root.wire(20,213,28,213);root.label('VREF',28,213);root.wire(20,217,28,217);root.label('PGND',28,217)
for arm,x in (('A',50),('B',90)):
    root.part('R',f'R{700 if arm=="A" else 701}',ohms(K*R),x,215,{'1':arm+'OUT','2':'PGND'},'TBD precision HV assembly','UNSELECTED_0.01pct_TARGET')
    root.wire(x-3,215,x-7,215);root.label(arm+'OUT',x-7,215);root.wire(x+3,215,x+7,215);root.label('PGND',x+7,215)
root.part('Transformer','T1','10k:8 / model only',135,216,{'1':'AOUT','2':'BOUT','3':'SPK+','4':'SPK-'},'TBD','MODEL_UNVALIDATED')
root.wire(129,213,118,213);root.label('AOUT',118,213);root.wire(129,219,118,219);root.label('BOUT',118,219)
root.part('Port','J2','8 ohm load interface',156,216,{'1':'SPK+','2':'SPK-'},'NONE - bench port','MODEL_INTERFACE')
root.wire(141,213,165,213);root.wire(165,213,165,214);root.wire(165,214,160,214)
root.wire(141,219,165,219);root.wire(165,219,165,218);root.wire(165,218,160,218)
# A2 height is 165 units; extend root to A1 to accommodate readable overview/output.
root.items[0]=root.items[0].replace('(paper "A2")','(paper "A1")')
root.text('Physical FPGA wiring, isolated bias, transformer, HV resistor assembly and hardware protection remain unfinished. See BOM status.',10,226,1.2)
root.save()
(OUT/(PROJECT+'.kicad_pro')).write_text(json.dumps({'meta':{'filename':PROJECT+'.kicad_pro','version':1}},indent=2))
(OUT/'HV3.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(LIB.values())+'\n)')
(OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "HV3") (type "KiCad") (uri "${KIPRJMOD}/HV3.kicad_sym") (options "") (descr "Design review symbols with verified candidate pin numbers")))')
(OUT/'expected_connections.json').write_text(json.dumps(EXPECTED,indent=2))
with (OUT/'bom.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=BOM[0].keys());w.writeheader();w.writerows(BOM)
print('Generated',len(BOM),'components across 34 sheets:',OUT)
