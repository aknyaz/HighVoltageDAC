"""3+9 analog blanking study; explicit 5 V switch surrogate and assumed transformer."""
from pathlib import Path
import sys, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ngspice_shared import NgSpice
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calc'))
from partition_study import weights,decode,R,K
FS=192000
N=3840  # Twenty 1 kHz periods; evaluate last two, check preceding two.
PARAMS=dict(primary_inductance_h=10.,secondary_inductance_h=.008,coupling=.999,
            primary_dcr_ohm=200.,secondary_dcr_ohm=.2,primary_shunt_pf=100.,
            primary_core_loss_ohm=100000.,load_ohm=8.,switch_ron_ohm=.35)

def deck(dead,cap,step):
    half=np.floor(2047.5+2047.5*.9*np.sin(2*np.pi*(np.arange(96)+.5)/192)+.5).astype(int)
    period=np.r_[half,4095-half]
    codes=np.r_[period[-1],period]
    states=np.stack([decode(3,codes),decode(3,4095-codes)],axis=1)
    lines=['3+9 DAC / 5 V / assumed linear transformer / command blanking',
           'Vref ref 0 5','.model sw SW(Ron=.35 Roff=1e12 Vt=.5 Vh=0)',
           '.options reltol=1e-6 abstol=1e-12 method=gear']
    for side,arm in enumerate(('a','b')):
        for j,w in enumerate(weights(3)):
            seq=states[:,side,j]
            for rail,node in ((1,'ref'),(0,'0')):
                initial=int(seq[0]==rail);points=[f'0 {initial}']
                for k in np.flatnonzero(seq[1:]!=seq[:-1])+1:
                    final=int(seq[k]==rail)
                    t=(k-.5)/FS+(dead*1e-9 if final else 0)
                    points.extend([f'{t:.14g} {1-final}',f'{t+2e-9:.14g} {final}'])
                points.append(f'.001 {initial}')
                ident=f'{arm}{j}_{rail}'
                lines.extend([f'V{ident} c{ident} 0 PWL('+ ' '.join(points)+') r=0',
                              f'B{ident} d{arm}{j} {node} I=v(d{arm}{j},{node})*(1e-12+(1/.35-1e-12)*v(c{ident}))',
                              f'C{ident} d{arm}{j} {node} {cap}p'])
            lines.append(f'R{arm}{j} {arm} d{arm}{j} {K*R/w:.14g}')
        lines.append(f'R{arm}term {arm} 0 {K*R:.14g}')
    lines += ['Rp a p 200','Lp p b 10','Ls s 0 .008','K1 Lp Ls .999',
              'Rs s out .2','Rload out 0 8','Rcore p b 100k','Cpri p b 100p',
              '.save v(a) v(b) v(out) i(Lp)',f'.tran {step}n {N/FS:.14g} 0 {step}n','.end']
    return '\n'.join(lines)+'\n'

def measure(spice):
    t=spice.vector('time');out=spice.vector('out');pri=spice.vector('a')-spice.vector('b');ip=spice.vector('lp#branch')
    dt=50e-9
    def spectrum(start):
        ts=start+np.arange(40000)*dt
        vs=np.interp(ts,t,out);f=np.fft.rfft(vs)*2/len(vs)
        return vs,f
    v,f=spectrum(.018);prev,fp=spectrum(.016)
    fundamental=abs(f[2]);thd=100*np.linalg.norm(f[np.arange(2,21)*2])/fundamental
    ts=.018+np.arange(40000)*dt
    # 500 Hz bins, harmonics only. No noise model or THD+N claim.
    row=dict(fundamental_peak_v=float(fundamental),thd_2_to_20_percent=float(thd),
             secondary_mean_v=float(v.mean()),load_power_w=float(np.mean(v*v)/8),
             primary_peak_v=float(max(abs(np.interp(ts,t,pri)))),
             primary_mean_current_a=float(np.mean(np.interp(ts,t,ip))),
             previous_window_fundamental_delta_percent=float(100*abs(abs(fp[2])-fundamental)/fundamental),
             previous_window_thd_delta_pp=float(abs(100*np.linalg.norm(fp[np.arange(2,21)*2])/abs(fp[2])-thd)))
    return row,(ts,v,f)

def main():
    res=ROOT/'results/controller_analog';gen=ROOT/'sim/generated/controller_analog';plots=ROOT/'plots/controller_analog'
    for p in (res,gen,plots):p.mkdir(parents=True,exist_ok=True)
    spice=NgSpice();rows=[];traces={}
    for cap in (20,100):
        for dead in (0,200):
            measurements=[]
            for step in (500,250):
                name=f'c{cap}pf_dead{dead}ns_step{step}ns';net=deck(dead,cap,step)
                (gen/(name+'.cir')).write_text(net)
                spice.run(net);metrics,trace=measure(spice);measurements.append(metrics)
                print(name,metrics,flush=True)
            coarse,fine=measurements
            gain_delta=100*abs(coarse['fundamental_peak_v']-fine['fundamental_peak_v'])/fine['fundamental_peak_v']
            thd_delta=abs(coarse['thd_2_to_20_percent']-fine['thd_2_to_20_percent'])
            assert gain_delta<.1 and thd_delta<.01,(gain_delta,thd_delta)
            assert fine['previous_window_fundamental_delta_percent']<.05
            assert fine['previous_window_thd_delta_pp']<.01
            rows.append(dict(cap_pf=cap,dead_ns=dead,**fine,timestep_gain_delta_percent=gain_delta,timestep_thd_delta_pp=thd_delta))
            traces[cap,dead]=trace
    report=dict(supply_v=5,architecture='3+9',sample_rate_hz=FS,input_hz=1000,amplitude_full_scale=.9,
                transformer=PARAMS,spice_runs=8,analysis_window_s=[.018,.020],uniform_analysis_step_ns=50,
                conductance_edge_ns=2,command_timing='Ideal 192 kS/s requests; not 50 MHz clock quantized',scope='Linear assumed transformer; frozen Coss per device; no vendor device model, driver delays, saturation, noise or HDL co-simulation',rows=rows)
    (res/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    (res/'ngspice.log').write_text('\n'.join(spice.log))
    fig,axes=plt.subplots(2,1,figsize=(10,7))
    for (cap,dead),(ts,v,f) in traces.items():
        axes[0].plot((ts-.018)*1e6,v,label=f'{cap} pF, {dead} ns')
        freq=np.fft.rfftfreq(len(v),50e-9)
        axes[1].plot(freq/1000,20*np.log10(np.maximum(abs(f)/abs(f[2]),1e-10)),label=f'{cap} pF, {dead} ns')
    axes[0].set(xlim=(0,100),xlabel='Time within analysis window (us)',ylabel='Secondary voltage (V)')
    axes[1].set(xlim=(0,25),ylim=(-120,5),xlabel='Frequency (kHz)',ylabel='Spectrum (dBc)')
    for ax in axes:ax.grid(alpha=.3);ax.legend()
    fig.suptitle('3+9 DAC: 1 kHz at 90% full scale, assumed linear transformer\n5 V simulation; frozen capacitance sensitivity')
    fig.tight_layout();fig.savefig(plots/'comparison.png',dpi=150);plt.close(fig)
    print('PASS: eight runs, timestep and settling checks',flush=True)
if __name__=='__main__':main()
