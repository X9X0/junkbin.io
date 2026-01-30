"""
Shared pytest fixtures for Junkbin.io backend tests.
"""
import pytest
from django.conf import settings

# Import all factories for easy access in tests
pytest_plugins = [
    'apps.users.tests.factories',
    'apps.products.tests.factories',
    'apps.components.tests.factories',
    'apps.submissions.tests.factories',
    'apps.reports.tests.factories',
]


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests."""
    pass


@pytest.fixture
def api_client():
    """Return a DRF API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def user(user_factory):
    """Create a basic user."""
    return user_factory()


@pytest.fixture
def trusted_user(user_factory):
    """Create a trusted user."""
    return user_factory(is_trusted=True)


@pytest.fixture
def moderator(user_factory):
    """Create a moderator user."""
    return user_factory(is_moderator=True)


@pytest.fixture
def staff_user(user_factory):
    """Create a staff user."""
    return user_factory(is_staff=True)


@pytest.fixture
def product(product_factory):
    """Create a basic product."""
    return product_factory()


@pytest.fixture
def approved_product(product_factory):
    """Create an approved product."""
    return product_factory(is_approved=True)


@pytest.fixture
def component(component_factory):
    """Create a basic component."""
    return component_factory()


@pytest.fixture
def submission(submission_factory):
    """Create a basic submission."""
    return submission_factory()
