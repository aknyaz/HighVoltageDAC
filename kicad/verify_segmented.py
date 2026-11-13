"""Verify actual KiCad hierarchy export against the intended pin partition."""
from pathlib import Path
import subprocess,json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
CLI=Path(r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe')
project=ROOT/'kicad/segmented/hv_rdac_segmented.kicad_sch'
out=ROOT/'results/segmented_review';out.mkdir(parents=True,exist_ok=True)
subprocess.run([str(CLI),'sch','export','netlist','--format','kicadxml','-o',str(out/'netlist.xml'),str(project)],check=True)
tree=ET.parse(out/'netlist.xml');expected=json.loads((project.parent/'expected_connections.json').read_text())
actual={(node.get('ref'),node.get('pin')):net.get('code') for net in tree.findall('.//nets/net') for node in net.findall('node')}
by_expected={};by_actual={}
for ref,pins in expected.items():
    for pin,name in pins.items():
        assert (ref,pin) in actual,(ref,pin,'missing')
        net=actual[ref,pin]
        by_expected.setdefault(name,set()).add(net);by_actual.setdefault(net,set()).add(name)
assert all(len(x)==1 for x in by_expected.values()),'split expected net'
assert all(len(x)==1 for x in by_actual.values()),'unintended short'
components=tree.findall('.//components/comp')
assert len(components)==618
assert sum(c.get('ref').startswith('Q') for c in components)==64
assert sum(c.get('ref').startswith('U') for c in components)==64
# APWM is intentionally unused; every other driver pin is checked above.
report=dict(sheets=34,components=len(components),transistors=64,drivers=64,
            checked_pins=sum(map(len,expected.values())),checked_nets=len(by_expected),
            unintended_shorts=0,split_nets=0,scope='Connectivity only; passive symbol pin types; not hardware ERC qualification')
(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
