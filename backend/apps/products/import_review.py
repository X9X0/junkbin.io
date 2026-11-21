"""
Human review of bulk-import batches before they go public.

A batch is everything one import lane created (BATCHES). Reviewers are shown
randomly drawn, not-yet-reviewed items with their evidence and mark each
correct or flagged. approve_batch() makes a batch public only when at least
SAMPLE_TARGET items (or the whole batch, if smaller) are marked correct and
no flag is outstanding; a superuser may force it. The norway-bom-pn batch's items are
parts whose part number a factory BOM line gave without confirmation: its BOM rows carry
the REVIEW mark, and marking the part correct takes the mark off all of them at once.
"""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from django.conf import settings

from apps.components.models import Component, ComponentDatasheet, ComponentImage, ComponentTypeImage, ProductComponent
from utils.cache import clear_page_cache
from .models import Firmware, ImportReview, Product, ProductImage, ProductLink, Schematic

SAMPLE_TARGET = 100

BATCHES = {
    'type-image': {'label': 'Default photos per component type and package (shown for every part without a photo of its own)',
                   'item_type': 'type-image'},
    'component-image': {'label': 'Renderings of individual parts (through-hole resistors with their colour bands, capacitors with their value)',
                        'item_type': 'component-image'},
    'norway-bom': {'label': 'Factory-BOM boards (Asus, 2002-2007)', 'item_type': 'product'},
    'norway-schem': {'label': 'Schematic boards up to 2008 (Asus, MSI, Gigabyte)', 'item_type': 'product'},
    'norway-board': {'label': 'Mainboards by board code (Compal, Quanta, Lenovo, Wistron, Inventec, Samsung, Apple)', 'item_type': 'product'},
    'norway-machine': {'label': 'Machines known only from a board schematic or listings that name them (stub products)', 'item_type': 'product'},
    'norway-board-stub': {'label': 'Boards known only from listings or BIOS labels, no schematic yet (stub products)', 'item_type': 'product'},
    'norway-svc': {'label': 'Products from service manuals', 'item_type': 'product'},
    'norway-board-links': {'label': 'Boards fitted in laptops (board-to-device links)', 'item_type': 'link'},
    'norway-ds-new': {'label': 'Components created from datasheets', 'item_type': 'component'},
    'norway-ds': {'label': 'Datasheets attached to existing components', 'item_type': 'datasheet'},
    'norway-fw': {'label': 'Firmware / BIOS flash dumps (mostly laptops)', 'item_type': 'firmware'},
    'image-search': {'label': 'Product photos found by image search', 'item_type': 'image'},
    'teardown': {'label': 'Products and parts lists from teardown write-ups (blogs, iFixit), facts only, source linked',
                 'item_type': 'product'},
    'norway-bom-pn': {'label': 'Part numbers read from a BOM line or a schematic label, not confirmed',
                      'item_type': 'bom-part'},
}
# the note import_board_bom gives a BOM row whose part number was read from the line, unconfirmed
UNCONFIRMED = 'part number read from the factory BOM line, not confirmed'


def items(batch):
    """Queryset of the batch's reviewable items."""
    if batch not in BATCHES:
        raise KeyError(batch)
    kind = BATCHES[batch]['item_type']
    if kind == 'product':
        return Product.objects.filter(import_source__startswith=f'{batch}:')
    if kind == 'component':
        return Component.objects.filter(datasheets__source_notes__startswith=f'[{batch}]').distinct()
    if kind == 'firmware':
        return Firmware.objects.filter(source_notes__startswith=f'[{batch}:')
    if kind == 'image':
        return ProductImage.objects.filter(source_notes__startswith=f'[{batch}]')
    if kind == 'type-image':
        return ComponentTypeImage.objects.filter(source_notes__startswith=f'[{batch}]')
    if kind == 'component-image':
        return ComponentImage.objects.filter(source_notes__startswith=f'[{batch}]')
    if kind == 'link':
        return ProductLink.objects.filter(import_source__startswith=f'{batch}:')
    if kind == 'bom-part':
        return Component.objects.filter(pk__in=unconfirmed_rows().values('component_id'))
    return ComponentDatasheet.objects.filter(source_notes__startswith=f'[{batch}]')


