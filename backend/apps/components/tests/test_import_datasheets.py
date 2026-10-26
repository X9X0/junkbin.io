"""
Tests for the import_datasheets management command.
"""
import hashlib
import json
from io import StringIO

import pytest
from django.core.management import call_command

from apps.components.models import ComponentDatasheet

pytestmark = pytest.mark.django_db


def _export(tmp_path, component, content=b'%PDF-1.4 fake'):
    (tmp_path / 'files').mkdir()
    (tmp_path / 'files' / '123.pdf').write_bytes(content)
    (tmp_path / 'matches.json').write_text(json.dumps({'version': 1, 'source_tag': 'norway-ds', 'matches': [{
        'manufacturer': component.manufacturer.upper(), 'part_number': component.part_number.lower(),
        'file': 'files/123.pdf', 'md5': hashlib.md5(content).hexdigest(), 'title': 'LM358 datasheet',
        'source_notes': 'letus.repair collection: x.pdf'}]}))
    return tmp_path


def _run(*args):
    out = StringIO()
    call_command('import_datasheets', *map(str, args), stdout=out)
    return out.getvalue()


def test_attaches_once_unapproved(tmp_path, settings, component_factory, user_factory):
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    comp = component_factory()
    (tmp_path / 'x').mkdir()
    folder = _export(tmp_path / 'x', comp)
    assert 'attached 1' in _run(folder)
    ds = ComponentDatasheet.objects.get()
    assert ds.component == comp and not ds.is_approved and ds.source_type == 'mirror'
    assert 'already attached 1' in _run(folder)
    assert ComponentDatasheet.objects.count() == 1


def test_dry_run_and_missing_component(tmp_path, settings, component_factory, user_factory):
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    comp = component_factory()
    (tmp_path / 'x').mkdir()
    folder = _export(tmp_path / 'x', comp)
    assert 'DRY RUN' in _run(folder, '--dry-run')
    assert not ComponentDatasheet.objects.exists()
    comp.delete()
    assert 'component missing 1' in _run(folder)


def test_creates_missing_component_when_asked(tmp_path, settings, user_factory):
    from apps.components.models import Component
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    content = b'%PDF-1.4 new part'
    (tmp_path / 'files').mkdir()
    (tmp_path / 'files' / '9.pdf').write_bytes(content)
    (tmp_path / 'matches.json').write_text(json.dumps({'version': 1, 'source_tag': 'norway-ds-new', 'matches': [{
        'manufacturer': 'Sanyo', 'part_number': '2SC3042', 'file': 'files/9.pdf',
        'md5': hashlib.md5(content).hexdigest(), 'title': '2SC3042', 'source_notes': 'x',
        'create': {'component_type': 'transistor', 'description': 'NPN Triple Diffused Planar Silicon Transistor'}}]}))
    assert 'components created 1' in _run(tmp_path)
    comp = Component.objects.get(part_number='2SC3042')
    assert comp.component_type == 'transistor' and not comp.is_verified
    assert comp.specifications == {'source': 'datasheet'}
    assert comp.datasheets.count() == 1
    assert 'already attached 1' in _run(tmp_path)          # re-run: nothing new
    assert Component.objects.filter(part_number='2SC3042').count() == 1


def test_new_component_is_typed_by_function_not_keyword(tmp_path, settings, user_factory):
    from apps.components.models import Component
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    user_factory(is_superuser=True, is_staff=True)
    content = b'%PDF-1.4 driver'
    (tmp_path / 'files').mkdir()
    (tmp_path / 'files' / '7.pdf').write_bytes(content)
    (tmp_path / 'matches.json').write_text(json.dumps({'version': 1, 'source_tag': 'norway-ds-new', 'matches': [{
        'manufacturer': 'Intersil', 'part_number': 'ISL6612', 'file': 'files/7.pdf',
        'md5': hashlib.md5(content).hexdigest(), 'title': 'ISL6612', 'source_notes': 'x',
        'create': {'component_type': 'mosfet',
                   'description': 'ISL6612 Advanced Synchronous Rectified Buck MOSFET Driver Features'}}]}))
    _run(tmp_path)
    comp = Component.objects.get(part_number='ISL6612')
    assert comp.component_type == 'ic'
    assert comp.description == 'Advanced Synchronous Rectified Buck MOSFET Driver'
