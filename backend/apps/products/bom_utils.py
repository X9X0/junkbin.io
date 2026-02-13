"""
BOM (Bill of Materials) import utilities.

Provides CSV column auto-detection, row validation, and component type
classification for the BOM import feature.
"""
import re
from django.conf import settings

# Valid component types from settings
VALID_COMPONENT_TYPES = {ct[0] for ct in settings.COMPONENT_TYPES}

# ──────────────────────────────────────────────────────────────────────
# Column alias mapping: common CSV header variations → canonical field
# ──────────────────────────────────────────────────────────────────────
AUTO_COLUMN_ALIASES = {
    # Part identification
    'part number': 'part_number',
    'part_number': 'part_number',
    'part no': 'part_number',
    'part no.': 'part_number',
    'p/n': 'part_number',
    'mpn': 'part_number',
    'mfr part no': 'part_number',
    'mfr part no.': 'part_number',
    'mfr part number': 'part_number',
    'manufacturer part number': 'part_number',
    'mfg part': 'part_number',
    'partnumber': 'part_number',
    'component': 'part_number',

    # Manufacturer
    'manufacturer': 'manufacturer',
    'mfr': 'manufacturer',
    'mfg': 'manufacturer',
    'mfr name': 'manufacturer',
    'vendor': 'manufacturer',
    'brand': 'manufacturer',
    'make': 'manufacturer',

    # Reference designator
    'reference designator': 'reference_designator',
    'reference_designator': 'reference_designator',
    'ref des': 'reference_designator',
    'refdes': 'reference_designator',
    'ref': 'reference_designator',
    'designator': 'reference_designator',
    'reference': 'reference_designator',
    'refs': 'reference_designator',

    # Quantity
    'quantity': 'quantity',
    'qty': 'quantity',
    'count': 'quantity',
    'qty.': 'quantity',
    'amount': 'quantity',

    # Component type
    'type': 'component_type',
    'component type': 'component_type',
    'component_type': 'component_type',
    'category': 'component_type',
    'part type': 'component_type',

    # Package
    'package': 'package_type',
    'package type': 'package_type',
    'package_type': 'package_type',
    'footprint': 'package_type',
    'case': 'package_type',
    'case/package': 'package_type',

    # Description
    'description': 'description',
    'desc': 'description',
    'desc.': 'description',
    'part description': 'description',
    'comment': 'description',

    # Value (electrical)
    'value': 'value',
    'nominal value': 'value',
    'nominal': 'value',

    # Location
    'location': 'location_description',
    'board location': 'location_description',
    'location_description': 'location_description',
    'pcb': 'location_description',
    'board': 'location_description',

    # Notes
    'notes': 'notes',
    'comments': 'notes',
    'remark': 'notes',
    'remarks': 'notes',
}

# Fields users can map to
BOM_FIELDS = [
    ('part_number', 'Part Number'),
    ('manufacturer', 'Manufacturer'),
    ('reference_designator', 'Reference Designator'),
    ('quantity', 'Quantity'),
    ('component_type', 'Component Type'),
    ('package_type', 'Package Type'),
    ('description', 'Description'),
    ('value', 'Value'),
    ('location_description', 'Location'),
    ('notes', 'Notes'),
]


def detect_column_mapping(headers):
    """Auto-detect column mapping from CSV headers.

    Returns a dict of {csv_header: canonical_field_name} for recognized headers.
    """
    mapping = {}
    used_fields = set()

    for header in headers:
        normalized = header.strip().lower()
        if normalized in AUTO_COLUMN_ALIASES:
            field = AUTO_COLUMN_ALIASES[normalized]
            if field not in used_fields:
                mapping[header] = field
                used_fields.add(field)

    return mapping


def validate_row(row, mapping):
    """Validate a single mapped BOM row.

    Args:
        row: dict of {csv_header: value} (raw CSV row)
        mapping: dict of {csv_header: canonical_field} (column mapping)

    Returns:
        (cleaned_data, errors) where cleaned_data is a dict with canonical keys
        and errors is a list of error strings.
    """
    errors = []
    cleaned = {}

    # Reverse mapping: canonical_field → csv_header
    field_to_header = {v: k for k, v in mapping.items()}

    # Extract mapped values
    for field, header in field_to_header.items():
        val = row.get(header, '').strip()
        if val:
            cleaned[field] = val

    # Required fields
    if not cleaned.get('part_number'):
        errors.append('Part Number is required')
    if not cleaned.get('manufacturer'):
        errors.append('Manufacturer is required')

    # Validate and clean quantity
    if 'quantity' in cleaned:
        try:
            qty = int(cleaned['quantity'])
            if qty < 1:
                errors.append(f'Invalid quantity: {cleaned["quantity"]}')
            else:
                cleaned['quantity'] = qty
        except (ValueError, TypeError):
            errors.append(f'Invalid quantity: {cleaned["quantity"]}')
            cleaned['quantity'] = 1
    else:
        cleaned['quantity'] = 1

    # Validate component_type against allowed choices
    if 'component_type' in cleaned:
        ct = cleaned['component_type'].lower().strip()
        if ct in VALID_COMPONENT_TYPES:
            cleaned['component_type'] = ct
        else:
            # Try to match display name
            type_map = {v.lower(): k for k, v in settings.COMPONENT_TYPES}
            if ct in type_map:
                cleaned['component_type'] = type_map[ct]
            else:
                # Will be auto-classified later
                del cleaned['component_type']

    return cleaned, errors


