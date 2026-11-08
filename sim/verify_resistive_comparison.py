"""Structural 5 V switched-SPICE verification of parallel resistive DACs."""
from pathlib import Path
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calc'))
from compare_resistive import branches,star_network
from power_trade_study import pcm,FS
from ngspice_shared import NgSpice


def deck_for(bits,codes,r,load,architecture):
    lines=['Parallel resistive DAC - 5 V verification only','Vref ref 0 5',
           '.model ideal SW(Ron=1u Roff=1e12 Vt=.5 Vh=0)',
           '.options reltol=1e-7 abstol=1e-13']
    resistors=[]
    for side,values in [('a',codes),('b',2**bits-1-codes)]:
        weights,states=branches(bits,values,architecture)
        for j,weight in enumerate(weights):
            points=[f'0 {states[0,j]:g}']
            for k in range(1,len(codes)):
                if states[k,j]!=states[k-1,j]:
                    points += [f'{k/FS:.12g} {states[k-1,j]:g}',f'{k/FS+1e-9:.12g} {states[k,j]:g}']
            lines += [f'V{side}{j} c{side}{j} 0 PWL('+' '.join(points)+')',
                      f'B{side}{j} n{side}{j} 0 V=1-v(c{side}{j})',
                      f'S{side}{j}h d{side}{j} ref c{side}{j} 0 ideal',
                      f'S{side}{j}l d{side}{j} 0 n{side}{j} 0 ideal']
            name=f'R{side}{j}';value=2**bits*r/weight
            lines.append(f'{name} {side} d{side}{j} {value:.12g}')
            resistors.append((name,side,f'd{side}{j}',value))
        name=f'R{side}term';value=2**bits*r
        lines.append(f'{name} {side} 0 {value:.12g}')
        resistors.append((name,side,'0',value))
    lines += [f'Rload a b {load:.12g}',f'.tran 100n {len(codes)/FS:.12g} 0 100n','.end']
    return '\n'.join(lines)+'\n',resistors


def main():
    directory=ROOT/'results/resistive_comparison'
    summary=json.loads((directory/'summary.json').read_text())
    out=ROOT/'sim/generated/resistive_comparison';out.mkdir(exist_ok=True)
    spice=NgSpice();records=[];code_checks=[]
    # Exhaustive code mapping and binary/segmented equivalence, including 12-bit boundaries.
    for bits in (4,12):
        codes=np.arange(2**bits)
        binary=star_network(bits,codes,5,1000,10000,'binary_parallel')
        segmented=star_network(bits,codes,5,1000,10000,'segmented_parallel')
        assert np.all(np.diff(binary['output'])>0)
        np.testing.assert_allclose(binary['output'],segmented['output'],atol=1e-13)
        np.testing.assert_allclose(binary['heat'],segmented['heat'],atol=1e-13)
        code_checks.append(dict(bits=bits,codes_checked=len(codes),mapping='passed',monotonicity='passed'))
    for architecture in ('binary_parallel','segmented_parallel'):
        codes=np.arange(16)
        deck,_=deck_for(4,codes,1000,10000,architecture)
        (out/f'4bit_code_sweep_{architecture}.cir').write_text(deck)
        spice.run(deck)
        sampled=np.interp((np.arange(16)+.5)/FS,spice.vector('time'),spice.vector('a')-spice.vector('b'))
        expected=star_network(4,codes,5,1000,10000,architecture)['output']
        assert np.max(abs(sampled-expected))<1e-6
        code_checks.append(dict(architecture=architecture,spice_4bit_max_error_v=float(np.max(abs(sampled-expected)))))
    points=[]
    for case in summary['cases']:
        if 'r2r' not in case: continue
        for architecture in ('binary_parallel','segmented_parallel'):
            points.append(case[architecture]['best_sampled'])
            if (case['bits'],case['supply_v'],case['primary_load_ohm'],case['target_fundamental_w'])==(12,650,10000,5):
                points.append(case[architecture]['best_with_reserve'])
    for index,p in enumerate(points):
        architecture=p['architecture'];codes=pcm(p['bits'],p['pcm_amplitude'])
        deck,resistors=deck_for(p['bits'],codes,p['r_ohm'],p['primary_load_ohm'],architecture)
        name=f"{architecture}_{p['bits']}bit_{p['supply_v']:g}V_{p['primary_load_ohm']:g}ohm_{p['target_fundamental_w']:g}W_a{p['pcm_amplitude']:g}"
        (out/f'{name}.cir').write_text(deck)
        spice.run(deck)
        t=spice.vector('time');v=spice.vector('a')-spice.vector('b')
        node=lambda n:np.zeros_like(t) if n=='0' else spice.vector(n)
        heat=sum((node(a)-node(b))**2/value for _,a,b,value in resistors)
        average=lambda values:float(np.trapezoid(values,t)/(t[-1]-t[0]))
        scale=(p['supply_v']/5)**2
        fundamental=2*abs(np.trapezoid(v*np.exp(-2j*np.pi*1000*t),t)/(t[-1]-t[0]))
        measured=dict(heat_w=average(heat)*scale,supply_power_w=average(-5*spice.vector('vref#branch'))*scale,
                      total_load_power_w=average(v**2/p['primary_load_ohm'])*scale,
                      target_fundamental_w=float(fundamental**2/(2*p['primary_load_ohm'])*scale))
        errors={key:abs(value/p[key]-1) for key,value in measured.items()}
        assert max(errors.values())<.002,(name,errors)
        balance=abs(measured['supply_power_w']-measured['heat_w']-measured['total_load_power_w'])
        assert balance<.0001*measured['supply_power_w'],(name,balance)
        records.append(dict(case=name,simulated_supply_v=5,target_equivalent=measured,relative_errors=errors))
        print(f'PASS {index+1}/{len(points)} {name} max error {max(errors.values()):.3g}',flush=True)
    (directory/'verification.json').write_text(json.dumps(dict(code_checks=code_checks,
        power_spice_cases=len(records),code_sweep_spice_cases=2,
        maximum_relative_power_error=max(max(r['relative_errors'].values()) for r in records),records=records),indent=2)+'\n')
    (directory/'ngspice.log').write_text('\n'.join(spice.log))


if __name__=='__main__':main()
