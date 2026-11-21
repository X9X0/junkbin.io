"""import_component_images: renderings for individual parts wait in the component-image batch and never displace a person's photo."""
import io
import json

import pytest
from django.core.management import call_command
from PIL import Image

from apps.components.models import Component, ComponentImage
from apps.products.import_review import approve_batch, evidence, items

pytestmark = pytest.mark.django_db


def _folder(tmp_path, entries):
    (tmp_path / 'images').mkdir(exist_ok=True)
    for e in entries:
        buf = io.BytesIO(); Image.new('RGBA', (64, 64), (30, 30, 200, 255)).save(buf, 'PNG')
        (tmp_path / e['file']).write_bytes(buf.getvalue())
    (tmp_path / 'manifest.json').write_text(json.dumps({'images': entries}))
    return tmp_path


def test_renderings_are_imported_once_and_reviewed(tmp_path, api_client, user_factory):
    r1 = Component.objects.create(manufacturer='Generic', part_number='RES 470K 1/2W', component_type='resistor')
    r2 = Component.objects.create(manufacturer='Generic', part_number='RES 4.7K', component_type='resistor')
    owned = Component.objects.create(manufacturer='Generic', part_number='RES 100R', component_type='resistor')
    ComponentImage.objects.create(component=owned, image='components/own.png', is_approved=True, uploaded_by=user_factory())
    folder = _folder(tmp_path, [
        {'component': {'manufacturer': 'generic', 'part_number': 'res 470k 1/2w'}, 'file': 'images/a.png', 'caption': '470 kΩ 5 % colour code yellow, violet, yellow, gold', 'source_notes': 'rendered from the value'},
        {'component': {'manufacturer': 'Generic', 'part_number': 'RES 4.7K'}, 'file': 'images/b.png', 'caption': '4.7 kΩ', 'source_notes': 'rendered'},
        {'component': {'manufacturer': 'Generic', 'part_number': 'RES 100R'}, 'file': 'images/c.png', 'caption': '100 Ω', 'source_notes': 'rendered'},
        {'component': {'manufacturer': 'Generic', 'part_number': 'RES 999R'}, 'file': 'images/d.png', 'caption': 'x', 'source_notes': 'rendered'},
    ])
    out = io.StringIO(); call_command('import_component_images', str(folder), stdout=out)
    assert 'added 2' in out.getvalue() and "kept (approved or a person's) 1" in out.getvalue() and 'part not found 1' in out.getvalue()
    img = ComponentImage.objects.get(component=r1)
    assert not img.is_approved and img.source_notes.startswith('[component-image] md5=')
    assert items('component-image').count() == 2
    ev = evidence('component-image', img)
    assert ev['item_type'] == 'component-image' and ev['component_id'] == str(r1.pk) and 'yellow' in ev['description']
    r = api_client.get(f'/api/components/{r1.pk}/')
    assert r.status_code == 200 and r.data.get('primary_image') is None                  # unapproved: not shown
    approve_batch('component-image', force=True)
    r = api_client.get(f'/api/components/{r1.pk}/')
    assert r.data.get('primary_image') is not None
    out = io.StringIO(); call_command('import_component_images', str(folder), stdout=out)
    assert 'unchanged 2' in out.getvalue() and 'added 0' in out.getvalue()
