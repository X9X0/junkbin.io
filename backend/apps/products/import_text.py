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


def clean_description(text, max_len=300, part_number=''):
    """A short English description from datasheet title-page text, or '' if no title can be read.
    Idempotent: cleaning a cleaned description changes nothing."""
    t = text or ''
    for _ in range(4):
        new = _clean_description_once(t, part_number)
        if new == t:
            break
        t = new
    return t[:max_len].rsplit(' ', 1)[0] if len(t) > max_len else t


def _clean_description_once(text, part_number):
    t = clean_text(text)
    t = re.sub(r'\bV\d+(\.\d+)+[A-Z]?\b', ' ', t)                 # 'V0.12P' before 'Version:' eats its 'V0'
    t = DATASHEET_NOISE.sub(' ', t)
    t = re.sub(r'\b(\S+)( \1\b)+', r'\1', t)                 # 'F71858AD F71858AD' -> once
    t = re.sub(r'(\s*[–:!-]\s*)+(?=\s|$)', ' ', t)               # dangling separators left behind
    t = re.sub(r'\s+', ' ', t).strip(' ,;:-–!')
    return datasheet_title(t, part_number)


# ---- datasheet title pages ----------------------------------------------------------
# A datasheet's first-page text runs the title together with banners, document
# numbers, dates, watermarks and the start of the Features / Description columns:
#   "19-1125;; 9/96 KIT ATION EVALU BLE AVAILA Single-Channel CardBus ... ____ General Description"
#   "® ISL6612 February 26, 2007 FN9153.8 Advanced Synchronous Rectified Buck Features MOSFET Drivers ..."
# datasheet_title() keeps the title. Text that is a scrambled watermark or numbers and
# labels gives '' - an empty description is better than a wrong one.
TITLE_JUNK = [
    r'^\s*a\s+(?=[A-Z0-9])',                                        # Analog Devices logo 'a'
    r'\b\d{2}-\d{4};;?\s*(Rev\s*\d+;?\s*)?\d{1,2}/\d{2}\b',          # Maxim '19-1125;; 9/96'
    r'\b(KIT|ATION|EVALU|EVALUATIO|EVALUATION|AVAILA|AVA|ILABLE|BLE|BL E|LUATIO|N KIT|EVA|NUAL|MA|ANUAL|U A T IO N|EVAL|'
    r'IN C LUDED|M A TION|INF O R|TION|EVALUA|INCLUDED|AVAILABLE|INFORMATION|U|M)\b(?=[^a-z]*\b(KIT|ATION|EVALU|AVAILA|BLE|'
    r'LUATIO|EVA|TION|ILABLE|INCLUDED)\b)',
    r'\b(EVALUATION|EVALUATIO|EVALU|EVA|LUATIO|ATION|KIT|AVAILABLE|AVAILA|ILABLE|AVA|BLE|BL E|INCLUDED|MANUAL|NUAL|ANUAL)\b',
    r'\bFN\d{4}(\.\d)?\b', r'\bFN \d{4}\b',
    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
    r'®|™|\bTM\b|(?<=[a-zA-Z])TM\b|\(R\)', r'Integrated Circuit Systems,? Inc\.?', r'\bNIKO-SEM\b', r'Global Mixed-mode Technology Inc\.?',
    r'Product Sample & Technical Tools & Support & Folder Buy Documents Software Community', r'http://\S*',
    r'Advance Information', r'\bNo\.\s*[A-Z0-9 ]{3,12}\b', r'Confidential', r'New Product', r'Vishay Siliconix',
    r'File Number \d+', r'\bIntegrated\b(?=.*\bCircuit\b)', r'(?<=\s)Circuit(?=\s)', r'\bSystems,? Inc\.?', r'—',
    r'PRODUCT DATA SHEET', r'Data ?Sheet', r'Preliminary', r'[A-Z]* ?USE ONLY ?/ ?DO NOT DISTRIBUTE',
    r'Track ID \S+', r'CONFIDENTIAL INFORMATION RESTRICTED TO [A-Z0-9 -]+? LICENSEES', r'\bPD \d{5}[A-Z]?\b', r'(?<=\s)l(?=\s)',
]
TITLE_STOP = re.compile(r'\b(General Description|GENERAL DESCRIPTION|Description|DESCRIPTION|Package Dimensions|PRODUCT SUMMARY|'
                  r'POWER MANAGEMENT|Check for Samples|PRODUCTION DATA|FUNCTIONAL BLOCK|Absolute Maximum|'
                  r'SEMICONDUCTOR TECHNICAL DATA|The [A-Z]{2,}[0-9]|Specification|VDS \(V\)|Copyright|DESCRIPTIO\b|'
                  r'Features|FEATURES|Table of Content|Semiconductor Corp|Tel\.|No\. \d|Current sensing is)|'
                  r'\dFEATURES|[•■]')
TITLE_FEATURES = re.compile(r'\b(Features|FEATURES|U FEATURES)\b')


def datasheet_title(text, pn=''):
    """A short title from datasheet title-page text, or '' when none can be read. Repeated until
    stable, so cleaning a cleaned title changes nothing."""
    t = text or ''
    for _ in range(4):
        new = _title_once(t, pn)
        if new == t:
            break
        t = new
    return t


