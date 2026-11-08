"""Equal-fundamental-power study of complete complementary voltage-mode R-2R ladders.

Exact linear nodal solutions per PCM code; ideal voltage switching and an ideal
transformer reflected resistance. No real HV device or transformer claims.
"""
from pathlib import Path
import json
import csv
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
FS=192000
F0=1000
SAMPLES=FS//F0
SUPPLIES=(600,650,700)
LOADS=(5000,10000,20000)
POWERS=(5,10)
BITS=(4,12)


def pcm(bits, amplitude):
    maximum=2**bits-1
    half=np.floor(maximum/2*(1+amplitude*np.sin(2*np.pi*(np.arange(SAMPLES//2)+.5)/SAMPLES))+.5).astype(int)
    return np.concatenate((half,maximum-half))


def fundamental_peak(values):
    # Exact Fourier coefficient of the zero-order-held periodic sequence.
    return float(2*abs(np.fft.rfft(values)[1])/len(values)*np.sinc(1/len(values)))


def unloaded(bits, codes):
    bit_values=((codes[:,None]>>np.arange(bits))&1).astype(float)
    conductance=np.eye(bits)*.5
    conductance[0,0]+=.5  # LSB 2R termination
    for b in range(1,bits):
        conductance[b,b]+=1
        conductance[b-1,b-1]+=1
        conductance[b,b-1]-=1
        conductance[b-1,b]-=1
    inv=np.linalg.inv(conductance)
    va=bit_values@inv.T*.5
    vb=(1-bit_values)@inv.T*.5
    expected=(2*codes-(2**bits-1))/2**bits
    assert np.max(abs((va[:,-1]-vb[:,-1])-expected))<1e-12
    assert abs(inv[-1,-1]-1)<1e-12
    return bit_values,va,vb,inv[:,-1]


def network(bits,codes,supply_v,r_ohm,load_ohm):
    """Full node voltages, every resistor's heat, and supply/load powers per code."""
    states,ua,ub,response=unloaded(bits,np.asarray(codes))
    load_ratio=load_ohm/r_ohm
    differential=(ua[:,-1]-ub[:,-1])*load_ratio/(load_ratio+2)
    current=differential/load_ratio
    va=ua-current[:,None]*response
    vb=ub+current[:,None]*response
    resistor_heat={}
    for side,nodes,drives in [('a',va,states),('b',vb,1-states)]:
        for bit in range(bits):
            resistor_heat[f'R{side}{bit}v']=(nodes[:,bit]-drives[:,bit])**2/2
            if bit:
                resistor_heat[f'R{side}{bit}h']=(nodes[:,bit]-nodes[:,bit-1])**2
        resistor_heat[f'R{side}term']=nodes[:,0]**2/2
    factor=supply_v**2/r_ohm
    resistor_heat={name:heat*factor for name,heat in resistor_heat.items()}
    heat=sum(resistor_heat.values())
    supply=(np.sum(states*(1-va),axis=1)+np.sum((1-states)*(1-vb),axis=1))*.5*factor
    output=differential*supply_v
    load=output**2/load_ohm
    assert np.max(abs(supply-heat-load))<1e-8*max(1,float(np.max(supply)))
    return dict(output_v=output,supply_w=supply,heat_w=heat,load_w=load,
                resistor_heat_w=resistor_heat,va=va*supply_v,vb=vb*supply_v)


def evaluate(bits,supply,load,target,amplitude):
    codes=pcm(bits,amplitude)
    un=(2*codes-(2**bits-1))/2**bits
    source_peak=fundamental_peak(un)*supply
    requested_peak=math.sqrt(2*target*load)
    r=load/2*(source_peak/requested_peak-1)
    if r<=0:
        return None
    result=network(bits,codes,supply,r,load)
    actual_fundamental=fundamental_peak(result['output_v'])**2/(2*load)
    assert abs(actual_fundamental/target-1)<1e-12
    total_load=float(np.mean(result['load_w']))
    supply_w=float(np.mean(result['supply_w']))
    heat=float(np.mean(result['heat_w']))
    states,ua,ub,_=unloaded(bits,codes)
    internal_no_load=float(np.mean((np.sum(states*(1-ua),axis=1)+np.sum((1-states)*(1-ub),axis=1))*.5)*supply**2/r)
    series_loss=total_load*2*r/load
    assert abs(heat-internal_no_load-series_loss)<1e-8*max(heat,1)
    atten=load/(load+2*r)
    available_code_peak=supply*(2**bits-1)/2**bits*atten
    full_scale_codes=pcm(bits,1)
    full_scale_peak=fundamental_peak((2*full_scale_codes-(2**bits-1))/2**bits)*supply*atten
    max_resistor=max(result['resistor_heat_w'],key=lambda name: np.mean(result['resistor_heat_w'][name]))
    # Alternating the two midpoint codes is a zero-mean idle sequence, not a quiet DC code.
    idle=network(bits,np.array([2**(bits-1)-1,2**(bits-1)]),supply,r,load)
    return dict(bits=bits,supply_v=supply,primary_load_ohm=load,target_fundamental_w=target,
                pcm_amplitude=round(float(amplitude),6),r_ohm=r,two_r_ohm=2*r,
                differential_source_ohm=2*r,attenuation=atten,
                required_source_fundamental_peak_v=source_peak,
                primary_fundamental_peak_v=requested_peak,
                loaded_code_endpoint_v=available_code_peak,
                endpoint_minus_fundamental_peak_v=available_code_peak-requested_peak,
                command_reserve_fraction=1-float(amplitude),
                max_fundamental_power_at_same_r_w=full_scale_peak**2/(2*load),
                fundamental_power_w=actual_fundamental,total_load_power_w=total_load,
                nonfundamental_load_power_w=total_load-actual_fundamental,
                ladder_heat_w=heat,supply_power_w=supply_w,
                unloaded_internal_heat_w=internal_no_load,equivalent_series_heat_w=series_loss,
                useful_efficiency_percent=100*target/supply_w,
                primary_rms_a=math.sqrt(total_load/load),
                primary_peak_a=float(np.max(abs(result['output_v']))/load),
                secondary_rms_a=math.sqrt(total_load/8),turns_ratio=math.sqrt(load/8),
                hottest_resistor=max_resistor,
                hottest_resistor_average_w=float(np.mean(result['resistor_heat_w'][max_resistor])),
                midpoint_idle_ladder_heat_w=float(np.mean(idle['heat_w'])),
                midpoint_idle_load_power_w=float(np.mean(idle['load_w'])))


def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main():
    all_rows=[]
    cases=[]
    # Grid search is explicitly not a proof of a continuous global optimum.
    amplitudes=np.linspace(.05,1,191)
    for bits in BITS:
        for target in POWERS:
            for supply in SUPPLIES:
                for load in LOADS:
                    rows=[row for a in amplitudes if (row:=evaluate(bits,supply,load,target,a)) is not None]
                    all_rows.extend(rows)
                    identity=dict(bits=bits,supply_v=supply,primary_load_ohm=load,target_fundamental_w=target)
                    if not rows:
                        cases.append(dict(**identity,status='infeasible_even_at_zero_source_resistance'))
                        continue
                    best=min(rows,key=lambda row:row['ladder_heat_w'])
                    # Keep margin from the sine command limit as a separate practical comparison.
                    reserve=[row for row in rows if row['pcm_amplitude']<=.9]
                    best_reserve=min(reserve,key=lambda row:row['ladder_heat_w']) if reserve else None
                    cases.append(dict(**identity,status='feasible_ideal_model',best_sampled=best,
                                      best_with_10_percent_command_reserve=best_reserve))
    (ROOT/'results/power_study').mkdir(exist_ok=True)
    (ROOT/'plots/power_study').mkdir(exist_ok=True)
    write_csv(ROOT/'results/power_study/sweep.csv',all_rows)
    write_csv(ROOT/'results/power_study/best_cases.csv',[c['best_sampled'] for c in cases if 'best_sampled' in c])
    summary=dict(supply_targets_v=SUPPLIES,primary_loads_ohm=LOADS,targets_w=POWERS,bits=BITS,
                 amplitude_grid=dict(start=.05,stop=1,step=.005),feasible_grid_points=len(all_rows),cases=cases)
    (ROOT/'results/power_study/summary.json').write_text(json.dumps(summary,indent=2)+'\n')

    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for ax,target in zip(axes,POWERS):
        for bits in BITS:
            for supply in SUPPLIES:
                ys=[]
                for load in LOADS:
                    case=next(c for c in cases if (c['bits'],c['supply_v'],c['primary_load_ohm'],c['target_fundamental_w'])==(bits,supply,load,target))
                    ys.append(case.get('best_sampled',{}).get('ladder_heat_w',float('nan')))
                ax.plot(np.array(LOADS)/1000,ys,marker='o',linestyle='-' if bits==12 else '--',label=f'{bits} bits, {supply} V')
        ax.set(title=f'{target} W useful sine power',xlabel='Reflected primary load (kohm)',ylabel='Total ladder heat (W)',yscale='log')
        ax.grid(True,which='both',alpha=.3)
    axes[0].legend(fontsize=8); fig.suptitle('Best sampled ideal R-2R cases | missing markers = infeasible | no device/transformer losses')
    fig.tight_layout(); fig.savefig(ROOT/'plots/power_study/equal_power_heat.png',dpi=160); plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for ax,target in zip(axes,POWERS):
        for bits in BITS:
            for load in LOADS:
                rows=[r for r in all_rows if (r['bits'],r['supply_v'],r['primary_load_ohm'],r['target_fundamental_w'])==(bits,650,load,target)]
                ax.plot([r['r_ohm']/1000 for r in rows],[r['ladder_heat_w'] for r in rows],linestyle='-' if bits==12 else '--',label=f'{bits} bits, {load/1000:g} kohm')
        ax.set(title=f'650 V / {target} W useful sine power',xlabel='Ladder R (kohm)',ylabel='Total ladder heat (W)',yscale='log',ylim=(60,5000))
        ax.grid(alpha=.3)
    axes[0].legend(fontsize=8);fig.suptitle('Equal useful output | 60-5000 W display range; full sweep in CSV')
    fig.tight_layout();fig.savefig(ROOT/'plots/power_study/resistance_tradeoff.png',dpi=160);plt.close(fig)
    selected=[next(c['best_sampled'] for c in cases if
                  (c['bits'],c['supply_v'],c['primary_load_ohm'],c['target_fundamental_w'])==spec)
              for spec in [(4,650,10000,5),(12,650,10000,5),(12,650,5000,10)]]
    fig,ax=plt.subplots(figsize=(9,5))
    bottom=np.zeros(3)
    for key,label in [('fundamental_power_w','Useful 1 kHz load power'),
                      ('nonfundamental_load_power_w','Other load power (harmonics/images)'),
                      ('equivalent_series_heat_w','Equivalent source series heat'),
                      ('unloaded_internal_heat_w','Internal ladder heat at no load')]:
        values=np.array([r[key] for r in selected])
        ax.bar(np.arange(3),values,bottom=bottom,label=label)
        bottom+=values
    for x,total in enumerate(bottom):ax.text(x,total+4,f'{total:.1f} W',ha='center')
    ax.set_xticks(np.arange(3),['4 bits / 5 W / 10 kohm','12 bits / 5 W / 10 kohm','12 bits / 10 W / 5 kohm'])
    ax.set(ylabel='Supply power allocation (W)',title='650 V equivalent | best sampled ideal cases',ylim=(0,430))
    ax.legend(fontsize=8,loc='upper left');fig.tight_layout()
    fig.savefig(ROOT/'plots/power_study/power_breakdown.png',dpi=160);plt.close(fig)
    print('Feasible grid points:',len(all_rows))
    for c in cases:
        if c['supply_v']==650:
            best=c.get('best_sampled')
            print(c['bits'],c['target_fundamental_w'],c['primary_load_ohm'],
                  f"R={best['r_ohm']:.1f} ohm heat={best['ladder_heat_w']:.2f} W eff={best['useful_efficiency_percent']:.3f}% a={best['pcm_amplitude']}" if best else 'INFEASIBLE')


if __name__=='__main__':
    main()
