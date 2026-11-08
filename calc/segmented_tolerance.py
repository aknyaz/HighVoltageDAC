"""Static 12-bit 4+8 parallel-DAC mismatch, with explicit complementary decoding."""
from pathlib import Path
import json
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from resistor_tolerance import K,R,LOAD,VS,TRIALS,TOLERANCES
from compare_resistive import branches

ROOT=Path(__file__).resolve().parents[1]
FINE=8
COARSE=15
STEP=256
COUNT=23
SEED=20261109
WEIGHTS=np.concatenate((2**np.arange(FINE),np.full(COARSE,STEP)))
NOMINAL=np.append(K*R/WEIGHTS,K*R)
CODES=np.arange(K)
SA=branches(12,CODES,'segmented_parallel')[1]
SB=branches(12,K-1-CODES,'segmented_parallel')[1]


def transfer(errors):
    conductance=1/(NOMINAL[None,None,:]*(1+errors))
    ga,gb=conductance[:,0,:],conductance[:,1,:]
    a=ga.sum(axis=1);b=gb.sum(axis=1)
    determinant=a*b+(a+b)/LOAD
    fine=VS*(b[:,None]*ga[:,:FINE]+a[:,None]*gb[:,:FINE])/determinant[:,None]
    # Increasing coarse count turns on A[j] and turns OFF B[14-j], not B[j].
    coarse=VS*(b[:,None]*ga[:,FINE:COUNT]+a[:,None]*gb[:,FINE:COUNT][:,::-1])/determinant[:,None]
    offset=-VS*a*gb[:,:COUNT].sum(axis=1)/determinant
    return offset,fine,coarse


def metrics(errors):
    offset,fine,coarse=transfer(errors)
    lsb=(fine.sum(axis=1)+coarse.sum(axis=1))/(K-1)
    fine_dev=fine-lsb[:,None]*2**np.arange(FINE)
    coarse_dev=coarse-STEP*lsb[:,None]
    prefix=np.column_stack((np.zeros(len(lsb)),np.cumsum(coarse_dev,axis=1)))
    highest=np.max(prefix,axis=1)+np.sum(np.maximum(fine_dev,0),axis=1)
    lowest=np.min(prefix,axis=1)+np.sum(np.minimum(fine_dev,0),axis=1)
    max_inl=np.maximum(abs(highest),abs(lowest))/lsb
    fine_steps=fine-np.column_stack((np.zeros(len(lsb)),np.cumsum(fine[:,:-1],axis=1)))
    boundary_steps=coarse-fine.sum(axis=1)[:,None]
    steps=np.concatenate((fine_steps,boundary_steps),axis=1)/lsb[:,None]
    ideal_lsb=VS*2/K*LOAD/(LOAD+2*R)
    return dict(max_inl_lsb=max_inl,max_abs_dnl_lsb=np.max(abs(steps-1),axis=1),
                min_step_lsb=np.min(steps,axis=1),
                minimum_boundary_step_lsb=np.min(boundary_steps/lsb[:,None],axis=1),
                gain_error_percent=100*(lsb/ideal_lsb-1),
                endpoint_center_offset_lsb=(offset+(K-1)*lsb/2)/ideal_lsb)


