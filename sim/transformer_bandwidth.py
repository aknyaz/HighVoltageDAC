"""Conditional transformer inductance requirement; not a component rating."""
import json
import numpy as np
from audio_band import ROOT,R,FS
from ngspice_shared import NgSpice
LEAK=10*(1-.999**2)

def response(f,lp):
    w=2*np.pi*f;ls=lp/1250;k=np.sqrt(1-LEAK/lp);m=k*np.sqrt(lp*ls)
    sec=8.2+1j*w*ls;coil=1j*w*lp+w*w*m*m/sec
    z=1/(1/coil+1/100000+1j*w*100e-12)
    return z/(2*R+200+z)/coil*(1j*w*m*8/sec)

def ratio(lp):
    return 20*np.log10(abs(response(20,lp))*np.sinc(20/FS)/(abs(response(1000,lp))*np.sinc(1000/FS)))

def main():
    lo,hi=10.,1000.
    for _ in range(70):
        mid=(lo+hi)/2
        if ratio(mid)<-1:lo=mid
        else:hi=mid
    lp=hi;ls=lp/1250;k=np.sqrt(1-LEAK/lp)
    assert abs(ratio(lp)+1)<1e-8
    circuit=(ROOT/'sim/generated/audio_band/transformer_ac.cir').read_text().replace('Lp p 0 10',f'Lp p 0 {lp:.15g}').replace('Ls s 0 .008',f'Ls s 0 {ls:.15g}').replace('K1 Lp Ls .999',f'K1 Lp Ls {k:.15g}').replace('.ac dec 80 10 1Meg','.ac lin 2 20 1000')
    spice=NgSpice();v=[]
    for frequency in (20,1000):
        case=circuit.replace('.ac lin 2 20 1000',f'.ac lin 1 {frequency} {frequency}')
        (ROOT/f'sim/generated/audio_band/inductance_requirement_{frequency}hz.cir').write_text(case)
        spice.run(case);spice.command('let output_magnitude = mag(v(out))')
        v.append(float(spice.vector('output_magnitude')[0]))
    observed=20*np.log10(v[0]*np.sinc(20/FS)/(v[1]*np.sinc(1000/FS)))
    assert abs(observed+1)<1e-6
    report=dict(target_20hz_gain_db_relative_1khz=-1,required_primary_self_inductance_h=lp,secondary_self_inductance_h=ls,
                held_primary_short_circuit_leakage_h=LEAK,coupling=k,spice_verified_gain_db=float(observed),
                assumed_source_resistance_ohm=2*R,spice_runs=2,
                scope='Conditional linear calculation: ratio, leakage, DCR, core-loss resistance and capacitance held fixed; no actual component selection or magnetic saturation claim')
    (ROOT/'results/audio_band/inductance_requirement.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'results/audio_band/inductance_ngspice.log').write_text('\n'.join(line.rstrip() for msg in spice.log for line in msg.splitlines())+'\n',newline='\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
