"""Stored-energy release in the 5 V 3+9 network; idealized rail clamps, not vendor diodes."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from controller_analog import ROOT,R,K,weights
from select_transformer import PARTS
from ngspice_shared import NgSpice
P=PARTS['LL1679_PP_B'];CP=20e-12;CT=100e-12;CORE=100000.;BUS=5.;I0=50e-6;STOP=.02

def deck(mode,load,step,sign=1):
 lp=P['lp'];ls=lp/P['n']**2;k=np.sqrt(1-P['leak']/lp)
 lines=[f'Stored energy release: {mode}, 5 V, initial magnetizing current {sign*I0}',
 'Vref ref 0 5','.options reltol=1e-7 abstol=1e-13 method=gear']
 for arm in ('a','b'):
  for j,w in enumerate(weights(3)):
   node=f'd{arm}{j}'
   lines.extend([f'R{arm}{j} {arm} {node} {K*R/w:.15g}',f'Rh{arm}{j} {node} ref 1e12',f'Rl{arm}{j} {node} 0 {0.35 if mode=="park_low" else 1e12}',f'Ch{arm}{j} {node} ref 20p IC=-5',f'Cl{arm}{j} {node} 0 20p IC=0'])
   if mode!='off_unclamped':
    lines.extend([f'Bdl{arm}{j} 0 {node} I=max(-v({node})-0.7,0)/2',f'Bdh{arm}{j} {node} ref I=max(v({node})-5.7,0)/2'])
  lines.append(f'Rt{arm} {arm} 0 {K*R:.15g}')
 lines.extend(['Rp a p 160',f'Lp p b {lp} IC={sign*I0}',f'Ls s 0 {ls:.15g} IC=0',f'K1 Lp Ls {k:.15g}','Rs s out .2',f'Rload out 0 {load}',f'Rcore p b {CORE}','Cpri p b 100p IC=0','.save all',f'.tran {step}u {STOP} 0 {step}u UIC','.end'])
 return '\n'.join(lines)+'\n'

def measure(spice,mode,load):
 t=spice.vector('time');v={n:spice.vector(n) for n in ['a','b','p','s','out','ref']}
 ip=spice.vector('lp#branch');iss=spice.vector('ls#branch');lp=P['lp'];ls=lp/P['n']**2;m=np.sqrt((lp-P['leak'])*ls)
 energy=.5*lp*ip**2+.5*ls*iss**2+m*ip*iss+.5*CT*(v['p']-v['b'])**2
 loss=(v['a']-v['p'])**2/P['rp']+(v['s']-v['out'])**2/P['rs']+v['out']**2/load+(v['p']-v['b'])**2/CORE
 node_peak=0.;excursion=0.;diode_peak=0.;clamp_loss=np.zeros_like(t)
 for arm in ('a','b'):
  loss+=v[arm]**2/(K*R)
  for j,w in enumerate(weights(3)):
   node=spice.vector(f'd{arm}{j}')
   energy+=.5*CP*(node**2+(node-BUS)**2)
   loss+=(v[arm]-node)**2/(K*R/w)+(node-BUS)**2/1e12+node**2/(.35 if mode=='park_low' else 1e12)
   node_peak=max(node_peak,float(max(np.max(abs(node)),np.max(abs(BUS-node)))))
   excursion=max(excursion,float(max(np.max(-node),np.max(node-BUS),0)))
   if mode!='off_unclamped':
    il=np.maximum(-node-.7,0)/2;ih=np.maximum(node-5.7,0)/2
    clamp_loss+=il*(-node)+ih*(node-5)
    diode_peak=max(diode_peak,float(max(il.max(),ih.max())))
 loss+=clamp_loss
 source=-BUS*spice.vector('vref#branch')
 e0=.5*lp*I0**2+32*.5*CP*BUS**2
 integral=lambda x:float(np.trapezoid(np.r_[0,x],np.r_[0,t]))
 supplied=integral(source);dissipated=integral(loss);balance=supplied-dissipated-(energy[-1]-e0)
 rel=abs(balance)/(.5*lp*I0**2)
 assert rel<.01,(mode,load,rel)
 return dict(primary_peak_v=float(max(abs(v['a']-v['b']))),secondary_peak_v=float(max(abs(v['out']))),
 device_vds_peak_v=node_peak,node_outside_rails_v=excursion,clamp_peak_a=diode_peak,
 final_primary_current_a=float(ip[-1]),initial_magnetic_energy_j=.5*lp*I0**2,
 final_total_energy_j=float(energy[-1]),supplied_energy_j=supplied,dissipated_energy_j=dissipated,
 clamp_energy_j=integral(clamp_loss),energy_balance_relative_error=rel), (t,v['a']-v['b'],v['out'],ip)

def main():
 out=ROOT/'results/shutdown';gen=ROOT/'sim/generated/shutdown';plots=ROOT/'plots/shutdown'
 for p in (out,gen,plots):p.mkdir(parents=True,exist_ok=True)
 spice=NgSpice();rows=[];traces={}
 cases=[(mode,load,sign) for mode in ('off_unclamped','off_clamped','park_low') for load in (8.,1e9) for sign in (1,-1)]
 for mode,load,sign in cases:
  stats=[]
  for step in (2.,1.):
   name=f'{mode}_load{load:g}_sign{sign}_step{step:g}us';net=deck(mode,load,step,sign)
   (gen/(name+'.cir')).write_text(net);spice.run(net);r,trace=measure(spice,mode,load);stats.append(r)
  coarse,fine=stats
  delta=abs(coarse['primary_peak_v']-fine['primary_peak_v'])
  assert delta<.001+.01*fine['primary_peak_v'],(mode,load,delta)
  rows.append(dict(mode=mode,load_ohm=load,initial_current_sign=sign,**fine,primary_peak_refinement_v=delta))
  if sign==1:traces[mode,load]=trace
  print(mode,load,sign,fine,flush=True)
 report=dict(spice_runs=len(cases)*2,rows=rows,stop_s=STOP,bus_v=BUS,initial_current_a=I0,
   transformer=P,capacitance_per_switch_f=CP,primary_capacitance_f=CT,assumed_core_loss_ohm=CORE,
   scope='Imposed initial magnetic state, not shutdown from simulated music. Fixed control states; 0.7 V / 2 ohm idealized rail clamps, no vendor diode, no saturation or bus collapse. Not a hardware shutdown qualification.')
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 (out/'ngspice.log').write_text('\n'.join(l.rstrip() for msg in spice.log for l in msg.splitlines())+'\n',newline='\n')
 fig,axes=plt.subplots(2,1,figsize=(10,7))
 for (mode,load),(t,v,sec,ip) in traces.items():
  if load==1e9:
   axes[0].plot(t*1000,v,label=mode);axes[1].plot(t*1000,ip*1e6,label=mode)
 axes[0].set(ylabel='Primary terminal voltage (V)',xlim=(0,.2),title='Open secondary, imposed 50 uA initial primary current, 5 V model')
 axes[1].set(ylabel='Primary current (uA)',xlabel='Time (ms)',xlim=(0,20))
 for ax in axes:ax.grid(alpha=.3);ax.legend()
 fig.tight_layout();fig.savefig(plots/'release.png',dpi=150);plt.close(fig)
 print('PASS',len(cases)*2,'runs')
if __name__=='__main__':main()
