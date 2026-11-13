"""Structural full-code verification of partition-study mismatch examples."""
from pathlib import Path
import sys,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calc'))
from partition_study import weights,direct,R,K,LOAD
from ngspice_shared import NgSpice

def deck(coarse,error):
    w=weights(coarse);fine=12-coarse
    lines=['Partition mismatch full-code verification, 5 V','Vref ref 0 5','Vcode code 0 0',
           '.model sw SW(Ron=1u Roff=1e12 Vt=.5 Vh=0)','.options reltol=1e-8 abstol=1e-14']
    for arm,side in enumerate(('a','b')):
        code='v(code)' if arm==0 else '(4095-v(code))'
        for j,weight in enumerate(w):
            control=f'floor({code}/{2**j})-2*floor({code}/{2**(j+1)})' if j<fine else f'(floor({code}/{2**fine})>{j-fine})'
            lines += [f'Bc{side}{j} c{side}{j} 0 V={control}',f'Bn{side}{j} n{side}{j} 0 V=1-v(c{side}{j})',
                      f'Sh{side}{j} d{side}{j} ref c{side}{j} 0 sw',f'Sl{side}{j} d{side}{j} 0 n{side}{j} 0 sw',
                      f'R{side}{j} {side} d{side}{j} {K*R/weight*(1+error[arm,j]):.15g}']
        lines.append(f'R{side}term {side} 0 {K*R*(1+error[arm,-1]):.15g}')
    return '\n'.join(lines+[f'Rload a b {LOAD}', '.dc Vcode 0 4095 1','.end'])+'\n'

def main():
    out=ROOT/'results/partition_study';gen=ROOT/'sim/generated/partition_study';gen.mkdir(parents=True,exist_ok=True)
    report=json.loads((out/'summary.json').read_text());examples=report['examples']
    examples.append(dict(coarse_bits=3,error=np.zeros((2,len(weights(3))+1)).tolist(),ideal=True))
    spice=NgSpice();rows=[]
    for ex in examples:
        c=ex['coarse_bits'];error=np.array(ex['error']);net=deck(c,error)
        name=f'coarse{c}_'+('ideal' if ex.get('ideal') else 'mismatch')
        (gen/f'{name}.cir').write_text(net);spice.run(net)
        v=spice.vector('a')-spice.vector('b');expected=direct(c,error);lsb=(expected[-1]-expected[0])/4095
        difference=float(max(abs(v-expected))/lsb)
        assert len(v)==4096 and difference<1e-5
        rows.append(dict(name=name,codes=4096,max_difference_lsb=difference))
    (out/'verification.json').write_text(json.dumps(dict(spice_cases=len(rows),rows=rows),indent=2)+'\n')
    (out/'ngspice.log').write_text('\n'.join(spice.log));print(rows)

if __name__=='__main__':main()
