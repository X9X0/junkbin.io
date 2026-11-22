"""Chip package sizes in both systems. EIA names a chip in hundredths of an inch (0603 = 0.06 x 0.03 in);
IEC / JIS names it in tenths of a millimetre (1608 = 1.6 x 0.8 mm). The two overlap in spelling (the metric
0402 is the EIA 01005, the metric 0603 is the EIA 0201), so a package is stored as its EIA code and shown with
its metric twin beside it, and a search for either finds the part."""
import re

EIA_TO_METRIC = {'01005': '0402', '0201': '0603', '0402': '1005', '0603': '1608', '0805': '2012', '1008': '2520',
                 '1206': '3216', '1210': '3225', '1806': '4516', '1812': '4532', '2010': '5025', '2512': '6332'}
METRIC_TO_EIA = {m: e for e, m in EIA_TO_METRIC.items()}
# package labels that start with a chip code: '0603', '4R8P 0603', '7343 (D case)' is metric already
CHIP_CODE = re.compile(r'(?<![\dA-Z])(01005|0201|0402|0603|0805|1008|1206|1210|1806|1812|2010|2512)(?![\d])')


def metric_for(package_type):
    """The IEC/JIS metric code for a package stored by its EIA code ('0603' -> '1608', '4R8P 0603' -> '1608'
    for the elements); '' when the package is not a chip size."""
    m = CHIP_CODE.search(package_type or '')
    return EIA_TO_METRIC.get(m.group(1), '') if m else ''


def eia_for(code):
    """The EIA code a metric code names ('1608' -> '0603'); '' when it is no metric chip code."""
    return METRIC_TO_EIA.get((code or '').strip(), '')


def query_terms(value):
    """What a package search should match: the text itself and, for a metric-only chip code, its EIA twin.
    A code spelled the same in both systems (0402, 0603) is taken as the EIA size, the far more common meaning."""
    value = (value or '').strip()
    twin = eia_for(value)
    return [value, twin] if twin and value not in EIA_TO_METRIC else [value]
