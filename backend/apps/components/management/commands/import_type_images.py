"""
Default photos per component type and package (ComponentTypeImage): the fallback a part without a photo of its
own shows. Import a folder of licensed stock photos with a manifest; they wait, unapproved, in the type-image
review batch (first in the moderation list) until a moderator accepts them.

    manage.py import_type_images DIR [--dry-run] [--replace-approved]

DIR/manifest.json: {"images": [{"component_type": "resistor", "package_type": "0603" | "",
                                "file": "images/resistor_0603.png", "md5": "...",
                                "source_url": "https://commons.wikimedia.org/wiki/File:...",
                                "source_notes": "CC BY-SA 4.0, photo by ... (Wikimedia Commons), background removed"}]}
One row per (type, package): a new pair is created unapproved; an unapproved row is replaced by the manifest's
photo; an approved row is left alone unless --replace-approved (then it goes back to unapproved). Re-running with
the same files changes nothing. The source note is prefixed "[type-image]" so the review batch finds the row.
"""
import hashlib
import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.components.models import ComponentTypeImage

BATCH = 'type-image'


class DryRun(Exception):
    pass


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('dir')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--replace-approved', action='store_true')

    def handle(self, *args, **opts):
        folder = Path(opts['dir'])
        manifest = folder / 'manifest.json'
        if not manifest.exists():
            raise CommandError(f'{manifest} missing')
        entries = json.loads(manifest.read_text(encoding='utf-8'))['images']
        n = {'created': 0, 'replaced': 0, 'unchanged': 0, 'kept approved': 0, 'missing file': 0}
        try:
            with transaction.atomic():
                for e in entries:
                    path = folder / e['file']
                    if not path.exists():
                        n['missing file'] += 1
                        continue
                    md5 = hashlib.md5(path.read_bytes()).hexdigest()
                    note = f"[{BATCH}] md5={md5} {e.get('source_notes', '')}".strip()
                    row = ComponentTypeImage.objects.filter(component_type=e['component_type'],
                                                            package_type=e.get('package_type', '')).first()
                    if row and f'md5={md5}' in (row.source_notes or ''):
                        n['unchanged'] += 1
                        continue
                    if row and row.is_approved and not opts['replace_approved']:
                        n['kept approved'] += 1
                        continue
                    if row is None:
                        row = ComponentTypeImage(component_type=e['component_type'], package_type=e.get('package_type', ''))
                        n['created'] += 1
                    else:
                        n['replaced'] += 1
                    row.is_approved = False
                    row.source_url = e.get('source_url', '')[:500]
                    row.source_notes = note[:500]
                    with path.open('rb') as fh:
                        row.image.save(path.name, File(fh), save=False)
                    row.save()
                if opts['dry_run']:
                    raise DryRun
        except DryRun:
            pass
        self.stdout.write(('DRY RUN (rolled back) - ' if opts['dry_run'] else '')
                          + ', '.join(f'{k} {v}' for k, v in n.items()))
