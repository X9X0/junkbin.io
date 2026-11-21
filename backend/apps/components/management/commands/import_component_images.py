"""
Photos or renderings for individual parts (ComponentImage), e.g. through-hole resistors drawn with their colour
bands. Imported unapproved into the component-image review batch.

    manage.py import_component_images DIR [--dry-run]

DIR/manifest.json: {"images": [{"component": {"manufacturer": "Generic", "part_number": "RES 470K 1/2W"},
                                "file": "images/res_470k.png", "md5": "...", "caption": "470 kΩ, 4-band colour code ...",
                                "image_type": "package", "source_url": "", "source_notes": "rendered from the part's value ..."}]}
A part is matched by manufacturer and part number (case-insensitive). An image this import already added with the
same md5 is skipped; a different, still unapproved one from this batch is replaced; an approved one or a person's
upload is left alone. Re-running changes nothing.
"""
import hashlib
import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.components.models import Component, ComponentImage

BATCH = 'component-image'


class DryRun(Exception):
    pass


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('dir')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        folder = Path(opts['dir'])
        manifest = folder / 'manifest.json'
        if not manifest.exists():
            raise CommandError(f'{manifest} missing')
        entries = json.loads(manifest.read_text(encoding='utf-8'))['images']
        n = {'added': 0, 'replaced': 0, 'unchanged': 0, 'kept (approved or a person\'s)': 0, 'part not found': 0, 'missing file': 0}
        try:
            with transaction.atomic():
                for e in entries:
                    path = folder / e['file']
                    if not path.exists():
                        n['missing file'] += 1
                        continue
                    k = e['component']
                    part = Component.objects.filter(manufacturer__iexact=k['manufacturer'], part_number__iexact=k['part_number']).first()
                    if part is None:
                        n['part not found'] += 1
                        continue
                    md5 = hashlib.md5(path.read_bytes()).hexdigest()
                    note = f"[{BATCH}] md5={md5} {e.get('source_notes', '')}".strip()[:500]
                    ours = ComponentImage.objects.filter(component=part, source_notes__startswith=f'[{BATCH}]')
                    if ours.filter(source_notes__contains=f'md5={md5}').exists():
                        n['unchanged'] += 1
                        continue
                    if part.images.filter(is_approved=True).exists() or part.images.exclude(source_notes__startswith=f'[{BATCH}]').exists():
                        n["kept (approved or a person's)"] += 1
                        continue
                    if ours.exists():
                        ours.delete()
                        n['replaced'] += 1
                    else:
                        n['added'] += 1
                    img = ComponentImage(component=part, image_type=e.get('image_type', 'package'), caption=e.get('caption', '')[:500],
                                         source_url=e.get('source_url', '')[:500], source_notes=note, is_approved=False)
                    with path.open('rb') as fh:
                        img.image.save(path.name, File(fh), save=False)
                    img.save()
                if opts['dry_run']:
                    raise DryRun
        except DryRun:
            pass
        self.stdout.write(('DRY RUN (rolled back) - ' if opts['dry_run'] else '') + ', '.join(f'{k} {v}' for k, v in n.items()))
