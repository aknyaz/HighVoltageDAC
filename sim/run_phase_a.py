"""Generate independent SPICE decks, run KiCad's ngspice DLL, verify and plot."""
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ngspice_shared import NgSpice

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from calc.architecture import calculate

FS = 192000
R = 1000.0
VREF = 5.0


def circuit(codes, transformer=False, skew=0):
    lines = ['4-bit differential R-2R low-voltage research bench',
             'Vref ref 0 5', '.model ideal SW(Ron=1u Roff=1e12 Vt=0.5 Vh=0)',
             '.options reltol=1e-6 abstol=1e-12']
    resistors = []
    def resistor(name, a, b, value):
        lines.append(f'{name} {a} {b} {value}')
        resistors.append((name, a, b, value))
    for side in ('a', 'b'):
        for bit in range(4):
            states = [((int(c) if side == 'a' else 15-int(c)) >> bit) & 1 for c in codes]
            points = [f'0 {states[0]}']
            for index in range(1, len(states)):
                if states[index] != states[index-1]:
                    t = index/FS + bit*skew
                    points.extend([f'{t:.12g} {states[index-1]}', f'{t+1e-9:.12g} {states[index]}'])
            lines.append(f'V{side}{bit} c{side}{bit} 0 PWL('+' '.join(points)+')')
            lines.append(f'B{side}{bit} n{side}{bit} 0 V=1-v(c{side}{bit})')
            lines.append(f'S{side}{bit}h d{side}{bit} ref c{side}{bit} 0 ideal')
            lines.append(f'S{side}{bit}l d{side}{bit} 0 n{side}{bit} 0 ideal')
            resistor(f'R{side}{bit}v', f'{side}{bit}', f'd{side}{bit}', 2*R)
            if bit:
                resistor(f'R{side}{bit}h', f'{side}{bit}', f'{side}{bit-1}', R)
        resistor(f'R{side}term', f'{side}0', '0', 2*R)
    if transformer:
        # Perfect coupling with finite magnetizing L; no core or winding losses.
        lines += ['Lp a3 b3 10', 'Ls sec 0 0.04', 'K1 Lp Ls 1', 'Rload sec 0 8']
    else:
        lines += ['Rload a3 b3 2000']
    lines += [f'.tran 200n {len(codes)/FS:.12g} 0 200n', '.end']
    return '\n'.join(lines)+'\n', resistors


