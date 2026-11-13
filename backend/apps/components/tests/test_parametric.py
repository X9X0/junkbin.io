"""
Tests for the equivalent-part search generic lines get instead of an exact lookup.
"""
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.utils import timezone
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


CERAMIC_FILTERS = [
    {'ParameterId': 2049, 'ParameterName': 'Capacitance', 'FilterValues': [
        {'ValueId': '4.7 pF', 'ValueName': '4.7 pF'}, {'ValueId': '5 pF', 'ValueName': '5 pF'}, {'ValueId': '15 pF', 'ValueName': '15 pF'}]},
    {'ParameterId': 14, 'ParameterName': 'Voltage - Rated', 'FilterValues': [
        {'ValueId': '25v', 'ValueName': '25V'}, {'ValueId': '50v', 'ValueName': '50V'}, {'ValueId': '250v', 'ValueName': '250V'},
        {'ValueId': '250vac', 'ValueName': '250VAC'}]},
    {'ParameterId': 16, 'ParameterName': 'Package / Case', 'FilterValues': [
        {'ValueId': '0201', 'ValueName': '0201 (0603 Metric)'}, {'ValueId': '0603', 'ValueName': '0603 (1608 Metric)'}]},
    {'ParameterId': 17, 'ParameterName': 'Temperature Coefficient', 'FilterValues': [
        {'ValueId': 'c0g', 'ValueName': 'C0G, NP0'}, {'ValueId': 'c0g1b', 'ValueName': 'C0G, NP0 (1B)'}, {'ValueId': 'x7r', 'ValueName': 'X7R'}]},
    {'ParameterId': 3, 'ParameterName': 'Tolerance', 'FilterValues': [{'ValueId': 't', 'ValueName': '±5%'}]},
]


def _digikey(filters, products):
    """A DigiKey client whose keyword search answers the filter-options call with `filters`
    and the filtered call with `products` (site-shaped hits; _parse_part passes them through)."""
    dk = MagicMock(is_configured=True, remaining=900)
    dk._parse_part.side_effect = lambda p: p
    dk.calls = []

    def answer(client, body):
        dk.calls.append(body)
        request = body.get('FilterOptionsRequest') or {}
        if 'CategoryFilter' in request:
            return {'Products': [], 'FilterOptions': {'ParametricFilters': filters}}
        if 'ParameterFilterRequest' in request:
            return {'Products': products}
        return {'Products': [{'Category': {'CategoryId': 3, 'ChildCategories': [{'CategoryId': 60, 'ChildCategories': []}]}}]}
    return dk, answer


def test_search_filters_by_the_category_parameters_digikey_offers():
    """"5 pF" is asked for with DigiKey's own filter ids (value, voltage at least 50 V, the
    0603 package - not '0201 (0603 Metric)' - and the C0G temperature coefficient), so
    the keyword ranking cannot bury the right value under other 0603 C0G parts."""
    c = _generic('CAP 5pF 50V C0G ±0.25pF 0603', 'capacitor',
                 {'capacitance_pf': 5, 'voltage_v': 50, 'dielectric': 'C0G', 'tolerance': '±0.25pF'}, package='0603')
    dk, answer = _digikey(CERAMIC_FILTERS, [_hit('C1608NP0509CGTS', '5 pF ±0.25pF 50V Ceramic Capacitor C0G, NP0 0603 (1608 Metric)', maker='Darfon')])
    with patch('apps.components.parametric.get_digikey', return_value=dk), \
            patch('apps.components.parametric.digikey_search', side_effect=answer):
        results, cached = parametric.search(c)
    assert [r['mpn'] for r in results] == ['C1608NP0509CGTS'] and results[0]['fit']['value'] == 'match'
    assert len(dk.calls) == 2                                   # known category: options + filtered search
    assert dk.calls[0]['FilterOptionsRequest'] == {'CategoryFilter': [{'Id': '60'}]}
    request = dk.calls[1]['FilterOptionsRequest']['ParameterFilterRequest']
    assert request['CategoryFilter'] == {'Id': '60'}
    chosen = {f['ParameterId']: [v['Id'] for v in f['FilterValues']] for f in request['ParameterFilters']}
    assert chosen == {2049: ['5 pF'], 14: ['50v', '250v'], 16: ['0603'], 17: ['c0g', 'c0g1b']}
    assert ExternalPartSearch.objects.get(query='CAP 5PF 50V C0G 0603').sources == ['digikey', 'parametric', 'filtered']


