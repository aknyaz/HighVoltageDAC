"""20 Hz mute/DC study in the continuous Thevenin equivalent, not a switch replay."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from controller_analog import ROOT,R
from select_transformer import PARTS
from ngspice_shared import NgSpice
P=PARTS['LL1679_PP_B']; LP=P['lp']; LS=LP/P['n']**2
M=np.sqrt((LP-P['leak'])*LS); RS=2*R+P['rp']; RC=100000.; C=100e-12
MUTE=.254; PARK=.258; RESUME=.458; STOP=.712; DT=10e-6
SCALE=5*4095/4096

def envelope(t):
    return np.clip((t-.002)/.002,0,1)*np.clip((MUTE+.002-t)/.002,0,1)+np.clip((t-RESUME-.002)/.002,0,1)

def source(t,phase,offset):
    return SCALE*(.9*np.cos(2*np.pi*20*(t-MUTE)+np.deg2rad(phase))+offset)*envelope(t)

def deck(phase,offset,step):
    env=f'(min(max((time-.002)/.002,0),1)*min(max(({MUTE+.002}-time)/.002,0),1)+min(max((time-{RESUME+.002})/.002,0),1))'
    expr=f'{SCALE:.15g}*(.9*cos(2*pi*20*(time-{MUTE})+{np.deg2rad(phase):.15g})+{offset})*{env}'
    return '\n'.join(['20 Hz continuous Thevenin model / 5 V / linear LL1679',
        f'Bsrc src 0 V={expr}',f'Rsrc src p {RS:.15g}',f'Lp p 0 {LP}',f'Ls s 0 {LS:.15g}',
        f'K1 Lp Ls {M/np.sqrt(LP*LS):.15g}','Rsec s out .2','Rload out 0 8',
        f'Rcore p 0 {RC}',f'Cpri p 0 {C}', '.options reltol=1e-8 abstol=1e-14 method=gear',
        '.save v(src) v(p) v(out) i(Lp) i(Ls)',f'.tran {step}u {STOP} 0 {step}u','.end'])+'\n'

def independent(t,phase,offset):
    # State [Ip, Is, Vprimary]; eliminate the resistive secondary and source nodes.
    inv=np.linalg.inv(np.array([[LP,M],[M,LS]]))
    a=np.zeros((3,3));a[:2,1]=inv[:,1]*(-8.2);a[:2,2]=inv[:,0]
    a[2]=[-1/C,0,-(1/RS+1/RC)/C];b=np.array([0.,0.,1/(RS*C)])
    eig,v=np.linalg.eig(a);beta=np.linalg.solve(v,b);z=eig*DT
    f=np.exp(z);g1=(np.expm1(z)-z)/(eig**2*DT);g0=np.expm1(z)/eig-g1
    u=source(t,phase,offset);state=np.zeros(3,dtype=complex);states=np.zeros((len(t),3))
    for j in range(len(t)-1):
        state=f*state+beta*(g0*u[j]+g1*u[j+1]);states[j+1]=(v@state).real
    return states,eig

def metrics(t,tr,offset):
    ip,iss=tr['lp#branch'],tr['ls#branch'];im=ip+M/LP*iss
    energy=.5*LP*ip**2+.5*LS*iss**2+M*ip*iss
    steady=(t>=MUTE-.05)&(t<MUTE);quiet=(t>=PARK)&(t<RESUME)
    qidx=np.flatnonzero(quiet);initial=abs(im[qidx[0]])
    hits=np.flatnonzero(np.maximum.accumulate(abs(im[qidx])[::-1])[::-1]<=initial*.01)
    dc=SCALE*offset/RS
    return dict(steady_primary_mean_a=float(ip[steady].mean()),expected_dc_a=dc,
        steady_magnetizing_peak_a=float(max(abs(im[steady]))),whole_magnetizing_peak_a=float(max(abs(im))),
        startup_magnetizing_peak_a=float(max(abs(im[t<.054]))),
        restart_magnetizing_peak_a=float(max(abs(im[t>=RESUME]))),
        flux_linkage_peak_wb_turn=float(LP*max(abs(im))),
        park_magnetizing_a=float(im[qidx[0]]),quiet_end_magnetizing_a=float(im[qidx[-1]]),
        quiet_output_peak_v=float(max(abs(tr['out'][quiet]))),quiet_end_output_v=float(tr['out'][qidx[-1]]),
        park_magnetic_energy_j=float(energy[qidx[0]]),quiet_end_magnetic_energy_j=float(energy[qidx[-1]]),
        decay_to_one_percent_s=float(t[qidx[hits[0]]]-PARK) if len(hits) else None,
        restart_output_peak_v=float(max(abs(tr['out'][t>=RESUME])))),im

def main():
    out=ROOT/'results/low_frequency';gen=ROOT/'sim/generated/low_frequency';plots=ROOT/'plots/low_frequency'
    for p in (out,gen,plots):p.mkdir(parents=True,exist_ok=True)
    t=np.arange(round(STOP/DT)+1)*DT;spice=NgSpice();rows=[];traces={};runs=0
    for offset in (0.,.01,-.01,.05):
        for phase in (0,90,180,270):
            name=f'phase{phase}_offset{offset:g}';measures=[]
            for step in (100,50):
                net=deck(phase,offset,step);(gen/f'{name}_{step}us.cir').write_text(net);spice.run(net);runs+=1
                tt=spice.vector('time');assert tt[-1]>=STOP-1e-10
                tr={n:np.interp(t,tt,spice.vector(n)) for n in ('out','p','lp#branch','ls#branch')}
                met,im=metrics(t,tr,offset);measures.append(met)
                (out/f'{name}_{step}us.log').write_text('\n'.join(l.rstrip() for msg in spice.log for l in msg.splitlines())+'\n');spice.log.clear()
            coarse,fine=measures
            delta=abs(coarse['quiet_output_peak_v']-fine['quiet_output_peak_v'])
            assert delta<2e-6,delta
            states,eig=independent(t,phase,offset)
            out_error=float(max(abs(tr['out']+8*states[:,1])))
            mag_error=float(max(abs(im-(states[:,0]+M/LP*states[:,1]))))
            assert out_error<5e-6,(name,out_error)
            assert mag_error<.1e-6,(name,mag_error)
            assert abs(fine['steady_primary_mean_a']-fine['expected_dc_a'])<.2e-6
            row=dict(phase_degrees_at_mute=phase,pcm_offset=offset,**fine,
                     quiet_peak_refinement_v=delta,independent_output_error_v=out_error,independent_magnetizing_error_a=mag_error)
            rows.append(row);traces[phase,offset]=(tr,im)
            (out/'partial.json').write_text(json.dumps(rows,indent=2)+'\n')
            print(name,row,flush=True)
    # Separate DC operating-point checks: no audio or initial-state ambiguity.
    dc_rows=[]
    for offset in (.01,-.01,.05):
        net=deck(0,offset,50).splitlines();net[1]=f'Vsrc src 0 DC {SCALE*offset:.15g}'
        net=[('.op' if line.startswith('.tran') else line) for line in net]
        text='\n'.join(net)+'\n';(gen/f'dc_{offset:g}.cir').write_text(text);spice.run(text);runs+=1
        ip=float(spice.vector('lp#branch')[0]);expected=SCALE*offset/RS
        assert abs(ip-expected)<1e-12
        dc_rows.append(dict(offset=offset,current_a=ip,expected_a=expected))
    (out/'dc.log').write_text('\n'.join(l.rstrip() for msg in spice.log for l in msg.splitlines())+'\n')
    report=dict(spice_runs=runs,bus_v=5,frequency_hz=20,amplitude=.9,transformer=P,
        source_resistance_with_primary_dcr_ohm=RS,assumed_core_loss_ohm=RC,assumed_primary_capacitance_f=C,
        mute_s=MUTE,park_s=PARK,resume_s=RESUME,stop_s=STOP,
        slowest_linear_time_constant_s=float(-1/max(eig.real)),rows=rows,dc_checks=dc_rows,
        scope='Continuous Thevenin equivalent with nominal DAC range scaling. No 12-bit quantization, held PCM, Coss, switch blanking, arm mismatch or RTL replay. Linear magnetic model; linkage is not flux density or saturation qualification.')
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
    for phase in (0,90,180,270):
        tr,im=traces[phase,0.];axes[0].plot((t-MUTE)*1000,tr['out']*1000,label=f'{phase} deg')
        axes[1].plot((t-MUTE)*1000,im*1e6,label=f'{phase} deg')
    for offset in (0.,.01,-.01,.05):
        tr,im=traces[90,offset];axes[2].plot((t-MUTE)*1000,im*1e6,label=f'DC {offset*100:g}%')
    axes[0].set(ylabel='Secondary (mV)',title='20 Hz, continuous 5 V equivalent: mute phase and DC offset')
    axes[1].set(ylabel='Magnetizing current (uA)')
    axes[2].set(ylabel='Magnetizing current (uA)',xlabel='Time after mute request (ms)',xlim=(-60,310))
    for ax in axes:ax.grid(alpha=.3);ax.legend();ax.axvspan(4,204,color='grey',alpha=.12)
    fig.tight_layout();fig.savefig(plots/'comparison.png',dpi=150);plt.close(fig)
    print('PASS',runs,'ngspice runs',flush=True)
if __name__=='__main__':main()
