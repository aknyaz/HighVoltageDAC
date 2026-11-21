"""Bounded digital quantization study; no physical switch or HDL implementation."""
from pathlib import Path
import sys,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sim'))
from select_transformer import PARTS,transfer
from partition_study import decode
from sic_charge import integrals
FS=192000;N=38400;WARM=1920;MODES=('round','tpdf','ef1_tpdf','ef2_tpdf')

def quantize(x,mode,seed):
 rng=np.random.default_rng(seed);d=rng.random(len(x))-rng.random(len(x)) if mode!='round' else np.zeros(len(x))
 q=np.empty(len(x));err=np.zeros(len(x));e1=e2=0.;clipped=0
 for i,value in enumerate(x):
  feedback=e1 if mode=='ef1_tpdf' else 2*e1-e2 if mode=='ef2_tpdf' else 0.
  v=value+feedback;unclipped=np.floor(v+d[i]+.5);out=np.clip(unclipped,0,4095)
  clipped+=int(out!=unclipped);e=v-out if out==unclipped else 0.
  q[i]=out;err[i]=e;e2=e1;e1=e
 assert clipped==0,(mode,seed,clipped)
 if mode.startswith('ef'):
  prev=np.r_[0,err[:-1]];prev2=np.r_[0,0,err[:-2]]
  predicted=prev-err if mode=='ef1_tpdf' else 2*prev-prev2-err
  assert max(abs(q-x-predicted))<1e-10
  assert max(abs(err))<1.5+1e-10
 return q.astype(int),clipped

def run(sample_rate=FS, study='quantization'):
 FS=sample_rate;N=int(.2*FS);WARM=int(.01*FS)
 result=ROOT/'results'/study;plots=ROOT/'plots'/study
 for p in (result,plots):p.mkdir(parents=True,exist_ok=True)
 f=np.fft.rfftfreq(N,1/FS);p=PARTS['LL1679_PP_B']
 h=np.zeros_like(f,dtype=complex);h[1:]=transfer(f[1:],p,100,100000)*np.sinc(f[1:]/FS)*np.exp(-1j*np.pi*f[1:]/FS)
 weight=np.full(len(f),2.);weight[[0,-1]]=1
 band=(f>=20)&(f<=20000);high=(f>20000)&(f<=FS/2)
 bins=np.arange(2,21)*int(1000*N/FS);fund=int(1000*N/FS)
 rows=[];spectra={}
 for amplitude in (.9,.01,.001,0.):
  x=2047.5+2047.5*amplitude*np.sin(2*np.pi*1000*(np.arange(N+WARM)+.5)/FS)
  wanted=x[WARM:];signal=np.sqrt(2)*abs(np.fft.rfft((wanted-2047.5)*10/4096)[fund]/N*h[fund])
  fs_signal=2047.5*10/4096*abs(h[fund])/np.sqrt(2)
  for mode in MODES:
   trials=[];accum=np.zeros(len(f))
   for seed in range(8):
    q,clipped=quantize(x,mode,20261115+seed);q=q[WARM:];error=q-wanted
    ef=np.fft.rfft(error)/N
    assert abs(np.sum(weight*abs(ef)**2)-np.mean(error**2))<1e-10
    physical_error=ef*10/4096*h
    rms=float(np.sqrt(np.sum(weight[band]*abs(physical_error[band])**2)))
    hf=float(np.sqrt(np.sum(weight[high]*abs(physical_error[high])**2)))
    out=np.fft.rfft((q-2047.5)*10/4096)/N*h
    harmonic=float(np.sqrt(np.sum(2*abs(out[bins])**2)))
    states=np.column_stack([decode(3,q),decode(3,4095-q)])
    toggles=int(np.count_nonzero(states[1:]!=states[:-1]))
    trials.append(dict(inband_error_percent_of_signal=100*rms/signal if amplitude else None,
      inband_error_dbfs=float(20*np.log10(max(rms/fs_signal,1e-20))),
      harmonic_bins_percent_of_signal=100*harmonic/signal if amplitude else None,
      outband_error_rms_v=hf,branch_transitions_per_s=toggles*FS/(N-1),
      conditional_coss_loss_650v_w=toggles*FS/(N-1)*650*integrals(650)[0],clipped_samples=clipped,
      average_code_error=float(np.mean(error))))
    accum+=weight*abs(out)**2/8
   first=trials[0];stats={}
   for key in first:
    if first[key] is not None:
     a=[v[key] for v in trials];stats[key]=dict(median=float(np.median(a)),min=float(min(a)),max=float(max(a)))
   rows.append(dict(amplitude=amplitude,mode=mode,statistics=stats))
   if amplitude==.01:spectra[mode]=accum
 report=dict(sample_rate_hz=FS,samples=N,warmup_samples=WARM,seeds=8,modes=MODES,rows=rows,
   transformer='LL1679/PP B equivalent: assumed 100 pF and 100 kohm core loss',
   loss_estimate='Transition rate times 650*Qoss(650) from existing approximate charge curve; hard-switch scenario only, excludes driver/gate/resistor losses',
   scope=f'Ideal {FS/1000:g} kS/s held-code spectral model, 5 V scaling. No 50 MHz jitter, blanking, mismatch, switching transients, physical noise or HDL. Baseband to Nyquist only; sampling images above {FS/2000:g} kHz omitted.')
 (result/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 fig,axes=plt.subplots(2,1,figsize=(10,8))
 for mode,power in spectra.items():
  # Combine ten 5 Hz bins into 50 Hz power bands, preserving integrated power.
  trim=(len(f)//10)*10;freq=f[:trim].reshape(-1,10).mean(axis=1);v=power[:trim].reshape(-1,10).sum(axis=1)
  reference=(2047.5*10/4096*abs(h[fund])/np.sqrt(2))**2
  axes[0].plot(freq/1000,10*np.log10(np.maximum(v/reference,1e-20)),label=mode)
 axes[0].set(xlim=(0,FS/2000),ylim=(-140,-25),xlabel='Frequency (kHz)',ylabel='Power per 50 Hz band (dBFS)',title='1% input: eight-seed mean output spectrum')
 for mode in MODES:
  selected=[r for r in rows if r['mode']==mode and r['amplitude']>0]
  axes[1].plot([20*np.log10(r['amplitude']) for r in selected],[r['statistics']['inband_error_percent_of_signal']['median'] for r in selected],'o-',label=mode)
 axes[1].set(yscale='log',xlabel='Input sine amplitude (dBFS)',ylabel='20 Hz-20 kHz error / signal (%)',title='Quantization error includes harmonics and added dither noise')
 for ax in axes:ax.grid(alpha=.3);ax.legend()
 fig.tight_layout();fig.savefig(plots/'comparison.png',dpi=150);plt.close(fig)
 for r in rows:
  if r['amplitude'] in (.01,0.):print(json.dumps(r),flush=True)
 print(f'PASS: {FS} Hz, 128 records, eight seeds, Parseval and error-feedback identities, no clipping',flush=True)
 return report
if __name__=='__main__':run()
