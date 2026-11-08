"""Check exported KiCad connectivity against intended passive ladder graph."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
tree = ET.parse(root/'results/core_netlist.xml')
actual = {}
for net in tree.findall('.//nets/net'):
    name = net.attrib['name'].removeprefix('/')
    for node in net.findall('node'):
        actual.setdefault(node.attrib['ref'], []).append(name)
expected = json.loads((root/'kicad/expected_core.json').read_text())
for component in expected:
    ref = component['ref']
    assert sorted(actual[ref]) == component['nodes'], (ref, actual[ref], component['nodes'])
assert len(actual) == 17
print('PASS: all 17 resistors have the intended two nets.')
