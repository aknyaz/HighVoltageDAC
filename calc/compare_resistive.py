"""Compare R-2R with explicit parallel binary and thermometer/binary branches."""
from pathlib import Path
import json
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from power_trade_study import pcm, fundamental_peak, write_csv

ROOT=Path(__file__).resolve().parents[1]


def branches(bits,codes,architecture):
    codes=np.asarray(codes)
    if architecture=='binary_parallel':
        weights=2**np.arange(bits)
        states=((codes[:,None]>>np.arange(bits))&1).astype(float)
    elif architecture=='segmented_parallel':
        upper=2 if bits==4 else 4
        lower=bits-upper
        weights=np.concatenate((2**np.arange(lower),np.full(2**upper-1,2**lower)))
        fine=((codes[:,None]>>np.arange(lower))&1)
        coarse=(codes[:,None]//2**lower>np.arange(2**upper-1)).astype(int)
        states=np.concatenate((fine,coarse),axis=1).astype(float)
    else:
        raise ValueError(architecture)
    assert np.array_equal(states@weights,codes)
    assert sum(weights)==2**bits-1
    return weights,states


def star_network(bits,codes,supply,r,load,architecture):
    maximum=2**bits-1
    weights,sa=branches(bits,codes,architecture)
    _,sb=branches(bits,maximum-np.asarray(codes),architecture)
    resistances=2**bits*r/weights
    ga=(sa/resistances).sum(axis=1)
    gb=(sb/resistances).sum(axis=1)
    matrix=np.array([[1/r+1/load,-1/load],[-1/load,1/r+1/load]])
    va,vb=np.linalg.solve(matrix,supply*np.array([ga,gb]))
    powers={}
    for side,v,states in [('a',va,sa),('b',vb,sb)]:
        for j,res in enumerate(resistances):
            powers[f'R{side}{j}']=(v-supply*states[:,j])**2/res
        # One always-grounded unit branch keeps Rout=R and exactly matches the R-2R code scale.
        powers[f'R{side}term']=v**2/(2**bits*r)
    heat=sum(powers.values())
    consumed=supply*(np.sum(sa*(supply-va[:,None])/resistances,axis=1)+np.sum(sb*(supply-vb[:,None])/resistances,axis=1))
    output=va-vb
    load_power=output**2/load
    np.testing.assert_allclose(consumed,heat+load_power,rtol=1e-12,atol=1e-8)
    expected=supply*(2*np.asarray(codes)-maximum)/2**bits*load/(load+2*r)
    np.testing.assert_allclose(output,expected,rtol=1e-10,atol=1e-9)
    return dict(output=output,heat=heat,supply=consumed,load=load_power,powers=powers,
                resistance=resistances,va=va,vb=vb)


def evaluate(base,architecture):
    bits=base['bits'];r=base['r_ohm'];supply=base['supply_v'];load=base['primary_load_ohm']
    result=star_network(bits,pcm(bits,base['pcm_amplitude']),supply,r,load,architecture)
    target=base['target_fundamental_w']
    assert abs(fundamental_peak(result['output'])**2/(2*load)/target-1)<1e-12
    hottest=max(result['powers'],key=lambda n:np.mean(result['powers'][n]))
    idle=star_network(bits,np.array([2**(bits-1)-1,2**(bits-1)]),supply,r,load,architecture)
    return dict(architecture=architecture,bits=bits,supply_v=supply,primary_load_ohm=load,
                target_fundamental_w=target,pcm_amplitude=base['pcm_amplitude'],r_ohm=r,
                heat_w=float(np.mean(result['heat'])),supply_power_w=float(np.mean(result['supply'])),
                total_load_power_w=float(np.mean(result['load'])),
                useful_efficiency_percent=100*target/float(np.mean(result['supply'])),
                switched_branches_per_arm=len(result['resistance']),
                spdt_total=2*len(result['resistance']),ideal_spst_total=4*len(result['resistance']),
                resistors_total=2*(len(result['resistance'])+1),
                minimum_branch_ohm=float(min(result['resistance'])),
                maximum_switched_branch_ohm=float(max(result['resistance'])),
                termination_ohm=2**bits*r,
                switched_resistance_ratio=float(max(result['resistance'])/min(result['resistance'])),
                hottest_resistor=hottest,hottest_resistor_average_w=float(np.mean(result['powers'][hottest])),
                idle_heat_w=float(np.mean(idle['heat'])))


def main():
    out=ROOT/'results/resistive_comparison';out.mkdir(exist_ok=True)
    plots=ROOT/'plots/resistive_comparison';plots.mkdir(exist_ok=True)
    with (ROOT/'results/power_study/sweep.csv').open() as f:
        base_rows=list(csv.DictReader(f))
    numeric=[]
    for row in base_rows:
        p={k:float(row[k]) for k in ('supply_v','primary_load_ohm','target_fundamental_w','pcm_amplitude','r_ohm')}
        p['bits']=int(row['bits']);numeric.append(p)
    rows=[]
    maximum_equivalence_error=0
    for base in numeric:
        a=evaluate(base,'binary_parallel');b=evaluate(base,'segmented_parallel')
        maximum_equivalence_error=max(maximum_equivalence_error,abs(a['heat_w']-b['heat_w'])/a['heat_w'])
        rows.extend((a,b))
    assert maximum_equivalence_error<1e-12
    original=json.loads((ROOT/'results/power_study/summary.json').read_text())
    cases=[]
    for old in original['cases']:
        identity={k:old[k] for k in ('bits','supply_v','primary_load_ohm','target_fundamental_w')}
        result=dict(**identity,status=old['status'])
        if 'best_sampled' in old:
            result['r2r']=old['best_sampled']
            for arch in ('binary_parallel','segmented_parallel'):
                options=[row for row in rows if row['architecture']==arch and all(row[k]==v for k,v in identity.items())]
                reserve=[row for row in options if row['pcm_amplitude']<=.9]
                result[arch]={'best_sampled':min(options,key=lambda row:row['heat_w']),
                              'best_with_reserve':min(reserve,key=lambda row:row['heat_w']) if reserve else None}
        cases.append(result)
    write_csv(out/'sweep.csv',rows)
    summary=dict(cases=cases,maximum_binary_segmented_relative_heat_difference=maximum_equivalence_error,
                 feasible_points=len(rows),segmentation={'4_bit':'2 thermometer MSBs + 2 binary LSBs',
                                                         '12_bit':'4 thermometer MSBs + 8 binary LSBs'})
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,target in zip(axes,(5,10)):
        chosen=[c for c in cases if c['bits']==12 and c['supply_v']==650 and c['target_fundamental_w']==target]
        for arch,label in [('r2r','R-2R'),('binary_parallel','Parallel binary'),('segmented_parallel','Parallel segmented (4+8)')]:
            values=[c['r2r']['ladder_heat_w'] if arch=='r2r' else c[arch]['best_sampled']['heat_w'] for c in chosen]
            ax.plot([c['primary_load_ohm']/1000 for c in chosen],values,marker='o' if arch!='segmented_parallel' else 'x',
                    linestyle='--' if arch=='segmented_parallel' else '-',label=label)
        ax.set(title=f'12 bits / 650 V / {target} W useful output',xlabel='Reflected primary load (kohm)',ylabel='Resistor heat (W)',yscale='log')
        ax.grid(alpha=.3);ax.legend(fontsize=8)
    fig.suptitle('Best sampled ideal cases | parallel binary and segmented overlap')
    fig.tight_layout();fig.savefig(plots/'heat_comparison.png',dpi=150);plt.close(fig)
    for c in cases:
        if c['bits']==12 and c['supply_v']==650 and 'r2r' in c:
            b=c['binary_parallel']['best_sampled'];s=c['segmented_parallel']['best_sampled']
            print(c['target_fundamental_w'],c['primary_load_ohm'], 'R2R',round(c['r2r']['ladder_heat_w'],2),'binary',round(b['heat_w'],2),'segmented',round(s['heat_w'],2),'eff',round(b['useful_efficiency_percent'],2),'a',b['pcm_amplitude'])


if __name__=='__main__':main()
