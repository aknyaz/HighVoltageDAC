"""Purchasable single-value array candidate; analysis and envelope model only.

Run: python calc/resistor_array_design.py
The baseline schematic is deliberately not changed by this candidate study.
"""
from pathlib import Path
import sys, json, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sim'))
from ngspice_shared import NgSpice
OUT=ROOT/'results/resistor_array'; OUT.mkdir(parents=True,exist_ok=True)
GEN=ROOT/'sim/generated/resistor_array'; GEN.mkdir(parents=True,exist_ok=True)
MODEL=ROOT/'output/resistor_array'; MODEL.mkdir(parents=True,exist_ok=True)
UNIT=169000.
OLD_ARM=5274.699627701833
MPN='ERA-8AEB1693V'
# weight, assembly count, resistors in series per string, parallel strings
CONFIG=[(512,14,6,24),(256,2,6,12),(128,2,6,6),(64,2,6,3),
        (32,2,8,2),(16,2,8,1),(8,2,16,1),(4,2,32,1),
        (2,2,64,1),(1,4,128,1)]
ROWS=[]
for w,q,s,p in CONFIG:
    r=UNIT*s/p
    # One high resistor against all remaining low resistors in its string.
    tol=.001
    imax=700/(s*UNIT*(1-tol))
    vmax=700*(1+tol)/((1+tol)+(s-1)*(1-tol))
    pmax=(700/((1+tol)+(s-1)*(1-tol)))**2*(1+tol)/UNIT
    assert vmax<150 and pmax<.25
    ROWS.append(dict(weight=w,quantity=q,series=s,parallel=p,parts_per_assembly=s*p,
                     total_parts=q*s*p,resistance_ohm=r,old_resistance_ohm=4096*OLD_ARM/w,
                     nominal_voltage_650_v=650/s,nominal_power_650_w=(650/s)**2/UNIT,
                     worst_voltage_700_v=vmax,worst_power_700_w=pmax,worst_current_700_a=imax))
BY_WEIGHT={r['weight']:r for r in ROWS}
ARM_R=ROWS[0]['resistance_ohm']/8
TOTAL=sum(r['total_parts'] for r in ROWS)
assert TOTAL==3052
assert all(abs(r['resistance_ohm']*r['weight']-4096*ARM_R)<1e-8 for r in ROWS)

def assemblies():
    for arm in ['a','b']:
        for j in range(7): yield arm,f'c{j}',512
        for j in range(9): yield arm,f'f{j}',2**j
        yield arm,'term',1

def deck(mode='dc',stray_pf=0):
    lines=['169 kohm single-MPN candidate, 5 V simulation only',
           '.options reltol=1e-8 abstol=1e-14','Vcode code 0 0']
    count=0
    for arm,name,w in assemblies():
        row=BY_WEIGHT[w];s,p=row['series'],row['parallel'];tag=arm+name
        source=tag+'in'
        if name=='term': source='0'
        elif mode=='dc':
            code='v(code)' if arm=='a' else '(4095-v(code))'
            if name.startswith('c'): state=f'(floor({code}/512)>{name[1:]})'
            else:
                bit=int(name[1:]);state=f'(floor({code}/{2**bit})-2*floor({code}/{2**(bit+1)}))'
            lines.append(f'B{tag} {source} 0 V=5*{state}')
        else: lines.append(f'V{tag} {source} 0 DC 0 AC {0.5 if arm=="a" else -0.5}')
        for parallel in range(p):
            prev=source
            for series in range(s):
                node=arm if series==s-1 else f'n{tag}_{parallel}_{series}'
                lines.append(f'R{tag}_{parallel}_{series} {prev} {node} {UNIT}')
                if mode!='dc' and stray_pf and series<s-1:
                    lines.append(f'C{tag}_{parallel}_{series} {node} 0 {stray_pf}p')
                prev=node;count+=1
    assert count==TOTAL
    lines+=['Rload a b 10000','.save v(a) v(b)', '.dc Vcode 0 4095 1' if mode=='dc' else '.ac dec 50 10 1000000','.end']
    return '\n'.join(lines)+'\n'

