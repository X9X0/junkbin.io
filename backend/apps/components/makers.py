"""
One name per component maker.

Imports bring makers as their sources print them: all capitals ('YAGEO', 'SUYIN'),
squeezed or dotted ('TOPYANG', 'MAG.LAYERS'), abbreviated ('A.D', 'S.T', 'WB'),
or misspelt ('PERCIOM', 'WEISON'). A name is written with only its first letters
capitalised unless it is an acronym or a letter code ('TDK', 'KOA', 'CA', 'HR');
brands with a mixed-case style keep it ('onsemi', 'JMicron', 'SigmaTel').

    canonical_maker('YAGEO') -> 'Yageo'
    canonical_product_maker('ASUS') -> 'Asus'
    canonical_part('JVE21R2264-10S10-01G-6', '3-V1-GN') -> ('JVE', '21R2264-10S10-01G-6/3-V1-GN')
    canonical_part('Generic', 'T49J NUT H=4.0mm 宏泰') -> ('Generic', 'T49J NUT H=4.0mm Hontech')
"""
from apps.products.import_text import clean_title, has_cjk

# printed name (upper case) -> the site's name. Names not listed are kept as they are.
CANONICAL = {
    # abbreviations and misplaced words
    'A.D': 'Analog Devices', 'ANALOG': 'Analog Devices', 'ANALOG DEVICES INC.': 'Analog Devices',
    'S.T': 'STMicroelectronics', 'ST ELECTRONICS': 'STMicroelectronics',
    'WB': 'Winbond', 'JK': 'JKMT', 'PAN': 'PanJit', 'NECIEEE': 'NEC',
    'CRYSTAL': 'Cirrus Logic',                      # Crystal Semiconductor: CS4280/CS4297 codecs
    'EEPROM': 'Atmel (Microchip Technology)', 'ATM': 'Atmel (Microchip Technology)',
    'ATMEL-JEDEC': 'Atmel (Microchip Technology)',
    'LINEAR': 'Linear Technology', 'DIODES': 'Diodes Incorporated', 'CENTRAL': 'Central Semiconductor',
    'CALIFORNIA': 'California Micro Devices', 'CMD': 'California Micro Devices',
    'MICROCHIP': 'Microchip Technology', 'MCC': 'Micro Commercial Components (MCC)',
    'MXIC': 'Macronix', 'CHINGS': 'PMC (Chingis)', 'O2': 'O2Micro', 'ASMT': 'ASMedia',
    'ON-MOTOROLA': 'onsemi', 'ON SEMICONDUCTOR': 'onsemi', 'ADVANCED MICRO DEVICES': 'AMD',
    'HYNIX': 'SK hynix', 'VISHAY-SIL': 'Vishay Siliconix',
    # spelling variants and misspellings
    'TA-I TECH': 'TA-I', 'TA-ITECH': 'TA-I', 'TAI TECH': 'Tai-Tech',
    'TOP YANG': 'Top Yang', 'TOPYANG': 'Top Yang', 'MAG LAYERS': 'Mag Layers', 'MAG.LAYERS': 'Mag Layers',
    'LITE-ON': 'Lite-On', 'LITEON': 'Lite-On', 'WEISON': 'Wieson',
    'ENTRY': 'Entery',                              # Entery Industrial: same 3761/6701 connector series
    'NIKE': 'Niketech',                             # Niketech Electronic: Asus BOMs print both spellings
    'CHEMI-CON': 'Nippon Chemi-Con', 'CHEMICO': 'Nippon Chemi-Con', 'CHEMNKO': 'Chenmko',
    'LINGY': 'Lingyang', 'PAN OVER': 'Pan Overseas', 'PAN OVERS': 'Pan Overseas', 'PERCIOM': 'Pericom',
    'NIKO-SEM': 'Niko Semiconductor', 'NJRC': 'New Japan Radio', 'NEW JAPAN RADIO (NJRC)': 'New Japan Radio',
    'NEW JAPAN RADIO CO. ,LTD.': 'New Japan Radio', 'CYPRESS': 'Cypress Semiconductor',
    'ALPHA AND OMEGA SEMICONDUCTOR': 'Alpha & Omega Semiconductor',
    'INFINEON TECHNOLOGIES': 'Infineon', 'INTEL CORPORATION': 'Intel', 'JAE ELECTRONICS': 'JAE',
    'MONOLITHIC POWER SYSTEMS INC.': 'Monolithic Power Systems', 'RICHTEK TECHNOLOGY': 'Richtek',
    # brands with a mixed-case style
    'ASMEDIA': 'ASMedia', 'JMICRON': 'JMicron', 'SIGMATEL': 'SigmaTel', 'C-MEDIA': 'C-Media',
    'ALCORMICRO': 'Alcor Micro', 'KYOCERA AVX': 'Kyocera AVX', 'UNI-OHM': 'Uni-Ohm',
    'E-TRONIC': 'E-Tronic', 'HUA-JIE': 'Hua-Jie', 'TAIYO YUDEN': 'Taiyo Yuden',
}

