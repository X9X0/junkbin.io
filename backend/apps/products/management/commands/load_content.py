"""
Load an export_content directory into this site, beside what it already has.

    manage.py load_content DIR [--dry-run] [--allow-missing-files] [--restore-dates]

Copy the media files first (files.tsv): the load stops if any is missing,
unless --allow-missing-files. Everything happens in one transaction; --dry-run
reports what it would do and rolls back.

Rows this site already has (same id) are left as they are. A new product whose
maker/model/revision/region, or a new component whose maker/part number, this
site already has is not added: its photos, documents and placements go to the
existing one. Users are matched by id, then username; an unknown user leaves
the field empty. Datasheet and review-verdict rows get new ids here. Afterwards
component usage counts, the product counts of products that gained rows, and
the search index of the new rows are rebuilt.

Rows keep their dates from the other site (bulk_create would stamp them with the
load time). --restore-dates does only that, for a site loaded before it did: a
row's creation date only moves earlier, and its last-updated date is put back
only while the row is unchanged since it was added.
"""
import json
import os
from collections import Counter

from django.apps import apps
from django.contrib.postgres.search import SearchVector
from django.core import serializers
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Count, OuterRef, Subquery
from django.db.models.functions import Coalesce

from apps.components.models import Component, ComponentDatasheet, ProductComponent
from apps.products.models import Firmware, ImportReview, Product, ProductImage, Schematic
from apps.users.models import User

from .export_content import MODELS, USER_FIELDS

BATCH = 2000


class DryRun(Exception):
    pass


def chunks(iterable, n=BATCH):
    batch = []
    for x in iterable:
        batch.append(x)
        if len(batch) == n:
            yield batch
            batch = []
    if batch:
        yield batch


