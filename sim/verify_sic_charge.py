"""Verify nonlinear charge and half-bridge capacitive energy at scaled 5 V."""
from pathlib import Path
import sys
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calc'))
from sic_charge import charge_expression,integrals
from ngspice_shared import NgSpice


def deck(supply,step):
    scale=supply/5
    # Complementary capacitor voltages. Both behavioral sources conserve charge.
    return '\n'.join(['Nonlinear Coss pair - scaled 5 V energy verification',
        'Vref ref 0 5','Vdrive x 0 PWL(0 0 1u 0 1.1u 5)',
        'Bcl x 0 I=ddt('+charge_expression('x',scale)+')',
        'Bch ref x I=ddt('+charge_expression('ref,x',scale)+')',
        '.options reltol=1e-7 abstol=1e-14 method=gear',
        f'.tran {step}n 1.2u 0 {step}n','.end'])+'\n'


def main():
    out=ROOT/'results/sic_charge';out.mkdir(parents=True,exist_ok=True)
    gen=ROOT/'sim/generated/sic_charge';gen.mkdir(parents=True,exist_ok=True)
    spice=NgSpice();rows=[]
    for supply in (600,650,700,1000):
        energies=[]
        for step in (.02,.01):
            text=deck(supply,step);(gen/f'charge_{supply}v_scaled_step{step}ns.cir').write_text(text)
            spice.run(text);t=spice.vector('time');x=spice.vector('x');current=-spice.vector('vdrive#branch')
            # Work dissipated by a hypothetical high-side conducting element
            # imposing this monotonic ramp: integral((Vbus-x)*I_node dt).
            energy=float(np.trapezoid((5-x)*current,t))*(supply/5)**2
            expected=supply*integrals(supply)[0]
            assert abs(energy/expected-1)<.005,(supply,energy,expected)
            assert abs(x[-1]-5)<1e-6
            energies.append(energy)
        assert abs(energies[0]/energies[1]-1)<.002
        rows.append(dict(supply_equivalent_v=supply,spice_energy_uj=energies[-1]*1e6,
                         analytic_energy_uj=expected*1e6,relative_error=energies[-1]/expected-1,
                         timestep_relative_difference=energies[0]/energies[1]-1))
    (out/'verification.json').write_text(json.dumps(dict(spice_runs=8,rows=rows),indent=2)+'\n')
    (out/'ngspice.log').write_text('\n'.join(spice.log));print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
