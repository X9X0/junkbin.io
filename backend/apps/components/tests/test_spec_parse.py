"""
Tests for apps.components.spec_parse: ratings from description text and part numbers.
Every case is a real line or part number from the imported BOMs and parts lists.
"""
import pytest

from apps.components.spec_parse import clean_bom_text, decode_mpn, derive, ic_package, parse_description


@pytest.mark.parametrize('text, kind, specs, package', [
    # Asus factory BOM lines
    ('P MLCC 15PF/50V (0402) NPO 5% TAIYO/UMK105CH150JW-F', 'capacitor',
     {'capacitance_pf': 15.0, 'voltage_v': 50.0, 'tolerance': '5%', 'dielectric': 'C0G'}, '0402'),
    ('P RES 576 OHM 1/10W(0603)1% YAGEO/RC0603FR-07576RL <G>', 'resistor',
     {'resistance_ohm': 576.0, 'tolerance': '1%', 'power_w': 0.1}, '0603'),
    ('P MLCC 2.7PF/50V(0402)NPO 0.25PF MURATA/GRM1555C1H2R7CZ01D', 'capacitor',
     {'capacitance_pf': 2.7, 'voltage_v': 50.0, 'tolerance': '±0.25pF', 'dielectric': 'C0G'}, '0402'),
    ('P MLCC 0.1UF/10V(0402)Y5V-80+20% MURATA/GRM155F51A104Z', 'capacitor',
     {'capacitance_pf': 100000.0, 'voltage_v': 10.0, 'tolerance': '+80/-20%', 'dielectric': 'Y5V'}, '0402'),
    ('P INDUCTOR 0.1UH/300mA (0603) 5% MAG.LAYERS/HFI-160808-R10J', 'inductor',
     {'inductance_uh': 0.1, 'current_a': 0.3, 'tolerance': '5%'}, '0603'),
    ('FERRITE BEAD(0603)600OHM/200mA MURATA/BLM18BD601SN1D', 'ferrite',
     {'impedance_ohm': 600.0, 'current_a': 0.2}, '0603'),
    ('P C.M. CHOKE(0805)120OHM/370mA CHILISIN/CMM21T-121M-N', 'cm_choke',
     {'impedance_ohm': 120.0, 'current_a': 0.37}, '0805'),
    ('XTAL 25MHZ DIP 49US 20PF/30PPM TQG/XP025000-203143BN <G>', 'crystal',
     {'frequency_mhz': 25.0, 'load_pf': 20.0, 'tolerance_ppm': 30}, '49US'),
    ('P RES A 33K OHM(0603)5% 4R8P RALEC/RTA03-4D333JTP', 'res_array',
     {'resistance_ohm': 33000.0, 'tolerance': '5%', 'configuration': '4R8P', 'size_on_bom': '0603'}, None),
    ('P CAP TAN 100U/6.3V (3528/B) AVX/TAJB107M006RNJ', 'capacitor',
     {'capacitance_pf': 100000000.0, 'voltage_v': 6.3, 'dielectric': 'tantalum'}, '3528 (B case)'),
    ('P CAP PL 330UF/16V 10*12.5 DIP FUJITSU/FP-016RE331M-SUC <G>', 'capacitor',
     {'capacitance_pf': 330000000.0, 'voltage_v': 16.0, 'dielectric': 'polymer'}, 'Radial 10x12.5 mm'),
    ('THERMISTOR 10K OHM (0603) 3% TKS/TSM1A103H34D1RZ', 'thermistor',
     {'resistance_ohm': 10000.0, 'tolerance': '3%'}, '0603'),
    # Samsung service-manual records: metric sizes
    ('C-CER,CHIP;1000nF,10%,6.3V,X7R,1608', 'capacitor',
     {'capacitance_pf': 1000000.0, 'voltage_v': 6.3, 'tolerance': '10%', 'dielectric': 'X7R'}, '0603'),
    ('R-CHIP;470ohm,5%,1/10W,TP,1608', 'resistor', {'resistance_ohm': 470.0, 'tolerance': '5%', 'power_w': 0.1}, '0603'),
    ('C-AL,SMD;100uF,20%,25V,WT,TP,8.3x8.3x10', 'capacitor',
     {'capacitance_pf': 100000000.0, 'voltage_v': 25.0, 'tolerance': '20%', 'dielectric': 'electrolytic'},
     'SMD 8.3x8.3x10 mm'),
    # Sharp / AOC / Sanyo shorthand
    ('CAP CHIP 0402 470PF J 50V NPO', 'capacitor',
     {'capacitance_pf': 470.0, 'voltage_v': 50.0, 'tolerance': '5%', 'dielectric': 'C0G'}, '0402'),
    ('RST CHIP 53K6 1/10W 1%', 'resistor', {'resistance_ohm': 53600.0, 'tolerance': '1%', 'power_w': 0.1}, None),
    ('RST 1206 1.2R 1% 1/4W -', 'resistor', {'resistance_ohm': 1.2, 'tolerance': '1%', 'power_w': 0.25}, '1206'),
    ('RST CHIPR 1.5 MOHM +-5% 1/4W', 'resistor', {'resistance_ohm': 1500000.0, 'tolerance': '5%', 'power_w': 0.25}, None),
    # contributor prose
    ('Electrolytic capacitor, ±20% tolerance, 160V rating', 'capacitor',
     {'voltage_v': 160.0, 'tolerance': '20%', 'dielectric': 'electrolytic'}, None),
    ('Ceramic capacitor, ±10% tolerance, 2kV rating', 'capacitor', {'voltage_v': 2000.0, 'tolerance': '10%'}, None),
    ('Metal glaze chip resistor, 1/16W, 680 Ω', 'resistor', {'resistance_ohm': 680.0, 'power_w': 0.0625}, None),
    ('Thick Film Resistors - SMD 3.3 Ohms 62.5 mW 0402 5%', 'resistor',
     {'resistance_ohm': 3.3, 'power_w': 0.0625, 'tolerance': '5%'}, '0402'),
])
def test_parse_description(text, kind, specs, package):
    assert parse_description(text) == (kind, specs, package)


