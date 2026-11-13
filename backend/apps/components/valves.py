"""
Valve (vacuum tube) substitution table.

No distributor the site asks stocks valves, so the Lookup button cannot answer for them.
This table says what else fits, the way the printed substitution guides and the makers'
data sheets do, and load_valve_substitutes writes it into Substitute rows.

SAME:  groups of designations for one and the same valve (American, European, military
       and industrial numbers). Every member replaces every other, grade 'same'.
NEAR:  (component, substitute, grade, note) - `substitute` can stand in for `component`;
       directional, because ratings go one way (a 7189 replaces an EL84, an EL84 replaces a
       7189 only at a lower plate voltage). 'near' is a drop-in with a difference worth
       knowing; 'check' fits the socket but needs the ratings, bias or wiring checked first.
MADE_TODAY_BY: brands producing the type now, keyed by the first name of its SAME group.
       Brands, not factories: Electro-Harmonix, Tung-Sol, Sovtek, the Mullard and Genalex
       reissues are New Sensor brands made in Saratov; TAD mostly relabels.

Sources: RCA Receiving Tube Manual, Mullard/Philips data sheets, the Sylvania and GE
substitution guides, and the makers' current data sheets (JJ, New Sensor, Shuguang).
Treat the notes as a repairer's starting point: the amp's plate voltage, bias range
and power transformer decide what is safe.
"""

SOURCE = 'valve substitution tables (RCA, Mullard, Sylvania/GE guides; current makers\' data sheets)'

SAME = [
    # small-signal double triodes
    ('12AX7', 'ECC83', '7025', '12AX7A', '12AX7WA', '12AX7WB', 'ECC83S', 'E83CC', 'CV4004', '6681'),
    ('12AT7', 'ECC81', '12AT7WA', '6201', 'CV4024', '6679', 'E81CC'),
    ('12AU7', 'ECC82', '12AU7A', '5814', '5814A', '6189', 'CV4003', '6680', 'E82CC'),
    ('12AY7', '6072', '6072A'),
    ('12DW7', '7247', 'ECC832'),
    ('12BH7', '12BH7A'),
    ('5751', '5751WA'),
    ('6SL7', '6SL7GT', '6SL7W', '6SL7WGT'),
    ('6SN7', '6SN7GT', '6SN7GTA', '6SN7GTB', '6SN7W', '6SN7WGT', 'CV1988'),
    ('6CG7', '6FQ7'),
    ('6C4', 'EC90', '6135', '6C4WA'),
    ('6J5', '6J5GT', 'L63'),
    ('6SC7', '6SC7GT'),
    ('6AV6', 'EBC91'),
    ('ECC808',),
    ('6EU7',),
    ('5691',),
    ('5692',),
    ('ECC35',),
    ('5693',),
    ('6J7', '6J7G', '6J7GT'),
    ('6AH6', '6AH6WA'),
    # small-signal pentodes and triode-pentodes
    ('6SJ7', '6SJ7GT', '6SJ7WGT'),
    ('6SQ7', '6SQ7GT'),
    ('6AU6', '6AU6A', 'EF94', '6136'),
    ('6BA6', 'EF93', '5749'),
    ('12AU6',),
    ('EF86', '6267', 'Z729', 'CV2901', 'EF806S'),
    ('5879',),
    ('7199',),
    ('6AN8', '6AN8A'),
    ('6BR8', '6BR8A'),
    ('6U8', '6U8A', 'ECF82'),
    ('6GH8', '6GH8A'),
    # output valves
    ('EL34', '6CA7', 'CV1741'),
    ('KT77',),
    ('E34L',),
    ('EL84', '6BQ5', 'N709', 'CV2975', '6P14P'),
    ('EL84M', '6P14P-EV'),
    ('E84L', '7320'),
    ('7189',),
    ('7189A',),
    ('6L6GC', '6L6WGC'),
    ('6L6', '6L6G', '6L6GA', '6L6GB'),
    ('5881', '6L6WGB', '5932'),
    ('7581', '7581A'),
    ('KT66', 'CV1075'),
    ('6V6', '6V6GT', '6V6GTA', '6V6GTY', '6V6G', '7408', 'CV511'),
    ('6AQ5', '6AQ5A', 'EL90', '6005', '6669'),
    ('6550', '6550A', '6550C', '6550WE'),
    ('KT88', 'CV5220'),
    ('KT90',),
    ('KT120',),
    ('7591', '7591A', '7591S'),
    ('7868',),
    ('7027', '7027A'),
    ('6973',),
    ('6CZ5',),
    ('ECL86', '6GW8'),
    ('6BM8', 'ECL82'),
    ('6DR7',),
    ('6U10',),
    ('50C5',),
    ('50L6', '50L6GT'),
    # rectifiers and regulators
    ('5AR4', 'GZ34', 'CV1377', '52KU', 'U77'),
    ('GZ37', 'CV378'),
    ('5Y3GT', '5Y3G', '5Y3', '6087', 'U50', 'CV1856'),
    ('5U4', '5U4G', '5U4GA', '5U4GB', 'U52', 'CV575'),
    ('5V4G', '5V4GA', '5V4', 'GZ32', 'CV717'),
    ('EZ81', '6CA4', 'U709'),
    ('EZ80', '6V4', 'U78'),
    ('6X4', 'EZ90', '6063', '6202', '6X4W'),
    ('6X5GT', '6X5', 'EZ35', '6X5WGT'),
    ('35W4',),
    ('35Z5GT', '35Z5'),
    ('0A2', '150C2', '0A2WA'),
    # indicators
    ('EM84', '6FG6'),
]