def test_search_stops_after_one_call_when_digikey_has_no_part_of_that_value():
    c = _generic('CAP 5.3pF 50V 0603', 'capacitor', {'capacitance_pf': 5.3, 'voltage_v': 50}, package='0603')
    dk, answer = _digikey(CERAMIC_FILTERS, [_hit('NEVER', 'nothing')])
    with patch('apps.components.parametric.get_digikey', return_value=dk), \
            patch('apps.components.parametric.digikey_search', side_effect=answer):
        results, _ = parametric.search(c)
    assert results == [] and len(dk.calls) == 1


def test_search_asks_for_the_category_when_the_line_does_not_tell_it():
    """A capacitor with no dielectric and no chip size could be in any capacitor category:
    the top keyword hit's category is used (one extra call)."""
    c = _generic('CAP 5pF 50V', 'capacitor', {'capacitance_pf': 5, 'voltage_v': 50})
    assert parametric.category_for(c) is None
    dk, answer = _digikey(CERAMIC_FILTERS, [_hit('X', '5 pF 50V Ceramic Capacitor C0G, NP0 0603 (1608 Metric)')])
    with patch('apps.components.parametric.get_digikey', return_value=dk), \
            patch('apps.components.parametric.digikey_search', side_effect=answer):
        results, _ = parametric.search(c)
    assert [r['mpn'] for r in results] == ['X'] and len(dk.calls) == 3
    assert dk.calls[1]['FilterOptionsRequest'] == {'CategoryFilter': [{'Id': '60'}]}


def test_category_for_reads_dielectric_and_mounting():
    assert parametric.category_for(_generic('a', 'capacitor', {'capacitance_pf': 1, 'dielectric': 'X7R'})) == 60
    assert parametric.category_for(_generic('b', 'capacitor', {'capacitance_pf': 1, 'dielectric': 'electrolytic'})) == 58
    assert parametric.category_for(_generic('c', 'capacitor', {'capacitance_pf': 1}, package='0402')) == 60
    assert parametric.category_for(_generic('d', 'resistor', {'resistance_ohm': 1}, package='0603')) == 52
    assert parametric.category_for(_generic('e', 'resistor', {'resistance_ohm': 1}, package='Axial')) == 53
    assert parametric.category_for(_generic('f', 'resistor', {'resistance_ohm': 1})) is None
    assert parametric.category_for(_generic('g', 'inductor', {'inductance_uh': 1})) == 71
    assert parametric.category_for(_generic('h', 'crystal', {'frequency_mhz': 1})) is None


