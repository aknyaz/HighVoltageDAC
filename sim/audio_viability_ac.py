"""Independent ngspice checks of audio-screen gain and output impedance."""
import json,sys
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'calc'))
from audio_viability import R,P,LP,LS,M,transfer,impedance
from ngspice_shared import NgSpice

def main():
 out=ROOT/'results/audio_viability';gen=ROOT/'sim/generated/audio_viability'
 for p in (out,gen):p.mkdir(exist_ok=True,parents=True)
 spice=NgSpice();rows=[]
 for load in (4,8,16,None):
  name=f'ac_load{load}'
  lines=[name,('Vsrc src 0 DC 0 AC 1' if load else 'Vsrc src 0 DC 0 AC 0'),f'Rsrc src p {2*R+P["rp"]:.15g}',
    f'Lp p 0 {LP}',f'Ls s 0 {LS:.15g}',f'K1 Lp Ls {M/np.sqrt(LP*LS):.15g}',
    'Rsec s out .2','Rcore p 0 100k','Cpri p 0 100p']
  lines += [f'Rload out 0 {load}'] if load else ['Itest 0 out DC 0 AC 1']
  lines+=['.ac dec 40 20 20000','.end'];net='\n'.join(lines)+'\n';(gen/(name+'.cir')).write_text(net);spice.run(net)
  spice.command('let f_real = real(frequency)');spice.command('let out_mag = mag(v(out))')
  f=spice.vector('f_real');actual=spice.vector('out_mag');expected=abs(transfer(f,load=load)) if load else abs(impedance(f))
  err=float(max(abs(actual/expected-1)));assert err<1e-7,err
  rows.append(dict(load_ohm=load,quantity='gain' if load else 'output_impedance',max_relative_analytic_error=err))
 (out/'ac_checks.json').write_text(json.dumps(dict(spice_runs=4,rows=rows),indent=2)+'\n')
 (out/'ac.log').write_text('\n'.join(l.rstrip() for msg in spice.log for l in msg.splitlines())+'\n')
 print('PASS',rows)
if __name__=='__main__':main()