NEAR = [
    # (component, substitute, grade, note): `substitute` stands in for `component`
    ('12AX7', '5751', 'near', 'Same pinout and heater; gain 70 instead of 100, so the stage runs quieter and cleaner. Often chosen on purpose for the first stage.'),
    ('12AX7', '12AY7', 'near', 'Gain 44 instead of 100 (the first-stage valve of the tweed Fenders): plug-in, with far less drive.'),
    ('12AX7', '12AT7', 'check', 'Plug-in, gain 60, but it wants a lower plate load and draws more current: fine in reverb-driver and phase-inverter sockets, dull as a gain stage.'),
    ('12AX7', '12AU7', 'check', 'Plug-in but gain 17: a large drop in level, only where that is wanted.'),
    ('12AX7', '6EU7', 'check', 'Same characteristics, different pinout and a 6.3 V heater only: needs a socket adapter or rewiring.'),
    ('12AX7', 'ECC808', 'check', 'Same characteristics, different pinout: not plug-in.'),
    ('12AT7', '12AX7', 'check', 'Plug-in; higher gain, less current: as a phase inverter it changes balance and drive.'),
    ('12AT7', '12AU7', 'check', 'Plug-in; gain 17 instead of 60, drives harder.'),
    ('12AU7', '12AT7', 'check', 'Plug-in; gain 60 instead of 17 and more current: expect a much hotter stage.'),
    ('12AU7', '12BH7', 'check', 'Plug-in with more current and dissipation, a common reverb-driver upgrade; the heater draws 0.6 A instead of 0.3 A.'),
    ('12AY7', '12AX7', 'near', 'Plug-in; gain 100 instead of 44: louder and breaks up sooner (the usual tweed Deluxe hot-rod).'),
    ('12AY7', '5751', 'near', 'Plug-in; gain 70, between the two.'),
    ('6EU7', '12AX7', 'check', 'Electrically the same valve, but the pins differ: only with an adapter or a rewired socket.'),
    ('6SL7', '5691', 'near', 'Premium long-life 6SL7 (red base); rated for a lower plate voltage (250 V): check the supply.'),
    ('6SL7', 'ECC35', 'near', 'British equivalent with slightly different heater current and ratings; plug-in.'),
    ('6SL7', '6SN7', 'check', 'Same pinout; gain 20 instead of 70 and much more current: a different amplifier, not a swap.'),
    ('6SN7', '5692', 'near', 'Premium long-life 6SN7 rated for a lower plate voltage (275 V) and dissipation: check the supply.'),
    ('6SN7', '6SL7', 'check', 'Same pinout; gain 70 instead of 20 and far less current: not like for like.'),
    ('6SN7', '6CG7', 'check', 'The same valve in a 9-pin bottle: needs a socket change.'),
    ('6CG7', '6SN7', 'check', 'Electrically the same; octal base, socket change needed.'),
    ('6C4', '12AU7', 'check', 'One half of a 12AU7 is a 6C4; different base.'),
    ('6J5', '6SN7', 'check', 'Half a 6SN7; different pinout.'),
    ('6SC7', '6SL7', 'check', 'Dual triode of similar gain, but the 6SC7 shares one cathode and the pinout differs: rewiring needed.'),
    ('6SJ7', '5693', 'near', 'Premium ruggedised 6SJ7; plug-in.'),
    ('6SJ7', '6J7', 'check', 'Same characteristics; the 6J7 has a top-cap grid: rewiring needed.'),
    ('6AU6', '6BA6', 'check', 'The remote-cutoff version (EF93): plug-in, but it biases differently and gain and clipping change.'),
    ('6AU6', '6AH6', 'check', 'Plug-in; higher gain and current, more heater current.'),
    ('12AU6', '6AU6', 'check', 'The same valve with a 6.3 V heater: only if the heater supply is changed; a series heater string cannot take it.'),
    ('EF86', '6AU6', 'check', 'Different pinout, rewiring needed, and it is noisier.'),
    ('5879', 'EF86', 'check', 'Different pinout; rewired socket needed.'),
    ('5879', '6AU6', 'check', 'Different pinout; rewired socket needed.'),
    ('7199', '6U8', 'check', 'Triode-pentode of similar ratings with a different pinout: rewire the socket (adapters exist for the Dynaco ST-70).'),
    ('7199', '6GH8', 'check', 'Triode-pentode of similar ratings with a different pinout: rewire the socket.'),
    ('7199', '6AN8', 'check', 'Triode-pentode of similar ratings with a different pinout: rewire the socket.'),
    ('6AN8', '7199', 'check', 'Different pinout: rewire the socket.'),
    ('6AN8', '6U8', 'check', 'Different pinout: rewire the socket.'),
    ('6BR8', '6U8', 'check', 'Different pinout: rewire the socket.'),
    # output valves
    ('EL34', 'KT77', 'near', 'Plug-in beam tetrode with EL34 ratings; set the bias again after the swap.'),
    ('EL34', 'E34L', 'near', 'JJ variant wanting about 10 % more negative grid bias: rebias.'),
    ('EL34', '6L6GC', 'check', 'Fits the socket; different bias point, no suppressor on pin 1 (check what the socket does with pin 1), rebias and expect a different tone.'),
    ('EL34', 'KT66', 'check', 'Fits the socket; rebias, and check the clearance, it is taller.'),
    ('KT77', 'EL34', 'near', 'Plug-in; rebias.'),
    ('EL84', '7189', 'near', 'Higher-rated version (400 V plate): a direct upgrade.'),
    ('EL84', '7189A', 'near', 'Higher-rated version; pins 1 and 6 are tied internally, which matters only in amps that use those pins for something else.'),
    ('EL84', 'EL84M', 'near', 'Sovtek\'s ruggedised 6P14P-EV with higher dissipation; plug-in.'),
    ('EL84', 'E84L', 'near', 'Higher-rated EL84; plug-in.'),
    ('7189', 'EL84', 'check', 'Lower-rated: only where the plate voltage stays under 300 V (many 7189 amps run higher).'),
    ('7189', '7189A', 'near', 'Pins 1 and 6 tied internally; check an amp that uses them for anything else.'),
    ('6L6GC', '5881', 'check', 'Rated 23 W instead of 30 W: fine at tweed-era voltages, overstressed in an amp above about 450 V; rebias.'),
    ('6L6GC', 'KT66', 'near', 'Plug-in with the same ratings in a taller bottle; rebias.'),
    ('6L6GC', '7581', 'near', 'Higher-rated 6L6GC; plug-in.'),
    ('6L6GC', '6L6', 'check', 'Lower-rated (19 W): only at modest plate voltage.'),
    ('6L6GC', 'EL34', 'check', 'Fits; different bias and pin-1 wiring, and the heater draws 1.5 A instead of 0.9 A: check the power transformer.'),
    ('6L6GC', '7027', 'check', 'Different pinout (pins 1 and 6 tied to screen and plate): works only if the socket wiring suits.'),
    ('6L6GC', '6550', 'check', 'Heater 1.6 A and a different bias range: transformer and bias supply are usually too small.'),
    ('6L6', '6L6GC', 'near', 'Direct replacement with higher ratings.'),
    ('6L6', '5881', 'near', 'Direct replacement with slightly higher ratings.'),
    ('5881', '6L6GC', 'near', 'Higher-rated replacement; rebias.'),
    ('5881', '6L6', 'near', 'Same ratings, older construction.'),
    ('5881', 'KT66', 'near', 'Plug-in with higher ratings in a taller bottle; rebias.'),
    ('6V6', '6AQ5', 'check', 'Electrically the same valve on a 7-pin miniature base: socket change.'),
    ('6V6', '6L6GC', 'check', 'Fits, and some do it, but the heater draws 0.9 A instead of 0.45 A and the bias differs: check the transformer and rebias.'),
    ('6AQ5', '6V6', 'check', 'Electrically the same valve on an octal base: socket change.'),
    ('6550', 'KT88', 'near', 'Plug-in with higher ratings; rebias.'),
    ('6550', 'KT90', 'check', 'Fits; more heater current and a different bias range.'),
    ('KT88', '6550', 'near', 'Close ratings, different bias point; rebias.'),
    ('KT88', 'KT90', 'near', 'Higher-rated; plug-in; rebias.'),
    ('KT88', 'KT120', 'check', 'Heater 1.95 A instead of 1.6 A: check the power transformer; rebias.'),
    ('7591', '7868', 'check', 'The same valve on a Novar base: socket change.'),
    ('7591', '6L6GC', 'check', 'Different pinout and bias: conversion wiring needed.'),
    ('7868', '7591', 'check', 'The same valve on an octal base: socket change.'),
    ('7027', '6L6GC', 'check', 'Fits if the socket does not rely on pins 1 and 6 (the 7027A ties them to screen and plate): check the wiring, rebias.'),
    ('6973', '6CZ5', 'near', 'Same electrically, same pinout; plug-in.'),
    ('6973', 'EL84', 'check', '9-pin, but a different pinout: not plug-in.'),
    ('6CZ5', '6973', 'near', 'Same electrically, same pinout; plug-in.'),
    ('6BM8', 'ECL86', 'check', 'Different pinout and a higher-power pentode: not plug-in.'),
    ('ECL86', '6BM8', 'check', 'Different pinout and a smaller pentode: not plug-in.'),
    # rectifiers
    ('5AR4', '5U4', 'check', 'Directly heated: more voltage drop (lower B+), a 3 A heater instead of 1.9 A, and B+ arrives before the valves warm up: check the transformer.'),
    ('5AR4', '5V4G', 'check', 'Lower current rating (175 mA); fine in a small amp.'),
    ('5AR4', 'GZ37', 'near', 'Plug-in with close ratings.'),
    ('GZ37', '5AR4', 'near', 'Plug-in with close ratings.'),
    ('5Y3GT', '5V4G', 'check', 'Indirectly heated with less voltage drop: B+ rises some 20 to 30 V; same 2 A heater.'),
    ('5Y3GT', '5AR4', 'check', 'Much less drop: B+ rises 30 V or more and the amp feels stiffer; 1.9 A heater.'),
    ('5Y3GT', '5U4', 'check', 'Heater 3 A instead of 2 A: check the transformer; less drop, higher B+.'),
    ('5U4', '5AR4', 'check', 'Less voltage drop: higher B+ and a slow start; 1.9 A heater.'),
    ('5U4', '5Y3GT', 'check', 'Lower current rating (125 mA): only in a small amp.'),
    ('5V4G', '5AR4', 'near', 'Higher-rated with similar drop; plug-in.'),
    ('5V4G', '5Y3GT', 'check', 'More drop (lower B+) and a lower current rating.'),
    ('EZ80', 'EZ81', 'near', 'Higher-rated; plug-in.'),
    ('EZ81', 'EZ80', 'check', 'Lower current rating (90 mA): only in a small amp.'),
    ('6X4', '6X5GT', 'check', 'Electrically the same; octal base, socket change.'),
    ('6X5GT', '6X4', 'check', 'Electrically the same; 7-pin miniature base, socket change.'),
]