def test_choose_filters_reads_resistor_values_power_and_package():
    r = _generic('RES 4.7K 1% 1/4W 1206', 'resistor', {'resistance_ohm': 4700, 'tolerance': '1%', 'power_w': 0.25}, package='1206')
    filters = [
        {'ParameterId': 2085, 'ParameterName': 'Resistance', 'FilterValues': [
            {'ValueId': 'a', 'ValueName': '4.7 kOhms'}, {'ValueId': 'b', 'ValueName': '47 kOhms'}, {'ValueId': 'c', 'ValueName': '4.75 kOhms'}]},
        {'ParameterId': 2, 'ParameterName': 'Power (Watts)', 'FilterValues': [
            {'ValueId': 'p1', 'ValueName': '0.1W, 1/10W'}, {'ValueId': 'p2', 'ValueName': '0.25W, 1/4W'}, {'ValueId': 'p3', 'ValueName': '0.5W, 1/2W'}]},
        {'ParameterId': 16, 'ParameterName': 'Package / Case', 'FilterValues': [
            {'ValueId': 's1', 'ValueName': '1206 (3216 Metric)'}, {'ValueId': 's2', 'ValueName': '0603 (1608 Metric)'}]},
    ]
    chosen = {f['ParameterId']: [v['Id'] for v in f['FilterValues']] for f in parametric.choose_filters(r, filters)}
    assert chosen == {2085: ['a', 'c'], 2: ['p2', 'p3'], 16: ['s1']}       # 4.75 k is within the 2% E-series slack
    # a category whose filters carry no value parameter cannot be narrowed
    assert parametric.choose_filters(r, filters[1:]) is None


def test_search_refetches_rows_the_keyword_only_search_left():
    """Rows cached before the filtered search carry sources without 'filtered' and often
    nothing of the right value; they are asked again, and the new row replaces them."""
    c = _generic('CAP 5pF 50V C0G 0603', 'capacitor', {'capacitance_pf': 5, 'voltage_v': 50, 'dielectric': 'C0G'}, package='0603')
    ExternalPartSearch.objects.create(query='CAP 5PF 50V C0G 0603', results=[], sources=['digikey', 'parametric'], search_count=4,
                                      fetched_at=timezone.now())
    dk, answer = _digikey(CERAMIC_FILTERS, [_hit('X', '5 pF ±0.25pF 50V Ceramic Capacitor C0G, NP0 0603 (1608 Metric)')])
    with patch('apps.components.parametric.get_digikey', return_value=dk), \
            patch('apps.components.parametric.digikey_search', side_effect=answer):
        results, cached = parametric.search(c)
        assert not cached and [r['mpn'] for r in results] == ['X']
        again, cached = parametric.search(c)
        assert cached and again == results
    row = ExternalPartSearch.objects.get(query='CAP 5PF 50V C0G 0603')
    assert row.sources == ['digikey', 'parametric', 'filtered'] and row.search_count == 6 and len(dk.calls) == 2


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


def test_exact_queries_find_the_part_number_inside_a_bom_line_name():
    flash = _generic('FLASH MXIC MX25L8005PC-15G 8M SPI PDIP-8', 'eeprom', {})
    assert parametric.exact_queries(flash) == [('MX25L8005PC-15G', 'Macronix')]
    ram = _generic('2M*32-7 MICRON TSOP SDRAM MT48LC2M32B2TG-7 (HP)', 'ic', {})
    assert parametric.exact_queries(ram) == [('MT48LC2M32B2TG-7', None)]           # SDRAM is not a maker
    con = _generic('HEADER 2X5P R/A,2.54mm,K8,G/F PINREX/211-82-05GY09,YELLOW', 'connector', {})
    assert parametric.exact_queries(con)[0] == ('211-82-05GY09', 'Pinrex')          # MAKER/PART
    assert parametric.exact_queries(_generic('2N3904', 'transistor', {})) == [('2N3904', None)]
    assert parametric.exact_queries(_generic('TRANSISTOR 2N3904 TO-92', 'transistor', {})) == [('2N3904', None)]
    named = Component.objects.create(part_number='LM358DR', manufacturer='Texas Instruments', component_type='opamp')
    assert parametric.exact_queries(named) == [('LM358DR', 'Texas Instruments')]


