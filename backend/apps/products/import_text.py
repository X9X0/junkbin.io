"""
Cleaning for text that arrives with bulk imports (factory BOMs, schematic and
manual filenames, datasheet title pages).

The source material is mostly English, with a small, fixed vocabulary of
Chinese factory shorthand and filename words; those are translated exactly
from GLOSSARY. Advertising watermarks and download-site names are removed.
Whatever CJK text is left after that is dropped rather than machine-translated:
a description must not guess. clean_description() also returns '' when too
little English remains to be worth showing.
"""
import re

# exact translations of the shorthand and filename words that occur in the sources
GLOSSARY = [
    ('立式', ' vertical '), ('臥式', ' horizontal '), ('卧式', ' horizontal '), ('臥', ' horizontal '),
    ('卧', ' horizontal '), ('虛擬料件', 'phantom item'), ('虚拟料件', 'phantom item'), ('不需填寫', 'not required'),
    ('要加底線', 'with underline'), ('無', ' none '), ('无', ' none '), ('或', ' or '),
    ('線路圖', ' schematic'), ('线路图', ' schematic'), ('引脚定义', ' pinout'), ('規格書', ' datasheet'),
    ('规格书', ' datasheet'), ('中文资料', ' (Chinese)'), ('电源芯片', ' power IC'), ('供电芯片', ' power IC'),
    ('笔记本用', ' for notebooks'), ('代码', ' code'), ('寸', '"'), ('三洋', 'Sanyo '), ('海尔', 'Haier '),
    ('厦普', 'Sharp '), ('夏普', 'Sharp '),
    ('此料無需marking', 'no marking required'), ('此料无需marking', 'no marking required'),
    ('品名更新貼紙', 'model name update label'), ('主件數量', ''),
    ('液晶彩色电视维修手册', 'LCD TV service manual'), ('液晶彩电维修手册', 'LCD TV service manual'),
    ('维修手册', 'service manual'), ('維修手冊', 'service manual'), ('维修指南', 'repair guide'),
    ('电路图', ' schematic'), ('電路圖', ' schematic'), ('位置图', ' component location map'),
    ('位置圖', ' component location map'), ('点位图', ' component location map'), ('點位圖', ' component location map'),
    ('图纸', ' drawings'), ('圖紙', ' drawings'), ('数据资料', 'datasheet'), ('數據資料', 'datasheet'),
    ('液晶彩电', 'LCD TV'), ('液晶彩色电视', 'LCD TV'), ('残缺', ' (incomplete)'), ('殘缺', ' (incomplete)'),
    ('小4P', 'small 4-pin'), ('立', ' vertical '), ('燒', ' (pre-programmed)'), ('烧', ' (pre-programmed)'),
    ('及', ' and '), ('华硕', 'ASUS '), ('華碩', 'ASUS '), ('松下', 'Panasonic '), ('飞利浦', 'Philips '),
    ('飛利浦', 'Philips '), ('康佳', 'Konka '), ('创维', 'Skyworth '),
]
GLOSSARY_LONGEST_FIRST = sorted(GLOSSARY, key=lambda pair: -len(pair[0]))
FULLWIDTH = str.maketrans({'；': ';', '，': ',', '：': ':', '（': '(', '）': ')', '！': '!', '　': ' ',
                           '、': ', ', '。': '. ', '“': '"', '”': '"'})
JUNK = [
    # a Maintek BOM printout's page header that leaked into an item (company, report title, dates, parent P/N)
    re.compile(r'名碩電腦.{0,240}?主件料號\s*[:：]?\s*[\w-]*'), re.compile(r'品名規格\S*'),
    re.compile(r'(名碩電腦|匯橋|匯僑)\S*'),
    re.compile(r'捷多邦[^！!]{0,30}[！!]?'),                              # PCB-shop advert watermark
    re.compile(r'查询["“]?[^"”]{0,40}["”]?供应商'),                           # "find suppliers of ..." advert
    re.compile(r'chinafix\.com\.cn\s*迅维网_?', re.I), re.compile(r'迅维网'),
    re.compile(r'www\.xinxunwei\.com\s*(400-800-9990)?', re.I), re.compile(r'www\.ic37\.com_?', re.I),
    re.compile(r'_?DiskStation_[A-Za-z]{3}-\d{1,2}-\d{3,4}-\d{4}_DownloadConflict', re.I),
    re.compile(r'\s*\(\d\)\s*$'),                                         # browser duplicate "(1)"
]
CJK = re.compile(r'[぀-ヿ㐀-鿿가-힯＀-￯]+')


def has_cjk(text):
    return bool(CJK.search(text or ''))


def clean_text(text):
    """Glossary translation + junk removal + leftover CJK dropped; whitespace tidied."""
    if not text:
        return text or ''
    t = text
    for pattern in JUNK:
        t = pattern.sub(' ', t).strip()
    for src, dst in GLOSSARY_LONGEST_FIRST:            # '此料無需marking' before its '無'
        t = t.replace(src, dst)
    t = t.translate(FULLWIDTH)
    t = CJK.sub(' ', t)
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r' +([,;:)])', r'\1', t)
    t = re.sub(r'\( +', '(', t)
    return t.strip()


