"""Audio/quiet transitions: structural 5 V DAC, fixed-Coss and linear-core surrogates."""
import json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from controller_analog import ROOT, R, K, weights, decode, FS
from select_transformer import PARTS
from ngspice_shared import NgSpice
P=PARTS['LL1679_PP_B']
STOP=.016
EDGE=2e-9
DEAD=200e-9

def schedule(policy):
    t=np.arange(round(STOP*FS)+1)/FS
    t=np.rint(t*50e6)/50e6
    env=np.minimum(t/.002,1.)
    if policy=='ramp':
        env*=np.clip((.006-t)/.002,0,1)+np.clip((t-.012)/.002,0,1)
        common=np.where(t<.006,1,np.where(t<.008,(.008-t)/.002,
                 np.where(t<.010,0,np.where(t<.012,(t-.010)/.002,1))))
    else:
        common=np.where((t>=.006)&(t<.012),0,1)
        env*=common
    a=np.floor(2047.5*common+2047.5*.9*env*np.cos(2*np.pi*1000*t)+.5).astype(int)
    b=np.floor(2047.5*common-2047.5*.9*env*np.cos(2*np.pi*1000*t)+.5).astype(int)
    codes=np.stack([a,b],axis=1)
    assert codes.min()>=0 and codes.max()<=4095
    quiet=(t>=.008)&(t<.010)
    assert np.all(codes[quiet]==0)
    states=np.stack([decode(3,a),decode(3,b)],axis=1)
    assert np.all(states[quiet]==0)
    assert np.min(np.diff(t))>DEAD+100e-9+EDGE
    return t,codes,states

def pwl(t,seq,delay=0,gate=False):
    pts=[f'0 {seq[0]:.15g}']
    for i in np.flatnonzero(seq[1:]!=seq[:-1])+1:
        tt=t[i]+delay+(DEAD if gate and seq[i] else 0)
        if tt+EDGE>STOP:continue
        pts += [f'{tt:.15g} {seq[i-1]:.15g}',f'{tt+EDGE:.15g} {seq[i]:.15g}']
    pts.append(f'{STOP:.15g} {seq[-2]:.15g}')
    return 'PWL('+ ' '.join(pts)+')'

def deck(policy,skew_ns,tol,step_ns,reference=False):
    t,codes,states=schedule(policy)
    rng=np.random.default_rng(20261115)
    lines=[f'Audio quiet {policy} / 5V / skew {skew_ns} ns / tolerance {tol}',
           'Vref ref 0 5',('.options reltol=1e-8 abstol=1e-14 method=gear' if reference else '.options reltol=1e-6 abstol=1e-12 method=gear')]
    for side,arm in enumerate(('a','b')):
        if reference:
            lines += [f'V{arm} src{arm} 0 '+pwl(t,codes[:,side]*5/K),f'R{arm} src{arm} {arm} {R:.15g}']
            continue
        for j,w in enumerate(weights(3)):
            node=f'd{arm}{j}'
            for rail,ref in ((1,'ref'),(0,'0')):
                seq=(states[:,side,j]==rail).astype(float)
                ident=f'{arm}{j}_{rail}'
                lines += [f'V{ident} c{ident} 0 '+pwl(t,seq,side*skew_ns*1e-9,True),
                          f'B{ident} {node} {ref} I=v({node},{ref})*(1e-12+(1/.35-1e-12)*v(c{ident}))',
                          f'C{ident} {node} {ref} 20p']
            lines += [f'R{arm}{j} {arm} {node} {K*R/w*(1+rng.uniform(-tol,tol)):.15g}',
                      f'Bdl{arm}{j} 0 {node} I=max(-v({node})-0.7,0)/2',
                      f'Bdh{arm}{j} {node} ref I=max(v({node})-5.7,0)/2']
        lines.append(f'Rt{arm} {arm} 0 {K*R*(1+rng.uniform(-tol,tol)):.15g}')
    lp=P['lp'];ls=lp/P['n']**2;k=np.sqrt(1-P['leak']/lp)
    lines += [f'Rp a p {P["rp"]}',f'Lp p b {lp}',f'Ls s 0 {ls:.15g}',f'K1 Lp Ls {k:.15g}',
              'Rs s out .2','Rload out 0 8','Rcore p b 100k','Cpri p b 100p',
              '.save v(a) v(b) v(out) i(Lp) i(Ls)',f'.tran {step_ns}n {STOP} 0 {step_ns}n','.end']
    return '\n'.join(lines)+'\n'

def trace(spice):
    t=spice.vector('time');assert t[-1]>=STOP-1e-10
    grid=np.arange(0,STOP,100e-9)
    out={n:np.interp(grid,t,spice.vector(n)) for n in ('a','b','out','lp#branch','ls#branch')}
    out['time']=grid
    # Flux linkage / Lp removes the secondary load-current contribution.
    out['magnetizing']=out['lp#branch']+np.sqrt((P['lp']-P['leak'])*P['lp']/P['n']**2)/P['lp']*out['ls#branch']
    return out

