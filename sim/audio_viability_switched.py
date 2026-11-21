"""Bounded switched checks for the audio viability decision, with LL1679 model."""
import json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from controller_analog import ROOT,R,K,FS,weights,decode
from select_transformer import PARTS,transfer
from ngspice_shared import NgSpice
P=PARTS['LL1679_PP_B'];STOP=.03;TAU=.030874264110659102

def stimulus(kind,amp):
    phase=(np.arange(192)+.5)/FS
    x=np.sin(2*np.pi*1000*phase) if kind=='sine' else .5*(np.sin(2*np.pi*19000*phase)+np.sin(2*np.pi*20000*phase))
    q=np.floor(2047.5*(1+amp*x)+.5).astype(int)
    times=np.rint(phase*50e6)/50e6
    return q,times

def deck(kind,amp,step):
    q,times=stimulus(kind,amp);states=np.stack([decode(3,np.r_[q[-1],q]),decode(3,4095-np.r_[q[-1],q])],axis=1)
    lines=['Audio viability / LL1679 / 5 V / 200 ns blanking / 20 pF',
           'Vref ref 0 5','.options reltol=1e-6 abstol=1e-12 method=gear']
    for side,arm in enumerate(('a','b')):
        for j,w in enumerate(weights(3)):
            node=f'd{arm}{j}'
            for rail,ref in ((1,'ref'),(0,'0')):
                seq=(states[:,side,j]==rail).astype(int);pts=[f'0 {seq[0]}']
                for k in np.flatnonzero(seq[1:]!=seq[:-1])+1:
                    final=seq[k];tt=times[k-1]+(200e-9 if final else 0)
                    pts.extend([f'{tt:.15g} {1-final}',f'{tt+2e-9:.15g} {final}'])
                pts.append(f'.001 {seq[0]}');ident=f'{arm}{j}_{rail}'
                lines += [f'V{ident} c{ident} 0 PWL('+ ' '.join(pts)+') r=0',
                    f'B{ident} {node} {ref} I=v({node},{ref})*(1e-12+(1/.35-1e-12)*v(c{ident}))',f'C{ident} {node} {ref} 20p']
            lines += [f'R{arm}{j} {arm} {node} {K*R/w:.15g}',f'Bdl{arm}{j} 0 {node} I=max(-v({node})-0.7,0)/2',f'Bdh{arm}{j} {node} ref I=max(v({node})-5.7,0)/2']
        lines.append(f'Rt{arm} {arm} 0 {K*R:.15g}')
    lp=P['lp'];ls=lp/P['n']**2;k=np.sqrt(1-P['leak']/lp)
    lines += [f'Rp a p {P["rp"]}',f'Lp p b {lp}',f'Ls s 0 {ls:.15g}',f'K1 Lp Ls {k:.15g}',
              'Rs s out .2','Rload out 0 8','Rcore p b 100k','Cpri p b 100p',
              '.save v(out)',f'.tran {step}n {STOP} 0 {step}n','.end']
    return '\n'.join(lines)+'\n'

def spectrum(t,out,start):
    dt=100e-9;tt=start+np.arange(100000)*dt;v=np.interp(tt,t,out)
    # Fit only period averages: stationary 1 ms-periodic AC content is retained.
    e=np.exp(-(tt-start)/TAU);a=np.c_[np.ones(10),e.reshape(10,10000).mean(axis=1)]
    coeff=np.linalg.lstsq(a,v.reshape(10,10000).mean(axis=1),rcond=None)[0]
    clean=v-coeff[0]-coeff[1]*e
    sp=2*np.fft.rfft(clean)/len(clean);raw=2*np.fft.rfft(v)/len(v)
    return sp,raw,float(coeff[1])

def metrics(sp,kind):
    idx=lambda hz:round(hz/.1e3)
    if kind=='sine':
        return dict(fundamental_peak_v=float(abs(sp[idx(1000)])),thd_2_to_20_percent=float(100*np.linalg.norm(sp[np.arange(2,21)*10])/abs(sp[10])))
    a,b=abs(sp[idx(19000)]),abs(sp[idx(20000)]);den=np.hypot(a,b)
    mask=np.zeros(len(sp),bool);mask[1:201]=True;mask[[190,200]]=False
    return dict(tone_19khz_peak_v=float(a),tone_20khz_peak_v=float(b),
        difference_1khz_percent_per_mean_tone=float(100*abs(sp[10])/((a+b)/2)),
        products_18_21khz_percent_rss_tones=float(100*np.hypot(abs(sp[180]),abs(sp[210]))/den),
        inband_nontone_percent_rss_tones=float(100*np.linalg.norm(sp[mask])/den))

def reference(kind,amp):
    q,times=stimulus(kind,amp);bounds=np.r_[0,times,.001];v=5*(2*np.r_[q[-1],q]-4095)/4096
    hz=np.arange(1,31)*1000;w=2*np.pi*hz
    c=2/.001*np.sum(v[None,:]*(np.exp(-1j*w[:,None]*bounds[:-1])-np.exp(-1j*w[:,None]*bounds[1:]))/(1j*w[:,None]),axis=1)
    sp=np.zeros(301,complex);sp[np.arange(1,31)*10]=c*transfer(hz,P,100,100000)
    return metrics(sp,kind)

