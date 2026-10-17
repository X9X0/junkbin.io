"""
Tests for part lookups: Nexar refusals, the DigiKey/Mouser fallback, and the lookup view.
"""
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from apps.components import lookup
from apps.components.distributors import DistributorError, same_maker, same_mpn
from apps.components.nexar import NexarClient, NexarError

QUOTA_BODY = {
    'errors': [{'message': 'You have exceeded your part limit of 100. Please upgrade your plan.'}],
    'data': None,
}


def _client():
    client = NexarClient()
    client.client_id = client.client_secret = 'x'
    client._token, client._token_expires = 'token', float('inf')
    return client


def test_search_mpn_raises_nexar_error_on_graphql_errors():
    resp = MagicMock(status_code=200)
    resp.json.return_value = QUOTA_BODY
    with patch('apps.components.nexar.requests.post', return_value=resp):
        with pytest.raises(NexarError, match='part limit'):
            _client().search_mpn('RC0603FR-0710KL')


def test_search_mpn_returns_none_when_no_results():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {'data': {'supSearchMpn': {'hits': 0, 'results': []}}}
    with patch('apps.components.nexar.requests.post', return_value=resp):
        assert _client().search_mpn('NOPE') is None


def _provider(result=None, error=None, configured=True):
    client = MagicMock(is_configured=configured)
    if error:
        client.search_mpn.side_effect = error
    else:
        client.search_mpn.return_value = result
    return client


def _answer(source, specs=0, price=1.0):
    return {
        'source': source, 'mpn': 'LM358DR', 'manufacturer': 'Texas Instruments',
        'description': f'{source} description', 'datasheet_url': None, 'status': 'Active',
        'specs': [{'name': f's{i}', 'value': 'v'} for i in range(specs)],
        'sellers': [{'name': source, 'url': '', 'offers': [
            {'stock': 1, 'price': price, 'currency': 'USD', 'qty_min': 1, 'buy_url': ''}]}],
    }


def _patch_providers(nexar, digikey, mouser):
    return (patch('apps.components.lookup.get_client', return_value=nexar),
            patch('apps.components.lookup.get_digikey', return_value=digikey),
            patch('apps.components.lookup.get_mouser', return_value=mouser))


@pytest.fixture
def clear_cache():
    from django.core.cache import cache
    cache.delete(lookup.NEXAR_PAUSE_KEY)
    yield
    cache.delete(lookup.NEXAR_PAUSE_KEY)


def test_lookup_merges_distributors_when_nexar_refuses(clear_cache):
    nexar = _provider(error=NexarError('You have exceeded your part limit of 100.'))
    a, b, c = _patch_providers(nexar, _provider(_answer('digikey', specs=15, price=0.2)),
                               _provider(_answer('mouser', price=0.1)))
    with a, b, c:
        result = lookup.lookup_part('LM358DR', 'TI')
    assert result['sources'] == ['digikey', 'mouser']
    assert result['description'] == 'digikey description'      # most specs leads
    assert [s['name'] for s in result['sellers']] == ['mouser', 'digikey']  # cheapest first


def test_lookup_pauses_nexar_after_refusal(clear_cache):
    nexar = _provider(error=NexarError('part limit'))
    a, b, c = _patch_providers(nexar, _provider(None), _provider(None))
    with a, b, c:
        assert lookup.lookup_part('X') is None
        assert lookup.lookup_part('Y') is None
    assert nexar.search_mpn.call_count == 1


def test_lookup_prefers_nexar_hit(clear_cache):
    digikey = _provider(_answer('digikey'))
    a, b, c = _patch_providers(_provider(_answer('nexar')), digikey, _provider(None))
    with a, b, c:
        assert lookup.lookup_part('LM358DR')['sources'] == ['nexar']
    digikey.search_mpn.assert_not_called()


def test_lookup_unavailable_when_no_provider_answers(clear_cache):
    a, b, c = _patch_providers(_provider(error=NexarError('limit')),
                               _provider(error=DistributorError('HTTP 429')),
                               _provider(configured=False))
    with a, b, c, pytest.raises(lookup.LookupUnavailable):
        lookup.lookup_part('LM358DR')


@pytest.mark.django_db
def test_lookup_view_reports_unavailable_as_503(component_factory, user_factory):
    component = component_factory()
    api = APIClient()
    api.force_authenticate(user_factory())
    with patch('apps.components.lookup.lookup_part', side_effect=lookup.LookupUnavailable('none')):
        resp = api.post(f'/api/components/{component.pk}/lookup/')
    assert resp.status_code == 503
    assert 'unavailable' in resp.data['detail']


def test_same_mpn_ignores_punctuation_and_case():
    assert same_mpn('RC0603FR-0710KL', 'rc0603fr0710kl')
    assert not same_mpn('LM358DR', 'LM358DR2G')


def test_same_maker_handles_bom_abbreviations():
    assert same_maker('NS', 'Texas Instruments')
    assert same_maker('PHILIPS', 'Nexperia USA Inc.')
    assert same_maker('VISHAY(SILICONIX)', 'Vishay Siliconix')
    assert not same_maker('ROHM', 'Texas Instruments')
