"""Verify selected mismatch and corner cases by sweeping every code in ngspice."""
from pathlib import Path
import sys
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calc'))
from resistor_tolerance import N,K,NOMINAL,LOAD,full_transfer
from ngspice_shared import NgSpice


def make_deck(errors):
    lines=['12-bit parallel mismatch verification - 5 V only','Vref ref 0 5','Vcode code 0 0',
           '.model ideal SW(Ron=1u Roff=1e12 Vt=.5 Vh=0)',
           '.options reltol=1e-8 abstol=1e-14']
    for arm,side in enumerate(('a','b')):
        for bit in range(N):
            expression=f'floor(v(code)/{2**bit})-2*floor(v(code)/{2**(bit+1)})'
            if side=='b':expression=f'1-({expression})'
            lines += [f'Bc{side}{bit} c{side}{bit} 0 V={expression}',
                      f'Bn{side}{bit} n{side}{bit} 0 V=1-v(c{side}{bit})',
                      f'S{side}{bit}h d{side}{bit} ref c{side}{bit} 0 ideal',
                      f'S{side}{bit}l d{side}{bit} 0 n{side}{bit} 0 ideal',
                      f'R{side}{bit} {side} d{side}{bit} {NOMINAL[bit]*(1+errors[arm,bit]):.15g}']
        lines.append(f'R{side}term {side} 0 {NOMINAL[-1]*(1+errors[arm,-1]):.15g}')
    lines += [f'Rload a b {LOAD:g}',f'.dc Vcode 0 {K-1} 1','.end']
    return '\n'.join(lines)+'\n'


def main():
    data=json.loads((ROOT/'results/resistor_tolerance/summary.json').read_text())
    out=ROOT/'sim/generated/resistor_tolerance';out.mkdir(exist_ok=True)
    spice=NgSpice();rows=[]
    for example in data['examples']:
        errors=np.array(example['error']);deck=make_deck(errors)
        (out/f"{example['name']}.cir").write_text(deck)
        spice.run(deck)
        observed=spice.vector('a')-spice.vector('b')
        assert len(observed)==K
        analytic=full_transfer(errors)
        lsb=(analytic[-1]-analytic[0])/(K-1)
        error=float(np.max(abs(observed-analytic))/lsb)
        assert error<1e-5,(example['name'],error)
        observed_lsb=(observed[-1]-observed[0])/(K-1)
        dnl=np.diff(observed)/observed_lsb-1
        inl=(observed-(observed[0]+np.arange(K)*observed_lsb))/observed_lsb
        row=dict(name=example['name'],codes_checked=K,max_transfer_difference_lsb=error,
                 max_inl_lsb=float(np.max(abs(inl))),minimum_step_lsb=float(np.min(np.diff(observed)/observed_lsb)),
                 max_abs_dnl_lsb=float(np.max(abs(dnl))),nonpositive_steps=int(np.sum(np.diff(observed)<=0)))
        rows.append(row);print(row,flush=True)
    report=dict(spice_cases=len(rows),total_dc_points=K*len(rows),maximum_difference_lsb=max(r['max_transfer_difference_lsb'] for r in rows),rows=rows)
    (ROOT/'results/resistor_tolerance/verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'results/resistor_tolerance/ngspice.log').write_text('\n'.join(spice.log))


if __name__=='__main__':main()