def simulation():
    spice=NgSpice();net=deck();(GEN/'full_array_dc.cir').write_text(net)
    spice.run(net);v=spice.vector('a')-spice.vector('b')
    expected=5*(2*np.arange(4096)-4095)/4096*10000/(10000+2*ARM_R)
    lsb=(expected[-1]-expected[0])/4095
    error=float(max(abs(v-expected))/lsb)
    assert len(v)==4096 and error<1e-5
    # The shared adapter exposes real vectors only. ngspice let creates real
    # magnitude/phase vectors for AC results before retrieval.
    ac=[]
    for cp in [0,.02,.1,.5]:
        net=deck('ac',cp);(GEN/f'full_array_ac_{cp:g}pf.cir').write_text(net)
        spice.run(net)
        spice.command('let gain_mag = mag(v(a)-v(b))')
        spice.command('let freq_real = real(frequency)')
        f=spice.vector('freq_real');mag=spice.vector('gain_mag')
        idx=int(np.argmin(abs(f-20000)))
        ac.append(dict(internal_node_ground_capacitance_pf=cp,frequency_hz=float(f[idx]),
                       gain_20k=float(mag[idx]),gain_20k_db=float(20*np.log10(mag[idx]))))
        plt.semilogx(f,20*np.log10(mag/mag[0]),label=f'{cp:g} pF / internal node')
    plt.xlabel('Frequency (Hz)');plt.ylabel('Gain relative to 10 Hz (dB)')
    plt.title('Hypothetical array parasitics - not extracted PCB capacitance')
    plt.grid(alpha=.25);plt.legend();plt.tight_layout();plt.savefig(MODEL/'parasitic_sensitivity.png',dpi=160);plt.close()
    (OUT/'ngspice.log').write_text('\n'.join(spice.log))
    return dict(full_code_dc_max_error_lsb=error,ac_sensitivity=ac)

