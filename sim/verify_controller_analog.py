"""Independent linear-transformer check and blanking comparison from executed runs."""
from pathlib import Path
import json
import numpy as np
from controller_analog import R
ROOT=Path(__file__).resolve().parents[1]

def main():
    folder=ROOT/'results/controller_analog'
    report=json.loads((folder/'summary.json').read_text())
    p=report['transformer'];w=2*np.pi*report['input_hz']
    lp=p['primary_inductance_h'];ls=p['secondary_inductance_h'];load=p['load_ohm']
    m=p['coupling']*np.sqrt(lp*ls);secondary=load+p['secondary_dcr_ohm']+1j*w*ls
    zcoil=1j*w*lp+w*w*m*m/secondary
    zparallel=1/(1/zcoil+1/p['primary_core_loss_ohm']+1j*w*p['primary_shunt_pf']*1e-12)
    transfer=zparallel/(2*R+p['primary_dcr_ohm']+zparallel)/zcoil*(1j*w*m*load/secondary)
    expected=5*.9*4095/4096*np.sinc(1000/192000)*abs(transfer)
    baseline=next(r for r in report['rows'] if r['dead_ns']==0 and r['cap_pf']==20)
    error=100*abs(baseline['fundamental_peak_v']/expected-1)
    # Ideal source calculation omits finite switch Ron, Coss and PCM rounding.
    assert error<.1,error
    comparisons=[]
    for cap in (20,100):
        pair={r['dead_ns']:r for r in report['rows'] if r['cap_pf']==cap}
        comparisons.append(dict(cap_pf=cap,blanking_gain_change_percent=100*(pair[200]['fundamental_peak_v']/pair[0]['fundamental_peak_v']-1),
                                thd_no_blanking_percent=pair[0]['thd_2_to_20_percent'],thd_200ns_percent=pair[200]['thd_2_to_20_percent']))
    result=dict(ideal_linear_fundamental_peak_v=float(expected),baseline_difference_percent=float(error),comparisons=comparisons,
                scope='Independent 1 kHz impedance calculation; no vendor/hardware qualification')
    (folder/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
