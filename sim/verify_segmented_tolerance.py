"""Full-code SPICE validation of explicit 4+8 segmented resistor mismatch cases."""
from pathlib import Path
import sys
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calc'))
from segmented_tolerance import K,FINE,COUNT,NOMINAL,LOAD,full_transfer
from ngspice_shared import NgSpice


def make_deck(errors):
    lines=['12-bit 4+8 segmented mismatch - 5 V only','Vref ref 0 5','Vcode code 0 0',
           '.model ideal SW(Ron=1u Roff=1e12 Vt=.5 Vh=0)',
           '.options reltol=1e-8 abstol=1e-14']
    for arm,side in enumerate(('a','b')):
        code='v(code)' if side=='a' else '(4095-v(code))'
        for branch in range(COUNT):
            if branch<FINE:
                expression=f'floor({code}/{2**branch})-2*floor({code}/{2**(branch+1)})'
            else:
                expression=f'(floor({code}/256)>{branch-FINE})'
            lines += [f'Bc{side}{branch} c{side}{branch} 0 V={expression}',
                      f'Bn{side}{branch} n{side}{branch} 0 V=1-v(c{side}{branch})',
                      f'S{side}{branch}h d{side}{branch} ref c{side}{branch} 0 ideal',
                      f'S{side}{branch}l d{side}{branch} 0 n{side}{branch} 0 ideal',
                      f'R{side}{branch} {side} d{side}{branch} {NOMINAL[branch]*(1+errors[arm,branch]):.15g}']
        lines.append(f'R{side}term {side} 0 {NOMINAL[-1]*(1+errors[arm,-1]):.15g}')
    lines += [f'Rload a b {LOAD:g}',f'.dc Vcode 0 {K-1} 1','.end']
    return '\n'.join(lines)+'\n'


def main():
    directory=ROOT/'results/segmented_tolerance'
    data=json.loads((directory/'summary.json').read_text())
    out=ROOT/'sim/generated/segmented_tolerance';out.mkdir(exist_ok=True)
    spice=NgSpice();rows=[]
    for example in data['examples']:
        errors=np.array(example['error']);deck=make_deck(errors)
        (out/f"{example['name']}.cir").write_text(deck)
        spice.run(deck)
        observed=spice.vector('a')-spice.vector('b')
        assert len(observed)==K
        expected=full_transfer(errors)
        reference_lsb=(expected[-1]-expected[0])/(K-1)
        difference=float(np.max(abs(observed-expected))/reference_lsb)
        assert difference<1e-5,(example['name'],difference)
        lsb=(observed[-1]-observed[0])/(K-1)
        steps=np.diff(observed)/lsb
        inl=(observed-observed[0]-np.arange(K)*lsb)/lsb
        assert abs(np.max(abs(inl))-example['metrics']['max_inl_lsb'])<1e-5
        assert abs(np.min(steps)-example['metrics']['min_step_lsb'])<1e-5
        row=dict(name=example['name'],codes_checked=K,max_transfer_difference_lsb=difference,
                 max_inl_lsb=float(np.max(abs(inl))),minimum_step_lsb=float(np.min(steps)),
                 max_abs_dnl_lsb=float(np.max(abs(steps-1))),nonpositive_steps=int(np.sum(steps<=0)))
        rows.append(row);print(row,flush=True)
    report=dict(spice_cases=len(rows),total_dc_points=K*len(rows),maximum_difference_lsb=max(r['max_transfer_difference_lsb'] for r in rows),rows=rows)
    (directory/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (directory/'ngspice.log').write_text('\n'.join(spice.log))


if __name__=='__main__':main()