def classify_component_type(description):
    """Classify component type from an English description.

    Returns one of the COMPONENT_TYPES choices or 'other'.
    """
    if not description:
        return 'other'
    dl = description.lower()

    # Capacitors
    if any(x in dl for x in ['capacitor', 'mlcc', 'cap ', 'cap,', 'electrolytic', 'tantalum']):
        return 'capacitor'

    # Resistors
    if any(x in dl for x in ['resistor', 'res ', 'res,', 'thick film', 'thin film', 'current sense']):
        return 'resistor'
    if 'resistor network' in dl or 'res array' in dl or 'res network' in dl:
        return 'resistor'

    # Inductors
    if any(x in dl for x in ['inductor', 'ind ', 'ind,', 'choke', 'coil']):
        return 'inductor'
    if 'ferrite' in dl or 'bead' in dl:
        return 'ferrite'

    # LEDs
    if 'led' in dl and 'driver' not in dl:
        return 'led'

    # Diodes
    if any(x in dl for x in ['esd', 'tvs', 'zener', 'schottky']):
        return 'diode'
    if 'diode' in dl:
        return 'diode'

    # MOSFETs
    if any(x in dl for x in ['mosfet', 'n-channel', 'p-channel', 'n-ch', 'p-ch']):
        return 'mosfet'

    # Transistors
    if any(x in dl for x in ['transistor', 'bjt', 'npn', 'pnp']):
        return 'transistor'

    # Voltage regulators
    if any(x in dl for x in ['ldo', 'voltage regulator', 'linear regulator', 'vreg']):
        return 'regulator'
    if any(x in dl for x in ['switching regulator', 'dc-dc', 'dc/dc', 'buck', 'boost converter']):
        return 'regulator'

    # Microcontrollers
    if any(x in dl for x in ['microcontroller', 'mcu', 'cortex', 'arm processor']):
        return 'mcu'

    # Connectors
    if any(x in dl for x in ['connector', 'header', 'socket', 'jack', 'receptacle', 'plug']):
        return 'connector'
    if any(x in dl for x in ['ffc', 'fpc', 'usb', 'hdmi']):
        if 'ic' not in dl and 'controller' not in dl:
            return 'connector'

    # Crystals / Oscillators
    if any(x in dl for x in ['crystal', 'oscillator', 'xtal', 'resonator']):
        return 'crystal'

    # Fuses
    if 'fuse' in dl:
        return 'fuse'

    # Antennas
    if 'antenna' in dl:
        return 'antenna'

    # Sensors
    if any(x in dl for x in ['sensor', 'accelerometer', 'gyroscope', 'thermometer', 'imu']):
        return 'sensor'
    if 'thermistor' in dl or 'ntc' in dl or 'ptc' in dl:
        return 'thermistor'

    # RF
    if any(x in dl for x in ['transceiver', 'rf ', 'rf,', 'radio', 'bluetooth', 'wifi', 'wireless']):
        return 'rf_module'
    if 'balun' in dl or 'saw filter' in dl:
        return 'balun'

    # Op-Amps
    if any(x in dl for x in ['op-amp', 'op amp', 'opamp', 'operational amplifier']):
        return 'opamp'

    # Transformers
    if 'transformer' in dl:
        return 'transformer'

    # Displays
    if any(x in dl for x in ['display', 'lcd', 'oled', 'screen']):
        return 'display'

    # Speakers / Buzzers
    if any(x in dl for x in ['speaker', 'buzzer', 'piezo']):
        return 'speaker'

    # Switches / Relays
    if 'switch' in dl or 'button' in dl:
        return 'switch'
    if 'relay' in dl:
        return 'relay'

    # Battery
    if any(x in dl for x in ['battery', 'cell', 'charger']):
        return 'battery'

    # Generic IC (catch-all for active components)
    if any(x in dl for x in ['ic', 'integrated circuit', 'driver', 'buffer',
                              'amplifier', 'converter', 'controller', 'processor',
                              'memory', 'flash', 'eeprom', 'fpga', 'cpld', 'asic']):
        return 'ic'

    return 'other'


