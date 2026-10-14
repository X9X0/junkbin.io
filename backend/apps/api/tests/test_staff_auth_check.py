"""
Tests for the nginx auth_request staff check and the /metrics redirect exemption.
"""
import pytest
from django.test import Client


def _logged_in_client(user):
    # UserFactory never flushes its password to the DB, so a force_login
    # session looks stale on the next request - re-save first (same
    # workaround as components/tests/test_admin_views.py).
    user.set_password('testpass123')
    user.save()
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestStaffAuthCheck:
    url = '/api/auth/staff-check/'

    def test_anonymous_gets_401(self):
        assert Client().get(self.url).status_code == 401

    def test_non_staff_gets_403(self, user_factory):
        assert _logged_in_client(user_factory()).get(self.url).status_code == 403

    def test_staff_gets_204(self, staff_user):
        response = _logged_in_client(staff_user).get(self.url)
        assert response.status_code == 204
        assert 'no-cache' in response['Cache-Control']


@pytest.mark.django_db
class TestSSLRedirectExemption:
    @pytest.fixture(autouse=True)
    def ssl_redirect(self, settings):
        # Mirrors production.py; SecurityMiddleware reads these at Client init
        settings.SECURE_SSL_REDIRECT = True
        settings.SECURE_REDIRECT_EXEMPT = [r'^metrics$']

    def test_metrics_not_redirected(self):
        assert Client().get('/metrics').status_code == 200

    def test_other_paths_still_redirected(self):
        response = Client().get('/api/health/')
        assert response.status_code == 301
        assert response['Location'].startswith('https://')