def measure(tr,ref):
    t=tr['time'];q=(t>=.009)&(t<.010);move=(t>=.006)&(t<.012);whole=(t>=.004)&(t<.014)
    error=tr['out']-ref['out']
    return dict(quiet_peak_v=float(max(abs(tr['out'][q]))),quiet_rms_v=float(np.sqrt(np.mean(tr['out'][q]**2))),
        common_move_output_peak_v=float(max(abs(tr['out'][move]))),
        transition_error_peak_v=float(max(abs(error[whole]))),transition_error_rms_v=float(np.sqrt(np.mean(error[whole]**2))),
        quiet_mean_primary_current_a=float(tr['lp#branch'][q].mean()),quiet_mean_magnetizing_current_a=float(tr['magnetizing'][q].mean()),
        magnetizing_peak_a=float(max(abs(tr['magnetizing']))),primary_peak_v=float(max(abs(tr['a']-tr['b']))))

def worker(args):
    policy,name,skew,tol,ref=args
    spice=NgSpice();measurements=[]
    gen=ROOT/'sim/generated/quiet_transitions'
    for step in (1000,500):
        net=deck(policy,skew,tol,step)
        (gen/f'{policy}_{name}_{step}ns.cir').write_text(net)
        spice.run(net);tr=trace(spice);measurements.append(measure(tr,ref))
    delta=abs(measurements[0]['transition_error_peak_v']-measurements[1]['transition_error_peak_v'])
    assert delta<2e-6+.02*measurements[1]['transition_error_peak_v'],delta
    row=dict(policy=policy,case=name,skew_ns=skew,resistor_tolerance=tol,**measurements[1],peak_error_refinement_v=delta)
    log='\n'.join(l.rstrip() for msg in spice.log for l in msg.splitlines())+'\n'
    (ROOT/f'results/quiet_transitions/{policy}_{name}_ngspice.log').write_text(log)
    return row,tr

def main():
    res=ROOT/'results/quiet_transitions';gen=ROOT/'sim/generated/quiet_transitions';plot=ROOT/'plots/quiet_transitions'
    for p in (res,gen,plot):p.mkdir(parents=True,exist_ok=True)
    spice=NgSpice();rows=[];traces={};refs={};runs=0;referrors={}
    def run(name,net):
        nonlocal runs
        (gen/(name+'.cir')).write_text(net);spice.run(net);runs+=1
        return trace(spice)
    for policy in ('abrupt','ramp'):
        refc=run(policy+'_reference_100ns',deck(policy,0,0,100,True))
        ref=run(policy+'_reference_50ns',deck(policy,0,0,50,True));refs[policy]=ref
        referr=float(max(abs(refc['out']-ref['out'])))
        assert referr<2e-6,referr
        referrors[policy]=referr
    jobs=[(policy,name,skew,tol,refs[policy]) for policy in ('abrupt','ramp')
          for name,skew,tol in [('nominal',0,0),('skew',100,0),('skew_mismatch',100,.0001)]]
    with ProcessPoolExecutor(max_workers=3) as pool:
        for row,tr in pool.map(worker,jobs):
            row['reference_refinement_v']=referrors[row['policy']]
            rows.append(row);traces[row['policy'],row['case']]=tr;runs+=2
            print(row,flush=True)
    report=dict(spice_runs=runs,bus_v=5,sample_rate_hz=FS,clock_hz=50000000,dead_ns=200,edge_ns=2,
        mismatch_seed=20261115,transformer=P,scope='Linear LL1679 model; assumed 100 kohm core, 100 pF primary, 20 pF per switch, generic 0.7 V / 2 ohm rail clamps; loaded 8 ohm; no vendor device, saturation, noise or HDL co-simulation.',rows=rows)
    (res/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    (res/'ngspice.log').write_text('\n'.join(l.rstrip() for msg in spice.log for l in msg.splitlines())+'\n')
    fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
    for policy in ('abrupt','ramp'):
        tr=traces[policy,'skew_mismatch'];t=tr['time']*1000
        axes[0].plot(t,tr['out']*1000,label=policy)
        axes[1].plot(t,(tr['out']-refs[policy]['out'])*1e6,label=policy)
        axes[2].plot(t,tr['magnetizing']*1e6,label=policy)
    axes[0].set(ylabel='Secondary (mV)',title='5 V model: 100 ns arm skew and seeded +/-0.01% resistor mismatch')
    axes[1].set(ylabel='Error vs ideal codes (uV)')
    axes[2].set(ylabel='Magnetizing current (uA)',xlabel='Time (ms)',xlim=(3,15))
    for ax in axes:
        ax.grid(alpha=.3);ax.legend();ax.axvspan(8,10,color='grey',alpha=.12)
    fig.tight_layout();fig.savefig(plot/'comparison.png',dpi=150);plt.close(fig)
    print('PASS',runs,'runs',flush=True)
if __name__=='__main__':main()


