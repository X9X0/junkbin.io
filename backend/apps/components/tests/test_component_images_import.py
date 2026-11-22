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


def test_a_corrected_rendering_replaces_an_approved_one_only_when_asked(tmp_path):
    part = Component.objects.create(manufacturer='Generic', part_number='CAP 100uF 25V ELEC', component_type='capacitor')
    folder = _folder(tmp_path, [{'component': {'manufacturer': 'Generic', 'part_number': 'CAP 100uF 25V ELEC'}, 'file': 'images/a.png',
                                 'caption': 'first', 'source_notes': 'rendered'}])
    call_command('import_component_images', str(folder), stdout=io.StringIO())
    ComponentImage.objects.filter(component=part).update(is_approved=True)
    (folder / 'images' / 'a.png').write_bytes((folder / 'images' / 'a.png').read_bytes() + b'\x00')     # a changed rendering
    out = io.StringIO(); call_command('import_component_images', str(folder), stdout=out)
    assert "kept (approved or a person's) 1" in out.getvalue() and ComponentImage.objects.get(component=part).caption == 'first'
    out = io.StringIO(); call_command('import_component_images', str(folder), '--replace-approved', stdout=out)
    assert 'replaced (approval kept) 1' in out.getvalue()
    img = ComponentImage.objects.get(component=part)
    assert img.is_approved and ComponentImage.objects.filter(component=part).count() == 1


def test_a_replaced_renderings_reviews_follow_it_and_its_flag_is_cleared(tmp_path, user_factory):
    from apps.products.models import ImportReview
    ok = Component.objects.create(manufacturer='Generic', part_number='CAP 330nF 50V', component_type='capacitor')
    bad = Component.objects.create(manufacturer='Generic', part_number='CAP 220nF 50V', component_type='capacitor')
    folder = _folder(tmp_path, [
        {'component': {'manufacturer': 'Generic', 'part_number': 'CAP 330nF 50V'}, 'file': 'images/a.png', 'caption': 'a', 'source_notes': 'rendered'},
        {'component': {'manufacturer': 'Generic', 'part_number': 'CAP 220nF 50V'}, 'file': 'images/b.png', 'caption': 'b', 'source_notes': 'rendered'},
    ])
    call_command('import_component_images', str(folder), stdout=io.StringIO())
    ComponentImage.objects.update(is_approved=True)
    who = user_factory()
    ImportReview.objects.create(batch='component-image', item_type='component-image', object_id=ComponentImage.objects.get(component=ok).pk, verdict='correct', reviewer=who)
    ImportReview.objects.create(batch='component-image', item_type='component-image', object_id=ComponentImage.objects.get(component=bad).pk, verdict='flagged', note='print off centre', reviewer=who)
    for name in ('a', 'b'):                                                                    # both renderings corrected
        (folder / 'images' / f'{name}.png').write_bytes((folder / 'images' / f'{name}.png').read_bytes() + b'\x00')
    out = io.StringIO(); call_command('import_component_images', str(folder), '--replace-approved', stdout=out)
    assert 'replaced (approval kept) 2' in out.getvalue() and 'reviews carried over 1' in out.getvalue() and 'flags cleared 1' in out.getvalue()
    assert ImportReview.objects.count() == 1
    assert ImportReview.objects.get().object_id == ComponentImage.objects.get(component=ok).pk               # the verdict names the new picture
    assert not ImportReview.objects.filter(verdict='flagged').exists()                                      # the corrected one waits for a fresh look
