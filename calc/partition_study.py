"""Bounded 12-bit partition comparison and explicit baseline decision."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from resistor_tolerance import R,LOAD,VS,K
from sic_charge import integrals
ROOT=Path(__file__).resolve().parents[1]

def weights(coarse):
    fine=12-coarse
    return np.r_[2.**np.arange(fine),np.full(2**coarse-1,2.**fine)]

def decode(coarse,codes):
    codes=np.asarray(codes);fine=12-coarse
    return np.column_stack(((codes[:,None]>>np.arange(fine))&1,
                            codes[:,None]//2**fine>np.arange(2**coarse-1)))

def metrics(coarse,error):
    fine=12-coarse;w=weights(coarse);n=len(w)
    g=1/(np.r_[K*R/w,K*R][None,None,:]*(1+error))
    ga,gb=g[:,0],g[:,1];a=ga.sum(1);b=gb.sum(1)
    det=a*b+(a+b)/LOAD
    f=VS*(b[:,None]*ga[:,:fine]+a[:,None]*gb[:,:fine])/det[:,None]
    c=VS*(b[:,None]*ga[:,fine:n]+a[:,None]*gb[:,fine:n][:,::-1])/det[:,None]
    lsb=(f.sum(1)+c.sum(1))/(K-1)
    fd=f-lsb[:,None]*2.**np.arange(fine)
    prefix=np.column_stack((np.zeros(len(error)),np.cumsum(c-lsb[:,None]*2**fine,axis=1)))
    hi=prefix.max(1)+np.maximum(fd,0).sum(1)
    lo=prefix.min(1)+np.minimum(fd,0).sum(1)
    steps=np.column_stack((f-np.column_stack((np.zeros(len(error)),np.cumsum(f[:,:-1],axis=1))),c-f.sum(1)[:,None]))
    return np.maximum(abs(hi),abs(lo))/lsb,steps.min(1)/lsb

def direct(coarse,error):
    w=weights(coarse);g=1/(np.r_[K*R/w,K*R][None,:]*(1+error));a,b=g.sum(1)
    codes=np.arange(K)
    rhs=VS*np.array([decode(coarse,codes)@g[0,:-1],decode(coarse,K-1-codes)@g[1,:-1]])
    va,vb=np.linalg.solve([[a+1/LOAD,-1/LOAD],[-1/LOAD,b+1/LOAD]],rhs)
    return va-vb

def main():
    out=ROOT/'results/partition_study';out.mkdir(parents=True,exist_ok=True)
    plots=ROOT/'plots/partition_study';plots.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(20261110);rows=[];examples=[]
    for coarse in range(7):
        w=weights(coarse);n=len(w);fine=12-coarse
        carry=int(max(w));bound=1/(2*carry-1)
        trials=[]
        for tol in (.0001,.0005,.001):
            for mode in ('independent','paired_same_index'):
                error=rng.uniform(-tol,tol,(5000,2,n+1))
                if mode=='paired_same_index':error[:,1]=error[:,0]
                inl,step=metrics(coarse,error)
                trials.append(dict(tolerance_percent=tol*100,mode=mode,inl_p95_lsb=float(np.quantile(inl,.95)),
                                   worst_inl_lsb=float(max(inl)),monotonic_percent=float(np.mean(step>0)*100),
                                   half_lsb_percent=float(np.mean(inl<=.5)*100)))
                if tol==.0001 and mode=='independent':
                    ex=error[np.argmax(inl)];v=direct(coarse,ex);lsb=(v[-1]-v[0])/(K-1)
                    assert abs(max(abs((v-v[0])/lsb-np.arange(K)))-max(inl))<1e-8
                    assert abs(min(np.diff(v)/lsb)-metrics(coarse,ex[None])[1][0])<1e-8
                    examples.append(dict(coarse_bits=coarse,error=ex.tolist()))
        budget=[]
        for amp in (.1,.5,1.):
            codes=np.rint(2047.5+2047.5*amp*np.sin(2*np.pi*np.arange(192)/192)).astype(int)
            state=np.stack((decode(coarse,codes),decode(coarse,K-1-codes)),axis=1)
            toggles=int(np.sum(state!=np.roll(state,1,axis=0)))
            cap=toggles*1000*650*integrals(650)[0];gate=toggles*1000*19e-9*19
            bias=2*n*.1628
            budget.append(dict(amplitude=amp,toggles_per_ms=toggles,capacitive_w=cap,gate_w=gate,
                               driver_bias_w=bias,switch_and_driver_w=cap+gate+bias))
        rows.append(dict(coarse_bits=coarse,fine_bits=fine,branches_per_arm=n,transistors=4*n,
                         ideal_adjacent_glitch_lsb=carry,monotonic_bound_percent=100*bound,
                         resistor_span=float(max(w)),trials=trials,budgets=budget))
    # Explicit engineering compromise, not a user requirement or global optimum.
    eligible=[r for r in rows if r['ideal_adjacent_glitch_lsb']<=512 and r['transistors']<=64
              and all(t['inl_p95_lsb']<.1 and t['monotonic_percent']==100 for t in r['trials'] if t['tolerance_percent']==.01)]
    assert len(eligible)==1 and eligible[0]['coarse_bits']==3
    report=dict(seed=20261110,trials_per_case=5000,total_random_networks=210000,
                selected_coarse_bits=3,selection='Working 3+9 baseline, not final hardware qualification',rows=rows,examples=examples)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    labels=[f'{r["coarse_bits"]}+{r["fine_bits"]}' for r in rows]
    axes[0].plot(labels,[r['transistors'] for r in rows],'o-',label='Transistors');axes[0].set_ylabel('Count');axes[0].set_title('Thermometer bits + binary bits')
    axes[1].plot(labels,[r['budgets'][-1]['switch_and_driver_w'] for r in rows],'o-');axes[1].set_ylabel('Estimated switch + driver loss (W)');axes[1].set_title('650 V, full-range 1 kHz, 192 kS/s')
    for ax in axes:ax.axvline(3,color='green',alpha=.4,label='Selected 3+9');ax.grid(alpha=.3);ax.legend()
    fig.tight_layout();fig.savefig(plots/'partitions.png',dpi=150);plt.close(fig)
    for r in rows:print(r['coarse_bits'],r['transistors'],r['ideal_adjacent_glitch_lsb'],r['trials'][0]['inl_p95_lsb'],r['trials'][1]['inl_p95_lsb'],r['budgets'][-1]['switch_and_driver_w'])

if __name__=='__main__':main()
