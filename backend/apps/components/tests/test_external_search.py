"""
Tests for distributor search of part numbers the catalogue doesn't have.
"""
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.components import external_search
from apps.components.models import Component, ExternalPartSearch

pytestmark = pytest.mark.django_db


def _part(mpn, maker='Texas Instruments', source='digikey', stock=10):
    return {'source': source, 'mpn': mpn, 'manufacturer': maker, 'description': 'Buck regulator',
            'category': 'PMIC - Voltage Regulators', 'datasheet_url': 'https://example.com/ds.pdf',
            'status': 'Active', 'stock': stock, 'specs': [{'name': 'Voltage', 'value': '28V'}],
            'sellers': [{'name': source, 'url': '', 'offers': [{'stock': stock, 'price': 1.0, 'currency': 'USD',
                                                                 'qty_min': 1, 'buy_url': ''}]}]}


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def _patch(dk_results=(), mo_results=(), dk_configured=True, mo_configured=True):
    dk = MagicMock(is_configured=dk_configured, remaining=900)
    mo = MagicMock(is_configured=mo_configured)
    return (patch('apps.components.external_search.get_digikey', return_value=dk),
            patch('apps.components.external_search.get_mouser', return_value=mo),
            patch('apps.components.external_search.digikey_keyword', return_value=list(dk_results)),
            patch('apps.components.external_search.mouser_begins_with', return_value=list(mo_results)))


def test_part_number_shape():
    assert external_search.looks_like_part_number('TPS54331DR')
    assert external_search.looks_like_part_number('lm358 dr')          # spaces are dropped
    assert not external_search.looks_like_part_number('resistor')
    assert not external_search.looks_like_part_number('10k')
    assert not external_search.looks_like_part_number('<script>1')


def test_search_merges_ranks_and_caches():
    a, b, c, d = _patch(dk_results=[_part('TPS54331DRG4', stock=0), _part('TPS54331DR', stock=5)],
                        mo_results=[_part('TPS54331DR', source='mouser', stock=100)])
    with a, b, c as dk_call, d:
        results, cached = external_search.search('tps54331dr')
        assert not cached
        assert [r['mpn'] for r in results] == ['TPS54331DR', 'TPS54331DRG4']   # exact match first
        assert results[0]['sources'] == ['digikey', 'mouser']                  # merged, sellers combined
        assert len(results[0]['sellers']) == 2
        again, cached = external_search.search('TPS54331DR')
        assert cached and again == results
        assert dk_call.call_count == 1                                         # second search was free


def test_search_unavailable_when_budget_spent():
    cache.set('digikey_remaining', 10)
    cache.set(f'mouser_searches:{external_search.timezone.now():%Y%m%d}', external_search.MOUSER_DAILY_BUDGET)
    a, b, c, d = _patch()
    with a, b, c, d, pytest.raises(external_search.SearchUnavailable):
        external_search.search('TPS54331DR')


def test_endpoint_rejects_non_part_numbers():
    resp = APIClient().get('/api/components/external-search/', {'q': 'power supply'})
    assert resp.status_code == 400


def test_add_only_accepts_cached_results(user_factory):
    """Variants a search showed (but didn't auto-add) can be added by a signed-in user."""
    api = APIClient()
    api.force_authenticate(user_factory())
    body = {'query': 'TPS54331DR', 'mpn': 'TPS54331DRG4', 'manufacturer': 'Texas Instruments'}
    assert api.post('/api/components/external-add/', body, format='json').status_code == 400   # not searched yet
    a, b, c, d = _patch(dk_results=[_part('TPS54331DR'), _part('TPS54331DRG4')])
    with a, b, c, d:
        assert api.get('/api/components/external-search/', {'q': 'TPS54331DR'}).status_code == 200
    resp = api.post('/api/components/external-add/', body, format='json')
    assert resp.status_code == 201
    comp = Component.objects.get(part_number='TPS54331DRG4')
    assert comp.component_type == 'regulator' and not comp.is_verified
    assert comp.specifications['nexar_data']['mpn'] == 'TPS54331DRG4'
    again = api.post('/api/components/external-add/', body, format='json')
    assert again.data == {'id': str(comp.id), 'created': False}
    assert ExternalPartSearch.objects.count() == 1


