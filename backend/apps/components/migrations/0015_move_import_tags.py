"""
Move bulk-import tags out of fields the site displays, and merge refdes lists
that were split across rows before reference_designator could hold them.

  Product.teardown_notes "[norway-bom:KEY] Component list from ..." ->
      import_source "norway-bom:KEY", the sentence appended to the description,
      teardown_notes cleared (it was shown as "teardown notes").
  ProductComponent.notes "[norway-bom:KEY] Factory BOM line: ..." ->
      import_source "norway-bom:KEY", notes "Factory BOM line: ...".
  Rows of one import with the same product + component -> one row, refdes joined.
"""
import re

from django.db import migrations

TAG = re.compile(r'^\[(norway-[^\]]+)\]\s*')


def forwards(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    ProductComponent = apps.get_model('components', 'ProductComponent')
    Component = apps.get_model('components', 'Component')

    batch = []
    for p in Product.objects.filter(teardown_notes__startswith='[norway-').iterator():
        m = TAG.match(p.teardown_notes)
        if not m:
            continue
        rest = p.teardown_notes[m.end():].strip()
        p.import_source = m.group(1)
        if rest and rest not in (p.description or ''):
            p.description = f'{p.description} {rest}'.strip()
        p.teardown_notes = ''
        batch.append(p)
        if len(batch) >= 500:
            Product.objects.bulk_update(batch, ['import_source', 'description', 'teardown_notes'])
            batch = []
    Product.objects.bulk_update(batch, ['import_source', 'description', 'teardown_notes'])

    batch = []
    for pc in ProductComponent.objects.filter(notes__startswith='[norway-').only('id', 'notes').iterator():
        m = TAG.match(pc.notes)
        if not m:
            continue
        pc.import_source = m.group(1)
        pc.notes = pc.notes[m.end():]
        batch.append(pc)
        if len(batch) >= 2000:
            ProductComponent.objects.bulk_update(batch, ['import_source', 'notes'])
            batch = []
    ProductComponent.objects.bulk_update(batch, ['import_source', 'notes'])

    # merge split refdes rows (same import, product, component)
    from django.db.models import Count
    dupes = (ProductComponent.objects.exclude(import_source='')
             .values('product_id', 'component_id', 'import_source')
             .annotate(n=Count('id')).filter(n__gt=1))
    touched_products, touched_components = set(), set()
    for d in dupes.iterator():
        rows = list(ProductComponent.objects.filter(product_id=d['product_id'], component_id=d['component_id'],
                                                    import_source=d['import_source']).order_by('created_at', 'id'))
        keep, extra = rows[0], rows[1:]
        refs = [r.strip() for row in rows for r in (row.reference_designator or '').split(',') if r.strip()]
        keep.reference_designator = ', '.join(dict.fromkeys(refs))[:2000]
        keep.quantity = min(sum(r.quantity for r in rows), 32767)
        keep.save(update_fields=['reference_designator', 'quantity'])
        ProductComponent.objects.filter(pk__in=[r.pk for r in extra]).delete()
        touched_products.add(d['product_id'])
        touched_components.add(d['component_id'])
    for pid in touched_products:
        Product.objects.filter(pk=pid).update(
            component_count=ProductComponent.objects.filter(product_id=pid).count())
    for cid in touched_components:
        Component.objects.filter(pk=cid).update(
            usage_count=ProductComponent.objects.filter(component_id=cid).count())


class Migration(migrations.Migration):

    dependencies = [
        ('components', '0014_import_source'),
        ('products', '0024_import_source'),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
