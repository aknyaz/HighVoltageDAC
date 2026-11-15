"""Short major-carry transient against the zero-blanking reference."""
from pathlib import Path
import re,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from controller_analog import deck,decode,ROOT
from ngspice_shared import NgSpice

def transient(dead,cap,step,reverse):
    codes=[2048,2047] if reverse else [2047,2048]
    states={a:decode(3,np.array(codes) if a=='a' else 4095-np.array(codes)) for a in ('a','b')}
    lines=[]
    for line in deck(dead,cap,step).splitlines():
        match=re.match(r'V([ab])(\d+)_(\d) ',line)
        if match:
            a,j,rail=match.groups();initial,final=(states[a][:,int(j)]==int(rail)).astype(int)
            value=str(initial)
            if initial!=final:
                t=1e-6+(dead*1e-9 if final else 0)
                value=f'PWL(0 {initial} {t:.14g} {initial} {t+2e-9:.14g} {final})'
            line=line.split(' PWL')[0]+' '+value
        if line.startswith('.tran'):line=f'.tran {step}n 10u 0 {step}n'
        lines.append(line)
    return '\n'.join(lines)+'\n'

def main():
    res=ROOT/'results/controller_analog';gen=ROOT/'sim/generated/controller_analog';plots=ROOT/'plots/controller_analog'
    for p in (res,gen,plots):p.mkdir(parents=True,exist_ok=True)
    spice=NgSpice();rows=[];plotdata={};grid=np.linspace(1e-6,10e-6,9001)
    for reverse in (False,True):
        for cap in (20,100):
            allsteps=[]
            for step in (2,1):
                traces={}
                for dead in (0,200):
                    net=transient(dead,cap,step,reverse)
                    name=f'carry_reverse{int(reverse)}_c{cap}_dead{dead}_step{step}'
                    (gen/(name+'.cir')).write_text(net);spice.run(net)
                    t=spice.vector('time');traces[dead]=np.array([np.interp(grid,t,spice.vector('a')-spice.vector('b')),np.interp(grid,t,spice.vector('out'))])
                difference=traces[200]-traces[0]
                measured=dict(primary_peak_difference_v=float(max(abs(difference[0]))),secondary_peak_difference_v=float(max(abs(difference[1]))),
                              primary_absolute_difference_v_ns=float(np.trapezoid(abs(difference[0]),grid)*1e9))
                allsteps.append(measured)
            area_delta=abs(allsteps[0]['primary_absolute_difference_v_ns']-measured['primary_absolute_difference_v_ns'])
            assert area_delta<.01+.005*measured['primary_absolute_difference_v_ns']
            rows.append(dict(reverse=reverse,cap_pf=cap,**measured,area_step_difference_v_ns=area_delta))
            if not reverse:plotdata[cap]=traces
    for cap in (20,100):
        pair=[r for r in rows if r['cap_pf']==cap]
        assert abs(pair[0]['primary_peak_difference_v']-pair[1]['primary_peak_difference_v'])<1e-5
    (res/'transitions.json').write_text(json.dumps(dict(spice_runs=16,window_s=[1e-6,10e-6],rows=rows,scope='Difference from overlapping-edge zero-blanking reference; no saturation, clamp or driver model'),indent=2)+'\n')
    (res/'transitions_ngspice.log').write_text('\n'.join(spice.log))
    fig,axes=plt.subplots(2,1,figsize=(9,7),sharex=True)
    for cap,traces in plotdata.items():
        for dead,trace in traces.items():
            for i,ax in enumerate(axes):ax.plot((grid-1e-6)*1e6,trace[i]*1000,label=f'{cap} pF, {dead} ns')
    axes[0].set(ylabel='Primary voltage (mV)',title='2047 to 2048, 5 V, assumed linear transformer')
    axes[1].set(ylabel='Secondary voltage (mV)',xlabel='Time after request (us)',xlim=(0,3))
    for ax in axes:ax.legend();ax.grid(alpha=.3)
    fig.tight_layout();fig.savefig(plots/'major_carry.png',dpi=150);plt.close(fig)
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
