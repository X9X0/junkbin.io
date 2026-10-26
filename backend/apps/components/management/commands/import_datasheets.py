"""
Attach matched datasheet files to components.

    manage.py import_datasheets DIR [--dry-run] [--user NAME]

DIR holds matches.json and the files it names:

    {"version": 1, "source_tag": "norway-ds",
     "matches": [{"manufacturer", "part_number", "file": "files/x.pdf", "md5", "title", "source_notes"}]}

Components are found by manufacturer + part number (case-insensitive), so the
same export works on any copy of the site. A match with a "create" object
({"component_type", "description"}) creates the component when it is missing
(unverified, specifications.source = "datasheet"). A file whose md5 is already
attached to the component is skipped. Datasheets are created unapproved with
source type "mirror".
"""
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.components.models import Component, ComponentDatasheet
from apps.products.import_text import clean_description, clean_title


class Command(BaseCommand):
    help = 'Attach matched datasheet files to components (unapproved)'

    def add_arguments(self, parser):
        parser.add_argument('directory')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--user', help='Username recorded as uploader (default: first superuser)')

    def handle(self, *args, **options):
        folder = Path(options['directory'])
        manifest = folder / 'matches.json'
        if not manifest.is_file():
            raise CommandError(f'{manifest} not found')
        data = json.loads(manifest.read_text(encoding='utf-8'))
        if data.get('version') != 1:
            raise CommandError('unsupported matches.json version')
        tag = data.get('source_tag', 'import')

        User = get_user_model()
        user = (User.objects.filter(username=options['user']).first() if options['user']
                else User.objects.filter(is_superuser=True).order_by('date_joined').first())

        counts = {'components_created': 0, 'attached': 0, 'already_attached': 0, 'component_missing': 0}
        with transaction.atomic():
            for m in data['matches']:
                component = Component.objects.filter(manufacturer__iexact=m['manufacturer'],
                                                     part_number__iexact=m['part_number']).first()
                if not component and m.get('create'):
                    # same part number under another maker is a different component: never borrow it
                    counts['components_created'] += 1
                    if options['dry_run']:
                        counts['attached'] += 1
                        continue
                    component = Component.objects.create(
                        manufacturer=m['manufacturer'][:200], part_number=m['part_number'][:200],
                        component_type=m['create'].get('component_type') or 'ic',
                        description=clean_description(m['create'].get('description') or '', part_number=m['part_number']),
                        specifications={'source': 'datasheet'}, created_by=user)
                if not component:
                    counts['component_missing'] += 1
                    continue
                marker = f"md5:{m['md5']}"
                if component.datasheets.filter(source_notes__contains=marker).exists():
                    counts['already_attached'] += 1
                    continue
                counts['attached'] += 1
                if options['dry_run']:
                    continue
                path = folder / m['file']
                if not path.is_file():
                    raise CommandError(f'{path} missing')
                with path.open('rb') as fh:
                    ComponentDatasheet.objects.create(
                        component=component, file=File(fh, name=path.name), title=clean_title(m['title'])[:300],
                        source_type=ComponentDatasheet.SourceType.MIRROR,
                        source_notes=f"[{tag}] {m.get('source_notes', '')} {marker}",
                        uploaded_by=user, is_approved=False,
                    )
        prefix = 'DRY RUN - ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(prefix + ', '.join(f'{k.replace("_", " ")} {v}' for k, v in counts.items())))
