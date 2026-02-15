import os, shutil
from django.conf import settings
from django.core.cache import cache

shutil.rmtree(os.path.join(settings.MEDIA_ROOT, 'cache'), ignore_errors=True)
cache.clear()

from apps.products.models import ProductImage
for img in ProductImage.objects.all():
    img.thumbnail.generate()
    img.medium.generate()
    print(f'Regenerated: {img.image.name}')
print('Done')