@pytest.mark.parametrize('text', [
    'CRYSTAL CS4297A-JQ TQFP48 AC97,D AUDIO CODEC',      # Crystal Semiconductor, the maker
    'P COMMON CHOKE FOR IEEE1394 SINKA/OD6560T-E301F',    # a choke, but no value to read
    'Fuse holder',
])
def test_no_false_values(text):
    kind, specs, _ = parse_description(text)
    assert kind != 'crystal' and kind != 'fuse' and not specs


def test_clean_bom_text_drops_markers_and_the_maker_part_echo():
    assert clean_bom_text('P MLCC 15PF/50V (0402) NPO 5% TAIYO/UMK105CH150JW-F <G>') == 'MLCC 15PF/50V (0402) NPO 5%'
    assert clean_bom_text('P WtoB CON 4P,1.25mm,S/T,SMT ACES/85205-0470N 虛擬料件: 59-NQNMB1000-A01PT') == \
        'WtoB CON 4P,1.25mm,S/T,SMT'
    assert clean_bom_text('DDR DIMM 184P,400/333 NY,G/F AMP/1470069-1') == 'DDR DIMM 184P,400/333 NY,G/F'
    assert clean_bom_text('Metal film resistor, ±1% tolerance') == 'Metal film resistor, ±1% tolerance'


