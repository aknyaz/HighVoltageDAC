"""Export and verify the actual parallel KiCad sheet, then simulate its SPICE export."""
from pathlib import Path
import os
import sys
import json
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sim'))
from ngspice_shared import NgSpice
from verify_resistive_comparison import deck_for

CLI=os.environ.get('KICAD_CLI',r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe')
SCHEMATIC=ROOT/'kicad/parallel/hv_rdac_parallel.kicad_sch'


def main():
    for fmt,filename in [('kicadxml','parallel_netlist.xml'),('spice','parallel_kicad.cir')]:
        subprocess.run([CLI,'sch','export','netlist','--format',fmt,'-o',str(ROOT/'results'/filename),str(SCHEMATIC)],check=True)
    subprocess.run([CLI,'sch','erc','--exit-code-violations','-o',str(ROOT/'results/parallel_erc.rpt'),str(SCHEMATIC)],check=True)
    tree=ET.parse(ROOT/'results/parallel_netlist.xml')
    actual={}
    for net in tree.findall('.//nets/net'):
        for node in net.findall('node'):
            actual[(node.attrib['ref'],node.attrib['pin'])]=net.attrib['name']
    expected=json.loads((ROOT/'kicad/parallel/expected_connections.json').read_text())
    expected={ref:pins for ref,pins in expected.items() if not ref.startswith('#')}
    mapping={}
    reverse={}
    for ref,pins in expected.items():
        for pin,logical in pins.items():
            net=actual[(ref,pin)]
            assert mapping.setdefault(logical,net)==net, f'Broken connection: {ref}.{pin} on {net}, expected {logical}'
            assert reverse.setdefault(net,logical)==logical, f'Short: {logical} and {reverse[net]}'
    assert len(actual)==sum(len(p) for p in expected.values())
    print(f'Connectivity PASS: {len(expected)} symbols, {len(actual)} pins, {len(mapping)} nets')
    spice=NgSpice()
    deck=(ROOT/'results/parallel_kicad.cir').read_text()
    spice.run(deck)
    t=spice.vector('time')
    primary=spice.vector('/aout')-spice.vector('/bout')
    secondary=spice.vector('/sec')
    mask=t>=.092
    average=lambda v: float(np.trapezoid(v[mask],t[mask])/(t[mask][-1]-t[mask][0]))
    metrics={'verified_symbols':len(expected),'verified_pins':len(actual),'verified_nets':len(mapping),
             'load_power_w':average(secondary**2/8),
             'primary_mean_v':average(primary),
             'supply_power_w':average(-5*spice.vector('v1#branch'))}
    heat=np.zeros_like(t)
    for line in deck.splitlines():
        if not line.startswith('R') or line.startswith('R17 '):
            continue
        _,a,b,value=line.split()
        node=lambda n:np.zeros_like(t) if n.lower() in ('0','gnd') else spice.vector(n)
        heat+=(node(a)-node(b))**2/float(value.lower().replace('k','e3'))
    metrics['resistor_heat_w']=average(heat)
    metrics['power_balance_residual_w']=metrics['supply_power_w']-metrics['load_power_w']-metrics['resistor_heat_w']
    assert abs(metrics['power_balance_residual_w'])<1e-6
    grid=np.arange(.098,.1,1/(192000*16))
    parallel=np.interp(grid,t,secondary)
    parallel_primary=np.interp(grid,t,primary)
    half=np.floor(7.5+7.5*.9*np.sin(2*np.pi*(np.arange(96)+.5)/192)+.5).astype(int)
    reference,_=deck_for(4,np.tile(np.concatenate((half,15-half)),100),1000,2000,'binary_parallel')
    reference=reference.replace('Rload a b 2000','Lp a b 10\nLs sec 0 0.04\nK1 Lp Ls 1\nRload sec 0 8').replace('.tran 100n 0.1 0 100n','.tran 200n 0.1 0 200n')
    (ROOT/'sim/generated/parallel_transformer.cir').write_text(reference)
    spice.run(reference)
    ref=np.interp(grid,spice.vector('time'),spice.vector('sec'))
    metrics['max_secondary_difference_from_reference_v']=float(np.max(np.abs(parallel-ref)))
    assert metrics['max_secondary_difference_from_reference_v']<1e-4,metrics
    baseline=json.loads((ROOT/'results/summary.json').read_text())['runs']['sine_0.9']
    metrics['r2r_reference_heat_w']=baseline['ladder_heat_w']
    metrics['heat_reduction_factor']=baseline['ladder_heat_w']/metrics['resistor_heat_w']
    metrics['relative_load_power_difference']=abs(metrics['load_power_w']/baseline['load_power_w']-1)
    assert metrics['relative_load_power_difference']<1e-4,metrics
    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
    axes[0].plot(grid*1000,parallel_primary); axes[0].set_ylabel('Primary voltage (V)')
    axes[1].plot(grid*1000,ref,label='Independent parallel netlist',linewidth=2)
    axes[1].plot(grid*1000,parallel,'--',label='Actual KiCad SPICE export',linewidth=1)
    axes[1].set(xlabel='Time (ms)',ylabel='Secondary voltage (V)')
    for ax in axes: ax.grid()
    axes[1].legend(); fig.suptitle('Parallel KiCad schematic verification | 1 kHz, 90% FS, 4 bits')
    fig.tight_layout(); fig.savefig(ROOT/'plots/parallel_kicad_verification.png'); plt.close(fig)
    (ROOT/'results/parallel_verification.json').write_text(json.dumps(metrics,indent=2)+'\n')
    (ROOT/'results/parallel_ngspice.log').write_text('\n'.join(spice.log))
    # Keep committed export portable; the unmodified absolute-path export was simulated above.
    library=(ROOT/'kicad/parallel/hv_rdac_models.lib').as_posix()
    deck=deck.replace(library,'../kicad/parallel/hv_rdac_models.lib')
    (ROOT/'results/parallel_kicad.cir').write_text('\n'.join(line.rstrip() for line in deck.splitlines())+'\n')
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':
    main()
