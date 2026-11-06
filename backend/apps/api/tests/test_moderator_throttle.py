"""Moderators get the 'moderator' request rate in a bucket of their own; everyone else the 'user' rate."""
from django.core.cache import cache
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.api.throttling import UserOrModeratorRateThrottle


def _throttle_for(user):
    request = APIView().initialize_request(APIRequestFactory().get('/api/products/'))
    request.user = user
    throttle = UserOrModeratorRateThrottle()
    assert throttle.allow_request(request, None)
    return throttle


def test_moderator_gets_the_moderator_rate(moderator):
    cache.clear()
    throttle = _throttle_for(moderator)
    assert throttle.scope == 'moderator' and throttle.num_requests == 10000
    assert throttle.key.startswith('throttle_moderator_')


def test_regular_user_keeps_the_user_rate(user):
    cache.clear()
    throttle = _throttle_for(user)
    assert throttle.scope == 'user' and throttle.num_requests == 1000