def worker(case):
    kind,amp=case
    out=ROOT/'results/audio_viability';gen=ROOT/'sim/generated/audio_viability'
    spice=NgSpice();records=[]
    for step in (500,250):
        name=f'{kind}_{amp:g}_{step}ns';net=deck(kind,amp,step);(gen/(name+'.cir')).write_text(net);spice.run(net)
        t=spice.vector('time');v=spice.vector('out');assert t[-1]>=STOP-1e-10
        sp,raw,tail=spectrum(t,v,.020);prev,_,_=spectrum(t,v,.010)
        measured=metrics(sp,kind);earlier=metrics(prev,kind)
        key='thd_2_to_20_percent' if kind=='sine' else 'products_18_21khz_percent_rss_tones'
        convergence=abs(measured[key]-earlier[key]);assert convergence<.001,(name,convergence)
        records.append(measured)
        (out/(name+'.log')).write_text('\n'.join(l.rstrip() for msg in spice.log for l in msg.splitlines())+'\n');spice.log.clear()
        (out/(name+'.json')).write_text(json.dumps(dict(metrics=measured,previous=earlier),indent=2)+'\n')
    delta=abs(records[0][key]-records[1][key]);assert delta<.001,delta
    row=dict(kind=kind,amplitude=amp,**measured,ideal_held_reference=reference(kind,amp),
             raw_window_metrics=metrics(raw,kind),metric_refinement_pp=delta,preceding_window_metric_change_pp=convergence,
             fitted_slow_tail_at_window_start_v=tail)
    (out/f'{kind}_{amp:g}_result.json').write_text(json.dumps(row,indent=2)+'\n')
    return row,sp

def main():
    out=ROOT/'results/audio_viability';gen=ROOT/'sim/generated/audio_viability';plots=ROOT/'plots/audio_viability'
    for p in (out,gen,plots):p.mkdir(parents=True,exist_ok=True)
    rows=[];spectra={}
    with ProcessPoolExecutor(max_workers=3) as pool:
        for row,sp in pool.map(worker,[('sine',.9),('sine',.01),('two_tone',.9)]):
            rows.append(row);spectra[row['kind'],row['amplitude']]=sp
            print(row,flush=True)
    report=dict(spice_runs=6,bus_v=5,rows=rows,clock_hz=50000000,sample_rate_hz=FS,
        analysis_window_s=[.02,.03],previous_window_s=[.01,.02],linear_tail_time_constant_s=TAU,
        scope='Full 3+9 conductance surrogate; 20 pF fixed Coss, 200 ns command blanking, 2 ns edges, generic clamps; nominal linear LL1679. No nonlinear core, physical noise, thermal drift, HV switching model or RTL replay.')
    (out/'switched.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(12,4));freq=np.fft.rfftfreq(100000,100e-9)
    for (kind,amp),sp in spectra.items():
        ax=axes[0 if kind=='sine' else 1];den=abs(sp[10]) if kind=='sine' else max(abs(sp[190]),abs(sp[200]))
        ax.plot(freq/1000,20*np.log10(np.maximum(abs(sp)/den,1e-10)),label=f'{kind}, {amp*100:g}%')
    for ax in axes:ax.set(xlim=(0,25),ylim=(-120,5),xlabel='Frequency (kHz)',ylabel='dBc');ax.grid(alpha=.3);ax.legend()
    fig.suptitle('Switched LL1679 model: harmonic and two-tone checks, 5 V');fig.tight_layout();fig.savefig(plots/'switched.png',dpi=150);plt.close(fig)
    print('PASS six switched runs',flush=True)
def check_analysis():
    t=np.arange(300001)*100e-9
    v=.03*np.sin(2*np.pi*19000*t)+.03*np.sin(2*np.pi*20000*t)+9e-7*np.sin(2*np.pi*1000*t)+.002+.02*np.exp(-t/TAU)
    sp,_,_=spectrum(t,v,.02);error=abs(abs(sp[10])-9e-7)
    assert error<1e-10,error
    out=ROOT/'results/audio_viability';out.mkdir(parents=True,exist_ok=True)
    r=dict(test='Known periodic 19/20 kHz tones and 0.003% 1 kHz product plus DC and exponential startup tail',
        expected_difference_peak_v=9e-7,recovered_difference_peak_v=float(abs(sp[10])),absolute_error_v=float(error),
        scope='Validates detrending algorithm for its assumed exponential, not physical completeness of the transformer model')
    (out/'detrend_check.json').write_text(json.dumps(r,indent=2)+'\n')
    print('PASS synthetic tail-removal check',flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--check-analysis',action='store_true');args=parser.parse_args()
    check_analysis()
    if not args.check_analysis:main()
