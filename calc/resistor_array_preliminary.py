"""Close the bounded preliminary thermal/substrate/edge-stress screen.

All ngspice excitation is 5 V; HV values are linear analytical scaling only.
Capacitances and thermal resistances below are sensitivity assumptions.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from resistor_array_design import ARM_R, UNIT, BY_WEIGHT, assemblies, deck
from ngspice_shared import NgSpice

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/resistor_array_preliminary';OUT.mkdir(parents=True,exist_ok=True)
GEN=ROOT/'sim/generated/resistor_array_preliminary';GEN.mkdir(parents=True,exist_ok=True)
PLOTS=ROOT/'output/resistor_array';PLOTS.mkdir(parents=True,exist_ok=True)

def thermal():
    codes=np.arange(4096);vs=650.;load=10000.
    ea=vs*codes/4096;eb=vs*(4095-codes)/4096
    dv=(ea-eb)*load/(load+2*ARM_R)
    nodes={'a':(ea+eb+dv)/2,'b':(ea+eb-dv)/2}
    powers={a:np.zeros(4096) for a in nodes}
    max_chip=0
    for arm,name,w in assemblies():
        d=codes if arm=='a' else 4095-codes
        if name=='term':state=np.zeros(4096)
        elif name[0]=='c':state=d//512>int(name[1:])
        else:state=(d>>int(name[1:]))&1
        row=BY_WEIGHT[w];drop=vs*state-nodes[arm]
        powers[arm]+=drop**2/row['resistance_ohm']
        max_chip=max(max_chip,float(np.max((drop/row['series'])**2/UNIT)))
    sine=np.rint(2047.5*(1+np.sin(2*np.pi*np.arange(192)/192))).astype(int)
    heat=dict(max_per_panel_w=max(float(np.max(p)) for p in powers.values()),
              min_per_panel_w=min(float(np.min(p)) for p in powers.values()),
              max_total_w=float(np.max(powers['a']+powers['b'])),
              full_sine_total_w=float(np.mean((powers['a']+powers['b'])[sine])),
              max_static_chip_w=max_chip)
    rows=[]
    for ambient in [20,25,35]:
        for theta in [1,2,4]:
            reject=(50-ambient)/theta
            rows.append(dict(ambient_c=ambient,theta_k_per_w=theta,heat_rejection_at_50c_w=reject,
                             supply_off_hold_50c_heater_w=reject,
                             additional_cooling_at_max_heat_w=max(0,heat['max_per_panel_w']-reject)))
    return dict(ideal_resistive_load_ohm=load,supply_v=vs,heat=heat,temperature_cases=rows,
                required_theta_at_35c_for_heater_only_k_per_w=15/heat['max_per_panel_w'])

def edge_deck(cg,cr,rise_ns,step_ns=1):
    # Six-part string, held-zero far end, initially discharged: conservative
    # source-edge fixture; not the operating waveform of the complete amplifier.
    lines=['Six-resistor edge screen, 5 V only','.options reltol=1e-7 abstol=1e-14',
           f'Vin in 0 PWL(0 0 1u 0 {1e-6+rise_ns*1e-9:.12g} 5 20u 5)']
    for j in range(6):
        a='in' if j==0 else f'n{j}'
        b='0' if j==5 else f'n{j+1}'
        lines.append(f'R{j} {a} {b} {UNIT}')
        if cr:lines.append(f'Cp{j} {a} {b} {cr}p')
        if j<5 and cg:lines.append(f'Cg{j} {b} 0 {cg}p')
    lines+=['.save v(in) v(n1) v(n2) v(n3) v(n4) v(n5)',f'.tran {step_ns}n 20u 0 {step_ns}n','.end']
    return '\n'.join(lines)+'\n'

def main():
    spice=NgSpice();edge=[]
    for cg in [0,.02,.1,1,5]:
        for cr in ([0] if cg==0 else [0,.05,.2]):
            for rise in [20,100]:
                name=f'edge_g{cg:g}_r{cr:g}_{rise}ns';net=edge_deck(cg,cr,rise)
                (GEN/f'{name}.cir').write_text(net);spice.run(net)
                t=spice.vector('time')
                nodes=[spice.vector('in')]+[spice.vector(f'n{j}') for j in range(1,6)]+[np.zeros(len(t))]
                peak=float(np.max(np.abs(np.diff(np.array(nodes),axis=0))))*130
                edge.append(dict(ground_pf=cg,across_resistor_pf=cr,rise_ns=rise,peak_chip_scaled_650_v=peak,
                                 exceeds_150v_continuous_limit=peak>150))
                if rise==20 and cr==0:
                    plt.plot((t-1e-6)*1e9,(nodes[0]-nodes[1])*130,label=f'{cg:g} pF/node')
    plt.xlim(-10,300);plt.ylim(0,680);plt.axhline(150,color='red',linestyle='--',label='150 V continuous rating')
    plt.xlabel('Time from source edge (ns)');plt.ylabel('First-chip voltage, scaled to 650 V')
    plt.title('20 ns source edge; six-resistor fixture; capacitance assumptions')
    plt.legend();plt.grid(alpha=.2);plt.tight_layout();plt.savefig(PLOTS/'edge_voltage_screen.png',dpi=160);plt.close()
    # Independent timestep refinement at a nontrivial parasitic corner.
    refined_deck=edge_deck(.1,.05,20,.5)
    (GEN/'edge_refinement_0p5ns.cir').write_text(refined_deck)
    spice.run(refined_deck)
    nodes=[spice.vector('in')]+[spice.vector(f'n{j}') for j in range(1,6)]
    nodes.append(np.zeros(len(nodes[0])))
    refined=float(np.max(np.abs(np.diff(np.array(nodes),axis=0))))*130
    base=next(r['peak_chip_scaled_650_v'] for r in edge if r['ground_pf']==.1 and r['across_resistor_pf']==.05 and r['rise_ns']==20)
    assert abs(refined-base)<1
    # Extend the full 3,052-resistor AC model to plausible metal-backed node-C scales.
    ac=[]
    for cp in [0,1,5,10]:
        net=deck('ac',cp);(GEN/f'array_ac_{cp}pf.cir').write_text(net);spice.run(net)
        spice.command('let gm = mag(v(a)-v(b))');spice.command('let fr = real(frequency)')
        f=spice.vector('fr');gain=spice.vector('gm');i=int(np.argmin(abs(f-20000)))
        ac.append(dict(ground_pf=cp,frequency_hz=float(f[i]),gain_db=float(20*np.log10(gain[i]))))
    for r in ac:r['additional_loss_db']=ac[0]['gain_db']-r['gain_db']
    caps=[]
    for area in [1,4]:
        for er in [4,7]:
            for thickness in [75,150]:
                caps.append(dict(area_mm2=area,epsilon_r=er,dielectric_um=thickness,
                                 capacitance_pf=8.8541878128e-12*er*area*1e-6/(thickness*1e-6)*1e12))
    report=dict(date='2026-11-22',thermal=thermal(),parallel_plate_sensitivity=caps,
                edge_fixture=edge,timestep_refinement_peak_difference_v=abs(refined-base),
                metal_backed_ac_sensitivity=ac,
                conclusion='Preliminary sourcing/static/envelope checks complete. Fast-edge resistor rating and substrate remain unqualified; do not release HV purchasing/layout.')
    (OUT/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'ngspice.log').write_text('\n'.join(spice.log))
    print(json.dumps(dict(thermal=report['thermal'],ac=ac,edge_examples=[r for r in edge if r['rise_ns']==20 and r['across_resistor_pf'] in [0,.05]],refinement_v=abs(refined-base)),indent=2))

if __name__=='__main__':main()
