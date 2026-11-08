"""
Photos found by image search (import_product_images) after a moderator has looked at them.

A rejected photo leaves feedback (ImageRejection) and, when the reason says the picture itself
was wrong, the next runner-up photo held for the product (ProductImageAlternate) takes its place
in the moderation queue. Each search photo keeps the picture as downloaded, before background
removal, as an applied BackgroundRemovalPreview: the existing "Undo background removal" control
then gives the uncut photo back, and background removal can be run again with other settings.
"""
import re

from django.core.files.base import ContentFile
from django.utils import timezone

from .models import ImageRejection, ProductImage, ProductImageAlternate

# Rejection presets (frontend moderation/pendingItems.ts) that mean "this picture is wrong": the
# next alternate is tried. 'Poor BG removal' is the cut-out's fault, not the picture's (undo the
# removal instead); 'Wrong category' is the listing's fault (fix the category).
WRONG_PICTURE = {'Different product', 'Not the whole product', 'Blurry or small', 'Watermark or text', 'Duplicate'}

NOTES = re.compile(r'^\[(?P<batch>[^\]]+)\] md5=(?P<md5>\S+)(?: Found on (?P<site>\S+))?')
IMAGE_URL = re.compile(r' image (?P<url>https?://\S+)')


def search_meta(image):
    """{'batch', 'md5', 'site', 'image_url'} of a photo an image search imported, else {}."""
    m = NOTES.match(image.source_notes or '')
    if not m:
        return {}
    u = IMAGE_URL.search(image.source_notes)
    return {'batch': m['batch'], 'md5': m['md5'], 'site': m['site'] or '', 'image_url': u['url'] if u else ''}


def notes_for(batch, md5, site='', title='', image_url='', match=''):
    """source_notes of an imported search photo; search_meta() reads it back."""
    return ' '.join(x for x in (
        f'[{batch}] md5={md5}',
        f'Found on {site}' if site else '',
        f'("{title[:200]}")' if title else '',
        f'image {image_url}' if image_url else '',
        'Photo of the series, not this exact model.' if match == 'family' else '',
    ) if x)


def keep_original(image, name, content, user):
    """Store the photo as downloaded as the applied background removal of `image`."""
    from apps.media_tools.models import BackgroundRemovalPreview
    preview = BackgroundRemovalPreview(created_by=user, product_image=image, applied_at=timezone.now(),
                                       status=BackgroundRemovalPreview.Status.DONE)
    preview.original.save(name, ContentFile(content), save=False)
    with image.image.open('rb') as fh:
        preview.result.save(f'cut-{image.pk}.png', ContentFile(fh.read()), save=False)
    preview.save()
    return preview


def rejected_md5s(product):
    return set(ImageRejection.objects.filter(product=product).exclude(md5='').values_list('md5', flat=True))


def record_rejection(image, reason, notes, user):
    meta = search_meta(image)
    return ImageRejection.objects.create(
        product=image.product, batch=meta.get('batch', ''), md5=meta.get('md5', ''),
        site=meta.get('site', ''), image_url=meta.get('image_url', '')[:1000],
        source_url=(image.source_url or '')[:1000], reason=(reason or '')[:50], notes=notes or '',
        background_removed=image.background_removed, rejected_by=user)


def promote_alternate(product, batch, user):
    """Make the best remaining alternate the product's pending photo; None when none is left.
    Alternates whose picture was rejected before are skipped (and dropped)."""
    rejected = rejected_md5s(product)
    for alt in product.image_alternates.filter(batch=batch).order_by('rank'):
        if alt.md5 in rejected:
            _drop(alt)
            continue
        image = ProductImage(
            product=product, image_type=ProductImage.ImageType.OVERVIEW,
            caption=f'{product.manufacturer} {product.model_number}'[:500],
            is_primary=not product.images.filter(is_primary=True).exists(), uploaded_by=user,
            is_approved=False, source_url=alt.source_url,
            source_notes=notes_for(batch, alt.md5, alt.site, alt.title, alt.image_url, alt.match),
            background_removed=True, has_transparency=True)
        with alt.image.open('rb') as fh:
            image.image.save(alt.image.name.rsplit('/', 1)[-1], ContentFile(fh.read()), save=False)
        image.save()
        if alt.original:
            with alt.original.open('rb') as fh:
                keep_original(image, alt.original.name.rsplit('/', 1)[-1], fh.read(), user)
        _drop(alt)
        return image
    return None


def _drop(alt):
    alt.image.delete(save=False)
    if alt.original:
        alt.original.delete(save=False)
    alt.delete()


def reject_search_photo(image, reason, notes, user):
    """Record why `image` was rejected and, for a wrong picture from an image search, queue the
    next alternate. Returns the promoted ProductImage or None. The caller deletes `image`."""
    rejection = record_rejection(image, reason, notes, user)
    meta = search_meta(image)
    if not meta or reason not in WRONG_PICTURE:
        return None
    promoted = promote_alternate(image.product, meta['batch'], image.uploaded_by or user)
    if promoted:
        rejection.alternate_promoted = True
        rejection.save(update_fields=['alternate_promoted'])
    return promoted