def main():
    for directory in ('sim/generated', 'results', 'plots'):
        (ROOT/directory).mkdir(parents=True, exist_ok=True)
    spice = NgSpice()
    report = {'engine': spice.log.copy(), 'ideal_transformer': [calculate(power_w=p) for p in (5, 10)], 'runs': {}}
    def execute(name, codes, transformer=False, skew=0):
        deck, resistors = circuit(codes, transformer, skew)
        (ROOT/f'sim/generated/{name}.cir').write_text(deck)
        spice.run(deck)
        t = spice.vector('time')
        node = lambda n: np.zeros_like(t) if n == '0' else spice.vector(n)
        diff = node('a3')-node('b3')
        output = node('sec') if transformer else diff
        # Uniform resampling for integration, plots and spectral estimates.
        tu = np.arange(0, t[-1], 1/(FS*16))
        vu = np.interp(tu, t, output)
        power = sum((node(a)-node(b))**2/value for _, a, b, value in resistors)
        mask = t >= (0.092 if transformer else 0)
        mean = lambda v: float(np.trapezoid(v[mask], t[mask])/(t[mask][-1]-t[mask][0]))
        metrics = dict(load_power_w=mean(output**2/(8 if transformer else 2000)),
                       ladder_heat_w=mean(power), primary_mean_v=mean(diff),
                       supply_power_w=mean(-VREF*spice.vector('vref#branch')))
        if transformer:
            metrics['primary_mean_a'] = mean(spice.vector('lp#branch'))
            # Last 8 ms = eight cycles, rectangular window, coherent 1 kHz input.
            segment = vu[(tu >= 0.092) & (tu < 0.100)]
            segment = segment[:24576]
            spectrum = np.abs(np.fft.rfft(segment-segment.mean()))*2/len(segment)
            freq = np.fft.rfftfreq(len(segment), 1/(FS*16))
            fundamental = int(np.argmin(abs(freq-1000)))
            harmonic = [int(np.argmin(abs(freq-h*1000))) for h in range(2, 21)]
            metrics['thd_2_to_20_percent'] = float(100*np.linalg.norm(spectrum[harmonic])/spectrum[fundamental])
            plt.figure(figsize=(9, 4))
            plt.plot(freq/1000, 20*np.log10(np.maximum(spectrum/spectrum[fundamental], 1e-12)))
            plt.xlim(0, 220); plt.ylim(-120, 10); plt.grid(); plt.xlabel('Frequency (kHz)'); plt.ylabel('dBc')
            plt.title(name+' | coherent 8 ms FFT; interpolated transient')
            plt.tight_layout(); plt.savefig(ROOT/f'plots/{name}_fft.png'); plt.close()
        np.savetxt(ROOT/f'results/{name}.csv', np.column_stack((t, diff, output, power)),
                   delimiter=',', header='time_s,primary_v,load_v,ladder_heat_w', comments='')
        report['runs'][name] = metrics
        return t, diff, metrics

    codes = np.repeat(np.arange(16), 4)
    t, voltage, metrics = execute('code_sweep', codes)
    sample_t = (np.arange(16)*4+2)/FS
    observed = np.interp(sample_t, t, voltage)
    expected = VREF*(2*np.arange(16)-15)/16 * 0.5
    error = float(np.max(abs(observed-expected)))
    assert error < 1e-6, f'Code mapping error: {error}'
    assert abs(metrics['supply_power_w']-metrics['load_power_w']-metrics['ladder_heat_w']) < 1e-7
    report['code_sweep_max_error_v'] = error
    plt.figure(figsize=(8, 4)); plt.plot(np.arange(16), expected, 'o', label='Theory'); plt.plot(np.arange(16), observed, '.', label='ngspice')
    plt.xlabel('Code'); plt.ylabel('Loaded differential voltage (V)'); plt.grid(); plt.legend()
    plt.tight_layout(); plt.savefig(ROOT/'plots/code_sweep.png'); plt.close()
    fig, ax = plt.subplots(figsize=(9, 4))
    for name, skew in [('major_carry_ideal', 0), ('major_carry_skew', 20e-9)]:
        t, v, _ = execute(name, np.array([7]*8+[8]*8), skew=skew)
        ax.plot((t-8/FS)*1e9, v, label=name)
    ax.set(xlim=(-20, 120), xlabel='Time from transition (ns)', ylabel='Primary-equivalent load (V)')
    ax.grid(); ax.legend(); fig.tight_layout(); fig.savefig(ROOT/'plots/major_carry.png'); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4))
    for amplitude in (0.9, 0.25):
        # Half-sample phase avoids exact rounding ties; force complementary half-cycles.
        half = np.floor(7.5+7.5*amplitude*np.sin(2*np.pi*(np.arange(96)+0.5)/192)+0.5).astype(int)
        period = np.concatenate((half, 15-half))
        codes = np.tile(period, 100)
        name = f'sine_{amplitude:g}'
        t, v, metrics = execute(name, codes, transformer=True)
        assert abs(metrics['primary_mean_v']) < 0.002
        ax.plot(t*1000, v, label=f'{amplitude:g} full scale')
    ax.set(xlim=(98, 100), xlabel='Time (ms)', ylabel='Primary voltage (V)')
    ax.grid(); ax.legend(); fig.tight_layout(); fig.savefig(ROOT/'plots/sine.png'); plt.close(fig)
    (ROOT/'results/summary.json').write_text(json.dumps(report, indent=2))
    (ROOT/'results/ngspice.log').write_text('\n'.join(spice.log))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