def geometry():
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="790" viewBox="0 0 1000 790">',
         '<rect width="1000" height="790" fill="white"/>',
         '<g font-family="Arial" fill="#203143"><text x="35" y="30" font-size="23">One coarse assembly: 6 in series x 24 parallel strings</text>',
         '<text x="35" y="55" font-size="16">Every rectangle = 169 kohm ERA-8AEB1693V. Total: 144 parts; equivalent: 42.25 kohm.</text></g>',
         '<g stroke="#287558" stroke-width="2" fill="none">',
         '<path d="M60 90 V734 M930 90 V734"/>']
    for j in range(24):
        y=90+j*28
        svg.append(f'<path d="M60 {y} H930"/>')
        for k in range(6):
            x=100+k*135
            svg.append(f'<rect x="{x}" y="{y-7}" width="70" height="14" fill="white"/>')
    svg+=['</g><g font-family="Arial" fill="#203143" font-size="14">',
          '<text x="35" y="773">Two-terminal conceptual network only; not a PCB layout or energized-HV build instruction.</text></g></svg>']
    (MODEL/'coarse_connection.svg').write_text('\n'.join(svg))
    parts=[];labels=[]
    # Two separate arm envelopes. Pitch is a visual assumption, NOT clearance.
    for arm,offset in [('A',0),('B',270)]:
        for j in range(7):
            x0=offset+10+(j%3)*78;y0=15+(j//3)*44
            labels.append((x0,y0-4,f'{arm} coarse {j+1}: 144'))
            for n in range(144): parts.append([x0+(n%12)*6,y0+(n//12)*3,1.6,3.2,1.6,.6,arm,f'coarse{j+1}'])
        n=0
        for w in [256,128,64,32,16,8,4,2,1,1]:
            row=BY_WEIGHT[w]
            for _ in range(row['parts_per_assembly']):
                parts.append([offset+10+(n%38)*6,153+(n//38)*3,1.6,3.2,1.6,.6,arm,f'fine{w}'])
                n+=1
        labels.append((offset+10,148,f'{arm} fine + termination: {n}'))
    assert len(parts)==TOTAL
    for part in parts:
        local=part[0]-(0 if part[6]=='A' else 270)
        assert 0<=local and local+part[3]<=250 and part[1]+part[4]<=220
    placement=dict(units='mm',board_envelopes=[[0,0,0,250,220,1.6],[270,0,0,250,220,1.6]],
        warning='Envelope only. No pads, copper, routing, clearance or thermal qualification.',parts=parts)
    (MODEL/'placements.json').write_text(json.dumps(placement,indent=2))
    template=(ROOT/'docs/resistor_array_viewer_template.html').read_text(encoding='utf-8')
    (MODEL/'resistor_array_3d.html').write_text(template.replace('__MODEL_DATA__',json.dumps(placement)),encoding='utf-8')
    # Explicit cuboid OBJ, millimetres. No external library required.
    vertices=[];faces=[]
    def box(x,y,z,dx,dy,dz,material):
        n=len(vertices)
        vertices.extend([(x,y,z),(x+dx,y,z),(x+dx,y+dy,z),(x,y+dy,z),
                         (x,y,z+dz),(x+dx,y,z+dz),(x+dx,y+dy,z+dz),(x,y+dy,z+dz)])
        for face in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            faces.append((material,[n+i+1 for i in face]))
    for x in [0,270]:box(x,0,0,250,220,1.6,'board')
    for part in parts:box(*part[:6],'resistor')
    obj=['# Units: millimetres; envelope study only','mtllib resistor_array.mtl']
    obj += ['v '+' '.join(map(str,v)) for v in vertices]
    last=None
    for mat,face in faces:
        if mat!=last:obj.append('usemtl '+mat);last=mat
        obj.append('f '+' '.join(map(str,face)))
    (MODEL/'resistor_array.obj').write_text('\n'.join(obj)+'\n')
    (MODEL/'resistor_array.mtl').write_text('newmtl board\nKd 0.08 0.35 0.26\nnewmtl resistor\nKd 0.17 0.21 0.26\n')
    fig,ax=plt.subplots(figsize=(14,7))
    for x in [0,270]:ax.add_patch(Rectangle((x,0),250,220,facecolor='#e1ede5',edgecolor='#386854'))
    for x,y,z,dx,dy,dz,*_ in parts:ax.add_patch(Rectangle((x,y),dx,dy,facecolor='#253549',linewidth=0))
    for x,y,text in labels:ax.text(x,y,text,fontsize=7)
    ax.set(xlim=(-5,525),ylim=(225,-15),aspect='equal',xlabel='mm',ylabel='mm',title=f'{TOTAL:,} resistors | two 250 x 220 mm envelopes | one mono channel')
    fig.text(.5,.02,'Component bodies only. Spacing is illustrative, not an HV PCB layout. Drivers and thermal system excluded.',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(MODEL/'array_top.png',dpi=160);plt.close(fig)
    fig=plt.figure(figsize=(13,7));ax=fig.add_subplot(111,projection='3d',computed_zorder=False)
    boards=[];tops=[]
    for x in [0,270]:boards.append([(x,0,1.6),(x+250,0,1.6),(x+250,220,1.6),(x,220,1.6)])
    for x,y,z,dx,dy,dz,*_ in parts:tops.append([(x,y,z+dz),(x+dx,y,z+dz),(x+dx,y+dy,z+dz),(x,y+dy,z+dz)])
    ax.add_collection3d(Poly3DCollection(boards,facecolors='#287558',edgecolors='#164a37',zorder=1))
    ax.add_collection3d(Poly3DCollection(tops,facecolors='#253549',edgecolors='none',zorder=2))
    ax.set(xlim=(0,520),ylim=(0,220),zlim=(0,30),xlabel='mm',ylabel='mm',zlabel='mm')
    ax.set_box_aspect((520,220,30));ax.view_init(elev=38,azim=-65)
    ax.set_zticks([0,30])
    ax.set_title('Resistor-array envelope | 3,052 actual-size 1206 bodies\nTwo 250 x 220 mm panels; no copper or thermal hardware')
    fig.tight_layout();fig.savefig(MODEL/'array_3d.png',dpi=180);plt.close(fig)
    return parts

def main():
    verify=simulation();geometry()
    shift=100*(ARM_R/OLD_ARM-1)
    gain_ratio=(10000+2*OLD_ARM)/(10000+2*ARM_R)
    data=dict(mpn=MPN,unit_ohm=UNIT,total_parts=TOTAL,spares_20pct_quantity=math.ceil(TOTAL*1.2),
              arm_resistance_ohm=ARM_R,common_resistance_shift_percent=shift,
              nominal_gain_change_percent=100*(gain_ratio-1),nominal_power_change_percent=100*(gain_ratio**2-1),
              cost_no_spares_usd=TOTAL*.15558,cost_20pct_spares_usd=math.ceil(TOTAL*1.2)*.15558,
              rows=ROWS,verification=verify)
    (OUT/'summary.json').write_text(json.dumps(data,indent=2)+'\n')
    lines=['| Weight | Old target (kohm) | Candidate (kohm) | Series x parallel | Assemblies | Parts each | Parts total |',
           '|---|---:|---:|---|---:|---:|---:|']
    for r in ROWS:lines.append(f"| {r['weight']} | {r['old_resistance_ohm']/1000:.6f} | {r['resistance_ohm']/1000:g} | {r['series']}S x {r['parallel']}P | {r['quantity']} | {r['parts_per_assembly']} | {r['total_parts']} |")
    (OUT/'assembly_table.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in data.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
