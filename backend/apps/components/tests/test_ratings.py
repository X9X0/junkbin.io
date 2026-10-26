"""
Tests for Component.ratings and the rating filters on /api/components/.
"""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_ratings_text_and_sort_values(component_factory):
    cap = component_factory(component_type='capacitor', specifications={
        'capacitance_pf': 15.0, 'voltage_v': 50.0, 'tolerance': '5%', 'dielectric': 'C0G'})
    assert cap.ratings == {'value': {'text': '15 pF', 'sort': pytest.approx(15e-12)},
                           'voltage': {'text': '50 V', 'sort': 50.0},
                           'tolerance': {'text': '±5%', 'sort': 5.0},
                           'dielectric': {'text': 'C0G', 'sort': None}}
    res = component_factory(component_type='resistor', specifications={
        'resistance_ohm': 20000.0, 'power_w': 0.1, 'tolerance_pct': 1})
    assert res.ratings['power']['text'] == '1/10 W' and res.ratings['tolerance']['text'] == '±1%'
    ind = component_factory(component_type='inductor', specifications={'inductance_uh': 0.1, 'current_a': 0.3})
    assert ind.ratings['current'] == {'text': '300 mA', 'sort': 0.3}
    bead = component_factory(component_type='ferrite', specifications={'impedance_ohm': 600.0})
    assert bead.primary_value == '600 Ω'                              # no '@ ? MHz'
    ntc = component_factory(component_type='thermistor', specifications={'resistance_ohm': 10000.0})
    assert ntc.primary_value == '10 kΩ'
    xtal = component_factory(component_type='crystal', specifications={
        'frequency_mhz': 25.0, 'load_pf': 20.0, 'tolerance_ppm': 30})
    assert xtal.ratings['tolerance']['text'] == '±30 ppm' and xtal.ratings['load']['text'] == '20 pF'
    assert component_factory(specifications={}).ratings == {}


def _codes(**params):
    resp = APIClient().get('/api/components/', params)
    assert resp.status_code == 200
    return sorted(c['part_number'] for c in resp.data['results'])


def test_rating_filters(component_factory):
    component_factory(part_number='C16', component_type='capacitor',
                      specifications={'capacitance_pf': 100000.0, 'voltage_v': 16.0, 'tolerance': '10%',
                                      'dielectric': 'X7R'})
    component_factory(part_number='C50', component_type='capacitor',
                      specifications={'capacitance_pf': 15.0, 'voltage_v': 50, 'tolerance': '5%', 'dielectric': 'C0G'})
    component_factory(part_number='R10', component_type='resistor',
                      specifications={'resistance_ohm': 10000.0, 'power_w': 0.1, 'tolerance_pct': 5})
    component_factory(part_number='R25', component_type='resistor',
                      specifications={'resistance_ohm': 10000.0, 'power_w': 0.25, 'tolerance': '1%'})
    component_factory(part_number='L1', component_type='inductor', specifications={'inductance_uh': 1, 'current_a': 0.5})
    assert _codes(voltage_min='25V') == ['C50']
    assert _codes(voltage_min='16') == ['C16', 'C50']
    assert _codes(power_min='1/8W') == ['R25']
    assert _codes(power_min='100mW') == ['R10', 'R25']
    assert _codes(current_min='500mA') == ['L1']
    assert _codes(tolerance='5') == ['C50', 'R10']
    assert _codes(tolerance='±1%') == ['R25']
    assert _codes(dielectric='npo') == ['C50']
    assert _codes(value='10k', power_min='0.25W') == ['R25']
    assert _codes(voltage_min='fifty') == []                             # not a rating: nothing, not everything


def test_new_component_gets_ratings_from_its_description(user_factory):
    api = APIClient()
    api.force_authenticate(user_factory())
    resp = api.post('/api/components/', {
        'manufacturer': 'Murata', 'part_number': 'GRM188R71H104KA93D', 'component_type': 'capacitor',
        'description': 'MLCC 0.1UF/50V (0603) X7R 10%', 'specifications': {'capacitance_pf': 100000},
    }, format='json')
    assert resp.status_code == 201, resp.data
    from apps.components.models import Component
    comp = Component.objects.get(part_number='GRM188R71H104KA93D')
    assert comp.specifications == {'capacitance_pf': 100000, 'voltage_v': 50, 'tolerance': '10%', 'dielectric': 'X7R'}
    assert comp.package_type == '0603'
