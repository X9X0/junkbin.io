"""
Tests for manage.py drop_cross_references.
"""
import json
from io import StringIO

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_listed_pairs_are_removed_both_ways_and_others_kept(tmp_path, component_factory):
    res = component_factory(manufacturer='TA-I', part_number='RM06FTN4992')
    good = component_factory(manufacturer='YAGEO', part_number='RC0603FR-0749K9L')
    wrong = component_factory(manufacturer='Murata', part_number='GRM155R60J105KE19')
    res.cross_references.add(good, wrong)
    path = tmp_path / 'pairs.json'
    path.write_text(json.dumps([[['ta-i', 'rm06ftn4992'], ['MURATA', 'GRM155R60J105KE19']],
                                [['NOBODY', 'X1'], ['TA-I', 'RM06FTN4992']]]))
    out = StringIO()
    call_command('drop_cross_references', str(path), stdout=out)
    assert list(res.cross_references.all()) == [good]
    assert list(wrong.cross_references.all()) == []
    assert '1 between existing components, 1 not on the site' in out.getvalue()


def test_dry_run_keeps_everything(tmp_path, component_factory):
    a = component_factory(manufacturer='A', part_number='1')
    b = component_factory(manufacturer='B', part_number='2')
    a.cross_references.add(b)
    path = tmp_path / 'pairs.json'
    path.write_text(json.dumps([[['A', '1'], ['B', '2']]]))
    call_command('drop_cross_references', str(path), '--dry-run', stdout=StringIO())
    assert list(a.cross_references.all()) == [b]
