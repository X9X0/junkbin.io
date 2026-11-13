"""
Write the valve substitution table (apps.components.valves) into Substitute rows.

    python manage.py load_valve_substitutes --dry-run
    python manage.py load_valve_substitutes

Every designation the table names gets a Generic vacuum_tube component if the catalogue
has none (so a search for "7025" or "ECC83" lands on a page that says what it is). Names
in one SAME group become 'same' substitutes of each other in both directions and
cross-references; NEAR rows are written as given, one direction each. The brands making
the type today go into each member's specifications as made_today_by. Re-running
updates grades and notes in place and never deletes a row someone added by hand.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.components import valves
from apps.components.models import Component, Substitute


def valve(name, head, created):
    """The Generic vacuum_tube component for a designation, created when missing. A
    designation that already exists under a maker's name (Fender's relabelled 12AX7) is
    left alone; the Generic one is what the table links."""
    component, made = Component.objects.get_or_create(
        manufacturer='Generic', part_number=name,
        defaults={'component_type': 'vacuum_tube',
                  'description': f'Valve, {name}' if name == head else f'Valve, {name}: the same valve as {head}',
                  'specifications': {'same_as': head} if name != head else {}})
    if made:
        created.append(name)
    elif component.component_type != 'vacuum_tube':
        component.component_type = 'vacuum_tube'
        component.save(update_fields=['component_type'])
    return component


class Command(BaseCommand):
    help = 'Load the valve substitution table into Substitute rows'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='report what would change; write nothing')

    def handle(self, *args, **options):
        problems = valves.check()
        if problems:
            raise CommandError('the table is inconsistent:\n  ' + '\n  '.join(problems))
        dry = options['dry_run']
        created, written, updated = [], 0, 0
        heads = valves.groups()
        with transaction.atomic():
            parts = {name: valve(name, head, created) for name, head in heads.items()}

            def put(a, b, grade, notes):
                nonlocal written, updated
                row, made = Substitute.objects.update_or_create(
                    component=parts[a], substitute=parts[b],
                    defaults={'grade': grade, 'notes': notes, 'source': valves.SOURCE})
                written += made
                updated += not made

            for group in valves.SAME:
                for a in group:
                    for b in group:
                        if a != b:
                            put(a, b, 'same', '')
                            parts[a].cross_references.add(parts[b])
            for component, substitute, grade, note in valves.NEAR:
                put(component, substitute, grade, note)

            stamped = 0
            for head, brands in valves.MADE_TODAY_BY.items():
                for name, h in heads.items():
                    if h == head and (parts[name].specifications or {}).get('made_today_by') != brands:
                        parts[name].specifications = {**(parts[name].specifications or {}), 'made_today_by': brands}
                        parts[name].save(update_fields=['specifications'])
                        stamped += 1

            self.stdout.write(f'{"DRY RUN (rolled back) - " if dry else ""}valves {len(parts)} ({len(created)} created: '
                              f'{", ".join(created) or "none"}), substitutes written {written}, updated {updated}, '
                              f'made_today_by stamped {stamped}')
            if dry:
                transaction.set_rollback(True)
