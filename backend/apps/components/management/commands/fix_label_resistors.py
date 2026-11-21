"""
Generic resistors made from a schematic label whose value token was really a clock net, a chip name or a
neighbouring part's spec ('33R_0402 48M_BUF' became 48 MΩ, '12M_XO' 12 MΩ, 'IT8712F/IX 8M' 8 MΩ). Each label was
read against its schematic page (2026-11-21); the table below says what the part really is. A placement whose
label is in the table moves to the right generic part (made if missing) with the purpose appended to its note, or is
deleted when the label named a chip or a regulator block rather than a resistor. Labels the sheet could not settle
are left alone and listed. The emptied megohm part is deleted with its rendering.

    manage.py fix_label_resistors [--apply]
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.components.models import Component, ComponentImage, ProductComponent
from apps.products.schematic_values import generic_name

LABEL = re.compile(r"^schematic label '([^']*)'")
DELETE = 'delete'

# label -> (ohms, tolerance, package, purpose) or (DELETE, reason)
FIX = {
    # clock nets: the series terminator beside the net name
    '12M_XO': (10e6, None, '0603', 'feedback resistor across the 12 MHz USB crystal (10M/6/X on the GA-7N400 sheet, not fitted)'),
    '33R 12M': (33, None, None, 'series resistor on the 12 MHz clock'),
    '1M 12M-16pf-HC49S-D': (1e6, None, None, 'feedback resistor across the 12 MHz crystal'),
    '2.2R ESR<12m': (2.2, None, None, "2.2 Ω; 'ESR<12m' is the neighbouring capacitor's spec"),
    '2.2R1%/5 ESR<12m': (2.2, '1%', '0805', "2.2 Ω 1 %; 'ESR<12m' is the neighbouring capacitor's spec"),
    '4.7K 14.3M': (4.7e3, None, None, 'pull resistor beside the 14.3 MHz clock net'),
    '475RST 14M-32pf-HC49S-D DCLKA0 DCLKA1': (475, None, None, 'clock generator IREF resistor; the 14 MHz crystal is the neighbour'),
    '475RST 14M-32pf-HC49S-D': (475, None, None, 'clock generator IREF resistor; the 14 MHz crystal is the neighbour'),
    'MS-3_14M': (22, None, None, '22 Ω series terminator on the 14 MHz clock to the MS-3 (MS-6593 sheet)'),
    'X_0 MS-3_14M': (0, None, None, 'jumper on the 14 MHz clock line, not fitted (X_)'),
    'R3G4 R3F6 R3G3 X_33 14M_ICH_SEL1_R R3F4': (33, None, None, '33 Ω on the 14 MHz ICH clock select, not fitted (X_)'),
    '4.7K_0402 14M_ICH': (4.7e3, None, '0402', 'pull resistor beside the 14 MHz ICH clock'),
    '128M': (DELETE, 'RV350/RV351 is the Radeon 9600 GPU block (128 MB), not a resistor'),
    '16M': (DELETE, 'RN50 is the ATI RN50 graphics chip (16 MB DDRAM), not a resistor network'),
    'IT8712F/IX 8M': (DELETE, 'RN50 is the ATI RN50 graphics chip; 8M is the firmware hub size'),
    '0.36A P1V8_VGA AIC-7902 7000M': (DELETE, 'VR1/VR6 are linear regulator blocks in the power-delivery table; 7000M is the Radeon 7000M'),
    '0R RTL8201CL 100M': (0, None, None, '0 Ω jumper beside the RTL8201CL 10/100M PHY'),
    '0R 100M': (0, None, None, '0 Ω jumper on a 100 MHz clock line'),
    '100M 100M': (4.7e3, None, '0402', 'strap resistor from the RS780 reference-clock table (R225/R228 stuffed for A12; 4.7K/4 like its neighbours)'),
    '100M_LED-': (100, None, '0603', '100 Ω series resistor for the LAN jack 100M LED (GA-8SKML sheet: R983 100/6)'),
    '_ICH_100M': (33, None, None, '33 Ω series terminator on the ICH 100 MHz clock (P4SD-LA sheet: R11 33)'),
    'X_0R_0402 100m_delay': (0, None, '0402', '0 Ω jumper, not fitted (X_); 100m_delay is the net'),
    '75_1%_0402 MDI1+ 10/100M': (75, '1%', '0402', '75 Ω MDI termination on the 10/100M PHY'),
    '1K/8P4R/4 1110000 1110001 P3V3 "0" "1"': (1e3, None, '0402', '1 kΩ 8P4R resistor network; 1110000/1110001 are strap nets'),
    '510/8P4R/6 1110000 1110001 P3V3': (510, None, '0603', '510 Ω 8P4R resistor network; 1110000/1110001 are strap nets'),
    '649K 1.3MOhm 200KHz ISEN2': (649e3, '1%', None, 'PWM frequency-set resistor; the sheet note says 1.3M would give 200 kHz, 649K is fitted'),
    '1M5%0402 1394_XI 1394_XO': (1e6, '5%', '0402', '1 MΩ feedback resistor across the 1394 crystal'),
    '20_0805 6.3V 21m': (20, None, '0805', "20 Ω; '6.3V 21m' is the neighbouring capacitor's spec"),
    'X_1M X_24M-16pf-HC49S-D': (1e6, None, None, '1 MΩ across the 24 MHz crystal, not fitted (X_)'),
    '22/6 24M': (22, None, '0603', '22 Ω series terminator on the 24 MHz clock'),
    '1M 24M-16pf-HC49S-D': (1e6, None, None, '1 MΩ feedback resistor across the 24 MHz crystal'),
    '4.7KR_0402 H:24M L:48M*': (4.7e3, None, '0402', 'strap resistor selecting 24/48 MHz'),
    'X_300 25M-18PF-HC49S-D': (300, None, None, '300 Ω beside the 25 MHz crystal, not fitted (X_)'),
    '25M 1.25MHz 3.125MHz 2.25MHz': (DELETE, 'R600 is a clock-option strap named in a note; the sheet gives no value'),
    '1M 25M-18pf-HC49S-D': (1e6, None, None, '1 MΩ feedback resistor across the 25 MHz crystal'),
    'X_0 25M_X1': (0, None, None, '0 Ω jumper on the 25 MHz crystal line, not fitted (X_)'),
    '200_1% 25M_O': (200, '1%', None, '200 Ω 1 % on the 25 MHz oscillator output'),
    '0/6/SHT/X VCC3A_BK 3VDUAL 1500u/D/6.3V/AD/26m 10u/1210/X7R/25V/K/X 10A': (0, None, '0603', "0 Ω jumper (SHT), not fitted; '26m' is a capacitor's ESR"),
    '0/4/SHT/X 1000U/D/6.3V/8C/30m': (0, None, '0402', "0 Ω jumper (SHT), not fitted; '30m' is a capacitor's ESR"),
    '0/6/SHT/X VCC3A_BK 3VDUAL 1000u/D/6.3V/8C/30m 10u/1210/X7R/25V/K 10A': (0, None, '0603', "0 Ω jumper (SHT), not fitted; '30m' is a capacitor's ESR"),
    '8.2K/8P4R/6 1000u/D/25V/AU/31m 1000u/D/25V/AU/31m': (8.2e3, None, '0603', "8.2 kΩ 8P4R network; '31m' is a capacitor's ESR"),
    '1000u/D/6.3V/8C/36m/[11CL1-8C1001-13R] 2.7K/8P4R/4 -REQ3 -REQ1 -REQ2 -REQ4': (2.7e3, None, '0402', "2.7 kΩ 8P4R network; '36m' is a capacitor's ESR"),
    '47/6/1/[10RC3-00470A-22R] 100u/D/10V/5B/580m/[11CL2-5B1000-01R]': (47, '1%', '0603', "47 Ω 1 %; '580m' is a capacitor's ESR"),
    '0/6/SHT/X NTD4858NAT4G/TO252/1644pF/6.5m/X': (0, None, '0603', "0 Ω jumper (SHT), not fitted; '6.5m' is the MOSFET's Rds(on)"),
    '0/6/SHT/X DRVL2 >20mils NTMFS4841NH/SO8/1436pF/7m BAT54A/SOT23/200mA': (0, None, '0603', "0 Ω jumper (SHT), not fitted; '7m' is the MOSFET's Rds(on)"),
    '0/6/SHT/X DRVL2 >20mils NTMFS4841NH/SO8/1436pF/7m BAT54A/SOT23/200mA DRVH2': (0, None, '0603', "0 Ω jumper (SHT), not fitted; '7m' is the MOSFET's Rds(on)"),
    '0/6/SHT/X 9.5m': (0, None, '0603', "0 Ω jumper (SHT), not fitted; '9.5m' is the inductor's DCR"),
    '0/6/SHT/X 2.8uH/V/20A/3P/T5052/D 9.5m': (0, None, '0603', "0 Ω jumper (SHT), not fitted; '9.5m' is the inductor's DCR"),
    '0/6/SHT/X 2SK3918/TO252/1300pF/7.5m 2SK3918/TO252/1300pF/7.5m': (0, None, '0603', "0 Ω jumper (SHT), not fitted; '7.5m' is the MOSFET's Rds(on)"),
    '100/SHT/X STD1703LT4/TO252/330pF/50m': (100, None, None, "100 Ω, not fitted; '50m' is the MOSFET's Rds(on)"),
    '0/4S/X 2SK3019/SC75/8000m/X': (0, None, '0402', "0 Ω jumper, not fitted; '8000m' is the MOSFET's Rds(on)"),
    '0R/X 3230000000': (0, None, None, '0 Ω jumper, not fitted (X); 3230000000 is a net label'),
    '0R 3230000000': (0, None, None, '0 Ω jumper; 3230000000 is a net label'),
    '27M_SEL': (33, None, '0402', '33 Ω series terminator on the SIO 33 MHz PCI clock (MS-7565 sheet: R124 33R0402)'),
    '27M_INT': (10e3, None, '0603', '10 kΩ pull-down on the clock generator REF27 pin (GA-8TRS300M sheet: R392 10K/6)'),
    '300RST P45N02LD/45A/28m/TO252': (300, None, None, "300 Ω; '28m' is the MOSFET's Rds(on)"),
    '3m': (0.003, None, None, '3 mΩ current-sense resistor in the VRM output (MS-6341 sheet)'),
    '3m 2.5u': (0.003, None, None, '3 mΩ current-sense resistor after the 2.5 µH VRM choke (MS-6515 sheet: R47)'),
    '3m/R_sense': (0.003, None, None, '3 mΩ current-sense resistor after the VRM choke (MS-6389 sheet: R5 3m/R_sense)'),
    '3m 2W': (0.003, None, None, '3 mΩ 2 W current-sense resistor after the VRM choke (MS-6137 sheet: R46)'),
    '3.3m 26.1K1%0402': (26.1e3, '1%', '0402', "26.1 kΩ 1 %; '3.3m' is a neighbouring spec"),
    '33MOHM/X 1210': (0.033, '1%', '1210', '33 mΩ 1210 RC-snubber resistor across the low-side MOSFET, not fitted (GV-R630X5ZA sheet: R719 Rs)'),
    '10K/X 402 M GPIO12': (10e3, None, None, '10 kΩ on GPIO12, not fitted (X)'),
    'X_10K 402 M': (10e3, None, None, '10 kΩ, not fitted (X_)'),
    'NV44M-V U100K 43M': (0, None, None, '0 Ω series on DDC_CLK (A6VC sheet: R8 0Ohm); NV44M-V/43M is the GPU'),
    '4.7K 24_48M 1.5X 24_48M': (4.7e3, None, None, 'strap resistor on the 24/48 MHz select'),
    '4.7K 12_48M 200 133 100 100': (4.7e3, None, None, 'strap resistor on the 12/48 MHz select'),
    '_CLK_48M': (33, None, None, '33 Ω series terminator on the 48 MHz USB clock (Z96JM sheet: R285 33Ohm CLK_48M)'),
    '48M': (33, None, None, '33 Ω series terminator on the 48 MHz clock (MS-6535 sheet: R118 33)'),
    '33R **FS3/48M_0': (33, None, None, '33 Ω series terminator on the 48 MHz clock'),
    '33R_0402 48M_BUF': (33, None, '0402', '33 Ω series terminator on the buffered 48 MHz clock'),
    '33R_0402 48M_BUF PCICLK0': (33, None, '0402', '33 Ω series terminator on the buffered 48 MHz clock'),
    '33_0402 48M_BUF': (33, None, '0402', '33 Ω series terminator on the buffered 48 MHz clock'),
    '0/6/X 4M': (0, None, '0603', '0 Ω jumper, not fitted (X); 4M is a net'),
    'X_4.7K 2MB 4MB 4M 2M': (4.7e3, None, None, '4.7 kΩ flash-size strap, not fitted (X_)'),
    '0/6S/X FANIO1 FANIO2 4M -TK00 FANPWM3': (0, None, '0603', '0 Ω jumper, not fitted (X); 4M is a net'),
    'X_0 XA18R 2MB 4MB 4M 2M': (0, None, None, '0 Ω flash-size strap, not fitted (X_)'),
    'X_0_0603 4M': (0, None, '0603', '0 Ω jumper, not fitted (X_); 4M is a net'),
    '.47K 1% 6N03LA/50A/5.4m/TO252': (470, '1%', None, "470 Ω 1 %; '5.4m' is the MOSFET's Rds(on)"),
    '301_1% 370mΩ': (301, '1%', None, "301 Ω 1 %; '370mΩ' is a neighbouring spec"),
    'X_1K 66M-5V-DH': (1e3, None, None, '1 kΩ beside the 66 MHz clock, not fitted (X_)'),
    '1K 128KB 64KB 66M SHD[15..0]': (1e3, None, None, '1 kΩ strap resistor beside the 66 MHz clock'),
    '33R 3V_66M_3 3V_66M_2': (33, None, None, '33 Ω series terminator on the 66 MHz clock'),
    '1K 66M-5V-DH 115 PCIRST-2 GNT6-': (1e3, None, None, '1 kΩ beside the 66 MHz clock'),
    '8M16 10k 5%': (10e3, '5%', None, '10 kΩ 5 %; 8M16 is a net'),
    'X_0 8M ADDR18 ADDR16 ADDR15 5/19': (0, None, None, '0 Ω address strap, not fitted (X_)'),
    '255/6/1 -DOT_96M -DOT_96M 3VDDCCL': (255, '1%', '0603', '255 Ω 1 % on the 96 MHz dot clock'),
    '255/6/1 -DOT_96M -DOT_96M 3VDDCCL [13] [13]': (255, '1%', '0603', '255 Ω 1 % on the 96 MHz dot clock'),
    '0/4S/X -DOT96M -DOT_96M': (0, None, '0402', '0 Ω jumper on the 96 MHz dot clock, not fitted (X)'),
    '33/0402 -DOT_96M': (33, None, '0402', '33 Ω series terminator on the 96 MHz dot clock'),
    '1394_33M': (33, None, '0603', '33 Ω series terminator on the 1394 33 MHz clock (MS-9157 sheet: 33/6)'),
}
# labels whose sheet did not settle the value; reported, never changed
UNSETTLED = {
    'G G MDIO3- 0.01uf 10/100M': 'MS-7204 R23/R41/R64: the designators on the sheet are BGA pin names, the resistor was not found',
    'AP40T03H/TO252/655pF/25m LD8104PS/SO16 U8C': "the label is a MOSFET's spec; the resistor's own value is not in it",
    'P45N02LD/45A/28m/TO252': "the label is a MOSFET's spec; the resistor's own value is not in it",
    '0603 15V 30W@25C 220A 5% 4mR': "0603 5 % with a MOSFET's spec; value not in the label",
    '0603 15V 5% 15W@25C 120A 6.7mR': "0603 5 % with a MOSFET's spec; value not in the label",
    'LM324DR/SO14 U98C 2SK3918/TO252/1300pF/7.5m': "the label is a MOSFET's spec; value not in it",
    '0.1u/4/X7R/16V/K 5V_DRV (38) 2SK3918/TO252/1300pF/7.5m': "capacitor and MOSFET specs; the resistor's value is not in the label",
    '2SK3918/TO252/1300pF/7.5m': "the label is a MOSFET's spec; value not in it",
    '0.1u/4/X7R/16V/K/X 5V_DRV 2SK3918/TO252/1300pF/7.5m': "capacitor and MOSFET specs; the resistor's value is not in the label",
    '0.1u/4/X7R/16V/K (37) 2SK3918/TO252/1300pF/7.5m': "capacitor and MOSFET specs; the resistor's value is not in the label",
    '66M_NB': 'P4I45GL/P4I45PE R4: the designator on the sheet is a BGA pin name, the resistor was not found',
    'X_60M JBAT1': 'MS-6176 R109: drawn as X_60M beside the CMOS-clear jumper, not fitted; the sheet gives nothing better',
    '16.5 1% =10/7 M (9)': 'P5BW R113: the sheet reads 20.5 1% (HRCOMP), the label 16.5; not settled',
}
EXCLUDE = {('3m', 'T75AL2'): 'Asus T75AL2 R390: "3m" sits on the +BATSB line where a sense resistor makes no sense; left alone'}


def label_of(note):
    m = LABEL.match(note or '')
    return m.group(1) if m else None


def target_name(ohm, tol, pkg):
    specs = {'resistance_ohm': ohm}
    if tol:
        specs['tolerance'] = tol
    return generic_name('resistor', specs, pkg), specs


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='make the changes (default: report only)')

    def handle(self, *args, **opts):
        apply = opts['apply']
        n = {'placements moved': 0, 'placements deleted': 0, 'duplicates dropped': 0, 'parts made': 0, 'parts deleted': 0, 'renderings deleted': 0, 'left unsettled': 0, 'excluded': 0}
        per_label = {}
        with transaction.atomic():
            parts = Component.objects.filter(manufacturer__iexact='Generic', component_type='resistor', specifications__resistance_ohm__gte=1e6)
            touched = set()
            for pc in ProductComponent.objects.filter(component__in=parts, notes__startswith='schematic label').select_related('product', 'component').order_by('component__part_number'):
                lab = label_of(pc.notes)
                if lab in UNSETTLED:
                    n['left unsettled'] += 1
                    continue
                if lab not in FIX:
                    continue
                if (lab, pc.product.model_number) in EXCLUDE:
                    n['excluded'] += 1
                    continue
                entry = FIX[lab]
                per_label[lab] = per_label.get(lab, 0) + 1
                old = pc.component
                touched.add(old.pk)
                if entry[0] == DELETE:
                    n['placements deleted'] += 1
                    if apply:
                        pc.delete()
                    continue
                ohm, tol, pkg, purpose = entry
                name, specs = target_name(ohm, tol, pkg)
                if not apply:
                    n['placements moved'] += 1
                    continue
                target = Component.objects.filter(manufacturer__iexact='Generic', part_number__iexact=name).first()
                if target is None:
                    target = Component.objects.create(manufacturer='Generic', part_number=name, component_type='resistor', package_type=pkg or '',
                                                      description=f'Generic resistor: {name}', specifications=specs, created_by=old.created_by)
                    n['parts made'] += 1
                dup = pc.reference_designator and ProductComponent.objects.filter(component=target, product=pc.product, reference_designator=pc.reference_designator).exists()
                if dup:
                    pc.delete()
                    n['duplicates dropped'] += 1
                    continue
                pc.component = target
                pc.notes = f"{pc.notes}; read against the schematic 2026-11-21: {purpose}"[:1000]
                pc.save()
                target.update_usage_count()
                n['placements moved'] += 1
            if apply:
                for pk in touched:
                    part = Component.objects.filter(pk=pk).first()
                    if part is None:
                        continue
                    part.update_usage_count()
                    if part.usage_count == 0:
                        ours = ComponentImage.objects.filter(component=part, source_notes__startswith='[component-image]')
                        n['renderings deleted'] += ours.count()
                        ours.delete()
                        if not (part.images.exists() or part.datasheets.exists() or part.substitutes.exists() or part.substitute_for.exists()
                                or part.product_requests.exists() or part.recipe_components.exists()):
                            self.stdout.write(f'deleted the empty part {part.part_number!r}')
                            part.delete()
                            n['parts deleted'] += 1
        for lab, k in sorted(per_label.items(), key=lambda x: -x[1]):
            e = FIX[lab]
            self.stdout.write(f'{k:3d} x {lab!r} -> ' + (f'DELETE ({e[1]})' if e[0] == DELETE else f'{target_name(e[0], e[1], e[2])[0]!r}: {e[3]}'))
        for lab, why in UNSETTLED.items():
            self.stdout.write(f'unsettled {lab!r}: {why}')
        self.stdout.write(('' if apply else 'DRY RUN - ') + ', '.join(f'{k} {v}' for k, v in n.items()))
