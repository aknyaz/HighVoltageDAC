"""Bounded audio-band/low-level follow-up to controller_analog.py."""
import json,re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from controller_analog import ROOT,R,FS,PARAMS,deck,decode,measure
from ngspice_shared import NgSpice
OUT=ROOT/'results/audio_band';GEN=ROOT/'sim/generated/audio_band';PLOTS=ROOT/'plots/audio_band'

def transfer(freq):
    w=2*np.pi*np.asarray(freq);p=PARAMS
    lp=p['primary_inductance_h'];ls=p['secondary_inductance_h'];m=p['coupling']*np.sqrt(lp*ls)
    sec=p['load_ohm']+p['secondary_dcr_ohm']+1j*w*ls
    coil=1j*w*lp+w*w*m*m/sec
    parallel=1/(1/coil+1/p['primary_core_loss_ohm']+1j*w*p['primary_shunt_pf']*1e-12)
    return parallel/(2*R+p['primary_dcr_ohm']+parallel)/coil*(1j*w*m*p['load_ohm']/sec)

def pcm():
    half=np.floor(2047.5+2047.5*.01*np.sin(2*np.pi*(np.arange(96)+.5)/192)+.5).astype(int)
    period=np.r_[half,4095-half]
    # Round sample request instants to the nearest 50 MHz edge. 1 ms is exactly 50000 clocks.
    times=np.floor(((np.arange(192)+.5)/FS)*50e6+.5)/50e6
    assert np.max(abs(times-(np.arange(192)+.5)/FS))<=10e-9+1e-15
    assert min(np.diff(times))>200e-9+2e-9
    return period,times

def low_deck(step):
    codes,times=pcm();states={a:decode(3,np.r_[codes[-1],codes] if a=='a' else 4095-np.r_[codes[-1],codes]) for a in ('a','b')}
    lines=[]
    for line in deck(200,20,step).splitlines():
        match=re.match(r'V([ab])(\d+)_(\d) ',line)
        if match:
            arm,j,rail=match.groups();seq=(states[arm][:,int(j)]==int(rail)).astype(int)
            pts=[f'0 {seq[0]}']
            for k in np.flatnonzero(seq[1:]!=seq[:-1])+1:
                final=seq[k];t=times[k-1]+(200e-9 if final else 0)
                pts.extend([f'{t:.14g} {1-final}',f'{t+2e-9:.14g} {final}'])
            pts.append(f'.001 {seq[0]}')
            line=line.split(' PWL')[0]+' PWL('+' '.join(pts)+') r=0'
        lines.append(line)
    lines[0]='3+9 low level / 1 kHz 1 percent / 50 MHz requests / 5 V'
    return '\n'.join(lines)+'\n'

def ideal_pcm_spectrum():
    codes,times=pcm();boundaries=np.r_[0,times,.001];v=5*(2*np.r_[codes[-1],codes]-4095)/4096
    harmonics=np.arange(1,21);w=2*np.pi*1000*harmonics
    coeff=2/.001*np.sum(v[None,:]*(np.exp(-1j*w[:,None]*boundaries[:-1])-np.exp(-1j*w[:,None]*boundaries[1:]))/(1j*w[:,None]),axis=1)
    return coeff*transfer(harmonics*1000)

