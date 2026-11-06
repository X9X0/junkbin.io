"""
'Newest first' lists products and parts with an approved photo before those without one,
without hiding anything; /products/recent/ only lists products with a photo.
"""
import io
from datetime import timedelta

from PIL import Image
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.components.models import Component, ComponentImage


def _aged(obj, days):
    type(obj).objects.filter(pk=obj.pk).update(created_at=timezone.now() - timedelta(days=days))


def _png():
    buf = io.BytesIO()
    Image.new('RGB', (8, 8), 'red').save(buf, 'PNG')
    return SimpleUploadedFile('part.png', buf.getvalue(), content_type='image/png')


def _names(resp):
    return [r.get('model_number') or r.get('part_number') for r in resp.data['results']]


def test_newest_first_lists_products_with_photos_first(product_factory, product_image_factory):
    cache.clear()
    old_photo = product_factory(model_number='OLD-PHOTO', is_approved=True)
    product_image_factory(product=old_photo, is_approved=True)
    _aged(old_photo, 30)
    pending_photo = product_factory(model_number='PENDING-PHOTO', is_approved=True)
    product_image_factory(product=pending_photo, is_approved=False)       # not approved yet: no photo
    _aged(pending_photo, 20)
    product_factory(model_number='NEW-BARE', is_approved=True)
    api = APIClient()

    for url in ('/api/products/', '/api/products/?ordering=-created_at'):   # the default sort is newest first
        resp = api.get(url)
        assert _names(resp) == ['OLD-PHOTO', 'NEW-BARE', 'PENDING-PHOTO']
        assert resp.data['count'] == 3                                      # nothing hidden
    assert _names(api.get('/api/products/?ordering=created_at')) == ['OLD-PHOTO', 'PENDING-PHOTO', 'NEW-BARE']


def test_recent_products_have_a_photo(product_factory, product_image_factory):
    cache.clear()
    with_photo = product_factory(model_number='WITH-PHOTO', is_approved=True)
    product_image_factory(product=with_photo, is_approved=True)
    product_factory(model_number='BARE', is_approved=True)
    assert [p['model_number'] for p in APIClient().get('/api/products/recent/').data] == ['WITH-PHOTO']


def test_newest_first_lists_parts_with_photos_first():
    cache.clear()
    old = Component.objects.create(manufacturer='TI', part_number='OLD-PHOTO', component_type='ic')
    ComponentImage.objects.create(component=old, image=_png(), is_approved=True)
    _aged(old, 30)
    Component.objects.create(manufacturer='TI', part_number='NEW-BARE', component_type='ic')
    resp = APIClient().get('/api/components/?ordering=-created_at')
    assert _names(resp) == ['OLD-PHOTO', 'NEW-BARE']
