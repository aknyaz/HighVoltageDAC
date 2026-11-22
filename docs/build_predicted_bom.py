"""Build the standalone planning BOM: python docs/build_predicted_bom.py.

Requires reportlab. Prices are the 2026-11-21 research snapshot, not live quotes.
"""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/HV_RDAC_Predicted_Bill_of_Materials.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleCustom', fontName='Helvetica-Bold', fontSize=25, leading=29, textColor=colors.HexColor('#16324f'), spaceAfter=14))
styles.add(ParagraphStyle(name='Deck', fontSize=12, leading=17, textColor=colors.HexColor('#37566f'), spaceAfter=14))
styles.add(ParagraphStyle(name='Cell', fontSize=9, leading=12))
styles.add(ParagraphStyle(name='SmallCustom', fontSize=8.5, leading=12, spaceAfter=7))
styles['BodyText'].fontSize = 10
styles['BodyText'].leading = 14
styles['BodyText'].spaceAfter = 9
story = []

def p(text, style='BodyText'):
    return Paragraph(text, styles[style])

def add(text, style='BodyText'):
    story.append(p(text, style))

def table(rows, widths):
    t = Table([[p(str(c), 'Cell') for c in row] for row in rows], colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2ecf3')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LINEBELOW', (0, 0), (-1, 0), .6, colors.HexColor('#93a9ba')),
        ('LINEBELOW', (0, 1), (-1, -1), .3, colors.HexColor('#dce3e8')),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

budget = [
    ('SiC switching transistors, including spares', 220, 300),
    ('Isolated gate-driver ICs, including spares', 210, 300),
    ('Driver bias supplies and associated circuitry', 400, 800),
    ('Precision resistor assemblies and selection stock', 200, 600),
    ('Output transformer', 300, 400),
    ('FPGA / control board, clock and digital interface', 100, 250),
    ('Main and auxiliary power supplies', 300, 800),
    ('Other passives, protection and connectors', 120, 250),
    ('Enclosure, cooling and mechanical parts', 150, 350),
    ('Bare PCB fabrication, small batches', 150, 350),
]
low, high = sum(r[1] for r in budget), sum(r[2] for r in budget)
assert (low, high) == (2150, 4400)

add('HV-RDAC', 'Deck')
add('Predicted Bill of Materials', 'TitleCustom')
add('One-channel research prototype | Revision 0.2 | 22 November 2026', 'Deck')
add('<b>Planning target: USD 4,000-5,000.</b> Allow approximately <b>USD 3,000-6,000</b> for the first complete mono prototype, including delivery, estimated taxes and contingency. This is a planning estimate, not a supplier quotation or a released purchasing BOM.')
add('Scope: current 12-bit, 3+9 segmented differential architecture; 32 half bridges, 64 SiC transistors, 64 gate drivers and one output transformer. Future HV operation is an analytical target; the repository remains simulation-only.')
table([['<b>Budget item</b>', '<b>Low, USD</b>', '<b>High, USD</b>']] + [[r[0], f'{r[1]:,}', f'{r[2]:,}'] for r in budget] + [
    ['<b>Parts and fabrication subtotal</b>', f'<b>{low:,}</b>', f'<b>{high:,}</b>'],
    ['Delivery and taxes: planning allowance', '150', '400'],
    ['20% contingency on subtotal plus delivery/taxes', '460', '960'],
    ['<b>Calculated all-in range</b>', '<b>2,760</b>', '<b>5,760</b>'],
], [339, 83, 83])
add('The rounded USD 3,000-6,000 range is deliberately broad. Bias supplies, resistor construction and main power supply are the largest unresolved cost items. Exceptional import duties can exceed the delivery/tax allowance.', 'SmallCustom')

