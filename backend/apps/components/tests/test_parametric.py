"""
Tests for the equivalent-part search generic lines get instead of an exact lookup.
"""
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.components import parametric
from apps.components.models import Component, ExternalPartSearch

pytestmark = pytest.mark.django_db


def _generic(part_number, component_type, specs, package=''):
    return Component.objects.create(part_number=part_number, manufacturer='Generic',
                                    component_type=component_type, specifications=specs, package_type=package)


def _hit(mpn, description, stock=10, status='Active', maker='Vishay'):
    return {'source': 'digikey', 'mpn': mpn, 'manufacturer': maker, 'description': description,
            'category': '', 'datasheet_url': None, 'product_url': '', 'status': status, 'stock': stock,
            'specs': [], 'sellers': [{'name': 'DigiKey', 'url': '', 'offers': [{'stock': stock, 'price': 0.1,
                                                                               'currency': 'USD', 'qty_min': 1, 'buy_url': ''}]}]}


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def test_mode_picks_the_lookup():
    assert parametric.mode(_generic('CAP 10nF 200V', 'capacitor', {'capacitance_pf': 10000, 'voltage_v': 200})) == 'equivalents'
    assert parametric.mode(_generic('12AX7', 'vacuum_tube', {})) == 'not_stocked'
    assert parametric.mode(_generic('ZENER8', 'diode', {})) == 'exact'          # nothing to search by
    named = Component.objects.create(part_number='LM358DR', manufacturer='Texas Instruments', component_type='opamp')
    assert parametric.mode(named) == 'exact'


def test_query_text_reads_like_a_distributor_description():
    assert parametric.query_for(_generic('RES 10K 5% 1/4W', 'resistor',
                                         {'resistance_ohm': 10000, 'tolerance': '5%', 'power_w': 0.25})) == 'RES 10K OHM 5% 1/4W'
    assert parametric.query_for(_generic('CAP 20uF 250V ELEC', 'capacitor',
                                         {'capacitance_pf': 2e7, 'voltage_v': 250, 'dielectric': 'electrolytic'})) == 'CAP 20UF 250V ALUM'
    assert parametric.query_for(_generic('RES 4.87K 1% 1/16W 0603', 'resistor',
                                         {'resistance_ohm': 4870, 'tolerance': '1%', 'power_w': 0.0625}, '0603')) == 'RES 4.87K OHM 1% 1/16W 0603'
    assert parametric.query_for(_generic('FUSE T4A', 'fuse', {'current_a': 4, 'speed': 'slow'})) == 'FUSE 4A SLOW BLOW'
    assert parametric.query_for(_generic('POT 600K', 'potentiometer', {'resistance_ohm': 600000})) == 'POT 600K OHM'


def test_rank_keeps_fits_and_drops_under_rated_or_wrong_parts():
    cap = _generic('CAP 10nF 200V', 'capacitor', {'capacitance_pf': 10000, 'voltage_v': 200, 'dielectric': 'film'})
    hits = [
        _hit('A', 'CAP CER 10000PF 100V X7R 0805'),                  # 100 V under a 200 V line: dropped
        _hit('B', 'CAP CER 0.022UF 250V X7R RADIAL'),                 # wrong value: dropped
        _hit('C', 'CAP CER 0.01UF 250V X7R RADIAL', stock=0),         # fits, out of stock
        _hit('D', 'CAP FILM 0.01UF 10% 630VDC RADIAL', stock=500),    # fits, film, in stock: best
        _hit('E', 'RES 10K OHM 1% 1/4W 0603'),                        # a resistor: dropped
        _hit('D2', 'CAP FILM 0.01UF 10% 630VDC RADIAL', stock=20),     # a packaging variant of D: folded into it
    ]
    ranked = parametric.rank(hits, cap)
    assert [h['mpn'] for h in ranked] == ['D', 'C']
    assert ranked[0]['fit']['value'] == 'match'
    assert '630 V (needs 200)' in ranked[0]['fit']['notes']
    assert ranked[0]['sources'] == ['digikey'] and 'source' not in ranked[0]