def full_transfer(error):
    offset,fine,coarse=transfer(np.asarray(error)[None,:,:])
    prefix=np.concatenate(([0],np.cumsum(coarse[0])))
    return offset[0]+SA[:,:FINE]@fine[0]+prefix[CODES//STEP]


def direct_solve(error):
    ga,gb=1/(NOMINAL[None,:]*(1+error))
    matrix=np.array([[sum(ga)+1/LOAD,-1/LOAD],[-1/LOAD,sum(gb)+1/LOAD]])
    rhs=VS*np.array([SA@ga[:COUNT],SB@gb[:COUNT]])
    va,vb=np.linalg.solve(matrix,rhs)
    return va-vb


def corner(tolerance):
    e=np.zeros((2,COUNT+1))
    e[:,:FINE]=-tolerance
    e[:,FINE:COUNT]=tolerance
    return e


def main():
    out=ROOT/'results/segmented_tolerance';out.mkdir(exist_ok=True)
    plots=ROOT/'plots/segmented_tolerance';plots.mkdir(exist_ok=True)
    rng=np.random.default_rng(SEED);rows=[];examples=[]
    for mode in ('independent','paired_same_error'):
        for tolerance in TOLERANCES:
            errors=rng.uniform(-tolerance,tolerance,(TRIALS,2,COUNT+1))
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
                     offset_p95_abs_lsb=float(np.quantile(abs(m['endpoint_center_offset_lsb']),.95)))
            rows.append(row)
            if mode=='independent' and tolerance in (.001,.0001):
                i=int(np.argmax(m['max_inl_lsb']))
                examples.append(dict(name=f'worst_inl_{100*tolerance:g}percent',error=errors[i].tolist()))
            if mode=='independent' and tolerance==.005:
                i=int(np.argmin(m['min_step_lsb']))
                examples.append(dict(name='smallest_step_0.5percent',error=errors[i].tolist()))
            print(f"{mode} +/-{100*tolerance:g}%: monotonic {row['strictly_monotonic_percent']:.2f}%, INL p95 {row['inl_p95_lsb']:.3f} LSB",flush=True)
    for tolerance in (.001,.002):
        examples.append(dict(name=f'corner_{100*tolerance:g}percent',error=corner(tolerance).tolist()))
    examples.append(dict(name='ideal',error=np.zeros((2,COUNT+1)).tolist()))
    bound=1/(2*STEP-1)
    assert metrics(corner(.999*bound)[None,:,:])['min_step_lsb'][0]>0
    assert metrics(corner(1.001*bound)[None,:,:])['min_step_lsb'][0]<0
    common={key:float(value[0]) for key,value in metrics(np.full((1,2,COUNT+1),.01)).items()}
    assert common['max_inl_lsb']<1e-9
    max_error=0
    fig,axes=plt.subplots(2,1,figsize=(11,7))
    for ex in examples:
        error=np.array(ex['error']);v=full_transfer(error);direct=direct_solve(error)
        max_error=max(max_error,float(np.max(abs(v-direct))))
        lsb=(v[-1]-v[0])/(K-1)
        inl=(v-v[0]-CODES*lsb)/lsb;dnl=np.diff(v)/lsb-1
        fast=metrics(error[None,:,:])
        assert abs(np.max(abs(inl))-fast['max_inl_lsb'][0])<1e-8
        assert abs(np.max(abs(dnl))-fast['max_abs_dnl_lsb'][0])<1e-8
        ex['metrics']={key:float(value[0]) for key,value in fast.items()}
        if ex['name'].startswith('worst_inl'):
            axes[0].plot(CODES,inl,label=ex['name'].replace('_',' '))
            axes[1].plot(CODES[:-1],dnl,label=ex['name'].replace('_',' '),linewidth=.7)
    assert max_error<1e-11
    axes[0].set(xlabel='Code',ylabel='Endpoint INL (LSB)')
    axes[1].set(xlabel='Starting code of transition',ylabel='DNL (LSB)')
    for ax in axes:ax.grid(alpha=.3);ax.legend(fontsize=8)
    axes[1].axhline(-1,color='red',linestyle=':')
    fig.suptitle('4+8 segmented parallel DAC | selected worst-INL samples, not bounds')
    fig.tight_layout();fig.savefig(plots/'linearity_examples.png',dpi=150);plt.close(fig)
    binary=json.loads((ROOT/'results/resistor_tolerance/summary.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for dataset,architecture in [(binary['rows'],'Binary'),(rows,'Segmented 4+8')]:
        for mode in ('independent','paired_same_error'):
            chosen=sorted([r for r in dataset if r['mode']==mode],key=lambda r:r['tolerance_percent'])
            x=[r['tolerance_percent'] for r in chosen]
            style='o-' if mode=='independent' else 'x--'
            label=architecture+(' / independent' if mode=='independent' else ' / paired same index')
            axes[0].plot(x,[r['strictly_monotonic_percent'] for r in chosen],style,label=label)
            axes[1].plot(x,[r['inl_p95_lsb'] for r in chosen],style,label=label)
    for ax in axes:ax.set_xscale('log');ax.set_xlabel('Resistor bound (+/- %)');ax.grid(alpha=.3)
    axes[0].set(ylabel='Strictly monotonic samples (%)',ylim=(-2,102));axes[0].legend(fontsize=7)
    axes[1].set(ylabel='95th percentile max |INL| (LSB)',yscale='log');axes[1].axhline(.5,color='red',linestyle=':')
    fig.suptitle('5000 networks per point | uniform bounded errors, not manufacturing yield')
    fig.tight_layout();fig.savefig(plots/'binary_vs_segmented.png',dpi=150);plt.close(fig)
    with (out/'summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    report=dict(bits=12,segmentation='15 thermometer branches of weight 256 + 8 binary branches + grounded unit termination per arm',
                seed=SEED,trials_per_point=TRIALS,total_random_networks=TRIALS*len(rows),
                nominal_r_ohm=R,load_ohm=LOAD,supply_v=VS,strict_monotonicity_bound_percent=100*bound,
                independent_direct_max_error_v=max_error,common_plus_one_percent=common,rows=rows,examples=examples)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Strict monotonicity bound:',100*bound,'percent')


if __name__=='__main__':main()
