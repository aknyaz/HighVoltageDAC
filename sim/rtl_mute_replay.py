"""Replay executed Amaranth gate vectors in the existing 5 V analog surrogate."""
import csv,json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from controller_analog import ROOT
from ngspice_shared import NgSpice
from quiet_transitions import deck as template

def read_rows(path):
    with path.open() as f:return np.array([[int(x) for x in r.values()] for r in csv.DictReader(f)],dtype=np.int64)

def pwl(times,values,stop):
    points=[f'0 {values[0]:.15g}'];last=values[0]
    for t,v in zip(times[1:],values[1:]):
        if v==last:continue
        assert 0<t<t+2e-9<stop
        points += [f'{t:.15g} {last:.15g}',f'{t+2e-9:.15g} {v:.15g}'];last=v
    points.append(f'{stop:.15g} {last:.15g}')
    return 'PWL('+ ' '.join(points)+')'

def netlist(edges,commands,clock,stop,step,reference):
    lines=template('ramp',0,0,step,reference).splitlines();replaced=0
    for i,line in enumerate(lines):
        if reference and line.startswith(('Va srca','Vb srcb')):
            side=int(line.startswith('Vb'));arm='ab'[side]
            lines[i]=f'V{arm} src{arm} 0 '+pwl(commands[:,0]/clock,commands[:,side+1]*5/4096,stop);replaced+=1
        elif not reference and line.startswith(('Va','Vb')):
            ident=line.split()[0][1:];arm=ident[0];j,rail=map(int,ident[1:].split('_'))
            bit=j+16*int(arm=='b');col=1 if rail else 2
            values=(edges[:,col]>>bit)&1
            lines[i]=f'V{ident} c{ident} 0 '+pwl(edges[:,0]/clock,values,stop);replaced+=1
        elif line.startswith('.tran '):lines[i]=f'.tran {step}n {stop:.15g} 0 {step}n'
    assert replaced==(2 if reference else 64),replaced
    lines[0]='Executed RTL mute replay / 5 V / nominal switches and loaded linear LL1679'
    return '\n'.join(lines)+'\n'

def main():
    out=ROOT/'results/rtl_replay';gen=ROOT/'sim/generated/rtl_replay';plots=ROOT/'plots/rtl_replay'
    for p in (out,gen,plots):p.mkdir(parents=True,exist_ok=True)
    meta=json.loads((out/'export.json').read_text());clock=meta['clock_hz'];stop=meta['stop_cycle']/clock
    edges=read_rows(out/'gate_edges.csv');commands=read_rows(out/'code_commands.csv')
    assert np.all(np.diff(edges[:,0])>0) and np.all((edges[:,1]&edges[:,2])==0)
    assert np.all(np.diff(commands[:,0])>0)
    spice=NgSpice();grid=np.arange(0,stop,100e-9);traces={}
    for reference,steps in ((True,(100,50)),(False,(1000,500))):
        for step in steps:
            name=f'{"reference" if reference else "rtl"}_{step}ns';net=netlist(edges,commands,clock,stop,step,reference)
            (gen/(name+'.cir')).write_text(net);spice.run(net)
            t=spice.vector('time');assert t[-1]>=stop-1e-10
            tr={n:np.interp(grid,t,spice.vector(n)) for n in ('a','b','out','lp#branch','ls#branch')}
            traces[name]=tr
            (out/(name+'_ngspice.log')).write_text('\n'.join(l.rstrip() for msg in spice.log for l in msg.splitlines())+'\n');spice.log.clear()
            print('Completed',name,flush=True)
    ref=traces['reference_50ns'];fine=traces['rtl_500ns'];coarse=traces['rtl_1000ns']
    error=fine['out']-ref['out'];coarse_error=coarse['out']-ref['out']
    refdelta=float(max(abs(ref['out']-traces['reference_100ns']['out'])))
    peakdelta=float(abs(max(abs(error))-max(abs(coarse_error))))
    assert refdelta<2e-6,refdelta
    assert peakdelta<2e-6+.02*max(abs(error)),peakdelta
    q=(grid>=.0092)&(grid<.0099)
    report=dict(spice_runs=4,bus_v=5,export=meta,
        source_sha256={f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in ('gate_edges.csv','code_commands.csv')},
        output_peak_v=float(max(abs(fine['out']))),error_peak_v=float(max(abs(error))),
        error_rms_v=float(np.sqrt(np.mean(error**2))),quiet_rms_v=float(np.sqrt(np.mean(fine['out'][q]**2))),
        quiet_mean_primary_current_a=float(fine['lp#branch'][q].mean()),
        reference_refinement_v=refdelta,peak_error_refinement_v=peakdelta,
        scope='Nominal one-way RTL command replay at 192 kS/s, 1 kHz 90% PCM, 8 ohm. 20 pF fixed Coss, 2 ns edges, generic rail clamps, linear LL1679; no delay skew, mismatch, nonlinear core or routed FPGA timing.')
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(3,1,figsize=(11,8),sharex=True)
    axes[0].plot(grid*1000,ref['out']*1000,label='Ideal code reference');axes[0].plot(grid*1000,fine['out']*1000,label='Actual RTL gate commands',alpha=.8)
    axes[0].set(ylabel='Secondary (mV)',title='Executed RTL -> 5 V analog model: startup, mute, resume');axes[0].legend()
    axes[1].plot(grid*1000,error*1e6);axes[1].set(ylabel='Error (uV)')
    axes[2].plot(grid*1000,fine['lp#branch']*1e6);axes[2].set(ylabel='Primary current (uA)',xlabel='Time (ms)')
    for ax in axes:ax.grid(alpha=.3);ax.axvspan(9,10,color='grey',alpha=.15)
    fig.tight_layout();fig.savefig(plots/'comparison.png',dpi=150);plt.close(fig)
    print('PASS',json.dumps(report),flush=True)
if __name__=='__main__':main()
