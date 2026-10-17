"""
Tests for the Nexar client's handling of refused queries and the lookup view.
"""
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

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


@pytest.mark.django_db
def test_lookup_view_reports_provider_limit_as_503(component_factory, user_factory):
    component = component_factory()
    api = APIClient()
    api.force_authenticate(user_factory())
    fake = MagicMock(is_configured=True)
    fake.search_mpn.side_effect = NexarError('You have exceeded your part limit of 100.')
    with patch('apps.components.nexar.get_client', return_value=fake):
        resp = api.post(f'/api/components/{component.pk}/lookup/')
    assert resp.status_code == 503
    assert 'limit' in resp.data['detail']
