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