class Command(BaseCommand):
    help = 'Load an export_content directory beside this site\'s own content'

    def add_arguments(self, parser):
        parser.add_argument('dir')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--allow-missing-files', action='store_true')
        parser.add_argument('--restore-dates', action='store_true',
                            help='only put the exported dates back on rows an earlier load added')

    def records(self, label):
        with open(os.path.join(self.dir, f'{label}.jsonl'), encoding='utf-8') as fh:
            for line in fh:
                yield json.loads(line)

    def objects(self, label):
        """(deserialized object, m2m data) per row, in batches."""
        for batch in chunks(self.records(label)):
            yield [(d.object, d.m2m_data) for d in serializers.deserialize('python', batch, ignorenonexistent=True)]

    def map_users(self, obj):
        for f in USER_FIELDS:
            attname = f + '_id'
            if hasattr(obj, attname) and getattr(obj, attname) is not None:
                setattr(obj, attname, self.users.get(str(getattr(obj, attname))))

    def handle(self, *args, **opts):
        self.dir = opts['dir']
        for label in MODELS:
            if not os.path.exists(os.path.join(self.dir, f'{label}.jsonl')):
                raise CommandError(f'{label}.jsonl missing from {self.dir}')
        missing = self.missing_files()
        self.stdout.write(f'media: {missing} of the listed files are not here')
        if missing and not (opts['dry_run'] or opts['allow_missing_files']):
            raise CommandError('copy the media files first (or --allow-missing-files)')
        self.n = Counter()
        self.notes = []
        try:
            with transaction.atomic():
                if not opts['restore_dates']:
                    self.load()
                    self.rebuild()
                self.restore_dates()
                self.report()
                if opts['dry_run']:
                    raise DryRun
        except DryRun:
            self.stdout.write('dry run: rolled back')

    def missing_files(self):
        missing = 0
        with open(os.path.join(self.dir, 'files.tsv')) as fh:
            for line in fh:
                name = line.split('\t')[0]
                if not default_storage.exists(name):
                    missing += 1
        return missing

    def load(self):
        with open(os.path.join(self.dir, 'users.json')) as fh:
            wanted = json.load(fh)
        by_pk = {str(pk) for pk in User.objects.filter(pk__in=list(wanted)).values_list('pk', flat=True)}
        by_name = dict(User.objects.filter(username__in=list(wanted.values())).values_list('username', 'pk'))
        self.users = {pk: (pk if pk in by_pk else by_name.get(name)) for pk, name in wanted.items()}
        unknown = [name for pk, name in wanted.items() if self.users[pk] is None]
        if unknown:
            self.notes.append(f'users not on this site (fields left empty): {", ".join(sorted(unknown))}')
        self.cmap, self.pmap, self.images = {}, {}, set()
        self.load_components()
        self.load_products()
        self.load_children('products.ProductImage', ProductImage)
        self.load_children('products.Schematic', Schematic)
        self.load_children('products.Firmware', Firmware)
        self.load_datasheets()
        self.load_placements()
        self.load_reviews()

    # --- components ---------------------------------------------------------------
    def load_components(self):
        pairs = []
        for batch in self.objects('components.Component'):
            pks = [o.pk for o, _ in batch]
            have = set(Component.objects.filter(pk__in=pks).values_list('pk', flat=True))
            keys = {}
            for c in Component.objects.filter(part_number__in={o.part_number for o, _ in batch}).only(
                    'pk', 'manufacturer', 'part_number'):
                keys[(c.manufacturer, c.part_number)] = c.pk
            new = []
            for o, m2m in batch:
                pairs += [(o.pk, other) for other in m2m.get('cross_references', [])]
                if o.pk in have:
                    self.cmap[o.pk] = o.pk
                    self.n['components already here'] += 1
                elif (o.manufacturer, o.part_number) in keys:
                    self.cmap[o.pk] = keys[(o.manufacturer, o.part_number)]
                    self.n['components merged into an existing one'] += 1
                else:
                    self.map_users(o)
                    self.cmap[o.pk] = o.pk
                    keys[(o.manufacturer, o.part_number)] = o.pk
                    new.append(o)
            Component.objects.bulk_create(new)
            self.n['components added'] += len(new)
        through = Component.cross_references.through
        src, dst = [f.attname for f in through._meta.fields if f.is_relation]
        rows = []
        for a, b in pairs:
            a, b = self.cmap.get(a, a), self.cmap.get(self.parse_pk(b), self.parse_pk(b))
            rows.append(through(**{src: a, dst: b}))
        existing = set(Component.objects.filter(pk__in={getattr(r, dst) for r in rows}).values_list('pk', flat=True))
        rows = [r for r in rows if getattr(r, dst) in existing and getattr(r, src) != getattr(r, dst)]
        through.objects.bulk_create(rows, ignore_conflicts=True, batch_size=BATCH)
        self.n['cross-references'] += len(rows)

    @staticmethod
    def parse_pk(value):
        import uuid
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))

    # --- products -----------------------------------------------------------------
    def load_products(self):
        for batch in self.objects('products.Product'):
            have = set(Product.objects.filter(pk__in=[o.pk for o, _ in batch]).values_list('pk', flat=True))
            slugs = set(Product.objects.filter(slug__in=[o.slug for o, _ in batch]).values_list('slug', flat=True))
            new = []
            for o, _ in batch:
                if o.pk in have:
                    self.pmap[o.pk] = o.pk
                    self.n['products already here'] += 1
                    continue
                same = Product.objects.filter(manufacturer=o.manufacturer, model_number=o.model_number,
                                              revision=o.revision, region=o.region).values_list('pk', flat=True).first()
                if same:
                    self.pmap[o.pk] = same
                    self.n['products merged into an existing one'] += 1
                    self.notes.append(f'product {o.manufacturer} {o.model_number} {o.revision} already here: '
                                      'its files and parts list go to that one')
                    continue
                if o.slug in slugs:
                    base, i = o.slug, 2
                    while Product.objects.filter(slug=f'{base}-{i}').exists() or f'{base}-{i}' in slugs:
                        i += 1
                    o.slug = f'{base}-{i}'
                slugs.add(o.slug)
                self.map_users(o)
                self.pmap[o.pk] = o.pk
                new.append(o)
            Product.objects.bulk_create(new)
            self.n['products added'] += len(new)

    def load_children(self, label, model):
        """Photos, schematics, firmware: keyed by product."""
        primaries = set(model.objects.filter(is_primary=True).values_list('product_id', flat=True)) \
            if model is ProductImage else set()
        for batch in self.objects(label):
            have = set(model.objects.filter(pk__in=[o.pk for o, _ in batch]).values_list('pk', flat=True))
            new = []
            for o, _ in batch:
                if o.pk in have:
                    self.n[f'{label} already here'] += 1
                    if model is ProductImage:
                        self.images.add(o.pk)
                    continue
                o.product_id = self.pmap.get(o.product_id, o.product_id)
                self.map_users(o)
                if model is ProductImage:
                    if o.is_primary and o.product_id in primaries:
                        o.is_primary = False
                    elif o.is_primary:
                        primaries.add(o.product_id)
                    self.images.add(o.pk)
                new.append(o)
            model.objects.bulk_create(new)
            self.n[f'{label} added'] += len(new)

    def load_datasheets(self):
        for batch in self.objects('components.ComponentDatasheet'):
            new = []
            for o, _ in batch:
                o.component_id = self.cmap.get(o.component_id, o.component_id)
                if ComponentDatasheet.objects.filter(component_id=o.component_id, file=o.file.name).exists():
                    self.n['datasheets already here'] += 1
                    continue
                o.pk = None
                self.map_users(o)
                new.append(o)
            ComponentDatasheet.objects.bulk_create(new)
            self.n['datasheets added'] += len(new)

    def load_placements(self):
        for batch in self.objects('components.ProductComponent'):
            have = set(ProductComponent.objects.filter(pk__in=[o.pk for o, _ in batch]).values_list('pk', flat=True))
            new = []
            for o, _ in batch:
                if o.pk in have:
                    self.n['placements already here'] += 1
                    continue
                o.product_id = self.pmap.get(o.product_id, o.product_id)
                o.component_id = self.cmap.get(o.component_id, o.component_id)
                if o.image_reference_id and o.image_reference_id not in self.images:
                    o.image_reference_id = None
                self.map_users(o)
                new.append(o)
            ProductComponent.objects.bulk_create(new)
            self.n['placements added'] += len(new)

    def load_reviews(self):
        for batch in self.objects('products.ImportReview'):
            new = []
            for o, _ in batch:
                o.pk = None
                self.map_users(o)
                new.append(o)
            ImportReview.objects.bulk_create(new, ignore_conflicts=True)
            self.n['review verdicts'] += len(new)

    # --- afterwards ---------------------------------------------------------------
    def rebuild(self):
        touched = set(self.cmap.values())
        for batch in chunks(touched):
            Component.objects.filter(pk__in=batch).update(usage_count=Coalesce(Subquery(
                ProductComponent.objects.filter(component=OuterRef('pk')).values('component')
                .annotate(n=Count('pk')).values('n')[:1]), 0))
        merged = {v for k, v in self.pmap.items() if k != v}
        for p in Product.objects.filter(pk__in=merged):
            p.update_component_count()
        new_products = [k for k, v in self.pmap.items() if k == v]
        for batch in chunks(new_products):
            Product.objects.filter(pk__in=batch, search_vector__isnull=True).update(search_vector=(
                SearchVector('manufacturer', weight='A') + SearchVector('model_number', weight='A') +
                SearchVector('fcc_id', weight='B') + SearchVector('description', weight='C') +
                SearchVector('teardown_notes', weight='D')))
        for batch in chunks([k for k, v in self.cmap.items() if k == v]):
            Component.objects.filter(pk__in=batch, search_vector__isnull=True).update(
                search_vector=Component.search_vector_expression())

    # --- dates ----------------------------------------------------------------------
    DATE_KEYS = {'components.ComponentDatasheet': ('file',), 'products.ImportReview': ('batch', 'item_type', 'object_id')}

    def restore_dates(self):
        """Put the exported auto_now / auto_now_add dates back. Rows are found by id, or for the
        models whose rows get new ids here, by file / review key; merged rows are not touched."""
        for label in MODELS:
            model = apps.get_model(label)
            created = [f for f in model._meta.concrete_fields if getattr(f, 'auto_now_add', False)]
            updated = [f for f in model._meta.concrete_fields if getattr(f, 'auto_now', False)]
            if not created and not updated:
                continue
            keys = [model._meta.get_field(k) for k in self.DATE_KEYS[label]] if label in self.DATE_KEYS \
                else [model._meta.pk]
            cols = keys + created + updated
            sets, where = [], []
            # the export cuts dates to milliseconds: a row both sites had is that much "later"
            for f in created:
                sets.append(f'{f.column} = v.{f.column}')
                where.append(f"t.{f.column} > v.{f.column} + interval '1 second'")
            for f in updated:
                if created:     # unchanged since added: bulk_create stamped both in the same instant
                    sets.append(f"{f.column} = CASE WHEN t.{f.column} - t.{created[0].column} < interval '1 second' "
                                f'THEN v.{f.column} ELSE t.{f.column} END')
                else:
                    sets.append(f'{f.column} = v.{f.column}')
                    where.append(f"t.{f.column} > v.{f.column} + interval '1 second'")
            n = 0
            for batch in chunks(self.records(label)):
                rows = []
                for rec in batch:
                    vals = [rec['pk'] if k.primary_key else rec['fields'].get(k.name) for k in keys]
                    vals += [rec['fields'].get(f.name) for f in created + updated]
                    if None not in vals:
                        rows.append(vals)
                if not rows:
                    continue
                casts = ', '.join(f'%s::{f.db_type(connection)}' for f in cols)
                sql = (f'UPDATE {model._meta.db_table} t SET {", ".join(sets)} '
                       f'FROM (VALUES {", ".join([f"({casts})"] * len(rows))}) '
                       f'AS v({", ".join(f.column for f in cols)}) '
                       f'WHERE {" AND ".join(f"t.{k.column} = v.{k.column}" for k in keys)} '
                       f'AND ({" OR ".join(where)})')
                with connection.cursor() as cur:
                    cur.execute(sql, [x for r in rows for x in r])
                    n += cur.rowcount
            self.n[f'{label} dates restored'] += n

    def report(self):
        for k in sorted(self.n):
            self.stdout.write(f'  {k}: {self.n[k]}')
        for note in self.notes[:50]:
            self.stdout.write(f'  note: {note}')
        if len(self.notes) > 50:
            self.stdout.write(f'  ... and {len(self.notes) - 50} more notes')
