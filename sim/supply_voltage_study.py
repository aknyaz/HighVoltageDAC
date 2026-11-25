"""Reuse the audio viability bench to compare fixed 650 V and 100 V rails.

Simulation only. No physical HV source or validated HV device model is implied.
"""
import json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import audio_viability_switched as av
from ngspice_shared import NgSpice

OUT = av.ROOT/'results/supply_voltage'
GEN = av.ROOT/'sim/generated/supply_voltage'
PLOTS = av.ROOT/'plots/supply_voltage'


def held(bus, amplitude):
    q, times = av.stimulus('sine', amplitude)
    bounds = np.r_[0, times, .001]
    levels = bus*(2*np.r_[q[-1], q]-4095)/4096
    hz = np.arange(1, 21)*1000
    omega = 2*np.pi*hz
    coefficients = 2/.001*np.sum(levels[None, :]*(
        np.exp(-1j*omega[:, None]*bounds[:-1])-
        np.exp(-1j*omega[:, None]*bounds[1:]))/(1j*omega[:, None]), axis=1)
    output = coefficients*av.transfer(hz, av.P, 100, 100000)
    ideal_peak = bus*4095/4096*amplitude*abs(av.transfer(1000, av.P, 100, 100000))*np.sinc(1000/av.FS)
    ideal_samples = bus*4095/4096*amplitude*np.sin(2*np.pi*1000*(np.arange(192)+.5)/av.FS)
    error = bus*(2*q-4095)/4096-ideal_samples
    return dict(bus_v=bus, code_amplitude=amplitude,
        fundamental_peak_v=float(abs(output[0])),
        fundamental_gain_error_percent=float(100*(abs(output[0])/ideal_peak-1)),
        thd_2_to_20_percent=float(100*np.linalg.norm(output[1:])/abs(output[0])),
        source_quantization_rms_v=float(np.sqrt(np.mean(error**2))),
        source_quantization_rms_percent_of_signal=float(100*np.linalg.norm(error)/np.linalg.norm(ideal_samples)),
        differential_source_step_v=2*bus/4096,
        distinct_codes=int(len(np.unique(q))))


def worker(case):
    bus, amplitude = case
    spice = NgSpice()
    checks = []
    for step in (500, 250):
        name = f'bus{bus}_amp{amplitude:g}_{step}ns'
        net = av.deck('sine', amplitude, step)
        net = net.replace('Vref ref 0 5', f'Vref ref 0 {bus}')
        net = net.replace('/ 5 V /', f'/ {bus} V /')
        # Preserve the generic 0.7 V diode drop relative to the actual rail.
        net = net.replace('-5.7,0)/2', f'-{bus+.7:g},0)/2')
        (GEN/(name+'.cir')).write_text(net)
        spice.run(net)
        t, v = spice.vector('time'), spice.vector('out')
        assert t[-1] >= av.STOP-1e-10
        sp, raw, tail = av.spectrum(t, v, .020)
        prev, _, _ = av.spectrum(t, v, .010)
        result = av.metrics(sp, 'sine')
        prior = av.metrics(prev, 'sine')
        change = abs(result['thd_2_to_20_percent']-prior['thd_2_to_20_percent'])
        assert change < .001, (name, change)
        record = dict(bus_v=bus, code_amplitude=amplitude, step_ns=step,
            **result, previous_window=prior, window_change_pp=change,
            raw_window=av.metrics(raw, 'sine'), fitted_tail_v=tail)
        checks.append(record)
        (OUT/(name+'.json')).write_text(json.dumps(record, indent=2)+'\n')
        (OUT/(name+'.log')).write_text('\n'.join(line.rstrip() for msg in spice.log for line in msg.splitlines())+'\n')
        spice.log.clear()
        print('SPICE', name, json.dumps(result), flush=True)
    delta = abs(checks[0]['thd_2_to_20_percent']-checks[1]['thd_2_to_20_percent'])
    assert delta < .001, delta
    return dict(**checks[-1], refinement_pp=delta, held=held(bus, amplitude)), (bus, amplitude, sp)


def main():
    for folder in (OUT, GEN, PLOTS):
        folder.mkdir(parents=True, exist_ok=True)
    static = []
    for base in (.1, .01, .001):
        high, low = held(650, base), held(100, base)
        assert abs(high['thd_2_to_20_percent']-low['thd_2_to_20_percent']) < 1e-10
        assert abs(high['fundamental_peak_v']/low['fundamental_peak_v']-6.5) < 1e-12
        assert abs(high['thd_2_to_20_percent']-av.reference('sine', base)['thd_2_to_20_percent']) < 1e-10
        for bus, amplitude, mode in ((650, base, 'baseline'),
                                     (100, base*6.5, 'equal_target_output'),
                                     (100, base, 'unchanged_codes')):
            static.append(dict(reference_amplitude_at_650_v=base, mode=mode, **held(bus, amplitude)))
    (OUT/'held.json').write_text(json.dumps(static, indent=2)+'\n')
    print('PASS nine held-code records and three scaling/reference checks', flush=True)
    with ProcessPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(worker, ((650, .01), (100, .065), (100, .01), (650, .001), (100, .0065))))
    rows = [r[0] for r in results]
    spectra = [r[1] for r in results]
    report = dict(sample_rate_hz=av.FS, tone_hz=1000, spice_runs=10,
        static=static, switched=rows,
        scope='Nominal 3+9 equivalent resistors and linear LL1679; existing fixed 20 pF, 0.35 ohm switch surrogate, 200 ns blanking, 2 ns edges, 50 MHz command grid. Ideal fixed supplies. Generic rail clamps corrected for each bus. No nonlinear HV devices/core, physical noise, supply ripple/ramps, tolerance or thermal drift. Not the expanded 3052-chip parasitic model. THD includes harmonics 2-20; not THD+N. Same target amplitude is set before quantization; actual amplitudes differ slightly from quantization and switching. Slow startup tail removed by the existing period-mean fit.')
    (OUT/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for base, ax in zip((.01, .001), axes):
        for bus, amp, sp in spectra:
            if (bus == 650 and amp == base) or (bus == 100 and np.isclose(amp, base*6.5)):
                bins = np.arange(2, 21)*10
                ax.plot(np.arange(2,21), 20*np.log10(np.maximum(abs(sp[bins])/abs(sp[10]), 1e-12)), 'o-', label=f'{bus} V, {100*amp:g}% code range')
        ax.set(xlabel='Harmonic order (1 kHz tone)', ylabel='dBc', title=f'Equal target: {100*base:g}% of 650 V full scale', ylim=(-140, 0))
        ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(PLOTS/'harmonics.png', dpi=150); plt.close(fig)
    print('PASS ten switched runs with timestep and window checks', flush=True)


if __name__ == '__main__':
    main()
