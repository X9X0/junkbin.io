"""
Tests for the import_product_images management command and its review batch.
"""
import json
from io import BytesIO, StringIO

import pytest
from django.core.management import call_command
from PIL import Image
from rest_framework.test import APIClient

from apps.products.models import ProductImage

pytestmark = pytest.mark.django_db


def _png(color='black'):
    buf = BytesIO()
    Image.new('RGBA', (40, 40), color).save(buf, 'PNG')
    return buf.getvalue()


def _manifest(tmp_path, product, md5='a1', color='black', **item):
    folder = tmp_path / f'images_{md5}'
    (folder / 'images').mkdir(parents=True)
    (folder / 'images' / 'x.png').write_bytes(_png(color))
    entry = {'product': {'import_source': product.import_source, 'manufacturer': product.manufacturer,
                         'model_number': product.model_number},
             'file': 'images/x.png', 'md5': md5, 'source_url': 'https://shop.example/laptop',
             'image_url': 'https://shop.example/laptop.jpg', 'site': 'shop.example', 'title': 'A laptop',
             'match': 'exact', **item}
    (folder / 'manifest.json').write_text(json.dumps({'batch': 'image-search', 'images': [entry]}))
    return folder


def _run(*args):
    out = StringIO()
    call_command('import_product_images', *map(str, args), stdout=out)
    return out.getvalue()


@pytest.fixture
def setup(tmp_path, settings, user_factory, product_factory):
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    return product_factory(manufacturer='Dell', model_number='Latitude D820', import_source='norway-fw:DELL_D820',
                           is_approved=False)


def test_photo_added_unapproved_as_preview_with_its_source(tmp_path, setup):
    out = _run(_manifest(tmp_path, setup))
    assert 'added 1' in out
    img = ProductImage.objects.get()
    assert img.product == setup and img.is_primary and not img.is_approved and img.has_transparency
    assert img.source_url == 'https://shop.example/laptop'
    assert img.source_notes.startswith('[image-search] md5=a1') and 'shop.example' in img.source_notes
    assert img.caption == 'Dell Latitude D820'


def test_rerun_is_unchanged_and_a_new_pick_replaces_the_old(tmp_path, setup):
    _run(_manifest(tmp_path, setup))
    assert 'unchanged 1' in _run(tmp_path / 'images_a1')
    assert 'replaced 1' in _run(_manifest(tmp_path, setup, md5='b2', color='white'))
    img = ProductImage.objects.get()
    assert img.source_notes.startswith('[image-search] md5=b2') and img.is_primary


def test_approved_photo_and_members_uploads_are_left_alone(tmp_path, setup, user_factory):
    mine = ProductImage.objects.create(product=setup, image='products/own.png', is_primary=True, is_approved=True)
    _run(_manifest(tmp_path, setup))
    found = ProductImage.objects.exclude(pk=mine.pk).get()
    assert not found.is_primary                        # the product already had a preview
    found.is_approved = True
    found.save()
    assert 'unchanged 1' in _run(_manifest(tmp_path, setup, md5='b2'))
    assert ProductImage.objects.count() == 2


def test_family_photo_is_captioned_as_the_series(tmp_path, setup):
    _run(_manifest(tmp_path, setup, match='family', series='Latitude D800'))
    img = ProductImage.objects.get()
    assert img.caption == 'Dell Latitude D800 series' and 'not this exact model' in img.source_notes


def test_unknown_product_and_dry_run(tmp_path, setup, product_factory):
    other = product_factory(manufacturer='HP', model_number='Nope', import_source='')
    other.import_source = 'gone'
    folder = _manifest(tmp_path, other)
    other.delete()
    assert 'no product 1' in _run(folder)
    assert 'dry run' in _run(_manifest(tmp_path, setup, md5='c3'), '--dry-run')
    assert not ProductImage.objects.exists()


def test_review_batch_lists_and_approves_the_photos(tmp_path, setup, user_factory):
    _run(_manifest(tmp_path, setup))
    api = APIClient()
    api.force_authenticate(user_factory(is_staff=True))
    items = api.get('/api/import-review/next/', {'batch': 'image-search'}).data
    assert items[0]['item_type'] == 'image' and items[0]['documents'][0]['url'] == 'https://shop.example/laptop'
    api.post('/api/import-review/verdict/', {'batch': 'image-search', 'object_id': items[0]['id'],
                                             'verdict': 'correct'}, format='json')
    resp = api.post('/api/import-review/approve/', {'batch': 'image-search'}, format='json')
    assert resp.status_code == 200 and resp.data['images'] == 1
    assert ProductImage.objects.get().is_approved
