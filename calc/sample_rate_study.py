"""192/384/768 kS/s comparison using the same quantizer and linear output model."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from quantization_study import run,ROOT,MODES

def main():
 baseline=json.loads((ROOT/'results/quantization/summary.json').read_text())
 combined=[];timing=[]
 for fs in (192000,384000,768000):
  report=run(fs,f'sample_rates/{fs}')
  if fs==192000:
   assert report['rows']==baseline['rows'],'192 kHz regression differs from saved prior study'
  # Scheduling check only; the spectral calculation itself uses uniform sample times.
  clocks=np.floor(np.arange(int(fs*.2))*50e6/fs+.5).astype(int)
  intervals=np.diff(clocks)
  assert intervals.min()>10, 'Requests would overlap the ten-cycle blank interval'
  timing.append(dict(sample_rate_hz=fs,min_clock_cycles=int(intervals.min()),max_clock_cycles=int(intervals.max()),
                     nominal_sample_period_ns=1e9/fs,command_blank_fraction=200e-9*fs))
  for row in report['rows']:
   rate=row['statistics']['branch_transitions_per_s']['median']
   combined.append(dict(sample_rate_hz=fs,**row,mean_blank_fraction_per_branch=rate*200e-9/32))
 out=ROOT/'results/sample_rates';plots=ROOT/'plots/sample_rates'
 summary=dict(rows=combined,timing=timing,total_trials=384,record_seconds=.2,warmup_seconds=.01,seeds=8,
               regression_192khz_exact_match=True,scope='Reused digital/linear model; no physical-switch transient validation at higher rates. Coss losses are conditional hard-switch estimates.')
 (out/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
 fig,axes=plt.subplots(1,3,figsize=(14,4.5))
 for mode in MODES:
  signal=[r for r in combined if r['mode']==mode and r['amplitude']==.01]
  idle=[r for r in combined if r['mode']==mode and r['amplitude']==0]
  rates=[r['sample_rate_hz']/1000 for r in signal]
  axes[0].plot(rates,[r['statistics']['inband_error_percent_of_signal']['median'] for r in signal],'o-',label=mode)
  axes[1].plot(rates,[r['statistics']['conditional_coss_loss_650v_w']['median'] for r in signal],'o-',label=mode)
  axes[2].plot(rates,[r['statistics']['conditional_coss_loss_650v_w']['median'] for r in idle],'o-',label=mode)
 axes[0].set(yscale='log',ylabel='20 Hz-20 kHz error / signal (%)',title='1% amplitude, 1 kHz sine')
 axes[1].set(ylabel='Conditional Coss loss (W)',title='1% input / 650 V loss scenario')
 axes[2].set(ylabel='Conditional Coss loss (W)',title='Silence / 650 V loss scenario')
 for ax in axes:ax.set_xlabel('Sample rate (kS/s)');ax.set_xticks([192,384,768]);ax.grid(alpha=.3);ax.legend(fontsize=8)
 fig.suptitle('Same 12-bit 3+9 decoder and LL1679 linear model; eight-seed medians')
 fig.tight_layout();fig.savefig(plots/'comparison.png',dpi=150);plt.close(fig)
 print('PASS: 384 trials; 192 kHz exact regression; clock interval checks',flush=True)
if __name__=='__main__':main()
