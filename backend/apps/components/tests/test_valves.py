"""
Valve substitutes: the curated table is consistent, the loader writes it both ways with
grades, and the component API lists a valve's stand-ins in order.
"""
from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.components import valves
from apps.components.models import Component, Substitute

pytestmark = pytest.mark.django_db


def test_the_table_is_consistent():
    assert valves.check() == []
    heads = valves.groups()
    assert heads['ECC83'] == '12AX7' and heads['7025'] == '12AX7' and heads['GZ34'] == '5AR4'


def _load(*args):
    out = StringIO()
    call_command('load_valve_substitutes', *args, stdout=out)
    return out.getvalue()


def test_loader_writes_same_both_ways_and_near_one_way(component_factory):
    el84 = component_factory(manufacturer='Generic', part_number='EL84', component_type='vacuum_tube')
    out = _load('--dry-run')
    assert 'DRY RUN' in out and Substitute.objects.count() == 0 and not Component.objects.filter(part_number='6BQ5').exists()

    out = _load()
    assert 'DRY RUN' not in out
    bq5 = Component.objects.get(manufacturer='Generic', part_number='6BQ5')
    assert bq5.component_type == 'vacuum_tube' and bq5.specifications['same_as'] == 'EL84'
    assert Substitute.objects.get(component=el84, substitute=bq5).grade == 'same'
    assert Substitute.objects.get(component=bq5, substitute=el84).grade == 'same'
    assert bq5 in el84.cross_references.all()
    s7189 = Component.objects.get(manufacturer='Generic', part_number='7189')
    assert Substitute.objects.get(component=el84, substitute=s7189).grade == 'near'
    assert Substitute.objects.get(component=s7189, substitute=el84).grade == 'check'
    el84.refresh_from_db()
    bq5.refresh_from_db()
    assert el84.specifications['made_today_by'] == bq5.specifications['made_today_by'] == valves.MADE_TODAY_BY['EL84']

    # a second run changes nothing
    before = Substitute.objects.count()
    out = _load()
    assert Substitute.objects.count() == before and 'substitutes written 0' in out


def test_component_api_lists_substitutes_by_grade_then_use(component_factory):
    _load()
    el84 = Component.objects.get(manufacturer='Generic', part_number='EL84')
    Component.objects.filter(part_number='6BQ5').update(usage_count=40)
    Component.objects.filter(part_number='N709').update(usage_count=3)
    resp = APIClient().get(f'/api/components/{el84.pk}/')
    assert resp.status_code == 200
    subs = resp.data['substitutes']
    grades = [s['grade'] for s in subs]
    assert grades == sorted(grades, key=Substitute.GRADE_ORDER.get)
    same = [s['part_number'] for s in subs if s['grade'] == 'same']
    assert same[:2] == ['6BQ5', 'N709']
    near = {s['part_number']: s for s in subs if s['grade'] == 'near'}
    assert '7189' in near and 'upgrade' in near['7189']['notes']
    assert resp.data['made_today_by'] == valves.MADE_TODAY_BY['EL84']
    assert resp.data['lookup_mode'] == 'not_stocked'


def test_valve_pages_list_specialist_dealers_and_other_parts_do_not(component_factory):
    tube = component_factory(manufacturer='Generic', part_number='EL34', component_type='vacuum_tube')
    res = component_factory(manufacturer='Generic', part_number='RES 10K', component_type='resistor')
    api = APIClient()
    dealers = api.get(f'/api/components/{tube.pk}/').data['dealers']
    assert dealers == valves.DEALERS and {'name', 'url', 'region'} <= set(dealers[0])
    assert all(d['url'].startswith('https://') for d in dealers)
    assert api.get(f'/api/components/{res.pk}/').data['dealers'] == []
