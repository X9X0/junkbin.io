"""
Attach product photos found online (by image search) to existing products.

    manage.py import_product_images DIR [--dry-run] [--user NAME]

DIR holds manifest.json and the image files it names:

    {
      "batch": "image-search",                       # review batch (import_review.BATCHES)
      "images": [{
          "product": {"import_source": "norway-fw:DELL_LATITUDE_D820",   # preferred: same on every server
                      "manufacturer": "Dell", "model_number": "Latitude D820", "revision": ""},
          "file": "images/Dell_Latitude_D820.png",   # relative to DIR
          "md5": "...",
          "source_url": "https://...",               # page the photo was found on
          "image_url": "https://...",                # the photo itself
          "site": "notebookcheck.net", "title": "Dell Latitude D820",
          "match": "exact" | "family",               # family: the photo is of the series ("L500" for L500-21R)
          "series": "L500"
      }]
    }

Each image is added unapproved, tagged "[<batch>] md5=<md5>" in source_notes, with the page it
came from in source_url (so a takedown request can be traced to its image). It becomes the
product's preview only when the product has none. Re-running is safe: an image this import
already added with the same md5 is skipped; a different, still unapproved one from this batch is
replaced; anything a person uploaded or approved is left alone.
"""
import hashlib
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.products.import_review import BATCHES
from apps.products.models import Product, ProductImage


class DryRun(Exception):
    pass


def find_product(ref):
    if ref.get('import_source'):
        found = list(Product.objects.filter(import_source=ref['import_source'])[:2])
        if len(found) == 1:
            return found[0]
    qs = Product.objects.filter(manufacturer=ref.get('manufacturer', ''), model_number=ref.get('model_number', ''))
    if 'revision' in ref:
        qs = qs.filter(revision=ref['revision'] or '')
    found = list(qs[:2])
    return found[0] if len(found) == 1 else None


def caption(product, item):
    if item.get('match') == 'family' and item.get('series'):
        return f'{product.manufacturer} {item["series"]} series'
    return f'{product.manufacturer} {product.model_number}'


class Command(BaseCommand):
    help = 'Attach image-search product photos from a manifest (unapproved, review batch)'

    def add_arguments(self, parser):
        parser.add_argument('dir')
        parser.add_argument('--dry-run', action='store_true', help='Report, then roll back')
        parser.add_argument('--user', help='Username recorded as uploader (default: first superuser)')

    def handle(self, *args, **opts):
        root = Path(opts['dir'])
        try:
            manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise CommandError(f'cannot read {root / "manifest.json"}: {exc}')
        batch = manifest.get('batch', 'image-search')
        if BATCHES.get(batch, {}).get('item_type') != 'image':
            raise CommandError(f'{batch!r} is not an image review batch')
        User = get_user_model()
        user = (User.objects.get(username=opts['user']) if opts['user']
                else User.objects.filter(is_superuser=True).order_by('pk').first())
        counts = {'added': 0, 'replaced': 0, 'unchanged': 0, 'no product': 0, 'missing file': 0}
        try:
            with transaction.atomic():
                for item in manifest.get('images', []):
                    counts[self.import_one(root, batch, item, user)] += 1
                if opts['dry_run']:
                    raise DryRun
        except DryRun:
            self.stdout.write('dry run, rolled back')
        self.stdout.write(', '.join(f'{k} {v}' for k, v in counts.items()))

    def import_one(self, root, batch, item, user):
        product = find_product(item.get('product', {}))
        if not product:
            return 'no product'
        path = root / item['file']
        if not path.is_file():
            return 'missing file'
        md5 = item.get('md5') or hashlib.md5(path.read_bytes()).hexdigest()
        tag = f'[{batch}] md5={md5}'
        ours = product.images.filter(source_notes__startswith=f'[{batch}]')
        if ours.filter(source_notes__startswith=tag).exists() or ours.filter(is_approved=True).exists():
            return 'unchanged'                         # same photo, or an approved one from an earlier run
        result = 'added'
        for old in ours:                               # an earlier, still unapproved pick
            old.image.delete(save=False)
            old.delete()
            result = 'replaced'
        notes = ' '.join(x for x in (
            tag,
            f'Found on {item["site"]}' if item.get('site') else '',
            f'("{item["title"][:200]}")' if item.get('title') else '',
            f'image {item["image_url"]}' if item.get('image_url') else '',
            'Photo of the series, not this exact model.' if item.get('match') == 'family' else '',
        ) if x)
        image = ProductImage(
            product=product, image_type=ProductImage.ImageType.OVERVIEW, caption=caption(product, item)[:500],
            is_primary=not product.images.filter(is_primary=True).exists(), uploaded_by=user, is_approved=False,
            source_url=(item.get('source_url') or '')[:1000], source_notes=notes,
            background_removed=True, has_transparency=True,
        )
        with path.open('rb') as fh:
            image.image.save(path.name, File(fh), save=False)
        image.save()
        return result