@pytest.mark.parametrize('maker, pn, expected', [
    ('YAGEO', 'RC0603FR-0720KL', ('resistor', {'resistance_ohm': 20000.0, 'tolerance': '1%', 'power_w': 0.1}, '0603')),
    ('YAGEO', 'CC0402JRNPO9BN150', ('capacitor', {'capacitance_pf': 15.0, 'voltage_v': 50, 'tolerance': '5%',
                                                  'dielectric': 'C0G'}, '0402')),
    ('TA-I', 'RM06FTN2002', ('resistor', {'resistance_ohm': 20000.0, 'tolerance': '1%'}, '0603')),
    ('Walsin', 'WR06X5760FTL', ('resistor', {'resistance_ohm': 576.0, 'tolerance': '1%'}, '0603')),
    ('Walsin', '0402N101J500LT', ('capacitor', {'capacitance_pf': 100.0, 'voltage_v': 50, 'tolerance': '5%',
                                               'dielectric': 'C0G'}, '0402')),
    ('UNI-OHM', '0402WGF165JTCE', ('resistor', {'resistance_ohm': 16.5, 'tolerance': '1%'}, '0402')),
    ('RALEC', 'RTT0210R0FTH', ('resistor', {'resistance_ohm': 10.0, 'tolerance': '1%'}, '0402')),
    ('Murata', 'GRM155R60J105ME19D', ('capacitor', {'capacitance_pf': 1000000.0, 'voltage_v': 6.3, 'tolerance': '20%',
                                                    'dielectric': 'X5R'}, '0402')),
    ('Samsung', 'CL05C150JB5NNNC', ('capacitor', {'capacitance_pf': 15.0, 'voltage_v': 50, 'tolerance': '5%',
                                                  'dielectric': 'C0G'}, '0402')),
    ('DARFON', 'C1005NP0229CGT', ('capacitor', {'capacitance_pf': 2.2, 'tolerance': '±0.25pF', 'dielectric': 'C0G'},
                                  '0402')),                                  # EIA '9' = x0.1
    ('TAIYO YUDEN', 'UMK105CH150JW-F', ('capacitor', {'capacitance_pf': 15.0, 'voltage_v': 50, 'tolerance': '5%',
                                                      'dielectric': 'CH'}, '0402')),
    ('Panasonic', 'ERJ3GEYG822', ('resistor', {'resistance_ohm': 8200.0, 'tolerance': '2%'}, '0603')),
    ('Panasonic', 'ERJ3RBD133', ('resistor', {'resistance_ohm': 13000.0, 'tolerance': '0.5%'}, '0603')),
    ('Panasonic', 'ERJ12YJ100', ('resistor', {'resistance_ohm': 10.0, 'tolerance': '5%'}, '1812')),
    ('Panasonic', 'ERJ12ZYJ100', ('resistor', {'resistance_ohm': 10.0, 'tolerance': '5%'}, '2010')),
    ('Panasonic', 'ERJ6GEY0R00', ('resistor', {'resistance_ohm': 0.0}, '0805')),
])
def test_decode_mpn(maker, pn, expected):
    assert decode_mpn(maker, pn) == expected


def test_unknown_or_other_makers_part_numbers_are_not_decoded():
    assert decode_mpn('Sony', '1-216-685-11') is None
    assert decode_mpn('Murata', 'RC0603FR-0720KL') is None        # a YAGEO number under the wrong maker
    assert decode_mpn('TAIYO YUDEN', 'CEEMK325BJ106KN-T') is None   # prefix not understood: no guess


def test_part_number_settles_ratings_but_not_a_disputed_value():
    # the line says 10V, the Murata part is 6.3V: the part's own rating wins
    d = derive('Murata', 'GRM155R60J105ME19D', 'P MLCC 1UF/10V(0402)X5R 20% MURATA/GRM155R60J105ME19D')
    assert d['specs']['voltage_v'] == 6.3 and d['conflict'] == ['voltage_v']
    # the line says 35.7 ohm, the number (with a typo, '07735R7') 735.7: neither is filled
    d = derive('YAGEO', 'RC0603FR-07735R7L', 'RES 35.7 OHM 1/10W (0603) 1% YAGEO/ RC0603FR-07735R7L')
    assert d['specs'] == {} and d['conflict'] == ['resistance_ohm']


def test_description_that_is_another_makers_part_number_is_decoded():
    d = derive('Samsung', '2007-008403', 'ERJ1GEJ102C')
    assert d['specs'] == {'resistance_ohm': 1000.0, 'tolerance': '5%'} and d['package'] == '0201'


@pytest.mark.parametrize('text, package', [
    ('LIN REG. LTC660CS8#TR S-8 LINEAR', 'SO-8'),
    ('LIN REG.APL5331U5C-TR TO-252-5 ANPEC', 'TO-252-5'),
    ('P SW REG. MAX8725ETI      QFN-28 MAXIM', 'QFN-28'),
    ('Vref. LM431BCM3X        SOT23 NS', 'SOT-23'),
    ('C.S  FW82801FR        BGA609 INTEL ICH6R B-1,SL79N/857493', 'BGA-609'),
])
def test_ic_package(text, package):
    assert ic_package(text) == package


@pytest.mark.parametrize('line, ohms, mhz', [
    ('BEAD-SMD;30ohm,2012,TP,15.9OHM/30MHz', 30.0, None),        # 30 MHz is the second figure's
    ('FERRITE BEAD 600OHM@100MHZ 0603', 600.0, 100.0),
    ('Chip ferrite bead, 120 ohm @ 100 MHz, 0603', 120.0, 100.0),
    ('FERRITE BEAD(0603)220OHM/600mA', 220.0, None),
])
def test_bead_frequency_belongs_to_its_impedance(line, ohms, mhz):
    _, specs, _ = parse_description(line)
    assert specs.get('impedance_ohm') == ohms and specs.get('frequency_mhz') == mhz
