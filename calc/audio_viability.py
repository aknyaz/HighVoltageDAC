"""Preliminary audio viability screen: static 12-bit DAC and linear LL1679."""
import json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'sim'))
from controller_analog import R,K,weights,decode,FS
from select_transformer import PARTS
P=PARTS['LL1679_PP_B'];LP=P['lp'];LS=LP/P['n']**2;M=np.sqrt((LP-P['leak'])*LS)
N=19200

def transfer(f,rsource=2*R,load=8):
    f=np.asarray(f);w=2*np.pi*f;sec=load+P['rs']+1j*w*LS
    coil=1j*w*LP+w*w*M*M/sec
    z=1/(1/coil+1/100000+1j*w*100e-12)
    return z/(rsource+P['rp']+z)/coil*(1j*w*M*load/sec)

def impedance(f):
    w=2*np.pi*np.asarray(f);zp=1/(1/(2*R+P['rp'])+1/100000+1j*w*100e-12)
    return P['rs']+1j*w*LS+w*w*M*M/(zp+1j*w*LP)

def main():
    out=ROOT/'results/audio_viability';plots=ROOT/'plots/audio_viability'
    for p in (out,plots):p.mkdir(parents=True,exist_ok=True)
    allcodes=np.arange(4096);da=decode(3,allcodes);db=decode(3,4095-allcodes)
    resistors=np.r_[K*R/weights(3),K*R]
    networks=[]
    for tol in (0,.0001,.001):
        for seed in range(1 if tol==0 else 8):
            rng=np.random.default_rng(20261121+seed);g=1/(resistors[None,:]*(1+rng.uniform(-tol,tol,(2,17))))
            total=g.sum(axis=1);lookup=5*(da@g[0,:16]/total[0]-db@g[1,:16]/total[1])
            if tol==0:
                assert max(abs(lookup-5*(2*allcodes-4095)/4096))<1e-12
                assert abs(sum(1/total)-2*R)<1e-9
            networks.append((tol,seed,lookup,float(sum(1/total))))
    f=np.fft.rfftfreq(N,1/FS);t=(np.arange(N)+.5)/FS;band=(f>=20)&(f<=20000)
    rows=[];spectra={}
    for frequency in (20,100,1000,5000):
        for amplitude in (.9,.1,.01,.001):
            ideal=amplitude*np.sin(2*np.pi*frequency*t)
            q=np.floor(2047.5*(1+ideal)+.5).astype(int);assert q.min()>=0 and q.max()<=4095
            for tol,seed,lookup,rs in networks:
                h=np.zeros(len(f),complex);h[1:]=transfer(f[1:],rs)*np.sinc(f[1:]/FS)*np.exp(-1j*np.pi*f[1:]/FS)
                v=lookup[q];raw=np.fft.rfft(v)/N
                assert abs(np.mean(v*v)-(abs(raw[0])**2+2*np.sum(abs(raw[1:-1])**2)+abs(raw[-1])**2))<1e-10
                sp=2*raw*h;fund=round(frequency*N/FS);hb=np.arange(2,20000//frequency+1)*fund
                denom=abs(sp[fund]);thd=100*np.linalg.norm(sp[hb])/denom
                mask=band.copy();mask[fund]=False;residual=np.linalg.norm(sp[mask])/denom
                rows.append(dict(frequency_hz=frequency,amplitude=amplitude,resistor_tolerance=tol,seed=seed,
                    thd_audio_band_percent=float(thd),inband_nontone_percent=float(residual*100),
                    sinad_quantization_and_static_db=float(-20*np.log10(residual)),
                    fundamental_peak_v=float(denom),harmonics_count=len(hb)))
                if frequency==1000 and tol==0:spectra[amplitude]=(f,sp)
    imd=[]
    for amplitude in (.9,.1,.01):
        q=np.floor(2047.5*(1+amplitude/2*(np.sin(2*np.pi*19000*t)+np.sin(2*np.pi*20000*t)))+.5).astype(int)
        for tol,seed,lookup,rs in networks:
            h=np.zeros(len(f),complex);h[1:]=transfer(f[1:],rs)*np.sinc(f[1:]/FS)
            sp=2*np.fft.rfft(lookup[q])/N*h
            bins=lambda hz:round(hz*N/FS)
            a,b=abs(sp[bins(19000)]),abs(sp[bins(20000)]);denom=np.hypot(a,b)
            mask=band.copy();mask[[bins(19000),bins(20000)]]=False
            imd.append(dict(amplitude=amplitude,resistor_tolerance=tol,seed=seed,
                difference_1khz_percent_per_mean_tone=float(100*abs(sp[bins(1000)])/((a+b)/2)),
                products_18_21khz_percent_rss_tones=float(100*np.hypot(abs(sp[bins(18000)]),abs(sp[bins(21000)]))/denom),
                inband_nontone_percent_rss_tones=float(100*np.linalg.norm(sp[mask])/denom)))
            if amplitude==.9 and tol==0:imd_spectrum=sp
    frequencies=np.geomspace(20,20000,300);gain=abs(transfer(frequencies))*np.sinc(frequencies/FS)
    response=[]
    for freq in (20,100,1000,10000,20000):
        response.append(dict(frequency_hz=freq,gain_db_relative_1khz=float(20*np.log10(abs(transfer(freq))*np.sinc(freq/FS)/(abs(transfer(1000))*np.sinc(1000/FS)))),
          output_impedance_magnitude_ohm=float(abs(impedance(freq))),damping_ratio_8ohm=float(8/abs(impedance(freq)))))
    load_response=[dict(load_ohm=l,gain_change_db_at_1khz=float(20*np.log10(abs(transfer(1000,load=l)/transfer(1000))))) for l in (4,8,16)]
    report=dict(sample_rate_hz=FS,samples=N,record_s=N/FS,rows=rows,two_tone=imd,response=response,load_response=load_response,
        scope='Exact static 3+9 resistor transfer table, 12-bit rounding, ideal uniform hold, linear LL1679/PP B; 100 pF/100 kohm assumed. No switch transients, nonlinear core, physical noise, dither or error feedback. Eight seeded networks per nonzero tolerance are examples, not worst-case limits.')
    (out/'spectral.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for frequency in (20,100,1000,5000):
        rr=[x for x in rows if x['frequency_hz']==frequency and x['resistor_tolerance']==0]
        axes[0,0].plot([20*np.log10(x['amplitude']) for x in rr],[x['inband_nontone_percent'] for x in rr],'o-',label=f'{frequency} Hz')
    axes[0,0].set(yscale='log',xlabel='Input amplitude (dBFS)',ylabel='In-band non-tone / signal (%)',title='All 20 Hz-20 kHz residual; no physical noise');axes[0,0].legend()
    for amplitude,(ff,sp) in spectra.items():
        hb=np.arange(1,21)*100
        axes[0,1].plot(ff[hb]/1000,20*np.log10(np.maximum(abs(sp[hb])/abs(sp[100]),1e-10)),'o-',markersize=3,label=f'{amplitude*100:g}% amplitude')
    axes[0,1].set(xlim=(0,20),ylim=(-120,5),xlabel='Frequency (kHz)',ylabel='dBc',title='1 kHz harmonic spectra');axes[0,1].legend()
    axes[1,0].semilogx(frequencies,20*np.log10(gain/(abs(transfer(1000))*np.sinc(1000/FS))))
    axes[1,0].set(xlabel='Frequency (Hz)',ylabel='Relative gain (dB)',title='Nominal frequency response including hold')
    axes[1,1].plot(f/1000,20*np.log10(np.maximum(abs(imd_spectrum)/max(abs(imd_spectrum)),1e-10)))
    axes[1,1].set(xlim=(0,25),ylim=(-120,5),xlabel='Frequency (kHz)',ylabel='dB relative to strongest tone',title='19 + 20 kHz, 90% combined peak envelope')
    for ax in axes.flat:ax.grid(alpha=.3)
    fig.tight_layout();fig.savefig(plots/'screen.png',dpi=150);plt.close(fig)
    print('PASS',len(rows),'single-tone records,',len(imd),'two-tone records',flush=True)
if __name__=='__main__':main()
