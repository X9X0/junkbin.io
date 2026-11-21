"""
Fold one product into another: links moved (a duplicate link dropped, its approval kept), every other row that
points at the duplicate moved (photos, documents, firmware, placements, comments, repair reports, suggestions,
submissions, swap-shop items, reports), approval carried over, the duplicate's review rows and the duplicate itself
deleted. Used by dedupe_stub_machines (stub machines), fix_family_typos (a typo'd name whose corrected form is
another page) and merge_sized_twins (one machine under two spellings).
"""
from django.contrib.contenttypes.models import ContentType
from django.db.models import ForeignKey

from apps.components.models import ProductComponent

from .models import ImportReview, Product, ProductImage, ProductLink

# generic-relation tables (content_type + object_id) that may point at a product
GENERIC = (('junkbin', 'junkbinitem'), ('reports', 'report'))


def merge_product(dup, target, n):
    """Move everything `dup` carries to `target` and delete `dup`; counts go into the Counter `n`."""
    for link in ProductLink.objects.filter(host=dup):
        twin = ProductLink.objects.filter(part_id=link.part_id, host=target, kind=link.kind).first()
        if twin or link.part_id == target.pk:
            if twin and link.is_approved and not twin.is_approved:
                twin.is_approved = True
                twin.save(update_fields=['is_approved'])
            link.delete()
            n['duplicate links dropped'] += 1
        else:
            link.host = target
            link.save(update_fields=['host'])
            n['links moved'] += 1
    for link in ProductLink.objects.filter(part=dup):
        if link.host_id == target.pk or ProductLink.objects.filter(part=target, host_id=link.host_id, kind=link.kind).exists():
            link.delete()
            n['duplicate links dropped'] += 1
        else:
            link.part = target
            link.save(update_fields=['part'])
            n['links moved'] += 1
    # a placement the target already has (same part at the same designator) is dropped, the rest move
    have = set(ProductComponent.objects.filter(product=target).values_list('component_id', 'reference_designator'))
    for pc in ProductComponent.objects.filter(product=dup):
        if (pc.component_id, pc.reference_designator) in have:
            pc.delete()
            n['duplicate placements dropped'] += 1
        else:
            pc.product = target
            pc.save(update_fields=['product'])
            have.add((pc.component_id, pc.reference_designator))
            n['placements moved'] += 1
    if ProductImage.objects.filter(product=target, is_primary=True).exists():
        ProductImage.objects.filter(product=dup, is_primary=True).update(is_primary=False)   # one preview per page
    for rel in Product._meta.get_fields():
        if not (rel.auto_created and not rel.concrete and isinstance(rel.field, ForeignKey)):
            continue
        if rel.related_model in (ProductLink, ProductComponent):
            continue
        moved = rel.related_model.objects.filter(**{rel.field.name: dup}).update(**{rel.field.name: target})
        if moved:
            n['rows moved'] += moved
    ct = ContentType.objects.get_for_model(Product)
    for app_label, model in GENERIC:
        try:
            m = ContentType.objects.get(app_label=app_label, model=model).model_class()
        except ContentType.DoesNotExist:
            continue
        moved = m.objects.filter(content_type=ct, object_id=dup.pk).update(object_id=target.pk)
        if moved:
            n['rows moved'] += moved
    if dup.is_approved and not target.is_approved:
        target.is_approved = True
        target.save(update_fields=['is_approved'])
        n['survivors approved'] += 1
    delete_product(dup)
    target.update_component_count()


def delete_product(dup):
    """Delete a product with its links and review rows."""
    ProductLink.objects.filter(host=dup).delete()
    ProductLink.objects.filter(part=dup).delete()
    ImportReview.objects.filter(object_id=dup.pk).delete()
    dup.delete()