story.append(PageBreak())
add('Component-level planning BOM', 'TitleCustom')
add('Quantities below are per mono channel. Candidate part numbers are not approvals for assembly. Unselected items are intentionally marked TBD.', 'BodyText')
table([
    ['<b>Function / quantity</b>', '<b>Candidate or target</b>', '<b>Price basis / status</b>'],
    ['SiC MOSFET / 64', 'Wolfspeed C3M0350120D', '$3.30 each; $211.20 for 64 [1]. Candidate; spares included in budget.'],
    ['Isolated gate driver / 64', 'Texas Instruments UCC21750DWR', '$3.28 each; $209.92 for 64 [2]. Candidate; protection/bias design incomplete.'],
    ['Precision assemblies / 34', 'ERA-8AEB1693V candidate; 3,052 chips across 34 assemblies', 'About $475 fitted / $570 with reserve. See page 4: pulse compliance unresolved.'],
    ['Floating driver bias / 32 domains', 'Topology and MPNs TBD; shared lower-side bias also required', '$400-800 allowance. Converter price benchmark: about $11.23 each [3].'],
    ['Output transformer / 1', 'Lundahl LL1679 PP, working candidate', '$299 listing [4]; $300-400 allowance. Final qualification pending.'],
    ['Gate series resistors / 128', 'RC0603FR-0710RL; provisional 10 ohm', 'Included in other passives. Pulse rating and final resistance pending.'],
    ['Gate-source bleeds / 64', 'RC0603FR-0710KL; provisional 10 kohm', 'Included in other passives; final value pending.'],
    ['Output-side bypass / 128', 'GRM32ER71E226KE15L; nominal 22 uF / 25 V', 'Included in other passives. Effective capacitance at bias pending.'],
    ['Input bypass / 64', '2.2 uF target; MPN TBD', 'Included in other passives; package/rating pending.'],
    ['Digital control / 1 set', 'FPGA, clock, configuration and audio interface; TBD', '$100-250 allowance. FPGA vendor/device selection deferred.'],
    ['Main + auxiliary power / 1 set', 'TBD', '$300-800 allowance for eventual device supplies; not a laboratory HV source quote.'],
    ['PCB + enclosure / 1 set', 'Board count, stackup and sizes TBD', 'PCB $150-350; mechanics $150-350. No assembly labor.'],
], [133, 178, 194])
add('No double counting: gate resistors, bleeds and bypass capacitors are sub-items of the $120-250 passives/protection/connectors allowance, not additional budget lines. Bias-specific circuitry is included in the separate bias allowance.', 'SmallCustom')

story.append(PageBreak())
add('Assumptions and price references', 'TitleCustom')
add('<b>Precision resistors are purchasable.</b> A representative Yageo 100 kohm, 0.1% part is listed at $0.22 [5]. This demonstrates availability, not suitability for our HV network. Voltage rating, dissipation, voltage coefficient, temperature tracking and ratio accuracy must determine the actual assemblies. Tighter grades or extensive selection may exceed the allowance.')
add('<b>Bias supply price benchmark only.</b> RECOM R12P21503D is listed around $11.23 at quantity 25 [3]; 32 units would be about $360 before supporting circuitry. Its +15/-3 V outputs differ from the present +15/-4 V model. It is not a selected replacement. Isolation test voltage does not establish continuous working-voltage suitability. The 64 logical bias interfaces in the schematic do not imply 64 physical converters.')
add('<b>Bare boards.</b> The allowance covers small batches of several possible board types. JLCPCB advertises prototype offers from $2 under specific conditions [6]; that is not a quotation for this design. Final dimensions, stackup, isolation features and board quantities are unknown. Assembly labor is excluded.')
add('<b>Excluded:</b> engineering labor, soldering/assembly labor, paid qualification work, oscilloscope, HV probes, precision resistance metrology, audio analyzer and a separately purchased laboratory HV power supply. The contingency covers limited rework or replacement stock, not an unlimited redesign.')
add('<b>Stereo indication:</b> approximately USD 5,000-9,000, assuming some shared control and power infrastructure. This is an architectural allowance, not a second detailed BOM. Power stages and output transformers largely duplicate.')
add('<b>Before purchase:</b> finalize resistor assemblies and driver bias, qualify the transformer and protection implementation, select main power and digital interfaces, then obtain distributor carts and PCB quotes. Simulation results do not qualify real-core distortion, insulation or thermal performance.')
add('Price snapshot and sources', 'Heading2')
sources = [
    ('1', 'Mouser - C3M0350120D; $3.30 at quantity 10', 'https://www.mouser.com/en/ProductDetail/Wolfspeed/C3M0350120D?qs=GedFDFLaBXHDzYoU6vvUCA%3D%3D'),
    ('2', 'DigiKey - UCC21750DWR; $3.28 at quantity 25', 'https://www.digikey.com/en/products/detail/texas-instruments/UCC21750DWR/12320381'),
    ('3', 'DigiKey - R12P21503D; $11.2336 at quantity 25', 'https://www.digikey.com/en/products/detail/recom-power/R12P21503D/7354331'),
    ('4', 'Erhard Audio - Lundahl output transformers; LL1679 $299', 'https://www.erhard-audio.com/OutputTransformers.html'),
    ('5', 'DigiKey - Yageo RT1206BRD07100KL; $0.22 at quantity 1', 'https://www.digikey.com/en/products/detail/yageo/RT1206BRD07100KL/1079461'),
    ('6', 'JLCPCB - prototype PCB offers and conditions', 'https://jlcpcb.com/ads/pcb-prototype'),
]
for num, label, url in sources:
    add(f'[{num}] <link href="{escape(url, {chr(34): "&quot;"})}" color="#205a88">{escape(label)}</link>', 'SmallCustom')
