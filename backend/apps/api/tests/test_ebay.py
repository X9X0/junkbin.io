"""The eBay account-deletion endpoint: the challenge answer eBay checks before enabling a keyset."""
import hashlib
import json

from django.test import Client, override_settings

URL = '/api/ebay/account-deletion/'


@override_settings(EBAY_VERIFICATION_TOKEN='abc123_verification-token_abc123_verification', SITE_URL='https://junkbin.io')
def test_challenge_is_sha256_of_code_token_and_endpoint():
    r = Client().get(URL, {'challenge_code': 'c0de'})
    assert r.status_code == 200 and r['Content-Type'].startswith('application/json')
    want = hashlib.sha256(('c0de' + 'abc123_verification-token_abc123_verification' + 'https://junkbin.io' + URL).encode()).hexdigest()
    assert r.json() == {'challengeResponse': want}


@override_settings(EBAY_VERIFICATION_TOKEN='abc123_verification-token_abc123_verification')
def test_notification_is_acknowledged_without_login_or_csrf():
    body = {'metadata': {'topic': 'MARKETPLACE_ACCOUNT_DELETION'}, 'notificationId': 'n1', 'notification': {'data': {'username': 'x'}}}
    r = Client(enforce_csrf_checks=True).post(URL, json.dumps(body), content_type='application/json')
    assert r.status_code == 200


@override_settings(EBAY_VERIFICATION_TOKEN='')
def test_without_a_token_the_endpoint_does_not_exist():
    assert Client().get(URL, {'challenge_code': 'c0de'}).status_code == 404
    assert Client().post(URL, '{}', content_type='application/json').status_code == 404
