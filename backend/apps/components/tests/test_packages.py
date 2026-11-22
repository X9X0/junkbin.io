"""Chip sizes in both systems: stored as the EIA code, shown with the metric twin, found by either."""
import pytest
from rest_framework.test import APIClient

from apps.components.models import Component
from apps.components.packages import eia_for, metric_for, query_terms

pytestmark = pytest.mark.django_db


def test_metric_twin_of_an_eia_code():
    assert metric_for('0603') == '1608' and metric_for('01005') == '0402' and metric_for('4R8P 0603') == '1608'
    assert metric_for('SOT-23') == '' and metric_for('7343 (D case)') == '' and metric_for('') == ''
    assert eia_for('1608') == '0603' and eia_for('0402') == '01005' and eia_for('0603') == '0201'
    assert query_terms('1608') == ['1608', '0603'] and query_terms(' SOT-23 ') == ['SOT-23']
    assert query_terms('0603') == ['0603'] and query_terms('0402') == ['0402']     # spelled the same in both systems: the EIA size


def test_package_filter_and_field_speak_both_systems(user_factory):
    a = Component.objects.create(manufacturer='Yageo', part_number='RC0603FR-0710KL', component_type='resistor', package_type='0603')
    b = Component.objects.create(manufacturer='Murata', part_number='GRM155R71C104KA88D', component_type='capacitor', package_type='0402')
    c = Component.objects.create(manufacturer='Generic', part_number='RES ARRAY 10K 4R8P 0603', component_type='resistor', package_type='4R8P 0603')
    client = APIClient()
    ids = lambda r: {x['part_number'] for x in r.json()['results']}
    assert ids(client.get('/api/components/', {'package_type': '1608'})) == {a.part_number, c.part_number}
    assert ids(client.get('/api/components/', {'package_type': '0603'})) == {a.part_number, c.part_number}
    assert ids(client.get('/api/components/', {'package_type': '1005'})) == {b.part_number}
    row = next(x for x in client.get('/api/components/', {'package_type': '0402'}).json()['results'] if x['part_number'] == b.part_number)
    assert row['package_metric'] == '1005'
    assert client.get(f'/api/components/{a.pk}/').json()['package_metric'] == '1608'
