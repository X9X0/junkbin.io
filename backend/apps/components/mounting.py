"""Where a BOM line names no package, the board it came from still says how the part is mounted. A computer
mainboard or graphics card from a factory schematic BOM (2000 on) carries chips: its resistors, inductors,
semiconductors and small ceramics are surface-mount, while its electrolytics and crystals may be leaded on a
desktop board, so those are left alone. A guitar amplifier or pedal schematic (1950s-90s) carries leaded parts:
its resistors and diodes are axial; its capacitors, transistors and ICs come in too many leaded forms to name.
The label is a mounting-only package ('SMD', 'Axial': spec_parse.MOUNT_ONLY), which a sized package from a parts
list still overrides."""
SMD_TYPES = frozenset({'resistor', 'inductor', 'ferrite', 'thermistor', 'fuse', 'diode', 'transistor', 'mosfet',
                       'ic', 'regulator', 'opamp', 'eeprom', 'mcu', 'sensor', 'switch', 'led'})
CERAMIC_MAX_PF = 4.7e6                                    # below 4.7 uF a mainboard capacitor is a ceramic chip
AXIAL_TYPES = frozenset({'resistor', 'diode'})


def mount_default(import_source, component_type, specifications=None):
    """The mounting-only package a part placed by this import source gets when its line names none: 'SMD',
    'Axial' or '' (the source does not say)."""
    family = (import_source or '').split(':', 1)[0]
    if family == 'schematic-bom':
        if component_type in SMD_TYPES:
            return 'SMD'
        pf = (specifications or {}).get('capacitance_pf')
        if component_type == 'capacitor' and pf and pf < CERAMIC_MAX_PF:
            return 'SMD'
    elif family == 'schematicheaven' and component_type in AXIAL_TYPES:
        return 'Axial'
    return ''