add('Prices researched 21 November 2026, USD unless stated otherwise; availability, duties and prices can change. Component counts: kicad/segmented/bom.csv and docs/kicad_segmented_review.md. That schematic export includes ideal interfaces and is not a purchasing BOM.', 'SmallCustom')

story.append(PageBreak())
add('Resistor-array review update', 'TitleCustom')
add('22 November 2026 | Sourcing candidate, not an HV purchasing release', 'Deck')
add('All 34 positions now have an explicit single-value implementation using <b>3,052 Panasonic ERA-8AEB1693V</b> resistors: 169 kohm, 0.1%, 1206. The nominal array resistances shift together by +0.12418%; their binary ratios are preserved. Full 4,096-code structural DC simulation passed.')
add('The published cut-tape price of $0.15558 gives <b>$474.83 fitted</b>, or <b>$569.89 for 3,663 pieces</b> with 20% reserve, before delivery/taxes. Archived stock observations exceed this quantity; they are not reservations. Selection yield for the 0.01% assembly-error target remains unknown.')
add('<link href="https://www.digikey.com/en/products/detail/panasonic-industry/ERA-8AEB1693V/3069615" color="#205a88">DigiKey: exact Panasonic candidate and price snapshot</link>', 'SmallCustom')
add('The mechanical envelope shows two 250 x 220 mm panels for one mono channel, with 1,526 resistor bodies per panel. This is a body-placement illustration, not a routed or insulation-qualified PCB. Array and thermal-system fabrication costs remain provisional.')
add('<b>Thermal screen:</b> the ideal 650 V-scaled model dissipates 25.28 W in the resistors on a full-scale sine and up to 40 W across static codes, approximately 20 W per panel at the maximum. The heater and cooler must be evaluated against this load; the 50 C setpoint is not yet selected.')
add('<b>New qualification concern:</b> DC sharing is insufficient to qualify the 150 V chips for fast switching. In an assumed six-resistor fixture with 0.1 pF per internal node to ground and 0.05 pF across each resistor, a 20 ns source edge produces a peak equivalent to about 385 V on one chip when scaled to 650 V. This is a sensitivity result, not a measured board voltage or proof of physical failure. Repetitive pulse limits and actual parasitics must be resolved.')
add('Aluminum-backed material also adds capacitance. It remains an option for thermal evaluation, not a selected substrate. The original resistor allowance is retained as a planning range; neither that allowance nor this candidate authorizes purchase for HV assembly.')
add('Reproducible detail: docs/resistor_array_candidate.md, docs/resistor_array_preliminary.md, calc/resistor_array_design.py and calc/resistor_array_preliminary.py. Preliminary screens are complete; full amplifier validation remains open.', 'SmallCustom')

def footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(colors.HexColor('#cad7e0'))
    canvas.line(45, 40, w-45, 40)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#567083'))
    canvas.drawString(45, 27, 'HV-RDAC | Predicted BOM | Rev 0.2 | USD | Planning only')
    canvas.drawRightString(w-45, 27, str(doc.page))
    canvas.restoreState()

doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=45, leftMargin=45, topMargin=40, bottomMargin=53,
                        title='HV-RDAC - Predicted Bill of Materials', author='HV-RDAC Project')
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
