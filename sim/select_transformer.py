"""Datasheet-informed candidate transformer screening; unmeasured parasitics swept."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from controller_analog import ROOT,R,FS
from ngspice_shared import NgSpice
PARTS={
 'LL1679_PP_B':dict(lp=150.,n=69/2,rp=160.,rs=.2,leak=.008,source='https://www.lundahltransformers.com/wp-content/uploads/datasheets/1679.pdf'),
 'LL1620_PP_B':dict(lp=300.,n=76.8/2,rp=308.,rs=.2,leak=.011,source='https://www.lundahltransformers.com/wp-content/uploads/datasheets/1620_3_7_9202.pdf')}

def transfer(f,p,cap,core,factor=1):
 w=2*np.pi*np.asarray(f);lp=p['lp']*factor;ls=lp/p['n']**2;m=np.sqrt((lp-p['leak'])*ls)
 sec=8+p['rs']+1j*w*ls;coil=1j*w*lp+w*w*m*m/sec
 z=1/(1/coil+1/core+1j*w*cap*1e-12)
 return z/(2*R+p['rp']+z)/coil*(1j*w*m*8/sec)

def main():
 out=ROOT/'results/transformer_selection';gen=ROOT/'sim/generated/transformer_selection';plots=ROOT/'plots/transformer_selection'
 for d in (out,gen,plots):d.mkdir(parents=True,exist_ok=True)
 spice=NgSpice();rows=[];fig,ax=plt.subplots(figsize=(9,5))
 for name,p in PARTS.items():
  for cap in (100,500,1000):
   for core in (100000,1000000000):
    for factor in (.5,1.):
     lp=p['lp']*factor;ls=lp/p['n']**2;k=np.sqrt(1-p['leak']/lp)
     lines=[name+' / 1 V AC / datasheet-informed linear screening','Vsrc src 0 DC 0 AC 1',f'Rsrc src a {2*R:.15g}',f'Rp a p {p["rp"]}',f'Lp p 0 {lp:.15g}',f'Ls s 0 {ls:.15g}',f'K1 Lp Ls {k:.15g}',f'Rs s out {p["rs"]}','Rload out 0 8',f'Rcore p 0 {core}',f'Cpri p 0 {cap}p','.ac dec 60 10 1Meg','.end']
     net='\n'.join(lines)+'\n';(gen/f'{name}_c{cap}_rc{core}_L{factor:g}.cir').write_text(net);spice.run(net)
     spice.command('let magnitude = mag(v(out))');spice.command('let frequency_real = real(frequency)')
     f=spice.vector('frequency_real');v=spice.vector('magnitude');expected=abs(transfer(f,p,cap,core,factor));err=float(max(abs(v/expected-1)));assert err<1e-7
     gain=lambda hz:abs(transfer(hz,p,cap,core,factor))*np.sinc(hz/FS)
     ref=gain(1000);row=dict(part=name,assumed_cap_pf=cap,assumed_core_ohm=core,inductance_factor=factor,gain_20hz_db=float(20*np.log10(gain(20)/ref)),gain_20khz_db=float(20*np.log10(gain(20000)/ref)),source_peak_for_5w_1khz_v=float(np.sqrt(2*8*5)/ref*4096/4095),source_peak_for_5w_20hz_v=float(np.sqrt(2*8*5)/gain(20)*4096/4095),linear_power_at_650v_fullscale_w=float((650*4095/4096*ref)**2/16),linear_power_at_700v_fullscale_w=float((700*4095/4096*ref)**2/16),max_spice_relative_error=err)
     rows.append(row)
     if factor==1 and core==100000 and cap in (100,1000):
      mask=f<=30000;ax.semilogx(f[mask],20*np.log10(v[mask]*np.sinc(f[mask]/FS)/ref),label=f'{name}, assumed {cap} pF')
 report=dict(date='2026-11-15',parts=PARTS,source_resistance_ohm=2*R,spice_runs=len(rows),rows=rows,scope='Datasheet nominal L/DCR/leakage/turns; assumed lumped C and core loss; L/2 sensitivity; not manufacturer SPICE or measured qualification')
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(out/'ngspice.log').write_text('\n'.join(l.rstrip() for msg in spice.log for l in msg.splitlines())+'\n',newline='\n')
 ax.set(xlabel='Frequency (Hz)',ylabel='Gain relative to 1 kHz (dB)',title='Candidate transformers: nominal L, assumed 100 kohm core loss')
 ax.grid(which='both',alpha=.3);ax.legend();fig.tight_layout();fig.savefig(plots/'comparison.png',dpi=150);plt.close(fig)
 print(json.dumps([r for r in rows if r['inductance_factor']==1 and r['assumed_cap_pf']==100],indent=2));print('PASS',len(rows),'AC sweeps')
if __name__=='__main__':main()