def test_lookup_endpoint_asks_for_the_embedded_part_number_without_a_generic_maker_filter(user_factory):
    client = APIClient()
    client.force_authenticate(user_factory())
    flash = _generic('FLASH MXIC MX25L8005PC-15G 8M SPI PDIP-8', 'eeprom', {})
    answer = {'mpn': 'MX25L8005PC-15G', 'manufacturer': 'Macronix', 'sellers': [], 'sources': ['digikey']}
    with patch('apps.components.lookup.lookup_part', return_value=answer) as call:
        resp = client.post(f'/api/components/{flash.id}/lookup/')
    assert resp.status_code == 200, resp.data
    assert call.call_args.args == ('MX25L8005PC-15G', None)
    flash.refresh_from_db()
    assert flash.specifications['nexar_data']['looked_up'] == {'part_number': 'MX25L8005PC-15G', 'manufacturer': 'Macronix'}

    with patch('apps.components.lookup.lookup_part', return_value=None), \
            patch('apps.components.parametric.family_search', return_value=([], 'MX25L8005PC', False)):
        resp = client.post(f'/api/components/{flash.id}/lookup/')
    assert resp.status_code == 404 and 'MX25L8005PC-15G' in resp.data['detail']


def test_family_search_tries_shorter_stems_and_keeps_the_family():
    dk = MagicMock(is_configured=True, remaining=900)
    answers = {'MX25L8005PC': [], 'MX25L8005': [], 'MX25L800': [_hit('MX25L8006EM1I-12G', 'IC FLASH 8MBIT SPI 86MHZ 8SOP', status='Not For New Designs', maker='Macronix'),
                                                           _hit('MX25L8006EM1J-12G', 'IC FLASH 8MBIT SPI 86MHZ 8SOP', stock=781, maker='Macronix'),
                                                           _hit('W25Q80DVSNIG', 'IC FLASH 8MBIT SPI 104MHZ 8SOIC', maker='Winbond')]}
    with patch('apps.components.parametric.get_digikey', return_value=dk), \
            patch('apps.components.parametric.digikey_keyword', side_effect=lambda c, q, limit: answers[q]) as call:
        results, stem, cached = parametric.family_search('MX25L8005PC-15G')
        assert stem == 'MX25L800' and not cached and call.call_count == 3
        assert [r['mpn'] for r in results] == ['MX25L8006EM1J-12G', 'MX25L8006EM1I-12G']   # Winbond: not the family
        assert results[0]['fit'] == {'score': 3, 'notes': [], 'value': 'family'}
        assert results[1]['fit']['notes'] == ['Not For New Designs']
        again = parametric.family_search('MX25L8005PC-15G')
        assert again[2] and again[1] == 'MX25L800' and call.call_count == 3                  # cached by stem


def test_family_search_gives_up_after_five_stems():
    dk = MagicMock(is_configured=True, remaining=900)
    with patch('apps.components.parametric.get_digikey', return_value=dk), \
            patch('apps.components.parametric.digikey_keyword', return_value=[]) as call:
        assert parametric.family_search('MX25L8005PC-15G') == ([], 'MX25L8005PC', False)
        assert call.call_count == 5


def test_lookup_endpoint_falls_back_to_the_family_when_the_number_is_gone(user_factory):
    client = APIClient()
    client.force_authenticate(user_factory())
    flash = _generic('FLASH MXIC MX25L8005PC-15G 8M SPI PDIP-8', 'eeprom', {})
    family = [{'mpn': 'MX25L8006EM1J-12G', 'manufacturer': 'Macronix', 'fit': {'score': 3, 'notes': [], 'value': 'family'}}]
    with patch('apps.components.lookup.lookup_part', return_value=None), \
            patch('apps.components.parametric.family_search', return_value=(family, 'MX25L800', False)):
        resp = client.post(f'/api/components/{flash.id}/lookup/')
    assert resp.status_code == 200 and resp.data['family_of'] == 'MX25L8005PC-15G' and resp.data['query'] == 'MX25L800'
    detail = client.get(f'/api/components/{flash.id}/').data
    assert detail['lookup_mode'] == 'exact' and detail['equivalent_parts']['candidates'][0]['mpn'] == 'MX25L8006EM1J-12G'