def extract_package(description):
    """Extract package type from description text."""
    if not description:
        return ''
    # Standard metric/imperial chip sizes
    for pkg in ['2512', '2010', '1812', '1210', '1206', '0805', '0603', '0402', '0201']:
        if pkg in description:
            return pkg
    # Named packages
    # Order matters: more specific prefixes first (LQFP before QFP, WQFN before QFN, etc.)
    patterns = [
        (r'(\d+)-?DSBGA', lambda m: f'DSBGA-{m.group(1)}'),
        (r'(\d+)-?WQFN', lambda m: f'WQFN-{m.group(1)}'),
        (r'TQFP-?(\d+)', lambda m: f'TQFP-{m.group(1)}'),
        (r'LQFP-?(\d+)', lambda m: f'LQFP-{m.group(1)}'),
        (r'QFN-?(\d+)', lambda m: f'QFN-{m.group(1)}'),
        (r'QFP-?(\d+)', lambda m: f'QFP-{m.group(1)}'),
        (r'BGA-?(\d+)', lambda m: f'BGA-{m.group(1)}'),
        (r'TSSOP-?(\d+)', lambda m: f'TSSOP-{m.group(1)}'),
        (r'SSOP-?(\d+)', lambda m: f'SSOP-{m.group(1)}'),
        (r'MSOP-?(\d+)', lambda m: f'MSOP-{m.group(1)}'),
        (r'SOIC-?(\d+)', lambda m: f'SOIC-{m.group(1)}'),
        (r'SOP-?(\d+)', lambda m: f'SOP-{m.group(1)}'),
        (r'DIP-?(\d+)', lambda m: f'DIP-{m.group(1)}'),
    ]
    for pattern, formatter in patterns:
        m = re.search(pattern, description, re.IGNORECASE)
        if m:
            return formatter(m)
    # Simple named packages
    for pkg in ['SOT-323', 'SOT-23', 'SOT-223', 'SOT-89', 'SC-70', 'TO-220', 'TO-92', 'TO-252', 'DO-214']:
        if pkg.lower() in description.lower():
            return pkg
    return ''


def extract_value_from_text(value_str, component_type=''):
    """Parse a value string (e.g. '100nF', '4.7kOhm') into specifications dict.

    This is used when the CSV has an explicit 'Value' column.
    """
    if not value_str:
        return {}
    specs = {}
    vl = value_str.strip().lower()
    ct = component_type.lower() if component_type else ''

    # Capacitance
    m = re.search(r'(\d+\.?\d*)\s*(uf|µf|pf|nf)', vl)
    if m:
        val = float(m.group(1))
        unit = m.group(2).replace('µ', 'u')
        if unit == 'uf':
            specs['capacitance_uf'] = val
        elif unit == 'nf':
            specs['capacitance_nf'] = val
        elif unit == 'pf':
            specs['capacitance_pf'] = val
        return specs

    # Resistance
    m = re.search(r'(\d+\.?\d*)\s*k\s*(?:ohm|Ω)', vl)
    if m:
        specs['resistance_ohm'] = float(m.group(1)) * 1000
        return specs
    m = re.search(r'(\d+\.?\d*)\s*m\s*(?:ohm|Ω)', vl)
    if m:
        specs['resistance_ohm'] = float(m.group(1)) / 1000
        return specs
    m = re.search(r'(\d+\.?\d*)\s*(?:ohm|Ω)', vl)
    if m:
        specs['resistance_ohm'] = float(m.group(1))
        return specs
    # EIA notation: 4K7 = 4.7kΩ
    m = re.search(r'\b(\d+)[kK](\d)\b', value_str)
    if m:
        specs['resistance_ohm'] = (int(m.group(1)) + int(m.group(2)) / 10) * 1000
        return specs

    # Inductance
    m = re.search(r'(\d+\.?\d*)\s*(uh|µh|nh|mh)', vl)
    if m:
        val = float(m.group(1))
        unit = m.group(2).replace('µ', 'u')
        if unit == 'uh':
            specs['inductance_uh'] = val
        elif unit == 'nh':
            specs['inductance_nh'] = val
        elif unit == 'mh':
            specs['inductance_uh'] = val * 1000
        return specs

    # Frequency
    m = re.search(r'(\d+\.?\d*)\s*(mhz|khz|ghz)', vl)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
        if 'ghz' in unit:
            specs['frequency_mhz'] = val * 1000
        elif 'khz' in unit:
            specs['frequency_mhz'] = val / 1000
        else:
            specs['frequency_mhz'] = val
        return specs

    # Voltage
    m = re.search(r'(\d+\.?\d*)\s*v\b', vl)
    if m and ct in ('diode', 'mosfet', 'transistor', 'regulator', 'fuse', ''):
        specs['voltage_v'] = float(m.group(1))
        return specs

    # Current
    m = re.search(r'(\d+\.?\d*)\s*a\b', vl)
    if m and ct in ('fuse', 'regulator', ''):
        specs['current_a'] = float(m.group(1))
        return specs

    return specs