def _stop(t):
    """Where the title ends: the first section label, or the first bullet after some words."""
    for m in TITLE_STOP.finditer(t):
        if m.group(0) in '•■' and len(re.findall(r'[A-Za-z]{3,}', t[:m.start()])) < 2:
            continue                                   # glyph codes before the title, not a list
        return m.start()
    return None


def _title_once(text, pn):
    t = re.sub(r'[\ue000-\uf8ff]+', ' ', text or '')                # private-use glyphs (logo fonts)
    t = re.sub(r'[\x00-\x1f]+', ' • ', t)                           # control characters: list bullets
    t = re.sub(r'\s+', ' ', t)
    m = re.match(r'\s*\d{2}-\d{4};;?', t)
    if m:                       # Maxim: doc number, date and a scrambled 'EVALUATION KIT AVAILABLE' stamp,
        rest = t[m.end():]      # all in capitals, before the title's first mixed-case word or rating
        start = re.search(r'(?<![A-Za-z])(\d+(\.\d+)?[A-Za-z]*,|[A-Z]?[a-z]{2,}|µP|Li\+)', rest)
        if start:
            t = rest[start.start():]
            t = re.sub(r'^[a-z]+\s', '', t) if not re.match(r'[A-Z0-9µ]', t) else t
    for pat in TITLE_JUNK:
        t = re.sub(pat, ' ', t)
    t = re.sub(r'_{3,}', ' ', t)
    m = TITLE_FEATURES.search(t)
    if m:
        head, tail = t[:m.start()], t[m.end():]
        cont = re.match(r'\s*((?:[A-Z][\w/&,.-]*|with|and|for|of|to|in)(?:\s+(?:[A-Z0-9][\w/&,.%-]*|with|and|for|of|to|in))*)', tail)
        stop = _stop(head)
        if stop is not None:
            head = head[:stop]
        elif cont and 1 <= len(cont.group(1).split()) <= 8 and not re.match(r'\s*(The|This|•|■|·)', tail):
            head = head + ' ' + cont.group(1)
        t = head
    else:
        stop = _stop(t)
        if stop is not None:
            t = t[:stop]
    stop = _stop(t)
    if stop is not None:
        t = t[:stop]
    if pn:                                                       # the title printed twice: keep the first
        hits = [m.start() for m in re.finditer(re.escape(pn), t, re.I)]
        if len(hits) >= 2 and len(re.findall(r'[A-Za-z]{3,}', t[:hits[1]].replace(pn, ''))) >= 2:
            t = t[:hits[1]]
    t = re.sub(r'\s+', ' ', t).strip(' ,;:-·•')
    t = re.sub(r'\s+(and|with|for|of|to|in)$', '', t)
    words = t.split()
    half = len(words) // 2
    if half >= 2 and words[:half] == words[half:2 * half]:      # 'X IC X IC' printed twice
        t = ' '.join(words[:half])
    if re.search(r'[╴∴□■♦✕]|�|Vol\.\d', t):
        return ''
    # a scrambled watermark ('D E D F O R NEW ... R E C O MMEND') or stripped CJK leaves loose letters:
    # keep the title before them, or nothing when they are inside it
    if re.search(r'RECOMMEND|MMEND|ESIGNS|\bGNS\b|\bDESIG\b', t):
        return ''
    loose = re.search(r'(?<![\w.&/-])(?<!\d )[B-HJ-Z](?![\w.&/,-])(?! &)(?! ?-?Channel)', t)
    if loose:
        t = t[:loose.start()].strip(' ,;:-·•(')
    t = re.sub(r'(\s+[^A-Za-z\s]+)+$', '', t)                   # trailing '.1 -05-08'
    t = re.sub(r'(\s*/?\s*[A-Z]{1,6}\d{3,}[A-Z0-9-]*\s*/?)+$', '', t) if len(t.split()) > 3 else t   # trailing sibling PNs
    # a leading list of part numbers ('SN5400, SN54LS00, ... SN74S00', '2SB1260 / 2SB1181 /'):
    # the part number is shown on its own anyway
    pn_token = (r'(?:[A-Za-z]{1,6}\d{2,}[A-Za-z0-9()+-]*|\d[A-Za-z]{1,3}\d{2,}[A-Za-z0-9()+-]*)'
                r'(?<!\d[mM][aA])(?<!\d[VWA])(?<![HhZz][Zz])')
    lead = re.match(rf'^(?:(?:{pn_token}|THRU|/)(?:[,\s]+|$))+(?=\S)', t)
    if lead and re.search(r'[A-Za-z]{3,}', t[lead.end():]):
        t = t[lead.end():]
    t = re.sub(r'^(?:[.,;:•·–—-]\S*\s+)+(?=\S)', '', t)               # leading '.1 ' or glyph bullets
    tokens = [w for w in t.split() if w.upper() != pn.upper()]
    if len(tokens) >= 5 and sum(bool(re.search(r'\d', w)) or not re.search(r'[A-Za-z]', w)
                                for w in tokens) / len(tokens) > 0.75:
        return ''                                                # labels and numbers, not a title
    english = [w for w in re.findall(r'[A-Za-z][A-Za-z-]{2,}', t) if not re.search(r'\d', w) and w.upper() != pn.upper()]
    if not english:
        return ''
    return t[:300]


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