def test_rank_resistor_power_and_tolerance():
    res = _generic('RES 100R 2W', 'resistor', {'resistance_ohm': 100, 'power_w': 2, 'tolerance': '5%'})
    ranked = parametric.rank([
        _hit('LOW', 'RES 100 OHM 5% 1/4W AXIAL'),                     # 1/4 W for a 2 W line: dropped
        _hit('WIDE', 'RES 100 OHM 10% 2W AXIAL'),                     # wider tolerance: kept, ranked lower
        _hit('OK', 'RES 100 OHM 1% 3W AXIAL'),
        _hit('OLD', 'RES 100 OHM 5% 2W AXIAL', status='Obsolete'),
        _hit('NEAR', 'RES 100 OHM 5% 2.02W AXIAL', maker='Yageo'),       # within 2%: no "needs" note
    ], res)
    assert [h['mpn'] for h in ranked] == ['OK', 'NEAR', 'WIDE', 'OLD']
    assert ranked[0]['fit']['notes'] == ['3 W (needs 2)']
    assert ranked[1]['fit']['notes'] == []
    assert '±10% (wants ±5%)' in ranked[2]['fit']['notes']


def test_search_asks_digikey_once_and_caches_by_query():
    a = _generic('CAP 10nF', 'capacitor', {'capacitance_pf': 10000})
    b = _generic('CAP 10nF 200V', 'capacitor', {'capacitance_pf': 10000})       # same query text
    dk = MagicMock(is_configured=True, remaining=900)
    with patch('apps.components.parametric.get_digikey', return_value=dk), \
            patch('apps.components.parametric.digikey_keyword', return_value=[_hit('X', 'CAP CER 0.01UF 50V X7R 0805')]) as call:
        results, cached = parametric.search(a)
        assert not cached and [r['mpn'] for r in results] == ['X']
        again, cached = parametric.search(b)
        assert cached and again == results
        assert call.call_count == 1
    row = ExternalPartSearch.objects.get(query='CAP 10NF')
    assert row.sources == ['digikey', 'parametric'] and row.search_count == 2


def test_search_unavailable_when_digikey_reserve_is_spent():
    cache.set('digikey_remaining', 10)
    dk = MagicMock(is_configured=True, remaining=10)
    with patch('apps.components.parametric.get_digikey', return_value=dk), pytest.raises(parametric.SearchUnavailable):
        parametric.search(_generic('CAP 10nF', 'capacitor', {'capacitance_pf': 10000}))


def test_lookup_endpoint_answers_by_mode(user_factory):
    client = APIClient()
    client.force_authenticate(user_factory())
    tube = _generic('12AX7', 'vacuum_tube', {})
    resp = client.post(f'/api/components/{tube.id}/lookup/')
    assert resp.status_code == 404 and 'not stocked' in resp.data['detail']

    cap = _generic('CAP 10nF 200V', 'capacitor', {'capacitance_pf': 10000, 'voltage_v': 200})
    with patch('apps.components.parametric.search', return_value=([{'mpn': 'X', 'manufacturer': 'Kemet', 'fit': {'score': 4, 'notes': [], 'value': 'match'}}], False)):
        resp = client.post(f'/api/components/{cap.id}/lookup/')
    assert resp.status_code == 200
    assert resp.data['query'] == 'CAP 10NF 200V' and resp.data['candidates'][0]['mpn'] == 'X'
    cap.refresh_from_db()
    assert cap.specifications['equivalent_parts']['candidates'][0]['manufacturer'] == 'Kemet'
    assert cap.specifications['capacitance_pf'] == 10000                       # ratings untouched

    detail = client.get(f'/api/components/{cap.id}/')
    assert detail.data['lookup_mode'] == 'equivalents'
    assert detail.data['equivalent_parts']['candidates'][0]['mpn'] == 'X'
    assert client.get(f'/api/components/{tube.id}/').data['lookup_mode'] == 'not_stocked'

    with patch('apps.components.parametric.search', side_effect=parametric.SearchUnavailable('budget')):
        assert client.post(f'/api/components/{cap.id}/lookup/').status_code == 503