# the note extract_schematic_boms gives a chip read from a schematic label, unconfirmed
UNCONFIRMED_LABEL = 'part number read from the schematic label; no factory BOM checked it'


def unconfirmed_rows(component=None):
    """BOM rows whose part number was read from a factory-BOM line or a schematic label
    without anything confirming it (import_board_bom marks them needs_review)."""
    rows = ProductComponent.objects.filter(
        Q(import_source__startswith='norway-bom:', notes__contains=UNCONFIRMED)
        | Q(import_source__startswith='schematic-bom:', notes__contains=UNCONFIRMED_LABEL))
    return rows.filter(component=component) if component is not None else rows


def stats(batch):
    qs = items(batch)
    total = qs.count()
    reviews = ImportReview.objects.filter(batch=batch)
    correct = reviews.filter(verdict=ImportReview.Verdict.CORRECT).count()
    flagged = reviews.filter(verdict=ImportReview.Verdict.FLAGGED).count()
    target = min(SAMPLE_TARGET, total)
    return {
        'batch': batch, 'label': BATCHES[batch]['label'], 'item_type': BATCHES[batch]['item_type'],
        'total': total, 'reviewed': correct + flagged, 'correct': correct, 'flagged': flagged,
        'target': target, 'unapproved': unapproved_count(batch),
        'can_approve': total > 0 and correct >= target and flagged == 0,
    }


def unapproved_count(batch):
    kind = BATCHES[batch]['item_type']
    if kind in ('product', 'firmware', 'image', 'link', 'type-image', 'component-image'):
        return items(batch).filter(is_approved=False).count()
    if kind == 'bom-part':                  # its rows show the REVIEW mark until accepted
        return items(batch).filter(product_components__in=unconfirmed_rows().filter(needs_review=True)) \
            .distinct().count()
    return ComponentDatasheet.objects.filter(source_notes__startswith=f'[{batch}]', is_approved=False).count()


def next_items(batch, n=10):
    """n random items nobody has reviewed yet."""
    reviewed = ImportReview.objects.filter(batch=batch).values_list('object_id', flat=True)
    return list(items(batch).exclude(pk__in=reviewed).order_by('?')[:n])


