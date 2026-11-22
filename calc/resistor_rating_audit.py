"""Analytical resistor stress screen; no HV hardware or layout is specified."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = 5274.699627701833
WEIGHTS = [2**i for i in range(9)] + [512]*7 + [1]

def states(code):
    return [(code >> i) & 1 for i in range(9)] + [int(code//512 > i) for i in range(7)] + [0]

def stress(code, supply, load):
    # Exact ideal matched two-node DC solution, with resistive primary load.
    ea, eb = supply*code/4096, supply*(4095-code)/4096
    differential = (ea-eb)*load/(load+2*R)
    va, vb = (ea+eb+differential)/2, (ea+eb-differential)/2
    rows = []
    for d, node in [(code, va), (4095-code, vb)]:
        side = []
        for weight, state in zip(WEIGHTS, states(d)):
            resistance = 4096*R/weight
            voltage = abs(supply*state-node)
            side.append((voltage, voltage/resistance, voltage**2/resistance))
        rows.append(side)
    return rows

def main():
    cases = {}
    for load in [10000., 34.5**2*8]:
        maxima = [[0., 0., 0.] for _ in WEIGHTS]
        for code in range(4096):
            for side in stress(code, 650., load):
                for j, values in enumerate(side):
                    maxima[j] = [max(a,b) for a,b in zip(maxima[j], values)]
        # Full-scale rounded 1 kHz sine, 192 kS/s, ideal quasi-static network.
        mean_p = [0.]*len(WEIGHTS)
        for i in range(192):
            code = round(2047.5*(1+math.sin(2*math.pi*i/192)))
            for side in stress(code,650.,load):
                for j, values in enumerate(side):
                    mean_p[j] += values[2]/384
        cases[str(load)] = dict(maxima_v_a_w=maxima, sine_mean_w_averaged_between_arms=mean_p)
    rows = []
    for weight in [512]+[2**i for i in range(8,-1,-1)]:
        indices = [i for i,w in enumerate(WEIGHTS) if w==weight]
        resistance = 4096*R/weight
        rows.append(dict(weight=weight, count=2*len(indices), resistance_ohm=resistance,
                         max_static_v=max(c['maxima_v_a_w'][i][0] for c in cases.values() for i in indices),
                         max_static_w=max(c['maxima_v_a_w'][i][2] for c in cases.values() for i in indices),
                         rail_bound_650_ma=650/resistance*1000, rail_bound_650_w=650**2/resistance,
                         rail_bound_700_w=700**2/resistance))
    result=dict(supply_v=650, arm_r_ohm=R, assumptions='Ideal matched resistors and ideal switches; 4096 static codes. Resistive loads, not transformer transients. Full-rail bounds exclude overshoot and faults outside rails.', rows=rows, cases=cases)
    out=ROOT/'results/resistor_rating_audit'
    out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['| Weight | Qty | R (kohm) | Static max V | Static max W | 650 V bound mA | 650 V bound W | 700 V bound W |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['weight']} | {r['count']} | {r['resistance_ohm']/1000:.6f} | {r['max_static_v']:.2f} | {r['max_static_w']:.4f} | {r['rail_bound_650_ma']:.4f} | {r['rail_bound_650_w']:.4f} | {r['rail_bound_700_w']:.4f} |")
    (out/'rating_table.md').write_text('\n'.join(lines)+'\n')
    assert sum(r['count'] for r in rows)==34
    print('\n'.join(lines))
    print('Full-scale sine total resistor power, 10 kohm:',2*sum(cases['10000.0']['sine_mean_w_averaged_between_arms']))

if __name__ == '__main__':
    main()
