"""Approximate typical Coss curve integration and driver budget, not a vendor model."""
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sim'))
from compare_switching_glitches import decode

# Manually read from C3M0350120D Rev 04, page 5, Figures 17/18.
# Rounded visual samples, not measured data. Piecewise-linear C, integrated Q.
V=np.array([0,5,10,15,20,30,40,50,75,100,150,200,300,400,600,800,1000,1200.])
C=np.array([350,180,140,110,95,77,64,57,47,41,33,30,25,22,20,20,20,20.])*1e-12


def integrals(voltage):
    q=e=0.
    for a,b,ca,cb in zip(V[:-1],V[1:],C[:-1],C[1:]):
        length=max(0.,min(voltage,b)-a)
        slope=(cb-ca)/(b-a)
        q+=ca*length+slope*length**2/2
        e+=a*ca*length+(ca+a*slope)*length**2/2+slope*length**3/3
    return q,e


def charge_expression(node,scale):
    # Qscaled(v) = Qphysical(scale*v)/scale; differentiation yields Cphysical(scale*v).
    terms=[f'{C[0]:.15g}*min({scale:.15g}*v({node}),0)',
           f'{C[-1]:.15g}*max({scale:.15g}*v({node})-{V[-1]:.15g},0)']
    for a,b,ca,cb in zip(V[:-1],V[1:],C[:-1],C[1:]):
        x=f'min(max(({scale:.15g}*v({node})-{a:.15g}),0),{b-a:.15g})'
        terms.append(f'({ca:.15g}*({x})+{(cb-ca)/(b-a)/2:.15g}*({x})^2)')
    return '('+'+'.join(terms)+f')/{scale:.15g}'


def main():
    out=ROOT/'results/sic_charge';out.mkdir(parents=True,exist_ok=True)
    plots=ROOT/'plots/sic_charge';plots.mkdir(parents=True,exist_ok=True)
    rows=[]
    for supply in (600,650,700,1000):
        q,e=integrals(supply)
        rows.append(dict(supply_v=supply,qoss_nc=q*1e9,eoss_uj=e*1e6,
                         halfbridge_hard_transition_uj=supply*q*1e6,charge_equivalent_pf=q/supply*1e12))
    budgets=[]
    for kind,count in (('binary',24),('segmented',46)):
        for amplitude in (0.,.1,.5,1.):
            codes=np.rint(2047.5+2047.5*amplitude*np.sin(2*np.pi*np.arange(192)/192)).astype(int)
            states=np.array([[decode(kind,int(c)),decode(kind,4095-int(c))] for c in codes])
            toggles=int(np.sum(states!=np.roll(states,1,axis=0)))
            cap=toggles*1000*650*integrals(650)[0]
            # One turn-on per node transition, not two gate-charge cycles.
            gate=toggles*1000*19e-9*19
            # Reference architecture: one UCC21750 per FET, 3.3 V logic, +15/-4 V output.
            # One high and one low driver per half bridge; typical DC currents.
            quiescent=count*(3.3*(.003+.002)+19*(.004+.0037))
            budgets.append(dict(architecture=kind,amplitude=amplitude,toggles_per_ms=toggles,
                                coss_loss_w=cap,coss_sensitivity_low_w=.75*cap,coss_sensitivity_high_w=1.25*cap,
                                gate_charge_w=gate,driver_quiescent_w=quiescent,
                                floating_high_side_domains=count,driver_channels=2*count,
                                auxiliary_output_w=gate+quiescent))
    report=dict(provenance='Manual approximate typical Coss samples: C3M0350120D Rev 04 Fig 17/18',
                capacitance_points=list(zip(V.tolist(),(C*1e12).tolist())),voltage_rows=rows,budgets=budgets,
                eoss_1000v_difference_from_10p6uj_percent=100*(integrals(1000)[1]/10.6e-6-1))
    assert abs(report['eoss_1000v_difference_from_10p6uj_percent'])<15
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    grid=np.linspace(0,1200,401)
    axes[0].semilogy(V,C*1e12,'o-');axes[0].set(xlabel='Vds (V)',ylabel='Coss (pF)',title='Approximate visual samples, typical curve')
    axes[1].plot(grid,[integrals(v)[1]*1e6 for v in grid],label='Integral of V*C(V)')
    axes[1].plot([200,400,600,800,1000,1200],[.8,2.4,4.5,7.2,10.6,15.],'x',label='Approximate Fig. 16 checkpoints')
    axes[1].set(xlabel='Vds (V)',ylabel='Stored energy (uJ)',title='Independent energy-curve cross-check')
    axes[1].legend()
    for ax in axes:ax.grid(alpha=.3)
    fig.tight_layout();fig.savefig(plots/'charge_model.png',dpi=160);plt.close(fig)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