def main():
    for p in (OUT,GEN,PLOTS):p.mkdir(parents=True,exist_ok=True)
    spice=NgSpice()
    circuit='\n'.join(['Linear Thevenin source / assumed transformer AC response','Vsrc src 0 DC 0 AC 1',f'Rsrc src a {2*R:.14g}',
                      'Rp a p 200','Lp p 0 10','Ls s 0 .008','K1 Lp Ls .999','Rs s out .2','Rload out 0 8','Rcore p 0 100k','Cpri p 0 100p',
                      '.ac dec 80 10 1Meg','.end'])+'\n'
    (GEN/'transformer_ac.cir').write_text(circuit);spice.run(circuit)
    spice.command('let response_mag = mag(v(out))');spice.command('let sweep_frequency = real(frequency)')
    freq=spice.vector('sweep_frequency');observed=spice.vector('response_mag');expected=abs(transfer(freq))
    err=float(max(abs(observed/expected-1)));assert err<1e-7,err
    norm=abs(transfer(1000))*np.sinc(1000/FS)
    selected=[]
    for f in [20,50,100,1000,10000,20000]:
        gain=abs(transfer(f))*np.sinc(f/FS)
        selected.append(dict(frequency_hz=f,held_sine_gain_db_relative_1khz=float(20*np.log10(gain/norm))))
    ac=dict(spice_runs=1,relative_analytic_error=err,transformer=PARAMS,selected=selected,
            scope='Linear continuous-source AC check plus analytical zero-order hold; excludes branch switching/capacitance, core saturation and resistor mismatch')
    (OUT/'ac.json').write_text(json.dumps(ac,indent=2)+'\n');print('AC',json.dumps(ac),flush=True)
    np.savetxt(OUT/'frequency_response.csv',np.c_[freq,observed,20*np.log10(observed/abs(transfer(1000)))],delimiter=',',header='frequency_hz,gain_v_per_v,analog_gain_db_relative_1khz',comments='')
    fig,ax=plt.subplots(figsize=(9,4));mask=freq<=30000
    ax.semilogx(freq[mask],20*np.log10(observed[mask]/abs(transfer(1000))),label='Analog transformer network')
    ax.semilogx(freq[mask],20*np.log10(observed[mask]*np.sinc(freq[mask]/FS)/norm),label='Including ideal sample hold')
    ax.set(xlabel='Frequency (Hz)',ylabel='Gain relative to 1 kHz (dB)',title='Assumed transformer, 10 H primary, 10.55 kohm source resistance')
    ax.grid(which='both',alpha=.3);ax.legend();fig.tight_layout();fig.savefig(PLOTS/'frequency_response.png',dpi=150);plt.close(fig)
    records=[]
    for step in (500,250):
        net=low_deck(step);(GEN/f'low_level_step{step}ns.cir').write_text(net);spice.run(net)
        metrics,trace=measure(spice);records.append(metrics);print('LOW',step,metrics,flush=True)
    a,b=records;gd=100*abs(a['fundamental_peak_v']/b['fundamental_peak_v']-1);td=abs(a['thd_2_to_20_percent']-b['thd_2_to_20_percent'])
    assert gd<.1 and td<.01,(gd,td)
    assert b['previous_window_fundamental_delta_percent']<.05 and b['previous_window_thd_delta_pp']<.01
    ref=ideal_pcm_spectrum();refthd=100*np.linalg.norm(ref[1:])/abs(ref[0])
    report=dict(spice_runs=2,input_hz=1000,amplitude_full_scale=.01,dead_ns=200,cap_pf=20,supply_v=5,clock_hz=50000000,
                analysis_window_s=[.018,.020],**b,timestep_gain_delta_percent=gd,timestep_thd_delta_pp=td,
                ideal_quantized_source_fundamental_peak_v=float(abs(ref[0])),ideal_quantized_source_thd_percent=float(refthd),
                scope='Full 3+9 conductance surrogate, assumed linear transformer, rounded 50 MHz request times; no HDL co-simulation, noise or nonlinear magnetic model')
    (OUT/'low_level.json').write_text(json.dumps(report,indent=2)+'\n')
    ts,v,spectrum=trace
    fig,axes=plt.subplots(2,1,figsize=(9,7))
    axes[0].plot((ts-.018)*1000,v*1000);axes[0].set(xlabel='Time (ms)',ylabel='Secondary voltage (mV)',xlim=(0,1))
    h=np.arange(1,21)
    axes[1].plot(h,20*np.log10(np.maximum(abs(spectrum[2*h])/abs(spectrum[2]),1e-10)),'o-',label='Switched 200 ns model')
    axes[1].plot(h,20*np.log10(np.maximum(abs(ref)/abs(ref[0]),1e-10)),'x--',label='Ideal held PCM through same transformer')
    axes[1].set(xlabel='Harmonic number (1 kHz fundamental)',ylabel='Harmonic amplitude (dBc)',ylim=(-120,5))
    axes[1].legend()
    for ax in axes:ax.grid(alpha=.3)
    fig.suptitle('1% full-scale input, 50 MHz request grid, no dither or noise model');fig.tight_layout();fig.savefig(PLOTS/'low_level.png',dpi=150);plt.close(fig)
    (OUT/'ngspice.log').write_text('\n'.join(line.rstrip() for msg in spice.log for line in msg.splitlines())+'\n',newline='\n')
    print('PASS',json.dumps(report),flush=True)
if __name__=='__main__':main()
