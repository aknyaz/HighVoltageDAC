"""Datasheet-informed linear switch surrogates, NOT vendor transistor models."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from compare_switching_glitches import states, topology, decode, R, LOAD, K, VS, LSB, T0
from ngspice_shared import NgSpice

ROOT=Path(__file__).resolve().parents[1]
PROFILES={
    'sic_20pf':dict(ron=.35,cap=20e-12,note='C3M0350120D Ron typ; Coss typ at 1000 V, frozen'),
    'sic_100pf_sensitivity':dict(ron=.35,cap=100e-12,note='Assumed capacitance sensitivity, not a device specification'),
    'silicon_102pf':dict(ron=6.,cap=102e-12,note='STP3N150 Ron typ; Coss typ at 25 V, frozen'),
}


def dc(kind,code,ron):
    w=topology(kind);g=1/(K*R/w+ron);total=sum(g)+1/(K*R)
    rhs=VS*np.array([g@decode(kind,code),g@decode(kind,K-1-code)])
    va,vb=np.linalg.solve([[total+1/LOAD,-1/LOAD],[-1/LOAD,total+1/LOAD]],rhs)
    return va-vb


def make_deck(kind,profile,dead_ns,skew_ns,step_ns):
    p=PROFILES[profile]
    w,start,end,late,_=states(kind,2047,2048,'heavy_late')
    lines=['Linear Ron/Coss/BBM surrogate - 5 V only','Vref ref 0 5',
           f'.model sw SW(Ron={p["ron"]} Roff=1e12 Vt=.5 Vh=0)',
           '.options reltol=1e-7 abstol=1e-13 method=gear']
    for arm,side in enumerate(('a','b')):
        for i,weight in enumerate(w):
            for rail,node in ((1,'ref'),(0,'0')):
                initial=int(start[arm,i]==rail);final=int(end[arm,i]==rail)
                when=T0+late[arm,i]*skew_ns*1e-9+(dead_ns*1e-9 if final else 0)
                source=str(initial) if initial==final else f'PWL(0 {initial} {when-5e-13:.15g} {initial} {when+5e-13:.15g} {final})'
                ident=f'{side}{i}r{rail}'
                lines += [f'V{ident} c{ident} 0 {source}',
                          f'S{ident} d{side}{i} {node} c{ident} 0 sw',
                          f'C{ident} d{side}{i} {node} {p["cap"]:.15g}']
            lines.append(f'R{side}{i} {side} d{side}{i} {K*R/weight:.15g}')
        lines.append(f'R{side}term {side} 0 {K*R:.15g}')
    lines += [f'Rload a b {LOAD:g}',f'.tran {step_ns}n 2u 0 {step_ns}n','.end']
    return '\n'.join(lines)+'\n'


def measure(spice,kind,profile):
    t=spice.vector('time');v=spice.vector('a')-spice.vector('b')
    before=dc(kind,2047,PROFILES[profile]['ron']);after=dc(kind,2048,PROFILES[profile]['ron'])
    assert abs(v[0]-before)/LSB<1e-4
    assert abs(v[-1]-after)/LSB<1e-4
    # Integrate error only after request; insert the continuous value at T0.
    keep=t>T0;tt=np.r_[T0,t[keep]];vv=np.r_[np.interp(T0,t,v),v[keep]]
    error=(vv-after)/LSB
    return dict(peak_error_lsb=float(max(abs(error))),
                absolute_area_lsb_ns=float(np.trapezoid(abs(error),tt)*1e9),
                signed_area_lsb_ns=float(np.trapezoid(error,tt)*1e9),
                final_error_lsb=float(abs(v[-1]-after)/LSB)),(t,v,after)


def main():
    result=ROOT/'results/nonideal_switches';generated=ROOT/'sim/generated/nonideal_switches';plots=ROOT/'plots/nonideal_switches'
    for path in (result,generated,plots):path.mkdir(parents=True,exist_ok=True)
    spice=NgSpice();rows=[];traces={}
    for kind in ('binary','segmented'):
        for profile in PROFILES:
            for dead,skew in ((0,0),(20,0),(20,20),(100,20)):
                name=f'{kind}_{profile}_dead{dead}_skew{skew}'
                netlist=make_deck(kind,profile,dead,skew,1.)
                (generated/f'{name}.cir').write_text(netlist);spice.run(netlist)
                values,trace=measure(spice,kind,profile)
                # Every case repeats at half maximum timestep to check integration.
                fine=make_deck(kind,profile,dead,skew,.5)
                (generated/f'{name}_fine.cir').write_text(fine);spice.run(fine)
                refined,_=measure(spice,kind,profile)
                delta=abs(refined['absolute_area_lsb_ns']-values['absolute_area_lsb_ns'])
                assert delta<.1+.005*refined['absolute_area_lsb_ns'],(name,delta)
                rows.append(dict(architecture=kind,profile=profile,dead_ns=dead,skew_ns=skew,
                                 **refined,area_convergence_lsb_ns=delta))
                if dead==20 and skew==20:traces[kind,profile]=trace
    # Count actual branch-node toggles for one periodic, rounded, full-range 1 kHz sine.
    pcm=np.rint(2047.5+2047.5*np.sin(2*np.pi*np.arange(192)/192)).astype(int)
    energy=[]
    for kind in ('binary','segmented'):
        sequence=np.array([[decode(kind,int(c)),decode(kind,K-1-int(c))] for c in pcm])
        toggles=int(np.sum(sequence!=np.roll(sequence,1,axis=0)))
        for profile,p in PROFILES.items():
            # Two equal linear Coss per half bridge: C*Vbus^2 per hard node transition.
            energy.append(dict(architecture=kind,profile=profile,toggles_per_1ms=toggles,
                               assumed_hard_switch_capacitive_w_650v=toggles*1000*p['cap']*650**2))
    report=dict(model='Linear surrogate only, no vendor MOSFET or driver model',profiles=PROFILES,
                spice_runs=2*len(rows),rows=rows,capacitive_loss_scenarios=energy)
    (result/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    (result/'ngspice.log').write_text('\n'.join(spice.log))
    fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True)
    for ax,kind in zip(axes,('binary','segmented')):
        for profile in PROFILES:
            t,v,after=traces[kind,profile];ax.plot((t-T0)*1e9,(v-after)/LSB,label=profile)
        ax.set_title(kind.title());ax.set_ylabel('Error (LSB)');ax.grid(alpha=.3);ax.legend();ax.set_xlim(-10,160)
    axes[-1].set_xlabel('Time from request (ns)')
    fig.suptitle('2047 to 2048: 20 ns dead time + 20 ns heavy-branch skew\n5 V linear surrogates; separate vertical scales; no transformer')
    fig.tight_layout();fig.savefig(plots/'midscale.png',dpi=150);plt.close(fig)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