# all-capitals names that are words, written with a leading capital
WORDS = '''
ABRACON ACES ADAPTEC AGERE ALCATEL ALLTOP ALPS AMBIZ AMCO AMPHENOL AOBA APAQ ASTRON ATHEROS AURAS AUREAL
AVIA BOTHHAND BOURNS BROADCOM CERATECH CHAMPION CHENMKO CHERRY CHIPSEA CHRONTEL CITIZEN COILCRAFT
COILTRONICS COMPOSTAR CREATIVE CYNTEC DARFON DINTECH DIPTRONICS ECERA ELITE ENTERY EUMAX FENGHUA FUJICOM
FUJITSU GOLDENBRIDGE HARVATEK HELE HIGHLY HOKURIKU HONDA HOSIDEN HOTEK INALWAYS INPAQ ISAHAYA JETCON
JOHANSON KEMET KEPO KINGBRIGHT LANKOM LATTICE LEDTECH LIGITEK LINGYANG LINKCOM LISHIN LITTELFUSE
LOVOLTECH LTEC MACHRONE MARVELL MATSUKI MATSUSHITA MAXECHO MAXWELLS MERITEC MINGSTAR MISAKI MITEL MOLDEC
MOTOROLA NETSWAP NIKETECH NVIDIA PARALIGHT PHYCOMP PINREX PROCONN PROMISE PULSE PYRAMIS RALEC
RAYCHEM RAYLOGY REISETECH RICOH ROHM SANTA SEIKO SEMITEC SHIBAURA SHOWA SILEGO SINGATRON SINKA SKYWELL
SOLTEAM SPEEDTECH SPRAGUE STAR STARCONN STARLINK SUMIDA SUYIN TAIMAG TAISOL TEAMYOUNG TEAPO TEKCON THINE
TOKO TOSHIN TOUKE TRIO VETTE WEITRON WIESON WINWIN YAGEO YAMAHA ZOWIE
'''.split()
CANONICAL.update({w: w.title() for w in WORDS})

# a maker and part number the source split in the wrong place
PART_FIXES = {
    ('JVE21R2264-10S10-01G-6', '3-V1-GN'): ('JVE', '21R2264-10S10-01G-6/3-V1-GN'),
    ('JVE21Y2264-10S10-01G-6', '3-V1-GN'): ('JVE', '21Y2264-10S10-01G-6/3-V1-GN'),
}


# product brands written in capitals by their sources: leading capital, like component makers
PRODUCT_MAKERS = {'ASUS': 'Asus', 'GIGABYTE': 'Gigabyte', 'ITEAD': 'Itead', 'XZOUND': 'Xzound', 'UNI-T': 'Uni-T'}


def canonical_product_maker(name):
    name = (name or '').strip()
    return PRODUCT_MAKERS.get(name.upper(), name)


def canonical_maker(name):
    name = (name or '').strip()
    return CANONICAL.get(name.upper(), name)


def canonical_part(manufacturer, part_number):
    """(manufacturer, part_number) as the site writes them."""
    fixed = PART_FIXES.get(((manufacturer or '').strip().upper(), (part_number or '').strip().upper()))
    if fixed:
        return fixed
    maker = canonical_maker(manufacturer)
    if maker == 'Generic' and has_cjk(part_number):
        part_number = clean_title(part_number)[:200]     # a no-part-number BOM line's name, in English
    return maker, part_number
