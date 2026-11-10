"""Isolate inter-branch timing skew in ideal 12-bit parallel DACs at 5 V.

Exact event calculation plus structural transient SPICE verification. No switch
capacitance, dead time, transformer, resistor mismatch or device claim is implied.
"""
from pathlib import Path
import sys
import json
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'calc'))
from resistor_tolerance import R, LOAD, VS, K
from ngspice_shared import NgSpice

T0 = 1e-6
EDGE = 1e-12
LSB = 2*VS/K*LOAD/(LOAD+2*R)


def topology(kind):
    return 2.**np.arange(12) if kind == 'binary' else np.r_[2.**np.arange(8), np.full(15, 256.)]


def decode(kind, code):
    fine = 12 if kind == 'binary' else 8
    bits = ((code >> np.arange(fine)) & 1).astype(float)
    return bits if kind == 'binary' else np.r_[bits, np.arange(15) < code//256]


def states(kind, old, new, profile):
    weights = topology(kind)
    initial = np.array([decode(kind, old), decode(kind, K-1-old)])
    final = np.array([decode(kind, new), decode(kind, K-1-new)])
    changed = initial != final
    largest = np.max(np.broadcast_to(weights, changed.shape)[changed])
    heavy = weights == largest
    late = changed & (heavy if profile == 'heavy_late' else ~heavy)
    intermediate = np.where(late, initial, final)
    return weights, initial, final, late, intermediate


def output(weights, state):
    return VS/K*LOAD/(LOAD+2*R)*np.dot(weights, state[0]-state[1])


def deck(kind, old, new, profile, delay, maxstep=1e-9):
    weights, initial, final, late, _ = states(kind, old, new, profile)
    lines = ['Ideal parallel DAC timing skew, 5 V only', 'Vref ref 0 5',
             '.model sw SW(Ron=1u Roff=1e12 Vt=.5 Vh=0)',
             '.options reltol=1e-8 abstol=1e-14']
    for arm, side in enumerate(('a', 'b')):
        for i, weight in enumerate(weights):
            before, after = initial[arm, i], final[arm, i]
            when = T0 + delay*late[arm, i]
            source = f'{before:g}' if before == after else f'PWL(0 {before:g} {when-EDGE/2:.15g} {before:g} {when+EDGE/2:.15g} {after:g})'
            lines += [f'Vc{side}{i} c{side}{i} 0 {source}',
                      f'Bn{side}{i} n{side}{i} 0 V=1-v(c{side}{i})',
                      f'S{side}{i}h d{side}{i} ref c{side}{i} 0 sw',
                      f'S{side}{i}l d{side}{i} 0 n{side}{i} 0 sw',
                      f'R{side}{i} {side} d{side}{i} {K*R/weight:.15g}']
        lines.append(f'R{side}term {side} 0 {K*R:.15g}')
    lines += [f'Rload a b {LOAD:g}', f'.tran {maxstep:g} 2u 0 {maxstep:g}', '.end']
    return '\n'.join(lines)+'\n'


def main():
    result = ROOT/'results/switching_glitches'
    generated = ROOT/'sim/generated/switching_glitches'
    plots = ROOT/'plots/switching_glitches'
    for path in (result, generated, plots):
        path.mkdir(parents=True, exist_ok=True)
    spice = NgSpice()
    rows = []
    traces = {}
    for kind in ('binary', 'segmented'):
        for old, new in ((127,128),(255,256),(2047,2048),(128,127),(256,255),(2048,2047)):
            for profile in ('heavy_late', 'light_late'):
                weights, initial, final, late, intermediate = states(kind, old, new, profile)
                before, after, middle = [output(weights, s) for s in (initial, final, intermediate)]
                assert abs((after-before)/LSB-(new-old)) < 1e-9
                for delay_ns in (0,20,100):
                    delay = delay_ns*1e-9
                    name = f'{kind}_{old}_{new}_{profile}_{delay_ns}ns'
                    netlist = deck(kind, old, new, profile, delay)
                    (generated/f'{name}.cir').write_text(netlist)
                    spice.run(netlist)
                    time = spice.vector('time')
                    voltage = spice.vector('a')-spice.vector('b')
                    expected = np.where(time<T0, before, np.where(time<T0+delay, middle, after))
                    away = (abs(time-T0)>5*EDGE) & (abs(time-T0-delay)>5*EDGE)
                    difference = float(np.max(abs(voltage[away]-expected[away]))/LSB)
                    assert difference < 1e-4, (name,difference)
                    # Integrate actual waveform and subtract the exact ideal-step integral.
                    ideal_integral = before*T0+after*(time[-1]-T0)
                    area = float((np.trapezoid(voltage,time)-ideal_integral)/LSB*1e9)
                    exact = (middle-after)/LSB*delay_ns
                    assert abs(area-exact) < .05 + abs(exact)*.001, (name,area,exact)
                    peak = abs(middle-after)/LSB if delay_ns else 0.
                    row = dict(architecture=kind,old_code=old,new_code=new,profile=profile,
                               delay_ns=delay_ns,peak_error_lsb=peak,
                               signed_area_lsb_ns=exact,absolute_area_lsb_ns=abs(exact),
                               signed_area_v_ns=exact*LSB,spice_area_lsb_ns=area,
                               max_plateau_error_lsb=difference)
                    rows.append(row)
                    if old == 2047 and delay_ns == 20:
                        traces[kind,profile] = (time,voltage,after)
    # Exhaustive adjacent-code event scan, both directions have equal magnitudes.
    sweep = {}
    for kind in ('binary','segmented'):
        peaks = []
        for old in range(K-1):
            errors = []
            for profile in ('heavy_late','light_late'):
                w,_,end,_,mid = states(kind,old,old+1,profile)
                errors.append(abs(output(w,mid)-output(w,end))/LSB)
            peaks.append(max(errors))
        sweep[kind] = dict(max_peak_error_lsb=max(peaks),worst_old_code=int(np.argmax(peaks)),
                           adjacent_transitions_checked=len(peaks))
    assert abs(sweep['binary']['max_peak_error_lsb']-2048)<1e-8
    assert abs(sweep['segmented']['max_peak_error_lsb']-256)<1e-8
    report = dict(scope='Ideal SPDT inter-branch timing only; resistive load; 5 V',
                  lsb_v=LSB,spice_cases=len(rows),adjacent_sweep=sweep,rows=rows)
    (result/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    with (result/'summary.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    (result/'ngspice.log').write_text('\n'.join(spice.log))
    fig, axes = plt.subplots(2,1,figsize=(10,7),sharex=True)
    for ax,kind in zip(axes,('binary','segmented')):
        for profile in ('heavy_late','light_late'):
            time,voltage,after = traces[kind,profile]
            ax.plot((time-T0)*1e9,(voltage-after)/LSB,label=profile.replace('_',' '))
        ax.set_ylabel('Error relative to final code (LSB)')
        ax.set_title(f'{kind.title()}: 2047 to 2048, 20 ns inter-group skew')
        ax.grid(alpha=.3);ax.legend();ax.set_xlim(-10,50)
    axes[-1].set_xlabel('Time relative to requested transition (ns)')
    fig.suptitle('Ideal switches, matched resistors, 5 V, 10 kohm resistive load\nSeparate vertical scales; no capacitance or transformer')
    fig.tight_layout();fig.savefig(plots/'midscale_glitch.png',dpi=160);plt.close(fig)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
    print('Maximum SPICE plateau error (LSB):',max(r['max_plateau_error_lsb'] for r in rows))


if __name__ == '__main__':
    main()