MADE_TODAY_BY = {
    '12AX7': ['JJ', 'Electro-Harmonix', 'Tung-Sol', 'Sovtek', 'Mullard (reissue)', 'Genalex Gold Lion', 'Shuguang', 'Psvane', 'TAD'],
    '12AT7': ['JJ', 'Electro-Harmonix', 'Tung-Sol', 'Mullard (reissue)', 'Genalex Gold Lion', 'Shuguang'],
    '12AU7': ['JJ', 'Electro-Harmonix', 'Tung-Sol', 'Mullard (reissue)', 'Genalex Gold Lion', 'Shuguang', 'Psvane'],
    '12AY7': ['JJ', 'Electro-Harmonix'],
    '12DW7': ['JJ', 'Electro-Harmonix'],
    '12BH7': ['JJ', 'Electro-Harmonix'],
    '5751': ['JJ', 'Electro-Harmonix', 'Tung-Sol', 'Sovtek'],
    '6SL7': ['Electro-Harmonix', 'Tung-Sol', 'Sovtek', 'Shuguang', 'Psvane'],
    '6SN7': ['Electro-Harmonix', 'Tung-Sol', 'Sovtek', 'Shuguang', 'Psvane'],
    '6CG7': ['Electro-Harmonix'],
    'EF86': ['JJ', 'Electro-Harmonix'],
    'EL34': ['JJ', 'Electro-Harmonix', 'Tung-Sol', 'Sovtek', 'Mullard (reissue)', 'Svetlana', 'Shuguang', 'Psvane', 'TAD'],
    'KT77': ['JJ', 'Genalex Gold Lion'],
    'E34L': ['JJ'],
    'EL84': ['JJ', 'Electro-Harmonix', 'Tung-Sol', 'Sovtek', 'Mullard (reissue)', 'Genalex Gold Lion', 'Shuguang', 'TAD'],
    'EL84M': ['Sovtek'],
    '6L6GC': ['JJ', 'Electro-Harmonix', 'Tung-Sol', 'Sovtek', 'Svetlana', 'Shuguang', 'Psvane', 'TAD'],
    '5881': ['Tung-Sol', 'Sovtek', 'TAD'],
    'KT66': ['JJ', 'Genalex Gold Lion', 'Shuguang', 'TAD'],
    '6V6': ['JJ', 'Electro-Harmonix', 'Tung-Sol', 'Sovtek', 'Shuguang', 'TAD'],
    '6550': ['Tung-Sol', 'Electro-Harmonix', 'Svetlana', 'Sovtek', 'Shuguang'],
    'KT88': ['JJ', 'Genalex Gold Lion', 'Electro-Harmonix', 'Tung-Sol', 'Svetlana', 'Shuguang', 'Psvane'],
    'KT90': ['Electro-Harmonix'],
    'KT120': ['Tung-Sol'],
    '7591': ['JJ', 'Electro-Harmonix', 'Tung-Sol'],
    '6973': ['Electro-Harmonix'],
    '5AR4': ['JJ', 'Sovtek', 'Mullard (reissue)', 'Genalex Gold Lion', 'Shuguang', 'TAD'],
    '5Y3GT': ['Sovtek', 'TAD'],
    '5U4': ['Sovtek', 'Electro-Harmonix', 'Shuguang', 'Psvane', 'TAD'],
    'EZ81': ['JJ', 'Electro-Harmonix'],
}


def groups():
    """{designation: head} for every name in SAME (head = first name of its group)."""
    return {name: group[0] for group in SAME for name in group}


def check():
    """Problems in the table: a name in two groups, a NEAR endpoint or MADE_TODAY_BY key no
    group names, a bad grade. [] when the table is consistent."""
    problems, seen = [], {}
    for group in SAME:
        for name in group:
            if name in seen and seen[name] is not group:
                problems.append(f'{name} is in two SAME groups')
            seen[name] = group
    for component, substitute, grade, note in NEAR:
        for name in (component, substitute):
            if name not in seen:
                problems.append(f'NEAR names {name}, which no SAME group has')
        if grade not in ('near', 'check'):
            problems.append(f'{component} -> {substitute}: grade {grade!r}')
        if component == substitute or not note.strip():
            problems.append(f'{component} -> {substitute}: empty or self-referencing')
    for head in MADE_TODAY_BY:
        if seen.get(head, (None,))[0] != head:
            problems.append(f'MADE_TODAY_BY key {head} is not the head of a SAME group')
    return problems