def evidence(batch, obj):
    """What a reviewer needs to judge one item."""
    kind = BATCHES[batch]['item_type']
    if kind == 'product':
        docs = obj.schematics.order_by('uploaded_at')[:6]
        image = obj.images.order_by('-is_primary').first()
        rows = (obj.product_components.select_related('component').order_by('reference_designator')[:6])
        return {
            'item_type': 'product', 'id': str(obj.pk), 'slug': obj.slug,
            'title': f'{obj.manufacturer} {obj.model_number}', 'revision': obj.revision,
            'category': obj.get_category_display(), 'subcategory': obj.subcategory,
            'year': obj.year_manufactured, 'description': obj.description,
            'component_count': obj.component_count,
            'documents': [{'title': d.title, 'type': d.get_schematic_type_display(), 'url': d.file.url,
                           'description': d.description} for d in docs],
            'image': image.image.url if image else None,
            'bom_sample': [{'ref': r.reference_designator[:60], 'part': r.component.part_number,
                            'maker': r.component.manufacturer, 'notes': r.notes[:160]} for r in rows],
        }
    if kind == 'firmware':
        product = obj.product
        return {
            'item_type': 'firmware', 'id': str(obj.pk), 'slug': product.slug,
            'title': f'{product.manufacturer} {product.model_number}', 'revision': product.revision,
            'category': product.get_category_display(), 'description': obj.description,
            'documents': [{'title': obj.title, 'type': 'Firmware', 'url': obj.file.url,
                           'description': f'{obj.file_size or 0:,} bytes'
                                          + (f' · {obj.version}' if obj.version else '')
                                          + (f' · {obj.chip_architecture}' if obj.chip_architecture else '')}],
        }
    if kind == 'link':
        part, host = obj.part, obj.host
        return {
            'item_type': 'link', 'id': str(obj.pk), 'slug': part.slug,
            'title': f'{part.manufacturer} {part.model_number} {obj.get_kind_display().lower()} {host.manufacturer} {host.model_number}',
            'revision': part.revision, 'category': part.get_category_display(), 'subcategory': part.subcategory,
            'description': obj.evidence,
            'documents': [{'title': f'{part.manufacturer} {part.model_number}' + (f' Rev {part.revision}' if part.revision else ''),
                           'type': 'Board', 'url': f'/products/{part.slug}', 'description': part.description[:200]},
                          {'title': f'{host.manufacturer} {host.model_number}' + (f' Rev {host.revision}' if host.revision else ''),
                           'type': str(obj.get_kind_display()), 'url': f'/products/{host.slug}', 'description': host.description[:200]}],
        }
    if kind == 'image':
        product = obj.product
        return {
            'item_type': 'image', 'id': str(obj.pk), 'slug': product.slug,
            'title': f'{product.manufacturer} {product.model_number}', 'revision': product.revision,
            'category': product.get_category_display(), 'description': obj.caption,
            'documents': [{'title': obj.source_url, 'type': 'Found on', 'url': obj.source_url,
                           'description': obj.source_notes.removeprefix(f'[{batch}]').strip()}]
                         if obj.source_url else [],
            'image': obj.image.url,
        }
    if kind == 'type-image':
        types = dict(settings.COMPONENT_TYPES)
        return {
            'item_type': 'type-image', 'id': str(obj.pk), 'slug': '',
            'component_type': obj.component_type, 'package_type': obj.package_type,
            'title': f"{types.get(obj.component_type, obj.component_type)} · {obj.package_type or 'any package'}",
            'revision': '', 'category': 'default photo',
            'description': ('Shown for every ' + str(types.get(obj.component_type, obj.component_type)).lower()
                            + (f' in a {obj.package_type} package' if obj.package_type else ' without a package-specific default')
                            + ' that has no photo of its own.'),
            'documents': [{'title': obj.source_url, 'type': 'Found on', 'url': obj.source_url,
                           'description': obj.source_notes.removeprefix(f'[{batch}]').strip()}] if obj.source_url else [],
            'image': obj.image.url,
        }
    if kind == 'component-image':
        c = obj.component
        return {
            'item_type': 'component-image', 'id': str(obj.pk), 'slug': '', 'component_id': str(c.pk),
            'title': f'{c.manufacturer} {c.part_number}', 'revision': '', 'category': c.get_component_type_display(),
            'description': obj.caption,
            'documents': [{'title': obj.source_url or 'Rendered here', 'type': 'Made from', 'url': obj.source_url or f'/components/{c.pk}',
                           'description': obj.source_notes.removeprefix(f'[{batch}]').strip()}],
            'image': obj.image.url,
        }
    if kind == 'bom-part':
        rows = unconfirmed_rows(obj).select_related('product').order_by('product__model_number')
        lines, why = {}, {}
        for row in rows:
            marker = UNCONFIRMED if UNCONFIRMED in row.notes else UNCONFIRMED_LABEL
            line, _, reason = row.notes.partition(f'; {marker}')
            line = line.removeprefix('Factory BOM line: ').removeprefix('Schematic label: ')
            lines[line] = lines.get(line, 0) + 1
            why.setdefault(reason.lstrip(': ') or ('read from a schematic label' if marker == UNCONFIRMED_LABEL else ''), None)
        products = {row.product_id: row.product for row in rows}
        return {
            'item_type': 'bom-part', 'id': str(obj.pk), 'component_id': str(obj.pk),
            'title': f'{obj.manufacturer} {obj.part_number}', 'category': obj.get_component_type_display(),
            'description': 'Not confirmed because ' + '; or '.join(r for r in why if r) + '.' if any(why) else '',
            'component_count': len(rows),
            'documents': [{'title': f'{p.manufacturer} {p.model_number} Rev {p.revision}', 'type': 'Used on',
                           'url': f'/products/{p.pk}', 'description': ''} for p in list(products.values())[:4]],
            'bom_sample': [{'ref': f'{n} row' + ('s' if n > 1 else ''), 'part': obj.part_number,
                            'maker': obj.manufacturer, 'notes': line[:300]}
                           for line, n in sorted(lines.items(), key=lambda kv: -kv[1])[:6]],
        }
    if kind == 'component':
        ds = obj.datasheets.filter(source_notes__startswith=f'[{batch}]').first()
        return {
            'item_type': 'component', 'id': str(obj.pk), 'title': f'{obj.manufacturer} {obj.part_number}',
            'category': obj.get_component_type_display(), 'description': obj.description,
            'documents': [{'title': ds.title, 'type': 'Datasheet', 'url': ds.file.url}] if ds else [],
        }
    return {
        'item_type': 'datasheet', 'id': str(obj.pk),
        'title': f'{obj.component.manufacturer} {obj.component.part_number}',
        'component_id': str(obj.component_id), 'category': obj.component.get_component_type_display(),
        'description': obj.component.description,
        'documents': [{'title': obj.title, 'type': 'Datasheet', 'url': obj.file.url}],
    }


