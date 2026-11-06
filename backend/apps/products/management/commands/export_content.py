"""
Export the bulk-imported content of this site, as it stands after review, for
load_content on another site (dev -> prod).

    manage.py export_content OUT_DIR [--since 2026-10-14] [--no-md5]

What goes: every product with an import_source and its photos, documents,
firmware and BOM placements; every component created since --since (the day the
other site's database was copied here: older rows are on both sites already)
with its cross-references; datasheets uploaded since then; import-review
verdicts. Rows carry their moderation state (approved, pending, category lock);
what a moderator rejected was deleted and so is not exported.

OUT_DIR gets one JSONL file per model (in load order), users.json (the users
the rows refer to, by id and username) and files.tsv (media path, size, md5 of
every file the rows point to - the files themselves are copied separately).
"""
import datetime
import hashlib
import json
import os

from django.core import serializers
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder

from apps.components.models import Component, ComponentDatasheet, ProductComponent
from apps.products.models import Firmware, ImportReview, Product, ProductImage, Schematic
from apps.users.models import User

# load order: what a row refers to is loaded before it
MODELS = ['components.Component', 'products.Product', 'products.ProductImage', 'products.Schematic',
          'products.Firmware', 'components.ComponentDatasheet', 'components.ProductComponent',
          'products.ImportReview']
USER_FIELDS = ('created_by', 'uploaded_by', 'verified_by', 'reviewer')


def md5_of(name):
    h = hashlib.md5()
    with default_storage.open(name, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


class Command(BaseCommand):
    help = 'Export bulk-imported content (with its review state) for load_content'

    def add_arguments(self, parser):
        parser.add_argument('out')
        parser.add_argument('--since', default='2026-10-14',
                            help="the day the other site's database was copied here (YYYY-MM-DD)")
        parser.add_argument('--no-md5', action='store_true', help='skip checksums (quick test runs)')

    def querysets(self, since):
        imported = Product.objects.exclude(import_source='')
        return {
            'components.Component': Component.objects.filter(created_at__gte=since),
            'products.Product': imported,
            'products.ProductImage': ProductImage.objects.filter(product__in=imported),
            'products.Schematic': Schematic.objects.filter(product__in=imported),
            'products.Firmware': Firmware.objects.filter(product__in=imported),
            'components.ComponentDatasheet': ComponentDatasheet.objects.filter(uploaded_at__gte=since),
            'components.ProductComponent': ProductComponent.objects.filter(product__in=imported),
            'products.ImportReview': ImportReview.objects.all(),
        }

    def handle(self, *args, **opts):
        out = opts['out']
        os.makedirs(out, exist_ok=True)
        since = datetime.datetime.fromisoformat(opts['since']).replace(tzinfo=datetime.timezone.utc)
        users, files = set(), {}
        for label, qs in self.querysets(since).items():
            model = qs.model
            file_fields = [f.name for f in model._meta.fields if f.get_internal_type() in ('FileField', 'ImageField')]
            n = 0
            with open(os.path.join(out, f'{label}.jsonl'), 'w', encoding='utf-8') as fh:
                for obj in qs.order_by('pk').iterator(chunk_size=2000):
                    rec = serializers.serialize('python', [obj])[0]
                    rec['fields'].pop('search_vector', None)
                    for f in USER_FIELDS:
                        if rec['fields'].get(f):
                            users.add(rec['fields'][f])
                    for f in file_fields:
                        if rec['fields'].get(f):
                            files[rec['fields'][f]] = None
                    fh.write(json.dumps(rec, cls=DjangoJSONEncoder, ensure_ascii=False) + '\n')
                    n += 1
            self.stdout.write(f'{label}: {n}')
        with open(os.path.join(out, 'users.json'), 'w') as fh:
            json.dump({str(u.pk): u.username for u in User.objects.filter(pk__in=users)}, fh, indent=1)
        missing = 0
        with open(os.path.join(out, 'files.tsv'), 'w') as fh:
            for name in sorted(files):
                if not default_storage.exists(name):
                    missing += 1
                    continue
                size = default_storage.size(name)
                fh.write(f"{name}\t{size}\t{'' if opts['no_md5'] else md5_of(name)}\n")
        self.stdout.write(f'users: {len(users)}; files: {len(files) - missing} '
                          f'({missing} referenced but missing here)')
