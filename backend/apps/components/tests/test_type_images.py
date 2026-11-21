"""Default photos per type and package: imported unapproved into the type-image batch, shown only once approved."""
import io
import json

import pytest
from django.core.management import call_command
from PIL import Image

from apps.components.models import Component, ComponentTypeImage
from apps.products.import_review import BATCHES, approve_batch, evidence, items, next_items

pytestmark = pytest.mark.django_db


def _folder(tmp_path, entries):
    (tmp_path / 'images').mkdir(exist_ok=True)
    for e in entries:
        im = Image.new('RGBA', (64, 64), (200, 30, 30, 255))
        buf = io.BytesIO(); im.save(buf, 'PNG')
        (tmp_path / e['file']).write_bytes(buf.getvalue())
    (tmp_path / 'manifest.json').write_text(json.dumps({'images': entries}))
    return tmp_path


def test_import_waits_for_review_and_fallback_uses_approved_only(tmp_path, api_client):
    folder = _folder(tmp_path, [
        {'component_type': 'resistor', 'package_type': '1206', 'file': 'images/r1206.png',
         'source_url': 'https://commons.wikimedia.org/wiki/File:x.jpg', 'source_notes': 'CC BY-SA 4.0, photo by A (Wikimedia Commons)'},
        {'component_type': 'capacitor', 'package_type': '', 'file': 'images/cap.png', 'source_url': 'https://example.org/c', 'source_notes': 'CC0'},
    ])
    out = io.StringIO(); call_command('import_type_images', str(folder), stdout=out)
    assert 'created 2' in out.getvalue()
    row = ComponentTypeImage.objects.get(component_type='resistor', package_type='1206')
    assert not row.is_approved and row.source_notes.startswith('[type-image] md5=')
    assert list(BATCHES)[0] == 'type-image'                                   # first in the moderation list
    assert set(items('type-image').values_list('pk', flat=True)) == set(ComponentTypeImage.objects.values_list('pk', flat=True))
    ev = evidence('type-image', row)
    assert ev['item_type'] == 'type-image' and ev['component_type'] == 'resistor' and ev['image'] and ev['documents'][0]['url'].startswith('https://commons')
    assert len(next_items('type-image')) == 2
    part = Component.objects.create(manufacturer='Yageo', part_number='RC1206FR-0710KL', component_type='resistor', package_type='1206')
    r = api_client.get(f'/api/components/{part.pk}/')
    assert r.status_code == 200 and r.data.get('primary_image') is None             # unapproved default: not shown
    out = io.StringIO(); call_command('import_type_images', str(folder), stdout=out)
    assert 'unchanged 2' in out.getvalue()                                      # same files: nothing changes
    approve_batch('type-image', force=True)
    r = api_client.get(f'/api/components/{part.pk}/')
    assert r.data.get('primary_image') is not None
    out = io.StringIO(); call_command('import_type_images', str(folder), stdout=out)
    assert 'unchanged 2' in out.getvalue()
