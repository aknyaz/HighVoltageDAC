"""Bounded equal-output heat and continuous supply-tracking study.

No regulator design, switching replay or physical HV implementation.
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from controller_analog import ROOT, decode, weights
from low_frequency_mute import LP, LS, M, RS, RC, C
from ngspice_shared import NgSpice

OUT=ROOT/'results/supply_tracking'
GEN=ROOT/'sim/generated/supply_tracking'
PLOTS=ROOT/'plots/supply_tracking'
STOP=1.0


def thermal():
    # Purchased single-value candidate: preserve its exact 5281.25 ohm arm R.
    arm_r=5281.25
    resistors=np.r_[4096*arm_r/weights(3),4096*arm_r]
    g=1/resistors
    rows=[]
    for amplitude in (.1,.01,.001):
        for bus in (650.,100.):
            use=amplitude*650/bus
            q=np.floor(2047.5*(1+use*np.sin(2*np.pi*(np.arange(192)+.5)/192))+.5).astype(int)
            assert q.min()>=0 and q.max()<=4095
            states=np.stack([np.c_[decode(3,q),np.zeros(192)],
                             np.c_[decode(3,4095-q),np.zeros(192)]])
            rail=bus*states
            source=np.sum(rail*g,axis=2)*arm_r
            current=(source[0]-source[1])/(10000+2*arm_r)
            nodes=np.stack([source[0]-current*arm_r,source[1]+current*arm_r])
            branch_power=(rail-nodes[:,:,None])**2*g
            heat=branch_power.sum(axis=(0,2))
            supply=np.sum(rail*(rail-nodes[:,:,None])*g,axis=(0,2))
            load=current**2*10000
            error=float(np.max(abs(supply-heat-load)))
            assert error<1e-10
            rows.append(dict(reference_amplitude_650_v=amplitude,bus_v=bus,
                code_amplitude=use,array_heat_w=float(heat.mean()),
                load_power_w=float(load.mean()),supply_power_w=float(supply.mean()),
                peak_arm_heat_w=float(branch_power.sum(axis=2).max()),
                power_balance_max_error_w=error))
    return dict(arm_resistance_ohm=arm_r,load_ohm=10000,rows=rows,
        scope='Exact nominal static branch power over a 192-sample 1 kHz cycle. 3052-chip candidate equivalent resistances, ideal switches and resistive 10 kohm load; no transformer/driver/supply losses or thermal transient.')


def deck(frequency,tau,feedback,step_us):
    # RC is a bounded first-order response assumption, not a converter design.
    lines=['Supply tracking / continuous differential equivalent / simulation only',
        'Vcmd cmd 0 PWL(0 650 .1 650 .3 100 .5 100 .7 650 1 650)',
        'Rlag cmd actual 1',f'Clag actual 0 {tau}',
        '.options reltol=1e-8 abstol=1e-14 method=gear']
    scale='actual' if feedback else 'cmd'
    lines += [f'Bdrive drive 0 V=6.5*sin(2*pi*{frequency}*time)*v(actual)/v({scale})',
              f'Bideal ideal 0 V=6.5*sin(2*pi*{frequency}*time)']
    for tag,src in (('a','drive'),('b','ideal')):
        lines += [f'Rsrc{tag} {src} p{tag} {RS:.15g}',
            f'Lp{tag} p{tag} 0 {LP}',f'Ls{tag} s{tag} 0 {LS:.15g}',
            f'K{tag} Lp{tag} Ls{tag} {M/np.sqrt(LP*LS):.15g}',
            f'Rsec{tag} s{tag} o{tag} .2',f'Rload{tag} o{tag} 0 8',
            f'Rcore{tag} p{tag} 0 {RC}',f'Cpri{tag} p{tag} 0 {C}']
    lines += ['.save v(cmd) v(actual) v(drive) v(ideal) v(oa) v(ob) i(Lpa) i(Lsa) i(Lpb) i(Lsb)',
              f'.tran {step_us}u {STOP} 0 {step_us}u','.end']
    return '\n'.join(lines)+'\n'


def analytic_bus(t,tau):
    # Exact first-order response to a sum of delayed slope changes.
    value=np.full_like(t,650.)
    for when,slope in ((.1,-2750),(.3,2750),(.5,2750),(.7,-2750)):
        z=np.maximum(t-when,0)
        value+=slope*(z-tau*(-np.expm1(-z/tau)))
    return value


def main():
    for path in (OUT,GEN,PLOTS):path.mkdir(parents=True,exist_ok=True)
    heat=thermal()
    (OUT/'thermal.json').write_text(json.dumps(heat,indent=2)+'\n')
    spice=NgSpice();rows=[];curves={}
    for frequency in (20,1000):
        for tau in (.01,.05):
            for feedback in (False,True):
                checks=[]
                for step in (20,10):
                    name=f'f{frequency}_tau{tau:g}_feedback{int(feedback)}_{step}us'
                    net=deck(frequency,tau,feedback,step)
                    (GEN/(name+'.cir')).write_text(net);spice.run(net)
                    t=spice.vector('time');assert t[-1]>=STOP-1e-10
                    tr={key:spice.vector(key) for key in ('cmd','actual','drive','ideal','oa','ob','lpa#branch','lsa#branch','lpb#branch','lsb#branch')}
                    rail_error=float(np.max(abs(tr['actual']-analytic_bus(t,tau))))
                    assert rail_error<.01,(name,rail_error)
                    mask=t>=.1
                    error=tr['oa']-tr['ob']
                    nominal=float(np.max(abs(tr['ob'][mask])))
                    flux_error=LP*(tr['lpa#branch']-tr['lpb#branch'])+M*(tr['lsa#branch']-tr['lsb#branch'])
                    ratio=tr['actual']/tr['cmd'] if not feedback else np.ones_like(t)
                    row=dict(frequency_hz=frequency,lag_s=tau,actual_voltage_feedback=feedback,
                        output_error_peak_v=float(np.max(abs(error[mask]))),
                        output_error_peak_percent=float(100*np.max(abs(error[mask]))/nominal),
                        gain_ratio_min=float(ratio[mask].min()),gain_ratio_max=float(ratio[mask].max()),
                        differential_source_mean_v=float(np.trapezoid((tr['drive']-tr['ideal'])[mask],t[mask])/(STOP-.1)),
                        flux_linkage_error_peak_wb_turn=float(np.max(abs(flux_error[mask]))),
                        analytic_rail_max_error_v=rail_error,
                        max_code_amplitude=float(np.max(6.5/(tr['actual'] if feedback else tr['cmd']))))
                    checks.append(row)
                    (OUT/(name+'.log')).write_text('\n'.join(line.rstrip() for msg in spice.log for line in msg.splitlines())+'\n');spice.log.clear()
                delta=abs(checks[0]['output_error_peak_v']-checks[1]['output_error_peak_v'])
                assert delta<max(2e-6,checks[1]['output_error_peak_v']*.005),(name,delta)
                if feedback:assert row['output_error_peak_v']<1e-8
                row['timestep_peak_error_difference_v']=delta
                rows.append(row)
                print(json.dumps(row),flush=True)
                if frequency==1000:curves[tau,feedback]=(t,tr,error)
    report=dict(date='2026-11-24',spice_runs=16,thermal=heat,tracking=rows,
        scope='Continuous unquantized Thevenin source, linear LL1679. Constant desired 6.5 V peak differential source while rail ramps 650->100->650 V, 200 ms per ramp. First-order 10/50 ms supply lag. Perfect instantaneous actual-voltage knowledge in feedback control case. No switch replay, 12-bit rounding, ADC delay/noise, supply ripple, rail load coupling or real converter model. Transient peak error is not THD; linkage is not flux density or saturation qualification.')
    (OUT/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(3,1,figsize=(10,9),sharex=True)
    for tau in (.01,.05):
        t,tr,error=curves[tau,False]
        stride=max(1,len(t)//5000)
        axes[0].plot(t[::stride],tr['actual'][::stride],label=f'Actual, lag {tau*1000:g} ms')
        axes[1].plot(t[::stride],(tr['actual']/tr['cmd'])[::stride],label=f'Command scaling, {tau*1000:g} ms')
        axes[2].plot(t[::stride],error[::stride]*1000,label=f'Command scaling, {tau*1000:g} ms')
    axes[0].plot(t[::stride],tr['cmd'][::stride],'k--',label='Command')
    axes[1].axhline(1,color='green',linestyle='--',label='Perfect actual-voltage scaling')
    axes[0].set(ylabel='Supply (V)',title='Fixed audio target during slow supply ramps: assumed regulator lag')
    axes[1].set(ylabel='Source amplitude ratio')
    axes[2].set(ylabel='Output error (mV)',xlabel='Time (s)')
    for ax in axes:ax.grid(alpha=.3);ax.legend()
    fig.tight_layout();fig.savefig(PLOTS/'tracking.png',dpi=150);plt.close(fig)
    print('PASS thermal power balance and 16 tracking SPICE runs',flush=True)


if __name__=='__main__':main()
