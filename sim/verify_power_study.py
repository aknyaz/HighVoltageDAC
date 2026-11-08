"""Independent nodal and low-voltage switched-SPICE checks of the power sweep."""
from pathlib import Path
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from calc.power_trade_study import network,pcm,FS,SAMPLES
from ngspice_shared import NgSpice


def direct_nodes(bits,codes,supply,r,load):
    # Assemble both arms and the bridge load directly, without a Thevenin reduction.
    g=np.zeros((2*bits,2*bits))
    rhs=np.zeros((2*bits,len(codes)))
    for side in range(2):
        for bit in range(bits):
            i=side*bits+bit
            state=((codes>>bit)&1) if side==0 else 1-((codes>>bit)&1)
            g[i,i]+=1/(2*r)
            rhs[i]=state*supply/(2*r)
            if bit==0:
                g[i,i]+=1/(2*r)
            else:
                g[i,i]+=1/r;g[i-1,i-1]+=1/r;g[i,i-1]-=1/r;g[i-1,i]-=1/r
    a,b=bits-1,2*bits-1
    g[a,a]+=1/load;g[b,b]+=1/load;g[a,b]-=1/load;g[b,a]-=1/load
    return np.linalg.solve(g,rhs).T


def make_deck(bits,codes,r,load):
    # Supply is always 5 V. Keep R and load unchanged; rescale power by (Vtarget/5)^2.
    lines=['Scaled 5 V R-2R power-study verification',
           'Vref ref 0 5','.model ideal SW(Ron=1u Roff=1e12 Vt=.5 Vh=0)',
           '.options reltol=1e-7 abstol=1e-13']
    resistors=[]
    def res(name,a,b,value):
        lines.append(f'{name} {a} {b} {value:.12g}')
        resistors.append((name,a,b,value))
    for side in ('a','b'):
        for bit in range(bits):
            values=(((codes if side=='a' else 2**bits-1-codes)>>bit)&1)
            points=[f'0 {values[0]}']
            for k in range(1,len(codes)):
                if values[k]!=values[k-1]:
                    points += [f'{k/FS:.12g} {values[k-1]}',f'{k/FS+1e-9:.12g} {values[k]}']
            lines.append(f'V{side}{bit} c{side}{bit} 0 PWL('+' '.join(points)+')')
            lines += [f'B{side}{bit} n{side}{bit} 0 V=1-v(c{side}{bit})',
                      f'S{side}{bit}h d{side}{bit} ref c{side}{bit} 0 ideal',
                      f'S{side}{bit}l d{side}{bit} 0 n{side}{bit} 0 ideal']
            res(f'R{side}{bit}v',f'{side}{bit}',f'd{side}{bit}',2*r)
            if bit: res(f'R{side}{bit}h',f'{side}{bit}',f'{side}{bit-1}',r)
        res(f'R{side}term',f'{side}0','0',2*r)
    lines += [f'Rload a{bits-1} b{bits-1} {load:.12g}', '.tran 100n 1m 0 100n','.end']
    return '\n'.join(lines)+'\n',resistors


def main():
    summary=json.loads((ROOT/'results/power_study/summary.json').read_text())
    points=[c['best_sampled'] for c in summary['cases'] if 'best_sampled' in c]
    reserve=next(c['best_with_10_percent_command_reserve'] for c in summary['cases']
                 if (c['bits'],c['supply_v'],c['primary_load_ohm'],c['target_fundamental_w'])==(12,650,10000,5))
    points.append(reserve)
    rng=np.random.default_rng(20261108)
    nodal_error=0
    for bits in (4,12):
        codes=np.arange(16) if bits==4 else np.concatenate(([0,2047,2048,4095],rng.integers(0,4096,40)))
        for load in (5000,10000,20000):
            result=network(bits,codes,650,2500,load)
            direct=direct_nodes(bits,codes,650,2500,load)
            nodal_error=max(nodal_error,float(np.max(abs(np.concatenate((result['va'],result['vb']),axis=1)-direct))))
    assert nodal_error<1e-9
    # Explicit checks of both voltage-scaling statements used in the design discussion.
    codes=pcm(12,.9)
    base=network(12,codes,5,1000,10000)
    voltage_only=network(12,codes,650,1000,10000)
    all_scaled=network(12,codes,650,1000*130**2,10000*130**2)
    for key in ('heat_w','supply_w','load_w'):
        np.testing.assert_allclose(voltage_only[key],base[key]*130**2,rtol=1e-12)
        np.testing.assert_allclose(all_scaled[key],base[key],rtol=1e-12)
    spice=NgSpice()
    records=[]
    out=ROOT/'sim/generated/power_study'
    out.mkdir(exist_ok=True)
    for index,p in enumerate(points):
        bits=p['bits'];codes=pcm(bits,p['pcm_amplitude'])
        deck,resistors=make_deck(bits,codes,p['r_ohm'],p['primary_load_ohm'])
        name=f"{bits}bit_{p['supply_v']}V_{p['primary_load_ohm']}ohm_{p['target_fundamental_w']}W_a{p['pcm_amplitude']:g}"
        (out/f'{name}.cir').write_text(deck)
        spice.run(deck)
        t=spice.vector('time')
        node=lambda name:np.zeros_like(t) if name=='0' else spice.vector(name)
        output=node(f'a{bits-1}')-node(f'b{bits-1}')
        heat=sum((node(a)-node(b))**2/value for _,a,b,value in resistors)
        average=lambda values:float(np.trapezoid(values,t)/(t[-1]-t[0]))
        scale=(p['supply_v']/5)**2
        fundamental=2*abs(np.trapezoid(output*np.exp(-2j*np.pi*1000*t),t)/(t[-1]-t[0]))
        measured=dict(ladder_heat_w=average(heat)*scale,
                      supply_power_w=average(-5*spice.vector('vref#branch'))*scale,
                      total_load_power_w=average(output**2/p['primary_load_ohm'])*scale,
                      fundamental_power_w=float(fundamental**2/(2*p['primary_load_ohm'])*scale))
        errors={key:abs(value/p[key]-1) for key,value in measured.items()}
        assert max(errors.values())<.002,(name,errors)
        balance=abs(measured['supply_power_w']-measured['ladder_heat_w']-measured['total_load_power_w'])
        # Allow 0.01% for finite switch transitions and transient integration.
        assert balance<1e-4*measured['supply_power_w'],(name,balance,measured)
        records.append(dict(case=name,simulated_supply_v=5,target_equivalent=measured,
                            relative_errors=errors,power_balance_error_w=balance))
        print(f"PASS {index+1}/{len(points)} {name}: max error {max(errors.values()):.3g}",flush=True)
    report=dict(direct_nodal_max_error_v=nodal_error,voltage_scaling_checks='passed',
                spice_cases=len(records),maximum_relative_error=max(max(r['relative_errors'].values()) for r in records),records=records)
    (ROOT/'results/power_study/verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'results/power_study/ngspice.log').write_text('\n'.join(spice.log))


if __name__=='__main__':main()