@transaction.atomic
def approve_batch(batch, user=None, force=False):
    """Make the batch public. Returns counts; raises ValueError when the review gate isn't met."""
    s = stats(batch)
    if not s['can_approve'] and not force:
        raise ValueError(f"review gate not met for {batch}: {s['correct']}/{s['target']} correct, "
                         f"{s['flagged']} flagged")
    kind = BATCHES[batch]['item_type']
    counts = {}
    if kind == 'product':
        products = items(batch)
        counts['products'] = products.filter(is_approved=False).update(is_approved=True)
        counts['documents'] = Schematic.objects.filter(product__in=products, source_notes__startswith='[norway-',
                                                       is_approved=False).update(is_approved=True)
        counts['images'] = ProductImage.objects.filter(product__in=products, caption__startswith='First page of',
                                                       is_approved=False).update(is_approved=True)
    elif kind == 'firmware':
        files = items(batch)
        counts['products'] = Product.objects.filter(pk__in=files.values('product_id'),
                                                    import_source__startswith=f'{batch}:',
                                                    is_approved=False).update(is_approved=True)
        counts['firmware'] = files.filter(is_approved=False).update(is_approved=True)
    elif kind == 'image':
        counts['images'] = items(batch).filter(is_approved=False).update(is_approved=True)
    elif kind == 'type-image':
        counts['type_images'] = items(batch).filter(is_approved=False).update(is_approved=True)
    elif kind == 'component-image':
        counts['component_images'] = items(batch).filter(is_approved=False).update(is_approved=True)
    elif kind == 'link':
        counts['links'] = items(batch).filter(is_approved=False).update(is_approved=True)
    elif kind == 'bom-part':
        flagged = ImportReview.objects.filter(batch=batch, verdict=ImportReview.Verdict.FLAGGED) \
            .values_list('object_id', flat=True)
        counts['rows'] = unconfirmed_rows().filter(needs_review=True).exclude(component_id__in=flagged) \
            .update(needs_review=False)
    else:
        counts['datasheets'] = ComponentDatasheet.objects.filter(source_notes__startswith=f'[{batch}]',
                                                                 is_approved=False).update(is_approved=True)
    counts['approved_at'] = timezone.now().isoformat()
    clear_page_cache()               # cached lists and counts would hide the batch for up to an hour
    return counts
