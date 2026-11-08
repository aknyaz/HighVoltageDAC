"""Static 12-bit binary parallel-DAC tolerance study; no device/thermal assumptions.

Endpoint-calibrated INL/DNL and explicit gain/offset. Uniform bounded resistor
errors are a scenario, not a manufacturing distribution or yield prediction.
"""
from pathlib import Path
import json
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
N=12
K=2**N
R=5274.699627701833
LOAD=10000.
VS=5.
SEED=20261108
TRIALS=5000
TOLERANCES=(.01,.005,.001,.0005,.0002,.0001,.00005,.00001)
NOMINAL=np.append(K*R/(2**np.arange(N)),K*R)
CODE_BITS=((np.arange(K)[:,None]>>np.arange(N))&1).astype(float)


def transfer(errors):
    """Return output offset and positive bit weights for shape (trials, 2, 13)."""
    conductance=1/(NOMINAL[None,None,:]*(1+errors))
    ga,gb=conductance[:,0,:],conductance[:,1,:]
    a=ga.sum(axis=1);b=gb.sum(axis=1)
    determinant=a*b+(a+b)/LOAD
    weights=VS*(b[:,None]*ga[:,:N]+a[:,None]*gb[:,:N])/determinant[:,None]
    offset=-VS*a*gb[:,:N].sum(axis=1)/determinant
    return offset,weights


def metrics(errors):
    offset,w=transfer(errors)
    lsb=w.sum(axis=1)/(K-1)
    deviations=w-lsb[:,None]*2**np.arange(N)
    # Every subset is a code. Positive and negative deviations sum to zero.
    max_inl=np.sum(abs(deviations),axis=1)/(2*lsb)
    carry_steps=w-np.column_stack((np.zeros(len(w)),np.cumsum(w[:,:-1],axis=1)))
    dnl=carry_steps/lsb[:,None]-1
    ideal_lsb=VS*2/K*LOAD/(LOAD+2*R)
    return dict(max_inl_lsb=max_inl,max_abs_dnl_lsb=np.max(abs(dnl),axis=1),
                min_step_lsb=np.min(carry_steps/lsb[:,None],axis=1),
                midpoint_step_lsb=carry_steps[:,-1]/lsb,
                gain_error_percent=100*(lsb/ideal_lsb-1),
                centered_offset_lsb=(offset+w.sum(axis=1)/2)/ideal_lsb)


def full_transfer(error):
    offset,w=transfer(np.asarray(error)[None,:,:])
    return offset[0]+CODE_BITS@w[0]


def direct_solve(error):
    ga,gb=1/(NOMINAL[None,:]*(1+error))
    matrix=np.array([[sum(ga)+1/LOAD,-1/LOAD],[-1/LOAD,sum(gb)+1/LOAD]])
    rhs=VS*np.array([CODE_BITS@ga[:N],(1-CODE_BITS)@gb[:N]])
    va,vb=np.linalg.solve(matrix,rhs)
    return va-vb


def corner(tolerance):
    # Weaken the MSB, strengthen every lower bit in both arms. Terminations nominal.
    e=np.zeros((2,N+1));e[:,:N-1]=-tolerance;e[:,N-1]=tolerance
    return e


