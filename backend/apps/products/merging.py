"""
Fold one product into another: links moved (a duplicate link dropped, its approval kept), photos, documents and
firmware moved, approval carried over, the duplicate's review rows and the duplicate itself deleted. Used by
dedupe_stub_machines (stub machines) and fix_family_typos (a typo'd name whose corrected form is another page).
"""
from .models import Firmware, ImportReview, ProductImage, ProductLink, Schematic


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
    if ProductImage.objects.filter(product=target, is_primary=True).exists():
        ProductImage.objects.filter(product=dup, is_primary=True).update(is_primary=False)   # one preview per page
    for model in (ProductImage, Schematic, Firmware):
        moved = model.objects.filter(product=dup).update(product=target)
        if moved:
            n['files moved'] += moved
    if dup.is_approved and not target.is_approved:
        target.is_approved = True
        target.save(update_fields=['is_approved'])
        n['survivors approved'] += 1
    delete_product(dup)


def delete_product(dup):
    """Delete a product with its links and review rows."""
    ProductLink.objects.filter(host=dup).delete()
    ProductLink.objects.filter(part=dup).delete()
    ImportReview.objects.filter(object_id=dup.pk).delete()
    dup.delete()