def test_add_requires_login():
    resp = APIClient().post('/api/components/external-add/', {}, format='json')
    assert resp.status_code in (401, 403)


def test_search_auto_adds_exact_matches_only(user_factory):
    api = APIClient()
    user = user_factory()
    api.force_authenticate(user)
    a, b, c, d = _patch(dk_results=[_part('TPS54331DR'), _part('TPS54331DRG4')])
    with a, b, c, d:
        resp = api.get('/api/components/external-search/', {'q': 'TPS54331DR'})
    assert resp.status_code == 200
    assert [x['part_number'] for x in resp.data['added']] == ['TPS54331DR']
    comp = Component.objects.get(part_number='TPS54331DR')
    assert comp.created_by == user and comp.specifications['source'] == 'distributor_search'
    assert not Component.objects.filter(part_number='TPS54331DRG4').exists()   # variants are not auto-added


def test_anonymous_search_also_adds_without_creator():
    a, b, c, d = _patch(dk_results=[_part('TPS54331DR')])
    with a, b, c, d:
        resp = APIClient().get('/api/components/external-search/', {'q': 'TPS54331DR'})
    assert resp.data['added'][0]['created'] is True
    assert Component.objects.get(part_number='TPS54331DR').created_by is None


def test_anonymous_product_request_goes_to_moderation(user_factory, component_factory):
    from apps.components.models import ProductRequest
    from apps.products.models import Product
    comp = component_factory()
    resp = APIClient().post('/api/product-requests/', {
        'manufacturer': 'Onkyo', 'model_number': 'TX-SR507', 'component': str(comp.id),
        'notes': 'Protection mode on power-up', 'search_query': comp.part_number}, format='json')
    assert resp.status_code == 201
    req = ProductRequest.objects.get()
    assert req.status == 'pending' and req.session_key and req.requested_by is None

    moderator = user_factory(is_staff=True)
    mod = APIClient()
    mod.force_authenticate(moderator)
    listing = mod.get('/api/product-requests/', {'status': 'pending'})
    assert listing.data['count'] == 1
    done = mod.post(f'/api/product-requests/{req.id}/fulfil/', {'category': 'audio'}, format='json')
    assert done.status_code == 200 and done.data['status'] == 'created'
    product = Product.objects.get(model_number='TX-SR507')
    assert product.is_approved and product.category == 'audio'
    assert product.product_components.filter(component=comp).exists()


def test_product_request_spam_trap_and_validation():
    from apps.components.models import ProductRequest
    api = APIClient()
    assert api.post('/api/product-requests/', {'manufacturer': 'X'}, format='json').status_code == 400
    trapped = api.post('/api/product-requests/', {'manufacturer': 'Spam', 'model_number': 'Bot',
                                                  'website': 'http://spam'}, format='json')
    assert trapped.status_code == 201 and not ProductRequest.objects.exists()


def test_only_moderators_list_product_requests(user_factory):
    api = APIClient()
    api.force_authenticate(user_factory())
    assert api.get('/api/product-requests/').status_code == 403


def test_search_adds_packing_variant_when_no_exact_match():
    a, b, c, d = _patch(dk_results=[_part('MP2307DN-LF-P', stock=5), _part('MP2307DN-LF-Z', stock=900),
                                    _part('MP2307DNXYZ123456')])
    with a, b, c, d:
        resp = APIClient().get('/api/components/external-search/', {'q': 'MP2307DN'})
    assert [x['part_number'] for x in resp.data['added']] == ['MP2307DN-LF-Z']   # best stocked, short suffix
    assert not Component.objects.filter(part_number='MP2307DNXYZ123456').exists()
