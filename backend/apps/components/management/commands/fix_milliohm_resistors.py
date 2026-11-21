"""
Generic resistors whose sub-ohm value was read as megohms: a parts list wrote '470m' (milliohm) and the ohm parser
upper-cased it into 470 MΩ. Each placement's own note still carries the true value: the parts-list note opens with
the schematic's figure ('Output emitters (.47 2W). Read from ...'), a factory BOM line says 'RES 100m OHM' in mixed
case (the BOM parser already reads that lower-case m as milli). A placement is moved only when that figure equals
the part's figure read as milliohms (470M -> 0.47 Ω). Bare schematic labels ('10m 10m', '3m 2W') are left alone:
they do not say what the figure is. A part whose placements
all move is renamed in place ('RES 470M 2W' -> 'RES 0.47R 2W') or merged into the existing part of that name;
otherwise only the verified placements move to the sub-ohm part and the rest stay.

    manage.py fix_milliohm_resistors [--apply]

Without --apply, reports what would change. The part's unapproved rendering (the 470 MΩ picture) is deleted with
the empty part; a renamed part keeps nothing wrong except the picture, which the next rendering import replaces.
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.components.models import Component, ComponentImage, ProductComponent

MEG = re.compile(r'^RES (\d+(?:\.\d+)?)M(?=\s|$)')
# the true value in the placement's note: the parts-list note's opening parenthetical '(.47 2W)', '(0,1E)',
# '(0.5/2W)', or a factory BOM line 'RES 100m OHM'
PAREN = re.compile(r'^[^()]{0,80}\(\s*(0?[.,]\d+)(?![\d.,])')
BOM = re.compile(r'Factory BOM line: (?:P )?RES (\d+(?:\.\d+)?)m OHM')


def note_value(note):
    """The sub-ohm value the note itself states, or None."""
    m = BOM.search(note)
    if m:
        return float(m.group(1)) / 1000
    if 'Read from' in note:
        m = PAREN.search(note)
        if m:
            return float(m.group(1).replace(',', '.'))
    return None


def fmt(v):
    return f'{v:.6g}'


def sub_ohm_name(part_number, value):
    """'RES 470M 2W' -> 'RES 0.47R 2W'; a repeated token ('RES 500M 2W 2W') is dropped."""
    tokens = part_number.split()
    tokens[1] = fmt(value) + 'R'
    seen, out = set(), []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return ' '.join(out)


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='make the changes (default: report only)')

    def handle(self, *args, **opts):
        apply = opts['apply']
        n = {'parts seen': 0, 'placements moved': 0, 'placements kept': 0, 'duplicates dropped': 0, 'renamed': 0, 'merged': 0,
             'split': 0, 'parts deleted': 0, 'renderings deleted': 0}
        with transaction.atomic():
            for part in Component.objects.filter(manufacturer__iexact='Generic', component_type='resistor', part_number__regex=r'^RES \d+(\.\d+)?M( |$)').order_by('part_number'):
                m = MEG.match(part.part_number)
                if not m:
                    continue
                value = float(m.group(1)) / 1000                    # the figure that was read as megohms, as milliohms
                placements = list(ProductComponent.objects.filter(component=part).select_related('product'))
                moving = [pc for pc in placements if note_value(pc.notes or '') is not None and abs(note_value(pc.notes or '') - value) < value * 1e-3 + 1e-9]
                if not moving:
                    continue
                n['parts seen'] += 1
                staying = [pc for pc in placements if pc not in moving]
                name = sub_ohm_name(part.part_number, value)
                target = Component.objects.filter(manufacturer__iexact='Generic', part_number__iexact=name).exclude(pk=part.pk).first()
                if target is None and not staying:
                    action = 'rename'
                elif target is None:
                    action = 'split'
                elif not staying:
                    action = 'merge'
                else:
                    action = 'split'
                self.stdout.write(f'{part.part_number!r}: {len(moving)} of {len(placements)} placements say {fmt(value)} Ω -> {action} to {name!r}'
                                  + (f' (existing part, {target.usage_count} uses)' if target else ''))
                if not apply:
                    n['placements moved'] += len(moving)
                    n['placements kept'] += len(staying)
                    n[{'rename': 'renamed', 'merge': 'merged', 'split': 'split'}[action]] += 1
                    continue
                if action == 'rename':
                    part.part_number = name
                    part.description = part.description.replace(m.group(1) + 'M', fmt(value) + 'R') if part.description else f'Resistor {fmt(value)}R'
                    specs = dict(part.specifications or {})
                    specs['resistance_ohm'] = value
                    part.specifications = specs
                    part.save()
                    n['renamed'] += 1
                    n['placements moved'] += len(moving)
                    continue
                if target is None:                                  # split with no existing part: a new one for the true value
                    target = Component.objects.create(manufacturer=part.manufacturer, part_number=name, component_type='resistor',
                                                      package_type=part.package_type, description=f'Resistor {fmt(value)}R' + (', ' + ' '.join(name.split()[2:]) if len(name.split()) > 2 else ''),
                                                      specifications={**(part.specifications or {}), 'resistance_ohm': value}, created_by=part.created_by)
                n[{'merge': 'merged', 'split': 'split'}[action]] += 1
                for pc in moving:
                    dup = pc.reference_designator and ProductComponent.objects.filter(component=target, product=pc.product, reference_designator=pc.reference_designator).exists()
                    if dup:
                        pc.delete()
                        n['duplicates dropped'] += 1
                    else:
                        pc.component = target
                        pc.save()
                        n['placements moved'] += 1
                n['placements kept'] += len(staying)
                target.update_usage_count()
                part.update_usage_count()
                if not staying:
                    ours = ComponentImage.objects.filter(component=part, source_notes__startswith='[component-image]')
                    n['renderings deleted'] += ours.count()
                    ours.delete()
                    others = (part.images.exists() or part.datasheets.exists() or part.substitutes.exists() or part.substitute_for.exists()
                              or part.product_requests.exists() or part.recipe_components.exists())
                    if others:
                        self.stdout.write(f'  kept the empty part {part.part_number!r}: it still has images, datasheets or other links')
                    else:
                        part.delete()
                        n['parts deleted'] += 1
        self.stdout.write(('' if apply else 'DRY RUN - ') + ', '.join(f'{k} {v}' for k, v in n.items()))