def main():
    out=ROOT/'results/resistor_tolerance';out.mkdir(exist_ok=True)
    plots=ROOT/'plots/resistor_tolerance';plots.mkdir(exist_ok=True)
    rng=np.random.default_rng(SEED)
    rows=[];examples=[]
    for mode in ('independent','paired_same_error'):
        for tolerance in TOLERANCES:
            errors=rng.uniform(-tolerance,tolerance,(TRIALS,2,N+1))
            if mode=='paired_same_error':errors[:,1,:]=errors[:,0,:]
            m=metrics(errors)
            row=dict(mode=mode,tolerance_percent=100*tolerance,trials=TRIALS,
                     strictly_monotonic_percent=100*float(np.mean(m['min_step_lsb']>0)),
                     inl_within_half_lsb_percent=100*float(np.mean(m['max_inl_lsb']<=.5)),
                     inl_median_lsb=float(np.median(m['max_inl_lsb'])),
                     inl_p95_lsb=float(np.quantile(m['max_inl_lsb'],.95)),
                     inl_worst_observed_lsb=float(np.max(m['max_inl_lsb'])),
                     dnl_p95_max_abs_lsb=float(np.quantile(m['max_abs_dnl_lsb'],.95)),
                     minimum_observed_step_lsb=float(np.min(m['min_step_lsb'])),
                     gain_p95_abs_percent=float(np.quantile(abs(m['gain_error_percent']),.95)),
                     offset_p95_abs_lsb=float(np.quantile(abs(m['centered_offset_lsb']),.95)))
            rows.append(row)
            if mode=='independent' and tolerance in (.001,.0001):
                i=int(np.argmax(m['max_inl_lsb']))
                examples.append(dict(name=f'worst_observed_{100*tolerance:g}percent',error=errors[i].tolist(),
                                     description=f'Largest endpoint INL among {TRIALS} independent samples, +/-{100*tolerance:g}%'))
                if tolerance==.001:
                    j=int(np.argmin(m['min_step_lsb']))
                    examples.append(dict(name='smallest_step_0.1percent',error=errors[j].tolist(),
                                         description='Smallest observed code step among independent +/-0.1% samples'))
            print(f"{mode} +/-{100*tolerance:g}%: monotonic {row['strictly_monotonic_percent']:.2f}%, INL p95 {row['inl_p95_lsb']:.3f} LSB",flush=True)
    for tol in (.0002,.0005):
        examples.append(dict(name=f'corner_{100*tol:g}percent',error=corner(tol).tolist(),
                             description='MSB weak, lower bits strong, same in both arms'))
    examples.append(dict(name='ideal',error=np.zeros((2,N+1)).tolist(),description='Nominal network'))
    # Common drift is distinct from ratio mismatch: only gain/offset fitting should be required.
    common=np.full((1,2,N+1),.01)
    common_metrics={k:float(v[0]) for k,v in metrics(common).items()}
    assert common_metrics['max_inl_lsb']<1e-9
    assert metrics(corner(.999/(K-1))[None,:,:])['min_step_lsb'][0]>0
    assert metrics(corner(1.001/(K-1))[None,:,:])['min_step_lsb'][0]<0
    direct_error=0
    fig,axes=plt.subplots(2,1,figsize=(11,7))
    for ex in examples:
        error=np.array(ex['error']);v=full_transfer(error);reference=direct_solve(error)
        direct_error=max(direct_error,float(np.max(abs(v-reference))))
        lsb=(v[-1]-v[0])/(K-1)
        inl=(v-(v[0]+np.arange(K)*lsb))/lsb
        dnl=np.diff(v)/lsb-1
        fast=metrics(error[None,:,:])
        assert abs(np.max(abs(inl))-fast['max_inl_lsb'][0])<1e-8
        assert abs(np.max(abs(dnl))-fast['max_abs_dnl_lsb'][0])<1e-8
        ex['metrics']={k:float(value[0]) for k,value in fast.items()}
        if ex['name'].startswith('worst_observed'):
            axes[0].plot(np.arange(K),inl,label=ex['name'].replace('_',' '))
            axes[1].plot(np.arange(2038,2058),dnl[2038:2058],'.-',label=ex['name'].replace('_',' '))
    assert direct_error<1e-11
    axes[0].set(xlabel='Code',ylabel='Endpoint INL (LSB)')
    axes[1].axhline(-1,color='red',linestyle=':',label='Zero step (DNL = -1)')
    axes[1].set(xlabel='Starting code of transition',ylabel='DNL (LSB)')
    for ax in axes:ax.legend(fontsize=8);ax.grid(alpha=.3)
    fig.suptitle('12-bit binary parallel DAC | illustrative worst observed samples, not worst-case bounds')
    fig.tight_layout();fig.savefig(plots/'linearity_examples.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for mode in ('independent','paired_same_error'):
        selected=sorted([r for r in rows if r['mode']==mode],key=lambda r:r['tolerance_percent'])
        x=[r['tolerance_percent'] for r in selected]
        axes[0].plot(x,[r['strictly_monotonic_percent'] for r in selected],'o-',label=mode.replace('_',' '))
        axes[1].plot(x,[r['inl_p95_lsb'] for r in selected],'o-',label=mode.replace('_',' '))
    for ax in axes:ax.set_xscale('log');ax.set_xlabel('Bounded resistor tolerance (+/- %)');ax.grid(alpha=.3);ax.legend(fontsize=8)
    axes[0].set(ylabel='Strictly monotonic samples (%)',ylim=(-2,102))
    axes[1].set(ylabel='95th percentile of max |INL| (LSB)',yscale='log')
    axes[1].axhline(.5,color='red',linestyle=':',label='0.5 LSB')
    fig.suptitle('5000 simulated networks per point | uniform errors; not manufacturing yield')
    fig.tight_layout();fig.savefig(plots/'tolerance_summary.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.5))
    for ex in examples:
        if ex['name'] not in ('ideal','corner_0.02percent','corner_0.05percent','smallest_step_0.1percent'):continue
        v=full_transfer(np.array(ex['error']));lsb=(v[-1]-v[0])/(K-1)
        ax.plot(np.arange(2044,2052),(v[2044:2052]-v[0])/lsb-2047,'o-',label=ex['name'].replace('_',' '))
    ax.set(xlabel='Input code',ylabel='Endpoint-normalized output relative to code 2047 (LSB)',
           title='Midscale transition | a downward step violates monotonicity')
    ax.grid(alpha=.3);ax.legend(fontsize=8);fig.tight_layout()
    fig.savefig(plots/'midscale_transition.png',dpi=150);plt.close(fig)
    with (out/'summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    report=dict(bits=N,nominal_r_ohm=R,reflected_load_ohm=LOAD,simulation_supply_v=VS,
                seed=SEED,trials_per_point=TRIALS,distribution='Independent uniform bounded fractional resistance errors unless paired mode',
                total_random_networks=TRIALS*len(rows),strict_monotonicity_bound_percent=100/(K-1),
                independent_direct_node_max_error_v=direct_error,common_plus_one_percent=common_metrics,rows=rows,examples=examples)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Bound for guaranteed strictly positive binary carry steps: tolerance <',100/(K-1),'percent')


if __name__=='__main__':main()
