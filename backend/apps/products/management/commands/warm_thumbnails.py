"""
Management command to pre-generate product image thumbnails.

Changing the thumbnail ImageSpecField's processors (e.g. AdaptiveThumbnail's
crop/letterbox logic) invalidates every existing cached thumbnail, since
django-imagekit derives the cache filename from the processor pipeline. If
that's left to happen lazily, the first real page load after a deploy ends
up firing many concurrent thumbnail-generation requests at once (e.g. a
product grid loading a dozen+ images simultaneously), which can race and
serve broken images. Run this once right after deploying such a change so
all thumbnails are already warmed before real traffic hits them.
"""
from django.core.management.base import BaseCommand
from apps.products.models import ProductImage


class Command(BaseCommand):
    help = 'Pre-generate thumbnail and medium image specs for all product images.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate even if a cached version already exists.',
        )

    def handle(self, *args, **options):
        force = options['force']
        images = ProductImage.objects.all()
        total = images.count()
        ok = 0
        failed = 0

        for image in images:
            for spec_name in ('thumbnail', 'medium'):
                spec = getattr(image, spec_name)
                try:
                    # ImageCacheFile.generate(force=True) doesn't overwrite an
                    # existing file in place — FileSystemStorage just saves a
                    # second copy under a randomized suffix and leaves the
                    # original cache entry untouched. Delete first so a forced
                    # regeneration actually replaces what gets served.
                    if force and spec.storage.exists(spec.name):
                        spec.storage.delete(spec.name)
                    spec.generate(force=force)
                except Exception as exc:
                    failed += 1
                    self.stderr.write(self.style.ERROR(
                        f'{image.product.manufacturer} {image.product.model_number} '
                        f'({spec_name}, image {image.id}): {exc}'
                    ))
                else:
                    ok += 1

        self.stdout.write(self.style.SUCCESS(
            f'Warmed {ok} thumbnail/medium spec(s) across {total} product image(s) '
            f'({failed} failed).'
        ))