def clean_title(text):
    """Filenames used as titles: also drop leading/trailing separators."""
    return clean_text(text).strip(' _-')


DATASHEET_NOISE = re.compile(
    r'(Release Date|Revised|Revision|Version|Rev\.?)\s*:?\s*[A-Za-z]{0,9},?\s*\d{0,4}|\bV\d+(\.\d+)+[A-Z]?\b|'
    r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s+\d{4}\b|'
    r'www\.\S+|\b[A-Z]{4,7}\d{1,4}[A-Z]?\b(?=\s*[–-])|\b[A-Z]{4}\d{2,4}[A-Z]?\b|'
    r'\b(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{4}\b|'
    r'Ordering number\s*:?\s*\S+|Product Preview|DATASHEET|Data Sheet|Preliminary', re.I)


def clean_description(text, max_len=300):
    """A short English description from datasheet title-page text, or '' if not enough English remains."""
    t = clean_text(text)
    t = re.sub(r'\bV\d+(\.\d+)+[A-Z]?\b', ' ', t)                 # 'V0.12P' before 'Version:' eats its 'V0'
    t = DATASHEET_NOISE.sub(' ', t)
    t = re.sub(r'\b(\S+)( \1\b)+', r'\1', t)                 # 'F71858AD F71858AD' -> once
    t = re.sub(r'(\s*[–:!-]\s*)+(?=\s|$)', ' ', t)               # dangling separators left behind
    t = re.sub(r'\s+', ' ', t).strip(' ,;:-–!')
    words = re.findall(r'\b[A-Za-z]{3,}\b', t)
    if len(words) < 3:
        return ''
    return t[:max_len].rsplit(' ', 1)[0] if len(t) > max_len else t


# component type from a factory BOM line ('P ' is the plant's marker, not part of the text)
BOM_TYPES = [
    ('capacitor', r'^(MLCC|CAP\b|CAP\.|CHIP CAP|SMD CAP|E/C|EC CAP|C\.(MYLAR|CE|EL|TA))|CAPACITOR|ELECTROLYTIC'),
    ('thermistor', r'^THERMISTOR|^NTC\b'), ('resistor', r'^(RES\b|RES\.|R\.ARRAY|CHIP RES|RESISTOR)'),
    ('inductor', r'^(INDUCTOR|CHOKE|COIL|COMMON CHOKE|COMMON MODE CHOKE)'), ('ferrite', r'^(FERRITE|BEAD)'),
    ('regulator', r'^(LIN\.? ?REG|SW\.? ?REG|REG\.|LDO\b|PWM\b|VREF|V\. ?REF)'),
    ('eeprom', r'^(EEPROM|FLASH)\b'), ('crystal', r'^(XTAL|CRYSTAL|OSC\b|OSCILLATOR)'),
    ('mosfet', r'^(N-|P-|NP-)?MOSFET'), ('transistor', r'^(TRASIS|TRANSISTOR|DIGITAL TR)'),
    ('diode', r'^(DIODE|SCHOTTKY|ZENER|RECTIFIER|BRIDGE)'), ('led', r'^LED\b'), ('fuse', r'^(POLYSWITCH|FUSE)'),
    ('opamp', r'^OP\.? ?AMP'), ('transformer', r'^(TRANSFORMER|LAN TRANS)'),
    ('socket', r'^(ZIF|SOCKET|PLCC SOCK|CPU SOCK)'),
    ('connector', r'^(WAFER|HEADER|CONN|D-SUB|MINI DIN|MINI-DIN|DIMM|DDR\d? DIMM|SO-?DIMM|SLOT|SATA|USB|RJ-?\d+|'
                  r'PHONE JACK|AUDIO JACK|RCA JACK|DC JACK|JACK|FPC|FFC|BTOB|IDE\b|FDD\b|PCI|AGP|POWER CON|ATX|'
                  r'[A-Z0-9 ]{0,12}\bCONN?\b)'),
    ('switch', r'^(SW\b(?!\.? ?REG)|SWITCH|TACT)'), ('speaker', r'^(BUZZER|SPEAKER)'), ('battery', r'^(BATT|BATTERY)'),
    ('other', r'^(HEATSINK|HEAT SINK|LABEL|SCREW|SPACER|BRACKET|SHIELD|JUMPER|MINI JUMPER|CABLE|ANCHOR|CLIP|PCB\b)'),
]


def bom_component_type(description):
    """Site component type for a factory BOM line, or None when the line doesn't say."""
    d = re.sub(r'^P\s+', '', (description or '').strip().upper())
    for kind, pattern in BOM_TYPES:
        if re.search(pattern, d):
            return kind
    return None
